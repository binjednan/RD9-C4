# coding:utf-8
"""Source-backed model geometry matching for two raft bodies; no model edits.

The gate rereads the authenticated PDF's raw grid, plan profiles and sections.
It does not infer proof from old verification flags, saved geometries or ledgers.
PC1's missing depressed lift pit is a reported model/source conflict, never a pass.
"""
import copy
import hashlib
import json
import math
from pathlib import Path

import fitz
from shapely.geometry import Polygon, Point, LineString

ROOT=Path(__file__).resolve().parents[1]
DATA_PATH=ROOT/'pipeline/data/raft_model_acceptance.json'
DATA_SHA256='5cecf3a989ca7aa9688af41097235b563151f94669ff01a2095bb6711894a750'
SCHEMA='c4.raft-model-acceptance.v1'
IDS=('S.raft-B-0001','S.raft-B-0002')

def _sha(v):
 return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def _bytes_sha(b):return hashlib.sha256(b).hexdigest()

def _pdf_path(name):
 for p in (ROOT.parents[1]/'project-sources'/name,Path('/Users/binqdair/Downloads')/name):
  if p.is_file():return p
 raise FileNotFoundError(name)

def _drawing(d):
 items=[]
 for q in d['items']:
  if q[0]=='l':pts=[list(v) for v in q[1:]]
  elif q[0]=='qu':pts=[list(v) for v in (q[1].ul,q[1].ur,q[1].lr,q[1].ll)]
  else:raise ValueError('Unexpected controlled drawing operator '+q[0])
  items.append({'operator':q[0],'points':pts})
 return {'layer':d.get('layer'),'bbox':list(d['rect']),'items':items}

def _points(d):
 q=_drawing(d)['items']
 return q[0]['points'] if len(q)==1 and q[0]['operator']=='qu' else [v['points'][0] for v in q]

def _tr(points,r):return [[x*r['s']+r['ox'],-y*r['s']+r['oy']] for x,y in points]

def _source(D,pdf_path=None,verify_images=True):
 """Independently reconstruct expected shapes from the current PDF, not D geometry."""
 import reg
 pdf=Path(pdf_path) if pdf_path else _pdf_path(D['source_pdf'])
 if _bytes_sha(pdf.read_bytes())!=D['source_pdf_sha256']:raise ValueError('Source PDF SHA differs')
 doc=fitz.open(pdf);pages={11:doc[10],12:doc[11]};drawings={p:pg.get_drawings() for p,pg in pages.items()}
 traces={p:pg.get_texttrace() for p,pg in pages.items()};annotations={p:list(pg.annots() or []) for p,pg in pages.items()}
 checks=[]
 for q in D['raw_texts']:
  t=traces[q['page']][q['texttrace_index']]
  actual={'text':''.join(chr(c[0]) for c in t['chars']),'bbox':list(t['bbox']),'layer':t.get('layer')}
  if actual!={k:q[k] for k in actual}:raise ValueError('Source text differs '+str((q['page'],q['texttrace_index'])))
  checks.append('text:%d:%d'%(q['page'],q['texttrace_index']))
 for q in D['raw_annotations']:
  a=annotations[q['page']][q['annotation_index']]
  if {'xref':a.xref,'text':a.info['content'],'bbox':list(a.rect)}!={k:q[k] for k in ('xref','text','bbox')}:raise ValueError('Source annotation differs')
  checks.append('annotation:%d:%d'%(q['page'],q['annotation_index']))
 for q in D['raw_drawings']:
  actual=_drawing(drawings[q['page']][q['drawing_index']])
  if actual!={k:q[k] for k in actual}:raise ValueError('Source drawing differs '+str((q['page'],q['drawing_index'])))
  checks.append('drawing:%d:%d'%(q['page'],q['drawing_index']))
 image_checks=[]
 if verify_images:
  for q in D['renderings']:
   saved=(ROOT/q['path']).resolve()
   pix=pages[q['page']].get_pixmap(matrix=fitz.Matrix(q['scale'],q['scale']),clip=fitz.Rect(q['clip']),annots=q['annots'])
   valid=saved.is_file() and _bytes_sha(saved.read_bytes())==q['sha256'] and _bytes_sha(pix.tobytes('png'))==q['sha256']
   image_checks.append({'path':q['path'],'sha256':q['sha256'],'pass':valid})
   if not valid:raise ValueError('Original rendering differs '+q['path'])
 ds=drawings[11]
 axes=[d for d in ds if d.get('layer') and ('GRID' in d['layer'].upper() or 'AXIS' in d['layer'].upper()) and 'IDEN' not in d['layer'].upper()]
 vv,hh=reg.grid_clusters(None,layers=None,drawings=axes,minlen=50);r=reg.register_free(vv,hh)
 if not r or (r['nx'],r['ny'],len(vv),len(hh))!=(17,11,17,11):raise ValueError('Complete registered structural raw grid unavailable')
 candidates=[(d['rect'].width*d['rect'].height,i) for i,d in enumerate(ds) if d.get('layer')=='S-COLUMN' and len(d['items'])==1 and d['items'][0][0]=='qu' and d['rect'].width>1200 and d['rect'].height>1200]
 oi=max(candidates)[1]
 ci_candidates=[i for i,d in enumerate(ds) if d.get('layer')=='PILES$0$ST-PILE-Caps' and len(d['items'])==6 and all(v[0]=='l' for v in d['items'])]
 if len(ci_candidates)!=1:raise ValueError('PC1 source outline not unique')
 ci=ci_candidates[0]
 if (oi,ci)!=(3561,6285):raise ValueError('Controlled source plan identity changed')
 cap=ds[ci]
 if list(cap['items'][0][1])!=list(cap['items'][-1][2]):raise ValueError('PC1 raw outline not closed')
 O=Polygon(_tr(_points(ds[oi]),r));C=Polygon(_tr(_points(cap),r));R=O.difference(C)
 if not all(g.is_valid and g.geom_type=='Polygon' for g in (O,C,R)):raise ValueError('Invalid raw footprint')
 # The labels must still lie in their respective independently reconstructed domains.
 for ai,region in ((63,R),(67,C)):
  a=annotations[11][ai];xy=_tr([list((a.rect.tl+a.rect.br)*.5)],r)[0]
  if not region.contains(Point(xy)):raise ValueError('Plan thickness label not in its domain')
 # Link section1A to the actual 80cm zone: matching raw horizontal leader datums.
 yl=ds[6]['items'][0][1].y;yr=ds[9]['items'][0][1].y
 if abs(yl-yr)>1e-6:raise ValueError('Section1A plan leaders not at same ordinate')
 line=LineString(_tr([[ds[oi]['rect'].x0,yl],[ds[oi]['rect'].x1,yl]],r))
 if line.intersection(C).length>1e-6 or abs(line.intersection(R).length-line.length)>1e-6:raise ValueError('Section1A does not cut only the 80cm region')
 top=drawings[12][5574]['items'][1];bot=drawings[12][5583]['items'][-1]
 if top[1].y!=top[2].y or bot[1].y!=bot[2].y or top[1].y>=bot[1].y:raise ValueError('Section1A is not a horizontal positive-thickness slab')
 # Literal80 and CL-3.9 control Z; the NTS section is not measured for height.
 top_m=float(''.join(chr(c[0]) for c in traces[12][77]['chars']).replace('CL.','').replace(' ',''))
 th80=float(''.join(chr(c[0]) for c in traces[12][57]['chars']))
 th150=float(''.join(chr(c[0]) for c in traces[12][71]['chars']))
 if (top_m,th80,th150)!=(-3.9,80.,150.):raise ValueError('Literal levels/thicknesses changed')
 # The lift inner regions are genuinely inside PC1. Their section has a lower top.
 pits=[Polygon(_tr(_points(ds[i]),r)) for i in (3737,3739)]
 if not all(C.contains(g) for g in pits):raise ValueError('Lift openings are not inside PC1')
 pit_top=drawings[12][22407]['items'][1];wing_top=drawings[12][22408]['items'][1]
 if pit_top[1].y<=wing_top[1].y:raise ValueError('Section does not depict a depressed lift pit')
 if ''.join(chr(c[0]) for c in traces[12][50]['chars'])!='CL.- AS MEP':raise ValueError('Unresolved pit datum changed')
 residuals={'X':[min(abs(x*r['s']+r['ox']-v) for v in reg.GX_list) for x in vv],'Y':[min(abs(-y*r['s']+r['oy']-v) for v in reg.GY_list) for y in hh]}
 result={'polys':{IDS[0]:R,IDS[1]:C},'pits':pits,'top_m':top_m,'thickness_cm':{IDS[0]:th80,IDS[1]:th150},
  'proof':{'pdf_sha256':D['source_pdf_sha256'],'raw_checks':checks,'renderings':image_checks,'registration':r,'registration_axis_residuals_cm':residuals,
   'max_registration_axis_residual_cm':max(residuals['X']+residuals['Y']),'registration_residuals_are_not_model_tolerance':True,
   'section_1A_plan_raw_y':yl,'PC1_min_raw_y':cap['rect'].y0,'section_1A_PC1_intersection_length_cm':line.intersection(C).length,
   'section_1A_registered_length_cm':line.length,'section_1A_raft80_intersection_length_cm':line.intersection(R).length,
   'lift_pit_inside_PC1':True,'lift_pit_source_Z':'CL.- AS MEP','lift_pit_is_depicted_lower':True,
   'PC1_outside_outer_cm2':C.difference(O).area,'PC1_bottom_source_edge_delta_cm':(cap['rect'].y1-ds[oi]['rect'].y1)*r['s'],
   'scope_ar':D['scope_ar']}}
 doc.close();return result

def audit(M,pdf_path=None,verify_images=True):
 """Read-only report. Known model conflict is distinct from failed proof guards."""
 errors=[];results=[]
 try:
  data_bytes=DATA_PATH.read_bytes()
  if _bytes_sha(data_bytes)!=DATA_SHA256:raise ValueError('Controlled data SHA differs')
  D=json.loads(data_bytes);S=_source(D,pdf_path,verify_images)
 except Exception as exc:
  return {'schema':SCHEMA,'pass':False,'errors':[str(exc)],'results':[],'matched_count':0,'conflict_count':0,'source_proof':None,'model_geometry_sha256':_sha([(e.get('id'),e.get('g')) for e in M.get('els',[]) if e.get('id') in IDS])}
 all_by={}
 for e in M.get('els',[]):all_by.setdefault(e.get('id'),[]).append(e)
 for eid in IDS:
  local=[];q=D['records'][eid];copies=all_by.get(eid,[])
  if len(copies)!=1:
   errors.append(eid+': identity missing or duplicated');results.append({'id':eid,'status':'conflict','model_geometry_match':False,'errors':['identity_missing_or_duplicated'],'conflict_ids':q['conflict_ids']});continue
  e=copies[0];g=e.get('g',[])
  if (e.get('c'),e.get('t'),e.get('l'))!=(q['category'],q['type'],q['level']):local.append('element_identity_differs')
  try:
   if g[0]!='p':raise ValueError('Expected polygon prism')
   body=Polygon(g[1],g[4] if len(g)>4 and g[4] else None)
   if not body.is_valid:raise ValueError('Invalid polygon')
   delta=body.hausdorff_distance(S['polys'][eid]);area_delta=body.symmetric_difference(S['polys'][eid]).area
   if delta>D['criteria']['model_to_registered_pdf_tolerance_cm']:local.append('registered_source_XY_or_shape_differs')
   z_delta=abs(g[3]-S['top_m']);th_delta=abs((g[3]-g[2])*100-S['thickness_cm'][eid]);bottom=S['top_m']-S['thickness_cm'][eid]/100
   if z_delta>D['criteria']['absolute_z_tolerance_m']:local.append('source_top_Z_differs')
   if th_delta>D['criteria']['absolute_z_tolerance_m']*100:local.append('source_thickness_differs')
   if abs(g[2]-bottom)>D['criteria']['absolute_z_tolerance_m']:local.append('derived_bottom_Z_differs')
   fills_lift_pit=all(body.covers(pit) for pit in S['pits'])
  except Exception as exc:
   local.append('invalid_geometry:'+str(exc));delta=area_delta=z_delta=th_delta=None;fills_lift_pit=None;bottom=None
  if local:errors.extend(eid+': '+v for v in local)
  # PC1 contains the two openings at the same flat top: source shape conflict.
  conflicts=list(q['conflict_ids'])
  full_shape=not conflicts
  if eid==IDS[1] and fills_lift_pit is not True:
   local.append('PC1_geometry_changed_requires_new_source_shape_review');errors.append(eid+': PC1 geometry changed requires new source shape review')
  matched=not local and full_shape
  results.append({'id':eid,'status':'matched' if matched else 'conflict','model_geometry_match':matched,
   'geometry_sha256':_sha(g),'identity_sha256':_sha({k:e.get(k) for k in ('id','c','t','l')}),
   'checks':{'registered_plan_XY':delta is not None and delta<=D['criteria']['model_to_registered_pdf_tolerance_cm'],
    'plan_domain_shape':delta is not None and delta<=D['criteria']['model_to_registered_pdf_tolerance_cm'],
    'section_top_Z':z_delta is not None and z_delta<=D['criteria']['absolute_z_tolerance_m'],
    'section_thickness':th_delta is not None and th_delta<=D['criteria']['absolute_z_tolerance_m']*100,
    'full_body_section_shape':full_shape and not local},
   'measurements':{'xy_deviation_cm':delta,'symmetric_difference_cm2':area_delta,'top_Z_deviation_m':z_delta,'thickness_deviation_cm':th_delta,
    'section_top_m':S['top_m'],'literal_thickness_cm':S['thickness_cm'][eid],'derived_bottom_m':bottom,'flat_body_covers_both_lift_pits':fills_lift_pit},
   'evidence':{'source_pdf_sha256':D['source_pdf_sha256'],'data_sha256':DATA_SHA256,'plan_page':'STR:11 / S-7','section':q['section'],
    'source_shape':q['source_shape'],'source_plan_profile_indices':[3561,6285] if eid==IDS[0] else [6285],
    'model_to_registered_pdf_tolerance_cm':D['criteria']['model_to_registered_pdf_tolerance_cm'],'registration_max_residual_cm':S['proof']['max_registration_axis_residual_cm']},
   'conflict_ids':conflicts,'errors':local,'physical_or_site_acceptance':False})
 return {'schema':SCHEMA,'pass':not errors,'errors':errors,'results':results,'source_proof':S['proof'],
  'data_sha256':DATA_SHA256,'model_geometry_sha256':_sha([(eid,all_by[eid][0].get('g')) for eid in IDS if len(all_by.get(eid,[]))==1]),
  'matched_count':sum(v['model_geometry_match'] for v in results),'conflict_count':sum(v['status']=='conflict' for v in results),
  'conflicts':copy.deepcopy(D['conflicts']),'scope_ar':D['scope_ar'],'physical_or_site_acceptance':False}

def apply(M,verbose=False):
 """Add only this proof report; parent integrates it in the modelMatching register."""
 report=audit(M)
 M['raftModelAcceptance']=report
 if verbose:print('Raft model match:',report['matched_count'],'conflicts:',report['conflict_count'],'proof:',report['pass'])
 return report
