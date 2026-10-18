> Historical development CLI guidance, superseded by the plugin specification and current INSTALLATION.md. Not the phase-0 plugin setup flow.

# How to install NDA Harness

This guide is for organization developers configuring an existing coding agent
with the team's workflow, specialist skills, Context7 and project test hooks.
Install the command once on your Mac, then run setup for each project you adopt.

The current implementation targets **Apple Silicon macOS**. It configures Codex
desktop/CLI, Cursor IDE/CLI and Claude Code CLI/Claude Desktop's **local Code tab**.
Intel macOS, Linux, Windows, remote sessions and Claude Chat/Cowork are outside
this phase. Full client compatibility validation is still pending; see the
[implementation and evidence guide](../../docs/compatibility/minimal-cli-phase.md).

## 1. Prepare your Mac and project

You need:

- Access to this private GitHub repository and your team's target repository.
- Python **3.11 or newer**, available as `python3`, and Git on PATH.
- At least one installed surface for every agent family you select. Install and
  sign in to the agent separately; setup does not install coding agents.
- Your project's approved, non-watch **unit-test command**, or choose to skip unit tests during project setup.
- Network access to GitHub for a missing RTK download and to
  `https://mcp.context7.com/mcp` for Context7.

Check the local prerequisites:

```sh
python3 --version
git --version
uname -m
```

Expect Python 3.11+, a Git version and `arm64`. Your selected CLI must also be
available on PATH: `codex`, Cursor's `agent`, or `claude`. A desktop-only
installation does not require its CLI sibling; desktop detection currently looks
in `/Applications`.

Ask your tech lead which harness revision and test command to use. Setup does
not install Python, use `sudo`, or change shell startup files. Its Python
dependency is bundled, so no pip installation or virtual environment is needed.

## 2. Install the command once

Clone the harness repository:

```sh
git clone https://github.com/pilacorp/nda-harness.git
cd nda-harness
```

Before installing, check out the branch, tag or commit approved by your tech lead.
It must contain `install.sh` and `bin/nda-harness`.

```sh
./install.sh
~/.local/bin/nda-harness --help
```

The installer places the command in `~/.local/bin/nda-harness` and its complete
bundle in `~/.local/share/nda-harness/`. You can remove the source clone afterward.

If `nda-harness` is not found in your terminal, use `~/.local/bin/nda-harness`
directly. To make the short command available in the current terminal:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

Persist that PATH entry through your normal shell configuration if desired.
For a different installation location, use `./install.sh --prefix /your/prefix`;
the command will be `/your/prefix/bin/nda-harness`.

Alternatively, keep the approved source clone and run `./bin/nda-harness setup`
from its root without installing the command.

## 3. Configure your project

Project scope is the usual choice for a shared team repository: it installs the
workflow pack and activates a local Git pre-commit test gate for this checkout.

Run setup from inside the project or one of its subfolders. It detects the Git
worktree root and offers **Use /detected/path** or **Choose another folder**.
Confirm the detected repository, or choose another folder and enter its absolute
root path. If the current folder is outside a Git repository, setup asks for the
path directly. The same behavior applies to `verify`.

You can also find the target repository root yourself:

```sh
git rev-parse --show-toplevel
```

**Target Git worktree root** means that printed top-level directory. It contains
the `.git` directory, or a `.git` file for a linked worktree. Supply the absolute
path, not a subfolder such as `src`, and not the harness source clone unless that
is the project you intend to configure.

Run guided setup from any directory:

```sh
nda-harness setup
```

| Prompt | What to select or enter |
| --- | --- |
| Agents | Use Up/Down to move, Space to check one or more of Codex, Cursor and Claude Code, then Enter to confirm |
| Scope | Use Up/Down to highlight Project or User, then Enter to confirm; choose Project for this walkthrough |
| Target Git worktree root | Confirm the detected path, or choose another folder and enter its absolute root, for example `/Users/yourname/Projects/tsa-simulator` |
| Non-watch unit-test command | Choose Enter a unit-test command and type the approved command, or Skip unit tests to automatically use `true` |
| Set up Hindsight memory? | Choose Enable for personal memory, or Skip to preserve any existing setup |
| Hindsight agents (when enabled) | Check one or more of the harness agents selected above |
| Hindsight multi-bank MCP URL | Root endpoint supplied by your team, such as `https://memory.example/mcp/`; do not append a bank ID |
| Personal Hindsight API key | Enter your personal user key; input is hidden |

Agents start unchecked; you must choose at least one. If the terminal cannot
display the keyboard menu, select from numbered choices instead: enter numbers
such as `1,3` for agents and one number for scope. Ctrl+C cancels before any
installation changes. Project paths and test commands remain text input.
The same menus appear for missing agent/scope options during `verify`; supplied
flags skip their corresponding menus. Redirected input requires complete flags.
An explicit `--project` skips repository detection and confirmation. A supplied
subfolder path is rejected; automatic discovery from a subfolder finds its root.

The test command runs from the target repository root during setup, verification
and pre-commit. Use a command that exits when finished. Run the chosen command
yourself first and resolve any project prerequisites it needs. Choosing **Skip
unit tests (use true)** stores `true` automatically; you do not type it. This
command always succeeds and runs no unit tests, so the harness test gate does not
check tests until you rerun setup with a real command. Existing pre-commit hooks
still run. Non-interactive setup still requires an explicit `--test-command`.

You can also supply all options explicitly. Replace both the path and test
command with your project's actual values:

```sh
nda-harness setup --agents claude --scope project \
  --project /absolute/path/to/project --test-command 'npm run test:unit'
```

With complete flags, the harness option menus are skipped; an interactive terminal
still offers optional Hindsight setup. Non-interactive setup skips Hindsight and
requires complete harness flags. Setup backs up changed
configuration, preserves unrelated entries and stops on ownership conflicts.
It does not grant client trust or create commits.

For Claude, successful application creates or updates:

```text
your-project/
  .nda-harness/       # Workflow, templates, skills, runtime and test profile
  .claude/skills/     # Complete specialist skills for Claude discovery
  CLAUDE.md          # Managed harness instruction block
  .mcp.json          # Context7 MCP registration
```

Codex uses `AGENTS.md`, `.agents/skills/` and `.codex/config.toml`. Cursor uses
`.cursor/rules/nda-harness.mdc`, `.cursor/skills/` and `.cursor/mcp.json`.
Dot-prefixed folders are hidden in Finder; press **Command+Shift+.** to show them.
Private backups, receipts and hook wrappers live under `~/.nda-harness/state/`.

Project setup appends `__pycache__/` and `*.py[cod]` to the repository's existing
`.gitignore` when those exact entries are missing. Existing rules and line endings
are preserved, changed files are backed up, and reruns do not duplicate entries.
Setup does not create a missing `.gitignore`, change it in user scope, or add an
ignore rule for the shared `.nda-harness/` pack. Commit the pack and the reviewed
`.gitignore` update as part of project adoption.

The Git gate runs the existing pre-commit hook first and the harness test command
second. A failure blocks the commit and preserves staging. If you use multiple
Git worktrees, ask the repository maintainer to arrange worktree-local Git
configuration before setup; the installer refuses unsafe shared hook activation.

Review project changes with your maintainer before committing adoption files.
Every developer must run setup for their own checkout, including after cloning a
repository that already contains `.nda-harness/`. Machine-local hook activation,
dependencies, credentials and trust approvals do not transfer through Git.

### Optional: configure user scope

Use user scope for personal registrations across projects:

```sh
nda-harness setup --agents claude --scope user
nda-harness verify --agents claude --scope user
```

The shared pack goes to `~/.nda-harness/pack/`. User scope accepts neither
`--project` nor `--test-command` and activates no Git hooks. A repository still
needs separate project adoption for its test gate and profile. Avoid registering
the same specialist skills in both user and project scope; setup rejects detected
user/project shadowing and asks for reconciliation.

## 4. Finish the client connections

### Optional Hindsight memory

Enable Hindsight only when your team has provided a working authenticated service,
your full multi-bank MCP URL, and a **personal user API key**. The organization's
admin key is not a memory-access key. Setup does not deploy Hindsight or provision
accounts. HTTPS is required except for a loopback development server.
Use the multi-bank root endpoint ending in `/mcp/` (also accepts `/mcp`), not
`/mcp/<bank>/`. Setup does not ask for or create a bank.

Setup registers **`nda-harness-hindsight`** in private user settings, even when
the harness scope is Project:

| Agent | Credential-bearing configuration |
| --- | --- |
| Codex CLI/desktop | `$CODEX_HOME/config.toml`, default `~/.codex/config.toml` |
| Cursor CLI/IDE | `~/.cursor/mcp.json` |
| Claude Code CLI/Desktop local Code tab | `~/.claude.json` |

These files contain your key in plaintext with owner-only permissions (`0600`).
They and private recovery backups must remain outside Git. Setup rejects a client
home inside a Git checkout and conflicting project/local server definitions.
The connection is available across your projects; replacing a managed URL/key
requires confirmation and affects all projects using that connection. Unmanaged
conflicts require reconciliation. Never paste your key into an issue or commit it.

Memory instructions follow the selected Project/User scope. They request relevant
recall before each response and useful retention **before the final reply**, since
the final reply ends the agent's turn. Before using memory or switching project/context,
the local agent lists existing banks, reviews their IDs/names/purposes and chooses
the appropriate one. It reuses a matching bank or creates a stable, descriptive bank
only when no appropriate bank exists, then passes `bank_id` explicitly on memory
calls. Bank selection is the agent's responsibility, not a setup question.
When creating a bank, the agent reads the installed `hindsight/README.md` and
chooses one of three bundled version-1 templates:

| Template | Purpose |
| --- | --- |
| `hindsight/templates/coding-agent.json` | Technical decisions, architecture, conventions, developer preferences and review patterns; default for coding |
| `hindsight/templates/multi-agent-orchestrator.json` | Decisions and rationale, ownership, agent coordination, hand-offs and escalation playbooks |
| `hindsight/templates/research.json` | Interests, durable knowledge, source reliability and traceable findings |

These files preserve the supplied bank settings, three mental models per template
and the orchestrator/research directives. The agent applies them through native
MCP tools to a newly created bank. Existing banks are reused without overwriting
their settings or models. Missing tools, conflicts or partially applied templates
are reported honestly; setup does not create banks or apply templates remotely.

MCP registration alone does not capture
conversations in the background. Memory does not replace approved specifications
or repository task records, and memory outages do not block normal work.

Restart the client and approve its memory tools through its usual MCP controls.
For **Cursor User scope**, paste the generated `cursor-user-rules.md` from the
installed pack into **Settings > Rules > User Rules**, preserving other rules.
This manual step is required for Cursor to load the instructions.

Automatic verification authenticates and discovers `list_banks`, `create_bank`
and `recall`/`retain` accepting `bank_id`, plus bank configuration, mental-model
and directive tools needed to apply templates (`update_bank` must accept
`config_updates`). Template files are covered by the installed asset hashes.
Verification does not list/create banks or read
or writing memories. Later `verify` uses the saved configuration without
asking for the key. Client loading and instruction execution remain pending until
confirmed in a fresh session. Skipping Hindsight on a later setup preserves it;
there are no Hindsight command-line flags.

For an earlier bank-specific installation, rerun interactive setup, enable Hindsight,
enter the root `/mcp/` URL and confirm replacing the managed connection. Existing
banks and their memories stay on the service; the agent can discover and reuse them.

Configuration follows [Hindsight's MCP documentation](https://github.com/vectorize-io/hindsight/blob/main/skills/hindsight-docs/references/developer/mcp-server.md),
researched using Context7, and each client's native HTTP MCP format.

### Context7

Context7 supplies public library documentation through Model Context Protocol
(MCP), the client's interface for connecting external tools.

Setup explicitly reports whether it added the harness Context7 MCP connection or
found it already configured. It uses the hosted endpoint
`https://mcp.context7.com/mcp` under the name **`nda-harness-context7`**; no local
Context7 server installation is needed. Matching existing harness entries are
reused, unrelated servers are preserved, and conflicting owned entries stop setup.

Restart the selected client, approve the connection through its MCP controls,
and authenticate if requested. New registrations print client-specific guidance:

| Client | Connection action |
| --- | --- |
| Claude Code CLI | Open `/mcp` in Claude Code and approve/connect `nda-harness-context7` |
| Claude Desktop | Open a **Local** session in the **Code** tab for the adopted repository and use its MCP/connector controls |
| Codex | Use its MCP settings; where supported, run `codex mcp login nda-harness-context7` |
| Cursor | Use its MCP settings; where supported, run `agent mcp login nda-harness-context7` |

Keep credentials in the client's private store. Do not put API keys in committed
MCP files, test commands or support messages. Confirm a public library resolution
and focused documentation retrieval inside each client you actually use. A
successful public server diagnostic does not prove client loading/authentication.

### RTK and Superpowers

RTK reduces output from supported shell commands. Superpowers supplies compatible
planning, testing and debugging skills through the client's plugin system.

Setup installs checksum-verified RTK 0.37.2 if RTK is absent. It also reuses
recorded compatible builds, including the observed Homebrew 0.40.0 build, when
both the binary checksum and version match. It does not replace an unrecognized
installation. Use the printed RTK executable path if it is not on the client PATH.

Install Superpowers through the client's supported plugin marketplace. For
Claude, the documented flow is `/plugin marketplace add obra/superpowers`, then
`/plugin install superpowers@superpowers-marketplace`; desktop uses its plugin
manager. Cursor uses `/add-plugin superpowers`; Codex uses its Plugins UI.
The reviewed source is `bb92a77741419a4ab5f06e711a283343f1ada0c3` (manifest 7.0.0).
If the client cannot identify or pin it, keep that check pending and consult the
maintainer. Setup does not install the plugin or edit upstream plugin hooks.

Start a fresh client session and confirm policy/template/skill discovery, RTK
usage and Superpowers activation. Python 3.11+ must also be visible to GUI-launched
clients and Git hooks. Native context lifecycle hooks are deferred; follow the
installed `.nda-harness/context-preparation.md` and its explicit helper commands.

For Cursor user scope, also paste the installed
`~/.nda-harness/pack/cursor-user-rules.md` into Cursor Settings > Rules > User Rules,
preserving existing rules.

## 5. Verify the installation

After connecting clients, run verification for the same agents, scope and project:

```sh
nda-harness verify --agents claude --scope project \
  --project /absolute/path/to/project
```

Verification runs automatically with complete flags. It checks installed assets,
registrations, RTK, public Context7 retrieval, CLI diagnostics and the configured
project test command. It never reinstalls dependencies, repairs registrations or
changes trust approvals. Do not supply `--test-command`; verify reads the profile.

The terminal shows only verification counts and the path to a private
`verification.json` report. Open that exact path to see failure details and pending
client steps. Reports contain sanitized check summaries, not raw transcripts,
credentials or test logs. To inspect a test failure, rerun the configured command
yourself from the target project root.

| Exit code | Meaning |
| --- | --- |
| `0` | All applicable checks completed |
| `1` | A verification, runtime or test check failed |
| `2` | Invalid options, unsupported prerequisites or a setup conflict |
| `3` | Configuration was applied, but required client/session checks remain pending |
| `130` | Interrupted |

**Exit `3` is not a complete onboarding success.** In this phase, session-only
checks remain pending even after you perform manual checks, because verify cannot
automatically establish them. Repeating setup does not clear them. Report actual
fresh-session observations to your maintainer; do not change receipts to force a
green result. Failure takes precedence over pending status.

## Troubleshooting and recovery

| Symptom | Next step |
| --- | --- |
| No project folders were created | Read the setup error first. Prerequisite and conflict checks run before project writes. Also confirm you selected project scope and the correct root. If the project installation is already gone, setup removes the stale private receipt and installs again. A different Git hook manager, or any remaining owned project file, still has to be reconciled. |
| `Existing RTK executable is incompatible or unrecognized` | Ask the harness maintainer to review the binary identity. The version number alone is insufficient; do not overwrite or downgrade the shared binary to bypass setup. |
| `nda-harness: command not found` | Use `~/.local/bin/nda-harness`, or add its bin directory to PATH. |
| Python is missing/too old | Install the organization-approved Python 3.11+ and ensure `python3` resolves correctly in the terminal, GUI client and Git environment. |
| Verification reports a missing pack | Complete a successful setup application for that same scope/project first. Verify cannot install a missing pack. |
| Existing settings, skill shadowing or symlinks conflict | Preserve the files and ask the maintainer to reconcile them. Repeated setup will not overwrite user-owned content. |
| Context7 fails | Check network access, client approval and authentication. Follow the printed connection guidance or the private verification report. |
| Existing CLI bundle differs during `install.sh` | There is no automatic upgrade command. Keep the old bundle and ask the maintainer to reconcile it, or install the approved revision under a different `--prefix`. |

Setup prints the private recovery receipt path. Preserve it and any
`recovery-needed.json` after a failed apply. Before restoring a backup, verify the
current file still matches its recorded `written_sha256`; otherwise reconcile
later edits first. Restore permissions and Git hook registration using the
[recovery procedure](../../docs/compatibility/minimal-cli-phase.md#git-gate-context-and-recovery).
Do not delete pack files or reset `core.hooksPath` blindly. No uninstall command
is provided in this phase.

When requesting help, share the command, exit code and relevant sanitized error
or check summary. Keep credentials, raw client transcripts and private source out
of support messages.
