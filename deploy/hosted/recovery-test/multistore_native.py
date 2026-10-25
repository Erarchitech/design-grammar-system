"""Native synthetic MinIO adapter, Python stdlib only; never starts a service.

Run in the already-approved data-service Python image, NOT PostgreSQL Alpine
(which has no Python). Credentials/endpoints are environment-only. The trusted
outer runner must enforce owned isolated synthetic services, writer quiescence,
pinned image identities, private exchange mount/DACL and total invocation timeout.
Checks below cannot prove ownership, snapshot isolation or exporter authenticity.
All output retains nativeRecoveryProven=false until independent target acceptance.

S3 subset: a complete never-versioned bucket, no policy/lifecycle/encryption/lock/
replication/notification/bucket tags, no multipart or historical versions. Bytes,
HTTP metadata, x-amz-meta and tags are preserved. ACLs must be default PRIVATE;
S3 timestamps, ETag identity, checksums, storage class transitions are not restored.
Export fails closed on unsupported state. Source is never deleted. A failed restore
may leave its disposable target partially populated; no automatic remote deletion.
Trusted private local filesystem, no concurrent same-user mutation; bounded in-
memory object buffers are intentional (16 MiB/object, 64 MiB total, 256 objects).

Callable CLI (in data-service, /opt/recovery mounted read-only):
  python -B /opt/recovery/multistore_native.py seed-objects
  python -B /opt/recovery/multistore_native.py export-objects --directory /exchange/objects
  python -B /opt/recovery/multistore_native.py manifest --directory /exchange/objects
  python -B /opt/recovery/multistore_native.py restore-objects --directory /exchange/objects
  python -B /opt/recovery/multistore_native.py verify-objects --directory /exchange/objects
  python -B /opt/recovery/multistore_native.py postgres-sql --directory /exchange/pg-sql
  python -B /opt/recovery/multistore_native.py verify-postgres --source /exchange/pg-source.json --target /exchange/pg-target.json
S3 env: RECOVERY_S3_ENDPOINT, RECOVERY_S3_ACCESS_KEY, RECOVERY_S3_SECRET_KEY,
RECOVERY_S3_BUCKET; optional RECOVERY_S3_REGION=us-east-1,
RECOVERY_S3_SESSION_TOKEN, RECOVERY_S3_ALLOW_HTTP=1 (isolated synthetic network).
No dotenv/config/credential discovery. No proxy, redirects, retries or deletion.
Buckets must preexist; seed/restore demand empty targets; restore requires a
DIFFERENT bucket NAME even on separate endpoints. Export/SQL directory must not
exist and its parent must be private (0700 POSIX, trusted runner DACL on Windows).
Each invocation emits exactly one JSON object, keys verified (bool), objectCount
(int), bytes (int), nativeRecoveryProven (always false); exit 0 success, 1 reject.
Errors emit fixed false/0 values, no stderr/path/key/URL/exception text. CLI has
no help/raw-output mode. Export writes objects/0000.bin ... and manifest.json
LAST; incomplete private output may remain on failure. Hashes are integrity, not
provenance; trusted outer archive authenticates manifest and data together.

PostgreSQL: postgres-sql emits seed.sql, empty.sql, snapshot.sql, catalog.sql and
contract.json. Execute SQL by stdin in source/destination PostgreSQL 16.4 using
/usr/local/bin/psql -X --no-password -qAt -v ON_ERROR_STOP=1 (no Python there).
Fixed database is postgres. Pass PGHOST/PGPORT/PGDATABASE/PGUSER/PGPASSWORD only
through the runner's cleared private environment. Seed SOURCE only; empty.sql
checks DESTINATION before restore. Dump SOURCE to private /exchange/pg.dump:
/usr/local/bin/pg_dump --format=custom --no-password --no-owner --no-privileges
Restore trusted authenticated dump into prechecked empty DESTINATION via stdin:
/usr/local/bin/pg_restore --exit-on-error --single-transaction --no-password --no-owner --no-privileges --dbname=postgres
Use snapshot.sql stdout as separate private source/target JSON files (do not
combine seed stdout, which includes setval). verify-postgres requires exact
fixture row/sequence values plus source/target equality of catalog projections.
It does NOT execute pg tools or claim SQL runtime qualification offline. This is
synthetic single-database recovery, not owner/ACL/role/global/production recovery.
Both stores still require the trusted runner's independent native target evidence.
"""
import argparse
import datetime
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import stat
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ERROR = 'native recovery operation rejected'
MAX_OBJECTS = 256
MAX_OBJECT = 16 * 1024 * 1024
MAX_TOTAL = 64 * 1024 * 1024
MAX_XML = 1024 * 1024
HTTP_FIELDS = ('content-type', 'cache-control', 'content-disposition', 'content-encoding', 'content-language', 'expires')
FIXTURES = (
    ('native/empty.bin', b'', {'content-type': 'application/octet-stream', 'x-amz-meta-fixture': 'empty'}),
    ('native/model + %.bin', bytes(range(256)) * 8, {'content-type': 'application/octet-stream', 'cache-control': 'private, max-age=0', 'x-amz-meta-fixture': 'binary'}),
    ('native/unicode-\u03bb.json', b'{"synthetic":true,"revision":1}\n', {'content-type': 'application/json', 'content-disposition': 'attachment; filename="fixture.json"', 'content-language': 'en', 'x-amz-meta-fixture': 'json'}),
)


class NativeError(ValueError):
    pass


def require(condition):
    if not condition:
        raise NativeError(ERROR)


def encode_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def pairs(items):
    out = {}
    for k, v in items:
        require(k not in out)
        out[k] = v
    return out


def xml(data, root=None):
    require(len(data) <= MAX_XML and b'<!' not in data)
    node = ET.fromstring(data)
    for item in node.iter():
        item.tag = item.tag.rsplit('}', 1)[-1]
    require(root is None or node.tag == root)
    return node


def single(node, name, default=None):
    found = node.findall(name)
    require(len(found) <= 1)
    return (found[0].text or '') if found else default


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise NativeError(ERROR)


class S3:
    def __init__(self):
        endpoint = os.environ['RECOVERY_S3_ENDPOINT']
        parsed = urllib.parse.urlsplit(endpoint)
        require(parsed.scheme in ('http', 'https') and parsed.hostname and not parsed.username
                and not parsed.password and parsed.path in ('', '/') and not parsed.query
                and not parsed.fragment and (parsed.scheme == 'https' or os.environ.get('RECOVERY_S3_ALLOW_HTTP') == '1'))
        require(parsed.port is None or 0 < parsed.port <= 65535)
        self.endpoint = endpoint.rstrip('/')
        self.host = parsed.netloc
        self.bucket = os.environ['RECOVERY_S3_BUCKET']
        require(re.fullmatch(r'[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', self.bucket)
                and '..' not in self.bucket and not re.fullmatch(r'[0-9.]+', self.bucket))
        self.access = os.environ['RECOVERY_S3_ACCESS_KEY']
        self.secret = os.environ['RECOVERY_S3_SECRET_KEY']
        self.region = os.environ.get('RECOVERY_S3_REGION', 'us-east-1')
        require(re.fullmatch('[A-Za-z0-9_-]{1,128}', self.access)
                and 0 < len(self.secret) <= 4096 and not any(c in self.secret for c in '\r\n\x00')
                and re.fullmatch('[a-z0-9-]{1,64}', self.region))
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, method='GET', key=None, query=(), body=b'', headers=None, absent=None, limit=MAX_XML):
        require(type(body) is bytes and len(body) <= MAX_OBJECT)
        if key is not None:
            require(type(key) is str and 0 < len(key.encode('utf-8')) <= 1024
                    and not any(ord(c) < 32 or ord(c) == 127 for c in key))
        path = '/' + self.bucket + (('/' + urllib.parse.quote(key, safe='/-_.~')) if key is not None else '')
        quoted = lambda v: urllib.parse.quote(v, safe='-_.~')
        canonical_query = '&'.join(sorted(quoted(k) + '=' + quoted(v) for k, v in query))
        now = datetime.datetime.now(datetime.timezone.utc)
        stamp, day = now.strftime('%Y%m%dT%H%M%SZ'), now.strftime('%Y%m%d')
        digest = hashlib.sha256(body).hexdigest()
        hdr = {'host': self.host, 'x-amz-date': stamp, 'x-amz-content-sha256': digest}
        hdr.update(headers or {})
        token = os.environ.get('RECOVERY_S3_SESSION_TOKEN')
        if token:
            hdr['x-amz-security-token'] = token
        require(all(re.fullmatch('[a-z0-9-]+', k) and type(v) is str and len(v) <= 8192
                    and all(32 <= ord(c) <= 126 for c in v) for k, v in hdr.items()))
        signed = ';'.join(sorted(hdr))
        canonical_headers = ''.join(k + ':' + ' '.join(hdr[k].split()) + '\n' for k in sorted(hdr))
        canonical = '\n'.join((method, path, canonical_query, canonical_headers, signed, digest))
        scope = day + '/' + self.region + '/s3/aws4_request'
        text = 'AWS4-HMAC-SHA256\n' + stamp + '\n' + scope + '\n' + hashlib.sha256(canonical.encode()).hexdigest()
        signing = ('AWS4' + self.secret).encode()
        for value in (day, self.region, 's3', 'aws4_request'):
            signing = hmac.new(signing, value.encode(), hashlib.sha256).digest()
        signature = hmac.new(signing, text.encode(), hashlib.sha256).hexdigest()
        hdr['authorization'] = 'AWS4-HMAC-SHA256 Credential=' + self.access + '/' + scope + ', SignedHeaders=' + signed + ', Signature=' + signature
        url = self.endpoint + path + (('?' + canonical_query) if canonical_query else '')
        req = urllib.request.Request(url, data=body if method == 'PUT' else None, headers=hdr, method=method)
        try:
            response = self.opener.open(req, timeout=10)
        except urllib.error.HTTPError as error:
            with error:
                raw = error.read(MAX_XML + 1)
                require(error.code == 404 and absent is not None)
                require(single(xml(raw, 'Error'), 'Code') == absent)
            return None, {}
        with response:
            require(response.status == 200)
            raw = response.read(limit + 1)
            require(len(raw) <= limit)
            values = {}
            for k in response.headers:
                require(k.lower() not in values)
                values[k.lower()] = response.headers[k]
            require(int(values.get('content-length', '-1')) == len(raw))
            return raw, values

    def private_acl(self, key=None):
        raw, _ = self.request(key=key, query=(('acl', ''),))
        node = xml(raw, 'AccessControlPolicy')
        require({n.tag for n in node} == {'Owner', 'AccessControlList'} and len(node) == 2)
        owner = node.find('Owner')
        identity = single(owner, 'ID')
        grants = node.find('AccessControlList')
        require(identity and len(grants) == 1 and grants[0].tag == 'Grant')
        grant = grants[0]
        grantee = grant.find('Grantee')
        require(len(grant) == 2 and single(grant, 'Permission') == 'FULL_CONTROL'
                and grantee is not None and len(grantee) in (1, 2)
                and {n.tag for n in grantee} <= {'ID', 'DisplayName'}
                and single(grantee, 'ID') == identity)

    def create_bucket(self):
        """Create ONE new bucket; an existing bucket (HTTP 409) fails closed, untouched.

        MinIO/us-east-1 body-less PUT only; no LocationConstraint, ACL or policy is set.
        The new bucket must then pass the same private/never-versioned checks as any restore target.
        """
        # Probe first: some stores (AWS us-east-1) answer 200 to a PUT on an existing bucket.
        raw, _ = self.request(query=(('list-type', '2'), ('max-keys', '1')), absent='NoSuchBucket')
        require(raw is None)
        raw, _ = self.request(method='PUT')
        require(raw == b'')
        self.bucket_check()
        require(self.inventory() == {})

    def bucket_check(self):
        self.private_acl()
        raw, _ = self.request(query=(('versioning', ''),))
        require(len(xml(raw, 'VersioningConfiguration')) == 0)
        absent = {'policy': 'NoSuchBucketPolicy', 'lifecycle': 'NoSuchLifecycleConfiguration',
                  'encryption': 'ServerSideEncryptionConfigurationNotFoundError',
                  'object-lock': 'ObjectLockConfigurationNotFoundError',
                  'replication': 'ReplicationConfigurationNotFoundError', 'tagging': 'NoSuchTagSet'}
        for feature, code in absent.items():
            raw, _ = self.request(query=((feature, ''),), absent=code)
            require(raw is None)
        raw, _ = self.request(query=(('notification', ''),))
        require(len(xml(raw, 'NotificationConfiguration')) == 0)
        raw, _ = self.request(query=(('uploads', ''),))
        node = xml(raw, 'ListMultipartUploadsResult')
        require(single(node, 'Bucket') == self.bucket and single(node, 'IsTruncated') == 'false'
                and not node.findall('Upload') and not node.findall('CommonPrefixes'))
        raw, _ = self.request(query=(('versions', ''),))
        node = xml(raw, 'ListVersionsResult')
        require(single(node, 'Name') == self.bucket and single(node, 'IsTruncated') == 'false'
                and not node.findall('DeleteMarker') and not node.findall('CommonPrefixes')
                and single(node, 'Prefix', '') == '' and single(node, 'Delimiter', '') == ''
                and single(node, 'KeyMarker', '') == '' and single(node, 'VersionIdMarker', '') == '')
        versions = {}
        # S3 lists current never-versioned objects as VersionId=null. Rejecting
        # every Version incorrectly rejects ordinary populated MinIO buckets.
        for item in node.findall('Version'):
            key, size, etag = single(item, 'Key'), single(item, 'Size'), single(item, 'ETag')
            require(single(item, 'VersionId') == 'null' and single(item, 'IsLatest') == 'true'
                    and type(key) is str and key not in versions and len(versions) < MAX_OBJECTS
                    and type(size) is str and re.fullmatch('[0-9]+', size) and int(size) <= MAX_OBJECT
                    and type(etag) is str and single(item, 'StorageClass', 'STANDARD') == 'STANDARD')
            versions[key] = {'bytes': int(size), 'etag': etag}
        require(versions == self.inventory())

    def inventory(self):
        token, tokens, entries = None, set(), {}
        for _ in range(MAX_OBJECTS + 1):
            query = [('list-type', '2'), ('max-keys', '1000')]
            if token is not None:
                query.append(('continuation-token', token))
            raw, _ = self.request(query=query)
            node = xml(raw, 'ListBucketResult')
            require(single(node, 'Name') == self.bucket and single(node, 'Prefix', '') == ''
                    and single(node, 'Delimiter', '') == '' and single(node, 'StartAfter', '') == ''
                    and not node.findall('CommonPrefixes') and single(node, 'EncodingType') is None
                    and single(node, 'ContinuationToken') == token)
            contents = node.findall('Contents')
            require(single(node, 'KeyCount') == str(len(contents)) and len(contents) <= 1000)
            for item in contents:
                key, size, etag = single(item, 'Key'), single(item, 'Size'), single(item, 'ETag')
                require(type(key) is str and 0 < len(key.encode()) <= 1024 and key not in entries
                        and type(size) is str and re.fullmatch('[0-9]+', size) and int(size) <= MAX_OBJECT
                        and type(etag) is str and len(etag) <= 256 and len(entries) < MAX_OBJECTS)
                require(single(item, 'StorageClass', 'STANDARD') == 'STANDARD')
                entries[key] = {'bytes': int(size), 'etag': etag}
                require(sum(v['bytes'] for v in entries.values()) <= MAX_TOTAL)
            truncated = single(node, 'IsTruncated')
            next_token = single(node, 'NextContinuationToken')
            require(truncated in ('true', 'false'))
            if truncated == 'false':
                require(next_token is None)
                return entries
            require(type(next_token) is str and 0 < len(next_token) <= 8192 and next_token not in tokens)
            tokens.add(next_token)
            token = next_token
        raise NativeError(ERROR)

    def read(self, key, info):
        raw, headers = self.request(key=key, limit=min(MAX_OBJECT, info['bytes']))
        require(len(raw) == info['bytes'] and headers.get('etag') == info['etag'])
        require(not any(k.startswith(('x-amz-server-side-encryption', 'x-amz-object-lock', 'x-amz-restore', 'x-amz-website-redirect')) for k in headers)
                and headers.get('x-amz-version-id', 'null') == 'null'
                and headers.get('x-amz-storage-class', 'STANDARD') == 'STANDARD')
        self.private_acl(key)
        metadata = {k: v for k, v in headers.items() if k in HTTP_FIELDS or k.startswith('x-amz-meta-')}
        return raw, metadata

    def tags(self, key):
        raw, _ = self.request(key=key, query=(('tagging', ''),))
        node = xml(raw, 'Tagging')
        require(len(node) == 1 and node[0].tag == 'TagSet' and len(node[0]) <= 10)
        tags = {}
        for item in node[0]:
            require(item.tag == 'Tag' and len(item) == 2)
            k, v = single(item, 'Key'), single(item, 'Value')
            require(type(k) is str and 1 <= len(k) <= 128 and k not in tags
                    and type(v) is str and len(v) <= 256)
            tags[k] = v
        return tags

    def put(self, key, data, metadata, tags=None):
        headers = {**metadata, 'if-none-match': '*'}
        if tags:
            headers['x-amz-tagging'] = urllib.parse.urlencode(sorted(tags.items()), quote_via=urllib.parse.quote)
        self.request('PUT', key, body=data, headers=headers, limit=MAX_XML)


def checked_directory(path):
    path = Path(os.path.abspath(path))
    require(os.name != 'nt' or all(':' not in p for p in path.parts[1:]))
    for parent in (path, *path.parents):
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode) and not stat.S_ISLNK(info.st_mode)
                and not getattr(info, 'st_file_attributes', 0) & 0x400)
    if os.name != 'nt':
        info = path.stat()
        require(info.st_uid == os.geteuid() and info.st_mode & 0o077 == 0)
    return path


def write_new(path, data):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def read_file(path, limit):
    before = path.lstat()
    regular = lambda s: (stat.S_ISREG(s.st_mode) and not stat.S_ISLNK(s.st_mode)
                         and not getattr(s, 'st_file_attributes', 0) & 0x400 and s.st_nlink == 1
                         and 0 <= s.st_size <= limit)
    signature = lambda s: (s.st_dev, s.st_ino, s.st_nlink, s.st_size, s.st_mtime_ns)
    require(regular(before))
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(descriptor, 'rb') as stream:
        require(signature(os.fstat(stream.fileno())) == signature(before))
        data = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    require(len(data) == before.st_size and regular(after) and signature(after) == signature(before)
            and signature(path.lstat()) == signature(before))
    return data


def names(directory, maximum):
    result = set()
    with os.scandir(directory) as entries:
        for item in entries:
            require(len(result) < maximum)
            result.add(item.name)
    return result


def validate_metadata(value):
    require(type(value) is dict and len(value) <= 64)
    for k, v in value.items():
        require(type(k) is str and (k in HTTP_FIELDS or re.fullmatch('x-amz-meta-[a-z0-9_-]{1,128}', k))
                and type(v) is str and len(v) <= 8192 and all(32 <= ord(c) <= 126 for c in v))
    require(sum(len(k) + len(v) for k, v in value.items()) <= 16384)


def load_export(path):
    directory = checked_directory(path)
    require(names(directory, 2) == {'manifest.json', 'objects'})
    manifest = json.loads(read_file(directory / 'manifest.json', MAX_XML), object_pairs_hook=pairs)
    require(type(manifest) is dict and set(manifest) == {'schema', 'sourceBucket', 'bucketProfile', 'entries'}
            and type(manifest['schema']) is int and manifest['schema'] == 1
            and type(manifest['sourceBucket']) is str and re.fullmatch('[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]', manifest['sourceBucket'])
            and manifest['bucketProfile'] == 'never-versioned-private-unconfigured-v1'
            and type(manifest['entries']) is list and len(manifest['entries']) <= MAX_OBJECTS)
    objects = checked_directory(directory / 'objects')
    result, keys, total = [], set(), 0
    for index, entry in enumerate(manifest['entries']):
        require(type(entry) is dict and set(entry) == {'key', 'file', 'bytes', 'sha256', 'metadata', 'tags'}
                and entry['file'] == f'{index:04d}.bin' and type(entry['key']) is str
                and 0 < len(entry['key'].encode()) <= 1024 and entry['key'] not in keys
                and not any(ord(c) < 32 or ord(c) == 127 for c in entry['key'])
                and type(entry['bytes']) is int and 0 <= entry['bytes'] <= MAX_OBJECT
                and type(entry['sha256']) is str and re.fullmatch('[0-9a-f]{64}', entry['sha256']))
        keys.add(entry['key'])
        total += entry['bytes']
        require(total <= MAX_TOTAL)
        validate_metadata(entry['metadata'])
        require(type(entry['tags']) is dict and len(entry['tags']) <= 10
                and all(type(k) is str and 1 <= len(k) <= 128 and type(v) is str and len(v) <= 256
                        for k, v in entry['tags'].items()))
        data = read_file(objects / entry['file'], entry['bytes'])
        require(len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256'])
        result.append((entry, data))
    require(names(objects, MAX_OBJECTS) == {entry['file'] for entry, _ in result})
    return manifest, result


def collect_object(client, key, info):
    data, metadata = client.read(key, info)
    validate_metadata(metadata)
    tags = client.tags(key)
    return data, metadata, tags


def export_objects(client, path):
    directory = Path(os.path.abspath(path))
    checked_directory(directory.parent)
    require(not directory.exists() and not directory.is_symlink())
    client.bucket_check()
    before = client.inventory()
    # Exclusive creation: a failure leaves an incomplete private export without
    # its LAST-written manifest. Never delete an existing exchange or source.
    directory.mkdir(mode=0o700)
    objects = directory / 'objects'
    objects.mkdir(mode=0o700)
    entries = []
    for index, key in enumerate(sorted(before)):
        data, metadata, tags = collect_object(client, key, before[key])
        filename = f'{index:04d}.bin'
        write_new(objects / filename, data)
        entries.append(dict(key=key, file=filename, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), metadata=metadata, tags=tags))
    require(before == client.inventory())
    # Re-read bytes and metadata: ETag alone does not detect metadata/tag changes.
    for entry in entries:
        data, metadata, tags = collect_object(client, entry['key'], before[entry['key']])
        require(hashlib.sha256(data).hexdigest() == entry['sha256'] and metadata == entry['metadata'] and tags == entry['tags'])
    require(before == client.inventory())
    client.bucket_check()
    manifest = dict(schema=1, sourceBucket=client.bucket, bucketProfile='never-versioned-private-unconfigured-v1', entries=entries)
    encoded = encode_json(manifest)
    require(len(encoded) <= MAX_XML)
    write_new(directory / 'manifest.json', encoded)
    load_export(directory)
    return report(len(entries), sum(e['bytes'] for e in entries))


def verify_objects(client, path):
    _, items = load_export(path)
    client.bucket_check()
    before = client.inventory()
    require(set(before) == {entry['key'] for entry, _ in items})
    for entry, expected in items:
        data, metadata, tags = collect_object(client, entry['key'], before[entry['key']])
        require(data == expected and metadata == entry['metadata'] and tags == entry['tags'])
    require(before == client.inventory())
    client.bucket_check()
    return report(len(items), sum(len(data) for _, data in items))


def restore_objects(client, path):
    manifest, items = load_export(path)  # All checksums validated BEFORE any remote write.
    require(manifest['sourceBucket'] != client.bucket)
    client.bucket_check()
    require(client.inventory() == {})
    for entry, data in items:
        client.put(entry['key'], data, entry['metadata'], entry['tags'])
    return verify_objects(client, path)


def report(count, size):
    return {'verified': True, 'objectCount': count, 'bytes': size, 'nativeRecoveryProven': False}


def seed_objects(client):
    client.bucket_check()
    require(client.inventory() == {})
    for key, body, metadata in FIXTURES:
        client.put(key, body, metadata)
    inventory = client.inventory()
    require(set(inventory) == {r[0] for r in FIXTURES})
    for key, body, metadata in FIXTURES:
        require(client.read(key, inventory[key]) == (body, metadata))
    client.bucket_check()
    return report(len(FIXTURES), sum(len(r[1]) for r in FIXTURES))


# PostgreSQL has NO Python runtime in the pinned Alpine image. These fixed SQL
# programs are emitted in the Python image and streamed by the trusted runner to
# /usr/local/bin/psql in postgres:16.4-alpine. Dump/restore argv are data, never a
# callback/attestation or a pretend native execution. PG SQL is not run offline.
PG_PSQL_ARGV = ['/usr/local/bin/psql', '-X', '--no-password', '-qAt', '-v', 'ON_ERROR_STOP=1']
PG_DUMP_ARGV = ['/usr/local/bin/pg_dump', '--format=custom', '--no-password', '--no-owner', '--no-privileges']
PG_RESTORE_ARGV = ['/usr/local/bin/pg_restore', '--exit-on-error', '--single-transaction', '--no-password', '--no-owner', '--no-privileges', '--dbname=postgres']
PG_ENV = ['PGDATABASE', 'PGHOST', 'PGPASSWORD', 'PGPORT', 'PGUSER']
PG_HEADER = r'''\set ON_ERROR_STOP on
SET client_min_messages = warning;
SET search_path = pg_catalog;
'''
PG_GUARD = r'''
DO $guard$
BEGIN
  IF current_setting('server_version_num')::integer <> 160004
     OR current_database() <> 'postgres' THEN
    RAISE EXCEPTION 'native recovery PostgreSQL identity rejected';
  END IF;
END $guard$;
'''
PG_EMPTY_BODY = r'''
DO $empty$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname !~ '^pg_'
             AND nspname NOT IN ('information_schema', 'public'))
     OR EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE n.nspname='public')
     OR EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
                WHERE n.nspname='public')
     OR EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace
                WHERE n.nspname='public')
     OR EXISTS (SELECT 1 FROM pg_extension WHERE extname <> 'plpgsql')
     OR EXISTS (SELECT 1 FROM pg_largeobject_metadata)
     OR EXISTS (SELECT 1 FROM pg_publication)
     OR EXISTS (SELECT 1 FROM pg_subscription)
     OR EXISTS (SELECT 1 FROM pg_event_trigger)
     OR EXISTS (SELECT 1 FROM pg_foreign_server) THEN
    RAISE EXCEPTION 'native recovery requires an empty disposable database';
  END IF;
END $empty$;
'''
PG_SEED_SQL = PG_HEADER + 'BEGIN;\n' + PG_GUARD + PG_EMPTY_BODY + r'''
CREATE SCHEMA recovery_native;
CREATE SEQUENCE recovery_native.item_id_seq AS bigint START WITH 7 INCREMENT BY 3;
CREATE TABLE recovery_native.items (
  id bigint PRIMARY KEY DEFAULT nextval('recovery_native.item_id_seq'::regclass),
  label text NOT NULL UNIQUE,
  height numeric(9,3) CHECK (height >= 0),
  payload jsonb NOT NULL,
  raw bytea NOT NULL,
  labels text[]
);
ALTER SEQUENCE recovery_native.item_id_seq OWNED BY recovery_native.items.id;
CREATE TABLE recovery_native.links (
  id integer PRIMARY KEY,
  item_id bigint NOT NULL,
  note text,
  CONSTRAINT links_item_fkey FOREIGN KEY (item_id) REFERENCES recovery_native.items(id)
);
CREATE INDEX items_payload_label_idx ON recovery_native.items ((payload->>'label'));
CREATE VIEW recovery_native.summary AS
  SELECT id, label, height FROM recovery_native.items WHERE height IS NOT NULL;
COMMENT ON TABLE recovery_native.items IS 'synthetic native recovery fixture';
INSERT INTO recovery_native.items VALUES
 (7, 'alpha', 12.500, '{"label":"A","nested":[1,true,null]}', decode('00ff1020','hex'), ARRAY['x','y']),
 (41, 'beta', NULL, '{"label":"B","nested":[]}', decode('','hex'), ARRAY[]::text[]),
 (99, 'gamma', 0.125, '{"label":"C","nested":["synthetic"]}', decode('deadbeef','hex'), NULL);
INSERT INTO recovery_native.links VALUES (1,7,'first'), (2,41,NULL), (3,7,'repeat');
SELECT setval('recovery_native.item_id_seq',151,true);
COMMIT;
'''
# OID-independent catalog projection: definitions are compared byte-semantically
# across source/target on the exact engine. No nonzero-count shortcut is accepted.
PG_CATALOG_QUERY = r'''
SELECT jsonb_build_object(
 'schemas', (SELECT coalesce(jsonb_agg(nspname ORDER BY nspname),'[]') FROM pg_namespace
              WHERE nspname !~ '^pg_' AND nspname <> 'information_schema'),
 'relations', (SELECT coalesce(jsonb_agg(jsonb_build_object('name',c.relname,'kind',c.relkind,
              'persistence',c.relpersistence,'rls',c.relrowsecurity,'forceRls',c.relforcerowsecurity)
              ORDER BY c.relname),'[]') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
              WHERE n.nspname='recovery_native'),
 'columns', (SELECT coalesce(jsonb_agg(jsonb_build_object('relation',c.relname,'name',a.attname,
              'type',format_type(a.atttypid,a.atttypmod),'notNull',a.attnotnull,
              'default',pg_get_expr(d.adbin,d.adrelid)) ORDER BY c.relname,a.attnum),'[]')
              FROM pg_attribute a JOIN pg_class c ON c.oid=a.attrelid
              JOIN pg_namespace n ON n.oid=c.relnamespace
              LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
              WHERE n.nspname='recovery_native' AND c.relkind IN ('r','v') AND a.attnum>0 AND NOT a.attisdropped),
 'constraints', (SELECT coalesce(jsonb_agg(jsonb_build_object('relation',c.relname,'name',x.conname,
              'kind',x.contype,'definition',pg_get_constraintdef(x.oid,true),'validated',x.convalidated)
              ORDER BY c.relname,x.conname),'[]') FROM pg_constraint x
              JOIN pg_class c ON c.oid=x.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
              WHERE n.nspname='recovery_native'),
 'indexes', (SELECT coalesce(jsonb_agg(jsonb_build_object('name',i.relname,'table',t.relname,
              'definition',pg_get_indexdef(i.oid),'valid',x.indisvalid) ORDER BY i.relname),'[]')
              FROM pg_index x JOIN pg_class i ON i.oid=x.indexrelid
              JOIN pg_class t ON t.oid=x.indrelid JOIN pg_namespace n ON n.oid=t.relnamespace
              WHERE n.nspname='recovery_native'),
 'sequences', (SELECT coalesce(jsonb_agg(jsonb_build_object('name',c.relname,'start',s.seqstart,
              'increment',s.seqincrement,'min',s.seqmin,'max',s.seqmax,'cache',s.seqcache,'cycle',s.seqcycle)
              ORDER BY c.relname),'[]') FROM pg_sequence s JOIN pg_class c ON c.oid=s.seqrelid
              JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='recovery_native'),
 'views', (SELECT coalesce(jsonb_agg(jsonb_build_object('name',c.relname,'definition',pg_get_viewdef(c.oid,true))
              ORDER BY c.relname),'[]') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
              WHERE n.nspname='recovery_native' AND c.relkind='v'),
 'functions', (SELECT coalesce(jsonb_agg(jsonb_build_object('name',p.proname,'definition',pg_get_functiondef(p.oid))
              ORDER BY p.proname),'[]') FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
              WHERE n.nspname='recovery_native'),
 'triggers', (SELECT coalesce(jsonb_agg(jsonb_build_object('relation',c.relname,'name',t.tgname,
              'definition',pg_get_triggerdef(t.oid,true)) ORDER BY c.relname,t.tgname),'[]')
              FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
              JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='recovery_native' AND NOT t.tgisinternal),
 'comments', (SELECT coalesce(jsonb_agg(jsonb_build_object('name',c.relname,'comment',obj_description(c.oid,'pg_class'))
              ORDER BY c.relname),'[]') FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
              WHERE n.nspname='recovery_native' AND obj_description(c.oid,'pg_class') IS NOT NULL)
) AS catalog
'''
PG_SNAPSHOT_SQL = PG_HEADER + 'BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;\n' + PG_GUARD + r'''
-- Fail closed on state outside the fixed fixture: not a general production dump verifier.
DO $scope$
BEGIN
 IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname !~ '^pg_'
            AND nspname NOT IN ('information_schema','public','recovery_native'))
    OR EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public')
    OR EXISTS (SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public')
    OR EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace WHERE n.nspname='public')
    OR EXISTS (SELECT 1 FROM pg_extension WHERE extname <> 'plpgsql')
    OR EXISTS (SELECT 1 FROM pg_largeobject_metadata)
    OR EXISTS (SELECT 1 FROM pg_publication) OR EXISTS (SELECT 1 FROM pg_subscription)
    OR EXISTS (SELECT 1 FROM pg_event_trigger) OR EXISTS (SELECT 1 FROM pg_foreign_server) THEN
   RAISE EXCEPTION 'native recovery fixture scope rejected';
 END IF;
END $scope$;
SELECT jsonb_build_object(
 'schema',1, 'serverVersion',current_setting('server_version_num')::integer,
 'database',current_database(),
 'items',(SELECT jsonb_agg(jsonb_build_object('id',id,'label',label,'height',height,
         'payload',payload,'rawHex',encode(raw,'hex'),'labels',labels) ORDER BY id) FROM recovery_native.items),
 'links',(SELECT jsonb_agg(to_jsonb(l) ORDER BY id) FROM recovery_native.links l),
 'summary',(SELECT jsonb_agg(to_jsonb(v) ORDER BY id) FROM recovery_native.summary v),
 'sequence',(SELECT jsonb_build_object('lastValue',last_value,'isCalled',is_called) FROM recovery_native.item_id_seq),
 'catalog',q.catalog
) FROM (
''' + PG_CATALOG_QUERY + r''') q;
COMMIT;
'''
PG_EMPTY_SQL = PG_HEADER + 'BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;\n' + PG_GUARD + PG_EMPTY_BODY + "SELECT true;\nCOMMIT;\n"
PG_CATALOG_SQL = PG_HEADER + 'BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;\n' + PG_GUARD + PG_CATALOG_QUERY + ';\nCOMMIT;\n'


def postgres_sql(path):
    directory = Path(os.path.abspath(path))
    checked_directory(directory.parent)
    directory.mkdir(mode=0o700)
    contract = dict(schema=1, psqlArgv=PG_PSQL_ARGV, dumpArgv=PG_DUMP_ARGV,
                    restoreArgv=PG_RESTORE_ARGV, connectionEnvironment=PG_ENV,
                    nativeRecoveryProven=False)
    files = {'seed.sql': PG_SEED_SQL.encode(), 'empty.sql': PG_EMPTY_SQL.encode(),
             'snapshot.sql': PG_SNAPSHOT_SQL.encode(), 'catalog.sql': PG_CATALOG_SQL.encode(),
             'contract.json': encode_json(contract)}
    for name, data in files.items():
        write_new(directory / name, data)
    return report(0, sum(len(data) for data in files.values()))


def reject_json_constant(_):
    raise NativeError(ERROR)


def json_document(data):
    from decimal import Decimal
    return json.loads(data, object_pairs_hook=pairs, parse_float=Decimal, parse_constant=reject_json_constant)


def semantic_equal(left, right):
    from decimal import Decimal
    if type(left) is bool or type(right) is bool:
        return type(left) is type(right) and left == right
    if type(left) in (int, Decimal) and type(right) in (int, Decimal):
        return left == right
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return left.keys() == right.keys() and all(semantic_equal(left[k], right[k]) for k in left)
    if type(left) is list:
        return len(left) == len(right) and all(semantic_equal(a, b) for a, b in zip(left, right))
    return left == right


def validate_postgres_snapshot(value):
    from decimal import Decimal
    require(type(value) is dict and set(value) == {'schema', 'serverVersion', 'database', 'items', 'links', 'summary', 'sequence', 'catalog'})
    require(type(value['schema']) is int and value['schema'] == 1 and type(value['serverVersion']) is int
            and value['serverVersion'] == 160004 and value['database'] == 'postgres')
    expected_items = [
        dict(id=7, label='alpha', height=Decimal('12.500'), payload={'label': 'A', 'nested': [1, True, None]}, rawHex='00ff1020', labels=['x', 'y']),
        dict(id=41, label='beta', height=None, payload={'label': 'B', 'nested': []}, rawHex='', labels=[]),
        dict(id=99, label='gamma', height=Decimal('0.125'), payload={'label': 'C', 'nested': ['synthetic']}, rawHex='deadbeef', labels=None),
    ]
    expected_links = [dict(id=1, item_id=7, note='first'), dict(id=2, item_id=41, note=None), dict(id=3, item_id=7, note='repeat')]
    expected_summary = [{k: row[k] for k in ('id', 'label', 'height')} for row in expected_items if row['height'] is not None]
    require(semantic_equal(value['items'], expected_items) and semantic_equal(value['links'], expected_links)
            and semantic_equal(value['summary'], expected_summary)
            and semantic_equal(value['sequence'], {'lastValue': 151, 'isCalled': True}))
    catalog = value['catalog']
    require(type(catalog) is dict and set(catalog) == {'schemas', 'relations', 'columns', 'constraints', 'indexes', 'sequences', 'views', 'functions', 'triggers', 'comments'})
    require(catalog['schemas'] == ['public', 'recovery_native'] and catalog['functions'] == [] and catalog['triggers'] == [])
    require(semantic_equal(catalog['comments'], [{'name': 'items', 'comment': 'synthetic native recovery fixture'}]))
    expected_relations = {'items': 'r', 'links': 'r', 'summary': 'v', 'item_id_seq': 'S',
                          'items_pkey': 'i', 'items_label_key': 'i', 'links_pkey': 'i', 'items_payload_label_idx': 'i'}
    require(type(catalog['relations']) is list and len(catalog['relations']) == len(expected_relations))
    seen = set()
    for rel in catalog['relations']:
        require(type(rel) is dict and set(rel) == {'name', 'kind', 'persistence', 'rls', 'forceRls'}
                and rel['name'] not in seen and rel['name'] in expected_relations
                and rel['kind'] == expected_relations[rel['name']] and rel['persistence'] == 'p'
                and rel['rls'] is False and rel['forceRls'] is False)
        seen.add(rel['name'])
    columns = {('items', c) for c in ('id', 'label', 'height', 'payload', 'raw', 'labels')} | {('links', c) for c in ('id', 'item_id', 'note')} | {('summary', c) for c in ('id', 'label', 'height')}
    require(type(catalog['columns']) is list and len(catalog['columns']) == len(columns))
    seen = set()
    for column in catalog['columns']:
        require(type(column) is dict and set(column) == {'relation', 'name', 'type', 'notNull', 'default'}
                and type(column['type']) is str and 0 < len(column['type']) < 256
                and type(column['notNull']) is bool and (column['default'] is None or type(column['default']) is str))
        identity = (column['relation'], column['name'])
        require(identity in columns and identity not in seen)
        seen.add(identity)
    specs = {
        'constraints': ({'items_pkey', 'items_label_key', 'items_height_check', 'links_pkey', 'links_item_fkey'}, {'relation', 'name', 'kind', 'definition', 'validated'}),
        'indexes': ({'items_pkey', 'items_label_key', 'items_payload_label_idx', 'links_pkey'}, {'name', 'table', 'definition', 'valid'}),
        'views': ({'summary'}, {'name', 'definition'}),
    }
    for group, (expected_names, fields) in specs.items():
        records = catalog[group]
        require(type(records) is list and len(records) == len(expected_names))
        seen = set()
        for record in records:
            require(type(record) is dict and set(record) == fields and record['name'] in expected_names
                    and record['name'] not in seen and type(record['definition']) is str
                    and 0 < len(record['definition']) <= 8192)
            if group == 'indexes':
                require(record['valid'] is True and record['table'] in ('items', 'links'))
            elif group == 'constraints':
                require(record['validated'] is True and record['relation'] in ('items', 'links') and record['kind'] in ('p', 'u', 'c', 'f'))
            seen.add(record['name'])
    require(semantic_equal(catalog['sequences'], [dict(name='item_id_seq', start=7, increment=3, min=1, max=9223372036854775807, cache=1, cycle=False)]))
    return value


def verify_postgres(source, target):
    source, target = Path(os.path.abspath(source)), Path(os.path.abspath(target))
    checked_directory(source.parent)
    checked_directory(target.parent)
    require(source != target and not os.path.samefile(source, target))
    left, right = read_file(source, MAX_XML), read_file(target, MAX_XML)
    # Exact complete row/sequence fixture plus an OID-independent catalog, not
    # nonzero counts. Identical synthetic JSON remains only offline evidence.
    require(semantic_equal(validate_postgres_snapshot(json_document(left)), validate_postgres_snapshot(json_document(right))))
    return report(0, len(left) + len(right))


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise NativeError(ERROR)


def main(argv=None):
    try:
        parser = Parser(allow_abbrev=False, add_help=False)
        parser.add_argument('mode', choices=('seed-objects', 'create-bucket', 'export-objects', 'restore-objects', 'verify-objects', 'manifest', 'postgres-sql', 'verify-postgres'))
        parser.add_argument('--directory')
        parser.add_argument('--source')
        parser.add_argument('--target')
        args = parser.parse_args(argv)
        if args.mode == 'verify-postgres':
            require(args.directory is None and args.source and args.target)
            result = verify_postgres(args.source, args.target)
        else:
            require(args.source is None and args.target is None)
            require((args.mode in ('seed-objects', 'create-bucket')) == (args.directory is None))
            if args.mode == 'seed-objects':
                result = seed_objects(S3())
            elif args.mode == 'create-bucket':
                S3().create_bucket()
                result = report(0, 0)
            elif args.mode == 'postgres-sql':
                result = postgres_sql(args.directory)
            elif args.mode == 'manifest':
                _, items = load_export(args.directory)
                result = report(len(items), sum(len(data) for _, data in items))
            else:
                action = {'export-objects': export_objects, 'restore-objects': restore_objects, 'verify-objects': verify_objects}[args.mode]
                result = action(S3(), args.directory)
        print(json.dumps(result, sort_keys=True))
        return 0
    except Exception:
        print(json.dumps({'verified': False, 'objectCount': 0, 'bytes': 0, 'nativeRecoveryProven': False}, sort_keys=True))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
