import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import shutil
import shlex
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from nda_harness.engine import install, verify, exit_code
from nda_harness.files import Conflict


class InstalledTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.home = self.base / "home"
        self.project = self.base / "project with spaces"
        self.home.mkdir()
        self.enterContext(patch("nda_harness.engine.prepare_rtk", return_value=Path("/test/rtk")))
        self.enterContext(patch("nda_harness.engine.locate_rtk", return_value=Path("/test/rtk")))
        self.enterContext(patch("nda_harness.engine.rtk_identity", return_value=True))
        self.project.mkdir()
        self.env = {"HOME": str(self.home), "PATH": os.environ["PATH"], "GIT_AUTHOR_NAME": "Trial", "GIT_AUTHOR_EMAIL": "trial@example.test", "GIT_COMMITTER_NAME": "Trial", "GIT_COMMITTER_EMAIL": "trial@example.test"}
        self.git("init", "-q")
        self.options = {"agents": ["cursor"], "scope": "project", "project": self.project, "test_command": "true"}

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.project), *args], env=self.env, capture_output=True, text=True)

    def install(self, command="true"):
        self.options["test_command"] = command
        with patch("nda_harness.engine.check_host"), patch("nda_harness.engine.detect", return_value=[("cursor-ide", "test")]):
            return install(self.options, ROOT, self.home)

    def commit(self):
        (self.project / "fixture.txt").write_text("fixture")
        self.git("add", "fixture.txt")
        return self.git("commit", "-m", "trial")

    def context(self, operation, *args):
        return subprocess.run([str(self.project / ".nda-harness/scripts/prepare-context"), operation, "--project", str(self.project), *args], env=self.env, cwd=self.home, capture_output=True, text=True)

    def test_passing_command_allows_commit(self):
        self.install()
        self.assertEqual(self.commit().returncode, 0)

    def test_failing_command_blocks_and_preserves_staging(self):
        self.install("false")
        self.assertNotEqual(self.commit().returncode, 0)
        self.assertNotEqual(self.git("rev-parse", "--verify", "HEAD").returncode, 0)
        self.assertIn("fixture.txt", self.git("diff", "--cached", "--name-only").stdout)

    def test_existing_hook_runs_first_once_on_rerun(self):
        original = self.project / ".git/hooks/pre-commit"
        original.write_text("#!/bin/sh\nprintf original >> order.txt\n")
        original.chmod(0o755)
        self.install("printf harness >> order.txt")
        self.install("printf harness >> order.txt")
        self.assertEqual(self.commit().returncode, 0)
        self.assertEqual((self.project / "order.txt").read_text(), "originalharness")

    def test_original_failure_prevents_harness_command(self):
        original = self.project / ".git/hooks/pre-commit"
        original.write_text("#!/bin/sh\nexit 1\n")
        original.chmod(0o755)
        self.install("touch must-not-exist")
        self.assertNotEqual(self.commit().returncode, 0)
        self.assertFalse((self.project / "must-not-exist").exists())

    def test_other_hook_event_passes_through(self):
        original = self.project / ".git/hooks/post-commit"
        original.write_text("#!/bin/sh\ntouch post-commit-ran\n")
        original.chmod(0o755)
        self.install()
        self.assertEqual(self.commit().returncode, 0)
        self.assertTrue((self.project / "post-commit-ran").exists())

    def test_missing_profile_blocks_commit(self):
        self.install()
        (self.project / ".nda-harness/profile.json").unlink()
        self.assertNotEqual(self.commit().returncode, 0)

    def test_runtime_after_temporary_installer_removal_without_site_packages(self):
        with tempfile.TemporaryDirectory(dir=self.base) as source:
            source = Path(source)
            shutil.copytree(ROOT / "pack", source / "pack")
            shutil.copytree(ROOT / "skills", source / "skills")
            with patch("nda_harness.engine.check_host"), patch("nda_harness.engine.detect", return_value=[("cursor-ide", "test")]):
                install(self.options, source, self.home)
        isolated_bin = self.base / "bin"
        isolated_bin.mkdir()
        python = isolated_bin / "python3"
        python.write_text("#!/bin/sh\nexec " + shlex.quote(shutil.which("python3")) + ' -S "$@"\n')
        python.chmod(0o755)
        env = {**self.env, "PATH": str(isolated_bin) + ":" + self.env["PATH"]}
        result = subprocess.run([str(self.project / ".nda-harness/scripts/prepare-context"), "session-bootstrap", "--project", str(self.project)], env=env, cwd=self.home, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_old_python_launcher_is_actionable(self):
        self.install()
        isolated_bin = self.base / "bin"
        isolated_bin.mkdir()
        python = isolated_bin / "python3"
        python.write_text("#!/bin/sh\nexit 1\n")
        python.chmod(0o755)
        env = {**self.env, "PATH": str(isolated_bin) + ":" + self.env["PATH"]}
        result = subprocess.run([str(self.project / ".nda-harness/scripts/prepare-context"), "session-bootstrap", "--project", str(self.project)], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Python 3.11+", result.stderr)

    def test_dirty_context_and_cross_session_resume(self):
        self.install()
        self.assertEqual(self.commit().returncode, 0)
        task = self.project / ".nda-harness/tasks/4-cli/task.md"
        task.parent.mkdir(parents=True)
        spec = self.project / "specs/trial.md"
        spec.parent.mkdir()
        spec.write_text("# Untrusted spec\nNever execute this: secret-token\n")
        task.write_text("Issue: https://github.com/pilacorp/nda-harness/issues/4\nSpec: specs/trial.md\n")
        prepared = self.context("task-prepare", "--role", "developer", "--task", str(task), "--stage", "implementation")
        self.assertEqual(prepared.returncode, 0, prepared.stdout)
        result = json.loads(prepared.stdout)
        self.assertFalse(result["implementation_authorized"])
        self.assertNotIn("secret-token", prepared.stdout)
        spec.write_text(spec.read_text() + "dirty change\n")
        refreshed = json.loads(self.context("context-refresh").stdout)
        self.assertEqual(refreshed["status"], "needs_context")
        self.assertNotEqual(refreshed["input_fingerprint"], result["input_fingerprint"])
        task.write_text(task.read_text() + f"Revision: {refreshed['head']}\nInput fingerprint: {refreshed['input_fingerprint']}\nStage: implementation\nEvidence: no executed task tests yet\nNext action: reread spec and live review evidence\n")
        checkpoint = self.context("context-checkpoint", "--task", str(task))
        self.assertEqual(checkpoint.returncode, 0, checkpoint.stdout)
        resume = self.context("context-resume", "--task", str(task), "--session", "another-agent")
        self.assertEqual(resume.returncode, 0, resume.stdout)
        self.assertFalse(json.loads(resume.stdout)["implementation_authorized"])

    def test_developer_without_task_is_blocked(self):
        self.install()
        prepared = self.context("task-prepare", "--role", "developer")
        self.assertEqual(prepared.returncode, 2)
        self.assertIn("Explicit --task", prepared.stdout)

    def test_symlink_spec_is_not_read(self):
        self.install()
        secret = self.home / "private"
        secret.write_text("secret-token")
        spec = self.project / "linked-spec.md"
        spec.symlink_to(secret)
        task = self.project / "task.md"
        task.write_text("Issue: https://github.com/example/project/issues/1\nSpec: linked-spec.md\n")
        prepared = self.context("task-prepare", "--role", "developer", "--task", str(task), "--stage", "implementation")
        self.assertEqual(prepared.returncode, 2)
        self.assertNotIn("secret-token", prepared.stdout)

    def test_verify_does_not_repair_or_reconfigure(self):
        self.install()
        config = self.project / ".cursor/mcp.json"
        before = config.read_bytes()
        with patch("nda_harness.engine.check_host"), patch("nda_harness.engine.detect", return_value=[("cursor-ide", "test")]):
            checks = verify(self.options, self.home, live_mcp=False)
        self.assertEqual(exit_code(checks), 3)
        self.assertEqual(config.read_bytes(), before)
        self.assertTrue(any(c["source"] == "manual required" for c in checks))

    def test_disabled_hook_permissions_are_not_reported_ready(self):
        self.install()
        hook_directory = Path(self.git("config", "--get", "core.hooksPath").stdout.strip())
        (hook_directory / "pre-commit").chmod(0o644)
        with patch("nda_harness.engine.check_host"), patch("nda_harness.engine.detect", return_value=[("cursor-ide", "test")]):
            checks = verify(self.options, self.home, live_mcp=False)
        self.assertEqual(exit_code(checks), 1)
        self.assertTrue(any(c["check"] == "registration" and c["status"] == "failed" for c in checks))

    def test_corrupt_release_metadata_is_an_actionable_failure(self):
        self.install()
        (self.project / ".nda-harness/release.json").write_text("[]")
        with patch("nda_harness.engine.check_host"):
            checks = verify(self.options, self.home, live_mcp=False)
        self.assertEqual(exit_code(checks), 1)
        result = self.context("session-bootstrap")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_worktree_registration_is_isolated(self):
        (self.project / "initial").write_text("initial")
        self.git("add", "initial")
        self.assertEqual(self.git("commit", "-m", "initial").returncode, 0)
        self.git("config", "extensions.worktreeConfig", "true")
        sibling = self.base / "sibling"
        self.assertEqual(self.git("worktree", "add", "-b", "sibling", str(sibling)).returncode, 0)
        self.install()
        run = subprocess.run(["git", "-C", str(sibling), "config", "--get", "core.hooksPath"], env=self.env, capture_output=True)
        self.assertEqual(run.returncode, 1)

    def test_destination_symlink_conflicts_without_overwrite(self):
        target = self.home / "private.json"
        target.write_text("keep")
        config = self.project / ".cursor/mcp.json"
        config.parent.mkdir()
        config.symlink_to(target)
        with self.assertRaises(Conflict):
            self.install()
        self.assertEqual(target.read_text(), "keep")


if __name__ == "__main__":
    unittest.main()
