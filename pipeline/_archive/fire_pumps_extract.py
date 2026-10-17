# -*- coding: utf-8 -*-
"""Read the positioned fire-pump assembly from FF-101; never place NTS details.

The audited regions identify actual equipment strokes, not their remote labels.
They are intentionally local to the one pump-room assembly. Coordinates stay in
the registered drawing frame; no snap to another service or a test endpoint.
"""
import collections
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib
import mep_common as MC

DATA = os.path.join(HERE, "data", "fire_pumps.json")
REGIONS = [
    ("FP-DP", "diesel", (609, 1165, 664, 1274)),
    ("FP-EP", "electric", (712, 1176, 757, 1274)),
    ("FP-JP", "jockey", (758, 1267, 776, 1320)),
]


def body_from_strokes(sh, mark, kind, region):
    x0, y0, x1, y1 = region
    pts = []
    strokes = 0
    for dr in sh.drawings("FIRE"):
        for pl in dr["polys"]:
            wp = [sh.T(x, y) for x, y in pl]
            if wp and all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in wp):
                pts.extend(wp)
                strokes += 1
    assert strokes >= 15, (mark, strokes)
    xs, ys = zip(*pts)
    return {"mark": mark, "kind": kind,
            "bbox_cm": [round(v, 1) for v in (min(xs), min(ys), max(xs), max(ys))],
            "source_region_cm": list(region), "source_strokes": strokes,
            "source_layer": "FIRE"}


def text_inventory(sh, filters):
    return [{"text": t["s"].strip(), "layer": t["layer"],
             "xy_cm": [round(t["X"], 1), round(t["Y"], 1)] if sh.reg else None}
            for t in sh.texts() if any(x in t["s"].upper() for x in filters)]


def extract():
    sh = lib.Sheet("MECH2", 11, ref=lib.Sheet("ARCH1", 5))
    assert sh.reg and sh.reg["nx"] >= 11 and sh.reg["ny"] >= 6
    pumps = [body_from_strokes(sh, *r) for r in REGIONS]
    # Independent circle signature: one 45.4 cm pressure vessel, not any
    # 15.7 cm riser circle or valve symbol in the neighbouring service.
    circles = [q for q in MC.closed_shapes(sh, "FIRE")
               if q["n"] == 41 and 40 < q["w"] < 50 and abs(q["w"] - q["h"]) < .1
               and 600 < q["c"][0] < 800 and 1150 < q["c"][1] < 1350]
    assert len(circles) == 1, len(circles)
    pressure = {"xy_cm": [round(v, 1) for v in circles[0]["c"]],
                "diameter_cm": round(circles[0]["w"], 1)}
    # Measured double edges of the drawn assembly. Valve glyphs interrupt
    # strokes but occupy the intervening assembly; use its centreline only.
    edge_rows = collections.defaultdict(list)
    for dr in sh.drawings("FIRE"):
        for pl in dr["polys"]:
            wp = [sh.T(x, y) for x, y in pl]
            if len(wp) != 2:
                continue
            a, b = wp
            if all(614 < x < 762 and 1305 < y < 1318 for x, y in wp) and abs(a[1]-b[1]) < .1 and math.dist(a,b) > 3:
                row = round((a[1]+b[1])/2, 1)
                if row in (1305.8, 1316.9):
                    edge_rows[row].append([round(min(a[0],b[0]),1), round(max(a[0],b[0]),1)])
    assert len(edge_rows[1305.8]) >= 8 and len(edge_rows[1316.9]) >= 8
    branch_pairs = []
    for dr in sh.drawings("FIRE"):
        for pl in dr["polys"]:
            wp = [sh.T(x,y) for x,y in pl]
            if len(wp) != 2:
                continue
            a,b = wp
            if all(625 < x < 777 and 1269 < y < 1303 for x,y in wp) and 28 < math.dist(a,b) < 33:
                branch_pairs.append(wp)
    # Three pairs of outline edges bound the three pipe branches.
    assert len(branch_pairs) == 6, len(branch_pairs)
    branch_pairs.sort(key=lambda x: sum(p[0] for p in x)/2)
    branch_axes = []
    for i in range(0,6,2):
        pair=branch_pairs[i:i+2]
        cx=round(sum(p[0] for pl in pair for p in pl)/4,1)
        lo=round(min(p[1] for pl in pair for p in pl),1)
        branch_axes.append([[cx,lo],[cx,1311.4]])
    branch_axes.append([[660.7,1267.2],[660.7,1311.4]])
    pg15=lib.Sheet("MECH2",15,auto_reg=False)
    pg16=lib.Sheet("MECH2",16,auto_reg=False)
    inv11=text_inventory(sh,("ELECTRIC PUMP","DIESEL PUMP","JOCKEY PUMP","750 GPM","40 GPM","VERTICAL TURBINE"))
    assert sum("ELECTRIC PUMP" in t["text"] for t in inv11)==1
    assert sum("DIESEL PUMP" in t["text"] for t in inv11)==1
    assert sum("JOCKEY PUMP" in t["text"] for t in inv11)==1
    labels15=[w["s"] for w in pg15.words() if w["s"] in ("FP-EP","FP-DP","FP-JP")]
    assert collections.Counter(labels15)=={"FP-EP":1,"FP-DP":1,"FP-JP":1},labels15
    return {"units":"cm; z in build is m", "plan_page":11,"registration":sh.reg,
            "pumps":pumps,"pressure_vessel":pressure,
            "header":{"axis_cm":[[614.9,1311.4],[767.1,1311.4]],
                      "edge_rows_cm":dict(edge_rows),"symbol_width_cm":11.1},
            "branches_cm":branch_axes,
            "label_inventory":{"MECH2:11":inv11,"MECH2:15":labels15},
            "nonspatial_details":{"MECH2:15":text_inventory(pg15,("FIRE FIGHTING PUMP SET","6\"Ø","FIRE RESERVE","RCC WATER TANK")),
                                  "MECH2:16":text_inventory(pg16,("PUMP SET","PRESSURE","FOAM","LPG","CLEAN AGENT","HANGER","CABINET"))},
            "limitations":["مخططا FF-105 وFF-106 بلا XY؛ لا هندسة مستخرجة منهما",
                           "نوع Vertical Turbine موثق نصيًا؛ رمز المجموعة مبسط",
                           "منسوب الوصلات وقطر المجمع غير معطيين؛ لا وصلة جديدة خارج المجموعة"]}


if __name__=="__main__":
    d=extract()
    with open(DATA,"w",encoding="utf-8") as f:
        json.dump(d,f,ensure_ascii=False,indent=2)
    print("fire pump extract:",len(d["pumps"]),"pump symbols;",len(d["branches_cm"]),"assembly branches; 1 pressure vessel")
