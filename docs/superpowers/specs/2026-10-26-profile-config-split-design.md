# Personal profile and project config

## Intent

`.nda-harness/profile.json` currently stores two different kinds of data in one schema: the personal memory identity and the project test command. Setup also refuses to finish when Git ignores that file, so the personal memory record has to stay committable.

Split them. Memory stays personal in `profile.json` and may be ignored by Git. The test command becomes project configuration in `config.json` and must stay committable. The two files use different schemas.

## Goals

- `profile.json` holds only the personal memory record.
- `config.json` holds only the project test command.
- Each file has its own schema. A field that belongs in one file is invalid in the other.
- Setup and verification accept a Git-ignored `profile.json`.
- Setup and verification reject a Git-ignored `config.json` and roll back a setup that would leave the project in that state.
- The pre-commit hook runs the test command from `config.json`.
- Bank identity is still derived from the Git remote, or from an explicit project name when there is no remote. Another clone of the same remote can rebuild the same bank without a committed profile.
- Task records stay local under `.nda-harness/tasks/` and stay ignored.

## Non-goals

- New settings beyond this split.
- A personal test command, or a project-scoped memory record.
- Storing the personal profile under `~/.nda-harness`.
- Ignoring the whole `.nda-harness/` directory. That would hide `config.json`.
- Changing how a bank id is calculated.
- Changing the historical user-scope installer profile, the schema-1 pack profile that also names `spec_directory` and `task_directory`.
- Untracking a profile that is already in the Git index. Setup does not run `git rm`.

## Decisions

These came from the design conversation:

- Personal means memory. Project-scoped means the test command.
- The schemas are different.
- `profile.json` no longer has to stay committable.
- `config.json` does have to stay committable, taking the place of the old profile rule.
- Setup adds `.nda-harness/profile.json` to `.gitignore` beside `.nda-harness/tasks/`.

## Schemas

`profile.json` schema 3:

```json
{
  "schema_version": 3,
  "memory": {
    "identity_sha256": "64 lowercase hex characters",
    "bank_id": "nda-project- plus the first 32 hex characters",
    "system": "optional packaged system id",
    "remote": "optional selected remote name",
    "name": "optional project-name slug"
  }
}
```

The memory object keeps today's validation. `system`, `remote`, and `name` stay optional. No other keys are allowed. `test_command` is not part of this schema.

`config.json` schema 1:

```json
{
  "schema_version": 1,
  "test_command": "nonempty command, or the literal true for an explicit Skip"
}
```

No other keys are allowed. Memory fields are not part of this schema. A null byte in the command remains invalid. Explicit Skip still stores the command `true`.

## Git

For a Git repository, setup ensures `.gitignore` contains these exact lines when they are absent:

```gitignore
.nda-harness/tasks/
.nda-harness/profile.json
```

Setup creates `.gitignore` when the repository does not have one. It preserves existing rules, comments, and line endings, and it does not duplicate a line that is already present. It does not remove or rewrite unrelated rules.

The committable check uses `git check-ignore` on `.nda-harness/config.json`. If that path is ignored, setup raises the existing project-configuration conflict, rolls back the files it just wrote, and tells the operator to reconcile ignore rules so `config.json` can be committed while `profile.json` and `tasks/` stay ignored. An ignored `profile.json` is valid.

A directory that is not a Git repository still receives both files. It does not get a hook, a `.gitignore` edit, or the committable check.

## Behavior

Setup writes both files. Re-running setup reuses an existing valid config command when the user does not pass a new test command or explicit Skip. It reuses an existing valid memory identity the same way it does today.

A valid schema-2 profile is migration input, not a supported steady state. On setup, when `config.json` is absent, setup copies `test_command` from that profile into a new schema-1 config, then rewrites the profile as schema 3 with the memory object only. When `config.json` already exists and its command differs from the schema-2 profile, setup stops with a conflict and leaves both files unchanged. Verify stays read-only. An unmigrated schema-2 profile means configuration is incomplete until setup is run again.

The pre-commit gate reads `config.json` only. A missing or invalid config fails the commit. A missing profile does not fail the test gate. Memory operations still require a valid schema-3 profile and still use `memory.bank_id` and `memory.system`.

Context preparation is ready only when both files are valid. A repository also needs `config.json` to be committable and the clone-local hook to be active. A non-repository needs both files and no hook.

## Documentation and packages

Update the policy, workflow, context-preparation text, setup and session skills, the Cursor rule, `docs/setup-guide.md`, `docs/plugin-operations.md`, and `specs/harness-plugins.md` so they commit `config.json`, keep `profile.json` and `tasks/` local, and describe the two schemas.

Edit the source trees the package build copies: `scripts/nda_harness/`, `pack/`, and `plugin/skills/`. Then regenerate `packages/nda-harness-codex`, `packages/nda-harness-cursor`, and `packages/nda-harness-claude`. Do not hand-edit generated package copies.

## Tests

Cover the schema split, migration of a schema-2 profile, a conflicting existing config, the hook reading `config.json`, an ignored profile being accepted, an ignored config being rejected and rolled back, `.gitignore` creation and preservation, and a non-repository receiving both files without a hook.

## Builder calls

- Profile schema version is 3. Config schema version is 1.
- Setup creates a missing `.gitignore` in a repository. The historical user-scope installer is unchanged.
- Setup does not untrack an already committed profile. Removing it from the index remains a human Git action.
- Verify does not rewrite files. Migration happens only in setup.
