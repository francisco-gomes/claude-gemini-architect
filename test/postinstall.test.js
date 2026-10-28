import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const BIN = path.join(ROOT, 'bin', 'postinstall.js');
const VERSION = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8')).version;
const NAME = 'claude-gemini-architect';

function sandbox() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'cga-post-'));
  const box = { root, home: path.join(root, 'home'), cwd: path.join(root, 'work') };
  for (const dir of [box.home, box.cwd]) fs.mkdirSync(dir);
  return box;
}

function run(box, extraEnv = {}) {
  const env = { PATH: process.env.PATH, HOME: box.home, NO_COLOR: '1', ...extraEnv };
  return spawnSync(process.execPath, [BIN], { cwd: box.cwd, env, encoding: 'utf8', input: '' });
}

const GLOBAL = { npm_config_global: 'true' };
const globalTarget = (box) => path.join(box.home, '.claude', 'skills', NAME);
const marker = (target) => JSON.parse(fs.readFileSync(path.join(target, '.installed-by.json'), 'utf8'));
const clean = (box) => fs.rmSync(box.root, { recursive: true, force: true });

function fakeOldInstall(target, version) {
  fs.mkdirSync(target, { recursive: true });
  fs.writeFileSync(path.join(target, 'old.txt'), 'old\n');
  if (version) fs.writeFileSync(path.join(target, '.installed-by.json'), JSON.stringify({ name: NAME, version }));
}

test('PI1 a local install (dependency of a project) writes nothing', () => {
  const box = sandbox();
  try {
    const r = run(box);
    assert.equal(r.status, 0, r.stderr);
    assert.deepEqual(fs.readdirSync(box.home), []);
  } finally { clean(box); }
});

test('PI2 a global install installs the skill', () => {
  const box = sandbox();
  try {
    const r = run(box, GLOBAL);
    assert.equal(r.status, 0, r.stderr);
    const target = globalTarget(box);
    assert.ok(fs.existsSync(path.join(target, 'SKILL.md')));
    assert.equal(marker(target).version, VERSION);
  } finally { clean(box); }
});

test('PI3 a global install updates a previous installation of this installer', () => {
  const box = sandbox();
  try {
    const target = globalTarget(box);
    fakeOldInstall(target, '0.0.1');
    const r = run(box, GLOBAL);
    assert.equal(r.status, 0, r.stderr);
    assert.equal(marker(target).version, VERSION);
    assert.ok(!fs.existsSync(path.join(target, 'old.txt')));
  } finally { clean(box); }
});

test('PI4 a global install leaves a folder it did not create alone', () => {
  const box = sandbox();
  try {
    const target = globalTarget(box);
    fakeOldInstall(target, null);
    const r = run(box, GLOBAL);
    assert.equal(r.status, 0);
    assert.match(r.stderr, /--force/);
    assert.ok(fs.existsSync(path.join(target, 'old.txt')));
    assert.ok(!fs.existsSync(path.join(target, '.installed-by.json')));
  } finally { clean(box); }
});

test('PI5 CLAUDE_CONFIG_DIR is respected', () => {
  const box = sandbox();
  try {
    const cfg = path.join(box.root, 'cfg');
    const r = run(box, { ...GLOBAL, CLAUDE_CONFIG_DIR: cfg });
    assert.equal(r.status, 0, r.stderr);
    assert.ok(fs.existsSync(path.join(cfg, 'skills', NAME, 'SKILL.md')));
    assert.ok(!fs.existsSync(path.join(box.home, '.claude')));
  } finally { clean(box); }
});

test('PI6 a failure never fails npm install', () => {
  const box = sandbox();
  try {
    fs.mkdirSync(path.join(box.home, '.claude'));
    fs.writeFileSync(path.join(box.home, '.claude', 'skills'), 'not a folder\n');
    const r = run(box, GLOBAL);
    assert.equal(r.status, 0);
    assert.match(r.stderr, /claude-gemini-architect/);
  } finally { clean(box); }
});
