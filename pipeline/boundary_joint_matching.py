# coding:utf-8
"""Literal 2cm CB1 joint cuts centred on the source-drawn STR32 joint location.

Only six coping end faces change. All other vertices, levels and elements remain
exactly intact. The STR31 leader identifies the opposing C* faces; the location
is the STR32 gap midpoint, explicitly derived rather than a dimensioned axis.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

import fitz
from shapely.geometry import Point,Polygon,box

ROOT=Path(__file__).resolve().parents[1]
DATA_PATH=ROOT/'pipeline/data/boundary_joint_matching.json'
DATA_SHA256='2ae2a9613554c90592a2377087bee3450282df2bff08662b0ec0a286decbd617'
IDS=tuple('S.beam-G-BND%04d'%i for i in range(1,7))
SCHEMA='c4.boundary-joint-matching.v1'

def _sha(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def _bsha(b):return hashlib.sha256(b).hexdigest()
def _data():
 b=DATA_PATH.read_bytes()
 if _bsha(b)!=DATA_SHA256:raise ValueError('Boundary joint data SHA differs')
 return json.loads(b)
def _base():
 sys.path.insert(0,str(ROOT/'tools'))
 import check_boundary_source as C
 return C

def _gap(rects,axis):
 a,b=rects
 return fitz.Rect(a.x1,max(a.y0,b.y0),b.x0,min(a.y1,b.y1)) if axis==0 else fitz.Rect(max(a.x0,b.x0),a.y1,min(a.x1,b.x1),b.y0)

def _source(D,verify_images=True):
 C=_base()
 if _bsha((ROOT/'tools/check_boundary_source.py').read_bytes())!=D['base_raw_gate_sha256']:raise ValueError('Raw boundary reconstruction changed; review required')
 if _bsha((ROOT/'pipeline/data/boundary_source_remaining.json').read_bytes())!=D['base_ledger_sha256']:raise ValueError('Base boundary ledger changed; review required')
 if _bsha(C.STR.read_bytes())!=D['source_pdf_sha256'] or _bsha(C.ARCH.read_bytes())!=D['arch_pdf_sha256']:raise ValueError('Source PDF SHA differs')
 raw=C._sources(C._revision(C.STR),C._revision(C.ARCH))
 doc=fitz.open(C.STR);pages={31:doc[30],32:doc[31]};ds={31:pages[31].get_drawings(),32:raw['drawings']};traces={p:pg.get_texttrace() for p,pg in pages.items()}
 refs=[]
 for q in D['raw_texts']:
  t=traces[q['page']][q['texttrace_index']]
  if C._text(t)!=q['text'] or list(t['bbox'])!=q['bbox'] or q['text']!='2CM EXP JOINT':raise ValueError('Joint literal differs')
  refs.append('text:%d:%d'%(q['page'],q['texttrace_index']))
 for q in D['raw_drawings']:
  d=ds[q['page']][q['drawing_index']]
  if C._raw(d)!=(q['raw_points'],q['raw_items']) or d.get('layer')!=q['layer'] or list(d['rect'])!=q['bbox']:raise ValueError('Joint raw reference differs')
  refs.append('drawing:%d:%d'%(q['page'],q['drawing_index']))
 if raw['transform']!=D['source_transform']:raise ValueError('Current corner/grid registration differs')
 origin31=ds[31][345]['rect'].tl;origin32=ds[32][342]['rect'].tl
 translation=[origin32.x-origin31.x,origin32.y-origin31.y]
 expected={};jointproof=[];t=raw['transform']
 # All 41 column shapes from independent original-PDF reconstruction are used
 # to verify that each transferred face has a unique nearest same column.
 pool=[(int(q['required_indices'].copy().pop()),q['pdf_poly']) for eid,q in raw['expected'].items() if q['category']=='S.col']
 for j in D['joints']:
  rect31=[ds[31][i]['rect'] for i in j['columns_STR31']];rect32=[ds[32][i]['rect'] for i in j['columns_STR32']]
  g31=_gap(rect31,j['axis']);g32=_gap(rect32,j['axis'])
  if not g31.is_valid or not g32.is_valid:raise ValueError('Opposing column faces do not bound a joint')
  if list(g32)!=j['source_gap_bbox_pdf']:raise ValueError('STR32 source joint faces differ')
  leader=ds[31][j['leader_arrow_STR31']]
  tip=leader['items'][0][2]
  tip_distance=box(*g31).distance(Point(tip.x,tip.y))
  if tip_distance>1e-4:raise ValueError('2cm leader no longer ends at the identified joint')
  columns=[]
  for i31,i32 in zip(j['columns_STR31'],j['columns_STR32']):
   poly=Polygon([[x+translation[0],y+translation[1]] for x,y in C._raw(ds[31][i31])[0]])
   ranking=sorted((poly.hausdorff_distance(p),i) for i,p in pool)
   if ranking[0][1]!=i32 or ranking[0][0]==ranking[1][0]:raise ValueError('Cross-sheet column association is not unique')
   columns.append({'STR31':i31,'STR32':i32,'matched_face_deviation_cm':ranking[0][0]*t['s'],'next_column_deviation_cm':ranking[1][0]*t['s']})
  centre_raw=[(g32.x0+g32.x1)/2,(g32.y0+g32.y1)/2];world=C._tr([centre_raw],t)[0];centre=world[j['axis']]
  if world!=j['source_center_world_cm']:raise ValueError('Derived source joint centre changed')
  old_c31=[(g31.x0+g31.x1)/2+translation[0],(g31.y0+g31.y1)/2+translation[1]]
  jproof={'face':j['face'],'ids':j['ids'],'source_raw_center_pdf':centre_raw,'source_center_world_cm':world,
   'literal_gap_cm':2.,'graphic_gap_cm':(g32.width if j['axis']==0 else g32.height)*t['s'],
   'cut_axis_coordinates_cm':[centre-1,centre+1],'anchor_kind':'derived midpoint of STR32 opposing source column faces',
   'STR31_leader_tip_distance_to_joint_pdf_pt':tip_distance,'cross_sheet_column_registration':columns,
   'cross_sheet_center_offset_cm':[(old_c31[0]-centre_raw[0])*t['s'],-(old_c31[1]-centre_raw[1])*t['s']],
   'cross_sheet_offset_axes':'world X right/Y up; positive means transferred STR31 centre minus STR32 centre','source_grid_axis_dimension_for_center':False}
  for eid in j['ids']:
   q=D['records'][eid];source_poly=raw['expected'][eid]['world_poly'];coords=[list(p) for p in source_poly.exterior.coords[:-1]];axis=q['axis'];side=q['end']
   extreme=(max if side=='max' else min)(p[axis] for p in coords);target=centre+(-1 if side=='max' else 1)
   # End face of a source-derived coping band, not its entire long side.
   n=0
   for p in coords:
    if p[axis]==extreme:p[axis]=target;n+=1
   if n<2:raise ValueError('Source end face unavailable '+eid)
   after=Polygon(coords)
   if not after.is_valid:raise ValueError('Corrected source cut invalid '+eid)
   before=q['before_g'];declared=q['after_g'];changed=copy.deepcopy(before)
   for k in q['moved_vertex_indices']:
    if before[1][k][axis]!=q['before_end_cm']:raise ValueError('Declared moved vertex is not on the end face')
    changed[1][k][axis]=round(target,10)
   if changed!=declared or before[2:]!=declared[2:]:raise ValueError('Correction changes something other than controlled end vertices')
   if _sha(before)!=q['before_geometry_sha256'] or _sha(declared)!=q['after_geometry_sha256']:raise ValueError('Declared geometry SHA differs')
   bp=Polygon(before[1],before[4] if len(before)>4 else None)
   if bp.hausdorff_distance(source_poly)>.0001:raise ValueError('Before geometry is not the raw source profile '+eid)
   expected[eid]={'poly':after,'raw_before_poly':source_poly,'target_cut_cm':target,'z':raw['expected'][eid]['z'],'raw_source_deviation_cm':bp.hausdorff_distance(source_poly),'source_head_indices':sorted(raw['expected'][eid]['head_indices'])}
  jointproof.append(jproof)
 images=[]
 if verify_images:
  for q in D['renderings']:
   path=(ROOT/q['path']).resolve();png=pages[q['page']].get_pixmap(matrix=fitz.Matrix(q['scale'],q['scale']),clip=fitz.Rect(q['clip']),annots=q['annots']).tobytes('png')
   valid=path.is_file() and _bsha(path.read_bytes())==q['sha256'] and _bsha(png)==q['sha256']
   if not valid:raise ValueError('Original joint evidence rendering differs')
   images.append({'path':q['path'],'sha256':q['sha256'],'pass':True})
 doc.close()
 return {'expected':expected,'proof':{'source_pdf_sha256':D['source_pdf_sha256'],'arch_pdf_sha256':D['arch_pdf_sha256'],'raw_source_checks':refs,'transform':t,'reference_registration':raw['reference_registration'],'STR31_to_STR32_translation_pdf_pt':translation,'joints':jointproof,'renderings':images,'center_derivation_disclosed':True,'nominal_CB1_width_cm':20.,'literal_CB1_depth_cm':30.,'literal_top_Z_m':3.0,'scope_ar':D['scope_ar']}}

def _index(M):
 out={}
 for e in M['els']:out.setdefault(e.get('id'),[]).append(e)
 return out

def _audit(M,D,S):
 errors=[];results=[];by=_index(M);polys={}
 for eid in IDS:
  q=D['records'][eid];es=by.get(eid,[])
  if len(es)!=1:errors.append(eid+': missing or duplicate identity');results.append({'id':eid,'status':'conflict','model_geometry_match':False,'errors':['missing_or_duplicate_identity']});continue
  e=es[0];local=[];g=e.get('g');expected=S['expected'][eid]
  if (e.get('c'),e.get('t'),e.get('l'))!=(q['category'],q['type'],q['level']):local.append('controlled_identity_differs')
  if g!=q['after_g']:local.append('geometry_differs_from_literal_joint_correction')
  try:
   if g[0]!='p':raise ValueError('Expected prism')
   p=Polygon(g[1],g[4] if len(g)>4 and g[4] else None);polys[eid]=p
   delta=p.hausdorff_distance(expected['poly']);z_error=max(abs(a-b) for a,b in zip(g[2:4],expected['z']))
   if not p.is_valid or delta>.0001:local.append('independent_literal_source_geometry_differs')
   if z_error>1e-8:local.append('literal_Z_or_depth_differs')
   width=(p.bounds[3]-p.bounds[1]) if q['axis']==0 else (p.bounds[2]-p.bounds[0])
  except Exception as exc:delta=z_error=width=None;local.append('invalid_geometry:'+str(exc))
  errors.extend(eid+': '+x for x in local)
  results.append({'id':eid,'status':'matched' if not local else 'conflict','model_geometry_match':not local,'geometry_sha256':_sha(g),
   'identity_sha256':_sha({k:e.get(k) for k in ('id','c','t','l')}),'checks':{'source_location_and_shape':delta is not None and delta<=.0001,'literal_depth_and_Z':z_error is not None and z_error<=1e-8,'only_source_joint_end_vertices_changed':g==q['after_g'],'literal_joint_width':False},
   'measurements':{'source_XY_deviation_cm':delta,'z_deviation_m':z_error,'nominal_section_width_cm':20.,'drawn_section_width_cm':width,'nominal_width_difference_cm':None if width is None else width-20,'joint_end_displacement_cm':q['displacement_cm']},
   'evidence':{'source_pdf_sha256':D['source_pdf_sha256'],'arch_pdf_sha256':D['arch_pdf_sha256'],'data_sha256':DATA_SHA256,'source_pages':['STR:31 / S-26','STR:32 / S-27'],'anchor_kind':'STR32 source joint face midpoint; explicitly derived','source_head_indices':expected['source_head_indices']},'conflict_ids':[],'errors':local,'physical_or_site_acceptance':False})
 jointchecks=[]
 for j in D['joints']:
  if any(eid not in polys for eid in j['ids']):continue
  a,b=(polys[eid] for eid in j['ids']);gap=a.distance(b);valid=abs(gap-2)<1e-8
  jointchecks.append({'face':j['face'],'ids':j['ids'],'gap_cm':gap,'literal_gap_cm':2.,'pass':valid})
  for row in results:
   if row['id'] in j['ids']:
    row['checks']['literal_joint_width']=valid
    if not valid:row.update(status='conflict',model_geometry_match=False);row['errors'].append('literal_joint_width_differs')
  if not valid:errors.append(j['face']+': literal joint width differs')
 return {'schema':SCHEMA,'pass':not errors,'errors':errors,'results':results,'matched_count':sum(r['model_geometry_match'] for r in results),'conflict_count':sum(not r['model_geometry_match'] for r in results),'joint_checks':jointchecks,'source_proof':S['proof'],'data_sha256':DATA_SHA256,'model_geometry_sha256':_sha([(eid,by[eid][0]['g']) for eid in IDS if len(by.get(eid,[]))==1]),'conflicts':[],'physical_or_site_acceptance':False,
  'scope_ar':'مطابقة الرسم المسجل بعد تطبيق عرض الفاصل الحرفي2سم حول مركزه المشتق. عرض القطاع الرسومي وفَرْقه عن20سم الاسمية ظاهران؛ لا تغيير للجوانب أو الأعمدة أو المناسيب ولا ادعاء دقة تنفيذ.'}

def audit(M,verify_images=True):
 try:
  D=_data();S=_source(D,verify_images)
  if M.get('meta',{}).get('owner_render_only'):
   by=_index(M);substitutions={}
   for eid,q in D['records'].items():
    originals=by.get(eid,[]);alternates=by.get(eid+'-ALT',[])
    if len(originals)!=1 or originals[0]['g']!=q['before_g']:raise ValueError('Original drawn boundary changed: '+eid)
    if len(alternates)!=1 or not alternates[0].get('a',{}).get('alt'):raise ValueError('Literal source alternative missing: '+eid)
    e=copy.deepcopy(alternates[0]);e['id']=eid;substitutions[eid]=e
   result=_audit({**M,'els':[substitutions.get(e['id'],e) for e in M['els']]},D,S)
   result['scope_ar']='الرسم الأصلي محفوظ؛ الشكل البديل وحده يمثل عرض النص 2 سم حول مركز مشتق. لا تصحيح للشكل الأصلي ولا اختيار مصدر.'
   result['original_drawn_shapes_preserved']=True
   return result
  return _audit(M,D,S)
 except Exception as exc:return {'schema':SCHEMA,'pass':False,'errors':[str(exc)],'results':[],'matched_count':0,'conflict_count':0,'conflicts':[]}

def apply(M,verbose=False):
 D=_data();S=_source(D);by=_index(M)
 for eid,q in D['records'].items():
  if len(by.get(eid,[]))!=1:raise ValueError('Controlled identity unavailable '+eid)
  e=by[eid][0]
  if (e.get('c'),e.get('t'),e.get('l'))!=(q['category'],q['type'],q['level']) or e.get('g') not in (q['before_g'],q['after_g']):raise ValueError('Controlled before/after guard differs '+eid)
 other_before=_sha([e for e in M['els'] if e.get('id') not in IDS]);owned_before={eid:copy.deepcopy(by[eid][0]) for eid in IDS};changed=[]
 for eid,q in D['records'].items():
  e=by[eid][0]
  if e['g']!=q['after_g']:changed.append(eid);e['g']=copy.deepcopy(q['after_g'])
 for eid,e in owned_before.items():
  e['g']=by[eid][0]['g']
  if e!=by[eid][0]:raise AssertionError('Owned non-geometry fields changed')
 other_after=_sha([e for e in M['els'] if e.get('id') not in IDS])
 if other_before!=other_after:raise AssertionError('Other element changed')
 report=_audit(M,D,S)
 if not report['pass']:raise AssertionError('Corrected source audit failed '+str(report['errors']))
 report['application']={'changed_this_run':changed,'other_elements_unchanged':True,'other_elements_sha256':other_after,'owned_non_geometry_fields_unchanged':True,'only_declared_joint_end_vertices_changed':True,'all_Z_unchanged':True}
 M['boundaryJointMatching']=report
 if verbose:print('CB1 literal joints:',len(changed),'bodies changed;',report['matched_count'],'model matches')
 return report

def legacy_projection(M):
 """Read-only projection for the original raw-profile gate; keep its .2cm scope.

Call audit on the actual corrected model in addition to this projection. It only
restores the six old g arrays, because the older gate correctly tests raw graphic
joint gaps rather than the literal2cm correction. No original model mutation.
"""
 D=_data();by=_index(M);p=dict(M);p['els']=[]
 for e in M['els']:
  eid=e.get('id')
  if eid in IDS:
   if len(by[eid])!=1 or e.get('g') not in (D['records'][eid]['before_g'],D['records'][eid]['after_g']):raise ValueError('Cannot project unrecognized corrected body '+eid)
   q=copy.deepcopy(e);q['g']=copy.deepcopy(D['records'][eid]['before_g']);p['els'].append(q)
  else:p['els'].append(e)
 return p
