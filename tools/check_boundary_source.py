# coding:utf-8
"""Independent raw PDF audit for C*/CB1 boundary components.

The architectural grid registration is computed anew from the current A101 PDF.
Data records provide identities and declared provenance, never expected XY.
Forty-one original column profiles and forty-three derived outlines stay distinct.
This tool reads only; it never opens lib.Sheet, writes its cache, or moves geometry.
"""
import argparse
import functools
import hashlib
import json
import math
import re
import sys
from pathlib import Path
import fitz
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'pipeline/data/boundary_source_remaining.json'
STR=Path('/Users/binqdair/Downloads/Structure Drawings (1).pdf')
ARCH=Path('/Users/binqdair/Downloads/Arch. Drawings Part I (1).pdf')
TOL=.2
SCHEMA='c4.boundary-source-audit.v1'

def _raw(d):
 points=[];items=[]
 for it in d['items']:
  if it[0]=='l':p=[[q.x,q.y] for q in it[1:3]]
  elif it[0]=='qu':p=[[q.x,q.y] for q in (it[1].ul,it[1].ur,it[1].lr,it[1].ll)]
  else:raise ValueError('Unexpected source operator '+it[0])
  items.append({'operator':it[0],'points':p});points.extend(p)
 return points,items
def _ring(r):return [[r.x0,r.y0],[r.x1,r.y0],[r.x1,r.y1],[r.x0,r.y1]]
def _poly(g):
 if g[0]=='p':return Polygon(g[1],g[4] if len(g)>4 and g[4] else [])
 if g[0]=='r':return box(*g[1:5])
 raise ValueError('Expected prism')
def _z(g):return g[2:4] if g[0]=='p' else g[5:7]
def _text(t):return ''.join(chr(c[0]) for c in t['chars'])
def _nested_error(a,b):
 if not isinstance(a,list) or len(a)!=len(b):return math.inf
 if b and isinstance(b[0],(int,float)):
  return max(abs(x-y) for x,y in zip(a,b)) if all(isinstance(x,(int,float)) for x in a) else math.inf
 return max((_nested_error(x,y) for x,y in zip(a,b)),default=0)
def _tr(points,t):return [[x*t['s']+t['ox'],-y*t['s']+t['oy']] for x,y in points]
def _revision(path):s=path.stat();return (str(path),s.st_mtime_ns,s.st_size)

@functools.lru_cache(maxsize=2)
def _sources(str_revision,arch_revision):
 sdoc=fitz.open(STR);adoc=fitz.open(ARCH)
 sp=sdoc[31];ds=sp.get_drawings();ap=adoc[3];ads=ap.get_drawings()
 sys.path.insert(0,str(ROOT/'pipeline'));import reg
 axes=[d for d in ads if d.get('layer') and
  ('GRID' in d['layer'].upper() or 'AXIS' in d['layer'].upper()) and 'IDEN' not in d['layer'].upper()]
 vv,hh=reg.grid_clusters(None,layers=None,drawings=axes,minlen=50)
 registered=reg.register_free(vv,hh)
 if not registered or registered['nx']<17 or registered['ny']<11:
  raise ValueError('A101 current raw axes do not prove full project registration')
 # Unique outer site quad, larger than the inner building/retaining-wall quad.
 plots=[(d['rect'].width*d['rect'].height,i,d) for i,d in enumerate(ads) if d.get('layer')=='S-COLUMN'
  and len(d['items'])==1 and d['items'][0][0]=='qu' and d['rect'].width>1200 and d['rect'].height>1200]
 _,plot_i,plot=max(plots)
 anchor=_tr([[plot['rect'].x0,plot['rect'].y0]],registered)[0]
 # Main-plan U edges: long three-line BEAM chains, source outer and inner faces.
 u=[]
 for i,d in enumerate(ds):
  if d.get('layer')!='BEAM' or len(d['items'])!=3 or d['rect'].width<1200:continue
  a,b,c=d['items']
  if any(q[0]!='l' for q in (a,b,c)):continue
  if a[1].x==a[2].x and b[1].y==b[2].y and c[1].x==c[2].x:u.append((i,d))
 unique={}
 for i,d in u:unique.setdefault(tuple(d['rect']), (i,d))
 edge=sorted(unique.values(),key=lambda q:q[1]['rect'].width,reverse=True)
 if len(edge)!=2:raise ValueError('Main source U edge pair not unique')
 outer_i,outer_d=edge[0];inner_i,inner_d=edge[1];outer=outer_d['rect'];inner=inner_d['rect']
 caps=[(i,d) for i,d in enumerate(ds) if d.get('layer')=='BEAM' and len(d['items'])==3
  and d['rect'].width<10 and d['rect'].height>400 and d['rect'].y0>800]
 if len(caps)!=2:raise ValueError('Lower coping capped-edge chains not unique')
 (lc_i,lc),(rc_i,rc)=sorted(caps,key=lambda q:q[1]['rect'].x0)
 t={'s':registered['s'],'ox':anchor[0]-registered['s']*outer.x0,'oy':anchor[1]+registered['s']*outer.y0}
 # Source precision epsilon here only selects the main sheet viewport, not model geometry.
 pool=[];seen=set()
 for i,d in enumerate(ds):
  if d.get('layer')!='S-COLUMN' or len(d['items'])!=1 or d['items'][0][0]!='qu':continue
  r=d['rect']
  if r.x0<outer.x0-.001 or r.x1>outer.x1+.001 or r.y0<outer.y0-.001 or r.y1>lc['rect'].y1+.001:continue
  if not (r.y0<inner.y0 or r.x1<=inner.x0+.001 or r.x0>=inner.x1-.001):continue
  signature=tuple(tuple(p) for p in _raw(d)[0])
  if signature in seen:continue
  seen.add(signature);pool.append(i)
 if len(pool)!=41:raise ValueError('Expected 41 unique main-plan C* profiles, got '+str(len(pool)))
 top=sorted([i for i in pool if ds[i]['rect'].y0<inner.y0],key=lambda i:ds[i]['rect'].x0)
 left=sorted([i for i in pool if i not in top and ds[i]['rect'].x0<inner.x0],key=lambda i:-ds[i]['rect'].y1)
 right=sorted([i for i in pool if i not in top and i not in left],key=lambda i:ds[i]['rect'].y0)
 columns=left+top+right
 expected={};joints=[];spans=[]
 def add(eid,points,category,kind,indices,z):
  expected[eid]={'pdf_poly':Polygon(points),'world_poly':Polygon(_tr(points,t)),
   'category':category,'proof_kind':kind,'required_indices':set(indices),'z':z}
 for n,i in enumerate(columns,1):
  add(f'S.col-G-BND{n:04d}',_raw(ds[i])[0],'S.col','original_closed_column_profile',[i],[-.1,2.7])
 for a,b in zip(columns,columns[1:]):
  ra,rb=ds[a]['rect'],ds[b]['rect']
  if a in left:r=fitz.Rect(ra.x0,rb.y1,ra.x1,ra.y0);face='left'
  elif a in top and b in top:r=fitz.Rect(ra.x1,ra.y0,rb.x0,ra.y1);face='top'
  else:r=fitz.Rect(rb.x0,ra.y1,rb.x1,rb.y0);face='right'
  gap=r.width if face=='top' else r.height
  if gap<1.1:joints.append((face,r,a,b))
  else:spans.append((r,a,b))
 if len(spans)!=37 or len(joints)!=3:raise ValueError('C* clear-span / expansion-joint partition differs')
 for n,(r,a,b) in enumerate(spans,1):add(f'A.site-G-BND{n:04d}',_ring(r),'A.site','derived_block_between_source_faces',[a,b],[-.1,2.7])
 tj=next(r for f,r,a,b in joints if f=='top');lj=next(r for f,r,a,b in joints if f=='left');rj=next(r for f,r,a,b in joints if f=='right')
 bands=[fitz.Rect(outer.x0,outer.y0,tj.x0,inner.y0),fitz.Rect(tj.x1,outer.y0,outer.x1,inner.y0),
  fitz.Rect(outer.x0,inner.y0,inner.x0,lj.y0),fitz.Rect(lc['rect'].x0,lj.y1,lc['rect'].x1,lc['rect'].y1),
  fitz.Rect(inner.x1,inner.y0,outer.x1,rj.y0),fitz.Rect(rc['rect'].x0,rj.y1,rc['rect'].x1,rc['rect'].y1)]
 for n,r in enumerate(bands,1):
  band=box(*r);heads=[i for i in pool if band.intersection(Polygon(_raw(ds[i])[0])).area/Polygon(_raw(ds[i])[0]).area>.99]
  union=unary_union([band]+[Polygon(_raw(ds[i])[0]) for i in heads])
  add(f'S.beam-G-BND{n:04d}',list(union.exterior.coords)[:-1],'S.beam','derived_continuous_source_coping_with_head_union',heads,[2.7,3.0])
  expected[f'S.beam-G-BND{n:04d}']['head_indices']=set(heads)
 # Validate current A400 unique closed U, including actual closed line chain.
 a400=adoc[15];d400=a400.get_drawings();candidates=[]
 for i,d in enumerate(d400):
  if d.get('layer')!='A-WALL' or len(d['items'])!=8 or d['rect'].width<1200 or d['rect'].height<1200:continue
  pts,items=_raw(d)
  if pts[0]==pts[-1] and Polygon([q['points'][0] for q in items]).is_valid:candidates.append((i,d))
 if len(candidates)!=1:raise ValueError('A400 closed boundary U not unique')
 i400,q400=candidates[0]
 literals=[]
 for trace_i in [26,13,27,77,79,97,99,100,102,104,105]:
  tr=sp.get_texttrace()[trace_i];literals.append({'source_page':'STR:32','texttrace_index':trace_i,'text':_text(tr),'bbox':list(tr['bbox'])})
 annotations=list(sp.annots());a_literals=[]
 for ai in [16,22,30,32,33,34,49,50,51]:
  a=annotations[ai];a_literals.append({'annotation_index':ai,'xref':a.xref,'text':a.info.get('content'),'bbox':list(a.rect)})
 if a_literals[0]['text']!='200' or a_literals[1]['text']!='300' or a_literals[2]['text']!='BLOCK WALL':raise ValueError('CB1 / material literals differ')
 if not any('CL.+ 3.0'==q['text'] for q in literals) or not any('CL.-0.10'==q['text'] for q in literals):raise ValueError('Vertical source datum literal differs')
 if sum(w[4]=='C*' for w in sp.get_text('words'))!=41 or sum(w[4]=='CB1' for w in sp.get_text('words'))!=37:raise ValueError('Current source C*/CB1 label quantities differ')
 p31=sdoc[30];j_literals=[{'source_page':'STR:31','texttrace_index':i,'text':_text(p31.get_texttrace()[i]),'bbox':list(p31.get_texttrace()[i]['bbox'])} for i in [260,261,262]]
 if any(q['text']!='2CM EXP JOINT' for q in j_literals):raise ValueError('Literal expansion joint scope missing')
 leaders={i:_raw(p31.get_drawings()[i]) for i in [8586,8587]}
 result={'expected':expected,'drawings':ds,'transform':t,'reference_registration':registered,
  'source_pdf_sha256':hashlib.sha256(STR.read_bytes()).hexdigest(),'arch_pdf_sha256':hashlib.sha256(ARCH.read_bytes()).hexdigest(),
  'plot_index':plot_i,'plot_raw_points':_raw(plot)[0],'anchor_pdf':[plot['rect'].x0,plot['rect'].y0],'anchor_world_cm':anchor,
  'A400_closed_index':i400,'A400_raw':_raw(q400),
  'A400_transform':{'s':t['s'],'ox':anchor[0]-t['s']*q400['rect'].x0,'oy':anchor[1]+t['s']*q400['rect'].y0},
  'A400_width_difference_cm':(q400['rect'].width-outer.width)*t['s'],
  'A400_side_difference_cm':(q400['rect'].height-(lc['rect'].y1-outer.y0))*t['s'],
  'literals':literals,'annotation_literals':a_literals,'joint_literals':j_literals,'joint_leaders':leaders}
 sdoc.close();adoc.close();return result

def audit(M):
 # Rehydrate external audit inputs; geometry remains the live model.
 import sys as _audit_sys
 from pathlib import Path as _AuditPath
 _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
 from source_audit_sidecar import audit_model as _source_audit_model
 M = _source_audit_model(M)
 findings=[];checks=[];uncovered=[]
 try:raw=_sources(_revision(STR),_revision(ARCH));D=json.loads(DATA.read_text())
 except Exception as error:
  return {'schema':SCHEMA,'checks':[],'findings':[{'reason':'raw_source_unavailable','detail':str(error)}],'uncovered':[], 'summary':{'passed':False}}
 by_id={e['id']:e for e in M['els']};t=raw['transform']
 for eid,q in raw['expected'].items():
  e=by_id.get(eid)
  if e is None:uncovered.append(eid);continue
  a=e.get('a') or {};record=D.get('records',{}).get(eid,{});s=record.get('source',{});errors=[]
  indices=a.get('source_drawing_indices',[])
  if indices!=s.get('source_drawing_indices') or not q['required_indices'].issubset(indices):errors.append('raw_drawing_identity_differs')
  if len(s.get('source_drawings',[]))!=len(indices):errors.append('saved_raw_drawing_count_differs')
  if q['proof_kind']=='original_closed_column_profile' and set(indices)!=q['required_indices']:errors.append('column_raw_identity_differs')
  if a.get('source_head_union_drawing_indices') is not None and set(a['source_head_union_drawing_indices'])!=q.get('head_indices',set()):errors.append('head_union_identity_differs')
  valid_indices=all(isinstance(i,int) and 0<=i<len(raw['drawings']) for i in indices)
  p_error=math.inf
  if valid_indices:
   try:
    p_error=_nested_error(a.get('source_pdf_points'),[_raw(raw['drawings'][i])[0] for i in indices])*t['s']
    for saved,i in zip(s.get('source_drawings',[]),indices):
     if saved.get('drawing_index')!=i or saved.get('layer')!=raw['drawings'][i].get('layer') or saved.get('raw_items')!=_raw(raw['drawings'][i])[1]:errors.append('saved_raw_operator_or_layer_differs');break
   except Exception:errors.append('source_drawing_operator_unexpected')
  if p_error>1e-6:errors.append('raw_source_metadata_points_differs')
  transform_error=max(abs((a.get('source_transform')or{}).get(k,math.inf)-t[k]) for k in ('s','ox','oy'))
  if transform_error>1e-8:errors.append('current_raw_registration_differs')
  if a.get('source_pdf_sha256')!=raw['source_pdf_sha256'] or s.get('source_pdf_sha256')!=raw['source_pdf_sha256']:errors.append('current_source_pdf_fingerprint_differs')
  try:
   actual=_poly(e['g']);xy_error=actual.hausdorff_distance(q['world_poly']);area=actual.symmetric_difference(q['world_poly']).area
   meta=Polygon(a['source_xy']);meta_error=meta.hausdorff_distance(q['world_poly'])
   boundary=Polygon(_tr(a['source_boundary_pdf'],t));boundary_error=boundary.hausdorff_distance(q['world_poly'])
   z_error=max(abs(x-y) for x,y in zip(_z(e['g']),q['z']))
   if not actual.is_valid:errors.append('invalid_model_polygon')
  except Exception as error:xy_error=area=meta_error=boundary_error=z_error=math.inf;errors.append('invalid_metadata_or_body:'+str(error))
  if max(xy_error,meta_error,boundary_error)>TOL:errors.append('source_footprint_deviation')
  if z_error>1e-8:errors.append('source_datum_boundaries_differ')
  if e['c']!=q['category']:errors.append('source_component_class_differs')
  if a.get('source_page')!='STR:32':errors.append('source_sheet_identity_differs')
  if q['category']=='S.col':
   if a.get('source_kind')!='closed_structural_column_quad' or not a.get('source_structural_XY_verified'):
    errors.append('raw_column_proof_kind_differs')
  elif not a.get('source_footprint_derived') or a.get('source_structural_XY_verified'):
   errors.append('derived_outline_promoted_to_original_raw_profile')
  if not a.get('source_locked_xy') or not a.get('source_semantics_checked'):errors.append('source_guards_missing')
  if q['category']!='S.beam' and a.get('source_Z_verified'):errors.append('derived_height_promoted_to_raw_verified')
  if not a.get('source_material_class_verified') or a.get('source_material_verified') or a.get('source_physical_color_verified'):
   errors.append('material_class_scope_promoted_to_full_material_or_color')
  check={'id':eid,'proof_kind':q['proof_kind'],'proof_scope':'raw_profile' if q['category']=='S.col' else 'derived_outline',
   'xy_deviation_cm':xy_error,'metadata_xy_deviation_cm':meta_error,'boundary_xy_deviation_cm':boundary_error,
   'symmetric_difference_cm2':area,'raw_metadata_deviation_cm':p_error,'registration_deviation':transform_error,
   'z_boundary_deviation_m':z_error,'height_scope':'literal_CB1_datums' if q['category']=='S.beam' else 'derived_above_grade_datums',
   'errors':errors}
  checks.append(check)
  if errors:findings.append({'id':eid,'reasons':errors})
 # Reference hashes and source literals are independently read, not inferred from counts.
 ref=D.get('registration_basis',{}).get('registered_arch_reference',{})
 if ref.get('source_pdf_sha256')!=raw['arch_pdf_sha256'] or ref.get('source_drawing_index')!=raw['plot_index'] or ref.get('raw',{}).get('raw_points')!=raw['plot_raw_points']:
  findings.append({'reason':'A101_live_source_reference_identity_differs'})
 a400=D.get('registration_basis',{}).get('A400_reference',{});saved=a400.get('raw_closed_boundary',{})
 if saved.get('drawing_index')!=raw['A400_closed_index'] or (saved.get('raw_points'),saved.get('raw_items'))!=raw['A400_raw']:
  findings.append({'reason':'A400_live_closed_boundary_identity_differs'})
 if any(abs(a400.get('transform',{}).get(k,math.inf)-raw['A400_transform'][k])>1e-8 for k in ('s','ox','oy')):
  findings.append({'reason':'A400_current_corner_registration_differs'})
 if D.get('source_datums',{}).get('traces')!=[{**q,'layer':None} for q in raw['literals']]:
  # Text trace layer is not a geometric authority; compare the remaining raw fields.
  saved=[{k:v for k,v in q.items() if k!='layer'} for q in D.get('source_datums',{}).get('traces',[])]
  expected=[{k:v for k,v in q.items() if k!='source_page'} for q in raw['literals']]
  if saved!=expected:findings.append({'reason':'source_datum_texttrace_or_bbox_differs'})
 if D.get('source_datums',{}).get('annotations')!=raw['annotation_literals']:findings.append({'reason':'source_annotation_literal_or_bbox_differs'})
 if D.get('source_datums',{}).get('joint_text')!=raw['joint_literals']:findings.append({'reason':'source_joint_text_or_bbox_differs'})
 for saved in D.get('source_datums',{}).get('top_joint_leader_drawings',[]):
  i=saved.get('drawing_index')
  if i not in raw['joint_leaders'] or (saved.get('raw_points'),saved.get('raw_items'))!=raw['joint_leaders'][i]:findings.append({'reason':'top_joint_raw_leader_differs'})
 for eid in ('A.site-G-0001','A.site-G-0002','A.site-G-0003'):
  if eid in by_id:findings.append({'id':eid,'reason':'retired_generic_envelope_still_present'})
 for eid in by_id:
  if re.search(r'-BND\d{4}$',eid) and eid not in raw['expected']:findings.append({'id':eid,'reason':'unrecognized_boundary_source_identity'})
 return {'schema':SCHEMA,'tolerance_cm':TOL,'checks':checks,'findings':findings,'uncovered':uncovered,
  'source_registration':{k:v for k,v in raw.items() if k in ('transform','reference_registration','anchor_pdf','anchor_world_cm','plot_index','A400_closed_index','A400_width_difference_cm','A400_side_difference_cm','source_pdf_sha256','arch_pdf_sha256')},
  'source_literals':{'traces':raw['literals'],'annotations':raw['annotation_literals'],'joint_text':raw['joint_literals']},
  'summary':{'raw_profile_checks':sum(q['proof_scope']=='raw_profile' for q in checks),
   'derived_outline_checks':sum(q['proof_scope']=='derived_outline' for q in checks),'findings':len(findings),'uncovered':len(uncovered),
   'max_xy_deviation_cm':max((q['xy_deviation_cm'] for q in checks),default=None),'passed':not findings and not uncovered,
   'scope_ar':'41 حدود أعمدة خام و43 بصمة مشتقة من وجوه المصدر؛ Z للحشوات/الأعمدة مشتق، والتسليح والربط والطلاء غير معتمد. لا إثبات تنفيذ بالموقع.'}}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--model',default=str(ROOT/'src/model.json'));parser.add_argument('--output')
 args=parser.parse_args();result=audit(json.loads(Path(args.model).read_text()))
 if args.output:Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps(result['summary'],ensure_ascii=False));sys.exit(0 if result['summary']['passed'] else 1)
