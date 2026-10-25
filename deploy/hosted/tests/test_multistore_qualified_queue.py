"""Offline tests only: no PostgreSQL, Redis or native app is contacted."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'recovery-test' / 'multistore_qualified_queue.py'
CONTRACT = HELPER.with_name('speckle-physical-contract.json')


class ContractTests(unittest.TestCase):
    def test_pinned_source_inventory_and_physical_expectations_exist(self):
        self.assertTrue(CONTRACT.is_file(), 'source-derived contract is missing')
        c = json.loads(CONTRACT.read_text(encoding='utf-8'))
        self.assertEqual(c['source']['commit'], '51d43b91c4681a75bff8b285da7f443a4599da67')
        self.assertEqual(c['qualification'], 'SOURCE_DERIVED_NOT_PG_EXECUTED')
        self.assertFalse(c['runtimeQualified'])
        # 147 files under migrations/ includes core/migrations/readme.md.
        self.assertEqual(c['migrationDirectoryFileCount'], 147)
        self.assertEqual(len(c['migrations']), 146)
        self.assertEqual(len({x['name'] for x in c['migrations']}), 146)
        self.assertTrue(all(x['name'].endswith('.js') for x in c['migrations']))
        self.assertEqual(len(c['migrationGroups']['backgroundjobs']), 2)
        # The exact source contains THREE webhooks migrations, not the brief's four.
        self.assertEqual(len(c['migrationGroups']['webhooks']), 3)
        columns = c['catalog']['background_jobs']['columns']
        self.assertNotIn('timeoutMs', columns)
        self.assertEqual({k: columns['remainingComputeBudgetSeconds'][k] for k in ['type','notNull','default']},
                         {'type': 'integer', 'notNull': True, 'default': '3600'})
        self.assertEqual(columns['createdAt']['type'], 'timestamp(3) with time zone')
        self.assertTrue(all(i['predicate'] is None for t in c['catalog'].values() for i in t['indexes']))
        self.assertEqual(c['bull']['version'], '4.16.5')
        self.assertEqual(c['redis']['queues'], ['preview-service-jobs',
                         'preview-service-results-speckle-ingress', 'default:user-notifications'])


    def test_altered_file_upload_timestamps_follow_knex_nullable_alter(self):
        c = json.loads(CONTRACT.read_text(encoding='utf-8'))
        # 20230330082209 .timestamp(...).defaultTo(...).alter() has NO
        # .notNullable(); Knex alter resets nullable to its default true.
        for name in ['uploadDate', 'convertedLastUpdate']:
            self.assertFalse(c['catalog']['file_uploads']['columns'][name]['notNull'])
        self.assertEqual(c['source']['archiveSha256'], '2c178d568a5cc04a6000d0fc61c5488639c3ea61ce518528f47d634f446e73ba')
        self.assertEqual(c['bull']['archiveSha256'], '0b64771e5b00b0267221ead447e69d6c318c1de8318f36dd3a5df0976c4d64e1')


    def test_contract_tamper_cannot_redefine_expectations(self):
        import tempfile
        q = load_helper()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'contract.json'
            c = json.loads(CONTRACT.read_text(encoding='utf-8'))
            c['catalog']['background_jobs']['columns']['id']['type'] = 'jsonb'
            path.write_text(json.dumps(c), encoding='utf-8')
            q.CONTRACT_PATH = path
            with self.assertRaises(q.AdmissionError): q.load_contract()


def load_helper():
    if not HELPER.is_file():
        raise AssertionError('offline queue admission implementation is missing')
    spec = importlib.util.spec_from_file_location('qualified_queue_under_test', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def pg_counts():
    return {**{'background.' + s: 0 for s in ['queued', 'processing', 'succeeded', 'failed']},
            **{'uploads.' + str(s): 0 for s in range(4)},
            **{'webhooks.' + str(s): 0 for s in range(4)},
            **{'previews.' + str(s): 0 for s in range(4)},
            **{s: 0 for s in ['background.invalid', 'background.stale', 'background.exhausted',
                              'uploads.invalid', 'uploads.incomplete', 'webhooks.invalid', 'previews.invalid']}}


def empty_snapshot():
    import copy
    c = json.loads(CONTRACT.read_text(encoding='utf-8'))
    return {'schemaVersion': 1,
            'profile': {'canonicalOrigin': 'http://speckle-ingress:8080', 'redisDb': 0,
                        'nextGenFileImporter': True, 'multiregion': False},
            'postgres': {db: {'catalog': copy.deepcopy(c['catalog']),
                             'migrations': [m['name'] for m in c['migrations']],
                             'migrationLock': 0, 'counts': pg_counts()} for db in ['application', 'fileimport']},
            'redis': {'database': 0, 'scanComplete': True, 'keys': {}}}


class AdmissionTests(unittest.TestCase):
    def test_known_empty_snapshot_yields_only_offline_digest(self):
        q = load_helper()
        result = q.admit_snapshot(empty_snapshot())
        self.assertTrue(result['schemaMatched'])
        self.assertTrue(result['drained'])
        self.assertRegex(result['fingerprint'], r'^[0-9a-f]{64}$')
        self.assertFalse(result['runtimeQualified'])
        self.assertEqual(result['evidenceClass'], 'OFFLINE_UNTRUSTED_OBSERVATION')
        self.assertNotIn('token', json.dumps(result))
        self.assertEqual(result, q.admit_snapshot(empty_snapshot()))


    def test_physical_schema_inventory_and_profile_drift_fail_closed(self):
        import copy
        q = load_helper()
        cases = []
        base = empty_snapshot()
        for db in ['application', 'fileimport']:
            for field in ['catalog', 'migrations', 'migrationLock', 'counts']:
                s = copy.deepcopy(base); del s['postgres'][db][field]; cases.append(s)
            for replacement in [[], base['postgres'][db]['migrations'] + ['unknown.js'],
                                base['postgres'][db]['migrations'] * 2]:
                s = copy.deepcopy(base); s['postgres'][db]['migrations'] = replacement; cases.append(s)
            s = copy.deepcopy(base); s['postgres'][db]['migrationLock'] = True; cases.append(s)
            s = copy.deepcopy(base); s['postgres'][db]['catalog']['background_jobs']['columns']['status']['type'] = 'jsonb'; cases.append(s)
            s = copy.deepcopy(base); s['postgres'][db]['catalog']['background_jobs']['columns']['id']['notNull'] = 1; cases.append(s)
            s = copy.deepcopy(base); s['postgres'][db]['catalog']['background_jobs']['indexes'][0]['predicate'] = 'false'; cases.append(s)
            s = copy.deepcopy(base); s['postgres'][db]['catalog']['file_uploads']['constraints'] = {}; cases.append(s)
            s = copy.deepcopy(base); s['postgres'][db]['catalog']['unexpected'] = {}; cases.append(s)
            s = copy.deepcopy(base); s['postgres'][db]['catalog']['background_jobs']['triggers'] = ['hidden_writer']; cases.append(s)
        for field, value in [('redisDb', True), ('nextGenFileImporter', 1), ('multiregion', True),
                             ('canonicalOrigin', 'http://elsewhere:8080')]:
            s = copy.deepcopy(base); s['profile'][field] = value; cases.append(s)
        s = copy.deepcopy(base); s['unreviewed'] = True; cases.append(s)
        for i, s in enumerate(cases):
            with self.subTest(i=i), self.assertRaises(q.AdmissionError):
                q.admit_snapshot(s)


    def test_postgres_counts_block_busy_failed_stale_and_exhausted(self):
        q = load_helper()
        for key in ['background.queued', 'background.processing', 'background.failed',
                    'background.stale', 'background.exhausted', 'uploads.0', 'uploads.1',
                    'uploads.3', 'uploads.incomplete', 'webhooks.0', 'webhooks.1',
                    'webhooks.3', 'previews.0', 'previews.1', 'previews.3']:
            with self.subTest(key=key):
                s = empty_snapshot(); s['postgres']['application']['counts'][key] = 1
                result = q.admit_snapshot(s)
                self.assertFalse(result['drained'])
                self.assertIsNone(result['fingerprint'])
        s = empty_snapshot()
        for db in s['postgres'].values():
            for k in ['background.succeeded', 'uploads.2', 'webhooks.2', 'previews.2']:
                db['counts'][k] = 2
        self.assertTrue(q.admit_snapshot(s)['drained'])

    def test_postgres_missing_unknown_and_invalid_counts_reject(self):
        q = load_helper()
        for change in ['missing', 'extra', 'bool', 'negative', 'string', 'float', 'overflow', 'invalid']:
            with self.subTest(change=change):
                s = empty_snapshot(); counts = s['postgres']['fileimport']['counts']
                if change == 'missing': del counts['background.queued']
                elif change == 'extra': counts['arbitrary'] = 0
                elif change == 'invalid': counts['background.invalid'] = 1
                else: counts['background.queued'] = {'bool': False, 'negative': -1, 'string': '0',
                                                     'float': 0.0, 'overflow': 2**63}[change]
                with self.assertRaises(q.AdmissionError): q.admit_snapshot(s)


    def test_redis_exact_queue_types_and_all_artifacts_block(self):
        q = load_helper()
        c = json.loads(CONTRACT.read_text(encoding='utf-8'))
        for name in c['redis']['queues']:
            for state, kind in c['redis']['states'].items():
                with self.subTest(queue=name, state=state):
                    s = empty_snapshot(); s['redis']['keys']['bull:' + name + ':' + state] = {'type': kind, 'count': 1}
                    r = q.admit_snapshot(s); self.assertFalse(r['drained']); self.assertIsNone(r['fingerprint'])
        for suffix, kind in [('1', 'hash'), ('1:lock', 'string'), ('1:logs', 'list'),
                             ('de:abc', 'string'), ('limiter', 'string'), ('limiter:index', 'hash'),
                             ('meta-paused', 'string'), ('meta', 'hash'), ('repeat:abc:123', 'hash')]:
            with self.subTest(suffix=suffix):
                s = empty_snapshot(); s['redis']['keys']['bull:preview-service-jobs:' + suffix] = {'type': kind, 'count': 1}
                self.assertFalse(q.admit_snapshot(s)['drained'])
        s = empty_snapshot()
        s['redis']['keys'] = {'bull:preview-service-jobs:id': {'type': 'string', 'value': '3'},
                             'bull:preview-service-jobs:stalled-check': {'type': 'string', 'ttlMs': 120}}
        self.assertTrue(q.admit_snapshot(s)['drained'])

    def test_redis_unknown_incomplete_or_wrong_type_is_never_zero(self):
        import copy
        q = load_helper(); base = empty_snapshot()
        for key, record in [('bull:other:wait', {'type':'list','count':0}),
                            ('bull:preview-service-jobs:unexpected', {'type':'hash','count':0}),
                            ('sess:abc', {'type':'string','count':0}),
                            ('bull:preview-service-jobs:wait', {'type':'zset','count':0}),
                            ('bull:preview-service-jobs:active', {'type':'list','count':False}),
                            ('bull:preview-service-jobs:id', {'type':'string','value':'-1'}),
                            ('bull:preview-service-jobs:stalled-check', {'type':'string','ttlMs':-1})]:
            with self.subTest(key=key, record=record):
                s = copy.deepcopy(base); s['redis']['keys'][key] = record
                with self.assertRaises(q.AdmissionError): q.admit_snapshot(s)
        for field, val in [('database', True), ('database', 1), ('scanComplete', False), ('scanComplete', 1)]:
            s = copy.deepcopy(base); s['redis'][field] = val
            with self.assertRaises(q.AdmissionError): q.admit_snapshot(s)
        s = copy.deepcopy(base); del s['redis']['keys']
        with self.assertRaises(q.AdmissionError): q.admit_snapshot(s)


    def test_zero_length_orphan_hash_still_blocks_and_ttl_is_not_fingerprint(self):
        q = load_helper()
        s = empty_snapshot(); s['redis']['keys']['bull:preview-service-jobs:1'] = {'type': 'hash', 'count': 0}
        self.assertFalse(q.admit_snapshot(s)['drained'])
        a = empty_snapshot(); b = empty_snapshot()
        for snap, ttl in [(a, 100), (b, 50)]:
            snap['redis']['keys']['bull:preview-service-jobs:stalled-check'] = {'type':'string','ttlMs':ttl}
        self.assertEqual(q.admit_snapshot(a)['fingerprint'], q.admit_snapshot(b)['fingerprint'])
        # Actual previews request jobId is project.object, not a numeric Bull ID.
        s = empty_snapshot(); s['redis']['keys']['bull:preview-service-jobs:abc1234567.' + 'a'*32] = {'type':'hash','count':0}
        self.assertFalse(q.admit_snapshot(s)['drained'])


    def test_direct_admission_bounds_apply_before_loading_contract(self):
        q = load_helper()
        s = empty_snapshot()
        # API calls (not only CLI) must bound aggregate input before hashing.
        s['redis']['keys'] = {'bull:preview-service-jobs:repeat:' + 'a'*420 + ':' + str(i):
                              {'type':'hash', 'count':1} for i in range(4096)}
        with self.assertRaises(q.AdmissionError): q.admit_snapshot(s)
        with self.assertRaises(q.AdmissionError): q.admit_snapshot(None)
        s = empty_snapshot(); s['postgres']['application']['counts']['background.queued'] = float('nan')
        with self.assertRaises(q.AdmissionError): q.admit_snapshot(s)


    def test_observation_cannot_claim_empty_retained_redis_collections(self):
        q = load_helper()
        for state in ['wait','active','paused','delayed','priority','repeat','stalled','completed','failed']:
            s = empty_snapshot(); kind = json.loads(CONTRACT.read_text())['redis']['states'][state]
            s['redis']['keys']['bull:preview-service-jobs:' + state] = {'type':kind,'count':0}
            with self.subTest(state=state), self.assertRaises(q.AdmissionError): q.admit_snapshot(s)


class SqlTests(unittest.TestCase):
    def test_sql_emission_is_complete_readonly_and_not_executed(self):
        q = load_helper()
        self.assertTrue(callable(getattr(q, 'emit_postgres_sql', None)), 'fixed SQL emitter missing')
        sql = q.emit_postgres_sql()
        self.assertTrue(sql.startswith('-- SOURCE_DERIVED_NOT_PG_EXECUTED'))
        self.assertIn('BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;', sql)
        self.assertIn("SET LOCAL statement_timeout = '5000ms'", sql)
        self.assertIn('pg_catalog.pg_attribute', sql)
        self.assertIn('pg_catalog.pg_index', sql)
        self.assertIn('pg_catalog.pg_constraint', sql)
        self.assertIn('pg_catalog.pg_trigger', sql)
        self.assertIn('pg_catalog.pg_policy', sql)
        self.assertIn('pg_get_expr(i.indpred', sql)
        self.assertIn('pg_get_expr(d.adbin', sql)
        self.assertIn('knex_migrations_lock', sql)
        self.assertIn('jsonb_object_agg', sql)
        for key in pg_counts(): self.assertIn("'" + key + "'", sql)
        self.assertIn("payload ->> 'fileType'", sql)
        self.assertIn('remainingComputeBudgetSeconds', sql)
        self.assertNotIn('SELECT *', sql.upper())
        import re
        self.assertIsNone(re.search(r'\b(?:UPDATE|DELETE|INSERT|CREATE|DROP|ALTER|COPY)\b', sql, re.I))
        self.assertTrue(sql.rstrip().endswith('COMMIT;'))


    def test_cli_sample_is_explicit_offline_and_bad_input_never_leaks(self):
        import subprocess
        def run(args, data=b''):
            return subprocess.run([sys.executable, '-B', str(HELPER), *args], input=data,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
        result = run(['sample'], json.dumps(empty_snapshot()).encode())
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout.strip(), 'sample CLI did not produce admission JSON')
        self.assertTrue(json.loads(result.stdout)['drained'])
        for raw in [b'', b'{"password":"SECRET_SYNTHETIC"}', b'{"x":1,"x":2}',
                    b'{"x":NaN}', b'x'*1048577, b'['*2000]:
            with self.subTest(size=len(raw)):
                result = run(['sample'], raw)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn(b'SECRET_SYNTHETIC', result.stdout + result.stderr)
                self.assertFalse(json.loads(result.stdout)['schemaMatched'])
                self.assertIsNone(json.loads(result.stdout)['fingerprint'])
                self.assertFalse(json.loads(result.stdout)['runtimeQualified'])
        result = run(['emit-sql'])
        self.assertEqual(result.returncode, 0)
        self.assertIn(b'READ ONLY', result.stdout)


    def test_sql_payload_field_types_and_nullable_timestamps_are_rejected(self):
        q = load_helper(); sql = q.emit_postgres_sql()
        self.assertIn("jsonb_typeof(payload -> field) IS DISTINCT FROM 'string'", sql)
        self.assertIn('"uploadDate" IS NULL', sql)
        self.assertIn('"convertedLastUpdate" IS NULL', sql)
        self.assertIn('jsonb_object_keys(payload)', sql)
        self.assertIn("'payloadVersion','jobType','serverUrl'", sql)


    def test_physical_indexes_include_full_definition_and_column_generation(self):
        q = load_helper(); c = json.loads(CONTRACT.read_text(encoding='utf-8'))
        self.assertIn('pg_catalog.pg_get_indexdef(i.indexrelid)', q.emit_postgres_sql())
        self.assertIn('a.attidentity', q.emit_postgres_sql())
        self.assertIn('a.attgenerated', q.emit_postgres_sql())
        for table, physical in c['catalog'].items():
            for index in physical['indexes']:
                self.assertTrue(index['definition'].startswith('CREATE '))
                self.assertIn(' ON public.' + table + ' USING btree ', index['definition'])
            for column in physical['columns'].values():
                self.assertEqual(column['identity'], '')
                self.assertEqual(column['generated'], '')
                self.assertIs(column['collationDefault'], True)
        self.assertEqual(c['catalog']['file_uploads']['columns']['performanceData']['default'], 'NULL::jsonb')


    def test_cli_no_input_reports_exact_native_transport_gap(self):
        import subprocess
        result = subprocess.run([sys.executable, '-B', str(HELPER), 'sample'], input=b'',
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['error'], 'NATIVE_PROBE_TRANSPORT_UNIMPLEMENTED')


class RespTests(unittest.TestCase):
    @staticmethod
    def frame(value):
        if isinstance(value, list):
            return b'*' + str(len(value)).encode() + b'\r\n' + b''.join(RespTests.frame(v) for v in value)
        if isinstance(value, int): return b':' + str(value).encode() + b'\r\n'
        value = value.encode() if isinstance(value, str) else value
        return b'$' + str(len(value)).encode() + b'\r\n' + value + b'\r\n'

    def test_scan_wire_reads_types_before_lengths_and_deduplicates(self):
        import io
        q = load_helper()
        self.assertTrue(callable(getattr(q, 'collect_redis', None)), 'bounded Redis wire collector missing')
        key = 'bull:preview-service-jobs:id'
        responses = self.frame(['7', [key]]) + self.frame(['0', [key]]) + self.frame('string') + self.frame('2')
        writer = io.BytesIO()
        observed = q.collect_redis(io.BytesIO(responses), writer)
        self.assertEqual(observed, {'database':0, 'scanComplete':True, 'keys':{key:{'type':'string','value':'2'}}})
        self.assertEqual(writer.getvalue(), self.frame(['SCAN','0','COUNT','128'])
                         + self.frame(['SCAN','7','COUNT','128'])
                         + self.frame(['TYPE',key]) + self.frame(['GET',key]))
        s = empty_snapshot(); s['redis'] = observed
        self.assertTrue(q.admit_snapshot(s)['drained'])


    def test_wire_rejects_total_budget_cycle_errors_and_state_type_drift(self):
        import io
        q = load_helper()
        for raw in [b'-SECRET_SYNTHETIC\r\n', b'$999999999999\r\n', b'*999999\r\n',
                    b'$3\r\nx', b'%1\r\n', self.frame(['5', []]) * 2,
                    self.frame(['0', ['bull:other:wait']]),
                    self.frame(['0', ['bull:preview-service-jobs:wait']]) + self.frame('set')]:
            with self.subTest(raw=raw[:30]):
                with self.assertRaises(q.AdmissionError) as caught:
                    q.collect_redis(io.BytesIO(raw), io.BytesIO())
                self.assertNotIn('SECRET_SYNTHETIC', str(caught.exception))
        # SCAN can duplicate the same key forever; enforce TOTAL response bytes,
        # not just a unique-key count, before materializing large replies.
        key = 'bull:preview-service-jobs:id'
        page = self.frame(['5', [key] * 4090])
        with self.assertRaises(q.AdmissionError): q.collect_redis(io.BytesIO(page), io.BytesIO())

    def test_wire_nonempty_zero_count_key_disappearance_rejects(self):
        import io
        q = load_helper()
        key = 'bull:preview-service-jobs:wait'
        # Redis cannot retain an empty list; zero after TYPE implies disappearance
        # or an incoherent synthetic response. Never convert that race to empty.
        data = self.frame(['0', [key]]) + self.frame('list') + self.frame(0)
        with self.assertRaises(q.AdmissionError): q.collect_redis(io.BytesIO(data), io.BytesIO())


    def test_command_cannot_be_used_for_destructive_or_secret_reads(self):
        import io
        q = load_helper()
        # Generic command allowlist alone must not turn this into arbitrary GET
        # against sessions/tokens, SELECT another DB, or a mutation interface.
        for parts in [('EVAL', 'x'), ('KEYS', '*'), ('SELECT', '1'), ('GET', 'sess:token'),
                      ('SCAN', '0', 'MATCH', '*'), ('TYPE', 'unreviewed:key')]:
            with self.subTest(parts=parts):
                with self.assertRaises(q.AdmissionError):
                    q.RespWire(io.BytesIO(b'+OK\r\n'), io.BytesIO()).command(*parts)


    def test_resp_decoder_depth_partial_reads_and_byte_budget(self):
        import io
        q = load_helper()
        class Partial(io.BytesIO):
            def read(self, size=-1): return super().read(min(size, 1))
        data = self.frame(['0', []])
        self.assertEqual(q.collect_redis(Partial(data), io.BytesIO())['keys'], {})
        for data in [b'*1\r\n'*6 + b':0\r\n', b'+' + b'x'*1024 + b'\r\n',
                     b':9223372036854775808\r\n', b'$3\r\nabcxx']:
            with self.subTest(data=data[:20]), self.assertRaises(q.AdmissionError):
                q.RespWire(io.BytesIO(data), io.BytesIO()).response()
        wire = q.RespWire(io.BytesIO(b'abc'), io.BytesIO()); wire.remaining = 2
        with self.assertRaises(q.AdmissionError): wire.read_exact(3)

    def test_wire_type_then_lengths_for_every_supported_collection(self):
        import io
        q = load_helper()
        for state, kind, command in [('wait','list','LLEN'), ('stalled','set','SCARD'),
                                     ('delayed','zset','ZCARD'), ('1','hash','HLEN')]:
            key = 'bull:preview-service-jobs:' + state
            data = self.frame(['0', [key]]) + self.frame(kind) + self.frame(1)
            writer = io.BytesIO(); obs = q.collect_redis(io.BytesIO(data), writer)
            self.assertEqual(obs['keys'][key], {'type':kind, 'count':1})
            self.assertTrue(writer.getvalue().endswith(self.frame(['TYPE',key]) + self.frame([command,key])))
        key = 'bull:preview-service-jobs:stalled-check'
        obs = q.collect_redis(io.BytesIO(self.frame(['0',[key]]) + self.frame('string') + self.frame(50)), io.BytesIO())
        self.assertEqual(obs['keys'][key]['ttlMs'], 50)
        key = 'bull:preview-service-jobs:1:lock'
        writer = io.BytesIO()
        obs = q.collect_redis(io.BytesIO(self.frame(['0',[key]]) + self.frame('string')), writer)
        self.assertEqual(obs['keys'][key]['count'], 1)
        self.assertNotIn(self.frame(['GET', key]), writer.getvalue())


if __name__ == '__main__':
    unittest.main()
