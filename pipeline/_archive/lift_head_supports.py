"""Two missing lift-head structural wall extensions from exact STR23 profiles.

The plan profiles are closed S-COL-HATCH line chains in the main roof plan.
Their vertical span is derived between source concrete datums: 23.15 to
24.00 - .25 = 23.75. No existing structural geometry or reinforcement changes.
"""
import copy
import hashlib
import json
import re
from pathlib import Path

DATA_PATH = Path(__file__).with_name('data') / 'lift_head_supports.json'
TYPES = {
    'lift_head_wall': {
        'n': 'امتداد جدار بئر المصعد عند الرأس', 'cf': 'derived',
        'sp': [['المسقط', 'حد خرسانة مغلق من STR23 / S-COL-HATCH'],
               ['القاع', 'CL +23.15 م'],
               ['القمة', '+23.75 م = CL24.00 − سماكة الغطاء25سم'],
               ['الارتفاع', '60 سم مشتق بين مرجعَي الخرسانة']],
        'sr': ['STR ص23 Roof Floor Slab Layout', 'ARCH2 ص17 A900 قطاع5'],
        'asm': ['تفصيل الارتكاز والاتصال والتسليح والمرابط غير مثبت؛ لا تسليح مختلق.'],
    },
}
MATS = {'lhs_concrete': {'name': 'خرسانة إنشائية — لون عرض محايد غير طلاء فعلي',
                         'color': '#c5c6c8', 'rough': .8}}


def _sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def build(M, els=None, verbose=False):
    els = M['els'] if els is None else els
    D = json.loads(DATA_PATH.read_text())
    old_s = {e['id']: copy.deepcopy(e) for e in els
             if e['c'].startswith('S.') and not re.search(r'-LHS\d{4}$', e['id'])}
    els[:] = [e for e in els if not re.search(r'-LHS\d{4}$', e['id'])]
    text = ('STR ص23: S-COL-HATCH رسم3489/3488 حدود خرسانة مغلقة لرأسي جداري البئرين؛ '
            'قاع23.15 من CL السطح، وقمة23.75 مشتقة من CL الغطاء24.00−سماكته25سم. '
            'ARCH2 ص17 A900 قطاع5 يؤكد الغطاء واستمرار البئر عبر منسوب السطح؛ '
            'تفصيل الارتكاز والاتصال والتسليح غير مثبت.')
    if text not in M['sp']:
        M['sp'].append(text)
    source_i = M['sp'].index(text)
    M['mats'].update(copy.deepcopy(MATS))
    for eid, row in D['records'].items():
        s = row['source']
        a = {
            'kind': 'lift_head_structural_extension',
            'source_kind': 'closed_structural_wall_outline',
            'source_page': s['source_page'], 'source_sheet': s['source_sheet'],
            'source_pdf_sha256': s['source_pdf_sha256'],
            'source_layer': s['source_layer'],
            'source_drawing_indices': copy.deepcopy(s['source_drawing_indices']),
            'source_poly_index': 0, 'source_pdf_points': copy.deepcopy(s['source_pdf_points']),
            'source_transform': copy.deepcopy(s['source_transform']),
            'source_xy': copy.deepcopy(s['source_xy']), 'source_locked_xy': True,
            'source_semantics_checked': True, 'source_structural_XY_verified': True,
            'source_Z_verified': False, 'source_height_derived': True,
            'source_height_basis': 'derived_between_confirmed_structural_datums',
            'source_z_proof': copy.deepcopy(row['datum_basis']),
            'source_bearing_verified': False, 'source_reinforcement_verified': False,
            'source_material_verified': True, 'source_physical_color_verified': False,
            'source_geometry_role': 'structural_wall_with_datum_derived_height',
            'lift_head_support_record': eid, 'extends_existing_id': row['lower_existing_id'],
            'height_cm': 60, 'structural_details_pending': True,
            'assumed': ('المنسوب الرأسي مشتق بين CL23.15 وأسفل الغطاء CL24.00−25سم؛ '
                        'لا ارتفاع مرقم للجدار نفسه. حدود الخرسانة الأفقية من STR فقط؛ '
                        'تفصيل الاتصال والارتكاز والتسليح والمرابط غير مثبت. اللون محايد للعرض.'),
        }
        els.append({'id': eid, 'c': 'S.wall', 'l': 'R', 'g': copy.deepcopy(row['g']),
                    't': 'lift_head_wall', 'm': 'lhs_concrete', 'mark': 'LIFT HEAD',
                    'grp': 'lift-head-source-structure', 'a': a, 's': [source_i]})
    existing_s_unchanged = all(old_s[e['id']] == e for e in els
                               if e['id'] in old_s)
    new = [e for e in els if e['id'] in D['records']]
    stats = {'generated': len(new), 'new_structural_ids': list(D['records']),
             'all_existing_S_unchanged': existing_s_unchanged,
             'geometry_sha256': _sha([(e['id'], e['g']) for e in new]),
             'data_sha256': hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
             'height_boundaries': D['height_boundaries_ar'], 'pending': D['pending_ar'],
             'scope_authorization': D['authorization_ar']}
    M.setdefault('meta', {})['lift_head_supports'] = stats
    if verbose:
        print('LHS:', len(new), 'old S unchanged:', existing_s_unchanged)
    return stats
