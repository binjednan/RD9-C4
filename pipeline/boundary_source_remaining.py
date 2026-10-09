# coding:utf-8
"""Literal C*/CB1 and block infill of the source U-shaped boundary wall.

Retires only the three audited generic A.site envelopes. Existing S bodies are
unchanged. Above-grade C* height is derived from two source concrete datums and
the CB1 depth; below-grade retaining walls already present are never duplicated.
"""
import copy
import hashlib
import json
from pathlib import Path
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

DATA_PATH=Path(__file__).with_name('data')/'boundary_source_remaining.json'
TYPES={
 'boundary_column_cstar':{'n':'عمود سور C* — المسقط الإنشائي','cf':'derived',
  'sp':[['المسقط','41 حدًا مغلقًا فعليًا من S-COLUMN في STR32'],['الجزء الممثل','CL−0.10→أسفل CB1 +2.70 م']],
  'sr':['STR ص31 S26 وص32 S27؛ ARCH1 ص4 A101 وص16 A400'],
  'asm':['ارتفاع الجزء فوق الأرض مشتق من المراجع وسماكة CB1، ولا يمثل اعتماد اتصال أو تسليح.']},
 'boundary_coping_cb1':{'n':'كمرة تغطية السور CB1','cf':'derived',
  'sp':[['القطاع الموسوم','200×300 مم'],['القمة','CL+3.00 م'],['التقسيم','6 قطع مستمرة فوق41 رأس عمود؛37 وسمًا للبحور']],
  'sr':['STR ص32 S27 مسقط BEAM وجدول CB1 وقطاعا BW1/BW2؛ STR ص31 فواصل2CM'],
  'asm':['القطع العلوي عند الفاصل مشتق من نص STR31 وحدّي عموديه؛ خط BEAM العلوي في STR32 مستمر رسوميًا.',
   '2T12 في الجدول مقابل2T16 في القطاع؛ لم يُنشأ تسليح قبل حسم اختلاف المصدر.']},
 'boundary_block_infill':{'n':'حشوة بلوك سور بين أعمدة C*','cf':'derived',
  'sp':[['المادة','BLOCK WALL — BW2'],['العدد','37 حشوة بين الوجوه الفعلية، خارج3 فواصل'],['القمة','+2.70 م مشتقة من أسفل CB1']],
  'sr':['STR ص32 S27 — المسقط وقطاع BW2؛ ARCH1 ص16 A400'],
  'asm':['نوع البلوك والتشطيب والطلاء غير محددة هنا؛ الألوان محايدة للعرض.']},
}
MATS={
 'bnd_concrete':{'name':'خرسانة سور C*/CB1 — لون عرض محايد','color':'#c5c6c8','rough':.8},
 'bnd_block':{'name':'بلوك سور — نوع البلوك والتشطيب غير محددين','color':'#d0d1d3','rough':.85},
}
def _sha(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def _poly(g):
 if g[0]=='p':return Polygon(g[1],g[4] if len(g)>4 and g[4] else [])
 if g[0]=='r':return box(g[1],g[2],g[3],g[4])
 raise ValueError(g[0])
def _z(g):return (g[2],g[3]) if g[0]=='p' else (g[5],g[6])

def build(M,els=None,verbose=False):
 els=M['els'] if els is None else els
 D=json.loads(DATA_PATH.read_text())
 own=set(D['records'])
 old_s={e['id']:copy.deepcopy(e) for e in els if e['c'].startswith('S.') and e['id'] not in own}
 retire={r['id']:r for r in D['retired_envelopes']}
 retired_now=[]
 for e in els:
  if e['id'] not in retire:continue
  q=retire[e['id']]
  if (e['c'],e['t'],e['l'],e['g'])!=(q['category'],q['type'],q['level'],q['geometry']):
   raise ValueError('BND retirement guard differs: '+e['id'])
  retired_now.append(e['id'])
 els[:]=[e for e in els if e['id'] not in own and e['id'] not in retire]
 source=('STR ص31–32 S26/S27: سور U على حد الأرض4570×4570سم وتوقف300سم أمامًا؛ '
         '41C* مغلقة،37CB1 وسوم بحور،كمرة مستمرة فوق رؤوس الأعمدة بعرض200 وعمق300مم وقمة CL+3.00. '
         'BW2 يصرح BLOCK WALL؛ استبدلت3 أجسام A.site تجميعية بـ37 حشوة،41 عمودًا و6 قطع غطاء دون تراكب. '
         'ربط الزوايا إلى A101 المحوري وA400، لا أقرب جدار ولا تحويل تفصيل NTS. '
         'تسليح الجدول2T12 يختلف عن قطاع2T16؛ عرض الفواصل المرقم2سم لا يساوي قياس الرمز وحده.')
 if source not in M['sp']:M['sp'].append(source)
 si=M['sp'].index(source);M['mats'].update(copy.deepcopy(MATS))
 for eid,row in D['records'].items():
  q=row['source'];a={
   'kind':row['source_role'],'source_kind':q['source_kind'],
   'source_page':q['source_page'],'source_sheet':q['source_sheet'],
   'source_pdf_sha256':q['source_pdf_sha256'],'source_layer':copy.deepcopy(q['source_layer']),
   'source_drawing_indices':copy.deepcopy(q['source_drawing_indices']),
   'source_pdf_points':copy.deepcopy(q['source_pdf_points']),
   'source_transform':copy.deepcopy(q['source_transform']),
   'source_xy':copy.deepcopy(q['source_xy']),'source_boundary_pdf':copy.deepcopy(q['source_boundary_pdf']),
   'source_locked_xy':True,'source_semantics_checked':True,
   'source_structural_XY_verified':row['c']=='S.col',
   'source_footprint_derived':row['c']!='S.col',
   'source_Z_verified':row['z_verified'],'source_height_derived':not row['z_verified'],
   'source_z_proof':copy.deepcopy(D['source_datums']),
   'source_material_class_verified':True,'source_material_verified':False,
   'source_material_grade_verified':False,'source_finish_verified':False,
   'source_physical_color_verified':False,
   'source_reinforcement_verified':False,'source_bearing_verified':False,
   'boundary_source_record':eid,'scope_above_grade_only':True,
   'physical_joint_width_pending':True,'assumed':row['derived_basis_ar']+
    ' نوع البلوك/الطلاء وتفاصيل الربط والتسليح والتنفيذ غير معتمدة؛ اللون محايد للعرض.'}
  if row.get('perimeter_face'):a['perimeter_face']=row['perimeter_face']
  if row.get('bounded_by_column_drawings'):a['bounded_by_column_drawings']=row['bounded_by_column_drawings']
  if q.get('head_union_drawing_indices'):a['source_head_union_drawing_indices']=copy.deepcopy(q['head_union_drawing_indices'])
  els.append({'id':eid,'c':row['c'],'l':'G','g':copy.deepcopy(row['g']),
   't':row['t'],'m':row['m'],'mark':row['mark'],'grp':'boundary-source-Cstar-CB1','a':a,'s':[si]})
 new=[e for e in els if e['id'] in own]
 original_area=sum(_poly(r['geometry']).area for r in D['retired_envelopes'])
 original_volume=sum(_poly(r['geometry']).area*(_z(r['geometry'])[1]-_z(r['geometry'])[0])/10000 for r in D['retired_envelopes'])
 groups={c:[e for e in new if e['c']==c] for c in ('A.site','S.col','S.beam')}
 area={c:sum(_poly(e['g']).area for e in items) for c,items in groups.items()}
 volume={c:sum(_poly(e['g']).area*(_z(e['g'])[1]-_z(e['g'])[0])/10000 for e in items) for c,items in groups.items()}
 col=unary_union([_poly(e['g']) for e in groups['S.col']]);beam=unary_union([_poly(e['g']) for e in groups['S.beam']])
 head_uncovered_area=col.difference(beam).area
 pair_overlap=[]
 for i,a in enumerate(new):
  for b in new[i+1:]:
   za,zb=_z(a['g']),_z(b['g']);h=min(za[1],zb[1])-max(za[0],zb[0])
   if h<=0:continue
   intersection=_poly(a['g']).intersection(_poly(b['g'])).area
   if intersection>0:pair_overlap.append({'ids':[a['id'],b['id']],'area_cm2':intersection,'volume_m3':intersection*h/10000})
 retained=[e for e in els if e['id'] in old_s]
 old_s_same=len(retained)==len(old_s) and all(e==old_s[e['id']] for e in retained)
 if not old_s_same:raise AssertionError('BND changed an existing S body')
 stats={'generated':len(new),'block_infill':37,'columns':41,'coping_segments':6,
  'new_structural_ids':[e['id'] for e in new if e['c'].startswith('S.')],
  'retired_now':retired_now,'retired_source_envelopes':list(retire),
  'old_S_objects_unchanged':old_s_same,'geometry_sha256':_sha([(e['id'],e['g']) for e in new]),
  'data_sha256':hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
  'source_binding':copy.deepcopy(D['registration_basis']),
  'before_area_cm2':original_area,'before_volume_m3':original_volume,
  'after_area_cm2_by_category':area,'after_volume_m3_by_category':volume,
  'source_column_head_uncovered_area_cm2':head_uncovered_area,
  'positive_volume_overlap_pairs':pair_overlap,
  'assembly_positive_volume_overlap_count':len(pair_overlap),
  'pending':copy.deepcopy(D['pending_ar'])}
 M.setdefault('meta',{})['boundary_source_remaining']=stats
 if verbose:print('BND:',len(new),'old S unchanged:',old_s_same,'old envelopes retired:',len(retired_now))
 return stats
