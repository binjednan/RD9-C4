"""Bounded EP-101/EP-108 HV and generator extent corrections; no model IO."""
import copy
import hashlib
import json
from pathlib import Path

DATA_PATH = Path(__file__).with_name('data') / 'equipment_completion.json'
DATA_SHA256 = '773ee989bc721d3062985f4eb0b121afb1bd99469ca38c2f0f632d45df3e6c29'
TYPES = {}


def data():
    raw = DATA_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DATA_SHA256:
        raise ValueError('Equipment completion source ledger changed')
    return json.loads(raw)


def apply(M, els=None):
    E = M['els'] if els is None else els
    D = data()
    by = {}
    for e in E:
        by.setdefault(e['id'], []).append(e)
    plans = []
    # Validate the whole batch before changing any element or metadata.
    for id, r in D['records'].items():
        matches = by.get(id, [])
        if len(matches) != 1:
            raise ValueError('Equipment completion identity missing/duplicate: ' + id)
        e = matches[0]
        for key in ('c', 't', 'l', 'm', 'mark', 'grp'):
            if e.get(key) != r['before_e'].get(key):
                raise ValueError('Equipment completion identity changed: ' + id + '/' + key)
        if e['g'] not in (r['before_e']['g'], r['after_g']):
            raise ValueError('Equipment completion exact geometry guard failed: ' + id)
        plans.append((e, r))
    changed = []
    for e, r in plans:
        if e['g'] != r['after_g']:
            changed.append(e['id'])
        e['g'] = copy.deepcopy(r['after_g'])
        source = r['source']
        e.setdefault('a', {}).update(
            equipment_completion=True,
            source_kind='electrical_equipment_plan_anchor_and_literal_extents',
            source_record_sha256=r['source_record_sha256'],
            source_data_sha256=DATA_SHA256,
            source_pdf_sha256=D['original_pdf']['sha256'],
            source_page='ELEC1:10', source_dimension_page='ELEC1:17',
            source_drawing_indices=[q['drawing_index'] for q in source['plan_drawings']],
            source_anchor_pdf=copy.deepcopy(source['plan_anchor_pdf']),
            source_xy=copy.deepcopy(source['plan_anchor_xy_cm']),
            source_transform=copy.deepcopy(source['registration']),
            source_locked_xy=True, source_plan_anchor_verified=True,
            source_axis_angle_verified=True,
            source_plan_dimensions_literal_verified=True,
            source_overall_dimensions_literal_verified=r['relative_height_verified'],
            source_literal_dimensions_cm=copy.deepcopy(r['literal_dimensions_cm']),
            source_relative_height_verified=r['relative_height_verified'],
            source_absolute_Z_verified=False, source_Z_verified=False,
            source_physical_body_verified=False, source_material_verified=False,
            source_mount_verified=False, source_ports_verified=False,
            source_contact_verified=False, source_colour_verified=False,
            source_front_face_verified=False,
            historical_material_code=e.get('m'),
            source_geometry_review='literal_extent_proxy_at_drawn_equipment_anchor',
            source_scope_limits=copy.deepcopy(r['limits_ar']),
        )
    result = {'schema': D['schema'], 'data_sha256': DATA_SHA256,
              'controlled_ids': list(D['records']), 'changed_ids': changed,
              'changed': len(changed), 'literal_plan_extents': 2,
              'relative_heights_verified': 1, 'absolute_Z_verified': 0,
              'installed_material_verified': 0,
              'lifecycle_dependencies': copy.deepcopy(D['lifecycle_dependencies'])}
    M.setdefault('meta', {})['equipment_completion'] = {
        k: copy.deepcopy(v) for k, v in result.items() if k not in ('changed', 'changed_ids')}
    return result


def issue_records(M):
    """Two bounded corrections; corrected dimensions are not full-device approval."""
    D = data()
    by = {e['id']: e for e in M['els']}
    rows = []
    for id, r in D['records'].items():
        e = by.get(id)
        if not e or e['g'] != r['after_g'] or not e.get('a', {}).get('equipment_completion'):
            raise ValueError('Equipment issue requires applied correction: ' + id)
        is_hv = r['relative_height_verified']
        rows.append({
            'id': 'DP-EQUIPMENT-HV-EXTENT' if is_hv else 'DP-EQUIPMENT-GENERATOR-EXTENT',
            'title': 'تصحيح الغلاف الكلي للقواطع من أبعاد الخلايا الثلاث' if is_hv else 'تصحيح بصمة المولد مع إبقاء ارتفاعه غير مثبت',
            'status': 'corrected',
            'source': 'ELEC1 ص10 EP-101 / ص17 EP-108، محاور ومحيط الجهاز وأبعاد حرفية',
            'note': r['source']['dimension_binding_ar'] + ' ' + ' '.join(r['limits_ar']),
            'level': e['l'], 'xy_cm': e['g'][1:3], 'z_m': e['g'][6], 'elements': [id],
            'before': {'g': copy.deepcopy(r['before_e']['g'])},
            'after': {'g': copy.deepcopy(r['after_g']),
                      'literal_dimensions_cm': copy.deepcopy(r['literal_dimensions_cm']),
                      'plan_extent_verified': True, 'relative_height_verified': is_hv,
                      'absolute_Z_verified': False, 'physical_body_accepted': False},
        })
    return rows
