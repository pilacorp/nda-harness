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
from nda_harness.files import Conflict, Plan, atomic, guard_path, read
from nda_harness.engine import exit_code
from nda_harness.mcp import check_context7, decode_response


class SafetyTests(unittest.TestCase):
    def test_existing_rtk_at_or_above_minimum_is_reused_without_installing(self):
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "rtk"
            executable.write_bytes(b"later installed build")
            plan = Plan({})
            for reported in ("0.40.0", "0.41.2", "1.1.0"):
                with self.subTest(reported=reported), patch("nda_harness.dependencies.locate", return_value=executable), patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "rtk " + reported + "\n")), patch("urllib.request.urlopen", side_effect=AssertionError("unexpected download")):
                    self.assertEqual(prepare(plan, Path(temporary)), executable)
            self.assertEqual(plan.writes, {})
            self.assertEqual(executable.read_bytes(), b"later installed build")

    def test_existing_rtk_below_minimum_is_left_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "rtk"
            executable.write_bytes(b"old build")
            plan = Plan({})
            with patch("nda_harness.dependencies.locate", return_value=executable), patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "rtk 0.37.2\n")), patch("urllib.request.urlopen", side_effect=AssertionError("unexpected download")):
                with self.assertRaisesRegex(Conflict, "0.40.0"):
                    prepare(plan, Path(temporary))
            self.assertEqual(plan.writes, {})
            self.assertEqual(executable.read_bytes(), b"old build")

    def test_rtk_identity_accepts_minimum_or_newer(self):
        with tempfile.TemporaryDirectory() as temporary:
            executable = Path(temporary) / "rtk"
            executable.write_bytes(b"fixture")
            accepted = ("0.40.0", "0.40.1", "1.1.0")
            rejected = ("0.37.2", "0.39.9", "9.9", "version 0.40.0")
            for reported in accepted:
                with self.subTest(reported=reported), patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "rtk " + reported + "\n")):
                    self.assertTrue(identity(executable))
            for reported in rejected:
                with self.subTest(reported=reported), patch("subprocess.run", return_value=subprocess.CompletedProcess([], 0, "rtk " + reported + "\n")):
                    self.assertFalse(identity(executable))
            with patch("subprocess.run", return_value=subprocess.CompletedProcess([], 1, "rtk 1.1.0\n")):
                self.assertFalse(identity(executable))
            with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("rtk", 10)):
                self.assertFalse(identity(executable))

    def test_read_does_not_require_a_writable_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve() / "package"
            directory.mkdir()
            target = directory / "nda-plugin.json"
            target.write_bytes(b'{"ok": true}\n')
            directory.chmod(0o555)
            try:
                self.assertEqual(read(target), b'{"ok": true}\n')
                self.assertIsNone(read(directory / "missing.json"))
            finally:
                directory.chmod(0o755)

    def test_write_to_unwritable_parent_names_the_permission_failure(self):
        import errno
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary).resolve() / "state"
            directory.mkdir()
            directory.chmod(0o555)
            try:
                with self.assertRaises(Conflict) as caught:
                    atomic(directory / "receipt.json", b"{}\n")
                self.assertIn("Unwritable destination (permissions)", str(caught.exception))
                self.assertFalse((directory / "receipt.json").exists())
            finally:
                directory.chmod(0o755)
            parent = Path(temporary).resolve()
            with patch("nda_harness.files.os.access", return_value=False), patch("nda_harness.files.os.open", side_effect=PermissionError(errno.EPERM, "operation not permitted")):
                with self.assertRaises(Conflict) as caught:
                    guard_path(parent / "receipt.json")
            self.assertIn("Unwritable destination (sandbox)", str(caught.exception))

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
