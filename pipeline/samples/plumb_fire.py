# -*- coding: utf-8 -*-
"""plumbing + fire-fighting object samples: valves, water meter, storage heater, sprinklers, fire hose cabinet, floor trap, cleanout"""
from .lib import *

BRASSC = "#c8a24a"; CHROME = "#cfd3d8"
SRC_WS = ["MECH2: مخططات التغذية بالمياه WS-100..102 وتفاصيل ص24"]
SRC_FF = ["MECH2: مخططات الإطفاء FF-100..105 ومفتاح الرموز (طبقة M_FF_SP / M_FF_FFC)", "MECH2 ص16: تفاصيل الإطفاء"]
SRC_DR = ["MECH2: مخططات الصرف DR-100..106"]
ASM = "الشكل التفصيلي قياسي لهذه الفئة (ليس طرازًا محددًا) — الطراز التجاري غير مذكور في المستندات"

def sprinkler(kind):
    """kind: pendent / upright / side. Frame-type quick-response sprinkler, 5 mm glass bulb (red = 68 C), K=5.6 — dimensions typical of the class"""
    if kind == "pendent":
        # anchor top: ceiling plane at y=-0.02; the head hangs below
        P = [cyl((0, -0.32, 0), 3.6, 0.3, "#f4f4f0", "gloss", n="طوق التغطية (Escutcheon) أبيض"), cyl((0, -1.9, 0), 0.9, 1.6, BRASSC, "metal", n="الجسم النحاسي المسنن ½″ NPT"),
             cyl((0, -3.6, 0), 1.15, 1.8, BRASSC, "metal", n="جسم الرشاش"), box((-0.12, -6.8, -1.3), (0.12, -3.6, -0.6), BRASSC, "metal", n="ذراع الإطار 1"), box((-0.12, -6.8, 0.6), (0.12, -3.6, 1.3), BRASSC, "metal", n="ذراع الإطار 2"),
             cyl((0, -6.9, 0), 1.2, 0.35, BRASSC, "metal", r1=0.9, n="مركز الإطار (Boss)"),
             cyl((0, -6.35, 0), 0.28, 2.6, "#d62828", "glass", n="بصيلة الزجاج الحساسة للحرارة (Glass bulb 68 م°)", seg=10), cyl((0, -7.3, 0), 1.85, 0.12, BRASSC, "metal", n="العاكس (Deflector)", seg=22)]
        for k in range(8): P.append(dict(box((1.2, -7.35, -0.12), (1.9, -7.2, 0.12), BRASSC, "metal", n="تسنينة العاكس"), rot=[0, k * 45, 0]))
        return P
    P = [cyl((0, 0, 0), 0.9, 1.6, BRASSC, "metal", n="الجسم النحاسي المسنن ½″"), cyl((0, 1.6, 0), 1.15, 1.8, BRASSC, "metal", n="جسم الرشاش"),
         box((-0.12, 3.4, -1.3), (0.12, 6.6, -0.6), BRASSC, "metal", n="ذراع الإطار 1"), box((-0.12, 3.4, 0.6), (0.12, 6.6, 1.3), BRASSC, "metal", n="ذراع الإطار 2"),
         cyl((0, 3.4, 0), 0.28, 2.6, "#d62828", "glass", n="بصيلة الزجاج (68 م°)", seg=10), cyl((0, 6.4, 0), 1.85, 0.12, BRASSC, "metal", n="العاكس العلوي (Upright deflector)", seg=22)]
    if kind == "double":
        P = [dict(p_, p=[p_["p"][0], f"-{9}+({p_['p'][1]})" if isinstance(p_["p"][1], str) else p_["p"][1] - 0, p_["p"][2]]) if False else p_ for p_ in P]
    return P

def sprinkler_double():
    up = sprinkler("upright"); pend = sprinkler("pendent")
    # pendent below the line (shift down), tee at the pipe level y=0
    shifted = []
    for p in pend:
        q = dict(p)
        if "p" in q: q["p"] = [q["p"][0], (q["p"][1] if isinstance(q["p"][1], (int, float)) else q["p"][1]) - 1.5, q["p"][2]]
        if "a" in q: q["a"] = [q["a"][0], q["a"][1] - 1.5, q["a"][2]]; q["b"] = [q["b"][0], q["b"][1] - 1.5, q["b"][2]]
        shifted.append(q)
    tee = [cyl((0, -1.6, 0), 1.7, 3.2, "#2a2d31", "metal", n="وصلة T (Tee) — حديد أسود"), cyl((-2.2, -0.0, 0), 1.7, 4.4, "#2a2d31", "metal", ax="x", n="خط التغذية ⌀32 مم")]
    return tee + up + shifted

def fhc():
    """recessed fire hose cabinet 88 x 32 x 140 cm: red steel cabinet, glazed door, hose reel + landing valve"""
    R = "#b3261e"
    P = [box(("-W/2", 0, "-D/2"), ("W/2", "H", "D/2"), R, "gloss", n="صندوق الإطفاء (Fire hose cabinet) — صاج أحمر"),
         box(("-W/2+2", 2, "D/2"), ("W/2-2", "H-2", "D/2+1.2"), "#9e1d17", "gloss", n="الباب الأمامي المفصلي"), box(("-W/2+7", 18, "D/2+1.2"), ("W/2-7", "H-30", "D/2+1.5"), "#d6e7ea", "glass", n="لوح زجاج شفاف (Break glass panel)"),
         box(("-W/2+14", "H-22", "D/2+1.2"), ("W/2-14", "H-8", "D/2+1.5"), "#f4f1ea", "matte", n="لافتة «FIRE HOSE»"), box(("W/2-8", "H/2-3", "D/2+1.2"), ("W/2-5", "H/2+10", "D/2+2.6"), STEEL, "metal", n="مقبض الباب"),
         box(("-W/2", 0, "-D/2"), ("-W/2+2", "H", "D/2+1.2"), "#8f1b15", "gloss", n="إطار تثبيت (Surround)")]
    # hose reel (left), landing valve (right)
    P += [cyl(("-W/2+24", "H-70", 0), 22, 9, "#2a2d31", "metal", ax="z", n="بكرة الخرطوم (Hose reel) — ⌀44 سم", seg=26), cyl(("-W/2+24", "H-70", -4.5), 22, 9, "#2a2d31", "metal", ax="z"),
          tor(("-W/2+24", "H-70", 0), 14, 6.5, "#e8e2c8", ax="z", m="matte", n="لفّات الخرطوم المسطح (Lay-flat hose) 30 م"), cyl(("-W/2+24", "H-70", -6), 4, 10, STEEL_D, "metal", ax="z", n="محور البكرة")]
    P += [cyl(("W/2-24", "H-45", "-4"), 3.2, 14, BRASSC, "metal", ax="z", n="صمام هبوط (Landing valve) 2½″ — زاوية نحاسي"), cyl(("W/2-24", "H-45", "10"), 4.2, 3, BRASSC, "metal", ax="z", n="وصلة انسيابية (Instantaneous coupling)"),
          cyl(("W/2-24", "H-37", "-4"), 1.5, 8, BRASSC, "metal", n="جذع الصمام"), tor(("W/2-24", "H-28", "-4"), 6.5, 0.7, "#c0392b", m="gloss", n="عجلة تشغيل الصمام (Handwheel) أحمر"), cyl(("W/2-24", "H-60", "-4"), 3.2, 15, BRASSC, "metal", n="أنبوب التغذية العمودي"),
          cyl(("W/2-24", "H-35", 0), 0.5, 2, "#222", "matte", ax="z", n="مقياس ضغط")]
    P += [cyl(("-W/2+4", 14, "D/2-3"), 3.2, 22, "#d4b255", "metal", ax="y", n="فوهة الخرطوم (Branch pipe nozzle)")]
    return P

def valve_ball():
    return [cyl((-4.5, "H/2", 0), 1.7, 9, "#c8a24a", "metal", ax="x", n="جسم الصمام الكروي (Ball valve) نحاسي"), cyl((0, "H/2", 0), 2.5, 3.2, "#b0893a", "metal", ax="x", n="جسم مركزي"), cyl((-4.5, "H/2", 0), 2.0, 1.2, "#b0893a", "metal", ax="x", n="صامولة وصلة (Union nut)"),
            cyl((4.5, "H/2", 0), 2.0, 1.2, "#b0893a", "metal", ax="x"), cyl((0, "H/2", 0), 0.6, 4.6, STEEL_D, "metal", n="جذع الصمام"), box((-5.5, "H/2+4.4", -0.9), (1.2, "H/2+5.4", 0.9), "#c0392b", "gloss", n="ذراع تشغيل (Lever) أحمر")]

def valve_gate():
    return [cyl((-5, "H/2-2", 0), 1.9, 10, "#b9892f", "metal", ax="x", n="جسم صمام البوابة (Gate valve)"), sph((0, "H/2-2", 0), 3.0, "#a5772a", s=[2.6, 2.8, 2.6], n="جسم مركزي"), cyl((0, "H/2+0.5", 0), 1.3, 3, "#8e949c", "metal", n="غطاء (Bonnet)"),
            cyl((0, "H/2+3.5", 0), 0.45, 3.0, STEEL_D, "metal", n="جذع صاعد (Rising stem)"), tor((0, "H/2+7.2", 0), 3.0, 0.45, "#c0392b", m="gloss", n="عجلة اليد (Handwheel)"), cyl((-5.2, "H/2-2", 0), 2.6, 1.0, "#8e949c", "metal", ax="x", n="شفة"),
            cyl((4.2, "H/2-2", 0), 2.6, 1.0, "#8e949c", "metal", ax="x", n="شفة")]

def water_meter():
    return [cyl((-5.5, "H/2", 0), 1.9, 11, "#c8a24a", "metal", ax="x", n="جسم عداد الماء (Water meter) نحاسي"), cyl((0, "H/2", 0), 3.4, 3.6, "#b0893a", "metal", ax="x", n="غرفة القياس"),
            cyl((0, "H/2+1.5", 0), 3.2, 1.8, "#cfd3d8", "gloss", n="غطاء السجل"), cyl((0, "H/2+3.3", 0), 2.8, 0.25, "#d6e7ea", "glass", n="زجاج السجل"), cyl((0, "H/2+3.2", 0), 2.4, 0.15, "#ffffff", "matte", n="قرص العدّاد (Register dial)"),
            box((-1.5, "H/2+3.35", -0.2), (1.5, "H/2+3.5", 0.2), "#222", "matte", n="مؤشر الأرقام"), cyl((-5.8, "H/2", 0), 2.4, 1.0, "#8e949c", "metal", ax="x", n="وصلة"), cyl((4.6, "H/2", 0), 2.4, 1.0, "#8e949c", "metal", ax="x")]

def heater80():
    # horizontal 80 L storage water heater: W=68 (length), D=43, H=43
    return [cyl(("-W/2+4", "H/2", 0), "H/2-1.5", "W-8", "#f2f2ee", "gloss", ax="x", n="خزان الماء الساخن 80 لتر (Enamelled steel tank) بغلاف أبيض", seg=28),
            sph(("-W/2+4", "H/2", 0), 1, "#e6e6e0", s=[3.5, "H/2-1.5", "H/2-1.5"], n="قبة نهاية — جهة اليسار", seg=22), sph(("W/2-4", "H/2", 0), 1, "#e6e6e0", s=[3.5, "H/2-1.5", "H/2-1.5"], n="قبة نهاية — جهة اليمين", seg=22),
            box(("-W/2", 0, "-5"), ("-W/2+3", "H/2", "5"), STEEL_D, "metal", n="حامل جداري (Wall bracket)"), box(("W/2-3", 0, "-5"), ("W/2", "H/2", "5"), STEEL_D, "metal"),
            cyl((-8, 0, "-6"), 1.3, 12, "#2d8bd6", "gloss", n="مدخل الماء البارد (Cold inlet) ½″"), cyl((8, 0, "-6"), 1.3, 12, "#d94a2a", "gloss", n="مخرج الماء الساخن (Hot outlet) ½″"),
            cyl((-8, -6.5, "-6"), 1.9, 2.6, "#c8a24a", "metal", n="صمام عزل / صمام عدم رجوع"), cyl((8, 3, "-9"), 1.0, 5, "#c8a24a", "metal", n="صمام الأمان T&P"),
            cyl(("W/2-3", "H/2", "H/2-2"), 2.8, 1.6, "#2a2d31", "matte", ax="z", n="ضابط الحرارة (Thermostat dial)"), cyl(("W/2-3", "H/2+4.5", "H/2-2"), 0.5, 0.4, "#ff4136", "emit", ax="z", n="مؤشر التسخين"),
            cyl((-12, 0, "-2"), 0.8, 7, "#222", "rubber", n="كابل التغذية (3×2.5 مم²)")]

def floor_trap():
    return [cyl((0, -0.35, 0), 6.0, 0.35, "#cfd3d8", "metal", n="غطاء المصرف (Stainless grate) ⌀12 سم", seg=24), tor((0, -0.2, 0), 5.8, 0.3, "#9aa1a8", m="metal", n="إطار المصرف"),
            cyl((0, -9, 0), 5.0, 8.6, "#8a6a3a", "matte", n="جسم المصرف PVC مع مصيدة الرائحة (P-trap)"), cyl((0, -9.2, 0), 5.0, 0.6, "#46392a", "matte")] + \
           [dict(box((-5.0, -0.5, -0.18), (5.0, -0.2, 0.18), "#222", "rubber", n="شقّ التصريف"), rot=[0, k * 30, 0]) for k in range(6)]

def cleanout():
    return [cyl((0, -0.3, 0), 6.0, 0.3, "#b9892f", "metal", n="غطاء فتحة التنظيف (Cleanout cover) نحاسي ⌀12 سم", seg=24), box((-1.0, -0.8, -1.0), (1.0, -0.3, 1.0), "#8c6a21", "metal", n="رأس المفتاح المربع (Square key)"),
            cyl((0, -3.0, 0), 5.0, 2.7, "#8a6a3a", "matte", n="جسم فتحة التنظيف"), tor((0, -0.15, 0), 5.7, 0.35, "#8c6a21", m="metal", n="طوق")] + \
           [dict(cyl((3.9, -0.6, 0), 0.4, 0.4, "#8e949c", "metal", n="برغي"), rot=[0, k * 90, 0]) for k in range(4)]

def make():
    out = {}
    def add(t): out[t[0]] = t[1]
    def S(id_, name, en, parts, place, cat="plumbing", lod=4.0, conf="derived", facts=None, asm=None, src=None, dims=None, **kw):
        add(sample(id_, name, en, cat, parts, place=place, lod=lod, conf=conf, src=src or [], facts=facts or [], asm=(asm or []) + [ASM], dims=dims or {}, **kw))
    B = {"mode": "box", "anchor": "bottom"}; C = {"mode": "cyl", "anchor": "top"}
    S("valve_IV", "صمام عزل (IV) كروي", "Isolation ball valve", valve_ball(), B, src=SRC_WS, facts=[["الوسم", "IV على M_WS_TEXT"], ["الاستخدام", "عزل فروع المياه الباردة/الساخنة"]], dims={"W": 9, "D": 9, "H": 12})
    S("valve_WM", "عداد مياه (W/M)", "Water meter", water_meter(), B, src=SRC_WS, facts=[["الوسم", "W/M"]], dims={"W": 9, "D": 9, "H": 12})
    S("valve_GV", "صمام بوابة (GV)", "Gate valve", valve_gate(), B, src=SRC_WS, facts=[["الوسم", "GV"]], dims={"W": 9, "D": 9, "H": 12})
    S("heater80", "سخان مياه كهربائي أفقي 80 لتر", "Horizontal storage water heater 80 L", heater80(), B, lod=6, src=SRC_WS, facts=[["السعة", "50 لتر / 1.2 كيلوواط أو 80 لتر / 1.5 كيلوواط (مفتاح المخطط)"], ["النوع", "سخان كهربائي أفقي مخزّن"]], asm=["السعة المعروضة 80 لتر حسب المخطط حيث لم يُذكر خلافها"], dims={"W": 68, "D": 43, "H": 43})
    S("sprk_pendent", "رشاش إطفاء هابط (Pendent)", "Pendent sprinkler (glass bulb)", sprinkler("pendent"), C, cat="fire", lod=3.5, src=SRC_FF, facts=[["النوع", "رشاش هابط — بصيلة زجاج 68 م°"], ["الوصلة", "½″"], ["معامل K", "5.6 (قياسي)"]], asm=["الاستجابة (سريعة/قياسية) ومعامل K ودرجة التفعيل: قياسية"], dims={"W": 8, "D": 8, "H": 10})
    S("sprk_upright", "رشاش إطفاء قائم (Upright)", "Upright sprinkler (glass bulb)", sprinkler("upright"), {"mode": "cyl", "anchor": "bottom"}, cat="fire", lod=3.5, src=SRC_FF, facts=[["النوع", "رشاش قائم فوق الأنبوب"]], dims={"W": 8, "D": 8, "H": 10})
    S("sprk_double", "رشاش مزدوج (هابط + قائم)", "Double sprinkler (pendent & upright)", sprinkler_double(), {"mode": "cyl", "anchor": "center"}, cat="fire", lod=3.5, src=SRC_FF, facts=[["النوع", "رشاشان على وصلة T: هابط وقائم"]], dims={"W": 8, "D": 8, "H": 10})
    S("fhc", "صندوق إطفاء بصمام هبوط (FHC)", "Fire hose cabinet with landing valve", fhc(), {"mode": "box", "anchor": "bottom", "mount": "wall"}, cat="fire", lod=6, conf="doc", src=SRC_FF + ["طبقة FHC المعمارية: تجويف 32×88 سم"],
      facts=[["البصمة", "88 × 32 سم من تجويف المخطط"], ["المحتوى", "بكرة خرطوم + صمام هبوط 2½″"], ["الخط", "خط FFC قطر 6″ (مخطط FF-105)"]], asm=["الارتفاع 1.4 م وبدايته 0.5 م: افتراض", "طول الخرطوم وتفاصيل البكرة والفوهة: قياسية"], dims={"W": 88, "D": 32, "H": 140})
    S("floor_trap", "مصرف أرضي (FT)", "Floor trap", floor_trap(), C, src=SRC_DR, facts=[["الوسم", "FT / FW (M_DR_TEXT)"]], dims={"W": 12, "D": 12, "H": 3})
    S("cleanout", "فتحة تنظيف (CO)", "Cleanout", cleanout(), C, src=SRC_DR, facts=[["الوسم", "CO / FCO (M_DR_TEXT)"]], dims={"W": 12, "D": 12, "H": 3})
    return out

RULES = [{"c": "P.cold", "t": "valve_IV", "s": "valve_IV"}, {"c": "P.cold", "t": "valve_WM", "s": "valve_WM"}, {"c": "P.cold", "t": "valve_GV", "s": "valve_GV"}, {"c": "P.heater", "t": "heater80", "s": "heater80"},
         {"c": "P.ff", "t": "sprk_pendent", "s": "sprk_pendent"}, {"c": "P.ff", "t": "sprk_upright", "s": "sprk_upright"}, {"c": "P.ff", "t": "sprk_double", "s": "sprk_double"}, {"c": "P.ff", "t": "fhc", "s": "fhc"},
         {"c": "P.drain", "t": "floor_trap", "s": "floor_trap"}, {"c": "P.drain", "t": "cleanout", "s": "cleanout"}]
