import fs from 'node:fs';
import path from 'node:path';

export const REQUIREMENTS = [
  { cmd: 'python3', level: 'required', why: 'runs the skill scripts' },
  { cmd: 'git', level: 'required', why: 'every task is committed and reviewed' },
  { cmd: 'agy', level: 'required', why: 'the Antigravity CLI is the executor (Gemini); install it and log in' },
  { cmd: 'herdr', level: 'optional', why: 'herdr mode (Gemini in a pane); without it only terminal mode works' },
];

/** True when an executable file named `cmd` is on PATH. */
export function hasCommand(cmd, env = process.env, platform = process.platform) {
  const dirs = (env.PATH || env.Path || '').split(path.delimiter).filter(Boolean);
  const exts = platform === 'win32' ? (env.PATHEXT || '.EXE;.CMD;.BAT').split(';') : [''];
  for (const dir of dirs) {
    for (const ext of exts) {
      const file = path.join(dir, cmd + ext);
      try {
        fs.accessSync(file, platform === 'win32' ? fs.constants.F_OK : fs.constants.X_OK);
        if (fs.statSync(file).isFile()) return true;
      } catch {
        // not here
      }
    }
  }
  return false;
}

export function checkRequirements(env = process.env, platform = process.platform) {
  return REQUIREMENTS.map((r) => ({ ...r, found: hasCommand(r.cmd, env, platform) }));
}
