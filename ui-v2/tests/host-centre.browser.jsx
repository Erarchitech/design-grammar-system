import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import App from '../src/App.jsx';
import HostCentre from '../src/landing/HostCentre.jsx';
import { setLang } from '../src/i18n/index.js';

window.IS_REACT_ACT_ENVIRONMENT = true;
window.GRAPH_CONFIG = { dataServiceUrl: '/data-service' };
const results = [], calls = [], unexpected = [], errors = [], viewport = [];
const queue = [];
window.addEventListener('error', e => errors.push(e.message));
window.addEventListener('unhandledrejection', e => errors.push(String(e.reason)));
window.addEventListener('securitypolicyviolation', e => { if (e.effectiveDirective !== 'img-src') errors.push(`Forbidden resource: ${e.blockedURI}`); });
const response = (status, body) => new Response(JSON.stringify(body), { status });
window.fetch = async (url, init) => {
  calls.push(`${init.method} ${url}`);
  const index = queue.findIndex(r => r.url === url && r.method === init.method);
  if (index < 0) { unexpected.push(`${init.method} ${url}`); throw new Error('Unmatched network'); }
  const [reply] = queue.splice(index, 1);
  return reply.promise || response(reply.status, reply.body);
};
const allow = (url, body, status = 200) => queue.push({ url: '/data-service' + url, body, status, method: 'GET' });
const check = (ok, why) => { if (!ok) throw new Error(why); };
const tick = () => act(async () => { await new Promise(r => setTimeout(r, 0)); });
const until = async (predicate, why) => { for (let i = 0; i < 40 && !predicate(); i++) await tick(); check(predicate(), why); };
const signal = async hash => {
  await act(async () => { location.hash = hash; window.dispatchEvent(new Event('hashchange')); });
  await tick();
};
async function run(id, fn) { try { await fn(); results.push({ id, status: 'PASS' }); } catch (e) { results.push({ id, status: 'FAIL', error: e.message }); } }
const user = { username: 'synthetic-viewer', email: 'synthetic@example.invalid', name: 'Synthetic Viewer', isAdmin: false, memberships: [{ project: 'A', role: 'viewer' }] };
const projects = { projects: [{ project: 'A', role: 'viewer', nodes: 1 }] };
(async () => {
  localStorage.clear();
  allow('/auth/me', user); allow('/auth/options', { selfRegistration: false });
  allow('/design-rule-sessions/default-project', { sessions: [] });
  allow('/design-rule-sessions/default-project', { sessions: [] });
  const container = document.createElement('div'); container.id = 'root'; document.body.append(container);
  await act(async () => { createRoot(container).render(<App />); }); await tick();
  await run('Host defaults to idle hero and no new-session pill', async () => {
    // D-03: ?lang=ru under host=degram resolves RU, so the owner-fixed boot line is Russian.
    check(container.textContent.includes('Система инициализирована'), 'Hero missing');
    check(container.textContent.includes('Грамматика.') && container.textContent.includes('Граф правил проекта.'), 'RU hero title/subtitle missing');
    check(!container.querySelector('.dgl-host-pill') && !container.querySelector('.dgl-host-centre--visible'), 'Host controls visible before selection');
  });
  await run('DeGram locale signal switches the mounted landing and other screen copy in both directions', async () => {
    check(!container.querySelector('[aria-label="Interface language"]'), 'Browser language dropdown leaked into DeGram');
    await signal('#degram-lang=en');
    check(document.documentElement.lang === 'en' && !location.hash, 'English signal did not update html language');
    check(container.textContent.includes('Design Grammars.') && container.textContent.includes('Encode your design intent.'), 'English landing copy missing');
    await signal('#degram-lang=ru');
    check(document.documentElement.lang === 'ru' && !location.hash, 'Russian signal did not update html language');
    check(container.textContent.includes('Грамматика.') && container.textContent.includes('Граф правил проекта.'), 'Russian landing copy missing');
  });
  await run('PROJECTS click announces selection and immediately shows one caption-less connecting sphere on the ring centre', async () => {
    allow('/projects', projects);
    allow('/projects/A/summary', {});
    allow('/validation/runs/A', { runs: [] });
    const label = [...container.querySelectorAll('.dgl-region-label')].find(e => e.textContent === 'Проекты.');
    check(label, 'Projects callout missing');
    await act(async () => label.click());
    await until(() => [...container.querySelectorAll('span')].some(e => e.textContent === 'A'), 'Project tile missing');
    let resolve;
    allow('/graph/A', { nodes: [], rels: [] });
    allow('/design-rule-sessions/A', { sessions: [] });
    queue.push({ url: '/data-service/auth/me', method: 'GET', promise: new Promise(r => { resolve = r; }) });
    const tile = [...container.querySelectorAll('span')].find(e => e.textContent === 'A');
    await act(async () => tile.click()); await tick();
    check(container.querySelector('.dgl-host-centre--visible'), 'Connecting state waits for membership read');
    // D-47: one caption-less sphere. The state stays announced through role=status + aria-label, not visible text.
    const centre = container.querySelector('.dgl-host-centre--visible');
    check(centre.textContent.trim() === '', `Connecting state has a visible caption: ${centre.textContent}`);
    check(!container.textContent.includes('Подключение к DG'), 'Connecting copy is rendered as visible text');
    check(centre.getAttribute('role') === 'status' && centre.getAttribute('aria-label') === 'Подключение к DG', 'role=status/aria-label (RU) absent');
    check(container.querySelector('.dgl-host-centre-sphere')?.getAttribute('src') === '/dg-think-light.gif' || container.querySelector('.dgl-host-centre-fallback'), 'Sphere and fallback both absent');
    check(!container.querySelector('.dgl-host-pill'), 'Pill appeared before ready');
    // D-47: once the 560 ms entrance has settled the sphere sits on the ring centre (landingEngine: cx = vw/2, cy = vh/2).
    // Headless virtual time does not advance CSS transitions, so the settled geometry is read with transitions off.
    const settle = document.createElement('style'); settle.textContent = '.dgl-host-centre{transition:none !important}'; document.head.append(settle);
    await tick();
    const sphere = container.querySelector('.dgl-host-centre-sphere') || container.querySelector('.dgl-host-centre-fallback');
    const box = sphere.getBoundingClientRect();
    const dx = box.left + box.width / 2 - window.innerWidth / 2, dy = box.top + box.height / 2 - window.innerHeight / 2;
    viewport.push({ width: window.innerWidth, height: window.innerHeight, dx, dy, size: [box.width, box.height] });
    check(box.width > 0 && box.height > 0, 'Sphere has no box');
    check(Math.abs(dx) <= 2 && Math.abs(dy) <= 2, `Sphere centre off the ring centre at ${window.innerWidth}x${window.innerHeight}: dx=${dx.toFixed(2)} dy=${dy.toFixed(2)}`);
    await act(async () => resolve(response(200, user))); await tick();
    check(container.querySelector('.dgl-sys')?.textContent.includes('A'), 'Project line missing');
    check(location.search.includes('host=degram') && location.search.includes('lang=ru'), 'Host query lost');
    check(!location.hash, 'Project announcement not cleared');
  });
  await run('Theme change swaps sphere and broken image falls back without network', async () => {
    const toggle = container.querySelector('[title="Переключить на тёмную тему"]'); check(toggle, 'Theme control missing');
    await act(async () => toggle.click()); await tick();
    check(container.querySelector('.dgl-host-centre-sphere')?.getAttribute('src') === '/dg-think-dark.gif' || container.querySelector('.dgl-host-centre-fallback'), 'Dark sphere/fallback absent');
    const image = container.querySelector('.dgl-host-centre-sphere');
    if (image) await act(async () => image.dispatchEvent(new Event('error')));
    check(container.querySelector('.dgl-host-centre-fallback'), 'Fallback missing');
  });
  await run('ready forms hero and pill; click announces new session', async () => {
    await signal('#degram-state=ready');
    check(!location.hash, 'Host state fragment not cleared');
    check(!container.querySelector('.dgl-host-centre--visible'), 'Connecting sphere persists');
    const pill = container.querySelector('.dgl-host-pill');
    check(pill?.textContent === 'Начать новую сессию' && pill.tagName === 'BUTTON', 'Accessible Russian pill absent');
    await act(async () => pill.click()); await tick();
    check(!location.hash && location.search.includes('lang=ru'), 'New-session fragment/query cleanup failed');
    check(container.querySelector('.dgl-sys')?.textContent.includes('A'), 'Hero did not return');
  });
  await run('host navigation only reaches permitted regions and idle hides pill', async () => {
    allow('/degram/grants/mine', { grants: [] });
    allow('/connectors?project=A', { categories: [], connectors: [] }); // 1301-40: hosted Connectors table reads the project's access
    await signal('#degram-go=connectors');
    check(container.textContent.includes('Доступ') && !location.hash, 'Connectors navigation failed');
    await signal('#degram-lang=en');
    check(document.documentElement.lang === 'en' && container.textContent.includes('Access'), 'English connector screen did not follow the host');
    await signal('#degram-lang=ru');
    check(document.documentElement.lang === 'ru' && container.textContent.includes('Доступ'), 'Russian connector screen did not follow the host');
    allow('/projects/A/summary', {});
    allow('/validation/runs/A', { runs: [] });
    await signal('#degram-go=landing');
    check(container.querySelector('.dgl-host-pill'), 'Landing navigation failed');
    await signal('#degram-go=reasoner');
    check(container.querySelector('.dgl-host-pill'), 'Unknown region changed landing');
    await signal('#degram-state=idle');
    check(!container.querySelector('.dgl-host-pill'), 'Idle still shows pill');
    check(location.search.includes('host=degram'), 'Host filter lost');
    await tick();
    check(!unexpected.length && !errors.length && !queue.length, `Unexpected requests/errors ${unexpected.join(', ')} ${errors.join(', ')}; pending ${queue.length}`);
  });
  await run('English connecting label is on role=status, with no visible caption', async () => {
    const original = location.search;
    allow('/projects/A/summary', {});
    allow('/validation/runs/A', { runs: [] });
    history.replaceState(null, '', location.pathname + '?host=degram&lang=en');
    // The language is a module store now (1308-05); a live host switch reaches it through setLang.
    act(() => setLang('en'));
    const host = document.createElement('div'); document.body.append(host);
    await act(async () => { createRoot(host).render(<HostCentre hostState="connecting" mode="connecting" />); });
    const centre = host.querySelector('.dgl-host-centre--visible');
    history.replaceState(null, '', location.pathname + original);
    check(centre, 'English connecting state absent');
    check(centre.getAttribute('role') === 'status' && centre.getAttribute('aria-label') === 'Connecting to DG', 'role=status/aria-label (EN) absent');
    check(centre.textContent.trim() === '', 'English connecting state has a visible caption');
  });
  const output = document.createElement('pre'); output.id = 'offline-results'; output.textContent = JSON.stringify({ results, calls, unexpected, errors, viewport }); document.body.append(output);
})().catch(e => { document.body.textContent = `HARNESS_ERROR: ${e.stack}`; });
