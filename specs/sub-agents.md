# Sub-agent handling

Feature issue: https://github.com/pilacorp/nda-harness/issues/28
Issue updated at: 2026-10-28T02:23:59Z
Issue body SHA-256: a9dfb962ef3aca8c5a199a254459bb03642802608d58375b40daa9307b362b91
Consulted source revisions: repository `d7943a8ba4bfe127dbec83cd4bae7372700ed218`; `docs/architecture.md` section "Skills hub and scoped sub-agents"; `skills/catalog.json`; `plugin/skills/session-bootstrap/SKILL.md`; `scripts/nda_harness/plugin_build.py`
Spec branch: `specs/sub-agents`

## Summary

The coordinating agent keeps a small assignment graph and writes one context
summary per node. Each sub-agent runs one node from that summary and returns a
short result. The parent calls Hindsight and internal RAG. The child reads the
local files named in the assignment and queries Context7 when the assignment
needs public library documentation.

The graph is a checklist in the existing task record. This change adds two
workflow skills. It does not add an orchestrator, a queue, or a new memory bank.

## Setup and daily use

No new server, credential, or project setting is required. After the skills are
reviewed and released, developers update the NDA Harness plugin. Existing
Hindsight banks, RAG login, and Jev skill selection stay as they are.

During work, the parent loads `sub-agent-graph` before it delegates. It recalls
personal memory and searches internal RAG, then writes the summary. Jev selects
the specialist skill, if any, before the child starts. The child loads
`sub-agent-loop` plus that specialist skill. The parent stores the child's
short result and chooses the next node.

## Outcome and boundaries

Task classification: behavior change.

Issue #28 asks for skills that cover handling, context summary, token use, and
which skills load. The parent is the graph engineer: it owns routing. The child
is the loop engineer: it owns one assignment and the act-check cycle inside
that assignment.

In scope: two workflow skills, a short pointer in session bootstrap, the
assignment summary, the task-record checklist, and tests that the packaged
skills and the specialist catalog match this contract.

Out of scope: a multi-agent runtime or queue; changing the Jev model,
thresholds, or the three specialist catalog entries; pre-delegation hooks;
editing vendored Superpowers files; a child calling Hindsight or internal RAG;
a child spawning its own sub-agents.

`subagent-driven-development` remains the shape for a dependent act-check cycle
on one node. `dispatching-parallel-agents` remains the shape for nodes that do
not share writable files. The new skills say which shape to use and require the
summary packet. A Superpowers instruction to keep going without the parent, or
to decide an open product question inside the child, yields to this spec.

## Implementation

### Skills

Add two workflow skills under `plugin/skills/`. The package build already copies
`plugin/skills/` into each client package. The skill text is the same for
Codex, Cursor, and Claude. Leave both skills out of `skills/catalog.json`.
Jev does not select them.

| Skill | Who loads it | Responsibility |
| --- | --- | --- |
| `sub-agent-graph` | Parent, before delegation | Decide the nodes, write each summary, spawn one child per ready node, store the short result, choose the next edge |
| `sub-agent-loop` | Child, at the start of its assignment | Work from the summary, check the evidence, stop at the stop condition, return the finding |

`plugin/skills/session-bootstrap/SKILL.md` gains a short paragraph: when the
agent delegates, it loads `sub-agent-graph` and gives the child
`sub-agent-loop`. Session bootstrap stays the place that introduces workflow
skills. No new hook event is added.

Add both directory names to the workflow-skill coverage in
`tests/test_plugins.py` so a built package contains
`skills/sub-agent-graph/SKILL.md` and `skills/sub-agent-loop/SKILL.md`, and the
two files are identical across clients. The existing catalog test continues to
expect only `diagram-design`, `ui-ux-pro-max`, and `vietnamese-official-wording`.

### Assignment graph

The parent writes the graph in the current repository task record under a
`Sub-agents` heading. Each node records its id, goal, dependency ids, selected
specialist id or `none`, and status. A node with no dependency can start
immediately. Nodes that do not share writable files may run together. Nodes
that share writable files, or that name each other as dependencies, run one at
a time in dependency order.

The parent stays the coordinator. The child works only inside its node and
returns the result to the parent. The child does not create another node or
spawn another sub-agent.

### Context summary

The parent writes one summary per node and passes that summary to the child.
The summary contains:

- the issue or task reference and repository revision
- the goal
- the relevant files and any cited RAG passage with its revision
- the constraints that apply, including allowed file scope and side effects
- the expected output
- the stop condition
- the selected specialist skill id and path, or `none`

The summary leaves out the parent transcript, earlier unrelated attempts,
files the child will not touch, credentials, and personal memory beyond a
short note the parent has already chosen to include.

### Parent and child queries

The parent calls Hindsight `recall` and `retain` for the project bank in
`.nda-harness/profile.json`. The parent searches and fetches internal RAG.
The child does not call `recall`, `retain`, or internal RAG search or fetch.
The parent does not put Hindsight credentials or a memory dump into the
summary.

The child reads the local files named in the summary. When the assignment
needs public library or framework documentation, the child queries Context7.
Context7 stays separate from internal RAG and from personal memory.

### Loop and return

Inside the node, the child acts, checks the evidence, and continues while the
stop condition is still open and the work remains inside the allowed scope.
The child stops when the stop condition is met, the next action would leave
the allowed scope, or the same check has failed on two consecutive attempts.
File reads, search hits, and test logs stay in the child.

The result returned to the parent is the finding, any artifact references, and
whether the stop condition was met. The parent appends that result to the
node in the task record and chooses the next edge.

### Skills loaded on each side

The parent keeps its session skills and loads `sub-agent-graph`. It runs Jev
for the node before spawning. It loads a specialist body only when the parent
itself is doing that specialist work.

The child loads `sub-agent-loop` and the one specialist skill named in the
summary. Ordinary backend or test work names no specialist. The child does
not load the rest of the parent's skills and does not call `select-skills`.

## Acceptance mapping

| ID | Issue criterion | Expected behavior |
| --- | --- | --- |
| AC-01 | Handling | The parent gives one assignment, the child stays inside it, and the parent keeps the short result. |
| AC-02 | Context summary | The child receives the summary fields above and the parent transcript stays with the parent. |
| AC-03 | Token use | The child returns the finding and artifact references. The loop transcript stays in the child. |
| AC-04 | Skills to load | The parent loads `sub-agent-graph`. The child loads `sub-agent-loop` plus only the named specialist, or none. |
| AC-05 | Context summary | The parent calls Hindsight and internal RAG. The child does not. The child may query Context7 for public library documentation. |
| AC-06 | Handling | The graph is a task-record checklist. Packages gain the two skills and no orchestrator process. |

## Concrete test cases

These are planned tests, not executed implementation evidence.

| ID | Setup/input | Action | Expected result | Layer / acceptance IDs |
| --- | --- | --- | --- | --- |
| TC-01 | Repository source after the skills exist | Build the Cursor, Codex, and Claude packages | Both skill files exist and match across clients | unit; AC-04, AC-06 |
| TC-02 | `skills/catalog.json` | Read catalog ids | The ids are `diagram-design`, `ui-ux-pro-max`, and `vietnamese-official-wording` | unit; AC-04 |
| TC-03 | `sub-agent-graph` skill text | Read the skill | It names the summary fields, the task-record checklist, and parent ownership of Hindsight and internal RAG | unit; AC-01, AC-02, AC-05 |
| TC-04 | `sub-agent-loop` skill text | Read the skill | It tells the child to skip Hindsight and internal RAG, to query Context7 only for public library needs, and to return a short result | unit; AC-03, AC-05 |
| TC-05 | Session bootstrap skill text | Read the skill | It points delegation at `sub-agent-graph` and the child at `sub-agent-loop` | unit; AC-04 |

A missing summary field, a child `recall` or `retain` call, or a child internal
RAG search fails the skill-text checks. Package generation remains the existing
`plugin_build` path.

## Hook changes

None. Pre-delegation and child-start hooks stay proposed architecture. This
spec uses skill instructions and the task record.

## Documentation and rollout/recovery

`docs/architecture.md` already describes scoped sub-agents. Implementation adds
the two skills and the session-bootstrap pointer. No migration of task records
or memory banks is required. Rolling back removes the two skill directories and
the bootstrap paragraph; existing vendored Superpowers skills remain.

Manual check after release: one parent session delegates a single backend node
with no specialist, and one node that names `diagram-design`. Confirm the child
prompt contains the summary and `sub-agent-loop`, and that the task record
contains the short result.

## Decisions and risks

The graph lives in the task record because the architecture already uses that
record for assignment scope and forbids a mandatory multi-agent runtime. A
client that cannot isolate a child context uses a fresh session with the same
summary and records that limitation, as the architecture already requires.

Skill text can be ignored by a model. These tests check that the instructions
ship. They do not prove a live session obeyed them. Human review of the task
record remains the place where a missing summary or a leaked transcript is
caught.

The two-failure stop is a local bound so a child returns to the parent. The
parent may open a new node. That bound is a harness rule, not a model limit.

## Review and implementation handoff

Spec PR: unset until opened
Review reference: unset until reviewed
Merge reference/revision: unset until merged
Local spec matches merged reviewed version: unset until merged
Next action: review and merge this spec before writing the skill files.

The issue owns intent. This document does not grant approval; behavior-change
implementation requires verified review/merge and matching local content.
