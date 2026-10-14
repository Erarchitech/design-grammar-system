// Only fixed evidence bytes and exact file names are observable; never print content.
const fs = require('node:fs');
const path = require('node:path');

const expected = {
  empty: {},
  init: {},
  named: {'named.txt': 'DG1309-NAMED-READ-VERIFIED'},
  denied: {
    'named.txt': 'DG1309-NAMED-READ-VERIFIED',
    'denied.txt': 'DG1309-DENIED-READ-VERIFIED',
  },
};

try {
  const [stage, directory] = process.argv.slice(2);
  if (!Object.hasOwn(expected, stage) || !directory) throw Error('invalid stage');
  const entries = fs.readdirSync(directory, {withFileTypes: true});
  const names = Object.keys(expected[stage]);
  if (entries.length !== names.length) throw Error('unexpected count');
  if (stage === 'init') {
    if (directory !== '/files/evidence' || process.getuid() !== 0) throw Error('invalid init');
    fs.chownSync(directory, 1000, 1000); // only this disposable named volume
    process.exit(0);
  }
  for (const entry of entries) {
    if (!entry.isFile() || !names.includes(entry.name)) throw Error('unexpected entry');
    const value = fs.readFileSync(path.join(directory, entry.name));
    const wanted = Buffer.from(expected[stage][entry.name], 'utf8');
    if (!value.equals(wanted)) throw Error('unexpected bytes');
  }
  process.exit(0);
} catch {
  process.exit(1);
}
