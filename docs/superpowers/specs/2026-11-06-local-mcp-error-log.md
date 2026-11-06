# Add a private local error log for Jev, Hindsight, and RAG MCP

Type: feature

Feature issue: https://github.com/pilacorp/nda-harness/issues/48
Issue updated at: 2026-11-06T10:12:47Z
Issue body SHA-256: `35c5eaa7bd0ece734bc51ed7a19e994ecf9405c5e9337fce3ceb2b42ff178d29`
Consulted source revision: `ab989440955f0bd4341d680ef7c1e1c8cc7f692c` (`dev`)
Spec branch: `spec/local-mcp-error-log`

## Problem

NDA Harness needs one private local file for debugging errors from Jev MCP, Hindsight MCP, and NDA RAG MCP. An error must identify the NDA Harness plugin version that observed it so reports remain useful after upgrades. The existing usage journal serves usage reporting and can record memory outcomes, but it does not provide a common diagnostic history for all three services.

## Detailed spec

### File and event format

Append one UTF-8 JSON object per line to `~/.nda-harness/logs/mcp-errors.jsonl`. Create the file lazily on the first recordable failure. Keep the log outside the checkout and use the harness's existing private-state path conventions. Create the log directory with owner-only access and the file with owner read/write access where the platform supports POSIX permissions. Reject unsafe destinations such as symlinks or non-regular files. Use append-safe writes so concurrent clients preserve separate complete records.

Each record contains:

| Field | Meaning |
| --- | --- |
| `timestamp` | UTC timestamp when the harness observed or received the failure |
| `client` | `codex`, `cursor`, or `claude` |
| `plugin_version` | Version from the running package's `nda-plugin.json`. Use `unknown` only when package metadata is missing or invalid, and preserve the original failure. |
| `server` | `nda-harness-jev`, `nda-harness-hindsight`, or `nda-harness-nda-rag` |
| `operation` | Allowlisted operation such as `select_skills`, `recall`, `search_docs`, `get_page`, or `startup` |
| `error_code` | Allowlisted diagnostic such as `timeout`, `transport_error`, `authentication_required`, `invalid_response`, or `unknown_error` |

Read the version per running package, independently of the project version, Git branch, or remote MCP server version. Entries from two installed plugin versions can coexist in one file. Store only the fields above. Never write raw exceptions or MCP payloads, OAuth data, request or response bodies, prompts, memory, retrieved documents, private URLs, or machine paths.

### Failure sources

- **Jev MCP** records failures at the local server boundary when it returns a terminal error or blocked diagnostic. Normal uncertainty, local-agent classification, and successful empty results are ordinary outcomes. If the client cannot reach Jev, it can report that observed failure through the same recorder when available.
- **Hindsight MCP** records failed calls at the harness workflow boundary and failures from supported client-native diagnostics that reach the harness. Reuse the existing native diagnostic classification for authentication. An unavailable tool or an unauthorized response alone does not prove a failed OAuth refresh.
- **NDA RAG MCP** records failed `search_docs` and `get_page` calls at the harness workflow boundary, plus failures from supported client-native diagnostics that reach the harness. Empty search results are ordinary outcomes.

Use a shared internal append function. Provide a packaged recorder entry point that accepts only the server, operation, and normalized failure code for failures observed by the agent or supplied by supported native diagnostic workflows. The runtime supplies the timestamp, client, and package version. Record each observed failure at its owning boundary to avoid logging the same Jev failure in both the server and its caller.

Client-owned events can only be captured when the host exposes them to the harness. Startup and prompt hooks do not currently subscribe to MCP lifecycle events. Document which signals each client exposes and the recorder fallback for failures the agent can observe. Keep remote MCP connections and OAuth under native client control. Do not add polling, a proxy, or log scraping. Do not add MCP calls to the Git test gate.

### Failure handling and rollout

If the log cannot be opened or appended, preserve the original MCP result and existing recovery behavior. Do not retry the MCP call or create a second log. The recorder reports a bounded local-write failure to its direct caller without echoing inputs. Document the path, fields, per-client capture limits, and manual cleanup in plugin operations. The first version uses one file with manual cleanup.

## Acceptance criteria and planned tests

| ID | Acceptance criterion | Verification |
| --- | --- | --- |
| AC-01 | Failures observed through each supported boundary appear in one local file with server, operation, timestamp, client, and plugin version. | Simulate one failure per MCP. Verify all three records and each exact field. |
| AC-02 | The installed package supplies the version, and older records keep their original version after an upgrade. | Append using two package fixtures with different versions. Verify both records. Exercise missing or invalid metadata separately. |
| AC-03 | Only normalized diagnostic fields are persisted. Ordinary outcomes create no record. | Use secret-bearing fixtures, unknown inputs, an empty RAG result, and a Jev uncertain result. Verify allowlisting, absence of secret text, and no records for ordinary outcomes. |
| AC-04 | Local writes stay private and preserve valid records under concurrent use. | Verify lazy creation, permissions, symlink rejection, and complete parseable lines after concurrent appends. |
| AC-05 | Logging failure preserves the original result. Native diagnostic coverage is explicit. | Simulate permission and I/O errors, compare MCP results with logging enabled and disabled, and test supported and unavailable native diagnostic fixtures. |

## Review handoff

The implementation gate requires the reviewed spec to be merged and verified against the local spec revision.
