# -*- coding: utf-8 -*-
"""Independent original-PDF audit for FHC1 graphic identities, not devices."""
import copy, hashlib, json, math, sys
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pipeline'))
import reg
import fire_cabinet_source as FC
def _serial(v):
 if isinstance(v,fitz.Point):return [v.x,v.y]
 if isinstance(v,fitz.Rect):return list(v)
 if isinstance(v,fitz.Quad):return [_serial(v.ul),_serial(v.ur),_serial(v.lr),_serial(v.ll)]
 if isinstance(v,(list,tuple)):return [_serial(q)for q in v]
 return v
def _fingerprint(d):return {k:_serial(d.get(k))for k in ['layer','type','color','fill','width','closePath','even_odd','items','rect']}
def audit(M):
 # Rehydrate external audit inputs; geometry remains the live model.
 import sys as _audit_sys
 from pathlib import Path as _AuditPath
 _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
 from source_audit_sidecar import audit_model as _source_audit_model
 M = _source_audit_model(M)
 D=FC.data();checks=[];global_findings=[];rawchecks=[];E={e['id']:e for e in M['els']}
 if hashlib.sha256(Path(D['source_pdf']).read_bytes()).hexdigest()!=D['source_pdf_sha256']:global_findings.append('original_pdf_sha_changed')
 if len(E)!=len(M['els']):global_findings.append('duplicate_model_ids')
 doc=fitz.open(D['source_pdf']);fresh={}
 for pg,row in D['pages'].items():
  p=doc[int(pg)-1];dr=p.get_drawings();grid=[i for i,d in enumerate(dr)if d.get('layer')and('GRID'in d['layer'].upper()or'AXIS'in d['layer'].upper())and'IDEN'not in d['layer'].upper()]
  errs=[]
  if grid!=row['axis_indices']:errs.append('axis_exact_set_changed')
  for i,expected in {**row['axis_fingerprints'],**row['drawings']}.items():
   if int(i)>=len(dr)or _fingerprint(dr[int(i)])!=expected:errs.append('raw_primitive_changed:'+i)
  vv,hh=reg.grid_clusters(None,layers=None,minlen=50,drawings=[dr[i]for i in grid]);T=reg.register_free(vv,hh)
  if T!=row['registration']:errs.append('current_free_grid_registration_changed')
  fresh[int(pg)]=(dr,T);rawchecks.append({'page':f'MECH2:{pg}','pass':not errs,'errors':errs})
  global_findings.extend(errs)
 if set(D['instances'][i]['id']for i in range(len(D['instances'])))!=set(D['records'])or len(D['records'])!=12:global_findings.append('ledger_survivor_exact_set')
 if len(D['retirements'])!=23 or set(D['exact_retired_ids'])!={r['id']for r in D['retirements']}:global_findings.append('ledger_retirement_exact_set')
 for eid,row in D['records'].items():
  pair=D['source_pairs'][row['pair_key']];dr,T=fresh[pair['source_page']];ui,li=pair['u_drawing_index'],pair['leaf_drawing_index'];errors=[]
  if li!=ui+1 or ui not in [int(k)for k in D['pages'][str(pair['source_page'])]['drawings']]:errors.append('source_pair_identity')
  u,leaf=dr[ui],dr[li]
  if not(u.get('fill')and leaf.get('fill')and len(u['items'])==30 and len(leaf['items'])==6 and u.get('layer')==leaf.get('layer')==pair['layer'] and pair['layer'].endswith('FHC')):errors.append('source_pair_semantics')
  if any(it[0]!='l'for it in leaf['items']):errors.append('open_leaf_operator_changed')
  x0,y0,x1,y1=u['rect'];s,ox,oy=T['s'],T['ox'],T['oy'];bb=[x0*s+ox,-y1*s+oy,x1*s+ox,-y0*s+oy];xy=[(bb[0]+bb[2])/2,(bb[1]+bb[3])/2]
  e=E.get(eid);maxerr=None
  if not e:errors.append('missing_survivor')
  else:
   expected=FC._after(row)
   if M.get('meta',{}).get('owner_render_only'):
    # Display-only mode removes grades and cached source attributes. The raw
    # PDF checks below still validate the live identity and geometry.
    expected.pop('q',None)
    expected['a']={k:v for k,v in expected['a'].items() if not k.startswith('source_') or k in e.get('a',{})}
   if e!=expected:errors.append('survivor_exact_object_changed')
   g=e['g'];gb=[g[1]-g[4]/2,g[2]-g[3]/2,g[1]+g[4]/2,g[2]+g[3]/2] if g[5]==90 else[g[1]-g[3]/2,g[2]-g[4]/2,g[1]+g[3]/2,g[2]+g[4]/2]
   maxerr=max(abs(a-b)for a,b in zip(gb,bb))
   if maxerr>.2:errors.append('graphic_bbox_position')
   if any(e['a'].get(k)is not False for k in ['source_dimensions_verified','source_Z_verified','source_absolute_Z_verified','source_material_verified','source_mount_verified','source_ports_verified','source_contact_verified','source_physical_body_verified']):errors.append('unsafe_physical_acceptance')
  checks.append({'id':eid,'pass':not errors,'errors':errors,'source_kind':'architectural_FHC_recess_bbox_graphic_proxy','source_page':f"MECH2:{pair['source_page']}",'source_u_leaf_indices':[ui,li],'source_xy_cm':xy,'source_bbox_cm':bb,'max_bbox_error_cm':maxerr,'source_physical_body_verified':False})
 retirement=[{'id':r['id'],'pass':r['id']not in E,'reason':r['reason']}for r in D['retirements']]
 if {e['id']for e in M['els']if e.get('t')=='fhc'}!=set(D['records']):global_findings.append('model_fhc_exact_set')
 badrefs=[e['id']for e in M['els']if(e.get('a')or{}).get('to')in D['exact_retired_ids']or(e.get('a')or{}).get('from')in D['exact_retired_ids']]
 if badrefs:global_findings.append({'dangling_retired_derived_refs':badrefs})
 summary={'checked':len(checks),'retirements':len(retirement),'raw_pages':len(rawchecks),'findings':len(global_findings)+sum(not c['pass']for c in checks+retirement),'uncovered':0,'max_bbox_error_cm':max((c['max_bbox_error_cm']or 0 for c in checks),default=0),'scope':'graphic_identity_bbox_only; no physical dimensions/Z/material/ports/mount acceptance'}
 return {'checks':checks,'source_checks':rawchecks,'retirement_checks':retirement,'global_findings':global_findings,'uncovered':[],'summary':summary}
