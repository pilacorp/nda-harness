"""Pinned, checksum-verified RTK installation; no custom command rewriting."""
import io
from pathlib import Path
import shutil
import subprocess
import tarfile
import urllib.error
import urllib.request
from .files import Conflict, digest


RTK_VERSION = "0.37.2"
RTK_URL = "https://github.com/rtk-ai/rtk/releases/download/v0.37.2/rtk-aarch64-apple-darwin.tar.gz"
ARCHIVE_SHA256 = "99e20a59847dedbb64032a3f7985f2fe959fcb9674d8eaf940fc58a189e27eca"
BINARY_SHA256 = "fb212aaa57018cff146a9053810b310845e477b4a1f789d38b4cf2908bb5c5dd"
OBSERVED_HOMEBREW_SHA256 = "33f8ba7f298ded5c88b5cc805267f03036fdf15731d3db9fa1f49ae98a6d6f53"
EXISTING_BINARY_VERSIONS = {
    BINARY_SHA256: RTK_VERSION,
    OBSERVED_HOMEBREW_SHA256: RTK_VERSION,
    "52b2a4a68e9a1f3c7880ddafea6cd590f0582e67324fe89ea41aaec83e7e9b58": "0.40.0",
}


def locate(home):
    found = shutil.which("rtk")
    if found:
        return Path(found)
    local = home / ".nda-harness/bin/rtk"
    return local if local.is_file() else None


def identity(executable):
    try:
        version = EXISTING_BINARY_VERSIONS.get(digest(executable.read_bytes()))
        if version is None:
            return False
        run = subprocess.run([str(executable), "--version"], capture_output=True, text=True, timeout=10)
        return run.returncode == 0 and run.stdout.strip() == "rtk " + version
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
            raise Conflict("Existing RTK executable is incompatible or unrecognized. It was left unchanged; reconcile the pinned version/identity before setup.")
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
