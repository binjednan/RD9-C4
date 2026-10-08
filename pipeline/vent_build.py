# -*- coding: utf-8 -*-
"""Ventilation system as model elements (data: pipeline/data/vent.json from pipeline/vent_extract.py; sheets MECH1 p23–27 + the riser diagram VE-105 p28).

  ducts       every drawn polyline of the extract (EA) and fresh-air (FA) layers -> one M.duct box per segment, sized from the nearest size label «250x150» (mm) of its family, at ONE elevation per level
              (the plans give plan positions and sizes, not the heights in the ceiling void: the elevation is the modeller's and the card says so)
  diffusers   the 25 x 25 cm crossed squares (toilet / kitchen extract) -> M.outlet 'diff_extract' flush with the ceiling plate under them, flow from the «EAD 15 L/S» label
  grilles     the «FA 30 L/S wire mesh» / «EA 50 L/S wire mesh» labels -> a wire-mesh grille on the nearest free duct end of their family
  dampers     the fire / volume-control damper symbols (M_VE_DAM) -> M.damper on the nearest duct, kind from the FD / VCD word beside it
  risers      the shaft boxes (EA at x 865 y 1038, FA at x 865 y 760) -> vertical duct boxes from floor to floor, SIZES FROM THE RISER DIAGRAM VE-105 (they shrink with the height: EA 25x15 → 95x50 cm), anchored at the
              face where the floor's branch ends so the network touches

Ids end with -VTnnnn (V is taken by the pipe risers), rebuilt on every run; post_model.py calls build() before the support analysis (rods / hangers are computed for these ducts like for the others).
Nothing is joined that the plans do not draw: a duct that stops short of the shaft face, a diffuser far from its duct stays dark in the life-cycle test (pipeline/lifecycle.py: «التهوية»)."""
import os, re, sys, json, math, collections
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
DATA = os.path.join(HERE, "data", "vent.json")
ID_RE = re.compile(r"-VT\d{4}$")
LEVELS = {"B": ["B"], "G": ["G"], "1": ["1"], "TY": ["2", "3", "4", "5"], "R": ["R"]}
ORDER = ["B", "G", "1", "2", "3", "4", "5", "R"]
BOTTOM = {"B": 2.85, "G": 3.65, "1": 2.52, "2": 2.52, "3": 2.52, "4": 2.52, "5": 2.52, "R": 1.00}      # m above the finished floor: underside of the ducts (above the ceiling plate by 12 cm in the flats)
SIZE_RE = re.compile(r"^(\d{2,4})[xX](\d{2,4})$")
SIZE_DEFAULT = (200, 150)
LABEL_R = 70.0               # cm  a size label this close to a duct segment (across) belongs to it
DAMPER_R = 28.0              # cm  a damper symbol this close to a duct segment sits on it
SRC_TEXT = "مخططات التهوية MECH1 ص23–27 (VE-100…VE-104): مجاري الشفط والهواء النقي والناشرات والمخمّدات؛ ومخطط الصاعد VE-105 (ص28) لمقاسات الصواعد؛ ارتفاع المجاري في فراغ السقف افتراض (pipeline/vent_build.py)"
SRC_RISER = "مخطط صاعد التهوية VE-105 (MECH1 ص28): مقاس مقطع الصاعد بين كل طابقين؛ موضع الصاعد من مربع الشفت في مسقط التهوية"

# riser sections from VE-105: (lower level, upper level) -> (width, depth) in cm.  EA flows UP (the label at floor k is the size after joining floor k's branch: it is the section above floor k);
# FA flows DOWN (the label at floor k is the size ARRIVING at floor k from above: it is the section above floor k as well).
EA_SECTIONS = {"G": (25, 15), "1": (50, 25), "2": (50, 40), "3": (75, 40), "4": (90, 45), "5": (95, 50), "R": (95, 50)}
FA_SECTIONS = {"B": (20, 15), "G": (25, 15), "1": (50, 30), "2": (60, 40), "3": (75, 40), "4": (95, 50), "5": (95, 50), "R": (95, 57)}
# the plan face at which the branch of each floor ends (the extract / fresh-air shaft boxes of the plans): level -> (x_edge, y_centre)
EDGE = {"ea": {"1": (895.2, 1027.3), "_": (912.4, 1037.8)}, "fa": {"1": (895.2, 770.0), "_": (912.1, 760.3)}}

MATS = {"m_duct_ea": {"name": "مجرى شفط (Extract air)", "color": "#c9955b", "code": "VE"}, "m_duct_fa": {"name": "مجرى هواء نقي (Fresh air)", "color": "#7fb69a", "code": "VE"},
        "m_diff_ea": {"name": "ناشر شفط سقفي", "color": "#e4e2da", "code": "VE"}, "m_grille_fa": {"name": "شبكة سلكية (wire mesh)", "color": "#9fb0bf", "code": "VE"},
        "m_damper_ve": {"name": "مخمّد (FD / VCD)", "color": "#b2554a", "code": "VE"}}
TYPES = {
    "duct_ea": {"n": "مجرى شفط هواء (حمامات / مطابخ)", "cf": "doc", "sp": [["المصدر", "طبقة M_T.EX_DIFF / M_T.EX_DUCT في مخطط التهوية"], ["المقاس", "وسم المقاس على المخطط (مم)"], ["الارتفاع", "في فراغ السقف (افتراض)"]], "sr": []},
    "duct_fa": {"n": "مجرى هواء نقي", "cf": "doc", "sp": [["المصدر", "طبقة M_FA_DUCT في مخطط التهوية"], ["المقاس", "وسم المقاس على المخطط (مم)"], ["الارتفاع", "في فراغ السقف (افتراض)"]], "sr": []},
    "riser_ea": {"n": "صاعد شفط الهواء (قطاع بين طابقين)", "cf": "derived", "sp": [["الموضع", "مربع الشفت في مسقط التهوية"], ["المقاس", "مخطط الصاعد VE-105"]], "sr": []},
    "riser_fa": {"n": "صاعد الهواء النقي (قطاع بين طابقين)", "cf": "derived", "sp": [["الموضع", "مربع الشفت في مسقط التهوية"], ["المقاس", "مخطط الصاعد VE-105"]], "sr": []},
    "diff_extract": {"n": "ناشر شفط سقفي (EAD)", "cf": "doc", "sp": [["الرمز", "مربع 25×25 سم بقطرين في طبقة M_T.EX_DIFF / M_RAD_DIFF"], ["الرقبة", "150×150 مم (وسم «EAD … 150x150 mm»)"]], "sr": []},
    "grille_ea": {"n": "شبكة سلكية لمجرى الشفط (wire mesh)", "cf": "doc", "sp": [["الوسم", "«EA 50 L/S wire mesh»"]], "sr": []},
    "grille_fa": {"n": "شبكة سلكية لمجرى الهواء النقي (wire mesh)", "cf": "doc", "sp": [["الوسم", "«FA 30 L/S wire mesh»"]], "sr": []},
    "damper_ea": {"n": "مخمّد في مجرى الشفط (FD / VCD)", "cf": "doc", "sp": [["الرمز", "طبقة M_VE_DAM"]], "sr": []},
    "damper_fa": {"n": "مخمّد في مجرى الهواء النقي (FD / VCD)", "cf": "doc", "sp": [["الرمز", "طبقة M_VE_DAM"]], "sr": []},
    "fan_window": {"n": "مروحة شفط نافذية (Window type)", "cf": "doc", "sp": [["المصدر", "رمز دائري 40 سم في طبقة M_HVAC_EQP ووسم «WINDOW TYPE Ex. FAN-0n»"], ["التدفق", "من الوسم (L/S)"]], "sr": []},
    "fan_prop": {"n": "مروحة شفط مروحية مقاومة للانفجار", "cf": "doc", "sp": [["المصدر", "رمز دائري 40 سم ووسم «EXPLOSION PROOF PROPELLER FAN Ex. FAN-0n»"], ["التدفق", "من الوسم (L/S)"]], "sr": []},
    "fan_axial": {"n": "مروحة محورية داخل المجرى (مقاومة للحريق)", "cf": "doc", "sp": [["المصدر", "رمز الصندوق ذي المروحة في طبقة AV-MAC ووسم «AXIAL TYPE (FIRE RATED AT 400 °C FOR 2 Hrs)»"]], "sr": []},
    "louver_intake": {"n": "ردّاد سحب الهواء النقي للوحدة FAHU", "cf": "doc", "sp": [["المصدر", "وسم مخطط السطح VE-104: «FRESH AIR INTAKE SAND TRAP LOUVER … 1750 mm x 950 mm»"]], "sr": []},
    "duct_flex_ea": {"n": "وصلة مرنة بين مجرى الشفط والناشر (مشتقة)", "cf": "derived", "sp": [["الأصل", "وصلة مشتقة من المسقط (pipeline/connectors.py)"]], "sr": []},
    "duct_flex_fa": {"n": "وصلة مرنة بين مجرى الهواء النقي والشبكة (مشتقة)", "cf": "derived", "sp": [["الأصل", "وصلة مشتقة من المسقط (pipeline/connectors.py)"]], "sr": []},
}


def normalise(pls):
    """the plans draw some ducts as hooked paths that run back over themselves (a stub toward a break symbol + the branch beyond it): noding the family's linework (unary_union) dissolves the overlaps and splits
    it where lines meet, so every free end is a real end of a duct"""
    lines = [LineString(pl) for pl in pls if len(pl) >= 2]
    if not lines: return []
    u = unary_union(lines)
    out = []
    for g in ([u] if u.geom_type == "LineString" else list(getattr(u, "geoms", []))):
        if g.geom_type == "LineString" and g.length >= 3.0: out.append([[round(x, 1), round(y, 1)] for x, y in g.coords])
    return out


BRIDGE_MAX = 60.0            # cm  the plans break a duct (a gap with a squiggle) where it passes under / over another duct: the duct continues on the other side of the gap


DAMPER_GAP_MAX = 95.0        # cm  a damper symbol hides the duct under it: the gap around a damper can be wider than a break symbol's


def bridges(pls, dampers=()):
    """pairs of free ends of different polylines of one family that face each other along one line within BRIDGE_MAX (or DAMPER_GAP_MAX when a damper symbol sits in the gap) -> [[p, q]]
    (the drawn break symbol / the damper is a gap in the line, not the end of the duct)"""
    ends = []
    for i, pl in enumerate(pls):
        for k, (p, q) in ((0, (pl[0], pl[1])), (1, (pl[-1], pl[-2]))):
            d = math.hypot(p[0] - q[0], p[1] - q[1])
            if d > 0: ends.append((i, p, ((p[0] - q[0]) / d, (p[1] - q[1]) / d)))          # outward direction
    out = []; used = set()
    for a in range(len(ends)):
        for b in range(a + 1, len(ends)):
            i, p, u = ends[a]; j, q, v = ends[b]
            if i == j or a in used or b in used: continue
            d = math.hypot(q[0] - p[0], q[1] - p[1])
            if not (4.0 < d <= DAMPER_GAP_MAX): continue
            if d > BRIDGE_MAX:
                mx, my = (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
                if not any(math.hypot(m["x"] - mx, m["y"] - my) <= 0.5 * d for m in dampers): continue          # a wide gap only where a damper symbol covers it
            w = ((q[0] - p[0]) / d, (q[1] - p[1]) / d)
            if u[0] * w[0] + u[1] * w[1] > 0.97 and -(v[0] * w[0] + v[1] * w[1]) > 0.97:
                used.add(a); used.add(b); out.append([[p[0], p[1]], [q[0], q[1]]])
    return out


def ray_bridges(pls, others, dampers=()):
    """a free end of a duct whose line, continued, reaches another duct of the SAME family across a duct of the OTHER family (the plans leave the crossing out: under / over it the duct goes on) or across a damper
    symbol, within DAMPER_GAP_MAX -> [[end, point on the duct it joins]]"""
    if not pls: return []
    lines = [LineString(pl) for pl in pls]; allu = unary_union(lines)
    oth = unary_union([LineString(pl) for pl in others]) if others else None
    out = []
    for i, pl in enumerate(pls):
        for k, (p, q) in ((0, (pl[0], pl[1])), (1, (pl[-1], pl[-2]))):
            P = Point(p)
            if any(j != i and lines[j].distance(P) < 4.0 for j in range(len(lines))): continue         # not a free end
            d = math.hypot(p[0] - q[0], p[1] - q[1])
            if d == 0: continue
            u = ((p[0] - q[0]) / d, (p[1] - q[1]) / d)
            ray = LineString([p, (p[0] + u[0] * DAMPER_GAP_MAX, p[1] + u[1] * DAMPER_GAP_MAX)])
            hit = ray.intersection(unary_union([lines[j] for j in range(len(lines)) if j != i]))
            pts = [hit] if hit.geom_type == "Point" else [g for g in getattr(hit, "geoms", []) if g.geom_type == "Point"]
            if not pts: continue
            h = min(pts, key=lambda g: g.distance(P)); dd = h.distance(P)
            if dd <= 4.0: continue
            seg = LineString([p, (h.x, h.y)])
            ok = dd <= BRIDGE_MAX or (oth is not None and seg.intersects(oth)) or any(math.hypot(m["x"] - (p[0] + h.x) / 2, m["y"] - (p[1] + h.y) / 2) <= 0.5 * dd + 5 for m in dampers)
            if ok: out.append([[p[0], p[1]], [round(h.x, 1), round(h.y, 1)]])
    return out


def _seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L2))
    q = (a[0] + dx * t, a[1] + dy * t); return math.hypot(p[0] - q[0], p[1] - q[1]), t


def build(M, els, verbose=False):
    els[:] = [e for e in els if not ID_RE.search(e["id"])]
    if not os.path.exists(DATA): return {}
    D = json.load(open(DATA, encoding="utf-8"))
    sp = M["sp"]
    for t in (SRC_TEXT, SRC_RISER):
        if t not in sp: sp.append(t)
    s_main, s_riser = sp.index(SRC_TEXT), sp.index(SRC_RISER)
    for k, v in MATS.items(): M["mats"].setdefault(k, v)
    for k, v in TYPES.items(): M.setdefault("types", {})[k] = v
    ffl = {l["id"]: l["ffl"] for l in M["levels"]}
    new = []; counter = collections.Counter(); stats = collections.Counter()

    def add(cat, lv, g, typ, mat, mark=None, a=None, u=None, s=None):
        counter[(cat, lv)] += 1
        e = {"id": f"{cat}-{lv}-VT{sum(counter.values()):04d}", "c": cat, "l": lv, "g": g, "mark": mark, "t": typ, "m": mat, "a": a or {}, "s": [s if s is not None else s_main]}
        if u: e["u"] = u
        new.append(e); return e

    def unit_at(lv, x, y):
        for u in M.get("units", []):
            if u["level"] != lv: continue
            for r in u["rects"]:
                if r[0] <= x <= r[2] and r[1] <= y <= r[3]: return u["id"]
        return None

    # ceiling plates per level (the diffusers sit flush under them)
    plates = {}
    for lv in ORDER:
        P = []
        for e in els:
            if e["c"] == "A.ceil" and e["l"] == lv and e["g"][0] == "p":
                try: pg = Polygon(e["g"][1]).buffer(0)
                except Exception: continue
                if not pg.is_empty: P.append((pg, e["g"][2]))
        plates[lv] = (STRtree([p for p, _ in P]), P) if P else None

    def ceil_z(lv, x, y, default):
        pl = plates.get(lv)
        if pl is None: return default
        tree, P = pl
        for i in tree.query(Point(x, y)):
            if P[int(i)][0].contains(Point(x, y)): return P[int(i)][1]
        return default

    for key, levels in LEVELS.items():
        S = D.get(key)
        if not S: continue
        words = S["words"]
        sizes = [w for w in words if SIZE_RE.match(w["t"])]
        for w in sizes: m = SIZE_RE.match(w["t"]); w["wd"], w["ht"] = int(m.group(1)), int(m.group(2))
        # flows: a number right before an «L/S» on the same line
        flows = []
        for w in words:
            if w["t"].upper() == "L/S":
                cand = [n for n in words if re.match(r"^\d{1,4}$", n["t"]) and abs(n["y"] - w["y"]) < 6 and 0 < w["x"] - n["x"] < 45]
                if cand: n = min(cand, key=lambda n: w["x"] - n["x"]); flows.append({"ls": int(n["t"]), "x": n["x"], "y": n["y"]})
        kinds = [w for w in words if w["t"] in ("FD", "VCD") and w["layer"] in ("M_HVAC_DAM", "M_VE_DAM")]
        # ---- duct segments of both families
        fam = {"ea": normalise(S["ea"]), "fa": normalise(S["fa"])}
        n_orig = {f: len(v) for f, v in fam.items()}
        for f in fam:
            other = fam["fa" if f == "ea" else "ea"]
            for br in bridges(fam[f], S["dampers"]): fam[f].append(br)                  # the break symbols and the dampers
            for br in ray_bridges(fam[f][:n_orig[f]], other, S["dampers"]): fam[f].append(br)   # a duct that goes on under / over a crossing duct to reach its main
        seg_all = []                                                                   # (family, a, b, polyline index, segment index)
        for f, pls in fam.items():
            for pi, pl in enumerate(pls):
                for si, (a, b) in enumerate(zip(pl, pl[1:])):
                    if math.hypot(a[0] - b[0], a[1] - b[1]) >= 6.0: seg_all.append((f, a, b, pi, si))
        def size_of(f, a, b, prev):
            best = None
            for w in sizes:
                d, t = _seg_dist((w["x"], w["y"]), a, b)
                if d > LABEL_R: continue
                lay = w["layer"]; ok = (f == "fa" and lay == "M_FA_TEXT") or (f == "ea" and lay in ("M_T.EX_TEXT", "M_K.EX_TEXT"))
                sc = d + (0 if ok else 40)
                if best is None or sc < best[0]: best = (sc, w)
            return (best[1]["wd"], best[1]["ht"], True) if best else (prev[0], prev[1], False) if prev else (SIZE_DEFAULT[0], SIZE_DEFAULT[1], False)
        made = {}                                                                      # (family, pi, si) -> (element, size)
        for lv in levels:
            f0 = ffl[lv]; zb = f0 + BOTTOM[lv]
            made.clear(); prev_of = {}
            for f, a, b, pi, si in seg_all:
                wd, ht, labelled = size_of(f, a, b, prev_of.get((f, pi)))
                prev_of[(f, pi)] = (wd, ht)
                w_cm, h_cm = wd / 10.0, ht / 10.0; zc = zb + h_cm / 200.0
                mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                e = add("M.duct", lv, ["d", [[a[0], a[1], round(zc, 3)], [b[0], b[1], round(zc, 3)]], w_cm, h_cm], "duct_" + f, "m_duct_" + f, u=unit_at(lv, *mid),
                        a={"sys": f, "w_cm": w_cm, "h_cm": h_cm, "size_note": "من وسم المخطط" if labelled else "مقاس افتراضي (لا وسم قريب) — بانتظار تأكيدك", "kind": "مجرى شفط" if f == "ea" else "مجرى هواء نقي",
                           "assumed": f"ارتفاع المجرى افتراض: الجنب السفلي {BOTTOM[lv]:.2f} م فوق الأرضية (فراغ السقف)"})
                if pi >= n_orig[f]: e["a"]["bridge"] = "فجوة رمز القطع في المخطط (المجرى يمر تحت/فوق مجرى آخر ويكمل بعدها)"; stats["bridges"] += 1
                made[(f, pi, si)] = (e, (a, b, zc, w_cm, h_cm)); stats["ducts"] += 1
            # ---- wire-mesh grilles: the symbol (a 40 cm bar across the duct end) at its drawn place, flow from the label beside it
            for q in S.get("grille_syms", []):
                f = "ea" if q["layer"] in ("M_T.EX_DIFF", "M_T.EX_DUCT") else "fa"
                ls = None; fl = [(math.hypot(fx["x"] - q["x"], fx["y"] - q["y"]), fx["ls"]) for fx in flows if math.hypot(fx["x"] - q["x"], fx["y"] - q["y"]) <= 170]
                if fl: ls = min(fl)[1]
                best = None
                for (f2, pi, si), (el, (a_, b_, zc_, w_cm, h_cm)) in made.items():
                    if f2 != f: continue
                    d, t = _seg_dist((q["x"], q["y"]), a_, b_)
                    if d <= 30 and (best is None or d < best[0]): best = (d, zc_, w_cm, h_cm)
                zc_, w_cm, h_cm = (best[1], best[2], best[3]) if best else (zb + 0.075, 25.0, 15.0)
                ang = math.degrees(math.atan2(q["dy"], q["dx"]))
                add("M.outlet", lv, ["b", q["x"], q["y"], 40.0, 4.0, round(ang, 1), round(zc_ - h_cm / 200 - 0.04, 3), round(zc_ + h_cm / 200 + 0.04, 3)], "grille_" + f, "m_grille_fa",
                    u=unit_at(lv, q["x"], q["y"]), a={"sys": f, "flow_ls": ls, "kind": "شبكة سلكية (wire mesh) عبر نهاية المجرى", "label": (f"{f.upper()} {ls} L/S wire mesh" if ls else None), "bar_cm": 40})
                stats["grilles"] += 1
            # ---- diffusers
            fl_used = set()
            for q in S["diffusers"]:
                z1 = ceil_z(lv, q["x"], q["y"], f0 + 2.40)
                near = [(math.hypot(fl["x"] - q["x"], fl["y"] - q["y"]), i) for i, fl in enumerate(flows) if i not in fl_used and 5 <= math.hypot(fl["x"] - q["x"], fl["y"] - q["y"]) <= 160]
                ls = None
                if near: dmin, i = min(near); ls = flows[i]["ls"]
                add("M.outlet", lv, ["b", q["x"], q["y"], q["w"], q["h"], 0, round(z1 - 0.04, 3), round(z1, 3)], "diff_extract", "m_diff_ea", u=unit_at(lv, q["x"], q["y"]),
                    a={"sys": "ea", "flow_ls": ls, "neck_mm": "150x150", "kind": "ناشر شفط مطبخ" if q.get("kind") == "kitchen" else "ناشر شفط حمام / دورة مياه", "size_cm": f"{round(q['w'])}×{round(q['h'])}"})
                stats["diffusers"] += 1
            # ---- dampers
            for q in S["dampers"]:
                best = None
                for (f, pi, si), (el, (a_, b_, zc, w_cm, h_cm)) in made.items():
                    d, t = _seg_dist((q["x"], q["y"]), a_, b_)
                    if d <= DAMPER_R and (best is None or d < best[0]): best = (d, f, a_, b_, zc, w_cm, h_cm)
                if best is None: stats["damper_no_duct"] += 1; continue
                d, f, a_, b_, zc, w_cm, h_cm = best
                kw = [k for k in kinds if math.hypot(k["x"] - q["x"], k["y"] - q["y"]) <= 40]
                kind = min(kw, key=lambda k: math.hypot(k["x"] - q["x"], k["y"] - q["y"]))["t"] if kw else "VCD"
                ang = math.degrees(math.atan2(b_[1] - a_[1], b_[0] - a_[0]))
                add("M.damper", lv, ["b", q["x"], q["y"], 12.0, round(w_cm + 8, 1), round(ang, 1), round(zc - h_cm / 200 - 0.04, 3), round(zc + h_cm / 200 + 0.04, 3)], "damper_" + f, "m_damper_ve", mark=kind,
                    u=unit_at(lv, q["x"], q["y"]), a={"sys": f, "damper": kind, "kind": "مخمّد حريق FD" if kind == "FD" else "مخمّد ضبط تدفق VCD"})
                stats["dampers"] += 1
    # ---- extract fans of the ground floor (symbols on M_HVAC_EQP / AV-MAC, labels «WINDOW TYPE Ex. FAN-01 70 L/S») and the fresh-air intake louver of the FAHU
    G = D.get("G") or {}
    walls = []
    for e in els:
        if e["l"] == "G" and e["c"] in ("A.wall", "S.wall") and e["g"][0] == "b": walls.append(e)
    def wall_dir(x, y):
        best = (120.0, None)
        for w in walls:
            cx, cy, wd, dp, rot = w["g"][1:6]
            th = math.radians(rot); c_, s_ = math.cos(th), math.sin(th); dx, dy = x - cx, y - cy
            u, v = dx * c_ + dy * s_, -dx * s_ + dy * c_
            d = math.hypot(max(abs(u) - wd / 2, 0), max(abs(v) - dp / 2, 0))
            if d < best[0]: best = (d, rot if wd >= dp else rot + 90)
        return best[1] or 0.0
    gwords = G.get("words", [])
    glabels = [w for w in gwords if re.match(r"^FAN-\d\d$", w["t"])]
    gflows = []
    for w in gwords:
        if w["t"].upper() == "L/S":
            cand = [n for n in gwords if re.match(r"^\d{1,4}$", n["t"]) and abs(n["y"] - w["y"]) < 6 and 0 < w["x"] - n["x"] < 45]
            if cand: n = min(cand, key=lambda n: w["x"] - n["x"]); gflows.append((n["x"], n["y"], int(n["t"])))
    for q in G.get("fans", []):
        lbl = [(math.hypot(w["x"] - q["x"], w["y"] - q["y"]), w["t"]) for w in glabels if math.hypot(w["x"] - q["x"], w["y"] - q["y"]) <= 260]
        name = min(lbl)[1] if lbl else None
        near = [w["t"].upper() for w in gwords if math.hypot(w["x"] - q["x"], w["y"] - q["y"]) <= 260]
        fl = [(math.hypot(x - q["x"], y - q["y"]), v) for x, y, v in gflows if math.hypot(x - q["x"], y - q["y"]) <= 280]
        ls = min(fl)[1] if fl else None
        f0 = ffl["G"]
        if q["kind"] == "box":
            kind, typ = "مروحة محورية داخل المجرى (مقاومة للحريق 400 °C لمدة ساعتين) — الرقم FAN-04 استُنتج لأنه الوحيد الناقص بين FAN-01…FAN-06", "fan_axial"; name = name or "FAN-04"
            e = add("M.fan", "G", ["b", q["x"], q["y"], q["w"], q["h"], 0, round(f0 + 3.62, 3), round(f0 + 3.62 + 0.50, 3)], typ, "m_fan", mark=name, a={"flow_ls": ls, "kind": kind, "assumed": "الارتفاع افتراض: على محور مجرى الشفط"}, u=None)
        else:
            is_prop = any("PROPELLER" in t or "EXPLOSION" in t for t in near)
            typ = "fan_prop" if is_prop else "fan_window"; kind = "مروحة شفط مروحية مقاومة للانفجار" if is_prop else "مروحة شفط نافذية (Window type)"
            rot = wall_dir(q["x"], q["y"])
            add("M.fan", "G", ["b", q["x"], q["y"], 40.0, 16.0, round(rot, 1), round(f0 + 2.05, 3), round(f0 + 2.45, 3)], typ, "m_fan", mark=name, a={"flow_ls": ls, "kind": kind, "assumed": "الارتفاع 2.05–2.45 م فوق الأرضية افتراض (ركب النافذة)؛ الاتجاه موازٍ لأقرب جدار"})
        stats["fans"] += 1
    R = D.get("R") or {}
    fahu = [e for e in els if e.get("t") == "fahu"]
    if fahu and R:
        g = fahu[0]["g"]                                                     # the louver sits on the intake (west) face of the unit: 1750 x 950 mm per the label of the roof plan
        y0, y1 = g[2], g[4]; cy = (y0 + y1) / 2
        add("M.outlet", "R", ["b", round(g[1] - 8, 1), round(cy, 1), 175.0, 16.0, 90, round(ffl["R"] + 0.45, 3), round(ffl["R"] + 0.45 + 0.95, 3)], "louver_intake", "m_grille_fa",
            a={"sys": "fa", "flow_ls": 3820, "kind": "ردّاد (لوفر) سحب الهواء النقي مع مصيدة رمل وNRD وشبكة حشرات — 1750×950 مم، سرعة الوجه 2.5 م/ث", "label": "FRESH AIR INTAKE SAND TRAP LOUVER 3820 L/S",
               "assumed": "الموضع على الوجه الغربي للوحدة FAHU والارتفاع افتراض؛ الرسم يذكر الأبعاد والتدفق فقط"})
        stats["louvers"] += 1
    slab = {}
    for e in els:
        if e["c"] == "S.slab" and e["g"][0] == "p": z0, z1 = slab.get(e["l"], (1e9, -1e9)); slab[e["l"]] = (min(z0, e["g"][2]), max(z1, e["g"][3]))
    def slab_bot(lv): return slab[lv][0] if lv in slab and lv not in ("B", "G") else ffl[lv] - (0.10 if lv != "B" else 0.0)
    # the face at which the branch of each floor ends = the east edge of the shaft box drawn on THAT floor's plan (the primary shafts stand at x ~ 865: EA y ~ 1038, FA y ~ 760)
    std = {"ea": (864.9, 1037.8), "fa": (864.6, 760.3)}; edge = {"ea": {}, "fa": {}}
    for key, lvs in LEVELS.items():
        for q in (D.get(key) or {}).get("shafts", []):
            sx, sy = std[q["kind"]]
            if abs(q["x"] - sx) < 130 and abs(q["y"] - sy) < 60:
                for lv in lvs: edge[q["kind"]][lv] = (q["x1"], q["y"])
    # ---- risers (floor to floor, sizes from VE-105)
    for fam_, SEC in (("ea", EA_SECTIONS), ("fa", FA_SECTIONS)):
        for lv, (w_cm, d_cm) in SEC.items():
            i = ORDER.index(lv); top_lv = ORDER[i + 1] if i + 1 < len(ORDER) else None
            z0 = slab_bot(lv); z1 = slab_bot(top_lv) if top_lv else ffl[lv] + 1.6               # from the underside of its own slab to the underside of the next one: the pieces meet and pass through the slabs
            xe, yc = edge[fam_].get(lv) or EDGE[fam_]["_"]
            cx = xe - w_cm / 2.0
            add("M.duct", lv, ["b", round(cx, 1), round(yc, 1), w_cm, d_cm, 0, round(z0, 3), round(z1, 3)], "riser_" + fam_, "m_duct_" + fam_, s=s_riser,
                a={"sys": fam_, "w_cm": w_cm, "h_cm": d_cm, "shaft": True, "kind": ("صاعد شفط" if fam_ == "ea" else "صاعد هواء نقي") + f" من {lv} إلى {top_lv or 'فوق السطح'}",
                   "size_note": "مقاس القطاع من مخطط الصاعد VE-105", "assumed": "وجه التوصيل عند حافة مربع الشفت في مسقط كل طابق؛ ارتفاع القطاع بين منسوبَي الأرضيتين"})
            stats["riser_sections"] += 1
    # the basement branch of the fresh air: a second, small FA shaft (150 x 200 mm box at x 1100, y 1140 on the B and G plans) carries the duct of the ground floor down to the basement duct
    for q in (D.get("B") or {}).get("shafts", []):
        if q["kind"] != "fa" or math.hypot(q["x"] - 1100, q["y"] - 1140) > 80: continue
        z1 = ffl["G"] + BOTTOM["G"] + 0.20
        add("M.duct", "B", ["b", q["x"], q["y"], round(q["w"]), round(q["h"]), 0, round(ffl["B"], 3), round(z1, 3)], "riser_fa", "m_duct_fa", s=s_riser,
            a={"sys": "fa", "w_cm": q["w"], "h_cm": q["h"], "shaft": True, "kind": "صاعد هواء نقي فرعي (200×150 مم) من الدور الأرضي إلى البدروم", "size_note": "مقاس الصندوق من مسقط البدروم ومخطط الصاعد VE-105 (B: 200x150)",
               "assumed": "ارتفاع القمة عند مجرى الدور الأرضي المفترض"})
        stats["riser_sections"] += 1
    els.extend(new)
    if verbose: print("ventilation:", len(new), dict(stats))
    return dict(stats)


if __name__ == "__main__":
    SRC = os.path.join(os.path.dirname(HERE), "src", "model.json")
    M = json.load(open(SRC, encoding="utf-8")); n0 = len(M["els"]); build(M, M["els"], verbose=True); print("elements", n0, "->", len(M["els"]))
