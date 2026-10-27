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
- [Setup guide](docs/setup-guide.md): initial project setup, Hindsight authentication, and the skill selection flow.
- [Installation](INSTALLATION.md): add the GitHub marketplace and install NDA Harness in Codex, Cursor or Claude.
- [Plugin operations](docs/plugin-operations.md): migration, project setup, optional memory, recovery and contributor builds.
- [Developer integration](docs/developer-integration.md): repository preparation, local agent setup, readiness checks, daily use, handoffs, and upgrades.
- [Skills hub](skills/catalog.md): UI/UX Pro Max, official Vietnamese document wording, and Diagram Design. The local Jev helper selects them; load only the returned bodies.
- [Skill selection](docs/skill-selection.md): personal OpenRouter key, Jev `typesafe/jev-1.14`, and the select/load commands.

Code stays in the developer's local repository for agent inspection. The existing Markdown/pgvector RAG supplies feature and architecture knowledge. Self-hosted Hindsight, using OpenRouter for LLM processing, provides each developer's personal memory, such as preferences and individual working notes; it is not an organization-wide source of facts.

Memory storage stays internal; processing sends relevant memory content through OpenRouter to the selected model provider. That OpenRouter credential stays on the Hindsight server. A developer's separate OpenRouter key, used only for Jev skill selection, stays in the macOS Keychain.

## Current phase

Phase 0 targets **Codex Desktop, Cursor IDE, and Claude Code Desktop on Apple
Silicon macOS**. This private repository supplies native marketplaces named
`nda-harness-internal`, each exposing the matching NDA Harness package at
version **0.0.7**, tracked from `main`. The
[marketplace spec](specs/internal-client-marketplaces.md), merged in
[PR #21](https://github.com/pilacorp/nda-harness/pull/21), extends the original
[plugin specification](specs/harness-plugins.md).

The shared package builder produces native plugins with full specialist and pinned
Superpowers skills, Context7 MCP, trusted startup bootstrap, five context operations,
and project Git test protection. On entry, the agent asks for a project's test command
or explicit Skip; `.nda-harness/config.json` is committed project configuration
and `.nda-harness/profile.json` is the local memory record.
Task records stay local in Git-ignored `.nda-harness/tasks/`, with shared assets
remaining in the plugin.

Install from GitHub using the [Codex](INSTALLATION.md#codex),
[Cursor](INSTALLATION.md#cursor-ide), or
[Claude Code](INSTALLATION.md#claude-code-and-the-desktop-code-tab) guide.
The installation guide targets `main`. The guide also covers private
access, updates, one-time migration from uploads/local plugins, and release generation.
All three `packages/nda-harness-<client>` directories and root catalogs are
generated from canonical sources. [Marketplace evidence](docs/compatibility/internal-client-marketplaces.md)
separates tested native CLI behavior from pending Desktop, Cursor provider and
authentication checks. Hindsight is optional; its HTTPS endpoint is packaged.
Local OAuth testing uses an explicit loopback-only exception.

Earlier `bin/nda-harness`, installer and CLI trial reports remain development
history; they are excluded from generated plugin runtimes and are not the plugin
installation path. No public marketplace release or complete desktop support claim
is made by the automated tests.
