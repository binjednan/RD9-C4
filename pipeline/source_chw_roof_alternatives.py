# -*- coding: utf-8 -*-
"""Draw separate CHW/roof source alternatives without editing current geometry.

Only this module and its data belong to this batch. `apply` neither promotes
source review nor creates connections. Raw PDF witnesses/images are sidecar data.
"""
import copy
import json
from pathlib import Path

DATA = Path(__file__).with_name('data') / 'source_chw_roof_alternatives.json'
TYPES = {
    'chw_alt_supply_graphic': {'n': 'بديل رسم المياه المبردة — تغذية', 'cf': 'derived', 'sp': [], 'asm': ['وجوه عرض أفقية مستقلة حول خطوط ورموز المصدر؛ عرض الخط 1 سم وZ افتراضيان: 2.80 م فوق منسوب الطابق، و0.50 م فوق السطح. المنحنى 20 خطوة لكل عملية مع حفظ نقاط تحكمه الأصلية في ملف المصدر. الضربات ليست أنابيب تنفيذية أو دليل اتصال.'], 'sr': ['MECH2 ص 32–36']},
    'chw_alt_return_graphic': {'n': 'بديل رسم المياه المبردة — رجوع', 'cf': 'derived', 'sp': [], 'asm': ['الشرطات والفجوات محفوظة كوجوه عرض أفقية مستقلة؛ عرض الخط 1 سم وZ افتراضيان: 2.74 م فوق منسوب الطابق، و0.35 م فوق السطح. المنحنى 20 خطوة لكل عملية مع حفظ نقاط تحكمه الأصلية في ملف المصدر. لا تنشأ وصلات.'], 'sr': ['MECH2 ص 32–36']},
    'roof_alt_arch_chiller': {'n': 'بديل مبرد السطح من مسقط العمارة', 'cf': 'derived', 'sp': [], 'asm': ['المسقط من A106؛ قاع العرض +23.35 م وارتفاعه 2.50 م والقاعدة والمادة واللون افتراضات عرض.'], 'sr': ['ARCH1 ص 9 A106']},
    'roof_alt_arch_fahu': {'n': 'بديل FAHU من مسقط العمارة', 'cf': 'derived', 'sp': [], 'asm': ['المسقط من A106؛ قاع العرض +23.35 م وارتفاعه 1.80 م والقاعدة والمادة واللون افتراضات عرض.'], 'sr': ['ARCH1 ص 9 A106']},
    'roof_alt_arch_tank': {'n': 'بديل خزان السطح من مسقط العمارة', 'cf': 'derived', 'sp': [], 'asm': ['حدود ألواح الخزان مرسومة في A106؛ قاع العرض +23.35 م وارتفاعه 2.00 م ووظيفته ولونه ومادة GRP افتراضات للعرض، لا يحددها A106.'], 'sr': ['ARCH1 ص 9 A106']},
    'roof_alt_arch_detail': {'n': 'تفصيل رسومي لبديل معدات السطح', 'cf': 'derived', 'sp': [], 'asm': ['وجوه أفقية مستقلة لضربات رمز المسقط؛ عرض الخط 0.5 سم والمنسوب على أعلى جسم العرض الافتراضي، وليست قطعة تصنيع مستقلة. المنحنى 20 خطوة لكل عملية مع حفظ نقاط تحكم المصدر.'], 'sr': ['ARCH1 ص 9 A106']},
}


def data():
    return json.loads(DATA.read_text(encoding='utf-8'))


def apply(M, els=None):
    """Append source alternatives once; return per-sheet counts and conflict slices.

    Existing elements are read only, including alternatives on repeated calls.
    Metadata used by consumers lives in a.alt/a.alt_conflict/a.alt_source.
    """
    target = M['els'] if els is None else els
    d = data()
    by_id = {e['id']: e for e in target}
    # Reusing an owned ID must never overwrite an unrelated or different body.
    for e in d['els']:
        old = by_id.get(e['id'])
        if old is not None and (any(old.get(k) != e.get(k) for k in ('c', 't', 'l', 'm', 'g')) or old.get('a', {}).get('alt_source') != e['a']['alt_source']):
            raise ValueError('Alternative ID is occupied by different geometry: ' + e['id'])
    sp = M.setdefault('sp', [])
    source_index = {s: i for i, s in enumerate(sp)}
    added = []
    for original in d['els']:
        if original['id'] in by_id:
            continue
        e = copy.deepcopy(original)
        refs = []
        for s in e.pop('src', []):
            if s not in source_index:
                source_index[s] = len(sp)
                sp.append(s)
            refs.append(source_index[s])
        e['s'] = refs
        e['q'] = 'dda'
        target.append(e)
        by_id[e['id']] = e
        added.append(e['id'])
    for key, value in TYPES.items():
        M.setdefault('types', {}).setdefault(key, copy.deepcopy(value))
    groups = copy.deepcopy(d['conflict_groups'])
    for group in groups:
        for s in group['sources']:
            selector = s.pop('existing_selector', None)
            if selector:
                s['element_ids'] = [e['id'] for e in target if not e.get('a', {}).get('alt') and e.get('t') in selector['types'] and e.get('l') in selector['levels']]
            if any(not by_id.get(eid, {}).get('a', {}).get('alt') for eid in s['element_ids']):
                s['values'] = {'existing_geometry_unchanged': [{'id': eid, 'g': copy.deepcopy(by_id[eid]['g'])} for eid in s['element_ids'] if eid in by_id]}
            s['missing_element_ids'] = [eid for eid in s['element_ids'] if eid not in by_id]
    added_set = set(added)
    sheets = copy.deepcopy(d['sheets'])
    for sheet in sheets:
        sheet['added_now'] = sum(e['id'] in added_set for e in d['els'] if e['a']['alt_source']['file_key'] == sheet['file_key'] and e['a']['alt_source']['page'] == sheet['page'])
    return {'module': 'source_chw_roof_alternatives', 'added': len(added), 'added_ids': added, 'total_alternative_elements': len(d['els']),
            'body_count': d['counts']['bodies'], 'raw_graphic_count': d['counts']['raw_graphic_elements'],
            'source_graphic_operator_count': d['counts'].get('source_graphic_operators_preserved'),
            'source_graphic_segment_count': d['counts'].get('source_graphic_segments_preserved'),
            'counts_by_sheet': sheets, 'conflict_groups': groups, 'undrawn': copy.deepcopy(d['undrawn']),
            'existing_elements_changed': 0, 'registration_changed': False, 'connections_created': 0,
            'compaction': copy.deepcopy(d.get('compaction', {})),
            'note_ar': 'البدائل مرسومة من كل مصدر كما هو؛ الأجسام الحالية محفوظة، وكل اختيار بين المصادر بانتظار تأكيدك.'}
