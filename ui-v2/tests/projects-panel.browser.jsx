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
    queue.push([200, { project: 'A', providerExportAllowed: true, wholeDefinitionAllowed: false }], [200, { projects: [] }], [200, { members: [{ username: 'owner', role: 'owner' }] }]);
    await render({ ...props, user: { email: 'admin', isAdmin: true } }); await tick(); check(host.textContent.includes('Members · A'), 'Admin panel available'); check(calls.some(c => c.url === '/data-service/projects/A/members'), 'Scoped members');
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
  const ownerReady = async () => { queue.push([200, { projects: [{ project: 'A', role: 'owner' }] }], [200, { members: [{ username: 'only-owner', role: 'owner' }] }]); await render(props); await until(() => !!button('Remove member'), 'Owner members ready'); };
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
    await ownerReady(); queue.push([409, { detail: { error: 'Cannot remove last owner', code: 'LAST_OWNER' } }]); await act(async () => button('Remove member').click()); await tick();
    check(host.textContent.includes('A project must keep at least one owner. Promote another member first.'), 'LAST_OWNER refusal rendered with the mapped text'); check(host.textContent.includes('only-owner'), 'Owner retained'); equal(calls.length, 3, 'No false-success refresh'); equal(calls[2].init.method, 'DELETE', 'Member deletion verb');
  });
  await run('PANEL-remove success scoped DELETE followed by fresh members', async () => {
    await ownerReady(); queue.push([204, null], [200, { members: [] }]); await act(async () => button('Remove member').click()); await tick(); check(!host.textContent.includes('only-owner'), 'Member refresh applied'); equal(calls[2].url, '/data-service/projects/A/members/only-owner', 'Scoped member deletion');
  });
  await run('PANEL-rights-loss hides and clears invitation and members', async () => {
    await ownerReady(); await fillInvite(); queue.push([201, { status: 'invited', inviteCode: 'SYNTHETIC-OWNER-CODE' }], [200, { members: [] }]); await act(async () => button('Invite').click()); await tick();
    await render({ ...props, active: false }); queue.push([200, { projects: [{ project: 'A', role: 'viewer' }] }], [200, { members: [] }]); await render(props); await tick(); check(!host.textContent.includes('Members ·'), 'Rights loss hides panel'); check(![...host.querySelectorAll('input')].some(i => i.value === 'SYNTHETIC-OWNER-CODE'), 'Code erased');
  });
  await run('PANEL-03 late A member-removal failure must not appear in B panel', async () => {
    queue.push([200, { projects: [{ project: 'A', role: 'owner' }, { project: 'B', role: 'owner' }] }], [200, { members: [{ username: 'A-member', role: 'viewer' }] }]); await render(props); await until(() => !!button('Remove member'), 'A member ready');
    const late = deferred(); queue.push(late.promise); await act(async () => button('Remove member').click());
    queue.push([200, { members: [{ username: 'B-only-member', role: 'viewer' }] }]); await render({ ...props, project: 'B' }); await until(() => host.textContent.includes('B-only-member'), 'B member ready');
    await act(async () => late.resolve(response(403, { detail: 'A-FOREIGN-REMOVAL-ERROR' }))); await until(() => queue.length === 0, 'Replies consumed'); await tick();
    check(!host.textContent.includes('A-FOREIGN-REMOVAL-ERROR'), 'Foreign A removal error leaked into B panel');
  });
  // Phase 1308-10 (D-16): role Select on the Members panel.
  const roleSelect = name => host.querySelector(`select[aria-label="Role of ${name}"]`);
  const pick = (select, value) => act(async () => { select.value = value; select.dispatchEvent(new Event('change', { bubbles: true })); });
  const twoMembers = [{ username: 'only-owner', role: 'owner' }, { username: 'bob', role: 'viewer' }];
  const roleReady = async (members, p = props) => { if (p.user?.isAdmin) queue.push([200, { project: 'A', providerExportAllowed: true, wholeDefinitionAllowed: false }]); queue.push([200, { projects: [{ project: 'A', role: 'owner' }] }], [200, { members }]); await render(p); await until(() => !!roleSelect(members[0].username), 'Role selects ready'); };
  await run('PANEL-role optimistic change disables the Select in flight then refreshes and announces', async () => {
    await roleReady(twoMembers);
    const inFlight = deferred(); queue.push(inFlight.promise);
    await pick(roleSelect('bob'), 'editor');
    equal(roleSelect('bob').value, 'editor', 'Optimistic value shown at once'); check(roleSelect('bob').disabled, 'Disabled while in flight'); equal(roleSelect('bob').style.opacity, '0.45', 'Disabled opacity');
    equal(calls[2].url, '/data-service/projects/A/members/bob', 'Scoped role PUT'); equal(calls[2].init.method, 'PUT', 'PUT verb'); equal(JSON.parse(calls[2].init.body), { role: 'editor' }, 'Role body');
    queue.push([200, { members: [{ username: 'only-owner', role: 'owner' }, { username: 'bob', role: 'editor' }] }]);
    await act(async () => inFlight.resolve(response(200, { project: 'A', username: 'bob', role: 'editor' }))); await until(() => queue.length === 0, 'Refresh consumed'); await tick();
    equal(roleSelect('bob').value, 'editor', 'Server value kept'); check(!roleSelect('bob').disabled, 'Enabled again');
    check(host.querySelector('[aria-live="polite"]') && host.textContent.includes('Role updated for bob'), 'Role saved announced');
  });
  await run('PANEL-role failure rolls back and shows the mapped inline error', async () => {
    await roleReady(twoMembers);
    queue.push([409, { detail: { error: 'Cannot demote the last owner', code: 'LAST_OWNER' } }]);
    await pick(roleSelect('bob'), 'owner'); await until(() => host.textContent.includes('A project must keep at least one owner. Promote another member first.'), 'Mapped error shown');
    equal(roleSelect('bob').value, 'viewer', 'Rolled back to the server value'); check(!host.textContent.includes('Cannot demote the last owner'), 'Server text not shown when the code is mapped'); equal(calls.length, 3, 'No reload after a failure');
  });
  await run('PANEL-role sole owner Select is disabled with tooltip and aria-describedby', async () => {
    await roleReady(twoMembers);
    const select = roleSelect('only-owner'); check(select.disabled, 'Sole owner disabled'); check(!roleSelect('bob').disabled, 'Other member enabled');
    const text = 'A project must keep at least one owner. Promote another member first.';
    equal(select.title, text, 'Tooltip'); const described = document.getElementById(select.getAttribute('aria-describedby')); check(described && described.textContent === text, 'Described-by node carries the text');
  });
  await run('PANEL-role two owners: no Select is disabled', async () => {
    await roleReady([{ username: 'only-owner', role: 'owner' }, { username: 'bob', role: 'owner' }]);
    check(!roleSelect('only-owner').disabled && !roleSelect('bob').disabled, 'Both owners can change');
  });
  await run('PANEL-role non-admin owner self-demotion asks first (Keep my role / Change role)', async () => {
    const owners = [{ username: 'owner', role: 'owner' }, { username: 'bob', role: 'owner' }];
    await roleReady(owners);
    await pick(roleSelect('owner'), 'editor');
    check(host.textContent.includes('You will no longer be able to manage members of this project.'), 'Confirm text'); equal(calls.length, 2, 'No PUT before confirm'); equal(roleSelect('owner').value, 'owner', 'Select stays on the server value');
    await act(async () => button('Keep my role').click()); check(!host.textContent.includes('You will no longer be able'), 'Confirm closed'); equal(calls.length, 2, 'Keep my role sends nothing');
    await pick(roleSelect('owner'), 'editor'); await act(async () => roleSelect('owner').dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))); check(!host.textContent.includes('You will no longer be able'), 'Escape keeps the role');
    await pick(roleSelect('owner'), 'editor'); queue.push([200, { project: 'A', username: 'owner', role: 'editor' }], [200, { members: [{ username: 'owner', role: 'editor' }, { username: 'bob', role: 'owner' }] }]);
    await act(async () => button('Change role').click()); await until(() => queue.length === 0, 'Change consumed'); await tick(); equal(calls[2].init.method, 'PUT', 'Confirmed PUT'); equal(JSON.parse(calls[2].init.body), { role: 'editor' }, 'Self-demotion body');
  });
  await run('PANEL-role admin demoting themselves needs no confirm', async () => {
    const owners = [{ username: 'admin', role: 'owner' }, { username: 'bob', role: 'owner' }];
    await roleReady(owners, { ...props, user: { email: 'admin', isAdmin: true } });
    queue.push([200, { project: 'A', username: 'admin', role: 'editor' }], [200, { members: [{ username: 'admin', role: 'editor' }, { username: 'bob', role: 'owner' }] }]);
    await pick(roleSelect('admin'), 'editor'); await until(() => queue.length === 0, 'Change consumed'); check(!host.textContent.includes('You will no longer be able'), 'No confirm for an admin');
  });
  // Phase 1308-10 (D-02, D-17): admin-only Project settings panel. The child panel's effect runs before the
  // screen's own, so a DG admin's first request is the policy GET, then projects, then members.
  const policyOf = (provider = true, whole = false) => [200, { project: 'A', providerExportAllowed: provider, wholeDefinitionAllowed: whole }];
  const adminProps = { ...props, user: { email: 'admin', isAdmin: true } };
  const box = label => [...host.querySelectorAll('[role="checkbox"]')].find(el => el.textContent === label);
  const clickBox = label => act(async () => box(label).querySelector('span[id]').click());
  const adminTail = [[200, { projects: [{ project: 'A', role: 'owner' }] }], [200, { members: [{ username: 'admin', role: 'owner' }] }]];
  const settingsReady = async (policy = policyOf()) => { queue.push(policy, ...adminTail); await render(adminProps); await until(() => !!box('Allow provider export'), 'Policy rows ready'); };
  const putCall = () => calls.filter(c => c.init.method === 'PUT');
  await run('PANEL-settings loading text then both toggles at server state (admin only)', async () => {
    const late = deferred(); queue.push(late.promise, ...adminTail);
    await render(adminProps); await tick();
    check(host.textContent.includes('Project settings · A'), 'Panel title'); check(host.textContent.includes('Loading settings…'), 'Loading text'); check(host.textContent.includes('Visible to DG admins only.'), 'Visibility note');
    equal(calls[0].url, '/data-service/projects/A/degram-policy', 'Policy GET first'); equal(calls[0].init.method, 'GET', 'GET verb');
    await act(async () => late.resolve(response(200, { project: 'A', providerExportAllowed: true, wholeDefinitionAllowed: false })));
    await until(() => !!box('Allow provider export'), 'Rows after load'); check(!host.textContent.includes('Loading settings…'), 'Loading text gone');
    equal(box('Allow provider export').getAttribute('aria-checked'), 'true', 'Provider export on'); equal(box('Allow whole-definition export').getAttribute('aria-checked'), 'false', 'Whole-definition export off');
    check(host.textContent.includes('Lets DeGram request the complete Grasshopper definition.'), 'Helper text');
  });
  await run('PANEL-settings a project owner who is not an admin gets no panel, no placeholder and no policy call', async () => {
    await ownerReady();
    check(!host.textContent.includes('Project settings'), 'No panel'); check(!host.textContent.includes('Visible to DG admins only.'), 'No placeholder'); check(!calls.some(c => /degram-policy/.test(c.url)), 'No policy request');
  });
  await run('PANEL-settings provider export toggles without confirm and sends only the changed flag', async () => {
    await settingsReady();
    const inFlight = deferred(); queue.push(inFlight.promise);
    await clickBox('Allow provider export');
    equal(putCall().length, 1, 'One PUT'); equal(putCall()[0].url, '/data-service/projects/A/degram-policy', 'Policy PUT url'); equal(JSON.parse(putCall()[0].init.body), { providerExportAllowed: false }, 'Only the changed flag');
    equal(box('Allow provider export').getAttribute('aria-checked'), 'false', 'Optimistic value'); equal(box('Allow provider export').getAttribute('aria-disabled'), 'true', 'Disabled in flight'); equal(box('Allow provider export').style.opacity, '0.45', 'Disabled opacity');
    await act(async () => inFlight.resolve(response(200, { project: 'A', providerExportAllowed: false, wholeDefinitionAllowed: false }))); await tick();
    equal(box('Allow provider export').getAttribute('aria-checked'), 'false', 'Server value kept'); equal(box('Allow provider export').getAttribute('aria-disabled'), 'false', 'Enabled again'); check(host.textContent.includes('Project settings saved'), 'Saved announced');
  });
  await run('PANEL-settings enabling whole-definition export asks first; Keep export off and Escape send nothing', async () => {
    await settingsReady();
    await clickBox('Allow whole-definition export');
    check(host.textContent.includes('Allow whole-definition export for A? DeGram will be able to request the entire definition'), 'Confirm text with the project'); check(!!button('Allow whole-definition export') && !!button('Keep export off'), 'Confirm buttons');
    equal(putCall().length, 0, 'No PUT before confirm'); equal(box('Allow whole-definition export').getAttribute('aria-checked'), 'false', 'Checkbox stays off');
    await act(async () => button('Keep export off').click()); check(!button('Keep export off'), 'Confirm closed'); equal(putCall().length, 0, 'Keep export off sends nothing');
    await clickBox('Allow whole-definition export'); await act(async () => box('Allow whole-definition export').dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }))); check(!button('Keep export off'), 'Escape keeps export off'); equal(putCall().length, 0, 'Escape sends nothing');
    await clickBox('Allow whole-definition export'); queue.push(policyOf(true, true));
    await act(async () => button('Allow whole-definition export').click()); await until(() => queue.length === 0, 'Confirmed PUT consumed'); await tick();
    equal(JSON.parse(putCall()[0].init.body), { wholeDefinitionAllowed: true }, 'Only whole-definition flag'); equal(box('Allow whole-definition export').getAttribute('aria-checked'), 'true', 'Now on'); check(!button('Keep export off'), 'Confirm gone');
  });
  await run('PANEL-settings turning whole-definition export off needs no confirm', async () => {
    await settingsReady(policyOf(true, true));
    queue.push(policyOf(true, false)); await clickBox('Allow whole-definition export'); await until(() => queue.length === 0, 'PUT consumed'); await tick();
    check(!button('Keep export off'), 'No confirm'); equal(JSON.parse(putCall()[0].init.body), { wholeDefinitionAllowed: false }, 'Off flag only'); equal(box('Allow whole-definition export').getAttribute('aria-checked'), 'false', 'Now off');
  });
  await run('PANEL-settings failed save rolls back and shows the mapped error', async () => {
    await settingsReady();
    queue.push([422, { detail: { error: 'No policy flag was given.', code: 'DEGRAM_POLICY_INVALID' } }]); await clickBox('Allow provider export'); await tick();
    check(host.textContent.includes('Choose a setting to change.'), 'Mapped error'); check(!host.textContent.includes('No policy flag was given.'), 'Server text not shown'); equal(box('Allow provider export').getAttribute('aria-checked'), 'true', 'Rolled back');
  });
  await run('PANEL-settings 403 ADMIN_REQUIRED shows the mapped message and reloads the panel', async () => {
    await settingsReady();
    queue.push([403, { detail: { error: 'Admin only', code: 'ADMIN_REQUIRED' } }], policyOf(false, false)); await clickBox('Allow provider export'); await until(() => queue.length === 0, 'PUT and reload consumed'); await tick();
    check(host.textContent.includes('Only a DG admin can change project settings.'), 'Mapped message'); equal(calls.filter(c => c.init.method === 'GET' && /degram-policy/.test(c.url)).length, 2, 'Panel reloaded');
    await until(() => !!box('Allow provider export'), 'Rows back'); equal(box('Allow provider export').getAttribute('aria-checked'), 'false', 'Server truth after reload');
  });
  await run('PANEL-settings load failure shows the retry button and recovers', async () => {
    queue.push([500, { detail: 'boom' }], ...adminTail); await render(adminProps); await until(() => host.textContent.includes('Could not load project settings.'), 'Load error'); check(!!button('Retry loading settings'), 'Retry button');
    queue.push(policyOf()); await act(async () => button('Retry loading settings').click()); await until(() => !!box('Allow provider export'), 'Rows after retry');
  });
  const output = document.createElement('pre'); output.id = 'offline-results'; output.textContent = JSON.stringify({ proof_level: 'offline-actual-React18-ReactDOM-panel-fake-fetch', results }); document.body.append(output);
})().catch(e => { document.body.textContent = `HARNESS_ERROR: ${e.stack}`; });
