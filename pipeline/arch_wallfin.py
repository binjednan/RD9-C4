# -*- coding: utf-8 -*-
"""Wall-finish layers (tile / glazed tile) on the wall faces INSIDE the wet rooms — owner 2026-10-07 «ابدأ التشطيبات» (item G of the architectural closure).

A500 gives every room kind a wall finish (kitchen W4 ceramic, bath / WC W6 ceramic, garbage room W9 glazed tile ...), and the model already carries those codes on the wall elements as a LIST OF
FACES («W6, W2» = tile on one face, paint on the other) — but the wall bodies were all drawn as plain block, so no tile was visible and a wall between a bath and a bedroom looked the same on both sides.

For every rectangular wall / column element (A.wall, S.wall, S.col) the four sides are walked in 10 cm steps; at every step the nearest finish cell of the level (A.floor with a room kind, <= 25 cm away)
says which room that side faces; when that room's A500 wall finish is a tile code the step belongs to a layer.  Consecutive steps merge into one thin plate (1.2 cm) from the floor up to the ceiling
of the room, clamped to the wall's own height (lintels keep their own range).  New category A.wfin («تشطيب الجدران»); the plates are rebuilt on every run (idempotent).

Height — read from A500 (owner 2026-10-08): the note under the schedule says «Finishing to be extended 10 cm above false ceiling level», so the plates run from the floor to the false ceiling
(2.40 m in the flats, FCL of A1401) + 10 cm = 2.50 m (clamped to the wall's own top).

Honest limits (all listed in the viewer's guesses list as G-WFIN):
  * A500 does not say whether the tile covers the whole room wall or only what is behind the fittings (its note «Ceramic tiles for a floor and wall required behind the kitchen cabinet»): the whole room wall is assumed.
  * which of the two faces of a wall carries which code is not stated either: the face is decided by the room it faces, not by the order of the codes.
  * lobbies (W7 / W13) are not layered here: the basement lobby is now a drawn room (A101, 540 x 380 cm) but its marble walls need the lift-door and corridor openings; the typical-floor lobbies carry no room label.
"""
import collections
from shapely.geometry import Polygon, box, Point
from shapely.strtree import STRtree
import finishes as FN

CATEGORY = ["A.wfin", "تشطيب الجدران (بلاط داخل الحمامات والمطابخ)"]
TILE_KINDS = {"kitchen", "bath", "wc", "garbage"}
CEIL_H = {"default": 2.40}      # false ceiling of the flats (FCL, A1401)
ABOVE_CEIL = 0.10               # m: A500 «Finishing to be extended 10 cm above false ceiling level»
THICK = 1.2            # cm
STEP = 10.0            # cm
REACH = 25.0           # cm: a side faces a cell when the cell is nearer than this
SRC = "A500 (جدول التشطيبات: W4/W6/W9 + ملاحظة «الإنهاء يمتد 10 سم فوق السقف المستعار») + حدود الغرف من المساقط A102–A105"
NOTE = ("طبقة بلاط على وجه الجدار داخل الغرفة الرطبة؛ الارتفاع = السقف المستعار 2.40 م + 10 سم بملاحظة A500 («Finishing to be extended 10 cm above false ceiling level») = 2.50 م؛ "
        "ولا يحدد A500 أي وجه من الجدار يحمل أي رمز (قُدّر الوجه من الغرفة التي يواجهها) ولا هل التكسية بكامل الجدار أم خلف الأدوات فقط — بانتظار تأكيدك")


def _poly(g):
    if g[0] == "p": return Polygon(g[1], g[4] if len(g) > 4 and g[4] else None).buffer(0)
    if g[0] == "r": return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4]))
    return None


def _pool(M, text):
    sp = M["sp"]
    if text not in sp: sp.append(text)
    return sp.index(text)


def register(M):
    """category in the architecture layer (right after the walls), once"""
    for L in M["layers"]:
        if L["id"] == "A" and not any(s[0] == CATEGORY[0] for s in L["subs"]):
            i = next((k for k, s in enumerate(L["subs"]) if s[0] == "A.wall"), len(L["subs"]) - 1)
            L["subs"].insert(i + 1, list(CATEGORY))


def build(M, els):
    """removes the old plates and returns the new ones (the caller appends them)"""
    els[:] = [e for e in els if e["c"] != "A.wfin"]
    register(M)
    LV = {l["id"]: l for l in M["levels"]}; si = _pool(M, SRC)
    cells = collections.defaultdict(list)                      # level -> [(polygon, kind, names, unit)]
    for e in els:
        if e["c"] != "A.floor": continue
        a = e.get("a") or {}; k = a.get("kind")
        if not k or (k not in FN.BY_KIND and k != "parking"): continue   # plates, strips, fills and unnamed cells face nobody
        p = _poly(e["g"])
        if p is not None and not p.is_empty: cells[e["l"]].append((p, k, a.get("room") or [], e.get("u")))
    trees = {l: STRtree([c[0] for c in cs]) for l, cs in cells.items() if cs}
    out = []; counter = collections.Counter(); n_by_level = collections.Counter()

    def face_of(lv, x, y):
        t = trees.get(lv)
        if t is None: return None
        P = Point(x, y); best = None
        for i in t.query(P.buffer(REACH)):
            d = cells[lv][i][0].distance(P)
            if d <= REACH and (best is None or d < best[0]): best = (d, i)
        if best is None: return None
        poly, kind, names, unit = cells[lv][best[1]]
        code = FN.BY_KIND.get(kind, (None, None, None))[1]
        return (code, kind, names, unit) if (kind in TILE_KINDS and code) else None

    for e in list(els):
        if e["c"] not in ("A.wall", "S.wall", "S.col") or e["g"][0] != "r": continue
        lv = e["l"]
        if lv not in cells: continue
        g = e["g"]; x0, x1 = sorted((g[1], g[3])); y0, y1 = sorted((g[2], g[4])); wz0, wz1 = g[5], g[6]
        ffl = LV[lv]["ffl"]; z0 = max(ffl + 0.012, wz0); z1 = min(ffl + CEIL_H["default"] + ABOVE_CEIL, wz1)
        if z1 - z0 < 0.05: continue
        # (axis, fixed coordinate of the face, outward sign, start, end)
        sides = [("x", y0, -1, x0, x1), ("x", y1, 1, x0, x1), ("y", x0, -1, y0, y1), ("y", x1, 1, y0, y1)]
        for axis, fixed, sg, a0, a1 in sides:
            if a1 - a0 < STEP * 0.8: continue
            n = max(1, int(round((a1 - a0) / STEP))); step = (a1 - a0) / n; run = None; runs = []
            for k in range(n):
                m = a0 + (k + 0.5) * step
                pt = (m, fixed + sg * 1.5) if axis == "x" else (fixed + sg * 1.5, m)
                f = face_of(lv, pt[0], pt[1])
                key = (f[0], f[1], tuple(f[2]), f[3]) if f else None
                if run and run[0] == key and abs(run[2] - (a0 + k * step)) < 1e-6: run[2] = a0 + (k + 1) * step
                else:
                    run = [key, a0 + k * step, a0 + (k + 1) * step]; runs.append(run)
            for key, s0, s1 in runs:
                if key is None or s1 - s0 < 8.0: continue
                code, kind, names, unit = key
                lo, hi = (fixed, fixed + sg * THICK) if sg > 0 else (fixed - THICK, fixed)
                rect = ["r", round(s0, 1), round(lo, 1), round(s1, 1), round(hi, 1), round(z0, 3), round(z1, 3)] if axis == "x" else \
                       ["r", round(lo, 1), round(s0, 1), round(hi, 1), round(s1, 1), round(z0, 3), round(z1, 3)]
                n_by_level[lv] += 1
                out.append({"id": f"A.wfin-{lv}-{n_by_level[lv]:04d}", "c": "A.wfin", "l": lv, "g": rect, "mark": code, "t": "wfin_" + code, "m": "fin_" + code,
                            "a": {"kind": kind, "fin": [code], "assumed_h": round(z1 - ffl, 2), "fin_guess": "wall"}, "u": unit, "s": [si]})
                counter[code] += 1
    return out, dict(counter)
