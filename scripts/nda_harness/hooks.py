"""Compose Git hooks using a private wrapper directory per worktree."""
from pathlib import Path
import shlex
import subprocess
from .files import Conflict


def git(project, *args):
    return subprocess.run(["git", "-C", str(project), *args], capture_output=True, text=True, timeout=15)


def value(project, *args):
    result = git(project, *args)
    if result.returncode not in (0, 1):
        raise Conflict("Git configuration could not be inspected; reconcile hook configuration.")
    return result.stdout.strip() if result.returncode == 0 else None


def hook_plan(plan, project, state, receipt):
    worktree_local = value(project, "config", "--get", "extensions.worktreeConfig") == "true"
    worktrees = git(project, "worktree", "list", "--porcelain").stdout.count("worktree ")
    if worktrees > 1 and not worktree_local:
        raise Conflict("Multiple worktrees require Git extensions.worktreeConfig=true before adopting hooks; no sibling configuration was changed.")
    scope = "--worktree" if worktree_local else "--local"
    effective = value(project, "config", "--get", "core.hooksPath")
    prior = value(project, "config", scope, "--get", "core.hooksPath")
    destination = state / "hooks"
    registration = receipt.get("git")
    if registration:
        if effective != str(destination) or registration["scope"] != scope:
            raise Conflict("Git hook manager/configuration changed since setup; reconcile using the private receipt.")
        original = Path(registration["original_directory"])
    else:
        if effective:
            original = Path(effective)
            if not original.is_absolute():
                original = project / original
        else:
            raw = value(project, "rev-parse", "--git-path", "hooks")
            if not raw:
                raise Conflict("Cannot resolve the original Git hook directory.")
            original = Path(raw)
            if not original.is_absolute():
                original = project / original
        original = original.resolve()
        if original == destination:
            raise Conflict("Unowned harness wrapper directory; reconcile before setup.")
        registration = {"scope": scope, "previous_local_value": prior, "original_directory": str(original), "written_value": str(destination)}
    names = {"pre-commit"}
    if original.exists():
        names.update(p.name for p in original.iterdir() if p.is_file() and not p.name.endswith(".sample") and p.stat().st_mode & 0o111)
    for name in names:
        original_hook = original / name
        body = "#!/bin/sh\nset -eu\n"
        if name == "pre-commit":
            body += f"if [ -x {shlex.quote(str(original_hook))} ]; then\n  {shlex.quote(str(original_hook))} \"$@\"\nfi\n"
            body += f"exec {shlex.quote(str(project / '.nda-harness/hooks/pre-commit'))} \"$@\"\n"
        else:
            body += f"if [ -x {shlex.quote(str(original_hook))} ]; then exec {shlex.quote(str(original_hook))} \"$@\"; fi\n"
        plan.file(destination / name, body.encode(), 0o755)
    return registration


def activate(project, registration):
    result = git(project, "config", registration["scope"], "core.hooksPath", registration["written_value"])
    if result.returncode:
        raise OSError("Unable to activate repository-local Git hook wrappers.")


def restore(project, registration):
    current = value(project, "config", registration["scope"], "--get", "core.hooksPath")
    if current != registration["written_value"]:
        return False
    previous = registration["previous_local_value"]
    if previous is None:
        git(project, "config", registration["scope"], "--unset", "core.hooksPath")
    else:
        git(project, "config", registration["scope"], "core.hooksPath", previous)
    return True
