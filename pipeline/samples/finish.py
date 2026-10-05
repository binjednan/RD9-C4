# -*- coding: utf-8 -*-
"""surface / building-element samples: walls (block + plaster + paint), floor and ceiling finishes (A500 schedule), porcelain cladding, parapets, fences, stairs, lift car, boundary wall.
Rectangular elements ('rect' mode): W = long side, D = short side (thickness for walls), H = vertical size (cm); origin at the bottom centre."""
from .lib import *

SRC_FIN = ["جدول التشطيبات A500 (ARCH1 ص18)", "BOQ — بنود التشطيبات 9.x"]
ASM_LAYERS = "سماكات الطبقات غير الواردة في الجدول (اللياسة 20 مم من W2 فقط) قياسية؛ تفصيل المونة والتسليح الخفيف افتراض"

def wall(thk_note, core_c="#a9a69e", ext=False, lintel=False):
    pl = 2.0                      # plaster thickness (W2: 20 mm)
    P = [box(("-W/2", 0, "-D/2"), ("W/2", "H", "D/2"), core_c, "matte", n=f"بلوك خرساني مفرّغ {thk_note} — قلب الجدار"),
         box(("-W/2", 0, "D/2"), ("W/2", "H", f"D/2+{pl}"), "#ece6d8" if not ext else "#e2d5b8", "matte", n="لياسة أسمنتية 20 مم (جهة +)"),
         box(("-W/2", 0, f"-D/2-{pl}"), ("W/2", "H", "-D/2"), "#ece6d8" if not ext else "#e2d5b8", "matte", n="لياسة أسمنتية 20 مم (جهة −)"),
         box(("-W/2", 0, f"D/2+{pl}"), ("W/2", "H", f"D/2+{pl+0.12}"), "#f0ede6" if not ext else "#e8dcc0", "matte", n="دهان إيمولشن قابل للغسل (W2) — طبقة نهائية"),
         box(("-W/2", 0, f"-D/2-{pl+0.12}"), ("W/2", "H", f"-D/2-{pl}"), "#f0ede6" if not ext else "#e8dcc0", "matte", n="دهان نهائي")]
    # exposed top: hollow cores of the blocks (every 40 cm) + joint lines on the block ends
    P += [rep(box(("-W/2+4", "H-0.2", "-D/2+2.5"), ("-W/2+17", "H+0.05", "D/2-2.5"), "#6f6c65", "matte", n="تجويف البلوك (Hollow core) — يظهر على القطع العلوي"), "max(1,floor(W/40))", (40, 0, 0)),
          rep(box(("-W/2+20", 0, "-D/2"), ("-W/2+21", "H", "D/2+0.01"), "#d9d3c6", "matte", n="فاصل مونة رأسي (على أطراف الجدار)"), "0", (40, 0, 0))]
    P += [rep(box(("-W/2", "20-0.5", "-D/2-0.01"), ("-W/2+0.4", "20+0.5", "D/2+0.01"), "#d9d3c6", "matte", n="خط مونة أفقي كل 20 سم (يظهر على نهاية الجدار)"), "floor(H/20)", (0, 20, 0))]
    if lintel:
        P += [box(("-W/2", 0, "-D/2"), ("W/2", "H", "D/2"), "#a09d95", "matte", n="عتبة خرسانية مسلّحة (Lintel) فوق الفتحة")]
    return P

def floor_tiles(tile, color, joint=0.3, gc="#6d6a62", shine="gloss", name="بلاط", plain=False):
    P = [box(("-W/2", 0, "-D/2"), ("W/2", "H", "D/2"), color, shine, n=f"{name} — سطح التشطيب"),
         box(("-W/2", "-3", "-D/2"), ("W/2", 0, "D/2"), "#9a978f", "matte", n="طبقة تسوية (Screed / Mortar bed)")]
    if not plain:
        P += [rep(box(("-W/2", "H", f"-D/2-{joint/2}"), ("W/2", "H+0.04", f"-D/2+{joint/2}"), gc, "matte", n=f"فاصل مونة {joint} سم — اتجاه X"), f"floor(D/{tile})+1", (0, 0, f"D/(floor(D/{tile})+0.0001)")),
              rep(box((f"-W/2-{joint/2}", "H", "-D/2"), (f"-W/2+{joint/2}", "H+0.04", "D/2"), gc, "matte", n=f"فاصل مونة {joint} سم — اتجاه Z"), f"floor(W/{tile})+1", (f"W/(floor(W/{tile})+0.0001)", 0, 0))]
    return P

def ceiling_board():
    return [box(("-W/2", "-1.2", "-D/2"), ("W/2", 0, "D/2"), "#f5f4ef", "matte", n="لوح جبس 12 مم + دهان إيمولشن (C1)"),
            rep(box(("-W/2", "-1.25", "-D/2"), ("W/2", "-1.2+0", "-D/2+0.25"), "#d9d6cd", "matte", n="فاصل ألواح (Joint) — مفروك بالمعجون"), "floor(D/120)+1", (0, 0, "D/(floor(D/120)+0.0001)")),
            rep(box(("-W/2", "-1.25", "-D/2"), ("-W/2+0.25", "-1.2+0", "D/2"), "#d9d6cd", "matte", n="فاصل ألواح — اتجاه ثان"), "floor(W/240)+1", ("W/(floor(W/240)+0.0001)", 0, 0)),
            rep(box(("-W/2", 0, "-D/2+30"), ("W/2", 2.8, "-D/2+34"), "#9aa1a8", "metal", n="قطاع حامل C-channel — كل 60 سم"), "floor(D/60)", (0, 0, 60)),
            rep(box(("-W/2+40", 2.8, "-D/2"), ("-W/2+44", 5.6, "D/2"), "#8e949c", "metal", n="قطاع رئيسي (Main runner) — كل 120 سم"), "floor(W/120)", (120, 0, 0)),
            rep(cyl(("-W/2+42", 5.6, "-D/2+60"), 0.25, 18, "#aab0b8", "metal", n="سلك تعليق (Hanger wire) 4 مم"), "floor(W/120)", (120, 0, 0))]

def ceiling_tiles():
    P = [box(("-W/2", "-0.7", "-D/2"), ("W/2", 0, "D/2"), "#e0e4e7", "matte", n="بلاط ألمنيوم 600×600×7 مم (C3) — مثقّب")]
    P += [rep(box(("-W/2", "-1.3", "-D/2-0.8"), ("W/2", "-0.7", "-D/2+0.8"), "#f4f6f8", "gloss", n="شبكة T-bar بيضاء (24 مم)"), "floor(D/60)+1", (0, 0, "D/(floor(D/60)+0.0001)")),
          rep(box(("-W/2-0.8", "-1.3", "-D/2"), ("-W/2+0.8", "-0.7", "D/2"), "#f4f6f8", "gloss", n="شبكة T-bar — اتجاه ثان"), "floor(W/60)+1", ("W/(floor(W/60)+0.0001)", 0, 0)),
          rep(cyl(("-W/2+30", 0, "-D/2+60"), 0.25, 18, "#aab0b8", "metal", n="سلك تعليق"), "floor(W/120)", (120, 0, 0))]
    return P

def cladding_porcelain():
    # W = width, D = depth (thickness), H = height — porcelain panels 60 x 120 cm, 2 cm, ventilated facade with aluminium sub-frame
    return [box(("-W/2", 0, "-D/2"), ("W/2", "H", "-D/2+2"), "#e9e9e5", "gloss", n="ألواح بورسلين 60×120 سم — 2 سم (W12)"),
            rep(box(("-W/2", "0-0.0", "-D/2-0.0"), ("-W/2+0.5", "H", "-D/2+2.05"), "#6d6a62", "matte", n="فاصل 5 مم — رأسي كل 60 سم"), "floor(W/60)+1", ("W/(floor(W/60)+0.0001)", 0, 0)),
            rep(box(("-W/2", "-0.0", "-D/2"), ("W/2", 0.5, "-D/2+2.05"), "#6d6a62", "matte", n="فاصل 5 مم — أفقي كل 120 سم"), "floor(H/120)+1", (0, "H/(floor(H/120)+0.0001)", 0)),
            rep(box(("-W/2+29", 0, "-D/2+2"), ("-W/2+31", "H", "-D/2+7"), "#8e949c", "metal", n="قطاع ألمنيوم رأسي (T-profile) خلف الألواح كل 60 سم"), "floor(W/60)", (60, 0, 0)),
            rep(box(("-W/2+28", "10", "-D/2+7"), ("-W/2+32", "18", "-D/2+11"), GALV, "metal", n="كتف تثبيت (Wall bracket)"), "floor(W/60)", (60, 0, 0)),
            box(("-W/2", 0, "-D/2+7"), ("W/2", "H", "D/2"), "#d9d4c4", "matte", n="جدار الدعم (خرسانة/بلوك) خلف الكسوة")]

def parapet(roof=False):
    # W long, D thickness, H height: concrete core + porcelain cladding + aluminium coping
    return [box(("-W/2", 0, "-D/2"), ("W/2", "H-3", "D/2"), "#a8a69f", "matte", n="قلب الحاجز (خرسانة / بلوك مع لياسة)"),
            box(("-W/2", 0, "D/2"), ("W/2", "H-3", "D/2+2"), "#e9e9e5", "gloss", n="كسوة بورسلين 2 سم — الواجهة"), box(("-W/2", 0, "-D/2-2"), ("W/2", "H-3", "-D/2"), "#e9e9e5", "gloss", n="كسوة بورسلين — الداخل"),
            box(("-W/2-0.5", "H-3", "-D/2-3"), ("W/2+0.5", "H", "D/2+3"), "#b9bec4", "metal", n="غطاء علوي ألمنيوم (Coping) مع ميل"),
            rep(box(("-W/2", 0, "D/2+1.9"), ("-W/2+0.5", "H-3", "D/2+2.05"), "#6d6a62", "matte", n="فاصل كسوة رأسي"), "floor(W/60)+1", ("W/(floor(W/60)+0.0001)", 0, 0))]

def fence_roof():
    P = [box(("-W/2", 0, "-D/2"), ("W/2", 12, "D/2"), "#9a978f", "matte", n="أساس / قاعدة خرسانية (Foundation) — «with foundation»"),
         rep(box(("-W/2+2", 12, "-2.5"), ("-W/2+7", "H", "2.5"), "#4a5057", "metal", n="عمود فولاذ مربع 50×50 مم كل 2 م"), "floor(W/200)+1", ("W/(floor(W/200)+0.0001)-0.0", 0, 0)),
         box(("-W/2", "H-6", "-2"), ("W/2", "H-3", "2"), "#4a5057", "metal", n="سكة علوية"), box(("-W/2", 14, "-2"), ("W/2", 17, "2"), "#4a5057", "metal", n="سكة سفلية"),
         rep(box(("-W/2+4", 17, "-0.15"), ("-W/2+4.4", "H-6", "0.15"), "#7b858f", "metal", n="سلك الشبك (Mesh wire) كل 5 سم"), "floor(W/5)", (5, 0, 0)),
         rep(box(("-W/2", "22", "-0.15"), ("W/2", "22.4", "0.15"), "#7b858f", "metal", n="سلك أفقي"), "floor((H-30)/5)", (0, 5, 0))]
    return P

def barrier_post():
    # housing of the automatic barrier (post element 30 x 18 cm in plan, 1.1 m high): cabinet, hinged service door, control plate, pivot cover, LED strip
    return [box(("-W/2-3", 0, "-D/2-3"), ("W/2+3", 1.5, "D/2+3"), "#7b858f", "metal", n="لوح القاعدة المثبّت بالأرضية (Base plate) + 4 مسامير تثبيت"),
            box(("-W/2", 1.5, "-D/2"), ("W/2", "H-2", "D/2"), "#d9dde1", "gloss", n="جسم الخزانة المعدني (Housing) — دهان بودرة"),
            box(("-W/2-0.1", "H-2", "-D/2-0.1"), ("W/2+0.1", "H", "D/2+0.1"), "#aab0b8", "metal", n="غطاء علوي (Cap)"),
            box(("-W/2+3", 30, "D/2"), ("W/2-3", "H-30", "D/2+0.4"), "#c0c6cc", "metal", n="باب الصيانة (Service door) مع قفل"),
            cyl((0, 45, "D/2+0.4"), 1.2, 0.8, "#1f2226", "metal", ax="z", n="قفل الباب"),
            box(("-W/2+4", "H-26", "D/2"), ("W/2-4", "H-16", "D/2+0.3"), "#1f2226", "matte", n="لوحة بيانات/إشارة"),
            rep(box(("-W/2+1", "H-14", "D/2"), ("W/2-1", "H-12", "D/2+0.4"), "#2ecc40", "emit", n="شريط LED حالة (أخضر/أحمر)"), 1, (0, 0, 0)),
            cyl(("W/2", "H-12", 0), 4, 2.5, "#8e949c", "metal", ax="x", n="غطاء محور الذراع (Pivot cover)")]

def barrier_boom():
    # boom of the barrier (element: 300 x 9 cm plan, 8 cm high): painted aluminium arm with red/white warning stripes, rubber edge, end cap
    return [box(("-W/2", 0, "-D/2"), ("W/2", "H", "D/2"), "#f2f2ee", "gloss", n="ذراع البوابة (Boom) — ألمنيوم مدهون أبيض"),
            rep(box(("-W/2+6", -0.05, "-D/2-0.1"), ("-W/2+36", "H+0.05", "D/2+0.1"), "#c0392b", "gloss", n="شريط تحذير أحمر (Warning stripe)"), "floor((W-6)/60)", (60, 0, 0)),
            box(("-W/2-0.8", 0, "-D/2-0.3"), ("-W/2", "H", "D/2+0.3"), "#1f2226", "rubber", n="غطاء طرف مطاطي"),
            box(("W/2", 0, "-D/2-0.3"), ("W/2+0.8", "H", "D/2+0.3"), "#1f2226", "rubber", n="غطاء طرف مطاطي"),
            box(("-W/2", -0.1, "-D/2+1"), ("W/2", 0.5, "D/2-1"), "#1f2226", "rubber", n="حافة سفلية مطاطية (Safety edge)"),
            rep(box(("-W/2+30", "H", "-0.5"), ("-W/2+34", "H+0.3", "0.5"), "#f5c518", "gloss", n="عاكس ضوء (Reflector)"), "floor((W-60)/100)", (100, 0, 0))]

def boundary_wall():
    return [box(("-W/2", 0, "-D/2"), ("W/2", "H-12", "D/2"), "#cfc6b2", "matte", n="جدار سور بلوك 200 مم مع لياسة ودهان خارجي"), box(("-W/2-3", "H-12", "-D/2-3"), ("W/2+3", "H", "D/2+3"), "#b9b3a2", "matte", n="كمرة غطاء (Coping beam) خرسانية"),
            rep(box(("-W/2", 0, "D/2"), ("-W/2+0.4", "H-12", "D/2+0.4"), "#a39d8d", "matte", n="فاصل تمدد/أخدود (Reveal)"), "floor(W/300)+1", ("W/(floor(W/300)+0.0001)", 0, 0))]

def stair_step():
    # W = flight width, D = tread, H = rise (the model draws each step as a rect); finish F10: granite 3 cm
    return [box(("-W/2", 0, "-D/2"), ("W/2", "H", "D/2"), "#a6a49d", "matte", n="خرسانة الدرجة (Concrete step)"),
            box(("-W/2", "H", "-D/2"), ("W/2", "H+3", "D/2+3"), "#cfa95a", "gloss", n="وجه الدرجة جرانيت أورو برازيل 3 سم (F10)"), box(("-W/2", "H-1", "D/2+3"), ("W/2", "H+3", "D/2+3.5"), "#cfa95a", "gloss", n="قائمة الدرجة (Riser) جرانيت"),
            rep(box(("-W/2+2", "H+3", "D/2-3.5"), ("W/2-2", "H+3.25", "D/2-3.1"), "#2a2a2a", "rubber", n="شريط مانع انزلاق (Anti-slip nosing)"), "1", (0, 0, 0.0)),
            rep(box(("-W/2+2", "H+3", "D/2-7"), ("W/2-2", "H+3.25", "D/2-6.6"), "#2a2a2a", "rubber", n="شريط ثانٍ"), "1", (0, 0, 0.0))]

def lift_car():
    # 160 x 140 x 220 car (A900): stainless walls, mirror, handrail, led ceiling, car operating panel, centre-opening doors on the front (+z)
    return [box(("-W/2", 0, "-D/2"), ("W/2", 8, "D/2"), "#cfa95a", "gloss", n="أرضية الكابينة (جرانيت/رخام)"),
            box(("-W/2", 8, "-D/2"), ("-W/2+3", "H-30", "D/2"), "#c9ced4", "metal", n="جدار جانبي ستانلس ستيل (مصقول)"), box(("W/2-3", 8, "-D/2"), ("W/2", "H-30", "D/2"), "#c9ced4", "metal", n="جدار جانبي ستانلس"),
            box(("-W/2", 8, "-D/2"), ("W/2", "H-30", "-D/2+3"), "#c9ced4", "metal", n="الجدار الخلفي"), box(("-W/2+3", 70, "-D/2+3"), ("W/2-3", "H-70", "-D/2+3.6"), "#b9d6e6", "glass", n="مرآة الجدار الخلفي"),
            box(("-W/2+3", 95, "-D/2+3.6"), ("W/2-3", 99, "-D/2+8.6"), "#e0e4e7", "metal", n="درابزين (Handrail) ستانلس"),
            box(("-W/2", "H-30", "-D/2"), ("W/2", "H-26", "D/2"), "#9aa1a8", "metal", n="سقف الكابينة"), box(("-W/2+10", "H-26.4", "-D/2+10"), ("W/2-10", "H-26", "D/2-10"), "#fffbe0", "emit", n="إضاءة LED مدمجة بالسقف"),
            box(("W/2-14", 95, "D/2-3"), ("W/2-3", 160, "D/2"), "#2b2f35", "gloss", n="لوحة التشغيل (COP) — أزرار طوابق + شاشة"), rep(cyl(("W/2-8.5", 108, "D/2"), 1.1, 0.6, "#c9ced4", "metal", ax="z", n="زر طابق"), 6, (0, 8, 0)),
            box(("-W/2+3", 8, "D/2-3"), ("-1.5", "H-30", "D/2"), "#aab0b8", "metal", n="ضلفة باب الكابينة اليسرى (Centre opening)"), box(("1.5", 8, "D/2-3"), ("W/2-14", "H-30", "D/2"), "#aab0b8", "metal", n="ضلفة باب الكابينة اليمنى"),
            box(("-W/2", "H-30", "D/2-3"), ("W/2", "H-26", "D/2+1"), "#7a828a", "metal", n="كابل/عارضة علوية للباب")]

def make():
    out = {}
    def add(t): out[t[0]] = t[1]
    R = {"mode": "rect", "anchor": "bottom"}
    def S(id_, name, en, parts, place=R, lod=6.0, conf="derived", facts=None, asm=None, src=None, dims=None, cat="architecture", **kw):
        add(sample(id_, name, en, cat, parts, place=place, lod=lod, conf=conf, src=src or SRC_FIN, facts=facts or [], asm=(asm or []) + [ASM_LAYERS], dims=dims or {}, **kw))
    S("wall_blk100", "جدار بلوك خرساني 100 مم (داخلي) — لياسة ودهان", "100 mm block wall, plaster + paint", wall("100 مم"), conf="derived", facts=[["القلب", "بلوك خرساني مفرّغ 100 مم"], ["التشطيب", "لياسة 20 مم + دهان إيمولشن (W2)"]], dims={"W": 300, "D": 10, "H": 300})
    S("wall_blk200", "جدار بلوك خرساني 200 مم — لياسة ودهان", "200 mm block wall, plaster + paint", wall("200 مم"), facts=[["القلب", "بلوك خرساني مفرّغ 200 مم"], ["التشطيب", "لياسة 20 مم + دهان (W2/W11)"]], dims={"W": 300, "D": 20, "H": 300})
    S("wall_blk_t", "جدار بلوك — نوع T (سماكة خاصة)", "Block wall (type T)", wall("T"), asm=["سماكة T غير مفسّرة في المخطط المعماري؛ تُعرض كجدار بلوك قياسي"], dims={"W": 300, "D": 15, "H": 300})
    S("wall_lintel", "عتبة خرسانية مسلّحة فوق الفتحات", "Reinforced concrete lintel", wall("", lintel=True), asm=["مقطع العتبة وتسليحها: غير مفصّلين — تُعرض خرسانة مع لياسة"], dims={"W": 120, "D": 20, "H": 30})
    fl = [("F1", "أرضية سيراميك غير زلقة 300×300×10 مم (نوع 01)", 30, "#c9b99c", "gloss"), ("F2", "أرضية سيراميك غير زلقة 300×300×10 مم (نوع 02)", 30, "#b7c0c6", "gloss"),
          ("F4", "أرضية بورسلين مصقول 600×600×10 مم", 60, "#dcd8cf", "gloss"), ("F8", "أرضية سيراميك شاق 300×300×10 مم", 30, "#9c9c96", "matte"), ("F16", "أرضية جرانيت 30 مم نوع 01 (ردهات)", 60, "#d3c3a3", "gloss")]
    for code, nm, t, c, sh in fl:
        S(f"floor_{code}", nm, nm, floor_tiles(t, c, shine=sh, name=nm), facts=[["الكود", code], ["القياس", f"{t}×{t} سم" if code != "F16" else "30 مم — قياس البلاطة غير مذكور"], ["المصدر", "جدول A500"]],
          asm=(["قياس بلاطة الجرانيت 60×60 سم وعرض المونة: افتراض (غير مذكور)"] if code == "F16" else ["عرض فاصل المونة 3 مم: افتراض"]), dims={"W": 300, "D": 250, "H": 1.5})
    S("floor_F6", "أرضية إيبوكسي على سكريد", "Epoxy floor on screed", floor_tiles(60, "#93a8a2", plain=True, shine="gloss", name="إيبوكسي"), facts=[["الكود", "F6"], ["النوع", "إيبوكسي أحادي اللون بلا فواصل"]], dims={"W": 300, "D": 250, "H": 0.3})
    S("floor_F1", "أرضية سيراميك غير زلقة 300×300 (F1)", "Ceramic non-slip F1", floor_tiles(30, "#c9b99c"), dims={"W": 300, "D": 250, "H": 1.0})
    S("ceil_C1", "سقف مستعار جبس 12 مم + دهان إيمولشن (C1)", "Gypsum board suspended ceiling C1", ceiling_board(), place={"mode": "rect", "anchor": "top"}, clip=True, facts=[["الكود", "C1"], ["اللوح", "جبس 12 مم + دهان إيمولشن"], ["الألواح", "120×240 سم (قياسي)"]], asm=["تفصيل الهيكل المعدني (باعدة 60 سم، قطاعات رئيسية 120 سم): قياسي"], dims={"W": 300, "D": 250, "H": 1.2})
    S("ceil_C3", "سقف مستعار بلاط ألمنيوم 600×600×7 مم (C3)", "Aluminium lay-in tile ceiling C3", ceiling_tiles(), place={"mode": "rect", "anchor": "top"}, clip=True, facts=[["الكود", "C3"], ["البلاط", "ألمنيوم 600×600×7 مم"]], dims={"W": 300, "D": 250, "H": 1.3})
    S("clad_porcelain", "كسوة بورسلين 60×120 سم — 2 سم (W12)", "Porcelain cladding W12 (ventilated)", cladding_porcelain(), facts=[["الكود", "W12"], ["الألواح", "60×120 سم، 2 سم"], ["النظام", "واجهة مهوّاة بهيكل ألمنيوم"]], asm=["نظام التثبيت (هيكل T وأكتاف) قياسي لهذا النوع من الكسوة"], dims={"W": 240, "D": 12, "H": 300})
    S("clad_edge", "حافة كسوة بورسلين (Return)", "Porcelain cladding edge return", cladding_porcelain(), dims={"W": 60, "D": 12, "H": 300})
    S("parapet_top", "حاجز (Parapet) السطح العلوي — كسوة بورسلين مع غطاء ألمنيوم", "Parapet with porcelain cladding & aluminium coping", parapet(), lod=8, dims={"W": 500, "D": 20, "H": 60}, asm=["سماكة الغطاء الألمنيوم وبروزه: قياسية"])
    S("parapet_roof", "حاجز السطح 1.9 م — كسوة بورسلين", "Roof parapet 1.9 m", parapet(True), lod=8, dims={"W": 500, "D": 30, "H": 190})
    S("fence_roof", "سياج السطح 1.8 م مع أساس", "Roof fence 1.8 m with foundation", fence_roof(), lod=8, conf="doc", src=["MECH1 ص15: «1.8m HEIGHT FENCING WITH FOUNDATION»"], facts=[["الارتفاع", "1.8 م (نص المخطط)"]],
      asm=["الاسم في الطبقة يذكر 2 م — بانتظار تأكيدك", "نوع الشبك (سلك مجلفن) والأعمدة 50×50: افتراض"], dims={"W": 400, "D": 6, "H": 180})
    S("barrier_post", "عمود بوابة الحاجز الآلي (خزانة المحرك)", "Automatic barrier housing (post)", barrier_post(), lod=10, src=["ARCH1 ص3 (A100/A102): طبقة Appliances"], asm=["الارتفاعات والأبعاد التفصيلية افتراض (غير مذكورة)", "الطراز التجاري غير مذكور"], dims={"W": 30, "D": 18, "H": 110})
    S("barrier_boom", "ذراع بوابة الحاجز الآلي (Boom)", "Automatic barrier boom", barrier_boom(), lod=10, src=["ARCH1 ص3 (A100/A102): طبقة Appliances"], asm=["الارتفاعات والأبعاد التفصيلية افتراض (غير مذكورة)", "طول الذراع من الرسم (3 م)"], dims={"W": 300, "D": 9, "H": 8})
    S("wall_boundary", "سور الموقع — بلوك 200 مم مع كمرة غطاء", "Boundary wall", boundary_wall(), lod=10, src=["ARCH1 ص16-17: A400/A401 تفاصيل السور"], facts=[["النوع", "سور بلوك مع كمرة غطاء"]], asm=["الارتفاع وتفصيل الكمرة من مخطط A400 — يلزم تحديث العينة منه"], dims={"W": 600, "D": 20, "H": 200})
    S("stair_step", "درجة سلم خرسانية بوجه جرانيت (F10)", "Concrete stair step with granite finish", stair_step(), lod=5, src=["ARCH2 ص1-5: تفاصيل السلالم A600-A604", "جدول A500: F10"], facts=[["التشطيب", "جرانيت أورو برازيل 3 سم (F10)"]], asm=["شريط مانع الانزلاق وحافة الدرجة: قياسية"], dims={"W": 120, "D": 28, "H": 17})
    S("stair_landing", "بسطة سلم خرسانية بجرانيت", "Stair landing", stair_step(), lod=6, src=["ARCH2 ص1-5"], dims={"W": 250, "D": 120, "H": 17})
    S("lift_car", "كابينة مصعد (160×140×220 سم)", "Lift car", lift_car(), place={"mode": "rect", "anchor": "bottom"}, lod=8, src=["ARCH2 ص17: A900 تفاصيل المصاعد"], facts=[["أبعاد الكابينة", "160 × 140 سم"], ["الارتفاع", "2.2 م"]], asm=["تشطيب الكابينة وتفاصيل لوحة التشغيل: قياسية — راجع A900 لتثبيت المواصفة"], dims={"W": 160, "D": 140, "H": 220})
    return out

RULES = [{"c": "A.wall", "t": t, "s": t} for t in ("wall_blk100", "wall_blk200", "wall_blk_t", "wall_lintel")] + [{"c": "A.floor", "t": f"floor_{c}", "s": f"floor_{c}"} for c in ("F1", "F2", "F4", "F6", "F8", "F16")] + \
        [{"c": "A.ceil", "t": "ceil_C1", "s": "ceil_C1"}, {"c": "A.ceil", "t": "ceil_C3", "s": "ceil_C3"}, {"c": "A.ceil", "t": "ceil_inferred", "s": "ceil_C1"}, {"c": "A.clad", "t": "clad_porcelain", "s": "clad_porcelain"}, {"c": "A.clad", "t": "clad_edge", "s": "clad_edge"},
         {"c": "A.rail", "t": "parapet_top", "s": "parapet_top"}, {"c": "A.rail", "t": "parapet_roof", "s": "parapet_roof"}, {"c": "A.rail", "t": "fence_roof", "s": "fence_roof"}, {"c": "A.rail", "t": "barrier_post", "s": "barrier_post"}, {"c": "A.rail", "t": "barrier_boom", "s": "barrier_boom"},
         {"c": "A.site", "t": "wall_boundary", "s": "wall_boundary"}, {"c": "S.stair", "t": "stair_step", "s": "stair_step"}, {"c": "S.stair", "t": "stair_landing", "s": "stair_landing"}, {"c": "A.fix", "t": "lift_car", "s": "lift_car"}]
