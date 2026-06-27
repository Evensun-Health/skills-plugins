#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const PLUGIN_NAME = 'hhs-hcc-risk-adjustment';
const CLAUDE_DIR = path.join(os.homedir(), '.claude');

// Skills-directory plugins auto-load — no settings.json patching needed.
// Claude Code discovers any directory under ~/.claude/skills/ that contains
// a .claude-plugin/plugin.json manifest.
const INSTALL_DIR = path.join(CLAUDE_DIR, 'skills', PLUGIN_NAME);

// Package root is one level up from bin/
const SOURCE_DIR = path.join(__dirname, '..');

const TOP_LEVEL_SKIP = new Set([
  'bin', 'node_modules', 'package.json', 'package-lock.json', '.git',
  'scripts', // stale root-level duplicate; real scripts are inside skills/
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

function main() {
  console.log(`\nInstalling ${PLUGIN_NAME}...\n`);

  copyDir(SOURCE_DIR, INSTALL_DIR, true);
  console.log(`  Installed to:\n    ${INSTALL_DIR}`);
  console.log(`\n  Claude Code auto-discovers plugins in ~/.claude/skills/ —`);
  console.log(`  no settings.json changes needed.\n`);

  console.log(`Done. Restart Claude Code (or run /reload-plugins) to activate.\n`);
  console.log(`Slash commands:`);
  console.log(`  /hhs-hcc-risk-adjustment:score    — score an enrollee`);
  console.log(`  /hhs-hcc-risk-adjustment:lookup   — look up a coefficient`);
  console.log(`  /hhs-hcc-risk-adjustment:transfer — compute a risk transfer`);
  console.log(`\nOr just ask Claude a question about the HHS-HCC model directly.\n`);
}

main();
