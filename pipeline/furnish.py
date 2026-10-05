# -*- coding: utf-8 -*-
"""Presentation furniture layout (stage) for the flats of the typical floor (A104) and the first floor (A103) -> data/furniture.json

NOT from the documents: the architectural plans draw only fixed fixtures (kitchen counters, sanitary ware, lifts), no loose furniture.  The layout below is a rule-based
staging so that an isolated flat does not look empty: beds, bedside tables, wardrobes, sofa group, TV unit, dining set, washing machine.  Everything is tagged `stage:furniture`
(hidden with one switch) and every dimension / position is an assumption.

Rules (all in cm, plan coordinates of the model):
 * the room polygon comes from the FloorMap grid (pipeline/floormap.py); it is shrunk by 6 cm; door zones (door width + 20 x 110) are keep-out areas;
 * bed: headboard against the wall that is farthest from the doors (glazed walls are penalised), >= 55 cm free on one long side and >= 70 cm at the foot;
 * wardrobe: against the longest free wall of a bedroom larger than 12 m2; dress rooms get a wardrobe band along their longest free wall;
 * living: sofa on the longest door-free wall, coffee table 90 cm in front of it, TV unit on the opposite wall, dining table + 6 chairs in the largest free area if the room is > 24 m2;
 * laundry: washing machine on a free wall.
usage: python3 pipeline/furnish.py   (needs the original A103/A104 PDFs through pipeline/lib.py)"""
import os, sys, json, math, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
from shapely.geometry import box, Polygon, Point, LineString, MultiLineString
from shapely.ops import unary_union
from shapely import affinity

# ----------------------------------------------------------------------------------------------------------- item library (local frame: x along the wall, y from the wall into the room)
def _p(ox, oy, w, d, z0, z1, m): return [ox, oy, w, d, z0, z1, m]
def bed(w=180, L=200):
    return dict(name="سرير", w=w, d=L + 8, parts=[_p(0, 3, w + 10, 6, 0.10, 1.05, "furn_wood"), _p(0, 4 + L / 2, w, L, 0.10, 0.30, "furn_wood"), _p(0, 4 + L / 2 + 2, w - 6, L - 8, 0.30, 0.52, "furn_white"),
                                                  _p(-w / 4, 28, 55, 36, 0.52, 0.63, "furn_white"), _p(w / 4, 28, 55, 36, 0.52, 0.63, "furn_white"), _p(0, 4 + L * 0.62, w - 4, L * 0.7, 0.52, 0.575, "furn_fabric_gray")])
def nightstand(): return dict(name="طاولة جانبية", w=45, d=40, parts=[_p(0, 20, 45, 40, 0.0, 0.50, "furn_wood")])
def wardrobe(W=180, dep=60): return dict(name="دولاب", w=W, d=dep, parts=[_p(0, dep / 2, W, dep, 0.0, 2.30, "furn_wood_light")] + [_p(-W / 2 + (k + 0.5) * W / max(1, round(W / 60)), dep + 0.5, W / max(1, round(W / 60)) - 1.2, 1.0, 0.1, 2.2, "furn_wood") for k in range(max(1, round(W / 60)))])
def sofa(W=230, dep=95):
    return dict(name="كنبة", w=W, d=dep, parts=[_p(0, dep / 2 + 5, W, dep - 10, 0.0, 0.42, "furn_fabric_gray"), _p(0, 11, W, 22, 0.42, 0.90, "furn_fabric_gray"), _p(-W / 2 + 10, dep / 2 + 5, 20, dep - 10, 0.42, 0.62, "furn_fabric_gray"), _p(W / 2 - 10, dep / 2 + 5, 20, dep - 10, 0.42, 0.62, "furn_fabric_gray"),
                                                _p(-W / 4, dep / 2 + 8, W / 2 - 24, dep - 34, 0.42, 0.50, "furn_fabric_beige"), _p(W / 4, dep / 2 + 8, W / 2 - 24, dep - 34, 0.42, 0.50, "furn_fabric_beige")])
def coffee_table(): return dict(name="طاولة قهوة", w=110, d=60, parts=[_p(0, 30, 110, 60, 0.36, 0.40, "furn_wood")] + [_p(sx * 48, 30 + sy * 25, 5, 5, 0.0, 0.36, "furn_dark") for sx in (-1, 1) for sy in (-1, 1)])
def tv_unit(): return dict(name="وحدة تلفاز", w=190, d=42, parts=[_p(0, 21, 190, 42, 0.0, 0.45, "furn_wood_dark"), _p(0, 8, 125, 4, 0.62, 1.22, "furn_dark")])
def dining(W=190, D=95):
    parts = [_p(0, 0, W, D, 0.72, 0.76, "furn_wood")] + [_p(sx * (W / 2 - 6), sy * (D / 2 - 6), 6, 6, 0.0, 0.72, "furn_dark") for sx in (-1, 1) for sy in (-1, 1)]
    for k in range(3):
        for sy in (-1, 1):
            cx = -W / 3 + k * W / 3; cy = sy * (D / 2 + 22)
            parts += [_p(cx, cy, 44, 44, 0.42, 0.46, "furn_fabric_beige"), _p(cx, cy + sy * 20, 44, 4, 0.46, 0.92, "furn_fabric_beige")]
    return dict(name="طاولة طعام مع 6 كراسٍ", w=W + 10, d=D + 100, parts=parts, free=True)
def washer(): return dict(name="غسالة", w=60, d=60, parts=[_p(0, 30, 60, 60, 0.0, 0.85, "furn_white"), _p(0, 60.5, 36, 1, 0.30, 0.66, "furn_dark")])

# ----------------------------------------------------------------------------------------------------------- geometry helpers
def room_poly(fm, comp):
    rects = fm.g2.rects(fm.g2.lab == comp)
    return unary_union([box(*r) for r in rects]).buffer(0.1).buffer(-0.1)

def door_zones(fm):
    zs = []
    for d in fm.r["doors"]:
        w = float(d["w"]); cx, cy = float(d["cx"]), float(d["cy"])
        zs.append(box(cx - w / 2 - 10, cy - 105, cx + w / 2 + 10, cy + 105) if d["o"] == "h" else box(cx - 105, cy - w / 2 - 10, cx + 105, cy + w / 2 + 10))
    return unary_union(zs) if zs else Polygon()

def glazed_lines(fm):
    segs = []
    for s in fm.sh.segments(("A-GALZ", "A-WINDOW")):
        if math.hypot(s[2] - s[0], s[3] - s[1]) > 5: segs.append(LineString([(s[0], s[1]), (s[2], s[3])]))
    return unary_union(segs) if segs else LineString()

def item_poly(item, base, t, n, ox=0.0):
    """footprint polygon of an item whose back-centre is `base` on the wall, wall direction t, inward normal n"""
    w, d = item["w"], item["d"]
    cx = base[0] + t[0] * ox + n[0] * d / 2; cy = base[1] + t[1] * ox + n[1] * d / 2
    ang = math.degrees(math.atan2(t[1], t[0]))
    return affinity.rotate(box(cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2), ang, origin=(cx, cy)), ang

def wall_edges(poly):
    """axis-aligned edges of the room exterior with their inward normal"""
    ring = list(poly.exterior.coords)
    ccw = Polygon(ring).exterior.is_ccw
    out = []
    for a, b in zip(ring[:-1], ring[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 40: continue
        t = ((b[0] - a[0]) / L, (b[1] - a[1]) / L)
        n = (-t[1], t[0]) if ccw else (t[1], -t[0])
        out.append((a, b, L, t, n))
    return out

class Room:
    def __init__(self, poly, doors, glazed):
        self.poly = poly; self.free = poly.buffer(-6); self.doors = doors; self.glazed = glazed; self.placed = []
    def ok(self, fp, clear=0.0, need_free=True):
        if need_free and not self.free.contains(fp): return False
        if fp.intersects(self.doors): return False
        for q in self.placed:
            if fp.buffer(clear).intersects(q): return False
        return True
    def wall_score(self, a, b, t, n, L):
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        g = self.glazed.buffer(12).intersection(LineString([a, b])).length / max(L, 1)
        d = self.doors.distance(Point(mid)) if not self.doors.is_empty else 300
        return d - 250 * g

    def place_on_wall(self, item, prefer="far", edge_filter=None, clear=0.0, side_strip=None, foot_strip=0, step=10, center_bonus=30):
        best = None
        for a, b, L, t, n in wall_edges(self.poly):
            if L < item["w"] + 6: continue
            base_score = self.wall_score(a, b, t, n, L)
            if prefer == "short": base_score = -base_score
            n_steps = int((L - item["w"] - 12) // step)
            for k in range(n_steps + 1):
                off = 6 + item["w"] / 2 + k * step
                base = (a[0] + t[0] * off + n[0] * 7.0, a[1] + t[1] * off + n[1] * 7.0)
                fp, ang = item_poly(item, base, t, n)
                if not self.ok(fp, clear): continue
                if foot_strip:
                    foot = item_poly(dict(w=item["w"], d=foot_strip), (base[0] + n[0] * item["d"], base[1] + n[1] * item["d"]), t, n)[0]
                    if not self.free.contains(foot): continue
                if side_strip:
                    ok_side = False
                    for sg in (-1, 1):
                        sb = (base[0] + t[0] * sg * (item["w"] / 2 + side_strip / 2), base[1] + t[1] * sg * (item["w"] / 2 + side_strip / 2))
                        st = item_poly(dict(w=side_strip, d=item["d"]), sb, t, n)[0]
                        if self.free.contains(st) and not st.intersects(self.doors): ok_side = True
                    if not ok_side: continue
                c = (L / 2 - (off)); sc = base_score + center_bonus * (1 - abs(c) / (L / 2))
                if edge_filter and not edge_filter(a, b, t, n, L): continue
                if best is None or sc > best[0]: best = (sc, base, t, n, ang, fp)
        return best
    def commit(self, item, best, flat_tag):
        sc, base, t, n, ang, fp = best
        self.placed.append(fp)
        cx = base[0] + n[0] * item["d"] / 2; cy = base[1] + n[1] * item["d"] / 2
        return dict(name=item["name"], base=[round(base[0], 1), round(base[1], 1)], t=[round(t[0], 4), round(t[1], 4)], n=[round(n[0], 4), round(n[1], 4)], ang=round(ang, 2), parts=item["parts"], w=item["w"], d=item["d"])

def place_free(room, item, around=None, step=30):
    """item with a free-standing footprint (w x d, centred) rotated 0 / 90; returns the best position or None"""
    best = None
    minx, miny, maxx, maxy = room.free.bounds
    for rot in (0, 90):
        w, d = (item["w"], item["d"]) if rot == 0 else (item["d"], item["w"])
        x = minx + w / 2
        while x <= maxx - w / 2:
            y = miny + d / 2
            while y <= maxy - d / 2:
                fp = box(x - w / 2, y - d / 2, x + w / 2, y + d / 2)
                if room.free.contains(fp) and not fp.intersects(room.doors) and all(not fp.buffer(30).intersects(q) for q in room.placed):
                    sc = -fp.centroid.distance(around) if around is not None else -fp.centroid.distance(room.poly.centroid)
                    if around is not None: sc = fp.centroid.distance(around)
                    if best is None or sc > best[0]: best = (sc, x, y, rot, fp)
                y += step
            x += step
    return best

def furnish_room(kind, names, area, poly, doors, glazed, unit_has_dress=False):
    R = Room(poly, doors, glazed); out = []
    def put(item, **kw):
        b = R.place_on_wall(item, **kw)
        if b: out.append(R.commit(item, b, kind)); return b
    if kind in ("master_bed", "bedroom"):
        w = 200 if kind == "master_bed" else (180 if area >= 13 else 160)
        b = put(bed(w), prefer="far", side_strip=55, foot_strip=70, clear=0)
        if b:
            sc, base, t, n, ang, fp = b
            for sg in (-1, 1):
                ns = nightstand(); bp = (base[0] + t[0] * sg * (w / 2 + 28), base[1] + t[1] * sg * (w / 2 + 28))
                fp2, _ = item_poly(ns, bp, t, n)
                if R.free.contains(fp2) and not fp2.intersects(R.doors) and not any(fp2.intersects(q) for q in R.placed):
                    R.placed.append(fp2); out.append(dict(name=ns["name"], base=[round(bp[0], 1), round(bp[1], 1)], t=[round(t[0], 4), round(t[1], 4)], n=[round(n[0], 4), round(n[1], 4)], ang=round(ang, 2), parts=ns["parts"], w=ns["w"], d=ns["d"]))
        if area >= 12 and not (kind == "master_bed" and unit_has_dress):
            for W in (210, 180, 150, 120):
                if put(wardrobe(W), prefer="far", clear=35): break
    elif kind == "dress":
        put(wardrobe(min(240, 40 * int((max(wall_edges(poly), key=lambda e: e[2])[2] - 20) // 40) or 120), 55), prefer="far")
    elif kind == "living":
        b = put(sofa(230, 95), prefer="far", clear=0, center_bonus=10)
        if b:
            sc, base, t, n, ang, fp = b
            ct = coffee_table(); bp = (base[0] + n[0] * (95 + 55), base[1] + n[1] * (95 + 55))
            fp2, _ = item_poly(ct, bp, t, n)
            if R.free.contains(fp2) and not fp2.intersects(R.doors) and not any(fp2.intersects(q) for q in R.placed):
                R.placed.append(fp2); out.append(dict(name=ct["name"], base=[round(bp[0], 1), round(bp[1], 1)], t=[round(t[0], 4), round(t[1], 4)], n=[round(n[0], 4), round(n[1], 4)], ang=round(ang, 2), parts=ct["parts"], w=ct["w"], d=ct["d"]))
            tv = tv_unit()
            # TV unit: the wall edge facing the sofa (inward normal opposite to the sofa's)
            opp = lambda a_, b_, t_, n_, L_: (n_[0] * n[0] + n_[1] * n[1]) < -0.9 and abs(sum((p - q) * nn for p, q, nn in zip(a_, base, n))) > 220
            put(tv, prefer="far", edge_filter=opp, clear=0)
        if area >= 24:
            dn = dining(); around = Point(base[0], base[1]) if b else None
            f = place_free(R, dn, around=around)
            if f:
                sc, x, y, rot, fp = f; R.placed.append(fp)
                out.append(dict(name=dn["name"], free=True, c=[round(x, 1), round(y, 1)], ang=rot, parts=dn["parts"], w=dn["w"], d=dn["d"]))
    elif kind == "laundry":
        put(washer(), prefer="far")
    return out


def without_kitchen(fm, poly):
    """open-plan living + kitchen: remove the kitchen fittings (hull of the fixed-furniture lines around the KITCHEN / WASH labels) from the room before furnishing the living part"""
    from shapely.geometry import MultiPoint
    labs = [(w["X"], w["Y"]) for w in fm.sh.words(layer="A-TEXT-DETAIL") if w["s"] in ("KITCHEN", "WASH") and poly.buffer(5).contains(Point(w["X"], w["Y"]))]
    if not labs: return poly
    pts = []
    for d in fm.sh.D:
        ly = d["layer"] or ""
        if not ly.endswith(("furrniture", "A-FURNITURE")): continue
        for pl in d["polys"]:
            for (x, y) in pl:
                X, Y = fm.sh.T(x, y)
                if any(math.hypot(X - lx, Y - ly_) < 320 for lx, ly_ in labs) and poly.buffer(3).contains(Point(X, Y)): pts.append((X, Y))
    if len(pts) < 6: return poly
    hull = MultiPoint(pts).convex_hull.buffer(55)
    rest = poly.difference(hull)
    if rest.is_empty: return None
    if rest.geom_type == "MultiPolygon": rest = max(rest.geoms, key=lambda g: g.area)
    return rest if rest.area > 6e4 else None

def main():
    import assemble_arch as AA
    res = {}
    for key, (pn, hv) in (("typ", (7, 4)), ("1", (6, 3))):
        fm = AA.fmap(pn, hv); dz = door_zones(fm); gl = glazed_lines(fm)
        floor = {}
        for no, fl in sorted(fm.flats.items()):
            rooms = [fm.comp_room[c] for c in fl["comps"]]
            has_dress = any(r["kind"] == "dress" for r in rooms)
            items = []
            for rm in rooms:
                if rm["kind"] not in ("master_bed", "bedroom", "dress", "living", "laundry"): continue
                poly = room_poly(fm, rm["comp"])
                if poly.is_empty or poly.geom_type != "Polygon": continue
                if rm["kind"] == "living" and ("KITCHEN" in rm["names"] or "WASH" in rm["names"]):
                    poly = without_kitchen(fm, poly)
                    if poly is None: continue
                for it in furnish_room(rm["kind"], rm["names"], float(rm["area_m2"]), poly, dz, gl, has_dress):
                    it["room"] = rm["kind"]; items.append(it)
            floor[str(no)] = items
            print(key, "flat", no, len(items), "items:", dict(collections.Counter(i["name"] for i in items)))
        res[key] = floor
    json.dump(res, open(os.path.join(HERE, "data", "furniture.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__": main()
