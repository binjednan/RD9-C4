# -*- coding: utf-8 -*-
"""Retained landing-wall and ground-fill trims.

The former TOP HEAD slab cut used a fictitious R-to-T flight and assumed
headroom. A600/A601/A105/A106 show that T is the cover above the last R landing.
Its controlled rollback is stair01_roof_source_correction; this module must not
invent a top-roof opening. Existing wall/fill trimming remains unchanged.
"""
import collections
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

MIN_AREA = 50.0        # cm2 of overlap that counts as a collision (slabs, finishes)
MIN_AREA_WALL = 200.0  # walls: ignore 1 cm overlaps at the landing edge


def _poly(g):
    if g[0] == "p":
        holes = [h for h in (g[4] if len(g) > 4 and g[4] else []) if len(h) >= 3]
        try:
            p = Polygon(g[1], holes)
            return p if p.is_valid else p.buffer(0)
        except Exception:
            return None
    if g[0] == "r":
        return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4]))
    return None


def _zr(g):
    return (g[2], g[3]) if g[0] == "p" else (g[5], g[6])


def _geom(poly, z0, z1):
    g = ["p", [[round(x, 1), round(y, 1)] for x, y in list(poly.exterior.coords)[:-1]], round(z0, 3), round(z1, 3)]
    holes = [[[round(x, 1), round(y, 1)] for x, y in list(h.coords)[:-1]] for h in poly.interiors]
    if holes: g.append(holes)
    return g


def _replace(els, e, new_geom_poly, suffix_start=0):
    """swap element e's footprint for new_geom_poly (Polygon / MultiPolygon); extra pieces become siblings (same type, id + letter)"""
    z0, z1 = _zr(e["g"])
    parts = [q for q in (list(new_geom_poly.geoms) if hasattr(new_geom_poly, "geoms") else [new_geom_poly]) if not q.is_empty and q.geom_type == "Polygon" and q.area > 20]
    if not parts: els.remove(e); return 0
    parts.sort(key=lambda q: -q.area)
    e["g"] = _geom(parts[0], z0, z1)
    for k, q in enumerate(parts[1:]):
        ne = {kk: (list(v) if isinstance(v, list) else (dict(v) if isinstance(v, dict) else v)) for kk, v in e.items()}
        ne["id"] = e["id"] + "-" + "bcdefghij"[k]
        ne["g"] = _geom(q, z0, z1)
        els.append(ne)
    return len(parts)


def fix(M, els):
    stats = collections.Counter()
    steps = [e for e in els if e["c"] == "S.stair" and e["g"][0] in ("p", "r")]
    # 2) walls that run through a landing / flight
    by_lv = collections.defaultdict(list)
    for e in steps: by_lv[e["l"]].append(e)
    for w in [e for e in els if e["c"] == "A.wall" and e["g"][0] in ("p", "r")]:
        if w["l"] not in by_lv: continue
        W = _poly(w["g"])
        if W is None or W.is_empty: continue
        wz0, wz1 = _zr(w["g"])
        hit = []
        for s in by_lv[w["l"]]:
            sz0, sz1 = _zr(s["g"])
            if min(wz1, sz1) - max(wz0, sz0) < 0.03: continue
            sp = _poly(s["g"])
            if sp is not None and W.intersection(sp).area >= MIN_AREA_WALL: hit.append(sp)
        if hit:
            cut = unary_union(hit).buffer(0.5)
            _replace(els, w, W.difference(cut))
            w.setdefault("a", {})["trim_note"] = "قُصّ عند بسطة السلم: الجدار الفاصل بين الجناحين لا يمر عبر البسطة"
            stats["walls_trimmed"] += 1
    # 3) the ground-floor fill finish must not cover the external stair
    g_steps = [e for e in steps if e["l"] == "G"]
    for f in [e for e in els if e["c"] == "A.floor" and e["l"] == "G" and (e.get("a") or {}).get("kind") == "floor_fill" and e["g"][0] in ("p", "r")]:
        F = _poly(f["g"])
        if F is None: continue
        fz0, fz1 = _zr(f["g"])
        cut = []
        for s in g_steps:
            sz0, sz1 = _zr(s["g"])
            if sz1 <= fz0 + 0.03 or sz0 >= fz1: continue
            sp = _poly(s["g"])
            if sp is not None and F.intersection(sp).area >= MIN_AREA: cut.append(sp)
        if cut:
            _replace(els, f, F.difference(unary_union(cut).buffer(0.5)))
            stats["floor_fill_cut"] += 1
    return dict(stats)
