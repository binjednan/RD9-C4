# -*- coding: utf-8 -*-
"""WMT: source circle-M watermeter graphic markers and false W/M retirement.

apply(M, els=None), after WSC/WST and before support/connectors. No physical
meter dimension, elevation, material, port or hydraulic connection is claimed.
Source graphic identity is used for deduplication; the old washing-machine text
proxy is retired, and the existing architectural washer is not duplicated.
"""
import copy,hashlib,json,re
from pathlib import Path
DATA_PATH=Path(__file__).with_name('data')/'water_meter_source_remaining.json'
ID_RE=re.compile(r'-WMT\d{4}$')
TYPES={'ws_water_meter_graphic':{'n':'عداد ماء — رمز M في المصدر','cf':'doc','sr':['MECH2:20','MECH2:21'],
 'sp':[['الدلالة المصدرية','دائرة M؛ المفتاح WATER METER. ستة رموز في الطابق الأول وستة في المسقط المتكرر للطوابق2–5']],
 'asm':['مؤشر عرض قطر3سم وارتفاع2سم فقط؛ أبعاد العداد التنفيذي وZ والمادة واللون والمنافذ والتركيب غير مثبتة']}}
def _sha(g):return hashlib.sha256(json.dumps(g,separators=(',',':')).encode()).hexdigest()
def apply(M,els=None,verbose=False):
 els=M['els']if els is None else els;D=json.loads(DATA_PATH.read_text());data_sha=hashlib.sha256(DATA_PATH.read_bytes()).hexdigest();E={e['id']:e for e in els};prior=M.get('meta',{}).get('water_meter_source_remaining',{})
 for r in D['retire_false_WM']:
  e=E.get(r['id'])
  if not e:
   if prior.get('source_data_sha256')==data_sha:continue
   raise ValueError('WMT retirement identity missing: '+r['id'])
  if(e['c'],e.get('t'),e['l'])!=(r['category'],r['type'],r['level'])or _sha(e['g'])!=r['before_g_sha256']:raise ValueError('WMT retirement geometry/type/level guard failed: '+r['id'])
 retired={r['id']for r in D['retire_false_WM']};removed=[e['id']for e in els if e['id']in retired];els[:]=[e for e in els if e['id']not in retired and not ID_RE.search(e['id'])]
 # No proximity-based deduplication. A source primitive on a particular level
 # is one meter, independently of nearby valves and appliance display bodies.
 for r in D['meter_markers']:
  for e in els:
   a=e.get('a')or{}
   if e['l']==r['level']and a.get('source_page')==r['source_page']and a.get('source_kind')=='water_meter_circle_M_graphic_anchor'and [r['drawing'],r['poly']]in a.get('source_primitives',[]):raise ValueError('WMT meter source already bound: '+e['id'])
 M.setdefault('types',{}).update(copy.deepcopy(TYPES));M.setdefault('sp',[]);M.setdefault('mats',{}).setdefault('ws_graphic_unknown',{'name':'مؤشر معدات ماء — المادة واللون غير محددين','source_material_literal':'unknown','source_finish_literal':'unknown','physical_color_literal':'unknown','physical_color_hex':None,'status':'graphic_source_marker_only'})
 for layer in M.get('layers',[]):
  if layer.get('id')=='P'and not any(s[0]=='P.equip'for s in layer.get('subs',[])):layer.setdefault('subs',[]).append(['P.equip','أجهزة الماء المثبتة بالرموز'])
 added=[]
 for r in D['meter_markers']:
  x,y=r['source_xy_cm'];z=r['display_z_m'];ref=r['source_page']+' WATER METER دائرة M؛ حضور XY فقط'
  if ref not in M['sp']:M['sp'].append(ref)
  a={'sys':'cold','no_connectors':True,'source_locked_xy':True,'source_kind':'water_meter_circle_M_graphic_anchor','source_page':r['source_page'],'source_layer':r['layer'],'source_primitives':[[r['drawing'],r['poly']]],'source_pdf_points':copy.deepcopy(r['source_pdf_points']),'source_raw_items':copy.deepcopy(r['raw_items']),'source_transform':copy.deepcopy(r['registration']),'source_xy':copy.deepcopy(r['source_xy_cm']),'source_M_character':copy.deepcopy(r['text_M']),'source_pdf_sha256':D['source_pdf_sha256'],'source_graphic_radius_not_body_dimension':True,'source_geometry_role':'graphic_marker_at_source_circle_M_anchor','source_dimensions_verified':False,'source_Z_verified':False,'source_material_verified':False,'source_finish_verified':False,'source_mount_verified':False,'source_contact_verified':False,'source_ports_verified':False,'physical_geometry_status':'pending_body_dimensions_Z_mount_material_and_ports','material_status':'unknown','elevation_status':'display_only_at_local_FFL','assumed':'مؤشر قطر3سم وارتفاع2سم عندFFL للطابق لأغراض العرض؛ دائرة M تثبت حضور ومركز الرمز فقط. قطر دائرة الرسم ليس مقاس جسم عداد؛Z والمادة واللون والمنافذ والاتصال غير مثبتة.'}
  added.append({'id':r['id'],'c':r['category'],'t':r['type'],'l':r['level'],'g':['cyl',round(x,4),round(y,4),1.5,z,round(z+.02,4)],'m':'ws_graphic_unknown','s':[M['sp'].index(ref)],'a':a})
 els.extend(added);stats={**D['summary'],'retired_ids':sorted(retired),'retired_present_this_apply':len(removed),'added_ids':[e['id']for e in added],'source_data':'pipeline/data/water_meter_source_remaining.json','source_data_sha256':data_sha,'scope_limit_ar':D['scope_limit_ar']};M.setdefault('meta',{})['water_meter_source_remaining']=stats
 if verbose:print('WMT:',{k:v for k,v in stats.items()if not isinstance(v,(list,dict))})
 return stats
build=apply
