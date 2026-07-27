"""Invariant tests for the Phase 37 Wave 0 Frame fixture builders
(`cg_fixtures.py`). No Neo4j, no `app` import -- these assert the fixture
builders behave as documented, independent of any live infrastructure.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import cg_fixtures as f  # noqa: E402


def test_full_envelope_has_two_procedures_and_two_parameters_on_proc_11():
    envelope = f.frame_cg_context()
    procedures = envelope["algorithms"][0]["procedures"]
    assert len(procedures) == 2
    proc_11 = procedures[0]
    assert proc_11["id"] == f.PROC_11_CG_ID
    assert len(proc_11["parameters"]) == 2


def test_param_htotal_cg_id_present_in_full_envelope():
    envelope = f.frame_cg_context()
    proc_11 = envelope["algorithms"][0]["procedures"][0]
    param_ids = {param["id"] for param in proc_11["parameters"]}
    assert f.PARAM_HTOTAL_CG_ID in param_ids


def test_procedure_names_are_parser_faithful():
    assert "Truss" in f.PROC_11_NAME
    assert "Footer" in f.PROC_12_NAME


def test_frame_without_interface_empties_proc_11_interfaces():
    full = f.frame_cg_context()
    mutated = f.frame_without_interface()
    assert full["algorithms"][0]["procedures"][0]["interfaces"] != []
    assert mutated["algorithms"][0]["procedures"][0]["interfaces"] == []


def test_frame_without_footer_procedure_drops_proc_12():
    mutated = f.frame_without_footer_procedure()
    procedures = mutated["algorithms"][0]["procedures"]
    assert len(procedures) == 1
    assert all(procedure["id"] != f.PROC_12_CG_ID for procedure in procedures)


def test_frame_with_normalization_warnings_is_nonempty_while_full_is_empty():
    full = f.frame_cg_context()
    warned = f.frame_with_normalization_warnings()
    assert full["warnings"] == []
    assert warned["warnings"] != []


def test_builders_are_deep_copy_isolated():
    first = f.frame_cg_context()
    second = f.frame_cg_context()
    assert first == second
    assert first is not second
    assert first["algorithms"] is not second["algorithms"]

    first_no_iface = f.frame_without_interface()
    second_no_iface = f.frame_without_interface()
    assert first_no_iface == second_no_iface
    assert first_no_iface is not second_no_iface

    first_no_footer = f.frame_without_footer_procedure()
    second_no_footer = f.frame_without_footer_procedure()
    assert first_no_footer == second_no_footer
    assert first_no_footer is not second_no_footer
