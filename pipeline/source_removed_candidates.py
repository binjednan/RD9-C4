"""Draw eleven original FF-100 plan symbols with their source and assumptions."""
import copy
import json
from pathlib import Path
DATA_PATH=Path(__file__).with_name('data')/'source_removed_candidates.json'
TYPES={'source_fire_plan_symbol':{'n':'رمز الإطفاء الأصلي من المسقط','asm':['منسوب العرض وسماكة الخط افتراضان؛ نوع الرشاش وتركيبه غير مستنتجين.']}}
MATS={'source_fire_plan_ink':{'name':'خطوط رمز الإطفاء من المصدر','color':'#c65a4d','rough':.8}}

def data():
    return json.loads(DATA_PATH.read_text())

def apply(M,els=None):
    """Append original source shapes once; never reuse a legacy retired ID."""
    D=data();target=M['els'] if els is None else els
    current={e['id']:e for e in target}
    for e in D['elements']:
        have=current.get(e['id'])
        if have is not None and (have.get('g')!=e['g'] or have.get('t')!=e['t'] or have.get('a',{}).get('source')!=e['a']['source']):
            raise ValueError('Existing identity has different source geometry: '+e['id'])
    for k,v in TYPES.items():M.setdefault('types',{}).setdefault(k,copy.deepcopy(v))
    for k,v in MATS.items():M.setdefault('mats',{}).setdefault(k,copy.deepcopy(v))
    label='Mechanical Drawings Part II (1).pdf — ص 10 — FF-100 — رموز المسقط الأصلية'
    sp=M.setdefault('sp',[])
    if label not in sp:sp.append(label)
    for saved in D['elements']:
        if saved['id'] in current:continue
        e=copy.deepcopy(saved);e['s']=[sp.index(label)];target.append(e)
    M.pop('sourceRemovedCandidates',None)
    return len(D['elements'])
