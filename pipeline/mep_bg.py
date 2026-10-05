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
