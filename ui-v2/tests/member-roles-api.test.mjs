import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { CSRF_HEADER } from '../src/lib/apiClient.js';
import { changeMemberRole } from '../src/lib/memberApi.js';
import { isSoleOwner, needsSelfDemotionConfirm } from '../src/lib/memberRoles.js';

// Phase 1308-10 (D-01, D-14, D-16): member role change client and the pure helpers
// behind the role Select. Cookie session + CSRF marker, never a bearer.
const saved = Object.fromEntries(['fetch', 'window'].map(k => [k, Object.getOwnPropertyDescriptor(globalThis, k)]));
let calls;
beforeEach(() => {
  calls = [];
  globalThis.window = { GRAPH_CONFIG: { dataServiceUrl: '/data-service' }, dispatchEvent() {} };
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return new Response(JSON.stringify({ project: 'p', username: 'u', role: 'editor' }), { status: 200 });
  };
});
afterEach(() => {
  for (const [key, descriptor] of Object.entries(saved)) {
    if (descriptor) Object.defineProperty(globalThis, key, descriptor);
    else delete globalThis[key];
  }
});

test('changeMemberRole PUTs the encoded member path with the role body, cookie and CSRF marker', async () => {
  const result = await changeMemberRole('A/B ?#', 'u@x', 'editor');
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, '/data-service/projects/A%2FB%20%3F%23/members/u%40x');
  assert.equal(calls[0].init.method, 'PUT');
  assert.equal(calls[0].init.credentials, 'include');
  assert.equal(calls[0].init.headers[CSRF_HEADER], '1');
  assert.deepEqual(JSON.parse(calls[0].init.body), { role: 'editor' });
  assert.doesNotMatch(JSON.stringify(calls[0]), /dgp_|dgc_|dgk_|authorization|bearer/i);
  assert.equal(result.role, 'editor');
});

test('changeMemberRole surfaces the server error code (LAST_OWNER) for describeError', async () => {
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: { error: 'Cannot demote last owner', code: 'LAST_OWNER' } }), { status: 409 });
  await assert.rejects(
    () => changeMemberRole('p', 'u', 'viewer'),
    (err) => err.status === 409 && err.code === 'LAST_OWNER'
  );
});

test('isSoleOwner is true only for the single owner of the list', () => {
  const one = [{ username: 'a', role: 'owner' }, { username: 'b', role: 'editor' }];
  const two = [{ username: 'a', role: 'owner' }, { username: 'b', role: 'owner' }];
  assert.equal(isSoleOwner(one, 'a'), true);
  assert.equal(isSoleOwner(one, 'b'), false);
  assert.equal(isSoleOwner(two, 'a'), false);
  assert.equal(isSoleOwner(two, 'b'), false);
  assert.equal(isSoleOwner([], 'a'), false);
  assert.equal(isSoleOwner(undefined, 'a'), false);
  assert.equal(isSoleOwner(one, 'ghost'), false);
});

test('needsSelfDemotionConfirm asks only a non-admin owner who demotes themselves', () => {
  const owner = { email: 'a', isAdmin: false };
  assert.equal(needsSelfDemotionConfirm({ user: owner, username: 'a', from: 'owner', to: 'editor' }), true);
  assert.equal(needsSelfDemotionConfirm({ user: owner, username: 'a', from: 'owner', to: 'viewer' }), true);
  assert.equal(needsSelfDemotionConfirm({ user: { username: 'a', isAdmin: false }, username: 'a', from: 'owner', to: 'viewer' }), true);
  assert.equal(needsSelfDemotionConfirm({ user: { email: 'a', isAdmin: true }, username: 'a', from: 'owner', to: 'editor' }), false);
  assert.equal(needsSelfDemotionConfirm({ user: owner, username: 'b', from: 'owner', to: 'editor' }), false);
  assert.equal(needsSelfDemotionConfirm({ user: owner, username: 'a', from: 'owner', to: 'owner' }), false);
  assert.equal(needsSelfDemotionConfirm({ user: owner, username: 'a', from: 'editor', to: 'viewer' }), false);
  assert.equal(needsSelfDemotionConfirm({ user: null, username: 'a', from: 'owner', to: 'editor' }), false);
  assert.equal(needsSelfDemotionConfirm({ user: owner, username: undefined, from: 'owner', to: 'editor' }), false);
});

test('ProjectsScreen wires the role Select through changeMemberRole with a sole-owner guard', async () => {
  const source = await readFile(new URL('../src/screens/ProjectsScreen.jsx', import.meta.url), 'utf8');
  assert.match(source, /changeMemberRole\(/);
  assert.match(source, /function MemberRoleSelect\(/);
  assert.match(source, /<MemberRoleSelect\b/);
  assert.match(source, /isSoleOwner\(/);
  assert.match(source, /needsSelfDemotionConfirm\(/);
  assert.match(source, /aria-describedby/);
  assert.match(source, /aria-live="polite"/);
  assert.doesNotMatch(source, /<Badge\b/, 'the static role badge is replaced by the Select');
});
