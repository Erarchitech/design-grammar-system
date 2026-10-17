"""Offline test for tools/mapping/evaluate_session.py on the synthetic facade."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "tools" / "mapping"), str(ROOT / "data-service"), str(ROOT / "data-service" / "tests")]

import evaluate_session as ev  # noqa: E402
import mapping_engine as m  # noqa: E402
import mapping_fixtures as fx  # noqa: E402


def _as_script_ids(descriptors):
    """The GH script keeps the input stream (GU) in the native id even when GuAsHu sends source "HU"."""
    out = []
    for d in descriptors:
        d = dict(d)
        if d.get("source") == "HU" and d["geometry"]["vertexCount"] == 5:
            d["nativeId"] = d["nativeId"].replace(":HU:", ":GU:")
        out.append(d)
    return out


class EvaluateSessionTests(unittest.TestCase):
    def test_cold_start_then_learned_profiles(self):
        classes = fx.facade_classes()
        constraints = m.constraints_from_rows(fx.facade_rule_rows())
        d = _as_script_ids(fx.facade_v1_descriptors())
        cold = m.compute(d, classes, constraints)
        r = ev.report(cold, ev.gold_for(cold))
        self.assertEqual(r["openQuestions"], 2)
        self.assertEqual(r["goldCovered"], 376)
        self.assertEqual(r["metrics"]["overall"]["recall"], 0.0)  # nothing bound before answers
        decided, profiles = {}, []
        for qtype, opt in (("batch-assign", "accept-all"), ("mapping-or-design", "class:ex:GroundFloorUnit")):
            q = next(x for x in cold["questions"] if x["type"] == qtype)
            out = m.decide(cold, d, q["questionId"], opt, "o", "2026-10-18T09:00:00Z", classes, profiles=profiles)
            decided.update(out["decided"])
            profiles = m.merge_profiles(profiles, out["profiles"])
        learned = m.compute(_as_script_ids(fx.facade_v2_descriptors()), classes, constraints, profiles)
        r2 = ev.report(learned, ev.gold_for(learned))
        self.assertEqual(r2["openQuestions"], 0)
        self.assertEqual(r2["autoShare"], 1.0)
        self.assertEqual(r2["metrics"]["overall"]["precision"], 1.0)
        self.assertEqual(r2["metrics"]["overall"]["recall"], 1.0)


if __name__ == "__main__":
    unittest.main()
