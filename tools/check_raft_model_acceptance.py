# coding:utf-8
"""Read-only CLI for raw-source raft geometry matching and its explicit conflict."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pipeline'))
import raft_model_acceptance as R

def audit(M):return R.audit(M)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--model',default=str(ROOT/'src/model.json'));p.add_argument('--output')
 a=p.parse_args();r=audit(json.loads(Path(a.model).read_text()))
 if a.output:Path(a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:r[k] for k in ('pass','matched_count','conflict_count','errors')},ensure_ascii=False))
 raise SystemExit(0 if r['pass'] else 1)
