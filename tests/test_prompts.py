import curses
import io
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

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from nda_harness.cli import collect_options, main
from nda_harness.prompts import _keyboard, select_options

AGENTS = [("codex", "Codex"), ("cursor", "Cursor"), ("claude", "Claude Code")]
SCOPES = [("project", "Project"), ("user", "User")]


class PromptTests(unittest.TestCase):
    def keyboard(self, keys, multiple=True):
        screen = Mock()
        screen.getmaxyx.return_value = (24, 100)
        screen.getch.side_effect = keys
        with patch("curses.curs_set"):
            result = _keyboard(screen, "Agents" if multiple else "Scope", AGENTS if multiple else SCOPES, multiple)
        return result, screen

    def test_multi_select_toggle_and_registry_order(self):
        values, _ = self.keyboard([32, curses.KEY_DOWN, 32, 32, curses.KEY_DOWN, 32, 10])
        self.assertEqual(values, ["codex", "claude"])

    def test_empty_enter_does_not_select_highlighted_agent(self):
        values, screen = self.keyboard([10, 32, 10])
        self.assertEqual(values, ["codex"])
        self.assertTrue(any("Select at least one" in str(call) for call in screen.addnstr.call_args_list))

    def test_both_scopes_and_resize(self):
        for keys, expected in (([10], "project"), ([curses.KEY_RESIZE, curses.KEY_DOWN, 13], "user")):
            self.assertEqual(self.keyboard(keys, multiple=False)[0], [expected])

    def test_keyboard_cancellation(self):
        for key, error in ((3, KeyboardInterrupt), (27, KeyboardInterrupt), (4, EOFError)):
            with self.subTest(key=key), self.assertRaises(error):
                self.keyboard([key])

    def test_numbered_fallback_retries_invalid_and_deduplicates(self):
        with patch("sys.stdin.isatty", return_value=True), patch.dict(os.environ, {"TERM": "dumb"}), patch("builtins.input", side_effect=["", "0", "4", "codex", "3,1,3"]), patch("sys.stderr", new_callable=io.StringIO), patch("curses.wrapper", side_effect=AssertionError("unexpected curses")):
            self.assertEqual(select_options("Agents", AGENTS, multiple=True), ["codex", "claude"])
        with patch("sys.stdin.isatty", return_value=True), patch.dict(os.environ, {"TERM": "dumb"}), patch("builtins.input", side_effect=["1,2", "2"]), patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(select_options("Scope", SCOPES), ["user"])

    def test_curses_failure_falls_back_to_numbers(self):
        with patch("sys.stdin.isatty", return_value=True), patch("sys.stdout.isatty", return_value=True), patch.dict(os.environ, {"TERM": "xterm"}), patch("curses.wrapper", side_effect=curses.error("unsupported")), patch("builtins.input", return_value="2"), patch("sys.stderr", new_callable=io.StringIO):
            self.assertEqual(select_options("Scope", SCOPES), ["user"])

    def test_long_repository_path_is_not_truncated(self):
        path = "/project/" + "long-folder-" * 10
        screen = Mock()
        screen.getmaxyx.return_value = (24, 40)
        def wrapper(callback, *args):
            return callback(screen, *args)
        with patch("sys.stdin.isatty", return_value=True), patch("sys.stdout.isatty", return_value=True), patch.dict(os.environ, {"TERM": "xterm"}), patch("curses.wrapper", side_effect=wrapper), patch("curses.curs_set"), patch("builtins.input", return_value="1"), patch("sys.stderr", new_callable=io.StringIO) as output:
            self.assertEqual(select_options("Repository", [(path, "Use " + path), ("", "Choose another folder")]), [path])
        self.assertIn("1. Use " + path, output.getvalue())
        screen.getch.assert_not_called()

    def test_nonterminal_selection_never_reads_input(self):
        with patch("sys.stdin.isatty", return_value=False), patch("builtins.input", side_effect=AssertionError("unexpected input")):
            with self.assertRaisesRegex(ValueError, "--agents and --scope"):
                select_options("Agents", AGENTS, multiple=True)

    def test_verify_prompts_for_missing_selections_only(self):
        with patch("sys.stdin.isatty", return_value=True), patch("nda_harness.cli.select_options", side_effect=[["claude"], ["user"]]) as menu, patch("builtins.input", side_effect=AssertionError("unexpected text prompt")):
            options = collect_options("verify", None, None, None, None)
        self.assertEqual(options["agents"], ["claude"])
        self.assertEqual(options["scope"], "user")
        self.assertEqual(menu.call_count, 2)

    def test_cancel_before_installation_returns_130(self):
        for command in ("setup", "verify"):
            for error in (KeyboardInterrupt, EOFError):
                with self.subTest(command=command, error=error), patch("sys.stdin.isatty", return_value=True), patch("nda_harness.cli.select_options", side_effect=error), patch("nda_harness.cli.install") as install, patch("nda_harness.cli.verify") as verify, patch("sys.stderr", new_callable=io.StringIO):
                    self.assertEqual(main([command]), 130)
                install.assert_not_called()
                verify.assert_not_called()

    def test_real_terminal_success_and_cancellation_restore_settings(self):
        code = '''import json, sys, termios
sys.path.insert(0, sys.argv[1])
from nda_harness.cli import collect_options
before = termios.tcgetattr(0)
try:
    options = collect_options("verify", None, None, None, None)
    print("RESULT=" + json.dumps(options), flush=True)
except (KeyboardInterrupt, EOFError):
    print("CANCELLED", flush=True)
finally:
    after = termios.tcgetattr(0)
    # macOS sets the transient pending-input bit when cooked mode is restored.
    before[3] &= ~termios.PENDIN
    after[3] &= ~termios.PENDIN
    print("RESTORED=" + str(before == after), flush=True)
'''
        for action in ("select", "interrupt", "eof", "small"):
            with self.subTest(action=action), tempfile.TemporaryDirectory() as temporary:
                master, slave = pty.openpty()
                self.addCleanup(os.close, master)
                self.addCleanup(os.close, slave)
                # Give curses a known screen size independently of the test runner.
                termios.tcsetwinsize(slave, (4 if action == "small" else 24, 100))
                env = {"PATH": os.environ["PATH"], "HOME": temporary, "TERM": "xterm-256color"}
                process = subprocess.Popen([sys.executable, "-c", code, str(ROOT / "scripts")], stdin=slave, stdout=slave, stderr=slave, env=env)
                self.addCleanup(lambda process=process: process.poll() is None and process.kill())
                output = b""
                def until(marker):
                    nonlocal output
                    deadline = time.monotonic() + 10
                    while marker not in output and time.monotonic() < deadline:
                        if select.select([master], [], [], 0.1)[0]:
                            output += os.read(master, 65536)
                    self.assertIn(marker, output)
                if action == "small":
                    until(b"Select numbers separated by commas")
                    os.write(master, b"1\r")
                    until(b"Select one number")
                    os.write(master, b"2\r")
                    until(b"RESTORED=")
                    self.assertIn(b"RESTORED=True", output)
                    self.assertIn(b'"scope": "user"', output)
                else:
                    until(b"[ ] Claude Code")
                if action == "select":
                    os.write(master, b" \r")
                    until(b"User - personal")
                    os.write(master, b"\x1bOB\r")
                    until(b"RESTORED=")
                    self.assertIn(b"RESTORED=True", output)
                    self.assertIn(b'"scope": "user"', output)
                    self.assertIn(b'"agents": ["codex"]', output)
                elif action != "small":
                    if action == "interrupt":
                        process.send_signal(signal.SIGINT)
                    else:
                        os.write(master, b"\x04")
                    until(b"RESTORED=")
                    self.assertIn(b"RESTORED=True", output)
                    self.assertIn(b"CANCELLED", output)
                self.assertEqual(process.wait(timeout=5), 0)
                self.assertFalse((Path(temporary) / ".nda-harness").exists())
