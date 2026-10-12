import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import * as api from '../src/lib/apiClient.js';
import * as graph from '../src/lib/graphApi.js';
import * as model from '../src/lib/modelApi.js';
import * as inputs from '../src/lib/inputGenApi.js';
import * as llm from '../src/lib/llmApi.js';
import * as connectors from '../src/lib/connectorsApi.js';
import * as reasoner from '../src/lib/reasonerApi.js';

const legacyToken = 'SYNTHETIC-LEGACY-TOKEN-NEVER-SEND';
const originals = Object.fromEntries(['fetch', 'window', 'localStorage'].map(k => [k, Object.getOwnPropertyDescriptor(globalThis, k)]));
let replies, calls, events;
beforeEach(() => {
  replies = []; calls = []; events = [];
  globalThis.window = { GRAPH_CONFIG: { dataServiceUrl: '/data-service///', speckleBaseUrl: '/speckle', neo4jPassword: legacyToken, n8nApiKey: legacyToken, speckleToken: legacyToken }, dispatchEvent(e) { events.push(e.type); } };
  globalThis.localStorage = { getItem() { throw new Error('Client must not read storage'); }, setItem() { throw new Error('Client must not persist tokens'); } };
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    assert.ok(replies.length, `Unexpected request (network forbidden): ${url}`);
    const reply = replies.shift();
    if (reply instanceof Error) throw reply;
    return new Response(reply[0] === 204 ? null : typeof reply[1] === 'string' ? reply[1] : JSON.stringify(reply[1]), { status: reply[0] });
  };
});
afterEach(() => {
  assert.equal(replies.length, 0, 'All scheduled fake replies consumed');
  assert.ok(!JSON.stringify(calls).includes(legacyToken), 'No legacy credential leaked');
  for (const c of calls) {
    assert.equal(c.init.credentials, 'include');
    assert.ok(!Object.keys(c.init.headers).some(k => /authorization|cookie/i.test(k)), 'Identity only via browser cookie handling');
    assert.equal(c.init.headers[api.CSRF_HEADER], ['POST', 'PUT', 'PATCH', 'DELETE'].includes(c.init.method) ? '1' : undefined);
    assert.ok(!/\/neo4j|\/n8n|execution-result\/latest/.test(c.url));
  }
  for (const [k, d] of Object.entries(originals)) { if (d) Object.defineProperty(globalThis, k, d); else delete globalThis[k]; }
});

const project = 'P/A ?#', encoded = encodeURIComponent(project), rule = 'R/1 ?#', er = encodeURIComponent(rule);
// Actual exported wrappers, not replacements: method, exact URL and parsed body.
const cases = [
  ['graph.fetchGraph', () => graph.fetchGraph(project), 'GET', `/data-service/graph/${encoded}`],
  ['graph.tagProjectNodes', () => graph.tagProjectNodes(project), 'POST', `/data-service/graph/${encoded}/claim-untagged`],
  ['graph.updateNodeProp', () => graph.updateNodeProp(project, 42, 'height', 10), 'PUT', `/data-service/graph/${encoded}/node/42/property`, { key: 'height', value: 10 }],
  ['graph.fetchRules', () => graph.fetchRules(project), 'GET', `/data-service/rules/${encoded}`],
  ['graph.fetchRuleDeletePreview', () => graph.fetchRuleDeletePreview(project, rule), 'GET', `/data-service/rules/${encoded}/${er}/delete-preview`],
  ['graph.deleteRule', () => graph.deleteRule(project, rule), 'DELETE', `/data-service/rules/${encoded}/${er}`],
  ['graph.resolveRuleDeletion', () => graph.resolveRuleDeletion(project, 'delete height'), 'POST', '/data-service/rules/resolve-deletion', { project, request: 'delete height' }],
  ['graph.bulkDeleteRules', () => graph.bulkDeleteRules(project, [rule]), 'POST', '/data-service/rules/bulk-delete', { project, ruleIds: [rule] }],
  ['graph.checkRuleConflict', () => graph.checkRuleConflict(project, 'height'), 'POST', '/data-service/rules/check-conflict', { project, rules_text: 'height' }],
  ['graph.supersedeRule', () => graph.supersedeRule(project, rule, 'new'), 'POST', '/data-service/rules/supersede', { project, oldRuleId: rule, newRuleId: 'new', prompt: '' }],
  ['graph.acceptRuleOverlap', () => graph.acceptRuleOverlap(project, rule), 'POST', '/data-service/rules/accept-overlap', { project, ruleId: rule, conflictsWith: [] }],
  ['graph.fetchProjects', () => graph.fetchProjects(), 'GET', '/data-service/projects'],
  ['graph.fetchDrSessions', () => graph.fetchDrSessions(project), 'GET', `/data-service/design-rule-sessions/${encoded}`],
  ['graph.saveDrSession', () => graph.saveDrSession(project, 'create', 'prompt', 'result'), 'POST', '/data-service/design-rule-sessions', { project, mode: 'create', prompt: 'prompt', result: 'result' }, 'best-effort'],
  ['graph.ingestRules', () => graph.ingestRules('height', project), 'POST', '/data-service/workflows/rules-ingest', { project, rulesText: 'height' }, 'workflow'],
  ['graph.queryGraph', () => graph.queryGraph('height?', project), 'POST', '/data-service/workflows/graph-query', { project, prompt: 'height?' }, 'workflow'],
  ['model.fetchValidationRuns', () => model.fetchValidationRuns(project), 'GET', `/data-service/validation/runs/${encoded}`],
  ['model.fetchValidationView', () => model.fetchValidationView(project, 'run/1', rule), 'GET', `/data-service/validation/view/${encoded}/run%2F1/${er}`],
  ['model.fetchRuleDetails', () => model.fetchRuleDetails(rule, project), 'GET', `/data-service/rules/${encoded}/${er}`],
  ['model.fetchEntityStatuses', () => model.fetchEntityStatuses(project, 'run/1', 'dg:x/y'), 'GET', `/data-service/validation/view/${encoded}/run%2F1/entity/dg%3Ax%2Fy`],
  ['inputs.generateInputs', () => inputs.generateInputs(project, 'def', rule, 2, [{ dgId: 'dg:1', value: 3 }]), 'POST', '/data-service/computgraph/generate-inputs', { project, ruleId: rule, definitionId: 'def', candidateCount: 2, parameterOverrides: [{ dgId: 'dg:1', value: 3 }] }],
  ['inputs.acceptCandidate', () => inputs.acceptCandidate(project, 'def', rule, { id: 'candidate', values: [1] }), 'POST', '/data-service/computgraph/candidates/accept', { project, definitionId: 'def', ruleId: rule, candidate: { id: 'candidate', values: [1] } }],
  ['inputs.fetchAcceptedCandidates', () => inputs.fetchAcceptedCandidates(project, rule), 'GET', `/data-service/computgraph/candidates/${encoded}?ruleId=${er}`],
  ['connectors.listConnectors', () => connectors.listConnectors(), 'GET', '/data-service/connectors'],
  ['connectors.createCredential', () => connectors.createCredential('C/1', 'label', project), 'POST', '/data-service/connectors/C%2F1/credentials', { project, label: 'label' }],
  ['connectors.revokeCredential', () => connectors.revokeCredential('C/1', 'key/1'), 'DELETE', '/data-service/connectors/C%2F1/credentials/key%2F1'],
  ['connectors.listProjectGrants', () => connectors.listProjectGrants(project), 'GET', `/data-service/projects/${encoded}/degram-grants`],
  ['connectors.issueGrant', () => connectors.issueGrant(project, { username: 'member', label: 'Studio', purpose: 'Review' }), 'POST', `/data-service/projects/${encoded}/degram-grants`, { username: 'member', label: 'Studio', purpose: 'Review' }],
  ['connectors.revokeGrant', () => connectors.revokeGrant(project, 'grant/1'), 'DELETE', `/data-service/projects/${encoded}/degram-grants/grant%2F1`],
  ['connectors.listMyGrants', () => connectors.listMyGrants(), 'GET', '/data-service/degram/grants/mine'],
  ['connectors.requestGrant', () => connectors.requestGrant(project, 'Review access'), 'POST', '/data-service/degram/grant-requests', { project, note: 'Review access' }],
  ['llm.getSettings', () => llm.getSettings(), 'GET', '/llm/settings'],
  ['llm.saveSettings', () => llm.saveSettings({ provider: 'offline', model: 'stub' }), 'PUT', '/llm/settings', { provider: 'offline', model: 'stub' }],
  ['llm.testConnection', () => llm.testConnection(), 'POST', '/llm/settings/test', {}],
  ['llm.fetchModels', () => llm.fetchModels('offline/a'), 'GET', '/llm/models?provider=offline%2Fa'],
  ['reasoner.getReasonerSettings', () => reasoner.getReasonerSettings(), 'GET', '/reasoner/settings'],
  ['reasoner.runConsistencyCheck', () => reasoner.runConsistencyCheck(project), 'POST', '/reasoner/consistency', { project, engine: 'hermit' }, 'passthrough'],
  ['reasoner.selectReasoner', () => reasoner.selectReasoner('hermit'), 'PUT', '/reasoner/settings', { reasoner: 'hermit' }]
];
for (const [name, invoke, method, url, body, mode] of cases) {
  for (const status of [200, 401, 403]) {
    test(`API-${name}-${status} scoped cookie/CSRF and denial boundary`, async () => {
      const denied = { detail: { error: 'Denied', code: 'PROJECT_FORBIDDEN', hint: 'Request membership' } };
      if (mode === 'workflow' && status === 200) replies.push([202, { status: 'accepted', executionId: 'owned/1' }], [200, { status: 'completed', payload: { answer: 'owned' } }]);
      else replies.push([status, status === 200 ? {} : denied]);
      if (status === 200) await invoke();
      else if (mode === 'best-effort') assert.equal(await invoke(), null);
      else if (mode === 'passthrough') assert.deepEqual(await invoke(), { ok: false, status, body: denied });
      else await assert.rejects(invoke(), e => e.status === status && e.code === 'PROJECT_FORBIDDEN' && e.hint === 'Request membership');
      assert.equal(calls[0].url, url); assert.equal(calls[0].init.method, method);
      assert.deepEqual(calls[0].init.body === undefined ? undefined : JSON.parse(calls[0].init.body), body);
      assert.deepEqual(events, status === 401 ? [api.AUTH_EXPIRED_EVENT] : []);
      assert.equal(calls.length, mode === 'workflow' && status === 200 ? 2 : 1);
    });
  }
}

test('TRANSPORT-01 config returns endpoints only', () => { assert.deepEqual(api.getConfig(), { dataServiceUrl: '/data-service///', speckleBaseUrl: '/speckle' }); assert.equal(api.dataServiceBase(), '/data-service'); });
for (const method of ['GET', 'HEAD', 'post', 'PUT', 'PATCH', 'DELETE']) test(`TRANSPORT-method-${method} exact CSRF handling`, async () => {
  replies.push([204, null]); assert.equal(await api.apiFetch('/data-service/check', { method, headers: { 'X-Test': 'preserved' } }), null);
  assert.equal(calls[0].init.headers['X-Test'], 'preserved'); assert.equal(calls[0].init.method, method.toUpperCase());
});
test('TRANSPORT-02 404 nullable rule details is not a denied success', async () => {
  replies.push([404, { detail: 'Unknown or foreign rule' }]); assert.equal(await model.fetchRuleDetails(rule, project), null);
});
test('TRANSPORT-03 network failures remain errors without retry or auth-expiry', async () => {
  replies.push(new TypeError('Synthetic offline failure')); await assert.rejects(graph.fetchGraph(project), /Synthetic offline failure/); assert.equal(calls.length, 1); assert.deepEqual(events, []);
});
test('TRANSPORT-04 passthrough preserves denial and abort signal', async () => {
  const controller = new AbortController(); replies.push([504, { semantic: 'timeout' }]);
  assert.deepEqual(await reasoner.runConsistencyCheck(project, { signal: controller.signal }), { ok: false, status: 504, body: { semantic: 'timeout' } }); assert.equal(calls[0].init.signal, controller.signal);
});
test('TRANSPORT-05 empty scopes no request where wrapper explicitly supports it', async () => {
  assert.deepEqual(await graph.fetchGraph(''), { nodes: [], rels: [] }); assert.deepEqual(await graph.fetchRules(''), []); await graph.tagProjectNodes(''); assert.equal(await model.fetchRuleDetails(rule, ''), null); assert.equal(calls.length, 0);
});
test('TRANSPORT-06 separate project calls never reuse foreign graph or read-token state', async () => {
  replies.push([200, { nodes: [{ id: 'only-A' }], rels: [] }], [403, { detail: 'Denied B' }], [200, { nodes: [{ id: 'only-C' }], rels: [] }]);
  assert.deepEqual((await graph.fetchGraph('A')).nodes, [{ id: 'only-A' }]); await assert.rejects(graph.fetchGraph('B'), e => e.status === 403); assert.deepEqual((await graph.fetchGraph('C')).nodes, [{ id: 'only-C' }]);
  replies.push([200, { speckleToken: 'SYNTHETIC-READ-A' }], [403, { detail: 'Denied B' }]);
  assert.equal((await model.fetchValidationView('A', 'run')).speckleToken, 'SYNTHETIC-READ-A'); await assert.rejects(model.fetchValidationView('B', 'run'), e => e.status === 403); assert.ok(!JSON.stringify(calls).includes('SYNTHETIC-READ-A'));
});
for (const status of [401, 403, 404]) test(`WORKFLOW-poll-${status} terminal denial no fallback or foreign payload`, async () => {
  replies.push([202, { status: 'accepted', executionId: 'foreign/id' }], [status, { detail: 'Denied' }]);
  await assert.rejects(graph.queryGraph('offline', project), e => status === 404 ? /not found or not permitted/.test(e.message) : e.status === status);
  assert.equal(calls.length, 2); assert.equal(calls[1].url, '/data-service/execution-result/foreign%2Fid'); assert.deepEqual(events, status === 401 ? [api.AUTH_EXPIRED_EVENT] : []);
});
test('WORKFLOW-no-id rejected no latest execution lookup', async () => { replies.push([202, { status: 'accepted' }]); await assert.rejects(graph.ingestRules('offline', project), /execution id/); assert.equal(calls.length, 1); });
for (const status of ['failed', 'cancelled']) test(`WORKFLOW-${status} terminal`, async () => { replies.push([202, { status: 'accepted', executionId: 'owned' }], [200, { status, message: 'Offline failed' }]); await assert.rejects(graph.ingestRules('offline', project), status === 'failed' ? /Offline failed/ : /cancelled/); assert.equal(calls.length, 2); });
test('MEMBER-01 LAST_OWNER structured 409 preserved by actual shared transport', async () => { replies.push([409, { detail: { error: 'Cannot remove last owner', code: 'LAST_OWNER' } }]); await assert.rejects(api.apiFetch('/data-service/projects/P/members/owner', { method: 'DELETE' }), e => e instanceof api.ApiError && e.status === 409 && e.code === 'LAST_OWNER'); });
