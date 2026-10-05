# -*- coding: utf-8 -*-
"""mechanical (HVAC) samples: ducted FCU, thermostat, diffusers, grilles, dampers, chiller, pumps, FAHU, fans"""
from .lib import *

SRC_AC = ["MECH1: مخططات التكييف AC-100..105 وجدول AC-106 (وحدات FCU)", "MECH1 ص9-10: تفاصيل AC-107"]
ASM = "الشكل التفصيلي قياسي لهذه الفئة (ليس طرازًا محددًا) — الطراز التجاري غير مذكور في المستندات"

def fcu():
    # ducted horizontal fan-coil unit hung under the slab: W=95 (length), D=38 (width), H=30; local z across, x along (air flows along +x)
    P = [box(("-W/2", 0, "-D/2"), ("W/2", "H", "D/2"), "#c7ccd2", "metal", n="غلاف الوحدة (Galvanised steel casing)"),
         box(("-W/2-0.4", 0, "-D/2-0.4"), ("W/2+0.4", 2.2, "D/2+0.4"), "#8e949c", "metal", n="حوض تجميع التكثيف (Drain pan) معزول"),
         box(("-W/2+4", 1.0, "-D/2+4"), ("-W/2+34", 2.0, "D/2-4"), "#9aa1a8", "metal", n="لوح وصول سفلي (Access panel)"),
         box(("W/2", 3.5, "-D/2+4.5"), ("W/2+3.5", "H-3.5", "D/2-4.5"), "#aab0b8", "metal", n="شفة خروج الهواء (Supply spigot flange)"),
         box(("W/2+3.5", 6, "-D/2+8"), ("W/2+8.0", "H-6", "D/2-8"), "#8e949c", "metal", n="وصلة المجرى (Duct collar)"),
         box(("-W/2-3.0", 3.5, "-D/2+4.5"), ("-W/2", "H-3.5", "D/2-4.5"), "#aab0b8", "metal", n="شفة دخول الهواء (Return flange)"),
         box(("-W/2-3.0", 4, "-D/2+6"), ("-W/2-2.4", "H-4", "D/2-6"), "#6f757c", "matte", n="إطار الفلتر (Filter frame) + وسط الفلتر"),
         rep(box(("-W/2-3.0", 5, "-D/2+7"), ("-W/2-2.2", "H-5", "-D/2+7.6"), "#e6e2d4", "matte", n="طيّات الفلتر المطوي"), 12, (0, 0, "(D-14)/11"))]
    # hanger rods (4) + nuts
    for sx in (-1, 1):
        for sz in (-1, 1):
            xx = f"{sx}*(W/2-6)"; zz = f"{sz}*(D/2+2.2)"
            P += [cyl((xx, "H-4", zz), 0.5, 14, "#aab0b8", "metal", n="قضيب التعليق المسنن (M10)"), box((f"({xx})-1.2", "H-5.4", f"({zz})-2.2"), (f"({xx})+1.2", "H-4.2", f"({zz})+2.2"), "#8e949c", "metal", n="كتف التعليق (Hanger bracket)")]
    # CHW coil connections on the return end (supply + return stubs with isolating valves) and drain
    for k, (zz, c) in enumerate(((-6, "#2d8bd6"), (6, "#e07b39"))):
        P += [cyl((f"-W/2+10", "H", zz), 1.1, 9, "#b87333", "metal", n=("وصلة المياه المبردة — تغذية" if k == 0 else "وصلة المياه المبردة — رجوع") + " (نحاس ⌀22 مم)"),
              cyl((f"-W/2+10", "H+4", zz), 1.7, 3.2, c, "gloss", ax="x", n="صمام عزل كروي (Ball valve)"), box((f"-W/2+8", "H+3.2", f"{zz}-0.3"), (f"-W/2+12.5", "H+4.0", f"{zz}+0.3"), "#c0392b", "gloss", n="مقبض الصمام")]
    P += [cyl(("-W/2+4", 0.5, "D/2-3"), 1.25, 9, "#e8e8e4", "gloss", ax="z", n="مخرج التكثيف (PVC ⌀25 مم)"), cyl(("-W/2+14", "H", "-D/2+5"), 0.5, 3, "#d9a21b", "metal", n="مفتاح تنفيس الهواء (Air vent)")]
    P += [box(("W/2-24", "H-11", "D/2"), ("W/2-12", "H-3", "D/2+6"), "#c9ced4", "gloss", n="علبة التوصيل الكهربائي"), box(("-W/2+36", "H-11", "-D/2-0.2"), ("-W/2+54", "H-3", "-D/2"), "#fff", "matte", n="ملصق الوحدة (Tag): FCU")]
    return P

def thermostat():
    return [box((-5.0, "H/2-5.0", "-D/2"), (5.0, "H/2+5.0", "-D/2+1.9"), "#ebe9e1", "gloss", n="جسم الثرموستات (Digital room thermostat)"),
            box((-3.2, "H/2+0.8", "-D/2+1.9"), (3.2, "H/2+3.8", "-D/2+2.0"), "#0b2a3a", "emit", n="شاشة LCD (درجة الحرارة المضبوطة)"),
            cyl((-2.6, "H/2-2.6", "-D/2+1.9"), 0.7, 0.3, "#c9ccd1", "gloss", ax="z", n="زر خفض"), cyl((0, "H/2-2.6", "-D/2+1.9"), 0.7, 0.3, "#c9ccd1", "gloss", ax="z", n="زر وضع (Mode/Fan)"),
            cyl((2.6, "H/2-2.6", "-D/2+1.9"), 0.7, 0.3, "#c9ccd1", "gloss", ax="z", n="زر رفع"), cyl((4.0, "H/2+4.0", "-D/2+1.9"), 0.25, 0.2, "#2ecc40", "emit", ax="z", n="LED تشغيل")]

def diffuser(ret=False):
    c = "#c9ccd1" if ret else "#f1f1ec"
    P = [box(("-W/2", -0.9, "-D/2"), ("W/2", 0, "D/2"), c, "gloss", n="إطار الناشر (Flange)")]
    if not ret:
        # 4-way louvre face: concentric square rings stepping up to a central plate
        for k, (ins, h) in enumerate(((1.4, 1.7), (4.0, 2.4), (6.6, 3.1))):
            P += [box((f"-W/2+{ins}", f"-{h}", f"-D/2+{ins}"), (f"W/2-{ins}", f"-{h-0.5}", f"-D/2+{ins+0.6}"), c, "gloss", n="حلقة موجّه الهواء (Louvre ring) — اتجاه 1"),
                  box((f"-W/2+{ins}", f"-{h}", f"D/2-{ins+0.6}"), (f"W/2-{ins}", f"-{h-0.5}", f"D/2-{ins}"), c, "gloss", n="حلقة موجّه الهواء — اتجاه 2"),
                  box((f"-W/2+{ins}", f"-{h}", f"-D/2+{ins}"), (f"-W/2+{ins+0.6}", f"-{h-0.5}", f"D/2-{ins}"), c, "gloss", n="حلقة موجّه الهواء — اتجاه 3"),
                  box((f"W/2-{ins+0.6}", f"-{h}", f"-D/2+{ins}"), (f"W/2-{ins}", f"-{h-0.5}", f"D/2-{ins}"), c, "gloss", n="حلقة موجّه الهواء — اتجاه 4")]
        P += [box(("-W/2+9", -3.6, "-D/2+9"), ("W/2-9", -3.0, "D/2-9"), c, "gloss", n="الصفيحة المركزية (Centre plate)")]
        for k in range(4):
            a = k * 90
            P += [dict(box((-0.3, -3.0, 0), (0.3, -0.9, "min(W,D)/2-8"), "#aab0b8", "metal", n="دعامة الصفيحة"), rot=[0, a, 0])]
    else:
        P += [box(("-W/2+1.2", -1.6, "-D/2+1.2"), ("W/2-1.2", -0.9, "D/2-1.2"), "#d9dde2", "gloss", n="شبكة متداخلة (Egg-crate) — الإطار الداخلي"),
              rep(box(("-W/2+1.2", -2.6, "-D/2+1.2"), ("W/2-1.2", -0.9, "-D/2+1.6"), "#e4e7ea", "gloss", n="شريحة الشبكة المتداخلة — اتجاه 1"), "round((D-2.4)/2.2)", (0, 0, 2.2)),
              rep(box(("-W/2+1.2", -2.6, "-D/2+1.2"), ("-W/2+1.6", -0.9, "D/2-1.2"), "#e4e7ea", "gloss", n="شريحة الشبكة المتداخلة — اتجاه 2"), "round((W-2.4)/2.2)", (2.2, 0, 0))]
    # neck + flexible duct collar above the ceiling
    P += [box(("-W/2+4", 0, "-D/2+4"), ("W/2-4", 9, "D/2-4"), "#aab0b8", "metal", n="صندوق التوصيل (Plenum neck)"), cyl((0, 9, 0), "min(W,D)/2-7", 12, "#c7cad0", "metal", n="مجرى مرن معزول (Flexible duct)", seg=20)]
    return P

def grille(ret=False):
    c = "#e3e6ea" if ret else "#f1f1ec"
    return [box(("-W/2", -0.8, "-Dd/2"), ("W/2", 0, "Dd/2"), c, "gloss", n="إطار الشبكة (Frame)"),
            rep(box(("-W/2+1.0", -2.2, "-Dd/2+1.0"), ("W/2-1.0", -1.0, "-Dd/2+1.5"), c, "gloss", rot=[0, 0, 0], n="ريشة ثابتة (Fixed bar)"), "round((Dd-2)/2.2)+1", (0, 0, 2.2)),
            box(("-W/2+1.0", -2.2, "-Dd/2+1.0"), ("-W/2+1.5", -0.8, "Dd/2-1.0"), c, "gloss", n="حاجز نهاية"), box(("W/2-1.5", -2.2, "-Dd/2+1.0"), ("W/2-1.0", -0.8, "Dd/2-1.0"), c, "gloss"),
            box(("-W/2+1.5", 0, "-Dd/2+1.5"), ("W/2-1.5", "H-2", "Dd/2-1.5"), "#aab0b8", "metal", n="صندوق التوصيل (Plenum box) — صاج مجلفن"),
            box(("-W/2+2", "H-2", "-Dd/2+2"), ("W/2-2", "H", "Dd/2-2"), "#8e949c", "metal", n="شفة التوصيل بالمجرى (Duct flange)")]

def damper():
    P = [box(("-W/2", 0, "-D/2"), ("W/2", 1.2, "D/2"), "#aab0b8", "metal", n="غلاف المخمد — الجدار السفلي (Galv. sleeve)"), box(("-W/2", "H-1.2", "-D/2"), ("W/2", "H", "D/2"), "#aab0b8", "metal", n="غلاف المخمد — العلوي"),
         box(("-W/2", 0, "-D/2"), ("-W/2+1.2", "H", "D/2"), "#aab0b8", "metal", n="غلاف المخمد — الجانب"), box(("W/2-1.2", 0, "-D/2"), ("W/2", "H", "D/2"), "#aab0b8", "metal"),
         box(("-W/2-1.8", -1.8, "-D/2-1.2"), ("W/2+1.8", "H+1.8", "-D/2+0.4"), "#8e949c", "metal", n="شفة الوصل — جهة الدخول (Angle flange 30×30)"), box(("-W/2-1.8", -1.8, "D/2-0.4"), ("W/2+1.8", "H+1.8", "D/2+1.2"), "#8e949c", "metal", n="شفة الوصل — جهة الخروج")]
    P += [rep(box(("-W/2+1.2", 0.6, "-0.6"), ("W/2-1.2", 1.4, "0.6"), "#c9ced4", "metal", n="ريشة المخمد (Opposed blade)"), "max(2,round(H/6))", (0, "(H-2.4)/max(1,round(H/6)-1)", 0))]
    P += [box(("W/2+0.2", "H/2-5", "-D/2+1"), ("W/2+7.5", "H/2+5", "D/2-1"), "#2c3e50", "matte", n="مشغّل المخمد (Actuator / fusible link)"), box(("W/2-1.0", "H/2-0.4", "-0.5"), ("W/2+0.4", "H/2+0.4", "0.5"), STEEL_D, "metal", n="ذراع تعشيق الريش"),
          box(("-W/2+4", "H+1.9", "-D/2-1.2"), ("-W/2+16", "H+2.5", "-D/2+0.2"), "#d9d34a", "matte", n="ملصق: مخمد حريق / تحكم بالحجم (FD / VCD)")]
    return P

def chiller():
    # air-cooled screw chiller, 70 TR: L=W (48 m? plan 480 cm), D=250, H=250. Fans are separate elements on top.
    P = [box(("-W/2", 0, "-D/2"), ("W/2", 22, "D/2"), "#7a828a", "metal", n="الإطار القاعدي (Galvanised base frame — channels)"),
         box(("-W/2", 22, "-D/2"), ("-W/2+6", "H-50", "D/2"), "#c7d2dc", "gloss", n="غلاف الطرف — جهة الضواغط"), box(("W/2-6", 22, "-D/2"), ("W/2", "H-50", "D/2"), "#c7d2dc", "gloss", n="غلاف الطرف الآخر")]
    P += [box((f"-W/2+6", 22, "-D/2"), (f"W/2-6", "H-52", "-D/2+6"), "#3f464d", "matte", n="ملف المكثف (Microchannel coil) — جانب 1"),
          box((f"-W/2+6", 22, "D/2-6"), (f"W/2-6", "H-52", "D/2"), "#3f464d", "matte", n="ملف المكثف — جانب 2"),
          rep(box((f"-W/2+8", 24, "-D/2-0.6"), (f"W/2-8", 25.2, "-D/2"), "#6b747c", "metal", n="شبكة حماية الملف (Coil guard)"), 40, (0, 5.0, 0)),
          rep(box((f"-W/2+8", 24, "D/2"), (f"W/2-8", 25.2, "D/2+0.6"), "#6b747c", "metal", n="شبكة حماية الملف"), 40, (0, 5.0, 0)),
          box(("-W/2+6", "H-52", "-D/2+3"), ("W/2-6", "H-48", "D/2-3"), "#c7d2dc", "gloss", n="سقف حجرة المراوح (Fan deck)"),
          box(("-W/2+6", "H-48", "-D/2+3"), ("W/2-6", "H", "-D/2+5"), "#c7d2dc", "gloss", n="حاجز علوي"), box(("-W/2+6", "H-48", "D/2-5"), ("W/2-6", "H", "D/2-3"), "#c7d2dc", "gloss")]
    # control panel on one end, compressors (2) visible through service opening
    P += [box(("-W/2-0.0", 40, "-60"), ("-W/2+1", 190, "60"), "#aab6c2", "gloss", n="باب لوحة التحكم (Control panel door) — 110×150"), box(("-W/2-1.8", 106, "40"), ("-W/2+0.3", 124, "56"), STEEL_D, "metal", n="مقبض الباب"),
          cyl(("-W/2+30", 22, "-30"), 22, 60, "#2d3a46", "metal", ax="x", n="ضاغط لولبي (Screw compressor) رقم 1 — داخل الغلاف"), cyl(("-W/2+30", 22, "40"), 22, 60, "#2d3a46", "metal", ax="x", n="ضاغط لولبي رقم 2")]
    # evaporator shell + CHW nozzles (supply/return Victaulic) on the +x end
    P += [cyl(("W/2-20", 60, 0), 26, 160, "#9aa5b0", "gloss", ax="x", n="مبخّر قشرة وأنابيب (Shell & tube evaporator) — معزول"), cyl(("W/2+14", 52, "-24"), 9, 22, "#2d8bd6", "gloss", ax="x", n="فوهة تغذية المياه المبردة (CHW supply, Victaulic)"),
          cyl(("W/2+14", 52, "24"), 9, 22, "#e07b39", "gloss", ax="x", n="فوهة رجوع المياه المبردة (CHW return)"), tor(("W/2+20", 52, "-24"), 9.5, 1.2, "#2a2d31", ax="x", m="metal", n="وصلة فيكتوليك"),
          tor(("W/2+20", 52, "24"), 9.5, 1.2, "#2a2d31", ax="x", m="metal")]
    # lifting lugs and nameplate
    P += [box(("-W/2+20", "H", "-D/2+10"), ("-W/2+30", "H+6", "-D/2+16"), "#d9a21b", "metal", n="أذن رفع (Lifting lug)"), box(("W/2-30", "H", "D/2-16"), ("W/2-20", "H+6", "D/2-10"), "#d9a21b", "metal"),
          box(("-W/2+210", 140, "-D/2-0.3"), ("-W/2+250", 160, "-D/2"), "#fff", "matte", n="لوحة بيانات المبرّد (70 TR / 110 kW / R-134a / 3368 kg)")]
    return P

def pump():
    # horizontal split-case chilled water pump: W=126 (length), D=62, H=90
    P = [box(("-W/2", 0, "-D/2"), ("W/2", 8, "D/2"), "#5b6670", "metal", n="قاعدة الصلب (Baseplate) على أساس خرساني"),
         box(("-W/2-4", -10, "-D/2-4"), ("W/2+4", 0, "D/2+4"), "#9a9a92", "matte", n="كتلة خرسانية (Inertia base)")]
    # motor (left) / volute (right)
    P += [cyl(("-W/2+4", 8+23, 0), 23, 52, "#3d6aa8", "gloss", ax="x", n="المحرك الكهربائي 6.5 كيلوواط (TEFC) — بزعانف تبريد"), rep(tor(("-W/2+10", 8+23, 0), 23.4, 0.8, "#2f5486", ax="x", m="gloss", n="زعنفة تبريد"), 8, (6, 0, 0)),
          box(("-W/2+14", 8+23+22, "-10"), ("-W/2+34", 8+23+34, "10"), "#2f5486", "gloss", n="علبة توصيل المحرك"),
          cyl(("-W/2+56", 8+23, 0), 9, 10, "#c0392b", "matte", ax="x", n="حارس الوصلة (Coupling guard) أحمر"), box(("-W/2+54", 8+23-12, "-14"), ("-W/2+68", 8+23+12, "14"), "#c0392b", "matte"),
          cyl(("-W/2+70", 8+22, 0), 30, 46, "#38566f", "gloss", ax="x", n="جسم المضخة المشطور (Split casing volute)"), cyl(("-W/2+78", 8+22, 0), 31, 3, "#2a3f52", "metal", ax="x", n="خط الفصل (Split line) + براغي"),
          rep(cyl((f"-W/2+80", 8+22+27, "-24"), 1.1, 2.5, "#aab0b8", "metal", n="برغي غطاء المضخة"), 5, (0, 0, 12))]
    # suction (end) and discharge (top) flanges
    P += [cyl(("W/2-12", 8+22, 0), 11, 12, "#2d8bd6", "gloss", ax="x", n="فوهة الشفط (Suction) — 100 مم"), cyl(("W/2-2", 8+22, 0), 14.5, 2.2, "#8e949c", "metal", ax="x", n="شفة الشفط PN16"),
          cyl((f"-W/2+90", 8+22+26, 0), 9, 24, "#e07b39", "gloss", n="فوهة الطرد (Discharge)"), cyl((f"-W/2+90", 8+22+49, 0), 12, 2.2, "#8e949c", "metal", n="شفة الطرد PN16")]
    P += [box((-6, 8+23-5, "D/2-1"), (6, 8+23+5, "D/2+0.4"), "#fff", "matte", n="لوحة بيانات المضخة (168 GPM @ 100 ft, 1450 rpm)"), cyl(("-W/2+78", 8+22+22, "30"), 2.5, 3, "#2a2d31", "matte", ax="z", n="مقياس ضغط (Pressure gauge)")]
    return P

def fahu():
    P = [box(("-W/2", 0, "-D/2"), ("W/2", 14, "D/2"), "#5b6670", "metal", n="الإطار القاعدي (Base frame) فولاذ")]
    secs = [(0, 0.16, "قسم السحب واللوفر (Intake louvre section)"), (0.16, 0.38, "قسم الفلاتر (Filter section — G4 + F7)"), (0.38, 0.6, "قسم ملف التبريد (Cooling coil section)"),
            (0.6, 0.85, "قسم المروحة (Fan section — EC plug fan)"), (0.85, 1.0, "قسم الطرد (Discharge plenum)")]
    for a, b, nm in secs:
        P += [box((f"-W/2+W*{a}", 14, "-D/2"), (f"-W/2+W*{b}-0.4", "H", "D/2"), "#bfd0e0", "gloss", n=f"{nm} — لوح ساندويتش معزول 50 مم"),
              box((f"-W/2+W*{a}+3", 40, "D/2"), (f"-W/2+W*{b}-3.4", 150, "D/2+1.8"), "#a9bccf", "gloss", n="باب وصول (Access door)"), box((f"-W/2+W*{b}-9", 94, "D/2+1.8"), (f"-W/2+W*{b}-6", 104, "D/2+3.2"), STEEL_D, "metal", n="مقبض الباب")]
    P += [rep(box(("-W/2+12", 20, "-D/2+4"), ("-W/2+W*0.16-4", 26, "D/2-4"), "#4a525a", "matte", n="ريشة لوفر السحب"), 18, (0, 7, 0)), box(("W/2", 40, "-D/2+20"), ("W/2+6", "H-30", "D/2-20"), "#8e949c", "metal", n="شفة التصريف (Duct flange)"),
          cyl(("-W/2+W*0.5", "H-6", 0), 10, 10, "#b87333", "metal", n="وصلة ملف المياه المبردة"), box(("W/2-60", 90, "D/2+1.8"), ("W/2-30", 100, "D/2+2.2"), "#fff", "matte", n="لوحة بيانات FAHU")]
    return P

def chiller_fan():
    P = [cyl((0, 0, 0), 43, 4, "#2a2d31", "metal", seg=28, caps=False, n="حلقة الفوهة (Fan ring / venturi)")]
    for k in range(5):
        P += [dict(box((2, 0.5, -7), (41, 1.8, 7), "#2f3640", "matte", n="ريشة المروحة (Blade)"), rot=[0, k * 72, 12])]
    P += [cyl((0, 0, 0), 6.5, 5, "#14171a", "metal", n="محور المروحة (Hub)"), tor((0, 6.2, 0), 43, 0.5, "#3b3f45", m="metal", n="حلقة شبكة الحماية")]
    for r in (12, 22, 32):
        P += [tor((0, 5.6, 0), r, 0.3, "#3b3f45", m="metal", n="حلقة شبكة")]
    for k in range(12):
        P += [dict(box((0, 5.2, -0.25), (43, 5.8, 0.25), "#3b3f45", "metal", n="سلك شعاعي (Guard wire)"), rot=[0, k * 30, 0])]
    return P

def make():
    out = {}
    def add(t): out[t[0]] = t[1]
    def S(id_, name, en, parts, place, lod=4.5, conf="derived", facts=None, asm=None, src=None, dims=None, **kw):
        add(sample(id_, name, en, "mechanical", parts, place=place, lod=lod, conf=conf, src=src or SRC_AC, facts=facts or [], asm=(asm or []) + [ASM], dims=dims or {}, **kw))
    B = {"mode": "box", "anchor": "bottom"}; T = {"mode": "box", "anchor": "top"}
    S("fcu", "وحدة ملف مروحة FCU مخفية (مجرى) — مثبتة بالسقف", "Ducted fan coil unit (concealed, ceiling hung)", fcu(), B, lod=5.5, src=SRC_AC, facts=[["الأبعاد من المخطط", "95 × 38 × 30 سم"], ["النوع", "FCU أفقي مخفي بمجرى"], ["المياه", "مبردة 12/7 م° — وصلتان ⌀22 مم"], ["الجدول", "AC-106 (سعات وتدفقات لكل وحدة)"]],
      asm=["ارتفاع التركيب فوق السقف المستعار: افتراض (2.78 م فوق الأرضية)", "عدد صفوف الملف والمروحة داخل الغلاف: غير مرسومة"], dims={"W": 95, "D": 38, "H": 30})
    S("thermostat", "ثرموستات غرفة رقمي", "Digital room thermostat", thermostat(), WALL if False else {"mode": "box", "anchor": "bottom", "mount": "wall"}, lod=3.5, facts=[["الارتفاع", "1.4 م (افتراض)"]], asm=["ارتفاع التركيب 1.4 م: افتراض"], dims={"W": 10, "D": 4, "H": 10})
    S("diff_supply", "ناشر هواء تغذية 4 اتجاهات (سقفي مربع)", "4-way ceiling supply diffuser", diffuser(False), T, lod=5, facts=[["الطبقة", "M_SAD_DIFF"], ["التوصيل", "مجرى مرن معزول من الصندوق"]], asm=["المقاس الفعلي للرقبة: من رمز المخطط؛ ارتفاع الصندوق فوق السقف: افتراض"], dims={"W": 40, "D": 40, "H": 4})
    S("diff_return", "ناشر هواء رجوع بشبكة متداخلة (Egg-crate)", "Egg-crate return air diffuser", diffuser(True), T, lod=5, facts=[["الطبقة", "M_RAD_DIFF"]], dims={"W": 40, "D": 40, "H": 4})
    S("grille_supply", "شبكة تغذية بريش ثابتة (Linear bar grille)", "Supply air linear bar grille", grille(False), T, lod=5, facts=[["الطبقة", "M_SAG_GRILL"]], vars={"Dd": "max(D,12)"}, dims={"W": 60, "D": 20, "H": 22}, asm=["عمق الشبكة D يساوي 0 في بعض الرموز؛ يُؤخذ 12 سم كحد أدنى"])
    S("grille_return", "شبكة رجوع بريش ثابتة", "Return air linear bar grille", grille(True), T, lod=5, facts=[["الطبقة", "M_RAG_GRILL"]], vars={"Dd": "max(D,12)"}, dims={"W": 60, "D": 30, "H": 22}, asm=["عمق الشبكة D يساوي 0 في بعض الرموز؛ يُؤخذ 12 سم كحد أدنى"])
    S("damper", "مخمد حريق / تحكم بالحجم (VCD/FD/MFD)", "Fire / volume control damper", damper(), B, lod=5, facts=[["الطبقة", "M_HVAC_DAM"], ["الوصل", "شفتان زاويتان 30×30"], ["الريش", "متقابلة (Opposed blades)"]], asm=["النوع (حريق/تحكم) وزمن الإغلاق: غير مميّز على الرمز"], dims={"W": 60, "D": 14, "H": 18})
    S("chiller", "مبرّد مياه مبرّدة بالهواء — لولبي 70 TR", "Air-cooled screw chiller 70 TR", chiller(), B, lod=14, conf="doc", src=["MECH1 ص15: مخطط السطح CHW-104", "MECH1 ص16: جدول المبرّدات CHW-105"],
      facts=[["السعة", "70 TR لكل مبرّد (2)"], ["النوع", "ضاغط لولبي — غاز R-134a"], ["القدرة", "110 كيلوواط، 415 فولت / 3 أطوار / 50 هرتز"], ["الأبعاد (الجدول)", "L 3.6 × W 2.5 × H 2.5 م"], ["الوزن", "3368 كجم"], ["المياه", "12 م° / 7 م° — 168 GPM"]],
      asm=["مسقط الرسم 4.8×2.5 م يخالف طول الجدول 3.6 م — بانتظار تأكيدك", "التقسيم الداخلي (ضاغطان، مبخّر، موضع لوحة التحكم) قياسي"], dims={"W": 480, "D": 250, "H": 250})
    S("chwp", "مضخة مياه مبردة أفقية مشطورة (Split case)", "Horizontal split-case chilled water pump", pump(), B, lod=8, src=["MECH1 ص15-16: جدول المضخات CHWP"],
      facts=[["العدد", "3 (2 عاملة + 1 احتياط)"], ["التدفق/الضغط", "168 GPM عند 100 قدم (تقديري)"], ["السرعة", "1450 د/د بمبدّل VFD"], ["المحرك", "6.5 كيلوواط (تقديري)"]], asm=["ارتفاع المضخة مع المحرك 0.9 م: افتراض"], dims={"W": 126, "D": 62, "H": 90})
    S("fahu", "وحدة معالجة الهواء النقي FAHU", "Fresh air handling unit (FAHU)", fahu(), B, lod=10, src=["MECH1 ص15: طبقة AC D FRESH"], facts=[["الاسم", "FAHU — Fresh Air Handling Unit"]], asm=["الارتفاع 1.8 م والتقسيم الداخلي للأقسام: افتراض"], dims={"W": 239, "D": 133, "H": 180})
    S("chiller_fan", "مروحة مبرّد بحماية سلكية", "Chiller axial fan with guard", chiller_fan(), {"mode": "cyl", "anchor": "bottom"}, lod=10, src=["MECH1 ص15: مروحة المبرّد ⌀86 سم (6 لكل مبرّد)"], facts=[["القطر", "86 سم"]], asm=["عدد الريش وزاويتها: قياسية"], dims={"W": 86, "D": 86, "H": 6})
    return out

RULES = [{"c": "M.equip", "t": t, "s": t} for t in ("fcu", "thermostat", "chiller", "chwp", "fahu")] + [{"c": "M.outlet", "t": t, "s": t} for t in ("diff_supply", "diff_return", "grille_supply", "grille_return")] + \
        [{"c": "M.damper", "t": "damper", "s": "damper"}, {"c": "M.fan", "t": "chiller_fan", "s": "chiller_fan"}]
