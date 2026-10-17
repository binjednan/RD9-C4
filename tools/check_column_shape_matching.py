"""Targeted atomic identity-edit and independent column-matching gate."""
import copy
import json
from pathlib import Path
import sys
from unittest.mock import patch

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'pipeline'))
import column_shape_matching as C


def run(M):
    D=C.data();target=D['identity_correction']['id']
    unchanged={e['id']:C.digest(e) for e in M['els'] if e['id']!=target}
    bodies={e['id']:C.digest(e['g']) for e in M['els']}
    # Reopen and guard all original PDF witnesses once. Reuse only these fresh
    # immutable source observations for injected-invalid-model guard cases.
    fresh=C._raw_sources(D)
    with patch.object(C,'_raw_sources',return_value=fresh):
        proof=C.apply(M)
        assert proof['matched_count']==8 and proof['conflict_count']==1
        assert {e['id']:C.digest(e) for e in M['els'] if e['id']!=target}==unchanged
        assert {e['id']:C.digest(e['g']) for e in M['els']}==bodies
        ids=set(D['records'])|{target}
        subset={'els':[copy.deepcopy(e) for e in M['els'] if e['id'] in ids]}
        once=copy.deepcopy(subset)
        assert C.apply(subset)['identity_changed']==0 and subset==once
        for e in subset['els']:e.pop('a',None)
        no_meta=C.audit(subset)
        assert no_meta['matched_count']==8 and no_meta['conflict_count']==1
        assert no_meta['results']==proof['results']
        rejected=[]
        for kind in ('missing','duplicate','identity_changed','planted_geometry_changed'):
            bad=copy.deepcopy(subset)
            e=next(e for e in bad['els'] if e['id']==target)
            if kind=='missing':bad['els'].remove(e)
            elif kind=='duplicate':bad['els'].append(copy.deepcopy(e))
            elif kind=='identity_changed':e['t']='col_C7'
            else:e['g'][2]-=.01
            frozen=copy.deepcopy(bad)
            try:C.apply(bad)
            except ValueError:
                assert bad==frozen,'Partial mutation on invalid model: '+kind
                rejected.append(kind)
            else:raise AssertionError('Missing guard: '+kind)
        continued=[]
        for kind in ('shifted_C1_XY','changed_C1_height'):
            bad=copy.deepcopy(subset);e=next(e for e in bad['els'] if e['id']=='S.col-B-0001')
            e['a']={'source_Z_verified':True,'source_locked_xy':True,'source_semantics_checked':True}
            if kind=='shifted_C1_XY':
                for p in e['g'][1]:p[0]+=1
            else:e['g'][3]+=.01
            frozen=C.digest(bad);r=C.audit(bad)
            assert C.digest(bad)==frozen and r['matched_count']==7 and r['conflict_count']==2
            row=next(x for x in r['results'] if x['id']==e['id'])
            assert row['status']=='conflict' and row['conflict_ids'] and not row['shape_match']
            continued.append(kind)
    issues=C.issue_records(M,proof)
    proof['issues']=issues
    gate={'schema':'c4.column-shape-matching-gate.v1','pass':True,'source_reopened':True,
          'matched_count':8,'conflict_count':1,'identity_changed_on_input':proof['identity_changed'],
          'all_body_geometries_unchanged':len(bodies),'unrelated_full_objects_unchanged':len(unchanged),
          'idempotence_passed':True,'metadata_not_used_as_proof':True,
          'atomic_rejections':rejected,'local_conflicts_do_not_block_remaining_matches':continued,
          'issue_ids':[r['id'] for r in issues]}
    return proof,gate


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--model',type=Path,default=REPO/'src/model.json')
    p.add_argument('--output',type=Path)
    p.add_argument('--source-output',type=Path)
    args=p.parse_args()
    proof,gate=run(json.loads(args.model.read_text()))
    for path,value in ((args.output,gate),(args.source_output,proof)):
        if path:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(gate,ensure_ascii=False))
