# -*- coding: utf-8 -*-
"""Main electrical equipment of the ground-floor electrical rooms (HV / transformer / LV / generator) -> pipeline/data/elec_rooms.json
Footprints are the outlines drawn on layer E.POWER of ELEC1 p10 (EP-101 ground power layout, registered to the model); sizes and heights come from
EP-108 (tables: 22 kV switchgear 2500x900x2350, LV metering panel 600x800x1800, transformer 4000x1700x3200, DMS RTU 1000x300x1000, battery rack 1200x500x1290,
48 V DC supply 820x600x2082; MDB 320x80x200 cm from the section).  Room floors are F.F.L. +0.90 (HV, transformer, LV rooms) and +0.35 (generator room) on A102/EP-101.
Not in the documents (flagged): which face of each cabinet is the front, the generator height, the RTU mounting height, the raised-floor build-up."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
els = []
EP = ["ELEC1 ص10 (EP-101 مخطط القدرة للدور الأرضي): مخطط الجهاز على طبقة E.POWER", "ELEC1 ص17 (EP-108 تفاصيل غرف الكهرباء): جدول الأبعاد والمقاطع"]
def add(c, g, mark, typ, mat, attrs, src=None):
    els.append({"c": c, "l": "G", "g": g, "mark": mark, "t": typ, "m": mat, "a": attrs, "src": src or EP})
def b(x0, y0, x1, y1, ang, z0, h, along_y=False):
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2; dx, dy = abs(x1 - x0), abs(y1 - y0)
    return ["b", round(cx, 1), round(cy, 1), round(dy if along_y else dx, 1), round(dx if along_y else dy, 1), 90 if along_y else ang, round(z0, 3), round(z0 + h, 3)]
Z90, Z35 = 0.90, 0.35
FACE = "اتجاه واجهة الجهاز غير مبيّن في المخططات — افتراض (الواجهة نحو الجنوب)"
add("E.panel", b(2715, 903, 3116, 1073, 0, Z90, 3.2), "TRANSFORMER", "det_transformer_dry", "m_panel", {"kind": "transformer", "kva": 1000, "hv_kv": 22, "lv_kv": 0.415, "dims_mm": "4000×1700×3200", "face_note": FACE})
add("E.panel", b(2764, 339, 3037, 592, 0, Z90, 2.35), "22 kV SWITCHGEAR", "det_hv_switchgear", "m_panel", {"kind": "hv_switchgear", "bays": 3, "dims_mm": "3 × (900 × 2500 × 2350)", "face_note": FACE})
add("E.panel", b(2454, 1400, 2777, 1482, 0, Z90, 2.0), "MDB", "det_mdb_2000a", "m_panel", {"kind": "mdb", "amps": 2000, "dims_cm": "320×80×200", "face_note": FACE})
add("E.gen", b(2964, 1260, 3077, 1522, 0, Z35, 1.9, along_y=True), "GENERATOR", "det_generator", "m_gen", {"kind": "generator", "dims_note": "المسقط 260×110 سم (EP-108)؛ الارتفاع 1.90 م افتراض", "face_note": FACE})
add("E.panel", b(2636, 409, 2698, 492, 0, Z90, 1.8), "LV METERING PANEL", "det_lv_metering", "m_panel", {"kind": "lv_metering", "dims_mm": "600×800×1800", "face_note": FACE})
add("E.panel", b(2676, 239, 2778, 272, 0, Z90 + 0.5, 1.0), "DMS RTU", "det_dms_rtu", "m_panel", {"kind": "dms_rtu", "dims_mm": "1000×300×1000", "mount_note": "تركيب جداري على ارتفاع 0.50 م من الأرضية — افتراض (غير مذكور)", "face_note": FACE})
add("E.panel", b(3127, 262, 3174, 379, 0, Z90, 1.29, along_y=True), "BATTERY RACK", "det_battery_rack", "m_panel", {"kind": "battery_rack", "dims_mm": "1200×500×1290", "face_note": FACE})
add("E.panel", b(3117, 401, 3174, 481, 0, Z90, 2.082, along_y=True), "48V DC SUPPLY", "det_dc_supply", "m_panel", {"kind": "dc_supply", "dims_mm": "820×600×2082", "face_note": FACE})
# raised floors (F.F.L. +0.90 against the +0.35 of the rest of the ground floor): concrete build-up under the finishes
PL = [("HV RM", (2635, 240, 3180, 791)), ("TRA. RM", (2635, 810, 3185, 1185)), ("LV RM", (2376, 1270, 2856, 1620))]
for nm, (x0, y0, x1, y1) in PL:
    add("S.slab", ["r", x0, y0, x1, y1, Z35, Z90], f"أرضية مرتفعة — {nm}", "slab_G", "conc", {"kind": "raised_floor", "ffl_m": Z90, "note": "F.F.L. +0.90 م على A102/EP-101؛ بناء الأرضية المرتفعة (خرسانة) افتراض"}, ["ARCH1 ص5 (A102): F.F.L. +0.90 لغرف HV/المحول/LV", "ELEC1 ص10"])
TYPES = {
    "det_transformer_dry": {"n": "محوّل جاف 1000 kVA — 22/0.415 kV", "cf": "derived", "sp": [["الأبعاد (EP-108)", "4000 × 1700 × 3200 مم"], ["القدرة", "1000 kVA، ثلاثي الطور، جاف"], ["الجهد", "22 kV / 0.415 kV"], ["المسقط", "قلب 320×170 سم + صندوق LV + صندوق HV"], ["الغرفة", "غرفة المحول A=19.50 م²، F.F.L. +0.90"]], "asm": ["اتجاه الواجهة وعدد الملفات التفصيلي"], "sr": ["ELEC1 ص17 (EP-108)", "ELEC1 ص16 (المخطط الأحادي)"]},
    "det_hv_switchgear": {"n": "لوحة قواطع 22 kV (3 خلايا)", "cf": "derived", "sp": [["أبعاد الخلية (EP-108)", "2500 × 900 × 2350 مم"], ["التركيب", "FEEDER | TRANSFORMER | FEEDER"], ["الغرفة", "غرفة HV A=30.20 م²، F.F.L. +0.90"]], "asm": ["اتجاه الواجهة", "تفسير الطول 2500 كعمق الخلية"], "sr": ["ELEC1 ص17 (EP-108)", "ELEC1 ص10"]},
    "det_mdb_2000a": {"n": "اللوحة الرئيسية MDB 2000 أمبير", "cf": "derived", "sp": [["الأبعاد", "320 × 80 × 200 سم"], ["القاطع الرئيسي", "ACB 2000 أمبير TPN"], ["القضبان", "نحاس مقلّون 2000 أمبير 4P"], ["قدرة القطع / الحماية", "50 كيلو أمبير / IP54"], ["الغرفة", "غرفة LV A=18.50 م²، F.F.L. +0.90"]], "asm": ["عدد الخلايا (8) وتوزيعها"], "sr": ["ELEC1 ص17 (EP-108)", "ELEC1 ص16 (SLD)"]},
    "det_generator": {"n": "مجموعة مولّد ديزل", "cf": "derived", "sp": [["المسقط", "260 × 110 سم (EP-108)"], ["الغرفة", "غرفة المولّد A=11.50 م²، F.F.L. +0.35"], ["التهوية", "حسب توصية المصنّع"]], "asm": ["القدرة (≈200 kVA) من ATS في المخطط الأحادي", "الارتفاع 1.90 م"], "sr": ["ELEC1 ص17 (EP-108)", "ELEC1 ص16 (SLD)"]},
    "det_lv_metering": {"n": "لوحة قياس الجهد المنخفض", "cf": "derived", "sp": [["الأبعاد (EP-108)", "600 × 800 × 1800 مم"]], "asm": ["اتجاه الواجهة"], "sr": ["ELEC1 ص17 (EP-108)"]},
    "det_dms_rtu": {"n": "وحدة RTU لنظام إدارة التوزيع (DMS)", "cf": "derived", "sp": [["الأبعاد (EP-108)", "1000 × 300 × 1000 مم"]], "asm": ["ارتفاع التركيب الجداري 0.50 م"], "sr": ["ELEC1 ص17 (EP-108)"]},
    "det_battery_rack": {"n": "رف بطاريات 48 فولت", "cf": "derived", "sp": [["الأبعاد (EP-108)", "1200 × 500 × 1290 مم"]], "asm": ["نوع البطاريات وعددها"], "sr": ["ELEC1 ص17 (EP-108)"]},
    "det_dc_supply": {"n": "مزوّد قدرة 48 فولت DC", "cf": "derived", "sp": [["الأبعاد (EP-108)", "820 × 600 × 2082 مم"]], "asm": ["عدد وحدات المقوّم"], "sr": ["ELEC1 ص17 (EP-108)"]},
}
MATS = {"m_gen": {"name": "مولّد ديزل (هيكل)", "color": "#e0a800", "code": "EP-108"}}
json.dump({"els": els, "types": TYPES, "mats": MATS}, open(os.path.join(HERE, "data", "elec_rooms.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("electrical-room elements:", len(els))
