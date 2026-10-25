"""Pure pinned-age invocation contract. No executable or keys are invoked/read."""
import importlib.util
from pathlib import Path
import unittest
import hashlib
import os
import sys
import subprocess
import tempfile


MODULE = Path(__file__).resolve().parents[1] / 'recovery_transport.py'


class TransportTests(unittest.TestCase):
    def module(self):
        self.assertTrue(MODULE.is_file(), 'pinned streaming transport plan is absent')
        spec = importlib.util.spec_from_file_location('transport', MODULE)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    def test_streaming_age_plan_has_no_shell_passphrase_or_private_key_argument(self):
        m = self.module()
        plan = m.age_plan(executable='C:/approved/age.exe', tool_sha256='1' * 64,
                          recipient='age1' + 'q' * 58, recipient_fingerprint='2' * 64,
                          qualified_version='1.2.1')
        self.assertEqual(plan['argv'], ['C:/approved/age.exe', '--encrypt', '--recipient', 'age1' + 'q' * 58])
        self.assertIs(plan['shell'], False)
        self.assertEqual(plan['stdin'], 'verified-framed-export-stream')
        self.assertEqual(plan['stdout'], 'exclusive-private-ciphertext-file')
        self.assertIs(plan['executableHashMustMatchBeforeSpawn'], True)
        self.assertIs(plan['runtimeQualified'], False)
        self.assertIs(plan['exporterAuthenticated'], False)
        for changes in ({'tool_sha256': 'latest'}, {'recipient': '--identity secret'},
                        {'qualified_version': 'latest'}, {'executable': 'age'},
                        {'recipient_fingerprint': 'bad'}):
            args = dict(executable='C:/approved/age.exe', tool_sha256='1' * 64,
                        recipient='age1' + 'q' * 58, recipient_fingerprint='2' * 64,
                        qualified_version='1.2.1')
            args.update(changes)
            with self.assertRaises(m.TransportError):
                m.age_plan(**args)

    def test_bounded_process_wrapper_hashes_tool_and_publishes_only_after_exit_zero(self):
        m = self.module()
        self.assertTrue(hasattr(m, 'encrypt_file'), 'bounded encryption process wrapper is absent')
        with tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as temp:
            root = Path(temp)
            source, target = root / 'framed.bin', root / 'sealed.age'
            payload = b'synthetic-not-encryption' * 100000
            source.write_bytes(payload)
            digest = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
            calls = []
            def child(argv, **kwargs):
                calls.append((argv, kwargs))
                return subprocess.Popen([sys.executable, '-B', '-c',
                    'import sys;\nwhile c:=sys.stdin.buffer.read(65536): sys.stdout.buffer.write(c)'], **kwargs)
            report = m.encrypt_file(source, target, executable=sys.executable,
                tool_sha256=digest, recipient='age1' + 'q' * 58,
                recipient_fingerprint='2' * 64, qualified_version='1.2.1',
                attest=lambda _: True, popen=child)
            self.assertEqual(target.read_bytes(), payload)
            self.assertEqual(report['sha256'], hashlib.sha256(payload).hexdigest())
            self.assertIs(report['nativeRecoveryProven'], False)
            self.assertIs(report['cryptographyQualified'], False)
            self.assertEqual(calls[0][0], [sys.executable, '--encrypt', '--recipient', 'age1' + 'q' * 58])
            self.assertIs(calls[0][1]['shell'], False)
            self.assertEqual(calls[0][1]['env'], {})
            self.assertEqual(source.read_bytes(), payload)
            self.assertEqual({p.name for p in root.iterdir()}, {'framed.bin', 'sealed.age'})

    def test_source_access_time_change_is_accepted_but_mutation_is_rejected(self):
        m = self.module()
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as temp:
            root = Path(temp)
            source, target = root / 'source', root / 'out'
            digest = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
            for scenario in ('atime', 'content', 'identity'):
                with self.subTest(scenario=scenario):
                    source.write_bytes(b'synthetic')
                    before = source.stat()
                    # Child copies first, then modifies a single synthetic source.
                    script = ('import os,sys; from pathlib import Path; '
                              'sys.stdout.buffer.write(sys.stdin.buffer.read()); '
                              'sys.stdout.buffer.flush(); p=Path(sys.argv[1]); '
                              's=p.stat(); ')
                    script += {
                        'atime': 'os.utime(p, ns=(s.st_atime_ns+10000000000, s.st_mtime_ns))',
                        'content': 'p.write_bytes(b"mutated!!"); os.utime(p, ns=(s.st_atime_ns, s.st_mtime_ns+10000000000))',
                        'identity': 'pass',
                    }[scenario]
                    def spawn(argv, **kwargs):
                        child = subprocess.Popen([sys.executable, '-B', '-c', script, str(source)], **kwargs)
                        if scenario == 'identity':
                            wait = child.wait
                            def replace_after_exit(*args, **options):
                                result = wait(*args, **options)
                                # Windows disallows replace while parent stdin is open.
                                kwargs['stdin'].close()
                                replacement = source.with_name('replacement')
                                replacement.write_bytes(b'synthetic')
                                os.replace(replacement, source)
                                return result
                            child.wait = replace_after_exit
                        return child
                    args = dict(executable=sys.executable, tool_sha256=digest,
                                recipient='age1'+'q'*58, recipient_fingerprint='2'*64,
                                qualified_version='1.2.1', attest=lambda _: True, popen=spawn)
                    if scenario == 'atime':
                        m.encrypt_file(source, target, **args)
                        self.assertEqual(target.read_bytes(), b'synthetic')
                        after = source.stat()
                        self.assertNotEqual(after.st_atime_ns, before.st_atime_ns)
                        self.assertEqual((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns),
                                         (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns))
                        target.unlink()
                    else:
                        with self.assertRaises(m.TransportError):
                            m.encrypt_file(source, target, **args)
                        self.assertFalse(target.exists())
                    self.assertEqual({p.name for p in root.iterdir()}, {'source'})

    def test_process_failures_are_sanitized_reaped_and_never_publish(self):
        m = self.module()
        with tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as temp:
            root = Path(temp)
            source = root / 'source'
            source.write_bytes(b'synthetic')
            digest = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
            for scenario, script in {
                'nonzero': 'import sys; sys.stdout.write("partial"); sys.stderr.write("PRIVATE"); sys.exit(7)',
                'timeout': 'import time; time.sleep(30)',
                'oversize': 'import sys; sys.stdout.write("x"*100)',
                'empty': 'pass',
            }.items():
                with self.subTest(scenario=scenario):
                    children = []
                    def spawn(argv, **kwargs):
                        p = subprocess.Popen([sys.executable, '-B', '-c', script], **kwargs)
                        children.append(p)
                        return p
                    with self.assertRaises(m.TransportError) as error:
                        m.encrypt_file(source, root / 'out', executable=sys.executable,
                            tool_sha256=digest, recipient='age1'+'q'*58,
                            recipient_fingerprint='2'*64, qualified_version='1.2.1',
                            attest=lambda _: True, popen=spawn,
                            timeout=0.2 if scenario == 'timeout' else 5, max_output=10)
                    self.assertNotIn('PRIVATE', str(error.exception))
                    self.assertTrue(all(p.poll() is not None for p in children))
                    self.assertEqual({p.name for p in root.iterdir()}, {'source'})

    def test_admission_rejections_never_spawn_and_preserve_existing_files(self):
        m = self.module()
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as temp:
            root = Path(temp)
            source = root / 'source'
            source.write_bytes(b'synthetic')
            digest = hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()
            base = dict(executable=sys.executable, tool_sha256=digest,
                        recipient='age1'+'q'*58, recipient_fingerprint='2'*64,
                        qualified_version='1.2.1', attest=lambda _: True)
            for changes in ({'tool_sha256':'0'*64}, {'attest':lambda _: 1},
                            {'max_input':1}, {'timeout':float('nan')},
                            {'max_output':True}):
                with self.subTest(changes=list(changes)), patch('subprocess.Popen') as spawn:
                    with self.assertRaises(m.TransportError):
                        m.encrypt_file(source, root / 'out', **(base | changes))
                    spawn.assert_not_called()
            target = root / 'out'
            target.write_bytes(b'keep')
            with patch('subprocess.Popen') as spawn:
                with self.assertRaises(m.TransportError):
                    m.encrypt_file(source, target, **base)
                spawn.assert_not_called()
            self.assertEqual(target.read_bytes(), b'keep')
            target.unlink()
            class Fixed:
                hex = '0'*32
            collision = root / ('.age-stage-' + Fixed.hex)
            collision.write_bytes(b'keep-stage')
            with patch('uuid.uuid4', return_value=Fixed()), patch('subprocess.Popen') as spawn:
                with self.assertRaises(m.TransportError):
                    m.encrypt_file(source, target, **base)
                spawn.assert_not_called()
            self.assertEqual(collision.read_bytes(), b'keep-stage')
            self.assertEqual({p.name for p in root.iterdir()}, {'source', collision.name})


if __name__ == '__main__':
    unittest.main()
