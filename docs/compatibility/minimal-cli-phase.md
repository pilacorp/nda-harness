# Codex and Cursor CLI: Apple Silicon phase

The owner authorized implementation on 2026-10-14 with Claude and Intel deferred.
The shared framework and executable setup/verify/context operations are implemented.
Original broad client compatibility remains incomplete; manual/runtime checks
report pending or failed rather than claiming success from configuration writes.

## Install and use

Requirements: Apple Silicon macOS, Python 3.11+, Git, and at least one installed
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
are observed; a broken detected client can produce exit 1 after configuration.
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

Skills are copied completely so this phase does not depend on unverified symlink
discovery. Source licenses/provenance are preserved. Existing user/project skill
shadowing, user edits to owned content, malformed configurations, duplicate
instruction markers and destination symlinks require reconciliation. Unrelated
instructions and MCP entries remain intact; Codex TOML comments/formatting use the
pinned tomlkit 0.13.3 parser. Adding a family requires an adapter implementing
installation detection, paths, registration and manual checks, then one registry
entry. The shared engine, ownership transactions and runtime are reusable.

### Dependencies and manual completion

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
observed in every selected installed client can complete an auth-pending server
check as manual evidence; old observations cannot satisfy a new run.

Superpowers stays upstream-owned. Install through the supported client Plugins/
marketplace UI (Cursor: `/add-plugin superpowers`), then observe activation and
compatible skills. The source revision is
`bb92a77741419a4ab5f06e711a283343f1ada0c3` (manifest 7.0.0). A marketplace that cannot
pin or identify that revision remains pending; setup never edits undocumented
plugin caches, disables handlers or fabricates immutable marketplace pins.

After restart/authentication/trust/manual steps, run verify. It does not reinstall,
repair, activate hooks or rewrite agent/Git settings. It may run the explicit
unit command, produce ordinary test artifacts and save sanitized private readiness
receipts. Interactive verify asks for pass/fail/pending observations separately
for each installed surface; non-interactive verify cannot fabricate them. Missing
siblings are not required for machine readiness; selecting an unconfigured or
entirely absent family fails. Real release coverage is a separate matrix.

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
live checks by the agent. Python 3.11+ must be available in the actual GUI/client
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

Deferred: Claude, Intel macOS, native lifecycle registration, fully observed real
client compatibility, registry publishing, uninstall/upgrade commands, RAG/
Hindsight, automatic authorization validators and CI merge gates. These limitations
do not disable executable setup or its explicit context fallback.
