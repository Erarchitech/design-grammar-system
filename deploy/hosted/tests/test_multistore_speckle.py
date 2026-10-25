"""Strict OFFLINE tests. SQL text is NOT executed on PostgreSQL here."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / 'recovery-test' / 'multistore_speckle.py'
SCRATCH = Path('C:/Users/Admin/AppData/Local/hermes/cache/scratch/dg-1309-offline-continuation/end-to-end-release/speckle-lane') if os.name == 'nt' else Path(os.environ['TMPDIR'])


class SpeckleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def cli(self, *args, env=None):
        self.assertTrue(HELPER.is_file(), 'executable Speckle helper is missing')
        result = subprocess.run([sys.executable, '-B', str(HELPER), *map(str, args)],
                                env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual('', result.stderr)
        report = json.loads(result.stdout)
        self.assertIs(False, report['nativeRecoveryProven'])
        self.assertIs(False, report['appNativeSeedProven'])
        self.assertIs(False, report['queueCatalogQualified'])
        return result.returncode, report

    def test_emit_fixed_speckle_contract_without_python_in_postgres_NOT_PG_EXECUTED(self):
        directory = self.root / 'sql'
        code, report = self.cli('postgres-sql', '--directory', directory)
        self.assertEqual(0, code)
        self.assertTrue(report['verified'])
        self.assertEqual({'empty.sql', 'snapshot.sql', 'contract.json'}, {p.name for p in directory.iterdir()})
        contract = json.loads((directory / 'contract.json').read_text())
        self.assertEqual(['/usr/local/bin/psql', '-X', '--no-password', '-qAt', '-v', 'ON_ERROR_STOP=1', '--dbname=speckle'], contract['psqlArgv'])
        self.assertEqual(['/usr/local/bin/pg_dump', '--format=custom', '--no-password', '--no-owner', '--no-privileges', '--dbname=speckle'], contract['dumpArgv'])
        self.assertEqual(['/usr/local/bin/pg_restore', '--exit-on-error', '--single-transaction', '--no-password', '--no-owner', '--no-privileges', '--dbname=speckle'], contract['restoreArgv'])
        self.assertEqual(['PGDATABASE', 'PGHOST', 'PGPASSWORD', 'PGPORT', 'PGUSER'], contract['connectionEnvironment'])
        self.assertFalse(contract['sqlExecutedOnPostgres'])
        self.assertEqual('APP_NATIVE_SEED_UNQUALIFIED', contract['appNativeSeedBlocker'])
        for name in ('empty.sql', 'snapshot.sql'):
            data = (directory / name).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), contract['filesSha256'][name])
            sql = data.decode()
            self.assertIn("current_database() <> 'speckle'", sql)
            self.assertIn('160004', sql)
        original = (directory / 'snapshot.sql').read_bytes()
        self.assertEqual(1, self.cli('postgres-sql', '--directory', directory)[0])
        self.assertEqual(original, (directory / 'snapshot.sql').read_bytes())
    def test_catalog_type_values_are_raw_names_not_sql_identifiers_NOT_PG_EXECUTED(self):
        directory = self.root / 'raw-type-contract'
        self.assertEqual(0, self.cli('postgres-sql', '--directory', directory)[0])
        sql = (directory / 'snapshot.sql').read_text()
        self.assertIn("'type',tn.nspname||'.'||t.typname", sql)
        self.assertNotIn("'type',format('%I.%I',tn.nspname,t.typname)", sql)
        # Logical JSON values are names, not executable quoted SQL syntax.
        fixture, _ = self.fixture_files()
        spec = importlib.util.spec_from_file_location('type_contract', HELPER)
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        for kind in ('text', 'varchar', 'numeric', 'timestamp', 'date', 'time', 'interval'):
            fixture['catalog'][1]['columns'][0]['type'] = 'pg_catalog.' + kind
            with self.subTest(kind=kind):
                # Check logical catalog admission, not int4 row data retyped as text.
                tables, _ = helper.catalog_check(fixture['catalog'])
                self.assertEqual('pg_catalog.' + kind,
                                 tables[('Synthetic "Schema', 'knex_migrations')]['columns'][0]['type'])

    def test_full_database_sql_is_bounded_oid_independent_NOT_PG_EXECUTED(self):
        directory = self.root / 'full'
        self.assertEqual(0, self.cli('postgres-sql', '--directory', directory)[0])
        sql = (directory / 'snapshot.sql').read_text()
        for text in ('REPEATABLE READ READ ONLY', 'pg_namespace', 'pg_class', 'pg_attribute',
                     'pg_constraint', 'pg_index', 'pg_sequence', 'pg_proc', 'pg_trigger',
                     'pg_type', 'pg_enum', 'pg_policy', 'pg_inherits', 'pg_depend',
                     'pg_extension', 'pg_largeobject_metadata', 'pg_foreign_server',
                     'pg_publication', 'pg_subscription', 'pg_event_trigger',
                     'pg_get_functiondef', 'pg_get_indexdef', 'pg_get_viewdef',
                     'pg_get_constraintdef', 'pg_get_triggerdef', 'last_value', 'is_called',
                     "format('%I.%I'", 'FROM ONLY %I.%I', '::text', 'sha256(',
                     '100001', '33554432', 'LIMIT 257', 'COLLATE "C"',
                     "'tables'", "'sequences'", "'catalog'", "'rowsSha256'", "'migrations'",
                     "'knex_migrations'", "'knex_migrations_lock'", 'pg_has_role', 'rolbypassrls'):
            self.assertIn(text, sql)
        for text in ('recovery_native', 'CREATE SCHEMA', 'CREATE TABLE', 'CREATE FUNCTION',
                     "'oid',", "'relfilenode'", 'ctid', 'tableoid'):
            self.assertNotIn(text, sql)
        self.assertIn("nspname !~ '^pg_'", sql)
        self.assertIn('information_schema', sql)
        empty = (directory / 'empty.sql').read_text()
        for text in ('pg_namespace', 'pg_class', 'pg_proc', 'pg_type', 'pg_extension',
                     'pg_largeobject_metadata', 'pg_publication', 'pg_subscription',
                     'pg_event_trigger', 'pg_foreign_server', 'pg_default_acl',
                     'pg_collation', 'pg_conversion', 'pg_ts_config', 'pg_operator'):
            self.assertIn(text, empty)
        self.assertIn("SELECT 'PRISTINE_SPECKLE_DESTINATION'", empty)
        contract = json.loads((directory / 'contract.json').read_text())
        self.assertIn('owners, ACLs, roles and cluster globals', contract['exclusions'])
        self.assertIn('fixture.json is independent expected data, not derived from a snapshot', contract['requirements'])
        self.assertEqual(['empty.sql: destination BEFORE pg_restore', 'snapshot.sql: quiesced source BEFORE pg_dump',
                          'pg_dump: source', 'pg_restore: admitted destination', 'snapshot.sql: restored destination',
                          'verify-postgres: independent fixture and both snapshots'], contract['executionOrder'])


    def fixture_files(self):
        # Independent synthetic expected rows/catalog, never harvested from a DB.
        columns = [dict(name='id', position=1, type='pg_catalog.int4', typmod=-1,
                        notNull=True, identity='', collation=None, default=None)]
        catalog = [dict(kind='schema', name='Synthetic "Schema')]
        tables, expected_tables = [], []
        for name, row in [('knex_migrations', '{"id":7}'),
                          ('knex_migrations_lock', '{"id":0}'), ('objects', '{"id":42}')]:
            catalog.append(dict(kind='table', schema='Synthetic "Schema', name=name,
                                replicaIdentity='d', accessMethod='heap', columns=columns,
                                constraints=[], indexes=[]))
            expected_tables.append(dict(schema='Synthetic "Schema', name=name, rows=[row]))
            digest = hashlib.sha256(hashlib.sha256(row.encode()).hexdigest().encode()).hexdigest()
            tables.append(dict(schema='Synthetic "Schema', name=name, rowCount=1, rowsSha256=digest))
        sequence = dict(schema='Synthetic "Schema', name='objects_id_seq', lastValue=42, isCalled=True)
        catalog.append(dict(kind='sequence', schema=sequence['schema'], name=sequence['name'],
                            type='bigint', start=1, increment=1, min=1, max=9223372036854775807,
                            cache=1, cycle=False, ownedBy=[[sequence['schema'],'objects','id','a']]))
        snapshot = dict(schema=1, database='speckle', serverVersion=160004, catalog=catalog,
                        tables=tables, sequences=[sequence], migrations=tables[:2])
        fixture = dict(schema=1, catalog=catalog, tables=expected_tables, sequences=[sequence])
        for name, value in [('fixture.json', fixture), ('source.json', snapshot), ('destination.json', snapshot)]:
            (self.root / name).write_text(json.dumps(value), encoding='utf-8')
        return fixture, snapshot

    def verify(self):
        return self.cli('verify-postgres', '--fixture', self.root / 'fixture.json',
                        '--source', self.root / 'source.json', '--destination', self.root / 'destination.json')

    def test_independent_fixture_and_complete_snapshots_real_cli_SYNTHETIC(self):
        self.fixture_files()
        code, result = self.verify()
        self.assertEqual(0, code)
        self.assertTrue(result['verified'])
        self.assertEqual(1, self.cli('verify-postgres', '--fixture', self.root / 'fixture.json',
                         '--source', self.root / 'source.json', '--destination', self.root / 'source.json')[0])


    def test_validator_rejects_semantic_drift_and_malformed_inputs_SYNTHETIC(self):
        import copy
        fixture, original = self.fixture_files()
        mutations = [
            lambda x: x['tables'].pop(),
            lambda x: x['tables'].append(dict(x['tables'][0], name='extra')),
            lambda x: x['migrations'].pop(),
            lambda x: x['tables'][2].update(rowsSha256='0'*64),
            lambda x: x['sequences'][0].update(lastValue=43),
            lambda x: x['sequences'][0].update(isCalled=1),
            lambda x: x['tables'][2].update(rowCount=True),
            lambda x: x['catalog'][1]['columns'][0].update(type='pg_catalog.text'),
            lambda x: x['catalog'][1]['columns'][0].update(notNull=1),
            lambda x: x.update(schema=True),
            lambda x: x.update(serverVersion=True),
            lambda x: x['catalog'].append(x['catalog'][0]),
            lambda x: x.update(unknown=False),
            lambda x: x['tables'][2].update(rowCount=100001),
        ]
        for number, mutate in enumerate(mutations):
            with self.subTest(case=number):
                value = copy.deepcopy(original)
                mutate(value)
                (self.root / 'destination.json').write_text(json.dumps(value), encoding='utf-8')
                code, result = self.verify()
                self.assertEqual(1, code)
                self.assertFalse(result['verified'])
        for raw in ('{"schema":1,"schema":1}', 'NaN', '['*10000,
                    ' '*4194305, '{}\n{}'):
            (self.root / 'destination.json').write_text(raw, encoding='utf-8')
            self.assertEqual(1, self.verify()[0])
        for name in ('source.json', 'destination.json'):
            value = copy.deepcopy(original)
            value.update(tables=[], catalog=[], sequences=[], migrations=[])
            (self.root / name).write_text(json.dumps(value), encoding='utf-8')
        self.assertEqual(1, self.verify()[0])

    def test_fixture_rejects_boolean_for_integer_even_with_matching_hashes_SYNTHETIC(self):
        fixture, snapshot = self.fixture_files()
        row = '{"id":true}'
        fixture['tables'][2]['rows'] = [row]
        snapshot['tables'][2]['rowsSha256'] = hashlib.sha256(hashlib.sha256(row.encode()).hexdigest().encode()).hexdigest()
        for name, value in [('fixture.json',fixture),('source.json',snapshot),('destination.json',snapshot)]:
            (self.root / name).write_text(json.dumps(value), encoding='utf-8')
        self.assertEqual(1, self.verify()[0])


    def test_prepare_fixed_absent_bucket_real_HTTP_child_SYNTHETIC(self):
        script = r'''
from http.server import HTTPServer, BaseHTTPRequestHandler
import sys
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_GET(self):
  assert self.path == '/dg-recovery-speckle-synthetic'
  assert 'AWS4-HMAC-SHA256' in self.headers['Authorization']
  body=b'<Error><Code>NoSuchBucket</Code></Error>'
  self.send_response(404); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
 def do_PUT(self):
  assert self.path == '/dg-recovery-speckle-synthetic'
  assert self.headers['x-amz-acl']=='private'
  assert self.headers['Content-Length']=='0'
  self.send_response(200); self.send_header('Content-Length','0'); self.end_headers()
s=HTTPServer(('127.0.0.1',0),Handler)
print(s.server_port,flush=True)
s.handle_request(); s.handle_request(); s.server_close()
'''
        child = subprocess.Popen([sys.executable,'-B','-u','-c',script], stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: child.poll() is None and child.kill())
        port = int(child.stdout.readline())
        env = dict(os.environ, RECOVERY_S3_ENDPOINT=f'http://127.0.0.1:{port}',
                   RECOVERY_S3_ALLOW_HTTP='1', RECOVERY_S3_BUCKET='dg-recovery-speckle-synthetic',
                   RECOVERY_S3_ACCESS_KEY='SYNTHETIC', RECOVERY_S3_SECRET_KEY='synthetic-not-owner')
        code, result = self.cli('prepare-bucket', '--admit-synthetic-absent-bucket', env=env)
        self.assertEqual(0, code)
        self.assertTrue(result['verified'])
        out, err = child.communicate(timeout=10)
        self.assertEqual((0,'',''), (child.returncode,out,err))
        for bad in ('owner-bucket','dg-recovery-speckle-synthetic.extra'):
            self.assertEqual(1,self.cli('prepare-bucket','--admit-synthetic-absent-bucket',
                                      env=dict(env,RECOVERY_S3_BUCKET=bad))[0])
        self.assertEqual(1,self.cli('prepare-bucket',env=env)[0])


    def test_sql_rejects_unrepresented_storage_and_array_types_NOT_PG_EXECUTED(self):
        directory = self.root / 'admission'
        self.assertEqual(0, self.cli('postgres-sql', '--directory', directory)[0])
        sql = (directory / 'snapshot.sql').read_text()
        for text in ('c.reltablespace <> 0', "am.amname <> 'heap'", 'a.attcompression',
                     'c.relreplident', 'i.indisvalid', 'i.indisready', 't.typarray',
                     'pg_range', 'pg_transform'):
            self.assertIn(text, sql)
        self.assertNotIn("t.typcategory='A'", sql)

    def test_existing_or_forbidden_bucket_never_PUT_real_HTTP_child_SYNTHETIC(self):
        for status, body in [(200,b''),(403,b'<Error><Code>AccessDenied</Code></Error>'),
                             (404,b'<Error><Code>NoSuchKey</Code></Error>')]:
            script = '''
from http.server import HTTPServer, BaseHTTPRequestHandler
class H(BaseHTTPRequestHandler):
 def log_message(self,*a): pass
 def do_GET(self):
  body=%r
  self.send_response(%d); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
s=HTTPServer(('127.0.0.1',0),H); print(s.server_port,flush=True)
s.handle_request(); s.timeout=1; s.handle_request(); s.server_close()
''' % (body,status)
            child = subprocess.Popen([sys.executable,'-B','-u','-c',script], stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE,text=True)
            self.addCleanup(lambda p=child: p.poll() is None and p.kill())
            port=int(child.stdout.readline())
            env=dict(os.environ,RECOVERY_S3_ENDPOINT=f'http://127.0.0.1:{port}',
                     RECOVERY_S3_ALLOW_HTTP='1',RECOVERY_S3_BUCKET='dg-recovery-speckle-synthetic',
                     RECOVERY_S3_REGION='us-east-1',RECOVERY_S3_ACCESS_KEY='SYNTHETIC',
                     RECOVERY_S3_SECRET_KEY='synthetic-not-owner')
            self.assertEqual(1,self.cli('prepare-bucket','--admit-synthetic-absent-bucket',env=env)[0])
            out,err=child.communicate(timeout=5)
            self.assertEqual((0,'',''),(child.returncode,out,err))


if __name__ == '__main__':
    unittest.main()
