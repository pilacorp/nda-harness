"""User-only file storage for one OpenRouter skill-selection key."""
import ctypes
import os
from pathlib import Path
import stat
import sys
import uuid

from nda_harness.files import atomic


SERVICE = 'vn.pila.nda-harness.openrouter'
ACCOUNT = 'skill-selection'
NOT_FOUND = -25300
UTF8 = 0x08000100
KEY_NAME = 'openrouter-key'
GITIGNORE_BODY = b'/openrouter-key\n'


class KeychainDenied(OSError):
    pass


def _guard_home(home):
    """Refuse a symlinked home state root (~/.nda-harness)."""
    root = Path(home)
    if root.is_symlink():
        raise KeychainDenied()


def _state(home):
    _guard_home(home)
    state = Path(home) / 'skill-selection'
    if state.is_symlink():
        raise KeychainDenied()
    state.mkdir(parents=True, exist_ok=True)
    state.chmod(0o700)
    return state


def generation_id(home):
    path = _state(home) / 'generation'
    if path.is_symlink() or not path.is_file():
        raise KeychainDenied()
    return path.read_text(encoding='utf-8').strip()


def _rotate(home):
    path = _state(home) / 'generation'
    if path.is_symlink():
        raise KeychainDenied()
    value = uuid.uuid4().hex
    atomic(path, (value + '\n').encode(), 0o600)
    return value


def _ensure_generation(home):
    """Create a generation id only when the file is absent. Does not rotate an existing id."""
    path = Path(home) / 'skill-selection' / 'generation'
    state = Path(home) / 'skill-selection'
    if state.is_symlink() or path.is_symlink():
        raise KeychainDenied()
    if path.is_file():
        return path.read_text(encoding='utf-8').strip()
    return _rotate(home)


def _output(tty):
    """Prompts must go to a writable stream. Standard input can be a terminal and still refuse writes."""
    try:
        tty.write('')
        tty.flush()
    except (AttributeError, OSError, ValueError):
        return sys.stderr
    return tty


def _confirm(tty, prompt):
    out = _output(tty)
    out.write(prompt + ' [y/N] ')
    out.flush()
    answer = tty.readline()
    return isinstance(answer, str) and answer.strip().lower() in {'y', 'yes'}


def _ask(tty, prompt):
    out = _output(tty)
    out.write(prompt + ' ')
    out.flush()
    answer = tty.readline()
    return answer.strip().lower() if isinstance(answer, str) else ''


def setup_message(report):
    """Human terminal text. selection-setup never prints the JSON report."""
    status = report.get('status')
    diagnostic = report.get('diagnostic')
    if status == 'ready' and diagnostic == 'credential_removed':
        return 'OpenRouter key removed.'
    if status == 'ready' and diagnostic == 'credential_kept':
        return 'The saved OpenRouter key was kept.'
    if status == 'ready':
        return 'OpenRouter key saved.'
    if status == 'cancelled':
        return 'Cancelled. The saved key was not changed.'
    mapped = {
        'terminal_required': 'A local terminal is required.',
        'invalid_credential': 'The key was empty. Nothing was saved.',
        'credential_unavailable': 'The key file could not be read.',
        'credential_missing': 'No OpenRouter key is saved.',
    }.get(diagnostic)
    if mapped:
        return mapped
    guidance = report.get('next')
    if isinstance(guidance, str) and guidance and '{' not in guidance:
        return guidance
    return 'Skill selection setup did not finish.'


def migrate_message(report):
    """Human terminal text for selection-migrate."""
    status = report.get('status')
    diagnostic = report.get('diagnostic')
    if status == 'ready' and diagnostic == 'credential_already_file':
        return 'The OpenRouter key is already in the local file.'
    if status == 'ready' and diagnostic in (None, 'credential_migrated', 'keychain_removed'):
        if diagnostic == 'keychain_removed':
            return 'The Keychain copy was removed. The local file was kept.'
        return 'OpenRouter key moved to the local file. The Keychain item was removed.'
    if status == 'cancelled':
        return 'Cancelled. The saved key was not changed.'
    mapped = {
        'terminal_required': 'A local terminal is required.',
        'credential_missing': 'No OpenRouter key is saved. Run selection-setup in a local terminal.',
        'credential_unavailable': 'The OpenRouter key could not be migrated.',
        'keychain_unavailable': 'The Keychain item could not be read, so it was not removed. The local file remains the store.',
        'sandbox_rerun': 'Skill selection must run outside the sandbox so it can use the shared OpenRouter key file. Rerun this command outside the sandbox.',
    }.get(diagnostic)
    if mapped:
        return mapped
    guidance = report.get('next')
    if isinstance(guidance, str) and guidance and '{' not in guidance:
        return guidance
    return 'Skill selection migration did not finish.'


def _report(status, code, diagnostic=None):
    payload = {'implementation_authorized': False, 'status': status}
    if diagnostic:
        payload['diagnostic'] = diagnostic
    return payload, code


def _parse_secret(raw):
    if not isinstance(raw, (bytes, bytearray)):
        raise KeychainDenied()
    text = raw.decode()
    if text.endswith('\n'):
        text = text[:-1]
    if not text or '\n' in text or '\r' in text:
        raise KeychainDenied()
    return text


class FileCredentialStore:
    """Regular file under ~/.nda-harness/skill-selection/openrouter-key."""

    def __init__(self, home):
        self.home = Path(home)

    def ensure_ignore(self):
        state = _state(self.home)
        path = state / '.gitignore'
        if path.is_symlink():
            raise KeychainDenied()
        atomic(path, GITIGNORE_BODY, 0o600)

    def _path(self):
        return self.home / 'skill-selection' / KEY_NAME

    def status(self):
        try:
            _guard_home(self.home)
        except KeychainDenied:
            return 'unavailable'
        state = self.home / 'skill-selection'
        path = self._path()
        if state.is_symlink() or path.is_symlink():
            return 'unavailable'
        if not path.exists():
            return 'missing'
        if not path.is_file():
            return 'unavailable'
        try:
            info = path.stat()
            parent = state.stat()
        except OSError:
            return 'unavailable'
        if stat.S_IMODE(info.st_mode) != 0o600 or stat.S_IMODE(parent.st_mode) != 0o700:
            return 'unavailable'
        if hasattr(os, 'getuid') and info.st_uid != os.getuid():
            return 'unavailable'
        try:
            _parse_secret(path.read_bytes())
        except (OSError, UnicodeError, KeychainDenied):
            return 'unavailable'
        return 'present'

    def read(self):
        if self.status() != 'present':
            raise KeychainDenied()
        return _parse_secret(self._path().read_bytes())

    def write(self, secret):
        if not isinstance(secret, str) or not secret.strip() or '\n' in secret.strip() or '\r' in secret.strip():
            raise KeychainDenied()
        self.ensure_ignore()
        path = _state(self.home) / KEY_NAME
        if path.is_symlink():
            raise KeychainDenied()
        atomic(path, (secret.strip() + '\n').encode(), 0o600)

    def delete(self):
        path = self._path()
        state = self.home / 'skill-selection'
        if state.is_symlink() or path.is_symlink():
            raise KeychainDenied()
        if not path.exists():
            return
        if not path.is_file():
            raise KeychainDenied()
        path.unlink()


def _keychain_status(keychain):
    if keychain is None:
        return 'missing'
    try:
        status = keychain.status()
    except OSError:
        return 'unavailable'
    if status not in ('present', 'missing', 'unavailable'):
        return 'unavailable'
    return status


def _write_file_from_secret(store, secret):
    store.write(secret)
    if store.read() != secret.strip():
        try:
            store.delete()
        except OSError:
            pass
        raise KeychainDenied()


def selection_setup(tty, home, *, keychain=None, remove=False, read_secret=None):
    """Store, replace, or remove the key from a terminal. Never accept it as an argument."""
    if not getattr(tty, 'isatty', lambda: False)():
        return _report('blocked', 2, 'terminal_required')
    store = FileCredentialStore(home)
    file_status = store.status()
    chain_status = _keychain_status(keychain)

    if remove:
        if file_status == 'missing' and chain_status == 'missing':
            return _report('blocked', 2, 'credential_missing')
        if file_status == 'unavailable' or chain_status == 'unavailable':
            return _report('blocked', 2, 'credential_unavailable')
        if not _confirm(tty, 'Remove the saved OpenRouter key?'):
            return _report('cancelled', 130)
        try:
            if file_status == 'present':
                store.delete()
            if chain_status == 'present':
                keychain.delete()
            _rotate(home)
            store.ensure_ignore()
        except OSError:
            return _report('blocked', 2, 'credential_unavailable')
        return _report('ready', 0, 'credential_removed')

    if file_status == 'missing' and chain_status == 'present':
        if _confirm(tty, 'An OpenRouter key is still in Keychain. Move it to the local file?'):
            try:
                secret = keychain.read()
                _write_file_from_secret(store, secret)
                _ensure_generation(home)
                keychain.delete()
            except OSError:
                return _report('blocked', 2, 'credential_unavailable')
            return _report('ready', 0)
        # Decline: continue to prompt for a new key, then offer Keychain delete.

    if file_status == 'present' and not _confirm(tty, 'Replace the saved OpenRouter key?'):
        return _report('ready', 0, 'credential_kept')
    if file_status == 'unavailable':
        return _report('blocked', 2, 'credential_unavailable')

    if read_secret is None:
        import getpass
        secret = getpass.getpass('OpenRouter key: ', stream=_output(tty))
    else:
        secret = read_secret()
    if not isinstance(secret, str) or not secret.strip():
        return _report('blocked', 2, 'invalid_credential')
    try:
        store.write(secret.strip())
        _rotate(home)
    except OSError:
        return _report('blocked', 2, 'credential_unavailable')
    if chain_status == 'present' and _confirm(tty, 'Delete the Keychain item?'):
        try:
            keychain.delete()
        except OSError:
            return _report('blocked', 2, 'credential_unavailable')
    return _report('ready', 0)


def migrate_openrouter_key(tty, home, keychain, *, client=None):
    """Copy the Keychain item into the user-only file, then delete the item."""
    from nda_harness.skill_selection import sandbox_refusal

    if not getattr(tty, 'isatty', lambda: False)():
        return _report('blocked', 2, 'terminal_required')
    refused = sandbox_refusal(client, home=home, kind='verify')
    if refused:
        payload, code = refused
        return payload, code

    store = FileCredentialStore(home)
    file_status = store.status()
    chain_status = _keychain_status(keychain)

    if file_status == 'unavailable':
        return _report('blocked', 2, 'credential_unavailable')
    if file_status == 'missing' and chain_status == 'missing':
        return _report('blocked', 2, 'credential_missing')
    if file_status == 'missing' and chain_status == 'unavailable':
        return _report('blocked', 2, 'credential_unavailable')
    if file_status == 'present' and chain_status == 'missing':
        return _report('ready', 0, 'credential_already_file')
    if file_status == 'present' and chain_status == 'unavailable':
        return _report('blocked', 2, 'keychain_unavailable')

    if file_status == 'missing' and chain_status == 'present':
        if not _confirm(tty, 'Move the OpenRouter key from Keychain into the local file and delete the Keychain item?'):
            return _report('cancelled', 130)
        try:
            secret = keychain.read()
            _write_file_from_secret(store, secret)
            _ensure_generation(home)
        except OSError:
            return _report('blocked', 2, 'credential_unavailable')
        try:
            keychain.delete()
        except OSError:
            return _report('blocked', 2, 'credential_unavailable')
        return _report('ready', 0, 'credential_migrated')

    # Both present.
    try:
        file_secret = store.read()
        chain_secret = keychain.read()
    except OSError:
        return _report('blocked', 2, 'credential_unavailable')

    if file_secret == chain_secret:
        if not _confirm(tty, 'Delete the Keychain copy? The local file already has this key.'):
            return _report('cancelled', 130)
        try:
            keychain.delete()
        except OSError:
            return _report('blocked', 2, 'credential_unavailable')
        return _report('ready', 0, 'keychain_removed')

    choice = _ask(tty, 'The local file and the Keychain item differ. Type file or keychain:')
    if choice == 'file':
        try:
            keychain.delete()
        except OSError:
            return _report('blocked', 2, 'credential_unavailable')
        return _report('ready', 0, 'keychain_removed')
    if choice == 'keychain':
        try:
            _write_file_from_secret(store, chain_secret)
            _rotate(home)
            keychain.delete()
        except OSError:
            return _report('blocked', 2, 'credential_unavailable')
        return _report('ready', 0, 'credential_migrated')
    return _report('cancelled', 130)


def _framework(path):
    library = ctypes.cdll.LoadLibrary(path)
    return library


def _symbol(library, name):
    return ctypes.c_void_p.in_dll(library, name)


class MacKeychain:
    """Exact service/account item. Synchronization stays off. Attributes can be checked without the secret."""

    def __init__(self):
        self.security = _framework('/System/Library/Frameworks/Security.framework/Security')
        self.core = _framework('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        self.core.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        self.core.CFStringCreateWithCString.restype = ctypes.c_void_p
        self.core.CFDataCreate.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long]
        self.core.CFDataCreate.restype = ctypes.c_void_p
        self.core.CFDataGetBytePtr.argtypes = [ctypes.c_void_p]
        self.core.CFDataGetBytePtr.restype = ctypes.POINTER(ctypes.c_char)
        self.core.CFDataGetLength.argtypes = [ctypes.c_void_p]
        self.core.CFDataGetLength.restype = ctypes.c_long
        self.core.CFRelease.argtypes = [ctypes.c_void_p]
        self.core.CFDictionaryCreate.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p]
        self.core.CFDictionaryCreate.restype = ctypes.c_void_p
        self.security.SecItemCopyMatching.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
        self.security.SecItemCopyMatching.restype = ctypes.c_int
        self.security.SecItemAdd.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.security.SecItemAdd.restype = ctypes.c_int
        self.security.SecItemUpdate.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        self.security.SecItemUpdate.restype = ctypes.c_int
        self.security.SecItemDelete.argtypes = [ctypes.c_void_p]
        self.security.SecItemDelete.restype = ctypes.c_int

    def _text(self, value):
        return self.core.CFStringCreateWithCString(None, value.encode(), UTF8)

    def _callbacks(self, name):
        return ctypes.cast(ctypes.pointer(ctypes.c_char.in_dll(self.core, name)), ctypes.c_void_p).value

    def _dictionary(self, pairs):
        keys = (ctypes.c_void_p * len(pairs))()
        values = (ctypes.c_void_p * len(pairs))()
        owned = []
        for index, (key, value) in enumerate(pairs):
            key_ref = self._text(key)
            owned.append(key_ref)
            keys[index] = key_ref
            values[index] = value
        created = self.core.CFDictionaryCreate(
            None, keys, values, len(pairs), self._callbacks('kCFTypeDictionaryKeyCallBacks'), self._callbacks('kCFTypeDictionaryValueCallBacks'))
        for item in owned:
            self.core.CFRelease(item)
        if not created:
            raise KeychainDenied()
        return created

    def _boolean(self, value):
        return _symbol(self.core, 'kCFBooleanTrue' if value else 'kCFBooleanFalse')

    def _query(self, include_secret):
        secret = [('r_Data', self._boolean(True))] if include_secret else [('r_Attributes', self._boolean(True))]
        return self._dictionary([
            ('class', self._text('genp')),
            ('svce', self._text(SERVICE)),
            ('acct', self._text(ACCOUNT)),
            ('sync', self._boolean(False)),
            ('m_Limit', self._text('m_LimitOne')),
            *secret,
        ])

    def _matching(self, include_secret):
        query = self._query(include_secret)
        result = ctypes.c_void_p()
        try:
            status = self.security.SecItemCopyMatching(query, ctypes.byref(result))
        finally:
            self.core.CFRelease(query)
        return status, result

    def status(self):
        status, result = self._matching(False)
        if result:
            self.core.CFRelease(result)
        if status == 0:
            return 'present'
        if status == NOT_FOUND:
            return 'missing'
        return 'unavailable'

    def read(self):
        status, result = self._matching(True)
        try:
            if status != 0 or not result:
                raise KeychainDenied()
            length = self.core.CFDataGetLength(result)
            pointer = self.core.CFDataGetBytePtr(result)
            return ctypes.string_at(pointer, length).decode()
        finally:
            if result:
                self.core.CFRelease(result)

    def write(self, secret):
        data = self.core.CFDataCreate(None, secret.encode(), len(secret.encode()))
        if not data:
            raise KeychainDenied()
        try:
            if self.status() == 'present':
                query = self._dictionary([
                    ('class', self._text('genp')), ('svce', self._text(SERVICE)), ('acct', self._text(ACCOUNT)), ('sync', self._boolean(False)),
                ])
                update = self._dictionary([('v_Data', data), ('sync', self._boolean(False))])
                try:
                    if self.security.SecItemUpdate(query, update) != 0:
                        raise KeychainDenied()
                finally:
                    self.core.CFRelease(query)
                    self.core.CFRelease(update)
                return
            created = self._dictionary([
                ('class', self._text('genp')), ('svce', self._text(SERVICE)), ('acct', self._text(ACCOUNT)),
                ('v_Data', data), ('sync', self._boolean(False)),
            ])
            try:
                if self.security.SecItemAdd(created, None) != 0:
                    raise KeychainDenied()
            finally:
                self.core.CFRelease(created)
        finally:
            self.core.CFRelease(data)

    def delete(self):
        query = self._dictionary([
            ('class', self._text('genp')), ('svce', self._text(SERVICE)), ('acct', self._text(ACCOUNT)), ('sync', self._boolean(False)),
        ])
        try:
            status = self.security.SecItemDelete(query)
        finally:
            self.core.CFRelease(query)
        if status not in (0, NOT_FOUND):
            raise KeychainDenied()
