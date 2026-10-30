import test, { afterEach, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { setLang } from '../src/i18n/index.js';
import { getProjectSummary } from '../src/lib/summaryApi.js';
import { buildLandingSummaries, formatActiveNames } from '../src/lib/landingSummary.js';
import { groupRunsByState, NO_STATE } from '../src/lib/runGroups.js';

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

test('shared grouping sorts states and keeps the no-state bucket last', () => {
  const runs = [{ state: { stateId: 'B' } }, { state: { stateId: 'A' } }, { state: { stateId: 'A' } }, {}];
  const groups = groupRunsByState(runs);
  assert.deepEqual(groups.map(group => group.key), ['A', 'B', NO_STATE]);
  assert.deepEqual(groups.map(group => group.runs.length), [2, 1, 1]);
});

test('model summary uses the same group count as Model Viewer', () => {
  const runs = [{ state: { stateId: 'A' } }, { state: { stateId: 'A' } }, { state: { stateId: 'B' } }, {}];
  const model = buildLandingSummaries({ project: 'alpha', runs: source({ project: 'alpha', runs }) }).model;
  assert.deepEqual(model, [{ label: 'Design States', value: 3 }, { label: 'Validation runs', value: 4 }]);
  assert.equal(buildLandingSummaries({ project: null, runs: source({ runs }) }).model, '—');
  assert.deepEqual(buildLandingSummaries({ project: 'alpha', runs: { status: 'error' } }).model.map(part => part.value), ['—', '—']);
});

test('system summaries render only public provider/model and selected reasoner name', () => {
  const data = buildLandingSummaries({
    project: 'alpha',
    llm: source({ provider: 'anthropic', model: 'very-long-model-name', apiKey: 'never-display', apiKeyPreview: 'hidden' }),
    reasoner: source({ selected: 'pellet', reasoners: [{ id: 'pellet', name: 'Pellet' }] })
  });
  assert.deepEqual(data.aiengine, [
    { label: 'Provider', value: 'anthropic' },
    { label: 'Model', value: 'very-long-model-name', title: 'very-long-model-name' }
  ]);
  assert.deepEqual(data.reasoner, [{ label: 'Active', value: 'Pellet' }]);
  assert.doesNotMatch(JSON.stringify(data), /never-display|hidden/);
  const empty = buildLandingSummaries({ llm: source({}), reasoner: source({ selected: null, reasoners: [] }) });
  assert.deepEqual(empty.aiengine.map(part => part.value), ['—', '—']);
  assert.deepEqual(empty.reasoner.map(part => part.value), ['—']);
  const hosted = buildLandingSummaries({ hostMode: true, llm: source({ provider: 'anthropic' }), reasoner: source({ selected: 'pellet' }) });
  assert.equal(hosted.aiengine, null);
  assert.equal(hosted.reasoner, null);
  assert.equal(hosted.connectors, null);
});

test('connector names keep registry order, DeGram last, and cap at two', () => {
  assert.equal(formatActiveNames(['Grasshopper', 'Revit', 'DeGram']), 'Grasshopper, Revit +1');
  assert.equal(formatActiveNames([]), '—');
  const connectors = source({ connectors: [
    { id: 'grasshopper', name: 'Grasshopper', status: 'active' },
    { id: 'degram', name: 'DeGram', status: 'active' },
    { id: 'revit', name: 'Revit', status: 'active' },
    { id: 'dynamo', name: 'Dynamo', status: 'stale' }
  ] });
  const summary = source({ project: 'alpha', connectors: { grantsIssued: 3 } });
  const result = buildLandingSummaries({ project: 'alpha', connectors, summary }).connectors;
  assert.deepEqual(result, [
    { label: 'Active', value: 'Grasshopper, Revit +1' },
    { label: 'Grants issued', value: 3 }
  ]);
  const none = buildLandingSummaries({ project: 'alpha', connectors: source({ connectors: [] }), summary }).connectors;
  assert.equal(none[0].value, '—');
  assert.equal(buildLandingSummaries({ project: null, connectors, summary }).connectors, '—');
});

test('sources fail independently and Russian summary labels match the contract', () => {
  setLang('ru');
  const result = buildLandingSummaries({
    project: 'alpha',
    summary: { status: 'error' },
    runs: source({ project: 'alpha', runs: [] }),
    llm: source({ provider: 'anthropic', model: 'm' }),
    reasoner: { status: 'error' },
    connectors: source({ connectors: [] })
  });
  assert.deepEqual(result.model.map(part => part.label), ['Снимки модели', 'Прогоны валидации']);
  assert.deepEqual(result.aiengine.map(part => part.label), ['Провайдер', 'Модель']);
  assert.deepEqual(result.connectors.map(part => part.label), ['Активно', 'Выдано доступов']);
  assert.deepEqual(result.reasoner.map(part => part.value), ['—']);
  assert.deepEqual(result.graph.map(part => part.value), ['—', '—', '—']);
  assert.deepEqual(result.model.map(part => part.value), [0, 0]);
});
