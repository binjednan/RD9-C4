"""Incremental positive-volume witnesses for corrected solid envelopes.

Uses the existing renderer-matched section engine, preserves polygon holes,
does not move elements, change legacy tolerances, or call an open stair surface
a concrete solid. This is a model review, never construction approval.
"""
import collections
import hashlib
import json

from shapely.strtree import STRtree

import coordination_review as CR


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode()).hexdigest()


def audit(M, target_ids):
    target_ids={eid for eid in target_ids if not next((e.get('a',{}).get('alt')for e in M['els']if e['id']==eid),False)}
    by = {e['id']: e for e in M['els']}
    if len(by) != len(M['els']) or not set(target_ids) <= set(by):
        raise ValueError('Duplicate identity or missing target')
    if any(by[i].get('stage') or by[i]['c'].endswith('.stage') for i in target_ids):
        raise ValueError('Display-only staging is outside the target scope')
    before = digest(M['els'])
    polygons, records, unsupported, stage = [], [], [], []
    for e in M['els']:
        if e.get('a',{}).get('alt'): continue
        if e.get('stage') or e['c'].endswith('.stage'):
            stage.append(e['id'])
            continue
        parts = CR._pieces(e)
        if not parts:
            unsupported.append({'id': e['id'], 'code': e['g'][0]})
        for p in parts:
            polygons.append(p['polygon'])
            records.append((e['id'], p['z']))
    tree = STRtree(polygons)
    known = {tuple(sorted((c['ea'], c['eb']))): c['id'] for c in M.get('clashes', [])}
    checked, candidates, results = set(), set(), []
    for eid in sorted(set(target_ids)):
        a = by[eid]
        for piece in CR._pieces(a):
            for index in tree.query(piece['polygon'], predicate='intersects'):
                other, z = records[index]
                if other == eid or min(piece['z'][1], z[1]) <= max(piece['z'][0], z[0]):
                    continue
                candidates.add(tuple(sorted((eid, other))))
    for pair in sorted(candidates):
        a, b = (by[i] for i in pair)
        witness = CR._geometry(a, b)
        checked.add(pair)
        if not witness['positive_volume_proved']:
            continue
        same_group = bool(a.get('grp') and a.get('grp') == b.get('grp'))
        results.append({
            'id': 'SC-' + digest(pair)[:10].upper(), 'ea': pair[0], 'eb': pair[1],
            'level': a['l'] if a['l'] == b['l'] else a['l'] + '/' + b['l'],
            'categories': [a['c'], b['c']], 'geometry': witness,
            'existing_clash_id': known.get(pair),
            'same_assembly': same_group,
            'classification': 'model_overlap_requires_semantic_review',
            'source_and_site_accepted': False,
            'note_ar': ('تداخل داخل تجميع واحد؛ يحتاج تفسير اتصال الأجزاء ولا يعد خطأ تلقائيًا.'
                        if same_group else
                        'شاهد تداخل موجب في المجسم؛ المنسوب والفتح والتثبيت بحاجة مراجعة المصدر قبل أي تعديل.'),
        })
    if digest(M['els']) != before:
        raise AssertionError('Read-only coordination mutated elements')
    return {
        'schema': 'c4.scoped-solid-coordination.v1',
        'target_ids': sorted(set(target_ids)), 'target_count': len(set(target_ids)),
        'supported_targets': sum(bool(CR._pieces(by[i])) for i in set(target_ids)),
        'compared_model_elements': len(by), 'broad_phase_pairs': len(candidates),
        'narrow_phase_pairs': len(checked), 'positive_volume_pairs': len(results),
        'already_in_legacy_clashes': sum(bool(q['existing_clash_id']) for q in results),
        'new_to_legacy_list': sum(not q['existing_clash_id'] for q in results),
        'unsupported_geometry_counts': dict(collections.Counter(q['code'] for q in unsupported)),
        'unsupported_elements': unsupported, 'excluded_stage_elements': stage,
        'model_elements_sha256': before, 'rows': results,
        'geometry_preserved': True, 'physical_acceptance': False,
        'negative_result_is_complete_clearance': False,
        'limit_ar': 'مسح للأغلفة الصلبة المحددة فقط مقابل الأجسام التي يدعمها محرك المقاطع. أسطح الدرج المفتوحة وأشكال العرض غير المدعومة مستثناة صراحة؛ لا يثبت غياب نتائج أو قبول التنفيذ.',
    }
