const fs = require('fs');
const raw = JSON.parse(fs.readFileSync('c:/Users/Admin/source/repos/design-grammar-system/test/neo4j_res3.json','utf8'));
// neo4j_res3 has post-cleanup cypher; simulate what the original LLM produced
// by adding the bad line back to test the nesting validator
const cypherText = raw[0].cypher;

function fixOutsideQuotes(str) {
  const parts = str.split("'");
  for (let i = 0; i < parts.length; i += 2) {
    parts[i] = parts[i].replace(/\)\)+/g, ')');
    parts[i] = parts[i].replace(/\}\}+/g, '}');
    parts[i] = parts[i].replace(/\]\}/g, ']');
  }
  return parts.join("'");
}

function hasValidNesting(str) {
  const u = str.replace(/'[^']*'/g, '');
  const stack = [];
  const opn = {'(':')','{':'}','[':']'};
  for (const c of u) {
    if (opn[c]) stack.push(c);
    else if (c === ')' || c === '}' || c === ']') {
      if (!stack.length || opn[stack.pop()] !== c) return false;
    }
  }
  return !stack.length;
}

const chunks = cypherText.split(/(?=MERGE\s)/i).map(s=>s.trim()).filter(s=>/^MERGE\s/i.test(s));
console.log('Total chunks:', chunks.length);
const cleaned = [];
for (const chunk of chunks) {
  let s = chunk;
  if (/MERME|MERX|MER:|MER\s*\{|LexicalForm|LexicalBody|LexicalHead|LexicalRule|LLEX|MERGEMINUS|BVar|:Lex\s/i.test(s)) { console.log('STOP degenerate:', s.slice(0,80)); break; }
  const sq = (s.match(/'/g)||[]).length;
  if (sq % 2 !== 0) { console.log('SKIP odd quotes:', s.slice(0,80)); continue; }
  s = fixOutsideQuotes(s);
  if (!/^MERGE\s*\(/i.test(s)) { console.log('SKIP not MERGE(:', s.slice(0,80)); continue; }
  if (!hasValidNesting(s)) { console.log('SKIP bad nesting:', s.slice(0,80)); continue; }
  const unquoted = s.replace(/'[^']*'/g, '');
  if (/-\[/.test(unquoted) && !/\]->\(\w+/.test(unquoted)) { console.log('SKIP incomplete rel:', s.slice(0,80)); continue; }
  cleaned.push(s);
}
console.log('\nValid:', cleaned.length);
cleaned.forEach((c,i) => console.log((i+1)+':', c));
console.log('\n--- Combined Cypher ---');
console.log(cleaned.join('\n'));
