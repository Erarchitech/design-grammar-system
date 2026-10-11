import { build } from 'esbuild';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, writeFileSync, rmSync, existsSync, readdirSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const chrome = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(existsSync);
if (!chrome) throw new Error('Installed browser unavailable; no dependency installation permitted');
const temp = mkdtempSync(path.join(tmpdir(), 'dg-host-centre-'));
try {
  const compiled = await build({
    entryPoints: [path.join(root, 'ui-v2/tests/host-centre.browser.jsx')], bundle: true, write: false,
    outfile: path.join(temp, 'bundle.js'), format: 'iife', platform: 'browser', loader: { '.woff2': 'dataurl' },
    define: { 'process.env.NODE_ENV': '"development"', 'import.meta.env.DEV': 'false' },
    plugins: [{ name: 'vite-docs-glob', setup(builder) {
      builder.onLoad({ filter: /apidocs[\\/]content[\\/]index\.js$/ }, args => {
        const files = readdirSync(path.dirname(args.path)).filter(f => /^\d\d-.*\.js$/.test(f)).sort();
        const imports = files.map((f, i) => `import * as m${i} from './${f}';`).join('\n');
        const object = '{' + files.map((f, i) => `'./${f}':m${i}`).join(',') + '}';
        return { contents: imports + '\n' + readFileSync(args.path, 'utf8').replace('import.meta.glob("./[0-9][0-9]-*.js", { eager: true })', object), loader: 'js' };
      });
    }}]
  });
  const bundle = compiled.outputFiles.find(f => f.path.endsWith('.js')).text.replaceAll('</script', '<\\/script');
  const css = compiled.outputFiles.find(f => f.path.endsWith('.css'))?.text || '';
  const html = `<!doctype html><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src data:; font-src data:"><style>${css}</style><body><script>${bundle}</script></body>`;
  const target = path.join(temp, 'index.html'); writeFileSync(target, html);
  const url = pathToFileURL(target); url.searchParams.set('host', 'degram'); url.searchParams.set('lang', 'ru');
  const result = spawnSync(chrome, ['--headless=new', '--disable-gpu', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-first-run', '--no-default-browser-check', '--host-resolver-rules=MAP * ~NOTFOUND', `--user-data-dir=${path.join(temp, 'profile')}`, '--virtual-time-budget=12000', '--dump-dom', url.href], { encoding: 'utf8', timeout: 60000, maxBuffer: 5 * 1024 * 1024 });
  const match = (result.stdout || '').match(/<pre id="offline-results">([\s\S]*?)<\/pre>/);
  if (!match) throw new Error(`No result DOM: ${result.error?.message || result.stderr?.slice(-800) || result.stdout?.slice(-800)}`);
  const data = JSON.parse(match[1].replaceAll('&quot;', '"').replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&amp;', '&'));
  console.log(JSON.stringify(data, null, 2));
  if (result.status !== 0 || !data.results.length || data.results.some(r => r.status !== 'PASS')) process.exitCode = 1;
} finally { rmSync(temp, { recursive: true, force: true }); }
