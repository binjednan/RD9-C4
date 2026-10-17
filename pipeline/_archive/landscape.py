# -*- coding: utf-8 -*-
"""Landscape data from the planting plan A2300 (ARCH2 'Arch. Drawings Part 2 31-58.pdf', page 19) -> data/landscape.json

The sheet is a portrait A4 page with the 1:100 plan turned 90 degrees (and drawn at ~1:370 to fit).  It is registered into model cm with the 12 square 60x60 C5 columns
(the black squares), which are on both A102 and STR p16:   x_cm = (Py - TX) / S0 ,   y_cm = 1810 - (-TY - Px) / S0     (P = PDF points)
(the y flip about the building mid-line resolves the symmetry of the column pattern; checked against A102: play area, planters, ramp text all land on the A102 positions).

Symbols (legend on the sheet):  tree = circle with a cross (radius = canopy),  shrub = 1-3 small circles with '+',  small circles r~12 = ground-cover / succulent plants.
Trees by canopy radius: 200 cm -> AZAD.I (Azadirachta indica, 5 pcs), 155-175 cm -> HIBI.T (Hibiscus tiliaceus, 14 pcs), 85 cm -> PLUM.O (Plumeria obtusa, 22 pcs):
the three counts equal the PLANTING SCHEDULE quantities (5 / 14 / 22), as do the shrub circles r25 (41) + r45 (14) = JATR.P 55.
Kids-play-area equipment (swing, spider-web swing, 3 sea-saws, trampoline, 3-slide set, 2 spring riders, go-round) and the 7-post shade-sail shed (A2305) are read off the same plan.
usage: python3 pipeline/landscape.py"""
import os, sys, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
S0 = 0.09035822247427902; TX = 108.94070499; TY = -268.08641183
PDFS = ["/Users/binqdair/Downloads/Arch. Drawings Part 2 31-58.pdf", "/home/user/c4-docs-privet/Arch. Drawings Part 2 31-58.pdf"]
def T(px, py): return ((py - TX) / S0, 1810 - ((-TY) - px) / S0)

def circles(pg):
    out = []
    for dr in pg.get_drawings():
        r = dr["rect"]; its = dr["items"]
        nc = sum(1 for i in its if i[0] == "c")
        if nc >= 4 and abs(r.width - r.height) < 0.6 and r.width > 2 and dr.get("fill") is None and len(its) <= 8:
            x, y = T((r.x0 + r.x1) / 2, (r.y0 + r.y1) / 2); out.append((r.width / 2 / S0, x, y))
    return out

def main():
    import fitz
    pdf = next((p for p in PDFS if os.path.exists(p)), None)
    if not pdf: sys.exit("A2300 sheet not found: " + ", ".join(PDFS))
    pg = fitz.open(pdf)[18]
    C = [(r, x, y) for r, x, y in circles(pg) if -60 <= x <= 4470 and -60 <= y <= 4470]
    L = {"trees": [], "shrubs": [], "small": [], "src": "A2300 PLANTING PLAN (ARCH2 p19) registered on the C5 columns"}
    for r, x, y in C:
        x, y = round(x), round(y)
        if 195 <= r <= 205: L["trees"].append({"sp": "AZAD.I", "x": x, "y": y, "r": 200})
        elif 150 <= r <= 175: L["trees"].append({"sp": "HIBI.T", "x": x, "y": y, "r": round(r)})
        elif 80 <= r <= 90: L["trees"].append({"sp": "PLUM.O", "x": x, "y": y, "r": round(r)})
        elif 22 <= r <= 28: L["shrubs"].append({"sp": "JATR.P", "x": x, "y": y, "r": 25})
        elif 43 <= r <= 48 and not (1000 < x < 2300 and 2300 < y < 3000): L["shrubs"].append({"sp": "JATR.P", "x": x, "y": y, "r": 45})
        elif 11 <= r <= 14: L["small"].append({"x": x, "y": y, "r": 12})
    # granite benches built into the planter walls: layer ADD-PLAN-PARAPET-5 of A102 holds ONLY the hatched BENCH pieces (7 of them) and the gazebo ring
    try:
        sys.path.insert(0, HERE)
        import lib, reg as R
        from shapely.geometry import LineString
        from shapely.ops import unary_union
        RG = json.load(open(os.path.join(HERE, "data", "reg_all.json"))); Tr = R.make_T(RG["ARCH1:5"])
        segs = []
        for dr in lib.doc("ARCH1")[4].get_drawings():
            if (dr.get("layer") or "") != "ADD-PLAN-PARAPET-5": continue
            for poly in lib.flat_path(dr):
                pts = [Tr(x, y) for x, y in poly]
                if len(pts) >= 2: segs.append(LineString(pts))
        U = unary_union([s_.buffer(7) for s_ in segs]).buffer(-5)
        L["benches"] = []
        for q in (list(U.geoms) if hasattr(U, "geoms") else [U]):
            if q.area < 3000 or q.area > 60000: continue
            q = q.simplify(4)
            L["benches"].append([[round(x), round(y)] for x, y in list(q.exterior.coords)[:-1]])
        print("benches:", len(L["benches"]))
    except Exception as ex:
        print("benches skipped:", ex)
    print("trees", collections.Counter(t["sp"] for t in L["trees"]), "| shrubs", len(L["shrubs"]), "| small plants", len(L["small"]))
    json.dump(L, open(os.path.join(HERE, "data", "landscape.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__": main()
