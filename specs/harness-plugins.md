# Developer spec: NDA Harness client plugins

Feature issue: [pilacorp/nda-harness#10](https://github.com/pilacorp/nda-harness/issues/10)
Spec branch: `specs/hindsight-supabase-auth`
Requirement clarification: owner instructions on 2026-10-18 in this development conversation.
Consulted source revisions: NDA Harness `93d704f97bf92b87ef4eee7649466412b755a01f`; Hindsight branch `nda/10-supabase-tenant` at `14be9a293`.

This document replaces `specs/minimal-cli.md` and `specs/hindsight-supabase-auth.md`.
The repository began in development phase 0. The merged follow-up
[internal marketplace specification](internal-client-marketplaces.md) supersedes
this document's exclusions for stored Claude packages, released-installation
updates, one-time identity migration and release recovery. Legacy credential
conversion remains excluded. Historical trial reports describe earlier experiments
and do not define the plugin requirements.
The issue has not been revalidated in this edit; reconcile it with the owner's
clarifications before implementation review.

## Outcome and boundaries

Task classification: behavior change; this edit changes the specification only.

The initial supported surfaces are Codex Desktop, Cursor IDE, and Claude Code
Desktop. Claude Code Desktop uses the shared Claude Code plugin store, so
`claude plugin` registers the same package the Desktop Code tab loads. Other
agent CLI surfaces are outside this initial phase. Each plugin provides the harness workflow, specialist skills,
context lifecycle operations, and setup/verification entrypoints. A shared local
CLI may remain an implementation helper. The plugin is the delivery and discovery
surface. Installing plugins for multiple clients requires no agent-selection menu.

Hindsight is an optional memory connection. The client connects directly to the
Hindsight HTTPS endpoint ending in `/mcp/` and performs OAuth with Hindsight using
the client's supported MCP authentication flow. The harness sees Hindsight as
the OAuth service. Identity-provider implementation details belong to Hindsight.

In scope:

- Initial packages: `nda-harness-codex`, `nda-harness-cursor`, and `nda-harness-claude`.
  The repository stores all three generated packages and matching root catalogs,
  as required by the follow-up internal marketplace specification.
- One shared engine and asset source, with thin client adapters and reproducible
  packaging of the same engine revision for the initial clients.
- Harness workflow/rules, specialist skills, context operations, project adoption,
  unit-test hook setup, and verification through each plugin.
- Optional Hindsight MCP registration and client-native OAuth connection.
- Local macOS development installation and client-specific compatibility evidence.

Out of scope:

- Compatibility with old CLI flags or credentials and credential conversion.
  Marketplace identity migration and release recovery are governed by the follow-up spec.
- Hindsight or identity-provider deployment, login pages, user management, token
  issuance, and database/schema management. These belong to the `hindsight` repo.
- A harness OAuth client implementation, token store, refresh service, local HTTP
  forwarder, callback listener, or LaunchAgent.
- RAG integration, public marketplace publication, Linux, and Windows.

## Plugin packaging and engine

Each package uses its client's supported manifest, skill discovery, MCP
configuration, and hook formats. Do not assume a shared manifest schema or a
custom `knowledge_systems` field is rendered by a client. Describe Hindsight as
optional memory in the plugin documentation and supported MCP listing metadata.

The package includes the shared `bin/`, `scripts/`, `pack/`, `skills/`, and `vendor/`
assets needed by its adapter. Package generation must not fork engine behavior
or maintain handwritten copies of the shared assets per client. Include dependency
pins, licenses, provenance, and required skill references and scripts.

The plugin's setup and verify entrypoints pass a fixed client identity to the
shared engine. Specify this as an internal `--client codex|cursor|claude` argument
on helper invocations; the plugin supplies it rather than prompting the user.
A direct helper invocation without a client reports the required argument. Each
invocation configures only that client and preserves unrelated settings.

Run helpers from packaged paths, independent of the working directory. Do not
require a prior global CLI installation. If the implementation also installs a
global helper, it is optional and cannot determine the active client by guessing
which applications are installed. Python helpers require Python 3.11+ with the
pinned dependency bundle; setup reports a missing prerequisite without installing
Python or changing shell startup files.

Plugin installation makes packaged skills and hooks discoverable. Automatic
bootstrap installs RTK, Superpowers, and the Context7 integration at the first
eligible session after required client permissions and hook trust. It does not
open a login browser or require Hindsight. No separate manual setup command is
the normal first-run experience. Record dependency pins and verify installation
idempotently without duplicating existing registrations. Report awaiting-trust,
installing, ready, and failed states; installing the package alone does not prove
the tools are ready. Serialize simultaneous bootstrap attempts.

Codex's candidate trigger is trusted `SessionStart`. Claude Code's is the same
event, including startup, resume, clear, compact, and fork; the first response
waits for it, and `UserPromptSubmit` injects the same readiness context.
`PreCompact` writes the local checkpoint and must not block compaction. Claude
Code discards `systemMessage` on that event, so the model-visible reminder is
the following `SessionStart` with source `compact`, `UserPromptSubmit`, and the
explicit `context-checkpoint` skill. Cursor's trigger is `sessionStart`, which
does not wait for setup to complete. Client-specific readiness checks must
handle that timing. Document actual activation and trust steps; do not assume an
install-time script callback. Explicit plugin setup remains a recovery fallback.

### Harness capabilities

Preserve the shared workflow and its prerequisite checks: issue linkage, reviewed
and merged developer specs before behavior-change implementation, unit Red →
Green → Refactor, human review, RTK, and current library documentation via Context7.
Instructions and hooks do not authenticate approvals or grant publication authority.

Each adapter exposes the following shared operations through plugin skills or
commands, with native hooks only where supported and validated:

| Operation | Trigger and behavior |
| --- | --- |
| `session-bootstrap` | Session start or explicit invocation; identify checkout, applicable instructions, profile, task records, and readiness. |
| `task-prepare` | Before dependent task work; gather authoritative sources, workflow stage, prerequisites, and next permitted action. |
| `context-refresh` | Relevant source changes, stage transitions, or explicit invocation; reconcile changed sources before dependent work. |
| `context-checkpoint` | Before compaction/handoff or a stage boundary; preserve sanitized task facts and evidence references in the repository task record. |
| `context-resume` | Resume or post-compaction invocation; rebuild context from repository artifacts and reconcile current revision and task state. |

Follow [context preparation](../docs/context-preparation-hooks.md) for trust
boundaries and operation semantics. External memory is never required to recover
task state or establish approval. A failed or unavailable native hook retains an
explicit invocation fallback and cannot imply readiness.

### Project configuration and commit checks

The installed plugin is available automatically in every project. There is no
project/user scope selection. On entering a project, harness hooks check for
`.nda-harness/` at its root. If missing, initiate project initialization and have
the agent ask for the test command in chat. Hooks consume/produce the client's
structured data; they do not run a terminal prompt on their JSON input stream.
After the answer, complete configuration and activate the Git check. Allow an explicit Skip choice, which stores the
literal command `true`; explain that this passes the check without running tests.
If interaction is unavailable, report configuration as pending rather than
silently choosing Skip. Reuse existing configuration without repeated prompts.

The project commits `.nda-harness/` to Git. It contains the project-specific
configuration, including the test command, project memory-bank identity, and
sanitized task records. Shared plugin skills and rules need not be copied into
each project. Credentials, private diagnostics, and machine-specific paths stay
outside the committed directory.

Install a local Git pre-commit check that executes the configured test command
from the project root. A failing test command blocks the commit; `true` succeeds
without running tests. Preserve and compose existing Git hooks or hook managers:
failure of either the existing check or the harness check blocks the commit.
Never silently replace an existing hook or bypass a failure. A clone's committed
configuration is reused, while local hook activation is checked on that machine.
Repeated activation must not duplicate hook calls.

Preserve unrelated files and use backed-up transactional writes; failed
initialization restores its owned writes. If safe hook composition cannot be
established, report the conflict and incomplete protection instead of claiming
that commits are guarded.

## Optional memory

A project uses one memory system at a time. The package lists the systems it can
offer. Setup writes that choice to `memory.system`. One packaged system is
selected automatically. Several packaged systems require an explicit
`--memory-system` choice. NDA Hindsight is the only system in this phase. Its MCP URL is
`https://hindsight-api.pila.vn/mcp/`. OAuth discovery and the REST API use
`https://hindsight-api.pila.vn`.

## Optional Hindsight memory

NDA Hindsight is packaged at `https://hindsight-api.pila.vn`. MCP is
`https://hindsight-api.pila.vn/mcp/`. OAuth metadata and `/ext/oauth/`, and the
REST API, use the same host. The URL is HTTPS, ends in `/mcp/` for MCP, and has
no userinfo, query, or fragment. A missing override does not block installation.

1. Install and initialize the plugin without authenticating to memory.
2. The plugin detail page presents a Hindsight memory row with the client's native
   authentication button, such as **Authenticate** or **Authorize**. The developer
   explicitly clicks it to start the client's OAuth action. The owner accepted
   native wording on 2026-10-18. Validate host support for each initial client.
   If a host cannot provide it, surface that limitation for a product decision
   rather than claim the exact UI is supported or silently substitute another flow.
   Investigation found an **Authenticate** button on an existing Cursor plugin's
   MCP row; this wording meets the requirement. NDA Harness's own integration
   and Codex's detail-page presentation still require validation.
3. The client connects directly to `HINDSIGHT_MCP_URL` and uses Hindsight's MCP
   OAuth discovery, registration, authorization-code/PKCE, and token endpoints.
4. The client opens Hindsight's authorization page and owns callback handling,
   credential storage, access-token renewal, and logout using supported client APIs.
5. Subsequent MCP calls go directly from that client to Hindsight. Bank selection
   uses the multi-bank tools' `bank_id` arguments where required.

Do not put static Authorization headers in the plugin. Do not collect passwords,
access tokens, refresh tokens, identity-provider URLs, anon keys, service keys, or
identity-provider credentials in the harness. Client-managed credentials are not
copied into harness state, project files, receipts, logs, or command arguments.

The server contract follows the `hindsight` repository's deployed OAuth-enabled
API, currently implemented by `hindsight-extensions/nda-oauth/nda_oauth/extension.py`.
Do not exchange a Hindsight authorization code at an identity-provider endpoint.
The server implementation is still evolving: record its tested revision and
public MCP URL during integration validation, and update the contract when it changes.

Memory states are disabled, awaiting authentication, connected, and unavailable.
Cancellation, expired/revoked authorization, or a network failure leaves the core
harness usable and produces an actionable memory status. Reauthentication uses
the client's Hindsight OAuth action. Disconnect uses the client's supported
disable/disconnect controls and does not modify other clients' connections.
No shared harness credential exists across clients. Each client signs in separately.

### Automatic memory and project banks

After authorization, the agent automatically recalls relevant context and saves
useful preferences and working notes. Keep credentials and secret values out of
memory; store references to their configured locations instead. Memory does not
replace authoritative repository sources or approval evidence.

Codex, Cursor, and Claude Code signed into the same Hindsight account share the
same project bank. Bank identity is project-scoped, independent of the harness engine and
client. Use the project's Git remote URL to identify it; equivalent SSH/HTTPS
forms of the same repository must resolve to the same identity. Different clones
and local folder names must not create separate banks. If no remote exists, or
the directory is not a Git checkout, ask the developer for the project name
before using Hindsight memory. A directory that is not a Git checkout still
receives `.nda-harness/profile.json`; commit hooks are installed only for a
repository. Persist the
resolved project identity in `.nda-harness/` and avoid guessing when remotes are
ambiguous or conflict with existing configuration.

Use one bank per project, not one bank per environment. Label dev/staging/prod
details within that bank, such as endpoints, IP addresses, and references to keys.
Default to dev; the developer explicitly selects staging or prod when needed.
Do not treat environment selection as authorization to access or change a service.

When Hindsight is unavailable, continue development using the client's default
memory where available. Report Hindsight's unavailable status; do not claim a
fallback exists if the client provides none or silently copy its memories into
Hindsight when connectivity returns.

## Verification and client bindings

Verify checks plugin assets, effective instructions/skills/hooks, helper runtime,
project configuration, unit-test integration, and configured knowledge connections. It
does not repair configuration or fabricate manual evidence. Store only sanitized
diagnostics in private state. Distinguish core readiness from optional memory
readiness; a disabled/unavailable memory service does not fail core verification.

For a connected memory service, use the client's authenticated MCP connection to
initialize and discover tools. Do not extract credentials to make a separate CLI
request. If no supported diagnostic exposes that connection, report the check as
pending and provide a real-client check. Do not retain content or read memories
as a verification side effect.

Before claiming support, record for Codex Desktop, Cursor IDE, and Claude Code Desktop:
exact version, manifest and MCP paths/schema, plugin installation steps, fixed-client
helper invocation, hook event names, trust/activation steps, OAuth connection and
disconnect actions, credential ownership, and observed test results. Do not assume
desktop/CLI parity.

Claude Code Desktop paths are `.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json` with plugin source `.`, `hooks/hooks.json`, and
`.mcp.json`. Leave `hooks` and `mcpServers` out of `plugin.json`; Claude Code
merges those keys with the default files and would register each hook and server
twice. Hook commands expand `${CLAUDE_PLUGIN_ROOT}`. Authentication is the native
MCP action in `/mcp` or the Desktop Code tab plugin/MCP row. Record the observed
label. Do not invent a custom Authenticate button. Installation does not open a
login browser.

See the [2026-10-18 capability investigation](../docs/compatibility/harness-plugin-investigation.md)
for documentation sources, live Cursor observations, Codex UI access limits, and
unexecuted checks. Existing plugins demonstrate host UI/component support; they
do not establish NDA Harness bootstrap or Hindsight OAuth compatibility.

The follow-up [minimal plugin OAuth test](../docs/compatibility/hindsight-oauth-plugin-test.md)
demonstrates native OAuth login and authenticated 39-tool discovery with our
minimal packages in Cursor IDE and the Codex desktop-bundled runtime. Cursor's
own sample detail page and Authenticate button were exercised. Codex's Desktop
detail-page UI, actual token expiry, optional-auth installation, and full harness
bootstrap remain unverified. This experiment used HTTP loopback only; deployed
connections still require HTTPS.

## Acceptance mapping

| ID | Requirement | Expected behavior |
| --- | --- | --- |
| AC-01 | Client plugin delivery | Codex Desktop, Cursor IDE, and Claude Code Desktop load packaged skills/hooks and automatically bootstrap RTK, Superpowers, and Context7 at the first eligible trusted session. |
| AC-02 | Client identity | Setup/verify target only the invoking plugin's client with no agent-selection menu. |
| AC-03 | Core independence | Fresh setup and core operation succeed without Hindsight or any login. |
| AC-04 | Direct OAuth | Each enabled client authenticates with Hindsight and calls `/mcp/` directly. |
| AC-05 | Service boundary | Harness packages and state contain no identity-provider configuration or harness-managed OAuth credentials/forwarder. |
| AC-06 | Memory lifecycle | Cancel, disconnect, expiry, renewal, and outage have explicit memory states without blocking core work. |
| AC-07 | Engine coverage | All five context operations are available in every project with documented hook fallbacks. |
| AC-08 | Original phase 0 boundary | Superseded for marketplace migration/update/recovery by the follow-up internal marketplace spec; no credential conversion is required. |
| AC-09 | Project configuration | Hooks initialize a missing committed `.nda-harness/`, ask for a test command, and allow Skip storing `true`. |
| AC-10 | Commit protection | Failed tests or existing hooks block commits; existing hooks are preserved and repeated initialization is idempotent. |
| AC-11 | Project memory | Same-account clients share a Git-remote-identified project bank; no remote prompts for a project name; environments are labels within the bank. |
| AC-12 | Automatic memory and fallback | Authorized memory is used automatically; Hindsight outages fall back to available client memory without blocking development. |
| AC-13 | Authorization UI | Each client surfaces a Hindsight MCP entry with its native authentication action (Authenticate/Authorize, or Claude Code's `/mcp` and Desktop plugin/MCP controls), verified against that client. |

## Concrete test cases

These are planned checks, not executed compatibility evidence.

| ID | Setup/input and action | Expected result | Layer / acceptance IDs |
| --- | --- | --- | --- |
| TC-01 | Generate initial packages; install in each target client; grant required trust and start a session | Shared hashes and manifests validate; packaged skills/hooks load; dependencies bootstrap automatically; before trust/setup completion readiness remains pending. | packaging + real client / AC-01 |
| TC-02 | Run each plugin's setup and verify entrypoints | Fixed client identity; no agent menu; other clients' settings unchanged. | unit + real client / AC-02 |
| TC-03 | Fresh install; Hindsight unconfigured or offline | Core setup and context operations work; memory remains disabled. | integration / AC-03 |
| TC-04 | Enable memory in each supported client against the OAuth-enabled Hindsight deployment | Browser authorization completes and direct `/mcp/` tool discovery succeeds. | real client / AC-04 |
| TC-05 | Inspect packaged MCP config, helper calls, state, and sanitized diagnostics | No static bearer, provider configuration, token copies, forwarder, or callback service. | unit + review / AC-05 |
| TC-06 | Cancel OAuth, disconnect, revoke authorization, or stop Hindsight | Actionable memory status; core engine remains usable; other clients unchanged. | real client / AC-03, AC-06 |
| TC-07 | Allow access authorization to expire; invoke MCP again and restart the client | Client renewal/reconnection works, or reports reauthentication; no harness token handling. | real client / AC-04, AC-06 |
| TC-08 | Invoke all five operations with hooks enabled, disabled, and awaiting trust | Correct context behavior or explicit fallback/pending state; no fabricated readiness. | unit + real client / AC-07 |
| TC-09 | Missing/existing project config, unrelated config, and injected write failure | Missing folder initializes; existing config is reused; unrelated data is preserved; owned writes recover on failure. | unit / AC-02, AC-07, AC-09 |
| TC-10 | Enter a test command, then choose Skip in another project | Commands persist in committed configuration; Skip stores `true` and reports no tests run. | unit / AC-09 |
| TC-11 | Passing/failing project tests and passing/failing existing Git hooks; repeat initialization | Either failure blocks commits; successful checks allow commits; hooks are preserved without duplicate execution. | integration / AC-10 |
| TC-12 | Same repository cloned with equivalent SSH/HTTPS remotes in each supported client | Same account uses one project bank across clones and clients. | unit + real client / AC-11 |
| TC-13 | No Git remote; then dev/staging/prod selection | Ask for project name before memory use; environment details remain in the same project bank; dev is default. | unit + real client / AC-11 |
| TC-14 | Authorized normal work followed by Hindsight outage | Automatic scoped recall/save when connected; available default client memory during outage; no fabricated connection or success. | real client / AC-12 |
| TC-15 | Open each client's native Hindsight authentication action | The action starts direct Hindsight OAuth. Cursor and Codex may show Authenticate/Authorize. Claude Code uses `/mcp` or the Desktop plugin/MCP row. Record the observed label; an unsupported control stays unresolved. | real client / AC-13 |
| TC-16 | Repeated/concurrent first sessions, missing tools, and bootstrap failure | No duplicate installations/registrations; bootstrap is serialized; installing or failed states never claim ready. | integration + real client / AC-01 |

## Documentation and review handoff

Implementation updates `INSTALLATION.md`, README, client integration guides, and
compatibility evidence to describe plugin-first installation, fixed-client setup,
optional direct Hindsight OAuth, and per-client trust and disconnect steps. Earlier
CLI trial reports remain historical evidence. Server deployment changes are made
in `hindsight`; the old `hindsight-deploy.md` is historical server planning, not
the auth contract for these plugins.

Release rollout, recovery and one-time migration now follow
`internal-client-marketplaces.md`. Development setup still needs safe failure
recovery for its own file writes.

Spec PR: unset
Review reference: unset until reviewed
Merge reference/revision: unset until merged
Local spec matches merged reviewed version: unset
Next action: review this phase-0 plugin spec and record concrete client bindings
and integration evidence before claiming compatibility. This draft does not grant
behavior-change implementation approval.
