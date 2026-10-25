import test from 'node:test';
import assert from 'node:assert/strict';
import { classifyObjectSets } from '../src/lib/objectSets.js';

// Phase 1303-25 (D-71), live 2026-10-25: 313 opening boxes without data were unknown in the evidence but listed and
// coloured as failing in the Model Viewer. /validation/view objectSets now carries an `unknown` set (no verdict); the
// viewer draws it apart from failing and passing objects.

const e = (id, name) => ({ dgEntityId: id, displayName: name });

test('the unknown set is its own status, not failing and not passing', () => {
  const sets = classifyObjectSets({ failed: [e('B', 'b')], passed: [e('C')], unknown: [e('A', 'a')] });
  assert.equal(sets.statusOf('A'), 'unknown');
  assert.equal(sets.statusOf('B'), 'failed');
  assert.equal(sets.statusOf('C'), 'passed');
  assert.deepEqual(sets.failedIds, ['B']);
  assert.deepEqual(sets.passedIds, ['C']);
  assert.deepEqual(sets.unknownIds, ['A']);
});

test('every object of the three sets is laid out, sorted by id', () => {
  const sets = classifyObjectSets({ failed: [e('B')], passed: [e('C')], unknown: [e('A')] });
  assert.deepEqual(sets.entities.map((x) => x.dgEntityId), ['A', 'B', 'C']);
});

test('a payload without the unknown set behaves as before', () => {
  const sets = classifyObjectSets({ failed: [e('B')], passed: [e('C')] });
  assert.deepEqual(sets.unknownIds, []);
  assert.deepEqual(sets.entities.map((x) => x.dgEntityId), ['B', 'C']);
  assert.equal(sets.statusOf('X'), 'passed');
});

test('no view at all yields empty sets', () => {
  const sets = classifyObjectSets(undefined);
  assert.deepEqual([sets.failedIds, sets.passedIds, sets.unknownIds, sets.entities], [[], [], [], []]);
});

test('list items carry a primary and a secondary line', () => {
  const sets = classifyObjectSets({ unknown: [e('A', 'Box A'), e('B')] });
  assert.deepEqual(sets.unknownItems, [
    { id: 'A', primary: 'Box A', secondary: 'id: A' },
    { id: 'B', primary: 'B', secondary: 'id: B' },
  ]);
});
