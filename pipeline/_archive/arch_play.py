# -*- coding: utf-8 -*-
"""Kids play area as submitted by INEX / EDUPARK (INEX-2208-2849-DTS-25-065, EDU-204-07-26, 12 Aug 2026) — replaces the equipment drawn on A2300.

  MULTIAP1D   multi-activity climbing frame, black metal, 400 x 100 x 245 cm: monkey bars, wooden climbing wall with holds, basketball backboard + hoop, fixed ladder, rope ladder, knotted rope, rings
  EDU-SW-3502 two-seat swing, wooden A-frame legs, lime top bar, black seats on chains (dimensions not given: 340 x 210 x 240 assumed)
  MF-23010    double air walker 185 x 45 x 145        MF-23036 double kin-riding machine 120 x 110 x 140        MF-23044 kin-riding and step 2 in 1 120 x 110 x 140   (blue frame, yellow handles)
  SHA-23283   park bench 150 x 50 x 80, 5 seat slats / 4 back slats, steel end frames
  E10         cast-in-place EPDM rubber floor, 65 m2, SBR 40 + EPDM 10 = 50 mm (dark green speckled)

The submittal gives products and the total rubber area, NOT positions: the layout inside the fenced play area (A2300 fence, A2305 shade sails) is a proposal and is flagged as an assumption.
Heights are measured from the play-area finish (+0.20 m, A102).  The A2300 equipment (trampoline, spider-web swing, seesaws, go-round, spring riders, three slide towers) stays in landscape_els.play() for reference
but is no longer placed (landscape_els.PLAY_SET).  The rubber: the drawn 146 m2 area keeps its F15 surface; the 65 m2 E10 zones are laid on top around the equipment."""
import math
from shapely.geometry import Polygon, box
from shapely.ops import unary_union

G0 = 0.20
SRC = ["INEX-2208-2849-DTS-25-065 (EDUPARK EDU-204-07-26): تقديم فني لمعدات الملاعب والأرضية والمقاعد", "ARCH2 ص50 (A2301)، ARCH2 ص49 (A2300)، ARCH2 ص51 (A2305): سياج وأشرعة الظل ومنطقة الألعاب"]
GRP_N = [0]

MATS = {
    "play_black": {"name": "إطار فولاذ أسود مطلي (MULTIAP1D)", "color": "#2a2d31", "rough": 0.55, "metal": 0.25, "code": "INEX"},
    "play_blue": {"name": "هيكل لياقة أزرق مطلي (MF-23010/36/44)", "color": "#2a4aa8", "rough": 0.5, "metal": 0.2, "code": "INEX"},
    "play_yel": {"name": "مقابض ومقاعد لياقة صفراء", "color": "#f0cf24", "rough": 0.5, "code": "INEX"},
    "play_lime": {"name": "عارضة أرجوحة خضراء ليموني (EDU-SW-3502)", "color": "#9cc72f", "rough": 0.5, "code": "INEX"},
    "play_wood": {"name": "خشب أرجوحة مصبوغ — بني ذهبي", "color": "#b98a45", "rough": 0.7, "code": "INEX"},
    "play_wall_wood": {"name": "لوح خشب جدار التسلق", "color": "#c79a64", "rough": 0.7, "code": "INEX"},
    "play_rope": {"name": "حبال وسلالم حبال", "color": "#cdb592", "rough": 0.95, "code": "INEX"},
    "play_chain": {"name": "سلاسل أرجوحة معدنية", "color": "#9ea4aa", "metal": 0.3, "rough": 0.5, "code": "INEX"},
    "play_seat": {"name": "مقعد أرجوحة مطاط أسود", "color": "#212326", "rough": 0.9, "code": "INEX"},
    "play_board": {"name": "لوحة سلة سوداء وحلقة حمراء", "color": "#343a40", "rough": 0.5, "code": "INEX"},
    "play_hoop": {"name": "حلقة السلة — برتقالي محمر", "color": "#d8452a", "rough": 0.5, "code": "INEX"},
    "hold_red": {"name": "نتوء تسلق — أحمر", "color": "#d83a2d", "rough": 0.6, "code": "INEX"},
    "hold_blue": {"name": "نتوء تسلق — أزرق", "color": "#2f6fc4", "rough": 0.6, "code": "INEX"},
    "hold_green": {"name": "نتوء تسلق — أخضر", "color": "#3fa34d", "rough": 0.6, "code": "INEX"},
    "hold_orange": {"name": "نتوء تسلق — برتقالي", "color": "#f08a24", "rough": 0.6, "code": "INEX"},
    "bench_steel": {"name": "هيكل مقعد فولاذ — رمادي فاتح خشن (SHA-23283)", "color": "#bfc2c4", "rough": 0.75, "metal": 0.15, "code": "INEX"},
    "bench_wood": {"name": "شرائح خشب صلب مقعد/ظهر — مصبوغ وطلاء شفاف (SHA-23283)", "color": "#8d5e3a", "rough": 0.65, "code": "INEX"},
    "rubber_e10": {"name": "أرضية EPDM مصبوبة موقعيًا — اللون E10 (أخضر داكن حبيبي) سماكة 50 مم", "color": "#34523a", "rough": 0.97, "code": "INEX E10"},
}


class Loc:
    """local frame of a piece of equipment: origin (cm), rotation (deg), z from the play finish"""
    def __init__(self, x, y, ang=0.0, z0=G0):
        self.x, self.y, self.z0 = x, y, z0
        a = math.radians(ang); self.c, self.s = math.cos(a), math.sin(a); self.ang = ang

    def pt(self, lx, ly): return (self.x + lx * self.c - ly * self.s, self.y + lx * self.s + ly * self.c)

    def box(self, lx, ly, w, d, za, zb):
        X, Y = self.pt(lx, ly)
        return ["b", round(X, 1), round(Y, 1), round(w, 1), round(d, 1), round(self.ang, 2), round(self.z0 + za, 3), round(self.z0 + zb, 3)]

    def cyl(self, lx, ly, r, za, zb):
        X, Y = self.pt(lx, ly)
        return ["cyl", round(X, 1), round(Y, 1), round(r, 1), round(self.z0 + za, 3), round(self.z0 + zb, 3)]

    def tube(self, pts, dia):
        out = []
        for lx, ly, z in pts:
            X, Y = self.pt(lx, ly); out.append([round(X, 1), round(Y, 1), round(self.z0 + z, 3)])
        return ["t", out, dia]

    def tri(self, pts, thick):
        out = []
        for lx, ly, z in pts:
            X, Y = self.pt(lx, ly); out.append([round(X, 1), round(Y, 1), round(self.z0 + z, 3)])
        return ["tri", out, thick]

    def sph(self, lx, ly, r, za, zb):
        X, Y = self.pt(lx, ly)
        return ["sph", round(X, 1), round(Y, 1), round(r, 1), round(self.z0 + za, 3), round(self.z0 + zb, 3), 8, 5]

    def foot(self, w, d):
        pts = [self.pt(sx * w / 2, sy * d / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        return Polygon(pts)


class Out:
    def __init__(self, typ, name, grp, extra):
        self.els = []; self.t = typ; self.name = name; self.grp = grp; self.extra = extra

    def add(self, g, mat, part):
        a = {"kind": self.name, "part": part}; a.update(self.extra)
        self.els.append({"c": "A.stage", "l": "G", "g": g, "mark": self.name, "t": self.t, "m": mat, "a": a, "src": SRC, "grp": self.grp, "stage": "play"})


# --------------------------------------------------------------------------------------------------------------------------------- equipment
def multiap(cx, cy, ang):
    L = Loc(cx, cy, ang); o = Out("play_multiap", "إطار أنشطة متعدد MULTIAP1D", "play-multiap", {"size_cm": "400 × 100 × 245", "model": "MULTIAP1D"})
    for sx, X in ((-1, -190), (1, 178)):
        for sy in (-1, 1): o.add(L.tube([(X, sy * 45, 0.0), (X, sy * 45, 2.42)], 6.5), "play_black", "عمود")
    for sy in (-1, 1): o.add(L.tube([(-195, sy * 45, 2.45), (200, sy * 45, 2.45)], 6.5), "play_black", "قضيب علوي")
    for k in range(11): o.add(L.tube([(-150 + 30 * k, -45, 2.40), (-150 + 30 * k, 45, 2.40)], 3.4), "play_black", "عقلة (Monkey bar)")
    for k in range(8): o.add(L.tube([(-190, -45, 0.35 + 0.25 * k), (-190, 45, 0.35 + 0.25 * k)], 3.2), "play_black", "درجة السلّم الثابت")
    o.add(L.box(-125, -47, 90, 3, 2.45, 3.00), "play_board", "لوحة كرة السلة")
    o.add(L.tube([(-125, -46, 2.20), (-125, -52, 2.20)], 2.4), "play_hoop", "ذراع الحلقة")
    o.add(L.tube([(-125 + 22 * math.cos(2 * math.pi * k / 14), -74 + 22 * math.sin(2 * math.pi * k / 14), 2.20) for k in range(15)], 2.4), "play_hoop", "حلقة السلة")
    for dx in (-12, 12): o.add(L.tube([(-60 + dx, 0, 2.40), (-60 + dx, 0, 0.48)], 1.4), "play_rope", "حبل السلّم المعلّق")
    for k in range(7): o.add(L.box(-60, 0, 26, 3, 0.52 + 0.28 * k, 0.55 + 0.28 * k), "play_wall_wood", "درجة السلّم المعلّق")
    o.add(L.tube([(5, 0, 2.40), (5, 0, 0.45)], 3.0), "play_rope", "الحبل المعقود")
    for k in range(6): o.add(L.cyl(5, 0, 3.6, 0.6 + 0.3 * k, 0.66 + 0.3 * k), "play_rope", "عقدة")
    for dx in (45, 75):
        o.add(L.tube([(dx, 0, 2.40), (dx, 0, 1.81)], 1.2), "play_chain", "حزام الحلقة")
        o.add(L.tube([(dx + 9 * math.cos(2 * math.pi * k / 12), 0, 1.72 + 0.09 * math.sin(2 * math.pi * k / 12)) for k in range(13)], 2.2), "play_wood", "حلقة جمباز")
    # climbing wall leaning at the right end (top towards the frame)
    o.add(L.tri([(213, -45, 0.0), (213, 45, 0.0), (183, -45, 2.35)], 6), "play_wall_wood", "جدار تسلق خشبي")
    o.add(L.tri([(213, 45, 0.0), (183, 45, 2.35), (183, -45, 2.35)], 6), "play_wall_wood", "جدار تسلق خشبي")
    holds = [(-28, 0.35, "hold_red"), (10, 0.5, "hold_blue"), (-8, 0.7, "hold_orange"), (25, 0.85, "hold_green"), (-30, 1.0, "hold_blue"), (5, 1.15, "hold_red"), (30, 1.3, "hold_orange"),
             (-15, 1.45, "hold_green"), (18, 1.6, "hold_red"), (-32, 1.75, "hold_orange"), (0, 1.9, "hold_blue"), (28, 2.0, "hold_green"), (-12, 2.15, "hold_red"), (14, 2.25, "hold_orange")]
    for dy, z, m in holds:
        x = 213 - 30 * (z / 2.35) - 4
        o.add(L.sph(x, dy, 4.0, z - 0.04, z + 0.04), m, "نتوء تسلق")
    return o, L.foot(430, 110)


def swing(cx, cy, ang):
    L = Loc(cx, cy, ang); o = Out("play_swing", "أرجوحة بمقعدين EDU-SW-3502", "play-swing", {"size_cm": "340 × 210 × 240 (افتراض)", "model": "EDU-SW-3502"})
    o.add(L.tube([(-170, 0, 2.40), (170, 0, 2.40)], 12), "play_lime", "العارضة العلوية")
    for sx in (-1, 1):
        o.add(L.box(sx * 165, 0, 14, 22, 2.12, 2.52), "play_lime", "صفيحة الربط")
        for sy in (-1, 1): o.add(L.tube([(sx * 163, sy * 6, 2.34), (sx * 150, sy * 105, 0.0)], 10), "play_wood", "ساق خشبية")
    for xs in (-62, 62):
        for dx in (-20, 20): o.add(L.tube([(xs + dx, 0, 2.34), (xs + dx, 0, 0.55)], 1.0), "play_chain", "سلسلة")
        o.add(L.box(xs, 0, 44, 15, 0.50, 0.54), "play_seat", "مقعد مطاطي")
    return o, L.foot(360, 230)


def airwalker(cx, cy, ang):
    L = Loc(cx, cy, ang); o = Out("play_fit_airwalker", "ماشي هوائي مزدوج MF-23010", "play-fit-1", {"size_cm": "185 × 45 × 145", "model": "MF-23010"})
    for sx in (-1, 1):
        for sy in (-1, 1): o.add(L.tube([(sx * 90, sy * 20, 0.0), (sx * 90, sy * 20, 1.45)], 8), "play_blue", "عمود")
    for sy in (-1, 1):
        o.add(L.tube([(-90, sy * 20, 1.43), (90, sy * 20, 1.43)], 6), "play_blue", "قضيب علوي")
        o.add(L.tube([(-90, sy * 20, 0.22), (90, sy * 20, 0.22)], 6), "play_blue", "قضيب سفلي")
    for xs in (-45, 45):
        o.add(L.tube([(xs, 0, 1.40), (xs - 14, 0, 0.36)], 3.2), "play_yel", "ذراع المشي")
        o.add(L.box(xs - 14, 0, 24, 12, 0.30, 0.34), "play_yel", "مسند القدم")
        o.add(L.tube([(xs + 4, -12, 1.12), (xs + 4, 12, 1.12)], 2.8), "play_yel", "مقبض")
    return o, L.foot(185, 45)


def kinride(cx, cy, ang, step=False):
    code = "MF-23044" if step else "MF-23036"
    L = Loc(cx, cy, ang); o = Out("play_fit_kinride", "كينرايد مع خطوة 2 في 1 " + code if step else "كينرايد مزدوج " + code, "play-fit-" + code, {"size_cm": "120 × 110 × 140", "model": code})
    for k, ((x0, y0), (x1, y1)) in enumerate((((-60, -55), (60, -55)), ((60, -55), (60, 55)), ((60, 55), (-60, 55)), ((-60, 55), (-60, -55)))):
        o.add(L.tube([(x0, y0, 0.14), (x1, y1, 0.14)], 6), "play_blue", "إطار القاعدة")
    o.add(L.tube([(0, -55, 0.14), (0, 55, 0.14)], 6), "play_blue", "عارضة وسطى")
    for sy in (-1, 1): o.add(L.tube([(0, sy * 30, 0.14), (-12, sy * 30, 1.38)], 6), "play_blue", "عمود مائل")
    for sy in ((-1, 1) if not step else (-1,)):
        o.add(L.box(-32, sy * 30, 34, 30, 0.52, 0.57), "play_yel", "مقعد")
        o.add(L.tube([(-12, sy * 30 - 12, 1.30), (-12, sy * 30 + 12, 1.30)], 2.8), "play_yel", "مقبض")
        o.add(L.box(38, sy * 30, 30, 22, 0.20, 0.24), "play_yel", "مسند القدم")
    if step: o.add(L.box(28, 32, 40, 32, 0.28, 0.33), "play_yel", "منصة الخطوة")
    return o, L.foot(120, 110)


def bench(cx, cy, ang):
    L = Loc(cx, cy, ang); o = Out("play_bench", "مقعد حديقة SHA-23283", "play-bench", {"size_cm": "150 × 50 × 80", "model": "SHA-23283"})
    for sx in (-1, 1):
        o.add(L.box(sx * 70, 18, 4, 6, 0.0, 0.45), "bench_steel", "ساق أمامية")
        o.add(L.box(sx * 70, -20, 4, 6, 0.0, 0.80), "bench_steel", "ساق خلفية/ظهر")
        o.add(L.box(sx * 70, -1, 4, 44, 0.40, 0.45), "bench_steel", "حامل المقعد")
    for k in range(5): o.add(L.box(0, -12 + 7.7 * k, 148, 7, 0.45, 0.48), "bench_wood", "شريحة مقعد")
    for k in range(4): o.add(L.box(0, -21 - (0.54 + 0.085 * k - 0.5) * 12, 148, 2.6, 0.54 + 0.085 * k, 0.60 + 0.085 * k), "bench_wood", "شريحة ظهر")
    return o, L.foot(150, 50)


# --------------------------------------------------------------------------------------------------------------------------------- layout
def build(M):
    """returns els (A.stage + A.site), mats, types.  Layout inside the fenced area: swing, frame, fitness column, two benches (assumption — positions are not in the submittal)."""
    items = []
    foots = []
    for fn, args in ((swing, (1500, 2570, 0)), (multiap, (1500, 2895, 0)), (airwalker, (2070, 2465, 90)), (kinride, (2070, 2640, 90, False)), (kinride, (2070, 2805, 90, True)),
                     (bench, (1700, 2412, 180)), (bench, (1960, 2412, 180))):
        o, ft = fn(*args)
        items.append(o); foots.append(ft)
    els = []
    for o in items: els.extend(o.els)
    # E10 rubber: safety zone around the equipment, clipped to the drawn play-area surface, grown until it covers 65 m2 (A: BOQ 9.2.1.1 / submittal)
    area = None
    for e in M["els"]:
        if e["t"] == "site_rubber" and e["g"][0] == "p":
            g = e["g"]; area = Polygon(g[1], [h for h in (g[4] if len(g) > 4 and g[4] else []) if len(h) >= 3]).buffer(0)
    zone = None
    if area is not None:
        U = unary_union(foots)
        lo, hi = 20.0, 400.0
        for _ in range(30):
            mid = (lo + hi) / 2
            z = U.buffer(mid, join_style=1).intersection(area)
            if z.area / 1e4 < 65.0: lo = mid
            else: hi = mid
        zone = U.buffer(hi, join_style=1).intersection(area)
        for q in (list(zone.geoms) if hasattr(zone, "geoms") else [zone]):
            if q.geom_type != "Polygon" or q.area < 2000: continue
            holes = [[[round(x, 1), round(y, 1)] for x, y in list(h.coords)[:-1]] for h in q.interiors]
            g = ["p", [[round(x, 1), round(y, 1)] for x, y in list(q.exterior.coords)[:-1]], 0.19, 0.205] + ([holes] if holes else [])
            els.append({"c": "A.site", "l": "G", "g": g, "mark": "E10", "t": "play_rubber_e10", "m": "rubber_e10",
                        "a": {"kind": "أرضية EPDM مصبوبة E10", "area_m2": round(zone.area / 1e4, 1), "thickness_mm": 50, "note": "SBR 40 مم + EPDM 10 مم + طلاء UV؛ المساحة المقدَّمة 65 م² والشكل حول المعدات تقدير"},
                        "src": SRC})
    # the A2300 ground-cover plants / shrubs drawn inside the play area would stand on the rubber and in the equipment: drop those that fall in the E10 zone or under a piece of equipment
    dropped = 0
    if zone is not None:
        keepout = unary_union([zone.buffer(12)] + [f.buffer(25) for f in foots])
        from shapely.geometry import Point
        kept = []
        for e in M["els"]:
            if e["c"] == "A.stage" and e["t"] in ("plant_small", "shrub_jatr", "ground_wet_sand", "ground_puddle") and e["g"][0] in ("sph", "p", "leaf"):
                g = e["g"]
                c = Point(g[1], g[2]) if g[0] in ("sph", "leaf") else Polygon(g[1]).centroid
                if keepout.contains(c): dropped += 1; continue
            kept.append(e)
        M["els"][:] = kept
    print("A2300 plants removed from the INEX play zone:", dropped)
    return {"els": els, "mats": MATS, "types": types(), "rubber_m2": round(zone.area / 1e4, 1) if zone is not None else None}


def types():
    S = SRC
    def T(n, cf, sp, asm=None):
        d = {"n": n, "cf": cf, "sp": sp, "sr": S}
        if asm: d["asm"] = asm
        return d
    POS = "موضع المعدة داخل منطقة الألعاب اقتراح للعرض — التقديم الفني لا يحدد المواضع"
    return {
        "play_multiap": T("إطار أنشطة متعدد MULTIAP1D (تسلق، عقلات، سلة)", "doc",
                          [["الكود", "MULTIAP1D — EDUPARK"], ["الأبعاد", "400 × 100 × 245 سم"], ["العمر", "3 سنوات فأكثر"], ["الهيكل", "فولاذ بطلاء أسود للاستعمال الخارجي؛ الحمل الأقصى 400 كغ"],
                           ["المكوّنات", "قسم عقلات علوي، جدار تسلق خشبي بنتوءات، لوحة سلة بحلقة وشبك، سلّم ثابت، سلّم حبال، حبل معقود، حلقتا جمباز"]],
                          [POS, "لوحة السلة مرسومة فوق ارتفاع الإطار (245 سم) وشكل الجدار المائل تقريبي"]),
        "play_swing": T("أرجوحة بمقعدين EDU-SW-3502", "doc", [["الكود", "EDU-SW-3502 — EDUPARK"], ["الهيكل", "ساقان خشبيتان على شكل A وعارضة خضراء ليموني ومقعدان مطاطيان أسودان على سلاسل"]],
                       ["الأبعاد غير مذكورة في التقديم: 340 × 210 × 240 سم تقدير من الصور", POS]),
        "play_fit_airwalker": T("ماشي هوائي مزدوج MF-23010", "doc", [["الكود", "MF-23010"], ["الأبعاد", "1850 × 450 × 1450 مم"], ["الوزن", "44 كغ"], ["اللون", "هيكل أزرق ومقابض صفراء"]], [POS]),
        "play_fit_kinride": T("جهاز لياقة كينرايد (MF-23036 مزدوج / MF-23044 مع خطوة)", "doc",
                              [["MF-23036", "كينرايد مزدوج — 1200 × 1100 × 1400 مم — 45 كغ"], ["MF-23044", "كينرايد وخطوة 2 في 1 — 1200 × 1100 × 1400 مم"], ["اللون", "هيكل أزرق ومقابض ومقاعد صفراء"]], [POS]),
        "play_bench": T("مقعد حديقة بظهر SHA-23283", "doc",
                        [["الأبعاد", "150 × 50 × 80 سم"], ["المقعد/الظهر", "خشب صلب مصبوغ وطلاء شفاف: 5 شرائح مقعد + 4 شرائح ظهر"], ["الهيكل", "ألواح نهاية فولاذية بطلاء رمادي فاتح خشن، قواعد مثبّتة بالبراغي"]],
                        [POS + "؛ عدد المقاعد غير محدد في الصفحة المتاحة (صفحة 1 من 2)"]),
        "play_rubber_e10": T("أرضية EPDM مصبوبة E10 — 65 م²", "doc",
                             [["التركيب", "SBR 40 مم (أساس ماص للصدمات) + EPDM 10 مم (سطح) + طلاء UV شفاف = 50 مم، تُصبّ في الموقع"], ["اللون", "E10 أخضر داكن حبيبي"], ["المساحة", "65 م² (C04 Residential Building)"],
                              ["الضمان والمنشأ", "3 سنوات — أوروبا"]],
                             ["شكل المنطقة حول المعدات تقدير (حدّ أمان متساوٍ يُضبط ليعطي 65 م²)؛ بقية المنطقة المرسومة (146 م²) تبقى بسطح F15 كما في A500 إلى حين التوضيح"]),
    }
