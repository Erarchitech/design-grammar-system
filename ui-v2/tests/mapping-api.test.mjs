import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
import { CSRF_HEADER } from '../src/lib/apiClient.js';
import {
  ITEM_KINDS,
  MAPPING_STATES,
  MAX_ELEMENTS,
  answerUndoable,
  appliedByClass,
  applySession,
  awaitingApply,
  calculatorConfirmPayload,
  calculatorConfirmable,
  cardOpen,
  classLabels,
  classLocalName,
  confidencePercent,
  confirmCalculator,
  consequenceRows,
  createProfile,
  createSession,
  getSession,
  includedGroupIds,
  itemView,
  labelFromFileName,
  listCalculatorCandidates,
  listProfiles,
  listSessions,
  mergeProfiles,
  optionKind,
  parseDescriptorUpload,
  pendingAnswerIds,
  postDecision,
  progressSegments,
  proposalItems,
  proposalTitle,
  questionText,
  rejectCalculator,
  retireCalculator,
  selectorEntries,
  sessionAnswers,
  sessionSummary,
  summaryTotals,
  toggleCard,
  undoAnswer,
  upsertSession
} from '../src/lib/mappingApi.js';

// Phase 1303-05 (D-18, D-21, D-29): Mapping panel client, built against 1303-API-CONTRACT v0.1 before the routes
// exist. Only fetch is stubbed; no request leaves the process.
const saved = Object.fromEntries(['fetch', 'window'].map(k => [k, Object.getOwnPropertyDescriptor(globalThis, k)]));
let calls, reply;
beforeEach(() => {
  calls = [];
  reply = [200, { ok: true }];
  globalThis.window = { GRAPH_CONFIG: { dataServiceUrl: '/data-service' }, dispatchEvent() {} };
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return new Response(JSON.stringify(reply[1]), { status: reply[0] });
  };
});
afterEach(() => {
  for (const call of calls) {
    assert.equal(call.init.credentials, 'include', 'cookie mode');
    assert.ok(!Object.keys(call.init.headers).some(k => /authorization|cookie/i.test(k)), 'no token header');
    assert.doesNotMatch(JSON.stringify(call), /dgp_|dgc_|dgk_|bearer/i);
  }
  for (const [key, descriptor] of Object.entries(saved)) {
    if (descriptor) Object.defineProperty(globalThis, key, descriptor);
    else delete globalThis[key];
  }
});

const project = 'A/B ?#';
const qp = `project=${encodeURIComponent(project)}`;
const sid = 'ms-0123 /?#';
const sessionPath = `/data-service/mapping/sessions/${encodeURIComponent(sid)}`;
const body = (i = 0) => JSON.parse(calls[i].init.body);

// Plans 1303-16 and 1303-17: nine store codes and three route-level codes (D-60 adds the owner one): twelve in all.
const CALCULATOR_ERROR_CODES = [
  'CALCULATOR_NOT_FOUND', 'CALCULATOR_NOT_PENDING', 'CALCULATOR_CHANGED', 'CALCULATOR_INTEGRITY',
  'CALCULATOR_RUN_NOT_FOUND', 'CALCULATOR_RUN_INVALID', 'CALCULATOR_INPUT_INVALID', 'CALCULATOR_IN_CATALOGUE',
  'CATALOGUE_COMPANY_REQUIRED', 'CATALOGUE_PROPERTY_TAKEN', 'CATALOGUE_ENTRY_NOT_FOUND', 'CATALOGUE_RECONFIRM_OWNER_REQUIRED'
];

test('listSessions GETs the project-scoped list with an optional limit and no CSRF marker', async () => {
  reply = [200, { sessions: [{ sessionId: 'ms-1' }] }];
  const res = await listSessions(project, 20);
  await listSessions(project);
  await listSessions(project, 0);
  assert.deepEqual(res, { sessions: [{ sessionId: 'ms-1' }] });
  assert.deepEqual(calls.map(c => c.url), [
    `/data-service/mapping/sessions?${qp}&limit=20`,
    `/data-service/mapping/sessions?${qp}`,
    `/data-service/mapping/sessions?${qp}`
  ]);
  for (const call of calls) {
    assert.equal(call.init.method, 'GET');
    assert.equal(call.init.headers[CSRF_HEADER], undefined);
    assert.equal(call.init.body, undefined);
  }
});

test('getSession GETs the encoded session id with the project in the query', async () => {
  await getSession(project, sid);
  assert.equal(calls[0].url, `${sessionPath}?${qp}`);
  assert.equal(calls[0].init.method, 'GET');
  assert.equal(calls[0].init.headers[CSRF_HEADER], undefined);
});

test('createSession POSTs only contract fields with the active project and the CSRF marker', async () => {
  const elements = [{ nativeId: 'gh:f:HU:{0;0}:0' }];
  await createSession(project, { project: 'FOREIGN', platform: 'grasshopper', label: 'act1', elements, context: { populationsFromSessionId: 'ms-0' }, source: { document: 'x' } });
  assert.equal(calls[0].url, '/data-service/mapping/sessions');
  assert.equal(calls[0].init.method, 'POST');
  assert.equal(calls[0].init.headers[CSRF_HEADER], '1');
  assert.deepEqual(body(), { project, platform: 'grasshopper', label: 'act1', elements, context: { populationsFromSessionId: 'ms-0' } });
  await createSession(project, { platform: 'revit', elements, label: '', context: [] });
  assert.deepEqual(body(1), { project, platform: 'revit', elements }, 'empty label and a non-object context are not sent');
});

test('postDecision POSTs one decision; groupIds, roles and comment only when given', async () => {
  await postDecision(project, sid, { questionId: 'Q-1', optionId: 'accept-all', groupIds: ['G-1', 'G-3'] });
  assert.equal(calls[0].url, `${sessionPath}/decisions`);
  assert.equal(calls[0].init.method, 'POST');
  assert.equal(calls[0].init.headers[CSRF_HEADER], '1');
  assert.deepEqual(body(), { project, questionId: 'Q-1', optionId: 'accept-all', groupIds: ['G-1', 'G-3'] });
  await postDecision(project, sid, { questionId: 'Q-2', optionId: 'class:ex:GroundFloorUnit' });
  assert.deepEqual(body(1), { project, questionId: 'Q-2', optionId: 'class:ex:GroundFloorUnit' });
  await postDecision(project, sid, { questionId: 'Q-2', optionId: 'both', roles: ['ex:A', 'ex:B'], comment: '  ok  ' });
  assert.deepEqual(body(2), { project, questionId: 'Q-2', optionId: 'both', roles: ['ex:A', 'ex:B'], comment: 'ok' });
});

test('applySession POSTs only the explicit accepted answer set and stable retry identity', async () => {
  const intent = { requestId: 'batch-four', revision: 'a'.repeat(24), answerIds: ['A-1', 'A-2', 'A-3', 'A-4'] };
  reply = [200, { batchId: 'batch-four', payload: { applied: 4 }, delivery: { state: 'queued' } }];
  const res = await applySession(project, sid, intent);
  await applySession(project, sid, intent);
  assert.equal(calls[0].url, `${sessionPath}/apply`);
  assert.equal(calls[0].init.method, 'POST');
  assert.equal(calls[0].init.headers[CSRF_HEADER], '1');
  assert.deepEqual(body(), { project, ...intent });
  assert.deepEqual(body(1), body(), 'a retry preserves request identity');
  assert.equal(res.payload.applied, 4);
  assert.equal(res.delivery.state, 'queued', 'server confirmation does not claim CAD success');
});

test('applySession refuses empty or implicit apply without sending a request', async () => {
  await assert.rejects(() => applySession(project, sid), err => err.code === 'MAPPING_COMMIT_REQUIRED');
  await assert.rejects(() => applySession(project, sid, { requestId: 'batch-one', revision: 'a'.repeat(24), answerIds: [] }));
  assert.equal(calls.length, 0);
});

test('undoAnswer POSTs the project and the answer id to the session undo route with the CSRF marker (contract §7.2)', async () => {
  reply = [200, { sessionId: sid, questions: [{ questionId: 'Q-1' }], answers: [] }];
  const res = await undoAnswer(project, sid, 'A-0123');
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `${sessionPath}/undo`);
  assert.equal(calls[0].init.method, 'POST');
  assert.equal(calls[0].init.headers[CSRF_HEADER], '1');
  assert.deepEqual(body(), { project, answerId: 'A-0123' }, 'only project and answerId travel');
  assert.deepEqual(res, { sessionId: sid, questions: [{ questionId: 'Q-1' }], answers: [] }, 'the recomputed session is returned as is');
  reply = [409, { detail: { error: 'Applied', code: 'MAPPING_SESSION_APPLIED' } }];
  await assert.rejects(() => undoAnswer(project, sid, 'A-0123'), err => err.status === 409 && err.code === 'MAPPING_SESSION_APPLIED');
  reply = [404, { detail: { error: 'Gone', code: 'MAPPING_ANSWER_NOT_FOUND' } }];
  await assert.rejects(() => undoAnswer(project, sid, 'A-gone'), err => err.status === 404 && err.code === 'MAPPING_ANSWER_NOT_FOUND');
  const { EN, RU } = await import('../src/i18n/dict/index.js');
  for (const code of ['MAPPING_SESSION_APPLIED', 'MAPPING_ANSWER_NOT_FOUND']) {
    assert.equal(typeof EN[`error.${code}`], 'string', `EN ${code}`);
    assert.equal(typeof RU[`error.${code}`], 'string', `RU ${code}`);
    assert.notEqual(EN[`error.${code}`], RU[`error.${code}`], code);
  }
});

test('listProfiles GETs and createProfile POSTs the authored profile', async () => {
  await listProfiles(project);
  assert.equal(calls[0].url, `/data-service/mapping/profiles?${qp}`);
  assert.equal(calls[0].init.method, 'GET');
  await createProfile(project, { platform: 'revit', selector: { family: 'Facade_Module_Hex' }, roles: ['ex:HexagonalUnit'], comment: 'family name' });
  assert.equal(calls[1].url, '/data-service/mapping/profiles');
  assert.equal(calls[1].init.method, 'POST');
  assert.equal(calls[1].init.headers[CSRF_HEADER], '1');
  assert.deepEqual(body(1), { project, platform: 'revit', selector: { family: 'Facade_Module_Hex' }, roles: ['ex:HexagonalUnit'], comment: 'family name' });
});

test('mapping error codes reach describeError through ApiError', async () => {
  reply = [404, { detail: { error: 'Unknown session', code: 'MAPPING_SESSION_NOT_FOUND' } }];
  await assert.rejects(() => getSession(project, 'ms-gone'), err => err.status === 404 && err.code === 'MAPPING_SESSION_NOT_FOUND');
  reply = [400, { detail: { error: 'Bad option', code: 'MAPPING_OPTION_INVALID' } }];
  await assert.rejects(() => postDecision(project, sid, { questionId: 'Q-1', optionId: 'x' }), err => err.status === 400 && err.code === 'MAPPING_OPTION_INVALID');
  reply = [400, { detail: { error: 'Too many', code: 'MAPPING_TOO_MANY_ELEMENTS' } }];
  await assert.rejects(() => createSession(project, { platform: 'grasshopper', elements: [] }), err => err.code === 'MAPPING_TOO_MANY_ELEMENTS');
});

test('mapping error codes have EN and RU texts and describeError maps them', async () => {
  const { EN, RU } = await import('../src/i18n/dict/index.js');
  const i18n = await import('../src/i18n/index.js');
  const codes = ['MAPPING_SESSION_NOT_FOUND', 'MAPPING_QUESTION_NOT_FOUND', 'MAPPING_OPTION_INVALID', 'MAPPING_INPUT_INVALID', 'MAPPING_TOO_MANY_ELEMENTS', 'MAPPING_COMMIT_REQUIRED', 'MAPPING_COMMIT_CONFLICT', 'MAPPING_ANSWER_COMMITTED', ...CALCULATOR_ERROR_CODES];
  for (const code of codes) {
    assert.equal(typeof EN[`error.${code}`], 'string', `EN ${code}`);
    assert.equal(typeof RU[`error.${code}`], 'string', `RU ${code}`);
    assert.notEqual(EN[`error.${code}`], RU[`error.${code}`], code);
  }
  i18n.setLang('ru');
  try {
    assert.equal(i18n.describeError({ code: 'MAPPING_OPTION_INVALID', message: 'Bad option' }, 'fb'), RU['error.MAPPING_OPTION_INVALID']);
  } finally {
    i18n.setLang('en');
  }
  assert.equal(i18n.describeError({ code: 'MAPPING_SESSION_NOT_FOUND' }, 'fb'), EN['error.MAPPING_SESSION_NOT_FOUND']);
});

// ── pure helpers ──────────────────────────────────────────────────────────────────────────────────────────────

test('questionText uses textRu for a Russian UI and the canonical text otherwise', () => {
  const q = { text: '25 elements from HU. Mapping error or design error?', textRu: '25 элементов из HU. Это ошибка меппинга или ошибка проекта?' };
  assert.equal(questionText(q, 'ru'), q.textRu);
  assert.equal(questionText(q, 'en'), q.text);
  assert.equal(questionText({ text: 'only en', textRu: '' }, 'ru'), 'only en');
  assert.equal(questionText({ text: 'only en' }, 'ru'), 'only en');
  assert.equal(questionText(null, 'ru'), '');
});

test('progressSegments gives five segments in fixed order with percentages of the total', () => {
  const segments = progressSegments({ total: 376, confirmed: 100, auto: 26, suggested: 200, ambiguous: 25, unmapped: 25, openQuestions: 2 });
  assert.deepEqual(segments.map(s => s.state), [...MAPPING_STATES]);
  assert.deepEqual(MAPPING_STATES, ['confirmed', 'auto', 'suggested', 'ambiguous', 'unmapped']);
  assert.deepEqual(segments.map(s => s.count), [100, 26, 200, 25, 25]);
  assert.ok(Math.abs(segments.reduce((a, s) => a + s.percent, 0) - 100) < 1e-9);
  assert.deepEqual(progressSegments({}).map(s => s.percent), [0, 0, 0, 0, 0]);
  assert.deepEqual(progressSegments({ total: 2, confirmed: 3, auto: -1, suggested: 'x' }).map(s => s.count), [3, 0, 0, 0, 0], 'total below the sum is ignored, junk is zero');
  assert.equal(progressSegments({ total: 2, confirmed: 3 })[0].percent, 100);
  assert.deepEqual(summaryTotals({ total: 376, confirmed: 100, auto: 26, openQuestions: 2 }), { total: 376, mapped: 126, openQuestions: 2 });
});

test('parseDescriptorUpload accepts the upload body or a bare array and reports why a file is refused', () => {
  const elements = [{ nativeId: 'a', platform: 'revit' }, { nativeId: 'b' }];
  const ok = parseDescriptorUpload(JSON.stringify({ project: 'v12', platform: 'revit', label: ' act3 ', source: { document: 'x.rvt' }, elements, context: { populationsFromSessionId: 'ms-1' } }));
  assert.deepEqual(ok, { body: { platform: 'revit', label: 'act3', elements, context: { populationsFromSessionId: 'ms-1' } }, count: 2, fileProject: 'v12' });
  assert.deepEqual(parseDescriptorUpload(JSON.stringify(elements)), { body: { platform: 'revit', elements }, count: 2, fileProject: null }, 'platform from the first descriptor');
  assert.deepEqual(parseDescriptorUpload('{nope'), { error: 'json' });
  assert.deepEqual(parseDescriptorUpload('null'), { error: 'elements' });
  assert.deepEqual(parseDescriptorUpload(JSON.stringify({ platform: 'revit', elements: {} })), { error: 'elements' });
  assert.deepEqual(parseDescriptorUpload(JSON.stringify({ platform: 'revit', elements: [] })), { error: 'empty' });
  const many = Array.from({ length: MAX_ELEMENTS + 1 }, (_, i) => ({ nativeId: `n${i}` }));
  assert.deepEqual(parseDescriptorUpload(JSON.stringify({ platform: 'revit', elements: many })), { error: 'too-many' });
  assert.deepEqual(parseDescriptorUpload(JSON.stringify({ platform: 'revit', elements: [{ nativeId: 'a' }, { nativeId: 'a' }] })), { error: 'descriptor' });
  assert.deepEqual(parseDescriptorUpload(JSON.stringify({ platform: 'revit', elements: [{ name: 'x' }] })), { error: 'descriptor' });
  assert.deepEqual(parseDescriptorUpload(JSON.stringify({ platform: 'rhino', elements: [{ nativeId: 'a' }] })), { error: 'platform' });
  assert.deepEqual(parseDescriptorUpload(JSON.stringify({ elements: [{ nativeId: 'a' }] })), { error: 'platform' });
  assert.equal(labelFromFileName('act3-revit.JSON'), 'act3-revit');
  assert.equal(labelFromFileName(undefined), '');
});

test('session list, profile merge and option helpers', () => {
  const full = { sessionId: 'ms-2', label: 'new', summary: { total: 1 }, questions: [1], groups: [2], elements: [3] };
  assert.deepEqual(sessionSummary(full), { sessionId: 'ms-2', label: 'new', summary: { total: 1 } });
  assert.deepEqual(upsertSession([{ sessionId: 'ms-1' }], full).map(s => s.sessionId), ['ms-2', 'ms-1']);
  assert.deepEqual(upsertSession([{ sessionId: 'ms-1' }, { sessionId: 'ms-2', label: 'old' }], full), [{ sessionId: 'ms-1' }, { sessionId: 'ms-2', label: 'new', summary: { total: 1 } }]);
  assert.deepEqual(upsertSession([{ sessionId: 'ms-1' }], null), [{ sessionId: 'ms-1' }]);

  const merged = mergeProfiles([{ profileId: 'P-1', confirmations: 1 }, { profileId: 'P-2' }], [{ profileId: 'P-1', confirmations: 2 }, { profileId: 'P-3' }, { nope: true }]);
  assert.deepEqual(merged, [{ profileId: 'P-3' }, { profileId: 'P-1', confirmations: 2 }, { profileId: 'P-2' }]);

  assert.deepEqual(optionKind('accept-all'), { kind: 'accept-all', arg: '' });
  assert.deepEqual(optionKind('class:ex:GroundFloorUnit'), { kind: 'class', arg: 'ex:GroundFloorUnit' });
  assert.deepEqual(optionKind('design-error:ex:HexagonalUnit'), { kind: 'design-error', arg: 'ex:HexagonalUnit' });
  assert.deepEqual(optionKind('split:geometry.vertexCount'), { kind: 'split', arg: 'geometry.vertexCount' });
  assert.deepEqual(optionKind('none'), { kind: 'none', arg: '' });
  assert.deepEqual(optionKind('class:'), { kind: 'other', arg: 'class:' });
  assert.deepEqual(optionKind(undefined), { kind: 'other', arg: '' });

  assert.equal(classLocalName('ex:GroundFloorUnit'), 'GroundFloorUnit');
  assert.equal(classLocalName('http://example.org/onto#Wall'), 'Wall');
  const labels = classLabels({ groups: [{ candidates: [{ classIri: 'ex:A', label: 'Alpha' }] }, { candidates: [{ classIri: 'ex:A', label: 'Other' }, { classIri: 'ex:B' }] }] });
  assert.deepEqual([...labels], [['ex:A', 'Alpha']]);

  assert.deepEqual(includedGroupIds({ groupIds: ['G-1', 'G-2', 'G-3'] }, ['G-2']), ['G-1', 'G-3']);
  assert.deepEqual(includedGroupIds({ groupIds: ['G-1'] }, undefined), ['G-1']);
  assert.deepEqual(consequenceRows({ consequences: [{ optionId: 'class:ex:GF', rules: [{ ruleId: 'R_GF', effect: 'passes', count: 25 }] }, { optionId: 'none', rules: [] }] }),
    [{ optionId: 'class:ex:GF', ruleId: 'R_GF', effect: 'passes', count: 25 }]);
  assert.deepEqual(appliedByClass({ byClass: { 'ex:B': ['1', '2'], 'ex:A': ['3', '4'], 'ex:C': ['5', '6', '7'] } }), [
    { classIri: 'ex:C', count: 3 }, { classIri: 'ex:A', count: 2 }, { classIri: 'ex:B', count: 2 }
  ]);
  assert.deepEqual(appliedByClass(null), []);
  assert.deepEqual(selectorEntries({ source: 'HU', 'geometry.vertexCount': 5, x: { a: 1 } }), ['source=HU', 'geometry.vertexCount=5', 'x={"a":1}']);
  assert.equal(confidencePercent(0.957), '96%');
  assert.equal(confidencePercent('x'), '—');
});

test('proposal card helpers: title by language, one item view per component, card state by id, answers and undo', () => {
  const q = { title: 'Panels A · 120 elements', titleRu: 'Panels A · 120 элементов' };
  assert.equal(proposalTitle(q, 'ru'), q.titleRu);
  assert.equal(proposalTitle(q, 'en'), q.title);
  assert.equal(proposalTitle({ title: 'only en', titleRu: ' ' }, 'ru'), 'only en');
  assert.equal(proposalTitle({ text: 'an older session has no title' }, 'ru'), '');
  assert.equal(proposalTitle(null, 'en'), '');

  assert.deepEqual(proposalItems({ items: [{ itemId: 'G-1' }, null, 'x', [1], { itemId: 'G-2' }] }), [{ itemId: 'G-1' }, { itemId: 'G-2' }]);
  assert.deepEqual(proposalItems({ text: 'older session' }), []);
  assert.deepEqual([...ITEM_KINDS], ['stream', 'measure', 'parameter']);

  const stream = itemView({ itemId: 'G-1', kind: 'stream', name: 'Panels A', count: 120, state: 'ambiguous',
    proposal: { iri: 'ex:GlassPanel', label: 'GlassPanel' },
    alternatives: [{ iri: 'ex:BottomTriangularPanel', label: 'BottomTriangularPanel' }, { iri: 'ex:GlassPanel', label: 'GlassPanel' }, { iri: 'ex:A' }, { iri: 'ex:B' }, { iri: 'ex:C' }] });
  assert.deepEqual(stream, { key: 'G-1', itemId: 'G-1', kind: 'stream', name: 'Panels A', state: 'ambiguous', proposal: 'GlassPanel',
    alternatives: ['BottomTriangularPanel', 'A', 'B'], count: 120 }, 'the proposal is not repeated as an alternative; at most three');
  assert.equal(itemView({ kind: 'measure', count: '125', proposal: { iri: 'ex:hasAreaM2' } }).count, 125);
  assert.equal(itemView({ kind: 'measure', proposal: { iri: 'ex:hasAreaM2' } }).proposal, 'hasAreaM2', 'label falls back to the local name');
  assert.equal(itemView({ kind: 'parameter', count: 4 }).count, null, 'a slider has no count');
  assert.equal(itemView({ kind: 'stream', count: null }).count, null);
  assert.equal(itemView({ kind: 'stream', count: -2 }).count, null);
  assert.equal(itemView({ kind: 'stream', proposal: null }).proposal, null);
  assert.equal(itemView({ state: 'weird' }).state, 'unmapped');
  assert.equal(itemView({ kind: 'robot' }).kind, '');
  assert.equal(itemView({ kind: 'stream', name: 'X' }, 4).key, 'stream:X:4', 'rows without an itemId still get a stable key');

  assert.equal(cardOpen({}, 'Q-1', true), true, 'default when never toggled');
  assert.equal(cardOpen({}, 'Q-2', false), false);
  assert.equal(cardOpen({ 'Q-1': false }, 'Q-1', true), false, 'an explicit toggle wins over the default');
  let state = toggleCard({}, 'Q-1', true);
  assert.deepEqual(state, { 'Q-1': false });
  state = toggleCard(state, 'Q-2', false);
  assert.deepEqual(state, { 'Q-1': false, 'Q-2': true }, 'each card keeps its own state');
  assert.deepEqual(toggleCard(state, 'Q-1', true), { 'Q-1': true, 'Q-2': true });
  assert.deepEqual(toggleCard(undefined, 'A-1', false), { 'A-1': true });

  assert.deepEqual(sessionAnswers({ answers: [{ answerId: 'A-2' }, { answerId: '' }, null, { questionId: 'Q-1' }, { answerId: 'A-1' }] }).map(a => a.answerId), ['A-2', 'A-1']);
  assert.deepEqual(sessionAnswers({}), []);
  assert.equal(answerUndoable({ answerId: 'A-1', undoable: true }, {}), true);
  assert.equal(answerUndoable({ answerId: 'A-1', undoable: false }, {}), false);
  assert.equal(answerUndoable({ answerId: 'A-1' }, {}), true, 'an absent flag follows the session');
  assert.equal(answerUndoable({ answerId: 'A-1', undoable: true }, { appliedAt: '2026-10-18T09:10:00Z' }), false, 'an applied session is never undoable');
  assert.equal(answerUndoable(null, {}), false);

  assert.equal(answerUndoable({ answerId: 'A-1', undoable: true, committedAt: 'now' }, {}), false);
  assert.equal(awaitingApply({ summary: { openQuestions: 0 } }), false, 'answer completion never authorizes writes');
  const partial = { revision: 'a'.repeat(24), pendingAnswerIds: ['A-1', 'A-2', 'A-3', 'A-4'], summary: { openQuestions: 6 } };
  assert.equal(awaitingApply(partial), true, 'four accepted of ten may be committed');
  assert.deepEqual(pendingAnswerIds(partial), ['A-1', 'A-2', 'A-3', 'A-4']);
  assert.equal(awaitingApply({ ...partial, appliedAt: '2026-10-18T09:10:00Z' }), false);
  assert.equal(awaitingApply({ ...partial, revision: null }), false);
  assert.equal(awaitingApply(null), false);
});

// ── source wiring (the panel is JSX, so these are structural checks) ─────────────────────────────────────────

test('ProjectsScreen mounts one MappingPanel for the active project and keeps its own initial requests', async () => {
  const source = await readFile(new URL('../src/screens/ProjectsScreen.jsx', import.meta.url), 'utf8');
  assert.match(source, /import MappingPanel from "\.\/MappingPanel\.jsx";/);
  assert.equal((source.match(/<MappingPanel\b/g) || []).length, 1, 'rendered in exactly one place');
  assert.match(source, /\{project && <MappingPanel key=\{project\} project=\{project\} active=\{active\} \/>\}/);
  // the screen's own loads are unchanged: projects on activation, members for owners/admins
  assert.match(source, /React\.useEffect\(\(\) => \{\s*if \(active\) load\(\);\s*\}, \[active, load\]\);/);
  assert.match(source, /if \(active\) loadMembers\(\);/);
  assert.doesNotMatch(source, /mappingApi/, 'the screen itself sends no mapping request');
});

test('MappingPanel starts collapsed, loads only when open and active, and uses the mapping client', async () => {
  const source = await readFile(new URL('../src/screens/MappingPanel.jsx', import.meta.url), 'utf8');
  assert.match(source, /export default function MappingPanel\(\{ project, active \}\)/);
  assert.match(source, /const \[open, setOpen\] = React\.useState\(false\);/);
  assert.match(source, /if \(open && active\) load\(selectedRef\.current\);/);
  assert.equal(
    (source.match(/\bload\(/g) || []).length,
    4,
    'load runs from the open/active effect, the Retry/Refresh buttons and the follow-new-sessions timer only'
  );
  // Sessions created by CONNECTOR are followed only while the panel is open on an active screen (2026-10-18).
  assert.match(source, /if \(!\(open && active && status === "ready"\)\) return undefined;/);
  assert.match(source, /return \(\) => clearInterval\(timer\);/);
  for (const fn of ['listSessions', 'listProfiles', 'getSession', 'createSession', 'postDecision', 'applySession', 'undoAnswer']) {
    assert.match(source, new RegExp(`\\b${fn}\\(`), `${fn} wired`);
  }
  assert.match(source, /from "\.\.\/lib\/mappingApi\.js"/);
  assert.match(source, /questionText\(question, lang\)/, 'question text follows the UI language');
  assert.match(source, /aria-expanded=\{open\}/);
  assert.match(source, /aria-live="polite"/);
  assert.doesNotMatch(source, /\bfetch\(|apiFetch|localStorage|\.toLocale\w*\(/);
});

test('MappingPanel defines the five state colours as local custom properties with dark variants', async () => {
  const source = await readFile(new URL('../src/screens/MappingPanel.jsx', import.meta.url), 'utf8');
  const light = { confirmed: '#2E7D32', auto: '#1565C0', suggested: '#F9A825', ambiguous: '#E65100', unmapped: '#9E9E9E' };
  const css = /const MAPPING_CSS = `([\s\S]*?)`;/.exec(source);
  assert.ok(css, 'MAPPING_CSS block');
  const [lightBlock, darkBlock] = css[1].split(':root[data-theme="dark"]');
  assert.ok(darkBlock, 'dark-theme block');
  for (const [state, colour] of Object.entries(light)) {
    assert.match(lightBlock, new RegExp(`--mapping-${state}: ${colour};`), `light ${state}`);
    const dark = new RegExp(`--mapping-${state}: (#[0-9A-F]{6});`).exec(darkBlock);
    assert.ok(dark && dark[1] !== colour, `dark ${state} differs from light`);
  }
  assert.match(source, /<style>\{MAPPING_CSS\}<\/style>/);
  assert.match(source, /var\(--mapping-\$\{state\}\)/);
});

// ── proposal and answer cards (contract §7, plan 1303-10, owner 2026-10-18) ──────────────────────────────────
// The cards are rendered for real: esbuild bundles them with React and react-dom/server (installed dependencies, no
// network), and the static markup is checked. The bundle carries its own i18n store, switched with its setLang.

let partsPromise;
function panelParts() {
  partsPromise ??= build({
    stdin: {
      contents: [
        'export { ProposalCard, AnswerCard, ItemRow, ApplyResult, CalculatorReviewCard, CatalogueEntryRow, BlockedCalculatorRow } from "./src/screens/MappingPanel.jsx";',
        'export { renderToStaticMarkup } from "react-dom/server.browser";',
        'export { createElement } from "react";',
        'export { default as React } from "react";',
        'export { setLang } from "./src/i18n/index.js";'
      ].join('\n'),
      resolveDir: fileURLToPath(new URL('..', import.meta.url)),
      loader: 'jsx'
    },
    bundle: true,
    write: false,
    format: 'esm',
    platform: 'browser',
    jsx: 'automatic',
    loader: { '.js': 'jsx' },
    define: { 'process.env.NODE_ENV': '"production"' },
    logLevel: 'silent'
  }).then(result => import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].text).toString('base64')}`));
  return partsPromise;
}

async function render(name, props, lang = 'en') {
  const parts = await panelParts();
  parts.setLang(lang);
  try {
    return parts.renderToStaticMarkup(parts.createElement(parts[name], props));
  } finally {
    parts.setLang('en');
  }
}

const count = (html, pattern) => (html.match(pattern) || []).length;
// Opening tag attributes of the button whose only content is `text` (option and undo buttons hold plain text).
const buttonTag = (html, text) => [...html.matchAll(/<button([^>]*)>([^<]*)<\/button>/g)].find(m => m[2] === text)?.[1];

const streamItem = { itemId: 'G-1', kind: 'stream', name: 'Panels A', componentId: '24549b0264794f1bb333b7768ab72820', count: 120,
  proposal: { iri: 'ex:GlassPanel', label: 'GlassPanel' }, alternatives: [{ iri: 'ex:BottomTriangularPanel', label: 'BottomTriangularPanel' }], state: 'ambiguous' };
const measureItem = { itemId: 'M-1', kind: 'measure', name: 'Panel area', componentId: null, count: 125,
  proposal: { iri: 'ex:hasAreaM2', label: 'hasAreaM2' }, alternatives: [], state: 'suggested' };
const sliderItem = { itemId: 'S-1', kind: 'parameter', name: 'Module width', componentId: null, count: null, proposal: null, alternatives: [], state: 'unmapped' };
const cardQuestion = {
  questionId: 'Q-1', type: 'mapping-or-design', groupIds: ['G-1'],
  text: 'Full canonical explanation that stays behind Details.', textRu: 'Полное каноническое объяснение под «Подробнее».',
  title: 'Panels A · 120 elements: BottomTriangularPanel or GlassPanel?', titleRu: 'Panels A · 120 элементов: BottomTriangularPanel или GlassPanel?',
  items: [streamItem, measureItem, sliderItem],
  options: [{ optionId: 'class:ex:GlassPanel', label: 'GlassPanel' }, { optionId: 'design-error:ex:BottomTriangularPanel' }, { optionId: 'none' }],
  consequences: [{ optionId: 'class:ex:GlassPanel', rules: [{ ruleId: 'R_GP_WIDTH_MIN_4.5_V', effect: 'violated', count: 3 }] }]
};
const cardProps = (question, extra = {}) => ({
  question, expanded: true, onToggleExpanded() {}, groupsById: new Map(), labelOf: iri => String(iri).split(':').pop(),
  excluded: undefined, busy: false, posting: false, error: null, onToggleGroup() {}, onAnswer() {}, ...extra
});

test('ProposalCard renders one row per proposed component, never a paragraph, and keeps the full text behind Details', async () => {
  const html = await render('ProposalCard', cardProps(cardQuestion));
  assert.match(html, /data-question-id="Q-1"/);
  assert.match(html, /<button type="button" aria-expanded="true" aria-controls="[^"]+"/, 'the header toggles this card');
  assert.match(html, /Panels A · 120 elements: BottomTriangularPanel or GlassPanel\?/);
  assert.match(html, />3 components</, 'item count in the header');
  assert.equal(count(html, /data-mapping-item="/g), 3, 'one row per item');
  assert.equal(count(html, /<li><div data-mapping-item="/g), 3, 'each item is its own list row');
  for (const [key, state] of [['G-1', 'ambiguous'], ['M-1', 'suggested'], ['S-1', 'unmapped']]) {
    const row = new RegExp(`data-mapping-item="${key}"[^>]*>(.*?)</div></li>`).exec(html);
    assert.ok(row, `row ${key}`);
    assert.match(row[1], new RegExp(`border:1px solid var\\(--mapping-${state}\\)`), `${key} state chip colour`);
  }
  assert.match(html, /Panels A<\/span><span[^>]*>Element stream<\/span><span[^>]*>→ <span[^>]*>GlassPanel<\/span><\/span><span[^>]*>120 elements<\/span><span[^>]*>or BottomTriangularPanel<\/span>/);
  assert.match(html, /Panel area<\/span><span[^>]*>Calculation output<\/span><span[^>]*>→ <span[^>]*>hasAreaM2<\/span><\/span><span[^>]*>125 values<\/span>/);
  assert.match(html, /Module width<\/span><span[^>]*>Slider<\/span><span[^>]*>→ <span[^>]*>no proposal<\/span><\/span><\/div>/, 'no count for a slider');
  assert.doesNotMatch(html, /role="checkbox"|<button[^>]*data-mapping-item|data-mapping-item="[^"]*"[^>]*(?:onclick|tabindex)/i, 'item chips are not interactive in the Web UI');
  for (const label of ['GlassPanel', 'BottomTriangularPanel — rule violations are design errors', 'None of these']) {
    const tag = buttonTag(html, label);
    assert.ok(tag !== undefined, `option ${label}`);
    assert.doesNotMatch(tag, /disabled/);
  }
  assert.match(html, /<button type="button" aria-expanded="false"[^>]*><svg[\s\S]*?<\/svg><span>Details<\/span><\/button>/);
  assert.doesNotMatch(html, /Full canonical explanation|R_GP_WIDTH_MIN_4\.5_V/, 'text and consequences stay folded by default');
});

test('ProposalCard collapsed shows only the one-line header; the RU UI uses titleRu and Russian row labels', async () => {
  const collapsed = await render('ProposalCard', cardProps(cardQuestion, { expanded: false }));
  assert.match(collapsed, /<button type="button" aria-expanded="false" style=/);
  assert.match(collapsed, /Mapping or design error/);
  assert.match(collapsed, /Panels A · 120 elements/);
  assert.match(collapsed, />3 components</);
  assert.doesNotMatch(collapsed, /data-mapping-item|None of these|Details/);

  const ru = await render('ProposalCard', cardProps(cardQuestion), 'ru');
  assert.match(ru, /Panels A · 120 элементов: BottomTriangularPanel или GlassPanel\?/);
  assert.doesNotMatch(ru, /Panels A · 120 elements/);
  for (const text of ['>3 компонента<', '>Поток элементов<', '>Расчётный выход<', '>Слайдер<', '>120 эл.<', '>125 знач.<', '>или BottomTriangularPanel<', '>нет предложения<', '>Подробнее<', '>Ни один из вариантов<']) {
    assert.ok(ru.includes(text), text);
  }
});

test('ProposalCard of an older session without items or title keeps the text rendering', async () => {
  const legacy = { questionId: 'Q-2', type: 'assign', groupIds: ['G-9'], text: 'Legacy canonical question text.', textRu: 'Старый текст вопроса.',
    options: [{ optionId: 'class:ex:Alpha', label: 'Alpha' }, { optionId: 'none' }] };
  const groupsById = new Map([['G-9', { groupId: 'G-9', size: 25, status: 'suggested', candidates: [{ classIri: 'ex:Alpha', label: 'Alpha', confidence: 0.9, evidence: [], conflicts: [] }] }]]);
  const html = await render('ProposalCard', cardProps(legacy, { groupsById }));
  assert.match(html, /Legacy canonical question text\./, 'full text shown without a Details toggle');
  assert.doesNotMatch(html, /data-mapping-item|<span>Details<\/span>/);
  assert.match(html, />1 component</, 'header falls back to type + component count');
  assert.ok(buttonTag(html, 'Alpha') !== undefined);
  assert.match(await render('ProposalCard', cardProps(legacy, { groupsById }), 'ru'), /Старый текст вопроса\./);
});

test('ProposalCard batch-assign rows carry the group checkboxes; no checked row disables the options', async () => {
  const batch = { questionId: 'Q-3', type: 'batch-assign', groupIds: ['G-1', 'G-2'], text: 'Accept all?', title: 'Accept 2 streams',
    items: [streamItem, { ...streamItem, itemId: 'G-2', name: 'Panels B', state: 'suggested' }],
    options: [{ optionId: 'accept-all' }, { optionId: 'none' }] };
  const html = await render('ProposalCard', cardProps(batch, { excluded: ['G-2'] }));
  assert.equal(count(html, /role="checkbox" tabindex="0" aria-checked="true"/g), 1);
  assert.equal(count(html, /role="checkbox" tabindex="0" aria-checked="false"/g), 1);
  assert.equal(count(html, /data-mapping-item="/g), 2);
  assert.doesNotMatch(buttonTag(html, 'Accept all proposed classes'), /disabled/);
  const none = await render('ProposalCard', cardProps(batch, { excluded: ['G-1', 'G-2'] }));
  assert.match(buttonTag(none, 'Accept all proposed classes'), /disabled=""/);
  assert.match(none, /Select at least one group\./);
});

const givenAnswer = {
  answerId: 'A-1', questionId: 'Q-7', type: 'batch-assign', optionId: 'accept-all',
  title: 'Panels B · 125 elements: GlassPanel', titleRu: 'Panels B · 125 элементов: GlassPanel',
  items: [{ itemId: 'G-2', kind: 'stream', name: 'Panels B', componentId: null, count: 125, proposal: { iri: 'ex:GlassPanel', label: 'GlassPanel' }, alternatives: [], state: 'confirmed' }],
  decidedAt: '2026-10-18T09:05:00Z', decidedBy: 'owner', undoable: true
};
const answerProps = (extra = {}) => ({
  answer: givenAnswer, expanded: true, onToggleExpanded() {}, labelOf: iri => String(iri).split(':').pop(),
  undoable: true, undoing: false, busy: false, error: null, onUndo() {}, ...extra
});

test('AnswerCard is collapsed by default to a header: green chip, title, chosen option, who and when', async () => {
  const html = await render('AnswerCard', answerProps({ expanded: false }));
  assert.match(html, /data-answer-id="A-1"/);
  assert.match(html, /<button type="button" aria-expanded="false" style=/);
  assert.match(html, /border:1px solid var\(--mapping-confirmed\)/);
  assert.match(html, /Panels B · 125 elements: GlassPanel/);
  assert.match(html, /Accept all proposed classes · owner · /);
  assert.doesNotMatch(html, /Undo decision|data-mapping-item/);
});

test('AnswerCard has its own undo button, disabled with a hint once the session is applied', async () => {
  const open = await render('AnswerCard', answerProps());
  assert.equal(count(open, /data-mapping-item="G-2"/g), 1, 'the decided components as rows');
  const tag = buttonTag(open, 'Undo decision');
  assert.ok(tag !== undefined, 'undo button');
  assert.doesNotMatch(tag, /disabled/);
  assert.doesNotMatch(open, /undo is not available/);

  const applied = await render('AnswerCard', answerProps({ undoable: false }));
  assert.match(buttonTag(applied, 'Undo decision'), /disabled=""/);
  assert.match(applied, /Committed decisions cannot be undone as drafts/);

  assert.ok(buttonTag(await render('AnswerCard', answerProps({ undoing: true })), 'Undoing…') !== undefined, 'running label');
  assert.match(buttonTag(await render('AnswerCard', answerProps({ busy: true })), 'Undo decision'), /disabled=""/, 'no undo while another request runs');
  assert.match(await render('AnswerCard', answerProps({ error: { code: 'MAPPING_SESSION_APPLIED' } })), /This session is already applied/);

  const ru = await render('AnswerCard', answerProps({ undoable: false }), 'ru');
  assert.match(buttonTag(ru, 'Отменить решение'), /disabled=""/);
  assert.match(ru, /Записанные решения нельзя отменить как черновики/);
  assert.match(ru, /Panels B · 125 элементов: GlassPanel/);
  assert.ok(buttonTag(await render('AnswerCard', answerProps({ undoing: true }), 'ru'), 'Отмена…') !== undefined);
});

test('ApplyResult distinguishes server commit from successful or failed CAD delivery', async () => {
  const result = { answerIds: ['A-1', 'A-2', 'A-3', 'A-4'], payload: { applied: 4, byClass: {} }, delivery: { state: 'queued' } };
  const props = { result, labelOf: iri => iri };
  const queued = await render('ApplyResult', props);
  assert.match(queued, /Confirmed on server — waiting for CAD/);
  assert.match(queued, /Accepted decisions: 4/);
  assert.doesNotMatch(queued, /Written to CAD/);
  const written = await render('ApplyResult', { ...props, result: { ...result, delivery: { state: 'written', written: 4, skipped: 0 } } });
  assert.match(written, /Written to CAD/);
  const failed = await render('ApplyResult', { ...props, result: { ...result, delivery: { state: 'failed', written: 0, skipped: 4 } } }, 'ru');
  assert.match(failed, /Не удалось записать в CAD/);
  assert.doesNotMatch(failed, /Записано в CAD/);
});

test('MappingPanel keys card state by questionId / answerId, undoes per answer and offers no start-mapping action', async () => {
  const source = await readFile(new URL('../src/screens/MappingPanel.jsx', import.meta.url), 'utf8');
  const api = await readFile(new URL('../src/lib/mappingApi.js', import.meta.url), 'utf8');
  // first open proposal expanded, the rest collapsed, each card toggled on its own
  assert.match(source, /const expanded = cardOpen\(questionOpen, question\.questionId, index === 0\);/);
  assert.match(source, /setQuestionOpen\(\(prev\) => toggleCard\(prev, question\.questionId, index === 0\)\)/);
  // answers collapsed by default, each with its own expansion and undo state
  assert.match(source, /expanded=\{cardOpen\(answerOpen, entry\.answerId, false\)\}/);
  assert.match(source, /setAnswerOpen\(\(prev\) => toggleCard\(prev, entry\.answerId, false\)\)/);
  assert.match(source, /undoable=\{answerUndoable\(entry, session\)\}/);
  assert.match(source, /undoing=\{undoing === entry\.answerId\}/);
  assert.match(source, /error=\{undoErr\?\.answerId === entry\.answerId \? undoErr\.err : null\}/);
  // the undo reply replaces the session like a decision reply does
  assert.match(source, /const next = await undoAnswer\(project, sessionId, entry\.answerId\);/);
  assert.match(source, /if \(!session \|\| busy \|\| !answerUndoable\(entry, session\)\) return;/);
  assert.ok(count(source, /setSession\(merged\);/g) >= 2, 'decision and undo both replace the session');
  assert.match(source, /const busy = posting !== null \|\| undoing !== null \|\|/);
  assert.match(source, /\{waitingApply \? \(/);
  assert.doesNotMatch(source, /applies the mapping in about 10 s/);
  assert.match(source, /t\("Confirm and write \(\{n\}\)"/);
  assert.match(source, /disabled=\{busy \|\| !waitingApply\}/);
  assert.match(source, /applySession\(project, sessionId, commitRef\.current\)/);
  assert.match(source, /CAD delivery failed/);
  assert.doesNotMatch(source, /setProfiles\(\(items\) => mergeProfiles\(items, res\.profiles\)\)/);
  assert.match(source, /t\("Decisions made"\)/);
  // owner 2026-10-18: the Web UI shows only existing sessions; the descriptor import stays for the Revit act
  for (const text of [source, api]) assert.doesNotMatch(text, /start_mapping|startMapping|start mapping|startSession/i);
  const { RU } = await import('../src/i18n/dict/index.js');
  assert.ok(!Object.keys(RU).some(key => /start mapping|start a mapping/i.test(key)), 'no start-mapping text');
  assert.match(source, /t\("Import descriptors \(JSON\)"\)/);
});

// ── calculator review (plans 1303-16..18, DGOPN-05, D-54..D-60) ───────────────────────────────────────────────

const SHA = 'a'.repeat(64);
const calcBase = '/data-service/scripts/property-calculators';

test('listCalculatorCandidates GETs the encoded project and run with no CSRF marker and no runId when absent', async () => {
  reply = [200, { project, companyAssigned: true, canRetire: false, run: null, candidates: [], blocked: [], catalogue: [] }];
  const res = await listCalculatorCandidates('A b', 'run/1');
  await listCalculatorCandidates('A b');
  await listCalculatorCandidates('A b', '');
  assert.equal(res.companyAssigned, true);
  assert.deepEqual(calls.map(c => c.url), [
    `${calcBase}/candidates?project=A%20b&runId=run%2F1`,
    `${calcBase}/candidates?project=A%20b`,
    `${calcBase}/candidates?project=A%20b`
  ]);
  for (const call of calls) {
    assert.equal(call.init.method, 'GET');
    assert.equal(call.init.headers[CSRF_HEADER], undefined);
    assert.equal(call.init.body, undefined);
  }
});

test('confirmCalculator POSTs exactly the shown sha256 and runId, the unit only when non-empty, with the CSRF marker', async () => {
  reply = [200, { catalogueId: 'cat-1', alreadyConfirmed: false, reconfirmed: false, reactivatedCopies: 0 }];
  const intent = { dataPropertyIri: 'ex:hasWindowArea', sha256: SHA, runId: 'run/1', meaning: '  Window area per box  ', unit: 'm2' };
  const res = await confirmCalculator(project, intent);
  await confirmCalculator(project, { ...intent, unit: '' });
  await confirmCalculator(project, { ...intent, unit: undefined });
  assert.equal(res.catalogueId, 'cat-1');
  assert.equal(calls[0].url, `${calcBase}/confirm`);
  assert.equal(calls[0].init.method, 'POST');
  assert.equal(calls[0].init.headers[CSRF_HEADER], '1');
  assert.deepEqual(body(0), { project, dataPropertyIri: 'ex:hasWindowArea', sha256: SHA, runId: 'run/1', meaning: 'Window area per box', unit: 'm2' });
  assert.deepEqual(body(1), { project, dataPropertyIri: 'ex:hasWindowArea', sha256: SHA, runId: 'run/1', meaning: 'Window area per box' });
  assert.deepEqual(body(2), body(1), 'an absent unit keeps the stored calculator unit');
});

test('confirmCalculator refuses a bad sha256, a missing run, a blank meaning or property without sending a request', async () => {
  const ok = { dataPropertyIri: 'ex:p', sha256: SHA, runId: 'run-1', meaning: 'm' };
  const bad = [
    { ...ok, sha256: 'A'.repeat(64) }, { ...ok, sha256: 'a'.repeat(63) }, { ...ok, sha256: undefined },
    { ...ok, runId: '' }, { ...ok, runId: undefined },
    { ...ok, meaning: '   ' }, { ...ok, meaning: undefined },
    { ...ok, dataPropertyIri: '' }
  ];
  for (const intent of bad) {
    await assert.rejects(() => confirmCalculator(project, intent), err => err.code === 'CALCULATOR_INPUT_INVALID', JSON.stringify(intent));
  }
  await assert.rejects(() => confirmCalculator(project), err => err.code === 'CALCULATOR_INPUT_INVALID');
  assert.equal(calls.length, 0, 'the client sends nothing without the exact sha256 and runId');
});

test('rejectCalculator POSTs a boolean regenerate and refuses a blank reason without a request', async () => {
  reply = [200, { alreadyRejected: false, regenerate: true, rejectedSha256s: [SHA] }];
  await rejectCalculator(project, { dataPropertyIri: 'ex:p', sha256: SHA, reason: ' too coarse ', regenerate: true });
  await rejectCalculator(project, { dataPropertyIri: 'ex:p', sha256: SHA, reason: 'wrong unit' });
  assert.equal(calls[0].url, `${calcBase}/reject`);
  assert.equal(calls[0].init.method, 'POST');
  assert.equal(calls[0].init.headers[CSRF_HEADER], '1');
  assert.deepEqual(body(0), { project, dataPropertyIri: 'ex:p', sha256: SHA, reason: 'too coarse', regenerate: true });
  assert.deepEqual(body(1), { project, dataPropertyIri: 'ex:p', sha256: SHA, reason: 'wrong unit', regenerate: false });
  const before = calls.length;
  for (const intent of [{ dataPropertyIri: 'ex:p', sha256: SHA, reason: '  ' }, { dataPropertyIri: 'ex:p', sha256: SHA }, { dataPropertyIri: 'ex:p', sha256: 'x', reason: 'r' }]) {
    await assert.rejects(() => rejectCalculator(project, intent), err => err.code === 'CALCULATOR_INPUT_INVALID');
  }
  assert.equal(calls.length, before);
});

test('retireCalculator POSTs the catalogue id and a reason and refuses a blank one without a request', async () => {
  reply = [200, { catalogueId: 'cat/1', retiredCopies: 2, alreadyRetired: false }];
  await retireCalculator(project, { catalogueId: 'cat/1', reason: ' superseded ' });
  assert.equal(calls[0].url, `${calcBase}/retire`);
  assert.equal(calls[0].init.method, 'POST');
  assert.equal(calls[0].init.headers[CSRF_HEADER], '1');
  assert.deepEqual(body(0), { project, catalogueId: 'cat/1', reason: 'superseded' });
  for (const intent of [{ catalogueId: 'cat/1', reason: '' }, { catalogueId: '', reason: 'r' }, { reason: 'r' }, undefined]) {
    await assert.rejects(() => retireCalculator(project, intent), err => err.code === 'CALCULATOR_INPUT_INVALID');
  }
  assert.equal(calls.length, 1);
});

test('calculatorConfirmable needs an effective run, a run newer than the calculator and at least one value', () => {
  const run = { runId: 'run-1', createdAt: '2026-10-22T09:00:00Z' };
  const good = { runNewerThanCalculator: true, stats: { n: 3 } };
  assert.equal(calculatorConfirmable(good, run), true);
  assert.equal(calculatorConfirmable(good, null), false, 'no published run');
  assert.equal(calculatorConfirmable({ ...good, run }, null), true, "the candidate's own run is enough when the shared run is null");
  assert.equal(calculatorConfirmable({ ...good, run: { runId: 'own' } }, run), true);
  assert.equal(calculatorConfirmable({ ...good, runNewerThanCalculator: false }, run), false, 'run older than the calculator');
  assert.equal(calculatorConfirmable({ ...good, runNewerThanCalculator: undefined }, run), false);
  assert.equal(calculatorConfirmable({ ...good, stats: { n: 0 } }, run), false, 'no values');
  assert.equal(calculatorConfirmable({ ...good, stats: undefined }, run), false);
  assert.equal(calculatorConfirmable({ ...good, run: { createdAt: 'x' } }, null), false, 'a run without an id cannot be confirmed against');
  assert.equal(calculatorConfirmable(null, run), false);
});

test('calculatorConfirmPayload carries the sha256 unchanged and the runId of the effective run (D-58, D-59)', () => {
  const candidate = { dataPropertyIri: 'ex:p', sha256: SHA, unit: 'm2', run: { runId: 'own-run' } };
  assert.deepEqual(calculatorConfirmPayload(candidate, { runId: 'shared-run' }, 'Window area', 'm2'),
    { dataPropertyIri: 'ex:p', sha256: SHA, runId: 'own-run', meaning: 'Window area', unit: 'm2' }, 'a retired copy confirms against its own run');
  assert.equal(calculatorConfirmPayload({ ...candidate, run: null }, { runId: 'shared-run' }, 'm', 'm2').runId, 'shared-run');
  assert.equal(calculatorConfirmPayload({ ...candidate, run: null }, null, 'm', 'm2').runId, '', 'no run, no id: confirmCalculator then refuses');
});

test('calculator error codes have EN and RU texts that differ and describeError maps them (CATALOGUE_PROPERTY_TAKEN in both languages)', async () => {
  const { EN, RU } = await import('../src/i18n/dict/index.js');
  const i18n = await import('../src/i18n/index.js');
  assert.equal(CALCULATOR_ERROR_CODES.length, 12);
  for (const code of CALCULATOR_ERROR_CODES) {
    assert.equal(typeof EN[`error.${code}`], 'string', `EN ${code}`);
    assert.equal(typeof RU[`error.${code}`], 'string', `RU ${code}`);
    assert.notEqual(EN[`error.${code}`], RU[`error.${code}`], code);
  }
  assert.equal(i18n.describeError({ code: 'CATALOGUE_PROPERTY_TAKEN', message: 'taken' }, 'fb'), EN['error.CATALOGUE_PROPERTY_TAKEN']);
  i18n.setLang('ru');
  try {
    assert.equal(i18n.describeError({ code: 'CATALOGUE_PROPERTY_TAKEN', message: 'taken' }, 'fb'), RU['error.CATALOGUE_PROPERTY_TAKEN']);
    assert.equal(i18n.describeError({ code: 'CATALOGUE_RECONFIRM_OWNER_REQUIRED' }, 'fb'), 'Подтвердить отозванный калькулятор снова может только владелец проекта. Обратитесь к владельцу.');
  } finally {
    i18n.setLang('en');
  }
  assert.equal(EN['error.CATALOGUE_RECONFIRM_OWNER_REQUIRED'], 'Only an owner of this project can confirm a retired calculator again. Ask an owner.');
});

// Static rendering of the review cards. The cards keep their input text in React state, which a static render never
// changes, so the seeded renderer answers the card's useState calls from `seeds` by call index. Card hooks, in
// order: meaning (0), unit (1), reason (2), regenerate (3). CatalogueEntryRow: reason (0).
async function renderSeeded(name, props, seeds = {}, lang = 'en') {
  const parts = await panelParts();
  const original = parts.React.useState;
  let index = 0;
  parts.React.useState = (initial) => {
    const value = typeof initial === 'function' ? initial() : initial;
    const at = index++;
    return [at in seeds ? seeds[at] : value, () => {}];
  };
  parts.setLang(lang);
  try {
    return parts.renderToStaticMarkup(parts.createElement(parts[name], props));
  } finally {
    parts.React.useState = original;
    parts.setLang('en');
  }
}

const calcRun = { runId: 'run/1', createdAt: '2026-10-22T09:00:00Z' };
const calcCandidate = (extra = {}) => ({
  dataPropertyIri: 'ex:hasWindowArea', propertyName: 'WindowArea', function: 'window_area',
  source: 'def calc(box):\n    return box.area', sha256: SHA, unit: 'm2',
  explanation: 'LLM explanation of the window area', provider: 'anthropic', model: 'claude-test',
  createdAt: '2026-10-22T08:00:00Z', createdBy: 'editor', readCategories: ['Windows', 'Walls'], ruleIds: ['R_WINDOW_MIN_V'],
  samples: Array.from({ length: 12 }, (_, i) => ({ objectRef: `rvt:${i}`, label: `Box ${i}`, value: i * 1.5 })),
  stats: { n: 12, numeric: 12, min: 0, max: 16.5 },
  verdicts: [{ ruleId: 'R_WINDOW_MIN_V', counts: { violated: 2, satisfied: 10 } }],
  run: calcRun, runNewerThanCalculator: true, retired: false, catalogueId: null, ...extra
});
const calcProps = (candidate, extra = {}) => ({
  candidate, run: calcRun, companyAssigned: true, canReconfirm: false, busy: false, error: null, onConfirm() {}, onReject() {}, ...extra
});
const CONFIRM = 'Confirm for the company catalogue';
const CONFIRM_AGAIN = 'Confirm again for the company catalogue';
const OWNER_HINT = 'Only an owner of the project can confirm a retired calculator again.';

test('CalculatorReviewCard shows source, up to ten sample rows, the stats line and one verdict row per rule', async () => {
  const html = await render('CalculatorReviewCard', calcProps(calcCandidate()));
  assert.match(html, /WindowArea/);
  for (const text of ['anthropic', 'claude-test', 'm2', 'Windows', 'Walls', 'LLM explanation of the window area']) assert.ok(html.includes(text), text);
  assert.match(html, /<pre[^>]*>def calc\(box\):\n    return box\.area<\/pre>/, 'the source sits in a code block');
  assert.equal(count(html, /data-calculator-sample="/g), 10, 'twelve samples, ten rows');
  assert.ok(html.includes('rvt:0 · Box 0 = 0'));
  assert.ok(html.includes('rvt:9 · Box 9 = 13.5'));
  assert.ok(!html.includes('rvt:10 · Box 10'));
  assert.ok(html.includes('Values on 12 boxes · min 0 · max 16.5'));
  assert.ok(html.includes('Rule verdicts'));
  assert.ok(html.includes('R_WINDOW_MIN_V · violated 2, satisfied 10'));
  assert.doesNotMatch(html, />Retired</, 'a pending candidate is not marked retired');
});

test('calculator cards never render the source, explanation, labels or reason as HTML', async () => {
  const hostile = calcCandidate({
    source: '<script>alert(1)</script>', explanation: '<img src=x onerror=alert(2)>',
    samples: [{ objectRef: '<b>ref</b>', label: '<i>x</i>', value: '<u>1</u>' }],
    verdicts: [{ ruleId: '<svg onload=alert(3)>', counts: { '<b>violated</b>': 1 } }]
  });
  const html = await render('CalculatorReviewCard', calcProps(hostile));
  assert.ok(html.includes('&lt;script&gt;alert(1)&lt;/script&gt;'));
  for (const raw of ['<script', '<img', '<b>ref', '<i>x', '<u>1', '<svg onload']) assert.ok(!html.includes(raw), raw);
  const blocked = await render('BlockedCalculatorRow', { item: { dataPropertyIri: 'ex:p', propertyName: '<b>P</b>', status: 'rejected', sha256: SHA, reason: '"><script>x</script>', by: 'e', regenerate: false }, busy: false, error: null, onRegenerate() {} });
  assert.ok(!blocked.includes('<script') && !blocked.includes('<b>P'));
});

test('CalculatorReviewCard Confirm needs a confirmable run, a company and a typed meaning (D-56, D-58)', async () => {
  const empty = await render('CalculatorReviewCard', calcProps(calcCandidate()));
  assert.match(buttonTag(empty, CONFIRM), /disabled=""/, 'empty meaning');
  assert.doesNotMatch(empty, /value="LLM explanation/, 'the LLM explanation is shown for reference and never pre-filled');
  const typed = { 0: 'Window area per box' };
  assert.doesNotMatch(buttonTag(await renderSeeded('CalculatorReviewCard', calcProps(calcCandidate()), typed), CONFIRM), /disabled/, 'meaning typed');
  assert.match(buttonTag(await renderSeeded('CalculatorReviewCard', calcProps(calcCandidate()), { 0: '   ' }), CONFIRM), /disabled=""/, 'blank meaning');
  const cases = [
    ['The run is older than this calculator: run the check again.', calcCandidate({ runNewerThanCalculator: false })],
    ['The run holds no values for this property.', calcCandidate({ stats: { n: 0, numeric: 0, min: null, max: null }, samples: [] })],
    ['No published run yet: run the check with publishing first.', calcCandidate({ run: null }), { run: null }]
  ];
  for (const [hint, candidate, extra] of cases) {
    const html = await renderSeeded('CalculatorReviewCard', calcProps(candidate, extra), typed);
    assert.match(buttonTag(html, CONFIRM), /disabled=""/, hint);
    assert.ok(html.includes(hint), hint);
  }
  const noCompany = await renderSeeded('CalculatorReviewCard', calcProps(calcCandidate(), { companyAssigned: false }), typed);
  assert.match(buttonTag(noCompany, CONFIRM), /disabled=""/, 'no company, no confirm');
  const ownRun = await renderSeeded('CalculatorReviewCard', calcProps(calcCandidate(), { run: null }), typed);
  assert.doesNotMatch(buttonTag(ownRun, CONFIRM), /disabled/, "the candidate's own run is enough");
  assert.match(buttonTag(await renderSeeded('CalculatorReviewCard', calcProps(calcCandidate(), { busy: true }), typed), CONFIRM), /disabled=""/, 'no second request while one runs');
});

test('CalculatorReviewCard pending candidate offers Reject with a reason and the regenerate option', async () => {
  const html = await render('CalculatorReviewCard', calcProps(calcCandidate()));
  assert.match(buttonTag(html, 'Reject'), /disabled=""/, 'blank reason');
  assert.ok(html.includes('Ask DG for a new calculator'));
  assert.ok(html.includes('>Reason<'));
  assert.doesNotMatch(buttonTag(await renderSeeded('CalculatorReviewCard', calcProps(calcCandidate()), { 2: 'values too coarse' }), 'Reject'), /disabled/);
  const failed = await render('CalculatorReviewCard', calcProps(calcCandidate(), { error: { code: 'CALCULATOR_CHANGED' } }));
  assert.ok(failed.includes('The calculator changed since it was shown'));
});

test('CalculatorReviewCard retired calculator with its own run and an owner: Confirm again (D-59)', async () => {
  const retired = calcCandidate({ retired: true, catalogueId: 'cat-1', run: { runId: 'source-run', createdAt: '2026-10-21T09:00:00Z' } });
  const html = await renderSeeded('CalculatorReviewCard', calcProps(retired, { run: null, canReconfirm: true }), { 0: 'Window area per box' });
  assert.match(html, />Retired</);
  assert.ok(html.includes('def calc(box):'), 'source shown as for a pending candidate');
  assert.ok(html.includes('Values on 12 boxes'));
  const tag = buttonTag(html, CONFIRM_AGAIN);
  assert.ok(tag !== undefined, 'Confirm again button');
  assert.doesNotMatch(tag, /disabled/);
  assert.equal(buttonTag(html, CONFIRM), undefined, 'the first-confirm label is not used for a retired calculator');
  assert.equal(count(html, /<input/g), 2, 'meaning and unit inputs');
  const ru = await render('CalculatorReviewCard', calcProps(retired, { run: null, canReconfirm: true }), 'ru');
  assert.match(ru, />Отозван</);
  assert.ok(buttonTag(ru, 'Подтвердить снова в каталог компании') !== undefined);
});

test('retired calculator: Confirm again only for an owner (D-60)', async () => {
  const retired = calcCandidate({ retired: true, catalogueId: 'cat-1' });
  const nonOwner = await render('CalculatorReviewCard', calcProps(retired, { canReconfirm: false }));
  assert.ok(!nonOwner.includes(CONFIRM_AGAIN), 'no Confirm again for a non-owner');
  assert.equal(buttonTag(nonOwner, CONFIRM), undefined);
  assert.ok(nonOwner.includes(OWNER_HINT), 'owner-only hint');
  assert.equal(count(nonOwner, /<input/g), 0, 'no meaning or unit input without the right to confirm');
  assert.match(nonOwner, />Retired</);
  const owner = await render('CalculatorReviewCard', calcProps(retired, { canReconfirm: true }));
  assert.ok(owner.includes(CONFIRM_AGAIN));
  assert.ok(!owner.includes(OWNER_HINT));
  const ru = await render('CalculatorReviewCard', calcProps(retired, { canReconfirm: false }), 'ru');
  assert.ok(ru.includes('Подтвердить отозванный калькулятор снова может только владелец проекта.'));
  assert.ok(!ru.includes('Подтвердить снова в каталог компании'));
});

test('retired calculator renders no Reject or regenerate action (D-60)', async () => {
  const retired = calcCandidate({ retired: true, catalogueId: 'cat-1' });
  for (const canReconfirm of [true, false]) {
    for (const [lang, reject, regenerate, reason] of [['en', 'Reject', 'Ask DG for a new calculator', '>Reason<'], ['ru', 'Отклонить', 'Попросить DG написать новый калькулятор', '>Обоснование<']]) {
      const html = await render('CalculatorReviewCard', calcProps(retired, { canReconfirm }), lang);
      assert.equal(buttonTag(html, reject), undefined, `${lang} Reject, canReconfirm ${canReconfirm}`);
      assert.ok(!html.includes(regenerate), `${lang} regenerate, canReconfirm ${canReconfirm}`);
      assert.ok(!html.includes(reason), `${lang} reason input, canReconfirm ${canReconfirm}`);
    }
  }
});

test('CatalogueEntryRow shows Retire only with canRetire and the owner-only fields only when present', async () => {
  const entry = { catalogueId: 'cat-1', propertyKey: 'windowarea', propertyName: 'WindowArea', dataPropertyIri: 'ex:hasWindowArea', sha256: SHA, unit: 'm2',
    meaning: 'Window area per box', readCategories: ['Windows'], contractVersion: 3, provider: 'anthropic', model: 'claude-test', confirmedAt: '2026-10-22T09:30:00Z' };
  const base = { entry, canRetire: false, busy: false, error: null, onRetire() {} };
  const viewer = await render('CatalogueEntryRow', base);
  for (const text of ['WindowArea', 'Window area per box', 'm2', 'Windows']) assert.ok(viewer.includes(text), text);
  assert.match(viewer, /Confirmed /);
  assert.equal(buttonTag(viewer, 'Retire'), undefined, 'no Retire without canRetire');
  assert.doesNotMatch(viewer, /str-openings-01|owner-1/);
  const owner = await render('CatalogueEntryRow', { ...base, canRetire: true, entry: { ...entry, sourceProject: 'str-openings-01', confirmedBy: 'owner-1' } });
  assert.match(buttonTag(owner, 'Retire'), /disabled=""/, 'Retire needs a typed reason');
  assert.ok(owner.includes('str-openings-01') && owner.includes('owner-1'));
  assert.doesNotMatch(buttonTag(await renderSeeded('CatalogueEntryRow', { ...base, canRetire: true }, { 0: 'superseded' }), 'Retire'), /disabled/);
  assert.ok(buttonTag(await render('CatalogueEntryRow', { ...base, canRetire: true }, 'ru'), 'Отозвать') !== undefined);
  assert.ok((await render('CatalogueEntryRow', { ...base, error: { code: 'CATALOGUE_ENTRY_NOT_FOUND' } })).includes('This catalogue entry was not found'));
});

test('BlockedCalculatorRow shows the status, the pre-filled reason and a regenerate action', async () => {
  const item = { dataPropertyIri: 'ex:hasWindowArea', propertyName: 'WindowArea', status: 'rejected', sha256: SHA, reason: 'values too coarse', by: 'editor', regenerate: false };
  const props = { item, busy: false, error: null, onRegenerate() {} };
  const html = await render('BlockedCalculatorRow', props);
  assert.ok(html.includes('WindowArea'));
  assert.match(html, />Rejected</);
  assert.ok(html.includes('value="values too coarse"'), 'reason input pre-filled from the rejected row');
  assert.doesNotMatch(buttonTag(html, 'Ask DG for a new calculator'), /disabled/);
  assert.match(buttonTag(await render('BlockedCalculatorRow', { ...props, item: { ...item, reason: '' } }), 'Ask DG for a new calculator'), /disabled=""/);
  const ru = await render('BlockedCalculatorRow', props, 'ru');
  assert.match(ru, />Отклонён</);
  assert.ok(buttonTag(ru, 'Попросить DG написать новый калькулятор') !== undefined);
});

test('PropertyCheckCard loads calculators only from the review button and after a decision (D-29, D-57)', async () => {
  const source = await readFile(new URL('../src/screens/MappingPanel.jsx', import.meta.url), 'utf8');
  assert.equal(count(source, /\blistCalculatorCandidates\(/g), 1, 'one call site');
  assert.match(source, /const loadCandidates = async \(\) => \{[\s\S]*?await listCalculatorCandidates\(project, check\?\.summary\?\.validationRunIds\?\.\[0\]\)/);
  assert.equal(count(source, /\bloadCandidates\(/g), 4, 'the review button and the three post-action refreshes');
  assert.match(source, /onClick=\{\(\) => loadCandidates\(\)\}/);
  assert.equal(count(source, /\bload\(/g), 4, 'the mapping-session load count is unchanged');
  const card = source.slice(source.indexOf('function PropertyCheckCard'), source.indexOf('export default function MappingPanel'));
  assert.doesNotMatch(card, /useEffect|useLayoutEffect/, 'nothing runs on mount');
  assert.match(source, /canReconfirm=\{review\.canRetire === true\}/, 'D-60: confirm-again rights are the server owner check');
  assert.match(source, /canRetire=\{review\.canRetire === true\}/);
  for (const fn of ['confirmCalculator', 'rejectCalculator', 'retireCalculator']) assert.match(source, new RegExp(`\\b${fn}\\(`), `${fn} wired`);
  assert.doesNotMatch(source, /dangerouslySetInnerHTML/);
  assert.doesNotMatch(source, /\bfetch\(|apiFetch/);
  assert.match(source, /t\("Review generated calculators"\)/);
});
