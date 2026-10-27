"""Tests for skill/scripts/next_block.py and agy_screen.py."""
import unittest

from _load import load

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


if __name__ == "__main__":
    unittest.main()
