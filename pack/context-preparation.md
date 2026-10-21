# Context preparation

All five operations are available as plugin skills: session-bootstrap,
task-prepare, context-refresh, context-checkpoint and context-resume. Each skill
uses its client-bound packaged `bin/nda-plugin` helper from the resolved plugin
installation path; no global CLI or per-project pack is required. Pass the actual
Git worktree root, an explicit selected task record and a local session identity.

On entry check `.nda-harness/profile.json`. Ask for a non-watch test command in
agent chat when missing. Only explicit Skip stores `true`; absent input stays
pending. Local Git protection must also be activated in every clone. Commit only
project configuration there. Keep sanitized task records local under
`.nda-harness/tasks/`, add that directory to `.gitignore`, and never stage or
force-add it. Shared policy/skills stay in this plugin. Run nda-setup for recovery
and nda-verify for read-only checks.

The older `pack/scripts/prepare-context` helper remains an internal metadata
collector. Plugin context skills add clone-local protection checks around it.

Use `--role tech-lead` without a record for issue drafting. Task records must be
explicitly created/saved by the agent, never inferred from a branch name. They
use templates/task-record.md. Implementation requires a real local spec and
independent remote prerequisite checks; the helper never performs them.

JSON schema version 1 reports operation, status, checkout/branch/HEAD, dirty state,
input fingerprint, source/task/spec pointers, blockers and next checks. `ready`
means local metadata collection succeeded, not authorization. `needs_context`
means inputs changed. `blocked` means missing prerequisites. Exit 2 means blocked;
otherwise exit 0. Task preparation defaults to specification work; use explicit
`--stage implementation` before implementing. No Markdown text is executed.

Codex SessionStart/UserPromptSubmit and Cursor sessionStart provide startup and
freshness reminders; pre-compaction events are observational checkpoint reminders.
Cursor's startup event is asynchronous. Trust controls, missing hooks and startup
races require the explicit skill fallback; never claim ready from installation.
The helper needs Python 3.9+ on the actual client PATH,
not the installer's virtual environment. Pass `--session` with a non-secret local
session identity when available. Private locked state is keyed by worktree and
session; explicit task switches replace selection. No transcript, credentials,
semantic decisions, approvals or test logs are stored there.

To checkpoint, save `Revision`, `Input fingerprint`, `Stage`, `Evidence` and
`Next action` in the record. The fingerprint is returned by prepare/refresh;
task-record content is excluded from that fingerprint so saving the record does
not make it stale. Resume rereads artifacts and requires live remote checks.
