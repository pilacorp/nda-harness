"""Committed project configuration and private, composed Git hook activation."""
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import subprocess
import re
import shlex
from urllib.parse import urlsplit

from .bank_select import valid_bank_id
from .files import Plan, Conflict, atomic, digest, guard_path, json_bytes, read
from .hooks import git, hook_plan, activate, restore, value


@contextmanager
def locked(state):
    guard_path(state / 'setup.lock')
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    state.chmod(0o700)
    with (state / 'setup.lock').open('a') as lock:
        os.chmod(state / 'setup.lock', 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def root_for(path):
    """Git worktree root, or the directory itself when it is not a repository."""
    candidate = Path(path).expanduser().resolve()
    if not candidate.is_dir():
        raise Conflict('Open a project directory before configuring NDA Harness.')
    try:
        result = git(candidate, 'rev-parse', '--show-toplevel')
    except (OSError, subprocess.TimeoutExpired):
        raise Conflict('Git could not be inspected; reconcile the project directory.') from None
    if result.returncode == 0:
        return Path(result.stdout.strip()).resolve()
    if 'not a git repository' in (result.stderr or '').lower():
        return candidate
    raise Conflict('Open a project directory before configuring NDA Harness.')


def is_repository(project):
    result = git(project, 'rev-parse', '--is-inside-work-tree')
    return result.returncode == 0 and result.stdout.strip() == 'true'


def state_for(project, home):
    return home / '.nda-harness/plugin-projects' / digest(str(project))


def load_json(path, default=None):
    raw = read(path)
    try:
        data = json.loads(raw) if raw is not None else default
        if data is not None and not isinstance(data, dict):
            raise ValueError()
        return data
    except (ValueError, UnicodeError):
        raise Conflict('Invalid harness configuration or private receipt; reconcile locally.') from None


def canonical_remote(raw):
    # Never persist raw URLs, usernames, passwords, query parameters or private paths.
    if any(c.isspace() or ord(c) < 32 for c in raw):
        raise Conflict('Remote identity needs reconciliation.')
    scp = re.fullmatch(r'(?:[^/@:]+@)?([^/:]+):(.+)', raw) if '://' not in raw else None
    if scp:
        host, path = scp.groups()
    else:
        try:
            parsed = urlsplit(raw)
            if parsed.scheme not in ('https', 'ssh', 'git') or not parsed.hostname or parsed.password or parsed.query or parsed.fragment:
                raise ValueError()
            if parsed.port not in (None, 22 if parsed.scheme == 'ssh' else 443 if parsed.scheme == 'https' else 9418):
                raise ValueError()
            host, path = parsed.hostname, parsed.path
        except ValueError:
            raise Conflict('Remote identity is not a supported credential-free Git URL; select a project name explicitly.') from None
    path = path.strip('/')
    if path.endswith('.git'):
        path = path[:-4]
    if not re.fullmatch(r'[A-Za-z0-9.-]+', host) or not path or not re.fullmatch(r'[A-Za-z0-9_./-]+', path) or '..' in path.split('/'):
        raise Conflict('Remote identity needs reconciliation.')
    # GitHub/GitLab namespaces can be cloned with differing casing.
    if host.lower() in ('github.com', 'gitlab.com', 'bitbucket.org'):
        path = path.lower()
    return host.lower() + '/' + path


def project_identity(project, *, name=None, remote=None):
    remotes = git(project, 'remote')
    if remotes.returncode:
        # A folder that is not a repository has no remotes. Ask for a project name.
        if is_repository(project):
            raise Conflict('Cannot inspect project Git remotes.')
        names = []
    else:
        names = remotes.stdout.splitlines()
    if remote and remote not in names:
        raise Conflict('Selected remote does not exist.')
    if name and (not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,79}', name)):
        raise Conflict('Project name must be a lowercase slug of at most 80 characters.')
    if name and remote:
        raise Conflict('Choose a project name or a remote, not both.')
    if name:
        identity, selection = 'name:' + name, {'name': name}
    else:
        candidates = set()
        for item in ([remote] if remote else names):
            run = git(project, 'remote', 'get-url', '--all', item)
            if run.returncode:
                raise Conflict('Cannot inspect selected remote.')
            candidates.update(canonical_remote(raw) for raw in run.stdout.splitlines())
        if len(candidates) != 1:
            raise Conflict('Project identity is ambiguous or has no remote. Ask for a project name or explicit remote selection.')
        identity = 'git:' + next(iter(candidates))
        selection = {'remote': remote} if remote else {}
    fingerprint = digest(identity)
    return {'identity_sha256': fingerprint, 'bank_id': 'nda-project-' + fingerprint[:32], **selection}


def _valid_command(command):
    return isinstance(command, str) and bool(command.strip()) and '\x00' not in command


def _valid_memory(memory):
    if not isinstance(memory, dict) or set(memory) - {'identity_sha256', 'bank_id', 'remote', 'name', 'system'}:
        raise ValueError()
    if 'system' in memory and (not isinstance(memory['system'], str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,31}', memory['system'])):
        raise ValueError()
    if 'identity_sha256' in memory and not re.fullmatch('[0-9a-f]{64}', memory['identity_sha256']):
        raise ValueError()
    if 'name' in memory and not re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,79}', memory['name']):
        raise ValueError()
    if 'remote' in memory and (not isinstance(memory['remote'], str) or not memory['remote'] or '\x00' in memory['remote']):
        raise ValueError()
    if not valid_bank_id(memory.get('bank_id')):
        raise ValueError()
    return memory


def resolve_bank_id(stored, requested):
    """Use an explicit choice, otherwise the bank already stored in the profile."""
    if requested is not None:
        if not valid_bank_id(requested):
            raise Conflict('Bank id must be a short slug of letters, digits, dots, underscores, or hyphens.')
        return requested
    if valid_bank_id(stored):
        return stored
    return None


def stored_profile(project):
    """Return (kind, profile). kind is current, legacy, or None. Invalid files raise Conflict."""
    profile = load_json(project / '.nda-harness/profile.json')
    if profile is None:
        return None, None
    try:
        if set(profile) == {'schema_version', 'memory'} and profile['schema_version'] == 3:
            _valid_memory(profile['memory'])
            return 'current', profile
        if set(profile) == {'schema_version', 'test_command', 'memory'} and profile['schema_version'] == 2 and _valid_command(profile['test_command']):
            _valid_memory(profile['memory'])
            return 'legacy', profile
        raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise Conflict('Project profile is invalid; reconcile configuration before dependent work.') from None


_MEMORY_KEYS = {'identity_sha256', 'bank_id', 'remote', 'name', 'system'}


def validate_config(config):
    required = {'schema_version', 'test_command'}
    if (not isinstance(config, dict) or not required <= config.keys()
            or config.keys() - required - {'enabled', 'workflow_mode'}
            or type(config['schema_version']) is not int or config['schema_version'] != 1
            or not _valid_command(config['test_command'])
            or type(config.get('enabled', True)) is not bool
            or config.get('workflow_mode', 'strict') not in ('strict', 'fast')):
        raise Conflict('Project configuration is invalid; reconcile configuration before dependent work.')
    return config


def directory_config(project):
    """Read config.json in this directory only."""
    config = load_json(project / '.nda-harness/config.json')
    return validate_config(config) if config is not None else None


def harness_layers(project):
    """Outer harness directories first. The folder in the repo is last and wins."""
    project = Path(project).resolve()
    found = []
    current = project
    home = Path.home().resolve()
    while True:
        directory = current / '.nda-harness'
        if directory.is_dir() and not directory.is_symlink():
            found.append(current)
        parent = current.parent
        if parent == current or parent == home:
            break
        parent_harness = parent / '.nda-harness'
        parent_git = parent / '.git'
        if parent_harness.is_symlink() or parent_git.is_symlink():
            break
        if not parent_git.exists() and not parent_harness.is_dir():
            break
        current = parent
    found.reverse()
    return found


def _layer_profile(root, project):
    try:
        return stored_profile(root)
    except Conflict:
        if Path(root).resolve() == Path(project).resolve():
            raise
        return None, None


def effective_profile(project):
    """Merge ancestor profiles. Keys in the repo folder replace outer keys."""
    project = Path(project).resolve()
    memory = {}
    nearest = None
    nearest_profile = None
    for root in harness_layers(project):
        kind, profile = _layer_profile(root, project)
        if profile is None:
            continue
        if kind == 'legacy' and Path(root).resolve() == project:
            return kind, profile
        if kind not in ('current', 'legacy'):
            continue
        memory.update({key: value for key, value in profile['memory'].items() if key in _MEMORY_KEYS})
        nearest = kind
        nearest_profile = profile
    if nearest == 'current':
        try:
            _valid_memory(memory)
        except (KeyError, TypeError, ValueError):
            raise Conflict('Project profile is invalid; reconcile configuration before dependent work.') from None
        return 'current', {'schema_version': 3, 'memory': memory}
    return nearest, nearest_profile


def effective_config(project):
    """Merge test commands. A config.json in the repo replaces an outer one.

    ``enabled`` merges by key. A layer that omits it leaves the outer value.
    A missing field means the project stays on.
    """
    project = Path(project).resolve()
    command = None
    enabled = True
    for root in harness_layers(project):
        try:
            config = directory_config(root)
        except Conflict:
            if Path(root).resolve() == project:
                raise
            continue
        if config:
            command = config['test_command']
            if 'enabled' in config:
                enabled = config['enabled']
            continue
        kind, profile = _layer_profile(root, project)
        if kind == 'legacy':
            command = profile['test_command']
    if command is None:
        return None
    return {'schema_version': 1, 'test_command': command, 'enabled': enabled}


def project_disabled(project):
    """True only when a resolved config explicitly sets enabled to false."""
    try:
        config = config_for(project)
    except (Conflict, OSError, ValueError):
        return False
    return bool(config and config.get('enabled') is False)


DISABLED_MESSAGE = 'NDA Harness is disabled on the project'


def profile_for(project):
    kind, profile = effective_profile(project)
    return profile if kind == 'current' else None


def config_for(project):
    return effective_config(project)


def ensure_project_gitignore(plan, project):
    path = project / '.gitignore'
    original = read(path)
    patterns = (b'.nda-harness/tasks/', b'.nda-harness/profile.json', b'.nda-harness/skill-selection/')
    if original is None:
        plan.write(path, b'\n'.join(patterns) + b'\n')
        return
    newline = b'\r\n' if b'\r\n' in original else b'\n'
    missing = [pattern for pattern in patterns if pattern not in original.splitlines()]
    if not missing:
        return
    separator = newline if original and not original.endswith(b'\n') else b''
    plan.write(path, original + separator + newline.join(missing) + newline)


def recover(state, project, receipt):
    transaction = receipt.get('transaction')
    if not transaction:
        return receipt
    plan = Plan({})
    plan.applied = transaction['applied']
    if plan.rollback():
        raise Conflict('Interrupted setup contains subsequently edited files; private backups require reconciliation.')
    restore(project, transaction['git'])
    prior = transaction['prior']
    atomic(state / 'receipt.json', json_bytes(prior))
    return prior


def configure(project, package, home, test_command=None, *, skip=False, name=None, remote=None, system=None, bank_id=None, enable=False):
    project, package, home = root_for(project), Path(package).resolve(), Path(home).resolve()
    if skip and test_command is not None:
        raise Conflict('Use an explicit test command or explicit Skip.')
    if test_command is not None and (not isinstance(test_command, str) or not test_command.strip() or '\x00' in test_command):
        raise Conflict('Provide a nonempty non-watch test command or explicit Skip.')
    state = state_for(project, home)
    with locked(state):
        receipt = recover(state, project, load_json(state / 'receipt.json', {'owned': {}}))
        kind, stored = stored_profile(project)
        previous = stored if kind == 'current' else None
        legacy = stored if kind == 'legacy' else None
        existing = directory_config(project)
        if legacy and existing and existing['test_command'] != legacy['test_command']:
            raise Conflict('Project test command conflicts with the saved profile; reconcile the two files before setup.')
        selection = (previous or legacy or {}).get('memory', {})
        # name and remote no longer choose the bank. They remain accepted so older callers do not break.
        del name, remote
        bank = resolve_bank_id(selection.get('bank_id'), bank_id)
        command = 'true' if skip else test_command if test_command is not None else existing['test_command'] if existing else legacy['test_command'] if legacy else None
        if command is None or bank is None:
            pending = {'status': 'needs_configuration', 'protection': 'incomplete'}
            if command is None:
                pending['test_command'] = 'pending'
                pending['next'] = 'Ask the user for a non-watch test command or explicit Skip in agent chat; never infer Skip.'
            if bank is None:
                pending['bank_id'] = 'pending'
                pending.setdefault('next', 'Run select-bank so the user can choose or create a Hindsight bank, then rerun setup with --bank-id.')
            return pending
        from nda_harness.memory import select_system
        chosen = select_system(load_json(package / 'nda-plugin.json') or {}, requested=system, previous=selection.get('system'))
        memory = {'bank_id': bank}
        if chosen:
            memory['system'] = chosen
        profile = {'schema_version': 3, 'memory': memory}
        project_config = {'schema_version': 1, 'test_command': command}
        if existing and 'workflow_mode' in existing:
            project_config['workflow_mode'] = existing['workflow_mode']
        if enable:
            project_config['enabled'] = True
        elif existing and 'enabled' in existing:
            project_config['enabled'] = existing['enabled']
        plan = Plan(receipt)
        plan.write(project / '.nda-harness/profile.json', json_bytes(profile))
        plan.write(project / '.nda-harness/config.json', json_bytes(project_config))
        config = load_json(package / 'nda-plugin.json')
        repository = is_repository(project)
        registration = None
        if repository:
            ensure_project_gitignore(plan, project)
            check = shlex.join([str(package / 'bin/nda-plugin'), 'unit-check', '--client', config['client'], '--project', str(project)])
            registration = hook_plan(plan, project, state, receipt, check_command=check)
        def journal(current):
            transaction = {'prior': receipt, 'applied': current.applied}
            if registration:
                transaction['git'] = registration
            atomic(state / 'receipt.json', json_bytes({'transaction': transaction}))
        try:
            plan.apply(state, journal=journal)
            if repository:
                if git(project, 'check-ignore', '-q', '.nda-harness/config.json').returncode == 0:
                    raise Conflict('Project configuration is ignored by Git. Reconcile ignore rules so .nda-harness/config.json can be committed.')
                activate(project, registration)
            saved = {'schema_version': 1, 'owned': plan.owned, 'package': str(package), 'client': config['client']}
            if registration:
                saved['git'] = registration
            atomic(state / 'receipt.json', json_bytes(saved))
        except BaseException:
            if registration:
                restore(project, registration)
            unresolved = plan.rollback()
            if not unresolved:
                atomic(state / 'receipt.json', json_bytes(receipt))
            raise
    return {'status': 'ready', 'protection': 'active' if is_repository(project) else 'not_applicable',
            'test_command': 'skipped' if command == 'true' else 'configured',
            'bank_id': bank, 'environment': 'dev'}


def inspect_project(project, package, home):
    project = root_for(project)
    kind, profile = effective_profile(project)
    project_config = effective_config(project)
    if kind != 'current' or project_config is None:
        return {'status': 'needs_configuration', 'protection': 'incomplete'}
    command = project_config['test_command']
    if not is_repository(project):
        return {'status': 'ready', 'protection': 'not_applicable',
                'bank_id': profile['memory']['bank_id'], 'environment': 'dev',
                'test_command': 'skipped' if command == 'true' else 'configured'}
    if git(project, 'check-ignore', '-q', '.nda-harness/config.json').returncode == 0:
        raise Conflict('Project configuration is ignored by Git; reconcile ignore rules.')
    state = state_for(project, home)
    receipt = load_json(state / 'receipt.json', {})
    registration = receipt.get('git', {})
    active = registration and not receipt.get('transaction') and value(project, 'config', '--get', 'core.hooksPath') == registration.get('written_value')
    wrapper = state / 'hooks/pre-commit'
    active = active and wrapper.is_file() and not wrapper.is_symlink() and os.access(wrapper, os.X_OK)
    if active:
        active_package = Path(receipt.get('package', ''))
        expected_command = shlex.join([str(active_package / 'bin/nda-plugin'), 'unit-check', '--client', receipt.get('client', ''), '--project', str(project)])
        active = (active_package / 'bin/nda-plugin').is_file() and expected_command in wrapper.read_text() and digest(wrapper.read_bytes()) == receipt.get('owned', {}).get(str(wrapper) + '::file')
    return {'status': 'ready' if active else 'needs_activation', 'protection': 'active' if active else 'incomplete',
            'bank_id': profile['memory']['bank_id'], 'environment': 'dev',
            'test_command': 'skipped' if command == 'true' else 'configured'}
