# -*- coding: utf-8 -*-
"""Floor-finish zones of the basement read from the drawing's OWN layers (A101, ARCH1 page 4) — owner 2026-10-08 («نعم مع تحديد في التفاصيل ماذا موجود في المخططات»).

What the sheet really contains (found by listing its layers):
  * layer A-PAIVING  — an interlock-paving herringbone hatch (6,524 strokes, every stroke 61.07 cm long) covering 472 m² of the open basement floor = «Walk way (Basement): F13 & CPF-2» of A500
                       (BOQ 9.1.1.4.1: F13 = 475 m²);  a few long strokes of the same layer are the transverse grooves of the ramp.
  * layer A-CAR      — the parking-bay symbols (37 bays numbered 15–51; bay 2.70 × 5.50 m).
  * layer A-WALL     — the lobby room: 540 cm wide inside (printed dimension), 380 cm deep (printed dimension), «LOBBY AREA:20.62 M²», F.F.L. -3.50, two lifts below it, SUMP PUMP ROOM beside it.
  * the white remainder of the open floor is the 6 m wide drive way (CSP-3); the ramp («M», Slope 16.5 %, Transition Ramp 8 %) is CSP-2 (A500 row «Car Ramp»).
Run once (needs the PDF in ~/Downloads); the result is committed as pipeline/data/a101_zones.json so the model build needs no PDF:   python3 pipeline/extract_a101_zones.py"""
import os, sys, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fitz
import reg
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

PDF = os.path.expanduser("~/Downloads/Arch. Drawings Part I (1).pdf")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "a101_zones.json")
S100 = 100 * 0.3527777778 / 10
HATCH_LEN = 61.5      # cm: every herringbone stroke is 61.07 cm (the longer strokes of the layer are the ramp grooves)


def ring(c):
    return [[round(x, 1), round(y, 1)] for x, y in list(c.coords)[:-1]]


def polys_of(g, min_m2):
    out = []
    for q in (list(g.geoms) if g.geom_type == "MultiPolygon" else [g]):
        if q.is_empty or q.geom_type != "Polygon" or q.area < min_m2 * 1e4: continue
        q = q.simplify(3.0)
        out.append({"ext": ring(q.exterior), "holes": [ring(h) for h in q.interiors if Polygon(h).area > 0.5e4], "m2": round(q.area / 1e4, 1)})
    return out


def main():
    d = fitz.open(PDF); page = None
    for pn in range(len(d)):
        t = d[pn].get_text()
        if "BASEMENT FLOOR PLAN" in t and "A101" in t: page = d[pn]; pno = pn + 1; break
    if page is None: sys.exit("A101 not found in " + PDF)
    T = reg.make_T(reg.register_page(page, S100))
    dr = page.get_drawings()
    herring, bays, walls = [], [], []
    for it in dr:
        ly = it.get("layer")
        for op in it["items"]:
            if op[0] != "l": continue
            a = T(op[1].x, op[1].y); b = T(op[2].x, op[2].y)
            if ly == "A-PAIVING":
                if ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** .5 <= HATCH_LEN: herring.append((a, b))
            elif ly == "A-CAR": bays.append((a, b))
            elif ly == "A-WALL": walls.append((op[1], op[2]))
    pav = unary_union([LineString(s).buffer(12) for s in herring]).buffer(25).buffer(-25)
    bay = unary_union([LineString(s).buffer(14) for s in bays]).buffer(25).buffer(-25)
    bay = unary_union([Polygon(q.exterior) for q in (list(bay.geoms) if bay.geom_type == "MultiPolygon" else [bay])])      # fill the symbol interiors: a bay block is its outer edge
    # lobby: the inner faces of the A-WALL lines around the LOBBY label (x 953.0 / 1106.1 pt, bottom 1117.6 pt); depth = the printed dimension 380
    lab = page.search_for("LOBBY")[0]; cx, cy = (lab.x0 + lab.x1) / 2, (lab.y0 + lab.y1) / 2
    vs = [a.x for a, b in walls if abs(a.x - b.x) < 0.05 and abs(a.y - b.y) > 15 and abs(a.y - cy) < 110]
    hs = [a.y for a, b in walls if abs(a.y - b.y) < 0.05 and abs(a.x - b.x) > 15 and abs(a.x - cx) < 110]
    xl, xr = min(vs, key=lambda x: abs(x - (cx - 73))), min(vs, key=lambda x: abs(x - (cx + 80)))
    yb = min(hs, key=lambda y: abs(y - (cy + 82)))
    x0, ybot = T(xl, yb); x1, _ = T(xr, yb)
    lobby = [round(min(x0, x1), 1), round(ybot, 1), round(max(x0, x1), 1), round(ybot + 380.0, 1)]
    # values printed on the sheet (checked against its text, then recorded)
    flat = re.sub(r"\s+", "", page.get_text())
    printed = {"lobby_m2": 20.62, "store1_m2": 48.50, "store2_m2": 63.10, "pump_irrigation_m2": 6.50, "pump_sump_m2": 7.30, "basement_plan_m2": 2000.0, "basement_calc_table_m2": 2016.0,
               "ramp": "Slope 16.5% ; Transition Ramp 8%", "drive_way": "6 m WIDE DRIVE WAY", "lobby_ffl": -3.50, "open_floor_ffl": -3.60}
    for needle in ("LOBBYAREA:20.62", "A=48.50", "A=63.10", "AREA:6.50", "AREA:7.30", "AREA:2000.0", "Slope16.5%", "TransitionRamp8%", "6mWIDEDRIVEWAY", "F.F.L.-3.50", "F.F.L.-3.60"):
        if needle not in flat: print("WARNING: not found on the sheet:", needle)
    out = {"source": f"ARCH1 p{pno} (A101 مخطط البدروم)", "scale_cm_per_pt": round(S100, 6),
           "layers": {"paving": "A-PAIVING (هاشور الإنترلوك — ضربات 61.07 سم)", "bays": "A-CAR (رموز مواقف السيارات)", "walls": "A-WALL"},
           "paving": polys_of(pav, 3.0), "bays": polys_of(bay, 5.0), "lobby": {"rect": lobby, "printed_m2": 20.62, "inner_cm": [540, 380]}, "printed": printed}
    out["stats"] = {"paving_m2": round(sum(p["m2"] for p in out["paving"]), 1), "bays_m2": round(sum(p["m2"] for p in out["bays"]), 1), "herringbone_strokes": len(herring), "bay_strokes": len(bays)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("wrote", OUT, os.path.getsize(OUT), "bytes;", out["stats"], "lobby", lobby, "w x h", round(lobby[2] - lobby[0], 1), round(lobby[3] - lobby[1], 1))


if __name__ == "__main__":
    main()
