"""One fixed-origin Jev decision call. No redirects, retries, or echoed provider bodies."""
import json
from pathlib import Path
import urllib.error
import urllib.request

from nda_harness.files import json_bytes
from nda_harness.skill_selection import MODEL, SelectionError, accept_model, load_catalog


DECISIONS_URL = 'https://openrouter.ai/api/alpha/decisions'
MAX_RESPONSE = 256 * 1024
REAUTHENTICATION = 'Run selection-setup again in a local terminal and confirm replacement of the OpenRouter key.'
SYNTHETIC_REQUEST = {
    'model': MODEL,
    'questions': {
        'synthetic': {
            'criteria': {
                'false': 'This includes a project task or skill body.',
                'true': 'This is the fixed selection-verify check.',
            },
            'instructions': 'Is this a synthetic connectivity check?',
            'type': 'noul',
        },
    },
    'state': {'purpose': 'selection-verify'},
}


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise OSError('redirect')


def _failure(diagnostic, nxt=None):
    payload = {'diagnostic': diagnostic, 'implementation_authorized': False, 'status': 'blocked'}
    if nxt:
        payload['next'] = nxt
    return payload


def _usage(value):
    if value is None:
        return None
    if not isinstance(value, dict):
        return None
    cleaned = {}
    for key in ('cost', 'input_tokens', 'output_tokens'):
        if key not in value:
            return None
        item = value[key]
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            return None
        cleaned[key] = item
    return cleaned


def urllib_transport(url, payload, headers):
    opener = urllib.request.build_opener(RejectRedirects)
    request = urllib.request.Request(url, data=payload, headers=headers, method='POST')
    try:
        with opener.open(request, timeout=15) as response:
            return response.status, response.read(MAX_RESPONSE + 1)
    except urllib.error.HTTPError as error:
        return error.code, error.read(MAX_RESPONSE + 1)


def post_decision(request, key, *, transport=None):
    """POST one decision request. The bearer is not copied into the result."""
    transport = transport or urllib_transport
    try:
        status, body = transport(DECISIONS_URL, json_bytes(request), {
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + key,
            'Content-Type': 'application/json',
        })
    except TimeoutError:
        return _failure('provider_unavailable')
    except OSError:
        return _failure('provider_unavailable')
    if status in (401, 403):
        return _failure('authorization_failed', REAUTHENTICATION)
    if status == 402:
        return _failure('credit_or_limit')
    if status == 429:
        return _failure('rate_limited')
    if status != 200:
        return _failure('provider_unavailable' if status >= 500 else 'invalid_provider_response')
    if not isinstance(body, (bytes, bytearray)) or len(body) > MAX_RESPONSE:
        return _failure('invalid_provider_response')
    try:
        payload = json.loads(body)
    except (UnicodeError, json.JSONDecodeError):
        return _failure('invalid_provider_response')
    if not isinstance(payload, dict) or not accept_model(payload.get('model')) or not isinstance(payload.get('answers'), dict):
        return _failure('invalid_provider_response')
    request_id = payload.get('id')
    return {
        'answers': payload['answers'],
        'implementation_authorized': False,
        'model': payload['model'],
        'provider_request_id': request_id if isinstance(request_id, str) else None,
        'status': 'ready',
        'usage': _usage(payload.get('usage')),
    }


def verify_message(report):
    """Human terminal text. selection-verify does not print the JSON report on a terminal."""
    status = report.get('status') if isinstance(report, dict) else None
    diagnostic = report.get('diagnostic') if isinstance(report, dict) else None
    model = report.get('model_returned') if isinstance(report, dict) else None
    if status == 'ready' and accept_model(model):
        return 'Live check passed. Model ' + model + '.'
    if status == 'ready':
        return 'OpenRouter key is present.'
    return {
        'credential_missing': 'No OpenRouter key is saved.',
        'credential_unavailable': 'Keychain could not be read.',
        'invalid_catalog': 'The skill selection package is invalid.',
        'authorization_failed': 'OpenRouter rejected the key. ' + REAUTHENTICATION,
        'credit_or_limit': 'OpenRouter reported a credit or limit problem.',
        'rate_limited': 'OpenRouter rate limited the check.',
        'provider_unavailable': 'OpenRouter could not be reached.',
        'invalid_provider_response': 'OpenRouter returned an unusable response.',
    }.get(diagnostic, 'Skill selection check did not finish.')


def selection_verify(package, keychain, *, live=False, transport=None):
    """Offline package and credential check, or one explicit synthetic decision call."""
    package = Path(package)
    try:
        metadata = json.loads((package / 'nda-plugin.json').read_text(encoding='utf-8'))
        if not isinstance(metadata, dict) or metadata.get('schema_version') != 1:
            raise SelectionError('invalid_catalog')
        load_catalog(package / 'skills')
    except (OSError, UnicodeError, json.JSONDecodeError, SelectionError):
        return {'diagnostic': 'invalid_catalog', 'implementation_authorized': False, 'status': 'blocked'}, 2
    try:
        presence = keychain.status()
    except OSError:
        presence = 'unavailable'
    if presence != 'present':
        diagnostic = 'credential_missing' if presence == 'missing' else 'credential_unavailable'
        return {'diagnostic': diagnostic, 'implementation_authorized': False, 'status': 'blocked'}, 2
    if not live:
        return {'implementation_authorized': False, 'status': 'ready', 'usage': None}, 0
    try:
        secret = keychain.read()
    except OSError:
        return {'diagnostic': 'credential_unavailable', 'implementation_authorized': False, 'status': 'blocked'}, 2
    result = post_decision(SYNTHETIC_REQUEST, secret, transport=transport)
    if result.get('diagnostic'):
        report = {'diagnostic': result['diagnostic'], 'implementation_authorized': False, 'status': 'blocked'}
        if result.get('next'):
            report['next'] = result['next']
        return report, 2
    answer = result['answers'].get('synthetic')
    probability = answer.get('noul') if isinstance(answer, dict) else None
    if not isinstance(answer, dict) or answer.get('type') != 'noul' or isinstance(probability, bool) or not isinstance(probability, (int, float)):
        return {'diagnostic': 'invalid_provider_response', 'implementation_authorized': False, 'status': 'blocked'}, 2
    return {
        'implementation_authorized': False,
        'model_returned': result['model'],
        'provider_request_id': result['provider_request_id'],
        'status': 'ready',
        'usage': result['usage'],
    }, 0
