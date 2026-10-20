"""Reproducible, self-contained native packages from canonical repository assets."""
import argparse
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tarfile
import tempfile
from urllib.parse import urlsplit
import zipfile

from .files import digest, json_bytes
from .bundled import WHEEL as TOMLKIT_WHEEL, SHA256 as TOMLKIT_SHA256
from .memory import NDA_HINDSIGHT, SYSTEMS, hindsight_services, auth_guidance

CLIENTS = ('codex', 'cursor', 'claude')
RELEASE_VERSION = '0.0.3'
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


def build(source, destination, client, endpoint=None, *, local_test=False, memory_endpoints=None, version=RELEASE_VERSION):
    source, destination = Path(source).resolve(), Path(destination).absolute()
    if not re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*)(?:\.(?:0|[1-9][0-9]*|[0-9]*[A-Za-z-][0-9A-Za-z-]*))*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?', version) or len(version) > 64:
        raise ValueError('Plugin version must be a semantic version of at most 64 characters.')
    if client not in CLIENTS:
        raise ValueError('Only Codex Desktop, Cursor IDE, and Claude Code Desktop packages are supported.')
    if memory_endpoints is None and not endpoint:
        endpoints = {'hindsight': NDA_HINDSIGHT['mcp']}
    else:
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
        services = {system_id: hindsight_services(url) if system_id == 'hindsight' else {'mcp': url}
                    for system_id, url in endpoints.items()}
        config = {'schema_version': 1, 'client': client,
                  'memory_systems': {'endpoints': endpoints, 'services': services},
                  'local_test': bool(local_test), 'superpowers_revision': SUPERPOWERS_REVISION}
        write(root, 'nda-plugin.json', json_bytes(config))
        description = 'NDA development workflow, project test gates and one optional memory system.'
        manifest = {'name': 'nda-harness', 'displayName': 'NDA Harness', 'version': version,
                    'description': description}
        logo = (source / 'plugin/assets/logo.jpg').read_bytes()
        write(root, 'assets/logo.jpg', logo)
        if client == 'claude':
            # skills/, hooks/hooks.json, and .mcp.json load from their default
            # locations. Declaring them in the manifest merges a second copy.
            manifest['author'] = {'name': 'NDA Harness'}
            manifest['logo'] = './assets/logo.jpg'
        elif client == 'codex':
            manifest.update({'author': {'name': 'NDA Harness'},
                             'skills': './skills/', 'hooks': './hooks/hooks.json', 'mcpServers': './.mcp.json',
                             'interface': {'displayName': 'NDA Harness', 'developerName': 'NDA Harness', 'category': 'Developer Tools',
                                           'capabilities': ['Development workflow', 'Project test gates'],
                                           'defaultPrompt': ['Set up NDA Harness for this project.'],
                                           'shortDescription': 'Development workflow', 'longDescription': description,
                                           'logo': './assets/logo.jpg', 'composerIcon': './assets/logo.jpg'}})
        else:
            manifest.update({'author': {'name': 'NDA Harness'}, 'logo': 'assets/logo.jpg', 'rules': './rules/',
                             'skills': './skills/', 'hooks': './hooks/hooks.json', 'mcpServers': './mcp.json'})
        write(root, f'.{client}-plugin/plugin.json', json_bytes(manifest))
        servers = {'nda-harness-context7': {'url': 'https://mcp.context7.com/mcp'}}
        for system_id, url in endpoints.items():
            servers[SYSTEMS[system_id]['server']] = {'url': url}
        if any(not isinstance(name, str) or re.fullmatch(r'[a-zA-Z0-9_:@/.-]+', name) is None for name in servers):
            raise ValueError('MCP server identifiers must not contain spaces or unsupported characters; use a separate display label.')
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
            write(root, 'rules/nda-harness.mdc', rule.replace('@AUTH_GUIDANCE@', auth_guidance(client)))
        else:
            hooks = {'hooks': {event: [{'hooks': [{'type': 'command', 'command': command(event), 'timeout': 60 if event == 'SessionStart' else 15}]}]
                               for event in ('SessionStart', 'UserPromptSubmit', 'PreCompact')}}
        write(root, 'hooks/hooks.json', json_bytes(hooks))
        # Client-bound wrapper skills never offer a client/scope selection menu.
        for name in ('nda-setup', 'nda-verify', 'session-bootstrap', 'hindsight-memory', 'task-prepare', 'context-refresh', 'context-checkpoint', 'context-resume'):
            path = root / 'skills' / name / 'SKILL.md'
            path.write_text(path.read_text().replace('@CLIENT@', client).replace('@ROOT@', variable)
                            .replace('@AUTH_GUIDANCE@', auth_guidance(client)))
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


def validate_archive(path, client):
    """Check ZIP structure and our release hashes before distributing a package."""
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        names = [entry.filename for entry in entries]
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP entry.')
        for entry in entries:
            name = entry.filename
            if name.startswith('/') or '\\' in name or any(p in ('', '.', '..') for p in name.rstrip('/').split('/')):
                raise ValueError('Unsafe ZIP entry: ' + name)
            mode = entry.external_attr >> 16
            if not (stat.S_ISDIR(mode) if entry.is_dir() else stat.S_ISREG(mode)):
                raise ValueError('ZIP entry must declare a regular file or directory: ' + name)
        if archive.testzip() is not None:
            raise ValueError('Corrupt ZIP entry.')
        manifest = json.loads(archive.read(f'.{client}-plugin/plugin.json'))
        if client == 'codex':
            if not manifest.get('author', {}).get('name'):
                raise ValueError('Codex manifest requires author.name.')
            for field in ('displayName', 'shortDescription', 'longDescription', 'developerName', 'category', 'logo', 'composerIcon'):
                if not manifest.get('interface', {}).get(field):
                    raise ValueError('Codex manifest requires interface.' + field)
            for field in ('capabilities', 'defaultPrompt'):
                values = manifest['interface'].get(field)
                if not isinstance(values, list) or any(not isinstance(value, str) or not value.strip() for value in values):
                    raise ValueError('Codex manifest requires interface.' + field + ' as a list of strings.')
            if any(name.endswith('/marketplace.json') for name in names):
                raise ValueError('Hosted upload requires a single plugin without a marketplace catalog.')
        if client == 'claude' and any(name == 'bin' or name.startswith('bin/') for name in names):
            raise ValueError('Claude hosted upload rejects a top-level bin/ directory.')
        hashes = json.loads(archive.read('release.json'))['asset_hashes']
        files = {entry.filename for entry in entries if not entry.is_dir()} - {'release.json'}
        if files != set(hashes):
            raise ValueError('ZIP files do not match release.json.')
        for name, expected in hashes.items():
            if digest(archive.read(name)) != expected:
                raise ValueError('ZIP release checksum mismatch: ' + name)
        if not any(name.startswith('skills/') and name.endswith('/SKILL.md') for name in files):
            raise ValueError('Plugin ZIP requires skills.')


def relocate_claude_launcher(package):
    """Move the launcher out of bin/ so a hosted Claude upload can declare it from hooks."""
    source = package / 'bin/nda-plugin'
    write(package, 'scripts/nda-plugin', source.read_bytes(), True)
    source.unlink()
    source.parent.rmdir()
    for path in sorted(package.rglob('*')):
        if not path.is_file() or path == package / 'scripts/nda-plugin':
            continue
        content = path.read_bytes()
        if b'bin/nda-plugin' not in content:
            continue
        path.write_bytes(content.replace(b'bin/nda-plugin', b'scripts/nda-plugin'))


def build_archive(source, destination, client, **options):
    """Build from canonical sources, then write and validate a deterministic ZIP."""
    destination = Path(destination).absolute()
    if destination.suffix != '.zip' or destination.exists() or destination.is_symlink():
        raise ValueError('Choose a new .zip output path; existing files are preserved.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.nda-zip-', dir=destination.parent) as temporary:
        package = build(source, Path(temporary) / 'package', client, **options)
        if client == 'codex':
            # Hosted upload accepts a plugin, not the local marketplace wrapper.
            shutil.rmtree(package / '.agents')
        elif client == 'claude':
            # claude.ai adds a top-level bin/ to PATH without showing it for approval.
            relocate_claude_launcher(package)
        # Keep upstream source without exposing its client manifests as extra plugins.
        upstream = package / 'vendor/superpowers'
        preserved = {name: (upstream / name).read_bytes() for name in ('SOURCE.json', 'LICENSE', 'hooks/session-start', 'hooks/run-hook.cmd')}
        shutil.rmtree(upstream)
        for name, content in preserved.items():
            write(upstream, name, content, name.startswith('hooks/'))
        write(package, 'vendor/' + SUPERPOWERS_ARCHIVE, (Path(source) / 'vendor' / SUPERPOWERS_ARCHIVE).read_bytes())
        hashes = {p.relative_to(package).as_posix(): digest(p.read_bytes())
                  for p in sorted(package.rglob('*')) if p.is_file() and p != package / 'release.json'}
        write(package, 'release.json', json_bytes({'schema_version': 1, 'asset_hashes': hashes}))
        output = Path(temporary) / 'plugin.zip'
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(package.rglob('*')):
                name = path.relative_to(package).as_posix() + ('/' if path.is_dir() else '')
                entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.create_system = 3
                mode = (stat.S_IFDIR | 0o755) if path.is_dir() else (stat.S_IFREG | (0o755 if path.stat().st_mode & 0o111 else 0o644))
                entry.external_attr = (mode << 16) | (0x10 if path.is_dir() else 0)
                entry.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(entry, b'' if path.is_dir() else path.read_bytes())
        validate_archive(output, client)
        os.replace(output, destination)
    return destination


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
        built.append(build(source, destination, client, version=RELEASE_VERSION))
    return built


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish-committed', action='store_true',
                        help='Replace packages/nda-harness-codex and packages/nda-harness-cursor. Does not write a Claude package.')
    parser.add_argument('--client', choices=CLIENTS)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--archive', action='store_true', help='Build a validated ZIP from fresh sources; --output must be a new .zip path.')
    parser.add_argument('--version', default=RELEASE_VERSION, help=f'Semantic plugin version (default: {RELEASE_VERSION}). Use a new version for each release.')
    parser.add_argument('--hindsight-mcp-url', default=None)
    parser.add_argument('--memory-endpoint', action='append', default=[])
    parser.add_argument('--local-test', action='store_true')
    args = parser.parse_args(argv)
    try:
        source = Path(__file__).resolve().parents[2]
        if args.publish_committed:
            if args.hindsight_mcp_url or args.memory_endpoint or args.local_test or args.client or args.output or args.archive or args.version != RELEASE_VERSION:
                raise ValueError('Committed packages use NDA Hindsight at hindsight-api.pila.vn and do not take a custom endpoint.')
            for output in publish_committed(source):
                print(output)
            return 0
        if not args.client or not args.output:
            parser.error('--client and --output are required unless --publish-committed is set')
        supplied = args.hindsight_mcp_url is not None or bool(args.memory_endpoint) or args.local_test or os.environ.get('HINDSIGHT_MCP_URL')
        builder = build_archive if args.archive else build
        if supplied:
            endpoint = args.hindsight_mcp_url if args.hindsight_mcp_url is not None else os.environ.get('HINDSIGHT_MCP_URL')
            endpoints = memory_endpoints(endpoint, args.memory_endpoint, local_test=args.local_test)
            output = builder(source, args.output, args.client, local_test=args.local_test, memory_endpoints=endpoints, version=args.version)
        else:
            output = builder(source, args.output, args.client, version=args.version)
        print(output)
        return 0
    except (OSError, ValueError, KeyError, tarfile.TarError, zipfile.BadZipFile) as error:
        print(f'Package build failed: {error}', file=__import__('sys').stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
