"""D16: one assembly of two drawn open leaves and two outerJAMB plan proxies.
Conditional opening-height envelope; no steel-gauge/host/installation inference.
API apply(M,els=None), build alias. No independent file or model writes.
"""
import copy,functools,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA_PATH=Path(__file__).with_name('data')/'d16_source_remaining.json'
FROZEN_DATA_SHA='41055c3747ad6588cd11fa7e3628162d8413ba75c20fae9289d07350f0093131'
TYPES={
 'd16_drawn_leaf_proxy':{'n':'D16 — درفة مفتوحة في وضع المسقط؛ نطاق رسومي مشروط','cf':'derived','sp':[['موضع المجموعة','Stair case03؛ A102→A604'],['فتحة المجموعة','125سم عرضًا ×110سم ارتفاعًا (A604)، لا أبعاد تصنيع كل جزء'],['المادة النصية','Galvanized steel leaf؛ A604 trace170'],['الفتح','Door opens to outside؛ الدرفتان في وضع المسقط المرسوم'],['تعارض المصادر','A604:90min وعرض125cm؛ BOQ:8.3.12 N/A وعرض125mm كما طُبع']],'asm':['عمق/سماكة الصاج والمصنع واللون والتثبيت والعتاد غير محددة.','+.20..+1.30 نطاق عرض مشروط من فتحة110سم فوق بسطة+.20؛ لا قبول Z أو ارتفاع كل جزء.','أثر الدرفة في المسقط لا يُرقّى إلى مقاس جسم تنفيذي، ولا يُحسم تعارض90min/N/A أو صفر BOQ.'],'sr':['ARCH1 ص5 A102؛ drawings47675–47682','ARCH2 ص5 A604؛ traces161/162/169/170/171/89','BOQ ص8،8.3.12؛ trace347']},
 'd16_drawn_outer_jamb_proxy':{'n':'D16 — مقطعJAMBخارجي كما رُسم؛ نطاق مشروط','cf':'derived','sp':[['موضع المجموعة','Stair03، مقطعاJAMBالخارجيان فقط'],['المادة النصية','Galvanized steel frame؛ A604 trace170'],['مصدر البصمة','A102 drawings47675 و47679؛ لا قوائم meetingوسطية']],'asm':['عمق الإطار وسماكة الصاج والتثبيت غير مثبتة؛ البصمة رسومية.','النطاق+.20..+1.30 مشروط بفتحة المجموعة، وليس طول كل جزء معتمدًا.','لون العرض حيادي افتراضي؛ لا تُنشأ فتحة إنشائية أو عتاد من القوس أو وسْم الباب.'],'sr':['ARCH1 ص5 A102','ARCH2 ص5 A604','BOQ ص8: تعارض125X1100mm/N/A']}}
MATS={'d16_galv_source':{'name':'Galvanized steel — A604:D16 literal؛ العرض حيادي افتراضي','color':'#c6c9cc','rough':.65,'metal':.45,'source_material_literal':'Galvanized steel','physical_color_literal':'unknown','physical_color_hex':None,'display_colour_source_verified':False,'installed_material_grade_gauge_product_accepted':False,'source_refs':['ARCH2:5/A604/trace170'],'assignment_limit':'D16 material class literal only; physical gauge/product/finish colour and installation unverified'}}
@functools.lru_cache(maxsize=2)
def _verify(text,stats):
 if hashlib.sha256(text.encode()).hexdigest()!=FROZEN_DATA_SHA:raise ValueError('D16 frozen source ledger changed')
 sys.path.insert(0,str(ROOT/'tools'));from check_d16_source_remaining import verify_source
 q=verify_source(json.loads(text))
 if q['errors']:raise ValueError('D16 original source guard: '+','.join(q['errors']))
 return True
def _data():
 text=DATA_PATH.read_text();D=json.loads(text);ps=sorted({q['source_pdf']for q in D['source_pages'].values()});_verify(text,tuple((p,Path(p).stat().st_size,Path(p).stat().st_mtime_ns)for p in ps));return D
def _attrs(D,row):
 return{'d16_source_remaining':True,'d16_source_data_sha256':FROZEN_DATA_SHA,'source_kind':'d16_drawn_plan_polygon_proxy','source_geometry_review':'original_open_plan_polygon_graphic_only','source_role':row['role'],'source_page':'ARCH1:5','source_layer':row['source_layer'],'source_drawing_indices':copy.deepcopy(row['source_drawing_indices']),'source_raw_items':copy.deepcopy(row['source_raw_items']),'source_pdf_points':copy.deepcopy(row['source_pdf_polygon']),'source_xy':copy.deepcopy(row['source_xy_polygon_cm']),'source_transform':copy.deepcopy(D['source_pages']['ARCH1:5']['source_transform']),'source_pdf_sha256':D['source_pages']['ARCH1:5']['source_pdf_sha256'],'source_locked_xy':True,'source_plan_polygon_verified':True,'source_material_class_literal_verified':True,'source_material_class_literal':'Galvanized steel','source_material_reference':'ARCH2:5/A604/trace170','source_opening_dimensions_literal_verified':True,'source_opening_width_cm':125,'source_opening_height_cm':110,'source_Z_conditional_envelope':True,'source_Z_envelope_basis':'A102/A604 بسطةStair03 FFL+.20، وفتحة110سم؛ عرض+.20..+1.30 مشروط، وليس ارتفاع/منسوب كل جزء معتمدًا','source_dimensions_verified':False,'source_physical_body_verified':False,'source_Z_verified':False,'source_absolute_Z_verified':False,'source_material_verified':False,'source_mount_verified':False,'source_ports_verified':False,'source_contact_verified':False,'source_colour_verified':False,'source_fire_rating_accepted':False,'source_part_height_verified':False,'source_fire_rating_literal_verified':True,'source_fire_rating_literal':'A604:90min؛ BOQ:N/A (تعارض غير محسوم)','source_conflicts':copy.deepcopy(D['confirmed_literal_source_conflicts']),'no_connectors':True,'assumed':'البصمة أثر رسومي مستقل. سماكة الصاج وعمق الإطار التنفيذي والتثبيت والعتاد واللون غير محددة. نطاق+.20..+1.30 مشروط لفتحة المجموعة، لا قبول ارتفاع كل جزء أو Zتركيبه. لم تُحرّك فتحة الحاجز القديمة إلى المصدر بهذه الإضافة.'}
def _ref(M,t):
 pool=M.setdefault('sp',[])
 if t not in pool:pool.append(t)
 return pool.index(t)
def apply(M,els=None):
 D=_data();els=M['els']if els is None else els;ids=set(D['records']);counts={i:sum(e['id']==i for e in els)for i in ids};present={i for i,n in counts.items()if n};by={e['id']:e for e in els}
 # Check all current evidence before adding references/materials/parts.
 for e in els:
  if((e.get('a')or{}).get('d16_source_remaining')or e.get('grp')=='D16-G-source'or'-D16'in e['id'])and e['id']not in ids:raise ValueError('D16 unexpected source identity: '+e['id'])
 if present and(present!=ids or any(counts[i]!=1 for i in ids)):raise ValueError('D16 missing/duplicate existing source part')
 if not present and M.get('meta',{}).get('d16_source_remaining'):raise ValueError('D16 previously built inventory missing')
 if present:
  sys.path.insert(0,str(ROOT/'tools'));from check_d16_source_remaining import audit
  q=audit({'els':els})
  if q['summary']['findings']or q['summary']['uncovered']:raise ValueError('D16 exact existing body/source scope guard failed')
 else:
  gs=[q['g']for q in D['records'].values()]
  if any(e['c']=='A.door'and e['l']=='G'and e['g']in gs for e in els):raise ValueError('D16 exact graphic already exists under another identity')
 created=[]
 if not present:
  src=['ARCH1 ص5 A102: رسمةD16 الأصلية47675–47682؛ الدرفتان في وضعهما المفتوح ومقطعاJAMBالخارجيان فقط','ARCH2 ص5 A604: فتحة125×110سم/FFL+.20/Galvanizedsteel/outsideopen؛ النطاقZمشروط','BOQ ص8،8.3.12:125X1100mmوN/A مقابلA604:125cmو90min؛ تعارض ظاهر بلا تصحيح تلقائي']
  for eid,row in D['records'].items():
   els.append({'id':eid,'c':row['c'],'t':row['t'],'l':row['l'],'m':row['m'],'grp':row['grp'],'g':copy.deepcopy(row['g']),'a':_attrs(D,row),'s':[_ref(M,t)for t in src]});created.append(eid)
 for k,v in TYPES.items():M.setdefault('types',{})[k]=copy.deepcopy(v)
 for k,v in MATS.items():M.setdefault('mats',{}).setdefault(k,copy.deepcopy(v))
 stats={**D['summary'],'source_data_sha256':FROZEN_DATA_SHA,'created_this_apply':len(created),'created_ids_this_apply':created,'controlled_ids':sorted(ids),'source_scope':'Four original plan polygons only; conditional opening envelope; no numeric physical part dimensions/Z/installed material acceptance','no_S_geometry_change':True}
 M.setdefault('meta',{})['d16_source_remaining']=stats;return stats
build=apply
