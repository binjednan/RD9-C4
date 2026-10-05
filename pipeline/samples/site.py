# -*- coding: utf-8 -*-
"""site-surface samples (catalog only: polygons of the landscape are too irregular for automatic swapping) + RC core walls"""
from .lib import *
from . import struct as _st

def layered(top, thk_top, name_top, extra):
    P = [box(("-W/2", 0, "-D/2"), ("W/2", thk_top, "D/2"), top, "matte", n=name_top)]
    y = 0
    for (c, t, nm, mat) in extra:
        P.append(box(("-W/2", f"-{y+t}", "-D/2"), ("W/2", f"-{y}", "D/2"), c, mat, n=nm)); y += t
    return P

def make():
    out = {}
    def add(t): out[t[0]] = t[1]
    SRC = ["ARCH1 ص3 و5: A100/A102 (الموقع والدور الأرضي)", "صور الموقع 7 أغسطس (docs/SITE_PHOTOS.md)"]
    N = {"mode": "none"}
    add(sample("site_asphalt", "أسفلت الممر والمواقف (طبقات)", "Asphalt road build-up", "architecture", layered("#4b5057", 5, "طبقة سطحية أسفلتية 5 سم", [("#3a3d42", 6, "طبقة رابطة 6 سم", "matte"), ("#9a9488", 25, "أساس حبيبي مدموك", "matte"), ("#bda97d", 15, "تربة مدموكة", "matte")]) +
               [rep(box(("-W/2", 5, "-D/2"), ("W/2", 5.05, "-D/2+0.1"), "#3a3d42", "matte"), "1", (0, 0, 0))], place=N, conf="assumed", src=SRC, facts=[["الاستخدام", "ممر القيادة والمواقف (A102)"]],
               asm=["التشطيب أسفلت افتراضًا؛ سماكات الطبقات قياسية (غير مذكورة)"], dims={"W": 200, "D": 150, "H": 5}))
    add(sample("site_mark", "علامات مرورية وخطوط مواقف (طلاء ترموبلاستيك)", "Road markings", "architecture",
               [box(("-W/2", 0, "-D/2"), ("W/2", 5, "D/2"), "#4b5057", "matte", n="سطح الأسفلت"), box(("-5", 5, "-D/2"), ("5", 5.35, "D/2"), "#f2f2ee", "gloss", n="خط طلاء أبيض 10 سم (ترموبلاستيك 3.5 مم)"),
                rep(box(("-4.5", 5.35, "-D/2"), ("-3.5", 5.5, "-D/2+0.6"), "#ffffff", "emit", n="خرز زجاجي عاكس"), "floor(D/20)", (0, 0, 20))], place=N, conf="derived", src=SRC, facts=[["العرض", "10 سم (وحدة المواقف 2.7 م)"]], asm=["السماكة والخرز العاكس: قياسية"], dims={"W": 100, "D": 100, "H": 5}))
    add(sample("site_grass", "عشب طبيعي (طبقات)", "Natural grass", "architecture",
               [box(("-W/2", 0, "-D/2"), ("W/2", 3, "D/2"), "#6f9f4f", "matte", n="طبقة العشب الحي (Turf) 3 سم"), box(("-W/2", -15, "-D/2"), ("W/2", 0, "D/2"), "#8a6a45", "matte", n="تربة زراعية 15 سم"), box(("-W/2", -25, "-D/2"), ("W/2", -15, "D/2"), "#bda97d", "matte", n="رمل/تربة مدموكة")] +
               [rep(cyl(("-W/2+5", 3, "-D/2+5"), 0.15, 5, "#4f8a3a", "matte", r1=0.02, seg=5, n="نصل عشب"), "floor(W/10)", (10, 0, 0))], place=N, conf="derived", src=SRC, facts=[["الطبقة في A102", "L1-THIN"]], asm=["منسوب العشب من نقاط F.L. على المخطط؛ السماكات قياسية", "في الصور (7 أغسطس) المسطحات ما زالت ترابًا بلا عشب"], dims={"W": 100, "D": 100, "H": 3}))
    add(sample("site_paving", "رصف إنترلوك رمادي (مربعات 20×20)", "Interlock paving", "architecture",
               [box(("-W/2", 0, "-D/2"), ("W/2", 6, "D/2"), "#9a958d", "matte", n="بلاط إنترلوك 6 سم (F13)"), rep(box(("-W/2", 6, "-D/2"), ("W/2", 6.05, "-D/2+0.5"), "#c9b99c", "matte", n="فاصل رملي"), "floor(D/20)+1", (0, 0, 20)),
                rep(box(("-W/2", 6, "-D/2"), ("-W/2+0.5", 6.05, "D/2"), "#c9b99c", "matte", n="فاصل رملي"), "floor(W/20)+1", (20, 0, 0)), box(("-W/2", -3, "-D/2"), ("W/2", 0, "D/2"), "#d9c9a0", "matte", n="طبقة رمل 3 سم"), box(("-W/2", -23, "-D/2"), ("W/2", -3, "D/2"), "#9a9488", "matte", n="أساس حبيبي")],
               place=N, conf="derived", src=SRC, facts=[["النوع في A500", "F13/F14: إنترلوك 60/80 مم"]], asm=["قياس البلاطة 20×20 وطبقات الأساس: من صور الموقع تقريبًا", "النوع (60 أم 80 مم) غير محدد على A102"], dims={"W": 100, "D": 100, "H": 6}))
    add(sample("site_rubber", "بلاط مطاطي خارجي 100 مم (منطقة ألعاب الأطفال F15)", "Outdoor rubber tile", "architecture",
               [box(("-W/2", 0, "-D/2"), ("W/2", 10, "D/2"), "#6e7a6a", "matte", n="بلاط مطاطي 100 مم (F15)"), rep(box(("-W/2", 10, "-D/2"), ("W/2", 10.05, "-D/2+0.3"), "#4f5a4c", "matte", n="فاصل بلاط 50×50"), "floor(D/50)+1", (0, 0, 50)),
                rep(box(("-W/2", 10, "-D/2"), ("-W/2+0.3", 10.05, "D/2"), "#4f5a4c", "matte"), "floor(W/50)+1", (50, 0, 0)), box(("-W/2", -3, "-D/2"), ("W/2", 0, "D/2"), "#c9c4b6", "matte", n="طبقة تسوية")], place=N, conf="derived", src=SRC, facts=[["الكود", "F15"]], asm=["قياس البلاطة 50×50: افتراض"], dims={"W": 100, "D": 100, "H": 10}))
    add(sample("site_paving_tiles", "بلاط خرساني 30×30 (F12)", "Concrete paving slabs 300x300", "architecture", layered("#a9a9a4", 3, "بلاط خرساني 300×300×30 مم", [("#d9c9a0", 3, "رمل", "matte")]), place=N, conf="derived", src=SRC, dims={"W": 100, "D": 100, "H": 3}))
    add(sample("site_shade", "مظلة ظل شراعية (Tensile shade sail) على عمود فولاذي", "Tensile shade sail", "architecture",
               [cyl((0, 0, 0), 12, 500, "#4a4f55", "metal", seg=20, n="عمود فولاذي دائري ⌀25 سم — رمادي داكن (من صور الموقع)"), cyl((0, 0, 0), 20, 3, "#3b3f45", "metal", n="لوح قاعدة"),
                ext([[0, 0], [380, 90], [250, -240]], 0.5, "#d9cdb0", "matte", p=(0, 470, 0), n="غشاء الشراع المثلثي (بيج) — تقريبي"), cyl((380, 470, 90), 1.5, 30, "#8e949c", "metal", ax="y", n="نقطة تثبيت الشراع (D-ring)")],
               place=N, conf="assumed", src=["صور الموقع 7 أغسطس (docs/SITE_PHOTOS.md) — لا يوجد مخطط للأشرعة"], facts=[["النوع", "أشرعة مثلثة متعددة على أعمدة (كما في الصور)"], ["في A102", "مظلة دائرية ثمانية 6.2 م (LINEA-1/2)"]],
               asm=["الأبعاد من التقدير البصري للصور فقط؛ يوجد اختلاف جوهري بين المصمَّم (دائرية) والمنفَّذ (شراعية) — بانتظار مخططات التنفيذ"], dims={"W": 400, "D": 300, "H": 500}))
    # RC core walls (polygons, not rectangles) — catalog
    core = _st.wall_rc(25, 10, 15)
    add(sample("wall_rc", "جدار/نواة خرسانية مسلّحة (قطاع نموذجي)", "RC core wall typical", "structure", core, place={"mode": "none"}, conf="derived", src=_st.SRC_C, facts=[["السماكة", "20–25 سم"]], asm=["نواة المصاعد وجدران القص غير مستطيلة: لا يوجد استبدال تلقائي؛ التسليح من W1–W3 (T25@15 وT10@15)"], dims={"W": 200, "D": 25, "H": 320}))
    return out

RULES = [{"c": "A.site", "t": t, "s": t} for t in ("site_asphalt", "site_mark", "site_grass", "site_paving", "site_rubber")] + [{"c": "A.stage", "t": "site_shade", "s": "site_shade"}] + \
        [{"c": "S.wall", "t": t, "s": "wall_rc"} for t in ("col_CORE", "col_core", "wall_rc", "col_wall", "wall_base300")]
