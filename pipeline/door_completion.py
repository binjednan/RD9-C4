"""Scoped A701 component detail/conflict review for 204 existing source leaves.

This module deliberately selects no manufacturing geometry. Two newly recorded
source contradictions prevent honest reconstruction of the affected profiles.
Call apply(M) after door_source_review_updates.append_to and before clash review.
It preserves all body geometry, identity, apartment bindings and acceptance flags.
"""
from pathlib import Path
import collections
import copy
import hashlib
import json
import fitz

HERE = Path(__file__).resolve().parent
DATA_PATH = HERE / 'data/door_completion.json'
BASE_PATH = HERE / 'data/door_source_templates.json'
DATA_SHA = 'c1de25af4ff44d00bd60008ba7e7009e7d01da95837c6434eb6006340559d0ec'
OWN_KEY = 'source_door_detail_review'
PREFIX = 'DP-DOOR-COMPLETION-'
FALSE_FLAGS = ['source_whole_assembly_verified', 'source_mount_verified',
               'source_hardware_verified', 'source_color_verified',
               'source_ports_verified', 'source_physical_hinge_pivot_verified',
               'source_whole_leaf_XY_verified']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def data():
    if sha(DATA_PATH) != DATA_SHA:
        raise ValueError('Door completion frozen review changed')
    result = json.loads(DATA_PATH.read_text())
    if sha(BASE_PATH) != result['base_data_sha256']:
        raise ValueError('Door completion parent source ledger changed')
    return result, json.loads(BASE_PATH.read_text())


def verify_source(review=None, base=None):
    """Verify unchanged source bytes, visual evidence pixels and A700 bindings.

    Raster fingerprints reproduce the visually reviewed evidence; they do not
    machine-validate the meaning of transcribed vector-outline numerals.
    """
    frozen, original = data()
    if review is not None and review != frozen:
        raise ValueError('Door completion review differs from frozen visual review')
    if base is not None and base != original:
        raise ValueError('Door completion parent ledger differs from frozen input')
    review, base = frozen, original
    errors = []
    sources = []
    for key, source in base['sources'].items():
        ok = sha(source['path']) == source['pdf_sha256']
        sources.append({'source': key, 'pass': ok})
        if not ok:
            errors.append('Source PDF fingerprint differs: ' + key)
    if errors:
        return {'pass': False, 'errors': errors, 'sources': sources}
    pdf = fitz.open(review['source_pdf']['path'])
    crops = []
    for name, record in review['crops'].items():
        pix = pdf[record['page'] - 1].get_pixmap(
            matrix=fitz.Matrix(*record['matrix']),
            clip=fitz.Rect(record['crop_pdf']), annots=record['annots'])
        ok = (hashlib.sha256(pix.samples).hexdigest() == record['render_samples_sha256']
              and [pix.width, pix.height, pix.n] == record['render_size'])
        crops.append({'detail': name, 'pass': ok})
        if not ok:
            errors.append('Original A701 crop changed: ' + name)
    traces = pdf[8].get_texttrace()
    schedule_checks = []
    for code, template in base['templates'].items():
        checks = [
            ''.join(chr(c[0]) for c in traces[int(index)]['chars']) == stored['text']
            for index, stored in template['schedule_text'].items()]
        schedule_checks.append({'code': code, 'pass': all(checks)})
        if not all(checks):
            errors.append('A700 type schedule text changed: ' + code)
    pdf.close()
    return {'pass': not errors, 'errors': errors, 'sources': sources,
            'crop_checks': crops, 'schedule_checks': schedule_checks,
            'scope': 'unchanged PDFs + visually inspected A701 crops + A700 typed text; no new 3D/source-registration acceptance'}


def _leaf_geometry(base, record):
    template = base['templates'][record['template']]
    width, depth = template['leaf_width_cm'], template['leaf_depth_cm']
    x, y = record['source_hinge_side_anchor_xy_cm']
    u = record['source_signed_open_vector_xy']
    n = [-u[1], u[0]]
    points = [[round(x + v * width * u[0] + q * depth / 2 * n[0], 4),
               round(y + v * width * u[1] + q * depth / 2 * n[1], 4)]
              for v, q in [(0, -1), (1, -1), (1, 1), (0, 1)]]
    z = base['level_datums'][record['level']]['ffl_m']
    return ['p', points, round(z, 6), round(z + template['leaf_height_cm'] / 100, 6), None]


def _annotation(record):
    return {'data_sha256': DATA_SHA, 'detail': record['detail'],
            'source': 'ARCH2:10 A701 / ARCH2:9 A700',
            'conflict_ids': record['conflict_ids'],
            'status': 'source_conflict', 'physical_components_added': 0,
            'frame_architrave_or_full_layers_accepted': False}


def _guard(model, review, base):
    grouped = collections.defaultdict(list)
    for element in model['els']:
        grouped[element['id']].append(element)
    if any(len(grouped[eid]) != 1 for eid in review['instances']):
        raise ValueError('Door completion requires 204 exact unique parent identities')
    if any((e.get('a') or {}).get(OWN_KEY) and e['id'] not in review['instances']
           for e in model['els']):
        raise ValueError('Door completion unowned annotated instance')
    states = set()
    for eid, record in base['instances'].items():
        e = grouped[eid][0]
        a = e.get('a') or {}
        old = base['original_bodies'][eid]
        if (e['g'] != _leaf_geometry(base, record)
                or e['c'] != 'A.door' or e['l'] != record['level']
                or e.get('mark') != record['code'] or e.get('t') != 'door_source_' + record['code']
                or a.get('source_door_instance') != eid
                or a.get('source_door_data_sha256') != review['base_data_sha256']
                or any(e.get(k) != old.get(k) for k in ['u', 'u2'])
                or any(a.get(k) is not False for k in FALSE_FLAGS)):
            raise ValueError('Door completion parent geometry/identity/scope changed: ' + eid)
        if OWN_KEY in a:
            states.add('applied')
            if a[OWN_KEY] != _annotation(review['instances'][eid]):
                raise ValueError('Door completion annotation changed: ' + eid)
        else:
            states.add('original')
    if len(states) != 1:
        raise ValueError('Door completion partial annotation inventory')
    return {eid: grouped[eid][0] for eid in review['instances']}


def _issues(review):
    result = []
    for conflict in review['conflicts']:
        ids = [eid for eid, r in review['instances'].items() if r['code'] in conflict['codes']]
        result.append({'id': conflict['id'], 'title': conflict['title'],
                       'status': 'source_conflict', 'source': 'ARCH2 ص10 A701 / ص9 A700',
                       'note': conflict['note'], 'level': None, 'xy_cm': None, 'z_m': None,
                       'elements': ids, 'before': None, 'after': copy.deepcopy(conflict['facts']),
                       'source_data_sha256': DATA_SHA,
                       'geometry_changed': False, 'physical_whole_assembly_accepted': False})
    return result


def apply(model, els=None):
    if els is not None and els is not model['els']:
        raise ValueError('Door completion must use the actual model array')
    review, base = data()
    proof = verify_source(review, base)
    if not proof['pass']:
        raise ValueError('Door completion source verification failed: ' + str(proof['errors']))
    by = _guard(model, review, base)
    # Perform all rejecting checks before touching the model.
    for eid, record in review['instances'].items():
        by[eid]['a'][OWN_KEY] = copy.deepcopy(_annotation(record))
    model['doorCompletion'] = {'data_sha256': DATA_SHA,
                               'summary': copy.deepcopy(review['summary']),
                               'detail_records': copy.deepcopy(review['detail_records']),
                               'conflicts': copy.deepcopy(review['conflicts']),
                               'scope': copy.deepcopy(review['scope']),
                               'external_report': 'pipeline/data/door_completion.json'}
    model['drawingIssues'] = [q for q in model.get('drawingIssues', [])
                              if not q.get('id', '').startswith(PREFIX)] + _issues(review)
    model.setdefault('meta', {})['door_completion'] = {
        **copy.deepcopy(review['summary']), 'data_sha256': DATA_SHA,
        'source_visual_review_reproduced': True, 'source_conflicts_resolved': False}
    return copy.deepcopy(model['meta']['door_completion'])


build = apply


def audit(model):
    review, base = data()
    errors = []
    proof = verify_source(review, base)
    errors.extend(proof['errors'])
    try:
        by = _guard(model, review, base)
        for eid, record in review['instances'].items():
            if by[eid]['a'].get(OWN_KEY) != _annotation(record):
                errors.append('Door completion annotation missing: ' + eid)
    except ValueError as exc:
        errors.append(str(exc))
    issues = [q for q in model.get('drawingIssues', []) if q.get('id', '').startswith(PREFIX)]
    if issues != _issues(review):
        errors.append('Door completion conflict evidence or affected identity set changed')
    result = model.get('doorCompletion', {})
    for key in ['summary', 'detail_records', 'conflicts', 'scope']:
        if result.get(key) != review[key]:
            errors.append('Door completion model ledger changed: ' + key)
    if result.get('data_sha256') != DATA_SHA:
        errors.append('Door completion model ledger fingerprint missing')
    expected_meta = {**review['summary'], 'data_sha256': DATA_SHA,
                     'source_visual_review_reproduced': True, 'source_conflicts_resolved': False}
    if model.get('meta', {}).get('door_completion') != expected_meta:
        errors.append('Door completion summary missing/changed')
    return {'summary': {'pass': not errors, 'findings': len(errors), **review['summary']},
            'errors': errors, 'source_proof': proof, 'source_data_sha256': DATA_SHA,
            'acceptance_scope': 'new typed conflict records only; original leaf geometry and all whole-assembly acceptance flags remain unchanged'}
