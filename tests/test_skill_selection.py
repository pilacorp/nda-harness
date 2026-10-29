"""Catalog agreement and deterministic Jev skill selection."""
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from nda_harness.credentials import selection_setup
from nda_harness.openrouter import DECISIONS_URL, post_decision, selection_verify
from nda_harness.skill_selection import (
    SelectionError, build_decision_request, classify_answers, input_fingerprint, load_catalog,
    load_selected_skills, read_resolution_request, read_selection_request, record_selection, select_skills, validate_task_input,
)


class _TTY:
    def __init__(self, answers):
        self.answers = list(answers)

    def isatty(self):
        return True

    def write(self, text):
        return len(text)

    def flush(self):
        return None

    def readline(self):
        return self.answers.pop(0) if self.answers else 'n\n'


class _Pipe:
    def __init__(self, text):
        self.text = text

    def isatty(self):
        return False

    def read(self, limit):
        return self.text[:limit]


class _Transport:
    def __init__(self, probabilities, status=200, delay=0):
        self.probabilities = probabilities
        self.status = status
        self.delay = delay
        self.calls = []

    def __call__(self, url, payload, headers):
        if self.delay:
            time.sleep(self.delay)
        self.calls.append((url, payload, headers))
        body = json.dumps({
            'answers': {skill: {'noul': probability, 'type': 'noul'} for skill, probability in self.probabilities.items()},
            'id': 'gen-cache', 'model': 'typesafe/jev-1.14',
            'usage': {'cost': 0, 'input_tokens': 2, 'output_tokens': 1},
        }).encode()
        return self.status, body


class _Keychain:
    def __init__(self, secret, status='present'):
        self.secret = secret
        self._status = status
        self.reads = 0
        self.writes = 0

    def status(self):
        if self._status != 'present':
            return self._status
        return 'missing' if self.secret is None else 'present'

    def read(self):
        self.reads += 1
        return self.secret

    def write(self, secret):
        self.secret = secret
        self.writes += 1
        self._status = 'present'

    def delete(self):
        self.secret = None


def task(**overrides):
    value = {
        'schema_version': 1,
        'request': 'Add a settings page for the existing account area.',
        'stage': 'implementation',
        'project_facts': {'stack': ['React'], 'deliverables': ['settings interface'], 'constraints': ['use the existing design system']},
    }
    value.update(overrides)
    return value


class SelectionTests(unittest.TestCase):
    def test_shipped_catalog_matches_human_links(self):
        catalog = json.loads((ROOT / 'skills/catalog.json').read_text())
        text = (ROOT / 'skills/catalog.md').read_text()
        links = re.findall(r'\(([^)]+/SKILL\.md)\)', text)
        skills = catalog['skills']
        self.assertEqual([skill['id'] for skill in skills], sorted(skill['id'] for skill in skills))
        self.assertEqual(sorted(skill['entrypoint'] for skill in skills), sorted(links))
        for skill in skills:
            self.assertEqual(skill['id'], skill['entrypoint'].split('/', 1)[0])
            self.assertIn(f']({skill["entrypoint"]})', text)

    def test_invalid_task_input_uses_a_stable_code(self):
        long_fact = 'x' * 501
        oversized = task()
        oversized['request'] = 'y' * 4000
        oversized['project_facts'] = {key: ['z' * 500] * 20 for key in ('stack', 'deliverables', 'constraints')}
        cases = (
            task(extra=True),
            task(request=1),
            task(request='   '),
            task(request='n' * 8001),
            task(project_facts={'stack': ['a'] * 21, 'deliverables': [], 'constraints': []}),
            task(project_facts={'stack': [long_fact], 'deliverables': [], 'constraints': []}),
            oversized,
            task(stage='deploy'),
            {key: value for key, value in task().items() if key != 'project_facts'},
        )
        for data in cases:
            with self.subTest(data=list(data) if isinstance(data, dict) else data):
                with self.assertRaises(SelectionError) as caught:
                    validate_task_input(data)
                self.assertEqual(caught.exception.code, 'invalid_task_input')
                self.assertNotIn('settings page', str(caught.exception))
                self.assertNotIn('n' * 20, str(caught.exception))

    def test_equivalent_inputs_share_one_fingerprint(self):
        composed = 'é'
        first = task(request='  e\u0301\r\nline  ')
        first['project_facts']['stack'] = ['b', 'a', 'a']
        second = task(request=f'{composed}\nline')
        second['project_facts']['stack'] = ['a', 'b']
        self.assertEqual(input_fingerprint(first), input_fingerprint(second))
        changed = task(request=f'{composed}\nline', stage='review')
        changed['project_facts']['stack'] = ['a', 'b']
        self.assertNotEqual(input_fingerprint(first), input_fingerprint(changed))

    def test_catalog_entrypoints_must_be_regular_files_inside_the_hub(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root.parent / f'outside-{os.getpid()}.md'
            outside.write_text('outside', encoding='utf-8')
            self.addCleanup(outside.unlink, missing_ok=True)
            skill = root / 'diagram-design'
            skill.mkdir()
            body = skill / 'SKILL.md'
            body.write_text('regular', encoding='utf-8')
            linked = skill / 'linked.md'
            linked.symlink_to(body)
            cases = (
                '../' + outside.name,
                str(body),
                'diagram-design/linked.md',
                'diagram-design/missing.md',
            )
            for entrypoint in cases:
                with self.subTest(entrypoint=entrypoint):
                    self._write_catalog(root, entrypoint)
                    with self.assertRaises(SelectionError) as caught:
                        load_catalog(root)
                    self.assertEqual(caught.exception.code, 'invalid_catalog')
            self._write_catalog(root, 'diagram-design/SKILL.md')
            loaded = load_catalog(root)
            self.assertEqual(loaded['skills'][0]['entrypoint'], 'diagram-design/SKILL.md')

    def test_decision_request_uses_metadata_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill = root / 'diagram-design'
            skill.mkdir()
            (skill / 'SKILL.md').write_text('SENTINEL_BODY_NOT_FOR_JEV', encoding='utf-8')
            self._write_catalog(root, 'diagram-design/SKILL.md', select_when='Create a diagram.', exclude_when='Only discuss one.')
            catalog = load_catalog(root)
            request = build_decision_request(task(request='Draw the deploy flow.'), catalog)
            encoded = json.dumps(request)
            self.assertNotIn('SENTINEL_BODY_NOT_FOR_JEV', encoded)
            self.assertEqual(list(request['questions']), ['diagram-design'])
            question = request['questions']['diagram-design']
            self.assertEqual(question['type'], 'noul')
            self.assertEqual(question['criteria']['true'], 'Create a diagram.')
            self.assertEqual(question['criteria']['false'], 'Only discuss one.')
            self.assertNotIn('SKILL.md', json.dumps(request['state']))

    def test_shipped_catalog_loads(self):
        catalog = load_catalog(ROOT / 'skills')
        self.assertEqual([skill['id'] for skill in catalog['skills']],
                         ['diagram-design', 'ui-ux-pro-max', 'vietnamese-official-wording'])

    def test_probability_sets_select_zero_one_or_many(self):
        catalog = load_catalog(ROOT / 'skills')
        low = self._classify(catalog, {'diagram-design': 0.04, 'ui-ux-pro-max': 0.02, 'vietnamese-official-wording': 0.01})
        self.assertEqual(low['status'], 'ready')
        self.assertEqual(low['selected'], [])
        self.assertEqual(set(low['probabilities']), {skill['id'] for skill in catalog['skills']})
        one = self._classify(catalog, {'diagram-design': 0.04, 'ui-ux-pro-max': 0.96, 'vietnamese-official-wording': 0.02})
        self.assertEqual(one['selected'], [{'entrypoint': 'ui-ux-pro-max/SKILL.md', 'id': 'ui-ux-pro-max'}])
        two = self._classify(catalog, {'diagram-design': 0.91, 'ui-ux-pro-max': 0.9, 'vietnamese-official-wording': 0.1})
        self.assertEqual([item['id'] for item in two['selected']], ['diagram-design', 'ui-ux-pro-max'])
        self.assertEqual([item['entrypoint'] for item in two['selected']], ['diagram-design/SKILL.md', 'ui-ux-pro-max/SKILL.md'])
        self.assertFalse(one['implementation_authorized'])
        self.assertTrue(one['selection_id'].startswith('sha256:'))

    def test_thresholds_reject_uncertain_and_invalid_answers(self):
        catalog = load_catalog(ROOT / 'skills')
        self.assertEqual(self._classify(catalog, {'diagram-design': 0.20, 'ui-ux-pro-max': 0.20, 'vietnamese-official-wording': 0.20})['selected'], [])
        selected = self._classify(catalog, {'diagram-design': 0.80, 'ui-ux-pro-max': 0.80, 'vietnamese-official-wording': 0.80})['selected']
        self.assertEqual([item['id'] for item in selected], ['diagram-design', 'ui-ux-pro-max', 'vietnamese-official-wording'])
        for probability in (0.21, 0.79):
            result = self._classify(catalog, {'diagram-design': probability, 'ui-ux-pro-max': 0.99, 'vietnamese-official-wording': 0.01})
            self.assertEqual(result['status'], 'needs_context')
            self.assertIsNone(result['selected'])
            self.assertEqual(result['diagnostic'], 'uncertain_decision')
            self.assertEqual(result['uncertain'], [{'id': 'diagram-design', 'probability': probability}])
            self.assertNotIn('selection_id', result)
        for answers in (
            {'diagram-design': True, 'ui-ux-pro-max': 0.1, 'vietnamese-official-wording': 0.1},
            {'diagram-design': float('nan'), 'ui-ux-pro-max': 0.1, 'vietnamese-official-wording': 0.1},
            {'diagram-design': 1.01, 'ui-ux-pro-max': 0.1, 'vietnamese-official-wording': 0.1},
            {'ui-ux-pro-max': 0.1, 'vietnamese-official-wording': 0.1},
            {'diagram-design': 0.1, 'ui-ux-pro-max': 0.1, 'vietnamese-official-wording': 0.1, 'extra': 0.9},
        ):
            result = self._classify(catalog, answers)
            self.assertEqual(result['status'], 'blocked')
            self.assertIsNone(result['selected'])
            self.assertEqual(result['diagnostic'], 'invalid_provider_response')
        self.assertEqual(self._classify(catalog, {'diagram-design': 0.01, 'ui-ux-pro-max': 0.01, 'vietnamese-official-wording': 0.01}, 'typesafe/jev-1.13')['diagnostic'], 'invalid_provider_response')
        dated = self._classify(catalog, {'diagram-design': 0.01, 'ui-ux-pro-max': 0.01, 'vietnamese-official-wording': 0.01}, 'typesafe/jev-1.14-20260917')
        self.assertEqual(dated['status'], 'ready')
        self.assertEqual(dated['model_returned'], 'typesafe/jev-1.14-20260917')

    def _classify(self, catalog, probabilities, model='typesafe/jev-1.14'):
        raw = {skill_id: {'noul': probability, 'type': 'noul'} for skill_id, probability in probabilities.items()}
        if any(isinstance(probability, float) and probability != probability for probability in probabilities.values()):
            answers = raw
        else:
            answers = json.loads(json.dumps(raw))
        return classify_answers(task(), catalog, answers, model)

    def test_verify_terminal_text_is_not_json(self):
        from io import StringIO
        from contextlib import redirect_stdout
        from nda_harness.openrouter import verify_message
        from nda_harness.plugin_runtime import main
        ready = verify_message({'implementation_authorized': False, 'status': 'ready', 'usage': None})
        self.assertEqual(ready, 'OpenRouter key is present.')
        self.assertNotIn('{', ready)
        live = verify_message({
            'implementation_authorized': False,
            'model_returned': 'typesafe/jev-1.14-20261014',
            'provider_request_id': 'gen-dec-1',
            'status': 'ready',
            'usage': {'cost': 0.01, 'input_tokens': 3, 'output_tokens': 1},
        })
        self.assertEqual(live, 'Live check passed. Model typesafe/jev-1.14-20261014.')
        self.assertNotIn('gen-dec-1', live)
        self.assertNotIn('bearer-token', verify_message({'status': 'blocked', 'diagnostic': 'authorization_failed', 'next': 'bearer-token'}))
        self.assertEqual(verify_message({'status': 'blocked', 'diagnostic': 'credential_missing', 'implementation_authorized': False}), 'No OpenRouter key is saved.')
        class _Terminal(StringIO):
            def isatty(self):
                return True

        report = {'implementation_authorized': False, 'status': 'ready', 'usage': None}
        terminal = _Terminal()
        with patch('nda_harness.plugin_runtime.package_config', return_value={'schema_version': 1, 'client': 'cursor'}), patch('nda_harness.plugin_runtime.selection_verify', return_value=(report, 0)), redirect_stdout(terminal):
            self.assertEqual(main(['selection-verify', '--client', 'cursor']), 0)
        self.assertEqual(terminal.getvalue().strip(), 'OpenRouter key is present.')
        captured = StringIO()
        with patch('nda_harness.plugin_runtime.package_config', return_value={'schema_version': 1, 'client': 'cursor'}), patch('nda_harness.plugin_runtime.selection_verify', return_value=(report, 0)), redirect_stdout(captured):
            self.assertEqual(main(['selection-verify', '--client', 'cursor']), 0)
        self.assertEqual(json.loads(captured.getvalue())['status'], 'ready')

    def test_verify_and_transport_keep_the_key_on_the_fixed_origin(self):
        package = self._package()
        sentinel = 'SENTINEL_BODY_NOT_FOR_JEV'
        skill = package / 'skills' / 'diagram-design' / 'SKILL.md'
        skill.write_text(skill.read_text(encoding='utf-8') + sentinel, encoding='utf-8')
        keychain = _Keychain('bearer-token-value')
        calls = []

        def transport(url, payload, headers):
            calls.append((url, payload, headers))
            if url != DECISIONS_URL:
                raise AssertionError(url)
            body = json.dumps({
                'id': 'gen-dec-1', 'model': 'typesafe/jev-1.14-20260917', 'provider': 'hidden-provider',
                'answers': {'synthetic': {'type': 'noul', 'noul': 0.5}},
                'usage': {'input_tokens': 3, 'output_tokens': 1, 'cost': 0.01, 'secret': keychain.secret},
            }).encode()
            return 200, body

        offline, code = selection_verify(package, keychain, live=False, transport=transport)
        self.assertEqual(code, 0)
        self.assertEqual(calls, [])
        self.assertEqual(keychain.reads, 0)
        self.assertIsNone(offline['usage'])
        self.assertNotIn(keychain.secret, json.dumps(offline))

        live, code = selection_verify(package, keychain, live=True, transport=transport)
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 1)
        url, payload, headers = calls[0]
        self.assertEqual(url, DECISIONS_URL)
        self.assertEqual(headers['Authorization'], 'Bearer ' + keychain.secret)
        self.assertNotIn(sentinel.encode(), payload)
        self.assertNotIn(b'settings page', payload)
        self.assertEqual(json.loads(payload)['state'], {'purpose': 'selection-verify'})
        self.assertEqual(live['provider_request_id'], 'gen-dec-1')
        self.assertEqual(live['model_returned'], 'typesafe/jev-1.14-20260917')
        self.assertNotIn(keychain.secret, json.dumps(live))
        self.assertNotIn('hidden-provider', json.dumps(live))
        self.assertNotIn('selected', live)

        def timed_out(url, payload, headers):
            calls.append(url)
            raise TimeoutError()

        failed, code = selection_verify(package, _Keychain(keychain.secret), live=True, transport=timed_out)
        self.assertEqual(failed['diagnostic'], 'provider_unavailable')
        self.assertEqual(sum(call == DECISIONS_URL for call in calls if isinstance(call, str)), 1)

        denied = post_decision({'model': 'typesafe/jev-1.14'}, keychain.secret, transport=lambda url, payload, headers: (401, b'{"error":"secret-body"}'))
        self.assertEqual(denied['diagnostic'], 'authorization_failed')
        self.assertIn('selection-setup', denied['next'])
        self.assertNotIn('secret-body', json.dumps(denied))
        self.assertNotIn(keychain.secret, json.dumps(denied))
        with self.assertRaises(OSError):
            self._redirect_handler().redirect_request(None, None, 302, 'Found', {}, 'http://evil.example/collect')

    def test_cache_reuses_equivalent_inputs_and_misses_on_change(self):
        package, project, home, keychain = self._selection_env()
        transport = _Transport({'diagram-design': 0.05})
        first, code = self._select(package, project, home, keychain, transport, task(project_facts=self._facts(['b', 'a', 'a'])))
        self.assertEqual(code, 0)
        self.assertEqual(first['source'], 'openrouter')
        self.assertEqual(len(transport.calls), 1)
        second, code = self._select(package, project, home, keychain, transport, task(project_facts=self._facts(['a', 'b'])))
        self.assertEqual(code, 0)
        self.assertEqual(second['source'], 'cache')
        self.assertIsNone(second['usage'])
        self.assertIsNone(second['provider_request_id'])
        self.assertEqual(len(transport.calls), 1)
        later = time.time() + 8 * 24 * 60 * 60
        with patch('nda_harness.skill_selection.time.time', return_value=later):
            self._select(package, project, home, keychain, transport, task(project_facts=self._facts(['a', 'b'])))
        self.assertEqual(len(transport.calls), 2)
        for changed in (
            task(request='Ship a different page.'),
            task(stage='review'),
            task(project_facts=self._facts(['Vue'])),
        ):
            self._select(package, project, home, keychain, transport, changed)
        self.assertEqual(len(transport.calls), 5)
        self._select(package, project, home, keychain, transport, task(), release={'schema_version': 2})
        with patch('nda_harness.skill_selection.RULES_VERSION', 'jev-specialists-v2'):
            self._select(package, project, home, keychain, transport, task())
        with patch('nda_harness.skill_selection.MODEL', 'typesafe/jev-1.14-20990101'):
            self._select(package, project, home, keychain, transport, task())
        catalog = json.loads((package / 'catalog.json').read_text())
        catalog['skills'][0]['select_when'] = 'A different applicability statement.'
        (package / 'catalog.json').write_text(json.dumps(catalog), encoding='utf-8')
        self._select(package, project, home, keychain, transport, task())
        self.assertEqual(len(transport.calls), 9)

    def test_concurrent_miss_calls_the_provider_once(self):
        package, project, home, keychain = self._selection_env()
        transport = _Transport({'diagram-design': 0.05}, delay=0.2)
        errors = []

        def run(session):
            try:
                self._select(package, project, home, keychain, transport, task(), session=session)
            except Exception as error:
                errors.append(error)

        threads = [threading.Thread(target=run, args=(f'session-{index}',)) for index in (1, 2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(transport.calls), 1)

    def test_load_follows_the_active_session_selection(self):
        package, project, home, keychain = self._selection_env()
        transport = _Transport({'diagram-design': 0.95})
        selected, code = self._select(package, project, home, keychain, transport, task(request='Draw the flow.'), session='parent')
        self.assertEqual(code, 0)
        loaded, code = load_selected_skills(task(request='Draw the flow.'), project=project, session='parent', home=home, catalog_root=package, release_manifest={'schema_version': 1}, keychain=keychain)
        self.assertEqual(code, 0)
        self.assertEqual(loaded['skills'][0]['id'], 'diagram-design')
        self.assertEqual(loaded['skills'][0]['entrypoint'], 'diagram-design/SKILL.md')
        self.assertIn('SENTINEL_BODY_NOT_FOR_JEV', loaded['skills'][0]['body'])
        child, code = load_selected_skills(task(request='Draw the flow.'), project=project, session='child', home=home, catalog_root=package, release_manifest={'schema_version': 1}, keychain=keychain)
        self.assertEqual(code, 2)
        self.assertEqual(child['diagnostic'], 'selection_required')
        self._select(package, project, home, keychain, transport, task(request='Draw the flow.'), session='child')
        self.assertEqual(len(transport.calls), 1)
        other, code = self._select(package, project, home, keychain, transport, task(request='Review the API.'), session='parent')
        self.assertEqual(code, 0)
        stale, code = load_selected_skills(task(request='Draw the flow.'), project=project, session='parent', home=home, catalog_root=package, release_manifest={'schema_version': 1}, keychain=keychain)
        self.assertEqual(stale['diagnostic'], 'selection_required')
        self.assertNotIn('skills', stale)
        (package / 'diagram-design' / 'SKILL.md').write_text('CHANGED_BODY', encoding='utf-8')
        changed, code = load_selected_skills(task(request='Review the API.'), project=project, session='parent', home=home, catalog_root=package, release_manifest={'schema_version': 1}, keychain=keychain)
        self.assertEqual(code, 2)
        self.assertNotIn('CHANGED_BODY', json.dumps(changed))

    def test_failed_refresh_removes_the_shared_cache_entry(self):
        package, project, home, keychain = self._selection_env()
        transport = _Transport({'diagram-design': 0.95})
        self._select(package, project, home, keychain, transport, task(), session='one')
        self._select(package, project, home, keychain, transport, task(), session='two')
        self.assertEqual(len(transport.calls), 1)
        transport.status = 500
        failed, code = self._select(package, project, home, keychain, transport, task(), session='one', refresh=True)
        self.assertEqual(code, 2)
        self.assertEqual(failed['diagnostic'], 'provider_unavailable')
        self.assertEqual(list(home.rglob('cache/*.json')), [])
        revived, code = load_selected_skills(task(), project=project, session='two', home=home, catalog_root=package, release_manifest={'schema_version': 1}, keychain=keychain)
        self.assertEqual(revived['diagnostic'], 'selection_required')
        transport.status = 200
        transport.probabilities = {'diagram-design': 0.5}
        uncertain, code = self._select(package, project, home, keychain, transport, task(request='Maybe a diagram.'), session='one', refresh=True)
        self.assertEqual(code, 3)
        self.assertEqual(uncertain['status'], 'needs_context')
        self.assertEqual(uncertain['uncertain'], [{'id': 'diagram-design', 'probability': 0.5}])
        self.assertEqual(list(home.rglob('cache/*.json')), [])
        self.assertEqual(len(list(home.rglob('pending/*.json'))), 1)
        repeated, code = self._select(package, project, home, keychain, transport, task(request='Maybe a diagram.'), session='one')
        self.assertEqual(code, 3)
        self.assertEqual(repeated['source'], 'pending')
        self.assertEqual(len(transport.calls), 3)
        missing, code = record_selection(task(request='Maybe a diagram.'), {'diagram-design': True, 'extra': False}, project=project, session='one', home=home, catalog_root=package, release_manifest={'schema_version': 1}, keychain=keychain)
        self.assertEqual(missing['diagnostic'], 'invalid_decision')
        recorded, code = record_selection(task(request='Maybe a diagram.'), {'diagram-design': True}, project=project, session='one', home=home, catalog_root=package, release_manifest={'schema_version': 1}, keychain=keychain)
        self.assertEqual(code, 0)
        self.assertEqual(recorded['source'], 'user')
        self.assertEqual(recorded['selected'], [{'entrypoint': 'diagram-design/SKILL.md', 'id': 'diagram-design'}])
        self.assertEqual(recorded['user_decisions'], {'diagram-design': True})
        self.assertEqual(list(home.rglob('pending/*.json')), [])
        loaded, code = load_selected_skills(task(request='Maybe a diagram.'), project=project, session='one', home=home, catalog_root=package, release_manifest={'schema_version': 1}, keychain=keychain)
        self.assertEqual(code, 0)
        self.assertEqual(loaded['skills'][0]['id'], 'diagram-design')
        cached, code = self._select(package, project, home, keychain, transport, task(request='Maybe a diagram.'), session='one')
        self.assertEqual(code, 0)
        self.assertEqual(cached['source'], 'cache')
        self.assertEqual(cached['user_decisions'], {'diagram-design': True})
        self.assertEqual(len(transport.calls), 3)
        declined, code = record_selection(task(request='Maybe a diagram.'), {'diagram-design': False}, project=project, session='one', home=home, catalog_root=package, release_manifest={'schema_version': 1}, keychain=keychain)
        self.assertEqual(code, 0)
        self.assertEqual(declined['selected'], [])
        self.assertEqual(len(transport.calls), 3)

    def test_replacement_uses_the_new_key_and_skips_the_old_cache(self):
        package, project, home, keychain = self._selection_env(secret='first-bearer-token')
        transport = _Transport({'diagram-design': 0.05})
        self._select(package, project, home, keychain, transport, task())
        tty = _TTY(['y\n'])
        selection_setup(tty, home, read_secret=lambda: 'second-bearer-token')
        self._select(package, project, home, keychain, transport, task())
        self.assertEqual(len(transport.calls), 2)
        self.assertEqual(transport.calls[1][2]['Authorization'], 'Bearer second-bearer-token')

    def test_request_file_and_stdin_are_mutually_exclusive(self):
        with self.assertRaises(SelectionError) as caught:
            read_selection_request(None, _TTY([]))
        self.assertEqual(caught.exception.code, 'invalid_task_input')
        with self.assertRaises(SelectionError):
            read_selection_request('request.json', _Pipe('{}'))

    def _selection_env(self, secret='bearer-token-value'):
        root = Path(tempfile.mkdtemp(dir=ROOT))
        self.addCleanup(shutil.rmtree, root)
        package = root / 'hub'
        skill = package / 'diagram-design'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_text('SENTINEL_BODY_NOT_FOR_JEV', encoding='utf-8')
        (package / 'catalog.json').write_text(json.dumps({'schema_version': 1, 'skills': [{
            'id': 'diagram-design', 'entrypoint': 'diagram-design/SKILL.md',
            'select_when': 'Create a diagram.', 'exclude_when': 'Only discuss one.',
            'required_context': ['audience'], 'output': 'A diagram',
        }]}), encoding='utf-8')
        project = root / 'project'
        project.mkdir()
        home = root / 'home'
        home.mkdir()
        from nda_harness.credentials import FileCredentialStore
        report, code = selection_setup(_TTY([]), home, read_secret=lambda: secret)
        self.assertEqual(code, 0)
        self.assertEqual(report['status'], 'ready')
        keychain = FileCredentialStore(home)
        return package, project, home, keychain

    def _facts(self, stack):
        return {'stack': stack, 'deliverables': ['settings interface'], 'constraints': ['use the existing design system']}

    def _select(self, package, project, home, keychain, transport, value, session='session-one', release=None, refresh=False):
        return select_skills(
            value, project=project, session=session, home=home, catalog_root=package,
            release_manifest=release or {'schema_version': 1}, keychain=keychain, transport=transport, refresh=refresh,
        )

    def test_sandboxed_skill_selection_reruns_outside_for_every_client(self):
        from nda_harness.openrouter import verify_message
        package, project, home, _keychain = self._selection_env()
        blocked_home = home.parent / 'sandboxed-home'
        blocked_home.mkdir()
        usable = _Keychain('bearer-token-value')
        transport = _Transport({'diagram-design': 0.95})
        with patch.dict(os.environ, {'CODEX_SANDBOX': 'seatbelt'}):
            for client in ('codex', 'cursor', 'claude'):
                selected, code = select_skills(
                    task(), project=project, session='session-one', home=home, catalog_root=package,
                    release_manifest={'schema_version': 1}, keychain=usable, transport=transport, client=client,
                )
                self.assertEqual(code, 2, client)
                self.assertEqual(selected['status'], 'blocked', client)
                self.assertEqual(selected['diagnostic'], 'sandbox_rerun', client)
                self.assertIsNone(selected['selected'], client)
                self.assertIn('outside the sandbox', selected['next'])
                self.assertIn('shared', selected['next'])
                loaded, load_code = load_selected_skills(
                    task(), project=project, session='session-one', home=home, catalog_root=package,
                    release_manifest={'schema_version': 1}, keychain=usable, client=client,
                )
                self.assertEqual(load_code, 2, client)
                self.assertEqual(loaded['diagnostic'], 'sandbox_rerun', client)
                self.assertEqual(loaded['skills'], [])
                recorded, record_code = record_selection(
                    task(), {}, project=project, session='session-one', home=home, catalog_root=package,
                    release_manifest={'schema_version': 1}, keychain=usable, client=client,
                )
                self.assertEqual(record_code, 2, client)
                self.assertEqual(recorded['diagnostic'], 'sandbox_rerun', client)
                verified, verify_code = selection_verify(self._package(), usable, client=client, home=home)
                self.assertEqual(verify_code, 2, client)
                self.assertEqual(verified['diagnostic'], 'sandbox_rerun', client)
                message = verify_message(verified)
                self.assertIn('outside the sandbox', message)
                self.assertNotIn('No OpenRouter key is saved.', message)
                self.assertNotIn('OpenRouter key is present.', message)
                self.assertNotIn('{', message)
        self.assertEqual(transport.calls, [])
        self.assertEqual(usable.reads, 0)
        with patch('nda_harness.skill_selection.write_denial', return_value='sandbox'):
            denied, denied_code = select_skills(
                task(), project=project, session='session-one', home=blocked_home, catalog_root=package,
                release_manifest={'schema_version': 1}, keychain=usable, transport=transport, client='cursor',
            )
        self.assertEqual(denied_code, 2)
        self.assertEqual(denied['diagnostic'], 'sandbox_rerun')
        missing = _Keychain(None, status='missing')
        outside, outside_code = select_skills(
            task(), project=project, session='session-one', home=blocked_home, catalog_root=package,
            release_manifest={'schema_version': 1}, keychain=missing, transport=transport, client='claude',
        )
        self.assertEqual(outside_code, 2)
        self.assertEqual(outside['diagnostic'], 'credential_missing')
        kept, kept_code = select_skills(
            task(), project=project, session='session-two', home=home, catalog_root=package,
            release_manifest={'schema_version': 1}, keychain=usable, transport=transport, client='cursor',
        )
        self.assertEqual(kept_code, 0)
        self.assertEqual(kept['status'], 'ready')
        self.assertNotEqual(kept.get('diagnostic'), 'sandbox_rerun')
        self.assertGreater(len(transport.calls), 0)

    def test_packages_include_the_client_bound_selection_wrapper(self):
        from nda_harness.plugin_build import build
        roots = {'codex': '${PLUGIN_ROOT}', 'cursor': '${CURSOR_PLUGIN_ROOT}', 'claude': '${CLAUDE_PLUGIN_ROOT}'}
        for client, root_variable in roots.items():
            parent = Path(tempfile.mkdtemp(dir=ROOT))
            self.addCleanup(shutil.rmtree, parent, ignore_errors=True)
            destination = parent / client
            build(ROOT, destination, client)
            skill = (destination / 'skills/skill-selection/SKILL.md').read_text(encoding='utf-8')
            bootstrap = (destination / 'skills/session-bootstrap/SKILL.md').read_text(encoding='utf-8')
            self.assertIn(client, skill)
            self.assertIn(root_variable, skill)
            self.assertNotIn('@CLIENT@', skill)
            for command in ('selection-setup', 'selection-verify', 'select-skills', 'record-selection', 'load-selected-skills'):
                self.assertIn(command, skill)
            self.assertIn('Replace the saved OpenRouter key', skill)
            self.assertIn('Answering no keeps the saved key and finishes setup', skill)
            self.assertIn('The saved OpenRouter key was kept.', skill)
            self.assertIn('open a terminal and run', skill)
            self.assertIn('not JSON', skill)
            self.assertIn('scripts/open-terminal.sh', skill)
            opener = (destination / 'skills/skill-selection/scripts/open-terminal.sh').read_text(encoding='utf-8')
            self.assertIn('do script', opener)
            self.assertIn('cd ', opener)
            self.assertIn('selection-setup --client', opener)
            self.assertNotIn('Forty-four visual types', skill)
            self.assertIn('skill-selection', bootstrap)
            self.assertIn('selection-setup', bootstrap)
            self.assertIn('selection-migrate', bootstrap)
            self.assertIn('selection-migrate', skill)
            self.assertIn('outside the sandbox', skill)
            self.assertIn('sandbox_rerun', skill)
            self.assertIn('shared by Codex, Cursor, and Claude', skill)
            self.assertIn('outside the sandbox', bootstrap)
            self.assertIn('sandbox_rerun', bootstrap)
            self.assertNotIn('sandbox_skipped', skill)
            self.assertNotIn('sandbox_skipped', bootstrap)
            self.assertNotIn('Add a settings page', bootstrap)
            self.assertNotIn('sk-or-', bootstrap)
        cursor_parent = Path(tempfile.mkdtemp(dir=ROOT))
        self.addCleanup(shutil.rmtree, cursor_parent, ignore_errors=True)
        cursor = cursor_parent / 'cursor-rule'
        build(ROOT, cursor, 'cursor')
        rule = (cursor / 'rules/nda-harness.mdc').read_text(encoding='utf-8')
        self.assertIn('selection-setup', rule)
        self.assertIn('selection-migrate', rule)
        self.assertIn('Replace the saved OpenRouter key', rule)
        self.assertIn('Answering no keeps the saved key and finishes setup', rule)
        self.assertIn('record-selection', rule)
        self.assertIn('outside the sandbox', rule)
        self.assertIn('sandbox_rerun', rule)
        self.assertIn('shared by Codex, Cursor, and Claude', rule)

    def _redirect_handler(self):
        from nda_harness.openrouter import RejectRedirects
        return RejectRedirects()

    def _package(self):
        root = Path(tempfile.mkdtemp(dir=ROOT))
        self.addCleanup(shutil.rmtree, root)
        skills = root / 'skills'
        skills.mkdir()
        shutil.copy(ROOT / 'skills' / 'catalog.json', skills / 'catalog.json')
        for name in ('diagram-design', 'ui-ux-pro-max', 'vietnamese-official-wording'):
            destination = skills / name
            destination.mkdir()
            shutil.copy(ROOT / 'skills' / name / 'SKILL.md', destination / 'SKILL.md')
        (root / 'nda-plugin.json').write_text(json.dumps({'schema_version': 1, 'client': 'cursor'}), encoding='utf-8')
        return root

    def _write_catalog(self, root, entrypoint, select_when='Create a diagram.', exclude_when='Only discuss one.'):
        payload = {'schema_version': 1, 'skills': [{
            'id': 'diagram-design', 'entrypoint': entrypoint, 'select_when': select_when,
            'exclude_when': exclude_when, 'required_context': ['audience'], 'output': 'A diagram',
        }]}
        (root / 'catalog.json').write_text(json.dumps(payload), encoding='utf-8')
