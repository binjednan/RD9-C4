# -*- coding: utf-8 -*-
"""Draw three A2300 planting symbols at their existing registered coordinates."""
import copy
import json
from pathlib import Path

DATA = Path(__file__).with_name('data') / 'source_a2300_plants.json'
TYPE = 'source_a2300_small_plant'
TYPE_DEF = {
    'n': 'نبات صغير من مسقط A2300',
    'cf': 'derived',
    'sr': ['ARCH2 ص49 A2300 — مخطط الزراعة'],
    'asm': [
        'مراكز XY من دوائر المصدر المسجلة في landscape.json؛ لا إزاحة لتجنب توزيع ألعاب INEX.',
        'نوع النبات ولونه وشكله الكروي للعرض افتراضية. نصف قطر العرض 12 سم؛ القاع +0.20 م والارتفاع 0.35 م افتراضا العرض المستخدمان للنباتات الصغيرة.'
    ]
}
MATS = {
    'plant_a': {'name': 'نباتات صغيرة — أخضر فاتح', 'color': '#86b252', 'code': 'A2300'},
    'plant_b': {'name': 'نباتات صغيرة — أخضر داكن', 'color': '#2f6f3a', 'code': 'A2300'},
    'plant_c': {'name': 'نباتات صغيرة — أخضر زيتوني', 'color': '#a3b85e', 'code': 'A2300'}
}


def apply(M, els=None):
    """Append missing source plants; leave every existing element unchanged."""
    target = M['els'] if els is None else els
    data = json.loads(DATA.read_text(encoding='utf-8'))
    by_id = {e['id']: e for e in target}
    for saved in data['els']:
        old = by_id.get(saved['id'])
        if old is not None and any(old.get(k) != saved.get(k) for k in ('c', 'l', 't', 'm', 'g')):
            raise ValueError('Source plant identity is occupied: ' + saved['id'])
    M.setdefault('types', {}).setdefault(TYPE, copy.deepcopy(TYPE_DEF))
    for key, value in MATS.items():
        M.setdefault('mats', {}).setdefault(key, copy.deepcopy(value))
    source = data['source']
    label = f"{source['file']} — ARCH2 ص{source['page']}، الرسم {source['drawing']}: رموز النباتات الصغيرة في مواضعها المسجلة."
    pool = M.setdefault('sp', [])
    if label not in pool:
        pool.append(label)
    occupied = {(e['g'][1], e['g'][2]) for e in target
                if e.get('t') in ('plant_small', TYPE) and e['g'][0] == 'sph'}
    added = []
    for saved in data['els']:
        if saved['id'] in by_id or tuple(saved['g'][1:3]) in occupied:
            continue
        e = copy.deepcopy(saved)
        e['s'] = [pool.index(label)]
        e['a'] = {'source_set': source['file_key'], 'source_page': source['page'], 'source_sheet': source['drawing']}
        target.append(e)
        occupied.add(tuple(e['g'][1:3]))
        added.append(e['id'])
    return added
