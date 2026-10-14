# Workflow

1. Run session-bootstrap and read full policy/profile/workflow plus skill discovery.
2. Explicitly select a role and issue-linked task record. Tech leads may draft an
   issue before a published record exists. Developers use the developer-spec
   template for specification drafting/review; no merged spec is needed to draft.
3. Before behavior-change implementation, independently verify live issue content,
   spec PR review/merge and matching local spec. Record references in the task file.
   Run task-prepare with `--stage implementation`. Helper metadata does not approve.
4. Execute focused unit TDD. Refresh after relevant code/spec/task/checkout changes
   and before dependent transitions. Update docs and keep concrete test evidence.
5. Save the task record with current revision/input fingerprint, stage, completed
   work, evidence, unresolved decisions and next action. Run context-checkpoint
   before compaction/handoff where possible. Resume through context-resume and
   revalidate actual local and remote state; do not restart completed work blindly.

Project-only pre-commit runs the existing pre-commit check before the configured
non-watch unit-test command. It blocks commits on failure and does not check
remote approvals. User setup does not activate Git hooks. Proposed RAG/Hindsight,
automated approval/CI gates, Claude and Intel support remain outside this phase.
