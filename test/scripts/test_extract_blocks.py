"""Tests for skill/scripts/extract_blocks.py."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _load import SCRIPTS, load

extract_blocks = load("extract_blocks")

PLAN = """# Plan
## Task 1
```bash
npm test
```
# PART B — production
## B0
```bash
cd /repo &&   git status
  --short && echo OK || echo FAILED
```
## B1
```bash
gh pr merge 1
```
"""


class ExtractPartBBlocks(unittest.TestCase):
    def test_e1_only_part_b_blocks_in_order_with_whitespace_collapsed(self):
        self.assertEqual(
            extract_blocks.extract_part_b_blocks(PLAN),
            ["cd /repo && git status --short && echo OK || echo FAILED", "gh pr merge 1"],
        )

    def test_e2_plan_without_part_b_raises(self):
        with self.assertRaisesRegex(ValueError, "no '# PART B' heading"):
            extract_blocks.extract_part_b_blocks("# Plan\n```bash\nnpm test\n```\n")

    def test_e3_part_b_without_bash_blocks_raises(self):
        with self.assertRaisesRegex(ValueError, "no ```bash blocks"):
            extract_blocks.extract_part_b_blocks("# PART B\nnothing to run\n")

    def test_e4_heading_must_be_exactly_part_b(self):
        with self.assertRaisesRegex(ValueError, "no '# PART B' heading"):
            extract_blocks.extract_part_b_blocks("# PART BETA\n```bash\nls\n```\n")


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "extract_blocks.py"), *args],
            capture_output=True, text=True,
        )

    def test_e5_writes_json_and_reports_count(self):
        with tempfile.TemporaryDirectory() as d:
            plan, out = Path(d, "plan.md"), Path(d, "blocks.json")
            plan.write_text(PLAN, encoding="utf-8")
            r = self.run_cli(str(plan), str(out))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout.strip(), "2 blocks (B0..B1)")
            self.assertEqual(len(json.loads(out.read_text(encoding="utf-8"))), 2)

    def test_e6_plan_without_part_b_exits_1_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            plan, out = Path(d, "plan.md"), Path(d, "blocks.json")
            plan.write_text("# Plan only\n", encoding="utf-8")
            r = self.run_cli(str(plan), str(out))
            self.assertEqual(r.returncode, 1)
            self.assertIn("PART B", r.stderr)
            self.assertFalse(out.exists())

    def test_e7_wrong_argument_count_exits_2(self):
        r = self.run_cli("only-one-arg")
        self.assertEqual(r.returncode, 2)
        self.assertIn("usage:", r.stderr)


if __name__ == "__main__":
    unittest.main()
