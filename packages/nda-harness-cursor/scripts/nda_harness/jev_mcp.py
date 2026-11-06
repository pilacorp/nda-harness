"""Bounded tools-only Jev MCP stdio adapter, using only Python 3.9+ stdlib.

Only the installed launcher constructs Engine. No credential, package, home,
provider, transport or client override is accepted in the tool interface.
"""
import json
from pathlib import Path
import sys

from nda_harness.credentials import FileCredentialStore
from nda_harness.files import Conflict
from nda_harness.mcp_error_log import JEV, JEV_CODES, record_failure
from nda_harness.openrouter import _selection_verify_engine
from nda_harness.skill_selection import (
    MAX_INPUT, _session_id, validate_task_input,
    _select_skills_engine, _record_selection_engine, _load_selected_skills_engine,
)

PROTOCOL = '2025-06-18'
MAX_LINE = 128 * 1024
MAX_RESPONSE = 2 * 1024 * 1024


def _schema(properties, required=()):
    return {'type': 'object', 'properties': properties, 'required': list(required), 'additionalProperties': False}


_COMMON = {'project': {'type': 'string', 'description': 'Absolute existing project directory.'},
           'session': {'type': 'string', 'minLength': 1, 'maxLength': 200},
           'task': {'type': 'object', 'description': 'Unchanged schema-1 assignment JSON.'}}
TOOLS = [
    {'name': 'select_skills',
     'description': 'Select metadata before loading bodies. Cache misses and refresh make one paid Jev call when a key exists. With local_agent, answer all questions using answers on the same task. Ask the user about every uncertain skill; never invent approval.',
     'inputSchema': _schema({**_COMMON, 'refresh': {'type': 'boolean', 'default': False}, 'answers': {'type': 'object'}}, _COMMON),
     'annotations': {'readOnlyHint': False, 'destructiveHint': False}},
    {'name': 'record_selection',
     'description': 'Record explicit human yes/no decisions for exactly the pending uncertain skills. No provider call. This never authorizes implementation.',
     'inputSchema': _schema({**_COMMON, 'decisions': {'type': 'object', 'additionalProperties': {'type': 'boolean'}}}, (*_COMMON, 'decisions')),
     'annotations': {'readOnlyHint': False, 'destructiveHint': False}},
    {'name': 'load_selected_skills',
     'description': 'Load only the same session and assignment’s ready selected bodies, after integrity checks. No provider call.',
     'inputSchema': _schema(_COMMON, _COMMON), 'annotations': {'readOnlyHint': True}},
    {'name': 'selection_verify',
     'description': 'Offline package and credential presence check by default. Set live true only for an explicitly requested paid synthetic check. No task data is sent by verification.',
     'inputSchema': _schema({'live': {'type': 'boolean', 'default': False}}),
     'annotations': {'readOnlyHint': False, 'destructiveHint': False}},
]


class InvalidParams(ValueError):
    pass


def validate_arguments(name, args):
    tool = next((tool for tool in TOOLS if tool['name'] == name), None)
    if tool is None or not isinstance(args, dict):
        raise InvalidParams()
    schema = tool['inputSchema']
    if set(args) - set(schema['properties']) or set(schema['required']) - set(args):
        raise InvalidParams()
    for key, value in args.items():
        expected = schema['properties'][key]['type']
        if not {'string': isinstance(value, str), 'object': isinstance(value, dict), 'boolean': type(value) is bool}[expected]:
            raise InvalidParams()
    if name != 'selection_verify':
        try:
            project = Path(args['project'])
            if not project.is_absolute() or not project.is_dir():
                raise InvalidParams()
            args = {**args, 'project': str(project.resolve())}
            _session_id(args['session'])
            validate_task_input(args['task'])
        except (OSError, ValueError, RuntimeError):
            raise InvalidParams() from None
        for field in ('answers', 'decisions'):
            if field in args and len(json.dumps(args[field], ensure_ascii=False).encode('utf-8')) > MAX_INPUT:
                raise InvalidParams()
        if 'decisions' in args and (not args['decisions'] or any(type(v) is not bool for v in args['decisions'].values())):
            raise InvalidParams()
    return args


def blocked(diagnostic):
    return {'status': 'blocked', 'diagnostic': diagnostic, 'implementation_authorized': False}


class Engine:
    def __init__(self, client):
        self.client = client
        self.package = Path(__file__).resolve().parents[2]
        self.home = Path.home().resolve() / '.nda-harness'

    def observe_failure(self, operation, diagnostic):
        if diagnostic not in ('local_agent', 'uncertain_decision'):
            record_failure(self.home, self.package, self.client, JEV, operation,
                           JEV_CODES.get(diagnostic, 'unknown_error'))

    def __call__(self, name, args):
        # Validate before any credential/cache access, including direct adapter use.
        args = validate_arguments(name, args)
        from nda_harness.plugin_runtime import package_config
        try:
            package_config(self.package, self.client)
        except (Conflict, OSError, ValueError):
            return blocked('package_integrity_failed')
        keychain = FileCredentialStore(self.home)
        if name == 'selection_verify':
            report, _ = _selection_verify_engine(self.package, keychain, live=args.get('live', False), client=self.client, home=self.home)
            return report
        kwargs = dict(project=Path(args['project']), session=args['session'], home=self.home,
                      catalog_root=self.package / 'skills', release_manifest=json.loads((self.package / 'release.json').read_text())['asset_hashes'],
                      keychain=keychain, client=self.client)
        if name == 'select_skills':
            # Answers are only meaningful in the missing-key flow, never silently ignored.
            if 'answers' in args:
                try:
                    presence = keychain.status()
                except OSError:
                    presence = 'unavailable'
                if presence == 'unavailable':
                    return blocked('credential_unavailable')
                if presence != 'missing':
                    return blocked('invalid_task_input')
            report, _ = _select_skills_engine(args['task'], refresh=args.get('refresh', False), answers=args.get('answers'), **kwargs)
        elif name == 'record_selection':
            report, _ = _record_selection_engine(args['task'], args['decisions'], **kwargs)
        else:
            report, _ = _load_selected_skills_engine(args['task'], **kwargs)
        # Preserve engine diagnostics/provenance, adapting only next-action transport wording.
        if report.get('diagnostic') == 'local_agent':
            report['next'] = 'Answer every question with type noul and probability 0 to 1; call select_skills with the same project, session, task and the answers object. Do not preload bodies.'
        elif report.get('diagnostic') == 'uncertain_decision':
            report['next'] = 'Ask the user about every uncertain skill, then call record_selection with the same project, session, task and exact boolean decisions; then load_selected_skills.'
        return report


def _error(ident, code, message):
    return {'jsonrpc': '2.0', 'id': ident, 'error': {'code': code, 'message': message}}


def _tool_result(report):
    return {'content': [{'type': 'text', 'text': json.dumps(report, ensure_ascii=False, allow_nan=False)}],
            'isError': report.get('status') == 'blocked'}


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8') + b'\n'


def _no_constant(value):
    raise ValueError('Invalid JSON constant')


def serve(handler, incoming=None, outgoing=None, errors=None):
    incoming = incoming if incoming is not None else sys.stdin.buffer
    outgoing = outgoing if outgoing is not None else sys.stdout.buffer
    errors = errors if errors is not None else sys.stderr
    initialized = ready = False
    while True:
        operation = diagnostic = None
        line = incoming.readline(MAX_LINE + 1)
        if not line:
            return 0
        if len(line) > MAX_LINE:
            errors.write('request_too_large\n')
            return 2
        try:
            message = json.loads(line.decode('utf-8'), parse_constant=_no_constant)
        except (ValueError, UnicodeError, RecursionError):
            response = _error(None, -32700, 'Parse error')
        else:
            ident = message.get('id') if isinstance(message, dict) else None
            valid_id = type(ident) in (str, int)
            if isinstance(ident, str):
                try:
                    ident.encode('utf-8')
                except UnicodeError:
                    valid_id = False
            if (not isinstance(message, dict) or message.get('jsonrpc') != '2.0'
                    or not isinstance(message.get('method'), str) or ('id' in message and not valid_id)):
                response = _error(ident if valid_id else None, -32600, 'Invalid request')
            elif 'id' not in message:
                if message['method'] == 'notifications/initialized' and initialized:
                    ready = True
                continue  # Never answer or dispatch notifications as requests.
            else:
                method, params = message['method'], message.get('params', {})
                try:
                    if not isinstance(params, dict):
                        raise InvalidParams()
                    if method == 'initialize':
                        if initialized or not isinstance(params.get('protocolVersion'), str) or not isinstance(params.get('capabilities'), dict) or not isinstance(params.get('clientInfo'), dict):
                            raise InvalidParams()
                        if any(not isinstance(params['clientInfo'].get(k), str) for k in ('name', 'version')):
                            raise InvalidParams()
                        result = {'protocolVersion': PROTOCOL, 'capabilities': {'tools': {}},
                                  'serverInfo': {'name': 'nda-harness-jev', 'version': '1.0.0'}}
                        initialized = True
                    elif method == 'ping':
                        if params:
                            raise InvalidParams()
                        result = {}
                    elif method not in ('tools/list', 'tools/call'):
                        response = _error(ident, -32601, 'Method not found')
                        result = None
                    elif not ready:
                        response = _error(ident, -32600, 'Server not initialized')
                        result = None
                    elif method == 'tools/list':
                        if set(params) - {'_meta'}:
                            raise InvalidParams()
                        result = {'tools': TOOLS}
                    else:
                        if set(params) - {'name', 'arguments', '_meta'} or not isinstance(params.get('name'), str):
                            raise InvalidParams()
                        args = validate_arguments(params['name'], params.get('arguments', {}))
                        operation = params['name']
                        try:
                            report = handler(operation, args)
                            result = _tool_result(report)
                        except (OSError, Conflict):
                            report = blocked('private_state_unavailable')
                            result = _tool_result(report)
                        except Exception:
                            report = blocked('internal_error')
                            result = _tool_result(report)
                        if result['isError']:
                            diagnostic = report.get('diagnostic', 'internal_error')
                    if result is not None:
                        response = {'jsonrpc': '2.0', 'id': ident, 'result': result}
                except (InvalidParams, ValueError, TypeError, RecursionError):
                    response = _error(ident, -32602, 'Invalid params')
                except Exception:
                    response = _error(ident, -32603, 'Internal error')
        try:
            encoded = _encoded(response)
        except (ValueError, TypeError, UnicodeError, RecursionError):
            response = {'jsonrpc': '2.0', 'id': response['id'], 'result': _tool_result(blocked('internal_error'))}
            encoded = _encoded(response)
        if len(encoded) > MAX_RESPONSE:
            response = {'jsonrpc': '2.0', 'id': response['id'], 'result': _tool_result(blocked('response_too_large'))}
            encoded = _encoded(response)
            diagnostic = 'response_too_large'
        observe_failure = getattr(handler, 'observe_failure', None)
        if operation and isinstance(diagnostic, str) and observe_failure:
            observe_failure(operation, diagnostic)
        outgoing.write(encoded)
        outgoing.flush()
