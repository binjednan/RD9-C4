# -*- coding: utf-8 -*-
"""Bind111 window assemblies to original A103/A104 glyph planes and centres.

The group identity is retained; old cached XY is only a guarded input, never
an authority. The resulting2776 parts are derived assemblies around the raw
anchor. Neither absoluteZ, physical depth nor mounting is source approved.
"""
import copy
import functools
import hashlib
import json
import math
from pathlib import Path

DATA_PATH = Path(__file__).with_name('data') / 'window_source_xy.json'
_FROZEN_DATA_SHA256 = '166c49aff36f96ced82c56fff4cfe6ccf150fa3e01935c620b4720eead76d155'


def _sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def _items(value):
    import fitz
    if isinstance(value, fitz.Point): return [value.x, value.y]
    if isinstance(value, fitz.Quad): return [[p.x, p.y] for p in value]
    if isinstance(value, fitz.Rect): return list(value)
    if isinstance(value, (list, tuple)): return [_items(p) for p in value]
    return value


@functools.lru_cache(maxsize=2)
def _verify_original(data_text, pdf_path, mtime_ns, size):
    import fitz
    import reg
    if hashlib.sha256(data_text.encode('utf-8')).hexdigest() != _FROZEN_DATA_SHA256:
        raise ValueError('WXY frozen source binding changed')
    data = json.loads(data_text)
    if hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest() != data['source_pdf_sha256']:
        raise ValueError('WXY original PDF fingerprint changed')
    schedule = data['schedule']; schedule_pdf = Path(schedule['source_pdf'])
    if hashlib.sha256(schedule_pdf.read_bytes()).hexdigest() != schedule['source_pdf_sha256']:
        raise ValueError('WXY original schedule PDF fingerprint changed')
    with fitz.open(schedule_pdf) as document:
        schedule_text = {}
        for code, reference in schedule['raw_dimension_references'].items():
            number = int(reference['source_page'].split(':')[1])-1
            if number not in schedule_text:
                schedule_text[number] = document[number].get_texttrace()
            text = schedule_text[number]
            for literal in reference['dimension_traces']:
                raw = text[literal['index']]
                if (''.join(chr(c[0]) for c in raw['chars']) != literal['literal'] or
                        list(raw['bbox']) != literal['bbox'] or raw.get('layer') != literal['layer'] or
                        [[c[0], list(c[2]), list(c[3])] for c in raw['chars']] != literal['chars']):
                    raise ValueError('WXY original schedule dimension changed: ' + code)
    with fitz.open(pdf_path) as doc:
        for pn, source in data['pages'].items():
            drawings = doc[int(pn) - 1].get_drawings()
            text = doc[int(pn) - 1].get_texttrace()
            grid = [d for d in drawings if d.get('layer') and
                    ('GRID' in d['layer'].upper() or 'AXIS' in d['layer'].upper()) and
                    'IDEN' not in d['layer'].upper()]
            vv, hh = reg.grid_clusters(None, layers=None, drawings=grid, minlen=50)
            actual = reg.register_free(vv, hh)
            if actual != source['registration'] or vv != source['grid_pdf_v'] or hh != source['grid_pdf_h']:
                raise ValueError('WXY current raw grid registration changed')
            for record in source['grid_raw_drawings']:
                d = drawings[record['drawing']]
                if d.get('layer') != record['layer'] or _items(d['items']) != record['items']:
                    raise ValueError('WXY original grid primitive changed')
            for row in source['rows']:
                if row['drawing_indices'] != [q['drawing'] for q in row['raw_items']]:
                    raise ValueError('WXY raw primitive identity list changed')
                for q in row['raw_items']:
                    d = drawings[q['drawing']]
                    if d.get('layer') != 'A-GALZ' or _items(d['items']) != q['items']:
                        raise ValueError('WXY original window primitive changed')
                tag = row['tag']; trace = text[tag['texttrace_index']]
                if (''.join(chr(c[0]) for c in trace['chars']).strip() != tag['code'] or
                        list(trace['bbox']) != tag['bbox_pdf'] or trace.get('layer') != 'A-WINDOW -IDEN'):
                    raise ValueError('WXY original CW tag changed')
    for unit in data['units'].values():
        pn = unit['source_page'].split(':')[1]
        source = next(r for r in data['pages'][pn]['rows'] if r['side'] == unit['side'] and
                      r['facade_ordinal'] == unit['facade_ordinal'])
        if source != unit['source_anchor'] or _sha(unit['source_anchor']) != unit['source_record_sha256']:
            raise ValueError('WXY unit raw binding changed: ' + unit['grp'])
    return True


def bind_modules(modules):
    """Return new modules in the identical order; raw111 bindings checked once."""
    data_text = DATA_PATH.read_text(encoding='utf-8'); data = json.loads(data_text)
    pdf = Path(data['source_pdf']); stat = pdf.stat()
    _verify_original(data_text, str(pdf), stat.st_mtime_ns, stat.st_size)
    from arch_windows import PAT, CW19
    if PAT != data['schedule']['PAT'] or [list(q) for q in CW19] != data['schedule']['CW19']:
        raise ValueError('WXY source schedule pattern binding changed')
    out = []
    seen = set()
    for old in modules:
        grp = old['grp']; unit = data['units'].get(grp)
        if unit is None:
            # The continuous CW19 glyph in repeated plans is an identity/context
            # witness only; the generator emits the single level1 assembly.
            if old['t'] == 'win_CW-19' and old['l'] in ('2', '3', '4', '5'):
                out.append(copy.deepcopy(old)); continue
            raise ValueError('WXY unbound module: ' + grp)
        if (old['l'], old['t'], old['side']) != (unit['level'], unit['type'], unit['side']):
            raise ValueError('WXY exact module identity guard failed: ' + grp)
        clean = {k: v for k, v in old.items() if not k.startswith('_source_')}
        if clean not in (unit['before_module'], unit['source_module']):
            raise ValueError('WXY guarded module input changed: ' + grp)
        mod = copy.deepcopy(unit['source_module'])
        mod['_source_window'] = {
            'grp': grp, 'source_page': unit['source_page'], 'source_sheet': data['pages'][unit['source_page'].split(':')[1]]['source_sheet'],
            'source_kind': 'derived_window_assembly_from_graphic_glazing_plane_and_profile_axis',
            'source_anchor': 'glazing_band_normal_plane_and_closed_profile_axis_midpoint',
            'source_drawing_indices': unit['source_anchor']['drawing_indices'],
            'source_closed_profile_primitives': unit['source_anchor']['closed_profile_primitives'],
            'source_glazing_bands': unit['source_anchor']['bands'],
            'source_anchor_pdf': unit['source_anchor']['source_anchor_pdf'],
            'source_xy': unit['source_anchor']['source_xy'],
            'source_transform': data['pages'][unit['source_page'].split(':')[1]]['registration'],
            'source_tag_texttrace': unit['source_anchor']['tag']['texttrace_index'],
            'source_tag_hex_drawing': unit['source_anchor']['tag']['tag_hex'][0],
            'source_facade_ordinal': unit['facade_ordinal'],
            'source_record_sha256': unit['source_record_sha256'],
            'source_pdf_sha256': data['source_pdf_sha256'],
            '_member_identity_guard': unit['model_member_identity_guard'],
            'source_literal_width_cm': unit['literal_schedule_width_cm'],
            'source_rough_profile_span_cm': unit['rough_frame_profile_span_cm'],
            'source_old_module_anchor': [(old['x0']+old['x1'])/2, (old['y0']+old['y1'])/2]}
        out.append(mod); seen.add(grp)
    if seen != set(data['units']):
        raise ValueError('WXY expected111 unique source groups not present')
    return out


def attributes(module, member_ordinal, geometry, typ, part):
    """Evidence describes assemblyanchor, explicitly not each part's centre."""
    source = module.get('_source_window')
    if not source:
        return {}
    a = copy.deepcopy(source); a['source_window_group'] = a.pop('grp')
    members = a.pop('_member_identity_guard')
    if member_ordinal >= len(members):
        raise ValueError('WXY derived member count changed')
    member = members[member_ordinal]
    if ((member['category'], member['type'], member['level'], member['part'], member['geometry_kind']) !=
            ('A.win', typ, module['l'], part, geometry[0]) or
            member['before_g_height_already_corrected'][5:] != geometry[5:]):
        raise ValueError('WXY member c/type/level/part/Z identity changed')
    a.update(source_window_member_identity=member['id'],
             source_window_member_ordinal=member_ordinal,
             source_window_member_identity_scope='procedural_group_member_identity_not_independent_raw_part')
    a.update(source_locked_xy=True, source_module_XY_verified=True,
             source_window_anchor_verified=True, source_body_part_independently_drawn=False,
             source_schedule_width_verified=True, source_absolute_Z_verified=False,
             source_Z_verified=False, source_frame_width_depth_verified=False,
             source_material_assignment_verified=False, source_material_verified=False,
             source_mount_verified=False, source_contact_verified=False,
             source_dimensions_verified=False,
             source_physical_geometry_status='assembly_derived_from_raw_anchor_schedule_with_proxy_sections',
             assumed='إسناد المجموعة XY وخط الزجاج من رمز A103/A104 المغلق، والعرض والخلايا من A801/A802. كل قطعة جسم مشتقة من هذا الإسناد، وليست رمزًا مرسومًا مستقلاً. FFL والبداية المطلقة Z غير متحققين؛ عرض الإطار5سم وعمقه8سم وسماكة جسم الزجاج3سم وقطاع الضلفة والمقبض وعمق العتبة تمثيل افتراضي؛ لا يثبت المسقط المضيف أو تماس التثبيت. عرض الجدول مستقل عن عرض الفتحة/القطاع المرسوم.')
    return a


@functools.lru_cache(maxsize=2)
def _identity_data(mtime_ns, size):
    content = DATA_PATH.read_text(encoding='utf-8')
    if hashlib.sha256(content.encode('utf-8')).hexdigest() != _FROZEN_DATA_SHA256:
        raise ValueError('WXY frozen procedural identity data changed')
    return json.loads(content)


def member_identity(element, previous_by_id):
    """Procedural oldID linkage, separate from PDF geometry acceptance.

    Called only for explicitly sourcebound WXY parts before the generic
    accessory ID proximity fallback. Prior Z is not an identity key: the
    independent scheduleheight correction legitimately changed it.
    """
    a = element.get('a') or {}
    wanted = a.get('source_window_member_identity')
    if wanted is None:
        return None
    stat = DATA_PATH.stat()
    data = _identity_data(stat.st_mtime_ns, stat.st_size)
    unit = data['units'].get(element.get('grp'))
    if unit is None or element.get('c') != 'A.win' or not a.get('source_locked_xy'):
        raise ValueError('WXY procedural ID scope failed')
    ordinal = a.get('source_window_member_ordinal')
    if not isinstance(ordinal, int) or not 0 <= ordinal < len(unit['model_member_identity_guard']):
        raise ValueError('WXY procedural member ordinal failed')
    record = unit['model_member_identity_guard'][ordinal]
    if wanted != record['id'] or a.get('source_record_sha256') != unit['source_record_sha256']:
        raise ValueError('WXY procedural record/ID guard failed')
    previous = previous_by_id.get(wanted)
    if previous is None:
        raise ValueError('WXY previous member ID missing: ' + wanted)
    identity = (element['c'], element['t'], element['l'], element.get('grp'), a.get('part'))
    prior = (previous['c'], previous['t'], previous['l'], previous.get('grp'),
             (previous.get('a') or {}).get('part'))
    literal = (record['category'], record['type'], record['level'], unit['grp'], record['part'])
    if identity != literal or prior != literal:
        raise ValueError('WXY procedural c/type/level/group/part guard failed: ' + wanted)
    return wanted
