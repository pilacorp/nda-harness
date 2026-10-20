# Hindsight authentication reporting and manual recovery

Feature issue: https://github.com/pilacorp/nda-harness/issues/18
Issue updated at: 2026-10-20T07:13:35Z
Issue body SHA-256: cc1884da6baaa0fefc2204e49b7b6afdeea2e614dbe473146344aa6d74a92dbd
Consulted source revisions: repository `b31e72c1c7825051d106827da42657487bb0b7fd`; official client documentation retrieved through Context7 on 2026-10-20
Spec branch: codex/18-hindsight-auth-recovery

## Summary

NDA Harness sometimes tells users to authenticate because the agent cannot see
Hindsight tools. This can be misleading: the connection may have failed for a
different reason, or may still be starting. The proposed change reports what
the client's own diagnostic actually proves and gives the correct recovery
steps for that client.

Codex and Claude expose different authentication signals. Cursor's local plugin
interface has no equivalent callback established by this research, so its check
stays pending until the user or agent can inspect native status. The harness
will not manage tokens or start login automatically.

## Setup and daily use

No server or administrator configuration changes are needed. After the
implementation is reviewed and released, developers update their NDA Harness
plugin and reconnect the client if needed. Existing project banks and login
credentials stay in place.

During normal work, the agent uses available Hindsight tools. If they are
missing, it checks supported native diagnostics or reports that the connection
is unavailable and authentication is unverified. A confirmed sign-in problem
produces the invoking client's manual recovery instructions. The user completes
that login in the native client/browser; the harness never requests a token.

The proposed `memory-status` helper below is for interpreting already available
native diagnostics. It is not an authentication or connectivity probe.

## Outcome and boundaries

Task classification: behavior change.

An agent must distinguish an unavailable Hindsight connection from a confirmed
need to authenticate. Today `plugin/skills/hindsight-memory/SKILL.md`,
`plugin/skills/session-bootstrap/SKILL.md`, and the Cursor rule instruct the agent
to report awaiting authentication when tools are missing. Missing tools can also
mean a timeout, an outage, disabled tools, or a connection that has not finished
starting. Saved OAuth credentials and a hidden Authenticate button do not prove
successful authenticated MCP initialization.

The change supplies client-specific interpretation of supported diagnostics,
consistent agent instructions, and manual recovery guidance. It preserves the
existing memory-system selection, project bank identity, and optional-memory
fallback. Codex, Cursor, and Claude continue to own login, token storage,
refresh, rotation, logout, and their native UI.

Excluded: implementing OAuth or token refresh; reading or editing credential
files or Keychain; background polling, automatic browser login, new SDK
dependencies, a custom settings UI, and server-side Hindsight changes.

## Implementation

### Evidence and client boundaries

| Client | Supported evidence | Meaning and recovery |
| --- | --- | --- |
| Codex | `mcpServer/startupStatus/updated`, matching server `name`, `status: failed`, `failureReason: reauthenticationRequired` | Awaiting authentication; stored authorization could not be renewed. Offer the client's MCP sign-in action. |
| Codex | Native `mcpServerStatus/list` entry for the matching server with `authStatus: oAuth` and nonempty discovered `tools` | Connected for discovery only. No assertion that memory operations or later refresh succeeded. |
| Claude Code | Matching server snapshot from documented MCP status with `status: needs-auth` | Awaiting authentication; use `/mcp` to authenticate. |
| Claude Code | `status: connected`, `pending`, or `failed` in a matching native status snapshot | Connected, pending native diagnostic, or unavailable respectively. An initial pending status must not become an authentication verdict. |
| Cursor local | Native MCP settings/status and its authentication controls; CLI `agent mcp list`, `agent mcp list-tools`, and `agent mcp login` where installed | Inspect the client's actual diagnostic. With no supported machine-readable diagnostic, leave the classifier pending and tell the user where to check. |

Codex's event and `failureReason` are not interpreted by Claude or Cursor.
Claude's `needs-auth` spelling is not interpreted by Codex or Cursor. Cursor
Cloud's `cursor.cloud_agent.mcp_auth_error` telemetry is not a local-plugin
callback and is excluded. Documentation research did not establish an equivalent
local Cursor callback; do not invent one or parse unstable human-facing text.

### Read-only diagnostic classifier

Add a small shared classifier in `scripts/nda_harness/memory.py`, consumed by a
`memory-status` operation in the existing client-bound `nda-plugin` helper. The
helper accepts optional native diagnostic JSON on stdin, bounded to the existing
1 MB hook-input limit. Empty stdin is missing evidence; when stdin is a terminal,
report pending immediately instead of waiting for input. It does not connect to the server, read credentials,
perform memory operations, install SDKs, or run login commands. It requires no
new event subscription or client hook. Agents invoke it only when native
diagnostic data is available; otherwise they report the pending state.

Accepted input shapes are a complete Codex notification with `method` and
`params`, a Codex native inventory entry, or a Claude native server-status
snapshot. The configured target is `SYSTEMS['hindsight']['server']`, currently
`nda-harness-hindsight`. Exact server-name matching is required. No user-defined
server override or arbitrary endpoint is added. Cursor has no structured parser
in this change; absent or unsupported diagnostics remain pending.

Return only reviewed static fields: `schema_version`, `client`, `server`,
`memory_state`, `diagnostic`, and `next_action`. Never copy error text, URLs,
prompt content, tokens, or unknown input fields into output. Native diagnostic
input and classifier output remain ordinary tool data, not privileged hook
instructions or persistent state.

| Input/result | `memory_state` | `diagnostic` |
| --- | --- | --- |
| Package has no Hindsight endpoint | `disabled` | `endpoint_not_packaged` |
| Targeted Codex reauthentication failure or Claude `needs-auth` | `awaiting_authentication` | `reauthentication_required` or `authentication_required` |
| Supported successful discovery/status | `connected` | `native_connection_observed` |
| Targeted generic startup/status failure | `unavailable` | `native_connection_failed` |
| No diagnostic, unsupported client signal, unknown/mismatched server or pending status | `pending_native_diagnostic` | `native_diagnostic_pending` |
| Invalid JSON, oversized stdin, or a non-object input | `pending_native_diagnostic` | `invalid_native_diagnostic` |

Classification is observational. A failed connection or invalid diagnostic must
not block core workflow. Valid reports return exit 0, including unavailable and
pending memory. Invalid diagnostic input returns exit 2 with the static pending
report and no raw input. Existing package/configuration errors retain their
current sanitized failure behavior. Do not persist a connection verdict across
sessions or claim that one observation guarantees future authorization.

For the same server, explicit failure takes precedence over any tools included
in that failed notification. An `authStatus: oAuth` entry without discovered
tools is pending. An arbitrary HTTP 401/403 or the word "unauthorized" does not
by itself prove that refresh failed; preserve the error as unavailable and ask
for the native diagnostic rather than inferring token lifecycle state.

### Instructions and manual recovery

Update shared memory/session instructions and verification guidance. Generate
only the invoking client's auth guidance into each package, including the
Cursor always-applied rule. Runtime startup/prompt guidance uses the same
client-specific source. Keep generic system-selection fallback unchanged.

When tools are absent, say Hindsight is unavailable in this session and its
authentication status is unverified unless native evidence establishes more.
Tool availability permits normal memory use but must not be treated as proof of
which login UI the user used. Continue using client default memory only when it
actually exists; do not fabricate saves or later synchronization.

Manual recovery is user-triggered. Instructions may offer the following paths,
but neither hooks nor `memory-status` execute them:

- Codex: use its native MCP OAuth action. If the UI hides sign-in, document
  `codex -c 'mcp_servers.nda-harness-hindsight.url="https://hindsight-api.pila.vn/mcp/"' mcp login nda-harness-hindsight`.
  The override is invocation-local and uses the same server identity. Use the
  actual installed executable, not a machine-specific hard-coded application
  path. Reconnect/restart the client afterward where needed.
- Cursor: use the Hindsight MCP authentication control. When Cursor Agent CLI
  and that server registration are available, `agent mcp login <identifier>` is
  an alternative. Obtain the actual identifier from native configuration/status;
  do not infer a plugin-prefixed identifier or promise cross-surface credentials.
- Claude Code: use `/mcp` to inspect/authenticate the Hindsight server. Document
  shell `claude mcp login <name>` only for versions that expose it, with the name
  verified by native inventory. The SDK's status APIs do not themselves launch
  interactive OAuth; do not claim the Desktop plugin has an embedded SDK bridge.

Do not recommend deleting credential files, uninstalling the plugin, or clearing
unrelated clients. Explain that devices authenticate independently and existing
credentials without expiry metadata may need one refresh or reauthentication.

### Affected files and compatibility

- `scripts/nda_harness/memory.py`: shared classifier and client recovery guidance.
- `scripts/nda_harness/plugin_runtime.py`: bounded, sanitized read-only operation
  and client-specific startup/prompt guidance.
- `scripts/nda_harness/plugin_build.py`: render client guidance into generated
  skills/rules without registering unsupported native callbacks.
- `plugin/skills/hindsight-memory/SKILL.md`, `session-bootstrap/SKILL.md`,
  `nda-verify/SKILL.md`, and `plugin/rules/nda-harness.mdc`: consistent evidence
  rules and recovery instructions.
- `INSTALLATION.md` and compatibility documentation: command examples, client
  boundaries, supported versions, and unresolved manual checks.
- Focused tests plus regenerated committed Codex/Cursor packages and their
  release hashes. Validate a freshly built Claude package as release output.

No existing command is removed. `verify` remains read-only and does not invent
observed native status from package configuration. No project-profile migration,
OAuth-header change, memory-bank change, or Hindsight deployment is required.

## Acceptance mapping

| ID | Issue criterion | Expected behavior |
| --- | --- | --- |
| AC-01 | 1 | Missing tools, an OAuth credential, or a missing UI button does not prove authentication state. |
| AC-02 | 2 | Codex and Claude signals are restricted to their client and the configured Hindsight server. |
| AC-03 | 3 | Unknown, pending, invalid, and unsupported diagnostics have honest pending/unavailable reports. |
| AC-04 | 4 | Each generated package supplies its own manual recovery path without executing it. |
| AC-05 | 5 | Memory failures leave core workflow, credential ownership, and bank identity intact. |
| AC-06 | 6 | Classifier, CLI boundary, sanitization, and generated package coverage pass before implementation ships. |

## Concrete test cases

These are planned tests, not executed implementation evidence.

| ID | Setup/input | Action | Expected result | Layer / acceptance IDs |
| --- | --- | --- | --- | --- |
| TC-01 | Targeted Codex failed startup with reauthentication reason | Classify complete notification | Awaiting authentication with Codex recovery | unit; AC-02, AC-04 |
| TC-02 | Codex event supplied to Claude/Cursor; unrelated server supplied to Codex | Classify | Pending; no borrowed signal or unrelated-server verdict | unit; AC-02, AC-03 |
| TC-03 | Claude snapshots `needs-auth`, `pending`, `failed`, `connected` | Classify each; supply `needs-auth` to other clients | Correct Claude states; other clients remain pending | unit; AC-02, AC-03 |
| TC-04 | Missing tools; OAuth status without tools; unknown or empty diagnostic | Classify | Pending; never falsely connected or awaiting authentication | unit; AC-01, AC-03 |
| TC-05 | Matching Codex native discovery with OAuth and tools; generic failure | Classify; include misleading tools in failed event | Connected only for successful discovery; failed remains unavailable | unit; AC-01, AC-03 |
| TC-06 | Malformed JSON, non-object JSON, input above limit, and private-looking fields/error text | Run packaged helper | Static pending report, exit 2 for invalid input, no raw/private content in stdout or stderr | CLI integration; AC-03, AC-05 |
| TC-07 | No Hindsight endpoint, unknown diagnostics, failing connection | Run helper in disposable home without network | Correct disabled/pending/unavailable report; no login, credential access, memory call, subprocess, or profile writes | integration; AC-03, AC-05 |
| TC-08 | Build Codex, Cursor, Claude packages and invoke startup/prompt consumers | Exercise emitted instructions and diagnostic CLI | Only client-appropriate recovery; no unsupported hook event; package hashes validate | package integration; AC-04, AC-06 |
| TC-09 | Explicit auth-required condition and a separate network outage in each installed client | Inspect native state, use offered recovery, discover tools | Clear distinction, successful recovery or honest pending check; no raw credentials retained | manual; AC-01–AC-05 |

Implement unit Red → Green → Refactor. Run the repository test suite and package
validation after focused tests. Record unavailable live-client tests separately;
the Cursor and Claude manual paths are not validated by a Codex-only result.

## Hook changes

No new native hook registrations or event subscriptions. Existing startup/prompt
hooks inject reviewed static client guidance only; native status payloads are
never promoted to privileged instructions. `memory-status` is explicitly
invoked when supported native diagnostic data is available. If the host cannot
expose it, leave the check pending and use the native UI/manual fallback.

## Documentation and rollout/recovery

Release rebuilt packages after implementation review and passing checks. Users
update the package and reconnect the client as appropriate. The server-side
expiry fix is already separate; this change only improves local reporting and
recovery. Roll back by reinstalling the previous package; no credential,
database, or profile migration must be reversed.

## Decisions and risks

- A startup hook is not a subscriber to Codex app-server notifications. This
  spec deliberately supplies an explicit classifier rather than claiming an
  automatic bridge that does not exist.
- No Cursor local callback was established. A future supported interface needs
  separate source verification and review before parsing it.
- Claude SDK status documentation establishes status semantics, not automatic
  availability of SDK objects inside a Desktop plugin.
- Client command availability and plugin server identifiers vary by version;
  show verified names and supported alternatives instead of guessing.
- Human review remains required. User authorization to create this spec PR is
  not implementation approval; the existing PR #14 is not claimed as approval
  for the changed local plugin spec or this new behavior.

## Sources

Retrieved through Context7 on 2026-10-20:

- [Codex app-server auth/status notifications](https://learn.chatgpt.com/docs/app-server#api-overview-1).
- [Codex native MCP configuration and login](https://learn.chatgpt.com/docs/extend/mcp).
- [Claude Agent SDK MCP status and authentication boundaries](https://code.claude.com/docs/en/agent-sdk/mcp).
- [Claude Code MCP authentication](https://code.claude.com/docs/en/mcp).
- [Cursor local MCP setup](https://cursor.com/docs/mcp) and [CLI commands](https://cursor.com/docs/cli/mcp).
- [Cursor Cloud telemetry](https://cursor.com/docs/enterprise/opentelemetry-export/wire), explicitly excluded from local-plugin handling.

## Review and implementation handoff

Spec PR: linked from the issue and PR body after publication.
Review reference: unset; awaiting human review.
Merge reference/revision: unset; unmerged.
Local spec matches merged reviewed version: not established before spec merge.
Next action: human review and merge of this spec-only PR, then prepare an
implementation task against the exact reviewed revision on the same feature
branch. The implementation PR closes #18 after accepted implementation.

The issue owns intent. This document does not grant approval; behavior-change
implementation requires verified review/merge and matching local content.
