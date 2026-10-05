# -*- coding: utf-8 -*-
"""Support analysis shared by the audit (pipeline/audit_support.py) and post_model.py.

For every MEP / electrical element it answers "what carries it?":
  * ceiling zone (top above FFL + 2.2 m):  a false ceiling / soffit just above (<= 30 cm)   -> carried
                                         a soffit further up (<= 3.5 m)                  -> carried by a rod / hanger of that length   (a.rod / a.hang, cm)
  * floor zone   (bottom within 6 cm of FFL): a floor / slab / site surface below                  -> carried
                                         pipes on an open roof / floor within 90 cm              -> carried by stands                (a.stand, cm)
  * wall zone    (in between, or wall-mounted device): a wall / column / parapet / cabinet touching (<= 15 cm) -> carried
Anything left is reported as "float".  Nothing is moved here: the result is only classification + the length of the missing support."""
import math, collections, json, os
from shapely.geometry import Polygon, Point, box
from shapely.strtree import STRtree
HERE = os.path.dirname(os.path.abspath(__file__))
def poly_of(g):
    if g[0] == "p":
        try: return Polygon(g[1], g[4] if len(g) > 4 and g[4] else None).buffer(0)
        except Exception: return None
    if g[0] == "r": return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4]))
    if g[0] == "b":
        hw, hd = g[3] / 2, g[4] / 2; a = math.radians(g[5]); c, s = abs(math.cos(a)), abs(math.sin(a)); ex, ey = hw * c + hd * s, hw * s + hd * c
        return box(g[1] - ex, g[2] - ey, g[1] + ex, g[2] + ey)
    if g[0] == "cyl": return Point(g[1], g[2]).buffer(g[3])
    return None
def zr(g):
    k = g[0]
    if k == "r": return g[5], g[6]
    if k == "b": return g[6], g[7]
    if k == "cyl": return g[4], g[5]
    if k == "p": return g[2], g[3]
    if k in ("t", "d", "rs"):
        zs = [p[2] for p in g[1] if len(p) > 2]; return (min(zs), max(zs)) if zs else (None, None)
class Idx:
    def __init__(self): self.polys = []; self.meta = []
    def add(self, p, z0, z1, ei, cat):
        if p is not None and not p.is_empty: self.polys.append(p); self.meta.append((z0, z1, ei, cat))
    def build(self): self.t = STRtree(self.polys) if self.polys else None
    def hits(self, geom, tol=0.0):
        if self.t is None: return []
        g = geom.buffer(tol) if tol else geom
        return [self.meta[i] + (self.polys[i],) for i in self.t.query(g) if self.polys[i].intersects(g)]
WALL_MOUNT_DEFAULT = {"thermostat"}
class Support:
    def __init__(self, els, levels, wall_types=()):
        self.els = els; self.LV = {l["id"]: l for l in levels}; self.wall_types = set(wall_types) | WALL_MOUNT_DEFAULT
        self.H = Idx(); self.V = Idx(); self.B = Idx(); self.P = Idx()
        for i, e in enumerate(els):
            c, g = e["c"], e["g"]; z0, z1 = zr(g)
            if z0 is None: continue
            if c in ("A.floor", "A.site", "S.raft", "S.stair"): self.H.add(poly_of(g), z1, z1, i, "floor")
            elif c == "S.slab": self.H.add(poly_of(g), z1, z1, i, "floor"); self.H.add(poly_of(g), z0, z0, i, "ceil")
            elif c == "A.ceil": self.H.add(poly_of(g), z0, z0, i, "ceil")
            elif c == "S.ramp" and g[0] == "rs":
                pts = g[1]; hw = g[2] / 2
                for a, b in zip(pts[:-1], pts[1:]):
                    dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1; nx, ny = -dy / L * hw, dx / L * hw
                    q = Polygon([(a[0] + nx, a[1] + ny), (b[0] + nx, b[1] + ny), (b[0] - nx, b[1] - ny), (a[0] - nx, a[1] - ny)])
                    self.H.add(q, min(a[2], b[2]), max(a[2], b[2]), i, "floor")
            if c in ("A.wall", "S.wall", "S.col", "A.rail", "A.fix", "A.clad", "S.beam"): self.V.add(poly_of(g), z0, z1, i, c)
            if c in ("M.equip", "P.heater", "E.panel", "E.gen", "M.fan", "A.fix"): self.B.add(poly_of(g), z0, z1, i, c)
            if c in ("M.pipe", "M.duct", "P.cold", "P.hot", "P.drain", "P.ff") and g[0] in ("t", "d"):
                for a, b in zip(g[1][:-1], g[1][1:]):
                    from shapely.geometry import LineString
                    self.P.add(LineString([(a[0], a[1]), (b[0], b[1])]).buffer(5), min(a[2], b[2]), max(a[2], b[2]), i, c)
        for ix in (self.H, self.V, self.B, self.P): ix.build()
    def zone(self, e):
        z0, z1 = zr(e["g"]); ffl = self.LV[e["l"]]["ffl"]
        if e.get("t") in self.wall_types: return "wall"
        if z0 - ffl < 0.06: return "floor"
        if z1 > ffl + 2.2: return "ceil"
        return "wall"
    def soffit_gap(self, shp, z, maxgap=3.5, tol=3):
        """smallest distance (m) from z up to a ceiling surface covering shp, or None"""
        best = None
        for h in self.H.hits(shp, tol):
            if h[3] == "ceil" and z - 0.03 <= h[0] <= z + maxgap:
                d = max(0.0, h[0] - z); best = d if best is None or d < best else best
        return best
    def floor_gap(self, shp, z, maxgap=0.9, tol=3):
        best = None
        for h in self.H.hits(shp, tol):
            if h[3] == "floor" and z - maxgap <= h[1] <= z + 0.04:
                d = max(0.0, z - h[1]); best = d if best is None or d < best else best
        return best
    def analyse(self, i):
        """-> dict(kind, ...) kind in ok | rod | hang | stand | float | skip"""
        e = self.els[i]; g = e["g"]; z0, z1 = zr(g)
        if z0 is None: return {"kind": "skip"}
        if g[0] in ("t", "d"):
            gaps = []; fl = []; walls = 0
            for p in g[1]:
                P = Point(p[0], p[1])
                s = self.soffit_gap(P, p[2]); f = self.floor_gap(P, p[2] - 0.0, 3.0)
                if s is not None: gaps.append(s)
                if f is not None: fl.append(f)
                if [h for h in self.V.hits(P, 25) if h[0] - 0.1 <= p[2] <= h[1] + 0.1]: walls += 1
            n = len(g[1])
            if gaps and len(gaps) >= 0.5 * n:
                gaps.sort(); med = gaps[len(gaps) // 2]
                return {"kind": "ok" if med <= 0.30 else "hang", "gap_cm": round(med * 100)}
            if fl and len(fl) >= 0.5 * n:
                fl.sort(); return {"kind": "stand", "gap_cm": round(fl[len(fl) // 2] * 100)}
            if walls >= 0.5 * n: return {"kind": "ok"}
            return {"kind": "float"}
        pl = poly_of(g)
        if pl is None: return {"kind": "skip"}
        zone = self.zone(e)
        if zone == "ceil":
            s0 = self.soffit_gap(pl, z1, 3.5, 6)
            if s0 is not None and s0 <= 0.30: return {"kind": "ok", "gap_cm": round(s0 * 100)}
            for h in self.B.hits(pl, 8):
                if h[2] != i and h[0] - 0.1 <= z1 and h[1] >= z0 - 0.1: return {"kind": "ok"}
            for h in self.P.hits(pl, 40):                                  # pendent heads / drops hang off a pipe or duct just above
                if h[2] != i and z1 - 0.05 <= h[1] <= z1 + 0.75: return {"kind": "ok"}
            if s0 is not None: return {"kind": "rod", "gap_cm": round(s0 * 100)}
            return {"kind": "float"}
        if zone == "floor":
            f = self.floor_gap(pl, z0, 0.08, 6)
            return {"kind": "ok"} if f is not None else {"kind": "float"}
        mid = (z0 + z1) / 2
        tops = []
        for h in self.V.hits(pl, 15):
            if h[0] - 0.1 <= mid <= h[1] + 0.1: return {"kind": "ok"}
            if h[1] < z0 + 0.02 and z0 - h[1] <= 1.2: tops.append(h[1])      # the host wall is lower than the device: it hovers above the wall top
        if tops: return {"kind": "lower", "wall_top": max(tops)}
        for h in self.B.hits(pl, 15):
            if h[2] != i and h[0] - 0.2 <= z1 and h[1] >= z0 - 0.2: return {"kind": "ok"}
        if self.floor_gap(pl, z0, 0.08, 6) is not None: return {"kind": "ok"}
        return {"kind": "float"}
