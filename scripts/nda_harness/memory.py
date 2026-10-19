"""One active memory system per project.

Register another system in SYSTEMS, give it a skill, and pass its MCP endpoint
when building a package. Setup stores the chosen id in profile memory.system.
"""
from nda_harness.files import Conflict


DISABLED = 'Memory is disabled: no memory system is packaged. Continue with client default memory if available.'
CHOOSE = ('One memory system is active per project. Several are packaged. Ask which one to use and pass it to nda-setup with --memory-system. '
          'Load only that system skill. Do not use a second memory system in the same project.')

SYSTEMS = {
    'hindsight': {
        'label': 'Hindsight',
        'skill': 'hindsight-memory',
        'server': 'hindsight',
        'tools': ('list_banks', 'create_bank', 'recall', 'retain'),
        'session': (
            'Hindsight is optional. Do not initiate login. When this session lists list_banks, create_bank, recall, and retain, the user already authenticated: '
            'load hindsight-memory and call those tools before substantive work. Read profile memory.bank_id, list_banks for it, create_bank with that same id when missing, then recall and later retain. '
            'Do not wait for the user to mention Hindsight. The client owns OAuth and credentials. '
            'Default environment dev; staging/prod are explicit labels in that same bank. Never store secrets. '
            'If Hindsight fails, continue using the client default memory if available; do not claim saves or later sync fallback content automatically. '
            'Verify memory only through client-native authenticated MCP diagnostics without reading or writing memories.'
        ),
    },
}


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
