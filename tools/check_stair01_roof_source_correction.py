"""Original-PDF multi-page gate for a disproved flight; caps stay procedural."""
import collections,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA_PATH=ROOT/'pipeline/data/stair01_roof_source_correction.json'
FROZEN_SHA='744205d5d6e609c857282781f399d4fa661cebf9efa7ad10fedc22602c6336c3'
SCHEMA='c4.stair01-roof-source-correction.v1'
CAPS={'S.slab-T-0008','S.slab-T-0009'}

def _items(v):
 import fitz
 if isinstance(v,fitz.Point):return[v.x,v.y]
 if isinstance(v,fitz.Quad):return[_items(q)for q in v]
 if isinstance(v,fitz.Rect):return list(v)
 if isinstance(v,(tuple,list)):return[_items(q)for q in v]
 return v

def _sha(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def _walk(v):
 if isinstance(v,dict):
  yield v
  for q in v.values():yield from _walk(q)
 elif isinstance(v,list):
  for q in v:yield from _walk(q)

def ledger_errors(D):
 errors=[]
 if D.get('schema')!=SCHEMA or set(D.get('records',{}))!=CAPS:errors.append('frozen_schema_cap_set')
 rr=D.get('retirement_records',{});expected={f'S.stair-R-{i:04d}'for i in range(148,169)}|{f'A.rail-R-X{i:04d}'for i in range(2037,2102)}|{'S.slab-T-0008-b'}
 if set(rr)!=expected:errors.append('exact87_retirement_set')
 for eid,row in D.get('records',{}).items():
  for q in row.get('known_exact_input_geometries',[]):
   if q.get('geometry_sha256')!=_sha(q.get('g')):errors.append('known_geometry_fingerprint')
  for q in [row['restored_before_TRO_g'],row['final_after_TRO_v2_g']]:
   z=q[2:4]if q[0]=='p'else q[5:7]
   if z!=[26.4,26.65]:errors.append('preserved_procedural_Z')
 return sorted(set(errors))

def source_facts(D):
 import fitz
 sys.path.insert(0,str(ROOT/'pipeline'));import lib,reg
 errors=[];facts=[]
 for name,row in D['source_pages'].items():
  key,pn=name.split(':');pn=int(pn);pdf=Path(row['source_pdf']);b=pdf.read_bytes()
  if hashlib.sha256(b).hexdigest()!=row['source_pdf_sha256']:errors.append(name+':PDF_SHA')
  with fitz.open(pdf)as doc:
   p=doc[pn-1];ds=p.get_drawings();tt=p.get_texttrace();ops={};texts={}
   for q in _walk(row):
    if'drawing_index'in q and'items'in q:ops[q['drawing_index']]=q
    if'texttrace_index'in q and'literal'in q:texts[q['texttrace_index']]=q
   for i,q in ops.items():
    try:d=ds[i]
    except Exception:errors.append(name+':raw_index');continue
    if d.get('layer')!=q['layer']or _items(d['items'])!=q['items']or _items(lib.flat_path(d))!=q['pdf_points']:errors.append(name+':original_operator')
   for i,q in texts.items():
    try:t=tt[i]
    except Exception:errors.append(name+':text_index');continue
    chars=[{'char_index':j,'unicode':c[0],'char':chr(c[0]),'origin_pdf':_items(c[2]),'bbox_pdf':_items(c[3])}for j,c in enumerate(t['chars'])]
    if t.get('layer')!=q['layer']or ''.join(chr(c[0])for c in t['chars'])!=q['literal']or chars!=q['chars']:errors.append(name+':original_text_chars')
   if'transform'in row:
    grid=[d for d in ds if d.get('layer')and('GRID'in d['layer'].upper()or'AXIS'in d['layer'].upper())and'IDEN'not in d['layer'].upper()];v,h=reg.grid_clusters(None,layers=None,drawings=grid,minlen=50);T=reg.register_free(v,h)
    if T!=row['transform']or v!=row['grid_pdf_v']or h!=row['grid_pdf_h']:errors.append(name+':fresh_original_grid')
   # Independent decisive anatomical/text predicates, not old model XY as source.
   def literal(i):return ''.join(chr(c[0])for c in tt[i]['chars'])
   if name=='ARCH1:8'and(literal(119)!='DN'or literal(302)!='F.F.L. +23.25'):errors.append('A105_last_roof_landing_binding')
   if name=='ARCH1:9':
    if literal(171)!='F.F.L. +26.85'or literal(172)!='TOP ROOF':errors.append('A106_cover_binding')
    B=(85,730,700,1090);found=[]
    from shapely.geometry import box
    for i,d in enumerate(ds):
     if not d.get('layer')or'stair'not in d['layer'].lower():continue
     pts=[(x*T['s']+T['ox'],T['oy']-y*T['s'])for pl in lib.flat_path(d)for x,y in pl]
     if pts and box(min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts)).intersects(box(*B)):found.append(i)
    if found:errors.append('A106_cover_region_stair_glyph_changed')
   if name=='ARCH2:2':
    if len(ds[21708]['items'])!=1 or ds[21708]['items'][0][0]!='qu'or literal(254)!='310'or literal(248)!='168':errors.append('A601_continuous_cover_last_step_binding')
   if name=='STR:24'and literal(24)!='CL. +26.65':errors.append('STR24_cover_CL_binding')
   facts.append({'source_page':name,'raw_operator_checks':len(ops),'texttrace_checks':len(texts),'whole_body_Z_material_accepted':False})
 return{'errors':sorted(set(errors)),'facts':facts}

def audit(M):
 # Rehydrate external audit inputs; geometry remains the live model.
 import sys as _audit_sys
 from pathlib import Path as _AuditPath
 _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
 from source_audit_sidecar import audit_model as _source_audit_model
 M = _source_audit_model(M)
 B=DATA_PATH.read_bytes();D=json.loads(B);gf=[];checks=[];retirement=[]
 if hashlib.sha256(B).hexdigest()!=FROZEN_SHA:gf.append({'kind':'frozen_data_fingerprint'})
 gf.extend({'kind':q}for q in ledger_errors(D))
 try:raw=source_facts(D);gf.extend({'kind':q}for q in raw['errors'])
 except Exception as ex:raw={'facts':[]};gf.append({'kind':'original_raw_review','reason':str(ex)})
 es=M['els'];cnt=collections.Counter(e['id']for e in es);by={e['id']:e for e in es}
 for e in es:
  if e.get('grp')=='STAIR1-R'or(e.get('grp')or'').startswith('rail-STAIR1-R'):gf.append({'kind':'unsupported_flight_or_derived_rail_remaining','id':e['id']})
  if(e.get('a')or{}).get('stair01_roof_source_correction')and e['id']not in CAPS:gf.append({'kind':'unexpected_cap_source_claim','id':e['id']})
 for eid,row in D['retirement_records'].items():retirement.append({'id':eid,'pass':eid not in by,'errors':[]if eid not in by else['source_disproved_element_remaining'],'scope':row['scope'],'source_installation_quantity_acceptance':False})
 for eid,row in D['records'].items():
  e=by.get(eid);errors=[]
  if e is None:errors.append('preserved_cap_missing')
  else:
   if cnt[eid]!=1 or(e['c'],e['t'],e['l'],e.get('m'),e.get('grp'))!=(row['c'],row['t'],row['l'],row['m'],None):errors.append('preserved_identity')
   if e['g']!=row['final_after_TRO_v2_g']:errors.append('final_domain_spelling')
   a=e.get('a')or{}
   if a.get('stair01_roof_source_correction')is not True or a.get('stair01_roof_source_data_sha256')!=FROZEN_SHA or'opening_note'in a:errors.append('correction_metadata_or_false_HEAD_claim')
   for k in ['source_outer_XY_verified','source_absolute_Z_verified','source_Z_verified','source_material_verified','source_physical_body_verified','source_dimensions_verified']:
    if a.get(k)is not False:errors.append('unsafe_body_Z_material_promotion')
  checks.append({'id':eid,'pass':not errors,'errors':errors,'scope':'undo_known_procedural_cut_only','body_source_checked':False,'absolute_Z_material_outer_source_accepted':False})
 failures=len(gf)+sum(not q['pass']for q in checks+retirement)
 return{'checks':checks,'retirement_checks':retirement,'source_facts':raw['facts'],'global_findings':gf,'summary':{'checked':len(checks),'retirement_checked':len(retirement),'retired_exact_inventory':87,'findings':failures,'uncovered':max(0,2-len(checks))+max(0,87-len(retirement)),'full_cap_source_checked':0,'source_scope':'source_disproved_extra_flight_retirement_and_undo_causal_HEAD_cut_only'}}
