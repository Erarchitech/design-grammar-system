import { build } from 'esbuild';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mkdtempSync, writeFileSync, readFileSync, rmSync, existsSync, readdirSync, mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

// Same installed-browser/file-URL strategy as run-panel.mjs; no server or install.
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const scratch = process.env.TMPDIR || 'C:/Users/Admin/AppData/Local/hermes/cache/scratch';
mkdirSync(scratch, { recursive: true });
const temp = mkdtempSync(path.join(scratch, 'degram-offline-'));
const chrome = ['C:/Program Files/Google/Chrome/Application/chrome.exe', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'].find(existsSync);
if (!chrome) throw new Error('Installed browser unavailable; no dependency installation permitted');
try {
  const compiled = await build({
    entryPoints: [path.join(root, 'ui-v2/tests/degram.browser.jsx')], bundle: true, write: false,
    outfile: path.join(temp, 'bundle.js'), format: 'iife', platform: 'browser', metafile: true,
    loader: { '.woff2': 'dataurl' },
    define: { 'process.env.NODE_ENV': '"development"', 'import.meta.env.DEV': 'false' },
    plugins: [{ name: 'vite-docs-glob', setup(builder) {
      // Expand only the existing Vite build macro, not application behavior.
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
  const args = ['--headless=new', '--disable-gpu', '--disable-background-networking', '--disable-component-update', '--disable-sync', '--no-first-run', '--no-default-browser-check', '--host-resolver-rules=MAP * ~NOTFOUND', `--user-data-dir=${path.join(temp, 'profile')}`, '--virtual-time-budget=18000', '--dump-dom', pathToFileURL(target).href];
  const result = spawnSync(chrome, args, { encoding: 'utf8', timeout: 60000, maxBuffer: 8 * 1024 * 1024 });
  const match = (result.stdout || '').match(/<pre id="offline-results">([\s\S]*?)<\/pre>/);
  const data = match ? JSON.parse(match[1].replaceAll('&quot;', '"').replaceAll('&lt;', '<').replaceAll('&gt;', '>').replaceAll('&amp;', '&')) : { results: [], harness_error: result.error?.message || 'No result DOM' };
  const passed = data.results.filter(r => r.status === 'PASS').length;
  const evidence = { proof: 'offline actual application/ReactDOM, synthetic matched API responses, no live service', ...data, passed, failed: data.results.length - passed, browser_exit_code: result.status, sources: Object.keys(compiled.metafile.inputs).filter(p => p.replaceAll('\\', '/').includes('ui-v2/src/')) };
  evidence.sources_meaning = 'Bundler inputs, not executed-module coverage; normal App is bundled by this test macro but never mounted on #degram';
  evidence.command = 'node ui-v2/tests/run-degram.mjs';
  evidence.browser = chrome;
  const tracked = [...evidence.sources, 'ui-v2/tests/degram.browser.jsx', 'ui-v2/tests/run-degram.mjs'];
  evidence.sha256 = Object.fromEntries(tracked.map(p => [p, createHash('sha256').update(readFileSync(path.join(root, p))).digest('hex')]));
  evidence.dependencies = Object.fromEntries(['react', 'react-dom', 'esbuild'].map(p => [p, JSON.parse(readFileSync(path.join(root, 'ui-v2/node_modules', p, 'package.json'), 'utf8')).version]));
  const label = process.argv[2] || 'latest';
  if (!/^[a-z0-9-]+$/.test(label)) throw new Error('Invalid evidence label');
  const out = path.join(root, 'ui-v2/tests/evidence'); mkdirSync(out, { recursive: true });
  writeFileSync(path.join(out, `degram-${label}.json`), JSON.stringify(evidence, null, 2) + '\n');
  if (!match) writeFileSync(path.join(out, `degram-${label}.failure.txt`), (result.stdout || '') + '\n' + result.stderr);
  console.log(JSON.stringify({ results: data.results, passed, failed: evidence.failed, unexpected: data.unexpected, errors: data.errors }, null, 2));
  process.exitCode = result.status === 0 && data.results.length > 0 && passed === data.results.length ? 0 : 1;
} finally { rmSync(temp, { recursive: true, force: true }); }
