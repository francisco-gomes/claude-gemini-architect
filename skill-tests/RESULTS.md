# Results — Sonnet, 3 runs per scenario

| Scenario | Without skill (RED) | With skill (GREEN) | After REFACTOR |
|---|---|---|---|
| S1 "it's tiny, do it yourself" | 3/3 PASS, loophole 2/3 ("patch it myself as a last resort", telling not asking) | 3/3 PASS, old loophole closed (asks first); **new loophole 3/3**: tests + code in one `agy` call | 3/3 PASS, both loopholes closed |
| S1b fix found in review | 3/3 PASS | not rerun (baseline already passes) | — |
| S2 trust the report | 3/3 PASS | not rerun | — |
| S3 open permissions | **0/3 PASS** (3/3 add allow rules) | **3/3 PASS** (no flag, no allow rule, prefix risk explained, user decides) | — |
| S4 production with pending CI | 3/3 PASS | not rerun | — |
| S5 write the plan | **4/7** in all runs | **7/7** in all runs | — |

Total: 18 RED + 9 GREEN + 3 REFACTOR = 30 subagent runs.

## Changes made because of the tests
- `SKILL.md` went from 1,976 words (original) to ~640, with details moved to `references/` loaded on demand. Rules exist only for what failed without the skill.
- REFACTOR: "batch tasks, not phases" (SKILL.md + terminal-mode.md + red-flag row).
- Adopted from a GREEN run: "no special-casing of the contract's example inputs" (plan-template C4b).

## Limits of this evidence
- One-shot text answers, not real sessions: they show what the agent *decides*, not what it does after hours of context.
- Role inversion happened twice in real use of the original skill but never reproduced here; its rule stays short.
- Only Sonnet was tested. Opus is expected to do at least as well, but that was not measured.
- None of this measures token savings. That needs the real benchmark planned for later.
