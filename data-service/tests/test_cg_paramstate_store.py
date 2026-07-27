"""Tests for cg_paramstate_store.py -- the accept-time ParamState writer
(Phase 38 Plan 05: GHIN-02/03/04, D-18/D-19/D-21).

No live Neo4j. A session is faked with a small object that routes by the
query's `// op=NAME` tag to a canned row list (read) or records the call
(write), mirroring `test_cg_input_generation.py`'s `_FakeGenerationSession`
precedent. `cg_input_bindings.load_input_bindings` is monkeypatched to a
synthetic in-memory bindings dict so these tests never touch
`llm/structure_rules.json` on disk.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

os.environ.setdefault("LLM_MASTER_SECRET", "test-master-secret")

import pytest  # noqa: E402

import cg_input_bindings  # noqa: E402
import cg_paramstate_store as store  # noqa: E402

PROJECT = "proj-a1"
DEFINITION_ID = "frame.gh"
RULE_ID = "R_TEST_MONO_V"


# ── Fake Neo4j session -- routes by the query's op tag ──


class _FakeResult(list):
    """A plain list that also supports `.single()` and `.consume()`,
    matching every call shape this module's functions use."""

    def single(self):
        return self[0] if self else None

    def consume(self):
        return None


class _FakeSession:
    def __init__(self, rule_limit_rows, published_parameters, fetch_rows=None):
        self._rule_limit_rows = rule_limit_rows
        self._published_parameters = published_parameters
        self._fetch_rows = fetch_rows or []
        self.all_calls: list[tuple[str, dict]] = []
        self.write_calls: list[tuple[str, dict]] = []

    def run(self, query, params=None):
        params = dict(params or {})
        self.all_calls.append((query, params))
        if "READ_RULE_LIMIT" in query:
            return _FakeResult(self._rule_limit_rows)
        if "ACCEPT_CANDIDATE_LIST_PARAMETERS" in query:
            return _FakeResult(self._published_parameters)
        if "ACCEPT_PARAM_STATE_CANDIDATE" in query:
            self.write_calls.append((query, params))
            return _FakeResult([])
        if "FETCH_GENERATED_PARAM_STATES" in query:
            rows = self._fetch_rows
            rule_id = params.get("ruleId")
            if rule_id:
                rows = [row for row in rows if row.get("sourceRuleId") == rule_id]
            return _FakeResult(rows)
        raise AssertionError(f"Unexpected query in _FakeSession: {query[:80]!r}")


# No comparison BuiltinAtom -- the rule "exists" (non-empty rows) but carries
# no readable limit. accept_candidate never uses the limit itself, only the
# classification's parameter scope, so this is sufficient for every test here.
_NO_LIMIT_ROWS = [
    {"builtinIri": None, "bodyOrder": 1, "variableName": None, "lex": None, "datatype": None}
]

_BINDINGS = {
    RULE_ID: {
        "ruleId": RULE_ID,
        "determinability": "monotone-bound",
        "parameters": ["HTotal"],
        "metricExpression": "HTotal",
        "monotoneIn": ["HTotal"],
    }
}


def _published_parameter_row(domain_min=0.0, domain_max=100.0, domain_step=0.5):
    return {
        "cgId": "cg:1:param:11_Var_HTotal",
        "dgId": "dg:AAAAAAAAAAAAAAAA",
        "parameterName": "HTotal",
        "reinstateParameterId": "HTotal",
        "paramKind": "Variable",
        "dataType": "Float",
        "domainMin": domain_min,
        "domainMax": domain_max,
        "domainStep": domain_step,
    }


def _candidate(value=40.0, source_rule_id=RULE_ID, provenance_overrides=None):
    provenance = {
        "source": "ai-generated",
        "sourceRuleId": source_rule_id,
        "provider": "anthropic",
        "model": "claude-sonnet-4-6",
        "confidence": 0.82,
        "definitionId": DEFINITION_ID,
        "publishedAt": "2026-07-08T00:00:00Z",
        "strategy": "conservative",
        "determinabilityClass": "monotone-bound",
        "generatedAt": "2026-07-27T12:00:00Z",
    }
    if provenance_overrides:
        provenance.update(provenance_overrides)
    return {
        "candidateId": "c0",
        "strategy": "conservative",
        "parameters": [
            {
                "parameterId": "HTotal",
                "displayName": "HTotal",
                "type": "Number",
                "numberValue": value,
                "integerValue": None,
                "booleanValue": None,
            }
        ],
        "excludedParameters": [],
        "ruleSatisfaction": {"claim": "satisfied", "basis": "HTotal <= 75"},
        "provenance": provenance,
        "statePayload": {"stateKind": "ParamState", "paramStates": []},
    }


@pytest.fixture(autouse=True)
def _synthetic_bindings(monkeypatch):
    """Never touch llm/structure_rules.json on disk -- classify_rule() reads
    whatever load_input_bindings() returns."""
    monkeypatch.setattr(cg_input_bindings, "load_input_bindings", lambda path=None: _BINDINGS)


# ── Test 1: a valid candidate writes exactly one MERGE with full provenance ──


def test_accept_valid_candidate_writes_exactly_one_merge_with_full_provenance():
    session = _FakeSession(_NO_LIMIT_ROWS, [_published_parameter_row()])
    result = store.accept_candidate(session, PROJECT, DEFINITION_ID, RULE_ID, _candidate())

    assert len(session.write_calls) == 1
    query, params = session.write_calls[0]
    assert "MERGE (ds:DesignState {StateId: $stateId, project: $project})" in query
    assert "ds.kind = 'ParamState'" in query
    assert "ds.graph = 'ValidGraph'" in query

    required_keys = {
        "source",
        "sourceRuleId",
        "provider",
        "model",
        "confidence",
        "definitionId",
        "publishedAt",
        "strategy",
        "determinabilityClass",
        "generatedAt",
        "acceptedAt",
    }
    assert required_keys.issubset(params.keys())

    assert result["kind"] == "ParamState"
    assert result["project"] == PROJECT
    assert result["parameterCount"] == 1
    assert result["provenance"]["sourceRuleId"] == RULE_ID


# ── Test 2: StateId is DS_-prefixed and deterministic ──


def test_compute_param_state_id_is_deterministic_and_ds_prefixed():
    candidate = _candidate()
    id_1 = store.compute_param_state_id(candidate)
    id_2 = store.compute_param_state_id(candidate)

    assert id_1.startswith("DS_")
    assert id_1 == id_2


# ── Test 3: an out-of-domain candidate is rejected with zero writes ──


def test_out_of_domain_candidate_raises_and_writes_nothing():
    session = _FakeSession(_NO_LIMIT_ROWS, [_published_parameter_row(domain_min=0.0, domain_max=100.0)])
    candidate = _candidate(value=999.0)

    with pytest.raises(store.CandidateDomainViolation) as exc_info:
        store.accept_candidate(session, PROJECT, DEFINITION_ID, RULE_ID, candidate)

    assert exc_info.value.violations
    assert len(session.write_calls) == 0


# ── Test 4: incomplete provenance is rejected with zero writes ──


def test_missing_provenance_key_raises_and_writes_nothing():
    session = _FakeSession(_NO_LIMIT_ROWS, [_published_parameter_row()])
    candidate = _candidate()
    del candidate["provenance"]["sourceRuleId"]

    with pytest.raises(store.CandidateRequestInvalid):
        store.accept_candidate(session, PROJECT, DEFINITION_ID, RULE_ID, candidate)

    assert len(session.write_calls) == 0


# ── Test 5: a candidate valid at generation time but out-of-domain against a
# CHANGED (narrower) live domain is rejected -- the case a client round-trip
# cannot catch, and the reason accept_candidate re-reads live parameters. ──


def test_candidate_rejected_against_narrowed_live_domain():
    # At generation time the domain was [0, 100] and 40.0 was valid. Since
    # then the published domain narrowed to [0, 10] -- the live re-read must
    # catch this even though the candidate content never changed.
    session = _FakeSession(_NO_LIMIT_ROWS, [_published_parameter_row(domain_min=0.0, domain_max=10.0)])
    candidate = _candidate(value=40.0)

    with pytest.raises(store.CandidateDomainViolation):
        store.accept_candidate(session, PROJECT, DEFINITION_ID, RULE_ID, candidate)

    assert len(session.write_calls) == 0


# ── Test 6: fetch_generated_param_states -- the GHIN-03 SC4 assertion ──


def test_fetch_generated_param_states_returns_rule_model_and_timestamp():
    rows = [
        {
            "stateId": "DS_AAAA",
            "sourceRuleId": RULE_ID,
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "generatedAt": "2026-07-27T12:00:00Z",
            "acceptedAt": "2026-07-27T12:05:00Z",
            "strategy": "conservative",
            "determinabilityClass": "monotone-bound",
        },
        {
            "stateId": "DS_BBBB",
            "sourceRuleId": "R_OTHER_V",
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
            "generatedAt": "2026-07-27T11:00:00Z",
            "acceptedAt": "2026-07-27T11:05:00Z",
            "strategy": "balanced",
            "determinabilityClass": "direct-parameter",
        },
    ]
    session = _FakeSession(_NO_LIMIT_ROWS, [], fetch_rows=rows)

    all_rows = store.fetch_generated_param_states(session, PROJECT)
    assert len(all_rows) == 2
    for row in all_rows:
        assert {"stateId", "sourceRuleId", "provider", "model", "generatedAt"}.issubset(row.keys())

    filtered = store.fetch_generated_param_states(session, PROJECT, rule_id=RULE_ID)
    assert len(filtered) == 1
    assert filtered[0]["stateId"] == "DS_AAAA"
    assert filtered[0]["sourceRuleId"] == RULE_ID


# ── Test 7: every captured query is parameterized -- no value from the bound
# parameter dict ever appears interpolated into the query text itself. ──


def test_every_captured_query_is_parameterized():
    session = _FakeSession(_NO_LIMIT_ROWS, [_published_parameter_row()])
    store.accept_candidate(session, PROJECT, DEFINITION_ID, RULE_ID, _candidate())
    store.fetch_generated_param_states(session, PROJECT, rule_id=RULE_ID)

    for query, params in session.all_calls:
        for value in params.values():
            if isinstance(value, str) and value:
                assert value not in query, (
                    f"Query text contains a bound parameter value {value!r} directly -- "
                    f"this indicates string interpolation instead of a bound parameter."
                )
