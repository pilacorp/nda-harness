# Developer spec: Hindsight setup signs in with Supabase

Status: draft for human review
Feature issue: [pilacorp/nda-harness#10](https://github.com/pilacorp/nda-harness/issues/10)
Issue updated at: `2026-10-15T11:14:51Z`
Issue body SHA-256: `e9d04202c574d90b6442299fa538f246ed77ea24cc74ce8f3d19ad31129d54b8`
Consulted source revisions: this branch at `c1e5001fb0286e15bc4140c4570bf1f3f44797dc`; upstream Supabase tenant extension read from the local Hindsight checkout at `e30a55f7b8383cadefdd695ac7a96949006d32fb` (`hindsight-extensions/supabase-tenant`)
Spec branch: `specs/hindsight-supabase-auth`

This spec covers the CLI slice of #10. Supabase deployment, the Hindsight image, dashboard login, schema cutover, and rollback stay on the issue and are not implemented here.

The issue's CLI sentence says setup collects an MCP URL and a hidden Supabase access token into the private client config. This spec is the agreed replacement for that step. Review of this draft is the reconciliation.

## Outcome and boundaries

Task classification: behavior change.

Developers install one plugin per client: Codex, Cursor, or Claude Code. Each plugin contains the same CLI bundle, and installation runs that bundle's `install.sh`. That places the `nda-harness` command on the default prefix. It does not sign the developer in. A developer who uses more than one client installs each plugin.

The plugin's client is the only agent it configures. Setup and verify do not ask which agent to use, and they do not offer a Hindsight agents menu. Opening the plugin in the client shows its knowledge systems. This revision has one entry, Hindsight, labeled as the memories system. `nda-harness setup` still asks whether to enable Hindsight memory. The Hindsight MCP URL is a fixed constant. There is no URL prompt and no API-key prompt. Enabling memory opens the internal Supabase login page in the browser. Supabase redirects an authorization code to the local CLI. The CLI exchanges that code for `access_token`, `refresh_token`, and `expires_in`, and stores them in a private credentials file.

Codex, Cursor, and Claude Code keep a static MCP header, so they do not receive the Supabase tokens. Setup registers them against a loopback forwarder. The forwarder reads the credentials file, refreshes the access token before it expires, and calls the fixed Hindsight MCP URL with `Authorization: Bearer <access_token>`.

The Supabase tenant extension accepts that access token only. It checks the signature, expiry, audience `authenticated`, and issuer `{SUPABASE_URL}/auth/v1`. The `sub` claim must be a UUID. That user gets schema `user_<uuid>`. The same Supabase user on the dashboard reaches that same schema. A refresh token, the anon key, and a Hindsight API key are not tenant credentials.

In scope:

- Three plugin packages, `nda-harness-codex`, `nda-harness-cursor`, and `nda-harness-claude`. Each vendors the CLI, runs its `install.sh` on install, and configures only its own client.
- The Hindsight enable step in interactive `setup`.
- Browser PKCE login, the credentials file, agent registration, the forwarder, and `verify`.
- `INSTALLATION.md` for the plugin install and the prompt change.

Out of scope:

- Deploying Supabase, building the Hindsight image, dashboard login, and the #3 cutover.
- Choosing or creating banks, bank templates, and memory instructions, except the credential wording those instructions already use.
- A RAG system. The knowledge-system list can hold one later. This revision does not add, configure, or sign in a RAG entry.
- New setup flags, a pasted token, and non-interactive login.
- Linux, Windows, and a Hindsight admin UI.
- Publishing the plugin to a public marketplace. Local installation of the package in this repository is the supported path.

## Plugin installation

The repository contains three plugins. Each contains the CLI tree (`install.sh`, `bin/`, `scripts/`, `pack/`, `skills/`, and `vendor/`) and the manifest for one client:

| Plugin | Client | Registration it owns |
| --- | --- | --- |
| `nda-harness-codex` | Codex | Codex user TOML |
| `nda-harness-cursor` | Cursor | Cursor user JSON |
| `nda-harness-claude` | Claude Code | Claude user JSON, `type: http` |

Installation copies that plugin. It does not download a second copy of the CLI. All three ship the same CLI revision.

Installing a plugin runs the bundled `install.sh` with no arguments. `install.sh` requires Python 3.11+, installs the bundle under the default prefix, and prints the `nda-harness` command. Installing the same version again is a repair, specified in [Plugin version and upgrade](#plugin-version-and-upgrade). A newer version follows that section too. Plugin installation does not run `nda-harness setup`, open the browser, or write Hindsight credentials.

None of the three clients has an install-time script hook. The plugin's first session in a new version runs `install.sh`. Reinstalling the same version runs it as a repair. A later session runs it when the installed files no longer match the plugin, and otherwise leaves that version unchanged. A failing `install.sh` is reported and leaves the previous bundle in place.

Setup and verify receive the plugin's client as a fixed family. There is no Agents prompt, no `--agents` list, and no Hindsight agents prompt. Scope, the project root, and the unit-test command remain prompts. Enabling Hindsight registers `nda-harness-hindsight` for that plugin's client only. Installing the Cursor plugin does not write Codex or Claude configuration.

## Plugin version and upgrade

Each plugin manifest has a `version` of `MAJOR.MINOR.PATCH`. The three plugins in one release use the same version. `install-manifest.json` records that version and the file hashes. `nda-harness --version` prints the version installed at `~/.local/share/nda-harness`. This revision does not use pre-release tags.

The first session after a plugin update compares the plugin version with the installed version:

| Installed bundle | Plugin version | Result |
| --- | --- | --- |
| Absent | Any | Install the bundle. |
| Same version | Same | Repair. Replace the program files from the plugin, whether or not the installed files match. |
| Older version, hashes match its manifest | Newer | Replace the bundle. |
| No `version` field, hashes match its manifest | Any versioned plugin | Replace the bundle. This covers a CLI installed before plugin versions existed. |
| Hashes do not match its manifest | Newer | Refuse. Reconcile the edited bundle before upgrading. |
| Newer version | Older | Refuse the downgrade. Leave the installed bundle in place. |

A refused downgrade or a refused upgrade does not change the bundle, the shim, credentials, or project files.

A same-version install is a repair. `install.sh` replaces the program files below from the plugin copy, including when those files already match and when they were edited. The files in [What an upgrade keeps](#what-an-upgrade-keeps) stay byte for byte. The forwarder restarts from the repaired bundle. Repair does not run setup and does not open the browser.

A later session does not run that repair while the installed version matches and the bundle hashes match the plugin. Reinstalling the plugin runs it. A same-version bundle whose hashes differ is repaired on the next session.

### What an upgrade replaces

The client replaces the plugin directory it loaded. `install.sh` then replaces the shared program files:

- `~/.local/share/nda-harness/`, including `bin/`, `scripts/`, `pack/`, `skills/`, `vendor/`, and `install-manifest.json`
- `~/.local/bin/nda-harness`, when the launcher text changes
- The forwarder code, by restarting `com.pilacorp.nda-harness.hindsight-forwarder` from the new bundle
- The LaunchAgent program arguments, only when the new version's plist differs. The label stays the same.

The replacement is atomic. The installer stages the new bundle, moves the old bundle to `~/.local/share/nda-harness.previous`, and moves the new bundle into place. It then runs `nda-harness --version` and requires the new version. If that command fails, it puts the previous bundle and shim back. After a successful start, it deletes `nda-harness.previous`.

### What an upgrade keeps

These stay byte for byte. Upgrade does not prompt, and it does not run setup or open the browser:

- `~/.nda-harness/state/hindsight/credentials.json`, including `access_token`, `refresh_token`, `expires_at`, and `local_secret`
- Receipts under `~/.nda-harness/state/`
- `~/.nda-harness/bin/rtk`
- The user pack at `~/.nda-harness/pack` and each project's `.nda-harness/` pack, `profile.json`, Git hook, and task records
- Client MCP entries, including the forwarder URL and the existing `local_secret` bearer
- Instruction files setup already wrote for Codex, Cursor, and Claude Code
- The Supabase session. The developer does not sign in again.

A minor or patch upgrade reads credentials `schema_version` 1. A major upgrade that cannot read the file leaves it in place and asks the developer to run setup and sign in. This revision does not define that migration. Minor and patch releases must keep reading schema 1.

The restarted forwarder uses the kept credentials and the same `local_secret`, so the agent configuration remains valid. One MCP call can fail during the restart. The client retries.

Updating one plugin upgrades the shared CLI. An older copy of another plugin does not downgrade it. Its detail page still shows the `knowledge_systems` list packaged in that older plugin, while `nda-harness` runs the newer CLI. Update all three installed plugins to the same version. A future RAG row appears only in a release whose list contains it. That release still keeps the Hindsight credentials.

## Plugin detail list

Each plugin manifest carries a `knowledge_systems` list. The client's plugin detail page lists those entries by name and role. Codex, Cursor, and Claude Code show a plugin's MCP servers on that page, so each list entry is one MCP server contributed by the plugin. The visible name is the entry's `name`, and the visible description is its role.

This revision contains one entry, the same in all three plugins:

| Field | Value |
| --- | --- |
| `id` | `hindsight` |
| `name` | `Hindsight` |
| `role` | `memories` |
| `description` | `Memories system` |

Opening the plugin shows Hindsight as the memories system. The server behind that row is the Hindsight forwarder registered by setup. Before setup, the row is present and the connection is not signed in.

The list is the extension point for a later RAG system. A RAG entry uses a new `id`, `role` `retrieval`, its own name and description, and its own MCP server. The manifest schema accepts `memories` and `retrieval`. This revision ships no `retrieval` entry. Adding one does not change the Hindsight entry, the Supabase login, or the credentials file.

## Fixed constants

These values are constants in the CLI. Setup does not prompt for them. Login refuses to start while any value is empty.

| Constant | Value |
| --- | --- |
| `HINDSIGHT_MCP_URL` | Internal multi-bank MCP URL. The path ends in `/mcp/` or `/mcp`. HTTPS, with no user, password, query, or fragment. |
| `SUPABASE_URL` | Internal Supabase API origin, no trailing slash. |
| `SUPABASE_ANON_KEY` | Anon key sent as the Auth `apikey` header. |
| `SUPABASE_AUTHORIZE_URL` | Internal Supabase login page for this deployment. |
| Forwarder | `127.0.0.1:47321` |
| Login callback | `127.0.0.1:47322` |

The four string values are the one input still required before implementation. The deployment must allow the exact redirect `http://127.0.0.1:47322/callback`.

## Login

Interactive setup keeps the current order after the removed agent menus. Enable starts login for the plugin's client. Skip leaves credentials, the forwarder, and that client's registration unchanged.

1. Bind `127.0.0.1:47322` and accept only `GET /callback`. If the port is busy, stop before opening a browser.
2. Generate a PKCE verifier and an S256 challenge. The verifier stays in memory for this attempt.
3. Open `SUPABASE_AUTHORIZE_URL` in the browser, preserving its existing query, and add `redirect_to=http://127.0.0.1:47322/callback`, `code_challenge`, and `code_challenge_method=s256`. If the browser cannot be opened, print that URL and keep waiting.
4. Wait up to 5 minutes. The callback is accepted only when it carries one `code` parameter. A Supabase `error` parameter, a missing code, or an `access_token` or `refresh_token` in the query or fragment ends the attempt with nothing stored.
5. Exchange the code:

```http
POST {SUPABASE_URL}/auth/v1/token?grant_type=pkce
apikey: {SUPABASE_ANON_KEY}
Authorization: Bearer {SUPABASE_ANON_KEY}
Content-Type: application/json

{"auth_code": "<code>", "code_verifier": "<verifier>"}
```

6. Require `access_token`, `refresh_token`, and a positive integer `expires_in`. Decode the access token payload without verifying the signature. Require audience `authenticated` and a UUID `sub`. The Hindsight server verifies the signature.
7. Hold the tokens in memory until the setup transaction commits. Cancellation, timeout, a closed callback port, or a failed exchange stores nothing and exits before installation writes. Cancellation exits 130. The other login failures exit 1.

Non-interactive setup skips the memory step, as it does today. There is no flag or environment variable for a token.

## Credentials file

Path: `~/.nda-harness/state/hindsight/credentials.json`

The directory is mode `0700`. The file is mode `0600`. Writes are atomic. The file contains:

| Field | Source |
| --- | --- |
| `schema_version` | `1` |
| `access_token` | token response |
| `refresh_token` | token response |
| `expires_at` | UTC time of receipt plus `expires_in` seconds |
| `local_secret` | 32-byte random secret, created on first success and kept across refresh and later logins |

Tokens stay out of agent config, project files, receipts, arguments, terminal output, and diagnostics. The ownership receipt continues to store digests only.

Replacing a managed connection still requires the existing Keep / Replace confirmation. Keep discards the new tokens. Replace writes the credentials and the agent entries in the same transaction. Rollback restores the previous credentials file and agent entries together.

## Agent registration and forwarder

Register `nda-harness-hindsight` in the private user config of the plugin's client:

| Agent | Entry |
| --- | --- |
| Codex | user TOML `http_headers.Authorization` |
| Cursor | user JSON `headers.Authorization` |
| Claude Code | user JSON `type: http` and `headers.Authorization` |

The URL is `http://127.0.0.1:47321/mcp/`. The bearer is `local_secret`. Config and backup files stay mode `0600`. Existing rules still apply: reject a client home inside a Git checkout, reject a project entry that shadows this server name, preserve unrelated servers, and reject an unmanaged conflict.

`nda-harness hindsight-forwarder` listens on `127.0.0.1:47321` only. Setup installs a user LaunchAgent, `com.pilacorp.nda-harness.hindsight-forwarder`, with `RunAtLoad` and `KeepAlive`, and restarts it after a credentials write. Logs go under the private state directory and contain no tokens or `Authorization` headers.

On each request the forwarder:

1. Requires `Authorization: Bearer <local_secret>`. Any other request gets 401 and is not forwarded.
2. Takes an exclusive lock on the credentials file when `expires_at` is within 60 seconds.
3. Refreshes with `POST {SUPABASE_URL}/auth/v1/token?grant_type=refresh_token` and body `{"refresh_token": "<refresh_token>"}`, using the same anon-key headers as login.
4. Saves the returned `access_token`, rotated `refresh_token`, and new `expires_at` before forwarding. A failed refresh leaves the previous refresh token in place and returns 401.
5. Forwards to `HINDSIGHT_MCP_URL` with `Authorization: Bearer <access_token>`. Redirects are not followed.

Missing credentials return 401 with the text `Run nda-harness setup and sign in`.

## Verify

`verify` stays read-only for agent config. It checks credentials permissions and fields, checks that each enabled agent points at the forwarder with `local_secret`, and checks that both Supabase tokens are absent from agent config and receipts. It then initializes MCP through the forwarder and discovers the existing required tools (`list_banks`, `create_bank`, recall, retain, bank configuration, mental models, and directives), all with `bank_id` where required. It does not call retain and does not read memories.

A 401 from the forwarder is a failed Hindsight check telling the developer to run setup and sign in again. Client restart and fresh-session checks stay pending.

## Acceptance mapping

| ID | Issue criterion | Expected behavior |
| --- | --- | --- |
| AC-01 | `nda-harness setup` no longer asks for a personal Hindsight API key | Enable opens the Supabase login page. The URL and API-key prompts are gone. |
| AC-02 | Enabling Hindsight stores the internal MCP URL and a Supabase access token privately, and `verify` authenticates with that token | Tokens and `expires_at` are in `credentials.json`. Agent config points at the forwarder. `verify` reaches Hindsight through it with the current access token. |
| AC-03 | Docs for the setup prompt match the new step | `INSTALLATION.md` describes browser login, the credentials file, and the forwarder. |
| AC-04 | Developer tokens are not written to logs | Login, the forwarder, setup output, and `verify` omit access tokens, refresh tokens, the local secret, and the authorization code. |
| AC-05 | Plugin installation provides the CLI | Installing any of the three plugins runs the bundled `install.sh`. The `nda-harness` command is available afterward. Setup and Supabase login have not run. |
| AC-06 | Setup does not ask the developer to choose an agent | Codex, Cursor, and Claude each have their own plugin. Setup and verify configure that plugin's client only, with no Agents prompt and no Hindsight agents prompt. |
| AC-07 | The plugin detail page shows Hindsight as the memories system | Each plugin's `knowledge_systems` list has one entry, Hindsight, with role `memories`. The detail page lists that entry. No RAG entry is installed. |
| AC-08 | A newer plugin version replaces the program and keeps the developer session | The shared CLI bundle and forwarder code are replaced. Credentials, `local_secret`, receipts, project packs, Git hooks, and client MCP entries stay. Setup does not run again. The same version repairs those program files and keeps the same state. A downgrade is refused. |

The other acceptance criteria in #10 belong to the server, dashboard, and cutover work.

## Concrete test cases

Unit tests use local fake Supabase and Hindsight HTTP servers. They do not open a browser or call the network. Planned tests, not executed evidence.

| ID | Setup/input | Action | Expected result | Layer / acceptance IDs |
| --- | --- | --- | --- | --- |
| TC-01 | Terminal; Hindsight enabled; authorize URL constant set | Run the login collector with a fake browser opener | The opened URL contains the S256 challenge and `redirect_to=http://127.0.0.1:47322/callback`. No URL or API-key prompt runs. | unit / AC-01 |
| TC-02 | Fake Supabase returns a JWT with audience `authenticated`, a UUID `sub`, a refresh token, and `expires_in` | Complete the callback with `code` | `credentials.json` is mode `0600`, the directory is mode `0700`, and the file has the access token, refresh token, `expires_at`, and `local_secret`. | unit / AC-02 |
| TC-03 | Callback includes `access_token` or `refresh_token` | Finish the callback | Login fails and no credentials file is written. | unit / AC-01, AC-04 |
| TC-04 | Token audience is wrong, or `sub` is not a UUID | Exchange the code | Login fails and no credentials file is written. | unit / AC-02 |
| TC-05 | Existing credentials and agent entry | Choose Skip | No browser opens. Credentials and agent config are unchanged. | unit / AC-01 |
| TC-06 | stdin is not a terminal | Run setup | The memory step is skipped. No login starts. | unit / AC-01 |
| TC-07 | Callback port busy, callback times out, or the exchange returns an error | Start login | Exit 1 before installation writes. Ctrl+C exits 130. Nothing is stored. | unit / AC-02 |
| TC-08 | Successful login from the Cursor plugin, then from the Codex and Claude plugins | Apply setup for each plugin | Each run writes only that client's private user entry, using `http://127.0.0.1:47321/mcp/` and `Bearer <local_secret>`. Claude stays `type: http`. Supabase tokens are absent from agent config, receipts, argv, and stdout. | unit / AC-02, AC-04, AC-06 |
| TC-09 | Access token is inside the 60-second window; refresh returns a new pair | Call the forwarder with the local secret | The new refresh token is stored before the upstream call. Hindsight sees `Bearer <new access token>`. | unit / AC-02 |
| TC-10 | Forwarder running | Call with the wrong secret, or with no credentials file | 401. Hindsight is not called. | unit / AC-02 |
| TC-11 | Refresh endpoint fails | Call the forwarder | 401. The previous refresh token remains. | unit / AC-02 |
| TC-12 | Forwarder and fake Hindsight tools | Run `verify` | Tool discovery passes through the forwarder. Retain is not called and no memory is read. Output contains no token. | unit / AC-02, AC-04 |
| TC-13 | A managed connection already exists | Choose Keep, then repeat and choose Replace | Keep leaves both files unchanged. Replace updates credentials and agent entries together. | unit / AC-02 |
| TC-14 | Setup fails after writing credentials | Roll the transaction back | The previous credentials file and agent entries return. | unit / AC-02 |
| TC-15 | Login URL printed because the browser failed | Inspect stdout | The URL contains the code challenge and no verifier, code, or token. | unit / AC-04 |
| TC-16 | Plugin package with the CLI tree; no `nda-harness` command installed | Run the plugin install hook | The hook executes the bundled `install.sh` with no arguments. The command shim exists. No browser opens and no credentials file is written. | unit / AC-05 |
| TC-17 | The same plugin version is installed, once with matching files and once with edited bundle files | Run `install.sh` again | Both runs replace the program files from the plugin. Credentials, receipts, project files, and MCP entries stay. Setup is not run. | unit / AC-05, AC-08 |
| TC-18 | Cursor plugin setup on a terminal | Run setup with no agent flag | No Agents prompt and no Hindsight agents prompt appear. The resulting registration is Cursor only. The same holds for the Codex and Claude plugins. | unit / AC-06 |
| TC-19 | Each plugin manifest | Read `knowledge_systems` and the MCP servers the detail page lists | The list has one entry: name `Hindsight`, role `memories`, description `Memories system`. Its MCP server is the Hindsight forwarder. No `retrieval` entry is present. The schema still accepts a later `retrieval` entry without changing the Hindsight entry. | unit / AC-07 |
| TC-20 | Installed `1.0.0` whose files match its manifest; credentials, a project pack, a Git hook, and a Cursor MCP entry exist | Upgrade to plugin `1.1.0` | The shared bundle and shim are the new version. Credentials, `local_secret`, receipts, the project pack, the Git hook, and the MCP entry are byte-for-byte unchanged. Setup is not run. | unit / AC-08 |
| TC-21 | Upgrade staged, then `nda-harness --version` fails | Finish the upgrade | The previous bundle and shim are restored. Credentials are unchanged. | unit / AC-08 |
| TC-22 | Installed `1.1.0` | Run the hook from plugin `1.0.0` | The downgrade is refused. The bundle and state stay on `1.1.0`. | unit / AC-08 |
| TC-23 | Installed bundle hashes do not match its manifest | Upgrade to a newer plugin | The upgrade is refused and nothing is replaced. | unit / AC-08 |
| TC-24 | Cursor plugin `1.1.0` upgrades the shared CLI; Codex plugin `1.0.0` then starts | Run the Codex first-session hook | The CLI stays at `1.1.0`. The Codex detail list is still the list packaged in `1.0.0`. | unit / AC-08 |

## Hook changes

Each plugin adds one first-session hook for its own client. It runs the bundled `install.sh` when the installed version is missing or older. It does not run setup, login, or a new Supabase sign-in. After a bundle replacement it restarts the forwarder. The Agents and Hindsight agents prompts are removed from setup and verify.

## Documentation and rollout/recovery

Implementation updates `INSTALLATION.md`: install the plugin for the client in use, which runs `install.sh`, then run `nda-harness setup`. Remove the Agents prompt, the Hindsight agents prompt, the MCP URL row, and the personal API-key row. Describe the three plugins, the version, what an upgrade replaces and keeps, the fixed internal service, the browser sign-in, the private credentials file, and the forwarder. Memory instructions that say "API keys" also name Supabase tokens as secrets.

Rollback is the setup transaction: restore the previous credentials file, agent entries, and LaunchAgent. A developer who still has the old API-key registration replaces it by running setup and signing in. The old key is not sent to Hindsight.

Manual check after implementation: sign in through the browser, restart the agent, list banks, and confirm the dashboard shows those banks for the same Supabase user.

## Decisions and risks

- The four constant strings are unset in this draft. Implementation waits for the internal MCP URL, Supabase URL, anon key, and authorize URL.
- The authorize URL must be the login page the internal project actually serves. The CLI always completes PKCE at `/auth/v1/token?grant_type=pkce`.
- One forwarder owns refresh. Agent processes do not refresh, so a rotated refresh token is not invalidated by a second client.
- The local secret is a loopback credential. The Supabase refresh token is the credential that must stay in `credentials.json`.
- Each plugin vendors the CLI and its install runs `install.sh` only. Supabase login stays in interactive `nda-harness setup`.
- The plugin replaces the agent choice. Scope, project root, and the unit-test command stay.
- `knowledge_systems` is the list the plugin detail page shows. Hindsight is its only entry in this revision. RAG is a future `retrieval` entry in that same list.
- The three plugins share one installed CLI. A newer plugin upgrades it, and an older plugin does not downgrade it. Update all installed plugins to the same version.

## Review and implementation handoff

Spec PR: unset
Review reference: unset until reviewed
Merge reference/revision: unset until merged
Local spec matches merged reviewed version: unset
Next action: human review of this draft. Recheck issue #10 before review; material issue edits require this draft to be updated. This document does not grant approval. Behavior-change implementation waits for review and merge of this spec.
