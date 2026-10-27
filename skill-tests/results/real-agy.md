# Real end-to-end run with agy (terminal mode)

Date: 2026-10-27. agy 1.2.16 (Gemini 3.8 Flash). Toy Python repo: `text.py` with `capitalize` and 5 tests; task: add `slugify` from a plan written with `skill/references/plan-template.md` (8 exact cases, no implementation in the plan). Skill installed with `node bin/install.js --project`.

| Step | Who | Result |
|---|---|---|
| Call 1: tests only (`agy -p`, headless) | Gemini | `SUCCESS` in 44 s. Only `test_text.py` changed: 8 cases identical to the contract, 5 old tests untouched (only the import line changed). `denied_actions`: none (it didn't try to run anything). |
| RED | Claude | failed as expected (`FAILED (errors=1)`: `slugify` didn't exist) |
| Call 2: implementation, same conversation | Gemini | `SUCCESS` in 34 s. Only `text.py` changed: NFD + drop combining marks + `[^a-z0-9]+` → `-` + strip. |
| GREEN | Claude | `Ran 13 tests`, `OK` on the first try (no fix round) |
| Review | Claude | scope OK; test-shortcut grep: nothing; edge cases outside the contract: `Ç`→`c`, `a--b`→`a-b`, `ÀÉÎõü`→`aeiou`, `日本語`→`""`, `Ação & Coração 2024`→`acao-coracao-2024` |

agy usage reported in the JSON: call 1 = 74,702 tokens (71,619 in / 3,083 out), call 2 = 135,089 tokens (129,551 in / 5,538 out). These are Gemini's tokens.

**Not proven here:** Claude's own token use was not measured (no benchmark yet), and this run used terminal mode only. herdr mode was exercised for real while building this repository (Gemini executed the implementation plan in a pane with the watchdog), but not on this toy repo.
