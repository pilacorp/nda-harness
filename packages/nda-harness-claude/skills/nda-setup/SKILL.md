---
name: nda-setup
description: Recover plugin bootstrap or configure the current project and its local Git test gate.
---

This plugin is bound to **claude**. Never ask the user to choose clients or scope.
Run the packaged `${CLAUDE_PLUGIN_ROOT}/bin/nda-plugin setup --client claude --project <actual-root>`
using the plugin's resolved absolute install path, quoted as a single executable.
Do not require a global nda-harness executable or a source checkout.

Read the full packaged policy and workflow. For a new project, ask for its non-watch
test command in chat, offering Skip. Then pass the exact user-chosen command as one
`--test-command` argument, or `--skip-tests` only for explicit Skip. Never infer Skip
from absent input, failures, or noninteractive hooks. Avoid commands containing
credentials; configure references to local secret stores instead.

For a folder that is not a Git checkout, and for a repository with no remote, ask
for a stable shared project name (`--project-name` lowercase slug). Git commit
hooks are installed only for a repository. For distinct remotes ask which remote identifies this project
(`--remote`); do not choose based on branch or client. Identity conflicts require
owner reconciliation, not deleting the profile or silently switching banks.

Commit `.nda-harness/profile.json`. Add `.nda-harness/tasks/` to the project's
`.gitignore` and keep task records local; never stage or force-add `task.md` or
other files in that directory. Do not copy plugin assets or private state into
the project. Local activation must run on each clone.
Test command configuration is owner-controlled and executes at Git commit from
the repository root. Both existing hooks and the configured command must pass.

Python 3.9+, Git and the supported Apple Silicon macOS host are prerequisites.
Bootstrap installs the checksum-pinned RTK if absent. Superpowers skills and full
support assets are bundled. Context7 is a native packaged MCP registration; inspect
its connection in the invoking client. Do not modify other clients or shell startup
files. A failed, untrusted or asynchronous hook does not prove readiness.
If RTK is not on PATH, read the absolute `rtk_path` from private
`~/.nda-harness/plugin-bootstrap/claude.json` and invoke that path. Keep that
machine-specific path out of committed project files and task records.

One memory system is active per project. If the package offers several, ask which
one and pass `--memory-system`. A single packaged system is selected automatically.
Do not start login here. NDA Hindsight uses MCP `https://hindsight-api.pila.vn/mcp/`
and OAuth and REST on `https://hindsight-api.pila.vn`. The user may Authenticate/Authorize the NDA Hindsight
row in plugin details. No endpoint packaged means optional memory is
disabled; core setup continues. Report core and memory status separately.
