# -*- coding: utf-8 -*-
"""Dashed centre line and direction arrows of the ground-floor plan (ARCH1 p5, layers «0» / «…A-Road Marks» / «…Arrow») — one polygon per DRAWING.

Every filled drawing of those layers is made of TRIANGLES (a dash = 2 triangles, an arrow shaft = 2, the arrow head = 1).  pipeline/site.py used to take only the first triangle of each drawing, so every dash
showed as a thin spike and every arrow as a broken bow-tie (owner screenshot 2026-10-08).  The triangles of one drawing are merged here; the number of elements is unchanged, so no element id shifts.

    python3 pipeline/site_marks.py     # re-reads the sheet and corrects those marks inside pipeline/data/site.json in place (idempotent; needs the source PDF, not OpenCV)"""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from shapely.geometry import Polygon
from shapely.ops import unary_union

SITE = os.path.join(HERE, "data", "site.json")


def merged(wpolys):
    """triangles / quads (plan cm) of one drawing -> the outline of their union (largest part), collinear points dropped"""
    pg = unary_union([Polygon(w).buffer(0) for w in wpolys if len(w) >= 3]).simplify(0.05)
    if pg.geom_type != "Polygon": pg = max(list(pg.geoms), key=lambda q: q.area)
    return [[round(x, 1), round(y, 1)] for x, y in pg.exterior.coords[:-1]]


def shapes(sh):
    """[(name, outline)] in drawing order: the dashed centre line (layer 0, x 3.60–3.64 m) and the direction arrows (Road Marks / Arrow layers)"""
    out = []
    for d in sh.D:
        if not d.get("fill") or not d["polys"]: continue
        ly = d["layer"] or ""
        ws = [[sh.T(x, y) for x, y in pl] for pl in d["polys"]]
        xs = [q[0] for w in ws for q in w]; ys = [q[1] for w in ws for q in w]
        if len(ws[0]) < 3: continue
        if ly == "0" and 3600 < min(xs) and max(xs) < 3640 and max(xs) - min(xs) < 20 and 90 < max(ys) - min(ys) < 140 and -100 < min(ys) < 3400:
            out.append(("خط منتصف متقطع (طبقة 0)", merged(ws)))
        elif ly.endswith("A-Road Marks") or ly.endswith("$Arrow"):
            out.append(("سهم اتجاه (طبقة " + ly.split("$")[-1] + ")", merged(ws)))
    return out


def patch():
    import lib
    sh = lib.Sheet("ARCH1", 5)
    new = shapes(sh)
    S = json.load(open(SITE, encoding="utf-8"))
    idx = [i for i, e in enumerate(S["els"]) if e["t"] == "site_mark" and any(k in " ".join(e.get("src") or []) for k in ("خط منتصف متقطع", "سهم اتجاه"))]
    if len(idx) != len(new): raise SystemExit(f"site.json has {len(idx)} drawn marks, the sheet gives {len(new)} — not patched")
    n = 0
    for i, (nm, poly) in zip(idx, new):
        e = S["els"][i]
        if e["g"][1] != poly: e["g"][1] = poly; n += 1
    json.dump(S, open(SITE, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
    print("marks corrected:", n, "of", len(idx))


if __name__ == "__main__":
    patch()
