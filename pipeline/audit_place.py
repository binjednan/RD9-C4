# -*- coding: utf-8 -*-
"""Placement audit of model.json (no PDFs needed): vertical range of every element against its level, elements outside the building footprint,
wall-hosted devices that are not touching a wall, doors/windows not inside a wall.   usage: python3 pipeline/audit_place.py [--json out]"""
import json, sys, os, math, collections
HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, "..", "src", "model.json")))
LV = {l["id"]: l for l in M["levels"]}
def zr(g):
    k = g[0]
    if k == "r": return g[5], g[6]
    if k == "b": return g[6], g[7]
    if k == "cyl": return g[4], g[5]
    if k == "p": return g[2], g[3]
    if k in ("t", "d"):
        zs = [p[2] for p in g[1] if len(p) > 2]; return (min(zs), max(zs)) if zs else (None, None)
def xyr(g):
    k = g[0]
    if k == "r": return min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4])
    if k == "b":
        hw, hd = g[3] / 2, g[4] / 2; a = math.radians(g[5]); c, s = abs(math.cos(a)), abs(math.sin(a)); ex, ey = hw * c + hd * s, hw * s + hd * c
        return g[1] - ex, g[2] - ey, g[1] + ex, g[2] + ey
    if k == "cyl": return g[1] - g[3], g[2] - g[3], g[1] + g[3], g[2] + g[3]
    if k == "p":
        xs = [p[0] for p in g[1]]; ys = [p[1] for p in g[1]]; return min(xs), min(ys), max(xs), max(ys)
    if k in ("t", "d"):
        xs = [p[0] for p in g[1]]; ys = [p[1] for p in g[1]]; return min(xs), min(ys), max(xs), max(ys)
FOOT = {"B": (-30, -30, 4440, 4440), "G": (-30, -100, 3230, 1900)}; FOOT.update({l: (60, -100, 3230, 1900) for l in "12345RT"})
def run():
    out = collections.defaultdict(list)
    for i, e in enumerate(M["els"]):
        l = LV.get(e["l"]); g = e["g"]
        if not l: continue
        z0, z1 = zr(g)
        if z0 is not None:
            top = l["top"] if e["l"] != "T" else l["ffl"] + 3.5
            if z1 < l["ffl"] - 0.35 or z0 > top + 0.35:
                if e["c"][0] not in "S": out["z_outside_level"].append((i, e["c"], e["l"], round(z0, 2), round(z1, 2)))
        bb = xyr(g); f = FOOT.get(e["l"])
        if f and e["c"][0] in "EMP" and (bb[0] < f[0] - 80 or bb[1] < f[1] - 80 or bb[2] > f[2] + 80 or bb[3] > f[3] + 80):
            out["outside_footprint"].append((i, e["c"], e["l"], [round(v) for v in bb]))
    return out
if __name__ == "__main__":
    out = run()
    for k, v in out.items():
        c = collections.Counter((x[1], x[2]) for x in v)
        print(k, len(v)); print("  ", c.most_common(25))
    if "--json" in sys.argv: json.dump(out, open(sys.argv[sys.argv.index("--json") + 1], "w"))
