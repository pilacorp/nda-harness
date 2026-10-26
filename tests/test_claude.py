from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from nda_harness.adapters import REGISTRY
from nda_harness.cli import main
from nda_harness.engine import install, verify, paths
from nda_harness.files import Conflict


class ClaudeTests(unittest.TestCase):
    def setUp(self):
        self.contexts = ExitStack()
        self.addCleanup(self.contexts.close)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name).resolve() / "home"
        self.home.mkdir()
        self.project = self.home.parent / "project with spaces"
        self.project.mkdir()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        self.options = dict(agents=["claude"], scope="project", project=self.project, test_command="true")
        for name, value in (("check_host", None), ("detect", [("claude-code-cli", "test"), ("claude-desktop-code", "test")]),
                            ("prepare_rtk", Path("/test/rtk"))):
            self.contexts.enter_context(patch("nda_harness.engine." + name, return_value=value))

    def install(self):
        return install(self.options, ROOT, self.home)

    def test_both_scopes_preserve_config_and_rerun(self):
        for scope in ("project", "user"):
            with self.subTest(scope=scope):
                self.options.update(scope=scope, project=self.project if scope == "project" else None,
                                    test_command="true" if scope == "project" else None)
                root = self.project if scope == "project" else self.home / ".claude"
                root.mkdir(exist_ok=True)
                instructions = root / "CLAUDE.md"
                instructions.write_text("Existing instructions\n")
                config = self.project / ".mcp.json" if scope == "project" else self.home / ".claude.json"
                original = {"mcpServers": {"other": {"command": "keep"}}, "projects": {"keep": {"trusted": False}}}
                config.write_text(json.dumps(original))
                settings = root / ".claude/settings.json" if scope == "project" else root / "settings.json"
                settings.parent.mkdir(exist_ok=True)
                settings.write_text('{"hooks":{"SessionStart":[{"hooks":[{"command":"upstream"}]}]}}')
                before_settings = settings.read_bytes()
                self.assertEqual(self.install()["context7_added"], ["claude"])
                before = config.read_bytes()
                self.assertEqual(self.install()["context7_added"], [])
                self.assertEqual(config.read_bytes(), before)
                doc = json.loads(before)
                self.assertEqual(doc["mcpServers"]["nda-harness-context7"], {"type": "http", "url": "https://mcp.context7.com/mcp"})
                self.assertEqual(doc["projects"], original["projects"])
                self.assertEqual(doc["mcpServers"]["other"], original["mcpServers"]["other"])
                self.assertEqual(settings.read_bytes(), before_settings)
                self.assertTrue(instructions.read_text().startswith("Existing instructions\n"))
                self.assertEqual(instructions.read_text().count("<!-- nda-harness:begin -->"), 1)
                self.assertTrue((root / ".claude/skills/diagram-design/SKILL.md" if scope == "project" else root / "skills/diagram-design/SKILL.md").is_file())

    def test_conflicting_mcp_stops_before_pack_writes(self):
        (self.project / ".mcp.json").write_text('{"mcpServers":{"nda-harness-context7":{"url":"https://other"}}}')
        with self.assertRaises(Conflict):
            self.install()
        self.assertFalse((self.project / ".nda-harness").exists())

    def test_detects_cli_and_local_desktop_separately(self):
        adapter = REGISTRY["claude"]
        with patch("shutil.which", return_value="/test/claude"), patch.object(Path, "is_file", return_value=True), patch.object(Path, "read_bytes", return_value=b"invalid plist"):
            self.assertEqual([name for name, _ in adapter.detect()], ["claude-code-cli", "claude-desktop-code"])
        with patch("shutil.which", return_value=None), patch.object(Path, "is_file", return_value=True), patch.object(Path, "read_bytes", return_value=b"invalid plist"):
            self.assertEqual([name for name, _ in adapter.detect()], ["claude-desktop-code"])
            self.assertEqual(adapter.checks(self.options, self.home), [])
        with patch("shutil.which", return_value="/test/claude"), patch.object(Path, "is_file", return_value=False):
            self.assertEqual([name for name, _ in adapter.detect()], ["claude-code-cli"])
        with patch("shutil.which", return_value=None), patch.object(Path, "is_file", return_value=False):
            self.assertEqual(adapter.detect(), [])

    def test_verify_is_automatic_read_only_and_sanitized(self):
        self.install()
        config = self.project / ".mcp.json"
        before = config.read_bytes()
        real_run = subprocess.run
        def run(argv, **kwargs):
            if argv[0] == "/test/claude":
                self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
                self.assertEqual(kwargs["cwd"], self.project)
                output = b'{"loggedIn":true,"email":"private@example.com"}' if argv[1:] == ["auth", "status", "--json"] else b"2.1.263 (Claude Code)"
                return subprocess.CompletedProcess(argv, 0, output, b"")
            return real_run(argv, **kwargs)
        with patch("builtins.input", side_effect=AssertionError("unexpected prompt")), patch("shutil.which", return_value="/test/claude"), patch("nda_harness.engine.locate_rtk", return_value=None), patch("subprocess.run", side_effect=run):
            checks = verify(self.options, self.home, live_mcp=False)
        self.assertEqual(config.read_bytes(), before)
        self.assertTrue(any(c["check"] == "claude-code-cli-auth" and c["status"] == "verified" for c in checks))
        self.assertTrue(any(c["check"].startswith("claude-desktop-code") for c in checks))
        _, state = paths(self.options, self.home)
        self.assertNotIn("private@example.com", str(checks) + (state / "readiness.json").read_text())

    def test_auth_diagnostic_handles_pending_failure_and_timeout(self):
        for code, output, expected in ((1, b'{"loggedIn":false}', "awaiting_manual"), (0, b"invalid", "failed"), (0, b'{"loggedIn":false}', "awaiting_manual")):
            with self.subTest(code=code, output=output), patch("shutil.which", return_value="/test/claude"), patch("subprocess.run", return_value=subprocess.CompletedProcess([], code, output, b"secret")):
                checks = REGISTRY["claude"].checks(self.options, self.home)
                self.assertEqual(checks[0]["status"], expected)
                self.assertNotIn("secret", str(checks))
        with patch("shutil.which", return_value="/test/claude"), patch("subprocess.run", side_effect=subprocess.TimeoutExpired([], 15)):
            self.assertEqual(REGISTRY["claude"].checks(self.options, self.home)[0]["status"], "failed")

    def test_verify_cli_never_requests_manual_observations_even_on_terminal(self):
        with patch("nda_harness.cli.Path.home", return_value=self.home), patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=AssertionError("unexpected prompt")), patch("nda_harness.cli.verify", return_value=[]) as diagnostic:
            self.assertEqual(main(["verify", "--agents", "claude", "--scope", "user"]), 0)
        self.assertFalse(diagnostic.call_args.kwargs.get("observe", False))
