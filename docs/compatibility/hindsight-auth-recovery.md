# Hindsight diagnostic classification and recovery

Implements the contract in [the approved specification](../../specs/hindsight-auth-recovery.md),
merged in [PR #19](https://github.com/pilacorp/nda-harness/pull/19), for
[issue #18](https://github.com/pilacorp/nda-harness/issues/18).

The helper only interprets supplied native evidence. It neither subscribes to
client events nor connects to an MCP server. Startup/prompt hooks inject static
guidance; their input is not an MCP lifecycle event bridge. Unknown diagnostics
stay pending. The core setup check remains independent of memory availability.

## Source and client boundaries

Documentation retrieved through Context7 on 2026-10-20:

| Client | Source | Supported interpretation |
| --- | --- | --- |
| Codex | [App-server notifications](https://learn.chatgpt.com/docs/app-server#api-overview-1) | Targeted failed `mcpServer/startupStatus/updated` with `failureReason: reauthenticationRequired`. |
| Codex | [MCP configuration/login](https://learn.chatgpt.com/docs/extend/mcp) | Native OAuth/tool discovery, manual login, and temporary configuration override. |
| Claude | [SDK MCP status](https://code.claude.com/docs/en/agent-sdk/mcp) and [native MCP controls](https://code.claude.com/docs/en/mcp) | Native server-status snapshot `needs-auth`, `pending`, `failed`, or `connected`; SDK status is not a Desktop SDK bridge. |
| Cursor | Installed agent catalog (`namespace` / `namespaceStatus`) and [Agent CLI](https://cursor.com/docs/cli/mcp) | `needsAuth` on `plugin-nda-harness-nda-harness-hindsight` or `nda-harness-hindsight` means authentication is required. `error` is unavailable; `loading` stays pending; `ready` or `connected` is discovery only. |

Cursor Cloud's `cursor.cloud_agent.mcp_auth_error` telemetry is not interpreted
as a local Cursor plugin signal. One client's authentication spelling is not
accepted as another client's event. Server names must match exactly.

## Verification scope

On 2026-10-20, `python3 -m unittest discover -s tests` passed all 171 tests.
Fresh Codex, Cursor and Claude release archives passed structural/hash validation;
committed Codex/Cursor packages passed reproducibility and integrity checks.
An independent source review reported no actionable findings. Native Codex
discovery returned 39 tools and the classifier reported `connected`.

Automated tests exercise pure classification, packaged CLI entrypoints for all
three clients, bounded and sanitized input, terminal stdin, disposable homes
without project setup/state writes, client-specific emitted guidance, unchanged
hook registrations, and reproducible packages. These are controlled native
diagnostic fixtures, not evidence of live client login or server reachability.

The earlier native OAuth experiment observed Codex bundled runtime
`0.163.0-alpha.10.2` and Cursor `3.25.9`; see
[its exact scope](hindsight-oauth-plugin-test.md). The current session separately
verified Codex token rotation and 39-tool discovery against the deployed server,
but that does not establish all recovery paths or automatic event delivery.

The specification's TC-09 live auth-required and outage scenarios in each
installed client remain manual checks. In particular, Cursor and Claude recovery
are not validated by a Codex result. Check command availability and actual server
identifiers in each installed version; do not extract host credentials for
testing or record private native errors.
