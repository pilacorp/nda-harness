Issue: https://github.com/pilacorp/nda-harness/issues/16
Spec: specs/jev-skill-selection.md
Revision: 03f6a8aa15db6313b4ea80cc3601ea8b0bc1e28d
Stage: specification
Evidence: live issue read on 2026-10-20; source/documentation review and independent builder check; JSON examples and document structure validated; no implementation or paid API tests
Next action: obtain GitHub review and merge of the spec-only PR; implementation requires reviewed merged spec

Branch: spec/jev-skill-selection, explicitly requested by the owner.
Issue updated at: 2026-10-20T02:03:51Z
Issue body SHA-256: 5356e7566b6cd93ca4ae2e1fea31cc38ad22309c8e6013262a9726fbb5b23201

Owner approval: approved in chat on 2026-10-20, with explicit instruction to update
status, commit, and create a PR. GitHub review and merge remain pending.

Specification scope: client-side Jev skill selection through OpenRouter using individually
provisioned keys; setup steps first, then implementation contracts, acceptance
mapping, and verification requirements. Hindsight and a hosted decision hub are
outside this task. Proposed setup stores keys in macOS Keychain through a hidden
person-operated terminal prompt. No credentials were accessed or requested.

Selected specialist skills: none; this is software specification drafting.
Workflow sources: repository developer-spec template, writing-plans guidance for
implementation handoff, and brainstorming builder-check guidance. Reviewed public
OpenRouter documentation via Context7 and primary web sources.

Builder-check findings resolved: explicit project/session active-selection state
prevents loading obsolete task input; failed refresh invalidates the old shared
loadable entry. These are specification decisions, not implemented protections.

This checkout has not been adopted as a configured plugin project. The earlier
session-bootstrap returned configuration_conflict. Continue specification review;
do not infer test setup, activate hooks, or treat local metadata as authorization.
Input fingerprint is not available from a ready helper; no checkpoint readiness
or approval is claimed. Original unrelated untracked files were preserved.
