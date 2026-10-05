# -*- coding: utf-8 -*-
"""Builds the landscape / play / shade elements of the 3-D model from data/landscape.json (pipeline/landscape.py, A2300 + A2305 + A102).
Everything here is regenerated on every post_model run (ids start with 'A.stage-G-L' / 'A.site-G-L' / 'A.rail-G-L'), nothing is edited by hand.

Heights / sizes that the sheets do NOT give are guesses and are flagged in `a.assumed`:  tree total heights of Azadirachta (5.0 m) and Hibiscus (4.2 m), the small-plant height,
play-equipment heights (the plan gives footprints only), gazebo lattice detail.  From the sheets: Plumeria 3.0 m overall, 1.8 m clear stem of the other two, shrubs 0.70-0.80 m,
shed posts steel pipe 200 mm with tops at +4.50 / +3.50 (A2305), gazebo 680 cm round, floor +0.95, wall top +3.95, apex +5.00, steel pipe 200 mm (A2305).
"""
import math
from shapely.geometry import Polygon, Point

MATS = {
    "tree_azad": {"name": "نيم (Azadirachta indica) — تاج الشجرة", "color": "#4d8a3b", "code": "A2300 AZAD.I"},
    "tree_hibi": {"name": "هبسكس (Hibiscus tiliaceus) — تاج الشجرة", "color": "#5c9c48", "code": "A2300 HIBI.T"},
    "tree_plum": {"name": "فرنجبان (Plumeria obtusa) — تاج الشجرة", "color": "#6fae4f", "code": "A2300 PLUM.O"},
    "tree_trunk": {"name": "جذوع الأشجار", "color": "#6b5236", "code": "A2300"},
    "shrub_jatr": {"name": "جاتروفا (Jatropha pandurifolia) — شجيرات", "color": "#3f7f3a", "code": "A2300 JATR.P"},
    "plant_a": {"name": "نباتات صغيرة (مغطّيات تربة/عصاريات) — الأخضر الفاتح", "color": "#86b252", "code": "A2300"},
    "plant_b": {"name": "نباتات صغيرة (مغطّيات تربة/عصاريات) — الأخضر الداكن", "color": "#2f6f3a", "code": "A2300"},
    "plant_c": {"name": "نباتات صغيرة (مغطّيات تربة/عصاريات) — الزيتوني", "color": "#a3b85e", "code": "A2300"},
    "steel_post": {"name": "ماسورة فولاذ ⌀200 مم — رمادي داكن", "color": "#4a4f55", "code": "A2305"},
    "shade_fabric": {"name": "قماش PVC مثقّب للتظليل (Knitted shade cloth) — بيج", "color": "#e3dcc6", "code": "A2305"},
    "wood_slat": {"name": "خشب (لوفر/عوارض السقف والبرجولة)", "color": "#a9794c", "code": "A2305"},
    "wood_lattice": {"name": "شبك خشبي (Wooden lattice)", "color": "#c49a6c", "code": "A2305"},
    "bench_granite": {"name": "مقعد جرانيت داكن مدمج في جدار الحوض (TOS +0.65)", "color": "#3b3e44", "code": "A2302 / A102"},
    "play_yellow": {"name": "ألعاب أطفال — بلاستيك أصفر", "color": "#f2c230", "code": "A2300"},
    "play_red": {"name": "ألعاب أطفال — بلاستيك أحمر", "color": "#d8402f", "code": "A2300"},
    "play_blue": {"name": "ألعاب أطفال — بلاستيك أزرق", "color": "#2f6fc4", "code": "A2300"},
    "play_steel": {"name": "ألعاب أطفال — هيكل فولاذي", "color": "#7b838c", "code": "A2300"},
    "play_net": {"name": "شبكة/حبال الألعاب", "color": "#c0392b", "code": "A2300"},
    "fence_steel": {"name": "سياج فولاذي رمادي داكن بقضبان — ارتفاع 120 سم", "color": "#3d4248", "code": "A2300 FENCING 120cm"},
    "paving_wood": {"name": "أرضية الجازيبو — بلاط (PASCO) +0.95", "color": "#c9b99c", "code": "A2305"},
}
SPEC = {   # canopy z0,z1 (above the soil), trunk radius, material
    "AZAD.I": dict(stem=1.8, h=5.0, tr=9, mat="tree_azad", name="نيم", assumed="الارتفاع الكلي 5.0 م افتراض (الجدول يذكر ساق 1.8 م وقطر 40–50 مم فقط)"),
    "HIBI.T": dict(stem=1.8, h=4.2, tr=7, mat="tree_hibi", name="هبسكس", assumed="الارتفاع الكلي 4.2 م افتراض (الجدول يذكر ساق 1.8 م وقطر 40–50 مم فقط)"),
    "PLUM.O": dict(stem=1.0, h=3.0, tr=5, mat="tree_plum", name="فرنجبان", assumed=None),
}
SRC = ["ARCH2 ص49 (A2300 خطة الزراعة)", "ARCH1 ص5 (A102)"]

def _e(c, t, g, mat, mark, a=None, stage=None, grp=None):
    e = {"c": c, "l": "G", "g": g, "mark": mark, "t": t, "m": mat, "a": a or {}, "src": list(SRC)}
    if stage: e["stage"] = stage
    if grp: e["grp"] = grp
    return e

def _base(beds, x, y, default=0.2):
    p = Point(x, y)
    for poly, top in beds:
        if poly.contains(p): return top
    return default

def plants(L, beds):
    out = []; n = 0
    for t in L["trees"]:
        sp = SPEC[t["sp"]]; z0 = _base(beds, t["x"], t["y"]); n += 1
        a = {"kind": "tree", "species": t["sp"], "name_ar": sp["name"], "canopy_diam_cm": 2 * t["r"], "total_h_m": sp["h"], "base_z_m": round(z0, 2),
             "note": "مصمَّم حسب مخطط الزراعة A2300 — غير مزروع بعد في صور الموقع (7 أغسطس)"}
        if sp["assumed"]: a["assumed"] = sp["assumed"]
        g = f"tree-{n}"
        out.append(_e("A.stage", "tree_trunk", ["cyl", t["x"], t["y"], sp["tr"], round(z0, 2), round(z0 + sp["stem"] + 0.4, 2)], "tree_trunk", t["sp"], a, "tree", g))
        out.append(_e("A.stage", "tree_" + t["sp"][:4].lower(), ["sph", t["x"], t["y"], t["r"], round(z0 + sp["stem"], 2), round(z0 + sp["h"], 2), 10, 6], sp["mat"], t["sp"], a, "tree", g))
    for s in L["shrubs"]:
        z0 = _base(beds, s["x"], s["y"]); n += 1
        out.append(_e("A.stage", "shrub_jatr", ["sph", s["x"], s["y"], s["r"], round(z0, 2), round(z0 + 0.75, 2), 8, 5], "shrub_jatr", "JATR.P",
                      {"kind": "shrub", "species": "JATR.P", "name_ar": "جاتروفا", "height_m": "0.70–0.80", "base_z_m": round(z0, 2), "note": "حسب A2300 (55 شجيرة في الجدول)"}, "plant"))
    for i, s in enumerate(L["small"]):
        z0 = _base(beds, s["x"], s["y"]); m = ("plant_a", "plant_b", "plant_c")[i % 3]
        out.append(_e("A.stage", "plant_small", ["sph", s["x"], s["y"], s["r"], round(z0, 2), round(z0 + 0.35, 2), 6, 4], m, "GC/SUC",
                      {"kind": "plant", "name_ar": "نبات صغير (مغطّي تربة/عصاريات)", "base_z_m": round(z0, 2),
                       "assumed": "النوع بين Ruellia / Alternanthera / Bougainvillea / Vitex / Adenium / Zamia لا يُحدَّد من الرمز (دوائر r≈12 سم)؛ الارتفاع 0.35 م افتراض بين 0.2–0.8 م"}, "plant"))
    return out

def benches(L):
    out = []
    for i, ring in enumerate(L.get("benches", []), 1):
        P = Polygon(ring)
        if not P.is_valid or P.area < 3000 or (P.bounds[2] - P.bounds[0]) > 400: continue
        out.append(_e("A.site", "site_bench", ["p", ring, 0.2, 0.65], "bench_granite", f"BENCH-{i:02d}",
                      {"kind": "bench", "top_of_seat_m": 0.65, "note": "مقعد مدمج في جدار الحوض (A102 BENCH / A2302 TOS +0.65)"}))
    return out

def shed():
    """kids-play-area shade sails (A2305): 3 + 4 steel posts 200 mm, rows 620 cm apart, 400 cm spacing, tops +4.50 (north row) / +3.50 (south row)"""
    top = [(1265, 2975), (1665, 2975), (2065, 2975)]; bot = [(1065, 2355), (1465, 2355), (1865, 2355), (2265, 2355)]
    out = []; ZT, ZB = 4.50, 3.50
    for i, (x, y) in enumerate(top, 1):
        out.append(_e("A.site", "shed_post", ["cyl", x, y, 10, 0.2, ZT], "steel_post", f"SHED-N{i}", {"kind": "post", "dia_mm": 200, "top_m": ZT, "assumed": "أي صف أعلى (+4.50) وأيهما +3.50 غير مفصّل بوضوح في A2305؛ افتُرض الصف الشمالي +4.50"}, grp="shed"))
    for i, (x, y) in enumerate(bot, 1):
        out.append(_e("A.site", "shed_post", ["cyl", x, y, 10, 0.2, ZB], "steel_post", f"SHED-S{i}", {"kind": "post", "dia_mm": 200, "top_m": ZB}, grp="shed"))
    P = lambda xy, z: [xy[0], xy[1], z]
    tris = [(P(top[0], ZT), P(bot[0], ZB), P(bot[1], ZB)), (P(top[1], ZT), P(bot[1], ZB), P(bot[2], ZB)), (P(top[2], ZT), P(bot[2], ZB), P(bot[3], ZB)),
            (P(top[0], ZT), P(top[1], ZT), P(bot[1], ZB)), (P(top[1], ZT), P(top[2], ZT), P(bot[2], ZB))]
    for i, tr in enumerate(tris, 1):
        out.append(_e("A.site", "shed_sail", ["tri", [list(p) for p in tr], 1.2], "shade_fabric", f"SAIL-{i}", {"kind": "shade_sail", "note": "قماش PVC (Knitted shade cloth) — شراع مسطّح تقريبي؛ في المخطط حواف منحنية (catenary)"}, grp="shed"))
    return out

def fence():
    pts = [(2250, 2745), (2250, 2960), (1260, 2960), (1060, 2540), (1062, 2490), (1085, 2420), (1141, 2370), (2250, 2370), (2250, 2585)]
    out = []; z0 = 0.2
    for zr_ in (0.4, 0.85, 1.38):
        out.append(_e("A.rail", "fence_play", ["t", [[x, y, zr_] for x, y in pts], 3.0], "fence_steel", "FENCE-120", {"kind": "fence", "height_cm": 120, "note": "سياج ساحة الألعاب: A2300 «FENCING HIGHT 120cm»؛ القضبان العمودية غير مرسومة (قضيبان أفقيان + عمود كل ~1.5 م)"}, grp="playfence"))
    # posts
    L = 0
    for a, b in zip(pts[:-1], pts[1:]):
        d = math.hypot(b[0] - a[0], b[1] - a[1]); n = max(1, round(d / 150))
        for j in range(n + (1 if (a, b) == (pts[-2], pts[-1]) else 0)):
            t = j / n; x = a[0] + (b[0] - a[0]) * t; y = a[1] + (b[1] - a[1]) * t
            out.append(_e("A.rail", "fence_post", ["cyl", round(x), round(y), 2.5, 0.2, 1.4], "fence_steel", "FENCE-120", {"kind": "post"}, grp="playfence"))
    return out

def play():
    out = []; S = "play"
    def box(cx, cy, w, d, z0, z1, mat, name, grp, ang=0, note=None):
        out.append(_e("A.stage", "play_part", ["b", cx, cy, w, d, ang, z0, z1], mat, name, {"kind": "play", "name_ar": name, "assumed": note or "الارتفاعات افتراض (المخطط يعطي المسقط فقط)"}, S, grp))
    def cyl(cx, cy, r, z0, z1, mat, name, grp):
        out.append(_e("A.stage", "play_part", ["cyl", cx, cy, r, z0, z1], mat, name, {"kind": "play", "name_ar": name, "assumed": "الارتفاعات افتراض (المخطط يعطي المسقط فقط)"}, S, grp))
    G0 = 0.2
    # 1 trampoline (r 49 at 1132,2473)
    cyl(1132, 2473, 49, G0 + 0.30, G0 + 0.36, "play_red", "ترامبولين — سطح القفز", "trampoline")
    for k in range(8):
        a = k * math.pi / 4; cyl(round(1132 + 52 * math.cos(a)), round(2473 + 52 * math.sin(a)), 2.5, G0, G0 + 1.1, "play_steel", "ترامبولين — عمود الشبكة", "trampoline")
    cyl(1132, 2473, 51, G0 + 1.05, G0 + 1.1, "play_net", "ترامبولين — حلقة الشبكة", "trampoline")
    # 2 spider-web swing (1402,2600, r 46)
    cyl(1402, 2600, 46, G0 + 0.45, G0 + 0.5, "play_net", "أرجوحة شبكة العنكبوت — القرص", "spiderweb")
    for dx in (-62, 62): box(1402 + dx, 2600, 5, 5, G0, G0 + 2.2, "play_steel", "أرجوحة شبكة — عمود", "spiderweb")
    box(1402, 2600, 130, 5, G0 + 2.15, G0 + 2.22, "play_steel", "أرجوحة شبكة — العارضة", "spiderweb")
    # 3 swing set (frame x 1315..1715, y 2531) with 3 seats
    for xx in (1315, 1715): box(xx, 2531, 6, 6, G0, G0 + 2.3, "play_steel", "أرجوحة — عمود", "swing")
    box(1515, 2531, 400, 6, G0 + 2.25, G0 + 2.33, "play_steel", "أرجوحة — العارضة", "swing")
    for xx in (1440, 1515, 1590): box(xx, 2531, 35, 16, G0 + 0.45, G0 + 0.5, "play_blue", "أرجوحة — مقعد", "swing")
    # 4 sea-saws x3
    for i, (xx, yy) in enumerate(((1293, 2802), (1249, 2702), (1206, 2601)), 1):
        box(xx, yy, 120, 18, G0 + 0.35, G0 + 0.42, "play_yellow", f"أرجوحة التوازن {i}", f"seesaw{i}"); box(xx, yy, 14, 14, G0, G0 + 0.35, "play_steel", "أرجوحة التوازن — محور", f"seesaw{i}")
    # 5 go-round (1896,2481 r 65)
    cyl(1896, 2481, 65, G0 + 0.2, G0 + 0.28, "play_blue", "دوّارة الأطفال — القرص", "goround"); cyl(1896, 2481, 4, G0, G0 + 0.9, "play_steel", "دوّارة — المحور", "goround")
    for k in range(3):
        a = k * 2 * math.pi / 3 + 0.5; box(round(1896 + 38 * math.cos(a)), round(2481 + 38 * math.sin(a)), 40, 12, G0 + 0.28, G0 + 0.75, "play_red", "دوّارة — مقعد", "goround", ang=round(math.degrees(a)) + 90)
    # 6 spring riders x2 (2088,2455) (2190,2462)
    for i, (xx, yy) in enumerate(((2088, 2455), (2190, 2462)), 1):
        cyl(xx, yy, 14, G0, G0 + 0.05, "play_steel", "حصان زنبركي — القاعدة", f"spring{i}"); cyl(xx, yy, 3, G0 + 0.05, G0 + 0.45, "play_steel", "حصان زنبركي — النابض", f"spring{i}")
        box(xx, yy, 24, 70, G0 + 0.45, G0 + 0.78, "play_yellow", "حصان زنبركي — الجسم", f"spring{i}", ang=0)
    # 7 three-slide set: decks, ladder, bridge, slides
    for name, x0, x1 in (("A", 1601, 1692), ("B", 1773, 1864), ("C", 1941, 2032)):
        cx = (x0 + x1) / 2
        for sx in (x0 + 4, x1 - 4):
            for sy in (2832, 2909): box(sx, sy, 7, 7, G0, G0 + 1.4, "play_steel", f"برج {name} — عمود", f"slideset-{name}")
        box(cx, 2870, x1 - x0, 85, G0 + 1.2, G0 + 1.28, "play_yellow", f"برج {name} — المنصة", f"slideset-{name}")
        # roof: pyramid of two triangles pairs (simple gable)
        out.append(_e("A.stage", "play_part", ["tri", [[x0 - 5, 2825, G0 + 2.2], [x1 + 5, 2825, G0 + 2.2], [cx, 2870, G0 + 2.6]], 1.5], "play_red", f"برج {name} — مظلة", {"kind": "play", "name_ar": f"برج {name} — مظلة", "assumed": "الارتفاعات افتراض (المخطط يعطي المسقط فقط)"}, S, f"slideset-{name}"))
        out.append(_e("A.stage", "play_part", ["tri", [[x0 - 5, 2915, G0 + 2.2], [x1 + 5, 2915, G0 + 2.2], [cx, 2870, G0 + 2.6]], 1.5], "play_red", f"برج {name} — مظلة", {"kind": "play", "name_ar": f"برج {name} — مظلة", "assumed": "الارتفاعات افتراض (المخطط يعطي المسقط فقط)"}, S, f"slideset-{name}"))
    box(1650, 2780, 50, 90, G0, G0 + 1.2, "play_steel", "سلّم الدخول", "slideset-A", ang=0)
    box(1732, 2870, 82, 6, G0 + 1.0, G0 + 1.08, "play_net", "جسر الحبال", "slideset-AB")
    out.append(_e("A.stage", "play_part", ["rs", [[1817, 2828, G0 + 1.2], [1817, 2640, G0 + 0.05]], 57, 0.05], "play_yellow", "زحليقة طويلة", {"kind": "play", "name_ar": "زحليقة طويلة", "assumed": "الارتفاعات افتراض (المخطط يعطي المسقط فقط)"}, S, "slideset-B"))
    out.append(_e("A.stage", "play_part", ["rs", [[1602, 2868, G0 + 1.2], [1412, 2868, G0 + 0.05]], 55, 0.05], "play_blue", "زحليقة عريضة", {"kind": "play", "name_ar": "زحليقة عريضة", "assumed": "الارتفاعات افتراض (المخطط يعطي المسقط فقط)"}, S, "slideset-A"))
    cyl(2045, 2804, 85, G0, G0 + 1.0, "play_blue", "زحليقة حلزونية (تقريبية: أسطوانة)", "slideset-C")
    return out

def gazebo(cx, cy):
    """A2305 gazebo: round 680 cm, floor +0.95, 8 steel posts 200 mm to +3.95, wooden lattice on the four diagonal sides (benches there), hip roof to +5.00"""
    out = []; R = 330; ZF, ZW, ZR = 0.95, 3.95, 5.00
    out.append(_e("A.site", "gazebo_floor", ["cyl", cx, cy, 340, 0.2, ZF], "paving_wood", "GAZEBO", {"kind": "gazebo_floor", "note": "منصة +0.95 (A2305) — ⌀680 سم"}, grp="gazebo"))
    corners = [(cx + R * math.cos(math.radians(22.5 + 45 * k)), cy + R * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]
    for k, (x, y) in enumerate(corners, 1):
        out.append(_e("A.site", "gazebo_post", ["cyl", round(x), round(y), 10, ZF, ZW], "steel_post", f"GAZEBO-P{k}", {"kind": "post", "dia_mm": 200}, grp="gazebo"))
    for k in range(8):
        a, b = corners[k], corners[(k + 1) % 8]
        mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2; L = math.hypot(b[0] - a[0], b[1] - a[1]); ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
        out.append(_e("A.site", "gazebo_rail", ["b", round(mx), round(my), round(L), 8, round(ang), ZW - 0.5, ZW], "wood_slat", f"GAZEBO-R{k+1}", {"kind": "top_rail", "height_cm": 50}, grp="gazebo"))
        out.append(_e("A.site", "gazebo_rail", ["b", round(mx), round(my), round(L), 8, round(ang), ZF, ZF + 0.4], "wood_slat", f"GAZEBO-B{k+1}", {"kind": "bottom_rail", "height_cm": 40}, grp="gazebo"))
        if k % 2 == 1:    # diagonal sides: lattice panel + bench
            out.append(_e("A.site", "gazebo_lattice", ["b", round(mx), round(my), round(L - 24), 3, round(ang), ZF + 0.4, ZW - 0.5], "wood_lattice", f"GAZEBO-L{k+1}", {"kind": "lattice", "assumed": "الشبك الخشبي على الأضلاع القطرية الأربعة (حيث المقاعد في المسقط)؛ الدقة البصرية للشبك لا تُرسم"}, grp="gazebo"))
            nx, ny = (cx - mx), (cy - my); nl = math.hypot(nx, ny); nx, ny = nx / nl, ny / nl
            out.append(_e("A.site", "gazebo_bench", ["b", round(mx + nx * 40), round(my + ny * 40), round(L - 60), 40, round(ang), ZF, ZF + 0.45], "wood_slat", f"GAZEBO-S{k+1}", {"kind": "bench", "assumed": "المقعد 40 سم عمق × 45 سم ارتفاع تقديري من المسقط"}, grp="gazebo"))
    apex = [round(cx), round(cy), ZR]; RO = 345
    ring = [(cx + RO * math.cos(math.radians(22.5 + 45 * k)) / math.cos(math.radians(0)), cy + RO * math.sin(math.radians(22.5 + 45 * k))) for k in range(8)]
    for k in range(8):
        a, b = ring[k], ring[(k + 1) % 8]
        out.append(_e("A.site", "gazebo_roof", ["tri", [[round(a[0]), round(a[1]), ZW], [round(b[0]), round(b[1]), ZW], apex], 6], "wood_slat", f"GAZEBO-T{k+1}", {"kind": "roof", "note": "سقف هرمي ثماني من عوارض/لوفر خشبية — الارتفاع +3.95 إلى +5.00 (A2305)"}, grp="gazebo"))
    return out

def all_elements(L, beds, gz):
    return plants(L, beds) + benches(L) + shed() + fence() + play() + gazebo(*gz)
