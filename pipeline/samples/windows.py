# -*- coding: utf-8 -*-
"""curtain-wall / window samples built from the elevations of the glazing schedules A800-A802 (ARCH2 p13-15):
powder-coated aluminium frame (light beige), reflective double glazing 6-12-6 mm light brown; every cell is F (fixed), S (spandrel) or hinged vent."""
from .lib import *

BEIGE = "#d6ccb4"; BEIGE_D = "#bdb298"; TINT = "#b79c72"; SPAN = "#6a5640"; INS = "#d8c98f"
SRC = ["جداول الزجاج والنوافذ A800 / A801 / A802 (ARCH2 ص13-15): المساقط والواجهات بالتقسيم والأبعاد", "تفاصيل النوافذ A803"]
ASM = ["رمز المثلث (رأسه للأسفل) فُسّر «مفصلة سفلية — فتح مائل للداخل (tilt-in)»؛ اتجاه الفتح الفعلي يحتاج تأكيدًا من المصمم",
       "تفاصيل المقاطع (عمق الإطار، فاصل الزجاج، التثبيت بالبلاطة، المقابض) قياسية لهذا النوع من الجدران الستارية وليست من طراز محدد",
       "المنطقة العلوية فوق ارتفاع الجدول 2.5 م (حتى أسفل البلاطة) كما في النموذج: لوح سبانديرل — غير مفصّلة في الجداول"]

def layout_parts(cols, rows_top_down):
    """cols: widths (cm) left->right; rows_top_down: list of strings, one per row (top first), each char S/F/H per column. Row heights: 50 / 140 / 60 (A801 elevations)"""
    sumw = sum(cols); hs = [50, 140, 60]
    P = []
    # vertical offsets (from the sill top upward): bottom row first
    ybot = 10.0            # sill height (model: 10 cm)
    ys = []; y = ybot
    for h in reversed(hs): ys.append((y, y + h)); y += h
    ys = list(reversed(ys))        # ys[0] = top row
    xcum = [0]
    for c in cols: xcum.append(xcum[-1] + c)
    X = lambda v: f"({v}*W/{sumw}-W/2)"
    # frame: sill, head, mullions, transoms
    P.append(box(("-W/2", 0, "-D/2"), ("W/2", ybot, "D/2"), BEIGE, "metal", n="عتبة سفلية (Sill) — قطاع ألمنيوم مطلي بالمسحوق"))
    P.append(box(("-W/2", f"{ys[0][1]}", "-D/2"), ("W/2", f"{ys[0][1]+5}", "D/2"), BEIGE, "metal", n="عارضة علوية (Head transom)"))
    for xv in xcum:
        P.append(box((f"{X(xv)}-2.5", ybot, "-D/2"), (f"{X(xv)}+2.5", f"{ys[0][1]}", "D/2"), BEIGE, "metal", n="قائم رأسي (Mullion) — 5 سم"))
        P.append(box((f"{X(xv)}-1.4", ybot, "D/2"), (f"{X(xv)}+1.4", f"{ys[0][1]}", "D/2+1.0"), BEIGE_D, "metal", n="غطاء ضاغط خارجي (Pressure cap)"))
    for (ya, yb) in ys[:-1]:
        P.append(box(("-W/2", f"{ya}-2.5", "-D/2"), ("W/2", f"{ya}+2.5", "D/2"), BEIGE, "metal", n="قاطع أفقي (Transom) — 5 سم"))
        P.append(box(("-W/2", f"{ya}-1.4", "D/2"), ("W/2", f"{ya}+1.4", "D/2+1.0"), BEIGE_D, "metal", n="غطاء ضاغط أفقي"))
    # cells
    for r, row in enumerate(rows_top_down):
        ya, yb = ys[r]
        for c, t in enumerate(row):
            xa, xb = X(xcum[c]), X(xcum[c + 1])
            gx0, gx1 = f"{xa}+2.5", f"{xb}-2.5"; gy0, gy1 = f"{ya}+2.5", f"{yb}-2.5"
            nm = {"S": "لوح سبانديرل (Spandrel)", "F": "زجاج ثابت (Fixed) 6-12-6", "H": "ضلفة مفصلية (Vent)"}[t]
            if t == "S":
                P += [box((gx0, gy0, "-1.2"), (gx1, gy1, "-0.2"), "#c9bfa0", "matte", n="عزل خلفي (Insulation board)"),
                      box((gx0, gy0, "-2.2"), (gx1, gy1, "-1.2"), "#9aa1a8", "metal", n="صفيحة ألمنيوم خلفية (Back pan)"),
                      box((gx0, gy0, "0"), (gx1, gy1, "0.7"), SPAN, "gloss", n="زجاج سبانديرل معتم مطلي (Enamelled glass) — 6 مم")]
            else:
                inset = 0.0
                if t == "H":
                    P += [box((f"{gx0}", f"{gy0}", "-1.6"), (f"{gx1}", f"{gy0}+5.0", "1.6"), BEIGE, "metal", n="إطار الضلفة — سفلي"),
                          box((f"{gx0}", f"{gy1}-5.0", "-1.6"), (f"{gx1}", f"{gy1}", "1.6"), BEIGE, "metal", n="إطار الضلفة — علوي"),
                          box((f"{gx0}", f"{gy0}", "-1.6"), (f"{gx0}+5.0", f"{gy1}", "1.6"), BEIGE, "metal", n="إطار الضلفة — جانبي"),
                          box((f"{gx1}-5.0", f"{gy0}", "-1.6"), (f"{gx1}", f"{gy1}", "1.6"), BEIGE, "metal", n="إطار الضلفة — جانبي"),
                          box((f"({xa}+{xb})/2-6", f"{gy1}-4.2", "1.6"), (f"({xa}+{xb})/2+6", f"{gy1}-3.2", "3.2"), STEEL, "metal", n="مقبض الضلفة (Handle) — فتح مائل"),
                          box((f"({xa}+{xb})/2-14", f"{gy0}+0.3", "-1.2"), (f"({xa}+{xb})/2+14", f"{gy0}+1.6", "1.2"), STEEL_D, "metal", n="مفصلة سفلية (Bottom hinge)"),
                          box((f"{gx0}+8", f"{gy0}+14", "1.6"), (f"{gx0}+9.2", f"{gy0}+50", "2.4"), STEEL_D, "metal", n="ذراع تحديد الفتح (Friction stay)")]
                    inset = 5.0
                P += [box((f"{gx0}+{inset}", f"{gy0}+{inset}", "-1.2"), (f"{gx1}-{inset}", f"{gy1}-{inset}", "1.2"), TINT, "glass", n="زجاج مزدوج عاكس 6-12-6 مم (بني فاتح)"),
                      box((f"{gx0}+{inset}", f"{gy0}+{inset}", "-1.2"), (f"{gx0}+{inset+1.2}", f"{gy1}-{inset}", "1.2"), "#8a8f94", "metal", n="شريط فاصل ألمنيوم (Spacer bar)"),
                      box((f"{gx1}-{inset+1.2}", f"{gy0}+{inset}", "-1.2"), (f"{gx1}-{inset}", f"{gy1}-{inset}", "1.2"), "#8a8f94", "metal"),
                      box((f"{gx0}+{inset}", f"{gy0}+{inset}", "-1.2"), (f"{gx1}-{inset}", f"{gy0}+{inset+1.2}", "1.2"), "#8a8f94", "metal"),
                      box((f"{gx0}+{inset}", f"{gy1}-{inset+1.2}", "-1.2"), (f"{gx1}-{inset}", f"{gy1}-{inset}", "1.2"), "#8a8f94", "metal")]
    # cover panel above the schedule height (slab zone)
    P += [box(("-W/2", f"{ys[0][1]+5}", "-1.0"), ("W/2", "H", "0.2"), "#c9bfa0", "matte", n="تغطية أعلى الوحدة حتى أسفل البلاطة (افتراض)"),
          box(("-W/2", f"{ys[0][1]+5}", "0.2"), ("W/2", "H", "1.0"), SPAN, "gloss", n="لوح سبانديرل علوي")]
    # slab anchor brackets (top and bottom) at each mullion
    for xv in xcum:
        P.append(box((f"{X(xv)}-4", "-0.5", "-D/2-3"), (f"{X(xv)}+4", "6", "-D/2"), GALV, "metal", n="كتف تثبيت بالبلاطة (Slab bracket) — فولاذ مجلفن"))
    return P

LAYOUTS = {
    "CW-07": ([125, 130], ["SS", "HF", "FF"]),
    "CW-08": ([130, 125], ["SS", "HS", "SS"]),
    "CW-09": ([125, 130], ["SS", "SH", "SS"]),
    "CW-10": ([110] * 7, ["SSSSSSS", "HSHFSFH", "SSFFSFF"]),
    "CW-11": ([110] * 7, ["SSSSSSS", "HFSFHSH", "FFSFFSS"]),
    "CW-12": ([100] * 3, ["SSS", "SSS", "SSS"]),
    "CW-13": ([105, 110, 105, 105], ["SSSS", "FHSS", "FFSS"]),
    "CW-14": ([105, 110, 105, 105], ["SSSS", "SHFS", "SFFS"]),
    "CW-15": ([80, 90, 90], ["SSS", "SHF", "SFF"]),
    "CW-16": ([90, 90, 80], ["SSS", "FHS", "FFS"]),
    "CW-17": ([120, 110, 120], ["SSS", "SHS", "SSS"]),
    "CW-18": ([120, 110, 130], ["SSS", "SHS", "SSS"]),
}
LOC = {"CW-07": "المعيشة / النوم الرئيسية / النوم (أول ومتكرر)", "CW-08": "المطبخ (أول ومتكرر)", "CW-09": "المطبخ (أول ومتكرر)", "CW-10": "المعيشة/النوم/المطبخ (أول ومتكرر)",
       "CW-11": "المعيشة/النوم/المطبخ (أول ومتكرر)", "CW-12": "غرفة نوم (أول ومتكرر)", "CW-13": "غرفة نوم رئيسية (أول ومتكرر)", "CW-14": "غرفة نوم رئيسية (أول ومتكرر)",
       "CW-15": "المعيشة (أول ومتكرر)", "CW-16": "المعيشة (أول ومتكرر)", "CW-17": "المطبخ (أول ومتكرر)", "CW-18": "المطبخ (أول ومتكرر)"}

def cw19():
    """stair window: 120 cm wide strip, repeating bands per storey (A802): S 100 / S 100 / F 150 (pattern read from the elevation)"""
    P = [box(("-W/2", 0, "-D/2"), ("-W/2+5", "H", "D/2"), BEIGE, "metal", n="قائم رأسي — يسار"), box(("W/2-5", 0, "-D/2"), ("W/2", "H", "D/2"), BEIGE, "metal", n="قائم رأسي — يمين")]
    P += [rep(box(("-W/2+5", 0, "-D/2"), ("W/2-5", 5, "D/2"), BEIGE, "metal", n="قاطع أفقي (Transom)"), "round(H/50)", (0, 50, 0))]
    P += [box(("-W/2+5", 5, "-1.0"), ("W/2-5", "H", "-0.0"), "#c9bfa0", "matte", n="عزل/خلفية السبانديرل"),
          rep(box(("-W/2+7.5", 7.5, "0"), ("W/2-7.5", "min(97.5,H-7.5)", "0.7"), SPAN, "gloss", n="زجاج سبانديرل"), "round(H/350)", (0, 350, 0)),
          rep(box(("-W/2+7.5", 102.5, "0"), ("W/2-7.5", "min(192.5,H-7.5)", "0.7"), SPAN, "gloss", n="زجاج سبانديرل"), "round(H/350)", (0, 350, 0)),
          rep(box(("-W/2+7.5", 197.5, "-1.2"), ("W/2-7.5", "min(347.5,H-2.5)", "1.2"), TINT, "glass", n="زجاج ثابت 6-12-6 (F)"), "round(H/350)", (0, 350, 0))]
    return P

def shopfront(modules=None):
    """ground-floor shopfront (A800): 100 cm modules, 70 cm fixed transom band over 230 cm tempered glass; frameless 10 mm glass doors where shown"""
    P = [box(("-W/2", 0, "-D/2"), ("W/2", 6, "D/2"), BEIGE, "metal", n="عتبة سفلية"), box(("-W/2", 300 - 5 if False else "H-5", "-D/2"), ("W/2", "H", "D/2"), BEIGE, "metal", n="عارضة علوية"),
         box(("-W/2", "H-75", "-D/2"), ("W/2", "H-70", "D/2"), BEIGE, "metal", n="قاطع أفقي بين الشريط العلوي والزجاج (70 سم من الأعلى)")]
    P += [rep(box(("-W/2-2.5+0", 6, "-D/2"), ("-W/2+2.5", "H-5", "D/2"), BEIGE, "metal", n="قائم رأسي كل 100 سم"), "round(W/100)+1", ("W/round(W/100)", 0, 0))]
    P += [rep(box(("-W/2+2.5", "H-70", "-1.2"), ("-W/2+W/round(W/100)-2.5", "H-5", "1.2"), TINT, "glass", n="زجاج علوي ثابت 6-12-6"), "round(W/100)", ("W/round(W/100)", 0, 0)),
          rep(box(("-W/2+2.5", 6, "-0.6"), ("-W/2+W/round(W/100)-2.5", "H-75", "0.6"), "#cfe6e8", "glass", n="زجاج مقسّى شفاف 10 مم (Frameless)"), "round(W/100)", ("W/round(W/100)", 0, 0))]
    return P

def make():
    out = {}
    def add(t): out[t[0]] = t[1]
    for code, (cols, rows) in LAYOUTS.items():
        sw = sum(cols)
        add(sample(f"win_{code}", f"نافذة/جدار ستاري {code} — {LOC[code]}", f"Curtain wall unit {code}", "architecture", layout_parts(cols, rows),
                   place={"mode": "group", "anchor": "bottom", "orient": "side"}, lod=9.0, conf="doc", src=SRC,
                   facts=[["العرض الكلي", f"{sw} سم"], ["التقسيم الأفقي (يسار → يمين)", " + ".join(str(c) for c in cols)], ["الصفوف (من الأعلى)", "50 + 140 + 60 سم"],
                          ["الصفوف (حرف لكل خلية: S سبانديرل / F ثابت / H مفصلي)", " | ".join(rows)], ["الإطار", "ألمنيوم مطلي بالمسحوق (بيج فاتح)"], ["الزجاج", "مزدوج عاكس 6-12-6 مم لون بني فاتح"],
                          ["الموقع", LOC[code]], ["التشغيل", "مفصلي وثابت وسبانديرل" if "H" in "".join(rows) else "سبانديرل"]],
                   asm=ASM, dims={"W": sw, "D": 20, "H": 320}))
    add(sample("win_CW-19", "نافذة السلم CW-19 (شريط رأسي 120 سم)", "Staircase window CW-19", "architecture", cw19(), place={"mode": "group", "anchor": "bottom", "orient": "side"}, lod=9.0, conf="doc", src=SRC,
               facts=[["العرض", "120 سم"], ["الموقع", "السلم (أول ومتكرر وسطح)"], ["التشغيل", "ثابت وسبانديرل"]], asm=ASM[1:] + ["تفصيل الدورة الرأسية (S100/S100/F150 لكل طابق) مقروء من واجهة A802 ويلزم تثبيته"], dims={"W": 120, "D": 20, "H": 350}))
    add(sample("win_CW-G", "واجهة محل زجاجية — الدور الأرضي (CW-01..06)", "Ground floor shopfront", "architecture", shopfront(), place={"mode": "group", "anchor": "bottom", "orient": "side"}, lod=10.0, conf="derived", src=SRC[:1],
               facts=[["الارتفاع (فتحة إنشائية)", "300 سم (محلات) / 230 سم (مدخل البدروم)"], ["الشريط العلوي", "70 سم زجاج ثابت 6-12-6"], ["الأبواب", "ألواح زجاج مقسّى 10 مم بلا إطار (Frameless)"]],
               asm=["أماكن الأبواب (ضلفتا 200 سم) تتغير بين CW-01..06؛ العينة تعرض الوحدات الثابتة بمقاس 100 سم والباب يُعرض كلوح زجاج مقسّى — يلزم تفصيل كل نوع من A800", "الإطار والمفصلات الأرضية والمقابض: قياسية"],
               dims={"W": 300, "D": 5, "H": 300}))
    return out

RULES = [{"c": "A.win", "t": f"win_{c}", "s": f"win_{c}"} for c in list(LAYOUTS) + ["CW-19"]] + [{"c": "A.win", "t": "win_CW-G", "s": "win_CW-G"}]
