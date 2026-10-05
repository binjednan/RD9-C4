# -*- coding: utf-8 -*-
"""Post-process src/model.json (no PDFs needed): adds data that is derivable from what is already in the model
and from the pure-data knowledge-base modules.

  python3 pipeline/post_model.py            # rewrites src/model.json in place (idempotent)

Adds / replaces these keys:
  types      asset-type cards: doors/windows (kb.py) and electrical device classes (kb_elec.py); every field is
             taken from those modules, assumptions are kept apart in 'asm' and the card is marked 'derived'.
  fin, finq  finish schedule A500 (finishes.py) + model-derived areas for floor/ceiling codes (BOQ reconciliation)
  ral        paint-system table supplied by the client (RAL.xlsx) — RAL values are NOT defined there ("RAL xxxx"),
             conflicts with the A500 extraction are flagged, never resolved.
  clashes    geometric clash candidates (MEP vs structure, duct vs pipe) computed from element geometry.
             MEP elevations above the ceiling are assumptions (see element cards), so these are candidates only.
Nothing here is invented: whatever is not in the documents stays out or is explicitly flagged.
"""
import json, os, sys, collections, math, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kb, kb_elec, finishes
from shapely.geometry import Polygon, LineString, Point, box
from shapely.affinity import rotate as shp_rotate
from shapely.strtree import STRtree

SRC = os.path.join(os.path.dirname(HERE), "src", "model.json")
M = json.load(open(SRC, encoding="utf-8"))
els = M["els"]
els[:] = [e for e in els if not re.search(r"-X\d{4}$", e["id"])]      # accessories of pipeline/extras.py are rebuilt below (keep them out of every earlier pass)

# ------------------------------------------------------------------ corrections to the extracted model (applied once, logged in meta.fixes)
FIXES = M.setdefault("meta", {}).setdefault("fixes", [])
LV = {l["id"]: l for l in M["levels"]}

def _z_idx(g):
    return {"b": (6, 7), "r": (5, 6), "cyl": (4, 5), "p": (2, 3)}.get(g[0])

def shift_z(e, dz):
    g = e["g"]
    ix = _z_idx(g)
    if ix:
        g[ix[0]] = round(g[ix[0]] + dz, 3); g[ix[1]] = round(g[ix[1]] + dz, 3)
    elif g[0] in ("d", "t"):
        for pt in g[1]:
            pt[2] = round(pt[2] + dz, 3)

def level_footprints():
    fl = collections.defaultdict(list)
    for e in els:
        if e["c"] in ("A.floor", "S.slab", "S.raft"):
            g = e["g"]
            if g[0] == "p":
                gg = Polygon(g[1], g[4] if len(g) > 4 and g[4] else []).buffer(0)
            elif g[0] == "r":
                gg = box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4]))
            else:
                continue
            fl[e["l"]].append(gg)
    from shapely.ops import unary_union
    out = {}
    for l, v in fl.items():
        u = unary_union(v)
        ps = list(u.geoms) if hasattr(u, "geoms") else [u]
        out[l] = unary_union([Polygon(p.exterior) for p in ps]).buffer(60)   # exterior only: lift shafts / stair voids stay "inside"
    return out

def plan_pts(g):
    t = g[0]
    if t == "p": return [(p[0], p[1]) for p in g[1]]
    if t == "r": return [((g[1] + g[3]) / 2, (g[2] + g[4]) / 2)]
    if t in ("cyl", "b"): return [(g[1], g[2])]
    if t in ("d", "t", "rs"): return [(p[0], p[1]) for p in g[1]]
    return []

if "duct_mm_to_cm" not in FIXES:
    # hvac.py read the duct size tag ("450x250", millimetres) as centimetres: every duct was 10x too big
    for e in els:
        if e["c"] == "M.duct":
            w, h = e["g"][2], e["g"][3]
            e["g"][2], e["g"][3] = round(w / 10, 1), round(h / 10, 1)
            shift_z(e, (h - h / 10) / 200.0)          # centre was soffit - h/200 with the wrong h
            a = e.setdefault("a", {})
            a["w_cm"], a["h_cm"] = round(w / 10, 1), round(h / 10, 1)
    FIXES.append("duct_mm_to_cm")

if "offplan_removed" not in FIXES:
    # sheet margins (details, legends, riser diagrams) were extracted as if they were plan content
    FP = level_footprints()
    keep_cats = {"A.site", "S.pile", "S.raft", "A.floor", "A.ceil", "S.slab"}
    removed, kept = [], []
    for e in els:
        u = FP.get(e["l"]); P = plan_pts(e["g"])
        outside = (u is not None and P and e["c"] not in keep_cats and e["t"] != "lift_car"
                   and all(not u.contains(Point(p)) for p in P))
        if outside and e["l"] == "T" and e["c"][0] == "E" and FP.get("R") is not None and all(FP["R"].contains(Point(p)) for p in P):
            shift_z(e, LV["R"]["ffl"] - LV["T"]["ffl"]); e["l"] = "R"
            e.setdefault("a", {})["mount_note"] = "نُقل من مستوى T إلى R (داخل نطاق المبنى) وأُعيد حساب ارتفاعه من أرضية R — افتراض هندسي يحتاج تأكيد"
            kept.append(e); continue
        if outside:
            removed.append({"id": e["id"], "c": e["c"], "l": e["l"], "t": e["t"], "xy": [round(v) for v in P[0]]})
        else:
            kept.append(e)
    els[:] = kept
    M["els"] = els
    json.dump(removed, open(os.path.join(HERE, "data", "removed_offplan.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    FIXES.append("offplan_removed")
    M["meta"]["removed_offplan"] = len(removed)
    print("removed off-plan elements:", len(removed))

if "roof_wall_lights" not in FIXES:
    # wall lights (TYPE-11) on the top-roof sheet were mounted 2.2 m above the T slab where there is no wall;
    # the rooms' walls belong to level R (their top is 26.4 m), so measure the 2.2 m from the R floor
    dz = LV["R"]["ffl"] - LV["T"]["ffl"]
    n = 0
    for e in els:
        if e["l"] == "T" and e["t"] == "e_L11":
            shift_z(e, dz); e["l"] = "R"; n += 1
            e.setdefault("a", {})["mount_note"] = "الارتفاع 2.2 م محسوب من أرضية R (جدران الغرف العلوية تتبع R) — افتراض هندسي يحتاج تأكيد"
    FIXES.append("roof_wall_lights"); print("rehomed roof wall lights:", n)

if "roof_dish_on_slab" not in FIXES:
    # the 1.2 m SMATV dishes were placed 1.1 m above the roof floor with no support (height on the roof is not in the documents)
    n = 0
    for e in els:
        if e["l"] == "T" and e["t"] == "e_T4":
            shift_z(e, -1.1); n += 1
            e.setdefault("a", {})["mount_note"] = "وُضع الصحن على بلاطة السطح مباشرة؛ ارتفاع القاعدة غير مذكور في المستندات — افتراض هندسي يحتاج تأكيد"
    FIXES.append("roof_dish_on_slab"); print("dishes lowered onto slab:", n)

if "piles_30cm_display" not in FIXES:
    # request: show only 30 cm of each pile below the raft (they go underground); the real 13 m length stays in the card
    n = 0
    for e in els:
        if e["c"] == "S.pile" and e["g"][0] == "cyl":
            top = e["g"][5]
            e["g"][4] = round(top - 0.30, 3)
            a = e.setdefault("a", {})
            a["display_note"] = "يُعرض 30 سم فقط تحت اللبشة للدلالة على امتداد الخازوق تحت الأرض؛ الطول الفعلي 13 م (من المخطط)"
            n += 1
    FIXES.append("piles_30cm_display"); print("piles shortened for display:", n)

# ------------------------------------------------------------------ site / ground-floor landscape (pipeline/site.py -> data/site.json)
SITE_JSON = os.path.join(HERE, "data", "site.json")
SITE_MATS = {
    "site_grass": {"name": "عشب / مسطحات خضراء (A102 طبقة L1-THIN)", "color": "#7fae5f", "code": "A102"},
    "site_paving": {"name": "رصف ممرات وساحات — النوع غير محدد على A102 (A500: F12/F13/F14)", "color": "#c9b99c", "code": "A102 LAND - TILE"},
    "site_rubber": {"name": "بلاط مطاطي خارجي 100 مم — منطقة ألعاب الأطفال", "color": "#6e7a6a", "code": "F15"},
    "site_asphalt": {"name": "أسفلت الممر والمواقف الخارجية — التشطيب غير محدد على A102", "color": "#4b5057", "code": "A102"},
    "site_mark": {"name": "علامات مرورية وخطوط مواقف (طلاء)", "color": "#f2f2ee", "code": "A102"},
    "site_shade": {"name": "مظلة ظل دائرية — مادة غير محددة (افتراض)", "color": "#d8cdb6", "code": "A102 LINEA"},
    "site_sand": {"name": "رمل/تربة برتقالية — أحواض ومسطحات غير مزروعة (كما في صور الموقع 7 أغسطس)", "color": "#c98a55", "code": "A102 L1-THIN / صور"},
    "granite_curb": {"name": "جرانيت داكن بعروق بيضاء — جدران أحواض الزراعة (من الصور؛ النوع غير محدد في المخططات)", "color": "#3b3e44", "code": "A102 / صور"},
}
for L_ in M["layers"]:
    if L_["id"] == "A" and not any(s_[0] == "A.stage" for s_ in L_["subs"]):
        L_["subs"].append(["A.stage", "الكماليات الإخراجية (للعرض لا للتنفيذ)"])
if os.path.exists(SITE_JSON):
    S_ = json.load(open(SITE_JSON, encoding="utf-8"))
    for k, v in SITE_MATS.items():
        M["mats"].setdefault(k, v)
    pool = M["sp"]; pidx = {t: i for i, t in enumerate(pool)}
    def sp_idx(t):
        if t not in pidx:
            pidx[t] = len(pool); pool.append(t)
        return pidx[t]
    els[:] = [e for e in els if not e["id"].startswith("A.site-G-S")]
    _BEDS = []; _gazebo_c = (940.0, 4020.0)
    for k, e in enumerate(S_["els"], 1):
        ne = {"id": f"A.site-G-S{k:03d}", "c": e["c"], "l": e["l"], "g": e["g"], "mark": e["mark"], "t": e["t"], "m": e["m"], "a": e["a"], "s": [sp_idx(t) for t in e["src"]]}
        if e.get("stage"): ne["stage"] = e["stage"]
        if e["t"] == "site_shade":                       # the old round gazebo canopy of site.json: replaced by the detailed gazebo of A2305 (landscape_els.gazebo)
            _gz_pts = e["g"][1] if e["g"][0] == "p" else None
            if _gz_pts: _gazebo_c = (sum(q[0] for q in _gz_pts) / len(_gz_pts), sum(q[1] for q in _gz_pts) / len(_gz_pts))
            continue
        if e["t"] == "site_grass":
            # the A102 'grass' hatch (L1-THIN) is the planting BED.  The granite wall (A2302 sections 1-2: stone-clad R.C., ~22 cm, top = FL +1.05 = finished level of the cap) stands OUTSIDE
            # the bed, between it and the paving.  Photos 7 Aug: the beds are unplanted orange sand BELOW the wall top, no lawn yet.  Small serpentine strips are planter beds,
            # large areas are open sand/lawn beds (planting plan A2300: ZOYS.T lawn + big trees).
            from shapely.geometry import Polygon as _P, box as _bxx
            _g = e["g"]; _poly = _P(_g[1], _g[4] if len(_g) > 4 and _g[4] else None).buffer(0); _top = _g[3]; _small = _poly.area / 1e4 < 40
            def _rings(pg):
                out_ = []
                for q in (list(pg.geoms) if hasattr(pg, "geoms") else [pg]):
                    if q.is_empty or q.area < 50: continue
                    out_.append(([[round(x, 1), round(y, 1)] for x, y in list(q.exterior.coords)[:-1]], [[[round(x, 1), round(y, 1)] for x, y in list(h.coords)[:-1]] for h in q.interiors]))
                return out_
            CW = 22; _sand = round(_top - (0.20 if _small else 0.10), 2)
            ne["m"] = "site_sand"; ne["t"] = "site_planter_bed" if _small else "site_sand_bed"
            _ra = _rings(_poly)
            if _ra: ne["g"] = ["p", _ra[0][0], -0.1, _sand] + ([_ra[0][1]] if _ra[0][1] else [])
            ne["a"] = dict(ne["a"], kind="planter_sand" if _small else "sand_bed", sand_top_m=_sand, fl_m=_top,
                           fill_note="رمل/تربة برتقالية غير مزروعة كما في صور الموقع؛ منسوب الرمل أخفض من حافة الجدار (+%.2f) بـ%d سم — افتراض بصري من الصور (التصميم A2302: التربة تحت غطاء الجرانيت مباشرة)" % (_top, round((_top - _sand) * 100)))
            els.append(ne)
            _BEDS.append((_poly, _sand))
            for _j, (_o, _h) in enumerate(_rings(_poly.buffer(CW).difference(_poly).intersection(_bxx(-45, -45, 4435, 4435))), 1):
                els.append({"id": f"A.site-G-S{k:03d}W{_j}", "c": "A.site", "l": "G", "g": ["p", _o, -0.1, _top] + ([_h] if _h else []), "mark": "PLANTER-CURB", "t": "site_planter_wall", "m": "granite_curb",
                            "a": {"kind": "planter_wall", "thick_cm": CW, "top_m": _top, "level_note": "جدار حوض جرانيت W12 مغطّى بالحجر — الحافة العلوية FL +%.2f (A2302 مقطع 1 و2)" % _top,
                                  "assumed": "السماكة 22 سم قُدّرت من مقياس A2302 (1:20) ومن الفراغ بين حدّ الطبقة L1-THIN وحافة الرصف على A102 (20–37 سم)"}, "s": ne["s"]})
            continue
        els.append(ne)
    # surrounding ground outside the plot / street: bare sand, as in photos 1, 5, 10, 21 (desert plots around the site). Inferred - no drawing covers it.
    from shapely.geometry import box as _bx
    from shapely.ops import unary_union as _uu0
    _roads = [r_ for r_ in (_bx(min(p_[0] for p_ in _e["g"][1]), min(p_[1] for p_ in _e["g"][1]), max(p_[0] for p_ in _e["g"][1]), max(p_[1] for p_ in _e["g"][1])) for _e in els if _e["id"].startswith("A.site-G-S") and _e.get("mark", "").startswith("STREET"))]
    _sand = _bx(-5500, -5500, 10000, 9000).difference(_uu0(_roads + [_bx(-90, -70, 4485, 4485)]))
    for _j, _q in enumerate(list(_sand.geoms) if hasattr(_sand, "geoms") else [_sand], 1):
        els.append({"id": f"A.site-G-S{900 + _j}", "c": "A.site", "l": "G", "g": ["p", [[round(x), round(y)] for x, y in list(_q.exterior.coords)[:-1]], -0.5, -0.1] + ([[[[round(x), round(y)] for x, y in list(h.coords)[:-1]] for h in _q.interiors]] if list(_q.interiors) else []),
                    "mark": "GROUND-SAND", "t": "site_sand_bed", "m": "site_sand",
                    "a": {"kind": "ground_sand", "level_note": "رمل الأرض خارج حدود القطعة والشارع — من الصور (أراضٍ رملية مجاورة)", "assumed": "المنسوب -0.10 م وحدود المنطقة افتراض؛ لا يوجد مخطط يغطي ما حول القطعة"}, "s": []})
    M["els"] = els
    print("site elements merged:", len(S_["els"]))

    # ---- landscape: trees / shrubs / plants (A2300), benches (A102), kids-area shade sails + fence + play equipment (A2300/A2305), gazebo (A2305). pipeline/landscape.py -> data/landscape.json
    LAND_JSON = os.path.join(HERE, "data", "landscape.json")
    els[:] = [e for e in els if not re.match(r"^A\.(stage|site|rail)-G-L\d+$", e["id"])]
    if os.path.exists(LAND_JSON):
        import landscape_els as _LE
        _LD = json.load(open(LAND_JSON, encoding="utf-8"))
        for _k, _v in _LE.MATS.items(): M["mats"].setdefault(_k, _v)
        _sidx = [sp_idx(t) for t in _LE.SRC]
        _new = _LE.all_elements(_LD, _BEDS, _gazebo_c)
        _cnt_l = collections.Counter()
        for _n, _e in enumerate(_new, 1):
            _cnt_l[_e["c"]] += 1
            ne2 = {"id": f"{_e['c']}-G-L{_n:04d}", "c": _e["c"], "l": _e["l"], "g": _e["g"], "mark": _e["mark"], "t": _e["t"], "m": _e["m"], "a": _e["a"], "s": _sidx}
            if _e.get("stage"): ne2["stage"] = _e["stage"]
            if _e.get("grp"): ne2["grp"] = _e["grp"]
            els.append(ne2)
        M["els"] = els
        print("landscape elements merged:", dict(_cnt_l), "| trees", len(_LD["trees"]), "shrubs", len(_LD["shrubs"]), "small plants", len(_LD["small"]))

if "g_exterior_finishes_removed" not in FIXES:
    # the generic room-kind -> finish mapping put granite floors (F16) and ceilings on the ground level outside the building
    # (drive way, bays, garden). The exterior is now modelled from A102 (pipeline/site.py), so drop them.
    BX0, BY0, BX1, BY1 = -80, -80, 3330, 2000          # building ground-floor zone (A102): tower + retail frontage + entrance paving band
    kept, gone = [], []
    for e in els:
        if e["l"] == "G" and e["c"] in ("A.floor", "A.ceil"):
            P = plan_pts(e["g"]); cx = sum(p[0] for p in P) / len(P); cy = sum(p[1] for p in P) / len(P)
            if not (BX0 <= cx <= BX1 and BY0 <= cy <= BY1):
                gone.append({"id": e["id"], "c": e["c"], "xy": [round(cx), round(cy)], "fin": (e.get("a") or {}).get("fin")}); continue
        kept.append(e)
    els[:] = kept; M["els"] = els
    json.dump(gone, open(os.path.join(HERE, "data", "removed_exterior_floors.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    M["meta"]["removed_exterior_floors"] = len(gone)
    FIXES.append("g_exterior_finishes_removed"); print("exterior G floors/ceilings removed:", len(gone))

# ------------------------------------------------------------------ roof equipment (pipeline/roof.py -> data/roof.json)
ROOF_JSON = os.path.join(HERE, "data", "roof.json")
ROOF_TYPES = {}
if os.path.exists(ROOF_JSON):
    import re as _re
    Rf = json.load(open(ROOF_JSON, encoding="utf-8"))
    for k, v in Rf["mats"].items():
        M["mats"].setdefault(k, v)
    ROOF_TYPES = Rf["types"]
    pool = M["sp"]; pidx = {t: i for i, t in enumerate(pool)}
    def sp_idx2(t):
        if t not in pidx:
            pidx[t] = len(pool); pool.append(t)
        return pidx[t]
    els[:] = [e for e in els if not _re.search(r"-R-S\d+$", e["id"])]
    for k, e in enumerate(Rf["els"], 1):
        ne = {"id": f"{e['c']}-R-S{k:04d}", "c": e["c"], "l": e["l"], "g": e["g"], "mark": e["mark"], "t": e["t"], "m": e["m"], "a": e["a"], "s": [sp_idx2(t) for t in e["src"]]}
        if e.get("grp"): ne["grp"] = e["grp"]
        els.append(ne)
    M["els"] = els
    print("roof elements merged:", len(Rf["els"]))

# ------------------------------------------------------------------ vehicle ramp + external stair 03 (pipeline/ramp_stair.py -> data/ramp_stair.json)
RS_JSON = os.path.join(HERE, "data", "ramp_stair.json")
RS_TYPES = {}
if os.path.exists(RS_JSON):
    import re as _re2
    Rs = json.load(open(RS_JSON, encoding="utf-8"))
    for k, v in Rs.get("mats", {}).items():
        M["mats"].setdefault(k, v)
    RS_TYPES = Rs["types"]
    pool = M["sp"]; pidx = {t: i for i, t in enumerate(pool)}
    def sp_idx4(t):
        if t not in pidx:
            pidx[t] = len(pool); pool.append(t)
        return pidx[t]
    els[:] = [e for e in els if not _re2.search(r"-RS\d+$", e["id"])]
    cnt_rs = collections.Counter()
    for e in Rs["els"]:
        cnt_rs[(e["c"], e["l"])] += 1
        els.append({"id": f"{e['c']}-{e['l']}-RS{cnt_rs[(e['c'], e['l'])]:03d}", "c": e["c"], "l": e["l"], "g": e["g"], "mark": e["mark"], "t": e["t"], "m": e["m"], "a": e["a"], "s": [sp_idx4(t) for t in e["src"]]})
    M["els"] = els
    print("ramp/stair elements merged:", len(Rs["els"]))

# ------------------------------------------------------------------ electrical rooms equipment (pipeline/elec_rooms.py -> data/elec_rooms.json)
ER_JSON = os.path.join(HERE, "data", "elec_rooms.json")
ER_TYPES = {}
if os.path.exists(ER_JSON):
    Er = json.load(open(ER_JSON, encoding="utf-8"))
    for k, v in Er.get("mats", {}).items():
        M["mats"].setdefault(k, v)
    ER_TYPES = Er["types"]
    pool = M["sp"]; pidx = {t: i for i, t in enumerate(pool)}
    def sp_idx5(t):
        if t not in pidx:
            pidx[t] = len(pool); pool.append(t)
        return pidx[t]
    els[:] = [e for e in els if not re.search(r"-ER\d+$", e["id"])]
    cnt_er = collections.Counter()
    for e in Er["els"]:
        cnt_er[(e["c"], e["l"])] += 1
        els.append({"id": f"{e['c']}-{e['l']}-ER{cnt_er[(e['c'], e['l'])]:03d}", "c": e["c"], "l": e["l"], "g": e["g"], "mark": e["mark"], "t": e["t"], "m": e["m"], "a": e["a"], "s": [sp_idx5(t) for t in e["src"]]})
    M["els"] = els
    # the HV / transformer / LV rooms are F.F.L. +0.90 (A102): lift their floor finishes, drop the 3.05 m ceilings that the 3.2 m transformer and 2.35 m switchgear would pierce
    ROOMS_UP = [box(2635, 240, 3185, 1185), box(2376, 1270, 2856, 1620)]
    ROOMS_NOCEIL = [box(2635, 240, 3185, 1185)]
    n_fl = n_ce = 0; kept = []
    for e in els:
        if e["l"] == "G" and e["c"] in ("A.floor", "A.ceil") and e["g"][0] in ("p", "r"):
            P = plan_pts(e["g"]); cx = sum(p[0] for p in P) / len(P); cy = sum(p[1] for p in P) / len(P)
            if e["c"] == "A.floor" and e["g"][0] == "p" and any(r.contains(Point(cx, cy)) for r in ROOMS_UP) and abs(e["g"][2] - 0.35) < 0.01:
                e["g"][2], e["g"][3] = 0.90, 0.912; n_fl += 1
                e.setdefault("a", {})["floor_note"] = "F.F.L. +0.90 م لغرف الكهرباء (A102) — رُفع من +0.35"
            if e["c"] == "A.floor" and e["g"][0] == "r" and any(r.contains(Point(cx, cy)) for r in ROOMS_UP) and abs(e["g"][5] - 0.35) < 0.01:
                e["g"][5], e["g"][6] = 0.90, 0.912; n_fl += 1
                e.setdefault("a", {})["floor_note"] = "F.F.L. +0.90 م لغرف الكهرباء (A102) — رُفع من +0.35"
            if e["c"] == "A.ceil" and any(r.contains(Point(cx, cy)) for r in ROOMS_NOCEIL):
                n_ce += 1; continue
        kept.append(e)
    els[:] = kept; M["els"] = els
    if n_ce: json.dump(["ceilings of the HV / transformer rooms (3.05 m) removed: equipment is taller"], open(os.path.join(HERE, "data", "removed_elec_room_ceilings.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("electrical rooms: equipment", len(Er["els"]), "| floors lifted to +0.90:", n_fl, "| ceilings removed:", n_ce)

if "r_open_roof_finishes_removed" not in FIXES:
    # the generic builder gave the OPEN roof (chillers, FAHU, open terraces) floors (F2 ceramic) and ceilings (C3) as if it were a bathroom
    # ('BATH A:4.8M2' text matched to every cell). Rooms of the roof are exactly the footprint of the top slabs (S.slab T): keep finishes only there.
    from shapely.ops import unary_union as _uu
    zones = []
    for e in els:
        if e["l"] == "T" and e["c"] == "S.slab" and e["g"][0] == "r":
            g = e["g"]; zones.append(box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4])))
    Z = _uu(zones).buffer(25) if zones else None
    kept, gone = [], []
    for e in els:
        if Z is not None and e["l"] == "R" and e["c"] in ("A.floor", "A.ceil"):
            P = plan_pts(e["g"]); cx = sum(p[0] for p in P) / len(P); cy = sum(p[1] for p in P) / len(P)
            if not Z.contains(Point(cx, cy)):
                gone.append({"id": e["id"], "c": e["c"], "xy": [round(cx), round(cy)], "fin": (e.get("a") or {}).get("fin")}); continue
        kept.append(e)
    els[:] = kept; M["els"] = els
    json.dump(gone, open(os.path.join(HERE, "data", "removed_open_roof_finishes.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    M["meta"]["removed_open_roof_finishes"] = len(gone)
    FIXES.append("r_open_roof_finishes_removed"); print("open-roof floors/ceilings removed:", len(gone))

# ------------------------------------------------------------------ B/G/R fire-fighting + FFC line + risers (pipeline/mep_bg.py -> data/mep_bg.json)
MEPBG_JSON = os.path.join(HERE, "data", "mep_bg.json")
MEPBG_TYPES = {}
if "pipe_glyphs_removed" not in FIXES:
    # flow-arrow heads, valve bow-ties and leader ticks on the pipe layers were extracted as tubes (hundreds of 8-15 cm fragments)
    import glyphs as _G
    groups = collections.defaultdict(list)
    for e in els:
        if e["c"] in ("P.ff", "P.cold", "P.hot", "P.drain") and e["g"][0] == "t" and not re.search(r"-M\d+$", e["id"]):
            groups[(e["c"], e["l"])].append(e)
    gone = []
    for k, es in groups.items():
        fl = _G.flags([[(p[0], p[1]) for p in e["g"][1]] for e in es])
        gone += [e["id"] for e, f in zip(es, fl) if f]
    gs = set(gone)
    els[:] = [e for e in els if e["id"] not in gs]; M["els"] = els
    M["meta"]["removed_pipe_glyphs"] = len(gone)
    FIXES.append("pipe_glyphs_removed"); print("pipe glyph fragments removed:", len(gone))

if os.path.exists(MEPBG_JSON):
    Mb = json.load(open(MEPBG_JSON, encoding="utf-8"))
    for k, v in Mb["mats"].items():
        M["mats"].setdefault(k, v)
    MEPBG_TYPES = Mb["types"]
    pool = M["sp"]; pidx = {t: i for i, t in enumerate(pool)}
    def sp_idx3(t):
        if t not in pidx:
            pidx[t] = len(pool); pool.append(t)
        return pidx[t]
    els[:] = [e for e in els if not re.search(r"-M\d+(c\d+)?$", e["id"])]
    cnt_ = collections.Counter()
    for e in Mb["els"]:
        cnt_[(e["c"], e["l"])] += 1
        ne = {"id": f"{e['c']}-{e['l']}-M{cnt_[(e['c'], e['l'])]:04d}", "c": e["c"], "l": e["l"], "g": e["g"], "mark": e["mark"], "t": e["t"], "m": e["m"], "a": e["a"], "s": [sp_idx3(t) for t in e["src"]]}
        if e.get("grp"): ne["grp"] = e["grp"]
        els.append(ne)
    M["els"] = els
    print("mep_bg elements merged:", len(Mb["els"]))

# ------------------------------------------------------------------ placement fixes (audit: devices floating next to the wall they belong to)
def _wall_geoms(level):
    from shapely.ops import unary_union as _u
    G = []
    for e in els:
        if e["l"] != level or e["c"] not in ("A.wall", "S.wall", "S.col", "A.rail"): continue
        g = e["g"]
        try:
            if g[0] == "r": G.append(box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4])))
            elif g[0] == "p": G.append(Polygon(g[1], g[4] if len(g) > 4 and g[4] else None).buffer(0))
        except Exception: pass
    return _u(G) if G else None

def _bbox_poly(g):
    import math as _m
    if g[0] == "b":
        hw, hd = g[3] / 2, g[4] / 2; a = _m.radians(g[5]); c, s_ = abs(_m.cos(a)), abs(_m.sin(a)); ex, ey = hw * c + hd * s_, hw * s_ + hd * c
        return box(g[1] - ex, g[2] - ey, g[1] + ex, g[2] + ey)
    if g[0] == "cyl": return box(g[1] - g[3], g[2] - g[3], g[1] + g[3], g[2] + g[3])
    if g[0] == "r": return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4]))
    return None

STAIR03 = (3985.0, 1100.0, 4305.0, 1700.0)      # external stair 03 footprint (A604)
if True:      # stateless + idempotent: merged sources (roof/mep_bg/site) are re-merged on every run
    # the ground-floor sheets repeat the devices of the external stair 03; at G the stair is an open well (no ceiling, upstand walls up to +1.40 m),
    # so ceiling devices hover and wall devices float above the wall top. Remove the ceiling ones, bring the wall ones down to the upstand wall.
    gone, lowered = [], 0
    kept = []
    for e in els:
        g = e["g"]
        if e["l"] == "G" and e["c"][0] == "E" and g[0] in ("b", "cyl") and STAIR03[0] <= g[1] <= STAIR03[2] and STAIR03[1] <= g[2] <= STAIR03[3]:
            z0, z1 = (g[6], g[7]) if g[0] == "b" else (g[4], g[5])
            if z0 > 2.8:                                  # ceiling-mounted (3.0-3.05): there is no ceiling over the open stair
                gone.append({"id": e["id"], "t": e["t"], "xy": [round(g[1]), round(g[2])], "z": [z0, z1]}); continue
            if z1 > 1.38:
                dz = round(1.38 - z1, 3); shift_z(e, dz); lowered += 1
                e.setdefault("a", {})["mount_note"] = "جدار بئر الدرج الخارجي 03 يرتفع حتى +1.40 م فقط عند الدور الأرضي (A604)؛ خُفض الجهاز ليكون على الجدار — افتراض هندسي يحتاج تأكيد"
        kept.append(e)
    els[:] = kept; M["els"] = els
    if gone: json.dump(gone, open(os.path.join(HERE, "data", "removed_stair03_g_ceiling.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    (FIXES.append("stair03_devices_v1") if "stair03_devices_v1" not in FIXES else None); print("stair 03: ceiling devices removed at G:", len(gone), "| wall devices lowered:", lowered)

if True:      # stateless + idempotent: merged sources (roof/mep_bg/site) are re-merged on every run
    # wall-mounted devices (sockets, panels, thermostats, speakers ...) are drawn as small symbols a few centimetres off the wall face; the 3-D plate then hovers.
    # Slide every one of them along the axis of the nearest wall until its back touches the wall (only when the wall is within the tolerance).
    from shapely.ops import nearest_points
    SJ = os.path.join(os.path.dirname(HERE), "src", "samples.json")
    wall_types = {"thermostat"}
    if os.path.exists(SJ):
        for k, v in json.load(open(SJ, encoding="utf-8"))["samples"].items():
            if (v.get("place") or {}).get("mount") == "wall": wall_types.add(k)
    wall_types.discard("fhc"); wall_types.discard("e_P5")                                  # FHC boxes already sit in the wall recess
    BIG = {"e_P18", "e_F8", "e_F9", "e_T20", "e_P14", "e_P16", "e_F19"}   # panels: wider tolerance
    cache = {}; moved = collections.Counter(); far = []
    for e in els:
        if e.get("t") not in wall_types or e["g"][0] not in ("b", "cyl", "r"): continue
        if e["l"] not in cache: cache[e["l"]] = _wall_geoms(e["l"])
        W_ = cache[e["l"]]
        if W_ is None: continue
        bp = _bbox_poly(e["g"]); d = W_.distance(bp)
        tol = 120 if (e["t"] in BIG or (e["l"] == "G" and STAIR03[0] <= e["g"][1] <= STAIR03[2] and STAIR03[1] <= e["g"][2] <= STAIR03[3])) else 80
        if d <= 0.5: continue
        if d > tol:
            far.append((e["id"], e["t"], e["l"], round(d))); continue
        pa, pb = nearest_points(bp, W_); dx, dy = pb.x - pa.x, pb.y - pa.y
        if abs(dx) >= abs(dy): dy = 0.0
        else: dx = 0.0
        g = e["g"]; g[1] = round(g[1] + dx, 1); g[2] = round(g[2] + dy, 1)
        a = e.setdefault("a", {}); a["snap_cm"] = round(d, 1)
        a["snap_note"] = f"سُحب {round(d,1)} سم إلى وجه الجدار — رمز المخطط يبعد عن الجدار؛ الجهاز مركّب على الجدار فعليًا (تصحيح مطابقة)"
        moved[e["t"]] += 1
    M["meta"]["wall_snap_far"] = far
    (FIXES.append("wall_snap_v1") if "wall_snap_v1" not in FIXES else None); print("wall devices snapped:", sum(moved.values()), "| still off any wall:", len(far))

if True:      # stateless + idempotent: merged sources (roof/mep_bg/site) are re-merged on every run
    # EP-103: "15A switch socket for FCU (double-pole switch with neon)" is drawn beside each FCU, which hangs in the ceiling void; the generic 1.30 m
    # wall height left 98 of the 106 switches floating in mid-air below the unit. Mount them on the casing of the FCU they serve (nearest unit on the level).
    fc = collections.defaultdict(list)
    for e in els:
        if e["c"] == "M.equip" and e.get("t") == "fcu" and e["g"][0] == "b": fc[e["l"]].append(e)
    n_ok = n_far = 0
    for e in els:
        if e.get("t") != "e_P5" or e["g"][0] != "b": continue
        cand = fc.get(e["l"], [])
        if not cand: continue
        gx, gy = e["g"][1], e["g"][2]
        f = min(cand, key=lambda u: math.hypot(u["g"][1] - gx, u["g"][2] - gy))
        fg = f["g"]; dist = math.hypot(fg[1] - gx, fg[2] - gy)
        if dist > 130: n_far += 1; continue
        # lateral side of the unit facing the symbol (FCU long axis = x when ang is 0/180, y when 90)
        horiz = abs(math.cos(math.radians(fg[5]))) > 0.7
        L, Wd = (fg[3], fg[4]) if True else (fg[3], fg[4])
        ux, uy = (1, 0) if horiz else (0, 1)           # unit axis in plan
        lx, ly = -uy, ux                                   # lateral axis
        along = (gx - fg[1]) * ux + (gy - fg[2]) * uy; lat = (gx - fg[1]) * lx + (gy - fg[2]) * ly
        sgn = 1 if lat >= 0 else -1
        half_l = fg[3] / 2; half_w = fg[4] / 2
        along = max(-half_l + 12, min(half_l - 12, along))
        cx = fg[1] + along * ux + sgn * (half_w + 2.3) * lx; cy = fg[2] + along * uy + sgn * (half_w + 2.3) * ly
        z_mid = (fg[6] + fg[7]) / 2
        g = e["g"]; g[1], g[2] = round(cx, 1), round(cy, 1); g[3], g[4] = 9, 4.0
        g[5] = 0.0 if abs(lx) < 0.5 else 90.0
        g[6], g[7] = round(z_mid - 0.045, 3), round(z_mid + 0.045, 3)
        a = e.setdefault("a", {})
        a["side"] = ("E" if lx * sgn > 0 else "W") if abs(lx) > 0.5 else ("N" if ly * sgn > 0 else "S")
        a["mount_note"] = "مفتاح FCU مركّب على غلاف الوحدة في فراغ السقف المستعار (EP-103) — الارتفاع 1.30 م الافتراضي كان يتركه معلّقًا في الهواء؛ الموضع على الوحدة افتراض هندسي يحتاج تأكيد"
        n_ok += 1
    # the ones whose unit is further than 130 cm (technical rooms): slide them onto the nearest wall (<= 100 cm) at the 1.30 m EP-109 height
    from shapely.ops import nearest_points as _np
    wc = {}; n_w = n_still = 0
    for e in els:
        if e.get("t") != "e_P5" or e["g"][0] != "b" or "FCU" in (e.get("a") or {}).get("mount_note", ""): continue
        if e["l"] not in wc: wc[e["l"]] = _wall_geoms(e["l"])
        W_ = wc[e["l"]]
        if W_ is None: n_still += 1; continue
        bp = _bbox_poly(e["g"]); d = W_.distance(bp)
        if d <= 0.5: continue
        if d > 100: n_still += 1; continue
        pa, pb = _np(bp, W_); dx, dy = pb.x - pa.x, pb.y - pa.y
        if abs(dx) >= abs(dy): dy = 0.0
        else: dx = 0.0
        e["g"][1] = round(e["g"][1] + dx, 1); e["g"][2] = round(e["g"][2] + dy, 1)
        e.setdefault("a", {})["snap_note"] = f"سُحب {round(d)} سم إلى أقرب جدار (لا توجد وحدة FCU قريبة) — تصحيح مطابقة"
        n_w += 1
    (FIXES.append("fcu_switch_to_unit_v1") if "fcu_switch_to_unit_v1" not in FIXES else None); print("FCU switches mounted on their unit:", n_ok, "| no unit within 130 cm:", n_far, "| slid to wall:", n_w, "| still free:", n_still)

if True:      # stateless: roof.json / mep_bg.json are re-merged on every run, so this must be re-applied every run
    n = 0
    for e in els:
        if e["c"] == "M.outlet" and e["g"][0] == "b" and (e["g"][3] < 1.5 or e["g"][4] < 1.5):
            g = e["g"]
            if g[4] < 1.5: g[4] = 12.0
            if g[3] < 1.5: g[3] = 12.0
            a = e.setdefault("a", {}); a["size_cm"] = f"{round(max(g[3], g[4]))}×{round(min(g[3], g[4]))}"
            a["size_note"] = "الرمز مرسوم كخط (بلا عمق)؛ أُعطي عمق 12 سم لشبكة خطية — افتراض هندسي يحتاج تأكيد"
            n += 1
    if "zero_depth_grille_v1" not in FIXES: FIXES.append("zero_depth_grille_v1")
    print("zero-depth grilles fixed:", n)

# ------------------------------------------------------------------ column de-duplication (owner: "ground-floor columns must not be doubled")
# The structural column-layout sheets draw every C1/C6 column twice on S-COLUMN: the concrete outline (e.g. 30x160) and the reinforcement-cage line 5 cm inside it
# (40 mm cover, STR general notes). Both were extracted as columns, so G carried 10 ghost columns inside the real ones. Drop every column that lies inside another one.
import support as _SUP0
_dup, _keep = [], []
for _lv in sorted({e["l"] for e in els if e["c"] == "S.col"}):
    _cols = [(e, _SUP0.poly_of(e["g"])) for e in els if e["c"] == "S.col" and e["l"] == _lv and e["g"][0] in ("p", "r")]
    for e, pp in _cols:
        if pp is None: continue
        if any(f is not e and q is not None and q.area > pp.area * 1.05 and q.buffer(8).contains(pp) for f, q in _cols):
            _dup.append({"id": e["id"], "l": _lv, "mark": e.get("mark"), "bounds": [round(v) for v in pp.bounds]})
_dup_ids = {d["id"] for d in _dup}
if _dup_ids:
    els[:] = [e for e in els if e["id"] not in _dup_ids]; M["els"] = els
    json.dump(_dup, open(os.path.join(HERE, "data", "removed_col_cage_lines.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
M["meta"]["removed_col_cage_lines"] = max(M["meta"].get("removed_col_cage_lines", 0), len(_dup_ids))
print("duplicate (cage-line) columns removed:", len(_dup_ids))

# ------------------------------------------------------------------ physical consistency fixes found by the support audit
# (1) basement services drawn inside the open ramp well: nothing can hang in the air above a ramp that is open to the sky -> removed (logged)
_hole = None
for _e in els:
    if _e["c"] == "S.slab" and _e["l"] == "G" and _e["g"][0] == "p":
        for _h in (_e["g"][4] or []):
            if len(_h) > 20 and max(p_[1] for p_ in _h) > 4000: _hole = Polygon(_h).buffer(0)
if _hole is not None:
    _gone, _keep = [], []
    for _e in els:
        if _e["l"] == "B" and _e["c"][0] in "EMP" and _e["g"][0] in ("b", "cyl", "t", "d", "r"):
            _pp = plan_pts(_e["g"])
            if _pp and all(_hole.contains(Point(q)) for q in _pp):
                _gone.append({"id": _e["id"], "c": _e["c"], "t": _e.get("t"), "xy": [round(_pp[0][0]), round(_pp[0][1])]}); continue
        _keep.append(_e)
    # pipes / ducts that only PARTLY cross the open ramp well: cut them at the opening edge (they would hang over the roadway)
    from shapely.geometry import LineString as _LS
    _trim = 0; _extra = []
    for _e in _keep:
        if _e["l"] != "B" or _e["c"][0] not in "EMP" or _e["g"][0] not in ("t", "d"): continue
        _pts = _e["g"][1]
        if len(_pts) < 2 or not _LS([(q[0], q[1]) for q in _pts]).intersects(_hole): continue
        _runs = []
        for _a, _b in zip(_pts[:-1], _pts[1:]):
            _sg = _LS([(_a[0], _a[1]), (_b[0], _b[1])]); _L = _sg.length
            if _L < 1e-6: continue
            _df = _sg.difference(_hole)
            for _pc in (list(_df.geoms) if hasattr(_df, "geoms") else [_df]):
                if _pc.is_empty or _pc.length < 8: continue
                _c = list(_pc.coords); _ends = []
                for _xy in (_c[0], _c[-1]):
                    _t = _sg.project(Point(_xy)) / _L; _ends.append([round(_xy[0], 1), round(_xy[1], 1), round(_a[2] + (_b[2] - _a[2]) * _t, 3)])
                if _runs and abs(_runs[-1][-1][0] - _ends[0][0]) < 0.6 and abs(_runs[-1][-1][1] - _ends[0][1]) < 0.6: _runs[-1].append(_ends[1])
                else: _runs.append(_ends)
        if len(_runs) == 1 and len(_runs[0]) == len(_pts) and all(abs(u[0] - v[0]) < 0.6 and abs(u[1] - v[1]) < 0.6 for u, v in zip(_runs[0], _pts)): continue
        _trim += 1
        if not _runs: _e["g"] = None; continue
        _e["a"] = dict(_e.get("a") or {}, mount_note="قُصّ الأنبوب/المجرى عند حافة فتحة المنحدر المفتوحة (لا يمكن أن يمرّ فوق الطريق) — تصحيح تعارض مكاني")
        _g0 = _e["g"]; _e["g"] = [_g0[0], _runs[0]] + list(_g0[2:])
        for _j, _rn in enumerate(_runs[1:], 1):
            _x = dict(_e); _x["id"] = f"{_e['id']}c{_j}"; _x["g"] = [_g0[0], _rn] + list(_g0[2:]); _extra.append(_x)
    _keep = [_e for _e in _keep if _e["g"] is not None] + _extra
    _gone_n = len(_gone)
    els[:] = _keep; M["els"] = els
    print("pipes/ducts trimmed at the ramp opening:", _trim)
    if _gone: json.dump(_gone, open(os.path.join(HERE, "data", "removed_ramp_zone_b.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    M["meta"]["removed_ramp_zone_b"] = max(M["meta"].get("removed_ramp_zone_b", 0), len(_gone))
    print("basement services inside the ramp well removed:", len(_gone))
# (2) roof build-up: the R floor level (+23.35) is 20 cm above the top of the roof slab (+23.15); the open roof had nothing in between, so every machine stood 20 cm above it
els[:] = [e for e in els if e["id"] != "A.floor-R-BU1"]
for _e in list(els):
    if _e["c"] == "S.slab" and _e["l"] == "R" and _e["g"][0] == "p":
        _lv = LV["R"]; _top = _e["g"][3]
        if _lv["ffl"] - _top > 0.05:
            M["mats"].setdefault("roof_buildup", {"name": "طبقات سطح الدور R (عزل مائي/حراري + مونة + تشطيب) — غير محدّدة في المستندات", "color": "#d3d2cb", "code": "A105"})
            els.append({"id": "A.floor-R-BU1", "c": "A.floor", "l": "R", "g": ["p", _e["g"][1], _top, _lv["ffl"], _e["g"][4] if len(_e["g"]) > 4 else None], "mark": "ROOF-BUILDUP", "t": "roof_buildup", "m": "roof_buildup",
                         "a": {"kind": "roof_buildup", "thick_cm": round((_lv["ffl"] - _top) * 100), "note": "الفرق بين منسوب بلاطة السطح (+23.15) وF.F.L. (+23.35)؛ مكوّنات الطبقات غير مذكورة — افتراض"}, "s": []})
            print("roof build-up layer added:", round((_lv["ffl"] - _top) * 100), "cm")
M["els"] = els

# (3) ground floor: only 31 % of the building footprint had a floor finish (the other ~450 m2 - lobby, corridors, retail - showed the bare slab, 45 cm
#     BELOW the finished floor level +0.35 on which walls, doors, sockets and pipes were modelled, so they all seemed to hover). Fill the gaps with the floor build-up.
els[:] = [e for e in els if not e["id"].startswith("A.floor-G-BU")]
import support as _SUP
from shapely.ops import unary_union as _uu2
_slabG = [_e for _e in els if _e["c"] == "S.slab" and _e["l"] == "G" and _e["g"][0] == "p"]
if _slabG:
    _sg = _slabG[0]["g"]; _slab_poly = Polygon(_sg[1], _sg[4] if len(_sg) > 4 and _sg[4] else None).buffer(0)
    _zone = _slab_poly.intersection(box(-80, -80, 3330, 2000))
    _cov = []
    for _e in els:
        if _e["l"] == "G" and _e["c"] in ("A.floor", "A.site") and _e["g"][0] in ("p", "r"):
            if _e["c"] == "A.site" and not (_e["g"][2 if _e["g"][0] == "p" else 5] > -0.2): continue
            _pp = _SUP.poly_of(_e["g"])
            if _pp is not None and not _pp.is_empty: _cov.append(_pp)
    _gap = _zone.difference(_uu2(_cov).buffer(1.0)) if _cov else _zone
    _top0, _ffl = _sg[3], LV["G"]["ffl"]
    M["mats"].setdefault("floor_fill", {"name": "أرضية الدور الأرضي — طبقة التسوية/التشطيب للمناطق غير المسمّاة (ردهة، ممرات، محلات)", "color": "#cfccc2", "code": "A102/A500"})
    _geoms = list(_gap.geoms) if hasattr(_gap, "geoms") else [_gap]; _n = 0
    for _g in _geoms:
        if _g.is_empty or _g.area < 900: continue
        _n += 1
        _ext = [[round(x, 1), round(y, 1)] for x, y in list(_g.exterior.coords)[:-1]]
        _holes = [[[round(x, 1), round(y, 1)] for x, y in list(h.coords)[:-1]] for h in _g.interiors if Polygon(h).area > 200]
        els.append({"id": f"A.floor-G-BU{_n}", "c": "A.floor", "l": "G", "g": ["p", _ext, _top0, _ffl, _holes or None], "mark": "G-FLOOR-FILL", "t": "floor_fill", "m": "floor_fill",
                    "a": {"kind": "floor_fill", "thick_cm": round((_ffl - _top0) * 100), "area_m2": round(_g.area / 1e4, 1), "note": "منطقة بلا تشطيب أرضية مسمّى في النموذج؛ أُكملت إلى F.F.L. +0.35 م — نوع التشطيب افتراض"}, "s": []})
    print("ground-floor fill added:", _n, "areas,", round(sum(g.area for g in _geoms if g.area >= 900) / 1e4), "m2")
M["els"] = els

# ground-floor cladding colour: the photos (7 Aug) show the ground floor clad in medium-grey stone / porcelain with beige GRC above (A200 finishes: 1 porcelain, 2 GRC beige)
M["mats"].setdefault("clad_stone_g", {"name": "كسوة حجر/بورسلين رمادي للدور الأرضي (من صور الموقع؛ اللون تقديري)", "color": "#a6a299", "code": "A200 (1)"})
for _e in els:
    if _e["l"] == "G" and _e["c"] == "A.clad" and _e.get("m") in ("clad_porc", "clad_stone_g"): _e["m"] = "clad_stone_g"

# (5) ground-floor facade openings: 5 openings of the envelope were completely open from the floor to the first-floor soffit (south x 370-570 / 1345-1515 / 2195-2395, north x 1590-1790):
#     A102 draws a glazed vestibule there (layer A-GLAZED: side glass 93 cm deep) with entrance doors (A200 elevation: aluminium frame, 10 mm tempered glass, GRC/porcelain panel above).
els[:] = [e for e in els if not re.match(r"^A\.(win|door|clad)-G-GX\d+$", e["id"])]
_gx = 0
def _gxadd(c, t, m, g, mark, note):
    global _gx
    _gx += 1
    els.append({"id": f"{c}-G-GX{_gx:03d}", "c": c, "l": "G", "g": g, "mark": mark, "t": t, "m": m, "a": {"kind": "entrance", "note": note}, "s": []})
_NOTE = "مدخل زجاجي ناقص في النموذج: A102 يرسم الردهة الزجاجية (طبقة A-GLAZED، عمق 93 سم) والواجهة A200 تُظهر باب ألمنيوم بزجاج مقسّى 10 مم؛ الارتفاعات من CW-G (0.35–3.35) والكسوة فوقها حتى بلاطة الدور الأول"
for _a, _b, _yf, _yi, _dir in ((370, 570, 235, 319, 1), (1345, 1515, 235, 309, 1), (2195, 2395, 235, 319, 1), (1590, 1790, 1630, 1541, -1)):
    _y0, _y1 = (min(_yf, _yi), max(_yf, _yf if False else _yi)) if _dir == 1 else (min(_yi, _yf), max(_yi, _yf))
    # side glazing (vestibule) and its frame
    for _x0, _x1 in ((_a, _a + 3), (_b - 3, _b)):
        _gxadd("A.win", "win_CW-G", "glass_vis", ["r", _x0, _y0, _x1, _y1, 0.40, 3.30], "CW-G", _NOTE)
        _gxadd("A.win", "win_CW-G", "frame_alu", ["r", _x0 - 1, _y0, _x1 + 1, _y1, 0.35, 0.40], "CW-G", _NOTE)
        _gxadd("A.win", "win_CW-G", "frame_alu", ["r", _x0 - 1, _y0, _x1 + 1, _y1, 3.30, 3.35], "CW-G", _NOTE)
    # inner entrance doors (double leaf) + transom
    _xi0, _xi1 = _a + 3, _b - 3; _ym = _yi; _mid = (_xi0 + _xi1) / 2
    _gxadd("A.win", "win_CW-G", "glass_vis", ["r", _xi0, _ym - 1.5, _xi1, _ym + 1.5, 0.45, 2.52], "D9", _NOTE)
    for _xx0, _xx1 in ((_xi0, _xi0 + 6), (_mid - 3, _mid + 3), (_xi1 - 6, _xi1)):
        _gxadd("A.door", "door_D9", "door_alu", ["r", _xx0, _ym - 2.5, _xx1, _ym + 2.5, 0.37, 2.55], "D9", _NOTE)
    _gxadd("A.door", "door_D9", "door_alu", ["r", _xi0, _ym - 2.5, _xi1, _ym + 2.5, 0.37, 0.47], "D9", _NOTE)
    _gxadd("A.door", "door_D9", "door_alu", ["r", _xi0, _ym - 2.5, _xi1, _ym + 2.5, 2.50, 2.60], "D9", _NOTE)
    _gxadd("A.win", "win_CW-G", "glass_vis", ["r", _xi0, _ym - 1.5, _xi1, _ym + 1.5, 2.60, 3.30], "CW-G", _NOTE)
    _gxadd("A.win", "win_CW-G", "frame_alu", ["r", _xi0, _ym - 2.5, _xi1, _ym + 2.5, 3.30, 3.35], "CW-G", _NOTE)
    # porcelain / GRC panel above the opening on the facade line (same band as the neighbouring bays: +3.35 to the first-floor soffit)
    _fy0, _fy1 = (223, 247) if _dir == 1 else (1618, 1642)
    _gxadd("A.clad", "clad_porcelain", "clad_porc", ["r", _a, _fy0, _b, _fy1, 3.35, 5.37], "CLAD", _NOTE)
print("ground-floor facade opening elements added:", _gx)
M["els"] = els

# ------------------------------------------------------------------ support analysis (pipeline/support.py): what carries every MEP / electrical element?
_wt = set()
try:
    for _k, _v in json.load(open(os.path.join(os.path.dirname(HERE), "src", "samples.json"), encoding="utf-8"))["samples"].items():
        if (_v.get("place") or {}).get("mount") == "wall": _wt.add(_k)
except Exception: pass
_wt.discard("fhc")
# (4) ground-floor ceilings: the typical floors carry a false ceiling over 98 % of their floor area, the ground floor only 15 % (the A1401 reflected-ceiling plan of the
#     ground floor could not be read), so ~80 lights / diffusers / detectors hung on 2.4 m rods from the first-floor slab. Where ceiling devices exist but no ceiling,
#     infer a plain ceiling at the typical height (F.F.L. + 2.70 m) over the floor area (room) that contains them. Flagged as an assumption.
els[:] = [e for e in els if not e["id"].startswith("A.ceil-G-INF")]
_S0 = _SUP.Support(els, M["levels"], set())
_gfl = [(_i, _SUP.poly_of(_e["g"])) for _i, _e in enumerate(els) if _e["l"] == "G" and _e["c"] == "A.floor" and _e["g"][0] in ("p", "r")]
_used = {}; _loose = []
_zc = LV["G"]["ffl"] + 2.70
for _i, _e in enumerate(els):
    if _e["l"] != "G" or _e["c"][0] in "SA": continue
    _z0, _z1 = _SUP.zr(_e["g"])
    if _z1 is None or not (_zc - 0.25 <= _z1 <= _zc + 0.05): continue          # sits at / just under the ceiling line
    _r = _S0.analyse(_i)
    if _r["kind"] not in ("rod", "float", "hang"): continue
    _pp = _SUP.poly_of(_e["g"])
    if _pp is None: continue
    _c = _pp.centroid; _hit = False
    for _fi, _fp in _gfl:
        if _fp is not None and _fp.contains(_c): _used[_fi] = _used.get(_fi, 0) + 1; _hit = True; break
    if not _hit: _loose.append(_c)
_nin = 0; _ain = 0
for _fi, _cnt_dev in sorted(_used.items()):
    _fp = _SUP.poly_of(els[_fi]["g"]).difference(box(2635, 240, 3185, 1185))          # no ceiling in the HV / transformer rooms (equipment taller than 3.05 m)
    for _q in (list(_fp.geoms) if hasattr(_fp, "geoms") else [_fp]):
        if _q.is_empty or _q.area < 900: continue
        _nin += 1; _ain += _q.area
        els.append({"id": f"A.ceil-G-INF{_nin:03d}", "c": "A.ceil", "l": "G", "g": ["p", [[round(x, 1), round(y, 1)] for x, y in list(_q.exterior.coords)[:-1]], round(_zc, 2), round(_zc + 0.02, 2)] + ([[[[round(x, 1), round(y, 1)] for x, y in list(h.coords)[:-1]] for h in _q.interiors]] if list(_q.interiors) else []),
                    "mark": "G-CEIL-INFERRED", "t": "ceil_inferred", "m": "fin_C1", "a": {"kind": "ceil_inferred", "fin": ["C1"], "assumed_h": 2.7, "devices": _cnt_dev, "note": "سقف مستنتج: أجهزة سقفية بلا سقف في الدور الأرضي؛ الارتفاع F.F.L.+2.70 (كالأدوار المتكررة) والتشطيب C1 — افتراض يحتاج مخطط A1401"}, "s": []})
# ceiling lights over the covered entrance band (no A.floor there - exterior paving): a rectangular soffit strip 3.2 m wide around each row of them
if _loose:
    from shapely.ops import unary_union as _uu3
    _soff = _uu3([_c.buffer(160, cap_style=3, join_style=2) for _c in _loose]).intersection(box(-80, 20, 3330, 2000)).difference(box(2635, 240, 3185, 1185))
    for _q in (list(_soff.geoms) if hasattr(_soff, "geoms") else [_soff]):
        if _q.is_empty or _q.area < 900: continue
        _nin += 1; _ain += _q.area
        els.append({"id": f"A.ceil-G-INF{_nin:03d}", "c": "A.ceil", "l": "G", "g": ["p", [[round(x, 1), round(y, 1)] for x, y in list(_q.exterior.coords)[:-1]], round(_zc, 2), round(_zc + 0.02, 2)],
                    "mark": "G-SOFFIT-INFERRED", "t": "ceil_inferred", "m": "fin_C1", "a": {"kind": "soffit_inferred", "fin": ["C1"], "assumed_h": 2.7, "note": "سقف/سوفيت مستنتج فوق الممر المغطى: إنارة سقفية بلا سقف؛ الارتفاع F.F.L.+2.70 — افتراض يحتاج مخطط A1401 والواجهات"}, "s": []})
print("ground-floor inferred ceilings:", _nin, "areas,", round(_ain / 1e4), "m2")
M["els"] = els

_S = _SUP.Support(els, M["levels"], _wt)
_cnt = collections.Counter()
for _i, _e in enumerate(els):
    _a = _e.setdefault("a", {})
    for _k in ("rod_cm", "hang_cm", "stand_cm", "unsupported"): _a.pop(_k, None)
    if _e["c"][0] in "SA": continue
    _r = _S.analyse(_i); _k = _r["kind"]; _cnt[_k] += 1
    if _k == "lower":                                                  # wall device above the top of its (lower) host wall: bring it down onto the wall
        _z0, _z1 = _SUP.zr(_e["g"]); _dz = round((_r["wall_top"] - 0.12) - _z1, 3); shift_z(_e, _dz)
        _a["mount_note"] = f"الجدار المضيف أخفض من ارتفاع التركيب الافتراضي؛ خُفض الجهاز {abs(round(_dz*100))} سم ليكون على الجدار — افتراض هندسي يحتاج تأكيد"
        _r = _S.analyse(_i); _k = _r["kind"]
    if _k == "rod": _a["rod_cm"] = max(8, _r["gap_cm"])
    elif _k == "hang": _a["hang_cm"] = max(8, _r["gap_cm"])
    elif _k == "stand": _a["stand_cm"] = max(8, _r["gap_cm"])
    elif _k == "float" and _e["l"] == "T" and _e["g"][0] in ("b", "cyl"):
        _dz = LV["R"]["ffl"] - LV["T"]["ffl"]; shift_z(_e, _dz); _e["l"] = "R"; _r2 = _S.analyse(_i)
        if _r2["kind"] in ("ok", "rod"):
            _a["mount_note"] = "لا بلاطة علوية T تحته؛ نُقل إلى سطح الدور R (قائم على السطح) — افتراض هندسي يحتاج تأكيد"; _cnt["rehomed_T_to_R"] += 1
        else:
            shift_z(_e, -_dz); _e["l"] = "T"; _a["unsupported"] = 1; _a.setdefault("mount_note", "لا يوجد جدار/سقف/أرضية مضيف قريب في النموذج — موضع الرمز على المخطط يحتاج مراجعة (مدقّق الدعم: غير محمول)")
    elif _k == "float": _a["unsupported"] = 1; _a.setdefault("mount_note", "لا يوجد جدار/سقف/أرضية مضيف قريب في النموذج — موضع الرمز على المخطط يحتاج مراجعة (مدقّق الدعم: غير محمول)")
M["meta"]["support"] = dict(_cnt)
print("support analysis:", dict(_cnt))

# ------------------------------------------------------------------ accessories added after the GitHub hand-off (pipeline/extras.py): cornices, ramp fence, site lights, parking canopies
import extras as _EXT
els[:] = [e for e in els if not re.search(r"-X\d{4}$", e["id"])]
EXT = _EXT.build(M)
els[:] = [e for e in els if e["t"] not in ("lift_car", "shed_sail")]                      # the two solid boxes are replaced by the detailed cars of extras.lifts()
for _k, _v in EXT["mats"].items(): M["mats"].setdefault(_k, _v)
_pool = M["sp"]; _pidx = {t: i for i, t in enumerate(_pool)}
def _spx(t):
    if t not in _pidx:
        _pidx[t] = len(_pool); _pool.append(t)
    return _pidx[t]
_cx = collections.Counter()
for _e in EXT["els"]:
    _cx[(_e["c"], _e["l"])] += 1
    _ne = {"id": f"{_e['c']}-{_e['l']}-X{sum(_cx.values()):04d}", "c": _e["c"], "l": _e["l"], "g": _e["g"], "mark": _e["mark"], "t": _e["t"], "m": _e["m"], "a": _e["a"], "s": [_spx(t) for t in _e["src"]]}
    if _e.get("grp"): _ne["grp"] = _e["grp"]
    if _e.get("stage"): _ne["stage"] = _e["stage"]
    if _e.get("u"): _ne["u"] = _e["u"]
    if _e.get("u2"): _ne["u2"] = _e["u2"]
    els.append(_ne)
M["els"] = els
print("extras merged:", len(EXT["els"]), dict(collections.Counter(e["t"] for e in EXT["els"])))

# ------------------------------------------------------------------ types
types = {}
for k, d in kb.DOORS.items():
    types["door_" + k] = {
        "n": d["ar"], "cf": "doc",
        "sp": [["المقاس (عرض × ارتفاع)", f'{d["w"]} × {d["h"]} سم'], ["مقاومة الحريق", d["fire"]], ["الموقع", d["loc"]],
               ["المادة", d["mat"]], ["الإطار", d["frame"]], ["اتجاه الفتح", d["opens"]], ["بند BOQ (الكمية)", d["boq"]]],
        "sr": [f'جدول الأبواب {d["sheet"]}', f'جدول الكميات BOQ البند {d["boq"].split(" — ")[0]}'],
    }
for code, v in kb.WINS.items():
    w, h, loc, qty = v[:4]
    types["win_" + code] = {
        "n": f"نافذة / واجهة زجاجية {code}", "cf": "doc",
        "sp": [["المقاس (عرض × ارتفاع)", f"{w} × {h} سم"], ["الموقع", loc], ["الكمية في BOQ", str(qty)]],
        "sr": ["جدول النوافذ والواجهات الزجاجية (المخططات المعمارية وجدول الكميات)"],
    }
for cid, c in kb_elec.C.items():
    t = {"n": c["ar"], "cf": "derived" if c["asm"] else "doc",
         "sp": [[a, b] for a, b in c["spec"]] + [["الاسم بالإنجليزية (من المفتاح)", c["en"]]],
         "sr": [c["src"]] if c["src"] else []}
    if c["asm"]:
        t["asm"] = list(c["asm"])
    types["e_" + cid] = t
used = {e["t"] for e in els}
types = {k: v for k, v in types.items() if k in used}
M["types"] = types
M["types"].update(ROOF_TYPES)
M["types"].update(MEPBG_TYPES)
M["types"].update(RS_TYPES)
M["types"].update(ER_TYPES)
M["types"].update(EXT["types"])

# ------------------------------------------------------------------ finishes + areas
def poly_area_cm2(g):
    if g[0] == "p":
        def ar(p):
            return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2
        return ar(g[1]) - sum(ar(h) for h in (g[4] if len(g) > 4 and g[4] else []))
    if g[0] == "r":
        return abs(g[3] - g[1]) * abs(g[4] - g[2])
    return None

M["fin"] = {k: list(v) for k, v in finishes.FIN.items()}
finq = collections.defaultdict(lambda: {"n": 0, "area": 0.0, "tower": 0.0})
for e in els:
    fl = (e.get("a") or {}).get("fin") or []
    for f in fl:
        finq[f]["n"] += 1
    if e["c"] in ("A.floor", "A.ceil", "A.site") and len(fl) == 1:
        a = poly_area_cm2(e["g"])
        if a is not None:
            finq[fl[0]]["area"] += a / 1e4
            if e["l"] in ("1", "2", "3", "4", "5"):
                finq[fl[0]]["tower"] += a / 1e4
# 'tower' = typical levels 1-5, 'area' = all levels (B/G/R use a generic room-kind -> finish mapping, see docs/PROGRESS.md)
M["finq"] = {k: {"n": v["n"], "area": round(v["area"], 1) if v["area"] > 0 else None, "tower": round(v["tower"], 1) if v["tower"] > 0 else None} for k, v in finq.items()}

# ------------------------------------------------------------------ RAL table supplied by the client
M["ral"] = {
    "note": "جدول أنظمة الدهان المرفق من العميل (RAL.xlsx). كل ألوان RAL فيه مكتوبة «RAL xxxx» أي غير محددة، فتبقى غير محددة هنا ولا تُخمَّن. "
            "التعارضات مع تعريف A500 المستخرج سابقًا موسومة بانتظار تأكيدك ولم تُحسم.",
    "rows": [
        {"code": "W2", "cat": "دهان داخلي", "space": "الشقق", "system": "Washable emulsion over plaster", "finish": "Matt", "ral": "RAL xxxx"},
        {"code": "W10", "cat": "دهان داخلي", "space": "غرف الخدمات", "system": "Semi epoxy over plaster", "finish": "Semi Gloss", "ral": "RAL xxxx",
         "flag": "تعارض: في A500 المستخرج W10 = دهان أكريليك مضاد للكربنة، وW5 = شبه إيبوكسي (معكوسان) — بانتظار تأكيدك"},
        {"code": "W5", "cat": "دهان داخلي", "space": "السلالم", "system": "Anti-carbonation acrylic", "finish": "Matt", "ral": "RAL xxxx",
         "flag": "تعارض: في A500 المستخرج W5 = بلاستر + دهان شبه إيبوكسي — بانتظار تأكيدك"},
        {"code": "W12", "cat": "دهان خارجي", "space": "واجهة المبنى", "system": "Weatherproof acrylic system", "finish": "Textured Matt", "ral": "RAL xxxx",
         "flag": "تعارض: في A500 المستخرج W12 = كسوة بورسلين 60×120، والدهان الأكريليك الخارجي هو W11 — بانتظار تأكيدك"},
        {"code": "W10", "cat": "دهان المواقف", "space": "جدران المواقف", "system": "Semi epoxy", "finish": "Semi Gloss", "ral": "RAL xxxx"},
        {"code": "CSP-3", "cat": "طلاء أرضيات المواقف", "space": "الممر", "system": "PU heavy-duty coating", "finish": "Anti-slip", "ral": "RAL xxxx",
         "flag": "A500 المستخرج يذكر CSP دون ترقيم فرعي (2/3/4) — بانتظار تأكيدك"},
        {"code": "CSP-2", "cat": "طلاء أرضيات المواقف", "space": "المنحدر", "system": "PU anti-slip coating", "finish": "Anti-slip", "ral": "RAL xxxx"},
        {"code": "CSP-4", "cat": "طلاء أرضيات المواقف", "space": "مواقف السيارات", "system": "PU deck coating", "finish": "Smooth finish", "ral": "RAL xxxx"},
        {"code": "CPF-1", "cat": "خطوط المواقف", "space": "خطوط المرور", "system": "Polyurethane line marking", "finish": "Gloss", "ral": "RAL xxxx"},
        {"code": "CPF-2", "cat": "خطوط المواقف", "space": "حجر البردورة", "system": "Road marking paint", "finish": "Gloss", "ral": "RAL xxxx"},
    ],
}

# ------------------------------------------------------------------ clash candidates
def shape_of(g):
    """-> list of (shapely geometry in plan cm, z0 m, z1 m)"""
    t = g[0]
    if t == "p":
        poly = Polygon(g[1], g[4] if len(g) > 4 and g[4] else [])
        if not poly.is_valid:
            poly = poly.buffer(0)
        return [(poly, g[2], g[3])]
    if t == "r":
        return [(box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4])), g[5], g[6])]
    if t == "cyl":
        return [(Point(g[1], g[2]).buffer(g[3], 8), g[4], g[5])]
    if t == "b":
        b = box(g[1] - g[3] / 2, g[2] - g[4] / 2, g[1] + g[3] / 2, g[2] + g[4] / 2)
        return [(shp_rotate(b, g[5], origin=(g[1], g[2])), g[6], g[7])]
    if t in ("d", "t"):
        out = []
        pts = g[1]
        for p, q in zip(pts, pts[1:]):
            if math.hypot(q[0] - p[0], q[1] - p[1]) < 0.5 and abs(q[2] - p[2]) < 0.02:
                continue
            if t == "d":
                half_w, half_h = g[2] / 2, g[3] / 200
            else:
                half_w, half_h = g[2] / 2, g[2] / 200
            if math.hypot(q[0] - p[0], q[1] - p[1]) < 0.5:   # vertical run
                out.append((Point(p[0], p[1]).buffer(half_w, 6), min(p[2], q[2]) - half_h * 0, max(p[2], q[2])))
            else:
                out.append((LineString([(p[0], p[1]), (q[0], q[1])]).buffer(half_w, cap_style=2),
                            min(p[2], q[2]) - half_h, max(p[2], q[2]) + half_h))
        return out
    return []

STRUCT = {"S.beam": "beam", "S.col": "col", "S.wall": "wall", "S.slab": "slab"}
KIND_AR = {
    "duct_beam": "مجرى هواء × جسر خرساني", "duct_col": "مجرى هواء × عمود", "duct_wall": "مجرى هواء × جدار خرساني / نواة", "duct_slab": "مجرى هواء × بلاطة",
    "pipe_beam": "أنبوب × جسر خرساني", "pipe_col": "أنبوب × عمود", "pipe_wall": "أنبوب × جدار خرساني / نواة",
    "equip_beam": "وحدة تكييف × جسر خرساني", "equip_col": "وحدة تكييف × عمود", "equip_wall": "وحدة تكييف × جدار خرساني / نواة",
    "duct_pipe": "مجرى هواء × أنبوب", "equip_pipe": "وحدة تكييف × أنبوب", "equip_duct": "وحدة تكييف × مجرى هواء",
}
S_items = []   # (geom, z0, z1, elementIndex, skind)
for i, e in enumerate(els):
    if e["c"] in STRUCT:
        for geom, z0, z1 in shape_of(e["g"]):
            if not geom.is_empty:
                S_items.append((geom, z0, z1, i, STRUCT[e["c"]]))
S_tree = STRtree([s[0] for s in S_items])

def mep_kind(e):
    c = e["c"]
    if c == "M.duct": return "duct"
    if c == "M.equip": return "equip"
    if c.startswith("P."): return "pipe"
    return None

MEP = []       # (geom, z0, z1, elementIndex, mkind)
for i, e in enumerate(els):
    k = mep_kind(e)
    if not k:
        continue
    for geom, z0, z1 in shape_of(e["g"]):
        if not geom.is_empty:
            MEP.append((geom, z0, z1, i, k))

MIN_AREA, MIN_Z = 4.0, 0.02
pairs = {}
def add_pair(a, b, kind, geom_area, zov, pt, z):
    key = (a, b)
    d = pairs.get(key)
    vol = geom_area * 1e-4 * zov
    if d is None:
        pairs[key] = {"a": a, "b": b, "k": kind, "v": vol, "best": vol, "pt": [pt[0], pt[1], z]}
    else:
        d["v"] += vol
        if vol > d["best"]:
            d["best"], d["pt"] = vol, [pt[0], pt[1], z]

# MEP vs structure
for geom, z0, z1, i, mk in MEP:
    for j in S_tree.query(geom):
        sg, sz0, sz1, si, sk = S_items[j]
        if mk == "pipe" and sk == "slab":
            continue                      # risers legitimately cross slabs
        zov = min(z1, sz1) - max(z0, sz0)
        if zov < MIN_Z:
            continue
        inter = geom.intersection(sg)
        if inter.is_empty or inter.area < MIN_AREA:
            continue
        c = inter.centroid
        add_pair(i, si, f"{mk}_{sk}", inter.area, zov, (c.x, c.y), (max(z0, sz0) + min(z1, sz1)) / 2)

# duct / equipment vs pipe, equipment vs duct
P_items = [m for m in MEP if m[4] == "pipe"]
P_tree = STRtree([m[0] for m in P_items])
for geom, z0, z1, i, mk in MEP:
    if mk not in ("duct", "equip"):
        continue
    for j in P_tree.query(geom):
        pg, pz0, pz1, pi, _ = P_items[j]
        zov = min(z1, pz1) - max(z0, pz0)
        if zov < MIN_Z:
            continue
        inter = geom.intersection(pg)
        if inter.is_empty or inter.area < MIN_AREA:
            continue
        c = inter.centroid
        add_pair(i, pi, f"{mk}_pipe", inter.area, zov, (c.x, c.y), (max(z0, pz0) + min(z1, pz1)) / 2)
D_items = [m for m in MEP if m[4] == "duct"]
D_tree = STRtree([m[0] for m in D_items])
for geom, z0, z1, i, mk in MEP:
    if mk != "equip":
        continue
    for j in D_tree.query(geom):
        dg, dz0, dz1, di, _ = D_items[j]
        zov = min(z1, dz1) - max(z0, dz0)
        if zov < MIN_Z:
            continue
        inter = geom.intersection(dg)
        if inter.is_empty or inter.area < MIN_AREA:
            continue
        c = inter.centroid
        add_pair(i, di, "equip_duct", inter.area, zov, (c.x, c.y), (max(z0, dz0) + min(z1, dz1)) / 2)

# MEP-vs-MEP crossings are dominated by tiny pipe/duct overlaps whose elevations are both assumed: keep only the significant ones
MIN_VOL = {"duct_pipe": 0.005, "equip_pipe": 0.001, "equip_duct": 0.001}
clashes = []
for d in pairs.values():
    if d["v"] < MIN_VOL.get(d["k"], 0.0):
        continue
    x, y, z = d["pt"]
    clashes.append({"a": d["a"], "b": d["b"], "k": d["k"], "l": els[d["a"]]["l"], "v": round(d["v"], 3), "pt": [round(x / 100, 2), round(z, 2), round(-y / 100, 2)]})
clashes.sort(key=lambda c: -c["v"])
M["clashes"] = clashes
import clash_log as _CL
_CL.merge_into(M, els)
_CL.write_doc(M)
M["clashKinds"] = {k: v for k, v in KIND_AR.items() if any(c["k"] == k for c in clashes)}
M["clashNote"] = ("تعارضات هندسية مرجّحة (تقاطع الحجوم) بين عناصر النموذج. مناسيب الخدمات في فراغ السقف افتراضية (انظر بطاقة كل عنصر)، "
                  "لذلك هي مرشّحات للمراجعة وليست حكمًا نهائيًا. ثقوب العبور عبر الجدران والجسور لا تظهر في النموذج وقد تكون مصمَّمة فعلًا. "
                  "مرتبة بحجم التداخل.")

json.dump(M, open(SRC, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
cnt = collections.Counter(c["k"] for c in clashes)
print("types", len(types), "| fin", len(M["fin"]), "| clashes", len(clashes), dict(cnt), "|", round(os.path.getsize(SRC) / 1e6, 2), "MB")
