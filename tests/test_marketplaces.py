"""Repository distribution contracts; no access to real client settings or credentials."""
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from nda_harness import plugin_build
from nda_harness.files import digest


CATALOGS = {
    'codex': '.agents/plugins/marketplace.json',
    'cursor': '.cursor-plugin/marketplace.json',
    'claude': '.claude-plugin/marketplace.json',
}


class MarketplaceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve() / 'repository'
        self.root.mkdir()
        for directory in ('scripts', 'bin', 'pack', 'skills', 'plugin', 'vendor'):
            shutil.copytree(ROOT / directory, self.root / directory,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))

    def snapshot(self):
        return {p.relative_to(self.root).as_posix():
                (digest(p.read_bytes()), stat.S_IMODE(p.stat().st_mode))
                for directory in ('packages', '.agents', '.cursor-plugin', '.claude-plugin')
                for p in (self.root / directory).rglob('*') if p.is_file()}

    def test_publish_routes_all_clients_at_one_version_and_is_reproducible(self):
        # A two-client publisher, wrong route/version, leaked records or changed modes breaks this.
        private = self.root / '.nda-harness'
        private.mkdir()
        (private / 'do-not-package').write_text('project-only')
        built = plugin_build.publish_committed(self.root)
        self.assertEqual([p.name for p in built],
                         ['nda-harness-codex', 'nda-harness-cursor', 'nda-harness-claude'])
        for client, relative in CATALOGS.items():
            catalog = json.loads((self.root / relative).read_text())
            self.assertEqual(catalog['name'], 'nda-harness-internal')
            self.assertEqual(len(catalog['plugins']), 1)
            entry = catalog['plugins'][0]
            self.assertEqual(entry['name'], 'nda-harness')
            route = entry['source']['path'] if client == 'codex' else entry['source']
            self.assertEqual((self.root / route).resolve(), self.root / 'packages' / f'nda-harness-{client}')
            if client == 'codex':
                self.assertEqual(entry['source']['source'], 'local')
                self.assertEqual(entry['policy'], {'installation': 'AVAILABLE', 'authentication': 'ON_USE'})
                self.assertTrue(entry['category'])
            else:
                self.assertTrue(catalog['owner']['name'])
            package = self.root / route
            manifest = json.loads((package / f'.{client}-plugin/plugin.json').read_text())
            self.assertEqual(manifest['version'], '0.0.4')
            self.assertEqual(json.loads((package / 'nda-plugin.json').read_text())['client'], client)
            self.assertTrue(os.access(package / 'bin/nda-plugin', os.X_OK))
            self.assertFalse((package / '.nda-harness').exists())
            hashes = json.loads((package / 'release.json').read_text())['asset_hashes']
            self.assertEqual(set(hashes), {p.relative_to(package).as_posix()
                                         for p in package.rglob('*') if p.is_file()} - {'release.json'})
            for name, expected in hashes.items():
                self.assertEqual(digest((package / name).read_bytes()), expected, name)
            hooks = (package / 'hooks/hooks.json').read_text()
            self.assertIn(f'--client {client} ', hooks)
            for other in set(CATALOGS) - {client}:
                self.assertNotIn(f'--client {other} ', hooks)
            if client == 'claude':
                self.assertNotIn('hooks', manifest)
                self.assertNotIn('mcpServers', manifest)
        before = self.snapshot()
        plugin_build.publish_committed(self.root)
        self.assertEqual(self.snapshot(), before)

    def test_bad_catalog_routes_and_package_identities_are_rejected(self):
        plugin_build.publish_committed(self.root)
        plugin_build.validate_marketplaces(self.root)
        for client, relative in CATALOGS.items():
            path = self.root / relative
            original = path.read_bytes()
            for bad in ('../outside', '/tmp', 'packages/missing', './packages/nda-harness-' +
                        ('cursor' if client != 'cursor' else 'codex')):
                with self.subTest(client=client, route=bad):
                    catalog = json.loads(original)
                    if client == 'codex':
                        catalog['plugins'][0]['source']['path'] = bad
                    else:
                        catalog['plugins'][0]['source'] = bad
                    path.write_text(json.dumps(catalog))
                    with self.assertRaisesRegex(ValueError, 'catalog|source|route'):
                        plugin_build.validate_marketplaces(self.root)
                path.write_bytes(original)
            path.unlink()
            with self.assertRaisesRegex(ValueError, 'catalog'):
                plugin_build.validate_marketplaces(self.root)
            path.write_bytes(original)
        package = self.root / 'packages/nda-harness-claude'
        config = package / 'nda-plugin.json'
        original = config.read_bytes()
        config.write_text('{"client":"codex"}')
        with self.assertRaisesRegex(ValueError, 'client'):
            plugin_build.validate_marketplaces(self.root)
        config.write_bytes(original)
        manifest_path = package / '.claude-plugin/plugin.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['version'] = '0.0.3'
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'version'):
            plugin_build.validate_marketplaces(self.root)

    def test_invalid_package_json_types_get_validation_errors(self):
        plugin_build.publish_committed(self.root)
        package = self.root / 'packages/nda-harness-codex'
        for relative in ('nda-plugin.json', '.codex-plugin/plugin.json'):
            path = package / relative
            original = path.read_bytes()
            for content in ('null', '[]'):
                with self.subTest(relative=relative, content=content):
                    path.write_text(content)
                    with self.assertRaisesRegex(ValueError, 'package'):
                        plugin_build.validate_marketplaces(self.root)
                path.write_bytes(original)

    def test_symlinked_package_cannot_escape_the_repository(self):
        plugin_build.publish_committed(self.root)
        package = self.root / 'packages/nda-harness-codex'
        outside = self.root.parent / 'outside'
        package.rename(outside)
        package.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'source|route|symlink'):
            plugin_build.validate_marketplaces(self.root)

    def test_failed_generation_preserves_previous_distribution(self):
        plugin_build.publish_committed(self.root)
        before = self.snapshot()
        original_build = plugin_build.build
        def fail_claude(source, destination, client, **kwargs):
            if client == 'claude':
                raise ValueError('invalid canonical asset')
            return original_build(source, destination, client, **kwargs)
        with patch.object(plugin_build, 'build', side_effect=fail_claude):
            with self.assertRaisesRegex(ValueError, 'invalid canonical asset'):
                plugin_build.publish_committed(self.root)
        self.assertEqual(self.snapshot(), before)

    def test_failed_output_replacement_restores_previous_distribution(self):
        plugin_build.publish_committed(self.root)
        before = self.snapshot()
        policy = self.root / 'pack/policy.md'
        policy.write_text(policy.read_text() + '\nUpdated canonical release content.\n')
        original_replace = os.replace
        failed = False
        def fail_once(source, destination):
            nonlocal failed
            if Path(destination) == self.root / '.cursor-plugin/marketplace.json' and not failed:
                failed = True
                raise OSError('publication interrupted')
            return original_replace(source, destination)
        with patch.object(plugin_build.os, 'replace', side_effect=fail_once):
            with self.assertRaisesRegex(OSError, 'publication interrupted'):
                plugin_build.publish_committed(self.root)
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
