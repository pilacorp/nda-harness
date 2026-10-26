# Internal marketplace compatibility evidence

Checked 2026-10-21 for issue #20, based on `dev` merge
`c4f763fcb60a0a4c1573473c135eded50d5bb368` (spec PR #21).
The implementation branch is `implementation/client-marketplace`. The local marketplace
spec matches the merged content; the live issue was unchanged from its recorded
2026-10-20T08:39:11Z revision. Human implementation review remains required.

## Automated package and recovery checks

Run from the repository root:

```sh
rtk proxy python3 -m unittest discover -s tests
```

The baseline passed 194 tests before implementation. New marketplace tests were
observed failing against the two-client publisher before implementation. They
exercise all three catalog routes, native schemas, missing/escaping/absolute and
wrong-client paths, symlink containment, malformed package metadata, client binding,
0.0.4 version consistency, complete release hashes and executable permissions.
Publication twice must produce identical files/modes. Injected generation and
output-replacement failures must preserve the preceding distribution.

Final verification: **201 tests passed in 92.357 seconds**. Regenerating the real
repository distribution preserved all **2187 files' bytes and permission modes**.
`git diff --check` passed. An independent read-only review found an initial-install
documentation dependency on RTK; installation/update snippets now invoke the
native client directly, allowing its first session to bootstrap RTK afterward.
No remaining code findings were reported. Real-client limitations below remain open.

Push verification after renaming to `implementation/client-marketplace`: all
three packages were rebuilt at 0.0.4 and **201 tests passed in 93.473 seconds**.
Staged authored changes pass whitespace checks. The newly stored Claude package
preserves whitespace in 22 upstream skill/vendor files byte for byte with their
already committed Codex counterparts; those generated assets were not reformatted.

### Current 0.0.5 PR verification

The initial 0.0.4 marketplace release is preserved in commit `55d33f5`. The
successor 0.0.5 release includes Python 3.9 compatibility. At branch revision
`61cafbf`, the complete suite passed **203 tests on Python 3.12.12** (99.804s)
and **203 tests on Python 3.9.6** (99.472s). These runs include fresh canonical
package comparisons, catalog routing, deterministic generation, rollback and
removed-cache Git hook recovery. All 2181 packaged asset hashes match their
release manifests, and the installation guide's local links/anchors pass.

An independent read-only review found no code blockers. Its stale release-version
statement in the native experiment record below was corrected to distinguish
the historical experiment from the current compatibility release. The manual
client rollout checks remain pending as listed below.

`PluginTests.test_repository_packages_match_all_three_canonical_builds` compares
every stored package byte against a fresh canonical build. Existing ZIP tests
exercise single-plugin hosted Codex uploads and the Claude hosted-launcher
relocation; the marketplace Claude directory retains `bin/nda-plugin`.

`PluginTests.test_upgrade_recovers_removed_cache_without_duplicate_hooks_or_profile_changes`
uses real Git and disposable homes. Removing the old cache makes protection
incomplete and blocks commits. Repeated existing setup against a newer package
preserves the profile bytes, bank and test command, rebinds one wrapper, executes
the prior hook exactly once and preserves both prior-hook and test failures.
No runtime hook manager or event was added.

## Native Git discovery and update

Executed with **Codex CLI 0.133.0** and **Claude Code 2.1.263**, Python 3.12.12,
Apple Silicon macOS. All client configuration lived in new disposable homes:
`HOME`, `CODEX_HOME` and `CLAUDE_CONFIG_DIR` were isolated. The subprocesses used
a minimal environment without inherited credentials. No chat session, native
OAuth login, hook execution or real installed-plugin change was performed.

A disposable Git repository on branch `dev` contained the actual three generated
packages/catalogs. Per-process Git `url.insteadOf` mapped
`https://example.invalid/nda-marketplace.git` to that local repository. This
exercises native Git cloning/ref refresh without networking or private credentials;
it does **not** establish access to the real private GitHub repository.

| Client | Executed operation | Observed result |
| --- | --- | --- |
| Codex | `plugin marketplace add <fixture-url> --ref dev` | Discovers `nda-harness-internal` at the root Codex catalog. |
| Codex | `plugin add nda-harness@nda-harness-internal` | Installs only the Codex entry; native list reports installed/enabled 0.0.4. |
| Claude | `plugin marketplace add '<fixture-url>#dev'` | Clones dev, validates the root Claude catalog, registers in the isolated user settings. |
| Claude | `plugin install nda-harness@nda-harness-internal` | Installs only the Claude entry, enabled at 0.0.4; native inventory reports the two packaged HTTP MCP declarations. |
| Codex | `plugin marketplace upgrade nda-harness-internal` after a fixture 0.0.5 commit | Native list reports installed/enabled 0.0.5; the 0.0.5 installed cache exists. No uninstall/re-add. |
| Claude | `plugin marketplace update nda-harness-internal`, then `plugin update nda-harness@nda-harness-internal` | Native inventory reports enabled 0.0.5; client explicitly says restart to apply. No uninstall/reinstall. |
| Both | Move fixture remote out of reach, then refresh | Both exit 1. All 0.0.5 installed-cache files remain byte-identical, and native lists still report installed/enabled. |

During that experiment, only the isolated test fixture was raised to 0.0.5;
repository artifacts were still **0.0.4**. The branch subsequently added the
**0.0.5** compatibility release for Python 3.9+. The native experiment above
records the earlier 0.0.4 installation and fixture update; it does not claim a
separate native installation test of the current 0.0.5 compatibility package.
The failed-fetch test checks installed-cache preservation, not transactional
guarantees for every native validation or import failure.

## Pending real-client rollout checks

| Spec test | Pending observation |
| --- | --- |
| TC-05 / Desktop | Codex Desktop and Claude Desktop loaded version, session reload and hook trust behavior; CLI results alone do not establish these. |
| TC-06 | Real private GitHub access with allowed and missing credentials, tested by the user through normal native access. |
| TC-07 | Cursor Teams/Enterprise provider authorization, private Import from Repo, tracked dev selection, Cursor-only indexing, manual/automatic refresh and installed-version activation. |
| TC-08 | Uploaded/account-synced/local identity inventory and disable/removal in actual client UI; exactly one hook/MCP activation; native reauthentication if requested. |
| TC-10 | Invalid catalog/package import and reviewed release recovery in actual clients. Unavailable local Git fetch was tested above. |

These checks remain pending. Do not infer them from JSON parsing, package hashes,
CLI installation, or upstream documentation. The repository stays private and
the implementation adds no installer for another client or custom updater.

## Documentation references

- [Codex marketplace metadata](https://developers.openai.com/plugins/build/plugins#marketplace-metadata)
- [Codex native Git upgrade implementation](https://github.com/openai/codex/blob/main/codex-rs/core-plugins/src/marketplace_upgrade.rs)
- [Cursor native marketplace schema](https://cursor.com/docs/reference/plugins)
- [Cursor team import and refresh](https://cursor.com/docs/plugins)
- [Claude private Git hosting/ref selection](https://code.claude.com/docs/en/plugins/host-marketplace)
- [Claude install/update commands](https://code.claude.com/docs/en/plugins/cli-reference)

The official schemas/commands were checked through Context7 during spec review;
installed native help and disposable-client runs above confirm the tested versions.
