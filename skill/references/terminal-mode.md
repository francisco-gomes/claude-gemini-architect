# Terminal mode (no herdr)

Gemini runs headless with `agy -p`. It can edit files; **every terminal command it tries is denied** and listed in `denied_actions`. So Gemini writes, and you run the plan's commands.

## Setup

- `command -v agy` and `agy models` (lists models only when logged in).
- Every call runs **from the repo root** and returns JSON:
  ```bash
  cd <repo> && agy -p "<instruction>" --mode accept-edits --print-timeout 900s --output-format json > <scratchpad>/agy_<step>.json
  ```
  Fields: `status` (`SUCCESS`), `response`, `conversation_id`, `denied_actions` (normal in this mode), `usage`.
- Continue the same conversation with `--conversation <conversation_id>`; that is how a failing test goes back to Gemini. Start a new conversation for each plan.
- Calls take minutes: run them in the background and read the JSON when they finish. Read only the fields you need (`jq '{status, response, conversation_id, denied_actions}'`) to save tokens.

## Part A, for each task

1. `agy -p "Plan <path>, Task N: write ONLY the TEST files of the contract (exact cases and strings). Don't run commands; only edit. Don't overwrite an existing file unless the plan says Modify. Reply with the list of files you created or changed."` Keep the `conversation_id`.
2. **You** run the RED block. It must print `OK` (tests fail). If the tests pass, they test nothing: send that back to Gemini.
3. Same conversation: `"Now implement the production code for Task N (rules C1, C4b, C4c of the plan). Only edit. Reply with the list of files."`
4. **You** run the GREEN block. `FAILED`: send only the relevant error lines in the same conversation: `"GREEN failed with: <error>. Fix the production code, not the test."` Up to 3 rounds; on the 4th, stop and re-plan.
5. `git status --short`: only the task's files? Review the diff (`review-checklist.md`) **before** committing.
6. **You** run the commit block.

A finding from your review goes back the same way: an instruction with a contract (files, change, new test case) in the same conversation, then you rerun the commands.

## Going faster without opening permissions

- Send two or three small, independent tasks in one call, each with its own test files, then run their RED/GREEN blocks in sequence.
- Switch to herdr mode, where Gemini runs its own commands and each one passes the watchdog or your approval.
- Don't add allow rules to agy's settings: they match by prefix, so `npx vitest run*` also lets through `npx vitest run && <anything>`.

## Part B

There is no code to write in Part B, and `agy -p` can't run commands without opening permissions. So **you** run the script, one block at a time, exactly as in the plan, checking each result before the next (PR CI before merge, a read-only query before any SQL that writes). Only after the user explicitly authorizes merge and deploy. Tell the user that in this mode you ran Part B yourself.
