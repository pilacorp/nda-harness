# NDA Harness

NDA Harness defines a shared development workflow for the internal team using Codex, Claude Code, Cursor, or another local coding agent. It combines spec-driven development (SDD), test-driven development (TDD), human review, and proposed CI merge gates.

The GitHub issue is the feature spec. The proposed harness helps the tech lead write, review, and revise its problem, users, outcome, scope, expected behavior, acceptance criteria, constraints, and open decisions. Supporting documents are linked when useful; no separate feature-spec document is required.

Developer work starts with that issue created by an authorized tech lead. The developer drafts a separate implementation-ready spec and submits it for review. A feature uses one issue-numbered branch for two sequential PRs: the developer-spec PR references the issue; human approval and spec merge unlock implementation; the implementation PR closes the issue after review and acceptance. Material issue edits require reconciliation with the approved developer spec.

Harness TDD uses focused unit tests in the code repository. QA owns integration and end-to-end verification; the harness does not require agents to build those test suites.

The proposed local hook set includes a Git `pre-commit` hook that runs configured unit tests and blocks failing commits, alongside CI merge checks.

Optional Hindsight memory connects directly through each client's native MCP OAuth.
After the user authenticates in plugin details, agents recall and retain useful
sanitized context in one bank per project, shared across clients and equivalent
Git clones. Dev/staging/prod are labels within the bank. Clients own credentials;
provider and deployment configuration stays in the Hindsight server repository.

## Read first

Supported coding-agent setups require Superpowers, RTK, and Context7. Context7 supplies relevant public library/framework documentation; the Skills hub adds selectively loaded specialist instructions.

- [Architecture](docs/architecture.md): workflow, responsibilities, knowledge boundaries, evidence, enforcement, and pilot validation.
- [Installation](INSTALLATION.md): developer prerequisites, project setup, Context7 and optional Hindsight connections, verification and recovery.
- [Developer integration](docs/developer-integration.md): repository preparation, local agent setup, readiness checks, daily use, handoffs, and upgrades.
- [Skills hub](skills/catalog.md): select UI/UX Pro Max, official Vietnamese document wording, or Diagram Design for a scoped sub-agent; load selected instructions only.

Code stays in the developer's local repository for agent inspection. The existing Markdown/pgvector RAG supplies feature and architecture knowledge. Self-hosted Hindsight, using OpenRouter for LLM processing, provides each developer's personal memory, such as preferences and individual working notes; it is not an organization-wide source of facts.

Memory storage stays internal; processing sends relevant memory content through OpenRouter to the selected model provider. OpenRouter credentials stay on the Hindsight server.

## Current phase

Phase 0 targets **Codex Desktop and Cursor IDE on Apple Silicon macOS**. Claude
Code Desktop is deferred. No release or migration exists. The approved
[plugin specification](specs/harness-plugins.md) was merged in
[PR #14](https://github.com/pilacorp/nda-harness/pull/14).

The shared package builder produces native plugins with full specialist and pinned
Superpowers skills, Context7 MCP, trusted startup bootstrap, five context operations,
and project Git test protection. On entry, the agent asks for a project's test command
or explicit Skip; `.nda-harness/` contains committed project configuration and task
records, with shared assets remaining in the plugin.

See [installation](INSTALLATION.md) to build and load a development plugin, and
[implementation evidence](docs/compatibility/harness-plugin-implementation.md) for
executed checks and remaining native-client validation. The production Hindsight
HTTPS hostname is still required for a deployed memory-enabled build. Core packages
work without it. Local OAuth testing uses an explicit loopback-only exception.

Earlier `bin/nda-harness`, installer and CLI trial reports remain development
history; they are excluded from generated plugin runtimes and are not the plugin
installation path. No public marketplace release or complete desktop support claim
is made by the automated tests.
