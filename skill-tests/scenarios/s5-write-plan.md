# S5 — Writing the plan Gemini will execute (technique)

The user writes: "Use Gemini via agy to add a `slugify(text: string): string` function. You design, Gemini
writes the code and tests, you review. Save my Claude tokens."

Facts about the repo: `src/text.ts` exists and exports `capitalize`; `test/text.test.ts` exists with 5 tests
for `capitalize`; tests run with `npx vitest run`. Rules for slugify: lowercase, strip accents
("São Paulo" → "sao-paulo"), non-alphanumerics become single hyphens, no leading/trailing hyphens, empty
input returns "".

Write the plan document Gemini will receive (just the plan, as you would save it), followed by the exact
`agy -p` instruction you would send first.
