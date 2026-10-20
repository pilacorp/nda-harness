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

Memory states: disabled (not opted in/no endpoint), awaiting authorization (user opted
in but native authentication incomplete), connected (native authenticated tool
discovery succeeds), unavailable (previously enabled but connection fails). The helper
cannot observe credential state and reports authorization/diagnostic pending rather
than guessing. Never verify by recalling, retaining or creating a bank.

Use the native Hindsight detail row to authenticate/re-authenticate. For disconnect,
disable its MCP connection in the client, use native logout/disconnect when available,
and revoke access in Hindsight if client logout is unavailable. Do not delete or read
host credential files. Core remains usable with memory disconnected.
