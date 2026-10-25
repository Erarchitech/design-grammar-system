"""Strict offline native-wire qualification; no Docker or real service calls."""
import datetime
import hashlib
import hmac
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, unquote, urlsplit
from xml.sax.saxutils import escape

HELPER = Path(__file__).resolve().parents[1] / 'recovery-test' / 'multistore_native.py'
SCRATCH = Path(os.environ.get('TMPDIR', tempfile.gettempdir()))
ACCESS, SECRET = 'synthetic-access', 'synthetic-secret-never-log'
NS = 'http://s3.amazonaws.com/doc/2006-03-01/'


class WireServer:
    """Actual local HTTP server independently verifies the AWS SigV4 wire bytes."""
    def __init__(self):
        self.buckets = {'source-bucket': {}, 'target-bucket': {}}
        self.requests = []
        self.tags = {}
        self.bad_signature = False
        self.feature = None
        self.list_fault = None
        self.corrupt_read = False
        self.public_acl = False
        self.object_sse = False
        self.version_fault = None
        self.on_get = None
        self.reply_mode = None
        self.aws_like_put = False
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, status, body=b'', headers=None):
                self.send_response(status)
                self.send_header('Content-Length', str(len(body)))
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                if self.command != 'HEAD':
                    self.wfile.write(body)

            def xml(self, root, inner=''):
                self.reply(200, f'<{root} xmlns="{NS}">{inner}</{root}>'.encode())

            def handle_s3(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                path = urlsplit(self.path)
                query = parse_qs(path.query, keep_blank_values=True)
                auth = self.headers.get('Authorization', '')
                try:
                    scheme, rest = auth.split(' ', 1)
                    parts = dict(p.strip().split('=', 1) for p in rest.split(','))
                    ident, date, region, service, terminal = parts['Credential'].split('/')
                    signed = parts['SignedHeaders'].split(';')
                    canonical_headers = ''.join(k + ':' + ' '.join(self.headers[k].split()) + '\n' for k in signed)
                    canonical_query = '&'.join(sorted(quote(k, safe='-_.~') + '=' + quote(v, safe='-_.~') for k, vals in query.items() for v in vals))
                    digest = hashlib.sha256(body).hexdigest()
                    canonical = '\n'.join((self.command, path.path, canonical_query, canonical_headers, ';'.join(signed), digest))
                    scope = '/'.join((date, region, service, terminal))
                    stamp = self.headers['X-Amz-Date']
                    text = 'AWS4-HMAC-SHA256\n' + stamp + '\n' + scope + '\n' + hashlib.sha256(canonical.encode()).hexdigest()
                    key = ('AWS4' + SECRET).encode()
                    for value in (date, region, service, terminal):
                        key = hmac.new(key, value.encode(), hashlib.sha256).digest()
                    signature = hmac.new(key, text.encode(), hashlib.sha256).hexdigest()
                    valid = (scheme == 'AWS4-HMAC-SHA256' and ident == ACCESS and service == 's3'
                             and terminal == 'aws4_request' and signature == parts['Signature']
                             and self.headers['X-Amz-Content-Sha256'] == digest)
                except Exception:
                    valid = False
                owner.bad_signature |= not valid
                owner.requests.append((self.command, path.path, query))
                if owner.reply_mode == 'redirect':
                    return self.reply(307, headers={'Location': owner.endpoint + '/should-not-follow'})
                if owner.reply_mode == 'xml-entity':
                    return self.reply(200, b'<!DOCTYPE a [<!ENTITY e "bad">]><AccessControlPolicy>&e;</AccessControlPolicy>')
                if owner.reply_mode == 'oversized':
                    return self.reply(200, b'x' * (1024 * 1024 + 1))
                if not valid:
                    return self.reply(403, b'<Error><Code>SignatureDoesNotMatch</Code></Error>')
                name, _, key = unquote(path.path).lstrip('/').partition('/')
                if self.command == 'PUT' and not key and not query:
                    if name in owner.buckets:
                        if owner.aws_like_put:
                            return self.reply(200)
                        return self.reply(409, b'<Error><Code>BucketAlreadyOwnedByYou</Code></Error>')
                    owner.buckets[name] = {}
                    return self.reply(200)
                if name not in owner.buckets:
                    return self.reply(404, b'<Error><Code>NoSuchBucket</Code></Error>')
                objects = owner.buckets[name]
                if 'acl' in query:
                    grantee = '<URI>http://acs.amazonaws.com/groups/global/AllUsers</URI>' if owner.public_acl else '<ID>synthetic-owner</ID>'
                    return self.xml('AccessControlPolicy', '<Owner><ID>synthetic-owner</ID></Owner><AccessControlList><Grant><Grantee>' + grantee + '</Grantee><Permission>FULL_CONTROL</Permission></Grant></AccessControlList>')
                if not key and query:
                    feature = 'list-type' if 'list-type' in query else next(iter(query))
                    if feature == 'versioning':
                        return self.xml('VersioningConfiguration', '<Status>Suspended</Status>' if owner.feature == feature else '')
                    if feature == 'uploads':
                        return self.xml('ListMultipartUploadsResult', '<Bucket>' + name + '</Bucket><IsTruncated>false</IsTruncated>' + ('<Upload><Key>x</Key></Upload>' if owner.feature == feature else ''))
                    if feature == 'versions':
                        versions = ''.join('<Version><Key>' + escape(k) + '</Key><VersionId>null</VersionId><IsLatest>true</IsLatest><Size>' + str(len(v[0])) + '</Size><ETag>"' + hashlib.md5(v[0]).hexdigest() + '"</ETag></Version>' for k, v in sorted(objects.items()))
                        if owner.version_fault:
                            versions = owner.version_fault(versions)
                        return self.xml('ListVersionsResult', '<Name>' + name + '</Name><IsTruncated>false</IsTruncated>' + ('<DeleteMarker><Key>gone</Key></DeleteMarker>' if owner.feature == feature else versions))
                    if feature == 'notification':
                        return self.xml('NotificationConfiguration', '<TopicConfiguration/>' if owner.feature == feature else '')
                    codes = {'policy': 'NoSuchBucketPolicy', 'lifecycle': 'NoSuchLifecycleConfiguration', 'encryption': 'ServerSideEncryptionConfigurationNotFoundError', 'object-lock': 'ObjectLockConfigurationNotFoundError', 'replication': 'ReplicationConfigurationNotFoundError', 'tagging': 'NoSuchTagSet'}
                    if feature in codes:
                        if owner.feature == feature:
                            return self.xml('Unsupported', '<Enabled>true</Enabled>')
                        return self.reply(404, ('<Error><Code>' + codes[feature] + '</Code></Error>').encode())
                    if feature == 'list-type':
                        keys = sorted(objects)
                        token = query.get('continuation-token', [None])[0]
                        offset = int(token or '0')
                        batch = keys[offset:offset+1]
                        more = offset + len(batch) < len(keys)
                        inner = '<Name>' + name + '</Name><Prefix/>'
                        if token is not None:
                            inner += '<ContinuationToken>' + token + '</ContinuationToken>'
                        inner += '<KeyCount>' + str(len(batch)) + '</KeyCount><IsTruncated>' + str(more).lower() + '</IsTruncated>'
                        for k in batch:
                            b = objects[k][0]
                            inner += '<Contents><Key>' + escape(k) + '</Key><Size>' + str(len(b)) + '</Size><ETag>"' + hashlib.md5(b).hexdigest() + '"</ETag></Contents>'
                        if more:
                            inner += '<NextContinuationToken>' + str(offset + 1) + '</NextContinuationToken>'
                        if owner.list_fault:
                            inner = owner.list_fault(inner, offset)
                        return self.xml('ListBucketResult', inner)
                if self.command == 'PUT':
                    if key in objects:
                        return self.reply(412, b'<Error><Code>PreconditionFailed</Code></Error>')
                    metadata = {k.lower(): v for k, v in self.headers.items() if k.lower().startswith('x-amz-meta-') or k.lower() in {'content-type', 'cache-control', 'content-disposition', 'content-encoding', 'content-language', 'expires'}}
                    owner.tags[(name, key)] = {k: v[0] for k, v in parse_qs(self.headers.get('x-amz-tagging', ''), keep_blank_values=True).items()}
                    objects[key] = (body, metadata)
                    return self.reply(200)
                if key not in objects:
                    return self.reply(404, b'<Error><Code>NoSuchKey</Code></Error>')
                body, headers = objects[key]
                if 'tagging' in query:
                    return self.xml('Tagging', '<TagSet>' + ''.join('<Tag><Key>' + escape(k) + '</Key><Value>' + escape(v) + '</Value></Tag>' for k, v in owner.tags.get((name, key), {}).items()) + '</TagSet>')
                if owner.on_get:
                    owner.on_get(name, key)
                if owner.corrupt_read:
                    body = b'X' * len(body)
                self.reply(200, body, {**headers, **({'x-amz-server-side-encryption': 'AES256'} if owner.object_sse else {}), 'ETag': '"' + hashlib.md5(body).hexdigest() + '"'})

            do_GET = do_PUT = do_HEAD = handle_s3

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.endpoint = 'http://127.0.0.1:' + str(self.server.server_port)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(3)


class NativeWireTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.wire = WireServer()
        self.addCleanup(self.wire.close)

    def cli(self, mode, *args, bucket='source-bucket', extra_env=None):
        self.assertTrue(HELPER.is_file(), 'native container-side helper is missing')
        env = {**os.environ, 'RECOVERY_S3_ENDPOINT': self.wire.endpoint,
               'RECOVERY_S3_ACCESS_KEY': ACCESS, 'RECOVERY_S3_SECRET_KEY': SECRET,
               'RECOVERY_S3_BUCKET': bucket, 'RECOVERY_S3_REGION': 'us-east-1',
               'RECOVERY_S3_ALLOW_HTTP': '1', **(extra_env or {})}
        result = subprocess.run([sys.executable, '-B', str(HELPER), mode, *map(str, args)], env=env,
                                capture_output=True, text=True, timeout=20)
        self.assertNotIn(SECRET, result.stdout + result.stderr)
        self.assertEqual('', result.stderr)
        report = json.loads(result.stdout)
        self.assertIs(report['nativeRecoveryProven'], False)
        return result.returncode, report

    def test_export_restore_complete_inventory_metadata_and_tags(self):
        self.assertEqual(0, self.cli('seed-objects')[0])
        # Not a canned fixture export: arbitrary binary, empty, UTF-8 and path-like keys.
        self.wire.buckets['source-bucket']['../not-a-local-path/☃'] = (
            b'\x00\xffarbitrary\r\n', {'content-type': 'application/x-synthetic',
                                    'cache-control': 'private,  max-age=1',
                                    'x-amz-meta-arbitrary': 'one  two'})
        self.wire.tags[('source-bucket', '../not-a-local-path/☃')] = {'kind': 'synthetic + %', 'λ': '☃'}
        source = dict(self.wire.buckets['source-bucket'])
        directory = self.root / 'export'
        code, result = self.cli('export-objects', '--directory', directory)
        self.assertEqual(0, code)
        self.assertEqual(4, result['objectCount'])
        manifest = json.loads((directory / 'manifest.json').read_bytes())
        self.assertEqual(4, len(manifest['entries']))
        self.assertEqual({'manifest.json', 'objects'}, {p.name for p in directory.iterdir()})
        self.assertEqual(4, len(list((directory / 'objects').iterdir())))
        self.assertEqual(0, self.cli('manifest', '--directory', directory)[0])
        self.assertEqual(0, self.cli('restore-objects', '--directory', directory, bucket='target-bucket')[0])
        self.assertEqual(source, self.wire.buckets['target-bucket'])
        self.assertEqual(self.wire.tags[('source-bucket', '../not-a-local-path/☃')],
                         self.wire.tags[('target-bucket', '../not-a-local-path/☃')])
        self.assertEqual(0, self.cli('verify-objects', '--directory', directory, bucket='target-bucket')[0])
        self.assertEqual(1, self.cli('restore-objects', '--directory', directory, bucket='target-bucket')[0])
        self.assertEqual(source, self.wire.buckets['source-bucket'])
        self.assertFalse(self.wire.bad_signature)
        self.assertFalse(any(method == 'DELETE' for method, _, _ in self.wire.requests))

    def test_create_bucket_makes_one_new_private_bucket_and_never_touches_existing(self):
        code, report = self.cli('create-bucket', bucket='new-destination')
        self.assertEqual(0, code)
        self.assertEqual({}, self.wire.buckets['new-destination'])
        self.assertTrue(report['verified'])
        self.assertEqual(0, self.cli('seed-objects')[0])
        before = dict(self.wire.buckets['source-bucket'])
        code, report = self.cli('create-bucket')
        self.assertEqual(1, code)
        self.assertFalse(report['verified'])
        self.assertEqual(before, self.wire.buckets['source-bucket'])
        self.assertFalse(self.wire.bad_signature)
        self.assertFalse(any(method == 'DELETE' for method, _, _ in self.wire.requests))

    def test_create_bucket_probes_absence_first_and_never_puts_over_an_existing_bucket(self):
        self.assertEqual(0, self.cli('seed-objects')[0])
        before = dict(self.wire.buckets['source-bucket'])
        for aws_like in (False, True):
            self.wire.aws_like_put = aws_like
            del self.wire.requests[:]
            code, report = self.cli('create-bucket')
            self.assertEqual(1, code, aws_like)
            self.assertFalse(report['verified'])
            self.assertEqual([], [r for r in self.wire.requests if r[0] == 'PUT'], aws_like)
            self.assertEqual(before, self.wire.buckets['source-bucket'])

    def test_create_bucket_issues_exactly_one_bucket_put_and_leaves_an_empty_bucket(self):
        code, _ = self.cli('create-bucket', bucket='fresh-destination')
        self.assertEqual(0, code)
        puts = [r for r in self.wire.requests if r[0] == 'PUT']
        self.assertEqual([('PUT', '/fresh-destination', {})], puts)
        self.assertEqual({}, self.wire.buckets['fresh-destination'])

    def test_create_bucket_is_not_rolled_back_when_the_private_check_fails(self):
        self.wire.public_acl = True
        self.assertEqual(1, self.cli('create-bucket', bucket='kept-public')[0])
        self.assertIn('kept-public', self.wire.buckets)  # no DELETE: needs a fresh destination volume
        self.assertFalse(any(method == 'DELETE' for method, _, _ in self.wire.requests))

    def test_create_bucket_fails_closed_when_the_new_bucket_is_not_private(self):
        self.wire.public_acl = True
        code, report = self.cli('create-bucket', bucket='public-destination')
        self.assertEqual(1, code)
        self.assertFalse(report['verified'])

    def test_create_bucket_takes_no_directory_and_restore_still_needs_one(self):
        self.assertEqual(1, self.cli('create-bucket', '--directory', self.root / 'x', bucket='another-new')[0])
        self.assertNotIn('another-new', self.wire.buckets)
        self.assertEqual(1, self.cli('restore-objects', bucket='target-bucket')[0])

    def test_unsupported_bucket_features_fail_closed(self):
        for feature in ('versioning', 'uploads', 'versions', 'policy', 'lifecycle', 'encryption',
                        'object-lock', 'replication', 'tagging', 'notification'):
            with self.subTest(feature=feature):
                self.wire.feature = feature
                directory = self.root / feature
                self.assertEqual(1, self.cli('export-objects', '--directory', directory)[0])
                self.assertFalse(directory.exists())
        self.assertFalse(any(method == 'PUT' for method, _, _ in self.wire.requests))

    def test_incomplete_or_filtered_continuation_inventory_is_rejected(self):
        self.assertEqual(0, self.cli('seed-objects')[0])
        faults = {
            'prefix': lambda s, n: s.replace('<Prefix/>', '<Prefix>native/</Prefix>') if n else s,
            'start-after': lambda s, n: s + '<StartAfter>x</StartAfter>' if n else s,
            'delimiter': lambda s, n: s + '<Delimiter>/</Delimiter>' if n else s,
            'cycle': lambda s, n: s.replace('<NextContinuationToken>2</NextContinuationToken>', '<NextContinuationToken>1</NextContinuationToken>'),
            'truncation': lambda s, n: s.replace('<IsTruncated>true</IsTruncated>', '<IsTruncated>maybe</IsTruncated>'),
            'count': lambda s, n: s.replace('<KeyCount>1</KeyCount>', '<KeyCount>2</KeyCount>'),
            'oversize': lambda s, n: s.replace('<Size>0</Size>', '<Size>16777217</Size>'),
            'duplicate': lambda s, n: s.replace('<Key>native/model + %.bin</Key>', '<Key>native/empty.bin</Key>'),
            'bad-token': lambda s, n: s.replace('<ContinuationToken>1</ContinuationToken>', '<ContinuationToken>9</ContinuationToken>'),
        }
        for name, fault in faults.items():
            with self.subTest(fault=name):
                self.wire.list_fault = fault
                directory = self.root / name
                self.assertEqual(1, self.cli('export-objects', '--directory', directory)[0])
                self.assertFalse(directory.exists())

    def test_checksums_and_exact_file_set_checked_before_restore(self):
        self.assertEqual(0, self.cli('seed-objects')[0])
        directory = self.root / 'export'
        self.assertEqual(0, self.cli('export-objects', '--directory', directory)[0])
        datafile = directory / 'objects' / '0001.bin'
        original = datafile.read_bytes()
        datafile.write_bytes(b'corrupt')
        self.assertEqual(1, self.cli('restore-objects', '--directory', directory, bucket='target-bucket')[0])
        self.assertEqual({}, self.wire.buckets['target-bucket'])
        datafile.write_bytes(original)
        (directory / 'objects' / 'unexpected').write_bytes(b'x')
        self.assertEqual(1, self.cli('manifest', '--directory', directory)[0])
        (directory / 'objects' / 'unexpected').unlink()
        manifest = directory / 'manifest.json'
        saved = manifest.read_bytes()
        manifest.write_bytes(saved.replace(b'"schema":1', b'"schema":1,"schema":1'))
        self.assertEqual(1, self.cli('manifest', '--directory', directory)[0])
        manifest.write_bytes(saved.replace(b'0000.bin', b'../x.bin'))
        self.assertEqual(1, self.cli('manifest', '--directory', directory)[0])
        self.assertEqual({}, self.wire.buckets['target-bucket'])

    def test_existing_export_is_never_clobbered(self):
        directory = self.root / 'existing'
        directory.mkdir()
        marker = directory / 'keep'
        marker.write_bytes(b'keep exactly')
        self.assertEqual(1, self.cli('export-objects', '--directory', directory)[0])
        self.assertEqual(b'keep exactly', marker.read_bytes())
        self.assertEqual([], self.wire.requests)

    def test_verification_detects_extra_keys_byte_metadata_and_tag_drift(self):
        self.assertEqual(0, self.cli('seed-objects')[0])
        directory = self.root / 'export'
        self.assertEqual(0, self.cli('export-objects', '--directory', directory)[0])
        self.assertEqual(0, self.cli('restore-objects', '--directory', directory, bucket='target-bucket')[0])
        target = self.wire.buckets['target-bucket']
        key = sorted(target)[1]
        body, metadata = target[key]
        for changed in ((b'X' * len(body), metadata), (body, {**metadata, 'x-amz-meta-drift': 'yes'})):
            target[key] = changed
            self.assertEqual(1, self.cli('verify-objects', '--directory', directory, bucket='target-bucket')[0])
        target[key] = (body, metadata)
        self.wire.tags[('target-bucket', key)] = {'drift': 'yes'}
        self.assertEqual(1, self.cli('verify-objects', '--directory', directory, bucket='target-bucket')[0])
        self.wire.tags[('target-bucket', key)] = {}
        target['unexpected'] = (b'', {})
        self.assertEqual(1, self.cli('verify-objects', '--directory', directory, bucket='target-bucket')[0])

    def test_manifest_is_offline_and_error_output_is_fixed(self):
        self.assertEqual(0, self.cli('export-objects', '--directory', self.root / 'empty')[0])
        count = len(self.wire.requests)
        self.assertEqual(0, self.cli('manifest', '--directory', self.root / 'empty', extra_env={'RECOVERY_S3_ENDPOINT': 'not-a-url'})[0])
        self.assertEqual(count, len(self.wire.requests))
        code, value = self.cli('bad-mode-' + SECRET)
        self.assertEqual(1, code)
        self.assertEqual({'verified': False, 'objectCount': 0, 'bytes': 0, 'nativeRecoveryProven': False}, value)
        self.assertEqual(1, self.cli('seed-objects', extra_env={'RECOVERY_S3_ALLOW_HTTP': '0'})[0])

    def test_acl_and_per_object_encryption_fail_closed(self):
        self.assertEqual(0, self.cli('seed-objects')[0])
        self.wire.public_acl = True
        directory = self.root / 'public'
        self.assertEqual(1, self.cli('export-objects', '--directory', directory)[0])
        self.assertFalse(directory.exists())
        self.wire.public_acl = False
        self.wire.object_sse = True
        directory = self.root / 'encrypted'
        self.assertEqual(1, self.cli('export-objects', '--directory', directory)[0])
        self.assertFalse((directory / 'manifest.json').exists())

    def test_declared_size_must_match_even_with_valid_empty_checksum(self):
        directory = self.root / 'export'
        self.assertEqual(0, self.cli('seed-objects')[0])
        self.assertEqual(0, self.cli('export-objects', '--directory', directory)[0])
        manifest_path = directory / 'manifest.json'
        manifest = json.loads(manifest_path.read_bytes())
        self.assertEqual(0, manifest['entries'][0]['bytes'])
        manifest['entries'][0]['bytes'] = 1
        manifest_path.write_text(json.dumps(manifest))
        self.assertEqual(1, self.cli('restore-objects', '--directory', directory, bucket='target-bucket')[0])
        self.assertEqual({}, self.wire.buckets['target-bucket'])

    def test_real_hardlink_rejected_before_remote_restore(self):
        directory = self.root / 'export'
        self.assertEqual(0, self.cli('seed-objects')[0])
        self.assertEqual(0, self.cli('export-objects', '--directory', directory)[0])
        os.link(directory / 'objects' / '0000.bin', self.root / 'hardlink')
        self.assertEqual(1, self.cli('restore-objects', '--directory', directory, bucket='target-bucket')[0])
        self.assertEqual({}, self.wire.buckets['target-bucket'])

    def test_object_count_bound_rejects_before_private_export(self):
        self.wire.buckets['source-bucket'] = {f'item-{i:04d}': (b'', {}) for i in range(257)}
        directory = self.root / 'export'
        self.assertEqual(1, self.cli('export-objects', '--directory', directory)[0])
        self.assertFalse(directory.exists())

    def test_null_current_versions_only_no_historical_or_missing_inventory(self):
        self.assertEqual(0, self.cli('seed-objects')[0])
        faults = [lambda s: s.replace('<VersionId>null</VersionId>', '<VersionId>historic-id</VersionId>'),
                  lambda s: s.replace('<IsLatest>true</IsLatest>', '<IsLatest>false</IsLatest>'),
                  lambda s: '', lambda s: s + s]
        for i, fault in enumerate(faults):
            self.wire.version_fault = fault
            path = self.root / f'bad-versions-{i}'
            self.assertEqual(1, self.cli('export-objects', '--directory', path)[0])
            self.assertFalse(path.exists())

    def test_metadata_mutation_during_export_prevents_completion(self):
        self.assertEqual(0, self.cli('seed-objects')[0])
        seen = set()
        def change_once(bucket, key):
            if key not in seen:
                seen.add(key)
                body, metadata = self.wire.buckets[bucket][key]
                self.wire.buckets[bucket][key] = (body, {**metadata, 'x-amz-meta-changed': 'yes'})
        self.wire.on_get = change_once
        directory = self.root / 'unstable'
        self.assertEqual(1, self.cli('export-objects', '--directory', directory)[0])
        self.assertFalse((directory / 'manifest.json').exists())
        self.assertEqual(3, len(self.wire.buckets['source-bucket']))

    def test_no_redirect_entity_or_oversized_response(self):
        for mode in ('redirect', 'xml-entity', 'oversized'):
            self.wire.reply_mode = mode
            count = len(self.wire.requests)
            self.assertEqual(1, self.cli('seed-objects')[0])
            self.assertEqual(count + 1, len(self.wire.requests))
        self.assertEqual({}, self.wire.buckets['source-bucket'])

    def test_real_total_and_object_bounds_on_wire(self):
        native = load_native()
        env = {'RECOVERY_S3_ENDPOINT': self.wire.endpoint, 'RECOVERY_S3_ACCESS_KEY': ACCESS,
               'RECOVERY_S3_SECRET_KEY': SECRET, 'RECOVERY_S3_BUCKET': 'source-bucket', 'RECOVERY_S3_ALLOW_HTTP': '1'}
        from unittest.mock import patch
        with patch.dict(os.environ, env), patch.object(native, 'MAX_TOTAL', 8), patch.object(native, 'MAX_OBJECT', 4):
            self.wire.buckets['source-bucket'] = {'a': (b'1234', {}), 'b': (b'1234', {})}
            self.assertEqual(2, len(native.S3().inventory()))
            self.wire.buckets['source-bucket']['c'] = (b'1', {})
            with self.assertRaises(native.NativeError):
                native.S3().inventory()
            self.wire.buckets['source-bucket'] = {'a': (b'12345', {})}
            with self.assertRaises(native.NativeError):
                native.S3().inventory()

    def test_signed_native_fixture_put_and_readback(self):
        code, report = self.cli('seed-objects')
        self.assertEqual(0, code)
        self.assertEqual(3, report['objectCount'])
        self.assertTrue(report['verified'])
        self.assertFalse(self.wire.bad_signature)
        self.assertEqual(3, len(self.wire.buckets['source-bucket']))
        code, _ = self.cli('seed-objects')
        self.assertEqual(1, code, 'must not reseed or overwrite nonempty bucket')


def load_native():
    spec = importlib.util.spec_from_file_location('native_under_test', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PostgreSQLContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_postgres_snapshot_semantics_not_nonzero_sample(self):
        native = load_native()
        self.assertTrue(callable(getattr(native, 'verify_postgres', None)), 'semantic PostgreSQL comparison missing')
        source = self.synthetic_snapshot()
        src, dst = self.root / 'source.json', self.root / 'target.json'
        src.write_text(json.dumps(source))
        dst.write_text(json.dumps(source))
        self.assertTrue(native.verify_postgres(src, dst)['verified'])
        # Genuine recovered shape is required, not any nonzero row count or a
        # successful command. The synthetic catalog is not native qualification.
        for field, changed in (('items', [source['items'][0]]), ('links', []), ('sequence', {'lastValue': 1, 'isCalled': True}),
                               ('serverVersion', 160003), ('database', 'other')):
            target = {**source, field: changed}
            dst.write_text(json.dumps(target))
            with self.subTest(field=field), self.assertRaises(native.NativeError):
                native.verify_postgres(src, dst)
        changed = json.loads(json.dumps(source))
        changed['catalog']['indexes'][0]['definition'] = 'changed index'
        dst.write_text(json.dumps(changed))
        with self.assertRaises(native.NativeError):
            native.verify_postgres(src, dst)
        source['items'][0]['rawHex'] = 'bad'
        src.write_text(json.dumps(source))
        dst.write_text(json.dumps(source))
        with self.assertRaises(native.NativeError):
            native.verify_postgres(src, dst)

    @staticmethod
    def synthetic_snapshot():
        # Independently spelled expected fixture. Catalog definition text is
        # synthetic transport data, never presented as PostgreSQL execution.
        items = [
            {'id': 7, 'label': 'alpha', 'height': 12.5, 'payload': {'label': 'A', 'nested': [1, True, None]}, 'rawHex': '00ff1020', 'labels': ['x', 'y']},
            {'id': 41, 'label': 'beta', 'height': None, 'payload': {'label': 'B', 'nested': []}, 'rawHex': '', 'labels': []},
            {'id': 99, 'label': 'gamma', 'height': 0.125, 'payload': {'label': 'C', 'nested': ['synthetic']}, 'rawHex': 'deadbeef', 'labels': None}]
        relation_kinds = {'items': 'r', 'links': 'r', 'summary': 'v', 'item_id_seq': 'S',
                          'items_pkey': 'i', 'items_label_key': 'i', 'links_pkey': 'i', 'items_payload_label_idx': 'i'}
        catalog = {
            'schemas': ['public', 'recovery_native'],
            'relations': [{'name': n, 'kind': k, 'persistence': 'p', 'rls': False, 'forceRls': False} for n, k in sorted(relation_kinds.items())],
            'columns': [{'relation': rel, 'name': col, 'type': 'synthetic', 'notNull': False, 'default': None}
                        for rel, cols in [('items', ['id','label','height','payload','raw','labels']), ('links', ['id','item_id','note']), ('summary', ['id','label','height'])] for col in cols],
            'constraints': [{'relation': rel, 'name': n, 'kind': k, 'definition': 'synthetic definition', 'validated': True}
                            for rel, n, k in [('items','items_pkey','p'),('items','items_label_key','u'),('items','items_height_check','c'),('links','links_pkey','p'),('links','links_item_fkey','f')]],
            'indexes': [{'name': n, 'table': 'links' if n == 'links_pkey' else 'items', 'definition': 'synthetic definition', 'valid': True} for n in ('items_label_key','items_payload_label_idx','items_pkey','links_pkey')],
            'sequences': [{'name':'item_id_seq','start':7,'increment':3,'min':1,'max':9223372036854775807,'cache':1,'cycle':False}],
            'views': [{'name':'summary','definition':'synthetic definition'}], 'functions': [], 'triggers': [],
            'comments': [{'name':'items','comment':'synthetic native recovery fixture'}]}
        return {'schema':1,'serverVersion':160004,'database':'postgres','items':items,
                'links':[{'id':1,'item_id':7,'note':'first'},{'id':2,'item_id':41,'note':None},{'id':3,'item_id':7,'note':'repeat'}],
                'summary':[{'id':7,'label':'alpha','height':12.5},{'id':99,'label':'gamma','height':0.125}],
                'sequence':{'lastValue':151,'isCalled':True},'catalog':catalog}

    def test_success_cli_verify_postgres_and_rejection_of_same_file(self):
        source = self.root / 'source.json'
        target = self.root / 'target.json'
        source.write_text(json.dumps(self.synthetic_snapshot()))
        target.write_text(json.dumps(self.synthetic_snapshot()))
        for destination, code in ((target, 0), (source, 1)):
            result = subprocess.run([sys.executable, '-B', str(HELPER), 'verify-postgres', '--source', str(source), '--target', str(destination)], capture_output=True, text=True, timeout=10)
            self.assertEqual(code, result.returncode)
            self.assertEqual('', result.stderr)
            self.assertIs(json.loads(result.stdout)['nativeRecoveryProven'], False)

    def test_native_postgres_sql_bundle_is_executable_fixed_and_exclusive(self):
        result = subprocess.run([sys.executable, '-B', str(HELPER), 'postgres-sql', '--directory', str(self.root / 'pg')],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode)
        self.assertEqual('', result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report['verified'])
        self.assertFalse(report['nativeRecoveryProven'])
        directory = self.root / 'pg'
        self.assertEqual({'seed.sql', 'snapshot.sql', 'empty.sql', 'catalog.sql', 'contract.json'}, {p.name for p in directory.iterdir()})
        seed = (directory / 'seed.sql').read_text()
        self.assertIn('CREATE SCHEMA recovery_native', seed)
        self.assertNotIn('IF NOT EXISTS', seed)
        self.assertIn('ON_ERROR_STOP', seed)
        self.assertIn('BEGIN;', seed)
        self.assertIn('COMMIT;', seed)
        for fragment in ('FOREIGN KEY', 'CREATE SEQUENCE', 'CREATE VIEW', 'CREATE INDEX', 'bytea', 'jsonb', 'setval', 'COMMENT ON'):
            self.assertIn(fragment, seed)
        snapshot = (directory / 'snapshot.sql').read_text()
        for fragment in ('pg_namespace', 'pg_class', 'pg_attribute', 'pg_constraint', 'pg_index', 'pg_sequence', 'pg_proc', 'pg_trigger', 'pg_largeobject_metadata'):
            self.assertIn(fragment, snapshot)
        self.assertIn('REPEATABLE READ', snapshot)
        self.assertIn('READ ONLY', snapshot)
        contract = json.loads((directory / 'contract.json').read_bytes())
        self.assertEqual(['/usr/local/bin/pg_dump', '--format=custom', '--no-password', '--no-owner', '--no-privileges'], contract['dumpArgv'])
        self.assertEqual(['/usr/local/bin/pg_restore', '--exit-on-error', '--single-transaction', '--no-password', '--no-owner', '--no-privileges', '--dbname=postgres'], contract['restoreArgv'])
        self.assertEqual(['/usr/local/bin/psql', '-X', '--no-password', '-qAt', '-v', 'ON_ERROR_STOP=1'], contract['psqlArgv'])
        self.assertEqual(['PGDATABASE', 'PGHOST', 'PGPASSWORD', 'PGPORT', 'PGUSER'], contract['connectionEnvironment'])
        second = subprocess.run([sys.executable, '-B', str(HELPER), 'postgres-sql', '--directory', str(directory)], capture_output=True, timeout=10)
        self.assertEqual(1, second.returncode)


if __name__ == '__main__':
    unittest.main()
