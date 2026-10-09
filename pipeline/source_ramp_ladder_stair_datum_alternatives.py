# -*- coding: utf-8 -*-
"""Draw registered ladder source alternatives and bind other conflicting sources.

A607 has no existing project XY transform. No original element is changed and
arithmetic +11.00 is never substituted for the printed +10.10.
"""
import copy
import json
from pathlib import Path

DATA_PATH = Path(__file__).with_name('data') / 'source_ramp_ladder_stair_datum_alternatives.json'
OWNER = 'ramp_ladder_stair_datum_sources'
TYPES = {
    'alt_source_midlanding_1010': {'n': 'بديل سطح البسطة المكتوب +10.10', 'cf': 'derived', 'asm': ['سماكة العرض 1 سم أسفل المنسوب المكتوب؛ المادة واللون افتراضان. سطح البسطة فقط دون تغيير الرحلات أو القوائم أو الجسم الحالي.'], 'sr': ['ARCH2 ص 1 A600؛ ص 3 A602']},
    'alt_a106_ladder_plan': {'n': 'بديل رمز سلّم A106 عند +26.85', 'cf': 'derived', 'asm': ['خطوط رمز المسقط في XY المسجل كما هي عند منسوب المصدر +26.85؛ قطر عرض 1 سم والمادة واللون افتراضات. المنحنيات 20 خطوة مع حفظ نقاط التحكم الخام في ملف الدليل.'], 'sr': ['ARCH1 ص 9 A106']},
    'alt_a106_ladder_span': {'n': 'بديل امتداد جانبي سلّم A106 إلى +26.85', 'cf': 'derived', 'asm': ['محور كل جانب وسط زوج الخطوط المرسومة في مسقط A106. استمراره رأسيًا بين +23.35 و+26.85 وقطر العرض 1 سم والمادة واللون افتراضات تمثيل؛ الصفحة لا تحدد شكل قطاع الجانب أو توزيع الدرجات أو التثبيتات.'], 'sr': ['ARCH1 ص 9 A106']},
}
MATS = {}


def data():
    return json.loads(DATA_PATH.read_text(encoding='utf-8'))


def apply(M, els=None):
    """Append the registered A106 alternative once; preserve every original body."""
    D = data()
    target = M['els'] if els is None else els
    by_id = {e['id']: e for e in target}
    added = []
    for original in D['elements']:
        old = by_id.get(original['id'])
        if old is not None:
            if old.get('a', {}).get('alt_owner') != OWNER or any(old.get(k) != original.get(k) for k in ('c', 't', 'l', 'm', 'g', 'a')):
                raise ValueError('Alternative identity is occupied: ' + original['id'])
            continue
        e = copy.deepcopy(original)
        sp = M.setdefault('sp', [])
        source = e['a']['alt_source']
        label = f"{source['file_key']} ص {source['page']} {source['drawing']}: بديل مصدر مستقل؛ تفاصيل العرض المفترضة مبينة في النوع."
        if label not in sp:
            sp.append(label)
        e['s'] = [sp.index(label)]
        e['q'] = 'dda'
        target.append(e)
        by_id[e['id']] = e
        added.append(e['id'])
    M.setdefault('types', {}).update(copy.deepcopy(TYPES))
    groups = copy.deepcopy(D['conflict_groups'])
    for group in groups:
        for source in group['sources']:
            source['missing_element_ids'] = [eid for eid in source['element_ids'] if eid not in by_id]
            source['current_geometry_unchanged'] = [{'id': eid, 'g': copy.deepcopy(by_id[eid]['g'])} for eid in source['element_ids'] if eid in by_id and not by_id[eid].get('a', {}).get('alt')]
    undrawn = copy.deepcopy(D['undrawn'])
    report = {
        'schema': D['schema'], 'owner': OWNER, 'element_ids': [e['id'] for e in D['elements']], 'added': len(added),
        'counts_by_file_page': copy.deepcopy(D['counts_by_file_page']),
        'counts_by_sheet': copy.deepcopy(D['counts_by_file_page']),
        'summary': copy.deepcopy(D['summary']), 'conflict_groups': groups,
        'current_source_bindings': copy.deepcopy(D['current_source_bindings']),
        'undrawn': undrawn,
        'unrepresented_reasons': [x for x in undrawn if x['state'] in ('بانتظار تأكيدك', 'لا هندسة في المصدر')],
        'source_data_file': 'pipeline/data/source_ramp_ladder_stair_datum_alternatives.json',
        'evidence_directory': D['evidence_directory'],
        'current_geometry_policy_ar': D['current_geometry_policy_ar'],
        'existing_elements_changed': 0, 'registration_changed': False,
    }
    M['sourceRampLadderStairDatumAlternatives'] = report
    return report
