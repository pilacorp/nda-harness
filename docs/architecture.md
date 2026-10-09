# NDA Harness architecture

Status: architecture proposal. Integration references checked on 2026-10-08. See [developer integration](developer-integration.md) for local adoption.

## Purpose and boundaries

The internal team currently gives tasks directly to coding agents, with some tools and plugins but no consistent development process. NDA Harness makes the process explicit and reviewable across agents: agreed behavior drives tests, tests drive implementation, and evidence accompanies review.

This phase documents that framework. It does not implement a coding agent, orchestration engine, installer, RAG backend, memory backend, or CI validator. Existing agents, project test runners, and knowledge services remain in use.

SDD means **spec-driven development**. Harness TDD means a meaningful red unit test before the corresponding implementation, followed by green and refactoring. QA owns integration and end-to-end verification. Prompts guide local work; proposed required CI checks enforce unit-test evidence at merge. Neither prompts nor a final green build guarantee that the agent actually followed every step.

## Components and data boundaries

![System overview: a pinned policy guides the local coding agent; local code and internal feature/architecture RAG provide project context, Hindsight supplies the developer's personal memory, and GitHub hosts review and proposed CI gates.](diagrams/system-overview.png)

[Open the editable system overview](diagrams/system-overview.html). Knowledge-service arrows show agent access, not repository ingestion. Dashed CI styling denotes proposed enforcement.

| Component | Responsibility | Source of truth |
| --- | --- | --- |
| Shared policy, agent adapters, and local hooks | Load the workflow and run unit tests before commits | Pinned, reviewed repository-local policy and hook package |
| Role-specific skills and tools | Guide tech-lead scoping/documentation and developer SDD; scaffold/validate artifacts, verify prerequisites, and retain test evidence | Pinned, reviewed skill/tool contracts; authoritative documents and authenticated records |
| Local coding agent | Read code, inspect callers, edit files, execute existing project tools | Developer's repository and recorded revisions |
| Internal RAG | Retrieve feature definitions and architecture from existing Markdown/pgvector knowledge | Cited source documents and revisions |
| Self-hosted Hindsight | Recall and retain each developer's preferences and personal working notes | Developer-controlled personal context; not authoritative organization facts |
| Repository task artifacts | Preserve specs, checkpoints, exceptions, and handoff state | Versioned artifacts and human approval records |
| GitHub Actions | Validate submitted evidence and run project checks | Results for the current PR revision |
| Human owners | Approve specs, exceptions, and code | Authenticated approval records |

The agent reads repository code directly on the developer's device. The feature/architecture RAG must not ingest repository code. Personal memory stores preferences and individual working notes, not code dumps or raw agent transcripts. It does not establish organizational requirements or decisions. This does not imply local model inference: the team's coding-agent provider and existing data policies still apply.

The data flow is: tech-lead GitHub issue → developer task → local agent → local code plus scoped RAG and personal-memory retrieval → repository spec and test evidence → PR checks and human review → merge. CI uses repository evidence rather than making live RAG or memory calls to decide compliance; issue and approval validation reads authenticated GitHub metadata.

## Development lifecycle

**Tech-lead issue → Understand → Specify → Human approval → Red → Green → Refactor → Review → Merge**

| Stage | Required work and output | Exit condition / owner |
| --- | --- | --- |
| Tech-lead issue | Tech lead creates an issue in the target GitHub repository with the problem, expected outcome, and constraints | An open issue created by an authorized tech lead exists before developer task work starts |
| Understand | Classify the task; inspect relevant local code and callers; retrieve feature/architecture context and relevant personal preferences; cite authoritative sources and identify uncertainty | Agent has enough authoritative context; unresolved behavior decisions go to the developer |
| Specify | Write intended behavior, acceptance criteria with stable identifiers, scope boundaries, relevant design decisions, and verification approach | Spec is ready for human approval |
| Human approval | Authorized developer/tech lead approves the spec-only GitHub PR; merge the approved spec and record its revision, including any exception | Spec PR is approved and merged before implementation |
| Red | Add focused unit tests linked to the changed logic; retain a test-only checkpoint and run them against pre-change code | Expected behavioral assertions fail; environment and unrelated failures are distinguished |
| Green | Implement the smallest change that satisfies the approved criteria and tests | Targeted tests pass without weakening the agreed assertions |
| Refactor | Improve structure when needed, keeping behavior and tests stable | Relevant tests remain green |
| Review | Check spec alignment, test quality, caller impact, evidence, and project checks | Required checks and human review pass |
| Merge | Merge the reviewed revision under repository branch rules | Authorized merge; changed code or spec invalidates affected evidence/approvals |

Repeat Red → Green → Refactor for each behavior increment. A material change to requirements returns to Specify and Human approval. A purely editorial spec correction can be recorded without restarting unchanged tests; the reviewer confirms it does not change acceptance criteria.

Features and bug fixes require the full path. A bug fix first reproduces the defect and traces the shared cause, including sibling callers. Docs and mechanical changes use task classification, appropriate existing checks, and human review without artificial red tests. A behavior change that cannot produce reproducible red evidence requires a named human approver, rationale, affected criteria, and alternate verification; the agent cannot approve its own exception. There is no silent emergency bypass.

### Unit-test scope and QA responsibility

Agents add a small set of meaningful unit tests for changed business logic, important branches, and bug regressions, using the repository's existing runner. There is no fixed test count, coverage-percentage target, or requirement to test every function. Those unit tests still follow Red → Green → Refactor and retain reproducible evidence.

The approved spec maps acceptance criteria to unit tests where appropriate and identifies scenarios for QA, such as cross-service behavior, complete user journeys, and integration with external systems. QA-owned criteria do not require artificial unit tests or agent-built integration/end-to-end suites. If a change has no meaningful unit-testable behavior, record the reason and QA verification in the existing human-approved exception path.

The implementation PR includes the approved spec and a short summary of QA scenarios and known limits. QA uses the team's existing process; this proposal adds no new QA automation, sign-off gate, or release workflow. QA's later findings return as issue work and regression tests where suitable. Do not treat green unit tests as proof that QA scenarios passed. Issue closure tracks accepted implementation merge, not completion of all QA testing.

Harness CI requires relevant unit tests and existing applicable lint/type/build checks. It adds no integration/end-to-end test requirement. Existing repository checks remain under repository-owner control; adopting the harness does not silently remove them.

### Issue, branch, and PR traceability

Every developer task requires one primary GitHub issue created by an authorized tech lead in the same repository. The issue captures intent; the approved spec defines the behavior to implement. The agent verifies the issue before task work and does not create a replacement issue on behalf of the tech lead. Missing, inaccessible, closed, or unauthorized issues block task start until the tech lead resolves them.

For issue #123, use `feat/123-<feature>` for both feature PRs. For lighter tasks, reuse the repository's existing branch prefix but retain the `<issue-number>-<slug>` segment. Record the full issue URL in the spec and task record; the branch issue number, spec, task record, and both PRs must refer to the same primary issue. Branch naming alone does not establish a GitHub relationship.

The spec PR body contains `Refs #123`, a plain non-closing reference. It must not contain an issue-closing keyword for the primary issue, have a manual closing link in GitHub's Development sidebar, or introduce a closing keyword in its commit messages. The issue remains open after the spec merges. Spec-change PRs follow the same non-closing rule.

The implementation PR body contains `Closes #123` and links the merged spec PR. Both PRs target the repository's default branch (main in these examples). GitHub's closing keywords act on merges into the default branch; commit messages and manual links can also cause closure. See [GitHub issue linking](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue). The reviewer confirms acceptance criteria before implementation merge; verify closure afterward and let the tech lead close the issue manually if repository settings do not close it automatically. Lighter tasks use a single completion PR with the same issue requirement.

### Human approval happens on GitHub

![Issue-led, one-branch, two-PR sequence: a tech lead creates the issue, the spec PR references it, approval and merge unlock local TDD, and the implementation PR closes it after checks and separate code review.](diagrams/spec-implementation-sequence.png)

[Open the editable approval sequence](diagrams/spec-implementation-sequence.html). This is the happy path; rejected or materially changed specs return to approval, and the CI gates shown still need implementation.

The default is one feature branch and two sequential PRs per behavior-change task: a **spec-only PR**, then an **implementation PR**, both from `feat/<issue-number>-<feature>` into main. The tech lead reviews from their own device in GitHub; no access to the developer's device or agent session is required. GitHub distinguishes an Approve review from a comment or request for changes; use an authorized human's explicit approval. See [GitHub PR reviews](https://docs.github.com/en/pull-requests/reference/pull-request-reviews).

Create `feat/<issue-number>-<feature>` and submit `specs/<feature>.md` in the first PR, without implementation changes. Keep the branch after the spec merges, fetch main, and merge updated main into that same branch before starting local TDD. Then push implementation changes and open a second PR from the same branch. This synchronization also handles squash/rebase merges without requiring a force push. Prevent automatic deletion of the feature branch after the spec PR, or re-push the retained local branch under the same name if it was deleted remotely. Delete the branch only after the implementation PR merges. Reuse an existing spec location when present; use `specs/<feature>/` only when multiple documents are needed.

The developer submits the spec and acceptance criteria without production implementation, resolves feedback, and gets approval from the designated spec approver. Merge the spec under required review rules. The local agent then fetches the merged revision and verifies the approved spec before starting Red. While approval is pending or changes are requested, it pauses dependent test/implementation work.

Record the spec PR URL, approval review reference/actor, approved PR head revision, and merged spec revision/path. A squash or rebase merge can change commit IDs; the future validator must verify the merged spec content matches the reviewed content, rather than requiring identical commit IDs. The implementation PR references these records and receives separate code review. A materially changed spec requires a new spec-change PR and approval before dependent work resumes.

Local chat, a pasted approval message, or an agent-written approval flag does not satisfy this gate. During the guided pilot, the developer verifies the GitHub record manually; later tooling can read it through the GitHub API or existing CLI. No automatic notification or message to the tech lead is part of the local harness contract.

## Shared policy and task artifacts

The future release package is copied into each adopted repository under `.nda-harness/` and pinned to an immutable release revision. Keep the policy concise; the detailed workflow is read as needed. Thin agent entrypoints load the policy and repository profile rather than maintaining separate process definitions.

The policy must cover stage transitions, required human decisions, test-first work, evidence, knowledge trust boundaries, unavailable services, exception handling, and completion reporting. These are repository instructions, not a replacement for provider-controlled system prompts or tool permissions. The baseline includes a Git pre-commit unit-test hook and required role-specific skill/tool procedures. Optional agent-native hooks provide convenience; skills and local checks do not replace the shared Git hook, authenticated approvals, or CI checks.

### Tech-lead and developer workflows

The harness execution layer includes tools and skills for both roles. Tech leads use `scope-initiative`, `document-requirements`, and `review-spec` to define boundaries, author feature/architecture intent, prepare issue briefs, and assess developer specifications. Developers use `execute-sdd`, `scope-task`, `write-spec`, and `document-change` to turn a verified issue into an approved behavior spec, meaningful unit-test evidence, implementation and review artifacts. Shared artifact tools scaffold and validate documents; developer tools verify authenticated task prerequisites and capture test-only red checkpoints. See the [role workflows and delivery contracts](../plan.md#role-workflows-and-handoff).

Tech-lead preparatory scoping/documentation precedes issue creation and is not blocked by the developer task's issue prerequisite. Versioned document changes still follow existing repository review rules. The authorized tech lead creates the primary issue; the developer agent cannot create a substitute. Draft lead documents remain drafts until accepted through the existing source-owner process. They inform the developer spec without replacing its human approval/merge gate.

Skills guide reasoning and authoring, tools perform deterministic operations, and context hooks prepare inputs and route by role/stage. Role selection is not authentication or permission. The human retains scope decisions and approval authority; skill execution cannot self-approve, grant access or advance a stage on its own. These are proposed pack capabilities for existing local agents, not a separate coding-agent runtime.

The repository profile records setup, targeted unit-test and relevant unit-suite commands, applicable lint/type/build checks, runtime prerequisites, spec/task locations, RAG project scope, supported agent versions, authorized tech-lead GitHub identities, approvers, default branch, and harness revision. Personal-memory identity and credentials stay in each developer's local configuration. Use Markdown for the initial profile and task records; a machine-readable gate format is a later implementation concern.

Each task record links the following:

- Task identifier, classification, stage, branch/revision, and harness revision.
- Primary issue URL/number, verified GitHub author, spec PR, and completion PR references.
- Approved spec location and revision; approval actor, time, and durable reference.
- Acceptance-criterion identifiers mapped to meaningful unit tests, QA scenarios, or approved alternate verification.
- For each red/green cycle: pre-change revision, test-only checkpoint, commands, environment requirements, and expected behavioral failure for replay; retain concise proof of final passing tests.
- Review/CI references, exceptions, unresolved decisions, and the next action for handoff.

Task records retain concise test-pass proof, not test logs: tested commit SHA, command/suite, pass status, and a link to the successful GitHub check/run for that revision. Local runs can record the same summary without a CI link, but an agent-authored PASS statement alone is not merge proof; CI verifies the final revision. Do not commit console output or require uploaded/downloaded log artifacts. GitHub's normal run output may remain available for troubleshooting without becoming a harness retention requirement. Preserve the test-only patch, base revision, and expected failure for red replay even if merge uses squash; no red log is required. Chat history and Hindsight cannot substitute for these records.

## Proposed local hooks

For session/task context loading, refresh, and handoff, see the [context preparation hooks proposal](context-preparation-hooks.md). It recommends a shared preparation contract with optional agent-native adapters; it is not an installed hook set or a replacement for the Git/CI checks below.

Start with one required hook: **Git `pre-commit` runs the repository's configured unit-test command**. Use the existing project hook setup if present; otherwise ship an executable `.nda-harness/hooks/pre-commit` and activate it per checkout with repository-local `core.hooksPath`. No new hook framework is required. Git supports a configured hook directory and aborts a commit on a nonzero pre-commit exit; the hook can be bypassed with `--no-verify`. See [Git hooks](https://git-scm.com/docs/githooks).

The repository owner selects a deterministic, non-watch unit-suite command using the existing runner. It may cover the affected module where the project already supports reliable selection; otherwise run the existing unit suite. A missing command, unavailable environment, test failure, or runner error blocks the commit with the command and actionable output. Do not silently skip tests, auto-fix files, stage changes, stash work, or call RAG/memory from the hook. Run this check on each normal commit, including spec/docs commits; it adds no integration/end-to-end tests.

Keep the hook script and test entrypoint versioned. The profile documents the command and hook activation; the implementation must call the existing executable test entrypoint rather than treating Markdown prose as executable configuration. Reuse existing hook chains and preserve their checks; do not overwrite a developer's hook path or disable a project's installed hooks during adoption.

**Red checkpoints do not require failing commits.** Before implementation, retain the complete test-only change as a patch against the recorded pre-change revision, including new test files, and capture the expected red result. After implementation turns green, commit the patch as evidence with the passing code/tests and reference it from the task record. CI can replay that retained patch against the base revision. This keeps ordinary commits green without a TDD-driven `--no-verify` bypass; the hook itself does not prove test-first order.

Tests run against the local working tree, so developers must stage the source/test/config changes that were tested before committing. A passing local hook alone does not certify the exact staged snapshot; CI rechecks the committed PR revision. The agent must not disable hooks or use `--no-verify` to bypass failures. Any authorized bypass is recorded for human review and does not waive required CI checks.

Activation is local to each checkout, not automatically enabled just because scripts are committed. Verify it for every developer device and worktree, and test the commit paths used by the supported agents. These hook contracts are part of the proposal; no executable hook is installed by this documentation phase.

## Knowledge contracts

The pinned pack also includes a proposed `.nda-harness/scripts/setup-knowledge` script for developer-local agent connection setup. It configures access to existing internal RAG and personal Hindsight through each supported client's integration mechanism, preserves existing configuration, keeps credentials local, and verifies scoped retrieval and personal-memory isolation. See the [setup script contract](developer-integration.md#pack-provided-setup-script). It is onboarding tooling, not a coding-agent runtime or a new knowledge backend; executable delivery remains in the tooling phase. The script configures local agent connections; RAG and Hindsight backends stay on the existing internal infrastructure.

### Internal feature and architecture RAG

Reuse the existing Markdown/pgvector service. Its actual transport, endpoints, authentication, and ownership must be confirmed with the service owner before implementation. The following are logical capabilities, not a new wire protocol:

| Capability | Inputs | Required results |
| --- | --- | --- |
| Search | Query, explicit project scope, optional feature/architecture category | Authorized matches with document ID, title, source reference, revision/update time, and relevant excerpt |
| Fetch | Document ID and, where supported, requested revision | Authorized source content, citation, and actual revision; explicitly report unavailable historical revisions |

Permissions must be enforced by the service, not just by an agent-supplied filter. Explicitly scoped retrieval prevents accidental cross-project context; it does not grant access. Distinguish no results from authentication, permission, and service failures. Fetch enough source context before using a search excerpt to decide behavior. Record consulted revisions in the spec.

Use an existing MCP interface if available. If the service exposes HTTP only, use a supported authenticated tool integration; propose a thin MCP mapping only when needed for shared client access. Do not introduce another indexing pipeline or vector store.

Retrieved text is context, not executable instructions. It cannot authorize commands, change harness rules, or override an approved spec. If a cited feature document conflicts with the spec, report the conflict and ask the human owner to reconcile it. Do not silently pick the newest text. If the required source is unavailable, pause the affected decision unless an authoritative local copy with known revision is sufficient.

### Self-hosted Hindsight

Use Hindsight for each developer's personal memory first: preferred explanation style, recurring personal setup notes, and individual reminders useful across sessions. Organizational facts, feature requirements, and architecture decisions remain in approved source documents/specs and internal RAG. Shared organizational memory and a lesson-promotion pipeline are outside this phase.

The development cycle ends at Merge. Personal-memory updates are handled through the developer's Hindsight integration outside that cycle; any additional learning workflow is deferred to a future phase.

Deploy the open-source [Hindsight server and Control Plane](https://github.com/vectorize-io/hindsight) on internal infrastructure with a pinned release and external PostgreSQL/pgvector. Its [MCP server](https://hindsight.vectorize.io/developer/mcp-server) exposes memory operations to supported local agents. Verify the actual deployed tools and transport; developer clients authenticate to the internal Hindsight endpoint, not a public hosted memory service.

Use individually authenticated tenants for personal memory. The standard shared-key extension uses one shared schema and does not meet this requirement. Include and configure the documented `StaticKeysTenantExtension` from the extensions registry, or an approved identity-provider tenant extension; each developer maps to a separate PostgreSQL schema. Banks organize memory within that tenant, not authorize access by themselves. Verify isolation through API, MCP, and the dashboard, including denied cross-user access. See [tenant extensions](https://hindsight.vectorize.io/developer/extensions).

Hindsight uses **OpenRouter for LLM processing**, with local embeddings and reranking as the initial default. Set `HINDSIGHT_API_LLM_PROVIDER=openrouter`, supply `HINDSIGHT_API_LLM_API_KEY` through server-side secret storage, and set `HINDSIGHT_API_LLM_MODEL` to an explicitly selected model ID. Model selection remains a deployment decision verified for extraction quality, structured output, latency, and cost; do not assume a benchmark score applies to that model. See [provider configuration](https://hindsight.vectorize.io/developer/configuration).

Storage stays internal, but memory content used for extraction, consolidation, and reflection is sent to OpenRouter and the selected upstream provider. This is not fully local inference. Record the selected model/routing and applicable data-handling settings before using personal memory; keep provider credentials on the Hindsight server, separate from developers' Hindsight access tokens. Neither the local setup script nor CI requires an OpenRouter key.

The self-hosted Control Plane provides memory inspection. Automatic consolidation updates derived observations when new evidence changes a preference; it does not guarantee deletion of old raw facts. Developers can edit or invalidate stale facts; invalidation removes them from active recall while preserving history. Verify these behaviors in the pilot using [memory curation](https://hindsight.vectorize.io/developer/api/memories).

Each developer controls what their agent recalls or saves, including whether supported automatic memory capture is enabled. Do not require tech-lead approval, maintainer publication, or repository lesson proposals for personal memory. These are harness usage boundaries, not claims that Hindsight provides a proposal/approval feature. Keep personal-memory content and identifiers out of shared task records and committed project configuration. Never save secrets; avoid uploading project content beyond the team's existing data permissions.

Recall only the current developer's relevant memory. Personal preferences cannot override the pinned policy, approved spec, or current architecture requirements. Any remembered claim about project behavior must be verified against current local code or authoritative documents before use. The developer can correct or remove stale personal notes. Memory outages or failed saves do not block task work or merge; proceed using required repository/RAG context. Task checkpoints and cross-developer handoffs remain in repository artifacts, never dependent on access to another developer's memory.

## Proposed GitHub Actions enforcement

These are gate requirements for the next implementation phase, not checks already installed by this proposal. [GitHub required status checks](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches) can prevent merge until configured checks succeed.

| Proposed check | Required outcome |
| --- | --- |
| Issue and branch | Every developer PR references an existing open issue in the same repository whose authenticated author is an authorized tech lead; branch issue number, spec/task links, and PR reference agree |
| PR lifecycle | Spec/spec-change PR uses `Refs #<issue>` without a closing relationship; implementation PR uses `Closes #<issue>`, links the spec PR, and reuses its source branch identity; completion PR targets the default branch |
| Spec and approval | Implementation PR links the merged spec-only PR and authorized human approval; verify reviewed spec content and material changes require renewed approval |
| Traceability and classification | Criteria identify unit-test coverage or QA-owned verification; reviewer confirms QA-only exceptions and lighter-path classification are valid |
| Red replay | Each retained unit-test-only checkpoint fails against its recorded pre-change implementation for the expected behavioral reason |
| Green verification | Mapped unit tests, relevant existing unit suites, and applicable lint/type/build checks pass on the current final revision; no new integration/end-to-end requirement |
| Review | Human reviewer evaluates test strength, spec alignment, exceptions, and remaining risks |

The issue validator reads GitHub issue metadata and compares the author identity with the maintainer-controlled tech-lead list. A pasted name, label, branch name, or issue-looking PR number is insufficient. Confirm the number identifies an issue rather than a pull request, belongs to this repository, and was created before the task's first PR. For implementation, match both the head repository and branch name with the merged spec PR. Invalid issue linkage cannot be waived by a TDD exception.

For open PRs, evaluate current descriptions, issue state, and closing relationships as well as the code revision. Re-run affected checks when PR metadata, issue state, or tech-lead authorization changes; an earlier green result must not authorize invalid new metadata. Normal issue closure after the completion PR merges does not invalidate historical evidence. GitHub lookup failures block the required check with an actionable error, rather than being treated as valid or missing evidence. Keep these metadata reads separate from execution of untrusted PR code.

For replay, use a recorded immutable parent implementation revision and a retained test-only patch containing only the new/changed unit tests and necessary test support. The patch can be stored in a later green commit; it need not be a failing commit. Replay applies it to the recorded base in a separate checkout and must not modify the developer's working tree. Where a new feature introduces an API, shape its unit test so replay reaches an expected behavioral assertion; an import/compile failure alone is insufficient. If that is impractical, use the explicit exception path.

Verify checkpoint diffs contain no corresponding production implementation or unrelated changes. Confirm existing tests/environment work before accepting the expected red assertion. Re-run the mapped tests on final code, including retained assertions if final tests have been reorganized. Removed or weakened assertions require review and renewed evidence. A task-authored log or nonzero exit code alone is not evidence of a valid red result.

Reproducible red/green proves that tests distinguish pre-change and final behavior. It does **not** independently prove the historical order in which edits happened. Human approval timing and authenticated review records support process auditing; stronger historical attestation would be a separate requirement.

The gate implementation must resolve approval from authenticated review records, not trust an agent-written approver name. Approval must identify the spec revision before implementation; final code review alone is not retroactive spec approval. Evidence is tied to the current PR revision, and stale runs cannot authorize a changed PR.

Protect policy, profile, adapters, gate code/workflows, and ownership rules through designated owner review. The future validator must use a trusted version that a task PR cannot redefine to approve itself. Run PR code without knowledge-service credentials or privileged write tokens; red replay executes submitted test code and needs the same isolation as other PR tests. Require checks and review on protected branches, with any authorized bypass documented as an exception.

## Ownership and pilot validation

Harness maintainers own policy releases and adapter compatibility. Repository owners define commands, approvers, and merge requirements. The RAG owner maintains source indexing and authorization. The memory service owner maintains deployment access and developer isolation; each developer manages their own personal memory. Developers provide intent and spec approval; reviewers assess behavior and evidence. These are responsibilities, not new mandatory job titles.

Use one pilot repository with its existing stack. First establish a baseline from recent comparable changes, then evaluate the same task categories with the harness. Do not set numeric improvement claims before measuring.

| Measure | Definition |
| --- | --- |
| Spec/test traceability | Share of behavior-change criteria assigned to reviewed unit tests, QA scenarios, or explicit exceptions; report unit and QA scope separately |
| Red/green compliance | Share of behavior-change PRs with valid replay and final green evidence; report exceptions separately |
| Review rework | Behavior/spec corrections requested after the first review and review iterations |
| Escaped defects | Defects linked to merged pilot changes during the same agreed observation window |
| Developer effort | Setup time, active development/review effort, and workflow friction reported by developers |

The following are acceptance walkthroughs to execute in the pilot, not completed integration tests:

| Scenario | Artifacts and owner | Acceptance / blocking condition |
| --- | --- | --- |
| Codex onboarding | Loaded instruction sources, profile, baseline results; developer | Policy read, local code inspected, scoped RAG and own personal-memory access verified; conflicting override resolved |
| Claude Code onboarding | Loaded project instructions, profile, baseline results; developer | Same capabilities; personal rules cannot silently replace the agreed process |
| Cursor onboarding | Active project rule, profile, baseline results; developer | Rule loads in a fresh session and the agent reads referenced policy; manual attachment alone is insufficient |
| Pre-commit hook | Activated hook, unit command and passing/failing trial changes in a disposable checkout; developer | Passing units permit a commit; test/runner failures block it; existing hook checks still execute |
| TDD with pre-commit | Retained red test patch, base revision, red result and green commit; developer | Red evidence survives without committing failing tests or bypassing the hook; CI replays the patch |
| Hook setup and staged-state limits | Checkout/worktree activation and recorded tested/staged changes; maintainer | Missing activation is detected in onboarding; CI validates the committed snapshot independently |
| Issue-linked feature | Tech-lead issue, `feat/123-<feature>`, spec `Refs #123`, code `Closes #123`; tech lead and reviewer | Spec merge leaves issue open; code PR uses the same branch and issue and closes it only after accepted implementation merge |
| Invalid issue linkage | Missing/non-issue number, wrong repo or author, closed issue, mismatched branch/spec/PR reference; developer | Task start or relevant merge check blocks; no silent fallback |
| Premature issue closure | Spec closing keyword, closing commit message, or manual closing link; reviewer | Spec PR blocks until the closing relationship is removed; prematurely closed issue is reopened by the tech lead |
| Changed GitHub metadata | Edited PR body or closed issue after a passing check; repository owner | Affected validation reruns and blocks invalid current metadata |
| Feature | Spec, prior human approval, criterion mapping, red checkpoint, green/review references; developer and reviewer | Expected behavior fails on pre-change code and passes on final code |
| Bug fix | Reproduction, caller analysis, approved regression criterion, evidence; developer and reviewer | Regression test reproduces the defect; fix covers shared cause |
| Unit tests plus QA scenarios | Focused unit-test evidence and QA scenarios linked to the approved spec; developer and QA | Unit logic follows red/green; QA owns integration/end-to-end verification without an added harness test-suite requirement |
| Documentation change | Classification, relevant doc/link checks, review; reviewer | Lighter path approved; no fabricated failing test |
| Changed spec | New spec revision and approval, refreshed affected evidence; spec approver | Implementation waits for approval; old evidence cannot cover changed criteria |
| Invalid red failure | Replay output and environment diagnosis; developer | Setup/compile/unrelated failures block red acceptance until fixed or excepted |
| Unavailable RAG | Recorded outage and local authoritative source, if any; developer | Continue only if required context is sufficient; otherwise pause affected decisions |
| Personal memory isolation | Separate developer accounts/scopes and an owner-provided denied-access check; service owner | Agent cannot access another developer's memory; absent isolation blocks memory integration, not task work |
| Knowledge setup script | Local client configuration, sanitized readiness report and rollback instructions; developer | First run connects the selected agent; rerun preserves unrelated settings without duplicate connections; failed auth is explicit; unverified memory stays disconnected |
| Stale personal memory | Conflicting preference or note and current source; developer | Approved requirements govern; developer corrects or removes the note |
| Cross-agent handoff | Versioned task state, cleanly identified revision, remaining actions; both developers/agents | Receiving agent rechecks state and resumes without repeating completed work or bypassing a gate |

## Decisions and prerequisites

Defaults are English documentation, one shared policy, repository-local version pinning, existing test runners, separate RAG and personal-memory services, and developer-controlled personal memory. Shared organizational memory and mandatory multi-agent orchestration are outside this phase.

Before implementation, owners must supply the pilot repository, existing test commands, authorized approvers, RAG interface/authentication, and self-hosted Hindsight endpoint/capabilities. These are integration facts to confirm, not reasons to invent replacement services. Release packaging, machine-readable evidence, validators, and deployment are subsequent work.
