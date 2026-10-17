# -*- coding: utf-8 -*-
"""Review tool: draws the vector content of one drawing sheet (registered into model cm) together with the 3-D model's plan outline of one level,
so that a human (or the audit scripts) can see at a glance what the sheet shows that the model does not - and the other way round.

usage: python3 pipeline/overlay.py ARCH1:5 G out.png [x0 y0 x1 y1] [--layers REGEX] [--cats A.wall,S.col] [--nomodel] [--nosheet] [--dpi 90]
  * sheet lines  : grey / (layer name matches --layers: blue)
  * model        : red outlines per category (A.wall, S.col, S.wall, A.win, A.door, A.site, A.rail ...), filled light when --fill
"""
import sys, os, json, re, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection, PolyCollection
import lib, reg as R

COL = {"A.wall": "#d62728", "S.col": "#9467bd", "S.wall": "#8c564b", "A.win": "#17becf", "A.door": "#ff7f0e", "A.site": "#2ca02c", "A.rail": "#e377c2", "S.beam": "#7f7f7f",
       "A.fix": "#bcbd22", "A.clad": "#1f77b4", "S.stair": "#333333", "A.floor": "#cccccc", "A.ceil": "#aaaaaa", "A.stage": "#ff00ff"}

def ring_list(g):
    k = g[0]
    if k == "p": return [g[1]] + list(g[4] or []) if len(g) > 4 else [g[1]]
    if k == "r": return [[(g[1], g[2]), (g[3], g[2]), (g[3], g[4]), (g[1], g[4])]]
    if k == "b":
        import math
        x, y, W, D, a = g[1], g[2], g[3], g[4], math.radians(g[5]); c, s = math.cos(a), math.sin(a)
        return [[(x + dx * c - dy * s, y + dx * s + dy * c) for dx, dy in ((-W / 2, -D / 2), (W / 2, -D / 2), (W / 2, D / 2), (-W / 2, D / 2))]]
    if k == "cyl":
        import math
        return [[(g[1] + g[3] * math.cos(t / 12 * 6.2832), g[2] + g[3] * math.sin(t / 12 * 6.2832)) for t in range(12)]]
    return []

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("sheet"); ap.add_argument("level"); ap.add_argument("out"); ap.add_argument("bbox", nargs="*", type=float)
    ap.add_argument("--layers", default=None); ap.add_argument("--cats", default="A.wall,S.col,S.wall"); ap.add_argument("--nomodel", action="store_true"); ap.add_argument("--nosheet", action="store_true")
    ap.add_argument("--dpi", type=int, default=90); ap.add_argument("--size", type=float, default=14); ap.add_argument("--minz", type=float, default=None); ap.add_argument("--maxz", type=float, default=None)
    a = ap.parse_args()
    key, pg = a.sheet.split(":"); pg = int(pg)
    RG = json.load(open(os.path.join(HERE, "data", "reg_all.json"))); rg = RG.get(f"{key}:{pg}")
    T = R.make_T(rg) if rg else (lambda x, y: (x, y))
    bb = a.bbox if len(a.bbox) == 4 else [-300, -300, 4700, 4700]
    fig, ax = plt.subplots(figsize=(a.size, a.size * (bb[3] - bb[1]) / max(bb[2] - bb[0], 1)))
    if not a.nosheet:
        p = lib.doc(key)[pg - 1]; segs_g, segs_b = [], []; rx = re.compile(a.layers, re.I) if a.layers else None
        for dr in p.get_drawings():
            ly = dr.get("layer") or ""
            for poly in lib.flat_path(dr):
                pts = [T(x, y) for x, y in poly]
                if not any(bb[0] - 50 <= x <= bb[2] + 50 and bb[1] - 50 <= y <= bb[3] + 50 for x, y in pts): continue
                (segs_b if rx and rx.search(ly) else segs_g).append(pts)
        ax.add_collection(LineCollection(segs_g, colors="#999999", linewidths=0.35)); ax.add_collection(LineCollection(segs_b, colors="#1f4fff", linewidths=0.6))
    if not a.nomodel:
        M = json.load(open(os.path.join(HERE, "..", "src", "model.json"), encoding="utf-8")); cats = a.cats.split(",")
        for c in cats:
            rings = []
            for e in M["els"]:
                if e["l"] != a.level or e["c"] != c: continue
                if a.minz is not None or a.maxz is not None:
                    g = e["g"]; z0, z1 = (g[2], g[3]) if g[0] == "p" else ((g[5], g[6]) if g[0] == "r" else (g[6], g[7]) if g[0] == "b" else (g[4], g[5]) if g[0] == "cyl" else (None, None))
                    if z0 is None or (a.minz is not None and z1 < a.minz) or (a.maxz is not None and z0 > a.maxz): continue
                rings += [list(r) for r in ring_list(e["g"])]
            ax.add_collection(PolyCollection(rings, facecolors="none", edgecolors=COL.get(c, "#d62728"), linewidths=0.8))
    ax.set_xlim(bb[0], bb[2]); ax.set_ylim(bb[1], bb[3]); ax.set_aspect("equal"); ax.grid(True, lw=0.2, alpha=0.4)
    plt.tight_layout(); plt.savefig(a.out, dpi=a.dpi); print("saved", a.out)

if __name__ == "__main__": main()
