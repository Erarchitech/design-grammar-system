"""Offline-exercised object stream adapter, NOT a native MinIO client.

Trusted provider methods must enforce approved synthetic bucket/identity/timeouts,
source quiescence and target emptiness. All metadata unsupported by this explicit
qualification subset MUST be rejected by provider (never silently omitted).
Supported: never-versioned bucket, no policy/lifecycle/encryption/lock/replication/
notifications; per-object HTTP metadata, user metadata and tags. Version history,
ACLs, legal hold/retention, checksums other than own SHA256, timestamps, multipart
state and server-managed encryption are NOT qualified. Native provider unavailable.
No completion marker/CLI; external expected manifest hash needs authenticated
provenance. Trusted local FS, private parent/DACL and no concurrent hostile writes.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import uuid
try:
    from .recovery_n8n import _root, _regular
except ImportError:
    from recovery_n8n import _root, _regular

MAX_OBJECTS = 4096
MAX_BYTES = 64 * 1024 ** 3
MAX_MANIFEST = 1024 * 1024
BUCKET = {'versioning': 'never-enabled', 'policy': None, 'lifecycle': None,
          'encryption': None, 'objectLock': False, 'replication': None, 'notifications': None}
HTTP_FIELDS = {'contentType', 'cacheControl', 'contentDisposition', 'contentEncoding', 'contentLanguage'}


class ObjectError(ValueError):
    pass


def _require(value):
    if not value:
        raise ObjectError('object operation rejected')


def _metadata(value):
    _require(type(value) is dict and set(value) == HTTP_FIELDS | {'userMetadata', 'tags'})
    _require(all(type(value[k]) is str and len(value[k]) <= 8192 and '\x00' not in value[k]
                 for k in HTTP_FIELDS))
    for name in ('userMetadata', 'tags'):
        pairs = value[name]
        _require(type(pairs) is dict and len(pairs) <= 64)
        _require(all(type(k) is str and type(v) is str and 0 < len(k) <= 1024
                     and len(v) <= 8192 and '\x00' not in k + v for k, v in pairs.items()))


def iter_s3_keys(client, bucket, *, max_pages=4097):
    """S3 ListObjectsV2 pagination seam; not a native qualified MinIO provider.

    Caller MUST pin a credential-scoped client to the approved endpoint/bucket,
    bounded SDK response parsing/retries/socket timeouts and immutable snapshot.
    No SDK import/network configuration or credentials are handled here. Response
    consistency cannot prove native completeness against a faulty server. For
    never-versioned buckets only; provider must check all bucket features first.
    """
    try:
        _require(type(bucket) is str and re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', bucket)
                 and '..' not in bucket and not re.fullmatch(r'\d+\.\d+\.\d+\.\d+', bucket))
        _require(type(max_pages) is int and 1 <= max_pages <= MAX_OBJECTS + 1)
        token = None
        tokens, keys = set(), set()
        for _ in range(max_pages):
            request = {'Bucket': bucket, 'MaxKeys': 1000}
            if token is not None:
                request['ContinuationToken'] = token
            page = client.list_objects_v2(**request)
            _require(type(page) is dict and type(page.get('IsTruncated')) is bool
                     and not page.get('CommonPrefixes') and not page.get('EncodingType'))
            if 'Name' in page:
                _require(page['Name'] == bucket)
            _require(page.get('Prefix', '') == '' and page.get('Delimiter', '') == ''
                     and page.get('StartAfter', '') == '')
            _require(page.get('ContinuationToken', token) == token)
            objects = page.get('Contents', [])
            _require(type(objects) is list and len(objects) <= 1000)
            _require(type(page.get('KeyCount')) is int and page['KeyCount'] == len(objects))
            next_token = page.get('NextContinuationToken')
            if page['IsTruncated']:
                _require(type(next_token) is str and 0 < len(next_token) <= 8192
                         and '\x00' not in next_token and next_token not in tokens)
                tokens.add(next_token)
            else:
                _require(next_token is None)
            batch = []
            for entry in objects:
                _require(type(entry) is dict)
                key = entry.get('Key')
                _require(type(key) is str and 0 < len(key.encode('utf-8')) <= 1024
                         and '\x00' not in key and key not in keys and len(keys) < MAX_OBJECTS)
                keys.add(key)
                batch.append(key)
            yield from batch
            if not page['IsTruncated']:
                return
            token = next_token
        raise ObjectError('object operation rejected')
    except Exception:
        raise ObjectError('object operation rejected') from None


def _keys(provider):
    # Iterative bounded enumeration; providers MUST implement full pagination.
    names = []
    for key in provider.list_objects():
        _require(type(key) is str and 0 < len(key.encode('utf-8')) <= 1024 and '\x00' not in key
                 and key not in names and len(names) < MAX_OBJECTS)
        names.append(key)
    return sorted(names)


def _new(path):
    path = Path(os.path.abspath(path))
    _root(path.parent)
    _require(re.fullmatch('[A-Za-z0-9][A-Za-z0-9_-]{0,100}', path.name)
             and not os.path.lexists(path))
    return path


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result)
        result[key] = value
    return result


def _bucket(provider):
    value = provider.describe_bucket()
    _require(type(value) is dict and value == BUCKET and value['objectLock'] is False)


def export_objects(provider, destination, *, attest):
    stage = None
    try:
        destination = _new(destination)
        _require(callable(attest) and attest({'operation': 'object-export-unversioned'}) is True)
        _bucket(provider)
        keys = _keys(provider)
        candidate = destination.parent / ('objects-stage-' + uuid.uuid4().hex)
        candidate.mkdir(mode=0o700)
        stage = candidate
        records, total = [], 0
        for index, key in enumerate(keys):
            info, stream = provider.read_object(key)
            try:
                _require(type(info) is dict and set(info) == {'bytes', 'metadata'}
                         and type(info['bytes']) is int and 0 <= info['bytes'] <= MAX_BYTES)
                _metadata(info['metadata'])
                # Freeze provider-owned nested dicts before stream reads/next calls.
                info = {'bytes': info['bytes'], 'metadata': {
                    **{field: info['metadata'][field] for field in HTTP_FIELDS},
                    'userMetadata': dict(info['metadata']['userMetadata']),
                    'tags': dict(info['metadata']['tags'])}}
                total += info['bytes']
                _require(total <= MAX_BYTES)
                name = f'{index:04d}.object'
                fd = os.open(stage / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
                with os.fdopen(fd, 'wb') as output:
                    digest, count = hashlib.sha256(), 0
                    while chunk := stream.read(65536):
                        _require(type(chunk) is bytes and len(chunk) <= 65536)
                        count += len(chunk)
                        _require(count <= info['bytes'])
                        output.write(chunk)
                        digest.update(chunk)
                    _require(count == info['bytes'])
                    output.flush()
                    os.fsync(output.fileno())
                records.append({'key': key, 'file': name, **info, 'sha256': digest.hexdigest()})
            finally:
                stream.close()
        _require(_keys(provider) == keys)
        _bucket(provider)
        manifest = {'schemaVersion': 1, 'kind': 'unversioned-object-subset',
                    'bucket': BUCKET, 'objects': records}
        raw = json.dumps(manifest, sort_keys=True, separators=(',', ':')).encode()
        _require(len(raw) <= MAX_MANIFEST)
        fd = os.open(stage / 'objects.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
        with os.fdopen(fd, 'wb') as output:
            output.write(raw)
            output.flush()
            os.fsync(output.fileno())
        _require(not os.path.lexists(destination))
        os.rename(stage, destination)
        stage = None
        return {'manifestSha256': hashlib.sha256(raw).hexdigest(),
                'nativeRecoveryProven': False}
    except Exception:
        raise ObjectError('object operation rejected') from None
    finally:
        if stage is not None and stage.exists():
            try:
                shutil.rmtree(stage)
            except Exception:
                raise ObjectError('object operation rejected') from None


def _verify(package, expected):
    _require(type(expected) is str and re.fullmatch('[0-9a-f]{64}', expected))
    marker = package / 'objects.json'
    _require(_regular(marker).st_size <= MAX_MANIFEST)
    raw = marker.read_bytes()
    _require(hashlib.sha256(raw).hexdigest() == expected)
    manifest = json.loads(raw, object_pairs_hook=_pairs)
    _require(type(manifest) is dict and set(manifest) == {'schemaVersion', 'kind', 'bucket', 'objects'})
    _require(type(manifest['schemaVersion']) is int and manifest['schemaVersion'] == 1
             and manifest['kind'] == 'unversioned-object-subset' and manifest['bucket'] == BUCKET
             and manifest['bucket']['objectLock'] is False)
    records = manifest['objects']
    _require(type(records) is list and len(records) <= MAX_OBJECTS)
    keys, names, total = set(), {'objects.json'}, 0
    for i, record in enumerate(records):
        _require(type(record) is dict and set(record) == {'key', 'file', 'bytes', 'metadata', 'sha256'})
        key = record['key']
        _require(type(key) is str and 0 < len(key.encode('utf-8')) <= 1024
                 and '\x00' not in key and key not in keys)
        keys.add(key)
        _require(record['file'] == f'{i:04d}.object')
        names.add(record['file'])
        _metadata(record['metadata'])
        _require(type(record['bytes']) is int and 0 <= record['bytes'] <= MAX_BYTES
                 and type(record['sha256']) is str and re.fullmatch('[0-9a-f]{64}', record['sha256']))
        total += record['bytes']
        _require(total <= MAX_BYTES)
        path = package / record['file']
        _require(_regular(path).st_size == record['bytes'])
        digest, count = hashlib.sha256(), 0
        with path.open('rb') as stream:
            while chunk := stream.read(65536):
                count += len(chunk)
                _require(count <= record['bytes'])
                digest.update(chunk)
        _require(count == record['bytes'] and digest.hexdigest() == record['sha256'])
    _require({p.name for p in package.iterdir()} == names)
    return raw, records


def restore_objects(package, provider, *, expected_manifest_sha256, attest):
    try:
        package = _root(package)
        raw, records = _verify(package, expected_manifest_sha256)
        _require(callable(attest) and attest({'operation': 'object-restore-unversioned',
                         'manifestSha256': expected_manifest_sha256}) is True)
        _require(_verify(package, expected_manifest_sha256)[0] == raw)
        _bucket(provider)
        _require(_keys(provider) == [])
        for record in records:
            with (package / record['file']).open('rb') as stream:
                provider.put_object(record['key'], stream, record)
        # Read-back byte+metadata verification; provider failures leave partial
        # owned target for the outer runner, NEVER auto-delete an unknown bucket.
        _require(_keys(provider) == sorted(r['key'] for r in records))
        for record in records:
            info, stream = provider.read_object(record['key'])
            try:
                _require(info == {k: record[k] for k in ('bytes', 'metadata')})
                digest, count = hashlib.sha256(), 0
                while chunk := stream.read(65536):
                    _require(type(chunk) is bytes and len(chunk) <= 65536)
                    count += len(chunk)
                    _require(count <= record['bytes'])
                    digest.update(chunk)
                _require(count == record['bytes'] and digest.hexdigest() == record['sha256'])
            finally:
                stream.close()
        return {'status': 'OBJECT_SUBSET_COPIED_NOT_RECOVERY', 'nativeRecoveryProven': False}
    except Exception:
        raise ObjectError('object operation rejected') from None
