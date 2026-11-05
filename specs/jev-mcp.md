# Developer spec: use Jev through a local MCP server

Feature issue: pending publication; related issues [#16](https://github.com/pilacorp/nda-harness/issues/16) and [#36](https://github.com/pilacorp/nda-harness/issues/36)
Issue updated at: pending
Issue body SHA-256: pending
Consulted source revision: `337109c6b06535e5bddff2f4ca8e2c8b425b4304` on `dev`
Spec branch: draft in the current checkout
Status: runtime implementation in progress, explicitly authorized in chat on 2026-11-04; native-client acceptance and release pending

## Summary

Developers currently switch Codex to Full Access to use Jev. There are two
separate barriers: shell network restrictions and the harness's own blanket
sandbox refusal. `in_sandbox()` treats any nonempty `CODEX_SANDBOX` as a refusal,
before the selector attempts to read a key or call OpenRouter. Selection also
writes private cache and session state outside the project.

Package a dedicated local stdio MCP server named `nda-harness-jev`. The coding
agent calls its tools while ordinary shell commands keep the client's existing
sandbox. The trusted server reads the existing personal key, uses the existing
selection engine and fixed OpenRouter endpoint, and returns sanitized results.
It is a privileged local component with a deliberately small interface.

The required outcome for Codex, Cursor, and Claude is normal skill selection
through MCP while ordinary agent shell commands retain their existing sandbox
or permission restrictions. Daily selection must not require switching Codex
to Full Access, enabling an equivalent unrestricted mode in Cursor or Claude,
or approving an escaped shell command for every selection. MCP installation,
enablement, and tool permissions still belong
to the client and its administrator. A managed policy can deny the server; the
harness must report that limitation rather than promise universal access.

This proposal amends the transport and daily agent-use requirements in
`jev-skill-selection.md` and the blanket outside-sandbox requirement in
`openrouter-credential.md`. It preserves `jev-classification-boundaries.md`, the
file credential contract, and all selection and approval rules except where
explicitly amended below. These amendments take effect with implementation;
the current released shell flow remains unchanged until then.

## Setup and daily use

1. Install or update NDA Harness through the existing client package mechanism.
   Enable/trust the new local MCP server using that client's normal controls.
   No separate daemon, port, account, or hosted service is required.
2. Reuse `~/.nda-harness/skill-selection/openrouter-key`. For first setup,
   replacement, removal, or Keychain migration, use the existing hidden prompt
   in a normal local terminal. The MCP server never accepts a key as input.
3. Restart or reload the client as needed for MCP discovery. Offline
   `selection_verify` checks the package and key presence; it makes no paid call.
4. For an assignment, the coordinator calls `select_skills` with bounded task
   JSON, explicit project root, and session id. It reads catalog metadata first,
   without preloading specialist bodies.
5. On `uncertain_decision`, the coordinator asks the user which uncertain skills
   to include, then sends those decisions to `record_selection`. The server
   records the answer; it does not elicit or invent human approval itself.
6. Call `load_selected_skills` with the same assignment and session. Only this
   tool returns selected bodies. Continue the normal workflow approval gates.

When no key exists, preserve the `local_agent` question/answer flow through
`select_skills`. An unreadable key is `credential_unavailable`, not a missing
key. An unavailable MCP server is not evidence that a key is missing.

## Outcome and boundaries

Task classification: behavior change / feature, not a bug-fix exception.

Ship the shared adapter and registrations for Codex, Cursor, and Claude. Each
client receives its own fixed client identity. Preserve Python 3.9+ and existing
offline, relocatable package installation. Native behavior must be verified in
each client before claiming support there. All three clients are required
release targets, not optional follow-up integrations. They use the same four
tools, selection semantics, credential file, cache, failure behavior, and
terminal-only credential administration; only host registration and launcher
paths differ. Claude hosted archives are included in this requirement.

Excluded: changing any client's global permission settings or network allowlists; removing
the shell sandbox; a hosted Jev gateway; credential administration over MCP;
new models, catalog questions, thresholds, automatic retries, or specialists;
changes to Context7, Hindsight, NDA RAG, or mandatory workflow approval.

## Implementation

### Server lifecycle and packaging

Add a proposed launcher operation:

```text
<installed-plugin>/bin/nda-plugin selection-mcp --client <fixed-client>
```

The client launches it as an MCP stdio child process. It resolves code, catalog,
and release hashes from its own installed package, never its current directory
or a caller-supplied package root. Derive private state from the same OS-user
home source used by the current runtime. Reuse the existing credential store.
Use one synchronous request at a time per process and the existing interprocess
cache locks across clients. EOF ends the process without deleting credentials
or completed cache records. No background listener or subprocess per tool call.

Implement the small tools-only adapter with Python's standard library, reusing
the current engine. Do not introduce an unbundled SDK, runtime package download,
or higher Python minimum. Protocol conformance is part of acceptance, not an
assumption based on a successful unit function call.

Generate the MCP entry from `scripts/nda_harness/plugin_build.py`:

| Client | File | Command | Args |
| --- | --- | --- | --- |
| Codex | `.mcp.json` | `${PLUGIN_ROOT}/bin/nda-plugin` | `selection-mcp`, `--client`, `codex` |
| Cursor | `mcp.json` | `${CURSOR_PLUGIN_ROOT}/bin/nda-plugin` | `selection-mcp`, `--client`, `cursor` |
| Claude | `.mcp.json` | `${CLAUDE_PLUGIN_ROOT}/bin/nda-plugin` | `selection-mcp`, `--client`, `claude` |

Use server id `nda-harness-jev`; a human label may say Jev skill selection.
Codex/Claude entries declare `type: stdio`; Cursor uses its native command/args
shape. Preserve existing HTTP entries. Replace the current builder loop that
assigns `type: http` to every server with transport-specific construction.
Claude hosted archives must relocate this command to `scripts/nda-plugin`
through the existing relocation mechanism. Verify root expansion, executable
permissions, paths containing spaces, and installed-package relocation in the
actual clients. Do not hand-edit generated packages.

### Protocol contract

Support MCP protocol revision `2025-06-18` as the initial baseline; advertise
only tools, with a stable list. On initialize, use that revision if the caller
requests an unsupported version, allowing the client to disconnect according to
MCP version negotiation. Any additional supported revision requires protocol
fixtures and native-client evidence; do not merely echo arbitrary versions.

Use newline-delimited UTF-8 JSON-RPC 2.0 on stdio. Stdout contains protocol
messages only. Support initialize, notifications/initialized, ping, tools/list,
and tools/call. Reject tool requests before initialization. Unknown request
methods and invalid parameters return JSON-RPC errors; notifications receive
no response. Do not advertise resources, prompts, elicitation, sampling, or
logging subscriptions. Ignore unsupported notifications. No JSON-RPC batches.

Read at most 128 KiB per input line; enforce existing task/answer limits before
engine work. Invalid JSON returns a sanitized parse error. Oversized lines
terminate the process with a sanitized stderr diagnostic, without processing
the oversized request. A response line is capped at 2 MiB, including loaded
bodies; overflow returns `response_too_large` without a partial body. Before
release, verify that the largest valid shipped selection fits this bound.

Each tool has an object inputSchema with additionalProperties false. Return
one text content block containing the existing JSON result; preserve status,
diagnostic, next action, provenance, and `implementation_authorized: false`.
Do not require structuredContent, keeping one response representation. An
expected workflow state such as `local_agent` or `uncertain_decision` is a
successful tool response. A blocked engine result sets isError true and retains
its sanitized diagnostic. Unexpected exceptions produce `internal_error`,
without a traceback, local path, task content, or provider body in stderr.

### Tool interface

All tools reject unknown fields and wrong types. Project is an explicit absolute
path to an existing directory, canonicalized for cache partitioning; it grants
no arbitrary file access. Session uses the existing session-id validator.

| Tool | Arguments | Behavior |
| --- | --- | --- |
| `select_skills` | required `project`, `session`, `task`; optional boolean `refresh` (default false), object `answers` | `task` is the unchanged schema-1 assignment object. `answers` uses the current local-agent answer validator and is accepted only in the existing missing-key flow. Reuse existing cache and fixed Jev transport. Never return bodies. |
| `record_selection` | required `project`, `session`, `task`, `decisions` | Preserve the existing exact uncertain-id/boolean validation and pending-decision checks. No provider call. |
| `load_selected_skills` | required `project`, `session`, `task` | Preserve generation, task fingerprint, release/catalog/body integrity, and ready-pointer checks. Return only selected bodies, never scan unrelated files. No provider call. |
| `selection_verify` | optional boolean `live` (default false) | Reuse package and credential verification. `live: true` makes only the existing synthetic paid check; task data is not an argument. |

Arguments contain JSON values directly. No `request_file`, `answers_file`,
credential path, home override, catalog root, endpoint, model override, command,
or arbitrary file-read tool is exposed. Tool discovery documents paid effects
of selection cache misses, refresh, and explicit live verification. Selection
tools that write cache must not advertise readOnlyHint true; annotations do not
replace enforcement. Tool descriptions instruct agents to keep live checks
explicit and preserve user confirmation for uncertain skills.

### Trust boundary and engine reuse

The local server, not the sandboxed shell, owns outbound HTTPS and private state.
It always uses `https://openrouter.ai/api/alpha/decisions`, the current model
pin, current request limits, 15-second provider timeout, no redirects, and no
automatic retries. Credentials stay in the mode-0600 file under its mode-0700
directory; retain symlink rejection, atomic writes, and generation rotation.
No request text, key, bearer header, raw provider response, or selected body is
logged. Read bounded task input as data, never as instructions or executable code.

Refactor the reusable selection engine so policy at the entry boundary determines
whether it may run. Direct shell operations retain their current sandbox refusal.
The registered MCP entry uses the engine in its trusted server process, without
accepting an agent-controlled `trusted` flag or unsetting `CODEX_SANDBOX` globally.
The MCP process may inherit environment markers; a marker alone must not reject
this supported entry path. Actual OS denial of key/cache/network access remains
a sanitized error. This separation does not grant capabilities the host denies.

Preserve schema 2 catalog rules `jev-specialists-v2`, .20/.80 thresholds, empty
selection, seven-day cache, cache identity and invalidation, local-agent behavior,
selection provenance, body-integrity checks, and locks. Switching between MCP
and CLI for the same package must reuse valid state; do not add transport to the
cache identity or rotate credentials for migration. Normal release-revision
invalidation still applies when the new package is installed. Concurrent MCP/CLI operations
must share the same cache semantics and never corrupt a pending or ready record.

### Failure and recovery

| Condition | Required behavior |
| --- | --- |
| MCP disabled, absent, startup failure, denied tool call | Coordinator reports `jev_mcp_unavailable` as a routing diagnostic and pauses dependent specialist work. Do not infer credential absence, change permissions, start setup, or silently escape to shell. |
| Key missing | Existing `local_agent` flow; no paid request or setup prompt. |
| Key inaccessible, state unwritable, invalid package | Block with sanitized credential/state/integrity diagnostic; no broad permission request or automatic fallback. |
| Auth, credit, rate, network, malformed provider failure | Preserve current sanitized engine diagnostics and recovery; no automatic retry. |
| Client timeout/disconnect during a call | Result delivery may be unknown. On reconnect reuse the same task/session; inspect existing cache through normal selection. Do not force refresh. A crash before caching can require another paid request; exactly-once billing is not promised. |
| Old package or direct sandboxed CLI | Existing `sandbox_rerun` remains valid for that shell path. Guidance distinguishes it from the proposed MCP path. |

## Acceptance mapping

| ID | Criterion | Observable result |
| --- | --- | --- |
| AC-01 | Same MCP behavior with existing restrictions in all clients | Codex, Cursor, and Claude each complete offline verification, selection, uncertain-decision recording if needed, and loading through MCP without Full Access, an equivalent unrestricted mode, or shell escalation; ordinary shell restrictions remain enforced. |
| AC-02 | Small privileged interface | Exactly four tools, strict arguments, no secret/configuration/file-read/command interface; protocol stdout only. |
| AC-03 | Selection parity | MCP and approved CLI fixtures return equivalent decisions, provenance, cache hits/invalidation and load checks. |
| AC-04 | Credential and network boundaries | Existing shared key reused; no leaks, redirects, extra origins, retries, or implicit paid verification. |
| AC-05 | Correct failures | Missing key, inaccessible key, uncertain scores, unavailable MCP, provider failure, and interrupted calls follow the recovery table. |
| AC-06 | Relocatable packages | Three generated clients and Claude hosted archive register the correct local command while preserving all existing HTTP servers. |
| AC-07 | Workflow and rollout | Instructions route agent selection through MCP, terminal setup remains intact, mandatory gates remain in force, and native verification evidence is recorded per client. |

## Concrete test cases

Acceptance cases are defined below. Executed automated coverage and remaining native-client checks are recorded in `docs/compatibility/jev-mcp.md`; do not infer completion of every case from unit success.

| ID | Setup/action | Expected result | Layer / acceptance |
| --- | --- | --- | --- |
| TC-01 | Spawn installed launcher; initialize, initialized, ping, list, call, EOF | Negotiated protocol, exactly four schemas, valid response ids, clean exit, no non-protocol stdout | subprocess / AC-02, AC-06 |
| TC-02 | Invalid JSON, oversized line, unknown method/tool/field, invalid types, batch, premature call, notifications | Bounded sanitized errors; no unintended engine call; notifications never answered | protocol / AC-02 |
| TC-03 | Fixed tasks and provider fixtures via MCP versus CLI | Same confident, empty, uncertain and local-agent outputs; only loader returns bodies | unit + subprocess / AC-03 |
| TC-04 | Confirm uncertain set; wrong ids/non-booleans; changed task; stale generation/release/catalog/body; concurrent clients | Valid decisions persist, invalid loads/decisions block, shared state remains consistent | integration / AC-03, AC-05 |
| TC-05 | Inherited CODEX_SANDBOX marker in registered MCP process, same direct CLI invocation | MCP adapter works if actual access is permitted; CLI still refuses sandbox entry | subprocess / AC-01 |
| TC-06 | Missing/unreadable/symlinked key, unwritable state, failed release integrity | Correct existing or explicit sanitized diagnostic; no secret read on invalid input; no unsafe fallback | integration / AC-04, AC-05 |
| TC-07 | Mock endpoint, redirects, auth/credit/rate/timeout/oversized/malformed responses, exception containing fake secret | Only fixed endpoint and one attempt; no secret or provider-body leakage to output/logs | transport / AC-04, AC-05 |
| TC-08 | Startup, tools/list, offline verify, record/load, then explicit live verify | Zero provider calls for first operations; one synthetic call for live; no task data in live request | integration / AC-04 |
| TC-09 | Build all clients plus Claude archive, relocate into path with spaces | Correct executable/args/root expansion and hashes; HTTP server entries preserved; no runtime dependency download | packaging / AC-06 |
| TC-10 | Disabled/denied MCP; killed process before/after cache write; reconnect with same task/session | Honest unavailable/unknown status; cached completed request reused, no automatic refresh or shell escape | integration + manual / AC-05 |
| TC-11 | Largest valid shipped skill set | Complete response fits limit, over-limit fixture errors without partial body | integration / AC-02, AC-03 |
| TC-12 | Fresh sandboxed Codex session using installed plugin and existing key | End-to-end selection/load without mode switch; shell restrictions still active; record client version and permissions | native manual / AC-01, AC-07 |
| TC-13 | Fresh Cursor session with existing shell restrictions and installed plugin | Discovery, offline verification, selection, human confirmation recording, and loading work through MCP without unrestricted mode or shell escalation; ordinary shell restrictions remain active | native manual / AC-01, AC-06, AC-07 |
| TC-14 | Fresh Claude session with existing shell restrictions; repeat for hosted archive installation | Same end-to-end MCP behavior as Codex and Cursor without unrestricted mode or shell escalation; ordinary shell restrictions remain active; relocated launcher works | native manual / AC-01, AC-06, AC-07 |

Automated tests use fake keys, temporary state, and mock provider transport; they
do not use a developer key or call OpenRouter. Real paid checks require explicit
user authorization and record sanitized evidence only. Unit success does not
claim native sandbox support or selection quality.

## Hook changes

No new hook event or provider call in hooks. Update static routing guidance in
`selection_guidance()`, the skill-selection and sub-agent-graph wrappers,
bootstrap, Cursor rules, pack policy/workflow and hook-injected context wherever
they currently prescribe outside-sandbox shell selection. Preserve selection
before delegation and existing human confirmation and implementation gates.
Do not call Jev from session startup, pre-commit, or compliance checks.

## Documentation and rollout/recovery

During implementation update `docs/skill-selection.md`, `docs/setup-guide.md`,
`docs/developer-integration.md`, `docs/plugin-operations.md`, and
`docs/architecture.md` to distinguish terminal credential setup, MCP daily use,
and legacy CLI diagnostics. Regenerate all three client packages and archives
through the existing builder; do not change generated outputs in this spec-only
change. Version and publish through the normal release process.

Verify local installations of Codex, Cursor, and Claude, including the Claude
hosted archive, before releasing this feature as complete. The order of local
testing does not reduce the required client scope.
Record client versions, installation form, server/tool enablement, Python version,
and actual sandbox behavior. If a client cannot launch this local server, record
the blocker and keep cross-client acceptance pending rather than changing that
user's global permissions or treating the integration as optional.

Rollback by disabling the new MCP row or restoring the preceding plugin version.
Keep credential and cache files; CLI retains its prior approved execution path.
Do not delete keys or force a new credential generation during rollback.

## Ownership, sequence, and risks

The implementing developer owns adapter/engine separation, protocol fixtures,
builder/relocation, instruction/doc updates and automated evidence. The reviewer
checks the privileged boundary and parity; the release owner records native
client evidence. No person is assigned implicitly by this draft.

Implement after feature review in this order: failing protocol/parity tests;
adapter and entry boundary; client generation/relocation; guidance and docs;
automated checks; native-client acceptance; release. The additional process and
three-client checks add work beyond a network configuration change. No delivery
date is committed; native-client failures must be resolved before claiming the
affected client is supported.

The server has the OS user's authority and is not itself a new sandbox. Its
fixed operations and client permissions constrain exposure; do not broaden it
into a general-purpose gateway. Client root-variable expansion and stdio
protocol compatibility need actual installation evidence. No universal managed
policy exemption, exactly-once billing, or zero tool-approval prompts is claimed.

## Documentation sources

Consulted on 2026-11-04:

- [Codex approvals and security](https://learn.chatgpt.com/docs/agent-approvals-security): shell sandbox versus approvals, and separate MCP policies.
- [Codex MCP configuration](https://developers.openai.com/codex/mcp): local stdio command/args and client configuration.
- Context7 `/openai/codex`, queried for workspace-write, command escalation and local stdio MCP execution: current executor launcher starts stdio MCP without the shell sandbox. This is implementation evidence, not a guarantee for every desktop/client policy.
- Context7 `/modelcontextprotocol/modelcontextprotocol/2025-06-18`, queried for stdio lifecycle and tools-only protocol: [transport](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2025-06-18/docs/docs/concepts/transports.mdx) and [logging](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/2025-06-18/docs/docs/tools/debugging.mdx). Implementation must verify full lifecycle/tool conformance against this revision, beyond the returned excerpts.

## Review and implementation handoff

Spec PR: not created
Review reference: MCP approach requested in chat on 2026-11-04; this detailed draft not yet reviewed
Merge reference/revision: not merged
Local spec matches merged reviewed version: not applicable
Next action: review the authorized implementation and automated evidence, reconcile
feature issue/spec review references through the authorized workflow, and complete
all native-client acceptance before release.

Runtime implementation was explicitly authorized in chat on 2026-11-04. See
`docs/compatibility/jev-mcp.md` for implementation evidence and remaining native
acceptance. No issue publication, spec review/merge, native compatibility or live
paid Jev call is claimed.
