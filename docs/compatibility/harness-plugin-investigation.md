# Phase-0 plugin capability investigation

Checked on 2026-10-18. Targets: Codex Desktop and Cursor IDE.

Follow-up: [minimal plugin OAuth test](hindsight-oauth-plugin-test.md) now records
installed samples, successful native OAuth login, and 39-tool discovery in both
clients' native runtimes. The sections below preserve the earlier investigation;
their unexecuted checks describe that earlier point in time.

This report distinguishes documentation, live inspection of existing plugins,
and tests that remain unexecuted. No NDA Harness sample plugin was installed;
no OAuth grant, dependency installation, or project-hook change was performed.

## Results

| Capability | Codex Desktop | Cursor IDE |
| --- | --- | --- |
| Package skills, hooks, and remote MCP | Documented; NDA package untested | Documented; existing plugin components observed in UI |
| Automatic dependency setup | Candidate: first trusted `SessionStart`; execution untested | Candidate: `sessionStart`; execution untested and event does not wait for completion |
| Silent install-time script | Not established; hook trust is required | Not established by the documented manifest/events |
| MCP row and OAuth action on plugin detail | Exact UI unverified | Observed: MCP row, Needs authentication, Authenticate button |
| Direct Hindsight OAuth | Documented MCP capability; server integration untested | Documented MCP capability; server integration untested |
| Ask for project test command from hook | Use agent conversation after hook detection; no terminal prompt assumed | Same; startup event is not a blocking configuration wizard |

## Live observations

Cursor's About dialog reported **3.25.9 (Universal)**, build date Oct 16, 2026.
Read-only navigation used Cursor Settings → Open Customize → Plugins.

- Existing Supabase plugin **0.1.4**: detail page displayed `MCPs 1`, a `supabase`
  row, `Needs authentication`, and an **Authenticate** button. The button was not
  clicked. This confirms a host-provided authentication action on a plugin detail
  page, not a successful Hindsight login or control over the button's wording.
- Existing Superpowers plugin **6.1.1**: detail page displayed `Skills 14` and
  `Hooks 1`, with `sessionstart` / `Hook: sessionStart`. This confirms discovery
  and presentation, not hook execution or compatibility with our pinned revision.
- Codex Desktop UI inspection was denied by the computer-use tool with
  `Computer Use is not allowed to use the app 'com.openai.codex' for safety reasons.`
  No alternative UI access was attempted. Codex findings below are documentation
  evidence, not live installation evidence.

## Documentation findings

Codex supports local desktop plugin hooks and bundled MCP configuration. Hooks
require user trust; installing a plugin does not grant it. Its npm plugin download
path does not run lifecycle scripts. Use a trusted session hook to attempt the
bootstrap, not an assumed installation callback. [Official packaging documentation](https://developers.openai.com/plugins/build/plugins).

Codex command hooks receive JSON on stdin. Session hooks can supply context to
the agent; do not use that input channel as an interactive terminal. A startup
hook can run before an MCP connection is ready. [Codex hooks](https://learn.chatgpt.com/docs/hooks).

Cursor's client manifest supports skills, rules, hooks, and bundled MCP. Use
`.cursor-plugin/plugin.json` for its full component set, `hooks/hooks.json`, and
`mcp.json`. It expands `CURSOR_PLUGIN_ROOT` for relevant MCP paths; the portable
`PLUGIN_ROOT` variable is not interchangeable. [Cursor plugin reference](https://cursor.com/docs/reference/plugins).

Cursor `sessionStart` supplies context but does not wait or enforce a blocking
response. `workspaceOpen` detects workspace changes. Its command hooks exchange
JSON, so configuration questions belong in the agent conversation. Treat these
events as detection/bootstrap triggers, not proof that setup has finished.
[Cursor hooks](https://cursor.com/docs/hooks).

Both clients support remote MCP OAuth. Cursor documents desktop callback
`http://localhost:8787/callback`; Hindsight must interoperate with the callback
and registration used by the real client. The harness must not introduce its own
callback or identity-provider configuration. [Cursor MCP](https://cursor.com/docs/mcp),
[OpenAI plugin OAuth](https://developers.openai.com/plugins/build/auth).

## Spec implications

1. Define automatic setup as an idempotent bootstrap at the first eligible
   trusted session. Report awaiting-trust, installing, ready, and failed states.
   Do not require a separate setup command for the normal path, but do not claim
   tools are installed merely because the package is installed.
2. Hooks inspect `.nda-harness/` and return a setup-needed message. The agent
   asks for the test command or explicit Skip in chat, then writes configuration
   and activates the Git check. No answer means pending, never implicit `true`.
3. Use a Git pre-commit hook for commit protection. Cursor's nonblocking startup
   event cannot itself enforce the tests or certify Git hook activation.
4. Owner accepted the host-native **Authenticate** wording on 2026-10-18. The spec
   accepts native authentication labels, including **Authenticate** and **Authorize**,
   while keeping the Hindsight row and explicit opt-in. No custom button label is
   required. Codex's detail-page presentation remains unverified.
5. Declare Hindsight through native bundled MCP configuration, with no fixed
   Authorization header. Validate optional/deferred authentication so installation
   does not force a login. There is no demonstrated common custom UI-row schema.

## Remaining validation

- Install a harmless sample package in each target app and record skill/hook/MCP
  discovery, trust behavior, actual startup execution, and repeat-session behavior.
  Existing-plugin UI observations do not substitute for this test.
- Exercise bootstrap with tools missing, already installed, and installation
  failing; verify no duplicate hooks or settings, including concurrent sessions.
- Exercise agent-driven project configuration and composed Git pre-commit checks
  in a disposable repository, including explicit Skip and failing existing hooks.
- Supply the actual internal HTTPS Hindsight `/mcp/` URL. Run login, cancel,
  renewal, app restart, disconnect, and optional-auth installation tests against
  the deployed revision. The spec still leaves that URL unset.
- Resolve Codex live UI access before claiming its detail-page acceptance test.

No production compatibility is claimed. No engine implementation or runtime
test suite changed as part of this investigation.
