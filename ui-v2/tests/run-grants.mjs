import { build } from 'esbuild';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const chrome = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(existsSync);
if (!chrome) throw new Error('Installed browser unavailable; no dependency installation permitted');
const temp = mkdtempSync(path.join(tmpdir(), 'dg-grants-offline-'));
try {
  const compiled = await build({ entryPoints: [path.join(root, 'ui-v2/tests/degram-grants.browser.jsx')], bundle: true, write: false, outfile: path.join(temp, 'bundle.js'), format: 'iife', platform: 'browser', loader: { '.woff2': 'dataurl' }, define: { 'process.env.NODE_ENV': '"development"' } });
  const bundle = compiled.outputFiles.find(f => f.path.endsWith('.js')).text.replaceAll('</script', '<\\/script');
  const css = compiled.outputFiles.find(f => f.path.endsWith('.css'))?.text || '';
  const html = `<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src data:; font-src data:"><style>${css}</style><body><script>${bundle}</script></body>`;
  const target = path.join(temp, 'index.html'); writeFileSync(target, html);
  const url = pathToFileURL(target); if (process.argv[2] === 'host') url.searchParams.set('host', 'degram');
  const result = spawnSync(chrome, ['--headless=new', '--disable-gpu', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-first-run', '--no-default-browser-check', '--host-resolver-rules=MAP * ~NOTFOUND', `--user-data-dir=${path.join(temp, 'profile')}`, '--virtual-time-budget=12000', '--dump-dom', url.href], { encoding: 'utf8', timeout: 60000, maxBuffer: 4 * 1024 * 1024 });
  const match = (result.stdout || '').match(/<pre id="offline-results">([\s\S]*?)<\/pre>/);
  if (!match) throw new Error(`No result DOM: ${result.error?.message || result.stderr?.slice(-500) || result.stdout?.slice(-500)}`);
  const data = JSON.parse(match[1].replaceAll('&quot;', '"').replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&amp;', '&'));
  console.log(JSON.stringify(data, null, 2));
  if (result.status !== 0 || !data.results.length || data.results.some(r => r.status !== 'PASS')) process.exitCode = 1;
} finally { rmSync(temp, { recursive: true, force: true }); }
