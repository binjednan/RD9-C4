# -*- coding: utf-8 -*-
"""Risers inferred from the plans (owner 2026-10-08: «أكمل استعمال جميع المخططات لتكون البيئة مناسبة للاختبار»).

Every plan sheet draws the pipes of ITS level only, and a riser is drawn on each level as the place where the horizontal pipes stop (or as a small ring).  The extraction therefore left every floor's
network as an island: the vertical pipe that joins them was never made.  What the plans DO document is the position: on every level the pipes of one medium end at the same plan point.  This module finds
those points and adds the vertical pipe between the levels — nothing else:

  evidence   ends (and ring symbols) of one medium, same plan point (<= RADIUS), on at least MIN_LEVELS levels in a row, one of them a non-typical level (basement / ground / roof — a rise that is
             repeated on the five typical floors alone is a fixture branch, not a riser), and the largest pipe at that point is a main (>= MIN_DIA mm of the medium)
  result     one tube per pair of consecutive levels (like the fire-fighting risers of mep_bg.py), diameter = the largest pipe that ends there, ids -Vnnnn (V = vertical; -L is taken by the landscape elements), grade 'vdd' (position derived from the
             alignment, size read from the pipes, elevation from the pipes' own ends), flagged on the card: «صاعد مستنتج من محاذاة نهايات المواسير على الطوابق»

Ids end with -Vnnnn so post_model.py drops and rebuilds them on every run (idempotent).  Runs after the clash pass (risers cross slabs on purpose) and before connectors.py."""
import os, re, sys, math, collections, copy, hashlib, json
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ID_RE = re.compile(r"-V\d{4}$")
FOOT_TOL = 15.0                     # cm  a riser that PASSES a level (no pipe end there) must stand inside that level's built footprint (walls, columns, floors, slabs) or touch it: a stack 25 cm outside the wall, in open air, is not a stack
RADIUS = 25.0                       # cm  plan distance within which ends of one medium count as the same point (the plans of different levels are registered to a few centimetres, rings are drawn off-centre)
SRC_TEXT = "صاعد مستنتج من محاذاة نهايات المواسير على الطوابق (نفس النقطة في المسقط على ثلاثة طوابق متتالية على الأقل بينها طابق غير نمطي؛ pipeline/risers.py) — الرسم يبيّن الموضع ولا يرسم الصاعد نفسه"
DRAIN_SRC_TEXT = "قائم صرف مولّد من تجميع نهايات النموذج بين المستويات في pipeline/risers.py؛ XY متوسط عنقود نهايات ضمن 25 سم، وZ والقطر مشتقان من تلك النهايات. لا يثبت هذا موضع صاعد خام مستقل أو قطره أو اتصاله أو منسوبه من المخطط."
DRAIN_LIMIT = "صاعد رأسي مشتق من نهايات النموذج؛ الربط بسجل سابق عند تطابق c/t/l/g كامل وفريد يثبت الهوية المشتقة فقط، ولا يثبت XY/Z أو جسمًا رأسيًا مرسومًا أو اتصالًا هيدروليكيًا."

# medium -> (category, element types, material, minimum main diameter in mm, name)
MEDIA = [
    ("chws", "M.pipe", ("pipe_chws",), "m_chws", 32, "صاعد مياه مبردة — تغذية"),
    ("chwr", "M.pipe", ("pipe_chwr",), "m_chwr", 32, "صاعد مياه مبردة — رجوع"),
    ("cold", "P.cold", ("pipe_cold",), "p_cold", 32, "صاعد مياه باردة"),
    ("hot", "P.hot", ("pipe_hot",), "p_hot", 32, "صاعد مياه ساخنة"),
    ("soil", "P.drain", ("pipe_soil",), "p_soil", 75, "قائم صرف (Soil stack)"),
    ("waste", "P.drain", ("pipe_waste",), "p_waste", 75, "قائم صرف (Waste stack)"),
]
TYPICAL = {"2", "3", "4", "5"}


def canonical_identity(e):
    """Exact identity of a derived segment; no distance or source-position test."""
    return json.dumps([e['c'], e.get('t'), e['l'], e['g']], separators=(',', ':'))


def canonical_identity_hash(e):
    return hashlib.sha256(canonical_identity(e).encode()).hexdigest()


def is_drain_riser(e):
    """Recognize the drain outputs of this generator, not raw plan routes."""
    return (e.get('c')=='P.drain' and e.get('t') in ('pipe_soil','pipe_waste')
            and bool((e.get('a') or {}).get('riser')) and bool(ID_RE.search(e.get('id',''))))


def derived_drain_bindings(M, els=None, records=None):
    """Read-only current-to-historical mapping by unique exact c/t/l/g.

    Historical V ordinals can be reused after an earlier medium changes count.
    An ordinal alone is never a binding. Unmatched/ambiguous outputs remain
    generated derivatives and carry no historical source-coordinate claim.
    """
    els=M['els'] if els is None else els
    current=[e for e in els if is_drain_riser(e)]
    old={eid:q for eid,q in (records or {}).items() if q.get('status')=='derived_vertical_riser'}
    old_keys=collections.defaultdict(list);current_keys=collections.defaultdict(list)
    for eid,q in old.items():
        old_keys[canonical_identity({'c':q['category'],'t':q['type'],'l':q['level'],'g':q['reviewed_g']})].append(eid)
    for e in current:current_keys[canonical_identity(e)].append(e['id'])
    bindings={}
    for e in current:
        key=canonical_identity(e);hits=old_keys.get(key,[])
        unique=len(hits)==1 and len(current_keys[key])==1
        bindings[e['id']]={'current_id':e['id'],'historical_id':hits[0] if unique else None,
            'canonical_identity_sha256':hashlib.sha256(key.encode()).hexdigest(),
            'binding_status':'exact_unique' if unique else 'ambiguous' if hits else 'unmatched',
            'candidate_historical_ids':hits,
            'proof_scope':'derived_identity_only_not_drawn_XY_Z_or_contact'}
    counts=collections.Counter(q['binding_status'] for q in bindings.values())
    return {'schema':'c4.derived-drain-riser-bindings.v1','source_generation_module':'pipeline/risers.py',
            'current_count':len(current),'historical_count':len(old),'exact_unique_count':counts['exact_unique'],
            'unmatched_count':counts['unmatched'],'ambiguous_count':counts['ambiguous'],'bindings':bindings}


def _annotate_derived_drain(e, binding=None, historical=None, inputs=None):
    a=e.setdefault('a',{})
    # These former direct-ID attributes could belong to a different V ordinal.
    # Candidate plan primitives are retained separately and are never an anchor.
    for key in ('source_locked_xy','source_page','source_transform','source_primitives','source_trace_record'):
        a.pop(key,None)
    a.update(source_trace_review=True,source_trace_status='derived_vertical_riser',
        source_kind='derived_vertical_riser',derived=True,
        source_generation_module='pipeline/risers.py',
        source_generation_identity_sha256=canonical_identity_hash(e),
        source_trace_limit=DRAIN_LIMIT,source_position_pending=True,source_position_review=DRAIN_LIMIT,
        geometry_role='derived_riser_display',source_XY_verified=False,source_Z_verified=False,
        source_dimensions_verified=False,source_material_verified=False,source_mount_verified=False,
        source_ports_verified=False,source_contact_verified=False,
        physical_geometry_status='derived_display_pending_source_riser_body_diameter_elevation_and_contact',
        elevation_status='derived_from_model_end_elevations_unverified',
        dimension_status='derived_from_largest_model_end_diameter_unverified',
        material_status='not_specified_in_reviewed_source',finish_status='not_specified_in_reviewed_source')
    if inputs is not None:a['source_generation_inputs']=copy.deepcopy(inputs)
    a['source_derived_historical_record']=binding.get('historical_id') if binding else None
    a['source_derived_binding_status']=binding.get('binding_status','unmatched') if binding else 'unmatched'
    a.pop('source_derived_historical_candidate',None)
    if historical is not None:
        a['source_derived_historical_candidate']={'historical_id':historical['id'],
            'reference':historical['source'],'source_primitives':copy.deepcopy(historical['source_primitives']),
            'proof_scope':'nearby_plan_candidates_only_not_a_riser_position_or_Z_source'}


def annotate_derived_drains(M, els=None, records=None):
    """Metadata only: classify current generated drains and bind unique old data."""
    els=M['els'] if els is None else els
    report=derived_drain_bindings(M,els,records)
    for e in els:
        binding=report['bindings'].get(e['id'])
        if binding is None:continue
        historical=(records or {}).get(binding['historical_id']) if binding['historical_id'] else None
        _annotate_derived_drain(e,binding,historical)
    return report


def _geom(e):
    g = e["g"]
    try:
        if g[0] == "p": return Polygon(g[1]).buffer(0)
        if g[0] == "r": return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4]))
        if g[0] == "b":
            cx, cy, w, d, rot = g[1:6]; th = math.radians(rot); c, s_ = math.cos(th), math.sin(th)
            return Polygon([(cx + px * c - py * s_, cy + px * s_ + py * c) for px, py in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))])
        if g[0] == "cyl": return Point(g[1], g[2]).buffer(g[3])
    except Exception: return None
    return None


def footprints(M):
    """level -> shapely geometry of what is BUILT at that level (floor finishes, walls, columns, stairs, and the slab of every floor above the ground: the ground slab is the whole plot)"""
    out = {}
    for lv in [l["id"] for l in M["levels"]]:
        parts = []
        for e in M["els"]:
            if e["l"] != lv: continue
            if e["c"] in ("A.floor", "S.col", "S.wall", "A.wall", "S.stair") or (e["c"] == "S.slab" and lv not in ("B", "G")):
                pg = _geom(e)
                if pg is not None and not pg.is_empty: parts.append(pg)
        out[lv] = unary_union(parts) if parts else None
    return out


def _dia_mm(e):
    a = e.get("a") or {}
    return a.get("dia_mm") or round(e["g"][2] * 10) if e["g"][0] == "t" else 0


def build(M, verbose=False):
    els = M["els"]
    els[:] = [e for e in els if not ID_RE.search(e["id"])]
    sp = M["sp"]
    if SRC_TEXT not in sp: sp.append(SRC_TEXT)
    sidx = sp.index(SRC_TEXT)
    if DRAIN_SRC_TEXT not in sp:sp.append(DRAIN_SRC_TEXT)
    drain_sidx=sp.index(DRAIN_SRC_TEXT)
    lv = {l["id"]: l for l in M["levels"]}; order = [l["id"] for l in M["levels"]]
    new = []; counter = collections.Counter(); skipped = []
    foot = footprints(M)
    for key, cat, types, mat, min_dia, name in MEDIA:
        if mat not in M["mats"]: mat = next((e["m"] for e in els if e["c"] == cat and e.get("t") in types), mat)
        ends = []                                     # (x, y, z, level, dia_mm, element id)
        for e in els:
            if e["c"] != cat or e.get("t") not in types or e["g"][0] != "t" or (e.get("a") or {}).get("connector") or (e.get("a") or {}).get("no_connectors"): continue
            pts = e["g"][1]; d = _dia_mm(e)
            closed = len(pts) >= 4 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 2 and max(abs(p[0] - pts[0][0]) for p in pts) < 60
            if closed:                                # a ring: the riser symbol itself
                cx = sum(p[0] for p in pts[:-1]) / (len(pts) - 1); cy = sum(p[1] for p in pts[:-1]) / (len(pts) - 1)
                ends.append((cx, cy, pts[0][2], e["l"], d, e["id"]))
            else:
                for p in (pts[0], pts[-1]): ends.append((p[0], p[1], p[2], e["l"], d, e["id"]))
        clusters = []
        for en in ends:
            for c in clusters:
                if math.hypot(c["x"] - en[0], c["y"] - en[1]) <= RADIUS: c["m"].append(en); c["x"] = sum(m[0] for m in c["m"]) / len(c["m"]); c["y"] = sum(m[1] for m in c["m"]) / len(c["m"]); break
            else: clusters.append({"x": en[0], "y": en[1], "m": [en]})
        for c in clusters:
            lvls = sorted({m[3] for m in c["m"]}, key=lambda l: order.index(l))
            if len(lvls) < 3: continue
            idx = [order.index(l) for l in lvls]
            if any(b - a > 2 for a, b in zip(idx, idx[1:])): continue             # no gap of more than one level (a riser may pass a level where nothing branches off)
            if not (set(lvls) - TYPICAL - {"1"}): continue                       # needs a basement / ground / roof end
            dia = max(m[4] for m in c["m"])
            if dia < min_dia: continue
            # one point per level: the mean elevation of that level's ends
            z = {l: sum(m[2] for m in c["m"] if m[3] == l) / sum(1 for m in c["m"] if m[3] == l) for l in lvls}
            for a, b in zip(lvls, lvls[1:]):
                ia, ib = order.index(a), order.index(b)
                out = [(l, round(foot[l].distance(Point(c["x"], c["y"])))) for l in order[ia + 1:ib] if foot.get(l) is not None and foot[l].distance(Point(c["x"], c["y"])) > FOOT_TOL]
                if out:                                                               # the stack would cross a level in open air: not built, listed for the owner
                    skipped.append({"medium": key, "x": round(c["x"]), "y": round(c["y"]), "from": a, "to": b, "open_at": out}); counter[("skipped", cat, a, b)] += 1; continue      # the id number of the skipped segment stays reserved
                counter[(cat, b)] += 1
                e = {"id": f"{cat}-{b}-V{sum(counter.values()):04d}", "c": cat, "l": b, "g": ["t", [[round(c["x"], 1), round(c["y"], 1), round(z[a], 3)], [round(c["x"], 1), round(c["y"], 1), round(z[b], 3)]], round(dia / 10 * 1.1, 1)],
                     "mark": f"RISER-{key.upper()}-{int(round(c['x']))}/{int(round(c['y']))}", "t": types[0], "m": mat,
                     "a": {"riser": True, "dia_mm": dia, "length_m": round(abs(z[b] - z[a]), 2), "kind": name, "levels": f"{a} → {b}", "evidence": f"{len(c['m'])} نهاية على {len(lvls)} طوابق عند النقطة نفسها",
                           "assumed": "القطر = أكبر ماسورة تنتهي هنا؛ المنسوب من نهايات المواسير نفسها"}, "s": [sidx]}
                if cat=='P.drain':
                    _annotate_derived_drain(e,inputs={'levels':lvls,
                        'endpoint_element_ids':sorted({m[5] for m in c['m']}),
                        'clustering_radius_cm':RADIUS,'XY_basis':'mean_of_generated_model_endpoint_cluster',
                        'Z_basis':'mean_of_model_endpoint_elevations_per_level',
                        'diameter_basis':'largest_model_endpoint_diameter_with_display_factor_1.1'})
                    e['s']=[drain_sidx]
                new.append(e)
            if verbose: print(f"  riser {key:5s} ({round(c['x'])},{round(c['y'])}) dia {dia} levels {lvls} ends {len(c['m'])}")
    els.extend(new)
    M.setdefault("meta", {})["risers_skipped"] = skipped
    if verbose: print("risers:", len(new), "skipped (cross a level in open air):", len(skipped), [(k["medium"], k["x"], k["y"], k["open_at"]) for k in skipped])
    return len(new)


if __name__ == "__main__":
    import json
    SRC = os.path.join(os.path.dirname(HERE), "src", "model.json")
    M = json.load(open(SRC, encoding="utf-8"))
    build(M, verbose=True)
