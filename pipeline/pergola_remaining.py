# -*- coding: utf-8 -*-
"""Three roof equipment canopies actually drawn in A106, detailed in A1700.

XY comes from stored raw PDF polygons. The height follows A1700; no anchors,
supports, or manufacturer wall gauges are added. Stable PG suffix; no model I/O.
"""
import collections
import copy
import json
import os
import re
from shapely.geometry import Polygon

DATA = os.path.join(os.path.dirname(__file__), "data", "pergola_remaining.json")
ID_RE = re.compile(r"-PG\d{4}$")
MATS = {
    "pg_aluminium_wood": {"name": "ألمنيوم PPC بتأثير خشب،80 ميكرون — A1700", "color": "#a38a6a", "metal": .35, "rough": .55},
}
TYPES = {
    "roof_pergola_frame": {"n": "إطار برجولة معدات السطح", "cf": "doc", "sp": [["الموضع", "حدود خارجية وداخلية مرسومة في A106"], ["الوحدات", "1200×300،700×300،400×250 سم من A1700"], ["المنسوب", "FFL+23.35؛ ارتفاع كلي295 سم،إطار20 سم فوق الأعمدة275 سم"]], "sr": ["ARCH1 ص8–9 A105/A106", "ARCH2 ص36 A1700"], "asm": ["غلاف الإطار يطابق المسقط؛ سماكة جدار قطاع الألمنيوم والتثبيت غير معتمدة"]},
    "roof_pergola_post": {"n": "عمود برجولة معدات السطح", "cf": "doc", "sp": [["الموضع", "22 عمودًا:10 للمبرّدات،6 لخزاني GRP،6 لـFAHU"], ["الارتفاع", "275 سم من قطاعات A1700"], ["المقطع", "حدود المقطع الخارجية والداخلية من رمز A106،عرض اسمي15 سم"]], "sr": ["ARCH1 ص9 A106", "ARCH2 ص36 A1700"], "asm": ["جدار القطاع مقروء من الرمز،ليس سماكة توريد مكتوبة؛ القواعد والمراسي غير ممثلة"]},
    "roof_pergola_slat": {"n": "شريحة برجولة معدات السطح", "cf": "doc", "sp": [["الموضع", "88 شريحة مرسومة:47+27+14؛ الحدود الأصلية محفوظة"], ["المقطع بالنص", "Aluminum Box150/100؛ PPC80 microns wood effect"]], "sr": ["ARCH1 ص9 A106", "ARCH2 ص36 A1700"], "asm": ["توجيه150 مم رأسيًا و100 مم أفقيًا افتراض يتفق مع عرض المسقط؛ سماكة جدار القطاع والتثبيت غير معتمدين"]},
}


def _prism(outline, inner, z0, z1):
    p = Polygon(outline, [inner] if inner else None)
    assert p.is_valid and p.area > 0
    return ["p", [[round(x, 2), round(y, 2)] for x, y in list(p.exterior.coords)[:-1]], round(z0, 3), round(z1, 3),
            [[[round(x, 2), round(y, 2)] for x, y in list(h.coords)[:-1]] for h in p.interiors] or None]


def build(M, els, verbose=False):
    els[:] = [e for e in els if not ID_RE.search(e["id"])]
    with open(DATA, encoding="utf-8") as f:
        D = json.load(f)
    M.setdefault("mats", {}).update(copy.deepcopy(MATS))
    M.setdefault("types", {}).update(copy.deepcopy(TYPES))
    for layer in M["layers"]:
        if layer["id"] == "A" and not any(s[0] == "A.pergola" for s in layer["subs"]):
            layer["subs"].append(["A.pergola", "برجولات معدات السطح من A106/A1700"])
    n = 0
    stats = collections.Counter()
    for unit in D["units"]:
        source = unit["source_reference"] + "؛ مادة ومقاسات وارتفاعات من ARCH2 ص36 A1700. مواضع المسقط من المحاور الأصلية دون إزاحة."
        if source not in M["sp"]:
            M["sp"].append(source)
        si = M["sp"].index(source)
        for part in unit["parts"]:
            n += 1
            kind = part["kind"]
            typ = "roof_pergola_" + kind
            stats[typ] += 1
            z0, z1 = {"post": (23.35, 26.10), "frame": (26.10, 26.30), "slat": (26.15, 26.30)}[kind]
            assumed = {"post": "جدار القطاع مقروء من رمز المسقط،ليس سماكة توريد مكتوبة؛ لم تضف قواعد أو مراسي",
                       "frame": "سماكة جدار قطاع الإطار والوصلات غير محددة؛ الغلاف يطابق الحدين المرسومين",
                       "slat": "توجيه قطاع150/100 مم:150 مم رأسي و100 مم أفقي افتراض؛ جدار القطاع والوصلات غير ممثلين"}[kind]
            a = {"source_kind": "drawn_polygon", "source_reference": unit["source_reference"],
                 "source_set": "ARCH1", "source_page": 9, "source_layer": part["layer"],
                 "source_drawing_indices": part["drawing_indices"], "source_pdf_points": part["pdf_points"],
                 "source_transform": copy.deepcopy(D["registration"]), "source_xy": part["xy"], "source_xy_units": "cm",
                 "source_inner_pdf_points": part.get("inner_pdf_points"), "source_inner_xy": part.get("inner_xy"),
                 "source_z_reference": "ARCH1 ص8–9:FFL+23.35؛ ARCH2 ص36 A1700 قطاعات3/6/9:275+20=295سم",
                 "ffl_m": 23.35, "height_above_ffl_cm": [round((z0-23.35)*100), round((z1-23.35)*100)],
                 "unit": unit["id"], "assumed": assumed,
                 "registration": "تحويل محاور A106 الأصلي؛ لا snap أو إزاحة إلى المجسم"}
            els.append({"id": f"A.pergola-R-PG{n:04d}", "c": "A.pergola", "l": "R",
                        "g": _prism(part["xy"], part.get("inner_xy"), z0, z1), "t": typ, "m": "pg_aluminium_wood",
                        "mark": unit["name_ar"], "grp": "PG-"+unit["id"], "a": a, "s": [si]})
    M.setdefault("meta", {})["pergola_remaining"] = {"count": n, "by_type": dict(stats),
        "units": [{k: copy.deepcopy(v) for k, v in unit.items() if k != "parts"} for unit in D["units"]],
        "registration": copy.deepcopy(D["registration"]), "source_file": "pipeline/data/pergola_remaining.json",
        "limits": copy.deepcopy(D["limits"])}
    if verbose:
        print("roof source pergolas:", n, dict(stats))
    return dict(stats)
