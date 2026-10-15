# Context preparation

All five operations use `scripts/prepare-context` installed in this pack. Run it
from any directory, passing the actual Git worktree root. For a project pack:

```sh
.nda-harness/scripts/prepare-context session-bootstrap --project /path/to/repository
.nda-harness/scripts/prepare-context task-prepare --project /path/to/repository --role developer --task .nda-harness/tasks/4-cli/task.md --stage specification
.nda-harness/scripts/prepare-context context-refresh --project /path/to/repository
.nda-harness/scripts/prepare-context context-checkpoint --project /path/to/repository --task .nda-harness/tasks/4-cli/task.md
.nda-harness/scripts/prepare-context context-resume --project /path/to/repository --task .nda-harness/tasks/4-cli/task.md
```

For user scope use `~/.nda-harness/pack/scripts/prepare-context`. User-only
unadopted repositories report a missing profile; run project setup separately.
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

This phase uses explicit agent-entrypoint fallbacks on Codex/Cursor desktop and
CLI. Native lifecycle events remain unregistered until client trials establish
safe output/coexistence. The helper needs Python 3.11+ on the actual client PATH,
not the installer's virtual environment. Pass `--session` with a non-secret local
session identity when available. Private locked state is keyed by worktree and
session; explicit task switches replace selection. No transcript, credentials,
semantic decisions, approvals or test logs are stored there.

To checkpoint, save `Revision`, `Input fingerprint`, `Stage`, `Evidence` and
`Next action` in the record. The fingerprint is returned by prepare/refresh;
task-record content is excluded from that fingerprint so saving the record does
not make it stale. Resume rereads artifacts and requires live remote checks.
