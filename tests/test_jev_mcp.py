"""Jev stdio protocol and installed-package boundary fixtures (no paid calls)."""
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
from nda_harness import jev_mcp
from nda_harness.plugin_build import build, build_archive


def request(method, params=None, ident=1):
    value = {'jsonrpc': '2.0', 'method': method}
    if ident is not None:
        value['id'] = ident
    if params is not None:
        value['params'] = params
    return value


INIT = request('initialize', {'protocolVersion': 'future', 'capabilities': {}, 'clientInfo': {'name': 'fixture', 'version': '1'}})
READY = request('notifications/initialized', ident=None)
TASK = {'schema_version': 1, 'request': 'Implement the local adapter', 'stage': 'implementation',
        'project_facts': {'stack': [], 'deliverables': [], 'constraints': []}}


class ProtocolTests(unittest.TestCase):
    def run_wire(self, messages, handler=None):
        incoming = io.BytesIO(b''.join((json.dumps(m).encode() + b'\n') if not isinstance(m, bytes) else m for m in messages))
        outgoing, errors = io.BytesIO(), io.StringIO()
        jev_mcp.serve(handler or (lambda name, args: {'status': 'ready', 'implementation_authorized': False}), incoming, outgoing, errors)
        return [json.loads(line) for line in outgoing.getvalue().splitlines()], errors.getvalue()

    def test_lifecycle(self):
        output, errors = self.run_wire([INIT, READY, request('ping'), request('tools/list')])
        self.assertEqual(errors, '')
        self.assertEqual(output[0]['result']['protocolVersion'], '2025-06-18')
        self.assertEqual(output[0]['result']['capabilities'], {'tools': {}})
        tools = output[-1]['result']['tools']
        self.assertEqual([t['name'] for t in tools], ['select_skills', 'record_selection', 'load_selected_skills', 'selection_verify'])
        self.assertTrue(all(t['inputSchema']['additionalProperties'] is False for t in tools))

    def test_errors_do_not_dispatch_or_answer_notifications(self):
        handler = unittest.mock.Mock()
        output, _ = self.run_wire([request('tools/list'), b'{secret\n', [], INIT, READY,
            request('unknown'), request('tools/call', {'name': 'selection_verify', 'arguments': {'live': 1}}),
            request('tools/call', {'name': 'selection_verify', 'arguments': {'home': '/private'}}),
            request('tools/call', {'name': 'selection_verify'}, ident=None)], handler)
        self.assertEqual([v['error']['code'] for v in output if 'error' in v], [-32600, -32700, -32600, -32601, -32602, -32602])
        handler.assert_not_called()
        self.assertNotIn('secret', json.dumps(output))

    def test_invalid_envelopes_and_strict_task_fields(self):
        handler = unittest.mock.Mock()
        messages = [INIT, READY, request('tools/call', {'name': 'unknown'}),
            request('tools/call', {'name': 'select_skills', 'arguments': {'project': str(ROOT), 'session': 's', 'task': {**TASK, 'extra': 1}}}),
            request('tools/call', {'name': 'select_skills', 'arguments': {'project': '.', 'session': 's', 'task': TASK}}),
            request('tools/call', {'name': 'load_selected_skills', 'arguments': {'project': str(ROOT), 'session': True, 'task': TASK}}),
            {'jsonrpc': '2.0', 'method': 'ping', 'id': True},
            {'jsonrpc': '2.0', 'method': 'ping', 'id': None},
            {'jsonrpc': '2.0', 'method': 'ping', 'id': '\ud800'},
            b'\xff\n']
        output, errors = self.run_wire(messages, handler)
        self.assertEqual(len(output), 9)
        self.assertTrue(all('error' in value for value in output[1:]))
        handler.assert_not_called()
        self.assertEqual(errors, '')

    def test_bounded_lines_and_responses(self):
        output, errors = self.run_wire([b'x' * (jev_mcp.MAX_LINE + 1) + b'\n', INIT])
        self.assertEqual(output, [])
        self.assertIn('request_too_large', errors)
        output, _ = self.run_wire([INIT, READY, request('tools/call', {'name': 'selection_verify'})],
            lambda *_: {'status': 'ready', 'skills': ['private-body' * jev_mcp.MAX_RESPONSE]})
        self.assertEqual(json.loads(output[-1]['result']['content'][0]['text'])['diagnostic'], 'response_too_large')
        self.assertNotIn('private-body', json.dumps(output))

    def test_exception_is_sanitized_and_workflow_is_success(self):
        for report, expected in [({'status': 'needs_context', 'diagnostic': 'local_agent'}, False),
                                 ({'status': 'blocked', 'diagnostic': 'credential_unavailable'}, True)]:
            output, _ = self.run_wire([INIT, READY, request('tools/call', {'name': 'selection_verify'})], lambda *_: report)
            self.assertEqual(output[-1]['result']['isError'], expected)
        def fail(*_):
            raise RuntimeError('/private/key Bearer fake-secret provider-body')
        output, errors = self.run_wire([INIT, READY, request('tools/call', {'name': 'selection_verify'})], fail)
        self.assertEqual(json.loads(output[-1]['result']['content'][0]['text'])['diagnostic'], 'internal_error')
        self.assertNotIn('fake-secret', json.dumps(output) + errors)
        for malformed in ({'status': 'ready', 'value': float('nan')}, {'status': 'ready', 'value': '\ud800'}):
            output, errors = self.run_wire([INIT, READY, request('tools/call', {'name': 'selection_verify'})], lambda *_: malformed)
            self.assertEqual(json.loads(output[-1]['result']['content'][0]['text'])['diagnostic'], 'internal_error')


class InstalledTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='jev paths with spaces ')
        cls.root = Path(cls.temp.name).resolve()
        cls.packages = {c: build(ROOT, cls.root / c, c) for c in ('codex', 'cursor', 'claude')}

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_launchers_and_archive_relocate_with_inherited_marker(self):
        import zipfile
        archive = build_archive(ROOT, self.root / 'claude.zip', 'claude')
        extracted = self.root / 'hosted archive'
        with zipfile.ZipFile(archive) as z:
            z.extractall(extracted)
            mode = z.getinfo('scripts/nda-plugin').external_attr >> 16
            self.assertTrue(mode & 0o111)
        (extracted / 'scripts/nda-plugin').chmod(0o755)
        for client, package in [*self.packages.items(), ('claude', extracted)]:
            with self.subTest(client=client, package=package):
                config = json.loads((package / ('mcp.json' if client == 'cursor' else '.mcp.json')).read_text())['mcpServers']
                entry = config['nda-harness-jev']
                self.assertEqual(entry.get('type'), None if client == 'cursor' else 'stdio')
                self.assertIn('url', config['nda-harness-context7'])
                if client == 'codex':
                    # Codex resolves relative cwd from the plugin root and passes command literally.
                    cwd = package / entry['cwd'] if 'cwd' in entry else '/'
                    launcher = package / 'bin/nda-plugin'
                    command = [entry['command'], *entry['args']]
                else:
                    self.assertEqual(entry['args'], ['selection-mcp', '--client', client])
                    cwd = '/'
                    relative = entry['command'].split('}', 1)[1].lstrip('/')
                    launcher = package / relative
                    command = [str(launcher), *entry['args']]
                ids = [v['id'] for v in json.loads((package / 'skills/catalog.json').read_text())['skills']]
                base = {'project': str(self.root), 'session': 'fixture', 'task': TASK}
                messages = [INIT, READY, request('tools/list', ident=2),
                    request('tools/call', {'name': 'selection_verify', 'arguments': {'live': False}}, ident=3),
                    request('tools/call', {'name': 'select_skills', 'arguments': base}, ident=4),
                    request('tools/call', {'name': 'select_skills', 'arguments': {**base, 'answers': {i: {'type': 'noul', 'noul': 1} for i in ids}}}, ident=5),
                    request('tools/call', {'name': 'load_selected_skills', 'arguments': base}, ident=6)]
                with tempfile.TemporaryDirectory() as home:
                    env = {**os.environ, 'HOME': home, 'CODEX_SANDBOX': 'seatbelt'}
                    result = subprocess.run(command, input=''.join(json.dumps(m) + '\n' for m in messages),
                        text=True, capture_output=True, env=env, cwd=cwd, timeout=30)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stderr, '')
                    output = [json.loads(v) for v in result.stdout.splitlines()]
                    reports = [json.loads(v['result']['content'][0]['text']) for v in output if 'content' in v.get('result', {})]
                    self.assertEqual(reports[0]['diagnostic'], 'credential_missing')
                    self.assertEqual(reports[1]['diagnostic'], 'local_agent')
                    self.assertNotIn('skills', reports[2])
                    self.assertEqual(reports[2]['status'], 'ready')
                    self.assertEqual(len(reports[3]['skills']), len(ids))
                    self.assertLess(max(len(v.encode()) + 1 for v in result.stdout.splitlines()), jev_mcp.MAX_RESPONSE)
                    # Same installed CLI still refuses; server did not alter environment policy.
                    cli = subprocess.run([str(launcher), 'selection-verify', '--client', client],
                        text=True, capture_output=True, env=env, timeout=30)
                    self.assertEqual(json.loads(cli.stdout)['diagnostic'], 'sandbox_rerun')
                    reconnect = [INIT, READY, request('tools/call', {'name': 'select_skills', 'arguments': base})]
                    again = subprocess.run(command,
                        input=''.join(json.dumps(m) + '\n' for m in reconnect), text=True,
                        capture_output=True, env=env, cwd=cwd, timeout=30)
                    self.assertEqual(again.returncode, 0, again.stderr)
                    cached = json.loads(json.loads(again.stdout.splitlines()[-1])['result']['content'][0]['text'])
                    self.assertEqual(cached['source'], 'cache')

    def engine(self, home):
        engine = jev_mcp.Engine('codex')
        engine.package = self.packages['codex']
        engine.home = Path(home).resolve() / '.nda-harness'
        return engine

    def test_provider_cache_cli_parity_uncertainty_and_integrity(self):
        from nda_harness.credentials import FileCredentialStore, _ensure_generation
        from nda_harness.skill_selection import select_skills, load_catalog
        with tempfile.TemporaryDirectory() as home:
            engine = self.engine(home)
            keychain = FileCredentialStore(engine.home)
            keychain.write('fake-fixture-key')
            _ensure_generation(engine.home)
            catalog = load_catalog(engine.package / 'skills')
            ids = [v['id'] for v in catalog['skills']]
            probabilities = {i: (0.5 if n == 0 else 0.1) for n, i in enumerate(ids)}
            calls = []
            def provider(payload, secret, **kwargs):
                calls.append(payload)
                return {'answers': {i: {'type': 'noul', 'noul': p} for i, p in probabilities.items()}, 'model': 'typesafe/jev-1.14', 'provider_request_id': 'fixture', 'usage': None}
            args = {'project': str(self.root), 'session': 'provider', 'task': TASK}
            with patch('nda_harness.openrouter.post_decision', side_effect=provider):
                first = engine('select_skills', args)
                self.assertEqual(first['diagnostic'], 'uncertain_decision')
                wrong = engine('record_selection', {**args, 'decisions': {'wrong-id': True}})
                self.assertEqual(wrong['status'], 'blocked')
                resolved = engine('record_selection', {**args, 'decisions': {ids[0]: True}})
                self.assertEqual(resolved['status'], 'ready')
                self.assertEqual(engine('load_selected_skills', args)['status'], 'ready')
                self.assertEqual(engine('select_skills', args)['source'], 'cache')
                manifest = json.loads((engine.package / 'release.json').read_text())['asset_hashes']
                with patch.dict(os.environ, {'CODEX_SANDBOX': ''}):
                    cli, code = select_skills(TASK, project=self.root, session='cli', home=engine.home,
                        catalog_root=engine.package / 'skills', release_manifest=manifest, keychain=keychain)
                self.assertEqual(code, 0)
                self.assertEqual(cli['selected'], resolved['selected'])
                self.assertEqual(cli['source'], 'cache')
                self.assertEqual(len(calls), 1)
                self.assertEqual(engine('selection_verify', {})['status'], 'ready')
                self.assertEqual(len(calls), 1)
                probabilities.clear()
                probabilities['synthetic'] = 1
                engine('selection_verify', {'live': True})
                self.assertEqual(len(calls), 2)
                self.assertNotIn(TASK['request'], json.dumps(calls[-1]))
                self.assertEqual(engine('select_skills', {**args, 'answers': {}})['status'], 'blocked')
                changed = {**args, 'task': {**TASK, 'request': 'different assignment'}}
                self.assertEqual(engine('load_selected_skills', changed)['status'], 'blocked')
                # All input validation precedes credential access.
                with patch.object(FileCredentialStore, 'status', side_effect=AssertionError('secret read')):
                    with self.assertRaises(jev_mcp.InvalidParams):
                        engine('select_skills', {**args, 'endpoint': 'https://evil.test'})
                with patch.object(FileCredentialStore, 'status', side_effect=OSError('private-path')):
                    self.assertEqual(engine('select_skills', {**args, 'answers': {}})['diagnostic'], 'credential_unavailable')
                (engine.package / 'skills/catalog.json').write_text('{}')
                try:
                    self.assertEqual(engine('selection_verify', {})['diagnostic'], 'package_integrity_failed')
                finally:
                    (engine.package / 'skills/catalog.json').write_bytes((ROOT / 'skills/catalog.json').read_bytes())

    def test_confident_and_empty_decisions_match_cli_and_state_denial_is_sanitized(self):
        from nda_harness.credentials import FileCredentialStore, _ensure_generation
        from nda_harness.skill_selection import select_skills, load_catalog
        from nda_harness.files import Conflict
        for probability in (0.0, 1.0):
            with self.subTest(probability=probability), tempfile.TemporaryDirectory() as home:
                engine = self.engine(home)
                keychain = FileCredentialStore(engine.home)
                keychain.write('fixture-key')
                _ensure_generation(engine.home)
                ids = [item['id'] for item in load_catalog(engine.package / 'skills')['skills']]
                result = {'answers': {i: {'type': 'noul', 'noul': probability} for i in ids}, 'model': 'typesafe/jev-1.14'}
                args = {'project': str(self.root), 'session': 'p', 'task': TASK}
                with patch('nda_harness.openrouter.post_decision', return_value=result) as provider:
                    mcp = engine('select_skills', args)
                    manifest = json.loads((engine.package / 'release.json').read_text())['asset_hashes']
                    with patch.dict(os.environ, {'CODEX_SANDBOX': ''}):
                        cli, code = select_skills(TASK, project=self.root, session='cli', home=engine.home,
                            catalog_root=engine.package / 'skills', release_manifest=manifest, keychain=keychain)
                    self.assertEqual(code, 0)
                    self.assertEqual(mcp['selected'], cli['selected'])
                    self.assertEqual(len(mcp['selected']), len(ids) if probability else 0)
                    self.assertEqual(provider.call_count, 1)
                with patch('nda_harness.jev_mcp._select_skills_engine', side_effect=Conflict('/private fixture-secret')):
                    wire = ProtocolTests()
                    output, errors = wire.run_wire([INIT, READY, request('tools/call', {'name': 'select_skills', 'arguments': args})], engine)
                    self.assertEqual(json.loads(output[-1]['result']['content'][0]['text'])['diagnostic'], 'private_state_unavailable')
                    self.assertNotIn('fixture-secret', json.dumps(output) + errors)

    def test_symlink_key_does_not_become_local_agent(self):
        with tempfile.TemporaryDirectory() as home:
            engine = self.engine(home)
            state = engine.home / 'skill-selection'
            state.mkdir(parents=True)
            (state / 'openrouter-key').symlink_to(self.root / 'missing')
            report = engine('select_skills', {'project': str(self.root), 'session': 's', 'task': TASK})
            self.assertEqual(report['diagnostic'], 'credential_unavailable')


if __name__ == '__main__':
    unittest.main()
