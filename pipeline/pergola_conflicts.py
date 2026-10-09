# -*- coding: utf-8 -*-
"""Read-only pergola/MEP intersection audit, matching src/engine.js primitives.

No geometry or model fields are changed. Positive model volume is a coordination
candidate, not source approval, a shop drawing check, or evidence about the site.
Plan coordinates are cm and elevations are metres. Polygon holes are preserved.
"""
import collections
import hashlib
import json
import math

from shapely.geometry import MultiPoint, Polygon, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

EPS = 1e-9  # Numerical equality only; no geometric tolerance or distance buffer.

# Independently checked in raw MECH2:22 drawing records by the water audit.
# These exact four closed tank outlines were erroneously classified as pipes.
# Bind the exclusion to the current geometry hash; a changed object is rechecked.
SEMANTIC_FALSE_PIPES = {
    "P.cold-R-M0025": (3788, "GRP west body", "9b00977e19f02c23dda9c98da3d524a799fb5366f2e2ea9dce81dbada65c38cb"),
    "P.cold-R-M0026": (3789, "GRP west outer frame", "06f36b3f8a48b572075ee5a4a1e7d91ee49e6be7856b40519455982c8f2a0f3f"),
    "P.cold-R-M0027": (3790, "GRP east body", "965e6acf74fb4c0ee3098f34aa5ea43aa105ea6631b5587ad7091be2d658f230"),
    "P.cold-R-M0028": (3791, "GRP east outer frame", "36a17d991f7b84c5d522df983cb78b40a5c76905444ac19ba9e8cc8228e736a3"),
}


def _hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _unit(a):
    length = math.sqrt(sum(v*v for v in a))
    return tuple(v/length for v in a)


def _footprint(g):
    if g[0] == "r":
        return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4])), (g[5], g[6])
    if g[0] == "p":
        return Polygon(g[1], g[4] if len(g) > 4 and g[4] else None), (g[2], g[3])
    if g[0] == "b":
        x, y, w, d, angle = g[1:6]
        co, si = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        p = Polygon([(x+u*co-v*si, y+u*si+v*co)
                     for u, v in [(-w/2, -d/2), (w/2, -d/2), (w/2, d/2), (-w/2, d/2)]])
        return p, (g[6], g[7])
    if g[0] == "cyl":
        # The actual display cylinder uses 14 sides, not a circumscribed circle.
        p = Polygon([(g[1]+g[3]*math.cos(2*math.pi*i/14), g[2]+g[3]*math.sin(2*math.pi*i/14))
                     for i in range(14)])
        return p, (g[4], g[5])
    return None, (None, None)


def _segment(g, p, q, index):
    """The convex segment body drawn by engine tubeSeg/ductSeg, in cm XYZ."""
    a, b = (p[0], p[1], p[2]*100), (q[0], q[1], q[2]*100)
    delta = tuple(y-x for x, y in zip(a, b))
    length = math.sqrt(sum(x*x for x in delta))
    if length <= EPS:
        return None
    if g[0] == "t":
        if length < .2:  # engine tubeSeg skips lengths below 0.002 m
            return None
        direction = _unit(delta)
        up = (1, 0, 0) if abs(direction[2]) > .9 else (0, 0, 1)
        n1 = _unit(_cross(direction, up))
        n2 = _cross(direction, n1)
        diameter, radius = g[2], g[2]/2
        sides = 5 if diameter <= 3.5 else (6 if diameter <= 7 else 8)
        offsets = [tuple(radius*(math.cos(2*math.pi*i/sides)*n1[j] + math.sin(2*math.pi*i/sides)*n2[j])
                         for j in range(3)) for i in range(sides)]
        method = "engine_tube_%d_sided_segment" % sides
    else:
        if length < .5:  # engine ductSeg threshold, in cm
            return None
        dx, dy = delta[:2]
        plan_length = math.hypot(dx, dy if dy else 1e-9)
        nx, ny = -dy/plan_length, dx/plan_length
        offsets = [(nx*g[2]/2*sw, ny*g[2]/2*sw, g[3]/2*sh)
                   for sw, sh in [(1, 1), (-1, 1), (-1, -1), (1, -1)]]
        sides, method = 4, "engine_duct_rectangular_segment"
    vertices = [tuple(c[j]+o[j] for j in range(3)) for c in (a, b) for o in offsets]
    edges = [(i, (i+1) % sides) for i in range(sides)]
    edges += [(i+sides, (i+1) % sides+sides) for i in range(sides)]
    edges += [(i, i+sides) for i in range(sides)]
    footprint = MultiPoint([(v[0], v[1]) for v in vertices]).convex_hull
    if footprint.area <= EPS:
        # The current renderer makes a strictly vertical duct degenerate in plan.
        return None
    z_events = sorted(set(v[2]/100 for v in vertices))
    return {"polygon": footprint, "z": (z_events[0], z_events[-1]), "events": z_events,
            "vertices": vertices, "edges": edges, "segment": index, "method": method}


def _slice(piece, z):
    if not piece["z"][0]-EPS <= z <= piece["z"][1]+EPS:
        return Polygon()
    if "vertices" not in piece:
        return piece["polygon"]
    z *= 100
    vertices, points = piece["vertices"], []
    for i, j in piece["edges"]:
        p, q = vertices[i], vertices[j]
        if abs(p[2]-z) <= EPS:
            points.append(p[:2])
        if abs(q[2]-z) <= EPS:
            points.append(q[:2])
        if (p[2]-z)*(q[2]-z) < 0:
            fraction = (z-p[2])/(q[2]-p[2])
            points.append((p[0]+fraction*(q[0]-p[0]), p[1]+fraction*(q[1]-p[1])))
    return MultiPoint(points).convex_hull if points else Polygon()


def _integrate(f, a, b, tolerance=1e-5, depth=14):
    """Adaptive Simpson estimate of area(cm2) over height(m); no geometry buffer."""
    mid = (a+b)/2
    fa, fm, fb = f(a), f(mid), f(b)
    first = (b-a)*(fa+4*fm+fb)/6

    def descend(lo, hi, flo, fmid, fhi, old, tol, remaining):
        m = (lo+hi)/2
        q0, q1 = (lo+m)/2, (m+hi)/2
        f0, f1 = f(q0), f(q1)
        left, right = (m-lo)*(flo+4*f0+fmid)/6, (hi-m)*(fmid+4*f1+fhi)/6
        correction = left+right-old
        if remaining == 0 or abs(correction) <= 15*tol:
            return left+right+correction/15, abs(correction)/15
        lv, le = descend(lo, m, flo, f0, fmid, left, tol/2, remaining-1)
        rv, re = descend(m, hi, fmid, f1, fhi, right, tol/2, remaining-1)
        return lv+rv, le+re

    return descend(a, b, fa, fm, fb, first, tolerance, depth)


def _sources(M, e):
    t, a = M.get("types", {}).get(e.get("t"), {}), e.get("a") or {}
    refs = [M["sp"][i] for i in e.get("s", []) if 0 <= i < len(M.get("sp", []))]
    refs += t.get("sr", [])
    refs += [a[k] for k in ("source_reference", "source_z_reference") if a.get(k)]
    if a.get("source_page"):
        page = a["source_page"]
        refs.append("%s:%s" % (a["source_set"], page) if a.get("source_set") else page)
    return list(dict.fromkeys(str(v) for v in refs))


def _assumptions(M, e):
    a, t = e.get("a") or {}, M.get("types", {}).get(e.get("t"), {})
    values = list(t.get("asm", []))
    values += [a[k] for k in ("assumed", "size_note", "drawing_conflict") if a.get(k)]
    if e.get("l") == "R" and e.get("t") in ("chiller", "fahu"):
        values.append("قاع جسم المعدة في المجسم عند FFL السطح 23.35 م؛ أبعاد/ارتفاع المعدة وحدها لا تثبت تفصيل القاعدة")
    if e.get("t") == "chiller_fan":
        values.append("حلقة المروحة في المجسم فوق المبرّد عند25.85–25.91 م؛ سماكة الحلقة6 سم افتراض مرئي")
    return list(dict.fromkeys(str(v) for v in values))


def _height_assumptions(values):
    return [v for v in values if any(word in v for word in ("ارتفاع", "الارتفاع", "منسوب", "قاع", "قاعدة", "FFL", "رأسي", "حلقة"))]


def audit(M, els=None):
    """Return exact positive section witnesses and numeric volume estimates.

    An interior horizontal section with positive area proves positive model
    volume by continuity. Unioned segment sections avoid counting route elbows
    twice. Volume estimates are diagnostic; candidate status never depends on
    an integration tolerance, assumed height, or a nearest-host relationship.
    """
    els = M["els"] if els is None else els
    pergolas = [e for e in els if e["c"] == "A.pergola"]
    services = [e for e in els if e["c"].split(".")[0] in {"M", "P", "E"}]
    if not pergolas:
        return {"status": "model_candidate", "pairs": [], "audit": {"pergola_count": 0}}
    pg_rows = []
    for e in pergolas:
        p, z = _footprint(e["g"])
        if p is None or not p.is_valid:
            raise ValueError("Invalid pergola polygon: " + e["id"])
        pg_rows.append((e, p, z))
    global_z = (min(z[0] for _, _, z in pg_rows), max(z[1] for _, _, z in pg_rows))
    pieces, unknown, degenerate = [], [], []
    for e in services:
        g = e["g"]
        if g[0] in ("t", "d"):
            for index, (p, q) in enumerate(zip(g[1], g[1][1:])):
                # Safe broad phase before constructing the actual cross-section.
                radius = g[2]/200 if g[0] == "t" else g[3]/200
                if min(p[2], q[2])-radius >= global_z[1] or max(p[2], q[2])+radius <= global_z[0]:
                    continue
                row = _segment(g, p, q, index)
                if row is None:
                    degenerate.append({"id": e["id"], "segment": index})
                    continue
                if row["z"][0] < global_z[1] and row["z"][1] > global_z[0]:
                    pieces.append(dict(row, element=e))
        else:
            p, z = _footprint(g)
            if p is None:
                unknown.append(e["id"])
            elif z[0] < global_z[1] and z[1] > global_z[0] and p.is_valid and p.area > EPS:
                pieces.append({"element": e, "polygon": p, "z": z, "events": list(z),
                               "method": "engine_%s_vertical_prism" % g[0], "segment": None})
    tree = STRtree([q["polygon"] for q in pieces]) if pieces else None
    pairs, semantic_false_pipe_overlaps, unresolved_envelopes, comparisons = [], [], [], 0
    exclusions, exclusion_mismatches = [], []
    for e in services:
        if e["id"] in SEMANTIC_FALSE_PIPES:
            index, kind, expected_hash = SEMANTIC_FALSE_PIPES[e["id"]]
            row = {"id": e["id"], "source_page": "MECH2:22", "source_layer": "M_WS_CW",
                   "source_drawing_index": index, "source_kind": kind,
                   "geometry_sha256": _hash(e["g"]), "expected_geometry_sha256": expected_hash,
                   "reason_ar": "مستطيل مغلق يمثل جسم خزانGRP أو إطاره الخارجي في الرسم؛ تصنيفه كأنبوب مياه باردة خطأ دلالي في المجسم"}
            (exclusions if row["geometry_sha256"] == expected_hash else exclusion_mismatches).append(row)
    excluded_ids = {q["id"] for q in exclusions}
    for pg, pp, pz in pg_rows:
        candidates = collections.defaultdict(list)
        for index in tree.query(pp, predicate="intersects") if tree is not None else []:
            piece = pieces[index]
            comparisons += 1
            if min(pz[1], piece["z"][1])-max(pz[0], piece["z"][0]) > EPS and pp.intersection(piece["polygon"]).area > EPS:
                candidates[piece["element"]["id"]].append(piece)
        for service_id in sorted(candidates):
            group = candidates[service_id]
            service = group[0]["element"]
            lo = max(pz[0], min(q["z"][0] for q in group))
            hi = min(pz[1], max(q["z"][1] for q in group))
            events = sorted(set([lo, hi]+[v for q in group for v in q["events"] if lo < v < hi]))
            witnesses, cache = [], {}

            def section(z):
                if z not in cache:
                    sections = [_slice(q, z) for q in group]
                    sections = [s for s in sections if not s.is_empty and s.area > EPS]
                    cache[z] = pp.intersection(unary_union(sections)) if sections else Polygon()
                return cache[z]

            def area(z):
                return section(z).area

            # Every candidate must have an interior positive-area witness.
            for a, b in zip(events, events[1:]):
                for fraction in (.125, .375, .5, .625, .875):
                    z = a+(b-a)*fraction
                    poly = section(z)
                    if poly.area > EPS:
                        witnesses.append((poly.area, z, poly))
            if not witnesses:
                unresolved_envelopes.append({"pergola_id": pg["id"], "service_id": service_id,
                                             "reason": "projection/Z envelope overlaps but no positive interior section proved"})
                continue
            volume, error = 0., 0.
            for a, b in zip(events, events[1:]):
                # Seed four intervals so thin edge intersections cannot be skipped by a single midpoint.
                for index in range(4):
                    v, err = _integrate(area, a+(b-a)*index/4, a+(b-a)*(index+1)/4)
                    volume += v/10000
                    error += err/10000
            best_area, witness_z, witness = max(witnesses, key=lambda q: q[0])
            representative = witness.representative_point()
            pg_assumed, service_assumed = _assumptions(M, pg), _assumptions(M, service)
            pg_height, service_height = _height_assumptions(pg_assumed), _height_assumptions(service_assumed)
            pg_refs, service_refs = _sources(M, pg), _sources(M, service)
            pair_id = "PG-MEP-" + _hash([pg["id"], service_id])[:12].upper()
            row = {
                "id": pair_id, "status": "model_candidate", "pergola_id": pg["id"], "service_id": service_id,
                "pergola_type": pg.get("t"), "service_type": service.get("t"), "level": pg["l"],
                "xy_cm": [representative.x, representative.y], "xy_overlap_bounds_cm": list(witness.bounds),
                "z_overlap_m": [lo, hi], "z_overlap_cm": (hi-lo)*100,
                "positive_model_volume_proved": True, "volume_m3": volume,
                "volume_method": "adaptive horizontal-section union; engine primitive body including pergola holes",
                "volume_numeric_error_estimate_m3": error,
                "positive_section_witness": {"z_m": witness_z, "area_cm2": best_area,
                                             "xy_cm": [representative.x, representative.y]},
                "source_refs": list(dict.fromkeys(pg_refs+service_refs)),
                "source_refs_by_element": {"pergola": pg_refs, "service": service_refs},
                "source_height_assumed": bool(pg_height or service_height),
                "height_assumptions": {"pergola": pg_height, "service": service_height},
                "section_and_dimension_assumptions": {"pergola": pg_assumed, "service": service_assumed},
                "model_z_ranges_m": {"pergola": list(pz), "service": [min(q["z"][0] for q in group), max(q["z"][1] for q in group)]},
                "source_z_reference": {"pergola": (pg.get("a") or {}).get("source_z_reference"),
                                       "service": (service.get("a") or {}).get("source_z_reference")},
                "segment_indices": [q["segment"] for q in group], "geometry_methods": sorted(set(q["method"] for q in group)),
                "geometry_sha256": {"pergola": _hash(pg["g"]), "service": _hash(service["g"])},
                "reason_ar": "تقاطع بحجم موجب في هندسة المجسم بين البرجولة وعنصر الخدمة عند الموضع والمناسيب المسجلة؛ مرشّح تنسيق، وتفاصيل الارتفاع/القطاع والمعدة المذكورة في الافتراضات تحتاج حسمًا من الرسم المعتمد. لا يثبت تنفيذًا ميدانيًا ولا يغيّر الموضع.",
            }
            if service_id in excluded_ids:
                row["status"] = "source_symbol_misclassification"
                row["reason_ar"] = "تقاطع هندسي ناتج من تمثيل حدود خزانGRP كأنبوب؛ يُستبعد من مرشحات تنسيق البرجولة والخدمات، مع حفظ دليل الخطأ الدلالي حتى تصحيح المصنف"
                row["semantic_source_proof"] = next(q for q in exclusions if q["id"] == service_id)
                semantic_false_pipe_overlaps.append(row)
            else:
                pairs.append(row)
    pairs.sort(key=lambda q: (q["pergola_id"], q["service_id"]))
    semantic_false_pipe_overlaps.sort(key=lambda q: (q["pergola_id"], q["service_id"]))
    return {"status": "model_candidate", "pairs": pairs, "semantic_false_pipe_overlaps": semantic_false_pipe_overlaps,
            "audit": {"model_elements": len(els), "model_geometry_sha256": _hash([[e["id"], e["g"]] for e in els]),
                      "pergola_count": len(pergolas), "service_count": len(services),
                      "possible_element_pairs": len(pergolas)*len(services), "roof_height_range_m": list(global_z),
                      "service_pieces_in_height_band": len(pieces), "projection_piece_comparisons": comparisons,
                      "geometric_positive_volume_pairs": len(pairs)+len(semantic_false_pipe_overlaps),
                      "positive_volume_pairs": len(pairs), "semantic_false_pipe_overlap_pairs": len(semantic_false_pipe_overlaps),
                      "semantic_excluded_objects": exclusions, "semantic_exclusion_geometry_mismatches": exclusion_mismatches,
                      "pair_types": dict(collections.Counter(q["pergola_type"]+" / "+q["service_type"] for q in pairs)),
                      "unproved_envelope_candidates": unresolved_envelopes,
                      "unsupported_geometry_ids": unknown, "degenerate_rendered_segments": degenerate,
                      "classification": "positive model volume only; all issues remain model_candidate",
                      "numerical_equality_cm": EPS, "geometry_preserved": True}}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model")
    parser.add_argument("output")
    args = parser.parse_args()
    with open(args.model) as handle:
        model = json.load(handle)
    result = audit(model)
    with open(args.output, "w") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(result["audit"], ensure_ascii=False))
