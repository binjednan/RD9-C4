# -*- coding: utf-8 -*-
"""FHC1: retire open-leaf false cabinets/stubs; retain source recess markers.

No cabinet body size, absolute Z, material, mount or port is accepted. All
preflight checks complete before mutation. This module does not redirect stubs.
"""
import copy, hashlib, json
from pathlib import Path
DATA_PATH=Path(__file__).with_name('data')/'fire_cabinet_source.json'
FROZEN_SHA='f65928198fdd3bb5df8e1cffce6855a1d9b70ffce49f716293c992a671cb4e35'
TYPES={'fhc':{'n':'صندوق خرطوم الإطفاء — موضع من تجويف FHC','cf':'derived',
 'sr':['MECH2 ص10–13 مساقطFF-100–103: طبقةFHC المعمارية','MECH2 ص16 FF-106 تفصيلاFHC1/FHC2'],
 'sp':[['حد المسقط','مستطيل إحاطة التجويف المعماري نحو88×32سم؛ ورقة الباب المائلة ليست صندوقًا ثانيًا'],['التفصيل','750مم عرض و300مم عمق؛1500/1550مم أبعاد رأسية. تخصيص النوع والحد التنفيذي لكل موضع غير مثبت'],['العدد هنا','12هوية تجويف بعد حذف12جسمًا زائفًا و11وصلة اشتققت إلى الأجسام الزائفة؛ ليس قبولًا لعدد الأجهزة التنفيذي']],
 'asm':['ارتفاع العرض1.4م وبدايته0.5م فوقFFL افتراضان باقيان. أبعاد الجسم والمنسوب والمادة واللون والتركيب والمنافذ والاتصال معلقة']}}
def data():
 raw=DATA_PATH.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=FROZEN_SHA:raise ValueError('FHC1 frozen source ledger changed')
 return json.loads(raw)
def _after(row):
 e=copy.deepcopy(row['after_e']);e['a']['source_fire_cabinet_data_sha256']=FROZEN_SHA
 return e
def apply(M,els=None):
 els=M['els']if els is None else els;D=data();old=list(els);by={e['id']:e for e in els}
 if len(by)!=len(els):raise ValueError('FHC1 duplicate model identity')
 prior=M.get('meta',{}).get('fire_cabinet_source',{}).get('source_data_sha256')==FROZEN_SHA
 for eid,row in D['records'].items():
  if by.get(eid)not in [row['before_e'],_after(row)]:raise ValueError('FHC1 survivor full-object guard: '+eid)
 for r in D['retirements']:
  e=by.get(r['id'])
  if e is None:
   if not prior:raise ValueError('FHC1 retirement identity missing before first adoption: '+r['id'])
  elif e!=r['before_e']:raise ValueError('FHC1 retirement full-object guard: '+r['id'])
 allowed=set(D['records'])|{r['id']for r in D['retirements']if r['reason']=='false_second_cabinet_from_open_door_leaf'}
 if {e['id']for e in els if e.get('t')=='fhc'}-allowed:raise ValueError('FHC1 unexpected cabinet identity')
 for h in D['withdrawn_clashes']:
  found=[c for c in M.get('clashes',[])if c.get('id')==h['before_full_record']['id']]
  if len(found)>1 or(found and found[0]!=h['before_full_record']):raise ValueError('FHC1 historical clash record guard')
 # Source pairs are identity evidence only, never a geometry alias/connection.
 retired=set(D['exact_retired_ids']);removed=[e['id']for e in els if e['id']in retired]
 for eid,row in D['records'].items():by[eid].clear();by[eid].update(_after(row))
 els[:]=[e for e in els if e['id']not in retired]
 withdrawn={h['before_full_record']['id']for h in D['withdrawn_clashes']}
 if 'clashes'in M:M['clashes'][:]=[c for c in M['clashes']if c.get('id')not in withdrawn]
 M.setdefault('types',{}).update(copy.deepcopy(TYPES))
 stats={**D['summary'],'source_data':'pipeline/data/fire_cabinet_source.json','source_data_sha256':FROZEN_SHA,'retired_ids':D['exact_retired_ids'],'retired_this_apply':len(removed),'retired_leaf_to_survivor_source_identity_only':D['retired_leaf_to_survivor'],'historical_withdrawn_clashes':copy.deepcopy(D['withdrawn_clashes']),'scope_limit_ar':D['scope_limit_ar']}
 M.setdefault('meta',{})['fire_cabinet_source']=stats
 newpos={e['id']:i for i,e in enumerate(els)}
 checks=[{'id':eid,'pass':True,'source_kind':'architectural_FHC_recess_bbox_graphic_proxy','scope':'graphic_identity_and_bbox_only','source_body_dimensions_Z_material_ports_mount_verified':False}for eid in D['records']]
 return {**stats,'checks':checks,'global_findings':[],'uncovered':[],'old_to_new_indices':{i:newpos[e['id']]for i,e in enumerate(old)if e['id']in newpos},'retired_indices':[i for i,e in enumerate(old)if e['id']in retired]}
build=apply
