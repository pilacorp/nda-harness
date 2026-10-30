"""Private, on-machine usage journal and report. Never stores prompts or secrets."""
import html
import json
import os
from pathlib import Path
import re
import time

from .files import digest, guard_path


SCHEMA = 1
DAY = 86400
WINDOWS = (7, 30)
KINDS = frozenset({
    'startup', 'context', 'selection', 'commit_gate', 'prompt', 'compact',
    'memory', 'subagent', 'spec_check',
})
STAGES = frozenset({'specification', 'implementation', 'unscoped'})
SPEC_RESULTS = frozenset({
    'no_spec', 'unmerged', 'mismatch', 'check_missing', 'matched',
    'docs', 'mechanical', 'exception',
})
MEMORY_OPERATIONS = frozenset({'retain', 'recall', 'reflect', 'create_bank'})
MEMORY_OUTCOMES = frozenset({'accepted', 'completed', 'failed', 'empty_bank'})
GATE_RESULTS = frozenset({'pass', 'fail', 'skip', 'invalid'})
MISS_REASONS = ('no_spec', 'unmerged', 'mismatch', 'check_missing')
TASK_PATTERN = re.compile(r'^[A-Za-z0-9_./-]{1,200}$')
ID_PATTERN = re.compile(r'^[A-Za-z0-9_-]{1,80}$')
ERROR_LIMIT = 200


def project_key(project):
    return digest(str(Path(project).resolve()))[:16]


def _root(home):
    root = Path(home).resolve() / '.nda-harness' / 'usage'
    guard_path(root / 'events.jsonl')
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    return root


def _clean_task(value):
    if not isinstance(value, str) or not TASK_PATTERN.fullmatch(value) or '..' in value.split('/'):
        return None
    return value


def _clean_error(value):
    if not isinstance(value, str):
        return None
    text = ' '.join(value.split())
    if not text or len(text) > ERROR_LIMIT:
        return None
    return text


def normalize_event(event, *, now=None):
    """Return a small journal line, or None when the event is not recordable."""
    if not isinstance(event, dict):
        return None
    kind = event.get('kind')
    client = event.get('client')
    if kind not in KINDS or client not in ('codex', 'cursor', 'claude'):
        return None
    line = {
        'schema_version': SCHEMA,
        'at': int(now if now is not None else time.time()),
        'client': client,
        'project': event.get('project') if isinstance(event.get('project'), str) and re.fullmatch(r'[0-9a-f]{16}', event['project']) else '',
        'kind': kind,
        'session': event.get('session') if isinstance(event.get('session'), str) and 1 <= len(event['session']) <= 200 else '',
    }
    if kind == 'startup':
        status = event.get('status')
        source = event.get('source')
        if status not in ('ready', 'blocked', 'failed', 'needs_context') or source not in ('hook', 'command'):
            return None
        line.update({'status': status, 'source': source})
    elif kind == 'context':
        operation = event.get('operation')
        status = event.get('status')
        stage = event.get('stage')
        if operation not in ('session-bootstrap', 'task-prepare', 'context-refresh', 'context-checkpoint', 'context-resume'):
            return None
        if status not in ('ready', 'blocked', 'needs_context') or stage not in ('specification', 'implementation'):
            return None
        line.update({
            'operation': operation,
            'status': status,
            'stage': stage,
            'task': _clean_task(event.get('task')) or '',
            'spec_missing': event.get('spec_missing') is True,
        })
    elif kind == 'selection':
        action = event.get('action')
        if action not in ('attempt', 'resolve'):
            return None
        line.update({'action': action, 'resolved': event.get('resolved') is True})
    elif kind == 'commit_gate':
        result = event.get('result')
        duration = event.get('duration_ms')
        if result not in GATE_RESULTS or type(duration) is not int or duration < 0 or duration > 3_600_000:
            return None
        line.update({'result': result, 'duration_ms': duration})
    elif kind == 'prompt':
        stage = event.get('stage')
        if stage not in STAGES:
            return None
        line['stage'] = stage
    elif kind == 'compact':
        pass
    elif kind == 'memory':
        operation = event.get('operation')
        outcome = event.get('outcome')
        if operation not in MEMORY_OPERATIONS or outcome not in MEMORY_OUTCOMES:
            return None
        operation_id = event.get('operation_id') or ''
        if operation_id and not ID_PATTERN.fullmatch(operation_id):
            return None
        error = _clean_error(event.get('error') or '')
        if event.get('error') and error is None:
            return None
        line.update({'operation': operation, 'outcome': outcome, 'operation_id': operation_id, 'error': error or ''})
    elif kind == 'subagent':
        chars = event.get('summary_chars')
        if type(chars) is not int or chars < 0 or chars > 200_000:
            return None
        line.update({'summary_chars': chars, 'task': _clean_task(event.get('task')) or ''})
    else:
        result = event.get('result')
        task = _clean_task(event.get('task'))
        if result not in SPEC_RESULTS or not task:
            return None
        line.update({'result': result, 'task': task})
    return line


def event_from_record(data, *, client, project, session):
    """Copy only the fields a developer may record. Extra keys are rejected."""
    allowed = {'schema_version', 'kind', 'operation', 'outcome', 'operation_id', 'error', 'summary_chars', 'task', 'result'}
    if not isinstance(data, dict) or set(data) - allowed or data.get('schema_version') != 1:
        raise ValueError('invalid usage event')
    kind = data.get('kind')
    if kind not in ('memory', 'subagent', 'spec_check'):
        raise ValueError('invalid usage event')
    event = {'kind': kind, 'client': client, 'project': project_key(project), 'session': session}
    if kind == 'memory':
        event.update({key: data.get(key, '') for key in ('operation', 'outcome', 'operation_id', 'error')})
    elif kind == 'subagent':
        event['summary_chars'] = data.get('summary_chars')
        if 'task' in data:
            event['task'] = data.get('task')
    else:
        event['result'] = data.get('result')
        event['task'] = data.get('task')
    return event


def append_event(home, event, *, now=None):
    line = normalize_event(event, now=now)
    if line is None:
        raise ValueError('invalid usage event')
    path = _root(home) / 'events.jsonl'
    payload = (json.dumps(line, sort_keys=True, separators=(',', ':')) + '\n').encode()
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)
    return line


def record_quietly(home, event, *, now=None):
    try:
        append_event(home, event, now=now)
    except (OSError, ValueError):
        return False
    return True


def read_events(home):
    path = Path(home).resolve() / '.nda-harness' / 'usage' / 'events.jsonl'
    if not path.is_file() or path.is_symlink():
        return []
    events = []
    for raw in path.read_text(encoding='utf-8').splitlines():
        try:
            item = json.loads(raw)
        except json.JSONDecodeError:
            continue
        normalized = normalize_event(item, now=item.get('at'))
        if normalized is not None:
            events.append(normalized)
    return events


def _stage_path(home):
    return _root(home) / 'stage.json'


def set_stage(home, project, stage):
    if stage not in ('specification', 'implementation'):
        return
    path = _stage_path(home)
    guard_path(path)
    current = {}
    if path.is_file() and not path.is_symlink():
        try:
            loaded = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(loaded, dict):
                current = {key: value for key, value in loaded.items() if value in ('specification', 'implementation')}
        except (OSError, json.JSONDecodeError):
            current = {}
    current[project_key(project)] = stage
    payload = (json.dumps(current, sort_keys=True) + '\n').encode()
    fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)


def stage_for(home, project):
    path = Path(home).resolve() / '.nda-harness' / 'usage' / 'stage.json'
    if not path.is_file() or path.is_symlink():
        return 'unscoped'
    try:
        loaded = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return 'unscoped'
    if not isinstance(loaded, dict):
        return 'unscoped'
    stage = loaded.get(project_key(project))
    return stage if stage in ('specification', 'implementation') else 'unscoped'


def _ratio(numerator, denominator):
    if not denominator:
        return None
    return round(numerator / denominator, 4)


def _in_window(events, now, days):
    start = int(now) - days * DAY
    return [event for event in events if isinstance(event.get('at'), int) and event['at'] >= start]


def _row():
    return {'checks': [], 'implementation': False, 'spec_missing': False}


def _spec_rows(events):
    by_task = {}
    for event in events:
        task = event.get('task') or ''
        if event['kind'] == 'spec_check' and task:
            by_task.setdefault(task, _row())['checks'].append(event)
        elif event['kind'] == 'context' and event.get('operation') == 'task-prepare' and event.get('stage') == 'implementation' and task:
            row = by_task.setdefault(task, _row())
            row['implementation'] = True
            row['spec_missing'] = row['spec_missing'] or event.get('spec_missing') is True
    if any(event['kind'] == 'prompt' and event.get('stage') == 'implementation' for event in events):
        if not any(row['implementation'] for row in by_task.values()):
            by_task.setdefault('', _row())['implementation'] = True
    misses = {reason: 0 for reason in MISS_REASONS}
    corrected = 0
    exceptions = 0
    lightweight = 0
    implementation_tasks = 0
    for row in by_task.values():
        if not row['implementation']:
            continue
        implementation_tasks += 1
        checks = sorted(row['checks'], key=lambda item: item['at'])
        results = [event['result'] for event in checks]
        if 'docs' in results or 'mechanical' in results:
            lightweight += 1
            continue
        if 'exception' in results and 'matched' not in results:
            exceptions += 1
            continue
        if not results:
            reason = 'no_spec' if row['spec_missing'] else 'check_missing'
            misses[reason] += 1
            continue
        first_miss = next((result for result in results if result in MISS_REASONS), None)
        if results[-1] == 'matched' and first_miss:
            misses[first_miss] += 1
            corrected += 1
        elif results[-1] == 'matched':
            continue
        elif results[-1] in MISS_REASONS:
            misses[results[-1]] += 1
        elif row['spec_missing']:
            misses['no_spec'] += 1
    return {
        'implementation_tasks': implementation_tasks,
        'without_spec': sum(misses.values()),
        'by_reason': misses,
        'corrected': corrected,
        'exceptions': exceptions,
        'lightweight': lightweight,
    }


def _workflows(events):
    groups = {}
    for event in events:
        if event['kind'] not in ('prompt', 'context'):
            continue
        groups.setdefault(event.get('project') or '', []).append(event)
    started = 0
    finished = 0
    for group in groups.values():
        ordered = sorted(group, key=lambda item: item['at'])
        current = []
        sessions = []
        for event in ordered:
            current.append(event)
            if event['kind'] == 'context' and event.get('operation') == 'context-checkpoint':
                sessions.append(current)
                current = []
        if current:
            sessions.append(current)
        for session in sessions:
            work = any(
                (item['kind'] == 'prompt' and item.get('stage') in ('specification', 'implementation'))
                or (item['kind'] == 'context' and item.get('operation') in ('task-prepare', 'context-refresh') and item.get('status') == 'ready')
                for item in session
            )
            if not work:
                continue
            started += 1
            if any(item['kind'] == 'context' and item.get('operation') == 'context-checkpoint' and item.get('status') == 'ready' for item in session):
                finished += 1
    return {'started': started, 'finished': finished, 'rate': _ratio(finished, started)}


def _selection(events):
    attempts = [event for event in events if event['kind'] == 'selection' and event.get('action') == 'attempt']
    resolves = [event for event in events if event['kind'] == 'selection' and event.get('action') == 'resolve']
    by_project = {}
    for event in resolves:
        by_project.setdefault(event.get('project') or '', []).append(event)
    followed = 0
    for attempt in attempts:
        if attempt.get('resolved'):
            followed += 1
            continue
        pool = by_project.get(attempt.get('project') or '', [])
        later = next((item for item in pool if item['at'] >= attempt['at']), None)
        if later is not None:
            pool.remove(later)
            followed += 1
    return {'attempts': len(attempts), 'followed': followed, 'rate': _ratio(followed, len(attempts))}


def _memory(events):
    operations = {}
    errors = []
    empty = 0
    for event in events:
        if event['kind'] != 'memory':
            continue
        if event['outcome'] == 'empty_bank':
            empty += 1
            continue
        row = operations.setdefault(event['operation'], {'completed': 0, 'failed': 0, 'accepted': 0})
        if event['outcome'] in row:
            row[event['outcome']] += 1
        if event['outcome'] == 'failed':
            errors.append({
                'at': event['at'],
                'operation': event['operation'],
                'operation_id': event.get('operation_id') or '',
                'error': event.get('error') or '',
            })
    for row in operations.values():
        row['rate'] = _ratio(row['completed'], row['completed'] + row['failed'])
    errors.sort(key=lambda item: item['at'], reverse=True)
    return {'operations': operations, 'empty_banks': empty, 'errors': errors[:20]}


def _turns(events):
    counts = {'specification': 0, 'implementation': 0, 'unscoped': 0}
    for event in events:
        if event['kind'] == 'prompt':
            counts[event['stage']] += 1
    return counts


def summarize(events, *, now=None, project=None):
    moment = int(now if now is not None else time.time())
    selected = events
    if project is not None:
        key = project if re.fullmatch(r'[0-9a-f]{16}', str(project)) else project_key(project)
        selected = [event for event in events if event.get('project') == key]
    windows = {}
    for days in WINDOWS:
        window = _in_window(selected, moment, days)
        gates = [event for event in window if event['kind'] == 'commit_gate']
        real = [event for event in gates if event['result'] in ('pass', 'fail')]
        passed = sum(1 for event in real if event['result'] == 'pass')
        startups = [event for event in window if event['kind'] == 'startup' and event.get('source') == 'hook']
        if not startups:
            startups = [event for event in window if event['kind'] == 'startup' and event.get('source') == 'command']
        blocked = sum(1 for event in startups if event.get('status') in ('blocked', 'failed'))
        spawns = [event for event in window if event['kind'] == 'subagent']
        spec = _spec_rows(window)
        compact = sum(1 for event in window if event['kind'] == 'compact')
        windows[str(days)] = {
            'workflows': _workflows(window),
            'commit_gate': {
                'real': len(real),
                'total': len(gates),
                'rate': _ratio(len(real), len(gates)),
                'first_try_pass': _ratio(passed, len(real)),
            },
            'blocked_starts': {'blocked': blocked, 'total': len(startups), 'rate': _ratio(blocked, len(startups))},
            'selection': _selection(window),
            'memory': _memory(window),
            'turns': _turns(window),
            'subagents': {
                'total': len(spawns),
                'average': _ratio(len(spawns), spec['implementation_tasks']),
                'summary_tokens': sum(event['summary_chars'] for event in spawns) // 4,
            },
            'compactions': compact,
            'spec_discipline': spec,
        }
    return {'schema_version': SCHEMA, 'generated_at': moment, 'windows': windows}


def _percent(rate):
    if rate is None:
        return 'n/a'
    return f'{rate * 100:.1f}%'


def render_text(report):
    lines = ['NDA Harness local usage', '']
    labels = (
        ('workflows', 'Workflows finished', lambda item: f"{item['workflows']['finished']}/{item['workflows']['started']} ({_percent(item['workflows']['rate'])})"),
        ('commit_gate', 'Real test gate', lambda item: f"{item['commit_gate']['real']}/{item['commit_gate']['total']} ({_percent(item['commit_gate']['rate'])})"),
        ('first_try', 'First-try pass', lambda item: _percent(item['commit_gate']['first_try_pass'])),
        ('blocked', 'Blocked starts', lambda item: f"{item['blocked_starts']['blocked']}/{item['blocked_starts']['total']} ({_percent(item['blocked_starts']['rate'])})"),
        ('selection', 'Selection followed', lambda item: f"{item['selection']['followed']}/{item['selection']['attempts']} ({_percent(item['selection']['rate'])})"),
        ('turns_spec', 'Spec turns', lambda item: str(item['turns']['specification'])),
        ('turns_impl', 'Implementation turns', lambda item: str(item['turns']['implementation'])),
        ('turns_other', 'Unscoped turns', lambda item: str(item['turns']['unscoped'])),
        ('subagents', 'Sub-agents', None),
        ('tokens', 'Estimated summary tokens', lambda item: str(item['subagents']['summary_tokens'])),
        ('compact', 'Parent compactions', lambda item: str(item['compactions'])),
        ('spec', 'Implemented without a proper spec', lambda item: str(item['spec_discipline']['without_spec'])),
    )
    for days, item in report['windows'].items():
        lines.append(f'{days} days')
        for _, label, value in labels:
            if label == 'Sub-agents':
                average = item['subagents']['average']
                shown = 'n/a' if average is None else f'{average:.2f}'
                lines.append(f'  Sub-agents: {item["subagents"]["total"]} total, average {shown}')
                continue
            lines.append(f'  {label}: {value(item)}')
        memory = item['memory']
        if not memory['operations'] and not memory['empty_banks']:
            lines.append('  Hindsight: no observations')
        for name, row in sorted(memory['operations'].items()):
            lines.append(f"  Hindsight {name}: {_percent(row['rate'])} ({row['completed']} completed, {row['failed']} failed, {row['accepted']} in flight)")
        lines.append(f"  Empty banks: {memory['empty_banks']}")
        discipline = item['spec_discipline']
        lines.append(
            '  Spec misses: '
            + ', '.join(f"{reason} {discipline['by_reason'][reason]}" for reason in MISS_REASONS)
            + f", corrected {discipline['corrected']}, exceptions {discipline['exceptions']}, docs/mechanical {discipline['lightweight']}"
        )
        if memory['errors']:
            lines.append('  Memory errors:')
            for error in memory['errors']:
                detail = error['error'] or error['operation_id'] or error['operation']
                lines.append(f"    {error['operation']}: {detail}")
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def render_html(report):
    text = html.escape(render_text(report))
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        '<title>NDA Harness local usage</title>'
        '<style>body{font:16px/1.5 sans-serif;margin:2rem;max-width:52rem}'
        'pre{white-space:pre-wrap}</style></head><body>'
        '<h1>NDA Harness local usage</h1>'
        '<p>This report stays on this machine.</p>'
        f'<pre>{text}</pre></body></html>\n'
    )


def write_report(home, report):
    path = _root(home) / 'report.html'
    guard_path(path)
    payload = render_html(report).encode()
    fd = os.open(path, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
    try:
        os.write(fd, payload)
    finally:
        os.close(fd)
    return path
