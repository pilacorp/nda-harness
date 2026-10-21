# Codex, Cursor and Claude Code CLI: Apple Silicon phase

The owner authorized initial implementation on 2026-10-14 and extended it to
Claude Code CLI and Desktop's local Code tab on 2026-10-15. Intel remains deferred.
The shared framework and executable setup/verify/context operations are implemented.
Original broad client compatibility remains incomplete; manual/runtime checks
report pending or failed rather than claiming success from configuration writes.

## Install and use

Requirements: Apple Silicon macOS, Python 3.9+, Git, and at least one installed
surface for each selected family. The installer does not install coding agents or
Python, require admin access, launch agents, change client trust or edit shell
startup files. The pinned Python dependency is bundled: no pip, virtual environment
or dependency download on first use is required. Install once:

```sh
./install.sh
~/.local/bin/nda-harness setup
```

The default prefix is `~/.local`; use `./install.sh --prefix /another/prefix` for
another writable location. Use `nda-harness` directly when its bin directory is
on PATH; otherwise the printed absolute command works immediately. The source
checkout may be removed after installing the CLI. Clone-and-run also works with
`./bin/nda-harness setup`, without any bootstrap step.

Guided setup asks for agents, scope and project-only options. Supplied flags are
preserved; partial flags ask only for missing values. Complete examples:

```sh
./bin/nda-harness setup --agents codex,cursor --scope project \
  --project /path/to/repository --test-command 'npm run test:unit'
./bin/nda-harness setup --agents codex,cursor --scope user
./bin/nda-harness verify --agents codex,cursor --scope project \
  --project /path/to/repository
./bin/nda-harness verify --agents cursor --scope user
./bin/nda-harness setup --agents claude --scope project \
  --project /path/to/repository --test-command 'npm run test:unit'
./bin/nda-harness verify --agents claude --scope project \
  --project /path/to/repository
```

Project must be the actual Git worktree root. The command is explicitly executable,
must run non-watch unit tests and is run from that root by setup, verify and
pre-commit. Setup does not infer test runners. User scope rejects project/test
flags and activates no Git hooks. Verify rejects `--test-command` and reads the
installed profile. Missing flags without a terminal return an error instead of
waiting for input. Cancellation before application does not register integrations.

Exit codes: **0** all applicable checks complete; **1** runtime/configuration/test
failure; **2** invalid input, unsupported prerequisites or preflight conflicts;
**3** required manual observations pending; **130** interrupted. Failed checks take
precedence over pending ones. Setup normally exits 3 until real-session checks
can be automatically established; a broken detected client can produce exit 1 after configuration.
The existing Codex CLI on the trial host has a missing executable, so repair that
agent installation separately before its runtime checks can pass.

## Installed behavior

Project pack: `.nda-harness/`. User pack: `~/.nda-harness/pack/`. Both include
policy/workflow, complete specialist skills/resources/licenses/provenance, the
developer-spec template, context/task templates, six hook guides and their index,
self-contained standard-library runtime and release hashes. Project scope adds
the explicit test-command profile and Git gate. Pack files and project entrypoint
references can be committed and moved with the checkout.

| Adapter | Project scope | User scope |
| --- | --- | --- |
| Codex | Managed block in root AGENTS.md; complete skills in .agents/skills; owned MCP entry in .codex/config.toml | Managed block in CODEX_HOME/AGENTS.md (default ~/.codex); skills in ~/.agents/skills; MCP in CODEX_HOME/config.toml |
| Cursor | Always-applied .cursor/rules/nda-harness.mdc; complete skills in .cursor/skills; MCP in .cursor/mcp.json | Skills in ~/.cursor/skills; MCP in ~/.cursor/mcp.json; exact User Rules block supplied in installed cursor-user-rules.md for a manual settings step |
| Claude Code CLI / Desktop local Code tab | Managed block in root CLAUDE.md; complete skills in .claude/skills; HTTP MCP entry in root .mcp.json | Managed block in ~/.claude/CLAUDE.md; complete skills in ~/.claude/skills; HTTP MCP entry in ~/.claude.json |

Claude's local Code tab uses the shared files documented by
[Claude Desktop](https://code.claude.com/docs/en/desktop#shared-configuration).
The MCP entry explicitly sets `type: http`, as required by the
[MCP configuration format](https://code.claude.com/docs/en/mcp). Setup preserves
other JSON entries and existing CLAUDE.md content. It leaves settings, permissions,
trust decisions and upstream hooks intact. Chat/Cowork and remote Code sessions
are outside this adapter. Desktop-only and CLI-only installations are accepted;
each detected surface receives its own pending fresh-session checks.

Skills are copied completely so this phase does not depend on unverified symlink
discovery. Source licenses/provenance are preserved. Existing user/project skill
shadowing, user edits to owned content, malformed configurations, duplicate
instruction markers and destination symlinks require reconciliation. Unrelated
instructions and MCP entries remain intact; Codex TOML comments/formatting use the
pinned tomlkit 0.13.3 parser. Adding a family requires an adapter implementing
installation detection, paths, registration and checks, then one registry
entry. The shared engine, ownership transactions and runtime are reusable.

### Dependencies and manual completion

Existing Homebrew RTK 0.40.0 is also accepted when its binary checksum matches
the observed Apple Silicon build recorded in `pack/dependencies.json` and its
version probe matches. Setup reuses it without downloading or replacing RTK.
Other builds remain conflicts until their identities are reviewed. This does not
change the pinned download or claim new native-hook compatibility.

The RTK compatibility fix passed 63 unit tests, including reuse without downloads,
hash/version mismatch rejection and refusal to execute an unknown binary. A live
test of the updated installed CLI with the host's RTK 0.40.0 created the expected
Claude project files in a disposable checkout. Automatic verify passed the RTK
check and preserved MCP configuration; both commands returned 3 for outstanding
session checks. The existing installed CLI bundle was backed up before replacement.

RTK 0.37.2 is pinned. Setup reuses recognized compatible executables; otherwise
it leaves existing versions/identities unchanged and reports a conflict. If
absent, it downloads the official Apple Silicon archive, verifies archive and
executable hashes, and installs once at `~/.nda-harness/bin/rtk`. The installed
RTK awareness file is the exact output of upstream `rtk init --codex` at this
version. Instructions require using RTK; no custom rewriting hook is added.
This is an **instruction fallback**, not a claim of automatic rewriting. The
upstream Cursor initializer's global-only/Claude side effects are not reproduced.
When the binary is not on GUI/CLI PATH, use the printed absolute path or configure
PATH locally and confirm behavior in the fresh session.

Context7 registers the official remote endpoint under `nda-harness-context7`,
without headers, literal keys or client trust changes. Authenticate through the
client's supported MCP flow, keeping credentials in its private store. Where
available, Codex uses `codex mcp login nda-harness-context7`; Cursor CLI uses
`agent mcp login nda-harness-context7`; desktop uses its MCP connection settings.
These are manual bindings awaiting target-client validation. Verify performs
bounded public initialize/tool-list/library-resolution/documentation requests.
Auth errors remain pending; rate, network and interface errors are failed. A
direct server request never proves client loading. A current successful retrieval
in a fresh client remains a separate check; old observations cannot satisfy a new run.

Superpowers stays upstream-owned. Install through the supported client Plugins/
marketplace UI (Cursor: `/add-plugin superpowers`), then observe activation and
compatible skills. The source revision is
`bb92a77741419a4ab5f06e711a283343f1ada0c3` (manifest 7.0.0). A marketplace that cannot
pin or identify that revision remains pending; setup never edits undocumented
plugin caches, disables handlers or fabricates immutable marketplace pins.

After restart/authentication/trust/manual steps, run verify. It does not reinstall,
repair, activate hooks or rewrite agent/Git settings. It may run the explicit
unit command, produce ordinary test artifacts and save sanitized private readiness
receipts. With complete flags, verify runs automatically, including on a terminal,
and never asks for pass/fail observations. It checks installed asset and registration
hashes, RTK identity, public Context7 retrieval, the configured project unit command,
and CLI version probes. Claude additionally runs bounded `claude auth status --json`
with closed stdin and retains no raw output or account fields. Its authentication
result applies only to the CLI, never Desktop. Missing
siblings are not required for machine readiness; selecting an unconfigured or
entirely absent family fails. Real release coverage is a separate matrix.

Setup shows a separate Context7 MCP step. Missing harness connections are added
automatically using the selected adapter's scope; existing matching entries are
reused, and unrelated servers are preserved. Newly added connections show the
client's approval/authentication instructions. Context7 is a hosted MCP service,
so no separate local server installation is required.

Setup and verify print only verification counts and the path to the private
`verification.json` report. Individual checks, failure details and pending client
steps are saved there with evidence sources and a timestamp, rather than printed
to the terminal. Reports have mode 0600 in the private state directory. Exit codes
are unchanged, including failures and pending session checks. The configured
project unit command still executes automatically with captured output.

This minimal automatic check does not start model sessions or approve trust.
Policy/skill discovery, authenticated client MCP retrieval, pinned Superpowers
activation, actual RTK usage and GUI Python/PATH behavior still need fresh-session
validation. Until supported automated diagnostics cover those checks, they stay
`awaiting_manual` and the overall command returns 3 even when machine checks pass.
Running setup again does not resolve these pending checks.

### Git gate, context and recovery

The project Git gate uses private per-worktree wrappers: original pre-commit
first, harness unit command second; other executable Git hook events pass through
with their arguments and worktree working directory. Either failure blocks the
commit and preserves staging. Later hook-manager changes require reconciliation.
Multiple worktrees require pre-existing `extensions.worktreeConfig=true`; the
installer refuses unsafe shared configuration and never enables it silently.
With that extension, hooksPath is worktree-local, leaving siblings unchanged.

All five context operations run through the installed `scripts/prepare-context`.
Read the installed context-preparation guide for role/task/stage/session arguments,
checkpoint fields and JSON meanings. Native lifecycle hooks are explicitly
deferred; entrypoint instructions require the helper/procedure before dependent
work. No helper contacts GitHub, infers approval or writes semantic task records.
Dirty source/spec, task or checkout changes invalidate context; resume requires
live checks by the agent. Python 3.9+ must be available in the actual GUI/client
PATH; installed helpers never import tomlkit or the source checkout.

Private receipts/backups live under `~/.nda-harness/state/<worktree-hash>/` (user
scope has its own key). Atomic application records created paths, original
backups, written hashes and prior effective Git hook registration. Reruns create
no duplicate registrations or backups when inputs are unchanged. Failed apply
restores only still-matching writes; subsequent edits are preserved and reported
in recovery-needed.json. A shared RTK executable is retained during recovery.

For manual recovery, inspect receipt.json and its recovery entries. Before
restoring a backup, check the current file's SHA-256 matches written_sha256;
otherwise reconcile the user edit first. Restore existing file permissions from
the recorded old mode. Remove an installer-created file only after the same hash
check. Restore git.previous_local_value at git.scope only if the current value
still equals git.written_value; if the previous value was absent, unset the local
override so the original effective hook directory applies. Preserve upstream
plugins/handlers and shared binaries. No uninstall command is provided.

After cloning an adopted project, run setup locally. An exact-release pack may
be adopted without previous private receipts; changed/unknown content conflicts.
Git activation, dependencies, credentials/trust and private receipts do not
transfer in Git. After `install.sh`, the source checkout may be removed; the
installed command retains its full bundle for setup/verify. Installed Git/context
hooks remain independent even of the CLI bundle.

## Validation and remaining evidence

Run `python3 -m unittest discover -s tests -v`. Tests use temporary homes,
repos and controlled commands, with network responses mocked in the normal suite.
They cover guided/partial/full input, both scopes, TOML preservation, ownership
conflicts/reruns, checksum rejection, safe recovery, public MCP error/protocol
handling, actual disposable Git commits, original/other hook preservation,
worktree isolation, independent installed runtime, stale context, checkpoint and
cross-session resume. A synthetic adapter verifies registry extensibility without
changing the engine. Client model sessions are not launched by the test suite.

An actual CLI smoke run on 2026-10-14 used a temporary home/Git repository and
`setup --agents cursor --scope project --test-command true`. It installed 379
hashed pack assets, preserved private scope, verified the existing RTK executable,
completed live public Context7 resolution/documentation and passed the unit
command. It returned exit 3 for the remaining per-client observations, as required.
No personal configuration was installed or changed by that run.

Claude extension evidence on 2026-10-15:

- `python3 -m unittest discover -s tests` passed all 61 tests. New cases cover
  Claude project/user registration, preservation/reruns, conflicting MCP entries,
  independent CLI/Desktop detection, automatic verification on a terminal,
  authentication failure/timeout handling and sanitized receipts. Installer/hook
  tests mock RTK provisioning/identity so the suite is independent of host RTK.
- Real disposable-home CLI runs used Claude Code `2.1.263`, detected Desktop
  `2.19675.1`, and the official checksum-verified RTK `0.37.2`. For both scopes,
  setup and verify completed automatic checks without stdin and returned 3 for
  outstanding session checks; the unauthenticated scratch CLI stayed pending.
  Rerunning setup changed zero files; verify preserved the MCP configuration.
- Live public Context7 resolution/documentation and CLI version checks passed in
  both scopes; project unit execution and Git registration checks passed. Desktop
  detection establishes presence only. No model session, GUI interaction, plugin
  installation, trust approval or personal configuration change was performed.
- The initial host RTK `0.40.0` was outside the recorded identities, so the first
  smoke run used a pinned binary on its temporary PATH. A subsequent setup fix
  records that Homebrew build's checksum/version and reuses it unchanged.

| Acceptance area | Phase evidence |
| --- | --- |
| AC-01–04 | Guided zero-flags user flow, partial/full flags, duplicates, invalid flags and non-interactive errors tested |
| AC-05, AC-07–08 | Registrations/resources installed; RTK archive verified; actual per-client loading/auth/plugin checks remain pending |
| AC-06, AC-10 | Preservation/reruns, malformed TOML, conflicts, symlinks, concurrent destination edits, failure rollback and checksums tested |
| AC-09 | Real commits permit/block, preserve staging/original hooks and isolate worktree settings |
| AC-11–14 | Isolated tests; bootstrap/recovery docs; complete template, guides and executable logical hooks installed |
| AC-15, AC-17–18 | Explicit selection, local spec checks, dirty changes, sanitized output, durable checkpoint, cross-session resume and standalone runtime tested; live approval checks remain agent-performed |
| AC-16 | No upstream plugin handlers are modified; actual joint output delivery remains pending |
| AC-19–20 | Original trial retained; owner authorized this phase; setup/verify report honest automated/manual readiness; broader release claims remain pending |

Deferred: Intel macOS, native lifecycle registration, fully observed real
client compatibility, registry publishing, uninstall/upgrade commands, RAG,
Hindsight server deployment/lifecycle hooks, automatic authorization validators and CI merge gates. These limitations
do not disable executable setup or its explicit context fallback.

Optional Hindsight setup now offers an explicit Enable/Skip menu, selected harness
agents, a multi-bank MCP URL and hidden personal-key input. Connections are
user-private even in project scope; instruction blocks follow the chosen scope.
Setup takes the root `/mcp/` endpoint without a bank question. The agent lists
existing banks and reuses a suitable bank or creates one when needed, passing
`bank_id` explicitly to memory tools.
The pack also ships coding-agent, multi-agent-orchestrator and research JSON
templates with a native-MCP application guide. Instructions select the appropriate
template for new banks; existing banks are preserved. Template files participate
in release hashes, and verification discovers the needed bank/model/directive tools
without applying templates remotely.
Shared ownership supports reuse and confirmed rotation across repositories. Keys
remain in owner-only client configuration and private backups, outside Git.
Automatic verification checks authenticated initialization, bank-management tool
discovery and `bank_id` on recall/retain, without listing/creating banks or reading
or writing memories. Fresh-session client loading and
instruction execution remain pending, including Cursor's User Rules paste step.
See [installation](../../INSTALLATION.md#optional-hindsight-memory) for the flow.
