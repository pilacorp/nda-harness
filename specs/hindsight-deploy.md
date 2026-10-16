# Developer spec: Supabase-tenant Hindsight deployment

| Item | Value |
| --- | --- |
| Primary issue | [pilacorp/nda-harness#10](https://github.com/pilacorp/nda-harness/issues/10) — Update internal Hindsight to the Supabase tenant extension |
| Supersedes | [#3](https://github.com/pilacorp/nda-harness/issues/3) (custom per-user API keys + admin UI) — replaced wholesale |
| Implementation | fork `pilacorp/hindsight`, branch `nda/10-supabase-tenant` |
| Phase | [Self-hosted Hindsight](../docs/architecture.md#self-hosted-hindsight) |
| Classification | Behavior change (Control Plane + deploy) plus a new OAuth HTTP extension in the API image. Hindsight API core and the upstream tenant extension are unmodified. |
| Status | **Implemented** on the fork branch; local end-to-end verified. This PR reconciles the spec; the dev-spec had described the #3 model. |

Identity and the database come from a **self-hosted open-source [Supabase](https://github.com/supabase/supabase)** (Auth + Postgres); Supabase Cloud is not a target. Each Supabase user gets an isolated PostgreSQL schema `user_<uuid>`, provisioned on first authenticated access. Hindsight issues and stores **no** keys. This replaces the custom `NdaTenantExtension` + `nda_auth` API-key store and the admin UI from #3.

## Spike findings (vectorize-io/hindsight, read before this spec)

Load-bearing; each is confirmed by the implementation.

1. `TenantExtension.authenticate()` runs on every REST and MCP request, so the Supabase extension sees a new user (and a rotated/expired token) without a restart.
2. The worker calls `list_tenants()` to decide which schemas to consolidate; the API and worker must get the **same** Supabase settings. Upstream `list_tenants()` returns only schemas this process has already initialized — after a restart a user's schema resumes consolidation once they authenticate again.
3. The upstream `supabase-tenant` extension (`hindsight_ext_supabase_tenant:SupabaseTenantExtension`) **only verifies** a Supabase JWT (JWKS locally, or `/auth/v1/user` for legacy HS256) and maps the `sub` claim to schema `{prefix}_{uuid}` (hyphens → underscores). It is a resource server; it is not an OAuth authorization server and does not manage users.
4. Self-hosted Hindsight core speaks **bearer-token only** — no OAuth endpoints or discovery metadata (native MCP OAuth is a Hindsight Cloud feature). The OAuth endpoints are added by an **HTTP extension** (`get_router`/`get_root_router`) loaded into the API image; the API core and the tenant extension are not modified.
5. The Control Plane (Next.js 16) reads the incoming request with `headers()` from `next/headers` (async context), so forwarding the browser's Supabase token needs **no** route-handler signature changes — one shared accessor reads the bearer.

## Planned behavior

Built on the fork `pilacorp/hindsight`, branch `nda/10-supabase-tenant`; `hindsight-api-slim/` and `hindsight-extensions/supabase-tenant/` are **not** modified. Compose stacks live in the fork under `deploy/`.

### Deployment

1. **Supabase stack** (`deploy/supabase/`): a minimal self-hosted open-source Supabase — Postgres + GoTrue Auth + an nginx gateway (`/auth/v1/*` → GoTrue). Only what Hindsight needs; PostgREST/Realtime/Storage/Studio/pooler/functions are dropped. Images and init scripts are pinned from `supabase/supabase`. For local dev it ships Supabase's published **demo HS256 keys**; a real deployment regenerates them.
2. **Hindsight stack** (`deploy/hindsight/`): the API (REST + MCP + in-process worker), and the Control Plane dashboard. The API also serves MCP OAuth via an HTTP extension (below). **No database service** — `HINDSIGHT_API_DATABASE_URL` points at the Supabase Postgres (which provides `vector`).
3. **Credentials in `.env`**, read inside the containers and never interpolated into the Compose config: OpenRouter key, the Supabase Postgres URL, the Supabase API URL, and (only for HS256 projects) the Supabase service key. No Hindsight key pepper or dataplane key exists any more.
4. **OpenRouter** is the LLM provider with explicit models; embeddings and reranking also run on OpenRouter (see [Selected models](#selected-models)). The key is server-side only.

### Identity and tenancy

5. **Tenant extension** = upstream `hindsight_ext_supabase_tenant:SupabaseTenantExtension`, built into the API image (`hindsight-extensions/supabase-tenant/Dockerfile`, base `hindsight-api:1.0.0-slim`), unmodified. Config: `HINDSIGHT_API_TENANT_SUPABASE_URL` (required), `HINDSIGHT_API_TENANT_SUPABASE_SERVICE_KEY` (only for HS256 / health check — prefer JWKS), `HINDSIGHT_API_TENANT_SCHEMA_PREFIX` (default `user`). Startup fails when the Supabase URL is missing, or the project is HS256 and no service key is set.
6. **Schema per user.** A Supabase user calling REST/MCP with their access token gets schema `user_<uuid>` created on first access, no restart. Isolation is at the database level; two users with the same bank id see only their own memories.
7. **Supabase is the only identity source.** New users, passwords, and revocation are managed in Supabase, not in Hindsight. There is no Hindsight admin UI or key API.

### Control Plane (dashboard) — Supabase sign-in

8. The login page signs the developer in through the internal Supabase Auth using `@supabase/supabase-js` **client-side**; the browser holds the session and auto-refreshes it. There is no API-key login form and no admin area.
9. The browser forwards its Supabase access token as `Authorization: Bearer <jwt>` on every `/api/*` call. The proxy routes read that bearer and forward it to the dataplane (one shared accessor); all bank routes are unchanged. Middleware returns a clean `401` for an `/api` call with no bearer (except `/api/version`, `/api/health`), and the client then redirects to sign-in. On a 401 the client refreshes the Supabase session once, else signs out.
10. The CP image bakes `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` at build (Next inlines `NEXT_PUBLIC_*`); the anon key is public by design.

### Local agents — MCP OAuth (HTTP extension)

11. **nda-oauth HTTP extension** (`hindsight-extensions/nda-oauth/`, in the API image): Hindsight itself speaks **OAuth 2.1 + Dynamic Client Registration (RFC 7591) + PKCE S256**, so an agent connects once in a browser and the session **refreshes itself** — no 1h static token pasted into a config. It serves `/.well-known/oauth-*` (root) and `/ext/oauth/{register,authorize,token}`; `/authorize` logs the user into Supabase (password grant, aiohttp) and `/token` hands the agent the **Supabase JWT directly** (pass-through, with the Supabase refresh token). The agent then calls the API's MCP endpoint **directly** and the unchanged `supabase-tenant` extension verifies it — no proxy, no gateway, no server-side session store. PKCE via `hashlib`; no hand-rolled crypto.
12. **Cutover from #3.** The custom `nda-multiuser` extension, the `nda_auth` key store, the API-key dashboard login, and the admin UI are removed. Old `u_<handle>` schemas and `nda_auth` keys are **not** reused as Supabase tenants and are never attached to a Supabase user; a fresh local run clears them. Rollback restores the previous image, `HINDSIGHT_API_TENANT_EXTENSION`, and database URL.

## Acceptance criteria

IDs are stable for review. "AC n" is the n-th acceptance criterion in issue #10.

| ID | Issue | Criterion | Verification |
| --- | --- | --- | --- |
| SB-1 | AC 1 | Self-hosted open-source Supabase runs; `HINDSIGHT_API_DATABASE_URL` points at its Postgres; Compose starts no database of its own | `deploy/supabase` + `deploy/hindsight`; E2E |
| SB-2 | AC 2 | The pinned API image includes `hindsight_ext_supabase_tenant` and starts with the tenant env on API and worker; startup fails on missing Supabase URL, or HS256 with no service key | build import-check; **startup-fail test (verified)** |
| SB-3 | AC 3 | A Supabase user calls REST and MCP with their token and no Hindsight key; first call creates `user_<uuid>` with no restart | E2E (verified: REST 200, MCP initialize 200) |
| SB-4 | AC 4 | Two users with the same bank id see only their own memories over REST/MCP/dashboard; two schemas exist | E2E (verified: two `user_<uuid>` schemas, each token its own) |
| SB-5 | AC 5 | The dashboard signs in via Supabase Auth; an API key cannot sign in; after login the developer manages their own banks with their Supabase token | E2E |
| SB-6 | AC 6 | An expired token is refreshed and work continues; an invalid/wrong-project token returns to login and is 401 on REST/MCP/bank requests | E2E (OAuth refresh verified; no-token 401 verified) |
| SB-7 | AC 7 | Dashboard and MCP as the same Supabase user reach the same schema; one user cannot see another's banks | E2E |
| SB-8 | AC 8 | `nda-harness setup` no longer asks for a Hindsight API key; it registers the API's MCP URL (OAuth on first use) and `verify` reaches the API's OAuth discovery; docs match | CLI (follow-up branch) |
| SB-9 | AC 9 | Supabase service key (if set) and Postgres password stay server-side — absent from committed files, client/CI config, logs, `docker compose config`, `docker inspect` | `verify`; review |
| SB-10 | AC 10 | After an API restart a user signs in again and reaches their previous banks; consolidation resumes after that auth; another user's schema is not consolidated as theirs | E2E |
| SB-11 | AC 11 | A documented cutover + rollback covers the previous extension, the API-key login, and the database URL | `deploy/hindsight/README`, `deploy/supabase/README` |

## Interfaces

**Memory API / MCP (Hindsight, unchanged core):** clients authenticate with a Supabase JWT. `GET/POST /v1/default/banks/...` and MCP `/mcp/<bank>/` with `Authorization: Bearer <supabase_jwt>`. The tenant extension maps the token to `user_<uuid>`.

**Supabase Auth** (`<supabase>/auth/v1/*`, via the stack's gateway): `POST /token?grant_type=password` (sign-in), `POST /token?grant_type=refresh_token`, `GET /user`, `POST /admin/users` (service key) for provisioning dev users. JWKS at `/auth/v1/.well-known/jwks.json` when the project uses asymmetric keys.

**MCP OAuth** (nda-oauth HTTP extension, served by the API):

| Method & path | Purpose |
| --- | --- |
| `GET /.well-known/oauth-authorization-server` | RFC 8414 AS metadata |
| `GET /.well-known/oauth-protected-resource` | RFC 9728; points MCP clients here |
| `POST /register` | Dynamic Client Registration (RFC 7591) |
| `GET /authorize` | Auth-code + PKCE S256; login form → Supabase password grant |
| `POST /token` | code→tokens (PKCE verified) and `refresh_token` → Supabase refresh |
| MCP `/mcp/<bank>/` (API core) | The agent calls this directly with the Supabase JWT from `/token`; supabase-tenant verifies |

**Deployment env (`.env`, read inside containers):** `HINDSIGHT_API_LLM_API_KEY`, `HINDSIGHT_API_DATABASE_URL` (→ Supabase Postgres), `HINDSIGHT_API_TENANT_SUPABASE_URL`, `HINDSIGHT_API_TENANT_SUPABASE_SERVICE_KEY` (HS256 only), `HINDSIGHT_API_TENANT_SCHEMA_PREFIX` (optional), `HINDSIGHT_API_HTTP_EXTENSION` (=`nda_oauth.extension:NdaOAuthExtension`), `HINDSIGHT_API_HTTP_SUPABASE_URL`, `HINDSIGHT_API_HTTP_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, plus the model settings below. Removed vs #3: `HINDSIGHT_API_TENANT_KEY_PEPPER` and all `nda_auth`/dataplane-key settings.

**Database:** one `user_<uuid>` schema per Supabase user in the Supabase Postgres (Hindsight core tables). No `nda_auth` schema.

## Selected models

Unchanged from the earlier plan — all calls go through OpenRouter on one server-side key, chosen for the lowest cost/latency holding English and Vietnamese quality. Prices per 1M tokens; re-check before rollout.

| Role | Setting | Model | Price | Note |
| --- | --- | --- | --- | --- |
| LLM | `HINDSIGHT_API_LLM_MODEL` | `openai/gpt-oss-20b` | $0.018 / $0.09 | Cheapest with the structured outputs every Hindsight LLM call needs |
| Embeddings | `HINDSIGHT_EMBEDDINGS_MODEL` | `perplexity/pplx-embed-v1-0.6b` | $0.004 | Best/cheapest in a vi/en retrieval test; 1024 dims, under pgvector's limit |
| Reranker | `HINDSIGHT_RERANKER_MODEL` | `voyageai/rerank-3-lite` | $0.02 | Matched Cohere rerank-4-fast on vi/en at ~1/10 the cost |

The embedding model and dimensions are fixed after the first memory.

## Design decisions

| Decision | Rationale | Alternative rejected |
| --- | --- | --- |
| Upstream `supabase-tenant`, not a custom extension | Supabase is the identity source; the extension only verifies its JWT — no keys to issue, store, or revoke in Hindsight | The #3 custom `NdaTenantExtension` + `nda_auth` |
| Self-hosted open-source Supabase, not Cloud | Internal infra, data stays in-house | Supabase Cloud |
| Dashboard sign-in client-side (supabase-js) | Standard Supabase SPA pattern; auto-refresh for free; issue #10 doesn't mandate server-side | `@supabase/ssr` httpOnly cookies (more secure; a later hardening option) |
| MCP OAuth as an HTTP extension in the API, not a separate gateway | One service; "Hindsight handles login"; the extension adds OAuth without touching core | A separate gateway service (more moving parts); native OAuth (Cloud-only); static pasted token (1h) |
| `/token` returns the Supabase JWT directly (pass-through) | The agent hits MCP directly; `supabase-tenant` stays the single verifier; no proxy or session store | Opaque gateway token → needs a proxy + session store |

## Edge cases to handle

- A Supabase access token expires mid-session: the dashboard (supabase-js) refreshes in the browser; an MCP agent refreshes via the OAuth `/token` refresh grant.
- A wrong-project / wrong-audience / expired-unrefreshable token: 401 on REST/MCP; the dashboard returns to sign-in.
- HS256 self-hosted project (no JWKS): the extension falls back to `/auth/v1/user`, which needs the service key — startup enforces this.
- First call for a brand-new Supabase user: schema provisioned on demand, no restart.
- After an API restart: `list_tenants()` only knows initialized schemas; a user's consolidation resumes once they authenticate again (documented, not a bug).
- Old `u_<handle>` schemas from #3: never attached to a Supabase user.

## Cutover and rollback

- Remove the `nda-multiuser` extension, `nda_auth`, the API-key login, and the admin UI. Switch `HINDSIGHT_API_TENANT_EXTENSION` to the Supabase extension and `HINDSIGHT_API_DATABASE_URL` to the Supabase Postgres. For a fresh local run, drop the old schemas.
- Rollback = run the previous `hindsight-api-nda` image, restore the `nda_hindsight_multiuser` extension env (pepper + HTTP extension), the API-key Control Plane image, and the previous database URL.

## Verification

**Automated / done so far (local, against `deploy/supabase`):**
- 57 upstream extension tests pass in the built image (JWT verify, schema mapping, `list_tenants`, non-UUID / SQL-injection rejection, HS256 fallback, shutdown).
- Startup fails with a clear error when `HINDSIGHT_API_TENANT_SUPABASE_URL` is missing.
- REST: no token → 401; Supabase token → 200 and `user_<uuid>` provisioned. Two users → two isolated schemas.
- Dashboard login path (browser → CP proxy → API) → 200 with a Supabase token; unauthenticated `/api/banks` → 401; `/api/version` public → 200; single CORS `Allow-Origin`.
- OAuth-in-API full flow (`test_oauth_mcp.py`): discovery on the API → DCR → `/authorize` (Supabase login) → PKCE token (a Supabase JWT) → MCP `initialize` + tools/list (36 tools) directly on the API → refresh → no-token 401. ALL PASS.

**End-to-end (QA, against the self-hosted Supabase):**

| ID | Scenario |
| --- | --- |
| E2E-signin | Sign in on the dashboard with a Supabase user; an API key cannot sign in; create/list/open own banks |
| E2E-isolation | Two Supabase users, same bank id; each sees only their own over REST/MCP/dashboard; two `user_<uuid>` schemas exist |
| E2E-refresh | An expired dashboard session refreshes and still opens the same bank; an invalid/wrong-project token returns to sign-in and is 401 |
| E2E-mcp-oauth | An MCP client (Claude Code/Cursor/Codex) pointed at the API completes DCR + browser approval, connects with no pasted token, and keeps working past the 1h token lifetime |
| E2E-restart | After an API restart, a user signs in again and reaches previous banks; consolidation resumes after that auth |
| E2E-secrets | Supabase service key (if used) and the Postgres password absent from logs, `docker compose config`, `docker inspect` |

## Known limits and follow-ups

- Anyone with database or host-root access can read any schema; isolation is between developers, not against operators. Out of scope.
- Dropping a user's memory schema is a database-owner runbook step, not a dashboard action.
- Dashboard sign-in is client-side (token in browser storage); `@supabase/ssr` httpOnly cookies are a later hardening option.
- The OAuth extension keeps auth codes + registered clients in memory (single replica, dev/pilot); move to a shared store to scale or survive restarts. MCP-client auto-discovery relies on the API serving `/.well-known/oauth-*`; a client that only discovers via the MCP 401 `WWW-Authenticate` challenge needs that header added (follow-up).
- `nda-harness setup` / `verify` changes (register the API's MCP URL; no static token) and `INSTALLATION.md` land on a follow-up branch.
