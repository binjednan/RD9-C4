# -*- coding: utf-8 -*-
"""electrical samples: luminaires TYPE-1..13 (ELEC1 legend), sockets/switches (EP-109 details), fire-alarm devices, low-current devices, earthing.
Wall devices: local z = 0 is the centre of the plan symbol (4 cm deep); the wall face is the plane z = -D/2, +z points into the room (the engine
rotates the sample toward the room side of the nearest wall). Ceiling devices hang below y = 0 (anchor 'top')."""
from .lib import *

WALL = {"mode": "box", "anchor": "bottom", "mount": "wall"}
CEIL = {"mode": "box", "anchor": "top"}
CEILC = {"mode": "cyl", "anchor": "top"}
SRC_L = ["ELEC1: مفتاح الإنارة (TYPE-1..13) ومخططات الإنارة"]
SRC_P = ["ELEC1: مفتاح القوى + تفاصيل التركيب EP-109"]
SRC_F = ["ELEC2: مخططات إنذار الحريق ومفتاح الرموز"]
SRC_T = ["ELEC2: مخططات التيار الخفيف ومفتاح الرموز"]
ASM_STD = "الشكل التفصيلي قياسي لهذه الفئة (ليس طرازًا محددًا) — الطراز التجاري غير مذكور في المستندات"

# ----------------------------------------------------------------- wall plates (BS 1363 style, 86 mm modules)
def _pl(w, h, t=0.9, c=PLASTIC, cy="H/2", z0="-D/2"):
    return box((f"-{w/2}", f"{cy}-{h/2}", z0), (f"{w/2}", f"{cy}+{h/2}", f"{z0}+{t}"), c, "gloss", n="اللوحة الأمامية (Faceplate)")

def _screws(w, h, cy="H/2", z="-D/2+0.9"):
    return [cyl((0, f"{cy}+{h/2-0.8}", z), 0.28, 0.25, STEEL_D, "metal", ax="z", n="برغي تثبيت"), cyl((0, f"{cy}-{h/2-0.8}", z), 0.28, 0.25, STEEL_D, "metal", ax="z")]

def _socket_face(x, cy="H/2", z="-D/2+0.9", c="#2a2a2a"):
    P = [box((f"{x}-0.45", f"{cy}+0.6", z), (f"{x}+0.45", f"{cy}+2.1", f"{z}+0.12"), c, "rubber", n="فتحة الأرضي (Earth)"),
         box((f"{x}-1.65", f"{cy}-1.2", z), (f"{x}-0.8", f"{cy}+0.2", f"{z}+0.12"), c, "rubber", n="فتحة الطور (Live)"),
         box((f"{x}+0.8", f"{cy}-1.2", z), (f"{x}+1.65", f"{cy}+0.2", f"{z}+0.12"), c, "rubber", n="فتحة التعادل (Neutral)")]
    return P

def _rocker(x, y, w=2.2, h=1.1, c=WHITE, z="-D/2+0.9", ax_h=False):
    return box((f"{x}-{w/2}", f"{y}-{h/2}", z), (f"{x}+{w/2}", f"{y}+{h/2}", f"{z}+0.45"), c, "gloss", n="مفتاح (Rocker)")

def _neon(x, y, z="-D/2+0.9", c="#e6892b"):
    return cyl((x, y, z), 0.32, 0.18, c, "emit", ax="z", n="مؤشر نيون")

def socket_plate(gangs=1, switched=True, c=PLASTIC, neon=False, flex=False, amp=13, label=None):
    w = 8.6 if gangs == 1 else 14.6
    P = [_pl(w, 8.6, c=c)]
    P += _screws(w, 8.6)
    xs = [0] if gangs == 1 else [-3.0, 3.0]
    for x in xs:
        if flex:
            P += [cyl((x, "H/2+0.8", "-D/2+0.9"), 1.15, 0.5, "#2a2a2a", "rubber", ax="z", n="مخرج مرن (Flex outlet)"), cyl((x, "H/2+0.8", "-D/2+1.0"), 0.55, 0.45, c, "gloss", ax="z")]
            P += [_rocker(x, "H/2-2.7", 3.2, 1.3, WHITE)]
            if neon: P += [_neon(x + 2.5, "H/2-2.7")]
        else:
            P += _socket_face(x)
            if switched: P += [_rocker(x, "H/2-3.0", 2.4, 1.1, WHITE)]
            if neon: P += [_neon(x + 1.7, "H/2-3.0")]
    return P

def switch_plate(gangs=1, c=PLASTIC, two_way=False):
    w = 8.6 if gangs <= 1 else (13.0 if gangs == 2 else 17.2)
    P = [_pl(w, 8.6, c=c)] + _screws(w, 8.6)
    step = 4.3
    for k in range(gangs):
        x = (k - (gangs - 1) / 2) * step
        P += [box((f"{x}-1.8", "H/2-2.9", "-D/2+0.9"), (f"{x}+1.8", "H/2+2.9", "-D/2+1.45"), WHITE, "gloss", n=f"مفتاح (Rocker) رقم {k+1}"),
              box((f"{x}-1.8", "H/2-0.15", "-D/2+1.45"), (f"{x}+1.8", "H/2+0.15", "-D/2+1.5"), "#c8c8c0", "matte", n="خط الفصل بين نصفي المفتاح")]
    return P

def wp_box(h=10.0, w=10.0, cd=6.5, kind="socket"):
    P = [box((f"-{w/2}", f"H/2-{h/2}", "-D/2"), (f"{w/2}", f"H/2+{h/2}", f"-D/2+{cd}"), "#8a9097", "gloss", n="علبة مقاومة للماء IP66 (ABS رمادي)"),
         box((f"-{w/2-0.8}", f"H/2-{h/2-0.8}", f"-D/2+{cd}"), (f"{w/2-0.8}", f"H/2+{h/2-0.8}", f"-D/2+{cd+0.4}"), "#9aa1a8", "gloss", n="غطاء شفاف مفصلي مع وسادة مطاطية"),
         box((f"-{w/2}", f"H/2-{h/2}", f"-D/2+{cd-1.1}"), (f"{w/2}", f"H/2-{h/2-0.5}", f"-D/2+{cd}"), STEEL_D, "metal", n="مفصل الغطاء"),
         cyl((f"{w/2-1.0}", f"H/2-{h/2-0.01}", f"-D/2+2.5"), 0.9, 1.4, BLACK, "rubber", ax="y", n="مدخل كابل (Gland)", r1=0.9)]
    if kind == "socket":
        P += [box((-3, "H/2-3.3", f"-D/2+{cd+0.2}"), (3, "H/2+3.3", f"-D/2+{cd+0.55}"), PLASTIC, "gloss", n="مقبس 13A داخل العلبة")] + _socket_face(0, z=f"-D/2+{cd+0.55}")
    else:
        P += [box((-1.8, "H/2-2.9", f"-D/2+{cd+0.2}"), (1.8, "H/2+2.9", f"-D/2+{cd+1.0}"), WHITE, "gloss", n="مفتاح داخل العلبة")]
    return P

def enclosure(w, h, d, c="#cfd3d8", door=True, led=False, handle=True, name="لوحة"):
    zb = "-D/2"
    P = [box((f"-{w/2}", f"H/2-{h/2}", zb), (f"{w/2}", f"H/2+{h/2}", f"{zb}+{d}"), c, "gloss", n=f"{name} — جسم الصاج")]
    if door:
        P += [box((f"-{w/2-1.2}", f"H/2-{h/2-1.2}", f"{zb}+{d}"), (f"{w/2-1.2}", f"H/2+{h/2-1.2}", f"{zb}+{d+0.5}"), "#dfe2e6", "gloss", n="الباب الأمامي (مفصلي)"),
              box((f"-{w/2}", f"H/2-{h/2}", f"{zb}+{d-0.8}"), (f"-{w/2-0.8}", f"H/2+{h/2}", f"{zb}+{d+0.1}"), STEEL_D, "metal", n="مفصلات الباب")]
    if handle:
        P += [cyl((f"{w/2-3}", "H/2", f"{zb}+{d+0.5}"), 0.9, 0.9, STEEL_D, "metal", ax="z", n="قفل بمفتاح"), box((f"{w/2-3.6}", "H/2-0.25", f"{zb}+{d+1.2}"), (f"{w/2-2.4}", "H/2+0.25", f"{zb}+{d+1.5}"), STEEL, "metal")]
    P += [box((f"-{w/2-2}", f"H/2+{h/2-3.2}", f"{zb}+{d+0.5}"), (f"{w/2-2}", f"H/2+{h/2-1.6}", f"{zb}+{d+0.7}"), "#2c3e50", "matte", n="لوحة تعريف (Label)")]
    if led:
        for k in range(3): P += [cyl((f"-{w/2-3}+{k*2.2}", f"H/2+{h/2-4.8}", f"{zb}+{d+0.5}"), 0.4, 0.2, ["#2ecc40", "#ff4136", "#ffdc00"][k], "emit", ax="z", n="مؤشر LED")]
    return P

# ----------------------------------------------------------------- luminaires
def lum_linear():          # TYPE-1 linear ceiling fixture 2x22W LED IP65 (118-121 x 10-20)
    return [box(("-W/2", "-4.6", "-D/2"), ("W/2", "-0.0", "D/2"), "#e8e8e4", "gloss", n="الهيكل (Polycarbonate/ABS) — محكم IP65"),
            box(("-W/2+1.0", "-4.9", "-D/2+1.2"), ("W/2-1.0", "-4.5", "D/2-1.2"), "#fbfbf6", "emit", n="ناشر LED معتم (Opal diffuser) — 2×22W"),
            box(("-W/2", "-4.7", "-D/2"), ("-W/2+1.2", "-0.2", "D/2"), "#c9ccd1", "gloss", n="غطاء طرفي"), box(("W/2-1.2", "-4.7", "-D/2"), ("W/2", "-0.2", "D/2"), "#c9ccd1", "gloss", n="غطاء طرفي"),
            rep(box(("-W/2+14", "-5.2", "-D/2-0.3"), ("-W/2+17", "-3.0", "D/2+0.3"), STEEL, "metal", n="مشبك فولاذ لا يصدأ (Clip)"), "round((W-28)/(W-28)*4)+0", ("(W-31)/3", 0, 0)),
            cyl((0, -0.1, "D/2-1.5"), 0.9, 0.9, BLACK, "rubber", n="مدخل كابل (Gland)")]

def lum_drum(dia=26, h=9.0, c=WHITE, ip="IP65"):
    r = dia / 2
    return [cyl((0, -2.2, 0), r, 2.2, "#e9e9e5", "gloss", n="القاعدة (Base plate)"),
            sph((0, -2.2, 0), r, "#f6f6f2", s=[r - 0.4, h - 2.2, r - 0.4], seg=22, n="الغطاء الأوبالي (Opal dome)", m="emit"),
            tor((0, -2.2, 0), r - 0.2, 0.45, "#c9ccd1", m="gloss", n="طوق الغطاء (Gasket ring)")]

def lum_bathroom(w=60):
    return [box((f"-W/2", "H/2-4", "-D/2"), ("W/2", "H/2+4", "-D/2+6.5"), ALU, "metal", n="هيكل ألمنيوم (Mirror light)"),
            box(("-W/2+1.4", "H/2-3.2", "-D/2+6.5"), ("W/2-1.4", "H/2+3.2", "-D/2+7.2"), "#fbfbf6", "emit", n="ناشر أوبال"),
            box(("-W/2", "H/2-4", "-D/2"), ("-W/2+1.2", "H/2+4", "-D/2+7.4"), "#d6d9dd", "gloss", n="غطاء طرفي"), box(("W/2-1.2", "H/2-4", "-D/2"), ("W/2", "H/2+4", "-D/2+7.4"), "#d6d9dd", "gloss"),
            box(("-3.6", "H/2-9.5", "-D/2+0.6"), ("3.6", "H/2-4", "-D/2+3.2"), PLASTIC, "gloss", n="مقبس حلاقة مدمج (Shaver socket 115/230V)"),
            cyl((0, "H/2-6.5", "-D/2+3.2"), 1.4, 0.2, "#444", "rubber", ax="z", n="فتحة مقبس الحلاقة")]

def lum_recessed_louvre(dia=None, sq=59.5, cells=6):
    P = [box((f"-{sq/2+1.1}", -0.2, f"-{sq/2+1.1}"), (f"{sq/2+1.1}", 0.4, f"{sq/2+1.1}"), "#f4f4f0", "gloss", n="إطار التثبيت على شبكة السقف المعلق"),
         box((f"-{sq/2}", "-5.5", f"-{sq/2}"), (f"{sq/2}", "-0.0", f"{sq/2}"), "#fafaf6", "gloss", n="جسم الكشاف الغاطس (Recessed housing)")]
    step = sq / cells
    for k in range(cells + 1):
        x = -sq / 2 + k * step
        P += [box((f"{x}-0.08", -5.3, f"-{sq/2}"), (f"{x}+0.08", -0.4, f"{sq/2}"), "#d9dde2", "metal", n="ريشة عاكس مكافئ (Parabolic louvre blade) — اتجاه X"),
              box((f"-{sq/2}", -5.3, f"{x}-0.08"), (f"{sq/2}", -0.4, f"{x}+0.08"), "#d9dde2", "metal", n="ريشة عاكس مكافئ — اتجاه Z")]
    P += [box((f"-{sq/2-1}", "-0.5", f"-{sq/2-1}"), (f"{sq/2-1}", "-0.3", f"{sq/2-1}"), "#fff7d0", "emit", n="وحدة LED 43W")]
    return P

def lum_recessed_prism(sq=59.5):
    P = [box((f"-{sq/2+1.1}", -0.2, f"-{sq/2+1.1}"), (f"{sq/2+1.1}", 0.4, f"{sq/2+1.1}"), "#f4f4f0", "gloss", n="إطار التثبيت"),
         box((f"-{sq/2}", "-3.0", f"-{sq/2}"), (f"{sq/2}", "-0.0", f"{sq/2}"), "#fafaf6", "gloss", n="جسم الكشاف الغاطس"),
         box((f"-{sq/2-1.0}", "-3.4", f"-{sq/2-1.0}"), (f"{sq/2-1.0}", "-3.0", f"{sq/2-1.0}"), "#f5f9ff", "emit", n="ناشر منشوري (Prismatic acrylic) — 31W")]
    for k in range(1, 12):
        x = -sq / 2 + k * sq / 12
        P += [box((f"{x}-0.05", -3.45, f"-{sq/2-1.0}"), (f"{x}+0.05", -3.4, f"{sq/2-1.0}"), "#dfe6ee", "gloss", n="نقش المنشور — خط"), box((f"-{sq/2-1.0}", -3.45, f"{x}-0.05"), (f"{sq/2-1.0}", -3.4, f"{x}+0.05"), "#dfe6ee", "gloss")]
    return P

def lum_downlight(dia=22, opal=True, cut=20):
    r = dia / 2
    P = [tor((0, -0.15, 0), r - 0.4, 0.4, "#f4f4f0", m="gloss", ax="y", n="طوق التشطيب (Trim ring)"),
         cyl((0, -9.0, 0), cut / 2, 9.0, "#e3e3df", "gloss", n="العلبة الغاطسة (Housing)")]
    if opal:
        P += [cyl((0, -0.7, 0), r - 0.9, 0.5, "#fffdf2", "emit", n="ناشر أوبال مسطح — 28W")]
    else:
        P += [cyl((0, -6.0, 0), r - 1.2, 6.0, "#d9dde2", "metal", r1=r - 3.4, n="عاكس مخروطي (Reflector cone)"), cyl((0, -6.3, 0), r - 4.6, 0.3, "#fff7d0", "emit", n="وحدة LED 26W")]
    P += [box((f"-{cut/2+1.3}", -7.5, "-0.4"), (f"-{cut/2-0.1}", -4.0, "0.4"), STEEL, "metal", n="نابض تثبيت (Spring clip)"), box((f"{cut/2-0.1}", -7.5, "-0.4"), (f"{cut/2+1.3}", -4.0, "0.4"), STEEL, "metal")]
    P += [box((-6, "1.0", -5), (6, "7", 5), "#444b53", "matte", n="مصدر الطاقة (LED driver) فوق السقف")]
    return P

def lum_ramp():
    return [box((-18, -9.5, -15.5), (18, -0.0, 15.5), "#5d6369", "metal", n="هيكل ألمنيوم مصبوب (IP65)"),
            box((-16.5, -10.2, -14), (16.5, -9.4, 14), "#f3f6fa", "emit", n="ناشر منشوري — 26W"),
            box((-18.8, -6, -1.5), (-18, -1, 1.5), "#40464c", "matte", n="لسان تثبيت"), cyl((14, -0.1, 13), 1.0, 1.0, BLACK, "rubber", n="مدخل كابل")]

def lum_wall_ext():
    return [box(("-W/2", "H/2-7", "-D/2"), ("W/2", "H/2+7", "-D/2+9.5"), "#6c7279", "metal", n="هيكل ألمنيوم مصبوب (IP65)"),
            box(("-W/2+2.0", "H/2+7", "-D/2+1.2"), ("W/2-2.0", "H/2+7.4", "-D/2+8.2"), "#fff7d0", "emit", n="نافذة إضاءة علوية (10W)"),
            box(("-W/2+2.0", "H/2-7.4", "-D/2+1.2"), ("W/2-2.0", "H/2-7", "-D/2+8.2"), "#fff7d0", "emit", n="نافذة إضاءة سفلية (10W)"),
            box(("-W/2+0.3", "H/2-6", "-D/2+9.5"), ("W/2-0.3", "H/2+6", "-D/2+10.0"), "#4a5057", "metal", n="واجهة أمامية")]

def lum_chandelier(big=False):
    flex = 28 if not big else 40; r = 3.2 if not big else 4.2
    return [cyl((0, -1.6, 0), 6.0, 1.6, "#f4f4f0", "gloss", n="وردة السقف (Ceiling rose)"),
            cyl((0, -1.6, 0), 0.5, 0.8, STEEL_D, "metal", n="خطاف التعليق (Hook)"),
            cyl((0, f"-{flex}", 0), 0.18, flex, BLACK, "rubber", n="سلك التعليق (Flex)"),
            cyl((0, f"-{flex+4}", 0), 1.4, 4, "#d9c27c", "metal", n="حامل المصباح (E27 lampholder)"),
            sph((0, f"-{flex+4+r}", 0), r, "#fffbe6", s=[r, r * 1.25, r], seg=18, m="emit", n="مصباح LED")]

# ----------------------------------------------------------------- fire alarm
def det_smoke(sounder=False, dia=10, h=6.0, heat=False, co=False):
    r = dia / 2
    P = [cyl((0, -0.9, 0), r, 0.9, "#f4f4f0", "gloss", n="القاعدة (Mounting base)"),
         cyl((0, f"-{h}", 0), r - 0.4, h - 0.9, "#fafaf6", "gloss", r1=r, n="رأس الكاشف (Detector head)")]
    if heat:
        P += [cyl((0, f"-{h+0.2}", 0), 1.6, 0.4, "#c9ccd1", "metal", n="عنصر استشعار الحرارة"), tor((0, f"-{h+0.1}", 0), 2.6, 0.35, "#d9dde2", m="metal", n="حلقة واقية")]
    else:
        for k in range(8):
            a = k * 45
            P += [dict(box((f"{(r-1.4)}-0.1", f"-{h-0.5}", -0.2), (f"{r-0.4}", f"-{h-4.2}", 0.2), "#222", "rubber", n="فتحة دخول الدخان"), rot=[0, a, 0])]
    P += [cyl((r - 1.9, f"-{h+0.1}", 0), 0.35, 0.2, "#ff4136", "emit", n="مؤشر LED (إنذار)")]
    if sounder: P += [cyl((0, f"-{h+0.1}", 0), 1.9, 0.25, "#222", "rubber", n="مكبر الصوت المدمج (Sounder)"), tor((0, f"-{h+0.1}", 0), 2.4, 0.2, "#aaa", m="metal")]
    if co: P += [cyl((0, f"-{h+0.1}", 0), 2.6, 0.2, "#d6d6d0", "matte", n="شبكة مستشعر CO"), box((-1.2, f"-{h+0.12}", -0.4), (1.2, f"-{h+0.3}", 0.4), "#1b3a5c", "matte", n="ملصق CO")]
    return P

def callpoint():
    return [box((-4.5, "H/2-4.5", "-D/2"), (4.5, "H/2+4.5", "-D/2+4.0"), "#c0392b", "gloss", n="جسم نقطة النداء (Manual call point) أحمر"),
            box((-3.3, "H/2-3.3", "-D/2+4.0"), (3.3, "H/2+3.3", "-D/2+4.35"), "#f4f1ea", "gloss", n="عنصر الزجاج (Break glass)"),
            box((-3.3, "H/2-0.2", "-D/2+4.35"), (3.3, "H/2+0.2", "-D/2+4.45"), "#444", "matte", n="خط كسر"),
            cyl((0, "H/2+3.9", "-D/2+4.0"), 0.45, 0.3, "#ff4136", "emit", ax="z", n="مؤشر LED"),
            box((-2.5, "H/2-4.0", "-D/2+4.35"), (2.5, "H/2-3.2", "-D/2+4.4"), "#fff", "matte", n="ملصق «PUSH»")]

def sounder_flasher():
    return [box(("-W/2", "H/2-5", "-D/2"), ("W/2", "H/2+5", "-D/2+7.0"), "#c0392b", "gloss", n="جسم الصفارة (Sounder)"),
            box(("-W/2+1.4", "H/2+0.8", "-D/2+7.0"), ("W/2-1.4", "H/2+4.2", "-D/2+7.6"), "#fff0b0", "emit", n="عدسة الوامض (Strobe lens)"),
            rep(box(("-W/2+2.0", "H/2-4.0", "-D/2+7.0"), ("W/2-2.0", "H/2-3.4", "-D/2+7.4"), "#1a1a1a", "rubber", n="شبكة السماعة"), 4, (0, -0.9, 0))]

def lum_emerg(dia=14):
    r = dia / 2
    return [tor((0, -0.15, 0), r - 0.4, 0.4, "#f4f4f0", m="gloss", n="طوق التشطيب"),
            cyl((0, -6.0, 0), r - 0.8, 6.0, "#e3e3df", "gloss", n="جسم الكشاف + بطارية Ni-Cd/Li"),
            cyl((0, -0.7, 0), r - 1.2, 0.5, "#fffdf2", "emit", n="عدسة LED طوارئ (Maintained/Non-maintained)"),
            cyl((r - 2.4, -0.5, 0), 0.35, 0.2, "#2ecc40", "emit", n="مؤشر الشحن"), box((-0.4, -0.55, -r + 2.2), (0.4, -0.5, -r + 3.6), "#555", "matte", n="زر الاختبار")]

def exit_sign():
    return [box(("-W/2", "H/2-9", "-D/2"), ("W/2", "H/2+9", "-D/2+6"), "#e8e8e4", "gloss", n="صندوق لوحة المخرج (EXIT) LED"),
            box(("-W/2+1.2", "H/2-7.8", "-D/2+6.0"), ("W/2-1.2", "H/2+7.8", "-D/2+6.3"), "#1e9e4a", "emit", n="وجه أخضر مضيء"),
            box(("-W/2+3.5", "H/2-4.5", "-D/2+6.3"), ("-W/2+9.5", "H/2+4.5", "-D/2+6.4"), "#ffffff", "emit", n="شخص يهرب (Pictogram)"),
            box(("-2", "H/2-3.5", "-D/2+6.3"), ("W/2-4", "H/2+3.5", "-D/2+6.4"), "#ffffff", "emit", n="نص EXIT / سهم الاتجاه")]

def wall_speaker():
    return [box(("-W/2", "H/2-8", "-D/2"), ("W/2", "H/2+8", "-D/2+4.0"), "#f4f4f0", "gloss", n="صندوق سماعة الإخلاء الصوتي"),
            cyl((0, "H/2", "-D/2+4.0"), 6.2, 0.4, "#2a2a2a", "rubber", ax="z", n="مخروط السماعة"), tor((0, "H/2", "-D/2+4.2"), 5.4, 0.25, "#aaa", ax="z", m="metal", n="حلقة"),
            rep(box(("-5.2", "H/2-5.5", "-D/2+4.4"), ("5.2", "H/2-5.2", "-D/2+4.5"), "#555", "matte", n="خطوط الشبكة"), 8, (0, 1.4, 0))]

def panel(w, h, d, name, screen=False, leds=0, keypad=False, c="#d6dae0"):
    P = enclosure(w, h, d, c=c, led=False, handle=True, name=name)
    z = f"-D/2+{d+0.5}"
    if screen:
        P += [box((f"-{w/2-4}", f"H/2+{h/2-14}", z), (f"{w/2-4}", f"H/2+{h/2-5}", f"{z}+0.2"), "#0b2a3a", "emit", n="شاشة العرض LCD")]
    for k in range(leds):
        P += [cyl((f"-{w/2-4}+{k*2.4}", f"H/2+{h/2-17}", z), 0.45, 0.2, ["#2ecc40", "#ffdc00", "#ff4136", "#2ecc40"][k % 4], "emit", ax="z", n="مؤشر LED")]
    if keypad:
        for r_ in range(3):
            for c_ in range(3): P += [box((f"-5+{c_*3.4}", f"H/2-4-{r_*3.4}", z), (f"-5+{c_*3.4}+2.6", f"H/2-4-{r_*3.4}+2.6", f"{z}+0.35"), "#3b3f45", "matte", n="مفتاح لوحة اللمس")]
    return P

# ----------------------------------------------------------------- low current
def rj45_plate(dual=False, tv=False, c=PLASTIC, label=None):
    w = 8.6
    P = [_pl(w, 8.6, c=c)] + _screws(w, 8.6)
    nodes = [(0, 1.7), (0, -1.7)] if dual else [(0, 0)]
    for (x, y) in nodes:
        if tv: P += [cyl((x, f"H/2+{y}", "-D/2+0.9"), 1.15, 0.6, "#c9ccd1", "metal", ax="z", n="مخرج TV/SAT (IEC coax)"), cyl((x, f"H/2+{y}", "-D/2+1.5"), 0.45, 0.4, "#222", "rubber", ax="z")]
        else: P += [box((f"{x}-1.15", f"H/2+{y}-0.75", "-D/2+0.9"), (f"{x}+1.15", f"H/2+{y}+0.75", "-D/2+1.35"), "#2a2a2a", "rubber", n="مقبس RJ45 (Cat6)"), box((f"{x}-0.8", f"H/2+{y}+0.75", "-D/2+0.9"), (f"{x}+0.8", f"H/2+{y}+1.05", "-D/2+1.2"), "#ffcf33", "emit", n="مؤشر")]
    return P

def small_box(w, h, d, c="#e6e6e0", name="صندوق وصلات", screws=True, cover_lines=True):
    P = [box((f"-{w/2}", f"H/2-{h/2}", "-D/2"), (f"{w/2}", f"H/2+{h/2}", f"-D/2+{d}"), c, "gloss", n=f"{name} — جسم بلاستيكي"),
         box((f"-{w/2-0.7}", f"H/2-{h/2-0.7}", f"-D/2+{d}"), (f"{w/2-0.7}", f"H/2+{h/2-0.7}", f"-D/2+{d+0.35}"), "#f0f0ea", "gloss", n="الغطاء")]
    if screws:
        for sx in (-1, 1):
            for sy in (-1, 1): P += [cyl((f"{sx*(w/2-1.6)}", f"H/2+{sy*(h/2-1.6)}", f"-D/2+{d+0.35}"), 0.3, 0.2, STEEL_D, "metal", ax="z", n="برغي الغطاء")]
    return P

def cctv_dome():
    return [cyl((0, -0.6, 0), 7.0, 0.6, "#e9e9e5", "gloss", n="القاعدة"), sph((0, -0.6, 0), 6.0, "#25292e", s=[6.2, -6.0, 6.2], seg=18, m="glass", n="القبة الشفافة (Dome)"),
            cyl((0, -3.4, 0), 2.0, 2.2, "#14171a", "matte", n="كتلة العدسة والمستشعر"), cyl((0, -3.7, 1.1), 0.9, 0.3, "#2a4a6a", "emit", ax="z", n="العدسة"),
            cyl((3.8, -1.2, 0), 0.25, 0.2, "#ff4136", "emit", n="LED الأشعة تحت الحمراء")]

def prox_reader():
    return [box(("-W/2", "H/2-6", "-D/2"), ("W/2", "H/2+6", "-D/2+2.0"), "#2b2f35", "gloss", n="قارئ بطاقة القرب (Proximity reader)"),
            box(("-W/2+1", "H/2+2", "-D/2+2.0"), ("W/2-1", "H/2+4", "-D/2+2.1"), "#0f1215", "emit", n="نافذة المؤشر"), cyl((0, "H/2+3", "-D/2+2.1"), 0.5, 0.2, "#2ecc40", "emit", ax="z", n="LED حالة"),
            tor((0, "H/2-1", "-D/2+2.1"), 2.0, 0.15, "#8a9097", ax="z", m="metal", n="رمز RFID")]

def intercom():
    return [box(("-W/2", "H/2-10", "-D/2"), ("W/2", "H/2+10", "-D/2+3.5"), "#e9e9e5", "gloss", n="وحدة الإنتركم (فيديو) — جسم"),
            box(("-W/2+1.5", "H/2+0.5", "-D/2+3.5"), ("W/2-1.5", "H/2+8.5", "-D/2+3.7"), "#0b1a2a", "emit", n="شاشة ملوّنة"),
            rep(cyl((-3.5, "H/2-4", "-D/2+3.5"), 0.9, 0.4, "#555", "matte", ax="z", n="زر"), 3, (3.5, 0, 0)),
            box((-3, "H/2-9", "-D/2+3.5"), (3, "H/2-7.2", "-D/2+3.6"), "#222", "rubber", n="سماعة/ميكروفون")]

def dish():
    return [sph((0, 36, 0), 60, "#dfe6ec", s=[60, 12, 60], seg=24, m="gloss", n="طبق الاستقبال 1.2 م (Offset parabolic) — الصحن"),
            cyl((0, 10, 0), 4.0, 26, "#9aa1a8", "metal", r1=3.0, n="عمود التثبيت (Mast)"), cyl((0, 0, 0), 14, 2.0, "#6b7178", "metal", n="قاعدة معدنية"),
            cyl((0, 36, 0), 0.8, 36, "#222", "matte", ax="z", n="ذراع LNB"), cyl((0, 36, 36), 3.2, 8, "#c9ccd1", "gloss", ax="z", n="رأس LNB")]

def earth_pit():
    return [cyl((0, 0, 0), 15, 10, "#7a8088", "matte", n="حفرة تفتيش (Inspection pit) — PP/خرسانة"), cyl((0, 9.6, 0), 14.8, 1.0, "#3b3f45", "metal", n="غطاء حديد زهر"),
            rep(box((-9, 10.5, -0.4), (9, 10.7, 0.4), "#2a2d31", "matte", n="نقش الغطاء"), 3, (0, 0, 3.5)), cyl((0, -26, 0), 0.8, 26, "#b87333", "metal", n="قضيب التأريض النحاسي")]

def tape_clip():
    return [cyl((0, 0, 0), 1.5, 0.5, "#b87333", "metal", n="مشبك الشريط النحاسي"), box((-1.2, 0.5, -0.5), (1.2, 1.2, 0.5), "#b87333", "metal", n="شريط نحاس 25×3 مم")]

def make():
    out = {}
    def add(t): out[t[0]] = t[1]
    def S(id_, name, en, parts, place, lod=3.5, conf="derived", facts=None, asm=None, src=None, dims=None, **kw):
        add(sample(id_, name, en, "electrical", parts, place=place, lod=lod, conf=conf, src=src or [], facts=facts or [], asm=(asm or []) + [ASM_STD], dims=dims or {}, **kw))
    # ---- luminaires
    S("e_L1", "كشاف سقفي خطي 2×22 واط LED IP65", "Ceiling linear LED 2x22W IP65", lum_linear(), CEIL, lod=5, src=SRC_L, facts=[["القدرة", "2×22 واط LED"], ["الفيض", "5670 لومن"], ["الحماية", "IP65"], ["الجهد", "240V / 50Hz"]], dims={"W": 120, "D": 15, "H": 8})
    S("e_L2", "كشاف سقفي 22 واط LED IP65", "Ceiling mounted LED 22W IP65", lum_drum(26, 9, ip="IP65"), CEILC, lod=4, src=SRC_L, facts=[["القدرة", "22 واط LED"], ["الفيض", "2835 لومن"], ["الحماية", "IP65"]], asm=["القطر 26 سم: افتراض (البصمة 6×4 سم على المخطط رمز فقط)"])
    S("e_L4", "كشاف جداري/سقفي 18 واط مع مقبس حلاقة", "Mirror light 18W LED with shaver socket", lum_bathroom(), WALL, lod=4, src=SRC_L, facts=[["القدرة", "18 واط LED"], ["الحماية", "IP54"], ["ملحق", "مقبس حلاقة مدمج"]], asm=["التركيب فوق المرآة بارتفاع 2.0 م: افتراض"], dims={"W": 60, "D": 10, "H": 12})
    S("e_L5", "كشاف غاطس 60×60 بعاكس مزدوج 43 واط", "Recessed 600x600 double-parabolic louvre 43W LED", lum_recessed_louvre(), CEIL, lod=4.5, src=SRC_L, facts=[["القدرة", "43 واط LED"], ["الفيض", "4900 لومن"], ["الحماية", "IP20"], ["الغطاء", "شبكة عاكسة مزدوجة (Flexi-glass louvre)"]], dims={"W": 60, "D": 60, "H": 5})
    S("e_L6", "كشاف غاطس 60×60 بناشر منشوري 31 واط", "Recessed 600x600 prismatic 31W LED", lum_recessed_prism(), CEIL, lod=4.5, src=SRC_L, facts=[["القدرة", "31 واط LED"], ["الفيض", "3700 لومن"], ["الحماية", "IP54"], ["الغطاء", "ناشر منشوري"]], dims={"W": 60, "D": 60, "H": 5})
    S("e_L7", "كشاف سلم سقفي 19 واط LED", "Ceiling staircase fixture 19W LED", lum_drum(24, 8, ip="IP40"), CEILC, lod=4, src=SRC_L, facts=[["القدرة", "19 واط LED"], ["الفيض", "1920 لومن"], ["الحماية", "IP40"]], dims={"W": 24, "D": 24, "H": 7})
    S("e_L8", "كشاف هابط غاطس 26 واط LED", "Recessed downlight 26W LED", lum_downlight(22, opal=False), CEILC, lod=4, src=SRC_L, facts=[["القدرة", "26 واط LED"], ["الفيض", "2000 لومن"], ["الحماية", "IP54"]], dims={"W": 22, "D": 22, "H": 4})
    S("e_L9", "كشاف هابط غاطس 28 واط LED بناشر معتم", "Recessed downlight 28W LED opal diffuser", lum_downlight(22, opal=True), CEILC, lod=4, src=SRC_L, facts=[["القدرة", "28 واط LED"], ["الفيض", "3000 لومن"], ["الحماية", "IP40"], ["الغطاء", "ناشر أوبال"]], dims={"W": 22, "D": 22, "H": 4})
    S("e_L10", "كشاف منحدر 26 واط LED IP65", "Ramp light 26W LED IP65", lum_ramp(), CEIL, lod=5, src=SRC_L, facts=[["القدرة", "26 واط LED"], ["الفيض", "1200 لومن"], ["الحماية", "IP65"]], dims={"W": 36, "D": 30, "H": 10})
    S("e_L11", "كشاف جداري خارجي 2×10 واط LED", "Wall external light 2x10W LED IP65", lum_wall_ext(), WALL, lod=4.5, src=SRC_L, facts=[["القدرة", "2×10 واط LED"], ["الفيض", "936 لومن"], ["الحماية", "IP65"]], asm=["ارتفاع التركيب 2.2 م: افتراض"], dims={"W": 18, "D": 4, "H": 12})
    S("e_L12", "ثريا صغيرة (خطاف ووردة سقف ولمبة LED)", "Chandelier (small): hook, ceiling rose, LED lamp", lum_chandelier(False), CEILC, lod=4.5, src=SRC_L, asm=["طول التعليق وشكل الثريا: افتراض — المفتاح يذكر الخطاف والوردة واللمبة فقط (الثريا من توريد المالك)"], dims={"W": 37, "D": 37, "H": 30})
    S("e_L13", "ثريا كبيرة (خطاف ووردة سقف ولمبة LED)", "Chandelier (large): hook, ceiling rose, LED lamp", lum_chandelier(True), CEILC, lod=4.5, src=SRC_L, asm=["طول التعليق وشكل الثريا: افتراض — المفتاح يذكر الخطاف والوردة واللمبة فقط"], dims={"W": 44, "D": 44, "H": 35})
    # ---- sockets
    pf = [["القياس", "BS 1363 — لوحة 86 مم"]]
    S("e_P1", "مقبس 13 أمبير مفرد مع مفتاح", "13A switched socket outlet", socket_plate(1, True), WALL, src=SRC_P, facts=pf + [["التيار", "13 أمبير"]], asm=["الارتفاع 0.40 م من EP-109"], dims={"W": 9, "D": 4, "H": 9})
    S("e_P2", "مقبس 13 أمبير مزدوج مع مفتاح", "13A twin switched socket outlet", socket_plate(2, True), WALL, src=SRC_P, facts=pf + [["التيار", "13 أمبير"], ["العدد", "مقبسان"]], asm=["الارتفاع 0.40 م من EP-109"], dims={"W": 15, "D": 4, "H": 9})
    S("e_P3", "مقبس 13 أمبير بمستوى السقف", "13A switched socket (ceiling level)", socket_plate(1, True), WALL, src=SRC_P, facts=pf, asm=["ارتفاع التركيب 2.3 م: افتراض"], dims={"W": 9, "D": 4, "H": 9})
    S("e_P4", "مقبس 13 أمبير مقاوم للماء (W/P)", "13A switched socket W/P IP66", wp_box(10, 10, 6.5, "socket"), WALL, src=SRC_P, facts=[["الحماية", "IP66"], ["التيار", "13 أمبير"]], asm=["الارتفاع 0.40 م من EP-109"], dims={"W": 10, "D": 4, "H": 10})
    S("e_P5", "مقبس 15 أمبير لوحدة FCU (مفتاح DP مع نيون)", "15A FCU switched fused connection unit", socket_plate(1, True, neon=True, flex=True, amp=15), WALL, src=SRC_P, facts=[["التيار", "15 أمبير"], ["الغرض", "تغذية وحدة ملف المروحة FCU"], ["النوع", "مفتاح ثنائي القطب مع مؤشر نيون"]], asm=["الارتفاع 1.30 م من EP-109"], dims={"W": 9, "D": 4, "H": 9})
    S("e_P6", "مخرج 15 أمبير للافتات (Spur)", "15A spur outlet for sign board", socket_plate(1, False, flex=True), WALL, src=SRC_P, facts=[["التيار", "15 أمبير"]], dims={"W": 9, "D": 4, "H": 9})
    S("e_P7", "مقبس 20 أمبير مع مخرج مرن", "20A switch with flex outlet", socket_plate(1, True, neon=True, flex=True, amp=20), WALL, src=SRC_P, facts=[["التيار", "20 أمبير"]], asm=["الارتفاع 0.40 م (مخرج الطباخ المرن) من EP-109"], dims={"W": 9, "D": 4, "H": 9})
    S("e_P8", "مفتاح 20 أمبير ثنائي القطب مع مخرج مرن", "20A DP switch with flex outlet", socket_plate(1, True, neon=True, flex=True, amp=20), WALL, src=SRC_P, facts=[["التيار", "20 أمبير"], ["الغرض", "سخان مياه / جهاز ثابت"]], asm=["الارتفاع 1.30 م من EP-109"], dims={"W": 9, "D": 4, "H": 9})
    S("e_P9", "وحدة تحكم الطباخ CCU", "Cooker control unit", [_pl(8.6, 14.6, c=PLASTIC, cy="H/2")] + [_rocker(0, "H/2+3.5", 3.6, 2.4, WHITE), _neon(2.6, "H/2+3.5")] + _socket_face(0, cy="H/2-2.8") + [_rocker(0, "H/2-5.3", 2.4, 1.0, WHITE)] + _screws(8.6, 14.6), WALL,
      src=SRC_P, facts=[["الغرض", "وحدة تحكم الطباخ"], ["الارتفاع", "200 مم فوق سطح العمل"]], asm=["سطح العمل 0.90 م؛ المركز 1.10 م: افتراض"], dims={"W": 9, "D": 4, "H": 14})
    S("e_P10", "نقطة سخان مياه", "Water heater connection (20A DP + flex)", socket_plate(1, True, neon=True, flex=True, amp=20), WALL, src=SRC_P, facts=[["الغرض", "توصيل سخان مياه كهربائي"]], asm=["الارتفاع: افتراض"], dims={"W": 12, "D": 4, "H": 12})
    S("e_P12", "عازل ثلاثي الأطوار TPN (IP65)", "TPN isolator IP65", [box(("-W/2", "H/2-H/2", "-D/2"), ("W/2", "H/2+H/2", "-D/2+9"), "#d6d9dd", "gloss", n="علبة العازل IP65"),
        cyl((0, "H/2", "-D/2+9"), 3.2, 1.2, "#d9a21b", "gloss", ax="z", n="مقبض دوّار أصفر (Rotary handle)"), box((-0.8, "H/2-0.5", "-D/2+10.2"), (0.8, "H/2+3.4", "-D/2+11.3"), "#c0392b", "gloss", n="ذراع المقبض"),
        cyl((0, "H/2-H/2+0.6", "-D/2+4"), 0.8, 1.6, BLACK, "rubber", n="مدخل كابل")], WALL, src=SRC_P, facts=[["النوع", "عازل TPN"], ["الحماية", "IP65"], ["السعة", "حسب قدرة الآلة"]], asm=["الارتفاع 1.30 م من EP-109"], dims={"W": 16, "D": 4, "H": 16})
    S("e_P14", "لوحة تحكم (C.P)", "Control panel (C.P)", panel(40, 60, 18, "لوحة تحكم", screen=False, leds=3, keypad=False), WALL, lod=5, src=SRC_P, facts=[["النوع", "لوحة تحكم"]], asm=["الأبعاد من رمز المخطط؛ ارتفاع التركيب: افتراض"], dims={"W": 40, "D": 18, "H": 60})
    S("e_P15", "بنك مكثفات (CB)", "Capacitor bank (CB) — 220 kVAr", [box(("-W/2", 0, "-D/2"), ("W/2", "H", "D/2"), "#9aa5b1", "gloss", n="خزانة بنك المكثفات (Floor cabinet)"),
        box(("-W/2+2", "H*0.15", "D/2"), ("W/2-2", "H*0.88", "D/2+0.8"), "#aeb7c1", "gloss", n="باب أمامي"), rep(box(("-W/2+4", "H*0.25", "D/2+0.8"), ("W/2-4", "H*0.25+4", "D/2+1.2"), "#7a828a", "metal", n="فتحة تهوية (Louvre)"), 5, (0, 8, 0)),
        box((-4, "H*0.9", "D/2+0.8"), (4, "H*0.9+6", "D/2+1.1"), "#13202c", "emit", n="مقياس معامل القدرة (PF controller)"), cyl(("W/2-6", "H*0.5", "D/2+0.8"), 0.9, 0.9, STEEL_D, "metal", ax="z", n="قفل")],
        {"mode": "box", "anchor": "bottom"}, lod=6, src=SRC_P, facts=[["السعة", "220 كيلوفار (SLD ELEC1 ص16)"]], asm=["الأبعاد من رمز المخطط"], dims={"W": 60, "D": 30, "H": 120})
    S("e_P16", "وحدة تحكم المستهلك (CCU)", "Consumer control unit", enclosure(20, 20, 8, c="#e6e6e0", led=True, name="CCU"), WALL, src=SRC_P, asm=["ارتفاع التركيب: افتراض"], dims={"W": 20, "D": 10, "H": 20})
    S("e_P18", "لوحة توزيع فرعية رئيسية (SMDB)", "Sub main distribution board (SMDB)", panel(80, 100, 25, "SMDB", leds=4), WALL, lod=6, src=SRC_P, facts=[["العرض × الارتفاع", "80 × 100 سم"], ["أعلى اللوحة عن الأرضية", "180 سم"]], asm=["العمق 25 سم: افتراض"], dims={"W": 80, "D": 25, "H": 100})
    # ---- switches
    sf = [["التيار", "10 أمبير (20 أمبير عند أكثر من 10 نقاط إنارة)"]]
    S("e_S1", "مفتاح إنارة مفرد باتجاه واحد", "One gang one way switch", switch_plate(1), WALL, src=SRC_P, facts=sf + [["عدد المفاتيح", "1"]], asm=["الارتفاع 1.30 م من EP-109"], dims={"W": 9, "D": 4, "H": 9})
    S("e_S2", "مفتاح إنارة مزدوج باتجاه واحد", "Two gang one way switch", switch_plate(2), WALL, src=SRC_P, facts=sf + [["عدد المفاتيح", "2"]], asm=["الارتفاع 1.30 م من EP-109"], dims={"W": 13, "D": 4, "H": 9})
    S("e_S4", "مفتاح إنارة مفرد مقاوم للماء", "Water-proof one gang switch", wp_box(10, 10, 6.5, "switch"), WALL, src=SRC_P, facts=sf + [["الحماية", "IP66"]], asm=["الارتفاع 1.30 م من EP-109"], dims={"W": 10, "D": 4, "H": 9})
    S("e_S5", "مفتاح إنارة مزدوج مقاوم للماء", "Water-proof two gang switch", wp_box(10, 14, 6.5, "switch"), WALL, src=SRC_P, facts=sf + [["الحماية", "IP66"], ["عدد المفاتيح", "2"]], asm=["الارتفاع 1.30 م من EP-109"], dims={"W": 13, "D": 4, "H": 9})
    S("e_S6", "مفتاح مفرد باتجاهين", "One gang two way switch", switch_plate(1, two_way=True), WALL, src=SRC_P, facts=sf + [["الاتجاهات", "2"]], asm=["الارتفاع 1.30 م من EP-109"], dims={"W": 9, "D": 4, "H": 9})
    S("e_S8", "مفتاح ضغط للسلم مع مؤقت", "Stair case push switch with timer", [_pl(8.6, 8.6)] + _screws(8.6, 8.6) + [cyl((0, "H/2+1.4", "-D/2+0.9"), 1.5, 0.9, "#f7f7f2", "gloss", ax="z", n="زر ضغط مضاء"), cyl((0, "H/2+1.4", "-D/2+1.8"), 1.0, 0.1, "#fff3b0", "emit", ax="z", n="LED توجيه"),
        cyl((0, "H/2-2.4", "-D/2+0.9"), 1.0, 0.7, "#555", "matte", ax="z", n="ضابط المؤقت (Timer)")], WALL, src=SRC_P, asm=["الارتفاع 1.30 م من EP-109"], dims={"W": 9, "D": 4, "H": 9})
    S("e_S9", "مروحة شفط خطية (Inline)", "Inline exhaust fan", [cyl((0, 0, 0), 9, 25, "#c9ced4", "gloss", n="غلاف المروحة المعدني"), tor((0, 0.8, 0), 9.2, 0.7, "#8e949c", m="metal", n="شفة الدخول"), tor((0, 24.2, 0), 9.2, 0.7, "#8e949c", m="metal", n="شفة الخروج"),
        box((8.2, 8, -4), (14.5, 17, 4), "#3b3f45", "matte", n="علبة التوصيل الكهربائي"), cyl((0, 12, 0), 8, 0.5, "#aab0b8", "metal", n="دوّار المروحة (Impeller) — داخل الغلاف")], {"mode": "cyl", "anchor": "top"}, lod=5,
        src=["ELEC1 مفتاح الإنارة: S9", "جدول التهوية MECH1 ص29"], facts=[["النوع", "مروحة شفط خطية Inline"]], asm=["القدرة والتدفق غير مذكورين في مفتاح الإنارة؛ راجع جدول التهوية الميكانيكي", "الاتجاه: محور المروحة رأسيًا في الرسم المبسّط"], dims={"W": 19, "D": 19, "H": 25})
    S("e_S10", "جرس وزر جرس", "Bell and bell push", [_pl(8, 9)] + [cyl((0, "H/2+1.5", "-D/2+0.9"), 1.4, 0.7, "#f7f7f2", "gloss", ax="z", n="زر الجرس"), box((-2.6, "H/2-3.8", "-D/2+0.9"), (2.6, "H/2-1.6", "-D/2+1.2"), "#f0ead2", "matte", n="بطاقة الاسم"),
        cyl((0, "H/2+1.5", "-D/2+1.6"), 0.5, 0.15, "#e6892b", "emit", ax="z", n="مؤشر")], WALL, src=SRC_P, asm=["الارتفاع 1.30 م من EP-109"], dims={"W": 8, "D": 4, "H": 9})
    S("e_S11", "حساس حركة", "Motion sensor", [cyl((0, -0.8, 0), 7, 0.8, "#f4f4f0", "gloss", n="القاعدة"), sph((0, -0.8, 0), 6, "#f6f6f2", s=[5.8, -3.8, 5.8], seg=20, m="gloss", n="قبة عدسة فرينل (PIR)"),
        rep(box((-0.15, -4.5, -5), (0.15, -0.9, 5), "#d9dde2", "gloss", n="قطاعات عدسة فرينل"), 7, (0.0, 0, 0)), cyl((3.8, -1.2, 0), 0.3, 0.2, "#2ecc40", "emit", n="LED الكشف")], CEILC, lod=4, src=SRC_P, asm=["نوع الحساس وزاوية الكشف غير مذكورة"], dims={"W": 14, "D": 14, "H": 5})
    # ---- fire alarm
    ff = lambda n: [["النوع", n]]
    S("e_F1", "كاشف دخان (SD)", "Smoke detector (SD)", det_smoke(False, 10, 6), CEILC, lod=4, src=SRC_F, facts=ff("كاشف دخان نقطي ضوئي"), asm=["الطراز والعنوان (addressable) غير مذكورين"], dims={"W": 10, "D": 10, "H": 6})
    S("e_F2", "كاشف حرارة (H)", "Heat detector (H)", det_smoke(False, 10, 5, heat=True), CEILC, lod=4, src=SRC_F, facts=ff("كاشف حرارة نقطي"), asm=["الطراز ودرجة التفعيل غير مذكورين"], dims={"W": 10, "D": 10, "H": 6})
    S("e_F3", "نقطة كسر زجاج (إنذار يدوي)", "Break glass call point", callpoint(), WALL, lod=3.5, src=SRC_F, facts=ff("نقطة إنذار يدوي"), asm=["ارتفاع التركيب 1.30 م من EP-109"], dims={"W": 9, "D": 4, "H": 9})
    S("e_F4", "جرس/صفارة مع وامض", "Sounder with flasher", sounder_flasher(), WALL, lod=4, src=SRC_F, facts=ff("صفارة مع وامض"), asm=["ارتفاع التركيب 2.2 م من EP-109"], dims={"W": 14, "D": 4, "H": 10})
    S("e_F5", "كاشف دخان مع صفارة", "Smoke detector with sounder", det_smoke(True, 12, 7), CEILC, lod=4, src=SRC_F, facts=ff("كاشف دخان بصفارة مدمجة"), asm=["الطراز غير مذكور"], dims={"W": 12, "D": 12, "H": 7})
    S("e_F6", "كاشف أول أكسيد الكربون (CO)", "Carbon monoxide detector (CO)", det_smoke(False, 10, 6, co=True), CEILC, lod=4, src=SRC_F, facts=ff("كاشف CO"), asm=["موضع الكاشف على السقف: افتراض (بعض المنتجات تُركّب على الجدار)"], dims={"W": 10, "D": 10, "H": 6})
    S("e_F7", "لوحة CO", "CO panel", panel(40, 40, 15, "لوحة كواشف CO", screen=True, leds=4), WALL, lod=5, src=SRC_F, facts=ff("لوحة كواشف CO"), asm=["الأبعاد من رمز المخطط؛ الارتفاع: افتراض"], dims={"W": 40, "D": 15, "H": 40})
    S("e_F8", "لوحة التحكم بالإنذار (FACP)", "Fire alarm control panel (FACP)", panel(55, 60, 18, "FACP", screen=True, leds=4, keypad=True), WALL, lod=5, src=SRC_F, facts=ff("لوحة تحكم إنذار الحريق عنونة"), asm=["الأبعاد من رمز المخطط؛ الارتفاع: افتراض"], dims={"W": 55, "D": 18, "H": 60})
    S("e_F9", "لوحة تكرار إنذار الحريق (Repeater)", "Repeater fire alarm panel", panel(45, 50, 15, "لوحة التكرار", screen=True, leds=3), WALL, lod=5, src=SRC_F, facts=ff("لوحة تكرار"), asm=["الأبعاد من رمز المخطط؛ الارتفاع: افتراض"], dims={"W": 45, "D": 15, "H": 50})
    S("e_F11", "إنارة طوارئ LED ذاتية (غاطسة)", "Emergency light LED self-contained (recessed)", lum_emerg(14), CEILC, lod=4, src=SRC_F, facts=ff("إنارة طوارئ ذاتية البطارية — غاطسة"), asm=["الاستطاعة ومدة التشغيل غير مذكورتين"], dims={"W": 14, "D": 14, "H": 4})
    S("e_F13", "لوحة مخرج طوارئ (EXIT) LED", "Exit sign (LED) self-contained", exit_sign(), WALL, lod=5, src=SRC_F, facts=ff("لوحة مخرج LED ذاتية"), asm=["ارتفاع التركيب 2.2 م: افتراض (فوق الباب)"], dims={"W": 35, "D": 6, "H": 18})
    S("e_F15", "سماعة إخلاء جدارية", "Wall mounted evacuation speaker", wall_speaker(), WALL, lod=4, src=SRC_F, facts=ff("سماعة إخلاء صوتي جدارية"), asm=["ارتفاع التركيب 2.2 م: افتراض"], dims={"W": 16, "D": 4, "H": 16})
    S("e_F18", "مقبس هاتف (Telephone jack)", "Telephone jack", [_pl(8.6, 8.6)] + _screws(8.6, 8.6) + [box((-1.0, "H/2-0.9", "-D/2+0.9"), (1.0, "H/2+0.9", "-D/2+1.4"), "#2a2a2a", "rubber", n="مقبس RJ11"), box((-0.5, "H/2+0.9", "-D/2+0.9"), (0.5, "H/2+1.2", "-D/2+1.2"), "#d9a21b", "metal", n="ملامسات")], WALL, src=SRC_F, facts=ff("مقبس هاتف"), asm=["ارتفاع التركيب 0.40 م من EP-109"], dims={"W": 9, "D": 4, "H": 9})
    # ---- low current
    S("e_T1", "مخرج تلفزيون", "T.V outlet", rj45_plate(tv=True), WALL, src=SRC_T, facts=[["النوع", "مخرج SMATV"]], asm=["ارتفاع التركيب 0.40 م من EP-109"], dims={"W": 9, "D": 4, "H": 9})
    S("e_T2", "صندوق وصلات تلفزيون", "T.V junction box", small_box(20, 20, 8, name="صندوق وصلات SMATV"), WALL, lod=4, src=SRC_T, facts=[["النوع", "صندوق وصلات SMATV"]], asm=["ارتفاع التركيب: افتراض"], dims={"W": 20, "D": 10, "H": 20})
    S("e_T3", "مبدّل متعدد 16 مخرج (IF+1RF)", "16-way multi switcher", enclosure(40, 40, 12, c="#9aa5b1", handle=False, name="مبدّل متعدد") + [rep(cyl((-15.5, "H/2+14", "-D/2+12.6"), 0.7, 0.8, "#c9ccd1", "metal", ax="z", n="موصل F-type"), 8, (4.4, 0, 0)), rep(cyl((-15.5, "H/2+9", "-D/2+12.6"), 0.7, 0.8, "#c9ccd1", "metal", ax="z"), 8, (4.4, 0, 0)), cyl((0, "H/2-12", "-D/2+12.6"), 0.9, 0.8, "#c9ccd1", "metal", ax="z", n="مدخل RF")], WALL, lod=5, src=SRC_T, asm=["الأبعاد وارتفاع التركيب: افتراض"], dims={"W": 40, "D": 15, "H": 40})
    S("e_T4", "صحن استقبال 1.2 م (SMATV)", "1.2 m dish (SMATV)", dish(), {"mode": "cyl", "anchor": "bottom"}, lod=9, src=SRC_T, facts=[["القطر", "1.2 م"]], asm=["موضع الارتفاع على السطح: افتراض"], dims={"W": 120, "D": 120, "H": 18})
    S("e_T5", "مبدّل مفرد (Single switch)", "Single switch (SMATV)", small_box(20, 20, 8, name="مبدّل SMATV مفرد"), WALL, lod=4, src=SRC_T, asm=["الأبعاد: افتراض"], dims={"W": 20, "D": 10, "H": 20})
    S("e_T6", "وحدة إنتركم صوت/صورة", "Audio video intercom", intercom(), WALL, lod=4, src=SRC_T, facts=[["النوع", "وحدة إنتركم صوت وصورة"]], asm=["الأبعاد وارتفاع التركيب: افتراض"], dims={"W": 15, "D": 5, "H": 20})
    S("e_T7", "قارئ بطاقة قرب (Proximity)", "Proximity card reader", prox_reader(), WALL, lod=3.5, src=SRC_T, asm=["ارتفاع التركيب 1.2 م: افتراض"], dims={"W": 8, "D": 4, "H": 12})
    S("e_T10", "زر خروج", "Exit push button", [_pl(8.6, 8.6, c="#d6dade")] + _screws(8.6, 8.6) + [cyl((0, "H/2+0.2", "-D/2+0.9"), 2.1, 0.8, "#2e8b57", "gloss", ax="z", n="زر الخروج الأخضر"), box((-2.8, "H/2-3.7", "-D/2+0.9"), (2.8, "H/2-2.7", "-D/2+1.0"), "#fff", "matte", n="ملصق EXIT")], WALL, src=SRC_T, asm=["ارتفاع التركيب: افتراض"], dims={"W": 9, "D": 4, "H": 9})
    S("e_T11", "صندوق وصلات (Access control)", "Junction box (access control)", small_box(15, 15, 6, name="صندوق وصلات"), WALL, lod=4, src=SRC_T, asm=["ارتفاع التركيب: افتراض"], dims={"W": 15, "D": 4, "H": 15})
    S("e_T12", "كاميرا IP ثابتة", "Fixed IP camera", cctv_dome(), {"mode": "cyl", "anchor": "top"}, lod=5, src=SRC_T, facts=[["النوع", "كاميرا مراقبة IP ثابتة"]], asm=["الطراز والدقة غير مذكورين"], dims={"W": 14, "D": 14, "H": 12})
    S("e_T20", "لوح التوزيع الرئيسي MDF", "Main distribution frame (MDF)", panel(80, 100, 25, "لوح MDF", leds=0) + [rep(box((-30, "H/2-30", "-D/2+25.6"), (30, "H/2-27", "-D/2+26.2"), "#8d6e3f", "matte", n="صف مقاطع التوصيل (Krone)"), 8, (0, 7, 0))], WALL, lod=6, src=SRC_T, facts=[["النوع", "MDF"]], asm=["الأبعاد وارتفاع التركيب: افتراض"], dims={"W": 80, "D": 25, "H": 100})
    # ---- earthing / lightning
    S("e_G2", "مشبك شريط", "Tape clip", tape_clip(), {"mode": "cyl", "anchor": "bottom"}, lod=3, src=["ELEC2: مخطط الصواعق"], dims={"W": 3, "D": 3, "H": 3})
    S("e_G3", "حفرة تفتيش للتأريض مع قضيب", "Earth inspection pit with earth rod", earth_pit(), {"mode": "cyl", "anchor": "bottom"}, lod=5, src=["ELEC2: LP-108 تفاصيل الصواعق"], facts=[["القضيب", "16 مم² — 3 × 1.2 م كحد أدنى"]], asm=["بقية الأبعاد من لوحة التفاصيل LP-108"], dims={"W": 30, "D": 30, "H": 10})
    return out

def _r(cat_t): return [{"c": c, "t": t, "s": t} for c, t in cat_t]
RULES = [{"t": f"e_{k}", "s": f"e_{k}"} for k in ["L1","L2","L4","L5","L6","L7","L8","L9","L10","L11","L12","L13","P1","P2","P3","P4","P5","P6","P7","P8","P9","P10","P12","P14","P15","P16","P18",
          "S1","S2","S4","S5","S6","S8","S9","S10","S11","F1","F2","F3","F4","F5","F6","F7","F8","F9","F11","F13","F15","F18","T1","T2","T3","T4","T5","T6","T7","T10","T11","T12","T20","G2","G3"]]
