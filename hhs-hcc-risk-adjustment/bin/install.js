#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const PLUGIN_NAME = 'hhs-hcc-risk-adjustment';
const CLAUDE_DIR = path.join(os.homedir(), '.claude');
const INSTALL_DIR = path.join(CLAUDE_DIR, 'plugins', PLUGIN_NAME);
const SETTINGS_PATH = path.join(CLAUDE_DIR, 'settings.json');

// Package root is one level up from bin/
const SOURCE_DIR = path.join(__dirname, '..');

// Directories/files to skip at the top level of the package
const TOP_LEVEL_SKIP = new Set([
  'bin', 'node_modules', 'package.json', 'package-lock.json',
  '.git', 'scripts', // scripts/ at plugin root is stale; real scripts are in skills/
]);

function copyDir(src, dest, topLevel = false) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    if (entry.name.startsWith('.') && entry.name !== '.claude-plugin') continue;
    if (topLevel && TOP_LEVEL_SKIP.has(entry.name)) continue;
    if (entry.name === 'node_modules' || entry.name === '__pycache__') continue;
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    entry.isDirectory() ? copyDir(s, d) : fs.copyFileSync(s, d);
  }
}

function patchSettings(skillPath) {
  let settings = {};
  if (fs.existsSync(SETTINGS_PATH)) {
    try { settings = JSON.parse(fs.readFileSync(SETTINGS_PATH, 'utf8')); }
    catch { console.warn(`Warning: could not parse ${SETTINGS_PATH} — will create a new one.`); }
  }

  if (!Array.isArray(settings.skills)) settings.skills = [];

  const already = settings.skills.some(
    (s) => (typeof s === 'string' ? s : s?.path) === skillPath
  );

  if (!already) {
    settings.skills.push({ path: skillPath });
    fs.mkdirSync(CLAUDE_DIR, { recursive: true });
    fs.writeFileSync(SETTINGS_PATH, JSON.stringify(settings, null, 2) + '\n', 'utf8');
    return true;
  }
  return false;
}

function main() {
  console.log(`\nInstalling ${PLUGIN_NAME}...\n`);

  copyDir(SOURCE_DIR, INSTALL_DIR, true);
  console.log(`  Files copied to:\n    ${INSTALL_DIR}`);

  // Register the skill subdirectory — this is the path Claude Code loads via settings.json
  const skillPath = path.join(INSTALL_DIR, 'skills', PLUGIN_NAME);
  const added = patchSettings(skillPath);
  if (added) {
    console.log(`  Skill registered in:\n    ${SETTINGS_PATH}`);
  } else {
    console.log(`  Already registered in Claude Code settings — no change needed.`);
  }

  console.log(`
Done. Restart Claude Code (or reload the window) for the skill to take effect.

Slash commands available:
  /hhs-hcc-score    — score an enrollee
  /hhs-hcc-lookup   — look up a coefficient
  /hhs-hcc-transfer — compute a risk transfer

Or just ask Claude a question about the HHS-HCC model directly.
`);
}

main();
