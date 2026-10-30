import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

from nda_harness.usage import (
    append_event, event_from_record, read_events, render_html, render_text,
    set_stage, stage_for, summarize, write_report,
)


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / 'home'
        self.home.mkdir()
        self.project = Path(self.tmp.name) / 'project'
        self.project.mkdir()
        self.now = 1_700_000_000

    def event(self, **fields):
        base = {'client': 'cursor', 'project': 'a' * 16, 'session': 's', 'at': self.now}
        base.update(fields)
        return base

    def test_prompt_text_is_not_stored(self):
        append_event(self.home, self.event(kind='prompt', stage='unscoped', prompt='SECRET-prompt'), now=self.now)
        journal = (self.home / '.nda-harness' / 'usage' / 'events.jsonl').read_text(encoding='utf-8')
        self.assertNotIn('SECRET', journal)
        self.assertEqual(stat.S_IMODE((self.home / '.nda-harness' / 'usage').stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.home / '.nda-harness' / 'usage' / 'events.jsonl').stat().st_mode), 0o600)

    def test_record_rejects_extra_fields_and_long_errors(self):
        with self.assertRaises(ValueError):
            event_from_record({'schema_version': 1, 'kind': 'memory', 'operation': 'retain', 'outcome': 'failed', 'prompt': 'SECRET'}, client='cursor', project=self.project, session='s')
        with self.assertRaises(ValueError):
            append_event(self.home, self.event(kind='memory', operation='retain', outcome='failed', error='x' * 201), now=self.now)

    def test_report_covers_the_agreed_metrics(self):
        task = '.nda-harness/tasks/4-usage/task.md'
        rows = [
            self.event(kind='startup', status='blocked', source='hook', at=self.now - 10),
            self.event(kind='startup', status='ready', source='hook', at=self.now - 9),
            self.event(kind='context', operation='task-prepare', status='ready', stage='specification', task=task, spec_missing=False, at=self.now - 8),
            self.event(kind='prompt', stage='specification', at=self.now - 7),
            self.event(kind='context', operation='context-checkpoint', status='ready', stage='specification', task=task, spec_missing=False, at=self.now - 6),
            self.event(kind='context', operation='task-prepare', status='blocked', stage='implementation', task=task, spec_missing=True, at=self.now - 5),
            self.event(kind='spec_check', result='no_spec', task=task, at=self.now - 4),
            self.event(kind='spec_check', result='matched', task=task, at=self.now - 3),
            self.event(kind='subagent', summary_chars=8, task=task, at=self.now - 3),
            self.event(kind='subagent', summary_chars=4, task='.nda-harness/tasks/5-other/task.md', at=self.now - 3),
            self.event(kind='context', operation='task-prepare', status='ready', stage='implementation', task='.nda-harness/tasks/5-other/task.md', spec_missing=False, at=self.now - 2),
            self.event(kind='selection', action='attempt', resolved=False, at=self.now - 2),
            self.event(kind='selection', action='resolve', resolved=True, at=self.now - 1),
            self.event(kind='commit_gate', result='skip', duration_ms=1, at=self.now - 1),
            self.event(kind='commit_gate', result='pass', duration_ms=2, at=self.now),
            self.event(kind='memory', operation='retain', outcome='completed', operation_id='ok', error='', at=self.now),
            self.event(kind='memory', operation='retain', outcome='failed', operation_id='bad', error='timeout', at=self.now),
            self.event(kind='memory', operation='retain', outcome='accepted', operation_id='wait', error='', at=self.now),
            self.event(kind='memory', operation='create_bank', outcome='empty_bank', operation_id='', error='', at=self.now),
            self.event(kind='compact', at=self.now),
            self.event(kind='prompt', stage='unscoped', at=self.now - 40 * 86400),
        ]
        for row in rows:
            append_event(self.home, row, now=row['at'])
        report = summarize(read_events(self.home), now=self.now)
        week = report['windows']['7']
        self.assertEqual(week['workflows']['finished'], 1)
        self.assertEqual(week['workflows']['started'], 2)
        self.assertEqual(week['blocked_starts']['blocked'], 1)
        self.assertEqual(week['blocked_starts']['total'], 2)
        self.assertEqual(week['commit_gate']['real'], 1)
        self.assertEqual(week['commit_gate']['total'], 2)
        self.assertEqual(week['commit_gate']['first_try_pass'], 1.0)
        self.assertEqual(week['selection']['followed'], 1)
        self.assertEqual(week['turns']['specification'], 1)
        self.assertEqual(week['turns']['unscoped'], 0)
        self.assertEqual(week['subagents']['total'], 2)
        self.assertEqual(week['subagents']['summary_tokens'], 3)
        self.assertEqual(week['compactions'], 1)
        self.assertEqual(week['memory']['operations']['retain']['rate'], 0.5)
        self.assertEqual(week['memory']['operations']['retain']['accepted'], 1)
        self.assertEqual(week['memory']['empty_banks'], 1)
        self.assertEqual(week['memory']['errors'][0]['error'], 'timeout')
        self.assertEqual(week['spec_discipline']['by_reason']['no_spec'], 1)
        self.assertEqual(week['spec_discipline']['corrected'], 1)
        self.assertEqual(week['spec_discipline']['without_spec'], 2)
        text = render_text(report)
        self.assertIn('Empty banks: 1', text)
        self.assertNotIn('SECRET', text)
        path = write_report(self.home, report)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertIn('This report stays on this machine.', path.read_text(encoding='utf-8'))

    def test_docs_tasks_are_excluded_and_stage_labels_prompts(self):
        task = '.nda-harness/tasks/9-docs/task.md'
        append_event(self.home, self.event(kind='context', operation='task-prepare', status='ready', stage='implementation', task=task, spec_missing=False), now=self.now)
        append_event(self.home, self.event(kind='spec_check', result='docs', task=task), now=self.now)
        report = summarize(read_events(self.home), now=self.now)['windows']['7']
        self.assertEqual(report['spec_discipline']['lightweight'], 1)
        self.assertEqual(report['spec_discipline']['without_spec'], 0)
        set_stage(self.home, self.project, 'implementation')
        self.assertEqual(stage_for(self.home, self.project), 'implementation')

    def test_html_escapes_error_text(self):
        append_event(self.home, self.event(kind='memory', operation='recall', outcome='failed', operation_id='e1', error='<script>'), now=self.now)
        page = render_html(summarize(read_events(self.home), now=self.now))
        self.assertNotIn('<script>', page)
        self.assertIn('&lt;script&gt;', page)
        self.assertTrue(json.loads((self.home / '.nda-harness' / 'usage' / 'events.jsonl').read_text(encoding='utf-8').splitlines()[0])['error'] == '<script>')


if __name__ == '__main__':
    unittest.main()
