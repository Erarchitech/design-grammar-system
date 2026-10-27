"""Stage the DG connector payloads a DeGram build bundles (quick 261027-sgc)."""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "stage_connector_payloads.py"
spec = importlib.util.spec_from_file_location("stage_connector_payloads", SCRIPT)
stage_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage_module)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class StageConnectorPayloadsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / "framework"
        self.out = Path(self.temp.name) / "out"
        gh = self.root / stage_module.GRASSHOPPER_OUTPUT
        for name, text in [("DG.gha", "gha"), ("DG.Core.dll", "core"), ("DG.Core.pdb", "symbols"), ("DG.Grasshopper.deps.json", "{}")]:
            write(gh / name, text)
        revit = self.root / stage_module.REVIT_CONNECTOR
        for name in ["extension.json", "startup.py", "main.py", "DG.tab/Connector.panel/x.py", "dg_revit_mcp/__init__.py",
                     "lib/dg_connector/a.py", "tests/test_x.py", "lib/__pycache__/a.cpython-311.pyc", ".venv/Scripts/python.exe"]:
            write(revit / name, name)

    def tearDown(self):
        self.temp.cleanup()

    def test_stages_both_payloads_with_hashes_and_without_generated_files(self):
        manifest = stage_module.stage(self.root, self.out, build=False)
        self.assertEqual(sorted(manifest["grasshopper"]["files"]), ["DG.Core.dll", "DG.gha"])
        revit = sorted(manifest["revit"]["files"])
        self.assertIn("main.py", revit)
        self.assertIn("DG.tab/Connector.panel/x.py", revit)
        self.assertFalse(any(p.startswith(("tests/", ".venv/")) or "__pycache__" in p for p in revit))
        self.assertTrue((self.out / "dg-grasshopper" / "DG.gha").is_file())
        written = json.loads((self.out / "connector-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(written["grasshopper"]["files"]["DG.gha"], stage_module.sha256(self.out / "dg-grasshopper" / "DG.gha"))
        self.assertFalse(written["built"])

    def test_refuses_a_non_empty_output(self):
        write(self.out / "old.txt", "x")
        with self.assertRaises(stage_module.StageError):
            stage_module.stage(self.root, self.out, build=False)

    def test_missing_dg_gha_fails_loudly(self):
        (self.root / stage_module.GRASSHOPPER_OUTPUT / "DG.gha").unlink()
        with self.assertRaisesRegex(stage_module.StageError, "DG.gha"):
            stage_module.stage(self.root, self.out, build=False)
        self.assertFalse(self.out.exists())

    def test_incomplete_revit_connector_fails(self):
        (self.root / stage_module.REVIT_CONNECTOR / "main.py").unlink()
        with self.assertRaisesRegex(stage_module.StageError, "main.py"):
            stage_module.stage(self.root, self.out, build=False)

    def test_build_runs_dotnet_net48_release_and_stops_on_failure(self):
        calls = []

        def run(command, **kwargs):
            calls.append(command)
            return subprocess.CompletedProcess(command, 1)

        with self.assertRaisesRegex(stage_module.StageError, "build failed"):
            stage_module.stage(self.root, self.out, build=True, run=run)
        self.assertEqual(calls[0][1:2], ["build"])
        self.assertIn("net48", calls[0])
        self.assertIn("Release", calls[0])
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
