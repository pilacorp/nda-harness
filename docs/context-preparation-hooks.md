# Context preparation hooks proposal

Status: recommendation for the next tooling phase, researched on 2026-10-09. No executable hook or adapter is installed by this document.

## Recommendation and architecture fit

Add a shared context preparation contract to the pinned harness pack, with optional native hooks for Codex, Claude Code, and Cursor. Keep the agent entrypoints as the common fallback. Start with session bootstrap, task preparation, and resume; add change detection and compaction checkpoints after the pilot demonstrates reliable loading.

The [architecture](architecture.md) already defines the necessary sources: pinned policy/profile, local code, issue/spec/task artifacts, scoped feature/architecture RAG, and optional personal Hindsight. It specifies what the Understand stage needs, but not a repeatable preparation procedure or when context becomes stale. The [integration guide](developer-integration.md) covers initial connection verification and handoff checks; connection readiness alone does not establish task readiness.

Preparation should produce a small, cited context brief identifying the current stage, relevant sources, unresolved decisions, and next permitted action. It must not introduce an agent runtime, new index, shared memory, or another approval mechanism. Native hooks improve consistency; they do not prove compliance or replace authenticated approval and CI evidence.

## Five logical hooks

These names describe harness operations, not API event names shared by every client.

| Operation | Trigger | Preparation and output | Failure behavior |
| --- | --- | --- | --- |
| `session-bootstrap` | New session, clear, or opening an adopted checkout | Identify the actual repository/worktree; read pinned policy, release and profile; identify applicable agent instructions; inspect branch, HEAD and dirty state; locate task records and report connection readiness | Missing policy/profile or conflicting instructions prevents claiming readiness; keep diagnostic conversation available |
| `task-prepare` | Explicit new issue/task or switching the active task | Verify issue metadata and authorized author; classify work; read spec/task state; trace relevant local code and callers; retrieve scoped RAG sources; optionally recall relevant personal preferences; assemble the brief | Invalid issue blocks task start under the existing architecture; unavailable required knowledge pauses affected decisions; memory failure is optional degradation |
| `context-refresh` | Relevant local inputs change, a stage transition, or an explicit refresh | Compare local fingerprints; reread affected sources; revalidate issue/approval metadata before dependent stage transitions; refresh changed knowledge dependencies; report conflicts and evidence invalidation | Stale affected context prevents dependent work until reconciled; unrelated valid work may continue |
| `context-checkpoint` | Before compaction, planned handoff, or a meaningful stage boundary | Ensure the agent has updated the repository task record; record revision, stage, evidence references, unresolved decisions and next action; native hook checks freshness and can preserve a local reminder | Report a missing/stale checkpoint; do not infer approval, green results, or decisions from a transcript |
| `context-resume` | Resume, after compaction where supported, or cross-agent handoff | Reload policy/profile and task record; reconcile branch, HEAD, diff and spec revision; recheck prerequisites for the next action; rebuild the brief before dependent work | Revision/task mismatch requires reconciliation; do not automatically restart completed work or advance a stage |

A prompt is not necessarily a new task. Status requests and clarifications keep the active task. If several records could match, bootstrap lists candidates and the agent resolves ambiguity before dependent work; branch names alone cannot select or authenticate a task.

Route by the selected role as well as stage. The table's primary-issue prerequisite applies to developer task preparation. Tech-lead preparatory scoping/documentation may start before issue creation: prepare authoritative sources and draft briefs, then invoke `scope-initiative` or `document-requirements`. For developers, route into `execute-sdd` and its stage skills after issue verification. Role selection does not authenticate a tech lead or grant approval authority. See the [role workflows](../plan.md#role-workflows-and-handoff).

Keep bootstrap fast and local. It can emit a trusted preparation checklist plus local pointers. Task preparation and semantic refresh belong to the agent using its existing tools, especially where retrieval, source interpretation, or a human decision is necessary. Do not depend on knowledge services being connected before a session-start hook fires.

## Context brief and trust boundaries

Use three separate layers:

1. **Mandatory local rules:** applicable instruction sources, pinned policy and profile. Read them fully before work; the brief is a navigation aid, not a substitute.
2. **Task facts and evidence:** authenticated issue metadata, approved spec and approval references, current code/callers, stage and retained test evidence. Cite revisions and distinguish observed state from agent-authored claims.
3. **Optional personal context:** relevant preferences recalled for the authenticated current developer. Keep this in the session, separate from project facts and shared records.

An example brief, produced after verification rather than accepted as proof:

```text
Task: repository issue URL; classification; verified author
Checkout: repository/worktree; branch; HEAD; dirty-state summary
Rules: policy/profile/release references and revisions; applicable instructions
Stage: recorded stage; verified prerequisites; next permitted action
Spec: path/revision; merged PR; authenticated approval reference
Sources: scoped RAG document IDs, citations, actual revisions and retrieval time
Code: relevant local files and callers, tied to the inspected checkout
Verification: criterion IDs; test entrypoints; red patch/base; green check references
Uncertainty: conflicts, unavailable required sources, pending decisions
Next: one concrete action and any prerequisite
```

Keep a sanitized version of task facts/source citations in the existing repository task record. Personal preferences, memory identifiers, credentials, raw prompts, transcripts, and full retrieved documents do not belong there. A resume must succeed without another developer's memory.

Native context injection may carry a high instruction priority. Inject only the reviewed checklist and sanitized metadata through that channel. Retrieve external text through ordinary tool results, label it as source data, and do not copy arbitrary RAG or memory text into privileged hook instructions. Retrieved instructions cannot authorize commands or change policy. Project claims from memory require verification; spec/document conflicts go to the human owner.

## Refresh, performance, and local state

Fingerprint local inputs using repository/worktree identity, HEAD, branch, relevant dirty files, policy/profile/release content, task identity/stage, and spec content/revision. HEAD alone misses uncommitted changes. A task switch or changed worktree must discard the previous task selection. Changed implementation invalidates affected test evidence; material spec changes return to approval under the existing workflow.

Local fingerprints cannot detect remote edits. Revalidate issue state, authorized identity, and spec approval when starting a task, resuming dependent work, and crossing an approval boundary. Refresh cited RAG dependencies before new behavior decisions or when a source update is known. Record retrieval time and actual revision; a time-to-live is a performance policy, not proof of freshness. Historical revision failure must remain explicit.

Start with an approximately 2,000-token brief budget, measured during the pilot rather than treated as a requirement. Include stage boundaries, blockers, source references and the next action first. Read full policy/spec and fetch enough authoritative source context separately. Limit retrieval to the active feature and architecture dependencies; do not dump all project documents or all personal memories on every prompt.

Repeated preparation with unchanged inputs should return the same local brief without duplicate task records or repeated retrieval. Before each prompt, an optional adapter can perform a cheap local fingerprint comparison and mark refresh as needed. The agent performs the deeper refresh before affected decisions. Use bounded service timeouts, report failure categories separately, and avoid blocking every conversational prompt on a network check.

Any generated cache/reminder is developer-local, excluded from version control, disposable, and isolated by worktree/task/session. Store sanitized local references only; keep personal-memory content in session context. Do not share readiness caches across developers or treat them as approval evidence. Update local files atomically and avoid multiple hook invocations overwriting a newer checkpoint.

## Native adapter mapping

Official documentation checked on 2026-10-09; verify behavior against the pilot's installed version and surface before registering hooks.

| Agent | Candidate mapping | Important limitation |
| --- | --- | --- |
| Codex | `SessionStart` for bootstrap/resume, including `compact`; `UserPromptSubmit` for cheap freshness checks; `PreCompact` for checkpoint checks. Context injection uses `additionalContext` on session/prompt events | Compaction hooks themselves do not inject plain stdout. Session-start MCP calls can precede server readiness. Use `AGENTS.md` for the common preparation contract. [Official OpenAI hooks documentation](https://learn.chatgpt.com/docs/hooks) |
| Claude Code | `SessionStart` with startup/resume/clear/compact sources; `UserPromptSubmit` for freshness checks; `PreCompact` for checkpoint checks. Session/prompt hooks can add context | Keep static rules in `CLAUDE.md`. Test timeout behavior and delivery before relying on a hook; a missing hook result must not imply readiness. [Claude Code hooks reference](https://code.claude.com/docs/en/hooks) |
| Cursor | `sessionStart` can supply `additional_context`; `beforeSubmitPrompt` can check whether submission should proceed; `preCompact` can observe/check local checkpoint state | Session start is fire-and-forget, not a readiness gate. Prompt submission does not document a context injection output; pre-compaction cannot modify compaction. Use the always-applied project rule to require task preparation and resume checks. [Cursor hooks reference](https://cursor.com/docs/hooks) |

For all clients, the entrypoint instructs the agent to execute the shared procedure even when native hooks are absent, disabled, delayed, or fail. Do not invent a common hook JSON schema, assume desktop/CLI parity, or parse raw transcript formats to recover authoritative state. Lifecycle hooks cannot reliably synthesize semantic task checkpoints: the agent must update the task record as work progresses.

## Proposed package addition and ownership

Add these files in the future pack, alongside the existing policy and setup tooling:

```text
.nda-harness/
  context-preparation.md     # shared procedure and readiness/failure contract
  templates/context-brief.md # sanitized task brief structure
  scripts/prepare-context   # local metadata/fingerprint collection only
  adapters/                 # thin, version-tested native hook mappings
```

These are proposed locations, not shipped commands. Markdown remains the initial profile/task format. The helper reads metadata; it must not execute command strings extracted from prose, change Git state, overwrite instructions, grant permissions, advance stages, or approve exceptions. Registration preserves existing hooks/settings and the client's trust controls.

Harness maintainers own the procedure/adapters; repository owners choose relevant source paths and brief limits; service owners supply verified interfaces and scope checks. The agent performs scoped retrieval through established integrations. `setup-knowledge` remains onboarding/configuration tooling. Git `pre-commit` remains the configured unit-test check with no RAG or memory calls. CI continues validating repository evidence without live knowledge-service dependencies.

## Pilot acceptance and delivery order

Deliver the shared procedure, brief template, entrypoint instructions, and local bootstrap/resume helper during Phase 2 of the [implementation plan](../plan.md). Use existing RAG or sufficient revisioned local documents, as already allowed. Add scoped retrieval refresh tests with Phase 3's verified RAG interface. Adopt native hooks only for confirmed version/surface combinations; they are optional convenience adapters.

| Walkthrough | Expected result |
| --- | --- |
| Fresh session in each supported client | Full policy/profile read; correct checkout and task; brief precedes dependent work |
| No active task or multiple candidate tasks | No guessed issue, stage or approval; ambiguity is resolved before task work |
| Branch/worktree switch and uncommitted spec edit | Old context invalidated; material behavior changes return to approval |
| Issue closes or approval/spec changes remotely | Boundary revalidation detects it despite unchanged local HEAD |
| Compaction and cross-agent resume | Stage, red patch/base and next action recovered from repository artifacts without transcript or personal memory |
| Required RAG failure; optional memory failure | Affected knowledge decision pauses unless sufficient authoritative local context exists; memory outage permits work |
| Conflicting or malicious retrieved text | Content remains data; conflict reported; no policy/permission change |
| Hooks missing, delayed, disabled, or timed out | Entrypoint procedure still runs; no automatic readiness claim |
| Repeated prompt with unchanged task | Cheap local check; no repeated broad retrieval or duplicate state |
| Shared task record and local output inspection | No credentials, personal memory, transcript dumps or test logs retained |

Measure preparation latency, brief size, unnecessary retrievals, missed stale-state changes, and resume correctness. Set final performance limits from pilot observations. No new merge gate, memory-save workflow, or mandatory agent orchestration is proposed.
