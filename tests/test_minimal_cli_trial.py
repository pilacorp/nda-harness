"""Tests for prerequisite trial tooling, not installer acceptance evidence."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


SOURCE = Path(__file__).resolve().parents[1] / "scripts/compatibility/minimal_cli_trial.py"
spec = importlib.util.spec_from_file_location("trial", SOURCE)
trial = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trial)


class TrialTests(unittest.TestCase):
    def test_environment_does_not_inherit_credentials_or_personal_config(self):
        with tempfile.TemporaryDirectory() as root:
            env = trial.isolated_environment(Path(root), "/usr/bin:/bin")
            self.assertEqual(env["HOME"], root)
            self.assertEqual(env["CODEX_HOME"], str(Path(root) / ".codex"))
            self.assertEqual(set(env), {"HOME", "PATH", "CODEX_HOME", "XDG_CONFIG_HOME", "NO_OPEN_BROWSER"})

    def test_missing_binary_is_pending(self):
        result = trial.version_probe(None, {}, Path("/tmp"))
        self.assertEqual(result, {"status": "not_installed", "version": None})

    def test_failed_probe_does_not_publish_raw_output(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            binary = root / "broken"
            binary.write_text("#!/bin/sh\necho secret-token >&2\nexit 1\n")
            binary.chmod(0o755)
            result = trial.version_probe(str(binary), trial.isolated_environment(root, "/usr/bin:/bin"), root)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["exit_code"], 1)
            self.assertNotIn("secret-token", str(result))

    def test_successful_version_is_allowlisted(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            binary = root / "version"
            binary.write_text("#!/bin/sh\necho 'rtk 0.37.2'\n")
            binary.chmod(0o755)
            result = trial.version_probe(str(binary), {}, root)
            self.assertEqual(result["version"], "0.37.2")
            self.assertEqual(result["status"], "available")

    def test_unrecognized_success_does_not_publish_output(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            binary = root / "version"
            binary.write_text("#!/bin/sh\necho 'secret-token'\n")
            binary.chmod(0o755)
            result = trial.version_probe(str(binary), {}, root)
            self.assertEqual(result["status"], "unrecognized_version")
            self.assertNotIn("secret-token", str(result))

    def test_timeout_does_not_promote_readiness(self):
        import subprocess
        with patch.object(trial.subprocess, "run", side_effect=subprocess.TimeoutExpired("probe", 15, output="secret-token")):
            result = trial.version_probe("probe", {}, Path("/tmp"))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["reason"], "timeout")
        self.assertNotIn("secret-token", str(result))

    def test_matrix_never_infers_client_support_from_inventory(self):
        rows = trial.pending_matrix()
        self.assertEqual(len(rows), 24)
        self.assertEqual(len({(r["architecture"], r["surface"], r["scope"]) for r in rows}), 24)
        self.assertTrue(all(r["status"] == "pending" for r in rows))

    def test_snapshot_records_hashes_not_file_contents(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            (root / "config.json").write_text("secret-token")
            snapshot = trial.file_hashes(root)
            self.assertEqual(len(snapshot["config.json"]), 64)
            self.assertNotIn("secret-token", str(snapshot))


if __name__ == "__main__":
    unittest.main()
