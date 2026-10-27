"""Tests for skill/scripts/watchdog.py (unit tests + runs against a fake herdr)."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

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
]
ALLOWED = [
    "npx vitest run test/deploy.test.ts", "npx vitest run test/migration.test.ts", "git status --short",
    "git add -- src/a.ts", "git commit -q -F -", "npx tsc --noEmit", "git --no-pager log --oneline -1",
    "python3 -m pytest -q", "npm init -y",
    "git -C /repo status --short", "git --no-pager diff --stat", "rm -f /tmp/cga_x.txt", "find . -name '*.py'",
    "npm run lint", "nvm ls", "node --version",
]

FAKE_HERDR = '''#!/usr/bin/env python3
import json, os, sys
path = os.environ["FAKE_HERDR_STATE"]
with open(path) as f:
    state = json.load(f)
args = sys.argv[1:]
if args[:2] == ["agent", "read"]:
    print(state["screens"][state["i"]])
elif args[:2] == ["agent", "get"]:
    print(json.dumps({"result": {"agent": {"agent_status": state["status"][state["i"]]}}}))
elif args[:2] == ["agent", "send-keys"]:
    state["keys"].append(args[3])
    state["i"] = min(state["i"] + 1, len(state["screens"]) - 1)
    with open(path, "w") as f:
        json.dump(state, f)
'''


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


class AgainstFakeHerdr(unittest.TestCase):
    def run_watchdog(self, screens, status, extra_deny=None):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d)
        herdr = Path(d, "herdr")
        herdr.write_text(FAKE_HERDR)
        herdr.chmod(0o755)
        state = Path(d, "state.json")
        state.write_text(json.dumps({"screens": screens, "status": status, "i": 0, "keys": []}))
        log = Path(d, "watchdog.log")
        env = {**os.environ, "PATH": d + os.pathsep + os.environ["PATH"], "FAKE_HERDR_STATE": str(state),
               "GEMINI_ARCHITECT_IDLE_SECS": "0.3", "GEMINI_ARCHITECT_POLL_SECS": "0.05",
               "PYTHONDONTWRITEBYTECODE": "1"}
        env.pop("GEMINI_ARCHITECT_EXTRA_DENY", None)
        if extra_deny is not None:
            env["GEMINI_ARCHITECT_EXTRA_DENY"] = extra_deny
        r = subprocess.run([sys.executable, str(SCRIPTS / "watchdog.py"), str(log), "gemini-exec"],
                           env=env, capture_output=True, text=True, timeout=20)
        keys = json.loads(state.read_text())["keys"]
        return r, keys, (log.read_text() if log.exists() else "")

    def test_w2_chained_forbidden_command_stops_without_pressing(self):
        r, keys, _ = self.run_watchdog([dialog("npx vitest run && git push origin main")], ["running"])
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stdout.startswith("FORBIDDEN:"))
        self.assertEqual(keys, [])

    def test_w3_truncated_command_stops_without_pressing(self):
        r, keys, _ = self.run_watchdog([dialog("npx vitest run && gi⋯")], ["running"])
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stdout.startswith("TRUNCATED:"))
        self.assertEqual(keys, [])

    def test_w4_safe_command_is_approved_then_idle_ends(self):
        r, keys, log = self.run_watchdog([dialog("npx vitest run"), "Done."], ["running", "idle"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(keys, ["enter"])
        self.assertIn("APPROVED #1", log)
        self.assertIn("END:", log)

    def test_w5_blocked_agent_without_a_known_dialog(self):
        r, keys, _ = self.run_watchdog(["Something unexpected"], ["blocked"])
        self.assertEqual(r.returncode, 3)
        self.assertEqual(keys, [])

    def test_w6_extra_deny_pattern_stops(self):
        r, keys, _ = self.run_watchdog([dialog("make release")], ["running"], extra_deny=r"make\s+release")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(keys, [])

    def test_w7_invalid_extra_deny_is_a_setup_error(self):
        r, keys, _ = self.run_watchdog([dialog("ls")], ["running"], extra_deny="(")
        self.assertEqual(r.returncode, 1)
        self.assertIn("invalid GEMINI_ARCHITECT_EXTRA_DENY", r.stderr)
        self.assertEqual(keys, [])

    def test_w9_command_wrapped_mid_word_is_still_caught(self):
        r, keys, _ = self.run_watchdog([dialog("npx vitest run && git pu\n  sh origin main")], ["running"])
        self.assertEqual(r.returncode, 2)
        self.assertEqual(keys, [])


if __name__ == "__main__":
    unittest.main()
