"""Scoped DD/CC/material updates for the retained204 door leaf IDs.

append_to(M,els=None,source_audit=None)
update_component_review(M,report,source_audit,beforeM=None,external_report=None)
update_material_review(M,source_audit)

Pass the frozen single-generation source_audit; all current owned bodies/IDs,
units and source flags are checked again cheaply. No register/PDF audit replay,
model/body write or external JSON write. The caller saves the returned report.
"""
from pathlib import Path
import json,copy,collections,hashlib,sys
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import door_source_templates as B,check_door_source_templates as G
MID='door_walnut_A700_source'
def digest(M):return hashlib.sha256(json.dumps(sorted((e['id'],e['g'])for e in M['els']),separators=(',',':')).encode()).hexdigest()
def _validate(M,source_audit):
 if G.sha(B.DATA_PATH)!=G.FROZEN_SHA:raise ValueError('Door review frozen data changed')
 D=json.loads(B.DATA_PATH.read_text());R=source_audit
 if not isinstance(R,dict)or R.get('source_data_sha256')!=G.FROZEN_SHA or R.get('global_findings')or R.get('summary',{}).get('pass')is not True or R['summary'].get('findings')!=0 or R['summary'].get('uncovered')!=0:raise ValueError('Door scoped audit is not passed/frozen')
 groups={(r['source_page'],tuple(r['source_drawing_indices']))for r in D['instances'].values()}
 specs=[('checks',set(D['instances']),lambda q:q['id']),('body_replacement_checks',set(D['instances']),lambda q:q['id']),('source_plan_checks',groups,lambda q:(q['source_page'],tuple(q['raw_drawing_indices']))),('source_template_checks',set(D['templates']),lambda q:q['id']),('source_literal_image_checks',{'A701:66','A701:48'},lambda q:q['id'])]
 for name,expected,key in specs:
  qs=R.get(name,[])
  if len(qs)!=len(expected)or{key(q)for q in qs}!=expected or any(q.get('pass')is not True or q.get('errors')for q in qs):raise ValueError('Door scoped audit exact checks failed: '+name)
 if R['summary'].get('whole_leaf_XY_source_checked')!=0 or R['summary'].get('physical_whole_assembly_checked')!=0 or R['summary'].get('native_anchor_raw_unique')!=81:raise ValueError('Door scope was promoted incorrectly')
 by=collections.defaultdict(list)
 for e in M['els']:by[e['id']].append(e)
 extra=[e['id']for e in M['els']if((e.get('a')or{}).get(G.OWN_META)or e.get('t','').startswith('door_source_'))and e['id']not in D['instances']]
 if extra:raise ValueError('Extra source door identity')
 for eid,r in D['instances'].items():
  if len(by[eid])!=1:raise ValueError('Door current identity missing/duplicate: '+eid)
  e=by[eid][0];a=e.get('a')or{};old=D['original_bodies'][eid]
  if e['g']!=G.expected_g(D,r)or(e['c'],e['l'],e.get('t'),e.get('mark'))!=('A.door',r['level'],'door_source_'+r['code'],r['code'])or a.get(G.OWN_META)!=eid or a.get('source_door_data_sha256')!=G.FROZEN_SHA or a.get('source_hinge_side_anchor_xy_cm')!=r['source_hinge_side_anchor_xy_cm']or a.get('source_signed_open_vector_xy')!=r['source_signed_open_vector_xy']or any(a.get(k)for k in G.FALSE_FLAGS)or any(e.get(k)!=old.get(k)for k in['u','u2']):raise ValueError('Door current scoped body/identity/metadata changed: '+eid)
 return D,{k:v[0]for k,v in by.items()}

def append_to(M,els=None,source_audit=None):
 if els is not None and els is not M['els']:raise ValueError('DD must use actual current model array')
 D,by=_validate(M,source_audit);ids=list(D['instances']);counts=dict(collections.Counter(r['code']for r in D['instances'].values()));issues=[]
 def add(suffix,title,status,note,before=None,after=None,eids=None):issues.append({'id':'DP-DOOR-TEMPLATE-'+suffix,'title':title,'status':status,'source':'ARCH1 ص6 A103 وص7 A104 / ARCH2 ص9 A700 وص10 A701 / A600 FFL','note':note,'level':None,'xy_cm':None,'z_m':None,'elements':ids if eids is None else eids,'before':before,'after':after})
 add('BODY','إعادة بناء الدرفات في وضع الفتح المرسوم','corrected','استبدلت204 أجسام مغلقة إجرائية بقوالب درفات مستقلة من A700/A701 عند نهاية الخشب جهة المفصلة وباتجاه الفتح الخام.81 مجموعة رسم فريدة؛40 بالأول و41 تتكرر في2–5. المعرفات القديمة وu/u2 محفوظة، دون nearest centre أو تغيير المضيف أو إضافة إطار/قفل/مفصلة.',{'guessed_closed_leaf_bodies':204,'depth_cm':4,'height_cm':215},{'copied_leaf_envelopes':204,'templates':6,'raw_unique_hinge_side_anchors':81,'codes':counts,'retained_IDs':204,'whole_leaf_XY_accepted':False})
 d7=[eid for eid,r in D['instances'].items()if r['code']=='D7'];add('D7-OPEN','تصحيح وصف اتجاه فتح D7','corrected','الجدول A700 يحدد Door open to outside؛ الوصف القديم inside كان خاطئاً. جسم الدرفة يتبع وضع المسقط الفعلي، ولا يعتمد اتجاه حركة جهاز مركب من النص وحده.','inside','outside',d7)
 add('EXTENT','فرق رمز الدرفة وقياس قالب الارتفاع محفوظ','source_gap','قلب D1 نحو91.817سم ليس طول الدرفة؛ نهايتا الخشب تكملانه إلى112.1268سم، وقالب A700 نحو112.4868سم. حُفظ الفرق≈0.36سم عند الطرف الحر مع ثبات نهاية جهة المفصلة. فروق كل81 مجموعة محفوظة؛ المقارنة بين غلافين رسومي/تفصيلي، وليست source_conflict تنفيذي مؤكد أو قبول wholeleafXY.',None,{'native_template_width_comparisons':copy.deepcopy(D['native_template_extent_comparison']),'hinge_end_preserved':True,'raw_warped':False})
 add('DETAILS','تفاصيل الأبواب المركبة تحتاج استكمال المصدر','source_gap','هذه أغلفة درفات مركبة فقط. الإطار والأرشيتراف والعتاد ومحور المفصلة الميكانيكي والتثبيت والتلامس بالمضيف واللون الفعلي غير معتمدة. يحفظ نص6mm MDF وتفصيل48mm كلٌ بنطاقه؛ تركيب الطبقات الداخلي غير مقبول.',None,{'frame_parts_added':0,'hardware_added':0,'physical_whole_assembly_accepted':False})
 old=[q for q in M.get('drawingIssues',[])if not q.get('id','').startswith('DP-DOOR-TEMPLATE-')];M['drawingIssues']=old+issues;return issues

def update_component_review(M,report,source_audit,beforeM=None,external_report=None):
 D,by=_validate(M,source_audit);R=copy.deepcopy(report);owned=set(D['instances']);current=set(by);basis=beforeM if beforeM is not None else M
 if report.get('model_geometry_sha256')!=digest(basis):raise ValueError('Door CC input report does not match before/current geometry')
 rows={r['id']:r for r in R['rows']}
 if len(rows)!=len(R['rows'])or set(rows)!=current:raise ValueError('Door CC exact unchanged ID set mismatch')
 if beforeM is not None:
  before={e['id']:e for e in beforeM['els']}
  if set(before)!=current or any(before[eid]!=by[eid]for eid in current-owned):raise ValueError('Door CC unrelated component changed')
 checks={q['id']:q for q in source_audit['checks']}
 for eid,r in D['instances'].items():
  e=by[eid];g=e['g'];xy=[sum(p[i]for p in g[1])/4 for i in[0,1]];refs=[f"ARCH1:{r['source_page']} A103/A104 native leaf/jamb",'ARCH2:9 A700','ARCH2:10 A701','ARCH2:1 A600']
  rows[eid]={'id':eid,'status':'derived','xy_basis':'غلاف درفة مركب من قالب A700/A701؛ نهاية جهة المفصلة واتجاه الفتح من المسقط الخام مفحوصان','z_basis':'drawn_ffl_only','source':' / '.join(refs),'findings':['قالب مركب؛ wholeleafXY والمفصلة الميكانيكية والإطار والعتاد والمضيف والمادة الكاملة/اللون غير معتمدة']}
  R['details'][eid]={'category':e['c'],'type':e['t'],'level':e['l'],'geometry_kind':'p','xy_cm':xy,'z_m':g[2:4],'source_refs':refs,'height_assumptions':['FFL الدور حرفي؛ ارتفاع الدرفة من محيط elevation A700 المعاير وليس220سم لكل جزء'],'evidence':{'door_composite_leaf_check':copy.deepcopy(checks[eid]),'native_hinge_side_anchor_cm':r['source_hinge_side_anchor_xy_cm'],'signed_open_vector_xy':r['source_signed_open_vector_xy'],'source_unique_group':[r['source_page'],r['source_drawing_indices']],'source_template':r['template'],'native_vs_template_width_cm':r['native_vs_template_width_cm']},'native_anchor_source_checked':True,'whole_leaf_XY_source_accepted':False,'needs_original_xy_proof':True,'needs_height_proof':True,'needs_dimension_semantic_review':True,'physical_whole_assembly_accepted':False}
 R['rows']=[rows[e['id']]for e in M['els']];fam=collections.defaultdict(collections.Counter)
 for row in R['rows']:fam[by[row['id']]['c'].split('.')[0]][row['status']]+=1
 R['counts']=dict(collections.Counter(r['status']for r in R['rows']));R['by_family']={k:dict(v)for k,v in fam.items()};R['height_counts']=dict(collections.Counter(r['z_basis']for r in R['rows']));R['model_elements']=len(M['els']);R['model_geometry_sha256']=digest(M);R['drawn_gate_snapshot_bound']=False;R['drawn_gate_unbound_reason']='Scoped door replacement; all unrelated exact bindings reused,81 native endpoints +6 templates checked; no repeated full audit';R.setdefault('raw_new_component_source_inventory',{})['door_source_templates']=copy.deepcopy(source_audit);R.setdefault('incremental_source_batches',{})['door_source_templates']={'source_data_sha256':G.FROZEN_SHA,'retained_IDs':204,'native_anchor_instances_checked':204,'raw_unique_anchor_groups':81,'derived_composite_leaf_rows':204,'whole_leaf_source_checked_promoted':0}
 # Reuse the established compact schema; only constructs dictionaries.
 sys.path.insert(0,str(G.ROOT/'tools'));import check_component_coverage as CC
 M['componentReview']=CC.compact(R,external_report or 'pipeline/data/component_coverage.json');return R


def update_material_review(M,source_audit):
 D,by=_validate(M,source_audit)
 if any(by[eid].get('m')!=MID for eid in D['instances']):raise ValueError('Door scoped material identity mismatch')
 review=M['materialReview'];materials=review['materials'];records={};rules=[];classbytype={}
 for code,t in D['templates'].items():
  typ='door_source_'+code;key='DOOR-SOURCE:A700:'+code;ids=[eid for eid,r in D['instances'].items()if r['code']==code];text=' / '.join(v['text']for v in t['schedule_text'].values());record={'id':key,'source':'ARCH2:9 A700','literal':text,'raw_texttrace_indices':[int(k)for k in t['schedule_text']],'source_text':copy.deepcopy(t['schedule_text']),'source_pdf_sha256':D['sources']['ARCH2']['pdf_sha256'],'scoped_veneer_material':'Walnut wood veneer','class_only':True,'full_material_or_layer_build_up_verified':False};record['record_sha256']=hashlib.sha256(json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest();records[key]=record;rules.append({'type':typ,'record_key':key,'expected_element_ids':ids,'accepted_scope':'literal veneer class and type-specific source text only','whole_material_acceptance':False});classbytype[typ]={'literal':text,'ids':ids,'record_key':key}
 materials[MID]={'id':MID,'status':'source_rule_partial','source_code':'DOOR-SOURCE:A700:TYPED','source_literal':'Type-specific A700 door descriptions; shared accepted scope: Walnut wood veneer only','source_material_literal':'Walnut wood veneer','source_finish_literal':'unknown','physical_color_literal':'unknown','physical_color_hex':None,'source_record_keys':list(records),'source_record_sha256':[q['record_sha256']for q in records.values()],'source_refs':['ARCH2:9 A700','ARCH2:10 A701'],'typed_scope':list(classbytype),'typed_literals':classbytype,'expected_element_ids':list(D['instances']),'assignment_limit':'Veneer class/type text only on204 copied leaf envelopes; no global firecore assignment acrossNR/FR, no installed grade, full layer build-up, hardware, finish/color or assembly approval','historical_display_color':None,'display_color_only':True}
 review.setdefault('scoped_literal_source_records',{})['door_source_templates']=records;review['typed_source_rules']=[q for q in review.get('typed_source_rules',[])if not q.get('type','').startswith('door_source_')]+rules;C=review['counts'];C['physical_material_ids']=len(materials);C['counts']=dict(collections.Counter(v['status']for v in materials.values()));base=C.setdefault('literal_source_records_base',C.get('literal_source_records',0));C['scoped_door_literal_records']=6;C['literal_source_records']=base+6;C['door_leaf_scoped_material_assignments']=204;C['door_leaf_complete_material_accepted']=0;M.setdefault('meta',{})['source_material_review']=copy.deepcopy(C)
 mat=M['mats'][MID];mat.update({'source_status':'source_rule_partial','source_material_literal':'Walnut wood veneer','source_finish_literal':'unknown','physical_color_literal':'unknown','physical_color_hex':None,'color_source_verified':False,'source_record_keys':list(records),'source_refs':['ARCH2:9 A700'],'source_typed_scope':list(classbytype),'source_assignment_limit':materials[MID]['assignment_limit'],'display_color_only':True})
 return materials[MID]
