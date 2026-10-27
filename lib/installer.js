import fs from 'node:fs';
import path from 'node:path';

export const SKILL_NAME = 'claude-gemini-architect';
export const MARKER = '.installed-by.json';

export class InstallError extends Error {}

/** <cwd>/.claude/skills/<name> with `project`, else <CLAUDE_CONFIG_DIR or ~/.claude>/skills/<name>. */
export function targetDir({ project, cwd, env, home }) {
  const base = project ? path.join(cwd, '.claude') : env.CLAUDE_CONFIG_DIR || path.join(home, '.claude');
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

/**
 * Copies `source` to `target` atomically: a failure never leaves a half-installed skill.
 * `confirm(question)` resolves to true/false; pass null when nobody can answer (not a TTY),
 * and replacing an existing folder then requires `force`.
 */
export async function install({ source, target, version, force = false, confirm = null, copy = copyTree }) {
  const exists = fs.existsSync(target);
  if (exists && !force) {
    const marker = readMarker(target);
    if (marker && marker.version === version) return 'unchanged';
    const why = marker ? `version ${marker.version} is installed` : 'the folder was not created by this installer';
    if (!confirm) throw new InstallError(`${target} already exists (${why}). Run again with --force to replace it.`);
    if (!(await confirm(`${target} already exists (${why}). Replace it? [y/N] `))) return 'aborted';
  }
  fs.mkdirSync(path.dirname(target), { recursive: true });
  const tmp = `${target}.tmp-${process.pid}`;
  const bak = `${target}.bak-${process.pid}`;
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
