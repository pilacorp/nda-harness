# Context preparation

All five operations are available as plugin skills: session-bootstrap,
task-prepare, context-refresh, context-checkpoint and context-resume. Each skill
uses its client-bound packaged `bin/nda-plugin` helper from the resolved plugin
installation path; no global CLI or per-project pack is required. Pass the actual
Git worktree root, an explicit selected task record and a local session identity.

On entry check `.nda-harness/profile.json` for memory and `.nda-harness/config.json`
for the test command. Ask for a non-watch test command in agent chat when the
config is missing. Only explicit Skip stores `true`; absent input stays pending.
The bank id is the one stored in the profile. It is chosen on the Hindsight bank
page during setup, not derived from the Git remote or a project name. A missing
profile means run `select-bank`, then setup with `--bank-id`.
Local Git protection must also be activated in every clone. Commit
`config.json`. Keep the personal profile and sanitized task records local under
`.nda-harness/`, add `.nda-harness/profile.json` and `.nda-harness/tasks/` to
`.gitignore`, and never stage or force-add task records. Shared policy/skills
stay in this plugin. Run nda-setup for recovery and nda-verify for read-only checks.

The older `pack/scripts/prepare-context` helper remains an internal metadata
collector. Plugin context skills add clone-local protection checks around it.

Use `--role tech-lead` without a record for issue drafting. Task records must be
explicitly created/saved by the agent, never inferred from a branch name. They
use templates/task-record.md. Feature implementation requires a real local spec
and independent remote prerequisite checks. The five local context operations
never perform them. Follow workflow.md to resolve strict or fast mode from
the authenticated target branch at start, resume and dependent transitions.
Use the separate `workflow-check` command for fast evidence; a task record or
local config cannot authorize fast mode. The local test gate makes no such calls.
`Type: bugfix` mirrors the live issue's `bug` label or `Type: bugfix` body field
for the workflow.md bug-fix path; absent local Type means feature. At issue
creation, use templates/bug-issue.md and follow workflow.md's publishing instructions.
The agent must verify the live classification; a local field alone is insufficient.
Only `feature` and `bugfix` are valid values. A bug fix can start without a local
spec, but any recorded spec path must resolve safely. The agent must verify this
restores established intent and sync the related spec before completion. When no
related spec exists, add a concise behavior/regression spec with the fix. The
helper reports `task_type` and `spec_sync_required`; these are reminders, not
verified eligibility, completed spec sync or approval. Read Type again on resume;
changing it invalidates the context fingerprint.

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
