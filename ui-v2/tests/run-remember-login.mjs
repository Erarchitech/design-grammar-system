import { build } from 'esbuild';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const chrome = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(existsSync);
if (!chrome) throw new Error('Installed browser unavailable; no dependency installation permitted');
const temp = mkdtempSync(path.join(tmpdir(), 'dg-remember-login-'));
try {
  const compiled = await build({
    entryPoints: [path.join(root, 'ui-v2/tests/remember-login.browser.jsx')], bundle: true, write: false,
    outfile: path.join(temp, 'bundle.js'), format: 'iife', platform: 'browser',
    define: { 'process.env.NODE_ENV': '"development"', 'import.meta.env.DEV': 'false' }
  });
  const bundle = compiled.outputFiles.find(f => f.path.endsWith('.js')).text.replaceAll('</script', '<\\/script');
  const css = compiled.outputFiles.find(f => f.path.endsWith('.css'))?.text || '';
  const target = path.join(temp, 'index.html');
  writeFileSync(target, `<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src data:"><style>${css}</style><body><script>${bundle}</script></body>`);
  for (const width of [1280, 390]) {
    const result = spawnSync(chrome, ['--headless=new', '--disable-gpu', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-first-run', '--no-default-browser-check', '--host-resolver-rules=MAP * ~NOTFOUND', `--window-size=${width},900`, `--user-data-dir=${path.join(temp, `profile-${width}`)}`, '--virtual-time-budget=12000', '--dump-dom', pathToFileURL(target).href], { encoding: 'utf8', timeout: 60000, maxBuffer: 5 * 1024 * 1024 });
    const match = (result.stdout || '').match(/<pre id="offline-results">([\s\S]*?)<\/pre>/);
    if (!match) throw new Error(`No result DOM: ${result.error?.message || result.stdout?.slice(-1600) || result.stderr?.slice(-800)}`);
    const data = JSON.parse(match[1].replaceAll('&quot;', '"').replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&amp;', '&'));
    console.log(JSON.stringify({ width, ...data }, null, 2));
    if (result.status !== 0 || data.results.length !== 6 || data.results.some(r => r.status !== 'PASS')) process.exitCode = 1;
  }
} finally { rmSync(temp, { recursive: true, force: true }); }
