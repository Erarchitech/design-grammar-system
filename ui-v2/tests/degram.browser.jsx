import React, { act } from 'react';
import GraphEngine from '../src/graph/graphEngine.js';
// Chrome virtual time may starve RAF. Retain the real engine and drive one
// real frame explicitly; no canvas/renderer methods are mocked.
let activeEngine;
const originalStart = GraphEngine.prototype.start;
GraphEngine.prototype.start = function (...args) { activeEngine = this; return originalStart.apply(this, args); };
const results = [], calls = [], unexpected = [], queue = [], errors = [];
window.IS_REACT_ACT_ENVIRONMENT = true;
window.GRAPH_CONFIG = { dataServiceUrl: '/data-service' };
window.addEventListener('error', e => errors.push(e.message));
window.addEventListener('unhandledrejection', e => errors.push(String(e.reason)));
window.addEventListener('securitypolicyviolation', e => errors.push(`Forbidden resource: ${e.blockedURI}`));
const response = (status, body) => new Response(status === 204 ? null : JSON.stringify(body), { status });
window.fetch = async (url, init) => {
  calls.push({ url, method: init.method, credentials: init.credentials, headers: init.headers });
  const i = queue.findIndex(r => r.url === url && r.method === init.method);
  if (i < 0) { unexpected.push(`${init.method} ${url}`); throw new Error('Forbidden unmatched network'); }
  const [reply] = queue.splice(i, 1);
  return reply.promise || response(reply.status, reply.body);
};
const allow = (url, body, status = 200, method = 'GET') => queue.push({ url: '/data-service' + url, body, status, method });
const check = (ok, why) => { if (!ok) throw new Error(why); };
const equal = (a, b, why) => check(JSON.stringify(a) === JSON.stringify(b), `${why}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`);
const tick = () => act(async () => { await new Promise(r => setTimeout(r, 0)); });
const until = async (predicate, why) => { for (let i = 0; i < 35 && !predicate(); i++) await tick(); check(predicate(), why); };
const button = label => [...document.querySelectorAll('#root button')].find(b => b.textContent === label);
const click = async label => { check(button(label), `Missing button ${label}`); await act(async () => button(label).click()); await tick(); };
const text = () => document.getElementById('root').textContent;
const me = { username: 'synthetic-viewer', isAdmin: false, memberships: [{ project: 'A', role: 'viewer' }, { project: 'B', role: 'viewer' }] };
const projects = { projects: [{ project: 'A', role: 'viewer', nodes: 1 }, { project: 'B', role: 'viewer', nodes: 1 }] };
const graph = name => ({ nodes: [{ id: name, labels: ['Class'], props: { graph: 'OntoGraph', label: name, height: 75 } }], rels: [] });
async function run(id, fn) { try { await fn(); results.push({ id, status: 'PASS' }); } catch (e) { results.push({ id, status: 'FAIL', error: e.message }); } }
(async () => {
  localStorage.clear(); localStorage.setItem('dgv2_project', 'REMEMBERED-UNAUTHORIZED');
  window.location.hash = '#degram';
  const host = document.createElement('div'); host.id = 'root'; document.body.append(host);
  await run('DG-01 dedicated entry resolves session, selects explicitly, renders and inspects real graph', async () => {
    allow('/auth/me', me); allow('/projects', projects);
    await act(async () => { await import('../src/main.jsx'); }); await tick();
    check(text().includes('DeGram'), 'Dedicated DeGram entry missing (normal App must not mount)');
    equal(calls.map(c => c.url), ['/data-service/auth/me', '/data-service/projects'], 'Only session and projects before selection');
    check(text().includes('Select a project'), 'Explicit selection required');
    check(!document.querySelector('#root canvas'), 'No graph before selection');
    allow('/graph/A', graph('A-node')); await click('A');
    await until(() => button('A-node'), 'Graph node listed');
    check(document.querySelector('canvas[aria-label="Project graph"]'), 'Shared canvas mounted');
    await click('A-node'); check(text().includes('75'), 'Read-only properties inspected');
    check(!document.querySelector('#root input, #root textarea, #root [contenteditable=true]'), 'No property/prompt editor');
    equal(unexpected, [], 'No forbidden background API calls');
    equal(errors, [], 'No browser errors');
  });
  await run('DG-02 switch clears old graph immediately and rejects late previous-project response', async () => {
    let resolve;
    const promise = new Promise(r => { resolve = r; });
    queue.push({ url: '/data-service/graph/B', method: 'GET', promise });
    await click('B');
    check(!text().includes('A-node') && !document.querySelector('#root canvas'), 'Old graph removed during switch');
    check(text().includes('Loading graph'), 'Loading state visible');
    allow('/graph/A', graph('A-current')); await click('A'); await until(() => button('A-current'), 'Current A loaded');
    await act(async () => resolve(response(200, graph('B-STALE')))); await tick();
    check(!text().includes('B-STALE') && button('A-current'), 'Late B response replaced current A');
  });
  await run('DG-03 logout clears context immediately and rejects pending graph', async () => {
    let resolve;
    queue.push({ url: '/data-service/graph/B', method: 'GET', promise: new Promise(r => { resolve = r; }) });
    await click('B');
    allow('/auth/logout', null, 204, 'POST'); await click('Sign out');
    check(!button('A') && !button('B') && !document.querySelector('#root canvas'), 'Logout clears all read context');
    check(!localStorage.getItem('dgv2_project'), 'Logout clears remembered tenant context');
    await act(async () => resolve(response(200, graph('AFTER-LOGOUT')))); await tick();
    check(!text().includes('AFTER-LOGOUT'), 'Late graph resurrected after logout');
    check(text().includes('Sign in to DeGram'), 'Signed-out state visible');
  });
  await run('DG-04 sign in uses existing cookie/CSRF flow and never stores credentials', async () => {
    const form = document.querySelector('#root form'); check(form, 'Existing auth transport sign-in form required');
    for (const [name, value] of [['username', 'synthetic-viewer'], ['password', 'TEST-ONLY-NOT-A-CREDENTIAL']]) {
      const input = form.elements.namedItem(name);
      await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, value); input.dispatchEvent(new Event('input', { bubbles: true })); });
    }
    allow('/auth/login', { username: me.username }, 200, 'POST'); allow('/auth/me', me); allow('/projects', projects);
    await act(async () => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))); await tick();
    await until(() => button('A'), 'Projects available after sign-in');
    check(!document.querySelector('#root input[type=password]'), 'Password form discarded');
    equal(localStorage.length, 0, 'No credential or graph persisted');
    check(text().includes('Select a project'), 'No project auto-selected after sign-in');
  });
  await run('DG-05 access refresh revokes project and invalidates pending graph', async () => {
    allow('/graph/A', graph('A-before-revoke')); await click('A');
    let resolve;
    queue.push({ url: '/data-service/graph/B', method: 'GET', promise: new Promise(r => { resolve = r; }) });
    await click('B');
    allow('/auth/me', { ...me, memberships: [] }); allow('/projects', { projects: [] });
    await click('Refresh access');
    check(!button('A') && !button('B') && !document.querySelector('#root canvas'), 'Revocation clears project/graph');
    check(text().includes('No accessible projects'), 'No projects message');
    await act(async () => resolve(response(200, graph('REVOKED-LATE')))); await tick();
    check(!text().includes('REVOKED-LATE'), 'Revoked graph resurrected');
    allow('/auth/me', me); allow('/projects', projects); await click('Refresh access');
    check(text().includes('Select a project'), 'Refresh never restores selection');
  });
  for (const code of [403, 401]) await run(`DG-06-${code} denial discards graph, projects and pending reads`, async () => {
    allow('/graph/A', graph('PRIVATE-BEFORE-DENIAL')); await click('A');
    allow('/graph/B', { detail: 'SYNTHETIC-DENIED-BODY-MUST-NOT-RENDER' }, code); await click('B');
    check(!document.querySelector('#root canvas') && !button('A') && !button('B'), 'Denied scope removed');
    check(!text().includes('PRIVATE-BEFORE-DENIAL') && !text().includes('SYNTHETIC-DENIED-BODY'), 'No old graph or server body');
    check(text().includes(code === 401 ? 'Sign in to DeGram' : 'Access denied'), 'Explicit denial state');
    allow('/auth/me', me); allow('/projects', projects); await click('Refresh access');
  });
  await run('DG-07 empty graph is explicit and offers no empty canvas', async () => {
    allow('/graph/A', { nodes: [], rels: [] }); await click('A');
    check(text().includes('This project has no graph nodes'), 'Empty graph state missing');
    check(!document.querySelector('#root canvas'), 'No misleading blank canvas');
  });
  await run('DG-08 inspection removes provider/model/key metadata including nested JSON', async () => {
    const data = graph('Metadata-node');
    Object.assign(data.nodes[0].props, { provider: 'HIDDEN-PROVIDER', model: 'HIDDEN-MODEL', api_key: 'HIDDEN-KEY', provenance: { providerName: 'HIDDEN-NESTED', safe: 'retained' }, statePayloadJson: JSON.stringify({ model_id: 'HIDDEN-JSON', height: 80 }) });
    allow('/graph/A', data); await click('A'); await click('Metadata-node');
    check(!text().includes('HIDDEN-'), 'Restricted metadata leaked through inspector');
    check(text().includes('retained') && text().includes('80'), 'Non-sensitive properties retained');
    check(!document.querySelector('#root img'), 'Read-only renderer must not load unused thinking assets');
  });
  await run('DG-09 service failures hide previous graph and project denial is explicit', async () => {
    allow('/graph/B', { detail: 'HIDDEN-PROVIDER-ERROR' }, 503); await click('B');
    check(text().includes('Graph unavailable') && !document.querySelector('#root canvas'), 'Graph unavailable and cleared');
    check(!text().includes('Metadata-node') && !text().includes('HIDDEN-PROVIDER'), 'No stale data/error payload');
    allow('/auth/me', me); allow('/projects', { detail: 'Forbidden projects' }, 403); await click('Refresh access');
    check(text().includes('Access denied') && !button('A'), 'Project-list access denial explicit');
    allow('/auth/me', { detail: 'unavailable' }, 503); await click('Refresh access');
    check(text().includes('Service unavailable'), 'Session transport failure explicit');
    allow('/auth/me', me); allow('/projects', projects); await click('Refresh access');
  });
  await run('DG-10 late sign-in project list cannot resurrect after logout', async () => {
    allow('/auth/logout', null, 204, 'POST'); await click('Sign out');
    const form = document.querySelector('#root form');
    form.elements.username.value = 'synthetic-viewer'; form.elements.password.value = 'SYNTHETIC-ONLY';
    allow('/auth/login', { username: me.username }, 200, 'POST'); allow('/auth/me', me);
    let resolve;
    queue.push({ url: '/data-service/projects', method: 'GET', promise: new Promise(r => { resolve = r; }) });
    await act(async () => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))); await tick();
    allow('/auth/logout', null, 204, 'POST'); await click('Sign out');
    await act(async () => resolve(response(200, projects))); await tick();
    check(!button('A') && !button('B'), 'Late sign-in projects resurrected after logout');
    allow('/auth/me', me); allow('/projects', projects); await click('Refresh access');
  });
  await run('DG-11 failed logout clears data and offers retry without silently re-entering session', async () => {
    allow('/graph/A', graph('LOGOUT-PRIVATE')); await click('A');
    allow('/auth/logout', { detail: 'unavailable' }, 503, 'POST'); await click('Sign out');
    check(!button('A') && !document.querySelector('#root canvas') && !text().includes('LOGOUT-PRIVATE'), 'Failed logout clears data');
    check(text().includes('Server sign-out unavailable'), 'Server logout failure disclosed');
    check(button('Retry sign-out'), 'Failed logout must be retryable');
    check(!button('Refresh access') && !document.querySelector('#root form'), 'Do not resume session while logout unconfirmed');
    allow('/auth/logout', null, 204, 'POST'); await click('Retry sign-out');
    check(text().includes('Sign in to DeGram'), 'Retry completes sign-out');
    allow('/auth/me', me); allow('/projects', projects); await click('Refresh access');
  });
  await run('DG-12 returning to workspace rechecks access and clears revoked graph', async () => {
    allow('/graph/A', graph('FOCUS-PRIVATE')); await click('A');
    allow('/auth/me', me); allow('/projects', { projects: [] });
    await act(async () => window.dispatchEvent(new Event('focus'))); await tick();
    check(!text().includes('FOCUS-PRIVATE') && !document.querySelector('#root canvas'), 'Focus must invalidate old graph');
    check(text().includes('No accessible projects'), 'Focus refreshed project access');
    allow('/auth/me', me); allow('/projects', projects); await click('Refresh access');
  });
  await run('DG-13 untagged graph nodes remain inspectable without inventing a graph layer', async () => {
    allow('/graph/A', { nodes: [{ id: 'untagged', labels: ['Class'], props: { label: 'Untagged node', height: 42 } }], rels: [] }); await click('A');
    check(button('Untagged node'), 'Untagged node missing from accessible node list');
    await click('Untagged node'); check(text().includes('42'), 'Untagged properties inspectable');
    check(text().includes('not placed on graph rings'), 'Missing graph layer disclosed');
  });
  await run('DG-14 expiry rejects late project-list and graph reads', async () => {
    let resolveProjects;
    allow('/auth/me', me);
    queue.push({ url: '/data-service/projects', method: 'GET', promise: new Promise(r => { resolveProjects = r; }) });
    await click('Refresh access');
    await act(async () => window.dispatchEvent(new CustomEvent('dg-auth-expired')));
    await act(async () => resolveProjects(response(200, projects))); await tick();
    check(!button('A') && !button('Sign out'), 'Late project list ignored after expiry');
    allow('/auth/me', me); allow('/projects', projects); await click('Refresh access');
    let resolveGraph;
    queue.push({ url: '/data-service/graph/A', method: 'GET', promise: new Promise(r => { resolveGraph = r; }) }); await click('A');
    await act(async () => window.dispatchEvent(new CustomEvent('dg-auth-expired')));
    await act(async () => resolveGraph(response(200, graph('EXPIRED-GRAPH')))); await tick();
    check(!text().includes('EXPIRED-GRAPH') && !document.querySelector('#root canvas'), 'Late graph ignored after expiry');
  });
  await run('DG-15 pending sign-in prevents duplicate submit and ignores late auth after expiry', async () => {
    const form = document.querySelector('#root form');
    form.elements.username.value = 'synthetic-viewer'; form.elements.password.value = 'SYNTHETIC-ONLY';
    let resolveLogin;
    queue.push({ url: '/data-service/auth/login', method: 'POST', promise: new Promise(r => { resolveLogin = r; }) });
    await act(async () => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))); await tick();
    check(button('Sign in')?.disabled, 'Pending login must disable duplicate submit');
    await act(async () => window.dispatchEvent(new CustomEvent('dg-auth-expired')));
    allow('/auth/me', me);
    await act(async () => resolveLogin(response(200, { username: me.username }))); await tick();
    check(!button('A') && !button('Sign out'), 'Late authentication cannot resurrect expired view');
  });
  for (const role of ['owner', 'admin']) await run(`DG-16-${role} privileged identity still gets only reading controls`, async () => {
    allow('/auth/me', { ...me, isAdmin: role === 'admin' });
    allow('/projects', { projects: [{ project: 'A', role: 'owner' }] }); await click('Refresh access');
    allow('/graph/A', graph('Privileged-node')); await click('A'); await click('Privileged-node');
    check(!document.querySelector('#root input, #root textarea, #root [contenteditable=true], #root a'), 'No editor, prompts, settings or connector escape');
    equal([...document.querySelectorAll('#root button')].map(b => b.textContent).sort(), ['A', 'Privileged-node', 'Refresh access', 'Sign out'].sort(), 'Bounded controls for privileged users');
    // Exercise the shared engine frame, not just a stub canvas element.
    activeEngine.drawGraph(); activeEngine.placeGraphDOM();
    const canvas = document.querySelector('#root canvas');
    const pixels = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
    check(pixels.some((value, i) => i % 4 === 3 && value > 0), 'Actual graph canvas painted');
  });
  await run('DG-18 late session identity cannot restore a logged-out workspace', async () => {
    let resolve;
    queue.push({ url: '/data-service/auth/me', method: 'GET', promise: new Promise(r => { resolve = r; }) });
    await click('Refresh access');
    allow('/auth/logout', null, 204, 'POST'); await click('Sign out');
    await act(async () => resolve(response(200, me))); await tick();
    check(!button('A') && !button('Sign out'), 'Late currentUser ignored');
  });
  await run('DG-19 rejected login clears password and never starts project read', async () => {
    const form = document.querySelector('#root form');
    form.elements.username.value = 'synthetic-viewer'; form.elements.password.value = 'SYNTHETIC-REJECTED';
    const before = calls.length;
    allow('/auth/login', { detail: 'HIDDEN-SERVER-ERROR' }, 401, 'POST');
    await act(async () => form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }))); await tick();
    equal(calls.length, before + 1, 'Only login attempted');
    check(!text().includes('HIDDEN-SERVER-ERROR'), 'Raw login error hidden');
    equal(document.querySelector('input[type=password]').value, '', 'Password cleared on denial');
    check(!button('A'), 'No projects after rejected login');
  });
  await run('DG-20 empty session requires explicit sign-in and no projects call', async () => {
    const before = calls.length;
    allow('/auth/me', null); await click('Refresh access');
    equal(calls.length, before + 1, 'No projects without session');
    check(text().includes('Sign in to DeGram') && document.querySelector('#root form'), 'Signed-out session recovery');
  });
  await run('DG-17 finite network allowlist, cookie transport and zero errors across complete flow', async () => {
    equal(unexpected, [], 'Forbidden unmatched network'); equal(queue.length, 0, 'All explicit replies consumed'); equal(errors, [], 'Browser runtime errors');
    for (const call of calls) {
      check((call.method === 'GET' && /^\/data-service\/(auth\/me|projects|graph\/[AB])$/.test(call.url)) || (call.method === 'POST' && /^\/data-service\/auth\/(login|logout)$/.test(call.url)), 'Forbidden endpoint or graph mutation');
      equal(call.credentials, 'include', 'Cookie session'); equal(call.headers['X-DG-CSRF'], call.method === 'POST' ? '1' : undefined, 'Shared CSRF transport');
      check(!Object.keys(call.headers).some(k => /authorization|cookie/i.test(k)), 'No credential headers');
    }
    equal(localStorage.length, 0, 'No graph, selection or credential storage');
  });
  const output = document.createElement('pre'); output.id = 'offline-results'; output.textContent = JSON.stringify({ results, calls, unexpected, errors }); document.body.append(output);
})().catch(e => { document.body.textContent = `HARNESS_ERROR: ${e.stack}`; });
