# NDA Harness implementation plan

Implement in this order: **Phase 1: internal Hindsight with OpenRouter → Phase 2: harness policy and local setup script → Phase 3: internal RAG updates**.

This plan turns the [architecture](docs/architecture.md) and [developer integration design](docs/developer-integration.md) into a released pack for existing local Codex, Claude Code, and Cursor agents. It does not introduce a coding-agent runtime or mandatory wrapper. Target a working pilot in **two weeks (10 working days)** from kickoff.

## Two-week delivery target

Assume one primary engineer using AI-assisted coding, part-time infrastructure/tech-lead support, a selected pilot repository, and timely access to internal infrastructure and GitHub approvals. Run phases sequentially; day numbers are working days rather than fixed calendar dates.

| Schedule | Deliverable |
| --- | --- |
| Days 1–2: Phase 1 | Deploy internal Hindsight, verify personal isolation and supported agent connections, and supply connection details for the setup script |
| Days 3–7: Phase 2 | Deliver pinned policy/templates/adapters, unit-test hook, local setup script, GitHub gates, and pilot repository adoption |
| Days 8–9: Phase 3 | Update existing RAG metadata/access/search/fetch, extend local connection setup, and verify cited retrieval across agents |
| Day 10: final validation | Complete the combined pilot walkthroughs, fix remaining issues, and review readiness with the owners |

Keep the phase acceptance criteria below as the completion gates. The two-week target assumes Hindsight supports the required internal deployment/isolation and the existing RAG needs incremental changes. Resolve these assumptions early; report any access, capability, or approval blocker with its schedule impact rather than weakening the gates. Broader rollout and observation of real developer usage follow the working pilot.

## Common requirements

- A tech lead creates the primary GitHub issue before developer task work starts. Branches, specs, task records, and PRs reference that issue.
- Behavior changes use one issue-numbered branch for two sequential PRs: spec-only `Refs #<issue>`, then implementation `Closes #<issue>`. Human approval and spec merge precede implementation; retain and synchronize the branch between PRs.
- The workflow is Understand → Specify → Human approval → Red → Green → Refactor → Review → Merge. There is no Learn stage.
- TDD uses meaningful unit tests and existing runners. QA owns integration and end-to-end verification. Documentation/mechanical tasks use the lighter path; untestable behavior requires a recorded human-approved exception.
- Keep concise passing-test proof: tested revision, command/suite, pass status, and successful GitHub check/run link. Do not retain test logs as task artifacts. Keep the test-only patch, base revision, and expected failure for red replay.
- Code stays in the local repository. Internal RAG holds feature/architecture documents. Hindsight holds each developer's personal memory, separate from organizational facts and task state.

Apply this workflow to implementation of the harness itself. The tech lead breaks each phase into issue-backed deliverables and approves their specifications. Until the gates ship, reviewers enforce the rules manually.

## Phase 1: setup internal Hindsight with OpenRouter

**Outcome:** an internal Hindsight service providing isolated personal memory for each developer, with verified connection details ready for the Phase 2 local setup script.

**Owners:** memory service owner owns deployment and access; harness maintainer records the integration contract for Phase 2; each developer controls their personal memory.

### Implementation sequence

1. Select a pinned open-source Hindsight release and verify its deployment requirements, license, MCP interface, Control Plane, and compatible tenant-extension version. Configure the native OpenRouter provider; select an explicit model ID and evaluate extraction, structured output, latency, and cost. Record OpenRouter routing/data-handling settings: storage is internal, while relevant memory content is processed externally. Use local embeddings and reranking initially.
2. Prepare the internal deployment using existing infrastructure practices: pinned containers, external PostgreSQL/pgvector, API/MCP and Control Plane, approved internal endpoint/network access, secret management, backup/restore, and an operational owner/runbook. Set `HINDSIGHT_API_LLM_PROVIDER=openrouter`, `HINDSIGHT_API_LLM_MODEL`, and the server-only secret `HINDSIGHT_API_LLM_API_KEY`; never distribute this key to developer clients. Backend hosting stays on internal infrastructure, not developer devices.
3. Include and configure `StaticKeysTenantExtension` or an approved identity-provider tenant extension, mapping each developer to an isolated PostgreSQL schema. Provision individual Hindsight credentials and a personal bank within each tenant. The shared-key default and bank names alone do not establish user isolation. Exercise authorized/denied checks through API, MCP, and the dashboard using designated test accounts.
4. Verify the deployed memory interface's search/save and any supported correction/deletion operations. Document actual tool names, transport, authentication, and limitations; verify dashboard inspection and edit/invalidate behavior. Test changed preferences through consolidation without claiming automatic deletion of old raw facts. Keep automatic capture under developer control.
5. Deliver the connection prerequisites for the Phase 2 setup script: internal endpoint, transport, authentication flow, credential-storage requirements, verified tool/capability names, and authorized/denied test procedures. Keep secrets outside the repository; the client setup script receives developer Hindsight credentials, never the OpenRouter service key. Validate connection compatibility with Codex, Claude Code, and Cursor using supported manual client setup; automate it in Phase 2.
6. Define and exercise read-only connection verification for authenticated personal identity, available capabilities, and service-owner isolation checks. Empty memory is valid. Unverified isolation blocks enabling memory integration; provide these checks to the Phase 2 script implementation.
7. Document developer onboarding, personal save preferences, stale-note correction, disconnect/revocation, outages, and upgrades. Keep credentials and personal memory out of Git, RAG, and shared task artifacts.

### Acceptance and phase exit

- Two designated test users cannot read or modify one another's memories through API, MCP, or dashboard; authentication errors are distinguished from empty results.
- OpenRouter-backed extraction/consolidation/reflection work with the selected model, while developer clients and CI hold no OpenRouter credentials. Record observed latency/cost and verify that provider failures are reported accurately.
- Codex, Claude Code, and Cursor can connect through their supported manual integration. Verified non-secret connection details and verification procedures are delivered for the Phase 2 setup script; script automation is not a Phase 1 deliverable.
- An authorized developer can save and recall a personal test note and correct/remove it where the deployment supports those capabilities. Onboarding itself performs no memory write.
- Memory preferences cannot override policy/specs; stale organizational claims are checked against authoritative sources.
- Service outage, empty memory, and save failure do not block development or merge. Backup/restore and access revocation are verified by the service owner.
- No Learn stage, shared lesson publication, or organizational fact store is added.

## Phase 2: implement harness policy and local setup script

**Outcome:** a pinned repository-local pack, working unit-test hook, and GitHub enforcement validated in one pilot repository. Use the verified internal Hindsight deployment from Phase 1; connect the existing RAG interface where supported while its updates remain in Phase 3.

**Owners:** harness maintainer owns the release; pilot repository owner supplies project commands and review ownership; tech lead approves specs; developers and reviewers validate adoption.

### Implementation sequence

1. Select one pilot repository and record its existing test runner, setup commands, supported agent versions, default branch, tech-lead identities, approvers, and existing hook/CI configuration. Establish the baseline for traceability, review rework, escaped defects, and developer effort before setting improvement targets.
2. Author the shared policy and workflow covering stage boundaries, classifications, approval, TDD, exceptions, task handoff, trusted context, outages, and completion. Create repository profile and release templates. Use immutable release revisions; upgrades happen through reviewed adoption PRs.
3. Provide spec and task templates. Default specs to `specs/<feature>.md`; use a folder only for multiple documents. Default task records to `.nda-harness/tasks/<issue>-<feature>/task.md` with the acceptance mapping and passing-test summary inline, plus `red.patch` when needed. Repositories can reuse existing locations through their profile. Task records contain no personal-memory content or credentials.
4. Provide thin Codex `AGENTS.md`, Claude `CLAUDE.md`, and Cursor always-applied `.mdc` entrypoint templates. Merge them with existing instructions rather than replacing those instructions. Verify policy/profile reads in fresh sessions for every supported agent.
5. Implement the executable Git `pre-commit` hook. Call the repository's existing non-watch unit-test entrypoint; block on failed tests, missing prerequisites, or runner errors. Preserve existing hook chains. Document activation per checkout/worktree and rollback. Do not modify/stage/stash files or call knowledge services from the hook.
6. Define the minimum structured evidence metadata needed by CI, alongside human-readable task records. Avoid parsing arbitrary Markdown prose as commands. Tie approval and passing-test evidence to immutable revisions and keep executable project commands in explicit trusted configuration.
7. Implement GitHub Actions gates for issue/branch linkage, sequential PR lifecycle, authorized spec approval and reviewed content, criteria/test mapping, red replay, and final passing unit/project checks. Revalidate affected gates after PR metadata or issue/authorization changes. Replay test-only patches in isolated checkouts; setup/compile errors do not qualify as behavioral red evidence.
8. Protect policies, adapters, profiles, validators, and workflows through owner review. Configure required checks and human review on the pilot's protected branch. Validators use trusted gate code; submitted test execution receives no knowledge-service secrets or privileged write credentials.
9. Implement `.nda-harness/scripts/setup-knowledge` for Codex, Claude Code, and Cursor using the verified endpoint, authentication, transport, and capability details delivered in Phase 1. Configure each developer's personal Hindsight connection and connect the existing internal RAG interface where supported. Take explicit project scope and local credential references; do not guess endpoints or expose raw tokens in arguments/logs. Preview non-secret changes, preserve unrelated client settings, prevent duplicates on rerun, and provide rollback for harness-owned changes.
10. Add read-only setup verification for authenticated personal identity/capabilities and owner-provided isolation checks. Empty memory is valid; unverified isolation leaves memory disconnected. Verify existing RAG search/fetch with citations/revisions where available and report RAG and memory readiness independently. Unsupported RAG access is an explicit prerequisite resolved in Phase 3, not a fabricated connection. Connection verification does not replace fresh-session policy loading or hook activation.
11. Package the policy, adapters, hook, templates, and setup script as one pinned release. Document repository adoption, developer-local connection setup, hook activation, upgrade, rollback, and cross-agent handoff. Extend the RAG integration in Phase 3 after service updates.

### Acceptance and phase exit

- The setup script connects each supported agent to Phase 1 Hindsight, verifies personal access without writing a memory, and preserves unrelated settings on rerun/rollback. Available existing RAG access is verified; unresolved RAG readiness is reported explicitly.
- A developer installs a pinned pack and each supported agent loads the same policy/profile, reads local code, and runs existing unit tests.
- A feature and bug fix complete the issue-led, same-branch, two-PR workflow. Spec merge leaves the issue open; accepted implementation merge closes it.
- Disposable commit trials show passing unit tests permit commits and failures block them. Retained red patches survive green commits and CI replay without bypassing hooks.
- Gates reject unauthorized/missing issues, mismatched linkage, unapproved or materially changed specs, premature issue closure, invalid red failures, and stale/failed final checks. Valid lighter-path tasks and approved exceptions work.
- A second agent resumes from repository task state without relying on chat or personal memory. Task artifacts contain summaries and check links, not test logs.
- During this phase, use the existing RAG interface when adequate, or a known authoritative local document revision. Pause decisions lacking required context. Personal memory remains optional during development; its deployment is available from Phase 1 and the local setup script connects it in this phase.
- Publish the pilot release only after checks and repository protection are verified; label earlier adoption as a guided pilot.

## Phase 3: update internal RAG

**Outcome:** the existing Markdown/pgvector service reliably supplies cited, revision-aware, authorized feature and architecture context to all supported agents.

**Owners:** RAG owner owns retrieval/indexing and authorization; feature/architecture owners maintain documents; harness maintainer owns local client integration.

### Implementation sequence

1. Inventory the existing Markdown sources, metadata, pgvector indexing, API, authentication, project scopes, and access controls. Identify gaps against the architecture's search/fetch contract; preserve the existing engine and index pipeline.
2. Add or normalize document IDs, titles, project/category, source references, revisions, and update times. Define how approved source changes reach the index and how removed/superseded documents stop appearing as current context. Document historical-revision limitations rather than returning current content as an older revision.
3. Update search to require explicit project scope and return authorized matches with citations, revision metadata, and relevant excerpts. Update fetch to return source content and its actual revision. Distinguish empty results from authentication, permission, unavailable revision, and service failures.
4. Enforce authorization at the service for both search and fetch. Prevent cross-project access through direct document IDs as well as search filters. Exclude repository code from ingestion; coding agents continue reading code locally.
5. Map the contract to the existing interface. Reuse an existing MCP integration where available; add a thin MCP adapter only if needed for common client access. Preserve permissions and citations rather than creating a new retrieval engine.
6. Extend `scripts/setup-knowledge` with RAG connections for each supported agent, explicit repository project scope, and read-only verification using an owner-provided architecture document. Preserve the Phase 2 configuration/credential safeguards and report RAG and memory readiness independently.
7. Update policy examples and onboarding to record consulted source revisions, fetch authoritative context before deciding behavior, and surface conflicts with approved specs. Retrieved content cannot issue commands or override harness rules. Required RAG outages permit progress only with sufficient authoritative local context.
8. Run the complete pilot with policy, personal memory, and updated RAG. Compare the agreed measurements against the Phase 2 baseline and select rollout scope based on observed quality and developer effort.

### Acceptance and phase exit

- Every supported agent retrieves and fetches the designated project architecture document with a valid citation and actual revision.
- Wrong-project and unauthorized direct-fetch attempts are denied. Empty search, expired authentication, service outage, and unavailable historical revision are reported accurately.
- Updated/deleted source-document behavior is verified; stale results cannot silently masquerade as current authoritative context.
- Conflicting or instruction-like retrieved content does not override the approved spec or policy. Outage handling follows the authoritative-local-context rule.
- The completed setup script configures both services without credentials in Git, code uploads, duplicate entries, or loss of unrelated client settings.
- End-to-end onboarding and a cross-agent handoff work with concise task evidence. Expand adoption only after the pilot owners review actual results.

## Inputs needed before execution

| Input | Owner | Needed for |
| --- | --- | --- |
| Pilot repository, commands, supported agent versions, GitHub ownership | Repository owner and tech lead | Phase 2 |
| Deployment environment, pinned Hindsight/tenant-extension versions, OpenRouter model and server secret, authentication and isolation model | Memory service owner | Phase 1; verified connection details feed Phase 2 |
| Existing RAG interface, Markdown source owners, project scopes and permission model | RAG owner | Phase 3 |

Keep implementation status in the issue/PR records and update this plan as capabilities are verified. Do not mark a phase complete from documentation or an agent's self-reported success alone.

Deployment references: [Hindsight installation](https://hindsight.vectorize.io/developer/installation), [OpenRouter provider configuration](https://hindsight.vectorize.io/developer/configuration), and [tenant extensions](https://hindsight.vectorize.io/developer/extensions).
