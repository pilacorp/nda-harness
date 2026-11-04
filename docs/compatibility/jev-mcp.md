# Jev local MCP implementation evidence

Date: 2026-11-04. Runtime implementation is available for review; cross-client
native acceptance and release remain pending. The user explicitly authorized
implementation of `specs/jev-mcp.md` in chat. No issue publication, spec PR merge,
release approval or native-client success is inferred from that authorization.

## Automated evidence

`tests/test_jev_mcp.py` uses temporary homes, fake keys, local-agent answers and
mock provider responses. It makes no live OpenRouter calls. Fixtures cover:

- Protocol 2025-06-18 negotiation and initialization, four stable strict tool
  schemas, notifications, invalid JSON/UTF-8/envelopes/ids, unknown methods/tools,
  wrong argument types, task limits, line limits, sanitized exceptions and tool
  errors, and bounded responses without partial bodies.
- Relocated executable packages for Codex, Cursor, Claude and the hosted Claude
  archive, including paths with spaces and an inherited `CODEX_SANDBOX` marker.
  Each launches from `/`, performs offline verification, local-agent selection,
  loads all four shipped specialists, and reconnects using the existing cache.
  The same direct CLI launcher still refuses sandboxed verification.
- Mocked paid selection, empty/confident/uncertain output parity with CLI,
  exact human decisions, shared cache reuse, wrong-task load refusal, symlinked
  keys, release-integrity failure, invalid input before credential access,
  sanitized private-state denial, and explicit synthetic-only live verification.

The complete four-specialist loader response is 61,729 UTF-8 bytes with JSON-RPC
id 1 in canonical source, well below 2 MiB. Subprocess tests independently check
the actual installed response bound. Existing selection/credential tests cover
cache TTL, generation/catalog/body invalidation, concurrent cache locking,
fixed endpoint, provider failures, no redirects and no retries.

The complete suite passes all 269 tests (186.227 seconds):
`rtk proxy env -u CODEX_SANDBOX python3 -m unittest discover -s tests`.
The final focused adapter rerun also passes all 9 tests. The full suite required
loopback binding outside the shell sandbox for an existing bank-selection HTTP
fixture. An initial restricted run also exposed an old CLI-guidance assertion
(updated for MCP) and a transient terminal cancellation failure; both pass on
the final full-suite rerun. All three committed packages were
regenerated through `plugin_build --publish-committed`; runtime bytes match the
canonical sources and package release integrity checks pass. All three generated
ZIPs pass the existing archive validator. `git diff --check` is clean.

Tests run on Python 3.13.2. The implementation uses Python 3.9-compatible stdlib
syntax and APIs; all bundled runtime modules parse with Python 3.9 grammar, but a separate Python 3.9 interpreter was not verified here.
Legacy CLI tests model an unrestricted entry process by removing the inherited
sandbox marker only from the test runner environment. Explicit sandbox fixtures
and installed MCP subprocesses set the marker themselves. Production code never
unsets it or exposes a trusted flag.

## Native acceptance still required

| Client / installation | Version observed | Server/tool enablement and actual shell restrictions | Status |
| --- | --- | --- | --- |
| Codex installed plugin | Not established | Not verified in a fresh session | Pending TC-12 |
| Cursor installed plugin | 3.28.7 app metadata | Not verified in a fresh session | Pending TC-13 |
| Claude installed plugin | Not established | Not verified in a fresh session | Pending TC-14 |
| Claude hosted archive | Not established | Launcher relocation verified only in subprocess | Pending TC-14 |

These versions are an inventory, not native acceptance. The current chat has no
registered Jev tools. Codex and Claude apps were not found in the standard
`/Applications/<name>.app` locations; this does not establish their absence from
the machine. Reloaded native discovery, root-variable expansion, client tool
permissions, the actual OS key/cache/network boundary, human uncertainty
confirmation, and preserved shell restrictions need per-client observation.
Do not change global permissions to obtain passing evidence. Managed denial
must be reported as `jev_mcp_unavailable` and acceptance stays pending.

No developer key was read by these fixtures and no paid check was authorized or
performed. Failure/reconnect fixtures demonstrate completed-cache reuse, not
exactly-once billing or all crash timing windows. Native timeout/denial/crash
observations remain part of release acceptance.
