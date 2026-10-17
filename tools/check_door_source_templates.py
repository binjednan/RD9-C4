"""Targeted raw door-template gate: audit(M), verify_source(D), expected_g(D,r).

204 retained IDs are copies of six A700/A701 leaf templates at 81 raw A103/A104
wood leaf hinge-side ends. Direct raw endpoints/pair-jamb identity are verified;
composite footprint, hardware, mechanical pivot, host contact and full installed
assembly are not promoted to whole-body source acceptance. No nearest-model fit.
0.001 PDFpt is endpoint serialization for polygonization, not model tolerance.
"""
from pathlib import Path
import json,hashlib,sys,math,collections,copy
HERE=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pipeline'))
import lib,fitz,reg
from shapely.geometry import LineString,Polygon
from shapely.ops import polygonize,unary_union
DATA_PATH=(HERE/'data/door_source_templates.json')if(HERE/'data/door_source_templates.json').exists()else ROOT/'pipeline/data/door_source_templates.json'
FROZEN_SHA='8b43c160d2863a1a400a045d702760667011198cbee23c2d8e08f7491385a2a2'
OWN_META='source_door_instance'
FALSE_FLAGS=['source_whole_assembly_verified','source_mount_verified','source_hardware_verified','source_color_verified','source_ports_verified','source_physical_hinge_pivot_verified','source_whole_leaf_XY_verified']
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def raw(d):
 def cv(q):
  if hasattr(q,'x'):return[q.x,q.y]
  if hasattr(q,'ul'):return[[q.ul.x,q.ul.y],[q.ur.x,q.ur.y],[q.lr.x,q.lr.y],[q.ll.x,q.ll.y]]
  if hasattr(q,'x0'):return[q.x0,q.y0,q.x1,q.y1]
  return q
 return{'layer':d.get('layer'),'items':[[it[0]]+[cv(q)for q in it[1:]]for it in d['items']],'close_path':d.get('closePath'),'fill':list(d['fill'])if d.get('fill')is not None else None,'polys':[[list(q)for q in pl]for pl in lib.flat_path(d,32)]}
def tx(t):return{'text':''.join(chr(c[0])for c in t['chars']),'layer':t.get('layer'),'bbox':list(t['bbox']),'chars':[[c[0],c[1],list(c[2]),list(c[3])]for c in t['chars']]}
def polys(drawings):
 lines=[]
 for d in drawings:
  for pl in lib.flat_path(d,32):
   for a,b in zip(pl,pl[1:]):
    a=tuple(round(v,3)for v in a);b=tuple(round(v,3)for v in b)
    if a!=b:lines.append(LineString([a,b]))
 return list(polygonize(unary_union(lines)))
def samegeom(a,b):return a.equals(b) or a.symmetric_difference(b).area<1e-10

def native_pose(dr,ids,global_ps,width_cm,T):
 ps=polys([dr[i]for i in ids]);core=max(ps,key=lambda q:q.area);b=core.bounds;ax=0 if b[2]-b[0]>b[3]-b[1]else 1;na=1-ax;bc=[(b[0]+b[2])/2,(b[1]+b[3])/2]
 body=[q for q in ps if q.bounds[na]>=b[na]-.121 and q.bounds[na+2]<=b[na+2]+.121 and q.bounds[ax]>=b[ax]-2.89 and q.bounds[ax+2]<=b[ax+2]+2.89 and q.buffer(.001).intersects(core)]
 wood=unary_union(body);wb=wood.bounds;jamb=[]
 for q in global_ps:
  qb=q.bounds
  if q.area<3 or not(.9<=qb[na+2]-qb[na]<=1.8)or not(2<=qb[ax+2]-qb[ax]<=6.2):continue
  for side in[-1,1]:
   e=wb[ax]if side<0 else wb[ax+2];gap=side*((qb[ax+2]if side<0 else qb[ax])-e)
   if -.002<=gap<=.55 and qb[na]<bc[na]+1.7 and qb[na+2]>bc[na]-1.7:jamb.append((q,side))
 if len(jamb)!=1:raise ValueError('Unique hinge-side jamb required')
 j,side=jamb[0];jb=j.bounds;other=[]
 for q in global_ps:
  qb=q.bounds
  if samegeom(q,j)or q.area<3 or not(.9<=qb[na+2]-qb[na]<=1.8):continue
  if abs(qb[ax]-jb[ax])>.13 or abs(qb[ax+2]-jb[ax+2])>.13:continue
  span=(max(qb[na+2],jb[na+2])-min(qb[na],jb[na]))*T['s']
  if abs(span-width_cm)<2:other.append(q)
 if len(other)!=1:raise ValueError('Unique opposite jamb required')
 o=other[0];ob=o.bounds;pb=[min(jb[k],ob[k])for k in[0,1]]+[max(jb[k],ob[k])for k in[2,3]];box=[pb[0]*T['s']+T['ox'],-pb[3]*T['s']+T['oy'],pb[2]*T['s']+T['ox'],-pb[1]*T['s']+T['oy']]
 anchor=[(wb[0]+wb[2])/2,(wb[1]+wb[3])/2];anchor[ax]=wb[ax]if side<0 else wb[ax+2];u=[0.,0.];u[ax]=-side;uw=[u[0],-u[1]];xy=[anchor[0]*T['s']+T['ox'],-anchor[1]*T['s']+T['oy']]
 return{'wood':wood,'core':core,'wood_bounds':wb,'hinge_jamb':j,'opposite_jamb':o,'anchor_pdf':anchor,'anchor_xy':xy,'u_xy':uw,'angle_deg':round(math.degrees(math.atan2(uw[1],uw[0])),8),'closed_opening_bbox_cm':box,'native_width_cm':(wb[ax+2]-wb[ax])*T['s']}

def source_citations(r):
 return[f"ARCH1 ص{r['source_page']}: {r['code']} نهاية الدرفة الخشبية جهة المفصلة واتجاه الفتح؛ ARCH2 ص9 A700 وص10 A701"]

def expected_g(D,r):
 t=D['templates'][r['template']];w=t['leaf_width_cm'];d=t['leaf_depth_cm'];cx,cy=r['source_hinge_side_anchor_xy_cm'];u=r['source_signed_open_vector_xy'];n=[-u[1],u[0]];xy=[[round(cx+v*w*u[0]+q*d/2*n[0],4),round(cy+v*w*u[1]+q*d/2*n[1],4)]for v,q in[(0,-1),(1,-1),(1,1),(0,1)]];z=D['level_datums'][r['level']]['ffl_m'];return['p',xy,round(z,6),round(z+t['leaf_height_cm']/100,6),None]

def verify_source(D):
 errors=[];pages={};grid_cache={};allps={};plan=[];templates=[];literal=[]
 if D.get('schema')!='c4.door-source-templates.v2' or len(D.get('instances',{}))!=204 or len(D.get('original_bodies',{}))!=204 or set(D['instances'])!=set(D['original_bodies']):errors.append({'kind':'data_schema_or_exact_identity'})
 for k,r in D['sources'].items():
  if sha(r['path'])!=r['pdf_sha256']:errors.append({'kind':'source_pdf_fingerprint','source':k})
 def page(k,pn):
  if(k,pn)not in pages:
   p=lib.doc(k)[pn-1];pages[k,pn]=(p,p.get_drawings(),p.get_texttrace())
  return pages[k,pn]
 C=D['schedule_calibration'];p,ds,tt=page('ARCH2',9)
 for di,d in C['source_drawings'].items():
  if raw(ds[int(di)])!=d:errors.append({'kind':'schedule_dimension_raw','drawing':di})
 for ti,t in C['source_texts'].items():
  if tx(tt[int(ti)])!=t:errors.append({'kind':'schedule_dimension_text','trace':ti})
 sx=120/(ds[104]['items'][0][1].x-ds[103]['items'][0][1].x);sy=220/(ds[76]['items'][0][1].y-ds[77]['items'][0][1].y)
 if abs(sx-C['s_x_cm_per_pdf_pt'])>1e-12 or abs(sy-C['s_y_cm_per_pdf_pt'])>1e-12:errors.append({'kind':'schedule_calibration'})
 for code,t in D['templates'].items():
  er=[];di=t['elevation_outline_drawing'];d=ds[di]
  if raw(d)!=t['elevation_source']:er.append('elevation_raw')
  b=d['rect'];expect=[(b.x1-b.x0)*sx,(b.y1-b.y0)*sy,int(t['depth_literal_source_image'])/10]
  if any(abs(a-b)>1e-9 for a,b in zip(expect,[t['leaf_width_cm'],t['leaf_height_cm'],t['leaf_depth_cm']])):er.append('template_dimensions')
  for ti,txt in t['schedule_text'].items():
   if tx(tt[int(ti)])!=txt:er.append('source_schedule_text')
  templates.append({'id':code,'pass':not er,'errors':er,'proof_scope':'measured_leaf_elevation_outline_and_detail_depth_literal; not wholeassembly'})
 p,_,_=page('ARCH2',10)
 for val,r in D['detail_images'].items():
  er=[];pix=p.get_pixmap(matrix=fitz.Matrix(*r['matrix']),clip=fitz.Rect(r['crop_pdf']),annots=r['annots'])
  if hashlib.sha256(pix.samples).hexdigest()!=r['render_samples_sha256']or[pix.width,pix.height,pix.n]!=r['render_size']:er.append('original_detail_crop_fingerprint')
  literal.append({'id':'A701:'+val,'pass':not er,'errors':er,'proof_scope':'native_main_PDF_render_literal_review; no OCR/vector digit claim'})
 anns={str(a.xref):a for a in p.annots()}
 for x,r in D['detail_annotations'].items():
  if x not in anns or list(anns[x].rect)!=r['rect_pdf']or anns[x].info.get('content')!=r['contents']or hashlib.sha256(lib.doc('ARCH2').xref_object(int(x)).encode()).hexdigest()!=r['object_sha256']:errors.append({'kind':'detail_original_annotation','xref':x})
 for lv,r in D['level_datums'].items():
  _,_,ts=page('ARCH2',1)
  if tx(ts[r['texttrace_index']])!=r['source_text']or('+'+str(r['ffl_m']))not in r['source_text']['text']:errors.append({'kind':'floor_literal','level':lv})
 seen={};accepted_identity=set()
 for eid,r in D['instances'].items():
  key=(r['source_page'],tuple(r['source_drawing_indices']));er=[]
  if key not in seen:
   _,dr,ts=page('ARCH1',r['source_page'])
   if r['source_page']not in grid_cache:
    grid=[d for d in dr if d.get('layer')and('GRID'in d['layer'].upper()or'AXIS'in d['layer'].upper())and'IDEN'not in d['layer'].upper()];vv,hh=reg.grid_clusters(None,layers=None,drawings=grid,minlen=50);grid_cache[r['source_page']]=reg.register_free(vv,hh);allps[r['source_page']]=polys([d for d in dr if d.get('layer')=='A-Door'])
   freshT=grid_cache[r['source_page']]
   if any(abs(freshT[k]-r['source_transform'][k])>1e-9 for k in['s','ox','oy']):er.append('source_transform_fresh_grid_policy')
   for di in r['source_drawing_indices']:
    if raw(dr[di])!=r['source_drawings'][str(di)]:er.append('raw_plan_'+str(di))
   for label,jb in r['source_jamb_bindings'].items():
    for di in jb['drawing_indices']:
     if raw(dr[di])!=jb['source_drawings'][str(di)]:er.append('raw_jamb_'+str(di))
   try:
    p0=native_pose(dr,r['source_drawing_indices'],allps[r['source_page']],D['templates'][r['code']]['opening_cm'][0],r['source_transform'])
    if not samegeom(p0['wood'],unary_union([Polygon(p)for p in r['source_full_wood_profiles_pdf']]))or list(p0['wood_bounds'])!=list(r['source_full_wood_bbox_pdf']):er.append('native_fullwood_core_stiles_profile')
    if not samegeom(p0['hinge_jamb'],Polygon(r['source_hinge_jamb_profile_pdf']))or not samegeom(p0['opposite_jamb'],Polygon(r['source_opposite_jamb_profile_pdf'])):er.append('native_paired_jamb_binding')
    for field,want in [('anchor_pdf','source_hinge_side_anchor_pdf'),('anchor_xy','source_hinge_side_anchor_xy_cm'),('u_xy','source_signed_open_vector_xy'),('closed_opening_bbox_cm','source_closed_opening_bbox_cm')]:
     if any(abs(a-b)>1e-9 for a,b in zip(p0[field],r[want])):er.append('native_'+field)
    if abs(p0['native_width_cm']-r['source_native_leaf_width_cm'])>1e-9 or abs(r['native_vs_template_width_cm']-(p0['native_width_cm']-D['templates'][r['code']]['leaf_width_cm']))>1e-9:er.append('native_vs_template_extent_record')
   except Exception as ex:er.append('native_pose_replay:'+str(ex))
   st=r['tag_source'];chars=[ts[st['texttrace_index']]['chars'][i]for i in st['char_indices']];actual=[[c[0],c[1],list(c[2]),list(c[3])]for c in chars]
   if actual!=st['chars']or''.join(chr(c[0])for c in chars)!=r['code']:er.append('door_tag_literal')
   seen[key]={'source_page':r['source_page'],'raw_drawing_indices':r['source_drawing_indices'],'pass':not er,'errors':er,'source_xy':r['source_hinge_side_anchor_xy_cm'],'native_width_cm':r['source_native_leaf_width_cm'],'template_width_cm':D['templates'][r['code']]['leaf_width_cm'],'difference_cm':r['native_vs_template_width_cm'],'proof_scope':'raw_fullwood_graphic_hinge_side_endpoint_and_signed_open_axis_only; composite_leaf_XY_not_wholeverified'};plan.append(seen[key])
  orig=D['original_bodies'][eid];box=r['source_closed_opening_bbox_cm'];hits=[]
  for oi,oe in D['original_bodies'].items():
   if oe['l']!=r['level']or oe.get('mark')!=r['code']or oe['g'][0]!='r':continue
   eb=oe['g'][1:5]
   if all(eb[k]>=box[k]-2 for k in[0,1])and all(eb[k]<=box[k]+2 for k in[2,3]):hits.append(oi)
  if hits!=[eid] or r['old_identity_binding']['candidate_ids']!=[eid]or orig['g']!=r['old_identity_binding']['original_g']:errors.append({'id':eid,'kind':'unique_native_opening_old_identity_binding'})
  if eid in accepted_identity:errors.append({'id':eid,'kind':'duplicate_original_identity'})
  accepted_identity.add(eid)
 if len(plan)!=81 or len(templates)!=6 or len(literal)!=2:errors.append({'kind':'exact_raw_source_denominators','raw_plan':len(plan),'templates':len(templates),'detail_images':len(literal)})
 return{'pass':not errors and all(q['pass']for q in plan+templates+literal),'global_findings':errors,'source_plan_checks':plan,'source_template_checks':templates,'source_literal_image_checks':literal,'identity_bindings_checked':len(accepted_identity)}

def audit(M):
 # Rehydrate external audit inputs; geometry remains the live model.
 import sys as _audit_sys
 from pathlib import Path as _AuditPath
 _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
 from source_audit_sidecar import audit_model as _source_audit_model
 M = _source_audit_model(M)
 D=json.loads(DATA_PATH.read_text());proof=verify_source(D);errors=list(proof['global_findings']);checks=[];replacements=[];by=collections.defaultdict(list)
 for e in M['els']:by[e['id']].append(e)
 if sha(DATA_PATH)!=FROZEN_SHA:errors.append({'kind':'frozen_data_fingerprint'})
 owned=[e for e in M['els']if(e.get('a')or{}).get(OWN_META)or e.get('t','').startswith('door_source_')];expected=set(D['instances'])
 if {e['id']for e in owned}!=expected or len(owned)!=204:errors.append({'kind':'exact_owned_inventory','missing':sorted(expected-{e['id']for e in owned}),'extra':sorted({e['id']for e in owned}-expected),'actual':len(owned)})
 for eid,r in D['instances'].items():
  er=[];values=by[eid];e=values[0]if len(values)==1 else None
  if e is None:er.append('missing_or_duplicate_instance')
  else:
   if(e['c'],e['l'],e['t'],e.get('mark'))!=('A.door',r['level'],'door_source_'+r['code'],r['code']):er.append('instance_identity')
   if e['g']!=expected_g(D,r):er.append('hinge_anchored_composite_geometry')
   for key in['u','u2']:
    if e.get(key)!=D['original_bodies'][eid].get(key):er.append('preserved_unit_'+key)
   a=e.get('a')or{}
   if a.get('source_door_template')!=r['template']or a.get('source_door_data_sha256')!=FROZEN_SHA or a.get(OWN_META)!=eid or a.get('source_hinge_side_anchor_xy_cm')!=r['source_hinge_side_anchor_xy_cm']or a.get('source_signed_open_vector_xy')!=r['source_signed_open_vector_xy']:er.append('source_metadata')
   if any(a.get(k)for k in FALSE_FLAGS):er.append('unsupported_physical_promotion')
   refs=e.get('s',[]);sp=M.get('sp',[])
   if any(type(i)is not int or not(0<=i<len(sp))for i in refs)or not refs:er.append('source_citation_index_schema')
   elif [sp[i]for i in refs]!=source_citations(r):er.append('source_citation_text')
  checks.append({'id':eid,'pass':not er,'errors':er,'proof_scope':'derived_composite_leaf_template_with_verified_native_hinge_side_anchor_and_signed_axis; not wholeleaf_XY'})
  re=[]
  if e is None:re.append('replacement_body_missing')
  elif e['g']==D['original_bodies'][eid]['g']:re.append('original_guessed_closed_leaf_body_not_replaced')
  replacements.append({'id':eid,'pass':not re,'errors':re,'identity_retained':True,'proof_scope':'old_body_geometry_removed; ID/u/u2 preserved'})
 bad=errors+[q for q in checks+replacements+proof['source_plan_checks']+proof['source_template_checks']+proof['source_literal_image_checks']if not q['pass']]
 return{'schema':'c4.door-source-templates-audit.v2','source_data_sha256':FROZEN_SHA,**proof,'checks':checks,'body_replacement_checks':replacements,'global_findings':errors,'summary':{'checked':len(checks),'body_replaced':len(replacements),'IDs_retained':204,'raw_plan_groups':81,'templates':6,'findings':len(bad),'uncovered':sum('missing_or_duplicate_instance'in q['errors']for q in checks),'native_anchor_instances_checked':204,'native_anchor_raw_unique':81,'whole_leaf_XY_source_checked':0,'physical_whole_assembly_checked':0,'derived_composite_leaves':204,'pass':not bad}}
