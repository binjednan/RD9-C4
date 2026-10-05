# -*- coding: utf-8 -*-
"""Column audit: for every level compare the model's S.col / S.wall plan footprints with the closed S-COLUMN outlines of the structural column-layout sheet of that level
(STR p15 basement, p16 ground, p17 typical 1-5, p18 roof, p19 top roof) registered into model cm.
Reports  - model columns without a sheet outline (wrong place / invented),
         - sheet outlines without a model column (missing),
         - nested / doubled columns inside the model (an outline drawn twice: the 40 mm cover line of the reinforcement cage is also an S-COLUMN outline).
usage: python3 pipeline/audit_cols.py"""
import sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from shapely.geometry import Polygon
import lib, reg as R
PAGE_OF = {"B": 15, "G": 16, "1": 17, "2": 17, "3": 17, "4": 17, "5": 17, "R": 18, "T": 19}

def sheet_outlines(pg):
    RG = json.load(open(os.path.join(HERE, "data", "reg_all.json"))); T = R.make_T(RG[f"STR:{pg}"])
    out = []
    for dr in lib.doc("STR")[pg - 1].get_drawings():
        if (dr.get("layer") or "") != "S-COLUMN": continue
        for poly in lib.flat_path(dr):
            pts = [T(x, y) for x, y in poly]
            if len(pts) < 4: continue
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            if min(xs) < -120 or max(xs) > 4600 or min(ys) < -120 or max(ys) > 4600: continue
            P = Polygon(pts).buffer(0)
            if P.is_empty or P.area < 150 or P.area > 2e5: continue
            out.append(P)
    return out

def cover_lines(polys):
    """outlines that sit inside another outline with a uniform small inset (= the reinforcement cage line) -> returned as (inner_idx, outer_idx)"""
    res = []
    for i, p in enumerate(polys):
        for j, q in enumerate(polys):
            if i != j and q.area > p.area * 1.02 and q.buffer(1.0).contains(p) and q.exterior.hausdorff_distance(p.exterior) <= 12: res.append((i, j))
    return res

if __name__ == "__main__":
    M = json.load(open(os.path.join(HERE, "..", "src", "model.json"), encoding="utf-8"))
    import support as S
    done = {}
    for lv in ("B", "G", "1", "3", "R", "T"):
        pg = PAGE_OF[lv]
        if pg not in done: done[pg] = sheet_outlines(pg)
        so = done[pg]; cov = cover_lines(so); inner = {i for i, _ in cov}
        real = [p for k, p in enumerate(so) if k not in inner]
        mod = [(e["id"], S.poly_of(e["g"])) for e in M["els"] if e["l"] == lv and e["c"] in ("S.col", "S.wall") and e["g"][0] in ("p", "r")]
        extra = [i for i, p in mod if not any(p.centroid.distance(q.centroid) < 6 and abs(p.area - q.area) < 0.35 * q.area for q in real)]
        miss = [q for q in real if not any(p.centroid.distance(q.centroid) < 6 for _, p in mod)]
        print(f"{lv:2} sheet p{pg}: outlines {len(so)} (cage-cover lines {len(inner)}) real {len(real)} | model cols+walls {len(mod)} | model without sheet outline {len(extra)} | sheet outline without model {len(miss)}")
        for i in extra[:40]: print("    extra :", i)
        for q in miss[:20]: print("    missing at", round(q.centroid.x), round(q.centroid.y), "area", round(q.area))
