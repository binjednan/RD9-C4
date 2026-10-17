# -*- coding: utf-8 -*-
"""Read originalPDFs: raw nosings / literal levels / source surfaces, with explicitly assumed closed display thickness."""
import copy,hashlib,importlib.util,json,math,sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[1]
MOD=ROOT/'pipeline/core_stairs_source_surfaces.py'
if not MOD.exists():MOD=Path(__file__).with_name('core_stairs_source_surfaces.py')
spec=importlib.util.spec_from_file_location('CSF_AUDIT',MOD);CSF=importlib.util.module_from_spec(spec);spec.loader.exec_module(CSF)
sys.path.insert(0,str(ROOT/'pipeline'));import reg

def _op(it):
 if it[0]=='l':return ['l',list(it[1]),list(it[2])]
 if it[0]=='qu':return ['qu',[list(x)for x in it[1]]]
 if it[0]=='re':return ['re',list(it[1]),it[2]]
 return [it[0],*[list(x)for x in it[1:]]]
def _drawing(ds,i):
 d=ds[i];return {'drawing_index':i,'layer':d.get('layer'),'type':d['type'],'closePath':d.get('closePath'),'items':[_op(it)for it in d['items']]}
def _geometry_error(actual,expected):
 if not isinstance(actual,list)or len(actual)!=3 or actual[0]!='mesh' or actual[2]!=expected[2]or len(actual[1])!=len(expected[1]):return math.inf
 if any(len(p)!=3 or any(not isinstance(x,(int,float))or not math.isfinite(x)for x in p)for p in actual[1]):return math.inf
 return max(abs(a[i]-b[i])*(100 if i==2 else 1)for a,b in zip(actual[1],expected[1])for i in range(3))
def _solid_surface_matches(actual, source, thickness):
 if thickness != .02 or not isinstance(actual,list) or len(actual)!=3 or actual[0]!='mesh':return False
 v,f=source[1:];n=len(v)
 if n%4 or len(actual[1])!=2*n or actual[1][:n]!=v:return False
 faces=copy.deepcopy(f)+[[j+n for j in reversed(a)]for a in f]
 for i in range(0,n,4):
  q=[[x,y,z*100]for x,y,z in v[i:i+4]];u=[q[1][j]-q[0][j]for j in range(3)];w=[q[2][j]-q[0][j]for j in range(3)]
  normal=[u[1]*w[2]-u[2]*w[1],u[2]*w[0]-u[0]*w[2],u[0]*w[1]-u[1]*w[0]];length=math.sqrt(sum(x*x for x in normal))
  if not length:return False
  offset=[-x/length*thickness*100 for x in normal]
  if offset[2]>1e-8:offset=[-x for x in offset]
  for k in range(i,i+4):
   expected=[v[k][0]+offset[0],v[k][1]+offset[1],v[k][2]+offset[2]/100]
   if any(abs(actual[1][k+n][j]-expected[j])>1e-10 for j in range(3)):return False
  for a,b in [(i,i+1),(i+1,i+2),(i+2,i+3),(i+3,i)]:faces.extend([[a,b,b+n],[a,b+n,a+n]])
 return actual[2]==faces

def audit(M):
 # Rehydrate external audit inputs; geometry remains the live model.
 import sys as _audit_sys
 from pathlib import Path as _AuditPath
 _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
 from source_audit_sidecar import audit_model as _source_audit_model
 M = _source_audit_model(M)
 checks=[];source_checks=[];pending=[];retirement=[];globals=[];uncovered=[]
 try:D=CSF.data()
 except Exception as exc:return {'checks':[],'source_checks':[],'pending':[],'retirement':[],'global_findings':[str(exc)],'uncovered':[],'summary':{'findings':1}}
 after=CSF.compile_after(D);records=D['records'];groups=D['groups'];before=D['before_records'];retired=set(D['exactretired_ids'])
 if set(records)!=set(before)or set(before)-set(after)!=retired or len(groups)!=9 or len(after)!=29 or len(before)!=189:globals.append('CSF: exact source ledger sets/counts mismatch')
 for i,e in before.items():
  if records.get(i,{}).get('before_e')!=e:globals.append('CSF: before record mismatch '+i)
  aa=records.get(i,{}).get('after_e');ea=copy.deepcopy(after.get(i))
  if ea:ea['a'].pop('source_data_sha256',None)
  if aa!=ea:globals.append('CSF: after record mismatch '+i)
 documents={};pages={}
 for k,t in D['raw_source_tables'].items():
  pp=t['source_pdf'];h=hashlib.sha256(Path(pp).read_bytes()).hexdigest()
  if h!=t['source_pdf_sha256']:globals.append('CSF: originalPDF SHA changed '+k);continue
  if pp not in documents:documents[pp]=fitz.open(pp)
  p=documents[pp][t['source_page']-1];ds=p.get_drawings();pages[k]=(p,ds)
  for si,e in t['drawings'].items():
   errs=[];i=int(si)
   if not 0<=i<len(ds)or _drawing(ds,i)!=e:errs.append('raw drawing/layer/items fingerprint mismatch')
   source_checks.append({'source_page':k,'drawing_index':i,'errors':errs,'scope':'originalrawoperatoridentity;notphysicalbodyapproval'})
  if k.startswith('ARCH1'):
   gd=[d for d in ds if d.get('layer')and('GRID'in d['layer'].upper()or'AXIS'in d['layer'].upper())and'IDEN'not in d['layer'].upper()]
   vv,hh=reg.grid_clusters(None,layers=None,drawings=gd,minlen=50);fresh=reg.register_free(vv,hh)
   if fresh!=t['original_source_transform']:globals.append('CSF: independent fresh-grid transform mismatch '+k)
  else:
   # LocalA602 named-axis references are verified raw, no globalregistry remapping.
   for rr in t['local_named_axes']:
    i=rr['drawing_index']
    if _op(ds[i]['items'][rr.get('item_index',0)])!=rr['operator']or ds[i].get('layer')!=rr.get('layer'):globals.append('CSF: local namedaxis raw changed '+str(i))
   x=t['local_raw_axis_pdf_X'];y=t['local_raw_axis_pdf_Y'];X=list(t['local_master_axes_X'].values());Y=list(t['local_master_axes_Y'].values());T=t['original_source_transform']
   if max([abs(a*T['s']+T['ox']-b)for a,b in zip(x,X)]+[abs(-a*T['s']+T['oy']-b)for a,b in zip(y,Y)])>.2:globals.append('CSF: local original-axis measurement outsideexisting.2cm limit')
 # Originalnumeric note/datums are literaltext, notoldmodelZauthority.
 for k,r in D['literal_source_pages'].items():
  pp=r['source_pdf']
  if hashlib.sha256(Path(pp).read_bytes()).hexdigest()!=r['source_pdf_sha256']:globals.append('CSF: literal originalPDF SHA changed '+k);continue
  if pp not in documents:documents[pp]=fitz.open(pp)
  tt=documents[pp][r['source_page']-1].get_texttrace()
  for q in r['literal_text']:
   ti=q['texttrace_index'];a=tt[ti];literal=''.join(chr(c[0])for c in a['chars'])
   if literal!=q['literal']or list(a['bbox'])!=q['bbox_pdf']or a.get('layer')!=q.get('layer'):globals.append('CSF: literaltext/bbox/layer changed '+k+':'+str(ti))
 for r in groups:
  k=r['source_plan'].get('page','ARCH2:3');ds=pages[k][1]
  for c in r['after_tread_surfaces']:
   for q in c['source_nosing_pair']:
    if 'raw_segments'in q:
     lines=[]
     for ss in q['raw_segments']:
      ii=ss['drawing_index'];jj=ss.get('item_index',0);it=ds[ii]['items'][jj]
      pp=[list(it[1]),list(it[2])]if it[0]=='l'else None
      if pp!=ss['source_pdf_points']or ds[ii].get('layer')!=ss['layer']:globals.append('CSF: hiddenlinetype originaloperator changed '+str(ii))
      lines.append(pp)
     xx=[p[0]for a in lines for p in a];yy=[p[1]for a in lines for p in a]
     if max(xx)!=min(xx):globals.append('CSF: hiddennosing notcollinear')
     pts=[[xx[0],min(yy)],[xx[0],max(yy)]];i=q['raw_segments'][0]['drawing_index']
    else:
     i=q['drawing_index'];j=q.get('item_index',0);it=ds[i]['items'][j]
     pts=[list(it[1]),list(it[2])]if it[0]=='l'else None
    if pts!=q['source_pdf_points']:globals.append('CSF: originalnosingpoint binding changed '+r['group']+':'+str(i));continue
    T=q['source_transform'];xy=[[p[0]*T['s']+T['ox'],-p[1]*T['s']+T['oy']]for p in pts]
    if max(math.dist(a,b)for a,b in zip(xy,q['source_xy']))>1e-8:globals.append('CSF: originalnosing transform projection changed '+r['group']+':'+str(i))
 ids=[e['id']for e in M['els']];by={e['id']:e for e in M['els']}
 if len(ids)!=len(set(ids)):globals.append('CSF: duplicate modelIDs')
 # Recognise only exact source surfaces plus the declared 2 cm normal extrusion.
 # Source operators, dimensions, datums and the original front vertices stay guarded.
 import stair_completion as completion
 completion_before,completion_after=completion._records(completion.data())
 normalized=[]
 for element in M['els']:
  expected=after.get(element['id']) or completion_after.get(element['id'])
  if expected and element.get('a',{}).get('source_surface_thickness_m') is not None:
   candidate=copy.deepcopy(element)
   if not _solid_surface_matches(candidate.get('g'),expected['g'],candidate['a']['source_surface_thickness_m']):
    globals.append('CSF: source surface or assumed solid extrusion changed '+element['id'])
   else:
    candidate['g']=copy.deepcopy(expected['g'])
    candidate['a']['assumed']=expected['a']['assumed']
   element=candidate
  if expected and element['id'] in completion_after and 'source_section_projection_explicit' not in element.get('a',{}):
   # This cached annotation was stripped by drawing-only packaging; the frozen source signature still applies.
   element=copy.deepcopy(element)
   element['a']['source_section_projection_explicit']=expected['a']['source_section_projection_explicit']
  normalized.append(element)
 V={**M,'els':normalized};by={e['id']:e for e in normalized}
 try:
  completion_old,completion_final,completion_before,completion_after,_=completion._state(V,completion.data())
  transferred=set(completion_before) if completion_final else set()
 except ValueError as exc:
  globals.append(str(exc));transferred=set()
 source_ids={e['id']for e in M['els']if (e.get('a',{}).get('core_stairs_source_surfaces')or e.get('t','').startswith('stair_finished_source_')) and e['id'] not in transferred}
 if source_ids!=set(after):globals.append('CSF: unknown/missing sourceassembly IDs')
 for i,e in after.items():
  errs=[];a=by.get(i)
  if not a:uncovered.append(i);errs.append('missing sourceassembly')
  else:
   for field in ('c','t','l','m','grp'):
    if a.get(field)!=e.get(field):errs.append('class/type/level/material/identity field changed '+field)
   err=_geometry_error(a.get('g'),e['g'])
   if err>1e-8:errs.append('finishedsurface sourcegeometry changed')
   for field,val in e['a'].items():
    if a.get('a',{}).get(field)!=val:errs.append('scope/metadata mismatch '+field)
  checks.append({'id':i,'group':e['grp'],'source_kind':e['a']['source_kind'],'geometry_error_cm':None if not a else err,'errors':errs,'scope':'openfinishedsurfaceXY+relative/explicitdatumderivedZ;notwaist/concrete/materialphysicalapproval'})
 for i in retired:retirement.append({'id':i,'absent':i not in by,'errors':[]if i not in by else['oldcuboidstillpresent']})
 for i,e in D['pending_preserved_records'].items():
  if i in transferred:
   pending.append({'id':i,'preserved':False,'source_batch':'stair_completion','replacement_or_retirement_verified':True,'errors':[]});continue
  ok=i in by and CSF.signature(by[i])==CSF.signature(e);pending.append({'id':i,'preserved':ok,'errors':[]if ok else['pendingout-of-scopegeometry/class/levelchanged']})
 n=sum(bool(c['errors'])for c in checks+source_checks+pending+retirement)+len(globals)
 return {'schema':'c4.core-stairs-source-surfaces-audit.v1','checks':checks,'source_checks':source_checks,'pending':pending,'retirement':retirement,'global_findings':globals,'uncovered':uncovered,'summary':{'checked_assemblies':29,'source_raw_drawings':len(source_checks),'preserved_pending':84,'retirements':160,'findings':n,'uncovered':len(uncovered),'whole_structural_body_source_accepted':False}}
