"""Keychain storage for one OpenRouter skill-selection key. No plaintext fallback."""
import ctypes
from pathlib import Path
import sys
import uuid

from nda_harness.files import atomic


SERVICE = 'vn.pila.nda-harness.openrouter'
ACCOUNT = 'skill-selection'
NOT_FOUND = -25300
UTF8 = 0x08000100


class KeychainDenied(OSError):
    pass


def _state(home):
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
        'credential_unavailable': 'Keychain could not store the key.',
        'credential_missing': 'No OpenRouter key is saved.',
    }.get(diagnostic)
    if mapped:
        return mapped
    guidance = report.get('next')
    if isinstance(guidance, str) and guidance and '{' not in guidance:
        return guidance
    return 'Skill selection setup did not finish.'


def _report(status, code, diagnostic=None):
    payload = {'implementation_authorized': False, 'status': status}
    if diagnostic:
        payload['diagnostic'] = diagnostic
    return payload, code


def selection_setup(keychain, tty, home, *, remove=False, read_secret=None):
    """Store, replace, or remove the key from a terminal. Never accept it as an argument."""
    if not getattr(tty, 'isatty', lambda: False)():
        return _report('blocked', 2, 'terminal_required')
    try:
        status = keychain.status()
    except OSError:
        return _report('blocked', 2, 'credential_unavailable')
    if status == 'unavailable':
        return _report('blocked', 2, 'credential_unavailable')
    if remove:
        if status != 'present':
            return _report('blocked', 2, 'credential_missing')
        if not _confirm(tty, 'Remove the saved OpenRouter key?'):
            return _report('cancelled', 130)
        try:
            keychain.delete()
            _rotate(home)
        except OSError:
            return _report('blocked', 2, 'credential_unavailable')
        return _report('ready', 0, 'credential_removed')
    if status == 'present' and not _confirm(tty, 'Replace the saved OpenRouter key?'):
        return _report('ready', 0, 'credential_kept')
    if read_secret is None:
        import getpass
        secret = getpass.getpass('OpenRouter key: ', stream=_output(tty))
    else:
        secret = read_secret()
    if not isinstance(secret, str) or not secret.strip():
        return _report('blocked', 2, 'invalid_credential')
    try:
        keychain.write(secret.strip())
        _rotate(home)
    except OSError:
        return _report('blocked', 2, 'credential_unavailable')
    return _report('ready', 0)


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
