---
type: conspect
status: migrated
source: 02_PhD_2024/01_OBSIDIAN_REPOSITORY
migrated: 2026-07-18
---

semantic web rule language - SWRL (used in sematic reasoners such as FaCT and HermiT in Protege)
Based on combination of parts of OWL and RuleML/DATALOG
DATALOG rules that apply on OWL ontologies
OWL DL (Description Logics) and DATALOG are applying the same interpretations:
- OWL individuals are DATALOG constants
- OWL classes are unary DATALOG predicates
- OWL properties are binary DATALOG predicates
Syntax:
XML Concrete Syntax
RDF Concrete Syntax 
Abstract Syntax
Rules consist of body(Antecedent) and Consequent (Head)
A+C = Conjunctions of Assertions (atoms) of the form
SWRL is undecidable
Class, Property, Variables, Atoms
Variables are individuals of OWL concrete domain
sameAs(x,y) differentFrom(x,y) same or different individuals
==SWRL Example==
	Body of the Rule: hasParent(?x,?y) ^ hasBrother(?y,?z)
	Head of the Rule: hasUncle(?x,?z) 
	==hasUncle(?x,?z) - hasParent(?x,?y) ^ hasBrother(?y,?z)==
	hasParent(?x,?y) - atom (assertion)
	
	XML Syntax
	‹rulem1: imp>
		crulem1:_rlab rulem1:href="#onkel/›
		cowlx: Annotation>
			cowlx: Documentation>The Uncle Rule‹/owlx:Documentation>
		</owlx: Annotation>
		‹rulem1:_body>
			<swrlx:individualPropertyAton swrlx:property="&family;hasParent*›
				crulem1:var>x</ruleml:var›
				‹rulem1: var›y</ruleml:var>
			</swrlx: individualPropertyAton›
			‹swrlx:individualPropertyAton swrlx:property="&fanily;hasBrother*>
				<rulem1:var›y‹/ruleml:var›
				<rulem1:var›z</ruleml: var›
			</swrl:individualPropertyAtom>
		‹/ruleml:_body> 
		‹ruleml: _head›
			(SwrIx: individualPropertyAton swr]x:property="&fanily;hasUncle"›
				<ruleni:var›x</rulem1:var>
				<rulem1: var›z</rulem1:var›
			</Swrlx: individualPropertyAton>
		‹/ruleml:_head>
	<rulem1: imp>
Tool support for SWRL
	Bossam, R2ML, Hoolet, Pellet, KAON2, RacerPro
	SWRL TAB (Proteje)
How to represent Natural Language Text
1-Hot Encoding - Vector representation
1 Problem: All words are equidistant
2 problem: polysemy (one word can have several meanings)
The words are defined by their environment

Lection 5.1 **==Ontological Engineering==**
Ontologies enable interoperability among metadata.
Ontology Design
Ontology Mapping
Ontology Merging
Scheduling
Control
Quality Assurance