"""Source bounded architectural lift cover; existing structural bodies stay intact.

A105 gives a closed architectural cover and three upstands. STR23 establishes
concrete level +24.00 and 25 cm thickness, but has no closed slab perimeter.
The hybrid cover is therefore A.detail, never a verified structural S.slab.
The 17 cm assembly below F12 is deliberately left without a fabricated body.
"""
import copy
import hashlib
import json
import re
from pathlib import Path

DATA_PATH = Path(__file__).with_name('data') / 'roof_lift_source.json'
TYPES = {
    'lift_roof_arch_cap': {
        'n': 'غطاء رأس المصعدين — تمثيل معماري مشتق', 'cf': 'derived',
        'sp': [['المسقط', 'حد A105 المعماري 440×240 سم تقريبًا'],
               ['قمة الخرسانة', '+24.00 م — STR23'], ['السماكة', '25 سم — STR23']],
        'sr': ['ARCH1 ص8 A105', 'STR ص23', 'ARCH2 ص17 A900 قطاع5'],
        'asm': ['حدود الارتكاز والبروز الإنشائي غير مثبتة؛ لا يُعد جسم S.slab معتمدًا.'],
    },
    'lift_roof_source_upstand': {
        'n': 'دروة غطاء المصعدين — حد A105', 'cf': 'derived',
        'sp': [['قمة الدروة', '+24.65 م — A900'],
               ['فوق التشطيب', '45 سم'], ['السماكة', 'نحو20 سم من حدّي المسقط']],
        'sr': ['ARCH1 ص8 A105', 'ARCH2 ص17 A900 قطاع5'],
        'asm': ['المادة والتشطيب التنفيذي غير محددين؛ لون العرض تحليلي محايد.'],
    },
}
MATS = {
    'srf_concrete_source': {'name': 'خرسانة غطاء المصدر؛ لون عرض محايد',
                            'color': '#c5c6c8', 'rough': .8},
    'srf_upstand_unknown': {'name': 'دروة — المادة غير محددة في المصدر',
                            'color': '#c5c6c8', 'rough': .8},
}


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':')).encode()).hexdigest()


def _prism(points, bottom, top):
    return ['p', [[round(x, 4), round(y, 4)] for x, y in points], bottom, top, None]


def _rectangle(x0, y0, x1, y1):
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def build(M, els=None, verbose=False):
    """Run before arch_remaining.build so F12 excludes this higher roof cover."""
    els = M['els'] if els is None else els
    D = json.loads(DATA_PATH.read_text())
    P = D['sources']['architectural_plan']
    section = D['sources']['lift_section']
    original_s_hash = _hash([e for e in els if e['c'].startswith('S.')])
    # Recreated deterministically: extras may regenerate the same false roof
    # landing at every pass. Remove only its explicitly audited identities.
    expected = {r['id']: r for r in D['removed_roof_landing']}
    removed, mismatched = [], []
    retained = []
    for e in els:
        row = expected.get(e['id'])
        if row:
            if (e['c'], e['t'], e['l']) == (row['category'], row['type'], row['level']):
                removed.append(e['id'])
                continue
            mismatched.append(e['id'])
        if not re.search(r'-SRF\d{4}$', e['id']):
            retained.append(e)
    els[:] = retained
    source = ('ARCH1 ص8 A105: غطاء TOP LIFT عند +24.20 وحدّاه الخارجي والداخلي؛ '
              'ARCH2 ص17 A900 قطاع5: دروة +24.65 ومعدات البئر أسفل الغطاء، دون توقف سطح؛ '
              'STR ص23: CL +24.00 و25cm THICK SLAB؛ ARCH1 ص18 A500 صفK: F12 بلاط خرساني3سم. '
              'حد الغطاء المعماري لا يثبت حدود ارتكاز بلاطة STR.')
    if source not in M['sp']:
        M['sp'].append(source)
    source_i = M['sp'].index(source)
    # Remove the inaccurate roof-stop claim from surviving car metadata and
    # its shared source statement, preserving actual car/shaft geometry.
    for e in els:
        if e.get('a', {}).get('stops') == 'B,G,1–5,R':
            e['a']['stops'] = 'B,G,1–5'
            e['a']['source_stops_corrected'] = 'A105 / A900 قطاع5: لا توقف سطح مرسوم'
    old_source = ('ARCH2 ص17 (A900 تفاصيل المصاعد): مصعدان متجاوران، فتحة إنشائية للباب '
                  'ارتفاعها 230 سم، توقفات B وG و1–5 والسطح')
    new_source = ('ARCH2 ص17 (A900 تفاصيل المصاعد): مصعدان متجاوران، فتحة إنشائية للباب '
                  'ارتفاعها230سم؛ التوقفات المرسومة B وG و1–5. غطاء البئر +24.20؛ لا توقف سطح.')
    for i, text in enumerate(M['sp']):
        if text == old_source:
            M['sp'][i] = new_source
    M['mats'].update(copy.deepcopy(MATS))
    outer, inner = P['outer_boundary_xy'], P['inner_boundary_xy']
    x0, y0 = outer[0]
    x1, y1 = outer[2]
    ix0, iy0 = inner[0]
    _, iy1 = inner[2]
    parts = [
        ('A.detail', outer, 23.75, 24.00, 'lift_roof_arch_cap', 'srf_concrete_source',
         'hybrid_architectural_cap', 'architectural_outer_boundary'),
        ('A.floor', inner, 24.17, 24.20, 'floor_F12', 'fin_F12',
         'roof_finish', 'architectural_inner_boundary'),
        ('A.wall', _rectangle(x0, y0, ix0, y1), 24.00, 24.65,
         'lift_roof_source_upstand', 'srf_upstand_unknown', 'roof_upstand', 'left_outer_minus_inner'),
        ('A.wall', _rectangle(ix0, y0, x1, iy0), 24.00, 24.65,
         'lift_roof_source_upstand', 'srf_upstand_unknown', 'roof_upstand', 'south_outer_minus_inner'),
        ('A.wall', _rectangle(ix0, iy1, x1, y1), 24.00, 24.65,
         'lift_roof_source_upstand', 'srf_upstand_unknown', 'roof_upstand', 'north_outer_minus_inner'),
    ]
    new_ids = []
    for n, (cat, points, bottom, top, typ, mat, kind, part) in enumerate(parts, 1):
        eid = f'{cat}-R-SRF{n:04d}'
        a = {
            'kind': kind, 'source_kind': 'derived_from_architectural_boundary',
            'source_page': P['source_page'], 'source_sheet': P['source_sheet'],
            'source_pdf_sha256': P['source_pdf_sha256'],
            'source_drawing_indices': P['source_drawing_indices'],
            'source_pdf_points': copy.deepcopy(P['source_pdf_points']),
            'source_transform': copy.deepcopy(P['source_transform']),
            'source_xy': copy.deepcopy(points), 'source_boundary_part': part,
            'source_locked_xy': True, 'source_Z_verified': True,
            'source_structural_extent_verified': False,
            'source_geometry_role': 'hybrid_architectural_cap' if n == 1 else 'source_boundary_finish_or_upstand',
            'source_semantics_checked': True, 'roof_lift_source_record': n,
            'source_z_proof': (D['sources']['structural_level_and_depth'] if n == 1
                               else section if n >= 3 else P['source_ffl']),
            'unknown_assembly_gap_cm': 17,
            'assumed': ('حد العرض المعماري من A105؛ امتداد بلاطة STR وارتكازها غير مثبتين. '
                        'طبقات17سم بين قمة الخرسانة24.00 وأسفل F12 عند24.17 غير مفصلة ولم يُنشأ لها جسم. '
                        'مادة الدروة وتشطيبها التنفيذي غير محددين؛ اللون محايد للعرض.'),
        }
        if n == 1:
            a['source_thickness_verified_cm'] = 25
        elif n == 2:
            a.update({'fin': ['F12'], 'drawn_ffl_m': 24.20,
                      'source_finish_code': 'ARCH1:18 A500 row K / F12',
                      'source_thickness_verified_cm': 3})
        else:
            a['above_local_ffl_cm'] = 45
        els.append({'id': eid, 'c': cat, 'l': 'R', 'g': _prism(points, bottom, top),
                    't': typ, 'm': mat, 'mark': 'TOP LIFT', 'grp': 'top-lift-roof-source',
                    'a': a, 's': [source_i]})
        new_ids.append(eid)
    s_unchanged = original_s_hash == _hash([e for e in els if e['c'].startswith('S.')])
    stats = {'generated': len(parts), 'new_ids': new_ids,
             'removed_roof_landing': list(expected), 'last_removed_roof_landing': removed,
             'roof_landing_identity_mismatches': mismatched, 'existing_S_unchanged': s_unchanged,
             'geometry_sha256': _hash([(e['id'], e['g']) for e in els if e['id'] in new_ids]),
             'data_sha256': hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
             'local_ffl_before_m': 23.35, 'local_ffl_after_m': 24.20,
             'pending': D['pending_ar'], 'source_differences': D['source_differences']}
    M.setdefault('meta', {})['roof_lift_source'] = stats
    if verbose:
        print('SRF:', stats['generated'], 'removed false roof landing:', len(removed),
              'existing S unchanged:', s_unchanged)
    return stats
