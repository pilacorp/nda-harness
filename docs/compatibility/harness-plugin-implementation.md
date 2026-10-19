# Phase-0 plugin implementation evidence

Checked 2026-10-18 on `implementation/hindsight-supabase-auth`, based on merged
`dev` revision `f035ccf1dbbb74131834f6673647474299447937` (PR #14).

The 2026-10-18 [package contract](evidence/harness-plugin-implementation-2026-10-18/package-contract.json)
recorded that the local spec matched that merged revision byte for byte. The
2026-10-19 Claude Code Desktop edit changes the local spec after that record.
Issue #10 was rechecked and still contains the earlier CLI/provider-token design;
the owner's subsequent clarifications and explicit implementation instruction
authorize the merged plugin contract. No server implementation is changed here.

## Claude Code Desktop package

Added 2026-10-19. `plugin_build --client claude` emits `nda-harness-claude` from
the same engine as Codex and Cursor. Automated package, hook-output, and shared
bank tests cover that contract. Native Desktop trust, OAuth, and hook execution
have not been observed in the Claude Code Desktop app. Those unit tests are not
Desktop UI evidence. The 2026-10-18 sections below remain the Codex and Cursor
record from that date.

## Implemented behavior

The shared `plugin_build` module creates reproducible `nda-harness-codex` and
`nda-harness-cursor` packages. Each final tested package contains 719 hashed files.
All 31 shared runtime/pack file hashes match across clients. Differences are native
manifests, hook/MCP/rule formats, client-bound skill instructions, and generated
Superpowers namespace references. There are no maintained client engine copies.

Packages include full specialist skills, Python support wheel, licenses, and
checksum-pinned Superpowers source. The original upstream source and handlers are
preserved in `vendor/superpowers`; active Markdown skill references are generated
under each containing plugin's namespace. NDA's bootstrap loads using-superpowers
without registering a duplicate upstream handler or changing existing plugins.

Trusted session hooks attempt locked bootstrap of RTK; Superpowers and Context7
are native packaged components. Failed, installing and awaiting-trust bootstrap
states cannot report core ready. Cursor's always-applied rule and explicit skills
handle asynchronous/missing hooks. Setup does not open OAuth or prompt on hook stdin.

Project configuration is schema 2 `.nda-harness/profile.json`: explicit test command
and project memory-bank identity. No response leaves configuration pending; explicit
Skip stores `true`. Shared assets and machine paths stay outside the project.
Each clone activates private composed Git wrappers; prior hooks and configured
tests must both pass. Repeated activation is idempotent, foreign manager changes
conflict, and ignored project configuration cannot report ready. Write-ahead
receipts/backups support rollback and interrupted setup recovery.

Git identity normalizes supported SSH/HTTPS forms and persists a deterministic
project bank ID. Ambiguous remotes require explicit selection; missing remote
requires a project name. Existing identity conflicts block silent reassignment.
Both clients share project protection/configuration. Dev/staging/prod remain labels
within the same bank, with dev the default.

Five context operations use the packaged runtime and explicit skills. They inspect
the real checkout/profile, fingerprint local inputs, and recover selected task
records across sessions. Task preparation, changed specs, stale checkpoints and
missing protection cannot imply approval. Retrieved/project prose is never copied
into privileged hook output; raw prompts/transcripts are ignored.

Optional Hindsight uses only a packaged `/mcp/` URL and native MCP declarations.
The client owns OAuth. There is no harness token collector/store, provider setting,
auth header, forwarder or callback listener. Authenticated agents use the
hindsight-memory instructions for automatic scoped recall/retention and available
client-default-memory fallback. These agent behaviors require real-client trials;
local tests do not prove the agent followed them.

## Automated checks

Run the complete suite:

```sh
.venv/bin/python -m unittest discover -s tests
```

The plugin-specific tests use disposable homes and real Git repositories. They
cover reproducible complete packages, endpoint restrictions, client-specific
schemas/namespace adaptation, absent configuration versus explicit Skip, passing
and failing tests/existing hooks, concurrent setup, foreign manager preservation,
clone activation, cross-client protection, shared bank identity, environment labels,
read-only verification, failed/bootstrap-pending states, symlink/integrity conflicts,
ignored configuration, all context operations, cross-session resume and durable
write-ahead recovery, including a write that never reached the filesystem.

The complete suite passed **147 tests**. Focused plugin/context checks were rerun
after the final local source-discovery addition. Runtime output lists instruction
and task candidates as ordinary data and never infers an active task from them.

A separate manual runtime trial used the generated package, actual local compatible
RTK, a disposable HOME and Git repository. Explicit Skip produced project/core
readiness and allowed a Git commit. Verify returned exit 3 because native session
and MCP checks remained pending. Hindsight was not needed for setup or the commit.

## Codex native runtime evidence

[codex-native-discovery.json](evidence/harness-plugin-implementation-2026-10-18/codex-native-discovery.json)
was produced using the final generated package and the Desktop-bundled
`codex-cli 0.163.0-alpha.10.2` at
`/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex`.

The trial used an isolated temporary CODEX_HOME/project. It registered the generated
local marketplace, installed the package, then used app-server `plugin/read`,
`hooks/list`, `skills/list` and `mcpServerStatus/list`. No agent thread/model was
started, no login was launched, and no memory read/write operation was called.

Observed:

- Installation returned **ON_USE** authentication.
- 26 skills were discovered, including all five context operations, setup/verify,
  specialist skills, and bundled Superpowers. No skill parser errors.
- SessionStart, UserPromptSubmit and PreCompact were discovered. Native diagnostics
  serialize those names in camelCase. No hook parser errors.
- All hooks were **untrusted**; execution was not attempted. Trust was not bypassed.
- Hindsight and Context7 native MCP registrations were discovered.
- Hindsight returned **oAuth** and **39 tools** through the native runtime.
  The host already had native credentials for the loopback service from the prior
  sample test; an isolated CODEX_HOME does not isolate the OS credential store.
  This proves authenticated discovery with this package, not a new login or expiry.

Reproduce the sanitized probe with a generated Codex package:

```sh
python3 scripts/compatibility/plugin_runtime_trial.py \
  --codex /Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex \
  --package /absolute/generated/codex/package
```

The probe changes only a temporary native profile and never exports credentials.
Desktop detail-page UI and trusted session execution are separate pending checks;
runtime discovery does not establish Desktop/CLI parity.

## Cursor binding and remaining client checks

Generated Cursor paths: `.cursor-plugin/plugin.json`, `mcp.json`,
`hooks/hooks.json`, `rules/nda-harness.mdc`. Hook candidates are sessionStart,
beforeSubmitPrompt, preCompact and workspaceOpen. Only sessionStart receives
`additional_context`; observational events do not invent context fields.
beforeSubmitPrompt keeps chat available while the rule requires readiness before
dependent work. Helpers use the resolved package root and fixed `--client cursor`.

The full generated Cursor package has automated schema/behavior checks but has
**not** been loaded in the actual IDE in this implementation trial. The prior
[minimal OAuth plugin test](hindsight-oauth-plugin-test.md) observed Cursor
**3.25.9 Universal** loading an MCP row, native **Authenticate**, successful OAuth,
39-tool discovery and persistence after Reload Window. That sample did not prove
the new full package's bootstrap/rule execution.

Before claiming complete supported-client acceptance, record:

- Full package loading and trusted hook execution in each target UI, including
  first setup, missing/failed tools, concurrent sessions and Cursor startup races.
- The full Cursor package's rule/skill discovery and project test-command chat.
- Codex Desktop's own Hindsight detail row and authentication action.
- Native cancel/disconnect/revoke/outage, actual access-token expiry/renewal and
  client restart, with independent clients' connections preserved.
- Automatic agent recall/retention in the exact same project bank from both clients,
  environment labeling, and truthful fallback when Hindsight is unavailable.

The production HTTPS Hindsight hostname remains unspecified. The final local
packages used explicit `--local-test` with `http://127.0.0.1:8891/mcp/` against the
Hindsight OAuth server previously tested at source revision `14be9a293`. Deployment
builds require HTTPS and must revalidate an evolving server contract. The hostname
blocks deployment memory activation, not core implementation or local testing.

## Acceptance status

| Spec criteria | Evidence/status |
| --- | --- |
| AC-01, AC-02 | Reproducible package/unit checks; native Codex discovery passes. Trusted host bootstrap and full Cursor loading pending. |
| AC-03, AC-05, AC-08 | Independent core setup verified; no harness OAuth/provider/migration runtime is packaged. |
| AC-04, AC-13 | Generated Codex native authenticated discovery and earlier two-client OAuth sample; full UI/deployment checks above pending. |
| AC-06, AC-12 | Native credential ownership and agent instructions implemented; full lifecycle and automatic behavior need real-client evidence. |
| AC-07, AC-09, AC-10 | Five-operation/project/real-Git/concurrency/recovery checks pass; actual host chat/trust flow pending. |
| AC-11 | Shared deterministic identity/environment/clone/client checks pass; shared live memory use still pending. |

No public release, migration, deployment approval or complete native compatibility
claim follows from these results. Historical CLI files are excluded from generated
plugin runtime modules and remain development evidence only.
