# Contributing

## Run the tests

```bash
npm test                               # installer (node:test) + scripts (unittest)
bash scripts/check-private.sh          # no private data in tracked files
bash scripts/check-private.sh --pack   # ...nor in the npm tarball
```

Requirements: Node 18+, Python 3. No dependencies to install.

## Changing the skill text

`skill/SKILL.md` and `skill/references/` were written test-first: a pressure scenario was run without the skill (RED), the text was written for the failures seen (GREEN), and loopholes were closed (REFACTOR). The scenarios, the rubric and every result are in `skill-tests/`.

A wording change should come with the scenario it fixes: run it without the change, run it with the change, and add both results to `skill-tests/results/`.

## Changing what the watchdog approves

The watchdog approves only commands identical to a bash block of the plan's Part A, and read-only commands (`is_read_only` in `skill/scripts/watchdog.py`). To allow another read-only command, add it to the allowed segments and add a row to `READ_ONLY_OK` in `test/scripts/test_watchdog.py`, plus a dangerous variant to `READ_ONLY_NO`. Then `npm test`.

When unsure, leave it out: an unknown command only makes the watchdog stop and hand the decision to Claude.

## Rules

- English everywhere except the pt-BR trigger phrases in the `SKILL.md` description.
- No private data (names of private projects, internal hosts, tokens, e-mails). CI checks it.
- No token-savings percentages without a published benchmark.
