"""Original-PDF gate for four D16 plan proxies; physical part dimensions stay unverified.
API audit(M), verify_source(D). Neither function writes the model or source.
"""
import collections,hashlib,json,math,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA_PATH=ROOT/'pipeline/data/d16_source_remaining.json'
FROZEN_SHA='41055c3747ad6588cd11fa7e3628162d8413ba75c20fae9289d07350f0093131'
SCHEMA='c4.d16-source-remaining.v1';TOL=.2
PARTS={'A.door-G-D160001':(47677,'right_open_leaf'),'A.door-G-D160002':(47681,'left_open_leaf'),'A.door-G-D160003':(47675,'right_outer_jamb'),'A.door-G-D160004':(47679,'left_outer_jamb')}
EXPECTED_IDS=set(PARTS)
FALSE_FLAGS=['source_dimensions_verified','source_physical_body_verified','source_Z_verified','source_absolute_Z_verified','source_material_verified','source_mount_verified','source_ports_verified','source_contact_verified','source_colour_verified','source_fire_rating_accepted','source_part_height_verified']
def _ser(v):
 import fitz
 if isinstance(v,fitz.Point):return[v.x,v.y]
 if isinstance(v,fitz.Quad):return[_ser(q)for q in v]
 if isinstance(v,fitz.Rect):return list(v)
 if isinstance(v,(list,tuple)):return[_ser(q)for q in v]
 return v
def _sha(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
def verify_source(D):
 """Reconstruct selected polygons and literals from originalPDF, independent of model metadata."""
 import fitz
 from shapely.geometry import Polygon
 sys.path.insert(0,str(ROOT/'pipeline'));import lib,reg
 errors=[];parts={};facts=[]
 if D.get('schema')!=SCHEMA or set(D.get('records',{}))!=EXPECTED_IDS:errors.append('exact_schema_part_inventory')
 if set(D.get('source_pages',{}))!={'ARCH1:5','ARCH2:5','BOQ:8'}:errors.append('exact_source_page_inventory')
 for page,row in D.get('source_pages',{}).items():
  key,pn=page.split(':');p=Path(row['source_pdf'])
  if hashlib.sha256(p.read_bytes()).hexdigest()!=row['source_pdf_sha256']:errors.append(page+':original_PDF_SHA')
  with fitz.open(p)as doc:
   pg=doc[int(pn)-1];ds=pg.get_drawings();tt=pg.get_texttrace()
   sourceops=row.get('source_drawings',[])+row.get('source_context_drawings',[])
   for q in sourceops:
    try:d=ds[q['drawing_index']]
    except Exception:errors.append(page+':original_drawing_index');continue
    if d.get('layer')!=q['layer']or _ser(d['items'])!=q['raw_items']:errors.append(page+':original_operators_or_layer')
   for q in row['raw_traces']:
    try:t=tt[q['texttrace_index']]
    except Exception:errors.append(page+':original_text_index');continue
    if t.get('layer')!=q['layer']or ''.join(chr(c[0])for c in t['chars'])!=q['literal']or _ser(t['chars'])!=q['raw_chars']or _ser(t['bbox'])!=q['bbox_pdf']:errors.append(page+':original_text_chars')
   def text(i):return ''.join(chr(c[0])for c in tt[i]['chars'])
   if page=='ARCH1:5':
    grid=[d for d in ds if d.get('layer')and('GRID'in d['layer'].upper()or'AXIS'in d['layer'].upper())and'IDEN'not in d['layer'].upper()];v,h=reg.grid_clusters(None,layers=None,drawings=grid,minlen=50);T=reg.register_free(v,h)
    if T!=row['source_transform']or v!=row['raw_grid_v']or h!=row['raw_grid_h']:errors.append('fresh_original_A102_grid')
    if text(692)!='D16'or text(340)!='F.F.L. +0.20'or text(471)!='A604':errors.append('A102_identity_landing_detail_binding')
    if {q['drawing_index']for q in row['source_drawings']}!=set(range(47675,47683)):errors.append('whole_D16_original_glyph_inventory')
    if {q['drawing_index']for q in row['source_context_drawings']}!={54813,37188}:errors.append('D16_tag_and_actual_stair_jamb_context')
    for eid,(di,role)in PARTS.items():
     d=ds[di];pl=lib.flat_path(d)
     if d.get('layer')!='X-AD738-Roof Floor Plan$0$A-DOOR'or len(pl)!=1 or pl[0][0]!=pl[0][-1]:errors.append(eid+':closed_actual_body_graphic');continue
     if len(d['items'])!=(1 if'leaf'in role else 8)or('leaf'in role and d['items'][0][0]!='qu')or('jamb'in role and any(it[0]!='l'for it in d['items'])):errors.append(eid+':glyph_anatomy')
     pdf=[list(q)for q in pl[0][:-1]];xy=[[x*T['s']+T['ox'],T['oy']-y*T['s']]for x,y in pdf];po=Polygon(xy)
     if not po.is_valid or po.area<=0:errors.append(eid+':invalid_source_polygon')
     parts[eid]={'di':di,'role':role,'pdf':pdf,'xy':xy,'raw_items':_ser(d['items']),'layer':d.get('layer'),'polygon':po,'T':T,'g':['p',[[round(x,6),round(y,6)]for x,y in xy],.20,1.30]}
   elif page=='ARCH2:5':
    if text(161)!='125STR. OPENING'or text(162)!='110 (HEIGHT)'or text(169)!='90 min'or text(171)!='D16'or text(89)!='F.F.L. +0.20':errors.append('A604_literal_opening_rating_landing_binding')
    for lit in ['Galvanized steel frame','Galvanized steel leaf','Door opens to outside']:
     if lit not in text(170):errors.append('A604_literal_material_or_direction')
    if {q['drawing_index']for q in row['source_drawings']}!=set(range(7202,7210))|set(range(7330,7348)):errors.append('A604_local_plan_elevation_scope')
   elif page=='BOQ:8':
    if'Type-D16'not in text(347)or'125X 1100  mm'not in text(347)or'rating : N/A'not in text(347):errors.append('BOQ_literal_D16_conflicts')
   facts.append({'source_page':page,'raw_operator_checks':len(sourceops),'raw_texttrace_checks':len(row['raw_traces']),'whole_physical_body_or_Z_accepted':False})
 literal=D.get('literal_scope',{})
 if literal.get('structural_opening_width_cm')!=125 or literal.get('opening_height_cm')!=110 or literal.get('conditional_display_envelope_m')!=[.2,1.3]or literal.get('ground_landing_absolute_FFL_m')!=.2:errors.append('literal_opening_conditional_envelope')
 if literal.get('numeric_physical_part_dimensions_accepted')is not False or literal.get('individual_leaf_or_jamb_height_accepted')is not False or literal.get('fire_rating_resolved_or_approved')is not False:errors.append('unsafe_literal_to_part_or_rating_promotion')
 if literal.get('literal_material_class')!='Galvanized steel'or literal.get('installed_material_grade_gauge_product_accepted')is not False or literal.get('physical_colour')!='unknown':errors.append('unsafe_material_or_colour_scope')
 for eid,r in parts.items():
  q=D['records'].get(eid,{})
  if(q.get('id'),q.get('c'),q.get('t'),q.get('l'),q.get('m'),q.get('grp'),q.get('role'))!=(eid,'A.door','d16_drawn_leaf_proxy'if'leaf'in r['role']else'd16_drawn_outer_jamb_proxy','G','d16_galv_source','D16-G-source',r['role']):errors.append(eid+':record_identity')
  if q.get('source_pdf_polygon')!=r['pdf']or q.get('source_xy_polygon_cm')!=r['xy']or q.get('source_raw_items')!=r['raw_items']or q.get('source_drawing_indices')!=[r['di']]or q.get('source_layer')!=r['layer']or q.get('g')!=r['g']:errors.append(eid+':record_raw_binding')
 if D.get('excluded_graphics',{}).get('meeting_edge_drawings')!=[47676,47680]or D.get('excluded_graphics',{}).get('swing_arc_drawings')!=[47678,47682]:errors.append('exclude_stationary_meeting_posts_and_arc_solids')
 expected_conf=[{'field':'structural_opening_width','ARCH2:5_A604':'125 cm','BOQ:8_8.3.12':'125 mm as printed','normalization_to_mm':{'ARCH2':1250,'BOQ':125},'suspected_BOQ_typo_not_silently_corrected':True},{'field':'fire_rating','ARCH2:5_A604':'90 min','BOQ:8_8.3.12':'N/A'}]
 if D.get('confirmed_literal_source_conflicts')!=expected_conf:errors.append('explicit_unresolved_literal_conflicts')
 return{'errors':sorted(set(errors)),'parts':parts,'facts':facts}
def audit(M):
 # Rehydrate external audit inputs; geometry remains the live model.
 import sys as _audit_sys
 from pathlib import Path as _AuditPath
 _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
 from source_audit_sidecar import audit_model as _source_audit_model
 M = _source_audit_model(M)
 from shapely.geometry import Polygon
 b=DATA_PATH.read_bytes();D=json.loads(b);gf=[];checks=[]
 if hashlib.sha256(b).hexdigest()!=FROZEN_SHA:gf.append({'kind':'frozen_data_fingerprint'})
 try:r=verify_source(D);gf.extend({'kind':e}for e in r['errors'])
 except Exception as ex:r={'parts':{},'facts':[]};gf.append({'kind':'original_raw_source','reason':str(ex)})
 cnt=collections.Counter(e['id']for e in M['els']);by={e['id']:e for e in M['els']}
 for e in M['els']:
  if ((e.get('a')or{}).get('d16_source_remaining')or e.get('grp')=='D16-G-source'or re.search(r'-D16\d{4}$',e['id']))and e['id']not in EXPECTED_IDS:gf.append({'kind':'unexpected_D16_identity','id':e['id']})
 for eid in sorted(EXPECTED_IDS):
  e=by.get(eid);raw=r['parts'].get(eid);q=D['records'].get(eid,{});errors=[];dev=None
  if e is None:errors.append('source_part_missing')
  if raw is None:errors.append('original_source_part_missing')
  if e is not None and raw is not None:
   if cnt[eid]!=1 or(e['c'],e['t'],e['l'],e.get('m'),e.get('grp'))!=(q['c'],q['t'],q['l'],q['m'],q['grp']):errors.append('exact_source_identity')
   try:dev=Polygon(e['g'][1]).hausdorff_distance(raw['polygon'])
   except Exception:errors.append('model_polygon_invalid')
   if dev is not None and(not math.isfinite(dev)or dev>TOL):errors.append('source_plan_polygon_deviation')
   if e['g']!=raw['g']:errors.append('exact_graphic_polygon_conditional_envelope')
   a=e.get('a')or{}
   if a.get('d16_source_remaining')is not True or a.get('d16_source_data_sha256')!=FROZEN_SHA or a.get('source_kind')!='d16_drawn_plan_polygon_proxy'or a.get('source_role')!=raw['role']:errors.append('scope_metadata')
   if a.get('source_pdf_points')!=raw['pdf']or a.get('source_xy')!=raw['xy']or a.get('source_transform')!=raw['T']or a.get('source_drawing_indices')!=[raw['di']]or a.get('source_page')!='ARCH1:5'or a.get('source_layer')!=raw['layer']or a.get('source_pdf_sha256')!=D['source_pages']['ARCH1:5']['source_pdf_sha256']or a.get('source_raw_items')!=raw['raw_items']:errors.append('original_source_metadata')
   if a.get('source_locked_xy')is not True or a.get('source_plan_polygon_verified')is not True or a.get('source_material_class_literal_verified')is not True or a.get('source_Z_conditional_envelope')is not True or a.get('source_opening_dimensions_literal_verified')is not True or a.get('source_fire_rating_literal_verified')is not True:errors.append('required_limited_evidence_flags')
   if a.get('source_opening_width_cm')!=125 or a.get('source_opening_height_cm')!=110 or a.get('source_material_class_literal')!='Galvanized steel':errors.append('literal_to_metadata_binding')
   if any(a.get(k)is not False for k in FALSE_FLAGS):errors.append('unsafe_physical_dimension_Z_material_mount_port_rating_promotion')
   if a.get('no_connectors')is not True or a.get('source_conflicts')!=D['confirmed_literal_source_conflicts']:errors.append('connections_or_conflicts_scope')
  checks.append({'id':eid,'pass':not errors,'errors':errors,'deviation_cm':dev,'source_page':'ARCH1:5','source_drawing_indices':[PARTS[eid][0]],'scope':'original_open_plan_polygon_graphic_only','numeric_physical_part_dimensions_checked':False,'absolute_Z_installed_material_acceptance':False,'method':'Fresh originalD16 leaf or outerJAMB polygon and originalA102 grid; conditional opening envelope only'})
 failures=len(gf)+sum(not q['pass']for q in checks)
 return{'checks':checks,'source_facts':r['facts'],'global_findings':gf,'summary':{'checked':len(checks),'source_assemblies':1,'source_plan_graphic_polygons':4,'source_page_facts':len(r['facts']),'findings':failures,'uncovered':sum(eid not in by for eid in EXPECTED_IDS),'max_deviation_cm':max((q['deviation_cm']or 0 for q in checks),default=0),'numeric_physical_part_dimensions_checked':0,'absolute_Z_installed_material_acceptance':False,'conditional_Z_envelope_guard_only':True}}
