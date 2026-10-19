# Developer integration

Use [plugin installation](../INSTALLATION.md) for Codex Desktop, Cursor IDE, or
Claude Code Desktop. The approved [spec](../specs/harness-plugins.md) is the
phase-0 delivery contract. No released CLI migration is required.

Each plugin includes the same engine, workflow and full skill assets. Superpowers
is pinned and bundled; RTK bootstraps under native trust controls; Context7 is a
native MCP registration. Python 3.11+ and Git must be on the GUI client's PATH.
Initial support is Apple Silicon macOS.

On project entry run session-bootstrap. Missing `.nda-harness/profile.json` means
answering the test-command question in chat or explicitly Skip (`true`, no tests).
Pending configuration blocks dependent implementation; diagnostic conversation stays
available. Commit project config and sanitized task records. Every clone activates
its local composed pre-commit hook; existing hooks and configured tests must pass.
Shared policy and skills stay in the plugin.

Use nda-verify before dependent work, especially during Cursor asynchronous startup.
Trust/installing/failed/pending states never imply ready. Use nda-setup to recover.
Verification does not repair, run tests or access memory content.

Read full packaged policy/workflow and applicable repo instructions. Developer work
needs the authorized tech-lead issue and an approved merged developer spec matching
local content before behavior-change implementation. The owner can explicitly
authorize exceptions. Hooks never authenticate roles or grant approvals.

Use task-prepare with an explicit task record, role and stage, then focused unit
Red → Green → Refactor and human review. Use context-refresh after relevant changes
and before dependent transitions. Verify live issue content and approval/merge
evidence; fingerprints cannot detect remote edits. Material behavior changes require
owner reconciliation and renewed specification review.

Before compaction/handoff update `.nda-harness/tasks/` with revision, stage, evidence
references, unresolved decisions and next action. Run context-checkpoint. On resume
or switching clients use context-resume and reconcile the current checkout/task.
Do not reconstruct authority from transcripts, branch names or memory. Explicit
skills remain the fallback for missing, disabled or delayed native hooks.

Hindsight is optional. Authenticate from plugin details using native MCP controls;
no provider settings or credentials belong in the harness. After authentication,
hindsight-memory automatically uses the configured project bank. Same-account clients
share it; dev/staging/prod are labels in that bank, with dev the default. Never
retain credentials or private logs. Outage permits available default client memory
without fabricated saves or automatic fallback-content synchronization later.

See [implementation evidence](compatibility/harness-plugin-implementation.md) for
executed runtime checks and remaining native UI/trust/expiry validation. Previous
[CLI integration guidance](compatibility/cli-developer-integration-historical.md)
is historical planning, not current installation instructions.
