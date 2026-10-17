"""Partial original-PDF gate: sixSTR24 shaft profiles and seven local domain cuts."""
import collections
import hashlib
import json
import math
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA_PATH=ROOT/'pipeline/data/top_roof_shaft_openings_source.json'
FROZEN_SHA='5d0c5f960609f47d9765f3b49129534de8b7511c6dff2fc9361c793d5fa2db7f'
SCHEMA='c4.top-roof-shaft-openings-source.v2'
EXPECTED_IDS={'S.slab-T-0009','S.slab-T-0010'}
DIAGS={2148:[2146,2147],2149:[2144,2145],2150:[2152,2153],2151:[2154,2155],2156:[2161,2162],2157:[2159,2160]}
TOL=.2

def _items(v):
 import fitz
 if isinstance(v,fitz.Point):return[v.x,v.y]
 if isinstance(v,fitz.Quad):return[_items(q)for q in v]
 if isinstance(v,fitz.Rect):return list(v)
 if isinstance(v,(tuple,list)):return[_items(q)for q in v]
 return v

def _poly(g):
 from shapely.geometry import Polygon,box
 return Polygon(g[1],g[4]if len(g)>4 else [])if g[0]=='p'else box(*g[1:5])

def _sha(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def _raw(pdfpath):
 import fitz
 from shapely.geometry import Polygon
 sys.path.insert(0,str(ROOT/'pipeline'));import lib,reg
 with fitz.open(pdfpath)as doc:
  p=doc[23];ds=p.get_drawings();tt=p.get_texttrace();grid=[(i,d)for i,d in enumerate(ds)if d.get('layer')and('GRID'in d['layer'].upper()or'AXIS'in d['layer'].upper())and'IDEN'not in d['layer'].upper()];v,h=reg.grid_clusters(None,layers=None,drawings=[d for i,d in grid],minlen=50);T=reg.register_free(v,h)
  if T is None or T['nx']!=11 or T['ny']!=6 or T['ex']/T['nx']>2.2 or T['ey']/T['ny']>2.2:raise ValueError('OriginalSTR24 whole-plan grid not resolved')
  observed={i for i,d in enumerate(ds)if d.get('layer')=='SHAFT'and len(d['items'])==1 and d['items'][0][0]=='qu'}
  if observed!=set(DIAGS):raise ValueError('Original exact closedSHAFT inventory changed')
  sources={}
  for di,diags in DIAGS.items():
   indices=[di]+diags;parts=[ds[i]for i in indices];d=parts[0];pl=lib.flat_path(d)
   if len(pl)!=1 or pl[0][0]!=pl[0][-1]or any(x.get('layer')!='SHAFT'for x in parts):raise ValueError('Original shaft scope/layer/closure changed')
   rect=d['rect']
   for cross in parts[1:]:
    if len(cross['items'])!=1 or cross['items'][0][0]!='l':raise ValueError('Original shaft X anatomy changed')
    a,b=cross['items'][0][1:]
    if abs(a.x-b.x)<=.1 or abs(a.y-b.y)<=.1:raise ValueError('Original shaft X diagonal missing')
    # PDF float endpoint spelling only; never expands a modeled opening orTOL.
    for q in (a,b):
     if not(rect.x0-.001<=q.x<=rect.x1+.001 and rect.y0-.001<=q.y<=rect.y1+.001):raise ValueError('Original shaft X no longer within quad')
   xy=[[x*T['s']+T['ox'],T['oy']-y*T['s']]for x,y in pl[0]];po=Polygon(xy)
   if not po.is_valid or po.area<=0:raise ValueError('Original shaft profile invalid')
   sources['STR24-SHAFT-'+str(di)]={'id':'STR24-SHAFT-'+str(di),'indices':indices,'raw_items':[_items(x['items'])for x in parts],'raw_points':[_items(lib.flat_path(x))for x in parts],'raw_types':[x['type']for x in parts],'xy':xy,'polygon':po}
  notes=[]
  for ti,needle in [(2,'ALL OPENINGS DIMENSIONS ARE TO BE COORDINATED'),(3,'UNLESS OTHERWISE SPECIFIED THICKNESS IS 25CMS.'),(92,'TOP ROOF SLAB LAYOUT')]:
   t=tt[ti];text=''.join(chr(c[0])for c in t['chars'])
   if needle not in text:raise ValueError('Original opening/conditional thickness/plan scope note changed')
   notes.append({'texttrace_index':ti,'role':{2:'opening_semantics_and_ARCH_coordination',3:'conditional_default_25cm_thickness_not_Z_or_outer',92:'actual_top_roof_plan_scope'}[ti],'layer':t.get('layer'),'literal_text':text,'raw_chars':_items(t['chars'])})
  return sources,T,v,h,[{'drawing_index':i,'layer':d.get('layer'),'raw_items':_items(d['items'])}for i,d in grid],notes

def audit(M):
 # Rehydrate external audit inputs; geometry remains the live model.
 import sys as _audit_sys
 from pathlib import Path as _AuditPath
 _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
 from source_audit_sidecar import audit_model as _source_audit_model
 M = _source_audit_model(M)
 from shapely.geometry import Polygon
 from shapely.ops import unary_union
 data_bytes=DATA_PATH.read_bytes();D=json.loads(data_bytes);gf=[];rawchecks=[];checks=[];preservation=[]
 if hashlib.sha256(data_bytes).hexdigest()!=FROZEN_SHA:gf.append({'kind':'frozen_data_fingerprint','reason':'Frozen local void ledger changed'})
 if D.get('schema')!=SCHEMA:gf.append({'kind':'schema','reason':'Frozen scope schema changed'})
 if set(D.get('records',{}))!=EXPECTED_IDS:gf.append({'kind':'exact_controlled_S_set','expected':sorted(EXPECTED_IDS),'actual':sorted(D.get('records',{}))})
 pdfsha=hashlib.sha256(Path(D['source_pdf']).read_bytes()).hexdigest()
 if pdfsha!=D['source_pdf_sha256']:gf.append({'kind':'original_pdf_fingerprint'})
 try:raw,T,v,h,grid,notes=_raw(D['source_pdf'])
 except Exception as ex:return {'checks':[],'source_opening_checks':[],'slab_preservation_checks':[],'global_findings':gf+[{'kind':'original_raw_reconstruction','reason':str(ex)}],'summary':{'checked':0,'findings':len(gf)+1,'uncovered':7,'body_source_checked':0,'source_scope':'local_opening_XY_subtraction_only'}}
 if D.get('source_transform')!=T or D.get('raw_grid_v')!=v or D.get('raw_grid_h')!=h or D.get('raw_grid_primitives')!=grid:gf.append({'kind':'original_grid_binding'})
 if D.get('source_notes')!=notes:gf.append({'kind':'original_note_binding'})
 source_rows=D.get('source_openings',[]);counts=collections.Counter(q['id']for q in source_rows)
 if set(counts)!=set(raw)or any(n!=1 for n in counts.values()):gf.append({'kind':'exact_raw_opening_set','expected':sorted(raw),'actual':sorted(counts),'multiplicity':dict(counts)})
 sources={q['id']:q for q in source_rows};model_counts=collections.Counter(e['id']for e in M['els']);by={e['id']:e for e in M['els']}
 claimed={e['id']for e in M['els']if(e.get('a')or{}).get('top_roof_shaft_openings_source')}
 if claimed-EXPECTED_IDS:gf.append({'kind':'unexpected_source_claimed_S','ids':sorted(claimed-EXPECTED_IDS)})
 for sid,r in raw.items():
  s=sources.get(sid);errors=[]
  if s is None:errors.append('source_ledger_identity_missing')
  else:
   if s.get('source_drawing_indices')!=r['indices']or s.get('source_raw_items')!=r['raw_items']or s.get('source_pdf_points')!=r['raw_points']or s.get('source_raw_types')!=r['raw_types']:errors.append('raw_original_whole_quad_and_X_operators')
   if s.get('source_transform')!=T or s.get('source_pdf_sha256')!=pdfsha or s.get('source_page')!='STR:24'or s.get('source_layer')!='SHAFT':errors.append('raw_original_scope_and_registration')
   try:
    dev=Polygon(s['source_xy_polygon']).hausdorff_distance(r['polygon'])
    if dev>TOL:errors.append('source_polygon_deviation')
   except Exception:dev=None;errors.append('source_polygon_invalid')
  rawchecks.append({'id':sid,'source_page':'STR:24','source_drawing_indices':r['indices'],'element_ids':[eid for eid,row in D.get('records',{}).items()if any(c.get('source_opening_id')==sid for c in row.get('clipped_voidrings',[]))],'pass':not errors,'errors':errors,'source_profile_deviation_cm':dev if s is not None else None,'scope':'raw_closed_SHAFT_quad_and_X_plan_opening_only','absolute_Z_outer_material_acceptance':False})
 voids=unary_union([r['polygon']for r in raw.values()]);expected_clips=set();actual_clips=set();maxdev=0
 for eid in sorted(EXPECTED_IDS):
  row=D.get('records',{}).get(eid);e=by.get(eid);errors=[]
  if row is None or e is None:preservation.append({'id':eid,'pass':False,'errors':['controlled_slab_or_ledger_missing']});continue
  before=_poly(row['before_g']);after_expected=before.difference(voids);actual=_poly(e['g']);metadata=e.get('a')or{};source_clips={c['source_opening_id']:c for c in row['clipped_voidrings']}
  if model_counts[eid]!=1:errors.append('model_identity_multiplicity')
  if (e['id'],e['c'],e['t'],e['l'],e.get('m'))!=(row['id'],row['c'],row['t'],row['l'],row['m']):errors.append('preserved_identity_category_type_level_material')
  oldZ=row['before_g'][2:4]if row['before_g'][0]=='p'else row['before_g'][5:7];newZ=e['g'][2:4]if e['g'][0]=='p'else e['g'][5:7]
  if newZ!=oldZ:errors.append('preserved_procedural_Z_changed')
  if not actual.is_valid:errors.append('corrected_domain_invalid')
  if actual.symmetric_difference(after_expected).area>1e-7:errors.append('domain_is_not_preserved_before_minus_original_source_voids')
  if e['g']!=row['after_g']or _sha(e['g'])!=row['after_geometry_sha256']:errors.append('frozen_after_geometry_exact_spelling')
  if _sha(row['before_g'])!=row['before_geometry_sha256']:errors.append('preserved_baseline_fingerprint')
  if metadata.get('top_roof_shaft_openings_source')is not True or metadata.get('top_roof_shaft_source_data_sha256')!=FROZEN_SHA or metadata.get('top_roof_shaft_after_geometry_sha256')!=row['after_geometry_sha256']:errors.append('source_scope_metadata')
  if metadata.get('clipped_source_voidrings')!=row['clipped_voidrings']:errors.append('clipped_source_mask_metadata')
  selected_ids={c['source_opening_id']for c in row['clipped_voidrings']};expected_sources=[q for q in D['source_openings']if q['id']in selected_ids]
  if metadata.get('source_openings')!=expected_sources or metadata.get('source_drawing_indices')!=[i for q in expected_sources for i in q['source_drawing_indices']]or metadata.get('source_pdf_points')!=[pt for q in expected_sources for pt in q['source_pdf_points']]or metadata.get('source_transform')!=T or metadata.get('source_pdf_sha256')!=pdfsha or metadata.get('source_page')!='STR:24'or metadata.get('top_roof_shaft_source_record')!=eid:errors.append('model_raw_source_metadata_binding')
  if metadata.get('source_opening_plan_XY_verified')is not True:errors.append('partial_opening_scope_missing')
  if any(metadata.get(k)is not False for k in ['source_outer_XY_verified','source_absolute_Z_verified','source_Z_verified','source_material_verified','source_physical_body_verified','source_dimensions_verified']):errors.append('unsafe_outer_Z_material_body_promotion')
  preservation.append({'id':eid,'pass':not errors,'errors':errors,'source_scope':'local_void_domain_correction_only','full_outer_source_checked':False,'preserved_identity_Z':not any(x.startswith('preserved_')for x in errors),'actual_domain_symmetric_difference_cm2':actual.symmetric_difference(after_expected).area,'before_area_cm2':before.area,'after_area_cm2':actual.area,'removed_area_cm2':before.area-actual.area})
  for sid,r in raw.items():
   clip=before.intersection(r['polygon'])
   if clip.area<=0:continue
   expected_clips.add((eid,sid));q=source_clips.get(sid);err=[]
   if q is None:err.append('source_clip_missing');dev=None
   else:
    actual_clips.add((eid,sid));meta_poly=Polygon(q['clipped_void_polygon']);dev=meta_poly.hausdorff_distance(clip);maxdev=max(maxdev,dev)
    if dev>TOL or meta_poly.symmetric_difference(clip).area>1e-7:err.append('source_clip_polygon')
    if q['source_drawing_indices']!=r['indices']:err.append('source_clip_raw_identity')
    if q['Z_preserved']!=oldZ:err.append('source_clip_procedural_Z')
   filled=actual.intersection(clip).area
   if filled>1e-7:err.append('source_opening_still_filled')
   checks.append({'id':eid+'::'+sid,'element_id':eid,'source_opening_id':sid,'source_page':'STR:24','source_drawing_indices':r['indices'],'pass':not err and not errors,'errors':err+errors,'deviation_cm':dev,'filled_opening_area_cm2':filled,'clipped_source_area_cm2':clip.area,'source_scope':'source_opening_XY_mask_partial_slab_only','body_source_checked':False,'physical_Z_material_acceptance':False})
  for sid in source_clips:
   if (eid,sid)not in expected_clips:actual_clips.add((eid,sid))
 if actual_clips!=expected_clips:gf.append({'kind':'exact_original_clipped_void_inventory','extra':sorted(actual_clips-expected_clips),'missing':sorted(expected_clips-actual_clips)})
 if len(expected_clips)!=7:gf.append({'kind':'original_expected_clipped_part_count','actual':len(expected_clips),'expected':7})
 failures=sum(not q['pass']for q in rawchecks)+sum(not q['pass']for q in checks)+sum(not q['pass']for q in preservation)+len(gf)
 return {'checks':checks,'source_opening_checks':rawchecks,'slab_preservation_checks':preservation,'global_findings':gf,'summary':{'checked':len(checks),'unique_raw_openings':len(rawchecks),'controlled_slab_preservation_checks':len(preservation),'findings':failures,'global_findings':len(gf),'uncovered':max(0,7-len(checks)),'max_deviation_cm':maxdev,'body_source_checked':0,'source_scope':'six_source_opening_XY_profiles_seven_local_clips_only','outer_absolute_Z_material_acceptance':False,'source_pdf_sha256':pdfsha,'source_data_sha256':hashlib.sha256(data_bytes).hexdigest()}}
