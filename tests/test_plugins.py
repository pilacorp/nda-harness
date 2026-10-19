"""Phase-0 plugin contracts, exercised with disposable homes and real Git."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from nda_harness.plugin_build import build, validate_endpoint
from nda_harness.project import configure, inspect_project, project_identity, state_for
from nda_harness.plugin_runtime import bootstrap, verify, hook
from nda_harness.files import Conflict, Plan, atomic, json_bytes


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / 'home'
        self.home.mkdir()
        self.project = self.base / 'project with spaces'
        self.project.mkdir()
        self.env = {**os.environ, 'HOME': str(self.home), 'GIT_CONFIG_GLOBAL': '/dev/null',
                    'GIT_AUTHOR_NAME': 'Test', 'GIT_COMMITTER_NAME': 'Test',
                    'GIT_AUTHOR_EMAIL': 'test@example.test', 'GIT_COMMITTER_EMAIL': 'test@example.test'}
        self.git('init', '-q')
        self.git('remote', 'add', 'origin', 'git@github.com:example/project.git')
        self.package = self.base / 'codex'
        build(ROOT, self.package, 'codex')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.project), *args], env=self.env, text=True, capture_output=True)

    def setup(self, command=None, skip=False):
        return configure(self.project, self.package, self.home, command, skip=skip)

    def commit(self):
        (self.project / 'fixture').write_text('test')
        self.git('add', 'fixture')
        return self.git('commit', '-m', 'test')

    def test_reproducible_complete_packages_and_native_clients(self):
        other = self.base / 'other'
        build(ROOT, other, 'codex')
        def tree(root):
            return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}
        self.assertEqual(tree(self.package), tree(other))
        self.assertTrue((self.package / 'skills/test-driven-development/SKILL.md').is_file())
        self.assertTrue((self.package / 'skills/diagram-design/assets/example-loop.html').is_file())
        self.assertFalse((self.package / 'scripts/nda_harness/hindsight.py').exists())
        mcp = json.loads((self.package / '.mcp.json').read_text())['mcpServers']
        self.assertEqual(mcp['NDA Hindsight'], {'type': 'http', 'url': 'https://hindsight-api.pila.vn/mcp/'})
        services = json.loads((self.package / 'nda-plugin.json').read_text())['memory_systems']['services']['hindsight']
        self.assertEqual(services, {'mcp': 'https://hindsight-api.pila.vn/mcp/', 'oauth': 'https://hindsight-api.pila.vn', 'rest': 'https://hindsight-api.pila.vn'})
        cursor = self.base / 'cursor'
        build(ROOT, cursor, 'cursor', 'https://memory.example.test/mcp/')
        self.assertEqual(json.loads((cursor / 'mcp.json').read_text())['mcpServers']['NDA Hindsight'], {'url': 'https://memory.example.test/mcp/'})
        hooks = json.loads((cursor / 'hooks/hooks.json').read_text())['hooks']
        self.assertIn('sessionStart', hooks)
        self.assertNotIn('SessionStart', hooks)
        self.assertEqual(len(hooks['sessionStart']), 1)
        for package, manifest_path in ((self.package, '.codex-plugin/plugin.json'), (cursor, '.cursor-plugin/plugin.json')):
            manifest = json.loads((package / manifest_path).read_text())
            self.assertEqual(manifest['name'], 'nda-harness')
            self.assertEqual(manifest['displayName'], 'NDA Harness')
            self.assertNotIn('cursor', manifest['name'])
            self.assertNotIn('codex', manifest['name'])
        logo = (ROOT / 'plugin/assets/logo.jpg').read_bytes()
        self.assertEqual((self.package / 'assets/logo.jpg').read_bytes(), logo)
        self.assertEqual((cursor / 'assets/logo.jpg').read_bytes(), logo)
        codex_manifest = json.loads((self.package / '.codex-plugin/plugin.json').read_text())
        self.assertEqual(codex_manifest['interface']['logo'], './assets/logo.jpg')
        self.assertEqual(codex_manifest['interface']['composerIcon'], './assets/logo.jpg')
        self.assertEqual(json.loads((cursor / '.cursor-plugin/plugin.json').read_text())['logo'], 'assets/logo.jpg')
        intro = (cursor / 'skills/using-superpowers/SKILL.md').read_text()
        self.assertNotIn('superpowers:', intro.replace('nda-harness:', ''))
        self.assertNotIn('nda-harness-cursor:', intro)
        self.assertNotIn('nda-harness-codex:', intro)
        self.assertTrue((cursor / 'vendor/superpowers/hooks/session-start').is_file())
        memory = self.base / 'codex-memory'
        build(ROOT, memory, 'codex', 'https://memory.example.test/mcp/')
        payload = {'cwd': str(self.project)}
        with patch('nda_harness.plugin_runtime.prepare_rtk', return_value=Path('/rtk')), patch.dict(os.environ, self.env), patch('pathlib.Path.home', return_value=self.home):
            started, start_code = hook(memory, 'codex', 'SessionStart', self.home, payload)
            prompted, prompt_code = hook(memory, 'codex', 'UserPromptSubmit', self.home, payload)
            cursor_started, cursor_code = hook(cursor, 'cursor', 'sessionStart', self.home, payload)
        self.assertEqual((start_code, prompt_code, cursor_code), (0, 0, 0))
        texts = (
            started['hookSpecificOutput']['additionalContext'],
            prompted['hookSpecificOutput']['additionalContext'],
            cursor_started['additional_context'],
        )
        for text in texts:
            self.assertIn('create_bank', text)
            self.assertIn('rtk --version', text)
            self.assertIn('resolve-library-id', text)
            self.assertIn('query-docs', text)
        provider = (memory / 'scripts/nda_harness/memory.py').read_text()
        self.assertIn('create_bank', provider)
        runtime = (memory / 'scripts/nda_harness/plugin_runtime.py').read_text()
        self.assertIn('session_instruction', runtime)
        self.assertIn('resolve-library-id', runtime)
        self.assertIn('list_banks', (memory / 'skills/session-bootstrap/SKILL.md').read_text())

    def test_project_uses_one_selected_memory_system(self):
        from nda_harness.memory import SYSTEMS, packaged, select_system, session_instruction
        example = {'label': 'Example', 'skill': 'example-memory', 'server': 'example-memory',
                   'tools': ('remember',), 'session': 'Example memory is selected. Load example-memory.'}
        SYSTEMS['example-memory'] = example
        self.addCleanup(SYSTEMS.pop, 'example-memory', None)
        both = {'memory_systems': {'endpoints': {
            'hindsight': 'https://memory.example.test/mcp/',
            'example-memory': 'https://example.example.test/mcp/'}}}
        with self.assertRaises(Conflict):
            select_system(both)
        self.assertEqual(select_system(both, requested='example-memory'), 'example-memory')
        self.assertIn('Example memory is selected', session_instruction(both, 'example-memory'))
        self.assertIn('--memory-system', session_instruction(both))
        self.assertEqual(select_system({'hindsight_mcp_url': 'https://memory.example.test/mcp/'}), 'hindsight')
        self.assertIsNone(select_system({'memory_systems': {'endpoints': {}}}))

        single = self.base / 'one-memory'
        build(ROOT, single, 'codex', 'https://memory.example.test/mcp/')
        configure(self.project, single, self.home, skip=True)
        profile = json.loads((self.project / '.nda-harness/profile.json').read_text())
        self.assertEqual(profile['memory']['system'], 'hindsight')
        self.assertEqual(packaged(json.loads((single / 'nda-plugin.json').read_text())),
                         {'hindsight': 'https://memory.example.test/mcp/'})

        several = self.base / 'several-memory'
        build(ROOT, several, 'codex', 'https://memory.example.test/mcp/')
        config_path = several / 'nda-plugin.json'
        config = json.loads(config_path.read_text())
        config['memory_systems']['endpoints']['example-memory'] = 'https://example.example.test/mcp/'
        config_path.write_text(json.dumps(config))
        other = self.base / 'other-project'
        other.mkdir()
        subprocess.run(['git', '-C', str(other), 'init', '-q'], env=self.env, check=True)
        subprocess.run(['git', '-C', str(other), 'remote', 'add', 'origin', 'git@github.com:example/other.git'], env=self.env, check=True)
        with self.assertRaises(Conflict):
            configure(other, several, self.home, skip=True)
        self.assertFalse((other / '.nda-harness/profile.json').exists())
        configure(other, several, self.home, skip=True, system='example-memory')
        chosen = json.loads((other / '.nda-harness/profile.json').read_text())
        self.assertEqual(chosen['memory']['system'], 'example-memory')
        self.assertIn('bank_id', chosen['memory'])

    def test_repository_packages_are_built_codex_and_cursor_only(self):
        packages = ROOT / 'packages'
        self.assertFalse((packages / 'nda-harness-claude').exists())

        def tree(root):
            return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}

        self.assertEqual(tree(packages / 'nda-harness-codex'), tree(self.package))
        cursor = self.base / 'cursor-committed'
        build(ROOT, cursor, 'cursor')
        self.assertEqual(tree(packages / 'nda-harness-cursor'), tree(cursor))
        for client, manifest in (('codex', '.mcp.json'), ('cursor', 'mcp.json')):
            servers = json.loads((packages / f'nda-harness-{client}' / manifest).read_text())['mcpServers']
            self.assertEqual(servers['NDA Hindsight']['url'], 'https://hindsight-api.pila.vn/mcp/')
            self.assertNotIn('Authorization', json.dumps(servers))

    def test_claude_package_matches_shared_engine_and_native_hooks(self):
        claude = self.base / 'claude'
        codex = self.base / 'codex-memory'
        endpoint = 'https://memory.example.test/mcp/'
        build(ROOT, claude, 'claude', endpoint)
        build(ROOT, codex, 'codex', endpoint)

        def files(root):
            return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob('*') if p.is_file()}

        claude_files, codex_files = files(claude), files(codex)
        self.assertEqual(set(claude_files) - set(codex_files), {'.claude-plugin/plugin.json', '.claude-plugin/marketplace.json'})
        self.assertEqual(set(codex_files) - set(claude_files), {'.codex-plugin/plugin.json', '.agents/plugins/marketplace.json'})
        bound = {f'skills/{name}/SKILL.md' for name in (
            'nda-setup', 'nda-verify', 'session-bootstrap', 'task-prepare', 'context-refresh', 'context-checkpoint', 'context-resume')}
        differ = bound | {'hooks/hooks.json', 'nda-plugin.json', 'release.json'}
        for name in set(claude_files) & set(codex_files) - differ:
            self.assertEqual(claude_files[name], codex_files[name], name)
        self.assertEqual(claude_files['.mcp.json'], codex_files['.mcp.json'])
        self.assertFalse((claude / 'rules/nda-harness.mdc').exists())
        self.assertFalse((claude / 'CLAUDE.md').exists())

        manifest = json.loads(claude_files['.claude-plugin/plugin.json'])
        self.assertEqual(manifest['name'], 'nda-harness')
        self.assertEqual(manifest['author'], {'name': 'NDA Harness'})
        self.assertEqual(manifest['logo'], './assets/logo.jpg')
        self.assertEqual((claude / 'assets/logo.jpg').read_bytes(), (ROOT / 'plugin/assets/logo.jpg').read_bytes())
        self.assertNotIn('hooks', manifest)
        self.assertNotIn('mcpServers', manifest)
        self.assertNotIn('skills', manifest)
        market = json.loads(claude_files['.claude-plugin/marketplace.json'])
        self.assertEqual(market['name'], 'nda-harness-local')
        self.assertEqual(market['owner'], {'name': 'NDA Harness'})
        self.assertEqual(market['plugins'][0]['source'], '.')
        servers = json.loads(claude_files['.mcp.json'])['mcpServers']
        self.assertEqual(servers['NDA Hindsight'], {'type': 'http', 'url': endpoint})
        self.assertEqual(servers['nda-harness-context7']['type'], 'http')
        for server in servers.values():
            self.assertNotIn('headers', server)
            self.assertNotIn('Authorization', json.dumps(server))
        hooks = json.loads(claude_files['hooks/hooks.json'])['hooks']
        self.assertEqual(set(hooks), {'SessionStart', 'UserPromptSubmit', 'PreCompact'})
        for event, entries in hooks.items():
            self.assertEqual(len(entries), 1)
            command = entries[0]['hooks']
            self.assertEqual(len(command), 1)
            self.assertIn('${CLAUDE_PLUGIN_ROOT}/bin/nda-plugin', command[0]['command'])
            self.assertIn(f'--client claude --event {event}', command[0]['command'])
            self.assertEqual(command[0]['timeout'], 60 if event == 'SessionStart' else 15)
        setup = (claude / 'skills/nda-setup/SKILL.md').read_text()
        self.assertIn('--client claude', setup)
        self.assertIn('${CLAUDE_PLUGIN_ROOT}', setup)
        self.assertNotIn('@CLIENT@', setup)
        self.assertNotIn('@ROOT@', setup)

        payload = {'cwd': str(self.project), 'prompt': 'SECRET-raw-prompt', 'transcript_path': 'SECRET-path'}
        with patch('nda_harness.plugin_runtime.prepare_rtk', return_value=Path('/rtk')), patch.dict(os.environ, self.env), patch('pathlib.Path.home', return_value=self.home):
            started, start_code = hook(claude, 'claude', 'SessionStart', self.home, payload)
            prompted, prompt_code = hook(claude, 'claude', 'UserPromptSubmit', self.home, payload)
            compact, compact_code = hook(claude, 'claude', 'PreCompact', self.home, payload)
        self.assertEqual((start_code, prompt_code, compact_code), (0, 0, 0))
        self.assertNotIn('decision', compact)
        session_texts = (
            started['hookSpecificOutput']['additionalContext'],
            prompted['hookSpecificOutput']['additionalContext'],
        )
        self.assertEqual(started['hookSpecificOutput']['hookEventName'], 'SessionStart')
        self.assertEqual(prompted['hookSpecificOutput']['hookEventName'], 'UserPromptSubmit')
        rendered = json.dumps({'started': started, 'prompted': prompted, 'compact': compact})
        self.assertNotIn('SECRET', rendered)
        for text in session_texts:
            self.assertIn('create_bank', text)
            self.assertIn('rtk --version', text)
            self.assertIn('resolve-library-id', text)
            self.assertIn('query-docs', text)
            self.assertIn('after resume or compaction', text)
        self.assertIn('context-checkpoint', compact['systemMessage'])
        self.assertIn('context-resume', compact['systemMessage'])

        rejected = subprocess.run([str(claude / 'bin/nda-plugin'), 'hook', '--client', 'claude', '--event', 'sessionStart'],
                                  cwd=self.home, env=self.env, capture_output=True, text=True)
        self.assertEqual(rejected.returncode, 2)
        verified = subprocess.run([str(claude / 'bin/nda-plugin'), 'verify', '--client', 'claude', '--project', str(self.project)],
                                  cwd=self.home, env=self.env, capture_output=True, text=True)
        self.assertEqual(json.loads(verified.stdout)['client'], 'claude')
        self.assertEqual(json.loads(verified.stdout)['memory'], 'disabled')

    def test_claude_project_shares_bank_with_codex_and_cursor(self):
        claude = self.base / 'claude'
        cursor = self.base / 'cursor'
        build(ROOT, claude, 'claude')
        build(ROOT, cursor, 'cursor')
        self.assertEqual(configure(self.project, claude, self.home, skip=True)['status'], 'ready')
        bank = json.loads((self.project / '.nda-harness/profile.json').read_text())['memory']['bank_id']
        for package in (claude, self.package, cursor):
            status = inspect_project(self.project, package, self.home)
            self.assertEqual(status['status'], 'ready')
            self.assertEqual(status['bank_id'], bank)

    def test_endpoint_rejects_secrets_and_nonproduction_http(self):
        for url in ('http://example.test/mcp/', 'https://user:secret@example.test/mcp/',
                    'https://@example.test/mcp/',
                    'https://example.test/mcp/?key=secret', 'https://example.test/mcp/#secret',
                    'https://example.test/banks/test/mcp/', 'https://example.test/mcp',
                    'http://127.0.0.1:8891/mcp/'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                validate_endpoint(url)
        self.assertEqual(validate_endpoint('http://127.0.0.1:8891/mcp/', local_test=True), 'http://127.0.0.1:8891/mcp/')

    def test_pending_is_not_implicit_skip_and_does_not_copy_pack(self):
        result = self.setup()
        self.assertEqual(result['status'], 'needs_configuration')
        self.assertFalse((self.project / '.nda-harness/profile.json').exists())
        self.assertFalse((self.project / '.nda-harness/policy.md').exists())
        self.assertNotEqual(inspect_project(self.project, self.package, self.home)['status'], 'ready')

    def test_explicit_skip_is_committed_config_and_allows_commit(self):
        self.assertEqual(self.setup(skip=True)['status'], 'ready')
        profile = self.project / '.nda-harness/profile.json'
        self.assertEqual(json.loads(profile.read_text())['test_command'], 'true')
        self.assertEqual(self.git('check-ignore', str(profile)).returncode, 1)
        self.assertEqual(self.commit().returncode, 0)
        self.assertEqual(sorted(p.name for p in profile.parent.iterdir()), ['profile.json'])

    def test_failing_tests_and_existing_hook_block_commit(self):
        prior = self.project / '.git/hooks/pre-commit'
        prior.write_text('#!/bin/sh\nprintf prior >> order\n')
        prior.chmod(0o755)
        self.setup('printf harness >> order; false')
        self.assertNotEqual(self.commit().returncode, 0)
        self.assertEqual((self.project / 'order').read_text(), 'priorharness')
        prior.write_text('#!/bin/sh\nexit 1\n')
        self.assertNotEqual(self.commit().returncode, 0)
        self.assertEqual((self.project / 'order').read_text(), 'priorharness')

    def test_idempotent_setup_and_foreign_manager_conflict(self):
        self.setup(skip=True)
        before = self.git('config', '--get', 'core.hooksPath').stdout
        self.setup()
        self.assertEqual(before, self.git('config', '--get', 'core.hooksPath').stdout)
        self.git('config', 'core.hooksPath', '.foreign/hooks')
        with self.assertRaises(Conflict):
            self.setup()
        self.assertEqual(self.git('config', '--get', 'core.hooksPath').stdout.strip(), '.foreign/hooks')

    def test_remote_canonicalization_shared_bank_and_ambiguity(self):
        first = project_identity(self.project)
        self.git('remote', 'set-url', 'origin', 'https://github.com/example/project.git')
        self.assertEqual(first, project_identity(self.project))
        self.setup(skip=True)
        profile = json.loads((self.project / '.nda-harness/profile.json').read_text())
        self.assertNotIn('environment', profile['memory'])
        self.git('remote', 'add', 'fork', 'https://github.com/other/project.git')
        with self.assertRaises(Conflict):
            project_identity(self.project)

    def test_directory_without_git_uses_project_name_and_skips_hooks(self):
        folder = self.base / 'local notes'
        folder.mkdir()
        with self.assertRaises(Conflict):
            configure(folder, self.package, self.home, skip=True)
        self.assertFalse((folder / '.nda-harness/profile.json').exists())
        result = configure(folder, self.package, self.home, skip=True, name='local-notes')
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['protection'], 'not_applicable')
        profile = json.loads((folder / '.nda-harness/profile.json').read_text())
        self.assertEqual(profile['test_command'], 'true')
        self.assertEqual(profile['memory']['name'], 'local-notes')
        self.assertNotIn('remote', profile['memory'])
        status = inspect_project(folder, self.package, self.home)
        self.assertEqual(status['status'], 'ready')
        self.assertEqual(status['protection'], 'not_applicable')
        self.assertEqual(status['bank_id'], profile['memory']['bank_id'])
        run = subprocess.run([str(self.package / 'bin/nda-plugin'), 'session-bootstrap', '--client', 'codex', '--project', str(folder)],
                             env=self.env, cwd=folder, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        report = json.loads(run.stdout)
        self.assertIsNone(report['head'])
        self.assertFalse(report['implementation_authorized'])

    def test_no_remote_needs_name_and_identity_does_not_follow_new_origin(self):
        self.git('remote', 'remove', 'origin')
        with self.assertRaises(Conflict):
            project_identity(self.project)
        a = project_identity(self.project, name='example-app')
        self.assertEqual(a, project_identity(self.project, name='example-app'))
        self.git('remote', 'add', 'origin', 'https://github.com/example/project')
        self.setup(skip=True)
        self.git('remote', 'set-url', 'origin', 'https://github.com/example/other')
        with self.assertRaises(Conflict):
            self.setup()

    def test_failed_activation_rolls_back_config_and_previous_hook(self):
        with patch('nda_harness.project.activate', side_effect=OSError('failure')):
            with self.assertRaises(OSError):
                self.setup(skip=True)
        self.assertFalse((self.project / '.nda-harness/profile.json').exists())
        self.assertEqual(self.git('config', '--get', 'core.hooksPath').returncode, 1)

    def test_verify_is_read_only_and_memory_does_not_gate_core(self):
        self.setup(skip=True)
        with patch('nda_harness.plugin_runtime.prepare_rtk', return_value=Path('/rtk')):
            bootstrap(self.package, 'codex', self.home)
        with patch('nda_harness.plugin_runtime.rtk_identity', return_value=True), patch('nda_harness.plugin_runtime.locate_rtk', return_value=Path('/rtk')):
            before = {str(p): p.read_bytes() for p in self.home.rglob('*') if p.is_file()}
            result = verify(self.package, 'codex', self.project, self.home)
            self.assertEqual(result['core'], 'ready')
            self.assertEqual(result['memory'], 'disabled')
            self.assertEqual(before, {str(p): p.read_bytes() for p in self.home.rglob('*') if p.is_file()})

    def test_installing_failed_or_untrusted_bootstrap_never_reports_core_ready(self):
        self.setup(skip=True)
        with patch('nda_harness.plugin_runtime.rtk_identity', return_value=True), patch('nda_harness.plugin_runtime.locate_rtk', return_value=Path('/rtk')):
            for state in ('awaiting-trust', 'installing', 'failed'):
                atomic(self.home / '.nda-harness/plugin-bootstrap/codex.json', json_bytes({'state': state}))
                self.assertEqual(verify(self.package, 'codex', self.project, self.home)['core'], 'pending')

    def test_bootstrap_failure_is_recoverable_and_separate_from_memory(self):
        with patch('nda_harness.plugin_runtime.prepare_rtk', side_effect=OSError('secret not reported')):
            result = bootstrap(self.package, 'codex', self.home)
        self.assertEqual(result['state'], 'failed')
        self.assertNotIn('secret', json.dumps(result))
        with patch('nda_harness.plugin_runtime.prepare_rtk', return_value=Path('/rtk')):
            result = bootstrap(self.package, 'codex', self.home)
        self.assertEqual(result['state'], 'ready')

    def test_helper_requires_client_and_runs_outside_source_checkout(self):
        command = [str(self.package / 'bin/nda-plugin'), 'verify', '--project', str(self.project)]
        missing = subprocess.run(command, cwd=self.home, env=self.env, capture_output=True, text=True)
        self.assertEqual(missing.returncode, 2)
        self.assertIn('--client', missing.stderr)
        run = subprocess.run([*command, '--client', 'codex'], cwd=self.home, env=self.env, capture_output=True, text=True)
        self.assertNotIn('Traceback', run.stderr)
        self.assertEqual(json.loads(run.stdout)['memory'], 'disabled')

    def test_concurrent_setup_has_one_composed_chain(self):
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self.setup(skip=True), range(2)))
        self.assertTrue(all(r['status'] == 'ready' for r in results))
        self.assertEqual(self.commit().returncode, 0)
        path = Path(self.git('config', '--get', 'core.hooksPath').stdout.strip())
        self.assertEqual((path / 'pre-commit').read_text().count('unit-check'), 1)

    def test_cross_client_protection_and_context_use_shared_config(self):
        self.setup(skip=True)
        cursor = self.base / 'cursor'
        build(ROOT, cursor, 'cursor')
        self.assertEqual(inspect_project(self.project, cursor, self.home)['status'], 'ready')
        before = (self.project / '.nda-harness/profile.json').read_bytes()
        configure(self.project, cursor, self.home)
        self.assertEqual(before, (self.project / '.nda-harness/profile.json').read_bytes())
        self.assertEqual(inspect_project(self.project, self.package, self.home)['status'], 'ready')
        run = subprocess.run([str(cursor / 'bin/nda-plugin'), 'session-bootstrap', '--client', 'cursor', '--project', str(self.project)],
                             env=self.env, cwd=self.home, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertFalse(json.loads(run.stdout)['implementation_authorized'])

    def test_hook_payload_never_promotes_prompt_or_profile_text(self):
        payload = {'cwd': str(self.project), 'prompt': 'SECRET-raw-prompt', 'transcript_path': 'SECRET-path'}
        self.setup('printf SECRET-project-value')
        with patch('nda_harness.plugin_runtime.prepare_rtk', return_value=Path('/rtk')), patch.dict(os.environ, self.env), patch('pathlib.Path.home', return_value=self.home):
            result, code = hook(self.package, 'codex', 'SessionStart', self.home, payload)
        self.assertEqual(code, 0)
        text = json.dumps(result)
        self.assertNotIn('SECRET', text)
        self.assertIn('hookSpecificOutput', result)
        self.assertIn('additionalContext', result['hookSpecificOutput'])
        self.assertIn('rtk --version', text)
        self.assertIn('resolve-library-id', text)
        self.assertIn('query-docs', text)
        self.assertFalse((self.project / 'SECRET-project-value').exists())

    def test_native_cursor_output_and_precompact_reminder(self):
        cursor = self.base / 'cursor'
        build(ROOT, cursor, 'cursor')
        with patch('nda_harness.plugin_runtime.bootstrap', return_value={'state': 'ready'}), patch('nda_harness.plugin_runtime.context', return_value={'status': 'blocked'}):
            output, code = hook(cursor, 'cursor', 'sessionStart', self.home, {'cwd': str(self.project)})
            self.assertEqual(code, 0)
            self.assertIn('additional_context', output)
            self.assertEqual(hook(cursor, 'cursor', 'beforeSubmitPrompt', self.home, {})[0], {'continue': True})
            self.assertEqual(hook(cursor, 'cursor', 'preCompact', self.home, {})[0], {})

    def test_clone_activates_locally_with_same_bank(self):
        self.setup(skip=True)
        self.git('add', '.nda-harness/profile.json')
        self.assertEqual(self.git('commit', '-m', 'project profile').returncode, 0)
        clone = self.base / 'clone'
        subprocess.run(['git', 'clone', '-q', str(self.project), str(clone)], env=self.env, check=True)
        subprocess.run(['git', '-C', str(clone), 'remote', 'set-url', 'origin', 'https://github.com/example/project.git'], env=self.env, check=True)
        self.assertEqual(inspect_project(clone, self.package, self.home)['status'], 'needs_activation')
        original = json.loads((self.project / '.nda-harness/profile.json').read_text())
        configure(clone, self.package, self.home)
        self.assertEqual(inspect_project(clone, self.package, self.home)['bank_id'], original['memory']['bank_id'])

    def test_symlink_profile_and_modified_package_are_rejected(self):
        private = self.home / 'secret'
        private.write_text('SECRET')
        directory = self.project / '.nda-harness'
        directory.mkdir()
        (directory / 'profile.json').symlink_to(private)
        with self.assertRaises(Conflict):
            self.setup(skip=True)
        self.assertEqual(private.read_text(), 'SECRET')
        (self.package / 'pack/policy.md').write_text('modified')
        with self.assertRaises(Conflict):
            verify(self.package, 'codex', self.project, self.home)

    def test_explicit_environment_never_changes_bank(self):
        self.setup(skip=True)
        before = (self.project / '.nda-harness/profile.json').read_bytes()
        command = [str(self.package / 'bin/nda-plugin'), 'verify', '--client', 'codex', '--project', str(self.project)]
        for environment in ('dev', 'staging', 'prod'):
            result = subprocess.run([*command, '--environment', environment], env=self.env, capture_output=True, text=True)
            self.assertEqual(json.loads(result.stdout)['environment'], environment)
            self.assertEqual(before, (self.project / '.nda-harness/profile.json').read_bytes())

    def test_ignored_configuration_is_not_reported_ready(self):
        (self.project / '.gitignore').write_text('.nda-harness/\n')
        with self.assertRaises(Conflict):
            self.setup(skip=True)
        self.assertFalse((self.project / '.nda-harness/profile.json').exists())
        self.assertEqual(self.git('config', '--get', 'core.hooksPath').returncode, 1)

    def test_all_context_operations_and_cross_session_resume(self):
        self.setup(skip=True)
        self.assertEqual(self.commit().returncode, 0)
        task = self.project / '.nda-harness/tasks/plugin/task.md'
        task.parent.mkdir(parents=True)
        spec = self.project / 'specs/feature.md'
        spec.parent.mkdir()
        spec.write_text('# Approved local example\n')
        task.write_text('Issue: https://github.com/example/project/issues/10\nSpec: specs/feature.md\n')
        (self.project / 'AGENTS.md').write_text('SECRET-INSTRUCTION-BODY')
        def operation(op, *args):
            result = subprocess.run([str(self.package / 'bin/nda-plugin'), op, '--client', 'codex', '--project', str(self.project), *args],
                                    env=self.env, capture_output=True, text=True)
            self.assertNotIn('Traceback', result.stderr)
            return json.loads(result.stdout), result.returncode
        prepared, code = operation('task-prepare', '--role', 'developer', '--task', str(task), '--stage', 'implementation')
        self.assertEqual(code, 0, prepared)
        self.assertFalse(prepared['implementation_authorized'])
        self.assertIn(str(self.project / 'AGENTS.md'), prepared['instruction_candidates'])
        self.assertIn('.nda-harness/tasks/plugin/task.md', prepared['task_candidates'])
        self.assertNotIn('SECRET-INSTRUCTION-BODY', json.dumps(prepared))
        spec.write_text(spec.read_text() + 'changed behavior\n')
        refreshed, code = operation('context-refresh')
        self.assertEqual(refreshed['status'], 'needs_context')
        task.write_text(task.read_text() + f"Revision: {refreshed['head']}\nInput fingerprint: {refreshed['input_fingerprint']}\nStage: implementation\nEvidence: test references\nNext action: review current spec\n")
        checkpoint, code = operation('context-checkpoint', '--task', str(task))
        self.assertEqual(code, 0, checkpoint)
        resumed, code = operation('context-resume', '--task', str(task), '--session', 'another-client')
        self.assertEqual(code, 0, resumed)
        self.assertEqual(resumed['task'], '.nda-harness/tasks/plugin/task.md')
        self.assertFalse(resumed['implementation_authorized'])

    def test_interrupted_project_transaction_is_recovered_before_retry(self):
        # Simulate abrupt death after a durable write-ahead receipt is saved.
        # configure normally rolls back BaseException. Exercise the persisted
        # recovery format directly, as a killed process cannot run that cleanup.
        from nda_harness.hooks import hook_plan
        state = state_for(self.project, self.home)
        state.mkdir(parents=True)
        prior = {'owned': {}}
        plan = Plan(prior)
        plan.write(self.project / '.nda-harness/profile.json', b'{"partial":true}\n')
        registration = hook_plan(plan, self.project, state, prior, check_command='false')
        def journal(current):
            atomic(state / 'receipt.json', json_bytes({'transaction': {'prior': prior, 'git': registration, 'applied': current.applied}}))
        plan.apply(state, journal=journal)
        result = self.setup(skip=True)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(self.commit().returncode, 0)
        self.assertNotIn('transaction', json.loads((state / 'receipt.json').read_text()))

    def test_write_ahead_recovery_handles_write_that_never_happened(self):
        state = self.home / 'transaction'
        state.mkdir()
        existing = self.project / 'unrelated'
        existing.write_text('keep original')
        new = self.project / 'new'
        plan = Plan({})
        plan.write(existing, b'new content')
        plan.write(new, b'new file')
        def stop_before_write(current):
            raise OSError('interruption before atomic replace')
        with self.assertRaises(OSError):
            plan.apply(state, journal=stop_before_write)
        self.assertEqual(plan.rollback(), [])
        self.assertEqual(existing.read_text(), 'keep original')
        self.assertFalse(new.exists())


if __name__ == '__main__':
    unittest.main()
