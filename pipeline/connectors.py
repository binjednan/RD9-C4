# -*- coding: utf-8 -*-
"""Derived connections (owner 2026-10-08: «أكمل استعمال جميع المخططات لتكون البيئة مناسبة للاختبار»).

The extraction put every pipe, duct and device where the plan drawings put it, but the LAST inch is missing: a sprinkler head hangs 55 cm under a pipe that passes right above it in plan, a mixer tap
stops 2 m below the pipe that ends beside it, a valve sits 8 cm next to its pipe.  Those short pieces are what plumbers and ducting contractors add on site; the plan shows the topology (pipe ends at
the device) and the 3-D elevations of both ends are already in the model, so the piece between them is DERIVED, not invented.  This module adds exactly those pieces and nothing else:

  joint  two components of one system whose pipe END comes within JOINT_MAX of the other component                                        -> a short coupling between the two closest points
  stub   a terminal (sprinkler head, diffuser, mixer, floor trap ...) that touches no conductor but has one of ITS system within STUB_R in plan   -> route: conductor point → above the device → down to it
  feed   a source (tank, chiller, heater, FCU ...) that touches no conductor but has one within FEED_R in plan                              -> same as a stub

Anything farther than that stays unconnected and fails the life-cycle test (pipeline/lifecycle.py): a real gap in the documents, listed for the owner.  Every piece carries a.connector,
a.from / a.to (element ids) and the grade 'vvv' (derived).  Ids end with -Knnnn, so post_model.py drops and rebuilds them on every run (idempotent)."""
import os, re, sys, math, collections

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lifecycle as L

JOINT_MAX = 0.20        # m  end-to-end / end-to-side gap that is a fitting, not a missing pipe
STUB_R = 60.0           # cm plan distance terminal surface ↔ conductor
FEED_R = 100.0          # cm plan distance source surface ↔ conductor
ID_RE = re.compile(r"-K\d{4}$")
SRC_TEXT = "وصلة مشتقة من المسقط: الماسورة تنتهي عند الجهاز في الرسم؛ النزول الرأسي والوصلة الأخيرة مشتقان من منسوبَي الطرفين (اختبارات دورة الحياة، pipeline/connectors.py)"
# type / material of a connector by the category of the conductor it continues
CONN = {"P.cold": ("pipe_cold", "p_cold"), "P.hot": ("pipe_hot", "p_hot"), "P.drain": ("pipe_waste", "p_waste"), "P.ff": ("pipe_ff", "p_ff"), "M.duct": ("duct_flex", "m_duct")}


def _ends(e):
    g = e["g"]
    return [(p[0] / 100.0, p[1] / 100.0, p[2]) for p in (g[1][0], g[1][-1])] if g[0] in ("t", "d") else []


def _poly(e):
    g = e["g"]
    return g[1] if g[0] in ("t", "d") else None


def _dia_cm(e):
    g = e["g"]
    if g[0] == "t": return g[2]
    if g[0] == "d": return round(min(max(g[2], g[3]) * 0.8, 25.0), 1)
    return 3.0


def closest_on_poly(poly, ax, ay):
    """plan-closest point of a polyline (points [x_cm, y_cm, z_m]) to (ax, ay) -> (distance_cm, [x, y, z])"""
    best = (1e18, None)
    for p, q in zip(poly, poly[1:]):
        dx, dy = q[0] - p[0], q[1] - p[1]; L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((ax - p[0]) * dx + (ay - p[1]) * dy) / L2))
        x, y = p[0] + dx * t, p[1] + dy * t; d = math.hypot(ax - x, ay - y)
        if d < best[0]: best = (d, [x, y, p[2] + (q[2] - p[2]) * t])
    return best


def anchor(e):
    """a device's attachment: (x_cm, y_cm, z_low, z_high) — centre of the footprint and its z span (a tube: first vertex)"""
    g = e["g"]
    if g[0] == "b": return g[1], g[2], g[6], g[7]
    if g[0] == "cyl": return g[1], g[2], g[4], g[5]
    if g[0] == "r": return (g[1] + g[3]) / 2, (g[2] + g[4]) / 2, g[5], g[6]
    if g[0] == "p":
        xs = [p[0] for p in g[1]]; ys = [p[1] for p in g[1]]; return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, g[2], g[3]
    if g[0] in ("t", "d"):
        zs = [p[2] for p in g[1]]; return g[1][0][0], g[1][0][1], min(zs), max(zs)
    return None


def plan_gap_cm(e, x, y):
    """plan distance (cm) from a point to the SURFACE of a device (0 when the point is over it)"""
    g = e["g"]
    if g[0] in ("t", "d"): return closest_on_poly(g[1], x, y)[0] - (g[2] / 2 if g[0] == "t" else 0)
    pr = L.prims(e)
    best = 1e18
    for p in pr:
        if p[0] == "box":
            c, h = p[1], p[2]
            dx = max(abs(x / 100.0 - c[0]) - h[0], 0.0); dy = max(abs(y / 100.0 - c[1]) - h[1], 0.0)
            best = min(best, math.hypot(dx, dy) * 100.0)
    return best


def attach_point(e, toward):
    """the point of a device the connector ends at, given the conductor point it comes from (x_cm, y_cm, z_m)"""
    g = e["g"]
    if g[0] in ("t", "d"):
        best = min(g[1], key=lambda p: math.hypot(p[0] - toward[0], p[1] - toward[1]))
        return [best[0], best[1], best[2]]
    x, y, z0, z1 = anchor(e); zc = toward[2]
    return [x, y, z1 if zc >= z1 else z0 if zc <= z0 else zc]


def route(pc, pt):
    """conductor point → horizontal run in the void at the conductor's elevation → vertical drop to the device (duplicate points removed)"""
    pts = [[pc[0], pc[1], pc[2]]]
    if math.hypot(pt[0] - pc[0], pt[1] - pc[1]) > 0.5: pts.append([pt[0], pt[1], pc[2]])
    pts.append([pt[0], pt[1], pt[2]])
    out = [[round(p[0], 1), round(p[1], 1), round(p[2], 3)] for p in pts]
    ded = [out[0]]
    for p in out[1:]:
        if math.hypot(p[0] - ded[-1][0], p[1] - ded[-1][1]) > 0.05 or abs(p[2] - ded[-1][2]) > 0.0015: ded.append(p)
    return ded if len(ded) > 1 else None


class UF:
    def __init__(self): self.p = {}
    def f(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x: self.p[x] = self.p[self.p[x]]; x = self.p[x]
        return x
    def u(self, a, b):
        a, b = self.f(a), self.f(b)
        if a == b: return False
        self.p[a] = b; return True


def build(M, verbose=False):
    els = M["els"]
    els[:] = [e for e in els if not ID_RE.search(e["id"])]
    sp = M["sp"]
    if SRC_TEXT not in sp: sp.append(SRC_TEXT)
    sidx = sp.index(SRC_TEXT)
    M.setdefault("types", {}).setdefault("duct_flex", {"n": "وصلة مجرى مرنة بين المجرى والناشر (مشتقة)", "cf": "derived", "sp": [["النوع", "وصلة مرنة مستديرة Ø 15–25 سم"], ["الأصل", "مشتقة من المسقط لإتمام اتصال الناشر بالمجرى"]], "sr": [SRC_TEXT]})
    counter = collections.Counter(); stats = collections.Counter(); new = []
    world = L.World(els)

    def make(kind, host, other, pts, sysid, note, vtype=None):
        """host = a tube conductor the new piece continues (category / material / type), other = the element at the far end"""
        eh = els[host]; eo = els[other]
        ct, cm = CONN.get(eh["c"], (eh["t"], eh["m"]))
        if eh["c"] == "M.pipe": ct, cm = eh["t"], eh["m"]
        if vtype: ct = vtype
        if cm not in M["mats"]: cm = eh["m"]
        counter[(eh["c"], eh["l"])] += 1
        dia = _dia_cm(eh)
        length = sum(math.hypot(p[0] - q[0], p[1] - q[1]) / 100.0 + abs(p[2] - q[2]) for p, q in zip(pts, pts[1:]))
        e = {"id": f"{eh['c']}-{eh['l']}-K{sum(counter.values()):04d}", "c": eh["c"], "l": eh["l"], "g": ["t", pts, dia], "mark": None, "t": ct, "m": cm,
             "a": {"connector": kind, "from": eh["id"], "to": eo["id"], "kind": note, "dia_mm": round(dia * 10), "length_m": round(length, 2)}, "s": [sidx]}
        if eh["c"] == "M.duct": e["a"].update({"w_cm": dia, "h_cm": dia})      # the sample library of the duct type reads the section size from these two attributes
        u = eo.get("u") or eh.get("u")
        if u: e["u"] = u
        new.append(e); stats[(sysid, kind)] += 1

    for sd in L.SYSTEMS:
        sid = sd["id"]
        if sd.get("no_connectors"): continue                  # electricity: only drawn conductors connect (pipeline/elec_build.py), nothing is derived here
        src = [i for i, e in enumerate(els) if sd["source"](e)]
        ter = [i for i, e in enumerate(els) if sd["terminal"](e)]
        for vname, vpred in sd["variants"]:
            con = [i for i, e in enumerate(els) if vpred(e)]
            node = set(con) | set(src)
            for i in node | set(ter): world.prim(i)
            # ---- components of conductors + sources at TOL
            uf = UF()
            for i in node: uf.f(i)
            for i, nb in L.neighbours(world, list(node)).items():
                for j in nb: uf.u(i, j)
            # ---- joints: closest pairs of different components within JOINT_MAX, the contact at an END of a tube (a pipe crossing another at a different height is not a joint)
            cand = []
            for i, nb in L.neighbours(world, list(node), tol=JOINT_MAX).items():
                for j, (d, c, x, y) in nb.items():
                    if i < j and d > L.TOL and uf.f(i) != uf.f(j): cand.append((d, i, j, x, y))
            cand.sort(key=lambda t: t[0])
            for d, i, j, x, y in cand:
                if uf.f(i) == uf.f(j): continue
                ei, ej = _ends(els[i]), _ends(els[j])
                at_end = (not sd.get("joint_end_only", True)) or (ei and any(math.dist(x, p) < 0.08 for p in ei)) or (ej and any(math.dist(y, p) < 0.08 for p in ej)) or not ei or not ej
                if not at_end: continue
                host, other, ph, po = (i, j, x, y) if ei else (j, i, y, x)
                pts = [[round(ph[0] * 100, 1), round(ph[1] * 100, 1), round(ph[2], 3)], [round(po[0] * 100, 1), round(po[1] * 100, 1), round(po[2], 3)]]
                if math.hypot(pts[0][0] - pts[1][0], pts[0][1] - pts[1][1]) < 0.05 and abs(pts[0][2] - pts[1][2]) < 0.0015: uf.u(i, j); continue
                uf.u(i, j); make("joint", host, other, pts, sid, "وصلة بين طرفين في الشبكة")
            # ---- stubs / feeds: devices that touch no conductor of this variant
            polys = collections.defaultdict(list)
            for i in con:
                pl = _poly(els[i])
                if pl: polys[els[i]["l"]].append((i, pl))
            adjT = L.neighbours(world, list(node | set(ter)))
            for role, group, radius in (("stub", ter, STUB_R), ("feed", src, FEED_R)):
                for t in group:
                    if any(j in node and j != t for j in adjT.get(t, {})): continue
                    et = els[t]; A = anchor(et)
                    if A is None: continue
                    best = (1e18, None, None)
                    for i, pl in polys.get(et["l"], []):
                        d, pc = closest_on_poly(pl, A[0], A[1])
                        if d < best[0]: best = (d, i, pc)
                    d, i, pc = best
                    if i is None or plan_gap_cm(et, pc[0], pc[1]) > radius: continue
                    pts = route(pc, attach_point(et, pc))
                    if not pts: continue
                    make(role, i, t, pts, sid, "وصلة الجهاز بالشبكة" if role == "stub" else "وصلة المصدر بالشبكة")
                    uf.u(i, t)
    els.extend(new)
    if verbose: print("connectors:", len(new), dict(sorted(((f"{s}/{k}", v) for (s, k), v in stats.items()))))
    return stats


if __name__ == "__main__":
    import json
    SRC = os.path.join(os.path.dirname(HERE), "src", "model.json")
    M = json.load(open(SRC, encoding="utf-8"))
    n0 = len(M["els"])
    build(M, verbose=True)
    print("elements", n0, "->", len(M["els"]))
    json.dump(M, open("/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/life/model_conn.json", "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
    L.run(M, verbose=True)
