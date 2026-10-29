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
