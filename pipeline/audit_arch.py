# -*- coding: utf-8 -*-
"""Architectural completeness audit of src/model.json (run after post_model.py).

Every check is geometric (shapely footprints + z-ranges), so a defect is reported with coordinates, never by eye:
  stairs   : stair steps/landings that penetrate slabs, beams, columns, walls (a stair "passing through concrete")
  ceilings : ceilings that are not enclosed by walls / not under a slab (floating plates)
  walls    : walls that stop short of the slab above, free wall ends, wall/slab gaps
  envelope : gaps in the exterior shell between floors (probe lines along every facade)
  equipment: equipment drawn as a single box (candidates for a realistic assembly)
usage: python3 pipeline/audit_arch.py [stairs|ceilings|walls|envelope|equipment|all]
"""
import json, math, os, sys, collections
from shapely.geometry import Polygon, box, Point, LineString
from shapely.affinity import rotate as _rot
from shapely.strtree import STRtree
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "src", "model.json")


def load():
    return json.load(open(SRC, encoding="utf-8"))


def foot(e):
    """plan footprint (shapely) and (z0, z1) of an element; None when the kind is not a solid prism"""
    g = e["g"]; k = g[0]
    if k == "p":
        pts = g[1]
        if len(pts) < 3: return None
        holes = [h for h in (g[4] if len(g) > 4 and g[4] else []) if len(h) >= 3]
        try:
            p = Polygon(pts, holes)
            if not p.is_valid: p = p.buffer(0)
        except Exception:
            return None
        return p, g[2], g[3]
    if k == "r":
        return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4])), g[5], g[6]
    if k == "b":
        p = box(g[1] - g[3] / 2, g[2] - g[4] / 2, g[1] + g[3] / 2, g[2] + g[4] / 2)
        return _rot(p, g[5], origin=(g[1], g[2])), g[6], g[7]
    if k == "cyl":
        return Point(g[1], g[2]).buffer(g[3], 12), g[4], g[5]
    return None


def solids(M, cats=None, types=None):
    out = []
    for i, e in enumerate(M["els"]):
        if cats and e["c"] not in cats: continue
        if types and e["t"] not in types: continue
        f = foot(e)
        if f: out.append((i, e, f[0], f[1], f[2]))
    return out


def audit_stairs(M, verbose=True):
    steps = solids(M, cats={"S.stair"})
    conc = solids(M, cats={"S.slab", "S.beam", "S.col", "S.wall", "A.wall"})
    tree = STRtree([c[2] for c in conc])
    hits = []
    for i, e, p, z0, z1 in steps:
        for j in tree.query(p):
            ci, ce, cp, cz0, cz1 = conc[j]
            zo = min(z1, cz1) - max(z0, cz0)
            if zo < 0.03: continue
            a = p.intersection(cp).area
            if a < 60: continue                         # < 60 cm2: edge touching
            hits.append({"step": e["id"], "lvl": e["l"], "with": ce["id"], "cat": ce["c"], "type": ce["t"], "area_cm2": round(a), "dz": round(zo, 2),
                         "at": [round(p.centroid.x), round(p.centroid.y)]})
    by = collections.Counter((h["lvl"], h["cat"]) for h in hits)
    if verbose:
        print(f"[stairs] {len(steps)} stair solids, {len(hits)} penetrations", dict(by))
        for h in sorted(hits, key=lambda h: -h["area_cm2"] * h["dz"])[:12]: print("   ", h)
    return hits


def audit_ceilings(M, verbose=True):
    """a ceiling is 'floating' when less than 60 % of its boundary touches a wall / column / beam / window / door / other ceiling plate,
    or when less than 80 % of it lies under the slab above (it hangs inside a stair / lift opening)"""
    L = {l["id"]: l for l in M["levels"]}
    ceil = solids(M, cats={"A.ceil"})
    vert = solids(M, cats={"A.wall", "S.wall", "S.col", "S.beam", "A.win", "A.clad", "A.door", "A.fix"})
    vt = STRtree([v[2] for v in vert])
    ct = STRtree([c[2] for c in ceil])
    sl = collections.defaultdict(list)
    for e in M["els"]:
        if e["c"] == "S.slab":
            f = foot(e)
            if f: sl[e["l"]].append(f[0])
    slabs = {lv: (unary_union(v),) for lv, v in sl.items()}
    order = [l["id"] for l in M["levels"]]
    res = []
    for i, e, p, z0, z1 in ceil:
        ring = p.exterior
        tot = ring.length
        touch = []
        for j in vt.query(p.buffer(14)):
            vi, ve, vp, vz0, vz1 = vert[j]
            if vz0 <= z0 + 0.3 and vz1 >= z1 - 0.1:
                touch.append(vp)
        for j in ct.query(p.buffer(14)):
            if ceil[j][0] != i and ceil[j][1]["l"] == e["l"]:
                touch.append(ceil[j][2])
        share = ring.intersection(unary_union(touch).buffer(12)).length / tot if touch and tot else 0
        lv = e["l"]; k = order.index(lv); cov = None
        if lv != "T" and k + 1 < len(order) and order[k + 1] in slabs:
            sp = slabs[order[k + 1]][0]
            cov = p.intersection(sp).area / p.area if p.area else 0
        res.append({"id": e["id"], "lvl": lv, "area_m2": round(p.area / 1e4, 2), "wall_share": round(share, 2), "under_slab": None if cov is None else round(cov, 2),
                    "at": [round(p.centroid.x), round(p.centroid.y)], "type": e["t"], "zone": (e.get("a") or {}).get("zone"), "fcl": (e.get("a") or {}).get("fcl_m")})
    bad = [r for r in res if r["wall_share"] < 0.6 or (r["under_slab"] is not None and r["under_slab"] < 0.8)]
    if verbose:
        print(f"[ceilings] {len(res)} ceiling elements, floating candidates {len(bad)}")
        for r in sorted(bad, key=lambda r: -r["area_m2"])[:14]: print("   ", r)
    return res, bad


def audit_walls(M, verbose=True):
    """walls: top reaches the slab above?  free ends: a wall end that touches no other wall/column/window/door"""
    L = {l["id"]: l for l in M["levels"]}
    order = [l["id"] for l in M["levels"]]
    short = []
    for e in M["els"]:
        if e["c"] != "A.wall": continue
        f = foot(e)
        if not f: continue
        lv = e["l"]; k = order.index(lv)
        if lv in ("T",): continue
        nxt = L[order[k + 1]]["ffl"] if k + 1 < len(order) else None
        # soffit of the slab above = next level slab bottom: typical = top of the level (L[lv]['top'])
        want = L[lv]["top"]
        gap = want - f[2]
        if gap > 0.05 and f[1] < 0.5:                   # starts at the floor but stops short of the soffit
            short.append({"id": e["id"], "lvl": lv, "type": e["t"], "top": round(f[2], 2), "soffit": want, "gap_m": round(gap, 2), "at": [round(f[0].centroid.x), round(f[0].centroid.y)]})
    if verbose:
        print(f"[walls] {sum(1 for e in M['els'] if e['c']=='A.wall')} walls; stop short of the soffit: {len(short)}")
        for r in short[:10]: print("   ", r)
    return short


def audit_envelope(M, verbose=True, du=10.0, dz=0.10):
    """probe every facade (4 sides x levels): is each (u, z) sample of the skin covered by a solid?  Reports uncovered rectangles (cm along the facade, m height)."""
    import numpy as np
    sides = {"S": ("y", -76.0, "x", -60.0, 3260.0), "N": ("y", 1865.0, "x", -60.0, 3260.0), "W": ("x", 100.0, "y", -60.0, 1900.0), "E": ("x", 3190.0, "y", -60.0, 1900.0)}
    cats = {"A.win", "A.clad", "A.wall", "S.col", "S.wall", "S.slab", "S.beam", "A.door", "A.rail"}
    sol = solids(M, cats=cats)
    # volumes as (polygon, z0, z1)
    tree = STRtree([c[2] for c in sol])
    L = {l["id"]: l for l in M["levels"]}
    out = collections.defaultdict(list)
    for side, (fix_ax, fix_v, run_ax, r0, r1) in sides.items():
        for lv in ("1", "2", "3", "4", "5"):
            ffl = L[lv]["ffl"]
            us = np.arange(r0, r1, du)
            zs = np.arange(ffl - 0.30, ffl + 3.45, dz)
            grid = np.zeros((len(zs), len(us)), bool)
            for iu, u in enumerate(us):
                x, y = (u, fix_v) if fix_ax == "y" else (fix_v, u)
                pt = Point(x, y).buffer(6)
                cand = [sol[j] for j in tree.query(pt) if sol[j][2].intersects(pt)]
                for iz, z in enumerate(zs):
                    for c in cand:
                        if c[3] - 1e-6 <= z <= c[4] + 1e-6:
                            grid[iz, iu] = True; break
            # uncovered cells -> merge into rectangles (greedy by rows of equal pattern)
            miss = ~grid
            for iz in range(len(zs)):
                iu = 0
                while iu < len(us):
                    if miss[iz, iu]:
                        j = iu
                        while j + 1 < len(us) and miss[iz, j + 1]: j += 1
                        if (j - iu + 1) * du >= 20:
                            out[(side, lv)].append((round(us[iu]), round(us[j] + du), round(zs[iz], 2)))
                        iu = j + 1
                    else:
                        iu += 1
    tot = {k: len(v) for k, v in out.items()}
    if verbose:
        print("[envelope] uncovered skin row-runs (>=20 cm) per side/level:", dict(sorted(tot.items())))
        for k in sorted(out):
            runs = out[k]
            if not runs: continue
            # merge rows into boxes per u-run
            boxes = collections.defaultdict(list)
            for a, b, z in runs: boxes[(a, b)].append(z)
            top = sorted(boxes.items(), key=lambda kv: -len(kv[1]))[:3]
            print("   ", k, [((a, b), round(min(zs), 2), round(max(zs) + dz, 2)) for (a, b), zs in top])
    return out


def main():
    M = load()
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    out = {}
    if what in ("stairs", "all"): out["stairs"] = audit_stairs(M)
    if what in ("ceilings", "all"): out["ceilings"] = audit_ceilings(M)[1]
    if what in ("walls", "all"): out["walls"] = audit_walls(M)
    if what in ("envelope", "all"): out["envelope"] = audit_envelope(M)
    return out


if __name__ == "__main__":
    main()
