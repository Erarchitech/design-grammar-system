import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import App from '../src/App.jsx';

window.IS_REACT_ACT_ENVIRONMENT = true;
window.GRAPH_CONFIG = { dataServiceUrl: '/data-service' };
const results = [], calls = [], unexpected = [], errors = [];
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
    check(container.textContent.includes('System initiated'), 'Hero missing');
    check(!container.querySelector('.dgl-host-pill') && !container.querySelector('.dgl-host-centre--visible'), 'Host controls visible before selection');
  });
  await run('PROJECTS click announces selection and immediately shows Russian connecting sphere', async () => {
    allow('/projects', projects);
    const label = [...container.querySelectorAll('.dgl-region-label')].find(e => e.textContent === 'Projects.');
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
    check(container.querySelector('.dgl-host-centre--visible').textContent.includes('Подключение к DG'), 'Russian copy absent');
    check(container.querySelector('.dgl-host-centre-sphere')?.getAttribute('src') === '/dg-think-light.gif' || container.querySelector('.dgl-host-centre-fallback'), 'Sphere and fallback both absent');
    check(!container.querySelector('.dgl-host-pill'), 'Pill appeared before ready');
    await act(async () => resolve(response(200, user))); await tick();
    check(container.querySelector('.dgl-sys')?.textContent.includes('A'), 'Project line missing');
    check(location.search.includes('host=degram') && location.search.includes('lang=ru'), 'Host query lost');
    check(!location.hash, 'Project announcement not cleared');
  });
  await run('Theme change swaps sphere and broken image falls back without network', async () => {
    const toggle = container.querySelector('[title="Switch to dark mode"]'); check(toggle, 'Theme control missing');
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
    await signal('#degram-go=connectors');
    check(container.textContent.includes('Access') && !location.hash, 'Connectors navigation failed');
    await signal('#degram-go=landing');
    check(container.querySelector('.dgl-host-pill'), 'Landing navigation failed');
    await signal('#degram-go=reasoner');
    check(container.querySelector('.dgl-host-pill'), 'Unknown region changed landing');
    await signal('#degram-state=idle');
    check(!container.querySelector('.dgl-host-pill'), 'Idle still shows pill');
    check(location.search.includes('host=degram'), 'Host filter lost');
    check(!unexpected.length && !errors.length && !queue.length, `Unexpected requests/errors ${unexpected.join(', ')} ${errors.join(', ')}; pending ${queue.length}`);
  });
  const output = document.createElement('pre'); output.id = 'offline-results'; output.textContent = JSON.stringify({ results, calls, unexpected, errors }); document.body.append(output);
})().catch(e => { document.body.textContent = `HARNESS_ERROR: ${e.stack}`; });
