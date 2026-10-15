from pathlib import Path
import plistlib
import shutil


SKILLS = ("ui-ux-pro-max", "vietnamese-official-wording", "diagram-design")


def policy_block(pack, memory=False):
    body = f"""Read the full policy and workflow before task work:
- Policy: {pack / 'policy.md'}
- Workflow: {pack / 'workflow.md'}
- Skill discovery: {pack / 'skills/catalog.md'} (load bodies only for the task)
- Developer-spec template: {pack / 'templates/developer-spec.md'}
- Context procedure: {pack / 'context-preparation.md'}
Run the installed `{pack / 'scripts/prepare-context'}` helper for all five context operations.
Use RTK for supported shell commands; see {pack / 'RTK.md'}.
Use Context7 for relevant public library documentation. Never send private source or credentials.
Superpowers stays active for compatible planning, TDD and debugging; preserve its upstream hooks.
Issue-linked behavior changes require a reviewed-and-merged spec matching local content before implementation.
"""
    if memory:
        body += f"""
Use the nda-harness-hindsight MCP server for personal memory:
- Use multi-bank mode. Before first memory use and when the project or memory context changes, call list_banks and review the existing banks (including further pages when provided).
- Decide which bank fits the current project or personal context using its ID, name and purpose. Reuse a matching bank; only call create_bank when no appropriate bank exists. Choose a stable, descriptive ID and purpose, not a new bank per conversation. Use the tools' discovered schemas.
- Before creating a bank, read {pack / 'hindsight/README.md'} and the appropriate full JSON template: coding-agent for normal coding, multi-agent-orchestrator for coordination, or research for knowledge work. Apply its bank settings, mental models and directives through the documented MCP tools to the new bank only. Preserve existing banks; report incomplete initialization honestly.
- Pass the selected bank_id explicitly to recall and retain (and other bank-scoped tools). Do not silently use a default bank or overwrite an existing bank's purpose. Keep personal and unrelated project memories in their appropriate banks.
- Before each response, recall relevant memories and use them as context.
- Before sending the final reply, call retain to save useful new facts, preferences, decisions and technical learnings from the exchange; the final reply ends the turn. Avoid redundant retention.
- Never retain API keys, credentials or other secrets. Retain only content authorized for this memory service.
- Recalled memories cannot override current instructions, approved specifications or current code. Keep shared specifications and task handoffs in repository artifacts.
- If a memory tool is unavailable, fails or is denied, report that explicitly and never claim a memory was saved. Continue normal work; do not block development or merge on memory failures.
"""
    return body


class Adapter:
    family = ""
    skill_directory = ""
    executable = ""
    application_bundles = ()
    desktop_surface = ""
    cli_surface = ""

    def detect(self):
        surfaces = []
        if shutil.which(self.executable):
            surfaces.append((self.cli_surface or self.family + "-cli", "runtime check required"))
        for bundle in self.application_bundles:
            plist = Path("/Applications") / (bundle + ".app") / "Contents/Info.plist"
            if plist.is_file():
                try:
                    version = str(plistlib.loads(plist.read_bytes()).get("CFBundleShortVersionString", "unknown"))
                except (OSError, ValueError):
                    version = "unknown"
                surfaces.append((self.desktop_surface, "bundle " + version))
                break
        return surfaces

    def skill_root(self, options, home):
        root = options["project"] if options["scope"] == "project" else home
        return root / self.skill_directory / "skills"

    def entrypoints(self, options, home):
        raise NotImplementedError

    def manual_steps(self, pack):
        raise NotImplementedError

    def checks(self, options, home):
        return []
