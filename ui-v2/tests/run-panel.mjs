import { build } from 'esbuild';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const out = path.join(root, '.planning/audit-evidence/v12.0-offline-repair/ui');
const label = process.argv[2] || 'panel';
if (!/^[a-z0-9-]+$/.test(label)) throw new Error('Invalid label');
const chrome = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(existsSync);
if (!chrome) throw new Error('No installed browser; do not install dependencies');
const temp = mkdtempSync(path.join(tmpdir(), 'dg-offline-panel-'));
try {
  const compiled = await build({ entryPoints: [path.join(root, 'ui-v2/tests/projects-panel.browser.jsx')], bundle: true, write: false, format: 'iife', platform: 'browser', define: { 'process.env.NODE_ENV': '"development"' }, metafile: true });
  const bundle = compiled.outputFiles[0].text.replaceAll('</script', '<\\/script');
  const html = '<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'unsafe-inline\'; style-src \'unsafe-inline\'; connect-src \'none\'; img-src data:"><body><script>' + bundle + '</script></body>';
  const target = path.join(temp, 'index.html'); writeFileSync(target, html);
  const args = ['--headless=new', '--disable-gpu', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-first-run', '--no-default-browser-check', '--host-resolver-rules=MAP * ~NOTFOUND', `--user-data-dir=${path.join(temp, 'profile')}`, '--virtual-time-budget=8000', '--dump-dom', pathToFileURL(target).href];
  const result = spawnSync(chrome, args, { encoding: 'utf8', timeout: 60000, maxBuffer: 4 * 1024 * 1024 });
  writeFileSync(path.join(out, `${label}.dom.html`), result.stdout || ''); writeFileSync(path.join(out, `${label}.stderr.log`), result.stderr || '');
  const match = (result.stdout || '').match(/<pre id="offline-results">([\s\S]*?)<\/pre>/);
  const data = match ? JSON.parse(match[1].replaceAll('&quot;', '"').replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&amp;', '&')) : { results: [], harness_error: result.error?.message || 'No result DOM; inspect retained DOM/stderr' };
  const exit = result.status === 0 && data.results.length && data.results.every(r => r.status === 'PASS') ? 0 : 1;
  const sources = Object.keys(compiled.metafile.inputs).map(p => path.relative(root, path.resolve(p)).replaceAll('\\', '/')).filter(p => p.startsWith('ui-v2/src/')).sort();
  if (new Set(data.results.map(r => r.id)).size !== data.results.length) throw new Error('Duplicate panel test identities');
  const testPaths = ['ui-v2/tests/projects-panel.browser.jsx', 'ui-v2/tests/run-panel.mjs'];
  const evidence = { gap: 'NQ-1205-03', ...data, command: ['node', 'ui-v2/tests/run-panel.mjs', label], browser_command: [chrome, ...args], browser_exit_code: result.status, exit_code: exit, tests: data.results, test_count: data.results.length, passed: data.results.filter(r => r.status === 'PASS').length, failed: data.results.filter(r => r.status === 'FAIL').length, source_paths: sources, source_paths_meaning: 'Bundler inputs, not a claim that every barrel-exported component was exercised', test_paths: testPaths, sha256: Object.fromEntries([...sources, ...testPaths].map(p => [p, createHash('sha256').update(readFileSync(path.join(root, p))).digest('hex')])), dependency_versions: Object.fromEntries(['react', 'react-dom', 'esbuild'].map(name => [name, JSON.parse(readFileSync(path.join(root, 'ui-v2/node_modules', name, 'package.json'), 'utf8')).version])), network: 'File URL, bundled installed deps, CSP connect-src none, finite fake fetch, isolated disposable browser profile; no server or live API' };
  writeFileSync(path.join(out, `${label}.json`), JSON.stringify(evidence, null, 2) + '\n'); console.log(JSON.stringify({ command: evidence.command, exit_code: exit, test_count: evidence.test_count, passed: evidence.passed, failed: evidence.failed, tests: evidence.tests }, null, 2)); process.exitCode = exit;
} finally { rmSync(temp, { recursive: true, force: true }); }
