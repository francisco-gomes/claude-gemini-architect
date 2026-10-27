#!/usr/bin/env python3
"""PART A watchdog (code only): approves the safe commands Gemini (agy) asks to run in a herdr pane and
STOPS at the first forbidden one (push, merge, deploy, migrations, docker, databases, rm -r, installs...).

Usage: python3 watchdog.py <log-file> [agent-name]   (default agent: gemini-exec)
GEMINI_ARCHITECT_EXTRA_DENY='<regex>' adds project-specific patterns (case-insensitive) to the built-in list.
Exit codes: 0 agent idle long enough (finished), 1 setup or usage error, 2 forbidden or truncated command,
3 unknown dialog.
NEVER use it in PART B (production): there every command is approved by hand after checking the script.
Run it inside Monitor (it expires after 30 min; restart it if Gemini is still working)."""
import os
import re
import shutil
import sys
import time

from agy_screen import agent_status, is_truncated, pending_request, press, read_screen, squash

BASE_DENY = (
    r"\bgit\s+(?:[^\s;&|]+\s+)*(?:push|merge|rebase|reset|clean|branch\s+-D|stash|restore|switch\b|checkout\s+--(?:\s|$))"
    r"|\bgh\s|docker|podman|kubectl|\bssh\s|\bscp\s|\brsync\s"
    r"|psql|mysql|mongosh?\b|redis-cli|sqlite3"
    r"|\bmigrat(?:e|ions?)\b(?!\.(?:test|spec)\b)"
    r"|(?:\b|/)deploy(?!\.(?:test|spec)\b)(?:[:;\"'\s-]|\.sh|$)"
    r"|\brm\s+(?:-[^\s;&|]+\s+)*(-[a-zA-Z]*r[a-zA-Z]*|--recursive)\b"
    r"|\bfind\s+.*?\s+-delete\b|--force(\s|$)"
    r"|\bcurl\s|\bwget\s"
    r"|\b(npm|pnpm|yarn|bun|pip3?|uv|cargo)\s+(install|add|i|uninstall|remove)\b"
    r"|\b(?:nvm|fnm)\s+(?:install|use|alias|uninstall)\b"
    r"|\bvolta\s+(?:install|pin)\b"
    r"|\b(?:asdf|pyenv)\s+(?:install|global|local)\b"
    r"|(?:^|[;&|])\s*n\s+(?:\d+|lts|latest)\b"
    r"|\bsudo\b|\bkill\b|pkill"
)


def deny_regex(extra=None):
    """The built-in deny list plus `extra` (a regex) when given. Raises re.error for an invalid `extra`."""
    pattern = BASE_DENY if not extra else f"(?:{BASE_DENY})|(?:{extra})"
    return re.compile(pattern, re.I)


def variants(request):
    """The request with screen lines joined by a space and by nothing (a wrap can split a word)."""
    lines = [line.strip() for line in request.splitlines() if line.strip()]
    return " ".join(lines), "".join(lines)


def is_forbidden(request, rx):
    return any(rx.search(v) for v in variants(request))


def log(path, message):
    with open(path, "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + message + "\n")


def main(argv):
    if len(argv) not in (2, 3):
        print("usage: python3 watchdog.py <log-file> [agent-name]", file=sys.stderr)
        return 1
    if shutil.which("herdr") is None:
        print("error: herdr not found in PATH (the watchdog only works in herdr mode)", file=sys.stderr)
        return 1
    try:
        rx = deny_regex(os.environ.get("GEMINI_ARCHITECT_EXTRA_DENY"))
    except re.error as e:
        print(f"error: invalid GEMINI_ARCHITECT_EXTRA_DENY: {e}", file=sys.stderr)
        return 1
    log_path = argv[1]
    agent = argv[2] if len(argv) == 3 else "gemini-exec"
    idle_secs = float(os.environ.get("GEMINI_ARCHITECT_IDLE_SECS", "45"))
    poll = float(os.environ.get("GEMINI_ARCHITECT_POLL_SECS", "3"))
    approved = 0
    idle_since = None
    while True:
        screen = read_screen(agent)
        request = pending_request(screen)
        if request is not None:
            command = " ".join(request.split())
            if is_truncated(request):
                log(log_path, f"STOPPED: truncated command, cannot check it -> {command}")
                print(f"TRUNCATED: {command[:300]}", flush=True)
                return 2
            if is_forbidden(request, rx):
                log(log_path, f"STOPPED: forbidden command requested -> {command}")
                print(f"FORBIDDEN: {command[:300]}", flush=True)
                return 2
            approved += 1
            log(log_path, f"APPROVED #{approved}: {command[:400]}")
            if approved % 10 == 0:
                print(f"{approved} commands approved", flush=True)
            press(agent, "enter")
            time.sleep(poll * 4 / 3)
            idle_since = None
            continue
        status = agent_status(agent)
        if status in ("idle", "done"):
            idle_since = idle_since or time.monotonic()
            if time.monotonic() - idle_since > idle_secs and "esc to interrupt" not in screen.lower():
                log(log_path, f"END: agent idle ({status}) after {approved} approvals")
                return 0
        elif status == "blocked":
            log(log_path, "STOPPED: agent blocked on an unrecognized dialog")
            log(log_path, screen[-2000:])
            return 3
        else:
            idle_since = None
        time.sleep(poll)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
