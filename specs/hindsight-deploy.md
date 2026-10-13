# Developer spec: multi-user Hindsight deployment

| Item | Value |
| --- | --- |
| Primary issue | [pilacorp/nda-harness#3](https://github.com/pilacorp/nda-harness/issues/3) — Deploy multi-user Hindsight with per-user keys, schema isolation, and admin management |
| Issue content used | updated `2026-10-14T04:56:36Z` (created by @phongnhat19, updated by @thainhat04); body SHA-256 `ee294fc2a8d5012751552c2495fabb07cd2558fa4078247a44437b765d47c57e` |
| Branch | `feat/3-hindsight-deploy` |
| Phase | [Phase 1: setup internal Hindsight with OpenRouter](../plan.md#phase-1-setup-internal-hindsight-with-openrouter), [Self-hosted Hindsight](../docs/architecture.md#self-hosted-hindsight) |
| Classification | Behavior change (new Python + TypeScript code) plus deployment configuration. Full TDD; no unit-test exception. |
| Status | **Proposed.** Nothing here is implemented by this PR. Implementation follows in a second PR from this branch after approval and merge. |

The issue defines the goal, scope, out-of-scope items and acceptance criteria; this spec does not restate them. It specifies what will be built, the interfaces, the key design decisions (grounded in a spike against the fork), the models, and how each criterion will be verified.

## Spike findings (vectorize-io/hindsight v1.0.0, read before this spec)

Load-bearing; the implementation re-confirms each.

1. `TenantExtension.authenticate()` runs on every REST and MCP request, so a database-backed extension sees new keys and revocations without a restart.
2. The worker calls `list_tenants()` every poll (~500 ms), so new users get background processing without a restart, and a user removed from the list pauses (nothing lost, resumes when re-added).
3. Extension Alembic revisions apply to **every** tenant schema, so the global auth tables must **not** go through Alembic. The extension creates its own `nda_auth` schema with idempotent DDL in `on_startup()`, using the engine's pool.
4. The tenant and HTTP extensions are separate instances but run in the same API process and both receive the pool; a shared module-level store lets an HTTP revoke invalidate the tenant-auth cache in-process (cross-replica within the cache TTL).
5. The Control Plane (Next.js 16) reads cookies via `cookies()` from `next/headers` (async context), so request-scoped auth needs **no** route-handler signature changes — only the three shared API accessors become async.

## Planned behavior

Built on a fork `pilacorp/hindsight`, branch `nda/v1.0.0` from tag `v1.0.0`; the Hindsight API core (`hindsight-api-slim/`) is not modified. Two custom images are produced and deployed by a Docker Compose stack in `deploy/hindsight/`.

### Deployment

1. **Services.** Exactly two, from the custom images pinned by tag and multi-platform digest: the API (REST + MCP on 8888, includes the worker) and the Control Plane (dashboard on 9999). No database service and no local build at deploy time. Both bind to `127.0.0.1` by default; an internal reverse proxy provides TLS.
2. **External PostgreSQL/pgvector**, operator-supplied. PostgreSQL 14+, `vector` installed, a role that may create schemas (one `u_<handle>` schema per user is created at runtime) and the `pg_trgm`/`btree_gin` extensions. `deploy/postgres` remains available for non-production hosts.
3. **Credentials in `.env`**, read inside the containers and never interpolated into the Compose config (so `docker compose config` and `docker inspect` show no secret): OpenRouter key, database URL, the tenant-key pepper, and the Control Plane session secret. No shared operator key or dataplane key remains.
4. **OpenRouter** is the LLM provider (`HINDSIGHT_API_LLM_PROVIDER=openrouter`) with an explicit model; embeddings and reranking also run on OpenRouter (see [Selected models](#selected-models)). The key is server-side only; developer clients and CI never receive it.

### Multi-user

5. **Tenant extension** (`nda_hindsight_multiuser.tenant:NdaTenantExtension`, in the fork's `hindsight-extensions/`): authenticates a bearer token against database-stored keys; one PostgreSQL schema `u_<handle>` per user, provisioned (migrated) on user creation via `ExtensionContext.run_migration` under a per-schema lock (idempotent). `list_tenants()` returns active users' schemas (short cache); a disabled user is excluded. Refuses to start when `HINDSIGHT_API_MCP_AUTH_TOKEN` or `HINDSIGHT_API_TENANT_MCP_AUTH_DISABLED` is set, or the pepper is missing.
6. **Auth store** (schema `nda_auth`): `users`, `api_keys`, `audit_events`, created by idempotent DDL at startup. Keys are random, shown once, stored only as an HMAC-SHA256 hash with a server-side pepper; lookup by an indexed non-secret prefix; constant-time compare. A shared module-level store holds a short-TTL auth cache both extensions use.
7. **HTTP extension** (`nda_hindsight_multiuser.http:NdaHttpExtension`): management endpoints under `/ext/nda/v1`, authenticating every route itself (missing/invalid key → 401; wrong key kind → 403). API core unchanged.
8. **Admin vs user keys.** A user key authenticates to memory (REST/MCP) and to its own dashboard. An admin key is rejected by the tenant extension (401 on `/v1/*` and `/mcp`) and reaches only the admin endpoints. The first admin key is created by a CLI run inside the container; no key passes through an env var.
9. **Control Plane fork — login.** A single login form takes an API key, classifies it (user via `/ext/nda/v1/me`, else admin via `/admin/whoami`), and issues an encrypted, HttpOnly session cookie carrying the key. Every API route builds its dataplane client/headers from the current session (request-scoped), replacing the module-level fixed-credential clients. A `401` from the API clears the session. User sessions reach memory pages and `/api/*`; admin sessions reach only `/admin/*`. `HINDSIGHT_CP_DATAPLANE_API_KEY` and `HINDSIGHT_CP_ACCESS_KEY` are removed; `HINDSIGHT_CP_SESSION_SECRET` encrypts the cookie.
10. **Admin UI (new pages under `/admin`, admin session only).** See [Admin UI flows](#admin-ui-flows) for the screens and [Management API](#interfaces) for the endpoints each calls.
    - **Users list:** a table of all non-deleted users (handle, display name, status, active-key count, created). Actions per row: view, enable/disable, delete. A "Create user" button opens a form (handle, display name) and may issue a first key immediately, shown once.
    - **User detail:** the user's fields with inline edit of the display name and an enable/disable control, plus the user's **API-keys table** (label, prefix, created, last used, status). "Generate key" issues an **additional** key — it never replaces existing keys — and shows the secret once with a copy control. "Revoke" acts on a single key by id and leaves the user's other keys working.
    - **Delete user:** a confirm dialog stating that all the user's keys are revoked and the user is removed from the list, while their memory schema and memories are **retained** and remain outside the admin UI (a database-owner action). The handle is kept reserved so it cannot be recreated to silently reattach the old schema.
    - **Audit:** a read-only table of management actions (actor, action, target, time), never showing a key secret.
    Every admin page reads and writes only through `/ext/nda/v1/admin/*` via request-scoped `/api/admin/*` routes; none touch memory data.
11. **Rotation and lifecycle.** A user may hold several keys at once. Rotation is overlap (issue new, switch, revoke old). No forced expiry by default (`api_keys.expires_at` exists, unset). Revoking a key or disabling a user takes effect promptly (in-process at once; cross-replica within the cache TTL), including an already-open MCP session and the dashboard. Deleting a user revokes all their keys and removes them from the list but retains their schema and memories. Admin manages users and keys only; no endpoint reads or deletes another user's memory.
12. **Images and upgrades.** `hindsight-api-nda` (from `hindsight-api:1.0.0-slim`, extension added, import-checked at build) and `hindsight-control-plane-nda` (the fork), both multi-arch (amd64, arm64), pinned by digest. A documented per-release upgrade procedure rebases the NDA branch onto the new upstream tag, re-runs the Control Plane codemod, and runs the full verification.

## Acceptance criteria

IDs are stable for review and the implementation PR. "AC n" is the n-th acceptance criterion in issue #3.

| ID | Issue | Criterion the implementation must meet | Verification |
| --- | --- | --- | --- |
| MU-1 | AC 1 | Pinned Compose starts the custom services against the external PostgreSQL/pgvector, provisions no local database, and documents health checks | `preflight.sh`; `verify.sh`; E2E |
| MU-2 | AC 2 | Admin creates a user and issues a key with no restart; within seconds that user uses REST, MCP, and the dashboard; container start time unchanged. Through the Admin UI an admin performs full user CRUD (create, list/view, edit details, enable/disable, delete) and per-user key management (list, generate additional, revoke individual), with one user holding several active keys at once | unit; E2E-onboard; E2E-ui-users; E2E-ui-keys |
| MU-3 | AC 3 | Two users with the same bank id see only their own memories over REST, MCP, and the dashboard; cross-user access gives 404/empty, distinct from auth errors; two schemas exist | unit; E2E-isolation |
| MU-4 | AC 4 | Revoking a key blocks REST, MCP (open session), and dashboard promptly; the user's other keys still work; disabling a user blocks all keys and pauses background work, resuming on enable. Generating a key never replaces existing keys; revoking one leaves the others working; deleting a user revokes all keys but retains the schema and memories | unit; E2E-revoke; E2E-ui-keys; E2E-ui-users |
| MU-5 | AC 5 | Admin keys get 401 on `/v1/*` and `/mcp`; user keys get 403 on admin endpoints; an admin session has no memory pages | unit; E2E-boundary |
| MU-6 | AC 6 | Keys and the OpenRouter credential are server-side only — absent from committed files, client/CI config, logs, `docker compose config`, `docker inspect`; keys shown once, stored hashed | unit; `verify.sh`; review |
| MU-7 | AC 7 | The Control Plane authenticates each request from the logged-in key; no fixed dataplane credential or shared access key remains | lint rule; unit; review |
| MU-8 | AC 8 | Both images build for amd64 and arm64, are pinned by digest in `nda-harness`, and an upstream-upgrade procedure is documented and dry-run verified | CI; review; upgrade dry-run |

## Interfaces

**Management API** (`/ext/nda/v1`, bearer-authenticated by the extension). No endpoint returns, modifies, or deletes another user's memory, banks, or documents.

| Method & path | Caller | Behavior |
| --- | --- | --- |
| `GET /me` | user | Current user (handle, display name, key label, expiry). Used by dashboard login and Phase 2 setup verification. |
| `GET /admin/whoami` | admin | Classify an admin login. |
| `POST /admin/users` | admin | Create a user `{handle, display_name}`; provision its schema; optionally issue a first key, returned once. 409 on a used or reserved handle. |
| `GET /admin/users` | admin | List non-deleted users with status and active-key count. |
| `GET /admin/users/{handle}` | admin | One user's fields and its keys' metadata. |
| `PATCH /admin/users/{handle}` | admin | Update mutable fields (display name). |
| `POST /admin/users/{handle}/disable` / `/enable` | admin | Set status; disable blocks all the user's keys and pauses background work; enable resumes. |
| `DELETE /admin/users/{handle}` | admin | Soft-delete: revoke all the user's keys, set status `deleted`, exclude from the list and from `list_tenants`, keep the handle reserved. The schema and memories are retained (database-owner scope). 200 idempotent. |
| `POST /admin/users/{handle}/keys` | admin | Issue an **additional** key; the secret is returned **once**. Never replaces or affects existing keys. |
| `GET /admin/users/{handle}/keys` | admin | Key metadata only (id, prefix, label, created, last used, status) — never a secret. |
| `POST /admin/keys/{id}/revoke` | admin | Revoke **one** key by id; the user's other keys keep working. 200 idempotent. |
| `POST /admin/admins/keys`, `POST /admin/admins/keys/{id}/revoke` | admin | Issue / revoke admin keys. |
| `GET /admin/audit` | admin | Management audit trail; no secret in any entry. |

**Memory API / MCP:** unchanged Hindsight core. Clients authenticate with their user key; MCP per-user via `/mcp/<bank>/` and the `Authorization` header.

**Deployment env (`.env`, read inside containers):** `HINDSIGHT_API_LLM_API_KEY`, `HINDSIGHT_API_DATABASE_URL`, `HINDSIGHT_API_TENANT_KEY_PEPPER`, `HINDSIGHT_CP_SESSION_SECRET`, `HINDSIGHT_API_TENANT_EXTENSION`, `HINDSIGHT_API_HTTP_EXTENSION`, plus the model settings below. Removed from the shared-key design: `HINDSIGHT_API_TENANT_API_KEY`, `HINDSIGHT_CP_ACCESS_KEY`, `HINDSIGHT_CP_DATAPLANE_API_KEY`.

**Database:** schema `nda_auth` (extension-owned), plus one `u_<handle>` schema per user (Hindsight core tables).

### Admin UI flows

Served by the forked Control Plane under `/admin`, reachable only by an admin session; each screen calls `/api/admin/*`, which proxies to `/ext/nda/v1/admin/*` with the session's admin key. A user session never sees these pages (middleware returns 401/redirect).

| Flow | Screen & actions | Endpoints |
| --- | --- | --- |
| **List users** | Table: handle, display name, status (active/disabled/deleted hidden), active-key count, created. Per row: View, Enable/Disable, Delete. | `GET /admin/users` |
| **Create user** | Button → modal `{handle, display_name}` → on submit, optional "issue first key". A returned key is shown once in a copy-and-dismiss dialog. | `POST /admin/users` |
| **View / edit user** | Detail page: fields with inline display-name edit; Enable/Disable control. | `GET`, `PATCH`, `.../disable|enable` |
| **Delete user** | Confirm dialog: "Revokes all keys and removes the user. Memory schema and memories are retained and are not deleted here." → on confirm, row leaves the list. | `DELETE /admin/users/{handle}` |
| **List keys** | On the detail page, a keys table: label, prefix, created, last used, status. | `GET /admin/users/{handle}/keys` |
| **Generate key** | "Generate key" → modal `{label}` → the new secret shows **once** with a copy control; the keys table gains a row. Existing keys are untouched. | `POST /admin/users/{handle}/keys` |
| **Revoke key** | Per-key "Revoke" → confirm → that row becomes `revoked`; other rows stay `active`. | `POST /admin/keys/{id}/revoke` |
| **Audit** | Read-only table (actor, action, target, time). | `GET /admin/audit` |

Rules enforced in the UI and the API: a generated key is displayed exactly once and never retrievable afterward; a user may hold several `active` keys at once; generating a key never replaces or disables another; revoking one key never affects the others; deleting a user never drops a schema or deletes memories.

## Selected models

All model calls go through OpenRouter on one server-side key; chosen for the lowest cost and latency that holds English and Vietnamese quality. Prices per 1M tokens, checked 2026-10-13; re-check before rollout.

| Role | Setting | Model | Price | Note |
| --- | --- | --- | --- | --- |
| LLM | `HINDSIGHT_API_LLM_MODEL` (+ `REASONING_EFFORT=low`) | `openai/gpt-oss-20b` | $0.018 / $0.09 | Cheapest with structured outputs, which every Hindsight LLM call needs |
| Embeddings | `HINDSIGHT_EMBEDDINGS_MODEL` | `perplexity/pplx-embed-v1-0.6b` | $0.004 | Best and cheapest in an XQuAD vi/en retrieval test (R@1 0.95 MRR); 1024 dims, under pgvector's 2000 limit |
| Reranker | `HINDSIGHT_RERANKER_MODEL` (+ `MAX_CANDIDATES=100`) | `voyageai/rerank-3-lite` | $0.02 | Matched Cohere rerank-4-fast on vi/en at ~1/10 the cost |
| Keyword dict | `HINDSIGHT_API_TEXT_SEARCH_EXTENSION_NATIVE_LANGUAGE` | `simple` | — | PostgreSQL has no Vietnamese dictionary |

Estimated cost ~$0.45 per developer per month; measured in the pilot. The embedding model and dimensions are fixed after the first memory.

## Design decisions

| Decision | Rationale | Alternative rejected |
| --- | --- | --- |
| Custom DB-backed tenant extension, not StaticKeys | StaticKeys declares users in an env var and needs a restart to add/revoke; the issue requires no restart | StaticKeys / env-declared keys |
| `nda_auth` via idempotent startup DDL, not Alembic | Extension Alembic revisions apply to every tenant schema; global tables must not be duplicated | Alembic version location for auth tables |
| Shared module-level auth store | Lets HTTP-extension revoke invalidate the tenant-extension cache in one process | Separate caches: revoke would not reach the auth path |
| Admin keys rejected from memory | Admin manages users/keys only; private memory stays out of scope | Admin can read all: violates out-of-scope |
| Request-scoped CP auth via `cookies()` | Next 16 async context avoids threading `request` through 66 handlers | Per-handler signature change: larger, error-prone diff |
| Credentials in `.env`, read inside containers | One file to configure while keeping `docker compose config` free of secrets | Compose interpolation: prints every value |
| Slim API image, OpenRouter embeddings/reranking | ~500 MB vs ~3.4 GB; a deliberate deviation from the plan's "local initially" | Full image with local models |
| Fork at v1.0.0 | Latest release; extension and CP interfaces unchanged from 0.10.3; only bug fixes since | Pin 0.10.3 |

## Edge cases to handle

- An open MCP session after its key is revoked: the next call re-authenticates and gets 401.
- Two replicas provisioning the same new user schema: a per-schema advisory lock serializes it.
- A handle that is not a valid Postgres identifier, or collides after normalization: rejected at creation.
- An empty or loopback database URL: rejected (an empty URL would start Hindsight's embedded database).
- Disabling a user mid-consolidation: the task resumes on re-enable.
- Deleting a user whose schema holds memories: keys are revoked and the user leaves the list, but the schema and memories remain; recreating the same handle is refused (reserved) so the old schema is never silently reattached to a new person.
- Deleting an already-deleted user, or revoking an already-revoked key: idempotent `200`, no error.
- Re-running the Control Plane codemod on upgrade: a lint rule fails CI if any route still imports a module-level dataplane client.

## Architecture reconciliation

`docs/architecture.md` (Self-hosted Hindsight) and `plan.md` (Phase 1) currently require `StaticKeysTenantExtension` or an approved identity-provider extension, and budget Phase 1 at ~2 days. This spec replaces that with the custom extension plus Control Plane fork (about 4 weeks). The implementation PR updates both documents; this change is approved with this spec.

## Implementation plan

After this spec is approved and merged, on the same branch:

1. Fork work on `pilacorp/hindsight` `nda/v1.0.0`: the `nda_hindsight_multiuser` package (store, keys, tenant extension, HTTP extension, admin CLI) with pytest against a disposable PostgreSQL.
2. Control Plane fork: request-scoped auth codemod + lint rule, per-key login, session cookie, route guards, admin UI, with Vitest.
3. Multi-arch image builds and CI; push to GHCR under `pilacorp`.
4. `nda-harness`: `deploy/hindsight` on the custom images (pinned by digest); env/scripts (`bootstrap.sh` generates pepper and session secret and creates the first admin); `verify.sh --multiuser`; `integration-record.md`; README; and the `architecture.md`/`plan.md` updates.
5. Run the verification below; open the implementation PR with `Closes #3`.

## Verification

**Unit tests (TDD).**
- Extension (pytest, disposable PostgreSQL): key format/hashing/pepper; authenticate valid / revoked / expired / disabled-user / admin-key-rejected; cache invalidation and TTL; provisioning lock; `list_tenants`; every endpoint's 401/403/404; audit entries contain no secret; startup refuses the bypass env vars.
- Control Plane (Vitest): session encrypt/decrypt, route guards, request-scoped accessor, the lint rule.

**End-to-end (`verify.sh --multiuser` + QA, non-production PostgreSQL/pgvector).** The `ui-*` scenarios drive the Control Plane Admin UI (browser automation), not just the API.

| ID | Scenario |
| --- | --- |
| E2E-onboard | Admin creates `alice`, `bob`, issues keys; within seconds both use REST, MCP, dashboard; worker consolidates a retain; container `StartedAt` unchanged |
| E2E-isolation | Both create a bank with the same id, different notes; each sees only their own over REST/MCP/dashboard; the other gives 404; two schemas exist |
| E2E-revoke | Revoke Alice's key → REST, MCP (open session), dashboard blocked within the TTL; her second key still works; disabling Alice blocks all her keys and pauses her background work |
| E2E-boundary | Admin key → 401 on `/v1/*` and `/mcp`; admin session has no memory pages; user key → 403 on `/ext/nda/v1/admin/*` |
| E2E-secrets | Keys shown once, stored hashed; no key or OpenRouter credential in logs, `docker compose config`, or `docker inspect`; no database service in the config |
| E2E-ui-users | In the Admin UI: create a user and issue it a key; see the user in the list; open detail; edit the display name and see it persist; **disable it and confirm every key of that user is rejected on REST, MCP, and dashboard login; enable it and confirm the same keys work again**; delete it and confirm all its keys are rejected and it leaves the list while its schema still exists in the database; recreating the same handle is refused |
| E2E-ui-keys | In the Admin UI: for one user, generate key A (shown once), then generate key B without replacing A — both appear `active` and both authenticate to REST/MCP; revoke A and confirm A is rejected while B still works; the keys table shows A `revoked`, B `active`; no secret is shown again after creation |
| E2E-upgrade | Dry run: build from the next upstream tag in staging, re-run the codemod, run this whole matrix |

## Known limits and follow-ups

- Anyone with database or host-root access can read any schema; isolation is between developers, not against operators. Documented, out of scope.
- Deleting a user's memory (schema drop) is a database-owner runbook step, not an admin action.
- Cross-replica revocation latency equals the auth-cache TTL (seconds).
- Reverse proxy, TLS certificate and internal DNS: infrastructure owner.
- Agent client setup (Codex, Claude Code, Cursor) and the MCP tool allow-list: Phase 2.
