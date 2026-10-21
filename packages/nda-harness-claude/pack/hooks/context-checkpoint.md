# H-05: context-checkpoint

## Trigger and support

Before compaction/handoff or a meaningful boundary. Scope: project and user. Phase: Codex, Cursor and Claude Code (CLI and Desktop local Code tab) on Apple Silicon macOS.
Real desktop/CLI loading remains pending in the compatibility report; all context
operations are executable through the explicit entrypoint fallback. Native event
registration is not claimed or installed in this phase.

## Implementation and registration

Checks that an explicitly saved durable record contains current Revision and Input fingerprint, Stage, Evidence and Next action. Does not write semantic task records.

Source: `hooks/pre-commit` plus `scripts/unit_check.py` for H-01;
`scripts/prepare-context` plus `scripts/context_runtime.py` for H-02–H-06.
`release.json` records installed asset hashes and the source revision.
H-01 uses the private per-worktree wrapper directory configured by setup.
Context fallbacks are required by the installed agent instructions; no agent
plugin files or unrelated lifecycle handlers are rewritten.

## Inputs, outputs and order

H-01 reads `profile.json` and executes only its explicit unit-test command;
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
scripts/prepare-context context-checkpoint --project /path/to/repository --task .nda-harness/tasks/4-cli/task.md
```

Checkpoint with an absent/stale record; save current fields and repeat. Expected result: Missing/stale fields return blocked. Compaction cannot be technically prevented by the fallback.
Linked specification cases: TC-25, TC-27, TC-28. Runtime works independently of the installer
checkout/virtual environment and from a different working directory.

## Recovery and privacy

The agent saves its current repository record and retries. No transcripts or fabricated decisions are synthesized.

Repair client Python/PATH locally and retry if the launcher reports a prerequisite
error. Restore only recorded files/Git settings still matching written hashes;
never overwrite subsequent user edits. Existing Superpowers/RTK handlers remain
untouched. Private context state contains hashes/selection/source identity only,
not credentials, raw transcript/Markdown bodies, approvals or test output.
