# -*- coding: utf-8 -*-
"""Guarded raw-source corrections for water traces and missing device symbols.

apply(M, els=None) is called after legacy MEP extraction and before connections.
It retires equipment strokes falsely extracted as water pipes, removes break
glyphs from actual water routes, keeps literal disconnected parts separate, and
adds one source graphic marker per identified device. Marker dimensions, Z,
material, mount and operation are unverified; no hydraulic connection is made.
"""
import copy,hashlib,json,re
from pathlib import Path
DATA_PATH=Path(__file__).with_name('data')/'water_supply_source_corrections.json'
ID_RE=re.compile(r'-WSC\d{4}$')
TYPES={
 'ws_lifting_graphic':{'name':'مضخة رفع ماء — رمز مصدر','sp':[['مواصفات المجموعة — MECH2:19 نص145','VERTICAL TYPE؛ 45GPM @5bar،3kW؛ 1 DUTY/1 STANDBY']], 'asm':['تعيين مضخة العمل والاحتياط لكل رمز، مقاس الجسم وZ والمنافذ غير مثبتة']},
 'ws_filtration_pump_graphic':{'name':'مضخة فلترة ماء — رمز مصدر','sp':[['مواصفات المجموعة — MECH2:22 نص95','45GPM @2bar،1.1kW؛ 1 DUTY/1 STANDBY']], 'asm':['تعيين مضخة العمل والاحتياط لكل رمز، مقاس الجسم وZ والمنافذ غير مثبتة']},
 'ws_booster_graphic':{'name':'مضخة تعزيز ماء — رمز مصدر','sp':[['مواصفات المجموعة — MECH2:22 نص94','60GPM @2bar،1.5kW؛ 1 DUTY/1 STANDBY']], 'asm':['تعيين مضخة العمل والاحتياط لكل رمز، مقاس الجسم وZ والمنافذ غير مثبتة']},
 'ws_media_filter_graphic':{'name':'وعاء فلتر متعدد الوسائط — رمز مصدر','sp':[['المصدر — MECH2:22 نص96','MULTI-MEDA WITH AUTO-HEAD CONTROLLER؛ 45GPM']], 'asm':['أبعاد الجسم وZ والمادة والمنافذ واتصالها غير مثبتة']},
 'ws_pv_graphic':{'name':'وعاء ضغطPV — رمز مصدر','sp':[['المصدر — MECH2:22 نص94','WITH PRESSURE VESSEL SIZE 110 Lit.']], 'asm':['مقاس الجسم وشكله التنفيذي وZ ومادته ومنافذه غير مثبتة']},
 'ws_break_tank_graphic':{'name':'خزان كسر الضغط — رمز مصدر','sp':[['المصدر — MECH2:22 نص97','PRESSURE BREAK TANK']], 'asm':['الحجم والأبعاد وZ والمادة والمنافذ غير محددة في المصدر المراجع']},
 'ws_uv_graphic':{'name':'معقمUV — رمز مصدر','sp':[['مواصفات المجموعة — MECH2:22 نص93','60GPM؛ 1 DUTY/1 STANDBY']], 'asm':['تعيين وحدة العمل والاحتياط لكل رمز، أبعاد الجسم وZ والمنافذ غير مثبتة']},
}
for _type in TYPES.values():
 _type['n']=_type.pop('name');_type['cf']='doc';_type['sr']=['MECH2:19','MECH2:22','MECH2:23']
 _type['sp'].append(['الدلالة','رمز جهاز كامل ومربوط بوسم المصدر؛ جسم العرض ليس جسمًا تنفيذيًا'])
def _sha(g):return hashlib.sha256(json.dumps(g,separators=(',',':')).encode()).hexdigest()
def _expected_part(r,p):
 z=r['before_g'][1][0][2]
 return ['t',[[round(x,4),round(y,4),z]for x,y in p['xy_cm']],r['before_g'][2]]
def _source_attrs(r,p,k):
 return {'sys':'water_roof' if r['level']=='R'else 'cold','source_locked_xy':True,'no_connectors':True,
  'source_kind':'raw_water_pipe_without_break_glyph','source_record':r['id'],'source_part_index':k,
  'source_page':r['source'],'source_layer':p['layer'],'source_primitives':[[p['drawing'],p['poly']]],
  'source_vertex_indices':copy.deepcopy(p['vertex_indices']),'source_pdf_points':copy.deepcopy(p['pdf_points']),
  'source_raw_pdf_points':copy.deepcopy(p['raw_pdf_points']),'source_raw_items':copy.deepcopy(p['raw_items']),
  'source_transform':copy.deepcopy(r['registration']),'source_xy':copy.deepcopy(p['xy_cm']),
  'source_Z_verified':False,'source_diameter_verified':False,'source_dimensions_verified':False,
  'source_geometry_role':'raw_drawn_water_route_with_original_unverified_Z_and_diameter',
  'source_review_reason':r['reason_ar'],'source_before_geometry_sha256':r['before_geometry_sha256'],
  'assumed':'XY من رؤوس خط الماء الخام؛Z والقطر الحاليان محفوظان كافتراض ولم يتحولا إلى إثبات. رموز القطع غير أنابيب، وفجوات الصمامات لا تصل تلقائيًا. '+r['reason_ar']}

def apply(M,els=None,verbose=False):
 els=M['els']if els is None else els
 D=json.loads(DATA_PATH.read_text(encoding='utf-8'));data_sha=hashlib.sha256(DATA_PATH.read_bytes()).hexdigest()
 byid={e['id']:e for e in els};prior=M.get('meta',{}).get('water_supply_source_corrections',{})
 # Validate every source binding before making any change. A missing retired
 # identity is accepted only on a repeat of this exact correction revision.
 for r in D['restore_records']+D['retire_records']:
  e=byid.get(r['id'])
  if e is None:
   if r in D['retire_records']and prior.get('source_data_sha256')==data_sha:continue
   raise ValueError('Water correction identity missing: '+r['id'])
  if(e['c'],e.get('t'),e['l'],e['g'][0])!=(r['category'],r['type'],r['level'],'t'):
   raise ValueError('Water correction identity/type changed: '+r['id'])
  allowed=[r['before_geometry_sha256']]
  if 'parts'in r:allowed.append(_sha(_expected_part(r,r['parts'][0])))
  if _sha(e['g'])not in allowed:raise ValueError('Water source geometry guard failed: '+r['id'])
 retired={r['id']for r in D['retire_records']};removed=[e['id']for e in els if e['id']in retired]
 els[:]=[e for e in els if e['id']not in retired and not ID_RE.search(e['id'])]
 M.setdefault('types',{}).update(copy.deepcopy(TYPES));M.setdefault('sp',[])
 M.setdefault('mats',{}).setdefault('ws_graphic_unknown',{'name':'مؤشر معدات ماء — المادة واللون غير محددين',
  'source_material_literal':'unknown','source_finish_literal':'unknown','physical_color_literal':'unknown',
  'physical_color_hex':None,'status':'graphic_source_marker_only'})
 for layer in M.get('layers',[]):
  if layer.get('id')=='P'and not any(sub[0]=='P.equip'for sub in layer.get('subs',[])):
   layer.setdefault('subs',[]).append(['P.equip','أجهزة الماء المثبتة بالرموز'])
 added=[];changes=[];part_number=13
 for r in D['restore_records']:
  e=byid[r['id']];oldg=copy.deepcopy(e['g']);e['g']=_expected_part(r,r['parts'][0])
  e.setdefault('a',{}).update(_source_attrs(r,r['parts'][0],0));e['a']['source_trace_review']='raw_pipe_restored_without_device_or_break_strokes'
  e['a']['trace_cm']=copy.deepcopy(e['g'][1]);e['a'].pop('guess_from',None)
  changes.append({'id':e['id'],'before_g':oldg,'after_g':copy.deepcopy(e['g']),'source':r['source'],
   'source_parts':[[p['drawing'],p['poly'],p['vertex_indices']]for p in r['parts']],
   'changed':oldg!=e['g'],'Z_preserved':True,'diameter_preserved':True,'reason_ar':r['reason_ar']})
  for k,p in enumerate(r['parts'][1:],1):
   q=copy.deepcopy(e);q['id']='P.cold-'+r['level']+'-WSC'+str(part_number).zfill(4);part_number+=1
   q['g']=_expected_part(r,p);q['a'].update(_source_attrs(r,p,k));q['a']['trace_cm']=copy.deepcopy(q['g'][1])
   q['a']['source_split_from']=r['id'];q['a']['source_split_preserves_disconnected_raw_parts']=True
   added.append(q)
 for d in D['device_markers']:
  # Identity deduplication uses actual source primitives, never proximity or
  # a similarly located fire/irrigation pump from another drawing system.
  own={(p['drawing'],p['poly'])for p in d['glyph_primitives']}
  for e in els:
   a=e.get('a')or{}
   if e['c']in('P.pump','P.tank','P.equip')and a.get('source_page')==d['source']and own.intersection(map(tuple,a.get('source_primitives',[]))):
    raise ValueError('A source-bound water device already exists: '+d['id']+' / '+e['id'])
  x,y=d['source_xy_cm'];z=d['display_z_m'];ref=d['source']+' رمز معدات ماء: '+d['name_ar']+'؛ الجسم والمادة والمنسوب غير مثبتين'
  if ref not in M['sp']:M['sp'].append(ref)
  a={'sys':'water_roof'if d['level']=='R'else 'water_site','no_connectors':True,'source_locked_xy':True,
   'source_kind':'water_device_whole_glyph_bbox_anchor','source_page':d['source'],'source_layer':'M_WS_CW',
   'source_primitives':[[p['drawing'],p['poly']]for p in d['glyph_primitives']],
   'source_pdf_points':[copy.deepcopy(d['source_pdf_centre'])],'source_xy':copy.deepcopy(d['source_xy_cm']),
   'source_transform':copy.deepcopy(d['registration']),'source_pdf_sha256':d['source_pdf_sha256'],
   'source_glyph_bbox_pdf':copy.deepcopy(d['glyph_bbox_pdf']),'source_texttrace':copy.deepcopy(d['source_texttrace']),
   'source_spec_texttraces':copy.deepcopy(d['source_spec_texttraces']),
   'source_leader_primitives':[[p['drawing'],p['poly']]for p in d['source_leaders']],
   'source_geometry_role':'graphic_marker_at_whole_device_symbol_anchor_not_physical_body',
   'source_dimensions_verified':False,'source_Z_verified':False,'source_material_verified':False,
   'source_finish_verified':False,'source_mount_verified':False,'source_contact_verified':False,
   'source_graphic_bbox_is_physical_dimension':False,'source_duty_assignment_verified':False,
   'physical_geometry_status':'pending_body_dimensions_Z_mount_material_and_ports',
   'material_status':'unknown','elevation_status':'display_only_at_local_roof_or_ground_FFL',
   'name':d['name_ar'],'assumed':'أسطوانة قطر3سم وارتفاع2سم للعرض عندFFL المحلي فقط؛XY هو مركز اتحاد كامل رمز الجهاز الخام. حجم الجهاز وشكله التنفيذي وZ ومادته ولونه ومنافذه واتصاله غير مثبتة. رمزا DUTY/STANDBY يثبتان العدد ولا يعينان دور كل جسم.'}
  added.append({'id':d['id'],'c':d['category'],'t':d['type'],'l':d['level'],
   'g':['cyl',round(x,4),round(y,4),1.5,z,round(z+.02,4)],'m':'ws_graphic_unknown','s':[M['sp'].index(ref)],'a':a})
 els.extend(added)
 stats={**D['summary'],'retired_ids':sorted(retired),'retired_present_this_apply':len(removed),
  'changed_paths_this_apply':sum(c['changed']for c in changes),'changes':changes,'added_ids':[e['id']for e in added],
  'source_data':'pipeline/data/water_supply_source_corrections.json','source_data_sha256':data_sha,
  'scope_limit_ar':D['scope_limit_ar']}
 M.setdefault('meta',{})['water_supply_source_corrections']=stats
 if verbose:print('water source corrections:',{k:v for k,v in stats.items()if not isinstance(v,(dict,list))})
 return stats

build=apply
