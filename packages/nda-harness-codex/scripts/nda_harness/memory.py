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

SYSTEMS = {
    'hindsight': {
        'label': 'NDA Hindsight',
        'skill': 'hindsight-memory',
        'server': 'nda-harness-hindsight',
        'tools': ('list_banks', 'create_bank', 'recall', 'retain'),
        'session': (
            'NDA Hindsight is optional. Do not initiate login. Its MCP URL is https://hindsight-api.pila.vn/mcp/. '
            'OAuth and REST use https://hindsight-api.pila.vn. OAuth discovery is /.well-known/oauth-authorization-server and /ext/oauth/ on that host. '
            'When this session lists list_banks, create_bank, recall, and retain, the user already authenticated: '
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
        return SYSTEMS[selected]['session']
    if len(offered) == 1:
        return SYSTEMS[next(iter(offered))]['session']
    if not offered:
        return DISABLED
    return CHOOSE
