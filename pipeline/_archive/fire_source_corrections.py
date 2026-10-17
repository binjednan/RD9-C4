# -*- coding: utf-8 -*-
"""Correct a verified double-line FFC outline after the MEP merge.

The source draws the two faces of one 6-inch route. Preserve the first model
identity, reconstruct only its source midpoint, and remove the duplicate face.
Z remains the existing ceiling-route assumption. Structural geometry is never
changed; its derived identity card separates the planted G column from C1.
"""
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data', 'fire_source_corrections.json')
TYPES = {
    'col_planted_G_upper_C9': {
        'n': 'عمود مزروع بالأرضي / C9 في الأدوار العليا', 'cf': 'derived',
        'sp': [['هوية الأرضي', 'شكل PLANTED COLUMN الأبيض في S-11؛ لا يحمل وسم C1 مستقلًا'],
               ['شاهد الأدوار العليا', 'S-12 / S-13: المستطيل نفسه مهشّر/مصمت بعلامة C9'],
               ['المقاس', 'هندسة المسقط نحو160×20 سم؛ جدول C9 كذلك160×20 سم'],
               ['حد الاستدلال', 'ربط هوية العمود مشتق من تطابق المسقط، دون تحقق مستقل لتسليح العمود المزروع أو تفصيل زرعه']],
        'sr': ['STR ص16 S-11 رسم2095 ومفتاح PLANTED COLUMN',
               'STR ص17 S-12 رسم1212 وهاتش1753–1772',
               'STR ص18 S-13 رسم1075؛ STR ص25 S-20 جدول C9'],
    },
}


def build(M, els):
    with open(DATA, encoding='utf-8') as handle:
        data = json.load(handle)
    q = data['ffc_ground']
    by_id = {e['id']: e for e in els}
    keep, duplicate = by_id.get(q['keep_id']), by_id.get(q['remove_id'])
    if keep is not None:
        if keep['c'] != 'P.ff' or keep['g'][0] != 't':
            raise ValueError('FFC source correction requires the identified P.ff tube')
        # This correction is invoked after the MEP merge, so the source geometry
        # is rebuilt on every post pass. The existing Z assumption is retained.
        z_values = [float(p[2]) for p in keep['g'][1]]
        if max(z_values)-min(z_values) > 1e-8:
            raise ValueError('FFC source correction requires a uniform route Z')
        z = z_values[0]
        keep['g'] = ['t', [[x, y, z] for x, y in q['centreline_xy_cm']], 15.0]
        a = keep.setdefault('a', {})
        a.update(sys='fire', dia_mm=150, source_size='6″ FFC LINE',
                 source_kind='centreline_from_two_pipe_faces',
                 source_reference=q['source_reference'], source_page=11,
                 source_drawing_indices=q['source_drawing_indices'],
                 source_pdf_points=copy.deepcopy(q['source_pdf_points']),
                 source_xy=copy.deepcopy(q['source_xy']),
                 source_transform=copy.deepcopy(q['source_transform']),
                 source_layer='M_FF_FFC',
                 source_route_group=q['source_route_group'],
                 assumed='منسوب محور FFC4.00م افتراض فراغ سقف قائم؛ المصدر يثبت المسقط وقطر6″ ولا يحدد المنسوب.',
                 source_correction='دُمج وجها أنبوب6″ المرسومان إلى محور واحد؛ حُذف الجسم الثاني الذي كان يمثل الوجه الآخر.',
                 source_size_note='6″ قطر اسمي؛ قطر العرض150مم، وفاصل وجهي رمز المسقط14.86سم تقريبًا.',
                 length_m=round(sum(((b[0]-a0[0])**2+(b[1]-a0[1])**2)**.5 for a0,b in zip(q['centreline_xy_cm'],q['centreline_xy_cm'][1:]))/100, 3))
        keep['q'] = 'daa'
        if duplicate is not None:
            if duplicate['c'] != 'P.ff':
                raise ValueError('FFC duplicate identity belongs to a different category')
            els[:] = [e for e in els if e['id'] != q['remove_id']]
        M.setdefault('meta', {})['fire_source_corrections'] = {
            'source_reference': q['source_reference'],
            'keep_id': q['keep_id'], 'remove_id': q['remove_id'],
            'source_route_count': 1, 'source_drawing_indices': q['source_drawing_indices'],
            'before': q['before'], 'after': {'geometry': copy.deepcopy(keep['g'])},
            'removed_model_face_ids': [q['remove_id']],
            'z_assumed_m': z, 'geometry_source_data': 'pipeline/data/fire_source_corrections.json',
        }
    col = by_id.get(data['planted_column']['id'])
    if col is not None:
        # Correct only its identity card: preserve category, material, geometry,
        # source-list indices and structural dimensions exactly.
        col['mark'] = 'PC G / C9 upper'
        col['t'] = 'col_planted_G_upper_C9'
        col.setdefault('a', {}).update(
            source_identity_kind='derived_from_planted_and_upper_column_plans',
            source_identity_reference=data['planted_column']['source_reference'],
            source_identity_note='الأفقي الأبيض عمود مزروع؛ C1 المجاور يخص العمود الرأسي. الأدوار العليا تحسم هوية الأفقي C9؛ لم تتغير هندسة S.',
            source_identity_bounds_cm=copy.deepcopy(data['planted_column']['bounds_cm']),
            source_identity_caveat='لم يتحقق تفصيل زرع/تسليح هذه الهوية استقلالًا؛ لا تُعمم بطاقة C9 على العمود الرأسي المجاور.',
        )
    M.setdefault('types', {}).update(copy.deepcopy(TYPES))
    return els
