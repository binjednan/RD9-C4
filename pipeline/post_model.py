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
    for k, e in enumerate(S_["els"], 1):
        ne = {"id": f"A.site-G-S{k:03d}", "c": e["c"], "l": e["l"], "g": e["g"], "mark": e["mark"], "t": e["t"], "m": e["m"], "a": e["a"], "s": [sp_idx(t) for t in e["src"]]}
        if e.get("stage"): ne["stage"] = e["stage"]
        els.append(ne)
    M["els"] = els
    print("site elements merged:", len(S_["els"]))

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
    els[:] = [e for e in els if not re.search(r"-M\d+$", e["id"])]
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
        tol = 60 if (e["t"] in BIG or (e["l"] == "G" and STAIR03[0] <= e["g"][1] <= STAIR03[2] and STAIR03[1] <= e["g"][2] <= STAIR03[3])) else 25
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
