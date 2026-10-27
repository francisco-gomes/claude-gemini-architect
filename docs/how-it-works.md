# How it works

## Roles

| | Claude: architect and reviewer | Gemini via `agy`: executor |
|---|---|---|
| Writes | the plan | all product code and tests, including the fixes the review finds |
| Runs | in terminal mode, every command (headless `agy` can't); the review; production steps | in herdr mode, the plan's commands, each one checked |
| Never | edits product code without asking you | starts production on its own |

## The phases

1. **Design.** Claude reads the code (and production data, when it's an incident) and writes the plan from [`skill/references/plan-template.md`](../skill/references/plan-template.md): design decisions, review focus, rules C1–C7, and tasks with exact test tables and commands that end in `OK` or `FAILED`. The plan is committed on a feature branch before Gemini sees it.
2. **Part A: code.** For each task: Gemini writes the tests → **RED**, the tests must fail → Gemini writes the code → **GREEN**, the tests must pass → Claude reviews the diff → commit. A finding from the review goes back to Gemini as a correction with its own contract.
3. **Mandatory stop.** Claude reports what was done and proven. You decide about production.
4. **Part B: production.** Only after your explicit authorization. One step at a time, each result checked before the next: the PR's CI before the merge, a read-only query before any SQL that writes.
5. **Closing.** Confirm in production with real data, then report what was proven and what wasn't yet (no traffic means not proven).

## Where the tokens go

| Work | Who pays |
|---|---|
| Reading the code, writing the plan | Claude |
| Writing tests and code, fix loops | Gemini |
| Running the commands (terminal mode) | Claude, but only one summary line per command: the blocks write the full output to `/tmp` and print a single line |
| Review | Claude, reading `git show --stat` and the diff, not whole files |

Ways to save more:

- Send Gemini only the plan's path, not its content.
- On a failing test, send back only the error lines.
- Read only the fields you need from agy's JSON (`jq '{status, response, conversation_id, denied_actions}'`).
- Start a new agy conversation for each plan.
- Batch small independent tasks into one call (tests first for all of them, then the code for all of them), never a task's tests and code together.

## The helper scripts (herdr mode)

| Script | What it does | Exit codes |
|---|---|---|
| `python3 scripts/watchdog.py <log> <plan.md> [--agent name]` | Part A only. Approves commands identical to a bash block of the plan's PART A, and read-only commands; everything else stops it. Log lines: `APPROVED #n [plan]` / `[read-only]`, `STOPPED: …`, `END: …`. | 0 finished, 1 setup error, 2 off-plan/forbidden/truncated, 3 unknown dialog |
| `python3 scripts/extract_blocks.py <plan.md> <blocks.json>` | Saves the bash blocks of the plan's `# PART B` as B0, B1… | 0 written, 1 no Part B or no block, 2 usage |
| `python3 scripts/next_block.py <blocks.json> [agent]` | Part B. Waits for Gemini's next request and says which block it is: `REQUEST: B3`, `REQUEST: OFF-SCRIPT: …` or `GEMINI STOPPED`. **Never approves anything.** | 0 done, 1 herdr missing, 2 usage |

Configuration: `GEMINI_ARCHITECT_EXTRA_DENY` (extra regex for the watchdog), `GEMINI_ARCHITECT_IDLE_SECS` (watchdog, default 45), `GEMINI_ARCHITECT_POLL_SECS` (watchdog default 3, next_block default 4) and `GEMINI_ARCHITECT_WAIT_SECS` (next_block, default 540: it prints `NO REQUEST YET` and you run it again).

## The review

Every commit, before it counts: scope (only the task's files?), tests run by Claude, the diff read against the contract, a grep for code that detects tests, justified changes to old tests, a few edge cases. The full checklist is in [`skill/references/review-checklist.md`](../skill/references/review-checklist.md).
