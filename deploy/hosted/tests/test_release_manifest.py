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
            allowlist.write_text(json.dumps({"schemaVersion": 1, "inputs": [
                {"path": "sample.txt", "purpose": "synthetic export proof"}
            ]}), encoding="utf-8")
            bundle = root / "bundle"
            result = subprocess.run([sys.executable, str(HOSTED / "assemble.py"),
                                     "--repo", str(source), "--revision", revision,
                                     "--allowlist", str(allowlist), "--output", str(bundle)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, "clean export assembly must succeed with resolved digests")
            self.assertEqual((bundle / "sample.txt").read_bytes(), b"committed fixture\n",
                             "dirty working-tree contents must not enter bundle")
            self.assertNotIn(b"dirty private", (bundle / "sample.txt").read_bytes())

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
