# -*- coding: utf-8 -*-
"""Alignment gate between a drawing sheet and the 3-D model (numpy + Pillow only; pipeline/audit_reg.py needs scipy and pipeline/overlay.py needs matplotlib, neither is installed here).

Owner 2026-10-08: no discipline («section») may sit shifted against the others.  Every plan sheet of every discipline carries the architectural underlay (layer *A-WALL); transformed with the sheet's
registration (lib.Sheet(...).reg) it must land on the walls of the model at the same level.  The shift that matches best (5 cm raster cross-correlation) is the sheet's displacement:
   |shift| >  tol (default 10 cm)   FAIL  (exit code 1)      |shift| == tol   WARN      otherwise OK
Sheets without a wall underlay (site plans, riser diagrams) are SKIPped: check them with --png against the model outline instead.

  python3 tools/check_alignment.py MECH2:27 MECH2:28 MECH2:29 MECH2:30            # numbers (the level comes from the sheet title; «typical» = level 3)
  python3 tools/check_alignment.py MECH2:27-31 MECH1:17-21 --tol 10
  python3 tools/check_alignment.py MECH2:1 --level G --png /tmp/site.png --box -200 1700 2600 2300 --cats A.wall,P.drain,P.storm     # picture: sheet grey, sheet underlay blue, model red / coloured"""
import sys, os, json, re, argparse
import numpy as np
from PIL import Image, ImageDraw
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import lib, reg as R

CELL = 5.0; X0, Y0, X1, Y1 = -300, -300, 4700, 4700
NX, NY = int((X1 - X0) / CELL), int((Y1 - Y0) / CELL)


def px(x, y): return ((x - X0) / CELL, (Y1 - y) / CELL)


def level_of(title):
    t = title.upper()
    for k, v in (("TOP ROOF", "T"), ("ROOF", "R"), ("BASEMENT", "B"), ("GROUND", "G"), ("5TH", "5"), ("FIRST", "1"), ("1ST", "1"), ("TYPICAL", "3")):
        if k in t: return v
    return None


def fftconvolve_same(a, b):
    s = [a.shape[i] + b.shape[i] - 1 for i in range(2)]
    full = np.fft.irfft2(np.fft.rfft2(a, s) * np.fft.rfft2(b, s), s)
    sy = (b.shape[0] - 1) // 2; sx = (b.shape[1] - 1) // 2
    return full[sy:sy + a.shape[0], sx:sx + a.shape[1]]


def dilate3(a):
    out = a.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1): out = np.maximum(out, np.roll(np.roll(a, dy, 0), dx, 1))
    return out


def model_raster(M, level):
    im = Image.new("L", (NX, NY), 0); d = ImageDraw.Draw(im)
    for e in M["els"]:
        if e["l"] != level or e["c"] != "A.wall": continue
        g = e["g"]
        if g[0] == "p":
            for ring in [g[1]] + list(g[4] if len(g) > 4 and g[4] else []):
                pts = [px(*p) for p in ring]
                if len(pts) > 2: d.line(pts + [pts[0]], fill=255, width=1)
        elif g[0] == "r": d.rectangle([px(g[1], g[4]), px(g[3], g[2])], outline=255)
    return np.asarray(im, dtype=np.float32) / 255


def sheet_raster(key, pg, rg):
    p = lib.doc(key)[pg - 1]; T = R.make_T(rg)
    im = Image.new("L", (NX, NY), 0); d = ImageDraw.Draw(im); n = 0
    for dr in p.get_drawings():
        if not (dr.get("layer") or "").endswith("A-WALL"): continue
        for poly in lib.flat_path(dr):
            pts = [px(*T(x, y)) for x, y in poly]
            if len(pts) >= 2: d.line(pts, fill=255, width=1); n += 1
    return np.asarray(im, dtype=np.float32) / 255, n


def best_shift(A, B, rad=30):
    """shift (cm, x right / y up) that moves the sheet's lines onto the model's walls"""
    c = fftconvolve_same(dilate3(B), A[::-1, ::-1]); cy, cx = np.array(c.shape) // 2
    sub = c[cy - rad:cy + rad + 1, cx - rad:cx + rad + 1]; iy, ix = np.unravel_index(np.argmax(sub), sub.shape)
    return (ix - rad) * CELL, -(iy - rad) * CELL, float(sub.max() / max(A.sum(), 1))


def parse(specs, levels):
    out = []
    for s in specs:
        m = re.match(r"^([A-Z0-9]+):(\d+)(?:-(\d+))?$", s)
        if not m: raise SystemExit("bad sheet spec " + s)
        for pg in range(int(m.group(2)), int(m.group(3) or m.group(2)) + 1): out.append((m.group(1), pg))
    return out


def picture(key, pg, level, M, box, cats, out, sc=0.3):
    sh = lib.Sheet(key, pg, ref=lib.Sheet("ARCH1", 7)); T = R.make_T(sh.reg)
    x0, y0, x1, y1 = box; W, H = int((x1 - x0) * sc), int((y1 - y0) * sc)
    im = Image.new("RGB", (W, H), "white"); d = ImageDraw.Draw(im)
    P = lambda x, y: ((x - x0) * sc, (y1 - y) * sc)
    for dr in sh.D:
        under = (dr["layer"] or "").endswith("A-WALL")
        for pl in dr["polys"]:
            pts = [P(*sh.T(x, y)) for x, y in pl]
            if len(pts) >= 2: d.line(pts, fill=(60, 90, 230) if under else (205, 205, 205), width=1)
    PAL = {"A.wall": (220, 30, 30), "S.col": (255, 140, 0), "P.drain": (140, 90, 40), "P.storm": (0, 150, 190), "M.duct": (0, 160, 90), "E.tray": (150, 60, 200)}
    for e in M["els"]:
        if e["l"] != level or e["c"] not in cats: continue
        g = e["g"]; col = PAL.get(e["c"], (0, 0, 0))
        if g[0] == "p":
            for ring in [g[1]] + list(g[4] if len(g) > 4 and g[4] else []): d.line([P(*p) for p in ring + [ring[0]]], fill=col, width=1)
        elif g[0] in ("t", "d"): d.line([P(p[0], p[1]) for p in g[1]], fill=col, width=2)
        elif g[0] in ("b", "cyl"): x, y = P(g[1], g[2]); d.ellipse([x - 3, y - 3, x + 3, y + 3], outline=col)
    im.save(out); print("picture", out, W, H)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("sheets", nargs="+"); ap.add_argument("--level"); ap.add_argument("--tol", type=float, default=10.0)
    ap.add_argument("--png"); ap.add_argument("--box", nargs=4, type=float, default=[-300, -300, 4700, 4700]); ap.add_argument("--cats", default="A.wall")
    a = ap.parse_args()
    M = json.load(open(os.path.join(ROOT, "src", "model.json"), encoding="utf-8")); SI = json.load(open(os.path.join(ROOT, "pipeline", "data", "sheet_index.json"), encoding="utf-8"))
    ref = lib.Sheet("ARCH1", 7); cache = {}; worst = 0.0; fail = 0
    for key, pg in parse(a.sheets, a.level):
        title = next((r["title"] for r in SI[key] if r["page"] == pg), "")
        lv = a.level or level_of(title)
        sh = lib.Sheet(key, pg, ref=ref)
        if not sh.reg: print(f"{key}:{pg:<3} SKIP (no registration)  {title[:50]}"); continue
        if a.png: picture(key, pg, lv or "G", M, a.box, a.cats.split(","), a.png); continue
        if not lv: print(f"{key}:{pg:<3} SKIP (no level in the title: pass --level)  {title[:50]}"); continue
        if lv not in cache: cache[lv] = model_raster(M, lv)
        A, n = sheet_raster(key, pg, sh.reg)
        if n < 20: print(f"{key}:{pg:<3} SKIP (no A-WALL underlay on the sheet: use --png)  {title[:50]}"); continue
        pix = np.argwhere(A > 0)
        spans = ((pix.max(axis=0)-pix.min(axis=0))*CELL) if len(pix) else [0,0]
        if not len(pix) or min(spans) < 500 or max(spans) < 1000:
            print(f"{key}:{pg:<3} SKIP (A-WALL is a local/detail fragment, raster span {list(spans)} cm; verify the source axes)  {title[:50]}")
            continue
        dx, dy, score = best_shift(A, cache[lv]); m = max(abs(dx), abs(dy)); worst = max(worst, m)
        st = "FAIL" if m > a.tol else "WARN" if m == a.tol else "OK  "
        fail += st == "FAIL"
        print(f"{key}:{pg:<3} {st} level {lv}  shift dx={dx:6.1f} dy={dy:6.1f} cm  match {score:.2f}  reg s={sh.reg.get('s', 0):.3f} grid {sh.reg.get('nx', 0)}x{sh.reg.get('ny', 0)}  {title[:44]}", flush=True)
    print("worst shift %.1f cm; failures %d" % (worst, fail)); sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
