export class UsageError extends Error {}

const FLAGS = {
  '--project': 'project',
  '--force': 'force',
  '--uninstall': 'uninstall',
  '--check': 'check',
  '--help': 'help',
  '-h': 'help',
  '--version': 'version',
  '-v': 'version',
};

export function parseArgs(argv) {
  const opts = { project: false, force: false, uninstall: false, check: false, help: false, version: false };
  for (const arg of argv) {
    const key = FLAGS[arg];
    if (!key) throw new UsageError(`unknown option: ${arg}`);
    opts[key] = true;
  }
  if (opts.check && opts.uninstall) throw new UsageError('--check and --uninstall cannot be used together');
  return opts;
}

export const HELP = `claude-gemini-architect: installs the Claude Code skill (Claude designs, Gemini builds through agy, Claude reviews)

Usage: npx claude-gemini-architect [options]

  (no option)    install in ~/.claude/skills/claude-gemini-architect ($CLAUDE_CONFIG_DIR/skills if set)
  --project      install in <repo root>/.claude/skills/claude-gemini-architect (nearest folder with .git, else here)
  --force        replace an existing installation without asking
  --uninstall    remove it (respects --project; a folder this installer didn't create needs --force)
  --check        only check the requirements (python3, git, agy, herdr); installs nothing
  -h, --help     show this help
  -v, --version  print the version

Exit codes: 0 ok, 1 error, 2 invalid usage.`;
