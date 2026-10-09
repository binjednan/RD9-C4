# -*- coding: utf-8 -*-
"""Apply every ready-to-draw source-detail file (pipeline/data/source_details/*.json) on each build.

File schema (one file per source sheet): {"elements": [...], "types": {...}, "mats": {...}}.
The loader OWNS its elements: it replaces current IDs in their existing slots, removes retired owned IDs, and appends new IDs.
This keeps element-index references stable when only geometry or attributes change.  So a data file can
change the geometry of an id (e.g. a flat stroke becomes a solid) without making the build fail.  Elements of other modules are
never touched.  `src` strings become indexes into M['sp'] like the other source modules.  Literal strokes (types ending _graphic) and
restored candidates (a.restored_candidate) are flagged a.source_graphic so the life-cycle engine skips them.
"""
import copy
import json
from pathlib import Path

DIR = Path(__file__).with_name('data') / 'source_details'


def files():
    return sorted(p for p in DIR.glob('*.json') if p.name != 'INDEX.json') if DIR.is_dir() else []


def _owned(e):
    a = e.get('a') or {}
    return bool(a.get('source_detail') or a.get('source_graphic'))


def apply(M, els=None):
    target = M['els'] if els is None else els
    loaded = []
    for p in files():
        loaded.append((p, json.loads(p.read_text(encoding='utf-8'))))
    current_ids = {e['id'] for _, d in loaded for e in (d.get('elements') or [])}
    before = len(target)
    previous = {e['id']: i for i, e in enumerate(target)}
    if len(previous) != len(target):
        raise ValueError('Duplicate model identity before source details')
    retired = {e['id'] for e in target if _owned(e) and e['id'] not in current_ids}
    removed = len(retired) + len(current_ids & previous.keys())
    staged = {}
    sp = M.setdefault('sp', [])
    source_index = {s: i for i, s in enumerate(sp)}
    per_file = {}
    for p, d in loaded:
        for k, v in (d.get('types') or {}).items():
            M.setdefault('types', {}).setdefault(k, copy.deepcopy(v))
        for k, v in (d.get('mats') or {}).items():
            M.setdefault('mats', {}).setdefault(k, copy.deepcopy(v))
        added = 0
        for saved in d.get('elements') or []:
            if saved['id'] in staged:
                raise ValueError('Duplicate source-detail identity: ' + saved['id'])
            e = copy.deepcopy(saved)
            refs = []
            for s in e.pop('src', []):
                if s not in source_index:
                    source_index[s] = len(sp)
                    sp.append(s)
                refs.append(source_index[s])
            e['s'] = refs
            a = e.setdefault('a', {})
            a['source_detail'] = p.stem
            if e.get('t', '').endswith('_graphic') or a.get('restored_candidate'):
                a['source_graphic'] = 1
            staged[e['id']] = e
            added += 1
        per_file[p.stem] = added
    ordered = [staged.pop(e['id'], e) for e in target if e['id'] not in retired]
    ordered.extend(staged.values())
    if retired and not M.get('_source_index_remap_pending'):
        from source_batch import remap_index_refs
        following = {e['id']: i for i, e in enumerate(ordered)}
        remap_index_refs(M, {i: following[k] for k, i in previous.items() if k in following},
                         [previous[k] for k in retired])
    target[:] = ordered
    return {'module': 'source_details_loader', 'files': len(per_file), 'added': sum(per_file.values()), 'removed_previous': removed, 'by_file': per_file}
