#!/usr/bin/env python3
"""Read-only MCP discovery through the desktop-bundled Codex runtime.

Run after installing the sample plugin and completing `codex mcp login hindsight`.
Does not read/export credentials, start an agent thread, or invoke a model.
"""
import json
import selectors
import subprocess
import sys
import time

CODEX = "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex"


def main():
    process = subprocess.Popen(
        [CODEX, "app-server", "--stdio"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    selector = selectors.DefaultSelector()
    selector.register(process.stdout, selectors.EVENT_READ)

    def send(message):
        process.stdin.write(json.dumps(message) + "\n")
        process.stdin.flush()

    def response(request_id):
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if not selector.select(timeout=1):
                continue
            line = process.stdout.readline()
            if not line:
                raise RuntimeError("Codex app-server exited before responding")
            message = json.loads(line)
            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError(str(message["error"]))
                return message["result"]
        raise TimeoutError("Codex MCP discovery timed out")

    try:
        send({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "nda_hindsight_oauth_probe", "version": "0.0.1"},
            "capabilities": {"experimentalApi": True},
        }})
        response(1)
        send({"method": "initialized", "params": {}})
        send({"id": 2, "method": "mcpServerStatus/list", "params": {
            "serverName": "hindsight", "detail": "toolsAndAuthOnly",
        }})
        result = response(2)
        servers = result.get("data", [])
        found = next((server for server in servers if server.get("name") == "hindsight"), None)
        if not found:
            raise RuntimeError("Installed test plugin's hindsight server was not discovered")
        tools = found.get("tools", {})
        names = list(tools) if isinstance(tools, dict) else [tool.get("name", "") for tool in tools]
        required = {"recall", "retain", "list_banks"}
        present = {name for name in required if any(tool == name or tool.endswith("__" + name) for tool in names)}
        summary = {
            "server": found["name"],
            "auth_status": found.get("authStatus"),
            "tool_count": len(tools),
            "required_tools_present": sorted(present),
            "passed": present == required,
        }
        print(json.dumps(summary, indent=2))
        return 0 if summary["passed"] else 1
    finally:
        selector.close()
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


if __name__ == "__main__":
    sys.exit(main())
