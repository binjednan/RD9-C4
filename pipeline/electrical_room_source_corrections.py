"""Six EP-101 equipment anchors + EP-108 literal overall dimensions. No model IO."""
import copy, hashlib, json
from pathlib import Path
DATA_PATH=Path(__file__).with_name('data')/'electrical_room_source_corrections.json'
DATA_SHA256='c7329f4269b9977bd386aa1ba7a205e047cd8f58d969d79502801ecbc0c590d8'
TYPES={}
def data():
    raw=DATA_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=DATA_SHA256:raise ValueError('Electrical-room source ledger changed')
    return json.loads(raw)
def apply(M,els=None):
    E=M['els'] if els is None else els;D=data();by={}
    for e in E:by.setdefault(e['id'],[]).append(e)
    plans=[]
    for id,r in D['records'].items():
        matches=by.get(id,[])
        if len(matches)!=1:raise ValueError('Electrical-room identity missing/duplicate: '+id)
        e=matches[0];old=r['before_e']
        for k in ('c','t','l','m','mark','grp'):
            if e.get(k)!=old.get(k):raise ValueError('Electrical-room identity changed: '+id+'/'+k)
        if e['g'] not in (old['g'],r['after_g']):raise ValueError('Electrical-room exact geometry guard failed: '+id)
        plans.append((e,r))
    changed=[]
    for e,r in plans:
        if e['g']!=r['after_g']:changed.append(e['id'])
        e['g']=copy.deepcopy(r['after_g']);s=r['source'];a=e.setdefault('a',{})
        a.update(electrical_room_source_correction=True,source_kind='electrical_room_plan_anchor_and_literal_overall_dimensions',
            source_record_sha256=r['source_record_sha256'],source_data_sha256=DATA_SHA256,
            source_page='ELEC1:10',source_dimension_page='ELEC1:17',source_drawing_indices=[q['drawing_index']for q in s['plan_drawings']],
            source_anchor_pdf=copy.deepcopy(s['plan_anchor_pdf']),source_xy=copy.deepcopy(s['plan_anchor_xy_cm']),
            source_transform=copy.deepcopy(s['registration']),source_pdf_sha256=D['original_pdf']['sha256'],
            source_locked_xy=True,source_plan_anchor_verified=True,source_axis_angle_verified=True,
            source_overall_dimensions_literal_verified=True,source_overall_dimensions_cm=copy.deepcopy(s['dimension_evidence']['dims_cm']),
            source_relative_height_verified=True,source_absolute_Z_verified=False,source_Z_verified=False,
            source_physical_body_verified=False,source_material_verified=False,source_mount_verified=False,
            source_ports_verified=False,source_contact_verified=False,source_colour_verified=False,
            source_front_face_verified=False,historical_material_code=e.get('m'),
            source_geometry_review='literal_overall_extent_proxy_at_drawn_equipment_anchor',
            source_scope_limits=copy.deepcopy(D['limits_ar']))
    result={'schema':D['schema'],'data_sha256':DATA_SHA256,'controlled_ids':list(D['records']),
            'changed_ids':changed,'changed':len(changed),'equipment':6,'absolute_Z_verified':0,
            'installed_material_verified':0,'lifecycle_dependencies':copy.deepcopy(D['lifecycle_dependencies'])}
    # Run-local changed counts are returned; persisted provenance is stable on reapply.
    M.setdefault('meta',{})['electrical_room_source_corrections']={k:copy.deepcopy(v)for k,v in result.items()if k not in ('changed','changed_ids')}
    return result
