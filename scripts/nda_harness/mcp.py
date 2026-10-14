"""Bounded public MCP diagnostic. Never reads or prints client credentials."""
import json
import urllib.error
import urllib.request
from .engine import result


ENDPOINT = "https://mcp.context7.com/mcp"


def decode_response(raw):
    text = raw.decode().replace("\r\n", "\n")
    try:
        return json.loads(text)
    except ValueError:
        for event in text.split("\n\n"):
            payload = "\n".join(line[5:].strip() for line in event.splitlines() if line.startswith("data:"))
            if payload:
                value = json.loads(payload)
                if isinstance(value, dict) and "id" in value:
                    return value
    raise ValueError("Invalid MCP response")


def check_context7():
    session = None
    def call(method, params, identifier):
        nonlocal session
        headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "MCP-Protocol-Version": "2025-03-26"}
        if session:
            headers["Mcp-Session-Id"] = session
        body = {"jsonrpc": "2.0", "method": method, "params": params}
        if identifier is not None:
            body["id"] = identifier
        request = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(), headers=headers)
        with urllib.request.urlopen(request, timeout=10) as response:
            session = response.headers.get("Mcp-Session-Id", session)
            if identifier is None:
                response.read(1024)
                return {}
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError()
            value = decode_response(raw)
            if "error" in value or value.get("id") != identifier:
                raise ValueError()
            return value["result"]
    try:
        call("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "nda-harness-verification", "version": "0.1.0"}}, 1)
        call("notifications/initialized", {}, None)
        listing = call("tools/list", {}, 2)
        names = {t["name"] for t in listing["tools"]}
        resolver = next(n for n in ("resolve-library-id", "resolve_library_id") if n in names)
        query = next(n for n in ("query-docs", "query_docs") if n in names)
        resolved = call("tools/call", {"name": resolver, "arguments": {"libraryName": "Python", "query": "Python pathlib read_text public documentation"}}, 3)
        if resolved.get("isError"):
            raise ValueError()
        import re
        text = "\n".join(c.get("text", "") for c in resolved.get("content", []) if c.get("type") == "text")
        ids = re.findall(r"(?:library ID:|Library ID:)\s*(/[^\s`]+)", text)
        if not ids:
            raise ValueError()
        docs = call("tools/call", {"name": query, "arguments": {"libraryId": ids[0], "query": "Python pathlib Path.read_text encoding"}}, 4)
        if docs.get("isError") or not docs.get("content"):
            raise ValueError()
        return result("context7-server", "verified", "Public library resolution/documentation succeeded; target-client loading needs a fresh-session observation.")
    except urllib.error.HTTPError as error:
        status = "awaiting_manual" if error.code in (401, 403) else "failed"
        return result("context7-server", status, f"Public endpoint returned HTTP {error.code}; authenticate in the client or retry a rate/network failure locally.")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, StopIteration):
        return result("context7-server", "failed", "Public MCP timeout/network/interface failure; no raw response or credential was retained.")
