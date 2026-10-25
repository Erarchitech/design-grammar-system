"""Immutable candidate + actual Windows PowerShell 5.1 lifecycle tests (no Docker)."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
REPO = HERE.parents[1]
LANE = Path('C:/Users/Admin/AppData/Local/hermes/cache/scratch/dg-1309-offline-continuation/end-to-end-release/packaging-lane')
AGE = Path('C:/Users/Admin/AppData/Local/hermes/cache/scratch/multistore-age121')
PS5 = Path('C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe')
sys.path.insert(0, str(HERE))


class PackageTests(unittest.TestCase):
    def module(self):
        path = HERE / 'build_multistore_package.py'
        self.assertTrue(path.is_file(), 'immutable multi-store packager missing')
        spec = importlib.util.spec_from_file_location('multistore_package', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_package_v2_omits_api_snapshot_and_generates_current_age_inventory(self):
        m = self.module()
        import tempfile
        snapshot = 'provenance/age/github-release-v1.2.1.json'
        self.assertNotIn(snapshot, m.AGE_FILES,
                         'mutable GitHub API bytes must not be a required package input')
        with tempfile.TemporaryDirectory(dir=LANE) as tmp:
            age = Path(tmp)
            # Copy only the ten pinned inputs, not historical delivery metadata.
            for origin, pin in m.AGE_FILES.values():
                self.assertRegex(pin, r'^[0-9a-f]{64}$')
                target = age / origin
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((AGE / origin).read_bytes())
            payload = m.build_payload(REPO, age)
            self.assertNotIn(snapshot, payload)
            manifest = json.loads(payload[m.MANIFEST])
            self.assertEqual(manifest['schemaVersion'], 2)
            self.assertEqual(manifest['ageTrust']['verificationEvidence'],
                             'historical-pinned-report-not-reverified')
            delivery = json.loads(payload['provenance/age/delivery-manifest.json'])
            self.assertEqual(set(delivery), {'schemaVersion', 'kind', 'files', 'verificationEvidence'})
            self.assertEqual(delivery['schemaVersion'], 2)
            self.assertEqual(delivery['kind'], 'current-package-age-inputs-not-historical-delivery')
            self.assertEqual(delivery['verificationEvidence'], 'historical-pinned-report-not-reverified')
            self.assertEqual(delivery['files'], {name: m.sha(payload[name]) for name in m.AGE_FILES})
            # Even present, fresh observation/old delivery files are not read or enrolled.
            (age / 'github-release-v1.2.1.json').write_bytes(b'fresh observation; not historical')
            (age / 'delivery-manifest.json').write_bytes(b'historical delivery; not current inventory')
            self.assertEqual(m.build_payload(REPO, age), payload)
            package = age / 'candidate.zip'
            digest = m.write_package(payload, package)
            self.assertEqual(m.verify(package, REPO, age), digest)

    def test_all_age_pins_remain_mandatory_and_tamper_rejected(self):
        m = self.module()
        import tempfile
        from unittest.mock import patch
        original = m.regular_bytes
        self.assertEqual(len(m.AGE_FILES), 10)
        for name, (origin, pin) in m.AGE_FILES.items():
            self.assertRegex(pin, r'^[0-9a-f]{64}$')
            target = AGE / origin
            def changed(path):
                data = original(path)
                return data + b'changed' if Path(path) == target else data
            with self.subTest(member=name), patch.object(m, 'regular_bytes', changed):
                with self.assertRaisesRegex(ValueError, 'age input pin'):
                    m.build_payload(REPO, AGE)
            def missing(path):
                if Path(path) == target:
                    raise FileNotFoundError('required pinned age input absent')
                return original(path)
            with self.subTest(missing=name), patch.object(m, 'regular_bytes', missing):
                with self.assertRaises(FileNotFoundError):
                    m.build_payload(REPO, AGE)

    def test_ps5_rejects_rehashed_wrong_age_inventory_and_evidence_labels(self):
        m = self.module()
        import tempfile
        import zipfile
        with tempfile.TemporaryDirectory(dir=LANE) as tmp:
            folder = Path(tmp)
            original = m.build_payload(REPO, AGE)
            for label in ('inventory', 'evidence', 'schema-v1', 'binary-rehashed', 'provenance-rehashed', 'api-extra'):
                with self.subTest(label=label):
                    payload = dict(original)
                    manifest = json.loads(payload[m.MANIFEST])
                    if label.endswith('-rehashed'):
                        name = ('tools/age' if label == 'binary-rehashed'
                                else 'provenance/age/signature-verification.json')
                        payload[name] += b'changed'
                        digest = m.sha(payload[name])
                        manifest['files'][name] = digest
                        manifest['preparationFiles'][name] = digest
                        delivery_name = 'provenance/age/delivery-manifest.json'
                        delivery = json.loads(payload[delivery_name])
                        delivery['files'][name] = digest
                        payload[delivery_name] = m.encoded(delivery)
                        manifest['files'][delivery_name] = m.sha(payload[delivery_name])
                        manifest['preparationFiles'][delivery_name] = m.sha(payload[delivery_name])
                    elif label == 'inventory':
                        name = 'provenance/age/delivery-manifest.json'
                        delivery = json.loads(payload[name])
                        delivery['files']['tools/age'] = '0' * 64
                        payload[name] = m.encoded(delivery)
                        manifest['files'][name] = m.sha(payload[name])
                        manifest['preparationFiles'][name] = m.sha(payload[name])
                    elif label == 'evidence':
                        manifest['ageTrust']['verificationEvidence'] = 'fresh-verification'
                    elif label == 'schema-v1':
                        manifest['schemaVersion'] = 1
                    else:
                        name = 'provenance/age/github-release-v1.2.1.json'
                        payload[name] = b'optional observation must stay outside package'
                        manifest['files'][name] = m.sha(payload[name])
                        manifest['preparationFiles'][name] = m.sha(payload[name])
                    payload[m.MANIFEST] = m.encoded(manifest)
                    package = folder / (label + '.zip')
                    digest = m.write_package(payload, package)
                    with self.assertRaises(ValueError):
                        m.verify(package, REPO, AGE)
                    root = folder / (label + '-extracted')
                    with zipfile.ZipFile(package) as archive:
                        archive.extractall(root)
                    proc, report = self.run_owner(root, package, digest, folder / (label + '-result'))
                    self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                    self.assertEqual(report['failureStage'], 'package-preflight')

    def test_runtime_n8n_helper_imports_from_flat_packaged_support(self):
        import os
        import shutil
        import tempfile
        with tempfile.TemporaryDirectory(dir=LANE) as tmp:
            support=Path(tmp)/'support';support.mkdir()
            for name,origin in self.module().SUPPORT.items():
                if name.endswith('.py'):
                    shutil.copyfile(HERE/origin,support/name)
            # Every packaged helper must resolve sibling adapter imports without
            # repository PYTHONPATH. --bad-mode fails sanitized, not ImportError.
            env={'SystemRoot':os.environ['SystemRoot'],'PATH':str(Path(sys.executable).parent)}
            p=subprocess.run([sys.executable,'-B',str(support/'multistore_n8n.py'),'--bad-mode'],
                             cwd=tmp,env=env,capture_output=True,timeout=30)
            self.assertEqual(p.returncode,1)
            self.assertEqual(p.stderr.strip(),b'n8n recovery check failed')
            self.assertEqual(p.stdout,b'')
            fixture=Path(tmp)/'fixture'
            good=subprocess.run([sys.executable,'-B',str(support/'multistore_n8n.py'),
                                 'prepare','--exchange',str(fixture)],
                                cwd=tmp,env=env,capture_output=True,timeout=30)
            self.assertEqual(good.returncode,0,good.stderr)
            self.assertEqual(json.loads(good.stdout),
                             {'fixturePrepared':True,'nativeRecoveryProven':False})
            self.assertEqual(good.stderr,b'')
            self.assertEqual({p.name for p in fixture.iterdir()},
                             {'credentials.json','workflow.json','fixture-state.json'})

    def test_function_slice_rejects_reversed_or_duplicate_markers(self):
        m = self.module()
        from unittest.mock import patch
        original = m.regular_bytes
        for malformed in (b'$root = [IO.Path]\nfunction Assert-True {}\n',
                          b'function Assert-True {}\nfunction Assert-True {}\n$root = [IO.Path]\n'):
            def read(path):
                if Path(path).name == 'Run-ImageRuntime.ps1':
                    return malformed
                return original(path)
            with self.subTest(raw=malformed), patch.object(m, 'regular_bytes', read):
                with self.assertRaisesRegex(ValueError, 'function slice'):
                    m.build_payload(REPO, AGE)

    def test_complete_store_helpers_and_fixed_source_binding_are_packaged_exactly(self):
        m = self.module()
        payload = m.build_payload(REPO, AGE)
        expected = {
            'support/multistore_qualified_app.py': 'recovery-test/multistore_qualified_app.py',
            'support/multistore_qualified_queue.py': 'recovery-test/multistore_qualified_queue.py',
            'support/speckle-physical-contract.json': 'recovery-test/speckle-physical-contract.json',
            'support/multistore_speckle.py': 'recovery-test/multistore_speckle.py',
            'support/multistore_exchange.py': 'recovery-test/multistore_exchange.py',
            'support/speckle-source-binding.json': 'recovery-test/speckle-source-binding.json',
        }
        for member, origin in expected.items():
            with self.subTest(member=member):
                self.assertIn(member, payload)
                self.assertEqual(payload.get(member), (HERE / origin).read_bytes())

    def test_source_is_187_exact_git_blobs_with_preparation_product_equivalence(self):
        m = self.module()
        payload = m.product_source(REPO)
        manifest = json.loads(payload.pop('source/manifest.json'))
        self.assertEqual(len(payload), 187)
        self.assertEqual(manifest['frameworkRevision'], m.PREPARATION_BASE)
        self.assertEqual(manifest['productRevision'], m.PRODUCT_REVISION)
        from build_multistore_test import verify_product_source
        self.assertEqual(verify_product_source(REPO, m.PRODUCT_REVISION,
                         {n[7:]: b for n, b in payload.items()}), 187)
        self.assertEqual(set(manifest['files']), {n[7:] for n in payload})

    def test_production_builder_requires_complete_orchestration_before_writing(self):
        m = self.module()
        import tempfile
        from unittest.mock import patch
        LANE.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=LANE) as tmp:
            folder = Path(tmp)
            (folder / 'recovery-test').mkdir()
            (folder / 'recovery-test/multistore_orchestrator.ps1').write_text(
                '# function-only but incomplete preparation\nfunction Get-MultiContainer {}\n')
            with patch.object(m, 'HERE', folder), self.assertRaisesRegex(ValueError, 'orchestrat'):
                m.prepare(REPO, folder / 'blocked.zip', AGE)
            self.assertFalse((folder / 'blocked.zip').exists())

    def test_main_function_name_alone_cannot_unblock_production_without_reviewed_profile(self):
        m = self.module()
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=LANE) as tmp:
            folder = Path(tmp)
            (folder / 'recovery-test').mkdir()
            (folder / 'recovery-test/multistore_orchestrator.ps1').write_text(
                'function Invoke-MultiStoreExercise($Root,$Output,$Job,$Scope,$Report) {}\n')
            with patch.object(m, 'HERE', folder), patch.object(m, 'build_payload', return_value={'synthetic.txt': b'not production'}) as build:
                with self.assertRaisesRegex(ValueError, 'reviewed runtime profile'):
                    m.prepare(REPO, folder / 'blocked.zip', AGE)
                build.assert_not_called()
            self.assertFalse((folder / 'blocked.zip').exists())

    def lifecycle_package(self, m, output):
        """Direct candidate-byte writer; NOT production admission or native-ready."""
        return m.write_package(m.build_payload(REPO, AGE), output)

    def fixture(self, m, folder):
        """Labelled lifecycle synthetic only; never a production orchestration."""
        import shutil
        tools = folder / 'preparation'
        tools.mkdir()
        for name in ('recovery-test', 'image-runtime', 'sandbox'):
            shutil.copytree(HERE / name, tools / name, ignore=shutil.ignore_patterns('__pycache__'))
        for name in HERE.glob('recovery_*.py'):
            shutil.copyfile(name, tools / name.name)
        (tools / 'recovery-test/multistore_orchestrator.ps1').write_text(
            '# LIFECYCLE SYNTHETIC; not native qualification or production provenance.\n'
            'function Invoke-MultiStoreExercise($Root,$Output,$Job,$Scope,$Report) {\n'
            ' throw "LIFECYCLE_SYNTHETIC_MUST_NOT_RUN"\n}\n', encoding='utf-8')
        return tools

    def test_deterministic_exact_package_and_extracted_ps5_default_without_docker(self):
        m = self.module()
        import tempfile
        import zipfile
        from unittest.mock import patch
        self.assertTrue(PS5.is_file(), 'required real PS5 absent')
        LANE.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=LANE) as tmp:
            folder = Path(tmp)
            tools = self.fixture(m, folder)
            with patch.object(m, 'HERE', tools):
                one, two = folder / 'one.zip', folder / 'two.zip'
                digest = self.lifecycle_package(m, one)
                self.assertEqual(self.lifecycle_package(m, two), digest)
                self.assertEqual(m.verify(one, REPO, AGE), digest)
            root = folder / 'extracted'
            with zipfile.ZipFile(one) as archive:
                archive.extractall(root)
            output = folder / 'result'
            cmd = [str(PS5), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                   '-File', str(root / 'support/Invoke-OwnerMultiStore.ps1'),
                   '-PackageZip', str(one), '-ExpectedZipSha256', digest,
                   '-OutputDirectory', str(output)]
            proc = subprocess.run(cmd, capture_output=True, text=True, errors='replace', timeout=90)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            report = json.loads((output / 'multistore-report.json').read_bytes())
            self.assertEqual(report['status'], 'PACKAGE_PREFLIGHT_COMPLETE')
            self.assertIs(report['dockerInvoked'], False)
            self.assertIs(report['releaseAccepted'], False)
            self.assertEqual(json.loads((output / 'process-exit.json').read_bytes())['processExitCode'], 0)
            self.assertEqual(len(json.loads((root / 'source/manifest.json').read_bytes())['files']), 187)

    def run_owner(self, root, package, digest, output, *extra):
        proc = subprocess.run([str(PS5), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                    '-File', str(root / 'support/Invoke-OwnerMultiStore.ps1'), '-PackageZip', str(package),
                    '-ExpectedZipSha256', digest, '-OutputDirectory', str(output), *extra],
                    capture_output=True, text=True, errors='replace', timeout=90)
        report = json.loads((output / 'multistore-report.json').read_bytes())
        record = json.loads((output / 'process-exit.json').read_bytes())
        self.assertEqual(record['processExitCode'], proc.returncode)
        self.assertIs(report['dockerInvoked'], False)
        return proc, report

    def test_ps5_rehashed_extra_member_rejected_before_support_import(self):
        m = self.module()
        import tempfile
        import zipfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=LANE) as tmp:
            folder = Path(tmp)
            tools = self.fixture(m, folder)
            with patch.object(m, 'HERE', tools):
                payload = m.build_payload(REPO, AGE)
            payload['support/injected.ps1'] = b'throw "must not be imported"\n'
            manifest = json.loads(payload[m.MANIFEST])
            manifest['files']['support/injected.ps1'] = m.sha(payload['support/injected.ps1'])
            manifest['preparationFiles']['support/injected.ps1'] = m.sha(payload['support/injected.ps1'])
            payload[m.MANIFEST] = m.encoded(manifest)
            package = folder / 'rehashed-extra.zip'
            digest = m.write_package(payload, package)
            root = folder / 'extracted'
            with zipfile.ZipFile(package) as archive:
                archive.extractall(root)
            proc, report = self.run_owner(root, package, digest, folder / 'result')
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(report['failureStage'], 'package-preflight')

    def test_builder_rejects_rehashed_source_and_support_against_exact_build_inputs(self):
        m = self.module()
        import tempfile
        import zipfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=LANE) as tmp:
            folder = Path(tmp)
            tools = self.fixture(m, folder)
            with patch.object(m, 'HERE', tools):
                original = m.build_payload(REPO, AGE)
                for index, name in enumerate(('source/data-service/Dockerfile', 'support/multistore_native.py', 'source-compose.json')):
                    payload = dict(original)
                    payload[name] += b'\n'
                    manifest = json.loads(payload[m.MANIFEST])
                    manifest['files'][name] = m.sha(payload[name])
                    if name in manifest['preparationFiles']:
                        manifest['preparationFiles'][name] = m.sha(payload[name])
                    payload[m.MANIFEST] = m.encoded(manifest)
                    package = folder / ('mutated-%s.zip' % index)
                    m.write_package(payload, package)
                    with self.subTest(name=name), self.assertRaises(ValueError):
                        m.verify(package, REPO, AGE)

    def test_zip_safety_names_limits_case_and_links(self):
        m = self.module()
        import tempfile
        import zipfile
        from unittest.mock import patch
        for name in ('../escape', '/absolute', 'C:/ads', 'support/NUL.txt', 'support/a.',
                     'support/a\\b', 'support/.env', 'support/x:ads'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                m.check_payload({name: b'x'})
        with self.assertRaises(ValueError):
            m.check_payload({'A.txt': b'x', 'a.txt': b'y'})
        with patch.object(m, 'MAX_TOTAL', 2), self.assertRaises(ValueError):
            m.check_payload({'a.txt': b'xxx'})
        with patch.object(m, 'MAX_FILE', 1), self.assertRaises(ValueError):
            m.check_payload({'a.txt': b'xx'})
        with patch.object(m, 'MAX_FILES', 1), self.assertRaises(ValueError):
            m.check_payload({'a.txt': b'', 'b.txt': b''})
        with tempfile.TemporaryDirectory(dir=LANE) as tmp:
            folder = Path(tmp)
            tools = self.fixture(m, folder)
            with patch.object(m, 'HERE', tools):
                payload = m.build_payload(REPO, AGE)
                for label, attribute, duplicate in [('link', 0o120777 << 16, False),
                                                    ('case', 0o100644 << 16, True)]:
                    package = folder / (label + '.zip')
                    with zipfile.ZipFile(package, 'w') as archive:
                        for name, data in payload.items():
                            info = zipfile.ZipInfo(name)
                            info.external_attr = attribute if name == 'support/probe.py' else 0o100644 << 16
                            archive.writestr(info, data)
                        if duplicate:
                            archive.writestr('SUPPORT/PROBE.PY', b'case alias')
                    with self.subTest(label=label), self.assertRaises(ValueError):
                        m.verify(package, REPO, AGE)

    def test_ps5_tamper_wrong_pin_missing_scope_rehashed_source_and_ads_fail_closed(self):
        m = self.module()
        import tempfile
        import zipfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=LANE) as tmp:
            folder = Path(tmp)
            tools = self.fixture(m, folder)
            with patch.object(m, 'HERE', tools):
                original = m.build_payload(REPO, AGE)
            for label in ('tamper', 'extra', 'wrong-pin', 'scope-missing', 'source-rehashed', 'ads', 'junction', 'hardlink'):
                with self.subTest(label=label):
                    payload = dict(original)
                    if label == 'source-rehashed':
                        name = 'source/data-service/Dockerfile'
                        payload[name] += b'\n# altered source\n'
                        source = json.loads(payload['source/manifest.json'])
                        source['files'][name[7:]] = m.sha(payload[name])
                        payload['source/manifest.json'] = m.encoded(source)
                        manifest = json.loads(payload[m.MANIFEST])
                        for key in (name, 'source/manifest.json'):
                            manifest['files'][key] = m.sha(payload[key])
                        manifest['sourceManifestSha256'] = m.sha(payload['source/manifest.json'])
                        payload[m.MANIFEST] = m.encoded(manifest)
                    package = folder / (label + '.zip')
                    digest = m.write_package(payload, package)
                    root = folder / (label + '-extracted')
                    with zipfile.ZipFile(package) as archive:
                        archive.extractall(root)
                    if label == 'tamper':
                        (root / 'support/runtime-functions.ps1').write_bytes(b'throw "MUST_NOT_IMPORT"\n')
                    elif label == 'extra':
                        (root / 'support/extra.txt').write_bytes(b'not in zip')
                    elif label == 'wrong-pin':
                        digest = '0' * 64
                    elif label == 'ads':
                        Path(str(root / 'support/probe.py') + ':unlisted').write_bytes(b'not a default stream')
                    elif label == 'hardlink':
                        import os
                        victim = root / 'support/probe.py'
                        victim.unlink()
                        os.link(tools / 'recovery-test/probe.py', victim)
                    elif label == 'junction':
                        link = root / 'support/unlisted-junction'
                        linked = subprocess.run(['cmd.exe', '/c', 'mklink', '/J', str(link), str(tools)], capture_output=True)
                        self.assertEqual(linked.returncode, 0, linked.stderr)
                    extra = ('-RunNativeMultiStore',) if label == 'scope-missing' else ()
                    try:
                        proc, report = self.run_owner(root, package, digest, folder / (label + '-result'), *extra)
                        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                        self.assertEqual(report['status'], 'FAILED')
                        self.assertEqual(report['failureStage'], 'external-scope' if label == 'scope-missing' else 'package-preflight')
                    finally:
                        if label == 'junction':
                            link.rmdir()

    def test_production_cli_missing_orchestration_is_blocked_no_zip(self):
        m = self.module()
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=LANE) as tmp:
            folder = Path(tmp)
            (folder / 'recovery-test').mkdir()
            with patch.object(m, 'HERE', folder):
                self.assertEqual(m.main(['--repo', str(REPO), '--age-directory', str(AGE),
                                         '--output', str(folder / 'blocked.zip')]), 1)
            self.assertFalse((folder / 'blocked.zip').exists())

    def test_ps5_output_no_clobber_inside_root_and_wrapper_preserves_nonzero(self):
        m = self.module()
        import tempfile
        import zipfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=LANE) as tmp:
            folder = Path(tmp)
            tools = self.fixture(m, folder)
            with patch.object(m, 'HERE', tools):
                payload = m.build_payload(REPO, AGE)
            package = folder / 'candidate.zip'
            digest = m.write_package(payload, package)
            root = folder / 'extracted'
            with zipfile.ZipFile(package) as archive:
                archive.extractall(root)
            output = root / 'must-not-create'
            proc = subprocess.run([str(PS5), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                        '-File', str(root / 'support/Run-MultiStore.ps1'), '-PackageZip', str(package),
                        '-ExpectedZipSha256', digest, '-OutputDirectory', str(output)],
                        capture_output=True, timeout=30)
            self.assertEqual(proc.returncode, 1)
            self.assertFalse(output.exists())
            output = folder / 'existing-output'
            output.mkdir()
            sentinel = output / 'sentinel.txt'
            sentinel.write_bytes(b'preserve')
            proc = subprocess.run([str(PS5), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                        '-File', str(root / 'support/Invoke-OwnerMultiStore.ps1'), '-PackageZip', str(package),
                        '-ExpectedZipSha256', digest, '-OutputDirectory', str(output)],
                        capture_output=True, timeout=30)
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(sentinel.read_bytes(), b'preserve')
            self.assertEqual(list(output.iterdir()), [sentinel])
            child = folder / 'failing-child.ps1'
            child.write_text('param($PackageZip,$ExpectedZipSha256,$OutputDirectory)\n'
                             '[void][IO.Directory]::CreateDirectory($OutputDirectory)\nexit 37\n')
            failed = folder / 'failed-child'
            proc = subprocess.run([str(PS5), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                        '-File', str(root / 'support/Invoke-OwnerMultiStore.ps1'), '-Runner', str(child),
                        '-PackageZip', str(package), '-ExpectedZipSha256', digest, '-OutputDirectory', str(failed)],
                        capture_output=True, timeout=30)
            self.assertEqual(proc.returncode, 37)
            self.assertEqual(json.loads((failed / 'process-exit.json').read_bytes())['processExitCode'], 37)

    def test_zip_output_parent_traversal_cannot_enter_repository(self):
        m = self.module()
        from contextlib import chdir
        import tempfile
        from unittest.mock import patch
        LANE.mkdir(parents=True, exist_ok=True)
        for style in ('absolute', 'relative', 'mixed-separators'):
            for existing in (False, True):
                with self.subTest(style=style, existing=existing), tempfile.TemporaryDirectory(dir=LANE) as tmp:
                    folder = Path(tmp)
                    repository = folder / 'repository'
                    sibling = folder / 'sibling'
                    repository.mkdir()
                    sibling.mkdir()
                    (repository / 'marker.txt').write_bytes(b'protected repository')
                    (sibling / 'marker.txt').write_bytes(b'protected sibling')
                    candidate = repository / 'candidate.zip'
                    if existing:
                        candidate.write_bytes(b'existing artifact')

                    def snapshot():
                        return {p.relative_to(folder).as_posix(): (
                            p.is_dir(), p.stat().st_mtime_ns,
                            None if p.is_dir() else p.read_bytes())
                            for p in (folder, *folder.rglob('*'))}

                    destination = Path('sibling/../repository/candidate.zip')
                    if style == 'absolute':
                        destination = folder / destination
                    elif style == 'mixed-separators':
                        destination = str(folder) + '/sibling\\../repository/candidate.zip'
                    with chdir(folder), patch.object(m, 'REPO', repository):
                        self.assertNotIn(repository, Path(destination).absolute().parents)
                        self.assertEqual(Path(destination).resolve(), candidate)
                        before = snapshot()
                        with self.assertRaisesRegex(ValueError, 'new external destination required'):
                            m.write_package({'fixture.txt': b'offline synthetic only'}, destination)
                        self.assertEqual(candidate.exists(), existing)
                        self.assertEqual(snapshot(), before)

    def test_zip_output_genuine_external_destination_remains_exclusive(self):
        m = self.module()
        import tempfile
        import zipfile
        from unittest.mock import patch
        LANE.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=LANE) as tmp:
            folder = Path(tmp)
            repository = folder / 'repository'
            sibling = folder / 'sibling'
            repository.mkdir()
            sibling.mkdir()
            marker = repository / 'marker.txt'
            marker.write_bytes(b'protected repository')
            output = sibling / 'candidate.zip'
            payload = {'fixture.txt': b'offline synthetic only'}
            with patch.object(m, 'REPO', repository):
                digest = m.write_package(payload, output)
                original = output.read_bytes()
                self.assertEqual(digest, m.sha(original))
                with zipfile.ZipFile(output) as archive:
                    self.assertIsNone(archive.testzip())
                    self.assertEqual(archive.namelist(), ['fixture.txt'])
                    self.assertEqual(archive.read('fixture.txt'), payload['fixture.txt'])
                with self.assertRaisesRegex(ValueError, 'new external destination required'):
                    m.write_package({'other.txt': b'must not overwrite'}, output)
                self.assertEqual(output.read_bytes(), original)
            self.assertEqual(marker.read_bytes(), b'protected repository')
            self.assertEqual(list(repository.iterdir()), [marker])
            self.assertEqual(list(sibling.iterdir()), [output])

    def test_build_inputs_age_pin_and_publication_no_clobber(self):
        m = self.module()
        import tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=LANE) as tmp:
            folder = Path(tmp)
            tools = self.fixture(m, folder)
            with patch.object(m, 'HERE', tools):
                age_bad = folder / 'bad-age'
                (age_bad / 'linux').mkdir(parents=True)
                (age_bad / 'linux/age').write_bytes(b'not official age')
                with self.assertRaisesRegex(ValueError, 'age input pin'):
                    m.build_payload(REPO, age_bad)
            package = folder / 'keep.zip'
            package.write_bytes(b'existing artifact')
            with self.assertRaises(ValueError):
                m.write_package({'a.txt': b'not overwrite'}, package)
            self.assertEqual(package.read_bytes(), b'existing artifact')


if __name__ == '__main__':
    unittest.main()
