import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from nda_harness.cli import collect_options
from nda_harness.engine import install, verify
from nda_harness.engine import check_host
from nda_harness.adapters import REGISTRY
from nda_harness.adapters.codex import CodexAdapter
from nda_harness.files import Conflict


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self.project = self.base / "project with spaces"
        self.project.mkdir()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        self.options = {"agents": ["codex", "cursor"], "scope": "project", "project": self.project, "test_command": "true"}

    def setup(self, **changes):
        options = {**self.options, **changes}
        with patch("nda_harness.engine.check_host"), patch("nda_harness.engine.detect", return_value=[("cursor-ide", "3.24.12")]), patch.dict("os.environ", {"CODEX_HOME": str(self.home / ".codex")}):
            return install(options, ROOT, self.home)

    def test_two_adapters_and_future_registry_extension(self):
        self.assertEqual(set(REGISTRY), {"codex", "cursor"})
        self.assertTrue(all(hasattr(adapter, "plan") for adapter in REGISTRY.values()))
        class FutureAdapter(CodexAdapter):
            family = "future"
            skill_directory = ".future"
        with patch.dict(REGISTRY, {"future": FutureAdapter()}):
            self.setup(agents=["future"])
            self.assertTrue((self.project / ".future/skills/diagram-design/SKILL.md").exists())

    def test_no_flags_user_flow(self):
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=["codex", "user"]) as prompt:
            options = collect_options("setup", None, None, None, None)
        self.assertEqual(options["scope"], "user")
        self.assertEqual(prompt.call_count, 2)

    def test_noninteractive_missing_options(self):
        with patch("sys.stdin.isatty", return_value=False):
            with self.assertRaisesRegex(ValueError, "--agents.*--scope"):
                collect_options("setup", None, None, None, None)

    def test_intel_host_is_deferred(self):
        with patch("platform.system", return_value="Darwin"), patch("platform.machine", return_value="x86_64"):
            with self.assertRaisesRegex(ValueError, "Apple Silicon"):
                check_host()

    def test_install_preserves_and_reruns(self):
        (self.project / "AGENTS.md").write_text("Original instructions\n")
        config = self.project / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text('# keep comment\nmodel = "test"\n')
        self.setup()
        before = config.read_bytes()
        self.setup()
        self.assertEqual(config.read_bytes(), before)
        self.assertIn("# keep comment", config.read_text())
        self.assertIn("Original instructions", (self.project / "AGENTS.md").read_text())
        self.assertEqual((self.project / "AGENTS.md").read_text().count("<!-- nda-harness:begin -->"), 1)
        self.assertTrue((self.project / ".agents/skills/diagram-design/SKILL.md").is_file())
        self.assertTrue((self.project / ".nda-harness/scripts/prepare-context").stat().st_mode & 0o111)

    def test_conflict_preflight_has_no_pack_side_effects(self):
        config = self.project / ".cursor/mcp.json"
        config.parent.mkdir()
        config.write_text('{"mcpServers":{"nda-harness-context7":{"url":"https://other.example"}}}')
        with self.assertRaises(Conflict):
            self.setup()
        self.assertFalse((self.project / ".nda-harness").exists())
        self.assertFalse((self.project / "AGENTS.md").exists())

    def test_unknown_pack_content_requires_reconciliation(self):
        pack = self.project / ".nda-harness"
        pack.mkdir()
        unknown = pack / "unowned-script.sh"
        unknown.write_text("user-owned content")
        with self.assertRaisesRegex(Conflict, "Unknown installed pack content"):
            self.setup()
        self.assertEqual(unknown.read_text(), "user-owned content")
        self.assertFalse((pack / "policy.md").exists())

    def test_user_scope_has_no_project_hook(self):
        self.setup(scope="user", project=None, test_command=None)
        self.assertTrue((self.home / ".nda-harness/pack/templates/developer-spec.md").exists())
        self.assertFalse((self.project / ".nda-harness").exists())
        self.assertEqual(subprocess.run(["git", "-C", str(self.project), "config", "--get", "core.hooksPath"], capture_output=True).returncode, 1)

    def test_changed_owned_block_conflicts(self):
        self.setup()
        instructions = self.project / "AGENTS.md"
        instructions.write_text(instructions.read_text().replace("Read the full", "EDIT Read the full"))
        with self.assertRaises(Conflict):
            self.setup()

    def test_partial_flags_preserve_supplied_values(self):
        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=["project", "true"]) as prompt:
            options = collect_options("setup", "codex", None, str(self.project), None)
        self.assertEqual(options["agents"], ["codex"])
        self.assertEqual(options["project"], self.project)
        self.assertEqual(prompt.call_count, 2)

    def test_full_flags_do_not_prompt(self):
        with patch("builtins.input", side_effect=AssertionError("unexpected prompt")):
            options = collect_options("setup", "codex,cursor,codex", "project", str(self.project), "true")
        self.assertEqual(options["agents"], ["codex", "cursor"])

    def test_user_scope_rejects_project_flags(self):
        with self.assertRaisesRegex(ValueError, "User scope rejects"):
            collect_options("setup", "codex", "user", str(self.project), None)

    def test_verify_rejects_test_command(self):
        with self.assertRaisesRegex(ValueError, "verify rejects"):
            collect_options("verify", "codex", "project", str(self.project), "true")

    def test_malformed_toml_is_not_overwritten(self):
        config = self.project / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text("[not valid")
        with self.assertRaises(Conflict):
            self.setup()
        self.assertEqual(config.read_text(), "[not valid")

    def test_failed_apply_restores_original_instructions(self):
        instructions = self.project / "AGENTS.md"
        instructions.write_text("original\n")
        from nda_harness.files import atomic
        def failing(path, *args, **kwargs):
            if path == self.project / ".cursor/mcp.json":
                raise OSError("simulated failure")
            return atomic(path, *args, **kwargs)
        with patch("nda_harness.files.atomic", side_effect=failing):
            with self.assertRaises(OSError):
                self.setup()
        self.assertEqual(instructions.read_text(), "original\n")
        self.assertFalse((self.project / ".nda-harness").exists())

    def test_runtime_is_self_contained(self):
        self.setup()
        helper = self.project / ".nda-harness/scripts/prepare-context"
        result = subprocess.run([str(helper), "session-bootstrap", "--project", str(self.project)], cwd=self.home, env={"HOME": str(self.home), "PATH": os.environ["PATH"]}, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('"operation": "session-bootstrap"', result.stdout)


if __name__ == "__main__":
    unittest.main()
