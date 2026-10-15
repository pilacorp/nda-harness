# How to install NDA Harness

This guide is for organization developers configuring an existing coding agent
with the team's workflow, specialist skills, Context7 and project test hooks.
Install the command once on your Mac, then run setup for each project you adopt.

The current implementation targets **Apple Silicon macOS**. It configures Codex
desktop/CLI, Cursor IDE/CLI and Claude Code CLI/Claude Desktop's **local Code tab**.
Intel macOS, Linux, Windows, remote sessions and Claude Chat/Cowork are outside
this phase. Full client compatibility validation is still pending; see the
[implementation and evidence guide](docs/compatibility/minimal-cli-phase.md).

## 1. Prepare your Mac and project

You need:

- Access to this private GitHub repository and your team's target repository.
- Python **3.11 or newer**, available as `python3`, and Git on PATH.
- At least one installed surface for every agent family you select. Install and
  sign in to the agent separately; setup does not install coding agents.
- Your project's approved, non-watch **unit-test command**, for project setup.
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

Find the target repository root from inside that repository:

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

| Prompt | What to enter |
| --- | --- |
| Agents | `claude`, `codex`, `cursor`, or a comma-separated selection such as `codex,claude` |
| Scope | `project` |
| Target Git worktree root | The absolute path printed above, for example `/Users/yourname/Projects/tsa-simulator` |
| Non-watch unit-test command | The command approved for that project, for example `npm run test:unit` if that script exists |

The test command runs from the target repository root during setup, verification
and pre-commit. Use a command that exits when finished. **Do not use `true`: it
always succeeds without running tests.** Run the chosen command yourself first
and resolve any project prerequisites it needs.

You can also supply all options explicitly. Replace both the path and test
command with your project's actual values:

```sh
nda-harness setup --agents claude --scope project \
  --project /absolute/path/to/project --test-command 'npm run test:unit'
```

With complete flags, no option-selection prompts are shown. Setup backs up changed
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
| No project folders were created | Read the setup error first. Prerequisite and conflict checks run before project writes. Also confirm you selected project scope and the correct root. |
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
[recovery procedure](docs/compatibility/minimal-cli-phase.md#git-gate-context-and-recovery).
Do not delete pack files or reset `core.hooksPath` blindly. No uninstall command
is provided in this phase.

When requesting help, share the command, exit code and relevant sanitized error
or check summary. Keep credentials, raw client transcripts and private source out
of support messages.
