"""One active memory system per project.

Register another system in SYSTEMS, give it a skill, and pass its MCP endpoint
when building a package. Setup stores the chosen id in profile memory.system.
"""
from nda_harness.files import Conflict


DISABLED = 'Memory is disabled: no memory system is packaged. Continue with client default memory if available.'
CHOOSE = ('One memory system is active per project. Several are packaged. Ask which one to use and pass it to nda-setup with --memory-system. '
          'Load only that system skill. Do not use a second memory system in the same project.')

# One host serves MCP, OAuth discovery, and the REST API. Clients connect to MCP
# and discover OAuth from that host. Do not put tokens or auth headers in the package.
NDA_HINDSIGHT_ORIGIN = 'https://hindsight-api.pila.vn'
NDA_HINDSIGHT = {
    'mcp': NDA_HINDSIGHT_ORIGIN + '/mcp/',
    'oauth': NDA_HINDSIGHT_ORIGIN,
    'rest': NDA_HINDSIGHT_ORIGIN,
}

NATIVE_CHECK = {
    'codex': 'Inspect the Hindsight native MCP startup or tool-discovery diagnostic in Codex.',
    'cursor': 'Inspect Hindsight in Cursor MCP settings; use agent mcp list where the CLI is installed. No local structured auth callback is established.',
    'claude': 'Inspect Hindsight with /mcp; a supported SDK status snapshot may still be pending.',
}
RECOVERY = {
    'codex': ('Use the native MCP sign-in action. If hidden, the user can run '
              'rtk proxy codex -c \'mcp_servers.nda-harness-hindsight.url="https://hindsight-api.pila.vn/mcp/"\' '
              'mcp login nda-harness-hindsight using the installed executable, then reconnect/restart Codex. '
              'The override is invocation-local and uses the same server identity.'),
    'cursor': ('Use the Hindsight native authentication control. With Cursor Agent CLI and the server registered there, '
               'the user can run rtk proxy agent mcp login <identifier>; verify the identifier in native inventory. '
               'Do not assume shared credentials across Cursor surfaces.'),
    'claude': ('Use /mcp to inspect and authenticate Hindsight. If the installed CLI exposes mcp login, '
               'the user can run rtk proxy claude mcp login <name> with the name from native inventory. '
               'SDK status APIs do not launch browser OAuth or imply a Desktop SDK bridge.'),
}


def auth_guidance(client):
    """Reviewed, client-specific instructions; never include diagnostic payloads."""
    common = ('Missing tools mean Hindsight is unavailable in this session; authentication is unverified without native evidence. '
              'Saved OAuth credentials and a hidden Authenticate button do not prove a working connection. '
              'Use the packaged memory-status helper with already available native diagnostic JSON, or leave the diagnostic pending. '
              'Existing hooks do not subscribe to MCP lifecycle events. Never initiate login automatically or read/edit credentials. ')
    signals = {
        'codex': ('Only for Codex, a matching mcpServer/startupStatus/updated notification with status failed and '
                  'failureReason reauthenticationRequired confirms reauthentication is required. '
                  'Native discovery with authStatus oAuth and tools proves connection/tool discovery only. '),
        'cursor': 'Do not interpret another client\'s auth signals or Cursor Cloud telemetry as a local Cursor callback. ',
        'claude': ('Only for Claude, a matching native MCP status needs-auth confirms authentication is required; '
                   'pending remains unresolved and failed means unavailable. '),
    }
    return common + signals[client] + NATIVE_CHECK[client] + ' Manual, user-triggered recovery: ' + RECOVERY[client]


def memory_status(config, client, native=None, *, invalid=False):
    """Classify supplied native evidence without connecting, persisting or authenticating."""
    state, diagnostic = 'pending_native_diagnostic', 'native_diagnostic_pending'
    action = NATIVE_CHECK[client]
    if invalid or native is not None and not isinstance(native, dict):
        diagnostic = 'invalid_native_diagnostic'
    elif 'hindsight' not in packaged(config):
        state, diagnostic = 'disabled', 'endpoint_not_packaged'
        action = 'Continue core work; use client default memory only if available.'
    elif isinstance(native, dict) and client != 'cursor':
        data = native
        notification = 'method' in data
        if notification:
            data = (data.get('params') if client == 'codex'
                    and data['method'] == 'mcpServer/startupStatus/updated' else None)
        if isinstance(data, dict) and data.get('name') == SYSTEMS['hindsight']['server']:
            status = data.get('status')
            if status == 'failed':
                state, diagnostic = 'unavailable', 'native_connection_failed'
                if client == 'codex' and notification and data.get('failureReason') == 'reauthenticationRequired':
                    state, diagnostic = 'awaiting_authentication', 'reauthentication_required'
            elif client == 'claude' and status == 'needs-auth':
                state, diagnostic = 'awaiting_authentication', 'authentication_required'
            elif (client == 'claude' and status == 'connected'
                  or client == 'codex' and not notification and status is None
                  and data.get('authStatus') == 'oAuth'
                  and isinstance(data.get('tools'), (dict, list)) and data['tools']):
                state, diagnostic = 'connected', 'native_connection_observed'
            if state == 'awaiting_authentication':
                action = RECOVERY[client]
            elif state == 'connected':
                action = 'Use available Hindsight tools; memory operations and future refresh are not verified by discovery.'
    return {'schema_version': 1, 'client': client, 'server': SYSTEMS['hindsight']['server'],
            'memory_state': state, 'diagnostic': diagnostic, 'next_action': action}


SYSTEMS = {
    'hindsight': {
        'label': 'NDA Hindsight',
        'skill': 'hindsight-memory',
        'server': 'nda-harness-hindsight',
        'tools': ('list_banks', 'create_bank', 'recall', 'retain'),
        'session': (
            'NDA Hindsight is optional. Do not initiate login. Its MCP URL is https://hindsight-api.pila.vn/mcp/. '
            'OAuth and REST use https://hindsight-api.pila.vn. OAuth discovery is /.well-known/oauth-authorization-server and /ext/oauth/ on that host. '
            'When this session lists list_banks, create_bank, recall, and retain, use those available tools: '
            'load hindsight-memory and call those tools before substantive work. Read profile memory.bank_id, list_banks for it, create_bank with that same id when missing, then recall and later retain. '
            'Do not wait for the user to mention NDA Hindsight. The client owns OAuth and credentials. '
            'Default environment dev; staging/prod are explicit labels in that same bank. Never store secrets. '
            'If NDA Hindsight fails, continue using the client default memory if available; do not claim saves or later sync fallback content automatically. '
            'Verify memory only through client-native authenticated MCP diagnostics without reading or writing memories.'
        ),
    },
}


def hindsight_services(mcp_url):
    """MCP, OAuth, and REST for a Hindsight endpoint. Production uses hindsight-api.pila.vn."""
    if mcp_url == NDA_HINDSIGHT['mcp']:
        return dict(NDA_HINDSIGHT)
    if not isinstance(mcp_url, str) or not mcp_url.endswith('/mcp/'):
        raise ValueError('A Hindsight MCP URL must end in /mcp/.')
    origin = mcp_url[:-len('/mcp/')]
    return {'mcp': mcp_url, 'oauth': origin, 'rest': origin}


def declared_endpoints(config):
    """Endpoint map from a package, including a legacy Hindsight URL."""
    endpoints = {}
    raw = config.get('memory_systems')
    if isinstance(raw, dict) and isinstance(raw.get('endpoints'), dict):
        for system_id, url in raw['endpoints'].items():
            if url:
                endpoints[str(system_id)] = url
    legacy = config.get('hindsight_mcp_url')
    if legacy and 'hindsight' not in endpoints:
        endpoints['hindsight'] = legacy
    return endpoints


def packaged(config):
    return {system_id: url for system_id, url in declared_endpoints(config).items() if system_id in SYSTEMS}


def select_system(config, requested=None, previous=None):
    """The one system this project uses, or None when memory is not packaged."""
    offered = packaged(config)
    if not offered:
        return None
    selected = requested or (previous if previous in offered else None)
    if selected is None and len(offered) == 1:
        return next(iter(offered))
    if selected is None:
        raise Conflict('Choose one memory system. Pass --memory-system with one packaged id.')
    if selected not in SYSTEMS:
        raise Conflict('Unknown memory system.')
    if selected not in offered:
        raise Conflict('Selected memory system is not packaged.')
    return selected


def session_instruction(config, selected=None):
    offered = packaged(config)
    if selected in offered:
        system = selected
    elif len(offered) == 1:
        system = next(iter(offered))
    elif not offered:
        return DISABLED
    else:
        return CHOOSE
    instruction = SYSTEMS[system]['session']
    if system == 'hindsight' and config.get('client') in RECOVERY:
        instruction += ' ' + auth_guidance(config['client'])
    return instruction
