# -*- coding: utf-8 -*-
"""Restore only the 89 P1 piles' literal diameter and design length.

The later user authorization supersedes the earlier S.* geometry freeze for
this correction. XY is preserved after a raw-plan comparison within 0.2 cm.
The head stays at the derived PC1 underside, not a verified cutoff/embedment.
"""
import copy
import hashlib
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data', 'structural_source_restore.json')
TYPES = {
    'pile': {
        'n': 'خازوق P1 — قطر60 سم وطول تصميم13 م', 'cf': 'derived',
        'sp': [['القطر النصي', '0.6m — P1 في PILE DETAILS / S-7'],
               ['طول التصميم النصي', 'Pile length = 13m في S-7'],
               ['التسليح النصي', '10T16 main steel / T10 spiral؛ يعاد تصميمه من شركة الخوازيق'],
               ['مواضع المسقط', '89 دائرة في طبقة PILES$0$ST-PILE؛ مقارنة مراكز مستقلة عن النصوص'],
               ['قمة جسم العرض', '−5.40م مشتقة من −3.90م وسماكة PC1 مقدار150سم؛ ليست منسوب قطع مثبتًا'],
               ['قاع جسم العرض', '−18.40م مشتق من مرجع القمة الحالي وطول13م'],
               ['الخلطة والتشطيب واللون', 'غير محددة في نص تفاصيل الخوازيق المراجع؛ العرض المحايد لا يعتمد مادة أو لونًا']],
        'asm': ['منسوب الرأس عند أسفل PC1 حد تمثيل مشتق. غرس الرأس داخل القبعة مرسوم دون بعد رقمي؛ لا يثبت منسوب القطع أو عمق الغرس.',
                'طول13م نص تصميم؛ لا يثبت الطول المنفذ أو اعتماد إعادة التصميم المطلوبة من شركة الخوازيق.',
                'العينة تعرض عدد10 وأقطارT16/T10 فقط من النص؛ ترتيب القضبان وغطاؤها وخطوة الحلزون وأطوال الرباط تمثيلية عند غياب أبعادها.'],
        'sr': ['STR ص11 / S-7 / PILE DETAILS / S-ANNO-TE texttrace115',
               'STR ص11 / S-7 / PILES$0$ST-PILE دوائر P1',
               'STR ص12 / S-8 / SECTION1-B PC1 — منسوب السطح والسماكة؛ الغرس غير مرقم'],
    },
}


def apply(M, els=None):
    """Mutate the identified pile bodies only; return a reviewable change log."""
    if els is None:
        els = M['els']
    with open(DATA, encoding='utf-8') as handle:
        data = json.load(handle)
    if len(data['piles']) != 89 or data['pile_count'] != 89:
        raise ValueError('P1 source correction requires exactly 89 source identities')
    by_id = {e['id']: e for e in els}
    before_struct = {e['id']: copy.deepcopy(e['g']) for e in els if e['c'].startswith('S.')}
    wanted = {q['id'] for q in data['piles']}
    if not wanted.issubset(by_id):
        raise ValueError('P1 source correction is missing identified model piles')
    length_m = float(data['length_literal']['value'])
    radius_cm = float(data['diameter_literal']['value']) / 2
    changes, max_xy = [], 0.0
    for q in data['piles']:
        e = by_id[q['id']]
        if e['c'] != 'S.pile' or e['l'] != 'B' or e['g'][0] != 'cyl':
            raise ValueError('P1 source identity is not a basement pile cylinder: ' + e['id'])
        old = copy.deepcopy(e['g'])
        delta = math.hypot(old[1] - q['source']['source_xy'][0], old[2] - q['source']['source_xy'][1])
        if delta > data['source_tolerance_cm'] + 1e-9:
            raise ValueError('P1 existing XY exceeds its source comparison: ' + e['id'])
        if abs(old[5] - data['z_basis']['pile_head_model_m']) > 1e-9:
            raise ValueError('P1 head anchor changed; verify its source basis: ' + e['id'])
        max_xy = max(max_xy, delta)
        e['g'] = ['cyl', old[1], old[2], radius_cm, round(old[5] - length_m, 6), old[5]]
        e['t'] = 'pile'
        a = e.setdefault('a', {})
        a.update(
            dia_cm=radius_cm * 2, len_m=length_m,
            source_kind='drawn_pile_circle_derived_center', source_page='STR:11', source_sheet='S-7',
            source_reference='STR ص11 S-7 دوائر P1 وPILE DETAILS؛ STR ص12 S-8 SECTION1-B PC1 للمرجع المشتق',
            source_pdf_sha256=data['source_pdf_sha256'], source_layer=q['source']['layer'],
            source_drawing_indices=copy.deepcopy(q['source']['drawing_indices']),
            source_pdf_points=copy.deepcopy(q['source']['source_pdf_points']),
            source_pdf_center=copy.deepcopy(q['source']['pdf_center']),
            source_xy=copy.deepcopy(q['source']['source_xy']),
            source_transform=copy.deepcopy(data['source_transform']),
            source_center_method=q['source']['center_method'],
            source_xy_comparison_cm=delta,
            source_xy_tolerance_cm=data['source_tolerance_cm'],
            source_length_verified=True, source_diameter_verified=True,
            source_length_literal=copy.deepcopy(data['length_literal']),
            source_diameter_literal=copy.deepcopy(data['diameter_literal']),
            source_reinforcement_literal=data['reinforcement_literal'],
            source_z_top_basis='cap_underside_derived_embedment_unverified',
            source_z_bottom_basis='derived_head_anchor_minus_literal_design_length',
            source_height_assumed=True, source_head_embedment_status='not_dimensioned_in_reviewed_section',
            source_material_status='pile_concrete_mix_not_specified_in_reviewed_pile_detail',
            source_finish_status='not_specified_in_reviewed_pile_detail',
            source_physical_color_status='not_specified_in_reviewed_pile_detail',
            assumed='قمة جسم الخازوق−5.40م حد تمثيل مشتق من أسفل PC1 (سطح−3.90م، سمك150سم). غرس الرأس داخل القبعة غير مرقم؛ القاع−18.40م مشتق من هذه القمة وطول التصميم13م. لا إثبات لمنسوب القطع أو التنفيذ الميداني.',
            display_note='استعيد طول التصميم13م وقطر60سم من نص S-7؛ الموضع XY والقمة الحالية محفوظان. طول30سم القديم كان اختزال عرض، وليس طول المخطط.',
        )
        a.pop('source_Z_verified', None)
        a.pop('source_z_verified', None)
        changes.append({'id': e['id'], 'before_geometry': old, 'after_geometry': copy.deepcopy(e['g']),
                        'geometry_changed': old != e['g'], 'delta_xy_cm': delta,
                        'source_drawing_indices': copy.deepcopy(q['source']['drawing_indices']),
                        'z_basis': 'derived_head_anchor; cutoff_and_embedment_unverified'})
    others = [e['id'] for e in els if e['c'].startswith('S.') and e['id'] not in wanted and e['g'] != before_struct[e['id']]]
    if others:
        raise AssertionError('P1 correction changed other structural geometry: ' + ', '.join(others))
    M.setdefault('types', {}).update(copy.deepcopy(TYPES))
    stats = {'pile_count': len(changes), 'geometry_changed': sum(q['geometry_changed'] for q in changes),
             'max_delta_xy_cm': max_xy, 'other_structural_geometry_changes': 0,
             'source_data': 'pipeline/data/structural_source_restore.json',
             'source_data_sha256': hashlib.sha256(open(DATA, 'rb').read()).hexdigest(),
             'adoption': copy.deepcopy(data['adoption']), 'z_basis': copy.deepcopy(data['z_basis']),
             'changes': changes}
    M.setdefault('meta', {})['structural_source_restore'] = copy.deepcopy(stats)
    return stats
