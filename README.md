# NDA Harness

NDA Harness defines a shared development workflow for the internal team using Codex, Claude Code, Cursor, or another local coding agent. It combines spec-driven development (SDD), test-driven development (TDD), human review, and proposed CI merge gates.

The GitHub issue is the feature spec. The proposed harness helps the tech lead write, review, and revise its problem, users, outcome, scope, expected behavior, acceptance criteria, constraints, and open decisions. Supporting documents are linked when useful; no separate feature-spec document is required.

Developer work starts with that issue created by an authorized tech lead. The developer drafts a separate implementation-ready spec and submits it for review. A feature uses one issue-numbered branch for two sequential PRs: the developer-spec PR references the issue; human approval and spec merge unlock implementation; the implementation PR closes the issue after review and acceptance. Material issue edits require reconciliation with the approved developer spec.

Harness TDD uses focused unit tests in the code repository. QA owns integration and end-to-end verification; the harness does not require agents to build those test suites.

The proposed local hook set includes a Git `pre-commit` hook that runs configured unit tests and blocks failing commits, alongside CI merge checks.

The proposed pack also includes a local knowledge-setup script to connect supported agents to internal RAG and each developer's personal Hindsight account, then verify access. Credentials stay on the developer's device.

## Read first

Supported coding-agent setups require Superpowers, RTK, and Context7. Context7 supplies relevant public library/framework documentation; the Skills hub adds selectively loaded specialist instructions.

- [Architecture](docs/architecture.md): workflow, responsibilities, knowledge boundaries, evidence, enforcement, and pilot validation.
- [Developer integration](docs/developer-integration.md): repository preparation, local agent setup, readiness checks, daily use, handoffs, and upgrades.
- [Skills hub](skills/catalog.md): select UI/UX Pro Max, official Vietnamese document wording, or Diagram Design for a scoped sub-agent; load selected instructions only.

Code stays in the developer's local repository for agent inspection. The existing Markdown/pgvector RAG supplies feature and architecture knowledge. Self-hosted Hindsight, using OpenRouter for LLM processing, provides each developer's personal memory, such as preferences and individual working notes; it is not an organization-wide source of facts.

Memory storage stays internal; processing sends relevant memory content through OpenRouter to the selected model provider. OpenRouter credentials stay on the Hindsight server.

## Current phase

This repository contains the architecture proposal, onboarding design, and a Skills hub with three specialist skills. It does **not** yet contain a released `.nda-harness/` policy package, an installer, executable GitHub Actions gates, or deployed service integrations. The integration guide distinguishes proposed adoption steps from working capabilities.

Next, prepare the shared policy package and gate implementation for one pilot repository, then validate it with the team's supported agent versions. No new coding agent or compulsory runtime wrapper is proposed.
