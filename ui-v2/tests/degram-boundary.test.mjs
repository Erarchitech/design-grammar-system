import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { inspectionGraph, inspectionValue } from '../src/degram/inspection.js';

// Supplemental regression/bundle checks; behavior RED/GREEN evidence is browser-side.
test('Restricted surface dependency closure excludes normal screens and model/LLM/connector clients', async () => {
  const result = await build({ entryPoints: ['ui-v2/src/degram/DeGramWorkspace.jsx'], outfile: 'degram.js', bundle: true, write: false, metafile: true, minify: true, define: { 'process.env.NODE_ENV': '"production"' } });
  const sources = Object.keys(result.metafile.inputs).join('\n');
  assert.doesNotMatch(sources, /src\/(screens|landing|App\.jsx)|lib\/(llmApi|modelApi|connectorsApi|inputGenApi|reasonerApi)/);
  for (const dependency of ['graphEngine.js', 'buildRings.js', 'auth.js', 'apiClient.js', 'graphApi.js', 'PropertiesTable.jsx']) assert.ok(sources.includes(dependency), dependency);
  const code = result.outputFiles.find(f => f.path.endsWith('.js')).text;
  assert.doesNotMatch(code, /claim-untagged|rules-ingest|graph-query|design-rule-sessions|llm\/settings|\/connectors|bulk-delete/);
});
test('Inspection projection is immutable and filters nested case/separator variants', () => {
  const props = { graph: 'ValidGraph', provider: 'private', MODEL_ID: 'private', apiKey: 'private', rows: [{ secretToken: 'private', height: 20 }], statePayloadJson: '{"modelName":"private","width":40}', invalidJson: '{broken' };
  const graph = { nodes: [{ id: '1', labels: ['DesignState'], props }], rels: [] };
  const clean = inspectionGraph(graph);
  assert.equal(props.provider, 'private');
  assert.doesNotMatch(JSON.stringify(clean), /private/);
  assert.deepEqual(clean.nodes[0].props.rows, [{ height: 20 }]);
  assert.equal(clean.nodes[0].props.statePayloadJson, '{"width":40}');
  assert.equal(clean.nodes[0].props.invalidJson, '[Structured value unavailable]');
  assert.deepEqual(inspectionValue([null, true, 0, 'safe']), [null, true, 0, 'safe']);
});
