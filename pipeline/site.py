# -*- coding: utf-8 -*-
"""Site / ground-floor landscape extraction from ARCH1 p5 (A102 ground floor plan 1:100) -> pipeline/data/site.json

Needs the source PDF (see lib.py) so it is run on its own; pipeline/post_model.py merges site.json into src/model.json
(no PDF needed there).  Everything is derived from layers of the drawing:
  L1-THIN      grass hatch              -> site_grass   (top level from the nearest 'F.L.' spot level written on the plan)
  LAND - TILE  paving hatch             -> site_paving  (top +0.20, the 'F.F.L. +0.20' written on the plan);
                                           the component under the 'F15' label (KIDS PLAY AREA) = F15 rubber tile (A500)
Heights that are not written on the drawing are NOT invented: slopes between spot levels are not modelled (flat tops).
"""
import sys, os, json, math, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np, cv2
import lib

X0, Y1, R = -200.0, 4750.0, 5.0            # raster frame (cm), 5 cm per pixel
Xmax, Ymin = 4700.0, -300.0
W, H = int((Xmax - X0) / R), int((Y1 - Ymin) / R)

def to_px(x, y): return ((x - X0) / R, (Y1 - y) / R)
def to_cm(px, py): return (X0 + px * R, Y1 - py * R)

def raster(sh, layer, th=1):
    im = np.zeros((H, W), np.uint8)
    for pl, d in sh.polys(layer):
        pts = np.array([to_px(x, y) for x, y in pl], np.int32)
        if len(pts) >= 2:
            cv2.polylines(im, [pts], False, 255, th)
    return im

def fill(im, k=17, min_m2=2.0):
    c = cv2.morphologyEx(im, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    n, lab, st, _ = cv2.connectedComponentsWithStats((c > 0).astype(np.uint8), connectivity=8)
    keep = np.zeros_like(c)
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] * R * R / 1e4 >= min_m2:
            keep[lab == i] = 255
    return keep

def polygons(mask, eps_px=1.6):
    """mask -> list of (outer[[x,y]...], [holes...]) in cm"""
    cnts, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    out = []
    if hier is None: return out
    hier = hier[0]
    def conv(c):
        a = cv2.approxPolyDP(c, eps_px, True).reshape(-1, 2)
        return [[round(v, 1) for v in to_cm(px, py)] for px, py in a]
    for i, c in enumerate(cnts):
        if hier[i][3] != -1: continue          # holes handled with their parent
        outer = conv(c)
        if len(outer) < 3: continue
        holes = []
        j = hier[i][2]
        while j != -1:
            h = conv(cnts[j])
            if len(h) >= 3 and cv2.contourArea(cnts[j]) * R * R / 1e4 >= 0.5: holes.append(h)
            j = hier[j][0]
        out.append((outer, holes))
    return out

def poly_area(p):
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2

def point_in(pt, poly):
    x, y = pt; ins = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1:
            ins = not ins
    return ins

def main():
    sh = lib.Sheet("ARCH1", 5)
    SRC = "ARCH1 ص5 (A102 مسقط الطابق الأرضي 1:100)"
    # ---- spot levels written on the plan: 'F.L.' + '+1.05'
    ws = sh.words()
    spots = []
    for w in ws:
        if w["s"] == "F.L.":
            best = None
            for v in ws:
                if v["s"].startswith("+") or v["s"].startswith("-"):
                    try: val = float(v["s"])
                    except ValueError: continue
                    d = math.hypot(v["X"] - w["X"], v["Y"] - w["Y"])
                    if d < 120 and (best is None or d < best[0]): best = (d, val)
            if best: spots.append((w["X"], w["Y"], best[1]))
    f15 = [(w["X"], w["Y"]) for w in ws if w["s"] == "F15"]

    G = fill(raster(sh, "L1-THIN")); T = fill(raster(sh, "LAND - TILE"))
    # the play area is a wide blob joined to the paths by narrow necks: a ~2 m opening separates it, the blob under the F15 label is the play area
    play = np.zeros_like(T)
    if f15:
        op = cv2.morphologyEx(T, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (41, 41)))
        n, lab, st, _ = cv2.connectedComponentsWithStats((op > 0).astype(np.uint8), connectivity=8)
        px, py = to_px(*f15[0]); i = lab[int(py), int(px)]
        if i > 0:
            play = cv2.dilate(((lab == i) * 255).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))) & T
    # the blob also swallows the paved band in front of the building: cut it at the top edge of the grass strip that closes the play garden below
    gp = [(o, h) for o, h in polygons(G) if poly_area(o) / 1e4 < 40]
    if play.any() and gp:
        ys, xs = np.nonzero(play); bx0, bx1 = to_cm(xs.min(), 0)[0], to_cm(xs.max(), 0)[0]
        cand = [o for o, h in gp if min(p[0] for p in o) > bx0 and max(p[0] for p in o) < bx1 + 600]
        if cand:
            low = min(cand, key=lambda o: min(p[1] for p in o))
            cut_y = max(p[1] for p in low)
            play[int((Y1 - cut_y) / R):, :] = 0
    T_other = cv2.morphologyEx(T & ~play, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    els = []
    def add(kind, outer, holes, z0, z1, mat, mark, typ, attrs, extra_src=()):
        els.append({"c": "A.site", "l": "G", "g": ["p", outer, z0, z1] + ([holes] if holes else []), "mark": mark, "t": typ, "m": mat,
                    "a": attrs, "src": [SRC + " — " + kind] + list(extra_src)})
    ng = 0
    for outer, holes in polygons(G):
        if poly_area(outer) / 1e4 < 2.0: continue
        near = [s for s in spots if point_in((s[0], s[1]), outer) or any(math.hypot(s[0] - p[0], s[1] - p[1]) < 400 for p in outer[::3])]
        if near:
            vals = sorted(s[2] for s in near); top = vals[len(vals) // 2]; note = f"المنسوب {top:+.2f} م من نقاط F.L. المكتوبة على المخطط ({len(near)} نقطة قريبة)"
        else:
            top = 0.2; note = "لا توجد نقطة منسوب قريبة: رُسم بمنسوب +0.20 م (F.F.L. المدخل) — افتراض يحتاج تأكيد"
        ng += 1
        add("هاتش العشب (طبقة L1-THIN)", outer, holes, -0.1, round(top, 2), "site_grass", f"GRASS-{ng:02d}", "site_grass",
            {"kind": "grass", "top_m": round(top, 2), "level_note": note, "area_m2": round((poly_area(outer) - sum(poly_area(h) for h in holes)) / 1e4, 1)})
    npv = 0
    for outer, holes in polygons(T_other):
        if poly_area(outer) / 1e4 < 2.0: continue
        npv += 1
        ar = round((poly_area(outer) - sum(poly_area(h) for h in holes)) / 1e4, 1)
        add("هاتش الرصف (طبقة LAND - TILE)", outer, holes, -0.1, 0.2, "site_paving", f"PAVING-{npv:02d}", "site_paving",
            {"kind": "paving", "top_m": 0.2, "area_m2": ar, "level_note": "المنسوب +0.20 م = F.F.L. المكتوب على المخطط",
             "finish_note": "نوع الرصف غير محدد على A102 (A500 يذكر F12/F13/F14) — بانتظار تأكيدك"})
    for outer, holes in polygons(play):
        if poly_area(outer) / 1e4 < 2.0: continue
        ar = round((poly_area(outer) - sum(poly_area(h) for h in holes)) / 1e4, 1)
        add("هاتش الرصف (طبقة LAND - TILE) تحت وسم F15 (منطقة ألعاب الأطفال)", outer, holes, -0.1, 0.2, "site_rubber", "F15-01", "site_rubber",
            {"kind": "play_area", "fin": ["F15"], "top_m": 0.2, "area_m2": ar, "level_note": "المنسوب +0.20 م = F.F.L. المكتوب على المخطط"})
    out = {"spots": spots, "f15": f15, "els": els}
    json.dump(out, open(os.path.join(HERE, "data", "site.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("grass", ng, "paving", npv, "spots", len(spots), "f15 labels", len(f15), "elements", len(els))

if __name__ == "__main__":
    main()
