"""Replace204 guessed closed leaf bodies using six independent copied templates.

apply(M,els=None) preserves exact oldID/u/u2 on81 raw paired-jamb openings.
Only source composite leaf envelopes are generated. No jamb/frame/hardware,
mechanical hinge, swing-arc body, host opening, colour or contact is invented.
"""
from pathlib import Path
import sys,json,copy,collections
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE));TOOLS=HERE.parent/'tools'
if TOOLS.is_dir():sys.path.insert(0,str(TOOLS))
import check_door_source_templates as G
DATA_PATH=HERE/'data/door_source_templates.json'
TYPES={}
for code in['D1','D2','D3','D4','D5','D7']:
 fire={'D1':'60 min','D2':'NA','D3':'NA','D4':'60 min','D5':'90 min','D7':'90 min'}[code]
 TYPES['door_source_'+code]={'n':'درفة باب '+code+' من قالب المصدر','cf':'doc','sp':[['الجدول','A700: وسم '+code+'؛ مقاومة الحريق النصية '+fire+'؛ قشرة خشب جوز حسب وصف النوع'],['السمك','A701: '+('48 مم'if code in['D2','D3']else'66 مم')+'، قراءة من التفاصيل الأصلية'],['الفتح','الوضع المفتوح مرسوم في A103/A104؛ D7 يفتح إلى الخارج حسب A700']],'sr':['ARCH1:6 A103 / ARCH1:7 A104','ARCH2:9 A700 / ARCH2:10 A701','ARCH2:1 A600: منسوب الدور'],'asm':['الدرفة غلاف مركب من محيط ارتفاع A700 المقاس بمعايرة أبعاد الفتحة وسمك A701؛ وليست قبولاً لكل جهاز الباب أو المصنع','مرجع الموضع هو نهاية الخشب جهة المفصلة واتجاهها الخام؛ محور المفصلة الميكانيكي والربط بالمضيف غير مثبتين','الإطار والأرشيتراف والقفل والأدوات والتلامس واللون الفعلي لم تُنشأ','في D2/D3 نص 6mm MDF والسمك الكلي 48mm محفوظان كلٌ بنطاق مصدره؛ توزيع طبقات الدرفة غير معتمد']}

def apply(M,els=None):
 els=M['els']if els is None else els
 if G.sha(DATA_PATH)!=G.FROZEN_SHA:raise ValueError('Door frozen source data changed')
 D=json.loads(DATA_PATH.read_text());proof=G.verify_source(D)
 if not proof['pass']:raise ValueError('Original door source proof failed: '+str(proof['global_findings'])+' '+str([q for q in proof['source_plan_checks']if not q['pass']][:2]))
 records=D['instances'];before=D['original_bodies'];by=collections.defaultdict(list)
 for e in els:by[e['id']].append(e)
 if any(len(by[eid])!=1 for eid in records):raise ValueError('Exact204 existing door IDs must be present once')
 extras=[e['id']for e in els if((e.get('a')or{}).get(G.OWN_META)or e.get('t','').startswith('door_source_'))and e['id']not in records]
 if extras:raise ValueError('Extra copied door identity: '+str(extras))
 stages=set()
 for eid,r in records.items():
  e=by[eid][0];b=before[eid]
  if(e.get('a')or{}).get(G.OWN_META)==eid:
   stages.add('source')
   if e['g']!=G.expected_g(D,r)or e['c']!=b['c']or e['l']!=b['l']or e.get('t')!='door_source_'+r['code']or any(e.get(k)!=b.get(k)for k in['mark','u','u2']):raise ValueError('Existing copied source door changed: '+eid)
  else:
   stages.add('original')
   if any(e.get(k)!=b.get(k)for k in['id','g','c','t','l','mark','u','u2','m']):raise ValueError('Original body/identity/unit guard failed: '+eid)
 if len(stages)!=1:raise ValueError('Partial copied/original door inventory')
 template_dimensions={c:{'width_cm':t['leaf_width_cm'],'height_cm':t['leaf_height_cm'],'depth_cm':t['leaf_depth_cm']}for c,t in D['templates'].items()};made={}
 for eid,r in records.items():
  t=copy.deepcopy(D['templates'][r['template']]);geometry=copy.deepcopy(template_dimensions[r['template']]);old=before[eid]
  a={'source_door_instance':eid,'source_door_template':r['template'],'source_door_data_sha256':G.FROZEN_SHA,'source_geometry_review':'composite_leaf_template_with_native_hinge_side_endpoint','source_locked_xy':True,'source_hinge_side_anchor_xy_cm':copy.deepcopy(r['source_hinge_side_anchor_xy_cm']),'source_signed_open_vector_xy':copy.deepcopy(r['source_signed_open_vector_xy']),'source_xy':copy.deepcopy(r['source_hinge_side_anchor_xy_cm']),'source_rotation_deg':r['source_rotation_deg'],'source_plan_page':r['source_page'],'source_plan_drawing_indices':list(r['source_drawing_indices']),'source_anchor_kind':r['source_anchor_kind'],'source_level_ffl_m':D['level_datums'][r['level']]['ffl_m'],'source_dimension_scope':{'leaf':geometry,'opening_cm':copy.deepcopy(t['opening_cm']),'leaf_outline':'محيط ارتفاع A700 مقاس بمعايرة الفتحة 120/220؛ السمك الحرفي A701','whole_assembly_verified':False},'source_native_leaf_width_cm':r['source_native_leaf_width_cm'],'source_native_vs_template_width_cm':r['native_vs_template_width_cm'],'source_material_schedule_text':copy.deepcopy(t['schedule_text']),'source_identity_old_id':eid,'source_identity_binding':copy.deepcopy(r['old_identity_binding']),'assumed':'غلاف درفة مركب: نقطة نهاية الخشب جهة المفصلة ثابتة من المسقط، واتجاه الفتح ثابت؛ الفرق بين عرض رمز الخشب والقالب محفوظ ويقع عند الطرف الحر. لا قبول شامل للدرفة أو المفصلة الميكانيكية أو الإطار أو أدوات التركيب أو المضيف أو اللون.'}
  a.update({k:False for k in G.FALSE_FLAGS});e={'id':eid,'c':'A.door','l':r['level'],'t':'door_source_'+r['code'],'mark':r['code'],'g':G.expected_g(D,r),'m':'door_walnut_A700_source','a':a,'s':[f"ARCH1 ص{r['source_page']}: {r['code']} نهاية الدرفة الخشبية جهة المفصلة واتجاه الفتح؛ ARCH2 ص9 A700 وص10 A701"]}
  for key in['u','u2','q','grp','name']:
   if key in old:e[key]=copy.deepcopy(old[key])
  made[eid]=e
 # Keep every oldID and array slot; all nonowned elements are the same objects.
 els[:]=[made[e['id']]if e['id']in made else e for e in els]
 M.setdefault('mats',{}).setdefault('door_walnut_A700_source',{'name':'قشرة خشب جوز حسب A700؛ لون عرض محايد','color':'#d4d8dc','rough':.65,'metal':0,'cf':'doc','color_source_verified':False,'physical_color_literal':'unknown','physical_color_hex':None,'display_color_only':True,'source_refs':['ARCH2:9 A700'],'assignment_limit':'قشرة جوز حرفية للنوع؛ جسم القلب ومقاومة الحريق لكل وصف النوع، دون اعتماد درجة أو طبقات كاملة أو تشطيب اللون أو أجهزة التركيب'})
 normalize_source_indices(M,els)
 M.setdefault('types',{}).update(copy.deepcopy(TYPES));stats={**D['summary'],'replaced_this_apply':204 if stages=={'original'}else 0,'created_leaf_envelopes':204,'data_sha256':G.FROZEN_SHA,'source_body_scope':'derived_composite_leaf_only','source_anchor_scope':'81 raw hinge-side endpoints /204 instances'};M.setdefault('meta',{})['door_source_templates']=stats;return stats
build=apply


def restore_before_post(M,els=None):
 """Restore exact204 original inputs before generic legacy corrections.

 No PDF re-registration: frozen data, exact allowned before/after geometry,
 identity, source metadata and unit guards only. Unrelated elements/slots stay.
 """
 els=M['els']if els is None else els
 if G.sha(DATA_PATH)!=G.FROZEN_SHA:raise ValueError('Door restore frozen data changed')
 D=json.loads(DATA_PATH.read_text());records=D['instances'];before=D['original_bodies'];by=collections.defaultdict(list)
 for e in els:by[e['id']].append(e)
 if any(len(by[k])!=1 for k in records):raise ValueError('Door restore exact204 identity missing/duplicate')
 extras=[e['id']for e in els if((e.get('a')or{}).get(G.OWN_META)or e.get('t','').startswith('door_source_'))and e['id']not in records]
 if extras:raise ValueError('Door restore extra controlled identity')
 state=set()
 for eid,r in records.items():
  e=by[eid][0];b=before[eid];a=e.get('a')or{}
  if a.get(G.OWN_META)==eid:
   state.add('source')
   if e['g']!=G.expected_g(D,r)or(e['c'],e['l'],e.get('t'),e.get('mark'))!=('A.door',r['level'],'door_source_'+r['code'],r['code'])or any(e.get(k)!=b.get(k)for k in['u','u2'])or a.get('source_door_data_sha256')!=G.FROZEN_SHA or a.get('source_hinge_side_anchor_xy_cm')!=r['source_hinge_side_anchor_xy_cm']or a.get('source_signed_open_vector_xy')!=r['source_signed_open_vector_xy']or any(a.get(k)for k in G.FALSE_FLAGS):raise ValueError('Door restore changed source body/identity/metadata: '+eid)
  else:
   state.add('original')
   if any(e.get(k)!=b.get(k)for k in['id','g','c','t','l','mark','u','u2','m']):raise ValueError('Door restore changed original input: '+eid)
 if len(state)!=1:raise ValueError('Door restore partial before/after state')
 if state=={'original'}:return{'restored_this_apply':0,'owned':204,'identity_and_slots_preserved':True}
 els[:]=[copy.deepcopy(before[e['id']])if e['id']in before else e for e in els]
 M.setdefault('meta',{}).pop('door_source_templates',None)
 return{'restored_this_apply':204,'owned':204,'identity_and_slots_preserved':True,'source_bodies_saved_by_frozen_ledger':True}


def normalize_source_indices(M,els=None):
 """Intern only these204 generated citations into M.sp; no geometry/raw replay."""
 els=M['els']if els is None else els
 if G.sha(DATA_PATH)!=G.FROZEN_SHA:raise ValueError('Door citation frozen data changed')
 D=json.loads(DATA_PATH.read_text());sp=M.setdefault('sp',[])
 if any(not isinstance(q,str)for q in sp):raise ValueError('Door citation source pool is not canonical string table')
 by=collections.defaultdict(list)
 for e in els:by[e['id']].append(e)
 if any(len(by[k])!=1 for k in D['instances']):raise ValueError('Door citation exact204 identities missing/duplicate')
 pool={text:i for i,text in enumerate(sp)};n=0;added=0
 for eid,r in D['instances'].items():
  e=by[eid][0];a=e.get('a')or{}
  if e['g']!=G.expected_g(D,r)or a.get(G.OWN_META)!=eid or a.get('source_door_data_sha256')!=G.FROZEN_SHA:raise ValueError('Door citation controlled body guard: '+eid)
  expected=G.source_citations(r);current=e.get('s',[]);decoded=[]
  for ref in current:
   if type(ref)is int and 0<=ref<len(sp):decoded.append(sp[ref])
   elif isinstance(ref,str):decoded.append(ref)
   else:raise ValueError('Door source citation invalid index: '+eid)
  if decoded!=expected:raise ValueError('Door source citation text differs from controlled ledger: '+eid)
  idx=[]
  for text in expected:
   if text not in pool:pool[text]=len(sp);sp.append(text);added+=1
   idx.append(pool[text])
  if e['s']!=idx:n+=1;e['s']=idx
 return{'normalized_elements':n,'owned':204,'new_pool_citations':added,'all_s_are_valid_integer_indices':True,'geometry_unchanged':True}
