"""Offline two-store recovery model and package contracts; no daemon."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))


class PackageTests(unittest.TestCase):
    def module(self):
        path = HERE / 'build_recovery_test.py'
        self.assertTrue(path.is_file(), 'recovery packager missing')
        spec = importlib.util.spec_from_file_location('build_recovery_test', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_model_is_two_store_no_ingress_and_helpers_bounded(self):
        module = self.module()
        for destination in (False, True):
            model = module.model(destination=destination)
            self.assertEqual(set(model['services']), {'neo4j', 'data-service', 'graph-admin', 'snapshot'})
            self.assertEqual(model['networks'], {'sandbox': {'internal': True, 'enable_ipv6': False}})
            self.assertEqual(set(model['volumes']), {'graph', 'api_state', 'exchange', 'graph_logs'})
            for name, service in model['services'].items():
                self.assertFalse(set(service) & {'build', 'ports', 'privileged', 'container_name'})
                self.assertEqual(service['pull_policy'], 'never')
                self.assertEqual(service['restart'], 'no')
                self.assertLessEqual(service['cpus'], 1)
                self.assertIn(service['image'], module.IMAGE_IDS.values())
            snapshot = model['services']['snapshot']
            state = next(m for m in snapshot['volumes'] if m['target'] == '/state')
            self.assertEqual(state.get('read_only', False), not destination)
            admin = model['services']['graph-admin']
            self.assertEqual(admin['network_mode'], 'none')
            self.assertEqual(snapshot['network_mode'], 'none')
            self.assertNotIn('networks', admin)
            self.assertNotIn('networks', snapshot)

    def test_rehashed_identity_and_extra_support_rejected(self):
        import tempfile
        import zipfile
        runtime = Path('C:/Users/Admin/Downloads/DG-image-runtime-c82b92b-v2.zip')
        module = self.module()
        with tempfile.TemporaryDirectory(dir='C:/Users/Admin/AppData/Local/hermes/cache/scratch') as tmp:
            path = Path(tmp) / 'base.zip'
            module.prepare(runtime, path)
            with zipfile.ZipFile(path) as archive:
                original = {n: archive.read(n) for n in archive.namelist()}
            for key, value in (('schemaVersion', True), ('target', 'other'),
                               ('toolingStatus', 'committed-product-source')):
                payload = dict(original)
                manifest = json.loads(payload['recovery-manifest.json'])
                manifest[key] = value
                payload['recovery-manifest.json'] = module.encoded(manifest)
                changed = Path(tmp) / (key + '.zip')
                with zipfile.ZipFile(changed, 'w') as archive:
                    for name, data in payload.items():
                        archive.writestr(name, data)
                with self.subTest(key=key), self.assertRaises(ValueError):
                    module.verify(changed)

    def test_exact_images_are_from_verified_source(self):
        module = self.module()
        self.assertEqual(module.REVISION, 'c82b92b29423c515e353e3fa4f9c17e9b0d83438')
        self.assertEqual(module.IMAGE_IDS['neo4j'], 'sha256:0efd832ad89fcc0526e80abf8b26bb79f196ebe87eac655c6f19c08c5be766b8')
        self.assertEqual(module.IMAGE_IDS['data-service'], 'sha256:9787e347b10eb8303498fed9e79651b89a3a1d4f62501ee98e51f6f25d0b22d1')


if __name__ == '__main__':
    unittest.main()
