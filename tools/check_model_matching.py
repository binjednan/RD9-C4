# -*- coding: utf-8 -*-
"""Validate register integrity, not a substitute for native drawing proofs."""
import argparse, copy, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pipeline'))
import model_matching as MM

def audit(M):
    if M.get('meta',{}).get('owner_render_only'):
        present='modelMatching' in M
        return {'pass':not present,'errors':['Retired conformity register is present'] if present else [],
                'counts':None,'scope':'Owner drawing-only mode: conformity register must remain absent; source geometry gates remain independent.'}
    errors=[]
    try:
        stored=M['modelMatching']
        rebuilt=MM.build(dict(M),stored['records'])
        for k in ('model_elements','reviewed_elements','counts','records','model_geometry_sha256','criteria_ar'):
            if stored[k]!=rebuilt[k]:errors.append('Register differs: '+k)
    except Exception as exc:errors.append(str(exc))
    return {'pass':not errors,'errors':errors,'counts':M.get('modelMatching',{}).get('counts'),
        'scope':'identity, geometry binding, count and conflict-link integrity; native PDF proofs are separate'}

def negative_guards(M):
    records=M['modelMatching']['records'];matched=next(r['id']for r in records if r['status']=='matched')
    conflict=next(r['id']for r in records if r['status']=='conflict')
    results=[]
    for name in ('geometry_change','identity_change','shape_flag_removed','source_removed','duplicate_record','conflict_link_removed','count_changed'):
        # Copy only edited collections to avoid shared mutation of the fixture.
        t=dict(M);t['modelMatching']=copy.deepcopy(M['modelMatching'])
        rs={r['id']:r for r in t['modelMatching']['records']}
        if name in ('geometry_change','identity_change'):
            t['els']=[copy.deepcopy(e)if e['id']==matched else e for e in M['els']]
            e=next(e for e in t['els']if e['id']==matched)
            if name=='geometry_change':e['g']=copy.deepcopy(e['g']);e['g'][2]+=0.01
            else:e['t']+='-unproved'
        elif name=='shape_flag_removed':rs[matched]['shape_match']=False
        elif name=='source_removed':rs[matched]['source_refs']=[]
        elif name=='duplicate_record':t['modelMatching']['records'].append(copy.deepcopy(rs[matched]))
        elif name=='conflict_link_removed':rs[conflict]['conflict_ids']=[]
        else:t['modelMatching']['counts']['matched']+=1
        result=audit(t);results.append({'guard':name,'rejected':not result['pass'],'errors':result['errors']})
    return {'pass':all(r['rejected']for r in results),'tests':results}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',default=ROOT/'src/model.json');p.add_argument('--output');p.add_argument('--guards',action='store_true');a=p.parse_args()
    M=json.loads(Path(a.model).read_text());r=audit(M)
    if a.guards:r['guards']=negative_guards(M);r['pass']=r['pass']and r['guards']['pass']
    if a.output:Path(a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2))
    print(json.dumps(r,ensure_ascii=False));raise SystemExit(0 if r['pass']else 1)
