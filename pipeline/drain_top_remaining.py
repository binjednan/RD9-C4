# -*- coding: utf-8 -*-
"""DR-105 top-roof stack terminations, from eleven actual plan circles.

python3 pipeline/drain_top_remaining.py writes extraction data only.
build(M, els) regenerates DTR elements in memory.  No plan riser is snapped to
the roof below: those two plans must supply independent positions.  The 1.5 m
height is the documented minimum, not an approved support/penetration detail.
"""
import collections
import json
import os
import re

import lib
import reg

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, 'data', 'drain_top_remaining.json')
ID_RE = re.compile(r'-DTR\d{4}$')
LAYERS = {'M_DR_WP': ('waste', 'pipe_waste', 'p_waste'),
          'M_DR_SP': ('soil', 'pipe_soil', 'p_soil'),
          'M_DR_VP': ('vent', 'vent_top_termination', 'p_vent')}
EXPECTED = {'waste': 5, 'soil': 3, 'vent': 3}
TYPES = {'vent_top_termination': {'n': 'نهاية قائم تهوية صرف فوق السطح العلوي', 'cf': 'doc',
    'sp': [['القطر', '4 بوصات (100 مم)'], ['الوظيفة', 'تهوية؛ لا يدخل في مسار تدفق مياه الصرف']],
    'sr': ['MECH2 ص8 DR-105، الملاحظتان4/5'],
    'asm': ['الارتفاع النهائي والتثبيت غير معطيين؛ التمثيل يستعمل الحد الأدنى1.5م فوقFFL']}}


def extract():
    sh = lib.Sheet('MECH2', 8)
    symbols = []
    for i, d in enumerate(sh.D):
        if d['layer'] not in LAYERS or len(d['polys']) != 1 or len(d['polys'][0]) != 41:
            continue
        r = d['rect']
        pdf = [(r[0] + r[2]) / 2, (r[1] + r[3]) / 2]
        xy = sh.T(*pdf)
        # The three plan leader groups lie in these two genuine top-roof shafts;
        # the separate legend is to their east and contains no plan instance.
        if not (900 < xy[0] < 2450 and 650 < xy[1] < 1150):
            continue
        w, h = (r[2] - r[0]) * sh.reg['s'], (r[3] - r[1]) * sh.reg['s']
        assert 10 < w < 12 and abs(w - h) < .01, (i, w, h)
        family, typ, material = LAYERS[d['layer']]
        symbols.append({'drawing_index': i, 'layer': d['layer'], 'family': family,
                        'type': typ, 'material': material, 'pdf_points': [pdf],
                        'xy': list(xy), 'diameter_mm': 100,
                        'symbol_diameter_cm': [w, h], 'source_transform': dict(sh.reg),
                        'source_graphic_colour_rgb': d.get('color')})
    count = collections.Counter(q['family'] for q in symbols)
    assert dict(count) == EXPECTED, count
    labels = []
    label_count = collections.Counter()
    # Two leader text blocks have no PDF layer.  Restricting labels to
    # M_DR_TEXT loses six real labels; the legend/general notes are excluded.
    for i, t in enumerate(sh.TX):
        names = re.findall(r'4"Ø (WASTE|SOIL|VENT) PIPE', t['s'])
        if not names:
            continue
        r = t['bbox']; xy = sh.T((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
        if not (800 < xy[0] < 2400 and 650 < xy[1] < 1100):
            continue
        labels.append({'text_index': i, 'layer': t['layer'], 'text': t['s'],
                       'bbox_pdf': list(r), 'xy': list(xy), 'names': names})
        label_count.update(n.lower() for n in names)
    assert dict(label_count) == EXPECTED, label_count
    page = lib.doc('MECH2')[7]
    drawings = [d for d in page.get_drawings() if d.get('layer') and
                ('GRID' in d['layer'].upper() or 'AXIS' in d['layer'].upper()) and
                'IDEN' not in d['layer'].upper()]
    vx, vy = reg.grid_clusters(None, layers=None, drawings=drawings, minlen=50)
    ax = [[x, x * sh.reg['s'] + sh.reg['ox'], min(reg.GX_list, key=lambda m: abs(m - (x * sh.reg['s'] + sh.reg['ox'])))] for x in vx]
    ay = [[y, -y * sh.reg['s'] + sh.reg['oy'], min(reg.GY_list, key=lambda m: abs(m - (-y * sh.reg['s'] + sh.reg['oy'])))] for y in vy]
    ax = [q for q in ax if abs(q[1] - q[2]) < 2]
    ay = [q for q in ay if abs(q[1] - q[2]) < 2]
    assert len(ax) >= 11 and len(ay) >= 6, (ax, ay)
    return {'source_set': 'MECH2', 'source_page': 8, 'sheet': 'DR-105',
            'registration': dict(sh.reg), 'registration_evidence': {'x_axes': ax, 'y_axes': ay,
                'max_residual_cm': max(abs(q[1] - q[2]) for q in ax + ay)},
            'symbols': symbols, 'label_inventory': labels,
            'symbol_counts': dict(count), 'label_counts': dict(label_count),
            'height_reference': 'DR general notes 4/5: vent pipes and drainage stacks terminate at least 1.5 m above finished roof/top roof.',
            'missing_reason': 'make_model and mep_bg never called extract_dr for MECH2:8; no old P.drain element was assigned to level T.'}


def build(M, els, verbose=False):
    els[:] = [e for e in els if not ID_RE.search(e['id'])]
    D = json.load(open(DATA, encoding='utf-8'))
    ffl = next(l['ffl'] for l in M['levels'] if l['id'] == 'T')
    source = 'MECH2 ص8 DR-105: 11 دائرة قائم 4″ حقيقية على السطح العلوي؛ الملاحظتان4/5 تحددان النهاية على الأقل1.5م فوق التشطيب. لم تستخرج الصفحة في النموذج القديم.'
    if source not in M['sp']:
        M['sp'].append(source)
    si = M['sp'].index(source)
    M.setdefault('types', {}).update(TYPES)
    count = collections.Counter()
    for i, q in enumerate(D['symbols'], 1):
        x, y = [round(v, 4) for v in q['xy']]
        a = {'sys': 'drain_top_vent' if q['family']=='vent' else 'drain_top',
             'no_connectors': True, 'source_kind': 'drawn_termination_circle',
             'flow_medium': 'vent_air' if q['family']=='vent' else 'waste_water',
             'kind': 'نهاية قائم صرف فوق السطح العلوي',
             'dia_mm': q['diameter_mm'], 'source_page': 'MECH2:8',
             'source_drawing': q['drawing_index'], 'source_layer': q['layer'],
             'source_pdf_points': q['pdf_points'], 'source_transform': q['source_transform'],
             'source_xy': q['xy'], 'source_anchor_kind': 'circle_centre',
             'drawn_ffl_m': ffl,
             'geometry_role': 'source_route_display',
             'material_status': 'not_specified_in_reviewed_source',
             'finish_status': 'not_specified_in_reviewed_source',
             'dimension_status': 'nominal_diameter_100mm_from_label',
             'elevation_status': 'minimum_height_from_note_local_ffl_derived',
             'physical_geometry_status': 'pending_final_height_mounting_and_penetration',
             'source_graphic_colour_rgb': q.get('source_graphic_colour_rgb'),
             'assumed': 'تمثيل النهاية من FFL السطح العلوي26.85م إلى الحد الأدنى1.5م فوقه وفق الملاحظتين4/5؛ طول التنفيذ النهائي وتفاصيل الحوامل والاختراق غير مرسومة. لا صاعد إلىR أو إزاحة لمركز الدائرة من أجل الربط.'}
        els.append({'id': f'P.drain-T-DTR{i:04d}', 'c': 'P.drain', 'l': 'T',
                    'g': ['t', [[x, y, ffl], [x, y, round(ffl + 1.5, 4)]], 10],
                    'mark': '4″ ' + q['family'].upper(), 't': q['type'],
                    'm': q['material'], 'a': a, 's': [si]})
        count[q['family']] += 1
    M.setdefault('meta', {})['drain_top_remaining'] = {'count': sum(count.values()),
        'by_family': dict(count), 'source': 'MECH2:8 DR-105', 'xy_snapping': False,
        'minimum_height_m': 1.5, 'mounting_detail_verified': False}
    if verbose:
        print('top roof drainage terminations:', dict(count))
    return dict(count)


if __name__ == '__main__':
    D = extract()
    with open(DATA, 'w', encoding='utf-8') as f:
        json.dump(D, f, ensure_ascii=False, indent=2); f.write('\n')
    print('DR-105 symbols / labels:', D['symbol_counts'], D['label_counts'])
