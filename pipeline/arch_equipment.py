# -*- coding: utf-8 -*-
"""Underground water tanks (A2500 'WATER TANK DETAILS', ARCH2 p57) and realistic colours for the equipment proxies.

A2500 (plan 1:50 + sections 01/02), measured from the drawing's own wall fills (cm, relative to the outer lower-left corner of the tank block; registered to the building by
the basement walls that already exist in the model: block interior x 1..850, y 1066..2385  =  drawing x 30..880, y 45..1365  ->  world = rel + (-29, +1021)):
    FIRE TANK  (left)   x  30..285  y   45..1218   255 x 1173   A = 32.5 m2  V = 97.5 m3  22,500 USG
    FIRE TANK  (right)  x 305..555  y  200..1365   250 x 1165   A = 32.5 m2  V = 97.5 m3  22,500 USG
    RCC WATER FOR DOMESTIC   x 580..880 y  45..360  300 x 315   A = 9.45 m2  V = 28.35 m3  5,500 USG
    RCC WATER FOR IRRIGATION x 580..880 y 380..525  300 x 145   A = 4.35 m2  V = 13.05 m3  2,500 USG
    IRRIGATION PUMP ROOM     x 580..885 y 550..760  305 x 210   A = 6.4 m2   (door D13 on the east side)
    floor -3.90 (SSL), water level -0.90, clear height 3.50, 30 cm roof slab (the ground-floor slab), 25 cm walls, 20 cm party wall between the fire tanks, GRP ladders, 80x80 access hatches.
Hatch / ladder positions are not dimensioned on the sheet (only drawn): placed at the corner next to the pump-room door and flagged as an assumption.
"""
import collections
from shapely.geometry import box, Polygon
from shapely.ops import unary_union

DX, DY = -29.0, 1021.0
Z_FLOOR, Z_WATER, Z_TOP = -3.90, -0.90, -0.40
WALLS_REL = [(285, 200, 305, 1218), (285, 180, 580, 200), (0, 1218, 305, 1238), (555, 360, 910, 380), (555, 525, 905, 550), (555, 200, 580, 360), (555, 380, 580, 525),
             (555, 550, 580, 1365), (880, 45, 905, 330), (880, 380, 910, 490), (555, 45, 580, 180)]
TANKS = [  # id, name, interior rel x0,y0,x1,y1, A m2, V m3, USG, service
    ("FT1", "خزان حريق 1", (30, 45, 285, 1218), 32.5, 97.5, 22500, "fire"),
    ("FT2", "خزان حريق 2", (305, 200, 555, 1365), 32.5, 97.5, 22500, "fire"),
    ("DT", "خزان مياه الاستعمال المنزلي", (580, 45, 880, 360), 9.45, 28.35, 5500, "domestic"),
    ("IT", "خزان مياه الري", (580, 380, 880, 525), 4.35, 13.05, 2500, "irrigation"),
]
SRC = ["ARCH2 ص57 (A2500 WATER TANK DETAILS — مسقط وقطاعان)", "MECH2 ص18 (WS-100 مخطط خزانات البدروم)", "BOQ 10.1.6"]

MATS = {
    "tank_water": {"name": "ماء الخزان (منسوب −0.90)", "color": "#4f93ba", "opacity": 0.55, "code": "A2500", "rough": 0.05, "metal": 0.0},
    "tank_conc": {"name": "خرسانة مسلحة مقاومة للكبريتات — خزان (SRC)", "color": "#8f918c", "code": "A2500", "rough": 0.9},
    "tank_lid": {"name": "غطاء فتحة الخزان — فولاذ مجلفن مع إطار", "color": "#9aa0a6", "code": "A2500", "metal": 0.6, "rough": 0.4},
    "grp_ladder": {"name": "سلّم GRP أصفر داخل الخزان", "color": "#d6b739", "code": "A2500", "rough": 0.5},
}
# realistic colours for the equipment proxies (the saturated discipline colours made them look like toy cubes): neutral metal / enamel
PROXY_COLORS = {"m_fcu": "#c9cdd2", "p_heater": "#f1f0ec", "m_chiller": "#d5dce3", "m_fahu": "#c4ccd4", "m_pump": "#5d6b79", "m_gen": "#cfcbbf", "m_panel": "#aeb6bf", "m_fan": "#b5bcc3",
                "m_damper": "#8d949b", "p_valve": "#6a727a", "m_therm": "#f2efe6", "m_diffuser": "#f3f1ec", "m_diffuser_r": "#f3f1ec", "m_grille": "#e9e7e1", "m_grille_r": "#e9e7e1"}


def _rect(x0, y0, x1, y1, z0, z1):
    return ["r", round(min(x0, x1), 1), round(min(y0, y1), 1), round(max(x0, x1), 1), round(max(y0, y1), 1), round(z0, 3), round(z1, 3)]


def _el(typ, mat, g, mark, a=None, grp=None, extra_src=None):
    e = {"c": "P.tank", "l": "B", "g": g, "mark": mark, "t": typ, "m": mat, "a": a or {}, "src": SRC + (extra_src or [])}
    if grp: e["grp"] = grp
    return e


def build(M):
    els = []
    walls_b = []
    for e in M["els"]:
        if e["l"] == "B" and e["c"] in ("A.wall", "S.wall", "S.col") and e["g"][0] in ("p", "r") and "-X" not in e["id"][-6:]:
            g = e["g"]
            if g[0] == "r": walls_b.append(box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4])))
            else:
                try:
                    q = Polygon(g[1], [h for h in (g[4] if len(g) > 4 and g[4] else []) if len(h) >= 3])
                    walls_b.append(q if q.is_valid else q.buffer(0))
                except Exception:
                    pass
    have = unary_union(walls_b) if walls_b else None
    # partition walls that the model does not have yet
    for k, (a, b, c, d) in enumerate(WALLS_REL):
        r = box(a + DX, b + DY, c + DX, d + DY)
        if have is not None and r.intersection(have).area > 0.6 * r.area: continue
        els.append(_el("tank_wall", "tank_conc", _rect(a + DX, b + DY, c + DX, d + DY, Z_FLOOR, Z_TOP + 0.30), f"TANK-W{k + 1}",
                       {"thk_cm": round(min(c - a, d - b)), "note": "جدار خرساني للخزان من A2500"}))
    for tid, name, (a, b, c, d), area, vol, usg, svc in TANKS:
        x0, y0, x1, y1 = a + DX, b + DY, c + DX, d + DY
        els.append(_el("tank_water", "tank_water", _rect(x0, y0, x1, y1, Z_FLOOR, Z_WATER), tid,
                       {"kind": name, "area_m2": area, "vol_m3": vol, "usg": usg, "water_level_m": Z_WATER, "clear_h_m": 3.5,
                        "note": "حجم الماء داخل الخزان حتى منسوب −0.90 م؛ الخزان مغلق بالبلاطة (A2500)"}, grp="TANK-" + tid))
        # hatch + ladder next to the pump-room side (east) of every tank, 80 x 80 cm
        hx = x1 - 55 if tid in ("DT", "IT") else x1 - 60
        hy = y1 - 60 if tid != "FT1" else y1 - 60
        els.append(_el("tank_hatch", "tank_lid", _rect(hx - 40, hy - 40, hx + 40, hy + 40, 0.34, 0.37), tid + "-H",
                       {"kind": "فتحة نزول 80×80 سم بغطاء فولاذي (A2500: WATER TANK ACCESS ABOVE)", "assumed": "الموضع تقريبي: الفتحة مرسومة بلا إحداثيات في A2500"}, grp="TANK-" + tid))
        z = Z_FLOOR + 0.05
        for sx in (-20, 20):
            els.append(_el("tank_ladder", "grp_ladder", _rect(hx + sx - 2, hy - 2, hx + sx + 2, hy + 2, Z_FLOOR, 0.30), tid + "-L", {"kind": "سلّم GRP — عمود جانبي"}, grp="TANK-" + tid))
        zz = Z_FLOOR + 0.30
        while zz < 0.25:
            els.append(_el("tank_ladder", "grp_ladder", _rect(hx - 20, hy - 1.5, hx + 20, hy + 1.5, zz, zz + 0.03), tid + "-L", {"kind": "سلّم GRP — درجة"}, grp="TANK-" + tid))
            zz += 0.30
    return {"els": els, "mats": MATS}


def types():
    return {
        "tank_water": {"n": "خزان مياه خرساني تحت الأرض (RCC) — حجم الماء", "cf": "doc",
                       "sp": [["الأنواع (A2500)", "حريق 2 × (32.5 م² — 97.5 م³ — 22500 جالون أمريكي)، منزلي (9.45 م² — 28.35 م³ — 5500)، ري (4.35 م² — 13.05 م³ — 2500)"],
                              ["منسوب القاع", "−3.90 م (SSL)"], ["منسوب الماء", "−0.90 م"], ["الارتفاع الصافي", "3.50 م"], ["الجدران", "RCC بسمك 25 سم وفاصل 20 سم بين خزّانَي الحريق"],
                              ["BOQ 10.1.6", "حريق 195 م³، منزلي 28.4 م³، ري 13.5 م³ (مستبعدة من السعر EXCLUDED)"]],
                       "asm": ["البعد من جدران الرسم (25 سم) ومن تسجيل المخطط على جدران البدروم الموجودة في النموذج (تطابق بالسنتيمتر)"], "sr": SRC},
        "tank_wall": {"n": "جدار خزان خرساني (RCC)", "cf": "doc", "sp": [["السماكة", "20–25 سم"], ["الخرسانة", "40 نيوتن/مم² مقاومة للكبريتات SRC (S-8)"]], "sr": SRC},
        "tank_hatch": {"n": "فتحة نزول الخزان 80×80 سم", "cf": "derived", "sp": [["المقاس", "80 × 80 سم"], ["الغطاء", "فولاذ مجلفن بإطار، مستوى أرضية المضخات +0.35"]],
                       "asm": ["الموضع تقريبي: الفتحة مرسومة بلا إحداثيات في A2500"], "sr": SRC},
        "tank_ladder": {"n": "سلّم GRP داخل الخزان", "cf": "derived", "sp": [["المادة", "GRP — سلّم نزول من الفتحة إلى القاع"], ["درجات", "كل 30 سم"]],
                        "asm": ["العرض 40 سم وعدد الدرجات تقدير من الرسم"], "sr": SRC},
    }
