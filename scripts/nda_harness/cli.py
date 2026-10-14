"""Public setup/verify command and guided option collection."""
import argparse
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nda_harness.adapters import REGISTRY
from nda_harness.engine import install, verify, exit_code
from nda_harness.files import Conflict


def agents_value(raw):
    agents = list(dict.fromkeys(raw.split(",")))
    if not agents or any(agent not in REGISTRY for agent in agents):
        raise ValueError("--agents requires one or more of: " + ",".join(REGISTRY))
    return agents


def project_value(raw):
    import subprocess
    project = Path(raw).expanduser().absolute().resolve()
    if not project.is_dir() or any(c in str(project) for c in "\n\r"):
        raise ValueError("--project must be an existing Git worktree root without newline characters.")
    run = subprocess.run(["git", "-C", str(project), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if run.returncode or Path(run.stdout.strip()).resolve() != project:
        raise ValueError("--project must be the Git worktree root; subdirectories are not accepted.")
    return project


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
    selected = agents_value(agents) if agents else ask("Agents [codex,cursor]", agents_value)
    def scope_value(raw):
        if raw not in ("project", "user"):
            raise ValueError("--scope must be project or user.")
        return raw
    scope = scope_value(scope) if scope else ask("Scope [project/user]", scope_value)
    if scope == "user":
        if project is not None or test_command is not None:
            raise ValueError("User scope rejects --project and --test-command.")
        return {"agents": selected, "scope": scope, "project": None, "test_command": None}
    if not project and not terminal:
        raise ValueError("Missing required flag: --project")
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
    parser = argparse.ArgumentParser(prog="nda-harness", description="Configure Codex/Cursor on Apple Silicon macOS. Agents must already be installed. Changes are backed up; runtime/manual checks may leave setup pending.", epilog="Examples: ./bin/nda-harness setup; ./bin/nda-harness setup --agents codex,cursor --scope project --project /path/to/repository --test-command 'npm run test:unit'; ./bin/nda-harness setup --agents codex --scope user")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("setup", "verify"):
        sub = commands.add_parser(name, help="Guided " + name + "; full flags skip option prompts. Exit 0=verified, 1=failed, 2=invalid/prerequisite/conflict, 3=manual pending, 130=interrupted.")
        sub.add_argument("--agents", help="Comma-separated codex,cursor; future harnesses register adapters")
        sub.add_argument("--scope", help="project or user; user scope activates no Git hooks")
        sub.add_argument("--project", help="Existing Git worktree root, required for project scope")
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
            applied = install(options, source, home)
            print(f"Configured pack: {applied['pack']}\nPrivate recovery receipt: {applied['receipt']}\nChanged files: {applied['changed_files']}")
            print(f"RTK executable: {applied['rtk_path']}. If not on the client PATH, use that absolute path or configure PATH locally; setup does not edit shell startup files.")
        print("Verifying installation; the configured unit-test command executes in project scope.")
        checks = verify(options, home, observe=args.command == "verify" and sys.stdin.isatty())
        for check in checks:
            print(f"[{check['status']}] {check['check']} ({check['source']}): {check['detail']}")
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
