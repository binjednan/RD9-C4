# -*- coding: utf-8 -*-
"""Source bound garbage-chute components from full plans and A1100 literals.

build(M, els=None) regenerates GC elements in memory. The small plan circle
proves its centre only: 600/300 mm and 1.5 mm SS304 are separate A1100 text
data. Every Z is explicitly uncertain. No structural opening, lower bend,
cleaning feeder, connector or support is invented. The fan is one graphic
marker, not two bodies for the repeated roof/top-roof symbol.
"""
import collections
import copy
import hashlib
import json
import math
import re
from pathlib import Path
from shapely.geometry import Polygon

DATA_PATH = Path(__file__).with_name('data') / 'garbage_chute_remaining.json'
ID_RE = re.compile(r'-GC\d{4}$')
TYPES = {
    'garbage_chute': {'n': 'مجرى النفايات — موضع المسقط وقطر التفصيل', 'cf': 'doc',
        'sp': [['القطر والمادة', '600 مم؛ SS304 سماكة 1.5 مم من A1100'],
               ['الموضع', 'مركز الرمز الأصلي لكل دور دون توحيد المراكز']],
        'sr': ['ARCH1 ص6–7 A103/A104', 'ARCH2 ص18 A1100'],
        'asm': ['حدود Z للعرض بين الطوابق؛ التثبيت والفتحات ونقطة المخفض غير معتمدة']},
    'garbage_hopper': {'n': 'باب استقبال مجرى النفايات', 'cf': 'doc',
        'sp': [['الإطار', '59×75 سم، فتحة صافية 45×45 سم، SS304'],
               ['الحريق', '120 دقيقة من النص؛ لا يثبت ذلك تنفيذ الجهاز']],
        'sr': ['ARCH1 ص6–7 رمز إطار الباب', 'ARCH2 ص18 A1100'],
        'asm': ['ارتفاع التركيب وسمك إطار الباب للعرض فقط؛ فتحات الجدار غير محسومة']},
    'garbage_chute_vent': {'n': 'أنبوب تهوية مجرى النفايات', 'cf': 'doc',
        'sp': [['القطر والمادة', '300 مم؛ SS304 سماكة 1.5 مم'],
               ['القطاع', 'قاعدة المروحة عند R+1.20م؛ منسوب قمتها وتصريفها النهائي غير مثبتين']],
        'sr': ['ARCH1 ص8 A105', 'ARCH2 ص18 A1100'],
        'asm': ['جزء العرض فوقR إلى قاعدة المروحة فقط؛ امتداد المخفض والتصريف النهائي غير معتمد']},
    'garbage_exhaust_fan_marker': {'n': 'موضع مروحة مجرى النفايات من الرمز', 'cf': 'doc',
        'sp': [['الوسم', 'CA150 MD E RF'], ['عدد الأجهزة', 'رمز مكرر في A105/A106 لنظام واحد']],
        'sr': ['ARCH1 ص8–9 A105/A106', 'ARCH2 ص18 A1100'],
        'asm': ['مؤشر فقط؛ حجم جسم المروحة وقمتها ونقطة التصريف النهائية غير معتمدة']},
}


def _hollow_circle(x, y, diameter, thickness, z0, z1):
    outer = [[round(x + diameter / 2 * math.cos(i * math.tau / 80), 4),
              round(y + diameter / 2 * math.sin(i * math.tau / 80), 4)] for i in range(80)]
    inner = [[round(x + (diameter / 2 - thickness) * math.cos(i * math.tau / 80), 4),
              round(y + (diameter / 2 - thickness) * math.sin(i * math.tau / 80), 4)] for i in range(80)]
    polygon = Polygon(outer, [inner])
    assert polygon.is_valid and polygon.area > 0
    return ['p', outer, z0, z1, [inner]]


def build(M, els=None, verbose=False):
    els = M['els'] if els is None else els
    els[:] = [e for e in els if not ID_RE.search(e['id'])]
    D = json.loads(DATA_PATH.read_text(encoding='utf-8'))
    M.setdefault('types', {}).update(copy.deepcopy(TYPES))
    M.setdefault('mats', {}).setdefault('gc_ss304', {
        'name': 'SS304 من A1100 — التشطيب واللون غير محددين',
        'source_material_literal': 'STAINLESS STEEL GRADE 304',
        'source_refs': ['ARCH2:18'], 'source_finish_literal': 'unknown',
        'physical_color_literal': 'unknown', 'physical_color_hex': None,
        'status': 'source_material_verified_finish_unknown'})
    M['mats'].setdefault('gc_graphic_unknown', {
        'name': 'مؤشر مصدر — لا مادة أو لون تنفيذ معتمد',
        'source_material_literal': 'unknown', 'source_finish_literal': 'unknown',
        'physical_color_literal': 'unknown', 'physical_color_hex': None,
        'status': 'graphic_source_marker_only'})
    count = collections.Counter()
    for q in D['records']:
        role = q['role'];source = q['source'];x, y = source['source_xy']
        a = {**copy.deepcopy(source), 'sys': 'garbage_chute', 'no_connectors': True,
             'source_locked_xy': True, 'source_kind': 'garbage_plan_graphic_anchor',
             'source_plan_role': role, 'source_dimension_literals': [copy.deepcopy(D['literals'][i]) for i in q['literal_refs']],
             'source_Z_verified': False, 'source_mount_verified': False,
             'source_contact_verified': False, 'source_finish_verified': False,
             'source_material_verified': role != 'fan_marker',
             'source_dimensions_verified': False,
             'material_status': 'literal_SS304' if role != 'fan_marker' else 'unknown',
             'finish_status': 'not_specified_in_reviewed_source',
             'elevation_status': 'source_detail_pending_or_partially_bounded',
             'physical_geometry_status': 'pending_Z_support_openings_and_remaining_details',
             'assumed': q['z_basis_ar'],
             'source_review_ids': [v['id'] for v in D['conflicts']],
             'source_conflict_ids': [v['id'] for v in D['conflicts'] if v.get('status') == 'confirmed_source_conflict'],
             'source_graphic_diameter_is_physical_size': False}
        if role in ('chute', 'vent'):
            g = _hollow_circle(x, y, q['diameter_cm'], q['sheet_thickness_cm'], q['z0'], q['z1'])
            a.update(source_diameter_verified=True, source_sheet_thickness_verified=True,
                     nominal_diameter_cm=q['diameter_cm'], sheet_thickness_cm=q['sheet_thickness_cm'],
                     geometry_role='literal_diameter_at_drawn_graphic_anchor_with_assumed_Z')
            typ = 'garbage_chute' if role == 'chute' else 'garbage_chute_vent'
            category = 'M.equip' if role == 'chute' else 'M.pipe'
        elif role == 'hopper':
            g = ['b', round(x, 4), round(y, 4), q['width_cm'], q['display_depth_cm'], 0, q['z0'], q['z1']]
            a.update(source_frame_width_verified=True, source_frame_height_verified=True,
                     source_frame_width_cm=59, source_frame_height_cm=75, source_clear_opening_cm=[45, 45],
                     source_fire_minutes=120, geometry_role='literal_frame_outline_at_drawn_plate_anchor_with_assumed_depth_and_Z')
            typ = 'garbage_hopper';category = 'M.equip'
        else:
            g = ['cyl', round(x, 4), round(y, 4), q['display_radius_cm'], q['z0'], q['z1']]
            a.update(source_is_annotation=True, source_semantic_marker=True,
                     tag='CA150 MD E RF', geometry_role='graphic_source_marker',
                     physical_geometry_status='graphic_only_body_and_Z_not_verified')
            typ = 'garbage_exhaust_fan_marker';category = 'M.equip'
        ref = source['source_page'].replace(':', ' ص') + ' موضع رمز أصلي؛ ARCH2 ص18 A1100 للأبعاد والمادة، مع Z وافتراضات موسومة.'
        if ref not in M['sp']:
            M['sp'].append(ref)
        els.append({'id': q['id'], 'c': category, 't': typ, 'l': q['level'], 'g': g,
                    'm': 'gc_graphic_unknown' if role == 'fan_marker' else 'gc_ss304',
                    's': [M['sp'].index(ref)], 'mark': TYPES[typ]['n'], 'a': a})
        count[role] += 1
    assert dict(count) == {'chute': 5, 'hopper': 5, 'vent': 1, 'fan_marker': 1}, count
    M.setdefault('meta', {})['garbage_chute_remaining'] = {
        **copy.deepcopy(D['summary']), 'by_role': dict(count),
        'source_data_sha256': hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
        'conflicts': copy.deepcopy(D['conflicts']), 'unbuilt_components': copy.deepcopy(D['unbuilt_components']),
        'scope_limit_ar': 'التحقق يثبت مواضع الرموز والأبعاد النصية المحددة. Z والفتحات والدعم والأجزاء السفلية والوصلات لا تزال غير معتمدة.'}
    if verbose:
        print('garbage chute source components:', sum(count.values()), dict(count))
    return dict(count)


apply = build
