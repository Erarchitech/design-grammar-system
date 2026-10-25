"""Offline exchange mechanics, not native/crypto qualification."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1]/'recovery-test/multistore_exchange.py'
SCRATCH = Path('C:/Users/Admin/AppData/Local/hermes/cache/scratch')

class ExchangeTests(unittest.TestCase):
    def cli(self, *args):
        return subprocess.run([sys.executable, '-B', str(MODULE), *map(str,args)], capture_output=True, timeout=15)

    def test_empty_mounted_exchange_initializes_a_private_child_not_the_mount_root(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            mount=Path(tmp)/'mount';mount.mkdir()
            r=self.cli('init','--root',mount/'run')
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(sorted(x.name for x in mount.iterdir()), ['run'])
            self.assertTrue((mount/'run/sql').is_dir())
            self.assertTrue((mount/'run/reports').is_dir())

    def test_copy_tree_preserves_empty_directories_and_rejects_collision(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);src=root/'source';src.mkdir()
            (src/'nested').mkdir();(src/'empty').mkdir();(src/'nested/value').write_bytes(b'synthetic')
            dst=root/'destination'
            r=self.cli('tree','--source',src,'--destination',dst)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual((dst/'nested/value').read_bytes(),b'synthetic')
            self.assertTrue((dst/'empty').is_dir())
            r=self.cli('tree','--source',src,'--destination',dst)
            self.assertNotEqual(r.returncode,0)
            self.assertEqual((dst/'nested/value').read_bytes(),b'synthetic')

    def test_restore_tree_fills_an_existing_empty_mount_root_and_preserves_it(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);src=root/'source';src.mkdir()
            (src/'nested').mkdir();(src/'empty').mkdir();(src/'nested/value').write_bytes(b'synthetic')
            mount=root/'mount';mount.mkdir()
            before=(mount.stat().st_ino)
            r=self.cli('restore-tree','--source',src,'--destination',mount)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(json.loads(r.stdout)['files'],1)
            self.assertEqual((mount/'nested/value').read_bytes(),b'synthetic')
            self.assertTrue((mount/'empty').is_dir())
            self.assertEqual(mount.stat().st_ino,before)

    def test_restore_tree_rejects_nonempty_missing_nested_or_link_destinations_without_mutation(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);src=root/'source';src.mkdir();(src/'value').write_bytes(b'synthetic')
            populated=root/'populated';populated.mkdir();(populated/'keep').write_bytes(b'keep')
            r=self.cli('restore-tree','--source',src,'--destination',populated)
            self.assertNotEqual(r.returncode,0)
            self.assertEqual(sorted(x.name for x in populated.iterdir()),['keep'])
            hidden=root/'hidden';hidden.mkdir();(hidden/'.hidden').write_bytes(b'x')
            self.assertNotEqual(self.cli('restore-tree','--source',src,'--destination',hidden).returncode,0)
            self.assertEqual(sorted(x.name for x in hidden.iterdir()),['.hidden'])
            missing=root/'missing'
            self.assertNotEqual(self.cli('restore-tree','--source',src,'--destination',missing).returncode,0)
            self.assertFalse(missing.exists())
            inside=src/'inside';inside.mkdir()
            self.assertNotEqual(self.cli('restore-tree','--source',src,'--destination',inside).returncode,0)
            self.assertEqual(list(inside.iterdir()),[])
            self.assertNotEqual(self.cli('restore-tree','--source',src,'--destination',src).returncode,0)

    def test_restore_tree_failure_removes_only_its_own_entries(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);src=root/'source';src.mkdir()
            (src/'a').write_bytes(b'one');(src/'b').write_bytes(b'two')
            mount=root/'mount';mount.mkdir()
            spec=importlib.util.spec_from_file_location('exchange_under_test',MODULE)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            real=module.shutil.copyfileobj;calls=[]
            def failing(inp,out,size=0):
                calls.append(1)
                if len(calls)==2:raise OSError('synthetic mid-copy failure')
                return real(inp,out,size)
            module.shutil.copyfileobj=failing
            try:
                with self.assertRaises(OSError):module.restore_tree(src,mount)
            finally:module.shutil.copyfileobj=real
            self.assertTrue(mount.is_dir());self.assertEqual(list(mount.iterdir()),[])

    def test_restore_tree_rejects_dotdot_nesting_before_any_copy(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);src=root/'source';src.mkdir();(src/'a').write_bytes(b'one')
            (src/'inside').mkdir()
            spec=importlib.util.spec_from_file_location('exchange_dotdot',MODULE)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            real=module.shutil.copyfileobj;calls=[]
            def counting(inp,out,size=0):
                calls.append(1);return real(inp,out,size)
            module.shutil.copyfileobj=counting
            try:
                with self.assertRaises(Exception):
                    module.restore_tree(src,root/'elsewhere'/'..'/'source'/'inside')
            finally:module.shutil.copyfileobj=real
            self.assertEqual(calls,[])
            self.assertEqual(list((src/'inside').iterdir()),[])

    def test_restore_tree_rejects_a_directory_link_destination(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);src=root/'source';src.mkdir();(src/'a').write_bytes(b'one')
            real_dir=root/'real';real_dir.mkdir();link=root/'link'
            if os.name=='nt':
                made=subprocess.run(['cmd.exe','/c','mklink','/J',str(link),str(real_dir)],capture_output=True)
                self.assertEqual(made.returncode,0,made.stderr)
            else:
                os.symlink(real_dir,link)
            try:
                r=self.cli('restore-tree','--source',src,'--destination',link)
                self.assertNotEqual(r.returncode,0)
                self.assertEqual(list(real_dir.iterdir()),[])
            finally:
                if os.name=='nt': os.rmdir(link)
                else: link.unlink()

    def test_restore_tree_failure_rolls_back_nested_directories_too(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);src=root/'source';src.mkdir()
            (src/'d1'/'d2').mkdir(parents=True);(src/'d1'/'d2'/'x').write_bytes(b'one')
            (src/'d1'/'y').write_bytes(b'two');(src/'z').write_bytes(b'three')
            mount=root/'mount';mount.mkdir()
            spec=importlib.util.spec_from_file_location('exchange_nested',MODULE)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            real=module.shutil.copyfileobj;calls=[]
            def failing(inp,out,size=0):
                calls.append(1)
                if len(calls)==3:raise OSError('synthetic mid-copy failure')
                return real(inp,out,size)
            module.shutil.copyfileobj=failing
            try:
                with self.assertRaises(OSError):module.restore_tree(src,mount)
            finally:module.shutil.copyfileobj=real
            self.assertTrue(mount.is_dir());self.assertEqual(list(mount.iterdir()),[])

    def test_capture_child_is_exclusive_and_requires_successful_structured_output(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);out=root/'result.json'
            # Real sibling child; SQL emission is offline and never executes PostgreSQL.
            args=('call','--helper','multistore_speckle','--stdout-file',out,'--','postgres-sql','--directory',root/'sql')
            r=self.cli(*args)
            self.assertEqual(r.returncode,0,r.stderr)
            value=json.loads(out.read_bytes())
            self.assertIs(value['verified'],True)
            self.assertIs(value['nativeRecoveryProven'],False)
            before=out.read_bytes()
            self.assertNotEqual(self.cli(*args).returncode,0)
            self.assertEqual(out.read_bytes(),before)
            bad=self.cli('call','--helper','not-an-allowed-helper','--stdout-file',root/'bad.json')
            self.assertNotEqual(bad.returncode,0)
            self.assertFalse((root/'bad.json').exists())

    def test_copy_file_uses_exact_hash_and_never_overwrites(self):
        import hashlib
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            root=Path(tmp);src=root/'source';src.write_bytes(b'ciphertext-fixture')
            dst=root/'dest';h=hashlib.sha256(src.read_bytes()).hexdigest()
            self.assertNotEqual(self.cli('copy','--source',src,'--destination',dst,'--sha256','0'*64).returncode,0)
            self.assertFalse(dst.exists())
            self.assertEqual(self.cli('copy','--source',src,'--destination',dst,'--sha256',h).returncode,0)
            self.assertNotEqual(self.cli('copy','--source',src,'--destination',dst,'--sha256',h).returncode,0)
            self.assertEqual(dst.read_bytes(),src.read_bytes())

    def test_initialize_private_new_exchange_and_no_clobber(self):
        self.assertTrue(MODULE.is_file(), 'executable exchange helper missing')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as tmp:
            p=Path(tmp)/'exchange'
            r=self.cli('init','--root',p)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertTrue(json.loads(r.stdout)['verified'])
            self.assertEqual({x.name for x in (p/'exports').iterdir()}, {'api','key-references','minio','n8n','neo4j','postgres'})
            marker=p/'keep';marker.write_bytes(b'keep')
            self.assertNotEqual(self.cli('init','--root',p).returncode,0)
            self.assertEqual(marker.read_bytes(),b'keep')

if __name__ == '__main__': unittest.main()
