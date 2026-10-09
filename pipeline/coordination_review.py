# -*- coding: utf-8 -*-
"""Read-only source/elevation review of every existing clash.

This module preserves model geometry, the legacy detection tolerance, and the
clash list. An engine-geometry witness proves positive model volume only. A
source-confirmed physical clash additionally needs independently verified XY
and Z bounds for both elements and an explicit semantic review.
"""
import collections
import copy
import hashlib
import json
import math
import os
import re

from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely.validation import explain_validity

from pergola_conflicts import _footprint, _segment, _slice, _integrate

EPS = 1e-9
ORIGINAL_TOLERANCE = {
    'min_xy_area_cm2': 4.0, 'min_z_overlap_m': .02,
    'mep_pair_min_volume_m3': {'duct_pipe': .005, 'equip_pipe': .001, 'equip_duct': .001},
    'legacy_small_depth_cm': 3.0, 'legacy_small_volume_m3': .003,
    'proposed_band_margin_m': .05,
}
LANE_AR = {
    'confirmed': 'تعارض مثبت من المصدر',
    'confirmed_plan': 'عبور مثبت بالمسقط؛ منسوب وفتحة غير مثبتين',
    'candidate_height': 'مرشح اختلاف منسوب أو شكل',
    'model_collision': 'تداخل في المجسم يحتاج تحقق المصدر',
    'source_conflict': 'تعارض بين المصادر',
}
PLAN_CASES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'coordination_source_cases.json')
CASE_NOTES = {
    'CL-6E26A265': 'حجم ماء خزان يتقاطع مع عمود: مثبت هندسيًا في المجسم، لكنه مجال حساب ماء وليس جسم خدمة صلبًا. يحتاج تدقيق صافي حجم الماء وحدود A2500/STR، ولا يثبت وحده خطأً إنشائيًا أو يستدعي نقل العمود.',
    'CL-C5AE2F07': 'جدار خزان خرساني وعمود خرساني: قد يكون التداخل اتصالًا أو وصفين للجسم نفسه. يلزم مطابقة المصدر والتفصيل الإنشائي قبل اعتباره تصادمًا غير مقصود.',
    'CL-497DA961': 'جدار خزان يلتقي الجدار الخارجي الخرساني. لا يحسم التصنيف العام P.tank إن كان جزءًا مشتركًا مقصودًا أو تكرارًا في المجسم.',
    'CL-110034AB': 'صاعد دخان يعبر بلاطة G. المسقط ومخطط الصاعد يثبتان وظيفة العبور؛ تفاصيل فتحة البلاطة والـsleeve وحدود الامتداد الرأسي لم يتحقق منها هذا السجل. لا يعالج كخدمة أفقية قابلة للخفض.',
    'CL-43FE8A67': 'صاعد بطول رأسي 5.02م وصندوق FHC: تحويل طول الصاعد إلى سماكة تكديس 5.02م خطأ تصنيفي. void القديم2.75→2.05 سالب، ولا يجوز أن يثبت عدم إمكان التكديس. موضع صاعد G نفسه مشتق من مخطط الصاعد بلا فرع G مرسوم.',
    'CL-56A895A3': 'صاعد هواء وصاعد رشاشات متوازيان رأسيًا: سماكة3.5م هي طول قطعة الصاعد، لا مقاس قطاعه. اقتراح وضع أحدهما فوق الآخر في فراغ7.75م غير مناسب لمسار رأسي بين طابقين.',
    'CL-4BB398A6': 'مجرى الدخان107.5سم يقطع B4 أسفله−.80م. منسوب المجرى مفترض، واتجاه العرض/الارتفاع ذو شرط مصدر. حد خلوص2.40م عند غياب سقف مستعار افتراض، فلا تثبت عدم ملاءمة التنفيذ بمجرد الفراغ المحسوب.',
    'CL-802558FC': 'أنبوب رشاشاتØ100مم فوق البدروم يقطع B5. Z−.72م افتراض تمديد، والخفض إلى مركز≈−.90م اقتراح موضعي لا حل مسار مكتمل أو تفصيل حريق معتمد.',
    'CL-398B2752': 'مجرى تغذية15سم وأنبوب رشاشات8سم بمنسوبين مفترضين. مقاس المجرى أيضًا افتراضي لغياب وسم قريب؛ وجود فراغ محلي لا يثبت حل مسار أو اتصال أو ميل كامل.',
    'CL-10CCA246': 'شريط بعرض1سم من حجم ماء الخزان يشغل نحو95لترًا من التداخل النموذجي. تصنيف m بسبب العمق لا يثبت فرق رسم مقبولًا ولا يجيز عبارة لا إجراء؛ يلزم صافي حجم وحسم المصدر.',
}


def _hash(g):
    return hashlib.sha256(json.dumps(g, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _refs(M, e):
    a, t = e.get('a') or {}, M.get('types', {}).get(e.get('t'), {})
    refs = [M['sp'][i] for i in e.get('s', []) if isinstance(i, int) and 0 <= i < len(M.get('sp', []))]
    refs += t.get('sr', [])
    refs += [str(a[k]) for k in ('source_reference', 'source_z_reference', 'plan_source') if a.get(k)]
    return list(dict.fromkeys(refs))


def _basis(M, e):
    a, t = e.get('a') or {}, M.get('types', {}).get(e.get('t'), {})
    notes = [str(v) for k, v in a.items() if k in ('assumed', 'assumed_h', 'size_note', 'dim_note', 'riser_note', 'drawing_scope', 'part', 'note')]
    notes += [str(v) for v in t.get('asm', [])]
    notes += _refs(M, e)
    assumed = [s for s in notes if re.search(r'افتراض|افتراضي|تقدير|assum', s, re.I)]
    height = [s for s in assumed if re.search(r'منسوب|مناسيب|ارتفاع|قاع|قمة|القطاع بين|نهايتا|رأسي|FFL|\bz\b|height|elev', s, re.I)]
    # A numeric assumed_h is an explicit height assumption even without prose.
    if a.get('assumed_h') is not None:
        height.append('a.assumed_h=%s م' % a['assumed_h'])
    shape = [s for s in assumed if re.search(r'مقاس|أبعاد|البعد|قطر|سماكة|سماك|سمك|غلاف|قطاع|shape|size', s, re.I)]
    drawn_z_notes = {k: a[k] for k in ('drawn_ffl_m', 'ffl_m', 'height_cm', 'height_above_ffl_cm', 'water_level_m') if k in a}
    return {
        'id': e['id'], 'source_kind': a.get('source_kind'), 'refs': _refs(M, e),
        'xy_basis': 'source_metadata_present' if a.get('source_pdf_points') or a.get('source_drawing_indices') else 'source_reference_without_independent_bounds_proof',
        'height_basis': 'explicit_assumption' if height else 'not_independently_verified',
        'height_assumptions': list(dict.fromkeys(height)),
        'shape_assumptions': list(dict.fromkeys(shape)), 'drawn_z_notes': drawn_z_notes,
        'vertical_route': bool(a.get('shaft')) or str(e.get('t', '')).startswith(('riser_', 'storm_stack')),
        'limit_ar': 'مرجع أو رقم في بطاقة العنصر لا يساوي تحققًا مستقلًا لحدود XY وZ؛ يلزم سجل إثبات مقيّد ببصمة الهندسة.',
    }


def _pieces(e):
    g = e['g']
    if g[0] in ('t', 'd'):
        return [dict(p, method=p['method']) for i, (a, b) in enumerate(zip(g[1], g[1][1:]))
                for p in [_segment(g, a, b, i)] if p is not None]
    p, z = _footprint(g)
    if p is None or p.is_empty or not p.is_valid:
        return []
    return [{'polygon': p, 'z': z, 'events': list(z), 'segment': None,
             'method': 'engine_%s_vertical_prism' % g[0]}]


def _geometry(A, B, measure_volume=False):
    aa, bb = _pieces(A), _pieces(B)
    active = [(a, b) for a in aa for b in bb if min(a['z'][1], b['z'][1]) > max(a['z'][0], b['z'][0])
              and a['polygon'].intersects(b['polygon'])]
    out = {'state': 'unproved', 'positive_volume_proved': False,
           'methods': sorted(set(p['method'] for p in aa+bb)),
           'tolerance_original': copy.deepcopy(ORIGINAL_TOLERANCE),
           'geometry_sha256': {'a': _hash(A['g']), 'b': _hash(B['g'])}}
    unsupported = []
    for e, pieces in ((A, aa), (B, bb)):
        if pieces:
            continue
        p, z = _footprint(e['g']) if e['g'][0] not in ('t', 'd') else (None, None)
        reason = ('invalid polygon: '+explain_validity(p) if p is not None and not p.is_valid else
                  'empty or unsupported engine body')
        unsupported.append({'id': e['id'], 'geometry_code': e['g'][0], 'reason': reason})
    if unsupported:
        out['unsupported_geometry_elements'] = unsupported
    if not active:
        out['reason_ar'] = 'لم يثبت مقطع حجم موجب من أجسام العرض الفعلية؛ يحتفظ بسجل المرشح القديم للمراجعة.'
        return out
    lo = min(max(a['z'][0], b['z'][0]) for a, b in active)
    hi = max(min(a['z'][1], b['z'][1]) for a, b in active)
    events = sorted(set([lo, hi]+[z for a, b in active for p in (a, b) for z in p['events'] if lo < z < hi]))
    cache = {}
    def section(z):
        if z not in cache:
            xa = [_slice(a, z) for a in aa if a['z'][0]-EPS <= z <= a['z'][1]+EPS]
            xb = [_slice(b, z) for b in bb if b['z'][0]-EPS <= z <= b['z'][1]+EPS]
            xa, xb = [p for p in xa if not p.is_empty], [p for p in xb if not p.is_empty]
            cache[z] = unary_union(xa).intersection(unary_union(xb)) if xa and xb else Polygon()
        return cache[z]
    witnesses = []
    for a, b in zip(events, events[1:]):
        for fraction in (.125, .375, .5, .625, .875):
            z = a+(b-a)*fraction
            p = section(z)
            if p.area > EPS:
                witnesses.append((p.area, z, p, b-a))
    out['z_overlap_m'] = [lo, hi]
    if not witnesses:
        out['reason_ar'] = 'تداخل إسقاط ونطاقZ بلا شاهد داخلي موجب في المقاطع المفحوصة؛ لا يرقّى إلى مثبت.'
        return out
    area, z, p, interval = max(witnesses, key=lambda w: w[0])
    q = p.representative_point()
    out.update(state='positive_model_volume', positive_volume_proved=True,
               witness_xy_cm=[q.x, q.y], witness_z_m=z, area_cm2=area,
               witness_interval_m=interval, xy_overlap_bounds_cm=list(p.bounds),
               passes_legacy_area_at_witness=area >= ORIGINAL_TOLERANCE['min_xy_area_cm2'],
               reason_ar='شاهد مقطع داخلي موجب من هندسة العرض مع حفظ الفتحات. يثبت تداخل المجسم عندZ المذكور،ولا يثبت مصدر المنسوب أو التنفيذ.')
    if measure_volume:
        value, error = 0., 0.
        for a, b in zip(events, events[1:]):
            for i in range(4):
                v, err = _integrate(lambda z: section(z).area, a+(b-a)*i/4, a+(b-a)*(i+1)/4)
                value += v/10000; error += err/10000
        out.update(unioned_volume_m3=value, volume_numeric_error_estimate_m3=error,
                   volume_method='unioned horizontal sections of actual engine bodies; diagnostic numeric integration')
    return out


def _proof(e, proofs):
    p = proofs.get(e['id']) or {}
    if not isinstance(p, dict):
        return False, {'validation_ar': 'سجل إثبات المصدر غير صالح؛ لا ترقية.'}
    pieces = _pieces(e)
    source_z = p.get('z_bounds_m') or []
    if not isinstance(source_z, (list, tuple)):
        source_z = []
    actual_z = [min(q['z'][0] for q in pieces), max(q['z'][1] for q in pieces)] if pieces else []
    z_match = (len(source_z) == 2 and len(actual_z) == 2 and
               all(isinstance(a, (int, float)) and abs(a-b) <= 1e-8 for a, b in zip(source_z, actual_z)))
    ok = (p.get('xy_verified') is True and p.get('z_verified') is True
          and p.get('source_reference') and p.get('geometry_sha256') == _hash(e['g'])
          and z_match and p.get('semantic_distinct_physical_body') is True)
    return bool(ok), copy.deepcopy(p)


def _plan_cases():
    if not os.path.exists(PLAN_CASES_PATH):
        return []
    with open(PLAN_CASES_PATH, encoding='utf-8') as handle:
        return json.load(handle).get('plan_proofs', [])


def _plan_proof(A, B, cases):
    """A witnessed plan crossing is weaker than source-confirmed 3-D volume.

    This requires an independently reviewed physical route and a column which
    continues across that story. Geometry fingerprints prevent stale evidence
    from promoting a moved element. No numeric service Z is inferred.
    """
    pair = {A['id'], B['id']}
    for p in cases:
        if pair != {p.get('service_id'), p.get('obstruction_id')}:
            continue
        e = {q['id']: q for q in (A, B)}
        geometry_ok = (p.get('geometry_sha256', {}).get('service') == _hash(e[p['service_id']]['g']) and
                       p.get('geometry_sha256', {}).get('obstruction') == _hash(e[p['obstruction_id']]['g']))
        ok = bool(geometry_ok and p.get('raw_plan_crossing_verified') is True and
                  p.get('whole_story_continuity_verified') is True and
                  p.get('semantic_distinct_physical_body') is True and
                  p.get('source_reference') and p.get('centreline_crossing_length_cm', 0) > EPS)
        summary = {k: copy.deepcopy(p[k]) for k in (
            'id', 'source_reference', 'service_id', 'obstruction_id', 'source_physical_route_group',
            'source_kind', 'raw_faces_separation_cm', 'source_column_bounds_cm',
            'centreline_crossing_xy_cm', 'centreline_crossing_length_cm',
            'raw_plan_crossing_verified', 'whole_story_continuity_verified',
            'service_level', 'z_verified', 'penetration_detail_verified',
            'physical_route_count', 'vertical_continuity_basis_ar', 'qualification_ar') if k in p}
        summary.update(geometry_fingerprint_matches=geometry_ok,
                       raw_case_file='pipeline/data/coordination_source_cases.json')
        return ok, summary
    return False, None


def _source_conflict(q):
    """Separate explicit Z disagreement from XY, attributes and copied titles.

    A z_m coordinate attached to an issue is a locator, not evidence of a level
    disagreement. Only reviewed source pairs below supply absolute Z values.
    """
    q = copy.deepcopy(q)
    key = q.get('id', '')
    z = {
        'DP-IR-FFL': {'sources': {'ARCH A101/A2500': -3.50, 'MECH IR-100': -3.30},
                      'difference_m': .20, 'subject_ar': 'أرضية غرفة مضخات الري'},
        'DP-SUMP-FFL': {'sources': {'ARCH1 A101': -3.50, 'MECH DR-100': -3.30},
                        'difference_m': .20, 'subject_ar': 'أرضية غرفة مضخات حفرة التجميع'},
        'DP-CAT-LEVEL': {'sources': {'A106 FFL': 26.85, 'A1800 FFL': 27.25},
                        'difference_m': .40, 'subject_ar': 'منصة نهاية سلم السطح؛ A106 يصف27.25 بوصفT.OP'},
        'ST-SHORING-DREDGE': {'sources': {'S-8A Dredge line': -5.30, 'S-8A same-point road-level label': -5.20},
                             'difference_m': .10, 'subject_ar': 'منسوب الحفر في قطاع sheetpile المؤقت'},
    }
    xy = (key.startswith('DP-LTG-') or key.startswith('DP-PG-EQUIP-') or
          key in ('DP-PG-TANK-SOURCE', 'DP-IR-RISER', 'DP-WS-FILL') or
          key.startswith('DP-CHW-') and key != 'DP-CHW-SCH')
    attributes = {
        'DP-WS-DT': 'capacity_and_unit', 'DP-CHW-SCH': 'schedule_capacity_and_dimensions',
        'DP-STR-FUT': 'future_load_scope', 'DP-STR-COVER': 'reinforcement_cover',
        'DP-SIGN-R': 'copied_floor_content', 'DP-TE-TITLE': 'copied_title',
        'AR-LADDER-MATERIAL': 'material', 'AR-CEIL-THICK': 'thickness',
        'AR-RAMP-SLOPE': 'vertical_profile_gradient',
        'GC-SHAFT-DEPTH': 'shaft_depth_distribution',
        'GC-PLAN-DETAIL-ROOM': 'linked_room_distribution',
        'GC-FUSIBLE-TEMP': 'fusible_temperature_literal',
        'GC-ACOUSTIC-COAT': 'acoustic_coating_thickness_scope',
        'DP-BOUNDARY-CB1-REBAR': 'reinforcement_diameter_literal',
    }
    kind = 'absolute_z' if key in z else 'plan_xy' if xy else attributes.get(key, 'unreviewed_source_difference')
    q.update(source_conflict_kind=kind, xyconflict=bool(xy), zconflict=key in z,
             conflict_axis='Z' if key in z else 'XY' if xy else 'attribute',
             classification={'lane': 'source_conflict', 'label_ar': LANE_AR['source_conflict'],
                             'hardconfirmed': False, 'reason_ar': 'اختلاف موثق بين قيم أو مواضع المصدر؛ لا يثبت وحده اصطدامًا ماديًا.'})
    if key in z:
        q['z_source_comparison'] = copy.deepcopy(z[key])
    q['source_classification_limit_ar'] = 'الإحداثي z_m في السجل قد يحدد موضع المراجعة فقط؛ علامة zconflict تستلزم قيمتين متعارضتين صريحتين من المصادر.'
    return q


def classify(M, c, proofs=None, geometry=None, plan_cases=None):
    """Return facts for one existing clash; never changes M or c."""
    A, B = M['els'][c['a']], M['els'][c['b']]
    bases = [_basis(M, e) for e in (A, B)]
    geometry = geometry or _geometry(A, B, c.get('id') in CASE_NOTES)
    proofs = proofs or M.get('meta', {}).get('coordination_source_proofs', {})
    verified = [_proof(e, proofs) for e in (A, B)]
    water_domain = A.get('t') == 'tank_water' or B.get('t') == 'tank_water'
    shared_concrete = (A.get('t') == 'tank_wall' and B['c'].startswith('S.')) or (B.get('t') == 'tank_wall' and A['c'].startswith('S.'))
    hard = bool(geometry['positive_volume_proved'] and all(v[0] for v in verified)
                and not water_domain and not shared_concrete)
    plan_ok, plan_proof = _plan_proof(A, B, _plan_cases() if plan_cases is None else plan_cases)
    plan_ok = bool(plan_ok and geometry['positive_volume_proved'] and not water_domain and not shared_concrete)
    assumed = any(p['height_assumptions'] or p['shape_assumptions'] for p in bases)
    lane = ('confirmed' if hard else 'confirmed_plan' if plan_ok else
            'candidate_height' if geometry['positive_volume_proved'] and assumed and not water_domain and not shared_concrete else 'model_collision')
    limitations = []
    if water_domain:
        limitations.append('أحد الحجمين مجال ماء لحساب السعة،لا جسم خدمة صلب؛ يُراجع صافي الحجم قبل وصفه كتصادم مادي.')
    if shared_concrete:
        limitations.append('جدار الخزان والعنصر الإنشائي قد يمثلان اتصالًا مقصودًا أو وصفين لجسم مشترك؛ يلزم تدقيق دلالي ومصدر مستقل.')
    if any(p['vertical_route'] for p in bases):
        limitations.append('مسار رأسي: طوله بين الطوابق ليس سماكة تكديس داخل فراغ السقف؛ لا يفترض حله بخفض المنسوب.')
    v = c.get('void')
    if v and v[1] <= v[0]:
        limitations.append('نطاق الفراغ القديم غير موجب؛ لا يستعمل لإثبات عدم إمكان المرور أو اقتراح تكديس.')
    if v and not v[2]:
        limitations.append('حد الفراغ السفلي القديمFFL+2.40 افتراض عند غياب سقف مستعار؛ ليس خلوصًا مرسومًا معتمدًا.')
    if c.get('tier') == 'm':
        limitations.append('m عتبة حجم/عمق أولوية فقط؛ لا تثبت سماحة رسم مقبولة أو تجيز إغلاق الحالة دون تحقق.')
    if not hard:
        limitations.append('لا توجد قرينة مستقلة كاملة مرتبطة ببصمة كل جسم لحدودهXY وZ ودلالته؛confirmed المصدر غير مثبت.')
    if plan_ok:
        limitations.append('المسقط يثبت عبور مسار الخدمة داخل عمود قصة الدور؛ منسوب الخدمة الرقمي وتفصيل فتحة أو sleeve غير مثبتين. لا يعادل confirmed ثلاثي الأبعاد أو تحقق موقع.')
    reason = ('لم يثبت حجم موجب من هندسة العرض الفعلية؛ يحفظ المرشح القديم بلا ترقية.' if not geometry['positive_volume_proved'] else
              'الهندسة والمواقع وحدودZ والدلالة مثبتة من سجلي مصدر مستقلين.' if hard else
              'المسار وعمود قصة الدور مثبتان في المسقط؛ يبقى منسوب الخدمة وتفصيل اختراق العمود غير مثبتين.' if plan_ok else
              'هندسة المجسم تقطع الجسم الآخر؛ المنسوب أو الشكل مفترض ويحتاج مصدرًا.' if lane == 'candidate_height' else
              'تداخل نموذج يحتاج تحقق حدود المصدر أو دلالة الأجسام،ولا يثبت تصادمًا منفذًا.')
    return {'id': c.get('id'), 'legacy_tier': c.get('tier'), 'ea': A['id'], 'eb': B['id'],
            'kind': c['k'], 'level': c['l'], 'model_point_cm_m': [c['pt'][0]*100, -c['pt'][2]*100, c['pt'][1]],
            'legacy_reported_volume_m3': c.get('v'), 'geometry': geometry,
            'source': {'elements': bases, 'proofs': [p for ok, p in verified], 'plan_proof': plan_proof, 'limitations': limitations},
            'classification': {'lane': lane, 'label_ar': LANE_AR[lane], 'hardconfirmed': hard,
                               'plan_crossing_confirmed': plan_ok, 'reason_ar': reason},
            'case_audit_ar': CASE_NOTES.get(c.get('id')),
            'resolution_status': c.get('st', 'open'),
            'limit_ar': 'تصنيف المصدر مستقل عن حالة الحل؛ لا دليل موقع أو اعتماد تنفيذ في هذا الاختبار.'}


def audit(M, proofs=None):
    """Review all existing clashes and source disagreements without mutation."""
    plan_cases = _plan_cases()
    issues = [classify(M, c, proofs, plan_cases=plan_cases) for c in M.get('clashes', [])]
    counts = collections.Counter(q['classification']['lane'] for q in issues)
    geometry_counts = collections.Counter(q['geometry']['state'] for q in issues)
    conflicts = [_source_conflict(q) for q in M.get('drawingIssues', []) if q.get('status') == 'source_conflict']
    zconflicts = [q for q in conflicts if q.get('zconflict')]
    return {'version': 1, 'coordinate_units': {'xy': 'cm', 'z': 'm'},
            'counts': dict(counts), 'geometry_counts': dict(geometry_counts),
            'coverage': {'existing_clashes': len(M.get('clashes', [])), 'reviewed': len(issues),
                         'uncovered': len(M.get('clashes', []))-len(issues),
                         'geometry_unsupported': sum(bool(q['geometry'].get('unsupported_geometry_elements')) for q in issues),
                         'geometry_unproved': sum(q['geometry']['state'] == 'unproved' for q in issues),
                         'source_conflicts': len(conflicts), 'source_zconflicts': len(zconflicts),
                         'confirmed_plan_source_routes': len({q['source']['plan_proof']['source_physical_route_group'] for q in issues if q['classification']['plan_crossing_confirmed']}),
                         'site_verified': 0},
            'lanes_ar': LANE_AR, 'original_tolerance': copy.deepcopy(ORIGINAL_TOLERANCE),
            'issues': issues, 'source_conflicts': conflicts, 'zconflicts': zconflicts,
            'review_cases': [q for q in issues if q.get('case_audit_ar')],
            'geometry_preserved': True, 'legacy_clash_list_preserved': True,
            'model_geometry_sha256': _hash([[e['id'], e['g']] for e in M['els']]),
            'limit_ar': 'الفحص يعيد تصنيف الدليل دون تغيير هندسة أو سماحة أو حذف نتائج. source_conflict من سجل المصدر،ولا يساوي اصطدامًا ماديًا أو حلًا ميدانيًا.'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model')
    parser.add_argument('output')
    args = parser.parse_args()
    with open(args.model, encoding='utf-8') as handle:
        model = json.load(handle)
    result = audit(model)
    with open(args.output, 'w', encoding='utf-8') as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print(json.dumps({'counts': result['counts'], 'coverage': result['coverage'], 'geometry_counts': result['geometry_counts']}, ensure_ascii=False))
