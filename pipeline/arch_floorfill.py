# -*- coding: utf-8 -*-
"""Floors closed to the walls and to the structure (owner 2026-10-07: "some floors are not connected to the walls and a gap forms between them").

The finish cells (A.floor, one rectangle per cell of the A500 finish grid) were modelled as 12 mm plates at F.F.L. with two kinds of hole around them:

  1. plan gaps    : strips 4-10 cm wide between a finish cell and the wall / door threshold / window sill next to it (the cells stop at the drawn room outline and the wall
                    blocks are drawn on a slightly different line), so the structure showed through;
  2. vertical gap : the plate floated 10 cm (levels 1-5), 20 cm (basement) or 45 cm (ground floor) above the structural slab, with nothing in between.

Both are closed here (stateless: runs on every post_model run, ids end -Xnnnn like every extras element):

  * every thin uncovered strip (< 25 cm wide) that touches a finish cell AND a wall / door / window / column is filled with the same finish as the neighbour it shares the longest
    edge with (strips outside the facade or next to no finish are left alone);
  * under each group of finish cells a solid 'floor_buildup' block rises from the top of whatever carries it (structural slab, raft, the ground-floor fill or the roof build-up)
    to the underside of the finish, so the plates sit on a body and walls / doors / stairs stand on a closed floor.

Nothing here is read from a drawing: the strips and the block heights come from the model's own geometry; the composition of the layer (screed / sand / blinding) is not given in the
documents, so the card says so."""
import math, collections
from shapely.geometry import Polygon, box, Point
from shapely.affinity import rotate as _rot
from shapely.ops import unary_union
from shapely.strtree import STRtree

SRC = ["A500: جدول التشطيبات (خلايا الأرضيات) وA102/A103: مخططات الأدوار — حدود الخلايا والجدران من النموذج نفسه", "المستندات لا تحدد مكوّنات طبقة التسوية؛ الارتفاع = الفرق بين منسوب البلاطة الإنشائية وأسفل التشطيب"]
MAT = {"floor_buildup": {"name": "طبقة التسوية تحت التشطيب (مونة / تسوية — تقديرية)", "color": "#c9c6bc", "rough": 0.95, "code": "A500/STR"}}
THIN_CM = 25.0                  # strips narrower than this are closed
MAX_STRIP_M2 = 3.0
SOLID_CATS = ("A.wall", "S.wall", "S.col", "A.door", "A.win", "A.glass", "A.clad", "S.stair")
FINISH_PREFIX = "floor_F"


def _foot(e):
    g = e["g"]; k = g[0]
    try:
        if k == "p":
            if len(g[1]) < 3: return None
            holes = [h for h in (g[4] if len(g) > 4 and g[4] else []) if len(h) >= 3]
            p = Polygon(g[1], holes)
            if not p.is_valid: p = p.buffer(0)
            return p, g[2], g[3]
        if k == "r":
            return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4])), g[5], g[6]
        if k == "b":
            p = box(g[1] - g[3] / 2, g[2] - g[4] / 2, g[1] + g[3] / 2, g[2] + g[4] / 2)
            return _rot(p, g[5], origin=(g[1], g[2])), g[6], g[7]
        if k == "cyl":
            return Point(g[1], g[2]).buffer(g[3], 8), g[4], g[5]
    except Exception:
        return None
    return None


def _parts(geom):
    return list(geom.geoms) if hasattr(geom, "geoms") else [geom]


def _ring(c):
    return [[round(x, 1), round(y, 1)] for x, y in list(c.coords)[:-1]]


def _pgeom(poly, z0, z1):
    holes = [_ring(h) for h in poly.interiors if Polygon(h).area > 100]
    return ["p", _ring(poly.exterior), round(z0, 3), round(z1, 3), holes or None]


def build(M):
    els = M["els"]; stats = collections.Counter(); out = []
    levels = [l["id"] for l in M["levels"]]
    for lv in levels:
        cells = []; supports = []; solids = []
        for e in els:
            if e["l"] != lv: continue
            c = e["c"]
            if c == "A.floor":
                f = _foot(e)
                if not f: continue
                if e["t"].startswith(FINISH_PREFIX): cells.append((e, f[0], f[1], f[2]))
                else: supports.append((f[0], f[2]))                       # ground-floor fill / roof build-up carry the finish like a slab does
            elif c in ("S.slab", "S.raft"):
                f = _foot(e)
                if f: supports.append((f[0], f[2]))
            if c in SOLID_CATS:
                f = _foot(e)
                if f: solids.append(f[0])
        if not cells: continue
        cell_polys = [c[1] for c in cells]; tree = STRtree(cell_polys)
        floors = unary_union(cell_polys)
        solid_u = unary_union(solids) if solids else Polygon()
        sup_polys = [s[0] for s in supports]
        reach = unary_union(sup_polys) if sup_polys else floors
        # ---- 1. thin strips between a finish cell and the structure next to it
        gap = reach.difference(floors.buffer(0.2)).difference(solid_u.buffer(0.2)) if not solid_u.is_empty else reach.difference(floors.buffer(0.2))
        strips = []
        for g in _parts(gap):
            if g.is_empty or g.geom_type != "Polygon" or g.area < 4 or g.area > MAX_STRIP_M2 * 1e4: continue
            if not g.buffer(-THIN_CM / 2).is_empty: stats["wide_left"] += 1; continue
            touch = [i for i in tree.query(g.buffer(1.5)) if cell_polys[i].distance(g) < 1.0]
            if not touch or solid_u.is_empty or solid_u.distance(g) > 1.0: stats["no_neighbour"] += 1; continue
            best = max(touch, key=lambda i: g.buffer(1.5).intersection(cell_polys[i]).area)
            strips.append((g, cells[best]))
        for g, (ce, cp, z0, z1) in strips:
            a = dict(ce.get("a") or {}); a["room"] = []; a["kind"] = "شريط تكميلي بين التشطيب والجدار"
            a["assumed"] = "فراغ بعرض %d سم بين خلية التشطيب والجدار/العتبة في النموذج؛ أُكمل بنفس تشطيب الخلية المجاورة (مثل عتبة الباب)" % round(2 * g.buffer(-0.01).area / max(g.length, 1))
            for part in _parts(g):
                if part.is_empty or part.geom_type != "Polygon": continue
                el = {"c": "A.floor", "l": lv, "g": _pgeom(part, z0, z1), "mark": "FLOOR-STRIP", "t": ce["t"], "m": ce["m"], "a": a, "src": SRC}
                if ce.get("u"): el["u"] = ce["u"]
                out.append(el); stats["strip_" + lv] += 1
        # ---- 2. solid body under the finish: from what carries it up to the underside of the plates
        groups = collections.defaultdict(list)
        for ce, cp, z0, z1 in cells:
            cen = cp.representative_point(); base = None
            for sp, top in supports:
                if top <= z0 + 0.001 and sp.contains(cen) and (base is None or top > base): base = top
            if base is None or z0 - base < 0.02: continue
            groups[(round(base, 3), round(z0, 3))].append(cp)
        for (base, z0), polys in sorted(groups.items()):
            polys = polys + [g for g, (ce, cp, zz0, zz1) in strips if abs(round(zz0, 3) - z0) < 0.002]
            body = unary_union(polys).buffer(0.4).buffer(-0.4).simplify(0.6, preserve_topology=True)
            for part in _parts(body):
                if part.is_empty or part.geom_type != "Polygon" or part.area < 400: continue
                out.append({"c": "A.floor", "l": lv, "g": _pgeom(part, base, z0), "mark": "FLOOR-BUILDUP", "t": "floor_buildup", "m": "floor_buildup",
                            "a": {"kind": "طبقة تسوية تحت التشطيب", "thick_cm": round((z0 - base) * 100), "area_m2": round(part.area / 1e4, 1),
                                  "assumed": "المستندات لا تحدد مكوّنات الطبقة بين البلاطة الإنشائية والتشطيب؛ جسم صلب يملأ الفراغ حتى أسفل التشطيب"}, "src": SRC})
                stats["body_" + lv] += 1
    print("floor strips / bodies:", dict(stats))
    return {"els": out, "mats": MAT}


def types():
    return {"floor_buildup": {"n": "طبقة التسوية تحت تشطيب الأرضية (Floor build-up)", "cf": "assumed",
                              "sp": [["الارتفاع", "من سطح البلاطة الإنشائية (أو اللبشة / التسوية / طبقة السطح) حتى أسفل التشطيب: 10 سم في الأدوار 1–5، 20 سم في القبو، 45 سم في الأرضي"],
                                     ["الغاية", "تغلق الفراغ تحت لوحة التشطيب فتقوم الجدران والأبواب والتشطيب على جسم متصل"]],
                              "asm": ["مكوّنات الطبقة (مونة / رمل / خرسانة نظافة / عزل) غير محددة في المستندات؛ الجسم يُعرض بمادة واحدة"], "sr": SRC}}
