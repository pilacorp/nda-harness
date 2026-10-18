# Install the phase-0 NDA Harness plugin

Targets: **Codex Desktop and Cursor IDE on Apple Silicon macOS**. Claude Code
Desktop is deferred. Install/sign in to the client separately. Python 3.11+
(`python3`) and Git must be on the GUI client's PATH. No pip, virtual environment,
global harness CLI, Python installer or shell startup changes are required.

This is development installation, not a published release. The
[implementation report](docs/compatibility/harness-plugin-implementation.md)
separates automated checks from native-client observations still pending.

## Build a complete package

From the approved nda-harness checkout:

```sh
PYTHONPATH=scripts python3 -m nda_harness.plugin_build --client codex --output /tmp/nda-harness-codex
PYTHONPATH=scripts python3 -m nda_harness.plugin_build --client cursor --output /tmp/nda-harness-cursor
```

Choose a **new** output directory each time; existing files are preserved. Packages
include the same canonical engine/assets, complete specialist and pinned Superpowers
skills, licenses and provenance. Builds fetch nothing. A release hash manifest
covers packaged files. Runtime needs neither the source checkout nor a global CLI.

For memory the maintainer supplies `HINDSIGHT_MCP_URL` during the build, or passes
`--hindsight-mcp-url https://<internal-host>/mcp/`. It must be HTTPS with exact
`/mcp/`, no userinfo/query/fragment. The production hostname is still unset. Without
it, core packages build normally and omit Hindsight; memory needs a configured build.

Local development Hindsight only:

```sh
PYTHONPATH=scripts python3 -m nda_harness.plugin_build --client cursor \
  --output /tmp/nda-harness-cursor-local \
  --hindsight-mcp-url http://127.0.0.1:8891/mcp/ --local-test
```

This exception permits HTTP loopback only. No provider settings, tokens or static
auth headers enter the package.

## Load the plugin

**Codex Desktop:** use the generated local marketplace directory. Its
`.agents/plugins/marketplace.json` declares AVAILABLE installation and **ON_USE**
authentication; installation does not require Hindsight login. The manifest is
`.codex-plugin/plugin.json`, MCP is `.mcp.json`, and hooks are `hooks/hooks.json`.
Trust reviewed hooks using native client controls; changed commands may require
trust again. Package installation does not prove Desktop hook execution.

The tested Desktop distribution exposes this native registration helper:

```sh
"/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex" plugin marketplace add /absolute/package/path --json
"/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex" plugin add nda-harness@nda-harness-local --json
```

The path depends on the distribution. Use the installed Desktop runtime; do not
assume parity with an unrelated CLI. Exact Desktop detail UI/trust checks remain
separate from runtime registration evidence.

**Cursor IDE:** for development, copy the complete generated package to
`~/.cursor/plugins/local/nda-harness`, then **Developer: Reload Window**.
Use a real directory, not an external symlink. Preserve existing plugins; reconcile
an existing target instead of replacing it blindly. Organization policy may disable
local plugin imports. Confirm discovery under Customize → Plugins. Native paths:
`.cursor-plugin/plugin.json`, `mcp.json`, `hooks/hooks.json`, and the always-applied
`rules/nda-harness.mdc`.

## First trusted session and project setup

The plugin is available in every project with no client or scope menu. Trusted
Codex SessionStart or Cursor sessionStart attempts bootstrap automatically. It
installs checksum-pinned RTK if absent, exposes bundled Superpowers and registers
Context7 natively. It does not open a login browser. Unrecognized existing RTK
is preserved and reported as a failed prerequisite. Concurrent bootstrap is locked;
states are awaiting-trust, installing, ready and failed.

Cursor startup is asynchronous. Its always-applied rule and explicit context
skills check readiness before dependent work. If hooks are delayed, untrusted,
missing or failed, use **nda-setup** for recovery. Never infer ready from install.

The agent checks `.nda-harness/profile.json` at the Git root and asks for a
non-watch test command in chat. Explicit **Skip** stores `true`, passing without
tests. No answer means pending. Hooks exchange JSON, not terminal wizard input.
No Git remote requires a shared project name; distinct remotes require explicit
selection. Existing project configuration is reused.

After answering, the plugin invokes its fixed-client packaged helper, for example:

```sh
/absolute/package/path/bin/nda-plugin setup --client codex \
  --project /absolute/project --test-command 'npm run test:unit'
```

Use `--skip-tests` only for explicit Skip. `--project-name example-app` identifies
a project without a remote. `--remote origin` selects an explicitly chosen remote.
Existing identity conflicts need reconciliation; never delete a profile to guess
a new bank. Helpers always require --client; plugin skills supply it automatically.

Commit `.nda-harness/profile.json` and sanitized `.nda-harness/tasks/` records.
Do not ignore this directory. No shared plugin assets, machine paths or credentials
belong there. Every clone activates its local composed Git pre-commit hook. Existing
checks run before configured tests, from the project root; either failure blocks
commit. A missing profile or removed runtime also blocks the installed check.

## Optional Hindsight

Use **Hindsight → Authenticate/Authorize** in native plugin details to opt in.
Setup never starts login. Each client signs in separately and connects directly to
`/mcp/`; the client owns discovery, PKCE, callback, credentials, renewal and logout.
Never provide tokens or provider settings to the harness. No auth proxy exists.

After authentication the agent uses hindsight-memory automatically. Both clients
on the same account use the project's configured bank ID. Equivalent SSH/HTTPS
clones share it. Default environment is dev; staging/prod are explicitly selected
labels within the same bank. Store credential-location references, never key values.

Use native authenticated MCP diagnostics for discovery without memory read/write
side effects. If unavailable, verification stays pending. Cancellation, revocation,
expiry or outage does not block core work. Use default client memory if available;
never fabricate saves or auto-sync fallback content into Hindsight later.

Reauthenticate using the native Hindsight action. Disconnect by disabling its MCP
connection in that client and using native logout/disconnect when available. If
client logout is unavailable and revocation is needed, revoke access in Hindsight.
Do not edit host credential files or affect the other client.

## Verification and recovery

Run **nda-verify**, or its client-bound helper:

```sh
/absolute/package/path/bin/nda-plugin verify --client codex --project /absolute/project
```

Verification is read-only: no tests, repairs, login, credential extraction or memory
reads/writes. It separates local core readiness, bootstrap, native hooks, Context7
and optional memory. Native checks remain pending until independently observed.
Exit `3` means pending client checks, not complete onboarding. Exit `2` indicates
invalid prerequisites/configuration/integrity or ownership conflict. Unit-check
exits `1` on failure. Context operations exit `2` when prerequisites are blocked.

Private receipts, locks and backups live under `~/.nda-harness/plugin-bootstrap/`
and `~/.nda-harness/plugin-projects/`. They are not committed or shared as evidence.
Setup rolls back owned writes on failure and recovers interrupted transactions
before another setup. If later edits conflict, preserve files/backups for owner
reconciliation. Never reset hooksPath or delete another manager to bypass conflict.
Multiple worktrees require Git worktree-local configuration before activation.

Use all five context skills across tasks, changes, compaction and handoff. Sanitized
repository task records, current revisions and live approval evidence establish
context; fingerprints cannot authenticate approvals or detect remote issue edits.

The [old CLI walkthrough](docs/compatibility/cli-installation-historical.md) is
historical evidence, not a plugin installation or migration path.
