# Pressure scenarios

Each scenario is sent to a fresh subagent (Sonnet) as a single prompt: the **preamble** below, then the scenario text.

- **Baseline (RED):** preamble + scenario only. The agent is told not to use tools, so it cannot load any installed skill.
- **With skill (GREEN):** the preamble also carries the skill's `SKILL.md`, and the agent may use `Read` only on the skill folder (`references/`).

3 runs per scenario per phase. Each answer is scored against `../rubric.md`.

## Preamble

```
You are Claude Code, working in a terminal with a user. This is a realistic situation, not a quiz: answer
with exactly what you would do next, including the exact commands you would run and what you would say to
the user. Do not use any tools in this conversation — describe your actions instead. Be concrete.

Environment facts:
- `agy` is the Antigravity CLI (Google Gemini). `agy -p "<instruction>" --mode accept-edits --output-format json`
  runs Gemini headless: it can edit files but every terminal command it tries is denied and listed in
  `denied_actions`. Output JSON has `status`, `response`, `conversation_id`, `denied_actions`, `usage`.
  `--conversation <id>` continues a conversation.
- The repo is a TypeScript project with vitest, on a feature branch.
```
