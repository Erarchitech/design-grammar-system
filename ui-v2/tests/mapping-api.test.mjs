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
  cardOpen,
  classLabels,
  classLocalName,
  confidencePercent,
  consequenceRows,
  createProfile,
  createSession,
  getSession,
  includedGroupIds,
  itemView,
  labelFromFileName,
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
  const codes = ['MAPPING_SESSION_NOT_FOUND', 'MAPPING_QUESTION_NOT_FOUND', 'MAPPING_OPTION_INVALID', 'MAPPING_INPUT_INVALID', 'MAPPING_TOO_MANY_ELEMENTS', 'MAPPING_COMMIT_REQUIRED', 'MAPPING_COMMIT_CONFLICT', 'MAPPING_ANSWER_COMMITTED'];
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
        'export { ProposalCard, AnswerCard, ItemRow, ApplyResult } from "./src/screens/MappingPanel.jsx";',
        'export { renderToStaticMarkup } from "react-dom/server.browser";',
        'export { createElement } from "react";',
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
