# -*- coding: utf-8 -*-
"""Electrical conductors + distribution boards as model elements (data: pipeline/data/elec_wires.json from pipeline/elec_wires.py).

  boards      the label of every board symbol of the power plans becomes an E.panel box (DB-F1 … DB-F6, DB-SR, SMDB-n); a board the model already has (symbol class e_P18, MDB) is reused
  circuits    every drawn conductor chain becomes E.tray tubes at the height the wiring runs: lighting in the ceiling void just above the highest fixture of the chain (Z_VOID), power (drawn dashed = concealed
              in the floor) in the screed.  ONE elevation per chain, so the polylines of a chain keep touching each other
  drops       from a chain down / up to every device of its family within SNAP of it in plan (fixtures + switches for lighting, sockets for power)
  circuit ends a chain end that carries a circuit tag «R1/DB-F1» (arrow + tag in the drawing) gets a short marked stub (CIRCUIT_END cm) pointing the way the circuit leaves the drawn conductors.  The ROUTE between
              the arrow and the board is NOT drawn on the plans, so no line is invented across rooms and walls (owner 2026-10-08, screenshots: «خطوط تعبر الجدران»): the stub names the board and
              carries its element id and the plan distance in the data (a.dest / a.to / a.plan_m) and the life-cycle tests treat the stub as the boundary of the drawn network

Ids end with -Wnnnn (W = wire), rebuilt on every run; post_model.py calls build() after the clash pass.  Nothing is joined that the drawings do not name: a device far from every chain, or a chain end
without a tag, stays unconnected and fails the life-cycle test (pipeline/lifecycle.py)."""
import os, re, sys, json, math, collections
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import connectors as C

DATA = os.path.join(HERE, "data", "elec_wires.json")
ID_RE = re.compile(r"-W\d{4}$")
LEVELS = {"B": ["B"], "G": ["G"], "1": ["1"], "TY": ["2", "3", "4", "5"], "R": ["R"], "T": ["T"]}
SNAP = 40.0               # cm  a device this close to a chain (plan) hangs on it (the placement passes move devices up to ~40 cm to the wall / ceiling grid)
END_TAG = 150.0           # cm  a circuit tag this close to a chain end belongs to that end
JOIN = 6.0                # cm  chain ends / vertices closer than this are one point
Z_LIGHT = 2.75            # m above the finished floor: lighting conduit in the ceiling void when a chain has no fixture to measure from (fixtures of the typical floors sit at about +2.35)
Z_VOID = 0.12             # m  the conduit of a lighting chain runs this far above the TOP of its highest fixture (ceilings differ: +2.4 flats, +3.4…+5 ground floor lobbies, basement slab soffit)
Z_CLEAR = 0.10            # m  never closer than this to the slab above (level top)
CIRCUIT_END = 30.0        # cm  length of the marked stub where a circuit leaves the drawn conductors
Z_POWER = -0.05           # m: power circuits are drawn dashed = concealed in the floor screed
DEST = re.compile(r"(S?MDB(?:-[A-Z0-9]+)*|DB(?:-[A-Z0-9]+)+)")
def norm(name): return re.sub(r"^DB-\d-", "DB-", name)          # DB-1-F4 (first-floor naming) is DB-F4 in the tags
SRC_TEXT = "موصل كهرباء من طبقة التوصيل في مخططات ELEC1 (E.LIGHT CONNE / E.POWER. CONNE): الخط بين الأجهزة وسهم الدائرة ووسمها مرسومة؛ ارتفاع التمديد من افتراضات الفراغ (pipeline/elec_build.py)"
MATS = {"m_wire": {"name": "موصل / مسار كابلات (توصيل الدوائر)", "color": "#6d5fb5", "code": "E.CONNE"},
        "m_db": {"name": "لوحة توزيع (DB)", "color": "#8e8ea0", "code": "E.POWER"}}
TYPES = {
    "wire_light": {"n": "دائرة إنارة — موصل بين الكشافات والمفاتيح", "cf": "doc", "sp": [["المصدر", "طبقة E.LIGHT CONNE. NORMAL في ELEC1 (مسقط الإنارة)"], ["الارتفاع", "في فراغ السقف (افتراض)"]], "sr": []},
    "wire_power": {"n": "دائرة قوى — موصل بين المقابس (مخفي في الأرضية)", "cf": "doc", "sp": [["المصدر", "طبقة E.POWER. CONNE.NORMAL في ELEC1 (خط متقطع = مخفي في الأرضية)"]], "sr": []},
    "wire_drop": {"n": "نزول الموصل إلى الجهاز", "cf": "derived", "sp": [["الأصل", "الجهاز على الدائرة في المسقط؛ النزول الرأسي مشتق من منسوبَي الطرفين"]], "sr": []},
    "wire_circuit_end": {"n": "نهاية دائرة إلى لوحتها (المسار غير مرسوم)", "cf": "doc", "sp": [["الأصل", "سهم الدائرة ووسمها (R1/DB-…) واللوحة مرسومة في المسقط؛ المسار بين السهم واللوحة غير مرسوم فلا يُرسم"]], "sr": []},
    "wire_homerun_open": {"n": "نهاية دائرة إلى لوحة غير مرسومة", "cf": "assumed", "sp": [["الأصل", "سهم الدائرة ووسمها مرسومان؛ اللوحة نفسها غير مرسومة في المسقط"]], "sr": []},
    "det_db": {"n": "لوحة توزيع (DB)", "cf": "derived", "sp": [["الأصل", "تسمية اللوحة في مسقط القدرة؛ الأبعاد افتراض 50×15×70 سم"]], "sr": []},
}
LIGHT_T = lambda e: (e["c"] in ("E.light",) and (e.get("t") or "").startswith("e_L")) or (e["c"] == "E.socket" and (e.get("t") or "").startswith("e_S"))
POWER_T = lambda e: e["c"] == "E.socket" and (e.get("t") or "").startswith("e_P") and e.get("t") not in ("e_P14", "e_P15", "e_P16", "e_P18")


def _poly_len(pl): return sum(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(pl, pl[1:]))


OPEN_SKY_M2 = 50.0        # a hole of the slab above bigger than this is open to the sky (the car ramp, 148 m²); lift shafts and stair voids are smaller and keep their conductors


def open_sky(M):
    """level -> shapely geometry of the big openings of the slab ABOVE that level: a conductor drawn over them would hang in the open air"""
    nxt = {a["id"]: b["id"] for a, b in zip(M["levels"], M["levels"][1:])}; holes = collections.defaultdict(list)
    for e in M["els"]:
        if e["c"] != "S.slab" or e["g"][0] != "p" or len(e["g"]) < 5 or not e["g"][4]: continue
        for h in e["g"][4]:
            try: pg = Polygon(h).buffer(0)
            except Exception: continue
            if pg.area / 1e4 >= OPEN_SKY_M2: holes[e["l"]].append(pg)
    out = {}
    for lv, upper in nxt.items():
        if holes.get(upper): out[lv] = unary_union(holes[upper])
    return out


def clip_open(pl, hole, min_cm=20.0):
    """polyline [(x, y)…] -> the parts of it outside `hole` (a conductor is not drawn across the open ramp)"""
    if hole is None: return [pl]
    ls = LineString(pl)
    if not ls.intersects(hole): return [pl]
    d = ls.difference(hole); parts = [d] if d.geom_type == "LineString" else [g for g in getattr(d, "geoms", []) if g.geom_type == "LineString"]
    return [[(round(x, 1), round(y, 1)) for x, y in g.coords] for g in parts if g.length >= min_cm]


def build(M, verbose=False):
    els = M["els"]
    els[:] = [e for e in els if not ID_RE.search(e["id"])]
    if not os.path.exists(DATA): return 0
    D = json.load(open(DATA, encoding="utf-8"))
    sp = M["sp"]
    if SRC_TEXT not in sp: sp.append(SRC_TEXT)
    sidx = sp.index(SRC_TEXT)
    for k, v in MATS.items(): M["mats"].setdefault(k, v)
    for k, v in TYPES.items(): M.setdefault("types", {}).setdefault(k, v)
    ffl = {l["id"]: l["ffl"] for l in M["levels"]}
    new = []; counter = collections.Counter(); stats = collections.Counter()
    devs = collections.defaultdict(list)                    # level -> element indices (E.*) that exist before this pass
    for i, e in enumerate(els):
        if e["c"][0] == "E": devs[e["l"]].append(i)

    extra = [9000]                                           # ids W9001… are for the second, third… part of a conductor that was cut by an opening (the first part keeps the original number, so no id after it shifts)
    def add(c, l, g, t, m, mark=None, a=None, u=None, number=None):
        counter[(c, l)] += 1
        e = {"id": f"{c}-{l}-W{(number if number is not None else sum(counter.values())):04d}", "c": c, "l": l, "g": g, "mark": mark, "t": t, "m": m, "a": a or {}, "s": [sidx]}
        if u: e["u"] = u
        new.append(e); return len(els) + len(new) - 1

    def unit_at(l, x, y):
        for u in M.get("units", []):
            if u["level"] != l: continue
            for r in u["rects"]:
                if r[0] <= x <= r[2] and r[1] <= y <= r[3]: return u["id"]
        return None

    def elem(i): return els[i] if i < len(els) else new[i - len(els)]

    boards_of = {}                                           # (sheet key, level) -> {name: element index}
    for sk, levels in LEVELS.items():
        psheet = D.get("power|" + sk)
        for lv in levels:
            if lv not in ffl: continue
            f0 = ffl[lv]; bd = {}
            for b in (psheet["boards"] if psheet else []):
                name = b["n"]; hit = None
                for i in devs[lv]:
                    e = els[i]
                    if e["g"][0] != "b": continue
                    near = math.hypot(e["g"][1] - b["x"], e["g"][2] - b["y"]) < 90
                    if near and ((e["c"] == "E.panel" and (e.get("t") or "").startswith("det_")) or e.get("t") == "e_P18"): hit = i; break
                if hit is None:
                    hit = add("E.panel", lv, ["b", round(b["x"], 1), round(b["y"], 1), 50, 15, 0.0, round(f0 + 1.1, 3), round(f0 + 1.8, 3)], "det_db", "m_db", mark=name,
                              a={"kind": "لوحة توزيع", "assumed": "الأبعاد 50×15×70 سم والارتفاع افتراض؛ الموضع تسمية الرمز في المسقط"}, u=unit_at(lv, b["x"], b["y"]))
                    stats["boards"] += 1
                else:
                    if not els[hit].get("mark"): els[hit]["mark"] = name                        # an existing board symbol takes the plan's name
                bd[norm(name)] = hit
            boards_of[(sk, lv)] = bd

    top_of = {l["id"]: l.get("top") for l in M["levels"]}
    sky = open_sky(M)
    for key, sheet in D.items():
        fam, sk = key.split("|")
        sel = LIGHT_T if fam == "light" else POWER_T
        for lv in LEVELS[sk]:
            if lv not in ffl: continue
            f0 = ffl[lv]; bd = boards_of.get((sk, lv), {})
            hole = sky.get(lv)
            parts_of = [[clip_open(pl, hole) for pl in ch] for ch in sheet["chains"]]                           # nothing is drawn across the open car ramp
            chains = [[q for parts in ch for q in parts] for ch in parts_of]
            # ---- 1. every device of the family hangs on the nearest drawn conductor (plan distance <= SNAP)
            att = collections.defaultdict(list)                                         # chain index -> [(element index, anchor)]
            for i in devs[lv]:
                e = els[i]
                if not sel(e): continue
                A = C.anchor(e)
                if A is None: continue
                best = (1e18, None)
                for ci, ch in enumerate(chains):
                    for pl in ch:
                        d, _ = C.closest_on_poly([[x, y, 0.0] for x, y in pl], A[0], A[1])
                        if d < best[0]: best = (d, ci)
                if best[1] is not None and best[0] <= SNAP: att[best[1]].append((i, A))
            # ---- 2. one elevation per chain
            zc = {}
            for ci in range(len(chains)):
                if fam == "light":
                    tops = [A[3] for _, A in att.get(ci, [])]
                    z = (max(tops) + Z_VOID) if tops else (f0 + Z_LIGHT)
                    if top_of.get(lv) is not None: z = min(z, top_of[lv] - Z_CLEAR)
                    zc[ci] = round(max(z, f0 + 0.3), 3)
                else: zc[ci] = round(f0 + Z_POWER, 3)
            polys = []                                                                  # (chain index, polyline, element index)
            for ci, ch in enumerate(parts_of):
                for parts in ch:
                    if not parts: counter[("skipped", lv, fam)] += 1; stats["wires_dropped_open"] += 1; continue     # fully over the open ramp: its id number stays reserved
                    for n_, pl in enumerate(parts):
                        pts = [[round(x, 1), round(y, 1), zc[ci]] for x, y in pl]
                        if len(pts) < 2: continue
                        num = None
                        if n_ > 0: extra[0] += 1; num = extra[0]
                        i = add("E.tray", lv, ["t", pts, 2.0], "wire_light" if fam == "light" else "wire_power", "m_wire",
                                a={"kind": "دائرة إنارة" if fam == "light" else "دائرة قوى", "length_m": round(_poly_len(pl) / 100.0, 2), "dia_mm": 20, "chain": ci,
                                   "assumed": ("ارتفاع التمديد افتراض: فراغ السقف فوق أعلى كشاف في الدائرة" if fam == "light" else "ارتفاع التمديد افتراض: مخفي في الأرضية")}, u=unit_at(lv, pl[0][0], pl[0][1]), number=num)
                        polys.append((ci, pts, i)); stats["wires_" + fam] += 1
            # ---- 3. drops to the devices
            by_chain = collections.defaultdict(list)
            for c, pts, wi in polys: by_chain[c].append((pts, wi))
            for i, ci, A in sorted((i, ci, A) for ci, lst in att.items() for i, A in lst):      # device order (stable ids)
                e = els[i]; best = (1e18, None, None)
                for pts, wi in by_chain.get(ci, []):
                    d, pc = C.closest_on_poly(pts, A[0], A[1])
                    if d < best[0]: best = (d, pc, wi)
                if best[1] is None: continue
                route = C.route(best[1], C.attach_point(e, best[1]))
                if not route: continue
                add("E.tray", lv, ["t", route, 1.6], "wire_drop", "m_wire", a={"kind": "نزول إلى الجهاز", "from": elem(best[2])["id"], "to": e["id"], "dia_mm": 16,
                    "length_m": round(sum(math.hypot(p[0] - q[0], p[1] - q[1]) / 100.0 + abs(p[2] - q[2]) for p, q in zip(route, route[1:])), 2)}, u=e.get("u"))
                stats["drops_" + fam] += 1
            # ---- 4. circuit ends: a free chain end with a circuit tag next to it names its board; only a short stub is drawn
            tags = [t for t in sheet["tags"] if DEST.search(t["t"])]
            for ci in sorted({c for c, _, _ in polys}):
                mine = [(pts, wi) for c, pts, wi in polys if c == ci]
                ends = []
                for pts, wi in mine:
                    for p in (pts[0], pts[-1]):
                        shared = any(math.hypot(q[0] - p[0], q[1] - p[1]) < JOIN for pts2, wi2 in mine if wi2 != wi for q in pts2)       # free end: not within JOIN of another polyline of the chain
                        if not shared: ends.append((p, wi))
                for p, wi in ends:
                    bt = min(((math.hypot(t["x"] - p[0], t["y"] - p[1]), t) for t in tags), key=lambda x: x[0], default=(1e18, None))
                    if bt[1] is None or bt[0] > END_TAG: continue
                    name = norm(DEST.search(bt[1]["t"]).group(1)); bi = bd.get(name)
                    q = None
                    for pts2, wi2 in mine:
                        if wi2 == wi: q = pts2[-2] if p == pts2[-1] else pts2[1]
                    dx, dy = (p[0] - q[0], p[1] - q[1]) if q else (1.0, 0.0); n_ = math.hypot(dx, dy) or 1.0
                    stub = [[p[0], p[1], p[2]], [round(p[0] + dx / n_ * CIRCUIT_END, 1), round(p[1] + dy / n_ * CIRCUIT_END, 1), p[2]]]
                    if bi is None:
                        add("E.tray", lv, ["t", stub, 2.0], "wire_homerun_open", "m_wire", a={"kind": "نهاية دائرة إلى " + name + " (اللوحة غير مرسومة)", "tag": bt[1]["t"], "dest": name, "from": elem(wi)["id"], "dia_mm": 20,
                            "length_m": round(CIRCUIT_END / 100.0, 2), "assumed": "الوجهة موسومة في المسقط لكن اللوحة غير مرسومة: القطعة علامة لخروج الدائرة من المرسوم"}, u=elem(wi).get("u"))
                        stats["circuit_end_open"] += 1
                    else:
                        bx, by = elem(bi)["g"][1], elem(bi)["g"][2]
                        add("E.tray", lv, ["t", stub, 2.0], "wire_circuit_end", "m_wire", a={"kind": "نهاية دائرة إلى " + name, "tag": bt[1]["t"], "dest": name, "to": elem(bi)["id"], "from": elem(wi)["id"], "dia_mm": 20,
                            "length_m": round(CIRCUIT_END / 100.0, 2), "plan_m": round(math.hypot(bx - p[0], by - p[1]) / 100.0, 1), "assumed": CIRCUIT_END_ASSUMED}, u=elem(wi).get("u"))
                        stats["circuit_end_" + fam] += 1
    els.extend(new)
    if verbose: print("elec wires:", len(new), dict(stats))
    return len(new)


CIRCUIT_END_ASSUMED = "مسار الدائرة بين نهاية الموصل واللوحة غير مرسوم في المسقط: المرسوم السهم ووسم الدائرة (R1/DB-…) واللوحة؛ لا يُرسم خط مختلَق عبر الغرف والجدران"

if __name__ == "__main__":
    SRC = os.path.join(os.path.dirname(HERE), "src", "model.json")
    M = json.load(open(SRC, encoding="utf-8"))
    n0 = len(M["els"]); build(M, verbose=True); print("elements", n0, "->", len(M["els"]))
