import test, { beforeEach, afterEach } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { CSRF_HEADER } from '../src/lib/apiClient.js';
import { fetchRuleConflicts, planConflictDecision } from '../src/lib/graphApi.js';

// Plan 1303-21 (D-65): the conflict check runs on the written rule's atoms after ingest.
// Only fetch is stubbed; no request leaves the process.
const saved = Object.fromEntries(['fetch', 'window'].map(k => [k, Object.getOwnPropertyDescriptor(globalThis, k)]));
let calls, reply;
beforeEach(() => {
  calls = [];
  reply = [200, { ruleId: 'R_NEW', conflict: false, matches: [] }];
  globalThis.window = { GRAPH_CONFIG: { dataServiceUrl: '/data-service' }, dispatchEvent() {} };
  globalThis.fetch = async (url, init) => {
    calls.push({ url, init });
    return new Response(JSON.stringify(reply[1]), { status: reply[0] });
  };
});
afterEach(() => {
  for (const [key, descriptor] of Object.entries(saved)) {
    if (descriptor) Object.defineProperty(globalThis, key, descriptor);
    else delete globalThis[key];
  }
});

test('fetchRuleConflicts GETs the encoded project and rule id with no body and no CSRF marker', async () => {
  reply = [200, { ruleId: 'R_A/B', conflict: true, matches: [{ ruleId: 'R_OLD', sharedClasses: ['Column'] }] }];
  const res = await fetchRuleConflicts('A/B ?#', 'R_A/B');
  assert.equal(calls.length, 1);
  assert.equal(calls[0].url, `/data-service/rules/${encodeURIComponent('A/B ?#')}/${encodeURIComponent('R_A/B')}/conflicts`);
  assert.equal(calls[0].init.method, 'GET');
  assert.equal(calls[0].init.body, undefined);
  assert.equal(calls[0].init.headers[CSRF_HEADER], undefined);
  assert.equal(calls[0].init.credentials, 'include');
  assert.deepEqual(res.matches[0].sharedClasses, ['Column']);
});

test('fetchRuleConflicts surfaces a missing rule as an error carrying the server code', async () => {
  reply = [404, { detail: { code: 'RULE_NOT_FOUND', message: 'Rule not found.' } }];
  await assert.rejects(() => fetchRuleConflicts('P', 'R_X'), (err) => err.code === 'RULE_NOT_FOUND');
});

const matches = [{ ruleId: 'R_OLD_1' }, { ruleId: 'R_OLD_2' }];

test('replace and update supersede the first match with the new rule', () => {
  for (const decision of ['replace', 'update']) {
    assert.deepEqual(planConflictDecision(decision, matches, 'R_NEW'), {
      action: 'supersede',
      oldRuleId: 'R_OLD_1',
      newRuleId: 'R_NEW'
    });
  }
});

test('keep both records the accepted overlap against every match', () => {
  assert.deepEqual(planConflictDecision('keep', matches, 'R_NEW'), {
    action: 'accept-overlap',
    ruleId: 'R_NEW',
    conflictsWith: ['R_OLD_1', 'R_OLD_2']
  });
});

test('cancel only opens the delete dialog for the new rule; it never deletes by itself', () => {
  assert.deepEqual(planConflictDecision('cancel', matches, 'R_NEW'), { action: 'delete-dialog', ruleId: 'R_NEW' });
});

test('an unknown, missing or unaddressable decision does nothing (nothing is deleted unconfirmed)', () => {
  assert.deepEqual(planConflictDecision(undefined, matches, 'R_NEW'), { action: 'none' });
  assert.deepEqual(planConflictDecision('', matches, 'R_NEW'), { action: 'none' });
  assert.deepEqual(planConflictDecision('delete', matches, 'R_NEW'), { action: 'none' });
  assert.deepEqual(planConflictDecision('replace', [], 'R_NEW'), { action: 'none' });
  assert.deepEqual(planConflictDecision('replace', matches, ''), { action: 'none' });
  assert.deepEqual(planConflictDecision('cancel', matches, undefined), { action: 'none' });
});

const SCREEN = fileURLToPath(new URL('../src/screens/GraphScreen.jsx', import.meta.url));

test('the ingest path writes first, checks the written rule, and no longer calls the text pre-check', async () => {
  const source = await readFile(SCREEN, 'utf8');
  const start = source.indexOf('const runIngestWithConflictCheck');
  const end = source.indexOf('// Split a persisted turn');
  assert.ok(start > 0 && end > start, 'ingest flow located');
  const flow = source.slice(start, end);
  assert.doesNotMatch(flow, /checkRuleConflict\(/, 'pre-ingest text check removed from the ingest path');
  assert.match(flow, /fetchRuleConflicts\(/);
  assert.ok(flow.indexOf('runTurn(0') < flow.indexOf('fetchRuleConflicts('), 'the turn runs before the conflict read');
  assert.match(flow, /planConflictDecision\(/);
  // The only deletion route from Cancel is the confirmed delete dialog.
  assert.match(flow, /openDeleteDialog\(/);
  assert.doesNotMatch(flow, /\bdeleteRule\(|\bbulkDeleteRules\(/, 'no unconfirmed delete in the ingest flow');
});
