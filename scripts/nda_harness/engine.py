"""Shared preflight/apply/verify pipeline; adapters own harness differences."""
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

from .adapters import REGISTRY
from .adapters.common import SKILLS
from .files import Plan, Conflict, atomic, digest, guard_path, json_bytes, read
from .hooks import hook_plan, activate, restore, value
from .dependencies import prepare as prepare_rtk, locate as locate_rtk, identity as rtk_identity
from . import hindsight


def check_host():
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise ValueError("This phase supports Apple Silicon macOS only. Intel support is deferred.")
    if sys.version_info < (3, 9):
        raise ValueError("Python 3.9+ is required.")
    if not shutil.which("git"):
        raise ValueError("Install Git before setup.")


def detect(family):
    return REGISTRY[family].detect()


def paths(options, home):
    pack = options["project"] / ".nda-harness" if options["scope"] == "project" else home / ".nda-harness/pack"
    key = digest(str(options["project"]) if options["scope"] == "project" else "user")
    return pack, home / ".nda-harness/state" / key


def load_receipt(state):
    path = state / "receipt.json"
    guard_path(path, write=False)
    try:
        receipt = json.loads(path.read_text()) if path.exists() else {"schema_version": 1, "owned": {}, "recovery": []}
        if receipt.get("schema_version") != 1 or not isinstance(receipt.get("owned"), dict):
            raise ValueError()
        return receipt
    except (ValueError, UnicodeError, AttributeError):
        raise Conflict("Malformed private ownership receipt; reconcile before setup.") from None


def _owned_project_paths(receipt, project):
    paths = []
    for key in receipt.get("owned", {}):
        raw, separator, _tag = key.rpartition("::")
        if not separator:
            continue
        path = Path(raw)
        try:
            path.relative_to(project)
        except ValueError:
            continue
        paths.append(path)
    return paths


def discard_absent_project_receipt(receipt, options, state):
    """Drop a private receipt when the project installation is completely gone.

    Setup used to stop on the stale hook registration and write nothing back.
    A remaining pack directory, any owned project file, or a different hook
    manager still has to be reconciled instead of being replaced.
    """
    if options["scope"] != "project":
        return receipt
    receipt_path = state / "receipt.json"
    if not receipt_path.is_file():
        return receipt
    project = options["project"]
    if (project / ".nda-harness").exists():
        return receipt
    if any(path.exists() for path in _owned_project_paths(receipt, project)):
        return receipt
    registration = receipt.get("git")
    if isinstance(registration, dict):
        effective = value(project, "config", "--get", "core.hooksPath")
        recorded = registration.get("written_value")
        if effective and effective != recorded:
            return receipt
        restore(project, registration)
    receipt_path.unlink()
    print("Removed stale private receipt because the project installation is gone; continuing setup.")
    return {"schema_version": 1, "owned": {}, "recovery": []}


def assets(source, options):
    result = {}
    for directory, prefix in ((source / "pack", Path(".")), (source / "skills", Path("skills"))):
        for path in sorted(directory.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and not path.name.endswith(".pyc"):
                if path.is_symlink():
                    raise Conflict("Source assets must be complete regular files, not symlinks.")
                relative = prefix / path.relative_to(directory)
                content = path.read_bytes()
                if relative == Path("skills/catalog.md"):
                    content = content.replace(b"../docs/architecture.md", b"https://github.com/pilacorp/nda-harness/blob/main/docs/architecture.md")
                mode = 0o755 if path.stat().st_mode & 0o111 or relative.as_posix() in ("scripts/prepare-context", "hooks/pre-commit") else 0o644
                result[relative] = (content, mode)
    if options["scope"] == "project":
        profile = {"schema_version": 1, "test_command": options["test_command"], "spec_directory": "specs", "task_directory": ".nda-harness/tasks"}
        result[Path("profile.json")] = (json_bytes(profile), 0o644)
    hashes = {str(path): digest(content) for path, (content, _) in result.items()}
    revision = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    release = {"schema_version": 1, "harness_revision": revision or "source-checkout", "asset_hashes": hashes,
               "phase": "codex-cursor-claude-apple-silicon", "native_lifecycle_hooks": "entrypoint_fallback"}
    result[Path("release.json")] = (json_bytes(release), 0o644)
    return result


def install(options, source, home):
    check_host()
    for family in options["agents"]:
        if not detect(family):
            raise ValueError(f"No installed {family} surface detected. Install the agent application/CLI separately.")
    pack, state = paths(options, home)
    # Guard state ancestors before opening a lock; lock serializes concurrent setup/verify.
    guard_path(state / "setup.lock")
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    state.chmod(0o700)
    memory_state = hindsight.shared_state(home)
    guard_path(memory_state / "setup.lock")
    memory_state.mkdir(parents=True, exist_ok=True, mode=0o700)
    memory_state.chmod(0o700)
    with (memory_state / "setup.lock").open("a") as memory_lock, (state / "setup.lock").open("a") as lock:
        os.chmod(memory_state / "setup.lock", 0o600)
        fcntl.flock(memory_lock, fcntl.LOCK_EX)
        os.chmod(state / "setup.lock", 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        receipt = discard_absent_project_receipt(load_receipt(state), options, state)
        shared = hindsight.load_shared(home)
        plan = Plan({"owned": {**receipt["owned"], **shared["owned"]}})
        memory_agents = sorted(set(receipt.get("memory_agents", [])) | set(options.get("hindsight", {}).get("agents", [])))
        options = {**options, "memory_agents": memory_agents}
        if options["scope"] == "project":
            ignore = options["project"] / ".gitignore"
            original = read(ignore)
            if original is not None:
                missing = [pattern for pattern in (b"__pycache__/", b"*.py[cod]") if pattern not in original.splitlines()]
                if missing:
                    newline = b"\r\n" if b"\r\n" in original else b"\n"
                    separator = newline if original and not original.endswith(b"\n") else b""
                    # Keep .gitignore user-owned so later developer edits remain valid.
                    plan.write(ignore, original + separator + newline.join(missing) + newline)
        files = assets(source, options)
        registrations = dict(receipt.get("registrations", {}))
        context7_added = []
        expected = {pack / relative for relative in files}
        if options["scope"] == "user" and "cursor" in options["agents"]:
            expected.add(pack / "cursor-user-rules.md")
        expected.update(Path(key.rsplit("::", 1)[0]) for key in receipt["owned"])
        if pack.exists():
            for existing in pack.rglob("*"):
                relative = existing.relative_to(pack)
                if relative.parts[0] == "tasks" or "__pycache__" in relative.parts:
                    continue
                if (existing.is_file() or existing.is_symlink()) and existing not in expected:
                    raise Conflict(f"Unknown installed pack content requires reconciliation: {existing}")
        for relative, (content, mode) in files.items():
            plan.file(pack / relative, content, mode)
        for family in options["agents"]:
            before = set(plan.owned)
            adapter = REGISTRY[family]
            if adapter.plan(plan, options, home, pack):
                context7_added.append(family)
            destination = adapter.skill_root(options, home)
            for relative, (content, mode) in files.items():
                if relative.parts[0] == "skills" and len(relative.parts) > 2:
                    plan.file(destination / Path(*relative.parts[1:]), content, mode)
            registrations[family] = sorted(set(registrations.get(family, [])) | (set(plan.owned) - before))
            # Reject shadowing instead of silently claiming duplicated skill discovery works.
            other_root = home / adapter.skill_directory / "skills" if options["scope"] == "project" else None
            if other_root and any((other_root / name).exists() for name in SKILLS):
                raise Conflict(f"Simultaneous user/project skill registrations require reconciliation: {other_root}")
        hindsight.plan_connections(plan, options, home)
        if options.get("hindsight"):
            shared_owned = {key: value for key, value in plan.owned.items() if key.endswith("::" + hindsight.TAG)}
            plan.write(memory_state / "receipt.json", json_bytes({"schema_version": 1, "owned": shared_owned}), 0o600, private=True)
        registration = hook_plan(plan, options["project"], state, receipt) if options["scope"] == "project" else None
        executable = prepare_rtk(plan, home)
        activated = False
        try:
            plan.apply(state)
            if registration:
                activate(options["project"], registration)
                activated = True
            receipt.update(schema_version=1, owned={key: value for key, value in plan.owned.items() if not key.endswith("::" + hindsight.TAG)},
                           registrations=registrations,
                           agents=sorted(set(receipt.get("agents", []) + options["agents"])),
                           scope=options["scope"], pack=str(pack), memory_agents=memory_agents)
            if registration:
                receipt["git"] = registration
            receipt.setdefault("recovery", []).extend(plan.applied)
            atomic(state / "receipt.json", json_bytes(receipt))
        except (Exception, KeyboardInterrupt):
            if activated and registration:
                restore(options["project"], registration)
            unresolved = plan.rollback(shared_paths={home / ".nda-harness/bin/rtk"})
            atomic(state / "recovery-needed.json", json_bytes({"paths": unresolved, "writes": plan.applied,
                   "retained_shared_dependency": str(home / ".nda-harness/bin/rtk") if (home / ".nda-harness/bin/rtk").exists() else None}))
            raise
    return {"pack": str(pack), "receipt": str(state / "receipt.json"), "changed_files": len(plan.writes), "rtk_path": str(executable), "context7_added": context7_added, "memory_agents": memory_agents}


def result(name, status, detail, source="automated"):
    return {"check": name, "status": status, "source": source, "detail": detail}


def verify(options, home, live_mcp=True):
    check_host()
    from .mcp import check_context7
    pack, state = paths(options, home)
    checks = []
    try:
        receipt = load_receipt(state)
        release = json.loads((pack / "release.json").read_text())
        hashes = release["asset_hashes"]
        for relative, expected in hashes.items():
            path = pack / relative
            if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != expected:
                raise ValueError()
        for relative in ("scripts/prepare-context", "hooks/pre-commit"):
            if not os.access(pack / relative, os.X_OK):
                raise ValueError()
        checks.append(result("pack", "verified", "Installed templates, skills and runtime match release hashes."))
    except (OSError, ValueError, KeyError, TypeError, AttributeError, Conflict):
        return [result("pack", "failed", "Installation/receipt missing, modified or invalid; run setup after reconciliation.")]
    for family in options["agents"]:
        if family not in receipt.get("agents", []):
            checks.append(result(family + "-registration", "failed", "Selected family has not been configured; run setup for it."))
    # Compare owned units, so unrelated instruction/config edits do not invalidate them.
    ignored = set()
    for family, keys in receipt.get("registrations", {}).items():
        if family not in options["agents"]:
            ignored.update(keys)
    for key, expected in receipt["owned"].items():
        if key in ignored:
            continue
        raw_path, tag = key.rsplit("::", 1)
        path = Path(raw_path)
        try:
            guard_path(path, write=False)
            content = path.read_bytes()
            if path.parent == state / "hooks" and not os.access(path, os.X_OK):
                raise ValueError()
            if tag == "block":
                text = content.decode()
                begin, end = "<!-- nda-harness:begin -->", "<!-- nda-harness:end -->"
                if text.count(begin) != 1 or text.count(end) != 1:
                    raise ValueError()
                content = text[text.index(begin):text.index(end) + len(end)].encode()
            elif tag == "mcp":
                if path.suffix == ".toml":
                    import tomlkit
                    doc = tomlkit.parse(content.decode()).unwrap()
                    servers = doc["mcp_servers"]
                else:
                    servers = json.loads(content)["mcpServers"]
                content = json_bytes(servers["nda-harness-context7"])
            if digest(content) != expected:
                raise ValueError()
        except (OSError, ValueError, KeyError, TypeError, AttributeError, Conflict):
            checks.append(result("registration", "failed", f"Owned registration changed or missing: {path}"))
    if receipt.get("memory_agents"):
        checks.extend(hindsight.verify_connections(options, home, receipt, live=live_mcp))
    rtk = locate_rtk(home)
    if rtk:
        passed = rtk_identity(rtk)
        checks.append(result("rtk-binary", "verified" if passed else "failed", "RTK must match a recorded compatible build checksum and version; unknown builds require reconciliation."))
    else:
        checks.append(result("rtk-binary", "failed", "Pinned RTK is missing; run setup to install it after reconciliation."))
    checks.append(check_context7() if live_mcp else result("context7-server", "awaiting_manual", "Live public MCP diagnostic was not run."))
    if options["scope"] == "project":
        registration = receipt.get("git", {})
        if value(options["project"], "config", "--get", "core.hooksPath") != registration.get("written_value"):
            checks.append(result("git-registration", "failed", "Effective hook directory changed; reconcile setup."))
        else:
            checks.append(result("git-registration", "verified", "Worktree hook wrappers match the recorded registration."))
        try:
            profile = json.loads((pack / "profile.json").read_text())
            command = profile["test_command"]
            if not isinstance(command, str) or not command.strip():
                raise ValueError()
            run = subprocess.run(["/bin/sh", "-c", command], cwd=options["project"], capture_output=True, timeout=300)
            checks.append(result("unit-tests", "verified" if run.returncode == 0 else "failed", "Configured unit-test command ran from the repository root; output is not retained."))
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
            checks.append(result("unit-tests", "failed", "Missing/invalid profile or test runtime failure; inspect locally."))
    for family in options["agents"]:
        adapter = REGISTRY[family]
        surfaces = detect(family)
        if not surfaces:
            checks.append(result(family, "failed", "No installed surface detected; install separately."))
        for surface, version in surfaces:
            if surface.endswith("-cli"):
                executable = shutil.which(adapter.executable)
                try:
                    run = subprocess.run([executable, "--version"], cwd=options["project"] or home,
                                         stdin=subprocess.DEVNULL, capture_output=True, timeout=15)
                    checks.append(result(surface + "-runtime", "failed" if run.returncode else "verified",
                                         "Client version probe failed; repair the executable installation." if run.returncode else "Client version probe passed; this does not prove fresh-session compatibility."))
                except (OSError, subprocess.TimeoutExpired):
                    checks.append(result(surface + "-runtime", "failed", "Client executable unavailable or timed out."))
            for number, step in enumerate(adapter.manual_steps(pack)):
                if options["scope"] == "project" and "For user scope" in step:
                    continue
                checks.append(result(f"{surface}-manual-{number}", "awaiting_manual", step, "manual required"))
        checks.extend(adapter.checks(options, home))
    summary = {"schema_version": 1, "observed_at": datetime.now(timezone.utc).isoformat(),
               "checks": [{"check": c["check"], "status": c["status"], "source": c["source"]} for c in checks],
               "release_sha256": digest((pack / "release.json").read_bytes())}
    guard_path(state / "readiness.json")
    atomic(state / "readiness.json", json_bytes(summary))
    return checks


def exit_code(checks):
    if any(c["status"] == "failed" for c in checks):
        return 1
    if any(c["status"] == "awaiting_manual" for c in checks):
        return 3
    return 0
