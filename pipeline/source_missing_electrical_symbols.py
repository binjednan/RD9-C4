# -*- coding: utf-8 -*-
"""Draw the fourteen source symbols omitted by historical spatial filters."""
import copy
import json
from pathlib import Path

DATA = Path(__file__).with_name('data') / 'source_missing_electrical_symbols.json'
TYPES = {
    'e_source_symbol_light': {'n': 'رسم رمز إنارة من المصدر', 'cf': 'derived', 'asm': ['رمز مسقط؛ منسوب العرض وسماكة الخط واللون افتراضات.']},
    'e_source_symbol_power': {'n': 'رسم رمز قوى من المصدر', 'cf': 'derived', 'asm': ['رمز مسقط؛ منسوب العرض وسماكة الخط واللون افتراضات.']},
    'e_source_symbol_fa': {'n': 'رسم رمز إنذار أو طوارئ من المصدر', 'cf': 'derived', 'asm': ['رمز مسقط؛ لا يفترض نوع جسم جهاز من تصنيف الأرشيف. منسوب العرض وسماكة الخط واللون افتراضات.']},
    'e_source_symbol_lc': {'n': 'رسم رمز تيار خفيف من المصدر', 'cf': 'derived', 'asm': ['رمز مسقط؛ منسوب العرض وسماكة الخط واللون افتراضات.']},
}


def apply(M, els=None):
    target = M['els'] if els is None else els
    by_id = {e['id']: e for e in target}
    originals = json.loads(DATA.read_text(encoding='utf-8'))
    for e in originals:
        old = by_id.get(e['id'])
        if old is not None and any(old.get(k) != e.get(k) for k in ('c', 't', 'l', 'm', 'g', 'a')):
            raise ValueError('Source symbol identity is already occupied: ' + e['id'])
    sp = M.setdefault('sp', [])
    refs = {s: i for i, s in enumerate(sp)}
    M.setdefault('types', {}).update(copy.deepcopy(TYPES))
    added = 0
    for original in originals:
        if original['id'] in by_id:
            continue
        e = copy.deepcopy(original)
        e['s'] = []
        for source in e.pop('src'):
            if source not in refs:
                refs[source] = len(sp)
                sp.append(source)
            e['s'].append(refs[source])
        target.append(e)
        added += 1
    return added
