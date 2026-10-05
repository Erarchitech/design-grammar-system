// Phase 1301 plan 09 (D-21, DGCL-03): the Model Viewer loads geometry only through the
// project-authorised DG proxy. No Speckle credential exists in the browser, so nothing
// here may ever carry one: no token argument, no Authorization header, no token in a
// URL, the bundle or the runtime config.
import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, statSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as proxy from '../src/lib/speckleProxy.js';
import { CSRF_HEADER } from '../src/lib/apiClient.js';

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, '..');
const read = (rel) => readFileSync(join(root, rel), 'utf8');

const SPID = 'abcdef0123';
const ROOT = 'a'.repeat(32);
const CHILD = 'c'.repeat(32);
const PREFIX = '/data-service/speckle-proxy/P1';
const RESOURCE = `${PREFIX}/objects/${SPID}/${ROOT}`;
const SYNTHETIC_TOKEN = 'SYNTHETIC-SPECKLE-READ-TOKEN-NEVER-IN-BROWSER';

const originals = Object.fromEntries(['fetch', 'window', 'indexedDB', 'localStorage'].map((k) => [k, Object.getOwnPropertyDescriptor(globalThis, k)]));
let calls;
beforeEach(() => {
  calls = [];
  // setTimeout/clearTimeout: ObjectLoader2's batching queue binds them off `window` when one exists.
  globalThis.window = { setTimeout: globalThis.setTimeout.bind(globalThis), clearTimeout: globalThis.clearTimeout.bind(globalThis), GRAPH_CONFIG: { dataServiceUrl: '/data-service', speckleBaseUrl: 'http://localhost:8090', speckleReadToken: SYNTHETIC_TOKEN } };
  Object.defineProperty(globalThis, 'indexedDB', { configurable: true, get() { throw new Error('geometry must not be persisted to IndexedDB'); } });
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, get() { throw new Error('the loader must not read stored tokens'); } });
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), init: init || {} });
    if (String(url).endsWith('/single')) {
      return new Response(JSON.stringify({ id: ROOT, speckle_type: 'Base', __closure: { [CHILD]: 1 }, totalChildrenCount: 1 }), { status: 200 });
    }
    if (!String(url).endsWith('/object-stream/')) return new Response('ok', { status: 200 });
    const body = JSON.parse(init.body);
    return new Response(body.objectIds.map((id) => `${id}\t${JSON.stringify({ id, speckle_type: 'Base' })}\n`).join(''), { status: 200 });
  };
});
afterEach(() => {
  for (const [k, d] of Object.entries(originals)) { if (d) Object.defineProperty(globalThis, k, d); else delete globalThis[k]; }
});

// -- resource parsing --------------------------------------------------------------

test('parseViewerResource splits a proxy object URL into server, project and object', () => {
  assert.deepEqual(proxy.parseViewerResource(RESOURCE), { serverUrl: PREFIX, streamId: SPID, objectId: ROOT });
  assert.deepEqual(
    proxy.parseViewerResource(`/mount/x/speckle-proxy/P%2F1/objects/${SPID}/${ROOT}`),
    { serverUrl: '/mount/x/speckle-proxy/P%2F1', streamId: SPID, objectId: ROOT }
  );
});

for (const [name, value] of [
  ['absolute http URL', `http://speckle.example${RESOURCE}`],
  ['absolute https URL', `https://localhost:8090${RESOURCE}`],
  ['protocol-relative URL', `//evil.example${RESOURCE}`],
  ['a Speckle viewer URL', `http://localhost:8090/projects/${SPID}/models/bm@bv`],
  ['an old streams URL', `http://localhost:8090/streams/${SPID}/objects/${ROOT}`],
  ['an uppercase hash', `${PREFIX}/objects/${SPID}/${'A'.repeat(32)}`],
  ['a short hash', `${PREFIX}/objects/${SPID}/${'a'.repeat(31)}`],
  ['a traversal segment', `${PREFIX}/objects/${SPID}/../../${ROOT}`],
  ['a query string carrying a token', `${RESOURCE}?token=${SYNTHETIC_TOKEN}`],
  ['a fragment', `${RESOURCE}#x`],
  ['an extra path segment', `${RESOURCE}/single`],
  ['a different proxy path', `/data-service/other/P1/objects/${SPID}/${ROOT}`],
  ['an empty value', ''],
  ['a non-string', 42],
  ['null', null],
]) {
  test(`parseViewerResource refuses ${name}`, () => assert.equal(proxy.parseViewerResource(value), null));
}

// -- the fetch the loader uses ---------------------------------------------------------

test('speckleProxyFetch is a credentialed same-origin fetch that never carries an Authorization header', async () => {
  await proxy.speckleProxyFetch(`${PREFIX}/x`, { headers: { Authorization: `Bearer ${SYNTHETIC_TOKEN}`, authorization: 'x', Cookie: 'c=1', Accept: 'text/plain' } });
  const { init } = calls[0];
  assert.equal(init.credentials, 'include');
  assert.deepEqual(Object.keys(init.headers).map((k) => k.toLowerCase()).sort(), ['accept']);
  assert.ok(!JSON.stringify(calls).includes(SYNTHETIC_TOKEN));
});

test('speckleProxyFetch adds the CSRF header to POST only', async () => {
  await proxy.speckleProxyFetch(`${PREFIX}/x`, { method: 'GET' });
  await proxy.speckleProxyFetch(`${PREFIX}/x`);
  await proxy.speckleProxyFetch(`${PREFIX}/x`, { method: 'post', body: '{}' });
  assert.equal(calls[0].init.headers[CSRF_HEADER], undefined);
  assert.equal(calls[1].init.headers[CSRF_HEADER], undefined);
  assert.equal(calls[2].init.headers[CSRF_HEADER], '1');
});

test('speckleProxyFetch refuses a URL that is not under /speckle-proxy/ without calling fetch', async () => {
  for (const url of ['http://localhost:8090/objects/x/y/single', 'https://evil.example/', '//evil.example/', '/data-service/graph/P1', '/graphql']) {
    await assert.rejects(proxy.speckleProxyFetch(url), /speckle-proxy/);
  }
  assert.equal(calls.length, 0);
});

// -- the real Speckle object loader against the proxy ------------------------------

test('the real ObjectLoader2 loads a resource through the proxy URL shapes, with no token and no cache', async () => {
  const loader = proxy.createProxyObjectLoader(RESOURCE);
  const rootObject = await loader.getRootObject();
  assert.equal(rootObject.baseId, ROOT);
  const seen = [];
  for await (const item of loader.getObjectIterator()) seen.push(item.baseId);
  await loader.disposeAsync();
  assert.ok(seen.length >= 1);

  assert.deepEqual(calls.map((c) => c.url), [
    `${PREFIX}/objects/${SPID}/${ROOT}/single`,
    `${PREFIX}/api/v2/projects/${SPID}/object-stream/`,
  ]);
  assert.deepEqual(calls.map((c) => c.init.method || 'GET'), ['GET', 'POST']);
  for (const call of calls) {
    assert.match(call.url, /^\/data-service\/speckle-proxy\/P1\//, 'only the DG proxy is ever contacted');
    assert.equal(call.init.credentials, 'include');
    assert.ok(!Object.keys(call.init.headers || {}).some((k) => /^(authorization|cookie)$/i.test(k)), 'no credential header');
  }
  assert.equal(calls[0].init.headers[CSRF_HEADER], undefined);
  assert.equal(calls[1].init.headers[CSRF_HEADER], '1');
  assert.ok(!JSON.stringify(calls).includes(SYNTHETIC_TOKEN), 'the runtime config token never reaches a request');
  assert.ok(JSON.parse(calls[1].init.body).objectIds.every((id) => /^[0-9a-f]{32}$/.test(id)));
});

test('createProxyObjectLoader refuses a resource that is not a proxy URL', () => {
  assert.throws(() => proxy.createProxyObjectLoader(`http://localhost:8090/streams/${SPID}/objects/${ROOT}`), /proxy/i);
  assert.equal(calls.length, 0);
});

test('a denied proxy answer surfaces as a loader error, never a retry with a token', async () => {
  globalThis.fetch = async (url, init) => { calls.push({ url: String(url), init }); return new Response('{}', { status: 403 }); };
  const loader = proxy.createProxyObjectLoader(RESOURCE);
  await assert.rejects(loader.getRootObject(), /access|403/i);
  assert.equal(calls.length, 1);
  await loader.disposeAsync().catch(() => {});
});

// -- no token plumbing left in the client ---------------------------------------------

test('SpeckleViewport loads through the proxy loader and no longer touches tokens or UrlHelper', () => {
  const src = read('src/components/speckle/SpeckleViewport.jsx');
  assert.match(src, /speckleProxy/);
  assert.match(src, /speckle-proxy/);
  assert.ok(!/UrlHelper/.test(src), 'UrlHelper.getResourceUrls queries Speckle GraphQL from the browser');
  assert.ok(!/readToken|authToken|Bearer|localStorage/.test(src));
  assert.ok(!/new SpeckleLoader\(/.test(src), 'the stock SpeckleLoader takes a token argument and the Speckle origin');
});

test('ModelScreen and modelApi no longer read or pass a Speckle token', () => {
  for (const rel of ['src/screens/ModelScreen.jsx', 'src/lib/modelApi.js']) {
    const src = read(rel);
    assert.ok(!/readToken|speckleToken|speckleBaseUrl/.test(src), `${rel} must not handle a Speckle credential`);
  }
  assert.match(read('src/screens/ModelScreen.jsx'), /viewerResources/);
});

test('the runtime config generators copy no Speckle token into the browser', () => {
  for (const rel of ['gen-config.sh', 'entrypoint.sh']) {
    assert.ok(!/READ_TOKEN|WRITE_TOKEN|speckleReadToken|readToken/i.test(read(rel)), rel);
  }
});

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const full = join(dir, name);
    if (statSync(full).isDirectory()) yield* walk(full);
    else yield full;
  }
}

test('no client source file names a Speckle read token field', () => {
  const offenders = [];
  for (const file of walk(join(root, 'src'))) {
    if (!/\.(js|jsx|mjs|css|html)$/.test(file)) continue;
    if (/readToken|SPECKLE_READ_TOKEN|speckleReadToken/.test(readFileSync(file, 'utf8'))) offenders.push(file);
  }
  assert.deepEqual(offenders, []);
});

test('a built bundle, when present, contains no read-token field and no synthetic credential', { skip: !existsSync(join(root, 'dist', 'assets')) }, () => {
  const offenders = [];
  for (const file of walk(join(root, 'dist'))) {
    if (!/\.(js|html)$/.test(file)) continue;
    const text = readFileSync(file, 'utf8');
    if (/readToken|SPECKLE_READ_TOKEN|speckleReadToken/.test(text)) offenders.push(file);
  }
  assert.deepEqual(offenders, [], 'the built bundle must not carry a read-token field');
  const config = join(root, 'dist', 'config.js');
  if (existsSync(config)) assert.ok(!/token/i.test(readFileSync(config, 'utf8')));
});
