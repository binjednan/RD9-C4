# -*- coding: utf-8 -*-
"""Registration audit: for every plan sheet (all disciplines) take the architectural underlay (layer *A-WALL) that every MEP/STR/ARCH sheet carries,
transform it with the sheet registration (data/reg_all.json) and measure how far it is from the walls of the 3-D model at the same level
(cross-correlation of 5 cm rasters).  A sheet whose shift is > 10 cm is placed wrongly relative to the model.
usage: python3 pipeline/audit_reg.py [out.json]"""
import sys, os, json, re
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
from PIL import Image, ImageDraw
from scipy.signal import fftconvolve
import lib, reg as R
CELL = 5.0; X0, Y0, X1, Y1 = -300, -300, 4700, 4700
NX, NY = int((X1 - X0) / CELL), int((Y1 - Y0) / CELL)
def px(x, y): return ((x - X0) / CELL, (Y1 - y) / CELL)
def level_of(title):
    t = title.upper()
    if "TOP ROOF" in t: return "T"
    if "ROOF" in t: return "R"
    if "BASEMENT" in t: return "B"
    if "GROUND" in t: return "G"
    if "5TH" in t: return "5"
    if "FIRST" in t or "1ST" in t: return "1"
    if "TYPICAL" in t: return "3"
    return None
def model_raster(M, level):
    im = Image.new("L", (NX, NY), 0); d = ImageDraw.Draw(im)
    for e in M["els"]:
        if e["l"] != level or e["c"] != "A.wall": continue
        g = e["g"]
        if g[0] == "p":
            for ring in [g[1]] + list(g[4] or []):
                pts = [px(*p) for p in ring]
                if len(pts) > 2: d.line(pts + [pts[0]], fill=255, width=1)
        elif g[0] == "r":
            d.rectangle([px(g[1], g[4]), px(g[3], g[2])], outline=255)
    return np.asarray(im, dtype=np.float32) / 255
def sheet_raster(key, pg, rg):
    p = lib.doc(key)[pg - 1]; T = R.make_T(rg)
    im = Image.new("L", (NX, NY), 0); d = ImageDraw.Draw(im); n = 0
    for dr in p.get_drawings():
        ly = dr.get("layer") or ""
        if not ly.endswith("A-WALL"): continue
        for poly in lib.flat_path(dr):
            pts = [px(*T(x, y)) for x, y in poly]
            if len(pts) >= 2: d.line(pts, fill=255, width=1); n += 1
    return np.asarray(im, dtype=np.float32) / 255, n
def best_shift(A, B, rad=30):
    """shift (cells) of A that best matches B: cross-correlation of A with a slightly dilated B"""
    from scipy.ndimage import maximum_filter
    Bd = maximum_filter(B, size=3)
    c = fftconvolve(Bd, A[::-1, ::-1], mode="same")
    cy, cx = np.array(c.shape) // 2
    sub = c[cy - rad:cy + rad + 1, cx - rad:cx + rad + 1]
    iy, ix = np.unravel_index(np.argmax(sub), sub.shape)
    dy, dx = iy - rad, ix - rad
    # the sheet lines moved by (dx,dy) cells match the model best; convert to world cm (x right, y up)
    return dx * CELL, -dy * CELL, float(sub.max() / max(A.sum(), 1)), float(c[cy, cx] / max(A.sum(), 1))
if __name__ == "__main__":
    M = json.load(open(os.path.join(HERE, "..", "src", "model.json")))
    RG = json.load(open(os.path.join(HERE, "data", "reg_all.json"))); SI = json.load(open(os.path.join(HERE, "data", "sheet_index.json")))
    cache = {}; out = []
    for key in ("ARCH1", "STR", "MECH1", "MECH2", "ELEC1", "ELEC2"):
        for e in SI[key]:
            rg = RG.get(f"{key}:{e['page']}"); lv = level_of(e["title"])
            if not rg or not lv or "PLAN" not in e["title"].upper() and "LAYOUT" not in e["title"].upper(): continue
            if lv not in cache: cache[lv] = model_raster(M, lv)
            try: A, n = sheet_raster(key, e["page"], rg)
            except Exception as ex: print(key, e["page"], "ERR", ex); continue
            if n < 20: out.append({"sheet": f"{key}:{e['page']}", "title": e["title"], "level": lv, "note": "no A-WALL underlay"}); continue
            dx, dy, sc, sc0 = best_shift(A, cache[lv])
            r = {"sheet": f"{key}:{e['page']}", "title": e["title"], "level": lv, "dx": dx, "dy": dy, "score": round(sc, 3), "score0": round(sc0, 3), "segs": n}
            out.append(r); print(f"{r['sheet']:10} {lv}  dx={dx:6.1f} dy={dy:6.1f}  match {sc:.2f} (at 0: {sc0:.2f})  {e['title'][:46]}", flush=True)
    json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "data", "audit_reg.json"), "w"), ensure_ascii=False, indent=1)
