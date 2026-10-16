"""Real Windows PowerShell 5.1 tests. Never invoke Docker (even for version).

All fixture packages/output live in the Hermes scratch directory, not the repo.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import zipfile

RUNNER = Path(__file__).resolve().parents[1] / 'build-job' / 'Run-ImageBuild.ps1'
PS = shutil.which('powershell.exe')
SCRATCH = Path('C:/Users/Admin/AppData/Local/hermes/cache/scratch')
REV = '2dedbfb3e138c2b437e781696197105dca93342a'
SERVICES = {'neo4j': 'neo4j', 'dg-reasoner': 'dg-reasoner',
            'data-service': 'data-service', 'design-grammars': 'ui-v2'}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(PS, 'Windows PowerShell 5.1 required')
class RunnerTests(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(prefix='dg-build-runner-', dir=SCRATCH)
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.root = self.base / 'package'
        self.root.mkdir()

    def ps(self, code, **kwargs):
        return subprocess.run([PS, '-NoLogo', '-NoProfile', '-NonInteractive',
                               '-ExecutionPolicy', 'Bypass', '-Command', code],
                              capture_output=True, text=True, errors='replace', timeout=30, cwd=self.base, **kwargs)

    def helpers(self, code):
        # Parse and load ONLY function declarations: script entrypoint cannot run.
        return self.ps("$ErrorActionPreference='Stop'; $tokens=$null; $errors=$null; "
                       f"$ast=[System.Management.Automation.Language.Parser]::ParseFile({quote(RUNNER)},[ref]$tokens,[ref]$errors); "
                       "if($errors.Count){throw 'parse failed'}; "
                       "$ast.FindAll({param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst]},$false) | "
                       "ForEach-Object { . ([scriptblock]::Create($_.Extent.Text)) }; " + code)

    def fixture(self, source_changes=None, job_changes=None):
        self.assertTrue(RUNNER.exists(), 'controlled runner is not implemented')
        files = {f'{directory}/Dockerfile': b'FROM scratch\n' for directory in SERVICES.values()}
        source = {'schemaVersion': 1, 'status': 'BLOCKED', 'frameworkRevision': REV,
                  'files': {name: sha(data) for name, data in sorted(files.items())},
                  'images': {}, 'degramGitlink': None, 'unresolved': ['mutable dependencies']}
        source.update(source_changes or {})
        payload = {'source/' + name: data for name, data in files.items()}
        payload['source/manifest.json'] = json.dumps(source, sort_keys=True).encode()
        payload['support/Run-ImageBuild.ps1'] = RUNNER.read_bytes()
        job = {'schemaVersion': 1, 'kind': 'controlled-image-build-not-release',
               'frameworkRevision': REV, 'sourceManifestSha256': sha(payload['source/manifest.json']),
               'target': 'DESKTOP-OS4Q8CP',
               'services': {service: {'context': 'source/' + directory, 'dockerfile': 'Dockerfile'}
                            for service, directory in SERVICES.items()},
               'files': {name: sha(data) for name, data in sorted(payload.items())},
               'toolingStatus': 'hashed-preparation-tools-not-part-of-source-revision'}
        job.update(job_changes or {})
        payload['build-job-manifest.json'] = json.dumps(job, sort_keys=True).encode()
        for name, data in payload.items():
            dest = self.root / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        self.zip = self.base / 'package.zip'
        with zipfile.ZipFile(self.zip, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(payload.items()):
                archive.writestr(name, data)
        self.output = self.base / 'output'
        return payload

    def run_fixture(self, preflight=True, expected=None, env=None):
        runner = self.root / 'support/Run-ImageBuild.ps1'
        command = (f'& {quote(runner)} -PackageZip {quote(self.zip)} '
                   f'-ExpectedZipSha256 {quote(expected or sha(self.zip.read_bytes()))} '
                   f'-OutputDirectory {quote(self.output)}' + (' -PreflightOnly' if preflight else ''))
        return self.ps(command, env=env)

    def report(self):
        return json.loads((self.output / 'build-report.json').read_text(encoding='utf-8-sig'))

    def test_real_powershell51_preflight_report(self):
        self.fixture()
        result = self.run_fixture()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = self.report()
        self.assertEqual(report['schemaVersion'], 1)
        self.assertEqual(report['kind'], 'controlled-image-build-not-release')
        self.assertEqual(report['status'], 'PREFLIGHT_ONLY_COMPLETE')
        self.assertEqual(report['sourceRevision'], REV)
        self.assertFalse(report['dockerInvoked'])
        self.assertFalse(report['releaseAccepted'])
        self.assertFalse(report['reproducibleDependencies'])
        self.assertFalse(report['daemonBuildCancellationProven'])
        self.assertIn('daemon-side build cancellation is unproven', report['timeoutCaveat'])
        self.assertEqual(len(report['contexts']), 4)
        self.assertEqual(report['runnerTooling']['sha256'], sha(RUNNER.read_bytes()))
        self.assertEqual(report['sourceManifest']['status'], 'BLOCKED')
        self.assertEqual(len(report['packageFiles']), 6)
        self.assertEqual(report['images'], {})

    def assert_rejected(self, result, stage='preflight'):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        report = self.report()
        self.assertEqual(report['status'], 'FAILED')
        self.assertEqual(report['failureStage'], stage)
        self.assertFalse(report['dockerInvoked'])
        self.assertNotIn('Exception', result.stdout + result.stderr)

    def test_zip_hash_tamper_rejected(self):
        self.fixture()
        self.assert_rejected(self.run_fixture(expected='0' * 64))

    def test_extracted_tamper_rejected(self):
        self.fixture()
        (self.root / 'source/neo4j/Dockerfile').write_bytes(b'FROM malicious\n')
        self.assert_rejected(self.run_fixture())

    def test_extracted_extra_file_rejected(self):
        self.fixture()
        (self.root / 'source/neo4j/extra').write_bytes(b'extra')
        self.assert_rejected(self.run_fixture())

    def test_zip_extra_member_rejected(self):
        self.fixture()
        with zipfile.ZipFile(self.zip, 'a') as archive:
            archive.writestr('source/neo4j/extra', b'extra')
        self.assert_rejected(self.run_fixture())

    def test_zip_member_tamper_rejected(self):
        payload = self.fixture()
        payload['source/neo4j/Dockerfile'] = b'tampered archive only'
        with zipfile.ZipFile(self.zip, 'w') as archive:
            for name, data in payload.items():
                archive.writestr(name, data)
        self.assert_rejected(self.run_fixture())

    def test_source_manifest_blocked_required(self):
        self.fixture(source_changes={'status': 'ACCEPTED'})
        self.assert_rejected(self.run_fixture())

    def test_source_revision_mismatch_rejected(self):
        self.fixture(source_changes={'frameworkRevision': 'a' * 40})
        self.assert_rejected(self.run_fixture())

    def test_source_membership_exact(self):
        self.fixture(source_changes={'files': {}})
        self.assert_rejected(self.run_fixture())

    def test_source_manifest_hash_required(self):
        self.fixture(job_changes={'sourceManifestSha256': '0' * 64})
        self.assert_rejected(self.run_fixture())

    def test_service_context_contract_exact(self):
        self.fixture(job_changes={'services': {}})
        self.assert_rejected(self.run_fixture())

    def test_existing_output_never_modified(self):
        self.fixture()
        self.output.mkdir()
        marker = self.output / 'build-report.json'
        marker.write_text('DO NOT OVERWRITE')
        result = self.run_fixture()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(), 'DO NOT OVERWRITE')

    def test_output_inside_package_rejected(self):
        self.fixture()
        self.output = self.root / 'output'
        result = self.run_fixture()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_zip_symlink_rejected(self):
        payload = self.fixture()
        with zipfile.ZipFile(self.zip, 'w') as archive:
            for name, data in payload.items():
                info = zipfile.ZipInfo(name)
                if name == 'source/neo4j/Dockerfile':
                    info.create_system = 3
                    info.external_attr = 0o120777 << 16
                archive.writestr(info, data)
        self.assert_rejected(self.run_fixture())

    def test_zip_traversal_rejected(self):
        self.fixture()
        with zipfile.ZipFile(self.zip, 'a') as archive:
            archive.writestr('../escape', b'no')
        self.assert_rejected(self.run_fixture())

    def test_zip_duplicate_rejected(self):
        self.fixture()
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.zip, 'a') as archive:
                archive.writestr('source/neo4j/Dockerfile', b'FROM scratch\n')
        self.assert_rejected(self.run_fixture())

    def test_parser_is_powershell51(self):
        result = self.helpers("if($PSVersionTable.PSVersion.Major -ne 5){throw 'not PS5'}; 'PARSE_OK'")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('PARSE_OK', result.stdout)

    def test_host_guard_rejects_current_pc_without_docker(self):
        self.fixture()
        self.assert_rejected(self.run_fixture(preflight=False), 'runtime-guard')

    def test_runtime_guard_pure_host_and_environment(self):
        code = "Assert-RuntimeGuard 'DESKTOP-OS4Q8CP' @{}; "
        code += "try { Assert-RuntimeGuard 'WRONG-HOST' @{}; throw 'accepted' } catch { if($_.Exception.Message -eq 'accepted'){throw} }; "
        overrides = ['DOCKER_HOST', 'DOCKER_CONTEXT', 'DOCKER_CONFIG', 'DOCKER_TLS',
                     'DOCKER_TLS_VERIFY', 'DOCKER_CERT_PATH', 'DOCKER_API_VERSION',
                     'BUILDKIT_HOST', 'BUILDX_BUILDER', 'DOCKER_BUILDKIT']
        for name in overrides:
            code += (f"try {{ Assert-RuntimeGuard 'DESKTOP-OS4Q8CP' @{{{name}='override'}}; throw 'accepted {name}' }} "
                     f"catch {{ if($_.Exception.Message -eq 'accepted {name}'){{throw}} }}; ")
        code += "'GUARDS_OK'"
        result = self.helpers(code)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('GUARDS_OK', result.stdout)

    def test_build_save_inspect_arguments_are_exact(self):
        result = self.helpers(
            "$build=@(Get-BuildArguments 'neo4j' 'C:\\job' 'C:\\out' " + quote(REV) + " 'dg-controlled/neo4j:abc'); "
            "$save=@(Get-SaveArguments 'neo4j' 'C:\\out' 'dg-controlled/neo4j:abc'); "
            "$inspect=@(Get-InspectArguments 'dg-controlled/neo4j:abc'); "
            "@{build=$build; save=$save; inspect=$inspect} | ConvertTo-Json -Compress")
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        prefix = ['--host', 'npipe:////./pipe/docker_engine']
        self.assertEqual(actual['build'], prefix + [
            'build', '--pull', '--no-cache', '--platform', 'linux/amd64',
            '--iidfile', 'C:\\out\\neo4j.iid', '--label',
            'org.opencontainers.image.revision=' + REV, '--tag', 'dg-controlled/neo4j:abc',
            '--file', 'C:\\job\\source\\neo4j\\Dockerfile', 'C:\\job\\source\\neo4j'])
        self.assertEqual(actual['save'], prefix + ['image', 'save', '--output',
                                                   'C:\\out\\neo4j.tar', 'dg-controlled/neo4j:abc'])
        self.assertEqual(actual['inspect'], prefix + ['image', 'inspect', '--format',
            '{"Id":{{json .Id}},"RepoDigests":{{json .RepoDigests}},"Os":{{json .Os}},"Architecture":{{json .Architecture}}}',
            'dg-controlled/neo4j:abc'])

    def test_unique_local_tags(self):
        result = self.helpers("$a=New-LocalTag 'neo4j'; $b=New-LocalTag 'neo4j'; @{a=$a;b=$b}|ConvertTo-Json -Compress")
        self.assertEqual(result.returncode, 0, result.stderr)
        tags = json.loads(result.stdout)
        self.assertNotEqual(tags['a'], tags['b'])
        self.assertRegex(tags['a'], r'^dg-controlled/neo4j:[0-9a-f]{32}$')

    def test_minimum_free_space(self):
        result = self.helpers("Assert-FreeBytes (30GB); try { Assert-FreeBytes (30GB - 1); throw 'accepted' } "
                              "catch {if($_.Exception.Message -eq 'accepted'){throw}}; 'SPACE_OK'")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('SPACE_OK', result.stdout)

    def test_inspect_verification_keeps_image_id_separate(self):
        iid = 'sha256:' + 'a' * 64
        digest = 'example/repo@sha256:' + 'b' * 64
        result = self.helpers("$i=Confirm-ImageIdentity " + quote(iid) + " " +
                              quote(json.dumps({'Id': iid, 'RepoDigests': [digest], 'Os': 'linux', 'Architecture': 'amd64'})) +
                              '; $i | ConvertTo-Json -Compress')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {'imageId': iid, 'repoDigests': [digest],
                                                    'os': 'linux', 'architecture': 'amd64'})

    def test_inspect_rejects_mismatched_iid_platform_and_extra_fields(self):
        iid = 'sha256:' + 'a' * 64
        cases = [{'Id': 'sha256:' + 'b' * 64, 'RepoDigests': [], 'Os': 'linux', 'Architecture': 'amd64'},
                 {'Id': iid, 'RepoDigests': [], 'Os': 'windows', 'Architecture': 'amd64'},
                 {'Id': iid, 'RepoDigests': [], 'Os': 'linux', 'Architecture': 'arm64'},
                 {'Id': iid, 'RepoDigests': [], 'Os': 'linux', 'Architecture': 'amd64', 'Config': 'secret'}]
        for data in cases:
            with self.subTest(data=data):
                result = self.helpers('Confirm-ImageIdentity ' + quote(iid) + ' ' + quote(json.dumps(data)))
                self.assertNotEqual(result.returncode, 0)

    def test_bounded_process_suppresses_raw_output(self):
        result = self.helpers("$r=Invoke-BoundedProcess " + quote(PS) +
                              " @('-NoProfile','-Command','[Console]::Write(\"private raw log\")') 10 ([datetime]::UtcNow.AddSeconds(20)); "
                              "if($r -ne ''){throw 'raw log leaked'}; 'DISCARDED'")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('DISCARDED', result.stdout)
        self.assertNotIn('private raw log', result.stdout)

    def test_bounded_process_captures_selected_output(self):
        result = self.helpers("Invoke-BoundedProcess " + quote(PS) +
                              " @('-NoProfile','-Command','[Console]::Write(\"selected\")') 10 ([datetime]::UtcNow.AddSeconds(20)) -Capture")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'selected')

    def test_timeout_kills_and_waits_for_child_without_docker(self):
        result = self.helpers("try { Invoke-BoundedProcess " + quote(PS) +
                              " @('-NoProfile','-Command','Start-Sleep -Seconds 20') 1 ([datetime]::UtcNow.AddSeconds(20)); throw 'accepted' } "
                              "catch {if($_.Exception.Message -ne 'command timeout; daemon build cancellation unproven'){throw}; 'TIMEOUT_OK'}")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('TIMEOUT_OK', result.stdout)

    def test_runtime_flow_and_bounds_contract(self):
        text = RUNNER.read_text()
        self.assertIn("$deadline = [datetime]::UtcNow.AddHours(3)", text)
        self.assertIn('2700', text)
        self.assertIn("$report.status = 'BUILD_EXPORT_COMPLETE'", text)
        self.assertIn('Get-BuildArguments', text)
        self.assertIn('Get-SaveArguments', text)
        self.assertIn('Confirm-ImageIdentity', text)
        self.assertIn('archiveSha256', text)
        self.assertIn('archiveBytes', text)
        self.assertNotRegex(text, r'(?i)docker\s+(?:push|run|compose|prune|rm|rmi|network|volume)\b')

    def test_zip_case_alias_member_rejected(self):
        payload = self.fixture()
        payload['source/neo4j/dockerfile'] = payload.pop('source/neo4j/Dockerfile')
        with zipfile.ZipFile(self.zip, 'w') as archive:
            for name, data in payload.items():
                archive.writestr(name, data)
        self.assert_rejected(self.run_fixture())

    def test_output_must_be_absolute_local_new_directory(self):
        self.fixture()
        self.output = Path('relative-output-must-not-create')
        result = self.run_fixture()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def junction(self, link, target):
        result = self.ps(f'New-Item -ItemType Junction -Path {quote(link)} -Target {quote(target)} | Out-Null')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.addCleanup(lambda: os.rmdir(link) if link.exists() else None)

    def test_extracted_tree_junction_rejected_without_following(self):
        self.fixture()
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'private').write_text('DO NOT READ')
        self.junction(self.root / 'source/linked', outside)
        self.assert_rejected(self.run_fixture())

    def test_package_junction_ancestor_rejected(self):
        self.fixture()
        alias = self.base / 'alias'
        self.junction(alias, self.root)
        self.root = alias
        self.assert_rejected(self.run_fixture())

    def test_output_junction_ancestor_rejected(self):
        self.fixture()
        target = self.base / 'outside'
        target.mkdir()
        alias = self.base / 'alias'
        self.junction(alias, target)
        self.output = alias / 'output'
        result = self.run_fixture()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((target / 'output').exists())

    def test_total_deadline_refuses_process_start(self):
        result = self.helpers("try { Invoke-BoundedProcess 'does-not-exist.exe' @() 2700 ([datetime]::UtcNow.AddSeconds(-1)); throw 'accepted' } "
                              "catch {if($_.Exception.Message -ne 'total time limit'){throw}; 'DEADLINE_OK'}")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('DEADLINE_OK', result.stdout)

    def test_process_failure_is_sanitized(self):
        result = self.helpers("try { Invoke-BoundedProcess " + quote(PS) +
                              " @('-NoProfile','-Command','[Console]::Error.Write(\"sensitive error\"); exit 9') 10 ([datetime]::UtcNow.AddSeconds(20)); throw 'accepted' } "
                              "catch {if($_.Exception.Message -ne 'command failed'){throw}; 'FAILURE_OK'}")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('sensitive error', result.stdout + result.stderr)

    def test_native_argument_roundtrip_spaces_quotes_and_slashes(self):
        args = ['', 'space value', 'quote"value', 'C:\\trailing slash\\', 'slashes\\\\"quote']
        script = self.base / 'argv.py'
        script.write_text('import json,sys; print(json.dumps(sys.argv[1:]))')
        import sys
        result = self.helpers('Invoke-BoundedProcess ' + quote(sys.executable) + ' @(' +
                              ','.join(quote(arg) for arg in [str(script), *args]) +
                              ') 10 ([datetime]::UtcNow.AddSeconds(20)) -Capture')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), args)

    def test_empty_unmanifested_directory_rejected(self):
        self.fixture()
        (self.root / 'source/neo4j/unmanifested').mkdir()
        self.assert_rejected(self.run_fixture())

    def test_build_arguments_cover_all_fixed_contexts(self):
        for service, directory in SERVICES.items():
            with self.subTest(service=service):
                result = self.helpers('Get-BuildArguments ' + quote(service) + " 'C:\\job' 'C:\\out' " +
                                      quote(REV) + " 'dg-controlled/test:abc' | ConvertTo-Json -Compress")
                self.assertEqual(result.returncode, 0, result.stderr)
                arguments = json.loads(result.stdout)
                self.assertEqual(arguments[-1], 'C:\\job\\source\\' + directory)
                self.assertEqual(arguments[-2], 'C:\\job\\source\\' + directory + '\\Dockerfile')

    def test_inspect_allows_empty_or_null_repo_digests_without_inventing_digest(self):
        iid = 'sha256:' + 'a' * 64
        for digests in ([], None):
            with self.subTest(digests=digests):
                inspection = {'Id': iid, 'RepoDigests': digests, 'Os': 'linux', 'Architecture': 'amd64'}
                result = self.helpers('Confirm-ImageIdentity ' + quote(iid) + ' ' + quote(json.dumps(inspection)) +
                                      ' | ConvertTo-Json -Compress')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['repoDigests'], [])
    def test_source_member_hash_mismatch_rejected(self):
        bad_files = {directory + '/Dockerfile': '0' * 64 for directory in SERVICES.values()}
        self.fixture(source_changes={'files': bad_files})
        self.assert_rejected(self.run_fixture())

    def test_support_runner_hash_mismatch_rejected(self):
        self.fixture()
        # Keep executable bytes valid, but change the hashed tooling identity.
        runner = self.root / 'support/Run-ImageBuild.ps1'
        runner.write_bytes(runner.read_bytes() + b'\n# unapproved modification\n')
        self.assert_rejected(self.run_fixture())

    def test_preflight_ignores_docker_overrides_without_invocation(self):
        self.fixture()
        env = os.environ.copy()
        env['DOCKER_HOST'] = 'tcp://must-never-connect.invalid:2375'
        result = self.run_fixture(env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.report()['dockerInvoked'])

    def test_zip_junction_ancestor_rejected(self):
        self.fixture()
        alias = self.base / 'zip-alias'
        self.junction(alias, self.base)
        self.zip = alias / 'package.zip'
        self.assert_rejected(self.run_fixture())

    def test_archive_unsupported_windows_names_rejected(self):
        self.fixture()
        for name in ('source/neo4j/NUL.txt', 'source/neo4j/file:stream',
                     'source/neo4j/trailing.', 'source/neo4j/back\\slash'):
            with self.subTest(name=name):
                result = self.helpers('Assert-SafeRelative ' + quote(name))
                self.assertNotEqual(result.returncode, 0)

    def test_new_output_creation_is_exclusive(self):
        text = RUNNER.read_text()
        self.assertIn("New-Item -ItemType Directory -Path $output -ErrorAction Stop", text)


if __name__ == '__main__':
    unittest.main()
