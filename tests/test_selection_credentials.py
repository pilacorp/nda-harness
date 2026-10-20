"""Keychain setup for the OpenRouter skill-selection key."""
import json
import stat
import sys
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from nda_harness.credentials import generation_id, selection_setup


FIRST = 'first-openrouter-key'
SECOND = 'second-openrouter-key'


class FakeKeychain:
    def __init__(self, denied=False):
        self.secret = None
        self.denied = denied
        self.writes = 0

    def status(self):
        return 'missing' if self.secret is None else 'present'

    def read(self):
        if self.secret is None:
            raise OSError('missing')
        return self.secret

    def write(self, secret):
        if self.denied:
            raise PermissionError('denied')
        self.secret = secret
        self.writes += 1

    def delete(self):
        if self.denied:
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

    def _cleanup(self):
        for path in sorted(self.home.rglob('*'), reverse=True):
            if path.is_symlink() or path.is_file():
                path.unlink()
            else:
                path.rmdir()
        self.home.rmdir()

    def files(self):
        blobs = []
        for path in self.home.rglob('*'):
            if path.is_file() and not path.is_symlink():
                blobs.append(path.read_bytes())
        return b'\n'.join(blobs)

    def setup(self, keychain, answers, secret=None):
        calls = []

        def read_secret():
            calls.append('secret')
            return secret

        tty = ScriptedTTY(answers)
        report, code = selection_setup(keychain, tty, self.home, read_secret=read_secret)
        return report, code, calls, tty

    def test_setup_replace_cancel_and_remove_keep_secrets_out_of_files(self):
        keychain = FakeKeychain()
        report, code, calls, _tty = self.setup(keychain, [], FIRST)
        self.assertEqual(code, 0)
        self.assertEqual(calls, ['secret'])
        self.assertEqual(keychain.secret, FIRST)
        generation = generation_id(self.home)
        self.assertTrue(generation)
        self.assertEqual(stat.S_IMODE((self.home / 'skill-selection' / 'generation').stat().st_mode), 0o600)

        report, code, calls, tty = self.setup(keychain, ['n\n'], SECOND)
        self.assertEqual(code, 130)
        self.assertEqual(calls, [])
        self.assertEqual(keychain.writes, 1)
        self.assertEqual(keychain.secret, FIRST)
        self.assertEqual(generation_id(self.home), generation)
        self.assertIn('Replace the saved OpenRouter key?', ''.join(tty.prompts))

        report, code, calls, _tty = self.setup(keychain, ['y\n'], SECOND)
        self.assertEqual(code, 0)
        self.assertEqual(keychain.secret, SECOND)
        self.assertNotEqual(generation_id(self.home), generation)
        replaced = generation_id(self.home)

        report, code = selection_setup(keychain, ScriptedTTY(['y\n']), self.home, remove=True)
        self.assertEqual(code, 0)
        self.assertIsNone(keychain.secret)
        self.assertNotEqual(generation_id(self.home), replaced)
        stored = self.files()
        self.assertNotIn(FIRST.encode(), stored)
        self.assertNotIn(SECOND.encode(), stored)
        self.assertNotIn(FIRST, json.dumps(report))

    def test_denied_write_stores_nothing(self):
        keychain = FakeKeychain(denied=True)
        report, code, _calls, _tty = self.setup(keychain, [], FIRST)
        self.assertEqual(code, 2)
        self.assertEqual(report['diagnostic'], 'credential_unavailable')
        self.assertEqual(keychain.writes, 0)
        self.assertNotIn(FIRST.encode(), self.files())

    def test_setup_command_rejects_a_key_argument(self):
        from io import StringIO
        from contextlib import redirect_stderr
        from nda_harness.plugin_runtime import main
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as caught:
                main(['selection-setup', '--client', 'cursor', '--key', 'rejected-argument'])
        self.assertEqual(caught.exception.code, 2)
