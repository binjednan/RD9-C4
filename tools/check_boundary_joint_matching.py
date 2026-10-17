# coding:utf-8
"""Read-only gate for corrected literal CB1 joints, not the legacy graphic gap."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'pipeline'))
import boundary_joint_matching as B

def audit(M):return B.audit(M)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--model',default=str(ROOT/'src/model.json'));p.add_argument('--output');a=p.parse_args()
 r=audit(json.loads(Path(a.model).read_text()))
 if a.output:Path(a.output).write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:r[k] for k in ('pass','matched_count','conflict_count','errors')},ensure_ascii=False));raise SystemExit(0 if r['pass'] else 1)
