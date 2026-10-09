"""Apply the reviewed continuation once, with dependent evidence refreshed.

This is the supported continuation entry point for the supplied checkpoint.
The input and output are staged before publication; no source generator or
full network run is invoked. No physical/site acceptance is granted.
"""
import argparse
import collections
import copy
import datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import source_batch as SB
import stair_completion as SC
import equipment_completion as EC
import door_completion as DC
import check_equipment_completion as EG
import check_component_coverage as CC
import check_geometry_integrity as GI
import coordination_review as CR
import completion_coordination as CO
import lifecycle as LC
import inventory as INV

BASE_SHA = '9e636423e4105d002c014ede34becbbc307d676902b548da0181de235cf6af7f'
BATCH_ID = 'component-continuation-20261009'


def encoded(v):
    return json.dumps(v, ensure_ascii=False, separators=(',', ':')).encode()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def refresh_coverage(M, previous, stairs, equipment, door):
    R = copy.deepcopy(previous)
    rows = {r['id']: r for r in R['rows']}
    D = SC.data()
    old_stairs = {e['id'] for g in D['groups'] for e in g['before_records']}
    new_stairs = {e['id'] for g in D['groups'] for e in g['after_records']}
    by = {e['id']: e for e in M['els']}
    for eid in old_stairs - new_stairs:
        rows.pop(eid, None)
        R['details'].pop(eid, None)
    for eid in new_stairs | set(EC.data()['records']):
        e = by[eid]
        is_stair = eid in new_stairs
        note = ('أسطح نهاية مشتقة من المسقط والقطاع؛ جسم الخرسانة والمادة والارتكاز غير معتمدة'
                if is_stair else 'مرساة وأبعاد مسقط مفحوصة؛ Z المطلق والمادة والمنافذ غير معتمدة')
        z = 'finished_surface_datum_and_derived_risers' if is_stair else 'assumed_or_derived'
        refs = CC.references(M, e)
        rows[eid] = {'id': eid, 'status': 'derived' if is_stair else 'source_checked',
                     'xy_basis': note, 'z_basis': z, 'source': ' / '.join(refs), 'findings': [note]}
        R['details'][eid] = {'category': e['c'], 'type': e['t'], 'level': e['l'],
            'geometry_kind': e['g'][0], 'xy_cm': CC.xy(e['g']), 'z_m': CC.z_range(e['g']),
            'source_refs': refs, 'height_assumptions': [note],
            'evidence': {'source_audit': 'stair_completion' if is_stair else 'equipment_completion',
                         'source_data_sha256': SC.DATA_SHA if is_stair else EC.DATA_SHA256,
                         'current_geometry_sha256': SB.digest(e['g'])},
            'needs_original_xy_proof': is_stair, 'needs_height_proof': True,
            'whole_physical_body_source_accepted': False}
    # Door body evidence and classification remain unchanged; new detail conflicts
    # are attached without upgrading the native anchor to a whole-leaf check.
    for eid in DC.data()[0]['instances']:
        R['details'][eid].setdefault('evidence', {})['door_detail_conflicts'] = copy.deepcopy(
            by[eid]['a']['source_door_detail_review'])
    if set(rows) != set(by):
        raise ValueError('Component coverage and live identities differ')
    R['rows'] = [rows[e['id']] for e in M['els']]
    R['counts'] = dict(collections.Counter(r['status'] for r in R['rows']))
    families = collections.defaultdict(collections.Counter)
    for r in R['rows']:
        families[by[r['id']]['c'][0]][r['status']] += 1
    R['by_family'] = {k: dict(v) for k, v in families.items()}
    R['height_counts'] = dict(collections.Counter(r['z_basis'] for r in R['rows']))
    R['model_elements'] = len(M['els'])
    R['model_geometry_sha256'] = SB.cc_geometry_sha(M)
    R['missing_components'] = [r for r in R.get('missing_components', []) if r.get('id') not in old_stairs - new_stairs]
    R['continuation_source_audits'] = {'stairs': stairs, 'equipment': equipment, 'doors': door}
    R['geometry_preserved'] = True  # This coverage pass did not mutate geometry.
    M['componentReview'] = CC.compact(R)
    return R


def remap_source_issues(M, stair_stats):
    aliases = stair_stats['retired_to_new']
    D = SC.data()
    owned = {e['id'] for g in D['groups'] for e in g['before_records']}
    live = {e['id'] for g in D['groups'] for e in g['after_records']}
    updates = []
    for q in M.get('drawingIssues', []):
        ids = q.get('elements') or []
        if not set(ids) & owned:
            continue
        original = copy.deepcopy(q)
        if q.get('status') == 'confirmed_model_error' and set(ids) <= owned:
            q['status'] = 'corrected'
            q['title'] = 'صُحح تمثيل أسطح المصدر: ' + q['title'].replace('خطأ مؤكد في ', '')
            q['note'] = 'عولج هذا الخطأ في أسطح البدروم/الأرضي بدفعة الاستكمال. حدود الجسم والمادة والارتكاز باقية؛ راجع DP-STAIR-COMPLETION-B-G.'
            q['after'] = {'corrected_by': BATCH_ID, 'open_surfaces_only': True,
                          'physical_body_accepted': False}
        mapped = []
        for eid in ids:
            mapped.extend(aliases.get(eid, [eid]))
        q['elements'] = list(dict.fromkeys(mapped))
        q['historical_element_ids'] = ids
        q['current_identity_mapping_scope'] = 'procedural group review aliases only; never a physical connection'
        updates.append({'id': q['id'], 'before': original, 'after_status': q['status']})
    M.setdefault('drawingIssueArchive', []).extend(updates)
    refresh_scope_notes(M)
    SC.apply_issues(M)
    return updates


def refresh_scope_notes(M):
    # Keep old scope records historical after the bounded continuation.
    for q in M.get('drawingIssues', []):
        if q.get('id') == 'DP-CORE-STAIRS-SURFACE-BODY-SCOPE':
            q['note'] = ('أُصلحت في الدفعة السابقة أسطح تسع مجموعات من المصدر:190 نائمة و209 قوائم و10 بسطات داخل29 تجميعة. '
                         'الأجسام أسطح مفتوحة بلا سماكة مخترعة؛ لا يعتمد بطن الخرسانة أو التسليح أو الارتكاز أو مادة الجسم. '
                         'استُكملت لاحقًا أسطح درج01 في البدروم والأرضي بعشر تجميعات ضمن DP-STAIR-COMPLETION-BODY؛ '
                         'تبقى مجموعتا الدور الثاني معلقتين لتعارض +10.10.')
        elif q.get('id') == 'DP-CORE-STAIRS-N-RISE':
            q['note'] = ('الخطأ المتبقي محصور في STAIR1-2 وSTAIR2-2: التقسيم الإجرائي الحالي20 قائمة للدور3.50م '
                         'مقابل22 قائمة في المصدر. يعوق اعتماد إعادة البناء تعارض منسوب +10.10؛ لا يعتمد +11.00 بالحساب. '
                         'يبقى42 جسمًا إجرائيًا في هاتين المجموعتين. مجموعات الطوابق الأخرى المصححة مستقلة في سجلاتها؛ '
                         'آخر استكمال هو أسطح درج01 في البدروم والأرضي، ولا يعني ذلك اعتماد جسم الخرسانة أو الارتكاز.')


def refresh_lifecycle(M, base):
    old, new = SB.lc_dependencies(base), SB.lc_dependencies(M)
    changed = [sid for sid in old if old[sid] != new[sid]]
    reused = [sid for sid in old if old[sid] == new[sid]]
    world = LC.World(M['els'])
    packed = {s['id']: s for s in M['lifecycle']['systems']}
    for sd in LC.SYSTEMS:
        if sd['id'] not in changed:
            continue
        R = LC.analyse_system(M, sd, world)
        R['isl'], R['near'], R['far'] = LC.diagnose(M, sd, R) if R['bad'] else ([], [], [])
        R['islands'], R['lone'] = LC.islands(M, R)
        R['tests'] = LC.tests_of(M, sd, R)
        packed[sd['id']] = LC.pack(M, [(sd, R)])['systems'][0]
    M['lifecycle']['systems'] = [packed[s['id']] for s in M['lifecycle']['systems']]
    old_packed = {s['id']: s for s in SB.packed_lifecycle_identity(base)['systems']}
    new_packed = {s['id']: s for s in SB.packed_lifecycle_identity(M)['systems']}
    for sid in reused:
        if old_packed[sid] != new_packed[sid]:
            raise ValueError('Unchanged system packed identity/result changed: ' + sid)
    baseline = json.loads((ROOT / 'pipeline/data/lifecycle_baseline.json').read_text())
    regressions = [t for s in M['lifecycle']['systems'] for t in s['tests']
                   if t['id'] in baseline and t['ok'] < baseline[t['id']]]
    if regressions:
        raise ValueError('Network baseline regressed: ' + str(regressions))
    proof = {'recomputed_systems': changed, 'reused_by_exact_dependencies': reused,
             'dependencies_before_sha256': SB.digest(old), 'dependencies_after_sha256': SB.digest(new),
             'reused_packed_ID_results_equal': True, 'regressions': [],
             'baseline_sha256': sha(ROOT / 'pipeline/data/lifecycle_baseline.json'),
             'all_network_completeness_tests_pass': all(t['p'] for s in M['lifecycle']['systems'] for t in s['tests']),
             'physical_ports_or_operation_verified': False}
    M['lifecycle']['continuation'] = copy.deepcopy(proof)
    return proof


def refresh_coordination(M, base):
    before_by = {e['id']: e for e in base['els']}
    cr = copy.deepcopy(base['coordinationReview'])
    for c in M['clashes']:
        for index_key, id_key in (('a', 'ea'), ('b', 'eb')):
            e = M['els'][c[index_key]]
            if e['id'] != c[id_key] or e['g'] != before_by[e['id']]['g']:
                raise ValueError('Cannot reuse a changed existing clash witness')
    cr['source_conflicts'] = [CR._source_conflict(q) for q in M['drawingIssues'] if q['status'] == 'source_conflict']
    cr['zconflicts'] = [q for q in cr['source_conflicts'] if q.get('zconflict')]
    cr['coverage']['source_conflicts'] = len(cr['source_conflicts'])
    cr['coverage']['source_zconflicts'] = len(cr['zconflicts'])
    cr['model_geometry_sha256'] = CR._hash([[e['id'], e['g']] for e in M['els']])
    cr['incremental_reuse'] = {'existing_pairs': len(M['clashes']),
        'full_pair_geometries_preserved': True, 'open_stair_surface_clearance_checked': False,
        'limit_ar': 'شواهد الأزواج السابقة ثابتة؛ أسطح الدرج الجديدة لا تملك جسمًا مغلقًا لفحص الحجم.'}
    M['coordinationReview'] = cr


def prepare(model_path, coverage_path, stage):
    if sha(model_path) != BASE_SHA:
        raise ValueError('Continuation requires the supplied checkpoint model SHA')
    base = json.loads(Path(model_path).read_text())
    previous = json.loads(Path(coverage_path).read_text())
    if previous['model_geometry_sha256'] != SB.cc_geometry_sha(base):
        raise ValueError('Input coverage is stale')
    M = copy.deepcopy(base)
    stair_stats = SC.apply(M)
    remap = SB.remap_index_refs(M, stair_stats['old_to_new_indices'], stair_stats['retired_indices'])
    equipment_stats = EC.apply(M)
    door_stats = DC.apply(M)
    old_issues = remap_source_issues(M, stair_stats)
    equipment_issues = EC.issue_records(M)
    issue_ids = {q['id'] for q in equipment_issues}
    M['drawingIssues'] = [q for q in M['drawingIssues'] if q['id'] not in issue_ids] + equipment_issues
    stairs, equipment, doors = SC.audit(M), EG.audit(M), DC.audit(M)
    if not all(r.get('pass', r.get('summary', {}).get('pass', False)) for r in (stairs, equipment, doors)):
        raise ValueError('Native source audit failed')
    stair_ids = {e['id'] for g in SC.data()['groups'] for e in g['after_records']}
    for e in M['els']:
        if e['id'] in stair_ids:
            e['q'] = 'vva'
    geometry = GI.audit(M)
    if not geometry['pass']:
        raise ValueError('Geometry integrity failed')
    coverage = refresh_coverage(M, previous, stairs, equipment, doors)
    lifecycle = refresh_lifecycle(M, base)
    refresh_coordination(M, base)
    # Broad phase targets the corrected door proxies from the preceding batch,
    # plus this batch's two equipment proxies. Open stair meshes are excluded.
    targets = set(DC.data()[0]['instances']) | set(EC.data()['records'])
    coordination = CO.audit(M, targets)
    M['completionCoordination'] = {k: v for k, v in coordination.items()
                                  if k not in ('unsupported_elements', 'excluded_stage_elements')}
    M['completionCoordination']['external_report'] = 'pipeline/data/completion_coordination.json'
    SB.aggregate_reliability(M)
    summary = ('استكمال درج01 بالبدروم والأرضي:42 جسمًا إجرائيًا استبدلت بـ10 تجميعات أسطح؛ '
               'تصحيح غلافي لوحة الجهد العالي والمولد، وتوثيق تعارضي تفاصيل الأبواب. '
               'أجسام الخرسانة والتثبيت والمنافذ والمواد غير المعتمدة تبقى معلقة.')
    M['meta'].setdefault('applied_source_batches', []).append({'id': BATCH_ID, 'saved': True,
        'summary_ar': summary, 'new_XY_checked': 2, 'whole_assembly_accepted': 0})
    M['meta']['component_continuation'] = {'id': BATCH_ID, 'base_model_sha256': BASE_SHA,
        'stairs': SC.data()['summary'], 'equipment': equipment_stats, 'doors': door_stats,
        'source_audits_pass': True, 'physical_acceptance': False}
    dependency_result = {'changed_systems': lifecycle['recomputed_systems'],
        'reason_ar': ('الهويتان خارج مدخلاتLC الحالية؛ ثبت تطابق مدخلات ونتائج20 نظامًا حسب الهوية. لا تشغيل قدرة جديد.'
                      if not lifecycle['recomputed_systems'] else 'أعيد تحليل الأنظمة التي تغيرت مدخلاتها فقط.')}
    M['meta']['equipment_completion']['actual_lifecycle_dependency_result'] = copy.deepcopy(dependency_result)
    M['meta']['component_continuation']['actual_lifecycle_dependency_result'] = dependency_result
    INV.build(M)
    old_by, new_by = SB.by_id(base), SB.by_id(M)
    owned = {e['id'] for g in SC.data()['groups'] for e in g['before_records']} | targets
    for eid in set(old_by) - owned:
        if new_by[eid] != old_by[eid]:
            raise ValueError('Unrelated full element changed: ' + eid)
    for eid in DC.data()[0]['instances']:
        if new_by[eid]['g'] != old_by[eid]['g']:
            raise ValueError('Door geometry unexpectedly changed')
    stage = Path(stage)
    stage.mkdir(parents=True, exist_ok=True)
    files = {'before-model.json': base, 'after-model.json': M, 'before-component-coverage.json': previous,
             'after-component-coverage.json': coverage, 'after-coordination-review.json': M['coordinationReview'],
             'completion-coordination.json': coordination, 'stairs-source-audit.json': stairs,
             'equipment-source-audit.json': equipment, 'doors-source-audit.json': doors,
             'geometry-integrity.json': geometry, 'index-remap.json': remap}
    for name, value in files.items():
        (stage / name).write_bytes(encoded(value))
    proof = {'schema': 'c4.component-continuation.v1', 'pass': True,
        'base_model_sha256': BASE_SHA, 'after_model_sha256': sha(stage / 'after-model.json'),
        'before_elements': len(base['els']), 'after_elements': len(M['els']),
        'unrelated_full_elements_preserved': len(set(old_by) - owned),
        'stairs': SC.data()['summary'], 'equipment': equipment_stats, 'doors': door_stats,
        'source_issues_refreshed': len(old_issues), 'component_counts': coverage['counts'],
        'lifecycle': lifecycle, 'geometry_integrity_pass': True,
        'scoped_coordination': {k: coordination[k] for k in ('target_count', 'narrow_phase_pairs', 'positive_volume_pairs', 'already_in_legacy_clashes', 'new_to_legacy_list', 'unsupported_geometry_counts')},
        'new_full_post_or_network_run': False, 'physical_acceptance': False,
        'staged_sha256': {name: sha(stage / name) for name in files}}
    (stage / 'proof.json').write_bytes(encoded(proof))
    return proof


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=Path, default=ROOT / 'src/model.json')
    parser.add_argument('--coverage', type=Path, default=ROOT / 'pipeline/data/component_coverage.json')
    parser.add_argument('--stage', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.model, args.coverage, args.stage), ensure_ascii=False, indent=2))
