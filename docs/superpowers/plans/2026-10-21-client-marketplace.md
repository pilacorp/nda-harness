# Internal Client Marketplace Implementation Plan

> **For agentic workers:** Use nda-harness:executing-plans to implement this plan inline with TDD and final review.

**Goal:** Deliver issue #20's private native marketplaces for all three clients.

**Architecture:** Extend the existing canonical package publisher. Generate root catalogs alongside all three packages; validate repository routing before publishing. Reuse existing native update commands and project hook recovery.

**Tech Stack:** Python standard library, unittest, Git, native Codex/Claude commands.

**Spec:** specs/internal-client-marketplaces.md (PR #21 merged at c4f763f).

## Global Constraints

- Marketplace name `nda-harness-internal`; plugin name `nda-harness`.
- Initial release `0.0.4`, tracked distribution ref `dev`, repository private.
- Separate fixed-client packages; preserve standalone directories and hosted ZIP behavior.
- No new updater, daemon, credential handling, cross-client installer or dependencies.
- Native checks use disposable homes; GUI/provider/auth checks remain pending until observed.

## Review Focus

- Escaping, absolute, symlinked, missing and wrong-client catalog sources must fail validation.
- A build failure must preserve previously generated packages/catalogs.
- Deterministic rebuilds must include executable modes and valid release hashes.
- A removed cache path must block commits until existing setup safely rebinds it.
- Native upgrades must resolve a higher version without uninstall; failed fetch must preserve the install.

### Task 1: Generate and validate native repository marketplaces

**Files:** scripts/nda_harness/plugin_build.py; tests/test_marketplaces.py; tests/test_plugins.py; generated packages and root catalogs.

**Interfaces:** Extend publish_committed(source); add validate_marketplaces(source) to reject invalid catalogs/packages. Existing build/build_archive remain compatible.

- [x] Write tests for all three routes, containment/client mismatches, versions/hashes, repeated publication and failure preservation. Update the old two-package contract test.
- [x] Run tests and observe failures from missing catalogs/Claude package.
- [x] Generate native catalogs and all three packages at 0.0.4; validate before replacing stored outputs.
- [x] Regenerate committed assets and run packaging tests, then the full unittest suite.

### Task 2: Verify native discovery/update and hook recovery

**Files:** tests/test_marketplaces.py; docs/compatibility/internal-client-marketplaces.md.

**Interfaces:** Reuse configure/inspect_project and native marketplace commands; no new runtime hooks.

- [x] Exercise removed-cache recovery with real Git, profile preservation, existing hooks and one wrapper.
- [x] Use disposable native client homes and a local Git fixture for install, higher-version update and failed refresh where available.
- [x] Record actual versions/results and explicit unavailable checks; fix only failures proven by tests.

### Task 3: Document distribution and complete review

**Files:** README.md; INSTALLATION.md; specs/harness-plugins.md; compatibility evidence; issue task record.

- [x] Document private access, dev registration, native updates, one-time migration, hook recovery and reviewed rollback; reconcile superseded spec exclusions.
- [x] Run full suite, deterministic generation check and git diff --check.
- [x] Review the complete change, resolve material findings and checkpoint evidence for human review. Do not push, merge or change live client installations.
