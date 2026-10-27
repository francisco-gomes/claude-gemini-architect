"""A fake `herdr` executable for script tests: plays a list of screens and records the keys pressed."""
import json
import os
import shutil
import tempfile
from pathlib import Path

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


def fake_herdr_env(testcase, screens, status):
    """Create the fake herdr in a temp dir; return (env, state_path). The dir is removed after the test."""
    d = tempfile.mkdtemp()
    testcase.addCleanup(shutil.rmtree, d)
    herdr = Path(d, "herdr")
    herdr.write_text(FAKE_HERDR)
    herdr.chmod(0o755)
    state = Path(d, "state.json")
    state.write_text(json.dumps({"screens": screens, "status": status, "i": 0, "keys": []}))
    env = {**os.environ, "PATH": d + os.pathsep + os.environ["PATH"], "FAKE_HERDR_STATE": str(state),
           "PYTHONDONTWRITEBYTECODE": "1"}
    for key in ("GEMINI_ARCHITECT_EXTRA_DENY", "GEMINI_ARCHITECT_IDLE_SECS", "GEMINI_ARCHITECT_POLL_SECS",
                "GEMINI_ARCHITECT_WAIT_SECS"):
        env.pop(key, None)
    return env, state
