# Local Graphify integration

Draft for review. Feature issue, issue revision, and issue body fingerprint are pending.
Consulted source revisions are NDA Harness `63d9e46` and the upstream [Graphify v8 merge reference](https://github.com/Graphify-Labs/graphify/blob/v8/graphify/skills/agents/references/github-and-merge.md).

## Summary

Add optional, local code navigation for coding agents working across explicitly selected Git repositories. Use Graphify to build one code-only index per checkout and merge those indexes for workspace queries. Results identify the repository and source location so the agent can verify relationships before using them in a spec or implementation.

## Setup and daily use

During explicit Harness setup, users can opt in to Graphify. Setup checks for a supported local Graphify CLI and reuses it when available. If the CLI is missing or unsupported, setup installs the pinned `graphifyy` package into an isolated, user-local environment managed by Harness and verifies that its executable runs at the expected version. Setup preserves existing user installations and reuses a healthy managed installation on subsequent runs. If installation or verification fails, setup reports the cause and how to retry, and reports Graphify as unavailable while core Harness setup continues.

The integration runs on demand from Codex, Cursor, or Claude Code through the shared Harness CLI. Proposed operations are build or refresh, status, and query. Users can query one checkout or an explicitly selected set of checkouts. Setup installs the CLI only. Indexing begins when explicitly requested.

## Outcome and boundaries

This is a behavior change. The first release covers symbol lookup and dependency paths across indexed code. It uses local code-only extraction with external model backends disabled. A workspace merge may resolve supported cross-repo calls. Runtime contracts such as HTTP endpoints and event names need source verification when the graph cannot resolve a link. The agent can fall back to native search when a graph is missing, stale, or incomplete.

## Implementation

- **Scope.** Validate and deduplicate explicit local Git worktree roots. Treat sibling repositories and linked worktrees as independent checkouts. Exclude nested repository contents from the parent index and index a nested repository separately when selected. Reject outputs that resolve outside the intended cache directory.
- **Per-repo storage.** Publish the indexed JSON at `<repo-root>/.nda-harness/graphify/graph.json`. Keep metadata, intermediate output, and any Graphify-generated caches under the same ignored directory. Exclude that directory from extraction. Add `/.nda-harness/graphify/` to the participating repository's `.gitignore` through the documented opt-in setup, and verify the rule before creating artifacts. Commit the ignore rule and shared project configuration. Keep graph JSON, metadata, and caches out of Git. They are reproducible, checkout-specific, and can contain private source structure or local paths.
- **Freshness.** Record the Git revision, Graphify version, and a fingerprint of the indexed inputs, including local file changes and resolver configuration such as `tsconfig.json`. Revision alone cannot detect dirty worktrees. Mark the index stale if the inputs or index version differ. Check inputs before and after a build and discard the candidate if they changed while building.
- **Build and recovery.** Run Graphify against one root at a time using a staging directory. Serialize writers per checkout. Publish a validated graph and matching metadata as one generation so queries cannot read mismatched files. Keep the prior generation on a failed or interrupted refresh and report its freshness. If the graph is missing or invalid, rebuild from source even if a manifest survives.
- **Workspace query.** Merge only fresh per-repo indexes. Preserve repository identity for each result, including when repo basenames or symbol names collide. Keep merged output temporary under the invoking checkout's ignored graph directory. For a stale or missing member, report which repo needs refresh and use native search for that scope. A query does not trigger an implicit rebuild.

## Acceptance mapping and planned tests

Criteria below are proposed and should be reconciled with the published issue.

| ID | Scenario | Expected result |
| --- | --- | --- |
| AC-01 | Enable Graphify and build a code-only index in a Git worktree | The repository's root `.gitignore` contains `/.nda-harness/graphify/` before indexing. `git check-ignore` confirms that `.nda-harness/graphify/graph.json` is ignored. The JSON is readable and extraction makes no external model calls. |
| AC-02 | Query two repositories with a known dependency and duplicate symbol names | Results identify the correct repo and source for each symbol. A supported cross-repo edge can be traced. An unresolved boundary remains unresolved. |
| AC-03 | Edit a resolver alias or switch branches in one repository | Status flags that checkout as stale. Refresh updates its graph and reuses the other fresh index for the next merge. |
| AC-04 | Delete the graph while retaining metadata, or interrupt a refresh | A missing graph requires a complete rebuild. An interrupted refresh preserves the previously published generation. |
| AC-05 | Run setup with Graphify enabled and no supported local CLI | Setup installs and verifies the pinned CLI without replacing an existing user installation. Re-running setup reuses a healthy installation. |
| AC-06 | Decline Graphify or encounter an installation or verification failure | Declining skips installation. A failure reports how to retry and leaves Graphify unavailable. Core setup and native search remain usable. |

Cover storage, ignore rules, stale detection, and publication with unit tests. Use an integration fixture with two local Git repositories to cover cross-repo identity, a known call, alias changes, branch changes, and recovery. Run manual smoke tests on each supported client and platform with the pinned CLI. These tests are planned.

## Hook changes

The feature runs only on demand. Session startup and the Git test gate have no dependency on Graphify.

## Documentation and rollout

Document setup opt-in, the supported version, installation retry, the ignore rule, explicit refresh, and cleanup of generated output. Compare the same agent with native tools and with Graphify on representative multi-repo tasks, measuring source-verified accuracy, elapsed time, and total tokens before enabling wider use.

## Decisions and review

Pin the supported Graphify version after checking code-only extraction, output placement, and recovery on the supported platforms. Spec PR, review, and merge evidence are pending. Next action is to link the published feature issue and reconcile its acceptance criteria before spec review.
