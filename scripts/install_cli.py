"""Install the complete local CLI bundle without third-party tooling."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import tempfile


def digest(data):
    return hashlib.sha256(data).hexdigest()


def install(source, prefix):
    prefix = prefix.expanduser().resolve()
    destination = prefix / "share/nda-harness"
    command = prefix / "bin/nda-harness"
    for path in (destination, command, *destination.parents, *command.parents):
        if path.is_symlink():
            raise ValueError("Install destination symlink requires reconciliation.")
    shim = ('#!/bin/sh\n# NDA Harness managed launcher\nexec ' + shlex.quote(str(destination / 'bin/nda-harness')) + ' "$@"\n').encode()
    if command.exists() and (not command.is_file() or command.read_bytes() != shim or not os.access(command, os.X_OK)):
        raise ValueError("An existing nda-harness command conflicts with this installation; choose a different --prefix.")
    payload = {}
    for directory in ("bin", "scripts", "pack", "skills", "vendor"):
        for path in sorted((source / directory).rglob("*")):
            if "__pycache__" in path.parts or path.suffix == ".pyc":
                continue
            if path.is_symlink():
                raise ValueError("Source bundle must contain regular files, not symlinks.")
            if path.is_file():
                payload[str(path.relative_to(source))] = digest(path.read_bytes())
    # Validate the bundled dependency before copying or installing a command.
    sys.path.insert(0, str(source / "scripts"))
    from nda_harness.bundled import load
    load()
    manifest = {"schema_version": 1, "files": payload}
    if destination.exists():
        try:
            recorded = json.loads((destination / "install-manifest.json").read_text())
            if recorded != manifest:
                raise ValueError()
            existing = {str(p.relative_to(destination)) for p in destination.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.name != "install-manifest.json"}
            if existing != set(payload):
                raise ValueError()
            for relative, checksum in payload.items():
                path = destination / relative
                if path.is_symlink() or digest(path.read_bytes()) != checksum:
                    raise ValueError()
        except (OSError, ValueError, TypeError):
            raise ValueError("Existing CLI bundle differs or was modified; choose a different --prefix or reconcile it before reinstalling.") from None
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".nda-install-", dir=destination.parent) as temporary:
            staged = Path(temporary) / "bundle"
            staged.mkdir()
            for relative in payload:
                target = staged / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source / relative, target)
                if digest(target.read_bytes()) != payload[relative]:
                    raise ValueError("Source bundle changed during installation; retry from an intact checkout.")
            (staged / "install-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            os.rename(staged, destination)
    command.parent.mkdir(parents=True, exist_ok=True)
    if not command.exists():
        fd, temporary = tempfile.mkstemp(prefix=".nda-launcher-", dir=command.parent)
        try:
            os.fchmod(fd, 0o755)
            with os.fdopen(fd, "wb") as stream:
                stream.write(shim)
            os.link(temporary, command)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    print(f"Installed: {command}")
    print("Run: nda-harness setup")
    if str(command.parent) not in os.environ.get("PATH", "").split(os.pathsep):
        print(f"Use {command} directly, or add {command.parent} to your PATH. No shell startup files were changed.")


def main():
    parser = argparse.ArgumentParser(description="Install the bundled CLI, with no pip, virtual environment, admin access or downloads.")
    parser.add_argument("--prefix", type=Path, default=Path.home() / ".local", help="Install prefix (default: ~/.local)")
    args = parser.parse_args()
    if sys.version_info < (3, 9):
        print("Python 3.9+ is required.", file=sys.stderr)
        return 2
    try:
        install(Path(__file__).resolve().parents[1], args.prefix)
        return 0
    except (ValueError, OSError):
        print("Installation failed: conflicting/modified destination or filesystem permissions. Choose another --prefix or reconcile the existing bundle.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
