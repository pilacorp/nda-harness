# Minimal NDA Harness setup CLI

Owner follow-up: project setup appends missing exact `__pycache__/` and
`*.py[cod]` entries to an existing root `.gitignore`, preserving its contents,
line endings and permissions through the normal backed-up transaction. Repeated
setup does not duplicate entries or claim ownership of unrelated ignore rules.
Do not create a missing `.gitignore`, change one in user scope, or ignore the
shared `.nda-harness/` pack. Verify remains read-only for `.gitignore`.

Owner follow-up: guided `setup` and `verify` use Up/Down selection menus for
missing agent/scope options. Space toggles agents (initially unchecked, at least
one required); Enter confirms agents or a single scope. Highlighting a scope
alone does not confirm it. Unsupported terminals fall back to numbered choices
(comma-separated numbers for agents, one number for scope). Invalid/empty choices
reprompt. Cancellation restores the terminal and exits 130 before installation.
Flags, prompt order, project/test text prompts and non-terminal errors are unchanged.

Owner follow-up: when project scope is selected interactively without `--project`,
detect the current folder's Git worktree root, including from nested folders, and
require confirmation through Use detected root / Choose another folder. Choosing
another folder or running outside a Git worktree asks for an explicit root path.
Explicit `--project` takes precedence and retains strict root validation;
non-terminal runs still require the flag. No installation occurs during discovery
or confirmation. Show the complete detected path, falling back to numbered
selection if it would be truncated in the keyboard menu.

Status: merged specification (PR #5); owner-authorized Codex/Cursor/Claude Apple Silicon
phase implemented; real-client validation pending.

Owner amendment on 2026-10-15: extend implementation to Claude Code CLI and
Claude Desktop's local Code tab. Verification must run automatically, with minimal
machine checks acceptable. With complete flags, `verify` never asks for manual
observations, even on a terminal; checks without an automated diagnostic remain
explicitly pending (exit 3). This supersedes the interactive observation flow
below. Intel and full real-session compatibility coverage remain deferred.

Owner follow-up on 2026-10-15: keep detailed verification output out of the
terminal. Setup/verify print a compact summary and save the complete sanitized
results in private `verification.json`. Setup includes an explicit Context7 step,
adding missing MCP registrations and showing connection instructions while
preserving existing matching registrations and unrelated servers.

Phase amendment authorized by the owner on 2026-10-14: implement the shared
framework now for Codex and Cursor on Apple Silicon macOS; defer Claude and Intel
macOS to later adapters/phases. The owner also confirmed tech-lead review of PR
#5. This instruction permits implementation despite incomplete original trial
coverage. Keep actual client/authentication/plugin/native-hook checks explicitly
pending; do not claim the original all-six-surface/two-architecture release matrix
is complete. The original requirements below remain the target for later phases.
For this phase, ship executable logical context operations with explicit
entrypoint fallbacks, preserving upstream integrations. See
[phase implementation and evidence](../docs/compatibility/minimal-cli-phase.md).

Feature issue: [pilacorp/nda-harness#4](https://github.com/pilacorp/nda-harness/issues/4) (`Refs #4`).

## Source reference and approval

- Issue updated at: `2026-10-13T11:32:47Z`.
- Issue-body SHA-256: `abad1b7520e382cc562ea1fcf1abc7d27ef62fe9ead1a1573b8e8980379fcecd`, calculated over the UTF-8 GitHub `body` string without normalization.
- Repository sources: [README](../README.md), [implementation plan](../plan.md), [developer integration](../docs/developer-integration.md), and [skills catalog](../skills/catalog.md), consulted at `ddcb5aebcf1a5086b2101d70c1735a28db219933`.
- Specification branch: `specs/minimal-cli`, explicitly requested by the owner instead of the issue-numbered branch convention.
- Owner follow-up on 2026-10-13: require a reusable developer-spec template, implemented/documented hooks, and concrete test cases; explicitly include session bootstrap, task preparation, context refresh, checkpoint, and resume. These additions are now reflected in the feature issue; the source reference above records the aligned issue content.
- Context-hook design source: [context preparation proposal](../docs/context-preparation-hooks.md); adopt its five logical operations and trust boundaries. RAG and memory lifecycle hooks remain deferred; optional Hindsight MCP setup is covered by the amendment below.

Recheck the issue content before implementation. Material differences require reconciliation and renewed review of this spec. A spec-only PR references the issue without closing it. Spec-PR review and merge precede implementation; only the accepted implementation PR closes #4. This document does not claim approval or completed client validation.

## Outcome and boundaries

Deliver one local setup command for macOS developers who already have Cursor, Codex, or Claude installed. It imports the three existing specialist skills and a reusable developer-spec template, adds minimal harness instructions, installs/configures RTK and Superpowers, configures Context7 MCP, and implements/registers the hooks below with documentation for each.

Support Cursor IDE/CLI, Codex desktop/CLI, and Claude Desktop's **local Code tab**/Claude Code CLI. Local desktop/CLI configuration is shared where the client supports it; each surface still requires its own fresh-session check. Support both Apple Silicon and Intel macOS using matching dependency artifacts.

Include SDD workflow instructions, the developer-spec template, and agent-performed prerequisite verification: the agent checks issue linkage, spec-PR review and merge, and matching local spec content before behavior-change implementation. The five context lifecycle operations and their supported native hooks are included to gather local facts, identify pending checks, and support this procedure.

Exclude agent application installation, cloud/remote sessions, Claude Chat/Cowork, Linux/Windows, registry publishing, uninstall/upgrade commands, RAG and Hindsight server deployment/lifecycle hooks, the full role-specific SDD skill suite, automated remote approval validators, and CI merge gates. These exclusions do not remove the SDD instructions or prerequisite checks described above. Do not launch agents, create commits, or publish PRs during setup.

V1 relies on agent compliance and human review for approval requirements; it does not technically prevent an agent from bypassing them. Local hook diagnostics, including a `blocked` helper status, are not an approval-enforcement mechanism. The Git pre-commit hook separately blocks failing unit-test commits; it does not verify spec approval or authorize implementation.

## CLI contract

```sh
# Guided setup
./bin/nda-harness setup

# Partial flags: prompt only for scope and project-specific options
./bin/nda-harness setup --agents codex,claude

# Fully specified project setup
./bin/nda-harness setup --agents cursor,codex,claude --scope project \
  --project /path/to/repository --test-command "npm run test:unit"

# Fully specified user setup; no project or Git hook
./bin/nda-harness setup --agents codex --scope user

# Verify an existing installation without reinstalling it
./bin/nda-harness verify --agents codex --scope project --project /path/to/repository
```

| Option | Contract |
| --- | --- |
| `--agents` | Comma-separated `cursor`, `codex`, and/or `claude`; at least one; deduplicate repeated valid IDs. |
| `--scope` | `project` or `user`. |
| `--project` | Required for project scope; existing Git worktree root, including a linked worktree. Resolve to an absolute path and reject a supplied subdirectory rather than silently adopting its parent. |
| `--test-command` | Required for project scope; nonempty, explicitly supplied non-watch unit command. Do not infer it from manifests or claim to statically prove that an arbitrary command runs unit tests. |
| `--help` | Explain both scopes, prompts, prerequisites, side effects, exit codes, and examples without changing anything. |

When stdin is a terminal, prompt for missing required options in this order: agents, scope, then project and test command for project scope. Discover the Git worktree root from the current directory and offer it for explicit confirmation, including when invoked from a subfolder; otherwise ask for a root path. Allow choosing another folder. Do not default agent selection or scope. Reprompt invalid interactive answers; invalid supplied flags are errors. Do not prompt for values already supplied. Reject project-only flags in user scope with a usage error.

Without a terminal, list missing required flags and exit before any changes. Fully specified flags skip option-selection prompts; they do not bypass client trust, authentication, or application approval steps. EOF or cancellation during option collection leaves the machine unchanged. Interruptions after installation starts retain recoverable completed changes and report them on rerun.

Both commands use exit `0` only when the applicable checks are complete, `1` for installation/configuration/verification failures, `2` for invalid input or unsupported prerequisites/conflicts found before application, `3` for otherwise valid configuration awaiting authentication, restart, trust approval, or required fresh-session checks, and `130` for interruption. Failure takes precedence over pending checks. A configuration write alone is not onboarding completion; setup can finish applying changes and still exit `3`.

### Verification command and completion flow

Implement `verify` beside `setup`, reusing option validation, adapter checks, and result formatting. It accepts `--agents`, `--scope`, `--project`, and `--help`. Missing options prompt in the same order as setup, except it never asks for a test command; project verification reads that command from the installed profile. Reject `--test-command` for verify. Non-terminal execution with missing required options exits `2` without waiting for input.

`setup` applies configuration and immediately runs the applicable machine-checkable verification steps. It prints remaining manual actions and the equivalent `verify` invocation for completing them. After restarting the client, authenticating, or granting required trust, the developer runs `verify` to reassess the existing installation. Rerunning setup is not required to record a completed manual check.

`verify` never installs/upgrades dependencies, rewrites agent settings, activates hooks, repairs files, or changes Git configuration. It may run bounded diagnostic commands, a generic public Context7 query, and the explicitly configured unit-test command, which can create the project's normal test artifacts. It may update sanitized private readiness receipts. Report a failed/missing installation with a setup/reconciliation instruction rather than repairing it silently. Neither command launches an agent or changes its trust approvals automatically.

For each selected, installed surface, verify pack/template/runtime integrity, effective instruction/skill/MCP/hook registrations, dependency identity/version, runtime prerequisites, and a current Context7 resolution/documentation request. CLI runtime inspection can be automated only where the tested client exposes a supported diagnostic. Otherwise print a surface-specific fresh-session checklist for policy/template discovery, RTK command rewriting, Superpowers activation, Context7 retrieval, and context-hook coexistence/fallback. Ask for the observed result of each applicable check only when stdin is a terminal; show the expected observable result, and record the response as a **manual observation**, never an automated measurement. Skipped/not-observed checks stay pending; an observed failure stays failed. A non-terminal run cannot fabricate or solicit a manual result and exits `3` when such checks remain.

Readiness summaries retain `verified`, `failed`, and `awaiting_manual`, but identify the evidence source for each result (`automated` or `manual observation`). Store only check ID, source, timestamp, a non-secret result summary, installed versions, and the relevant configuration/asset fingerprints. Do not store raw transcripts, prompts, credentials, or test logs. Receipts are an audit aid: each verify run repeats live machine checks, and old manual observations do not prove fresh-session behavior; require new observation in the current run for checks without a supported automated diagnostic. Version, registration, pack, runtime-path, or configuration changes invalidate the affected evidence.

### Release support versus machine readiness

Release acceptance covers all six surfaces in both scopes on the supported macOS architectures. Individual setup/verify runs cover only the selected agent families and the surfaces actually installed for those families. Detect installed desktop applications and CLI executables, display the detection result, and verify each installed surface once even when it shares configuration. A selected family with no installed surface is an actionable prerequisite error. An absent desktop or CLI sibling is listed as “not installed; not checked” and does not cause exit `3` or prevent success for an installed sibling. An installed surface at an untested version is reported as unsupported/pending validation, not assumed compatible or silently upgraded.

For example, `--agents codex` on a machine with only a supported Codex CLI can complete verification without Codex desktop. Installing desktop later requires another verification run before claiming that new surface ready. This does not waive release-wide desktop coverage.

## Implementation structure and installed pack

Use Python 3.11+ with `argparse`, standard file/process libraries, and `unittest`. The **installer CLI (setup/verify) only** uses one pinned `tomlkit` dependency for preserving Codex TOML while editing owned entries; do not implement a TOML parser or serialize unrelated settings from scratch. Owner amendment on 2026-10-14: users install the CLI and run directly without manually installing Python packages. Bundle the checksum-verified pure-Python dependency with its license/provenance, load it without pip or a virtual environment, and provide `install.sh` for the complete local command bundle. Clone-and-run must also work directly. Installed harness hooks remain self-contained standard-library runtimes and never import `tomlkit` or depend on the CLI distribution. Missing/old Python or a damaged bundle produces an actionable prerequisite error; setup must not install Python or require administrative access.

Keep one setup engine and three small adapter modules. The engine collects validated options, checks prerequisites/conflicts, copies assets, applies backed-up writes, installs shared dependencies, and produces readiness results. Adapters supply instruction/skill/MCP registration, supported dependency integration, and verification/manual steps. A simple adapter registry is sufficient; no dynamic plugin framework or agent runtime is needed.

Planned source groups: `bin/nda-harness`, `scripts/nda_harness/` for the engine and adapters, `pack/` for rules/templates/dependency pins, and `tests/` for isolated checks. Existing `skills/` remains the canonical specialist source.

Project pack root is `<project>/.nda-harness/`; user pack root is `~/.nda-harness/pack/`. Both contain:

- `policy.md` and `workflow.md`: minimal shared rules and lifecycle instructions.
- `templates/developer-spec.md`: reusable developer specification template, installed in both scopes.
- `context-preparation.md`, `templates/context-brief.md`, and `templates/task-record.md`: shared context procedure, brief, and durable handoff structure.
- `scripts/prepare-context` plus its Python helper and any required local modules: a self-contained installed context runtime, available independently of native hook support and the installer checkout.
- `hooks/README.md` and individual hook guides: trigger, registration, behavior, failure handling, verification, and recovery contracts.
- `skills/catalog.md` and the full `ui-ux-pro-max`, `vietnamese-official-wording`, and `diagram-design` directories.
- `release.json`: harness revision, installed asset hashes, and dependency revisions.

Project scope also adds a small `profile.json` containing the explicit unit-test command, default spec location `specs/`, and task location `.nda-harness/tasks/`, plus `hooks/pre-commit`. Machine-specific settings, credentials, configuration backups, and operation receipts live under `~/.nda-harness/state/`, not inside the committed project pack. Project receipts are keyed by the resolved worktree path so linked worktrees do not share hook state accidentally. User-scope context hooks use the active repository's profile and task records when available; otherwise they report an unadopted checkout and pending project prerequisites rather than inventing a profile or installing Git hooks.

Copy all skill data, scripts, references, templates, licenses, and provenance. Generate the installed discovery catalog from the existing stable IDs and metadata; its local links must resolve inside the installed pack. Keep references to wider architecture documents as source URLs rather than broken relative links. Do not preload specialist bodies into instruction entrypoints.

The shared policy requires an issue before developer behavior-change work, a reviewed-and-merged developer spec before implementation, unit Red → Green → Refactor, human review, RTK for shell output, and relevant public library documentation through Context7. Explain the lighter documentation-only path. Harness workflow takes precedence over conflicting Superpowers workflow advice; neither skills nor setup authorizes an approval or stage transition. Do not present these instructions as technical enforcement of approval.

### Installed hook runtime and adoption after cloning

Implement the canonical installed context runtime under `pack/scripts/`: a small `/bin/sh` launcher named `prepare-context`, its Python helper, and only the standard-library local modules it requires. Copy these files completely into `<installed-pack>/scripts/` in both scopes. Resolve the helper/modules relative to the launcher's own installed directory, independently of the caller's working directory; pass the project root explicitly. Python-based parts of the pre-commit check follow the same standard-library-only rule. Preserve executable permissions and include all runtime files in release hashes.

The launcher locates `python3` in its execution environment and checks Python 3.11+ before invoking the installed helper. Quote launcher/helper paths and preserve arguments without evaluating them as shell source. A missing or older interpreter produces an actionable error explaining the Python/PATH prerequisite; it does not install Python, fall back to the source checkout, or claim context readiness. Setup verifies interpreter availability in the actual tested hook environments, including GUI-launched sessions, and documents any developer-local PATH action rather than silently editing shell startup files. A native adapter surfaces runtime errors through the client's supported diagnostics and retains the entrypoint fallback; a pre-commit runtime error blocks the commit.

Installed harness hooks must run after the installer checkout and its virtual environment are removed. They must not require `PYTHONPATH`, an activated virtual environment, symlinks into the installer, or third-party Python packages. No virtual environment is created per target repository. This restriction concerns the harness hooks/helper; vendored specialist skills and upstream RTK/Superpowers retain their separately documented runtime requirements.

After cloning an adopted project, committed pack files and relative skill links remain portable, but machine-local Git hook activation, dependency installation, trust approvals, and private receipts do not transfer. Each developer runs setup from an available installer clone to verify prerequisites and activate integrations for that checkout/worktree. An exact pack matching its committed release hashes may be adopted without an existing local ownership receipt: preserve those bytes, initialize a new private receipt, and create the local registrations. Changed/unknown pack content remains a conflict rather than being overwritten. Do not auto-activate hooks merely because the pack is present in Git. The temporary installer clone may be removed once setup is complete.

## Developer-spec template

Implement the canonical Markdown template at `pack/templates/developer-spec.md`; copy it unchanged into each installed pack's `templates/` directory. Entrypoints and workflow instructions direct developers to use it for `specs/<feature>.md`, adapting to an existing repository spec location when agreed with its owner. Setup installs the template; it does not generate a feature spec, invent an issue, or overwrite an existing developer spec.

The template contains short guidance and explicit placeholders for:

1. Title, draft/review status, feature issue URL, issue update time and body fingerprint, consulted source revisions, and spec branch.
2. Outcome, task classification (behavior change or lighter documentation/mechanical path), in/out of scope, and constraints.
3. Observed current behavior and the proposed behavior, including relevant callers and user-visible failures.
4. Implementation approach, changed interfaces/configuration, data flow, compatibility, and recovery where applicable.
5. Stable acceptance IDs (`AC-01`, etc.) mapped to the feature issue's criteria.
6. Concrete test cases with ID, setup/input, action, expected result, test layer, and acceptance IDs; distinguish planned tests from executed evidence.
7. Hook changes, including links to each hook's documentation, affected agents/scopes, triggers, failure behavior, and fallback where relevant; allow an explicit “none” for tasks without hook changes.
8. Documentation impact, rollout/rollback, and QA/manual scenarios where applicable.
9. Open decisions, risks, and proposed exceptions; unresolved items remain visible rather than fabricated as decisions.
10. Spec-PR review/merge references and implementation handoff. Review/merge fields remain unset until the corresponding GitHub events occur.

Use the same stable section headings in all copies. Guidance must explain that the GitHub issue owns feature intent and the developer spec defines implementation, rather than maintaining a second competing feature spec. No approval validator, spec scaffolding command, or new skill is required for this template deliverable.

## Agent adapters

| Family | Project registration | User registration |
| --- | --- | --- |
| Codex | Managed block in root `AGENTS.md`; skill links in `.agents/skills/`; Context7 in `.codex/config.toml`. | Managed block in `~/.codex/AGENTS.md`; skill links in `~/.agents/skills/`; Context7 in `~/.codex/config.toml`. Honor an explicitly configured `CODEX_HOME` for Codex-owned files. |
| Claude | Managed block in root `CLAUDE.md`; skill links in `.claude/skills/`; Context7 in `.mcp.json`. | Managed block in `~/.claude/CLAUDE.md`; skill links in `~/.claude/skills/`; Context7 through Claude's supported user MCP registration. |
| Cursor | Owned always-applied `.cursor/rules/nda-harness.mdc`; skill links in `.cursor/skills/`; Context7 in `.cursor/mcp.json`. | Skill links in `~/.cursor/skills/`; Context7 in `~/.cursor/mcp.json`; provide an exact block for supported User Rules settings. Where no supported scriptable rule mechanism exists, report the UI step as pending. |

Use relative skill links in project scope so a committed adoption works in another checkout. User links point to the installed user pack. Verify symlink discovery per client; if a tested client cannot discover links, its adapter copies complete skill directories and tracks their hashes instead. No registration may point into the maintainer's source checkout.

Instruction blocks use unique `nda-harness` begin/end markers. A rerun updates only an unchanged, previously owned block. Existing user text stays intact. Unknown files, malformed or duplicate markers, matching skill-name conflicts, and user edits to owned content require reconciliation instead of overwrite. Detect simultaneous project/user skill registration and client precedence; do not create duplicate Codex selectors or silently let a different user skill shadow the installed project skill.

Do not write to Cursor's internal settings database or invent a global rule-file path. Manual settings are a supported pending step, not verified installation. Document project trust, application restart/new session, and MCP permissions needed by each tested surface.

## Dependencies and readiness

Keep a reviewed dependency manifest with exact RTK release/artifact hashes, an immutable Superpowers revision, and pinned setup Python dependencies. Select those concrete pins through the compatibility trial below and commit them before implementing the full installer. Never resolve `latest` or execute instructions from mutable remote Markdown at setup time; supported marketplace paths must record the exact observed plugin revision and any pinning limitation rather than claiming a mutable marketplace name is an immutable pin.

### Compatibility trial before full installer implementation

Run a small integration trial in disposable test repositories/user profiles before building the full setup engine. Do not use a maintainer's personal configuration as an automated test fixture. Test one explicitly chosen version of Cursor IDE/CLI, Codex desktop/CLI, and Claude Desktop local Code tab/CLI in both installation scopes. Record native hook and Superpowers output coexistence, GUI hook Python/PATH behavior, and authentication/trust steps, not merely successful file writes.

Commit the trial results in `docs/compatibility/minimal-cli.md` and the resulting dependency pins in `pack/dependencies.json`. Each surface/scope row records macOS version/architecture, client version, dependency revision, exact supported install/initialization command or manual UI procedure, configuration location, authentication and secret-storage mechanism, restart/trust requirements, verification procedure, observed result, and limitation/fallback. Use the same matrix for release validation on both supported architectures. Missing access or an unresolved method is explicitly pending and cannot establish support.

Use upstream RTK agent initialization and supported Superpowers plugin installation, with no custom substitutes. Use Context7's remote MCP endpoint; choose **one tested authentication and credential-storage mechanism per adapter/scope** from supported client/upstream mechanisms. Replace the conditional authentication guidance with those exact bindings when the trial is complete; do not let installer code guess OAuth flows, header syntax, or precedence between project and user servers. Document manual-only plugin/authentication approvals and exact command flags accepted by the pinned versions. If a selected scope cannot preserve credentials or achieve activation through a supported path, return the limitation to the issue owner before promising support.

The trial is a prerequisite deliverable, not completed evidence in this spec. Its results must settle integration bindings and pinning limitations before the full installer implementation proceeds; release remains gated on the complete real-client matrix. Dependency/client updates require rerunning affected trial rows rather than silently widening the supported-version claim.

**RTK:** reuse an existing compatible executable after checking identity/version; leave incompatible or ambiguous installations unchanged and report the mismatch. If absent, download the pinned official macOS artifact, verify its checksum, and install into a user-writable harness bin directory. Complete RTK's documented agent initialization for the selected scope (for example, its `rtk init` integration), preserving existing configuration. Use the upstream-owned automatic rewriting where supported; otherwise retain the upstream-documented instruction fallback. Installing the binary alone does not enable automatic rewriting, and RTK runs on supported shell commands rather than as a continuously running service. An instruction fallback is reported as such, not as verified automatic rewriting. Do not modify shell startup files; report any required PATH action and use the absolute executable path in integrations.

**Context7:** configure the official remote MCP endpoint `https://mcp.context7.com/mcp` under a unique owned server name, `nda-harness-context7`, using the exact adapter/scope authentication binding established by the compatibility trial. Never place a literal key in project configuration, a command-line argument, or output. If the tested client requires stored headers, place them only in its private user-local configuration with restrictive permissions; keep the project definition non-secret and document the effective scope. No authentication-bypass or invented client interpolation syntax is allowed.

Verification initializes MCP, lists tools, resolves a public library, and retrieves a focused documentation excerpt using the returned library identifier. Use only a generic public query, with bounded waits and sanitized errors. Successful configuration or a successful direct server request does not prove the agent loaded the connection; require a fresh-session client check as well. Authentication errors, rate limits, unavailable coverage, and network failures are distinct failures. A missing credential is an actionable authentication/manual step, not an empty documentation result. The hosted service itself cannot be pinned; record its endpoint and observed tool interface separately from pinned local artifacts.

**Superpowers:** install and enable the upstream-supported plugin/integration for each family and selected scope, pinned to the reviewed revision where supported. Once activated, its own bootstrap and skill triggers apply automatically in matching sessions; do not require a separate harness hook or manual invocation on each task. Preserve an existing compatible installation; do not silently upgrade, replace, or duplicate it. Native marketplace approval or installation that is only available through a UI is an explicit manual step. Do not edit undocumented plugin caches to automate it. Verify the installed revision and bootstrap/skill loading in a fresh session; a downloaded directory alone is insufficient.

Print a concise component summary using `verified`, `failed`, or `awaiting_manual`, with evidence source and actionable next steps as defined in the verify contract. Cover pack/configuration, RTK binary and per-agent usage, Context7 retrieval and per-surface loading, Superpowers, and the project hook when applicable. Differentiate installed surfaces within each selected family even when they share files; absent siblings are listed outside required readiness checks. Readiness receipts contain versions and non-secret check summaries only. A rerun rechecks deterministic configuration; an old receipt never proves current runtime loading. Desktop/CLI observations belong in the validation record and remain pending until actually exercised.

## Configuration and hook safety

Perform input validation and a complete local configuration/conflict preflight before copying assets or registering anything. Identify selected family installations from executables and standard application bundles; at least one local surface must exist per selected family. A missing sibling surface is shown as not installed/not checked, not pending local readiness, and is never automatically installed. Parse JSON/TOML before edits. Stop on an existing different server definition, unknown asset ownership, unwritable paths, or unsupported hook configuration.

Write through sibling temporary files and atomic replacement. Preserve original permissions and back up changed existing files under the private state directory before replacement. Track created paths, original hashes, new hashes, and local Git configuration needed for recovery. Reruns with unchanged inputs perform no duplicate writes or backups. Existing compatible unowned entries may be reused unchanged after verification; incompatible entries are conflicts. Never follow a destination symlink to overwrite a user-owned external file.

The Git hook uses the explicit profile command through `/bin/sh -c` from `git rev-parse --show-toplevel`. Quote paths independently from the command; storing a command in JSON must not turn it into generated shell source. Test-runner failure or missing profile aborts the commit. Do not change staging, stash files, disable hooks, or execute test commands during mere input collection. Setup must explain that the supplied command is executable and run the command once to verify it after registration.

Inspect the effective `core.hooksPath` and existing hook tooling. Preserve all existing hooks by installing an owned wrapper directory per worktree: pass through other existing hook events; for `pre-commit`, run the original executable first and then the harness check, propagating either failure. Store the original effective hook directory and registration so reruns do not wrap the wrapper. Apply `core.hooksPath` only at repository-local scope; for linked worktrees, use Git's worktree-local configuration when supported, without modifying sibling worktrees. Refuse configurations that cannot be safely composed. Preserve the prior hook working directory and arguments, and document that later hook-manager changes require setup reconciliation.

Configuration failure attempts to restore only files still matching this run's written hashes and its own Git config changes. Do not overwrite intervening user edits or remove an RTK binary/plugin that another setup may use. Report partial external installations accurately and provide backup/receipt paths. Cancellation and recovery must not expose credentials. The manual rollback guide restores recorded files and the previous effective hook configuration only after checking for subsequent edits; no uninstall command is added.

## Hook implementation and documentation

Implement six NDA Harness hooks: the project pre-commit check and the five context lifecycle operations explicitly requested by the owner. Implement executable behavior and registration/composition tests; prose or a copied config file alone does not satisfy the hook deliverable. Implement the five context operations through one shared local helper and thin native adapters, retaining entrypoint instructions as the required fallback. RTK and Superpowers are upstream dependency integrations, not additional NDA Harness hooks: their supported installers/plugins own command rewriting and automatic skill activation. Setup enables and verifies those integrations once in the selected scope; do not add custom RTK rewriting, a second Superpowers bootstrap, or per-session opt-in.

| ID / guide | Trigger and scope | Required implementation | Failure / unsupported behavior |
| --- | --- | --- | --- |
| H-01 / `hooks/pre-commit.md` | Git pre-commit in an adopted project/worktree; never installed by user-only setup. | Run the existing pre-commit first, then the explicit non-watch unit command from the Git root; propagate failures and preserve other hooks as defined above. | Runner errors, missing profile, or either failed check block the commit without altering staging; setup rejects unsafe hook composition. |
| H-02 / `hooks/session-bootstrap.md` | New session, clear, or opening an adopted checkout; both scopes. | Identify the actual worktree, branch, HEAD, dirty state, pack/profile, applicable instructions, and candidate task records. Emit a reviewed checklist and source pointers; require the agent to read full rules before task work. | Missing/modified required assets or conflicting instructions leave readiness unresolved; allow diagnostic conversation. No candidate or several candidates never selects a task from branch name alone. |
| H-03 / `hooks/task-prepare.md` | Explicit feature-issue drafting/review, developer task start, or task switch. | Accept explicit role/task selection and distinguish specification work from implementation. Developers verify the issue and sources; before behavior-change implementation, verify the issue-linked spec in `specs/` (or the configured location), reviewed-and-merged spec PR and matching local content. Produce a cited brief identifying the next permitted action. | Specification drafting/review may proceed without a merged spec. Missing, unreviewed, unmerged, changed, or unverifiable implementation prerequisites pause implementation; task switches discard old selection. Status questions do not implicitly start new tasks. |
| H-04 / `hooks/context-refresh.md` | Relevant input changes, dependent stage transitions, or explicit refresh. | Compare local fingerprints including dirty spec content; identify stale context and direct the agent to reread affected sources and revalidate remote issue/approval information at dependent boundaries. | Material spec/issue changes require reconciliation and renewed human approval; unchanged HEAD cannot prove freshness. Do not advance stages or mark old test evidence valid. |
| H-05 / `hooks/context-checkpoint.md` | Before compaction where supported, planned handoff, or meaningful stage boundary. | Check that the agent has saved a current repository task record with revision, recorded stage, evidence references, unresolved decisions, and next action; preserve a sanitized local reminder if needed. | Missing/stale records remain explicit. Never synthesize semantic decisions, approvals, or test results from a transcript; do not claim a native hook can prevent compaction where the client cannot. |
| H-06 / `hooks/context-resume.md` | Resume, post-compaction, or cross-agent handoff. | Reload policy/profile and selected task record; reconcile actual checkout/diff/spec with recorded state and rebuild the brief before dependent work. | Mismatches pause affected work for reconciliation; completed work is not restarted automatically, and resuming never upgrades a recorded stage or approval claim. |

Document exact native event names, registration paths, input/output schemas, timeout/exit semantics, and availability **for the tested client versions**, separately for desktop and CLI. Do not invent common native event names or claim that a plugin provides hooks on a surface where only skill loading was observed. Native-hook configuration must preserve the client's permissions and unrelated settings. Project/user coexistence must not execute an owned handler twice; where client precedence cannot establish this safely, stop with a conflict.

Implement `pack/hooks/README.md` as an index and one guide per hook listed above; install all seven Markdown files in both scopes, including the Git guide in user scope with its “project setup required” limitation. Each guide must include:

- Purpose, trigger, supported agents/surfaces/scopes, and tested versions.
- Executable source/upstream revision, registration location, and inputs/outputs.
- Execution order relative to existing hooks, working directory, timeout, and success/failure behavior.
- Configuration/example, prerequisites, activation/restart/trust steps, and explicit unsupported fallback.
- Verification command or disposable scenario, expected result, and linked test-case IDs.
- Troubleshooting, backup restoration/disable instructions that preserve existing hooks, and side effects/privacy limits.

The index links every registered hook to its guide and distinguishes native hooks from instruction fallbacks. Setup's summary links the relevant local guides. No lifecycle hook may grant approval, advance workflow stages, or inject credentials/external documentation as privileged instructions.

### Task preparation: merged-spec prerequisite

The implemented `hooks/task-prepare.md` guide and entrypoint fallback must describe two distinct paths:

- **Specification drafting/review:** a developer can understand the published issue, inspect code, and draft/review `specs/<feature>.md` before its spec PR is reviewed and merged. Tech-lead feature-issue drafting can also precede issue creation. A missing merged spec must not block the work required to create one.
- **Behavior-change implementation:** before Red → Green → Refactor, verify that the task's issue-linked developer spec exists under `specs/` (or the repository's configured spec location), its spec-only PR was reviewed and merged into the target base branch, and the local spec content matches the reviewed merged version. Record the spec path, PR URL, review/merge references, and merged content revision in the context brief/task record.

A local Markdown file, a reviewed-but-open PR, an unreviewed merge, or a task record claiming review/merge does not satisfy this prerequisite. A stale/mismatched local spec, material changes after review, or unavailable review/merge evidence pauses implementation and directs the developer to reconcile the spec or finish its review/merge. Apply the same check on task switches, resume, and dependent stage transitions. Documentation/mechanical tasks retain the recorded lighter path; any behavior-change exception requires explicit human-approved evidence rather than a silent bypass.

Repository owners restrict the required spec-PR review and merge permissions to tech leads through existing GitHub controls. This is an adoption prerequisite managed outside the CLI; setup does not configure branch protection or maintain a separate approver allowlist. The agent verifies that the spec PR was reviewed and merged and that the local spec matches its reviewed merged content, without independently checking reviewer identity or team membership. Changes to spec behavior require a new reviewed-and-merged spec revision before dependent implementation resumes.

The shared helper reports local spec presence/fingerprints and pending verification checks; the agent verifies spec-PR review and merge evidence through its existing authenticated GitHub tools and follows the instruction to pause when prerequisites fail. This requirement does not add network calls to native hooks or imply that v1 implements a deterministic approval/CI gate. Here and in the acceptance cases, “pauses implementation” describes required agent behavior, not a technical guarantee that the hooks prevent source edits.

### Shared context helper and durable state

Implement `scripts/prepare-context <operation> --project <root>` for `session-bootstrap`, `task-prepare`, `context-refresh`, `context-checkpoint`, and `context-resume`. Require explicit `--role tech-lead|developer` for task preparation and an explicit `--task <record-path>` for selecting/resuming a published task; tech-lead issue drafting may omit a task record. Other operations may use a prior explicit selection only when its worktree identity still matches. Native adapters derive the project from verified session working-directory metadata; malformed or missing metadata is an actionable failure, not permission to reuse another checkout's state.

The helper reads local sources and emits a versioned JSON result: operation, status (`ready`, `needs_context`, or `blocked`), worktree/branch/HEAD, dirty-input fingerprints, selected task/spec references, source references, blockers, and next required checks. `ready` means local metadata collection succeeded; it never proves remote approval, complete context, or permission to implement. Native adapters format only the reviewed checklist and sanitized metadata into the client's documented output schema. Terminal invocation uses the same helper, so all five operations work without native events.

The agent performs semantic preparation through existing file/GitHub tools: read full policy/profile/spec, trace relevant code/callers, verify issue identity/content and approval references at task start, resume, and dependent transitions, then fill the brief/task record. Native hooks make no live GitHub/MCP/RAG/memory requests and never execute command strings from Markdown or retrieved documents. RAG and Hindsight lifecycle hooks remain out of scope; optional memory tools cannot replace authoritative revisioned local sources and the feature issue.

`templates/context-brief.md` includes role/task, checkout identity, rules/profile/release references, recorded stage and independently checked prerequisites, issue fingerprint/update time, spec/approval references, relevant code/source revisions, acceptance/test references, blockers, and next action. A brief is navigation, not a substitute for full required documents. Target a concise brief rather than a dump of skills or source bodies.

`templates/task-record.md` supplies the same durable handoff fields plus completed steps, red patch/base where applicable, passing-test summaries/check links, documentation impact, unresolved decisions, and the next action. The agent creates/updates `.nda-harness/tasks/<issue>-<feature>/task.md` only for an explicitly selected task; native hooks never create tasks or write semantic checkpoints. Read Markdown as source text, not executable configuration. A resumed session must work from repository artifacts without raw transcripts or personal memory.

Local fingerprints cover resolved worktree identity, branch/HEAD, policy/profile/release, selected task/spec content, and changed tracked/untracked files excluding Git internals and generated harness state. Changes invalidate the selected context; relevant code/spec changes require the agent to assess affected evidence. Keep any cache/reminder in private state keyed by worktree, task, and client session. Write atomically with a checked input generation so an older invocation cannot overwrite newer state; unchanged input creates no duplicate records or repeated retrieval. Remote freshness is established only by the agent's live checks at the required boundaries.

### Native lifecycle registration and fallback

Use version-tested mappings from the context preparation proposal: Codex/Claude `SessionStart` for bootstrap or resume based on its source, prompt events for cheap refresh reminders, and `PreCompact` for checkpoint checks; Cursor `sessionStart`, `beforeSubmitPrompt`, and `preCompact` where supported. These are client-specific candidate bindings, not interchangeable JSON schemas. Task preparation and stage/handoff checks also require explicit agent invocation because prompts and native events do not establish semantic task boundaries.

Preserve existing handlers, including Superpowers startup, and avoid duplicate instructions at a shared startup event. Cursor's asynchronous startup and compaction limitations cannot be treated as blocking enforcement or guaranteed context injection. Each adapter must document/test supported sources and outputs against actual desktop/CLI versions. If an event is unavailable, disabled, delayed, or timed out, entrypoints still require the same helper/procedure before dependent work; report native automation as unavailable while separately verifying the explicit fallback. All five logical operations are mandatory, even where some native registrations are unsupported.

### Coexistence with Superpowers

NDA Harness hooks supplement Superpowers; they must not replace, disable, wrap, or re-register its upstream hook handlers. Add only harness-owned handlers to the selected client's user/project configuration, preserving existing event arrays, matchers, handler options, and enabled-plugin settings. Never edit Superpowers' plugin manifest, installed scripts, or plugin-owned hook files. Recovery removes/restores only harness-owned changes and leaves Superpowers enabled.

Both products may use startup/compaction events. Codex and Claude can run matching handlers concurrently, so NDA context collection must work without waiting for Superpowers bootstrap and must not depend on execution order or shared mutable plugin state. Test the two sets of outputs together, not just their configuration entries. Cursor runs matching hooks but merges output fields according to field-specific rules; do not assume that separate `additional_context` outputs are concatenated. If a tested client drops/replaces Superpowers context when NDA emits native context, keep Superpowers' native output untouched and use the NDA entrypoint/helper fallback for that event.

The upstream configurations differ by client: the currently inspected Claude hook uses `SessionStart` with `startup|clear|compact`, Cursor has a dedicated hook file, and the Codex plugin manifest declares `hooks: {}`. Resolve the actual hooks supplied by the pinned plugin/client rather than inferring Codex behavior from Claude's file or assuming an empty manifest field proves no runtime hooks. Record the inspected manifest/hook revisions and the observed startup behavior in the validation matrix.

No hook should inject an instruction to ignore or disable Superpowers. The existing policy precedence is intentional and limited: NDA issue/spec/human-approval requirements govern the project; Superpowers remains active for compatible planning, TDD, debugging, and other skills. Show this distinction in the installed policy and hook guides. Native context order is not an authority mechanism, and unchanged plugin files alone do not prove that both instruction sets reached the agent.

## Acceptance and test mapping

| ID | Issue criterion | Verification |
| --- | --- | --- |
| AC-01 | No-flags interactive project/user setup | Scripted terminal input exercises both flows, conditional questions, invalid-answer retries, EOF, and cancellation before mutation. |
| AC-02 | Partial flags preserve supplied options | Exercise each omitted option; assert supplied agents/scope/command are not asked again or altered. |
| AC-03 | Full flags equal guided setup | Compare resulting assets/configurations for all three adapters and both scopes; ignore receipt timestamps. |
| AC-04 | Missing options without a terminal fail | Assert exit 2, named missing flags, no hanging, and unchanged temporary home/repository. |
| AC-05 | Both scopes support all six surfaces | Real macOS matrix: six surfaces × two scopes; record OS/architecture, client/dependency versions, restart/trust steps, and observed limitations. |
| AC-06 | Reruns preserve settings without duplicates | Fixtures with unrelated instruction text, JSON/TOML servers, existing hooks, user edits, duplicate markers, skill conflicts, and simultaneous scopes; compare unrelated values and original file content where unchanged. |
| AC-07 | Fresh sessions load rules and discover skills | Each surface reads policy/catalog and executes one diagram assignment; a backend assignment loads no unrelated specialist bodies. Verify bundled resources resolve after relocating a project checkout. |
| AC-08 | RTK, Context7, and Superpowers work | Assert RTK identity/run, Context7 library resolution/documentation, and Superpowers bootstrap in each selected surface; exercise failed auth, rate limiting, timeouts, version mismatch, and pending UI steps. |
| AC-09 | Hook permits/blocks commits and retains existing checks | Disposable Git repositories: passing/failing unit commands, failing original hook, other hook events, paths with spaces, rerun, existing hooksPath, and linked-worktree isolation. Assert failed checks prevent commit creation. |
| AC-10 | Errors are actionable | Test unsupported OS/architecture, absent runtime/agent, invalid repository/flags, malformed config, unowned files/symlinks, checksum mismatch, interrupted install, and recovery with intervening edits. |
| AC-11 | Tests are isolated and real checks are recorded | Unit tests use temporary homes and repositories, fake subprocess/network responses, and no live personal configuration; separate opt-in macOS walkthroughs exercise actual clients. |
| AC-12 | Onboarding/recovery documentation exists | Walk through clone/bootstrap, guided/partial/full flags, scope choice, pins, secrets, restart/trust/manual steps, exit codes, and hash-aware backup restoration. |
| AC-13 | Owner addition: reusable developer-spec template | Both scopes install the complete canonical template; verify required sections, criterion/test mapping fields, placeholder approval state, resolved entrypoint links, and preservation of existing feature specs. |
| AC-14 | Owner addition: implement/document each harness hook | H-01 works in project scope; H-02 through H-06 each work through the shared helper and verified native mappings or explicit entrypoint fallback. All six harness hooks have installed guides, preserved registrations, and tests for behavior/failure paths. Upstream RTK/Superpowers activation is verified under AC-08 without duplicate custom hooks. |
| AC-15 | Owner addition: context lifecycle correctness | Bootstrap/prepare/refresh/checkpoint/resume respect explicit selection, dirty inputs, task/checkout changes, remote verification boundaries, durable checkpoints, and cross-agent handoff without granting approval or retaining sensitive content. |
| AC-16 | Superpowers coexistence | Setup/rerun/recovery preserve upstream plugin handlers and activation; shared events deliver both intended contexts without an execution-order dependency or silent output replacement. Use the NDA fallback for events whose output cannot safely coexist. |
| AC-17 | Task preparation requires a reviewed-and-merged spec PR before implementation | Specification drafting/review works without a merged spec; behavior-change implementation requires an issue-linked local spec matching the reviewed-and-merged PR. Missing, stale, unreviewed, unmerged, or unverifiable evidence pauses implementation across preparation/resume/transition paths. |
| AC-18 | Installed hook runtime is independent of the installer | Both scopes contain all required standard-library helper files; hooks work without the source checkout/CLI virtual environment. Missing Python 3.11+ is actionable, and newly cloned exact-release packs support explicit local adoption without destructive replacement. |
| AC-19 | Integration bindings are established by a compatibility trial | Trial results specify tested versions, pins, exact install/authentication/configuration methods, manual steps, and verification for each surface/scope; pending rows do not imply support. Full installer implementation uses those bindings instead of inventing them. |
| AC-20 | Verification completes installation without reconfiguration | Setup reports pending steps and a verify command; verify rechecks existing installation, records automated versus manual results, invalidates stale evidence, and verifies only selected installed surfaces. Exit codes distinguish verified, failed, invalid, and pending outcomes. |

### Concrete test cases

These are implementation requirements, not claims that tests already exist or pass. Automated cases run in temporary homes/repositories with subprocess/network fixtures unless a case explicitly requires a real client.

| ID | Layer / criteria | Setup and action | Expected result |
| --- | --- | --- | --- |
| TC-01 | Unit / AC-01, AC-03 | Supply terminal answers for one agent, project scope, a temporary Git root, and `true`; compare with equivalent flags. | Same owned assets/configuration; all four prompts appear only in the guided run. |
| TC-02 | Unit / AC-01, AC-02 | Supply `--agents codex --scope user`, then repeat with only `--agents codex` and answer `user`. | No project/test-command questions; both runs preserve `codex` and produce equivalent user configuration. |
| TC-03 | Unit / AC-02 | Supply agent and project flags, then answer the missing scope and test-command prompts. | Supplied values are unchanged and never asked again. |
| TC-04 | Unit / AC-04, AC-10 | Run with non-terminal stdin and missing required options. | Exit 2 lists missing flags; no pack, backup, download, or registration is created. |
| TC-05 | Unit / AC-01, AC-10 | Enter an unknown agent, retry with a valid agent, then send EOF before completing options. | Invalid answer is explained; cancellation leaves the temporary home and repository unchanged. |
| TC-06 | Unit / AC-06 | Start with unrelated instructions, MCP servers, and TOML comments; run identical setup twice. | Unrelated content survives; owned entries appear once; the second run adds no backups or wrapper layers. |
| TC-07 | Unit / AC-06, AC-10 | Modify an owned instruction block after setup, or create an unowned server with the requested name; rerun. | Preflight exits 2 with the conflicting path/entry; no user edit or other configuration is replaced. |
| TC-08 | Unit / AC-08, AC-10 | Return a wrong download checksum, failed MCP authentication, or a timed-out verification request. | Each failure is categorized and sanitized; no component is falsely marked verified and setup exits nonzero. |
| TC-09 | Integration / AC-09 | Register a project hook with `true`, stage a fixture, and commit in a disposable repository. | Hook runs from the repository root and the commit is created. |
| TC-10 | Integration / AC-09 | Repeat with `false`, a nonexistent test executable, and a missing profile. | Each commit fails; HEAD stays unchanged and staged files remain staged. |
| TC-11 | Integration / AC-06, AC-09 | Original pre-commit appends to a marker and exits 0; harness command appends a second marker. | Both markers appear once in original-then-harness order; repeated setup does not multiply execution. |
| TC-12 | Integration / AC-09 | Original pre-commit exits 1; harness command would create a marker. | Commit is blocked and the harness marker is absent; the original failure propagates. |
| TC-13 | Integration / AC-09 | Adopt a worktree whose path contains spaces; retain an existing other hook event and inspect a sibling worktree. | Paths and hook arguments work, the other event still runs, and the sibling's effective hook configuration is unchanged. |
| TC-14 | Unit / AC-13 | Install the template in project and user scopes; compare each with the canonical source. | Contents match, required sections and `AC-`/test-case fields exist, and no placeholder claims human approval. |
| TC-15 | Unit / AC-06, AC-13 | Create `specs/existing.md` before setup; install/rerun and resolve template links from entrypoints. | Existing spec stays byte-identical; both template paths resolve independently of the source checkout. |
| TC-16 | Manual / AC-05, AC-07, AC-08 | Open a fresh session in each surface/scope, follow restart/trust steps, select Diagram Design, run RTK, retrieve public docs, and load Superpowers. | Observe actual policy/template discovery, selected skill resources, and dependency behavior; record versions and evidence or pending/failure explicitly. |
| TC-17 | Unit / AC-06, AC-14 | Seed each adapter's supported native hook config with an unrelated handler; install the upstream RTK/Superpowers integrations and all six harness hooks twice and test project/user coexistence. | Existing handlers remain unchanged; each configured handler is registered/executed once or a scope conflict is reported before mutation. |
| TC-18 | Unit / AC-08 | Invoke the pinned upstream RTK integration with supported, unsupported, and failing handler inputs using controlled command fixtures. | Supported commands use RTK; unsupported commands retain upstream semantics; errors are visible and commands with side effects never execute twice. |
| TC-19 | Unit and manual / AC-07, AC-08 | Exercise upstream Superpowers startup with a valid integration, absent approval, duplicate registration, and hook timeout. | Successful bootstrap supplies the expected skill instructions once; missing/failed bootstrap stays pending/failed and does not mark readiness or approval. Confirm success in a real fresh session. |
| TC-20 | Unit / AC-12, AC-14 | Install both scopes and resolve the hook index, all six harness hook guides, context/task templates, summary links, and test-case references. | Every harness hook has a complete guide; user scope documents H-01 without activating it; all required artifacts and local links resolve. |
| TC-21 | Unit / AC-14, AC-15 | Bootstrap an adopted checkout, then remove its profile and repeat in a user-only unadopted checkout. | Correct identity/source pointers on success; missing profile is an explicit prerequisite, with no invented task or ready-to-implement claim. |
| TC-22 | Unit and manual / AC-15 | Prepare a developer task without an issue or with two candidate records; contrast tech-lead issue drafting and a status-only question. | Developer task requires explicit valid selection; tech-lead drafting can precede issue creation; no guessed task, new record, or stage transition for a status question. |
| TC-23 | Unit / AC-15 | Prepare a selected task, switch branch/worktree/task, and edit its spec without committing. | Identity/content fingerprints change; old context is invalidated even with unchanged HEAD; material changes require reconciliation. |
| TC-24 | Manual / AC-15 | Edit the GitHub issue or change remote approval while local files and HEAD stay fixed; resume or attempt a dependent transition. | Agent's required live boundary check catches the change/unavailable metadata; local cache cannot authorize dependent implementation. |
| TC-25 | Unit and manual / AC-14, AC-15 | Checkpoint with missing/stale task state, then save a current record and resume through a different agent after compaction. | Missing/stale state is reported; valid repository artifacts restore completed steps/evidence/next action without transcript parsing, stage advancement, or restarting completed work. |
| TC-26 | Unit / AC-14, AC-15 | Disable or time out native lifecycle hooks, including a Cursor-style fire-and-forget startup; invoke all five operations explicitly. | Helper/procedure still performs each operation; native failure is not readiness, and only documented output channels receive context. |
| TC-27 | Unit / AC-15 | Repeat unchanged preparation and race older/newer hook results for different tasks/worktrees. | No duplicate records or broad retrieval; state stays isolated and stale generations cannot overwrite newer selections/checkpoints. |
| TC-28 | Unit and manual / AC-15 | Include command-like text, credentials, or raw transcript content in input fixtures; inspect hook output, caches, and checkpoints. | No text is executed or elevated into privileged instructions; sensitive/transcript content is not copied into output/state and failures remain sanitized. |
| TC-29 | Unit / AC-06, AC-14, AC-16 | Use fixtures from the pinned Superpowers manifests/hook files; apply NDA setup twice, then restore only NDA changes. Repeat with Superpowers installed before and after NDA setup. | Plugin-owned files and handlers remain unchanged; plugin stays enabled; NDA handlers are unique and recovery leaves upstream activation intact. |
| TC-30 | Unit and manual / AC-05, AC-07, AC-16 | Fire shared startup/clear/compact events with both integrations; vary handler order/completion time and simulate NDA timeout or missing profile. | Superpowers bootstrap still runs where supplied; NDA collects independent metadata or reports its own pending state without suppressing Superpowers. Confirm both contexts in real fresh sessions. |
| TC-31 | Unit and manual / AC-14, AC-16 | Exercise Cursor response merging with distinguishable Superpowers and NDA startup context, plus project/user registrations. | Both contexts are observed or the adapter uses NDA entrypoint fallback; no last-response replacement is accepted as successful coexistence. |
| TC-32 | Manual / AC-07, AC-15, AC-16 | Start an unapproved behavior-change task with both products active, then run a compatible planning/debugging skill after satisfying prerequisites. | The agent follows NDA issue/spec approval instructions and pauses premature implementation while Superpowers remains discoverable/usable; no hook disables its plugin or skills. This walkthrough checks agent compliance, not deterministic enforcement. |
| TC-33 | Unit and manual / AC-13, AC-15, AC-17 | Prepare specification drafting/review for a published issue with no local or merged developer spec. | The next permitted action is drafting/review using the developer-spec template; no implementation permission or fabricated approval is recorded. |
| TC-34 | Unit and manual / AC-15, AC-17 | Request behavior-change implementation with a missing spec, reviewed-but-open PR, merged-but-unreviewed PR, mismatched issue link, changed local spec, or unavailable remote review/merge evidence. | Each case explicitly pauses implementation and lists the failed prerequisite; native metadata collection or task-record claims do not bypass the check. |
| TC-35 | Unit and manual / AC-15, AC-17 | Prepare implementation with an issue-linked spec at the default or configured location matching its reviewed-and-merged spec PR; then resume with a material spec change. | Initial brief records the verified path/PR/review/merge/revision and permits the next workflow action; changed content requires reconciliation and renewed approval before affected implementation continues. |
| TC-36 | Integration / AC-14, AC-18 | Install both scopes into temporary targets, remove the disposable installer checkout and its virtual environment, clear `PYTHONPATH`, and invoke all five context operations plus the project pre-commit check from a different directory using Python 3.11+ without third-party packages. | Installed runtime resolves only its own packaged modules; each operation executes with the expected metadata/prerequisite result, and the unit-test commit check runs independently of the removed installer. |
| TC-37 | Unit and manual / AC-10, AC-18 | Run launchers with missing/older `python3`, valid Python, and installed paths containing spaces; exercise a GUI-launched client with its actual PATH. | Missing/old Python yields a diagnostic and no false readiness; pre-commit blocks on runtime failure; valid paths/arguments work without shell expansion or an activated virtual environment. |
| TC-38 | Integration / AC-06, AC-09, AC-18 | Commit an adopted pack, clone into a new temporary home/repository with no receipts, and run setup; contrast a pack whose runtime file was modified. | Clone alone activates no machine-local Git hook; explicit setup preserves the exact-release pack, establishes fresh local activation/receipts, and verifies the runtime. Modified pack content produces a conflict rather than replacement. |
| TC-39 | Unit / AC-01, AC-04, AC-20 | Run verify with complete flags, partial flags, and terminal/non-terminal stdin; attempt to supply a test command. | Only missing applicable selection options prompt; verify reads the installed profile command, rejects `--test-command`, and missing non-terminal options exit `2` without hanging. |
| TC-40 | Unit and manual / AC-08, AC-20 | Finish setup with restart/authentication/trust checks pending; complete those steps externally and run verify with observed fresh-session results. | Setup exits `3` and gives the exact follow-up command; verify can complete with exit `0`, distinguishing manual observations from automated checks without reinstalling or rewriting agent configuration. |
| TC-41 | Unit / AC-05, AC-20 | Select Codex on a machine with CLI only, desktop only, both, or neither; add an untested installed version. | Supported installed surfaces alone determine readiness; missing siblings do not block it; neither installed is a prerequisite error, and untested versions are not silently marked supported. |
| TC-42 | Unit / AC-06, AC-20 | Snapshot config/Git/dependency files, run verify, then change a version/config fingerprint, revoke Context7 access, or rerun non-interactively with old manual receipts. | Verify does not repair/reconfigure installation; private receipts/test artifacts are the only expected local writes. Changed inputs invalidate affected checks, live auth failure is reported, and old manual observations cannot turn pending checks into success. |
| TC-43 | Unit / AC-08, AC-20 | Aggregate all-pass results, a pending manual check, a failed check, and a failure plus pending checks. | Exit `0` only for complete applicable verification; pending exits `3`; failed checks exit `1` and take precedence. Output shows each check's evidence source. |
| TC-44 | Manual and artifact checks / AC-05, AC-08, AC-19 | Execute the integration trial for six surfaces/two scopes and inspect its versioned matrix, auth bindings, pin manifest, and exact manual procedures; leave one row unresolved. | Completed rows have concrete reproducible methods and observations; missing/pending rows remain explicit and block the full support claim. Full installer implementation cannot proceed on guessed bindings. |

Use focused `unittest` tests for option collection, asset registration/ownership, JSON/TOML preservation, adapter plans, dependency failures, and readiness aggregation. Hook integration tests execute real Git commits in disposable repositories with controlled author settings and commands. Mock dependency downloads and MCP responses in normal tests; live queries use public inputs and a designated test account. Never install into a maintainer's real home as part of the automated suite.

Ship only after the supported-surface matrix is completed. Missing desktop access or UI approval leaves the relevant checks explicitly pending; source review and mocked tests cannot establish client compatibility. In particular, Cursor user-rule loading and pinned marketplace installation must be validated, not assumed from filesystem writes. If a supported surface cannot meet the issue, return the capability gap to the issue owner rather than silently narrowing support.

## Documentation and handoff

Update the README and developer integration guide during implementation to distinguish shipped minimal setup from the broader proposed harness. Add clone-and-run prerequisites, the setup-only virtual environment versus standard-library hook runtime, explicit adoption after cloning, setup/verify examples and completion flow, a tested adapter/capability table, credential handling, evidence-source/exit-code meanings, installed-surface readiness versus release coverage, and backup restoration. Retain proposed Phase 2/3 work as future scope.

The implementation PR must include concrete dependency pins, passing isolated test evidence, disposable hook trial results, the macOS validation matrix, and lifecycle walkthroughs covering all five operations plus native-hook failure/fallback, cross-agent resume, and Superpowers coexistence (configuration preservation and observed output delivery). This spec-only change adds no CLI, installer, hooks, dependency downloads, or client configuration.

## Integration references

Consulted on 2026-10-13; behavior must be rechecked against the client versions tested during implementation:

- [Codex local skill locations](https://learn.chatgpt.com/docs/build-skills) and [MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).
- [Claude skill configuration](https://code.claude.com/docs/en/skills) and [desktop shared configuration](https://code.claude.com/docs/en/desktop#shared-configuration).
- [Cursor skills](https://cursor.com/docs/skills), [rules](https://cursor.com/docs/rules), and [MCP](https://cursor.com/docs/mcp).
- [RTK upstream](https://github.com/rtk-ai/rtk), [Context7 upstream](https://github.com/upstash/context7), and [Superpowers installation](https://github.com/obra/superpowers#installation).
- [OpenAI hooks](https://learn.chatgpt.com/docs/hooks), [Claude hooks](https://code.claude.com/docs/en/hooks), and [Cursor hooks](https://cursor.com/docs/hooks); native mappings must be verified per client version/surface.
- Superpowers upstream coexistence inspection: [Claude startup hooks](https://github.com/obra/superpowers/blob/main/hooks/hooks.json), [startup output handler](https://github.com/obra/superpowers/blob/main/hooks/session-start), [Cursor manifest](https://github.com/obra/superpowers/blob/main/.cursor-plugin/plugin.json), and [Codex manifest](https://github.com/obra/superpowers/blob/main/.codex-plugin/plugin.json). These mutable source links inform the design; implementation tests must use the reviewed pinned revision.


## Owner amendment: optional Hindsight memory setup

Interactive `setup` offers an explicit Enable/Skip memory menu after existing
options and before installation writes. Enable offers an unchecked agent menu
restricted to the selected harness families, then a full multi-bank MCP URL
ending in `/mcp/` (or `/mcp`) and hidden personal API-key input. Do not ask for a
bank name or accept a bank-scoped endpoint. Use existing keyboard controls and numbered
fallback. Reject empty keys, whitespace/control characters, credential/query/fragment
URLs, and HTTP except loopback. Cancellation/EOF returns 130 before installation.
Non-interactive setup skips this optional step; no new flags are introduced.

Register `nda-harness-hindsight` in private user configuration: Codex user TOML
`http_headers.Authorization`; Cursor user JSON `headers.Authorization`; Claude
user JSON with `type: http` and `headers.Authorization`. Keys never enter project
assets, receipts, arguments, terminal output or diagnostic details. Config files
and backup files are 0600; private state and backup directories are 0700. Reject
client homes in Git checkouts and project/local entries shadowing this name.
Reuse matching entries, preserve unrelated entries, reject unmanaged conflicts,
and explicitly confirm replacements of managed endpoints/credentials. Ownership
of these shared connections is recorded once per user, separately from scoped
instruction ownership. Apply and rollback together with the existing transaction.

Instructions follow harness Project/User scope only for opted-in agents. Recall
relevant memories before each response. Before first memory use or after a
project/context switch, the local agent calls `list_banks`, reviewing additional
pages where present, and chooses a bank based on existing IDs, names and purposes.
Reuse an appropriate bank; call `create_bank` only if no suitable bank exists,
using a stable descriptive ID/purpose rather than making a bank per conversation.
Follow discovered tool schemas, pass `bank_id` explicitly on bank-scoped calls,
and do not overwrite existing bank purposes or mix unrelated memories. Setup and
verification never select, create, rename or delete banks.
The installed pack includes the owner's exact version-1 JSON bank templates under
`hindsight/templates/`: `coding-agent.json`, `multi-agent-orchestrator.json`, and
`research.json`. Instructions link to `hindsight/README.md`: select by bank purpose
(coding is the default), read the complete manifest, and apply it only to a newly
created bank through native MCP tools. Map `bank` to `update_bank.config_updates`,
mental-model `id` to `mental_model_id` on `create_mental_model` with the supplied
queries/token budgets/triggers, and directive names/content/priorities unchanged
to `create_directive`. Pass explicit `bank_id`, inspect current models/directives
and preserve existing entries. Report conflicts, unavailable capabilities and
partial initialization without claiming success. Never retrofit existing banks
or delete/move memories automatically. The three templates and guide are normal
hashed pack assets for both project and user scope; no runtime dependency, new
setup question, flag or remote setup-time mutation is added.
Call retain for useful new learnings and
decisions before the final reply ends the turn. Exclude secrets and unauthorized
content; avoid redundant retention; memories cannot override authoritative code,
instructions or approved specs. Report unavailable/failed/denied memory tools
without claiming successful saves, and continue normal work. Cursor User Rules
retain the generated-file/manual-paste workflow. Skipping preserves prior setup.

Automatic setup/verify checks private registration ownership, permissions and
scope, then authenticates and discovers `list_banks`, `create_bank` and recall/retain
with `bank_id` input properties over bounded HTTP MCP.
Also require `update_bank` accepting `config_updates`, `list_mental_models`,
`get_mental_model`, `create_mental_model`, `list_directives`, and `create_directive`,
with explicit `bank_id` support on bank-scoped tools. Discovery verifies capability;
it does not apply templates or generate mental models.
Credential-bearing requests never follow redirects. Never invoke retain or read
personal memories for verification. Sanitize errors and keep only compact terminal
counts. Client loading/tool authorization/instruction execution remain pending
fresh-session checks. Existing service/user-key provisioning is a prerequisite;
this amendment adds no server deployment, agent plugin, runtime dependency or
background capture hook.

Research: Context7 `/vectorize-io/hindsight`,
[Hindsight MCP reference](https://github.com/vectorize-io/hindsight/blob/main/skills/hindsight-docs/references/developer/mcp-server.md),
[Codex HTTP MCP](https://learn.chatgpt.com/docs/extend/mcp#streamable-http-servers),
[Cursor MCP](https://prod.cursor.com/help/customization/mcp),
and [Claude Code MCP](https://code.claude.com/docs/en/mcp).
