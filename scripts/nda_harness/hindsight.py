"""Optional personal Hindsight connections; credentials never enter project assets."""
import getpass
import ipaddress
import json
import subprocess
import sys
from urllib.parse import urlsplit
import warnings

from .adapters import REGISTRY
from .files import Conflict, digest, guard_path, json_bytes, read
from .prompts import select_options

NAME = "nda-harness-hindsight"
TAG = "mcp-" + NAME


def endpoint_value(raw):
    try:
        url = urlsplit(raw)
        local = url.hostname == "localhost"
        if url.hostname and not local:
            try:
                local = ipaddress.ip_address(url.hostname).is_loopback
            except ValueError:
                pass
        url.port  # Validate malformed ports before any request.
        if (not raw or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in raw)
                or not url.hostname or url.username is not None or url.password is not None
                or "?" in raw or "#" in raw or "\\" in raw
                or not (url.scheme == "https" or url.scheme == "http" and local)
                or url.path.rstrip("/").rsplit("/", 1)[-1] != "mcp"):
            raise ValueError()
    except ValueError:
        raise ValueError("Enter the multi-bank HTTPS MCP URL ending in /mcp/ without a bank name (HTTP is allowed only on loopback). No credentials, query or fragment.") from None
    return raw


def key_value(raw):
    if not raw or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in raw):
        raise ValueError("Hindsight API key must be nonempty and contain no whitespace or control characters.")
    return raw


def shared_state(home):
    return home / ".nda-harness/state/hindsight"


def load_shared(home):
    path = shared_state(home) / "receipt.json"
    raw = read(path)
    try:
        doc = json.loads(raw) if raw else {"schema_version": 1, "owned": {}}
        if doc.get("schema_version") != 1 or not isinstance(doc.get("owned"), dict):
            raise ValueError()
        if any(not key.endswith("::" + TAG) or not isinstance(value, str) for key, value in doc["owned"].items()):
            raise ValueError()
        return doc
    except (ValueError, TypeError, AttributeError):
        raise Conflict("Malformed private Hindsight receipt; reconcile before setup.") from None


def config_path(family, home):
    options = {"scope": "user", "project": None}
    return REGISTRY[family].entrypoints(options, home)[1]


def entry(path):
    raw = read(path)
    try:
        if path.suffix == ".toml":
            import tomlkit
            doc = tomlkit.parse(raw.decode()).unwrap() if raw else {}
            servers = doc.get("mcp_servers", {})
        else:
            doc = json.loads(raw) if raw else {}
            servers = doc.get("mcpServers", {})
        if not isinstance(servers, dict):
            raise ValueError()
        value = servers.get(NAME)
        if value is not None and not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, TypeError, AttributeError, UnicodeError):
        raise Conflict("Malformed Hindsight client configuration; reconcile locally.") from None


def desired(family, url, key):
    config = {"url": url, "http_headers" if family == "codex" else "headers": {"Authorization": "Bearer " + key}}
    if family == "claude":
        config["type"] = "http"
    return config


def check_destination(family, options, home):
    path = config_path(family, home)
    guard_path(path)
    ancestor = path.parent
    while not ancestor.exists():
        ancestor = ancestor.parent
    # Customized client homes must not put credentials in any Git checkout.
    try:
        run = subprocess.run(["git", "-C", str(ancestor), "rev-parse", "--show-toplevel"], capture_output=True, timeout=10)
        if run.returncode == 0:
            raise Conflict("Private Hindsight configuration must be outside Git checkouts; reconcile the client home.")
    except subprocess.TimeoutExpired:
        raise Conflict("Could not validate the private Hindsight destination; reconcile the client home.") from None
    project = options.get("project")
    if project:
        if path.resolve().is_relative_to(project):
            raise Conflict("Private Hindsight configuration must be outside the project; reconcile CODEX_HOME.")
        scoped = REGISTRY[family].entrypoints(options, home)[1]
        if entry(scoped) is not None:
            raise Conflict("A project Hindsight server shadows the private connection; reconcile it before setup.")
        if family == "claude":
            raw = read(path)
            try:
                local = (json.loads(raw) if raw else {}).get("projects", {}).get(str(project), {}).get("mcpServers", {})
                if not isinstance(local, dict):
                    raise ValueError()
            except (ValueError, TypeError, AttributeError):
                raise Conflict("Malformed Claude local configuration; reconcile locally.") from None
            if NAME in local:
                raise Conflict("A Claude local Hindsight server shadows the private connection; reconcile it before setup.")
    return path


def replacements(options, home):
    prior = load_shared(home)["owned"]
    memory = options["hindsight"]
    changed = []
    for family in memory["agents"]:
        path = check_destination(family, options, home)
        old = entry(path)
        if old is not None and old != desired(family, memory["url"], memory["key"]):
            if digest(json_bytes(old)) != prior.get(str(path) + "::" + TAG):
                raise Conflict("Conflicting user-owned Hindsight connection; reconcile it before setup.")
            changed.append(family)
    return changed


def collect_memory(options, home):
    if not sys.stdin.isatty():
        return
    if select_options("Set up Hindsight memory?", [("enable", "Enable"), ("skip", "Skip (preserve existing setup)")])[0] == "skip":
        return
    labels = {"codex": "Codex", "cursor": "Cursor", "claude": "Claude Code"}
    agents = select_options("Hindsight agents", [(name, labels[name]) for name in options["agents"]], multiple=True)
    while True:
        try:
            url = endpoint_value(input("Hindsight multi-bank MCP URL (https://host/mcp/): ").strip())
            break
        except ValueError as error:
            print(error, file=sys.stderr)
    while True:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", getpass.GetPassWarning)
                key = key_value(getpass.getpass("Personal Hindsight API key (hidden): "))
            break
        except getpass.GetPassWarning:
            raise ValueError("A terminal with hidden input is required for the Hindsight API key.") from None
        except ValueError as error:
            print(error, file=sys.stderr)
    options["hindsight"] = {"agents": agents, "url": url, "key": key}
    changed = replacements(options, home)
    if changed:
        decision = select_options("Replace managed Hindsight connection for " + ", ".join(changed) + "?", [
            ("keep", "Keep existing connection"), ("replace", "Replace (affects every project using it)")])[0]
        if decision == "keep":
            del options["hindsight"]
            return
    options["hindsight"]["replace"] = bool(changed)


def plan_connections(plan, options, home):
    memory = options.get("hindsight")
    if not memory:
        return
    endpoint_value(memory["url"])
    key_value(memory["key"])
    if not memory["agents"] or any(agent not in options["agents"] for agent in memory["agents"]):
        raise ValueError("Hindsight agents must be selected harness agents.")
    if replacements(options, home) and not memory.get("replace"):
        raise Conflict("Replacing a managed Hindsight connection requires explicit confirmation.")
    for family in memory["agents"]:
        path = check_destination(family, options, home)
        plan.mcp(path, "toml" if family == "codex" else "json", name=NAME,
                 desired=desired(family, memory["url"], memory["key"]), private=True)


def verify_connections(options, home, receipt, live=True):
    from .engine import result
    from .mcp import check_hindsight
    checks, probed = [], set()
    try:
        shared = load_shared(home)
        state = shared_state(home)
        if state.stat().st_mode & 0o077 or (state / "receipt.json").stat().st_mode & 0o077:
            raise ValueError()
        for family in receipt.get("memory_agents", []):
            if family not in options["agents"]:
                continue
            path = check_destination(family, options, home)
            config = entry(path)
            if config is None or path.stat().st_mode & 0o777 != 0o600:
                raise ValueError()
            if digest(json_bytes(config)) != shared["owned"].get(str(path) + "::" + TAG):
                raise ValueError()
            url = endpoint_value(config["url"])
            auth = config["http_headers" if family == "codex" else "headers"]["Authorization"]
            if not auth.startswith("Bearer "):
                raise ValueError()
            key_value(auth[7:])
            checks.append(result(family + "-hindsight-registration", "verified", "Private Hindsight MCP registration and permissions match shared ownership."))
            identity = (url, auth)
            if identity not in probed:
                checks.append(check_hindsight(url, auth) if live else result("hindsight-server", "awaiting_manual", "Live Hindsight diagnostic was not run."))
                probed.add(identity)
            checks.append(result(family + "-hindsight-session", "awaiting_manual", "Restart the client and confirm memory tools and scoped instructions load; Cursor User Rules require the documented paste step.", "manual required"))
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        checks.append(result("hindsight-registration", "failed", "Hindsight configuration, ownership, permissions or effective scope is invalid. For a bank-specific installation, rerun setup with the multi-bank /mcp/ URL and confirm replacement. Credentials were not retained in this report."))
    return checks
