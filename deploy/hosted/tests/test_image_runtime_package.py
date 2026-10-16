"""Offline image-runtime package tests; never start Docker or services."""
import importlib.util
import tempfile
import zipfile
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
MODULE = HERE / 'build_image_runtime.py'


class RuntimeModelTests(unittest.TestCase):
    def test_rehashed_extra_support_and_typed_model_refused(self):
        import build_image_runtime as module
        with tempfile.TemporaryDirectory(prefix='dg-runtime-verify-', dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as tmp:
            base = Path(tmp)
            source = base / 'runtime.zip'
            module.prepare('C:/Users/Admin/Downloads/DG-controlled-build-c82b92b-v2.zip', source)
            with zipfile.ZipFile(source) as archive:
                original = {n: archive.read(n) for n in archive.namelist()}
            import json
            for case in ('extra', 'typed', 'source'):
                payload = dict(original)
                manifest = json.loads(payload['image-runtime-manifest.json'])
                if case == 'extra':
                    payload['support/unreviewed.py'] = b'not authorized'
                    manifest['files']['support/unreviewed.py'] = module.sha(payload['support/unreviewed.py'])
                elif case == 'typed':
                    model = json.loads(payload['compose.json'])
                    model['services']['neo4j']['cpus'] = True
                    payload['compose.json'] = module.encoded(model)
                    manifest['files']['compose.json'] = module.sha(payload['compose.json'])
                else:
                    payload['source/ui-v2/src/main.jsx'] = b'modified input'
                    manifest['files']['source/ui-v2/src/main.jsx'] = module.sha(payload['source/ui-v2/src/main.jsx'])
                payload['image-runtime-manifest.json'] = module.encoded(manifest)
                target = base / (case + '.zip')
                with zipfile.ZipFile(target, 'w') as archive:
                    for name, value in payload.items():
                        archive.writestr(name, value)
                with self.subTest(case=case), self.assertRaises(ValueError):
                    module.verify(target)

    def test_four_image_model_has_no_build_ports_or_external_network(self):
        self.assertTrue(MODULE.is_file(), 'image runtime packager is not implemented')
        spec = importlib.util.spec_from_file_location('build_image_runtime', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        images = {name: {'imageId': 'sha256:' + str(i) * 64}
                  for i, name in enumerate(('neo4j', 'dg-reasoner', 'data-service', 'design-grammars'), 1)}
        model = module.runtime_model(images)
        self.assertEqual(set(model['services']), set(images))
        self.assertEqual(model['networks'], {'sandbox': {'internal': True, 'enable_ipv6': False}})
        for name, service in model['services'].items():
            self.assertEqual(service['image'], images[name]['imageId'])
            self.assertEqual(service['pull_policy'], 'never')
            self.assertEqual(service['networks'], ['sandbox'])
            self.assertFalse(set(service) & {'build', 'ports', 'container_name', 'privileged', 'extra_hosts'})
            self.assertEqual(service['restart'], 'no')
            self.assertIn('mem_limit', service)
            for mount in service.get('volumes', []):
                if mount['type'] == 'bind':
                    self.assertTrue(mount['read_only'])
                    self.assertFalse(mount['bind']['create_host_path'])
                    self.assertNotEqual(mount['target'], '/mnt/repo')
        self.assertEqual(model['services']['data-service']['environment']['DG_REASONER_URL'], 'http://dg-reasoner:8000')
        self.assertEqual(model['services']['data-service']['depends_on']['neo4j']['condition'], 'service_healthy')


if __name__ == '__main__':
    unittest.main()
