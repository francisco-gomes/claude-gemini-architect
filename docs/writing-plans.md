# Writing plans

The plan is a contract. Gemini executes a precise script well; left to improvise, it loosens tests, overwrites files and miscounts. Each rule below exists because that happened.

## The rules and why

| Rule | Why |
|---|---|
| **C1** Touch only the listed files; names, cases and strings are copied letter by letter | stops "while I was there" edits and paraphrased test strings |
| **C2** Every command ends in `OK` or `FAILED` | the executor follows the last line instead of interpreting output |
| **C3** RED before code | a test that passes before the code exists tests nothing |
| **C4** GREEN failed → fix the code, never the contract; 3 attempts, then stop | the usual shortcut is weakening the test |
| **C4b** Production code never detects tests, never special-cases the examples | `NODE_ENV === 'test'` and lookup tables make tests pass and production fail |
| **C4c** CREATE on an existing file → stop | one name collision once replaced a file and deleted its tests |
| **C5** Never wait on or interrupt a background command | half-finished commands leave a confusing state |
| **C6** No push, PR, merge, deploy, SQL, `gh`, `curl`, `git add .` in Part A | Part A never leaves the machine |
| **C7** Stop after the last task | production needs your authorization, not Gemini's momentum |

Before writing **Create**, check that the file doesn't exist (`ls`, `git ls-files`). Before writing a path or a signature, read the code: a plan written from memory gets them wrong.

## A complete small example

The request: *add `slugify(text: string): string` to `src/text.ts`. `src/text.ts` exists (it exports `capitalize`), `test/text.test.ts` exists with 5 tests, and tests run with `npx vitest run`.*

```markdown
### Task 1: slugify

**Files:** Modify: `src/text.ts` (exists). Modify: `test/text.test.ts` (exists; keep the 5 `capitalize` tests unchanged).
**Interfaces (produces):** `export function slugify(text: string): string`, the same export style as `capitalize`.
**Behavior:** lowercase; strip accents; every run of characters outside `a-z0-9` becomes one `-`; no leading or trailing `-`; empty input returns `""`.

**Test contract** — `test/text.test.ts`, new `describe('slugify')`, one `it` per row, the name starts with the id:

| # | Input | Exact result |
|---|---|---|
| S1 | `"Hello World"` | `"hello-world"` |
| S2 | `"São Paulo"` | `"sao-paulo"` |
| S3 | `"  Hello   World  "` | `"hello-world"` |
| S4 | `"Hello, World!"` | `"hello-world"` |
| S5 | `"---foo---"` | `"foo"` |
| S6 | `""` | `""` |
| S7 | `"!!!"` | `""` |
| S8 | `"Top 10 Tips"` | `"top-10-tips"` |

- [ ] Step 1 (Gemini): write ONLY the tests.
- [ ] Step 2 (RED, must print OK):
      cd <repo> && timeout 300 npx vitest run test/text.test.ts > /tmp/pA_red.txt 2>&1; L=$(sed -E "s/\x1b\[[0-9;]*m//g" /tmp/pA_red.txt | grep -E "^ +Tests " | tail -1); echo "$L"; echo "$L" | grep -q "failed" && echo OK || echo FAILED
- [ ] Step 3 (Gemini): implement `slugify` in `src/text.ts` only.
- [ ] Step 4 (GREEN, whole suite, 13 tests):
      cd <repo> && timeout 300 npx vitest run > /tmp/pA_green.txt 2>&1; L=$(sed -E "s/\x1b\[[0-9;]*m//g" /tmp/pA_green.txt | grep -E "^ +Tests " | tail -1); echo "$L"; echo "$L" | grep -q "passed" && ! echo "$L" | grep -q "failed" && echo OK || echo FAILED
- [ ] Step 5: review the diff, then commit exactly `src/text.ts` and `test/text.test.ts`.
```

What makes it a contract:
- the table has exact inputs and outputs, accents included;
- both files are **Modify**, and the old tests are protected;
- every command judges itself;
- RED comes before the code;
- and there is **no implementation in the plan**. Code in the plan is Claude doing the work Gemini is there for.

The first instruction to Gemini is short, because the plan carries the detail:

```bash
agy -p "Plan docs/plans/2026-10-26-slugify.md, Task 1, Step 1: write ONLY the test cases S1–S8 (exact inputs and strings) in test/text.test.ts, in a new describe('slugify') block. Don't touch src/text.ts yet. Don't run commands; only edit. Reply with the list of files you changed." --mode accept-edits --output-format json
```

The full template, with blocks for vitest, jest, pytest, tsc, commit, PR CI, merge, main CI by SHA and counted SQL: [`skill/references/plan-template.md`](../skill/references/plan-template.md).
