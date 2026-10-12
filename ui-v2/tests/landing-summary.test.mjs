import test, { afterEach, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { setLang } from '../src/i18n/index.js';
import { getProjectSummary } from '../src/lib/summaryApi.js';
import { buildLandingSummaries } from '../src/lib/landingSummary.js';

const saved = Object.fromEntries(['window', 'fetch'].map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)]));
let calls;
beforeEach(() => {
  calls = [];
  globalThis.window = { GRAPH_CONFIG: { dataServiceUrl: '/data-service' }, dispatchEvent() {} };
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return new Response(JSON.stringify({ project: 'A/B ?#', graph: { classes: 7, properties: 16, rules: 12 } }), { status: 200 });
  };
  setLang('en');
});
afterEach(() => {
  setLang('en');
  for (const [key, descriptor] of Object.entries(saved)) {
    if (descriptor) Object.defineProperty(globalThis, key, descriptor);
    else delete globalThis[key];
  }
});

const loading = { status: 'loading', data: null };
const source = data => ({ status: 'ok', data });
const graph = (project, summary = loading) => buildLandingSummaries({ project, summary, hostMode: false }).graph;

test('project summary uses encoded project and authenticated GET', async () => {
  const result = await getProjectSummary('A/B ?#');
  assert.equal(result.graph.classes, 7);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, '/data-service/projects/A%2FB%20%3F%23/summary');
  assert.equal(calls[0].init.method, 'GET');
  assert.equal(calls[0].init.credentials, 'include');
  assert.doesNotMatch(JSON.stringify(calls[0]), /authorization|bearer|token/i);
});

test('graph summary is absent while loading and a dash without a project', () => {
  assert.equal(graph('alpha'), null);
  assert.equal(graph(null), '—');
});

test('graph counts are translated and only project-scoped counts are read', () => {
  const data = { project: 'alpha', graph: { classes: 7, properties: 16, rules: 12, secret: 'do-not-show' } };
  assert.deepEqual(graph('alpha', source(data)), [
    { label: 'Classes', value: 7 },
    { label: 'Properties', value: 16 },
    { label: 'Rules', value: 12 }
  ]);
  assert.doesNotMatch(JSON.stringify(graph('alpha', source(data))), /secret|do-not-show/);
  setLang('ru');
  assert.deepEqual(graph('alpha', source(data)).map(part => part.label), ['Классы', 'Свойства', 'Правила']);
});

test('graph errors and foreign project responses never show counts', () => {
  const failed = { status: 'error', data: null };
  assert.deepEqual(graph('alpha', failed).map(part => part.value), ['—', '—', '—']);
  assert.deepEqual(graph('alpha', source({ project: 'beta', graph: { classes: 99 } })).map(part => part.value), ['—', '—', '—']);
});
