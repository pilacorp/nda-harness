import os
from pathlib import Path
from .common import Adapter, policy_block


class CodexAdapter(Adapter):
    family = "codex"
    skill_directory = ".agents"
    executable = "codex"
    application_bundles = ("Codex", "ChatGPT")
    desktop_surface = "codex-desktop"

    def entrypoints(self, options, home):
        root = options["project"] if options["scope"] == "project" else Path(os.environ.get("CODEX_HOME") or home / ".codex").absolute()
        config = root / ".codex/config.toml" if options["scope"] == "project" else root / "config.toml"
        return root / "AGENTS.md", config

    def plan(self, plan, options, home, pack):
        instructions, config = self.entrypoints(options, home)
        plan.block(instructions, policy_block(Path(".nda-harness") if options["scope"] == "project" else pack, memory=self.family in options.get("memory_agents", [])))
        return plan.mcp(config, "toml")

    def manual_steps(self, pack):
        return ["Start a fresh Codex session and read the installed policy/catalog/template.",
                "Connect nda-harness-context7 through Codex MCP authentication; keep credentials in the client's private store. Use codex mcp login nda-harness-context7 where available. In this fresh client resolve a public library ID and retrieve focused docs through this server.",
                "Install Superpowers through Codex Plugins using its official marketplace; verify compatible skills load. Require revision bb92a77741419a4ab5f06e711a283343f1ada0c3 (manifest 7.0.0); if the UI cannot pin/identify it, leave this pending rather than claiming a mutable marketplace name is pinned.",
                "Confirm RTK usage and invoke all context operations through the documented entrypoint fallback."]
