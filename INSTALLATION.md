# Install the phase-0 NDA Harness plugin

Targets: **Codex Desktop, Cursor IDE, and Claude Code Desktop on Apple Silicon
macOS**. Install/sign in to the client separately. Python 3.11+
(`python3`) and Git must be on the GUI client's PATH. No pip, virtual environment,
global harness CLI, Python installer or shell startup changes are required.

This is development installation, not a published release. The
[implementation report](docs/compatibility/harness-plugin-implementation.md)
separates automated checks from native-client observations still pending.

## Install the stored Codex and Cursor packages

The checkout stores built packages at `packages/nda-harness-codex` and
`packages/nda-harness-cursor`. Install those directories. They include the
NDA Hindsight endpoint listed below. The Claude Code package is not stored here; create it when
cutting a release, into a directory outside the repository:

```sh
PYTHONPATH=scripts python3 -m nda_harness.plugin_build --client claude --output /tmp/nda-harness-claude
```

After engine or skill changes, refresh only the stored Codex and Cursor packages:

```sh
PYTHONPATH=scripts python3 -m nda_harness.plugin_build --publish-committed
```

That command never writes `packages/nda-harness-claude`. A one-off package for
any client still uses `--client` and a **new** `--output` directory; existing
files are preserved. Packages
include the same canonical engine/assets, complete specialist and pinned Superpowers
skills, licenses and provenance. Builds fetch nothing. A release hash manifest
covers packaged files. Runtime needs neither the source checkout nor a global CLI.

NDA Hindsight is the packaged memory provider. A package built without an override
uses this host:

- MCP: `https://hindsight-api.pila.vn/mcp/`
- OAuth: `https://hindsight-api.pila.vn`
- REST: `https://hindsight-api.pila.vn`

The client connects to the MCP URL and discovers OAuth on that host. No token or
auth header is packaged. `--hindsight-mcp-url` still overrides the MCP URL for a
one-off package. It must be HTTPS with exact `/mcp/`, no userinfo/query/fragment.

Local development Hindsight only:

```sh
PYTHONPATH=scripts python3 -m nda_harness.plugin_build --client cursor \
  --output /tmp/nda-harness-cursor-local \
  --hindsight-mcp-url http://127.0.0.1:8891/mcp/ --local-test
```

This exception permits HTTP loopback only. No provider settings, tokens or static
auth headers enter the package.

## Build a ZIP for Codex Upload plugin archive

Run from the repository root, choosing a new semantic version for each release:

```sh
PYTHONPATH=scripts python3 -m nda_harness.plugin_build --client codex \
  --archive --version 0.0.3 --output dist/nda-harness-codex-0.0.3.zip
```

Select the ZIP in **Upload plugin archive**. The command preserves existing
output files; move an earlier ZIP aside before rebuilding to the same path.
Use `--version` with directory builds too when releasing another client.

This builds fresh sources rather than zipping a potentially edited package.
It includes hidden manifest directories, all runtime dependencies and licenses,
and explicit Unix file types and executable permissions. ZIP timestamps and
entry ordering are fixed. The original Superpowers source stays in its pinned
tarball alongside its license, provenance, and startup handlers, so its own
plugin manifests do not become additional plugin roots. Active skills remain
under `skills/`. `release.json` is generated after packaging and checked against
every archived file; never edit the manifest or delete dependencies afterward.
The Codex ZIP excludes `.agents/plugins/marketplace.json`: hosted upload expects
one plugin, while the directory build keeps the catalog for local installation.
The manifest explicitly supplies `interface.category`, `capabilities`, and
`defaultPrompt` for the hosted importer.

The previously rejected ZIP omitted 241 hashed vendor files (including the
tomlkit wheel), changed the manifest without updating its hash, and omitted Unix
file type bits. Extracting that ZIP fails the harness integrity check. The builder
also now emits the required Codex author and long description itself.

The hosted upload dialog hides server rejection details behind “Couldn't add
plugin. Try again.” On 2026-10-19, browser Network inspection of
`POST /backend-api/public/plugins/workspace` exposed successive HTTP 400 errors:

- Missing category: `interface.category` must not be empty when provided.
- Missing capabilities: `interface.capabilities` must be a list of strings.
- Included marketplace catalog: `Expected a single plugin archive`.

An inert probe with explicit listing metadata uploaded successfully. The full
0.0.2 archive then uploaded successfully after excluding the marketplace catalog;
its cloud plugin page showed all 26 skills and both MCP servers. The tested
archive is `dist/nda-harness-codex.zip`. This verifies hosted import, not installation
or hook execution. For future generic errors, inspect the failing request's status
and Response body without sharing request headers, cookies, tokens, or signed URLs.
This archive retains the full Desktop hooks and remote MCP configuration.
Public-directory **Skills only** submissions have separate restrictions; see
[OpenAI's submission rules](https://developers.openai.com/plugins/deploy/submission-errors).
Use the local marketplace installation below if hosted upload is unavailable.

## Load the plugin

**Codex Desktop:** use `packages/nda-harness-codex`. Its
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

**Cursor IDE:** for development, copy `packages/nda-harness-cursor` to
`~/.cursor/plugins/local/nda-harness`, then **Developer: Reload Window**.
Use a real directory, not an external symlink. Preserve existing plugins; reconcile
an existing target instead of replacing it blindly. Organization policy may disable
local plugin imports. Confirm discovery under Customize → Plugins. Native paths:
`.cursor-plugin/plugin.json`, `mcp.json`, `hooks/hooks.json`, and the always-applied
`rules/nda-harness.mdc`.

**Claude Code Desktop:** the generated package is both the plugin and a local
marketplace. `.claude-plugin/plugin.json` names the plugin and does not repeat
`hooks` or `mcpServers`, because Claude Code also loads `hooks/hooks.json` and
`.mcp.json`. `.claude-plugin/marketplace.json` lists source `.`. Hooks are
`SessionStart`, `UserPromptSubmit`, and `PreCompact`, and commands expand
`${CLAUDE_PLUGIN_ROOT}`. There is no always-applied rule file and no plugin-root
`CLAUDE.md`; those events carry the readiness instructions.

Register it with the Claude Code plugin store shared by the Desktop Code tab:

```sh
claude plugin marketplace add /absolute/release/nda-harness-claude
claude plugin install nda-harness@nda-harness-local
```

In a local Desktop Code session, open the same plugins with `+` → Plugins.
Trust reviewed hooks in the client. Package installation does not prove Desktop
hook execution. Hindsight authentication is the native MCP action in `/mcp` or
the Desktop plugin/MCP row. Record the label that client shows. Do not invent an
Authenticate button. Installation does not open a login browser.

## First trusted session and project setup

The plugin is available in every project with no client or scope menu. Trusted
Codex or Claude Code SessionStart, or Cursor sessionStart, attempts bootstrap
automatically. It installs checksum-pinned RTK if absent, exposes bundled Superpowers and registers
Context7 natively. It does not open a login browser. Unrecognized existing RTK
is preserved and reported as a failed prerequisite. Concurrent bootstrap is locked;
states are awaiting-trust, installing, ready and failed.

Cursor startup is asynchronous. Its always-applied rule and explicit context
skills check readiness before dependent work. Claude Code waits for SessionStart
before the first response and repeats that context on UserPromptSubmit. Its
PreCompact hook writes the local checkpoint without blocking compaction; Claude
Code does not show that event's `systemMessage`, so the following compact
SessionStart, UserPromptSubmit, and the context-checkpoint skill carry the
reminder. If hooks are delayed, untrusted,
missing or failed, use **nda-setup** for recovery. Never infer ready from install.

The agent checks `.nda-harness/profile.json` at the project directory and asks for a
non-watch test command in chat. Explicit **Skip** stores `true`, passing without
tests. No answer means pending. Hooks exchange JSON, not terminal wizard input.
A folder that is not a Git checkout, and a repository with no remote, requires a
shared project name. Distinct remotes require explicit selection. Git commit
hooks are installed only for a repository. Existing project configuration is reused.

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

A project uses one memory system, stored as `memory.system`. NDA Hindsight is the
only system a package includes today. When a later package offers more than
one, ask which system and pass `--memory-system`. Setup selects the only packaged
system automatically.

## Optional NDA Hindsight

The MCP server identifier is **`nda-harness-hindsight`**; NDA Hindsight is its
human-readable label. Version 0.0.2 incorrectly used the label as the identifier.
Codex rejected its spaces before connecting, even after OAuth completed. Version
0.0.3 fixes the identifier and rejects invalid server names during package builds.
Update the plugin, then authenticate the new `nda-harness-hindsight` entry in
native plugin details if requested. The client may require authorization again
because the MCP identifier changed; never copy or edit stored credentials.

Use the NDA Hindsight entry's native **Authenticate/Authorize** action to opt in.
Setup never starts login. Each client signs in separately and connects directly to
`/mcp/`; the client owns discovery, PKCE, callback, credentials, renewal and logout.
Never provide tokens or provider settings to the harness. No auth proxy exists.

After authentication the agent uses hindsight-memory automatically. Codex, Cursor,
and Claude Code on the same account use the project's configured bank ID. Equivalent SSH/HTTPS
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

### Authentication reports and manual recovery

Missing Hindsight tools mean the connection is unavailable in this session;
authentication remains unverified until the client's native diagnostics establish
more. Saved OAuth credentials or a hidden Authenticate button are not connection
proof. Devices authenticate independently. A login created before the server
started supplying expiry metadata may need one refresh or reauthentication.

The packaged **memory-status** operation interprets already available native JSON.
It does not fetch diagnostics, access credentials, run memory calls or start
login. Existing hooks do not subscribe to MCP lifecycle events. For example,
given an actual Codex startup notification:

```sh
rtk proxy /absolute/package/path/bin/nda-plugin memory-status --client codex <<'JSON'
{"method":"mcpServer/startupStatus/updated","params":{"name":"nda-harness-hindsight","status":"failed","failureReason":"reauthenticationRequired"}}
JSON
```

This reports `awaiting_authentication`. Only Codex interprets that event. A native
Codex inventory entry needs both OAuth status and nonempty discovered tools to
report connected. Claude accepts matching native MCP status snapshots such as
`{"name":"nda-harness-hindsight","status":"needs-auth"}`; pending remains
unresolved and failed means unavailable. Cursor's equivalent is a matching
catalog entry whose `namespaceStatus` is `needsAuth`:

```sh
rtk proxy /absolute/package/path/bin/nda-plugin memory-status --client cursor <<'JSON'
{"namespace":"plugin-nda-harness-nda-harness-hindsight","namespaceStatus":"needsAuth"}
JSON
```

The mcp.json key `nda-harness-hindsight` with `serverStatus` or `status`
`needsAuth` is the same verdict. `error` means unavailable, `loading` stays
pending, and `ready` or `connected` reports discovery only. These observations
do not test memory operations or future renewal. Codex and Claude do not
interpret `needsAuth`.

Without native JSON, run with empty stdin for a pending report; terminal stdin
returns immediately. Disabled packages report disabled. Reports do not change
core readiness. Invalid/non-object JSON or input over 1 MB returns a sanitized
pending report with exit 2; valid reports, including unavailable, return exit 0.
Use the helper path from the installed package; hosted Claude packages relocate
the launcher to `scripts/nda-plugin`.

Manual sign-in remains the user's action:

- **Codex:** use the native MCP sign-in control. If hidden, use the installed
  Codex executable with the invocation-local override below, then reconnect or
  restart the client. The name matches the plugin's stored server identity.
- **Cursor:** use the Hindsight authentication control in MCP settings. If Cursor
  Agent CLI is installed and the server is registered there, inspect
  `rtk proxy agent mcp list` and run `rtk proxy agent mcp login <identifier>` with
  its actual identifier. Do not assume credentials are shared across surfaces.
- **Claude Code:** inspect/authenticate through `/mcp`. Shell
  `rtk proxy claude mcp login <name>` is an alternative only when the installed
  version exposes it; verify the name in native inventory. SDK status APIs do not
  launch browser OAuth or supply a Desktop plugin SDK bridge.

```sh
rtk proxy codex \
  -c 'mcp_servers.nda-harness-hindsight.url="https://hindsight-api.pila.vn/mcp/"' \
  mcp login nda-harness-hindsight
```

No credential deletion or plugin uninstall is required. See the
[diagnostic compatibility evidence](docs/compatibility/hindsight-auth-recovery.md)
for source references and live-test limits.

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
