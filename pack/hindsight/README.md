# Hindsight bank templates

Use these version-1 manifests when creating a new bank through multi-bank MCP.
Choose the template by the bank's purpose, not the client application:

| Template | Use for |
| --- | --- |
| [Coding agent](templates/coding-agent.json) | Coding, project architecture, conventions and developer review preferences; the default for normal coding work |
| [Multi-agent orchestrator](templates/multi-agent-orchestrator.json) | Coordinating agents, ownership, pipeline phases, decisions and hand-offs |
| [Research](templates/research.json) | Research, briefings, durable findings, user interests and source reliability |

## Creating a bank

1. Call `list_banks` first, following pagination, and reuse an appropriate existing
   bank. Respect explicit user bank IDs and routing rules. Do not apply a template
   to an existing bank just because its configuration differs from these defaults.
2. If no appropriate bank exists, read the chosen JSON file in full. Create a bank
   with a stable ID and descriptive name using `create_bank`. Do not create a bank
   per conversation or overwrite an existing bank's purpose. List again if creation
   reports an existing bank or a conflict; reuse it without reconfiguration.
3. Inspect the discovered MCP schemas. For the bank you just created, call
   `update_bank` with explicit `bank_id` and `config_updates` equal to the entire
   manifest's `bank` object. Preserve every supplied mission, observation flag and
   disposition value; omitted fields remain server defaults.
4. Call `list_mental_models` for that bank, following pagination, before creating each missing model with
   `create_mental_model`. Map manifest `id` to `mental_model_id`; pass `name`,
   `source_query`, `max_tokens` and `trigger` unchanged, plus explicit `bank_id`.
   In particular, keep `refresh_after_consolidation: true`. Preserve existing
   models (inspect them with `get_mental_model`), including ones installed by a server default template; do not replace
   their settings automatically. Report any conflicting ID/settings as incomplete
   initialization rather than claiming the requested template was applied.
5. If the manifest has `directives`, call `list_directives` with `active_only: false`
   and follow pagination. Create missing directives with `create_directive`, passing
   each exact `name`, `content`, `priority` and explicit `bank_id`. Do not duplicate
   names or overwrite existing directives; report conflicting settings as incomplete.
   If `directives` is absent, leave directives unchanged.
6. Check each tool result for errors, then list directives and use `get_mental_model`
   for each model to confirm their IDs/names and supplied settings. Mental model creation may return a pending
   operation: report it as pending, not completed content generation. Do not claim
   full initialization if any setting, model, directive or tool is unavailable.
   Report the exact incomplete step and continue normal development without
   falling back to another/default bank. Do not delete a partially initialized bank.

Only configure a bank created for this task, or one whose initialization you have
explicit authorization to resume. Before resuming, read its current configuration,
models and directives; preserve existing entries and add only missing components.
Do not blindly repeat writes after an uncertain/failed request. This procedure
does not authorize retrofitting templates onto existing personal/project banks,
moving memories, changing access controls, or sharing banks across user accounts.

The manifests also use the upstream
[bank template import format](https://github.com/vectorize-io/hindsight/blob/main/skills/hindsight-docs/references/developer/api/bank-templates.md).
MCP application uses the native tools rather than exposing API keys to shell
commands. CLI setup and verification install/check the local assets and discover
tool capabilities; they do not create banks, apply templates, or synthesize models.
