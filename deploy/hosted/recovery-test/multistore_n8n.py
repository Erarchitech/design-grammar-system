"""Full stopped-tree helper; n8n 2.4.8 SQLite, Python stdlib only.

OUTER RUNNER CONTRACT (synthetic resources only, separate runtime approval):
Keep this file in recovery-test/ beside ../recovery_n8n.py and
../recovery_filesystem.py. Run it in the existing data-service maintenance image,
no network, mounting the entire STOPPED .n8n tree read-only for inspection/export.
No Docker, n8n process, HTTP, database writes, key generation or activation is
performed by this helper. Native n8n creates/migrates/encrypts the source DB.

CLI (all paths container-local, illustrative placeholders, no secrets in argv):
  python -B multistore_n8n.py prepare --exchange /exchange/n8n-fixture
  python -B multistore_n8n.py inspect --tree TREE COMMON [SEMANTIC]
  python -B multistore_n8n.py snapshot --tree TREE --package PACKAGE
      --key-reference REF COMMON SEMANTIC
  python -B multistore_n8n.py restore --package PACKAGE --destination NEW_TREE
      --expected EXPECTED --key-reference REF COMMON SEMANTIC
  python -B multistore_n8n.py verify --tree RESTORED_TREE --expected EXPECTED
      --key-reference REF COMMON FRESH_SEMANTIC
COMMON = --version 2.4.8 --key-file KEY_FILE --scratch PRIVATE_EXISTING_DIRECTORY
SEMANTIC = --fixture-state /exchange/n8n-fixture/fixture-state.json
           --decrypted-export PRIVATE_NATIVE_EXPORT_FILE
EXPECTED is the snapshot stdout JSON, retained independently of the package in
private exchange storage. Stdout is one sanitized JSON object; failure is exit1
and fixed stderr. No report, key hash, SQL rows or secret value is printed.
The key file is UTF-8 with NO trailing newline, exactly matching config.encryptionKey.
The helper reads no environment inputs and never reads .env/owner config.

Required native calls, exact approved n8n image, bounded outer argv-only launches:
  n8n --version                              # require exactly 2.4.8
  n8n user-management:reset                   # fresh synthetic source ONLY
  n8n import:credentials --input=/exchange/n8n-fixture/credentials.json
  n8n import:workflow --input=/exchange/n8n-fixture/workflow.json
  n8n export:credentials --all --decrypted --output=PRIVATE_SOURCE_EXPORT
Each command must exit, then prove no .n8n writers/consumers remain before helper
calls. Native CLI import encrypts object-valued data. BaseCommand initializes and
migrates SQLite; reset creates/uses the shell owner and personal project. Import
always replaces workflow versionId and deactivates it, so semantic verification
compares nodes/connections/settings and credential references, not import UUID.
After restoring, DO NOT reimport/reset/seed: run the same native decrypted export
to a NEW initially absent private destination export file, then stop/verify all
native processes before `verify` with that fresh file. Exit0 or a supplied JSON
file alone is NOT proof native CLI ran: the trusted runner must record its actual
launch/image/exit and unique output provenance, never substitute stale exports.

Pin effective native env: DB_TYPE=sqlite, DB_SQLITE_DATABASE=database.sqlite,
DB_TABLE_PREFIX empty, EXECUTIONS_MODE=regular, N8N_ENCRYPTION_KEY_FILE=KEY_FILE,
N8N_DIAGNOSTICS_ENABLED=false, N8N_VERSION_NOTIFICATIONS_ENABLED=false,
N8N_TEMPLATES_ENABLED=false, N8N_COMMUNITY_PACKAGES_ENABLED=false. Require binary
storage filesystem under this tree (N8N_DEFAULT_BINARY_DATA_MODE=filesystem,
N8N_BINARY_DATA_STORAGE_PATH=.../.n8n/binaryData); no external DB/S3/path overrides,
custom nodes/hooks, unapproved settings or live queue mode. Network denial is the
real no-egress gate. Suppress/retain native stdout/stderr privately; never print
decrypted exports, fixture-state.json or plaintext import JSON. Delete exports
and fixture/key scratch under the outer protected-volume cleanup contract.

NEW_TREE must NOT exist; never restore over an existing mounted-volume root. In
the synthetic harness mount the volume at the PARENT and use its .n8n child (and
matching native N8N_USER_FOLDER parent), or provide another approved nonexistent
child. Mounting an empty root directly does not satisfy the archive API.
Restored files are helper-owned mode0600/dirs0700; run helper with native n8n UID
(usually1000) or independently fix/verify ownership before native CLI use.

All SQLite access uses a disposable FULL tree copy; mode=ro on the source could
mutate WAL SHM. Cleanup closes connections before deleting scratch. Manifest
hashes verify the complete tree/config/key/sidecars/binaryData before restore;
post-native-open verification compares logical core DB rows plus binary hashes,
not physical SQLite bytes (native WAL checkpointing can legitimately change them).
Limits: underlying archive4096 entries/64GiB, JSON1MiB, core table10000 rows/1MiB
per encoded row. Scratch must be private/quota-backed outside source/package/target.
Unsupported schemas, unknown status (including 'unknown'), missing columns,
nonterminal/contradictory rows, active workflows and mismatched keys fail closed.
`inspect` reports nonzero queues for outer polling; snapshot/restore/verify reject.

PUBLIC SOURCE BASIS, NOT TARGET QUALIFICATION:
https://github.com/n8n-io/n8n/tree/e040ab67e5acf63df4438a7f9352ab91cd43ccc4
(n8n@2.4.8). Required shape from packages/@n8n/db/src/entities/{execution-entity,
workflow-entity,credentials-entity,settings}.ts and SQLite/common migrations.
128 migration names from db/src/migrations/sqlite/index.ts (upstream SHA256
5f30156f1f57a10c5f514274527b1fac4675ec12306749d51a36c32cbe679a9b), exact
membership/timestamps checked independent of execution order. Status enum from
packages/workflow/src/execution-status.ts. Import/export behavior from
packages/cli/src/commands/{import,export}/credentials.ts, import/workflow.ts,
services/import.service.ts and commands/base-command.ts. This required-column
profile is not an attestation of every n8n table/index/migration implementation.

Offline tests use explicitly synthetic schemas/opaque credential text and parser
exports, never claim native migration or decryption. Every result deliberately
retains nativeRecoveryProven=false: only the independently authorized outer run
can establish native evidence. Binary bytes are preserved/compared, but reading
native binary objects through an executed workflow/API is a separate runtime
check; this fixture deliberately never executes its disabled HTTP node.
"""
from contextlib import closing
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import sqlite3
import sys
import tempfile
import uuid

_HOSTED = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_HOSTED))
try:
    import recovery_n8n as archive
finally:
    sys.path.remove(str(_HOSTED))

VERSION = '2.4.8'
ERROR = 'n8n recovery check failed'


class ProbeError(ValueError):
    pass


def require(value):
    if not value:
        raise ProbeError(ERROR)


def _write_json(path, value):
    raw = json.dumps(value, sort_keys=True, separators=(',', ':')).encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
    with os.fdopen(fd, 'wb') as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())


def prepare_fixture(exchange):
    """Generate private import JSON only; native CLI must create/migrate the DB."""
    owned = False
    try:
        exchange = Path(os.path.abspath(exchange))
        archive._root(exchange.parent)
        archive._name(exchange.name)
        exchange.mkdir(mode=0o700)
        owned = True
        suffix = secrets.token_hex(8)
        credential = {'id': 'dgcred' + suffix, 'name': 'DG recovery ' + suffix,
                      'type': 'httpHeaderAuth', 'data': {'name': 'X-DG-Recovery',
                                                       'value': secrets.token_hex(32)}}
        workflow = {'id': 'dgwf' + suffix, 'name': 'DG recovery ' + suffix,
                    'active': False, 'versionId': str(uuid.uuid4()),
                    'nodes': [
                        {'id': 'manual', 'name': 'Manual', 'type': 'n8n-nodes-base.manualTrigger',
                         'typeVersion': 1, 'position': [0, 0], 'parameters': {}},
                        {'id': 'offline', 'name': 'Never send', 'type': 'n8n-nodes-base.httpRequest',
                         'typeVersion': 4.2, 'position': [240, 0], 'disabled': True,
                         'parameters': {'url': 'http://127.0.0.1:9', 'authentication': 'genericCredentialType',
                                        'genericAuthType': 'httpHeaderAuth'},
                         'credentials': {'httpHeaderAuth': {'id': credential['id'], 'name': credential['name']}}}],
                    'connections': {'Manual': {'main': [[{'node': 'Never send', 'type': 'main', 'index': 0}]]}},
                    'settings': {'executionOrder': 'v1'}}
        _write_json(exchange / 'credentials.json', [credential])
        _write_json(exchange / 'workflow.json', [workflow])
        _write_json(exchange / 'fixture-state.json', {'schemaVersion': 1, 'version': VERSION,
                                                    'credential': credential, 'workflow': workflow})
        return {'fixturePrepared': True, 'nativeRecoveryProven': False}
    except Exception:
        if owned:
            shutil.rmtree(exchange)
        raise ProbeError(ERROR) from None


def _json_loads(raw):
    def reject(_):
        raise ProbeError(ERROR)
    value = json.loads(raw, object_pairs_hook=archive._pairs, parse_constant=reject)
    # Also reject overflowed standard numeric literals (e.g. 1e999).
    json.dumps(value, allow_nan=False)
    return value


def _same_json(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(_same_json(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(_same_json(a, b) for a, b in zip(left, right))
    return left == right


def _read_json(path):
    path = Path(path)
    require(archive._regular(path).st_size <= archive.MAX_MANIFEST)
    return _json_loads(path.read_bytes())


def _fixture_schema(state):
    require(type(state) is dict and set(state) == {'schemaVersion', 'version', 'workflow', 'credential'})
    require(type(state['schemaVersion']) is int and state['schemaVersion'] == 1 and state['version'] == VERSION)
    w, c = state['workflow'], state['credential']
    require(type(w) is dict and set(w) == {'id', 'name', 'active', 'versionId', 'nodes', 'connections', 'settings'})
    require(type(c) is dict and set(c) == {'id', 'name', 'type', 'data'})
    require(all(type(w[k]) is str and w[k] for k in ('id', 'name', 'versionId')) and w['active'] is False)
    require(all(type(c[k]) is str and c[k] for k in ('id', 'name', 'type')))
    require(type(c['data']) is dict and all(type(c['data'].get(k)) is str and c['data'][k] for k in ('name', 'value')))
    require(type(w['nodes']) is list and w['nodes'] and type(w['connections']) is dict and type(w['settings']) is dict)
    for node in w['nodes']:
        require(type(node) is dict and {'id', 'name', 'type', 'typeVersion', 'position', 'parameters'} <= node.keys())
        require(all(type(node[k]) is str and node[k] for k in ('id', 'name', 'type')))
        require(type(node['typeVersion']) in (int, float) and type(node['parameters']) is dict)
        require(type(node['position']) is list and len(node['position']) == 2
                and all(type(v) in (int, float) for v in node['position']))
        require('disabled' not in node or type(node['disabled']) is bool)
        require('credentials' not in node or type(node['credentials']) is dict)


def _expected_schema(expected, version, key_reference):
    require(type(expected) is dict and set(expected) == {'schemaVersion', 'version',
            'keyReference', 'manifestSha256', 'observation', 'nativeRecoveryProven'})
    require(type(expected['schemaVersion']) is int and expected['schemaVersion'] == 1
            and expected['version'] == version == VERSION and expected['keyReference'] == key_reference
            and expected['nativeRecoveryProven'] is False)
    observation = expected['observation']
    counters = ('workflowCount', 'credentialCount', 'activeWorkflowCount', 'settingsCount')
    hashes = ('logicalStateSha256', 'binaryStateSha256')
    require(type(observation) is dict and set(observation) ==
            {'schemaVersion', 'version', 'executions', 'nativeRecoveryProven',
             'workflowMatched', 'credentialExportMatched', *counters, *hashes})
    require(type(observation['schemaVersion']) is int and observation['schemaVersion'] == 1
            and observation['version'] == VERSION and observation['nativeRecoveryProven'] is False
            and observation['workflowMatched'] is True and observation['credentialExportMatched'] is True)
    require(all(type(observation[k]) is int and 0 <= observation[k] <= 10000 for k in counters))
    executions = observation['executions']
    require(type(executions) is dict and set(executions) == {'pending', 'running', 'waiting'})
    require(all(type(v) is int and 0 <= v <= 10000 for v in executions.values()))
    for value in (expected['manifestSha256'], *(observation[k] for k in hashes)):
        require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value))


def _verify_semantics(db, fixture_state, decrypted_export):
    state = _read_json(fixture_state)
    _fixture_schema(state)
    workflow, credential = state['workflow'], state['credential']
    row = db.execute('SELECT name,active,activeVersionId,nodes,connections,settings FROM workflow_entity WHERE id=?',
                     (workflow['id'],)).fetchone()
    require(row is not None and row[0] == workflow['name'] and row[1] == 0 and row[2] is None)
    for raw, name in zip(row[3:], ('nodes', 'connections', 'settings')):
        require(_same_json(_json_loads(raw), workflow[name]))
    row = db.execute('SELECT name,type,data FROM credentials_entity WHERE id=?', (credential['id'],)).fetchone()
    require(row is not None and row[0] == credential['name'] and row[1] == credential['type'])
    require(type(row[2]) is str and len(row[2]) > 0 and credential['data']['value'] not in row[2])
    exported = _read_json(decrypted_export)
    require(type(exported) is list and len(exported) == 1 and type(exported[0]) is dict)
    require(all(_same_json(exported[0].get(name), credential[name]) for name in ('id', 'name', 'type', 'data')))
    return {'workflowMatched': True, 'credentialExportMatched': True}


def _logical_digest(db):
    digest = hashlib.sha256()
    for table in ('workflow_entity', 'credentials_entity', 'settings', 'execution_entity', 'execution_data'):
        info = db.execute('PRAGMA table_info("' + table + '")').fetchall()
        columns = [row[1] for row in info]
        primary = [row[1] for row in sorted(info, key=lambda row: row[5]) if row[5]]
        quote = lambda name: '"' + name.replace('"', '""') + '"'
        digest.update(json.dumps([table, columns], separators=(',', ':')).encode())
        count = 0
        for row in db.execute('SELECT * FROM ' + quote(table) + ' ORDER BY ' + ','.join(map(quote, primary))):
            count += 1
            require(count <= 10000)
            values = [['blob', value.hex()] if type(value) is bytes else value for value in row]
            raw = json.dumps(values, separators=(',', ':'), allow_nan=False).encode()
            require(len(raw) <= archive.MAX_MANIFEST)
            digest.update(len(raw).to_bytes(8, 'big'))
            digest.update(raw)
    return digest.hexdigest()


def _inspect_database(db):
    # Bound SQLite values/whole records BEFORE Python materialization. JSON's
    # worst-case ASCII escaping is 12 bytes per UTF-8 byte; BLOB hex is 2x.
    db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, archive.MAX_MANIFEST // 12)
    db.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 256)
    catalog = db.execute("SELECT name, type FROM sqlite_master LIMIT 513").fetchmany(513)
    require(len(catalog) <= 512)
    tables = dict(catalog)
    columns = {
        'workflow_entity': {'id', 'name', 'active', 'activeVersionId', 'nodes', 'connections', 'settings', 'versionId'},
        'credentials_entity': {'id', 'name', 'data', 'type'},
        'execution_entity': {'id', 'workflowId', 'finished', 'mode', 'status', 'createdAt',
                             'startedAt', 'stoppedAt', 'deletedAt', 'waitTill', 'retryOf', 'retrySuccessId'},
        'execution_data': {'executionId', 'workflowData', 'data', 'workflowVersionId'},
        'settings': {'key', 'value', 'loadOnStartup'},
        'migrations': {'id', 'timestamp', 'name'},
    }
    for table, expected in columns.items():
        require(tables.get(table) == 'table')
        info = {row[1]: row for row in db.execute('PRAGMA table_info("' + table + '")')}
        require(expected <= info.keys())
        for name in expected:
            declared = info[name][2].lower().split('(')[0]
            if name in ('finished', 'active', 'loadOnStartup'):
                require(declared == 'boolean')
            elif name in ('timestamp', 'executionId') or (table in ('execution_entity', 'migrations') and name == 'id'):
                require(declared in ('int', 'integer', 'bigint'))
            elif name in ('startedAt', 'stoppedAt', 'createdAt', 'deletedAt', 'waitTill'):
                require(declared == 'datetime')
            else:
                require(declared in ('text', 'varchar'))
        primary = {'workflow_entity': 'id', 'credentials_entity': 'id', 'execution_entity': 'id',
                   'execution_data': 'executionId', 'settings': 'key', 'migrations': 'id'}[table]
        require(info[primary][5] == 1)
    require(db.execute('SELECT count(*) FROM workflow_entity WHERE active IS NULL OR '
                       'active NOT IN (0,1)').fetchone()[0] == 0)
    ledger = db.execute('SELECT name,timestamp FROM migrations ORDER BY id LIMIT 129').fetchmany(129)
    names = [row[0] for row in ledger]
    # Exact membership, independent of TypeORM execution order or upgrade history.
    # This is compatibility validation, not proof a native process ran migrations.
    require(len(names) == 128 and all(type(n) is str for n in names))
    require(hashlib.sha256(json.dumps(sorted(names), separators=(',', ':')).encode()).hexdigest()
            == '86289baf63780b03fb95a41da1ef374848ffcbde1111f726f0e580634bec31c0')
    require(all(type(ts) is int and ts == int(n[-13:]) for n, ts in ledger))
    require(db.execute('PRAGMA integrity_check(1)').fetchmany(2) == [('ok',)])
    require(not db.execute('PRAGMA foreign_key_check').fetchmany(1))
    # 2.4.8 ExecutionEntity documents finished as successful, not merely
    # terminal. Failed/canceled/crashed executions may legitimately store zero.
    require(db.execute("SELECT count(*) FROM execution_entity WHERE "
                       "typeof(finished) != 'integer' OR finished NOT IN (0,1) OR "
                       "(status='success' AND finished != 1)").fetchone()[0] == 0)
    counts = {'pending': 0, 'running': 0, 'waiting': 0}
    # Conservatively refuse contradictory terminal rows (including deleted rows)
    # rather than interpreting status alone as proof nothing can resume.
    require(db.execute("SELECT count(*) FROM execution_entity WHERE status IN "
                       "('success','error','canceled','crashed') AND "
                       "(stoppedAt IS NULL OR waitTill IS NOT NULL)").fetchone()[0] == 0)
    for status, count in db.execute('SELECT status, count(*) FROM execution_entity GROUP BY status'):
        require(status in ('new', 'running', 'waiting', 'success', 'error', 'canceled', 'crashed'))
        if status in ('new', 'running', 'waiting'):
            counts[{'new': 'pending', 'running': 'running', 'waiting': 'waiting'}[status]] = count
    return {'schemaVersion': 1, 'version': VERSION, 'executions': counts,
            'workflowCount': db.execute('SELECT count(*) FROM workflow_entity').fetchone()[0],
            'credentialCount': db.execute('SELECT count(*) FROM credentials_entity').fetchone()[0],
            'activeWorkflowCount': db.execute('SELECT count(*) FROM workflow_entity WHERE active != 0 '
                                               'OR activeVersionId IS NOT NULL').fetchone()[0],
            'settingsCount': db.execute('SELECT count(*) FROM settings').fetchone()[0],
            'nativeRecoveryProven': False}


def inspect_tree(tree, *, version, key_file, scratch, fixture_state=None, decrypted_export=None):
    """Inspect an isolated copy; unknown schemas raise, never return zero."""
    try:
        require(version == VERSION)
        tree = archive._root(tree)
        scratch = archive._root(scratch)
        require(tree != scratch and tree not in scratch.parents and scratch not in tree.parents)
        with tempfile.TemporaryDirectory(prefix='n8n-probe-', dir=scratch) as temporary:
            package = Path(temporary) / 'package'
            manifest = archive.export_state(tree, package, version=version, attest=lambda _: True)
            inventory = {name: manifest[name] for name in ('files', 'directories')}
            clone = package / 'tree'
            config = json.loads((clone / 'config').read_bytes(), object_pairs_hook=archive._pairs)
            key = Path(key_file)
            require(archive._regular(key).st_size <= 4096)
            require(key.read_bytes().decode('utf-8') == config['encryptionKey'])
            with closing(sqlite3.connect((clone / 'database.sqlite').as_uri() + '?mode=ro', uri=True)) as db:
                db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, archive.MAX_MANIFEST // 12)
                db.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 256)
                db.execute('PRAGMA query_only=ON')
                result = _inspect_database(db)
                result['logicalStateSha256'] = _logical_digest(db)
                require(archive._inventory(tree) == inventory)
                binary = {name: item for name, item in inventory['files'].items() if name.startswith('binaryData/')}
                result['binaryStateSha256'] = hashlib.sha256(json.dumps(binary, sort_keys=True,
                                                separators=(',', ':')).encode()).hexdigest()
                require((fixture_state is None) == (decrypted_export is None))
                if fixture_state is not None:
                    result.update(_verify_semantics(db, fixture_state, decrypted_export))
                return result
    except Exception:
        raise ProbeError(ERROR) from None


def _key_reference(value):
    require(type(value) is str and re.fullmatch('[A-Za-z0-9_.-]{1,128}', value))


def snapshot_tree(tree, package, *, version, key_file, key_reference, scratch,
                  fixture_state, decrypted_export):
    """Publish stopped full tree only after drain and semantic checks."""
    try:
        _key_reference(key_reference)
        require(fixture_state is not None and decrypted_export is not None)
        observation = inspect_tree(tree, version=version, key_file=key_file, scratch=scratch,
                                   fixture_state=fixture_state, decrypted_export=decrypted_export)
        require(not any(observation['executions'].values()) and observation['activeWorkflowCount'] == 0)
        # Reinspect the exact bytes at the adapter's pre-copy boundary. No claim
        # that this callback discovers live processes or establishes authority.
        def admit(_):
            require(inspect_tree(tree, version=version, key_file=key_file, scratch=scratch,
                    fixture_state=fixture_state, decrypted_export=decrypted_export) == observation)
            return True
        archive.export_state(tree, package, version=version, attest=admit)
        digest = archive._hash(Path(package) / 'state-manifest.json')['sha256']
        return {'schemaVersion': 1, 'version': VERSION, 'keyReference': key_reference,
                'manifestSha256': digest, 'observation': observation, 'nativeRecoveryProven': False}
    except Exception:
        raise ProbeError(ERROR) from None


def restore_tree(package, destination, *, version, key_file, key_reference, scratch,
                 expected, fixture_state, decrypted_export):
    """Validate whole package and key/semantics BEFORE destination publication.

    `expected` must be retained separately by the trusted runner, not loaded from
    a self-asserting package. After restore native n8n must freshly decrypt.
    """
    try:
        _key_reference(key_reference)
        require(fixture_state is not None and decrypted_export is not None)
        _expected_schema(expected, version, key_reference)
        def admit(_):
            observation = inspect_tree(Path(package) / 'tree', version=version, key_file=key_file,
                            scratch=scratch, fixture_state=fixture_state, decrypted_export=decrypted_export)
            require(_same_json(observation, expected['observation']) and not any(observation['executions'].values())
                    and observation['activeWorkflowCount'] == 0)
            return True
        archive.restore_state(package, destination, version=version,
                    expected_manifest_sha256=expected['manifestSha256'], attest=admit)
        return {'treeRestored': True, 'nativeRecoveryProven': False}
    except Exception:
        raise ProbeError(ERROR) from None


def verify_tree(tree, *, expected, key_reference, version, key_file, scratch,
                fixture_state, decrypted_export):
    """Compare post-native-open logical DB/binary state to retained snapshot."""
    try:
        _key_reference(key_reference)
        require(fixture_state is not None and decrypted_export is not None)
        _expected_schema(expected, version, key_reference)
        result = inspect_tree(tree, version=version, key_file=key_file, scratch=scratch,
                              fixture_state=fixture_state, decrypted_export=decrypted_export)
        require(_same_json(result, expected['observation']) and not any(result['executions'].values())
                and result['activeWorkflowCount'] == 0)
        return {**result, 'restoredStateMatched': True}
    except Exception:
        raise ProbeError(ERROR) from None


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ProbeError(ERROR)


def main(argv=None):
    """Fixed modes, JSON success / fixed stderr + exit1; never echo bad argv."""
    try:
        parser = _Parser(add_help=False)
        modes = parser.add_subparsers(dest='mode', required=True, parser_class=_Parser)
        prepare = modes.add_parser('prepare', add_help=False)
        prepare.add_argument('--exchange', required=True)
        for mode in ('inspect', 'verify', 'snapshot', 'restore'):
            command = modes.add_parser(mode, add_help=False)
            for name in ('version', 'key-file', 'scratch'):
                command.add_argument('--' + name, required=True)
            if mode in ('inspect', 'verify', 'snapshot'):
                command.add_argument('--tree', required=True)
            if mode in ('snapshot', 'restore'):
                command.add_argument('--package', required=True)
            if mode in ('snapshot', 'restore', 'verify'):
                command.add_argument('--key-reference', required=True)
            if mode == 'restore':
                command.add_argument('--destination', required=True)
            if mode in ('restore', 'verify'):
                command.add_argument('--expected', required=True)
            for name in ('fixture-state', 'decrypted-export'):
                command.add_argument('--' + name, required=mode != 'inspect')
        args = parser.parse_args(sys.argv[1:] if argv is None else argv)
        if args.mode == 'prepare':
            result = prepare_fixture(args.exchange)
        else:
            options = {name: getattr(args, name) for name in
                       ('version', 'key_file', 'scratch', 'fixture_state', 'decrypted_export')}
            if args.mode == 'inspect':
                result = inspect_tree(args.tree, **options)
            elif args.mode == 'verify':
                result = verify_tree(args.tree, expected=_read_json(args.expected),
                                     key_reference=args.key_reference, **options)
            elif args.mode == 'snapshot':
                result = snapshot_tree(args.tree, args.package, key_reference=args.key_reference, **options)
            else:
                result = restore_tree(args.package, args.destination, key_reference=args.key_reference,
                                      expected=_read_json(args.expected), **options)
        print(json.dumps(result, sort_keys=True, separators=(',', ':')))
        return 0
    except Exception:
        print(ERROR, file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
