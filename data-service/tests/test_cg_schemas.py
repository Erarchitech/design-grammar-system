"""Unit coverage for cg_schemas: the Pydantic output contract and the
provider-acceptable strict-schema emitter (Phase 35-06, RCGN-01).

No network. Mirrors test_cg_recognition.py's class-per-concern organisation.
"""

import copy

import pytest
from pydantic import ValidationError

import cg_recognition
import cg_schemas


def _proposal(**overrides) -> dict:
    base = {
        "kind": "Interface",
        "suggestedName": "11_IntF_SplitParameter",
        "procedureIndex": 11,
        "memberIds": ["n-parsplit"],
        "confidence": 0.82,
        "rationale": "bare Param, one input from procedure 11's tagged Divide Curve, one output",
    }
    base.update(overrides)
    return base


# ── recursive helpers: a root-only check would miss the exact bug these
#    assertions exist to catch (a nested $defs object failing the invariant) ──


def _object_nodes(node):
    """Yield every schema node that describes an object."""
    if isinstance(node, dict):
        if node.get("type") == "object" or "properties" in node:
            yield node
        for value in node.values():
            yield from _object_nodes(value)
    elif isinstance(node, list):
        for item in node:
            yield from _object_nodes(item)


def _all_keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _all_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _all_keys(item)


class TestProposedStructureModel:
    def test_valid_proposal_round_trips_unchanged(self):
        payload = {"proposals": [_proposal()], "unrecognized": []}
        model = cg_schemas.ProposedStructure.model_validate(payload)
        assert model.model_dump(mode="json") == payload

    @pytest.mark.parametrize("kind", ["IntF", "Interface", "Var", "VariableParam", "Pat", "Pattern"])
    def test_both_kind_spellings_accepted(self, kind):
        model = cg_schemas.StructureProposal.model_validate(_proposal(kind=kind))
        assert model.kind == kind

    def test_unknown_kind_rejected(self):
        with pytest.raises(ValidationError):
            cg_schemas.StructureProposal.model_validate(_proposal(kind="Algorithm"))

    @pytest.mark.parametrize("confidence", [-0.1, 1.1])
    def test_confidence_out_of_bounds_rejected(self, confidence):
        with pytest.raises(ValidationError):
            cg_schemas.StructureProposal.model_validate(_proposal(confidence=confidence))

    @pytest.mark.parametrize("confidence", [0.0, 1.0])
    def test_confidence_bounds_inclusive(self, confidence):
        model = cg_schemas.StructureProposal.model_validate(_proposal(confidence=confidence))
        assert model.confidence == confidence

    def test_extra_key_rejected_on_proposal(self):
        with pytest.raises(ValidationError):
            cg_schemas.StructureProposal.model_validate(_proposal(sneaky="x"))

    def test_extra_key_rejected_at_top_level(self):
        with pytest.raises(ValidationError):
            cg_schemas.ProposedStructure.model_validate(
                {"proposals": [], "unrecognized": [], "sneaky": "x"}
            )

    def test_unrecognized_defaults_to_empty_list(self):
        model = cg_schemas.ProposedStructure.model_validate({"proposals": []})
        assert model.unrecognized == []

    def test_unrecognized_block_requires_reason(self):
        with pytest.raises(ValidationError):
            cg_schemas.UnrecognizedBlock.model_validate({"memberIds": ["n1"]})

    def test_kind_set_matches_cg_recognition_allow_list(self):
        # The two lists are declared separately to avoid a circular import;
        # this assertion is what stops them drifting.
        assert set(cg_schemas.ProposalKind.__args__) == cg_recognition.ALLOWED_PROPOSAL_KINDS

    def test_validation_error_exposes_msg_and_loc(self):
        # 35-12 formats exc.errors() entries into schema_violation dicts using
        # exactly these two fields.
        with pytest.raises(ValidationError) as exc_info:
            cg_schemas.ProposedStructure.model_validate(
                {"proposals": [_proposal(confidence=5.0)]}
            )
        errors = exc_info.value.errors()
        assert errors
        assert "msg" in errors[0] and "loc" in errors[0]


class TestStrictJsonSchema:
    @pytest.fixture
    def schema(self):
        return cg_schemas.to_strict_json_schema(cg_schemas.ProposedStructure)

    def test_no_refs_or_defs_anywhere(self, schema):
        keys = set(_all_keys(schema))
        assert "$ref" not in keys
        assert "$defs" not in keys

    def test_additional_properties_false_on_every_object(self, schema):
        nodes = list(_object_nodes(schema))
        assert nodes, "expected at least the root and the two nested models"
        assert all(node.get("additionalProperties") is False for node in nodes)

    def test_required_equals_properties_on_every_object(self, schema):
        for node in _object_nodes(schema):
            assert set(node.get("required", [])) == set(node.get("properties", {}))

    def test_unrecognized_is_required_despite_python_default(self, schema):
        # OpenAI strict expresses optionality as a null union, never by
        # omission -- the single most common cause of a 400 from strict mode.
        assert "unrecognized" in schema["required"]

    def test_unsupported_keywords_stripped(self, schema):
        keys = set(_all_keys(schema))
        assert not (keys & set(cg_schemas._UNSUPPORTED_KEYWORDS))

    def test_emitter_does_not_mutate_pydantic_cached_schema(self):
        before = copy.deepcopy(cg_schemas.ProposedStructure.model_json_schema())
        cg_schemas.to_strict_json_schema(cg_schemas.ProposedStructure)
        after = cg_schemas.ProposedStructure.model_json_schema()
        assert after == before
        # And the bound is still present on the model side even though the
        # wire schema strips it.
        assert "minimum" in str(after)

    def test_nested_proposal_object_survived_inlining(self, schema):
        proposal_items = schema["properties"]["proposals"]["items"]
        assert set(proposal_items["properties"]) == {
            "kind",
            "suggestedName",
            "procedureIndex",
            "memberIds",
            "confidence",
            "rationale",
        }
