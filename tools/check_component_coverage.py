# -*- coding: utf-8 -*-
"""Independent coverage inventory for every component; read-only model/source audit.

Citations and type cf=doc are never geometric verification. Archived extraction
matches prove only consistency with that record. Only a fresh, independently
bound position gate or actual PDF primitive check can be source_checked, for XY
only. Heights, cross-sections, semantics and operational behaviour remain separate.
"""
import argparse, collections, copy, hashlib, json, math, os, re, sys
from pathlib import Path
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'pipeline', 'data')
sys.path.insert(0, os.path.join(ROOT, 'pipeline'))
TOL = .2  # Same XY threshold as check_drawn_positions, never a host tolerance.
GEN = re.compile(r'-(X|K|V|ARF|AD|PG|VT|SM|ST|FP|WS|ELR|W|SG)\d{4,}$')
PAGE_RE = re.compile(r'(ARCH[12]|STR|MECH[12]|ELEC[12])\s*(?:[:]|p\s*|ص\s*)(\d+)', re.I)


def read(name):
    p = os.path.join(DATA, name+'.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


def sha(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def xy(g):
    if g[0] in ('b', 'cyl', 'sph'): return [g[1], g[2]]
    p = g[1] if g[0] in ('t', 'd', 'p', 'rs', 'tri', 'mesh') else [[g[1], g[2]], [g[3], g[4]]] if g[0] == 'r' else None
    return [(min(q[k] for q in p)+max(q[k] for q in p))/2 for k in (0, 1)] if p else None


def plan(g):
    if g[0] == 'mesh':
        # Actual projected surface triangles only; no hull or bounding box solid.
        parts = [Polygon([g[1][i][:2] for i in face]) for face in g[2]]
        return unary_union([p for p in parts if p.is_valid and p.area > 0])
    if g[0] in ('t', 'd', 'rs'):
        p = [q[:2] for q in g[1]]
        return Point(p[0]) if all(math.dist(p[0], q) < 1e-8 for q in p) else LineString(p)
    if g[0] == 'p': return Polygon(g[1], g[4] if len(g)>4 and g[4] else None).buffer(0)
    if g[0] == 'r': return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4]))
    p = xy(g)
    return Point(p) if p else None


def z_range(g):
    if g[0] == 'b': return g[6:8]
    if g[0] == 'r': return g[5:7]
    if g[0] == 'cyl': return g[4:6]
    if g[0] == 'p': return g[2:4]
    if g[0] in ('t', 'd', 'rs', 'tri', 'mesh'): return [min(p[2] for p in g[1]), max(p[2] for p in g[1])]
    return None


def references(M, e):
    t, a = M.get('types', {}).get(e.get('t'), {}), e.get('a') or {}
    r = [M['sp'][i] for i in e.get('s', []) if isinstance(i, int) and 0 <= i < len(M.get('sp', []))]
    r += t.get('sr', [])
    r += [a[k] for k in ('source_reference', 'source_z_reference') if a.get(k)]
    if a.get('source_page'):
        r.append(str(a.get('source_set', ''))+':'+str(a['source_page']) if a.get('source_set') else str(a['source_page']))
    return list(dict.fromkeys(str(q) for q in r))


def height_basis(M, e, refs):
    if (e.get('a') or {}).get('core_stairs_source_surfaces') and (e.get('a') or {}).get('source_surface_Z_checked'):
        return 'finished_surface_datum_and_derived_risers', ['مناسيب أسطح الرسم من القطاع وتقسيم الرحلة؛ لا قبول لبطن الخرسانة أو الارتكاز أو كامل جسم الدرج']
    a, t = e.get('a') or {}, M.get('types', {}).get(e.get('t'), {})
    assumptions = list(t.get('asm', []))+[a[k] for k in ('assumed', 'z_note', 'height_note', 'level_note') if a.get(k)]
    assumptions += [r for r in refs if 'افتراض' in r]
    heights = [q for q in assumptions if any(w in str(q) for w in ('ارتفاع', 'الارتفاع', 'منسوب', 'قاع', 'سقف', 'قاعدة', 'رأسي', 'حلقة'))]
    if a.get('assumed_h') is not None: heights.append('assumed_h='+str(a['assumed_h']))
    if a.get('connector') or a.get('riser'): heights.append('Derived endpoint elevations; not an independently traced section')
    if heights: return 'assumed_or_derived', list(dict.fromkeys(str(q) for q in heights))
    if a.get('source_z_reference'): return 'section_reference_requires_check', [str(a['source_z_reference'])]
    if a.get('drawn_ffl_m') is not None: return 'drawn_ffl_only', ['FFL does not prove complete component height or mounting detail']
    return 'not_independently_checked', []


def archived_bindings(M):
    """Deterministic emitter identities, never nearest-ID matching."""
    bindings = {}
    for name, suffix in (('roof', 'S'), ('mep_bg', 'M'), ('elec_rooms', 'ER')):
        d = read(name); counts = collections.Counter()
        for index, q in enumerate(d.get('els', [])):
            counts[(q['c'], q['l'])] += 1
            if name == 'roof': eid = '%s-R-S%04d' % (q['c'], index+1)
            elif name == 'mep_bg': eid = '%s-%s-M%04d' % (q['c'], q['l'], counts[(q['c'], q['l'])])
            else: eid = '%s-%s-ER%03d' % (q['c'], q['l'], counts[(q['c'], q['l'])])
            bindings[eid] = {'file': name+'.json', 'record': 'els[%d]' % index, 'source': q.get('src', []), 'geometry': q['g'], 'type': q.get('t')}
    for q in read('els_struct'):
        bindings[q['id']] = {'file': 'els_struct.json', 'record': q['id'], 'source': q.get('s', []), 'geometry': q['g'], 'type': q.get('t')}
    # Original make_model emitter enumerates across categories in this fixed order.
    import kb_elec as K
    inst = read('elec_inst'); counts = collections.Counter()
    levels = [('TY', ('2', '3', '4', '5')), ('1', ('1',)), ('G', ('G',)), ('B', ('B',)), ('R', ('R',)), ('T', ('T',))]
    for family in ('light', 'power', 'fa', 'lc', 'tel', 'ltg'):
        for sk, lvs in levels:
            rec = inst.get(family+'|'+sk, {})
            for lv in lvs:
                for index, q in enumerate(rec.get('inst', [])):
                    cls = q.get('c')
                    if not cls or cls not in K.C or family == 'tel' and cls not in ('T18', 'T19', 'T20'): continue
                    if family == 'lc' and cls == 'T14' and lv != 'G': cls = 'T2'
                    category = K.C[cls]['cat']; counts[category] += 1
                    eid = '%s-%s-%04d' % (category, lv, counts[category])
                    bindings[eid] = {'file': 'elec_inst.json', 'record': '%s|%s.inst[%d]' % (family, sk, index), 'source': [rec.get('sheet')],
                                     'anchor': [q['x'], q['y']], 'class': cls, 'type': 'e_'+cls,
                                     'semantic_limit': 'Raster-classified symbol bounding-box centre; plate face/apex and class require PDF check'}
    return bindings


def raw_water_supply(M, tolerance=TOL):
    """Compare legacy CW/HW traces to actual PDF layer primitives, not text.

    A route passes only when the entire centreline is covered by the original
    same-layer linework within the existing XY threshold. This does not prove
    pipe diameter, glyph semantics, Z, or that all source routes were extracted.
    Heater clusters retain raw primitive identities; unmatched clusters are
    candidates until semantic confirmation, never automatically generated.
    """
    import lib, symbols as SY
    result, missing, inventory = {}, [], []
    for page, levels in ((18, ('B',)), (19, ('G',)), (20, ('1',)), (21, ('2', '3', '4', '5')), (22, ('R',))):
        sh = lib.Sheet('MECH2', page)
        bounds = (-50, -150, 4500, 4500) if page == 18 else (50, -150, 3250, 2000)
        raw = {}
        for family, layer in (('cold', 'M_WS_CW'), ('hot', 'M_WS_HW')):
            lines, ids = [], []
            for index, d in enumerate(sh.D):
                if d['layer'] != layer: continue
                for pi, p in enumerate(d['polys']):
                    if len(p) < 2: continue
                    world = [sh.T(*q) for q in p]
                    ls = LineString(world)
                    if ls.length <= 1e-8 or not box(*bounds).intersects(ls): continue
                    lines.append(ls); ids.append([index, pi])
            raw[family] = (lines, ids, unary_union(lines), STRtree(lines) if lines else None)
        for lv in levels:
            matched = collections.Counter()
            for e in M['els']:
                if e['l'] != lv or e.get('t') not in ('pipe_cold', 'pipe_hot') or e['g'][0] != 't': continue
                if (e.get('a') or {}).get('connector') or re.search(r'-(K|V)\d{4}$', e['id']): continue
                refs = references(M, e)
                if not any(re.search(r'MECH2\s*(?:p|ص)\s*'+str(page)+r'\b', r) for r in refs): continue
                fam = 'cold' if e['t'] == 'pipe_cold' else 'hot'; lines, indices, linework, tree = raw[fam]
                route = plan(e['g'])
                if not lines: continue
                hit = list(tree.query(route.buffer(tolerance), predicate='intersects'))
                # Distant primitives cannot cover any part of this route. Use
                # the exact spatial subset to avoid buffering the whole sheet
                # again for every component; the threshold is unchanged.
                nearby=unary_union([lines[i] for i in hit])
                outside = route.difference(nearby.buffer(tolerance, cap_style=2, join_style=2))
                # Also preserve a measured diagnostic; the continuous coverage is the gate.
                probes = [route.interpolate(i/200, normalized=True) for i in range(201)] if route.geom_type == 'LineString' else [route]
                nearest=tree.nearest(probes)
                deviation=max(p.distance(lines[int(i)]) for p,i in zip(probes,nearest))
                endpoints=[Point(p[:2]) for p in e['g'][1]]
                endpoint_nearest=tree.nearest(endpoints)
                vertex_delta=max(p.distance(lines[int(i)]) for p,i in zip(endpoints,endpoint_nearest))
                gaps=[q.length for q in getattr(outside,'geoms',[outside]) if not q.is_empty]
                covered_trace=route.intersection(nearby.buffer(tolerance,cap_style=2,join_style=2))
                def spans(shape):
                    return [[[round(x,5),round(y,5)] for x,y in q.coords] for q in getattr(shape,'geoms',[shape]) if q.geom_type=='LineString' and not q.is_empty]
                # A short interpolated span between correctly placed source
                # vertices is evidence of extraction gap-joining, not evidence
                # that the whole pipe was physically displaced. The 14cm value
                # describes the historical axis_merge rule; it never changes
                # the .2cm independent position gate or accepts a connection.
                failure_kind='interpolated_source_gap_requires_semantic_review' if not outside.is_empty and vertex_delta<=tolerance and max(gaps or [0])<=14 else 'trace_deviation_requires_source_review'
                result[e['id']] = {'pass': outside.is_empty, 'source': 'MECH2:%d' % page,
                                  'layer': 'M_WS_CW' if fam == 'cold' else 'M_WS_HW',
                                  'method': 'Entire model XY trace inside actual PDF layer linework envelope',
                                  'sampled_deviation_cm': deviation, 'uncovered_model_trace_cm': outside.length,
                                  'model_vertex_deviation_cm':vertex_delta,'uncovered_spans_cm':gaps,
                                  'model_spans_within_source_threshold_xy_cm':spans(covered_trace),
                                  'model_spans_outside_source_threshold_xy_cm':spans(outside),
                                  'span_basis':'Partition of current model trace at the existing .2cm source envelope; these are not replacement source coordinates',
                                  'replacement_review_path':'pipeline/plumb.py extract_ws -> pipes.axis_merge(gap14) -> mep_common.merge_polylines(tol1.2) -> mep_common.simplify_poly(tol0.8); raw source primitive IDs retained below',
                                  'failure_kind':None if outside.is_empty else failure_kind,
                                  'raw_drawing_primitives': [indices[i] for i in hit], 'registration': sh.reg,
                                  'limit': 'XY trace only; source linework includes symbols, so semantics/dimensions/Z remain unverified'}
                matched[fam] += 1
            inventory.append({'source': 'MECH2:%d' % page, 'level': lv, 'raw_pipe_layer_primitives': {k: len(v[0]) for k,v in raw.items()}, 'model_routes_checked': dict(matched)})
        # Independently keep drawing indices lost by the historical heater extractor.
        prims = []
        for di, d in enumerate(sh.D):
            if d['layer'] != 'WATER': continue
            for pi, p in enumerate(d['polys']):
                if not p: continue
                xs, ys = [q[0] for q in p], [q[1] for q in p]
                if max(max(xs)-min(xs), max(ys)-min(ys)) > 80: continue
                prims.append({'bb': [min(xs),min(ys),max(xs),max(ys)], 'drawing':di, 'primitive':pi})
        for group in SY.cluster_prims(prims, gap=.6):
            inf = SY.group_info(prims, group); w,h=inf['w']*sh.reg['s'],inf['h']*sh.reg['s']
            if not (55 <= max(w,h) <= 95 and 30 <= min(w,h) <= 60): continue
            anchor = list(sh.T(*inf['c']))
            if not box(*bounds).covers(Point(anchor)): continue
            for lv in levels:
                devices = [e for e in M['els'] if e['l']==lv and e['c']=='P.heater']
                hits = [e for e in devices if math.dist(xy(e['g']), anchor) <= tolerance]
                proof = {'source':'MECH2:%d'%page,'level':lv,'source_xy_cm':anchor,'raw_drawing_primitives':[[prims[i]['drawing'],prims[i]['primitive']] for i in group],
                         'method':'Actual WATER-layer clustered heater footprint; bounding-box centre', 'source_bbox_dimensions_cm':[w,h]}
                if len(hits)==1:
                    result[hits[0]['id']] = {**proof,'pass':True,'sampled_deviation_cm':math.dist(xy(hits[0]['g']),anchor),'limit':'XY heater footprint only; capacity, mounting and height separate'}
                elif not hits:
                    missing.append(dict(proof,status='unmatched_raw_symbol_candidate',reason='Heater-sized WATER cluster has no model heater at its drawn centre; semantic review required'))
    return result, missing, inventory


def raw_drain_sources(M, tolerance=TOL):
    """Rebind drain review identities to original PDF vectors and current XY.

    The reviewed geometry is an identity guard only. Actual PDF drawings are
    read again, then transformed using the current sheet registration. A whole
    route passes only for raw_drawn_linework and continuous envelope coverage.
    Glyph compositions, bridges and interlevel risers retain their separate
    limits even if a generic position gate or some source vertices pass.
    """
    import lib
    import check_drawn_positions as position_gate
    import drain_trace_review as drain_review
    review=read('drain_trace_review')
    data_digest=sha(review)
    records=review.get('records',{})
    elements={e['id']:e for e in M['els']};sheets={};results={}
    vp_ids=set(review.get('VP_ids',[]));source_counts=collections.Counter()
    checked_counts=collections.Counter();failures=[];absent=[]
    source_hashes={}
    # The V ordinal is shared by media and can change when a different medium
    # changes its output count. Current drain risers are generator derivatives;
    # their old nearby plan records can only be candidate references. Never
    # bind a historical V row to a coincident current ordinal.
    riser_bindings=drain_review.derived_riser_bindings(M,records=records)
    riser_generation=position_gate.drain_riser_generation_checks(M)
    riser_checks={q['id']:q for q in riser_generation['checks']}
    def spans(shape):
        return [[[round(x,6),round(y,6)]for x,y in p.coords]
                for p in getattr(shape,'geoms',[shape])
                if p.geom_type=='LineString' and not p.is_empty and p.length>1e-8]
    for eid,q in records.items():
        source_counts[q['status']]+=1
        if q['status']=='derived_vertical_riser':continue
        e=elements.get(eid)
        if e is None:
            absent.append({'id':eid,'source':q['source'],'reason':'Reviewed drain identity absent from current model'})
            continue
        problems=[]
        guard=sha(e['g'])==q.get('geometry_guard_sha256')
        if not guard:problems.append('Current geometry differs from the reviewed identity guard; source binding must be renewed')
        if e['c']!=q['category'] or e['l']!=q['level']:problems.append('Current category or level differs from the reviewed source identity')
        permitted_types={q['type']}
        if eid in vp_ids:permitted_types.add('vent_drain_pipe')
        if e.get('t') not in permitted_types:problems.append('Current service type differs from the reviewed layer binding')
        book,page=q['source'].split(':');page=int(page);key=(book,page)
        if key not in sheets:
            sh=lib.Sheet(book,page)
            # Do not trust the cached/data coordinates as the source itself.
            # Indices bind the actual current PDF get_drawings list.
            sheets[key]=(sh,lib.doc(book)[page-1].get_drawings(),{})
            if book not in source_hashes:
                with open(os.path.join(lib.DL,lib.FILES[book]),'rb')as f:
                    source_hashes[book]=hashlib.sha256(f.read()).hexdigest()
        sh,drawings,flat=sheets[key]
        if sh.reg!=q.get('registration'):problems.append('Stored source registration differs from current independently measured registration')
        stored={(p['drawing'],p['poly']):p for p in q.get('raw_primitives',[])}
        indices=q.get('source_primitives',[])
        if set(tuple(v)for v in indices)!=set(stored):problems.append('Source primitive identity list differs from stored raw proof')
        lines=[];actual_records=[]
        for di,pi in indices:
            if not (0<=di<len(drawings)):
                problems.append('Original PDF drawing index absent: %s'%di);continue
            d=drawings[di]
            if d.get('layer')!=q['layer'] or d.get('fill'):
                problems.append('Original primitive is not unfilled linework on the bound service layer: %s'%di);continue
            if di not in flat:flat[di]=lib.flat_path(d,seg_per_curve=10)
            if not (0<=pi<len(flat[di])):
                problems.append('Original polyline index absent: %s:%s'%(di,pi));continue
            pdf=[list(v)for v in flat[di][pi]]
            world=[list(sh.T(*v))for v in pdf]
            p=stored.get((di,pi),{})
            if sha(pdf)!=sha(p.get('pdf_points')) or sha(world)!=sha(p.get('xy')) or p.get('layer')!=q['layer']:
                problems.append('Stored raw coordinates/layer differ from original PDF and current transform: %s:%s'%(di,pi))
            actual_records.append({'drawing':di,'poly':pi,'layer':q['layer'],'pdf_points_sha256':sha(pdf),'xy_sha256':sha(world)})
            if len(world)>=2 and any(math.dist(world[0],v)>1e-8 for v in world):lines.append(LineString(world))
        route=plan(e['g']);linework=unary_union(lines)
        envelope=linework.buffer(tolerance,cap_style=1,join_style=1)
        outside=route.difference(envelope) if route is not None else None
        covered=route.intersection(envelope) if route is not None else None
        probes=[Point(v[:2])for v in e['g'][1]] if e['g'][0]=='t' else []
        if route is not None and route.geom_type=='LineString':
            probes += [route.interpolate(i/200,normalized=True)for i in range(201)]
        delta=max((v.distance(linework)for v in probes),default=0) if lines else None
        vertex_delta=max((Point(v[:2]).distance(linework)for v in e['g'][1]),default=0) if lines and e['g'][0]=='t' else None
        binding_valid=not problems and bool(lines) and route is not None
        whole=bool(binding_valid and outside.is_empty)
        original_status=q['status']
        classification='source_checked' if original_status=='raw_drawn_linework' and whole else 'derived' if binding_valid and original_status in ('derived_bridge_through_source_symbols','derived_vertical_riser') else 'unverified'
        if original_status=='raw_drawn_linework' and binding_valid and not whole:
            problems.append('Current complete trace is not covered by its original PDF linework at the existing threshold')
        rr={'pass':classification=='source_checked','source':q['source'],'layer':q['layer'],
            'method':'Complete current XY trace checked against bound original PDF service-layer primitives',
            'coverage_classification':classification,'source_review_status':original_status,
            'source_record':eid,'source_data_sha256':data_digest,'source_record_sha256':sha(q),
            'source_pdf_sha256':source_hashes[book],'geometry_guard_matches':guard,
            'source_binding_valid':binding_valid,'source_binding_problems':problems,
            'raw_drawing_primitives':indices,'actual_raw_primitive_checks':actual_records,
            'registration':sh.reg,'source_parser':'PyMuPDF get_drawings + lib.flat_path(seg_per_curve=10)',
            'whole_current_trace_in_source_envelope':whole,
            'whole_trace_xy_verified':classification=='source_checked',
            'sampled_deviation_cm':delta,'model_vertex_deviation_cm':vertex_delta,
            'uncovered_model_trace_cm':outside.length if outside is not None else None,
            'uncovered_spans_cm':[p.length for p in getattr(outside,'geoms',[outside]) if p is not None and p.geom_type=='LineString' and not p.is_empty],
            'model_spans_within_source_threshold_xy_cm':spans(covered) if covered is not None else [],
            'model_spans_outside_source_threshold_xy_cm':spans(outside) if outside is not None else [],
            'span_basis':'Partition of the current model trace at .2cm from original PDF vectors; not replacement geometry or proof of a connection',
            'tolerance_cm':tolerance,'physical_geometry_verified':False,
            'limit':q['limit_ar']+' القطر والمنسوب والمادة والتشطيب والسند غير مثبتة بهذا الفحص.'}
        if classification=='derived':
            rr['failure_kind']='derived_vertical_riser' if original_status=='derived_vertical_riser' else 'interpolated_source_gap_requires_semantic_review'
        elif classification=='unverified':rr['failure_kind']='source_arc_glyph_composition_pending' if original_status=='arc_glyph_composition_pending' and binding_valid else 'drain_source_binding_or_trace_requires_review'
        else:rr['failure_kind']=None
        results[eid]=rr;checked_counts[classification]+=1
        if problems or not binding_valid:failures.append({'id':eid,'source':q['source'],'problems':problems or ['No bound source linework/current trace']})
    for eid,binding in riser_bindings['bindings'].items():
        checked=riser_checks.get(eid)
        problems=checked.get('errors',[]) if checked else ['Current generated drain riser lacks an independent classification check']
        valid=bool(checked and checked['pass'])
        classification='derived' if valid else 'unverified'
        results[eid]={'pass':False,'source':'pipeline/risers.py','layer':None,
            'method':'Current drain riser generation/provenance and exact canonical c/t/l/g classification guard',
            'coverage_classification':classification,'source_review_status':'derived_vertical_riser',
            'source_binding_valid':valid,'source_binding_problems':problems,
            'current_riser_binding':binding,'independent_generation_check':checked,
            'generation_module_sha256':hashlib.sha256(Path(position_gate.ROOT,'pipeline','risers.py').read_bytes()).hexdigest(),
            'source_record':binding['historical_id'],'source_data_sha256':data_digest,
            'historical_plan_record_is_candidate_only':True,
            'whole_current_trace_in_source_envelope':False,'whole_trace_xy_verified':False,
            'physical_geometry_verified':False,'sampled_deviation_cm':None,
            'model_vertex_deviation_cm':None,'uncovered_model_trace_cm':None,
            'failure_kind':'derived_vertical_riser',
            'limit':'الصاعد ناتج مشتق من نهايات النموذج. الربط التاريخي فريد بـc/t/l/g كاملة فقط، لا برقمV أو القرب؛ الخطوط القديمة مرشحات وليست دليلXY أوZ أو قطر أو مادة أو اتصال.'}
        checked_counts[classification]+=1
        if problems:failures.append({'id':eid,'source':'pipeline/risers.py','problems':problems})
    inventory={'source_scope':review.get('source_scope'),'review_records':len(records),
               'source_status_counts':dict(source_counts),'current_classification_counts':dict(checked_counts),
               'actual_pdf_pages_checked':len(sheets),'source_pdf_sha256':source_hashes,
               'source_data_sha256':data_digest,'source_binding_failures':failures,
               'missing_reviewed_identities':absent,'tolerance_cm':tolerance,
               'current_derived_riser_bindings':riser_bindings,
               'current_derived_riser_generation_checks':riser_generation,
               'geometry_preserved':True,'physical_geometry_verified':False,
               'limit':'Whole source_checked applies only to raw_drawn_linework XY; glyph compositions, bridges and vertical risers are never promoted to complete physical source routes'}
    return results,inventory


def _historical_transform(clusters, records):
    """Exact feasibility of the archive's .1 cm coordinate rounding intervals.

    Least squares need not keep every point inside its rounding interval. For a
    single common scale, all pair differences constrain an interval of feasible
    scales; offsets are the intersections of their per-point intervals.
    """
    import numpy as np
    lo,hi=-math.inf,math.inf
    for axis,sign in ((0,1),(1,-1)):
        q=np.array([c['c'][axis]*sign for c in clusters]);v=np.array([r['x' if axis==0 else 'y'] for r in records])
        dq=q[:,None]-q[None,:];dv=v[:,None]-v[None,:];mask=dq>1e-10
        if mask.any():
            lo=max(lo,float(((dv-.1)[mask]/dq[mask]).max()));hi=min(hi,float(((dv+.1)[mask]/dq[mask]).min()))
    if lo>hi+1e-10:return None
    s=(lo+hi)/2 if math.isfinite(lo+hi) else 1
    offsets=[]
    for axis,sign in ((0,1),(1,-1)):
        values=[r['x' if axis==0 else 'y']-s*c['c'][axis]*sign for c,r in zip(clusters,records)]
        a,b=max(values)-.05,min(values)+.05
        if a>b+1e-7:return None
        offsets.append((a+b)/2)
    return [s,*offsets]


def _electrical_legend_sizes():
    import lib, elec
    ref=lib.Sheet('ARCH1',7)
    families={
        'light':elec.exemplars_light(ref)[0],
        'power':elec.exemplars_by_legend(ref,'ELEC1',12,elec.POWER_LAYERS,[(360,1405,620,1610),(625,1405,900,1610)],elec.K.POWER_MAP,maxdim=60)[0],
        'fa':elec.exemplars_by_legend(ref,'ELEC2',5,elec.FA_LAYERS,[(660,1385,925,1545),(925,1385,1165,1545),(1165,1385,1450,1545)],elec.K.FA_MAP,maxdim=70)[0],
        'lc':elec.exemplars_by_legend(ref,'ELEC2',21,elec.LC_LAYERS+('0',),[(940,1425,1120,1480),(1125,1425,1330,1480),(940,1490,1120,1575),(1125,1490,1330,1575)],elec.LC_MAP,maxdim=90)[0],
        'tel':elec.exemplars_by_legend(ref,'ELEC2',31,elec.TEL_LAYERS,[(985,1462,1340,1590)],elec.TEL_MAP,maxdim=70)[0],
        'ltg':elec.exemplars_by_legend(ref,'ELEC2',14,elec.LTG_LAYERS,[(1040,1555,1330,1640)],elec.LTG_MAP,maxdim=70)[0]}
    out={}
    for family,ex in families.items():
        sizes=collections.defaultdict(list)
        for e in ex:sizes[e.label].append(e.size)
        out[family]=dict(sizes)
    return out


def raw_electrical(M, bindings, tolerance=TOL):
    """Bind historical symbol rows to the actual ordered PDF primitive clusters.

    The original extractor's complete row order, cluster primitive count and
    dimensions must agree. A fitted historical transform only checks that this
    is the same archived extraction; current XY uses the independently measured
    sheet registration. No model proximity or nearest host assigns identity.
    """
    import lib, symbols as SY
    import numpy as np
    layers = {'light': ('E.LIGHT','ELE.LIGHT'), 'power': ('E.POWER','POWER'),
              'fa': ('FIRE ALARM',), 'lc': ('S.M.A TV','LOW CURRENT','ACCESS CONTROL','CCTV'),
              'tel': ('TELEPHONE',), 'ltg': ('Down conductor','ACCESSORIES','LIGHT PROTECTION')}
    records = read('elec_inst'); result, inventory = {}, []
    legend_sizes=_electrical_legend_sizes()
    identity = collections.defaultdict(list)
    for eid,b in bindings.items():
        if b['file']=='elec_inst.json': identity[b['record']].append(eid)
    elements = {e['id']:e for e in M['els']}
    for key, rec in records.items():
        family = key.split('|')[0]
        if family not in layers or not rec.get('inst'): continue
        book,page = PAGE_RE.findall(rec['sheet'])[0];page=int(page)
        sh=lib.Sheet(book.upper(),page)
        rects=[(w['x']-70,w['y']-35,w['x']+360,w['y']+330) for w in sh.WD if 'LEGEND' in w['s'].upper() and w['x']<2200]
        prims=[]; maxdim=40 if family=='ltg' else 60
        for di,d in enumerate(sh.D):
            if d['layer'] not in layers[family]:continue
            for pi,p in enumerate(d['polys']):
                if not p:continue
                xs,ys=[q[0] for q in p],[q[1] for q in p]
                bb=[min(xs),min(ys),max(xs),max(ys)]
                if max(bb[2]-bb[0],bb[3]-bb[1])>maxdim:continue
                prims.append({'bb':bb,'drawing':di,'primitive':pi})
        clusters=[]
        for group in SY.cluster_prims(prims,gap=.5):
            q=SY.group_info(prims,group);x,y=q['c']
            if x>=2040 or any(r[0]<=x<=r[2] and r[1]<=y<=r[3] for r in rects):continue
            if q['w']*rec['s']<2.5 and q['h']*rec['s']<2.5:continue
            q['indices']=[[prims[i]['drawing'],prims[i]['primitive']] for i in group]
            clusters.append(q)
        summary={'source':book.upper()+':'+str(page),'family':family,'archive_key':key,
                 'archive_rows':len(rec['inst']),'raw_clusters':len(clusters),'identity_method':'Complete extractor row order + primitive count + dimensions + recovered historical transform, never nearest model'}
        inventory.append(summary)
        if len(clusters)!=len(rec['inst']):summary['binding_error']='Full ordered cluster count mismatch';continue
        dims=max(max(abs(q['w']*rec['s']-r['w']),abs(q['h']*rec['s']-r['h'])) for q,r in zip(clusters,rec['inst']))
        counts=all(q['n']==r['n'] for q,r in zip(clusters,rec['inst']))
        # Recover one historical scale/offset jointly from archived rounded XY;
        # this is an association check and never the current source transform.
        old=_historical_transform(clusters,rec['inst'])
        if old is None:
            summary['binding_error']='No historical transform satisfies all original .1cm rounding intervals';continue
        residual=max(math.hypot(old[0]*q['c'][0]+old[1]-r['x'],-old[0]*q['c'][1]+old[2]-r['y']) for q,r in zip(clusters,rec['inst']))
        summary.update(dimension_rounding_error_cm=dims,primitive_counts_match=counts,historical_xy_residual_cm=residual,
                       historical_transform={'s':float(old[0]),'ox':float(old[1]),'oy':float(old[2])},registration=sh.reg)
        # Source scale was rounded to .001 in the archive, so dimensions can
        # differ by up to max PDF dimension *.0005 plus .05 cm rounding.
        dimension_bound=maxdim*.0005+.05+1e-7
        if not counts or dims>dimension_bound or residual>math.sqrt(2)*.05+1e-7:
            summary['binding_error']='Ordered cluster consistency failed';continue
        for i,(q,r) in enumerate(zip(clusters,rec['inst'])):
            source=list(sh.T(*q['c'])); record='%s.inst[%d]'%(key,i)
            for eid in identity.get(record,[]):
                if eid not in elements:continue
                # A later correction bound to an actual vector glyph/apex is
                # more specific than this historical raster bbox centre.
                if (elements[eid].get('a') or {}).get('source_xy') is not None:continue
                sizes=legend_sizes.get(family,{}).get(r.get('c'),[])
                ratios=[max(q['w'],q['h'])/s for s in sizes if s]
                isolated=any(.5<=v<=2 for v in ratios)
                delta=math.dist(xy(elements[eid]['g']),source)
                result[eid]={'pass':delta<=tolerance,'source':book.upper()+':'+str(page),
                             'source_xy_cm':source,'source_pdf_centre_pt':list(q['c']),
                             'raw_drawing_primitives':q['indices'],'registration':sh.reg,
                             'archive_record':record,'anchor':'drawn_symbol_cluster_bbox_centre',
                             'method':'Actual ordered PDF symbol-cluster centre, deterministic legacy emitter identity',
                             'sampled_deviation_cm':delta,'uncovered_model_trace_cm':0,
                             'source_bbox_pdf_pt':[q['w'],q['h']],'legend_size_pdf_pt':sizes,'legend_size_ratio':ratios,
                             'isolated_symbol_size_match':isolated,
                             'limit':'XY symbol anchor only. Historical raster class, physical device orientation/size and Z require separate proof; no claim of wall face or shop location'}
    return result,inventory


def raw_hvac_sources(M, tolerance=TOL):
    """Recheck named HVAC glyphs and literal text against the original PDF.

    The shared independent checker reads the actual circle/quad primitives and
    T/FCU text. Its result only binds the graphic centre and the one FCU angle;
    the retained proxy dimensions, elevations, material and mount are not proof.
    """
    import check_drawn_positions as gate
    review=read('restore_hvac_source'); elements={e['id']:e for e in M['els']}
    result={}; counts=collections.Counter(); missing=[]
    for eid,q in review.get('records',{}).items():
        e=elements.get(eid)
        if e is None:
            missing.append(eid);counts['absent']+=1;continue
        checked=gate.hvac_source_check(e)
        passed=bool(checked and all(checked.get(k) is not None and checked[k]<=tolerance
            for k in ('deviation_cm','metadata_deviation_cm','source_anchor_deviation_cm','source_transform_deviation_cm'))
            and checked.get('source_semantic_text_verified') and checked.get('source_rotation_matches_symbol'))
        counts['passed' if passed else 'unverified']+=1
        result[eid]={'pass':passed,'source':q['source']['source_page'],
            'method':'Actual original MECH1 circle/quad and literal T/FCU-R-LR text; graphic anchor only',
            'sampled_deviation_cm':checked.get('deviation_cm',0) if checked else 0,
            'uncovered_model_trace_cm':0,'original_pdf_check':checked,
            'source_record_sha256':sha(q),
            'parser':'tools/check_drawn_positions.py:hvac_source_check',
            'binding_problem':None if checked else 'Current metadata/identity/raw vector/text binding is missing or stale',
            'source_xy_verified':passed,'source_dimensions_verified':False,'source_Z_verified':False,
            'source_material_verified':False,'source_mount_face_verified':False,
            'limit':'A graphic anchor and FCU symbol angle are checked. No physical size, elevation, mounting face, color or complete HVAC connection is certified.'}
    return result,{'records':len(review.get('records',{})),'counts':dict(counts),'missing':missing,
        'source_file':'pipeline/data/restore_hvac_source.json','source_review_sha256':sha(review),
        'source_summary':review.get('summary',{}),
        'scope_limit':'106 thermostat instances from 72 original circles plus one labelled FCU. Only source graphic XY and the FCU symbol angle are independently checked.'}


def raw_electrical_tail_sources(M, tolerance=TOL):
    """Recheck the two source curves/lines and V tips, excluding proxy links."""
    import check_drawn_positions as gate
    review=read('electrical_trace_restore');elements={e['id']:e for e in M['els']}
    result={};counts=collections.Counter();missing=[]
    for q in review.get('records',[]):
        for n in range(1,5):
            eid='E.tray-'+q['level']+'-ETR'+str(n).zfill(4);e=elements.get(eid)
            if e is None:missing.append(eid);counts['absent']+=1;continue
            if n==4:
                valid=e.get('t')=='wire_drop' and(e.get('a')or{}).get('source_kind')=='derived_graphic_terminal_connector'
                counts['derived' if valid else 'unverified']+=1
                result[eid]={'pass':False,'source':q['source'],'coverage_classification':'derived'if valid else'unverified',
                    'method':'Derived graphic terminal-to-proxy connector inside the selected source glyph',
                    'source_review_status':'derived_graphic_terminal_connector','source_binding_problems':[]if valid else['Derived connector identity changed'],
                    'source_record_sha256':sha(q),'limit':'No original complete cable path or physical port is claimed for the short link inside the symbol.'}
                continue
            checked=gate.electrical_tail_check(e)
            passed=bool(checked and all(checked.get(k)is not None and checked[k]<=tolerance
                for k in('deviation_cm','metadata_deviation_cm','source_anchor_deviation_cm','source_transform_deviation_cm')))
            counts['passed'if passed else'unverified']+=1
            result[eid]={'pass':passed,'source':q['source'],
                'method':'Original ELEC1 POWER-CONN. Bezier/straight path or literal V-arrow tip',
                'sampled_deviation_cm':checked.get('deviation_cm',0)if checked else 0,
                'uncovered_model_trace_cm':0,'original_pdf_check':checked,'source_record_sha256':sha(q),
                'parser':'tools/check_drawn_positions.py:electrical_tail_check',
                'binding_problem':None if checked else'Current raw path/arrow identity or metadata binding is missing or stale',
                'source_xy_verified':passed,'source_Z_verified':False,'source_dimensions_verified':False,
                'source_curve_100_vs_1000_segment_hausdorff_cm':q['curve_100_vs_1000_segment_hausdorff_cm'] if n==1 else 0,
                'limit':'Graphic XY and circuit arrow boundary only; physical cable diameter, height, mounting face and feeder-to-board route are unverified.'}
    return result,{'source_file':'pipeline/data/electrical_trace_restore.json','source_review_sha256':sha(review),
        'devices':len(review.get('records',[])),'counts':dict(counts),'missing':missing,
        'scope_limit':'Four literal plan paths and two source arrow tips are checked; two proxy links stay derived regardless of a generic gate result.'}


def raw_new_component_sources(M, tolerance=TOL):
    """Original component graphic/profile checks and derived assembly checks.

    Plan and boundary evidence never certifies a wall's datum-derived height,
    a full structural cap perimeter, or chute Z/support/openings. Literal GC
    dimension checks are preserved as separate, partial evidence. HVAC body
    cores exclude arrows/open strokes; window members stay derived even when
    their group's anchor/envelope is independently checked.
    """
    import check_drawn_positions as gate
    elements={e['id']:e for e in M['els']};result={};inventories={}
    lhs=read('lift_head_supports');gc=read('garbage_chute_remaining')
    def geometric_pass(checked):
        return bool(checked and all(checked.get(k)is not None and checked[k]<=tolerance
            for k in('deviation_cm','metadata_deviation_cm','source_anchor_deviation_cm','source_transform_deviation_cm')))
    for family,review,records,checker in(
            ('lift_head',lhs,list(lhs.get('records',{}).values()),gate.lift_head_wall_check),
            ('garbage_chute',gc,gc.get('records',[]),gate.garbage_source_check)):
        counts=collections.Counter();missing=[]
        for q in records:
            eid=q['id'];e=elements.get(eid)
            if e is None:missing.append(eid);counts['absent']+=1;continue
            gc_identity={'chute':('M.equip','garbage_chute'),'hopper':('M.equip','garbage_hopper'),
                         'vent':('M.pipe','garbage_chute_vent'),'fan_marker':('M.equip','garbage_exhaust_fan_marker')}
            expected=(q['category'],q['type'],q['level'])if family=='lift_head'else(*gc_identity[q['role']],q['level'])
            identity=(e['c'],e.get('t'),e['l'])==expected
            checked=checker(e) if identity else None
            passed=geometric_pass(checked);counts['passed'if passed else'unverified']+=1
            result[eid]={'pass':passed,'source':q['source']['source_page'],
                'method':'Original closed STR23 profile; graphic XY only'if family=='lift_head'else'Original full-plan GC graphic anchor and separate A1100 literal text',
                'sampled_deviation_cm':checked.get('deviation_cm',0)if checked else 0,
                'uncovered_model_trace_cm':0,'original_pdf_check':checked,
                'source_record_sha256':sha(q),'parser':'tools/check_drawn_positions.py:'+checker.__name__,
                'binding_problem':None if checked else'Current source identity/profile/glyph/literal binding is missing or stale',
                'source_xy_verified':passed,'source_Z_verified':False,'source_complete_body_verified':False,
                'dimension_metrics_are_separate_from_xy_pass':True,
                'partial_dimension_proof':{k:v for k,v in(checked or{}).items()if k.startswith('literal_')or k in('source_literal_dimensions_verified','source_diameter_deviation_cm')},
                'limit':'LHS Z is datum-derived; bearing/rebar/connectivity unverified'if family=='lift_head'else'GC literal dimensions/material are partial; plan circle is an anchor, not a physical diameter; Z/support/openings/depth/fan body remain unverified'}
        inventories[family]={'records':len(records),'counts':dict(counts),'missing':missing,'source_review_sha256':sha(review)}
    roof=read('roof_lift_source');checks=gate.lift_architectural_boundary_checks(M,tolerance);counts=collections.Counter()
    for checked in checks:
        eid=checked['id'];passed=bool(checked.get('pass'));counts['derived_boundary_passed'if passed else'unverified']+=1
        result[eid]={'pass':False,'source':'ARCH1:8',
            'coverage_classification':'derived'if passed else'unverified',
            'method':'Derived architectural A105 boundary piece checked against original outer/inner raw edges',
            'source_review_status':'derived_architectural_boundary_piece',
            'source_binding_problems':[]if passed else['Original architectural boundary piece check failed'],
            'original_pdf_check':checked,'source_review_sha256':sha(roof),
            'source_boundary_xy_checked':passed,'source_structural_extent_verified':False,
            'source_complete_body_verified':False,'source_Z_independently_checked_here':False,
            'limit':'Derived architectural cap/finish/upstands. A105 extent does not supply a closed STR slab perimeter or prove bearing; source datum/thickness references remain separate.'}
    inventories['roof_lift']={'expected':roof.get('output_count',0),'counts':dict(counts),
        'source_review_sha256':sha(roof),'status':'derived_architectural_boundaries_only'}
    water=read('water_supply_source_corrections')
    if water:
        expected=[q['id']for q in water.get('restore_records',[])]+[q['id']for q in water.get('device_markers',[])]
        expected.extend('P.cold-'+q['level']+'-WSC'+str(n).zfill(4)
            for n,q in enumerate([q for q in water.get('restore_records',[])for _ in q['parts'][1:]],13))
        counts=collections.Counter();missing=[]
        for eid in expected:
            e=elements.get(eid)
            if e is None:missing.append(eid);counts['absent']+=1;continue
            checked=gate.water_source_check(e);passed=geometric_pass(checked)
            counts['passed'if passed else'unverified']+=1
            result[eid]={'pass':passed,'source':checked.get('reference')if checked else(e.get('a')or{}).get('source_page'),
                'method':'Original straight water vertices with break glyphs excluded, or complete device graphic bbox and literal callout',
                'sampled_deviation_cm':checked.get('deviation_cm',0)if checked else 0,'uncovered_model_trace_cm':0,
                'original_pdf_check':checked,'source_review_sha256':sha(water),'parser':'tools/check_drawn_positions.py:water_source_check',
                'binding_problem':None if checked else'Raw water path/whole glyph/callout identity or vertex selection differs',
                'source_xy_verified':passed,'source_Z_verified':False,'source_complete_body_verified':False,
                'limit':'Selected literal XY path or whole-device graphic anchor only; pipe diameter/Z and device physical body dimensions/material/Z/ports/mounting/duty assignment are unverified.'}
        inventories['water_supply_corrections']={'expected':len(expected),'counts':dict(counts),'missing':missing,
            'source_review_sha256':sha(water),'retired_nonpipe_ids':[q['id']for q in water.get('retire_records',[])],
            'retirement_scope':'Sixty-one source equipment/tank/motor/coupling glyph traces are not water pipes; XY agreement alone never certifies their former pipe semantics.'}
    boundary=read('boundary_source_remaining')
    if boundary:
        import check_boundary_source
        checked_boundary=check_boundary_source.audit(M);counts=collections.Counter()
        global_binding_errors=[q for q in checked_boundary.get('findings',[])if not q.get('id')]
        for checked in checked_boundary.get('checks',[]):
            eid=checked['id'];q=boundary['records'][eid];e=elements[eid]
            identity=(e['c'],e.get('t'),e['l'])==(q['c'],q['t'],'G')
            passed=not checked.get('errors')and not global_binding_errors and identity
            original=checked.get('proof_scope')=='raw_profile'
            counts['source_profile_passed'if passed and original else'derived_outline_passed'if passed else'unverified']+=1
            result[eid]={'pass':passed and original,'source':'STR:32',
                'coverage_classification':'source_checked'if passed and original else'derived'if passed else'unverified',
                'method':'Original closed C* source quad with fresh A101 raw axes registration'if original else'Derived boundary block/coping from original C* faces, BEAM edges and joint literals',
                'sampled_deviation_cm':checked.get('xy_deviation_cm',0),'uncovered_model_trace_cm':0,
                'original_pdf_check':checked,'source_record_sha256':sha(q),
                'parser':'tools/check_boundary_source.py:audit','source_binding_problems':checked.get('errors',[])+([]if identity else['Boundary category/type/level differs']),
                'source_xy_verified':passed and original,'source_derived_boundary_xy_checked':passed and not original,
                'source_Z_verified':False,'source_complete_body_verified':False,
                'height_scope':checked.get('height_scope'),
                'limit':'C* raw XY only; above-grade height datum-derived. CB1/block outlines remain derived; joint cut, reinforcement, bearing, material grade, finish/color and site acceptance are separate.'}
        missing_boundary=checked_boundary.get('uncovered',[]);counts['absent']+=len(missing_boundary)
        inventories['boundary']={'expected':len(boundary.get('records',{})),'counts':dict(counts),
            'missing':missing_boundary,'source_review_sha256':sha(boundary),'original_pdf_summary':checked_boundary.get('summary',{}),
            'global_binding_errors':global_binding_errors,'status':'41 original column profiles;43 derived block/coping outlines'}
    outlets=read('restore_hvac_outlets_source')
    if outlets:
        import check_hvac_outlets_source
        checked_outlets=check_hvac_outlets_source.audit(M);counts=collections.Counter()
        ledger_findings=checked_outlets.get('findings',[])
        global_errors=[q for q in ledger_findings if not q.get('id')]
        ledger_byid={q['id']:q.get('errors',[])for q in ledger_findings if q.get('id')}
        for checked in checked_outlets.get('checks',[]):
            eid=checked['id'];q=outlets.get('records',{}).get(eid)
            errors=list(checked.get('errors',[]))+ledger_byid.get(eid,[])
            passed=bool(q and checked.get('pass')and not errors and not global_errors and geometric_pass(checked))
            counts['graphic_anchor_passed'if passed else'unverified']+=1
            if eid not in elements:
                counts['absent']+=1
                continue
            result[eid]={'pass':passed,'source':checked['reference'],
                'method':'Original selected actual outlet body-core graphic bbox; airflow arrows, spines and open duct linework excluded',
                'sampled_deviation_cm':checked.get('deviation_cm',0),'uncovered_model_trace_cm':0,
                'original_pdf_check':checked,'source_record_sha256':sha(q)if q else None,'parser':'tools/check_hvac_outlets_source.py:audit',
                'source_binding_problems':errors,
                'binding_problem':None if passed else'Original selected body-core identity/anchor/registration or normalized procedural Z guard differs',
                'source_xy_verified':passed,'source_Z_verified':False,'source_complete_body_verified':False,
                'source_graphic_body_extent_checked':passed,'source_graphic_angle_checked':passed,
                'limit':'Selected actual body graphic XY/bbox only. Symbolic size/angle does not prove physical dimensions/rotation, ports, material, absolute Z, mounting or operation; procedural Z is only an unchanged-assumption guard.'}
        missing=checked_outlets.get('uncovered',[])
        retirement_checks=checked_outlets.get('retirement_checks',[])
        retirement_findings=[q for q in retirement_checks if not q.get('pass')or q.get('errors')]
        for checked in retirement_findings:
            eid=checked['id']
            if eid not in elements:continue
            result[eid]={'pass':False,'source':checked['reference'],'coverage_classification':'unverified',
                'method':'Raw airflow arrow/spine/duct fragment is not an outlet device',
                'source_binding_problems':checked.get('errors',[]),
                'original_pdf_check':checked,'source_xy_verified':False,'source_Z_verified':False,
                'source_complete_body_verified':False,
                'limit':'A false outlet body must be retired; raw fragment presence does not certify a physical device.'}
        failed_ids={q['id']for q in checked_outlets.get('checks',[])+retirement_checks if not q.get('pass')or q.get('errors')}
        failed_ids.update(q['id']for q in ledger_findings if q.get('id'))
        inventories['hvac_outlets_source_restore']={'expected':len(outlets.get('records',{})),'counts':dict(counts),'missing':missing,
            'source_review_sha256':sha(outlets),'original_pdf_summary':checked_outlets.get('summary',{}),
            'ledger_findings':ledger_findings,'global_binding_errors':global_errors,
            'retirement_checks':retirement_checks,'retirement_findings':retirement_findings,
            'all_findings_count':len(failed_ids)+len(global_errors),
            'source_inventory_complete':not failed_ids and not global_errors and not missing,
            'limit':'Actual body-core anchors are counted independently from raw clusters/legend graphics. Every excluded fragment must pass retirement, including findings on identities absent from the ledger; physical dimensions/Z/mount/ports/material/operation remain unverified.'}
    dampers=read('hvac_damper_source')
    if dampers:
        import check_hvac_dampers_source
        checked_dampers=check_hvac_dampers_source.audit(M);counts=collections.Counter();missing=[]
        damper_global_findings=checked_dampers.get('global_findings',[])
        records={**dampers.get('records',{}),**dampers.get('additions',{})}
        for checked in checked_dampers.get('checks',[]):
            eid=checked['id'];q=records.get(eid)
            passed=bool(q and checked.get('pass')and not checked.get('errors')and not damper_global_findings)
            counts['graphic_anchor_passed'if passed else'unverified']+=1
            if eid not in elements:missing.append(eid);counts['absent']+=1;continue
            result[eid]={'pass':passed,'source':checked['reference'],
                'method':'Original closed L damper graphic anchor/extent/angle; exact distinct contours and original raw-grid registration',
                'sampled_deviation_cm':checked.get('deviation_cm',0),'uncovered_model_trace_cm':0,
                'original_pdf_check':checked,'source_record_sha256':sha(q)if q else None,
                'parser':'tools/check_hvac_dampers_source.py:audit',
                'binding_problem':None if passed else'Original closed L contour identity/graphic bbox/registration or normalized procedural Z guard differs',
                'source_xy_verified':passed,'source_Z_verified':False,'source_complete_body_verified':False,
                'source_graphic_body_extent_checked':passed,'source_graphic_angle_checked':passed,
                'limit':'Closed L graphic scope only; no subtype, absolute Z, physical device dimensions/rotation, material, mount, port or operation acceptance.'}
        for checked in checked_dampers.get('pending',[]):
            eid=checked['id'];counts['unverified_transform']+=1
            if eid not in elements:missing.append(eid);counts['absent']+=1;continue
            result[eid]={'pass':False,'source':checked['reference'],'coverage_classification':'unverified',
                'method':'Roof L damper symbol has no resolved absolute source registration',
                'source_binding_problems':[checked['reason']]+([]if checked.get('geometry_preserved')else['Pending roof symbol geometry changed']),
                'original_pdf_check':checked,'source_xy_verified':False,'source_Z_verified':False,
                'source_complete_body_verified':False,'source_record_sha256':sha(dampers.get('pending',{}).get(eid)),
                'limit':'Pending roof positions remain unchanged and unverified; local underlay alignment is not a global source registration.'}
        inventories['hvac_damper_source']={'expected_graphic_anchors':len(records),
            'expected_unverified_transform':len(dampers.get('pending',{})),
            'counts':dict(counts),'missing':missing,'source_review_sha256':sha(dampers),
            'original_pdf_summary':checked_dampers.get('summary',{}),'pending':checked_dampers.get('pending',[]),
            'global_findings':damper_global_findings,
            'source_inventory_complete':not missing and not damper_global_findings and all(q.get('pass')and not q.get('errors')for q in checked_dampers.get('checks',[])),
            'limit':'Qualified raw graphic anchors and six unresolved roof symbols remain separate. Normalized procedural Z guard never certifies absolute source elevation.'}
    valves=read('water_valve_source')
    if valves:
        import check_water_valves_source
        valve_audit=check_water_valves_source.audit(M);counts=collections.Counter();missing=[]
        records={**valves.get('records',{}),**valves.get('additions',{})}
        global_findings=valve_audit.get('global_findings',[])
        # Findings with a model ID outside the expected set are inventory
        # failures too; never promote merely because all expected rows pass.
        all_findings=valve_audit.get('findings',[])
        if isinstance(all_findings,int):all_findings=[{'reported_findings':all_findings}]if all_findings else[]
        inventory_failed=bool(global_findings or all_findings or valve_audit.get('summary',{}).get('findings')or valve_audit.get('summary',{}).get('uncovered'))
        checked_by={q['id']:q for q in valve_audit.get('checks',[])}
        inventory_failed=inventory_failed or set(checked_by)!=set(records)or len(checked_by)!=len(valve_audit.get('checks',[]))
        for eid,q in records.items():
            checked=checked_by.get(eid);e=elements.get(eid)
            if e is None:missing.append(eid);counts['absent']+=1;continue
            passed=bool(checked and checked.get('pass')and not checked.get('errors')and not inventory_failed)
            counts['graphic_anchor_passed'if passed else'unverified']+=1
            source=q.get('source',{})
            result[eid]={'pass':passed,'source':(checked or{}).get('reference')or source.get('source_page'),
                'method':'Original water-valve symbol graphic anchor/extent/angle and separate literal code/key/context; physical valve body and subtype remain scoped',
                'sampled_deviation_cm':(checked or{}).get('deviation_cm',0),'uncovered_model_trace_cm':0,
                'original_pdf_check':checked,'source_record_sha256':sha(q),'parser':'tools/check_water_valves_source.py:audit',
                'binding_problem':None if passed else'Original valve raw identity, graphic anchor or global inventory guard failed',
                'source_xy_verified':passed,'source_Z_verified':False,'source_complete_body_verified':False,
                'source_graphic_body_extent_checked':passed,'source_graphic_angle_checked':passed,
                'source_subtype_pending':eid in valve_audit.get('pending_subtype',[]),
                'limit':'Graphic XY only; explicit code/provision and untyped bow-tie marker are separate. No absolute Z, physical dimensions/material/mount/ports or operational acceptance; normalized procedural Z only guards retained assumptions.'}
        unexpected=[eid for eid in checked_by if eid not in records]
        inventories['water_valve_source']={'expected_graphic_anchors':len(records),'counts':dict(counts),'missing':missing,
            'source_review_sha256':sha(valves),'original_pdf_summary':valve_audit.get('summary',{}),'global_findings':global_findings,
            'all_findings':all_findings,'unexpected_checked_ids':unexpected,'pending_subtype':valve_audit.get('pending_subtype',[]),
            'source_inventory_complete':not inventory_failed and not missing and not unexpected and set(checked_by)==set(records)and all(q.get('pass')and not q.get('errors')for q in checked_by.values()),
            'limit':'Literal symbol/count inventory, not complete physical components, confirmed valve subtypes for unlabelled symbols, port connections, operating water topology or procurement acceptance.'}
    roof_voids=read('top_roof_shaft_openings_source')
    if roof_voids:
        import check_top_roof_shaft_openings_source
        opening_audit=check_top_roof_shaft_openings_source.audit(M)
        records=roof_voids.get('records',{});expected_ids=set(records)
        clips=opening_audit.get('checks',[]);raw_openings=opening_audit.get('source_opening_checks',[])
        preservation=opening_audit.get('slab_preservation_checks',[]);global_findings=opening_audit.get('global_findings',[])
        expected_clips={(eid,q['source_opening_id'])for eid,row in records.items()for q in row.get('clipped_voidrings',[])}
        actual_clips={(q.get('element_id'),q.get('source_opening_id'))for q in clips}
        inventory_failed=bool(global_findings or opening_audit.get('summary',{}).get('findings')or opening_audit.get('summary',{}).get('uncovered'))
        inventory_failed=inventory_failed or actual_clips!=expected_clips or len(clips)!=len(expected_clips)
        inventory_failed=inventory_failed or {q.get('id')for q in raw_openings}!={q['id']for q in roof_voids.get('source_openings',[])}or len(raw_openings)!=len(roof_voids.get('source_openings',[]))
        inventory_failed=inventory_failed or {q.get('id')for q in preservation}!=expected_ids or len(preservation)!=len(expected_ids)
        inventory_failed=inventory_failed or any(q.get('pass')is not True or q.get('errors')for q in clips+raw_openings+preservation)
        inventory_failed=inventory_failed or opening_audit.get('summary',{}).get('body_source_checked')!=0
        inventory_failed=inventory_failed or any(q.get('body_source_checked')is not False or q.get('physical_Z_material_acceptance')is not False for q in clips)
        inventory_failed=inventory_failed or any(q.get('full_outer_source_checked')is not False for q in preservation)
        counts=collections.Counter();missing=[]
        for eid,q in records.items():
            if eid not in elements:missing.append(eid);counts['absent']+=1;continue
            partial_passed=not inventory_failed;counts['partial_void_subtraction_checked'if partial_passed else'partial_void_check_failed']+=1
            scoped_clips=[c for c in clips if c.get('element_id')==eid]
            result[eid]={'pass':False,'partial_source_passed':partial_passed,'source':'STR:24',
                'coverage_classification':'unverified','source_binding_problems':[]if partial_passed else['Original six opening profiles/local subtraction or global inventory guard failed'],
                'partial_source_review':{'scope':'source_opening_XY_subtraction_only','pass':partial_passed,
                    'source_opening_ids':[c['source_opening_id']for c in scoped_clips],
                    'whole_profile_status':'unverified','whole_slab_source_checked':False},
                'method':'Six original SHAFT opening subdomains checked; preserved whole slab outer domain and absolute Z remain unverified',
                'parser':'tools/check_top_roof_shaft_openings_source.py:audit','source_record_sha256':sha(q),
                'original_pdf_check':{'clipped_void_checks':scoped_clips,'slab_preservation_check':next((c for c in preservation if c.get('id')==eid),None)},
                'sampled_deviation_cm':max((c.get('deviation_cm')or 0 for c in scoped_clips),default=0),
                'uncovered_model_trace_cm':0,'source_xy_verified':False,'source_outer_XY_verified':False,
                'source_opening_plan_XY_checked':partial_passed,'source_Z_verified':False,
                'source_complete_body_verified':False,'source_dimensions_verified':False,
                'limit':'Partial source opening subtraction only. Frozen old outer/Z are procedural preservation inputs, not original-source authority; no whole slab source_checked, physical body/material/rebar/bearing or site acceptance.'}
        inventories['top_roof_shaft_openings_source']={'expected_controlled_slabs':len(records),
            'expected_original_openings':len(roof_voids.get('source_openings',[])),'expected_clipped_void_parts':len(expected_clips),
            'counts':dict(counts),'missing':missing,'source_review_sha256':sha(roof_voids),
            'original_pdf_summary':opening_audit.get('summary',{}),'global_findings':global_findings,
            'source_opening_checks':raw_openings,'clipped_void_checks':clips,'slab_preservation_checks':preservation,
            'source_inventory_complete':not inventory_failed and not missing,
            'whole_slab_source_checked_promoted':0,'limit':'Six raw opening profiles and seven clipped domains only; two controlled slabs retain unverified whole footprints/Z.'}
    stair_roof=read('stair01_roof_source_correction')
    if stair_roof:
        import check_stair01_roof_source_correction
        stair_audit=check_stair01_roof_source_correction.audit(M)
        records=stair_roof.get('records',{});retired=stair_roof.get('retirement_records',{})
        checks=stair_audit.get('checks',[]);retire_checks=stair_audit.get('retirement_checks',[])
        facts=stair_audit.get('source_facts',[]);summary=stair_audit.get('summary',{})
        globals_=stair_audit.get('global_findings',[])
        bycheck={q.get('id'):q for q in checks}
        expected_caps={'S.slab-T-0008','S.slab-T-0009'}
        expected_retired={f'S.stair-R-{n:04d}'for n in range(148,169)}|{f'A.rail-R-X{n:04d}'for n in range(2037,2102)}|{'S.slab-T-0008-b'}
        inventory_failed=bool(globals_ or summary.get('findings')or summary.get('uncovered'))
        inventory_failed=inventory_failed or set(records)!=expected_caps or set(retired)!=expected_retired
        inventory_failed=inventory_failed or set(bycheck)!=expected_caps or len(checks)!=2
        inventory_failed=inventory_failed or {q.get('id')for q in retire_checks}!=expected_retired or len(retire_checks)!=87
        inventory_failed=inventory_failed or any(q.get('pass')is not True or q.get('errors')for q in checks+retire_checks)
        inventory_failed=inventory_failed or summary.get('full_cap_source_checked')!=0
        inventory_failed=inventory_failed or any(q.get('body_source_checked')is not False or q.get('absolute_Z_material_outer_source_accepted')is not False for q in checks)
        inventory_failed=inventory_failed or {q.get('source_page')for q in facts}!=set(stair_roof.get('source_pages',{}))or len(facts)!=len(stair_roof.get('source_pages',{}))
        inventory_failed=inventory_failed or any(q.get('whole_body_Z_material_accepted')is not False for q in facts)
        counts=collections.Counter();missing=[]
        for eid,q in records.items():
            if eid not in elements:missing.append(eid);counts['absent']+=1;continue
            partial_passed=not inventory_failed;counts['partial_procedural_cut_rollback_checked'if partial_passed else'partial_check_failed']+=1
            scope={'scope':'source_disproved_flight_retirement_and_known_HEAD_cut_rollback_only',
                'pass':partial_passed,'retired_stair_parts':21,'retired_derived_rails':65,'retired_cut_fragment':1,
                'whole_profile_status':'unverified','whole_slab_source_checked':False}
            prior=result.get(eid)
            entry={'pass':False,'partial_source_passed':partial_passed,'source':'ARCH1:8/9;ARCH2:1/2;STR:24',
                'coverage_classification':'unverified','source_binding_problems':[]if partial_passed else['Original multi-page flight semantics, exact retirement inventory or causal cap rollback guard failed'],
                'partial_source_review':scope,'stair_roof_source_review':scope,
                'method':'Undo a known procedural HEAD cut caused by a source-disproved extra roof flight; full cap perimeter/Z remain unverified',
                'parser':'tools/check_stair01_roof_source_correction.py:audit','source_record_sha256':sha(q),
                'original_pdf_check':bycheck.get(eid),'sampled_deviation_cm':0,'uncovered_model_trace_cm':0,
                'source_xy_verified':False,'source_outer_XY_verified':False,'source_Z_verified':False,
                'source_complete_body_verified':False,'source_dimensions_verified':False,
                'limit':'Procedural causal rollback and disproved-flight retirement only; no whole slab source_checked, physical Z/material/bearing/rebar or operation acceptance.'}
            if prior:
                entry['partial_source_reviews']=[prior.get('partial_source_review'),scope]
                entry['partial_source_passed']=bool(prior.get('partial_source_passed')and partial_passed)
                entry['source_binding_problems']=prior.get('source_binding_problems',[])+entry['source_binding_problems']
                entry['original_pdf_check']={'opening_review':prior.get('original_pdf_check'),'stair_rollback_review':bycheck.get(eid)}
                entry['source_opening_plan_XY_checked']=prior.get('source_opening_plan_XY_checked',False)
            result[eid]=entry
        for checked in retire_checks:
            eid=checked.get('id')
            if eid not in elements:continue
            result[eid]={'pass':False,'source':'ARCH1:8/9;ARCH2:1/2;STR:24',
                'coverage_classification':'unverified','method':'Source-disproved roof stair or derived rail/cut fragment remains in the model',
                'source_binding_problems':checked.get('errors',[]),'original_pdf_check':checked,
                'source_xy_verified':False,'source_Z_verified':False,'source_complete_body_verified':False,
                'limit':'Exact source retirement must pass; retained false geometry is not a derived or literal source component.'}
        inventories['stair01_roof_source_correction']={'expected_controlled_caps':2,'expected_retirements':87,
            'counts':dict(counts),'missing':missing,'source_review_sha256':sha(stair_roof),
            'original_pdf_summary':summary,'global_findings':globals_,'retirement_checks':retire_checks,'source_facts':facts,
            'source_inventory_complete':not inventory_failed and not missing,
            'whole_cap_source_checked_promoted':0,
            'limit':'Known procedural-cut rollback is partial provenance, not literal whole-cap XY/Z or physical structural acceptance.'}
    d16=read('d16_source_remaining')
    if d16:
        import check_d16_source_remaining
        d16_audit=check_d16_source_remaining.audit(M)
        records=d16.get('records',{});checks=d16_audit.get('checks',[])
        facts=d16_audit.get('source_facts',[]);summary=d16_audit.get('summary',{})
        globals_=d16_audit.get('global_findings',[])
        expected={f'A.door-G-D16{n:04d}'for n in range(1,5)}
        bycheck={q.get('id'):q for q in checks}
        inventory_failed=bool(globals_ or summary.get('findings')or summary.get('uncovered'))
        inventory_failed=inventory_failed or set(records)!=expected or set(bycheck)!=expected or len(checks)!=4
        inventory_failed=inventory_failed or {q.get('source_page')for q in facts}!=set(d16.get('source_pages',{}))or len(facts)!=3
        inventory_failed=inventory_failed or any(q.get('pass')is not True or q.get('errors')for q in checks)
        inventory_failed=inventory_failed or summary.get('numeric_physical_part_dimensions_checked')!=0 or summary.get('absolute_Z_installed_material_acceptance')is not False
        inventory_failed=inventory_failed or any(q.get('numeric_physical_part_dimensions_checked')is not False or q.get('absolute_Z_installed_material_acceptance')is not False for q in checks)
        inventory_failed=inventory_failed or any(q.get('whole_physical_body_or_Z_accepted')is not False for q in facts)
        counts=collections.Counter();missing=[]
        for eid,q in records.items():
            if eid not in elements:missing.append(eid);counts['absent']+=1;continue
            checked=bycheck.get(eid);passed=bool(checked and checked.get('pass')and not inventory_failed)
            counts['source_plan_graphic_polygon_passed'if passed else'unverified']+=1
            result[eid]={'pass':passed,'coverage_classification':'source_checked'if passed else'unverified',
                'source':'ARCH1:5','method':'Fresh original A102 D16 open leaf or outer jamb closed polygon; separate A604/BOQ literal facts',
                'sampled_deviation_cm':(checked or{}).get('deviation_cm',0),'uncovered_model_trace_cm':0,
                'original_pdf_check':checked,'source_record_sha256':sha(q),'parser':'tools/check_d16_source_remaining.py:audit',
                'source_binding_problems':[]if passed else['Original D16 graphic/facts/inventory or scope guard failed'],
                'source_xy_verified':passed,'source_graphic_polygon_extent_checked':passed,
                'source_Z_verified':False,'source_complete_body_verified':False,'source_dimensions_verified':False,
                'source_material_class_literal_only':'Galvanized steel','source_installed_material_verified':False,
                'limit':'Four original plan graphic polygons only. 125cm opening/110cm height and conditional +0.20m landing envelope do not prove individual leaf/jamb physical sizes, absolute installed Z, material grade/gauge/product, rating resolution, colour, mount, ports or operation; source conflicts remain explicit.'}
        inventories['d16_source_remaining']={'expected_source_plan_graphic_polygons':4,'expected_source_page_facts':3,
            'counts':dict(counts),'missing':missing,'source_review_sha256':sha(d16),'original_pdf_summary':summary,
            'source_facts':facts,'global_findings':globals_,'source_inventory_complete':not inventory_failed and not missing,
            'numeric_physical_part_dimensions_checked':0,'absolute_Z_installed_material_acceptance':False,
            'literal_source_conflicts':d16.get('confirmed_literal_source_conflicts',[]),
            'limit':'Source plan proxy polygons and separately scoped literal facts; no complete door or installed material/operation acceptance.'}
    mixed=read('water_supply_mixed_corrections')
    if mixed and M.get('meta',{}).get('water_supply_mixed_corrections'):
        counts=collections.Counter();missing=[]
        expected=[q['id']for q in mixed.get('restore_records',[])]
        expected.extend('P.cold-'+q['level']+'-WST'+str(n).zfill(4)
            for n,q in enumerate([q for q in mixed.get('restore_records',[])for _ in q['parts'][1:]],1))
        for eid in expected:
            e=elements.get(eid)
            if e is None:missing.append(eid);counts['absent']+=1;continue
            checked=gate.water_source_check(e);passed=geometric_pass(checked)
            counts['literal_part_passed'if passed else'unverified']+=1
            result[eid]={'pass':passed,'source':checked.get('reference')if checked else(e.get('a')or{}).get('source_page'),
                'method':'Original unique open CW straight vertices with break/device strokes removed; disconnected source parts kept separate',
                'sampled_deviation_cm':checked.get('deviation_cm',0)if checked else 0,'uncovered_model_trace_cm':0,
                'original_pdf_check':checked,'source_review_sha256':sha(mixed),'parser':'tools/check_drawn_positions.py:water_source_check',
                'binding_problem':None if checked else'Current WST raw primitive/vertex selection/identity/registration differs',
                'source_xy_verified':passed,'source_Z_verified':False,'source_complete_body_verified':False,
                'limit':'Literal selected XY only; diameter/Z/material/ports/body/support/operation remain independently unverified. Disconnected lines are not joined by this review.'}
        retirement_checks,dash_checks=gate.water_mixed_source_checks(M,tolerance)
        dash_by={q['id']:q for q in dash_checks}
        for q in mixed.get('review_records',[]):
            eid=q['id'];e=elements.get(eid)
            if e is None:missing.append(eid);counts['absent']+=1;continue
            if q['status']=='whole_open_linear_trace_within_0.2cm':
                checked=gate.water_mixed_review_check(e,tolerance)
                passed=bool(checked and all(checked.get(k)is not None and checked[k]<=tolerance
                    for k in('deviation_cm','source_anchor_deviation_cm','source_transform_deviation_cm'))
                    and checked.get('whole_trace_source_covered')and checked.get('review_geometry_unchanged'))
                counts['whole_open_line_passed'if passed else'unverified']+=1
                result[eid]={'pass':passed,'source':q['source'],'method':'Original open linear water strokes only; closed device glyphs and S curves excluded',
                    'sampled_deviation_cm':checked.get('deviation_cm',0)if checked else 0,'uncovered_model_trace_cm':0,
                    'original_pdf_check':checked,'source_record_sha256':sha(q),'parser':'tools/check_drawn_positions.py:water_mixed_review_check',
                    'binding_problem':None if checked else'Current review identity/open-line primitive binding/geometry hash differs',
                    'source_xy_verified':passed,'source_Z_verified':False,'source_complete_body_verified':False,
                    'limit':'Whole XY trace in original open linework within0.2cm. Device body, diameter/Z/material/ports/hydraulic continuity and operation are separate.'}
            else:
                checked=dash_by.get(eid);passed=bool(checked and checked.get('pass'))
                counts['derived_dash_rule_passed'if passed else'unverified']+=1
                result[eid]={'pass':False,'source':q['source'],'coverage_classification':'derived'if passed else'unverified',
                    'method':'Raw HW dash strokes with independently read legend and turn/crossing rule; continuation between dashes remains derived',
                    'source_review_status':q['status'],'source_binding_problems':[]if passed else['Raw dash/legend/turn rule or geometry binding failed'],
                    'original_pdf_check':checked,'source_record_sha256':sha(q),'parser':'tools/check_drawn_positions.py:water_mixed_source_checks',
                    'source_xy_verified':False,'source_raw_dash_parts_checked':passed,'whole_literal_route_verified':False,
                    'source_Z_verified':False,'source_complete_body_verified':False,
                    'limit':'Dashed source linetype supports the water medium and rule-scoped turns/crossings; full continuous geometry and hydraulic connection remain derived.'}
        inventories['water_mixed_corrections']={'expected_literal_parts':len(expected),'expected_review_routes':len(mixed.get('review_records',[])),
            'counts':dict(counts),'missing':missing,'source_review_sha256':sha(mixed),'source_summary':mixed.get('summary',{}),
            'retirement_checks':retirement_checks,'retirement_findings':[q for q in retirement_checks if not q.get('pass')],
            'limit':'Independent literal XY/open-line checks, derived dash-rule checks and nonpipe retirement checks remain separate; no whole physical or operational acceptance.'}
    meters=read('water_meter_source_remaining')
    if meters and M.get('meta',{}).get('water_meter_source_remaining'):
        counts=collections.Counter();missing=[]
        for q in meters.get('meter_markers',[]):
            eid=q['id'];e=elements.get(eid)
            if e is None:missing.append(eid);counts['absent']+=1;continue
            checked=gate.water_meter_source_check(e);passed=geometric_pass(checked)
            counts['graphic_anchor_passed'if passed else'unverified']+=1
            result[eid]={'pass':passed,'source':q['source_page'],
                'method':'Original circle M centre, actual M character and WATER METER key; graphic presence only',
                'sampled_deviation_cm':checked.get('deviation_cm',0)if checked else 0,'uncovered_model_trace_cm':0,
                'original_pdf_check':checked,'source_record_sha256':sha(q),'parser':'tools/check_drawn_positions.py:water_meter_source_check',
                'binding_problem':None if checked else'Water meter circle/M/key/source identity differs',
                'source_xy_verified':passed,'source_Z_verified':False,'source_complete_body_verified':False,
                'limit':'Graphic presence/centre only; drawn circle radius is not physical meter diameter. Body dimensions/Z/material/finish/mounting/ports/hydraulic contact remain unverified.'}
        retirement_checks=gate.water_meter_source_checks(M,tolerance)
        inventories['water_meter_source_remaining']={'expected':len(meters.get('meter_markers',[])),
            'counts':dict(counts),'missing':missing,'source_review_sha256':sha(meters),
            'retirement_checks':retirement_checks,'retirement_findings':[q for q in retirement_checks if not q.get('pass')],
            'limit':'Original circle M anchors and separate nonmeter retirement/washer-presence proofs only; no physical body or operation acceptance.'}
    raft=read('raft_source_restore')
    if raft:
        import check_raft_source
        checked_raft=check_raft_source.audit(M);counts=collections.Counter()
        global_errors=[q for q in checked_raft.get('findings',[])if not q.get('id')]
        for checked in checked_raft.get('checks',[]):
            eid=checked['id'];q=raft['records'][eid]
            passed=not checked.get('errors')and not global_errors
            original=checked.get('proof_scope')=='original_closed_PC1_profile'
            counts['source_profile_passed'if passed and original else'derived_domain_passed'if passed else'unverified']+=1
            result[eid]={'pass':passed and original,'source':'STR:11',
                'coverage_classification':'source_checked'if passed and original else'derived'if passed else'unverified',
                'method':'Original complete closed PC1 outline'if original else'Boolean raft domain from original outer minus original PC1',
                'sampled_deviation_cm':checked.get('xy_deviation_cm',0),'uncovered_model_trace_cm':0,
                'original_pdf_check':checked,'source_record_sha256':sha(q),'parser':'tools/check_raft_source.py:audit',
                'source_binding_problems':checked.get('errors',[]),'source_xy_verified':passed and original,
                'source_derived_boundary_xy_checked':passed and not original,'source_Z_verified':False,
                'source_complete_body_verified':False,'source_thickness_literal_cm':q['thickness_cm'],
                'limit':'Controlled XY correction from original STR11 operators and literal80/150cm thickness. Absolute Z, material, reinforcement, bearing and site acceptance remain unverified; raft80 domain is derived.'}
        counts['absent']+=len(checked_raft.get('uncovered',[]))
        inventories['raft_source_restore']={'expected':2,'counts':dict(counts),'missing':checked_raft.get('uncovered',[]),
            'source_review_sha256':sha(raft),'original_pdf_summary':checked_raft.get('summary',{}),
            'global_binding_errors':global_errors,'status':'One original PC1 profile and one derived outer-minus-PC1 domain; real source corrections, not representation-only repairs'}
    windows=read('window_source_xy')
    if windows:
        import check_window_source
        checked_windows=check_window_source.audit(M)
        by_group={q['id']:q for q in checked_windows.get('checks',[])}
        expected_window_ids={eid for q in windows.get('units',{}).values()for eid in q.get('model_member_ids',[])}
        missing=sorted(expected_window_ids-set(elements));counts=collections.Counter({'absent':len(missing)})
        for q in checked_windows.get('derived',[]):
            eid=q['id'];group=q['source_group'];checked=by_group.get(group)
            if eid not in elements:missing.append(eid);counts['absent']+=1;continue
            passed=bool(checked and checked.get('pass')and not checked.get('errors'))
            counts['derived_assembly_part_with_checked_anchor'if passed else'unverified']+=1
            source=checked.get('reference')if checked else windows.get('units',{}).get(group,{}).get('source_page')
            result[eid]={'pass':False,'source':source,
                'coverage_classification':'derived'if passed else'unverified',
                'method':'Derived window member; original closed profile/glazing-plane anchor and literal relative envelope checked for its assembly',
                'source_review_status':'derived_window_assembly_part','source_window_group':group,
                'source_binding_problems':[]if passed else(list((checked or{}).get('errors',[]))or['Current window assembly/group binding missing']),
                'original_pdf_check':checked,
                'source_record_sha256':windows.get('units',{}).get(group,{}).get('source_record_sha256'),
                'parser':'tools/check_window_source.py:audit',
                'source_xy_verified':False,'source_assembly_anchor_xy_checked':passed,
                'source_relative_envelope_checked':passed,'source_Z_verified':False,
                'source_complete_body_verified':False,'source_frame_depth_material_mounting_verified':False,
                'limit':'111 group anchors and relative schedule envelopes are checked independently. Each of2776 procedural members remains derived; no individual part geometry, absolute Z, frame depth/material, finish/color, mounting or operation is accepted.'}
        inventories['window_source_xy']={'expected_group_anchors':len(windows.get('units',{})),
            'expected_derived_members':sum(len(q.get('model_member_ids',[]))for q in windows.get('units',{}).values()),
            'counts':dict(counts),'missing':missing,'source_review_sha256':sha(windows),
            'original_pdf_summary':checked_windows.get('summary',{}),
            'assembly_checks':checked_windows.get('checks',[]),'schedule_checks':checked_windows.get('schedule_checks',[]),
            'limit':'An assembly-level raw anchor check never promotes all procedural parts to source_checked; absolute Z and physical frame/material/mounting remain outside this gate.'}
    if M.get('meta', {}).get('core_stairs_source_surfaces'):
        import check_core_stairs_source_surfaces as CSF_GATE
        checked = CSF_GATE.audit(M)
        valid = checked.get('summary', {}).get('findings') == 0 and checked.get('summary', {}).get('uncovered') == 0
        for q in checked.get('checks', []):
            passed = valid and not q.get('errors')
            result[q['id']] = {'pass': False, 'coverage_classification': 'derived' if passed else 'unverified',
                'source': 'ARCH1:6–8 / ARCH2:1–4', 'method': 'Finished stair surfaces compiled from original nosings and literal flight datums',
                'source_binding_problems': [] if passed else q.get('errors', []) or ['Finished stair source binding failed'],
                'original_pdf_check': q, 'parser': 'tools/check_core_stairs_source_surfaces.py:audit',
                'source_input_XY_checked': passed, 'source_finished_surface_Z_checked': passed,
                'source_complete_body_verified': False,
                'limit': 'Interpolated treads, risers and landing surfaces remain derived assemblies; no solid concrete waist, thickness, material, bearing, reinforcement or physical acceptance.'}
        inventories['core_stairs_source_surfaces'] = checked
    return result,inventories


def audit(M, drawn_report=None, raw_ws=False, raw_elec=False, raw_drain=True, raw_hvac=True, raw_etr=True, raw_new_components=True):
    # Rehydrate external audit inputs; geometry remains the live model.
    import sys as _audit_sys
    from pathlib import Path as _AuditPath
    _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
    from source_audit_sidecar import audit_model as _source_audit_model
    M = _source_audit_model(M)
    before = sha([[e['id'],e['g']] for e in M['els']])
    bindings = archived_bindings(M); rows, details, missing = [], {}, []
    electrical_review=read('electrical_source_restore')
    semantic_reviews={r['id']:r for r in electrical_review.get('semantic_review',[])}
    geometry_digest = hashlib.sha256(json.dumps(sorted((e['id'],e['g']) for e in M['els']),separators=(',', ':')).encode()).hexdigest()
    gate_bound = bool(drawn_report and drawn_report.get('model_geometry_sha256') == geometry_digest)
    gates = {q['id']:q for q in (drawn_report or {}).get('checks', [])} if gate_bound else {}
    gate_derived = {q['id']:q for q in (drawn_report or {}).get('derived', [])} if gate_bound else {}
    raw, raw_missing, raw_inventory = raw_water_supply(M) if raw_ws else ({},[],[])
    electrical, electrical_inventory = raw_electrical(M,bindings) if raw_elec else ({},[])
    raw.update(electrical)
    drain,drain_inventory=raw_drain_sources(M) if raw_drain else ({},{})
    raw.update(drain)
    hvac,hvac_inventory=raw_hvac_sources(M) if raw_hvac else ({},{})
    raw.update(hvac)
    tails,tail_inventory=raw_electrical_tail_sources(M)if raw_etr else({}, {})
    raw.update(tails)
    new_components,new_inventory=raw_new_component_sources(M)if raw_new_components else({}, {})
    raw.update(new_components)
    missing.extend(raw_missing)
    counts = collections.Counter(); family_counts = collections.defaultdict(collections.Counter); height_counts=collections.Counter()
    for e in M['els']:
        a=e.get('a') or {}; t=M.get('types',{}).get(e.get('t'),{}); refs=references(M,e)
        sheets=list(dict.fromkeys(k.upper()+':'+p for r in refs for k,p in PAGE_RE.findall(r)))
        source=', '.join(sheets[:5]) or (refs[0][:120] if refs else '')
        status, basis, findings = 'unverified', 'No independent geometric source binding', []
        proof={}; suffix=GEN.search(e['id']); suffix=suffix.group(1) if suffix else None
        if a.get('connector') or a.get('bridge') or suffix in ('K','V','X','ARF') or e['id'] in gate_derived or a.get('source_kind') in ('derived_from_outline','derived_from_model_face','derived_from_section'):
            status,basis='derived','Geometry assembled or inferred from documented inputs; independent piece position not claimed'
        elif t.get('cf')=='derived': status,basis='derived','Type is explicitly derived; its anchor may still have drawing evidence'
        g=gates.get(e['id'])
        if g:
            proof['position_gate']=g
            if g.get('pass'):
                independent=all(g.get(k) is not None for k in ('source_anchor_deviation_cm','source_transform_deviation_cm'))
                status='source_checked' if independent else 'legacy_extract_match'
                basis=g.get('method','Independent XY gate')
            else:
                status='unverified';basis=g.get('method');findings.append('Independent XY gate failed; deviation='+str(g.get('deviation_cm'))+' cm')
        b=bindings.get(e['id'])
        if b:
            proof['archived_record']={k:v for k,v in b.items() if k not in ('geometry','anchor')}
            if 'geometry' in b:
                p,q=plan(e['g']),plan(b['geometry']);delta=p.hausdorff_distance(q) if p is not None and q is not None else None
                semantic=e.get('t')==b.get('type')
            else:
                delta=math.dist(xy(e['g']),b['anchor']) if xy(e['g']) else None;semantic=e.get('t')==b.get('type')
            proof['archived_record'].update(xy_deviation_cm=delta,type_matches=semantic)
            if status not in ('source_checked','derived') and delta is not None and delta<=TOL and semantic:
                status,basis='legacy_extract_match','Deterministic identity matches archived extraction XY; original PDF primitive/semantics not bound'
            elif status=='unverified' and delta is not None and delta>TOL:
                findings.append('Archived anchor differs %.3f cm; bounding-box/face/source corrections require review, not automatic relocation'%delta)
        rr=raw.get(e['id'])
        if rr:
            proof['raw_pdf']=rr
            if rr.get('coverage_classification'):
                status,basis=rr['coverage_classification'],rr['method']
                source=rr['source']
                if rr['source_binding_problems']:
                    findings.extend(rr['source_binding_problems'])
                if rr.get('source_review_status')=='derived_vertical_riser':
                    basis='Interlevel riser derived from model endpoints; nearby plan primitives do not prove its complete geometry'
                    findings.append(rr['limit'])
                elif rr.get('source_review_status')=='derived_bridge_through_source_symbols':
                    basis='Mixed drawn/derived trace through gaps in source symbols; full source route and connection remain unproved'
                    findings.append(rr['limit'])
                elif rr.get('source_review_status')=='arc_glyph_composition_pending':
                    basis='Historical composition of arcs/glyph linework requires a unique source route and semantic proof'
                    findings.append(rr['limit'])
            elif rr.get('isolated_symbol_size_match') is False:
                status,basis='unverified','Compound PDF linework cluster is not independently proven to be one device'
                findings.append('Original classifier disabled symbol size filtering; cluster dimensions disagree with its legend exemplar or no exemplar exists')
            elif rr['pass']:
                status,basis='source_checked',rr['method']
            elif rr.get('failure_kind')=='interpolated_source_gap_requires_semantic_review':
                status,basis='derived','Source vertices match; historical extractor joined an untraced span between drawn fragments'
                findings.append('Mixed drawn/derived trace: gaps '+str([round(v,3) for v in rr['uncovered_spans_cm']])+' cm require symbol/route review; no physical XY displacement or accepted connection inferred')
            else:
                status,basis='unverified',rr['method'];findings.append('Actual PDF trace check failed: %.3f cm sampled deviation; %.3f cm outside existing threshold'%(rr.get('sampled_deviation_cm',0),rr.get('uncovered_model_trace_cm',0)))
            if rr.get('binding_problem'):findings.append(rr['binding_problem'])
        sr=semantic_reviews.get(e['id'])
        if sr and not a.get('source_semantics_checked'):
            proof['symbol_semantic_review']=sr
            status='unverified';basis='Historical raster cluster is not independently proven to be one physical device'
            findings.append('Source cluster dimensions disagree with its class legend exemplar or no exemplar exists; primitive decomposition and class proof required')
        z_basis,z_notes=height_basis(M,e,refs);height_counts[z_basis]+=1
        if a.get('unsupported'):findings.append('No proven existing support body; geometry retained')
        if a.get('network_gap'):findings.append('Network connection remains unspecified or not modelled')
        if a.get('drawing_conflict'):findings.append(str(a['drawing_conflict']))
        row={'id':e['id'],'status':status,'xy_basis':basis,'z_basis':z_basis,'source':source,'findings':findings}
        rows.append(row);counts[status]+=1;family_counts[e['c'].split('.')[0]][status]+=1
        details[e['id']]={'category':e['c'],'type':e.get('t'),'level':e['l'],'geometry_kind':e['g'][0], 'xy_cm':xy(e['g']), 'z_m':z_range(e['g']),
                          'source_refs':refs,'height_assumptions':z_notes,'evidence':proof,
                          'needs_original_xy_proof':status in ('unverified','legacy_extract_match'),
                          'needs_height_proof':True,'needs_dimension_semantic_review':True}
    # Missing archived identities remain extraction-record candidates, not new geometry.
    ids={e['id'] for e in M['els']};corrected=M.get('meta',{}).get('drawing_corrections',{})
    outlet_inventory=new_inventory.get('hvac_outlets_source_restore',{})
    source_retired={q['id']for q in outlet_inventory.get('retirement_checks',[])if q.get('pass')and not q.get('errors')}
    for family,key in [('hvac_outlet','hvac_outlets_source_restore'),('hvac_damper','hvac_damper_source')]:
        for eid in new_inventory.get(key,{}).get('missing',[]):
            missing.append({'id':eid,'status':'literal_graphic_source_identity_absent','source_family':family,
                'source_file':key+'.json','reason':'A deterministic qualified source graphic identity is absent. Source anchor/graphic semantics must pass before rebuilding; physical body/Z/ports are not inferred.'})
    for eid,b in bindings.items():
        if eid in ids or eid in corrected or eid in source_retired or b['file']=='els_struct.json':continue
        if b['file']=='elec_inst.json' and b.get('type') in ('e_T18','e_T19','e_T20','e_G1','e_G2','e_G3','e_G4'):continue
        missing.append({'id':eid,'status':'archived_record_without_model_identity','source_file':b['file'],'record':b['record'],'source':b.get('source',[]),
                        'source_xy_cm':b.get('anchor') or xy(b['geometry']),'reason':'Record has no deterministic model identity; removals/corrections/source semantics must be checked before treating it as a missing component'})
    assert before == sha([[e['id'],e['g']] for e in M['els']])
    return {'rows':rows,'counts':dict(counts),'by_family':{k:dict(v) for k,v in family_counts.items()},'height_counts':dict(height_counts),'missing_components':missing,
            'unchecked_reason':'Citations/type labels do not bind geometry to a PDF primitive. The owner requires literal original-source authority; archive consistency does not authorize design, position, height, material, finish or color.',
            'classification_limits':['source_checked means independent XY evidence only; no global component acceptance or material/finish/color/Z proof','legacy_extract_match is historical consistency only and has no design authority; no geometry, material or color may be adopted from the old file','derived is an explicit model inference/assembly, not an independently traced piece or literal source approval','A missing extraction identity or heater-sized raw cluster is a review candidate until source semantics are confirmed','Operation, dimensions, Z and completeness of all PDF pages are not certified by this tool','CAD stroke/fill color is graphic symbol evidence, not physical paint or RAL; physical material/finish/color needs its own literal source record'],
            'model_elements':len(M['els']),'model_geometry_sha256':geometry_digest,'geometry_preserved':True,'drawn_gate_snapshot_bound':gate_bound,
            'drawn_gate_unbound_reason':None if gate_bound else 'Saved position report lacks/mismatches the current geometry digest; its counts are not promoted',
            'raw_water_supply_source_inventory':raw_inventory,'raw_electrical_source_inventory':electrical_inventory,
            'raw_drain_source_inventory':drain_inventory,'raw_hvac_source_inventory':hvac_inventory,'raw_electrical_tail_source_inventory':tail_inventory,'raw_new_component_source_inventory':new_inventory,'details':details}


def compact(report, external_report='pipeline/data/component_coverage.json'):
    """Viewer summary; all per-component evidence remains in the full report.

    Ordinary rows use the status map and the model's own source/assumption card.
    Explicit findings remain visible as rows. Repeated methodological paragraphs
    and raw primitive arrays are deliberately kept outside the standalone HTML.
    """
    rows=[]
    for r in report['rows']:
        if not r['findings']:continue
        rows.append({k:r[k] for k in ('id','status','xy_basis','z_basis','source','findings')})
    return {'counts':report['counts'],'by_family':report['by_family'],'height_counts':report['height_counts'],
            'model_elements':report['model_elements'],'model_geometry_sha256':report['model_geometry_sha256'],
            'status_by_id':{r['id']:r['status'] for r in report['rows']},'rows':rows,
            'missing_components':report['missing_components'],
            'unchecked_reason':report['unchecked_reason'],'classification_limits':report['classification_limits'],
            'external_report':external_report,'external_report_sha256':sha(report),
            'full_evidence_external':True,'geometry_preserved':report['geometry_preserved']}


def apply_incremental(M, baseM, base_report, source_audit):
    """Reuse unchanged source bindings and refresh only the bounded source batch.

    The caller supplies the fresh source audit. Every unrelated component must
    survive exactly; this does not repeat the complete PDF audit.
    """
    import core_stairs_source_surfaces as CSF
    d = CSF.data()
    old = {e['id']: e for e in baseM['els']}
    new = {e['id']: e for e in M['els']}
    owned = set(d['before_records'])
    after = CSF.compile_after(d)
    heaters = {e['id'] for e in baseM['els'] if e['c'] == 'P.heater'}
    assert len(old) == len(baseM['els']) and len(new) == len(M['els'])
    assert set(old) - set(new) == set(d['exactretired_ids'])
    assert not (set(new) - set(old))
    base_digest = hashlib.sha256(json.dumps(sorted((e['id'], e['g']) for e in baseM['els']), separators=(',', ':')).encode()).hexdigest()
    assert base_report['model_geometry_sha256'] == base_digest, 'Incremental CC base is not bound to the before model'
    assert {r['id'] for r in base_report['rows']} == set(old)
    for eid in set(old) - owned - heaters:
        assert old[eid] == new[eid], 'Unrelated component changed: ' + eid
    for eid in heaters:
        assert all(old[eid].get(k) == new[eid].get(k) for k in ('id', 'c', 'l', 'm', 'g', 's', 'q')), 'Heater body or position changed'
    assert source_audit.get('summary', {}).get('findings') == 0
    assert source_audit.get('summary', {}).get('uncovered') == 0
    checks = {q['id']: q for q in source_audit['checks']}
    assert set(checks) == set(after) and all(not q['errors'] for q in checks.values())
    report = copy.deepcopy(base_report)
    rows = {r['id']: r for r in report['rows']}
    for eid in owned:
        rows.pop(eid, None)
        report['details'].pop(eid, None)
    for eid in heaters:
        report['details'][eid]['type'] = new[eid]['t']
        report['details'][eid]['evidence']['heater_capacity_property'] = copy.deepcopy(new[eid]['a']['source_heater_capacity_review'])
    for eid, expected in after.items():
        e = new[eid]
        assert CSF.signature(e) == CSF.signature(expected)
        refs = references(M, e)
        z_basis, z_notes = height_basis(M, e, refs)
        rows[eid] = {'id': eid, 'status': 'derived',
            'xy_basis': 'أسطح درج مشتقة من نوسينغ المخطط الأصلي؛ مدخلات المصدر مفحوصة ضمن المجموعة',
            'z_basis': z_basis, 'source': ' / '.join(refs),
            'findings': ['تم استبدال الجسم الإجرائي الخاطئ بأسطح النائمات والقوائم والبسطات؛ سمك وبطن الخرسانة والتسليح والارتكاز والمادة غير معتمدة']}
        report['details'][eid] = {'category': e['c'], 'type': e['t'], 'level': e['l'], 'geometry_kind': 'mesh',
            'xy_cm': xy(e['g']), 'z_m': z_range(e['g']), 'source_refs': refs, 'height_assumptions': z_notes,
            'evidence': {'source_surface_audit': checks[eid]}, 'needs_original_xy_proof': False,
            'needs_height_proof': True, 'needs_dimension_semantic_review': True,
            'input_nosing_and_datum_checked': True, 'whole_structural_body_source_accepted': False}
    report['rows'] = [rows[e['id']] for e in M['els']]
    families = collections.defaultdict(collections.Counter)
    for r in report['rows']:
        families[new[r['id']]['c'].split('.')[0]][r['status']] += 1
    report['counts'] = dict(collections.Counter(r['status'] for r in report['rows']))
    report['by_family'] = {k: dict(v) for k, v in families.items()}
    report['height_counts'] = dict(collections.Counter(r['z_basis'] for r in report['rows']))
    report['model_elements'] = len(M['els'])
    report['model_geometry_sha256'] = hashlib.sha256(json.dumps(sorted((e['id'], e['g']) for e in M['els']), separators=(',', ':')).encode()).hexdigest()
    report['drawn_gate_snapshot_bound'] = False
    report['drawn_gate_unbound_reason'] = 'Incremental source batch; unchanged bindings reused by exact component preservation, new surface inputs checked in a scoped audit'
    report['raw_new_component_source_inventory']['core_stairs_source_surfaces'] = source_audit
    report['incremental_source_batch'] = {'base_report_sha256': sha(base_report), 'base_geometry_sha256': base_digest,
        'reused_unchanged_body_rows': len(set(old) - owned), 'heater_property_rows_refreshed': len(heaters),
        'replaced_old_stair_rows': len(owned), 'new_derived_surface_assemblies': len(after),
        'retired_ids': d['exactretired_ids'], 'whole_new_body_source_checked_promoted': 0,
        'reason_ar': 'بتوجيه المستخدم: تصحيح المتأثر ونسخ المتشابه؛ لا تكرار البناء أو فحص المخططات الشامل.'}
    M['componentReview'] = compact(report)
    return report


def apply(M, drawn_report=None, raw_ws=False, raw_elec=False, external_path=None, raw_drain=True, raw_hvac=True, raw_etr=True, raw_new_components=True):
    """Integrate a review of this exact in-memory model after final repair.

    Pass a freshly computed independent gate report from the same M; do not read
    a preceding src/model.json snapshot. Only the review key is added to M.
    """
    if not drawn_report or not drawn_report.get('model_geometry_sha256'):
        import check_drawn_positions as gate
        drawn_report=gate.audit(M)
        drawn_report['model_geometry_sha256']=hashlib.sha256(json.dumps(sorted((e['id'],e['g']) for e in M['els']),separators=(',', ':')).encode()).hexdigest()
    report=audit(M,drawn_report,raw_ws,raw_elec,raw_drain,raw_hvac,raw_etr,raw_new_components)
    report['model_path']='current in-memory post-process model'
    if external_path is None:external_path=os.path.join(DATA,'component_coverage.json')
    os.makedirs(os.path.dirname(os.path.abspath(external_path)),exist_ok=True)
    json.dump(report,open(external_path,'w',encoding='utf-8'),ensure_ascii=False,separators=(',',':'))
    ref=os.path.relpath(external_path,ROOT) if os.path.commonpath([os.path.abspath(external_path),ROOT])==ROOT else os.path.abspath(external_path)
    M['componentReview']=compact(report,ref)
    return report


def source_gap_inventory(M, report=None):
    """Index the existing page/identity gaps without rerunning or changing gates.

    A source citation is only a pointer. This result never treats the absence of
    a reference, a retired extraction ID, or a PDF hatch stroke as a missing body.
    """
    report = report if report is not None else read('component_coverage')
    index = read('sheet_index')
    pages = {(book, r['page']): r for book, rows in index.items() for r in rows}
    source_files = {'ARCH1': 'Arch. Drawings Part I (1).pdf', 'ARCH2': 'Arch. Drawings Part II.pdf',
                    'STR': 'Structure Drawings (1).pdf', 'MECH1': 'Mechanical Drawings Part I (1).pdf',
                    'MECH2': 'Mechanical Drawings Part II (1).pdf', 'ELEC1': 'Electrical Drawings Part I (1).pdf',
                    'ELEC2': 'Electrical Drawings Part II (1).pdf'}
    books_by_file = {name: book for book, name in source_files.items()}
    pattern = re.compile(r'\b(ARCH[12]|STR|MECH[12]|ELEC[12])\s*(?::|p\s*|ص\s*)\s*(\d+)(?:\s*[–−-]\s*(\d+))?', re.I)
    def references_in(text):
        for book, start, end in pattern.findall(str(text)):
            for page in range(int(start), min(int(end or start), int(start)+60)+1):
                key = (book.upper(), page)
                if key in pages:
                    yield key
    candidates = report.get('missing_components', [])
    wanted = {r['id'] for r in candidates}
    live = {e['id'] for e in M['els']}
    restored = collections.defaultdict(list)
    for e in M['els']:
        alias = (e.get('a') or {}).get('archive_candidate')
        if alias and not (e.get('a') or {}).get('alt'):
            restored[alias].append(e['id'])
    detail_index = Path(DATA) / 'source_details' / 'INDEX.json'
    detail_rows = json.loads(detail_index.read_text()) if detail_index.is_file() else []
    excluded_candidates = {q['id']: q for row in detail_rows for q in row.get('excluded_archive_candidates', [])}
    value_refs = collections.defaultdict(set)
    key_refs = collections.defaultdict(set)
    identity_refs = collections.defaultdict(list)
    excluded = {'component_coverage.json', 'coordination_review.json', 'source_audit_attributes.json', 'source_conflict_evidence.json',
                'sheet_index.json', 'remaining_review.json', 'model_matching.json'}
    ledger_paths = list(Path(DATA).glob('*.json')) + list((Path(DATA) / 'source_details').glob('*.json'))
    for path in sorted(ledger_paths):
        if path.name in excluded or 'proof' in path.name or 'audit' in path.name:
            continue
        data = json.loads(path.read_text())
        stack = [(data, '$', None)]
        while stack:
            value, pointer, parent = stack.pop()
            if isinstance(value, str):
                for key in references_in(value):
                    value_refs[key].add(path.name)
                if value in wanted:
                    context = parent if isinstance(parent, dict) else {}
                    notes = {k: context[k] for k in ('action', 'reason_ar', 'reason', 'status', 'source', 'interpretation_ar')
                             if isinstance(context.get(k), (str, int, float, bool))}
                    identity_refs[value].append({'file': path.name, 'record': pointer, **notes})
            elif isinstance(value, list):
                stack.extend((q, pointer+'['+str(i)+']', parent) for i, q in enumerate(value))
            elif isinstance(value, dict):
                book = value.get('set') or value.get('book') or value.get('source_set') or value.get('file_key') or books_by_file.get(value.get('file'))
                page = value.get('page') or value.get('source_page')
                if isinstance(book, str) and isinstance(page, int) and (book, page) in pages:
                    value_refs[(book, page)].add(path.name)
                for key, child in value.items():
                    child_pointer = pointer+'/'+str(key)
                    if not path.name.startswith('reg_'):
                        for page_key in references_in(key):
                            key_refs[page_key].add(path.name+':'+child_pointer)
                    if key in wanted:
                        notes = {k: child[k] for k in ('action', 'reason_ar', 'reason', 'status', 'source', 'interpretation_ar')
                                 if isinstance(child, dict) and isinstance(child.get(k), (str, int, float, bool))}
                        identity_refs[key].append({'file': path.name, 'record': child_pointer, **notes})
                    stack.append((child, child_pointer, value))
    model_refs = collections.defaultdict(set)
    file_elements = collections.defaultdict(dict)
    unbound_model_ids = []
    for element in M['els']:
        attrs = element.get('a') or {}
        keys = {key for text in references(M, element) for key in references_in(text)}
        alt_source = attrs.get('alt_source') or {}
        if isinstance(alt_source, dict):
            book = alt_source.get('file_key') or books_by_file.get(alt_source.get('file'))
            key = (book, alt_source.get('page'))
            if key in pages:
                keys.add(key)
        elif isinstance(alt_source, str):
            keys.update(key for key in references_in(alt_source) if key in pages)
        if not keys:
            unbound_model_ids.append(element['id'])
        for key in keys:
            model_refs[key].add(element['id'])
            file_elements[key[0]][element['id']] = element
    per_file = []
    for book, rows in index.items():
        elements = list(file_elements[book].values())
        alternatives = [e for e in elements if (e.get('a') or {}).get('alt')]
        per_file.append({'book': book, 'file': source_files[book], 'source_page_count': len(rows),
            'drawn': {'model_element_count': len(elements)-len(alternatives),
                      'label_ar': 'عناصر النموذج المرتبطة بالملف؛ وجودها ليس إثبات اكتمال أجزاء المصدر.'},
            'source_shapes': {'alternative_element_count': len(alternatives),
                'explicit_plan_outline_body_count': sum((e.get('a') or {}).get('geometry_role') == 'extruded_literal_plan_outline' for e in alternatives),
                'source_operator_count': sum((e.get('a') or {}).get('source_operator_count', 0) for e in alternatives),
                'source_segment_count': sum((e.get('a') or {}).get('source_segment_count', 0) for e in alternatives),
                'label_ar': 'تمثيلات بدائل المصدر الحية؛ قد يجمع عنصر واحد عدة ضربات رسم. الضربات ليست أجهزة.'},
            'no_geometry': {'confirmed_page_count': None,
                'reason_ar': 'لم يثبت جرد الأوراق الحالي خلو صفحات كاملة من الهندسة؛ تفاصيل بلا XY جديد لا تعني غياب الأشكال.'},
            'ignored_not_proven': {'unrepresented_part_count': None,
                'pages_without_live_model_reference': [r['page'] for r in rows if not model_refs[(book, r['page'])]],
                'reason_ar': 'عدد الأجزاء غير المرسومة غير مثبت. وجود مرجع أو شكل في صفحة لا يثبت تمثيل بقية أجزائها.'}})
    registry = read('reg_all')
    page_rows = []
    for key, row in pages.items():
        if value_refs[key]:
            continue
        code = 'reference_in_ledger_key' if key_refs[key] else 'cited_page_without_part_inventory' if model_refs[key] else 'page_without_part_inventory'
        reason = ('مرجع الصفحة موجود في مفتاح سجل المصدر؛ لم يلتقطه فهرس القيم النصية.' if key_refs[key] else
                  'توجد عناصر تستشهد بهذه الصفحة، لكن لا جرد حصري لأجزائها في فهرس سجلات المصدر.' if model_refs[key] else
                  'لا ربط لأجزاء هذه الصفحة في الجرد الموجود؛ غياب الربط لا يثبت أنها تحتوي أجسامًا غائبة.')
        if key in (('MECH1', 9), ('MECH1', 10)):
            code = 'nonspatial_detail_duplicate' if key[1] == 10 else 'nonspatial_detail_without_new_xy'
            reason = ('تفاصيل AC-107-B مكررة لصفحة 9 وفق chw_review؛ لا مواقع XY جديدة.' if key[1] == 10 else
                      'تفاصيل دعم وعزل وعبور للتكييف؛ chw_review يسجل أنها لا تحدد مواقع جديدة.')
        page_rows.append({'source_id': key[0]+':'+str(key[1]), 'book': key[0], 'page': key[1],
            'drawing_number': row.get('no'), 'title': row.get('title'), 'reason_code': code, 'reason_ar': reason,
            'resolved_key_references': sorted(key_refs[key]), 'live_citation_element_ids': sorted(model_refs[key]),
            'current_registration': registry.get(key[0]+':'+str(key[1])),
            'unrepresented_part_count': None, 'complete_part_inventory': False})
    absent = []
    resolved = []
    for row in candidates:
        links = identity_refs[row['id']]
        retired = [q for q in links if re.search(r'retire|remove|deleted', q['record'], re.I) or
                   re.match(r'retire|remove|delete', str(q.get('action', '')))]
        filtered = [q for q in links if q['file'] in ('removed_ramp_zone_b.json', 'removed_offplan.json')]
        code = 'documented_retired_identity' if retired else 'archived_identity_without_current_binding'
        reason = ('للهوية سجل إزالة صريح؛ تُراجع دلالة الرسم قبل اعتبارها جسمًا يجب إضافته.' if retired else
                  'هوية استخراج تاريخية غير موجودة في النموذج؛ يلزم ربط السجل برمز المصدر وحسم سبب عدم إصدارها.')
        if not retired and filtered:
            code = 'historical_geometric_filter_removal'
            reason = ('حذف سابق بمرشح نطاق منحدر البدروم؛ هذا سبب تاريخي لا يثبت غياب العنصر من المخطط.'
                      if filtered[0]['file'] == 'removed_ramp_zone_b.json' else
                      'حذف سابق بمرشح خارج نطاق المسقط؛ يلزم فحص موضع الرمز الأصلي قبل الإبقاء على الحذف.')
        if row['id'] in live:
            code, reason = 'identity_now_present', 'الهوية موجودة الآن؛ بند الغياب من تقرير الجرد السابق متقادم.'
        if row['id'] in live or len(restored.get(row['id'], [])) == 1 or row['id'] in excluded_candidates:
            resolved.append({'id': row['id'], 'element_ids': [row['id']] if row['id'] in live else restored.get(row['id'], []),
                             'resolution': excluded_candidates.get(row['id'], {'reason': 'existing_restored_identity'}),
                             'source_approval': False})
            continue
        absent.append({'id': row['id'], 'source_pages': sorted({b+':'+str(p) for text in row.get('source', []) for b, p in references_in(text)}),
            'archive_file': row.get('source_file'), 'archive_record': row.get('record'), 'source_refs': row.get('source', []),
            'reason_code': code, 'reason_ar': reason, 'identity_ledger_links': retired or filtered or links,
            'currently_present': row['id'] in live, 'drawing_required_without_source_review': False})
    groups = collections.defaultdict(list)
    for row in absent:
        for page in row['source_pages']:
            groups[page].append(row['id'])
    return {'schema': 'c4.source-gap-inventory.v1', 'source_pages': len(pages), 'page_review_list': page_rows,
        'per_file': per_file, 'live_alternatives_included': True,
        'model_elements_without_indexed_page': unbound_model_ids,
        'per_file_counts_note_ar': 'الأعداد محسوبة من النموذج الحي، وقد يستشهد العنصر بأكثر من ملف؛ لا تجمع أعداد الملفات كمقام للعناصر.',
        'resolved_archive_candidates': resolved, 'absent_identity_candidates': absent, 'absent_candidates_by_page': dict(sorted(groups.items())),
        'summary': {'page_reference_scan_gaps': len(page_rows), 'resolved_via_ledger_keys': sum(bool(r['resolved_key_references']) for r in page_rows),
                    'resolved_archive_candidates': len(resolved), 'absent_identity_candidates': len(absent), 'candidate_pages': len(groups),
                    'identity_reason_counts': dict(collections.Counter(r['reason_code'] for r in absent))},
        'model_geometry_changed': False, 'source_coverage_not_inferred_from_citations': True}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',default=os.path.join(ROOT,'src','model.json'))
    parser.add_argument('--output',required=True)
    parser.add_argument('--inventory-only', action='store_true', help='List current page-reference and archived-identity gaps from existing ledgers; do not rerun gates')
    parser.add_argument('--refresh-drawn',action='store_true',help='Read-only fresh independent position audit; never overwrites the other tool/report')
    parser.add_argument('--raw-ws',action='store_true',help='Read actual MECH2:18–22 CW/HW/heater PDF primitives')
    parser.add_argument('--raw-electrical',action='store_true',help='Bind legacy electrical identities to actual ordered PDF symbol clusters')
    parser.add_argument('--no-raw-drain',action='store_true',help='Skip the default independent current drain review primitive check')
    parser.add_argument('--no-raw-hvac',action='store_true',help='Skip the default original HVAC glyph/text anchor check')
    parser.add_argument('--no-raw-etr',action='store_true',help='Skip the default original electrical tail paths/arrow check')
    parser.add_argument('--no-raw-new-components',action='store_true',help='Skip the default independent LHS/GC/SRF checks')
    args=parser.parse_args();snapshot=open(args.model,'rb').read();M=json.loads(snapshot);drawn=read('drawn_position_audit')
    if args.inventory_only:
        report = source_gap_inventory(M)
        report['model_file_sha256'] = hashlib.sha256(snapshot).hexdigest()
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps(report['summary'], ensure_ascii=False))
        return 0
    if args.refresh_drawn:
        import check_drawn_positions as gate
        drawn=gate.audit(M)
        drawn['model_geometry_sha256']=hashlib.sha256(json.dumps(sorted((e['id'],e['g']) for e in M['els']),separators=(',', ':')).encode()).hexdigest()
    report=audit(M,drawn,args.raw_ws,args.raw_electrical,not args.no_raw_drain,not args.no_raw_hvac,not args.no_raw_etr,not args.no_raw_new_components);report['model_file_sha256']=hashlib.sha256(snapshot).hexdigest();report['model_path']=os.path.abspath(args.model)
    os.makedirs(os.path.dirname(os.path.abspath(args.output)),exist_ok=True)
    json.dump(report,open(args.output,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
    print(json.dumps({k:report[k] for k in ('model_elements','counts','by_family','height_counts','drawn_gate_snapshot_bound')},ensure_ascii=False))
    print('missing component review candidates:',len(report['missing_components']))
    return 0


if __name__=='__main__':sys.exit(main())
