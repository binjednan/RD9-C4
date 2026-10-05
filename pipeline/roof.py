# -*- coding: utf-8 -*-
"""Roof (level R) equipment extraction -> pipeline/data/roof.json   (needs the source PDFs, see lib.py)

Sources:  MECH1 p15 (CHW-104 roof chilled-water connection layout 1:50)  -> chillers, fans, CHW pumps, FAHU, CHW pipes, fence
          MECH1 p16 (CHW-105 chilled-water riser diagram + schedule of chillers / pumps) -> capacities, dimensions, weights
          MECH1 p6  (AC layout of the roof)  -> FCUs / ducts / outlets of the roof rooms (same extractor as the typical floors)
Documented (p16): 2 chillers, 70 TR each, screw compressors, R-134a, 110 kW each, L 3.6 x W 2.5 x H 2.5 m, 3368 kg; 3 CHW pumps (2 duty + 1
standby), 168 GPM @ 100 ft, 1450 rpm VFD, 6.5 kW (estimated), horizontal split case.
Heights/positions not in the documents are flagged as assumptions in each element.
"""
import sys, os, json, math, re, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lib, geo, mep_common as MC, pipes as PP, plumb, hvac
import assemble_arch as AA

LEVEL, FFL = "R", AA.FFL["R"]
S15, S16, S6 = "MECH1 ص15 (CHW-104 مخطط السطح للمياه المبردة 1:50)", "MECH1 ص16 (CHW-105 مخطط الأعمدة الرأسية + جداول المبرّدات والمضخات)", "MECH1 ص6 (مخطط التكييف للسطح)"
els = []

def add(c, g, mark=None, typ=None, mat="conc", attrs=None, src=None, u=None, u2=None, level=LEVEL, **kw):
    e = {"c": c, "l": level, "g": g, "mark": mark, "t": typ, "m": mat, "a": attrs or {}, "src": src or []}
    els.append(e)

ROOM_DZ = -0.06      # roof rooms are 3.05 m high (R ffl 23.35 -> slab T at 26.40) vs 3.5 m on the typical floors: keep the void equipment below the slab
def _shift(g, dz):
    if g[0] == "b": g[6] = round(g[6] + dz, 3); g[7] = round(g[7] + dz, 3)
    elif g[0] == "r": g[5] = round(g[5] + dz, 3); g[6] = round(g[6] + dz, 3)
    elif g[0] == "cyl": g[4] = round(g[4] + dz, 3); g[5] = round(g[5] + dz, 3)
    elif g[0] in ("d", "t"):
        for p_ in g[1]: p_[2] = round(p_[2] + dz, 3)

def hvac_add(c, level, g, mark=None, typ=None, mat="conc", attrs=None, src=None, u=None, u2=None, flat_no=None, grp=None):
    _shift(g, ROOM_DZ)
    src = list(src or []) + ["ارتفاع غرف السطح 3.05 م (مقابل 3.5 م): خُفض المنسوب 6 سم ليبقى تحت بلاطة T — افتراض"]
    e = {"c": c, "l": level, "g": g, "mark": mark, "t": typ, "m": mat, "a": attrs or {}, "src": src or []}
    if grp: e["grp"] = grp
    els.append(e)

def rect(x0, y0, x1, y1): return ["r", round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)]

def main():
    ref = lib.Sheet("ARCH1", 8)
    sh = lib.Sheet("MECH1", 15, ref=ref)
    # ---------------------------------------------------------------- chillers (plan outline 480 x 250, 6 fans each)
    outlines = [s for s in MC.closed_shapes(sh, "M_HVAC_EQP") if s["n"] == 5 and 440 <= s["w"] <= 520 and 220 <= s["h"] <= 280]
    fans = [s for s in MC.closed_shapes(sh, "M_HVAC_EQP") if s["n"] == 41 and 80 <= s["w"] <= 92]
    labels = [(sp["s"], sp["X"], sp["Y"]) for sp in MC.spans(sh, "M_HVAC_TEXT") if sp["s"].startswith("CHILLER-")]
    outlines.sort(key=lambda s: s["c"][0])
    for k, o in enumerate(outlines, 1):
        cx, cy = o["c"]; w, h = o["w"], o["h"]
        tag = min(labels, key=lambda l: math.hypot(l[1] - cx, l[2] - cy))[0] if labels else f"CHILLER-{k}"
        add("M.equip", ["r", round(cx - w / 2, 1), round(cy - h / 2, 1), round(cx + w / 2, 1), round(cy + h / 2, 1), FFL, FFL + 2.5], mark=tag, typ="chiller", mat="m_chiller",
            attrs={"kind": "chiller", "h_m": 2.5, "size_note": f"مسقط الرسم {round(w)}×{round(h)} سم؛ الجدول: L 3.6 × W 2.5 × H 2.5 م (الطول مختلف — بانتظار تأكيدك)"},
            src=[f"{S15} طبقة M_HVAC_EQP (مسقط المبرّد)", f"{S16}: جدول المبرّدات — 70 TR لكل مبرّد، 110 كيلوواط، 3368 كجم، L 3.6 × W 2.5 × H 2.5 م"])
        for f in fans:
            if abs(f["c"][0] - cx) <= w / 2 and abs(f["c"][1] - cy) <= h / 2:
                add("M.fan", ["cyl", round(f["c"][0], 1), round(f["c"][1], 1), round(f["w"] / 2, 1), FFL + 2.5, FFL + 2.56], mark=tag + " FAN", typ="chiller_fan", mat="m_fan_guard",
                    attrs={"dia_cm": round(f["w"])}, src=[f"{S15} طبقة M_HVAC_EQP (مروحة المبرّد، قطر {round(f['w'])} سم)", "ارتفاع حلقة المروحة فوق المبرّد: افتراض"])
    # ---------------------------------------------------------------- chilled-water pumps (3: 2 duty + 1 standby) in the pump room
    pumps = sorted([s for s in MC.closed_shapes(sh, "AC") if 55 <= s["w"] <= 70 and 115 <= s["h"] <= 135], key=lambda s: s["c"][0])
    for k, p in enumerate(pumps, 1):
        cx, cy = p["c"]
        add("M.equip", ["r", round(cx - p["w"] / 2, 1), round(cy - p["h"] / 2, 1), round(cx + p["w"] / 2, 1), round(cy + p["h"] / 2, 1), FFL, FFL + 0.9], mark=f"CHWP-0{k}", typ="chwp", mat="m_pump",
            attrs={"kind": "pump", "assumed_h": 0.9, "duty": "احتياطية" if k == 3 else "عاملة"},
            src=[f"{S15} طبقة AC (مسقط المضخة) ووسم CHWP-0{k}", f"{S16}: جدول مضخات المياه المبردة — 3 (2 عاملة / 1 احتياط)، 168 GPM @ 100 قدم، 1450 د/د بمبدّل VFD، 6.5 كيلوواط (تقديري)", "ارتفاع المضخة مع المحرك: افتراض"])
    # ---------------------------------------------------------------- FAHU (fresh-air handling unit) outline from its layer
    xs, ys = [], []
    for d in sh.D:
        if d["layer"] == "AC D FRESH":
            for pl in d["polys"]:
                w = [sh.T(x, y) for x, y in pl]
                if all(340 <= p[0] <= 700 and 1290 <= p[1] <= 1520 for p in w):
                    xs += [p[0] for p in w]; ys += [p[1] for p in w]
    if xs:
        add("M.equip", ["r", round(min(xs), 1), round(min(ys), 1), round(max(xs), 1), round(max(ys), 1), FFL, FFL + 1.8], mark="FAHU", typ="fahu", mat="m_fahu",
            attrs={"kind": "fahu", "assumed_h": 1.8}, src=[f"{S15} طبقة AC D FRESH (وحدة معالجة الهواء النقي FAHU)", "الارتفاع 1.8 م: افتراض (غير مذكور)"])
    # ---------------------------------------------------------------- chilled-water pipes on the roof (supply + return) with sizes from the plan texts
    labs = []
    for sp in MC.spans(sh, "M_HVAC_TEXT"):
        m = re.search(r"(\d{2,3})\s*mm", sp["s"])
        if m: labs.append({"v": (int(m.group(1)),), "x": sp["X"], "y": sp["Y"], "s": sp["s"]})
    for name, layers, typ, mat, dz, nm in (("S", ("M_CHI_S", "MECH-CHWS-CHILLED WATER SUPPLY"), "pipe_chws", "m_chws", 0.50, "تغذية"), ("R", ("M_CHI_R",), "pipe_chwr", "m_chwr", 0.35, "رجوع")):
        segs = PP.axis_merge(PP.layer_segments(sh, layers), gap=8)
        sized = PP.assign_sizes(segs, labs)
        for d, pl, labeled in plumb._polys_from_segs(sized, 20):
            if geo.polyline_len(pl) < 6: continue
            add("M.pipe", ["t", [[round(p[0], 1), round(p[1], 1), FFL + dz] for p in pl], round(max(d / 10.0, 2.2), 1)], typ=typ, mat=mat,
                attrs={"dia_mm": d, "length_m": round(geo.polyline_len(pl) / 100, 2), "dia_note": "من وسم المخطط" if labeled else "افتراضي 20 مم (قطر فروع FCU في جدول التكييف)", "kind": nm},
                src=[f"{S15} طبقات M_CHI_S / M_CHI_R (مياه مبردة — {nm})", "منسوب الأنابيب فوق السطح (على مساند): افتراض"])
    # ---------------------------------------------------------------- roof fence (layer '2m HEIGHT FENCING'; the plan text says 1.8 m with foundation)
    fl = [pl for pl, d in sh.polys("XR-104-ROOF FLOOR PLAN$0$X-AD738-Roof Floor Plan$0$2m HEIGHT FENCING")]
    fl = [pl for pl in fl if len(pl) >= 3]
    if fl:
        pl = max(fl, key=lambda p: geo.polyline_len(p))
        for a, b in zip(pl[:-1], pl[1:]):
            if math.hypot(b[0] - a[0], b[1] - a[1]) < 2: continue
            x0, x1 = sorted((a[0], b[0])); y0, y1 = sorted((a[1], b[1]))
            add("A.rail", ["r", round(x0 - 3, 1), round(y0 - 3, 1), round(x1 + 3, 1), round(y1 + 3, 1), FFL, FFL + 1.8], mark="FENCE-R", typ="fence_roof", mat="frame_alu",
                attrs={"kind": "fence", "h_m": 1.8, "dim_note": "الارتفاع 1.8 م من نص المخطط («1.8m HEIGHT FENCING WITH FOUNDATION»)؛ اسم الطبقة يذكر 2 م — بانتظار تأكيدك"},
                src=[f"{S15} طبقة 2m HEIGHT FENCING + نص الارتفاع"])
    # ---------------------------------------------------------------- roof AC layout: FCUs of the roof rooms, ducts, outlets (same extractor as the typical floors)
    try:
        R6 = hvac.extract_ac(6, 8)
        hvac.emit_ac(hvac_add, LEVEL, R6, None, FFL, floor_label="R")
    except Exception as ex:                                  # keep the rest if this sheet needs special handling
        print("roof AC layout skipped:", ex)
    types = {
        "chiller": {"n": "مبرّد مياه مبرّدة بالهواء (Screw) 70 TR", "cf": "doc",
                    "sp": [["السعة", "70 TR لكل مبرّد (2 مبرّد)"], ["النوع", "ضاغط لولبي Screw — غاز R-134a"], ["القدرة الكهربائية", "110 كيلوواط لكل مبرّد، 415 فولت / 3 أطوار / 50 هرتز"],
                           ["درجة حرارة الدخول / الخروج", "12 م° / 7 م°"], ["تدفق المياه", "168 GPM"], ["الأبعاد (الجدول)", "L 3.6 × W 2.5 × H 2.5 م"], ["الوزن", "3368 كجم"]],
                    "asm": ["مسقط الرسم 4.8×2.5 م يختلف عن طول الجدول 3.6 م — بانتظار تأكيدك"], "sr": [S16, S15]},
        "chwp": {"n": "مضخة مياه مبرّدة (Split case أفقية)", "cf": "derived",
                 "sp": [["العدد", "3 (2 عاملة + 1 احتياط)"], ["التدفق والضغط", "168 GPM عند 100 قدم (تقديري)"], ["السرعة", "1450 د/د بمبدّل VFD"], ["قدرة المحرك", "6.5 كيلوواط (تقديري)"], ["النوع", "Horizontal split case"]],
                 "asm": ["ارتفاع المضخة مع المحرك 0.9 م: افتراض"], "sr": [S16, S15]},
        "fahu": {"n": "وحدة معالجة الهواء النقي (FAHU)", "cf": "derived", "sp": [["الاسم", "FAHU — Fresh Air Handling Unit"]], "asm": ["الارتفاع 1.8 م والأبعاد التفصيلية: افتراض"], "sr": [S15]},
        "chiller_fan": {"n": "مروحة مبرّد", "cf": "derived", "sp": [], "asm": ["ارتفاع الحلقة فوق المبرّد: افتراض"], "sr": [S15]},
        "pipe_chws": {"n": "أنبوب مياه مبرّدة — تغذية", "cf": "derived", "sp": [], "asm": ["منسوب الأنابيب فوق السطح: افتراض"], "sr": [S15]},
        "pipe_chwr": {"n": "أنبوب مياه مبرّدة — رجوع", "cf": "derived", "sp": [], "asm": ["منسوب الأنابيب فوق السطح: افتراض"], "sr": [S15]},
        "fence_roof": {"n": "سياج السطح 1.8 م مع أساس", "cf": "derived", "sp": [["الارتفاع", "1.8 م (نص المخطط)"]], "asm": ["الاسم في الطبقة يذكر 2 م"], "sr": [S15]},
    }
    mats = {"m_chiller": {"name": "مبرّد مياه مبرّدة (هيكل)", "color": "#c7d2dc", "code": "MECH1 ص15"}, "m_fan_guard": {"name": "مروحة مبرّد", "color": "#3b3f45", "code": "MECH1 ص15"},
            "m_pump": {"name": "مضخة مياه مبرّدة", "color": "#4d5b6a", "code": "MECH1 ص15"}, "m_fahu": {"name": "وحدة FAHU", "color": "#9db7cf", "code": "MECH1 ص15"},
            "m_chws": {"name": "أنبوب مياه مبرّدة — تغذية", "color": "#2d8bd6", "code": "M_CHI_S"}, "m_chwr": {"name": "أنبوب مياه مبرّدة — رجوع", "color": "#e07b39", "code": "M_CHI_R"}}
    json.dump({"els": els, "types": types, "mats": mats}, open(os.path.join(HERE, "data", "roof.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    c = collections.Counter((e["c"], e["t"]) for e in els)
    print("roof elements", len(els)); [print("  ", k, v) for k, v in sorted(c.items())]

if __name__ == "__main__":
    main()
