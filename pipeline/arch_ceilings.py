# -*- coding: utf-8 -*-
"""False ceilings rebuilt from the approved reflected-ceiling plans.

Approved levels (FCL = finished ceiling level above the room's finished floor), read from the drawings on 2026-10-05:
  A1401 (ARCH2 p29) typical / first / roof plans : apartment rooms +2.40 FCL; corridor and lift lobby +2.35 / +2.50 (A1601: lowered 45-60 cm border, raised central tray)
  A1401 ground floor plan                         : entrance +3.40 / +3.55, retail +3.50, colonnade soffit slab +3.75, service rooms (pump, command, garbage, gas, wc) +2.80
  A1600 (ARCH2 p34)                               : ground-floor entrance +3.40 / +3.55, basement lobby +2.35 / +2.50
  C1 = 12 mm gypsum board, emulsion paint, suspended system "as per drawing level"
The earlier model used one assumed height (2.70) and the ground-floor sheet "could not be read"; the audit (pipeline/audit_arch.py) also found 15 m2 plates inside both stair wells on every floor,
dozens of wall-thickness slivers and 'inferred soffit' strips floating in the open colonnade.

rebuild(): removes every A.ceil, regenerates one plate per floor polygon (unioned per room) at its approved FCL, cuts the openings of the slab above (stairs, lifts, shafts),
adds corridor / lobby trays, and moves the ceiling-mounted devices (lights, detectors, diffusers, pendent sprinklers) with the ceiling.  Idempotent: the shift already applied
to a device is stored in a['ceil_dz'].
"""
import collections
from shapely.geometry import Polygon, box, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree

H_FLAT = 2.40
TRAY = (2.35, 2.50)
BORDER = 45.0                      # cm: lowered border of a corridor / lobby tray
H_SERVICE = 2.80
H_RETAIL = 3.50
H_LOBBY_G = (3.40, 3.55)
OLD_H = 2.70                       # the height every earlier pass used for the devices
WET = ("bath", "wc", "laundry", "store")
NO_CEIL_ROOMS = ("HV", "TRA", "GEN", "LV ROOM")
SERVICE_ROOMS = ("PUMP", "TANK", "COMMAND", "GARBAGE", "GAS", "TELEPHONE", "WC")
ORDER = ["B", "G", "1", "2", "3", "4", "5", "R", "T"]
DEV_CATS = {"E.light", "E.emerg", "E.fa"}
DEV_TYPES = {"diff_supply", "diff_return", "sprk_pendent", "grille_return", "grille_supply"}
PENDANTS = {"e_L12", "e_L13"}          # hook + rose + bulb hang from the plate: their top follows the plate, they are not lowered by the full 0.30 m
SRC = ["ARCH2 ص29 (A1401 المساقط المعكوسة للأسقف)", "ARCH2 ص35 (A1601 سقف الممر وردهة المصاعد)", "ARCH2 ص34 (A1600 ردهة الأرضي)"]


def _poly(g):
    if g[0] == "p":
        holes = [h for h in (g[4] if len(g) > 4 and g[4] else []) if len(h) >= 3]
        try:
            p = Polygon(g[1], holes)
            return p if p.is_valid else p.buffer(0)
        except Exception:
            return None
    if g[0] == "r":
        return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4]))
    return None


def _floor_z(g):
    return g[2] if g[0] == "p" else g[5]


def _ring(poly):
    return [[round(x, 1), round(y, 1)] for x, y in list(poly.exterior.coords)[:-1]]


def _prism(poly, z0, z1):
    g = ["p", _ring(poly), round(z0, 3), round(z1, 3)]
    holes = [[[round(x, 1), round(y, 1)] for x, y in list(h.coords)[:-1]] for h in poly.interiors]
    if holes: g.append(holes)
    return g


def _pieces(geom, min_area=3000, min_width=14):
    out = []
    for q in (list(geom.geoms) if hasattr(geom, "geoms") else [geom]):
        if q.is_empty or q.geom_type != "Polygon" or q.area < min_area: continue
        b = q.bounds
        if min(b[2] - b[0], b[3] - b[1]) < min_width: continue
        out.append(q)
    return out


def height_class(level, a, fin):
    """-> (height or (border, centre) tuple or None, class key)"""
    rooms = " ".join(a.get("room") or []).upper()
    kind = a.get("kind")
    if level == "G":
        if kind == "floor_fill": return H_RETAIL, "retail"
        if any(k in rooms for k in NO_CEIL_ROOMS): return None, "none"
        if any(k in rooms for k in SERVICE_ROOMS) or kind in ("pump", "cmd", "garbage", "wc", "elec"): return H_SERVICE, "service"
        if "F16" in fin: return H_LOBBY_G, "lobby"
        return H_RETAIL, "retail"
    if level == "B": return None, "none"
    if level in ("1", "2", "3", "4", "5") and "F16" in fin and not rooms.strip(): return TRAY, "corridor"
    if "DN" in rooms: return None, "none"                                 # stair landing at roof level
    return H_FLAT, "flat"


def rebuild(M, els, LV):
    """replace every A.ceil; return stats"""
    els[:] = [e for e in els if e["c"] != "A.ceil"]
    slabs = {e["l"]: e for e in els if e["c"] == "S.slab" and e["g"][0] == "p"}
    parts = collections.defaultdict(list)
    for e in els:
        if e["c"] == "S.slab" and e["g"][0] in ("p", "r"):
            q = _poly(e["g"])
            if q is not None and not q.is_empty: parts[e["l"]].append(q)
    slab_union = {lv: unary_union(v) for lv, v in parts.items()}
    elec = [box(2635, 240, 3185, 1185)]
    new = []; stats = collections.Counter(); ceil_of = collections.defaultdict(list)       # level -> [(polygon, H)]
    counter = collections.Counter()
    for lv in ORDER:
        if lv in ("B", "T"): continue
        k = ORDER.index(lv); nxt = ORDER[k + 1] if k + 1 < len(ORDER) else None
        holes = []
        if nxt in slabs:
            holes = [Polygon(h) for h in (slabs[nxt]["g"][4] if len(slabs[nxt]["g"]) > 4 and slabs[nxt]["g"][4] else []) if len(h) >= 3]
        above = slab_union.get(nxt)                            # the slab above (a plate only makes sense under it)
        cut_parts = holes + (elec if lv == "G" else [])
        cut = unary_union(cut_parts) if cut_parts else None
        groups = collections.defaultdict(list)             # (class, H, fin) -> polygons
        for e in els:
            if e["l"] != lv or e["c"] != "A.floor": continue
            a = e.get("a") or {}
            if a.get("kind") in ("roof_buildup",): continue
            p = _poly(e["g"])
            if p is None or p.is_empty: continue
            fin = a.get("fin") or []
            H, cls = height_class(lv, a, fin)
            if H is None: continue
            wet = a.get("kind") in WET
            groups[(cls, H, "C3" if wet else "C1", round(_floor_z(e["g"]), 2))].append((p, a))
        for (cls, H, cfin, fz), items in groups.items():
            U = unary_union([p.buffer(0.5) for p, _ in items])
            if cut is not None: U = U.difference(cut)
            rooms = sorted({r for _, a in items for r in (a.get("room") or [])})
            kind = collections.Counter(a.get("kind") for _, a in items).most_common(1)[0][0]
            for q in _pieces(U):
                if above is not None and q.intersection(above).area < 0.7 * q.area: continue       # outdoors / not under a slab
                if isinstance(H, tuple):                       # tray: lowered border + raised centre + riser
                    ctr = q.buffer(-BORDER)
                    base = q.difference(ctr) if not ctr.is_empty and ctr.area > 4000 else q
                    zb = fz + H[0]
                    counter[lv] += 1
                    new.append(_mk(lv, counter, "ceil_C1", cfin, _prism(base, zb, zb + 0.02), rooms, kind, "tray-border", H[0]))
                    ctr_pieces = _pieces(ctr, 4000, 20) if not ctr.is_empty else []
                    for c in ctr_pieces:
                        zc = fz + H[1]
                        counter[lv] += 1
                        new.append(_mk(lv, counter, "ceil_C1", cfin, _prism(c, zc, zc + 0.02), rooms, kind, "tray-centre", H[1]))
                        ring = c.buffer(1.2).difference(c.buffer(-0.2))
                        for r in _pieces(ring, 100, 0.5):
                            counter[lv] += 1
                            new.append(_mk(lv, counter, "ceil_riser", cfin, _prism(r, zb, zc + 0.02), rooms, kind, "tray-riser", H[1]))
                    ceil_of[lv].append((q, H[1], fz))
                else:
                    z = fz + H
                    counter[lv] += 1
                    new.append(_mk(lv, counter, "ceil_" + cfin, cfin, _prism(q, z, z + 0.02), rooms, kind, cls, H))
                    ceil_of[lv].append((q, H, fz))
            stats[(lv, cls)] += 1
    pool = M["sp"]
    idx = []
    for t in SRC:
        if t not in pool: pool.append(t)
        idx.append(pool.index(t))
    for e in new: e["s"] = list(idx)
    els.extend(new)
    n_dev = _move_devices(els, ceil_of, slabs, LV)
    return {"ceilings": len(new), "devices_moved": n_dev, "by_level": dict(counter)}


def _mk(lv, counter, typ, cfin, geom, rooms, kind, part, H):
    return {"id": f"A.ceil-{lv}-C{counter[lv]:04d}", "c": "A.ceil", "l": lv, "g": geom, "mark": "C1" if cfin == "C1" else "C3", "t": typ if typ != "ceil_C1" or cfin == "C1" else "ceil_C3",
            "m": "fin_" + cfin, "a": {"room": rooms, "kind": kind, "fin": [cfin], "fcl_m": H if not isinstance(H, tuple) else H[0], "zone": part}, "s": []}


def _shift(e, dz):
    g = e["g"]
    if g[0] in ("d", "t"):
        for pt in g[1]: pt[2] = round(pt[2] + dz, 3)
        return True
    ix = {"b": (6, 7), "r": (5, 6), "cyl": (4, 5)}.get(g[0])
    if not ix: return False
    g[ix[0]] = round(g[ix[0]] + dz, 3); g[ix[1]] = round(g[ix[1]] + dz, 3)
    return True


def _zr(g):
    if g[0] in ("d", "t"):
        zs = [p[2] for p in g[1]]
        return min(zs), max(zs)
    ix = {"b": (6, 7), "r": (5, 6), "cyl": (4, 5), "p": (2, 3)}.get(g[0])
    return (g[ix[0]], g[ix[1]]) if ix else (None, None)


def _xy(g):
    if g[0] in ("b", "cyl"): return Point(g[1], g[2])
    if g[0] == "r": return Point((g[1] + g[3]) / 2, (g[2] + g[4]) / 2)
    if g[0] in ("d", "t"):
        pts = g[1]; m = len(pts) // 2
        return Point(pts[m][0], pts[m][1])
    return None


def _move_devices(els, ceil_of, slabs, LV=None):
    """lights / detectors / diffusers / pendent sprinklers follow their ceiling (device centre inside the plate); in the open colonnade they go up to the slab soffit;
    devices that were hung in a stair / lift opening (no plate there any more) are fixed to the nearest wall of the opening"""
    trees = {}
    for lv, items in ceil_of.items():
        trees[lv] = (STRtree([q for q, _, _ in items]), items)
    soffit = {}
    if "1" in slabs: soffit["G"] = slabs["1"]["g"][2]
    # openings of the slab above each level (stairs, lifts, shafts) and the walls around them
    order = ORDER
    holes = {}
    for k, lv in enumerate(order[:-1]):
        nxt = order[k + 1]
        if nxt in slabs and len(slabs[nxt]["g"]) > 4 and slabs[nxt]["g"][4]:
            holes[lv] = [Polygon(h) for h in slabs[nxt]["g"][4] if len(h) >= 3]
    walls = collections.defaultdict(list)
    for e in els:
        if e["c"] in ("A.wall", "S.wall", "S.col") and e["g"][0] in ("p", "r"):
            q = _poly(e["g"])
            if q is not None and not q.is_empty: walls[e["l"]].append(q)
    wall_u = {lv: unary_union(v) for lv, v in walls.items()}
    from shapely.ops import nearest_points
    n = 0
    for e in els:
        lvl = e["l"]
        is_dev = e["c"] in DEV_CATS or e["t"] in DEV_TYPES
        is_void = lvl == "G" and e["c"][0] in "MEP" and e["t"] != "site_post_light" and e["g"][0] in ("b", "cyl", "r", "d", "t")
        if not (is_dev or is_void): continue
        g = e["g"]
        if g[0] not in ("b", "cyl", "r", "d", "t"): continue
        if e["t"] == "e_L4": continue                              # wall luminaires
        z0, z1 = _zr(g)
        a = e.setdefault("a", {})
        done = a.get("ceil_dz", 0.0)
        z0o, z1o = z0 - done, z1 - done                            # the original (assumed 2.70) position
        pt = _xy(g)
        if pt is None: continue
        ffl = LV[lvl]["ffl"] if LV and lvl in LV else None
        tp = trees.get(lvl)
        hit = None
        if tp:
            tree, items = tp
            for j in tree.query(pt):
                q, H, fz = items[j]
                if q.contains(pt):
                    hit = (H, fz); break
        in_hole = any(h.contains(pt) for h in holes.get(lvl, []))
        if hit is not None and not in_hole:
            H, fz = hit
            if is_dev and (fz + OLD_H - 0.25 <= z1o <= fz + OLD_H + 0.05 or e["t"] in PENDANTS and fz + OLD_H - 0.6 <= z1o <= fz + OLD_H + 0.05):
                want = ((fz + H) - z1o) if e["t"] in PENDANTS else H - OLD_H
            elif is_void and ffl is not None and z0o - ffl >= 2.5 and H > OLD_H + 0.05:
                want = H - OLD_H                                   # services in the void follow the higher ground-floor ceiling
            else:
                continue
        elif in_hole and is_dev and ffl is not None and (ffl + OLD_H - 0.25 <= z1o <= ffl + OLD_H + 0.05) and g[0] in ("b", "cyl"):
            # fix to the nearest wall of the opening, 9 cm off the face, top at 2.30 m above the landing
            wu = wall_u.get(lvl)
            if wu is None: continue
            p1, p2 = nearest_points(wu, pt)
            dx, dy = pt.x - p1.x, pt.y - p1.y; L = (dx * dx + dy * dy) ** 0.5 or 1.0
            nx, ny = p1.x + dx / L * 9.0, p1.y + dy / L * 9.0
            g[1], g[2] = round(nx, 1), round(ny, 1)
            want = (ffl + 2.30) - z1o
            a["mount_note"] = "ثُبّت على جدار فتحة السلم/المصعد: لا سقف مستعار داخل الفتحة (A1401)"
        elif lvl == "G" and "G" in soffit and ffl is not None and is_dev and (OLD_H - 0.25 <= z1o - ffl <= OLD_H + 0.05) and not in_hole:
            want = soffit["G"] - 0.01 - z1o
        else:
            continue
        d = round(want - done, 3)
        if abs(d) < 1e-6: continue
        if _shift(e, d):
            a["ceil_dz"] = round(want, 3); n += 1
    return n


def types():
    return {"ceil_riser": {"n": "جانب حوض السقف (Tray) — ممر/ردهة", "cf": "doc",
                           "sp": [["الارتفاع", "من 2.35 إلى 2.50 م فوق الأرضية (فرق 15 سم)"], ["الموضع", "حول المنطقة الوسطى المرفوعة من سقف الممر/ردهة المصاعد"]],
                           "sr": ["ARCH2 ص35 (A1601 المسقط المعكوس للممر: FCL +2.35 و+2.50)"]}}
