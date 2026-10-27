#!/usr/bin/env python3
"""PART A watchdog (code only): approves only bash blocks of the plan's PART A and read-only commands;
stops at any other command (push, installs, commands outside the plan, forbidden or truncated commands).

Usage: python3 watchdog.py <log-file> <plan.md> [<plan.md> ...] [--agent <name>]   (default agent: gemini-exec)
GEMINI_ARCHITECT_EXTRA_DENY='<regex>' adds project-specific patterns (case-insensitive) to veto even read-only commands.
Exit codes: 0 agent idle long enough (finished), 1 setup or usage error, 2 command outside the plan, forbidden or truncated,
3 unknown dialog.
NEVER use it in PART B (production): there every command is approved by hand after checking the script.
Run it inside Monitor (it expires after 30 min; restart it if Gemini is still working)."""
import os
import re
import shutil
import sys
import time

from agy_screen import agent_status, is_truncated, pending_request, press, read_screen, squash

PART_B = re.compile(r"^# PART B\b", re.M)
BASH_BLOCK = re.compile(r"```bash[ \t]*\n(.*?)```", re.S)

GIT_OPTS = (
    r"(?:(?:-C|-c|--git-dir|--work-tree|--namespace)(?:=[^\s;&|]+|\s+[^\s;&|]+)"
    r"|--no-pager|-P|--bare|--no-replace-objects|--literal-pathspecs)"
)

BASE_DENY = (
    rf"\bgit\s+(?:{GIT_OPTS}\s+)*(?:push|merge|rebase|reset|clean|branch\s+-D|stash|restore|switch\b|checkout\s+(?:[^;&|]*?\s)?(--|\.)(?:\s|$))"
    r"|\bgh\s|docker|podman|kubectl|\bssh\s|\bscp\s|\brsync\s"
    r"|psql|mysql|mongosh?\b|redis-cli|sqlite3"
    r"|\bmigrat(?:e|ions?)\b(?!\.(?:test|spec)\b)"
    r"|\bdeploy(?!\.(?:test|spec)\b)(?!ments?\b)"
    r"|\brm\b[^;&|]*?\s(-[a-zA-Z]*r[a-zA-Z]*|--recursive)\b"
    r"|\bfind\s+.*?\s+-delete\b|--force(\s|$)"
    r"|\bcurl\s|\bwget\s"
    r"|\b(npm|pnpm|yarn|bun|pip3?|uv|cargo)\s+(install|add|i|uninstall|remove)\b"
    r"|\b(?:nvm|fnm)\s+(?:install|use|alias|uninstall)\b"
    r"|\bvolta\s+(?:install|pin)\b"
    r"|\b(?:asdf|pyenv)\s+(?:install|global|local)\b"
    r"|(?:^|[;&|\n])\s*n\s+(?:\d+|lts|latest|stable|current|auto|engine|install|i|use|run|exec|rm|prune|uninstall)\b"
    r"|\bsudo\b|\bkill\b|pkill"
)

SIMPLE_READ_ONLY = {
    "cd", "cat", "head", "wc", "ls", "pwd", "echo",
    "grep", "test", "true", "stat", "cut", "tr", "diff", "which",
}

FORBIDDEN_FIND = {
    "-delete", "-exec", "-execdir", "-ok", "-okdir",
    "-fprint", "-fprint0", "-fprintf", "-fls",
}

GIT_READ_ONLY = {
    "status", "log", "diff", "show", "rev-parse", "ls-files", "rev-list",
}


def deny_regex(extra=None):
    """The built-in deny list plus `extra` (a regex) when given. Raises re.error for an invalid `extra`."""
    pattern = BASE_DENY if not extra else f"(?:{BASE_DENY})|(?:{extra})"
    return re.compile(pattern, re.I | re.M)


def variants(request):
    """The request with screen lines joined by a space and by nothing (a wrap can split a word)."""
    lines = [line.strip() for line in request.splitlines() if line.strip()]
    return " ".join(lines), "".join(lines)


def is_forbidden(request, rx):
    return any(rx.search(v) for v in (request, *variants(request)))


def part_a_blocks(text):
    heading = PART_B.search(text)
    part_a = text[:heading.start()] if heading else text
    return [" ".join(b.split()) for b in BASH_BLOCK.findall(part_a)]


def is_segment_allowed(seg):
    if any(c in seg for c in ("'", '"', "\\", "$", "`")):
        return False
    tokens = seg.split()
    if not tokens:
        return False
    first = tokens[0]
    if first in SIMPLE_READ_ONLY:
        return True
    if first == "tail":
        return not any(t in ("-f", "-F") or t.startswith("--follow") for t in tokens[1:])
    if first == "command":
        return len(tokens) >= 2 and tokens[1] == "-v"
    if first == "node":
        return tokens[1:] in (["--version"], ["-v"])
    if first == "python3":
        return tokens[1:] == ["--version"]
    if first == "find":
        return not any(t in FORBIDDEN_FIND for t in tokens[1:])
    if first == "git":
        if any(t.startswith("--output") or t.startswith("--ext-diff") for t in tokens[1:]):
            return False
        idx = 1
        if idx < len(tokens) and tokens[idx] == "--no-pager":
            idx += 1
        if idx >= len(tokens):
            return False
        sub = tokens[idx]
        if sub in GIT_READ_ONLY:
            return True
        if sub == "branch" and tokens[idx:] == ["branch", "--show-current"]:
            return True
        return False
    return False


def is_read_only(command):
    if any(bad in command for bad in ("$(", "`", "<<", "<(")):
        return False
    cleaned = command.strip()
    cleaned = re.sub(r"(?:2>&1|2>/dev/null|>\s*/dev/null)(?=\s|$)", " ", cleaned)
    if ">" in cleaned:
        return False
    segments = [s.strip() for s in re.split(r"&&|\|\||[;&|\n]", cleaned)]
    if not segments or any(not s for s in segments):
        return False
    return all(is_segment_allowed(s) for s in segments)


def decide(request, plan_blocks, rx):
    if is_truncated(request):
        return ("stop", "TRUNCATED")
    if " ".join(request.split()) in plan_blocks:
        return ("approve", "plan")
    if is_read_only(request):
        if not is_forbidden(request, rx):
            return ("approve", "read-only")
        else:
            return ("stop", "FORBIDDEN")
    return ("stop", "OFF-PLAN")


def log(path, message):
    with open(path, "a", encoding="utf-8") as f:
        f.write(time.strftime("%H:%M:%S ") + message + "\n")


def parse_args(argv):
    agent = "gemini-exec"
    positional = []
    i = 1
    while i < len(argv):
        arg = argv[i]
        if arg == "--agent":
            if i + 1 >= len(argv):
                return None, None, None, "usage: python3 watchdog.py <log-file> <plan.md> [<plan.md> ...] [--agent <name>]"
            agent = argv[i + 1]
            i += 2
        elif arg.startswith("--agent="):
            agent = arg.split("=", 1)[1]
            i += 1
        elif arg.startswith("-"):
            return None, None, None, "usage: python3 watchdog.py <log-file> <plan.md> [<plan.md> ...] [--agent <name>]"
        else:
            positional.append(arg)
            i += 1
    if len(positional) < 2:
        return None, None, None, "usage: python3 watchdog.py <log-file> <plan.md> [<plan.md> ...] [--agent <name>]"
    return positional[0], positional[1:], agent, None


def main(argv):
    log_path, plan_paths, agent, err = parse_args(argv)
    if err:
        print(err, file=sys.stderr)
        return 1
    if shutil.which("herdr") is None:
        print("error: herdr not found in PATH (the watchdog only works in herdr mode)", file=sys.stderr)
        return 1
    try:
        rx = deny_regex(os.environ.get("GEMINI_ARCHITECT_EXTRA_DENY"))
    except re.error as e:
        print(f"error: invalid GEMINI_ARCHITECT_EXTRA_DENY: {e}", file=sys.stderr)
        return 1
    plan_blocks = []
    for p in plan_paths:
        if not os.path.isfile(p):
            print(f"error: plan file not found: {p}", file=sys.stderr)
            return 1
        with open(p, encoding="utf-8") as f:
            plan_blocks.extend(part_a_blocks(f.read()))

    idle_secs = float(os.environ.get("GEMINI_ARCHITECT_IDLE_SECS", "45"))
    poll = float(os.environ.get("GEMINI_ARCHITECT_POLL_SECS", "3"))
    approved = 0
    idle_since = None
    while True:
        screen = read_screen(agent)
        request = pending_request(screen)
        if request is not None:
            command = " ".join(request.split())
            action, reason = decide(request, plan_blocks, rx)
            if action == "approve":
                approved += 1
                log(log_path, f"APPROVED #{approved} [{reason}]: {command[:400]}")
                if approved % 10 == 0:
                    print(f"{approved} commands approved", flush=True)
                press(agent, "enter")
                time.sleep(poll * 4 / 3)
                idle_since = None
                continue
            else:
                log(log_path, f"STOPPED: {reason} -> {command}")
                print(f"{reason}: {command[:300]}", flush=True)
                return 2
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
