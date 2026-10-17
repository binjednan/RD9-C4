# coding:utf-8
"""Read-only raw source XY gate for the two controlled STR11 raft corrections.

The current PDF, raw grid, closed profiles and explicit80/150 thickness labels
are read independently. Before/after ledgers prove identity/preservation, not XY.
Absolute Z, material, reinforcement and bearing never become source acceptance.
"""
import argparse
import functools
import hashlib
import json
import math
import sys
from pathlib import Path
import fitz
from shapely.geometry import Polygon, Point

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'pipeline/data/raft_source_restore.json'
PDF=Path('/Users/binqdair/Downloads/Structure Drawings (1).pdf')
TOL=.2
SCHEMA='c4.raft-source-audit.v1'

def _raw(d):
 points=[];items=[]
 for it in d['items']:
  if it[0]=='l':q=[[v.x,v.y] for v in it[1:3]]
  elif it[0]=='qu':q=[[v.x,v.y] for v in (it[1].ul,it[1].ur,it[1].lr,it[1].ll)]
  else:raise ValueError('Unexpected raft source operator '+it[0])
  points.extend(q);items.append({'operator':it[0],'points':q})
 return points,items
def _tr(points,r):return [[x*r['s']+r['ox'],-y*r['s']+r['oy']] for x,y in points]
def _nested_error(a,b):
 if not isinstance(a,list) or len(a)!=len(b):return math.inf
 if b and isinstance(b[0],(int,float)):
  return max(abs(x-y) for x,y in zip(a,b)) if all(isinstance(x,(int,float)) for x in a) else math.inf
 return max((_nested_error(x,y) for x,y in zip(a,b)),default=0)
def _poly(g):
 if g[0]!='p':raise ValueError('Expected raft polygon prism')
 return Polygon(g[1],g[4] if len(g)>4 and g[4] else None)

@functools.lru_cache(maxsize=2)
def _source(mtime,size):
 doc=fitz.open(PDF);p=doc[10];ds=p.get_drawings()
 sys.path.insert(0,str(ROOT/'pipeline'));import reg
 axes=[d for d in ds if d.get('layer') and ('GRID' in d['layer'].upper() or 'AXIS' in d['layer'].upper()) and 'IDEN' not in d['layer'].upper()]
 v,h=reg.grid_clusters(None,layers=None,drawings=axes,minlen=50);r=reg.register_free(v,h)
 if not r or r['nx']!=17 or r['ny']!=11:raise ValueError('STR11 full registered raw grid unavailable')
 candidates=[(d['rect'].width*d['rect'].height,i,d) for i,d in enumerate(ds) if d.get('layer')=='S-COLUMN'
  and len(d['items'])==1 and d['items'][0][0]=='qu' and d['rect'].width>1200 and d['rect'].height>1200]
 _,oi,outer=max(candidates)
 caps=[(i,d) for i,d in enumerate(ds) if d.get('layer')=='PILES$0$ST-PILE-Caps'
  and len(d['items'])==6 and all(q[0]=='l' for q in d['items'])]
 if len(caps)!=1:raise ValueError('Original six-line PC1 outline is not unique')
 ci,cap=caps[0];cap_points=[q['points'][0] for q in _raw(cap)[1]]
 if _raw(cap)[1][0]['points'][0]!=_raw(cap)[1][-1]['points'][1]:raise ValueError('PC1 source line chain not closed')
 O=Polygon(_tr(_raw(outer)[0],r));C=Polygon(_tr(cap_points,r));D=O.difference(C)
 if not O.is_valid or not C.is_valid or not D.is_valid or D.geom_type!='Polygon':raise ValueError('Original source raft domain invalid')
 literals={}
 for ai,a in enumerate(p.annots()):
  text=a.info.get('content','')
  if text.strip() not in ('SLAB -80cm THICK RAFT','PC1 - 150cm'):continue
  key='RAFT80' if text.strip().startswith('SLAB') else 'PC1'
  if key in literals:raise ValueError('Raft thickness source label duplicated')
  centre=a.rect.tl+(a.rect.br-a.rect.tl)*.5
  pt=Point(*_tr([[centre.x,centre.y]],r)[0])
  if (key=='PC1' and not C.contains(pt)) or (key=='RAFT80' and not D.contains(pt)):raise ValueError('Thickness label does not identify its literal closed plan region')
  literals[key]={'annotation_index':ai,'xref':a.xref,'text':text,'bbox':list(a.rect)}
 if set(literals)!=set(('RAFT80','PC1')):raise ValueError('Explicit80/150 source labels missing')
 result={'drawings':ds,'registration':r,'pdf_sha256':hashlib.sha256(PDF.read_bytes()).hexdigest(),
  'outer_index':oi,'PC1_index':ci,'outer':O,'PC1':C,'domain':D,'literals':literals,
  'PC1_outside_outer_cm2':C.difference(O).area,
  'PC1_bottom_edge_delta_cm':(cap['rect'].y1-outer['rect'].y1)*r['s'],
  'expected':{'S.raft-B-0001':{'poly':D,'indices':[oi,ci],'category':'S.raft','type':'raft80','thickness_cm':80,
    'source_kind':'raft_domain_from_original_outer_minus_PC1','scope':'derived_raft_domain','literal':literals['RAFT80']},
   'S.raft-B-0002':{'poly':C,'indices':[ci],'category':'S.raft','type':'raft150','thickness_cm':150,
    'source_kind':'closed_original_PC1_line_outline','scope':'original_closed_PC1_profile','literal':literals['PC1']}}}
 doc.close();return result

def audit(M):
 # Rehydrate external audit inputs; geometry remains the live model.
 import sys as _audit_sys
 from pathlib import Path as _AuditPath
 _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
 from source_audit_sidecar import audit_model as _source_audit_model
 M = _source_audit_model(M)
 checks=[];findings=[];uncovered=[]
 try:
  stat=PDF.stat();raw=_source(stat.st_mtime_ns,stat.st_size);D=json.loads(DATA.read_text())
 except Exception as error:
  return {'schema':SCHEMA,'checks':[],'findings':[{'reason':'raw_source_unavailable','detail':str(error)}],
   'uncovered':[],'summary':{'passed':False}}
 by={e['id']:e for e in M['els']};r=raw['registration']
 for eid,q in raw['expected'].items():
  e=by.get(eid)
  if not e:uncovered.append(eid);continue
  a=e.get('a') or {};ledger=D.get('records',{}).get(eid,{});source=ledger.get('source',{});errors=[]
  indices=a.get('source_drawing_indices',[])
  if indices!=q['indices'] or source.get('source_drawing_indices')!=q['indices']:errors.append('raw_source_drawing_identity_differs')
  raw_error=math.inf
  if all(isinstance(i,int) and 0<=i<len(raw['drawings']) for i in indices):
   try:raw_error=_nested_error(a.get('source_pdf_points'),[_raw(raw['drawings'][i])[0] for i in indices])*r['s']
   except Exception:errors.append('raw_source_operator_unexpected')
  if raw_error>1e-6:errors.append('raw_metadata_points_differ')
  if len(source.get('source_drawings',[]))!=len(q['indices']):errors.append('raw_source_drawing_count_differs')
  for saved,i in zip(source.get('source_drawings',[]),q['indices']):
   d=raw['drawings'][i]
   if saved.get('drawing_index')!=i or saved.get('layer')!=d.get('layer') or saved.get('raw_items')!=_raw(d)[1]:errors.append('source_layer_or_raw_operators_differ')
  transform_error=max(abs((a.get('source_transform')or{}).get(k,math.inf)-r[k]) for k in ('s','ox','oy'))
  if transform_error>1e-8:errors.append('current_raw_grid_registration_differs')
  if a.get('source_pdf_sha256')!=raw['pdf_sha256'] or source.get('source_pdf_sha256')!=raw['pdf_sha256']:errors.append('current_PDF_fingerprint_differs')
  if a.get('source_annotation')!=q['literal'] or source.get('source_annotation')!=q['literal']:errors.append('thickness_source_literal_or_bbox_differs')
  try:
   body=_poly(e['g']);delta=body.hausdorff_distance(q['poly']);symdiff=body.symmetric_difference(q['poly']).area
   meta=Polygon(a['source_xy']);meta_delta=meta.hausdorff_distance(q['poly'])
   thickness=abs((e['g'][3]-e['g'][2])*100-q['thickness_cm'])
   if not body.is_valid:errors.append('invalid_model_domain')
  except Exception as error:delta=meta_delta=symdiff=thickness=math.inf;errors.append('invalid_prism:'+str(error))
  if max(delta,meta_delta)>TOL:errors.append('original_source_XY_deviation')
  if thickness>1e-8:errors.append('source_thickness_deviation')
  if e['c']!=q['category'] or e['t']!=q['type'] or e['l']!='B':errors.append('controlled_source_identity_differs')
  if a.get('source_page')!='STR:11' or a.get('source_kind')!=q['source_kind']:errors.append('source_provenance_kind_differs')
  if not a.get('source_locked_xy') or not a.get('source_semantics_checked'):errors.append('source_guards_missing')
  if a.get('source_Z_verified') or a.get('source_material_verified') or a.get('source_physical_color_verified'):errors.append('XY_scope_promoted_to_Z_material_or_color')
  if ledger.get('before_g',[None]*4)[2:4]!=e['g'][2:4]:errors.append('retained_Z_values_changed')
  check={'id':eid,'proof_scope':q['scope'],'xy_deviation_cm':delta,'metadata_xy_deviation_cm':meta_delta,
   'symmetric_difference_cm2':symdiff,'raw_metadata_deviation_cm':raw_error,
   'registration_deviation':transform_error,'thickness_deviation_cm':thickness,
   'Z_verified':False,'material_verified':False,'errors':errors}
  checks.append(check)
  if errors:findings.append({'id':eid,'reasons':errors})
 return {'schema':SCHEMA,'tolerance_cm':TOL,'checks':checks,'findings':findings,'uncovered':uncovered,
  'current_source_registration':r,'current_source_pdf_sha256':raw['pdf_sha256'],'source_literals':raw['literals'],
  'source_edge_precision':{'PC1_outside_outer_cm2':raw['PC1_outside_outer_cm2'],
   'PC1_bottom_edge_delta_cm':raw['PC1_bottom_edge_delta_cm'],
   'scope_ar':'فرق تقريبي خام منPDF؛ PC1 لم يُقص، والمجال80سم هوouter minusPC1. لا اختلاف تصميمي مؤكد بهذا الفرق.'},
  'summary':{'original_profile_checks':sum(c['proof_scope']=='original_closed_PC1_profile' for c in checks),
   'derived_domain_checks':sum(c['proof_scope']=='derived_raft_domain' for c in checks),
   'findings':len(findings),'uncovered':len(uncovered),'max_xy_deviation_cm':max((c['xy_deviation_cm'] for c in checks),default=None),
   'passed':not findings and not uncovered,'scope_ar':'تحقق XY والهوية وسماكة80/150 المرقمة فقط؛ Z المطلق والمواد والتسليح والارتكاز غير مثبتة هنا.'}}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--model',default=str(ROOT/'src/model.json'));parser.add_argument('--output')
 args=parser.parse_args();result=audit(json.loads(Path(args.model).read_text()))
 if args.output:Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps(result['summary'],ensure_ascii=False));sys.exit(0 if result['summary']['passed'] else 1)
