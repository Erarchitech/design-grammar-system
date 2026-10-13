import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import * as auth from '../src/lib/auth.js';
import { ApiError, AUTH_EXPIRED_EVENT } from '../src/lib/apiClient.js';

const originals = Object.fromEntries(['fetch', 'window', 'localStorage'].map(k => [k, Object.getOwnPropertyDescriptor(globalThis, k)]));
let replies, calls, events, storage;
beforeEach(() => {
  replies = []; calls = []; events = [];
  storage = new Map();
  globalThis.localStorage = {
    get length() { return storage.size; }, key(i) { return [...storage.keys()][i] ?? null; },
    getItem(k) { return storage.get(k) ?? null; }, setItem(k, v) { storage.set(k, String(v)); }, removeItem(k) { storage.delete(k); }
  };
  globalThis.window = { dispatchEvent(e) { events.push(e.type); } };
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    assert.ok(replies.length, `Unplanned request; no network fallback: ${url}`);
    const reply = replies.shift();
    if (reply instanceof Error) throw reply;
    return new Response(JSON.stringify(reply[1]), { status: reply[0] });
  };
});
afterEach(() => {
  assert.equal(replies.length, 0, 'All scheduled replies consumed');
  for (const [k, descriptor] of Object.entries(originals)) {
    if (descriptor) Object.defineProperty(globalThis, k, descriptor); else delete globalThis[k];
  }
});

test('AUTH-01 login must not establish identity when the session expires before /auth/me', async () => {
  replies.push([200, { username: 'old-owner', isAdmin: true }], [401, { detail: 'Session expired' }]);
  await assert.rejects(auth.login('old-owner', 'synthetic-password-only'), e => e instanceof ApiError && e.status === 401);
  assert.deepEqual(events, [AUTH_EXPIRED_EVENT]);
  assert.deepEqual(calls.map(c => c.url), ['/data-service/auth/login', '/data-service/auth/me']);
  assert.equal(storage.size, 0);
});

const onboarding = [
  ['login', () => auth.login('requested', 'SYNTHETIC-PASSWORD'), '/auth/login', { username: 'requested', password: 'SYNTHETIC-PASSWORD' }],
  ['acceptInvite', () => auth.acceptInvite('SYNTHETIC-INVITE', 'SYNTHETIC-PASSWORD'), '/auth/accept-invite', { inviteCode: 'SYNTHETIC-INVITE', password: 'SYNTHETIC-PASSWORD' }],
  ['register', () => auth.register('requested', 'SYNTHETIC-PASSWORD'), '/auth/register', { username: 'requested', password: 'SYNTHETIC-PASSWORD' }]
];
for (const [name, invoke, path, body] of onboarding) {
  test(`AUTH-${name}-success identity and memberships come from current session, no token persistence`, async () => {
    replies.push([200, { username: 'not-authoritative', isAdmin: true, token: 'SYNTHETIC-RESPONSE-TOKEN' }], [200, { username: 'actual-member', isAdmin: false, memberships: [{ project: 'own', role: 'viewer' }], token: 'SYNTHETIC-ME-TOKEN' }]);
    assert.deepEqual(await invoke(), { email: 'actual-member', name: 'actual-member', isAdmin: false, memberships: [{ project: 'own', role: 'viewer' }] });
    assert.equal(calls[0].url, `/data-service${path}`); assert.equal(calls[0].init.method, 'POST'); assert.deepEqual(JSON.parse(calls[0].init.body), body);
    for (const c of calls) assert.equal(c.init.credentials, 'include');
    assert.equal(calls[0].init.headers['X-DG-CSRF'], '1'); assert.equal(calls[1].init.headers['X-DG-CSRF'], undefined);
    assert.ok(!JSON.stringify(calls).includes('SYNTHETIC-RESPONSE-TOKEN')); assert.equal(storage.size, 0);
  });
  for (const status of [401, 403, 404, 409]) test(`AUTH-${name}-${status} denial no membership fetch or stored credentials`, async () => {
    replies.push([status, { detail: { error: 'Denied', code: 'DENIED' } }]);
    await assert.rejects(invoke(), e => e.status === status && e.code === 'DENIED'); assert.equal(calls.length, 1); assert.equal(storage.size, 0); assert.deepEqual(events, status === 401 ? [AUTH_EXPIRED_EVENT] : []);
  });
  for (const me of [null, {}, { username: '' }]) test(`AUTH-${name}-invalid-me-${JSON.stringify(me)} cannot restore response admin identity`, async () => {
    replies.push([200, { username: 'stale-owner', isAdmin: true }], [200, me]);
    await assert.rejects(invoke(), e => e instanceof ApiError && e.status === 401); assert.equal(storage.size, 0);
  });
  test(`AUTH-${name}-me-401 no stale principal resurrection`, async () => {
    replies.push([200, { username: 'stale-owner', isAdmin: true }], [401, { detail: 'Expired' }]); await assert.rejects(invoke(), e => e.status === 401); assert.deepEqual(events, [AUTH_EXPIRED_EVENT]);
  });
}
test('AUTH-current-user-401 null and expiry event', async () => { replies.push([401, { detail: 'Expired' }]); assert.equal(await auth.currentUser(), null); assert.deepEqual(events, [AUTH_EXPIRED_EVENT]); });
test('AUTH-current-user-403 not signed-out success', async () => { replies.push([403, { detail: 'Forbidden' }]); await assert.rejects(auth.currentUser(), e => e.status === 403); });
for (const value of [true, false, undefined, 1, 'true']) test(`AUTH-options-${typeof value}-${String(value)} registration enabled only for boolean true`, async () => { replies.push([200, { selfRegistration: value }]); assert.deepEqual(await auth.authOptions(), { selfRegistration: value === true }); assert.equal(calls[0].init.method, 'GET'); });
test('AUTH-options-failure propagated for UI fail-closed handling', async () => { replies.push([503, { detail: 'Offline' }]); await assert.rejects(auth.authOptions(), e => e.status === 503); });
for (const status of [200, 401, 403, 500]) test(`AUTH-logout-${status} expired idempotent, real denials not swallowed`, async () => {
  replies.push([status, { detail: 'Offline reply' }]);
  if (status === 200 || status === 401) assert.equal(await auth.logout(), undefined); else await assert.rejects(auth.logout(), e => e.status === status);
  assert.equal(calls[0].url, '/data-service/auth/logout'); assert.equal(calls[0].init.method, 'POST'); assert.equal(calls[0].init.credentials, 'include'); assert.equal(calls[0].init.headers['X-DG-CSRF'], '1'); assert.deepEqual(events, status === 401 ? [AUTH_EXPIRED_EVENT] : []);
});
for (const status of [200, 401, 403]) test(`AUTH-password-${status} unsafe cookie transport no storage`, async () => {
  replies.push([status, { detail: 'Offline reply' }]); if (status === 200) await auth.changePassword('SYNTHETIC-OLD', 'SYNTHETIC-NEW'); else await assert.rejects(auth.changePassword('SYNTHETIC-OLD', 'SYNTHETIC-NEW'), e => e.status === status);
  assert.deepEqual(JSON.parse(calls[0].init.body), { currentPassword: 'SYNTHETIC-OLD', newPassword: 'SYNTHETIC-NEW' }); assert.equal(calls[0].init.headers['X-DG-CSRF'], '1'); assert.equal(storage.size, 0);
});
test('AUTH-storage-clear removes tenant keys and preserves browser display preferences plus foreign namespace', () => {
  for (const key of ['dgv2_project', 'dgv2_owner', 'dgv2_graph_A', 'dgv2_project_shots', 'dgv2_secret_future', 'dgv2_theme', 'dgv2_lang', 'other-app']) storage.set(key, 'synthetic');
  auth.clearTenantBrowserData(); assert.deepEqual([...storage.keys()], ['dgv2_theme', 'dgv2_lang', 'other-app']); auth.clearTenantBrowserData(); assert.equal(storage.size, 3);
});
test('AUTH-legacy-purge deletes old accounts without migration or touching unrelated storage', () => {
  storage.set('dg_users', 'synthetic-old-hash'); storage.set('dg_current_user', 'old-owner'); storage.set('other-app', 'kept'); auth.purgeLegacyLocalAuth(); assert.deepEqual([...storage], [['other-app', 'kept']]); assert.equal(calls.length, 0);
});
test('AUTH-unavailable-storage cleanup safe no network', () => { globalThis.localStorage = { get length() { throw new Error('Blocked'); }, removeItem() { throw new Error('Blocked'); } }; auth.clearTenantBrowserData(); auth.purgeLegacyLocalAuth(); assert.equal(calls.length, 0); });
