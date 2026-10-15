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

`nda-harness setup` still asks whether to enable Hindsight memory, and for which selected agents. The Hindsight MCP URL is a fixed constant. There is no URL prompt and no API-key prompt. Enabling memory opens the internal Supabase login page in the browser. Supabase redirects an authorization code to the local CLI. The CLI exchanges that code for `access_token`, `refresh_token`, and `expires_in`, and stores them in a private credentials file.

Codex, Cursor, and Claude Code keep a static MCP header, so they do not receive the Supabase tokens. Setup registers them against a loopback forwarder. The forwarder reads the credentials file, refreshes the access token before it expires, and calls the fixed Hindsight MCP URL with `Authorization: Bearer <access_token>`.

The Supabase tenant extension accepts that access token only. It checks the signature, expiry, audience `authenticated`, and issuer `{SUPABASE_URL}/auth/v1`. The `sub` claim must be a UUID. That user gets schema `user_<uuid>`. The same Supabase user on the dashboard reaches that same schema. A refresh token, the anon key, and a Hindsight API key are not tenant credentials.

In scope:

- The Hindsight enable step in interactive `setup`.
- Browser PKCE login, the credentials file, agent registration, the forwarder, and `verify`.
- `INSTALLATION.md` for the prompt change.

Out of scope:

- Deploying Supabase, building the Hindsight image, dashboard login, and the #3 cutover.
- Choosing or creating banks, bank templates, and memory instructions, except the credential wording those instructions already use.
- New setup flags, a pasted token, and non-interactive login.
- Linux, Windows, and a Hindsight admin UI.

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

Interactive setup keeps the current order. After the selected-agent menu, Enable starts login. Skip leaves credentials, the forwarder, and agent registrations unchanged.

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

For each enabled agent, register `nda-harness-hindsight` in the existing private user config:

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
| TC-08 | Successful login for Codex, Cursor, and Claude | Apply setup | Each private user entry uses `http://127.0.0.1:47321/mcp/` and `Bearer <local_secret>`. Claude stays `type: http`. Supabase tokens are absent from agent config, receipts, argv, and stdout. | unit / AC-02, AC-04 |
| TC-09 | Access token is inside the 60-second window; refresh returns a new pair | Call the forwarder with the local secret | The new refresh token is stored before the upstream call. Hindsight sees `Bearer <new access token>`. | unit / AC-02 |
| TC-10 | Forwarder running | Call with the wrong secret, or with no credentials file | 401. Hindsight is not called. | unit / AC-02 |
| TC-11 | Refresh endpoint fails | Call the forwarder | 401. The previous refresh token remains. | unit / AC-02 |
| TC-12 | Forwarder and fake Hindsight tools | Run `verify` | Tool discovery passes through the forwarder. Retain is not called and no memory is read. Output contains no token. | unit / AC-02, AC-04 |
| TC-13 | A managed connection already exists | Choose Keep, then repeat and choose Replace | Keep leaves both files unchanged. Replace updates credentials and agent entries together. | unit / AC-02 |
| TC-14 | Setup fails after writing credentials | Roll the transaction back | The previous credentials file and agent entries return. | unit / AC-02 |
| TC-15 | Login URL printed because the browser failed | Inspect stdout | The URL contains the code challenge and no verifier, code, or token. | unit / AC-04 |

## Hook changes

None.

## Documentation and rollout/recovery

Implementation updates `INSTALLATION.md`: remove the MCP URL and personal API-key rows, and describe the fixed internal service, the browser sign-in, the private credentials file, and the forwarder. Memory instructions that say "API keys" also name Supabase tokens as secrets.

Rollback is the setup transaction: restore the previous credentials file, agent entries, and LaunchAgent. A developer who still has the old API-key registration replaces it by running setup and signing in. The old key is not sent to Hindsight.

Manual check after implementation: sign in through the browser, restart the agent, list banks, and confirm the dashboard shows those banks for the same Supabase user.

## Decisions and risks

- The four constant strings are unset in this draft. Implementation waits for the internal MCP URL, Supabase URL, anon key, and authorize URL.
- The authorize URL must be the login page the internal project actually serves. The CLI always completes PKCE at `/auth/v1/token?grant_type=pkce`.
- One forwarder owns refresh. Agent processes do not refresh, so a rotated refresh token is not invalidated by a second client.
- The local secret is a loopback credential. The Supabase refresh token is the credential that must stay in `credentials.json`.

## Review and implementation handoff

Spec PR: unset
Review reference: unset until reviewed
Merge reference/revision: unset until merged
Local spec matches merged reviewed version: unset
Next action: human review of this draft. Recheck issue #10 before review; material issue edits require this draft to be updated. This document does not grant approval. Behavior-change implementation waits for review and merge of this spec.
