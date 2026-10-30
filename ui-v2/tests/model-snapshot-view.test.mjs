import test from 'node:test';
import assert from 'node:assert/strict';
import {
  CLASS_PALETTE, NO_CLASS, STATE_COLOURS, classColours, elementColour, legendRows, viewGroups
} from '../src/lib/classPalette.js';
import { groupRunsByState, NO_STATE } from '../src/lib/runGroups.js';

// Phase 1303-26 (D-82): the mapping view of a model snapshot colours every class with its own colour, or the five
// mapping states with the shared D-50 palette; legend rows hide and show their elements.

const el = (id, classIris, state = 'confirmed') => ({
  nativeId: id, classIris, classLabels: classIris.map((i) => i.split(':')[1]), state
});
const ELEMENTS = [
  el('w1', ['ex:Wall']), el('w2', ['ex:Wall'], 'auto'), el('b1', ['ex:OpeningBox', 'ex:Penetration'], 'suggested'),
  el('d1', [], 'unmapped')
];

test('every class of a view gets its own colour, the same one on every load', () => {
  const iris = ['ex:Wall', 'ex:OpeningBox', 'ex:Penetration', 'ex:Beam', 'ex:Column'];
  const a = classColours(iris);
  const b = classColours([...iris].reverse());
  assert.equal(new Set(a.values()).size, iris.length);
  for (const iri of iris) assert.equal(a.get(iri), b.get(iri));
  assert.equal(classColours(['ex:Wall']).get('ex:Wall'), a.get('ex:Wall'));
});

test('more classes than palette colours still stay distinct', () => {
  const iris = Array.from({ length: CLASS_PALETTE.length + 5 }, (_, i) => `ex:C${i}`);
  assert.equal(new Set(classColours(iris).values()).size, iris.length);
});

test('the class palette avoids the mapping-state colours and the fail red', () => {
  const taken = new Set([...Object.values(STATE_COLOURS), '#E7000B'].map((c) => c.toUpperCase()));
  for (const c of CLASS_PALETTE) assert.ok(!taken.has(c.toUpperCase()), c);
});

test('the class legend counts a multi-class element under each class and lists elements without a class', () => {
  const colours = classColours(['ex:Wall', 'ex:OpeningBox', 'ex:Penetration']);
  const rows = legendRows(ELEMENTS, 'classes', colours, new Set());
  assert.deepEqual(rows.map((r) => [r.key, r.count]), [
    ['ex:Wall', 2], ['ex:OpeningBox', 1], ['ex:Penetration', 1], [NO_CLASS, 1]
  ]);
  assert.equal(rows[0].label, 'Wall');
  assert.equal(rows[3].colour, STATE_COLOURS.unmapped);
  assert.equal(elementColour(ELEMENTS[2], 'classes', colours), colours.get('ex:OpeningBox'));  // first class, sorted
});

test('the status legend lists the five mapping states with the D-50 colours', () => {
  const rows = legendRows(ELEMENTS, 'status', new Map(), new Set(['auto']));
  assert.deepEqual(rows.map((r) => [r.key, r.count, r.colour, r.hidden]), [
    ['confirmed', 1, STATE_COLOURS.confirmed, false], ['auto', 1, STATE_COLOURS.auto, true],
    ['suggested', 1, STATE_COLOURS.suggested, false], ['ambiguous', 0, STATE_COLOURS.ambiguous, false],
    ['unmapped', 1, STATE_COLOURS.unmapped, false]
  ]);
});

test('hidden legend rows hide their elements; a multi-class element hides when all its classes are hidden', () => {
  const colours = classColours(['ex:Wall', 'ex:OpeningBox', 'ex:Penetration']);
  let out = viewGroups(ELEMENTS, 'classes', colours, new Set(['ex:Wall', 'ex:OpeningBox']));
  assert.deepEqual(out.hiddenNativeIds.sort(), ['w1', 'w2']);
  out = viewGroups(ELEMENTS, 'classes', colours, new Set(['ex:OpeningBox', 'ex:Penetration', NO_CLASS]));
  assert.deepEqual(out.hiddenNativeIds.sort(), ['b1', 'd1']);
  const wall = out.colorGroups.find((g) => g.color === colours.get('ex:Wall'));
  assert.deepEqual(wall.nativeIds, ['w1', 'w2']);
  out = viewGroups(ELEMENTS, 'status', colours, new Set(['unmapped']));
  assert.deepEqual(out.hiddenNativeIds, ['d1']);
  assert.equal(out.colorGroups.length, 3);
});

test('a snapshot is a design state group even without runs, newest snapshot first', () => {
  const snapshots = [
    { stateId: 'OS_new', kind: 'snapshot', capturedAtUtc: '2026-10-30T12:00:00Z' },
    { stateId: 'OS_old', kind: 'snapshot', capturedAtUtc: '2026-10-29T12:00:00Z' }
  ];
  const runs = [
    { runId: 'r1', state: { stateId: 'OS_old', kind: 'snapshot' } },
    { runId: 'r2', state: { stateId: 'DS_a' } },
    { runId: 'r3', state: null }
  ];
  const groups = groupRunsByState(runs, snapshots);
  assert.deepEqual(groups.map((g) => [g.key, g.runs.length, Boolean(g.snapshot)]), [
    ['OS_new', 0, true], ['OS_old', 1, true], ['DS_a', 1, false], [NO_STATE, 1, false]
  ]);
  assert.deepEqual(groupRunsByState(runs).map((g) => g.key), ['DS_a', 'OS_old', NO_STATE]);  // as before
});
