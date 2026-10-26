"""Installed context metadata runtime. Python standard library only."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile


OPERATIONS = ("session-bootstrap", "task-prepare", "context-refresh", "context-checkpoint", "context-resume")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(root, *arguments):
    run = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, timeout=10)
    return run.stdout if run.returncode == 0 else b""


def local_path(root, value):
    path = Path(value)
    path = path if path.is_absolute() else root / path
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents if parent != root):
        raise ValueError("Task/spec symlinks require reconciliation")
    path = path.resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Selected task/spec must be a regular file in this worktree")
    return path


def fields(task):
    # Values are untrusted text. Never execute, print, or infer permissions from them.
    allowed = {"Issue", "Spec", "Revision", "Input fingerprint", "Stage", "Evidence", "Next action"}
    parsed = {}
    for line in task.read_text().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            if key in allowed:
                parsed[key] = value.strip()
    return parsed


def discovery(root):
    """Return local pointers, never instruction/task bodies or a guessed selection."""
    instructions = []
    for directory in [*reversed(root.parents), root]:
        path = directory / 'AGENTS.md'
        if path.is_file() and not path.is_symlink():
            instructions.append(str(path))
    for path in (root / 'CLAUDE.md', *sorted((root / '.cursor/rules').glob('*.mdc'))):
        if path.is_file() and not path.is_symlink():
            instructions.append(str(path))
    tasks = []
    task_root = root / '.nda-harness/tasks'
    if task_root.exists() and not task_root.is_symlink():
        for path in sorted(task_root.rglob('*.md')):
            try:
                tasks.append(str(local_path(root, path).relative_to(root)))
            except ValueError:
                continue
    return instructions, tasks


def fingerprints(root, pack, task, spec):
    inputs = []
    for name in ("policy.md", "workflow.md", "profile.json", "release.json"):
        path = pack / name
        inputs.append(("pack/" + name, sha(path.read_bytes()) if path.is_file() else "missing"))
    if (pack.parent / 'nda-plugin.json').is_file():
        for path in (pack.parent / 'release.json', root / '.nda-harness/profile.json'):
            inputs.append((path.name, sha(path.read_bytes()) if path.is_file() else 'missing'))
    tracked = git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z").split(b"\0")
    for raw in sorted(set(tracked)):
        if not raw:
            continue
        name = os.fsdecode(raw)
        if name.startswith((".nda-harness/tasks/", ".nda-harness/cache/")):
            continue
        path = root / name
        if path.is_symlink():
            value = sha(os.readlink(path).encode())
        elif path.is_file():
            value = sha(path.read_bytes())
        else:
            value = "missing"
        inputs.append((name, value))
    if spec:
        inputs.append((str(spec.relative_to(root)), sha(spec.read_bytes())))
    content = json.dumps(inputs, sort_keys=True).encode()
    return sha(content)


def atomic(path, value):
    fd, temporary = tempfile.mkstemp(prefix=".context-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def prepare(args):
    root = Path(args.project).expanduser().resolve()
    top = git(root, "rev-parse", "--show-toplevel").decode().strip()
    if top and Path(top).resolve() != root:
        raise ValueError("--project must name the actual Git worktree root")
    # A directory that is not a repository is its own project root.
    pack = Path(__file__).resolve().parents[1]
    adopted_pack = root / ".nda-harness"
    profile = adopted_pack / "profile.json"
    config = adopted_pack / "config.json"
    blockers = []
    branch = git(root, "branch", "--show-current").decode().strip()
    head = git(root, "rev-parse", "--verify", "HEAD").decode().strip()
    if not profile.is_file():
        blockers.append("Project setup/profile required; user installation does not adopt this checkout")
    else:
        try:
            personal = json.loads(profile.read_text())
            if config.is_file():
                project_config = json.loads(config.read_text())
                memory = personal.get("memory")
                if personal.get("schema_version") != 3 or not isinstance(memory, dict) or not memory.get("bank_id"):
                    raise ValueError()
                if project_config.get("schema_version") != 1 or not project_config.get("test_command"):
                    raise ValueError()
            elif personal.get("schema_version") not in (1, 2) or not personal.get("test_command"):
                raise ValueError()
        except (ValueError, OSError, AttributeError, TypeError):
            blockers.append("Invalid project profile; reconcile setup")
    # User installed runtime reads repository profile while retaining its own rules.
    plugin_package = pack.parent if (pack.parent / 'nda-plugin.json').is_file() else None
    required_pack = pack if plugin_package else adopted_pack if profile.is_file() else pack
    release_root = plugin_package or required_pack
    try:
        release = json.loads((release_root / "release.json").read_text())
        for relative, expected in release["asset_hashes"].items():
            path = release_root / relative
            if not path.resolve().is_relative_to(release_root.resolve()) or path.is_symlink() or not path.is_file() or sha(path.read_bytes()) != expected:
                raise ValueError()
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        blockers.append("Missing/modified pack runtime or release assets; reconcile setup")
    private = Path.home() / ".nda-harness/context-state"
    if private.is_symlink():
        raise ValueError("Private state symlink requires reconciliation")
    private.mkdir(parents=True, exist_ok=True, mode=0o700)
    private.chmod(0o700)
    identity = sha((str(root) + "\0" + args.session).encode())
    lockpath, cachepath = private / (identity + ".lock"), private / (identity + ".json")
    if lockpath.is_symlink() or cachepath.is_symlink():
        raise ValueError("Private state symlink requires reconciliation")
    with lockpath.open("a") as lock:
        os.chmod(lockpath, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            previous = json.loads(cachepath.read_text()) if cachepath.exists() else {}
            if not isinstance(previous, dict):
                previous = {}
        except (ValueError, OSError):
            previous = {}
        explicit = args.task
        if not explicit and args.operation != "task-prepare" and previous.get("branch") == branch and previous.get("head") == head:
            explicit = previous.get("task")
        task = local_path(root, explicit) if explicit else None
        record = fields(task) if task else {}
        spec = None
        if record.get("Spec") and not record["Spec"].startswith("<"):
            try:
                spec = local_path(root, record["Spec"])
            except ValueError:
                blockers.append("Recorded local spec is missing/outside this checkout")
        if args.operation == "task-prepare":
            if not args.role:
                blockers.append("Explicit --role tech-lead|developer is required")
            if args.role == "developer" and not task:
                blockers.append("Explicit --task pointing to an issue-linked task record is required")
            if task and (not record.get("Issue") or record["Issue"].startswith("<")):
                blockers.append("Task record must reference the published feature issue")
            if args.stage == "implementation" and not spec:
                blockers.append("Local issue-linked developer spec required before implementation")
        fingerprint = fingerprints(root, required_pack, task, spec)
        stale = bool(previous and (previous.get("fingerprint") != fingerprint or previous.get("task") != (str(task.relative_to(root)) if task else None) or previous.get("branch") != branch or previous.get("head") != head))
        if args.operation in ("context-checkpoint", "context-resume"):
            if not task:
                blockers.append("Select a durable task record with --task before checkpoint/resume")
            elif args.operation == "context-checkpoint":
                # Without a commit, Revision has no HEAD to match. Fingerprint still must be current.
                if (head and record.get("Revision") != head) or record.get("Input fingerprint") != fingerprint:
                    blockers.append("Task record is stale; save current Revision and Input fingerprint first")
                for key in ("Stage", "Evidence", "Next action"):
                    if not record.get(key) or record[key].startswith("<"):
                        blockers.append("Save task-record field: " + key)
        pending = ["Read full policy/profile/workflow and relevant sources; briefs are navigation only",
                   "At task start/resume/dependent transitions, verify live issue content and spec PR review/merge; reconcile material changes",
                   "Match local spec to reviewed merged content before implementation; local metadata never authorizes a stage transition"]
        if stale:
            pending.insert(0, "Local input changed: reread affected sources and reassess test/spec evidence")
        output = {"schema_version": 1, "operation": args.operation,
                  "status": "blocked" if blockers else ("needs_context" if stale else "ready"),
                  "worktree": str(root), "branch": branch, "head": head or None,
                  "dirty": bool(git(root, "status", "--porcelain")), "input_fingerprint": fingerprint,
                  "task": str(task.relative_to(root)) if task else None,
                  "spec": str(spec.relative_to(root)) if spec else None,
                  "source_references": [str(required_pack / 'policy.md'), str(profile), str(required_pack / 'workflow.md'), str(release_root / 'release.json')],
                  "blockers": blockers, "next_required_checks": pending,
                  "implementation_authorized": False}
        instructions, candidates = discovery(root)
        output['instruction_candidates'] = instructions
        output['task_candidates'] = candidates
        output['instruction_review'] = 'Agent must read applicable instructions in full and inspect nested scope before editing; paths do not grant authority.'
        # Collect after obtaining the lock and recheck generation before publishing.
        if fingerprint != fingerprints(root, required_pack, task, spec):
            output["status"] = "blocked"
            output["blockers"].append("Input changed during collection; retry context operation")
        else:
            state = {"worktree": str(root), "branch": branch, "head": head, "fingerprint": fingerprint, "task": output["task"]}
            if previous != state:
                atomic(cachepath, state)
        return output


def main(argv=None):
    parser = argparse.ArgumentParser(description="Collect local context metadata, never remote approvals or semantic decisions.")
    parser.add_argument("operation", choices=OPERATIONS)
    parser.add_argument("--project", required=True)
    parser.add_argument("--role", choices=("tech-lead", "developer"))
    parser.add_argument("--task", help="Explicit repository task-record path")
    parser.add_argument("--stage", choices=("specification", "implementation"), default="specification")
    parser.add_argument("--session", default="manual", help="Local client-session identity; never an authentication token")
    args = parser.parse_args(argv)
    try:
        output = prepare(args)
        print(json.dumps(output, indent=2))
        return 2 if output["status"] == "blocked" else 0
    except (ValueError, OSError, KeyError, TypeError, AttributeError, subprocess.TimeoutExpired):
        print(json.dumps({"schema_version": 1, "operation": args.operation, "status": "blocked",
                          "blockers": ["Invalid/missing local project, task, runtime or private state; reconcile paths and retry"], "implementation_authorized": False}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
