import test from 'node:test';
import assert from 'node:assert/strict';
import buildRings from '../src/graph/buildRings.js';

// Phase 1303-24 (D-69, owner decision 2026-10-25): the OntoGraph is a flat vocabulary, so an ObjectProperty carries
// its domain and range as node properties and no stored Class -> Class edge exists. The viewer derives one edge per
// property from them; nothing is written anywhere.

let nextId = 1;
const node = (labels, props) => ({ id: nextId++, labels, props: { graph: 'OntoGraph', ...props } });
const cls = (name) => node(['Class'], { iri: `ex:${name}`, label: name });
const prop = (name, domain, range) => node(['ObjectProperty'], { iri: `ex:${name}`, label: name, domain: `ex:${domain}`, range: `ex:${range}` });

function edgesOf(graph, key = 'OntoGraph') {
  const ring = graph.rings.find((r) => r.key === key);
  return ring.edges.map(([a, b, label, derived]) => ({ from: ring.nodes[a].label, to: ring.nodes[b].label, label, derived: derived === true }));
}

const text = (edges) => edges.map((e) => `${e.from}>${e.to}:${e.label}`).sort();

test('an ObjectProperty yields one derived edge from its domain class to its range class', () => {
  nextId = 1;
  const nodes = [cls('Opening'), cls('Slab'), cls('Column'), cls('Wall'),
    prop('hostedBy', 'Opening', 'Slab'), prop('projectsOnto', 'Column', 'Slab'), prop('projectsOntoWall', 'Wall', 'Slab')];
  const derived = edgesOf(buildRings({ nodes, rels: [] })).filter((e) => e.derived);
  assert.deepEqual(text(derived), ['Column>Slab:projectsOnto', 'Opening>Slab:hostedBy', 'Wall>Slab:projectsOntoWall']);
});

test('derived edges add no node or relationship and do not change a node degree', () => {
  nextId = 1;
  const nodes = [cls('Opening'), cls('Slab'), prop('hostedBy', 'Opening', 'Slab')];
  const rels = [{ source: nodes[2].id, type: 'REFERS_TO', target: nodes[0].id }];
  const before = JSON.stringify({ nodes, rels });
  const graph = buildRings({ nodes, rels });
  assert.equal(JSON.stringify({ nodes, rels }), before, 'the fetched graph is not touched');
  const ring = graph.rings[0];
  assert.equal(ring.nodes.length, 3);
  const slab = ring.nodes.find((n) => n.label === 'Slab');
  assert.equal(slab.deg, 0, 'a derived edge is not a stored relationship');
  assert.equal(ring.edges.filter((e) => e[3] !== true).length, 1, 'the stored REFERS_TO edge is unchanged');
});

test('an end that matches no class, or equal ends, add nothing; a property listed twice gives one edge', () => {
  nextId = 1;
  const nodes = [cls('Opening'), cls('Slab'),
    prop('ghost', 'Opening', 'Nothing'), prop('self', 'Slab', 'Slab'),
    prop('hostedBy', 'Opening', 'Slab'), prop('hostedBy', 'Opening', 'Slab')];
  const derived = edgesOf(buildRings({ nodes, rels: [] })).filter((e) => e.derived);
  assert.deepEqual(text(derived), ['Opening>Slab:hostedBy']);
});

test('two different properties between the same classes give two edges, and an ontology without properties none', () => {
  nextId = 1;
  const nodes = [cls('Opening'), cls('Slab'), prop('hostedBy', 'Opening', 'Slab'), prop('cuts', 'Opening', 'Slab')];
  assert.equal(edgesOf(buildRings({ nodes, rels: [] })).filter((e) => e.derived).length, 2);
  nextId = 1;
  assert.equal(edgesOf(buildRings({ nodes: [cls('A'), cls('B')], rels: [] })).length, 0);
});

test('only an OntoGraph property is read, and a class is matched by iri or by local name', () => {
  nextId = 1;
  const meta = node(['ObjectProperty'], { graph: 'Metagraph', iri: 'ex:x', label: 'x', domain: 'ex:Opening', range: 'ex:Slab' });
  const near = node(['ObjectProperty'], { iri: 'ex:near', label: 'near', domain: 'https://w3id.org/dg#Opening', range: 'Slab' });
  const derived = edgesOf(buildRings({ nodes: [cls('Opening'), cls('Slab'), meta, near], rels: [] })).filter((e) => e.derived);
  assert.deepEqual(text(derived), ['Opening>Slab:near']);
});
