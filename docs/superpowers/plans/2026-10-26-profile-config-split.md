# Profile and config split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use nda-harness:subagent-driven-development (recommended) or nda-harness:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Store memory in personal `.nda-harness/profile.json` schema 3 and the test command in project `.nda-harness/config.json` schema 1, and stop requiring the profile to be committable.

**Architecture:** `scripts/nda_harness/project.py` reads and writes the two files, migrates a valid schema-2 profile during setup, and checks Git ignore only for `config.json`. The pre-commit gate and context preparation read `config.json` for the test command. Policy text and generated client packages follow the source trees.

**Tech Stack:** Python 3.9+, unittest, Git, the existing plugin package build.

**Spec:** `docs/superpowers/specs/2026-10-26-profile-config-split-design.md`

## Global Constraints

- `profile.json` schema 3 contains only `schema_version` and `memory`.
- `config.json` schema 1 contains only `schema_version` and `test_command`.
- Explicit Skip stores the command `true`.
- Setup accepts an ignored profile and rejects an ignored `config.json`, rolling back files it wrote.
- Setup adds `.nda-harness/tasks/` and `.nda-harness/profile.json` to `.gitignore` in a Git repository, creating the file when it is missing.
- Setup does not run `git rm`.
- Verify does not rewrite files. Schema-2 migration happens only in setup.
- A stored command disagreement between a schema-2 profile and an existing `config.json` stops setup and leaves both files unchanged.
- A missing profile does not fail the pre-commit test gate. A missing or invalid config does.
- A directory that is not a Git repository receives both files and no hook or `.gitignore` edit.
- The historical user-scope installer profile stays unchanged.
- Edit source trees, then regenerate `packages/nda-harness-*`. Do not hand-edit generated packages.

## Review Focus

- A schema-2 profile whose command differs from an existing `config.json` must not be overwritten, even when setup is given a new command.
- Ignoring `.nda-harness/` must reject setup because `config.json` is ignored, and the previous `.gitignore` must remain.
- Re-running setup must not duplicate ignore lines or change CRLF files except for the new lines.
- Deleting `profile.json` after setup must still allow a passing test command to commit.
- Verify on a schema-2 profile must leave the file bytes unchanged.

---

### Task 1: Split the project files

**Files:**
- Modify: `scripts/nda_harness/project.py`
- Modify: `scripts/nda_harness/plugin_runtime.py`
- Modify: `pack/scripts/unit_check.py`
- Modify: `pack/scripts/context_runtime.py`
- Test: `tests/test_plugins.py`

**Interfaces:**
- Produces: `profile_for(project) -> dict | None` for schema 3 only
- Produces: `config_for(project) -> dict | None` for schema 1
- Produces: `stored_profile(project) -> tuple[str | None, dict | None]` with kinds `current` and `legacy`

- [ ] Write failing plugin tests for schema 3, config schema 1, migration, conflict, ignore, rollback, and a missing profile.
- [ ] Run `python3 -m unittest tests.test_plugins -v` and confirm the new assertions fail.
- [ ] Implement the split in `project.py`, `plugin_runtime.unit_check`, `pack/scripts/unit_check.py`, and `context_runtime.py`.
- [ ] Re-run `python3 -m unittest tests.test_plugins -v` and confirm it passes.

### Task 2: Documentation and packages

**Files:**
- Modify: `pack/policy.md`, `pack/workflow.md`, `pack/context-preparation.md`, `pack/hindsight/README.md`, `pack/hooks/*.md`
- Modify: `plugin/skills/nda-setup/SKILL.md`, `plugin/rules/nda-harness.mdc`
- Modify: `docs/setup-guide.md`, `docs/plugin-operations.md`, `specs/harness-plugins.md`

- [ ] Update the prose so `config.json` is the committed project file and `profile.json` plus `tasks/` stay local.
- [ ] Regenerate packages with `python3 scripts/nda_harness/plugin_build.py --publish-committed`.
- [ ] Run `python3 -m unittest tests.test_plugins tests.test_marketplaces -v`.

**Ruling:** Do not create Git commits during this implementation. The request was to implement, and commits stay a separate request.

**Ruling:** The copied-pack CLI installer still stores its test command in schema-1 `profile.json`. `pack/scripts/unit_check.py` and context preparation use `config.json` when that file exists, and the profile command only when it does not. The plugin gate in `plugin_runtime.unit_check` reads `config.json` only.
