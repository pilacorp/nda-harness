from pathlib import Path
from .common import Adapter, policy_block


class CursorAdapter(Adapter):
    family = "cursor"
    skill_directory = ".cursor"
    executable = "agent"
    application_bundles = ("Cursor",)
    desktop_surface = "cursor-ide"

    def entrypoints(self, options, home):
        root = options["project"] if options["scope"] == "project" else home
        instructions = root / ".cursor/rules/nda-harness.mdc" if options["scope"] == "project" else None
        return instructions, root / ".cursor/mcp.json"

    def plan(self, plan, options, home, pack):
        instructions, config = self.entrypoints(options, home)
        if instructions:
            content = '---\ndescription: NDA Harness workflow\nalwaysApply: true\n---\n\n' + policy_block(Path(".nda-harness"))
            plan.file(instructions, content.encode())
        else:
            plan.file(pack / "cursor-user-rules.md", policy_block(pack).encode())
        return plan.mcp(config, "json")

    def manual_steps(self, pack):
        return [f"For user scope, paste the exact contents of {pack / 'cursor-user-rules.md'} into Cursor Settings > Rules > User Rules. Preserve other rules.",
                "Start a fresh Cursor session; confirm policy/catalog/template and complete skill resources load.",
                "Connect nda-harness-context7 in MCP settings (CLI: agent mcp login nda-harness-context7); keep authentication in the client's private store. In this fresh client resolve a public library ID and retrieve focused docs through this server.",
                "Install the official Superpowers plugin using /add-plugin superpowers; verify activation. Require revision bb92a77741419a4ab5f06e711a283343f1ada0c3 (manifest 7.0.0); if the marketplace cannot pin/identify it, leave this pending.",
                "Use RTK instructions and the explicit context-helper fallback. This phase installs no custom rewriting or lifecycle native hooks."]
