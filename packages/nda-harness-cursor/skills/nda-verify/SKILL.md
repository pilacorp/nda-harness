---
name: nda-verify
description: Inspect plugin and project readiness without repairs or memory side effects.
---

Run `${CURSOR_PLUGIN_ROOT}/bin/nda-plugin verify --client cursor --project <actual-root>`
from this plugin's resolved path. Verification reads configuration and asset hashes;
it does not run configured tests, install dependencies, alter hooks, log in, export
credentials, or call memory read/write tools. Report pending checks honestly.

Core readiness means local package/dependency/project protection checks passed.
It is distinct from observed native hook execution, Context7 connection, and memory
availability. Inspect the invoking client's native MCP diagnostics for Context7 and
Hindsight. An unauthenticated request is not proof that the client's OAuth works.
Do not retrieve credentials to probe HTTP. If the client has no supported diagnostic,
report pending. Record only sanitized outcomes, counts and tool names in evidence.

Memory states: disabled (no endpoint), awaiting authentication (confirmed native
auth evidence), connected (native authenticated discovery/status succeeds),
unavailable (connection fails), or pending native diagnostic (missing/unsupported
evidence). `verify` cannot observe credential state and leaves native checks pending.
Interpret already available native diagnostic JSON with the explicit read-only
`${CURSOR_PLUGIN_ROOT}/bin/nda-plugin memory-status --client cursor` operation. It neither
collects diagnostics nor initiates login. Never verify by recalling, retaining or
creating a bank.

Missing tools mean Hindsight is unavailable in this session; authentication is unverified without native evidence. Saved OAuth credentials and a hidden Authenticate button do not prove a working connection. Use the packaged memory-status helper with already available native diagnostic JSON, or leave the diagnostic pending. Existing hooks do not subscribe to MCP lifecycle events. Never initiate login automatically or read/edit credentials. Do not interpret another client's auth signals or Cursor Cloud telemetry as a local Cursor callback. Inspect Hindsight in Cursor MCP settings; use agent mcp list where the CLI is installed. No local structured auth callback is established. Manual, user-triggered recovery: Use the Hindsight native authentication control. With Cursor Agent CLI and the server registered there, the user can run rtk proxy agent mcp login <identifier>; verify the identifier in native inventory. Do not assume shared credentials across Cursor surfaces.

Offer the invoking client's manual authentication action only when appropriate. For disconnect,
disable its MCP connection in the client, use native logout/disconnect when available,
and revoke access in Hindsight if client logout is unavailable. Do not delete or read
host credential files. Core remains usable with memory disconnected.
