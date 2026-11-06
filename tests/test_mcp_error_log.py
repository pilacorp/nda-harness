import concurrent.futures
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))

from nda_harness.mcp_error_log import record_failure
from nda_harness import jev_mcp, plugin_runtime


class MCPErrorLogTests(unittest.TestCase):
    def test_jev_logs_terminal_failure_once_and_preserves_result_on_io_error(self):
        def wire(engine):
            messages = [
                {'id': 1, 'method': 'initialize', 'params': {
                    'protocolVersion': jev_mcp.PROTOCOL, 'capabilities': {},
                    'clientInfo': {'name': 'fixture', 'version': '1'}}},
                {'method': 'notifications/initialized'},
                {'id': 2, 'method': 'tools/call', 'params': {'name': 'selection_verify'}},
            ]
            incoming = io.BytesIO(b''.join(jev_mcp._encoded({'jsonrpc': '2.0', **row})
                                           for row in messages))
            outgoing = io.BytesIO()
            jev_mcp.serve(engine, incoming, outgoing)
            return outgoing.getvalue()

        with tempfile.TemporaryDirectory() as tmp:
            engine = jev_mcp.Engine('codex')
            engine.home = Path(tmp).resolve()
            log = engine.home / 'logs/mcp-errors.jsonl'
            with patch.object(jev_mcp.Engine, '__call__', return_value={'status': 'ready'}):
                wire(engine)
            with patch.object(jev_mcp.Engine, '__call__', return_value=jev_mcp.blocked('uncertain_decision')):
                wire(engine)
            self.assertFalse(log.exists())
            with patch.object(jev_mcp.Engine, '__call__', return_value=jev_mcp.blocked('authorization_failed')):
                expected = wire(engine)
                with patch('nda_harness.mcp_error_log._append', side_effect=PermissionError):
                    self.assertEqual(wire(engine), expected)
            rows = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['error_code'], 'authentication_required')
            self.assertEqual(rows[0]['plugin_version'], 'unknown')

    def test_hindsight_native_failure_and_rag_recorder(self):
        native = {'method': 'mcpServer/startupStatus/updated', 'params': {
            'name': 'nda-harness-hindsight', 'status': 'failed',
            'failureReason': 'reauthenticationRequired', 'detail': 'fixture secret'}}
        config = {'memory_systems': {'endpoints': {'hindsight': 'https://example.test/mcp/'}}}
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve()
            log = home / '.nda-harness/logs/mcp-errors.jsonl'
            with patch.object(Path, 'home', return_value=home), patch.object(
                    plugin_runtime, 'package_config', return_value=config), contextlib.redirect_stdout(io.StringIO()):
                with patch('sys.stdin', io.StringIO('{}')):
                    self.assertEqual(plugin_runtime.main(['memory-status', '--client', 'codex']), 0)
                self.assertFalse(log.exists())
                with patch('sys.stdin', io.StringIO(json.dumps(native))):
                    self.assertEqual(plugin_runtime.main(['memory-status', '--client', 'codex']), 0)
                self.assertEqual(plugin_runtime.main([
                    'mcp-error-record', '--client', 'codex', '--server', 'nda-harness-nda-rag',
                    '--operation', 'get_page', '--error-code', 'timeout']), 0)
            rows = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual([(row['server'], row['operation'], row['error_code']) for row in rows], [
                ('nda-harness-hindsight', 'startup', 'authentication_required'),
                ('nda-harness-nda-rag', 'get_page', 'timeout'),
            ])
            self.assertNotIn('fixture secret', log.read_text())

    def test_private_concurrent_records_and_package_versions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            state = root / 'state'
            package = root / 'package'
            package.mkdir()
            metadata = package / 'nda-plugin.json'
            metadata.write_text('{"version":"1.2.3"}')
            log = state / 'logs/mcp-errors.jsonl'
            self.assertEqual(record_failure(state, package, 'codex', 'nda-harness-jev',
                                            'select_skills', 'secret'), 'invalid_event')
            self.assertFalse(log.exists())
            self.assertEqual(record_failure(state, package, 'codex', 'nda-harness-jev',
                                            'select_skills', 'timeout'), 'recorded')
            metadata.write_text('{"version":"2.0.0"}')
            events = [('nda-harness-hindsight', 'recall'), ('nda-harness-nda-rag', 'search_docs')] * 16
            with concurrent.futures.ThreadPoolExecutor() as pool:
                outcomes = list(pool.map(lambda event: record_failure(
                    state, package, 'cursor', *event, 'transport_error'), events))
            self.assertEqual(outcomes, ['recorded'] * len(events))
            metadata.write_text('{"version":"secret/path"}')
            self.assertEqual(record_failure(state, package, 'claude', 'nda-harness-nda-rag',
                                            'get_page', 'invalid_response'), 'recorded')
            lines = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(len(lines), 34)
            self.assertEqual(lines[0], {'timestamp': lines[0]['timestamp'], 'client': 'codex',
                                        'plugin_version': '1.2.3', 'server': 'nda-harness-jev',
                                        'operation': 'select_skills', 'error_code': 'timeout'})
            self.assertTrue(lines[0]['timestamp'].endswith('Z'))
            self.assertEqual({row['plugin_version'] for row in lines[1:-1]}, {'2.0.0'})
            self.assertEqual(lines[-1]['plugin_version'], 'unknown')
            self.assertNotIn('secret', log.read_text())
            self.assertEqual(log.stat().st_mode & 0o777, 0o600)
            self.assertEqual(log.parent.stat().st_mode & 0o777, 0o700)

    def test_rejects_symlinks_and_fifo(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp).resolve()
            directory = state / 'logs'
            directory.symlink_to(state, target_is_directory=True)
            args = (state, state, 'codex', 'nda-harness-hindsight', 'startup', 'timeout')
            self.assertEqual(record_failure(*args), 'local_write_failed')
            directory.unlink()
            directory.mkdir(mode=0o700)
            log = directory / 'mcp-errors.jsonl'
            target = state / 'target'
            target.write_text('preserve')
            log.symlink_to(target)
            self.assertEqual(record_failure(*args), 'local_write_failed')
            self.assertEqual(target.read_text(), 'preserve')
            log.unlink()
            os.mkfifo(log)
            self.assertEqual(record_failure(*args), 'local_write_failed')
