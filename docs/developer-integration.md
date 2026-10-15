# Developer integration

Status: onboarding design for the [architecture proposal](architecture.md), with the minimal CLI phase implemented as described below. The broader adoption steps include proposed future work; CI validators are not shipped yet.

## Implemented minimal CLI phase

For Codex, Cursor and Claude Code (CLI and Desktop local Code tab) on Apple Silicon macOS, use the
[minimal CLI onboarding guide](compatibility/minimal-cli-phase.md). It documents
the implemented setup/verify commands, both scopes, project unit-test hooks,
five explicit context operations, automatic verification with pending session checks, pinned dependencies
and backup restoration. The broader architecture/adoption procedure below still
contains proposed future work; Intel, native lifecycle registration and
remote approval/CI enforcement are not shipped by this phase.

## What runs where

Developers keep using their existing local coding agent and project tooling. The agent reads code from the local checkout. Internal RAG supplies feature and architecture documents; self-hosted Hindsight supplies the current developer's personal preferences and working notes. It is not a shared organization fact store. Neither service becomes a copy of the code repository.

The harness is a versioned set of instructions, workflow documents, and repository settings. Agent-native file and terminal tools do the coding. MCP supplies service access where available; it is not a mandatory runtime wrapper.

Repository maintainers prepare shared project configuration once. Each developer configures local authentication and verifies their selected agent. Global personal preferences remain local, while the required project workflow stays reviewed and committed.

## Maintainer: prepare a repository

### 1. Pin the shared package

After a release exists, copy the approved release's policy and workflow into `.nda-harness/` in the target repository. Record its immutable release revision and source. Commit these files in an adoption PR; do not use mutable links to a developer's global configuration or a remote latest policy.

The proposed layout is:

```text
.nda-harness/
  policy.md          # shared stage rules, evidence, and stop conditions
  workflow.md        # detailed process from the approved harness release
  profile.md         # repository-specific commands, scopes, and ownership
  release.md         # pinned source/revision and reviewed local deviations
  skills/
    catalog.md       # discovery metadata, not all skill instructions
    ui-ux-pro-max/   # SKILL.md, bundled resources, license, pinned provenance
    vietnamese-official-wording/SKILL.md
    diagram-design/  # SKILL.md, references, templates, scripts, license/provenance
  hooks/
    pre-commit       # proposed executable unit-test hook
  scripts/
    setup-knowledge  # proposed RAG/Hindsight/Context7 connection setup
```

This is a package design, not an existing downloadable release. Keep specs and task records in the project's existing locations when possible; record those locations in the profile. Do not duplicate them into memory.

### 2. Complete the repository profile

| Profile information | Maintainer action |
| --- | --- |
| Project identity | Set stable repository and RAG project identifiers; keep personal-memory identity in developer-local configuration and do not infer scopes from folder names |
| Setup | Record runtime/tool versions, installation steps, environment prerequisites, and working directory |
| Checks | Record targeted unit-test, relevant unit-suite, and applicable lint/type/build commands; preserve existing runners and identify integration/end-to-end verification as QA-owned |
| Local hooks | Identify the executable unit-test entrypoint, existing hook setup, activation procedure, and checks for every checkout/worktree |
| Specifications and tasks | Use GitHub issues as feature specs; identify developer-spec/task locations, criterion mappings, consulted issue content references and evidence locations |
| Approvals | Name the roles/people authorized to approve specs, exceptions, and changes; use spec-only GitHub PR approval before implementation and record review references |
| GitHub issue policy | Record the repository/default branch and authorized tech-lead GitHub identities; require an issue number in task branches and matching references in specs, task records, and PRs |
| Services | Record non-secret connection instructions, service owners, outage contacts, and required retrieval/write permissions |
| Compatibility | Record tested agent versions/surfaces, known limitations, pinned harness revision, and reviewed deviations |

Setup details must let another developer reproduce the baseline without guessing commands. If existing tests fail, record and resolve or explicitly account for them before claiming new red/green evidence.

### 3. Connect agent entrypoints

Add an entrypoint for each agent the team uses. Preserve existing instruction content and audit relevant global/nested rules. Entrypoints must state the mandatory boundary directly: read the shared policy and profile before work; behavior changes require an approved spec and red evidence; do not silently waive gates. The detailed process stays in `.nda-harness/`.

| Agent | Repository entrypoint | Integration action |
| --- | --- | --- |
| Codex | Root `AGENTS.md` | Add explicit instructions to read `.nda-harness/policy.md`, `workflow.md`, and `profile.md`; verify applicable nested files and overrides |
| Claude Code | Root `CLAUDE.md` | Add the same read instructions using project instructions; review personal/project instruction interactions |
| Cursor | `.cursor/rules/nda-harness.mdc` | Use an always-applied project rule with `alwaysApply: true`; put the mandatory boundary in the rule body and direct the agent to read the shared files |

These files configure agent instructions, not provider system prompts. File references alone do not establish that an agent read the full policy. Verify loading in a fresh session. Cursor project rules require `.mdc`; a plain `.md` rule is ignored, and referenced files are not automatically inlined. See [Codex instruction discovery](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [Claude project instructions](https://code.claude.com/docs/en/memory), and [Cursor rule loading](https://cursor.com/docs/rules).

Resolve a conflicting personal or nested instruction with the maintainer before adoption. Agent/platform security restrictions remain effective. A repo entrypoint cannot guarantee precedence over every user setting or enforce local edits by itself; merge checks provide the common enforcement boundary.

### Select skills for each assignment

Follow the architecture's [discovery and loading contract](architecture.md#metadata-first-discovery-and-loading). Configure startup to load mandatory policy/Superpowers and catalog metadata; the coordinator selects IDs before a child reads specialist bodies. Keep native registration metadata-only, with no recursive imports of the hub.

Copy the source [Skills hub](../skills/catalog.md) with the pinned package. Entrypoints direct the coordinating agent to the catalog; they must not inline or recursively import every `SKILL.md`. Native skill registration should expose names/descriptions for discovery and load selected bodies on demand. Preserve existing skill configuration and verify the actual client behavior; the repository folder alone does not install native skills or delegation support.

For a new sub-agent, give a bounded assignment with policy/profile paths, exact selected skill paths and pinned revision, issue/task, repository revision, relevant input references, allowed scope/side effects, output, and stop conditions. Use a fresh/minimal context mode where supported. A UI child loads `ui-ux-pro-max`; a formal Vietnamese drafting child loads `vietnamese-official-wording`; a diagram child loads `diagram-design`. Backend/test-review work may need none. Select multiple only when they apply. Do not pass the whole hub to every child or inherit unrelated history. If the client cannot isolate instruction loading, use a fresh separate session and record the limitation.

Record selection/scope and returned findings in the task record. Skill findings do not replace approval or CI. Keep credentials and personal-memory content out of child assignments. Capability checks during onboarding/upgrades, context preparation at task start/resume, and test-quality review before code review finishes remain harness workflow responsibilities, independent of hub skills. The proposed `doctor` diagnostic can automate readiness later; today use existing tools for these checks. UI/UX Pro Max requires Python for its bundled local search; resolve its skill directory from the assignment, not a hardcoded agent plugin path. The Vietnamese skill uses the document owner's templates and glossary, and requires human approval for issuance. Diagram Design resolves its resources relative to the selected skill directory, loads only relevant type references, and preserves the approved project style. Use its bundled self-check; upstream repository-only development gates are not part of the vendored skill.

For each agent/version/surface, maintainers record which native lifecycle events can introduce catalog metadata, validate delegation, and initialize child context. Preserve existing Superpowers/RTK hooks and avoid duplicate startup injection. Event names and supported interception differ by client: do not copy another agent's hook configuration and assume it works. Where hooks are unavailable, use entrypoint instructions and a bounded fresh-session assignment; record the weaker enforcement explicitly. The Git pre-commit hook is independent of discovery.

Before claiming readiness, try a fresh diagram assignment and a backend assignment with no specialist skill. Inspect actual context/tool inventories or file-read evidence where the host exposes them; verify the diagram child loads `diagram-design` without UI/UX or Vietnamese bodies, and that parent history is not fully inherited. Confirm selected IDs/paths and catalog revision are recorded. Test rejection of unknown IDs, stale revisions, and missing resources. An agent's self-report is not proof of absence; mark unavailable inspection as unverified.

Inspect MCP exposure separately. Use native tool allowlists/lazy discovery where supported, preserve platform permissions, and record fixed/global tool definitions that cannot be hidden. A fresh session does not remove globally injected skill bodies/tool schemas. If the current surface cannot provide scoped specialist loading, use a verified configuration/surface; do not claim isolation from instructions alone. These adapter hooks and automated checks remain future tooling.

### 4. Prepare the local hook

The future package includes a Git `pre-commit` hook that runs the existing non-watch unit-test command before each normal commit. Test failures, runner errors, or missing prerequisites abort the commit. Reuse the repository's installed hook tooling and preserve existing checks; otherwise use the package's executable `.nda-harness/hooks/pre-commit` with repository-local `core.hooksPath`. Do not introduce another hook manager for this one check.

Maintainers verify pass/fail behavior in a disposable checkout and document the actual command. The hook must not edit/stage/stash files or access knowledge services. Agent-native hooks remain optional additions; the Git hook covers commits through Git regardless of which coding agent initiates them. See [Git hook behavior](https://git-scm.com/docs/githooks).

### 5. Prepare merge enforcement

In the subsequent tooling phase, add the architecture's issue/branch, PR lifecycle, spec/approval, traceability, red replay, and final green checks using GitHub Actions. Validate authenticated issue authors against the trusted tech-lead list, consistent issue references, the shared source branch, and non-closing spec versus closing completion PRs. Revalidate when relevant GitHub metadata changes. Configure required checks and human review, with owner review for harness and gate changes. See [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches).

Until executable gates and branch requirements are installed and validated, label adoption as a **guided pilot**, not strict merge enforcement. Reviewers must inspect evidence manually during that period.

## Developer: connect a local agent

### 1. Open the adopted checkout

Use the project's normal setup procedure and the same checkout/branch for the task. Confirm the committed harness revision and profile match the repository. Run the baseline checks before requesting a behavior change.

Once executable hooks ship, activate them for this checkout using the documented project setup. For a repository with no existing hook configuration, the native fallback is `git config --local core.hooksPath .nda-harness/hooks`; confirm `pre-commit` is executable. Inspect existing configuration first and preserve its checks rather than replacing it blindly. Cloning committed hook scripts does not activate them. Repeat verification for additional worktrees and for Git/agent commit paths you use.

Start a fresh agent session at the repository root so the project entrypoint is discoverable. Ask the agent to identify loaded instruction sources, read the shared files, summarize the mandatory stages, and report any conflict. Verify the cited files and rules yourself; a confident summary alone is not a loading check.

### 2. Configure knowledge access

Obtain the internal RAG interface and Hindsight endpoint from the service owners. Use approved VPN/network access and per-developer authentication. Do not connect the public Hindsight hosted endpoint as a substitute. Keep keys/tokens in supported local secret storage or environment configuration, outside Git; never paste them into prompts, specs, or evidence logs.

Context7 is a required documentation integration, not a Skills hub entry. Use the maintainer-approved MCP transport/authentication or an approved CLI route from [Context7's official setup documentation](https://github.com/upstash/context7). Keep credentials local and preserve existing client settings. Pin locally executed packages; record the hosted connection/tool contract and verify it per supported surface. Do not install a mutable `latest` package or auto-load an extra skill collection just to configure documentation access.

Use Context7 for library/framework API, setup, and configuration questions when relevant. Inspect installed versions locally, resolve the correct library ID, then query the focused topic/version. Record returned source/version information; do not assume current docs cover an older installed version. Queries must not contain proprietary code, internal requirements, personal memory, or credentials. See the [documentation-access contract](architecture.md#context7-documentation-access) for version gaps and outages. Make it available to children that need documentation through supported scoped/lazy tools, without injecting full documentation into startup context.

| Agent | MCP setup route | Local verification |
| --- | --- | --- |
| Codex | Use its supported MCP configuration or CLI management; follow the [Codex MCP guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) | Confirm the configured server is available in the selected local surface and authenticated tools can be called |
| Claude Code | Add the approved server through Claude Code's MCP management and authenticate as required; follow [Claude MCP setup](https://code.claude.com/docs/en/mcp) | Confirm server status and available tools in the current project/session |
| Cursor | Add the approved server through Cursor MCP settings/configuration; follow [Cursor MCP setup](https://cursor.com/docs/mcp) | Confirm connection status and enabled tools in the local agent |

No common config file format is assumed across clients. Use each client's supported configuration for the deployed transport and authentication; restart/reconnect where needed. Commit only non-secret, portable connection information if the client supports it. Credentials and developer-specific paths stay local.

#### Pack-provided setup script

The release must include `.nda-harness/scripts/setup-knowledge` to perform this connection setup and verification for the selected agent. This is a proposed executable in the next tooling phase, not a script shipped by the current documentation. The script configures local **agent connections** to internal RAG/Hindsight and approved Context7 documentation access. It does not deploy RAG or Hindsight backends on developer devices.

The script has the following contract:

1. Read the pinned release and repository profile, then take the agent choice, owner-supplied internal endpoints, RAG project scope, and developer-local credential references. Do not guess endpoints, transports, tool names, or personal identity. Use the client's supported authentication flow; do not take raw tokens in command-line arguments or print them in logs.
2. Check the installed agent's supported integration and inspect its existing configuration. Preview the exact non-secret configuration changes, preserve unrelated servers/settings, and add or update only harness-owned connections. Keep machine-specific values and credentials outside the committed package. A missing supported integration is an actionable prerequisite, not permission to install a new agent or retrieval engine.
3. Apply the selected client's configuration using its supported mechanism. Make reruns safe: no duplicate server entries, no destructive replacement of existing settings, and no silently changed endpoint or identity. Retain a local backup for file changes and document how to undo only the harness changes.
4. Verify authenticated RAG search/fetch for the explicit project scope against an owner-provided architecture document, including citation and actual revision. Verify Hindsight's authenticated personal identity, available capabilities, and owner-provided isolation check. Do not write a memory just to test onboarding; an empty account is valid. If identity/isolation cannot be established, leave memory disconnected.
5. Configure Context7 through the selected client's approved mechanism and credential references. Verify public-library resolution followed by a focused documentation query with actual source/version information. Use only public, generic test queries. Report authentication, rate-limit, coverage, and service failures explicitly; do not fabricate matching documentation.
6. Report readiness separately for RAG, memory, and Context7 with actionable connection, permission, capability, or configuration errors. Do not report authentication failures as empty results. Required RAG/Context7 setup failure prevents claiming onboarding complete; optional memory failure permits work using authoritative repository/RAG context. Emit only a sanitized summary suitable for the adoption review.

The script does not upload repository code, seed shared memory, modify agent policy, activate Git hooks, or run on every commit. Connection verification does not replace the fresh-session policy-loading and local-code checks below. Endpoint changes and upgraded agent integrations require another setup/verification run.

If the existing RAG provides HTTP rather than MCP, use an already-approved tool integration. Do not fabricate MCP tool names or build a second RAG to finish onboarding; record missing shared access as an integration prerequisite. A future thin MCP mapping should preserve the existing service's permissions and citations.

Hindsight's [self-hosted MCP server](https://hindsight.vectorize.io/developer/mcp-server) is the connection target. Authenticate with your individual Hindsight credentials and verify your tenant, bank, available memory tools, and denied cross-developer access. The service owner configures a tenant extension with separate database schemas; a bank name or shared API key alone does not provide personal isolation. Keep personal-memory identifiers and credentials local. You control personal saves and any supported automatic capture; no maintainer publication or tech-lead approval is required.

OpenRouter is configured on the internal Hindsight server by the service owner, not on each developer's device. The local setup script needs only the internal endpoint and developer's Hindsight credentials; it must not distribute the server's OpenRouter key. Storage is internal, while memory-processing prompts go through OpenRouter to the selected model provider. The owner supplies the approved model/routing and data-handling configuration. See the architecture's [Hindsight deployment contract](architecture.md#self-hosted-hindsight).

Use the internal dashboard to inspect your own memories and correct or invalidate stale notes. Verify that dashboard access respects the same tenant boundary as MCP/API access; a dashboard configured with a shared administrative credential must not be exposed as a personal-memory portal.

### 3. Verify readiness

Use an existing approved feature/architecture document from the RAG owner and, if available, a note from your own personal memory. Onboarding should be read-only apart from ordinary build/test artifacts; do not create or expose another developer's memories merely to test the connection.

| Check | Evidence to inspect | Pass condition |
| --- | --- | --- |
| Policy loading | Agent's loaded sources and actual reads | Correct pinned policy/profile loaded; no unresolved conflict |
| Local code access | Agent names a relevant file and traces a real caller | Code read from this checkout rather than requested from RAG |
| Test execution | Unit-test baseline command and result | Existing unit runner works or known failures are explicitly accounted for |
| Pre-commit activation | Effective hook configuration and disposable passing/failing commit trials | Unit checks run and failures abort commit; existing project hook checks are preserved |
| RAG retrieval | Scoped search plus fetched source citation/revision | Correct project architecture document is accessible and cited |
| Context7 retrieval | Public library resolution, focused query, actual source/version metadata | Correct library and applicable version verified on this surface; no private task data included |
| Memory recall | Authenticated identity and own relevant note, if one exists | Correct personal account/scope; empty personal memory is acceptable |
| Isolation | Owner-provided authorized/denied access check | Server enforces RAG permissions and separation of developer memories; a project tag alone is not authorization |

An empty personal memory is a valid starting state; verify authenticated access without requiring a seeded lesson. Do not interpret an auth error as an empty result. If isolation cannot be verified, leave Hindsight disconnected and continue the harness using required repository/RAG context. Record agent version/surface, harness revision, and readiness findings in the adoption review without credentials or personal-memory content.

## Daily work

### Tech lead: scope and document intent

The GitHub issue is the feature spec. The future pack includes `scope-initiative` for discovery when needed, `document-requirements` for issue authoring/revision, an issue-body template and a `scaffold-brief` helper. Draft the problem, users, desired outcome, in/out of scope, expected behavior/flows, failure cases, observable acceptance criteria, constraints, sources and open decisions. Supporting scope/architecture documents are optional; no separate feature-spec document is required. Drafting/review may begin before an issue exists. These capabilities are planned, not installed by this guide.

Use `review-spec` on the issue draft or published content to check clarity, outcome, scope, completeness, contradictions, missing flows and verifiable criteria. It returns prioritized findings with locations, impact, suggested resolutions, the reviewed content reference and remaining blockers. Revise through `document-requirements`, resolving product decisions with the tech lead. The authorized tech lead explicitly creates/updates the issue through existing tools and review practices; drafting and agent review do not implicitly publish it. No additional feature-spec PR gate is required.

The same `review-spec` skill assesses developer-spec drafts/PRs for issue alignment, feasibility, interfaces/edge cases and unit/QA coverage. Human approval and merge of the developer-spec PR remain required before implementation. Optional supporting-document publication into RAG stays with the existing source-owner process.

### Developer: execute SDD

The planned `execute-sdd` skill guides the full lifecycle and invokes `scope-task`, `write-spec`, and `document-change`. Use `prepare-context` for local context, `scaffold-task`/`validate-artifacts` for task/spec documents, `verify-task` for authenticated issue/approval prerequisites, and `capture-red` for complete test-only checkpoints. Actual commands and client skill discovery must be shipped and validated before use; the same procedures remain readable through the entrypoint fallback. Developer scoping refines implementation within the tech lead's intent; changed outcomes return to the owner and specification approval.

The tech lead first publishes the feature spec as an issue in this GitHub repository. Provide its URL/number through normal chat and ask the agent to follow the repository's NDA Harness workflow. The agent verifies the issue exists, is open, and was authored by an authorized tech lead before task work. It does not create a substitute issue or accept an unverified pasted author name. No new command or slash-command availability is assumed.

1. The agent reads the feature issue, classifies the task, inspects local code/callers, and retrieves relevant supporting sources plus personal preferences when available. Record the issue URL, update time and content fingerprint used for specification; unresolved product choices go to the tech lead. Personal memory cannot override project policy or approved behavior.
2. For issue #123, use `feat/123-<feature>` to draft the developer spec: issue-criterion coverage, implementation-ready behavior, interface changes, edge cases, design decisions, focused unit-test mapping and QA scenarios. Reference feature requirements rather than copying them; record the issue content reference in the spec/task record. Validate structure/links and use `review-spec` to find alignment, feasibility and coverage gaps, then revise. Open a spec-only GitHub PR with `Refs #123`; the authorized human reviews and approves it remotely. Merge the approved spec before implementation, retaining the branch and leaving the issue open.
3. Fetch main and merge it into the same `feat/123-<feature>` branch, then verify the approved spec. Before implementation, retain the complete unit-test-only red change as a patch against the recorded base, including new tests, and record the expected failing result. Implement green increments and refactor with unit tests passing, then commit the retained patch as evidence alongside green code/tests. Pre-commit checks run on normal commits; do not bypass them to commit failing red tests. Add meaningful tests for changed logic/regressions, without a fixed count or new integration/end-to-end suite.
4. The developer reviews the diff and evidence, then opens a second PR from the same feature branch with `Closes #123` in its body. The implementation PR links the merged spec PR, approval review, spec revision, task record, and results; future required gates replay and validate them. Confirm acceptance criteria before merging, then verify issue closure. Delete the branch only after this PR merges. If GitHub deleted it after the spec PR, re-push the retained local branch under the same name.

Daily development ends at merge. Personal-memory updates are handled through the developer's Hindsight integration outside the development cycle. Any additional learning workflow is deferred to a future phase.

Include a brief QA handoff in the implementation PR: approved spec reference, integration/user-journey scenarios, and known limits. QA handles these using the existing team process. Harness checks validate unit tests and relevant lint/type/build results; they do not require an agent-created integration/end-to-end flow or a new QA sign-off gate. Green unit results do not imply those QA scenarios passed. Existing repository checks are not removed by this policy.

Stage the source/test/config changes you tested before committing. The pre-commit hook runs against the working tree, while CI verifies the committed PR snapshot. Do not disable hooks or use `--no-verify` to evade failing checks; any authorized bypass must be recorded and does not waive CI.

Keep test evidence brief in the repository task record: tested commit SHA, command/suite, pass status, and the successful GitHub check/run link for that revision. Local checks use the same summary without a CI link; CI supplies the verified merge proof. Do not commit test logs or require separate log artifacts. Keep the red test patch, base revision, and expected failure for replay, without a red log. GitHub's ordinary run output can be consulted for troubleshooting when needed.

For docs or mechanical work, the tech-lead issue and issue-numbered branch are still required; reuse the repository's branch prefix. Record the classification, run relevant existing checks, and obtain review in a single completion PR with `Closes #<issue>`. For untestable behavior, seek the recorded exception with alternate verification; it does not waive issue linkage. When approved behavior changes, stop dependent implementation and renew the spec approval and affected evidence in a spec-change PR referencing the same issue.

Spec and spec-change PRs use plain `Refs #<issue>` references only. Do not add a manual closing link in GitHub's Development sidebar or a closing keyword in their bodies or commit messages. Completion PRs target the default branch so `Closes #<issue>` can close the issue on merge. These GitHub behaviors are described in [issue linking](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue). If automatic closure is disabled, the tech lead closes the issue after verifying the accepted implementation merged.

For spec approval, the agent summarizes the exact spec revision and decision needed, then waits for the GitHub approval/merge. The tech lead uses GitHub on their own device, not the developer's local agent. The developer or agent verifies the authorized Approve review and merged content using existing GitHub access, fetches the merged spec, and records the PR URL, review reference, approved head revision, and merged spec revision/path before Red. A comment, silence, local chat, or an agent-written flag is insufficient. See [GitHub PR reviews](https://docs.github.com/en/pull-requests/reference/pull-request-reviews).

If the spec PR is rejected or updated after approval, resolve feedback and obtain approval for the final spec content. Material requirement changes during implementation use another spec-change PR; dependent work waits for its approval and merge. Final code approval is a separate decision and cannot retroactively approve the spec-first step.

Recheck feature-issue content on task start/resume and before dependent stage transitions, even when local HEAD is unchanged. Compare it with the recorded content fingerprint; an update time alone is not an immutable revision. Reconcile edits with the tech lead, record editorial-only changes, and obtain renewed developer-spec approval/merge for material behavior changes before affected work resumes. An edited issue never silently overrides the approved developer spec, and pending/stale approval cannot unlock implementation.

## Pause, resume, and switch agents

Before pausing, update the task record with the primary issue URL/update time/content fingerprint, branch and PR references, current stage, harness/spec revisions, approval reference, acceptance mapping, completed red/green cycles, known failures, unresolved questions, next action, and working-tree state. Preserve checkpoints and reviewable local changes through the project's normal version-control practice. Do not discard unrelated developer work or commit secrets to create a handoff.

The receiving agent loads its own entrypoint and the same pinned policy/profile, reads the task record and source artifacts, inspects the actual checkout/diff, and confirms which evidence still applies. It verifies that required checkpoints exist and that the current revision matches the record. Changed state is reconciled before proceeding; completed work is not repeated solely because the agent changed.

Switching agents does not reset human approval, change the RAG project scope, or justify skipping a gate. A developer switching tools connects their own memory account; a different developer uses their own account and relies on repository artifacts for the handoff. Do not share personal-memory credentials or require access to the previous developer's memory. Verify the recorded GitHub spec PR and approval against the current spec content. If private/local chat was the only approval record, complete the spec PR approval/merge before relying on it. Use repository task state, not a personal conversation or memory profile, for continuity.

## Upgrade and rollback

The maintainer reviews an immutable new harness release, compares policy/workflow and adapter changes, and updates the copied package through a PR. Re-run readiness walkthroughs for supported agents and verify evidence compatibility before adoption. Record local deviations explicitly instead of silently modifying shared rules.

Active tasks retain the recorded policy revision unless the maintainer explicitly migrates them and revalidates affected approvals/evidence. Do not claim an older task meets new requirements without checking. Roll back a problematic package through a normal reviewed revert; reconcile active tasks and retain the evidence history. Do not remove branch protection as an upgrade workaround.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Missing, inaccessible, closed, or unauthorized issue | Pause task work and ask the tech lead to create, reopen, or correct the repository issue; a TDD exception cannot waive this requirement |
| Issue number differs between branch, spec, task record, or PR | Correct the linkage before continuing; checks must validate the same primary issue |
| Spec PR would close the issue | Remove closing keywords/manual closing links, including closing commit messages; use `Refs #<issue>` and keep the issue open |
| PR body or issue state/content changed after a green check | Re-run affected validation and reconcile issue edits with the tech lead; material behavior changes require renewed developer-spec approval before affected work resumes |
| Implementation merged but issue stayed open | Verify the default-branch target and repository closure settings; tech lead closes it after confirming acceptance |
| Pre-commit does not run | Check the effective hook path, executable permission, checkout/worktree activation, and actual commit command; do not claim local enforcement until verified |
| Pre-commit unit tests fail | Fix code/tests or runner prerequisites and retry; retain red evidence as a patch instead of bypassing the hook |
| Hook uses a different runtime from the terminal | Make required runtime/tool paths available to the actual Git/agent commit environment; missing prerequisites must block clearly |
| Agent starts coding before approval | Stop dependent work, inspect loaded instructions, and restore the approved-spec boundary; do not treat completed code as retroactive approval |
| Policy not loaded | Check root/session, entrypoint discovery, nested overrides, and referenced-file reads; start a fresh session after correction |
| Cursor rule missing | Check `.mdc` extension and `alwaysApply: true`; verify active rule in a fresh session |
| MCP connection/auth failure | Check approved endpoint, network/VPN, client configuration, transport, and local credentials; report to owner without logging secrets |
| RAG unavailable | Record outage; use a known authoritative local source if sufficient, otherwise pause the affected decision |
| RAG document contradicts spec | Cite both revisions and ask the spec owner to reconcile; do not silently override approved behavior |
| Personal memory stale or unavailable | Follow current policy/specs and authoritative sources; correct your own notes when needed and continue without memory |
| Personal memory save fails | Report the failed save to the developer; retry if useful, without blocking task completion or merge |
| Memory account is shared or isolation is unverified | Disconnect memory and ask the service owner to provide individual authorized scopes; do not expose other developers' notes |
| Red replay only fails at setup/compile | Repair test/environment so an expected behavioral assertion fails, or obtain an explicit exception |
| Evidence/checkpoint missing after squash | Recover retained evidence or regenerate and re-review it; do not claim reproducibility from a pasted log |
| Final tests pass but gate fails | Repair missing linkage, approval, replay evidence, or stale revision; green tests alone do not satisfy the process |
| Agent switch finds mismatched task state | Reconcile the actual diff/revisions with the record before resuming |

## Adoption acceptance

A maintainer and developer must execute the architecture's [pilot walkthroughs](architecture.md#ownership-and-pilot-validation), including fresh-session onboarding for each supported agent. Record actual outcomes and friction. Documentation review alone does not establish working service access or CI enforcement.

Start with one repository, verify the guided workflow and pre-commit hook, implement and validate merge gates, then expand based on measured quality and effort. Additional plugins, agent-specific hooks, and orchestration are optional improvements only when the pilot exposes a concrete need.
