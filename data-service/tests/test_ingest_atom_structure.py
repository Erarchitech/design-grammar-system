"""F27: schema-invalid generated atoms must never reach Neo4j."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('LLM_MASTER_SECRET', 'test-master-secret')
import dg_context
import pytest

SW = 'FacadeModule(?m) ^ hasUpperVertex(?m, ?v1) ^ hasLowerVertex(?m, ?v2) -> PatternNode(?v1) ^ PatternNode(?v2)'


def a1_cypher(broken=False):
    lines = [f"MERGE (r:Rule {{Rule_Id:'R_FAC_A1_CONTROL_V', project:$project, graph:'Metagraph'}}) SET r.SWRL='{SW}'"]
    terms = [('cm', 'Class', 'FacadeModule'), ('cn', 'Class', 'PatternNode'),
             ('up', 'ObjectProperty', 'hasUpperVertex'), ('lo', 'ObjectProperty', 'hasLowerVertex')]
    for var, label, name in terms:
        lines.append(f"MERGE ({var}:{label} {{iri:'ex:{name}', project:$project, graph:'OntoGraph'}}) SET {var}.label='{name}'")
    for i, name in enumerate(['?m', '?v1', '?v2']):
        lines.append(f"MERGE (v{i}:Var {{name:'{name}', project:$project, graph:'Metagraph'}})")
    atoms = [('a1', 'A1', 'ClassAtom', 'FacadeModule', 'cm', [0]),
             ('a2', 'A2', 'ObjectPropertyAtom', 'hasUpperVertex', 'up', [0, 1]),
             ('a3', 'A3', 'ObjectPropertyAtom', 'hasLowerVertex', 'lo', [0, 2]),
             ('h1', 'H1', 'ClassAtom', 'PatternNode', 'cn', [1]),
             ('h2', 'H2', 'ClassAtom', 'PatternNode', 'cn', [2])]
    for var, suffix, kind, pred, target, args in atoms:
        lines.append(f"MERGE ({var}:Atom {{Atom_Id:'R_FAC_A1_CONTROL_V_{suffix}', project:$project, graph:'Metagraph'}})")
        if broken:
            lines.append(f"SET {var}.Builtin_iri='swrlb:{pred}'")
        else:
            lines.append(f"SET {var}.type='{kind}', {var}.iri='ex:{pred}', {var}.SWRL_label='{pred}'")
            lines.append(f"MERGE ({var})-[:REFERS_TO]->({target})")
        side = 'HAS_HEAD' if suffix.startswith('H') else 'HAS_BODY'
        lines.append(f"MERGE (r)-[:{side} {{order:{suffix[1:]}}}]->({var})")
        for pos, v in enumerate(args, 1):
            lines.append(f"MERGE ({var})-[:ARG {{pos:{pos}}}]->(v{v})")
    return '\n'.join(lines)


def test_f27_untyped_builtin_iri_atoms_are_rejected():
    result = dg_context.validate_cypher(a1_cypher(True), 'rule_ingest', project='p')
    assert not result['valid'], 'F27: untyped atoms with no REFERS_TO admitted'
    assert 'invalid_atom_structure' in {v['code'] for v in result['violations']}


def test_original_a1_typed_class_and_objectproperty_atoms_are_accepted():
    assert dg_context.validate_cypher(a1_cypher(), 'rule_ingest', project='p')['valid']


@pytest.mark.parametrize('old,new', [
    ("MERGE (a2)-[:REFERS_TO]->(up)", ""),
    ("MERGE (a2)-[:REFERS_TO]->(up)", "MERGE (a2)-[:REFERS_TO]->(cm)"),
    ("a2.iri='ex:hasUpperVertex'", "a2.iri='swrlb:hasUpperVertex'"),
    ("MERGE (a2)-[:ARG {pos:2}]->(v1)", ""),
    ("MERGE (a2)-[:ARG {pos:2}]->(v1)", "MERGE (a2)-[:ARG {pos:1}]->(v1)"),
    ("SET a2.type='ObjectPropertyAtom'", "SET a2.type='BuiltinAtom'"),
])
def test_generated_atom_corruption_is_rejected(old, new):
    cypher = a1_cypher().replace(old, new)
    result = dg_context.validate_cypher(cypher, 'rule_edit', project='p')
    assert not result['valid']
    assert 'invalid_atom_structure' in {v['code'] for v in result['violations']}


def test_literal_cannot_forge_missing_refers_to():
    cypher = a1_cypher().replace('MERGE (a2)-[:REFERS_TO]->(up)', '')
    cypher += "\nSET r.RuleDescription='MERGE (a2)-[:REFERS_TO]->(up)'"
    assert not dg_context.validate_cypher(cypher, 'rule_ingest', project='p')['valid']


def test_reversed_reference_is_supported():
    cypher = a1_cypher().replace('MERGE (a2)-[:REFERS_TO]->(up)', 'MERGE (up)<-[:REFERS_TO]-(a2)')
    assert dg_context.validate_cypher(cypher, 'rule_ingest', project='p')['valid']


def test_correct_inline_atom_properties_are_supported():
    cypher = a1_cypher().replace(
        "graph:'Metagraph'})\nSET a2.type='ObjectPropertyAtom', a2.iri='ex:hasUpperVertex', a2.SWRL_label='hasUpperVertex'",
        "graph:'Metagraph', type:'ObjectPropertyAtom', iri:'ex:hasUpperVertex', SWRL_label:'hasUpperVertex'})",
    )
    assert cypher != a1_cypher()
    assert dg_context.validate_cypher(cypher, 'rule_ingest', project='p')['valid']


def test_generate_retries_structural_failure_before_accepting(monkeypatch):
    from llm_gateway import GenerateResponse

    class Adapter:
        def __init__(self):
            self.prompts = []

        def generate(self, request, api_key):
            self.prompts.append(request.prompt)
            return GenerateResponse(text=a1_cypher(broken=len(self.prompts) == 1), provider='test', model='test', usage={})

    adapter = Adapter()
    monkeypatch.setattr(dg_context, 'load_persisted_llm_settings', lambda: {})
    monkeypatch.setattr(dg_context, 'resolve_active_provider', lambda *_: ('test', 'test', None))
    monkeypatch.setattr(dg_context, 'get_adapter', lambda *_: adapter)
    result = dg_context.generate_validated_cypher('original A1', 'rule_ingest', project='p')
    assert result['valid'] and result['attempts'] == 2
    assert 'invalid_atom_structure' in adapter.prompts[1]


def test_catalog_supported_comparison_shapes_keep_valid_structure():
    for shape in dg_context.load_cypher_catalog()['shapes']:
        example = shape.get('worked_example')
        if example:
            assert not dg_context.cypher_allowlist.check_ingest_atom_structure(example), shape['id']


def test_negative_argument_position_is_rejected():
    cypher = a1_cypher().replace('MERGE (a1)-[:ARG {pos:1}]->(v0)', 'MERGE (a1)-[:ARG {pos:-1}]->(v0)')
    assert not dg_context.validate_cypher(cypher, 'rule_ingest', project='p')['valid']


@pytest.mark.parametrize('edge', [
    'MERGE (a1)-[:ARG {pos:9}]-(v0)',
    'MERGE (a1)-[:REFERS_TO {extra:true}]-(v0)',
])
def test_undirected_extra_atom_edge_is_rejected(edge):
    assert not dg_context.validate_cypher(a1_cypher() + '\n' + edge, 'rule_ingest', project='p')['valid']


def data_atom_cypher(subject_literal=False):
    cypher = a1_cypher()
    cypher += "\nMERGE (dp:DatatypeProperty {iri:'ex:testData', project:$project, graph:'OntoGraph'})"
    cypher += "\nMERGE (lit:Literal {lex:'42', datatype:'xsd:integer', project:$project, graph:'Metagraph'})"
    cypher += "\nMERGE (da:Atom {Atom_Id:'R_TEST_A1', type:'DataPropertyAtom', iri:'ex:testData', project:$project, graph:'Metagraph'})"
    cypher += '\nMERGE (da)-[:REFERS_TO]->(dp)'
    cypher += '\nMERGE (da)-[:ARG {pos:1}]->(' + ('lit' if subject_literal else 'v0') + ')'
    cypher += '\nMERGE (da)-[:ARG {pos:2}]->(lit)'
    return cypher


def test_dataproperty_literal_subject_is_rejected():
    assert not dg_context.validate_cypher(data_atom_cypher(True), 'rule_ingest', project='p')['valid']


def test_dataproperty_literal_object_is_supported():
    assert dg_context.validate_cypher(data_atom_cypher(), 'rule_ingest', project='p')['valid']


def test_two_variables_cannot_declare_same_persisted_atom():
    cypher = a1_cypher()
    cypher += "\nMERGE (alias:Atom {Atom_Id:'R_FAC_A1_CONTROL_V_A2', project:$project, graph:'Metagraph', type:'ObjectPropertyAtom', iri:'ex:hasUpperVertex'})"
    cypher += '\nMERGE (alias)-[:REFERS_TO]->(up)'
    cypher += '\nMERGE (alias)-[:ARG {pos:1}]->(v1)'
    cypher += '\nMERGE (alias)-[:ARG {pos:2}]->(v0)'
    assert not dg_context.validate_cypher(cypher, 'rule_ingest', project='p')['valid']


@pytest.mark.parametrize('value', ['0', '-2', '1.0', '1e0'])
def test_noncanonical_argument_position_is_rejected(value):
    cypher = a1_cypher().replace('MERGE (a1)-[:ARG {pos:1}]->(v0)', f'MERGE (a1)-[:ARG {{pos:{value}}}]->(v0)')
    assert not dg_context.validate_cypher(cypher, 'rule_ingest', project='p')['valid']


def test_later_atom_property_override_is_checked():
    assert not dg_context.validate_cypher(a1_cypher() + '\nSET a2.iri=null', 'rule_ingest', project='p')['valid']


def test_chained_directed_argument_and_reference_are_supported():
    cypher = a1_cypher().replace('MERGE (a2)-[:ARG {pos:1}]->(v0)', '')
    cypher = cypher.replace(
        'MERGE (a2)-[:REFERS_TO]->(up)',
        'MERGE (up)<-[:REFERS_TO]-(a2)-[:ARG {pos:1}]->(v0)',
    )
    assert dg_context.validate_cypher(cypher, 'rule_ingest', project='p')['valid']


@pytest.mark.parametrize('value', ["''", 'null', '12', 'true', "'R_NEW_ID'"])
def test_atom_identity_cannot_be_erased_or_renamed(value):
    assert not dg_context.validate_cypher(a1_cypher() + '\nSET a2.Atom_Id=' + value, 'rule_ingest', project='p')['valid']


def test_duplicate_atom_alias_then_rename_is_rejected():
    cypher = a1_cypher()
    cypher += "\nMERGE (alias:Atom {Atom_Id:'R_FAC_A1_CONTROL_V_A2', project:$project, graph:'Metagraph', type:'ObjectPropertyAtom', iri:'ex:hasUpperVertex'})"
    cypher += '\nMERGE (alias)-[:REFERS_TO]->(up) MERGE (alias)-[:ARG {pos:1}]->(v1) MERGE (alias)-[:ARG {pos:2}]->(v0)'
    cypher += "\nSET alias.Atom_Id='R_NEW_ID'"
    assert not dg_context.validate_cypher(cypher, 'rule_ingest', project='p')['valid']


def test_predicate_alias_identity_mutation_is_rejected():
    cypher = a1_cypher() + "\nMERGE (up_alias:ObjectProperty {iri:'ex:hasUpperVertex', project:$project, graph:'OntoGraph'}) SET up_alias.iri='ex:other'"
    assert not dg_context.validate_cypher(cypher, 'rule_ingest', project='p')['valid']


def test_identity_mutation_then_restore_is_rejected():
    cypher = a1_cypher() + "\nSET up.iri='ex:other' SET up.iri='ex:hasUpperVertex'"
    assert not dg_context.validate_cypher(cypher, 'rule_ingest', project='p')['valid']
