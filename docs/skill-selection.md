# Jev skill selection

The plugin selects optional specialist skills with Jev through OpenRouter. When no OpenRouter key is saved, the same helper gives those questions to the coding agent already running the session and stores the answer as `local-agent`. The agent does not read specialist bodies before the helper returns them.

Model: `typesafe/jev-1.14`. Endpoint: `https://openrouter.ai/api/alpha/decisions`. One request asks one yes/no question per specialist in `skills/catalog.json`, sorted by id. The request carries bounded task text and catalog metadata. It does not carry skill bodies or the key.

Catalog schema version 2 gives each specialist its own required `question`, positive `select_when` criterion, and negative `exclude_when` criterion. Each question is followed by shared instructions to classify the agreed deliverables: do not invent optional work, and do not select a skill merely because its subject, technology, or language is mentioned. Missing source material or approvals affects readiness to execute, not applicability. These instructions apply equally to Jev and the local-agent fallback.

Diagram creation, modification, and evaluation qualify; architecture discussion or reading a diagram as background alone does not. UI/UX includes interface and interaction evaluation, including accessibility; backend work does not qualify merely because it serves a UI. Vietnamese official wording covers documents whose primary purpose is organizational communication or administration. Vietnamese technical writing covers engineering and product content, including translation and interface messages. An internal engineering RFC remains technical content; ordinary Vietnamese chat alone selects neither writing skill.

The current specialists are `diagram-design`, `ui-ux-pro-max`, `vietnamese-official-wording`, and `vietnamese-tech-writing`. A probability of at least 0.80 selects a skill. A probability of at most 0.20 excludes it. A value strictly between those thresholds is `uncertain_decision`. The agent asks the user whether to load each uncertain skill, then calls `record_selection` so that choice is stored in the local Jev cache. An empty selection is valid. Mandatory workflow skills stay in force either way. Selection does not approve work.

## Key

Each developer uses a personal OpenRouter key. It is stored in `~/.nda-harness/skill-selection/openrouter-key` (mode `0600`) and is not the Hindsight server key. That path is ignored by Git. Do not paste it into chat, a command argument, or a project file.

If an older install still has the key in the macOS Keychain, migrate once in a local terminal:

```sh
rtk proxy <plugin-root>/bin/nda-plugin selection-migrate --client <client>
```

For a new key, or after migration, run setup:

```sh
rtk proxy <plugin-root>/bin/nda-plugin selection-setup --client <client>
```

The Cursor plugin opens that terminal with `skill-selection`. The prompt is hidden. When the key is saved, the terminal prints `OpenRouter key saved.` It does not print JSON. Running the command again asks before replacing the saved key. Answering no keeps that key, prints `The saved OpenRouter key was kept.`, and finishes setup for this client. A setup problem also prints a sentence, including `A local terminal is required.` when the command is not attached to a terminal.

`selection-verify` checks the package, catalog, and whether a key is present. It does not call OpenRouter. Add `--live` only for one synthetic paid check. In a terminal the check prints a sentence, such as `OpenRouter key is present.` or `Live check passed.` An agent that captures the command still receives JSON.

## Agent use

Enable/trust the local `nda-harness-jev` MCP server in the installed client and reload for discovery if needed. Codex, Cursor, and Claude registrations use the same bundled Python 3.9+ standard-library server, launched as a stdio child process. There is no daemon, port or runtime dependency download. Claude hosted archives relocate the launcher to `scripts/nda-plugin`.

For a new assignment call MCP `select_skills` with an absolute existing `project` directory, `session`, and `task` containing the unchanged schema-1 assignment JSON. Call `load_selected_skills` with the same values. Each response contains one text block with JSON. Only the loader returns bodies. A cache miss or explicit `refresh: true` can make one paid request; no automatic retries occur.

```json
{"project":"/absolute/project","session":"assignment-1","task":{"schema_version":1,"request":"Implement the agreed feature","stage":"implementation","project_facts":{"stack":[],"deliverables":[],"constraints":[]}}}
```

Call `selection_verify` without arguments for an offline check. Only an explicit request for a paid synthetic check permits `{"live":true}`. Tools cannot set keys, endpoints, models, home paths or package roots. Terminal `selection-verify` remains available for legacy diagnostics.

When Jev returns `uncertain_decision`, `select_skills` lists each uncertain skill and its probability and does not return a loadable selection. The agent asks the user, in chat, whether to load each of those skills. It does not choose for them. It then calls `record_selection` with the same task JSON plus `decisions`, an object mapping each uncertain skill id to `true` or `false`. That writes the resolved choice into the local cache. A later `select_skills` for the same task reuses that cache. `load_selected_skills` then returns only the skills the user included.

When no key is saved, `select_skills` returns diagnostic `local_agent` and the same questions Jev would have received. It does not call OpenRouter and it does not ask for setup. The running coding agent answers every question with `type` `noul` and a probability from 0 to 1, then calls `select_skills` again with an `answers` object containing those answers. The helper stores the model name `local-agent` and applies the same 0.80 / 0.20 cutoffs. A saved key this session cannot read still stops with `credential_unavailable`. A `local-agent` result is cached for seven days. Saving a key starts a new generation, so the next selection calls Jev.

Equivalent task text reuses a cached result for seven days. A changed assignment, catalog, package, rules version, model, or key generation calls Jev again. Replacing the key starts a new generation, so the previous cache is not loaded.

The per-skill question contract uses rules version `jev-specialists-v2`. Changing a catalog question invalidates earlier selections, including recorded user choices. Legacy catalog schemas are rejected; runtime and catalog updates ship together in each client package. The task-input schema remains version 1.

The server owns private key/cache access and HTTPS while ordinary shell restrictions remain in place. The key and seven-day cache are shared with legacy CLI operations; changing transport does not rotate credentials or change cache identity. Direct sandboxed CLI operations retain `sandbox_rerun`.

If native discovery or invocation establishes that the server is absent, disabled, denied or cannot start, report `jev_mcp_unavailable` and follow the installed [outage guide](../pack/jev-outage.md). The running agent answers the verified catalog questions directly, applies the same thresholds and asks about every uncertain skill. Verify and load only the selected entrypoints. Record local-agent, the catalog revision, IDs and decisions without claiming a cache entry. No credentials, provider call, setup or selector rerun is needed. Pause dependent specialist work if the relevant bundle files cannot be verified. A responding server's failures still follow its diagnostics.

After timeout or disconnect, delivery may be unknown. Reconnect with the same task/session and reuse completed cache records without refresh. A crash before caching can cause another paid call; exactly-once billing is not promised. To roll back, disable the Jev MCP entry or restore the preceding plugin version, preserving keys and cache files.

## Limits

Specialist directories still ship beside workflow skills. A separate hub directory is later work. Paid selection quality and native client checks are not claimed by the unit tests. No live OpenRouter call is part of those tests.

The uncertainty band remains `0.20 < p < 0.80` while evaluating the clearer questions. No reduction in confirmations is claimed until a labeled comparison measures both unnecessary confirmations and missed applicable skills. Narrowing the band is a separate policy decision.
