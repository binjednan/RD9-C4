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
import json, os, sys, collections, math
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
    if e["c"] in ("A.floor", "A.ceil") and len(fl) == 1:
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
M["clashKinds"] = {k: v for k, v in KIND_AR.items() if any(c["k"] == k for c in clashes)}
M["clashNote"] = ("تعارضات هندسية مرجّحة (تقاطع الحجوم) بين عناصر النموذج. مناسيب الخدمات في فراغ السقف افتراضية (انظر بطاقة كل عنصر)، "
                  "لذلك هي مرشّحات للمراجعة وليست حكمًا نهائيًا. ثقوب العبور عبر الجدران والجسور لا تظهر في النموذج وقد تكون مصمَّمة فعلًا. "
                  "مرتبة بحجم التداخل.")

json.dump(M, open(SRC, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
cnt = collections.Counter(c["k"] for c in clashes)
print("types", len(types), "| fin", len(M["fin"]), "| clashes", len(clashes), dict(cnt), "|", round(os.path.getsize(SRC) / 1e6, 2), "MB")
