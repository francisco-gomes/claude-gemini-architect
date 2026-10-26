# herdr mode (`HERDR_ENV=1`)

Gemini runs interactively in a herdr pane next to you (`agy --mode accept-edits`): file edits are accepted automatically, and **every terminal command asks for permission**. That prompt is where you stay in control.

## Setup

- Check the panes: `herdr pane list`, `herdr agent list`.
- Start the executor once per session:
  ```bash
  herdr pane split --current --direction right --cwd <repo> --no-focus
  herdr agent start gemini-exec --kind agy --pane <new-pane-id> -- --mode accept-edits
  ```
- Claude Code permissions needed in `~/.claude/settings.json`: `Bash(herdr agent start:*)`, `Bash(herdr agent prompt:*)`, and the `read`, `get`, `wait`, `send-keys`, `list` agent subcommands, plus `Bash(herdr pane list:*)`, `Bash(herdr pane read:*)`, `Bash(herdr pane layout:*)`.
- Before each new plan: `herdr agent prompt gemini-exec "/clear" --wait --timeout 30000`.

## Part A

- Start the watchdog **inside Monitor**: `python3 <skill-dir>/scripts/watchdog.py <log-file> gemini-exec`. It approves safe commands on its own and **stops** on push, merge, docker, database, `rm -r`, package installs, `git checkout --` / `restore` / `stash`. Add project-specific patterns with `GEMINI_ARCHITECT_EXTRA_DENY='<regex>'`. Exit codes: 0 Gemini finished, 2 forbidden command, 3 unknown dialog.
- Send the instruction: `"Execute PART A of the plan <path>, from 'Before you start' to the end of Task N. You write the code and the tests; follow C1–C7 (especially C4b and C4c). When done, STOP and write the report."`
- **Monitor expires after 30 minutes and the watchdog dies with it.** If Gemini is still working when the expiry notice arrives, restart it right away. Never run two watchdogs at once.
- Stopped on a forbidden command: read what Gemini asked for. If it is legitimate and narrow (undoing a file it touched outside the list), approve just that one with `herdr agent send-keys gemini-exec enter` and restart the watchdog. Otherwise send `esc` and correct it with an instruction.
- Review **commit by commit**: wait in the background (`until` loop on `git rev-list --count origin/main..HEAD`, or `STOPPED|END` in the watchdog log) and review each commit as soon as it lands. An error caught early doesn't contaminate the next tasks.

## Part B — manual approval, one by one

Never use the watchdog in Part B. Only after the user explicitly authorizes merge and deploy.

- `python3 <skill-dir>/scripts/extract_blocks.py <plan> <blocks.json>`, then tell Gemini to execute Part B.
- Loop: `python3 <skill-dir>/scripts/next_block.py <blocks.json>` (says which block Bn Gemini is asking to run) → **check the previous step's result yourself** (`/tmp/<P>_*` files, service status, `gh pr checks`, logs, database) → `herdr agent send-keys gemini-exec enter`.
- `OFF-SCRIPT` request: approve only harmless reads (`git log`); otherwise `esc`.
- The "last OK/FAILED" line from `next_block.py` can show a **false FAILED** (the `|| echo FAILED` text of the command itself, wrapped on screen). The real output of the step decides.
- Before the merge, look at `gh pr checks` yourself. Before any SQL that writes, run the read-only query and see the exact rows.
- A Bash call times out at 10 minutes; CI and deploy waits can take longer. Use the background or check the state directly.

## Gotchas

- herdr shows the agent `idle` even with a permission dialog open; look at the screen (`herdr agent read gemini-exec --source visible`).
- Gemini sometimes runs extra `git log` / `git status`; reads are fine.
- A Monitor pipeline with `| sed | cut` and no flushing delivers no events. Use `grep --line-buffered` / `sed -u` and avoid `cut` at the end.
