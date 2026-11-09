# Identify the coding agent on Hindsight MCP requests

- Feature issue: https://github.com/pilacorp/nda-harness/issues/57
- Issue updated at: 2026-11-09T09:13:32Z
- Issue body SHA-256: 0c0b50eb6b2e4810790a246511d897c815463c1d7430562485c42b75dbb1cbd9
- Consulted source revisions: NDA Harness `d6d4217db1fd100e18da4b5feb712be31d875eae`, Hindsight contract `a8f7c4b30741592e3927f1ae4a21f2907e815dc6`

## Summary

The NDA Harness package builder will add the fixed `X-Hindsight-Coding-Agent` header to each client's Hindsight MCP configuration. Hindsight uses it to attribute authenticated connections on the team usage page. The value identifies the client family and carries no user or project data. [Hindsight header contract](https://github.com/pilacorp/hindsight/pull/54)

## Implementation

This behavior change applies to the `nda-harness-hindsight` remote server entry emitted by `scripts/nda_harness/plugin_build.py`. Set the header in the native plugin manifest's `headers` object, alongside any existing headers. Preserve the current server key, URL, transport fields, and OAuth handling. Apply the same rule to a configured Hindsight endpoint override so the release package can be tested against a disposable endpoint. Context7, NDA RAG, Jev, and other server entries retain their current configuration.

| Client | Packaged manifest | Header value |
| --- | --- | --- |
| Cursor | `mcp.json` | `cursor` |
| Codex | `.mcp.json` | `codex` |
| Claude Code | `.mcp.json` | `claude-code` |

The native clients continue to own OAuth discovery, sign-in, and authorization headers. The package adds only the client identifier to the MCP transport. Hindsight's classification, storage, and dashboard are tracked separately. [Cursor MCP configuration](https://cursor.com/docs/mcp), [Codex plugin HTTP configuration](https://github.com/openai/codex/blob/main/codex-rs/codex-mcp/src/agent_plugin_config.rs), [Claude Code MCP configuration](https://code.claude.com/docs/en/mcp), [Hindsight issue #51](https://github.com/pilacorp/hindsight/issues/51)

## Acceptance and verification

| ID | Check | Expected result |
| --- | --- | --- |
| AC-01–03 | Build and inspect the packages for all three clients. | Each Hindsight entry contains its exact header value and retains the existing URL and transport shape. |
| AC-04 | Inspect default, endpoint-override, and Hindsight-omitted builds. | Only Hindsight receives the attribution header. Existing headers and OAuth configuration are preserved, and a build that omits Hindsight has no attribution header. |
| AC-05 | Load each built package in its supported native client against a disposable Hindsight MCP endpoint. Complete client-managed OAuth with a test account, then reconnect and trigger MCP discovery. | For each client, capture a successful authenticated `POST` whose JSON-RPC method is `initialize` and whose attribution header has the expected value. |

Start with failing assertions in `tests/test_plugins.py`. Update the builder, regenerate the tracked packages, and run the package tests and canonical build verification. Record native client versions and sanitized evidence for the three initialization requests. Keep the request method, JSON-RPC method, attribution header value, and response status. Exclude tokens, cookies, user identifiers, and full request payloads.

If a supported client ignores the header, record its version and the observed request. Resolve client compatibility before marking AC-05 complete.

## Rollout and review

No hook changes or setup changes are required. Regenerate the three packages through the existing build workflow. An earlier package can still connect because the server contract treats the header as optional.

This draft awaits review and merge. Before implementation, verify that a maintainer reviewed the spec PR, that GitHub shows it merged, and that the local spec matches the merged revision. Package tests and native request captures are planned.
