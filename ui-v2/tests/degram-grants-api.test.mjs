import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { CSRF_HEADER } from '../src/lib/apiClient.js';
import { issueGrant, listMyGrants, listProjectGrants, requestGrant, revokeGrant } from '../src/lib/connectorsApi.js';

const saved = Object.fromEntries(['fetch', 'window'].map(k => [k, Object.getOwnPropertyDescriptor(globalThis, k)]));
let calls;
beforeEach(() => {
  calls = [];
  globalThis.window = { GRAPH_CONFIG: { dataServiceUrl: '/data-service' }, dispatchEvent() {} };
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return new Response(init.method === 'DELETE' ? null : '{}', { status: init.method === 'DELETE' ? 204 : 200 });
  };
});
afterEach(() => {
  for (const [key, descriptor] of Object.entries(saved)) {
    if (descriptor) Object.defineProperty(globalThis, key, descriptor);
    else delete globalThis[key];
  }
});
const project = 'A/B ?#';
const path = `/data-service/projects/${encodeURIComponent(project)}/degram-grants`;
for (const [name, call, method, url, body] of [
  ['listProjectGrants', () => listProjectGrants(project), 'GET', path],
  ['issueGrant', () => issueGrant(project, { username: 'member', label: 'Studio', purpose: 'Review' }), 'POST', path, { username: 'member', label: 'Studio', purpose: 'Review' }],
  ['revokeGrant', () => revokeGrant(project, 'g/1'), 'DELETE', `${path}/g%2F1`],
  ['listMyGrants', () => listMyGrants(), 'GET', '/data-service/degram/grants/mine'],
  ['requestGrant', () => requestGrant(project, 'Review'), 'POST', '/data-service/degram/grant-requests', { project, note: 'Review' }]
]) {
  test(`${name} uses scoped cookie/CSRF transport without a key`, async () => {
    await call();
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, url);
    assert.equal(calls[0].init.method, method);
    assert.equal(calls[0].init.credentials, 'include');
    assert.equal(calls[0].init.headers[CSRF_HEADER], method === 'GET' ? undefined : '1');
    assert.deepEqual(calls[0].init.body === undefined ? undefined : JSON.parse(calls[0].init.body), body);
    assert.doesNotMatch(JSON.stringify(calls[0]), /dgp_|authorization|bearer/i);
  });
}
