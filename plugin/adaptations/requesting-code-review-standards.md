## Standards sub-agent

Dispatch a second general-purpose sub-agent in the same turn as the spec reviewer. Fill [standards-reviewer.md](standards-reviewer.md). Use the same `{BASE_SHA}` and `{HEAD_SHA}` as [code-reviewer.md](code-reviewer.md).

Before that dispatch, list the repository files that document how code is written. Include `CODING_STANDARDS.md` and `CONTRIBUTING.md` when they exist. Name linter and formatter configs so the standards reviewer skips rules those tools already enforce.

The spec reviewer stays on [code-reviewer.md](code-reviewer.md). Present the reports under separate `## Spec` and `## Standards` headings. Do not merge or rerank them. The spec report keeps its own assessment. Neither report approves a merge.
