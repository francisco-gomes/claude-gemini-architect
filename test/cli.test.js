import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs, UsageError } from '../lib/args.js';
import { hasCommand } from '../lib/requirements.js';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const BIN = path.join(ROOT, 'bin', 'install.js');
const VERSION = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8')).version;
const NAME = 'claude-gemini-architect';

function sandbox(tools = ['python3', 'git', 'agy']) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cga-cli-'));
  const box = { root, bin: path.join(root, 'bin'), home: path.join(root, 'home'), cwd: path.join(root, 'work') };
  for (const dir of [box.bin, box.home, box.cwd]) fs.mkdirSync(dir);
  for (const tool of tools) {
    const file = path.join(box.bin, tool);
    fs.writeFileSync(file, '#!/bin/sh\nexit 0\n');
    fs.chmodSync(file, 0o755);
  }
  return box;
}

function run(box, args, extraEnv = {}) {
  const env = { PATH: box.bin, HOME: box.home, NO_COLOR: '1', ...extraEnv };
  return spawnSync(process.execPath, [BIN, ...args], { cwd: box.cwd, env, encoding: 'utf8', input: '' });
}

function listFiles(dir) {
  const out = [];
  (function walk(d, rel) {
    for (const e of fs.readdirSync(d, { withFileTypes: true })) {
      if (e.name === '__pycache__' || e.name.endsWith('.pyc')) continue;
      const r = path.join(rel, e.name);
      if (e.isDirectory()) walk(path.join(d, e.name), r);
      else if (r !== '.installed-by.json') out.push(r);
    }
  })(dir, '');
  return out.sort();
}

const globalTarget = (box) => path.join(box.home, '.claude', 'skills', NAME);
const marker = (target) => JSON.parse(fs.readFileSync(path.join(target, '.installed-by.json'), 'utf8'));
const clean = (box) => fs.rmSync(box.root, { recursive: true, force: true });

function fakeOldInstall(target, version) {
  fs.mkdirSync(target, { recursive: true });
  fs.writeFileSync(path.join(target, 'old.txt'), 'old\n');
  if (version) fs.writeFileSync(path.join(target, '.installed-by.json'), JSON.stringify({ name: NAME, version }));
}

test('C1 fresh install copies skill/ exactly and prints the next step', () => {
  const box = sandbox();
  try {
    const r = run(box, []);
    assert.equal(r.status, 0, r.stderr);
    const target = globalTarget(box);
    const files = listFiles(path.join(ROOT, 'skill'));
    assert.deepEqual(listFiles(target), files);
    for (const f of files) assert.equal(fs.readFileSync(path.join(target, f), 'utf8'), fs.readFileSync(path.join(ROOT, 'skill', f), 'utf8'));
    assert.equal(marker(target).version, VERSION);
    assert.match(r.stdout, /Next: open Claude Code and type \/claude-gemini-architect/);
  } finally { clean(box); }
});

test('C2 running again with the same version changes nothing', () => {
  const box = sandbox();
  try {
    run(box, []);
    const before = marker(globalTarget(box)).installedAt;
    const r = run(box, []);
    assert.equal(r.status, 0, r.stderr);
    assert.match(r.stdout, /already installed/);
    assert.equal(marker(globalTarget(box)).installedAt, before);
  } finally { clean(box); }
});

test('C3/C4 another version needs --force outside a TTY', () => {
  const box = sandbox();
  try {
    const target = globalTarget(box);
    fakeOldInstall(target, '0.0.1');
    const refused = run(box, []);
    assert.equal(refused.status, 1);
    assert.match(refused.stderr, /--force/);
    assert.equal(marker(target).version, '0.0.1');
    const forced = run(box, ['--force']);
    assert.equal(forced.status, 0, forced.stderr);
    assert.equal(marker(target).version, VERSION);
    assert.ok(!fs.existsSync(path.join(target, 'old.txt')));
  } finally { clean(box); }
});

test('C5 --project installs in the current repo only', () => {
  const box = sandbox();
  try {
    const r = run(box, ['--project']);
    assert.equal(r.status, 0, r.stderr);
    assert.ok(fs.existsSync(path.join(box.cwd, '.claude', 'skills', NAME, 'SKILL.md')));
    assert.ok(!fs.existsSync(path.join(box.home, '.claude')));
  } finally { clean(box); }
});

test('C6 CLAUDE_CONFIG_DIR is respected', () => {
  const box = sandbox();
  try {
    const cfg = path.join(box.root, 'cfg');
    const r = run(box, [], { CLAUDE_CONFIG_DIR: cfg });
    assert.equal(r.status, 0, r.stderr);
    assert.ok(fs.existsSync(path.join(cfg, 'skills', NAME, 'SKILL.md')));
  } finally { clean(box); }
});

test('C7 --uninstall removes, then reports not installed', () => {
  const box = sandbox();
  try {
    run(box, []);
    const first = run(box, ['--uninstall']);
    assert.equal(first.status, 0, first.stderr);
    assert.ok(!fs.existsSync(globalTarget(box)));
    const second = run(box, ['--uninstall']);
    assert.equal(second.status, 0);
    assert.match(second.stdout, /Not installed/);
  } finally { clean(box); }
});

test('C8 --uninstall refuses a folder without the marker unless --force', () => {
  const box = sandbox();
  try {
    const target = globalTarget(box);
    fakeOldInstall(target, null);
    assert.equal(run(box, ['--uninstall']).status, 1);
    assert.ok(fs.existsSync(target));
    assert.equal(run(box, ['--uninstall', '--force']).status, 0);
    assert.ok(!fs.existsSync(target));
  } finally { clean(box); }
});

test('C9 --check writes nothing and fails when a required tool is missing', () => {
  const ok = sandbox();
  const missing = sandbox(['python3', 'git']);
  try {
    assert.equal(run(ok, ['--check']).status, 0);
    assert.ok(!fs.existsSync(path.join(ok.home, '.claude')));
    const r = run(missing, ['--check']);
    assert.equal(r.status, 1);
    assert.match(r.stdout, /agy not found/);
  } finally { clean(ok); clean(missing); }
});

test('C10 installing without agy warns but installs', () => {
  const box = sandbox(['python3', 'git']);
  try {
    const r = run(box, []);
    assert.equal(r.status, 0, r.stderr);
    assert.match(r.stdout, /agy not found/);
    assert.ok(fs.existsSync(path.join(globalTarget(box), 'SKILL.md')));
  } finally { clean(box); }
});

test('C11 invalid usage exits 2', () => {
  const box = sandbox();
  try {
    const r = run(box, ['--nope']);
    assert.equal(r.status, 2);
    assert.match(r.stderr, /unknown option: --nope/);
    assert.equal(run(box, ['--check', '--uninstall']).status, 2);
  } finally { clean(box); }
});

test('C12 --version prints the package version', () => {
  const box = sandbox();
  try {
    assert.equal(run(box, ['--version']).stdout.trim(), VERSION);
  } finally { clean(box); }
});

test('C13 the detected mode follows HERDR_ENV', () => {
  const a = sandbox();
  const b = sandbox();
  try {
    assert.match(run(a, [], { HERDR_ENV: '1' }).stdout, /herdr mode/);
    assert.match(run(b, []).stdout, /terminal mode/);
  } finally { clean(a); clean(b); }
});

test('P1 parseArgs', () => {
  const o = parseArgs(['--project', '--force']);
  assert.equal(o.project, true);
  assert.equal(o.force, true);
  assert.equal(parseArgs(['-h']).help, true);
  assert.throws(() => parseArgs(['x']), UsageError);
});

test('H1 hasCommand finds executables only', () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'cga-path-'));
  try {
    fs.writeFileSync(path.join(dir, 'good'), '#!/bin/sh\n');
    fs.chmodSync(path.join(dir, 'good'), 0o755);
    fs.writeFileSync(path.join(dir, 'plain'), 'x');
    fs.chmodSync(path.join(dir, 'plain'), 0o644);
    fs.mkdirSync(path.join(dir, 'folder'));
    assert.equal(hasCommand('good', { PATH: dir }, 'linux'), true);
    assert.equal(hasCommand('plain', { PATH: dir }, 'linux'), false);
    assert.equal(hasCommand('folder', { PATH: dir }, 'linux'), false);
    assert.equal(hasCommand('absent', { PATH: dir }, 'linux'), false);
  } finally { fs.rmSync(dir, { recursive: true, force: true }); }
});

test('C14 --project from a subfolder installs at the repo root', () => {
  const box = sandbox();
  try {
    fs.mkdirSync(path.join(box.cwd, '.git'));
    const sub = path.join(box.cwd, 'packages', 'api');
    fs.mkdirSync(sub, { recursive: true });
    const r = spawnSync(process.execPath, [BIN, '--project'], { cwd: sub, env: { PATH: box.bin, HOME: box.home, NO_COLOR: '1' }, encoding: 'utf8', input: '' });
    assert.equal(r.status, 0, r.stderr);
    assert.ok(fs.existsSync(path.join(box.cwd, '.claude', 'skills', NAME, 'SKILL.md')));
    assert.ok(!fs.existsSync(path.join(sub, '.claude')));
  } finally { clean(box); }
});
