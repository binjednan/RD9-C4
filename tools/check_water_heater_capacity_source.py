"""Independent partial property gate for82 drawn heater capacity glyphs.

This accepts original50/80 litre numerals and associated1.2/1.5kW legend data.
It does not accept physical body dimensions, XY mounting, Z, material or ports.
The data and original PDF are checked before property/preservation checks.
"""
from pathlib import Path
import collections,hashlib,json,math,sys
import fitz
from shapely.geometry import LineString
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'pipeline'));import lib
LOCAL_DATA_PATH=Path(__file__).with_name('data')/'water_heater_capacity_source.json'
DATA_PATH=LOCAL_DATA_PATH if LOCAL_DATA_PATH.is_file()else ROOT/'pipeline'/'data'/'water_heater_capacity_source.json'
FROZEN_SHA='f17f3088b2c7441b5455088dfa55ed6ad0a1da2a57a20f133e193636b18d12b8'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def items(d):
 out=[]
 for it in d['items']:
  pp=[]
  for q in it[1:]:
   if hasattr(q,'x'):pp.append([q.x,q.y])
   elif hasattr(q,'ul'):pp.append([[v.x,v.y]for v in[q.ul,q.ur,q.lr,q.ll]])
   elif hasattr(q,'x0'):pp.append(list(q))
   else:pp.append(q)
  out.append([it[0],pp])
 return out
def normalized(pp):
 xs=[p[0]for p in pp];ys=[p[1]for p in pp];cx=(min(xs)+max(xs))/2;cy=(min(ys)+max(ys))/2;s=max(max(xs)-min(xs),max(ys)-min(ys))
 return[[(x-cx)/s,(y-cy)/s]for x,y in pp]
def glyph_distance(pp,kp):
 a=LineString(normalized(pp));b=normalized(kp);result=[]
 for rotation in range(4):
  br=b
  for _ in range(rotation):br=[[-y,x]for x,y in br]
  result.append(a.hausdorff_distance(LineString(br)))
 return min(result)
def verify_source(D):
 errors=[];sourcechecks=[];docs={}
 if D.get('schema')!='c4.water-heater-capacity-source.v1':errors.append('schema')
 if len(D.get('records',{}))!=82 or len(D.get('raw_glyph_sources',{}))!=34:errors.append('exact_source_denominator')
 for name in ['source_pdf','BOQ_pdf']:
  if sha(D[name]['path'])!=D[name]['sha256']:errors.append(name+'_PDF_fingerprint')
  docs[name]=fitz.open(D[name]['path'])
 dd={n:docs['source_pdf'][n-1].get_drawings()for n in[19,20,21,22]}
 def checkdrawing(n,q):
  d=dd[n][q['drawing_index']]
  if d.get('layer')!=q['layer']or items(d)!=q['items']or [[list(p)for p in pl]for pl in lib.flat_path(d,10)]!=q['polys']:raise ValueError('raw_drawing_binding')
  return d
 keyglyph={}
 try:
  for cap,qs in D['legend_capacity_primitives'].items():
   for q in qs:checkdrawing(20,q)
   keyglyph[int(cap)]=qs[0]['polys'][0]
  for key,q in D['raw_glyph_sources'].items():
   n=int(q['source'].split(':')[1]);local=[]
   try:
    sources={r['drawing_index']:r for r in q['source_drawings']}
    for r in sources.values():checkdrawing(n,r)
    numbers=q['capacity_primitives'];assert len(numbers)==3 and len(set(numbers))==3
    first,zero,L=[dd[n][di]for di in numbers]; pp=[lib.flat_path(x,10)[0]for x in[first,zero,L]]
    assert all(x.get('layer')=='WATER'and all(it[0]=='l'for it in x['items'])for x in[first,zero,L])
    closed=[math.dist(p[0],p[-1])<.01 for p in pp]
    cap=80 if len(first['items'])==28 and closed[0]else 50 if len(first['items'])==16 and not closed[0]else None
    assert cap in(50,80)and cap==q['capacity_l']and len(zero['items'])==16 and closed[1]and len(L['items'])==2 and not closed[2]
    gd=glyph_distance(pp[0],keyglyph[cap]);other=glyph_distance(pp[0],keyglyph[130-cap])
    # Glyph recognition quantization only. This is not component XY tolerance.
    assert gd<.05 and other>3*gd
    p0,p1=q['body_bbox_pdf'][:2],q['body_bbox_pdf'][2:];raw=[]
    for di,pi in q['body_primitives']:raw.extend(lib.flat_path(dd[n][di],10)[pi])
    bb=[min(p[0]for p in raw),min(p[1]for p in raw),max(p[0]for p in raw),max(p[1]for p in raw)]
    assert bb==q['body_bbox_pdf']
    T=q['registration'];xy=[(bb[0]+bb[2])/2*T['s']+T['ox'],-(bb[1]+bb[3])/2*T['s']+T['oy']]
    w=(bb[2]-bb[0])*T['s'];h=(bb[3]-bb[1])*T['s'];expected=[round(xy[0],1),round(xy[1],1),round(max(w,h),1),round(min(w,h),1),0 if w>=h else 90]
    assert expected==q['emitter_xy_geometry']
   except(Exception,)as e:local.append(str(e)or type(e).__name__)
   sourcechecks.append({'id':key,'source':q['source'],'capacity_l':q['capacity_l'],'glyph_recognition_scope':'literal_vector_character_not_body_dimension','physical_dimensions_Z_material_mount_ports_accepted':False,'pass':not local,'errors':local})
  for name,records in [('source_pdf',[D['legend_literal']]),('BOQ_pdf',D['BOQ_capacity_literals'])]:
   for q in records:
    t=docs[name][q['page']-1].get_texttrace()[q['texttrace_index']];chars=[[c[0],list(c[2]),list(c[3])]for c in t['chars']]
    assert chars==q['chars']and ''.join(chr(c[0])for c in t['chars'])==q['text']and list(t['bbox'])==q['bbox_pdf']
  counts=collections.Counter(q['source_capacity_l']for q in D['records'].values());assert counts=={50:21,80:61}
  for eid,r in D['records'].items():assert r['id']==eid and r['source_capacity_l']==D['raw_glyph_sources'][r['source_key']]['capacity_l']and r['after_type']=='heater'+str(r['source_capacity_l'])
 except Exception as e:errors.append(str(e)or type(e).__name__)
 for doc in docs.values():doc.close()
 return {'source_checks':sourcechecks,'global_findings':errors,'pass':not errors and len(sourcechecks)==34 and all(q['pass']for q in sourcechecks)}
def audit(M):
 # Rehydrate external audit inputs; geometry remains the live model.
 import sys as _audit_sys
 from pathlib import Path as _AuditPath
 _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
 from source_audit_sidecar import audit_model as _source_audit_model
 M = _source_audit_model(M)
 D=json.loads(DATA_PATH.read_text());globalerrors=[];checks=[]
 if sha(DATA_PATH)!=FROZEN_SHA:globalerrors.append('frozen_data_fingerprint')
 proof=verify_source(D);globalerrors.extend(proof['global_findings'])
 if not proof['pass']:globalerrors.append('original_capacity_source_failed')
 records=D['records'];es=[e for e in M['els']if e['c']=='P.heater'];by={e['id']:e for e in es}
 if len(es)!=82 or len(by)!=82 or set(by)!=set(records):globalerrors.append('exact_heater_inventory')
 for eid,r in records.items():
  e=by.get(eid);errors=[]
  if e is None:errors.append('missing_heater')
  else:
   if(e['c'],e['l'],e['g'])!=(r['category'],r['level'],r['before_g']):errors.append('preservation_guard_full_g_c_l')
   if e['t']!=r['after_type']or e.get('mark')!=r['after_mark']:errors.append('capacity_type_mark')
   a=e.get('a')or{};p=a.get('source_heater_capacity_review')or{}
   if a.get('cap_l')!=r['source_capacity_l']or a.get('cap_known')is not True:errors.append('capacity_property')
   if p.get('source_key')!=r['source_key']or p.get('data_sha256')!=FROZEN_SHA or p.get('capacity_literal_l')!=r['source_capacity_l']or p.get('power_literal_kw')!=r['source_power_kw']:errors.append('capacity_metadata_binding')
   if p.get('property_scope')!='capacity_and_power_literal_only' or p.get('physical_dimensions_Z_material_mount_ports_accepted')is not False or p.get('whole_body_source_checked')is not False:errors.append('unsupported_physical_promotion')
  checks.append({'id':eid,'capacity_l':r['source_capacity_l'],'property_scope':'capacity_and_power_literal_only','body_source_checked':False,'pass':not errors,'errors':errors})
 allerrors=sum(bool(q['errors'])for q in checks)+len(globalerrors)
 return {'schema':'c4.water-heater-capacity-source-audit.v1','checks':checks,'source_glyph_checks':proof['source_checks'],'global_findings':globalerrors,'summary':{'checked':82,'unique_raw_glyphs':34,'capacity80L':61,'capacity50L':21,'property_corrections':21,'body_source_checked':0,'whole_geometry_changes':0,'uncovered':sum(eid not in by for eid in records),'findings':allerrors,'passed':allerrors==0}}
