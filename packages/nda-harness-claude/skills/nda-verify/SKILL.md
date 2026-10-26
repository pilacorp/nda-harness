---
name: nda-verify
description: Inspect plugin and project readiness without repairs or memory side effects.
---

Run `${CLAUDE_PLUGIN_ROOT}/bin/nda-plugin verify --client claude --project <actual-root>`
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
`${CLAUDE_PLUGIN_ROOT}/bin/nda-plugin memory-status --client claude` operation. It neither
collects diagnostics nor initiates login. Never verify by recalling, retaining or
creating a bank.

Missing tools mean Hindsight is unavailable in this session; authentication is unverified without native evidence. Saved OAuth credentials and a hidden Authenticate button do not prove a working connection. Use the packaged memory-status helper with already available native diagnostic JSON, or leave the diagnostic pending. Existing hooks do not subscribe to MCP lifecycle events. Never initiate login automatically or read/edit credentials. Only for Claude, a matching native MCP status needs-auth confirms authentication is required; pending remains unresolved and failed means unavailable. Inspect Hindsight with /mcp; a supported SDK status snapshot may still be pending. Manual, user-triggered recovery: Use /mcp to inspect and authenticate Hindsight. If the installed CLI exposes mcp login, the user can run rtk proxy claude mcp login <name> with the name from native inventory. SDK status APIs do not launch browser OAuth or imply a Desktop SDK bridge.

Offer the invoking client's manual authentication action only when appropriate. For disconnect,
disable its MCP connection in the client, use native logout/disconnect when available,
and revoke access in Hindsight if client logout is unavailable. Do not delete or read
host credential files. Core remains usable with memory disconnected.
