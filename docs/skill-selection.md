# Jev skill selection

The plugin selects optional specialist skills with Jev through OpenRouter. The coding model does not choose that set, and it does not read specialist bodies before the helper returns them.

Model: `typesafe/jev-1.14`. Endpoint: `https://openrouter.ai/api/alpha/decisions`. One request asks one yes/no question per specialist in `skills/catalog.json`, sorted by id. The request carries bounded task text and catalog metadata. It does not carry skill bodies or the key.

The current specialists are `diagram-design`, `ui-ux-pro-max`, and `vietnamese-official-wording`. A probability of at least 0.80 selects a skill. A probability of at most 0.20 excludes it. A value strictly between those thresholds is `uncertain_decision`. The agent asks the user whether to load each uncertain skill, then calls `record-selection` so that choice is stored in the local Jev cache. An empty selection is valid. Mandatory workflow skills stay in force either way. Selection does not approve work.

## Key

Each developer uses a personal OpenRouter key. It is stored in the macOS Keychain and is not the Hindsight server key. Do not paste it into chat, a command argument, or a project file.

In a local terminal, from the project directory:

```sh
rtk proxy <plugin-root>/bin/nda-plugin selection-setup --client <client>
```

The Cursor plugin opens that terminal with `skill-selection`. The prompt is hidden. When the key is saved, the terminal prints `OpenRouter key saved.` It does not print JSON. Running the command again asks before replacing the saved key. Answering no keeps that key, prints `The saved OpenRouter key was kept.`, and finishes setup for this client. A setup problem also prints a sentence, including `A local terminal is required.` when the command is not attached to a terminal.

`selection-verify` checks the package, catalog, and whether a key is present. It does not call OpenRouter. Add `--live` only for one synthetic paid check. In a terminal the check prints a sentence, such as `OpenRouter key is present.` or `Live check passed.` An agent that captures the command still receives JSON.

## Agent use

For a new assignment the agent calls `select-skills` with `--project`, `--session`, and `--request-file`, then `load-selected-skills` with the same task JSON. Those agent commands return JSON. `select-skills` does not include skill bodies. `load-selected-skills` returns only the selected bodies.

When Jev returns `uncertain_decision`, `select-skills` lists each uncertain skill and its probability and does not return a loadable selection. The agent asks the user, in chat, whether to load each of those skills. It does not choose for them. It then calls `record-selection` with the same task JSON plus `decisions`, an object mapping each uncertain skill id to `true` or `false`. That writes the resolved choice into the local cache. A later `select-skills` for the same task reuses that cache. `load-selected-skills` then returns only the skills the user included.

Equivalent task text reuses a cached result for seven days. A changed assignment, catalog, package, rules version, model, or key generation calls Jev again. Replacing the key starts a new generation, so the previous cache is not loaded.

## Limits

Specialist directories still ship beside workflow skills. A separate hub directory is later work. Paid selection quality and native client checks are not claimed by the unit tests. No live OpenRouter call is part of those tests.
