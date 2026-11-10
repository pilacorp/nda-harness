"""Fast workflow checks against a Git checkout and fixture GitHub responses."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from nda_harness import plugin_build, workflow
from nda_harness.plugin_runtime import unit_check
from nda_harness.project import directory_config


class FastWorkflowTests(unittest.TestCase):
    repo = 'repos/team/project'
    target, approved, head = 'a' * 40, 'b' * 40, 'c' * 40
    spec_path = 'specs/feature.md'
    spec = b'# Behavior and acceptance\n'
    issue_url = 'https://github.com/team/project/issues/42'

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name).resolve()
        subprocess.run(['git', 'init', '-q', '-b', 'feature', str(self.project)], check=True)
        subprocess.run(['git', '-C', str(self.project), 'remote', 'add', 'origin',
                        'git@github.com:team/project.git'], check=True)
        (self.project / 'specs').mkdir()
        (self.project / self.spec_path).write_bytes(self.spec)
        (self.project / '.nda-harness').mkdir()
        self.config_path = self.project / '.nda-harness/config.json'
        self.config = {'schema_version': 1, 'test_command': 'true', 'workflow_mode': 'fast'}
        self.config_path.write_text(json.dumps(self.config))
        self.owner = {'login': 'owner', 'id': 1, 'type': 'User'}
        self.issue = {'number': 42, 'state': 'open', 'title': 'Feature', 'body': 'Type: feature\nNew behavior'}
        self.pr = {'number': 7, 'state': 'open', 'draft': False, 'body': 'Closes #42',
                   'base': {'ref': 'main', 'repo': {'id': 77}}, 'head': {'sha': self.head}}
        self.comments = []
        self.reviews = []
        self.checks = [{'head_sha': self.head, 'status': 'completed', 'conclusion': 'success'}]
        self.status = {'sha': self.head, 'total_count': 0, 'state': 'pending'}
        self.remote_config = self.config.copy()

    def api(self, path, *, paginate=False):
        if path == 'orgs/team/memberships/owner':
            return {'state': 'active', 'role': 'admin', 'user': self.owner, 'organization': {'id': 8}}
        path = path.removeprefix(self.repo)
        if path.startswith('/git/commits/'):
            sha = path.rsplit('/', 1)[-1]
            if sha not in (self.target, self.approved, self.head):
                raise ValueError('missing remote commit')
            return {'sha': sha, 'tree': {'sha': sha}}
        if path.startswith('/git/trees/'):
            sha = path.rsplit('/', 1)[-1]
            entries = ({
                self.target: [('.nda-harness', '040000', 'd' * 40)],
                self.approved: [('specs', '040000', 'e' * 40)],
                self.head: [('specs', '040000', 'e' * 40)],
                'd' * 40: [('config.json', '100644', 'f' * 40)] if self.remote_config is not None else [],
                'e' * 40: [('feature.md', '100644', '1' * 40)],
            })[sha]
            return {'sha': sha, 'truncated': False, 'tree': [
                {'path': name, 'mode': mode, 'sha': oid} for name, mode, oid in entries
            ]}
        if path.startswith('/git/blobs/'):
            sha = path.rsplit('/', 1)[-1]
            raw = json.dumps(self.remote_config).encode() if sha == 'f' * 40 else self.spec
            return {'sha': sha, 'encoding': 'base64', 'content': base64.b64encode(raw).decode()}
        return {
            '': {'id': 77, 'full_name': 'team/project', 'default_branch': 'main',
                 'owner': {'login': 'team', 'id': 8, 'type': 'Organization'}},
            '/git/ref/heads/main': {'ref': 'refs/heads/main', 'object': {'type': 'commit', 'sha': self.target}},
            '/issues/42': self.issue,
            '/issues/42/comments': [self.comments],
            '/pulls/7': self.pr,
            '/issues/7/comments': [self.reviews],
            f'/commits/{self.head}/check-runs': [{'total_count': len(self.checks), 'check_runs': self.checks}],
            f'/commits/{self.head}/status': self.status,
        }[path]

    def verify(self, **options):
        return workflow.verify(self.api, self.project, self.issue_url, self.spec_path, **options)

    def comment(self, text, **fields):
        return {'id': 1, 'body': text, 'user': self.owner, 'performed_via_github_app': None, **fields}

    def signoff(self):
        fingerprint = self.verify()['issue_fingerprint']
        self.comments.append(self.comment(
            f'NDA fast spec: main {self.spec_path} {self.approved} {fingerprint}'
        ))

    def test_only_committed_target_config_can_opt_in_and_unit_gate_stays_local(self):
        self.assertEqual(directory_config(self.project)['workflow_mode'], 'fast')
        with patch.object(workflow, 'github', side_effect=AssertionError('network in unit gate')):
            self.assertEqual(unit_check(self.project), 0)
        self.remote_config.pop('workflow_mode')
        self.assertEqual(self.verify()['workflow_mode'], 'strict')
        self.remote_config = None
        self.assertEqual(self.verify()['workflow_mode'], 'strict')
        self.remote_config = {**self.config, 'workflow_mode': True}
        self.assertEqual(self.verify()['status'], 'blocked')

    def test_local_or_pr_head_cannot_be_its_own_fast_target(self):
        self.pr['head'].update(ref='main', repo={'id': 77})
        self.assertEqual(self.verify(pr_number=7)['diagnostic'], 'fast_requires_separate_branch')
        self.pr['base']['repo']['id'] = 88
        self.assertEqual(self.verify(pr_number=7)['diagnostic'], 'pull_request_mismatch')

    def test_owner_signoff_is_bound_to_issue_target_remote_commit_and_local_bytes(self):
        self.assertEqual(self.verify()['diagnostic'], 'owner_spec_signoff_required')
        self.signoff()
        self.assertEqual(self.verify()['status'], 'verified')
        comment = self.comments[0]
        comment['performed_via_github_app'] = {'id': 123}
        self.assertEqual(self.verify()['status'], 'blocked')
        comment['performed_via_github_app'] = None
        comment['user'] = {**self.owner, 'id': 3}
        self.assertEqual(self.verify()['status'], 'blocked')
        comment['user'] = self.owner
        original = comment['body']
        comment['body'] = original.replace(self.approved, '2' * 40)
        self.assertEqual(self.verify()['status'], 'blocked')
        comment['body'] = original
        (self.project / self.spec_path).write_bytes(b'unapproved changes')
        self.assertEqual(self.verify()['status'], 'blocked')
        (self.project / self.spec_path).write_bytes(self.spec)
        self.issue['title'] = 'Changed intent'
        self.assertEqual(self.verify()['status'], 'blocked')

    def test_final_head_requires_owner_review_ci_and_issue_link(self):
        self.signoff()
        self.assertEqual(self.verify(pr_number=7, before_merge=True)['diagnostic'], 'owner_head_review_required')
        self.reviews.append(self.comment('NDA fast review: ' + '2' * 40))
        self.assertEqual(self.verify(pr_number=7, before_merge=True)['status'], 'blocked')
        self.reviews.append(self.comment('NDA fast review: ' + self.head))
        self.assertEqual(self.verify(pr_number=7, before_merge=True)['status'], 'verified')
        self.pr['head']['sha'] = self.approved  # Same spec, different revision.
        self.assertEqual(self.verify(pr_number=7, before_merge=True)['diagnostic'], 'owner_head_review_required')
        self.pr['head']['sha'] = self.head
        self.checks[0]['conclusion'] = 'failure'
        self.assertEqual(self.verify(pr_number=7, before_merge=True)['status'], 'blocked')
        self.checks[0]['conclusion'] = 'success'
        self.status.update(total_count=1, state='failure')
        self.assertEqual(self.verify(pr_number=7, before_merge=True)['status'], 'blocked')
        self.status.update(total_count=0, state='pending')
        self.checks.clear()
        self.assertEqual(self.verify(pr_number=7, before_merge=True)['status'], 'blocked')
        self.pr['body'] = 'Closes #43'
        self.assertEqual(self.verify(pr_number=7, before_merge=True)['diagnostic'], 'issue_link_required')
        self.pr['body'] = '\x60\x60\x60text\nCloses #42\n\x60\x60\x60'
        self.assertEqual(self.verify(pr_number=7, before_merge=True)['diagnostic'], 'issue_link_required')

    def test_packaged_command_verifies_strict_and_fast_against_a_test_repository(self):
        package = plugin_build.build(Path(__file__).resolve().parents[1], self.project / 'package', 'cursor')
        task = self.project / '.nda-harness/task.md'
        task.write_text(f'Issue: {self.issue_url}\nType: feature\nSpec: {self.spec_path}\n')
        replies = {}

        def record(endpoint, *, paginate=False):
            response = self.api(endpoint, paginate=paginate)
            replies[endpoint] = response
            return response

        fixture = self.project / 'responses.json'
        gh = self.project / 'gh'
        gh.write_text(
            '#!/usr/bin/env python3\nimport json, sys\nfrom pathlib import Path\n'
            'assert sys.argv[1:6] == ["api", "--hostname", "github.com", "--method", "GET"]\n'
            'print(json.dumps(json.loads(Path(__file__).with_name("responses.json").read_text())[sys.argv[-1]]))\n'
        )
        gh.chmod(0o755)
        command = [str(package / 'bin/nda-plugin'), 'workflow-check', '--client', 'cursor',
                   '--project', str(self.project), '--task', str(task.relative_to(self.project))]

        def run(expected, *args):
            fixture.write_text(json.dumps(replies))
            result = subprocess.run([*command, *args], capture_output=True, text=True, check=True,
                                    env={**os.environ, 'PATH': str(self.project) + os.pathsep + os.environ['PATH']})
            self.assertEqual(json.loads(result.stdout)['status'], expected)

        self.remote_config.pop('workflow_mode')
        workflow.verify(record, self.project, self.issue_url, self.spec_path)
        run('strict')
        self.remote_config = self.config
        self.signoff()
        self.reviews.append(self.comment('NDA fast review: ' + self.head))
        workflow.verify(record, self.project, self.issue_url, self.spec_path, pr_number=7, before_merge=True)
        run('verified', '--pr', '7', '--before-merge')
