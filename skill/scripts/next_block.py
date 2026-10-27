#!/usr/bin/env python3
"""PART B (production): waits for Gemini's next permission request (or for it to stop) and says which block
of the script it is. It NEVER approves anything: the architect approves with
`herdr agent send-keys <agent> enter` after checking the previous step.

Usage: python3 next_block.py <blocks.json> [agent-name]   (blocks.json comes from extract_blocks.py)
Output: "REQUEST: B3" | "REQUEST: B3|B4 (truncated, ambiguous)" | "REQUEST: OFF-SCRIPT: ..." |
        "GEMINI STOPPED (no pending request)", then "last OK/FAILED: [...]".
WARNING: "last OK/FAILED" can show a false FAILED (the `|| echo FAILED` text of the command itself, wrapped on
screen). The real output of the step (/tmp/<prefix>_* files) decides.
Exit codes: 0 done, 1 herdr not found, 2 wrong usage."""
import json
import re
import shutil
import sys
import time

from agy_screen import REQ_END, agent_status, is_truncated, pending_request, read_screen, squash


def match_blocks(request, blocks):
    """Indexes of the (squashed) blocks the request can be. A truncated request matches by prefix."""
    truncated = is_truncated(request)
    first_ellipsis = re.split(r"[⋯…]", request)[0]
    visible = squash(first_ellipsis)
    if truncated:
        visible = visible.rstrip(".")
    if not visible:
        return []
    return [i for i, b in enumerate(blocks) if visible == b or (truncated and b.startswith(visible))]


def describe(request, blocks):
    found = match_blocks(request, blocks)
    if len(found) == 1:
        return f"REQUEST: B{found[0]}"
    if found:
        return "REQUEST: " + "|".join(f"B{i}" for i in found) + " (truncated, ambiguous)"
    return "REQUEST: OFF-SCRIPT: " + " ".join(request.split())[:300]


def looks_idle(status, screen):
    return (status in ("idle", "done") and "esc to interrupt" not in screen.lower()
            and "running" not in screen and REQ_END not in screen)


def gemini_stopped(agent, screen):
    if not looks_idle(agent_status(agent), screen):
        return False
    time.sleep(8)
    return looks_idle(agent_status(agent), read_screen(agent, "visible", 80))


def main(argv):
    if len(argv) not in (2, 3):
        print("usage: python3 next_block.py <blocks.json> [agent-name]", file=sys.stderr)
        return 2
    if shutil.which("herdr") is None:
        print("error: herdr not found in PATH", file=sys.stderr)
        return 1
    with open(argv[1], encoding="utf-8") as f:
        blocks = [squash(b) for b in json.load(f)]
    agent = argv[2] if len(argv) == 3 else "gemini-exec"
    time.sleep(6)
    for _ in range(400):
        screen = read_screen(agent, "visible", 80)
        request = pending_request(screen)
        if request is not None:
            print(describe(request, blocks))
            break
        if gemini_stopped(agent, screen):
            print("GEMINI STOPPED (no pending request)")
            break
        time.sleep(4)
    recent = read_screen(agent, "recent-unwrapped", 60)
    print("last OK/FAILED:", re.findall(r"^\s*(OK|FAILED)\s*$", recent, re.M)[-3:])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
