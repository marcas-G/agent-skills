import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install.py"


class InstallerTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                              cwd=ROOT, text=True, capture_output=True)

    def test_install_universal_and_runtime(self):
        with tempfile.TemporaryDirectory() as temp:
            r = self.run_cli("--agent", "universal", "--scope", "project",
                             "--target", temp, "--only", "plain", "fractal")
            self.assertEqual(r.returncode, 0, r.stderr)
            dst = Path(temp) / ".agents" / "skills"
            self.assertTrue((dst / "plain" / "SKILL.md").is_file())
            self.assertTrue((dst / "fractal" / "_plugin" / "scripts" / "fractal.py").is_file())
            duplicate = self.run_cli("--agent", "universal", "--scope", "project",
                                     "--target", temp, "--only", "plain")
            self.assertNotEqual(duplicate.returncode, 0)
            replace = self.run_cli("--agent", "universal", "--scope", "project",
                                   "--target", temp, "--only", "plain", "--force")
            self.assertEqual(replace.returncode, 0, replace.stderr)

    def test_dry_run_never_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            r = self.run_cli("--agent", "gemini", "--scope", "user",
                             "--target", temp, "--only", "optloop", "--dry-run")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertFalse((Path(temp) / ".gemini").exists())

    def test_portable_locations(self):
        paths = {
            "cursor": ".cursor/skills",
            "opencode": ".opencode/skills",
            "gemini": ".gemini/skills",
            "copilot": ".github/skills",
            "claude": ".claude/skills",
            "codex": ".agents/skills",
        }
        for agent, relative in paths.items():
            with self.subTest(agent=agent), tempfile.TemporaryDirectory() as temp:
                r = self.run_cli("--agent", agent, "--scope", "project",
                                 "--target", temp, "--only", "termcard", "--no-runtime")
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertTrue((Path(temp) / relative / "termcard" / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
