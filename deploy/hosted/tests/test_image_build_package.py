"""Offline exact-revision build package checks, never start Docker."""
import importlib.util
import json
from pathlib import Path
import sys
import os
import subprocess
import tempfile
import zipfile
import unittest

HOSTED = Path(__file__).resolve().parents[1]


def builder():
    path = HOSTED / 'build_image_job.py'
    if not path.is_file():
        raise AssertionError('controlled build job packager missing')
    spec = importlib.util.spec_from_file_location('build_image_job', path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(HOSTED))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(HOSTED))
    return module


class ImageBuildPackageTests(unittest.TestCase):
    def test_verify_rejects_rehashed_extra_preparation_tool(self):
        module = builder()
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            root = Path(tmp)
            manifest = {'schemaVersion': 1, 'frameworkRevision': 'a' * 40,
                        'status': 'BLOCKED', 'degramGitlink': None,
                        'files': {'data-service/Dockerfile': module.digest(b'FROM fixture')}}
            raw = json.dumps(manifest).encode()
            files = {'source/manifest.json': raw, 'source/data-service/Dockerfile': b'FROM fixture',
                     'support/Run-ImageBuild.ps1': b'# fixture only', 'support/unreviewed.ps1': b'bad'}
            job = {'schemaVersion': 1, 'kind': module.KIND, 'frameworkRevision': 'a' * 40,
                   'sourceManifestSha256': module.digest(raw), 'target': 'DESKTOP-OS4Q8CP',
                   'services': module.SERVICES, 'toolingStatus': module.TOOLING,
                   'files': {name: module.digest(data) for name, data in files.items()}}
            path = root / 'bad.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                for name, data in files.items():
                    archive.writestr(name, data)
                archive.writestr('build-job-manifest.json', json.dumps(job))
            with self.assertRaises(ValueError):
                module.verify(path)

    def test_exact_committed_export_ignores_dirty_runtime_checkout(self):
        module = builder()
        repo = HOSTED.parents[1]
        revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            root = Path(tmp)
            runner = root / 'runner.ps1'
            runner.write_text('# explicitly inert test fixture, not a runtime runner')
            output = root / 'job.zip'
            checksum = module.prepare(repo, revision, output, runner=runner)
            self.assertEqual(checksum, module.verify(output))
            with zipfile.ZipFile(output) as archive:
                job = json.loads(archive.read('build-job-manifest.json'))
                self.assertEqual(job['frameworkRevision'], revision)
                self.assertEqual(job['toolingStatus'], module.TOOLING)
                self.assertEqual(archive.read('support/Run-ImageBuild.ps1'), runner.read_bytes())
                self.assertFalse(any('.env' == Path(name).name for name in archive.namelist()))
            with self.assertRaises(ValueError):
                module.prepare(repo, revision, output, runner=runner)

    def test_only_four_source_build_contexts_not_runtime_stack(self):
        module = builder()
        self.assertEqual(module.SERVICES, {
            'neo4j': {'context': 'source/neo4j', 'dockerfile': 'Dockerfile'},
            'data-service': {'context': 'source/data-service', 'dockerfile': 'Dockerfile'},
            'dg-reasoner': {'context': 'source/dg-reasoner', 'dockerfile': 'Dockerfile'},
            'design-grammars': {'context': 'source/ui-v2', 'dockerfile': 'Dockerfile'},
        })


if __name__ == '__main__':
    unittest.main()
