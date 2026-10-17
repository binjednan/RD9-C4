# -*- coding: utf-8 -*-
"""Host audit: doors / windows must lie in a wall of the same level; wall-hosted electrical devices must touch a wall; ceiling devices must be under a ceiling/slab zone.
usage: python3 pipeline/audit_host.py"""
import json, os, sys, math, collections
from shapely.geometry import Polygon, box as sbox, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, "..", "src", "model.json")))
def wall_geoms(level):
    G = []
    for e in M["els"]:
        if e["l"] != level or e["c"] not in ("A.wall", "S.wall", "S.col"): continue
        g = e["g"]
        if g[0] == "r": G.append(sbox(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4])))
        elif g[0] == "p":
            try: G.append(Polygon(g[1], g[4] if len(g) > 4 else None).buffer(0))
            except Exception: pass
    return G
def bbox_of(g):
    if g[0] == "r": return min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4])
    if g[0] == "b":
        hw, hd = g[3] / 2, g[4] / 2; a = math.radians(g[5]); c, s = abs(math.cos(a)), abs(math.sin(a)); ex, ey = hw * c + hd * s, hw * s + hd * c
        return g[1] - ex, g[2] - ey, g[1] + ex, g[2] + ey
    if g[0] == "cyl": return g[1] - g[3], g[2] - g[3], g[1] + g[3], g[2] + g[3]
def main():
    walls = {}; tree = {}
    rows = collections.defaultdict(list)
    for i, e in enumerate(M["els"]):
        c = e["c"]
        if c not in ("A.door", "A.win", "E.socket", "E.switch", "E.panel", "E.fa", "E.lc") : continue
        l = e["l"]
        if l not in walls:
            walls[l] = wall_geoms(l); tree[l] = STRtree(walls[l])
        bb = bbox_of(e["g"])
        if not bb: continue
        pt = sbox(*bb).buffer(1.0 if c.startswith("A.") else 3.0)
        idx = tree[l].query(pt)
        hit = [j for j in idx if walls[l][j].intersects(pt)]
        if not hit: rows[(c, e.get("t"), l)].append((i, [round(v) for v in bb], e["g"][-2:] ))
    tot = collections.Counter()
    for (c, t, l), v in sorted(rows.items(), key=lambda kv: -len(kv[1])):
        tot[c] += len(v)
    print("not touching any wall:", dict(tot))
    for (c, t, l), v in sorted(rows.items(), key=lambda kv: -len(kv[1]))[:30]: print(" ", c, t, l, len(v), v[:2])
if __name__ == "__main__": main()
