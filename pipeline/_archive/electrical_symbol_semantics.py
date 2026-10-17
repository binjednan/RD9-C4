# -*- coding: utf-8 -*-
"""Correct reviewed electrical glyph semantics after legacy XY restoration.

Only deterministic PDF primitive identities in the companion data authorize a
change. Annotation fragments are removed; real glyphs receive their drawn XY.
Graphic footprint, physical enclosure and mounting elevation stay distinct.
This module does not alter supports, route tolerances or other disciplines.
"""
import collections
import copy
import hashlib
import json
import os

DATA = os.path.join(os.path.dirname(__file__), 'data', 'electrical_symbol_semantics.json')
XY_GUESS_KEYS = ('guess_from', 'guess_host', 'guess_kind', 'guess_cm', 'guess_dz_cm',
                 'guess_conf', 'guess_intent', 'guess_conv', 'snap_cm', 'snap_note')
TYPES = {
    'e_P17': {
        'n': 'لوحة توزيع (DB)', 'cf': 'derived',
        'sp': [['الدلالة', 'Distribution board (DB)؛ رمز المخطط ومسمّيات DB'],
               ['مادة الغلاف والتشطيب', 'غير محددين في المصادر المراجعة؛ لون رمز CAD ليس طلاء الجهاز'],
               ['غلاف العرض', '40×15×60 سم: تمثيل افتراضي؛ ليس مقاسًا عامًا مثبتًا لكل DB-F/DB-E'],
               ['منسوب العرض', 'القاع FFL+1.20م والقمة FFL+1.80م: تمثيل مشتق من تفصيل DB-S']],
        'sr': ['ELEC1 ص11–12 مفتاح القوى، Distribution board (DB)',
               'ELEC1 ص18 EP-109: واجهة DB-S بعرض40 وارتفاع60 سم والقمة180 سم فوق FFL'],
        'asm': ['مقاس DB-F/DB-E وعمق15 سم ومنسوب تركيبهما يحتاجان جدول المصنّع/التفصيل النوعي؛ تفصيل DB-S لا يثبتها.'],
    },
    'e_T5': {
        'n': 'مبدّل إنتركم صوت وصورة مفرد', 'cf': 'derived',
        'sp': [['الدلالة من المفتاح', 'AUDIO VIDEO INTERCOM SINGLE SWITCH'],
               ['النطاق', 'LEGEND: INTERCOM'],
               ['مادة الغلاف والتشطيب', 'غير محددين في المصادر المراجعة؛ لون العرض ليس اعتمادًا للمادة']],
        'sr': ['ELEC2 ص21 LC-104: مفتاح INTERCOM، Single switch'],
        'asm': ['مقاس الغلاف ومنسوب التركيب واتجاه وجهه افتراضات العرض القائمة؛ لا يثبتها الرمز.'],
    },
}


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def _metadata(M, e, q):
    a = e.setdefault('a', {})
    previous_guess = {k: a[k] for k in XY_GUESS_KEYS if k in a}
    for k in XY_GUESS_KEYS:
        a.pop(k, None)
    a.update(source_semantics_checked=True,
             source_semantics_method=q['parser'],
             source_semantics_reference='pipeline/data/electrical_symbol_semantics.json#records/'+e['id'],
             source_semantics_record_sha256=q['record_sha256'],
             source_locked_xy=True, source_page=q['source'],
             source_primitives=copy.deepcopy(q['selected_glyph_primitives']),
             source_excluded_primitives=copy.deepcopy(q['excluded_annotation_primitives']),
             source_pdf_points=copy.deepcopy(q['glyph_pdf_points']),
             source_transform=copy.deepcopy(q['registration']),
             source_xy=copy.deepcopy(q['source_xy_cm']),
             source_kind=q['source_kind'], source_anchor=q['source_kind'],
             source_pdf_sha256=q['source_pdf_sha256'],
             source_reference=q['source']+' — '+q['parser']+'؛ primitives '+str(q['selected_glyph_primitives']),
             source_electrical_legacy_record=q.get('archive_record'),
             source_xy_note='مركز الرمز الفعلي بعد فصل حروف/خطوط التسمية والتغذية؛ لا يثبت وجه تثبيت الجهاز أو منسوبه.',
             source_semantics_note=q['reason_ar'])
    a.update(source_material_status='not_specified_in_reviewed_source',
             source_finish_status='not_specified_in_reviewed_source',
             source_physical_geometry_status='display_proxy_pending_dimensions_and_mounting',
             source_height_assumed=True,
             source_cad_colors=copy.deepcopy(q.get('source_cad_colors', [])),
             material_note='مادة/تشطيب الجهاز غير محددين في المصادر المراجعة؛ ألوان CAD تخص الرمز، ولون المجسم تمثيل غير معتمد.')
    if q.get('source_board_name'):
        e['mark'] = q['source_board_name']
        a['source_board_identity'] = copy.deepcopy(q['board_identity_proof'])
    # Historical class-match notes are audit history; the current element cites
    # its reviewed raw glyph and actual legend, with physical properties pending.
    a.setdefault('legacy_source_indices', copy.deepcopy(e.get('s', [])))
    citations = [a['source_reference']+'؛ إثبات دلالة الرمز وXY فقط؛ الغلاف وZ والمادة pending.']
    legend = q.get('actual_legend_reference')
    if legend:
        citations.append(legend['source']+' — مفتاح الرمز؛ primitives '+str(legend['raw_drawing_primitives']))
    source_indices = []
    for citation in citations:
        if citation not in M['sp']:
            M['sp'].append(citation)
        source_indices.append(M['sp'].index(citation))
    e['s'] = source_indices
    # Current mount evidence cannot retain the former nearest-host claim.
    if previous_guess or q['action'] == 'reclassify':
        a['mount_note'] = 'موضع رمز المصدر محفوظ؛ الحامل والوجه ومنسوب التركيب يحتاجان شاهدًا مستقلًا.'
    return previous_guess


def apply(M, els=None):
    els = M['els'] if els is None else els
    with open(DATA, encoding='utf-8') as handle:
        data = json.load(handle)
    by_id = {e['id']: e for e in els}
    changes, mismatches, unresolved = [], [], []
    remove = set()
    actions = collections.Counter()
    log = M.setdefault('meta', {}).setdefault('electrical_semantic_corrections', {})
    for eid, q in data['records'].items():
        if not q['class_verified']:
            unresolved.append(eid)
            continue
        e = by_id.get(eid)
        if e is None:
            if q['action'] != 'remove_nondevice_fragment':
                mismatches.append({'id': eid, 'reason': 'identified device missing'})
            continue
        expected = (q['expected_category'], q['expected_type'], q['expected_level'])
        actual = (e['c'], e.get('t'), e['l'])
        target = (q.get('target_category', expected[0]), q.get('target_type', expected[1]), expected[2])
        if actual not in (expected, target):
            mismatches.append({'id': eid, 'expected': list(expected), 'actual': list(actual)})
            continue
        before = {'category': e['c'], 'type': e.get('t'), 'geometry': copy.deepcopy(e['g'])}
        actions[q['action']] += 1
        if q['action'] == 'remove_nondevice_fragment':
            remove.add(eid)
            after = {'removed': True}
            prior_guess = {k: e.get('a', {}).get(k) for k in XY_GUESS_KEYS if k in e.get('a', {})}
        else:
            if e['g'][0] not in ('b', 'cyl'):
                mismatches.append({'id': eid, 'reason': 'unsupported legacy device geometry'})
                continue
            if q['action'] == 'reclassify':
                e['c'] = q['target_category']; e['t'] = q['target_type']; e['m'] = q['target_material']
                e['g'] = copy.deepcopy(q['target_geometry'])
                if 'match' in e.get('a', {}):
                    e['a']['legacy_class_match'] = e['a'].pop('match')
                e.setdefault('a', {}).update(cls=q['target_type'][2:],
                                            original_symbol_class=q['expected_type'][2:],
                                            source_height_assumed=True, assumed=q['assumed_ar'])
                e['q'] = 'daa'
            elif q['action'] == 'restore_glyph_xy':
                e['g'][1:3] = q['source_xy_cm']
            prior_guess = _metadata(M, e, q)
            after = {'category': e['c'], 'type': e.get('t'), 'geometry': copy.deepcopy(e['g'])}
        row = {'id': eid, 'action': q['action'], 'source': q['source'],
               'source_record_sha256': q['record_sha256'], 'source_primitives': q['raw_drawing_primitives'],
               'glyph_primitives': q['selected_glyph_primitives'], 'reason_ar': q['reason_ar'],
               'before': before, 'after': after, 'prior_xy_placement': prior_guess}
        if before != after:
            changes.append(row)
        if eid not in log or log[eid].get('source_record_sha256') != q['record_sha256']:
            log[eid] = row
    els[:] = [e for e in els if e['id'] not in remove]
    # Two first-floor motion-sensor glyphs were fragmented into fake TYPE2 ticks.
    # Recreate only these complete source symbols; typical sensors already exist.
    for q in data['create_sensors']:
        eid = q['id']
        existing = next((e for e in els if e['id'] == eid), None)
        if existing is None:
            e = {'id': eid, 'c': 'E.socket', 'l': '1', 'g': copy.deepcopy(q['target_geometry']),
                 'mark': None, 't': 'e_S11', 'm': 'm_sensor', 'a': {}, 's': [], 'q': 'daa'}
            els.append(e)
            _metadata(M, e, q)
            e['a'].update(cls='S11', assumed=q['assumed_ar'], source_height_assumed=True)
            changes.append({'id': eid, 'action': 'create_complete_source_sensor', 'source': q['source'],
                            'glyph_primitives': q['selected_glyph_primitives'], 'before': None,
                            'after': copy.deepcopy(e['g']), 'reason_ar': q['reason_ar']})
        elif existing['t'] != 'e_S11' or existing['l'] != '1':
            mismatches.append({'id': eid, 'reason': 'new sensor ID occupied by another identity'})
    M.setdefault('types', {}).update(copy.deepcopy(TYPES))
    stats = {'review_scope_original': data['scope_original_count'], 'actions_applied': dict(actions),
             'removed_nondevices': len(remove), 'source_sensor_count': len(data['create_sensors']),
             'changed_now': len(changes), 'unproved_ids': unresolved, 'identity_mismatches': mismatches,
             'source_file': 'pipeline/data/electrical_symbol_semantics.json',
             'source_data_sha256': _hash(data),
             'limit_ar': 'التحقق دلالي ولـXY الرمز فقط؛ أبعاد الأجهزة وZ والحامل ليست مثبتة إلا بما يصرّح به الدليل.'}
    M['meta']['electrical_symbol_semantics'] = stats
    return dict(stats, changes=changes)
