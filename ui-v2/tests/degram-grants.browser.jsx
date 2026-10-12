import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import ConnectorsScreen from '../src/screens/ConnectorsScreen.jsx';
import DegramGrantsPanel from '../src/screens/DegramGrantsPanel.jsx';
import { setLang } from '../src/i18n/index.js';
import { eligibleGrantMembers } from '../src/screens/ConnectorsScreen.jsx';

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
  localStorage.clear(); setLang('en'); host = document.createElement('div'); document.body.append(host); root = createRoot(host);
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
    queue.push([200, { grants: [], requests: [] }]); await render(<DegramGrantsPanel {...props} />); await until(() => !!button('Request access'), 'Request available');
    queue.push([201, { request_id: 'r1' }], [200, { grants: [], requests: [{ project: 'A', status: 'pending' }] }]);
    await act(async () => { button('Request access').closest('form').requestSubmit(); }); await until(() => host.textContent.includes('Request sent'), 'Pending state');
    equal(JSON.parse(calls[1].init.body), { project: 'A', note: '' }, 'Request scope'); assert(!button('Request access'), 'Request button still offered');
  });
  await run('GRANTS-member-409-existing', async () => {
    queue.push([200, { grants: [], requests: [] }]); await render(<DegramGrantsPanel {...props} />); await until(() => !!button('Request access'), 'Request available');
    queue.push([409, { detail: { error: 'Already granted', code: 'GRANT_EXISTS' } }]);
    await act(async () => button('Request access').closest('form').requestSubmit()); await until(() => host.textContent.includes('Access already granted'), '409 state');
    assert(!button('Request access'), 'Request button still offered after 409');
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
  const registry = (access) => [200, { categories: ['VPL Platforms', 'BIM Authoring', 'Agents'], connectors: [
    { id: 'grasshopper', name: 'Grasshopper', category: 'VPL Platforms', status: 'active', last_connection: null, active_sessions: 1, access: access.grasshopper },
    { id: 'revit', name: 'Revit', category: 'BIM Authoring', status: 'never_connected', last_connection: null, active_sessions: 0, access: access.revit },
    { id: 'dynamo', name: 'Dynamo', category: 'VPL Platforms', status: 'stale', last_connection: null, active_sessions: 0, access: access.dynamo },
    { id: 'degram', name: 'DeGram', category: 'Agents', status: 'never_connected', last_connection: null, active_sessions: 0 }
  ] }];
  const row = id => host.querySelector(`tr[data-connector="${id}"]`);
  const dotStyle = id => row(id).querySelector('[data-testid="status-dot"]').getAttribute('style');
  if (new URLSearchParams(location.search).get('host') === 'degram') {
    await run('GRANTS-host-live-language', async () => {
      queue.push(registry({ grasshopper: 'available', revit: 'requestable', dynamo: 'pending' }), [200, { grants: [], requests: [] }]);
      await render(<ConnectorsScreen {...props} onBack={() => {}} />);
      await until(() => !!row('grasshopper'), 'Hosted table rendered');
      await act(async () => setLang('ru'));
      assert(row('grasshopper').textContent.includes('Доступен') && !row('grasshopper').querySelector('button'), 'Russian available is plain text');
      assert(row('revit').textContent.includes('Запросить доступ') && host.textContent.includes('Входите из аддина под своей учётной записью DG.'), 'Shared language updates table and caption');
    });
    await run('GRANTS-host-connector-table', async () => {
      queue.push(registry({ grasshopper: 'available', revit: 'requestable', dynamo: 'pending' }), [200, { grants: [], requests: [] }]);
      await render(<ConnectorsScreen {...props} onBack={() => {}} />);
      await until(() => !!host.querySelector('table'), 'Connector table rendered');
      equal(calls.map(c => c.url), ['/data-service/connectors?project=A', '/data-service/degram/grants/mine'], 'Host loaded the registry and own grants');
      equal([...host.querySelectorAll('tbody tr')].map(r => r.getAttribute('data-connector')), ['grasshopper', 'revit', 'dynamo', 'degram'], 'One row per connector');
      equal([...host.querySelectorAll('tbody th')].map(h => h.textContent), ['Grasshopper', 'Revit', 'Dynamo', 'DeGram'], 'Names in the first column');
      assert(row('grasshopper').textContent.includes('Available') && !row('grasshopper').querySelector('button'), 'Available row is plain text');
      assert(!host.textContent.includes('Create token') && host.textContent.includes('Sign in from the add-in with your DG account.'), 'Account sign-in caption replaces token action');
      assert(row('revit').textContent.includes('Request access'), 'Requestable row');
      assert(row('dynamo').textContent.includes('Request sent'), 'Pending row');
      assert(row('degram').textContent.includes('Request access'), 'DeGram row requests access');
      assert(row('grasshopper').textContent.includes('On') && row('revit').textContent.includes('Off') && row('dynamo').textContent.includes('Off'), 'On/Off statuses');
      assert(dotStyle('grasshopper').includes('var(--status-on)'), 'Active dot is green');
      assert(dotStyle('revit').includes('var(--status-fail)') && dotStyle('dynamo').includes('var(--status-fail)'), 'Inactive dots are red');
      assert(!button('Grant access') && !host.textContent.includes('Issued grants') && !host.textContent.includes('Pending requests'), 'Host owner acquired admin controls');
      const table = host.querySelector('table'); assert(table.style.border === 'none' || table.style.borderStyle === 'none' || table.getAttribute('style').includes('border: none'), 'Table has no visible border');
      assert(![...host.querySelectorAll('th, td')].some(c => /(^|;)\s*border[^:]*:\s*[^;]*solid/.test(c.getAttribute('style') || '')), 'No visible cell separators');
    });
    await run('GRANTS-host-request-access-without-token', async () => {
      queue.push(registry({ grasshopper: 'available', revit: 'requestable', dynamo: 'requestable' }), [200, { grants: [], requests: [] }]);
      await render(<ConnectorsScreen {...props} onBack={() => {}} />);
      await until(() => !!row('revit'), 'Table rendered');
      queue.push([201, { request_id: 'r1' }], registry({ grasshopper: 'available', revit: 'pending', dynamo: 'requestable' }), [200, { grants: [], requests: [] }]);
      await act(async () => { row('revit').querySelector('form').requestSubmit(); });
      await until(() => row('revit').textContent.includes('Request sent'), 'Revit request sent');
      equal(calls[2].url, '/data-service/connector-access-requests', 'Request URL'); equal(JSON.parse(calls[2].init.body), { project: 'A', connector_id: 'revit' }, 'Request body');
      assert(!button('Create token') && !host.textContent.includes('shown once'), 'No credential action or reveal');
      assert(!calls.some(c => c.url.includes('/credentials')), 'No credential request made');
    });
    await run('GRANTS-host-degram-row-request-flow', async () => {
      queue.push(registry({ grasshopper: 'available', revit: 'requestable', dynamo: 'requestable' }), [200, { grants: [], requests: [] }]);
      await render(<ConnectorsScreen {...props} onBack={() => {}} />);
      await until(() => !!row('degram'), 'Table rendered');
      queue.push([201, { request_id: 'r1' }], registry({ grasshopper: 'available', revit: 'requestable', dynamo: 'requestable' }), [200, { grants: [], requests: [{ project: 'A', note: '' }] }]);
      await act(async () => { row('degram').querySelector('form').requestSubmit(); });
      await until(() => row('degram').textContent.includes('Request sent'), 'DeGram request sent');
      equal(calls[2].url, '/data-service/degram/grant-requests', 'D-40 request URL'); equal(JSON.parse(calls[2].init.body), { project: 'A', note: '' }, 'D-40 request body');
    });
    await run('GRANTS-host-degram-row-available-with-grant', async () => {
      queue.push(registry({ grasshopper: 'requestable', revit: 'requestable', dynamo: 'requestable' }), [200, { grants: [{ project: 'A', active: true, label: 'Own' }], requests: [] }]);
      await render(<ConnectorsScreen {...props} onBack={() => {}} />);
      await until(() => !!row('degram'), 'Table rendered');
      assert(row('degram').textContent.includes('Available') && !row('degram').textContent.includes('Create token'), 'DeGram available without a token action');
    });
  } else {
    await run('GRANTS-eligible-members', async () => {
      equal(eligibleGrantMembers([{ username: 'a', role: 'viewer' }, { username: 'b', role: 'editor' }, { username: 'c', role: 'owner' }, { username: 'd', role: 'viewer' }], [{ username: 'a', connector_id: 'grasshopper', active: true }, { username: 'b', connector_id: 'revit', active: true }, { username: 'd', connector_id: 'grasshopper', active: false }], 'grasshopper').map(m => m.username), ['b', 'd'], 'Only eligible members');
    });
    await run('GRANTS-normal-screen-member-form-and-errors', async () => {
      const cards = () => [200, { categories: ['VPL Platforms'], connectors: [{ id: 'grasshopper', name: 'Grasshopper', category: 'VPL Platforms', status: 'active', last_connection: null, active_sessions: 1 }] }];
      const access = () => [200, { project: 'A', grants: [], requests: [] }];
      const members = () => [200, { members: [{ username: 'viewer', role: 'viewer' }, { username: 'editor', role: 'editor' }, { username: 'owner', role: 'owner' }] }];
      queue.push(cards(), access(), members());
      await render(<ConnectorsScreen {...props} user={owner} onBack={() => {}} />);
      await until(() => host.textContent.includes('Grasshopper'), 'Owner registry loaded');
      await act(async () => [...host.querySelectorAll('span')].find(s => s.textContent === 'Grasshopper').click());
      const admin = () => host.querySelector('[data-testid="connector-access-admin"]');
      assert(admin().textContent.includes('No access has been granted yet.'), 'Empty grants shown');
      const select = admin().querySelector('select');
      equal([...select.options].map(o => o.value), ['', 'viewer', 'editor'], 'Only eligible roles in the form');
      await act(async () => { select.value = 'viewer'; select.dispatchEvent(new Event('change', { bubbles: true })); });
      const grant = () => [...admin().querySelectorAll('button')].find(b => b.textContent.trim() === 'Grant access');
      const pending = deferred(); queue.push(pending.promise);
      await act(async () => grant().closest('form').requestSubmit());
      await until(() => grant().disabled, 'Grant disabled in flight');
      equal(calls.filter(c => c.init.method === 'POST').length, 1, 'One grant request sent');
      await act(async () => grant().closest('form').requestSubmit());
      equal(calls.filter(c => c.init.method === 'POST').length, 1, 'Second grant blocked');
      await act(async () => pending.resolve(reply(409, { detail: { error: 'Duplicate', code: 'ACCESS_EXISTS' } })));
      await until(() => !!host.querySelector('[role="alert"]'), 'Duplicate error displayed');
      assert(host.querySelector('[role="alert"]').textContent.includes('This member already has access.'), 'Mapped duplicate error');
      equal(JSON.parse(calls[3].init.body), { username: 'viewer', connector_id: 'grasshopper' }, 'Grant form payload');
      await act(async () => setLang('ru'));
      assert(host.querySelector('[role="alert"]').textContent.includes('У этого участника уже есть доступ.'), 'Duplicate error follows language');
      assert(host.textContent.includes('1 активный вход'), 'Russian one-form');
    });
    await run('GRANTS-normal-screen-project-change-hides-stale-access', async () => {
      const cards = (name) => [200, { categories: ['VPL Platforms'], connectors: [{ id: 'grasshopper', name, category: 'VPL Platforms', status: 'active', active_sessions: 3, access: 'available' }] }];
      queue.push(cards('A-only'), [200, { project: 'A', grants: [], requests: [] }], [200, { members: [{ username: 'a', role: 'viewer' }] }]);
      await render(<ConnectorsScreen {...props} user={owner} onBack={() => {}} />);
      await until(() => host.textContent.includes('A-only'), 'A loaded');
      const late = deferred(); queue.push(late.promise, [200, { project: 'B', grants: [], requests: [] }], [200, { members: [] }]);
      await render(<ConnectorsScreen {...props} user={{ memberships: [{ project: 'B', role: 'owner' }] }} project="B" onBack={() => {}} />);
      assert(!host.textContent.includes('A-only'), 'A card exposed after switching to B');
      await act(async () => late.resolve(reply(...cards('B-only'))));
      await until(() => host.textContent.includes('B-only'), 'B loaded');
      await act(async () => [...host.querySelectorAll('span')].find(s => s.textContent === 'B-only').click());
      assert(host.textContent.includes('3 live sign-ins'), 'English other-form');
      await act(async () => setLang('ru'));
      assert(host.textContent.includes('3 активных входа'), 'Russian few-form');
    });
    await run('GRANTS-normal-screen-member-fetch-fails-closed', async () => {
      queue.push(registry({ grasshopper: 'available', revit: 'available', dynamo: 'available' }), [200, { grants: [], requests: [] }], [503, { detail: { code: 'SERVICE_UNAVAILABLE', error: 'Members unavailable' } }]);
      await render(<ConnectorsScreen {...props} user={owner} onBack={() => {}} />);
      await until(() => !!host.querySelector('[role="alert"]'), 'Member load error shown');
      assert(!host.textContent.includes('All editors and viewers already have access.'), 'Failure not mistaken for empty members');
      assert(!host.querySelector('[data-testid="connector-access-admin"]'), 'No owner controls on incomplete load');
    });
    await run('GRANTS-normal-screen-degram-card', async () => {
      queue.push([200, { categories: ['Integration'], connectors: [{ id: 'degram', name: 'DeGram', category: 'Integration', status: 'active', active_sessions: 0 }] }], [200, { project: 'A', grants: [], requests: [] }], [200, { members: [{ username: 'member', role: 'viewer' }] }]);
      await render(<ConnectorsScreen {...props} user={owner} onBack={() => {}} />);
      await until(() => host.textContent.includes('DeGram'), 'Normal DeGram card loaded');
      queue.push([200, { grants: [], requests: [] }], [200, { members: [{ username: 'member' }] }]);
      await act(async () => [...host.querySelectorAll('span')].find(s => s.textContent === 'DeGram').click());
      await until(() => !!button('Grant access'), 'Owner grant controls on expanded card');
      equal(calls.map(c => c.url), ['/data-service/connectors?project=A', '/data-service/projects/A/connector-access', '/data-service/projects/A/members', '/data-service/projects/A/degram-grants', '/data-service/projects/A/members'], 'Normal grant calls');
      assert(!host.textContent.includes('Pair DeGram'), 'Pairing still offered');
    });
    await run('GRANTS-normal-screen-owner-approves-connector-request', async () => {
      const cards = () => [200, { categories: ['VPL Platforms'], connectors: [{ id: 'grasshopper', name: 'Grasshopper', category: 'VPL Platforms', status: 'never_connected', active_sessions: 0 }] }];
      const members = [200, { members: [{ username: 'viewer', role: 'viewer' }, { username: 'other', role: 'editor' }] }];
      queue.push(cards(), [200, { project: 'A', grants: [], requests: [{ request_id: 'r1', username: 'viewer', connector_id: 'grasshopper', note: 'Need it', created_at: '2026-10-11T10:00:00Z' }, { request_id: 'r2', username: 'other', connector_id: 'revit', note: '', created_at: '2026-10-11T10:00:00Z' }] }], members);
      await render(<ConnectorsScreen {...props} user={owner} onBack={() => {}} />);
      await until(() => host.textContent.includes('Grasshopper'), 'Normal card loaded');
      await act(async () => [...host.querySelectorAll('span')].find(s => s.textContent === 'Grasshopper').click());
      await until(() => host.textContent.includes('Access requests') && !!button('Grant access'), 'Pending requests on the connector card');
      assert(host.querySelector('[data-testid="connector-access-admin"]').textContent.includes('viewer · Need it') && !host.querySelector('[data-testid="connector-access-admin"]').textContent.includes('other ·'), 'Only this connector requests shown');
      queue.push([201, { access_id: 'a1' }], cards(), [200, { project: 'A', grants: [{ access_id: 'a1', username: 'viewer', connector_id: 'grasshopper', active: true, created_at: '2026-10-11T10:05:00Z' }], requests: [] }], members);
      await act(async () => button('Grant access').click());
      await until(() => !!button('Revoke access'), 'Issued access shown with Revoke');
      equal(calls[3].url, '/data-service/projects/A/connector-access', 'Issue URL'); equal(JSON.parse(calls[3].init.body), { username: 'viewer', connector_id: 'grasshopper' }, 'Issue body');
      const savedConfirm = window.confirm; window.confirm = () => true;
      try { queue.push([204, null], cards(), [200, { project: 'A', grants: [], requests: [] }], members); await act(async () => button('Revoke access').click()); await until(() => !button('Revoke access'), 'Revoked access removed'); }
      finally { window.confirm = savedConfirm; }
      equal(calls[7].url, '/data-service/projects/A/connector-access/a1', 'Revoke URL'); equal(calls[7].init.method, 'DELETE', 'Revoke method');
    });
  }
  const output = document.createElement('pre'); output.id = 'offline-results'; output.textContent = JSON.stringify({ results }); document.body.append(output);
})().catch(e => { document.body.textContent = `HARNESS_ERROR: ${e.stack}`; });
