# Minimal Hindsight plugin OAuth test

Date: 2026-10-18. Hindsight source: `nda/10-supabase-tenant` at `14be9a293`.
Endpoint: `http://127.0.0.1:8891/mcp/` (local loopback test only).

## Result

**Native OAuth login and authenticated MCP tool discovery passed in both clients.**

| Check | Cursor IDE | Codex desktop-bundled runtime |
| --- | --- | --- |
| Version | 3.25.9 Universal | 0.163.0-alpha.10.2 |
| Minimal local plugin discovered | Pass, Customize → Plugins | Pass, native plugin installer and resolved MCP inventory |
| Native browser OAuth | Pass, plugin detail → Authenticate | Pass, bundled `codex mcp login hindsight` |
| Authenticated MCP discovery | Pass, 39 tools enabled | Pass, 39 tools through native app-server |
| Required tools | UI lists `recall`, `retain`, `list_banks` | Native discovery confirms all three |
| Reconnect with stored authorization | Pass, MCP configuration Reload remains Connected | Pass, a fresh app-server process discovers tools using client-managed credentials |
| Codex Desktop detail-page button | Not applicable | Unverified: computer-use access to Codex Desktop is restricted |

This validates the native OAuth/MCP integration, not every desktop UI, token-expiry,
memory-operation, or production deployment requirement.

Committed proof:

- [Codex native discovery result](evidence/hindsight-oauth-2026-10-18/codex-discovery.json), captured directly from the read-only runtime probe.
- [Cursor plugin detail excerpt](evidence/hindsight-oauth-2026-10-18/cursor-discovery.txt), captured from the native UI with unrelated workspace content omitted.
- [Codex browser authentication completion](evidence/hindsight-oauth-2026-10-18/codex-oauth-complete.png), showing the completed native callback without credentials or callback query parameters.

## Packages and installation

Sources: [minimal packages](../../experiments/hindsight-oauth/README.md).
Each contributes one MCP connection and contains no skills, executable hooks,
static headers, secrets, or identity-provider configuration. No forwarder is used.

- Cursor copy: `~/.cursor/plugins/local/nda-hindsight-oauth-test/`.
- Codex local marketplace: `nda-oauth-local-test`, rooted at
  `experiments/hindsight-oauth/`, with its own `.agents/plugins/marketplace.json`.
- Codex plugin: `nda-hindsight-oauth-test@nda-oauth-local-test`, installed by the
  native CLI into the user's plugin cache. No existing marketplace was replaced.
- Dedicated empty test account: `oauth-plugin-test@local.test`. Its password stays
  in the Git-ignored, mode-0600 Hindsight deployment environment file, alongside
  the other local test configuration. It is not packaged in either plugin.

The shell's npm-installed Codex launcher was broken. Testing instead used the
working runtime already bundled with the installed desktop app at
`/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex`.
This is a native runtime test; it is not evidence that the Desktop button was clicked.

## Observed flows

Cursor discovered the local package after Developer: Reload Window. Its detail
page showed Hindsight needing authentication. Authenticate opened Hindsight's
login page with DCR, S256 PKCE, a resource parameter, and Cursor's callback. After
sign-in, the native plugin detail page reported **39 tools enabled**. Configure
Hindsight reported **Local / Connected** and listed the required tools. Reload
preserved the connected state without another login.

Browser automatic approval review rejected observation of Cursor's final
`localhost:8787` callback, treating the local origin as unestablished. That page
was not inspected through another route. Login had completed; the unaffected
native Cursor UI independently confirmed the authenticated connection and tools.
The callback itself is documented by [Cursor MCP](https://cursor.com/docs/mcp).

Codex's native plugin installer accepted the package. Its MCP inventory resolved
the plugin's server as `hindsight` with no static headers. Native login opened
Hindsight, and the browser completed the callback on a loopback port verified as
owned by the Codex process. The CLI reported successful login and `auth_status:
o_auth`. A separate app-server process then initialized and discovered Hindsight
tools using the client's stored authorization; no tokens were extracted.

The reproducible [Codex probe](../../experiments/hindsight-oauth/probe_codex.py)
uses `initialize` and `mcpServerStatus/list` from the installed runtime's generated
protocol schema. It neither starts an agent thread nor invokes a model. Output:

```json
{
  "server": "hindsight",
  "auth_status": "oAuth",
  "tool_count": 39,
  "required_tools_present": ["list_banks", "recall", "retain"],
  "passed": true
}
```

## What this means for the spec

- Keep direct client-to-Hindsight OAuth and native token ownership. The minimal
  experiment needs no Supabase settings or client-side forwarder.
- Cursor's requested detail-page row and accepted Authenticate label are now
  demonstrated with our own package, not just another installed plugin.
- Keep Codex Desktop's exact detail-page presentation pending even though its
  bundled native OAuth runtime passed.
- Keep production HTTPS, actual token expiry/automatic renewal, logout/revocation,
  and read/write memory operations as separate tests. No memory content was read
  or written in this experiment, and `list_banks` was discovered rather than invoked.
- The Codex test marketplace uses `ON_INSTALL` auth policy solely for this
  connection test. This does not establish the full plugin's optional/deferred
  authentication policy. No hooks or automatic dependency setup were tested.

Both samples remain installed for inspection; their native OAuth credentials
remain in the respective clients. They are test packages, not the harness release.
