"""Shared helpers: read a herdr pane and the agy permission dialog shown in it."""
import json
import re
import subprocess

REQ_START = "Requesting permission for:"
REQ_END = "Run this command?"


def sh(*args):
    return subprocess.run(args, capture_output=True, text=True).stdout


def read_screen(agent, source="visible", lines=60):
    return sh("herdr", "agent", "read", agent, "--source", source, "--lines", str(lines))


def agent_status(agent):
    try:
        return json.loads(sh("herdr", "agent", "get", agent))["result"]["agent"]["agent_status"]
    except (ValueError, KeyError, TypeError):
        return "?"


def press(agent, key):
    sh("herdr", "agent", "send-keys", agent, key)


def pending_request(screen):
    """The command text of an open permission dialog, or None when there is no dialog."""
    if REQ_START in screen and REQ_END in screen:
        return screen.split(REQ_START)[-1].split(REQ_END)[0]
    return None


def squash(text):
    return re.sub(r"\s", "", text)


def is_truncated(request):
    """True when the dialog shows only part of the command, so it can't be checked."""
    return "⋯" in request or request.strip().endswith("…") or squash(request).endswith("....")
