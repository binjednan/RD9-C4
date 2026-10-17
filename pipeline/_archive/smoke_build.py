# -*- coding: utf-8 -*-
"""Build drawn smoke-management routes from the MECH1 plan extraction.
Car-park duct paths are split at drawn branches and sized from nearby labels.
Shafts, dampers, fans, grilles and corridor branches follow their plan symbols.
Floor elevations without section geometry are recorded as assumptions.
The five corridor levels share the typical-floor plan and one vertical shaft axis.
Roof ducts follow the drawn vertices to the two fan and louver symbols.
Every generated element has a stable SM suffix and its source/system metadata.
The caller rebuilds these elements before support, connector and lifecycle checks.
"""
import os, re, sys, json, math, collections
from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
DATA = os.path.join(HERE, "data", "smoke.json")
ID_RE = re.compile(r"-SM\d{4}$")
ORDER = ["B", "G", "1", "2", "3", "4", "5", "R"]
FLOORS = ["1", "2", "3", "4", "5"]

Z_SOFFIT_GAP = 0.05          # m   the top of the car-park ducts sits this far under the underside of the ground-floor slab (slab["G"][0] = -0.45 -> top at -0.50)
BOTTOM_COR = 2.52            # m   above the floor: underside of the corridor extract ducts (the same as the ventilation ducts of floors 1–5 in vent_build.py)
Z_FAG = (2.05, 2.25)         # m   above the floor: the SMS FAG box on the shaft wall, its branch and its MFD
ROOF_BOTTOM = 0.60           # m   above the roof floor: underside of the roof smoke ducts (on stands)
FAN_ROOF_H = 1.20            # m   height of a roof fan casing, from the roof floor
LOUVER_ROOF = (0.0, 1.20)    # m   above the roof floor: louver of a roof fan (stands on the roof floor)
LOUVER_HEAD_H = 1.50         # m   height of the louver head on a car-park shaft (the SM-101 text says L X H 2 M X 1.5 M)
FAN_LEN_CP = 80.0            # cm  assumed length of a car-park fan casing along its duct
GRILLE_LEN = {"fa": 150.0, "ea": 170.0}   # cm  FAG 1500x200 mm / EAG 1700x200 mm (SM-100 text); the drawn bar is 80 cm (schematic)
GRILLE_H = 20.0              # cm
STUB_W, STUB_H = 30.0, 20.0  # cm  the 300x200 mm branch of every car-park grille
DAMPER_ALONG, DAMPER_PAD = 12.0, 8.0   # cm  a damper box: 12 along the duct, duct width + 8 across; its z span is the duct's +/- 0.04 m
VCD_R, CLUSTER_R = 30.0, 20.0           # cm  a VCD symbol / grille cluster belongs to the stub whose grille end is this close
RISER = {"fa": (25.0, 40.0), "ea": (20.0, 30.0)}   # cm plan x, y of the corridor risers (labels 400x250 / 300x200 and the drawn boxes)
RISER_CENTRE = {"fa": (1327.5, 1044.9), "ea": (1355.0, 1039.9)}   # ground schematic reference only; each plan keeps its own drawn centre
COR_FA_BRANCH = (25.0, 20.0)  # cm  w, h of the stub between the FA riser and its SMS FAG (the drawn 25 x 20 box)
COR_EA_BRANCH = (30.0, 20.0)  # cm  300x200
COR_EA_MAIN = (25.0, 15.0)    # cm  250x150
FAG_COR = (40.0, 4.0, 20.0)   # cm  SMS FAG 400x200 mm: width along x, depth, height
EAD = 25.0                    # cm  SMS EAD 225x225 mm: the drawn 25 x 25 plate
ROOF_DUCT = {"fa": (40.0, 25.0), "ea": (30.0, 20.0)}   # cm  400x250 / 300x200

# --- car-park duct topology (goes into pipeline/smoke_build.py) -------------------------------------------------------------------------------------------------------------------------
import re, math

SIZE_RE = re.compile(r"^(\d{2,4})x(\d{2,4})$")
STUB_STD = (300, 200)             # mm  the branch stub of every grille («300x200» on the make-up side; the extract stubs carry no label and are taken equal)
STUB_MAX = 60.0                   # cm  an arm's last segment (or a free 2-vertex polyline) up to this long is a grille stub
LABEL_R = 60.0                    # cm  a size label this close to an arm belongs to it
CONN_R = 250.0                    # cm  a size label this close to the connection piece (shaft -> junction) may size it


def dist(p, q): return math.hypot(p[0] - q[0], p[1] - q[1])
def plen(pl): return sum(dist(a, b) for a, b in zip(pl, pl[1:]))


def project(pl, pt):
    """(arclength of the point of polyline pl closest to pt, distance to it)"""
    best = (1e9, 0.0); acc = 0.0
    for a, b in zip(pl, pl[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]; l2 = dx * dx + dy * dy; seg = math.sqrt(l2)
        t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dy) / l2))
        d = math.hypot(pt[0] - (a[0] + dx * t), pt[1] - (a[1] + dy * t))
        if d < best[0]: best = (d, acc + seg * t)
        acc += seg
    return best[1], best[0]


def point_at(pl, s):
    acc = 0.0
    for a, b in zip(pl, pl[1:]):
        seg = dist(a, b)
        if acc + seg >= s - 1e-9:
            t = 0.0 if seg == 0 else (s - acc) / seg
            return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
        acc += seg
    return list(pl[-1])


def cut(pl, s0, s1):
    """the part of polyline pl between arclengths s0 < s1 (the vertices in between are kept)"""
    out = [point_at(pl, s0)]; acc = 0.0
    for a, b in zip(pl, pl[1:]):
        acc += dist(a, b)
        if s0 + 1e-6 < acc < s1 - 1e-6: out.append(list(b))
    out.append(point_at(pl, s1)); return out


def topology(F, labels):
    """F = smoke.json['B'][fam] ({shaft, paths, grilles}); labels = the size words of that family ({t, x, y}).
    -> {J, conn, conn_size, arms: [{pts, sections: [{s0, s1, size, labelled}]}], stubs: [{grille_end, duct_end, arm, s}]}   sizes are (width_mm, height_mm)"""
    sb = F["shaft"]; paths = [[list(p) for p in pl] for pl in F["paths"]]
    inside = lambda p: sb[0] - 5 <= p[0] <= sb[2] + 5 and sb[1] - 5 <= p[1] <= sb[3] + 5
    main = max(paths, key=plen)
    conn_src = [p for p in paths if p is not main and any(inside(v) for v in p)][0]
    ji = [i for i, v in enumerate(conn_src) if any(dist(v, m) < 2 for m in main)][0]
    J = [m for m in main if dist(m, conn_src[ji]) < 2][0]; jidx = main.index(J)
    ii = [i for i, v in enumerate(conn_src) if inside(v)][0]
    if ii < ji: conn = conn_src[ii:ji + 1][::-1]; rest = conn_src[ji:]
    else: conn = conn_src[ji:ii + 1]; rest = conn_src[:ji + 1][::-1]
    arm_pts = [a for a in (main[jidx:], main[:jidx + 1][::-1]) if len(a) > 1]
    if len(rest) > 1:
        arm = rest[:]
        for e in paths:
            if e is main or e is conn_src or len(e) < 3: continue
            if dist(e[-1], arm[-1]) < 3: arm = arm + e[::-1][1:]
            elif dist(e[0], arm[-1]) < 3: arm = arm + e[1:]
        arm_pts.append(arm)
    # stubs: free 2-vertex polylines + the last segment of every arm
    stubs = []
    for e in paths:
        if len(e) == 2 and e is not conn_src and 20 <= plen(e) <= STUB_MAX:
            d0 = min(project(a, e[0])[1] for a in arm_pts); d1 = min(project(a, e[1])[1] for a in arm_pts)
            stubs.append({"grille_end": e[0], "duct_end": e[1]} if d1 <= d0 else {"grille_end": e[1], "duct_end": e[0]})
    for k, a in enumerate(arm_pts):
        if plen(a[-2:]) <= STUB_MAX: stubs.append({"grille_end": a[-1], "duct_end": a[-2]}); arm_pts[k] = a[:-1]
    for st in stubs:
        best = min(((project(a, st["duct_end"]), k) for k, a in enumerate(arm_pts)), key=lambda t: t[0][1])
        (s, d), k = best
        assert d <= 1.5, ("stub does not touch an arm", st, d)
        st["arm"], st["s"] = k, s
    lab = []
    for w in labels:
        m = SIZE_RE.match(w["t"])
        if m: lab.append(((w["x"], w["y"]), (int(m.group(1)), int(m.group(2)))))
    arms = []
    for k, a in enumerate(arm_pts):
        L = plen(a); taps = sorted(set(round(st["s"], 1) for st in stubs if st["arm"] == k))
        bounds = [0.0] + [t for t in taps if 0.5 < t < L - 0.5] + [L]
        secs = [{"s0": b0, "s1": b1} for b0, b1 in zip(bounds, bounds[1:])]
        near = [(project(a, p)[0], size) for p, size in lab if project(a, p)[1] <= LABEL_R]
        for i, sec in enumerate(secs):
            last = i == len(secs) - 1; mid = (sec["s0"] + sec["s1"]) / 2
            cand = [(abs(s - mid), size) for s, size in near if sec["s0"] - 0.1 <= s < sec["s1"] + (0.1 if last else -0.1) and (size != STUB_STD or last)]
            sec["size"], sec["labelled"] = (min(cand)[1], True) if cand else (None, False)
        first = next((s["size"] for s in secs if s["size"]), STUB_STD)
        prev = None
        for sec in secs:
            if sec["size"] is None: sec["size"] = prev or first
            prev = sec["size"]
        arms.append({"pts": a, "len": L, "sections": secs})
    big = [(size[0] * size[1], size) for p, size in lab if size != STUB_STD and min(project(conn, p)[1], dist(p, conn[0]), dist(p, conn[-1])) <= CONN_R]
    conn_size = max(big)[1] if big else arms[0]["sections"][0]["size"]
    return {"J": J, "conn": conn, "conn_size": conn_size, "arms": arms, "stubs": stubs}


def pieces(arm):
    """[(p, q, size, labelled)] one duct piece per vertex-to-vertex segment of every section (pieces shorter than 6 cm are dropped)"""
    out = []
    for sec in arm["sections"]:
        sub = cut(arm["pts"], sec["s0"], sec["s1"])
        for p, q in zip(sub, sub[1:]):
            if dist(p, q) >= 6.0: out.append((p, q, sec["size"], sec["labelled"]))
    return out

SYS = {("cp", "fa"): "smk_cp_fa", ("cp", "ea"): "smk_cp_ea", ("co", "fa"): "smk_co_fa", ("co", "ea"): "smk_co_ea"}
NOTE_WH = "مقاس الوسم «العرض×الارتفاع» بالمليمتر؛ إن كان الترتيب معكوسًا فالارتفاع الصافي تحت المجرى أكبر — بانتظار تأكيدك"
ASSUME_Z_CP = "ارتفاع المجرى افتراض: قمته تحت بلاطة الدور الأرضي بـ5 سم (−0.50 م)؛ المخطط يعطي المسقط والمقاس لا المنسوب"
ASSUME_Z_COR = "ارتفاع المجرى في فراغ السقف افتراض: الجنب السفلي 2.52 م فوق الأرضية"
ASSUME_Z_FAG = "ارتفاع فتحة الهواء على جدار الشفت افتراض: 2.05–2.25 م فوق الأرضية (تحت السقف المستعار 2.40 م)"
ASSUME_Z_ROOF = "ارتفاع المجرى فوق السطح افتراض: الجنب السفلي 0.60 م فوق الأرضية على حوامل"
ASSUME_FAN_CP = "هيكل المروحة افتراض: رمز المسقط (37×54 سم) تخطيطي؛ طول الهيكل 80 سم وعرضه بعرض المجرى وارتفاعه بارتفاعه"
ASSUME_FAN_ROOF = "هيكل المروحة من مستطيل AV-MAC في مسقط السطح؛ ارتفاعه 1.20 م افتراض"
ASSUME_LOUVER_HEAD = "الردّادات: المرسوم نص «L×H 2 م × 1.5 م — 3 عدد» ولا موضع لها في المسقط؛ رُسم رأس بصمة الشفت نفسها بارتفاع 1.5 م، ومواضع الردّادات الثلاثة الفعلية — بانتظار تأكيدك"
ASSUME_LOUVER_ROOF = "ردّاد مروحة السطح: مستطيل التهشير في المسقط؛ ارتفاعه 1.20 م فوق أرضية السطح افتراض"
ASSUME_INHERIT = "مقطع بلا وسم مقاس: أُخذ مقاس المقطع الأقرب إلى نقطة الوصل (أو أقرب وسم) — بانتظار تأكيدك"
ASSUME_STUB_EA = "الفروع 300×200 مم بلا وسم على جانب الشفط؛ أُخذت مساويةً لجانب هواء التعويض الموسوم — بانتظار تأكيدك"

SRC_CP = "مخططات إدارة الدخان لموقف السيارات: SM-100 (البدروم، MECH1 ص17) وSM-101 (الدور الأرضي، MECH1 ص18) ومخطط الصاعد SM-105 (MECH1 ص22): المسارات والمقاسات ومواضع الشبكات والمخمّدات والمراوح كما رُسمت؛ ارتفاع المجاري وأبعاد هياكل المراوح افتراض (pipeline/smoke_build.py)"
SRC_CO = "مخططات إدارة الدخان للممرات: SM-102 (الأول، MECH1 ص19) وSM-103 (النمطي، MECH1 ص20) وSM-104 (السطح، MECH1 ص21) ومخطط الصاعد SM-105 (MECH1 ص22): الصاعدان والفروع والناشرات والمخمّدات والمراوح كما رُسمت؛ المناسيب افتراض (pipeline/smoke_build.py)"
MATS = {"m_duct_sm_fa": {"name": "مجرى هواء تعويض لإدارة الدخان", "color": "#4f8fa8", "code": "SM"},
        "m_duct_sm_ea": {"name": "مجرى شفط دخان (مقاوم للحرارة)", "color": "#a8553a", "code": "SM"}}
AREA_AR = {"cp": "موقف السيارات (البدروم)", "co": "الممرات"}
FAM_AR = {"fa": "هواء التعويض", "ea": "شفط الدخان"}
KIND_AR = {"duct": "مجرى", "riser": "صاعد / شفت", "damper": "مخمّد", "duct_flex": "وصلة مرنة (مشتقة)", "fan": "مروحة", "louver": "ردّاد", "grille": "شبكة", "diff": "ناشر شفط EAD"}
CF = {"duct": "doc", "riser": "doc", "damper": "doc", "duct_flex": "derived", "fan": "doc", "louver": "assumed", "grille": "doc", "diff": "doc"}
SP_AR = {"cp": "مخططات SM-100 وSM-101 وSM-105 (MECH1 ص17 وص18 وص22)", "co": "مخططات SM-102 وSM-103 وSM-104 وSM-105 (MECH1 ص19–22)"}
TYPES = {}
for _area in ("cp", "co"):
    for _fam in ("fa", "ea"):
        kinds = ["duct", "riser", "damper", "duct_flex", "fan", "louver"] + (["grille"] if (_area, _fam) != ("co", "ea") else ["diff"])
        for _k in kinds:
            spl = [["المصدر", SP_AR[_area]], ["المقاومة", "400 °م لساعتين بحسب ملاحظات المخطط"]]
            if _k == "duct": spl += [["المقاس", "وسم المقاس على المخطط (مم، العرض × الارتفاع)"], ["الارتفاع", "افتراض (المخطط يعطي المسقط لا المنسوب)"]]
            if _k == "riser": spl += [["المقاس", "صندوق الشفت في المسقط ووسم المقاس"]]
            if _k == "damper": spl += [["النوع", "FD أو VCD أو MFD بحسب الكلمة المجاورة للرمز"]]
            if _k == "duct_flex": spl += [["الأصل", "وصلة مشتقة من المسقط (pipeline/connectors.py)"]]
            t = {"n": f"{KIND_AR[_k]} — {FAM_AR[_fam]} — {AREA_AR[_area]}", "cf": CF[_k], "sp": spl, "sr": []}
            if _k == "fan": t["asm"] = ["أبعاد هيكل المروحة افتراض؛ رمز المسقط تخطيطي"]
            if _k == "louver": t["asm"] = ["موضع الردّادات الثلاثة (2×1.5 م) غير مرسوم؛ رُسم رأس بصمة الشفت" if _area == "cp" else "ارتفاع ردّاد مروحة السطح افتراض"]
            TYPES[f"{_k}_{_area}_{_fam}"] = t


def build(M, els, verbose=False):
    els[:] = [e for e in els if not ID_RE.search(e["id"])]
    if not os.path.exists(DATA): return {}
    D = json.load(open(DATA, encoding="utf-8"))
    sp = M["sp"]
    for t in (SRC_CP, SRC_CO):
        if t not in sp: sp.append(t)
    s_cp, s_co = sp.index(SRC_CP), sp.index(SRC_CO)
    for k, v in MATS.items(): M["mats"].setdefault(k, v)
    for k, v in TYPES.items(): M.setdefault("types", {})[k] = v
    ffl = {l["id"]: l["ffl"] for l in M["levels"]}
    new = []; counter = collections.Counter(); stats = collections.Counter()
    def unit_at(lv, x, y):
        for u in M.get("units", []):
            if u["level"] != lv: continue
            for r in u["rects"]:
                if r[0] <= x <= r[2] and r[1] <= y <= r[3]: return u["id"]
        return None

    def add(cat, lv, g, typ, mat, area, mark=None, a=None):
        counter[(cat, lv)] += 1
        e = {"id": f"{cat}-{lv}-SM{sum(counter.values()):04d}", "c": cat, "l": lv, "g": g, "mark": mark, "t": typ, "m": mat, "a": a or {}, "s": [s_cp if area == "cp" else s_co]}
        u = unit_at(lv, g[1], g[2]) if g[0] == "b" else unit_at(lv, g[1][0][0], g[1][0][1])
        if u: e["u"] = u
        new.append(e); stats[typ] += 1; return e

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

    slab = {}
    for e in els:
        if e["c"] == "S.slab" and e["g"][0] == "p": z0, z1 = slab.get(e["l"], (1e9, -1e9)); slab[e["l"]] = (min(z0, e["g"][2]), max(z1, e["g"][3]))
    def slab_bot(lv): return slab[lv][0] if lv in slab and lv not in ("B", "G") else ffl[lv] - (0.10 if lv != "B" else 0.0)
    Z_TOP_B = slab["G"][0] - Z_SOFFIT_GAP
    def ang(p, q): return round(math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])), 1)
    def zc_b(h_cm): return round(Z_TOP_B - h_cm / 200.0, 3)               # centre z of a car-park duct h_cm high, top-aligned under the slab

    def attrs(area, fam, **kw):
        return dict(sys=SYS[area, fam], **kw)

    def duct_attrs(area, fam, w, h, part, assumed, labelled=True):
        note = ('من وسم المخطط' if labelled else ASSUME_INHERIT) + '. ' + NOTE_WH
        return attrs(area, fam, w_cm=w, h_cm=h,
                     kind='مجرى هواء تعويض لإدارة الدخان' if fam == 'fa' else 'مجرى شفط دخان',
                     part=part, size_note=note, assumed=assumed)

    def shaft_attrs(area, fam, w, h, label, size_mm, part=None, flow=None):
        a = attrs(area, fam, w_cm=w, h_cm=h, shaft=True,
                  kind='صاعد / شفت إدارة الدخان', label=label, size_mm=size_mm)
        if part: a['part'] = part
        if flow is not None: a['flow_ls'] = flow
        return a

    cp_labels = {
        'fa': ('P.FA DUCT-F/A 9000 L/S 1400 mm x 1000 mm', '1400x1000',
               'FRESH AIR INTAKE LOUVER — L X H 2 M X 1.5 M — 3 NOS.'),
        'ea': ('P.EX DUCT-T/A 10600 L/S 1600 mm x 1000 mm', '1600x1000',
               'EXTRACT AIR LOUVER — L X H 2 M X 1.5 M — 3 NOS.'),
    }
    cp_flow = {
        'fa': ('مروحة هواء التعويض معلّقة بالسقف (Ceiling suspended Type) — Car Park Makeup Fan',
               '9000 (10 ACH) · 5400 (6 ACH) · 2700 (3 ACH)'),
        'ea': ('مروحة شفط الدخان معلّقة بالسقف (Ceiling suspended Type) — Car Park E.A Fan',
               '10600 (10 ACH) · 6360 (6 ACH) · 3180 (3 ACH)'),
    }
    grille_data = {
        'fa': ('1500x200', 'شبكة هواء تعويض FAG',
               '208 (3 ACH، CO منخفض) · 415 (6 ACH، CO مرتفع) · 693 (10 ACH، حريق)',
               '13 NO. FAG 1500 mm x 200 mm', 'FAG'),
        'ea': ('1700x200', 'شبكة شفط دخان EAG',
               '245 (3 ACH) · 489 (6 ACH) · 815 (10 ACH، حريق)',
               '13 NO. EAG 1700 mm x 200 mm', 'EAG'),
    }

    # Car-park systems, make-up then extract. Keep insertion order for SM ids.
    for fam in ('fa', 'ea'):
        F = D['B'][fam]
        labels = [w for w in D['B']['words'] if w['layer'] == ('M_FA_TEXT' if fam == 'fa' else 'M_EX_TEXT')]
        top = topology(F, labels); sb = F['shaft']
        wc, hc = (x / 10 for x in top['conn_size'])
        zc = zc_b(hc); J = top['J']; S = top['conn'][-1]
        cang = ang(J, S)
        cx, cy = (sb[0] + sb[2]) / 2, (sb[1] + sb[3]) / 2
        sw, sd = sb[2] - sb[0], sb[3] - sb[1]
        shaft_label, shaft_size, head_label = cp_labels[fam]
        mat = 'm_duct_sm_' + fam
        add('M.duct', 'B', ['b', cx, cy, sw, sd, 0, round(Z_TOP_B - hc / 100, 3), ffl['G']],
            'riser_cp_' + fam, mat, 'cp',
            a=shaft_attrs('cp', fam, sw, sd, shaft_label, shaft_size))
        add('M.outlet', 'G', ['b', cx, cy, sw, sd, 0, ffl['G'], round(ffl['G'] + LOUVER_HEAD_H, 3)],
            'louver_cp_' + fam, 'm_grille_fa', 'cp',
            a=attrs('cp', fam, w_cm=sw, h_cm=sd, shaft=True, kind='رأس ردّادات الشفت',
                    label=head_label, assumed=ASSUME_LOUVER_HEAD))
        add('M.duct', 'B', ['d', [[J[0], J[1], zc], [S[0], S[1], zc]], wc, hc],
            'duct_cp_' + fam, mat, 'cp',
            a=duct_attrs('cp', fam, wc, hc, 'قطعة وصل بين الشفت والتفرّع الرئيسي', ASSUME_Z_CP))
        fd = min(D['B']['fd'], key=lambda r: dist((r['x'], r['y']), (cx, cy)))
        fx, fy = fd['x'], fd['y']
        add('M.damper', 'B', ['b', fx, fy, DAMPER_ALONG, wc + DAMPER_PAD, cang,
                              round(zc-hc/200-0.04, 3), round(zc+hc/200+0.04, 3)],
            'damper_cp_' + fam, 'm_damper_ve', 'cp', mark='FD',
            a=attrs('cp', fam, damper='FD', kind='مخمّد حريق FD عند الشفت'))
        fan = min(D['B']['fans'], key=lambda r: dist(((r[0]+r[2])/2, (r[1]+r[3])/2), (cx, cy)))
        mx, my = (fan[0]+fan[2])/2, (fan[1]+fan[3])/2
        fan_kind, fan_flow = cp_flow[fam]
        add('M.fan', 'B', ['b', mx, my, FAN_LEN_CP, wc, cang,
                           round(zc-hc/200, 3), round(zc+hc/200, 3)],
            'fan_cp_' + fam, 'm_fan', 'cp',
            a=attrs('cp', fam, kind=fan_kind, flow_modes_ls=fan_flow, assumed=ASSUME_FAN_CP))
        for arm in top['arms']:
            for p, q, size, labelled in pieces(arm):
                w, h = size[0]/10, size[1]/10; z = zc_b(h)
                add('M.duct', 'B', ['d', [[p[0],p[1],z],[q[0],q[1],z]], w, h],
                    'duct_cp_' + fam, mat, 'cp',
                    a=duct_attrs('cp', fam, w, h, 'مجرى رئيسي (ذراع)', ASSUME_Z_CP, labelled))
        for stub in sorted(top['stubs'], key=lambda s: (s['grille_end'][1],s['grille_end'][0])):
            de, ge = stub['duct_end'], stub['grille_end']; z = zc_b(STUB_H)
            assumed = ASSUME_Z_CP + (' | ' + ASSUME_STUB_EA if fam == 'ea' else '')
            add('M.duct', 'B', ['d', [[de[0],de[1],z],[ge[0],ge[1],z]], STUB_W, STUB_H],
                'duct_cp_' + fam, mat, 'cp',
                a=duct_attrs('cp', fam, STUB_W, STUB_H, 'فرع 300×200 مم إلى الشبكة', assumed,
                             fam == 'fa'))
            v = min(D['B']['vcd'], key=lambda r: dist((r['x'],r['y']), ge))
            assert dist((v['x'],v['y']), ge) <= VCD_R, ('VCD', fam, ge, v)
            add('M.damper', 'B', ['b', v['x'], v['y'], DAMPER_ALONG, STUB_W+DAMPER_PAD,
                                  ang(de,ge), round(z-STUB_H/200-0.04,3), round(z+STUB_H/200+0.04,3)],
                'damper_cp_' + fam, 'm_damper_ve', 'cp', mark='VCD',
                a=attrs('cp', fam, damper='VCD', kind='مخمّد ضبط تدفق VCD'))
            c = min(F['grilles'], key=lambda r: dist((r['x'],r['y']),ge))
            assert dist((c['x'],c['y']),ge) <= CLUSTER_R, ('grille',fam,ge,c)
            rot, thick = (90,c['w']) if c['h'] > c['w'] else (0,c['h'])
            size, kind, flow, label, mark = grille_data[fam]
            add('M.outlet', 'B', ['b', c['x'],c['y'],GRILLE_LEN[fam],thick,rot,
                                  round(z-GRILLE_H/200,3),round(z+GRILLE_H/200,3)],
                'grille_cp_' + fam, 'm_grille_fa', 'cp', mark=mark,
                a=attrs('cp',fam,w_cm=GRILLE_LEN[fam],h_cm=GRILLE_H,size_mm=size,kind=kind,
                        flow_modes_ls=flow,label=label,
                        assumed='الطول من وسم المخطط؛ رمز المسقط (80 سم) تخطيطي'))

    co_labels = {
        'fa': ('SMS FA DUCT 284 L/S 400 x 250 -F/A-T/B', '400x250', 284),
        'ea': ('SMS EA DUCT 167 L/S 300 x 200 -F/B-T/A', '300x200', 167),
    }
    ground_note = 'القطعة من مخطط الصاعد SM-105؛ مسقط SM-101 لا يرسم الصاعد ولا فرع الدور الأرضي — بانتظار تأكيدك'
    for fam in ('fa','ea'):
        w,h = RISER[fam]; label,size,flow = co_labels[fam]
        add('M.duct','G',['b',*RISER_CENTRE[fam],w,h,0,ffl['G'],round(slab_bot('1'),3)],
            'riser_co_'+fam,'m_duct_sm_'+fam,'co',
            a=shaft_attrs('co',fam,w,h,label,size,part=ground_note,flow=flow))

    for lv in FLOORS:
        S = D['1'] if lv == '1' else D['TY']
        f0 = ffl[lv]; nxt = ORDER[ORDER.index(lv)+1]
        for fam in ('fa','ea'):
            w,h = RISER[fam]; label,size,flow = co_labels[fam]
            centre=[S[fam+'_riser'][0]['x'],S[fam+'_riser'][0]['y']]
            add('M.duct',lv,['b',*centre,w,h,0,round(slab_bot(lv),3),round(slab_bot(nxt),3)],
                'riser_co_'+fam,'m_duct_sm_'+fam,'co',
                a=dict(shaft_attrs('co',fam,w,h,label,size,flow=flow),source_xy=centre))
        fx = S['fa_riser'][0]['x']; fy0 = S['fa_riser'][0]['y']
        fy1 = min(S['fag_box'], key=lambda b:b['h'])['y']
        z = round(f0+sum(Z_FAG)/2,3)
        add('M.duct',lv,['d',[[fx,fy0,z],[fx,fy1,z]],*COR_FA_BRANCH],
            'duct_co_fa','m_duct_sm_fa','co',
            a=duct_attrs('co','fa',*COR_FA_BRANCH,'فرع إلى شبكة SMS FAG',ASSUME_Z_FAG))
        dam = next(v for v in S['dampers'] if v['layer']=='M_HVAC_DAM' and v['x']<1340)
        add('M.damper',lv,['b',dam['x'],dam['y'],DAMPER_ALONG,COR_FA_BRANCH[0]+DAMPER_PAD,-90.0,
                             round(z-0.14,3),round(z+0.14,3)],
            'damper_co_fa','m_damper_ve','co',mark='MFD',
            a=attrs('co','fa',damper='MFD',kind='مخمّد حريق ودخان آلي MFD (يُسمّى MSFD في مخطط الصاعد SM-105)'))
        add('M.outlet',lv,['b',fx,fy1,FAG_COR[0],FAG_COR[1],0,
                             round(f0+Z_FAG[0],3),round(f0+Z_FAG[1],3)],
            'grille_co_fa','m_grille_fa','co',mark='FAG',
            a=attrs('co','fa',w_cm=FAG_COR[0],h_cm=FAG_COR[2],flow_ls=142,size_mm='400x200',
                    kind='شبكة هواء تعويض FAG',label='SMS FAG 142 L/S 400x200 mm',assumed=ASSUME_Z_FAG))
        ex,ey0 = S['ea_riser'][0]['x'],S['ea_riser'][0]['y']
        b = S['ea_branch'][0]; ey1 = b[1][1]
        ez = round(f0+BOTTOM_COR+COR_EA_BRANCH[1]/200,3)
        add('M.duct',lv,['d',[[ex,ey0,ez],[b[1][0],ey1,ez]],*COR_EA_BRANCH],
            'duct_co_ea','m_duct_sm_ea','co',
            a=duct_attrs('co','ea',*COR_EA_BRANCH,'فرع شفط الممر',ASSUME_Z_COR))
        dam = next(v for v in S['dampers'] if v['layer']=='M_VE_DAM' and 1340<v['x']<1370)
        add('M.damper',lv,['b',dam['x'],dam['y'],DAMPER_ALONG,COR_EA_BRANCH[0]+DAMPER_PAD,-90.0,
                             round(ez-0.14,3),round(ez+0.14,3)],
            'damper_co_ea','m_damper_ve','co',mark='MFD',
            a=attrs('co','ea',damper='MFD',kind='مخمّد حريق ودخان آلي MFD (يُسمّى MSFD في مخطط الصاعد SM-105)'))
        m = S['ea_main'][0]; jx = b[1][0]; my = m[0][1]
        mz = round(f0+BOTTOM_COR+COR_EA_MAIN[1]/200,3)
        for p,q in ((m[0],[jx,my]),([jx,my],m[1])):
            add('M.duct',lv,['d',[[p[0],my,mz],[q[0],my,mz]],*COR_EA_MAIN],
                'duct_co_ea','m_duct_sm_ea','co',
                a=duct_attrs('co','ea',*COR_EA_MAIN,'مجرى الممر الرئيسي',ASSUME_Z_COR))
        for v in sorted((v for v in S['dampers'] if v['layer']=='M_VE_DAM' and (v['x']<1340 or v['x']>1370)),key=lambda v:v['x']):
            add('M.damper',lv,['b',v['x'],my,DAMPER_ALONG,COR_EA_MAIN[0]+DAMPER_PAD,0,
                                 round(mz-COR_EA_MAIN[1]/200-0.04,3),round(mz+COR_EA_MAIN[1]/200+0.04,3)],
                'damper_co_ea','m_damper_ve','co',mark='VCD',
                a=attrs('co','ea',damper='VCD',kind='مخمّد ضبط تدفق VCD'))
        for d in sorted(S['ead'],key=lambda d:d['x']):
            z1 = round(ceil_z(lv,d['x'],d['y'],f0+2.40),3)
            add('M.outlet',lv,['b',d['x'],d['y'],EAD,EAD,0,round(z1-0.04,3),z1],
                'diff_co_ea','m_diff_ea','co',mark='EAD',
                a=attrs('co','ea',w_cm=EAD,h_cm=EAD,flow_ls=84,size_mm='225x225',
                        kind='ناشر شفط EAD',label='2 No. SMS EAD 84 L/S EACH 225 x 225 mm'))

    S = D['R']; f0 = ffl['R']
    for fam in ('fa','ea'):
        w,h = RISER[fam]; label,size,flow = co_labels[fam]
        top_z = round(f0+ROOF_BOTTOM+ROOF_DUCT[fam][1]/100+0.02,3)
        centre=[S[fam+'_riser'][0]['x'],S[fam+'_riser'][0]['y']]
        add('M.duct','R',['b',*centre,w,h,0,round(slab_bot('R'),3),top_z],
            'riser_co_'+fam,'m_duct_sm_'+fam,'co',
            a=dict(shaft_attrs('co',fam,w,h,label,size,flow=flow),source_xy=centre))
    for fam,key in (('fa','fa_duct'),('ea','ea_duct')):
        pl = [list(p) for p in S[key][0]]
        w,h = ROOF_DUCT[fam]; z = round(f0+ROOF_BOTTOM+h/200,3)
        for p,q in zip(pl,pl[1:]):
            add('M.duct','R',['d',[[p[0],p[1],z],[q[0],q[1],z]],w,h],
                'duct_co_'+fam,'m_duct_sm_'+fam,'co',
                a=duct_attrs('co',fam,w,h,'مجرى السطح',ASSUME_Z_ROOF))
    for fam in ('fa','ea'):
        dam = next(v for v in S['dampers'] if (v['x']<1340) == (fam=='fa'))
        w,h = ROOF_DUCT[fam]; z = round(f0+ROOF_BOTTOM+h/200,3)
        add('M.damper','R',['b',dam['x'],dam['y'],DAMPER_ALONG,w+DAMPER_PAD,0,
                              round(z-h/200-0.04,3),round(z+h/200+0.04,3)],
            'damper_co_'+fam,'m_damper_ve','co',mark='MFD',
            a=attrs('co',fam,damper='MFD',kind='مخمّد حريق ودخان آلي MFD (يُسمّى MSFD في مخطط الصاعد SM-105)'))
    for fam,y0 in (('fa',1138),('ea',1758)):
        r = max((r for r in S['fan_rects'] if abs(r['y']-y0)<60),key=lambda r:r['w'])
        kind = ('مروحة هواء تعويض الممرات SMSF — مقاومة 400 °م لساعتين' if fam=='fa'
                else 'مروحة شفط دخان الممرات SMEF — مقاومة 400 °م لساعتين')
        add('M.fan','R',['b',r['x'],r['y'],r['w'],r['h'],0,round(f0,3),round(f0+FAN_ROOF_H,3)],
            'fan_co_'+fam,'m_fan','co',mark='SMSF' if fam=='fa' else 'SMEF',
            a=attrs('co',fam,kind=kind,flow_ls=284 if fam=='fa' else 167,assumed=ASSUME_FAN_ROOF))
    for fam in ('fa','ea'):
        v = S['louvers'][fam]
        add('M.outlet','R',['b',round((v['x0']+v['x1'])/2,1),round((v['y0']+v['y1'])/2,1),
                              round(v['x1']-v['x0'],1),round(v['y1']-v['y0'],1),0,
                              round(f0+LOUVER_ROOF[0],3),round(f0+LOUVER_ROOF[1],3)],
            'louver_co_'+fam,'m_grille_fa','co',
            a=attrs('co',fam,kind='ردّاد مروحة السطح (مصيدة رمل وشبكة طيور)',assumed=ASSUME_LOUVER_ROOF))

    els.extend(new)
    if verbose: print('smoke management:',len(new),dict(sorted(stats.items())))
    return dict(stats)


if __name__ == '__main__':
    SRC = os.path.join(os.path.dirname(HERE),'src','model.json')
    M = json.load(open(SRC,encoding='utf-8'))
    n0 = len(M['els']); build(M,M['els'],verbose=True)
    print('elements',n0,'->',len(M['els']))
