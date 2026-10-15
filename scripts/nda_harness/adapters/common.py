from pathlib import Path
import plistlib
import shutil


SKILLS = ("ui-ux-pro-max", "vietnamese-official-wording", "diagram-design")


def policy_block(pack):
    return f"""Read the full policy and workflow before task work:
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
