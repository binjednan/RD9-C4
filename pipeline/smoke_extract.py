# -*- coding: utf-8 -*-
"""Smoke-management layouts (MECH1 p17–21: SM-100 basement, SM-101 ground, SM-102 first floor, SM-103 typical floors, SM-104 roof) -> pipeline/data/smoke.json
(needs the source PDFs, see lib.py; post_model.py merges the json through pipeline/smoke_build.py)

Owner 2026-10-08: «أكمل استعمال جميع المخططات لتكون البيئة مناسبة للاختبار».  What these sheets draw (layer names of the NHR MEP drawings):

  B   p17  M_FA_GRILL / M_EX_GRILL   car-park make-up (FA) / extract (EA) system: the single-line duct polylines (a main with two arms, stubs 29 / 50 cm long, a connection piece to the shaft),
                                     the 13 grille symbols of each system (a cluster of 16 filled slivers), the shaft box (rectangle, 140 x 100 / 160 x 100 cm)
           M_VE_DAM                  the 26 volume-control dampers (VCD, 7-vertex outline);  M_HVAC_DAM the two fire dampers (FD);  M_HVAC_EQP the two ceiling-suspended fans
           M_FA_TEXT / M_EX_TEXT     duct size labels «600x1300» (mm, width x height) and the words FD / VCD
  G   p18  M_FA_GRILL / M_EX_GRILL   the two shaft boxes again (the louver text has no position on the plan)
  1 / TY / R   p19 / p20 / p21       corridor smoke system: the two riser boxes, the dampers (MFD / VCD), the extract branch and corridor duct, the two extract diffusers (EAD, crossed squares),
                                     the fresh-air grille box (SMS FAG); on the roof the two ducts, the two fan units (AV-MAC rectangles) and their louver hatch (M1-EQUP)

Everything is stored as drawn (plan centimetres, 1 decimal); pipeline/smoke_build.py associates sizes and builds the elements.

    python3 pipeline/smoke_extract.py       # parses five big sheets (cached by lib.py)"""
import sys, os, re, json, math, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lib, geo
from vent_extract import crosses                         # pairs of opposite diagonals = the crossed-square diffusers (already used for the ventilation sheets)

OUT = os.path.join(HERE, "data", "smoke.json")
SHEETS = {"B": 17, "G": 18, "1": 19, "TY": 20, "R": 21}   # MECH1 pages
FAMS = (("fa", "M_FA_GRILL"), ("ea", "M_EX_GRILL"))
SIZE_RE = re.compile(r"^\d{2,4}x\d{2,4}$")
KEEP_WORDS = ("FD", "VCD", "MFD")


def short(layer): return (layer or "").split("$")[-1]
def r1(v): return round(v, 1)
def wh(w):
    b = geo.bbox(w); return b[2] - b[0], b[3] - b[1]
def box(w):
    b = geo.bbox(w); return {"x": r1((b[0] + b[2]) / 2), "y": r1((b[1] + b[3]) / 2), "w": r1(b[2] - b[0]), "h": r1(b[3] - b[1])}
def rect(w):
    b = geo.bbox(w); return [r1(b[0]), r1(b[1]), r1(b[2]), r1(b[3])]
def closed(w, n): return len(w) == n and geo.is_closed(w, 1.5)
def pts(w): return [[r1(p[0]), r1(p[1])] for p in w]


def polys(sh, layers, test):
    """[(layer, plan polyline, drawing)] of every polyline on the given layers that passes test(w, d)"""
    out = []
    for d in sh.D:
        ly = short(d["layer"])
        if ly not in layers: continue
        for pl in d["polys"]:
            w = [sh.T(x, y) for x, y in pl]
            if test(w, d): out.append((ly, w, d))
    return out


def words_of(sh, layers):
    """size labels («500x900») and damper words (FD / VCD / MFD) of the given text layers, plan position of the word centre"""
    out = []
    for w in sh.words():
        ly = short(w["layer"])
        if ly in layers and (SIZE_RE.match(w["s"]) or w["s"] in KEEP_WORDS):
            X, Y = sh.T(w["x"], w["y"]); out.append({"t": w["s"], "x": r1(X), "y": r1(Y), "layer": ly})
    return out


def clusters(sh, layer):
    """the grille symbols: 16 filled 4-vertex slivers per grille; slivers whose boxes are within 4 cm of each other form one cluster -> bbox centre / size of the cluster (legend symbols at x >= 5000 are skipped)"""
    items = [geo.bbox(w) for ly, w, d in polys(sh, (layer,), lambda w, d: d.get("fill") and closed(w, 4) and geo.bbox(w)[0] < 5000)]
    par = list(range(len(items)))
    def find(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if a[0] - 4 <= b[2] and b[0] - 4 <= a[2] and a[1] - 4 <= b[3] and b[1] - 4 <= a[3]: par[find(i)] = find(j)
    groups = collections.defaultdict(list)
    for i, it in enumerate(items): groups[find(i)].append(it)
    out = []
    for v in groups.values():
        x0 = min(b[0] for b in v); y0 = min(b[1] for b in v); x1 = max(b[2] for b in v); y1 = max(b[3] for b in v)
        out.append({"x": r1((x0 + x1) / 2), "y": r1((y0 + y1) / 2), "w": r1(x1 - x0), "h": r1(y1 - y0)})
    return sorted(out, key=lambda c: (c["x"], c["y"]))


def shaft_of(sh, layer):
    """the shaft box: one closed 5-vertex rectangle 120–200 x 80–120 cm on the layer (the X inside it is a 4-vertex open path)"""
    found = [rect(w) for ly, w, d in polys(sh, (layer,), lambda w, d: closed(w, 5) and geo.bbox(w)[0] < 5000 and 120 <= max(wh(w)) <= 200 and 80 <= min(wh(w)) <= 120)]
    assert len(found) == 1, (layer, found)
    return found[0]


def car_park(sh):
    out = {}
    for fam, layer in FAMS:
        sb = shaft_of(sh, layer)
        def is_x(w, sb=sb):
            b = geo.bbox(w); return all(abs(b[i] - sb[i]) <= 1.0 for i in range(4))
        paths = [pts(w) for ly, w, d in polys(sh, (layer,), lambda w, d: len(w) >= 2 and not geo.is_closed(w, 1.5) and geo.bbox(w)[0] < 5000 and geo.polyline_len(w) >= 25 and not is_x(w))]
        out[fam] = {"shaft": sb, "paths": paths, "grilles": clusters(sh, layer)}
    out["vcd"] = [box(w) for ly, w, d in polys(sh, ("M_VE_DAM",), lambda w, d: closed(w, 7))]
    out["fd"] = [box(w) for ly, w, d in polys(sh, ("M_HVAC_DAM",), lambda w, d: closed(w, 7))]
    out["fans"] = [rect(w) for ly, w, d in polys(sh, ("M_HVAC_EQP",), lambda w, d: closed(w, 5))]
    out["words"] = words_of(sh, ("M_FA_TEXT", "M_EX_TEXT", "M_HVAC_DAM", "M_VE_DAM"))
    assert [len(out[f]["grilles"]) for f, _ in FAMS] == [13, 13] and len(out["vcd"]) == 26 and len(out["fd"]) == 2 and len(out["fans"]) == 2, "basement counts"
    return out


def ground(sh):
    out = {}
    for fam, layer in FAMS:
        found = polys(sh, (layer,), lambda w, d: closed(w, 5) and geo.bbox(w)[0] < 5000 and 120 <= max(wh(w)) <= 200 and 80 <= min(wh(w)) <= 120)
        assert len(found) == 1, (layer, len(found))
        out[fam] = box(found[0][1])
    return out


def corridor(sh, roof):
    S = {}
    S["fa_riser"] = [box(w) for ly, w, d in polys(sh, ("M_FA_DUCT",), lambda w, d: closed(w, 5) and 20 <= wh(w)[0] <= 30 and 35 <= wh(w)[1] <= 45)]
    S["ea_riser"] = [box(w) for ly, w, d in polys(sh, ("M_T.EX_DIFF",), lambda w, d: closed(w, 5) and 15 <= wh(w)[0] <= 25 and 25 <= wh(w)[1] <= 35)]
    S["dampers"] = [dict(box(w), layer=ly) for ly, w, d in polys(sh, ("M_HVAC_DAM", "M_VE_DAM"), lambda w, d: closed(w, 7) and geo.bbox(w)[0] < 2500)]
    S["words"] = words_of(sh, ("M_HVAC_DAM", "M_VE_DAM", "M_FA_TEXT", "M_T.EX_TEXT"))
    if not roof:
        S["ea_branch"] = [pts(w) for ly, w, d in polys(sh, ("M_T.EX_DIFF",), lambda w, d: len(w) == 2 and 120 <= geo.polyline_len(w) <= 160 and abs(w[0][0] - w[1][0]) < 1)]
        S["ea_main"] = [pts(w) for ly, w, d in polys(sh, ("M_T.EX_DIFF",), lambda w, d: len(w) == 2 and geo.polyline_len(w) > 800)]
        S["ead"] = crosses(sh, ("M_T.EX_DIFF",))
        S["fag_box"] = [box(w) for ly, w, d in polys(sh, ("M_SAG_GRILL",), lambda w, d: closed(w, 5) and geo.bbox(w)[0] < 2500)]
        assert len(S["fa_riser"]) == 1 and len(S["ea_riser"]) == 1 and len(S["ea_branch"]) == 1 and len(S["ea_main"]) == 1 and len(S["ead"]) == 2 and len(S["fag_box"]) == 2, "corridor counts"
    else:
        S["fa_duct"] = [pts(w) for ly, w, d in polys(sh, ("M_DR_WP",), lambda w, d: len(w) == 4 and geo.polyline_len(w) > 900)]          # the layer name is odd (drain / waste); the polyline joins the FA riser to the supply fan
        S["ea_duct"] = [pts(w) for ly, w, d in polys(sh, ("M_EX_GRILL",), lambda w, d: len(w) == 6 and geo.polyline_len(w) > 1500)]
        S["fan_rects"] = [dict(box(w), layer=ly) for ly, w, d in polys(sh, ("AV-MAC",), lambda w, d: closed(w, 5) and geo.bbox(w)[0] < 500)]      # outer + inner rectangle of each unit
        S["fan_circles"] = [dict(box(w), layer=ly) for ly, w, d in polys(sh, ("AV-MAC",), lambda w, d: len(w) == 41 and geo.bbox(w)[0] < 500)]
        strokes = collections.defaultdict(list)                                                                                           # louver hatch west of each fan unit
        for d in sh.D:
            if short(d["layer"]) != "M1-EQUP": continue
            for pl in d["polys"]:
                w = [sh.T(x, y) for x, y in pl]; b = geo.bbox(w)
                if b[2] < 310: strokes["fa" if b[1] < 1500 else "ea"].append(b)
        S["louvers"] = {k: {"x0": r1(min(b[0] for b in v)), "y0": r1(min(b[1] for b in v)), "x1": r1(max(b[2] for b in v)), "y1": r1(max(b[3] for b in v))} for k, v in strokes.items()}
        assert len(S["fa_duct"]) == 1 and len(S["ea_duct"]) == 1 and len(S["fan_rects"]) == 4 and len(S["fan_circles"]) == 2 and sorted(S["louvers"]) == ["ea", "fa"], "roof counts"
    return S


def run(out=OUT):
    ref = lib.Sheet("ARCH1", 7); res = {}
    for key, page in SHEETS.items():
        sh = lib.Sheet("MECH1", page, ref=ref)
        if sh.reg is None: raise SystemExit(f"no registration for MECH1 p{page}")
        if key == "B": body = car_park(sh)
        elif key == "G": body = ground(sh)
        else: body = corridor(sh, roof=(key == "R"))
        res[key] = dict({"sheet": f"MECH1 p{page}", "scale": round(sh.reg["s"], 3)}, **body)
        print(key, f"MECH1 p{page}", {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in body.items()})
    json.dump(res, open(out, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
    print("saved", out, round(os.path.getsize(out) / 1e3), "kB")


if __name__ == "__main__":
    run()
