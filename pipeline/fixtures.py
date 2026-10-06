# -*- coding: utf-8 -*-
"""Interior fixed fixtures of the flats and toilets, placed where the approved plans draw them (data/fixtures.json <- pipeline/fixtures_extract.py) and shaped by the approved details:

  sanitary ware  (P.fix)   WC, vanity counter + basin + tap + towel bar + mirror, built-in bath tub + mixer + shower          A1200-A1203 (ARCH2 p19-22), plans A102-A105
  kitchens       (A.fix)   base units, granite worktop, sink, wall units, electrical hood, ceramic splash, bar counter       A1204 K1-K6 (ARCH2 p23), plans A103 / A104
  appliances     (A.stage) cooker, fridge, washing machine -- 'not included in the tenders' (A1204 note) so staged, hide-able
  wardrobes      (A.fix)   WR1..WR7 wood frame, varnish, 4 equal panels, full height to the false ceiling                      A1300 (ARCH2 p25)

Plan symbols give the position and footprint; the approved sections give the heights (bath: tub rim +0.50, WC bowl +0.40, counter top +0.95, mirror 120 x 100 at +1.15; kitchen: plinth 10, base 75,
worktop 20 mm at +0.85..0.87, wall units 60 high with the top 20 below the false ceiling +2.40, ceramic splash between).  Brand, model, cabinet colour and granite colour are NOT in the documents:
they are flagged as assumptions (cards) and kept neutral.  Everything is regenerated on every post_model run (ids end -Xnnnn)."""
import os, json, math
from shapely.geometry import Polygon, box, Point, LineString
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
ZF = 0.012                       # finished floor (tile 12 mm): fixtures stand on it
PLAN_LEVELS = {"typ": ["2", "3", "4", "5"], "1": ["1"], "G": ["G"], "R": ["R"]}

SRC_BATH = ["ARCH2 ص22 (A1203 تفاصيل الحمامات 04: مقطعان، مغسلة تحت السطح، WC)", "ARCH2 ص19–21 (A1200–A1202 تفاصيل الحمامات)", "ARCH1 ص6–7 (A103 / A104 المساقط: رموز الأجهزة)"]
SRC_KIT = ["ARCH2 ص23 (A1204 تفاصيل المطابخ K1–K6: مساقط ومقاطع S01–S12)", "ARCH2 ص24 (A1205)", "ARCH1 ص6–7 (A103 / A104 المساقط)"]
SRC_WR = ["ARCH2 ص25 (A1300 جدول الدواليب WR1–WR7 ومساقطها)", "ARCH2 ص26 (A1301 / A1302 مقاطع الدواليب)", "ARCH1 ص6–7 (A103 / A104 المساقط)"]

MATS = {
    "san_porcelain": {"name": "خزف صحي أبيض لامع (مرحاض / مغسلة / بانيو)", "color": "#f4f4f0", "rough": 0.12, "metal": 0.0, "code": "A1203"},
    "san_chrome": {"name": "كروم مصقول — خلاطات وإكسسوارات الحمام", "color": "#d9dde0", "metal": 0.5, "rough": 0.25, "code": "A1203"},
    "bath_mirror": {"name": "مرآة شفافة سماكة 6 مم", "color": "#c3d8e2", "metal": 0.25, "rough": 0.06, "code": "A1203"},
    "marble_gray": {"name": "رخام Armani Gray — سطح مغسلة سماكة 3 سم", "color": "#7e8184", "rough": 0.22, "code": "A1203"},
    "tub_tile": {"name": "سيراميك جداري/أرضي لمحيط البانيو (حسب جدول التشطيبات)", "color": "#d9d6ce", "rough": 0.35, "code": "A1203"},
    "granite_nat": {"name": "جرانيت طبيعي 20 مم — سطح المطبخ (اللون بانتظار تأكيدك)", "color": "#46484c", "rough": 0.3, "code": "A1204"},
    "kit_cabinet": {"name": "خزائن المطبخ — واجهات وهياكل (التشطيب واللون بانتظار تأكيدك)", "color": "#d8d3c9", "rough": 0.5, "code": "A1204"},
    "kit_kick": {"name": "قاعدة الخزائن (سقف القدم 10 سم)", "color": "#3b3d41", "rough": 0.7, "code": "A1204"},
    "kit_handle": {"name": "مقابض ستانلس ستيل مصقول (ملاحظة A1204)", "color": "#d0d4d8", "metal": 0.45, "rough": 0.35, "code": "A1204"},
    "kit_steel": {"name": "ستانلس ستيل — حوض وشفاط المطبخ", "color": "#c4c9ce", "metal": 0.4, "rough": 0.35, "code": "A1204"},
    "splash_ceramic": {"name": "سيراميك جداري 30×60 — خلفية المطبخ (حسب الجدول)", "color": "#e6e3da", "rough": 0.3, "code": "A1204"},
    "wood_varnish": {"name": "خشب مطلي ورنيش أملس — دواليب WR (A1300)", "color": "#a97d55", "rough": 0.45, "code": "A1300"},
    "wood_gap": {"name": "فواصل ألواح الدولاب", "color": "#4a3526", "rough": 0.8, "code": "A1300"},
    "app_white": {"name": "جهاز منزلي أبيض (للعرض، غير مشمول بالعقد)", "color": "#ecebe7", "rough": 0.35, "code": "A1204"},
    "app_steel": {"name": "جهاز منزلي ستانلس (للعرض، غير مشمول بالعقد)", "color": "#c9cdd1", "metal": 0.35, "rough": 0.4, "code": "A1204"},
    "app_dark": {"name": "زجاج/لوحة داكنة لجهاز منزلي", "color": "#26282b", "rough": 0.2, "code": "A1204"},
}

WR_CODE = {220: "WR1", 200: "WR2", 190: "WR3", 180: "WR4", 170: "WR5", 120: "WR6", 110: "WR7"}
WR_QTY = {"WR1": "الأول 4 + النموذجي 16 = 20", "WR2": "1 + 4 = 5", "WR3": "1 + 4 = 5", "WR4": "2 (الأول، ردهة)", "WR5": "2 + 16 (الجدول يذكر المجموع 20)", "WR6": "3 + 12 = 15", "WR7": "1 + 4 = 5 (الجدول يكرّر الرمز WR6 للمقاس 110×50)"}


# ------------------------------------------------------------------------------------------------------------------------ geometry helpers
def _r(v): return round(v, 1)


class Fr:
    """local frame of a fixture: origin = back-centre on the wall, x = t (along the wall), y = n (out of the wall), z absolute from the floor finish"""
    def __init__(self, base, n, z0):
        self.b = base; self.n = (float(n[0]), float(n[1])); self.t = (self.n[1], -self.n[0]); self.z0 = z0
        self.rot = math.degrees(math.atan2(self.t[1], self.t[0]))

    def pt(self, x, y): return (self.b[0] + self.t[0] * x + self.n[0] * y, self.b[1] + self.t[1] * x + self.n[1] * y)

    def box(self, x, y, w, d, za, zb):
        cx, cy = self.pt(x, y)
        return ["b", _r(cx), _r(cy), _r(w), _r(d), round(self.rot, 2), round(self.z0 + za, 3), round(self.z0 + zb, 3)]

    def cyl(self, x, y, r, za, zb):
        cx, cy = self.pt(x, y)
        return ["cyl", _r(cx), _r(cy), _r(r), round(self.z0 + za, 3), round(self.z0 + zb, 3)]

    def _ring(self, pts): return [[_r(self.pt(x, y)[0]), _r(self.pt(x, y)[1])] for x, y in pts]

    def prism(self, pts, za, zb, hole=None):
        g = ["p", self._ring(pts), round(self.z0 + za, 3), round(self.z0 + zb, 3)]
        if hole: g.append([self._ring(hole)])
        return g

    def tube(self, pts, dia):
        out = []
        for x, y, z in pts:
            X, Y = self.pt(x, y); out.append([_r(X), _r(Y), round(self.z0 + z, 3)])
        return ["t", out, dia]


def ell(cx, cy, rx, ry, n=24):
    return [(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n)) for k in range(n)]


def rrect(cx, cy, w, d, r, seg=3):
    r = min(r, w / 2 - 0.1, d / 2 - 0.1)
    out = []
    for (sx, sy, a0) in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        ccx, ccy = cx + sx * (w / 2 - r), cy + sy * (d / 2 - r)
        for k in range(seg + 1):
            a = math.radians(a0 + 90.0 * k / seg)
            out.append((ccx + r * math.cos(a), ccy + r * math.sin(a)))
    return out


def rect_pts(cx, cy, w, d): return [(cx - w / 2, cy - d / 2), (cx + w / 2, cy - d / 2), (cx + w / 2, cy + d / 2), (cx - w / 2, cy + d / 2)]


def _foot(g):
    k = g[0]
    try:
        if k == "p":
            holes = [h for h in (g[4] if len(g) > 4 and g[4] else []) if len(h) >= 3]
            p = Polygon(g[1], holes); return p if p.is_valid else p.buffer(0)
        if k == "r": return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4]))
        if k == "b":
            from shapely.affinity import rotate
            return rotate(box(g[1] - g[3] / 2, g[2] - g[4] / 2, g[1] + g[3] / 2, g[2] + g[4] / 2), g[5], origin=(g[1], g[2]))
    except Exception:
        return None
    return None


def _E(c, lv, g, t, m, mark, a, src, grp, u=None, stage=None):
    e = {"c": c, "l": lv, "g": g, "mark": mark, "t": t, "m": m, "a": a, "src": src, "grp": grp}
    if u: e["u"] = u
    if stage: e["stage"] = stage
    return e


# ------------------------------------------------------------------------------------------------------------------------ sanitary ware
def wc(fr, ctx):
    """close-coupled WC: bowl rim +0.40 (A1203 'WC detail'), cistern 38 x 20 on the wall, closed lid, hand spray holder (A1203 legend)"""
    P = "P.fix"; A = {"kind": "مرحاض أرضي بخزان ملاصق", "size_cm": "38 × 68"}
    out = []
    def add(g, m, part, t="san_wc"): out.append((P, g, t, m, "WC", dict(A, part=part)))
    add(fr.box(0, 10, 38, 20, 0.40, 0.82), "san_porcelain", "الخزان")
    add(fr.box(0, 10, 14, 5, 0.82, 0.835), "san_chrome", "زر التنظيف")
    add(fr.prism(ell(0, 36, 12, 17), 0.0, 0.28), "san_porcelain", "قاعدة الحوض")
    add(fr.prism(ell(0, 40, 15.5, 24), 0.28, 0.36), "san_porcelain", "جسم الحوض")
    add(fr.prism(ell(0, 41.5, 18.5, 27.5), 0.36, 0.43), "san_porcelain", "الحوض والمقعد")
    add(fr.box(26, 2, 3.5, 4, 0.48, 0.60), "san_chrome", "حامل الدش اليدوي (A1203: WATER HOSE & HAND SPRAY)", "san_accessory")
    add(fr.box(-27, 4, 6, 8, 0.70, 0.78), "san_chrome", "حامل ورق التواليت (A1203)", "san_accessory")
    return out


def vanity(fr, w, d, basins, ctx):
    """wall-hung marble counter 3 cm (top +0.95, apron to +0.85) with an under-counter basin (A1203 section 2 / 'undercounter wash basin detail'), tap, towel bar, mirror 120 x 100 at +1.15"""
    out = []
    A = {"kind": "مغسلة تحت سطح رخام", "size_cm": f"{round(w)} × {round(d)}"}
    off = basins[0] if basins else 0.0
    hole = ell(off, d / 2 + 1, 22.0, 17.0, 20)
    out.append(("A.fix", fr.prism(rect_pts(0, d / 2, w, d), 0.92, 0.95, hole), "san_vanity_top", "marble_gray", "سطح مغسلة", dict(A, part="سطح الرخام 3 سم")))
    ring_out = rect_pts(0, d / 2 - 1.5, w, d - 3)
    ring_in = rect_pts(0, d / 2 - 1.5, w - 6, d - 9)
    out.append(("A.fix", fr.prism(ring_out, 0.85, 0.92, ring_in), "san_vanity_top", "marble_gray", "سطح مغسلة", dict(A, part="حافة السطح (إطار)")))
    out.append(("P.fix", fr.prism(ell(off, d / 2 + 1, 23.5, 18.5, 20), 0.55, 0.92, ell(off, d / 2 + 1, 21.8, 16.8, 20)), "san_basin", "san_porcelain", "مغسلة", dict(A, part="حوض المغسلة")))
    out.append(("P.fix", fr.prism(ell(off, d / 2 + 1, 21.8, 16.8, 20), 0.55, 0.58), "san_basin", "san_porcelain", "مغسلة", dict(A, part="قاع الحوض")))
    out.append(("P.fix", fr.tube([(off, 6, 0.95), (off, 6, 1.13), (off, 15, 1.13), (off, 15, 1.08)], 2.4), "san_tap", "san_chrome", "خلاط", dict(A, part="خلاط المغسلة")))
    xl, xr = off - 31, off + 31
    out.append(("P.fix", fr.tube([(xl, d - 4, 0.70), (xl, d + 4, 0.70), (xr, d + 4, 0.70), (xr, d - 4, 0.70)], 2.0), "san_accessory", "san_chrome", "حامل مناشف", dict(A, part="حامل مناشف (A1203: TOWEL BAR)")))
    mw = min(120.0, w - 6)
    out.append(("A.fix", fr.box(off if abs(off) < w / 2 - mw / 2 + 0.01 else 0, 0.7, mw, 0.8, 1.15, 2.15), "bath_mirror", "bath_mirror", "مرآة", dict(A, size_cm=f"{round(mw)} × 100 × 0.8", part="مرآة شفافة 6 مم")))
    return out


def basin_wall(fr, w, d, ctx):
    out = []
    A = {"kind": "مغسلة جدارية بيضاوية", "size_cm": f"{round(w)} × {round(d)}"}
    out.append(("P.fix", fr.prism(ell(0, 22, min(w, 56) / 2 - 3, 20, 20), 0.80, 0.90, ell(0, 22, min(w, 56) / 2 - 5.5, 17.5, 20)), "san_basin", "san_porcelain", "مغسلة", dict(A, part="الحوض")))
    out.append(("P.fix", fr.prism(ell(0, 22, min(w, 56) / 2 - 5.5, 17.5, 20), 0.80, 0.83), "san_basin", "san_porcelain", "مغسلة", dict(A, part="القاع")))
    out.append(("P.fix", fr.tube([(0, 5, 0.90), (0, 5, 1.04), (0, 13, 1.04), (0, 13, 1.0)], 2.4), "san_tap", "san_chrome", "خلاط", dict(A, part="خلاط")))
    out.append(("A.fix", fr.box(0, 0.7, 60, 0.8, 1.20, 2.00), "bath_mirror", "bath_mirror", "مرآة", dict(A, size_cm="60 × 80 × 0.8", part="مرآة شفافة 6 مم (A1203: عرض 60 سم مع إنارة أعلاها)")))
    return out


def tub(c, L, W, ax, tap, z0):
    """built-in tub: tiled apron to +0.485, white shell rim at +0.50 (A1203 sections: rim 50 cm), stepped bowl, mixer + shower rail at the tap end"""
    sgn = tap if tap in (1, -1) else 1
    axis = (0.0, 1.0) if ax == "y" else (1.0, 0.0)
    base = (c[0] + axis[0] * sgn * L / 2, c[1] + axis[1] * sgn * L / 2)
    n = (-axis[0] * sgn, -axis[1] * sgn)                   # from the tap end towards the foot
    fr = Fr(base, n, z0)
    A = {"kind": "بانيو مدمج بكسوة سيراميك", "size_cm": f"{round(W)} × {round(L)}"}
    out = []
    ro = rrect(0, L / 2, W, L, 3, 2); ri = rrect(0, L / 2, W - 8, L - 8, 6, 3)
    out.append(("P.fix", fr.prism(ro, 0.0, 0.485, ri), "san_tub", "tub_tile", "بانيو", dict(A, part="محيط البانيو المكسو بالسيراميك")))
    out.append(("P.fix", fr.prism(ri, 0.30, 0.50, rrect(0, L / 2, W - 20, L - 20, 10, 3)), "san_tub", "san_porcelain", "بانيو", dict(A, part="حافة البانيو (منسوب +0.50)")))
    out.append(("P.fix", fr.prism(ri, 0.14, 0.30, rrect(0, L / 2, W - 30, L - 34, 12, 3)), "san_tub", "san_porcelain", "بانيو", dict(A, part="جسم البانيو")))
    out.append(("P.fix", fr.prism(rrect(0, L / 2, W - 30, L - 34, 12, 3), 0.12, 0.14), "san_tub", "san_porcelain", "بانيو", dict(A, part="قاع البانيو")))
    out.append(("P.fix", fr.box(0, 2.5, 16, 5, 0.74, 0.80), "san_tap", "san_chrome", "خلاط", dict(A, part="خلاط البانيو")))
    out.append(("P.fix", fr.tube([(0, 3, 0.76), (0, 13, 0.76), (0, 13, 0.70)], 2.4), "san_tap", "san_chrome", "خلاط", dict(A, part="صنبور البانيو")))
    out.append(("P.fix", fr.tube([(0, 1.5, 1.05), (0, 1.5, 1.95), (0, 9, 1.95)], 2.0), "san_shower", "san_chrome", "دش", dict(A, part="عمود الدش (A1203: SHOWER)")))
    out.append(("P.fix", fr.cyl(0, 10, 5.0, 1.93, 1.96), "san_shower", "san_chrome", "دش", dict(A, part="رأس الدش")))
    return out


# ------------------------------------------------------------------------------------------------------------------------ wardrobes
def wardrobe(fr, w, d, h, code):
    out = []
    A = {"kind": f"دولاب {code} — إطار خشبي بتشطيب ورنيش أملس", "size_cm": f"{w} × {d} × {round(h * 100)}"}
    out.append(("A.fix", fr.box(0, d / 2 - 0.9, w - 0.4, d - 1.8, 0.0, h), "wardrobe_wr", "wood_gap", code, dict(A, part="هيكل الدولاب")))
    pw = (w - 0.4) / 4
    for k in range(4):
        x = -(w - 0.4) / 2 + pw * (k + 0.5)
        out.append(("A.fix", fr.box(x, d - 0.9, pw - 0.8, 1.8, 0.04, h - 0.04), "wardrobe_wr", "wood_varnish", code, dict(A, part=f"لوح {k + 1} من 4 (A1300: 4 X EQ. PANELS)")))
    for k in (1, 2, 3):
        x = -(w - 0.4) / 2 + pw * k
        out.append(("A.fix", fr.box(x + (3.0 if k != 2 else -3.0), d + 0.6, 1.6, 1.6, 0.95, 1.15), "wardrobe_wr", "wood_gap", code, dict(A, part="مقبض")))
    return out


# ------------------------------------------------------------------------------------------------------------------------ kitchens
def split_span(s0, s1, target=45.0, lo=34.0, hi=62.0):
    L = s1 - s0
    if L < 14: return []
    n = max(1, round(L / target))
    while L / n > hi: n += 1
    while n > 1 and L / n < lo: n -= 1
    w = L / n
    return [(s0 + i * w, s0 + (i + 1) * w) for i in range(n)]


def _segbox(a, u, wn, s0, s1, q0, q1, z0, z1):
    s, q = (s0 + s1) / 2, (q0 + q1) / 2
    cx, cy = a[0] + u[0] * s + wn[0] * q, a[1] + u[1] * s + wn[1] * q
    return ["b", _r(cx), _r(cy), _r(s1 - s0), _r(q1 - q0), round(math.degrees(math.atan2(u[1], u[0])), 2), round(z0, 3), round(z1, 3)]


def kitchen(k, z0, win_u, fcl):
    """returns [(cat, geom, type, mat, mark, attrs)], plus appliance entries with cat 'A.stage'"""
    out = []
    A = {"kind": "مطبخ"}
    base_polys = [Polygon(r) for r in k["base"]]
    base_u = unary_union(base_polys) if base_polys else None
    items = k["items"]
    cooker = next((i for i in items if i["k"] == "cooker"), None)
    washer = next((i for i in items if i["k"] == "washer"), None)
    sink = next((i for i in items if i["k"] == "sink"), None)
    fridge = next((i for i in items if i["k"] == "fridge"), None)

    def item_rect(it, w_along, d_deep):
        n = it["n"]; c = it["c"]; t = (n[1], -n[0])
        pts = [(c[0] + t[0] * a + n[0] * b, c[1] + t[1] * a + n[1] * b) for a, b in ((-w_along / 2, -d_deep / 2), (w_along / 2, -d_deep / 2), (w_along / 2, d_deep / 2), (-w_along / 2, d_deep / 2))]
        return Polygon(pts)

    ck_poly = item_rect(cooker, 90.0, 60.0) if cooker and cooker.get("n") else None
    wa_poly = item_rect(washer, 60.0, 60.0) if washer and washer.get("n") else None
    sk_poly = item_rect(sink, 120.0, 60.0) if sink and sink.get("n") else None
    solid = base_u
    if base_u is not None:
        cut = [p for p in (ck_poly, wa_poly) if p is not None]
        solid = base_u.difference(unary_union(cut).buffer(0.2)) if cut else base_u
    # --- base carcass, toe kick, worktop
    if solid is not None and not solid.is_empty:
        for q in (list(solid.geoms) if hasattr(solid, "geoms") else [solid]):
            if q.geom_type != "Polygon" or q.area < 60: continue
            ring = [[_r(x), _r(y)] for x, y in list(q.exterior.coords)[:-1]]
            out.append(("A.fix", ["p", ring, round(z0 + 0.10, 3), round(z0 + 0.85, 3)], "kit_base", "kit_cabinet", "خزائن سفلية", dict(A, part="هيكل الخزائن (قاعدة 10 + وحدة 75 سم)", size_cm="عمق 60 × ارتفاع 85")))
            kick = q.buffer(-4.0, join_style=2)
            for kq in (list(kick.geoms) if hasattr(kick, "geoms") else [kick]):
                if kq.is_empty or kq.geom_type != "Polygon" or kq.area < 60: continue
                out.append(("A.fix", ["p", [[_r(x), _r(y)] for x, y in list(kq.exterior.coords)[:-1]], round(z0, 3), round(z0 + 0.10, 3)], "kit_kick", "kit_kick", "قاعدة الخزائن", dict(A, part="سقف القدم (تراجع 4 سم)")))
    tops = []
    if base_u is not None:
        tops.append(base_u.buffer(1.5, join_style=2))
    for b in k.get("bars", []):
        try:
            bp = Polygon(b); bp = bp if bp.is_valid else bp.buffer(0)
        except Exception:
            continue
        ring = [[_r(x), _r(y)] for x, y in list(bp.exterior.coords)[:-1]]
        out.append(("A.fix", ["p", ring, round(z0 + 0.10, 3), round(z0 + 0.85, 3)], "kit_base", "kit_cabinet", "خزانة بار", dict(A, part="طاولة البار (من المسقط)", size_cm="عمق 60")))
        tops.append(bp.buffer(1.5, join_style=2))
    if tops:
        top = unary_union(tops)
        if ck_poly is not None: top = top.difference(ck_poly.buffer(0.2))
        if sk_poly is not None: top = top.difference(sk_poly)
        for q in (list(top.geoms) if hasattr(top, "geoms") else [top]):
            if q.geom_type != "Polygon" or q.area < 60: continue
            g = ["p", [[_r(x), _r(y)] for x, y in list(q.exterior.coords)[:-1]], round(z0 + 0.85, 3), round(z0 + 0.87, 3)]
            hs = [[[_r(x), _r(y)] for x, y in list(h.coords)[:-1]] for h in q.interiors]
            if hs: g.append(hs)
            out.append(("A.fix", g, "kit_top", "granite_nat", "سطح المطبخ", dict(A, part="جرانيت طبيعي 20 مم (A1204)", size_cm="سماكة 2")))
    # --- sink
    if sink and sk_poly is not None:
        n = sink["n"]; c = sink["c"]
        fr = Fr((c[0] - n[0] * 30, c[1] - n[1] * 30), n, z0)
        S = {"kind": "حوض مطبخ ستانلس بحوضين", "size_cm": "120 × 60"}
        plate = rect_pts(0, 30, 119, 59)
        h1 = rrect(-30, 30, 42, 46, 3, 2); h2 = rrect(13, 30, 42, 46, 3, 2)
        out.append(("A.fix", ["p", fr._ring(plate), round(z0 + 0.865, 3), round(z0 + 0.875, 3), [fr._ring(h1), fr._ring(h2)]], "kit_sink", "kit_steel", "حوض المطبخ", dict(S, part="إطار الحوض ولوح التجفيف")))
        for hx in (-30, 13):
            out.append(("A.fix", fr.prism(rrect(hx, 30, 44, 48, 3, 2), 0.64, 0.875, rrect(hx, 30, 41.2, 45.2, 3, 2)), "kit_sink", "kit_steel", "حوض المطبخ", dict(S, part="حوض")))
            out.append(("A.fix", fr.prism(rrect(hx, 30, 41.2, 45.2, 3, 2), 0.64, 0.655), "kit_sink", "kit_steel", "حوض المطبخ", dict(S, part="قاع الحوض")))
        out.append(("A.fix", fr.tube([(-8, 7, 0.875), (-8, 7, 1.10), (-8, 22, 1.10), (-8, 22, 1.03)], 2.6), "kit_sink", "san_chrome", "خلاط المطبخ", dict(S, part="خلاط الحوض")))
    # --- segments: modules, handles, wall units, splash
    win_ext = win_u.buffer(6) if win_u is not None and not win_u.is_empty else None
    segs = []
    if base_u is not None:
        for front in k["fronts"]:
            pts = [tuple(p) for p in front]
            for a, b in zip(pts[:-1], pts[1:]):
                L = math.hypot(b[0] - a[0], b[1] - a[1])
                if L < 20: continue
                u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L); nl = (-u[1], u[0]); mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                wn = None
                for sg in (1, -1):
                    if base_u.buffer(0.3).contains(Point(mid[0] + sg * nl[0] * 30, mid[1] + sg * nl[1] * 30)): wn = (sg * nl[0], sg * nl[1])
                if wn is None: continue
                segs.append({"a": a, "b": b, "u": u, "wn": wn, "L": L})
    def span_of(seg, poly):
        """[s0, s1] of a polygon along the segment when it sits on it, else None"""
        if poly is None: return None
        a, u, wn = seg["a"], seg["u"], seg["wn"]
        pts = list(poly.exterior.coords)
        ss = [((x - a[0]) * u[0] + (y - a[1]) * u[1]) for x, y in pts]; qq = [((x - a[0]) * wn[0] + (y - a[1]) * wn[1]) for x, y in pts]
        if max(qq) < 5 or min(qq) > 70 or max(ss) < 2 or min(ss) > seg["L"] - 2: return None
        return (min(ss), max(ss))
    for sg in segs:
        a, u, wn, L = sg["a"], sg["u"], sg["wn"], sg["L"]
        free = [(0.0, L)]
        for poly in (ck_poly, wa_poly):
            sp = span_of(sg, poly)
            if sp is None: continue
            nf = []
            for (s0, s1) in free:
                if sp[1] <= s0 or sp[0] >= s1: nf.append((s0, s1)); continue
                if sp[0] > s0: nf.append((s0, sp[0]))
                if sp[1] < s1: nf.append((sp[1], s1))
            free = nf
        # door gaps + handles on the base units (front face at q = 0 on the segment line)
        for (s0, s1) in free:
            mods = split_span(s0, s1)
            for (m0, m1) in mods:
                if m0 > s0 + 0.5:
                    out.append(("A.fix", _segbox(a, u, wn, m0 - 0.25, m0 + 0.25, -0.3, 0.1, z0 + 0.10, z0 + 0.85), "kit_base", "kit_kick", "خزائن سفلية", dict(A, part="فاصل بين الأبواب")))
                mc = (m0 + m1) / 2
                out.append(("A.fix", _segbox(a, u, wn, mc - 6, mc + 6, -1.9, -0.3, z0 + 0.775, z0 + 0.79), "kit_handle", "kit_handle", "مقبض", dict(A, part="مقبض ستانلس مصقول (A1204 ملاحظة 7)")))
        # wall units 1.60 .. 2.20 (top 20 cm under the false ceiling), 35 deep; none above the cooker (hood), none where a window is
        hood = span_of(sg, ck_poly)
        wfree = [(0.0, L)]
        if hood:
            wfree = [(0.0, max(0.0, hood[0] - 1.0)), (min(L, hood[1] + 1.0), L)]
        zt = min(z0 + 2.20, z0 + fcl - 0.20)
        for (s0, s1) in wfree:
            for (m0, m1) in split_span(s0, s1):
                bx = _segbox(a, u, wn, m0 + 0.25, m1 - 0.25, 25.0, 60.0, z0 + 1.60, zt)
                fp = _foot(bx)
                if win_ext is not None and fp is not None and win_ext.intersects(fp): continue
                out.append(("A.fix", bx, "kit_wall", "kit_cabinet", "خزائن علوية", dict(A, part="وحدة علوية (ارتفاع 60 سم)", size_cm="عمق 35 × ارتفاع 60")))
                mc = (m0 + m1) / 2
                out.append(("A.fix", _segbox(a, u, wn, mc - 0.8, mc + 0.8, 23.4, 25.0, z0 + 1.60 + 0.04, z0 + 1.60 + 0.18), "kit_handle", "kit_handle", "مقبض", dict(A, part="مقبض ستانلس مصقول")))
        if hood:
            hc = (hood[0] + hood[1]) / 2
            out.append(("A.fix", _segbox(a, u, wn, hc - 45, hc + 45, 10.0, 60.0, z0 + 1.60, z0 + 1.78), "kit_hood", "kit_steel", "شفاط المطبخ", dict(A, kind="شفاط كهربائي (A1204: ELECTRICAL HOOD)", part="غطاء الشفاط", size_cm="90 × 50")))
            out.append(("A.fix", _segbox(a, u, wn, hc - 15, hc + 15, 32.0, 60.0, z0 + 1.78, min(z0 + 2.40, z0 + fcl)), "kit_hood", "kit_steel", "شفاط المطبخ", dict(A, kind="شفاط كهربائي (A1204: ELECTRICAL HOOD)", part="مدخنة الشفاط", size_cm="30 × 28")))
        # ceramic splash 0.87 .. 1.60 on the wall face, not across windows
        sfree = [(0.0, L)]
        for (s0, s1) in sfree:
            bx = _segbox(a, u, wn, s0, s1, 58.6, 60.0, z0 + 0.87, z0 + 1.60)
            fp = _foot(bx)
            if win_ext is not None and fp is not None and win_ext.intersects(fp):
                # split into 40 cm pieces and keep those clear of the window
                for (m0, m1) in split_span(s0, s1, target=40, lo=20, hi=60):
                    b2 = _segbox(a, u, wn, m0, m1, 58.6, 60.0, z0 + 0.87, z0 + 1.60); f2 = _foot(b2)
                    if f2 is not None and not win_ext.intersects(f2): out.append(("A.fix", b2, "kit_splash", "splash_ceramic", "سيراميك خلفية المطبخ", dict(A, part="سيراميك 30×60 (A1204)")))
            else:
                out.append(("A.fix", bx, "kit_splash", "splash_ceramic", "سيراميك خلفية المطبخ", dict(A, part="سيراميك 30×60 (A1204)")))
    # corners: base is one prism already; wall corner = L-shaped 35 cm band where two wall segments meet at a right angle
    for i in range(len(segs) - 1):
        s1, s2 = segs[i], segs[i + 1]
        if abs(s1["b"][0] - s2["a"][0]) > 0.6 or abs(s1["b"][1] - s2["a"][1]) > 0.6: continue
        if abs(s1["u"][0] * s2["u"][0] + s1["u"][1] * s2["u"][1]) > 0.1: continue
        P = s1["b"]; n1, n2 = s1["wn"], s2["wn"]
        def sq(d0, d1):
            return Polygon([(P[0] + (n1[0] + n2[0]) * d0, P[1] + (n1[1] + n2[1]) * d0), (P[0] + n1[0] * d1 + n2[0] * d0, P[1] + n1[1] * d1 + n2[1] * d0),
                            (P[0] + (n1[0] + n2[0]) * d1, P[1] + (n1[1] + n2[1]) * d1), (P[0] + n1[0] * d0 + n2[0] * d1, P[1] + n1[1] * d0 + n2[1] * d1)])
        corner = sq(0, 60).difference(sq(0, 25))
        if win_ext is not None and win_ext.intersects(sq(0, 60)): continue
        for q in (list(corner.geoms) if hasattr(corner, "geoms") else [corner]):
            if q.geom_type != "Polygon" or q.area < 30: continue
            out.append(("A.fix", ["p", [[_r(x), _r(y)] for x, y in list(q.exterior.coords)[:-1]], round(z0 + 1.60, 3), round(min(z0 + 2.20, z0 + fcl - 0.20), 3)], "kit_wall", "kit_cabinet", "خزائن علوية", dict(A, part="وحدة علوية — زاوية", size_cm="عمق 35 × ارتفاع 60")))
    # --- appliances (staged: 'All kitchen appliances are not included in the tenders except cooker hood' — A1204 note)
    ap = {"kind": "جهاز منزلي (غير مشمول بالعقد — للعرض)"}
    if cooker and cooker.get("n"):
        n = cooker["n"]; c = cooker["c"]
        fr = Fr((c[0] - n[0] * 30, c[1] - n[1] * 30), n, z0)
        out.append(("A.stage", fr.box(0, 30, 89.6, 59.6, 0.0, 0.85), "app_cooker", "app_steel", "طباخ", dict(ap, part="جسم الطباخ والفرن", size_cm="90 × 60 × 85")))
        out.append(("A.stage", fr.box(0, 30, 89.6, 59.6, 0.85, 0.87), "app_cooker", "app_dark", "طباخ", dict(ap, part="سطح الموقد")))
        for bx_, by_ in ((-20, 16), (20, 16), (-20, 44), (20, 44)):
            out.append(("A.stage", fr.cyl(bx_, by_, 7.0, 0.87, 0.895), "app_cooker", "app_steel", "طباخ", dict(ap, part="شعلة")))
        out.append(("A.stage", fr.box(0, 60.4, 60, 0.8, 0.25, 0.62), "app_cooker", "app_dark", "طباخ", dict(ap, part="زجاج باب الفرن")))
        out.append(("A.stage", fr.tube([(-32, 63.5, 0.68), (32, 63.5, 0.68)], 2.0), "app_cooker", "san_chrome", "طباخ", dict(ap, part="مقبض الفرن")))
    if washer and washer.get("n"):
        n = washer["n"]; c = washer["c"]
        fr = Fr((c[0] - n[0] * 30, c[1] - n[1] * 30), n, z0)
        out.append(("A.stage", fr.box(0, 29.5, 59.6, 59, 0.0, 0.84), "app_washer", "app_white", "غسالة", dict(ap, part="جسم الغسالة", size_cm="60 × 60 × 84")))
        out.append(("A.stage", fr.box(0, 59.6, 36, 1.2, 0.24, 0.60), "app_washer", "app_dark", "غسالة", dict(ap, part="باب الغسالة")))
    if fridge:
        n = fridge["n"]; c = fridge["c"]
        fr = Fr((c[0] - n[0] * 40, c[1] - n[1] * 40), n, z0)
        out.append(("A.stage", fr.box(0, 40, 89.5, 79.5, 0.0, 1.90), "app_fridge", "app_steel", "ثلاجة", dict(ap, part="جسم الثلاجة", size_cm="90 × 80 × 190")))
        out.append(("A.stage", fr.box(0, 79.8, 89, 0.6, 0.62, 0.64), "app_fridge", "app_dark", "ثلاجة", dict(ap, part="فاصل الأبواب")))
        out.append(("A.stage", fr.box(-38, 82, 2.4, 2.4, 0.95, 1.55), "app_fridge", "san_chrome", "ثلاجة", dict(ap, part="مقبض")))
    return out


# ------------------------------------------------------------------------------------------------------------------------ build
def _wins_by_level(M, win_els):
    by = {}
    for e in list(M["els"]) + list(win_els or []):
        if e["c"] != "A.win": continue
        f = _foot(e["g"])
        if f is not None and not f.is_empty: by.setdefault(e["l"], []).append(f)
    return {lv: unary_union(v) for lv, v in by.items()}


def build(M, win_els=None):
    p = os.path.join(D, "fixtures.json")
    if not os.path.exists(p): return {"els": [], "mats": {}, "types": {}}
    FX = json.load(open(p, encoding="utf-8"))
    LV = {l["id"]: l for l in M["levels"]}
    WU = _wins_by_level(M, win_els)
    out = []
    for key, rec in FX.items():
        for lv in PLAN_LEVELS[key]:
            if lv not in LV: continue
            z0 = LV[lv]["ffl"] + ZF
            fcl = 2.40                                  # false ceiling level of flats / kitchens / baths (A1204, A1203, A1401)
            cnt = {}
            def put(items, flat, room, grp, stage_default=None):
                u = f"{lv}-{flat}" if flat else None
                for (cat, g, t, m, mark, a) in items:
                    a = dict(a)
                    if room: a.setdefault("room", {"bath": "حمام", "wc": "دورة مياه", "kitchen": "مطبخ", "living": "معيشة / مطبخ", "master_bed": "غرفة نوم رئيسية", "bedroom": "غرفة نوم", "dress": "غرفة ملابس"}.get(room, room))
                    stage = "appliance" if cat == "A.stage" else None
                    out.append(_E(cat, lv, g, t, m, mark, a, SRC_KIT if t.startswith(("kit_", "app_")) else (SRC_WR if t.startswith("wardrobe") else SRC_BATH), grp, u, stage))
            for i, w in enumerate(rec.get("wc", [])):
                put(wc(Fr(w["b"], w["n"], z0), None), w["f"], w["r"], f"wc-{lv}-{w['f'] or 'x'}-{i}")
            for i, v in enumerate(rec.get("vanity", [])):
                put(vanity(Fr(v["b"], v["n"], z0), v["w"], v["d"], v["basins"], None), v["f"], v["r"], f"vanity-{lv}-{v['f'] or 'x'}-{i}")
            for i, b in enumerate(rec.get("basin", [])):
                put(basin_wall(Fr(b["b"], b["n"], z0), b["w"], b["d"], None), b["f"], b["r"], f"basin-{lv}-{b['f'] or 'x'}-{i}")
            for i, t_ in enumerate(rec.get("tub", [])):
                put(tub(t_["c"], t_["L"], t_["W"], t_["ax"], t_["tap"], z0), t_["f"], t_["r"], f"tub-{lv}-{t_['f'] or 'x'}-{i}")
            for i, k in enumerate(rec.get("kitchen", [])):
                put(kitchen(k, z0, WU.get(lv), fcl), k["flat"], k["room"], f"kitchen-{lv}-{k['flat']}")
            for i, w in enumerate(rec.get("wardrobe", [])):
                code = WR_CODE.get(int(w["w"]), "WR")
                put(wardrobe(Fr(w["b"], w["n"], z0), w["w"], w["d"], min(2.50, fcl), code), w["f"], w["r"], f"wardrobe-{lv}-{w['f'] or 'x'}-{i}")
    return {"els": out, "mats": MATS, "types": types()}


def drop_staged_wardrobes(fur, fix_els):
    """the loose staged wardrobes (furnish.py: rule-based, 210 x 60) give way to the drawn WR1..WR7 of A1300: in every flat that has at least one drawn wardrobe the staged ones are removed
    (the approved schedule is the complete list of wardrobes; the staged ones were an invention)"""
    units = set(e.get("u") for e in fix_els if e["t"] == "wardrobe_wr" and e.get("u"))
    keep, dropped = [], 0
    for e in fur:
        if e["t"] == "furn_wardrobe" and e.get("u") in units:
            dropped += 1; continue
        keep.append(e)
    return keep, dropped


# ------------------------------------------------------------------------------------------------------------------------ cards
def types():
    S = SRC_BATH; K = SRC_KIT
    def T(n, cf, sp, asm=None, sr=None):
        d = {"n": n, "cf": cf, "sp": sp}
        if asm: d["asm"] = asm
        d["sr"] = sr or S
        return d
    return {
        "san_wc": T("مرحاض أرضي بخزان ملاصق (WC)", "derived",
                    [["الموضع والاتجاه", "من رمز المسقط (A103 / A104 / A102): ظهر الخزان على الجدار"], ["ارتفاع حافة الحوض", "40 سم (A1203 تفصيل WC 7)"], ["البعد", "38 سم عرض × 68 سم من الجدار (الرمز في المسقط 70 × 68 بما فيه ملحقاته)"],
                     ["المقعد", "غطاء مغلق (تمثيل)"], ["وصلات", "دش يدوي «WATER HOSE & HAND SPRAY» وحامل ورق (وسيلة إيضاح A1203)"]],
                    ["شكل الحوض (بيضاوي) وارتفاع الخزان 82 سم تمثيل مبسَّط؛ المورّد والموديل غير محددين في المخططات"]),
        "san_accessory": T("إكسسوارات حمام (حامل ورق / دش يدوي / حامل مناشف)", "derived",
                           [["حسب وسيلة إيضاح A1203", "TOILET ROLL HOLDER — TOWEL BAR — WATER HOSE & HAND SPRAY"], ["التركيب", "على الجدار بارتفاعات تقريبية"]],
                           ["مواضع الإكسسوارات وارتفاعاتها تقدير (A1203 يحدد وجودها)"]),
        "san_vanity_top": T("سطح مغسلة رخام Armani Gray سماكة 3 سم (معلّق)", "doc",
                            [["المادة والسماكة", "Armani Gray Marble — سماكة 3 سم (A1203 مقطع 2)"], ["منسوب السطح", "+0.95 م؛ حافة الرخام 10 سم (+0.85 إلى +0.95)"], ["الأبعاد", "من رمز المسقط (عرض 100–220 × عمق 50–53 سم)"]],
                            ["الحافة (الإطار) تمثيل لسماكة 10 سم الواردة في المقطع"]),
        "san_basin": T("مغسلة تحت السطح (undercounter wash basin)", "doc",
                       [["النوع", "UNDERCOUNTER WASH BASIN — A1203 تفصيل 6"], ["العمق تحت السطح", "30 سم (من +0.85 إلى +0.55)"], ["الموضع", "من رمز المسقط"]],
                       ["مقاس الحوض 46 × 36 سم تقدير من رمز المسقط (52 × 40)"]),
        "san_tap": T("خلاط مغسلة / بانيو (كروم)", "assumed", [["الوصف", "خلاط كروم مقاوم للصدأ (A1204 ملاحظة: معدن غير قابل للتآكل)"]], ["الشكل والارتفاع تقدير؛ لا مواصفة للمورّد في المخططات"]),
        "san_tub": T("بانيو مدمج بكسوة سيراميك", "derived",
                     [["المقاس", "70 × 180 / 190 / 200 سم (مستطيل منطقة الرطوبة في المسقط A103/A104)"], ["منسوب الحافة", "+0.50 م (A1203 مقطع 1 و2: 50 سم)"], ["الجسم", "حوض أبيض مدمج داخل محيط مكسو بالسيراميك"], ["الخلاط والدش", "عند طرف الصنابير المحدد في رمز المسقط؛ الدش بوصلة مرنة (A1203: SHOWER)"]],
                     ["شكل الحوض الداخلي ومنسوب القاع (+0.12) تقدير؛ لون الخزف والسيراميك حسب جدول التشطيبات"]),
        "san_shower": T("عمود دش ورأس دش", "derived", [["وسيلة الإيضاح", "SHOWER — A1203 مقطع 1"], ["الارتفاع", "رأس الدش عند +1.95 م تقريبًا"]], ["الارتفاع تقدير"]),
        "bath_mirror": T("مرآة حمام شفافة 6 مم", "doc",
                         [["المقاس", "120 × 100 × 0.8 سم (A1203 مقطع 2)"], ["الارتفاع", "قاعدتها فوق السطح بـ 20 سم (+1.15) وقمتها 25 سم تحت السقف المستعار"], ["إنارة", "«6 mm THICK CLEAR MIRROR — 60 CM WIDE WITH LIGHTING ABOVE» (وسيلة الإيضاح)"]],
                         ["عرض المرآة في الدورات الصغيرة يُقصر إلى عرض السطح؛ إنارة المرآة غير مرسومة بعد"]),
        "kit_base": T("خزائن المطبخ السفلية", "derived",
                      [["الارتفاع", "قاعدة 10 + وحدة 75 = 85 سم (A1204 مقاطع S01–S12)"], ["العمق", "60 سم (المساقط)"], ["الامتداد", "على جدران المطبخ حسب خط واجهة الخزائن في المسقط A103/A104"], ["الأبواب", "وحدات 40–60 سم مقسمة آليًا بين الأجهزة (تقسيم تمثيلي)"], ["المقابض", "ستانلس ستيل مصقول (A1204 ملاحظة 7)"]],
                      ["لون الواجهات وتشطيبها بانتظار تأكيدك (رمادي فاتح محايد مؤقتًا)؛ تقسيم الأبواب تمثيلي وليس من الرسم", "الأدراج: «Drawers to be bottom fixed on running wheels, self closing» (ملاحظة A1204) غير مفصّلة"], K),
        "kit_kick": T("قاعدة الخزائن (سقف القدم)", "doc", [["الارتفاع", "10 سم (A1204: بعد 10 أسفل الوحدات)"], ["التراجع", "4 سم تقدير"]], None, K),
        "kit_top": T("سطح المطبخ جرانيت طبيعي 20 مم", "doc",
                     [["المادة", "NATURAL GRANITE 20 mm (A1204 مقاطع)"], ["المنسوب", "+0.85 إلى +0.87 م"], ["بروز الواجهة", "1.5 سم تقدير"]],
                     ["لون الجرانيت بانتظار تأكيدك (رمادي داكن محايد مؤقتًا)"], K),
        "kit_sink": T("حوض مطبخ ستانلس ستيل بحوضين ولوح تجفيف", "derived",
                      [["الموضع والأبعاد", "من المسقط: مستطيل 120 × 60 سم في المطبخ"], ["العمق", "حوض بعمق 23 سم تقريبًا"]],
                      ["توزيع الحوضين ولوح التجفيف تمثيلي (A1204 يرسم حوضين ولوح)"], K),
        "kit_wall": T("خزائن المطبخ العلوية", "derived",
                      [["الارتفاع", "60 سم؛ القاعدة +1.60 والقمة +2.20 (20 سم تحت السقف المستعار +2.40) — A1204 S01"], ["العمق", "35 سم"], ["الحذف", "لا وحدات فوق الطباخ (الشفاط) ولا أمام النوافذ"]],
                      ["العمق 35 سم وعرض الوحدات تقدير؛ الأبواب والتقسيم تمثيلي"], K),
        "kit_hood": T("شفاط كهربائي (ELECTRICAL HOOD)", "doc",
                      [["العقد", "الشفاط الوحيد المشمول بالعقد من أجهزة المطبخ (ملاحظة A1204)"], ["الموضع", "فوق الطباخ داخل صف الخزائن العلوية"], ["المقاس", "غطاء 90 × 50 سم + مدخنة 30 × 28 سم"]],
                      ["مقاسات الغطاء والمدخنة تقدير من المقطع"], K),
        "kit_splash": T("سيراميك خلفية المطبخ 30×60", "doc", [["الوصف", "WALL CERAMIC 30X60 AS PER SCHEDULE (A1204)"], ["الارتفاع", "من سطح العمل +0.87 إلى +1.60 م"]], ["اللون حسب جدول التشطيبات"], K),
        "kit_handle": T("مقبض ستانلس ستيل مصقول", "doc", [["الوصف", "Handles for Kitchen cabinets to be brushed stainless steel (A1204)"]], ["الموضع والطول تقدير"], K),
        "app_cooker": T("طباخ بفرن (غير مشمول بالعقد)", "assumed",
                        [["A1204", "«OVEN» في المساقط والمقاطع؛ «All kitchen appliances are not included in the tenders except cooker hood»"], ["المقاس", "90 × 60 × 85 سم (المقطع S01: عرض 90)"]],
                        ["الجهاز غير مشمول بالعقد: للعرض فقط ويُخفى من «الكماليات»؛ الشكل تمثيلي"], K),
        "app_fridge": T("ثلاجة (غير مشمولة بالعقد)", "assumed",
                        [["A1204", "«FRIDGE» عرض 90 سم وارتفاع 190 سم (المقطع S01)، عمق 80 سم (المسقط)"]], ["الموضع عند طرف صف الخزائن حيث تتسع 70–135 سم؛ للعرض فقط"], K),
        "app_washer": T("غسالة (غير مشمولة بالعقد)", "assumed", [["A1204", "«WASHING MACHINE» أسفل سطح العمل؛ رمز «WASH» في المسقط (دائرة 54 سم داخل مربع 60 سم)"]], ["الارتفاع 84 سم تقدير؛ للعرض فقط"], K),
        "wardrobe_wr": T("دولاب WR — إطار خشبي بتشطيب ورنيش أملس", "doc",
                         [["جدول A1300", "WR1 220×60 (20) — WR2 200×50 (5) — WR3 190×55 (5) — WR4 180×60 (2، ردهة) — WR5 170×60 (20) — WR6 120×50 (15) — WR7 110×50 (5): الارتفاع 250 سم لكل الأنواع"],
                          ["الارتفاع في النموذج", "حتى السقف المستعار (+2.40 م): «WARDROBE TO BE FULL HEIGHT UP TO THE SOFFIT … WHEREVER THERE IS NO FALSE CEILING»"],
                          ["الألواح", "4 ألواح متساوية (4 X EQ. PANELS)"], ["الموضع", "من رمز علّاقات الملابس في المسقط، والعمق من الجدول"]],
                         ["الجدول يعطي لـ WR5 مجموع 20 والتفصيل 2 + 16 = 18؛ ويكرّر الرمز WR6 للمقاس 110×50 (مسقط WARDROBE-7 يرسمه 1100×500 — خطأ رسم بالمليمتر)؛ لون الورنيش بانتظار تأكيدك"], SRC_WR),
    }
