import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import ProjectsScreen from '../src/screens/ProjectsScreen.jsx';

// Render the actual panel/primitives with real ReactDOM; only fetch is faked.
const results = [], calls = [], unexpected = [], queue = [];
window.IS_REACT_ACT_ENVIRONMENT = true;
window.GRAPH_CONFIG = { dataServiceUrl: '/data-service' };
const savedFetch = window.fetch;
window.fetch = async (url, init) => {
  calls.push({ url, init });
  const reply = queue.shift();
  if (!reply) { unexpected.push(url); throw new Error(`No network allowed: ${url}`); }
  if (reply instanceof Promise) return reply;
  return response(...reply);
};
const response = (status, body) => new Response(status === 204 ? null : JSON.stringify(body), { status });
const equal = (a, b, label) => { if (JSON.stringify(a) !== JSON.stringify(b)) throw new Error(`${label}: ${JSON.stringify(a)} != ${JSON.stringify(b)}`); };
const check = (ok, label) => { if (!ok) throw new Error(label); };
let root, host;
const props = { active: true, project: 'A', user: { email: 'owner', isAdmin: false }, onBack() {}, onProject() {} };
const tick = () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
const until = async (predicate, label) => { for (let i = 0; i < 20 && !predicate(); i += 1) await tick(); check(predicate(), label); };
const render = p => act(async () => { root.render(<ProjectsScreen {...p} />); });
async function setup() {
  queue.length = 0; calls.length = 0; unexpected.length = 0;
  localStorage.clear(); host = document.createElement('div'); document.body.append(host); root = createRoot(host);
}
async function teardown() {
  await act(async () => root.unmount()); host.remove(); equal(queue.length, 0, 'Unused replies'); equal(unexpected, [], 'Unexpected requests');
  for (const call of calls) {
    equal(call.init.credentials, 'include', 'Cookie mode');
    equal(call.init.headers['X-DG-CSRF'], ['POST', 'PUT', 'DELETE', 'PATCH'].includes(call.init.method) ? '1' : undefined, 'CSRF marker');
    check(!Object.keys(call.init.headers).some(k => /authorization|cookie/i.test(k)), 'No token header');
  }
}
async function run(id, fn) {
  await setup(); let error;
  try { await fn(); } catch (e) { error = e.message; }
  try { await teardown(); } catch (e) { error = [error, e.message].filter(Boolean).join('; '); }
  results.push({ id, status: error ? 'FAIL' : 'PASS', ...(error ? { error } : {}) });
}
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
(async () => {
  await run('PANEL-01 late A member response must not appear in B panel', async () => {
    const late = deferred();
    queue.push([200, { projects: [{ project: 'A', role: 'owner' }, { project: 'B', role: 'owner' }] }], late.promise);
    await render(props); await tick();
    equal(calls.map(c => c.url), ['/data-service/projects', '/data-service/projects/A/members'], 'Initial owner calls');
    queue.push([200, { members: [{ username: 'B-only-member', role: 'viewer' }] }]);
    await render({ ...props, project: 'B' }); await tick();
    check(host.textContent.includes('B-only-member'), 'B members loaded');
    await act(async () => { late.resolve(response(200, { members: [{ username: 'A-FOREIGN-MEMBER', role: 'viewer' }] })); }); await tick();
    check(!host.textContent.includes('A-FOREIGN-MEMBER'), 'Foreign A member leaked into B panel');
    check(host.textContent.includes('B-only-member'), 'B members replaced by stale A response');
  });
  await run('PANEL-02 late A invitation code must not appear in B panel', async () => {
    queue.push([200, { projects: [{ project: 'A', role: 'owner' }, { project: 'B', role: 'owner' }] }], [200, { members: [] }]);
    await render(props); await tick();
    const input = host.querySelector('input[placeholder="Username to invite"]');
    await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, 'invitee'); input.dispatchEvent(new Event('input', { bubbles: true })); });
    const late = deferred(); queue.push(late.promise);
    await act(async () => [...host.querySelectorAll('button')].find(b => b.textContent === 'Invite').click());
    queue.push([200, { members: [] }]); await render({ ...props, project: 'B' }); await tick();
    // Old implementation reloads A members after the late invitation; keep
    // that local reply available to expose code leakage rather than harness noise.
    queue.push([200, { members: [] }]);
    await act(async () => { late.resolve(response(200, { status: 'invited', inviteCode: 'SYNTHETIC-A-FOREIGN-INVITE' })); }); await tick();
    if (queue.length === 1) queue.pop();
    check(![...host.querySelectorAll('input')].some(i => i.value === 'SYNTHETIC-A-FOREIGN-INVITE'), 'Foreign A invitation code leaked into B panel');
    equal(localStorage.length, 0, 'No invitation persisted');
  });
  for (const role of ['viewer', 'editor']) await run(`PANEL-role-${role} cannot see owner panel or fetch members`, async () => {
    queue.push([200, { projects: [{ project: 'A', role }] }]); await render(props); await tick();
    check(!host.textContent.includes('Members ·'), 'Owner panel hidden'); equal(calls.length, 1, 'No member request');
  });
  await run('PANEL-admin can administer without owner role', async () => {
    queue.push([200, { projects: [] }], [200, { members: [{ username: 'owner', role: 'owner' }] }]);
    await render({ ...props, user: { email: 'admin', isAdmin: true } }); await tick(); check(host.textContent.includes('Members · A'), 'Admin panel available'); equal(calls[1].url, '/data-service/projects/A/members', 'Scoped members');
  });
  for (const status of [401, 403]) await run(`PANEL-members-${status} no foreign member state on denied read`, async () => {
    let expiries = 0; const listener = () => { expiries += 1; }; window.addEventListener('dg-auth-expired', listener);
    queue.push([200, { projects: [{ project: 'A', role: 'owner' }] }], [status, { detail: 'Member read denied' }]); await render(props); await tick();
    await until(() => host.textContent.includes('Member read denied'), 'Denial shown'); window.removeEventListener('dg-auth-expired', listener); equal(expiries, status === 401 ? 1 : 0, 'Expiry only on 401'); check(!host.textContent.includes('FOREIGN-MEMBER'), 'No denied data');
  });
  const fillInvite = async () => {
    const input = host.querySelector('input[placeholder="Username to invite"]');
    await act(async () => { Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, 'invitee'); input.dispatchEvent(new Event('input', { bubbles: true })); });
  };
  const button = label => [...host.querySelectorAll('button')].find(b => b.textContent === label);
  const ownerReady = async () => { queue.push([200, { projects: [{ project: 'A', role: 'owner' }] }], [200, { members: [{ username: 'only-owner', role: 'owner' }] }]); await render(props); await until(() => !!button('Remove'), 'Owner members ready'); };
  await run('PANEL-invite once-only display dismiss/hide/remount no token persistence', async () => {
    await ownerReady(); await fillInvite();
    queue.push([201, { status: 'invited', inviteCode: 'SYNTHETIC-ONCE-CODE' }], [200, { members: [] }]); await act(async () => button('Invite').click()); await tick();
    equal(JSON.parse(calls[2].init.body), { username: 'invitee', project: 'A', role: 'viewer' }, 'Invite scoped body');
    equal([...host.querySelectorAll('input')].filter(i => i.value === 'SYNTHETIC-ONCE-CODE').length, 1, 'Single displayed code'); equal(localStorage.length, 0, 'No code persisted');
    await act(async () => button('Dismiss').click()); check(![...host.querySelectorAll('input')].some(i => i.value === 'SYNTHETIC-ONCE-CODE'), 'Dismiss discards code');
    await render({ ...props, active: false });
    queue.push([200, { projects: [{ project: 'A', role: 'owner' }] }], [200, { members: [] }]); await render(props); await tick();
    check(![...host.querySelectorAll('input')].some(i => i.value === 'SYNTHETIC-ONCE-CODE'), 'No code replay on reactivation');
  });
  await run('PANEL-existing-account member-added note not invite code', async () => {
    await ownerReady(); await fillInvite(); queue.push([200, { status: 'member-added' }], [200, { members: [{ username: 'invitee', role: 'viewer' }] }]); await act(async () => button('Invite').click()); await tick();
    check(host.textContent.includes('invitee was added to A as viewer.'), 'Member note shown'); check(!button('Copy'), 'No invite code copy surface'); equal(localStorage.length, 0, 'No credential persisted');
  });
  for (const status of [401, 403]) await run(`PANEL-invite-${status} denial no code or member refresh`, async () => {
    await ownerReady(); await fillInvite(); queue.push([status, { detail: 'Invite denied' }]); await act(async () => button('Invite').click()); await tick(); check(host.textContent.includes('Invite denied'), 'Invite error visible'); check(!button('Copy'), 'No code'); equal(calls.length, 3, 'No member reload on denial');
  });
  await run('PANEL-LAST_OWNER 409 keeps existing member and shows refusal', async () => {
    await ownerReady(); queue.push([409, { detail: { error: 'Cannot remove last owner', code: 'LAST_OWNER' } }]); await act(async () => button('Remove').click()); await tick();
    check(host.textContent.includes('Cannot remove last owner'), 'LAST_OWNER refusal rendered'); check(host.textContent.includes('only-owner'), 'Owner retained'); equal(calls.length, 3, 'No false-success refresh'); equal(calls[2].init.method, 'DELETE', 'Member deletion verb');
  });
  await run('PANEL-remove success scoped DELETE followed by fresh members', async () => {
    await ownerReady(); queue.push([204, null], [200, { members: [] }]); await act(async () => button('Remove').click()); await tick(); check(!host.textContent.includes('only-owner'), 'Member refresh applied'); equal(calls[2].url, '/data-service/projects/A/members/only-owner', 'Scoped member deletion');
  });
  await run('PANEL-rights-loss hides and clears invitation and members', async () => {
    await ownerReady(); await fillInvite(); queue.push([201, { status: 'invited', inviteCode: 'SYNTHETIC-OWNER-CODE' }], [200, { members: [] }]); await act(async () => button('Invite').click()); await tick();
    await render({ ...props, active: false }); queue.push([200, { projects: [{ project: 'A', role: 'viewer' }] }], [200, { members: [] }]); await render(props); await tick(); check(!host.textContent.includes('Members ·'), 'Rights loss hides panel'); check(![...host.querySelectorAll('input')].some(i => i.value === 'SYNTHETIC-OWNER-CODE'), 'Code erased');
  });
  await run('PANEL-03 late A member-removal failure must not appear in B panel', async () => {
    queue.push([200, { projects: [{ project: 'A', role: 'owner' }, { project: 'B', role: 'owner' }] }], [200, { members: [{ username: 'A-member', role: 'viewer' }] }]); await render(props); await until(() => !!button('Remove'), 'A member ready');
    const late = deferred(); queue.push(late.promise); await act(async () => button('Remove').click());
    queue.push([200, { members: [{ username: 'B-only-member', role: 'viewer' }] }]); await render({ ...props, project: 'B' }); await until(() => host.textContent.includes('B-only-member'), 'B member ready');
    await act(async () => late.resolve(response(403, { detail: 'A-FOREIGN-REMOVAL-ERROR' }))); await until(() => queue.length === 0, 'Replies consumed'); await tick();
    check(!host.textContent.includes('A-FOREIGN-REMOVAL-ERROR'), 'Foreign A removal error leaked into B panel');
  });
  const output = document.createElement('pre'); output.id = 'offline-results'; output.textContent = JSON.stringify({ proof_level: 'offline-actual-React18-ReactDOM-panel-fake-fetch', results }); document.body.append(output);
})().catch(e => { document.body.textContent = `HARNESS_ERROR: ${e.stack}`; });
