#!/usr/bin/env node
// Only runs on `npm i -g`; never fails the npm install.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { install, readMarker, targetDir } from '../lib/installer.js';

if (process.env.npm_config_global !== 'true') {
  process.exit(0);
}

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const { version } = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8'));

try {
  const target = targetDir({ project: false, cwd: process.cwd(), env: process.env, home: os.homedir() });
  const ours = readMarker(target);
  if (fs.existsSync(target) && !ours) {
    console.error(`${target} already exists and was not created by this installer; left it untouched. Run claude-gemini-architect --force to replace it.`);
    process.exit(0);
  }
  const result = await install({
    source: path.join(ROOT, 'skill'),
    target,
    version,
    force: Boolean(ours) && ours.version !== version,
    confirm: null,
  });
  if (result === 'unchanged') {
    console.log(`claude-gemini-architect ${version} is already installed at ${target}`);
  } else if (result === 'updated') {
    console.log(`Updated claude-gemini-architect ${version} at ${target}`);
  } else if (result === 'installed') {
    console.log(`Installed claude-gemini-architect ${version} at ${target}`);
  }
} catch (err) {
  console.error(`claude-gemini-architect: could not install the skill (${err.message}). Run claude-gemini-architect to try again.`);
}
