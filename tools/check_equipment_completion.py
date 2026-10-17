"""Reopen original source and verify the two equipment extents without writing it."""
import copy
import hashlib
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'pipeline'))
import equipment_completion as EC
import reg


def serial(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return [serial(x) for x in value]


def drawing(d, index):
    return dict({k: serial(d.get(k)) for k in
                 ('layer', 'type', 'fill', 'color', 'closePath', 'rect', 'items')},
                drawing_index=index)


def trace(t, index):
    return dict(trace_index=index, text=''.join(chr(c[0]) for c in t['chars']),
                bbox=serial(t['bbox']), chars=serial(t['chars']),
                dir=serial(t['dir']), size=t['size'], layer=t.get('layer'))


def source_registration(drawings):
    grids = [d for d in drawings if d.get('layer') and
             ('GRID' in d['layer'].upper() or 'AXIS' in d['layer'].upper()) and
             'IDEN' not in d['layer'].upper()]
    vv, hh = reg.grid_clusters(None, layers=None, drawings=grids, minlen=50)
    return reg.register_free(vv, hh)


def _sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def audit(M):
    # Rehydrate external audit inputs; geometry remains the live model.
    import sys as _audit_sys
    from pathlib import Path as _AuditPath
    _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
    from source_audit_sidecar import audit_model as _source_audit_model
    M = _source_audit_model(M)
    import fitz
    D = EC.data()
    path = Path(os.environ.get('C4_ELEC1_PDF', D['original_pdf']['path']))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == D['original_pdf']['sha256'], 'Original PDF changed'
    doc = fitz.open(path)
    raw = {page: {'drawings': doc[page - 1].get_drawings(),
                  'traces': doc[page - 1].get_texttrace()} for page in (10, 17)}
    registration = source_registration(raw[10]['drawings'])
    by = {}
    for e in M['els']:
        by.setdefault(e['id'], []).append(e)
    records = []
    for id, r in D['records'].items():
        assert r['source_record_sha256'] == _sha({k: v for k, v in r.items() if k != 'source_record_sha256'})
        s = r['source']
        assert registration == s['registration'], 'Original plan registration changed'
        assert len(by.get(id, [])) == 1, 'Equipment identity missing/duplicate: ' + id
        e = by[id][0]
        assert e['g'] == r['after_g'], 'Unapplied equipment geometry: ' + id
        assert e['g'][6:] == r['before_e']['g'][6:], 'Absolute height changed'
        for q in s['plan_drawings']:
            assert drawing(raw[10]['drawings'][q['drawing_index']], q['drawing_index']) == q
        for q in s['plan_labels']:
            assert trace(raw[10]['traces'][q['trace_index']], q['trace_index']) == q
        for evidence in s['dimension_evidence']:
            p = raw[evidence['page']]
            for q in evidence['traces']:
                assert trace(p['traces'][q['trace_index']], q['trace_index']) == q
            for q in evidence['drawings']:
                assert drawing(p['drawings'][q['drawing_index']], q['drawing_index']) == q
        # Independently reconstruct placement from the plan; NTS details supply numbers only.
        rects = [q['rect'] for q in s['plan_drawings']]
        anchor = [(min(x[0] for x in rects) + max(x[2] for x in rects)) / 2,
                  (min(x[1] for x in rects) + max(x[3] for x in rects)) / 2]
        assert anchor == s['plan_anchor_pdf']
        xy = [anchor[0] * registration['s'] + registration['ox'],
              -anchor[1] * registration['s'] + registration['oy']]
        assert [round(x, 4) for x in xy] == e['g'][1:3]
        a = e['a']
        assert a['equipment_completion'] and a['source_plan_dimensions_literal_verified']
        assert a['source_relative_height_verified'] == r['relative_height_verified']
        assert all(a[k] is False for k in ('source_absolute_Z_verified', 'source_Z_verified',
                   'source_physical_body_verified', 'source_material_verified', 'source_mount_verified',
                   'source_ports_verified', 'source_contact_verified', 'source_colour_verified'))
        records.append({'id': id, 'before_g': r['before_e']['g'], 'after_g': e['g'],
                        'literal_dimensions_cm': r['literal_dimensions_cm'],
                        'source_record_sha256': r['source_record_sha256']})
    hv = D['records']['E.panel-G-ER002']
    hv_plan = hv['source']['dimension_evidence'][0]
    assert [x['text'] for x in hv_plan['traces']] == ['90', '90', '90', '250', 'FEEDER', 'FEEDERTRANSFORMER']
    assert hv['literal_dimensions_cm'] == [sum([90, 90, 90]), 250, 235]
    assert hv['after_g'][3:6] == [270, 250, 0]
    # These are three adjacent traced rectangles, each with its own 90 dimension.
    bays = sorted((x['rect'] for x in hv_plan['drawings'] if x['layer'] == 'E.POWER'), key=lambda x: x[0])
    assert len(bays) == 3
    assert all(b[1] == bays[0][1] and b[3] == bays[0][3] for b in bays)
    assert all(abs(bays[i][2] - bays[i + 1][0]) < 1 for i in (0, 1))
    gen = D['records']['E.gen-G-ER001']
    assert [x['text'] for x in gen['source']['dimension_evidence'][0]['traces']] == ['GENERATOR', '110', '260']
    assert gen['literal_dimensions_cm'] == [260, 110, None]
    assert gen['after_g'][3:6] == [260, 110, 90]
    assert gen['relative_height_verified'] is False
    return {'schema': 'c4.equipment-completion-source-audit.v1', 'pass': True,
            'source_pdf_sha256': D['original_pdf']['sha256'], 'records': records,
            'literal_plan_extents': 2, 'relative_heights_verified': 1,
            'absolute_Z_verified': 0, 'material_or_ports_verified': 0,
            'registration': registration}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=Path, default=REPO / 'src/model.json')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    from source_audit_sidecar import audit_model
    M = audit_model(json.loads(args.model.read_text()))
    before = copy.deepcopy(M)
    result = EC.apply(M)
    proof = audit(M)
    assert result['changed'] in (0, 2)
    controlled = set(EC.data()['records'])
    assert [e for e in M['els'] if e['id'] not in controlled] == [e for e in before['els'] if e['id'] not in controlled]
    reapplied = copy.deepcopy(M)
    assert EC.apply(reapplied)['changed'] == 0 and reapplied == M
    guard_cases = []
    for mode in ('changed_geometry', 'missing_identity', 'duplicate_identity'):
        bad = copy.deepcopy(before)
        rows = [e for e in bad['els'] if e['id'] == 'E.gen-G-ER001']
        if mode == 'changed_geometry':
            rows[0]['g'][3] += 1
        elif mode == 'missing_identity':
            bad['els'].remove(rows[0])
        else:
            bad['els'].append(copy.deepcopy(rows[0]))
        frozen = copy.deepcopy(bad)
        try:
            EC.apply(bad)
        except ValueError:
            assert bad == frozen, 'Batch partially mutated on validation failure'
            guard_cases.append(mode)
        else:
            raise AssertionError('Missing safety guard: ' + mode)
    proof.update(apply=result, element_count_before=len(before['els']), element_count_after=len(M['els']),
                 unrelated_elements_unchanged=True, idempotent=True,
                 atomic_guard_cases=guard_cases, source_model_written=False)
    payload = json.dumps(proof, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(payload)
    print(payload)
