# -*- coding: utf-8 -*-
"""Residential facade windows rebuilt from the approved window schedule (ARCH2 p14-15: A801 CW-07..CW-14, A802 CW-15..CW-19) and the wall section A1500.

What the approved sheets say (read from the drawings, checked on 2026-10-05):
  * every apartment window is 250 cm high: bottom row 60 + middle row 140 + top row 50, standing on a 60 cm block-work upstand with porcelain cladding (A1500: 60 + 250 = 310 clear height, floor-to-floor 350, slab 40)
  * cells: F = fixed vision glass, S = spandrel (non-vision) glass, a V symbol = hinged vent
  * powder-coated aluminium frame, Light Beige; reflective double-glazed glass 6-12-6 mm, Light Brown
  * CW-19 (stair window, 120 cm wide) is one continuous element 20.65 m high: 130 S, 100 S, 150 F, ... 185 F (from the top); its fixed panels centre on the landings of every floor
The elevations are drawn from outside, left to right (CW-08 on the north wall and CW-09 on the south wall are mirror images and their vents land on the same x).

modules() extracts the old window modules once (data/win_modules.json) so the rebuild stays idempotent: post_model removes the old window elements, build() emits the new ones.
"""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
MODS = os.path.join(HERE, "data", "win_modules.json")

# cols = widths left->right seen from outside (cm); rows bottom -> top; F fixed, S spandrel, V hinged vent
PAT = {
    "CW-07": dict(cols=[125, 130], bot="FF", mid="VF", top="SS"),
    "CW-08": dict(cols=[130, 125], bot="SS", mid="VS", top="SS"),
    "CW-09": dict(cols=[125, 130], bot="SS", mid="SV", top="SS"),
    "CW-10": dict(cols=[110] * 7, bot="SSFFSFF", mid="VSVFSFV", top="S" * 7),
    "CW-11": dict(cols=[110] * 7, bot="FFSFFSS", mid="VFSFVSV", top="S" * 7),
    "CW-12": dict(cols=[100] * 3, bot="SSS", mid="SSS", top="SSS"),
    "CW-13": dict(cols=[105, 110, 105, 105], bot="FFSS", mid="FVSS", top="SSSS"),
    "CW-14": dict(cols=[105, 110, 105, 105], bot="SFFS", mid="SVFS", top="SSSS"),
    "CW-15": dict(cols=[80, 90, 90], bot="SFF", mid="SVF", top="SSS"),
    "CW-16": dict(cols=[90, 90, 80], bot="FFS", mid="FVS", top="SSS"),
    "CW-17": dict(cols=[120, 110, 120], bot="SSS", mid="SVS", top="SSS"),
    "CW-18": dict(cols=[120, 110, 130], bot="SSS", mid="SVS", top="SSS"),
}
ROWS = (("bot", 0.60, 1.20), ("mid", 1.20, 2.60), ("top", 2.60, 3.12))      # z above FFL; sill below 0.60
SILL_H = 0.60
# CW-19, bottom -> top (cm): F185 S100 F150 S100 S100 F150 ... S100 S130  (starts 10 cm under the first floor finish = slab top)
CW19 = [("F", 185), ("S", 100), ("F", 150), ("S", 100), ("S", 100), ("F", 150), ("S", 100), ("S", 100), ("F", 150), ("S", 100), ("S", 100), ("F", 150),
        ("S", 100), ("S", 100), ("F", 150), ("S", 100), ("S", 130)]

FRAME_W = 5.0        # cm face width of mullions / rails
FRAME_D = 8.0        # cm depth of the frame
GLASS_T = 3.0        # cm
SILL_D = 20.0        # cm upstand depth (block + 2 cm porcelain outside)
CLAD_T = 2.0

MATS = {
    "frame_alu": {"name": "إطار ألمنيوم مطلي بالمسحوق — بيج فاتح (Light Beige)", "color": "#d6c7a6", "code": "A800–A802", "rough": 0.45, "metal": 0.35},
    "glass_vis": {"name": "زجاج مزدوج عاكس 6-12-6 مم — بني فاتح (Light Brown) — ثابت/مفصلي", "color": "#a58a6b", "opacity": 0.40, "code": "A800–A802", "rough": 0.06, "metal": 0.35},
    "glass_span": {"name": "زجاج سبانديرل (غير شفاف) — بني فاتح عاكس", "color": "#7a6b5a", "opacity": 0.96, "code": "A800–A802", "rough": 0.12, "metal": 0.30},
    "sill_block": {"name": "عتبة بلوك 60 سم — لياسة داخلية بيضاء", "color": "#eeeae2", "code": "A1500"},
    "win_handle": {"name": "مقبض نافذة مفصلية (ستانلس)", "color": "#9aa0a6", "code": "A800–A802", "metal": 0.8, "rough": 0.3},
}


def modules(M):
    """old-style window modules -> list of dicts (saved once to data/win_modules.json)"""
    if os.path.exists(MODS):
        return json.load(open(MODS, encoding="utf-8"))
    by = collections.defaultdict(list)
    for e in M["els"]:
        if e["c"] == "A.win" and e["t"].startswith("win_CW-") and e["t"] != "win_CW-G" and e.get("grp"):
            by[e["grp"]].append(e)
    out = []
    for grp, els in sorted(by.items()):
        vis = next((e for e in els if e["m"] == "glass_vis" and not (e.get("a") or {}).get("part")), None)
        if not vis: continue
        g = vis["g"]; a = vis.get("a") or {}
        out.append({"grp": grp, "t": vis["t"], "l": vis["l"], "side": a.get("side"), "x0": min(g[1], g[3]), "y0": min(g[2], g[4]), "x1": max(g[1], g[3]), "y1": max(g[2], g[4]),
                    "u": vis.get("u"), "u2": vis.get("u2"), "w": a.get("w_cm"), "h": a.get("h_cm"), "loc": a.get("loc")})
    json.dump(out, open(MODS, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    return out


def is_old(e):
    return e["c"] == "A.win" and e["t"].startswith("win_CW-") and e["t"] != "win_CW-G" and bool(e.get("grp")) and "-X" not in e["id"][-6:]


def _frame(mod):
    """local frame of a module: origin (left end on the facade line), unit vector along the facade (left->right seen from outside), outward normal"""
    s = mod["side"]; x0, y0, x1, y1 = mod["x0"], mod["y0"], mod["x1"], mod["y1"]
    if s == "S": return (x0, (y0 + y1) / 2), (1, 0), (0, -1), x1 - x0
    if s == "N": return (x1, (y0 + y1) / 2), (-1, 0), (0, 1), x1 - x0
    if s == "E": return ((x0 + x1) / 2, y0), (0, 1), (1, 0), y1 - y0
    return ((x0 + x1) / 2, y1), (0, -1), (-1, 0), y1 - y0          # W


def _box(o, u, n, a0, a1, d0, d1, z0, z1):
    """axis-aligned rectangle element 'r' from local coords: along [a0,a1], depth (outward) [d0,d1] cm, z [z0,z1] m"""
    pts = []
    for al, de in ((a0, d0), (a1, d1)):
        pts.append((o[0] + u[0] * al + n[0] * de, o[1] + u[1] * al + n[1] * de))
    x0 = min(p[0] for p in pts); x1 = max(p[0] for p in pts); y0 = min(p[1] for p in pts); y1 = max(p[1] for p in pts)
    return ["r", round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1), round(z0, 3), round(z1, 3)]


def build(M):
    """new window elements (extras format) + materials"""
    L = {l["id"]: l for l in M["levels"]}
    mods = modules(M)
    els = []

    def add(mod, geom, mat, part, typ=None, extra=None, stage=False):
        a = {"w_cm": mod["w"], "h_cm": mod["h"], "loc": mod["loc"], "side": mod["side"], "part": part}
        if extra: a.update(extra)
        e = {"c": "A.win", "l": mod["l"], "g": geom, "mark": mod["t"][4:], "t": typ or mod["t"], "m": mat, "a": a,
             "src": [f"ARCH2 ص14–15 (A801/A802 جداول النوافذ {mod['t'][4:]})", "ARCH2 ص31 (A1500 مقطع الجدار 01: عتبة 60 + نافذة 250 = 310)"], "grp": mod["grp"]}
        if mod.get("u"): e["u"] = mod["u"]
        if mod.get("u2"): e["u2"] = mod["u2"]
        els.append(e)

    for mod in mods:
        code = mod["t"][4:]
        o, u, n, length = _frame(mod)
        ffl = L[mod["l"]]["ffl"]
        # ---------------- the continuous stair window: one module for levels 1..R at level '1'
        if code == "CW-19":
            if mod["l"] != "1":
                continue
            z = L["1"]["ffl"] - 0.10
            run = []
            for kind, h in CW19:
                run.append((kind, z, z + h / 100.0)); z += h / 100.0
            m19 = dict(mod, h=round((z - (L["1"]["ffl"] - 0.10)) * 100)); m19["w"] = 120
            add(m19, _box(o, u, n, 0, FRAME_W, -FRAME_D / 2, FRAME_D / 2, run[0][1], z), "frame_alu", "frame")
            add(m19, _box(o, u, n, length - FRAME_W, length, -FRAME_D / 2, FRAME_D / 2, run[0][1], z), "frame_alu", "frame")
            for kind, za, zb in run:
                add(m19, _box(o, u, n, FRAME_W, length - FRAME_W, -GLASS_T / 2, GLASS_T / 2, za + 0.025, zb - 0.025), "glass_vis" if kind == "F" else "glass_span", "glass" if kind == "F" else "spandrel")
                add(m19, _box(o, u, n, 0, length, -FRAME_D / 2, FRAME_D / 2, zb - 0.025, zb + 0.025), "frame_alu", "frame")
            continue
        pat = PAT.get(code)
        if not pat: continue
        cols = pat["cols"]
        scale = length / float(sum(cols))                      # tolerance only (the sums match the drawing to the centimetre)
        edges = [0.0]
        for w in cols: edges.append(edges[-1] + w * scale)
        z0 = ffl + SILL_H
        # sill: block core (inside plaster) + porcelain face outside
        add(mod, _box(o, u, n, 0, length, -SILL_D / 2, SILL_D / 2 - CLAD_T, ffl, z0), "sill_block", "sill", typ="win_sill",
            extra={"note": "عتبة بلوك 60 سم تحت النافذة (A1500)"})
        add(mod, _box(o, u, n, 0, length, SILL_D / 2 - CLAD_T, SILL_D / 2, ffl, z0), "clad_porc", "sill", typ="win_sill", extra={"fin": ["W12"]})
        # frame: perimeter + mullions at every column edge + rails at every row edge
        for k, x in enumerate(edges):
            a0 = max(0.0, x - FRAME_W / 2) if 0 < k < len(edges) - 1 else (0.0 if k == 0 else length - FRAME_W)
            a1 = a0 + FRAME_W
            add(mod, _box(o, u, n, a0, a1, -FRAME_D / 2, FRAME_D / 2, z0, ffl + 3.12), "frame_alu", "frame")
        for zr in (0.60, 1.20, 2.60):
            add(mod, _box(o, u, n, 0, length, -FRAME_D / 2, FRAME_D / 2, ffl + zr - 0.025 + (0.025 if zr == 0.60 else 0), ffl + zr + 0.025 + (0.025 if zr == 0.60 else 0)), "frame_alu", "frame")
        add(mod, _box(o, u, n, 0, length, -FRAME_D / 2, FRAME_D / 2, ffl + 3.07, ffl + 3.12), "frame_alu", "frame")
        # glass: consecutive cells of the same kind in a row are one plate
        for row, za, zb in ROWS:
            kinds = pat[row]; k = 0
            while k < len(kinds):
                j = k
                while j + 1 < len(kinds) and kinds[j + 1] == kinds[k]: j += 1
                a0 = edges[k] + FRAME_W / 2; a1 = edges[j + 1] - FRAME_W / 2
                za2 = ffl + za + (0.05 if row == "bot" else 0.025); zb2 = ffl + (3.07 if row == "top" else zb - 0.025)
                kind = kinds[k]
                if kind == "S":
                    add(mod, _box(o, u, n, a0, a1, -GLASS_T / 2, GLASS_T / 2, za2, zb2), "glass_span", "spandrel")
                else:
                    add(mod, _box(o, u, n, a0, a1, -GLASS_T / 2, GLASS_T / 2, za2, zb2), "glass_vis", "glass" if kind == "F" else "vent_glass",
                        extra=({"operation": "مفصلية Hinged"} if kind == "V" else {"operation": "ثابتة Fixed"}))
                    if kind == "V":                                   # hinged vent: sash frame on both faces and a handle inside
                        for aa, bb in ((a0, a0 + 3), (a1 - 3, a1)):
                            add(mod, _box(o, u, n, aa, bb, 1.5, 3.0, za2, zb2), "frame_alu", "sash")
                            add(mod, _box(o, u, n, aa, bb, -3.0, -1.5, za2, zb2), "frame_alu", "sash")
                        for zz0, zz1 in ((za2, za2 + 0.03), (zb2 - 0.03, zb2)):
                            add(mod, _box(o, u, n, a0, a1, 1.5, 3.0, zz0, zz1), "frame_alu", "sash")
                            add(mod, _box(o, u, n, a0, a1, -3.0, -1.5, zz0, zz1), "frame_alu", "sash")
                        am = (a0 + a1) / 2
                        add(mod, _box(o, u, n, am - 1.5, am + 1.5, -7.0, -3.0, ffl + 1.80, ffl + 2.00), "win_handle", "handle")
                k = j + 1
    return {"els": els, "mats": MATS}


def types(M):
    out = {}
    names = {"F": "ثابت", "S": "سبانديرل (غير شفاف)", "V": "مفصلي"}
    for code, pat in PAT.items():
        def row(r): return " ".join(names[c] for c in pat[r])
        out["win_" + code] = {
            "n": f"نافذة {code} — شبكة الخلايا حسب A801/A802", "cf": "doc",
            "sp": [["الارتفاع", "250 سم: صف سفلي 60 + أوسط 140 + علوي 50 فوق عتبة بلوك 60 سم (A1500)"],
                   ["الأعمدة (من اليسار لليمين كما تُرى من الخارج)", " + ".join(str(w) for w in pat["cols"]) + f" = {sum(pat['cols'])} سم"],
                   ["الصف العلوي 50 سم", row("top")], ["الصف الأوسط 140 سم", row("mid")], ["الصف السفلي 60 سم", row("bot")],
                   ["الإطار", "ألمنيوم مطلي بالمسحوق — بيج فاتح (Light Beige)"], ["الزجاج", "مزدوج عاكس 6-12-6 مم — بني فاتح (Light Brown)"]],
            "asm": ["عرض الإطار 5 سم وعمقه 8 سم وشكل المقبض افتراض بصري", "اتجاه الفتح الفعلي للخلية المفصلية (علوي/سفلي) غير محدد في الرمز V — بانتظار تأكيدك"],
            "sr": ["ARCH2 ص14–15 (A801/A802 جداول النوافذ)", "ARCH2 ص31 (A1500 مقطع الجدار 01)", "BOQ 8.4.1"]}
    out["win_CW-19"] = {
        "n": "نافذة السلم CW-19 — عنصر واحد متصل 20.65 م", "cf": "doc",
        "sp": [["العرض", "120 سم"], ["التسلسل من الأعلى", "130 S، 100 S، 150 F، ثم (100 S، 100 S، 150 F) ×4، ثم 100 S و185 F"], ["اللوحات الثابتة 150", "تتمركز عند مستوى كل طابق (ممرات السلم)"],
               ["الإطار والزجاج", "بيج فاتح / بني فاتح عاكس 6-12-6 مم"]],
        "asm": ["بداية النافذة 10 سم تحت أرضية الدور الأول (فوق سطح البلاطة 5.65) افتراض من تطابق المناسيب"], "sr": ["ARCH2 ص15 (A802 CW-19)"]}
    out["win_sill"] = {
        "n": "عتبة النافذة — بلوك 60 سم بكسوة بورسلين", "cf": "doc",
        "sp": [["الارتفاع", "60 سم فوق أرضية الغرفة المنتهية (A1500: 60 + 250 = 310 ارتفاعًا صافيًا)"], ["العمق", "20 سم: بلوك بلياسة بيضاء من الداخل + بورسلين W12 سماكة 2 سم من الخارج"]],
        "asm": ["عمق العتبة 20 سم تقدير من مقطع A1500 (1:50)"], "sr": ["ARCH2 ص31 (A1500 مقطع الجدار 01 — «BLOCK WORK / PORCELAIN CLADDING»)"]}
    return out
