# -*- coding: utf-8 -*-
"""Missing-wall audit: every wall line of the architectural plan (layer *A-WALL of ARCH1 A101..A105, same CAD xref as all other sheets) must be covered by a
wall / column / core of the model at the same level.  Reports the plan length of wall lines that are NOT covered (cm) and where they are.
usage: python3 pipeline/audit_walls.py [--json out]"""
import json, os, sys, math, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
import lib
M = json.load(open(os.path.join(HERE, "..", "src", "model.json")))
PAGES = {"B": 4, "G": 5, "1": 6, "3": 7, "R": 8}
def model_walls(level, cats=("A.wall", "S.wall", "S.col", "A.rail", "A.fix")):
    G = []
    for e in M["els"]:
        if e["l"] != level or e["c"] not in cats: continue
        g = e["g"]
        try:
            if g[0] == "r": G.append(box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4])))
            elif g[0] == "p": G.append(Polygon(g[1], g[4] if len(g) > 4 and g[4] else None).buffer(0))
        except Exception: pass
    return unary_union(G).buffer(6)
def run(levels=PAGES):
    out = {}
    for lv, pg in levels.items():
        sh = lib.Sheet("ARCH1", pg); W = model_walls(lv); miss = []; tot = 0.0; unc = 0.0
        for d in sh.D:
            ly = d["layer"] or ""
            if not ly.endswith("A-WALL"): continue
            for pl in d["polys"]:
                pts = [sh.T(x, y) for x, y in pl]
                for a, b in zip(pts[:-1], pts[1:]):
                    L = math.hypot(a[0] - b[0], a[1] - b[1])
                    if L < 25: continue
                    ln = LineString([a, b]); tot += L
                    inside = ln.intersection(W).length
                    if inside < L - 1:
                        unc += L - inside; miss.append((round((a[0] + b[0]) / 2), round((a[1] + b[1]) / 2), round(L - inside)))
        out[lv] = {"total_cm": round(tot), "uncovered_cm": round(unc), "pct": round(100 * unc / max(tot, 1), 1), "segs": miss}
        print(f"{lv:2}  wall-line length {tot/100:8.0f} m   not covered by the model {unc/100:7.0f} m  ({100*unc/max(tot,1):.1f} %)")
    return out
if __name__ == "__main__":
    r = run()
    if "--json" in sys.argv: json.dump(r, open(sys.argv[sys.argv.index("--json") + 1], "w"))
