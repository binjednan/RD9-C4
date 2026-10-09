# -*- coding: utf-8 -*-
"""Correct actual HVAC body graphics; retire arrow/line clusters misread as bodies.

Only registered XY, body graphic bounds and their axis orientation are read
from the drawing. Physical body/neck dimensions, material, Z and ports are not
accepted. The normalized Z guard protects the existing assumed base while
allowing the separately logged procedural ceiling offset to be recalculated.
"""
import copy
import functools
import hashlib
import json
from pathlib import Path
import sys

DATA_PATH = Path(__file__).with_name('data') / 'restore_hvac_outlets_source.json'
TYPES = {}
_OLD_PLACEMENT = ('mount_note','guess_from','guess_host','guess_kind','guess_cm',
                  'guess_conf','guess_intent','guess_conv','snap_cm','snap_note')


@functools.lru_cache(maxsize=4)
def _verify_original(data_text, pdf_path, mtime_ns, size):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
    import check_hvac_outlets_source as gate
    data=json.loads(data_text)
    raw, findings=gate.validate_ledger(data)
    if findings:
        raise ValueError('HVO v2 original body/source guard failed: '+json.dumps(findings[:4],ensure_ascii=False))
    return True


def _guard(e, row, split=False):
    if (e['c'],e.get('t'),e['l'],e['g'][0]) != (row['category'],row['type'],row['level'],'b'):
        raise ValueError('HVO c/type/level/kind guard failed: '+e['id'])
    accepted=[row['after_g'][:6]] if split else [row['before_g'][:6],row['after_g'][:6]]
    if not split and row.get('procedural_source_emitter_g_core') is not None:
        # The ground-floor emitter is stateless and serializes raw XY to 0.1cm.
        # This exact original input is independently bound to the same raw slot;
        # it is a procedural guard, not an additional accepted body position.
        accepted.append(row['procedural_source_emitter_g_core'])
    if e['g'][:6] not in accepted:
        raise ValueError('HVO exact procedural graphic guard failed: '+e['id'])
    a=e.get('a') or {}
    zbase=[round(v-float(a.get('ceil_dz',0)),3) for v in e['g'][6:8]]
    if zbase != row['normalized_assumed_Z_base_m']:
        raise ValueError('HVO normalized assumed Z base guard failed: '+e['id'])
    if e.get('m') != row['prototype'].get('m'):
        raise ValueError('HVO procedural display material guard failed: '+e['id'])


def apply(M, els=None):
    els=M['els'] if els is None else els
    data_text=DATA_PATH.read_text(encoding='utf-8');data=json.loads(data_text)
    pdf=Path(data['source_pdf']);stat=pdf.stat()
    _verify_original(data_text,str(pdf),stat.st_mtime_ns,stat.st_size)
    elements={e['id']:e for e in els}
    if len(elements)!=len(els):raise ValueError('HVO duplicate model identities')
    # Validate the entire mutation before removing or adding any model element.
    for eid,row in data['records'].items():
        e=elements.get(eid);split=row['review_action']=='split_raw_body_core'
        if e is None:
            if not split:raise ValueError('HVO missing existing actual body: '+eid)
            origin=elements.get(row['origin_id'])
            if origin is None:raise ValueError('HVO missing split procedural origin: '+eid)
        else:
            _guard(e,row,split)
    retired=[]
    for eid,row in data['retired_non_device_records'].items():
        e=elements.get(eid)
        if e is None:continue
        a=e.get('a') or {};base=[round(v-float(a.get('ceil_dz',0)),3) for v in e['g'][6:8]]
        if ((e['c'],e.get('t'),e['l'],e['g'][:6]) !=
            (row['category'],row['type'],row['level'],row['before_g'][:6]) or
                base!=row['normalized_assumed_Z_base_m']):
            raise ValueError('HVO false-component identity/geometry guard failed: '+eid)
        retired.append(eid)
    retired_set=set(retired)
    els[:]=[e for e in els if e['id'] not in retired_set]
    changes=[];added=[]
    for eid,row in data['records'].items():
        e=elements.get(eid);split=row['review_action']=='split_raw_body_core'
        if e is None:
            e=copy.deepcopy(row['prototype']);e['id']=eid
            # Keep the same assumed vertical base as the source-bound prototype.
            e['g']=copy.deepcopy(row['after_g']);els.append(e);elements[eid]=e;added.append(eid)
        before=copy.deepcopy(e['g']);e['g'][:6]=copy.deepcopy(row['after_g'][:6])
        a=e.setdefault('a',{});source=row['source']
        previous={key:copy.deepcopy(a[key]) for key in _OLD_PLACEMENT if key in a}
        for key in _OLD_PLACEMENT:a.pop(key,None)
        for key in ('source_kind','source_page','source_sheet','source_layer','source_primitives','source_pdf_points',
                    'source_transform','source_xy','source_glyph_bbox_pdf','source_sheet_text','source_pdf_sha256',
                    'source_body_kind','source_body_primitives','source_body_pdf_points','source_body_bbox_pdf',
                    'source_body_component_index','source_graphic_dimensions_cm'):
            a[key]=copy.deepcopy(source[key])
        a.update({
            'source_locked_xy':True,'source_anchor':'actual_device_body_graphic_core_bbox_centre',
            'source_drawing_indices':[p[0] for p in source['source_primitives']],
            'source_raw_items':[copy.deepcopy(p['raw_items']) for p in source['source_bound_primitives']],
            'source_record_sha256':row['source_record_sha256'],'source_hvac_outlet_record':eid,
            'source_glyph_bounds_verified':True,'source_graphic_bbox_verified':True,
            'source_graphic_rotation_verified':True,'source_geometry_review':'body_graphic_only',
            'source_mount_verified':False,'source_contact_verified':False,'source_Z_verified':False,
            'source_dimensions_verified':False,'source_material_verified':False,
            'source_rotation_verified':False,'source_ports_verified':False,
            'source_physical_geometry_status':'symbolic_body_proxy_pending_physical_dimensions_Z_ports_material_mounting',
            'source_mount_gap':'الموضع وحدود رمز الجسم من المصدر بعد استبعاد أسهم التدفق والخطوط. مقاس العنق أو الجسم التنفيذي والمنسوب والمضيف والمنافذ تحتاج دليلًا مستقلًا؛ لم يُختر أقرب جدار أو مجرى.',
            'assumed':row['assumed_ar'],'source_review_action':row['review_action'],
            'size_cm':str(round(e['g'][3],1))+'×'+str(round(e['g'][4],1)),
            'size_note':'حدود رمز الجسم على الرسم؛ ليست مقاس العنق أو جسم المصنع.'})
        if previous and 'source_previous_placement' not in a:a['source_previous_placement']=previous
        if split:a['sys']='air';a['source_split_origin_id']=row['origin_id']
        changes.append({'id':eid,'origin_id':row['origin_id'],'before_g':before,'after_g':copy.deepcopy(e['g']),
            'XY_changed':before[1:3]!=e['g'][1:3],'graphic_shape_changed':before[3:6]!=e['g'][3:6],
            'assumed_Z_material_category_type_level_preserved':True,
            'source_record_sha256':row['source_record_sha256']})
    stats={**data['summary'],'locked':len(changes),'XY_changed_this_apply':sum(q['XY_changed'] for q in changes),
        'graphic_shape_changed_this_apply':sum(q['graphic_shape_changed'] for q in changes),
        'retired_non_device_count':len(data['retired_non_device_records']),'retired_this_apply':retired,
        'added_this_apply':added,'source_data':'pipeline/data/restore_hvac_outlets_source.json',
        'source_data_sha256':hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
        'scope_ar':data['scope_ar'],'historical_v1_acceptance_revoked':True,'changes':changes}
    M.setdefault('meta',{})['hvac_outlets_source_restore']=stats
    return stats


build=apply
