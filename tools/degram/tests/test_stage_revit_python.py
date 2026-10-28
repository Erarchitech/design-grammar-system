"""Stage the Python the DeGram installer bundles for the Revit adapter (quick 261029 revit-python)."""
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "stage_revit_python.py"
spec = importlib.util.spec_from_file_location("stage_revit_python", SCRIPT)
stage_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage_module)

PTH = "python311.zip\r\n.\r\n\r\n# Uncomment to run site.main() automatically\r\n#import site\r\n"


def completed(returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


class StageRevitPythonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_path_file_gets_site_packages_the_adapter_folder_and_site(self):
        target = self.root / "py"
        target.mkdir()
        (target / "python311._pth").write_bytes(PTH.encode("utf-8"))
        stage_module.patch_path_file(target)
        lines = (target / "python311._pth").read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[:4], ["python311.zip", ".", "Lib\\site-packages", "..\\revit-mcp"])
        self.assertIn("import site", lines)
        self.assertNotIn("#import site", lines)

    def test_patching_twice_does_not_duplicate_entries(self):
        target = self.root / "py"
        target.mkdir()
        (target / "python311._pth").write_bytes(PTH.encode("utf-8"))
        stage_module.patch_path_file(target)
        stage_module.patch_path_file(target)
        raw = (target / "python311._pth").read_bytes()
        self.assertNotIn(b"\r\r\n", raw)
        lines = raw.decode("utf-8").splitlines()
        self.assertEqual(lines.count("Lib\\site-packages"), 1)
        self.assertEqual(lines.count("..\\revit-mcp"), 1)
        self.assertEqual(lines.count("import site"), 1)

    def test_path_file_must_be_unique(self):
        target = self.root / "py"
        target.mkdir()
        with self.assertRaises(stage_module.StageError):
            stage_module.patch_path_file(target)

    def test_pip_targets_windows_cpython_311_binary_wheels_only(self):
        seen = {}

        def run(command, **_):
            seen["command"] = command
            site = Path(command[command.index("--target") + 1])
            (site / "bin").mkdir(parents=True)
            (site / "bin" / "x.exe").write_text("x", encoding="utf-8")
            (site / "pkg" / "__pycache__").mkdir(parents=True)
            (site / "pkg" / "__pycache__" / "m.pyc").write_text("c", encoding="utf-8")
            (site / "pkg" / "m.py").write_text("m", encoding="utf-8")
            return completed()

        target = self.root / "py"
        stage_module.install_packages("python", target, run=run)
        command = seen["command"]
        for flag, value in [("--python-version", "3.11"), ("--platform", "win_amd64"), ("--implementation", "cp")]:
            self.assertEqual(command[command.index(flag) + 1], value)
        self.assertIn("--only-binary=:all:", command)
        self.assertEqual(command[-2:], ["mcp<2", "httpx"])
        site = target / "Lib" / "site-packages"
        self.assertFalse((site / "bin").exists())
        self.assertFalse((site / "pkg" / "__pycache__").exists())
        self.assertTrue((site / "pkg" / "m.py").is_file())

    def test_pip_failure_is_a_stage_error_without_leaking_the_whole_log(self):
        with self.assertRaises(stage_module.StageError) as caught:
            stage_module.install_packages("python", self.root / "py", run=lambda *a, **k: completed(1, "", "boom " * 400))
        self.assertLess(len(str(caught.exception)), 800)

    def test_refuses_a_non_empty_output_folder(self):
        out = self.root / "out"
        out.mkdir()
        (out / "leftover").write_text("x", encoding="utf-8")
        with self.assertRaises(stage_module.StageError):
            stage_module.stage(out)

    def test_an_interpreter_not_signed_by_the_psf_is_refused(self):
        def run(command, **_):
            return completed(0, "CN=Someone Else\n")

        self.assertNotIn(stage_module.PUBLISHER, stage_module.signature_publisher(self.root / "python.exe", run))

    def test_an_unsigned_interpreter_reports_no_publisher(self):
        self.assertEqual(stage_module.signature_publisher(self.root / "python.exe", lambda *a, **k: completed(0, "")), "")

    def test_requirements_keep_mcp_below_two(self):
        self.assertIn("mcp<2", stage_module.REQUIREMENTS)
        self.assertIn("httpx", stage_module.REQUIREMENTS)


if __name__ == "__main__":
    unittest.main()
