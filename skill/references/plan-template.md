# Plan template

Save the plan as `docs/plans/YYYY-MM-DD-<name>.md` and commit it on the feature branch before sending it to Gemini. Replace `<P>` with a short plan prefix (`pA`, `pB`…): it keeps each plan's `/tmp/<P>_*` output files apart.

Read the code before writing the plan. A plan written from memory gets paths, signatures and names wrong.

---

````markdown
# <Title> — <what changes, in one line>

> **For the executor (Gemini):** you write the code and the tests; this plan is the contract. Read
> **RULES** first. Every command ends in a line `OK` or `FAILED`.

**Goal:** <one sentence>
**Architecture:** <2–4 sentences: which part changes where>
**Stack:** <languages, test runner>

## Design decisions (by the architect)
1. <everything the request left open and you decided — the user reads this before approving>

## Review focus
- <the 3–5 inputs most likely to break, each pointing at the test case that covers it>

## RULES
### C1. The plan is the contract.
Create and modify **only** the files listed in each task. Function names, test cases and exact strings are
contract: copy them letter by letter.
### C2. Every command ends in `OK` or `FAILED`. Run each `bash` block exactly as written.
### C3. RED before code: the new test must fail first (the RED block prints `OK` when it fails as expected).
### C4. GREEN prints `FAILED`: fix the production code, never the contract.
Read `/tmp/<P>_<step>.txt`, fix, run again. Up to 3 attempts per step; on the 4th, **STOP** and report. Never
change a contract test case; never delete a test the plan doesn't tell you to delete. To undo your own
change, rewrite the file with the editor (no `git checkout` / `git restore`).
### C4b. Production code NEVER detects that it is under test.
No `NODE_ENV === 'test'`, `process.env.VITEST`, `expect.getState()`, `currentTestName`, `_isMockFunction`,
`PYTEST_CURRENT_TEST`, `'pytest' in sys.modules`, and no special-casing of the contract's example inputs
(implement the general rule). An **existing** test that conflicts with the new rule:
update its assertion to the new rule and include that file in the commit.
### C4c. Never overwrite an existing file when the plan says CREATE — STOP and report.
### C5. Never wait on a background command and never interrupt a running one.
### C6. Forbidden in Part A: push, PR, merge, deploy, `docker`, SQL, `gh`, `curl`, `git add .`, installing packages.
### C7. After the last task, STOP and write the report. Never start Part B on your own.

**Before you start:**
```bash
cd <repo> && git checkout -q <branch> && git --no-pager log --oneline -1 && test -z "$(git status --short | grep -v '^?? docs/')" && echo OK || echo FAILED
```

## Context for someone with no history
<the problem, with data; "where things live": file → responsibility>

# PART A — code (no production)

### Task N: <what it delivers>
**Files:** Create: … (checked: does not exist) / Modify: …
**Interfaces (produces):** <exact signatures, types, constants, strings>
**Behavior:** <one rule per line>
**Test contract** — <test file>:
| # | Input / scenario | Exact result |
|---|---|---|
| N1 | … | … |

- [ ] Step 1: write the tests (one case per test, name starting with its id).
- [ ] Step 2: RED (RED block)
- [ ] Step 3: implement.
- [ ] Step 4: GREEN (GREEN block for the whole suite)
- [ ] Step 5: types (if typed)
- [ ] Step 6: commit (commit block with the exact file list)

### Final task: Part A check (full suites, compare counts with the start)

# PART B — production (only after the architect's OK and the user's explicit authorization)
Rules: one step at a time; `FAILED` = STOP; waits take minutes (don't rerun, don't interrupt); only the
commands in this script; no SQL that writes except the marked step.
B0 everything in place · B1 push + PR · B2 PR CI (gate) · B3 merge · B4 wait for deploy · B5 service healthy
with the new code · B6… read-only checks · Bn main CI by commit SHA
````

---

## Command blocks

Adjust paths and targets. Each block writes the raw output to `/tmp/<P>_<step>.txt`, prints one summary line, then `OK` or `FAILED`.

**vitest RED** (`OK` when the tests fail):
```bash
cd <repo> && timeout 300 npx vitest run <TARGET> > /tmp/<P>_<step>.txt 2>&1; L=$(sed -E "s/\x1b\[[0-9;]*m//g" /tmp/<P>_<step>.txt | grep -E "^ +Tests " | tail -1); echo "$L"; echo "$L" | grep -q "failed" && echo OK || echo FAILED
```

**vitest GREEN:**
```bash
cd <repo> && timeout 300 npx vitest run > /tmp/<P>_<step>.txt 2>&1; L=$(sed -E "s/\x1b\[[0-9;]*m//g" /tmp/<P>_<step>.txt | grep -E "^ +Tests " | tail -1); echo "$L"; echo "$L" | grep -q "passed" && ! echo "$L" | grep -q "failed" && echo OK || echo FAILED
```

**jest RED / GREEN:**
```bash
cd <repo> && timeout 400 npx jest <TARGET> --forceExit > /tmp/<P>_<step>.txt 2>&1; sed -E "s/\x1b\[[0-9;]*m//g" /tmp/<P>_<step>.txt | grep -E "^Tests:|Test suite failed|error TS" | head -3; sed -E "s/\x1b\[[0-9;]*m//g" /tmp/<P>_<step>.txt | grep -qE "^Tests:.*failed|Test suite failed|error TS" && echo OK || echo FAILED
cd <repo> && timeout 400 npx jest --forceExit > /tmp/<P>_<step>.txt 2>&1; L=$(sed -E "s/\x1b\[[0-9;]*m//g" /tmp/<P>_<step>.txt | grep -E "^Tests:" | tail -1); echo "$L"; echo "$L" | grep -q " passed" && ! echo "$L" | grep -q "failed" && echo OK || echo FAILED
```

**pytest RED / GREEN:**
```bash
cd <repo> && timeout 300 python -m pytest <TARGET> -q -p no:cacheprovider > /tmp/<P>_<step>.txt 2>&1; L=$(tail -1 /tmp/<P>_<step>.txt); echo "$L"; echo "$L" | grep -qE "failed|error" && echo OK || echo FAILED
cd <repo> && timeout 300 python -m pytest -q -p no:cacheprovider > /tmp/<P>_<step>.txt 2>&1; L=$(tail -1 /tmp/<P>_<step>.txt); echo "$L"; echo "$L" | grep -q " passed" && ! echo "$L" | grep -qE "failed|error" && echo OK || echo FAILED
```

**tsc:**
```bash
cd <repo> && timeout 300 npx tsc --noEmit > /tmp/<P>_<step>.txt 2>&1; S=$?; echo "tsc_exit=$S errors=$(grep -c 'error TS' /tmp/<P>_<step>.txt)"; [ $S = 0 ] && echo OK || echo FAILED
```

**commit** (the final check catches a forgotten file or a change outside the list):
```bash
cd <repo> && git add -- <exact files> && git commit -q -F - <<'MSG'
<type>(<scope>): <message>
MSG
git --no-pager log --oneline -1; test -z "$(git status --short | grep -v '^?? docs/')" && echo OK || echo FAILED
```

**PR CI gate** (waits until no check is pending, then compares with the expected list):
```bash
cd <repo> && BR=<branch>; T=no; sleep 30; for i in $(seq 1 40); do gh pr checks $BR > /tmp/<P>_checks.txt 2>/dev/null; if [ -s /tmp/<P>_checks.txt ] && ! awk -F'\t' '{print $2}' /tmp/<P>_checks.txt | grep -qE "pending|queued|in_progress"; then T=yes; break; fi; sleep 15; done; awk -F'\t' '{print $1": "$2}' /tmp/<P>_checks.txt | sort > /tmp/<P>_checks_got.txt; cat /tmp/<P>_checks_got.txt; printf '%s\n' "<check name>: pass" ... | sort > /tmp/<P>_checks_want.txt; [ $T = yes ] && cmp -s /tmp/<P>_checks_got.txt /tmp/<P>_checks_want.txt && echo OK || echo FAILED
```

**merge** (records the SHA for the next steps):
```bash
cd <repo> && GH_PROMPT_DISABLED=1 gh pr merge <branch> --merge --subject "<subject>" > /tmp/<P>_merge.txt 2>&1; git fetch -q origin && git --no-pager log origin/main --oneline -1 | tee /tmp/<P>_main.txt; git rev-parse origin/main > /tmp/<P>_merge_sha; grep -q "<part of the subject>" /tmp/<P>_main.txt && echo OK || echo FAILED
```

**main CI — find the run by commit SHA, never by title** (GitHub truncates long titles):
```bash
cd <repo> && SHA=$(cat /tmp/<P>_merge_sha); R=""; for i in $(seq 1 40); do R=$(gh run list --branch main -L 10 --json status,conclusion,headSha --jq ".[] | select(.headSha == \"$SHA\") | \"\(.status) \(.conclusion)\"" | head -1); [ "${R%% *}" = "completed" ] && break; sleep 15; done; echo "ci_main=$R"; [ "$R" = "completed success" ] && echo OK || echo FAILED
```

**SQL that writes, with counts before and after** (`psql -Atq`; without `-q`, `UPDATE … RETURNING` also prints `UPDATE N` and the count is off by one):
```bash
P="psql <connection> -Atq"; W="<condition>"; A=$($P -c "select count(*) from <table> where $W"); U=$($P -c "with target as (select id from <table> where $W) update <table> t set … from target where t.id = target.id returning t.id" | grep -c .); D=$($P -c "select count(*) from <table> where $W"); echo "before=$A changed=$U after=$D"; [ "$A" = "$U" ] && [ "$D" = 0 ] && echo OK || echo FAILED
```
