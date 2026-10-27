"""Pinned, checksum-verified RTK installation; no custom command rewriting."""
import io
import re
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.error
import urllib.request
from .files import Conflict, digest


RTK_MINIMUM = (0, 40, 0)
RTK_VERSION = "0.40.0"
RTK_URL = "https://github.com/rtk-ai/rtk/releases/download/v0.40.0/rtk-aarch64-apple-darwin.tar.gz"
ARCHIVE_SHA256 = "60c2c325b4edf0367cfa9716ac2e2c888abcd065eff45d01510da6561ab82e3c"
BINARY_SHA256 = "aa84021875b75e72ccf73adea524e3cba0b10e9e5097359b6dadf74e6500f3eb"
_VERSION = re.compile(r"rtk ([0-9]+)\.([0-9]+)\.([0-9]+)")


def locate(home):
    found = shutil.which("rtk")
    if found:
        return Path(found)
    local = home / ".nda-harness/bin/rtk"
    return local if local.is_file() else None


def reported_version(text):
    match = _VERSION.fullmatch(text.strip())
    if not match:
        return None
    return tuple(int(part) for part in match.groups())


def identity(executable):
    try:
        run = subprocess.run([str(executable), "--version"], capture_output=True, text=True, timeout=10)
        version = reported_version(run.stdout) if run.returncode == 0 else None
        return version is not None and version >= RTK_MINIMUM
    except (OSError, subprocess.TimeoutExpired):
        return False


def unpack(raw):
    if digest(raw) != ARCHIVE_SHA256:
        raise Conflict("Official RTK archive checksum mismatch; no executable was installed.")
    try:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as archive:
            members = archive.getmembers()
            if len(members) != 1 or members[0].name != "rtk" or not members[0].isfile() or members[0].size > 20_000_000:
                raise ValueError()
            content = archive.extractfile(members[0]).read()
    except (tarfile.TarError, ValueError, AttributeError):
        raise Conflict("Invalid RTK release archive; no executable was installed.") from None
    if digest(content) != BINARY_SHA256:
        raise Conflict("RTK executable checksum mismatch; no executable was installed.")
    return content


def prepare(plan, home):
    executable = locate(home)
    if executable:
        if not identity(executable):
            raise Conflict("Existing RTK must be version 0.40.0 or newer. It was left unchanged.")
        return executable
    try:
        with urllib.request.urlopen(RTK_URL, timeout=30) as response:
            raw = response.read(10_000_001)
        if len(raw) > 10_000_000:
            raise ValueError()
    except (OSError, ValueError, urllib.error.URLError):
        raise OSError("Pinned RTK download failed; retry network prerequisites") from None
    destination = home / ".nda-harness/bin/rtk"
    plan.file(destination, unpack(raw), 0o755)
    return destination
