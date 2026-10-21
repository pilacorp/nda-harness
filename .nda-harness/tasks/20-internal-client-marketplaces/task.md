# Internal client marketplaces

Issue: https://github.com/pilacorp/nda-harness/issues/20
Role: developer
Stage: implementation
Revision: 61cafbf2b915b72282e5a4ade7b73356bf52d510
Spec PR: https://github.com/pilacorp/nda-harness/pull/21
Spec: specs/internal-client-marketplaces.md
Input fingerprint: 2e668a937664fd7e7b6c52d80027118ca0ccf8c3d5b4032b0dd6cdc7de66daa2

Intent: use the existing private repository for Codex, Cursor, and Claude native marketplaces, with a separate bound package per client and native version updates. No separate marketplace service, public publishing or credential migration.

Evidence: docs/compatibility/internal-client-marketplaces.md. Baseline 194 tests passed. New marketplace tests failed before implementation, then passed. Boundary tests reproduced malformed metadata and partial publication before fixes. Final full suite passed 201 tests in 92.357 seconds. Independent read-only review found only a first-install documentation dependency on RTK; fixed by invoking native install/update commands directly. No code findings remain. Repository regeneration preserved all 2187 distribution file bytes/modes; diff whitespace checks passed. Native Codex CLI 0.133.0 and Claude 2.1.263 installed 0.0.4, updated to fixture-only 0.0.5 and preserved installed-cache bytes/activation after unavailable Git fetch, all using disposable homes and a local Git rewrite fixture.

Completed: merged spec verified; requested branch created from latest dev. Existing publisher now stages/validates all three 0.0.4 packages plus native root catalogs and restores prior outputs on replacement failure. Added routing/version/determinism/failure tests; reused and tested existing hook rebind recovery. Updated installation, migration/update/recovery docs, README and superseded plugin-spec exclusions. No live client changes, login, push, publishing or PR creation.

Open checks: human implementation review; real private Git access; Cursor Teams/Enterprise dashboard import/dev ref and installed refresh; Desktop activation/trust; real initial identity migration and optional native authentication; invalid native import and reviewed release recovery.

Next action: create the user-requested implementation PR against dev after pushing the reviewed verification note; human review and pending native rollout checks follow.

PR review (2026-10-21): user requested spec-compliance review and PR creation if OK. Issue #20 and merged PR #21 were independently revalidated; local marketplace spec is unchanged. Initial 0.0.4 is present at 55d33f5; current successor 0.0.5 includes Python 3.9 compatibility. Full suite passed 203 tests on Python 3.12.12 and 203 on Python 3.9.6. Independent review found no code blockers and verified all 2181 asset hashes. One stale evidence-doc statement about the current version was corrected. Guide links/anchors and authored whitespace checks pass. All eight acceptance criteria are covered by implementation, documentation and tests; spec-permitted native provider/Desktop/auth checks remain explicitly pending. No new runtime edits made during this review. PR creation authorized; merge is not authorized.

Push preparation: user corrected the branch name to implementation/client-marketplace and authorized a fresh 0.0.4 build and GitHub push. Branch renamed, dev/spec/issue revalidated, all three 0.0.4 packages rebuilt. Fresh full suite passed 201 tests in 93.473 seconds. Authored staged whitespace checks pass; 22 generated upstream files retain the same whitespace as committed Codex counterparts to preserve source hashes. Only the issue #20 sanitized task record is selected; unrelated task records are excluded.

## Implementation prerequisites (2026-10-21)

User confirmed review/merge and requested implementation. GitHub independently reports PR #21 merged at 2026-10-21T06:06:50Z, merge c4f763fcb60a0a4c1573473c135eded50d5bb368. The local spec has no diff from that merge. Issue #20 is unchanged since 2026-10-20T08:39:11Z. Branch created from origin/dev at that merge. Core verification reports ready and Git protection active; configured tests remain explicitly skipped, so run the actual unittest suite separately. Hindsight tools are unavailable; no memory reads or saves. No specialist skills selected: packaging and documentation only. Use canonical plugin_build and existing project hook recovery.

## GitHub guide follow-up (2026-10-21)

User requested GitHub installation guidance for all three clients. Documentation-only lighter path: INSTALLATION and README now show the exact private URLs, HTTPS/SSH access prerequisites, working implementation/client-marketplace refs before merge, the eventual dev transition, native install/update/version checks, Codex source replacement and numbered Cursor team/provider import steps. Official public documentation was rechecked through Context7. origin/dev still lacks the root catalogs; no implementation PR exists yet. README section anchors, current refs and whitespace were checked. No runtime/package changes or live installations; no full test rerun for prose. Existing Git protection was needs_activation after cache removal; normal setup recovery using the repository package restored active protection without changing the saved project settings. Next: push this guide update, then human implementation review and pending native rollout checks.
