"""Bounded single-database Speckle SQL contract; Python runs OUTSIDE PG Alpine.

postgres-sql --directory NEW_PRIVATE_DIR emits fixed SQL, never invokes pg tools.
The trusted outer runner uses contract.json argv with cleared PG environment,
private stdout files, an authenticated dump, pinned PostgreSQL 16.4, and quiesced
writers across BOTH source snapshots and pg_dump. Execute empty.sql on the live
DISPOSABLE destination before restore, with no concurrent connections/writers.
This process cannot prove synthetic-service ownership, quiescence or provenance.
No application seed is invented: app-native seeding needs a separately qualified
Speckle image/source profile. Roles, grants/owners and cluster globals are excluded.
Unknown queues and catalogs are NOT qualified by SQL equality or offline tests.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

# Reuse the sibling's private-file and SigV4 machinery WITHOUT modifying it.
_spec = importlib.util.spec_from_file_location('_speckle_native', Path(__file__).with_name('multistore_native.py'))
native = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(native)
require = native.require

HEADER = r'''\set ON_ERROR_STOP on
SET client_min_messages = warning;
SET search_path = pg_catalog;
SET timezone = 'UTC';
SET datestyle = 'ISO, YMD';
SET intervalstyle = 'postgres';
SET bytea_output = 'hex';
SET extra_float_digits = 3;
SET row_security = off;
SET statement_timeout = '120s';
SET lock_timeout = '5s';
'''
GUARD = r'''
DO $guard$
BEGIN
 IF current_database() <> 'speckle'
    OR current_setting('server_version_num')::integer <> 160004 THEN
   RAISE EXCEPTION 'Speckle recovery identity rejected';
 END IF;
END $guard$;
'''
# Deliberately narrow admission: ordinary heap tables, builtin scalar columns,
# ordinary indexes/constraints and owned or standalone sequences. No user code.
# pg_get_functiondef, pg_get_viewdef and pg_get_triggerdef are NOT used: these
# objects are rejected rather than represented incompletely.
USER_NS = "n.nspname !~ '^pg_' AND n.nspname <> 'information_schema'"
UNSUPPORTED = r'''
 EXISTS (SELECT FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE {ns})
 OR EXISTS (SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE {ns} AND (c.relkind NOT IN ('r','i','S') OR c.relpersistence <> 'p'
              OR c.relrowsecurity OR c.relforcerowsecurity OR c.relispartition
              OR c.reloptions IS NOT NULL OR c.reloftype <> 0))
 OR EXISTS (SELECT FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
            WHERE {ns} AND NOT (t.typtype='c' AND t.typrelid IN
              (SELECT oid FROM pg_class WHERE relkind='r')) AND NOT EXISTS
              (SELECT FROM pg_type base JOIN pg_class bc ON bc.oid=base.typrelid
               WHERE base.typarray=t.oid AND t.typarray=0 AND base.typtype='c' AND bc.relkind='r'))
 OR EXISTS (SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            LEFT JOIN pg_am am ON am.oid=c.relam WHERE {ns} AND
             (c.reltablespace <> 0 OR (c.relkind='r' AND am.amname <> 'heap')))
 OR EXISTS (SELECT FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace WHERE {ns} AND c.relkind='r'
             AND a.attnum>0 AND (a.attcompression<>'' OR a.attoptions IS NOT NULL
                  OR a.attfdwoptions IS NOT NULL OR a.attstattarget<>-1))
 OR EXISTS (SELECT FROM pg_index i JOIN pg_class c ON c.oid=i.indrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace WHERE {ns}
             AND (NOT i.indisvalid OR NOT i.indisready OR i.indcheckxmin))
 OR EXISTS (SELECT FROM pg_range r JOIN pg_type t ON t.oid=r.rngtypid
            JOIN pg_namespace n ON n.oid=t.typnamespace WHERE {ns})
 OR EXISTS (SELECT FROM pg_transform)
 OR EXISTS (SELECT FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
            JOIN pg_namespace n ON n.oid=c.relnamespace JOIN pg_type t ON t.oid=a.atttypid
            WHERE {ns} AND c.relkind='r' AND a.attnum>0 AND
             (a.attisdropped OR a.attgenerated<>'' OR t.typnamespace<>'pg_catalog'::regnamespace
              OR t.typname NOT IN ('bool','int2','int4','int8','text','varchar','bpchar',
                 'numeric','float4','float8','uuid','json','jsonb','bytea','date',
                 'timestamp','timestamptz','time','timetz','interval')))
 OR EXISTS (SELECT FROM pg_trigger WHERE NOT tgisinternal)
 OR EXISTS (SELECT FROM pg_policy) OR EXISTS (SELECT FROM pg_inherits)
 OR EXISTS (SELECT FROM pg_enum)
 OR EXISTS (SELECT FROM pg_extension WHERE extname <> 'plpgsql')
 OR EXISTS (SELECT FROM pg_largeobject_metadata) OR EXISTS (SELECT FROM pg_foreign_server)
 OR EXISTS (SELECT FROM pg_publication) OR EXISTS (SELECT FROM pg_subscription)
 OR EXISTS (SELECT FROM pg_event_trigger)
 OR EXISTS (SELECT FROM pg_collation c JOIN pg_namespace n ON n.oid=c.collnamespace WHERE {ns})
 OR EXISTS (SELECT FROM pg_conversion c JOIN pg_namespace n ON n.oid=c.connamespace WHERE {ns})
 OR EXISTS (SELECT FROM pg_ts_config c JOIN pg_namespace n ON n.oid=c.cfgnamespace WHERE {ns})
 OR EXISTS (SELECT FROM pg_ts_dict c JOIN pg_namespace n ON n.oid=c.dictnamespace WHERE {ns})
 OR EXISTS (SELECT FROM pg_ts_parser c JOIN pg_namespace n ON n.oid=c.prsnamespace WHERE {ns})
 OR EXISTS (SELECT FROM pg_ts_template c JOIN pg_namespace n ON n.oid=c.tmplnamespace WHERE {ns})
 OR EXISTS (SELECT FROM pg_operator c JOIN pg_namespace n ON n.oid=c.oprnamespace WHERE {ns})
 OR EXISTS (SELECT FROM pg_opclass c JOIN pg_namespace n ON n.oid=c.opcnamespace WHERE {ns})
 OR EXISTS (SELECT FROM pg_opfamily c JOIN pg_namespace n ON n.oid=c.opfnamespace WHERE {ns})
 OR EXISTS (SELECT FROM pg_rewrite r JOIN pg_class c ON c.oid=r.ev_class
            JOIN pg_namespace n ON n.oid=c.relnamespace WHERE {ns})
 OR EXISTS (SELECT FROM pg_statistic_ext c JOIN pg_namespace n ON n.oid=c.stxnamespace WHERE {ns})
'''.format(ns=USER_NS)
EMPTY_SQL = HEADER + 'BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;\n' + GUARD + r'''
DO $empty$ BEGIN
 IF ''' + UNSUPPORTED + r'''
 OR EXISTS (SELECT FROM pg_namespace n WHERE n.nspname !~ '^pg_'
             AND n.nspname NOT IN ('public','information_schema'))
 OR EXISTS (SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE ''' + USER_NS + r''')
 OR EXISTS (SELECT FROM pg_default_acl)
 THEN RAISE EXCEPTION 'Destination is not pristine'; END IF;
END $empty$;
SELECT 'PRISTINE_SPECKLE_DESTINATION';
COMMIT;
'''
# Catalog entries contain logical names/definitions only, never transient OIDs.
CATALOG = r'''
SELECT coalesce(jsonb_agg(v ORDER BY v::text COLLATE "C"),'[]'::jsonb) FROM (
 SELECT jsonb_build_object('kind','schema','name',n.nspname) v
 FROM pg_namespace n WHERE ''' + USER_NS + r'''
 UNION ALL
 SELECT jsonb_build_object('kind','table','schema',n.nspname,'name',c.relname,
   'replicaIdentity',c.relreplident,'accessMethod',am.amname,
   'columns',(SELECT jsonb_agg(jsonb_build_object('name',a.attname,'position',a.attnum,
     'type',tn.nspname||'.'||t.typname,'typmod',a.atttypmod,
     'notNull',a.attnotnull,'identity',a.attidentity,
     'collation',CASE WHEN co.oid IS NOT NULL THEN format('%I.%I',cn.nspname,co.collname) END,
     'default',pg_get_expr(d.adbin,d.adrelid,false)) ORDER BY a.attnum)
    FROM pg_attribute a JOIN pg_type t ON t.oid=a.atttypid
    JOIN pg_namespace tn ON tn.oid=t.typnamespace
    LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
    LEFT JOIN pg_collation co ON co.oid=a.attcollation
    LEFT JOIN pg_namespace cn ON cn.oid=co.collnamespace
    WHERE a.attrelid=c.oid AND a.attnum>0),
   'constraints',(SELECT coalesce(jsonb_agg(jsonb_build_object('name',k.conname,
      'definition',pg_get_constraintdef(k.oid,false),'validated',k.convalidated)
      ORDER BY k.conname COLLATE "C"),'[]'::jsonb) FROM pg_constraint k WHERE k.conrelid=c.oid),
   'indexes',(SELECT coalesce(jsonb_agg(jsonb_build_object('name',ic.relname,
      'definition',pg_get_indexdef(i.indexrelid),'valid',i.indisvalid,'ready',i.indisready,
      'clustered',i.indisclustered,'replicaIdentity',i.indisreplident)
      ORDER BY ic.relname COLLATE "C"),'[]'::jsonb)
      FROM pg_index i JOIN pg_class ic ON ic.oid=i.indexrelid WHERE i.indrelid=c.oid))
 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 LEFT JOIN pg_am am ON am.oid=c.relam WHERE ''' + USER_NS + r''' AND c.relkind='r'
 UNION ALL
 SELECT jsonb_build_object('kind','sequence','schema',n.nspname,'name',c.relname,
   'type',format_type(s.seqtypid,NULL),'start',s.seqstart,'increment',s.seqincrement,
   'min',s.seqmin,'max',s.seqmax,'cache',s.seqcache,'cycle',s.seqcycle,
   'ownedBy',(SELECT jsonb_agg(jsonb_build_array(tn.nspname,tc.relname,a.attname,d.deptype)
      ORDER BY tn.nspname COLLATE "C",tc.relname COLLATE "C",a.attname COLLATE "C")
      FROM pg_depend d JOIN pg_class tc ON tc.oid=d.refobjid
      JOIN pg_namespace tn ON tn.oid=tc.relnamespace
      JOIN pg_attribute a ON a.attrelid=tc.oid AND a.attnum=d.refobjsubid
      WHERE d.classid='pg_class'::regclass AND d.objid=c.oid
        AND d.refclassid='pg_class'::regclass AND d.deptype IN ('a','i')))
 FROM pg_sequence s JOIN pg_class c ON c.oid=s.seqrelid
 JOIN pg_namespace n ON n.oid=c.relnamespace WHERE ''' + USER_NS + r'''
) logical_catalog
'''
SNAPSHOT_SQL = HEADER + 'BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;\n' + GUARD + r'''
DO $admit$
DECLARE r record; count_rows bigint; bytes bigint; total_rows bigint:=0; total_bytes bigint:=0;
BEGIN
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname=current_user AND
     (rolsuper OR rolbypassrls)) OR NOT pg_has_role(current_user,'pg_read_all_data','USAGE')
 THEN RAISE EXCEPTION 'Complete read privileges required'; END IF;
 IF ''' + UNSUPPORTED + r''' THEN RAISE EXCEPTION 'Unsupported database feature'; END IF;
 IF (SELECT count(*) FROM (SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE ''' + USER_NS + r''' LIMIT 257) q)>256
 OR (SELECT count(*) FROM pg_namespace n WHERE ''' + USER_NS + r''')>32
 OR (SELECT count(*) FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
     JOIN pg_namespace n ON n.oid=c.relnamespace WHERE ''' + USER_NS + r''' AND a.attnum>0)>4096
 THEN RAISE EXCEPTION 'Catalog bound exceeded'; END IF;
 FOR r IN SELECT n.nspname,c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
          WHERE ''' + USER_NS + r''' AND c.relkind='r' LOOP
   EXECUTE format('SELECT count(*), coalesce(sum(octet_length(row_to_json(t)::text)),0)
      FROM (SELECT * FROM ONLY %I.%I LIMIT 100001) t',r.nspname,r.relname)
      INTO count_rows,bytes;
   total_rows:=total_rows+count_rows; total_bytes:=total_bytes+bytes;
   IF total_rows>100000 OR total_bytes>33554432 THEN RAISE EXCEPTION 'Row bound exceeded'; END IF;
 END LOOP;
END $admit$;
-- User functions/views/triggers are rejected above, not silently omitted:
-- pg_get_functiondef / pg_get_viewdef / pg_get_triggerdef are not a reviewed
-- substitute for their full dependencies and execution semantics.
-- psql executes a generated SELECT only. Every relation identifier uses %I.
WITH tables AS (
 SELECT string_agg(format($q$SELECT jsonb_build_object('schema',%L,'name',%L,
   'rowCount',count(*),'rowsSha256',encode(sha256(convert_to(coalesce(
     string_agg(encode(sha256(convert_to(row_to_json(t)::text,'UTF8')),'hex'),''
       ORDER BY encode(sha256(convert_to(row_to_json(t)::text,'UTF8')),'hex') COLLATE "C"),''),'UTF8')),'hex')) v
   FROM (SELECT * FROM ONLY %I.%I LIMIT 100001) t$q$,n.nspname,c.relname,n.nspname,c.relname),
   ' UNION ALL ' ORDER BY n.nspname COLLATE "C",c.relname COLLATE "C") sql
 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
 WHERE ''' + USER_NS + r''' AND c.relkind='r'
), sequences AS (
 SELECT string_agg(format($q$SELECT jsonb_build_object('schema',%L,'name',%L,
     'lastValue',last_value,'isCalled',is_called) v FROM %I.%I$q$,
     n.nspname,c.relname,n.nspname,c.relname),' UNION ALL '
     ORDER BY n.nspname COLLATE "C",c.relname COLLATE "C") sql
 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE ''' + USER_NS + r''' AND c.relkind='S'
)
SELECT format($q$SELECT jsonb_build_object('schema',1,'database','speckle','serverVersion',160004,
 'catalog',%L::jsonb,'tables',(SELECT coalesce(jsonb_agg(v ORDER BY v->>'schema' COLLATE "C",v->>'name' COLLATE "C"),'[]'::jsonb) FROM (%s) t),
 'sequences',(SELECT coalesce(jsonb_agg(v ORDER BY v->>'schema' COLLATE "C",v->>'name' COLLATE "C"),'[]'::jsonb) FROM (%s) s),
 'migrations',(SELECT coalesce(jsonb_agg(v ORDER BY v->>'schema' COLLATE "C",v->>'name' COLLATE "C"),'[]'::jsonb) FROM (%s) m
 WHERE v->>'name' IN ('knex_migrations','knex_migrations_lock')))$q$,
 (''' + CATALOG + r'''),coalesce(tables.sql,'SELECT NULL::jsonb v WHERE false'),
 coalesce(sequences.sql,'SELECT NULL::jsonb v WHERE false'),coalesce(tables.sql,'SELECT NULL::jsonb v WHERE false'))
FROM tables,sequences
\gexec
COMMIT;
'''


def report(verified=False):
    return dict(verified=verified, nativeRecoveryProven=False,
                appNativeSeedProven=False, queueCatalogQualified=False)


def postgres_sql(path):
    directory = Path(os.path.abspath(path))
    native.checked_directory(directory.parent)
    directory.mkdir(mode=0o700)
    files = {'empty.sql': EMPTY_SQL.encode(), 'snapshot.sql': SNAPSHOT_SQL.encode()}
    contract = dict(schema=1, database='speckle', serverVersion=160004,
                    psqlArgv=[*native.PG_PSQL_ARGV, '--dbname=speckle'],
                    dumpArgv=[*native.PG_DUMP_ARGV, '--dbname=speckle'],
                    restoreArgv=[*native.PG_RESTORE_ARGV[:-1], '--dbname=speckle'],
                    connectionEnvironment=native.PG_ENV,
                    filesSha256={k: hashlib.sha256(v).hexdigest() for k, v in files.items()},
                    sqlExecutedOnPostgres=False, nativeRecoveryProven=False,
                    appNativeSeedBlocker='APP_NATIVE_SEED_UNQUALIFIED',
                    exclusions=['owners, ACLs, roles and cluster globals',
                                'user functions, views, triggers, custom types, extensions except plpgsql, RLS, partitions, foreign objects, replication, large objects, custom text search/operators/collations'],
                    requirements=['fixture.json is independent expected data, not derived from a snapshot',
                                  'trusted host must bound private psql output to 4 MiB; quiesce all writers and DDL including sequence users',
                                  'row serialization can allocate a single large value before the 32 MiB aggregate check; statement timeout is not an OS memory quota',
                                  'source-pinned application catalog and native SQL execution remain unqualified'],
                    executionOrder=['empty.sql: destination BEFORE pg_restore',
                                    'snapshot.sql: quiesced source BEFORE pg_dump',
                                    'pg_dump: source', 'pg_restore: admitted destination',
                                    'snapshot.sql: restored destination',
                                    'verify-postgres: independent fixture and both snapshots'])
    for name, data in files.items():
        native.write_new(directory / name, data)
    native.write_new(directory / 'contract.json', native.encode_json(contract))
    return report(True)


def document(path):
    # Regular private files only, bounded before JSON parsing; no symlink traversal.
    import stat
    p = Path(os.path.abspath(path))
    native.checked_directory(p.parent)
    info = p.lstat()
    require(stat.S_ISREG(info.st_mode) and not p.is_symlink() and info.st_size <= 4194304)
    with p.open('rb') as stream:
        raw = stream.read(4194305)
    require(len(raw) <= 4194304)
    return native.json_document(raw)


def integer(v, low=-(2**63), high=2**63-1):
    require(type(v) is int and low <= v <= high)


def text(v, maximum=8192):
    require(type(v) is str and 0 < len(v.encode('utf-8')) <= maximum and '\x00' not in v)


def keys(v, names):
    require(type(v) is dict and set(v) == set(names.split()))


def array(v, maximum):
    require(type(v) is list and len(v) <= maximum)


def named(items, maximum=256):
    array(items, maximum)
    result = {}
    for item in items:
        require(type(item) is dict)
        text(item.get('schema'), 63)
        text(item.get('name'), 63)
        key = (item['schema'], item['name'])
        require(key not in result)
        result[key] = item
    return result


def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def catalog_check(items):
    array(items, 544)
    schemas, tables, sequences = set(), {}, {}
    for c in items:
        require(type(c) is dict)
        kind = c.get('kind')
        text(c.get('name'), 63)
        if kind == 'schema':
            keys(c, 'kind name')
            require(c['name'] not in schemas and not c['name'].startswith('pg_')
                    and c['name'] != 'information_schema')
            schemas.add(c['name'])
            continue
        require(kind in ('table', 'sequence'))
        text(c.get('schema'), 63)
        key = (c['schema'], c['name'])
        target = tables if kind == 'table' else sequences
        require(key not in target)
        target[key] = c
        if kind == 'table':
            keys(c, 'kind schema name replicaIdentity accessMethod columns constraints indexes')
            require(c['accessMethod'] == 'heap' and c['replicaIdentity'] in ('d','n','f','i'))
            array(c['columns'], 1600)
            require(c['columns'])
            names = set()
            allowed = {'bool','int2','int4','int8','text','varchar','bpchar','numeric','float4',
                       'float8','uuid','json','jsonb','bytea','date','timestamp','timestamptz',
                       'time','timetz','interval'}
            for position, col in enumerate(c['columns'], 1):
                keys(col, 'name position type typmod notNull identity collation default')
                text(col['name'], 63)
                require(col['name'] not in names)
                names.add(col['name'])
                integer(col['position'], position, position)
                integer(col['typmod'], -1, 2**31-1)
                require(type(col['notNull']) is bool and col['identity'] in ('','a','d'))
                require(col['type'] in {'pg_catalog.' + t for t in allowed})
                for field in ('collation','default'):
                    if col[field] is not None:
                        text(col[field])
            for group in ('constraints', 'indexes'):
                array(c[group], 256)
                seen = set()
                for obj in c[group]:
                    fields = 'name definition validated' if group == 'constraints' else 'name definition valid ready clustered replicaIdentity'
                    keys(obj, fields)
                    text(obj['name'], 63)
                    text(obj['definition'])
                    require(obj['name'] not in seen)
                    seen.add(obj['name'])
                    for field in set(obj) - {'name','definition'}:
                        require(type(obj[field]) is bool)
        else:
            keys(c, 'kind schema name type start increment min max cache cycle ownedBy')
            require(c['type'] in ('smallint','integer','bigint'))
            for field in ('start','increment','min','max','cache'):
                integer(c[field])
            require(c['increment'] != 0 and c['cache'] > 0 and c['min'] <= c['start'] <= c['max']
                    and type(c['cycle']) is bool)
            if c['ownedBy'] is not None:
                array(c['ownedBy'], 1)
                require(len(c['ownedBy']) == 1)
                owner = c['ownedBy'][0]
                array(owner, 4)
                require(len(owner) == 4 and owner[3] in ('a','i'))
                for value in owner[:3]:
                    text(value, 63)
    require(0 < len(schemas) <= 32 and 0 < len(tables) <= 256 and len(sequences) <= 256)
    require(not set(tables).intersection(sequences))
    require(all(k[0] in schemas for k in [*tables, *sequences]))
    require(sum(len(t['columns']) for t in tables.values()) <= 4096)
    for seq in sequences.values():
        if seq['ownedBy']:
            schema, table, column, _ = seq['ownedBy'][0]
            require((schema,table) in tables and column in
                    {c['name'] for c in tables[(schema,table)]['columns']})
    return tables, sequences


def state_check(value, fixture=False):
    keys(value, 'schema catalog tables sequences' if fixture else
         'schema database serverVersion catalog tables sequences migrations')
    integer(value['schema'], 1, 1)
    if not fixture:
        require(value['database'] == 'speckle')
        integer(value['serverVersion'], 160004, 160004)
    catalog_tables, catalog_sequences = catalog_check(value['catalog'])
    tables, sequences = named(value['tables']), named(value['sequences'])
    require(set(tables) == set(catalog_tables) and set(sequences) == set(catalog_sequences))
    total_rows, total_bytes = 0, 0
    digests = {}
    for key, table in tables.items():
        if fixture:
            keys(table, 'schema name rows')
            array(table['rows'], 100000)
            hashes = []
            for row in table['rows']:
                text(row, 33554432)
                # Reject duplicate keys, invalid numbers and non-object rows too.
                parsed = native.json_document(row)
                require(type(parsed) is dict and set(parsed) ==
                        {c['name'] for c in catalog_tables[key]['columns']})
                for col in catalog_tables[key]['columns']:
                    v = parsed[col['name']]
                    if v is None:
                        require(not col['notNull'])
                        continue
                    typ = col['type'].removeprefix('pg_catalog.')
                    if typ in ('int2','int4','int8'):
                        bits = {'int2':16,'int4':32,'int8':64}[typ]
                        integer(v, -(2**(bits-1)), 2**(bits-1)-1)
                    elif typ == 'bool':
                        require(type(v) is bool)
                    elif typ in ('numeric','float4','float8'):
                        from decimal import Decimal
                        require(type(v) in (int, Decimal) or v in ('NaN','Infinity','-Infinity'))
                        require(type(v) is not bool)
                    elif typ not in ('json','jsonb'):
                        require(type(v) is str and '\x00' not in v)
                total_bytes += len(row.encode('utf-8'))
                hashes.append(hashlib.sha256(row.encode('utf-8')).hexdigest())
            digest = hashlib.sha256(''.join(sorted(hashes)).encode('ascii')).hexdigest()
            item = dict(schema=key[0], name=key[1], rowCount=len(hashes), rowsSha256=digest)
        else:
            keys(table, 'schema name rowCount rowsSha256')
            integer(table['rowCount'], 0, 100000)
            import re
            require(type(table['rowsSha256']) is str and re.fullmatch('[0-9a-f]{64}', table['rowsSha256']))
            item = table
        digests[key] = item
        total_rows += item['rowCount']
    require(0 < total_rows <= 100000 and total_bytes <= 33554432)
    migration_keys = {k for k in tables if k[1] in ('knex_migrations','knex_migrations_lock')}
    require({k[1] for k in migration_keys} == {'knex_migrations','knex_migrations_lock'})
    require(all(digests[k]['rowCount'] > 0 for k in migration_keys))
    require(any(k not in migration_keys and digests[k]['rowCount'] > 0 for k in tables))
    if not fixture:
        migrations = named(value['migrations'])
        require(set(migrations) == migration_keys)
        require(canonical(migrations_list(migrations)) == canonical(migrations_list({k: digests[k] for k in migration_keys})))
    for key, seq in sequences.items():
        keys(seq, 'schema name lastValue isCalled')
        integer(seq['lastValue'])
        require(type(seq['isCalled']) is bool and
                catalog_sequences[key]['min'] <= seq['lastValue'] <= catalog_sequences[key]['max'])
    return dict(catalog=sorted(value['catalog'], key=canonical),
                tables=migrations_list(digests), sequences=migrations_list(sequences))


def migrations_list(mapping):
    return [mapping[k] for k in sorted(mapping)]


def verify_postgres(fixture, source, destination):
    paths = [Path(p).resolve(strict=True) for p in (fixture, source, destination)]
    require(len(set(paths)) == 3)
    require(all(not os.path.samefile(paths[a], paths[b]) for a,b in ((0,1),(0,2),(1,2))))
    expected = state_check(document(fixture), True)
    before, after = state_check(document(source)), state_check(document(destination))
    require(canonical(expected) == canonical(before) == canonical(after))
    return report(True)


def prepare_bucket(admitted):
    # Explicit preparation only: never called by export/restore and never deletes.
    require(admitted is True and os.environ.get('RECOVERY_S3_BUCKET') ==
            'dg-recovery-speckle-synthetic')
    s3 = native.S3()
    require(s3.region == 'us-east-1')
    raw, _ = s3.request(absent='NoSuchBucket')
    require(raw is None)  # Existing, forbidden or ambiguous bucket => no PUT.
    raw, _ = s3.request(method='PUT', headers={'x-amz-acl':'private'})
    require(raw == b'')
    return report(True)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise native.NativeError('Speckle operation rejected')


def main(argv=None):
    try:
        parser = Parser(allow_abbrev=False, add_help=False)
        modes = parser.add_subparsers(dest='mode', required=True)
        emit = modes.add_parser('postgres-sql', add_help=False, allow_abbrev=False)
        emit.add_argument('--directory', required=True)
        verify = modes.add_parser('verify-postgres', add_help=False, allow_abbrev=False)
        for name in ('fixture', 'source', 'destination'):
            verify.add_argument('--' + name, required=True)
        bucket = modes.add_parser('prepare-bucket', add_help=False, allow_abbrev=False)
        bucket.add_argument('--admit-synthetic-absent-bucket', action='store_true')
        args = parser.parse_args(argv)
        if args.mode == 'postgres-sql':
            result = postgres_sql(args.directory)
        elif args.mode == 'prepare-bucket':
            result = prepare_bucket(args.admit_synthetic_absent_bucket)
        else:
            result = verify_postgres(args.fixture, args.source, args.destination)
        code = 0
    except Exception:
        result, code = report(), 1
    print(json.dumps(result, sort_keys=True))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
