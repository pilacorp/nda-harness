#!/usr/bin/env python3
"""Collect prerequisite evidence without configuring personal agent installations.

This is trial tooling, not the NDA Harness setup/verify implementation. --rtk
initializes the installed upstream RTK in disposable homes and repositories.
It never starts an agent session, authenticates, downloads, or installs software.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import subprocess
import tempfile


SURFACES = ("cursor-ide", "cursor-cli", "codex-desktop", "codex-cli", "claude-desktop-code", "claude-code-cli")
VERSION = re.compile(r"(?:rtk |codex(?:-cli)? )?([0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?)")
SENTINEL = "Existing trial instructions must survive.\n"


def isolated_environment(home, path):
    # Replace only the child's environment; never mutate the invoking process.
    return {"HOME": str(home), "PATH": path, "CODEX_HOME": str(home / ".codex"),
            "XDG_CONFIG_HOME": str(home / ".config"), "NO_OPEN_BROWSER": "1"}


def version_probe(executable, env, cwd):
    if not executable:
        return {"status": "not_installed", "version": None}
    try:
        result = subprocess.run([executable, "--version"], cwd=cwd, env=env,
                                capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired:
        return {"status": "failed", "version": None, "reason": "timeout"}
    except OSError:
        return {"status": "failed", "version": None, "reason": "cannot_execute"}
    if result.returncode:
        return {"status": "failed", "version": None, "exit_code": result.returncode}
    first = result.stdout.splitlines()[0] if result.stdout else ""
    match = VERSION.fullmatch(first.strip())
    return {"status": "available" if match else "unrecognized_version",
            "version": match.group(1) if match else None}


def file_hashes(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()}


def pending_matrix():
    return [{"architecture": arch, "surface": surface, "scope": scope, "status": "pending"}
            for arch in ("arm64", "x86_64") for surface in SURFACES for scope in ("project", "user")]


def inventory(env, cwd):
    result = {"os": platform.system(), "os_version": platform.mac_ver()[0],
              "architecture": platform.machine(), "python": platform.python_version(),
              "cli": {}, "applications": {}}
    for name in ("rtk", "codex", "cursor", "agent", "claude"):
        result["cli"][name] = version_probe(shutil.which(name), env, cwd)
    for label, bundle in (("cursor-ide", "Cursor"), ("codex-desktop", "ChatGPT"), ("claude-desktop-code", "Claude")):
        plist = Path("/Applications") / (bundle + ".app") / "Contents/Info.plist"
        entry = {"status": "not_installed", "version": None}
        if plist.is_file():
            try:
                data = plistlib.loads(plist.read_bytes())
                raw = data.get("CFBundleShortVersionString", "")
                match = VERSION.fullmatch(raw)
                entry = {"status": "detected" if match else "unrecognized_version",
                         "version": match.group(1) if match else None}
            except (OSError, plistlib.InvalidFileException, TypeError):
                entry["status"] = "unreadable_bundle"
        result["applications"][label] = entry
    result["applications"]["codex-desktop"]["limitation"] = "ChatGPT bundle detection does not establish Codex runtime support"
    return result


def rtk_trial(executable, base, family, scope, path):
    home, repo = base / "home", base / "repo"
    home.mkdir(parents=True)
    repo.mkdir()
    for folder in (".codex", ".cursor", ".claude"):
        (home / folder).mkdir()
    instructions = repo / "AGENTS.md" if scope == "project" else home / ".codex/AGENTS.md"
    instructions.write_text(SENTINEL)
    (home / ".claude/CLAUDE.md").write_text(SENTINEL)
    hooks = home / ".cursor/hooks.json"
    original_handler = {"command": "/usr/bin/true"}
    hooks.write_text(json.dumps({"version": 1, "hooks": {"sessionStart": [original_handler]}}))
    env = isolated_environment(home, path)
    arguments = [executable, "init", *( ["--codex"] if family == "codex" else ["--agent", "cursor"] ),
                 *(["--global"] if scope == "user" else [])]
    attempts = []
    for _ in range(2):
        try:
            run = subprocess.run(arguments, cwd=repo, env=env, input="", capture_output=True, text=True, timeout=20)
            attempts.append({"exit_code": run.returncode, "files": file_hashes(base)})
        except (OSError, subprocess.TimeoutExpired):
            attempts.append({"exit_code": None, "reason": "cannot_execute_or_timeout", "files": file_hashes(base)})
    try:
        handlers = json.loads(hooks.read_text())["hooks"]["sessionStart"]
        hook_preserved = original_handler in handlers
    except (OSError, ValueError, KeyError, TypeError):
        hook_preserved = False
    return {"family": family, "scope": scope, "source": "automated", "command": "rtk " + " ".join(arguments[1:]),
            "attempts": attempts, "rerun_files_unchanged": attempts[0]["files"] == attempts[1]["files"],
            "existing_instructions_preserved": instructions.read_text().startswith(SENTINEL),
            "existing_cursor_handler_preserved": hook_preserved,
            "existing_claude_instructions_preserved": (home / ".claude/CLAUDE.md").read_text().startswith(SENTINEL),
            "client_runtime_verified": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rtk", action="store_true", help="Exercise upstream initialization twice per scope in disposable homes")
    args = parser.parse_args(argv)
    path = os.environ.get("PATH", "/usr/bin:/bin")
    with tempfile.TemporaryDirectory(prefix="nda-minimal-cli-trial-") as temporary:
        root = Path(temporary)
        home = root / "inventory-home"
        home.mkdir()
        result = {"schema_version": 1, "observed_at": datetime.now(timezone.utc).isoformat(),
                  "kind": "prerequisite_trial", "installer_ready": False,
                  "inventory": inventory(isolated_environment(home, path), root),
                  "rtk_trials": [], "release_matrix": pending_matrix()}
        if args.rtk:
            executable = shutil.which("rtk")
            if not executable:
                result["rtk_trials"] = [{"status": "not_installed"}]
            else:
                result["rtk_binary_sha256"] = hashlib.sha256(Path(executable).read_bytes()).hexdigest()
                result["rtk_trials"] = [rtk_trial(executable, root / (family + "-" + scope), family, scope, path)
                                        for family in ("codex", "cursor") for scope in ("project", "user")]
        print(json.dumps(result, indent=2))
    # A successful evidence collection is still not completed compatibility.
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
