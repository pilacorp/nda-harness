"""Private, allowlisted diagnostics for harness MCP boundaries."""
from datetime import datetime, timezone
import fcntl
import json
import os
import re
import stat

from nda_harness.files import Conflict, guard_path

JEV = 'nda-harness-jev'
HINDSIGHT = 'nda-harness-hindsight'
RAG = 'nda-harness-nda-rag'
OPERATIONS = {
    JEV: ('startup', 'select_skills', 'record_selection', 'load_selected_skills', 'selection_verify'),
    HINDSIGHT: ('startup', 'list_banks', 'create_bank', 'recall', 'retain', 'reflect'),
    RAG: ('startup', 'search_docs', 'get_page', 'list_pages'),
}
ERROR_CODES = ('timeout', 'transport_error', 'authentication_required', 'invalid_response',
               'unknown_error', 'unavailable', 'rate_limited', 'invalid_request', 'local_state_error')
JEV_CODES = {
    'authorization_failed': 'authentication_required',
    'credential_missing': 'authentication_required',
    'credential_unavailable': 'local_state_error',
    'private_state_unavailable': 'local_state_error',
    'package_integrity_failed': 'local_state_error',
    'invalid_task_input': 'invalid_request',
    'invalid_provider_response': 'invalid_response',
    'response_too_large': 'invalid_response',
    'provider_unavailable': 'transport_error',
    'rate_limited': 'rate_limited',
}


def _version(package):
    try:
        metadata = json.loads((package / 'nda-plugin.json').read_text(encoding='utf-8'))
        version = metadata.get('version') if isinstance(metadata, dict) else None
    except (OSError, ValueError, RecursionError):
        return 'unknown'
    if isinstance(version, str) and len(version) <= 64 and re.fullmatch(
        r'[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?', version
    ):
        return version
    return 'unknown'


def _append(state, line):
    directory = state / 'logs'
    guard_path(directory / 'mcp-errors.jsonl', write=False)
    state.mkdir(exist_ok=True, mode=0o700)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    state_fd = os.open(state, flags)
    try:
        state_info = os.fstat(state_fd)
        if state_info.st_uid != os.getuid() or state_info.st_mode & 0o022:
            raise PermissionError()
        try:
            os.mkdir('logs', mode=0o700, dir_fd=state_fd)
        except FileExistsError:
            pass
        directory_fd = os.open('logs', flags, dir_fd=state_fd)
    finally:
        os.close(state_fd)
    try:
        if os.fstat(directory_fd).st_uid != os.getuid():
            raise PermissionError()
        os.fchmod(directory_fd, 0o700)
        fd = os.open('mcp-errors.jsonl', os.O_WRONLY | os.O_CREAT | os.O_APPEND |
                     os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=directory_fd)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
                raise PermissionError()
            os.fchmod(fd, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX)
            start = os.fstat(fd).st_size
            if os.write(fd, line) != len(line):
                os.ftruncate(fd, start)
                raise OSError('short append')
        finally:
            os.close(fd)
    finally:
        os.close(directory_fd)


def record_failure(state, package, client, server, operation, error_code):
    """Return a bounded outcome. Callers retain their original diagnostic."""
    if (client not in ('codex', 'cursor', 'claude') or not isinstance(server, str)
            or operation not in OPERATIONS.get(server, ()) or error_code not in ERROR_CODES):
        return 'invalid_event'
    event = {
        'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        'client': client, 'plugin_version': _version(package), 'server': server,
        'operation': operation, 'error_code': error_code,
    }
    try:
        _append(state, (json.dumps(event) + '\n').encode('utf-8'))
    except (OSError, Conflict):
        return 'local_write_failed'
    return 'recorded'
