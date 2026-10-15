import io
import json
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from nda_harness.dependencies import unpack, identity, prepare
from nda_harness.files import Conflict, Plan, atomic
from nda_harness.engine import exit_code
from nda_harness.mcp import check_context7, decode_response


class SafetyTests(unittest.TestCase):
    def test_existing_rtk_040_is_reused_without_installing(self):
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "rtk"
            executable.write_bytes(b"known Homebrew build")
            plan = Plan({})
            with patch("nda_harness.dependencies.locate", return_value=executable), patch("nda_harness.dependencies.digest", return_value="52b2a4a68e9a1f3c7880ddafea6cd590f0582e67324fe89ea41aaec83e7e9b58"), patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "rtk 0.40.0\n")), patch("urllib.request.urlopen", side_effect=AssertionError("unexpected download")):
                self.assertEqual(prepare(plan, Path(temporary)), executable)
            self.assertEqual(plan.writes, {})
            self.assertEqual(executable.read_bytes(), b"known Homebrew build")

    def test_rtk_identity_requires_matching_hash_and_version(self):
        hashes = {"fb212aaa57018cff146a9053810b310845e477b4a1f789d38b4cf2908bb5c5dd": "0.37.2",
                  "33f8ba7f298ded5c88b5cc805267f03036fdf15731d3db9fa1f49ae98a6d6f53": "0.37.2",
                  "52b2a4a68e9a1f3c7880ddafea6cd590f0582e67324fe89ea41aaec83e7e9b58": "0.40.0"}
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "rtk"
            executable.write_bytes(b"fixture")
            for checksum, version in hashes.items():
                for reported, code, expected in ((version, 0, True), ("9.9.9", 0, False), (version, 1, False)):
                    with self.subTest(version=version, reported=reported, code=code), patch("nda_harness.dependencies.digest", return_value=checksum), patch("subprocess.run", return_value=subprocess.CompletedProcess([], code, "rtk " + reported + "\n")):
                        self.assertEqual(identity(executable), expected)
            with patch("subprocess.run", side_effect=AssertionError("must not run an unknown binary")):
                self.assertFalse(identity(executable))

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
