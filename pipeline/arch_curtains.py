# -*- coding: utf-8 -*-
"""Curtains of the flats (staged: not in the drawings, shown to make the rooms read as lived-in; one switch hides them).

Every living / bedroom window module of A801 / A802 (data/win_modules.json, the same modules arch_windows.py builds the frames from) gets a floor-to-ceiling curtain on a ceiling track, 16 cm inside the
window plane (clear of the 60 cm block sill, A1500).  The state of each window is chosen deterministically (hash of the module id) so the building looks varied but stays reproducible:

  drawn   heavy curtain drawn across the whole window                         ~22 %
  sheer   only the light (sheer) curtain closed, the heavy one bundled aside ~28 %
  open    heavy curtain bundled at both sides, nothing across the glass      ~35 %
  half    heavy curtain drawn over one half, sheer closed across             ~15 %

Kitchens (A1204: no curtains), the stair window and modules without a unit get none.  Geometry kind 'cur' = pleated vertical sheet along a plan segment (viewer: engine.js curtain()).
"""
import zlib, math
import arch_windows as AW

HEAVY = ["cur_beige", "cur_taupe", "cur_gray", "cur_ivory", "cur_blue"]
MATS = {
    "cur_beige": {"name": "ستارة قماش ثقيلة — بيج (إخراجي)", "color": "#cdbfa5", "rough": 0.95, "code": "stage"},
    "cur_taupe": {"name": "ستارة قماش ثقيلة — بني رمادي (إخراجي)", "color": "#a39080", "rough": 0.95, "code": "stage"},
    "cur_gray": {"name": "ستارة قماش ثقيلة — رمادي (إخراجي)", "color": "#8c9197", "rough": 0.95, "code": "stage"},
    "cur_ivory": {"name": "ستارة قماش ثقيلة — عاجي (إخراجي)", "color": "#e6dfcf", "rough": 0.95, "code": "stage"},
    "cur_blue": {"name": "ستارة قماش ثقيلة — أزرق رمادي (إخراجي)", "color": "#6f8497", "rough": 0.95, "code": "stage"},
    "cur_sheer": {"name": "ستارة خفيفة شفافة — أبيض (إخراجي)", "color": "#f5f3ec", "opacity": 0.5, "rough": 0.9, "code": "stage"},
    "cur_rail": {"name": "سكة ستارة ألمنيوم (إخراجي)", "color": "#b9bec3", "metal": 0.4, "rough": 0.4, "code": "stage"},
}
SRC = ["إخراجي — الستائر غير مرسومة في المخططات؛ المواضع من وحدات النوافذ A801/A802 وعتبة A1500 (60 سم)"]
INSET = 16.0        # cm inside the window plane
OVER = 10.0         # cm overhang at each side of the module
Z_TOP = 2.36        # under the false ceiling (+2.40)
Z_BOT = 0.04


def _state(mod):
    h = zlib.crc32(("cur" + mod["grp"] + mod["l"]).encode()) % 100
    return "drawn" if h < 22 else "sheer" if h < 50 else "open" if h < 85 else "half"


def _skip(mod):
    loc = mod.get("loc") or ""
    return (not mod.get("u")) or mod["t"] == "win_CW-19" or loc.startswith("المطبخ")


def build(M):
    L = {l["id"]: l for l in M["levels"]}
    els = []
    for mod in AW.modules(M):
        if _skip(mod) or mod["l"] not in L: continue
        o, u, n, length = AW._frame(mod)
        ffl = L[mod["l"]]["ffl"]
        z0, z1 = ffl + 0.012 + Z_BOT, ffl + Z_TOP
        heavy = HEAVY[zlib.crc32(("c" + str(mod.get("u")) + mod["grp"]).encode()) % len(HEAVY)]
        st = _state(mod)
        A0, A1 = -OVER, length + OVER
        W_ = A1 - A0
        bw = max(30.0, 0.18 * W_)

        def seg(a, b):
            return (o[0] + u[0] * a - n[0] * INSET, o[1] + u[1] * a - n[1] * INSET, o[0] + u[0] * b - n[0] * INSET, o[1] + u[1] * b - n[1] * INSET)

        def add(a, b, mat, folds, amp, part, t):
            x0, y0, x1, y1 = seg(a, b)
            e = {"c": "A.stage", "l": mod["l"], "g": ["cur", round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1), round(z0, 3), round(z1, 3), folds, amp], "mark": "ستارة", "t": t, "m": mat,
                 "a": {"kind": "ستارة", "state": {"drawn": "منسدلة (مغلقة)", "sheer": "القطعة الخفيفة مغلقة والثقيلة مفتوحة", "open": "مفتوحة", "half": "نصف منسدلة"}[st], "part": part,
                       "w_cm": round(abs(b - a)), "loc": mod["loc"]},
                 "src": SRC, "grp": "CUR-" + mod["grp"], "stage": "curtain"}
            if mod.get("u"): e["u"] = mod["u"]
            els.append(e)

        if st == "drawn":
            add(A0, A1, heavy, max(4, round(W_ / 11)), 3.2, "ستارة ثقيلة منسدلة", "curtain_heavy")
        elif st == "sheer":
            add(A0, A1, "cur_sheer", max(4, round(W_ / 9)), 1.4, "ستارة خفيفة مغلقة", "curtain_sheer")
            add(A0, A0 + bw, heavy, max(3, round(bw / 8)), 3.6, "ستارة ثقيلة مجمّعة (يسار)", "curtain_heavy")
            add(A1 - bw, A1, heavy, max(3, round(bw / 8)), 3.6, "ستارة ثقيلة مجمّعة (يمين)", "curtain_heavy")
        elif st == "open":
            add(A0, A0 + bw, heavy, max(3, round(bw / 8)), 3.6, "ستارة ثقيلة مجمّعة (يسار)", "curtain_heavy")
            add(A1 - bw, A1, heavy, max(3, round(bw / 8)), 3.6, "ستارة ثقيلة مجمّعة (يمين)", "curtain_heavy")
        else:                                                   # half: heavy drawn over the left half, bundled at the right, sheer across
            mid = (A0 + A1) / 2
            add(A0, A1, "cur_sheer", max(4, round(W_ / 9)), 1.4, "ستارة خفيفة مغلقة", "curtain_sheer")
            add(A0, mid, heavy, max(3, round((mid - A0) / 11)), 3.2, "ستارة ثقيلة منسدلة (نصف)", "curtain_heavy")
            add(A1 - bw, A1, heavy, max(3, round(bw / 8)), 3.6, "ستارة ثقيلة مجمّعة (يمين)", "curtain_heavy")
        # ceiling track
        x0, y0, x1, y1 = seg(A0, A1)
        e = {"c": "A.stage", "l": mod["l"], "g": ["t", [[round(x0, 1), round(y0, 1), round(z1 + 0.02, 3)], [round(x1, 1), round(y1, 1), round(z1 + 0.02, 3)]], 2.4], "mark": "سكة ستارة", "t": "curtain_rail", "m": "cur_rail",
             "a": {"kind": "سكة ستارة", "w_cm": round(W_)}, "src": SRC, "grp": "CUR-" + mod["grp"], "stage": "curtain"}
        if mod.get("u"): e["u"] = mod["u"]
        els.append(e)
    return {"els": els, "mats": MATS}


def types():
    S = SRC
    return {
        "curtain_heavy": {"n": "ستارة قماش ثقيلة (إخراجية)", "cf": "assumed",
                          "sp": [["الموضع", "على سكة سقفية خلف مستوى النافذة بـ16 سم، من +0.05 إلى +2.36 م"], ["الحالة", "تتنوع بين منسدلة / مجمّعة / نصف منسدلة بحسب النافذة (قيمة عشوائية ثابتة)"]],
                          "asm": ["الستائر غير مرسومة في المخططات؛ اللون والقماش والحالة افتراضات للعرض فقط، وتُخفى من «الكماليات → ستائر»"], "sr": S},
        "curtain_sheer": {"n": "ستارة خفيفة شفافة (إخراجية)", "cf": "assumed", "sp": [["الموضع", "نفس سكة الستارة الثقيلة، قماش شفاف أبيض بشفافية 50%"]],
                          "asm": ["افتراض للعرض فقط"], "sr": S},
        "curtain_rail": {"n": "سكة ستارة (إخراجية)", "cf": "assumed", "sp": [["الموضع", "تحت السقف المستعار مباشرة (+2.38 م)"]], "asm": ["افتراض للعرض فقط"], "sr": S},
    }
