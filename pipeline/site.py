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
    # ================= v2: driveway, parking bays, markings, street, barrier gate, gazebo =================
    def rect(x0, y0, x1, y1): return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
    def add_el(c, kind, g, mat, mark, typ, attrs, stage=None, srcs=()):
        e = {"c": c, "l": "G", "g": g, "mark": mark, "t": typ, "m": mat, "a": attrs, "src": [SRC + " — " + kind] + list(srcs)}
        if stage: e["stage"] = stage
        els.append(e)
    TOP_DW = 0.10                                # 'F.F.L. +0.10 DRIVE WAY' written on the plan
    # drive way = 6 m between the two bay columns (x 3320..3920), from the street apron to the ramp junction
    DW = [(3320, -480, 3920, 3430, "ممر القيادة 6 م (النص «6 m WIDE DRIVE WAY»)"), (2770, 1870, 3320, 3330, "مواقف السيارات — العمود الأيسر"),
          (3920, 1710, 4471, 3330, "مواقف السيارات — العمود الأيمن العلوي"), (3920, 220, 4471, 1035, "مواقف السيارات — العمود الأيمن السفلي")]
    for k, (x0, y0, x1, y1, nm) in enumerate(DW, 1):
        add_el("A.site", nm, ["p", rect(x0, y0, x1, y1), -0.1, TOP_DW], "site_asphalt", f"ASPH-{k}", "site_asphalt",
               {"kind": "asphalt", "top_m": TOP_DW, "area_m2": round((x1 - x0) * (y1 - y0) / 1e4, 1),
                "level_note": "المنسوب +0.10 م = F.F.L. المكتوب للممر على المخطط",
                "finish_note": "مادة الطبقة النهائية (أسفلت) غير محددة على A102 — الأسفلت افتراض بناءً على طلب المشروع «الشارع المسفلت»"})
    # bay dividers: the exact y values come from the merged dashed lines of layer A-CAR (stall module 2.7 m)
    BAYS = [(2770, 3320, [1870, 2120, 2270, 2520, 2790, 3060, 3330], 2770), (3920, 4471, [1710, 1980, 2250, 2520, 2790, 3060, 3330], 4470),
            (3920, 4471, [220, 490, 760, 1030], 4470)]
    mk = 0
    def mark(poly, nm, kind="line"):
        nonlocal mk
        mk += 1
        add_el("A.site", nm, ["p", poly, TOP_DW, TOP_DW + 0.01], "site_mark", f"MARK-{mk:03d}", "site_mark", {"kind": "marking"})
    for x0, x1, ys, back in BAYS:
        for y in ys: mark(rect(x0, y - 5, x1, y + 5), "فاصل موقف (طبقة A-CAR)")
        mark(rect(back - 5, min(ys), back + 5, max(ys)), "خط خلفية المواقف (طبقة A-CAR)")
    # dashed centre line: filled rectangles x 3615..3626 of layer 0; direction arrows: filled shapes of the Road Marks / Arrow layers
    for d in sh.D:
        if not d.get("fill") or not d["polys"]: continue
        ly = d["layer"] or ""
        w = [sh.T(x, y) for x, y in d["polys"][0]]
        xs = [q[0] for q in w]; ys_ = [q[1] for q in w]
        if len(w) < 3: continue
        if ly == "0" and 3600 < min(xs) and max(xs) < 3640 and max(xs) - min(xs) < 20 and 90 < max(ys_) - min(ys_) < 140 and -100 < min(ys_) < 3400:
            mark([[round(a, 1), round(b, 1)] for a, b in w], "خط منتصف متقطع (طبقة 0)")
        elif ly.endswith("A-Road Marks") or ly.endswith("$Arrow"):
            mark([[round(a, 1), round(b, 1)] for a, b in w], "سهم اتجاه (طبقة " + ly.split("$")[-1] + ")")
    # ---- street in front of the plot (A100 site plan, registered to A102 by hatch matching, data/reg_p3.json)
    STREET = [(-1277, -1030, 6000, -480, "الشارع الجنوبي (حوافه من A100: y=-480 و y=-1030)"), (-1277, -480, -479, 4600, "الشارع الغربي (حوافه من A100: x=-1277 و x=-479)")]
    for k, (x0, y0, x1, y1, nm) in enumerate(STREET, 1):
        add_el("A.site", nm, ["p", rect(x0, y0, x1, y1), -0.25, 0.0], "site_asphalt", f"STREET-{k}", "site_asphalt",
               {"kind": "street", "top_m": 0.0, "level_note": "المنسوب ±0.00 م (R.L ±0.00 المكتوب عند المدخل)",
                "finish_note": "عرض الشارع من خطوط حافة الطريق في A100؛ مادة التشطيب غير محددة (أسفلت افتراض)"}, srcs=["ARCH1 ص3 (A100 مخطط الموقع 1:200) طبقة roadedge"])
    # ---- automatic barrier gate: two posts and two booms across the drive way (layer 'Appliances' of A102)
    for nm, (x0, y0, x1, y1, z0, z1) in (("عمود البوابة الأيسر", (3292, 1624, 3310, 1654, TOP_DW, 1.2)), ("عمود البوابة الأيمن", (3930, 1624, 3949, 1654, TOP_DW, 1.2)),
                                          ("ذراع الحاجز الأيسر", (3310, 1634, 3610, 1643, 1.0, 1.08)), ("ذراع الحاجز الأيمن", (3631, 1634, 3930, 1643, 1.0, 1.08))):
        add_el("A.rail", nm + " (بوابة الحاجز الآلي AUTOMATIC BARRIER GATE)", ["r", x0, y0, x1, y1, z0, z1], "frame_alu", "BARRIER-GATE", "barrier_gate",
               {"kind": "barrier_gate", "h_m": z1, "dim_note": "الأرتفاعات افتراضية — غير مذكورة على A102 (الموضع والأطوال من الرسم)"})
    # ---- circular shade (gazebo): octagon of layers LINEA-1/LINEA-2; heights are NOT in the documents -> stage item flagged as assumed
    xs = []; ys_ = []
    for a, b, c, d in sh.segments("LINEA-1"):
        xs += [a, c]; ys_ += [b, d]
    if xs:
        cx, cy, rr = (min(xs) + max(xs)) / 2, (min(ys_) + max(ys_)) / 2, (max(xs) - min(xs)) / 2
        oct_ = [[round(cx + rr * math.cos(math.radians(22.5 + 45 * i)), 1), round(cy + rr * math.sin(math.radians(22.5 + 45 * i)), 1)] for i in range(8)]
        add_el("A.stage", "مظلة دائرية ثمانية (طبقتا LINEA-1 وLINEA-2)", ["p", oct_, 2.8, 2.95], "site_shade", "SHADE-01", "site_shade",
               {"kind": "shade", "dia_cm": round(2 * rr), "assumed_h": 2.8, "dim_note": "القطر من الرسم؛ ارتفاع المظلة وسماكتها وأعمدتها غير مذكورة — افتراض يحتاج تأكيد"}, stage="shade")
        add_el("A.stage", "عمود المظلة الدائرية المركزي", ["cyl", round(cx, 1), round(cy, 1), 10, 0.2, 2.8], "site_shade", "SHADE-01-POLE", "site_shade",
               {"kind": "shade_pole", "dim_note": "افتراض هندسي — يحتاج تأكيد"}, stage="shade")
    out = {"spots": spots, "f15": f15, "els": els}
    json.dump(out, open(os.path.join(HERE, "data", "site.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("grass", ng, "paving", npv, "spots", len(spots), "f15 labels", len(f15), "elements", len(els))

if __name__ == "__main__":
    main()
