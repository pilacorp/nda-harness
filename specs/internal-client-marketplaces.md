# Internal Git marketplaces for Codex, Cursor, and Claude

Feature issue: [pilacorp/nda-harness#20](https://github.com/pilacorp/nda-harness/issues/20)
Issue updated at: 2026-10-20T08:39:11Z
Issue body SHA-256: 256fb2bfcb01bc9606a45f5a450ae51a58601128b3e2e342391f490c02dff3ec
Consulted source revisions: NDA Harness dev at `f624ca69c2331bb3a28150579ce205682d036a11`.
Spec branch: `codex/20-client-marketplace-spec`

## Summary

Use the existing private `pilacorp/nda-harness` repository as a native marketplace
for Codex, Cursor, and Claude Code. One marketplace catalog per client exposes one
logical plugin named `nda-harness`, backed by a separate client-bound package.
No separate service, marketplace repository, public listing, or repository visibility
change is required. The initial distribution ref is `dev`, matching the active
integration branch; changing it later is an explicit administrator rollout decision.

The latest private ZIP upload failed while an older plugin was installed. Its
underlying server response is unknown. This specification does not diagnose that
failure or promise an in-place migration of an uploaded plugin's identity.

## Setup and daily use

All commands below are proposed installation documentation, not executed evidence.
The administrator merges reviewed package and catalog changes into `dev`, grants
company users read access, and publishes a distinct manifest version for each
release. The first marketplace release is `0.0.4` for all three clients.

Codex users add the Git marketplace and install its entry:

```sh
codex plugin marketplace add git@github.com:pilacorp/nda-harness.git --ref dev
codex plugin add nda-harness@nda-harness-internal
```

Use existing Git/SSH authentication, never credentials embedded in URLs. Later
updates use `codex plugin marketplace upgrade nda-harness-internal`. Native Codex
source supports refreshing installed non-curated plugins after Git marketplace
refresh. Document the observed desktop activation behavior rather than promising
all existing chats reload immediately.

Claude users run `claude plugin marketplace add
"git@github.com:pilacorp/nda-harness.git#dev"`, then
`claude plugin install nda-harness@nda-harness-internal`. The Git URL fragment
selects the tracked branch; SSH must already work without an interactive prompt.
Later updates refresh the marketplace with `claude plugin marketplace update
nda-harness-internal`, then run `claude plugin update nda-harness@nda-harness-internal`.
The new version loads next session or through `/reload-plugins` when supported.
Do not write repository-wide settings to install it for other users implicitly.

Cursor's private team distribution uses Teams or Enterprise and **Dashboard →
Plugins & MCPs → Team Marketplaces → Add Marketplace → Import from Repo**. Connect
the repository provider, select the tracked `dev` ref where supported, set access
to the intended company team, and verify the index resolves the Cursor package.
The administrator can click Refresh. GitHub Auto Refresh additionally needs the
Cursor GitHub App authorized for this repository; indexing is rate-limited to at
most once per ten minutes. If branch selection or private import is unavailable
for the actual account, mark that rollout check pending and report the limitation;
do not publish the repo or claim Codex/Claude CLI commands work in Cursor.

## Outcome and boundaries

Task classification: behavior change.

This follow-up supersedes the limited clauses in `specs/harness-plugins.md` that
exclude stored Claude packages and released-installation update documentation.
All workflow, optional Hindsight, hook preservation, and fixed-client requirements
remain applicable. This change does not relax their authorization requirements.

In scope: repository-native catalogs, all three generated packages, versioned
release generation, native install/update instructions, and one-time migration
checks. Existing canonical shared assets remain the single source of truth.

Out of scope: changing repository visibility; public directory submission; automatic
migration across plugin identities; global user-policy changes; automatic installs
into another client; custom update daemons; credential migration; OAuth/server
changes; fixing the unknown ZIP-upload error; promising identical UI or automatic
update behavior across clients.

## Implementation

### Repository layout and routing

```text
.agents/plugins/marketplace.json        # Codex catalog
.cursor-plugin/marketplace.json         # Cursor catalog
.claude-plugin/marketplace.json         # Claude catalog
packages/
  nda-harness-codex/                    # .codex-plugin/plugin.json
  nda-harness-cursor/                   # .cursor-plugin/plugin.json
  nda-harness-claude/                   # .claude-plugin/plugin.json
```

Use `nda-harness-internal` as the stable marketplace name in each catalog and
`nda-harness` as the plugin name. Use each client's native marketplace schema:
Codex uses a local source object with `path: ./packages/nda-harness-codex`, required
category and install/auth policy; Cursor uses its native source-path entry for
`packages/nda-harness-cursor`; Claude uses `source: ./packages/nda-harness-claude`
and required owner metadata. Do not reuse one schema indiscriminately. Paths are
resolved against the repository root and must remain inside it. Root catalogs
are not plugin manifests and must not register hooks or MCP servers themselves.

Every catalog has exactly one entry targeting its own package. Codex catalog
discovery prefers `.agents/plugins/marketplace.json`; the native Claude and Cursor
catalog paths must be validated with their actual discovery mechanisms. Never
interpret a successful JSON parse as proof that a host imports the marketplace.

### Release generation

Extend the existing shared package publisher instead of adding an updater or a
second build pipeline. `--publish-committed` generates the three packages and
root catalogs deterministically from canonical sources. Set the shared release
version to `0.0.4`; all package manifests and generated version metadata must agree.
Keep existing standalone archive/directory build options functional. Reject bad
catalog paths and mismatched client routing in package verification/tests.

The stored Claude package uses the ordinary directory layout with `bin/nda-plugin`.
Its hosted ZIP build continues relocating that helper to `scripts/nda-plugin`;
that upload-specific workaround does not belong in Git marketplace catalogs.
Preserve default-file discovery rules so Claude hook and MCP registrations are
not duplicated by extra manifest declarations. Keep executable permissions,
dependency pins, licenses, provenance, and file hash integrity intact.

Include only committed package source assets. Never package `.nda-harness` project
records, private receipts, credentials, or workstation paths. Package updates do
not install project copies of shared rules or skills.

### Identity, migration, and recovery

Marketplace-qualified identities differ from uploaded/account-synced or ad-hoc
local installations. Inventory the old identity before switching and disable the
old client-specific plugin before enabling the marketplace entry. Prefer reversible
disable when available; if a client requires removal, explicitly document that
one-time step rather than promising uninstall-free initial migration. Do not
disable plugins for other clients or treat a synced Claude plugin as a Codex install.

Preserve committed project profile/test-command/memory-bank settings. OAuth belongs
to the client; do not inspect, export, copy or rewrite tokens. A new native identity
may require the user's ordinary client authentication action; do not promise
credential continuity. Later marketplace version upgrades must not require routine
manual uninstall/reinstall. Verify Git hook wrappers after an upgrade: if an old
version cache path becomes unavailable, the existing setup recovery must rebind it
safely; report pending protection until complete instead of silently leaving broken
hooks. Do not invent a second hook manager for distribution.

Document recovery using a reviewed revert on the tracked release ref and a
verified package version; do not hand-edit caches. Preserve existing working
installs if a fetch, import, or validation fails. State native client limitations
where atomic failure recovery has not been observed.

## Acceptance mapping

| ID | Issue criterion | Expected behavior |
| --- | --- | --- |
| AC-01 | Native catalogs | Three root catalogs expose only the corresponding package. |
| AC-02 | Complete releases | Three committed packages are generated from shared sources at version 0.0.4. |
| AC-03 | Client isolation | Paths resolve inside the repo; hooks/helpers/MCP stay bound to the correct client. |
| AC-04 | Internal access | Repo stays private; private Git/provider access and tracked dev ref are documented. |
| AC-05 | Native updates | Each host's supported install/refresh/update steps and prerequisites are documented honestly. |
| AC-06 | One-time migration | Old activation is avoided, project config is preserved, OAuth is left to the host. |
| AC-07 | Evidence | Routing, determinism, package versions and hook binding are tested; unexecuted host checks remain pending. |
| AC-08 | Scope | No custom updater, global cross-client installer or public publishing is added. |

## Concrete test cases

These are planned tests, not executed compatibility evidence.

| ID | Setup/input | Action | Expected result | Layer / acceptance IDs |
| --- | --- | --- | --- | --- |
| TC-01 | Fresh generated repo layout | Resolve each root catalog | Exactly one entry; correct existing package and matching native plugin name/client. | unit / AC-01, AC-03 |
| TC-02 | Catalog fixtures with missing, escaping or wrong-client source | Validate | Rejected with a useful diagnostic; no claim of successful installation. | unit / AC-01, AC-03 |
| TC-03 | Canonical source and version 0.0.4 | Publish twice | Same file names/content/hashes; all three manifests use 0.0.4; no stale generated Claude exclusion. | packaging / AC-02, AC-07 |
| TC-04 | Three directory builds and ZIP builds | Validate assets and hook commands | Native formats and fixed clients preserved; Claude directory/hosted ZIP launcher difference remains valid. | packaging / AC-02, AC-03 |
| TC-05 | Local Git marketplace fixture, isolated client homes | Discover/install then publish a higher version and update | Codex/Claude native commands resolve correct package and new version without routine uninstall; original user settings untouched. | local integration where available / AC-05, AC-07 |
| TC-06 | Private repo access present/absent | Register marketplace using native host | Correct access works; unavailable credentials leave an actionable error; no credential collection. | real client/manual / AC-04, AC-05 |
| TC-07 | Cursor Teams/Enterprise account with repository provider access | Import from Repo, set team access, refresh | Only Cursor package indexed; tracked ref confirmed; native installed refresh behavior recorded. | real client/manual / AC-01, AC-04, AC-05 |
| TC-08 | Existing uploaded/synced/local identity | Follow migration steps | Only one NDA hook/MCP activation per client; existing project settings unchanged; optional native reauth clearly reported. | real client/manual / AC-03, AC-06 |
| TC-09 | Project wrapper pointing to prior package cache | Upgrade package and verify/recover setup | Commit protection remains functional or is explicitly pending until safely rebound; no duplicate wrappers. | integration / AC-05, AC-06 |
| TC-10 | Invalid/unavailable release | Refresh/update | Existing install is preserved where native behavior supports it; documented recovery/pending evidence otherwise. | integration/manual / AC-05, AC-07 |

## Hook changes

No new lifecycle events or global registrations. Existing packaged client hooks
remain unchanged. Distribution tests cover their client binding, duplicate
activation during migration, and Git wrapper paths after a native version upgrade.

## Documentation and review handoff

Update README, INSTALLATION, and client compatibility documentation with private
repo registration, initial dev ref, one-time migration, updates, release publishing,
Cursor plan/provider requirements, and verified versus pending checks. Reconcile
the superseded clauses in the existing plugin spec when implementation lands.

Sources consulted on 2026-10-20:

- [Codex marketplace metadata](https://developers.openai.com/plugins/build/plugins#marketplace-metadata)
- [Codex native marketplace update implementation](https://github.com/openai/codex/blob/main/codex-rs/core-plugins/src/marketplace_upgrade.rs)
- [Cursor plugin reference](https://cursor.com/docs/reference/plugins)
- [Cursor team marketplaces and refresh](https://cursor.com/docs/plugins)
- [Claude hosting and private access](https://code.claude.com/docs/en/plugins/host-marketplace)
- [Claude install/update commands](https://code.claude.com/docs/en/plugins/cli-reference)

The issue owns intent. Implementation starts only after this spec has been
reviewed and merged and its local revision matches that merged content.
