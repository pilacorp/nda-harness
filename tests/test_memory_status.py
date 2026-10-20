"""Native diagnostic interpretation, not a second OAuth client."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from nda_harness import memory
from nda_harness.plugin_build import build

SERVER = 'nda-harness-hindsight'
CONFIG = {'memory_systems': {'endpoints': {'hindsight': 'https://hindsight-api.pila.vn/mcp/'}}}


def notification(**fields):
    return {'method': 'mcpServer/startupStatus/updated',
            'params': {'name': SERVER, 'status': 'failed', **fields}}


class MemoryStatusTests(unittest.TestCase):
    def report(self, client, data=None, config=CONFIG):
        return memory.memory_status(config, client, data)

    def test_codex_refresh_failure_is_targeted_to_client_and_server(self):
        data = notification(failureReason='reauthenticationRequired')
        result = self.report('codex', data)
        self.assertEqual(result['memory_state'], 'awaiting_authentication')
        self.assertEqual(result['diagnostic'], 'reauthentication_required')
        self.assertIn('mcp login nda-harness-hindsight', result['next_action'])
        for client in ('cursor', 'claude'):
            with self.subTest(client=client):
                self.assertEqual(self.report(client, data)['memory_state'], 'pending_native_diagnostic')
        data['params']['name'] = 'another-server'
        self.assertEqual(self.report('codex', data)['memory_state'], 'pending_native_diagnostic')

    def test_claude_statuses_are_not_codex_or_cursor_signals(self):
        for status, expected in [('needs-auth', 'awaiting_authentication'),
                                 ('pending', 'pending_native_diagnostic'),
                                 ('failed', 'unavailable'), ('connected', 'connected')]:
            data = {'name': SERVER, 'status': status}
            with self.subTest(status=status):
                self.assertEqual(self.report('claude', data)['memory_state'], expected)
                self.assertEqual(self.report('cursor', data)['memory_state'], 'pending_native_diagnostic')
        for client in ('codex', 'claude'):
            self.assertEqual(self.report(client, {'name': 'other', 'status': 'needs-auth'})['memory_state'],
                             'pending_native_diagnostic')
        self.assertEqual(self.report('codex', {'name': SERVER, 'status': 'needs-auth'})['memory_state'],
                         'pending_native_diagnostic')

    def test_missing_tools_and_saved_oauth_are_not_authentication_verdicts(self):
        for data in (None, {}, {'name': SERVER, 'authStatus': 'oAuth'},
                     {'name': SERVER, 'authStatus': 'oAuth', 'tools': {}},
                     {'name': SERVER, 'authStatus': 'oAuth', 'tools': 'not-a-tool-list'},
                     notification(status='starting', failureReason='reauthenticationRequired')):
            with self.subTest(data=data):
                self.assertEqual(self.report('codex', data)['memory_state'], 'pending_native_diagnostic')

    def test_codex_discovery_and_failure_precedence(self):
        tools = {'recall': {'name': 'recall'}}
        self.assertEqual(self.report('codex', {'name': SERVER, 'authStatus': 'oAuth', 'tools': tools})['memory_state'],
                         'connected')
        for data in (notification(tools=tools), notification(error='HTTP 401 SECRET'),
                     {'name': SERVER, 'status': 'failed', 'authStatus': 'oAuth', 'tools': tools}):
            with self.subTest(data=data):
                result = self.report('codex', data)
                self.assertEqual(result['memory_state'], 'unavailable')
                self.assertNotIn('SECRET', json.dumps(result))

    def test_disabled_and_output_do_not_copy_untrusted_fields(self):
        self.assertEqual(self.report('codex', {}, {})['memory_state'], 'disabled')
        result = self.report('codex', notification(error='SECRET', prompt='SECRET', url='SECRET'))
        self.assertEqual(set(result), {'schema_version', 'client', 'server', 'memory_state', 'diagnostic', 'next_action'})
        self.assertNotIn('SECRET', json.dumps(result))


class PackagedMemoryStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.base = Path(cls.tmp.name).resolve()
        cls.packages = {client: build(ROOT, cls.base / client, client) for client in ('codex', 'cursor', 'claude')}
        cls.home = cls.base / 'home'
        cls.home.mkdir()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def run_helper(self, client, data='', package=None):
        root = package or self.packages[client]
        return subprocess.run([str(root / 'bin/nda-plugin'), 'memory-status', '--client', client],
                              input=data, text=True, capture_output=True, cwd=self.home,
                              env={**os.environ, 'HOME': str(self.home)}, timeout=15)

    def test_packaged_cli_classifies_without_project_setup_or_state_writes(self):
        for client, data, expected in (
                ('codex', notification(failureReason='reauthenticationRequired'), 'awaiting_authentication'),
                ('claude', {'name': SERVER, 'status': 'needs-auth'}, 'awaiting_authentication'),
                ('cursor', notification(failureReason='reauthenticationRequired'), 'pending_native_diagnostic')):
            with self.subTest(client=client):
                run = self.run_helper(client, json.dumps(data))
                self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
                self.assertEqual(json.loads(run.stdout)['memory_state'], expected)
                self.assertEqual(list(self.home.iterdir()), [])

    def test_invalid_input_is_bounded_and_sanitized(self):
        for data in ('SECRET {', '["SECRET"]', '"SECRET"', '{"error":"' + 'x' * 1_000_001,
                     '{"error":"' + 'é' * 600_000 + '"}', '[' * 2000):
            with self.subTest(size=len(data)):
                run = self.run_helper('codex', data)
                self.assertEqual(run.returncode, 2)
                result = json.loads(run.stdout)
                self.assertEqual(result['diagnostic'], 'invalid_native_diagnostic')
                self.assertEqual(result['memory_state'], 'pending_native_diagnostic')
                self.assertNotIn('SECRET', run.stdout + run.stderr)
                self.assertLess(len(run.stdout + run.stderr), 2000)

    def test_empty_input_and_disabled_package(self):
        self.assertEqual(json.loads(self.run_helper('codex').stdout)['memory_state'], 'pending_native_diagnostic')
        package = build(ROOT, self.base / 'disabled', 'codex', memory_endpoints={})
        run = self.run_helper('codex', package=package)
        self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
        self.assertEqual(json.loads(run.stdout)['memory_state'], 'disabled')

    def test_terminal_stdin_never_waits_for_input(self):
        from nda_harness.plugin_runtime import read_memory_diagnostic

        class Terminal(io.StringIO):
            def isatty(self):
                return True

            def read(self, *args):
                raise AssertionError('Must not read a terminal')

        self.assertEqual(read_memory_diagnostic(Terminal()), (None, False))

    def test_client_guidance_reaches_packages_and_runtime_without_payload_text(self):
        from nda_harness.plugin_runtime import hook
        for client, marker in [('codex', 'reauthenticationRequired'), ('claude', 'needs-auth'),
                               ('cursor', 'agent mcp login')]:
            package = self.packages[client]
            event = 'sessionStart' if client == 'cursor' else 'UserPromptSubmit'
            with patch('nda_harness.plugin_runtime.bootstrap', return_value={'state': 'failed'}), \
                    patch('nda_harness.plugin_runtime.context', return_value={'status': 'ready'}):
                output, code = hook(package, client, event, self.home,
                                    {'cwd': str(self.home), 'diagnostic': {'error': 'SECRET'}})
            text = json.dumps(output)
            self.assertEqual(code, 0)
            self.assertIn(marker, text)
            self.assertNotIn('SECRET', text)
            self.assertNotIn('reauthenticationRequired', text if client != 'codex' else '')
            self.assertNotIn('needs-auth', text if client != 'claude' else '')
            for name in ('hindsight-memory', 'session-bootstrap', 'nda-verify'):
                skill = (package / 'skills' / name / 'SKILL.md').read_text()
                self.assertIn(marker, skill)
                self.assertNotIn('@AUTH_GUIDANCE@', skill)
                self.assertIn('memory-status', skill)
            if client == 'cursor':
                rule = (package / 'rules/nda-harness.mdc').read_text()
                self.assertIn(marker, rule)
                self.assertNotIn('reauthenticationRequired', rule)
                self.assertNotIn('needs-auth', rule)


if __name__ == '__main__':
    unittest.main()
