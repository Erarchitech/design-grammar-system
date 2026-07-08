"""Publish a validation run WITH geometry to verify the F-01 fix end-to-end.

Mimics the payload the Grasshopper VALIDATOR now sends after
DesignStateBindingService propagates ObjState.Geometry (commit 0b15ce0).
"""
import json
import urllib.request

RULE_ID = "R_BUILDING_MAX_HEIGHT_75_V"
PROJECT = "v8-ui-smoke"
DATA_SERVICE = "http://localhost:8000"

# 3x3 grid of buildings, heights mix pass (<=75) and fail (>75)
HEIGHTS = [60, 84, 72, 90, 45, 110, 75, 68, 96]
SIZE = 20.0   # footprint
GAP = 12.0


def box_mesh(x0, y0, w, d, h):
    v = [
        (x0, y0, 0), (x0 + w, y0, 0), (x0 + w, y0 + d, 0), (x0, y0 + d, 0),
        (x0, y0, h), (x0 + w, y0, h), (x0 + w, y0 + d, h), (x0, y0 + d, h),
    ]
    vertices = [c for p in v for c in p]
    faces = [
        [0, 3, 2, 1],  # bottom
        [4, 5, 6, 7],  # top
        [0, 1, 5, 4],
        [1, 2, 6, 5],
        [2, 3, 7, 6],
        [3, 0, 4, 7],
    ]
    return {"kind": "mesh", "vertices": vertices, "faces": faces, "colors": [], "values": []}


entities = []
failed_ids = []
passed_ids = []
for i, h in enumerate(HEIGHTS):
    row, col = divmod(i, 3)
    x0 = col * (SIZE + GAP)
    y0 = row * (SIZE + GAP)
    eid = f"obj_{i}"
    failing = h > 75
    (failed_ids if failing else passed_ids).append(eid)
    entities.append({
        "dgEntityId": eid,
        "displayName": f"b({eid}): h({h})",
        "geometry": {"units": "m", "items": [box_mesh(x0, y0, SIZE, SIZE, float(h))]},
        "ruleIds": [RULE_ID],
        "failedRuleIds": [RULE_ID] if failing else [],
        "passedRuleIds": [] if failing else [RULE_ID],
        "overallStatus": "failed" if failing else "passed",
    })

payload = {
    "project": PROJECT,
    "rules": [{
        "ruleId": RULE_ID,
        "ruleName": RULE_ID,
        "ruleDescription": "All building must be maximum 75 meters high",
    }],
    "ruleResults": [{
        "ruleId": RULE_ID,
        "passed": False,
        "failedEntityIds": failed_ids,
        "passedEntityIds": passed_ids,
    }],
    "entities": entities,
}

req = urllib.request.Request(
    f"{DATA_SERVICE}/validation/publish",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req, timeout=120) as resp:
    print(json.dumps(json.load(resp), indent=1))
