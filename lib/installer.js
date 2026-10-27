import fs from 'node:fs';
import path from 'node:path';

export const SKILL_NAME = 'claude-gemini-architect';
export const MARKER = '.installed-by.json';

export class InstallError extends Error {}

function findRepoRoot(startDir) {
  let curr = path.resolve(startDir);
  while (true) {
    if (fs.existsSync(path.join(curr, '.git'))) {
      return curr;
    }
    const parent = path.dirname(curr);
    if (parent === curr) {
      return startDir;
    }
    curr = parent;
  }
}

/** <repo-root or cwd>/.claude/skills/<name> with `project`, else <CLAUDE_CONFIG_DIR or ~/.claude>/skills/<name>. */
export function targetDir({ project, cwd, env, home }) {
  const base = project ? path.join(findRepoRoot(cwd), '.claude') : env.CLAUDE_CONFIG_DIR || path.join(home, '.claude');
  return path.join(base, 'skills', SKILL_NAME);
}

/** The marker this installer writes, or null when it is missing, unreadable or someone else's. */
export function readMarker(dir) {
  try {
    const marker = JSON.parse(fs.readFileSync(path.join(dir, MARKER), 'utf8'));
    return marker && marker.name === SKILL_NAME ? marker : null;
  } catch {
    return null;
  }
}

function copyTree(source, destination) {
  fs.cpSync(source, destination, {
    recursive: true,
    filter: (src) => path.basename(src) !== '__pycache__' && !src.endsWith('.pyc'),
  });
}

function isPidDead(pid) {
  try {
    process.kill(pid, 0);
    return false;
  } catch (err) {
    return err.code === 'ESRCH';
  }
}

function getBaseDir(skillsDir) {
  try {
    const stat = fs.lstatSync(skillsDir);
    if (stat.isSymbolicLink()) {
      return path.dirname(fs.realpathSync(skillsDir));
    }
  } catch {}
  return path.dirname(skillsDir);
}

function restoreOrphanBackup(base, target) {
  if (fs.existsSync(target) || !fs.existsSync(base)) return;
  try {
    for (const entry of fs.readdirSync(base)) {
      const m = entry.match(/^\.claude-gemini-architect\.bak-(\d+)$/);
      if (m && isPidDead(Number(m[1]))) {
        fs.renameSync(path.join(base, entry), target);
        break;
      }
    }
  } catch {}
}

function cleanLeftovers(base, skillsDir) {
  if (fs.existsSync(base)) {
    try {
      for (const entry of fs.readdirSync(base)) {
        const m = entry.match(/^\.claude-gemini-architect\.(tmp|bak)-(\d+)$/);
        if (m && isPidDead(Number(m[2]))) {
          fs.rmSync(path.join(base, entry), { recursive: true, force: true });
        }
      }
    } catch {}
  }
  if (fs.existsSync(skillsDir)) {
    try {
      for (const entry of fs.readdirSync(skillsDir)) {
        const m = entry.match(/^claude-gemini-architect\.(tmp|bak)-(\d+)$/);
        if (m && isPidDead(Number(m[2]))) {
          fs.rmSync(path.join(skillsDir, entry), { recursive: true, force: true });
        }
      }
    } catch {}
  }
}

/**
 * Copies `source` to `target` atomically: a failure never leaves a half-installed skill.
 * `confirm(question)` resolves to true/false; pass null when nobody can answer (not a TTY),
 * and replacing an existing folder then requires `force`.
 */
export async function install({ source, target, version, force = false, confirm = null, copy = copyTree }) {
  const skillsDir = path.dirname(target);
  const base = getBaseDir(skillsDir);
  restoreOrphanBackup(base, target);

  const exists = fs.existsSync(target);
  if (exists && !force) {
    const marker = readMarker(target);
    if (marker && marker.version === version) return 'unchanged';
    const why = marker ? `version ${marker.version} is installed` : 'the folder was not created by this installer';
    if (!confirm) throw new InstallError(`${target} already exists (${why}). Run again with --force to replace it.`);
    if (!(await confirm(`${target} already exists (${why}). Replace it? [y/N] `))) return 'aborted';
  }
  cleanLeftovers(base, skillsDir);
  fs.mkdirSync(skillsDir, { recursive: true });
  const tmp = path.join(base, `.${SKILL_NAME}.tmp-${process.pid}`);
  const bak = path.join(base, `.${SKILL_NAME}.bak-${process.pid}`);
  fs.rmSync(tmp, { recursive: true, force: true });
  try {
    copy(source, tmp);
    const marker = { name: SKILL_NAME, version, installedAt: new Date().toISOString() };
    fs.writeFileSync(path.join(tmp, MARKER), JSON.stringify(marker, null, 2) + '\n');
    if (exists) fs.renameSync(target, bak);
    fs.renameSync(tmp, target);
  } catch (err) {
    fs.rmSync(tmp, { recursive: true, force: true });
    if (fs.existsSync(bak) && !fs.existsSync(target)) fs.renameSync(bak, target);
    throw err;
  }
  fs.rmSync(bak, { recursive: true, force: true });
  return exists ? 'updated' : 'installed';
}

/** Removes the installed skill; refuses a folder without this installer's marker unless `force`. */
export function uninstall({ target, force = false }) {
  if (!fs.existsSync(target)) return 'absent';
  if (!readMarker(target) && !force) {
    throw new InstallError(`${target} was not created by this installer; refusing to delete it. Use --force to delete it anyway.`);
  }
  fs.rmSync(target, { recursive: true, force: true });
  return 'removed';
}
