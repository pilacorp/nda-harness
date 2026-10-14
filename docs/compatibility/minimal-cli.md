# Minimal CLI compatibility trial

Historical trial status: **incomplete**. The owner subsequently authorized the
[Codex/Cursor Apple Silicon implementation phase](minimal-cli-phase.md), deferring
Claude and Intel. This report records
actual prerequisite checks on 2026-10-14. It does not certify client support or
claim that AC-01–20 or TC-01–44 have passed.

## Specification and review

- [Issue #4](https://github.com/pilacorp/nda-harness/issues/4) was reread in the
  authenticated browser. Its visible requirements still match the merged spec;
  an API body fingerprint was not recalculated because the connector cannot
  access the private repository.
- [PR #5](https://github.com/pilacorp/nda-harness/pull/5) is merged into `dev` at
  `b9cc5c518d71ab79c0407bff9335ed63616c6f78`. The local spec is byte-identical to
  the PR head `da9c7e94c0e016578f4a13fd8bf166344a73b115` (empty Git diff).
- GitHub displays no formal PR review. The owner explicitly confirmed in this
  implementation conversation that a tech lead already reviewed it. This is
  owner-confirmed evidence, not a fabricated GitHub approval event.
- The accepted plan and [spec](../../specs/minimal-cli.md#compatibility-trial-before-full-installer-implementation)
  require concrete integration bindings and pins before building the full engine.

## Executed checks

The host is Apple Silicon (`arm64`), macOS 26.5.2, with Python 3.13.2.
Version probes and upstream RTK initialization use scratch directories and fresh
child environments without inherited credentials. Personal agent configuration
was not used as a fixture or modified.

| Check | Observation | Meaning |
| --- | --- | --- |
| RTK executable | Version 0.37.2; installed binary SHA-256 recorded in the dependency manifest | Identity observation only; official release artifact verification remains pending |
| Codex CLI `--version` | Exit 1; npm launcher cannot spawn its missing native executable (`ENOENT`) | This installation cannot run a client trial |
| Cursor IDE bundle | 3.24.12, build 3.24.12 | Application detection only |
| Cursor launcher | Normal-environment version probe reported 3.24.12; fresh-home probe timed out after 15 seconds | GUI configuration isolation remains unresolved |
| Cursor Agent CLI | `2026.03.30-a5d3e17` | Executable version observed |
| Isolated Cursor Agent session | Exit -11, `SecItemCopyMatching failed -50`, before receiving an answer | macOS Keychain/isolation failure; no successful authenticated session |
| Desktop bundle labelled ChatGPT | 26.1007.30912, build 20156 | Does not establish Codex desktop version or isolated runtime compatibility |
| Claude | No CLI executable or `/Applications/Claude.app` found | Both Claude surfaces remain unavailable |
| Context7 connected tool | Resolved Cursor, RTK, Superpowers and retrieved focused public documentation | Hosted docs retrieval works through the existing connector; target-client MCP loading/authentication is untested |
| Superpowers source | Inspected revision `bb92a77741419a4ab5f06e711a283343f1ada0c3`, manifests version 7.0.0 | Source inspection only; plugin installation, approval, activation and observed output are pending |

### RTK scope and preservation trials

| Command (RTK 0.37.2) | Observed result | Rerun / preservation |
| --- | --- | --- |
| `rtk init --codex` | Exit 0; project `AGENTS.md` references generated `RTK.md`; no Codex native hook created | Second run leaves the scratch file hashes unchanged; existing instructions preserved |
| `rtk init --global --codex` | Exit 0; instruction files under the isolated `CODEX_HOME` | Second run unchanged; existing instructions preserved |
| `rtk init --agent cursor` | Exit 1; upstream reports that Cursor hooks are global-only | Existing instructions and unrelated handler preserved; no project binding established |
| `rtk init --global --agent cursor` | Exit 0 after creating the expected `.claude` directory; writes `.cursor/hooks.json`, `.claude/RTK.md`, `.claude/CLAUDE.md`, RTK filters | Second run unchanged; seeded unrelated Cursor handler and Claude instructions preserved |

Cursor's global hook registers `preToolUse` with matcher `Shell` and command
`rtk hook cursor`. Its command relies on PATH; GUI resolution has not been
verified. A completely fresh home without `.claude` failed initialization with
a missing-directory error. These are observations of upstream 0.37.2, not a
reason to implement custom rewriting or silently install a different version.

The spec allows documented RTK instruction fallbacks. Codex's observed instruction
integration is a candidate fallback, not verified automatic rewriting. Cursor's
project-scope integration needs an upstream-supported solution or an owner-reviewed
scope decision; a user-global hook must not be silently labelled project-local.

### Superpowers source evidence

At the inspected immutable revision:

- `.codex-plugin/plugin.json` declares the skills directory and `hooks: {}`.
  This alone does not establish client startup behavior.
- `.cursor-plugin/plugin.json` points to `hooks/hooks-cursor.json`, registering
  `sessionStart` with `./hooks/run-hook.cmd session-start`.
- `hooks/hooks.json` registers Claude `SessionStart` for `startup|clear|compact`.
- `.codex/INSTALL.md` is absent. Do not use obsolete installation instructions.

No upstream code was executed during this source inspection, and no plugin was
installed into a personal client.

## Required support matrix

Each cell represents a separate surface/scope/architecture trial. **All remain
pending**, including locally detected applications: configuration writes and
version detection do not prove fresh-session support.

| Surface | arm64 project | arm64 user | Intel project | Intel user | Current limitation |
| --- | --- | --- | --- | --- | --- |
| Cursor IDE | Pending | Pending | Pending | Pending | Isolated GUI profile, User Rules, plugin activation, Python/PATH and context coexistence unverified |
| Cursor CLI | Pending | Pending | Pending | Pending | Isolated session crashes; authentication/secret-storage binding unresolved |
| Codex desktop | Pending | Pending | Pending | Pending | Isolated desktop runtime/version and plugin loading unverified |
| Codex CLI | Pending | Pending | Pending | Pending | Local executable installation is broken |
| Claude Desktop local Code tab | Pending | Pending | Pending | Pending | Application unavailable |
| Claude Code CLI | Pending | Pending | Pending | Pending | Executable unavailable |

For every cell, record OS/client/dependency versions, exact supported install
command or UI steps, configuration paths, a tested authentication/secret-storage
mechanism, restart/trust steps, native/fallback bindings, GUI interpreter behavior,
fresh-session observations, and recovery/preservation evidence. Unresolved fields
remain pending; do not fill them from another client or architecture.

The [dependency manifest](../../pack/dependencies.json) retains
`installer_ready: false` for the broad compatibility claim. The subsequent phase
pinned tomlkit and Superpowers source, and verified official Apple Silicon RTK
archive/executable hashes. Target-client authentication and plugin activation
remain manual/pending; see the phase report for the implemented behavior.

## Reproduction and next steps

From the repository root, with Python 3.11+:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/compatibility/minimal_cli_trial.py --rtk
```

The trial runner emits sanitized JSON and exits **3** because compatibility is
pending. It detects local installations and optionally runs upstream RTK scope
and rerun trials in automatically cleaned scratch homes. It never authenticates,
starts agents, installs dependencies, or registers personal hooks. It drops
inherited credentials, does not print raw subprocess output, and records only
version allowlists, exit codes and scratch file hashes. Its 24 pending matrix
rows are not automatically promoted by successful inventory or RTK writes.

The checked-in [local evidence](minimal-cli.local-evidence.json) is the output of
that command. Temporary path-dependent hashes are valid only for comparison
within the same trial; do not compare those hashes across hosts.

Required before full engine implementation:

1. Supply a working isolated Codex CLI installation and isolated desktop profiles.
2. Resolve Cursor's fresh-home Keychain failure using a supported test profile
   and a designated test account; do not copy personal credentials into fixtures.
3. Provide isolated Claude installations and an Intel macOS environment.
4. Complete actual skill/rules discovery, Context7 per-client authentication and
   retrieval, Superpowers installation/pinning/activation, upstream RTK command
   behavior, hook output coexistence, Python/PATH and recovery trials.
5. Select reviewed release pins and official artifact hashes only from successful
   trial evidence. Then implement the full CLI with the spec's AC/TC mapping.

### Acceptance evidence

AC-19 / TC-44: prerequisite inventory, RTK file-preservation trials and upstream
manifest inspection executed; the compatibility matrix and exact authentication
bindings remain incomplete. AC-05/07/08/16 and real-client portions of AC-18 are
pending. AC-01–04/06/09–15/17/20 and remaining TC-01–43 await full implementation
and their specified tests. The trial runner unit tests verify only isolation,
failure-output handling, version extraction, pending-matrix completeness and
hash-only snapshots; they are not substitutes for installer acceptance tests.

## Documentation consulted

Consulted on 2026-10-14; documentation may describe versions newer than those
installed locally. Executed observations take precedence for the tested version.

- [Cursor CLI parameters](https://cursor.com/docs/cli/reference/parameters),
  [authentication](https://cursor.com/docs/cli/reference/authentication) and
  [MCP](https://cursor.com/docs/cli/mcp), retrieved through Context7.
- [RTK supported agents](https://github.com/rtk-ai/rtk/blob/develop/docs/guide/getting-started/supported-agents.md),
  retrieved through Context7; checked against installed `rtk init --help`.
- [Superpowers source](https://github.com/obra/superpowers/tree/bb92a77741419a4ab5f06e711a283343f1ada0c3),
  read from an official temporary clone at the recorded revision.
- Official OpenAI [configuration](https://learn.chatgpt.com/docs/config-file/config-basic),
  [hooks](https://learn.chatgpt.com/docs/hooks) and
  [skills](https://learn.chatgpt.com/docs/build-skills) references were opened;
  their mechanisms still require local client trials.
