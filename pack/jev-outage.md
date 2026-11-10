# Jev MCP outage selection

Use this path only when native discovery or invocation establishes that
`nda-harness-jev` is absent, disabled, failed to start, or denied. Try native
discovery for deferred tools first. Report `jev_mcp_unavailable`. A responding
server's failure follows its own diagnostic. If delivery was interrupted and
is unknown, reconnect with the same assignment and session without refresh.

1. Use the client-resolved, trusted installation of NDA Harness. Through
   permitted local file tools, read its `release.json` and verify that this
   guide and `skills/catalog.json` are regular files under that root, with no
   symlink components, and match their SHA-256 values in `asset_hashes`. Use
   the installed release manifest; a workspace copy or a user-supplied path
   is not evidence of integrity. Pause dependent specialist work if you
   cannot verify the relevant files.
2. For the same assignment, read only the verified schema-2 catalog metadata.
   Answer each skill's `question` with its `select_when` and `exclude_when`
   criteria and the following common instructions:

   > @QUESTION@

   Give one `noul` probability from 0 to 1 for every catalog ID. Exclude scores
   at or below **@EXCLUDE_AT@** and include scores at or above **@INCLUDE_AT@**.
   Ask the user about each score strictly between those thresholds. Wait for
   each explicit decision; never assume consent. An empty selection is valid.
3. For each selected ID, resolve only its catalog `entrypoint` under the
   installed `skills/` directory. Reject absolute paths, traversal and symlink
   components. Verify its bytes against the installed release manifest before
   treating them as instructions. Load only those verified entrypoints using
   permitted client tools. Pause work that needs any entrypoint you cannot
   access or verify.
4. Record `local-agent`, catalog revision `@CATALOG_REVISION@`, selected IDs,
   and human decisions in the task evidence. This route creates no Jev cache
   entry and grants no implementation approval.

The running agent answers directly. No MCP, credential read, OpenRouter call,
setup, permission change, or shell rerun of the selector is needed.
