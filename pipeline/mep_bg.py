# -*- coding: utf-8 -*-
"""Fire-fighting network of the basement (B), ground (G) and roof (R) levels + the FFC (hose-cabinet) line of every level + the vertical risers
between levels  ->  pipeline/data/mep_bg.json   (needs the source PDFs, see lib.py; post_model.py merges the json)

Why: model.json only had the sprinkler network of the 1st..5th floors, so the fire-fighting system stopped at the 1st floor ("not connected to
the level before it").  The drawings show (MECH2 pages 10-14, FF-105 riser diagram):
  * sprinkler network (layer M_FF_PIPE) and a separate FFC line (layer M_FF_FFC, 6" per FF-105) on every level;
  * four 6" riser circles drawn at the SAME plan position on consecutive levels:
        A1 (835,771) sprinkler + A2 (860,771) FFC   G -> 1 -> 2..5 -> R     ("RISER-F/B-T/A")
        B1 (1088,1111) sprinkler + B2 (1088,1086) FFC   B -> G              ("RISER-F/A", "RISER-T/B")
        S1 (392,1117), S2 (361,1522)  suction lines   B tanks -> G pump room ("SUCTION LINE-F/B", "-T/A")
Everything that is not drawn (pipe elevation above the ceiling, riser end elevations) is flagged as an assumption on the element.
"""
import sys, os, json, math, re, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib, geo, mep_common as MC, pipes as PP, plumb
import assemble_arch as AA
import glyphs as G

# level -> (MECH2 FF page, ARCH1 reference page)
PAGE = {"B": (10, 4), "G": (11, 5), "1": (12, 6), "2": (13, 7), "3": (13, 7), "4": (13, 7), "5": (13, 7), "R": (14, 8)}
ORDER = ["B", "G", "1", "2", "3", "4", "5", "R"]
FFL = {l: AA.FFL[l] for l in ORDER}
FOOT = {"B": (-30, -30, 4440, 4440), "G": (-30, -100, 3230, 1900)}
FOOT.update({l: (60, -100, 3230, 1900) for l in ("1", "2", "3", "4", "5", "R")})
Z_SPR, Z_FFC = 2.98, 2.85          # pipe axis above the floor (sprinkler: same as the typical floors; FFC lower to avoid touching the sprinkler pipes) — assumptions
R_DZ = -0.12                        # roof rooms are 3.05 m high: keep the void pipes under the T slab
SHEET = lambda pg: f"MECH2 ص{pg}"
els = []

def z_of(level, kind):
    z = FFL[level] + (Z_SPR if kind == "spr" else Z_FFC)
    if level == "R": z += R_DZ
    return round(z, 3)

def add(c, level, g, mark=None, typ=None, mat="conc", attrs=None, src=None, grp=None):
    e = {"c": c, "l": level, "g": g, "mark": mark, "t": typ, "m": mat, "a": attrs or {}, "src": src or []}
    if grp: e["grp"] = grp
    els.append(e)

def inside(level, pl):
    x0, y0, x1, y1 = FOOT[level]
    return all(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for p in pl)

def clean(pipes):
    """drop flow-arrow heads / valve glyphs / leader ticks that the layer extraction returns as 'pipes' (see glyphs.py)"""
    fl = G.flags([p["pl"] for p in pipes])
    return [p for p, f in zip(pipes, fl) if not f], sum(fl)

# ------------------------------------------------------------------------------------------------------------------ extraction
def sprinkler_level(level):
    pg, ref = PAGE[level]
    R = plumb.extract_ff(pg, ref)
    R["pipes"] = [p for p in R["pipes"] if inside(level, p["pl"])]
    R["pipes"], bad = clean(R["pipes"])
    R["heads"] = [h for h in R["heads"] if FOOT[level][0] <= h["x"] <= FOOT[level][2] and FOOT[level][1] <= h["y"] <= FOOT[level][3]]
    shift = R_DZ if level == "R" else 0.0
    ffl = FFL[level]
    def add_(cat, lv, g, mark=None, typ=None, mat="conc", attrs=None, u=None, u2=None, src=None):
        if shift and typ != "fhc":
            for p_ in (g[1] if g[0] == "t" else []): p_[2] = round(p_[2] + shift, 3)
            if g[0] == "cyl": g[4] = round(g[4] + shift, 3); g[5] = round(g[5] + shift, 3)
        s = list(src or [])
        if typ in ("pipe_ff",): s.append("منسوب التمديد فوق الأرضية: افتراض (فراغ السقف المستعار)")
        add(cat, lv, g, mark=mark, typ=typ, mat=mat, attrs=attrs, src=s)
    n = plumb.emit_ff(lambda cat, lv, g, **kw: add_(cat, lv, g, **kw), level, R, None, ffl)
    print(f"  sprinkler network {level}: {n} elements (glyph fragments dropped: {bad})")

def ffc_pipes(level):
    """FFC line: layer M_FF_FFC polylines (no size on the plans: 6\" from the riser diagram FF-105)."""
    pg, ref = PAGE[level]
    sh = lib.Sheet("MECH2", pg, ref=lib.Sheet("ARCH1", ref))
    segs = plumb.drop_short_diag(PP.axis_merge(PP.layer_segments(sh, ("M_FF_FFC",), min_poly_len=6.0), gap=6))
    pls = plumb._polys_from_segs([(a, b, 150) for a, b in segs], 150)
    out = [{"d": 150, "pl": pl} for d, pl, _ in pls if inside(level, pl)]
    out, bad = clean(out)
    return out, bad, sh

RISERS = []      # detected riser circles: {kind, x, y, levels:{level:(x,y)}}

def riser_circles(level):
    """15.7 cm (6") circles of M_FF_PIPE / M_FF_FFC = riser symbols (plan view of a vertical 6\" pipe)"""
    pg, ref = PAGE[level]
    sh = lib.Sheet("MECH2", pg, ref=lib.Sheet("ARCH1", ref))
    res = []
    for d in sh.D:
        ly = d["layer"] or ""
        if ly not in ("M_FF_PIPE", "M_FF_FFC"): continue
        pts = [sh.T(x, y) for pl in d["polys"] for x, y in pl]
        if len(pts) < 8: continue
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        w = max(xs) - min(xs); h = max(ys) - min(ys)
        if 14 <= w <= 18 and 14 <= h <= 18 and abs(w - h) < 2 and not d.get("fill") and -50 < min(xs) < 4500:
            res.append({"layer": ly, "x": (min(xs) + max(xs)) / 2, "y": (min(ys) + max(ys)) / 2})
    return res

def build_risers(circles):
    """join circles at the same plan position (±12 cm) on consecutive levels into vertical pipes"""
    groups = []
    for lv in ORDER:
        for c in circles.get(lv, []):
            for g in groups:
                if g["layer"] == c["layer"] and math.hypot(g["x"] - c["x"], g["y"] - c["y"]) <= 12 and lv not in g["levels"]:
                    g["levels"][lv] = (c["x"], c["y"]); break
            else:
                groups.append({"layer": c["layer"], "x": c["x"], "y": c["y"], "levels": {lv: (c["x"], c["y"])}})
    return groups

def emit_risers(groups):
    n = 0
    for k, g in enumerate(groups):
        lvs = [l for l in ORDER if l in g["levels"]]
        if len(lvs) < 2: continue
        xs = [g["levels"][l][0] for l in lvs]; ys = [g["levels"][l][1] for l in lvs]
        x, y = sum(xs) / len(xs), sum(ys) / len(ys)
        kind = "spr" if g["layer"] == "M_FF_PIPE" else "ffc"
        suction = (x < 500 and kind == "spr")
        for lo, hi in zip(lvs[:-1], lvs[1:]):
            if ORDER.index(hi) - ORDER.index(lo) != 1: continue
            if suction:
                z0 = round(FFL[lo] + 0.30, 3); z1 = round(FFL[hi] + 0.60, 3)
                nm, typ, mat, grp = "خط شفط الخزان → مضخات الإطفاء", "pipe_suction", "p_ff", f"FF-SUCTION-{int(round(y))}"
                src = [f"{SHEET(10)} و{SHEET(11)}: دائرة أنبوب 6″ بنفس الموقع (SUCTION LINE-T/A و F/B)", "منسوب بداية الخط في الخزان ونهايته عند المضخات: افتراض هندسي يحتاج تأكيد"]
            else:
                z0, z1 = z_of(lo, kind), z_of(hi, kind)
                nm = "رايزر شبكة الرشاشات 6″" if kind == "spr" else "رايزر خط صناديق الإطفاء FFC 6″"
                typ, mat = ("riser_spr", "p_ff") if kind == "spr" else ("riser_ffc", "p_ffc_line")
                grp = f"FF-RISER-{'SPR' if kind == 'spr' else 'FFC'}-{int(round(x))}-{int(round(y))}"
                src = [f"{SHEET(PAGE[lo][0])} و{SHEET(PAGE[hi][0])}: رمز رايزر 6″ (دائرة قطرها 15.7 سم على طبقة {g['layer']}) بنفس الإحداثي على الطابقين",
                       "الوسوم: «6″Ø DRY RISER / WET RISER» + مخطط الأعمدة الرأسية FF-105؛ تخصيص الجاف/الرطب لأي دائرتين غير مرسوم — بانتظار تأكيدك"]
            lvl = hi                                                  # a riser interval is assigned to the upper level (most of its height lies there)
            add("P.ff", lvl, ["t", [[round(x, 1), round(y, 1), z0], [round(x, 1), round(y, 1), z1]], 15.0], mark=f"{lo}→{hi}", typ=typ, mat=mat,
                attrs={"dia_mm": 150, "length_m": round(z1 - z0, 2), "from_level": lo, "to_level": hi, "x_cm": round(x), "y_cm": round(y),
                       "riser_note": "نهايتا الأنبوب عند منسوب خط التوزيع الأفقي في الطابقين؛ المنسوب فوق الأرضية افتراض" },
                src=src, grp=grp); n += 1
    return n


# ------------------------------------------------------------------------------------------------------------------ cabinets (FHC) from the architectural recess layer
def fhc_cabinets(level):
    """fire-hose cabinets: the filled U-shaped recess (~32 x 88 cm) on the xref layer '...$FHC' of the FF sheets (the plan symbol has no size of its own)"""
    pg, ref = PAGE[level]
    sh = lib.Sheet("MECH2", pg, ref=lib.Sheet("ARCH1", ref))
    out = []
    for d in sh.D:
        if not (d["layer"] or "").endswith("FHC") or not d.get("fill"): continue
        pts = [sh.T(x, y) for pl in d["polys"] for x, y in pl]
        if len(pts) < 8: continue
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        w, h = max(xs) - min(xs), max(ys) - min(ys)
        if 25 <= min(w, h) <= 40 and 70 <= max(w, h) <= 100:
            out.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, w, h))
    return out

# ------------------------------------------------------------------------------------------------------------------ ventilation / AC (B, G)
def ac_level(level, pg, ref):
    import hvac
    R = hvac.extract_ac(pg, ref)
    fx0, fy0, fx1, fy1 = FOOT[level]
    inb = lambda x, y: fx0 <= x <= fx1 and fy0 <= y <= fy1
    R["fcus"] = [f for f in R["fcus"] if inb(f["x"], f["y"])]
    R["duct_segs"] = [d for d in R["duct_segs"] if inb(*d["a"]) and inb(*d["b"])]
    for k in ("sad", "rad", "sag", "rag", "dam", "therm"):
        R[k] = [s for s in R[k] if inb(s["x"], s["y"])]
    n = hvac.emit_ac(lambda c, lv, g, **kw: add(c, lv, g, mark=kw.get("mark"), typ=kw.get("typ"), mat=kw.get("mat"), attrs=kw.get("attrs"), src=kw.get("src")),
                     level, R, None, FFL[level], floor_label=level)
    print(f"  AC layout {level}: {n} elements ({len(R['fcus'])} FCU)")

# ------------------------------------------------------------------------------------------------------------------ chilled water pipes (B, G, 1, typical)
def chw_level(level, pg, ref):
    sh = lib.Sheet("MECH1", pg, ref=lib.Sheet("ARCH1", ref))
    labs = []
    for sp in MC.spans(sh, "M_HVAC_TEXT"):
        m = re.search(r"(\d{2,3})\s*mm", sp["s"])
        if m: labs.append({"v": (int(m.group(1)),), "x": sp["X"], "y": sp["Y"], "s": sp["s"]})
    n = 0; dropped = 0
    for name, layers, typ, mat, dz, nm, gp in (("S", ("M_CHI_S",), "pipe_chws", "m_chws", 2.80, "تغذية", 8), ("R", ("M_CHI_R",), "pipe_chwr", "m_chwr", 2.74, "رجوع", 14)):   # the return line is drawn dashed (25 cm dash, 12.5 cm gap)
        segs = plumb.drop_short_diag(PP.axis_merge(PP.layer_segments(sh, layers), gap=gp))
        sized = PP.assign_sizes(segs, labs)
        pls = [(d, pl, lab) for d, pl, lab in plumb._polys_from_segs(sized, 20) if geo.polyline_len(pl) >= 6 and inside(level, pl)]
        fl = G.flags([pl for d, pl, lab in pls]); dropped += sum(fl)
        for (d, pl, labeled), f in zip(pls, fl):
            if f: continue
            add("M.pipe", level, ["t", [[round(p[0], 1), round(p[1], 1), round(FFL[level] + dz, 3)] for p in pl], round(max(d / 10.0, 2.2), 1)], typ=typ, mat=mat,
                attrs={"dia_mm": d, "length_m": round(geo.polyline_len(pl) / 100, 2), "dia_note": "من وسم المخطط" if labeled else "افتراضي 20 مم (قطر فروع FCU في جدول التكييف)", "kind": nm},
                src=[f"MECH1 ص{pg} طبقة {layers[0]} (مياه مبردة — {nm})", "منسوب الأنابيب في فراغ السقف المستعار: افتراض"]); n += 1
    print(f"  CHW pipes {level}: {n} (glyphs dropped {dropped})")

# ------------------------------------------------------------------------------------------------------------------ cold/hot water supply (B, G, R)
def ws_level(level, pg, ref):
    R = plumb.extract_ws(pg, ref)
    nd = 0
    for key in ("cold", "hot"):
        P = [p for p in R[key] if inside(level, p["pl"])]
        fl = G.flags([p["pl"] for p in P]); nd += sum(fl)
        R[key] = [p for p, f in zip(P, fl) if not f]
    R["heaters"] = [h for h in R["heaters"] if FOOT[level][0] <= h["x"] <= FOOT[level][2] and FOOT[level][1] <= h["y"] <= FOOT[level][3]]
    R["valves"] = [v for v in R["valves"] if FOOT[level][0] <= v["x"] <= FOOT[level][2] and FOOT[level][1] <= v["y"] <= FOOT[level][3]]
    ffl = FFL[level]; dz = R_DZ if level == "R" else 0.0
    def add_(cat, lv, g, mark=None, typ=None, mat="conc", attrs=None, u=None, u2=None, src=None):
        if dz and g[0] == "t":
            for p_ in g[1]: p_[2] = round(p_[2] + dz, 3)
        add(cat, lv, g, mark=mark, typ=typ, mat=mat, attrs=attrs, src=src)
    n = plumb.emit_ws(add_, level, R, None, ffl)
    print(f"  water supply {level}: {n} elements (glyphs dropped {nd})")

# ------------------------------------------------------------------------------------------------------------------ drainage (B, G low + high level, R)
DR_Z = {  # level/page -> (soil z, waste z, vent z) relative to the floor — assumptions: B pipes buried in the 20 cm screed above the raft, G low-level pipes hung under the 35 cm G slab
    "B": (-0.12, -0.09, 2.90), "G": (-0.98, -0.93, 2.95), "G-high": (2.78, 2.82, 2.95), "R": (-0.50, -0.46, 2.85)}
def dr_level(level, pg, ref, tag=None):
    R = plumb.extract_dr(pg, ref)
    key_z = DR_Z[tag or level]
    nd = 0; n = 0
    sheet = f"MECH2 ص{pg}"
    ffl = FFL[level]
    for key, typ, mat, z, ly in (("soil", "pipe_soil", "p_soil", ffl + key_z[0], "M_DR_SP"), ("waste", "pipe_waste", "p_waste", ffl + key_z[1], "M_DR_WP"), ("vent", "pipe_vent", "p_vent", ffl + key_z[2], "M_DR_VP")):
        P = [p for p in R[key] if inside(level, p["pl"])]
        fl = G.flags([p["pl"] for p in P]); nd += sum(fl)
        for p, f in zip(P, fl):
            if f: continue
            add("P.drain", level, plumb._tube(p["pl"], z, p["d"]), typ=typ, mat=mat,
                attrs={"dia_mm": p["d"], "length_m": round(geo.polyline_len(p["pl"]) / 100, 2), "dia_note": "افتراضي حسب نوع الخط (التسميات بالبوصة عند الأعمدة فقط)"},
                src=[f"{sheet} طبقة {ly}", "منسوب الصرف: افتراض" + (" (مخطط «المستوى العالي» — داخل فراغ سقف الأرضي)" if tag == "G-high" else "")]); n += 1
    for key, typ, txt in (("ft", "floor_trap", "FT"), ("co", "cleanout", "CO")):
        for s in R[key]:
            if not (FOOT[level][0] <= s["x"] <= FOOT[level][2] and FOOT[level][1] <= s["y"] <= FOOT[level][3]): continue
            add("P.drain", level, ["cyl", round(s["x"], 1), round(s["y"], 1), 6, round(ffl - 0.02, 3), round(ffl + 0.01, 3)], mark=txt, typ=typ, mat="p_waste", src=[f"{sheet} وسم {txt} (M_DR_TEXT)"]); n += 1
    print(f"  drainage {level}{'/' + tag if tag else ''}: {n} elements (glyphs dropped {nd})")

def main():
    circles = {}
    for lv in ("B", "G", "1", "2", "R"):
        circles[lv] = riser_circles(lv)
    circles["3"] = circles["4"] = circles["5"] = circles["2"]
    print("riser circles:", {k: [(c["layer"], round(c["x"]), round(c["y"])) for c in v] for k, v in circles.items() if k in ("B", "G", "1", "R")})
    # sprinkler network of the levels that were missing
    for lv in ("B", "G", "R"):
        sprinkler_level(lv)
    # FFC line of every level
    for lv in ORDER:
        ps, bad, sh = ffc_pipes(lv)
        z = z_of(lv, "ffc")
        for p in ps:
            add("P.ff", lv, plumb._tube(p["pl"], z, 150), typ="pipe_ffc", mat="p_ffc_line",
                attrs={"dia_mm": 150, "length_m": round(geo.polyline_len(p["pl"]) / 100, 2), "dia_note": "6″ من مخطط الأعمدة الرأسية FF-105 («6″Ø FFC LINE»)؛ لا وسم قطر على المخططات الأفقية"},
                src=[f"{SHEET(PAGE[lv][0])} طبقة M_FF_FFC (خط صناديق الإطفاء)", "منسوب التمديد فوق الأرضية: افتراض"], grp=None)
        print(f"  FFC line {lv}: {len(ps)} pipes (glyphs dropped {bad})")
    # hose cabinets
    for lv in ORDER:
        for (x, y, w, h) in fhc_cabinets(lv):
            if not (FOOT[lv][0] <= x <= FOOT[lv][2] and FOOT[lv][1] <= y <= FOOT[lv][3]): continue
            z0 = FFL[lv] + 0.50
            add("P.ff", lv, ["b", round(x, 1), round(y, 1), round(max(w, h), 1), round(min(w, h), 1), 0 if w >= h else 90, round(z0, 3), round(z0 + 1.40, 3)], mark="FHC", typ="fhc", mat="p_ffc",
                attrs={"dim_note": "المسقط 32×88 سم من تجويف الصندوق على المخطط؛ الارتفاع 1.4 م وبدايته 0.5 م: افتراض"},
                src=[f"{SHEET(PAGE[lv][0])} طبقة FHC (تجويف صندوق الإطفاء) ووسم FFC", "الارتفاعات: افتراض هندسي يحتاج تأكيد"])
    # AC layout B/G
    for lv, pg, ref in (("B", 1, 4), ("G", 2, 5)): ac_level(lv, pg, ref)
    # chilled-water pipes B, G, 1, typical
    for lv, pg, ref in (("B", 11, 4), ("G", 12, 5), ("1", 13, 6), ("2", 14, 7), ("3", 14, 7), ("4", 14, 7), ("5", 14, 7)): chw_level(lv, pg, ref)
    # water supply and drainage
    for lv, pg, ref in (("B", 18, 4), ("G", 19, 5), ("R", 22, 8)): ws_level(lv, pg, ref)
    dr_level("B", 2, 4); dr_level("G", 4, 5); dr_level("G", 3, 5, tag="G-high"); dr_level("R", 7, 8)
    n = emit_risers(build_risers(circles))
    print("risers:", n)
    types = {
        "pipe_ffc": {"n": "أنبوب خط صناديق الإطفاء (FFC) 6″", "cf": "derived", "sp": [["القطر", "6″ (150 مم) — مخطط FF-105"], ["الطبقة", "M_FF_FFC"]], "asm": ["منسوب التمديد في فراغ السقف: افتراض"], "sr": [SHEET(10) + "–" + str(14), "MECH2 ص15 (FF-105)"]},
        "riser_spr": {"n": "رايزر شبكة الرشاشات 6″ (رأسي)", "cf": "derived", "sp": [["القطر", "6″ (150 مم)"], ["من / إلى", "حسب العنصر"]], "asm": ["تخصيص الجاف/الرطب غير مرسوم", "نهايتا الرايزر عند منسوب خط التوزيع في كل طابق: افتراض"], "sr": ["MECH2 ص10–14 (رموز الرايزر)", "MECH2 ص15 (FF-105)"]},
        "riser_ffc": {"n": "رايزر خط صناديق الإطفاء FFC 6″ (رأسي)", "cf": "derived", "sp": [["القطر", "6″ (150 مم)"], ["من / إلى", "حسب العنصر"]], "asm": ["تخصيص الجاف/الرطب غير مرسوم", "نهايتا الرايزر عند منسوب خط التوزيع في كل طابق: افتراض"], "sr": ["MECH2 ص10–14 (رموز الرايزر)", "MECH2 ص15 (FF-105)"]},
        "pipe_suction": {"n": "خط شفط مضخات الإطفاء 6″ (من خزان البدروم)", "cf": "derived", "sp": [["القطر", "6″ (150 مم)"]], "asm": ["منسوب الخط داخل الخزان وعند المضخات: افتراض"], "sr": ["MECH2 ص10 و11 (SUCTION LINE)", "MECH2 ص15 (FF-105)"]},
    }
    mats = {"p_ffc_line": {"name": "أنبوب خط صناديق الإطفاء FFC (فولاذ أسود)", "color": "#1f5fbf", "code": "M_FF_FFC"}}
    json.dump({"els": els, "types": types, "mats": mats}, open(os.path.join(HERE, "data", "mep_bg.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    c = collections.Counter((e["c"], e["l"], e["t"]) for e in els)
    print("elements", len(els))
    for k, v in sorted(c.items()): print("  ", k, v)

if __name__ == "__main__":
    main()
