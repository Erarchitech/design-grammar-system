// Test the variable consolidation logic against neo4j_res3 data (which had duplicates)
// and simulate the neo4j_res4 pattern (R_R redeclared)

// Simulate patterns from neo4j_res3 + neo4j_res4
const testStatements = [
  // First block (model often outputs the node definitions first)
  "MERGE (R_R:Rule {id:'R_URB_HEIGHT_MAX_75_V', kind:'violation'})",
  "MERGE (a1:Atom {id:'R_URB_HEIGHT_MAX_75_V_A1', type:'ClassAtom'})",
  "MERGE (a2:Atom {id:'R_URB_HEIGHT_MAX_75_V_A2', type:'DataPropertyAtom'})",
  "MERGE (a3:Atom {id:'R_URB_HEIGHT_MAX_75_V_A3', type:'BuiltinAtom'})",
  "MERGE (h1:Atom {id:'R_URB_HEIGHT_MAX_75_V_H1', type:'DataPropertyAtom'})",
  "MERGE (R_R)-[:HAS_BODY {order:1}]->(a1)",
  "MERGE (R_R)-[:HAS_BODY {order:2}]->(a2)",
  "MERGE (R_R)-[:HAS_HEAD {order:1}]->(h1)",
  "MERGE (a1)-[:ARG {pos:1}]->(litM)",
  // Second block (model repeats with SET)
  "MERGE (R_R:Rule {id:'R_URB_HEIGHT_MAX_75_V'}) SET R_R.text='Building(?b)^hasHeadM(?b,?h)^swrlb:greaterThan(?h,75)->violation(?b,true)', R_R.kind='violation'",
  "MERGE (a1:Atom {id:'R_URB_HEIGHT_MAX_75_V_A1', type:'ClassAtom'})",
  "MERGE (R_V:Class {iri:'ex:Building'}) SET R_V.label='Building'",
  "MERGE (DP_H:DatatypeProperty {iri:'ex:hasHeightM'}) SET DP_H.label='hasHeightM'",
  "MERGE (DP_V:DatatypeProperty {iri:'ex:violatesMaxHeightM'}) SET DP_V.label='violatesMaxHeightM'",
];

// Deduplicate exact matches first
const unique = [...new Set(testStatements)];
console.log('After dedup:', unique.length, '(from', testStatements.length, ')');

// Separate node MERGEs and relationship MERGEs
const varDefs = new Map();
const otherNodes = [];
const relMerges = [];

for (const stmt of unique) {
  const stripped = stmt.replace(/'[^']*'/g, '');
  if (/-\[/.test(stripped)) {
    relMerges.push(stmt);
    continue;
  }
  const m = stmt.match(/^MERGE\s*\((\w+)(:\w+)\s*(\{[^}]+\})\)\s*(.*)/);
  if (m) {
    const vn = m[1], label = m[2], props = m[3], rest = (m[4] || '').trim();
    if (!varDefs.has(vn)) {
      varDefs.set(vn, { label, props, sets: new Set() });
    }
    if (/^SET\s+/i.test(rest)) {
      const setPart = rest.replace(/^SET\s+/i, '').trim();
      // Split by comma respecting quotes
      const assigns = setPart.split(/,(?=(?:[^']*'[^']*')*[^']*$)/);
      for (const a of assigns) {
        if (a.trim()) varDefs.get(vn).sets.add(a.trim());
      }
    }
  } else {
    otherNodes.push(stmt);
  }
}

console.log('\nVariable definitions:');
for (const [vn, info] of varDefs) {
  console.log(`  ${vn}: ${info.label} ${info.props} | sets: [${[...info.sets].join('; ')}]`);
}

// Rebuild consolidated
const consolidated = [];
for (const [vn, info] of varDefs) {
  let line = 'MERGE (' + vn + info.label + ' ' + info.props + ')';
  if (info.sets.size > 0) {
    line += ' SET ' + [...info.sets].join(', ');
  }
  consolidated.push(line);
}

const finalCypher = [...consolidated, ...otherNodes, ...relMerges].join('\n');

console.log('\nConsolidated nodes:', consolidated.length);
console.log('Other nodes:', otherNodes.length);
console.log('Relationships:', relMerges.length);
console.log('\n--- Final Cypher ---');
console.log(finalCypher);
