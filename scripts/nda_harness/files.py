"""Preflighted, atomic writes and hash-aware recovery."""
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import uuid


class Conflict(ValueError):
    pass


def digest(value):
    if isinstance(value, str):
        value = value.encode()
    return hashlib.sha256(value).hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def guard_path(path):
    for parent in [path, *path.parents]:
        if parent.is_symlink():
            raise Conflict(f"Destination symlink requires reconciliation: {parent}")
    if path.exists() and not path.is_file():
        raise Conflict(f"Expected a file: {path}")
    parent = path.parent
    while not parent.exists():
        parent = parent.parent
    if not os.access(parent, os.W_OK):
        raise Conflict(f"Unwritable destination: {parent}")


def read(path):
    guard_path(path)
    return path.read_bytes() if path.exists() else None


def atomic(path, content, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=".nda-", dir=path.parent)
    try:
        os.fchmod(fd, mode)
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


class Plan:
    def __init__(self, receipt):
        self.prior = receipt.get("owned", {})
        self.owned = dict(self.prior)
        self.writes = {}
        self.applied = []
        self.created_directories = []

    def own(self, path, tag, old, desired):
        key = str(path) + "::" + tag
        if old is not None and old != desired and digest(old) != self.prior.get(key):
            raise Conflict(f"Conflicting user-owned entry: {path} ({tag})")
        self.owned[key] = digest(desired)

    def write(self, path, desired, mode=0o644):
        old = read(path)
        if path in self.writes:
            raise Conflict(f"Overlapping planned writes: {path}")
        current_mode = stat.S_IMODE(path.stat().st_mode) if old is not None else mode
        if old != desired or (mode & 0o111 and not current_mode & 0o111):
            self.writes[path] = (old, desired, current_mode | (mode & 0o111))

    def file(self, path, desired, mode=0o644):
        old = read(path)
        self.own(path, "file", old, desired)
        self.write(path, desired, mode)

    def block(self, path, body):
        begin, end = "<!-- nda-harness:begin -->", "<!-- nda-harness:end -->"
        raw = read(path)
        try:
            old = raw.decode() if raw is not None else ""
        except UnicodeError:
            raise Conflict(f"Non-UTF-8 instructions: {path}") from None
        if old.count(begin) != old.count(end) or old.count(begin) > 1:
            raise Conflict(f"Malformed/duplicate harness markers: {path}")
        desired_block = begin + "\n" + body + "\n" + end
        prior_block = None
        if begin in old:
            start, finish = old.index(begin), old.index(end) + len(end)
            if finish <= start:
                raise Conflict(f"Malformed harness markers: {path}")
            prior_block = old[start:finish]
            result = old[:start] + desired_block + old[finish:]
        else:
            result = old + ("\n" if old and not old.endswith("\n") else "") + desired_block + "\n"
        self.own(path, "block", prior_block.encode() if prior_block else None, desired_block.encode())
        self.write(path, result.encode())

    def mcp(self, path, format, transport=None):
        # No literal credentials are generated or copied into receipts.
        name = "nda-harness-context7"
        desired = {"url": "https://mcp.context7.com/mcp"}
        if transport:
            desired["type"] = transport
        raw = read(path)
        try:
            if format == "toml":
                import tomlkit
                doc = tomlkit.parse(raw.decode() if raw else "")
                servers = doc.get("mcp_servers", {})
                old = servers.get(name)
                if old is not None:
                    old = old.unwrap()
            else:
                doc = json.loads(raw) if raw else {}
                if not isinstance(doc, dict):
                    raise ValueError()
                servers = doc.get("mcpServers", {})
                if not isinstance(servers, dict):
                    raise ValueError()
                old = servers.get(name)
        except (ValueError, TypeError, UnicodeError, AttributeError):
            raise Conflict(f"Malformed {format.upper()} configuration: {path}") from None
        self.own(path, "mcp", json_bytes(old) if old is not None else None, json_bytes(desired))
        if old == desired:
            return False
        if format == "toml":
            if "mcp_servers" not in doc:
                doc["mcp_servers"] = tomlkit.table()
            doc["mcp_servers"][name] = desired
            content = tomlkit.dumps(doc).encode()
        else:
            doc.setdefault("mcpServers", {})[name] = desired
            content = json_bytes(doc)
        self.write(path, content, 0o600)
        return old is None

    def apply(self, state):
        backup_dir = state / "backups" / uuid.uuid4().hex
        for path, (old, new, mode) in self.writes.items():
            if read(path) != old:
                raise Conflict(f"Destination changed after preflight: {path}")
            backup = None
            original_mode = stat.S_IMODE(path.stat().st_mode) if old is not None else mode
            if old is not None:
                backup = backup_dir / (digest(str(path)) + ".backup")
                atomic(backup, old)
                backup_dir.chmod(0o700)
            absent = [p for p in [path.parent, *path.parent.parents] if not p.exists()]
            atomic(path, new, mode)
            self.created_directories.extend(reversed(absent))
            self.applied.append({"path": str(path), "backup": str(backup) if backup else None,
                                 "written_sha256": digest(new), "old_mode": original_mode})

    def rollback(self, shared_paths=()):
        unresolved = []
        for item in reversed(self.applied):
            path = Path(item["path"])
            if path in shared_paths:
                continue
            if path.is_symlink() or not path.exists() or digest(path.read_bytes()) != item["written_sha256"]:
                unresolved.append(str(path))
                continue
            if item["backup"]:
                atomic(path, Path(item["backup"]).read_bytes(), item["old_mode"])
            else:
                path.unlink()
        for path in reversed(self.created_directories):
            try:
                path.rmdir()
            except OSError:
                pass
        return unresolved
