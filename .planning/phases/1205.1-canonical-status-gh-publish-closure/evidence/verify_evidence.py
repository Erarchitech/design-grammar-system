"""Offline phase evidence verifier. No service connections or credential reads."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[3]


def verify_wire():
    manifests = sorted((EVIDENCE / "wire").glob("*/manifest.json"))
    assert {p.parent.name for p in manifests} == {"supported", "unsupported", "zero_rows", "diagnostics"}
    for path in manifests:
        manifest = json.loads(path.read_bytes())
        assert manifest["captureHits"] == manifest["readbackHits"] == 1
        assert len(manifest["files"]) == 5
        for name, expected in manifest["files"].items():
            data = (path.parent / name).read_bytes()
            assert len(data) == expected["bytes"]
            assert hashlib.sha256(data).hexdigest() == expected["sha256"]
        persisted = (path.parent / "persisted-evidence.json").read_bytes()
        assert persisted == (path.parent / "reader-input.json").read_bytes()
        read = json.loads((path.parent / "reader-output.json").read_bytes())
        assert read["inputSha256"] == manifest["readerInputSha256"] == hashlib.sha256(persisted).hexdigest()
        assert read["envelopePresent"] is True and read["collisions"] == []
        view = json.loads((path.parent / "view-response.json").read_bytes())
        assert view["evidenceEnvelope"] == json.loads(persisted)
        assert view["readToken"] is None
        # Artifact allowlist: no auth headers, cookies, credentials or tokens with values.
        def inspect(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if any(term in key.lower() for term in ("token", "password", "authorization", "cookie", "secret")):
                        assert child is None, (path, key)
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)
        for name in manifest["files"]:
            inspect(json.loads((path.parent / name).read_bytes()))
        print(manifest["scenario"], "5 exact files; persist/read/view linked", manifest["readerInputSha256"])
    print("PASS: 4 scenarios / 20 raw payload files; capture and readback checksums verified")


def sdk_proof():
    command = ["dotnet", "msbuild", "DG/src/DG.Grasshopper/DG.Grasshopper.csproj",
               "-t:ResolveReferences", "-getProperty:DefineConstants", "-getProperty:RhinoCommonPath",
               "-getProperty:GrasshopperPath", "-getProperty:GhIoPath", "-getItem:ReferencePath",
               "-getItem:Compile", "-property:Configuration=Release"]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, check=True, timeout=120)
    raw = result.stdout.decode("utf-8-sig")
    data = json.loads(raw[raw.index("{"):])
    reference_names = {"RhinoCommon.dll", "Grasshopper.dll", "GH_IO.dll"}
    references = [item["Identity"] for item in data["Items"]["ReferencePath"]
                  if Path(item["Identity"]).name in reference_names]
    sources = [item["Identity"] for item in data["Items"]["Compile"]
               if Path(item["Identity"]).name in {"ValidationPublishClient.cs", "ValidationPublishContract.cs"}]
    assert {Path(p).name for p in references} == reference_names
    assert all(Path(p).is_file() for p in references)
    assert len(sources) == 2 and "GRASSHOPPER_SDK" in data["Properties"]["DefineConstants"]
    proof = {"command": command, "exit_code": result.returncode,
             "Properties": data["Properties"], "resolvedSdkReferences": references, "compiledPublishSources": sources}
    (EVIDENCE / "06-sdk-resolved.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(proof, indent=2))


if __name__ == "__main__":
    verify_wire()
    if "--sdk" in sys.argv:
        sdk_proof()
