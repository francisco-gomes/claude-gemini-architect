# Review checklist (every commit, before it lands)

Gemini's report is not evidence. Check the diff, not the summary; that also keeps the review cheap in tokens.

1. **Scope:** `git status --short` / `git show --stat`. Only the task's files? A file outside the list: read that diff first. An **existing** file rewritten wholesale (many `-` lines)? Compare with `git show <commit>^:<file>`.
2. **Tests ran:** run the RED/GREEN blocks yourself. In headless mode Gemini could not have run them, whatever its report says.
3. **Contract:** read the production diff against the plan. Look for what a mocked test misses: a field now overwritten when the caller didn't send it, an error not caught on a path the contract says "never throws", a background task with no reference kept, a route or config the code never reaches.
4. **Test shortcuts** (production files only, must find nothing):
   ```bash
   git diff <base>...HEAD --name-only | grep -vE '(\.test\.|\.spec\.|^tests?/|_test\.py$)' | xargs -r git grep -nE "NODE_ENV *[!=]==? *['\"]test|process\.env\.VITEST|_isMockFunction|getState\(\)|currentTestName|PYTEST_CURRENT_TEST|in sys\.modules" --
   ```
5. **Old tests changed:** accept only changes that follow the new rule (values, numbers, a new field). A test deleted, skipped or loosened without the plan saying so is a rejection.
6. **Edges:** run a few contract cases and a few outside it yourself (empty input, `null`/`None`, wrong type).
7. **End of Part A:** run the full suites and compare the counts with the ones from before the plan.

Findings go into a findings file (`docs/plans/<plan>-findings.md`) and back to **Gemini** as a correction round with a contract: files, change, new test case, verification command, commit message. Review the fix commit before moving on.

## Closing (after Part B)

- Confirm in production with real data: services restarted after the merge and healthy, the new code is what's running, main CI green for the merge SHA, and, when there is traffic, the behavior visible in logs or data. No traffic yet: say it is not proven yet.
- Report to the user what was proven and what wasn't.
