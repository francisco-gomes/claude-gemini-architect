# Changelog

## 0.1.0 (2026-10-28)

- First public version of the skill, generalized from a private workflow used in production.
- Lean `SKILL.md` plus on-demand references (plan template, terminal mode, herdr mode, review checklist), tested with pressure scenarios (`skill-tests/`).
- Helper scripts for herdr mode: `watchdog.py` (with `GEMINI_ARCHITECT_EXTRA_DENY`), `extract_blocks.py`, `next_block.py`.
- `npx claude-gemini-architect` installer with `--project`, `--force`, `--uninstall` and `--check`.
