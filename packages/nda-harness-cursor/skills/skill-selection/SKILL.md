---
name: skill-selection
description: Set up or reuse Jev skill selection for this client, then load only the selected specialist bodies.
disable-model-invocation: true
---

If `.nda-harness/config.json` in this project has `"enabled": false`, reply with exactly `NDA Harness is disabled on the project` and stop. Do not run this skill.

This plugin is bound to **cursor**. Never ask the user to choose a client.

When the user invokes this command, open a terminal and run selection-setup. Do not run it in the agent shell. Pass the actual project root:

`sh ${CURSOR_PLUGIN_ROOT}/skills/skill-selection/scripts/open-terminal.sh cursor <project-root>`

That script opens Terminal, changes to that project directory, and then runs `rtk proxy ${CURSOR_PLUGIN_ROOT}/bin/nda-plugin selection-setup --client cursor`. Leave that terminal focused so the user can answer the prompt. The terminal prints a short sentence, not JSON.

Task text and catalog metadata are sent to OpenRouter at `https://openrouter.ai/api/alpha/decisions` using model `typesafe/jev-1.14`. The OpenRouter key stays in `~/.nda-harness/skill-selection/openrouter-key`. Never paste a key into chat, a command argument, or a project file. If a Keychain item remains from an older install, run `selection-migrate` in a local terminal once.

First setup and re-setup use the same command in a normal local terminal:

`rtk proxy ${CURSOR_PLUGIN_ROOT}/bin/nda-plugin selection-setup --client cursor`

Replace the saved OpenRouter key by running that command again. The terminal asks before replacing it. Answering no keeps the saved key and finishes setup. The terminal prints `The saved OpenRouter key was kept.`

For daily selection use the local `nda-harness-jev` MCP server. Keep the client's ordinary shell restrictions. Enable/trust the server through the client's normal controls and reload if discovery requires it.

Call `selection_verify` without arguments for an offline package/key check. Only an explicit request for a paid synthetic check permits `selection_verify` with `{"live": true}`. Terminal `selection-verify` remains a legacy diagnostic.

On `authorization_failed`, direct the user to the same terminal re-setup command. Do not ask for the key in chat.

For a new assignment call MCP `select_skills` with `project` (an absolute existing directory), `session`, and `task` (the unchanged schema-1 assignment JSON). A cache miss or explicit `refresh: true` can incur a paid Jev request. Never preload specialist bodies. Call `load_selected_skills` with the same project, session, and task to receive only selected bodies.

On `uncertain_decision`, ask the user whether to include every uncertain skill. Do not choose for them. Call `record_selection` with the same assignment plus `decisions`, mapping exactly those ids to booleans, then `load_selected_skills`.

On `local_agent` (only a missing key), answer every question with type `noul` and probability 0 to 1. Call `select_skills` again with the same assignment and `answers` object. The model name is `local-agent`. An unreadable key blocks with `credential_unavailable`.

When native discovery or invocation confirms MCP is absent, disabled, failed to
start, or denied, report `jev_mcp_unavailable` and follow the installed
`pack/jev-outage.md` for local-agent selection. Legacy CLI selection operations
retain `sandbox_rerun`. The key file is shared by Codex, Cursor, and Claude.
After an interrupted call with unknown delivery, reconnect with the same
task/session without refresh. A responding server's failure keeps its own diagnostic.

Mandatory workflow skills stay in force. Jev does not grant approval.
