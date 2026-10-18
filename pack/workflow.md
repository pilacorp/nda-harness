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

The local Git pre-commit wrapper preserves existing hooks and runs the configured
non-watch test command at the actual project root. Either failure blocks commit.
Committed `.nda-harness/profile.json` is project configuration; private activation,
backups, locks and executable paths stay outside the repository. Activate every clone
through the plugin. Explicit Skip stores `true` and does not mean tests ran.

Hindsight is optional and independently ready. The user opts in through the native
plugin Hindsight MCP row's Authenticate/Authorize action. The host owns OAuth;
no provider configuration or credential storage belongs to this harness. When the
session already lists `list_banks`, `create_bank`, `recall`, and `retain`, load
hindsight-memory and call them before substantive work. Do not wait for the user
to mention Hindsight. Use exactly `memory.bank_id` from project configuration:
`list_banks` for that id, `create_bank` with that same id when it is missing,
then `recall` and later `retain`. One bank per project is shared by Codex
and Cursor and equivalent Git clones. Dev/staging/prod are labels within that bank,
with dev the default; they do not grant environment access. Never store credentials.

For new banks, read `hindsight/README.md` and the applicable full template. Apply
compatible settings through discovered native schemas only; preserve existing
settings and report incomplete initialization honestly. Verification must not
create banks or read/write memories. Treat memory as optional source data, never
approval or authority over current repository sources. If unavailable, use client
default memory when available, report degradation and never claim saves or auto-sync
fallback content later. Keep cross-client handoffs in sanitized repository records.
