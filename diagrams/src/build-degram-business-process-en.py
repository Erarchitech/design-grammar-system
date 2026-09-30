"""Localize the verified Russian artifacts without changing their layout or originals.
Run with: uv run --no-project --with lxml python diagrams/src/build-degram-business-process-en.py
"""
from pathlib import Path
from html import escape
import json
import re
from lxml import etree, html

BASE = Path(__file__).resolve().parents[1]
SRC, OUT = BASE/'src', BASE/'export'
SOURCE = 'fig-02-degram-business-process'
STEM = SOURCE + '-en'
labels = {
'process': {
'brand':'DESIGN GRAMMARS / DeGram Agent',
'status':'TARGET PROCESS · 1/2',
'title':'From requirements to an approved design decision',
'subtitle':'Six process steps and the system components that support them',
'cde-title':'CDE · common data environment',
'cde-body':'Input: documents and their revisions\nOutput: approved project deliverables',
'onto-title':'Ontograph · company object classes',
'onto-body':'A shared vocabulary of objects and properties\nFor projects within the company’s CDE',
'rights-title':'Access rights · at every step',
'rights-body':'View / edit / manage\nDG and the CDE enforce user permissions',
'step-title-01':'Gather\nrequirements',
'step-title-02':'Agree\non rules',
'step-title-03':'Link to\nthe model',
'step-title-04':'Develop\na design option',
'step-title-05':'Check\nthe option',
'step-title-06':'Approve\nand hand over',
'role-01':'Client + architect',
'role-02':'Lead architect',
'role-03':'Designer',
'role-04':'Designer',
'role-05':'System + designer',
'role-06':'Design decision owner',
'project-graphs-title':'ACTIVE PROJECT GRAPHS · numbers indicate the process steps where each graph is used',
'spec-title':'SpecGraph · 01, 06',
'spec-body':'Sources, explanations\nand decision rationale',
'meta-title':'Metagraph · 02, 03, 05',
'meta-body':'Project rules\nand their scope of applicability',
'comput-title':'ComputGraph · 03, 04',
'comput-body':'Links between parameters,\nscripts and the model',
'valid-title':'ValidGraph · 05, 06',
'valid-body':'Validation results\nand the checked model state',
'degram-title':'DeGram · the participant’s workspace: chat + DG web interface + Model Viewer',
'degram-subtitle':'Supports all six steps; people approve changes. Graph access is governed by DG and project permissions.',
'llm-title':'LLM · large language model',
'llm-body':'Suggests and explains; people approve',
'mcp-revit-title':'Revit MCP server ↔ Revit',
'mcp-revit-body':'Local model on the participant’s PC',
'mcp-gh-title':'GH MCP server ↔ Grasshopper',
'mcp-gh-body':'Scripts and mapping through the DG addin',
'legend':'→ workflow order · dashed lines: system links · issues at 05 → rework at 04 · approved output of 06 → publication in the CDE',
},
'scope': {
'brand':'DESIGN GRAMMARS / DeGram Agent',
'status':'TARGET PROCESS · 2/2',
'title':'Shared classes — project-specific rules',
'subtitle':'Experience is reused across company projects as a copy to be checked, not as a company-wide active rule',
'company-title':'COMPANY AND ITS CDE · a shared environment for data, object classes and accumulated experience',
'shared-cde-title':'CDE · documents and models',
'shared-cde-body':'Revisions and accessible project information\nLinks to sources and published deliverables',
'shared-onto-title':'Ontograph · shared object classes',
'shared-onto-body':'Company classes, properties and terminology\nVocabulary changes require separate approval',
'org-rights-title':'User permissions',
'org-rights-body':'Company + project\n+ CDE access',
'project-a-name':'PROJECT A · source',
'project-a-rule':'Metagraph: rule A, revision 3',
'project-b-name':'PROJECT B · new',
'project-b-rule':'Metagraph: a copy → its own revision',
'project-a-scope':'Applies only within this project:\nto selected classes, objects and conditions',
'project-b-scope':'Applies only within this project:\nto selected classes, objects and conditions',
'project-a-evidence':'ComputGraph · model and calculations; ValidGraph · checks\nSpecGraph · sources, decisions and history',
'project-b-evidence':'ComputGraph · model and calculations; ValidGraph · checks\nSpecGraph · sources, decisions and history',
'independence':'Shared classes\n\nSeparate rules\nand results',
'lessons-title':'Lessons learned · curated company experience',
'lessons-body':'Rule copy + source + applicability conditions + rationale\nIn the new project: adapt → validate → approve',
'select-label':'Select and authorize\nknowledge transfer\nfrom project A',
'adopt-label':'Copy into project B\nwith authorized\naccess',
'no-global':'Project B retains the source reference and maintains its own history. Rule A and its validation results remain in project A.',
'scope-footer':'Permissions define WHO may act. Rule scope defines WHAT it applies to and IN WHICH PROJECT.',
}}
for i in range(1,7): labels['process'][f'num-{i:02}']=f'{i:02}'

doc = html.fromstring((OUT/f'{SOURCE}.html').read_text(encoding='utf8'))
xml = etree.parse(str(SRC/f'{SOURCE}.drawio'))
svg_outputs=[]
for slug, translations in labels.items():
    sheet=doc.get_element_by_id(slug)
    sheet.set('aria-label', translations['title'])
    svg=sheet.xpath('./svg')[0]
    svg.xpath('./title')[0].text=translations['title']
    text_nodes=svg.xpath('.//text')
    assert {e.get('data-id') for e in text_nodes}==set(translations), slug
    for e in text_nodes:
        id=e.get('data-id')
        lines=translations[id].split('\n')
        size=float(e.get('font-size'))
        y=float(e.get('data-y')); h=float(e.get('data-h'))
        ty=y+h/2-(len(lines)-1)*size*1.25/2+size*.34
        e.set('y',str(ty))
        for child in list(e): e.remove(child)
        e.text=None
        for i,line in enumerate(lines):
            t=etree.SubElement(e,'tspan',x=e.get('x'),dy=str(0 if i==0 else size*1.25))
            t.text=line
    diagram=xml.xpath(f'//diagram[@id="{slug}"]')[0]
    diagram.set('name',translations['title'])
    for id,label in translations.items():
        cell=diagram.xpath(f'.//mxCell[@id="{id}"]')[0]
        cell.set('value','<br>'.join(escape(line) for line in label.split('\n')))
    svg_string=etree.tostring(svg,encoding='unicode')
    etree.fromstring(svg_string.encode())
    suffix='' if slug=='process' else '-scope'
    (OUT/f'{STEM}{suffix}.svg').write_text(svg_string,encoding='utf8')
    svg_outputs.append(svg_string)

doc.set('lang','en')
doc.xpath('//head/title')[0].text='DG and DeGram — workflow and rule scope'
nav=doc.xpath('//nav')[0]
nav.set('aria-label','Navigation')
for a,label in zip(nav.xpath('./a'),['1. Process and system','2. Company and projects','Explanations','Lessons learned']): a.text=label
doc.xpath('//p[@class="hint"]')[0].text='Two presentation slides. Scroll horizontally on narrow screens; Ctrl+P prints each diagram on a separate page.'
explanation='''<section class="explain" id="explain"><h2>System connections in plain language</h2>
<table><thead><tr><th>Component</th><th>Role in the process</th><th>Scope</th></tr></thead><tbody>
<tr><th>Ontograph</th><td>A shared vocabulary of object classes and properties, used to formalize rules, link models and validate them.</td><td>The company and its CDE. Each project references an agreed vocabulary revision.</td></tr>
<tr><th>Metagraph</th><td>Rules, criteria and applicability conditions. Creating, revising and retiring rules requires confirmation.</td><td>A single project. An object class may be shared, but a rule associated with it applies only within its project.</td></tr>
<tr><th>ComputGraph</th><td>Links between parameters, script components and the model explain how a design option is implemented. Calculations remain in the relevant design tools.</td><td>The project and its model/design option.</td></tr>
<tr><th>ValidGraph</th><td>Records what was checked, the model state and rule revision used, results, coverage and missing data.</td><td>The project and a specific validation run. Results from project A do not establish compliance in project B.</td></tr>
<tr><th>SpecGraph</th><td>Links to documents and excerpts, explanations, decision rationale and the provenance of copied rules.</td><td>The project. Source documents and their revisions remain in the CDE.</td></tr>
<tr><th>CDE</th><td>The common data environment supplies source material at step 01 and receives approved deliverables after step 06. A new document revision triggers a review of affected rules.</td><td>The company, with project-specific access controls. DeGram complements the CDE rather than replacing it.</td></tr>
<tr><th>Access rights</th><td>View (viewer), edit (editor) and manage the project (owner). Approval of vocabulary and design decisions depends on assigned responsibility, not just a technical access role.</td><td>DG enforces access to project data; the CDE enforces access to documents. Permission in one project does not grant access to another.</td></tr>
<tr><th>LLM</th><td>Helps interpret requirements, propose rules or edits, and explain results. Context is shared within the limits of user permissions and company policy.</td><td>An approved enterprise, local or external model, subject to company policy. The LLM supports human approval and tool-based validation; it replaces neither.</td></tr>
<tr><th>MCP servers</th><td>Local bridges from DeGram to Revit and Grasshopper. The DG addin maps objects, parameters and GH script components to DG. The user confirms changes.</td><td>The participant’s PC. A successful tool call is not proof of a correct design decision; these bridges do not bypass DG permissions.</td></tr>
</tbody></table>
<details id="boundaries"><summary>How experience is reused across projects</summary><ol>
<li>In project A, the responsible person selects a useful rule, authorizes its transfer and records its source, revision and limitations.</li>
<li>A participant with authorized access creates a copy in project B. The lessons learned library consists of curated company material in the CDE with links to DG. It is neither a sixth graph nor a company-wide set of automatically active rules.</li>
<li>In project B, the team checks compatibility with shared classes, adapts parameters and applicability, and validates the rule against that project’s model.</li>
<li>The responsible person in project B approves the new revision. The projects then evolve independently while retaining the source reference.</li>
</ol><p><strong>Example:</strong> “Door” is a company-wide object class. A door-width requirement from project A is copied into B as a proposal; its value and applicability are agreed for B’s conditions.</p></details>
<details><summary>What “target process” means</summary><p>This diagram describes the intended business process, not the readiness of the current implementation. LLM policy, CDE integrations, knowledge reuse and the scope of permitted Revit operations require design and verification. Company-wide classes do not imply that the Ontograph must be physically stored inside the CDE product.</p><p>Validation issues send the option back for rework. Missing data is supplied and checks are repeated. New requirements go through approval, while previous revisions and decisions remain in the history.</p></details></section>'''
old=doc.get_element_by_id('explain')
old.getparent().replace(old,html.fromstring(explanation))
doc.xpath('//footer')[0].text='Target process for discussion. Based on ptBIM R2, the ITcon submission, the DeGram integration review and the clarified company/project boundaries. DG has five graphs; DeGram is the participant’s client, not an additional graph.'
html_string='<!doctype html>\n'+etree.tostring(doc,method='html',encoding='unicode')
xml_string=etree.tostring(xml,encoding='unicode',pretty_print=True)
assert not re.search('[\u0400-\u04ff]',html_string), 'Untranslated Cyrillic in HTML'
assert not re.search('[\u0400-\u04ff]',xml_string), 'Untranslated Cyrillic in draw.io'
(OUT/f'{STEM}.html').write_text(html_string,encoding='utf8')
(SRC/f'{STEM}.drawio').write_text(xml_string,encoding='utf8')
manifest={'language':'en','pages':len(labels),'translated_diagram_labels':sum(map(len,labels.values())),'source':SOURCE,'status':'XML/SVG parsed; all diagram labels translated; no Cyrillic remains; visual/browser verification pending'}
(OUT/f'{STEM}-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print(json.dumps(manifest,indent=2))
