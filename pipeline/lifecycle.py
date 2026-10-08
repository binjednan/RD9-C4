# -*- coding: utf-8 -*-
"""System life-cycle tests (owner 2026-10-08: «قم بدورة حياة للكهرباء … تضيء فقط ما هو موصل بموصلات فعلية … أيضًا للتكييف والمياه والصرف والحريق … اعتبرها اختبارات»).

For every building system the model is "switched on" from its sources: electricity from the transformer / MDB / generator, chilled water from the chillers, supply air from the FCUs, cold water from the
domestic tank, hot water from the heaters, fire water from the fire tanks, drainage from the outlet back to the fixtures.  What is energised is exactly what is connected through REAL geometry in the
model — conductors, pipes, ducts and in-line valves / dampers that touch each other (surface gap <= TOL) — so a device that merely sits near a pipe, a pipe that stops short of its riser or a fixture
without a drain stays dark and shows up as a failed test.  Nothing here assumes a connection: it only measures the model.

  python3 pipeline/lifecycle.py            # analyse src/model.json, write docs/LIFECYCLE_TESTS.md, print the table; exit code 1 if a test regressed against pipeline/data/lifecycle_baseline.json
  python3 pipeline/lifecycle.py --save     # same, and store the result inside src/model.json (M['lifecycle']) for the viewer's «اختبارات دورة الحياة»
  python3 pipeline/lifecycle.py --baseline # record the current pass counts as the new floor (after an intended improvement)

post_model.py calls apply(M) at its end so the viewer always shows the current state.  Geometry units: plan x / y in cm, z in metres (as everywhere in model.json); distances below are metres."""
import os, sys, json, math, heapq, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src", "model.json")
BASE = os.path.join(HERE, "data", "lifecycle_baseline.json")
DOC = os.path.join(ROOT, "docs", "LIFECYCLE_TESTS.md")

TOL = 0.04          # surface gap (m) that still counts as touching: pipe fittings / rounding of the extraction, not a design gap
CELL = 1.0          # spatial hash cell (m)
NEAR_CM = 60.0      # diagnosis only: a failing terminal with a conductor of its system this close IN PLAN is «missing connector», farther is «nothing documented nearby»


# ------------------------------------------------------------------------------------------------ geometry
def prims(e):
    """element -> primitives in metres: ('seg', p, q, r) capsule axis | ('box', centre, half, None) axis-aligned bound of the (possibly rotated) box"""
    g = e["g"]; k = g[0]; out = []
    if k in ("t", "d"):
        pts = [(p[0] / 100.0, p[1] / 100.0, p[2]) for p in g[1]]
        r = g[2] / 200.0 if k == "t" else (g[2] + g[3]) / 400.0
        if len(pts) == 1: pts = pts * 2
        for a, b in zip(pts, pts[1:]): out.append(("seg", a, b, r))
    elif k == "b":
        cx, cy, w, d, rot, z0, z1 = g[1:8]
        th = math.radians(rot); c, s = abs(math.cos(th)), abs(math.sin(th))
        hx, hy = (c * w + s * d) / 200.0, (s * w + c * d) / 200.0
        out.append(("box", (cx / 100.0, cy / 100.0, (z0 + z1) / 2), (hx, hy, (z1 - z0) / 2), None))
    elif k == "cyl":
        cx, cy, r, z0, z1 = g[1:6]
        out.append(("box", (cx / 100.0, cy / 100.0, (z0 + z1) / 2), (r / 100.0, r / 100.0, (z1 - z0) / 2), None))
    elif k == "r":
        x0, y0, x1, y1, z0, z1 = g[1:7]
        out.append(("box", ((x0 + x1) / 200.0, (y0 + y1) / 200.0, (z0 + z1) / 2), (abs(x1 - x0) / 200.0, abs(y1 - y0) / 200.0, (z1 - z0) / 2), None))
    elif k == "p":
        pts = g[1]; z0, z1 = g[2], g[3]; xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        out.append(("box", ((min(xs) + max(xs)) / 200.0, (min(ys) + max(ys)) / 200.0, (z0 + z1) / 2), ((max(xs) - min(xs)) / 200.0, (max(ys) - min(ys)) / 200.0, (z1 - z0) / 2), None))
    return out


def _sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def _clamp(x, lo=0.0, hi=1.0): return lo if x < lo else hi if x > hi else x


def seg_seg(p1, q1, p2, q2):
    """closest points of two segments -> (distance, point on 1, point on 2)"""
    d1 = _sub(q1, p1); d2 = _sub(q2, p2); r = _sub(p1, p2)
    a = _dot(d1, d1); e = _dot(d2, d2); f = _dot(d2, r)
    if a < 1e-12 and e < 1e-12: s = t = 0.0
    elif a < 1e-12: s = 0.0; t = _clamp(f / e)
    else:
        c = _dot(d1, r)
        if e < 1e-12: t = 0.0; s = _clamp(-c / a)
        else:
            b = _dot(d1, d2); den = a * e - b * b
            s = _clamp((b * f - c * e) / den) if den > 1e-12 else 0.0
            t = (b * s + f) / e
            if t < 0.0: t = 0.0; s = _clamp(-c / a)
            elif t > 1.0: t = 1.0; s = _clamp((b - c) / a)
    c1 = (p1[0] + d1[0] * s, p1[1] + d1[1] * s, p1[2] + d1[2] * s); c2 = (p2[0] + d2[0] * t, p2[1] + d2[1] * t, p2[2] + d2[2] * t)
    return math.dist(c1, c2), c1, c2


def pt_box(p, c, h):
    q = tuple(min(max(p[i], c[i] - h[i]), c[i] + h[i]) for i in range(3))
    return math.dist(p, q), q


def seg_box(a, b, c, h, n=16):
    """distance from the segment a–b to an axis-aligned box (centre c, half sizes h) -> (distance, point on the segment, point on the box).  The distance from a point of a line to a convex set is a convex function
    of the parameter, so a ternary search is exact.  (It was a 16-sample scan: a long duct passing through a thin grille between two samples read as 4 cm apart and a connected terminal stayed dark.)"""
    def f(t):
        p = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t); d, q = pt_box(p, c, h); return d, p, q
    lo, hi = 0.0, 1.0
    for _ in range(40):
        m1 = lo + (hi - lo) / 3.0; m2 = hi - (hi - lo) / 3.0
        if f(m1)[0] <= f(m2)[0]: hi = m2
        else: lo = m1
    best = f((lo + hi) / 2.0)
    for t in (0.0, 1.0):
        r = f(t)
        if r[0] < best[0]: best = r
    return best


def box_box(c1, h1, c2, h2):
    gaps = [max(0.0, abs(c1[i] - c2[i]) - h1[i] - h2[i]) for i in range(3)]
    mid = tuple((c1[i] + c2[i]) / 2 for i in range(3))
    return math.sqrt(sum(g * g for g in gaps)), mid, mid


def gap(pa, pb):
    """smallest surface gap between two elements (lists of primitives) -> (gap, point on a, point on b)"""
    best = (1e9, None, None)
    for a in pa:
        for b in pb:
            if a[0] == "seg" and b[0] == "seg": d, x, y = seg_seg(a[1], a[2], b[1], b[2]); d -= a[3] + b[3]
            elif a[0] == "seg": d, x, y = seg_box(a[1], a[2], b[1], b[2]); d -= a[3]
            elif b[0] == "seg": d, y, x = seg_box(b[1], b[2], a[1], a[2]); d -= b[3]
            else: d, x, y = box_box(a[1], a[2], b[1], b[2])
            if d < best[0]: best = (d, x, y)
    return best


def bound(pr, pad=0.0):
    mn = [1e9] * 3; mx = [-1e9] * 3
    for p in pr:
        if p[0] == "seg":
            for q in (p[1], p[2]):
                for i in range(3): mn[i] = min(mn[i], q[i] - p[3]); mx[i] = max(mx[i], q[i] + p[3])
        else:
            for i in range(3): mn[i] = min(mn[i], p[1][i] - p[2][i]); mx[i] = max(mx[i], p[1][i] + p[2][i])
    return [v - pad for v in mn], [v + pad for v in mx]


# ------------------------------------------------------------------------------------------------ the systems
def _t(e): return e.get("t") or ""
def _m(e): return e.get("mark") or ""
def _part(e): return (e.get("a") or {}).get("part") or ""


def fix_cold_inlet(e):                # where a cold supply pipe really ends on a fixture: the mixer, the cistern, the hand spray (spout / shower column are fed from the mixer)
    if e["c"] != "P.fix": return False
    t = _t(e); p = _part(e)
    return (t == "san_tap" and "خلاط" in p) or (t == "san_wc" and "الخزان" in p) or (t == "san_accessory" and "A1203: WATER HOSE" in p)
def fix_hot_inlet(e): return e["c"] == "P.fix" and _t(e) == "san_tap" and "خلاط" in _part(e)
def fix_waste_outlet(e):              # the part that sits over the drain: WC bowl base, basin bottom, tub bottom
    if e["c"] != "P.fix": return False
    t = _t(e); p = _part(e)
    return (t == "san_wc" and "قاعدة الحوض" in p) or (t == "san_basin" and "القاع" in p) or (t == "san_tub" and "قاع" in p)


def _grp(e): return e.get("grp") or e["id"]

# Every system: sources (where it is switched on), conductors (pipes / ducts / conduits and in-line valves / dampers), terminals (where it is used).
# `variants` are separate conductor networks that must ALL reach a terminal (chilled-water supply and return).  `sink=True` runs the flow backwards (drainage: from the outlet to the fixtures).
VENT_T = ("duct_ea", "duct_fa", "riser_ea", "riser_fa", "damper_ea", "damper_fa", "duct_flex_ea", "duct_flex_fa")       # the ventilation network (pipeline/vent_build.py) is tested apart from the supply air
BOARDS_T = ("det_db", "e_P18")                                   # distribution boards: wired from their circuits, boundary of what the drawings connect
def _is_board(e): return (e["c"] == "E.panel" and _t(e) == "det_db") or _t(e) == "e_P18"
def _elec_load(e):
    t = _t(e)
    if e["c"] in ("E.light", "E.emerg"): return True
    if e["c"] == "E.socket": return (t.startswith("e_S") or t.startswith("e_P")) and t not in ("e_P14", "e_P15", "e_P16", "e_P18")
    return False


SYSTEMS = [
    dict(id="power", name="الكهرباء", icon="⚡", color="#8C6BD0", pass_terminal=True, no_connectors=True,
         desc="اللوحة الرئيسية MDB ← لوحات التوزيع (DB / SMDB) ← دوائر الإنارة والقوى (موصلات مرسومة في ELEC1) ← الكشافات والمفاتيح والمقابس؛ المغذّيات بين اللوحات غير مرسومة",
         source=lambda e: e["c"] == "E.panel" and _t(e) == "det_mdb_2000a",
         edge=lambda e: _is_board(e) or _t(e) in ("wire_homerun_open", "wire_circuit_end"), edge_name="لوحات التوزيع ونهايات الدوائر (المسار من نهاية الموصل إلى اللوحة والمغذّيات من MDB غير مرسومة في المخططات)",
         variants=[("الدوائر", lambda e: (e["c"] == "E.tray" and _t(e).startswith("wire_")) or _is_board(e))],
         terminal=_elec_load, term_name=lambda e: "كشاف" if e["c"] in ("E.light", "E.emerg") else "مفتاح / مقبس", source_name="MDB", conductor_name="موصل كهرباء"),
    dict(id="fire", name="الإطفاء", icon="🔥", color="#D55E00",
         desc="خزانات الإطفاء ← أنابيب السحب ← الصاعدان ← شبكة الرشاشات وخط FFC ← الرشاشات وصناديق الخراطيم",
         source=lambda e: e["c"] == "P.tank" and _t(e) == "tank_water" and _m(e) in ("FT1", "FT2"),
         edge=lambda e: e["c"] == "P.ff" and _t(e) in ("riser_spr", "riser_ffc") and _m(e) in ("G→1", "B→G"), edge_name="مخرج مضخات الإطفاء (غير مرسومة)",
         variants=[("الشبكة", lambda e: e["c"] == "P.ff" and (_t(e).startswith("pipe_") or _t(e).startswith("riser_") or _t(e) == "sprk_drop"))],
         terminal=lambda e: e["c"] == "P.ff" and (_t(e) in ("sprk_pendent", "sprk_upright", "sprk_double") or _t(e) == "fhc"),
         term_name=lambda e: "صندوق خرطوم" if _t(e) == "fhc" else "رشاش", source_name="خزان إطفاء", conductor_name="أنبوب إطفاء"),
    dict(id="chw", name="المياه المبردة", icon="❄", color="#0072B2",
         desc="المبردات والمضخات ← أنابيب التغذية ← وحدات FCU / FAHU ← أنابيب الرجوع ← المبردات",
         source=lambda e: e["c"] == "M.equip" and _t(e) in ("chiller", "chwp"),
         variants=[("تغذية", lambda e: e["c"] == "M.pipe" and _t(e) == "pipe_chws"), ("رجوع", lambda e: e["c"] == "M.pipe" and _t(e) == "pipe_chwr")],
         terminal=lambda e: e["c"] == "M.equip" and _t(e) in ("fcu", "fahu"),
         term_name=lambda e: "وحدة مناولة" if _t(e) == "fahu" else "FCU", source_name="مبرّد / مضخة", conductor_name="أنبوب مياه مبردة"),
    dict(id="air", name="هواء التغذية", icon="≋", color="#56B4E9",
         desc="وحدات FCU / FAHU ← مجاري الهواء والمخمّدات ← الناشرات وفتحات التغذية (الراجع عبر السقف المستعار بلا مجاري مرسومة)",
         source=lambda e: e["c"] == "M.equip" and _t(e) in ("fcu", "fahu"),
         variants=[("الشبكة", lambda e: e["c"] in ("M.duct", "M.damper") and _t(e) not in VENT_T)],
         terminal=lambda e: e["c"] == "M.outlet" and _t(e) in ("diff_supply", "grille_supply"),
         term_name=lambda e: "ناشر تغذية" if _t(e) == "diff_supply" else "فتحة تغذية", source_name="FCU / FAHU", conductor_name="مجرى هواء"),
    dict(id="vent_fa", name="التهوية — الهواء النقي", icon="⇣", color="#4d9a73",
         desc="وحدة معالجة الهواء النقي FAHU على السطح ← صاعد الهواء النقي (ينزل حتى البدروم) ← مجاري كل طابق ومخمّداتها ← الشبكات السلكية عند نهايات المجاري (المرسوم في مخططات التهوية VE-100…VE-105)",
         source=lambda e: e["c"] == "M.equip" and _t(e) == "fahu",
         variants=[("الشبكة", lambda e: (e["c"] == "M.duct" and _t(e) in ("duct_fa", "riser_fa", "duct_flex_fa")) or (e["c"] == "M.damper" and _t(e) == "damper_fa"))],
         terminal=lambda e: e["c"] == "M.outlet" and _t(e) == "grille_fa", term_name=lambda e: "شبكة هواء نقي", source_name="FAHU", conductor_name="مجرى هواء نقي"),
    dict(id="vent_ea", name="التهوية — الشفط", icon="⇡", color="#b0763a", sink=True,
         desc="الناشرات وشبكات الشفط في الحمامات والمطابخ ← مجاري الشفط ومخمّداتها ← صاعد الشفط ← قسم الشفط في وحدة FAHU على السطح (الاتجاه معكوس: يُختبر الوصل من المصدر نحو الناشرات)",
         source=lambda e: e["c"] == "M.equip" and _t(e) == "fahu",
         variants=[("الشبكة", lambda e: (e["c"] == "M.duct" and _t(e) in ("duct_ea", "riser_ea", "duct_flex_ea")) or (e["c"] == "M.damper" and _t(e) == "damper_ea"))],
         terminal=lambda e: e["c"] == "M.outlet" and _t(e) in ("diff_extract", "grille_ea"), term_name=lambda e: "ناشر شفط" if _t(e) == "diff_extract" else "شبكة شفط", source_name="FAHU (قسم الشفط)", conductor_name="مجرى شفط"),
    dict(id="cold", joint_end_only=False, name="المياه الباردة", icon="💧", color="#06b6d4",
         desc="خزان المياه المنزلي ← مواسير المياه الباردة والمحابس ← مداخل الأجهزة الصحية والسخانات",
         source=lambda e: e["c"] == "P.tank" and _t(e) == "tank_water" and _m(e) == "DT",
         edge=lambda e: e["c"] == "P.cold" and e["g"][0] == "t" and e["l"] in ("R", "G", "B") and ((e.get("a") or {}).get("dia_mm") or 0) >= 50 and not (e.get("a") or {}).get("connector"),
         edge_name="رئيسيات غرف المضخات (مضخات الرفع والتعزيز غير مرسومة)",
         variants=[("الشبكة", lambda e: e["c"] == "P.cold")],
         terminal=lambda e: fix_cold_inlet(e) or e["c"] == "P.heater", group=_grp,
         term_name=lambda e: "سخان" if e["c"] == "P.heater" else "مدخل جهاز صحي", source_name="خزان منزلي", conductor_name="ماسورة مياه باردة"),
    dict(id="hot", joint_end_only=False, name="المياه الساخنة", icon="♨", color="#DB7F4A",
         desc="السخانات ← مواسير المياه الساخنة ← الخلاطات والدشّات",
         source=lambda e: e["c"] == "P.heater",
         variants=[("الشبكة", lambda e: e["c"] == "P.hot")],
         terminal=fix_hot_inlet, group=_grp,
         term_name=lambda e: "خلاط / دش", source_name="سخان", conductor_name="ماسورة مياه ساخنة"),
    dict(id="drain", joint_end_only=False, name="الصرف", icon="⇩", color="#8a6d4b", sink=True,
         desc="المخرج ← مواسير الصرف والصاعدان ← المصائد ← مصارف الأجهزة (المسار عكس اتجاه الجريان)",
         source=lambda e: e["c"] == "P.drain" and _t(e) == "drain_outlet",
         edge=lambda e: e["c"] == "P.drain" and _t(e).startswith("pipe_") and e["l"] in ("B", "G") and not (e.get("a") or {}).get("connector"),
         edge_name="مواسير الصرف تحت الأرض (المخرج إلى المجمّع العام غير مرسوم)",
         variants=[("الشبكة", lambda e: e["c"] == "P.drain" and (_t(e).startswith("pipe_") or _t(e) in ("cleanout", "floor_trap", "stack")))],
         terminal=lambda e: fix_waste_outlet(e) or (e["c"] == "P.drain" and _t(e) == "floor_trap"), group=_grp,
         term_name=lambda e: "مصيدة أرضية" if _t(e) == "floor_trap" else "مصرف جهاز", source_name="مخرج الصرف", conductor_name="ماسورة صرف"),
]


# ------------------------------------------------------------------------------------------------ graph
class World:
    def __init__(self, els):
        self.els = els; self.P = {}; self.B = {}; self.C = {}
    def prim(self, i):
        p = self.P.get(i)
        if p is None:
            p = self.P[i] = prims(self.els[i]); self.B[i] = bound(p, TOL)
            mn, mx = bound(p); self.C[i] = tuple((mn[k] + mx[k]) / 2 for k in range(3))
        return p


def neighbours(world, idx, tol=TOL):
    """pairs of the given elements whose surface gap <= tol -> {i: {j: (gap, contact point)}}"""
    grid = collections.defaultdict(list)
    for i in idx:
        world.prim(i); mn, mx = world.B[i]
        for gx in range(int(mn[0] // CELL), int(mx[0] // CELL) + 1):
            for gy in range(int(mn[1] // CELL), int(mx[1] // CELL) + 1):
                grid[(gx, gy)].append(i)
    adj = collections.defaultdict(dict); seen = set()
    for lst in grid.values():
        for a in range(len(lst)):
            for b in range(a + 1, len(lst)):
                i, j = lst[a], lst[b]
                if i > j: i, j = j, i
                if (i, j) in seen: continue
                seen.add((i, j))
                A, B = world.B[i], world.B[j]
                if any(A[1][k] < B[0][k] or B[1][k] < A[0][k] for k in range(3)): continue
                d, x, y = gap(world.P[i], world.P[j])
                if d <= tol:
                    c = tuple((x[k] + y[k]) / 2 for k in range(3))
                    adj[i][j] = (d, c, x, y); adj[j][i] = (d, c, y, x)       # (gap, contact, point on this element, point on the other)
    return adj


def flood(world, src, kind, adj, pass_t=False):
    """Dijkstra from the sources over conductors; arrival distance (m) = centre → contact → centre along the way.  A terminal consumes: it never passes anything on —
    except in a daisy-chained electrical circuit, where a fixture / switch / socket is a junction of the wiring (pass_t)."""
    dist = {}; pq = []
    for i in src: dist[i] = 0.0; heapq.heappush(pq, (0.0, i))
    while pq:
        d, i = heapq.heappop(pq)
        if d > dist.get(i, 1e18) or (kind[i] == "t" and not pass_t): continue
        ci = world.C[i]
        for j, (g, c, _x, _y) in adj.get(i, {}).items():
            if kind[j] == "s" or kind[j] == "x": continue
            nd = d + math.dist(ci, c) + math.dist(c, world.C[j])
            if nd < dist.get(j, 1e18): dist[j] = nd; heapq.heappush(pq, (nd, j))
    return dist


def plan_dist_cm(e, conds):
    """diagnosis: plan distance (cm) from a terminal's anchor to the nearest conductor segment of the same level"""
    g = e["g"]
    if g[0] in ("b", "cyl"): a = (g[1], g[2])
    elif g[0] == "r": a = ((g[1] + g[3]) / 2, (g[2] + g[4]) / 2)
    elif g[0] in ("t", "d"): a = (g[1][0][0], g[1][0][1])
    elif g[0] == "p": a = (sum(p[0] for p in g[1]) / len(g[1]), sum(p[1] for p in g[1]) / len(g[1]))
    else: return None
    best = 1e9
    for ax, ay, bx, by in conds.get(e["l"], ()):
        dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((a[0] - ax) * dx + (a[1] - ay) * dy) / L2))
        d = math.hypot(a[0] - (ax + dx * t), a[1] - (ay + dy * t))
        if d < best: best = d
    return best


def analyse_system(M, sd, world):
    els = M["els"]
    src = [i for i, e in enumerate(els) if sd["source"](e)]
    edge = [i for i, e in enumerate(els) if sd.get("edge") and sd["edge"](e)]
    ter = [i for i, e in enumerate(els) if sd["terminal"](e)]
    grp = sd.get("group")
    units = collections.OrderedDict()
    for i in ter: units.setdefault(grp(els[i]) if grp else els[i]["id"], []).append(i)
    var = []
    allcon = set()
    for vname, vpred in sd["variants"]:
        con = [i for i, e in enumerate(els) if vpred(e)]
        kind = {}
        for i in con: kind[i] = "c"
        for i in ter: kind[i] = "t"
        for i in src: kind[i] = "s"
        for i in list(kind): world.prim(i)
        adj = neighbours(world, list(kind))
        pt = bool(sd.get("pass_terminal"))
        chain = flood(world, src, kind, adj, pt)                              # strict: only from the real sources
        dist = flood(world, src + [i for i in edge if i in kind and i not in src], kind, adj, pt)   # distribution: also from the boundary entries (what the model does not draw lies behind them)
        var.append(dict(name=vname, con=con, dist=dist, chain=chain, adj=adj, kind=kind))
        allcon.update(con)
    # a unit (terminal) is OK when it is reached through EVERY variant
    ok_units, bad_units, chain_units = [], [], []
    for k, v in units.items():
        if all(any(i in vr["dist"] for i in v) for vr in var): ok_units.append(k)
        else: bad_units.append(k)
        if all(any(i in vr["chain"] for i in v) for vr in var): chain_units.append(k)
    reached_any = {}
    for vr in var:
        for i, d in vr["dist"].items():
            if i not in reached_any or d < reached_any[i]: reached_any[i] = d
    orphans = [i for vr in var for i in vr["con"] if i not in vr["dist"]]
    edge_ok = [i for i in edge if any(i in vr["chain"] for vr in var)]
    return dict(src=src, edge=edge, edge_ok=edge_ok, ter=ter, units=units, ok=ok_units, bad=bad_units, chain=chain_units, var=var, reach=reached_any, orph=orphans, allcon=allcon)


def diagnose(M, sd, R):
    """why a terminal failed -> (island, near, far)
       island  it touches a conductor, but that network never reaches a source (a link between networks / to the source is missing)
       near    it touches nothing, but a conductor of its system is within NEAR_CM in plan (the last piece is missing)
       far     nothing of its system documented nearby"""
    els = M["els"]; conds = collections.defaultdict(list)
    for i in R["allcon"]:
        g = els[i]["g"]
        if g[0] in ("t", "d"):
            for a, b in zip(g[1], g[1][1:]): conds[els[i]["l"]].append((a[0], a[1], b[0], b[1]))
        else:
            for q in prims(els[i]):
                if q[0] == "box": conds[els[i]["l"]].append((q[1][0] * 100, q[1][1] * 100, q[1][0] * 100, q[1][1] * 100))
    island, near, far = [], [], []
    for k in R["bad"]:
        v = R["units"][k]
        touch = any(any(j in vr["kind"] and vr["kind"][j] == "c" for j in vr["adj"].get(i, {})) for vr in R["var"] for i in v)
        if touch: island.append(k); continue
        d = min((plan_dist_cm(els[i], conds) or 1e9) for i in v)
        (near if d <= NEAR_CM else far).append(k)
    return island, near, far


def islands(M, R):
    """networks (components of conductors) that no source reaches: [(size, {level: n})] largest first, and the sources that touch no conductor"""
    els = M["els"]; out = []
    for vr in R["var"]:
        un = [i for i in vr["con"] if i not in vr["dist"]]; seen = set(); unset = set(un)
        for i in un:
            if i in seen: continue
            st = [i]; seen.add(i); comp = [i]
            while st:
                x = st.pop()
                for y in vr["adj"].get(x, {}):
                    if y in unset and y not in seen: seen.add(y); st.append(y); comp.append(y)
            out.append((len(comp), dict(collections.Counter(els[j]["l"] for j in comp))))
    out.sort(key=lambda t: -t[0])
    lone = [i for i in R["src"] if not any(j in vr["kind"] and vr["kind"][j] == "c" for vr in R["var"] for j in vr["adj"].get(i, {}))]
    return out, lone


# ------------------------------------------------------------------------------------------------ tests + output
def levels_of(els, idxs): return collections.Counter(els[i]["l"] for i in idxs)


def tests_of(M, sd, R):
    els = M["els"]; T = []; sid = sd["id"]
    nsrc, nu = len(R["src"]), len(R["units"])
    tname = (sd["term_name"](els[R["ter"][0]]) + (" …" if len({sd["term_name"](els[i]) for i in R["ter"]}) > 1 else "")) if R["ter"] else "نهايات الاستهلاك"
    T.append(dict(id=sid + ".src", n="توجد عناصر مصدر في النموذج (" + sd["source_name"] + ")", ok=nsrc, of=max(nsrc, 1), pass_=nsrc > 0))
    T.append(dict(id=sid + ".dist", n="كل نهاية استهلاك موصولة بالشبكة الموزّعة من " + ("مصدرها أو من نقاط دخولها" if R["edge"] else "مصدرها") + " (" + tname + ")", ok=len(R["ok"]), of=max(nu, 1), pass_=nu > 0 and len(R["ok"]) == nu))
    T.append(dict(id=sid + ".cov", n="السلسلة كاملة: كل نهاية استهلاك موصولة بالمصدر نفسه (" + sd["source_name"] + ") عبر موصلات فعلية", ok=len(R["chain"]), of=max(nu, 1), pass_=nu > 0 and len(R["chain"]) == nu))
    if R["edge"]:
        T.append(dict(id=sid + ".edge", n="نقاط الدخول (" + sd.get("edge_name", "") + ") موصولة بالمصدر عبر هندسة فعلية", ok=len(R["edge_ok"]), of=len(R["edge"]), pass_=len(R["edge_ok"]) == len(R["edge"])))
    ncon = len(R["allcon"])
    T.append(dict(id=sid + ".orph", n="لا موصل يتيم: كل " + sd["conductor_name"] + " موصول بمصدر أو نقطة دخول", ok=ncon - len(R["orph"]), of=max(ncon, 1), pass_=ncon > 0 and not R["orph"]))
    lv_ok = collections.Counter(); lv_all = collections.Counter(); okset = set(R["ok"])
    for k, v in R["units"].items():
        l = els[v[0]]["l"]; lv_all[l] += 1
        if k in okset: lv_ok[l] += 1
    order = [l["id"] for l in M["levels"]]
    lv = [l for l in order if lv_all[l]]
    full = [l for l in lv if lv_ok[l] == lv_all[l]]
    T.append(dict(id=sid + ".lvl", n="كل طابق فيه نهايات استهلاك موصول كله بالشبكة", ok=len(full), of=max(len(lv), 1), pass_=bool(lv) and len(full) == len(lv), detail={l: [lv_ok[l], lv_all[l]] for l in lv}))
    return T


def run(M, verbose=False):
    world = World(M["els"]); out = []
    for sd in SYSTEMS:
        R = analyse_system(M, sd, world)
        isl, near, far = diagnose(M, sd, R) if R["bad"] else ([], [], [])
        R["isl"], R["near"], R["far"] = isl, near, far
        R["islands"], R["lone"] = islands(M, R)
        R["tests"] = tests_of(M, sd, R)
        out.append((sd, R))
        if verbose:
            print(f"{sd['id']:6s} sources {len(R['src']):3d} entries {len(R['edge']):3d} conductors {len(R['allcon']):5d} terminals {len(R['units']):5d} distribution {len(R['ok']):5d} chain {len(R['chain']):5d}  failed {len(R['bad']):4d} [island {len(isl)}, last piece missing {len(near)}, nothing nearby {len(far)}]  unreached networks {len(R['islands'])} (largest {[n for n, _ in R['islands'][:5]]})")
    return out


def pack(M, results):
    """compact JSON for the viewer: parallel arrays so 10k nodes stay ~100 kB"""
    S = []
    els = M["els"]
    for sd, R in results:
        reach = sorted(R["reach"].items(), key=lambda kv: kv[1])
        role = []
        srcs, eds, ters = set(R["src"]), set(R["edge"]), set(R["ter"])
        for i, d in reach:
            role.append("s" if i in srcs else "e" if i in eds else "t" if i in ters else "c")
        unreached_ter = [i for k in R["bad"] for i in R["units"][k]]
        S.append(dict(id=sd["id"], name=sd["name"], icon=sd["icon"], color=sd["color"], desc=sd["desc"],
                      cnt=dict(src=len(R["src"]), edge=len(R["edge"]), con=len(R["allcon"]), ter=len(R["units"]), ok=len(R["ok"]), chain=len(R["chain"]), orph=len(R["orph"]), isl=len(R["isl"]), near=len(R["near"]), far=len(R["far"]), lone=len(R["lone"])),
                      tests=[dict(id=t["id"], n=t["n"], ok=t["ok"], of=t["of"], p=1 if t["pass_"] else 0, **({"d": t["detail"]} if "detail" in t else {})) for t in R["tests"]],
                      src=R["src"], ri=[i for i, d in reach], rd=[int(round(d * 10)) for i, d in reach], rk="".join(role), x=unreached_ter, o=R["orph"]))
    return {"v": 1, "tol": TOL, "built": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "systems": S}


def apply(M, verbose=False):
    """called by post_model.py: analyse and store M['lifecycle'], write the report"""
    results = run(M, verbose)
    M["lifecycle"] = pack(M, results)
    write_doc(M, results)
    return results


def write_doc(M, results):
    els = M["els"]; P = []; w = P.append
    w("# اختبارات دورة الحياة للأنظمة (كهرباء · تكييف · مياه · صرف · إطفاء)"); w("")
    w("> يُنتَج آليًّا بـ `python3 pipeline/lifecycle.py` ويُحدَّث مع كل بناء للنموذج. **المبدأ:** يُشغَّل كل نظام من مصادره، ولا يُضاء إلا ما هو موصول بالمصدر عبر هندسة فعلية في النموذج "
      f"(موصلات أو مواسير أو مجاري أو محابس ومخمّدات تتلامس بفجوة سطحية ≤ {int(TOL * 100)} سم). لا يُفترض أي وصل: ما لا يتصل يبقى مظلمًا ويظهر فشلًا في الاختبار، وسببه يُشخَّص هنا.")
    w("")
    w("## الخلاصة"); w("")
    w("| النظام | المصادر | الموصلات | نهايات الاستهلاك | الموصول | الفاشل: قريب في المسقط (وصلة ناقصة) | الفاشل: لا شيء موثّق قربه | موصلات يتيمة | الاختبارات |")
    w("|---|---|---|---|---|---|---|---|---|")
    for sd, R in results:
        t = R["tests"]; np_ = sum(1 for x in t if x["pass_"])
        w(f"| {sd['icon']} {sd['name']} | {len(R['src'])} | {len(R['allcon'])} | {len(R['units'])} | {len(R['ok'])} | {len(R['near'])} | {len(R['far'])} | {len(R['orph'])} | {np_} / {len(t)} |")
    w("")
    for sd, R in results:
        w(f"## {sd['icon']} {sd['name']}"); w(""); w(sd["desc"]); w("")
        w("| الاختبار | النتيجة | العدد |"); w("|---|---|---|")
        for t in R["tests"]: w(f"| {t['n']} | {'✔ نجح' if t['pass_'] else '✖ فشل'} | {t['ok']} / {t['of']} |")
        w("")
        if R["bad"]:
            bt = collections.Counter(); bl = collections.Counter()
            for k in R["bad"]:
                e0 = els[R["units"][k][0]]; bt[sd["term_name"](e0)] += 1; bl[e0["l"]] += 1
            w("- **الفاشل حسب النوع:** " + "، ".join(f"{k} {v}" for k, v in bt.most_common()))
            w("- **الفاشل حسب الطابق:** " + "، ".join(f"{k} {v}" for k, v in sorted(bl.items())))
            w(f"- **التشخيص:** {len(R['near'])} منها يوجد موصل من نظامها على بعد ≤ {int(NEAR_CM)} سم في المسقط (الوصلة الأخيرة غير مرسومة في النموذج)، و{len(R['far'])} لا يوجد قربها شيء موثّق.")
            w("")
        if R["orph"]:
            ol = collections.Counter(els[i]["l"] for i in R["orph"]); w("- **الموصلات اليتيمة حسب الطابق:** " + "، ".join(f"{k} {v}" for k, v in sorted(ol.items()))); w("")
    os.makedirs(os.path.dirname(DOC), exist_ok=True)
    open(DOC, "w", encoding="utf-8").write("\n".join(P) + "\n")


def regress(results):
    """ratchet: a test may improve but never fall below the recorded floor"""
    if not os.path.exists(BASE): return []
    base = json.load(open(BASE, encoding="utf-8")); bad = []
    for sd, R in results:
        for t in R["tests"]:
            b = base.get(t["id"])
            if b is not None and t["ok"] < b: bad.append((t["id"], t["ok"], b))
    return bad


if __name__ == "__main__":
    M = json.load(open(SRC, encoding="utf-8"))
    results = run(M, verbose=True)
    write_doc(M, results)
    if "--baseline" in sys.argv:
        json.dump({t["id"]: t["ok"] for sd, R in results for t in R["tests"]}, open(BASE, "w", encoding="utf-8"), indent=1)
        print("baseline recorded")
    if "--save" in sys.argv:
        M["lifecycle"] = pack(M, results); json.dump(M, open(SRC, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False); print("saved M['lifecycle']")
    bad = regress(results)
    for b in bad: print("REGRESSION", b)
    sys.exit(1 if bad else 0)
