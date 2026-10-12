import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { CSRF_HEADER } from '../src/lib/apiClient.js';
import {
  getDegramPolicy,
  policyPatch,
  setDegramPolicy,
  shouldShowProjectSettings
} from '../src/lib/projectSettingsApi.js';

// Phase 1308-10 (D-02, D-17): admin-only export policy client. The routes are admin-only on the
// server; shouldShowProjectSettings only keeps the panel (and its values) away from non-admins.
const saved = Object.fromEntries(['fetch', 'window'].map(k => [k, Object.getOwnPropertyDescriptor(globalThis, k)]));
let calls;
beforeEach(() => {
  calls = [];
  globalThis.window = { GRAPH_CONFIG: { dataServiceUrl: '/data-service' }, dispatchEvent() {} };
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return new Response(JSON.stringify({ project: 'p', providerExportAllowed: true, wholeDefinitionAllowed: false }), { status: 200 });
  };
});
afterEach(() => {
  for (const [key, descriptor] of Object.entries(saved)) {
    if (descriptor) Object.defineProperty(globalThis, key, descriptor);
    else delete globalThis[key];
  }
});

const project = 'A/B ?#';
const policyPath = `/data-service/projects/${encodeURIComponent(project)}/degram-policy`;

test('getDegramPolicy GETs the encoded policy path with the cookie and no CSRF marker', async () => {
  const policy = await getDegramPolicy(project);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, policyPath);
  assert.equal(calls[0].init.method, 'GET');
  assert.equal(calls[0].init.credentials, 'include');
  assert.equal(calls[0].init.headers[CSRF_HEADER], undefined);
  assert.equal(policy.providerExportAllowed, true);
});

test('setDegramPolicy PUTs exactly the given patch with the CSRF marker', async () => {
  await setDegramPolicy(project, { wholeDefinitionAllowed: true });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, policyPath);
  assert.equal(calls[0].init.method, 'PUT');
  assert.equal(calls[0].init.credentials, 'include');
  assert.equal(calls[0].init.headers[CSRF_HEADER], '1');
  assert.deepEqual(JSON.parse(calls[0].init.body), { wholeDefinitionAllowed: true });
  assert.doesNotMatch(JSON.stringify(calls[0]), /dgp_|dgc_|dgk_|authorization|bearer/i);
});

test('setDegramPolicy surfaces ADMIN_REQUIRED and DEGRAM_POLICY_INVALID codes for describeError', async () => {
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: { error: 'Admin only', code: 'ADMIN_REQUIRED' } }), { status: 403 });
  await assert.rejects(() => setDegramPolicy('p', { providerExportAllowed: false }), (err) => err.status === 403 && err.code === 'ADMIN_REQUIRED');
  globalThis.fetch = async () => new Response(JSON.stringify({ detail: { error: 'No flag', code: 'DEGRAM_POLICY_INVALID' } }), { status: 422 });
  await assert.rejects(() => setDegramPolicy('p', {}), (err) => err.status === 422 && err.code === 'DEGRAM_POLICY_INVALID');
});

test('policyPatch carries only the changed flag; equal states give an empty patch', () => {
  assert.deepEqual(
    policyPatch({ providerExportAllowed: true, wholeDefinitionAllowed: false }, { providerExportAllowed: true, wholeDefinitionAllowed: true }),
    { wholeDefinitionAllowed: true }
  );
  assert.deepEqual(
    policyPatch({ providerExportAllowed: true, wholeDefinitionAllowed: true }, { providerExportAllowed: false, wholeDefinitionAllowed: true }),
    { providerExportAllowed: false }
  );
  assert.deepEqual(
    policyPatch({ providerExportAllowed: true, wholeDefinitionAllowed: false }, { providerExportAllowed: true, wholeDefinitionAllowed: false }),
    {}
  );
  assert.deepEqual(
    policyPatch({ providerExportAllowed: true, wholeDefinitionAllowed: false }, { providerExportAllowed: false, wholeDefinitionAllowed: true }),
    { providerExportAllowed: false, wholeDefinitionAllowed: true }
  );
  // only booleans are ever sent
  assert.deepEqual(policyPatch({ providerExportAllowed: true }, { providerExportAllowed: 'no', wholeDefinitionAllowed: undefined }), {});
});

test('shouldShowProjectSettings is true only for a DG admin with a project (D-02, T-1308-10-04)', () => {
  assert.equal(shouldShowProjectSettings({ isAdmin: true }, 'p'), true);
  assert.equal(shouldShowProjectSettings({ isAdmin: false }, 'p'), false);
  assert.equal(shouldShowProjectSettings({ isAdmin: true }, null), false);
  assert.equal(shouldShowProjectSettings({ isAdmin: true }, ''), false);
  assert.equal(shouldShowProjectSettings(null, 'p'), false);
  assert.equal(shouldShowProjectSettings(undefined, 'p'), false);
  assert.equal(shouldShowProjectSettings({ email: 'owner' }, 'p'), false);
  assert.equal(shouldShowProjectSettings({ isAdmin: 'true' }, 'p'), false);
});

test('ProjectsScreen renders ProjectSettingsPanel only behind shouldShowProjectSettings and confirms enabling whole-definition export', async () => {
  const source = await readFile(new URL('../src/screens/ProjectsScreen.jsx', import.meta.url), 'utf8');
  assert.match(source, /function ProjectSettingsPanel\(/);
  assert.match(source, /shouldShowProjectSettings\(user, project\)\s*&&\s*\(?\s*<ProjectSettingsPanel/);
  assert.equal((source.match(/<ProjectSettingsPanel\b/g) || []).length, 1, 'rendered in exactly one place');
  assert.match(source, /setDegramPolicy\(/);
  assert.match(source, /policyPatch\(/);
  assert.match(source, /getDegramPolicy\(/);
  assert.match(source, /"Keep export off"/);
});
