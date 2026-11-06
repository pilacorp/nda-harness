"""Hindsight tool-use rules must cover MCP tools listed by name only (deferred schemas)."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from nda_harness import memory

SOURCES = (
    'plugin/skills/hindsight-memory/SKILL.md',
    'plugin/skills/session-bootstrap/SKILL.md',
    'plugin/rules/nda-harness.mdc',
    'pack/workflow.md',
)


class DeferredToolRuleTests(unittest.TestCase):
    def texts(self):
        yield 'memory.SYSTEMS session', memory.SYSTEMS['hindsight']['session']
        for relative in SOURCES:
            yield relative, (ROOT / relative).read_text(encoding='utf-8')

    def test_every_source_says_how_to_use_deferred_tools(self):
        for name, text in self.texts():
            flat = ' '.join(text.split())
            with self.subTest(source=name):
                self.assertIn('deferred', flat)
                self.assertIn('ToolSearch', flat)
                self.assertIn('not a missing tool', flat)

    def test_no_source_treats_unloaded_tools_as_missing(self):
        for name, text in self.texts():
            flat = ' '.join(text.split())
            with self.subTest(source=name):
                self.assertNotIn('Missing tools mean Hindsight', flat)
                self.assertNotIn('Missing tools mean\nunavailable', text)
                self.assertNotIn('use those available tools', flat)

    def test_auth_guidance_keeps_deferred_tools_out_of_the_unavailable_verdict(self):
        for client in ('claude', 'codex', 'cursor'):
            text = ' '.join(memory.auth_guidance(client).split())
            with self.subTest(client=client):
                self.assertIn('Tools not listed at all mean Hindsight is unavailable', text)
                self.assertIn('deferred', text)

    def test_hindsight_is_not_optional_once_tools_are_listed(self):
        flat = ' '.join(memory.SYSTEMS['hindsight']['session'].split())
        self.assertIn('optional to enable', flat)
        self.assertIn('recall and retain are expected, not optional', flat)
        self.assertIn('do not skip silently', flat)


if __name__ == '__main__':
    unittest.main()
