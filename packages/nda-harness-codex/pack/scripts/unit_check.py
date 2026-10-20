"""Installed unit-test commit gate. Standard library only."""
import json
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(sys.argv[1])
    try:
        profile = json.loads((root / ".nda-harness/profile.json").read_text())
        command = profile["test_command"]
        if not isinstance(command, str) or not command.strip():
            raise ValueError()
        # Execute only the explicit profile command, never a task/spec instruction.
        run = subprocess.run(["/bin/sh", "-c", command], cwd=root, timeout=300, capture_output=True)
        if run.returncode:
            print("NDA pre-commit: unit tests failed; rerun the configured command locally for output.", file=sys.stderr)
        return run.returncode
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
        print("NDA pre-commit: missing/invalid profile or test runtime failure; reconcile setup.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
