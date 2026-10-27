#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import readline from 'node:readline/promises';
import { fileURLToPath } from 'node:url';
import { HELP, parseArgs, UsageError } from '../lib/args.js';
import { InstallError, install, targetDir, uninstall, findBackups } from '../lib/installer.js';
import { checkRequirements } from '../lib/requirements.js';

const ROOT = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const { version } = JSON.parse(fs.readFileSync(path.join(ROOT, 'package.json'), 'utf8'));

const useColor = Boolean(process.stdout.isTTY) && !('NO_COLOR' in process.env);
const paint = (code, text) => (useColor ? `\x1b[${code}m${text}\x1b[0m` : text);
const red = (t) => paint(31, t);
const green = (t) => paint(32, t);
const yellow = (t) => paint(33, t);

function printRequirements(reqs) {
  for (const r of reqs) {
    if (r.found) console.log(`${green('✓')} ${r.cmd}`);
    else if (r.level === 'required') console.log(`${red('✗')} ${r.cmd} not found: ${r.why}`);
    else console.log(`${yellow('!')} ${r.cmd} not found (optional): ${r.why}`);
  }
}

async function ask(question) {
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  try {
    return /^y(es)?$/i.test((await rl.question(question)).trim());
  } finally {
    rl.close();
  }
}

async function main(argv) {
  let opts;
  try {
    opts = parseArgs(argv);
  } catch (err) {
    if (err instanceof UsageError) {
      console.error(`${err.message}\n\n${HELP}`);
      return 2;
    }
    throw err;
  }
  if (opts.help) {
    console.log(HELP);
    return 0;
  }
  if (opts.version) {
    console.log(version);
    return 0;
  }
  const reqs = checkRequirements(process.env, process.platform);
  if (opts.check) {
    printRequirements(reqs);
    return reqs.some((r) => r.level === 'required' && !r.found) ? 1 : 0;
  }
  const target = targetDir({ project: opts.project, cwd: process.cwd(), env: process.env, home: os.homedir() });
  if (opts.uninstall) {
    const result = uninstall({ target, force: opts.force });
    console.log(result === 'removed' ? `Removed ${target}` : `Not installed at ${target}`);
    return 0;
  }
  printRequirements(reqs);
  if (process.platform === 'win32') console.log(yellow('Windows: the skill scripts need WSL (agy and herdr are Unix tools).'));
  const confirm = process.stdin.isTTY && process.stdout.isTTY ? ask : null;
  const result = await install({ source: path.join(ROOT, 'skill'), target, version, force: opts.force, confirm });
  if (result === 'unchanged') {
    console.log(`claude-gemini-architect ${version} is already installed at ${target}`);
    return 0;
  }
  if (result === 'aborted') {
    console.log('Nothing changed.');
    return 0;
  }
  console.log(green(`${result === 'updated' ? 'Updated' : 'Installed'} claude-gemini-architect ${version} at ${target}`));
  for (const b of findBackups(target)) {
    console.log(`Note: a backup of a previous installation is at ${b}; delete it when you no longer need it.`);
  }
  const mode = process.env.HERDR_ENV === '1'
    ? 'herdr mode (Gemini in a pane next to Claude)'
    : 'terminal mode (Gemini edits files, Claude runs the commands)';
  console.log(`\nNext: open Claude Code and type /claude-gemini-architect\nDetected: ${mode}`);
  return 0;
}

main(process.argv.slice(2)).then(
  (code) => {
    process.exitCode = code;
  },
  (err) => {
    console.error(red(err instanceof InstallError ? err.message : `error: ${err.message}`));
    process.exitCode = 1;
  },
);
