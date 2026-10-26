"""Load the verified pure-Python wheel directly, without pip or a venv."""
import hashlib
from pathlib import Path
import sys


WHEEL = "tomlkit-0.13.3-py3-none-any.whl"
SHA256 = "c89c649d79ee40629a9fda55f8ace8c6a1b42deb912b2a8fd8d942ddadb606b0"


def load():
    wheel = Path(__file__).resolve().parents[2] / "vendor" / WHEEL
    try:
        if wheel.is_symlink() or hashlib.sha256(wheel.read_bytes()).hexdigest() != SHA256:
            raise ValueError()
    except (OSError, ValueError):
        print("CLI dependency bundle is missing or modified; reinstall NDA Harness from an intact checkout.", file=sys.stderr)
        raise SystemExit(2) from None
    location = str(wheel)
    if location not in sys.path:
        sys.path.insert(0, location)
