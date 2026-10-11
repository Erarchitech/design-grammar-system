import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import ConnectorsScreen from '../src/screens/ConnectorsScreen.jsx';
import DegramGrantsPanel from '../src/screens/DegramGrantsPanel.jsx';

window.IS_REACT_ACT_ENVIRONMENT = true;
window.GRAPH_CONFIG = { dataServiceUrl: '/data-service' };
const results = [], calls = [], queue = [], unexpected = [];
const reply = (status, body) => new Response(status === 204 ? null : JSON.stringify(body), { status });
window.fetch = async (url, init) => {
  calls.push({ url, init });
  const next = queue.shift();
  if (!next) { unexpected.push(url); throw new Error(`Unexpected request: ${url}`); }
  return next instanceof Promise ? next : reply(...next);
};
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const equal = (actual, expected, message) => assert(JSON.stringify(actual) === JSON.stringify(expected), `${message}: ${JSON.stringify(actual)} != ${JSON.stringify(expected)}`);
const tick = () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
const until = async (predicate, message) => { for (let i = 0; i < 20 && !predicate(); i += 1) await tick(); assert(predicate(), message); };
const button = text => [...host.querySelectorAll('button')].find(b => b.textContent.trim() === text);
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
let root, host;
const owner = { memberships: [{ project: 'A', role: 'owner' }] };
const member = { memberships: [{ project: 'A', role: 'viewer' }] };
const props = { project: 'A', user: member, active: true };
async function render(component) { await act(async () => root.render(component)); }
async function run(id, action) {
  queue.length = 0; calls.length = 0; unexpected.length = 0;
  localStorage.clear(); host = document.createElement('div'); document.body.append(host); root = createRoot(host);
  let error;
  try { await action(); } catch (e) { error = e.message; }
  try { await act(async () => root.unmount()); host.remove(); equal(queue.length, 0, 'Unused responses'); equal(unexpected, [], 'Unexpected requests');
    for (const call of calls) {
      equal(call.init.credentials, 'include', 'Cookie mode');
      equal(call.init.headers['X-DG-CSRF'], ['POST', 'PUT', 'PATCH', 'DELETE'].includes(call.init.method) ? '1' : undefined, 'CSRF marker');
    }
    equal(localStorage.length, 0, 'No grant persisted');
  } catch (e) { error = [error, e.message].filter(Boolean).join('; '); }
  results.push({ id, status: error ? 'FAIL' : 'PASS', ...(error ? { error } : {}) });
}
(async () => {
  await run('GRANTS-member-own-project-only', async () => {
    queue.push([200, { grants: [{ project: 'B', active: true, label: 'Foreign' }, { project: 'A', active: true, label: 'Own', purpose: 'Review' }], requests: [] }]);
    await render(<DegramGrantsPanel {...props} trimmed />); await until(() => host.textContent.includes('Own'), 'Own grant loaded');
    assert(!host.textContent.includes('Foreign'), 'Foreign grant displayed'); assert(!button('Revoke') && !button('Grant access'), 'Admin controls displayed');
    equal(calls.map(c => c.url), ['/data-service/degram/grants/mine'], 'Only own-grants endpoint');
  });
  await run('GRANTS-member-request-pending', async () => {
    queue.push([200, { grants: [], requests: [] }]); await render(<DegramGrantsPanel {...props} />); await until(() => !!button('Request a new token'), 'Request available');
    queue.push([201, { request_id: 'r1' }], [200, { grants: [], requests: [{ project: 'A', status: 'pending' }] }]);
    await act(async () => { button('Request a new token').closest('form').requestSubmit(); }); await until(() => host.textContent.includes('Request sent'), 'Pending state');
    equal(JSON.parse(calls[1].init.body), { project: 'A', note: '' }, 'Request scope'); assert(!button('Request a new token'), 'Request button still offered');
  });
  await run('GRANTS-member-409-existing', async () => {
    queue.push([200, { grants: [], requests: [] }]); await render(<DegramGrantsPanel {...props} />); await until(() => !!button('Request a new token'), 'Request available');
    queue.push([409, { detail: { error: 'Already granted', code: 'GRANT_EXISTS' } }]);
    await act(async () => button('Request a new token').closest('form').requestSubmit()); await until(() => host.textContent.includes('Access already granted'), '409 state');
    assert(!button('Request a new token'), 'Request button still offered after 409');
  });
  await run('GRANTS-owner-issue-revoke', async () => {
    queue.push([200, { grants: [], requests: [{ request_id: 'r1', username: 'member', note: 'Review' }] }], [200, { members: [{ username: 'member' }] }]);
    await render(<DegramGrantsPanel {...props} user={owner} />); await until(() => !!button('Grant'), 'Pending request loaded');
    queue.push([201, { grant_id: 'g1' }], [200, { grants: [{ grant_id: 'g1', active: true, username: 'member', label: 'Review', purpose: 'Review' }], requests: [] }], [200, { members: [{ username: 'member' }] }]);
    await act(async () => button('Grant').click()); await until(() => !!button('Revoke'), 'Issued grant displayed');
    equal(calls[2].url, '/data-service/projects/A/degram-grants', 'Issue project URL'); equal(JSON.parse(calls[2].init.body), { username: 'member', label: 'Review', purpose: 'Review' }, 'Issue fields');
    const savedConfirm = window.confirm; window.confirm = () => true;
    try { queue.push([204, null], [200, { grants: [], requests: [] }], [200, { members: [{ username: 'member' }] }]); await act(async () => button('Revoke').click()); await until(() => !button('Revoke'), 'Revoked grant removed'); }
    finally { window.confirm = savedConfirm; }
    equal(calls[5].url, '/data-service/projects/A/degram-grants/g1', 'Revoke scope'); equal(calls[5].init.method, 'DELETE', 'Revoke method');
  });
  await run('GRANTS-late-project-read-is-ignored', async () => {
    const late = deferred(); queue.push(late.promise);
    await render(<DegramGrantsPanel {...props} />); await until(() => calls.length === 1, 'A request started');
    queue.push([200, { grants: [{ project: 'B', active: true, label: 'B-only' }], requests: [] }]);
    await render(<DegramGrantsPanel {...props} project="B" />); await until(() => host.textContent.includes('B-only'), 'B grant loaded');
    await act(async () => late.resolve(reply(200, { grants: [{ project: 'A', active: true, label: 'A-foreign' }], requests: [] })));
    assert(!host.textContent.includes('A-foreign') && host.textContent.includes('B-only'), 'Stale A grant displaced B');
  });
  if (new URLSearchParams(location.search).get('host') === 'degram') {
    await run('GRANTS-host-screen-no-registry', async () => {
      queue.push([200, { grants: [{ project: 'A', active: true, label: 'Own', purpose: 'Review' }], requests: [] }]);
      await render(<ConnectorsScreen {...props} user={owner} onBack={() => {}} />);
      await until(() => host.textContent.includes('Own'), 'Host own grant loaded');
      assert(!button('Grant access') && !host.textContent.includes('Issued grants'), 'Host owner acquired admin controls');
      assert(!host.textContent.includes('Speckle') && !host.textContent.includes('API keys'), 'Other connector cards shown');
      equal(calls.map(c => c.url), ['/data-service/degram/grants/mine'], 'Host called connector registry');
    });
  } else {
    await run('GRANTS-normal-screen-degram-card', async () => {
      queue.push([200, { categories: ['Integration'], connectors: [{ id: 'degram', name: 'DeGram', category: 'Integration', status: 'connected', credentials: [] }] }]);
      await render(<ConnectorsScreen {...props} user={owner} onBack={() => {}} />);
      await until(() => host.textContent.includes('DeGram'), 'Normal DeGram card loaded');
      queue.push([200, { grants: [], requests: [] }], [200, { members: [{ username: 'member' }] }]);
      await act(async () => [...host.querySelectorAll('span')].find(s => s.textContent === 'DeGram').click());
      await until(() => !!button('Grant access'), 'Owner grant controls on expanded card');
      equal(calls.map(c => c.url), ['/data-service/connectors', '/data-service/projects/A/degram-grants', '/data-service/projects/A/members'], 'Normal grant calls');
      assert(!host.textContent.includes('Pair DeGram'), 'Pairing still offered');
    });
  }
  const output = document.createElement('pre'); output.id = 'offline-results'; output.textContent = JSON.stringify({ results }); document.body.append(output);
})().catch(e => { document.body.textContent = `HARNESS_ERROR: ${e.stack}`; });
