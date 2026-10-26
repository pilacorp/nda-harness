---
name: nda-verify
description: Inspect plugin and project readiness without repairs or memory side effects.
---

Run `@ROOT@/bin/nda-plugin verify --client @CLIENT@ --project <actual-root>`
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
`@ROOT@/bin/nda-plugin memory-status --client @CLIENT@` operation. It neither
collects diagnostics nor initiates login. Never verify by recalling, retaining or
creating a bank.

@AUTH_GUIDANCE@

Offer the invoking client's manual authentication action only when appropriate. For disconnect,
disable its MCP connection in the client, use native logout/disconnect when available,
and revoke access in Hindsight if client logout is unavailable. Do not delete or read
host credential files. Core remains usable with memory disconnected.
