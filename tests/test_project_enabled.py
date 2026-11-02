"""Per-project enabled flag. A missing field stays on. False quiets that repo."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from nda_harness.files import Conflict
from nda_harness.plugin_build import build
from nda_harness.plugin_runtime import hook, unit_check
from nda_harness.project import config_for, configure, directory_config

MESSAGE = 'NDA Harness is disabled on the project'


class ProjectEnabledTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / 'home'
        self.home.mkdir()
        self.project = self.base / 'pet'
        self.project.mkdir()
        self.env = {**os.environ, 'HOME': str(self.home), 'GIT_CONFIG_GLOBAL': '/dev/null',
                    'GIT_AUTHOR_NAME': 'Test', 'GIT_COMMITTER_NAME': 'Test',
                    'GIT_AUTHOR_EMAIL': 'test@example.test', 'GIT_COMMITTER_EMAIL': 'test@example.test'}
        subprocess.run(['git', 'init', '-q', str(self.project)], env=self.env, check=True)
        subprocess.run(['git', '-C', str(self.project), 'remote', 'add', 'origin', 'git@github.com:example/pet.git'], env=self.env, check=True)
        self.package = build(ROOT, self.base / 'cursor', 'cursor')

    def write_config(self, project, command='true', enabled=None):
        body = {'schema_version': 1, 'test_command': command}
        if enabled is not None:
            body['enabled'] = enabled
        path = project / '.nda-harness'
        path.mkdir(exist_ok=True)
        (path / 'config.json').write_text(json.dumps(body) + '\n')

    def test_missing_enabled_stays_on_and_non_boolean_is_invalid(self):
        self.write_config(self.project)
        self.assertTrue(config_for(self.project)['enabled'])
        self.write_config(self.project, enabled=True)
        self.assertTrue(directory_config(self.project)['enabled'])
        self.write_config(self.project, enabled='false')
        with self.assertRaises(Conflict):
            directory_config(self.project)

    def test_inner_enabled_false_wins_and_an_omitted_inner_field_keeps_the_outer_value(self):
        parent = self.base / 'workspace'
        parent.mkdir()
        subprocess.run(['git', 'init', '-q', str(parent)], env=self.env, check=True)
        self.write_config(parent, command='printf parent', enabled=False)
        child = parent / 'pet'
        child.mkdir()
        subprocess.run(['git', 'init', '-q', str(child)], env=self.env, check=True)
        self.write_config(child, command='printf child')
        self.assertFalse(config_for(child)['enabled'])
        self.assertEqual(config_for(child)['test_command'], 'printf child')
        self.write_config(child, command='printf child', enabled=True)
        self.assertTrue(config_for(child)['enabled'])

    def test_unit_check_skips_the_test_command_when_disabled(self):
        marker = self.project / 'ran-tests'
        self.write_config(self.project, command=f'touch {marker}', enabled=False)
        self.assertEqual(unit_check(self.project), 0)
        self.assertFalse(marker.exists())

    def test_setup_writes_enabled_true(self):
        self.write_config(self.project, enabled=False)
        (self.project / '.nda-harness/profile.json').write_text(json.dumps({
            'schema_version': 3, 'memory': {'bank_id': 'pet-bank', 'system': 'hindsight'},
        }) + '\n')
        result = configure(self.project, self.package, self.home, enable=True)
        self.assertEqual(result['status'], 'ready')
        self.assertTrue(json.loads((self.project / '.nda-harness/config.json').read_text())['enabled'])

    def test_startup_hook_stays_quiet_and_does_not_enable_the_project(self):
        self.write_config(self.project, enabled=False)
        output, code = hook(self.package, 'cursor', 'sessionStart', self.home, {'cwd': str(self.project)})
        self.assertEqual(code, 0)
        self.assertNotIn('additional_context', output)
        self.assertNotIn('search_docs', json.dumps(output))
        self.assertFalse(json.loads((self.project / '.nda-harness/config.json').read_text())['enabled'])

    def test_verify_and_skill_selection_reply_disabled(self):
        self.write_config(self.project, enabled=False)
        binary = str(self.package / 'bin/nda-plugin')
        for command in (['verify'], ['select-skills', '--session', 'quiet'], ['session-bootstrap']):
            with self.subTest(command=command[0]):
                run = subprocess.run(
                    [binary, *command, '--client', 'cursor', '--project', str(self.project)],
                    env=self.env, cwd=self.home, capture_output=True, text=True, input='{}',
                )
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertEqual(run.stdout.strip(), MESSAGE)

    def test_rule_tells_the_agent_the_project_is_off(self):
        rule = (ROOT / 'plugin/rules/nda-harness.mdc').read_text()
        self.assertIn(MESSAGE, rule)
        self.assertIn('nda-setup', rule)
        built = (self.package / 'rules/nda-harness.mdc').read_text()
        self.assertIn(MESSAGE, built)
