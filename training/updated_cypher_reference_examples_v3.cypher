// Example 1: Maximum height of each building must be at most 75 m.
MERGE (C_Building:Class {iri: 'ex:Building'})
SET C_Building.label = 'Building',
    C_Building.project = 'default-project',
    C_Building.graph = 'OntoGraph'

MERGE (DP_H:DatatypeProperty {iri: 'ex:hasHeightM'})
SET DP_H.SWRL_label = 'hasHeightM',
    DP_H.range = 'xsd:decimal',
    DP_H.project = 'default-project',
    DP_H.graph = 'OntoGraph'

MERGE (B_gt:Builtin {iri: 'swrlb:greaterThan'})
SET B_gt.label = 'greaterThan',
    B_gt.project = 'default-project',
    B_gt.graph = 'Metagraph'

MERGE (DP_V:DatatypeProperty {iri: 'ex:violatesMaxHeight'})
SET DP_V.SWRL_label = 'violatesMaxHeight',
    DP_V.range = 'xsd:boolean',
    DP_V.project = 'default-project',
    DP_V.graph = 'OntoGraph'

MERGE (r:Rule {Rule_Id: 'R_URB_HEIGHT_MAX_75_V'})
SET r.text = 'Building(?b)^hasHeightM(?b,?h)^swrlb:greaterThan(?h,75)->violatesMaxHeight(?b,true)',
    r.kind = 'violation',
    r.project = 'default-project',
    r.graph = 'Metagraph'

MERGE (vb:Var {name: '?b'})
SET vb.project = 'default-project',
    vb.graph = 'Metagraph'

MERGE (vh:Var {name: '?h'})
SET vh.project = 'default-project',
    vh.graph = 'Metagraph'

MERGE (lit75:Literal {lex: '75', datatype: 'xsd:decimal'})
SET lit75.project = 'default-project',
    lit75.graph = 'Metagraph'

MERGE (litT:Literal {lex: 'true', datatype: 'xsd:boolean'})
SET litT.project = 'default-project',
    litT.graph = 'Metagraph'

MERGE (a1:Atom {Atom_Id: 'R_URB_HEIGHT_MAX_75_V_A1'})
SET a1.type = 'ClassAtom',
    a1.iri = 'ex:Building',
    a1.SWRL_label = 'Building',
    a1.project = 'default-project',
    a1.graph = 'Metagraph'

MERGE (a2:Atom {Atom_Id: 'R_URB_HEIGHT_MAX_75_V_A2'})
SET a2.type = 'DataPropertyAtom',
    a2.iri = 'ex:hasHeightM',
    a2.SWRL_label = 'hasHeightM',
    a2.project = 'default-project',
    a2.graph = 'Metagraph'

MERGE (a3:Atom {Atom_Id: 'R_URB_HEIGHT_MAX_75_V_A3'})
SET a3.type = 'BuiltinAtom',
    a3.iri = 'swrlb:greaterThan',
    a3.SWRL_label = 'greaterThan',
    a3.project = 'default-project',
    a3.graph = 'Metagraph'

MERGE (h1:Atom {Atom_Id: 'R_URB_HEIGHT_MAX_75_V_H1'})
SET h1.type = 'DataPropertyAtom',
    h1.iri = 'ex:violatesMaxHeight',
    h1.SWRL_label = 'violatesMaxHeight',
    h1.project = 'default-project',
    h1.graph = 'Metagraph'

MERGE (r)-[:HAS_BODY {`order`: 1}]->(a1)
MERGE (r)-[:HAS_BODY {`order`: 2}]->(a2)
MERGE (r)-[:HAS_BODY {`order`: 3}]->(a3)
MERGE (r)-[:HAS_HEAD {`order`: 1}]->(h1)

MERGE (a1)-[:REFERS_TO]->(C_Building)
MERGE (a2)-[:REFERS_TO]->(DP_H)
MERGE (a3)-[:REFERS_TO]->(B_gt)
MERGE (h1)-[:REFERS_TO]->(DP_V)

MERGE (a1)-[:ARG {`pos`: 1}]->(vb)
MERGE (a2)-[:ARG {`pos`: 1}]->(vb)
MERGE (a2)-[:ARG {`pos`: 2}]->(vh)
MERGE (a3)-[:ARG {`pos`: 1}]->(vh)
MERGE (a3)-[:ARG {`pos`: 2}]->(lit75)
MERGE (h1)-[:ARG {`pos`: 1}]->(vb)
MERGE (h1)-[:ARG {`pos`: 2}]->(litT);

// Example 2: Minimum Hours of Direct Sunlight for Each Building must be at least 2.8 hours per day.
MERGE (C_Building:Class {iri: 'ex:Building'})
SET C_Building.label = 'Building',
    C_Building.project = 'default-project',
    C_Building.graph = 'OntoGraph'

MERGE (DP_S:DatatypeProperty {iri: 'ex:directSunlightHoursPerDay'})
SET DP_S.SWRL_label = 'directSunlightHoursPerDay',
    DP_S.range = 'xsd:decimal',
    DP_S.project = 'default-project',
    DP_S.graph = 'OntoGraph'

MERGE (B_lt:Builtin {iri: 'swrlb:lessThan'})
SET B_lt.label = 'lessThan',
    B_lt.project = 'default-project',
    B_lt.graph = 'Metagraph'

MERGE (DP_V:DatatypeProperty {iri: 'ex:violatesMinDirectSunlight'})
SET DP_V.SWRL_label = 'violatesMinDirectSunlight',
    DP_V.range = 'xsd:boolean',
    DP_V.project = 'default-project',
    DP_V.graph = 'OntoGraph'

MERGE (r:Rule {Rule_Id: 'R_SUNLIGHT_MIN_2_8H_V'})
SET r.text = 'Building(?b)^directSunlightHoursPerDay(?b,?s)^swrlb:lessThan(?s,2.8)->violatesMinDirectSunlight(?b,true)',
    r.kind = 'violation',
    r.title = 'Minimum Hours of Direct Sunlight for Each Building must be at least 2.8 hours/day (violation if less than 2.8)',
    r.project = 'default-project',
    r.graph = 'Metagraph'

MERGE (vb:Var {name: '?b'})
SET vb.project = 'default-project',
    vb.graph = 'Metagraph'

MERGE (vs:Var {name: '?s'})
SET vs.project = 'default-project',
    vs.graph = 'Metagraph'

MERGE (lit28:Literal {lex: '2.8', datatype: 'xsd:decimal'})
SET lit28.project = 'default-project',
    lit28.graph = 'Metagraph'

MERGE (litT:Literal {lex: 'true', datatype: 'xsd:boolean'})
SET litT.project = 'default-project',
    litT.graph = 'Metagraph'

MERGE (a1:Atom {Atom_Id: 'R_SUNLIGHT_MIN_2_8H_V_A1'})
SET a1.type = 'ClassAtom',
    a1.iri = 'ex:Building',
    a1.SWRL_label = 'Building',
    a1.project = 'default-project',
    a1.graph = 'Metagraph'

MERGE (a2:Atom {Atom_Id: 'R_SUNLIGHT_MIN_2_8H_V_A2'})
SET a2.type = 'DataPropertyAtom',
    a2.iri = 'ex:directSunlightHoursPerDay',
    a2.SWRL_label = 'directSunlightHoursPerDay',
    a2.project = 'default-project',
    a2.graph = 'Metagraph'

MERGE (a3:Atom {Atom_Id: 'R_SUNLIGHT_MIN_2_8H_V_A3'})
SET a3.type = 'BuiltinAtom',
    a3.iri = 'swrlb:lessThan',
    a3.SWRL_label = 'lessThan',
    a3.project = 'default-project',
    a3.graph = 'Metagraph'

MERGE (h1:Atom {Atom_Id: 'R_SUNLIGHT_MIN_2_8H_V_H1'})
SET h1.type = 'DataPropertyAtom',
    h1.iri = 'ex:violatesMinDirectSunlight',
    h1.SWRL_label = 'violatesMinDirectSunlight',
    h1.project = 'default-project',
    h1.graph = 'Metagraph'

MERGE (r)-[:HAS_BODY {`order`: 1}]->(a1)
MERGE (r)-[:HAS_BODY {`order`: 2}]->(a2)
MERGE (r)-[:HAS_BODY {`order`: 3}]->(a3)
MERGE (r)-[:HAS_HEAD {`order`: 1}]->(h1)

MERGE (a1)-[:REFERS_TO]->(C_Building)
MERGE (a2)-[:REFERS_TO]->(DP_S)
MERGE (a3)-[:REFERS_TO]->(B_lt)
MERGE (h1)-[:REFERS_TO]->(DP_V)

MERGE (a1)-[:ARG {`pos`: 1}]->(vb)
MERGE (a2)-[:ARG {`pos`: 1}]->(vb)
MERGE (a2)-[:ARG {`pos`: 2}]->(vs)
MERGE (a3)-[:ARG {`pos`: 1}]->(vs)
MERGE (a3)-[:ARG {`pos`: 2}]->(lit28)
MERGE (h1)-[:ARG {`pos`: 1}]->(vb)
MERGE (h1)-[:ARG {`pos`: 2}]->(litT);

// Example 3: Urban block grid size must be between 12 m and 48 m (violation if less than 12 m).
MERGE (C_UrbanBlock:Class {iri: 'ex:UrbanBlock'})
SET C_UrbanBlock.label = 'UrbanBlock',
    C_UrbanBlock.project = 'default-project',
    C_UrbanBlock.graph = 'OntoGraph'

MERGE (DP_G:DatatypeProperty {iri: 'ex:blockGridSizeM'})
SET DP_G.SWRL_label = 'blockGridSizeM',
    DP_G.range = 'xsd:decimal',
    DP_G.project = 'default-project',
    DP_G.graph = 'OntoGraph'

MERGE (B_lt:Builtin {iri: 'swrlb:lessThan'})
SET B_lt.label = 'lessThan',
    B_lt.project = 'default-project',
    B_lt.graph = 'Metagraph'

MERGE (DP_V:DatatypeProperty {iri: 'ex:violatesMinUrbanBlockGridSize'})
SET DP_V.SWRL_label = 'violatesMinUrbanBlockGridSize',
    DP_V.range = 'xsd:boolean',
    DP_V.project = 'default-project',
    DP_V.graph = 'OntoGraph'

MERGE (r:Rule {Rule_Id: 'R_URBANBLOCK_GRID_MIN_12M_V'})
SET r.text = 'UrbanBlock(?ub)^blockGridSizeM(?ub,?g)^swrlb:lessThan(?g,12)->violatesMinUrbanBlockGridSize(?ub,true)',
    r.kind = 'violation',
    r.project = 'default-project',
    r.graph = 'Metagraph'

MERGE (vub:Var {name: '?ub'})
SET vub.project = 'default-project',
    vub.graph = 'Metagraph'

MERGE (vg:Var {name: '?g'})
SET vg.project = 'default-project',
    vg.graph = 'Metagraph'

MERGE (lit12:Literal {lex: '12', datatype: 'xsd:decimal'})
SET lit12.project = 'default-project',
    lit12.graph = 'Metagraph'

MERGE (litT:Literal {lex: 'true', datatype: 'xsd:boolean'})
SET litT.project = 'default-project',
    litT.graph = 'Metagraph'

MERGE (a1:Atom {Atom_Id: 'R_URBANBLOCK_GRID_MIN_12M_V_A1'})
SET a1.type = 'ClassAtom',
    a1.iri = 'ex:UrbanBlock',
    a1.SWRL_label = 'UrbanBlock',
    a1.project = 'default-project',
    a1.graph = 'Metagraph'

MERGE (a2:Atom {Atom_Id: 'R_URBANBLOCK_GRID_MIN_12M_V_A2'})
SET a2.type = 'DataPropertyAtom',
    a2.iri = 'ex:blockGridSizeM',
    a2.SWRL_label = 'blockGridSizeM',
    a2.project = 'default-project',
    a2.graph = 'Metagraph'

MERGE (a3:Atom {Atom_Id: 'R_URBANBLOCK_GRID_MIN_12M_V_A3'})
SET a3.type = 'BuiltinAtom',
    a3.iri = 'swrlb:lessThan',
    a3.SWRL_label = 'lessThan',
    a3.project = 'default-project',
    a3.graph = 'Metagraph'

MERGE (h1:Atom {Atom_Id: 'R_URBANBLOCK_GRID_MIN_12M_V_H1'})
SET h1.type = 'DataPropertyAtom',
    h1.iri = 'ex:violatesMinUrbanBlockGridSize',
    h1.SWRL_label = 'violatesMinUrbanBlockGridSize',
    h1.project = 'default-project',
    h1.graph = 'Metagraph'

MERGE (r)-[:HAS_BODY {`order`: 1}]->(a1)
MERGE (r)-[:HAS_BODY {`order`: 2}]->(a2)
MERGE (r)-[:HAS_BODY {`order`: 3}]->(a3)
MERGE (r)-[:HAS_HEAD {`order`: 1}]->(h1)

MERGE (a1)-[:REFERS_TO]->(C_UrbanBlock)
MERGE (a2)-[:REFERS_TO]->(DP_G)
MERGE (a3)-[:REFERS_TO]->(B_lt)
MERGE (h1)-[:REFERS_TO]->(DP_V)

MERGE (a1)-[:ARG {`pos`: 1}]->(vub)
MERGE (a2)-[:ARG {`pos`: 1}]->(vub)
MERGE (a2)-[:ARG {`pos`: 2}]->(vg)
MERGE (a3)-[:ARG {`pos`: 1}]->(vg)
MERGE (a3)-[:ARG {`pos`: 2}]->(lit12)
MERGE (h1)-[:ARG {`pos`: 1}]->(vub)
MERGE (h1)-[:ARG {`pos`: 2}]->(litT);

