"""Correct 281 horizontal ceiling board/tile thicknesses from A500; no file IO."""
import copy
import hashlib
import json
from pathlib import Path

DATA_PATH = Path(__file__).with_name('data') / 'ceiling_shape_match.json'
DATA_SHA256 = 'c017119dc267255a414a74b30e350d0728425c74e4341993158f6776f0061420'
TYPES = {}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def data():
    raw = DATA_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != DATA_SHA256:
        raise ValueError('Ceiling shape source ledger changed')
    return json.loads(raw)


def apply(M, els=None):
    """Keep XY rings and the current lower face; change only board upper faces.

    A p-prism encodes [kind, outer_ring, lower_Z, upper_Z, optional_holes].
    The vertical tray risers deliberately do not participate in this operation.
    """
    D = data()
    E = M['els'] if els is None else els
    by = {}
    for e in E:
        by.setdefault(e['id'], []).append(e)
    actual = {e['id'] for e in E if e['t'] in ('ceil_C1', 'ceil_C3')}
    if actual != set(D['records']):
        raise ValueError('Ceiling shape controlled population changed')
    plans = []
    # Every guard completes before any mutation, including metadata.
    for eid, r in D['records'].items():
        if len(by.get(eid, [])) != 1:
            raise ValueError('Ceiling shape identity missing/duplicate: ' + eid)
        e = by[eid][0]
        for ek, rk in [('c','category'),('t','type'),('l','level'),('m','material_code'),('mark','mark')]:
            if e.get(ek) != r[rk]:
                raise ValueError('Ceiling shape identity changed: ' + eid + '/' + ek)
        for key, value in r['retained_source_assignment'].items():
            if e.get('a', {}).get(key) != value:
                raise ValueError('Ceiling source zone assignment changed: ' + eid + '/' + key)
        g = e['g']
        if g[0] != 'p' or len(g) not in (4,5):
            raise ValueError('Ceiling geometry encoding changed: ' + eid)
        if digest(g) not in (r['before_geometry_sha256'], r['after_geometry_sha256']):
            raise ValueError('Ceiling exact geometry guard failed: ' + eid)
        if g[2] != r['lower_face_z_m']:
            raise ValueError('Ceiling lower face changed: ' + eid)
        after = copy.deepcopy(g)
        after[3] = round(g[2] + r['after_thickness_mm'] / 1000, 3)
        if digest(after) != r['after_geometry_sha256']:
            raise ValueError('Ceiling target geometry guard failed: ' + eid)
        plans.append((e, r, after))
    for r in D['excluded_vertical_risers']:
        matches = by.get(r['id'], [])
        if len(matches) != 1 or digest(matches[0]['g']) != r['geometry_sha256']:
            raise ValueError('Excluded vertical riser changed: ' + r['id'])
    changed = []
    for e, r, after in plans:
        if e['g'] != after:
            changed.append(e['id'])
        e['g'] = after
        e.setdefault('a', {}).update(
            ceiling_shape_match=True,
            ceiling_source_thickness_mm=r['after_thickness_mm'],
            ceiling_source_thickness_verified=True,
            ceiling_source_thickness_page='ARCH1:18 A500 / ARCH1-supplement:1 A500',
            ceiling_source_thickness_pdf_sha256=D['source_pdf']['sha256'],
            ceiling_shape_data_sha256=DATA_SHA256,
            ceiling_lower_face_retained=True,
            ceiling_xy_rings_retained=True,
            ceiling_location_shape_fully_verified=False,
            ceiling_match_scope='source_type_thickness_only',
            ceiling_location_shape_conflict='DP-CEILING-SHAPE-LOCATION-BOUNDARY',
        )
    result = {'schema':D['schema'], 'data_sha256':DATA_SHA256,
              'controlled_ids':list(D['records']), 'controlled_count':len(D['records']),
              'by_code':{c:sum(r['ceiling_code']==c for r in D['records'].values()) for c in D['source_rows']},
              'changed_ids':changed, 'changed':len(changed),
              'lower_faces_preserved':len(D['records']), 'xy_rings_preserved':len(D['records']),
              'excluded_vertical_risers':[r['id'] for r in D['excluded_vertical_risers']],
              'location_shape_fully_verified':0}
    M.setdefault('meta', {})['ceiling_shape_match'] = {
        k:copy.deepcopy(v) for k,v in result.items() if k not in ('changed_ids','changed')}
    return result


def issue_records(M):
    """Two corrected thickness findings and explicit location/shape evidence gaps."""
    D = data()
    by = {e['id']:e for e in M['els']}
    for eid, r in D['records'].items():
        e = by.get(eid)
        if not e or digest(e['g']) != r['after_geometry_sha256'] or not e.get('a',{}).get('ceiling_shape_match'):
            raise ValueError('Ceiling issues require applied thickness correction: ' + eid)
    rows = []
    for code, spec in D['source_rows'].items():
        ids = [eid for eid,r in D['records'].items() if r['ceiling_code']==code]
        rows.append({'id':'DP-CEILING-SHAPE-'+code+'-THICKNESS',
            'title':'تصحيح سُمك أسقف '+code+' من20مم إلى'+str(spec['thickness_mm'])+'مم',
            'status':'corrected', 'source':'ARCH1 ص18 / الملحق ص1، A500 جدول تشطيبات الأسقف',
            'drawing_ids':['A500'], 'elements':ids,
            'note':'سُمك اللوح/البلاطة مكتوب حرفيًا في صف النوع. حُفظت مضلعاتXY وثقوبها والوجه السفلي الحالي؛ توزيع النوع وحدود السقف ومناسيبه تُراجع في DP-CEILING-SHAPE-LOCATION-BOUNDARY.',
            'before':{'thickness_mm':20,'count':len(ids)},
            'after':{'thickness_mm':spec['thickness_mm'],'count':len(ids),'lower_face_preserved':True,
                     'xy_rings_preserved':True,'location_shape_fully_verified':False}})
    rows.append({'id':'DP-CEILING-SHAPE-LOCATION-BOUNDARY',
        'title':'مقابلة حدود الأسقف وتوزيع الأنواع والمناسيب لكل منطقة مع مخططها',
        'status':'source_gap', 'source':'ARCH2 ص29 A1401، ص34 A1600، ص35 A1601',
        'drawing_ids':D['remaining_conflicts']['drawing_ids'], 'elements':list(D['records']),
        'note':D['remaining_conflicts']['location_shape_ar'],
        'after':{'source_type_thickness_verified':True,'location_shape_fully_verified':False}})
    rows.append({'id':'DP-CEILING-SHAPE-RISER',
        'title':'مقابلة جسمي رجوع فرق منسوب السقف الرأسيين مع القطاع',
        'status':'source_gap', 'source':'ARCH2 ص34 A1600 / ص35 A1601',
        'drawing_ids':['A1600','A1601'], 'elements':[r['id'] for r in D['excluded_vertical_risers']],
        'note':D['remaining_conflicts']['riser_ar'],
        'after':{'unchanged':True,'location_shape_fully_verified':False}})
    return rows
