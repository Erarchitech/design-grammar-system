import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { CSRF_HEADER } from '../src/lib/apiClient.js';
import { listProjectMembers } from '../src/lib/memberApi.js';
import {
  issueConnectorAccess,
  listConnectors,
  listMyConnectorAccess,
  listProjectConnectorAccess,
  requestConnectorAccess,
  revokeConnectorAccess
} from '../src/lib/connectorsApi.js';

// Phase 1301-40 (D-46): per-connector access client. Cookie session + CSRF
// marker, never a bearer, and no key anywhere in the call.
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
const accessPath = `/data-service/projects/${encodeURIComponent(project)}/connector-access`;

for (const [name, call, method, url, body] of [
  ['listConnectors (no project)', () => listConnectors(), 'GET', '/data-service/connectors'],
  ['listConnectors (project)', () => listConnectors(project), 'GET', `/data-service/connectors?project=${encodeURIComponent(project)}`],
  ['requestConnectorAccess', () => requestConnectorAccess(project, 'revit', 'Review'), 'POST', '/data-service/connector-access-requests', { project, connector_id: 'revit', note: 'Review' }],
  ['listMyConnectorAccess', () => listMyConnectorAccess(), 'GET', '/data-service/connector-access/mine'],
  ['listProjectConnectorAccess', () => listProjectConnectorAccess(project), 'GET', accessPath],
  ['listProjectMembers', () => listProjectMembers(project), 'GET', `/data-service/projects/${encodeURIComponent(project)}/members`],
  ['issueConnectorAccess', () => issueConnectorAccess(project, { username: 'member', connectorId: 'revit' }), 'POST', accessPath, { username: 'member', connector_id: 'revit' }],
  ['revokeConnectorAccess', () => revokeConnectorAccess(project, 'a/1'), 'DELETE', `${accessPath}/a%2F1`]
]) {
  test(`${name} uses scoped cookie/CSRF transport without a key`, async () => {
    await call();
    assert.equal(calls.length, 1);
    assert.equal(calls[0].url, url);
    assert.equal(calls[0].init.method, method);
    assert.equal(calls[0].init.credentials, 'include');
    assert.equal(calls[0].init.headers[CSRF_HEADER], method === 'GET' ? undefined : '1');
    assert.deepEqual(calls[0].init.body === undefined ? undefined : JSON.parse(calls[0].init.body), body);
    assert.doesNotMatch(JSON.stringify(calls[0]), /dgp_|dgc_|authorization|bearer/i);
  });
}
