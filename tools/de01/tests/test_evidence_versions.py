"""NEW offline version controls; frozen fixture and report metadata stay unchanged."""
import copy
import json
from pathlib import Path
import sys

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/de01"))
sys.path.insert(0, str(ROOT / "data-service"))
import evidence_contract as contract
import legs
import report
import run_de01_repeat as repeat
from projection_hash import verdict_projection_hash


def envelope(version):
    # Reuse frozen expected outcomes, excluding its explicitly declared alternate
    # C# unsupported result. These are contract controls, not new live leg results.
    fixture = json.loads((ROOT / "fixtures/golden/fixture.json").read_text(encoding="utf-8"))
    rows = [contract.EvidenceRow(ruleId=r["ruleId"], objectId=r["objectId"],
                                canonicalStatus=r["expectedCanonicalStatus"])
            for r in fixture["expectedOutcomes"] if r["expectedCanonicalStatus"] != "unsupported"]
    if version == "2.0.0":
        result = contract.build_envelope_with_rule_results(
            fixture["project"], "def-golden-01", "offline-control", "1", "test", rows,
            [contract.EvidenceRuleResult(ruleId="R_ZERO", canonicalStatus="no_population", warnings=[])])
    else:
        result = contract.build_envelope(fixture["project"], "def-golden-01", "offline-control", "1", "test", rows)
    payload = result.model_dump(mode="json", exclude_none=True)
    payload["contractVersion"] = version  # explicit alias control, never a relabelled fixture
    return payload


@pytest.mark.parametrize("version", ["1", "1.0.0", "2.0.0"])
@pytest.mark.parametrize("mutation", ["valid", "crossed", "missing", "numeric", "future", "status", "extra"])
def test_actual_leg_admission_uses_raw_root_schema(version, mutation):
    payload = envelope(version)
    if mutation == "crossed":
        if version == "2.0.0":
            del payload["ruleResults"]
        else:
            payload["ruleResults"] = []
    elif mutation == "missing":
        del payload["contractVersion"]
    elif mutation == "numeric":
        payload["contractVersion"] = 1
    elif mutation == "future":
        payload["contractVersion"] = "3.0.0"
    elif mutation == "status":
        payload["rows"][0]["canonicalStatus"] = "PASS"
    elif mutation == "extra":
        payload["extra"] = True
    before = copy.deepcopy(payload)
    result = legs._validated_leg_result("csharp", payload)
    assert payload == before
    assert result.available == (mutation == "valid")
    if result.available:
        assert result.envelope is payload
        assert result.envelope["contractVersion"] == version
        contract.parse_envelope_model(payload)
    else:
        assert "schema validation failed" in result.error
        assert result.envelope["contractVersion"] == "1.0.0"
        assert result.envelope["canonicalStatus"] == "error"
        assert all(r["canonicalStatus"] == "error" for r in result.envelope["rows"])
    jsonschema.validate(result.envelope, contract.load_contract_schema())


def test_mixed_versions_keep_frozen_verdicts_repeat_and_report_baseline(tmp_path):
    versions = {"data-service": "1.0.0", "dg-reasoner": "2.0.0", "csharp": "1", "replay": "2.0.0"}
    payloads = {name: envelope(version) for name, version in versions.items()}
    before = copy.deepcopy(payloads)
    admitted = {name: legs._validated_leg_result(name, value) for name, value in payloads.items()}
    assert all(leg.available for leg in admitted.values())
    comparison = report.compare_legs(admitted)
    assert comparison.silent_disagreement_count == 0
    assert len(comparison.rows) == 3
    assert {r.object_id for r in comparison.rows} == {"OBJ_GOLD_EMPTY", "OBJ_GOLD_FAIL", "OBJ_GOLD_PASS"}
    target = tmp_path / "single.json"
    report.emit_json_report(comparison, target, "1.3.0")
    emitted = json.loads(target.read_text(encoding="utf-8"))
    jsonschema.validate(emitted, json.loads((ROOT / "tools/de01/report_schema.json").read_text(encoding="utf-8")))
    assert emitted["contractVersion"] == "1.0.0"  # harness baseline, not each leg's token
    assert emitted["canonicalizationVersion"] == 1
    calls = []
    def adapter(name):
        def invoke(fixture, config):
            calls.append(name)
            return legs._validated_leg_result(name, payloads[name])
        return invoke
    def no_process_probe(*args, **kwargs):
        raise FileNotFoundError("External process probes are disabled in this offline control")
    pins = repeat.collect_config_pins({"fixtureVersion": "1.3.0"},
        {"iterations": 2, "batches": 1, "pinned_replay_run_id": "def-golden-01"},
        subprocess_runner=no_process_probe)
    result = repeat.run_repeat({}, leg_callables={name: adapter(name) for name in versions},
                               iterations=2, batches=1, config=pins)
    assert calls == list(versions) * 2
    assert result.gate_passed is True
    assert result.per_iteration_silent_counts == [0, 0]
    assert result.leg_hashes == {name: [verdict_projection_hash(value)] * 2 for name, value in payloads.items()}
    repeat_target = tmp_path / "repeat.json"
    repeat.emit_repeat_json_report(result, repeat_target)
    repeated = json.loads(repeat_target.read_text(encoding="utf-8"))
    jsonschema.validate(repeated, json.loads((ROOT / "tools/de01/report_schema_repeat.json").read_text(encoding="utf-8")))
    assert repeated["contractVersion"] == "1.0.0"
    assert repeated["canonicalizationVersion"] == 1
    assert repeated["gate"]["nonProofStatement"] == repeat.NON_PROOF_STATEMENT
    assert payloads == before
    assert {name: leg.envelope["contractVersion"] for name, leg in admitted.items()} == versions


def test_mixed_version_real_disagreement_is_not_hidden():
    payloads = {name: envelope("2.0.0" if name == "csharp" else "1.0.0") for name in repeat.LEG_ROLES}
    row = next(r for r in payloads["csharp"]["rows"] if r["objectId"] == "OBJ_GOLD_PASS")
    row["canonicalStatus"] = "failed"
    comparison = report.compare_legs({name: legs._validated_leg_result(name, p) for name, p in payloads.items()})
    assert comparison.silent_disagreement_count == 1
