"""RED-first HOST-02 contract; Task 2 implements the absent entry points.

Offline Compose config parses the effective model; no service starts, network
request, installed profile access or live checkout copy occurs here.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
HOSTED = ROOT / "deploy" / "hosted"


class ReleaseManifestTests(unittest.TestCase):
    def test_hosted_mounts_are_named_capabilities_not_repo_root(self):
        # Offline Compose parse only; no service/container operation.
        from test_compose_profile import BASE, MULTI_USER, HOSTED as OVERLAY, model
        services = model(BASE, MULTI_USER, OVERLAY)["services"]
        ds = {v["target"]: v for v in services["data-service"]["volumes"]}
        self.assertNotIn("/mnt/repo", ds, "whole-repository bind is forbidden")
        self.assertTrue(ds["/mnt/repo/hosted-ingest"]["read_only"])
        for path in ("/mnt/repo/llm/cypher_catalog.json", "/mnt/repo/llm/structure_rules.json",
                     "/mnt/repo/ontology/DesignGrammar-V7.owl",
                     "/mnt/repo/ontology/export_to_markdown_v7.py",
                     "/mnt/repo/spec/evidence-contract.schema.json"):
            with self.subTest(path=path):
                self.assertTrue(ds[path]["read_only"])
        self.assertEqual(ds["/app/data"]["type"], "volume", "sandbox data cannot bind the developer checkout")
        self.assertEqual({v["target"] for v in services["n8n"]["volumes"]},
                         {"/home/node/.n8n", "/files/workflows"})
        self.assertTrue(next(v for v in services["n8n"]["volumes"]
                             if v["target"] == "/files/workflows")["read_only"])
        self.assertEqual({v["target"] for v in services["dg-reasoner"]["volumes"]},
                         {"/app/ontology/DesignGrammar-V7.owl", "/app/ontology/dg-disjointness.ttl",
                          "/app/ontology/dg-shapes.ttl"})

    def test_assembler_uses_temporary_clean_git_export_not_dirty_checkout(self):
        with tempfile.TemporaryDirectory(prefix="dg-hosted-export-") as temporary:
            root = Path(temporary)
            source = root / "source"
            source.mkdir()
            (source / ".gitattributes").write_bytes(b"* -text\n")
            subprocess.run(["git", "init", "-q", str(source)], check=True, capture_output=True)
            (source / "sample.txt").write_bytes(b"committed fixture\n")
            subprocess.run(["git", "-C", str(source), "add", "sample.txt", ".gitattributes"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(source), "-c", "user.name=Hosted Test",
                            "-c", "user.email=hosted@example.invalid", "commit", "-qm", "fixture"],
                           check=True, capture_output=True)
            (source / "sample.txt").write_text("dirty private working-tree value\n", encoding="utf-8")
            revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
            archive = root / "clean.tar"
            with archive.open("wb") as output:
                subprocess.run(["git", "-C", str(source), "archive", "--format=tar", revision],
                               stdout=output, check=True)
            import tarfile
            with tarfile.open(archive) as exported:
                self.assertEqual(exported.extractfile("sample.txt").read(), b"committed fixture\n")
            # Targeted RED: missing assembler, not git setup or an import typo.
            self.assertTrue((HOSTED / "assemble.py").is_file(), "absent assembler: Task 2 must implement clean export assembly")
            allowlist = root / "allowlist.json"
            allowlist.write_text(json.dumps({"schemaVersion": 1, "includeDegram": False, "inputs": [
                {"path": "sample.txt", "purpose": "synthetic export proof"}
            ]}), encoding="utf-8")
            bundle = root / "bundle"
            result = subprocess.run([sys.executable, str(HOSTED / "assemble.py"),
                                     "--repo", str(source), "--revision", revision,
                                     "--allowlist", str(allowlist), "--output", str(bundle)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads((bundle / "manifest.json").read_text())["status"], "BLOCKED")
            self.assertEqual((bundle / "sample.txt").read_bytes(), b"committed fixture\n",
                             "dirty working-tree contents must not enter bundle")
            self.assertNotIn(b"dirty private", (bundle / "sample.txt").read_bytes())

    def test_unexpected_source_suffix_in_recursive_ui_glob_rejected(self):
        from test_helpers import fixture_repository, assemble
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, _ = fixture_repository(root)
            ui = source / 'ui-v2' / 'src'
            ui.mkdir(parents=True)
            (ui / 'App.jsx').write_text('export default 1;')
            (ui / 'secret.key').write_text('fixture only')
            subprocess.run(['git', '-C', str(source), 'add', 'ui-v2/src'], check=True)
            subprocess.run(['git', '-C', str(source), '-c', 'user.name=Fixture',
                            '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'ui'], check=True)
            revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
            self.assertNotEqual(assemble(source, revision, root / 'bundle', 'ui-v2/src/**/*').returncode, 0)

    def test_forbidden_private_filename_rejected(self):
        from test_helpers import fixture_repository, assemble
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, _ = fixture_repository(root)
            (source / '.env.production').write_text('fixture only')
            subprocess.run(['git', '-C', str(source), 'add', '.env.production'], check=True)
            subprocess.run(['git', '-C', str(source), '-c', 'user.name=Fixture',
                            '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'env'], check=True)
            revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
            self.assertNotEqual(assemble(source, revision, root / 'bundle', '.env.production').returncode, 0)

    def test_untrusted_allowlist_inputs_rejected(self):
        from test_helpers import fixture_repository, assemble
        for path in ("../secret.txt", ".secrets/private.txt", "sample.txt/../secret.txt"):
            with self.subTest(path=path), tempfile.TemporaryDirectory() as temp:
                source, revision = fixture_repository(Path(temp))
                result = assemble(source, revision, Path(temp) / "bundle", path)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((Path(temp) / "bundle").exists())

    def test_symlink_source_and_unexpected_private_output_rejected(self):
        from test_helpers import fixture_repository, assemble, validator
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, revision = fixture_repository(root, symlink=True)
            self.assertNotEqual(assemble(source, revision, root / "bad", "link.txt").returncode, 0)
            bundle = root / "bundle"
            self.assertEqual(assemble(source, revision, bundle).returncode, 0)
            (bundle / "Publications").mkdir()
            (bundle / "Publications" / "private.txt").write_text("private")
            self.assertNotEqual(validator(bundle).returncode, 0)

    def test_missing_digest_and_floating_images_rejected(self):
        from test_helpers import fixture_repository, assemble, validator
        import hashlib
        sys.path.insert(0, str(HOSTED))
        from validate_manifest import validate
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, revision = fixture_repository(root)
            bundle = root / "bundle"
            self.assertEqual(assemble(source, revision, bundle).returncode, 0)
            self.assertNotEqual(validator(bundle).returncode, 0)  # blocked draft is never release
            manifest = json.loads((bundle / "manifest.json").read_text())
            for filename, text in (
                ("docker-compose.yml", "services:\n  service:\n    image: fixture:latest\n"),
                ("docker-compose.multi-user.yml", "services: {}\n"),
                ("docker-compose.hosted.yml", "services: {}\n"),
            ):
                (bundle / filename).write_text(text)
                manifest["files"][filename] = hashlib.sha256((bundle / filename).read_bytes()).hexdigest()
            manifest["files"] = dict(sorted(manifest["files"].items()))
            policy_path = bundle / 'deploy' / 'hosted' / 'release-allowlist.json'
            policy_path.parent.mkdir(parents=True)
            policy_path.write_text(json.dumps({'schemaVersion': 1, 'includeDegram': False,
                'inputs': [{'path': name, 'purpose': 'synthetic'} for name in manifest['files']] +
                          [{'path': 'deploy/hosted/release-allowlist.json', 'purpose': 'policy'}]}))
            manifest['files'][policy_path.relative_to(bundle).as_posix()] = hashlib.sha256(policy_path.read_bytes()).hexdigest()
            manifest["files"] = dict(sorted(manifest["files"].items()))
            manifest["status"] = "FROZEN"
            manifest["unresolved"] = []
            manifest["imageProvenance"] = {"service": {"registryDigest": "fixture:latest"}}
            manifest["images"] = {}
            (bundle / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "missing/extra service image digest"):
                validate(bundle)
            manifest["images"] = {"service": "fixture:latest"}
            (bundle / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "mutable or missing image digest"):
                validate(bundle)

    def test_repo_root_mount_and_secret_logs_rejected(self):
        from test_helpers import fixture_repository, assemble, validator
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, revision = fixture_repository(root)
            bundle = root / "bundle"
            self.assertEqual(assemble(source, revision, bundle).returncode, 0)
            (bundle / "docker-compose.yml").write_text("services:\n  x:\n    image: fixture:latest\n    volumes:\n      - .:/mnt/repo:ro\n")
            self.assertNotEqual(validator(bundle).returncode, 0)
            (bundle / "docker-compose.yml").unlink()
            manifest = json.loads((bundle / "manifest.json").read_text())
            manifest["logs"] = "password=known-secret-value"
            (bundle / "manifest.json").write_text(json.dumps(manifest))
            self.assertNotEqual(validator(bundle, "--allow-blocked").returncode, 0)
            self.assertNotIn("known-secret-value", validator(bundle, "--allow-blocked").stderr)

    def test_broad_mount_rejected_even_when_manifest_hash_updated(self):
        from test_helpers import fixture_repository, assemble, validator
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, revision = fixture_repository(root)
            bundle = root / "bundle"
            self.assertEqual(assemble(source, revision, bundle).returncode, 0)
            # Three minimal Compose files: parser inspects actual effective model.
            for filename, content in (
                ("docker-compose.yml", "services:\n  data-service:\n    image: fixture:latest\n    volumes:\n      - .:/mnt/repo:ro\n"),
                ("docker-compose.multi-user.yml", "services: {}\n"),
                ("docker-compose.hosted.yml", "services: {}\n"),
            ):
                (bundle / filename).write_text(content)
            manifest = json.loads((bundle / "manifest.json").read_text())
            for filename in ("docker-compose.yml", "docker-compose.multi-user.yml", "docker-compose.hosted.yml"):
                manifest["files"][filename] = hashlib.sha256((bundle / filename).read_bytes()).hexdigest()
            manifest["files"] = dict(sorted(manifest["files"].items()))
            (bundle / "manifest.json").write_text(json.dumps(manifest))
            self.assertNotEqual(validator(bundle, "--allow-blocked").returncode, 0)

    def test_dirty_selection_policy_is_rejected(self):
        from test_helpers import fixture_repository
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, _ = fixture_repository(root)
            policy_path = source / 'deploy/hosted/release-allowlist.json'
            policy_path.parent.mkdir(parents=True)
            policy = {'schemaVersion': 1, 'includeDegram': False, 'inputs': [
                {'path': 'sample.txt', 'purpose': 'fixture'},
                {'path': 'deploy/hosted/release-allowlist.json', 'purpose': 'policy'}]}
            policy_path.write_text(json.dumps(policy))
            subprocess.run(['git', '-C', str(source), 'add', 'deploy/hosted/release-allowlist.json'], check=True)
            subprocess.run(['git', '-C', str(source), '-c', 'user.name=Fixture',
                            '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'policy'], check=True)
            revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
            policy['inputs'].append({'path': 'missing.txt', 'purpose': 'dirty'})
            policy_path.write_text(json.dumps(policy))
            result = subprocess.run([sys.executable, str(HOSTED / 'assemble.py'), '--repo', str(source),
                '--revision', revision, '--allowlist', str(policy_path), '--output', str(root / 'bundle')],
                capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'bundle').exists())

    def test_allowlisted_policy_rejects_extra_rehashed_file(self):
        from test_helpers import fixture_repository, assemble, validator
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, revision = fixture_repository(root)
            policy_path = source / 'deploy/hosted/release-allowlist.json'
            policy_path.parent.mkdir(parents=True)
            policy_path.write_text(json.dumps({'schemaVersion': 1, 'includeDegram': False,
                'inputs': [{'path': 'sample.txt', 'purpose': 'fixture'},
                           {'path': 'deploy/hosted/release-allowlist.json', 'purpose': 'policy'}]}))
            subprocess.run(['git', '-C', str(source), 'add', 'deploy/hosted/release-allowlist.json'], check=True)
            subprocess.run(['git', '-C', str(source), '-c', 'user.name=Fixture',
                            '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'policy'], check=True)
            revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
            bundle = root / 'bundle'
            result = subprocess.run([sys.executable, str(HOSTED / 'assemble.py'), '--repo', str(source),
                '--revision', revision, '--allowlist', str(policy_path), '--output', str(bundle)],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(validator(bundle, '--allow-blocked').returncode, 0)
            (bundle / 'extra.txt').write_text('fixture')
            manifest = json.loads((bundle / 'manifest.json').read_text())
            manifest['files']['extra.txt'] = hashlib.sha256((bundle / 'extra.txt').read_bytes()).hexdigest()
            manifest['files'] = dict(sorted(manifest['files'].items()))
            (bundle / 'manifest.json').write_text(json.dumps(manifest))
            self.assertNotEqual(validator(bundle, '--allow-blocked').returncode, 0)

    def test_extra_unlisted_regular_file_rejected(self):
        from test_helpers import fixture_repository, assemble, validator
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, revision = fixture_repository(root)
            bundle = root / "bundle"
            self.assertEqual(assemble(source, revision, bundle).returncode, 0)
            (bundle / "extra.txt").write_text("unexpected")
            self.assertNotEqual(validator(bundle, "--allow-blocked").returncode, 0)

    def test_manifest_validator_requires_real_file_and_image_digests(self):
        # Targeted RED until Task 2; schema must contain revision, optional gitlink,
        # exact per-file SHA-256 and all merged service image digests (built DG too).
        self.assertTrue((HOSTED / "validate_manifest.py").is_file(),
                        "absent validator: Task 2 must implement fail-closed manifest validation")
        with tempfile.TemporaryDirectory(prefix="dg-hosted-manifest-") as temporary:
            root = Path(temporary)
            (root / "sample.txt").write_text("sample\n", encoding="utf-8")
            (root / "manifest.json").write_text(json.dumps({
                "schemaVersion": 1, "frameworkRevision": "0" * 40,
                "degramGitlink": None, "files": {"sample.txt": "0" * 64}, "images": {}
            }), encoding="utf-8")
            result = subprocess.run([sys.executable, str(HOSTED / "validate_manifest.py"), str(root)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0, "missing image digests and wrong file hash must fail")


if __name__ == "__main__":
    unittest.main()
