"""File-backed OpenRouter skill-selection credentials and Keychain migration."""
import io
import json
import os
import stat
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from nda_harness.credentials import (
    FileCredentialStore,
    generation_id,
    migrate_openrouter_key,
    migrate_message,
    selection_setup,
    setup_message,
)
from nda_harness.project import ensure_project_gitignore
from nda_harness.files import Plan


FIRST = 'first-openrouter-key'
SECOND = 'second-openrouter-key'


class FakeKeychain:
    def __init__(self, denied=False, unavailable=False):
        self.secret = None
        self.denied = denied
        self.unavailable = unavailable
        self.writes = 0
        self.reads = 0
        self.deletes = 0

    def status(self):
        if self.unavailable:
            return 'unavailable'
        return 'missing' if self.secret is None else 'present'

    def read(self):
        self.reads += 1
        if self.denied or self.unavailable:
            raise PermissionError('denied')
        if self.secret is None:
            raise OSError('missing')
        return self.secret

    def write(self, secret):
        if self.denied or self.unavailable:
            raise PermissionError('denied')
        self.secret = secret
        self.writes += 1

    def delete(self):
        self.deletes += 1
        if self.denied or self.unavailable:
            raise PermissionError('denied')
        self.secret = None


class ScriptedTTY:
    def __init__(self, answers):
        self.answers = list(answers)
        self.prompts = []

    def isatty(self):
        return True

    def write(self, text):
        self.prompts.append(text)
        return len(text)

    def flush(self):
        return None

    def readline(self):
        return self.answers.pop(0)


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(dir=ROOT))
        self.addCleanup(self._cleanup)
        self.store = FileCredentialStore(self.home)

    def _cleanup(self):
        for path in sorted(self.home.rglob('*'), reverse=True):
            if path.is_symlink() or path.is_file():
                path.unlink()
            else:
                path.rmdir()
        self.home.rmdir()

    def key_path(self):
        return self.home / 'skill-selection' / 'openrouter-key'

    def ignore_path(self):
        return self.home / 'skill-selection' / '.gitignore'

    def files(self):
        blobs = []
        for path in self.home.rglob('*'):
            if path.is_file() and not path.is_symlink():
                blobs.append(path.read_bytes())
        return b'\n'.join(blobs)

    def setup(self, answers, secret=None, keychain=None):
        calls = []

        def read_secret():
            calls.append('secret')
            return secret

        tty = ScriptedTTY(answers)
        report, code = selection_setup(tty, self.home, keychain=keychain, read_secret=read_secret)
        return report, code, calls, tty

    def test_setup_writes_file_gitignore_and_keeps_secrets_out_of_other_files(self):
        report, code, calls, _tty = self.setup([], FIRST)
        self.assertEqual(code, 0)
        self.assertEqual(calls, ['secret'])
        self.assertEqual(self.store.status(), 'present')
        self.assertEqual(self.store.read(), FIRST)
        self.assertEqual(self.key_path().read_bytes(), (FIRST + '\n').encode())
        self.assertEqual(stat.S_IMODE(self.key_path().stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE((self.home / 'skill-selection').stat().st_mode), 0o700)
        self.assertEqual(self.ignore_path().read_bytes(), b'/openrouter-key\n')
        self.assertEqual(stat.S_IMODE(self.ignore_path().stat().st_mode), 0o600)
        generation = generation_id(self.home)
        self.assertTrue(generation)

        report, code, calls, tty = self.setup(['n\n'], SECOND)
        self.assertEqual(code, 0)
        self.assertEqual(report['diagnostic'], 'credential_kept')
        self.assertEqual(calls, [])
        self.assertEqual(self.store.read(), FIRST)
        self.assertEqual(generation_id(self.home), generation)
        self.assertIn('Replace the saved OpenRouter key?', ''.join(tty.prompts))
        self.assertEqual(setup_message(report), 'The saved OpenRouter key was kept.')

        report, code, calls, _tty = self.setup(['y\n'], SECOND)
        self.assertEqual(code, 0)
        self.assertEqual(self.store.read(), SECOND)
        self.assertNotEqual(generation_id(self.home), generation)
        replaced = generation_id(self.home)

        report, code = selection_setup(ScriptedTTY(['y\n']), self.home, remove=True)
        self.assertEqual(code, 0)
        self.assertEqual(self.store.status(), 'missing')
        self.assertTrue(self.ignore_path().is_file())
        self.assertNotEqual(generation_id(self.home), replaced)
        stored = self.files()
        self.assertNotIn(FIRST.encode(), stored)
        self.assertNotIn(SECOND.encode(), stored)
        self.assertNotIn(FIRST, json.dumps(report))

    def test_wrong_mode_is_unavailable_without_chmod(self):
        self.store.write(FIRST)
        os.chmod(self.key_path(), 0o644)
        self.assertEqual(self.store.status(), 'unavailable')
        with self.assertRaises(OSError):
            self.store.read()
        self.assertEqual(stat.S_IMODE(self.key_path().stat().st_mode), 0o644)

    def test_empty_or_multiline_key_file_is_unavailable(self):
        state = self.home / 'skill-selection'
        state.mkdir(mode=0o700)
        path = self.key_path()
        path.write_bytes(b'\n')
        os.chmod(path, 0o600)
        self.assertEqual(self.store.status(), 'unavailable')
        path.write_bytes(b'line-one\nline-two\n')
        os.chmod(path, 0o600)
        self.assertEqual(self.store.status(), 'unavailable')
        with self.assertRaises(OSError):
            self.store.read()

    def test_denied_atomic_write_stores_nothing(self):
        with patch('nda_harness.credentials.atomic', side_effect=PermissionError('denied')):
            report, code, _calls, _tty = self.setup([], FIRST)
        self.assertEqual(code, 2)
        self.assertEqual(report['diagnostic'], 'credential_unavailable')
        self.assertEqual(self.store.status(), 'missing')
        self.assertNotIn(FIRST.encode(), self.files())

    def test_setup_terminal_text_is_not_json(self):
        saved = setup_message({'implementation_authorized': False, 'status': 'ready'})
        self.assertEqual(saved, 'OpenRouter key saved.')
        self.assertNotIn('{', saved)
        self.assertEqual(setup_message({'status': 'ready', 'diagnostic': 'credential_removed'}), 'OpenRouter key removed.')
        self.assertEqual(setup_message({'status': 'cancelled'}), 'Cancelled. The saved key was not changed.')
        self.assertEqual(setup_message({'status': 'ready', 'diagnostic': 'credential_kept'}), 'The saved OpenRouter key was kept.')
        self.assertEqual(setup_message({'status': 'blocked', 'diagnostic': 'invalid_credential'}), 'The key was empty. Nothing was saved.')
        self.assertEqual(setup_message({'status': 'blocked', 'diagnostic': 'credential_unavailable'}), 'The key file could not be read.')
        self.assertNotIn('first-openrouter-key', setup_message({'status': 'ready'}))

    def test_unwritable_stdin_prompts_on_stderr(self):
        class ReadOnlyTTY(ScriptedTTY):
            def write(self, text):
                raise io.UnsupportedOperation('not writable')

        streams = []

        def fake_getpass(prompt, stream=None):
            streams.append((prompt, stream))
            return FIRST

        with patch('getpass.getpass', fake_getpass):
            report, code = selection_setup(ReadOnlyTTY([]), self.home)
        self.assertEqual(code, 0)
        self.assertEqual(streams, [('OpenRouter key: ', sys.stderr)])
        self.assertEqual(self.store.read(), FIRST)
        self.assertNotIn(FIRST, json.dumps(report))

    def test_setup_moves_keychain_before_prompting(self):
        keychain = FakeKeychain()
        keychain.secret = FIRST
        report, code, calls, tty = self.setup(['y\n'], SECOND, keychain=keychain)
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertEqual(self.store.read(), FIRST)
        self.assertIsNone(keychain.secret)
        self.assertEqual(keychain.deletes, 1)
        self.assertIn('An OpenRouter key is still in Keychain. Move it to the local file?', ''.join(tty.prompts))
        generation = generation_id(self.home)

        # Same bytes already in file: generation unchanged by migrate path.
        self.assertEqual(generation_id(self.home), generation)

    def test_setup_command_prints_a_sentence_without_a_terminal(self):
        from io import StringIO
        from contextlib import redirect_stdout
        from nda_harness.plugin_runtime import main
        output = StringIO()
        with patch('sys.stdin.isatty', return_value=False), patch('nda_harness.plugin_runtime.package_config', return_value={'schema_version': 1, 'client': 'cursor'}), redirect_stdout(output):
            code = main(['selection-setup', '--client', 'cursor'])
        text = output.getvalue()
        self.assertEqual(code, 2)
        self.assertEqual(text.strip(), 'A local terminal is required.')
        self.assertNotIn('{', text)

    def test_setup_command_rejects_a_key_argument(self):
        from io import StringIO
        from contextlib import redirect_stderr
        from nda_harness.plugin_runtime import main
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main(['selection-setup', '--client', 'cursor', '--key', 'rejected-argument'])
        self.assertEqual(caught.exception.code, 2)

    def test_migrate_copies_keychain_to_file_without_rotating_generation(self):
        keychain = FakeKeychain()
        keychain.secret = FIRST
        # Seed generation as an existing 0.0.9 install would.
        from nda_harness.credentials import _rotate
        generation = _rotate(self.home)
        report, code = migrate_openrouter_key(ScriptedTTY(['y\n']), self.home, keychain)
        self.assertEqual(code, 0)
        self.assertEqual(report['status'], 'ready')
        self.assertEqual(self.store.read(), FIRST)
        self.assertIsNone(keychain.secret)
        self.assertEqual(generation_id(self.home), generation)
        self.assertEqual(self.ignore_path().read_bytes(), b'/openrouter-key\n')
        self.assertEqual(migrate_message(report), 'OpenRouter key moved to the local file. The Keychain item was removed.')
        self.assertNotIn(FIRST, json.dumps(report))
        self.assertNotIn(FIRST, ''.join(ScriptedTTY(['y\n']).prompts))

    def test_migrate_cancel_leaves_both_stores(self):
        keychain = FakeKeychain()
        keychain.secret = FIRST
        from nda_harness.credentials import _rotate
        generation = _rotate(self.home)
        report, code = migrate_openrouter_key(ScriptedTTY(['n\n']), self.home, keychain)
        self.assertEqual(code, 130)
        self.assertEqual(report['status'], 'cancelled')
        self.assertEqual(self.store.status(), 'missing')
        self.assertEqual(keychain.secret, FIRST)
        self.assertEqual(generation_id(self.home), generation)

    def test_migrate_already_file(self):
        self.store.write(FIRST)
        from nda_harness.credentials import _rotate
        generation = _rotate(self.home)
        report, code = migrate_openrouter_key(ScriptedTTY([]), self.home, FakeKeychain())
        self.assertEqual(code, 0)
        self.assertEqual(report['diagnostic'], 'credential_already_file')
        self.assertEqual(generation_id(self.home), generation)
        self.assertEqual(migrate_message(report), 'The OpenRouter key is already in the local file.')

    def test_migrate_same_bytes_deletes_keychain_copy(self):
        self.store.write(FIRST)
        keychain = FakeKeychain()
        keychain.secret = FIRST
        from nda_harness.credentials import _rotate
        generation = _rotate(self.home)
        report, code = migrate_openrouter_key(ScriptedTTY(['y\n']), self.home, keychain)
        self.assertEqual(code, 0)
        self.assertEqual(self.store.read(), FIRST)
        self.assertIsNone(keychain.secret)
        self.assertEqual(generation_id(self.home), generation)

    def test_migrate_different_bytes_file_or_keychain(self):
        self.store.write(FIRST)
        keychain = FakeKeychain()
        keychain.secret = SECOND
        from nda_harness.credentials import _rotate
        generation = _rotate(self.home)

        report, code = migrate_openrouter_key(ScriptedTTY(['file\n']), self.home, keychain)
        self.assertEqual(code, 0)
        self.assertEqual(self.store.read(), FIRST)
        self.assertIsNone(keychain.secret)
        self.assertEqual(generation_id(self.home), generation)

        keychain.secret = SECOND
        report, code = migrate_openrouter_key(ScriptedTTY(['keychain\n']), self.home, keychain)
        self.assertEqual(code, 0)
        self.assertEqual(self.store.read(), SECOND)
        self.assertIsNone(keychain.secret)
        self.assertNotEqual(generation_id(self.home), generation)

    def test_migrate_failed_write_keeps_keychain(self):
        keychain = FakeKeychain()
        keychain.secret = FIRST
        with patch.object(FileCredentialStore, 'write', side_effect=PermissionError('denied')):
            report, code = migrate_openrouter_key(ScriptedTTY(['y\n']), self.home, keychain)
        self.assertEqual(code, 2)
        self.assertEqual(report['diagnostic'], 'credential_unavailable')
        self.assertEqual(keychain.secret, FIRST)
        self.assertEqual(self.store.status(), 'missing')

    def test_migrate_sandbox_rerun_does_not_touch_stores(self):
        keychain = FakeKeychain()
        keychain.secret = FIRST
        with patch.dict(os.environ, {'CODEX_SANDBOX': 'seatbelt'}):
            report, code = migrate_openrouter_key(ScriptedTTY(['y\n']), self.home, keychain, client='cursor')
        self.assertEqual(code, 2)
        self.assertEqual(report['diagnostic'], 'sandbox_rerun')
        self.assertEqual(keychain.reads, 0)
        self.assertEqual(self.store.status(), 'missing')

    def test_project_gitignore_includes_skill_selection(self):
        import shutil
        import subprocess
        project = Path(tempfile.mkdtemp(dir=ROOT))
        self.addCleanup(shutil.rmtree, project)
        state = project / 'state'
        state.mkdir()
        plan = Plan({})
        ensure_project_gitignore(plan, project)
        plan.apply(state)
        text = (project / '.gitignore').read_text(encoding='utf-8')
        self.assertIn('.nda-harness/skill-selection/', text)
        self.assertIn('.nda-harness/tasks/', text)
        self.assertIn('.nda-harness/profile.json', text)
        dummy = project / '.nda-harness' / 'skill-selection' / 'openrouter-key'
        dummy.parent.mkdir(parents=True)
        dummy.write_text('secret\n', encoding='utf-8')
        subprocess.run(['git', 'init', '-q'], cwd=project, check=True)
        checked = subprocess.run(['git', 'check-ignore', '-q', '.nda-harness/skill-selection/openrouter-key'], cwd=project)
        self.assertEqual(checked.returncode, 0)

    def test_migrate_other_answer_leaves_both_stores(self):
        self.store.write(FIRST)
        keychain = FakeKeychain()
        keychain.secret = SECOND
        from nda_harness.credentials import _rotate
        generation = _rotate(self.home)
        report, code = migrate_openrouter_key(ScriptedTTY(['maybe\n']), self.home, keychain)
        self.assertEqual(code, 130)
        self.assertEqual(report['status'], 'cancelled')
        self.assertEqual(self.store.read(), FIRST)
        self.assertEqual(keychain.secret, SECOND)
        self.assertEqual(generation_id(self.home), generation)

    def test_symlink_paths_are_unavailable(self):
        keychain = FakeKeychain()
        keychain.secret = FIRST
        # openrouter-key symlink
        state = self.home / 'skill-selection'
        state.mkdir(mode=0o700)
        target = self.home / 'elsewhere'
        target.write_text(FIRST + '\n', encoding='utf-8')
        (state / 'openrouter-key').symlink_to(target)
        self.assertEqual(self.store.status(), 'unavailable')
        report, code = migrate_openrouter_key(ScriptedTTY(['y\n']), self.home, keychain)
        self.assertEqual(code, 2)
        self.assertEqual(report['diagnostic'], 'credential_unavailable')
        self.assertEqual(keychain.secret, FIRST)
        (state / 'openrouter-key').unlink()
        target.unlink()
        state.rmdir()

        # skill-selection directory symlink
        real = self.home / 'real-selection'
        real.mkdir(mode=0o700)
        state.symlink_to(real)
        self.assertEqual(self.store.status(), 'unavailable')
        report, code = selection_setup(ScriptedTTY([]), self.home, keychain=keychain, read_secret=lambda: SECOND)
        self.assertEqual(code, 2)
        self.assertEqual(report['diagnostic'], 'credential_unavailable')
        state.unlink()
        real.rmdir()

        # home (~/.nda-harness) symlink
        linked = Path(tempfile.mkdtemp(dir=ROOT))
        self.addCleanup(lambda: __import__('shutil').rmtree(linked, ignore_errors=True))
        target_home = linked / 'target'
        target_home.mkdir()
        home_link = linked / 'home-link'
        home_link.symlink_to(target_home)
        store = FileCredentialStore(home_link)
        self.assertEqual(store.status(), 'unavailable')
        report, code = migrate_openrouter_key(ScriptedTTY(['y\n']), home_link, keychain)
        self.assertEqual(code, 2)
        self.assertEqual(report['diagnostic'], 'credential_unavailable')

    def test_select_skills_refuses_symlink_key_without_opening_transport(self):
        from nda_harness.skill_selection import select_skills
        package = Path(tempfile.mkdtemp(dir=ROOT))
        self.addCleanup(lambda: __import__('shutil').rmtree(package, ignore_errors=True))
        skill = package / 'diagram-design'
        skill.mkdir()
        (skill / 'SKILL.md').write_text('body', encoding='utf-8')
        (package / 'catalog.json').write_text(
            '{"schema_version":1,"skills":[{"id":"diagram-design","entrypoint":"diagram-design/SKILL.md",'
            '"select_when":"diagram","exclude_when":"none","required_context":["audience"],"output":"A diagram"}]}',
            encoding='utf-8',
        )
        project = package / 'project'
        project.mkdir()
        from nda_harness.credentials import _rotate
        _rotate(self.home)
        state = self.home / 'skill-selection'
        target = self.home / 'elsewhere-key'
        target.write_text(FIRST + '\n', encoding='utf-8')
        key = state / 'openrouter-key'
        if key.exists() or key.is_symlink():
            key.unlink()
        key.symlink_to(target)
        calls = []

        def transport(url, payload, headers):
            calls.append(url)
            raise AssertionError('transport must not run')

        report, code = select_skills(
            {
                'schema_version': 1,
                'request': 'Draw a flow.',
                'stage': 'implementation',
                'project_facts': {'stack': ['Python'], 'deliverables': ['diagram'], 'constraints': ['none']},
            },
            project=project,
            session='symlink-session',
            home=self.home,
            catalog_root=package,
            release_manifest={'schema_version': 1},
            keychain=self.store,
            transport=transport,
            client='cursor',
        )
        self.assertEqual(code, 2)
        self.assertEqual(report['diagnostic'], 'credential_unavailable')
        self.assertEqual(calls, [])

    def test_setup_declines_move_then_writes_new_key(self):
        keychain = FakeKeychain()
        keychain.secret = FIRST
        report, code, calls, tty = self.setup(['n\n', 'y\n'], SECOND, keychain=keychain)
        self.assertEqual(code, 0)
        self.assertEqual(calls, ['secret'])
        self.assertEqual(self.store.read(), SECOND)
        self.assertIsNone(keychain.secret)
        prompts = ''.join(tty.prompts)
        self.assertIn('An OpenRouter key is still in Keychain. Move it to the local file?', prompts)
        self.assertIn('Delete the Keychain item?', prompts)
        self.assertNotEqual(generation_id(self.home), '')

    def test_remove_deletes_file_and_keychain(self):
        self.store.write(FIRST)
        keychain = FakeKeychain()
        keychain.secret = SECOND
        from nda_harness.credentials import _rotate
        generation = _rotate(self.home)
        report, code = selection_setup(ScriptedTTY(['n\n']), self.home, keychain=keychain, remove=True)
        self.assertEqual(code, 130)
        self.assertEqual(self.store.read(), FIRST)
        self.assertEqual(keychain.secret, SECOND)
        self.assertEqual(generation_id(self.home), generation)

        report, code = selection_setup(ScriptedTTY(['y\n']), self.home, keychain=keychain, remove=True)
        self.assertEqual(code, 0)
        self.assertEqual(report['diagnostic'], 'credential_removed')
        self.assertEqual(self.store.status(), 'missing')
        self.assertIsNone(keychain.secret)
        self.assertTrue(self.ignore_path().is_file())
        self.assertNotEqual(generation_id(self.home), generation)

    def test_migrate_keychain_unavailable_keeps_file(self):
        self.store.write(FIRST)
        keychain = FakeKeychain(unavailable=True)
        report, code = migrate_openrouter_key(ScriptedTTY([]), self.home, keychain)
        self.assertEqual(code, 2)
        self.assertEqual(report['diagnostic'], 'keychain_unavailable')
        self.assertEqual(self.store.read(), FIRST)
        self.assertEqual(
            migrate_message(report),
            'The Keychain item could not be read, so it was not removed. The local file remains the store.',
        )

    def test_home_gitignore_matches_openrouter_key(self):
        import shutil
        import subprocess
        self.store.write(FIRST)
        root = Path(tempfile.mkdtemp(dir=ROOT))
        self.addCleanup(shutil.rmtree, root)
        # Mirror the skill-selection directory into a disposable git work tree.
        selection = root / 'skill-selection'
        selection.mkdir()
        (selection / '.gitignore').write_bytes(self.ignore_path().read_bytes())
        (selection / 'openrouter-key').write_bytes(self.key_path().read_bytes())
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        checked = subprocess.run(['git', 'check-ignore', '-q', 'skill-selection/openrouter-key'], cwd=root)
        self.assertEqual(checked.returncode, 0)
        self.assertEqual((selection / '.gitignore').read_bytes(), b'/openrouter-key\n')
        # Removal leaves the ignore file.
        selection_setup(ScriptedTTY(['y\n']), self.home, remove=True)
        self.assertTrue(self.ignore_path().is_file())
        self.assertEqual(self.ignore_path().read_bytes(), b'/openrouter-key\n')
