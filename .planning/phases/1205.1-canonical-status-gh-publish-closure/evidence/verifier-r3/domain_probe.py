"""Independent closed-domain and deep tuple held-out controls, no application startup."""
import json, sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from collections import OrderedDict
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'data-service'))
import evidence_contract as c
class DictSubclass(dict): pass
class ListSubclass(list): pass
class TupleSubclass(tuple): pass
observations=[]
def check(name, metadata, accepted):
    results={}
    for gate in ['factory','legacy-validator','resources']:
        try:
            if gate=='factory':
                m=c.build_envelope_with_rule_results('p','d','s','1','test',[],[],source_representation=metadata)
                wire=m.model_dump(mode='json',exclude_none=True)['sourceRepresentation']
                results['wire']=wire
            elif gate=='legacy-validator':
                c.validate_envelope(c.build_envelope('p','d','s','1','test',[],source_representation=metadata))
            else:
                c.validate_json_resources({'sourceRepresentation':metadata})
            results[gate]='accepted'
        except ValueError as exc:
            results[gate]=type(exc).__name__
        assert (results[gate]=='accepted')==accepted,(name,gate,results)
    observations.append(dict(case=name,expectedAccepted=accepted,results=results))
for name,item in [('dict-subclass',DictSubclass(x=1)),('list-subclass',ListSubclass([1])),('tuple-subclass',TupleSubclass([1])),('ordered-dict',OrderedDict(x=1)),('bytes',b'x'),('decimal',Decimal('1.5')),('datetime',datetime(2020,1,1)),('complex',complex(1,2))]:
    check(name,{'nested':item},False)
for name,item in [('nested-tuple-finite',((1.5,None,True,'\U0001f600'),)),('dict-list-tuple-finite',{'a':[(1.5,{'\u00e9':2,'e\u0301':3})]})]:
    check(name,{'nested':item},True)
for number in [float('nan'),float('inf'),float('-inf')]:
    check('dict-list-tuple-'+str(number),{'x':[{'y':((number,),)}]},False)
for depth in [127,128,129]:
    item=1.5
    for _ in range(depth-2): item=(item,)
    meta={'x':item}
    row={'case':'tuple-depth-'+str(depth)}
    try:
        c.validate_json_resources({'sourceRepresentation':meta}); row['resources']='accepted'
    except ValueError as exc: row['resources']=type(exc).__name__
    assert (row['resources']=='accepted')==(depth<=128)
    try:
        model=c.build_envelope_with_rule_results('p','d','s','1','test',[],[],source_representation=meta)
        leaf=model.sourceRepresentation['x']
        for _ in range(depth-2):
            assert len(leaf)==1
            leaf=leaf[0]
        assert leaf==1.5
        row['factory']='accepted-with-leaf-preserved'
    except ValueError as exc:
        row['factory']='explicit-'+type(exc).__name__
        row['message']=str(exc)
    assert depth<=128 or row['factory'].startswith('explicit-')
    observations.append(row)
# Existing typed record path is exercised structurally, not treated as an opaque object.
record=c.EvidenceRow(ruleId='R',objectId='O',canonicalStatus=c.CanonicalStatus.UNSUPPORTED,detail='\U0001f600')
check('typed-record-finite',{'nested':(record,)},True)
record.detail='\ud800'
check('typed-record-invalid-unicode',{'nested':(record,)},False)
(OUT/'domain-probe.json').write_text(json.dumps(observations,indent=2),encoding='utf-8')
print(json.dumps(observations,indent=2))
print('PASS cases='+str(len(observations)))
