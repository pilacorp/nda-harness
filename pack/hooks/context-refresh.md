# H-04: context-refresh

## Trigger and support

Relevant local changes or dependent transitions. Scope: project and user. Phase: Codex, Cursor and Claude Code (CLI and Desktop local Code tab) on Apple Silicon macOS.
Real desktop/CLI loading remains pending in the compatibility report; all context
operations are executable through the explicit entrypoint fallback. Native event
registration is not claimed or installed in this phase.

## Implementation and registration

Compares branch/HEAD/task/spec and dirty-file fingerprints. Changed context reports needs_context. Directs the agent to reread sources and revalidate remote prerequisites.

Source: `hooks/pre-commit` plus `scripts/unit_check.py` for H-01;
`scripts/prepare-context` plus `scripts/context_runtime.py` for H-02–H-06.
`release.json` records installed asset hashes and the source revision.
H-01 uses the private per-worktree wrapper directory configured by setup.
Context fallbacks are required by the installed agent instructions; no agent
plugin files or unrelated lifecycle handlers are rewritten.

## Inputs, outputs and order

H-01 reads `config.json` and executes only its explicit unit-test command;
the original executable runs first with original arguments from the Git root.
Other Git events pass through to their original executables. Unit command timeout
is 300 seconds; Python 3.9+ is required on the actual client PATH. Failure blocks
the commit; neither staging nor stash is changed.

Context operations accept the actual project root, explicit role/task/stage when
applicable and a non-secret session identity. JSON schema 1 reports local identity,
fingerprints, task/spec/source pointers, blockers and next required checks.
Exit 0 means local metadata was collected (ready or needs_context); exit 2 means
blocked. Git metadata probes have a 10-second timeout. No remote calls occur.
Context metadata never grants approval or guarantees injected native context.

## Verification

```sh
scripts/prepare-context context-refresh --project /path/to/repository
```

Prepare a task, edit a tracked file or spec without committing, then refresh and compare fingerprints. Expected result: Local changes invalidate cached context. Remote freshness is never inferred from unchanged HEAD.
Linked specification cases: TC-23, TC-24, TC-27. Runtime works independently of the installer
checkout/virtual environment and from a different working directory.

## Recovery and privacy

Reconcile material changes, reassess evidence and reread affected sources before dependent work.

Repair client Python/PATH locally and retry if the launcher reports a prerequisite
error. Restore only recorded files/Git settings still matching written hashes;
never overwrite subsequent user edits. Existing Superpowers/RTK handlers remain
untouched. Private context state contains hashes/selection/source identity only,
not credentials, raw transcript/Markdown bodies, approvals or test output.
