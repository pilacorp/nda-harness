"""Shared registrations for Claude Code CLI and Desktop's local Code tab."""
import json
import os
from pathlib import Path
import shutil
import subprocess

from .common import Adapter, policy_block


class ClaudeAdapter(Adapter):
    family = "claude"
    skill_directory = ".claude"
    executable = "claude"
    application_bundles = ("Claude",)
    cli_surface = "claude-code-cli"
    desktop_surface = "claude-desktop-code"

    def entrypoints(self, options, home):
        if options["scope"] == "project":
            return options["project"] / "CLAUDE.md", options["project"] / ".mcp.json"
        return home / ".claude/CLAUDE.md", home / ".claude.json"

    def plan(self, plan, options, home, pack):
        instructions, config = self.entrypoints(options, home)
        plan.block(instructions, policy_block(Path(".nda-harness") if options["scope"] == "project" else pack))
        return plan.mcp(config, "json", transport="http")

    def checks(self, options, home):
        executable = shutil.which(self.executable)
        if not executable:
            return []  # Desktop-only installations do not require the standalone CLI.
        status = "failed"
        detail = "Claude authentication diagnostic failed or is unsupported; inspect claude auth status locally."
        try:
            run = subprocess.run([executable, "auth", "status", "--json"],
                                 cwd=options["project"] or home, env={**os.environ, "HOME": str(home)},
                                 stdin=subprocess.DEVNULL, capture_output=True, timeout=15)
            auth = json.loads(run.stdout)
            if run.returncode in (0, 1) and isinstance(auth, dict) and isinstance(auth.get("loggedIn"), bool):
                status = "verified" if run.returncode == 0 and auth["loggedIn"] else "awaiting_manual"
                detail = "CLI authentication is available; Desktop authentication is checked separately in its local Code tab." if status == "verified" else "Sign in using claude auth login, then rerun verify."
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        return [{"check": self.cli_surface + "-auth", "status": status, "source": "automated", "detail": detail}]

    def manual_steps(self, pack):
        return ["Start a fresh local Claude Code session (Desktop: Code tab, Local environment, adopted project folder). Confirm policy/catalog/template and specialist skills load; CLI checks do not prove Desktop readiness.",
                "Approve nda-harness-context7 through the client's MCP controls and authenticate if required (CLI: /mcp). Resolve a public library ID and retrieve focused docs in this surface; keep credentials in the client store.",
                "Install Superpowers through the official plugin marketplace (CLI: /plugin marketplace add obra/superpowers, then /plugin install superpowers@superpowers-marketplace; Desktop: plugin manager). Require revision bb92a77741419a4ab5f06e711a283343f1ada0c3 (manifest 7.0.0); leave pending if the client cannot identify/pin it. Confirm activation and upstream SessionStart output.",
                f"Confirm RTK usage from {pack / 'RTK.md'} and run the five documented context operations through {pack / 'scripts/prepare-context'} in this client's PATH. Native lifecycle and rewriting use the explicit instruction fallback; preserve upstream hooks."]
