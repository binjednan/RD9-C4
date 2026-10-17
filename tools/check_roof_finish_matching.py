"""Prove that matching depends on actual roof geometry, not trusted metadata."""
import copy
import json
from pathlib import Path
import sys

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'pipeline'))
import roof_finish_matching as RF


def run(M):
    before=RF.digest(M)
    proof=RF.audit(M)
    assert RF.digest(M)==before
    ids=set(proof['accepted_ids'])
    subset={'els':[copy.deepcopy(e) for e in M['els'] if e['id'] in ids]}
    # Remove all previous source flags: raw geometry and original PDFs still pass.
    for e in subset['els']:e.pop('a',None)
    assert RF.audit(subset)['results']==proof['results']
    guards=[]
    for kind in ('shifted_xy','changed_thickness','changed_upstand_height'):
        bad=copy.deepcopy(subset)
        e=next(e for e in bad['els'] if e['id']==('A.wall-R-SRF0003' if kind=='changed_upstand_height' else 'A.floor-R-SRF0002'))
        e['a']={'source_Z_verified':True,'source_semantics_checked':True,'source_locked_xy':True}
        if kind=='shifted_xy':
            for p in e['g'][1]:p[0]+=1
        elif kind=='changed_thickness':e['g'][2]-=.001
        else:e['g'][3]+=.01
        frozen=RF.digest(bad)
        try:RF.audit(bad)
        except AssertionError:
            assert RF.digest(bad)==frozen
            guards.append(kind)
        else:raise AssertionError('Unmatched geometry accepted despite source flags: '+kind)
    return {'schema':'c4.roof-finish-matching-guards.v1','pass':True,'source_reopened':True,
            'accepted_count':len(ids),'metadata_removed_still_passes':True,
            'changed_geometry_despite_positive_metadata_rejected':guards,'model_unchanged':True}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--model',type=Path,default=REPO/'src/model.json')
    p.add_argument('--output',type=Path)
    args=p.parse_args()
    result=run(json.loads(args.model.read_text()))
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))
