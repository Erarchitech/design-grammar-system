import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { CSRF_HEADER } from '../src/lib/apiClient.js';
import {
  MAPPING_STATES,
  MAX_ELEMENTS,
  appliedByClass,
  applySession,
  classLabels,
  classLocalName,
  confidencePercent,
  consequenceRows,
  createProfile,
  createSession,
  getSession,
  includedGroupIds,
  labelFromFileName,
  listProfiles,
  listSessions,
  mergeProfiles,
  optionKind,
  parseDescriptorUpload,
  postDecision,
  progressSegments,
  questionText,
  selectorEntries,
  sessionSummary,
  summaryTotals,
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

test('applySession POSTs the project to the session apply route', async () => {
  reply = [200, { applied: 3, byClass: {} }];
  const res = await applySession(project, sid);
  assert.equal(calls[0].url, `${sessionPath}/apply`);
  assert.equal(calls[0].init.method, 'POST');
  assert.equal(calls[0].init.headers[CSRF_HEADER], '1');
  assert.deepEqual(body(), { project });
  assert.equal(res.applied, 3);
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

test('the five MAPPING_* codes have EN and RU texts and describeError maps them', async () => {
  const { EN, RU } = await import('../src/i18n/dict/index.js');
  const i18n = await import('../src/i18n/index.js');
  const codes = ['MAPPING_SESSION_NOT_FOUND', 'MAPPING_QUESTION_NOT_FOUND', 'MAPPING_OPTION_INVALID', 'MAPPING_INPUT_INVALID', 'MAPPING_TOO_MANY_ELEMENTS'];
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
  for (const fn of ['listSessions', 'listProfiles', 'getSession', 'createSession', 'postDecision', 'applySession']) {
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
