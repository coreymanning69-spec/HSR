#!/usr/bin/env node
/**
 * Unified UI test runner for Hollow Star.
 * Runs Playwright test suites in tests/*-check.cjs sequentially.
 * If port 8765 is not already active, launches an ephemeral web server for the run.
 */
const fs = require('node:fs');
const path = require('node:path');
const { spawn, spawnSync } = require('node:child_process');

const root = path.resolve(__dirname, '..');
const testsDir = path.join(root, 'tests');

const codexPython = 'C:/Users/ACore/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const python = process.env.HSR_PYTHON || (fs.existsSync(codexPython) ? codexPython : 'python');

const args = process.argv.slice(2);
let filter = '';
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--filter' || args[i] === '-f') {
    filter = args[++i] || '';
  } else if (!args[i].startsWith('-')) {
    filter = args[i];
  }
}

// Discover all *-check.cjs test files
const allFiles = fs.readdirSync(testsDir)
  .filter(name => name.endsWith('-check.cjs'))
  .sort();

const targetFiles = filter
  ? allFiles.filter(name => name.toLowerCase().includes(filter.toLowerCase()))
  : allFiles;

if (targetFiles.length === 0) {
  console.error(`No test files matched filter: "${filter}"`);
  process.exit(1);
}

async function isPortOpen(port, host = '127.0.0.1') {
  try {
    const res = await fetch(`http://${host}:${port}/api/health`, { signal: AbortSignal.timeout(1000) });
    return res.ok;
  } catch {
    return false;
  }
}

async function ensureServer() {
  const open = await isPortOpen(8765);
  if (open) {
    return { spawned: false };
  }
  console.log('Starting ephemeral Hollow Star Web Server on 127.0.0.1:8765...');
  const child = spawn(python, [path.join(root, 'hollowstar_web_server.py'), '--port', '8765'], {
    cwd: root,
    stdio: ['ignore', 'pipe', 'pipe']
  });
  let serverLogs = '';
  child.stdout.on('data', d => { serverLogs += d; });
  child.stderr.on('data', d => { serverLogs += d; });

  for (let i = 0; i < 50; i++) {
    if (child.exitCode !== null) {
      throw new Error(`Web server failed to start:\n${serverLogs}`);
    }
    if (await isPortOpen(8765)) {
      return { spawned: true, child };
    }
    await new Promise(r => setTimeout(r, 200));
  }
  throw new Error(`Web server timed out waiting on port 8765:\n${serverLogs}`);
}

(async () => {
  console.log(`\n=== Hollow Star UI Test Suite (${targetFiles.length} files) ===\n`);
  let serverHandle = null;
  try {
    serverHandle = await ensureServer();
  } catch (err) {
    console.error(`Failed to ensure web server: ${err.message}`);
    process.exit(1);
  }

  const results = [];
  let passedCount = 0;
  let failedCount = 0;

  for (let idx = 0; idx < targetFiles.length; idx++) {
    const file = targetFiles[idx];
    const testPath = path.join(testsDir, file);
    const start = Date.now();
    process.stdout.write(`[${idx + 1}/${targetFiles.length}] ${file} ... `);

    const proc = spawnSync(process.execPath, [testPath], {
      cwd: root,
      encoding: 'utf8',
      env: process.env
    });

    const duration = ((Date.now() - start) / 1000).toFixed(2);
    if (proc.status === 0) {
      passedCount++;
      console.log(`PASS (${duration}s)`);
      results.push({ file, ok: true, duration });
    } else {
      failedCount++;
      console.log(`FAIL (${duration}s)`);
      if (proc.stdout) console.error(proc.stdout.trim());
      if (proc.stderr) console.error(proc.stderr.trim());
      results.push({ file, ok: false, duration, output: proc.stderr || proc.stdout });
    }
  }

  if (serverHandle?.spawned && serverHandle.child) {
    console.log('\nShutting down ephemeral web server...');
    try {
      await fetch('http://127.0.0.1:8765/api/host', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ id: 'shutdown', command: 'shutdown' }),
        signal: AbortSignal.timeout(1500)
      }).catch(() => {});
    } catch {}
    if (serverHandle.child.exitCode === null) {
      serverHandle.child.kill();
    }
  }

  console.log('\n------------------------------------------------------------');
  console.log(`Summary: ${passedCount} passed, ${failedCount} failed (${targetFiles.length} total)`);
  console.log('------------------------------------------------------------\n');

  process.exit(failedCount > 0 ? 1 : 0);
})();
