"""Read-only verification of fast workflow evidence from GitHub."""
import base64
import json
import os
from pathlib import PurePosixPath
import re
import subprocess
from urllib.parse import quote

from nda_harness.files import digest, json_bytes, read
from nda_harness.hooks import git
from nda_harness.project import canonical_remote, validate_config

ISSUE = re.compile(r'https://github\.com/([\w.-]+/[\w.-]+)/issues/([1-9][0-9]*)', re.ASCII)
SHA = re.compile(r'[a-f0-9]{40}')
LOGIN = re.compile(r'[a-zA-Z0-9-]+')


def github(endpoint, *, paginate=False):
    """Use existing GitHub CLI authentication; never output raw API errors or content."""
    flags = ['--paginate', '--slurp'] if paginate else []
    result = subprocess.run(
        ['gh', 'api', '--hostname', 'github.com', '--method', 'GET', *flags, endpoint],
        capture_output=True, timeout=30, check=True,
        env={**os.environ, 'GH_PROMPT_DISABLED': '1', 'GH_NO_UPDATE_NOTIFIER': '1'},
    )
    return json.loads(result.stdout)


def _sha(value):
    if not isinstance(value, str) or not SHA.fullmatch(value):
        raise ValueError('invalid remote SHA')
    return value


def _unique_keys(pairs):
    result = dict(pairs)
    if len(result) != len(pairs):
        raise ValueError('duplicate config key')
    return result


def _file(api, repo, revision, path):
    """Resolve only regular blobs at an immutable remote commit (never follow symlinks)."""
    commit = api(f'{repo}/git/commits/{revision}')
    if commit['sha'] != revision:
        raise ValueError('remote commit mismatch')
    oid = _sha(commit['tree']['sha'])
    parts = PurePosixPath(path).parts
    for i, part in enumerate(parts):
        tree = api(f'{repo}/git/trees/{oid}')
        if tree['sha'] != oid or tree['truncated'] is not False:
            raise ValueError('incomplete tree evidence')
        entry = next((item for item in tree['tree'] if item['path'] == part), None)
        if entry is None:
            return None
        modes = ('100644', '100755') if i == len(parts) - 1 else ('040000',)
        if entry['mode'] not in modes:
            raise ValueError('unsafe remote file mode')
        oid = _sha(entry['sha'])
    blob = api(f'{repo}/git/blobs/{oid}')
    if blob['sha'] != oid or blob['encoding'] != 'base64':
        raise ValueError('remote blob mismatch')
    return base64.b64decode(''.join(blob['content'].splitlines()), validate=True)


def _owner(api, owner, comment):
    user = comment.get('user') or {}
    login = user.get('login', '')
    if (comment.get('performed_via_github_app') is not None or user.get('type') != 'User'
            or not LOGIN.fullmatch(login) or type(user.get('id')) is not int):
        return False
    if owner['type'] == 'User':
        return owner['id'] == user['id']
    if owner['type'] != 'Organization' or not LOGIN.fullmatch(owner['login']):
        return False
    try:
        member = api(f"orgs/{owner['login']}/memberships/{login}")
    except (subprocess.SubprocessError, OSError, ValueError):
        return False
    return (member['state'] == 'active' and member['role'] == 'admin'
            and member['user']['id'] == user['id'] and member['organization']['id'] == owner['id'])


def _comments(api, repo, number):
    return [comment for page in api(f'{repo}/issues/{number}/comments', paginate=True) for comment in page]


def _issue_fingerprint(issue, number):
    if (issue['number'] != number or issue['state'] != 'open' or 'pull_request' in issue
            or not isinstance(issue['title'], str)
            or (issue['body'] is not None and not isinstance(issue['body'], str))):
        raise ValueError('not an open issue')
    return digest(json_bytes([issue['title'], issue['body']]))


def _target_head(api, repo, target):
    ref = api(f'{repo}/git/ref/heads/{quote(target, safe="")}')
    if ref['ref'] != f'refs/heads/{target}' or ref['object']['type'] != 'commit':
        raise ValueError('target branch mismatch')
    return _sha(ref['object']['sha'])


def _passing_ci(api, repo, head):
    pages = api(f'{repo}/commits/{head}/check-runs', paginate=True)
    runs = [run for page in pages for run in page['check_runs']]
    if not pages or pages[0]['total_count'] != len(runs):
        return False
    statuses = api(f'{repo}/commits/{head}/status')
    has_status = statuses['total_count'] > 0
    return (statuses['sha'] == head
            and all(run['head_sha'] == head and run['status'] == 'completed'
                and run['conclusion'] in ('success', 'neutral', 'skipped') for run in runs)
            and (not has_status or statuses['state'] == 'success')
            and (has_status or any(run['conclusion'] == 'success' for run in runs)))


def verify(api, project, issue_url, spec_path, *, pr_number=None, before_merge=False):
    report = {'status': 'blocked', 'implementation_authorized': False}

    def blocked(code):
        return {**report, 'diagnostic': code}

    try:
        match = ISSUE.fullmatch(issue_url)
        if not match or (before_merge and pr_number is None):
            return blocked('workflow_inputs_invalid')
        name, number = match[1].lower(), int(match[2])
        if any(part in ('.', '..') for part in name.split('/')):
            return blocked('workflow_inputs_invalid')
        remotes = git(project, 'remote')
        urls = [raw for remote in remotes.stdout.splitlines()
                for raw in git(project, 'remote', 'get-url', '--all', remote).stdout.splitlines()]
        if not any(canonical_remote(raw) == f'github.com/{name}' for raw in urls):
            return blocked('issue_repository_mismatch')
        repo = f'repos/{name}'
        repository = api(repo)
        if repository['full_name'].lower() != name:
            return blocked('issue_repository_mismatch')
        pr = api(f'{repo}/pulls/{pr_number}') if pr_number is not None else None
        if pr is not None and (pr['number'] != pr_number or pr['state'] != 'open'
                               or pr['base']['repo']['id'] != repository['id']):
            return blocked('pull_request_mismatch')
        target = pr['base']['ref'] if pr is not None else repository['default_branch']
        if not isinstance(target, str) or not target or any(c.isspace() for c in target):
            return blocked('target_branch_invalid')
        target_head = _target_head(api, repo, target)
        config_blob = _file(api, repo, target_head, '.nda-harness/config.json')
        config = {} if config_blob is None else validate_config(json.loads(config_blob, object_pairs_hook=_unique_keys))
        report.update(target_branch=target, target_revision=target_head)
        if config.get('workflow_mode') != 'fast':
            return {**report, 'status': 'strict', 'workflow_mode': 'strict'}
        report['workflow_mode'] = 'fast'
        if (config.get('enabled') is False
                or git(project, 'symbolic-ref', '--quiet', '--short', 'HEAD').stdout.strip() == target
                or (pr and pr['head'].get('ref') == target
                    and (pr['head'].get('repo') or {}).get('id') == repository['id'])):
            return blocked('fast_requires_separate_branch')
        path = PurePosixPath(spec_path)
        if (path.is_absolute() or not path.parts or '..' in path.parts
                or path.as_posix() != spec_path or re.search(r'[\\\x00-\x1f\x7f]', spec_path)):
            return blocked('local_spec_invalid')
        local_spec = read(project / spec_path)
        if not local_spec:
            return blocked('local_spec_invalid')
        issue_endpoint = f'{repo}/issues/{number}'
        fingerprint = _issue_fingerprint(api(issue_endpoint), number)
        report['issue_fingerprint'] = fingerprint
        marker = re.compile(rf'NDA fast spec: {re.escape(target)} {re.escape(spec_path)} ({SHA.pattern}) {fingerprint}')
        for comment in reversed(_comments(api, repo, number)):
            signoff = marker.fullmatch((comment.get('body') or '').strip())
            if signoff and _owner(api, repository['owner'], comment):
                approved = signoff[1]
                break
        else:
            return blocked('owner_spec_signoff_required')
        if _file(api, repo, approved, spec_path) != local_spec:
            return blocked('approved_spec_mismatch')
        report.update(spec_revision=approved, spec_comment_id=comment['id'])
        if before_merge:
            head = _sha(pr['head']['sha'])
            report['pr_head'] = head
            if pr['draft'] is not False:
                return blocked('pull_request_is_draft')
            first_line = next((line for line in (pr['body'] or '').splitlines() if line.strip()), '')
            if first_line != f'Closes #{number}':
                return blocked('issue_link_required')
            if _file(api, repo, head, spec_path) != local_spec:
                return blocked('approved_spec_mismatch')
            for review in reversed(_comments(api, repo, pr_number)):
                if ((review.get('body') or '').strip() == f'NDA fast review: {head}'
                        and _owner(api, repository['owner'], review)):
                    report['review_comment_id'] = review['id']
                    break
            else:
                return blocked('owner_head_review_required')
            if not _passing_ci(api, repo, head):
                return blocked('passing_ci_required')
        if (_issue_fingerprint(api(issue_endpoint), number) != fingerprint
                or _target_head(api, repo, target) != target_head
                or read(project / spec_path) != local_spec
                or (pr is not None and api(f'{repo}/pulls/{pr_number}') != pr)):
            return blocked('workflow_inputs_changed')
        return {**report, 'status': 'verified'}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, subprocess.SubprocessError):
        return blocked('workflow_evidence_unavailable')
