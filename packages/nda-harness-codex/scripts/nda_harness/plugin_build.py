"""Reproducible, self-contained native packages from canonical repository assets."""
import argparse
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
from urllib.parse import urlsplit

from .files import digest, json_bytes
from .bundled import WHEEL as TOMLKIT_WHEEL, SHA256 as TOMLKIT_SHA256
from .memory import SYSTEMS

CLIENTS = ('codex', 'cursor', 'claude')
SUPERPOWERS_REVISION = 'bb92a77741419a4ab5f06e711a283343f1ada0c3'
SUPERPOWERS_ARCHIVE = 'superpowers-bb92a777.tar.gz'
SUPERPOWERS_SHA256 = '496b576d4a4a62c0d72cce4a9e99ff46c57026c07fe503931cbb8afd33006cf2'
RUNTIME = ('__init__.py', 'plugin_build.py', 'plugin_runtime.py', 'project.py',
           'dependencies.py', 'files.py', 'hooks.py', 'bundled.py', 'memory.py')


def validate_endpoint(url, local_test=False):
    if url is None:
        return None
    if not isinstance(url, str) or any(c.isspace() or ord(c) < 32 for c in url):
        raise ValueError('HINDSIGHT_MCP_URL must be an HTTPS /mcp/ URL without credentials, query or fragment.')
    try:
        parsed = urlsplit(url)
        local = parsed.hostname == 'localhost'
        try:
            local = local or ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError:
            pass
        valid_scheme = parsed.scheme == 'https' or (local_test and local and parsed.scheme == 'http')
        if not valid_scheme or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.path != '/mcp/' or parsed.query or parsed.fragment or '?' in url or '#' in url:
            raise ValueError()
        _ = parsed.port
    except (ValueError, TypeError):
        raise ValueError('HINDSIGHT_MCP_URL must be an HTTPS /mcp/ URL without credentials, query or fragment; HTTP loopback needs --local-test.') from None
    return url


def write(root, relative, content, executable=False):
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content if isinstance(content, bytes) else content.encode())
    target.chmod(0o755 if executable else 0o644)


def copy_assets(source, root, directory):
    for path in sorted((source / directory).rglob('*')):
        if '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        if path.is_symlink():
            raise ValueError('Package sources cannot contain symlinks.')
        if path.is_file():
            content = path.read_bytes()
            if path.relative_to(source).as_posix() == 'skills/catalog.md':
                content = content.replace(b'../docs/architecture.md', b'https://github.com/pilacorp/nda-harness/blob/dev/docs/architecture.md')
            write(root, path.relative_to(source), content, bool(path.stat().st_mode & 0o111))


def superpowers(source, root, client):
    archive = source / 'vendor' / SUPERPOWERS_ARCHIVE
    if archive.is_symlink() or digest(archive.read_bytes()) != SUPERPOWERS_SHA256:
        raise ValueError('Pinned Superpowers archive checksum mismatch.')
    with tarfile.open(archive, 'r:gz') as bundle:
        for member in bundle.getmembers():
            relative = PurePosixPath(member.name)
            if relative.parts[0] != 'superpowers-' + SUPERPOWERS_REVISION or '..' in relative.parts or member.issym() or member.islnk():
                raise ValueError('Unsafe Superpowers archive member.')
            if not member.isfile():
                continue
            relative = Path(*relative.parts[1:])
            content = bundle.extractfile(member).read()
            write(root, Path('vendor/superpowers') / relative, content, bool(member.mode & 0o111))
            if relative.parts[0] in ('skills', 'agents'):
                if (root / relative).exists():
                    raise ValueError('Superpowers asset collides with harness asset.')
                active = content.replace(b'superpowers:', b'nda-harness:') if relative.suffix == '.md' else content
                write(root, relative, active, bool(member.mode & 0o111))
    write(root, 'vendor/superpowers/SOURCE.json', json_bytes({
        'upstream': 'https://github.com/obra/superpowers', 'revision': SUPERPOWERS_REVISION,
        'archive_sha256': SUPERPOWERS_SHA256, 'license': 'MIT', 'modified': False,
        'active_skill_adaptation': 'Generated Markdown namespace references use nda-harness:; original source and handlers preserved here.'}))


def memory_endpoints(hindsight_url=None, pairs=(), *, local_test=False):
    """One HTTPS endpoint per memory system. Hindsight keeps its existing flag."""
    endpoints = {}
    if hindsight_url:
        endpoints['hindsight'] = validate_endpoint(hindsight_url, local_test)
    for item in pairs:
        if not isinstance(item, str) or item.count('=') != 1:
            raise ValueError('Use --memory-endpoint <system>=<https-mcp-url> once per memory system.')
        system_id, url = item.split('=', 1)
        if system_id not in SYSTEMS:
            raise ValueError('Unknown memory system.')
        if system_id in endpoints:
            raise ValueError('Each memory system has one endpoint.')
        endpoints[system_id] = validate_endpoint(url, local_test)
    return endpoints


def build(source, destination, client, endpoint=None, *, local_test=False, memory_endpoints=None):
    source, destination = Path(source).resolve(), Path(destination).absolute()
    if client not in CLIENTS:
        raise ValueError('Only Codex Desktop, Cursor IDE, and Claude Code Desktop packages are supported.')
    endpoints = dict(memory_endpoints or {})
    if endpoint:
        url = validate_endpoint(endpoint, local_test)
        if 'hindsight' in endpoints and endpoints['hindsight'] != url:
            raise ValueError('Each memory system has one endpoint.')
        endpoints['hindsight'] = url
    for system_id, url in list(endpoints.items()):
        if system_id not in SYSTEMS:
            raise ValueError('Unknown memory system.')
        endpoints[system_id] = validate_endpoint(url, local_test)
    if destination.exists() or destination.is_symlink():
        raise ValueError('Choose a new package output directory; existing files are preserved.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.nda-build-', dir=destination.parent) as temporary:
        root = Path(temporary) / 'package'
        root.mkdir()
        for directory in ('pack', 'skills'):
            copy_assets(source, root, directory)
        for module in RUNTIME:
            write(root, 'scripts/nda_harness/' + module, (source / 'scripts/nda_harness' / module).read_bytes())
        if digest((source / 'vendor' / TOMLKIT_WHEEL).read_bytes()) != TOMLKIT_SHA256:
            raise ValueError('Pinned Python dependency checksum mismatch.')
        for name in (TOMLKIT_WHEEL, 'tomlkit-LICENSE'):
            write(root, 'vendor/' + name, (source / 'vendor' / name).read_bytes())
        superpowers(source, root, client)
        write(root, 'bin/nda-plugin', (source / 'bin/nda-plugin').read_bytes(), True)
        for path in sorted((source / 'plugin/skills').rglob('*')):
            if path.is_file():
                write(root, Path('skills') / path.relative_to(source / 'plugin/skills'), path.read_bytes())
        config = {'schema_version': 1, 'client': client, 'memory_systems': {'endpoints': endpoints},
                  'local_test': bool(local_test), 'superpowers_revision': SUPERPOWERS_REVISION}
        write(root, 'nda-plugin.json', json_bytes(config))
        description = 'NDA development workflow, project test gates and one optional memory system.'
        manifest = {'name': 'nda-harness', 'displayName': 'NDA Harness', 'version': '0.0.0',
                    'description': description}
        if client == 'claude':
            # skills/, hooks/hooks.json, and .mcp.json load from their default
            # locations. Declaring them in the manifest merges a second copy.
            manifest['author'] = {'name': 'NDA Harness'}
        elif client == 'codex':
            manifest.update({'skills': './skills/', 'hooks': './hooks/hooks.json', 'mcpServers': './.mcp.json',
                             'interface': {'displayName': 'NDA Harness', 'developerName': 'NDA Harness',
                                           'shortDescription': 'Development workflow with optional Hindsight memory'}})
        else:
            manifest.update({'author': {'name': 'NDA Harness'}, 'rules': './rules/',
                             'skills': './skills/', 'hooks': './hooks/hooks.json', 'mcpServers': './mcp.json'})
        write(root, f'.{client}-plugin/plugin.json', json_bytes(manifest))
        servers = {'nda-harness-context7': {'url': 'https://mcp.context7.com/mcp'}}
        for system_id, url in endpoints.items():
            servers[SYSTEMS[system_id]['server']] = {'url': url}
        if client in ('codex', 'claude'):
            for server in servers.values():
                server['type'] = 'http'
        write(root, 'mcp.json' if client == 'cursor' else '.mcp.json', json_bytes({'mcpServers': servers}))
        variable = {'codex': '${PLUGIN_ROOT}', 'cursor': '${CURSOR_PLUGIN_ROOT}', 'claude': '${CLAUDE_PLUGIN_ROOT}'}[client]
        def command(operation):
            return f'"{variable}/bin/nda-plugin" hook --client {client} --event {operation}'
        if client == 'cursor':
            hooks = {'version': 1, 'hooks': {event: [{'command': command(event), 'timeout': 60 if event == 'sessionStart' else 15}]
                                            for event in ('sessionStart', 'beforeSubmitPrompt', 'preCompact', 'workspaceOpen')}}
            # Our own bootstrap loads the bundled introductory skill. Registering
            # a second upstream handler would duplicate an existing Superpowers
            # installation; leave its hooks and client configuration untouched.
            rule = (source / 'plugin/rules/nda-harness.mdc').read_text()
            write(root, 'rules/nda-harness.mdc', rule)
        else:
            hooks = {'hooks': {event: [{'hooks': [{'type': 'command', 'command': command(event), 'timeout': 60 if event == 'SessionStart' else 15}]}]
                               for event in ('SessionStart', 'UserPromptSubmit', 'PreCompact')}}
        write(root, 'hooks/hooks.json', json_bytes(hooks))
        # Client-bound wrapper skills never offer a client/scope selection menu.
        for name in ('nda-setup', 'nda-verify', 'session-bootstrap', 'task-prepare', 'context-refresh', 'context-checkpoint', 'context-resume'):
            path = root / 'skills' / name / 'SKILL.md'
            path.write_text(path.read_text().replace('@CLIENT@', client).replace('@ROOT@', variable))
        if client == 'codex':
            write(root, '.agents/plugins/marketplace.json', json_bytes({
                'name': 'nda-harness-local', 'interface': {'displayName': 'NDA Harness'},
                'plugins': [{'name': 'nda-harness', 'source': {'source': 'local', 'path': './'},
                             'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_USE'}, 'category': 'Productivity'}]}))
        elif client == 'claude':
            write(root, '.claude-plugin/marketplace.json', json_bytes({
                'name': 'nda-harness-local', 'owner': {'name': 'NDA Harness'},
                'plugins': [{'name': 'nda-harness', 'source': '.', 'description': description}]}))
        hashes = {p.relative_to(root).as_posix(): digest(p.read_bytes()) for p in sorted(root.rglob('*')) if p.is_file()}
        write(root, 'release.json', json_bytes({'schema_version': 1, 'asset_hashes': hashes}))
        os.replace(root, destination)
    return destination


COMMITTED_CLIENTS = ('codex', 'cursor')


def publish_committed(source):
    """Replace the stored Codex and Cursor packages. Claude is a release output only."""
    source = Path(source).resolve()
    packages = source / 'packages'
    packages.mkdir(parents=True, exist_ok=True)
    claude = packages / 'nda-harness-claude'
    if claude.exists() or claude.is_symlink():
        shutil.rmtree(claude)
    built = []
    for client in COMMITTED_CLIENTS:
        destination = packages / f'nda-harness-{client}'
        if destination.exists() or destination.is_symlink():
            shutil.rmtree(destination)
        built.append(build(source, destination, client))
    return built


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish-committed', action='store_true',
                        help='Replace packages/nda-harness-codex and packages/nda-harness-cursor. Does not write a Claude package.')
    parser.add_argument('--client', choices=CLIENTS)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--hindsight-mcp-url', default=None)
    parser.add_argument('--memory-endpoint', action='append', default=[])
    parser.add_argument('--local-test', action='store_true')
    args = parser.parse_args(argv)
    try:
        source = Path(__file__).resolve().parents[2]
        if args.publish_committed:
            if args.hindsight_mcp_url or args.memory_endpoint or args.local_test or args.client or args.output:
                raise ValueError('Committed packages omit memory endpoints and are only Codex and Cursor.')
            for output in publish_committed(source):
                print(output)
            return 0
        if not args.client or not args.output:
            parser.error('--client and --output are required unless --publish-committed is set')
        endpoint = args.hindsight_mcp_url if args.hindsight_mcp_url is not None else os.environ.get('HINDSIGHT_MCP_URL')
        endpoints = memory_endpoints(endpoint, args.memory_endpoint, local_test=args.local_test)
        output = build(source, args.output, args.client, local_test=args.local_test, memory_endpoints=endpoints)
        print(output)
        return 0
    except (OSError, ValueError, tarfile.TarError):
        print('Package build failed: check client, endpoint, pinned assets and a new writable output directory.', file=__import__('sys').stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
