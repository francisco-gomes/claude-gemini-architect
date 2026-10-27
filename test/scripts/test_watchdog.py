"""Tests for skill/scripts/watchdog.py (unit tests + runs against a fake herdr)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from _fake_herdr import fake_herdr_env
from _load import SCRIPTS, load

watchdog = load("watchdog")

FORBIDDEN = [
    "git push", "git push origin main --force", "npx vitest run && git push", "gh pr merge 1",
    "docker compose up", "./deploy.sh prod", "npm run deploy", "npm run migrate:prod",
    "npx typeorm migration:run", "psql -c 'delete from orders'", "rm -rf build", "rm -r dist",
    "npm install lodash", "pnpm add zod", "pip install requests", "curl https://example.com",
    "git checkout -- src/a.ts", "git restore src/a.ts", "git stash", "sudo ls", "kill 123", "ssh host",
    "git -C /repo push origin main", "git --no-pager reset --hard HEAD~3", "git -c core.pager=cat push",
    "./scripts/migrate.sh", "python migrate.py", "node db/migrate.js",
    "npm run deploy:prod", "yarn deploy:staging", "./deploy-prod.sh", "./deploy.sh;echo done", 'sh -c "./deploy.sh"',
    "rm -f -r src", "rm -v -rf build", "rm --recursive dist", "find . -name '*.tmp' -delete",
    "nvm install 18", "nvm use 20", "fnm install 22", "volta install node@18", "asdf install nodejs 20.0.0",
    "pyenv install 3.11", "n 18",
    "cd /r && n 20", "true; n lts",
    "node scripts/deploy.js", "python deploy.py", "./deploy_prod.sh", "npm run deploy&&echo ok",
    "git checkout HEAD -- a.js", "git checkout .", "git checkout -- .",
    "rm build -rf", "rm dir -r",
    "n stable", "n install 20", "n current", "n auto", "echo hi\nn 18",
]
ALLOWED = [
    "npx vitest run test/deploy.test.ts", "npx vitest run test/migration.test.ts", "git status --short",
    "git add -- src/a.ts", "git commit -q -F -", "npx tsc --noEmit", "git --no-pager log --oneline -1",
    "python3 -m pytest -q", "npm init -y",
    "git -C /repo status --short", "git --no-pager diff --stat", "rm -f /tmp/cga_x.txt", "find . -name '*.py'",
    "npm run lint", "nvm ls", "node --version",
    "head -n 5 /tmp/x.txt", "git --no-pager log -n 3 --oneline", "tail -n 20 /tmp/cga_x.txt",
    'git commit -m "chore: clean up imports"', "git commit -q -F - <<'MSG' fix: push notifications MSG",
    "git checkout -q feat/x", "git checkout -b feat/y", "go test ./...", "cat docs/deployment.md",
]

def dialog(command):
    return f"Requesting permission for:\n  {command}\nRun this command?\n> Yes  No"


class DenyList(unittest.TestCase):
    def test_w1_forbidden_and_allowed_commands(self):
        rx = watchdog.deny_regex()
        for command in FORBIDDEN:
            with self.subTest(forbidden=command):
                self.assertTrue(watchdog.is_forbidden(command, rx))
        for command in ALLOWED:
            with self.subTest(allowed=command):
                self.assertFalse(watchdog.is_forbidden(command, rx))

    def test_w8_extra_deny_adds_to_the_built_in_list(self):
        rx = watchdog.deny_regex(r"make\s+release")
        self.assertTrue(watchdog.is_forbidden("make release", rx))
        self.assertTrue(watchdog.is_forbidden("git push", rx))

    def test_w10_truncation_detection(self):
        self.assertTrue(watchdog.is_truncated("npx vitest run && gi⋯"))
        self.assertFalse(watchdog.is_truncated("npx vitest run"))

    def test_w11_ellipsis_and_three_dots_are_truncation(self):
        self.assertTrue(watchdog.is_truncated("npx vitest run && git pu…"))
        self.assertTrue(watchdog.is_truncated("npx vitest run && git pu...."))
        self.assertFalse(watchdog.is_truncated("git log ."))

    def test_w13_truncation_rule_is_shared(self):
        self.assertIs(watchdog.is_truncated, load("agy_screen").is_truncated)

    def test_w14_no_false_truncation(self):
        self.assertFalse(watchdog.is_truncated("go test ./..."))
        self.assertFalse(watchdog.is_truncated('git commit -m "wip…" && echo OK'))
        self.assertTrue(watchdog.is_truncated("x && y ⋯ (2 lines hidden)"))


PLAN_TEXT = textwrap.dedent("""\
    # Plan
    ```bash
    npx vitest run
    ```
    ```bash
    cd /repo && git add -- a.ts && git commit -q -F - <<'MSG'
    feat: deploy notes
    MSG
    ```
    # PART B
    ```bash
    git push origin main
    ```
    """)

READ_ONLY_OK = [
    "cat /tmp/cga_t5_red.txt", "git status --short; git --no-pager log --oneline -5",
    "test -e package.json && echo EXISTS || echo NOT_FOUND", "ls -la skill/scripts", "grep -n slugify src/text.ts",
    "tail -1 /tmp/cga_x.txt | grep -q OK && echo OK || echo FAILED", "git --no-pager diff --stat",
    "git show HEAD~1:lib/installer.js", "cd /repo && git diff", "head -n 20 README.md", "wc -l docs/a.md",
    "find . -name '*.py'", "node --version", "python3 --version", "git rev-parse HEAD", "git ls-files",
    "which node", "command -v agy", "pwd", "ls 2>/dev/null", "cat x 2>&1", "git branch --show-current",
]
READ_ONLY_NO = [
    "rm -f /tmp/x", "echo hi > file.txt", "cat a >> b", "cat <<EOF", "echo $(curl x)", "echo `id`",
    "find . -delete", "find . -exec rm {} ;", "sed -i s/a/b/ f", "awk 'BEGIN{print 1}'",
    "git -C /repo status", "git -c x=y log", "git commit -m x", "git checkout main", "git branch -D x",
    "npm test", "npx vitest run", "env | grep NODE", "nvm ls", "node -e 'process.exit(0)'", "python3 -c 'print(1)'",
    "PYTHONDONTWRITEBYTECODE=1 python3 -m unittest", "bash -c 'ls'", "ls | xargs rm", "echo x | tee out.txt",
    "git branch -m new", "cat /tmp/a | sh", "ls & rm x", "diff <(ls) <(ls)",
]


class ReadOnly(unittest.TestCase):
    def test_w18_read_only_table(self):
        for command in READ_ONLY_OK:
            with self.subTest(ok=command):
                self.assertTrue(watchdog.is_read_only(command))
        for command in READ_ONLY_NO:
            with self.subTest(no=command):
                self.assertFalse(watchdog.is_read_only(command))


class PlanBlocks(unittest.TestCase):
    def test_w17_only_part_a_blocks(self):
        squash = load("agy_screen").squash
        self.assertEqual(watchdog.part_a_blocks(PLAN_TEXT), [
            squash("npx vitest run"),
            squash("cd /repo && git add -- a.ts && git commit -q -F - <<'MSG'\nfeat: deploy notes\nMSG"),
        ])

    def test_w19_decide(self):
        blocks = watchdog.part_a_blocks(PLAN_TEXT)
        rx = watchdog.deny_regex(r"\.env\b")
        self.assertEqual(watchdog.decide("npx vitest run", blocks, rx), ("approve", "plan"))
        self.assertEqual(watchdog.decide("git status --short", blocks, rx), ("approve", "read-only"))
        self.assertEqual(watchdog.decide("cat .env", blocks, rx), ("stop", "FORBIDDEN"))
        self.assertEqual(watchdog.decide("git push origin main", blocks, rx), ("stop", "OFF-PLAN"))
        self.assertEqual(watchdog.decide("npm install x", blocks, rx), ("stop", "OFF-PLAN"))
        self.assertEqual(watchdog.decide("npx vitest run && gi⋯", blocks, rx), ("stop", "TRUNCATED"))


class AgainstFakeHerdr(unittest.TestCase):
    def run_watchdog(self, screens, status, extra_deny=None, plan=PLAN_TEXT, args=None):
        env, state = fake_herdr_env(self, screens, status)
        env.update(GEMINI_ARCHITECT_IDLE_SECS="0.3", GEMINI_ARCHITECT_POLL_SECS="0.05")
        if extra_deny is not None:
            env["GEMINI_ARCHITECT_EXTRA_DENY"] = extra_deny
        log = state.with_name("watchdog.log")
        plan_file = state.with_name("plan.md")
        plan_file.write_text(plan, encoding="utf-8")
        argv = args if args is not None else [str(log), str(plan_file), "--agent", "gemini-exec"]
        r = subprocess.run([sys.executable, str(SCRIPTS / "watchdog.py"), *argv],
                           env=env, capture_output=True, text=True, timeout=20)
        keys = json.loads(state.read_text())["keys"]
        return r, keys, (log.read_text() if log.exists() else "")

    def test_w2_command_outside_the_plan_stops(self):
        r, keys, _ = self.run_watchdog([dialog("npx vitest run && git push origin main")], ["running"])
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stdout.startswith("OFF-PLAN:"))
        self.assertEqual(keys, [])

    def test_w3_truncated_command_stops(self):
        r, keys, _ = self.run_watchdog([dialog("npx vitest run && gi⋯")], ["running"])
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stdout.startswith("TRUNCATED:"))
        self.assertEqual(keys, [])

    def test_w4_plan_block_is_approved_then_idle_ends(self):
        r, keys, log = self.run_watchdog([dialog("npx vitest run"), "Done."], ["running", "idle"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(keys, ["enter"])
        self.assertIn("APPROVED #1 [plan]", log)
        self.assertIn("END:", log)

    def test_w4b_wrapped_plan_commit_block_is_approved(self):
        screen = dialog("cd /repo && git add -- a.ts && git commit -q -F -\n  <<'MSG' feat: deploy\n  notes MSG")
        r, keys, log = self.run_watchdog([screen, "Done."], ["running", "idle"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(keys, ["enter"])

    def test_w4c_part_b_block_is_not_approved(self):
        r, keys, _ = self.run_watchdog([dialog("git push origin main")], ["running"])
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stdout.startswith("OFF-PLAN:"))
        self.assertEqual(keys, [])

    def test_w5_blocked_agent_without_a_known_dialog(self):
        r, keys, _ = self.run_watchdog(["Something unexpected"], ["blocked"])
        self.assertEqual(r.returncode, 3)
        self.assertEqual(keys, [])

    def test_w6_extra_deny_vetoes_a_read_only_command(self):
        r, keys, _ = self.run_watchdog([dialog("cat .env")], ["running"], extra_deny=r"\.env\b")
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stdout.startswith("FORBIDDEN:"))
        self.assertEqual(keys, [])

    def test_w6b_read_only_command_is_approved(self):
        r, keys, log = self.run_watchdog([dialog("git status --short"), "Done."], ["running", "idle"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(keys, ["enter"])
        self.assertIn("[read-only]", log)

    def test_w7_invalid_extra_deny_is_a_setup_error(self):
        r, keys, _ = self.run_watchdog([dialog("ls")], ["running"], extra_deny="(")
        self.assertEqual(r.returncode, 1)
        self.assertIn("invalid GEMINI_ARCHITECT_EXTRA_DENY", r.stderr)
        self.assertEqual(keys, [])

    def test_w9_command_wrapped_mid_word_is_not_in_the_plan(self):
        r, keys, _ = self.run_watchdog([dialog("npx vitest run && git pu\n  sh origin main")], ["running"])
        self.assertEqual(r.returncode, 2)
        self.assertEqual(keys, [])

    def test_w12_ellipsis_truncated_command_stops(self):
        r, keys, _ = self.run_watchdog([dialog("npx vitest run && git pu…")], ["running"])
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stdout.startswith("TRUNCATED:"))
        self.assertEqual(keys, [])

    def test_w15_missing_plan_file_is_a_setup_error(self):
        r, keys, _ = self.run_watchdog([dialog("ls")], ["running"], args=["/tmp/x.log", "/nonexistent/plan.md"])
        self.assertEqual(r.returncode, 1)
        self.assertEqual(keys, [])

    def test_w16_no_plan_is_a_usage_error(self):
        r, keys, _ = self.run_watchdog([dialog("ls")], ["running"], args=["/tmp/x.log"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("usage:", r.stderr)
        self.assertEqual(keys, [])


if __name__ == "__main__":
    unittest.main()
