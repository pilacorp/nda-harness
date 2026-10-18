# Local Hindsight OAuth test plugins

Two deliberately minimal packages: one Codex plugin and one Cursor plugin.
Each contributes only a remote `hindsight` MCP server pointing directly at
`http://127.0.0.1:8891/mcp/`. HTTP loopback is for this local test only; deployed
harness connections still require HTTPS.

No token, identity-provider configuration, static Authorization header, skills,
hooks, or forwarder is bundled. Use the client's native authentication action
with the local Hindsight test account. Credentials belong to the client and
must not be copied here.

Cursor: copy `cursor/` to `~/.cursor/plugins/local/nda-hindsight-oauth-test/`,
then reload the window and inspect Customize → Plugins and MCPs.

Codex: expose `codex/` through a local marketplace, install/enable the plugin,
and inspect its Hindsight connection. Desktop presentation and native OAuth
must be tested separately from a direct HTTP protocol smoke test.

The minimal OAuth check means the real client completes OAuth, initializes MCP,
and discovers tools without a pasted token or static header. Calling `list_banks`
and other memory operations is a separate follow-up. Record the client version,
exact package configuration, auth UI behavior, and any failure.

Executed results: [compatibility report](../../docs/compatibility/hindsight-oauth-plugin-test.md).

Codex test setup used its desktop-bundled binary:

```sh
rtk proxy /Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex plugin marketplace add /Users/user/Desktop/Projects/nda-harness/experiments/hindsight-oauth
rtk proxy /Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex plugin add nda-hindsight-oauth-test@nda-oauth-local-test
rtk proxy /Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex mcp login hindsight
rtk proxy python3 experiments/hindsight-oauth/probe_codex.py
```

The test marketplace's `ON_INSTALL` policy is not the full harness's optional-auth
policy. Both sample plugins remain installed so their native connections can be
inspected; uninstall them through the clients' normal plugin controls when done.
