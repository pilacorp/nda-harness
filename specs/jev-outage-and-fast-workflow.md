# Jev outage fallback and fast SDD workflow

- Status: Proposed for review
- Feature issue: [#60](https://github.com/pilacorp/nda-harness/issues/60)
- Issue updated at: 2026-11-10T03:11:30Z
- Issue body SHA-256: `38b02d9d699c244e05e6b6914a0313030a04b73db2a974809ce9430229924513`
- Spec branch: `codex/60-jev-fast-workflow`
- Consulted sources at `cc504b024b6a`: [Jev MCP contract](jev-mcp.md), [harness policy](../pack/policy.md), [workflow](../pack/workflow.md), and [delivery plan](../plan.md)

## Outcome and scope

The coding agent can finish specialist selection when the Jev MCP tool is
unavailable. Repositories can opt into a single-PR workflow that preserves a
human-approved spec before implementation and human review before merge.
Both are behavior changes. The current Jev spec requires a pause during an
MCP outage, and the current feature workflow requires a reviewed and merged
spec before coding. This draft proposes changing both rules.

## Jev MCP outage

- Use native Jev MCP when it is available. Keep its existing missing-key
  `local-agent` round trip, cache, and credential handling.
- When native discovery or invocation establishes that Jev MCP is absent,
  disabled, failed to start, or denied, surface `jev_mcp_unavailable` and use
  the release's bundled catalog metadata. The running agent answers the same
  questions without MCP, credentials, an OpenRouter call, or a shell rerun.
  An interrupted call with unknown delivery still follows the existing
  reconnect procedure.
- Apply the existing probability thresholds. Exclude scores at or below 0.20,
  include scores at or above 0.80, and ask the user about each score in between.
  Load only selected entrypoints from the verified installed bundle through
  permitted client tools. An empty selection is valid. When bundle integrity
  or access cannot be verified, pause work that needs the affected skill.
- Record `local-agent`, the catalog revision, selected IDs, and any human
  decisions in the task evidence. Claim a Jev cache entry only when MCP
  actually created one. A failure reported by a responding Jev server follows
  its own diagnostic. Skill selection never authorizes implementation.

## Fast SDD workflow

- Add an opt-in `workflow_mode: "fast"` to committed
  `.nda-harness/config.json`. For workflow authorization, use the configuration
  on the authenticated target branch. A missing mode uses the current strict
  workflow. Invalid or unverifiable configuration cannot activate fast mode.
  A PR or worktree cannot authorize its own change of mode.
- Keep the published issue and the developer spec with testable acceptance
  criteria. Before implementation, verify an explicit sign-off on the issue
  from an authorized repository owner. It must identify the spec path and the
  exact commit containing its approved contents. Verify the remote commit,
  current issue intent, signer authority, and matching local spec. A draft PR
  or a pushed spec-only commit can make that revision available without an
  upfront spec merge.
- Recheck the evidence at start, resume, and dependent transitions. Material
  changes to the issue or approved spec require fresh owner sign-off before
  continuing affected implementation. Missing or inaccessible evidence pauses
  that transition.
- Keep Red → Green → Refactor and the local test gate. Ship the spec,
  implementation, and acceptance tests in one PR linked to the issue. Require
  passing CI and a human owner to record review of the final head revision
  before merging. The owner may also be the PR author. Changed heads require
  fresh final review evidence. Automated agents and hooks cannot sign off.
- The harness respects existing GitHub protections and does not edit them.
  Repositories whose rules require an independent reviewer must still satisfy
  those rules. The existing strict, bug-fix, and documentation paths retain
  their current requirements.

## Acceptance and planned checks

| ID | Scenario | Expected result |
| --- | --- | --- |
| AC-01 | Client starts with Jev absent, disabled, or denied | Agent classifies from the installed catalog without credentials, network, or shell reruns. A backend task can return zero specialists. |
| AC-02 | Outage assignment yields an uncertain score or an invalid bundle | Human confirmation is required for each uncertain skill. Invalid bundles cannot supply skill bodies. |
| AC-03 | Native Jev responds, with or without a key | Existing MCP selection, missing-key fallback, and failure diagnostics still apply. |
| AC-04 | Target branch has no fast opt-in, but the working branch enables it | The strict two-PR requirements still apply. |
| AC-05 | Fast mode is enabled and owner sign-off matches the remote and local spec | Issue-linked TDD can start before spec merge. Missing authority, mismatched content, or material issue changes pause affected work. |
| AC-06 | Fast PR has passing CI and human review of its final head | The owner can merge subject to GitHub protections. A stale review or failed CI does not satisfy the fast path. |

Add unit checks for fallback classification, configuration and evidence
validation. Exercise real MCP unavailability with each supported client
(Codex, Cursor, and Claude Code), including a client with no provider
credentials. Exercise strict and fast end-to-end cases in a test repository.
These are planned checks.

## Packaging and rollout

Update the source policy, context guidance, templates and injected client
instructions together. Regenerate the client packages from source so stale
guidance cannot reintroduce the outage pause or require a separate spec merge
in fast mode. Check that the test gate makes no additional network calls.

## Review and implementation handoff

Verify the live spec PR approval, merge, and exact spec revision under the
current strict workflow before starting implementation.
