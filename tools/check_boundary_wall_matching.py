"""Read-only boundary wall source matching gate."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'pipeline'))
import boundary_wall_matching as B

def audit(M):return B.audit(M)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model',default=str(ROOT/'src/model.json'));p.add_argument('--output');a=p.parse_args()
    try:r=audit(json.loads(Path(a.model).read_text()))
    except Exception as e:r={'pass':False,'errors':[str(e)],'matched_count':0,'conflict_count':0}
    if a.output:Path(a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:r[k]for k in ('pass','matched_count','conflict_count','errors')},ensure_ascii=False))
    raise SystemExit(0 if r['pass'] else 1)
