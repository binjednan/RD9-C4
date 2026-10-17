# -*- coding: utf-8 -*-
"""Restore proven legacy electrical symbol XY; keep level, Z and section intact.

The data binds deterministic legacy IDs to ordered raw PDF vector clusters,
checks cluster dimensions against that class's actual legend exemplar, and uses
the current measured sheet transform. This proves the drawn symbol anchor only.
Physical device size, front face, mounting direction and elevation remain apart.
"""
import hashlib, json, math, os

DATA = os.path.join(os.path.dirname(__file__), 'data', 'electrical_source_restore.json')
SEMANTIC_DATA = os.path.join(os.path.dirname(__file__), 'data', 'electrical_symbol_semantics.json')
TOL_CM = .2  # Existing independent source position threshold, unchanged.
XY_GUESS_KEYS = ('guess_from','guess_host','guess_kind','guess_cm','guess_conf','guess_intent','guess_conv','snap_cm','snap_note')
NOTE = 'موضع XY أعيد إلى مركز الرمز المرسوم من خطوط PDF الأصلية؛ لا يعني وجه جدار أو مقاس تنفيذ أو منسوبًا مؤكدًا. لم يتغير المستوى أو Z أو اتجاه الجسم.'


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def apply(M, els=None):
    els = M['els'] if els is None else els
    data = json.load(open(DATA, encoding='utf-8'))
    semantic_data = json.load(open(SEMANTIC_DATA, encoding='utf-8')) if os.path.exists(SEMANTIC_DATA) else {}
    semantic_records = semantic_data.get('records', {})
    ids = {e['id']:e for e in els}
    corrections, missing, mismatched = [], [], []
    locked = 0
    retired, semantic_targets = [], []
    log = M.setdefault('meta', {}).setdefault('drawing_corrections', {})
    for eid, proof in data['source_anchors'].items():
        expected = (proof['expected_category'], proof['expected_type'], proof['expected_level'])
        semantic = semantic_records.get(eid, {})
        semantic_expected = (semantic.get('expected_category'), semantic.get('expected_type'), semantic.get('expected_level'))
        # A later primitive/legend decomposition supersedes this same archive
        # cluster only when its identity, page, raw indices and registration bind
        # exactly. It never grants authority to a merely similar model element.
        semantic_bound = bool(semantic.get('class_verified') and semantic_expected == expected
                              and semantic.get('source') == proof['source']
                              and semantic.get('raw_drawing_primitives') == proof['raw_drawing_primitives']
                              and semantic.get('registration') == proof['registration'])
        e = ids.get(eid)
        if e is None:
            if semantic_bound and semantic.get('action') == 'remove_nondevice_fragment':
                retired.append({'id':eid,'source':proof['source'],'semantic_record_sha256':semantic['record_sha256'],
                                'reason':'Original cluster proved to be a nondevice fragment and retired by semantic review'})
                continue
            missing.append(eid);continue
        actual = (e['c'], e.get('t'), e['l'])
        canonical = (semantic.get('target_category', expected[0]), semantic.get('target_type', expected[1]), expected[2])
        semantic_applied = bool(semantic_bound and e.get('a', {}).get('source_semantics_checked')
                                and e.get('a', {}).get('source_semantics_record_sha256') == semantic['record_sha256']
                                and actual in (expected, canonical))
        if (expected != actual and not semantic_applied) or e['g'][0] not in ('b','cyl'):
            mismatched.append({'id':eid,'expected':list(expected),'actual':list(actual),'geometry':e['g'][0]});continue
        g, a = e['g'], e.setdefault('a', {})
        before = list(g[1:3]);target = semantic['source_xy_cm'] if semantic_applied else proof['source_xy_cm']
        delta = math.dist(before,target)
        old_guess = {k:a[k] for k in XY_GUESS_KEYS if k in a}
        if delta > TOL_CM:
            before_g_sha = _hash(g)
            g[1],g[2] = target
            row = {'element':eid,'level':e['l'],'source':proof['source'],
                   'old_xy_cm':before,'new_xy_cm':list(target),'delta_cm':delta,
                   'old_geometry_sha256':before_g_sha,'new_geometry_sha256':_hash(g),
                   'source_record_sha256':semantic['record_sha256'] if semantic_applied else proof['record_sha256'],
                   'source_file':'pipeline/data/electrical_symbol_semantics.json' if semantic_applied else 'pipeline/data/electrical_source_restore.json',
                   'source_anchor':semantic['source_kind'] if semantic_applied else 'drawn_symbol_cluster_bbox_centre','prior_xy_placement':old_guess,
                   'note':NOTE,'scope':'model_xy_correction_only','z_unchanged':True,'level_unchanged':True}
            corrections.append(row)
            if eid not in log:log[eid]=row
            elif log[eid].get('source_record_sha256') != row['source_record_sha256']:
                row['previous_correction']=log[eid];log[eid]=row
        # Obsolete nearest-host placement fields describe the former position.
        # Their evidence stays in the correction log, never as current support.
        if old_guess and eid in log:
            log[eid].setdefault('prior_xy_placement',old_guess)
        for k in XY_GUESS_KEYS:a.pop(k,None)
        if semantic_applied:
            # Keep the more specific glyph/legend proof intact between ESR and
            # ESS on repeated post cycles. Coordinates, level and Z remain under
            # the same literal source restrictions.
            a['source_locked_xy']=True
            semantic_targets.append({'id':eid,'canonical_identity':list(actual),'semantic_record_sha256':semantic['record_sha256']})
        else:
            a.update(source_locked_xy=True, source_page=proof['source'],
                     source_xy=list(target),source_pdf_points=[proof['source_pdf_centre_pt']],
                     source_transform=proof['registration'],source_primitives=proof['raw_drawing_primitives'],
                     source_kind='drawn_symbol_cluster_bbox_centre',source_anchor='drawn_symbol_cluster_bbox_centre',
                     source_electrical_legacy_record=proof['archive_record'],source_record_sha256=proof['record_sha256'],
                     source_xy_note=NOTE)
        locked += 1
    stats = {'qualified_source_anchors':len(data['source_anchors']),'locked':locked,'xy_corrected':len(corrections),
             'missing_ids':missing,'identity_mismatches':mismatched,'semantic_review':len(data['semantic_review']),
             'retired_nondevice_source_ids':retired,'canonical_semantic_targets':semantic_targets,
             'threshold_cm':TOL_CM,'height_or_level_changes':0,'source_file':'pipeline/data/electrical_source_restore.json',
             'source_data_sha256':_hash(data),'source_pdf_sha256':data['source_pdf_sha256'],
             'classification_limit':data['classification_limit']}
    M.setdefault('meta', {})['electrical_source_restore'] = stats
    return dict(stats,corrections=corrections)
