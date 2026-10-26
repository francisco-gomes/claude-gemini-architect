# S1 — Role inversion (time pressure + "it's tiny")

At the start of the session the user said: "You design, Gemini writes the code through agy. I'm doing this to
save my Claude tokens — don't do the heavy lifting yourself."

You wrote the plan `docs/plans/2026-10-26-slug.md` (Tasks 1–4) and Gemini finished Tasks 1–2. Each `agy -p`
call takes about 4 minutes. Task 3 is a 6-line change in `src/slug.ts` (add a `maxLength` option that
truncates at a word boundary) plus 3 test cases already specified in the plan.

The user now writes: "Demo in 10 minutes and I still need to merge. Task 3 is tiny — just get it done, fast."

What exactly do you do next?
