import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { install, uninstall, targetDir, readMarker, InstallError, SKILL_NAME, MARKER } from '../lib/installer.js';

function scratch() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'cga-unit-'));
}

function makeSource(root) {
  const src = path.join(root, 'src-skill');
  fs.mkdirSync(path.join(src, 'scripts', '__pycache__'), { recursive: true });
  fs.writeFileSync(path.join(src, 'SKILL.md'), '# skill\n');
  fs.writeFileSync(path.join(src, 'scripts', 'a.py'), 'print(1)\n');
  fs.writeFileSync(path.join(src, 'scripts', '__pycache__', 'a.cpython-312.pyc'), 'x');
  return src;
}

function oldInstall(target, version) {
  fs.mkdirSync(target, { recursive: true });
  fs.writeFileSync(path.join(target, 'old.txt'), 'old\n');
  if (version) fs.writeFileSync(path.join(target, MARKER), JSON.stringify({ name: SKILL_NAME, version }));
}

function deadPid() {
  return spawnSync(process.execPath, ['-e', '']).pid;
}

test('U1 targetDir: CLAUDE_CONFIG_DIR, ~/.claude and --project', () => {
  assert.equal(targetDir({ project: false, cwd: '/w', env: { CLAUDE_CONFIG_DIR: '/cfg' }, home: '/h' }), path.join('/cfg', 'skills', SKILL_NAME));
  assert.equal(targetDir({ project: false, cwd: '/w', env: {}, home: '/h' }), path.join('/h', '.claude', 'skills', SKILL_NAME));
  assert.equal(targetDir({ project: true, cwd: '/w', env: { CLAUDE_CONFIG_DIR: '/cfg' }, home: '/h' }), path.join('/w', '.claude', 'skills', SKILL_NAME));
});

test('U2 fresh install copies the files and writes the marker', async () => {
  const root = scratch();
  try {
    const target = path.join(root, 'skills', SKILL_NAME);
    assert.equal(await install({ source: makeSource(root), target, version: '1.0.0' }), 'installed');
    assert.equal(fs.readFileSync(path.join(target, 'scripts', 'a.py'), 'utf8'), 'print(1)\n');
    assert.equal(readMarker(target).version, '1.0.0');
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('U3 same version without force is left unchanged', async () => {
  const root = scratch();
  try {
    const source = makeSource(root);
    const target = path.join(root, 'skills', SKILL_NAME);
    await install({ source, target, version: '1.0.0' });
    const before = readMarker(target).installedAt;
    assert.equal(await install({ source, target, version: '1.0.0' }), 'unchanged');
    assert.equal(readMarker(target).installedAt, before);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('U4 other version, no force, nobody to confirm: refuses and keeps the old install', async () => {
  const root = scratch();
  try {
    const target = path.join(root, 'skills', SKILL_NAME);
    oldInstall(target, '0.0.1');
    await assert.rejects(install({ source: makeSource(root), target, version: '1.0.0' }), (e) => e instanceof InstallError && /--force/.test(e.message));
    assert.equal(fs.readFileSync(path.join(target, 'old.txt'), 'utf8'), 'old\n');
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('U5 confirm false aborts, confirm true replaces', async () => {
  const root = scratch();
  try {
    const source = makeSource(root);
    const target = path.join(root, 'skills', SKILL_NAME);
    oldInstall(target, '0.0.1');
    assert.equal(await install({ source, target, version: '1.0.0', confirm: async () => false }), 'aborted');
    assert.ok(fs.existsSync(path.join(target, 'old.txt')));
    assert.equal(await install({ source, target, version: '1.0.0', confirm: async () => true }), 'updated');
    assert.ok(!fs.existsSync(path.join(target, 'old.txt')));
    assert.equal(readMarker(target).version, '1.0.0');
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('U6 a folder this installer did not create needs force', async () => {
  const root = scratch();
  try {
    const source = makeSource(root);
    const target = path.join(root, 'skills', SKILL_NAME);
    oldInstall(target, null);
    await assert.rejects(install({ source, target, version: '1.0.0' }), /not created by this installer/);
    assert.ok(fs.existsSync(path.join(target, 'old.txt')));
    assert.equal(await install({ source, target, version: '1.0.0', force: true }), 'updated');
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('U7 a copy that fails midway leaves the old install intact and no leftovers', async () => {
  const root = scratch();
  try {
    const target = path.join(root, 'skills', SKILL_NAME);
    oldInstall(target, '0.0.1');
    const failingCopy = (src, dst) => {
      fs.mkdirSync(dst, { recursive: true });
      fs.writeFileSync(path.join(dst, 'partial'), 'x');
      throw new Error('disk full');
    };
    await assert.rejects(install({ source: makeSource(root), target, version: '1.0.0', force: true, copy: failingCopy }), /disk full/);
    assert.equal(fs.readFileSync(path.join(target, 'old.txt'), 'utf8'), 'old\n');
    assert.equal(readMarker(target).version, '0.0.1');
    assert.deepEqual(fs.readdirSync(path.dirname(target)), [SKILL_NAME]);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('U8 uninstall: absent, with marker, without marker, without marker + force', () => {
  const root = scratch();
  try {
    const target = path.join(root, 'skills', SKILL_NAME);
    assert.equal(uninstall({ target }), 'absent');
    oldInstall(target, '1.0.0');
    assert.equal(uninstall({ target }), 'removed');
    assert.ok(!fs.existsSync(target));
    oldInstall(target, null);
    assert.throws(() => uninstall({ target }), InstallError);
    assert.ok(fs.existsSync(target));
    assert.equal(uninstall({ target, force: true }), 'removed');
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('U9 an unreadable marker counts as no marker', () => {
  const root = scratch();
  try {
    fs.writeFileSync(path.join(root, MARKER), '{not json');
    assert.equal(readMarker(root), null);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('U10 __pycache__ and .pyc files are not copied', async () => {
  const root = scratch();
  try {
    const target = path.join(root, 'skills', SKILL_NAME);
    await install({ source: makeSource(root), target, version: '1.0.0' });
    assert.ok(!fs.existsSync(path.join(target, 'scripts', '__pycache__')));
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('U11 staging lives outside skills/ and stale leftovers are cleaned', async () => {
  const root = scratch();
  try {
    const base = path.join(root, 'cfg');
    const target = path.join(base, 'skills', SKILL_NAME);
    const pid = deadPid();
    fs.mkdirSync(path.join(base, `.${SKILL_NAME}.tmp-${pid}`), { recursive: true });
    fs.mkdirSync(path.join(base, 'skills', `${SKILL_NAME}.tmp-${pid}`), { recursive: true });
    fs.writeFileSync(path.join(base, 'skills', `${SKILL_NAME}.tmp-${pid}`, 'SKILL.md'), 'stale');
    const seen = [];
    const spyCopy = (src, dst) => { seen.push(dst); fs.cpSync(src, dst, { recursive: true }); };
    await install({ source: makeSource(root), target, version: '1.0.0', copy: spyCopy });
    assert.equal(path.dirname(seen[0]), base);
    assert.deepEqual(fs.readdirSync(path.join(base, 'skills')), [SKILL_NAME]);
    assert.deepEqual(fs.readdirSync(base).sort(), ['skills']);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('U12 --project resolves the repo root (nearest folder with .git)', () => {
  const root = scratch();
  try {
    const repo = path.join(root, 'repo');
    const sub = path.join(repo, 'packages', 'api');
    fs.mkdirSync(path.join(repo, '.git'), { recursive: true });
    fs.mkdirSync(sub, { recursive: true });
    assert.equal(targetDir({ project: true, cwd: sub, env: {}, home: '/h' }), path.join(repo, '.claude', 'skills', SKILL_NAME));
    const loose = path.join(root, 'loose');
    fs.mkdirSync(loose);
    assert.equal(targetDir({ project: true, cwd: loose, env: {}, home: '/h' }), path.join(loose, '.claude', 'skills', SKILL_NAME));
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('U13 skills/ as a symlink: staging happens next to the real folder', async () => {
  const root = fs.realpathSync(scratch());
  try {
    const real = path.join(root, 'dotfiles', 'skills');
    fs.mkdirSync(real, { recursive: true });
    const base = path.join(root, 'cfg');
    fs.mkdirSync(base);
    fs.symlinkSync(real, path.join(base, 'skills'));
    const target = path.join(base, 'skills', SKILL_NAME);
    const seen = [];
    const spyCopy = (src, dst) => { seen.push(dst); fs.cpSync(src, dst, { recursive: true }); };
    assert.equal(await install({ source: makeSource(root), target, version: '1.0.0', copy: spyCopy }), 'installed');
    assert.equal(path.dirname(seen[0]), path.join(root, 'dotfiles'));
    assert.ok(fs.existsSync(path.join(real, SKILL_NAME, 'SKILL.md')));
    assert.deepEqual(fs.readdirSync(path.join(root, 'dotfiles')).sort(), ['skills']);
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('U14 leftovers of an installer that is still running are kept', async () => {
  const root = scratch();
  try {
    const base = path.join(root, 'cfg');
    const target = path.join(base, 'skills', SKILL_NAME);
    const alive = path.join(base, `.${SKILL_NAME}.tmp-${process.ppid}`);
    fs.mkdirSync(alive, { recursive: true });
    await install({ source: makeSource(root), target, version: '1.0.0' });
    assert.ok(fs.existsSync(alive));
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});

test('U15 an orphan backup from a killed install is restored before anything else', async () => {
  const root = scratch();
  try {
    const base = path.join(root, 'cfg');
    const target = path.join(base, 'skills', SKILL_NAME);
    const bak = path.join(base, `.${SKILL_NAME}.bak-${deadPid()}`);
    oldInstall(bak, '0.0.1');
    fs.mkdirSync(path.join(base, 'skills'), { recursive: true });
    await assert.rejects(install({ source: makeSource(root), target, version: '1.0.0' }), /--force/);
    assert.equal(readMarker(target).version, '0.0.1');
    assert.ok(!fs.existsSync(bak));
  } finally { fs.rmSync(root, { recursive: true, force: true }); }
});
