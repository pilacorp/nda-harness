# H-06: context-resume

## Trigger and support

Resume, post-compaction or cross-agent handoff. Scope: project and user. Phase: Codex, Cursor and Claude Code (CLI and Desktop local Code tab) on Apple Silicon macOS.
Real desktop/CLI loading remains pending in the compatibility report; all context
operations are executable through the explicit entrypoint fallback. Native event
registration is not claimed or installed in this phase.

## Implementation and registration

Reloads explicit task/spec/source pointers, compares actual inputs and directs live prerequisite checks. Completed work/evidence must be reread from the task record.

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
scripts/prepare-context context-resume --project /path/to/repository --task .nda-harness/tasks/4-cli/task.md
```

Resume an explicit saved record from a different session identity, then change the checkout/spec and repeat. Expected result: Missing record blocks; mismatches require context reconciliation. Resume never advances stages or upgrades approval.
Linked specification cases: TC-24, TC-25, TC-26, TC-35. Runtime works independently of the installer
checkout/virtual environment and from a different working directory.

## Recovery and privacy

Read full task/source artifacts and independently recheck live issue/spec review/merge before dependent work.

Repair client Python/PATH locally and retry if the launcher reports a prerequisite
error. Restore only recorded files/Git settings still matching written hashes;
never overwrite subsequent user edits. Existing Superpowers/RTK handlers remain
untouched. Private context state contains hashes/selection/source identity only,
not credentials, raw transcript/Markdown bodies, approvals or test output.
