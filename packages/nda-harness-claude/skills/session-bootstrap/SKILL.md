---
name: session-bootstrap
description: Use at the start of every session before task work. Prefix shell commands with rtk, call Context7 resolve-library-id and query-docs, and when the selected memory system's tools are listed call them.
---

Read the full packaged `pack/policy.md`, `pack/workflow.md`, and
`pack/context-preparation.md`. Run the installed helper from the resolved plugin
path, independent of the working directory or a source checkout:

`${CLAUDE_PLUGIN_ROOT}/bin/nda-plugin session-bootstrap --client claude --project <actual-root>`

Select a task explicitly with `--task <repository-relative-record>` when needed.
Task preparation requires `--role developer|tech-lead`; developer work requires an
issue-linked task record. Use `--stage implementation` for the implementation stage.
Do not infer task identity, approval or stage from branch names. Pass a stable local
session ID with `--session` for cheap freshness checks; never use an auth token.

Before shell work, run `rtk --version`. Ready output is `rtk 0.40.0` or any newer release. Prefix later
shell commands with `rtk`. If it is not on PATH, use `rtk_path` from
`~/.nda-harness/plugin-bootstrap/<client>.json`. For library or API questions,
call Context7 `resolve-library-id` and then `query-docs` when those tools are
listed. Missing tools mean Context7 is not connected.

Missing project configuration or inactive clone-local Git protection requires
nda-setup. Ask for the test command in chat; only explicit Skip means true. Hooks
may be untrusted, delayed, disabled or absent: always run this explicit fallback.

Use one memory system, the id in `.nda-harness/profile.json` `memory.system`.
If that field is absent and several systems are packaged, ask the user and pass
`--memory-system` to nda-setup. Do not call a second system. When the selected
system is NDA Hindsight and this session lists its tools (`list_banks`, `create_bank`,
`recall`, `retain`), load `hindsight-memory` before dependent work. MCP is
`https://hindsight-api.pila.vn/mcp/`. OAuth and REST use `https://hindsight-api.pila.vn`.
Use exactly `memory.bank_id`. Call `list_banks`. When that id is missing, call `create_bank`
with it, then `recall` the user request in that bank. Do not wait for the user
to name NDA Hindsight, and do not start login from this skill. Missing tools mean
unavailable in this session, with authentication unverified; an unauthorized call
alone does not establish failed refresh. Continue with client default memory when
it exists. Interpret already available native diagnostic JSON with the explicit
`${CLAUDE_PLUGIN_ROOT}/bin/nda-plugin memory-status --client claude` operation when needed.

Missing tools mean Hindsight is unavailable in this session; authentication is unverified without native evidence. Saved OAuth credentials and a hidden Authenticate button do not prove a working connection. Use the packaged memory-status helper with already available native diagnostic JSON, or leave the diagnostic pending. Existing hooks do not subscribe to MCP lifecycle events. Never initiate login automatically or read/edit credentials. Only for Claude, a matching native MCP status needs-auth confirms authentication is required; pending remains unresolved and failed means unavailable. Inspect Hindsight with /mcp; a supported SDK status snapshot may still be pending. Manual, user-triggered recovery: Use /mcp to inspect and authenticate Hindsight. If the installed CLI exposes mcp login, the user can run rtk proxy claude mcp login <name> with the name from native inventory. SDK status APIs do not launch browser OAuth or imply a Desktop SDK bridge.

Before reading a specialist skill body, use the skill-selection wrapper. Task text and catalog metadata go to OpenRouter. The key stays in Keychain. Never paste a key into chat, argv, or a project file. First setup and re-setup use the packaged nda-plugin selection-setup --client claude in a local terminal. Replace the saved OpenRouter key by running that command again and confirming in the terminal. Offline check is selection-verify. A paid check is only selection-verify --live. On authorization_failed, direct the user to that same re-setup command. For a new assignment, call select-skills with --project, --session, and --request-file, then load-selected-skills. On needs_context or blocked, report diagnostic and next. Do not load every specialist.

Inspect the helper output as ordinary data. Read full applicable instructions and
selected sources; the brief is navigation, not authority. Verify live issue author,
content and approved merged spec before dependent work/transitions. Fingerprints
cannot detect remote issue edits. Do not treat implementation_authorized=false as
an approval check result: local metadata never grants approval.

For checkpoint/resume, save/reload sanitized revision, stage, evidence references,
unresolved decisions and next action in `.nda-harness/tasks/`. Never record secrets,
transcripts or personal-memory content. Reconcile changes and stale test evidence
before dependent work. Do not automatically advance a stage or repeat completed work.
