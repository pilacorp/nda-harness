import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from nda_harness.dependencies import unpack
from nda_harness.files import Conflict, Plan, atomic
from nda_harness.engine import exit_code
from nda_harness.mcp import check_context7, decode_response


class SafetyTests(unittest.TestCase):
    def test_wrong_archive_checksum_never_extracts(self):
        with self.assertRaisesRegex(Conflict, "checksum mismatch"):
            unpack(b"not an official archive")

    def test_full_conflict_stops_planned_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            path = root / "owned"
            path.write_text("user data")
            plan = Plan({})
            with self.assertRaises(Conflict):
                plan.file(path, b"replacement")
            self.assertEqual(path.read_text(), "user data")
            self.assertEqual(plan.applied, [])

    def test_rollback_preserves_intervening_user_edit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            path = root / "owned"
            plan = Plan({})
            plan.file(path, b"installed")
            plan.apply(root / "state")
            path.write_text("user edit")
            self.assertEqual(plan.rollback(), [str(path)])
            self.assertEqual(path.read_text(), "user edit")

    def test_modified_destination_after_preflight_conflicts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            path = root / "owned"
            plan = Plan({})
            plan.file(path, b"installed")
            path.write_text("user edit")
            with self.assertRaises(Conflict):
                plan.apply(root / "state")
            self.assertEqual(path.read_text(), "user edit")

    def test_failure_takes_precedence_over_pending(self):
        self.assertEqual(exit_code([{"status": "verified"}]), 0)
        self.assertEqual(exit_code([{"status": "awaiting_manual"}]), 3)
        self.assertEqual(exit_code([{"status": "awaiting_manual"}, {"status": "failed"}]), 1)

    def test_sse_and_json_decode(self):
        self.assertEqual(decode_response(b'{"id":1,"result":{}}')["id"], 1)
        self.assertEqual(decode_response(b'event: message\r\ndata: {"id":1,"result":{}}\r\n\r\n')["id"], 1)

    def test_auth_error_is_sanitized_pending(self):
        error = urllib.error.HTTPError("https://example", 401, "secret-token", {}, io.BytesIO(b"secret-token"))
        with patch("urllib.request.urlopen", side_effect=error):
            result = check_context7()
        self.assertEqual(result["status"], "awaiting_manual")
        self.assertNotIn("secret-token", str(result))

    def test_rate_limit_is_failed(self):
        error = urllib.error.HTTPError("https://example", 429, "rate limit", {}, io.BytesIO(b"private"))
        with patch("urllib.request.urlopen", side_effect=error):
            result = check_context7()
        self.assertEqual(result["status"], "failed")

    def test_rpc_tool_resolution_and_docs_use_returned_identifier(self):
        class Response:
            headers = {}
            def __init__(self, body):
                self.body = body
            def read(self, size):
                return self.body
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
        responses = [
            {"jsonrpc": "2.0", "id": 1, "result": {}}, {},
            {"id": 2, "result": {"tools": [{"name": "resolve-library-id"}, {"name": "query-docs"}]}},
            {"id": 3, "result": {"content": [{"type": "text", "text": "Context7-compatible library ID: /python/cpython"}]}},
            {"id": 4, "result": {"content": [{"type": "text", "text": "Focused public documentation"}]}},
        ]
        with patch("urllib.request.urlopen", side_effect=[Response(json.dumps(r).encode()) for r in responses]) as transport:
            result = check_context7()
        self.assertEqual(result["status"], "verified")
        request = transport.call_args_list[-1].args[0]
        self.assertEqual(json.loads(request.data)["params"]["arguments"]["libraryId"], "/python/cpython")


if __name__ == "__main__":
    unittest.main()
