# Developer spec: multi-user Hindsight

| Item | Value |
| --- | --- |
| Primary issue | [pilacorp/nda-harness#7](https://github.com/pilacorp/nda-harness/issues/7) — Multi-user Hindsight: per-user keys, schema isolation, admin management (forked) |
| Issue content used | updated `2026-10-14T04:15:48Z` (created by @thainhat04); body SHA-256 `82db848eaa052715364034ced21870b167e1d848aa0ea091e03bdf03ea2158bc` |
| Branch | `feat/7-multiuser-hindsight` |
| Supersedes | [#3](https://github.com/pilacorp/nda-harness/issues/3) interim shared-key deployment and its deferred isolation follow-up |
| Phase | [Phase 1: setup internal Hindsight with OpenRouter](../plan.md#phase-1-setup-internal-hindsight-with-openrouter), [Self-hosted Hindsight](../docs/architecture.md#self-hosted-hindsight) |
| Classification | Behavior change (new Python + TypeScript code). Full TDD; no unit-test exception. |
| Status | **Proposed.** Nothing here is implemented by this PR. Implementation follows in a second PR from this branch after approval and merge. |

The issue defines the goal, scope, out-of-scope items and acceptance criteria; this spec does not restate them. It specifies what will be built, the interfaces, the key design decisions (grounded in a spike against the fork), and how each criterion will be verified.

## Spike findings (vectorize-io/hindsight v1.0.0, read before this spec)

These shape the design and are load-bearing; the implementation re-confirms each.

1. `TenantExtension.authenticate()` runs on every REST and MCP request, so a database-backed extension sees new keys and revocations without a restart.
2. The worker calls `list_tenants()` every poll (~500 ms), so new users get background processing without a restart, and a user removed from the list simply pauses (nothing lost, resumes when re-added).
3. Extension Alembic revisions are applied to **every** tenant schema, so the global auth tables must **not** go through Alembic. The extension creates its own `nda_auth` schema with idempotent DDL in `on_startup()`, using the engine's connection pool.
4. The tenant extension and HTTP extension are separate instances but run in the same API process and both receive the pool; a shared module-level store lets an HTTP revoke invalidate the tenant-auth cache in-process (cross-replica within the cache TTL).
5. The Control Plane (Next.js 16) reads cookies via `cookies()` from `next/headers`, which uses async context, so request-scoped auth needs **no** route-handler signature changes — only the three shared API accessors become async.

## Planned behavior

Built on a fork `pilacorp/hindsight`, branch `nda/v1.0.0` from tag `v1.0.0`. The Hindsight API core (`hindsight-api-slim/`) is not modified. Two custom images are produced; `nda-harness` deploys them.

1. **Tenant extension** (`nda_hindsight_multiuser.tenant:NdaTenantExtension`, in the fork's `hindsight-extensions/`).
   - Authenticates a bearer token against database-stored keys; one PostgreSQL schema `u_<handle>` per user.
   - A user's schema is provisioned (migrated) on user creation via `ExtensionContext.run_migration`, under a per-schema lock; re-provision is idempotent.
   - `list_tenants()` returns active users' schemas (short cache), so the worker processes them. A disabled user is excluded.
   - Refuses to start when `HINDSIGHT_API_MCP_AUTH_TOKEN` or `HINDSIGHT_API_TENANT_MCP_AUTH_DISABLED` is set (either would bypass per-user auth), or when the key pepper is missing.
2. **Auth store** (schema `nda_auth`): `users`, `api_keys`, `audit_events`, created by idempotent DDL at startup. Keys are random, shown once, stored only as an HMAC-SHA256 hash with a server-side pepper; lookup by an indexed non-secret prefix; constant-time compare. A shared module-level store instance holds a short-TTL auth cache that both extensions use.
3. **HTTP extension** (`nda_hindsight_multiuser.http:NdaHttpExtension`) mounts management endpoints under `/ext/nda/v1`, authenticating every route itself (missing/invalid key → 401; wrong key kind → 403). API core is unchanged.
4. **Admin vs user keys.** A user key authenticates to memory (REST/MCP) and to its own dashboard. An admin key is rejected by the tenant extension (401 on `/v1/*` and `/mcp`), and reaches only the admin endpoints. The first admin key is created by a CLI run inside the container; no key is passed through an environment variable.
5. **Control Plane fork.** A single login form takes an API key, classifies it (user via `/ext/nda/v1/me`, else admin via `/admin/whoami`), and issues an encrypted, HttpOnly session cookie carrying the key. Every API route builds its dataplane client/headers from the current session (request-scoped), replacing the module-level fixed-credential clients. A `401` from the API clears the session. User sessions reach memory pages and `/api/*`; admin sessions reach only `/admin/*`. `HINDSIGHT_CP_DATAPLANE_API_KEY` and `HINDSIGHT_CP_ACCESS_KEY` are removed; a new `HINDSIGHT_CP_SESSION_SECRET` encrypts the cookie.
6. **Rotation and lifecycle.** A user may hold several keys at once. Rotation is overlap: issue a new key, switch, revoke the old. No forced expiry by default (`api_keys.expires_at` exists, unset). Revoking a key or disabling a user takes effect promptly (in-process at once; across replicas within the cache TTL), including an already-open MCP session, and including the dashboard. Admin manages users and keys only; no endpoint reads or deletes another user's memory.
7. **Images and upgrades.** `hindsight-api-nda` (from `hindsight-api:1.0.0-slim`, extension added, import-checked at build) and `hindsight-control-plane-nda` (the fork), both multi-arch (amd64, arm64), pinned by digest in `nda-harness`. A documented per-release upgrade procedure rebases the NDA branch onto the new upstream tag, re-runs the Control Plane codemod, and runs the full verification.

## Acceptance criteria

IDs are stable for review and the implementation PR. "AC n" is the n-th acceptance criterion in issue #7.

| ID | Issue | Criterion the implementation must meet | Verification |
| --- | --- | --- | --- |
| MU-1 | AC 1 | Admin creates a user and issues a key with no restart; within seconds that user uses REST, MCP, and the dashboard. Container start time is unchanged throughout | unit; E2E-onboard |
| MU-2 | AC 2 | Two users with the same bank id see only their own memories over REST, MCP, and the dashboard; cross-user access gives 404/empty, distinct from auth errors; the database shows two schemas | unit; E2E-isolation |
| MU-3 | AC 3 | Revoking a key blocks REST, MCP (including an open session), and dashboard promptly; the user's other keys still work; disabling a user blocks all their keys and pauses background work, resuming on enable | unit; E2E-revoke |
| MU-4 | AC 4 | Admin keys get 401 on `/v1/*` and `/mcp`; user keys get 403 on admin endpoints; an admin session has no memory pages | unit; E2E-boundary |
| MU-5 | AC 5 | Keys are shown once, stored only as hashes, and absent from committed files, logs, `docker compose config`, and `docker inspect` | unit; `verify.sh`; review |
| MU-6 | AC 6 | The Control Plane authenticates each request from the logged-in key; no fixed dataplane credential or shared access key remains | lint rule; unit; review |
| MU-7 | AC 7 | Both images build for amd64 and arm64, are pinned by digest in `nda-harness`, and an upstream-upgrade procedure is documented and dry-run verified | CI; review; upgrade dry-run |

## Interfaces

**Management API** (`/ext/nda/v1`, bearer-authenticated by the extension):
`GET /me` (user), `GET /admin/whoami` (admin), `POST|GET /admin/users`, `GET /admin/users/{handle}`, `POST /admin/users/{handle}/{disable,enable}`, `POST|GET /admin/users/{handle}/keys`, `POST /admin/keys/{id}/revoke`, `POST /admin/admins/keys`, `POST /admin/admins/keys/{id}/revoke`, `GET /admin/audit`. No endpoint returns another user's memory, banks, or documents.

**Memory API / MCP:** unchanged Hindsight core. Clients authenticate with their user key; MCP per-user via `/mcp/<bank>/` and the `Authorization` header.

**Deployment env (`nda-harness`, `.env`, read inside containers):** adds `HINDSIGHT_API_TENANT_EXTENSION`, `HINDSIGHT_API_HTTP_EXTENSION`, `HINDSIGHT_API_TENANT_KEY_PEPPER`, `HINDSIGHT_CP_SESSION_SECRET`; removes `HINDSIGHT_API_TENANT_API_KEY`, `HINDSIGHT_CP_ACCESS_KEY`, `HINDSIGHT_CP_DATAPLANE_API_KEY`.

**Database:** schema `nda_auth` (extension-owned), plus one `u_<handle>` schema per user (Hindsight core tables).

## Design decisions

| Decision | Rationale | Alternative rejected |
| --- | --- | --- |
| Custom DB-backed tenant extension, not StaticKeys | StaticKeys declares users in an env var and needs a restart to add/revoke; the issue requires no restart | StaticKeys / env-declared keys |
| `nda_auth` via idempotent startup DDL, not Alembic | Extension Alembic revisions apply to every tenant schema; global tables must not be duplicated per user | Alembic version location for auth tables |
| Shared module-level auth store | Lets HTTP-extension revoke invalidate the tenant-extension cache in one process | Separate caches: revoke would not reach the auth path |
| Admin keys rejected from memory | Admin manages users/keys only; private memory stays out of scope | Admin can read all: violates the issue's out-of-scope |
| Request-scoped CP auth via `cookies()` | Next 16 async context avoids threading `request` through 66 handlers | Per-handler signature change: larger, error-prone diff |
| Slim API image | Embeddings/reranking run on OpenRouter; ~500 MB vs ~3.4 GB | Full image: unused local models |
| Fork at v1.0.0 | Latest release; extension and CP interfaces unchanged from 0.10.3; only bug fixes since | Pin 0.10.3: older, no benefit |

## Edge cases to handle

- An open MCP session after its key is revoked: the next call authenticates again and gets 401.
- Two replicas provisioning the same new user schema: per-schema advisory lock serializes it.
- A handle that is not a valid Postgres identifier, or collides after normalization: rejected at creation.
- Disabling a user mid-consolidation: the task is not lost; it resumes when the user is re-enabled.
- Re-running the Control Plane codemod on upgrade: a lint rule fails CI if any route still imports a module-level dataplane client.

## Architecture reconciliation

`docs/architecture.md` (Self-hosted Hindsight) and `plan.md` (Phase 1) currently require `StaticKeysTenantExtension` or an approved identity-provider extension, and budget Phase 1 at ~2 days. This spec replaces that with the custom extension plus Control Plane fork (about 4 weeks). The implementation PR updates both documents; this change is approved with this spec.

## Implementation plan

After this spec is approved and merged, on the same branch:

1. Fork work on `pilacorp/hindsight` `nda/v1.0.0`: the `nda_hindsight_multiuser` package (store, keys, tenant extension, HTTP extension, admin CLI) with pytest against a disposable PostgreSQL.
2. Control Plane fork: request-scoped auth codemod + lint rule, per-key login, session cookie, route guards, admin UI, with Vitest.
3. Multi-arch image builds and CI; push to GHCR under `pilacorp`.
4. `nda-harness`: switch `deploy/hindsight` to the custom images (pinned by digest), update env/scripts (`bootstrap.sh` generates pepper and session secret and creates the first admin), `verify.sh --multiuser`, `integration-record.md`, README, and update `architecture.md`/`plan.md`.
5. Run the verification below; open the implementation PR with `Closes #7`.

## Verification

**Unit tests (TDD).**
- Extension (pytest, disposable PostgreSQL): key format/hashing/pepper; authenticate valid / revoked / expired / disabled-user / admin-key-rejected; cache invalidation and TTL; provisioning lock; `list_tenants`; every endpoint's 401/403/404; audit entries contain no secret; startup refuses the bypass env vars.
- Control Plane (Vitest): session encrypt/decrypt, route guards, request-scoped accessor, the lint rule.

**End-to-end (`verify.sh --multiuser` + QA, non-production PostgreSQL/pgvector).**

| ID | Scenario |
| --- | --- |
| E2E-onboard | Admin creates `alice`, `bob`, issues keys; within seconds both use REST, MCP, dashboard; worker consolidates a retain; container `StartedAt` unchanged |
| E2E-isolation | Both create a bank with the same id, different notes; each sees only their own over REST/MCP/dashboard; the other gives 404; two schemas exist |
| E2E-revoke | Revoke Alice's key → REST, MCP (open session), dashboard blocked within the TTL; her second key still works; disabling Alice blocks all her keys and pauses her background work |
| E2E-boundary | Admin key → 401 on `/v1/*` and `/mcp`; admin session has no memory pages; user key → 403 on `/ext/nda/v1/admin/*` |
| E2E-secrets | Keys shown once, stored hashed; none in logs, `docker compose config`, or `docker inspect` |
| E2E-upgrade | Dry run: build from the next upstream tag in staging, re-run the codemod, run this whole matrix |

## Known limits and follow-ups

- Anyone with database or host-root access can read any schema; isolation is between developers, not against operators. Documented, out of scope.
- Deleting a user's memory (schema drop) is a database-owner runbook step, not an admin action.
- Cross-replica revocation latency equals the auth-cache TTL (seconds).
- Agent client setup (Codex, Claude Code, Cursor) and the MCP tool allow-list remain Phase 2.
