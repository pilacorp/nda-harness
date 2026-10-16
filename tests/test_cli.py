import io
import json
from contextlib import redirect_stdout
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from nda_harness.cli import collect_options, main, detect_project
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
        self.enterContext(patch("nda_harness.engine.prepare_rtk", return_value=Path("/test/rtk")))
        self.project = self.base / "project with spaces"
        self.project.mkdir()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        self.options = {"agents": ["codex", "cursor"], "scope": "project", "project": self.project, "test_command": "true"}

    def setup(self, **changes):
        options = {**self.options, **changes}
        with patch("nda_harness.engine.check_host"), patch("nda_harness.engine.detect", return_value=[("cursor-ide", "3.24.12")]), patch.dict("os.environ", {"CODEX_HOME": str(self.home / ".codex")}):
            return install(options, ROOT, self.home)

    def test_three_adapters_and_future_registry_extension(self):
        self.assertEqual(set(REGISTRY), {"codex", "cursor", "claude"})
        self.assertTrue(all(hasattr(adapter, "plan") for adapter in REGISTRY.values()))
        class FutureAdapter(CodexAdapter):
            family = "future"
            skill_directory = ".future"
        with patch.dict(REGISTRY, {"future": FutureAdapter()}):
            self.setup(agents=["future"])
            self.assertTrue((self.project / ".future/skills/diagram-design/SKILL.md").exists())

    def test_verification_details_go_to_private_report_not_terminal(self):
        checks = [{"check": "pack", "status": "failed", "source": "automated", "detail": "Detailed installation failure"},
                  {"check": "session", "status": "awaiting_manual", "source": "manual required", "detail": "Long session checklist"}]
        for command, added in (("setup", ["claude"]), ("setup", []), ("verify", [])):
            with self.subTest(command=command, added=added):
                output = io.StringIO()
                applied = dict(pack=str(self.home / ".nda-harness/pack"), receipt="receipt", changed_files=1,
                               rtk_path="/test/rtk", context7_added=added)
                with patch("nda_harness.cli.Path.home", return_value=self.home), patch("nda_harness.cli.install", return_value=applied), patch("nda_harness.cli.verify", return_value=checks), redirect_stdout(output):
                    self.assertEqual(main([command, "--agents", "claude", "--scope", "user"]), 1)
                text = output.getvalue()
                self.assertNotIn("Detailed installation failure", text)
                self.assertNotIn("Long session checklist", text)
                self.assertIn("1 failed", text)
                from nda_harness.engine import paths
                _, state = paths(dict(scope="user", project=None), self.home)
                report = state / "verification.json"
                self.assertEqual(json.loads(report.read_text())["checks"], checks)
                self.assertEqual(report.stat().st_mode & 0o777, 0o600)
                if command == "setup":
                    self.assertIn("Context7", text)
                    if added:
                        self.assertIn("added for claude", text)
                        self.assertIn("/mcp", text)
                    else:
                        self.assertIn("already configured", text)
                        self.assertNotIn("/mcp", text)

    def test_no_flags_user_flow(self):
        with patch("sys.stdin.isatty", return_value=True), patch("nda_harness.cli.select_options", side_effect=[["codex"], ["user"]]) as prompt:
            options = collect_options("setup", None, None, None, None)
        self.assertEqual(options["scope"], "user")
        self.assertEqual(prompt.call_count, 2)

    def test_noninteractive_missing_options(self):
        with patch("sys.stdin.isatty", return_value=False):
            with self.assertRaisesRegex(ValueError, "--agents.*--scope"):
                collect_options("setup", None, None, None, None)

    def test_detected_project_requires_confirmation_from_root_or_subfolder(self):
        nested = self.project / "src"
        nested.mkdir()
        for directory in (self.project, nested):
            for command in ("setup", "verify"):
                with self.subTest(directory=directory, command=command), patch("sys.stdin.isatty", return_value=True), patch("nda_harness.cli.Path.cwd", return_value=directory), patch("nda_harness.cli.select_options", return_value=[str(self.project)]) as menu, patch("builtins.input", side_effect=AssertionError("unexpected text prompt")):
                    options = collect_options(command, "claude", "project", None, "true" if command == "setup" else None)
                self.assertEqual(options["project"], self.project)
                menu.assert_called_once()
                self.assertIn(str(self.project), menu.call_args.args[1][0][1])
                self.assertEqual(menu.call_args.args[1][1], ("", "Choose another folder"))

    def test_choose_other_project_retries_invalid_root(self):
        with patch("sys.stdin.isatty", return_value=True), patch("nda_harness.cli.detect_project", return_value=self.project), patch("nda_harness.cli.select_options", return_value=[""]), patch("builtins.input", side_effect=[str(self.home), str(self.project)]), patch("sys.stderr", new_callable=io.StringIO):
            options = collect_options("setup", "claude", "project", None, "true")
        self.assertEqual(options["project"], self.project)

    def test_no_detected_repository_asks_for_path(self):
        with patch("sys.stdin.isatty", return_value=True), patch("nda_harness.cli.Path.cwd", return_value=self.home), patch("nda_harness.cli.select_options", side_effect=AssertionError("unexpected menu")), patch("builtins.input", return_value=str(self.project)) as prompt:
            options = collect_options("verify", "claude", "project", None, None)
        self.assertEqual(options["project"], self.project)
        prompt.assert_called_once()

    def test_supplied_project_user_scope_and_nonterminal_skip_detection(self):
        with patch("nda_harness.cli.detect_project", side_effect=AssertionError("unexpected detection")):
            options = collect_options("verify", "claude", "project", str(self.project), None)
            self.assertEqual(options["project"], self.project)
            self.assertIsNone(collect_options("verify", "claude", "user", None, None)["project"])
            with patch("sys.stdin.isatty", return_value=False), self.assertRaisesRegex(ValueError, "--project"):
                collect_options("verify", "claude", "project", None, None)

    def test_detect_linked_worktree_root(self):
        env = {"HOME": str(self.home), "PATH": os.environ["PATH"]}
        subprocess.run(["git", "-C", str(self.project), "-c", "user.name=Test", "-c", "user.email=test@example.test", "commit", "--allow-empty", "-qm", "fixture"], check=True, env=env)
        linked = self.base / "linked worktree"
        subprocess.run(["git", "-C", str(self.project), "worktree", "add", "--detach", str(linked)], check=True, capture_output=True, env=env)
        with patch("nda_harness.cli.Path.cwd", return_value=linked):
            self.assertEqual(detect_project(), linked)

    def test_cancel_repository_confirmation_does_not_install(self):
        for error in (KeyboardInterrupt, EOFError):
            with self.subTest(error=error), patch("sys.stdin.isatty", return_value=True), patch("nda_harness.cli.detect_project", return_value=self.project), patch("nda_harness.cli.select_options", side_effect=error), patch("nda_harness.cli.install") as install, patch("sys.stderr", new_callable=io.StringIO):
                self.assertEqual(main(["setup", "--agents", "claude", "--scope", "project", "--test-command", "true"]), 130)
            install.assert_not_called()

    def test_detection_failure_falls_back_to_path_prompt(self):
        for error in (OSError(), subprocess.TimeoutExpired("git", 15)):
            with self.subTest(error=type(error)), patch("nda_harness.cli.git", side_effect=error):
                self.assertIsNone(detect_project())

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

    def test_setup_appends_missing_gitignore_patterns_and_preserves_user_edits(self):
        ignore = self.project / ".gitignore"
        original = b"# Keep existing rules\r\n.env\r\n__pycache__/"
        ignore.write_bytes(original)
        ignore.chmod(0o640)
        applied = self.setup()
        expected = original + b"\r\n*.py[cod]\r\n"
        self.assertEqual(ignore.read_bytes(), expected)
        self.assertEqual(ignore.stat().st_mode & 0o777, 0o640)
        receipt = Path(applied["receipt"])
        recovery = json.loads(receipt.read_text())["recovery"]
        backup = next(item["backup"] for item in recovery if item["path"] == str(ignore))
        self.assertEqual(Path(backup).read_bytes(), original)
        self.setup()
        self.assertEqual(ignore.read_bytes(), expected)
        self.assertEqual(json.loads(receipt.read_text())["recovery"], recovery)
        ignore.write_bytes(expected + b"# Later developer rule\r\nnode_modules/\r\n")
        self.setup()
        self.assertTrue(ignore.read_bytes().endswith(b"node_modules/\r\n"))
        self.assertEqual(ignore.read_bytes().count(b"__pycache__/"), 1)
        self.assertEqual(ignore.read_bytes().count(b"*.py[cod]"), 1)
        for path, code in ((".nda-harness/scripts/__pycache__/runtime.pyc", 0), ("module.pyo", 0), (".nda-harness/policy.md", 1)):
            self.assertEqual(subprocess.run(["git", "-C", str(self.project), "check-ignore", "-q", path]).returncode, code)

    def test_setup_preserves_empty_or_lf_gitignore(self):
        ignore = self.project / ".gitignore"
        for original in (b"", b"# Existing\n.env\n"):
            with self.subTest(original=original):
                ignore.write_bytes(original)
                self.setup()
                self.assertEqual(ignore.read_bytes(), original + b"__pycache__/\n*.py[cod]\n")

    def test_setup_does_not_create_gitignore_or_change_it_in_user_scope(self):
        ignore = self.project / ".gitignore"
        self.setup()
        self.assertFalse(ignore.exists())
        ignore.write_text(".env\n")
        self.setup(scope="user", project=None, test_command=None)
        self.assertEqual(ignore.read_text(), ".env\n")

    def test_gitignore_update_is_rolled_back_after_apply_failure(self):
        ignore = self.project / ".gitignore"
        ignore.write_bytes(b".env\n")
        from nda_harness.files import atomic
        def failing(path, *args, **kwargs):
            if path == self.project / ".cursor/mcp.json":
                raise OSError("simulated failure")
            return atomic(path, *args, **kwargs)
        with patch("nda_harness.files.atomic", side_effect=failing), self.assertRaises(OSError):
            self.setup()
        self.assertEqual(ignore.read_bytes(), b".env\n")

    def test_gitignore_symlink_is_rejected_without_changes(self):
        external = self.home / "ignore"
        external.write_text(".env\n")
        (self.project / ".gitignore").symlink_to(external)
        with self.assertRaises(Conflict):
            self.setup()
        self.assertEqual(external.read_text(), ".env\n")
        self.assertFalse((self.project / ".nda-harness").exists())

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

    def _remove_project_installation(self, applied):
        receipt = json.loads(Path(applied["receipt"]).read_text())
        for key in receipt["owned"]:
            path = Path(key.rsplit("::", 1)[0])
            try:
                path.relative_to(self.project)
            except ValueError:
                continue
            if path.is_file() and not path.is_symlink():
                path.unlink()
        shutil.rmtree(self.project / ".nda-harness")

    def test_missing_project_installation_discards_receipt_and_reinstalls(self):
        applied = self.setup()
        receipt_path = Path(applied["receipt"])
        state = receipt_path.parent
        self._remove_project_installation(applied)
        unset = subprocess.run(["git", "-C", str(self.project), "config", "--local", "--unset", "core.hooksPath"], capture_output=True)
        self.assertEqual(unset.returncode, 0)
        self.setup()
        self.assertTrue((self.project / ".nda-harness/release.json").is_file())
        self.assertTrue((self.project / "AGENTS.md").is_file())
        hooks = subprocess.run(["git", "-C", str(self.project), "config", "--get", "core.hooksPath"], capture_output=True, text=True)
        self.assertEqual(hooks.stdout.strip(), str(state / "hooks"))
        self.assertEqual(json.loads(receipt_path.read_text())["schema_version"], 1)

    def test_missing_project_installation_keeps_active_hook_wrapper_then_reinstalls(self):
        applied = self.setup()
        self._remove_project_installation(applied)
        self.setup()
        self.assertTrue((self.project / ".nda-harness/release.json").is_file())
        hooks = subprocess.run(["git", "-C", str(self.project), "config", "--get", "core.hooksPath"], capture_output=True, text=True)
        self.assertEqual(hooks.stdout.strip(), str(Path(applied["receipt"]).parent / "hooks"))

    def test_partial_project_files_keep_stale_receipt(self):
        self.setup()
        instructions = (self.project / "AGENTS.md").read_text()
        shutil.rmtree(self.project / ".nda-harness")
        subprocess.run(["git", "-C", str(self.project), "config", "--local", "--unset", "core.hooksPath"], check=True)
        with self.assertRaisesRegex(Conflict, "Git hook manager"):
            self.setup()
        self.assertFalse((self.project / ".nda-harness").exists())
        self.assertEqual((self.project / "AGENTS.md").read_text(), instructions)

    def test_foreign_hook_manager_is_not_replaced_when_project_files_are_gone(self):
        applied = self.setup()
        self._remove_project_installation(applied)
        foreign = self.base / "other-hooks"
        foreign.mkdir()
        subprocess.run(["git", "-C", str(self.project), "config", "--local", "core.hooksPath", str(foreign)], check=True)
        with self.assertRaisesRegex(Conflict, "Git hook manager"):
            self.setup()
        self.assertEqual(subprocess.run(["git", "-C", str(self.project), "config", "--get", "core.hooksPath"], capture_output=True, text=True).stdout.strip(), str(foreign))
        self.assertTrue(Path(applied["receipt"]).is_file())

    def test_partial_flags_preserve_supplied_values(self):
        with patch("sys.stdin.isatty", return_value=True), patch("nda_harness.cli.select_options", side_effect=[["project"], ["enter"]]) as menu, patch("builtins.input", return_value="python3 -m unittest") as prompt:
            options = collect_options("setup", "codex", None, str(self.project), None)
        self.assertEqual(options["agents"], ["codex"])
        self.assertEqual(options["project"], self.project)
        self.assertEqual(prompt.call_count, 1)
        self.assertEqual(menu.call_count, 2)
        self.assertEqual(options["test_command"], "python3 -m unittest")

    def test_skip_test_command_never_reads_text_and_installs_true(self):
        with patch("sys.stdin.isatty", return_value=True), patch("nda_harness.cli.select_options", return_value=["skip"]) as menu, patch("builtins.input", side_effect=AssertionError("unexpected text prompt")):
            options = collect_options("setup", "codex", "project", str(self.project), None)
        self.assertEqual(options["test_command"], "true")
        menu.assert_called_once_with("Non-watch unit-test command", [("enter", "Enter a unit-test command"), ("skip", "Skip unit tests (use true)")])
        applied = self.setup(**options)
        self.assertEqual(json.loads((Path(applied["pack"]) / "profile.json").read_text())["test_command"], "true")

    def test_enter_test_command_retries_empty_and_noninteractive_still_requires_flag(self):
        with patch("sys.stdin.isatty", return_value=True), patch("nda_harness.cli.select_options", return_value=["enter"]), patch("builtins.input", side_effect=["", "python3 -m unittest"]), patch("sys.stderr", new_callable=io.StringIO):
            options = collect_options("setup", "codex", "project", str(self.project), None)
        self.assertEqual(options["test_command"], "python3 -m unittest")
        with patch("sys.stdin.isatty", return_value=False), patch("nda_harness.cli.select_options", side_effect=AssertionError("unexpected menu")), self.assertRaisesRegex(ValueError, "--test-command"):
            collect_options("setup", "codex", "project", str(self.project), None)

    def test_cancel_test_command_menu_returns_130_before_install(self):
        for error in (KeyboardInterrupt, EOFError):
            with self.subTest(error=error), patch("sys.stdin.isatty", return_value=True), patch("nda_harness.cli.select_options", side_effect=error), patch("nda_harness.cli.install") as install, patch("sys.stderr", new_callable=io.StringIO):
                self.assertEqual(main(["setup", "--agents", "codex", "--scope", "project", "--project", str(self.project)]), 130)
            install.assert_not_called()

    def test_full_flags_do_not_prompt(self):
        with patch("builtins.input", side_effect=AssertionError("unexpected prompt")), patch("nda_harness.cli.select_options", side_effect=AssertionError("unexpected menu")):
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
