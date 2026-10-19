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


def profile_for(project):
    profile = load_json(project / '.nda-harness/profile.json')
    if profile is None:
        return None
    try:
        memory = profile['memory']
        if set(profile) != {'schema_version', 'test_command', 'memory'} or profile['schema_version'] != 2:
            raise ValueError()
        if not isinstance(profile['test_command'], str) or not profile['test_command'].strip():
            raise ValueError()
        if not isinstance(memory, dict) or set(memory) - {'identity_sha256', 'bank_id', 'remote', 'name'}:
            raise ValueError()
        if not re.fullmatch('[0-9a-f]{64}', memory['identity_sha256']) or memory['bank_id'] != 'nda-project-' + memory['identity_sha256'][:32]:
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise Conflict('Project profile is invalid; reconcile configuration before dependent work.') from None
    return profile


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


def configure(project, package, home, test_command=None, *, skip=False, name=None, remote=None):
    project, package, home = root_for(project), Path(package).resolve(), Path(home).resolve()
    if skip and test_command is not None:
        raise Conflict('Use an explicit test command or explicit Skip.')
    if test_command is not None and (not isinstance(test_command, str) or not test_command.strip() or '\x00' in test_command):
        raise Conflict('Provide a nonempty non-watch test command or explicit Skip.')
    state = state_for(project, home)
    with locked(state):
        receipt = recover(state, project, load_json(state / 'receipt.json', {'owned': {}}))
        previous = profile_for(project)
        selection = previous['memory'] if previous else {}
        identity = project_identity(project, name=name or selection.get('name'), remote=remote or selection.get('remote'))
        if previous and identity['identity_sha256'] != previous['memory']['identity_sha256']:
            raise Conflict('Project bank identity conflicts with current Git identity; reconcile explicitly before changing banks.')
        command = 'true' if skip else test_command if test_command is not None else previous['test_command'] if previous else None
        if command is None:
            return {'status': 'needs_configuration', 'test_command': 'pending', 'protection': 'incomplete',
                    'next': 'Ask the user for a non-watch test command or explicit Skip in agent chat; never infer Skip.'}
        profile = {'schema_version': 2, 'test_command': command, 'memory': identity}
        plan = Plan(receipt)
        # Project owners may edit committed configuration between sessions.
        plan.write(project / '.nda-harness/profile.json', json_bytes(profile))
        config = load_json(package / 'nda-plugin.json')
        repository = is_repository(project)
        registration = None
        if repository:
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
                if git(project, 'check-ignore', '-q', '.nda-harness/profile.json').returncode == 0:
                    raise Conflict('Project configuration is ignored by Git. Reconcile ignore rules so .nda-harness can be committed.')
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
            'bank_id': identity['bank_id'], 'environment': 'dev'}


def inspect_project(project, package, home):
    project = root_for(project)
    profile = profile_for(project)
    if profile is None:
        return {'status': 'needs_configuration', 'protection': 'incomplete'}
    if not is_repository(project):
        return {'status': 'ready', 'protection': 'not_applicable',
                'bank_id': profile['memory']['bank_id'], 'environment': 'dev',
                'test_command': 'skipped' if profile['test_command'] == 'true' else 'configured'}
    if git(project, 'check-ignore', '-q', '.nda-harness/profile.json').returncode == 0:
        raise Conflict('Project configuration is ignored by Git; reconcile ignore rules.')
    expected = project_identity(project, name=profile['memory'].get('name'), remote=profile['memory'].get('remote'))
    if expected['identity_sha256'] != profile['memory']['identity_sha256']:
        raise Conflict('Project bank identity conflicts with Git remote identity.')
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
            'test_command': 'skipped' if profile['test_command'] == 'true' else 'configured'}
