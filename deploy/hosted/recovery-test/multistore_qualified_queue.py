"""Source-bound OFFLINE PostgreSQL/Bull queue admission.

No native transport is enabled. `sample` reads an explicitly supplied bounded
JSON observation from stdin; a no-input orchestrator call fails closed. Emitted
SQL is SOURCE_DERIVED_NOT_PG_EXECUTED. Offline observations are untrusted and
never establish a producer barrier, independent n8n drain, native qualification,
or authenticated store/catalog identity. See the adjacent contract limitations.
"""
import hashlib
import json
import re
import sys
from pathlib import Path

CONTRACT_PATH = Path(__file__).with_name('speckle-physical-contract.json')
# Binding protects against independently replacing the expectation file; it is
# not a signature or an assertion of native schema/runtime qualification.
CONTRACT_SHA256 = '72789eadb4997d51cf0637319db09d3107cd246080e62fcb4e6db9a8c4d6f5ce'


class AdmissionError(ValueError):
    """Fixed messages only; never include catalog, payload, keys or secrets."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def load_contract():
    with CONTRACT_PATH.open('rb') as stream:
        raw = stream.read(256 * 1024 + 1)
    require(len(raw) <= 256 * 1024 and hashlib.sha256(raw).hexdigest() == CONTRACT_SHA256,
            'CONTRACT_INTEGRITY_REJECTED')
    return strict_json(raw)


def require(condition, code='OBSERVATION_REJECTED'):
    if not condition:
        raise AdmissionError(code)


def exact_keys(value, keys):
    require(type(value) is dict and set(value) == set(keys))


def count_keys():
    return (['background.' + s for s in ['queued', 'processing', 'succeeded', 'failed']]
            + [group + '.' + str(s) for group in ['uploads', 'webhooks', 'previews'] for s in range(4)]
            + ['background.invalid', 'background.stale', 'background.exhausted',
               'uploads.invalid', 'uploads.incomplete', 'webhooks.invalid', 'previews.invalid'])


def unsigned_count(value):
    require(type(value) is int and 0 <= value < 2**63, 'COUNT_REJECTED')
    return value


def classify_key(key, contract):
    require(type(key) is str and len(key) <= 512, 'REDIS_KEY_REJECTED')
    suffix = None
    for queue in contract['queues']:
        prefix = contract['prefix'] + ':' + queue + ':'
        if key.startswith(prefix):
            suffix = key[len(prefix):]
            break
    require(suffix is not None and suffix != '', 'UNKNOWN_REDIS_NAMESPACE')
    if suffix in contract['states']:
        return suffix, contract['states'][suffix]
    if suffix in contract['controls']:
        return suffix, contract['controls'][suffix]
    # Speckle production jobs use generated numeric IDs; repeat-job IDs and
    # per-job lock/log/debounce artifacts are recognized but NEVER drained.
    job_pattern = r'(?:[0-9]+|[a-zA-Z0-9_-]{1,64}\.[a-zA-Z0-9_-]{1,64}|repeat:[a-zA-Z0-9_-]+:[0-9]+)'
    if re.fullmatch(job_pattern, suffix):
        return 'job', 'hash'
    if re.fullmatch(job_pattern + ':lock', suffix) or re.fullmatch(r'de:[a-zA-Z0-9_-]+', suffix):
        return 'lock', 'string'
    if re.fullmatch(job_pattern + ':logs', suffix):
        return 'logs', 'list'
    raise AdmissionError('UNKNOWN_REDIS_STATE')


def validate_redis(redis, contract):
    exact_keys(redis, ['database', 'scanComplete', 'keys'])
    require(type(redis['database']) is int and redis['database'] == 0, 'REDIS_DB_REJECTED')
    require(redis['scanComplete'] is True, 'INCOMPLETE_REDIS_SCAN')
    require(type(redis['keys']) is dict and len(redis['keys']) <= 4096, 'REDIS_SCAN_LIMIT')
    drained = True
    for key, record in redis['keys'].items():
        role, kind = classify_key(key, contract)
        require(type(record) is dict and record.get('type') == kind, 'REDIS_TYPE_REJECTED')
        if role == 'id':
            exact_keys(record, ['type', 'value'])
            require(type(record['value']) is str and re.fullmatch(r'[0-9]{1,19}', record['value']) is not None,
                    'REDIS_ID_REJECTED')
            unsigned_count(int(record['value']))
        elif role == 'stalled-check':
            exact_keys(record, ['type', 'ttlMs'])
            require(type(record['ttlMs']) is int and 0 < record['ttlMs'] <= 30000, 'REDIS_TTL_REJECTED')
        else:
            exact_keys(record, ['type', 'count'])
            count = unsigned_count(record['count'])
            # String artifacts carry existence count=1, not their secret values.
            require(kind != 'string' or count == 1, 'REDIS_COUNT_REJECTED')
            require(role not in contract['states'] or count > 0, 'REDIS_KEY_DISAPPEARED')
            drained = drained and count == 0 and role not in ['job', 'lock', 'logs', 'meta', 'meta-paused', 'limiter', 'limiter:index']
    return drained


class RespWire:
    """RESP2 on supplied binary streams; no dialing, AUTH or endpoint selection.

    A future native connector must bind DB0, authenticated store identity and an
    absolute wall-clock timeout before supplying streams. These byte/iteration
    limits do not preempt a blocked read. Never return server error strings.
    """
    def __init__(self, reader, writer):
        self.reader, self.writer = reader, writer
        self.remaining = 1024 * 1024

    def read_exact(self, size):
        require(0 <= size <= self.remaining, 'RESP_LIMIT')
        result = bytearray()
        while len(result) < size:
            part = self.reader.read(size - len(result))
            require(type(part) is bytes and 0 < len(part) <= size - len(result), 'RESP_TRUNCATED')
            result.extend(part)
        self.remaining -= size
        return bytes(result)

    def line(self):
        value = bytearray()
        while not value.endswith(b'\r\n'):
            require(len(value) < 1024, 'RESP_LIMIT')
            value.extend(self.read_exact(1))
        return bytes(value[:-2])

    def response(self, depth=0):
        require(depth <= 3, 'RESP_LIMIT')
        marker = self.read_exact(1)
        line = self.line()
        if marker in (b'+', b'-'):
            require(marker == b'+', 'REDIS_ERROR')
            return line
        require(re.fullmatch(rb'-?[0-9]{1,19}', line) is not None, 'RESP_INVALID')
        number = int(line)
        if marker == b':':
            require(-(2**63) <= number < 2**63, 'RESP_INVALID')
            return number
        if marker == b'$':
            require(0 <= number <= 65536, 'RESP_LIMIT')
            value = self.read_exact(number)
            require(self.read_exact(2) == b'\r\n', 'RESP_INVALID')
            return value
        require(marker == b'*' and 0 <= number <= 4096, 'RESP_INVALID')
        return [self.response(depth + 1) for _ in range(number)]

    def command(self, *parts):
        require(parts and parts[0] in ['SCAN', 'TYPE', 'GET', 'PTTL', 'LLEN', 'SCARD', 'ZCARD', 'HLEN'], 'COMMAND_REJECTED')
        if parts[0] == 'SCAN':
            require(len(parts) == 4 and re.fullmatch(r'[0-9]{1,20}', parts[1]) is not None
                    and parts[2:] == ('COUNT', '128'), 'COMMAND_REJECTED')
        else:
            require(len(parts) == 2, 'COMMAND_REJECTED')
            role, kind = classify_key(parts[1], load_contract()['redis'])
            if parts[0] == 'GET':
                require(role == 'id', 'COMMAND_REJECTED')
            elif parts[0] == 'PTTL':
                require(role == 'stalled-check', 'COMMAND_REJECTED')
            elif parts[0] != 'TYPE':
                require({'LLEN':'list', 'SCARD':'set', 'ZCARD':'zset', 'HLEN':'hash'}[parts[0]] == kind,
                        'COMMAND_REJECTED')
        chunks = [b'*' + str(len(parts)).encode() + b'\r\n']
        for part in parts:
            value = part.encode('utf-8')
            chunks.extend([b'$' + str(len(value)).encode() + b'\r\n', value, b'\r\n'])
        data = b''.join(chunks)
        require(self.writer.write(data) == len(data), 'RESP_WRITE_FAILED')
        self.writer.flush()
        return self.response()


def collect_redis(reader, writer):
    """Bounded whole-DB SCAN -> classify -> TYPE -> length/existence only.

    No MATCH filter hides alien prefixes. SCAN may duplicate keys; dedupe before
    type/length queries. A concurrent disappearance, cursor cycle, wrong type,
    unknown key or missing reply rejects the entire observation. Cross-scan
    consistency still requires a separately enforced writer barrier.
    """
    contract = load_contract()['redis']
    wire = RespWire(reader, writer)
    cursor, cursors, keys = '0', set(), set()
    for _ in range(128):
        result = wire.command('SCAN', cursor, 'COUNT', '128')
        require(type(result) is list and len(result) == 2 and type(result[0]) is bytes
                and type(result[1]) is list, 'SCAN_REJECTED')
        require(re.fullmatch(rb'[0-9]{1,20}', result[0]) is not None, 'SCAN_REJECTED')
        cursor = result[0].decode('ascii')
        for raw in result[1]:
            require(type(raw) is bytes and len(raw) <= 512, 'REDIS_KEY_REJECTED')
            try:
                key = raw.decode('utf-8', errors='strict')
            except UnicodeError:
                raise AdmissionError('REDIS_KEY_REJECTED') from None
            classify_key(key, contract)
            keys.add(key)
            require(len(keys) <= 4096, 'REDIS_SCAN_LIMIT')
        if cursor == '0':
            break
        require(cursor not in cursors, 'SCAN_CYCLE')
        cursors.add(cursor)
    else:
        raise AdmissionError('REDIS_SCAN_LIMIT')
    records = {}
    for key in sorted(keys):
        role, kind = classify_key(key, contract)
        require(wire.command('TYPE', key) == kind.encode(), 'REDIS_TYPE_REJECTED')
        if role == 'id':
            value = wire.command('GET', key)
            require(type(value) is bytes and re.fullmatch(rb'[0-9]{1,19}', value) is not None, 'REDIS_ID_REJECTED')
            records[key] = {'type': kind, 'value': value.decode('ascii')}
        elif role == 'stalled-check':
            records[key] = {'type': kind, 'ttlMs': wire.command('PTTL', key)}
        elif kind == 'string':
            records[key] = {'type': kind, 'count': 1}
        else:
            command = {'list': 'LLEN', 'set': 'SCARD', 'zset': 'ZCARD', 'hash': 'HLEN'}[kind]
            records[key] = {'type': kind, 'count': wire.command(command, key)}
            require(unsigned_count(records[key]['count']) > 0, 'REDIS_KEY_DISAPPEARED')
    observed = {'database': 0, 'scanComplete': True, 'keys': records}
    validate_redis(observed, contract)
    return observed


def emit_postgres_sql():
    """Fixed SQL for each of the TWO fresh databases; no executor is provided.

    The final SELECT emits one db observation object. A future reviewed executor
    must use ON_ERROR_STOP/one JSON row, preserve real JSON ints/bools, authenticate
    the exact isolated stores, and reject stderr/nonzero/truncation. It must not
    translate errors or missing rows to zero. This text has NOT run on PostgreSQL.
    """
    c = load_contract()
    tables = ', '.join("'" + t + "'" for t in sorted(c['catalog']))
    origin = c['postgres']['origin']  # fixed source profile, never CLI input
    counts = []
    for status in c['postgres']['backgroundStatuses']:
        counts.append((f'background.{status}', f"(SELECT count(*) FROM public.background_jobs WHERE status = '{status}')"))
    for prefix, table, column in [('uploads', 'file_uploads', 'convertedStatus'),
                                  ('webhooks', 'webhooks_events', 'status'),
                                  ('previews', 'object_preview', 'previewStatus')]:
        for status in range(4):
            counts.append((f'{prefix}.{status}', f'(SELECT count(*) FROM public.{table} WHERE "{column}" = {status})'))
        condition = f'"{column}" IS NULL OR "{column}" NOT IN (0,1,2,3)'
        if prefix == 'previews':
            condition += ' OR attempts < 0'
        if prefix == 'uploads':
            condition += ' OR "uploadDate" IS NULL OR "convertedLastUpdate" IS NULL'
        counts.append((prefix + '.invalid', f'(SELECT count(*) FROM public.{table} WHERE {condition})'))
    # CASE protects timestamp/interval casts from malformed JSON. IS DISTINCT FROM
    # catches nulls as well as wrong type/version; token contents never leave DB.
    counts.extend([
        ('background.invalid', """(SELECT count(*) FROM public.background_jobs WHERE
          "jobType" IS DISTINCT FROM 'fileImport'
          OR "originServerUrl" IS DISTINCT FROM 'ORIGIN'
          OR status NOT IN ('queued','processing','succeeded','failed')
          OR jsonb_typeof(payload) IS DISTINCT FROM 'object'
          OR payload ->> 'jobType' IS DISTINCT FROM 'fileImport'
          OR payload -> 'payloadVersion' IS DISTINCT FROM '1'::jsonb
          OR payload ->> 'fileType' IS DISTINCT FROM 'ifc'
          OR payload ->> 'serverUrl' IS DISTINCT FROM 'ORIGIN'
          OR NOT (payload ?& ARRAY['projectId','modelId','token','blobId','fileName','timeOutSeconds'])
          OR EXISTS (SELECT 1 FROM unnest(ARRAY['projectId','modelId','token','blobId','fileName']) field
            WHERE jsonb_typeof(payload -> field) IS DISTINCT FROM 'string')
          OR CASE WHEN jsonb_typeof(payload) = 'object' THEN EXISTS (
            SELECT 1 FROM jsonb_object_keys(payload) field WHERE field NOT IN
              ('payloadVersion','jobType','serverUrl','projectId','modelId','token','blobId','fileType','fileName','timeOutSeconds'))
            ELSE true END
          OR CASE WHEN jsonb_typeof(payload -> 'timeOutSeconds') = 'number'
              AND (payload ->> 'timeOutSeconds') ~ '^[0-9]{1,8}$'
              THEN (payload ->> 'timeOutSeconds')::bigint NOT BETWEEN 1 AND 86400
              ELSE true END
          OR attempt < 0 OR "maxAttempt" < 1 OR attempt > "maxAttempt"
          OR "createdAt" > "updatedAt")""".replace('ORIGIN', origin)),
        ('background.stale', """(SELECT count(*) FROM public.background_jobs WHERE status = 'processing'
          AND CASE WHEN jsonb_typeof(payload -> 'timeOutSeconds') = 'number'
            AND (payload ->> 'timeOutSeconds') ~ '^[0-9]{1,8}$'
            THEN "updatedAt" < CURRENT_TIMESTAMP - (payload ->> 'timeOutSeconds')::bigint * interval '1 second'
            ELSE true END)"""),
        ('background.exhausted', """(SELECT count(*) FROM public.background_jobs WHERE
          (status = 'queued' AND attempt >= "maxAttempt") OR
          (status IN ('queued','processing') AND "remainingComputeBudgetSeconds" <= 0))"""),
        ('uploads.incomplete', '(SELECT count(*) FROM public.file_uploads WHERE "uploadComplete" IS DISTINCT FROM true)')])
    count_sql = ',\n'.join("  '" + key + "', " + expression for key, expression in counts)
    return """-- SOURCE_DERIVED_NOT_PG_EXECUTED. No credentials or payloads emitted.
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '5000ms';
SET LOCAL lock_timeout = '1000ms';
SET LOCAL search_path = pg_catalog, public;
WITH relations AS (
 SELECT r.oid, r.relname, r.relkind, r.relpersistence, r.relrowsecurity,
        r.relforcerowsecurity, r.relispartition
 FROM pg_catalog.pg_class r JOIN pg_catalog.pg_namespace n ON n.oid=r.relnamespace
 WHERE n.nspname='public' AND r.relname IN (TABLES)
), physical AS (
 SELECT r.relname, jsonb_build_object(
 'kind', r.relkind, 'persistence', r.relpersistence,
 'rowSecurity', r.relrowsecurity, 'forceRowSecurity', r.relforcerowsecurity,
 'partition', r.relispartition,
 'columns', (SELECT jsonb_object_agg(a.attname, jsonb_build_object(
    'type', pg_catalog.format_type(a.atttypid,a.atttypmod), 'notNull', a.attnotnull,
    'default', pg_catalog.pg_get_expr(d.adbin,d.adrelid),
    'identity', a.attidentity, 'generated', a.attgenerated,
    'collationDefault', a.attcollation=ty.typcollation))
    FROM pg_catalog.pg_attribute a JOIN pg_catalog.pg_type ty ON ty.oid=a.atttypid
    LEFT JOIN pg_catalog.pg_attrdef d
      ON d.adrelid=a.attrelid AND d.adnum=a.attnum
    WHERE a.attrelid=r.oid AND a.attnum>0 AND NOT a.attisdropped),
 'indexes', (SELECT coalesce(jsonb_agg(j.obj ORDER BY j.name),'[]'::jsonb) FROM (
    SELECT ic.relname AS name, jsonb_build_object(
      'name',ic.relname, 'columns',(SELECT jsonb_agg(a.attname ORDER BY k.ord)
        FROM unnest(i.indkey) WITH ORDINALITY k(num,ord)
        LEFT JOIN pg_catalog.pg_attribute a ON a.attrelid=i.indrelid AND a.attnum=k.num),
      'unique',i.indisunique,'primary',i.indisprimary,'method',am.amname,
      'predicate',pg_catalog.pg_get_expr(i.indpred,i.indrelid),
      'expression',pg_catalog.pg_get_expr(i.indexprs,i.indrelid),
      'valid',i.indisvalid,'ready',i.indisready,
      'definition',pg_catalog.pg_get_indexdef(i.indexrelid)) AS obj
    FROM pg_catalog.pg_index i JOIN pg_catalog.pg_class ic ON ic.oid=i.indexrelid
    JOIN pg_catalog.pg_am am ON am.oid=ic.relam WHERE i.indrelid=r.oid) j),
 'constraints', (SELECT coalesce(jsonb_object_agg(co.conname,
      pg_catalog.pg_get_constraintdef(co.oid)), '{}'::jsonb)
      FROM pg_catalog.pg_constraint co WHERE co.conrelid=r.oid AND co.contype <> 'n'),
 'triggers', (SELECT coalesce(jsonb_agg(pg_catalog.pg_get_triggerdef(t.oid) ORDER BY t.tgname),'[]'::jsonb)
      FROM pg_catalog.pg_trigger t WHERE t.tgrelid=r.oid AND NOT t.tgisinternal),
 'policies', (SELECT coalesce(jsonb_agg(p.polname ORDER BY p.polname),'[]'::jsonb)
      FROM pg_catalog.pg_policy p WHERE p.polrelid=r.oid)
 ) AS obj FROM relations r
)
SELECT jsonb_build_object(
 'catalog',(SELECT coalesce(jsonb_object_agg(relname,obj),'{}'::jsonb) FROM physical),
 'migrations',(SELECT coalesce(jsonb_agg(name ORDER BY name),'[]'::jsonb) FROM public.knex_migrations),
 'migrationLock',(SELECT CASE WHEN count(*)=1 THEN max(is_locked) ELSE -1 END FROM public.knex_migrations_lock),
 'counts',jsonb_build_object(
COUNTS
 )) AS observation;
COMMIT;
""".replace('TABLES', tables).replace('COUNTS', count_sql)


def admit_snapshot(observation):
    # Snapshot caller-owned mutable containers and enforce the same byte ceiling
    # as the CLI. Invalid direct Python values get fixed errors, not tracebacks.
    try:
        raw = canonical(observation).encode('utf-8')
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise AdmissionError('OBSERVATION_REJECTED') from None
    observation = strict_json(raw)
    c = load_contract()
    exact_keys(observation, ['schemaVersion', 'profile', 'postgres', 'redis'])
    require(type(observation['schemaVersion']) is int and observation['schemaVersion'] == 1)
    expected_profile = {'canonicalOrigin': c['postgres']['origin'], 'redisDb': 0,
                        'nextGenFileImporter': True, 'multiregion': False}
    require(canonical(observation['profile']) == canonical(expected_profile), 'PROFILE_REJECTED')
    exact_keys(observation['postgres'], ['application', 'fileimport'])
    expected_names = sorted(m['name'] for m in c['migrations'])
    drained = True
    for db in observation['postgres'].values():
        exact_keys(db, ['catalog', 'migrations', 'migrationLock', 'counts'])
        require(type(db['migrationLock']) is int and db['migrationLock'] == 0, 'MIGRATION_LOCKED')
        names = db['migrations']
        require(type(names) is list and all(type(n) is str for n in names), 'MIGRATIONS_REJECTED')
        require(sorted(names) == expected_names, 'MIGRATIONS_REJECTED')
        # Canonical JSON comparison distinguishes bool/int; observed catalogs never
        # become expectations. No normalization that erases predicates/defaults.
        require(canonical(db['catalog']) == canonical(c['catalog']), 'CATALOG_REJECTED')
        exact_keys(db['counts'], count_keys())
        for key, value in db['counts'].items():
            unsigned_count(value)
            if key.endswith('.invalid'):
                require(value == 0, 'UNKNOWN_POSTGRES_JOB')
            if key not in ['background.succeeded', 'uploads.2', 'webhooks.2', 'previews.2']:
                drained = drained and value == 0
    redis_drained = validate_redis(observation['redis'], c['redis'])
    drained = drained and redis_drained
    normalized = json.loads(canonical(observation))
    for db in normalized['postgres'].values():
        db['migrations'].sort()
    for key, record in normalized['redis']['keys'].items():
        if key.endswith(':stalled-check'):
            record['ttlMs'] = 'validated-live-lease'
    return {'schemaMatched': True, 'drained': drained,
            'fingerprint': hashlib.sha256(canonical({'contract': c, 'observation': normalized}).encode()).hexdigest() if drained else None,
            'runtimeQualified': False, 'evidenceClass': 'OFFLINE_UNTRUSTED_OBSERVATION'}


def strict_json(raw):
    require(type(raw) is bytes and 0 < len(raw) <= 1024 * 1024, 'INPUT_LIMIT')
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'DUPLICATE_JSON_KEY')
            result[key] = value
        return result
    def nonfinite(_):
        raise AdmissionError('JSON_REJECTED')
    try:
        return json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=pairs,
                          parse_constant=nonfinite)
    except (ValueError, UnicodeError, RecursionError):
        raise AdmissionError('JSON_REJECTED') from None


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        require(args in [['sample'], ['emit-sql']], 'MODE_REJECTED')
        if args == ['emit-sql']:
            print(emit_postgres_sql(), end='')
            return 0
        # stdin is an OFFLINE observation only. No native collector is selected
        # by environment variables or silently substituted fixtures.
        require(not sys.stdin.isatty(), 'NATIVE_PROBE_TRANSPORT_UNIMPLEMENTED')
        raw = sys.stdin.buffer.read(1024 * 1024 + 1)
        require(raw != b'', 'NATIVE_PROBE_TRANSPORT_UNIMPLEMENTED')
        result = admit_snapshot(strict_json(raw))
        print(canonical(result))
        return 0 if result['drained'] else 3
    except (AdmissionError, OSError, ValueError, TypeError, RecursionError) as error:
        code = ('NATIVE_PROBE_TRANSPORT_UNIMPLEMENTED'
                if isinstance(error, AdmissionError) and str(error) == 'NATIVE_PROBE_TRANSPORT_UNIMPLEMENTED'
                else 'QUEUE_ADMISSION_REJECTED')
        print(canonical({'schemaMatched': False, 'drained': False, 'fingerprint': None,
                         'runtimeQualified': False, 'evidenceClass': 'OFFLINE_UNTRUSTED_OBSERVATION',
                         'error': code}))
        return 2


if __name__ == '__main__':
    sys.exit(main())

