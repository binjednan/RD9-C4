# -*- coding: utf-8 -*-
"""Risers inferred from the plans (owner 2026-10-08: «أكمل استعمال جميع المخططات لتكون البيئة مناسبة للاختبار»).

Every plan sheet draws the pipes of ITS level only, and a riser is drawn on each level as the place where the horizontal pipes stop (or as a small ring).  The extraction therefore left every floor's
network as an island: the vertical pipe that joins them was never made.  What the plans DO document is the position: on every level the pipes of one medium end at the same plan point.  This module finds
those points and adds the vertical pipe between the levels — nothing else:

  evidence   ends (and ring symbols) of one medium, same plan point (<= RADIUS), on at least MIN_LEVELS levels in a row, one of them a non-typical level (basement / ground / roof — a rise that is
             repeated on the five typical floors alone is a fixture branch, not a riser), and the largest pipe at that point is a main (>= MIN_DIA mm of the medium)
  result     one tube per pair of consecutive levels (like the fire-fighting risers of mep_bg.py), diameter = the largest pipe that ends there, ids -Vnnnn (V = vertical; -L is taken by the landscape elements), grade 'vdd' (position derived from the
             alignment, size read from the pipes, elevation from the pipes' own ends), flagged on the card: «صاعد مستنتج من محاذاة نهايات المواسير على الطوابق»

Ids end with -Vnnnn so post_model.py drops and rebuilds them on every run (idempotent).  Runs after the clash pass (risers cross slabs on purpose) and before connectors.py."""
import os, re, sys, math, collections
from shapely.geometry import Polygon, Point, box
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ID_RE = re.compile(r"-V\d{4}$")
FOOT_TOL = 15.0                     # cm  a riser that PASSES a level (no pipe end there) must stand inside that level's built footprint (walls, columns, floors, slabs) or touch it: a stack 25 cm outside the wall, in open air, is not a stack
RADIUS = 25.0                       # cm  plan distance within which ends of one medium count as the same point (the plans of different levels are registered to a few centimetres, rings are drawn off-centre)
SRC_TEXT = "صاعد مستنتج من محاذاة نهايات المواسير على الطوابق (نفس النقطة في المسقط على ثلاثة طوابق متتالية على الأقل بينها طابق غير نمطي؛ pipeline/risers.py) — الرسم يبيّن الموضع ولا يرسم الصاعد نفسه"

# medium -> (category, element types, material, minimum main diameter in mm, name)
MEDIA = [
    ("chws", "M.pipe", ("pipe_chws",), "m_chws", 32, "صاعد مياه مبردة — تغذية"),
    ("chwr", "M.pipe", ("pipe_chwr",), "m_chwr", 32, "صاعد مياه مبردة — رجوع"),
    ("cold", "P.cold", ("pipe_cold",), "p_cold", 32, "صاعد مياه باردة"),
    ("hot", "P.hot", ("pipe_hot",), "p_hot", 32, "صاعد مياه ساخنة"),
    ("soil", "P.drain", ("pipe_soil",), "p_soil", 75, "قائم صرف (Soil stack)"),
    ("waste", "P.drain", ("pipe_waste",), "p_waste", 75, "قائم صرف (Waste stack)"),
]
TYPICAL = {"2", "3", "4", "5"}


def _geom(e):
    g = e["g"]
    try:
        if g[0] == "p": return Polygon(g[1]).buffer(0)
        if g[0] == "r": return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4]))
        if g[0] == "b":
            cx, cy, w, d, rot = g[1:6]; th = math.radians(rot); c, s_ = math.cos(th), math.sin(th)
            return Polygon([(cx + px * c - py * s_, cy + px * s_ + py * c) for px, py in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))])
        if g[0] == "cyl": return Point(g[1], g[2]).buffer(g[3])
    except Exception: return None
    return None


def footprints(M):
    """level -> shapely geometry of what is BUILT at that level (floor finishes, walls, columns, stairs, and the slab of every floor above the ground: the ground slab is the whole plot)"""
    out = {}
    for lv in [l["id"] for l in M["levels"]]:
        parts = []
        for e in M["els"]:
            if e["l"] != lv: continue
            if e["c"] in ("A.floor", "S.col", "S.wall", "A.wall", "S.stair") or (e["c"] == "S.slab" and lv not in ("B", "G")):
                pg = _geom(e)
                if pg is not None and not pg.is_empty: parts.append(pg)
        out[lv] = unary_union(parts) if parts else None
    return out


def _dia_mm(e):
    a = e.get("a") or {}
    return a.get("dia_mm") or round(e["g"][2] * 10) if e["g"][0] == "t" else 0


def build(M, verbose=False):
    els = M["els"]
    els[:] = [e for e in els if not ID_RE.search(e["id"])]
    sp = M["sp"]
    if SRC_TEXT not in sp: sp.append(SRC_TEXT)
    sidx = sp.index(SRC_TEXT)
    lv = {l["id"]: l for l in M["levels"]}; order = [l["id"] for l in M["levels"]]
    new = []; counter = collections.Counter(); skipped = []
    foot = footprints(M)
    for key, cat, types, mat, min_dia, name in MEDIA:
        if mat not in M["mats"]: mat = next((e["m"] for e in els if e["c"] == cat and e.get("t") in types), mat)
        ends = []                                     # (x, y, z, level, dia_mm, element id)
        for e in els:
            if e["c"] != cat or e.get("t") not in types or e["g"][0] != "t" or (e.get("a") or {}).get("connector"): continue
            pts = e["g"][1]; d = _dia_mm(e)
            closed = len(pts) >= 4 and math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1]) < 2 and max(abs(p[0] - pts[0][0]) for p in pts) < 60
            if closed:                                # a ring: the riser symbol itself
                cx = sum(p[0] for p in pts[:-1]) / (len(pts) - 1); cy = sum(p[1] for p in pts[:-1]) / (len(pts) - 1)
                ends.append((cx, cy, pts[0][2], e["l"], d, e["id"]))
            else:
                for p in (pts[0], pts[-1]): ends.append((p[0], p[1], p[2], e["l"], d, e["id"]))
        clusters = []
        for en in ends:
            for c in clusters:
                if math.hypot(c["x"] - en[0], c["y"] - en[1]) <= RADIUS: c["m"].append(en); c["x"] = sum(m[0] for m in c["m"]) / len(c["m"]); c["y"] = sum(m[1] for m in c["m"]) / len(c["m"]); break
            else: clusters.append({"x": en[0], "y": en[1], "m": [en]})
        for c in clusters:
            lvls = sorted({m[3] for m in c["m"]}, key=lambda l: order.index(l))
            if len(lvls) < 3: continue
            idx = [order.index(l) for l in lvls]
            if any(b - a > 2 for a, b in zip(idx, idx[1:])): continue             # no gap of more than one level (a riser may pass a level where nothing branches off)
            if not (set(lvls) - TYPICAL - {"1"}): continue                       # needs a basement / ground / roof end
            dia = max(m[4] for m in c["m"])
            if dia < min_dia: continue
            # one point per level: the mean elevation of that level's ends
            z = {l: sum(m[2] for m in c["m"] if m[3] == l) / sum(1 for m in c["m"] if m[3] == l) for l in lvls}
            for a, b in zip(lvls, lvls[1:]):
                ia, ib = order.index(a), order.index(b)
                out = [(l, round(foot[l].distance(Point(c["x"], c["y"])))) for l in order[ia + 1:ib] if foot.get(l) is not None and foot[l].distance(Point(c["x"], c["y"])) > FOOT_TOL]
                if out:                                                               # the stack would cross a level in open air: not built, listed for the owner
                    skipped.append({"medium": key, "x": round(c["x"]), "y": round(c["y"]), "from": a, "to": b, "open_at": out}); counter[("skipped", cat, a, b)] += 1; continue      # the id number of the skipped segment stays reserved
                counter[(cat, b)] += 1
                e = {"id": f"{cat}-{b}-V{sum(counter.values()):04d}", "c": cat, "l": b, "g": ["t", [[round(c["x"], 1), round(c["y"], 1), round(z[a], 3)], [round(c["x"], 1), round(c["y"], 1), round(z[b], 3)]], round(dia / 10 * 1.1, 1)],
                     "mark": f"RISER-{key.upper()}-{int(round(c['x']))}/{int(round(c['y']))}", "t": types[0], "m": mat,
                     "a": {"riser": True, "dia_mm": dia, "length_m": round(abs(z[b] - z[a]), 2), "kind": name, "levels": f"{a} → {b}", "evidence": f"{len(c['m'])} نهاية على {len(lvls)} طوابق عند النقطة نفسها",
                           "assumed": "القطر = أكبر ماسورة تنتهي هنا؛ المنسوب من نهايات المواسير نفسها"}, "s": [sidx]}
                new.append(e)
            if verbose: print(f"  riser {key:5s} ({round(c['x'])},{round(c['y'])}) dia {dia} levels {lvls} ends {len(c['m'])}")
    els.extend(new)
    M.setdefault("meta", {})["risers_skipped"] = skipped
    if verbose: print("risers:", len(new), "skipped (cross a level in open air):", len(skipped), [(k["medium"], k["x"], k["y"], k["open_at"]) for k in skipped])
    return len(new)


if __name__ == "__main__":
    import json
    SRC = os.path.join(os.path.dirname(HERE), "src", "model.json")
    M = json.load(open(SRC, encoding="utf-8"))
    build(M, verbose=True)
