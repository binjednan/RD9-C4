# -*- coding: utf-8 -*-
"""Water review wave WST: apply(M, els=None), after WSC and before supports/CN.

Preserves source line vertices as separate literal parts; retires S-break
strokes and two equipment frames falsely extracted as pipes. No source gap is
filled. Z, diameter, material and S geometry are untouched. Remaining records
separate entire open-line XY support from dashed-line interpretation and local
symbol gaps. See DESIGN_WATER_MIXED_SOURCE_REVIEW.md and the frozen raw ledger.
"""
import copy,hashlib,json,re
from pathlib import Path
DATA_PATH=Path(__file__).with_name('data')/'water_supply_mixed_corrections.json'
ID_RE=re.compile(r'-WST\d{4}$')
TYPES={}
def _sha(g):return hashlib.sha256(json.dumps(g,separators=(',',':')).encode()).hexdigest()
def _expected_part(r,p):
 z=r['before_g'][1][0][2]
 return ['t',[[round(x,4),round(y,4),z]for x,y in p['xy_cm']],r['before_g'][2]]
def _attrs(r,p,k):
 return {'sys':'water_roof'if r['level']=='R'else'cold','source_locked_xy':True,'no_connectors':True,
  'source_kind':'raw_water_pipe_without_break_glyph','source_correction_wave':'mixed560',
  'source_record':r['id'],'source_part_index':k,'source_page':r['source'],'source_layer':p['layer'],
  'source_primitives':[[p['drawing'],p['poly']]],'source_vertex_indices':copy.deepcopy(p['vertex_indices']),
  'source_pdf_points':copy.deepcopy(p['pdf_points']),'source_raw_pdf_points':copy.deepcopy(p['raw_pdf_points']),
  'source_raw_items':copy.deepcopy(p['raw_items']),'source_transform':copy.deepcopy(r['registration']),
  'source_xy':copy.deepcopy(p['xy_cm']),'source_Z_verified':False,'source_diameter_verified':False,
  'source_dimensions_verified':False,'source_contact_verified':False,'source_geometry_role':'literal_raw_water_line_with_retained_unverified_Z_and_diameter',
  'source_trace_review':'water_mixed_source_wave','source_trace_status':'literal_water_part_without_source_gap_bridge',
  'source_before_geometry_sha256':r['before_geometry_sha256'],'source_review_reason':r['reason_ar'],
  'assumed':'XY من رؤوس خط الماء الخام المحددة بالهوية. Z والقطر القديمان محفوظان كافتراض. الأجزاء المنفصلة والرموز وفجوات المصدر لا توصل تلقائيًا؛ لم يعتمد جسم جهاز أو مادة أو تشغيل.'}
def apply(M,els=None,verbose=False):
 els=M['els']if els is None else els;D=json.loads(DATA_PATH.read_text(encoding='utf-8'));data_sha=hashlib.sha256(DATA_PATH.read_bytes()).hexdigest()
 E={e['id']:e for e in els};prior=M.get('meta',{}).get('water_supply_mixed_corrections',{})
 for r in D['restore_records']+D['retire_records']+D['review_records']:
  e=E.get(r['id'])
  if e is None:
   if r in D['retire_records']and prior.get('source_data_sha256')==data_sha:continue
   raise ValueError('WST source identity missing: '+r['id'])
  if(e['c'],e.get('t'),e['l'],e['g'][0])!=(r['category'],r['type'],r['level'],'t'):raise ValueError('WST category/type/level guard failed: '+r['id'])
  allowed=[r['before_geometry_sha256']]
  if 'parts'in r:allowed.append(_sha(_expected_part(r,r['parts'][0])))
  if _sha(e['g'])not in allowed:raise ValueError('WST geometry guard failed: '+r['id'])
 retired={r['id']for r in D['retire_records']};removed=[e['id']for e in els if e['id']in retired]
 els[:]=[e for e in els if e['id']not in retired and not ID_RE.search(e['id'])]
 added=[];changes=[];number=1
 for r in D['restore_records']:
  e=E[r['id']];oldg=copy.deepcopy(e['g']);e['g']=_expected_part(r,r['parts'][0]);e.setdefault('a',{}).update(_attrs(r,r['parts'][0],0))
  e['a']['trace_cm']=copy.deepcopy(e['g'][1]);e['a'].pop('guess_from',None)
  changes.append({'id':e['id'],'before_g':oldg,'after_g':copy.deepcopy(e['g']),'changed':oldg!=e['g'],
    'source':r['source'],'source_parts':[[p['drawing'],p['poly'],p['vertex_indices']]for p in r['parts']],
    'Z_preserved':True,'diameter_preserved':True,'source_gap_bridged':False})
  for k,p in enumerate(r['parts'][1:],1):
   q=copy.deepcopy(e);q['id']='P.cold-'+r['level']+'-WST'+str(number).zfill(4);number+=1;q['g']=_expected_part(r,p)
   q['a'].update(_attrs(r,p,k));q['a']['trace_cm']=copy.deepcopy(q['g'][1]);q['a']['source_split_from']=r['id'];added.append(q)
 for r in D['review_records']:
  a=E[r['id']].setdefault('a',{});status=r['status'];prior_status=a.get('source_water_review_status');a.update({'source_trace_review':'water_mixed_source_wave',
   'source_water_review_record':r['id'],'source_page':r['source'],'source_transform':copy.deepcopy(r['registration']),
   'source_primitives':[[p['drawing'],p['poly']]for p in r['source_primitives']],
   'source_locked_xy':True,'source_contact_verified':False,'source_Z_verified':False,'source_diameter_verified':False,
   'source_geometry_review_sha256':r['whole_trace_geometry_sha256'],'source_trace_limit':r['limit_ar'],
   'source_correction_wave':'mixed560','source_water_review_status':status})
  if status=='whole_open_linear_trace_within_0.2cm':a.update({'source_kind':'water_layer_linear_trace','source_trace_status':'raw_open_linear_water_trace'})
  else:
   a.update({'source_kind':'dashed_water_linework_route','source_trace_status':'derived_from_water_dash_pattern',
    'source_derived_spans_cm':copy.deepcopy(r['uncovered_openline_segments_cm']),
    'source_pending_spans_cm':copy.deepcopy(r['pending_spans_cm']),
    'source_position_pending':bool(r['pending_spans_cm'])})
   # A dash omission at a turn/crossing is source graphic line type. It is
   # not enough reason to block legacy CN, nor to prove a hydraulic crossing.
   if prior_status=='HW_dash_and_nonperiodic_symbol_gap_pending':a.pop('no_connectors',None)
 stats={**D['summary'],'retired_ids':sorted(retired),'retired_present_this_apply':len(removed),
  'changed_paths_this_apply':sum(r['changed']for r in changes),'changes':changes,'added_ids':[e['id']for e in added],
  'source_data':'pipeline/data/water_supply_mixed_corrections.json','source_data_sha256':data_sha,'scope_limit_ar':D['scope_limit_ar']}
 els.extend(added);M.setdefault('meta',{})['water_supply_mixed_corrections']=stats
 if verbose:print('WST:',{k:v for k,v in stats.items()if not isinstance(v,(list,dict))})
 return stats
build=apply
