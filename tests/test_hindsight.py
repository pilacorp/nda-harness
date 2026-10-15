import io
import json
import os
from pathlib import Path
import pty
import select
import signal
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from unittest.mock import Mock, patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from nda_harness import hindsight as memory
from nda_harness.cli import main
from nda_harness.engine import install, paths, verify
from nda_harness.files import Conflict, atomic
from nda_harness.mcp import check_hindsight, connection, NoRedirect

URL = "https://memory.example/mcp/"
KEY = "synthetic-test-key-only"
TEMPLATES = ("coding-agent", "multi-agent-orchestrator", "research")
MCP_TOOLS = ("retain", "recall", "list_banks", "create_bank", "update_bank",
             "list_mental_models", "get_mental_model", "create_mental_model",
             "list_directives", "create_directive")


def tool_listing(names):
    return [{"name": name, "inputSchema": {"type": "object", "properties": {
        "bank_id": {"type": "string"}, **({"config_updates": {"type": "object"}} if name == "update_bank" else {})
    }}} for name in names]


class TemplateTests(unittest.TestCase):
    def test_supplied_template_structure_settings_and_model_budgets(self):
        expected = {
            "coding-agent": ((5, 3, None), [("project-context", 2048), ("developer-preferences", 1024), ("review-patterns", 1024)], []),
            "multi-agent-orchestrator": ((4, 4, 2), [("decisions-and-rationale", 2048), ("ownership-map", 1536), ("resolution-playbook", 1536)], [("Preserve decision provenance", 10), ("Hand off with full context", 9)]),
            "research": ((3, 4, 2), [("interests-and-focus", 1536), ("knowledge-base", 2048), ("sources-and-reliability", 1024)], [("Learn from what's ignored", 10), ("Attach provenance to findings", 8)]),
        }
        for name, (dispositions, models, directives) in expected.items():
            with self.subTest(template=name):
                manifest = json.loads((ROOT / "pack/hindsight/templates" / (name + ".json")).read_text())
                self.assertEqual(manifest["version"], "1")
                bank = manifest["bank"]
                self.assertIs(bank["enable_observations"], True)
                self.assertTrue(bank["retain_mission"])
                self.assertTrue(bank["observations_mission"])
                self.assertEqual(tuple(bank.get("disposition_" + field) for field in ("literalism", "skepticism", "empathy")), dispositions)
                self.assertEqual([(model["id"], model["max_tokens"]) for model in manifest["mental_models"]], models)
                for model in manifest["mental_models"]:
                    self.assertTrue(model["name"])
                    self.assertTrue(model["source_query"])
                    self.assertEqual(model["trigger"], {"refresh_after_consolidation": True})
                self.assertEqual([(item["name"], item["priority"]) for item in manifest.get("directives", [])], directives)
                self.assertTrue(all(item["content"] for item in manifest.get("directives", [])))
                if name == "coding-agent":
                    self.assertNotIn("directives", manifest)
                    self.assertNotIn("reflect_mission", bank)
                    self.assertIn("what they flag, what they wave through", bank["retain_mission"])
                else:
                    self.assertTrue(bank["reflect_mission"])


class MemoryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.home = self.base / "home"
        self.home.mkdir()
        self.project = self.base / "project"
        self.project.mkdir()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        self.options = dict(agents=["codex", "cursor", "claude"], scope="project", project=self.project, test_command="true")
        self.enterContext(patch.dict(os.environ, {"CODEX_HOME": str(self.home / ".codex")}))
        self.enterContext(patch("nda_harness.engine.check_host"))
        self.enterContext(patch("nda_harness.engine.detect", return_value=[("test-desktop", "fixture")]))
        self.enterContext(patch("nda_harness.engine.prepare_rtk", return_value=Path("/test/rtk")))

    def setup_memory(self, agents=None, **changes):
        options = {**self.options, **changes}
        options.setdefault("hindsight", dict(agents=agents or options["agents"], url=URL, key=KEY))
        return install(options, ROOT, self.home)

    def verify_memory(self, options=None, live=False):
        applied = options or self.options
        _, state = paths(applied, self.home)
        receipt = json.loads((state / "receipt.json").read_text())
        return memory.verify_connections(applied, self.home, receipt, live)

    def test_url_and_key_validation(self):
        for value in (URL, "https://host/mcp", "https://host/prefix/mcp/", "http://localhost:8888/mcp/", "http://127.0.0.1/mcp", "http://[::1]/mcp/"):
            self.assertEqual(memory.endpoint_value(value), value)
        for value in ("", "http://remote.example/mcp/", "https://user:key@host/mcp/", URL + "?token=secret", URL + "#fragment", "https://host", "https://host/mcp/developer/", "https://host:bad/mcp/", "https://host/m\ncp/", "https://host\\evil/mcp/"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                memory.endpoint_value(value)
        for value in ("", "contains space", "has\rnewline", "\x7f"):
            with self.assertRaises(ValueError):
                memory.key_value(value)

    def test_enable_filters_agents_and_retries_invalid_inputs(self):
        options = {**self.options, "agents": ["codex", "claude"]}
        with patch("sys.stdin.isatty", return_value=True), patch("nda_harness.hindsight.select_options", side_effect=[["enable"], ["claude"]]) as menu, patch("builtins.input", side_effect=["bad", URL]), patch("getpass.getpass", side_effect=["", KEY]) as hidden, patch("sys.stderr", new_callable=io.StringIO):
            memory.collect_memory(options, self.home)
        self.assertEqual(options["hindsight"]["agents"], ["claude"])
        self.assertEqual(menu.call_args_list[1].args[1], [("codex", "Codex"), ("claude", "Claude Code")])
        self.assertEqual(hidden.call_count, 2)

    def test_bank_scoped_url_is_rejected_without_a_bank_question(self):
        options = dict(self.options)
        with patch("sys.stdin.isatty", return_value=True), patch("nda_harness.hindsight.select_options", side_effect=[["enable"], ["codex"]]), patch("builtins.input", side_effect=[URL + "old-bank/", URL]) as prompt, patch("getpass.getpass", return_value=KEY), patch("sys.stderr", new_callable=io.StringIO) as errors:
            memory.collect_memory(options, self.home)
        self.assertEqual(options["hindsight"]["url"], URL)
        self.assertEqual(prompt.call_count, 2)
        self.assertTrue(all(call.args == ("Hindsight multi-bank MCP URL (https://host/mcp/): ",) for call in prompt.call_args_list))
        self.assertIn("without a bank name", errors.getvalue())

    def test_skip_and_noninteractive_do_not_read_credentials(self):
        for terminal in (True, False):
            options = dict(self.options)
            with patch("sys.stdin.isatty", return_value=terminal), patch("nda_harness.hindsight.select_options", return_value=["skip"]) as menu, patch("getpass.getpass", side_effect=AssertionError("must not read key")):
                memory.collect_memory(options, self.home)
            self.assertNotIn("hindsight", options)
            self.assertEqual(menu.call_count, int(terminal))

    def test_hidden_input_fallback_is_rejected_without_echo(self):
        import getpass
        with patch("sys.stdin.isatty", return_value=True), patch("nda_harness.hindsight.select_options", side_effect=[["enable"], ["codex"]]), patch("builtins.input", return_value=URL), patch("getpass.getpass", side_effect=getpass.GetPassWarning()), self.assertRaisesRegex(ValueError, "hidden input"):
            memory.collect_memory(dict(self.options), self.home)

    def test_cancel_memory_before_install_returns_130(self):
        for error in (KeyboardInterrupt, EOFError):
            with self.subTest(error=error), patch("sys.stdin.isatty", return_value=True), patch("nda_harness.hindsight.select_options", side_effect=[["enable"], ["codex"]]), patch("builtins.input", return_value=URL), patch("getpass.getpass", side_effect=error), patch("nda_harness.cli.install") as installer, patch("nda_harness.cli.Path.home", return_value=self.home), patch("sys.stderr", new_callable=io.StringIO):
                self.assertEqual(main(["setup", "--agents", "codex", "--scope", "user"]), 130)
            installer.assert_not_called()
            self.assertFalse((self.home / ".nda-harness").exists())

    def test_all_clients_private_configs_scoped_instructions_and_skip_rerun(self):
        applied = self.setup_memory()
        for family in self.options["agents"]:
            path = memory.config_path(family, self.home)
            self.assertEqual(memory.entry(path), memory.desired(family, URL, KEY))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        for name in ("AGENTS.md", "CLAUDE.md", ".cursor/rules/nda-harness.mdc"):
            self.assertIn(memory.NAME, (self.project / name).read_text())
            self.assertIn("Before sending the final reply", (self.project / name).read_text())
            self.assertIn("call list_banks", (self.project / name).read_text())
            self.assertIn("only call create_bank when no appropriate bank exists", (self.project / name).read_text())
            self.assertIn("bank_id explicitly", (self.project / name).read_text())
            self.assertIn(".nda-harness/hindsight/README.md", (self.project / name).read_text())
        for path in self.project.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                self.assertNotIn(KEY.encode(), path.read_bytes())
        self.assertNotIn(KEY, Path(applied["receipt"]).read_text())
        shared = memory.shared_state(self.home)
        self.assertEqual(shared.stat().st_mode & 0o777, 0o700)
        self.assertNotIn(KEY, (shared / "receipt.json").read_text())
        before = {family: memory.config_path(family, self.home).read_bytes() for family in self.options["agents"]}
        install(self.options, ROOT, self.home)
        for family, content in before.items():
            self.assertEqual(memory.config_path(family, self.home).read_bytes(), content)
        self.assertEqual(self.verify_memory()[0]["status"], "verified")

    def test_only_selected_agent_instructions_include_memory(self):
        self.setup_memory(agents=["claude"])
        self.assertNotIn(memory.NAME, (self.project / "AGENTS.md").read_text())
        self.assertNotIn(memory.NAME, (self.project / ".cursor/rules/nda-harness.mdc").read_text())
        self.assertIn(memory.NAME, (self.project / "CLAUDE.md").read_text())

    def test_user_scope_merges_context7_and_hindsight_and_prepares_cursor_rules(self):
        options = {**self.options, "scope": "user", "project": None, "test_command": None}
        applied = self.setup_memory(**options)
        for family in options["agents"]:
            path = memory.config_path(family, self.home)
            self.assertIn("nda-harness-context7", path.read_text())
            self.assertEqual(memory.entry(path), memory.desired(family, URL, KEY))
        for path in (self.home / ".codex/AGENTS.md", self.home / ".claude/CLAUDE.md", Path(applied["pack"]) / "cursor-user-rules.md"):
            self.assertIn(memory.NAME, path.read_text())
            self.assertIn("call list_banks", path.read_text())
            self.assertIn("only call create_bank when no appropriate bank exists", path.read_text())
            self.assertIn(str(Path(applied["pack"]) / "hindsight/README.md"), path.read_text())
        self.assertFalse((self.project / ".nda-harness").exists())
        install(options, ROOT, self.home)
        self.assertTrue(all(c["status"] != "failed" for c in self.verify_memory(options)))

    def test_second_project_reuses_shared_connection_and_rotation_verifies_both(self):
        first = self.setup_memory(agents=["codex"])
        second = self.base / "second"
        second.mkdir()
        subprocess.run(["git", "init", "-q", str(second)], check=True)
        self.setup_memory(agents=["codex"], project=second)
        for receipt_path in (Path(first["receipt"]), paths({**self.options, "project": second}, self.home)[1] / "receipt.json"):
            receipt = json.loads(receipt_path.read_text())
            self.assertFalse(any(key.endswith("::" + memory.TAG) for key in receipt["owned"]))
        rotated = dict(agents=["codex"], url=URL, key="new-synthetic-key", replace=True)
        self.setup_memory(project=second, hindsight=rotated)
        for project in (self.project, second):
            self.assertFalse(any(c["status"] == "failed" for c in self.verify_memory({**self.options, "project": project})))

    def test_managed_replacement_needs_confirmation_and_preserves_other_entries(self):
        path = memory.config_path("cursor", self.home)
        path.parent.mkdir()
        path.write_text(json.dumps({"mcpServers": {"other": {"url": "https://other.example"}}}))
        path.chmod(0o644)
        self.setup_memory(agents=["cursor"])
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        changed = dict(agents=["cursor"], url=URL, key="rotated-key")
        with self.assertRaisesRegex(Conflict, "explicit confirmation"):
            self.setup_memory(hindsight=changed)
        for choice in ("keep", "replace"):
            options = dict(self.options)
            with patch("sys.stdin.isatty", return_value=True), patch("nda_harness.hindsight.select_options", side_effect=[["enable"], ["cursor"], [choice]]), patch("builtins.input", return_value=URL), patch("getpass.getpass", return_value="rotated-key"):
                memory.collect_memory(options, self.home)
            self.assertEqual("hindsight" in options, choice == "replace")
            install(options, ROOT, self.home)
        self.assertIn("other", json.loads(path.read_text())["mcpServers"])
        self.assertEqual(memory.entry(path)["headers"]["Authorization"], "Bearer rotated-key")
        for backup in (self.home / ".nda-harness/state").rglob("*.backup"):
            self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
            self.assertEqual(backup.parent.stat().st_mode & 0o777, 0o700)

    def test_unmanaged_conflict_and_shadowing_are_rejected(self):
        path = memory.config_path("cursor", self.home)
        path.parent.mkdir()
        path.write_text(json.dumps({"mcpServers": {memory.NAME: {"url": "https://other.example"}}}))
        with self.assertRaisesRegex(Conflict, "user-owned"):
            self.setup_memory(agents=["cursor"])
        self.assertFalse((self.project / ".nda-harness").exists())
        path.unlink()
        for family in self.options["agents"]:
            scoped = memory.REGISTRY[family].entrypoints(self.options, self.home)[1]
            scoped.parent.mkdir(parents=True, exist_ok=True)
            scoped.write_text('[mcp_servers.nda-harness-hindsight]\nurl="https://other.example"\n' if family == "codex" else json.dumps({"mcpServers": {memory.NAME: {"url": "https://other.example"}}}))
            with self.subTest(family=family), self.assertRaisesRegex(Conflict, "shadows"):
                self.setup_memory(agents=[family])
            scoped.unlink()

    def test_codex_home_inside_checkout_is_rejected_in_both_scopes(self):
        with patch.dict(os.environ, {"CODEX_HOME": str(self.project / ".codex")}):
            for scope in ("project", "user"):
                with self.subTest(scope=scope), self.assertRaisesRegex(Conflict, "outside Git"):
                    self.setup_memory(agents=["codex"], scope=scope, project=self.project if scope == "project" else None, test_command="true" if scope == "project" else None)

    def test_identical_connection_is_reused_without_reformatting_and_tightens_permissions(self):
        path = memory.config_path("cursor", self.home)
        path.parent.mkdir()
        content = json.dumps({"mcpServers": {memory.NAME: memory.desired("cursor", URL, KEY)}}, separators=(",", ":"))
        path.write_text(content)
        path.chmod(0o644)
        self.setup_memory(agents=["cursor"])
        self.assertEqual(path.read_text(), content)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_legacy_single_bank_connection_requires_confirmed_replacement(self):
        from nda_harness.files import digest, json_bytes
        self.setup_memory(agents=["cursor"])
        config = memory.config_path("cursor", self.home)
        old = memory.desired("cursor", URL + "old-bank/", KEY)
        config.write_bytes(json_bytes({"mcpServers": {memory.NAME: old}}))
        shared = memory.shared_state(self.home) / "receipt.json"
        receipt = json.loads(shared.read_bytes())
        receipt["owned"][str(config) + "::" + memory.TAG] = digest(json_bytes(old))
        shared.write_bytes(json_bytes(receipt))
        checks = self.verify_memory()
        self.assertTrue(any(c["status"] == "failed" and "multi-bank /mcp/" in c["detail"] for c in checks))
        with self.assertRaisesRegex(Conflict, "explicit confirmation"):
            self.setup_memory(agents=["cursor"])
        options = dict(self.options)
        with patch("sys.stdin.isatty", return_value=True), patch("nda_harness.hindsight.select_options", side_effect=[["enable"], ["cursor"], ["replace"]]) as menu, patch("builtins.input", return_value=URL), patch("getpass.getpass", return_value=KEY):
            memory.collect_memory(options, self.home)
        self.assertIn("Replace managed Hindsight", menu.call_args_list[-1].args[0])
        install(options, ROOT, self.home)
        self.assertEqual(memory.entry(config)["url"], URL)
        self.assertTrue(all(c["status"] != "failed" for c in self.verify_memory()))

    def test_claude_local_shadow_is_rejected_and_verify_detects_new_project_shadow(self):
        self.setup_memory(agents=["claude"])
        path = memory.config_path("claude", self.home)
        doc = json.loads(path.read_text())
        doc["projects"] = {str(self.project): {"mcpServers": {memory.NAME: memory.desired("claude", URL, KEY)}}}
        path.write_text(json.dumps(doc))
        with self.assertRaisesRegex(Conflict, "local Hindsight"):
            self.setup_memory(agents=["claude"])
        self.assertTrue(any(c["status"] == "failed" for c in self.verify_memory()))

    def test_symlinked_backup_directory_cannot_copy_credentials_into_checkout(self):
        self.setup_memory(agents=["cursor"])
        _, state = paths(self.options, self.home)
        backups = state / "backups"
        # This first installation created no backups for initially absent files.
        self.assertFalse(backups.exists())
        backups.symlink_to(self.project, target_is_directory=True)
        config = memory.config_path("cursor", self.home)
        before = config.read_bytes()
        with self.assertRaises(Conflict):
            self.setup_memory(hindsight=dict(agents=["cursor"], url=URL, key="rotated-key", replace=True))
        self.assertEqual(config.read_bytes(), before)
        self.assertFalse(list(self.project.rglob("*.backup")))

    def test_rollback_restores_shared_config_and_receipt(self):
        self.setup_memory(agents=["cursor"])
        config = memory.config_path("cursor", self.home)
        shared = memory.shared_state(self.home) / "receipt.json"
        before = (config.read_bytes(), shared.read_bytes(), (self.project / "CLAUDE.md").read_bytes())
        def fail(path, *args, **kwargs):
            if path.name == "receipt.json" and path.parent != shared.parent:
                raise OSError("simulated failure")
            return atomic(path, *args, **kwargs)
        with patch("nda_harness.engine.atomic", side_effect=fail), self.assertRaises(OSError):
            self.setup_memory(hindsight=dict(agents=["cursor", "claude"], url=URL, key="rotated-key", replace=True))
        self.assertEqual((config.read_bytes(), shared.read_bytes(), (self.project / "CLAUDE.md").read_bytes()), before)
        self.assertFalse(memory.config_path("claude", self.home).exists())

    def test_automatic_verify_deduplicates_connections_and_sanitizes_reports(self):
        self.setup_memory()
        with patch("nda_harness.mcp.check_hindsight", return_value=dict(check="hindsight-server", status="verified", detail="safe", source="automated")) as probe, patch("nda_harness.adapters.claude.ClaudeAdapter.checks", return_value=[]), patch("nda_harness.mcp.check_context7", return_value=dict(check="context7-server", status="verified", detail="safe", source="automated")):
            checks = verify(self.options, self.home, live_mcp=True)
        probe.assert_called_once_with(URL, "Bearer " + KEY)
        self.assertNotIn(KEY, json.dumps(checks))
        config = memory.config_path("cursor", self.home)
        config.chmod(0o644)
        self.assertTrue(any(c["status"] == "failed" for c in self.verify_memory()))

    def test_templates_ship_in_both_scopes_and_tampering_fails_verification(self):
        for scope in ("project", "user"):
            options = {**self.options, "scope": scope}
            if scope == "user":
                options.update(project=None, test_command=None)
            applied = self.setup_memory(**options)
            pack = Path(applied["pack"])
            release = json.loads((pack / "release.json").read_text())
            for name in TEMPLATES:
                relative = Path("hindsight/templates") / (name + ".json")
                self.assertEqual((pack / relative).read_bytes(), (ROOT / "pack" / relative).read_bytes())
                self.assertIn(str(relative), release["asset_hashes"])
            self.assertIn("hindsight/README.md", release["asset_hashes"])
            template = pack / "hindsight/templates/coding-agent.json"
            template.write_bytes(template.read_bytes() + b" ")
            self.assertEqual(verify(options, self.home, live_mcp=False)[0]["status"], "failed")

    def test_disposable_terminal_setup_hides_key_and_restores_settings(self):
        code = '''import json, sys, termios
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
from nda_harness.cli import main
before = termios.tcgetattr(0)
with patch("nda_harness.engine.check_host"), patch("nda_harness.engine.detect", return_value=[("test-desktop", "fixture")]), patch("nda_harness.engine.prepare_rtk", return_value=Path("/test/rtk")), patch("nda_harness.cli.verify", return_value=[]):
    status = main(["setup", "--agents", "codex", "--scope", "user"])
after = termios.tcgetattr(0)
before[3] &= ~getattr(termios, "PENDIN", 0)
after[3] &= ~getattr(termios, "PENDIN", 0)
print("RESTORED=" + str(before == after), flush=True)
print("STATUS=" + str(status), flush=True)
'''
        for cancel in (False, True):
            with self.subTest(cancel=cancel), tempfile.TemporaryDirectory() as temporary:
                master, slave = pty.openpty()
                process = None
                try:
                    termios.tcsetwinsize(slave, (24, 100))
                    env = dict(PATH=os.environ["PATH"], HOME=temporary, TERM="xterm-256color")
                    process = subprocess.Popen([sys.executable, "-c", code, str(ROOT / "scripts")], stdin=slave, stdout=slave, stderr=slave, env=env)
                    output = b""
                    def until(marker):
                        nonlocal output
                        deadline = time.monotonic() + 10
                        while marker not in output and time.monotonic() < deadline:
                            if select.select([master], [], [], 0.1)[0]:
                                output += os.read(master, 65536)
                        self.assertIn(marker, output)
                    until(b"Skip (preserve existing setup)")
                    os.write(master, b"\r")
                    until(b"[ ] Codex")
                    os.write(master, b" \r")
                    until(b"Hindsight multi-bank MCP URL (https://host/mcp/):")
                    os.write(master, URL.encode() + b"\r")
                    until(b"Personal Hindsight API key (hidden):")
                    if cancel:
                        # The test PTY is not the child's controlling terminal.
                        process.send_signal(signal.SIGINT)
                    else:
                        os.write(master, KEY.encode() + b"\r")
                    until(b"RESTORED=")
                    self.assertIn(b"RESTORED=True", output)
                    self.assertIn(b"STATUS=130" if cancel else b"STATUS=0", output)
                    self.assertNotIn(KEY.encode(), output)
                    self.assertNotIn(b"\x1b[40m", output)
                    self.assertNotIn(b"\x1b[37m", output)
                    self.assertEqual(process.wait(timeout=5), 0)
                    config = Path(temporary) / ".codex/config.toml"
                    if cancel:
                        self.assertFalse(config.exists())
                        self.assertFalse((Path(temporary) / ".nda-harness").exists())
                    else:
                        self.assertEqual(config.stat().st_mode & 0o777, 0o600)
                        self.assertIn(KEY, config.read_text())
                finally:
                    if process and process.poll() is None:
                        process.kill()
                        process.wait(timeout=5)
                    os.close(master)
                    os.close(slave)


class DiagnosticTests(unittest.TestCase):
    def test_discovery_only_with_pagination_and_missing_tools(self):
        required = list(MCP_TOOLS)
        for names, expected in [(required, "verified")] + [(list(set(required) - {missing}), "failed") for missing in required]:
            tools = tool_listing(names)
            call = Mock(side_effect=[{}, {}, {"tools": tools[:1], "nextCursor": "next"}, {"tools": tools[1:]}])
            with patch("nda_harness.mcp.connection", return_value=call):
                self.assertEqual(check_hindsight(URL, "Bearer " + KEY)["status"], expected)
            self.assertEqual([c.args[0] for c in call.call_args_list], ["initialize", "notifications/initialized", "tools/list", "tools/list"])

    def test_single_bank_tool_schemas_are_rejected(self):
        for missing_schema in ("recall", "retain"):
            tools = tool_listing(MCP_TOOLS)
            next(tool for tool in tools if tool["name"] == missing_schema)["inputSchema"]["properties"].pop("bank_id")
            call = Mock(side_effect=[{}, {}, {"tools": tools}])
            with patch("nda_harness.mcp.connection", return_value=call):
                check = check_hindsight(URL, "Bearer " + KEY)
            self.assertEqual(check["status"], "failed")
            self.assertIn("multi-bank /mcp/", check["detail"])

    def test_legacy_bank_update_without_config_overrides_is_rejected(self):
        tools = tool_listing(MCP_TOOLS)
        next(tool for tool in tools if tool["name"] == "update_bank")["inputSchema"]["properties"].pop("config_updates")
        with patch("nda_harness.mcp.connection", return_value=Mock(side_effect=[{}, {}, {"tools": tools}])):
            check = check_hindsight(URL, "Bearer " + KEY)
        self.assertEqual(check["status"], "failed")
        self.assertIn("config_updates", check["detail"])

    def test_sanitized_failures(self):
        failures = [TimeoutError(KEY), ValueError(KEY), KeyError(KEY), TypeError(KEY)]
        failures += [urllib.error.HTTPError(URL, code, KEY, {}, io.BytesIO(KEY.encode())) for code in (301, 302, 307, 401, 403, 500)]
        for error in failures:
            with self.subTest(error=type(error)), patch("nda_harness.mcp.connection", return_value=Mock(side_effect=error)):
                check = check_hindsight(URL, "Bearer " + KEY)
            self.assertEqual(check["status"], "failed")
            self.assertNotIn(KEY, str(check))

    def test_transport_sends_header_and_disables_redirects(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)
        response.headers = {"Mcp-Session-Id": "test-session"}
        response.read.return_value = b'{"id":1,"result":{}}'
        opener = Mock()
        opener.open.return_value = response
        with patch("urllib.request.build_opener", return_value=opener) as build:
            call = connection(URL, "Bearer " + KEY)
            call("initialize", {}, 1)
        build.assert_called_once_with(NoRedirect)
        request = opener.open.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer " + KEY)
        self.assertIsNone(NoRedirect().redirect_request(request, None, 302, "redirect", {}, "https://elsewhere.example"))

    def test_malformed_or_unbounded_discovery_fails_without_raw_data(self):
        for listing in ({}, {"tools": KEY}, {"tools": [], "nextCursor": "forever"}):
            call = Mock(side_effect=[{}, {}] + [listing] * 10)
            with patch("nda_harness.mcp.connection", return_value=call):
                check = check_hindsight(URL, "Bearer " + KEY)
            self.assertEqual(check["status"], "failed")
            self.assertNotIn(KEY, str(check))


if __name__ == "__main__":
    unittest.main()
