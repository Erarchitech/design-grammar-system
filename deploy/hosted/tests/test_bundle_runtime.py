"""Permission-gated runtime specification. NEVER run before owner sandbox approval.

This module deliberately fails nonzero when approval/harness is absent; a skip or
static substitute cannot attest live mounts, data-service, or n8n file access.
"""
import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[3]


class HostedBundleRuntimeTests(unittest.TestCase):
    def test_curated_data_service_ingest_and_n8n_file_read(self):
        """After checkpoint: run against isolated Compose candidate with curated files.

        Harness must assert: /mnt/repo has ONLY named read-only fixture/ingest
        paths; writable /app/data is isolated fresh sandbox state. Authenticate
        an actual POST /knowledge/ingest/folder for one approved mounted .md,
        inspect returned count and scoped Neo4j SpecNote, then request an absent
        path and a DG_OBSIDIAN/.secrets path and prove zero private reads/writes.
        Import actual n8n workflow in sandbox; execute a file-reading node/path
        against /files/workflows/<approved>.json and reject /files/../private.
        Currently committed workflows have no file-reading node: add an explicitly
        approved synthetic n8n file-read harness, not a fictitious production
        workflow claim. Keep sanitized request/response and cleanup evidence.
        """
        approval = os.environ.get("DG_HOSTED_SANDBOX_APPROVAL_REF")
        self.assertTrue(approval, "BLOCKED: named owner sandbox runtime permission required")
        harness = ROOT / "deploy" / "hosted" / "tests" / "run_bundle_runtime.py"
        self.assertTrue(harness.is_file(), "BLOCKED: actual service integration harness absent")
        result = subprocess.run(["python", str(harness), "--approval-ref", approval],
                                cwd=ROOT, capture_output=True, text=True, timeout=300)
        self.assertEqual(result.returncode, 0, "actual authorized service harness failed (not static PASS)")


if __name__ == "__main__":
    unittest.main()
