"""Offline framed multi-store archive tests (not crypto qualification)."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE = Path(__file__).resolve().parents[1] / 'recovery-test' / 'multistore_archive.py'
SCRATCH = Path(os.environ.get('HERMES_SCRATCH_DIR',
    'C:/Users/Admin/AppData/Local/hermes/cache/scratch' if os.name == 'nt' else tempfile.gettempdir()))


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def module(self):
        self.assertTrue(MODULE.is_file(), 'authenticated full multi-store archive helper is absent')
        spec = importlib.util.spec_from_file_location('multistore_archive', MODULE)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def fixture(self):
        source = self.root / 'exports'
        source.mkdir()
        # Independently enumerate required components, not production constants.
        for component, name, payload in (
            ('neo4j', 'neo4j.dump', b'neo4j-native-dump\x00'),
            ('postgres', 'n8n.dump', b'PGDMP\x00postgres-custom-dump'),
            ('minio', 'manifest.json', b'{"synthetic":true}'),
            ('n8n', 'full.tar', b'opaque-full-n8n-volume-archive'),
            ('api', 'nested/auth.json', b'api-tree\x00'),
            ('key-references', 'references.json', b'{"retainedIdentity":"separate"}'),
        ):
            target = source / component / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        (source / 'api' / 'empty').mkdir()
        return source

    def snapshot(self, source):
        return {p.relative_to(source).as_posix(): p.read_bytes()
                for p in source.rglob('*') if p.is_file()}

    def test_frame_roundtrip_covers_every_store_exact_bytes_and_empty_directory(self):
        m = self.module()
        source = self.fixture()
        original = self.snapshot(source)
        frame = self.root / 'frame.bin'
        manifest = m.build_frame(source, frame)
        self.assertEqual(manifest['schema'], 'dg-multistore-frame-v1')
        self.assertEqual({entry['path'] for entry in manifest['files']}, set(original))
        self.assertIn('api/empty', manifest['directories'])
        for entry in manifest['files']:
            self.assertEqual(entry['sha256'], hashlib.sha256(original[entry['path']]).hexdigest())
            self.assertEqual(entry['bytes'], len(original[entry['path']]))
        restored = self.root / 'restored'
        result = m.extract_frame(frame, restored)
        self.assertEqual(result, manifest)
        self.assertEqual(self.snapshot(restored), original)
        self.assertTrue((restored / 'api/empty').is_dir())
        self.assertEqual(self.snapshot(source), original)

    def test_crypto_roundtrip_is_pinned_bounded_and_completion_is_last(self):
        m = self.module()
        self.assertTrue(hasattr(m, 'seal'), 'seal/open process orchestration is absent')
        source = self.fixture()
        original = self.snapshot(source)
        work = self.root / 'work'
        work.mkdir()
        digest = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
        calls = []
        def spawn(argv, **kwargs):
            calls.append((argv, kwargs))
            script = ('import sys; '
                      'sys.stdout.write("1.2.1\\n")' if argv[-1] == '--version' else
                      'import sys;\nwhile c:=sys.stdin.buffer.read(65536): sys.stdout.buffer.write(c)')
            return subprocess.Popen([sys.executable, '-B', '-c', script], **kwargs)
        options = dict(executable=sys.executable, tool_sha256=digest,
                       work=work, popen=spawn, timeout=10)
        recipient = self.root / 'recipient.txt'
        recipient.write_text('age1' + 'q' * 58 + '\n')
        identity = self.root / 'identity.txt'
        identity.write_text(self.synthetic_identity())
        sealed = self.root / 'sealed'
        report = m.seal(source, sealed, recipient_file=recipient, **options)
        self.assertEqual({p.name for p in sealed.iterdir()}, {'archive.age', 'COMPLETE.json'})
        ciphertext = sealed / 'archive.age'
        self.assertEqual(report['sha256'], hashlib.sha256(ciphertext.read_bytes()).hexdigest())
        restored = self.root / 'restored'
        opened = m.open_archive(ciphertext, restored, identity_file=identity,
                                archive_sha256=report['sha256'], **options)
        self.assertEqual(self.snapshot(restored) | {}, original | {'COMPLETE.json': (restored / 'COMPLETE.json').read_bytes()})
        self.assertTrue(opened['authenticatedBeforeDestinationCreation'])
        self.assertFalse(opened['exporterAuthenticated'])
        self.assertFalse(opened['nativeRecoveryProven'])
        self.assertEqual(self.snapshot(source), original)
        self.assertEqual(list(work.iterdir()), [])
        self.assertEqual([a[-1] for a, _ in calls].count('--version'), 2)
        self.assertTrue(all(k['shell'] is False and k['env'] == {} for _, k in calls))
        self.assertTrue(any('--identity' in a and str(identity) in a for a, _ in calls))
        self.assertFalse(any('AGE-SECRET-' in str(a) for a, _ in calls))
    def crypto_fixture(self):
        source = self.fixture()
        work = self.root / 'work'
        work.mkdir()
        recipient = self.root / 'recipient.txt'
        recipient.write_text('age1' + 'q' * 58 + '\n')
        identity = self.root / 'identity.txt'
        identity.write_text(self.synthetic_identity())
        options = dict(executable=sys.executable,
                       tool_sha256=hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
                       work=work, timeout=5)
        return source, recipient, identity, options

    def child(self, script, children=None):
        def spawn(argv, **kwargs):
            code = ('import sys; sys.stdout.write("1.2.1\\n")'
                    if argv[-1] == '--version' else script)
            p = subprocess.Popen([sys.executable, '-B', '-c', code], **kwargs)
            if children is not None:
                children.append(p)
            return p
        return spawn

    def test_partial_decrypt_nonzero_timeout_empty_oversize_never_create_destination(self):
        m = self.module()
        source, recipient, identity, opts = self.crypto_fixture()
        frame = self.root / 'ciphertext'
        m.build_frame(source, frame)
        digest = hashlib.sha256(frame.read_bytes()).hexdigest()
        for name, script in {
            'late-auth-failure': 'import sys; sys.stdout.buffer.write(sys.stdin.buffer.read()); sys.stderr.write("PRIVATE"); sys.exit(7)',
            'timeout': 'import time; time.sleep(30)',
            'empty': 'pass',
            'oversize': 'import sys; sys.stdout.buffer.write(b"x"*100000)',
        }.items():
            with self.subTest(name=name):
                children = []
                with patch.object(m, 'MAX_TOTAL', 128 if name == 'oversize' else m.MAX_TOTAL), \
                     patch.object(m, 'MAX_MANIFEST', 128 if name == 'oversize' else m.MAX_MANIFEST):
                    with self.assertRaises(m.ArchiveError) as err:
                        m.open_archive(frame, self.root / 'out', identity_file=identity,
                            archive_sha256=digest, **(opts | {'timeout':0.2 if name=='timeout' else 5,
                            'popen':self.child(script, children)}))
                self.assertNotIn('PRIVATE', str(err.exception))
                self.assertFalse((self.root / 'out').exists())
                self.assertEqual(list(opts['work'].iterdir()), [])
                self.assertTrue(children and all(p.poll() is not None for p in children))

    def test_malicious_framing_rejects_paths_duplicates_links_limits_and_trailing_bytes(self):
        m = self.module()
        source = self.fixture()
        frame = self.root / 'frame'
        manifest = m.build_frame(source, frame)
        encoded_len = struct.unpack('>Q', frame.read_bytes()[len(m.MAGIC):len(m.MAGIC)+8])[0]
        payload = frame.read_bytes()[len(m.MAGIC)+8+encoded_len:]
        scenarios = []
        for path in ('../escape', '/absolute', 'C:/drive', 'api\\escape', 'api//escape',
                     'api/./escape', 'api/x:stream', 'api/CON', 'api/has. ', 'api/../x'):
            v = json.loads(json.dumps(manifest)); v['files'][0]['path'] = path; scenarios.append((path,v,payload))
        for name in ('duplicate','case','hash','missing-store','extra-field','file-dir-collision','oversize','bool-size'):
            v = json.loads(json.dumps(manifest))
            if name == 'duplicate': v['files'].append(v['files'][0])
            if name == 'case': v['directories'].append('API')
            if name == 'hash': v['files'][0]['sha256'] = '0'*64
            if name == 'missing-store': v['files'] = [f for f in v['files'] if not f['path'].startswith('neo4j/')]
            if name == 'extra-field': v['files'][0]['link'] = 'target'
            if name == 'file-dir-collision': v['directories'].append(v['files'][0]['path'])
            if name == 'oversize': v['files'][0]['bytes'] = m.MAX_TOTAL+1
            if name == 'bool-size': v['files'][0]['bytes'] = True
            scenarios.append((name,v,payload))
        for name, value, body in scenarios:
            with self.subTest(name=name):
                data = json.dumps(value).encode()
                frame.write_bytes(m.MAGIC + struct.pack('>Q',len(data)) + data + body)
                with self.assertRaises(m.ArchiveError): m.extract_frame(frame, self.root/'out')
                self.assertFalse((self.root/'out').exists())
        for content in (b'', b'not-a-frame', m.MAGIC+struct.pack('>Q',m.MAX_MANIFEST+1)):
            frame.write_bytes(content)
            with self.assertRaises(m.ArchiveError): m.extract_frame(frame,self.root/'out')
        m.build_frame(source,self.root/'valid')
        valid=(self.root/'valid').read_bytes()
        for content in (valid+b'trailing', valid[:-1]):
            frame.write_bytes(content)
            with self.assertRaises(m.ArchiveError): m.extract_frame(frame,self.root/'out')

    def test_manifest_parser_errors_are_sanitized(self):
        m = self.module()
        frame = self.root/'bad'
        bad = b'{"PRIVATE": invalid}'
        frame.write_bytes(m.MAGIC+struct.pack('>Q',len(bad))+bad)
        with self.assertRaises(m.ArchiveError) as error:
            m.validate_frame(frame)
        self.assertNotIn('PRIVATE', str(error.exception))
    def test_inventory_total_is_bounded_before_reading_extra_file(self):
        m = self.module()
        source = self.fixture()
        read = []
        original = m._hash
        def bounded(stream, size, output=None):
            read.append(size)
            return original(stream,size,output)
        with patch.object(m,'MAX_TOTAL',70), patch.object(m,'_hash',side_effect=bounded):
            with self.assertRaises(m.ArchiveError): m.build_frame(source,self.root/'frame')
        self.assertLessEqual(sum(read),70,'over-limit file bytes were read before rejection')

    def test_links_inventory_collision_and_foreign_staging_never_get_removed(self):
        m = self.module()
        source,recipient,identity,opts=self.crypto_fixture()
        frame=self.root/'frame'
        file=source/'api/nested/auth.json'
        linked=self.root/'hardlink'
        os.link(file,linked)
        with self.assertRaises(m.ArchiveError): m.build_frame(source,frame)
        linked.unlink()
        # Windows symlink privilege is not required: use junction creation on Windows.
        outside=self.root/'outside'; outside.mkdir(); (outside/'keep').write_bytes(b'keep')
        link=source/'api/link'
        if os.name=='nt':
            result=subprocess.run(['cmd.exe','/c','mklink','/J',str(link),str(outside)],
                stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            self.assertEqual(result.returncode,0)
        else:
            link.symlink_to(outside,target_is_directory=True)
        try:
            with self.assertRaises(m.ArchiveError): m.build_frame(source,frame)
        finally:
            if os.name=='nt': os.rmdir(link)
            else: link.unlink()
        self.assertEqual((outside/'keep').read_bytes(),b'keep')
        class Fixed:
            hex='0'*32
        collision=opts['work']/('.multistore-'+Fixed.hex)
        for populated in (False,True):
            collision.mkdir()
            if populated: (collision/'keep').write_bytes(b'keep')
            with patch.object(m.uuid,'uuid4',return_value=Fixed()), patch.object(m.subprocess,'Popen') as spawn:
                with self.assertRaises(m.ArchiveError): m.seal(source,self.root/'out',recipient_file=recipient,**opts)
                spawn.assert_not_called()
            self.assertTrue(collision.is_dir())
            if populated: self.assertEqual((collision/'keep').read_bytes(),b'keep')
            import shutil; shutil.rmtree(collision)
        for existing in (b'keep',None):
            out=self.root/'out'
            if existing: out.write_bytes(existing)
            else: out.mkdir()
            with self.assertRaises(m.ArchiveError): m.seal(source,out,recipient_file=recipient,**opts)
            if existing: self.assertEqual(out.read_bytes(),existing); out.unlink()
            else: self.assertEqual(list(out.iterdir()),[]); out.rmdir()

    def test_ciphertext_bound_includes_complete_frame_chunk_tags_and_header(self):
        m = self.module()
        frame = 64 * 1024**3 + 8 * 1024**2 + len(m.MAGIC) + 8
        expected = frame + ((frame + 65535) // 65536) * 16 + 65536
        self.assertEqual(getattr(m, 'MAX_CIPHERTEXT', 0), expected)
        self.assertGreater(expected, m.MAX_TOTAL + m.MAX_MANIFEST + 16*1024**2)
        for size, tags in ((65535, 16), (65536, 16), (65537, 32), (0, 16)):
            self.assertEqual(m._ciphertext_bound(size), size + tags + 65536)
        # Both actual call sites must use the same derived admission ceiling.
        source, recipient, identity, opts = self.crypto_fixture()
        calls = []
        original = m._run
        def record(argv, *args, **kwargs):
            calls.append((argv, kwargs['max_output']))
            return original(argv, *args, **kwargs)
        opts['popen'] = self.child('import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())')
        with patch.object(m, '_run', side_effect=record):
            result = m.seal(source, self.root/'sealed', recipient_file=recipient, **opts)
        self.assertEqual(next(limit for argv, limit in calls if '--encrypt' in argv), expected)
        archive = self.root/'sealed/archive.age'
        real_node = m._node
        from types import SimpleNamespace
        def sized(path, directory=False):
            value = real_node(path, directory)
            return SimpleNamespace(st_size=expected+1) if Path(path)==archive else value
        with patch.object(m, '_node', side_effect=sized), patch.object(m, '_file_digest', return_value=result['sha256']), \
             patch.object(m.subprocess, 'Popen') as spawn:
            with self.assertRaises(m.ArchiveError):
                m.open_archive(archive, self.root/'out', identity_file=identity,
                    archive_sha256=result['sha256'], **(opts | {'popen': None}))
            spawn.assert_not_called()

    def test_negative_rejects_unrelated_failures_and_invalid_wrong_identities(self):
        m = self.module()
        source, recipient, identity, opts = self.crypto_fixture()
        frame = self.root / 'ciphertext'
        m.build_frame(source, frame)
        digest = hashlib.sha256(frame.read_bytes()).hexdigest()
        wrong = self.root / 'wrong.identity'
        for kind in ('missing', 'malformed', 'checksum', 'same', 'exit1', 'timeout',
                     'spawn', 'permission', 'version', 'tool'):
            with self.subTest(kind=kind):
                wrong.unlink(missing_ok=True)
                if kind != 'missing':
                    wrong.write_text('PRIVATE invalid' if kind == 'malformed' else
                        'AGE-SECRET-KEY-1' + 'Q' * 58 if kind == 'checksum' else
                        identity.read_text() if kind == 'same' else self.synthetic_identity(1))
                def spawn(argv, **kwargs):
                    is_wrong = str(wrong) in argv
                    if is_wrong and kind == 'spawn': raise OSError('PRIVATE')
                    if is_wrong and kind == 'permission': raise PermissionError('PRIVATE')
                    if argv[-1] == '--version':
                        script = 'print("1.2.0")' if kind == 'version' else 'print("1.2.1")'
                    elif is_wrong:
                        script = 'import time; time.sleep(30)' if kind == 'timeout' else 'import sys; sys.exit(1)'
                    elif kwargs['stdin'].name.endswith('corrupt.age'):
                        script = 'import sys; sys.exit(1)'
                    else:
                        script = 'import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())'
                    return subprocess.Popen([sys.executable, '-B', '-c', script], **kwargs)
                with self.assertRaises(m.ArchiveError) as error:
                    m.negative(frame, self.root / 'probe', identity_file=identity,
                        wrong_identity_file=wrong, archive_sha256=digest,
                        **(opts | {'popen': spawn, 'timeout': 0.2 if kind == 'timeout' else 5,
                                   'tool_sha256': '0'*64 if kind == 'tool' else opts['tool_sha256']}))
                self.assertNotIn('PRIVATE', str(error.exception))
                self.assertFalse((self.root / 'probe').exists())
                self.assertEqual(list(opts['work'].iterdir()), [])

    @staticmethod
    def synthetic_identity(value=0):
        # Public deterministic throwaway Bech32 fixture; no crypto assertion.
        alphabet = 'qpzry9x8gf2tvdw0s3jn54khce6mua7l'
        hrp = 'age-secret-key-'
        data = [value] + [0] * 51
        def polymod(values):
            chk = 1
            for v in values:
                top = chk >> 25
                chk = ((chk & 0x1ffffff) << 5) ^ v
                for i, g in enumerate((0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3)):
                    if (top >> i) & 1: chk ^= g
            return chk
        expanded = [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]
        checksum = polymod(expanded + data + [0]*6) ^ 1
        return (hrp + '1' + ''.join(alphabet[v] for v in data +
            [(checksum >> (5*(5-i))) & 31 for i in range(6)])).upper() + '\n'

    def test_cli_negative_mode_exercises_both_failures_without_output_mutation(self):
        m = self.module()
        self.assertTrue(hasattr(m,'negative'), 'negative decrypt probe is absent')
        source,recipient,identity,opts=self.crypto_fixture()
        frame=self.root/'ciphertext'
        m.build_frame(source,frame)
        original=frame.read_bytes()
        # Synthetic orchestration only: distinct valid keys, fixed simulated diagnostics.
        bad=self.root/'wrong.identity'; bad.write_text(self.synthetic_identity(1))
        def spawn(argv,**kwargs):
            if argv[-1]=='--version':
                script='import sys; sys.stdout.write("1.2.1\\n")'
            elif str(bad) in argv or kwargs['stdin'].name.endswith('corrupt.age'):
                text = ('no identity matched any of the recipients' if str(bad) in argv
                        else 'failed to decrypt and authenticate payload chunk')
                diagnostic = 'age: error: ' + text + '\nage: report unexpected or unhelpful errors at https://filippo.io/age/report\n'
                script='import sys; sys.stderr.write(' + repr(diagnostic) + '); sys.exit(1)'
            else:
                script='import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())'
            return subprocess.Popen([sys.executable,'-B','-c',script],**kwargs)
        result=m.negative(frame,self.root/'probe',identity_file=identity,
            wrong_identity_file=bad,archive_sha256=hashlib.sha256(original).hexdigest(),
            **(opts|{'popen':spawn}))
        self.assertTrue(result['badKeyRejectedBeforeDestination'])
        self.assertTrue(result['corruptCiphertextRejectedBeforeDestination'])
        self.assertFalse((self.root/'probe').exists())
        self.assertEqual(frame.read_bytes(),original)
        self.assertEqual(list(opts['work'].iterdir()),[])
    def test_invalid_private_key_kinds_and_tool_hash_reject_before_spawn(self):
        m=self.module()
        source,recipient,identity,opts=self.crypto_fixture()
        frame=self.root/'frame'; m.build_frame(source,frame)
        for key in ('AGE-PLUGIN-UNKNOWN-1BAD','ssh-ed25519 invalid','', 'PRIVATE NOT A KEY'):
            identity.write_text(key)
            with patch.object(m.subprocess,'Popen') as spawn:
                with self.assertRaises(m.ArchiveError):
                    m.open_archive(frame,self.root/'out',identity_file=identity,
                        archive_sha256=hashlib.sha256(frame.read_bytes()).hexdigest(),**opts)
                spawn.assert_not_called()
        with patch.object(m.subprocess,'Popen') as spawn:
            with self.assertRaises(m.ArchiveError):
                m.seal(source,self.root/'out',recipient_file=recipient,**(opts|{'tool_sha256':'0'*64}))
            spawn.assert_not_called()

    def test_authentication_failure_does_not_even_mkdir_destination(self):
        m=self.module()
        source,recipient,identity,opts=self.crypto_fixture()
        frame=self.root/'ciphertext'; m.build_frame(source,frame)
        original=Path.mkdir
        target=self.root/'must-not-touch'
        mkdirs=[]
        def recording(path,*args,**kwargs):
            mkdirs.append(path)
            return original(path,*args,**kwargs)
        with patch.object(Path,'mkdir',recording):
            with self.assertRaises(m.ArchiveError):
                m.open_archive(frame,target,identity_file=identity,
                    archive_sha256=hashlib.sha256(frame.read_bytes()).hexdigest(),
                    **(opts|{'popen':self.child('import sys; sys.stdout.buffer.write(sys.stdin.buffer.read()); sys.exit(4)')}))
        self.assertNotIn(target,mkdirs)
        self.assertFalse(target.exists())

    def test_source_access_time_is_accepted_but_content_mutation_aborts(self):
        m=self.module(); source=self.fixture(); frame=self.root/'frame'
        item=source/'api/nested/auth.json'
        original=m._hash
        done=[]
        def mutate(stream,size,output=None):
            result=original(stream,size,output)
            if not done and str(stream.name)==str(item):
                s=item.stat(); os.utime(item,ns=(s.st_atime_ns+1000000000,s.st_mtime_ns)); done.append(True)
            return result
        with patch.object(m,'_hash',side_effect=mutate): m.build_frame(source,frame)
        self.assertTrue(done); frame.unlink(); done.clear()
        def content(stream,size,output=None):
            result=original(stream,size,output)
            if not done and str(stream.name)==str(item):
                s=item.stat(); os.utime(item,ns=(s.st_atime_ns,s.st_mtime_ns+1000000000)); done.append(True)
            return result
        with patch.object(m,'_hash',side_effect=content):
            with self.assertRaises(m.ArchiveError): m.build_frame(source,frame)
        self.assertFalse(frame.exists())

    def test_enumeration_budget_is_checked_at_os_iterator_before_sorting(self):
        m=self.module(); source=self.fixture()
        real=m.os.scandir; count=[]
        class Many:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def __iter__(self):
                for i in range(100):
                    count.append(i)
                    yield object() # No names accessed before over-budget rejection.
        with patch.object(m,'MAX_FILES',1), patch.object(m,'MAX_DIRS',1), \
             patch.object(m.os,'scandir',return_value=Many()):
            with self.assertRaises(m.ArchiveError): m.build_frame(source,self.root/'frame')
        self.assertEqual(len(count),3)
    def test_completion_is_published_atomically_after_payload_and_failure_rolls_back(self):
        m=self.module()
        source,recipient,identity,opts=self.crypto_fixture()
        opts['popen']=self.child('import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())')
        original=m.os.link
        observations=[]
        def publishing(src,dst,*args,**kwargs):
            observations.append(Path(dst).name)
            self.assertEqual(Path(dst).name,'COMPLETE.json')
            self.assertFalse(Path(dst).exists())
            self.assertEqual(json.loads(Path(src).read_bytes())['schema'],'dg-multistore-sealed-v1')
            self.assertTrue((Path(dst).parent/'archive.age').is_file())
            return original(src,dst,*args,**kwargs)
        with patch.object(m.os,'link',side_effect=publishing):
            m.seal(source,self.root/'sealed',recipient_file=recipient,**opts)
        self.assertEqual(observations,['COMPLETE.json'])
        self.assertEqual({p.name for p in (self.root/'sealed').iterdir()},{'archive.age','COMPLETE.json'})
        with patch.object(m,'_complete',side_effect=OSError('PRIVATE')):
            with self.assertRaises(m.ArchiveError):
                m.seal(source,self.root/'failure',recipient_file=recipient,**opts)
        self.assertFalse((self.root/'failure').exists())
        self.assertEqual(list(opts['work'].iterdir()),[])
    def test_private_identity_is_rejected_instead_of_public_recipient_before_spawn(self):
        m=self.module()
        source,recipient,identity,opts=self.crypto_fixture()
        private=source/'key-references/identity.txt'
        private.write_bytes(identity.read_bytes())
        with patch.object(m.subprocess,'Popen') as spawn:
            with self.assertRaises(m.ArchiveError):
                m.seal(source,self.root/'out',recipient_file=private,**opts)
            spawn.assert_not_called()

    def test_version_mismatch_is_rejected_and_admission_invalid_limits_never_spawn(self):
        m=self.module(); source,recipient,identity,opts=self.crypto_fixture()
        for change in ({'timeout':float('nan')},{'timeout':True},{'timeout':0},{'timeout':3601},
                       {'tool_sha256':'bad'},{'executable':'age'}):
            with patch.object(m.subprocess,'Popen') as spawn:
                with self.assertRaises(m.ArchiveError):
                    m.seal(source,self.root/'out',recipient_file=recipient,**(opts|change))
                spawn.assert_not_called()
        def wrong_version(argv,**kwargs):
            return subprocess.Popen([sys.executable,'-B','-c','print("v1.2.0")'],**kwargs)
        with self.assertRaises(m.ArchiveError):
            m.seal(source,self.root/'out',recipient_file=recipient,**(opts|{'popen':wrong_version}))
        self.assertFalse((self.root/'out').exists())
        self.assertEqual(list(opts['work'].iterdir()),[])


if __name__ == '__main__':
    unittest.main()
