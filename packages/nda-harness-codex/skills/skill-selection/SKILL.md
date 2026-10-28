---
name: skill-selection
description: Set up or reuse Jev skill selection for this client, then load only the selected specialist bodies.
disable-model-invocation: true
---

This plugin is bound to **codex**. Never ask the user to choose a client.

When the user invokes this command, open a terminal and run selection-setup. Do not run it in the agent shell. Pass the actual project root:

`sh ${PLUGIN_ROOT}/skills/skill-selection/scripts/open-terminal.sh codex <project-root>`

That script opens Terminal, changes to that project directory, and then runs `rtk proxy ${PLUGIN_ROOT}/bin/nda-plugin selection-setup --client codex`. Leave that terminal focused so the user can answer the prompt. The terminal prints a short sentence, not JSON.

Task text and catalog metadata are sent to OpenRouter at `https://openrouter.ai/api/alpha/decisions` using model `typesafe/jev-1.14`. The OpenRouter key stays in the macOS Keychain. Never paste a key into chat, a command argument, or a project file.

First setup and re-setup use the same command in a normal local terminal:

`rtk proxy ${PLUGIN_ROOT}/bin/nda-plugin selection-setup --client codex`

Replace the saved OpenRouter key by running that command again. The terminal asks before replacing it. Answering no keeps the saved key and finishes setup. The terminal prints `The saved OpenRouter key was kept.`

Check without a paid call:

`rtk proxy ${PLUGIN_ROOT}/bin/nda-plugin selection-verify --client codex`

A paid synthetic check is only:

`rtk proxy ${PLUGIN_ROOT}/bin/nda-plugin selection-verify --client codex --live`

On `authorization_failed`, direct the user to the same re-setup command. Do not ask for the key in chat.

For a new assignment, call `select-skills` with `--project`, `--session`, and `--request-file`, then `load-selected-skills` with the same task JSON. Do not read specialist bodies before that. On `uncertain_decision`, ask the user whether to load each skill in `uncertain`. Do not choose for them. Then call `record-selection` with the same task JSON plus a `decisions` object mapping each uncertain skill id to true or false. That stores the choice in the local Jev cache. Then call `load-selected-skills`. On `blocked`, report `diagnostic` and `next`. Do not load every specialist.

Mandatory workflow skills stay in force. Jev does not grant approval.
