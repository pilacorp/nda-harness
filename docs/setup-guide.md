# NDA Harness setup guide

Follow these steps to prepare your project, connect optional Hindsight memory,
and enable specialist skill selection. Repeat project setup in each clone and
Hindsight authentication in each client you use.

## Before you start

- Use Codex Desktop, Cursor IDE, or Claude Code / the Desktop Code tab on Apple
  Silicon macOS. Python 3.9+ and Git must be available on the client's PATH.
- Have access to the private `pilacorp/nda-harness` repository. Cursor private
  team marketplaces require Teams or Enterprise and an administrator's setup.
- Prepare a non-watch unit test command for your project, such as
  `npm run test:unit`, or explicitly choose **Skip**.
- Have a personal OpenRouter key available for skill selection. Hindsight sign-in
  is separate; its server-side OpenRouter key is managed by the server owner.

## 1. Set up NDA Harness

1. Follow the marketplace installation instructions for your client:
   [Codex](../INSTALLATION.md#codex),
   [Cursor](../INSTALLATION.md#cursor-ide), or
   [Claude Code](../INSTALLATION.md#claude-code-and-the-desktop-code-tab).
   These instructions track `main`.
   If you already have an uploaded or local copy, follow the
   [migration steps](plugin-operations.md#one-time-migration-from-an-upload-or-local-plugin)
   to avoid duplicate hooks and MCP servers.
2. Open your project in a new client session and trust the reviewed plugin hooks
   when prompted. Ask the agent:

   > Use nda-setup to set up NDA Harness for this project.

   Startup attempts bootstrap automatically. It installs pinned RTK if absent,
   exposes bundled Superpowers, and registers Context7. `nda-setup` also recovers
   incomplete startup; installation alone does not establish readiness.
3. Answer the test-command question in chat. Supply the exact command to run
   from the repository root, or explicitly answer **Skip** to configure a passing
   `true` command with no tests. If the project has no Git remote, provide a stable
   shared project name when asked. If it has distinct remotes, choose which one
   identifies the project.
4. Review the resulting project files. Commit `.nda-harness/config.json` and
   the `.gitignore` entries for `.nda-harness/profile.json` and
   `.nda-harness/tasks/`. Keep the personal profile and task records local and
   ignored. Each Git clone needs its own local hook activation, even when the
   config is already committed.
5. Ask the agent:

   > Run nda-verify and report core readiness, native hook status, and Context7
   > connection status. Report Hindsight separately.

   Core checks should pass. Independently confirm trusted hook execution and
   Context7 tool discovery in the client. Run your configured test command too:
   `nda-verify` does not run it. The Git pre-commit hook composes existing checks
   with that command; either failure blocks a commit. With **Skip**, only the
   configured test step is bypassed.

A pending native check is not completed onboarding. A helper exit code of `3`
means native checks remain pending; `2` indicates a configuration, prerequisite,
integrity, or ownership problem. Use `nda-setup` to recover and verify again.
See [project setup details](plugin-operations.md#first-trusted-session-and-project-setup).

## 2. Authenticate with Hindsight

Hindsight adds personal project memory and is optional. Core work can continue
while memory is disconnected. Setup never opens its login browser automatically.

1. Open your client's native MCP controls and find the packaged
   `nda-harness-hindsight` server, displayed as **NDA Hindsight** where supported:

   | Client | Where to sign in |
   | --- | --- |
   | Codex | Plugin details or native MCP controls for NDA Hindsight. |
   | Cursor | MCP settings and the Hindsight authentication control. |
   | Claude Code / Desktop Code tab | `/mcp` or the native plugin/MCP row. |

2. Use the native sign-in action, such as **Authenticate** or **Authorize**,
   and complete the browser flow. Labels vary by client version. The packaged
   endpoint is `https://hindsight-api.pila.vn/mcp/`; the client manages OAuth
   credentials and renewal. Do not paste tokens into chat or project files.
3. Return to the client and reconnect or start a new session if needed. Ask the
   agent to inspect native authenticated MCP status and discovered Hindsight
   tools. Verify through diagnostics without creating a bank or reading/writing
   memory just to test the connection. If diagnostics are unavailable, record
   verification as pending.

After authentication, the `hindsight-memory` workflow uses the project's configured
bank. Equivalent clones and clients signed into the same account share that bank;
the default environment label is `dev`.

If tools are missing, authentication is still unverified. Use the native sign-in
action again when diagnostics report authentication is required. For a hidden
Codex sign-in control or other recovery paths, follow
[manual authentication recovery](plugin-operations.md#authentication-reports-and-manual-recovery).
Do not copy credentials between clients or delete credential files to retry.

## 3. Set up the skill selection flow

The plugin uses Jev (`typesafe/jev-1.14`) through OpenRouter to choose optional
specialists. Your personal OpenRouter key stays in the macOS Keychain. It is
separate from Hindsight authentication and the server's OpenRouter key.

1. In the project chat, run:

   ```text
   /skill-selection
   ```

   That command opens macOS Terminal in the project directory and starts key
   setup. Leave the Terminal window focused. The chat cannot show the hidden
   prompt. The global `nda-harness` command does not set up skill selection; it
   only runs project `setup` and `verify`.
2. Enter your personal OpenRouter key at the hidden Terminal prompt. Do not put
   it in chat, a command argument, or a project file. Success prints:

   ```text
   OpenRouter key saved.
   ```

   Running `/skill-selection` again asks before replacing a saved key. Answering
   no keeps the saved key, prints `The saved OpenRouter key was kept.`, and
   finishes setup.
3. Return to the chat and ask the agent to run `selection-verify`. A successful
   offline check reports `OpenRouter key is present.` This checks local setup,
   not API authorization or account credit. For one synthetic paid API check,
   ask for `selection-verify --live`. Success starts with `Live check passed.`
   and includes the model name.
4. Give the agent a concrete assignment with a clear deliverable. The agent runs
   `select-skills` with the project, session, and request file, then
   `load-selected-skills` with the same task JSON. It loads only the returned
   specialist bodies. You do not need to run these agent commands yourself.

Selection sends bounded task text and catalog metadata to OpenRouter. The current
specialists are Diagram Design, UI/UX Pro Max, and Vietnamese official wording.
An empty selection is valid. When a score is strictly between 0.20 and 0.80, the agent
asks whether to load that skill and stores the answer in the local Jev cache.
Mandatory workflow skills remain active, and selection does not approve
implementation. See [skill selection details](skill-selection.md).

If Terminal prints `A local terminal is required.`, run `/skill-selection` again
and use the Terminal window it opens. For `authorization_failed`, run
`/skill-selection` again and confirm replacement of the saved key. For
`needs_context` or `blocked`, follow the reported diagnostic and next action
before loading specialist skills. On Codex, Cursor, and Claude, run skill
selection outside the sandbox so it can use the shared macOS Keychain key. Diagnostic
`sandbox_rerun` means that command ran in the sandbox: rerun it outside the sandbox
and continue the assignment. Do not create a new OpenRouter key.

## Setup checklist

- NDA Harness is enabled once in the client, its hooks are trusted, and core
  project verification passes.
- The project profile is committed, task records are ignored, the configured
  test command passes (or Skip was explicit), and native hook/Context7 checks
  have been observed.
- Hindsight has authenticated native tool discovery, or is explicitly recorded
  as optional and disconnected/pending.
- The personal OpenRouter key passes offline verification, and the agent uses
  the select/load flow for new assignments. Live API verification is optional.
