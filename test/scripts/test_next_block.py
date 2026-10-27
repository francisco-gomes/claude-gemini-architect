"""Tests for skill/scripts/next_block.py and agy_screen.py."""
import json
import subprocess
import sys
import unittest

from _fake_herdr import fake_herdr_env
from _load import SCRIPTS, load

agy_screen = load("agy_screen")
next_block = load("next_block")

BLOCKS = [agy_screen.squash(b) for b in [
    "cd /repo && git status --short && echo OK || echo FAILED",
    "gh pr merge feat-x --merge --subject 'feat: x' > /tmp/pB_merge.txt 2>&1",
    "gh pr merge feat-x --merge --subject 'feat: y'",
    "git log .",
]]


def dialog(command):
    return f"Gemini wants to run a command\nRequesting permission for:\n  {command}\nRun this command?\n> Yes  No"


class PendingRequest(unittest.TestCase):
    def test_n1_no_dialog(self):
        self.assertIsNone(agy_screen.pending_request("Thinking...\nesc to interrupt"))

    def test_n2_dialog_returns_the_command_text(self):
        self.assertIn("npx vitest run", agy_screen.pending_request(dialog("npx vitest run")))


class Describe(unittest.TestCase):
    def describe(self, command):
        return next_block.describe(agy_screen.pending_request(dialog(command)), BLOCKS)

    def test_n3_exact_match_across_a_line_wrap(self):
        self.assertEqual(self.describe("cd /repo && git status\n   --short && echo OK || echo FAILED"), "REQUEST: B0")

    def test_n4_truncated_unique_prefix(self):
        self.assertEqual(self.describe("gh pr merge feat-x --merge --subject 'feat: x' > /tmp/pB_m⋯"), "REQUEST: B1")

    def test_n5_truncated_ambiguous_prefix_lists_every_candidate(self):
        self.assertEqual(self.describe("gh pr merge feat-x --merge --subj⋯"), "REQUEST: B1|B2 (truncated, ambiguous)")

    def test_n6_command_not_in_the_script(self):
        self.assertEqual(self.describe("rm -rf /tmp/x"), "REQUEST: OFF-SCRIPT: rm -rf /tmp/x")

    def test_n7_nothing_visible_never_matches_a_block(self):
        self.assertTrue(self.describe("⋯").startswith("REQUEST: OFF-SCRIPT:"))

    def test_n8_trailing_dot_kept_when_not_truncated(self):
        self.assertEqual(self.describe("git log ."), "REQUEST: B3")

    def test_n9_unicode_ellipsis_is_truncation_too(self):
        self.assertEqual(self.describe("gh pr merge feat-x --merge --subject 'feat: x' > /tmp/pB_m…"), "REQUEST: B1")

    def test_n10_truncation_rule_is_shared(self):
        self.assertIs(next_block.is_truncated, agy_screen.is_truncated)

    def test_n13_ellipsis_inside_a_full_command_is_not_truncation(self):
        block = 'git commit -m "wip…" && echo OK'
        self.assertEqual(next_block.describe(block, [agy_screen.squash(block)]), "REQUEST: B0")


class AgainstFakeHerdr(unittest.TestCase):
    def run_next_block(self, screens, status, blocks):
        env, state = fake_herdr_env(self, screens, status)
        env.update(GEMINI_ARCHITECT_POLL_SECS="0.05", GEMINI_ARCHITECT_WAIT_SECS="0.5")
        blocks_file = state.with_name("blocks.json")
        blocks_file.write_text(json.dumps(blocks))
        return subprocess.run([sys.executable, str(SCRIPTS / "next_block.py"), str(blocks_file), "gemini-exec"],
                              env=env, capture_output=True, text=True, timeout=20)

    def test_n11_request_for_a_script_block(self):
        block = "cd /repo && git status --short && echo OK || echo FAILED"
        r = self.run_next_block([dialog(block)], ["running"], [block])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines()[0], "REQUEST: B0")

    def test_n12_bounded_wait_reports_no_request(self):
        r = self.run_next_block(["Working on it... running tests"], ["working"], ["ls"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.splitlines()[0].startswith("NO REQUEST YET"))

    def test_n14_reads_the_screen_at_least_once_even_with_a_tiny_deadline(self):
        block = "ls -la"
        env_wait = {"GEMINI_ARCHITECT_WAIT_SECS": "0.01"}
        env, state = fake_herdr_env(self, [dialog(block)], ["running"])
        env.update(GEMINI_ARCHITECT_POLL_SECS="0.05", **env_wait)
        blocks_file = state.with_name("blocks.json")
        blocks_file.write_text(json.dumps([block]))
        r = subprocess.run([sys.executable, str(SCRIPTS / "next_block.py"), str(blocks_file), "gemini-exec"],
                           env=env, capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines()[0], "REQUEST: B0")


if __name__ == "__main__":
    unittest.main()
