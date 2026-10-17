# -*- coding: utf-8 -*-
"""Original-PDF gate for actual HVAC body graphics, separated from flow arrows.

audit(M) returns body checks, false-component retirement checks and raw scope.
The original ordered layer identities are procedural bindings; body cores and
anchors are reconstructed afresh. Physical dimensions/Z/ports remain pending.
"""
import collections
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'pipeline/data/restore_hvac_outlets_source.json'
TOL = .2
_START = {'1': 1, '2': 166, '3': 325, '4': 484, '5': 643}
_PAGE = {'1': 3, '2': 4, '3': 4, '4': 4, '5': 5, 'G': 2}
_LAYERS = [('diff_supply', 'M_SAD_DIFF'), ('diff_return', 'M_RAD_DIFF'),
           ('grille_supply', 'M_SAG_GRILL'), ('grille_return', 'M_RAG_GRILL')]


def _items(value):
    import fitz
    if isinstance(value, fitz.Point): return [value.x, value.y]
    if isinstance(value, fitz.Quad): return [[p.x, p.y] for p in value]
    if isinstance(value, fitz.Rect): return list(value)
    if isinstance(value, (list, tuple)): return [_items(v) for v in value]
    return value


def _bbox(points):
    return [min(p[k] for p in points) for k in (0, 1)] + [max(p[k] for p in points) for k in (0, 1)]


def _groups(primitives, gap=.6):
    """Independent component grouping; order is earliest raw primitive."""
    parent = list(range(len(primitives)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i, left in enumerate(primitives):
        a = left['bbox']
        for j in range(i + 1, len(primitives)):
            b = primitives[j]['bbox']
            if a[0] - gap <= b[2] and b[0] - gap <= a[2] and a[1] - gap <= b[3] and b[1] - gap <= a[3]:
                parent[root(j)] = root(i)
    groups = collections.defaultdict(list)
    for i in range(len(primitives)): groups[root(i)].append(i)
    return sorted(groups.values(), key=lambda group: min(group))


def _original_groups(drawings, transform):
    sys.path.insert(0, str(ROOT / 'pipeline'))
    import lib
    out = []
    for typ, layer in _LAYERS:
        primitives = []
        for di, raw in enumerate(drawings):
            if raw.get('layer') != layer: continue
            for pi, path in enumerate(lib.flat_path(raw)):
                b = _bbox(path)
                if max(b[2] - b[0], b[3] - b[1]) <= 200:
                    primitives.append({'drawing': di, 'poly': pi, 'bbox': b,
                                       'points': _items(path), 'items': _items(raw['items'])})
        for component in _groups(primitives):
            parts = [primitives[i] for i in component]
            points = [p for q in parts for p in q['points']]; b = _bbox(points)
            centre = [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2]
            out.append({'type': typ, 'layer': layer, 'parts': parts, 'bbox': b,
                        'pdf_centre': centre,
                        'xy': [centre[0] * transform['s'] + transform['ox'],
                               transform['oy'] - centre[1] * transform['s']]})
    return out


def _diffuser_body_core(q):
    """Read the square annular frame and its X; reject arrow-only clusters.

    Filled CAD frames are eight triangular subpaths, not one closed quad.
    The two crossing strokes inside the same frame distinguish a SAD/RAD
    device graphic from its adjacent filled flow arrow and damper leader.
    """
    by_drawing = collections.defaultdict(list)
    for part in q['parts']:
        by_drawing[part['drawing']].append(part)
    candidates = []
    for drawing, parts in by_drawing.items():
        if len(parts) != 8:
            continue
        for part in parts:
            points = part['points']; unique = []
            for point in points:
                if not any(math.dist(point, p) < .01 for p in unique): unique.append(point)
            if len(unique) != 3 or math.dist(points[0], points[-1]) >= .01:
                break
        else:
            bbox = _bbox([p for part in parts for p in part['points']]); w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if min(w, h) <= 0 or max(w, h) / min(w, h) > 1.03: continue
            crosses = []
            for part in q['parts']:
                points = part['points']
                if len(points) != 2: continue
                if (bbox[0] <= min(p[0] for p in points) <= max(p[0] for p in points) <= bbox[2] and
                    bbox[1] <= min(p[1] for p in points) <= max(p[1] for p in points) <= bbox[3] and
                    abs(points[0][0] - points[1][0]) > .75 * w and abs(points[0][1] - points[1][1]) > .75 * h):
                    crosses.append(part)
            if len(crosses) != 2: continue
            signs = [(p['points'][1][0] - p['points'][0][0]) * (p['points'][1][1] - p['points'][0][1]) for p in crosses]
            if signs[0] * signs[1] >= 0: continue
            candidates.append({'parts': parts + crosses, 'bbox': bbox, 'kind': 'square_diffuser_frame_and_cross'})
    return candidates[0] if len(candidates) == 1 else None


def _bar_body_cores(q):
    """Closed rectangular source profiles only; discard flow arrows/open runs.

    The .001pt bound joins authored shared PDF edges with float noise. It is
    not a host, model-position or network-connectivity tolerance.
    """
    rectangles = []
    for part in q['parts']:
        points = part['points']; unique = list(dict.fromkeys(tuple(p) for p in points))
        if points[0] != points[-1] or len(unique) != 4: continue
        bbox = _bbox(points); box_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        area = abs(sum(a[0]*b[1] - b[0]*a[1] for a, b in zip(points, points[1:] + points[:1]))) / 2
        if box_area > 0 and abs(area - box_area) < .0005 * box_area:
            rectangles.append(part)
    parent = list(range(len(rectangles)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i, left in enumerate(rectangles):
        a = left['bbox']
        for j in range(i + 1, len(rectangles)):
            b = rectangles[j]['bbox']
            if a[0] - .001 <= b[2] and b[0] - .001 <= a[2] and a[1] - .001 <= b[3] and b[1] - .001 <= a[3]:
                parent[root(j)] = root(i)
    groups = collections.defaultdict(list)
    for i, part in enumerate(rectangles): groups[root(i)].append(part)
    return [{'parts': group, 'bbox': _bbox([p for part in group for p in part['points']]),
             'kind': 'closed_bar_grille_source_profiles'}
            for group in sorted(groups.values(), key=lambda g: min((p['drawing'], p['poly']) for p in g))]


def _body_cores(q):
    if q['type'] in ('diff_supply', 'diff_return'):
        core = _diffuser_body_core(q)
        return [core] if core else []
    return _bar_body_cores(q)

def _sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def _raw_scope(data):
    """Reconstruct every raw slot and each actual body without ledger counts."""
    import fitz
    registry = json.loads((ROOT / 'pipeline/data/reg_all.json').read_text())
    verified = json.loads((ROOT / 'pipeline/data/reg_verified.json').read_text())
    pdf_path = Path(data['source_pdf'])
    pdf_sha = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    body = {}; retired = {}; inventory = []; pages = {}; split_number = 0
    with fitz.open(pdf_path) as document:
        for level, number in _PAGE.items():
            ref = 'MECH1:' + str(number)
            transform = verified.get(ref, {}).get('reg', registry[ref])
            if number not in pages:
                page = document[number - 1]
                pages[number] = _original_groups(page.get_drawings(), transform), page.get_texttrace()
            raw, text = pages[number]
            inside = lambda q: -30 <= q['xy'][0] <= 3230 and -100 <= q['xy'][1] <= 1900
            if level == 'G':
                inventory.extend({'id': None, 'level': level, 'reference': ref,
                    'disposition': 'legend_context_not_component', 'source_primitives':
                    [[p['drawing'], p['poly']] for p in q['parts']]} for q in raw if not inside(q))
                original = [q for q in raw if inside(q)]
            else:
                original = raw
            for ordinal, q in enumerate(original, 1 if level == 'G' else _START[level]):
                eid = 'M.outlet-' + level + ('-M' if level == 'G' else '-') + str(ordinal).zfill(4)
                entry = {'id': eid, 'level': level, 'reference': ref,
                    'source_primitives': [[p['drawing'], p['poly']] for p in q['parts']]}
                if not inside(q):
                    inventory.append(dict(entry, disposition='legend_context_not_component'))
                    continue
                cores = _body_cores(q)
                base = {'q': q, 'level': level, 'reference': ref, 'transform': transform,
                        'text': text, 'ordinal': ordinal, 'total': len(original), 'origin_id': eid}
                if not cores:
                    retired[eid] = base
                    inventory.append(dict(entry, disposition='retired_non_device_fragment'))
                else:
                    inventory.append(dict(entry, disposition='source_body_group', body_components=len(cores)))
                    for index, core in enumerate(cores):
                        target = eid
                        if index:
                            split_number += 1
                            target = 'M.outlet-' + level + '-HOB' + str(split_number).zfill(4)
                        b = core['bbox']; tr = transform
                        body[target] = dict(base, core=core, index=index, id=target,
                            xy=[(b[0]+b[2])/2*tr['s']+tr['ox'], tr['oy']-(b[1]+b[3])/2*tr['s']],
                            dimensions=[(b[2]-b[0])*tr['s'], (b[3]-b[1])*tr['s']])
    return {'bodies': body, 'retired': retired, 'inventory': inventory, 'pdf_sha256': pdf_sha}


def _binding_errors(data, row, raw, body):
    s = row.get('source', {}); q = raw['q']; errors = []
    wanted = {'source_page': raw['reference'], 'source_layer': q['layer'],
        'source_primitives': [[p['drawing'],p['poly']] for p in q['parts']],
        'source_pdf_points': [p['points'] for p in q['parts']],
        'source_glyph_bbox_pdf': q['bbox'], 'source_transform': raw['transform'],
        'source_whole_cluster_xy': q['xy']}
    for key, value in wanted.items():
        if s.get(key) != value: errors.append('Original raw binding differs: ' + key)
    bound = s.get('source_bound_primitives', [])
    expected_bound = [{'drawing': p['drawing'], 'poly': p['poly'], 'layer': q['layer'],
        'raw_items': p['items'], 'pdf_points': p['points'], 'drawing_bbox': p['bbox']} for p in q['parts']]
    if bound != expected_bound: errors.append('Original raw drawing operators/paths differ')
    slot = s.get('source_slot', {})
    if slot.get('ordinal_for_level') != raw['ordinal'] or slot.get('total_groups_for_level') != raw['total']:
        errors.append('Original emitter slot differs')
    literal = s.get('source_sheet_text', {})
    index = literal.get('index')
    if not isinstance(index, int) or not 0 <= index < len(raw['text']):
        errors.append('Original sheet literal index differs')
    else:
        trace = raw['text'][index]
        if (literal.get('literal') != ''.join(chr(c[0]) for c in trace['chars']) or
                literal.get('bbox') != list(trace['bbox']) or literal.get('layer') != trace.get('layer')):
            errors.append('Original sheet-name literal differs')
    if s.get('source_pdf_sha256') != data.get('source_pdf_sha256'):
        errors.append('Source PDF fingerprint binding differs')
    if _sha(s) != row.get('source_record_sha256'):
        errors.append('Source record fingerprint differs')
    if (row.get('category'), row.get('type'), row.get('level')) != ('M.outlet', q['type'], raw['level']):
        errors.append('Raw source category/type/level identity differs')
    if body:
        core = raw['core']
        core_fields = {'source_kind': 'source_device_body_graphic_core', 'source_body_kind': core['kind'],
            'source_body_primitives': [[p['drawing'],p['poly']] for p in core['parts']],
            'source_body_pdf_points': [p['points'] for p in core['parts']], 'source_body_bbox_pdf': core['bbox'],
            'source_body_component_index': raw['index'], 'source_xy': raw['xy'],
            'source_graphic_dimensions_cm': raw['dimensions']}
        for key, value in core_fields.items():
            if s.get(key) != value: errors.append('Actual body core binding differs: ' + key)
        if row.get('origin_id') != raw['origin_id']:
            errors.append('Body origin identity differs')
        g = row.get('after_g', [])
        graphic = ['b']+[round(v,1) for v in raw['xy']]+[round(v,1) for v in raw['dimensions']]+[0]
        if g[:6] != graphic: errors.append('Saved graphic proxy differs from independently read body core')
        if row.get('physical_body_dimensions_Z_material_mounting_ports_verified') is not False:
            errors.append('Unsupported physical body acceptance in data')
        serialized=row.get('procedural_source_emitter_g_core')
        if serialized is not None:
            prefix=list(row['before_g'][:6]);prefix[1:3]=[round(v,1) for v in q['xy']]
            if (row['id']!='M.outlet-G-M0008' or row['before_g'][1:3]!=q['xy'] or
                    serialized!=prefix):
                errors.append('Unbound stateless original-emitter serialization guard')
    else:
        if s.get('source_kind') != 'raw_flow_or_line_fragment_not_device' or s.get('source_xy') != q['xy']:
            errors.append('False-component source disposition differs')
        if row.get('replacement_device_or_connection_assumed') is not False:
            errors.append('Unsupported replacement component/connection')
    return errors


def validate_ledger(data):
    raw = _raw_scope(data); findings = []
    if data.get('schema') != 'c4.hvac-outlet-body-source.v2':
        findings.append({'errors': ['Revoked or unsupported HVO source schema']})
    if raw['pdf_sha256'] != data.get('source_pdf_sha256'):
        findings.append({'errors': ['Original PDF fingerprint changed']})
    for name, source_name, is_body in (('records','bodies',True), ('retired_non_device_records','retired',False)):
        rows = data.get(name, {}); expected = raw[source_name]
        for eid in sorted(set(rows)^set(expected)):
            findings.append({'id':eid,'errors':['Missing or excluded deterministic original identity in '+name]})
        for eid in set(rows)&set(expected):
            errors = _binding_errors(data, rows[eid], expected[eid], is_body)
            if rows[eid].get('id') != eid: errors.append('Ledger key/ID differs')
            if errors: findings.append({'id':eid,'errors':errors})
    return raw, findings


def audit(M):
    # Rehydrate external audit inputs; geometry remains the live model.
    import sys as _audit_sys
    from pathlib import Path as _AuditPath
    _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
    from source_audit_sidecar import audit_model as _source_audit_model
    M = _source_audit_model(M)
    data = json.loads(DATA_PATH.read_text(encoding='utf-8'))
    raw, findings = validate_ledger(data)
    byid = {e['id']:e for e in M['els']}; checks=[]; retirement=[]; uncovered=[]
    binding = {q['id']:q['errors'] for q in findings if q.get('id')}
    global_errors = [q for q in findings if not q.get('id')]
    for eid, expected in raw['bodies'].items():
        row=data.get('records',{}).get(eid); e=byid.get(eid); errors=list(binding.get(eid,[]))
        check={'id':eid,'method':'Original actual device body core; arrows and open linework excluded',
            'reference':expected['reference'],'source_kind':'source_device_body_graphic_core',
            'proof_scope':'body_graphic_XY_and_bbox_only','source_xy':expected['xy'],
            'source_primitives':[[p['drawing'],p['poly']] for p in expected['core']['parts']],
            'physical_ports_dimensions_Z_rotation_material_mounting_verified':False}
        if e is None or row is None:
            uncovered.append(eid); errors.append('Missing exact source/model body identity')
        else:
            a=e.get('a') or {}; s=row['source']; g=e['g']
            if (e['c'],e.get('t'),e['l'],g[0]) != ('M.outlet',expected['q']['type'],expected['level'],'b'):
                errors.append('Model source identity/kind differs')
            if e.get('m') != row['prototype'].get('m'):
                errors.append('Procedural display material guard differs')
            for key in ('source_primitives','source_pdf_points','source_glyph_bbox_pdf','source_transform',
                        'source_sheet_text','source_body_primitives','source_body_pdf_points','source_body_bbox_pdf',
                        'source_body_kind','source_body_component_index','source_graphic_dimensions_cm'):
                if a.get(key) != s.get(key): errors.append('Model source metadata differs: '+key)
            if a.get('source_raw_items') != [p['raw_items'] for p in s['source_bound_primitives']]:
                errors.append('Model original operators differ')
            if a.get('source_record_sha256') != row['source_record_sha256'] or a.get('source_hvac_outlet_record') != eid:
                errors.append('Model source record identity/fingerprint differs')
            if a.get('source_geometry_review') != 'body_graphic_only' or a.get('source_locked_xy') is not True:
                errors.append('Model body source evidence scope differs')
            if any(a.get(k) for k in ('source_Z_verified','source_dimensions_verified','source_mount_verified',
                'source_material_verified','source_rotation_verified','source_contact_verified','source_ports_verified')):
                errors.append('Unsupported physical source acceptance')
            graphic=['b']+[round(v,1) for v in expected['xy']]+[round(v,1) for v in expected['dimensions']]+[0]
            if g[:6] != graphic: errors.append('Model graphic proxy differs from actual body core')
            base=[round(v-float(a.get('ceil_dz',0)),3) for v in g[6:8]]
            if base != row['normalized_assumed_Z_base_m']:
                errors.append('Assumed procedural Z base changed without justified ceiling offset')
            delta=math.dist(g[1:3],expected['xy']); check['deviation_cm']=delta
            metadata=math.dist(a.get('source_xy',[1e10,1e10]),expected['xy']);check['metadata_deviation_cm']=metadata
            if delta>TOL or metadata>TOL: errors.append('Source body anchor exceeds existing 0.2cm limit')
            check.update(source_anchor_deviation_cm=0.0,source_transform_deviation_cm=0.0)
        check.update(errors=errors, **{'pass':not errors and not global_errors}); checks.append(check)
    for eid, expected in raw['retired'].items():
        errors=list(binding.get(eid,[]))
        if eid in byid: errors.append('False outlet body remains in model')
        retirement.append({'id':eid,'reference':expected['reference'],'source_kind':'raw_fragment_not_device',
            'source_primitives':[[p['drawing'],p['poly']] for p in expected['q']['parts']],
            'errors':errors,'pass':not errors and not global_errors})
    counts=collections.Counter(q['disposition'] for q in raw['inventory'])
    failed_ids={q['id'] for q in checks+retirement if not q['pass']}
    failed_ids.update(q['id'] for q in findings if q.get('id'))
    return {'checks':checks,'retirement_checks':retirement,'findings':findings,'uncovered':uncovered,
        'source_inventory':raw['inventory'],'summary':{'checked':len(checks),
            'findings':len(failed_ids)+len(global_errors),
            'uncovered':len(uncovered),'retired_checked':len(retirement),
            'retired_findings':sum(not q['pass'] for q in retirement),
            'raw_cluster_instances':len(raw['inventory']),'qualified_body_anchors':len(raw['bodies']),
            'legend_cluster_instances':counts['legend_context_not_component'],
            'split_new_body_ids':sum(q['index']>0 for q in raw['bodies'].values()),
            'max_deviation_cm':max((q.get('deviation_cm',0) for q in checks),default=0),
            'source_PDF_sha256':raw['pdf_sha256'],'source_data_sha256':hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
            'source_Z_mounting_and_physical_body_accepted':False,
            'limit':'Actual body graphics only; arrows/open lines are retired; dimensions are symbolic, not neck/manufacturer dimensions; physical Z/ports/mount/material remain unverified.'}}
