"""One exact guarded architectural plan correction; no model IO or source-Z claim."""
import copy,hashlib,json
from pathlib import Path
DATA_PATH=Path(__file__).with_name('d16_host_source_correction.json')
if not DATA_PATH.exists():DATA_PATH=Path(__file__).parent/'data'/'d16_host_source_correction.json'
DATA_SHA='891a264961fee496aeb26b1c260417fe168f6b5b3e0cd58712316a3459e2f441'
TYPES={'wall_plan_source_proxy':{'n':'حاجز درج03 — مسقط معماري من المصدر؛ جسم رأسي مفترض','cf':'derived','sp':[['المسقط','A102 رسم37188، جدار U مع عودة مركزية؛ رجلان نحو20سم وعودة نحو10سم'],['حد الإثبات','XY ودلالة الجدار المعماري فقط؛ لا يثبت RC أو القاعدة أو التسليح أو المادة']], 'sr':['ARCH1 ص5 A102 رسم37188','ARCH2 ص5 A604 رسم4780، A-WALL'],'asm':['نطاق العرض−0.45..+1.40م باقٍ من التمثيل السابق، غير معتمد كحد إنشائي. المادة والتثبيت والكسوة معلقة.']}}
MATS={'wall_source_unknown':{'name':'مادة الحاجز غير مثبتة؛ لون عرض حيادي','color':'#bdbdbd','rough':.8,'source_material_literal':'unknown','physical_color_literal':'unknown','physical_color_hex':None,'display_colour_source_verified':False,'display_colour_only':True}}
def data():
 raw=DATA_PATH.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=DATA_SHA:raise ValueError('D16 host frozen data changed')
 D=json.loads(raw)
 for p in D['source_pages']:
  if hashlib.sha256(Path(p['pdf']).read_bytes()).hexdigest()!=p['sha256']:raise ValueError('D16 host original PDF changed')
 return D
def _after(r):
 e=copy.deepcopy(r['after_e']);e['a']['source_d16_host_data_sha256']=DATA_SHA;return e
def apply(M,els=None):
 els=M['els']if els is None else els;D=data();by={e['id']:e for e in els}
 if len(by)!=len(els):raise ValueError('D16 host duplicate identity')
 for eid,r in D['records'].items():
  expected_generated=copy.deepcopy(r['before_e']);expected_generated.pop('q',None)
  if by.get(eid)not in[r['before_e'],expected_generated,_after(r)]:raise ValueError('D16 host exact fullobject guard: '+eid)
 for eid,e in D['unchanged_door_fullobjects'].items():
  if by.get(eid)!=e:raise ValueError('D16 correct source door changed: '+eid)
 for eid,r in D['records'].items():by[eid].clear();by[eid].update(_after(r))
 M.setdefault('types',{}).update(copy.deepcopy(TYPES));M.setdefault('mats',{}).update(copy.deepcopy(MATS))
 stats={**D['summary'],'source_data_sha256':DATA_SHA,'scope':'XY architectural wall contour only; retained assumed Z; no RC/material/physical body acceptance'}
 M.setdefault('meta',{})['d16_host_source_correction']=stats
 return{**stats,'checks':[{'id':eid,'pass':True,'source_plan_XY_verified':True,'source_physical_body_Z_material_verified':False}for eid in D['records']],'global_findings':[],'uncovered':[]}

def issue_records(M):
 D=data();by={e['id']:e for e in M['els']}
 for eid,r in D['records'].items():
  if by.get(eid)!=_after(r):raise ValueError('D16 DD corrected host guard: '+eid)
 return[copy.deepcopy(D['after_DD_row']),copy.deepcopy(D['source_body_gap'])]
def apply_issues(M):
 rows=issue_records(M);owned={q['id']for q in rows};dd=M.setdefault('drawingIssues',[])
 dd[:]=[q for q in dd if q['id']not in owned]+rows
 return{'owned_issue_ids':sorted(owned),'source_physical_acceptance':False}
