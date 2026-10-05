# -*- coding: utf-8 -*-
"""Vehicle ramp (G -> B) + its guard walls, and the external pedestrian stair 03 (G -> B) with its upstand walls and hand rails
   ->  pipeline/data/ramp_stair.json     (no PDFs needed: every number below was read from the drawings, the sources are written on each element)

Why: the 3-D model had the openings of both in the ground slab but neither the ramp nor the stair, so the whole basement access was missing and the
devices drawn on the stair (EXIT, call point, bell, speaker ...) hovered over an empty hole.
Sources
  ARCH2 p7  A606 RAMP DETAILS 01   : slope 16.5 %, transition ramp 8 % x 300 cm at the lower end, 6 m wide drive way, basement F.F.L. -3.70/-3.60
  STR   p28 S-23 RAMP DETAILS      : ramp slab TH = 35 cm, width 600 between the walls, top of ramp slab at the G slab (-0.10), end level -3.90 (raft)
  ARCH1 p5/p4 A102/A101            : opening in the ground slab (centre line = straight band y 3810..4410 + 90 deg arc R=400..1000 about (2920,3410))
  ARCH2 p5  A604 STAIR DETAILS 03  : 22 steps, riser 16.81 cm, thread 30 cm, width 120 cm, landing F.F.L. -1.65, bottom -3.50, G paving +0.20, wall top H.L +1.40,
                                     two flights separated by a 20 cm divider, 130/120 cm landings, galvanized steel door D16 (90 min), finish W12 porcelain
Assumed (flagged on the elements): ramp surface finish and guard-wall height (+1.40 as on A604), hand-rail tube diameter / height, step block depth.
"""
import json, math, os
from shapely.geometry import Polygon, box
HERE = os.path.dirname(os.path.abspath(__file__))
M = json.load(open(os.path.join(HERE, "..", "src", "model.json"), encoding="utf-8"))
els = []

def add(c, l, g, mark, typ, mat, attrs, src):
    els.append({"c": c, "l": l, "g": g, "mark": mark, "t": typ, "m": mat, "a": attrs, "src": src})

# ================================================================= vehicle ramp
Z0 = 0.10                                   # F.F.L. +0.10 DRIVE WAY (A102)
SLOPE, TRANS, TRANS_SLOPE = 0.165, 300.0, 0.08
C = (2920.0, 3410.0); RC = 700.0            # arc centre and centre-line radius (inner 400, outer 1000)
Y_STRAIGHT, X_END = 4110.0, 1550.0
arc_len = math.pi / 2 * RC; st_len = C[0] - X_END; S_TOT = arc_len + st_len; L1 = S_TOT - TRANS
def z_at(s):
    if s <= L1: return Z0 - SLOPE * s / 100.0
    return Z0 - SLOPE * L1 / 100.0 - TRANS_SLOPE * (s - L1) / 100.0
pts = []
N = 18
for k in range(N + 1):
    a = k * (math.pi / 2) / N; s = a * RC
    pts.append((C[0] + RC * math.cos(a), C[1] + RC * math.sin(a), s))
s_L1 = L1; pts.append((C[0] - (L1 - arc_len), Y_STRAIGHT, L1)); pts.append((X_END, Y_STRAIGHT, S_TOT))
# split at the underside of the G slab (-0.45): upper part belongs to G, the rest to B
Z_SPLIT = -0.45
up, low = [], []
for i, p in enumerate(pts):
    z = z_at(p[2])
    if z >= Z_SPLIT: up.append([round(p[0], 1), round(p[1], 1), round(z, 3)])
    else:
        if not low and up:                         # shared boundary point
            q = pts[i - 1]; f = (Z_SPLIT - z_at(q[2])) / (z - z_at(q[2])) if z != z_at(q[2]) else 0
            bx = q[0] + (p[0] - q[0]) * f; by = q[1] + (p[1] - q[1]) * f
            up.append([round(bx, 1), round(by, 1), Z_SPLIT]); low.append([round(bx, 1), round(by, 1), Z_SPLIT])
        low.append([round(p[0], 1), round(p[1], 1), round(z, 3)])
RAMP_SRC = ["ARCH2 ص7 (A606 RAMP DETAILS 01): ميل 16.5% + منحدر انتقالي 8% بطول 300 سم + عرض الممر 6 م", "STR ص28 (S-23 RAMP DETAILS): سماكة بلاطة المنحدر TH=35 سم، العرض 600 سم", "ARCH1 ص4-5 (A101/A102): مسار المنحدر (مستقيم + قوس 90° نق 400–1000 حول (2920,3410))"]
RAMP_A = {"kind": "ramp", "width_cm": 600, "slope_pct": 16.5, "transition_pct": 8, "transition_cm": 300, "thick_cm": 35,
          "z_note": f"المنسوب العلوي من +0.10 (درب السيارات A102) إلى {round(z_at(S_TOT),2)} م؛ طول المسار {round(S_TOT)} سم محسوب من الهندسة ومتّسق مع الفرق −3.70 م (A101)",
          "finish_note": "تشطيب سطح المنحدر غير محدد في المستندات المتاحة — يُعرض خرسانة (افتراض يحتاج تأكيد)"}
if len(up) >= 2: add("S.ramp", "G", ["rs", up, 600, 0.35], "RAMP-1", "ramp_slab", "conc", dict(RAMP_A, part="الجزء العلوي فوق بلاطة الدور الأرضي"), RAMP_SRC)
if len(low) >= 2: add("S.ramp", "B", ["rs", low, 600, 0.35], "RAMP-1", "ramp_slab", "conc", dict(RAMP_A, part="الجزء السفلي في البدروم"), RAMP_SRC)

# guard walls around the opening of the ground slab (the entrance edge y=3410, x 3320..3920 stays open)
HOLE = None
for e in M["els"]:
    if e["c"] == "S.slab" and e["l"] == "G" and e["g"][0] == "p":
        for h in (e["g"][4] or []):
            ys = [p[1] for p in h]
            if len(h) > 20 and max(ys) > 4000: HOLE = Polygon(h).buffer(0)
WALL_Z0, WALL_Z1, WALL_T = -0.45, 1.40, 30.0
def ring_walls(hole, thick, gap_boxes, mark, srcs, typ="wall_rc", attrs=None):
    ring = hole.buffer(thick, join_style=2).difference(hole)
    for gb in gap_boxes: ring = ring.difference(gb)
    geoms = list(ring.geoms) if hasattr(ring, "geoms") else [ring]
    n = 0
    for g_ in geoms:
        if g_.is_empty or g_.area < 400: continue
        ext = [[round(x, 1), round(y, 1)] for x, y in list(g_.exterior.coords)[:-1]]
        add("S.wall", "G", ["p", ext, WALL_Z0, WALL_Z1], mark, typ, "conc", dict(attrs or {}, kind="guard_wall", thick_cm=thick, top_m=WALL_Z1), srcs); n += 1
    return n
if HOLE is not None:
    ring_walls(HOLE, WALL_T, [box(3300, 3380, 3940, 3445)], "RAMP-WALL", RAMP_SRC + ["ارتفاع جدار الحماية +1.40 م: كما في تفصيل الدرج A604 (H.L +1.40) — افتراض لجدران المنحدر يحتاج تأكيد"],
               attrs={"height_note": "قمة الجدار +1.40 م (افتراض: كما A604)"})

# ================================================================= external stair 03
RISER, TREAD, TOPG, MID, BOT = 16.81, 30.0, 0.20, -1.65, -3.50
X_R0, X_R1 = 4150.0, 4270.0                 # right flight (enters from G, goes south)
X_L0, X_L1 = 4010.0, 4130.0                 # left flight (goes back north to the basement door D16)
Y_TOP, Y_MID0, Y_MID1 = 1545.0, 1125.0, 1245.0
STAIR_SRC = ["ARCH2 ص5 (A604 STAIR DETAILS 03): 22 درجة، ارتفاع القائمة 16.81 سم، العمق 30 سم، العرض 120 سم، منسوب +0.20 / −1.65 / −3.50", "ARCH1 ص4-5 (A101/A102): امتداد الدرج في المسقط (طبقة stairs)"]
STEP_BLOCK = 0.30
def level_of(z): return "G" if z >= -0.45 else "B"
for i in range(1, 11):                      # right flight
    zt = TOPG - RISER / 100 * i; y1 = Y_TOP - TREAD * (i - 1); y0 = y1 - TREAD
    add("S.stair", level_of(zt), ["r", X_R0, y0, X_R1, y1, round(zt - STEP_BLOCK, 3), round(zt, 3)], f"درج خارجي 03 — {i}", "stair_step", "conc", {"kind": "stair_step", "flight": "R", "n": i}, STAIR_SRC)
for j in range(1, 11):                      # left flight
    zt = MID - RISER / 100 * j; y0 = Y_MID1 + TREAD * (j - 1); y1 = y0 + TREAD
    add("S.stair", level_of(zt), ["r", X_L0, y0, X_L1, y1, round(zt - STEP_BLOCK, 3), round(zt, 3)], f"درج خارجي 03 — {11 + j}", "stair_step", "conc", {"kind": "stair_step", "flight": "L", "n": 11 + j}, STAIR_SRC)
add("S.stair", "B", ["r", X_L0, Y_MID0, X_R1, Y_MID1, MID - 0.30, MID], "درج خارجي 03 — البسطة الوسطى", "stair_landing", "conc", {"kind": "landing", "level_m": MID}, STAIR_SRC)
add("S.stair", "B", ["r", X_L0, Y_TOP, X_L1, 1650.0, BOT - 0.30, BOT], "درج خارجي 03 — البسطة السفلية", "stair_landing", "conc", {"kind": "landing", "level_m": BOT}, STAIR_SRC)
# hand rails along the divider (stainless tube, 100 cm above the nosing line: assumed)
HR_A = {"kind": "handrail", "dia_cm": 4.8, "h_cm": 100, "note": "قطر الأنبوب (4.8 سم) وارتفاعه 100 سم: افتراض؛ المخطط يبيّن ارتفاع الحاجز H.L +1.40 م فقط"}
zR0 = TOPG + 1.0; zR1 = TOPG - RISER / 100 * 10 + 1.0
add("A.rail", "G", ["t", [[4145.0, Y_TOP + 20, zR0], [4145.0, Y_TOP, zR0], [4145.0, Y_MID1, zR1]], 4.8], "درابزين الدرج 03 — الجناح الأول", "stair_handrail", "frame_alu", HR_A, STAIR_SRC)
zL0 = MID + 1.0; zL1 = MID - RISER / 100 * 10 + 1.0
add("A.rail", "B", ["t", [[4135.0, Y_MID1, zL0], [4135.0, Y_TOP, zL1], [4135.0, Y_TOP + 20, zL1]], 4.8], "درابزين الدرج 03 — الجناح الثاني", "stair_handrail", "frame_alu", HR_A, STAIR_SRC)
# upstand walls at ground level around the stair opening (hole 3990..4300 x 1180..1620), door D16 opening kept
ring_walls(box(3990, 1180, 4300, 1620), 30.0, [box(4005, 1590, 4140, 1660)], "STAIR03-WALL", STAIR_SRC + ["ARCH2 ص5: قمة الجدار H.L +1.40 م؛ الكسوة W12 بورسلين 60×120 سم"], attrs={"cladding": "W12 بورسلين 60×120 سم، 2 سم (A604)"})

TYPES = {
    "ramp_slab": {"n": "بلاطة منحدر السيارات (خرسانة مسلّحة 35 سم) — دور أرضي → بدروم", "cf": "derived",
                  "sp": [["العرض", "6 م بين الجدران"], ["السماكة", "35 سم (S-23)"], ["الميل", "16.5% + منحدر انتقالي 8% بطول 3 م في الطرف السفلي"], ["المنسوب", "من +0.10 م (الدرب) إلى −3.70 م (البدروم)"], ["شكل المسار", "مستقيم + قوس 90° نق 4–10 م + مستقيم"]],
                  "asm": ["تشطيب سطح المنحدر غير محدد في المستندات", "نقطة بداية المسار على حافة فتحة البلاطة (y=3410)"], "sr": ["ARCH2 ص7 (A606)", "STR ص28 (S-23)"]},
    "stair_handrail": {"n": "درابزين ستانلس للدرج الخارجي 03", "cf": "derived", "sp": [["الأنبوب", "ستانلس ⌀48 مم (افتراض)"], ["الارتفاع", "100 سم فوق خط الدرجات (افتراض)"]], "asm": ["مواصفات الدرابزين غير مذكورة في A604"], "sr": ["ARCH2 ص5 (A604)"]},
}
json.dump({"els": els, "types": TYPES, "mats": {}}, open(os.path.join(HERE, "data", "ramp_stair.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("ramp/stair elements:", len(els), "| ramp length", round(S_TOT), "cm, end level", round(z_at(S_TOT), 3), "| split points up/low", len(up), len(low))
