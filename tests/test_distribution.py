import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.source = self.base / "source with spaces"
        self.source.mkdir()
        for directory in ("bin", "scripts", "pack", "skills", "vendor"):
            shutil.copytree(ROOT / directory, self.source / directory, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("install.sh",):
            if (ROOT / name).exists():
                shutil.copy2(ROOT / name, self.source / name)
        self.env = {"PATH": os.environ["PATH"], "HOME": str(self.base), "PYTHONNOUSERSITE": "1"}

    def test_launcher_works_without_venv_or_pip(self):
        result = subprocess.run([str(self.source / "bin/nda-harness"), "--help"], cwd=self.base, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("setup", result.stdout)
        self.assertFalse((self.source / ".venv").exists())

    def test_bundled_tomlkit_imports_without_site_packages(self):
        python = shutil.which("python3")
        code = "import sys; sys.path.insert(0, 'scripts'); import nda_harness; import tomlkit; print(tomlkit.__version__)"
        result = subprocess.run([python, "-S", "-c", code], cwd=self.source, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "0.13.3")

    def test_installed_command_survives_source_removal(self):
        prefix = self.base / "prefix with spaces"
        result = subprocess.run([str(self.source / "install.sh"), "--prefix", str(prefix)], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        shutil.rmtree(self.source)
        result = subprocess.run([str(prefix / "bin/nda-harness"), "--help"], cwd=self.base, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((prefix / "share/nda-harness/.venv").exists())

    def test_modified_bundle_is_rejected(self):
        wheel = self.source / "vendor/tomlkit-0.13.3-py3-none-any.whl"
        wheel.write_bytes(b"changed")
        result = subprocess.run([str(self.source / "bin/nda-harness"), "--help"], env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("bundle", result.stderr.lower())
        self.assertNotIn("Traceback", result.stderr)

    def test_reinstall_is_idempotent(self):
        prefix = self.base / "prefix"
        command = [str(self.source / "install.sh"), "--prefix", str(prefix)]
        self.assertEqual(subprocess.run(command, env=self.env, capture_output=True).returncode, 0)
        manifest = prefix / "share/nda-harness/install-manifest.json"
        before = manifest.stat().st_mtime_ns
        self.assertEqual(subprocess.run(command, env=self.env, capture_output=True).returncode, 0)
        self.assertEqual(manifest.stat().st_mtime_ns, before)

    def test_existing_unowned_command_is_not_overwritten(self):
        prefix = self.base / "prefix"
        command = prefix / "bin/nda-harness"
        command.parent.mkdir(parents=True)
        command.write_text("existing user command")
        result = subprocess.run([str(self.source / "install.sh"), "--prefix", str(prefix)], env=self.env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(command.read_text(), "existing user command")
        self.assertFalse((prefix / "share/nda-harness").exists())


if __name__ == "__main__":
    unittest.main()
