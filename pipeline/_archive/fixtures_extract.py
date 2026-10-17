# -*- coding: utf-8 -*-
"""Fixed fixtures of the flats, read from the approved plans (A103 first floor, A104 typical floor, A102 ground, A105 roof) -> data/fixtures.json

The plans draw the real fixed fixtures as CAD symbols on the layers `furrniture`, `A-FURNITURE` and `A-WET AREA`: WC, vanity counters with their basin, bath tubs, kitchen counters / cooker /
sink / washing machine, wardrobe hanger rails.  This script finds every symbol (stroke clustering), measures its footprint and its back wall and writes frame-based records; the 3D shape comes from the
approved details (A1200-A1205 bathrooms and kitchens, A1300-A1302 wardrobes) in pipeline/fixtures.py.

  wc        base (back-centre on the wall) + n (inward normal) + w x d     (symbol 70 x 68 incl. cistern; body 38 wide)
  vanity    base + n + w x d + basin centre offset                          (counter 150 x 50 / 100 x 50 ... as drawn)
  tub       centre + L x W + long axis + tap end                           (wet-area rectangle 70 x 180/190/200)
  kitchen   room polygon + front polylines (counter faces) + cooker / sink / washer / bar polygons + fridge anchor
  rail      wardrobe hanger rail (line) + hangers count                    (schedule size from A1300 by rail length)
usage: python3 pipeline/fixtures_extract.py   (needs the original plan PDFs through pipeline/lib.py, like furnish.py)"""
import os, sys, json, math, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from shapely.geometry import box, Polygon, LineString, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree

LAYERS = ("furrniture", "A-FURNITURE")
BUF = 1.4          # cm: strokes closer than this belong to one symbol (separates WC / basin / tub details; larger values merge neighbouring symbols through the wall lines)


def obb_axis(poly):
    """axis-aligned extent (the plans are orthogonal): (cx, cy, dx, dy)"""
    b = poly.bounds
    return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2, b[2] - b[0], b[3] - b[1]


def strokes(sh, layers=LAYERS, region=None):
    out = []
    for d in sh.D:
        if d.get("layer") not in layers: continue
        for pl in d["polys"]:
            pts = [sh.T(x, y) for (x, y) in pl]
            if len(pts) < 2: continue
            g = LineString(pts)
            if g.length < 0.05: continue
            if region is not None and not g.intersects(region): continue
            out.append({"g": g, "n": len(pts), "layer": d["layer"], "closed": bool(d.get("closed")) or (len(pts) > 2 and pts[0] == pts[-1]), "fill": d.get("fill") is not None})
    return out


def clusters(S, buf=BUF):
    U = unary_union([s["g"].buffer(buf) for s in S])
    comps = list(U.geoms) if U.geom_type == "MultiPolygon" else [U]
    tree = STRtree([s["g"] for s in S])
    out = []
    for c in comps:
        idx = [i for i in tree.query(c) if c.intersects(S[i]["g"])]
        out.append({"poly": c, "S": [S[i] for i in idx]})
    return out


def back_side(bounds, room, long_only=False):
    """which side of the item (x0,y0,x1,y1) touches the wall: returns the inward normal (towards the room centre) of the side nearest to the room boundary;
    long_only: counters / wardrobes stand with a LONG side on the wall"""
    x0, y0, x1, y1 = bounds
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    ring = room.exterior
    cand = {(0, 1): Point(cx, y0), (0, -1): Point(cx, y1), (1, 0): Point(x0, cy), (-1, 0): Point(x1, cy)}   # normal -> midpoint of the back side
    if long_only:
        keep = [(0, 1), (0, -1)] if (x1 - x0) >= (y1 - y0) else [(1, 0), (-1, 0)]
        cand = {k: v for k, v in cand.items() if k in keep}
    best = min(cand.items(), key=lambda kv: ring.distance(kv[1]))
    return best[0], round(ring.distance(best[1]), 1)


def room_of(fm, x, y):
    c = fm.comp_at(x, y)
    if c is None:
        for rad in (10, 25, 45):
            for k in range(8):
                a = k * math.pi / 4
                c = fm.comp_at(x + rad * math.cos(a), y + rad * math.sin(a))
                if c is not None: break
            if c is not None: break
    return (fm.comp_room.get(c) if c is not None else None), c


# ------------------------------------------------------------------------------------------------------------------------------ kitchens
def front_strip(line, room, depth=60.0):
    """counter body behind a front polyline: the single-sided buffer (mitred) on the side that is nearer to the room's walls"""
    best = None
    for sign in (1, -1):
        try:
            st = line.buffer(sign * depth, single_sided=True, join_style=2, cap_style=2, mitre_limit=5)
        except Exception:
            continue
        if st.is_empty: continue
        d = room.exterior.distance(st.centroid) if room is not None else 0
        # a strip lies on the wall side when a wall (outside the room polygon) is within a few cm of its far edge
        far = st.difference(line.buffer(depth - 6, join_style=2, cap_style=2)).buffer(0)
        dw = room.exterior.distance(far) if (room is not None and not far.is_empty) else 999
        if best is None or dw < best[0]: best = (dw, st)
    return best


def rect_candidates(S, depth_lo=57.0, depth_hi=63.0):
    """axis-aligned rectangles built from pairs of long 2-point strokes (the plans draw a sink / washer as four loose segments): returns (x0, y0, x1, y1) lists"""
    H, V = [], []
    for s in S:
        if s["n"] != 2: continue
        b = s["g"].bounds; w, h = b[2] - b[0], b[3] - b[1]
        if h < 0.4 and w >= 50: H.append((b[0], b[2], b[1]))
        elif w < 0.4 and h >= 50: V.append((b[1], b[3], b[0]))
    out = []
    for lst, flip in ((H, False), (V, True)):
        for i, (a0, a1, ya) in enumerate(lst):
            for (c0, c1, yc) in lst[i + 1:]:
                if abs(a0 - c0) < 1.5 and abs(a1 - c1) < 1.5 and depth_lo <= abs(yc - ya) <= depth_hi:
                    y0, y1 = min(ya, yc), max(ya, yc)
                    r = (y0, a0, y1, a1) if flip else (a0, y0, a1, y1)
                    if not any(max(abs(r[k] - q[k]) for k in range(4)) < 2.5 for q in out): out.append(r)
    return out


def kitchen_of(c, S_all, fm, room_poly_fn, label_pts):
    """items of one kitchen cluster: front polylines, cooker, sink, washer"""
    poly = c["poly"]
    cx, cy = poly.centroid.x, poly.centroid.y
    kind, comp = room_of(fm, cx, cy)
    S = c["S"]
    fronts, items = [], []
    for s in S:
        b = s["g"].bounds; w, h = b[2] - b[0], b[3] - b[1]
        if max(w, h) >= 100 and min(w, h) >= 40 and not s["closed"] and s["n"] >= 3:
            fronts.append([[round(x, 1), round(y, 1)] for x, y in s["g"].coords])
    # washer: the 41-point circle (about 54 cm) inside a 60 x 60 square
    for s in S:
        b = s["g"].bounds
        if s["n"] >= 40 and 50 <= (b[2] - b[0]) <= 60 and 50 <= (b[3] - b[1]) <= 60 and s["closed"]:
            mx, my = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
            if not any(it["k"] == "washer" and abs(it["c"][0] - mx) < 8 and abs(it["c"][1] - my) < 8 for it in items):
                items.append({"k": "washer", "c": [round(mx, 1), round(my, 1)], "ext": [60.0, 60.0]})
    # sink: 120 x 60 rectangle of loose segments (long side 105..140)
    for r in rect_candidates(S):
        L, W = max(r[2] - r[0], r[3] - r[1]), min(r[2] - r[0], r[3] - r[1])
        if 105 <= L <= 140:
            items.append({"k": "sink", "c": [round((r[0] + r[2]) / 2, 1), round((r[1] + r[3]) / 2, 1)], "ext": [round(r[2] - r[0], 1), round(r[3] - r[1], 1)]})
    # cooker: closed 5-point rectangle ~60 x 77 holding four 13-point burner circles
    burners = [((s["g"].bounds[0] + s["g"].bounds[2]) / 2, (s["g"].bounds[1] + s["g"].bounds[3]) / 2) for s in S
               if s["n"] in (13, 14) and 15 <= max(s["g"].bounds[2] - s["g"].bounds[0], s["g"].bounds[3] - s["g"].bounds[1]) <= 32]
    for s in S:
        b = s["g"].bounds; w, h = b[2] - b[0], b[3] - b[1]
        if s["n"] == 5 and 55 <= min(w, h) <= 68 and 68 <= max(w, h) <= 100:
            inside = [q for q in burners if b[0] <= q[0] <= b[2] and b[1] <= q[1] <= b[3]]
            if len(inside) >= 3 and not any(it["k"] == "cooker" and abs(it["c"][0] - (b[0] + b[2]) / 2) < 5 and abs(it["c"][1] - (b[1] + b[3]) / 2) < 5 for it in items):
                items.append({"k": "cooker", "c": [round((b[0] + b[2]) / 2, 1), round((b[1] + b[3]) / 2, 1)], "ext": [round(w, 1), round(h, 1)]})
    return {"c": [round(cx, 1), round(cy, 1)], "room": kind, "flat": None, "fronts": fronts, "items": items}

def _ring(pg):
    return [[round(x, 1), round(y, 1)] for x, y in list(pg.exterior.coords)[:-1]]


def _polys(g, min_area=40.0):
    return [q for q in (list(g.geoms) if hasattr(g, "geoms") else [g]) if (not q.is_empty) and q.geom_type == "Polygon" and q.area >= min_area]


def _rect_on(a, b, n, d0, d1):
    """rectangle between the front segment a-b offset by d0 and d1 along the unit normal n"""
    return Polygon([(a[0] + n[0] * d0, a[1] + n[1] * d0), (b[0] + n[0] * d0, b[1] + n[1] * d0), (b[0] + n[0] * d1, b[1] + n[1] * d1), (a[0] + n[0] * d1, a[1] + n[1] * d1)])


def kitchen_final(k, room, fm):
    """counter bodies behind the front polylines, wall-unit / splash bands, bars, appliance frames, fridge at a free run end.
    A front polyline segment is a WALL segment when a wall face lies 60 cm behind it (counter depth, A1204); otherwise it is a free-standing (bar) edge."""
    out = {"flat": k["flat"], "room": k["room"], "base": [], "bars": [], "wall": [], "splash": [], "items": [], "fronts": k["fronts"]}
    if room is None: return out
    ext = room.exterior
    for f in k["fronts"]:
        pts = [tuple(p) for p in f]
        segs = []          # (a, b, wall_normal or None)
        for a, b in zip(pts[:-1], pts[1:]):
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L < 20: continue
            u = ((b[0] - a[0]) / L, (b[1] - a[1]) / L); nl = (-u[1], u[0]); mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            wn = None
            for sg in (1, -1):
                q = Point(mid[0] + sg * nl[0] * 61.5, mid[1] + sg * nl[1] * 61.5)
                if ext.distance(q) <= 7.0 and wn is None: wn = (sg * nl[0], sg * nl[1])
            segs.append((a, b, wn, u, L))
        polys, wall_p, splash_p = [], [], []
        for i, (a, b, wn, u, L) in enumerate(segs):
            if wn is None: continue
            polys.append(_rect_on(a, b, wn, 0, 60)); wall_p.append(_rect_on(a, b, wn, 25, 60)); splash_p.append(_rect_on(a, b, wn, 58.4, 60))
            # inside corner: the next wall segment turns 90 degrees -> fill the corner square
            for (c0, c1, nb) in ((segs[i + 1] if i + 1 < len(segs) else None, "next", None),):
                pass
        for i in range(len(segs) - 1):
            a1, b1, n1, u1, L1 = segs[i]; a2, b2, n2, u2, L2 = segs[i + 1]
            if n1 is None or n2 is None: continue
            if abs(u1[0] * u2[0] + u1[1] * u2[1]) > 0.1: continue                         # not a right-angle corner
            P = b1
            far = (P[0] + n1[0] * 60 + n2[0] * 60, P[1] + n1[1] * 60 + n2[1] * 60)
            if ext.distance(Point(far)) > 9.0: continue
            sq = lambda d0, d1: Polygon([(P[0] + n1[0] * d0 + n2[0] * d0, P[1] + n1[1] * d0 + n2[1] * d0), (P[0] + n1[0] * d1 + n2[0] * d0, P[1] + n1[1] * d1 + n2[1] * d0),
                                          (P[0] + n1[0] * d1 + n2[0] * d1, P[1] + n1[1] * d1 + n2[1] * d1), (P[0] + n1[0] * d0 + n2[0] * d1, P[1] + n1[1] * d0 + n2[1] * d1)])
            polys.append(sq(0, 60)); wall_p.append(sq(0, 60).difference(sq(0, 25)))
        for q in polys: pass
        U = unary_union(polys) if polys else None
        if U is not None:
            for q in _polys(U.intersection(room)): out["base"].append(_ring(q))
        if wall_p:
            for q in _polys(unary_union(wall_p).intersection(room), 20): out["wall"].append(_ring(q))
        if splash_p:
            for q in _polys(unary_union(splash_p).intersection(room), 10): out["splash"].append(_ring(q))
        # free-standing run (bar): consecutive free segments forming a U
        free = [i for i, sg_ in enumerate(segs) if sg_[2] is None]
        if len(free) >= 3 and free[-1] - free[0] == len(free) - 1:
            fa = segs[free[0]]; fc = segs[free[-1]]
            if fa[3][0] * fc[3][0] + fa[3][1] * fc[3][1] < -0.9:
                xs = [fa[0][0], fa[1][0], fc[0][0], fc[1][0]]; ys = [fa[0][1], fa[1][1], fc[0][1], fc[1][1]]
                if abs(fa[3][0]) > 0.9:       # long faces along x
                    x0 = max(min(fa[0][0], fa[1][0]), min(fc[0][0], fc[1][0])); x1 = min(max(fa[0][0], fa[1][0]), max(fc[0][0], fc[1][0]))
                    out["bars"].append(_ring(box(x0, min(ys), x1, max(ys))))
                else:
                    y0 = max(min(fa[0][1], fa[1][1]), min(fc[0][1], fc[1][1])); y1 = min(max(fa[0][1], fa[1][1]), max(fc[0][1], fc[1][1]))
                    out["bars"].append(_ring(box(min(xs), y0, max(xs), y1)))
        # fridge at a free end of the polyline whose next wall is 70..135 cm away
        for idx, (end, nxt) in ((0, (pts[0], pts[1])), (1, (pts[-1], pts[-2]))):
            seg = segs[0] if idx == 0 else segs[-1]
            if seg[2] is None: continue
            u = (end[0] - nxt[0], end[1] - nxt[1]); L = math.hypot(*u)
            if L < 1: continue
            u = (u[0] / L, u[1] / L)
            ray = LineString([end, (end[0] + u[0] * 220, end[1] + u[1] * 220)])
            inter = ray.intersection(ext)
            if inter.is_empty: continue
            cand = [inter] if inter.geom_type == "Point" else [q for q in getattr(inter, "geoms", []) if q.geom_type == "Point"]
            g = min((ray.project(q) for q in cand), default=None)
            if g is None or not (70 <= g <= 135): continue
            wn = seg[2]
            cx = end[0] + u[0] * min(g / 2, 50) + wn[0] * 20; cy = end[1] + u[1] * min(g / 2, 50) + wn[1] * 20
            out["items"].append({"k": "fridge", "c": [round(cx, 1), round(cy, 1)], "n": [round(-wn[0], 3), round(-wn[1], 3)], "w": 90.0, "d": 80.0})
    for it in k["items"]:
        cx, cy = it["c"]; ex, ey = it["ext"]
        bb = (cx - ex / 2, cy - ey / 2, cx + ex / 2, cy + ey / 2)
        nrm, gap = back_side(bb, room)
        out["items"].append({"k": it["k"], "c": it["c"], "ext": it["ext"], "n": nrm, "gap": gap})
    return out


def extract_plan(key, pn, hv):
    import assemble_arch as AA
    import furnish as FU
    fm = AA.fmap(pn, hv); sh = fm.sh
    S = strokes(sh)
    C = clusters(S)
    wet = [s for d in sh.D if "WET AREA" in (d.get("layer") or "") for s in [d]]
    res = {"wc": [], "vanity": [], "tub": [], "kitchen": [], "rail": [], "other": []}
    room_polys = {}

    def rpoly(comp):
        if comp not in room_polys: room_polys[comp] = FU.room_poly(fm, comp)
        return room_polys[comp]

    def flat_of(x, y):
        f = fm.flat_at(x, y)
        return f[0] if f else None

    # ---- wet-area rectangles: tubs 70 x (170..210)
    tubs = {}
    for d in sh.D:
        if "WET AREA" not in (d.get("layer") or ""): continue
        for pl in d["polys"]:
            pts = [sh.T(x, y) for (x, y) in pl]
            if len(pts) != 5: continue
            xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
            w, h = max(xs) - min(xs), max(ys) - min(ys)
            L, W = max(w, h), min(w, h)
            if 68 <= W <= 76 and 165 <= L <= 215:
                tubs[(round((min(xs) + max(xs)) / 2), round((min(ys) + max(ys)) / 2))] = (min(xs), min(ys), max(xs), max(ys))
    detail_blocks = []     # tub tap / drain blocks (55 x 26 symbol) -> tap end
    for c in C:
        cx, cy, dx, dy = obb_axis(c["poly"]); n = len(c["S"])
        L, W = max(dx, dy), min(dx, dy)
        if n >= 150 and 50 <= L <= 62 and 20 <= W <= 32: detail_blocks.append((cx, cy))
    for (tx, ty), (x0, y0, x1, y1) in sorted(tubs.items()):
        kind, comp = room_of(fm, tx, ty)
        along_x = (x1 - x0) >= (y1 - y0)
        L = (x1 - x0) if along_x else (y1 - y0); W = (y1 - y0) if along_x else (x1 - x0)
        tap = None
        near = [b for b in detail_blocks if x0 - 5 <= b[0] <= x1 + 5 and y0 - 5 <= b[1] <= y1 + 5]
        if near:
            b = near[0]; tap = (1 if (b[0] > tx) else -1) if along_x else (1 if (b[1] > ty) else -1)
        poly = rpoly(comp) if comp is not None else None
        nrm = None
        if poly is not None and not poly.is_empty and poly.geom_type == "Polygon":
            nrm, dist = back_side((x0, y0, x1, y1), poly)
        res["tub"].append({"c": [round(tx, 1), round(ty, 1)], "L": round(L, 1), "W": round(W, 1), "ax": "x" if along_x else "y", "tap": tap, "n": nrm, "room": kind, "flat": flat_of(tx, ty)})

    # ---- clusters: WC, vanity, others
    for c in C:
        cx, cy, dx, dy = obb_axis(c["poly"]); n = len(c["S"])
        L, W = max(dx, dy), min(dx, dy)
        if 50 <= L <= 62 and 20 <= W <= 32 and n >= 150: continue          # tub tap block
        kind, comp = room_of(fm, cx, cy)
        poly = rpoly(comp) if comp is not None else None
        if poly is None or poly.is_empty or poly.geom_type != "Polygon": poly = None
        if n >= 150 and 60 <= L <= 80 and 55 <= W <= 80:                      # WC
            nrm, dist = back_side(c["poly"].bounds, poly) if poly is not None else (None, None)
            res["wc"].append({"c": [round(cx, 1), round(cy, 1)], "ext": [round(dx, 1), round(dy, 1)], "n": nrm, "wall_gap": dist, "room": kind, "flat": flat_of(cx, cy)})
        elif 9 <= n <= 25 and 95 <= L <= 225 and 44 <= W <= 58:              # vanity counter with basin
            nrm, dist = back_side(c["poly"].bounds, poly, long_only=True) if poly is not None else (None, None)
            basin = None
            for s in c["S"]:
                b = s["g"].bounds
                dd = sorted((b[2] - b[0], b[3] - b[1]))
                if 30 <= dd[0] <= 44 and 36 <= dd[1] <= 56 and s["n"] >= 30:
                    basin = [round((b[0] + b[2]) / 2, 1), round((b[1] + b[3]) / 2, 1), round(b[2] - b[0], 1), round(b[3] - b[1], 1)]; break
            res["vanity"].append({"c": [round(cx, 1), round(cy, 1)], "ext": [round(dx, 1), round(dy, 1)], "n": nrm, "wall_gap": dist, "basin": basin, "room": kind, "flat": flat_of(cx, cy), "recs": n})
        elif L >= 25 and n >= 3:
            on = back_side(c["poly"].bounds, poly, long_only=(L / max(W, 1) > 1.8))[0] if poly is not None else None
            res["other"].append({"c": [round(cx, 1), round(cy, 1)], "ext": [round(dx, 1), round(dy, 1)], "n_rec": n, "room": kind, "flat": flat_of(cx, cy), "n": on})

    # ---- kitchens: the big clusters (counters + appliances) of a kitchen / open-plan living room
    for c in C:
        cx, cy, dx, dy = obb_axis(c["poly"]); n = len(c["S"])
        if n >= 100 and max(dx, dy) >= 200:
            k = kitchen_of(c, S, fm, rpoly, None)
            if k["room"] and k["room"].get("kind") in ("kitchen", "living") and k["items"]:
                comp_room = rpoly(room_of(fm, cx, cy)[1])
                k["room"] = k["room"].get("kind"); k["flat"] = flat_of(cx, cy)
                res["kitchen"].append(kitchen_final(k, comp_room if comp_room.geom_type == "Polygon" else None, fm))
    # ---- closed bar polygons (60 x 180 breakfast bar with a chamfered end) belong to the kitchen of the same flat
    for st_ in S:
        if st_["n"] == 6:
            b = st_["g"].bounds; w, h = b[2] - b[0], b[3] - b[1]
            if 55 <= min(w, h) <= 66 and 170 <= max(w, h) <= 190:
                f_ = flat_of((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
                for k in res["kitchen"]:
                    if k["flat"] == f_ and f_ is not None: k["bars"].append([[round(x, 1), round(y, 1)] for x, y in list(st_["g"].coords)])
    # ---- wardrobe hanger rails: single long thin line (170..225) with hanger strokes (49 x 26) alongside
    rails = []
    for c in C:
        cx, cy, dx, dy = obb_axis(c["poly"]); n = len(c["S"])
        if n == 1 and max(dx, dy) >= 100 and min(dx, dy) <= 6:
            rails.append({"c": [round(cx, 1), round(cy, 1)], "len": round(max(dx, dy), 1), "ax": "x" if dx >= dy else "y"})
    hangers = [c for c in C if 40 <= max(obb_axis(c["poly"])[2:]) <= 55 and 7 <= min(obb_axis(c["poly"])[2:]) <= 30 and len(c["S"]) <= 2]
    for r in rails:
        h = [c for c in hangers if abs(c["poly"].centroid.x - r["c"][0]) <= r["len"] / 2 + 8 and abs(c["poly"].centroid.y - r["c"][1]) <= 40]
        r["hangers"] = len(h)
        if h:
            if r["ax"] == "x": r["side"] = (0, 1) if sum(c["poly"].centroid.y for c in h) / len(h) > r["c"][1] else (0, -1)
            else: r["side"] = (1, 0) if sum(c["poly"].centroid.x for c in h) / len(h) > r["c"][0] else (-1, 0)
        else: r["side"] = None
        kind, comp = room_of(fm, r["c"][0], r["c"][1])
        r["room"] = kind; r["flat"] = flat_of(r["c"][0], r["c"][1])
        res["rail"].append(r)
    return res, fm



WR_SIZES = {220: 60, 200: 50, 190: 55, 180: 60, 170: 60, 120: 50, 110: 50}      # A1300 schedule: length -> depth (cm)


def snap_wr(length):
    sz = min(WR_SIZES, key=lambda k: abs(k - (length - 2.5)))
    return sz, WR_SIZES[sz]


def finalize(res, fm):
    """compact fixtures.json record set for one plan"""
    def nrm(n): return [n[0], n[1]] if n else None
    out = {"wc": [], "vanity": [], "tub": [], "kitchen": res["kitchen"], "wardrobe": [], "basin": []}
    def rk(it):
        r = it.get("room"); return r.get("kind") if isinstance(r, dict) else r
    for w in res["wc"]:
        n = w["n"]
        if not n: continue
        dn = w["ext"][1] if n[0] == 0 else w["ext"][0]
        out["wc"].append({"f": w["flat"], "r": rk(w), "b": [round(w["c"][0] - n[0] * dn / 2, 1), round(w["c"][1] - n[1] * dn / 2, 1)], "n": nrm(n), "w": round(w["ext"][0] if n[0] == 0 else w["ext"][1], 1), "d": round(dn, 1)})
    for v in res["vanity"]:
        n = v["n"]
        if not n: continue
        dn = v["ext"][1] if n[0] == 0 else v["ext"][0]; wt = v["ext"][0] if n[0] == 0 else v["ext"][1]
        base = [round(v["c"][0] - n[0] * dn / 2, 1), round(v["c"][1] - n[1] * dn / 2, 1)]
        t = (n[1], -n[0])
        if not v["basin"]:
            # no basin symbol: a plain 120 x 50 cabinet-like outline in a bedroom / dress room = wardrobe WR6 (A1300), not a vanity
            if rk(v) in ("master_bed", "bedroom", "dress") and 105 <= wt <= 130:
                sz, dp = snap_wr(wt)
                out["wardrobe"].append({"f": v["flat"], "r": rk(v), "b": base, "n": nrm(n), "w": sz, "d": dp, "src": "outline"})
            continue
        offs = [round((v["basin"][0] - v["c"][0]) * t[0] + (v["basin"][1] - v["c"][1]) * t[1], 1)]
        out["vanity"].append({"f": v["flat"], "r": rk(v), "b": base, "n": nrm(n), "w": round(wt, 1), "d": round(dn, 1), "basins": offs})
    for t_ in res["tub"]:
        out["tub"].append({"f": t_["flat"], "r": rk(t_), "c": t_["c"], "L": t_["L"], "W": t_["W"], "ax": t_["ax"], "tap": t_["tap"]})
    for r in res["rail"]:
        if r["len"] < 100 or r.get("side") is None: continue
        sz, dp = snap_wr(r["len"])
        side = r["side"]                       # rail -> hangers (into the wardrobe body); the rail line is the FRONT edge of the wardrobe (the wardrobes stand back to back between two rooms)
        n = (-side[0], -side[1])
        out["wardrobe"].append({"f": r["flat"], "r": rk(r), "b": [round(r["c"][0] + side[0] * dp, 1), round(r["c"][1] + side[1] * dp, 1)], "n": nrm(n), "w": sz, "d": dp, "src": "rail"})
    for o in res["other"]:
        # 50 x 55 oval basin symbol (17 strokes) in a toilet: wall basin
        if 15 <= o["n_rec"] <= 20 and 44 <= o["ext"][0] <= 58 and 44 <= o["ext"][1] <= 58 and rk(o) in ("wc", "bath") and o.get("n"):
            n = o["n"]; dn = o["ext"][1] if n[0] == 0 else o["ext"][0]
            out["basin"].append({"f": o["flat"], "r": rk(o), "b": [round(o["c"][0] - n[0] * dn / 2, 1), round(o["c"][1] - n[1] * dn / 2, 1)], "n": nrm(n), "w": round(o["ext"][0] if n[0] == 0 else o["ext"][1], 1), "d": round(dn, 1)})
        # 110 x 50 wardrobe outline without hanger symbols (WR7) in a bedroom
        elif 5 <= o["n_rec"] <= 12 and rk(o) in ("master_bed", "bedroom", "dress") and o.get("n") and 45 <= min(o["ext"]) <= 53 and 105 <= max(o["ext"]) <= 130:
            n = o["n"]; dn = o["ext"][1] if n[0] == 0 else o["ext"][0]; wt = o["ext"][0] if n[0] == 0 else o["ext"][1]
            sz, dp = snap_wr(wt)
            out["wardrobe"].append({"f": o["flat"], "r": rk(o), "b": [round(o["c"][0] - n[0] * dn / 2, 1), round(o["c"][1] - n[1] * dn / 2, 1)], "n": nrm(n), "w": sz, "d": dp, "src": "outline"})
    return out


if __name__ == "__main__":
    out, raw = {}, {}
    for key, pn, hv in (("typ", 7, 4), ("1", 6, 3), ("G", 5, None), ("R", 8, None)):
        r, fm = extract_plan(key, pn, hv)
        raw[key] = r
        out[key] = finalize(r, fm)
        print(key, {k: len(v) for k, v in out[key].items()})
    json.dump(out, open(os.path.join(HERE, "data", "fixtures.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    dbg = os.environ.get("FIXTURES_RAW")
    if dbg: json.dump(raw, open(dbg, "w", encoding="utf-8"), ensure_ascii=False, default=str)
