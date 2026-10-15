"""Public setup/verify command and guided option collection."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nda_harness.adapters import REGISTRY
from nda_harness.engine import install, verify, exit_code, paths
from nda_harness.files import Conflict, atomic, guard_path, json_bytes
from nda_harness.prompts import select_options
from nda_harness.hooks import git


def agents_value(raw):
    agents = list(dict.fromkeys(raw.split(",")))
    if not agents or any(agent not in REGISTRY for agent in agents):
        raise ValueError("--agents requires one or more of: " + ",".join(REGISTRY))
    return agents


def project_value(raw):
    project = Path(raw).expanduser().absolute().resolve()
    if not project.is_dir() or any(c in str(project) for c in "\n\r"):
        raise ValueError("--project must be an existing Git worktree root without newline characters.")
    run = subprocess.run(["git", "-C", str(project), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if run.returncode or Path(run.stdout.strip()).resolve() != project:
        raise ValueError("--project must be the Git worktree root; subdirectories are not accepted.")
    return project


def detect_project():
    try:
        run = git(Path.cwd(), "rev-parse", "--show-toplevel")
        return project_value(run.stdout.strip()) if run.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def collect_options(command, agents, scope, project, test_command):
    terminal = sys.stdin.isatty()
    def ask(label, parse):
        while True:
            raw = input(label + ": ").strip()
            try:
                return parse(raw)
            except ValueError as error:
                print(error, file=sys.stderr)
    missing = []
    if not agents:
        missing.append("--agents")
    if not scope:
        missing.append("--scope")
    if scope == "project":
        if not project:
            missing.append("--project")
        if command == "setup" and not test_command:
            missing.append("--test-command")
    if missing and not terminal:
        raise ValueError("Missing required flags: " + ", ".join(missing) + "; project scope also requires --project and --test-command for setup.")
    labels = {"codex": "Codex", "cursor": "Cursor", "claude": "Claude Code"}
    selected = agents_value(agents) if agents else select_options("Agents", [(name, labels.get(name, name)) for name in REGISTRY], multiple=True)
    def scope_value(raw):
        if raw not in ("project", "user"):
            raise ValueError("--scope must be project or user.")
        return raw
    scope = scope_value(scope) if scope else select_options("Scope", [
        ("project", "Project - this repository, including Git test hook"),
        ("user", "User - personal registrations, no Git hooks"),
    ])[0]
    if scope == "user":
        if project is not None or test_command is not None:
            raise ValueError("User scope rejects --project and --test-command.")
        return {"agents": selected, "scope": scope, "project": None, "test_command": None}
    if not project and not terminal:
        raise ValueError("Missing required flag: --project")
    if not project:
        detected = detect_project()
        if detected:
            project = select_options("Target Git worktree root", [
                (str(detected), f"Use {detected}"),
                ("", "Choose another folder"),
            ])[0]
    project = project_value(project) if project else ask("Target Git worktree root", project_value)
    if command == "verify":
        if test_command is not None:
            raise ValueError("verify rejects --test-command; it reads the installed profile.")
    else:
        def test_value(raw):
            if not raw.strip():
                raise ValueError("--test-command must be an explicit nonempty non-watch unit-test command.")
            return raw
        if not test_command and not terminal:
            raise ValueError("Missing required flag: --test-command")
        test_command = test_value(test_command) if test_command is not None else ask("Non-watch unit-test command (will execute from repository root)", test_value)
    return {"agents": selected, "scope": scope, "project": project, "test_command": test_command}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="nda-harness", description="Configure Codex/Cursor/Claude Code on Apple Silicon macOS. Agents must already be installed. Changes are backed up; automatic verification reports session-only checks as pending without observation prompts.", epilog="Examples: ./bin/nda-harness setup; ./bin/nda-harness setup --agents codex,cursor,claude --scope project --project /path/to/repository --test-command 'npm run test:unit'; ./bin/nda-harness verify --agents claude --scope user")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("setup", "verify"):
        sub = commands.add_parser(name, help="Guided " + name + "; full flags skip option prompts. Exit 0=verified, 1=failed, 2=invalid/prerequisite/conflict, 3=manual pending, 130=interrupted.")
        sub.add_argument("--agents", help="Comma-separated " + ",".join(REGISTRY))
        sub.add_argument("--scope", help="project or user; user scope activates no Git hooks")
        sub.add_argument("--project", help="Existing Git worktree root; when omitted interactively, detect from the current folder and confirm")
        sub.add_argument("--test-command", help="setup project only: explicit non-watch unit command; executed by setup/verify/pre-commit")
    args = parser.parse_args(argv)
    try:
        import tomlkit
        if tomlkit.__version__ != "0.13.3":
            raise ValueError("CLI dependency bundle version mismatch; reinstall from an intact checkout.")
        options = collect_options(args.command, args.agents, args.scope, args.project, args.test_command)
        source = Path(__file__).resolve().parents[2]
        home = Path.home().resolve()
        if args.command == "setup":
            print("Setting up harness and Context7 MCP (missing connections are added automatically)...")
            applied = install(options, source, home)
            print(f"Configured pack: {applied['pack']}\nPrivate recovery receipt: {applied['receipt']}\nChanged files: {applied['changed_files']}")
            print(f"RTK executable: {applied['rtk_path']}. If not on the client PATH, use that absolute path or configure PATH locally; setup does not edit shell startup files.")
            added = applied["context7_added"]
            print("Context7 MCP: " + ("added for " + ", ".join(added) if added else "already configured") + ".")
            for family in added:
                for step in REGISTRY[family].manual_steps(Path(applied["pack"])):
                    if "nda-harness-context7" in step:
                        print(f"Context7 connection ({family}): {step}")
        print("Running automatic verification...")
        checks = verify(options, home)
        _, state = paths(options, home)
        report = state / "verification.json"
        guard_path(report)
        state.mkdir(parents=True, exist_ok=True, mode=0o700)
        state.chmod(0o700)
        atomic(report, json_bytes({"schema_version": 1, "observed_at": datetime.now(timezone.utc).isoformat(), "checks": checks}))
        counts = {status: sum(check["status"] == status for check in checks) for status in ("verified", "failed", "awaiting_manual")}
        print(f"Verification: {counts['verified']} verified, {counts['failed']} failed, {counts['awaiting_manual']} pending. Details: {report}")
        if args.command == "setup":
            import shlex
            followup = [str(source / "bin/nda-harness"), "verify", "--agents", ",".join(options["agents"]), "--scope", options["scope"]]
            if options["project"]:
                followup += ["--project", str(options["project"])]
            print("After completing manual steps: " + shlex.join(followup))
        return exit_code(checks)
    except (ValueError, Conflict) as error:
        print(str(error), file=sys.stderr)
        return 2
    except (EOFError, KeyboardInterrupt):
        print("Interrupted. Rerun setup; private receipts retain recovery information for completed writes.", file=sys.stderr)
        return 130
    except ImportError:
        print("CLI dependency bundle could not load; reinstall from an intact checkout.", file=sys.stderr)
        return 2
    except OSError:
        print("Filesystem/process failure; inspect local prerequisites and private recovery receipts.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
