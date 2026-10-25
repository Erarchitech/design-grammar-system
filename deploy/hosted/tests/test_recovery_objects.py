"""Synthetic S3 stream contract; no network/MinIO service is invoked."""
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'recovery_objects.py'


class SyntheticS3:
    def __init__(self):
        self.objects = {'nested/юникод.bin': (b'\x00\xffpayload',
            {'contentType': 'application/octet-stream', 'cacheControl': 'max-age=10',
             'contentDisposition': 'attachment', 'contentEncoding': '',
             'contentLanguage': '', 'userMetadata': {'source': 'synthetic'},
             'tags': {'project': 'one'}}), 'empty': (b'',
            {'contentType': 'text/plain', 'cacheControl': '', 'contentDisposition': '',
             'contentEncoding': '', 'contentLanguage': '', 'userMetadata': {}, 'tags': {}})}
        self.writes = []
    def describe_bucket(self):
        return {'versioning': 'never-enabled', 'policy': None, 'lifecycle': None,
                'encryption': None, 'objectLock': False, 'replication': None,
                'notifications': None}
    def list_objects(self):
        return sorted(self.objects)
    def read_object(self, key):
        data, metadata = self.objects[key]
        return {'bytes': len(data), 'metadata': metadata}, io.BytesIO(data)
    def put_object(self, key, stream, record):
        data = bytearray()
        while chunk := stream.read(65536):
            data.extend(chunk)
        self.objects[key] = (bytes(data), record['metadata'])
        self.writes.append(key)


class ObjectTests(unittest.TestCase):
    def module(self):
        self.assertTrue(MODULE.is_file(), 'bounded object/metadata stream adapter is absent')
        sys.path.insert(0, str(MODULE.parent))
        self.addCleanup(lambda: sys.path.remove(str(MODULE.parent)))
        spec = importlib.util.spec_from_file_location('objects', MODULE)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_unversioned_roundtrip_preserves_bytes_and_metadata(self):
        m = self.module()
        with tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as temp:
            source = SyntheticS3()
            package = Path(temp) / 'objects'
            exported = m.export_objects(source, package, attest=lambda _: True)
            self.assertIs(exported['nativeRecoveryProven'], False)
            destination = SyntheticS3()
            destination.objects = {}
            m.restore_objects(package, destination, expected_manifest_sha256=exported['manifestSha256'],
                              attest=lambda _: True)
            self.assertEqual(destination.objects, source.objects)
            self.assertEqual(destination.writes, sorted(source.objects))
            self.assertTrue(all(p.name.isascii() for p in package.iterdir()))

    def test_failure_and_interruption_leave_no_published_export_or_stage(self):
        m = self.module()
        for failure in (RuntimeError('synthetic-private'), KeyboardInterrupt()):
            with tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as temp:
                source = SyntheticS3()
                def broken(key):
                    raise failure
                source.read_object = broken
                error = KeyboardInterrupt if isinstance(failure, KeyboardInterrupt) else m.ObjectError
                with self.assertRaises(error) as caught:
                    m.export_objects(source, Path(temp) / 'package', attest=lambda _: True)
                self.assertNotIn('synthetic-private', str(caught.exception))
                self.assertEqual(list(Path(temp).iterdir()), [])

    def test_unsupported_bucket_config_is_refused_before_any_object_read(self):
        m = self.module()
        for field, value in [('versioning', 'suspended'), ('policy', {}),
                             ('lifecycle', {}), ('encryption', {}), ('objectLock', True),
                             ('replication', {}), ('notifications', {})]:
            with tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as temp:
                source = SyntheticS3()
                description = source.describe_bucket()
                description[field] = value
                source.describe_bucket = lambda: description
                source.read_object = lambda _: self.fail('must reject before read')
                with self.assertRaises(m.ObjectError):
                    m.export_objects(source, Path(temp) / 'package', attest=lambda _: True)
                self.assertEqual(list(Path(temp).iterdir()), [])

    def test_corruption_extra_file_wrong_hash_and_nonempty_target_never_write(self):
        m = self.module()
        with tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as temp:
            package = Path(temp) / 'package'
            exported = m.export_objects(SyntheticS3(), package, attest=lambda _: True)
            digest = exported['manifestSha256']
            destination = SyntheticS3()
            with self.assertRaises(m.ObjectError):
                m.restore_objects(package, destination, expected_manifest_sha256=digest, attest=lambda _: True)
            self.assertEqual(destination.writes, [])
            destination.objects = {}
            for bad in ('corrupt', 'extra', 'hash'):
                original = (package / '0000.object').read_bytes()
                if bad == 'corrupt':
                    (package / '0000.object').write_bytes(b'x')
                elif bad == 'extra':
                    (package / 'unexpected').write_bytes(b'x')
                with self.assertRaises(m.ObjectError):
                    m.restore_objects(package, destination,
                        expected_manifest_sha256='0' * 64 if bad == 'hash' else digest,
                        attest=lambda _: True)
                self.assertEqual(destination.writes, [])
                (package / '0000.object').write_bytes(original)
                if bad == 'extra':
                    (package / 'unexpected').unlink()

    def test_stream_reads_are_bounded_and_fidelity_verified(self):
        m = self.module()
        with tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as temp:
            source = SyntheticS3()
            original = source.read_object
            class Bounded(io.BytesIO):
                def read(inner, size=-1):
                    self.assertTrue(0 < size <= 65536)
                    return super().read(size)
            def read(key):
                record, stream = original(key)
                return record, Bounded(stream.read())
            source.read_object = read
            package = Path(temp) / 'package'
            exported = m.export_objects(source, package, attest=lambda _: True)
            destination = SyntheticS3()
            destination.objects = {}
            put = destination.put_object
            def bad_put(key, stream, record):
                put(key, stream, record)
                data, metadata = destination.objects[key]
                destination.objects[key] = (data + b'x', metadata)
            destination.put_object = bad_put
            with self.assertRaises(m.ObjectError):
                m.restore_objects(package, destination,
                    expected_manifest_sha256=exported['manifestSha256'], attest=lambda _: True)
            self.assertTrue(destination.writes)

    def test_stage_collision_and_cleanup_failure_preserve_and_sanitize(self):
        m = self.module()
        from unittest.mock import patch
        class Fixed:
            hex = '0' * 32
        with tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as temp:
            existing = Path(temp) / ('objects-stage-' + '0' * 32)
            existing.mkdir()
            (existing / 'keep').write_bytes(b'preexisting')
            with patch.object(m.uuid, 'uuid4', return_value=Fixed()):
                with self.assertRaises(m.ObjectError):
                    m.export_objects(SyntheticS3(), Path(temp) / 'package', attest=lambda _: True)
            self.assertTrue((existing / 'keep').exists(), 'preexisting object stage was removed')
        with tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as temp:
            source = SyntheticS3()
            def broken(_):
                raise OSError('synthetic-private')
            source.read_object = broken
            with patch.object(m.shutil, 'rmtree', side_effect=OSError('synthetic-private')):
                with self.assertRaisesRegex(m.ObjectError, '^object operation rejected$'):
                    m.export_objects(source, Path(temp) / 'package', attest=lambda _: True)
            self.assertFalse((Path(temp) / 'package').exists())
            self.assertTrue(list(Path(temp).glob('objects-stage-*')))

    def test_reused_provider_metadata_is_snapshotted_before_stream_read(self):
        m = self.module()
        import json
        with tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as temp:
            provider = SyntheticS3()
            shared = dict(provider.objects['empty'][1])
            shared['tags'] = {}
            shared['userMetadata'] = {}
            def read(key):
                shared['tags']['name'] = key
                shared['userMetadata']['name'] = key
                class MutatingStream(io.BytesIO):
                    def read(inner, size=-1):
                        shared['tags']['name'] = 'mutated-during-read'
                        return super().read(size)
                return {'bytes': 1, 'metadata': shared}, MutatingStream(b'x')
            provider.read_object = read
            package = Path(temp) / 'package'
            m.export_objects(provider, package, attest=lambda _: True)
            records = json.loads((package / 'objects.json').read_bytes())['objects']
            self.assertEqual([r['metadata']['tags']['name'] for r in records], sorted(provider.objects))
            self.assertEqual([r['metadata']['userMetadata']['name'] for r in records], sorted(provider.objects))

    def test_s3_listing_follows_continuation_without_prefix_or_delimiter(self):
        m = self.module()
        self.assertTrue(hasattr(m, 'iter_s3_keys'), 'bounded S3 pagination is absent')
        class Client:
            def __init__(inner):
                inner.calls = []
            def list_objects_v2(inner, **request):
                inner.calls.append(request)
                if len(inner.calls) == 1:
                    return {'IsTruncated':True, 'Contents':[{'Key':'nested/юникод.bin'}],
                            'NextContinuationToken':'opaque-token', 'KeyCount':1}
                return {'IsTruncated':False, 'Contents':[{'Key':'empty'}], 'KeyCount':1}
        client = Client()
        self.assertEqual(list(m.iter_s3_keys(client, 'synthetic-bucket')), ['nested/юникод.bin','empty'])
        self.assertEqual(client.calls, [
            {'Bucket':'synthetic-bucket','MaxKeys':1000},
            {'Bucket':'synthetic-bucket','MaxKeys':1000,'ContinuationToken':'opaque-token'}])

    def test_s3_pagination_rejects_ambiguous_or_filtered_pages(self):
        m = self.module()
        import copy
        base = {'IsTruncated':False, 'Contents':[{'Key':'one'}], 'KeyCount':1}
        for change in (
            {'IsTruncated':1}, {'IsTruncated':True},
            {'IsTruncated':True,'NextContinuationToken':''},
            {'KeyCount':True}, {'KeyCount':0}, {'Contents':None},
            {'Contents':[{'Key':'one'},{'Key':'one'}],'KeyCount':2},
            {'CommonPrefixes':[{'Prefix':'hidden/'}]}, {'Prefix':'subset/'},
            {'Delimiter':'/'}, {'StartAfter':'m-hidden'},
            {'Name':'other-bucket'}, {'EncodingType':'url'},
            {'ContinuationToken':'unexpected'}, {'NextContinuationToken':'unexpected'},
            {'Contents':[{'Key':'x'*1025}]},
        ):
            class Client:
                def list_objects_v2(inner, **request):
                    return copy.deepcopy(base | change)
            with self.subTest(change=change), self.assertRaises(m.ObjectError):
                list(m.iter_s3_keys(Client(), 'synthetic-bucket'))
        class Empty:
            def list_objects_v2(inner, **request):
                return {'IsTruncated':False,'KeyCount':0}
        self.assertEqual(list(m.iter_s3_keys(Empty(), 'synthetic-bucket')), [])

    def test_s3_pagination_bounds_cycles_pages_and_total_keys(self):
        m = self.module()
        from unittest.mock import patch
        for scenario in ('cycle','duplicate','pages','objects','private-error'):
            calls = []
            class Client:
                def list_objects_v2(inner, **request):
                    calls.append(request)
                    if scenario == 'private-error':
                        raise RuntimeError('PRIVATE')
                    n = len(calls)
                    return {'IsTruncated':True, 'KeyCount':1,
                            'Contents':[{'Key':'same' if scenario == 'duplicate' else str(n)}],
                            'NextContinuationToken':'same' if scenario == 'cycle' else str(n)}
            with self.subTest(scenario=scenario), patch.object(m, 'MAX_OBJECTS', 2):
                with self.assertRaises(m.ObjectError) as error:
                    list(m.iter_s3_keys(Client(), 'synthetic-bucket',
                                       max_pages=1 if scenario == 'pages' else 3))
                self.assertNotIn('PRIVATE', str(error.exception))
                self.assertEqual(len(calls), {'cycle':2,'duplicate':2,'pages':1,
                                             'objects':3,'private-error':1}[scenario])


if __name__ == '__main__':
    unittest.main()
