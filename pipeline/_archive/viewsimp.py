# -*- coding: utf-8 -*-
"""Viewer-only simplification of polygon outlines (applied by src/build.py to the copy of the model that goes into index.html; src/model.json keeps the full outlines).

Outlines traced from arcs carry hundreds of vertices 1 mm apart: a ceiling outline of 1,364 points costs ~4,000 triangles every frame, and the whole model drew 1.14 M triangles (owner screenshots
2026-10-08: 5–27 fps in Safari).  Douglas–Peucker at a sub-centimetre tolerance keeps the shape (area within 1 %) and cuts the vertex count ~10× on ceilings.  It is NOT done in model.json on purpose:
ceilings are rebuilt from the floor polygons on every run of post_model.py, so simplified floors would silently renumber the ceilings (ids are what the owner's notes / hidden elements / saved views point at).
Structure (S.*) is never simplified."""
from shapely.geometry import Polygon

TOL_CM = {"A.ceil": 0.8, "A.floor": 0.6, "A.fix": 0.6, "P.fix": 0.6}


def simplify_model(M):
    """in place; returns (elements changed, vertices before, vertices after)"""
    n_el = v0 = v1 = 0
    for e in M["els"]:
        tol = TOL_CM.get(e["c"]); g = e["g"]
        if not tol or g[0] != "p": continue
        holes = g[4] if len(g) > 4 and g[4] else None
        try: pg = Polygon(g[1], holes)
        except Exception: continue
        if pg.is_empty or not pg.is_valid: continue
        sp = pg.simplify(tol, preserve_topology=True)
        if sp.geom_type != "Polygon" or sp.is_empty or not sp.is_valid or abs(sp.area - pg.area) > 0.01 * pg.area + 1.0: continue
        a = len(g[1]) + sum(len(h) for h in (holes or [])); b = len(sp.exterior.coords) - 1 + sum(len(r.coords) - 1 for r in sp.interiors)
        if b >= a: continue
        g[1] = [[round(x, 1), round(y, 1)] for x, y in sp.exterior.coords[:-1]]
        if holes: g[4] = [[[round(x, 1), round(y, 1)] for x, y in r.coords[:-1]] for r in sp.interiors] or None
        n_el += 1; v0 += a; v1 += b
    return n_el, v0, v1
