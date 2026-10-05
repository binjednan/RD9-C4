# -*- coding: utf-8 -*-
"""Site lighting from the landscape tile/light layout A2301 (ARCH2 'Arch. Drawings Part II.pdf', page 50) -> data/site_lights.json

The sheet is a normal 1:100 landscape page (north up, same orientation as A102).  It is registered with the 12 black 60x60 cm C5 columns
(rows at world y = 1810 / 0, columns at x = 125 + 605*k):  x_cm = 125 + (px - 248.5) * 3.528 ,  y_cm = (1413.5 - py) * 3.528   (P = PDF points).

LIGHT DETAILS legend of A2301:  'WATER PROOF OUTDOOR WALL MOUNTED LAMP' (layer '...EL- Wall Mount WP 20W' -> 20 W, label 'H -230' = mounted 2.30 m above the ground),
'WATER PROOF OUTDOOR LIGHT' (rectangular symbol, none drawn on the plan outside the legend) and 'POST LIGHT' (centre cross on layer 'A-ELEV 04' + four small circles on 'ELECTRICAL').
Wall lamps are the dense 16x12 pt symbols (23 of them, 540 cm apart on the west / east / north boundary walls); post lights are the 25-primitive clusters of layer A-ELEV 04.
usage: python3 pipeline/site_lights.py"""
import os, sys, json, collections
HERE = os.path.dirname(os.path.abspath(__file__))
PDFS = ["/Users/binqdair/Downloads/Arch. Drawings Part II.pdf", "/home/user/c4-docs-privet/Arch. Drawings Part II.pdf"]
LY = "X-EL-100-Ground Floor Plan$0$AD738-ECC-100-Ground Floor Plan$0$EL- Wall Mount WP 20W"
def W(x, y): return (125 + (x - 248.5) * 3.528, (1413.5 - y) * 3.528)

def clusters(items, gap):
    n = len(items); par = list(range(n))
    def f(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    H = collections.defaultdict(list)
    for i, (x0, y0, x1, y1) in enumerate(items):
        for cx in range(int((x0 - gap) // 20), int((x1 + gap) // 20) + 1):
            for cy in range(int((y0 - gap) // 20), int((y1 + gap) // 20) + 1): H[(cx, cy)].append(i)
    for ids in H.values():
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                A = items[ids[a]]; B = items[ids[b]]
                if A[0] - gap <= B[2] and B[0] - gap <= A[2] and A[1] - gap <= B[3] and B[1] - gap <= A[3]: par[f(ids[a])] = f(ids[b])
    g = collections.defaultdict(list)
    for i in range(n): g[f(i)].append(i)
    out = []
    for v in g.values():
        out.append((min(items[i][0] for i in v), min(items[i][1] for i in v), max(items[i][2] for i in v), max(items[i][3] for i in v), len(v)))
    return out

def main():
    import fitz
    pdf = next((p for p in PDFS if os.path.exists(p)), None)
    if not pdf: sys.exit("A2301 sheet not found: " + ", ".join(PDFS))
    pg = fitz.open(pdf)[49]
    dr = pg.get_drawings()
    wall = []
    for x0, y0, x1, y1, n in clusters([(d["rect"].x0, d["rect"].y0, d["rect"].x1, d["rect"].y1) for d in dr if d.get("layer") == LY], 1.0):
        w, h = x1 - x0, y1 - y0
        if (15 <= w <= 17 and 11 <= h <= 13) or (11 <= w <= 13 and 15 <= h <= 17):
            X, Y = W((x0 + x1) / 2, (y0 + y1) / 2)
            side = "W" if X < 0 else "E" if X > 4400 else "N" if Y > 4400 else "?"
            wall.append({"x": round(X), "y": round(Y), "side": side})
    post = []
    for x0, y0, x1, y1, n in clusters([(d["rect"].x0, d["rect"].y0, d["rect"].x1, d["rect"].y1) for d in dr if d.get("layer") == "A-ELEV 04"], 2.0):
        X, Y = W((x0 + x1) / 2, (y0 + y1) / 2)
        if n == 25 and -60 < X < 4470 and -60 < Y < 4470: post.append({"x": round(X), "y": round(Y)})
    wall.sort(key=lambda r: (r["side"], r["x"], r["y"])); post.sort(key=lambda r: (r["y"], r["x"]))
    out = {"wall": wall, "post": post, "src": "A2301 LANDSCAPE AREA / FLOORING TILE LAYOUT (ARCH2 p50) registered on the C5 columns"}
    json.dump(out, open(os.path.join(HERE, "data", "site_lights.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("wall lamps", len(wall), collections.Counter(w["side"] for w in wall), "| post lights", len(post))

if __name__ == "__main__": main()
