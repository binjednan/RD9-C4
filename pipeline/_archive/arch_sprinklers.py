# -*- coding: utf-8 -*-
"""Drop nipples that connect every sprinkler head to its branch pipe.

The sprinkler heads (P.ff sprk_pendent / sprk_upright / sprk_double) were drawn at their plan symbols with a small cylinder 26 cm below (pendent) or above (upright) the branch pipe and nothing
between them: they hung in the air (owner 2026-10-07).  Each head now has a 25 mm nipple (and, when the symbol is not exactly on the pipe line, an arm-over at pipe level): one tube element per head,
type 'sprk_drop', material of the pipe it taps.  Pipe level, plan distance and head level come from the model itself; nothing is invented for heads that already touch their pipe."""
import math, collections
from shapely.geometry import LineString, Point

DROP_DIA_CM = 2.5          # 25 mm drop (NFPA 13 branch line to sprinkler, 1")
SRC = ["MECH2 ص10–14 (FF-100..FF-105): رموز الرشاشات على خطوط الفروع", "وصلة النزول 25 مم افتراض — المخطط لا يرسم وصلات الرشاش"]


def _poly(g):
    from shapely.geometry import Polygon, box
    try:
        if g[0] == "p": return Polygon(g[1], [h for h in (g[4] if len(g) > 4 and g[4] else []) if len(h) >= 3]).buffer(0)
        if g[0] == "r": return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4]))
    except Exception:
        return None
    return None


def _head(e):
    g = e["g"]
    if g[0] in ("cyl", "sph"): return g[1], g[2], g[4], g[5]
    if g[0] == "b": return g[1], g[2], g[6], g[7]
    if g[0] == "r": return (g[1] + g[3]) / 2, (g[2] + g[4]) / 2, g[5], g[6]
    return None


def build(M):
    els = M["els"]
    pipes = collections.defaultdict(list)
    for e in els:
        if e["c"] == "P.ff" and e["t"] in ("pipe_ff", "pipe_ffc", "riser_spr") and e["g"][0] == "t" and "-X" not in e["id"][-6:]:
            pts = e["g"][1]
            for a, b in zip(pts[:-1], pts[1:]):
                if math.hypot(b[0] - a[0], b[1] - a[1]) < 1.0: continue
                pipes[e["l"]].append((LineString([(a[0], a[1]), (b[0], b[1])]), a[2], b[2], e["m"], (e.get("a") or {}).get("dia_mm", 25)))
    out = []; stats = collections.Counter()
    for e in els:
        if e["c"] != "P.ff" or not e["t"].startswith("sprk_") or "-X" in e["id"][-6:]: continue
        h = _head(e)
        if h is None: continue
        hx, hy, z0, z1 = h
        cand = pipes.get(e["l"], [])
        if not cand: stats["no_pipe"] += 1; continue
        P = Point(hx, hy)
        best = min(cand, key=lambda c: c[0].distance(P))
        d = best[0].distance(P)
        if d > 90:
            # no branch pipe in the model near this head (roof rooms): hang it from the suspended ceiling / slab soffit right above it
            top = None
            for c in els:
                if c["l"] == e["l"] and c["c"] in ("A.ceil", "S.slab") and c["g"][0] in ("p", "r"):
                    q = _poly(c["g"])
                    if q is not None and q.contains(P):
                        zc = c["g"][2] if c["g"][0] == "p" else c["g"][5]
                        if c["c"] == "A.ceil" and zc > z1 - 0.02 and (top is None or zc < top): top = zc
                        if c["c"] == "S.slab" and c["g"][2] > z1 and (top is None or c["g"][2] < top): top = c["g"][2]
            if top is not None and top - z1 <= 1.5 and e["t"] != "sprk_upright":
                out.append({"c": "P.ff", "l": e["l"], "g": ["t", [[round(hx, 1), round(hy, 1), round(z1, 3)], [round(hx, 1), round(hy, 1), round(top, 3)]], DROP_DIA_CM], "mark": "DROP", "t": "sprk_drop", "m": cand[0][3],
                            "a": {"head": e["id"], "dia_mm": 25, "kind": "وصلة رشاش إلى السقف", "length_m": round(top - z1, 2), "assumed": "لا أنبوب فرع قريب في النموذج؛ الرشاش معلّق بوصلة من السقف/البلاطة فوقه"}, "src": SRC})
                stats["to_ceiling"] += 1; continue
            if d > 350: stats["too_far"] += 1; continue        # falls through: long branch stub to the nearest pipe (assumed, flagged in the card)
            stats["stub"] += 1
        t = best[0].project(P); n = best[0].interpolate(t)
        L = best[0].length
        pz = best[1] + (best[2] - best[1]) * (t / L if L else 0)
        r = best[4] / 20.0 / 100.0                       # pipe radius in m
        below = z1 < pz
        end = z1 if below else z0
        gap = abs(pz - end) - r
        if gap < 0.03 and d < 3: stats["touching"] += 1; continue
        pts = []
        if d >= 3: pts.append([round(n.x, 1), round(n.y, 1), round(pz, 3)])
        pts.append([round(hx, 1), round(hy, 1), round(pz, 3)]); pts.append([round(hx, 1), round(hy, 1), round(end, 3)])
        el = {"c": "P.ff", "l": e["l"], "g": ["t", pts, DROP_DIA_CM], "mark": "DROP", "t": "sprk_drop", "m": best[3],
              "a": {"head": e["id"], "dia_mm": 25, "kind": "وصلة نزول الرشاش", "length_m": round(abs(pz - end) + d / 100.0, 2), "assumed": "وصلة 25 مم؛ الرشاش بلا وصلة في رسم المخطط"}, "src": SRC}
        if e.get("u"): el["u"] = e["u"]
        out.append(el); stats["pendent" if below else "upright"] += 1
        if d >= 3: stats["arm_over"] += 1
    print("sprinkler drops:", dict(stats))
    return out


def types():
    return {"sprk_drop": {"n": "وصلة نزول الرشاش 25 مم (Drop nipple)", "cf": "assumed",
                          "sp": [["القطر", "25 مم (1 بوصة)"], ["الوظيفة", "تربط رأس الرشاش بأنبوب الفرع فوقه (هابط) أو تحته (قائم)"], ["التفصيل", "ذراع أفقي بمنسوب الأنبوب عندما لا يقع رمز الرشاش على خط الأنبوب تمامًا"]],
                          "asm": ["المخطط يرسم رمز الرشاش فقط؛ الوصلة والقطر تقدير (NFPA 13: وصلة 1\" لرأس الرشاش)"], "sr": SRC}}
