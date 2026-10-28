# Changelog

## 0.1.1 (unreleased)

- `npm i -g claude-gemini-architect` now installs the skill: a `postinstall` that runs only on global installs, updates an earlier installation of this installer and leaves any other folder alone. A local `npm i` still installs nothing, and the README now says so.
- README: install with `npx skills add francisco-gomes/claude-gemini-architect` ([vercel-labs/skills](https://github.com/vercel-labs/skills)).
- Troubleshooting: the skill doesn't show up after `npm i`; npm's `allow-scripts` warning.

## 0.1.0 (2026-10-28)

- First public version of the skill, generalized from a private workflow used in production.
- Lean `SKILL.md` plus on-demand references (plan template, terminal mode, herdr mode, review checklist), tested with pressure scenarios (`skill-tests/`).
- Helper scripts for herdr mode: `watchdog.py` (with `GEMINI_ARCHITECT_EXTRA_DENY`), `extract_blocks.py`, `next_block.py`.
- `npx claude-gemini-architect` installer with `--project`, `--force`, `--uninstall` and `--check`.
