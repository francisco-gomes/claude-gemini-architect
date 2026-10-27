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

## Adding a watchdog pattern

1. Add the pattern to `BASE_DENY` in `skill/scripts/watchdog.py`.
2. Add the command to `FORBIDDEN` in `test/scripts/test_watchdog.py`, plus a similar command that must stay allowed (to `ALLOWED`) if the pattern could catch it.
3. `npm test`.

When unsure, block: a false positive only makes the watchdog stop and hand the decision to Claude.

Project-specific commands (your deploy tool, your release script) don't belong in the built-in list. Use `GEMINI_ARCHITECT_EXTRA_DENY`.

## Rules

- English everywhere except the pt-BR trigger phrases in the `SKILL.md` description.
- No private data (names of private projects, internal hosts, tokens, e-mails). CI checks it.
- No token-savings percentages without a published benchmark.
