# Developer spec: store the OpenRouter key in a user-only file

Feature issue: https://github.com/pilacorp/nda-harness/issues/36
Issue updated at: 2026-10-29T06:47:40Z
Issue body SHA-256: 59cefbbb70a80423df61809542eb5d16c80f749f6e9819534c95eb42ba751e25
Consulted source revisions: repository `f912fc2b2435ec90089eaa6680ea94f0e55f9775`; `specs/jev-skill-selection.md` section "Credentials, cache, and task records"; `scripts/nda_harness/credentials.py`; `scripts/nda_harness/openrouter.py`; `scripts/nda_harness/plugin_runtime.py`; `scripts/nda_harness/files.py`; `docs/skill-selection.md`
Spec branch: `spec/openrouter-credential`

## Summary

Skill selection keeps one personal OpenRouter key for Codex, Cursor, and Claude.
Version 1 stores that key in the macOS login Keychain. A Seatbelt sandbox cannot
see that item, and Keychain grants access per app, so the same item is a poor
shared store for these three clients.

This change stores the key in a user-only file:

`~/.nda-harness/skill-selection/openrouter-key`

The directory mode is `0700`. The file mode is `0600`. The helper refuses a
symlink. It writes the file with the existing atomic-write helper. The sandboxed
selector returns `sandbox_rerun` before it opens the file. The key path stays
out of Git: the state directory carries a local `.gitignore` for
`openrouter-key`, and project setup also ignores
`.nda-harness/skill-selection/`.

People who already saved the key in Keychain move it with one terminal command,
`selection-migrate`. That command is the migration script. It reads the existing
Keychain item through the current Security-framework adapter, writes the file,
checks the file in memory, and then deletes the Keychain item. It never prints
the key and never passes the key as a command argument.

Codex can still ask the user before the task text goes to OpenRouter. This spec
does not change that review.

This document supersedes the Keychain-only storage rule in
`specs/jev-skill-selection.md`. Jev selection, thresholds, cache identity, and
the OpenRouter request stay as they are.

## Setup and daily use

No new OpenRouter key is required. The Hindsight server key stays on the
Hindsight server. This file is a different key, and it is not a project file.

After the implementation is released, each person updates the NDA Harness plugin.
On a Mac that already has the 0.0.9 Keychain item, they run the migration script
once in a local terminal, outside the sandbox:

```sh
rtk proxy <plugin-root>/bin/nda-plugin selection-migrate --client <client>
```

`<client>` is `codex`, `cursor`, or `claude`. The command has no key argument.
The terminal asks before it moves the key. On success it prints
`OpenRouter key moved to the local file. The Keychain item was removed.`
It does not print the key or a JSON report.

A person with no saved key runs the existing setup command in that same kind of
terminal. Setup prompts in hidden input and writes the file:

```sh
rtk proxy <plugin-root>/bin/nda-plugin selection-setup --client <client>
```

Running setup again asks before replacing the file. Answering no keeps the file
and finishes setup. `selection-setup --remove` removes the saved key after a
terminal confirmation. Removal deletes the file when it exists and deletes a
leftover Keychain item when it exists.

`selection-verify` checks the package and whether the file is present. It does
not call OpenRouter. `--live` remains the only paid check. `select-skills`,
`record-selection`, `load-selected-skills`, and `selection-verify` still run
outside the sandbox. A sandboxed result is `sandbox_rerun`. The agent reruns the
same command outside the sandbox. It does not create a new key, and it does not
treat `sandbox_rerun` as a missing key.

The file is shared by every client that runs as the same Mac user. A second
client answers no at the replace prompt and keeps that file.

## Outcome and boundaries

Task classification: behavior change.

Issue #36 asks for a shared store that Codex, Cursor, and Claude can read
outside the sandbox, plus a developer-spec contract for moving the current
Keychain item. The observable result is: the same key bytes work from the file
for all three clients; the sandboxed helper does not open the file; a missing
or replaced key keeps today's diagnostics and generation rotation; the secret
stays out of chat, argv, logs, and the repository.

In scope: the file store, `selection-migrate`, setup and removal against that
file, sandbox refusal before any read, generation behavior for a move versus a
replacement, and the docs and skill text that still say the key lives in
Keychain.

Out of scope: changing the Jev model, catalog, thresholds, or request body;
skipping Codex's approval to send task text to OpenRouter; an environment
variable; a project `.env`; a second key per client; Hindsight credentials;
deleting an OpenRouter key at the provider. Provider revocation stays an
administrator action. Local removal does not revoke the key at OpenRouter.

The helper still cannot stop another process running as the same user from
reading a file that user can read. The file mode and the home-directory location
are the local boundary. The sandbox refusal is what keeps the sandboxed agent
from opening the file.

## Implementation

### File store

Add a file-backed store next to the existing Keychain adapter in
`scripts/nda_harness/credentials.py`. The state directory remains
`~/.nda-harness/skill-selection/`, the directory `plugin_runtime.py` already
passes as `Path.home() / '.nda-harness'`. This is the user home directory, not
the project `.nda-harness/` folder.

| Path | Mode | Role |
| --- | --- | --- |
| `~/.nda-harness/skill-selection/` | `0700` | Existing state directory. Reject a symlink. |
| `~/.nda-harness/skill-selection/.gitignore` | `0600` | Ignores `openrouter-key` when that directory is inside a Git work tree. |
| `~/.nda-harness/skill-selection/generation` | `0600` | Unchanged generation id. |
| `~/.nda-harness/skill-selection/openrouter-key` | `0600` | The key file. Reject a symlink. |

The file body is the stripped secret encoded as UTF-8, plus one trailing
newline. A present file is a regular file, owned by the current user, mode
exactly `0600`, with a parent directory mode exactly `0700`. After stripping
the final newline, the secret is non-empty and contains no other newline.
Any other shape is unusable: diagnostic `credential_unavailable`, and the next
step tells the person to run `selection-setup` in a terminal. An absent file is
`credential_missing`.

Writes go through `files.atomic` so the temporary file is mode `0600` and the
replace is atomic. Setup and migrate set the directory to `0700` before they
write. `select-skills`, `record-selection`, `load-selected-skills`, and
`selection-verify` do not chmod. When the mode or owner is wrong, they return
`credential_unavailable` and point at setup.

### Git ignore

The key must never enter a Git index.

1. The store is only under the user home directory
   `Path.home() / '.nda-harness' / 'skill-selection' / 'openrouter-key'`.
   Never write `openrouter-key`, `generation`, or selection cache files under a
   project's `.nda-harness/` folder.
2. Whenever setup or migrate creates or updates the home state directory, write
   `~/.nda-harness/skill-selection/.gitignore` whose entire body is the single
   pattern `/openrouter-key` followed by a newline:

   ```
   /openrouter-key
   ```

   Use `files.atomic` at mode `0600`. Reject a symlink at that path. Do not put
   the secret in the ignore file. The leading slash limits the rule to the key
   file in that directory. Leave `.gitignore` in place on key removal so a later
   setup still finds the rule.
3. Extend `ensure_project_gitignore` in `scripts/nda_harness/project.py` so every
   project `.gitignore` also contains `.nda-harness/skill-selection/`. Keep the
   existing `.nda-harness/tasks/` and `.nda-harness/profile.json` patterns.
   Commit that same pattern in this repository's root `.gitignore`. The project
   pattern is defense when an agent or person places a key under the checkout by
   mistake; it does not replace the home-directory store.
4. Setup, migrate, verify, and selection commands must not `git add`,
   `git commit`, or force-add the key file. Documentation repeats that the key
   stays out of chat, argv, project files, and Git.

`select-skills`, `record-selection`, `load-selected-skills`, and
`selection-verify` read this file only. They do not call the Keychain adapter.
The sandbox check stays first. On `sandbox_rerun` the process does not open
`openrouter-key` and does not call Keychain.

The cache key still includes the generation id and still excludes the key
bytes. A successful move of the same bytes does not rotate generation, so an
existing cache stays valid. These actions rotate generation once: saving a new
secret, replacing the file with different bytes, and removing the key.

### Migration script

The migration script is the packaged command `selection-migrate`. Implement it
as `migrate_openrouter_key` in `scripts/nda_harness/credentials.py`, and dispatch
it from `plugin_runtime.py`. Do not add a shell script. Do not call the
`security` command-line tool. Do not pass the secret with `-w` or any other
argument. Keychain read and delete use the existing `MacKeychain` adapter:
service `vn.pila.nda-harness.openrouter`, account `skill-selection`,
synchronization off.

The command requires a terminal, the same way `selection-setup` does. Without a
terminal it returns `terminal_required` and does not read either store. Inside
the sandbox it returns `sandbox_rerun` and does not read either store. A symlink
at `~/.nda-harness`, `skill-selection`, or `openrouter-key` returns
`credential_unavailable` and does not follow the link.

The script compares secrets only in memory. It writes no secret to stdout,
stderr, the prompt, argv, or a log. Exit `0` means ready, exit `2` means
blocked, and exit `130` means the person cancelled. A terminal always receives
one sentence. It does not receive the JSON report.

| File | Keychain | Result |
| --- | --- | --- |
| Missing | Missing | `credential_missing`. Tell the person to run `selection-setup`. Write nothing. |
| Missing | Unavailable | `credential_unavailable`. Write nothing. |
| Missing | Present | Ask `Move the OpenRouter key from Keychain into the local file and delete the Keychain item? [y/N]`. No leaves both stores unchanged and returns cancelled. Yes reads the item, writes the file, reads the file back, and compares in memory. Delete the Keychain item only after that compare matches. Do not rotate generation. If the write or the compare fails, leave the Keychain item in place and remove a partial file. If the delete fails after a matching file, return `credential_unavailable` and keep the file. A later run uses the both-present row. |
| Present | Missing | Ready, diagnostic `credential_already_file`. Sentence: `The OpenRouter key is already in the local file.` Do not rotate generation. |
| Present | Unavailable | Do not overwrite the file. `credential_unavailable`. The file remains the store. The sentence says the Keychain item could not be read, so it was not removed. |
| Present, same bytes | Present | Ask `Delete the Keychain copy? The local file already has this key. [y/N]`. Yes deletes the Keychain item and does not rotate generation. No cancels, and both copies stay. |
| Present, different bytes | Present | Ask `The local file and the Keychain item differ. Type file or keychain:`. Any other answer cancels, and both copies stay. `file` deletes the Keychain item, leaves the file, and does not rotate generation. `keychain` overwrites the file, rotates generation, and deletes the Keychain item only after the file read-back matches. A failed overwrite leaves the previous file and the Keychain item. |

`selection-setup` uses the same function when it can avoid a second key. If the
file is missing and Keychain status is `present`, setup first asks
`An OpenRouter key is still in Keychain. Move it to the local file? [y/N]`.
Yes runs the missing-file row above with no second confirmation. No continues
to the hidden prompt, writes the new secret to the file, rotates generation,
and then asks `Delete the Keychain item? [y/N]`. Setup does not read the
Keychain secret on that No path. Status checks that do not return the password
are allowed in setup, migrate, and `selection-setup --remove`. They are not
allowed in `select-skills`, `record-selection`, or `load-selected-skills`.

`selection-setup --remove` asks once: `Remove the saved OpenRouter key? [y/N]`.
Yes deletes the file when it exists and deletes the Keychain item when it
exists, then rotates generation once. A failure leaves the remaining copy and
returns `credential_unavailable` without claiming the key is gone.

### Call sites that still name Keychain

Change the source strings in `scripts/nda_harness/skill_selection.py` and
`scripts/nda_harness/openrouter.py`. The sandbox sentence becomes: the shared
OpenRouter key file is what the unsandboxed command reads. Regenerate the
client packages from those sources. Do not hand-edit `packages/`.

Update the skill and rule text that tells the agent where the key lives:
`plugin/skills/skill-selection/SKILL.md`, `plugin/skills/session-bootstrap/SKILL.md`,
and the Cursor rule source. Say the key stays in the user-only file under
`~/.nda-harness/skill-selection/`. Keep the ban on chat, command arguments, and
project files.

Update the user docs that describe the current store: `docs/skill-selection.md`,
`docs/setup-guide.md`, `docs/developer-integration.md`, `docs/plugin-operations.md`,
`docs/architecture.md`, and the skill-selection sentence in `README.md`. State
that `~/.nda-harness/skill-selection/openrouter-key` is ignored by Git and must
not be staged or committed. In `specs/jev-skill-selection.md`, replace the
Keychain storage paragraphs and the sandbox row that says the Keychain key is
shared. Point them at this spec. Leave the historical Keychain failure note in
`docs/compatibility/minimal-cli.md` as history. It is not this key.

Update `scripts/nda_harness/project.py` `ensure_project_gitignore` and this
repository's root `.gitignore` as required under Git ignore above.

`credential_unavailable` for a file problem says the key file could not be read.
The Keychain-specific sentence remains only on `selection-migrate` and on
removal when the Keychain delete fails.

## Acceptance mapping

| ID | Issue criterion | Expected behavior |
| --- | --- | --- |
| AC-01 | Shared file store | Outside the sandbox, Codex, Cursor, and Claude read one `0600` file under `~/.nda-harness/skill-selection/`. A second client's declined replacement keeps that file. |
| AC-02 | Sandbox refusal | A sandboxed selector returns `sandbox_rerun`, does not open the key file, does not call Keychain, and does not call OpenRouter. |
| AC-03 | Migration script | `selection-migrate` copies the current Keychain item into the file and deletes the item only after the file matches. The key is absent from output and argv. The same key does not rotate generation. |
| AC-04 | Setup, replacement, removal | Hidden setup writes the file. Cancel keeps the previous secret. Removal deletes the file and a leftover Keychain item. Generation rotates only when the saved secret changes or the key is removed. |
| AC-05 | Existing diagnostics | A missing file is `credential_missing`. An unreadable, wrong-mode, or symlink path is `credential_unavailable`. Selection still does not load every specialist. |
| AC-06 | Codex egress stays | The helper still sends the task only from the existing OpenRouter call. This change adds no flag that skips a client approval prompt. |
| AC-07 | Key stays out of Git | Home state writes `/openrouter-key` into `~/.nda-harness/skill-selection/.gitignore`. Project setup keeps `.nda-harness/skill-selection/` in `.gitignore`. The key is never written under a project `.nda-harness/` tree. |

## Concrete test cases

These tests are planned. None have been run for this spec. Use a temporary home
directory and a fake Keychain double. Do not read or write the developer
machine's real Keychain item, and do not put a real key in the fixture.

| ID | Setup/input | Action | Expected result | Layer / acceptance IDs |
| --- | --- | --- | --- | --- |
| TC-01 | Fake Keychain holds `sk-test-a`. The file is absent. Generation id is `g1`. | Run migrate and answer yes. | File mode is `0600`, directory mode is `0700`, body is `sk-test-a` plus one newline, Keychain status is missing, generation is still `g1`, `skill-selection/.gitignore` contains `/openrouter-key`, and stdout/stderr/argv contain no `sk-test-a`. | Unit; AC-01, AC-03, AC-07 |
| TC-02 | Same as TC-01. | Answer no. | No file is created, the Keychain item remains, generation stays `g1`, exit `130`. | Unit; AC-03 |
| TC-03 | File already holds `sk-test-a`. Keychain is missing. | Run migrate. | Diagnostic `credential_already_file`. Generation is unchanged. | Unit; AC-03 |
| TC-04 | File and Keychain both hold `sk-test-a`. | Answer yes to delete the Keychain copy. | File bytes stay, Keychain is missing, generation is unchanged. | Unit; AC-03 |
| TC-05 | File holds `sk-test-a`. Keychain holds `sk-test-b`. | Answer `file`, then in a second case answer `keychain`. | `file` deletes Keychain and keeps `sk-test-a` with the same generation. `keychain` writes `sk-test-b`, rotates generation, and deletes Keychain only after read-back matches. Any other answer changes nothing. | Unit; AC-03, AC-04 |
| TC-06 | Keychain holds `sk-test-a`. The file write raises. | Run migrate and answer yes. | Keychain item remains. No usable file remains. Diagnostic `credential_unavailable`. | Unit; AC-03 |
| TC-07 | `openrouter-key` or the state directory is a symlink. | Run migrate, setup, and select-skills. | `credential_unavailable`. The symlink target is not read or written. | Unit; AC-01, AC-05 |
| TC-08 | `CODEX_SANDBOX=seatbelt`, for each of codex, cursor, and claude. File and fake Keychain are present. | Run migrate, select-skills, record-selection, load-selected-skills, and selection-verify. | Exit `2`, diagnostic `sandbox_rerun`. The fake Keychain receives no call. The key file's read timestamp or test spy shows it was not opened. OpenRouter is not called. | Unit; AC-02 |
| TC-09 | File holds the key at mode `0600`. Fake Keychain is empty. | Run select-skills outside the sandbox. | The request uses the file secret. Keychain `read` and `status` are not called. | Unit; AC-01, AC-05 |
| TC-10 | No file. Fake Keychain status is `present`. | Run selection-setup, answer yes to the move prompt. Then repeat on a fresh home, answer no, and enter `sk-test-b`. | The yes path matches TC-01. The no path writes `sk-test-b`, rotates generation, and asks whether to delete the Keychain item. | Unit; AC-03, AC-04 |
| TC-11 | File exists, and a different Keychain item exists. | Run `selection-setup --remove` and answer yes. | Both stores are gone. Generation rotates once. A no answer leaves both. | Unit; AC-04 |
| TC-12 | File mode is `0644`, or the file is empty, or the body has an internal newline. | Run selection-verify and select-skills. | `credential_unavailable`. The command does not chmod the file. | Unit; AC-05 |
| TC-13 | Built Codex, Cursor, and Claude packages. | Read the skill, bootstrap, and Cursor rule text. | They name the user-only file, `selection-migrate`, and `sandbox_rerun`. They do not tell the agent to read the login Keychain for this key. | Unit; AC-01, AC-02 |
| TC-14 | Temporary home with a key written by setup or migrate. Initialize a Git repository whose work tree is that home (or the `skill-selection` directory). | Run `git check-ignore -q skill-selection/openrouter-key` from the home root, or `git check-ignore -q openrouter-key` from `skill-selection`. | Exit `0`. The ignore file body is exactly `/openrouter-key` plus a newline. Removing the key leaves `.gitignore` in place. | Unit; AC-07 |
| TC-15 | Temporary project without `.nda-harness/skill-selection/` in `.gitignore`. | Run project configure / `ensure_project_gitignore`. | Project `.gitignore` contains `.nda-harness/skill-selection/` as well as the existing profile and tasks patterns. `git check-ignore -q .nda-harness/skill-selection/openrouter-key` exits `0` after a dummy file is created under that path. | Unit; AC-07 |

Failure cases above must leave the previous good copy in place whenever the
new copy is not verified. A test that inspects process output fails if the
fixture secret appears there.

## Hook changes

No new hook event. Session start still injects the skill-selection guidance.
That guidance text changes from the Keychain item to the user-only file and
names `selection-migrate` for a machine that still has the 0.0.9 item. The
sandboxed command still returns `sandbox_rerun` instead of calling OpenRouter.
Hooks do not run migrate and do not open the key file.

## Documentation and rollout/recovery

Documentation changes are the files listed under "Call sites that still name
Keychain". The setup page should show `selection-migrate` before
`selection-setup` for an existing install, and setup alone for a new install.

Roll out by releasing the plugin, then running `selection-migrate` once per Mac
user that already has the Keychain item. Confirm with `selection-verify` outside
the sandbox. The sentence for a present file stays `OpenRouter key is present.`
A missing file tells the person to migrate or to run setup. Do not create a new
OpenRouter key for this rollout.

Rollback to the 0.0.9 package restores Keychain reads. Take a rollback only
before migrate deletes the Keychain item, or restore the item by running 0.0.9
`selection-setup` and entering the key again. Migrate's delete is the point of
no return for the Keychain copy. The file can be removed with
`selection-setup --remove`. Rollback does not revoke the key at OpenRouter and
does not change Hindsight.

QA on each client, in a fresh session: migrate on a Mac with the old item;
decline replacement on a second client; run one offline verify; run one sandboxed
command and confirm `sandbox_rerun`; rerun that command outside the sandbox and
confirm it reads the file. A live `--live` check stays optional and uses the
existing test key. Codex's question about sending the task text remains a
pass if it appears. This spec does not require that question to disappear.

## Decisions and risks

The file name `openrouter-key` and the `selection-migrate` command are the
choices this spec adds beyond the issue text. The issue left both to the
developer spec.

A same-user process outside the sandbox can still read the file. That limit is
accepted because the three clients are three apps for one Mac user, which is
the sharing requirement Keychain could not meet.

`selection-setup` offers migration before a new key is typed. The standalone
script remains the path an agent tells the user to run. Setup does not migrate
silently.

If Keychain delete fails after a verified write, the file is already the store
and a retry takes the both-present path. The script must not rotate generation
on that retry when the bytes match.

The sandbox probe may create and remove a probe file in the state directory.
It must not open `openrouter-key`.

The home-directory `.gitignore` does not protect a key that an agent writes
under a project tree. That is why the project ignore pattern and the ban on
project-relative key paths are both required.

## Review and implementation handoff

Spec PR: not opened
Review reference: unset until reviewed
Merge reference/revision: unset until merged
Local spec matches merged reviewed version: not applicable yet
Next action: review this spec. The spec-only PR body uses `Refs #36` and does
not use a closing keyword. Implement only after the spec review is merged and
the local file matches that revision.

The issue owns intent. This document does not grant approval. No key was read,
moved, or printed while writing this spec.
