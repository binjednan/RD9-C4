# -*- coding: utf-8 -*-
"""One scoped source batch, staged first and committed without reapplying.

This does not call post_model, lifecycle.run/apply, connector generators or build.
LC reuse is permitted only for exact role/group/geometry/directed-link inputs.
The previous exit0 is historical evidence bound to the before file, not a new
physical-network test. Current source surfaces remain open/derived assemblies.
"""
import argparse
import collections
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
TOOLS = ROOT / 'tools'
for directory in (HERE, TOOLS):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
BASE_MODEL_SHA = '58d8e436b27f0bb2767fd7349f64fb5ca7cec8c2254f31e620e8074205fd6acd'
BASELINE_SHA = '3217be0ceaa5508e83af9e4367841e020f8fc52ceff2c5cb9acbabb11f51fec1'
SCALAR_INDEX_KEYS = {'e', 'ei', 'element_index', 'el_index', 'index_in_els',
                     'hostidx', 'host_idx', 'host_index', 'host_e'}
LIST_INDEX_KEYS = {'eis', 'element_indices', 'els_indices', 'indices_in_els'}


def encoded(value, ordered=False):
    return json.dumps(value, ensure_ascii=False, sort_keys=ordered,
                      separators=(',', ':')).encode('utf-8')


def digest(value):
    return hashlib.sha256(encoded(value, True)).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cc_geometry_sha(M):
    # Match the established CC hash exactly, including JSON's ASCII default.
    return hashlib.sha256(json.dumps(sorted((e['id'], e['g']) for e in M['els']),
                                    separators=(',', ':')).encode()).hexdigest()


def by_id(M):
    result = {e['id']: e for e in M['els']}
    if len(result) != len(M['els']):
        raise ValueError('Duplicate element IDs')
    return result


def remap_index_refs(M, old_to_new_indices, retired_indices=None,
                     include_lifecycle=True, include_clashes=True):
    """Remap only declared element-index fields, never drawing/triangle indices.

    Exposed for the future post hook. Pass include_lifecycle/include_clashes=False
    when those arrays are about to be rebuilt. A retired reference is an error,
    not a reason to silently drop a clash, terminal, guess or host assignment.
    """
    mapping = {int(k): int(v) for k, v in old_to_new_indices.items()}
    retired = {int(v) for v in (retired_indices or [])}
    changes = []

    def scalar(index, path):
        if not isinstance(index, int) or isinstance(index, bool):
            raise ValueError('Element reference must be an integer: ' + path)
        if index in retired or index not in mapping:
            raise ValueError('Retired/unmapped element reference: ' + path + '=' + str(index))
        new = mapping[index]
        changes.append({'path': path, 'before': index, 'after': new})
        return new

    def walk(node, path=''):
        if isinstance(node, dict):
            for key in list(node):
                value = node[key]
                where = path + '/' + key
                if key in SCALAR_INDEX_KEYS and isinstance(value, int) and not isinstance(value, bool):
                    node[key] = scalar(value, where)
                elif key in LIST_INDEX_KEYS and isinstance(value, list):
                    node[key] = [scalar(v, where + '/' + str(i)) for i, v in enumerate(value)]
                elif key != 'g':  # Vertex/face indices belong to their primitive.
                    walk(value, where)
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, path + '/' + str(i))

    # All current generic e/ei/hostidx references, including guesses/items/e.
    # Exclude the packed LC arrays, which have their own parallel-array guard.
    for key, value in M.items():
        if key not in ('lifecycle', 'clashes'):
            walk(value, '/' + key)
    if include_clashes:
        for i, clash in enumerate(M.get('clashes', [])):
            for key in ('a', 'b'):
                clash[key] = scalar(clash[key], '/clashes/' + str(i) + '/' + key)
    if include_lifecycle:
        for system in M.get('lifecycle', {}).get('systems', []):
            n = len(system['ri'])
            if len(system['rd']) != n or len(system['rk']) != n:
                raise ValueError('LC ri/rd/rk alignment: ' + system['id'])
            rd, rk = copy.deepcopy(system['rd']), system['rk']
            for key in ('src', 'ri', 'x', 'o'):
                system[key] = [scalar(v, '/lifecycle/' + system['id'] + '/' + key + '/' + str(i))
                               for i, v in enumerate(system[key])]
            if system['rd'] != rd or system['rk'] != rk:
                raise ValueError('LC distance/role changed during remap')
    return {'schema': 'c4.element-index-remap.v1', 'references': len(changes),
            'changed_indices': sum(q['before'] != q['after'] for q in changes),
            'retired_references': 0, 'bindings': changes}


def lc_dependencies(M):
    import lifecycle as LC
    result = {}
    for sd in LC.SYSTEMS:
        source = [e['id'] for e in M['els'] if sd['source'](e)]
        edge = [e['id'] for e in M['els'] if sd.get('edge') and sd['edge'](e)]
        terminal = [e for e in M['els'] if sd['terminal'](e)]
        units = collections.OrderedDict()
        group = sd.get('group')
        for e in terminal:
            units.setdefault(group(e) if group else e['id'], []).append(e['id'])
        variants = [[name, [e['id'] for e in M['els'] if predicate(e)]]
                    for name, predicate in sd['variants']]
        eligible = set(source) | set(edge) | {e['id'] for e in terminal}
        for _, members in variants:
            eligible.update(members)
        bodies = []
        for e in M['els']:
            if e['id'] not in eligible:
                continue
            a = e.get('a') or {}
            bodies.append({'id': e['id'], 'c': e['c'], 'l': e['l'], 'm': e.get('m'), 'g': e['g'],
                           'from': a.get('from'), 'to': a.get('to'), 'sys': a.get('sys'),
                           'connector': a.get('connector'), 'no_connectors': a.get('no_connectors')})
        result[sd['id']] = {'source': source, 'edge': edge,
            'terminal': [e['id'] for e in terminal], 'units': list(units.items()),
            'variants': variants, 'eligible_fullg_directed': bodies,
            'rules': {k: sd.get(k) for k in ('sink', 'pass_terminal', 'no_connectors', 'family')},
            'tol': LC.TOL}
    if len(result) != 20:
        raise ValueError('Expected exactly20 LC systems')
    return result


def packed_lifecycle_identity(M):
    ids = [e['id'] for e in M['els']]
    out = copy.deepcopy(M['lifecycle'])
    for system in out['systems']:
        if len(system['ri']) != len(system['rd']) or len(system['ri']) != len(system['rk']):
            raise ValueError('Packed LC arrays do not align')
        for key in ('src', 'ri', 'x', 'o'):
            system[key] = [ids[i] for i in system[key]]
    return out


def verify_source_audit(audit, expected, label):
    summary = audit.get('summary') or {}
    errors = list(audit.get('global_findings') or [])
    if summary.get('findings') != 0 or summary.get('uncovered') != 0 or audit.get('uncovered'):
        errors.append('nonzero/missing findings or uncovered summary')
    checks = audit.get('checks') or []
    ids = [q.get('id') for q in checks]
    if len(ids) != len(set(ids)) or set(ids) != set(expected):
        errors.append('exact owned source check set differs')
    for section in ('checks', 'source_checks', 'source_glyph_checks', 'pending', 'retirement'):
        for check in audit.get(section) or []:
            if check.get('errors') or check.get('pass') is False:
                errors.append(section + ':' + str(check.get('id', check.get('drawing_index'))))
    if errors:
        raise ValueError(label + ' source audit failed: ' + str(errors))


def aggregate_reliability(M):
    import reliability as REL
    overall = collections.Counter()
    layer, level = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
    axes = {k: collections.Counter() for k in ('xy', 'z', 'spec')}
    for e in M['els']:
        q = e.get('q')
        if not isinstance(q, str) or len(q) != 3:
            raise ValueError('Missing existing reliability grade: ' + e['id'])
        grade = REL.overall(q)
        overall[grade] += 1
        layer[e['c'][0]][grade] += 1
        level[e['l']][grade] += 1
        for i, axis in enumerate(('xy', 'z', 'spec')):
            axes[axis][q[i]] += 1
    M.setdefault('meta', {})['reliability'] = {'overall': dict(overall),
        'layer': {k: dict(v) for k, v in layer.items()}, 'level': {k: dict(v) for k, v in level.items()},
        'axes': {k: dict(v) for k, v in axes.items()}}


def protected_objects(before, after, core_data, heater_data):
    old, new = by_id(before), by_id(after)
    owned = set(core_data['before_records'])
    heaters = set(heater_data['records'])
    retired = set(core_data['exactretired_ids'])
    if set(old) - set(new) != retired or set(new) - set(old):
        raise ValueError('Unexpected element retirement/addition')
    unchanged = []
    for eid in sorted(set(old) - owned - heaters):
        if old[eid] != new[eid]:
            raise ValueError('Unrelated complete element changed: ' + eid)
        unchanged.append([eid, digest(old[eid])])
    for eid in heaters:
        a, b = copy.deepcopy(old[eid]), copy.deepcopy(new[eid])
        record = heater_data['records'][eid]
        if b['t'] != record['after_type'] or b.get('mark') != record['after_mark']:
            raise ValueError('Heater final property differs: ' + eid)
        for value in (a, b):
            value.pop('t', None); value.pop('mark', None)
            for key in ('cap_l', 'cap_known', 'source_heater_capacity_review'):
                value.get('a', {}).pop(key, None)
        if a != b:
            raise ValueError('Heater body/other attributes changed: ' + eid)
    for eid in owned - retired:
        for key in ('id', 'c', 'l', 'm', 'grp', 'mark', 'u', 'u2', 'stage'):
            if old[eid].get(key) != new[eid].get(key):
                raise ValueError('Stair preserved field changed: ' + eid + ':' + key)
    return {'unrelated_full_objects_exact': len(unchanged), 'unrelated_full_objects_sha256': digest(unchanged),
            'heater_property_only': len(heaters),
            'heater_types_changed': sum(old[i]['t'] != new[i]['t'] for i in heaters),
            'retired_exact_ids': sorted(retired), 'replaced_stair_assemblies': len(owned - retired)}


def reuse_coordination(M, baseM, heater_ids):
    import coordination_review as CR
    old, new = by_id(baseM), by_id(M)
    baseline = baseM['coordinationReview']
    by_case = {q['id']: q for q in baseline['issues']}
    if len(by_case) != len(baseM['clashes']):
        raise ValueError('Prior CR issue set is not bound to clashes')
    issues, pair_proofs, changed = [], [], []
    for c in M['clashes']:
        a, b = M['els'][c['a']], M['els'][c['b']]
        if a['id'] != c['ea'] or b['id'] != c['eb']:
            raise ValueError('Clash index/ID mismatch')
        prior = by_case[c['id']]
        if (prior['ea'], prior['eb']) != (a['id'], b['id']):
            raise ValueError('CR pair identity differs')
        for e in (a, b):
            if e['g'] != old[e['id']]['g'] or e['c'] != old[e['id']]['c'] or e['l'] != old[e['id']]['l']:
                raise ValueError('Cannot reuse clash witness for changed pair body: ' + e['id'])
        pair_proofs.append([c['id'], a['id'], digest(a['g']), b['id'], digest(b['g'])])
        if {a['id'], b['id']} & heater_ids:
            q = CR.classify(M, c, geometry=copy.deepcopy(prior['geometry']))
            changed.append(c['id'])
        else:
            q = copy.deepcopy(prior)
            q['resolution_status'] = c.get('st', 'open')
        issues.append(q)
    result = copy.deepcopy(baseline)
    result['issues'] = issues
    result['counts'] = dict(collections.Counter(q['classification']['lane'] for q in issues))
    result['geometry_counts'] = dict(collections.Counter(q['geometry']['state'] for q in issues))
    result['source_conflicts'] = [CR._source_conflict(q) for q in M.get('drawingIssues', []) if q.get('status') == 'source_conflict']
    result['zconflicts'] = [q for q in result['source_conflicts'] if q.get('zconflict')]
    result['review_cases'] = [q for q in issues if q.get('case_audit_ar')]
    result['coverage'].update(existing_clashes=len(M['clashes']), reviewed=len(issues), uncovered=0,
        source_conflicts=len(result['source_conflicts']), source_zconflicts=len(result['zconflicts']),
        geometry_unsupported=sum(bool(q['geometry'].get('unsupported_geometry_elements')) for q in issues),
        geometry_unproved=sum(q['geometry']['state'] == 'unproved' for q in issues))
    result['model_geometry_sha256'] = CR._hash([[e['id'], e['g']] for e in M['els']])
    result['incremental_reuse'] = {'pair_fullg_sha256': digest(pair_proofs), 'existing_pairs': len(pair_proofs),
        'heater_card_reclassified_pairs': changed, 'new_surface_clashes_checked': False,
        'limit_ar': 'أعيدت شواهد582زوجًا محفوظًا بعد تطابق الجسمين؛ لا يثبت غياب تعارضات جديدة مع أسطح الدرج المفتوحة.'}
    M['coordinationReview'] = result
    return result['incremental_reuse']


def _source_files(core_data, heater_data):
    paths = [Path(__file__), ROOT/'src/model.json', HERE/'data/component_coverage.json', HERE/'data/lifecycle_baseline.json']
    for name in ('water_heater_capacity_source', 'core_stairs_source_surfaces', 'lifecycle', 'drawing_deviations',
                 'clash_log', 'coordination_review', 'reliability', 'inventory', 'support'):
        paths.append(HERE/(name + '.py'))
    for name in ('water_heater_capacity_source', 'core_stairs_source_surfaces'):
        paths.extend([HERE/'data'/(name + '.json'), TOOLS/('check_' + name + '.py')])
    paths.extend([TOOLS/'check_component_coverage.py', TOOLS/'check_geometry_integrity.py'])
    def walk(v):
        if isinstance(v, dict):
            for q in v.values(): walk(q)
        elif isinstance(v, list):
            for q in v: walk(q)
        elif isinstance(v, str) and v.lower().endswith('.pdf') and Path(v).is_file():
            paths.append(Path(v))
    walk(core_data); walk(heater_data)
    return {str(p.resolve()): file_sha(p) for p in sorted(set(paths))}


def prepare(model_path, coverage_path, lc_proof_path, stage_dir):
    """Apply this batch once in memory, then write only scratch staging files."""
    import core_stairs_source_surfaces as CSF
    import water_heater_capacity_source as H
    import check_core_stairs_source_surfaces as CG
    import check_water_heater_capacity_source as HG
    import check_geometry_integrity as GI
    import check_component_coverage as CC
    import drawing_deviations as DD
    import clash_log as CL
    import inventory as INV
    import reliability as REL
    model_path, coverage_path, lc_proof_path = map(Path, (model_path, coverage_path, lc_proof_path))
    original = model_path.read_bytes()
    if hashlib.sha256(original).hexdigest() != BASE_MODEL_SHA:
        raise ValueError('Batch requires the exact approved current before model58d8…')
    if file_sha(HERE/'data/lifecycle_baseline.json') != BASELINE_SHA:
        raise ValueError('Approved selective LC baseline changed')
    prior_lc = json.loads(lc_proof_path.read_text())
    if not (prior_lc.get('pass') is True and prior_lc.get('exit_code') == 0 and
            not prior_lc.get('regression_lines') and prior_lc.get('model_file_sha256') == BASE_MODEL_SHA and
            prior_lc.get('baseline_file_sha256') == BASELINE_SHA):
        raise ValueError('Historical LC exit0 proof is not bound to this before model/baseline')
    baseM, base_report = json.loads(original), json.loads(coverage_path.read_text())
    if base_report['model_geometry_sha256'] != cc_geometry_sha(baseM):
        raise ValueError('Before component report is stale')
    core_data = CSF.data()
    heater_data = json.loads((HERE/'data/water_heater_capacity_source.json').read_text())
    input_files = _source_files(core_data, heater_data)
    dependencies_before = lc_dependencies(baseM)
    packed_before = packed_lifecycle_identity(baseM)
    M = copy.deepcopy(baseM)
    heater_stats = H.apply(M)
    core_stats = CSF.apply(M)
    M.setdefault('types', {}).update(CSF.TYPES)
    after_expected = CSF.compile_after(core_data)
    active = by_id(M)
    for eid in after_expected:
        active[eid]['q'] = REL.grade(active[eid], M['types'])
    protected = protected_objects(baseM, M, core_data, heater_data)
    dependencies_after = lc_dependencies(M)
    if dependencies_before != dependencies_after:
        changed = [s for s in dependencies_before if dependencies_before[s] != dependencies_after.get(s)]
        raise ValueError('LC dependencies changed; isolated reanalysis required: ' + str(changed))
    before_indices = {e['id']: i for i, e in enumerate(baseM['els'])}
    after_indices = {e['id']: i for i, e in enumerate(M['els'])}
    mapping = {old: after_indices[eid] for eid, old in before_indices.items() if eid in after_indices}
    retired_indices = [before_indices[eid] for eid in core_data['exactretired_ids']]
    reference_proof = remap_index_refs(M, mapping, retired_indices)
    if packed_lifecycle_identity(M) != packed_before:
        raise ValueError('LC packed result IDs/distances/roles/tests changed')
    # Numeric references were remapped; preserved bodies remain exact.
    protected = protected_objects(baseM, M, core_data, heater_data)
    heater_audit, core_audit = HG.audit(M), CG.audit(M)
    verify_source_audit(heater_audit, heater_data['records'], 'Heater82')
    verify_source_audit(core_audit, after_expected, 'Core29')
    target_geometry = GI.audit({'els': [active[eid] for eid in after_expected]})
    if not target_geometry['pass']:
        raise ValueError('Target triangle geometry failed: ' + str(target_geometry['findings']))
    DD.apply(M, M['els'])
    CL.merge_into(M, M['els'])
    coordination = reuse_coordination(M, baseM, set(heater_data['records']))
    aggregate_reliability(M)
    coverage = CC.apply_incremental(M, baseM, base_report, core_audit)
    INV.build(M)
    protected_objects(baseM, M, core_data, heater_data)
    if lc_dependencies(M) != dependencies_before or packed_lifecycle_identity(M) != packed_before:
        raise ValueError('Final callbacks changed the reusable LC dependencies/results')
    proof = {'schema': 'c4.targeted-source-batch.v1', 'pass': True,
        'before_model_sha256': BASE_MODEL_SHA, 'before_elements': len(baseM['els']), 'after_elements': len(M['els']),
        'input_files_sha256': input_files, 'before_coverage_file_sha256': file_sha(coverage_path),
        'historical_lifecycle_proof': {'path': str(lc_proof_path.resolve()), 'sha256': file_sha(lc_proof_path)},
        'protected': protected, 'heater_stats': heater_stats, 'core_stats': {k:v for k,v in core_stats.items() if k not in ('old_to_new_indices', 'retired_indices')},
        'index_remap': reference_proof, 'target_geometry': target_geometry,
        'lifecycle': {'mode': 'exact_inputs_and_packed_ID_result_reuse', 'systems': 20,
            'dependencies_sha256': digest(dependencies_before), 'before_after_dependencies_equal': True,
            'packed_ID_result_sha256': digest(packed_before), 'rd_rk_alignment_preserved': True,
            'baseline_sha256': BASELINE_SHA, 'new_full_cli_run': False, 'previous_exit0_reused': True,
            'counts': {s['id']: s['cnt'] for s in M['lifecycle']['systems']}},
        'coordination': coordination, 'component_counts': coverage['counts'],
        'no_post_no_graph_rebuild_no_full_build': True,
        'limits': ['Source-surface assemblies remain derived, with no concrete waist/body/material/bearing approval',
                   'Existing clashes only are reused; absence of new stair-surface collisions is not certified',
                   'Historical lifecycle exit0 reused by exact eligible geometry/roles/group/directeds; no physical port/operation approval']}
    stage = Path(stage_dir); stage.mkdir(parents=True, exist_ok=True)
    (stage/'before-model.json').write_bytes(original)
    (stage/'before-component-coverage.json').write_bytes(coverage_path.read_bytes())
    (stage/'heater-source-audit.json').write_bytes(encoded(heater_audit))
    (stage/'core-source-audit.json').write_bytes(encoded(core_audit))
    (stage/'after-component-coverage.json').write_bytes(encoded(coverage))
    (stage/'after-coordination-review.json').write_bytes(encoded(M['coordinationReview']))
    M.setdefault('meta', {})['source_batch'] = {'schema': proof['schema'], 'base_model_sha256': BASE_MODEL_SHA,
        'scope': 'heater82 capacity properties; core189 legacy bodies replaced by29 open source-surface assemblies',
        'historical_lifecycle_exit0_reused': True, 'lifecycle_dependency_sha256': proof['lifecycle']['dependencies_sha256'],
        'no_global_rebuild': True, 'physical_acceptance': False}
    staged = encoded(M)
    (stage/'after-model.json').write_bytes(staged)
    proof['after_model_sha256'] = hashlib.sha256(staged).hexdigest()
    proof['staged_files_sha256'] = {p.name: file_sha(p) for p in stage.glob('*.json') if p.name != 'proof.json'}
    (stage/'proof.json').write_bytes(encoded(proof))
    return proof


def commit_staged(stage_dir, ready_file, model_path=ROOT/'src/model.json'):
    """Commit the reviewed exact bytes; no source modules or graph are reapplied."""
    stage, ready_file, model_path = Path(stage_dir), Path(ready_file), Path(model_path)
    proof = json.loads((stage/'proof.json').read_text())
    ready = json.loads(ready_file.read_text())
    if not (ready.get('ready') is True and ready.get('base_model_sha256') == BASE_MODEL_SHA and
            ready.get('staged_model_sha256') == proof['after_model_sha256'] and
            ready.get('proof_sha256') == file_sha(stage/'proof.json')):
        raise ValueError('Root READY must bind this exact staging proof and output')
    if proof.get('pass') is not True or file_sha(model_path) != BASE_MODEL_SHA:
        raise ValueError('Staging failed or the current base file changed')
    for path, checksum in proof['input_files_sha256'].items():
        if file_sha(path) != checksum:
            raise ValueError('Source/input changed after staging: ' + path)
    for name, checksum in proof['staged_files_sha256'].items():
        if file_sha(stage/name) != checksum:
            raise ValueError('Staged evidence/bytes changed: ' + name)
    staged = (stage/'after-model.json').read_bytes()
    if hashlib.sha256(staged).hexdigest() != proof['after_model_sha256']:
        raise ValueError('Exact staged model bytes differ')
    M = json.loads(staged)
    import inventory as INV
    import clash_log as CL
    # These document writers do not run model generators or LC.
    INV.write_doc(M); CL.write_doc(M)
    for source, target in [('after-component-coverage.json', HERE/'data/component_coverage.json'),
                           ('after-coordination-review.json', HERE/'data/coordination_review.json'),
                           ('after-model.json', model_path)]:
        temporary = target.with_name(target.name + '.source-batch.tmp')
        temporary.write_bytes((stage/source).read_bytes())
        os.replace(temporary, target)
    receipt = {'schema': 'c4.targeted-source-batch-commit.v1', 'pass': True,
        'ready_file_sha256': file_sha(ready_file), 'staged_proof_sha256': file_sha(stage/'proof.json'),
        'model_file_sha256': file_sha(model_path), 'elements': len(M['els']),
        'same_staged_bytes_saved': True, 'source_reapplied': False, 'graph_recomputed': False,
        'baseline_unchanged': file_sha(HERE/'data/lifecycle_baseline.json') == BASELINE_SHA}
    (stage/'commit-receipt.json').write_bytes(encoded(receipt))
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', default=str(ROOT/'src/model.json'))
    parser.add_argument('--base-coverage', default=str(HERE/'data/component_coverage.json'))
    parser.add_argument('--lifecycle-proof')
    parser.add_argument('--stage-dir', required=True)
    parser.add_argument('--save-staged', action='store_true')
    parser.add_argument('--ready-file')
    args = parser.parse_args()
    if args.save_staged:
        if not args.ready_file:
            parser.error('--save-staged requires the exact root --ready-file')
        result = commit_staged(args.stage_dir, args.ready_file, args.model)
    else:
        if not args.lifecycle_proof:
            parser.error('Staging requires --lifecycle-proof; this command does not run global LC')
        result = prepare(args.model, args.base_coverage, args.lifecycle_proof, args.stage_dir)
    print(json.dumps({k: result[k] for k in ('schema', 'pass', 'before_elements', 'after_elements', 'after_model_sha256',
                                           'model_file_sha256', 'elements') if k in result}, ensure_ascii=False))


if __name__ == '__main__':
    main()
