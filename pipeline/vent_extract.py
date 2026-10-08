# -*- coding: utf-8 -*-
"""Ventilation layouts (MECH1 p23–27: B, G, 1, typical, roof) -> pipeline/data/vent.json   (needs the source PDFs, see lib.py; post_model.py merges the json through vent_build.py)

Owner 2026-10-08: «أكمل استعمال جميع المخططات لتكون البيئة مناسبة للاختبار».  The ventilation plans were unused (96 sheets were).  What they draw, per level (layer names of the NHR MEP drawings):

  M_T.EX_DIFF / M_T.EX_DUCT   toilet extract: single-line extract ducts + the extract ceiling diffusers (a 25 cm square with an X) + the shaft box of the extract riser
  M_RAD_DIFF                  kitchen extract diffusers (same symbol)
  M_FA_DUCT                   fresh-air ducts (+ the box of the fresh-air riser); the «FA 30 L/S wire mesh» labels sit at their ends
  M_VE_DAM                    fire dampers FD and volume-control dampers VCD (7-vertex outline); the kind is the word beside it (layer M_HVAC_DAM)
  M_T.EX_TEXT / M_FA_TEXT /
  M_K.EX_TEXT / M_HVAC_DAM    duct sizes («250x150» = mm), flows («15 L/S»), fan labels («WINDOW TYPE Ex. FAN-01 70 L/S»), riser boxes («EA.DUCT 950X500-T/A …»)

Everything is stored as drawn (polylines, symbol centres, word tokens with positions); pipeline/vent_build.py associates sizes and flows and builds the elements.  What is NOT drawn — the duct elevations in the
ceiling void, the riser sizes of the other floors (they are on the riser diagram VE-105, p28) — is added there with the assumption marked.

    python3 pipeline/vent_extract.py       # parses five big sheets (cached by lib.py)"""
import sys, os, re, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lib, geo

OUT = os.path.join(HERE, "data", "vent.json")
SHEETS = {"B": 23, "G": 24, "1": 25, "TY": 26, "R": 27}                  # MECH1 pages
EA_LAYERS = ("M_T.EX_DIFF", "M_T.EX_DUCT")
FA_LAYERS = ("M_FA_DUCT",)
TEXT_LAYERS = ("M_T.EX_TEXT", "M_FA_TEXT", "M_K.EX_TEXT", "M_HVAC_DAM", "M_VE_DAM", "M_WS_TEXT", "M_HVAC_TEXT")
MIN_DUCT = 35.0           # cm  shorter open polylines are parts of the diffuser symbols
MAX_DUCT = 1700.0         # cm  a line this long on these layers is the building / projection line of the roof plan, not a duct (the longest real run is 1360 cm)


def short(layer): return (layer or "").split("$")[-1]


def is_diag(w, square=True):
    """one stroke of the cross inside a diffuser (square, ~25 cm): two points, both extents > 8 cm"""
    if len(w) != 2: return False
    dx, dy = abs(w[0][0] - w[1][0]), abs(w[0][1] - w[1][1])
    return dx > 8 and dy > 8 and (abs(dx - dy) < 2.5 if square else True) and 12 <= max(dx, dy) <= 130


def crosses(sh, layers):
    """pairs of opposite diagonals with the same box -> [{x, y, w, h, layer}]: the extract diffusers (25 x 25 cm)"""
    segs = []
    for d in sh.D:
        ly = short(d["layer"])
        if ly not in layers: continue
        for pl in d["polys"]:
            w = [sh.T(x, y) for x, y in pl]
            if is_diag(w): b = geo.bbox(w); segs.append((ly, (b[0] + b[2]) / 2, (b[1] + b[3]) / 2, b[2] - b[0], b[3] - b[1], w))
    out = []; used = set()
    for i, a in enumerate(segs):
        if i in used: continue
        for j in range(i + 1, len(segs)):
            b = segs[j]
            if j in used or a[0] != b[0] or math.hypot(a[1] - b[1], a[2] - b[2]) > 1.5 or abs(a[3] - b[3]) > 1.5 or abs(a[4] - b[4]) > 1.5: continue
            sa = (a[5][1][0] - a[5][0][0]) * (a[5][1][1] - a[5][0][1]); sb = (b[5][1][0] - b[5][0][0]) * (b[5][1][1] - b[5][0][1])
            if sa * sb >= 0: continue
            used.add(i); used.add(j); out.append({"x": round(a[1], 1), "y": round(a[2], 1), "w": round(a[3], 1), "h": round(a[4], 1), "layer": a[0]}); break
    return out


def shafts_of(sh, diffs=()):
    """vertical duct boxes (the riser seen from above): rectangles with an X — 95 x 50 cm on the typical floors, 50 x 25 on the first, 24 x 15 on the ground floor, 16 x 20 for the basement branch — drawn as one 4–8 point path on the extract / fresh-air layers"""
    out = []
    for d in sh.D:
        ly = short(d["layer"])
        if ly not in EA_LAYERS + FA_LAYERS: continue
        for pl in d["polys"]:
            w = [sh.T(x, y) for x, y in pl]
            if len(w) >= 4:
                b = geo.bbox(w); W, H = b[2] - b[0], b[3] - b[1]
                if 14 <= max(W, H) <= 140 and 10 <= min(W, H) <= 90 and len(w) <= 8 and geo.polyline_len(w) >= 1.6 * (W + H):
                    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
                    if max(W, H) < 40 and any(math.hypot(q["x"] - cx, q["y"] - cy) < 45 for q in diffs): continue      # the flexible-connection mark beside a diffuser, not a shaft
                    out.append({"x": round((b[0] + b[2]) / 2, 1), "y": round((b[1] + b[3]) / 2, 1), "x0": round(b[0], 1), "x1": round(b[2], 1), "y0": round(b[1], 1), "y1": round(b[3], 1),
                                "w": round(W, 1), "h": round(H, 1), "layer": ly, "kind": "ea" if ly in EA_LAYERS else "fa"})
    ded = []
    for q in out:
        if not any(abs(q["x"] - r["x"]) < 2 and abs(q["y"] - r["y"]) < 2 and q["kind"] == r["kind"] for r in ded): ded.append(q)
    return ded


def grille_symbol(w):
    """the wire-mesh grille symbol: a 40 cm bar across the end of the duct with a 15 cm hook (3 points, a right angle) -> (centre of the bar, unit direction of the bar) or None"""
    if len(w) != 3: return None
    (ax, ay), (bx, by), (cx, cy) = w
    l1, l2 = math.hypot(bx - ax, by - ay), math.hypot(cx - bx, cy - by)
    if not (33 <= l1 <= 48 and 9 <= l2 <= 22): return None
    if abs((bx - ax) * (cx - bx) + (by - ay) * (cy - by)) / (l1 * l2) > 0.12: return None
    return ((ax + bx) / 2, (ay + by) / 2, (bx - ax) / l1, (by - ay) / l1)


def ducts_of(sh, layers, diffs, shafts, syms=None):
    """open polylines >= MIN_DUCT that are not the strokes of a cross, not a wire-mesh grille symbol (collected in syms) and do not sit inside a symbol box"""
    out = []
    for d in sh.D:
        if short(d["layer"]) not in layers: continue
        for pl in d["polys"]:
            w = [sh.T(x, y) for x, y in pl]
            if len(w) < 2 or geo.is_closed(w, 1.5) or is_diag(w): continue
            g = grille_symbol(w)
            if g is not None:
                if syms is not None: syms.append({"x": round(g[0], 1), "y": round(g[1], 1), "dx": round(g[2], 3), "dy": round(g[3], 3), "layer": short(d["layer"])})
                continue
            L = geo.polyline_len(w)
            if len(w) >= 4 and L < 60:
                b = geo.bbox(w)
                if b[2] - b[0] <= 25 and b[3] - b[1] <= 25: continue                                              # a small squiggle: the flexible-connection / attenuator mark of a symbol
            if L < MIN_DUCT or L > MAX_DUCT: continue
            if len(w) == 2 and L < 70 and min(abs(w[0][0] - w[1][0]), abs(w[0][1] - w[1][1])) > 6: continue          # ducts are drawn along the axes: a short slanted stroke is part of a symbol
            if len(w) == 2 and is_diag(w, False) and any(s["x0"] - 2 <= w[0][0] <= s["x1"] + 2 and s["y0"] - 2 <= w[0][1] <= s["y1"] + 2 for s in shafts): continue         # the X of a shaft box
            if len(w) >= 4 and any(s["x0"] - 2 <= min(p[0] for p in w) and max(p[0] for p in w) <= s["x1"] + 2 and s["y0"] - 2 <= min(p[1] for p in w) and max(p[1] for p in w) <= s["y1"] + 2 for s in shafts): continue   # the box itself
            if L < 80 and all(any(abs(p[0] - q["x"]) <= q["w"] / 2 + 25 and abs(p[1] - q["y"]) <= q["h"] / 2 + 25 for q in diffs) for p in w): continue         # strokes of the symbol, not a duct
            out.append([[round(p[0], 1), round(p[1], 1)] for p in w])
    return out


def dampers_of(sh):
    out = []
    for d in sh.D:
        if short(d["layer"]) != "M_VE_DAM": continue
        for pl in d["polys"]:
            w = [sh.T(x, y) for x, y in pl]
            if len(w) >= 6 and geo.is_closed(w, 1.5):
                b = geo.bbox(w); W, H = b[2] - b[0], b[3] - b[1]
                if 20 <= max(W, H) <= 45: out.append({"x": round((b[0] + b[2]) / 2, 1), "y": round((b[1] + b[3]) / 2, 1), "w": round(W, 1), "h": round(H, 1)})
    return out


def fans_of(sh):
    """extract fans: a 40 cm circle (41-point path) with two blade strokes on M_HVAC_EQP (window / propeller fans), and the framed 50 x 50 cm box with a propeller on AV-MAC (the axial fan in a duct)"""
    out = []
    for d in sh.D:
        ly = short(d["layer"])
        if ly not in ("M_HVAC_EQP", "AV-MAC"): continue
        for pl in d["polys"]:
            w = [sh.T(x, y) for x, y in pl]
            if len(w) < 4 or not geo.is_closed(w, 1.5): continue
            b = geo.bbox(w); W, H = b[2] - b[0], b[3] - b[1]
            if ly == "M_HVAC_EQP" and len(w) >= 30 and 30 <= W <= 60 and abs(W - H) < 3: out.append({"kind": "circle", "x": round((b[0] + b[2]) / 2, 1), "y": round((b[1] + b[3]) / 2, 1), "w": round(W, 1), "h": round(H, 1), "layer": ly})
            if ly == "AV-MAC" and 40 <= W <= 70 and 40 <= H <= 70 and len(w) <= 12: out.append({"kind": "box", "x": round((b[0] + b[2]) / 2, 1), "y": round((b[1] + b[3]) / 2, 1), "w": round(W, 1), "h": round(H, 1), "layer": ly})
    ded = []
    for q in out:
        if not any(abs(q["x"] - r["x"]) < 5 and abs(q["y"] - r["y"]) < 5 for r in ded): ded.append(q)
    return ded


def run():
    ref = lib.Sheet("ARCH1", 7); res = {}
    for key, page in SHEETS.items():
        sh = lib.Sheet("MECH1", page, ref=ref)
        if sh.reg is None: print("skip (no registration)", key, page); continue
        words = []
        for w in sh.words():
            ly = short(w["layer"])
            if ly in TEXT_LAYERS and len(w["s"]) <= 40:
                X, Y = sh.T(w["x"], w["y"]); words.append({"t": w["s"], "x": round(X, 1), "y": round(Y, 1), "layer": ly, "dx": round(w["dx"], 1), "dy": round(w["dy"], 1)})
        cr = crosses(sh, ("M_T.EX_DIFF", "M_RAD_DIFF"))
        for c in cr: c["kind"] = "kitchen" if c["layer"] == "M_RAD_DIFF" else "toilet"
        shafts = shafts_of(sh, cr); dams = dampers_of(sh); fans = fans_of(sh)
        gsyms = []
        ea = ducts_of(sh, EA_LAYERS, cr, shafts, gsyms); fa = ducts_of(sh, FA_LAYERS, cr, shafts, gsyms)
        res[key] = {"sheet": f"MECH1 p{page}", "scale": round(sh.reg["s"], 3), "ea": ea, "fa": fa, "diffusers": cr, "shafts": shafts, "dampers": dams, "fans": fans, "grille_syms": gsyms, "words": words}
        print(key, f"MECH1 p{page}", "ea ducts", len(ea), "fa ducts", len(fa), "diffusers", len(cr), "shafts", len(shafts), "dampers", len(dams), "fans", len(fans), "grille symbols", len(gsyms), "words", len(words))
    json.dump(res, open(OUT, "w"), separators=(",", ":"), ensure_ascii=False)
    print("saved", OUT, round(os.path.getsize(OUT) / 1e3), "kB")


if __name__ == "__main__":
    run()
