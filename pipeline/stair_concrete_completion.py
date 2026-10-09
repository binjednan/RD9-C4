# -*- coding: utf-8 -*-
"""Bind exact STR/A500/BOQ source facts and record a stair profile discrepancy.

No source geometry is invented and no model file IO occurs. Call after the
stair_completion surface layer. Only a dedicated nested attribute and this
module's own meta entry / drawing issues are owned by this module.
"""
import copy
import hashlib
import json
from pathlib import Path

DATA_PATH = Path(__file__).with_name('data') / 'stair_concrete_completion.json'
DATA_SHA256 = '1a52346a1afd74f71765c7f851d330f2d98dc80e7306813cb7a7ae8329368c60'
ATTRIBUTE = 'source_stair_concrete_review'
META = 'stair_concrete_completion'


def data(verify_files=True):
    raw = DATA_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DATA_SHA256:
        raise ValueError('Stair concrete source ledger changed')
    D = json.loads(raw)
    if verify_files:
        for source in D['sources'].values():
            if hashlib.sha256(Path(source['path']).read_bytes()).hexdigest() != source['sha256']:
                raise ValueError('Stair concrete original PDF changed: ' + source['file'])
    return D


def _review(r):
    return {**copy.deepcopy(r['review']), 'source_data_sha256': DATA_SHA256}


def _preflight(M, D):
    by = {}
    for e in M['els']:
        if e['id'] in by:
            raise ValueError('Stair concrete duplicate identity: ' + e['id'])
        by[e['id']] = e
    states = []
    for eid, r in D['records'].items():
        e = by.get(eid)
        if e is None:
            raise ValueError('Stair concrete identity missing: ' + eid)
        for key, val in r['before_identity'].items():
            if e.get(key) != val:
                raise ValueError('Stair concrete source identity/geometry changed: ' + eid + '/' + key)
        if e.get('a', {}).get('stair_completion_data_sha256') != r['required_source_surface_sha256']:
            raise ValueError('Stair concrete requires reviewed finished surfaces: ' + eid)
        existing = e.get('a', {}).get(ATTRIBUTE)
        if existing is not None and existing != _review(r):
            raise ValueError('Stair concrete unknown evidence state: ' + eid)
        states.append(existing is not None)
    if len(set(states)) > 1:
        raise ValueError('Stair concrete partial evidence state')
    return by, all(states)


def apply(M, els=None):
    if els is not None and els is not M['els']:
        raise ValueError('Stair concrete pass model elements by identity')
    D = data()
    by, final = _preflight(M, D)
    # Complete preflight precedes all writes. Geometry, material assignment,
    # existing verification flags and all unrelated evidence stay byte-for-byte.
    for eid, r in D['records'].items():
        by[eid].setdefault('a', {})[ATTRIBUTE] = _review(r)
    stats = {**copy.deepcopy(D['summary']), 'data_sha256': DATA_SHA256,
             'controlled_ids': list(D['records']),
             'retired_indices': [], 'old_to_new_indices': {i: i for i in range(len(M['els']))}}
    M.setdefault('meta', {})[META] = {k: v for k, v in stats.items()
                                    if k not in ('retired_indices', 'old_to_new_indices')}
    return {**stats, 'evidence_bound_this_apply': 0 if final else len(D['records'])}


def issue_records(M):
    D = data()
    _, final = _preflight(M, D)
    if not final:
        raise ValueError('Stair concrete issues require bound source evidence')
    ids = list(D['records'])
    shared = {'level': 'G', 'xy_cm': None, 'z_m': None, 'elements': ids}
    return [
        {**shared, 'id': 'DP-STAIR-CONCRETE-G-SOURCE-PROPERTIES',
         'title': 'ربط خواص خرسانة وتشطيب درج01 الأرضي بالمصادر الأصلية',
         'status': 'corrected', 'source': 'STR ص29 S-24؛ A500؛ BOQ ص9 PDF',
         'note': 'ثبتت خواص مكتوبة: خصر25سم عمودي على الميل، وبسطات25سم رأسيًا، '
                 'وCL−.10/+2.05/+3.85/+5.65، ونصوص6T16/M و6T10/M وT10/STEP و5T8/m. '
                 'F10 جرانيت3سم للنائمة والبسطة و2سم للقائمة بحسبBOQ. '
                 'ربطت هذه الخواص بخمسة تجميعات؛ لم تنشأ أجسام خرسانة أو قضبان أو اتصال ارتكاز، '
                 'ولم تصبح تسمية المادة دليلًا على منتج منفذ أو معتمد.',
         'before': {'source_concrete_specification_bound': False},
         'after': copy.deepcopy(D['summary'])},
        {**shared, 'id': 'DP-STAIR-CONCRETE-G-SECTION-PLAN',
         'title': 'قطاع الخرسانة يرسم13 قائمة مقابل11 في مسقط درج01 الأرضي',
         'status': 'source_conflict', 'source': 'STR ص29 S-24 / ص21 S-16؛ ARCH2 A600/A601',
         'note': 'الرحلة منCL+3.85 إلى+5.65 في قطاعS-24 الموسومNTS ترسم13 قائمًا؛ '
                 'مسقطS-16 يرقمها23…33 أي11، موافقًا لأسطحA600/A601. '
                 'سجل الاختلاف بين رسم القطاع والمسقط دون مساواة القوائم أو استنتاج عدد من السماكة. '
                 'لذلك لم يركب جسم خصر على أسطح ذات عدد مختلف، واستمرت مطابقة بقية الخواص المكتوبة.',
         'before': {'source_section_graphic_risers': 13},
         'after': {'source_plan_numbered_risers': 11, 'comparison_result_ar': 'تعارض مسجل',
                   'source_graphics_reconciled': False, 'body_geometry_added': False}},
        {**shared, 'id': 'DP-STAIR-CONCRETE-G-BODY-EXTENTS',
         'title': 'حدود جسم وارتكاز السلم لا تكتمل من خواص المقطع وحدها',
         'status': 'source_gap', 'source': 'STR S-24 وS-16 / ARCH2 A600/A601',
         'note': '25سم سماكة خصر عمودية على الميل وليست إزاحة رأسية لجميع النائمات. '
                 'فرقFFL−CL عند الأرضي45سم، وعندالبسطتين والأول10سم؛ فلا تطرح10سم من كل نقطة. '
                 'المسقط يبينB2 والجدارين الجانبيين، لكنه لا يغلق محيط خرسانة البسطتين مع طول الارتكاز. '
                 'لم يتحول محيط التشطيب إلى صندوق خرسانة. نصوص التسليح محفوظة دون أطوال تثبيت أو أجسام قضبان.',
         'before': None,
         'after': {'concrete_levels_m': [-.1, 2.05, 3.85, 5.65],
                   'finished_levels_m': [.35, 2.15, 3.95, 5.75],
                   'finished_minus_concrete_cm': [45, 10, 10, 10],
                   'landing_top_bottom_m': [[2.05, 1.8], [3.85, 3.6]],
                   'full_body_coordinates_matched': False, 'physical_acceptance': False}}
    ]


def apply_issues(M):
    rows = issue_records(M)
    owned = {r['id'] for r in rows}
    issues = M.setdefault('drawingIssues', [])
    issues[:] = [r for r in issues if r['id'] not in owned] + rows
    return {'owned_issue_ids': sorted(owned), 'source_conflicts': 1,
            'geometry_changes': 0, 'physical_acceptance': False}


def _serial(it):
    if it[0] == 'l':
        return ['l', list(it[1]), list(it[2])]
    if it[0] == 'qu':
        return ['qu', [list(p) for p in it[1]]]
    if it[0] == 're':
        return ['re', list(it[1]), it[2]]
    return [it[0], *[list(p) for p in it[1:]]]


def source_replay(D=None, verify_images=True):
    import fitz
    D = data() if D is None else D
    docs = {key: fitz.open(source['path']) for key, source in D['sources'].items()}
    pages = {}
    drawings, texts, annotations = {}, {}, {}
    checks = []
    def page(key, n):
        if (key, n) not in pages:
            pages[key, n] = docs[key][n - 1]
        return pages[key, n]
    try:
        for row in D['raw_drawings']:
            k = row['source'], row['page']
            if k not in drawings:
                drawings[k] = page(*k).get_drawings()
            d = drawings[k][row['drawing_index']]
            ok = (d.get('layer') == row['layer'] and d['type'] == row['type'] and
                  d.get('closePath') == row['closePath'] and
                  [_serial(it) for it in d['items']] == row['items'])
            checks.append({'ref': f'{k}:drawing{row["drawing_index"]}', 'pass': ok})
        for row in D['raw_texts']:
            k = row['source'], row['page']
            if k not in texts:
                texts[k] = page(*k).get_texttrace()
            t = texts[k][row['texttrace_index']]
            ok = (''.join(chr(c[0]) for c in t['chars']) == row['literal'] and
                  list(t['bbox']) == row['bbox'] and
                  [{'unicode': c[0], 'origin': list(c[2]), 'bbox': list(c[3])}
                   for c in t['chars']] == row['chars'])
            checks.append({'ref': f'{k}:text{row["texttrace_index"]}', 'pass': ok})
        for row in D['raw_annotations']:
            k = row['source'], row['page']
            if k not in annotations:
                annotations[k] = list(page(*k).annots())
            a = annotations[k][row['annotation_index']]
            ok = (a.xref == row['xref'] and list(a.rect) == row['rect'] and
                  a.info.get('content') == row['literal'])
            checks.append({'ref': f'{k}:annotation{row["annotation_index"]}', 'pass': ok})
        for row in D['source_renderings'] if verify_images else []:
            pix = page(row['source'], row['source_page']).get_pixmap(
                matrix=fitz.Matrix(row['matrix_scale'], row['matrix_scale']),
                clip=fitz.Rect(row['clip_pdf_pt']), alpha=False, annots=row['annots'])
            ok = hashlib.sha256(pix.tobytes('png')).hexdigest() == row['png_sha256']
            checks.append({'ref': Path(row['file']).name, 'pass': ok})
        d = D['section_plan_discrepancy']
        p = drawings['STR', 29]
        segments = []
        for r in d['section_risers']:
            op = p[r['drawing_index']]['items'][r['operator_index']]
            segments.append(op)
        count_ok = (len(segments) == 13 and
                    len({tuple(op[1]) for op in segments}) == 13 and
                    all(op[0] == 'l' and abs(op[1].x - op[2].x) < .001 for op in segments))
        values = [int(''.join(chr(c[0]) for c in texts['STR', 21][i]['chars']))
                  for i in d['plan_texttrace_indices']]
        checks.append({'ref': 'original_segment_count13_vs_numbered_plan11',
                       'pass': count_ok and values == list(range(23, 34))})
        line = p[7088]['items'][0]
        slope = p[6541]['items'][0]
        u, v = line[2] - line[1], slope[2] - slope[1]
        dot = (u.x * v.x + u.y * v.y) / (abs(u) * abs(v))
        checks.append({'ref': 'waist_dimension_normal_not_vertical',
                       'pass': abs(dot) < .005 and abs(u.x) > 1 and abs(u.y) > 1,
                       'normalized_dot': dot})
    finally:
        for doc in docs.values():
            doc.close()
    return checks


def audit(M, replay_source=True, verify_images=True):
    D = data()
    _, final = _preflight(M, D)
    checks = source_replay(D, verify_images=verify_images) if replay_source else []
    failures = [r['ref'] for r in checks if not r['pass']]
    if not final:
        failures.append('source evidence not bound')
    return {'pass': not failures, 'global_findings': failures, 'source_checks': checks,
            'source_data_sha256': DATA_SHA256, 'summary': copy.deepcopy(D['summary']),
            'whole_body_matching_ar': 'تعارض مسجل',
            'source_conflicts_resolved': False, 'geometry_changes': 0}
