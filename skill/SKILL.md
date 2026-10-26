---
name: claude-gemini-architect
description: Use when the user wants Gemini / Antigravity (`agy`) to write the code while Claude designs and reviews, to save Claude tokens on implementation work; when asked to run a plan or spec with Gemini or agy; or when the user says "/claude-gemini-architect", "let Gemini do the heavy lifting", "you design, agy executes", "coloca o gemini pra executar", "você projeta e o antigravity executa", "o gemini faz o pesado e você confere", "manda o agy fazer".
---

# Claude designs, Gemini builds, Claude reviews

**Goal: save Claude tokens.** Writing code, writing tests and fix loops are the expensive part; Gemini does them through `agy`. You spend tokens on two things: the plan (a contract) and the review of each diff.

## Roles

- **You:** the plan, running and judging commands Gemini can't run, the review, production steps.
- **Gemini:** all product code and tests, including the fixes your review finds (send them back with `--conversation <id>`).
- About to edit product code or tests yourself ("it's one line", "no time left")? **Ask the user first.** Telling them afterwards is not asking.

## Pick the mode

```bash
test "${HERDR_ENV:-}" = 1 && echo HERDR || echo TERMINAL
```

- TERMINAL → read `references/terminal-mode.md` (Gemini only edits; you run every command).
- HERDR → read `references/herdr-mode.md` (Gemini runs commands in a pane; each one is approved).

## The plan is a contract

Write it from `references/plan-template.md`. It is ready to send only when it has:

1. A test-case table with exact inputs and outputs.
2. Commands that end in a single `OK` or `FAILED` line.
3. RED before GREEN in every task.
4. Every file marked **Create** or **Modify**. Before writing Create, check the file doesn't exist.
5. Anti-shortcut rules: production code never detects it is under test; an existing test changes only when the new rule requires it, and is never weakened or deleted.
6. Part A (code) and Part B (production), with a mandatory stop between them.

The plan describes behavior, interfaces and tests. **It never contains the implementation**: code written in the plan is you doing the heavy lifting.

## Permissions

- Never `--dangerously-skip-permissions`.
- Never add allow rules to agy's settings, however narrow. Rules match by prefix: `npx vitest run*` also allows `npx vitest run && ./deploy.sh prod`. In headless mode the denial is the only control between Gemini and production.
- Gemini never commits. You commit after your review.
- User wants it faster? Offer herdr mode (Gemini runs its own commands, each one checked), several tasks per `agy` call (batch tasks, never phases: tests and code always go in separate calls), or keep going as is. Explain the prefix risk. A bypass is a change the user makes in their own settings, not one you make.

## Review every commit

Never trust Gemini's report: in headless mode it could not even run the tests. Follow `references/review-checklist.md` before each commit.

## Production (Part B)

Only after the user explicitly authorizes merge and deploy. One step at a time, verifying each result before the next. Never auto-approve a Part B command.

## Red flags

| Thought | Reality |
|---|---|
| "It's one line, I'll fix it myself" | Send it back to Gemini, or ask the user. |
| "A narrow allow rule is safe" | Prefix match: chained commands pass too. |
| "Let Gemini commit, I'll review after" | The review is the gate. It comes before the commit. |
| "I'll put a suggested implementation in the plan" | That's the work Gemini is there to do. |
| "Tests and code in one call saves a round" | The RED has to fail before the code exists. A RED rebuilt afterwards (stash, old copy) proves less. Batch tasks, not phases. |
| "Gemini says all tests pass" | Run them yourself. |
