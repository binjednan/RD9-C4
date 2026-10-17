# -*- coding: utf-8 -*-
"""Focused source replay and preservation checks. Never writes a model."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline'))
import stair_concrete_completion as SC


def check(model_path, output=None):
    original_bytes = Path(model_path).read_bytes()
    from source_audit_sidecar import audit_model
    original = audit_model(json.loads(original_bytes))
    if original.get('meta', {}).get('owner_render_only'):
        # No conformity mutations or repeated full-model copies in drawing-only mode.
        from check_core_stairs_source_surfaces import _solid_surface_matches
        D = SC.data()
        normalized = []
        for e in original['els']:
            r = D['records'].get(e['id'])
            if r and e.get('a', {}).get('source_surface_thickness_m') is not None:
                if not _solid_surface_matches(e['g'], r['before_identity']['g'], e['a']['source_surface_thickness_m']):
                    raise ValueError('Stair source surface / assumed thickness changed: ' + e['id'])
                e = {**e, 'g': r['before_identity']['g']}
            normalized.append(e)
        result = SC.audit({**original, 'els': normalized}, verify_images=False)
        return {'pass': result['pass'], 'audit': result, 'tests': [{'name': 'source_surfaces_and_concrete_literals', 'pass': result['pass']}], 'no_model_file_write': True,
                'scope': 'Original source surfaces and numeric concrete conflict facts; assumed finish thickness is not concrete approval.'}
    M = copy.deepcopy(original)
    results = []
    def test(name, ok):
        results.append({'name': name, 'pass': bool(ok)})
        if not ok:
            raise AssertionError(name)
    applied = SC.apply(M)
    SC.apply_issues(M)
    D = SC.data()
    ids = set(D['records'])
    test('five_source_property_bindings_zero_geometry_changes', applied['reviewed_assemblies'] == 5 and applied['geometry_changes'] == 0)
    test('element_order_identity_and_geometry_preserved',
         [e['id'] for e in M['els']] == [e['id'] for e in original['els']] and
         all(e['g'] == b['g'] for e, b in zip(M['els'], original['els'])))
    for e, b in zip(M['els'], original['els']):
        c = copy.deepcopy(e)
        if e['id'] in ids:
            c['a'].pop(SC.ATTRIBUTE)
            baseline = copy.deepcopy(b)
            baseline['a'].pop(SC.ATTRIBUTE, None)
            test('only_owned_evidence_changed_' + e['id'], c == baseline)
        elif e != b:
            raise AssertionError('Unrelated element changed ' + e['id'])
    test('all_unrelated_elements_preserved', all(e == b for e, b in zip(M['els'], original['els']) if e['id'] not in ids))
    v = copy.deepcopy(M)
    second = SC.apply(M)
    SC.apply_issues(M)
    test('repeat_is_exact_noop', second['evidence_bound_this_apply'] == 0 and M == v)
    rows = SC.issue_records(M)
    test('conflict_explicit_no_false_body_resolution',
         sum(r['status'] == 'source_conflict' for r in rows) == 1 and
         all(not e['a'][SC.ATTRIBUTE]['full_body_coordinates_matched'] for e in M['els'] if e['id'] in ids))
    r = list(D['records'].values())
    test('ground45cm_not_silently10cm', r[0]['review']['finished_minus_concrete_datums_cm'] == [45, 10])
    test('landing_concrete_bottoms_from_literal_vertical25cm',
         [x['review']['source_concrete_landing_top_bottom_m'] for x in r[3:]] == [[2.05, 1.8], [3.85, 3.6]])
    for name, mutate in [
        ('unknown_geometry', lambda v: v['els'][next(i for i, e in enumerate(v['els']) if e['id'] in ids)]['g'][1][0].__setitem__(0, -999)),
        ('partial_evidence', lambda v: v['els'][next(i for i, e in enumerate(v['els']) if e['id'] in ids)]['a'].pop(SC.ATTRIBUTE)),
        ('unknown_evidence', lambda v: v['els'][next(i for i, e in enumerate(v['els']) if e['id'] in ids)]['a'][SC.ATTRIBUTE].__setitem__('full_body_coordinates_matched', True)),
        ('duplicate_identity', lambda v: v['els'].append(copy.deepcopy(v['els'][0]))),
    ]:
        bad = copy.deepcopy(M)
        mutate(bad)
        before = copy.deepcopy(bad)
        rejected = False
        try:
            SC.apply(bad)
        except ValueError:
            rejected = True
        test('preflight_rejects_' + name + '_before_write', rejected and bad == before)
    audit = SC.audit(M)
    test('original_PDF_operators_texts_annotations_and_renderings_replay', audit['pass'])
    test('source_conflict_stays_unresolved', audit['source_conflicts_resolved'] is False)
    test('model_file_not_written', Path(model_path).read_bytes() == original_bytes)
    proof = {'schema': 'c4.stair_concrete_completion.proof.v1',
             'pass': all(t['pass'] for t in results) and audit['pass'],
             'model_input': str(model_path), 'model_sha256': hashlib.sha256(original_bytes).hexdigest(),
             'tests': results, 'audit': audit, 'no_model_file_write': True}
    if output:
        Path(output).write_text(json.dumps(proof, ensure_ascii=False, indent=2) + '\n')
    return proof


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--model', type=Path, default=ROOT / 'src/model.json')
    p.add_argument('--output', type=Path)
    a = p.parse_args()
    proof = check(a.model, a.output)
    print(json.dumps({'pass': proof['pass'], 'tests': len(proof['tests']),
                      'source_checks': len(proof['audit']['source_checks']),
                      'geometry_changes': 0, 'source_conflicts_resolved': False}, ensure_ascii=False))
