# -*- coding: utf-8 -*-
"""Installation-detail samples read from the detail sheets of the project (catalog entries: they show the REAL assembly of a component, not a plan symbol):
   AC-107 (MECH1 p8-10: FCU connection / mounting, duct construction, hangers, dampers, penetrations, riser clamps, insulation),
   DR-106 (MECH2 p9: floor drain, gully trap, manhole, catch basin, pump chamber, stack connection, FCU condensate trap, pipe supports, bedding),
   WS-106 (MECH2 p24: pump foundation, valve pit, water heater, booster / transfer pumps, fixtures rough-in, clevis hanger, encasement),
   FF-106 (MECH2 p16: alarm check valve, zone control valve, fire pump set, breeching inlet, sprinkler / hanger details, extinguishers),
   EP-108 / EP-109 / FA-108 (ELEC1 p17-18, ELEC2 p10: electrical rooms equipment, SMDB + meter enclosure, cable tray, down-light box).
Numbers printed on those sheets go in `facts`; anything else (colours, bolt sizes, exact arrangement) is listed under `asm` and the sample is marked 'derived'/'assumed'."""
from .lib import *

NONE = {"mode": "none"}
BLUE = "#2d8bd6"; ORANGE = "#e07b39"; INS = "#2b2e33"; CU = "#b87333"; PVC = "#e8e4d8"; SS = "#c9ced4"; GI = "#aab0b8"; CAST = "#4a4f55"; FIRE = "#c0281f"
SRC_AC = ["MECH1 ص8-9: AC-107 تفاصيل التكييف"]; SRC_DR = ["MECH2 ص9: DR-106 تفاصيل الصرف"]; SRC_WS = ["MECH2 ص24: WS-106 تفاصيل التغذية بالمياه"]; SRC_FF = ["MECH2 ص16: FF-106 تفاصيل الإطفاء"]
SRC_EP = ["ELEC1 ص17: EP-108 تفاصيل غرف الكهرباء"]; SRC_EG = ["ELEC1 ص18: EP-109 تفاصيل عامة"]
A_COL = "الألوان وقياسات البراغي والحشوات والتفاصيل الدقيقة غير مبيّنة في المستندات: قياسية لهذه الفئة"

# ---------------------------------------------------------------------------------------------------- small builders (cm, local frame: x width, y up, z depth)
def px(x0, x1, y, z, r, c, m="metal", seg=14, n=None):
    return cyl((x0, y, z), r, x1 - x0, c, m, ax="x", seg=seg, n=n)
def pz(z0, z1, x, y, r, c, m="metal", seg=14, n=None):
    return cyl((x, y, z0), r, z1 - z0, c, m, ax="z", seg=seg, n=n)
def py(y0, y1, x, z, r, c, m="metal", seg=14, n=None):
    return cyl((x, y0, z), r, y1 - y0, c, m, seg=seg, n=n)
def ball_valve(x, y, z, n="صمام عزل كروي (Ball valve)", r=2.0, c=BRASS):
    return [cyl((x - 2.5, y, z), r, 5, c, "metal", ax="x", seg=14, n=n), box((x - 0.4, y + r, z - 3.2), (x + 0.4, y + r + 1.2, z + 3.2), RED, "gloss", n="مقبض الصمام")]
def gate_valve(x, y, z, r=3.0, n="صمام بوابة (Gate valve)", c="#3a5f8f"):
    return [cyl((x - 3.5, y, z), r, 7, c, "metal", ax="x", seg=16, n=n), cyl((x, y + r - 0.5, z), r * 0.45, r * 1.3, c, "metal", seg=12, n="جسم الغطاء"), py(y + r, y + r + r * 1.6, x, z, 0.35, "#8e949c", n="ساق الصمام"),
            cyl((x, y + r + r * 1.6, z), r * 0.95, 0.6, RED, "gloss", seg=16, n="عجلة التشغيل (Handwheel)")]
def check_valve(x, y, z, r=3.0, n="صمام عدم رجوع (Non-return valve)", c="#5a6570"):
    return [cyl((x - 4, y, z), r, 8, c, "metal", ax="x", seg=16, n=n), cyl((x, y, z), r * 1.15, 2, "#8e949c", "metal", ax="x", seg=16, n="حلقة الصمام")]
def strainer(x, y, z, r=2.1, n="مصفاة Y (Strainer)"):
    return [cyl((x - 3, y, z), r, 6, GI, "metal", ax="x", seg=14, n=n), cyl((x - 1, y - 3.5, z + r * 0.9), 1.5, 4, GI, "metal", ax="y", seg=12, n="غطاء المصفاة"), cyl((x - 1, y - 4.2, z + r * 0.9), 1.0, 0.8, "#8e949c", "metal", seg=10, n="سدادة التنظيف")]
def flex_coupling(x, y, z, r=2.2, n="وصلة مرنة (Flexible connector)"):
    return [cyl((x - 3, y, z), r, 6, "#8e949c", "metal", ax="x", seg=16, n=n), cyl((x - 3, y, z), r * 1.3, 1, "#6f757c", "metal", ax="x", seg=16, n="شفة"), cyl((x + 2, y, z), r * 1.3, 1, "#6f757c", "metal", ax="x", seg=16)]
def gauge(x, y, z, n="مقياس ضغط (Pressure gauge)"):
    return [py(y, y + 3, x, z, 0.4, BRASS, n="وصلة المقياس"), cyl((x, y + 3, z), 2.2, 1.6, "#f2f2ee", "gloss", ax="z", seg=18, n=n), cyl((x, y + 3, z + 1.6), 2.0, 0.1, "#111", "matte", ax="z", seg=18, n="قرص المقياس")]
def insulated(x0, x1, y, z, r, t, n="أنبوب معزول"):
    return [px(x0, x1, y, z, r, GI, n=n), px(x0, x1, y, z, r + t, INS, "rubber", n=f"عزل مطاطي {round(t*10)} مم")]
def anchor_plate(x, y, z, w=8, n="لوح تثبيت بالبلاطة"):
    return box((x - w / 2, y, z - w / 2), (x + w / 2, y + 0.6, z + w / 2), "#8e949c", "metal", n=n)
def spring_isolator(x, y, z, h=9, r=4.5):
    P = [cyl((x, y, z), r, 0.8, "#444", "rubber", seg=16, n="قاعدة مطاطية للنابض"), cyl((x, y + h - 0.8, z), r, 0.8, "#444", "rubber", seg=16, n="غطاء علوي")]
    P += [rep(tor((x, y + 1.6, z), r - 0.9, 0.35, "#2f6fb0", m="metal", ax="y", seg=16, n="لفّات النابض (Spring isolator — انحراف 50 مم)"), 7, (0, (h - 3.2) / 6, 0))]
    return P

# ====================================================================================================== MECHANICAL (AC-107)
def fcu_pipe_connection():
    Y0 = 24.0; yy = Y0 + 20
    P = [box((-48, Y0, -19), (48, Y0 + 30, 19), "#c7ccd2", "ghost", n="وحدة FCU (غلاف مبسّط للمرجع)")]
    for z, nm in ((-6.0, "تغذية"), (6.0, "رجوع")):
        P += [px(-96, -48, yy, z, 1.1, CU, n=f"وصلة ملف FCU — {nm} (نحاس ¾″)"), px(-58, -50, yy, z, 1.5, "#8e949c", n=f"خرطوم مرن مضفّر (Flexible hose) — {nm}"),
              px(-118, -96, yy, z, 1.1, GI, n=f"{nm} من الشبكة"), px(-118, -96, yy, z, 3.6, INS, "rubber", n="عزل مطاطي 25 مم")]
    P += ball_valve(-66, yy, -6) + strainer(-74, yy, -6) + \
         [cyl((-83, yy, -6), 2.2, 5, "#9fb6c9", "metal", ax="x", seg=14, n="صمام موازنة (Balancing / circuit setter)"), box((-84, yy + 2, -7.4), (-81.5, yy + 4.3, -4.6), "#1f2226", "matte", n="مقياس الموازنة"),
          box((-91, yy - 2, -8.2), (-86.5, yy + 2.2, -3.8), BRASS, "metal", n="صمام تحكم ثنائي الاتجاه (2-way control valve)"), box((-92, yy + 2.2, -9), (-85.5, yy + 10, -3), "#2c3e50", "matte", n="مشغّل كهربائي للصمام (Actuator)")]
    P += ball_valve(-70, yy, 6, n="صمام عزل كروي — رجوع") + [cyl((-82, yy, 6), 2.0, 4, "#9fb6c9", "metal", ax="x", seg=14, n="صمام موازنة اختياري — رجوع")]
    P += [py(Y0 + 30, Y0 + 34, -40, 0, 0.9, BRASS, n="مأخذ التنفيس"), cyl((-40, Y0 + 34, 0), 1.6, 3.2, "#d9a21b", "metal", seg=14, n="مفتاح تنفيس هواء أوتوماتيكي (AAV)"),
          py(Y0 + 4, Y0 + 12, -52, 0, 0.7, BRASS, n="وصلة تصريف الملف"), cyl((-52, Y0 + 1.5, 0), 1.2, 3, BRASS, "metal", seg=12, n="صمام تصريف (Drain valve)")]
    xd, zd = 40, 12
    P += [pz(zd, zd + 6, xd, Y0 + 1.5, 1.25, PVC, "gloss", n="مخرج تكثيف من الحوض (PVC ⌀25 مم)"), py(Y0 - 20, Y0 + 1.5, xd, zd + 6, 1.25, PVC, "gloss", n="أنبوب تكثيف نازل"),
          py(Y0 - 20, Y0 - 12, xd + 7, zd + 6, 1.25, PVC, "gloss", n="الساق الثانية للمصيدة"), px(xd, xd + 7, Y0 - 20, zd + 6, 1.25, PVC, "gloss", n="قاع مصيدة U (U-trap)"),
          cyl((xd, Y0 - 8, zd + 6), 1.9, 1.6, "#c9c5b6", "gloss", seg=14, n="وصلة فكّ (Union) لتنظيف المصيدة"), cyl((xd + 7, Y0 - 8, zd + 6), 1.9, 1.6, "#c9c5b6", "gloss", seg=14, n="وصلة فكّ (Union)"),
          px(xd + 7, xd + 28, Y0 - 12, zd + 6, 1.25, PVC, "gloss", n="تصريف بميل 1:40 إلى أقرب مصرف (DR-106 تفصيل 07)")]
    return P

def fcu_hanger_mount():
    P = [box((-62, 82, -30), (62, 100, 30), "#b4b4ae", "ghost", n="بلاطة الخرسانة (Soffit)"), box((-47, 30, -19), (47, 60, 19), "#c7ccd2", "ghost", n="وحدة FCU (غلاف مبسّط)")]
    for sx in (-1, 1):
        for sz in (-1, 1):
            x, z = sx * 40, sz * 22
            P += [cyl((x, 80, z), 1.2, 3.5, "#8e949c", "metal", seg=10, n="مرساة تمدد M10 في البلاطة (Expansion anchor)"), cyl((x, 36, z), 0.5, 46, GI, "metal", seg=8, n="قضيب تعليق مسنن M10 (Threaded rod)"),
                  box((x - 3, 60, z - 2), (x + 3, 63, z + 2), "#6f757c", "metal", n="أذن التعليق على غلاف الوحدة (Hanger lug)"), cyl((x, 63, z), 2.3, 2.2, "#222", "rubber", seg=14, n="عازل مطاطي للاهتزاز (Neoprene isolator)"),
                  cyl((x, 65.2, z), 1.1, 1.0, "#8e949c", "metal", seg=6, n="صامولة مزدوجة + وردة (Double nut + washer)"), cyl((x, 58.8, z), 1.1, 1.0, "#8e949c", "metal", seg=6, n="صامولة سفلية")]
    return P

def duct_hanger_set():
    # AC-107 hanger table: duct <= 760 mm -> 25x25x3 angle @ 2.4 m ; 790-1520 -> 40x40x3 @ 1.8 m ; >= 1250 -> 50x50x6 @ 1.8 m ; rod dia 10 mm
    a = "(W<=76?2.5:(W<=152?4:5))"; t = "(W<=152?0.3:0.6)"; S = "(W<=76?240:180)"; Z0 = 40
    P = [box((f"-{S}/2-30", Z0, "-W/2"), (f"{S}/2+30", f"{Z0}+H", "W/2"), "#b9c2ca", "ghost", n="مجرى الهواء الصاج المجلفن (مبسّط)")]
    for sx in (-1, 1):
        x = f"({sx}*{S}/2)"
        P += [box((f"{x}-{a}/2", f"{Z0}-{t}", "-W/2-5"), (f"{x}+{a}/2", Z0, "W/2+5"), "#6f757c", "metal", n="عارضة تعليق زاوية (Trapeze angle) — القياس حسب جدول AC-107"),
              box((f"{x}-{a}/2", f"{Z0}-{a}", "-W/2-5"), (f"{x}-{a}/2+{t}", f"{Z0}-{t}", "W/2+5"), "#6f757c", "metal", n="الساق الرأسية للزاوية"),
              cyl((x, f"{Z0}-{t}", "-W/2-3.5"), 0.5, "H+60+" + t, GI, "metal", seg=8, n="قضيب تعليق ⌀10 مم (AC-107)"), cyl((x, f"{Z0}-{t}", "W/2+3.5"), 0.5, "H+60+" + t, GI, "metal", seg=8, n="قضيب تعليق ⌀10 مم"),
              box((f"{x}-4", f"{Z0}+H+59", "-W/2-7.5"), (f"{x}+4", f"{Z0}+H+60", "-W/2+0.5"), "#8e949c", "metal", n="لوح تثبيت بالبلاطة"), box((f"{x}-4", f"{Z0}+H+59", "W/2-0.5"), (f"{x}+4", f"{Z0}+H+60", "W/2+7.5"), "#8e949c", "metal")]
    P += [box((f"-{S}/2-30", f"{Z0}+H+60", "-W/2-12"), (f"{S}/2+30", f"{Z0}+H+80", "W/2+12"), "#b4b4ae", "ghost", n="البلاطة (Soffit)")]
    return P

def duct_access_door():
    # AC D-37: hinged access door on a duct: frame, insulated panel, gasket, 2 hinges, 2 cam latches
    P = [box((-30, 0, -3), (30, 40, 0), "#b9c2ca", "ghost", n="جدار المجرى (مبسّط)"),
         box((-14, 4, 0), (14, 4.6, 1.2), "#8e949c", "metal", n="إطار الفتحة (Frame)"), box((-14, 28.4, 0), (14, 29, 1.2), "#8e949c", "metal"), box((-14, 4, 0), (-13.4, 29, 1.2), "#8e949c", "metal"), box((13.4, 4, 0), (14, 29, 1.2), "#8e949c", "metal"),
         box((-13.4, 4.6, 0.4), (13.4, 28.4, 2.4), "#d9d6cb", "matte", n="لوح الباب معزول (Insulated door panel)"), box((-13.4, 4.6, 0.2), (13.4, 28.4, 0.4), "#222", "rubber", n="جوان إحكام (Gasket)")]
    for y in (10, 23):
        P += [box((-13.6, y - 1.5, 0.2), (-11.6, y + 1.5, 2.8), "#6f757c", "metal", n="مفصلة (Hinge)"), cyl((12.0, y, 2.4), 1.1, 1.0, "#c9ced4", "metal", ax="z", seg=12, n="قفل كامة (Cam latch)"),
              box((11.2, y - 0.3, 3.2), (12.8, y + 0.3, 3.8), "#222", "metal", n="مقبض القفل")]
    return P

def vaned_elbow():
    # AC D-28: square elbow W x H with turning vanes at 45 degrees (spacing assumed)
    P = [box(("-W/2-W", 0, "-W/2"), ("-W/2", "H", "W/2"), "#b9c2ca", "ghost", n="الذراع الأول للكوع"), box(("-W/2", 0, "-W/2"), ("W/2", "H", "W/2"), "#b9c2ca", "ghost", n="منطقة الدوران"),
         box(("-W/2", 0, "W/2"), ("W/2", "H", "W/2+W"), "#b9c2ca", "ghost", n="الذراع الثاني للكوع")]
    for k in range(1, 6):
        d = f"(W*{k}/6)"; L = f"((W-{d})*1.4142)"
        P.append(dict(box((f"-{d}/2-{L}/2", 0.5, f"{d}/2-0.3"), (f"-{d}/2+{L}/2", "H-0.5", f"{d}/2+0.3"), "#aab0b8", "metal", n="ريشة توجيه الهواء (Turning vane) 45°"), rot=[0, -45, 0]))
    P += [box(("-W/2-W-2", -2, "-W/2-3"), ("-W/2-W+0.6", "H+2", "W/2+3"), "#8e949c", "metal", n="شفة وصل — بداية الكوع"), box(("-W/2-3", -2, "W/2+W-0.6"), ("W/2+3", "H+2", "W/2+W+2"), "#8e949c", "metal", n="شفة وصل — نهاية الكوع")]
    return P

def fd_drop_curtain():
    # AC D-25: drop-curtain fire damper in a duct sleeve: curtain blades stacked in the head, fusible link, retaining angles, mounting frame
    P = [box(("-W/2-4", -4, "-6"), ("W/2+4", "H+10", "6"), "#8e949c", "ghost", n="غلاف المخمد (Galvanised sleeve) — يُثبّت في فتحة الجدار/البلاطة")]
    P += [box(("-W/2", 0, "-4"), ("W/2", 1.5, "4"), GI, "metal", n="إطار سفلي"), box(("-W/2", "H-1.5", "-4"), ("W/2", "H", "4"), GI, "metal", n="إطار علوي"),
          box(("-W/2", 0, "-4"), ("-W/2+1.5", "H", "4"), GI, "metal", n="جانب الإطار"), box(("W/2-1.5", 0, "-4"), ("W/2", "H", "4"), GI, "metal"),
          box(("-W/2+1.5", "H-9", "-3.2"), ("W/2-1.5", "H-1.5", "3.2"), "#6f757c", "metal", n="صندوق الستارة المطوية (Curtain head)")]
    P += [rep(box(("-W/2+1.5", "H-9-0", "-0.8"), ("W/2-1.5", "H-9+0.9", "0.8"), "#d0d4d9", "metal", n="شرائح الستارة (Curtain blades) في وضع الفتح"), "min(6,max(2,floor((H-12)/7)))", (0, "-7", 0))]
    P += [cyl((0, "H-10", 0), 0.4, 5, "#f5c518", "metal", ax="z", seg=8, n="رابط منصهر (Fusible link) — 72°م"), box((-3, "H-11.5", 4), (3, "H-8.5", 4.6), "#d9d34a", "matte", n="ملصق: FD")]
    for z0, z1 in (("6", "6.8"), ("-6.8", "-6")):
        P += [box(("-W/2-4", -4, z0), ("W/2+4", -2.5, z1), "#8e949c", "metal", n="زاوية تثبيت للجدار (Retaining angle) — إطار"), box(("-W/2-4", "H+8.5", z0), ("W/2+4", "H+10", z1), "#8e949c", "metal"),
              box(("-W/2-4", -4, z0), ("-W/2-2.5", "H+10", z1), "#8e949c", "metal"), box(("W/2+2.5", -4, z0), ("W/2+4", "H+10", z1), "#8e949c", "metal")]
    return P

def duct_smoke_detector():
    # AC D-21: duct smoke detector — housing on the duct wall, sampling and return tubes projecting >= 32 mm into the air stream, access door
    P = [box((-35, 0, -2), (35, 40, 0), "#b9c2ca", "ghost", n="جدار المجرى (مبسّط)"), box((-15, 8, 0), (15, 32, 12), "#e8e8e4", "gloss", n="جسم كاشف الدخان للمجرى (Duct smoke detector housing)"),
         box((-13, 10, 12), (13, 30, 12.6), "#d8d8d4", "matte", n="غطاء شفاف مع مؤشرات"), cyl((-6, 26, 12.6), 0.8, 0.3, "#d63a2a", "emit", ax="z", seg=10, n="مؤشر إنذار LED أحمر"), cyl((6, 26, 12.6), 0.8, 0.3, "#2ecc40", "emit", ax="z", seg=10, n="مؤشر تشغيل LED أخضر"),
         box((-17, 6, 0), (17, 8, 1), "#8e949c", "metal", n="لوح التثبيت بالمجرى"), cyl((-8, 10, -3), 0.9, 30, "#c9ced4", "metal", ax="z", seg=10, n="أنبوب أخذ العيّنة (Sampling tube) — يمتد ≥32 مم في تيار الهواء"),
         cyl((8, 10, -3), 0.9, 30, "#c9ced4", "metal", ax="z", seg=10, n="أنبوب الإرجاع (Exhaust tube)"), box((-10, 34, 0), (10, 38, 3), "#d9d6cb", "matte", n="باب وصول للتنظيف (Access door) 300 مم")]
    return P

def roof_duct_penetration():
    # AC-107: duct through the roof slab — solid block upstand, concrete capping stone with 0.5 m projection and drip groove, mastic sealant, water-tested
    P = [box((-80, 0, -60), (80, 20, 60), "#b4b4ae", "ghost", n="بلاطة السطح (Roof slab)"), box((-45, 20, -45), (45, 70, 45), "#c9c2b0", "matte", n="كتلة بلوك مصمتة (Solid blockwork) حول الفتحة"),
         box((-31, -30, -21), (31, 130, 21), "#b9c2ca", "metal", n="مجرى الهواء الصاج المجلفن (يخترق السطح)"), box((-57, 70, -57), (57, 78, 57), "#d9d4c4", "gloss", n="غطاء حجر خرساني (Concrete capping stone) بنتوء 0.5 م"),
         box((-57, 70, -57), (57, 71.2, -55), "#7a756a", "matte", n="أخدود تنقيط (Drip groove)"), box((-33, 78, -23), (33, 80, 23), "#222", "matte", n="مستكي/مانع تسرّب (Mastic sealant)"),
         box((-33, 128, -23), (33, 130, 23), "#8e949c", "metal", n="شفة زاوية في أعلى المجرى (Angle flange)"), box((-85, 20, -65), (85, 21.2, 65), "#1c1c1c", "matte", n="عزل مائي أسفلتي ليفي (Fibrated asphalt) يُدار حول الكتلة")]
    return P

def pipe_sleeve_penetration():
    # AC-107: pipe through a wall/floor: 20 gauge sheet-metal sleeve, 25 mm gap packed with fibrous packing, firestop 120 mils, metal escutcheon each side
    P = [box((-40, 0, -9), (40, 80, 9), "#b4b4ae", "ghost", n="جدار/بلاطة خرسانية أو بلوك"), cyl((0, 40, -12), 5.6, 24, "#aab0b8", "metal", ax="z", seg=24, n="كم معدني بسماكة 20 gauge (Sheet-metal sleeve)"),
         cyl((0, 40, -9), 4.6, 18, "#d9d4a8", "matte", ax="z", seg=24, n="حشو ليفي غير قابل للاشتعال (Fibrous packing) — فراغ 25 مم"), cyl((0, 40, -16), 3.1, 32, "#7a828a", "metal", ax="z", seg=20, n="الأنبوب (Pipe)"),
         cyl((0, 40, -9.2), 6.3, 0.2, "#c0281f", "matte", ax="z", seg=24, n="مادة سدّ حريق (Firestop) — 120 mils"), cyl((0, 40, 9), 6.3, 0.2, "#c0281f", "matte", ax="z", seg=24),
         cyl((0, 40, -9.8), 6.5, 0.6, "#c9ced4", "metal", ax="z", seg=24, n="غطاء معدني (Escutcheon)"), cyl((0, 40, 9.2), 6.5, 0.6, "#c9ced4", "metal", ax="z", seg=24)]
    return P

def riser_clamp():
    # AC-107 riser clamp (bolted two-part clamp welded to a pipe lug, resting on a steel beam). Schedule: clamp 50x6 / 40x6 / 32x6 / 32x5, bolt dia 10-15 (pipe 12-25 / 32-75 / 125-150 / 200-250)
    P = [box((-30, 0, -8), (30, 6, 8), "#6f757c", "metal", n="كمرة فولاذية (Steel beam) تحمل المشبك"), cyl((0, 6, 0), 3.8, 60, "#7a828a", "metal", seg=20, n="أنبوب الرايزر (Riser pipe)"),
         box((-6.5, 6.4, -1.5), (6.5, 10.4, 1.5), "#8e949c", "metal", n="مشبك رايزر — نصف أول (Riser clamp 50×6)"), box((-6.5, 6.4, -9), (6.5, 10.4, -6), "#8e949c", "metal", n="مشبك رايزر — نصف ثانٍ"),
         cyl((-5, 6.2, -4.3), 0.6, 6, "#c9ced4", "metal", seg=8, n="برغي المشبك (Bolt Ø10–15)"), cyl((5, 6.2, -4.3), 0.6, 6, "#c9ced4", "metal", seg=8, n="برغي المشبك"),
         box((-6.5, 6, -3), (6.5, 6.4, 3), "#5a636c", "metal", n="لحام مستمر 3 مم (Continuous weld)")]
    return P

def pipe_insulation_pair():
    # AC-107 insulation details: indoor (conditioned space: 25 mm) and outdoor / exposed (50 mm + aluminium jacket) — fibre-glass, k <= 0.032 W/mK (WS-106 note 7)
    P = [px(0, 100, 7, -12, 2.2, GI, n="أنبوب مياه (داخل الحيز المكيّف)"), px(0, 100, 7, -12, 2.2 + 2.5, "#dfd9b8", "matte", n="عزل ألياف زجاجية 25 مم (k ≤ 0.032 واط/م·°م)"), px(0, 100, 7, -12, 4.75, "#f2f2ee", "matte", seg=18, n="غلاف PVC/قصدير للعزل (Jacket)")]
    P += [px(0, 100, 7, 12, 2.2, GI, n="أنبوب مياه (خارجي/مكشوف)"), px(0, 100, 7, 12, 2.2 + 5.0, "#dfd9b8", "matte", n="عزل ألياف زجاجية 50 مم — الأماكن المكشوفة"), px(0, 100, 7, 12, 7.3, "#b9bec4", "metal", seg=18, n="غلاف ألمنيوم مضلّع (Aluminium cladding) للعزل الخارجي")]
    P += [rep(px(14, 15, 7, 12, 7.7, "#8e949c", "metal", seg=18, n="سير تثبيت الغلاف (Band strap)"), 4, (24, 0, 0)), rep(px(14, 15, 7, -12, 5.1, "#8e949c", "metal", seg=18, n="سير ربط العزل"), 4, (24, 0, 0))]
    return P

def aav():
    # automatic air vent (AC-107 detail) with an isolating valve below
    return [cyl((0, 0, 0), 1.3, 3, BRASS, "metal", seg=14, n="وصلة ⅜″ للشبكة"), cyl((0, 3, 0), 1.9, 2.5, BRASS, "metal", seg=14, n="صمام عزل صغير (Isolating valve)"), box((-0.3, 3.4, -3), (0.3, 4.4, 3), RED, "gloss", n="مقبض الصمام"),
            cyl((0, 5.5, 0), 2.6, 7, "#d9a21b", "metal", seg=18, n="جسم مفتاح التنفيس الأوتوماتيكي (Float-type AAV)"), cyl((0, 12.5, 0), 1.4, 2, "#8e949c", "metal", seg=12, n="غطاء التنفيس"), cyl((0, 14.5, 0), 0.5, 1.2, "#555", "metal", seg=8, n="فوهة الهواء"),
            pz(0, 8, 0, 2, 0.5, "#b87333", n="أنبوب تصريف للمصرف (اختياري)")]

def pump_foundation():
    # WS-106: housekeeping pad (10 cm above the slab; notes: pump sets on a concrete base min 30 cm high), inertia base, spring isolators (50 mm deflection)
    P = [box((-90, -15, -50), (90, 0, 50), "#b4b4ae", "ghost", n="بلاطة الأرضية (Slab)"), box((-85, 0, -45), (85, 10, 45), "#bdbab2", "matte", n="قاعدة خرسانية (Housekeeping pad) 10 سم"),
         box((-75, 19, -35), (75, 30, 35), "#8e949c", "metal", n="قاعدة القصور الذاتي الفولاذية (Inertia base) مملوءة بالخرسانة"), box((-70, 30, -30), (70, 31, 30), "#bdbab2", "matte", n="خرسانة داخل الإطار")]
    for sx in (-1, 1):
        for sz in (-1, 1):
            P += spring_isolator(sx * 62, 10, sz * 26, 9, 4.5)
    P += [box((-65, 31, -25), (65, 33, 25), "#3a5f8f", "metal", n="لوح قاعدة المضخة (Pump base plate)")]
    for sx in (-1, 1):
        for sz in (-1, 1): P.append(cyl((sx * 56, 33, sz * 20), 0.9, 2.2, "#c9ced4", "metal", seg=6, n="برغي تثبيت المضخة"))
    return P

def pump_piping_connection():
    # AC-107 typical pump & piping connection: suction (IV, strainer, flexible connector) -> split-case pump + motor on base -> discharge (flexible connector, check valve, IV), pressure gauges both sides
    Y = 42
    P = [box((-95, 0, -34), (95, 10, 34), "#bdbab2", "matte", n="قاعدة خرسانية للمضخة (Housekeeping pad)"), box((-65, 10, -22), (65, 15, 22), "#3a5f8f", "metal", n="لوح القاعدة (Base plate)")]
    P += [cyl((-20, 26, 0), 15, 40, "#2f6fb0", "gloss", ax="x", seg=28, n="هيكل المضخة Split-case (Volute casing)"), box((-34, 15, -9), (-6, 26, 9), "#2f6fb0", "metal", n="قاعدة الهيكل"), cyl((-20, 26, 0), 5, 54, "#8e949c", "metal", ax="x", seg=14, n="عمود التدوير + الوصلة (Coupling)"),
          cyl((18, 26, 0), 13, 46, "#2c4a73", "gloss", ax="x", seg=28, n="محرك كهربائي (Electric motor) 1450 د/د"), box((22, 36, -6), (36, 44, 6), "#2c4a73", "metal", n="صندوق توصيل المحرك")]
    # suction on the -x side (below), discharge on top: horizontal headers along z
    P += [pz(-60, -4, -20, 26, 4.2, GI, n="خط الشفط (Suction) ⌀ 8 سم"), pz(4, 60, -20, 42, 3.4, GI, n="خط الطرد (Discharge)"), py(26, 42, -20, 0, 3.4, GI, n="رفع الطرد")]
    P += [cyl((-20, 26, -52), 4.8, 6, "#3a5f8f", "metal", ax="z", seg=18, n="صمام عزل (Isolating valve) — الشفط"), cyl((-20, 31.5, -52), 2.0, 5, "#3a5f8f", "metal", seg=12, n="غطاء الصمام"), cyl((-20, 36.5, -52), 3.2, 0.6, RED, "gloss", seg=16, n="عجلة التشغيل"),
          cyl((-20, 26, -40), 4.8, 8, GI, "metal", ax="z", seg=18, n="مصفاة (Strainer)"), cyl((-20, 26, -30), 5.4, 6, "#8e949c", "metal", ax="z", seg=18, n="وصلة مرنة (Flexible connector) — الشفط"),
          cyl((-20, 42, 14), 5.4, 6, "#8e949c", "metal", ax="z", seg=18, n="وصلة مرنة — الطرد"), cyl((-20, 42, 26), 4.8, 8, "#5a6570", "metal", ax="z", seg=18, n="صمام عدم رجوع (Non-return valve)"),
          cyl((-20, 42, 44), 4.8, 6, "#3a5f8f", "metal", ax="z", seg=18, n="صمام عزل (IV) — الطرد"), cyl((-20, 47, 44), 2.0, 5, "#3a5f8f", "metal", seg=12), cyl((-20, 52, 44), 3.2, 0.6, RED, "gloss", seg=16, n="عجلة التشغيل")]
    P += gauge(-26, 29.5, -8, "مقياس ضغط — الشفط") + gauge(-26, 45, 8, "مقياس ضغط — الطرد")
    return P

# ====================================================================================================== PLUMBING (WS-106 / DR-106)
def clevis_hanger():
    # WS-106 "typical adjustable clevis hanger": threaded rod from the slab, nut, clevis (U-strap with bolt), pipe
    return [box((-8, 62, -8), (8, 64, 8), "#8e949c", "metal", n="لوح تثبيت بالبلاطة (Anchor plate)"), py(20, 62, 0, 0, 0.5, GI, n="قضيب تعليق مسنن (Threaded rod)"), cyl((0, 40, 0), 1.1, 1.0, "#8e949c", "metal", seg=6, n="صامولة ضبط الارتفاع (Adjusting nut)"),
            box((-1.6, 18, -0.8), (1.6, 21.4, 0.8), "#6f757c", "metal", n="رأس المشبك (Clevis cross-piece)"), tor((0, 11, 0), 5.2, 0.45, "#6f757c", m="metal", ax="z", seg=24, n="حزام المشبك (Clevis strap)"),
            cyl((0, 11, 0), 4.2, 20, "#3a86d9", "gloss", ax="z", seg=24, n="الأنبوب (Pipe)"), cyl((-5.7, 18.5, 0), 0.5, 1.8, "#c9ced4", "metal", ax="x", seg=8, n="برغي المشبك"), cyl((5.7, 18.5, 0), 0.5, 1.8, "#c9ced4", "metal", ax="x", seg=8)]

def pipe_encasement():
    # WS-106: concrete encasement of uPVC pipes — 20 cm of concrete all round (cover = pipe dia on each side as drawn: "20 | PIPE Ø | 20")
    P = [box((-30, 0, -22), (30, 40, 22), "#b4b4ae", "ghost", n="كتلة الخرسانة الحامية (Concrete surround) — 20 سم على كل جانب"), cyl((0, 20, -30), 6.3, 60, "#e8e4d8", "gloss", ax="z", seg=24, n="أنبوب uPVC (داخل كم)"),
         cyl((0, 20, -10), 8.5, 22, "#aab0b8", "metal", ax="z", seg=24, n="كم uPVC عند اختراق الجدار (UPVC pipe sleeve)")]
    return P

def valve_pit():
    # WS-106 valve pit: 60x60 cm clear chamber, concrete walls, cover 40x60 medium duty single seal CI, 50 cm deep, incoming CWS main with isolating valve + strainer + sampling point, soak-away for draining
    P = [box((-50, -15, -50), (50, 0, 50), "#b4b4ae", "ghost", n="قاعدة خرسانية + طبقة حصى للتصريف (Soak-away)"), box((-50, 0, -50), (-30, 90, 50), "#c9c2b0", "ghost", n="جدار الغرفة (Concrete wall)"), box((30, 0, -50), (50, 90, 50), "#c9c2b0", "ghost"),
         box((-30, 0, -50), (30, 90, -30), "#c9c2b0", "ghost"), box((-30, 0, 30), (30, 90, 50), "#c9c2b0", "ghost"),
         box((-50, 90, -50), (50, 100, 50), "#bdbab2", "matte", n="بلاطة السقف (Cover slab)"), box((-20, 100, -30), (20, 101.5, 30), "#3a3f45", "metal", n="غطاء حديد زهر 40×60 سم — ثقيل (Single seal)"),
         box((-18, 101.5, -28), (18, 102, 28), "#2c3036", "metal", n="إطار + نقش الغطاء")]
    P += [px(-70, 70, 30, 0, 3.0, "#3a86d9", n="خط التغذية الداخل CWS (مدفون)")] + gate_valve(-14, 30, 0, 3.0, n="صمام عزل (IV)") + strainer(14, 30, 0, 3.0, n="مصفاة (Strainer)") + \
         [py(30, 52, 24, 0, 0.7, BRASS, n="نقطة أخذ عيّنة المياه (Water sampling point)"), cyl((24, 52, 0), 1.2, 2, BRASS, "metal", seg=10, n="صنبور العيّنة"), cyl((-14, 12, 14), 1.4, 1.5, "#8e949c", "metal", seg=10, n="كم uPVC عند الجدار (PVC sleeve)")]
    return P

def water_heater_install():
    # WS-106 installation detail of the water heater (side + rear views): wall bracket / L-clamp, concealed angle valve below the false ceiling, safety valve to the nearest drain
    P = [box((-60, 0, -12), (60, 120, -10), "#c9c2b0", "matte", n="الجدار (Wall)"), cyl((0, 80, 5), 21, 50, "#f2f2ee", "gloss", ax="x", seg=32, n="سخان المياه (Water heater) — خزان أفقي"),
         box((-12, 62, -10), (-10, 98, 0), "#8e949c", "metal", n="مشبك L جداري (L-clamp)"), box((10, 62, -10), (12, 98, 0), "#8e949c", "metal"), box((-12, 98, -10), (-10, 100, 6), "#8e949c", "metal", n="ذراع حامل"), box((10, 98, -10), (12, 100, 6), "#8e949c", "metal"),
         box((-60, 130, -12), (60, 135, 12), "#e8e6df", "matte", n="السقف المستعار (False ceiling)")]
    P += [py(100, 128, -20, -4, 0.8, BRASS, n="مدخل الماء البارد (Cold feed)"), py(100, 128, 20, -4, 0.8, BRASS, n="مخرج الماء الساخن (Hot outlet)"),
          cyl((-20, 118, -4), 1.5, 3, BRASS, "metal", ax="x", seg=12, n="صمام زاوية مخفي (Concealed angle valve) تحت السقف المستعار"), cyl((20, 118, -4), 1.5, 3, BRASS, "metal", ax="x", seg=12),
          py(52, 62, 24, 8, 0.9, BRASS, n="مخرج صمام الأمان"), cyl((24, 52, 8), 1.6, 4, "#d9a21b", "metal", seg=12, n="صمام أمان (Safety valve) — يصرف إلى أقرب نقطة تصريف"), py(12, 52, 24, 8, 0.8, PVC, "gloss", n="أنبوب تصريف صمام الأمان"),
          px(24, 52, 12, 8, 0.8, PVC, "gloss", n="إلى أقرب نقطة تصريف (To nearest drain point)")]
    return P

def booster_pump_set():
    # WS-106 booster pumps connection: two pumps (duty/standby), each IV - NRV - FC - pump - FC - strainer - IV, common bypass, pressure vessel PV, pressure switches PS + gauges PG, control panel
    P = [box((-110, 0, -50), (110, 12, 50), "#bdbab2", "matte", n="قاعدة خرسانية (Housekeeping pad) ≥ 30 سم حسب الملاحظة 11")]
    for z, tag in ((-26, "A"), (26, "B")):
        P += [cyl((-30, 26, z), 11, 36, "#2f6fb0", "gloss", ax="x", seg=24, n=f"مضخة رفع {tag} (Booster pump)"), cyl((18, 26, z), 10, 34, "#2c4a73", "gloss", ax="x", seg=24, n=f"محرك المضخة {tag}"), box((-48, 12, z - 9), (36, 17, z + 9), "#3a5f8f", "metal", n="لوح القاعدة"),
              px(-90, -48, 26, z, 3.2, "#3a86d9", n="خط الشفط (من الخزان المرشّح)"), px(-48, -42, 26, z, 3.2, "#3a86d9"), px(-60, -54, 26, z, 4.2, "#8e949c", n="وصلة مرنة (FC)"), px(-78, -70, 26, z, 3.7, "#3a5f8f", n="صمام عزل (IV)"),
              px(-20, 60, 52, z, 3.0, "#3a86d9", n="خط الطرد"), py(26, 52, -20, z, 3.0, "#3a86d9", n="رفع الطرد"), px(-14, -8, 52, z, 4.0, "#5a6570", n="صمام عدم رجوع (NRV)"), px(2, 8, 52, z, 4.0, "#3a5f8f", n="صمام عزل (IV)"), px(-28, -22, 52, z, 4.2, "#8e949c", n="وصلة مرنة (FC)")]
    P += [pz(-26, 26, 60, 52, 3.4, "#3a86d9", n="مجمّع الطرد (Header) إلى الشبكة"), pz(-26, 26, -90, 26, 3.4, "#3a86d9", n="مجمّع الشفط (Header) من الخزان"), px(30, 60, 30, 0, 1.6, "#3a86d9", n="خط المجاز (Bypass pipe)")]
    P += [cyl((78, 0, 30), 14, 70, "#2a6fb5", "gloss", seg=24, n="وعاء الضغط (Pressure vessel — PV)"), cyl((78, 70, 30), 14, 0.1, "#2a6fb5", "gloss", seg=24)] + gauge(60, 55, 10, "مقياس ضغط (PG)") + \
         [box((-8, 62, -3), (6, 70, 3), "#2c3e50", "matte", n="مفتاح ضغط (Pressure switch — PS)"), box((-120, 20, 30), (-100, 70, 44), "#8e949c", "metal", n="لوحة التحكم (Control panel) بخزانة ألمنيوم"), cyl((-110, 62, 44.4), 1.2, 0.4, "#2ecc40", "emit", ax="z", seg=8, n="مؤشر تشغيل")]
    return P

def transfer_pump_set():
    # WS-106 transfer pump connection: suction header + IV + strainer (ST) + FC -> end-suction pump on base -> FC + NRV + IV -> discharge header; PG, PS; float switch control panel
    P = [box((-80, 0, -30), (90, 10, 30), "#bdbab2", "matte", n="قاعدة خرسانية"), box((-40, 10, -16), (60, 15, 16), "#3a5f8f", "metal", n="لوح القاعدة")]
    P += [cyl((-10, 26, 0), 12, 30, "#2f6fb0", "gloss", ax="x", seg=24, n="مضخة نقل (Transfer pump)"), cyl((34, 26, 0), 11, 36, "#2c4a73", "gloss", ax="x", seg=24, n="محرك كهربائي"), box((-30, 15, -8), (-4, 26, 8), "#2f6fb0", "metal", n="قاعدة المضخة"),
          px(-80, -30, 26, 0, 3.4, "#3a86d9", n="مجمّع الشفط (Suction header)"), px(-70, -64, 26, 0, 4.4, "#3a5f8f", n="صمام عزل (IV)")] + strainer(-52, 26, 0, 3.6, n="مصفاة (ST)") + [px(-42, -36, 26, 0, 4.6, "#8e949c", n="وصلة مرنة (FC)"),
          py(26, 70, -10, 0, 3.0, "#3a86d9", n="رفع الطرد"), py(70, 76, -10, 0, 3.0, "#3a86d9")]
    P += [cyl((-10, 34, 0), 4.2, 6, "#8e949c", "metal", seg=14, n="وصلة مرنة (FC)"), cyl((-10, 44, 0), 4.0, 8, "#5a6570", "metal", seg=14, n="صمام عدم رجوع (NRV)"), cyl((-10, 58, 0), 4.2, 6, "#3a5f8f", "metal", seg=14, n="صمام عزل (IV)"), px(-10, 60, 76, 0, 3.0, "#3a86d9", n="مجمّع الطرد (Discharge header)")]
    P += gauge(-26, 29, -6, "مقياس ضغط (PG)") + [box((60, 20, 12), (74, 46, 22), "#8e949c", "metal", n="لوحة تحكم (Control panel) — من مفتاح العوامة الكهربائي"), box((-6, 60, 4), (4, 66, 9), "#2c3e50", "matte", n="مفتاح ضغط (PS)")]
    return P

def wash_basin():
    # WS-106 wash basin rough-in: rim 85 cm, supply stub-outs at +60 cm A.F.F.L. spaced 10 cm each side of centre (100|100), angle valves, bottle trap
    P = [box((-30, 0, -20), (30, 1.5, 20), "#c9c2b0", "ghost", n="الأرضية (F.F.L.)"), box((-30, 0, -22), (30, 150, -20), "#c9c2b0", "ghost", n="الجدار")]
    P += [box((-28, 80, -20), (28, 85, 14), "#f5f5f2", "gloss", n="حوض الغسيل (Wash basin) — حافة عند 85 سم"), box((-26, 74, -18), (26, 80, 12), "#ececea", "gloss", n="قاع الحوض"), cyl((0, 82, -2), 2.2, 3.5, "#c9ced4", "metal", seg=14, n="مصرف الحوض"),
          cyl((0, 85, -17), 1.4, 12, "#c9ced4", "metal", seg=14, n="خلّاط الحوض (Mixer)"), box((-1, 97, -17), (1, 98.4, -6), "#c9ced4", "metal", n="ذراع الخلّاط")]
    for sx, nm in ((-10, "ماء ساخن"), (10, "ماء بارد")):
        P += [pz(-20, -12, sx, 60, 0.7, CU, n=f"مخرج {nm} عند +60 سم"), cyl((sx, 60, -12.5), 1.4, 3, BRASS, "metal", ax="z", seg=12, n="صمام زاوية (Angle valve)"), py(60, 78, sx, -9, 0.45, "#c9ced4", n="خرطوم مرن (Flexible tap connector)")]
    P += [py(48, 74, 0, -2, 1.6, "#c9ced4", n="مصيدة زجاجة (Bottle trap)"), cyl((0, 44, -2), 3.4, 6, "#c9ced4", "metal", seg=18, n="جسم المصيدة"), pz(-20, -2, 0, 47, 1.8, PVC, "gloss", n="خط تصريف 50 مم إلى الجدار")]
    return P

def water_closet():
    # WS-106 water closet rough-in: close-coupled cistern, angle valve with flexible hose at 15 cm above the floor (as dimensioned 150), floor-outlet pan 110 mm
    P = [box((-30, 0, -28), (30, 1.5, 28), "#c9c2b0", "ghost", n="الأرضية"), box((-30, 0, -30), (30, 120, -28), "#c9c2b0", "ghost", n="الجدار")]
    P += [box((-18, 1.5, -27), (18, 40, 24), "#f5f5f2", "gloss", n="قاعدة المرحاض (WC pan)"), box((-18.5, 40, -27), (18.5, 42, -4), "#f5f5f2", "gloss", n="حافة"), box((-19, 42, -4), (19, 44, 24), "#e8e8e4", "gloss", n="مقعد المرحاض (Seat)"),
          box((-19, 40, -27), (19, 80, -17), "#f5f5f2", "gloss", n="خزان الطرد (Cistern) 38 سم"), box((-17, 80, -26), (17, 81.5, -18), "#f5f5f2", "gloss", n="غطاء الخزان"), cyl((0, 81.5, -22), 2.5, 1.2, "#c9ced4", "metal", seg=16, n="زر الطرد المزدوج")]
    P += [py(1.5, 15, 10, -28, 0.7, CU, n="مخرج الماء البارد عند 15 سم"), cyl((10, 15, -28.3), 1.4, 3, BRASS, "metal", ax="z", seg=12, n="صمام زاوية (Angle valve)"), py(15, 46, 10, -25, 0.4, "#c9ced4", n="خرطوم مرن (Flexible hose) إلى الخزان"),
          cyl((0, 1.5, 0), 5.5, 0.2, "#7a756a", "matte", seg=24, n="مخرج الأرضية 110 مم (Floor outlet)"), pz(-4, 8, 0, 8, 5.5, PVC, "gloss", seg=18, n="وصلة التصريف uPVC 110 مم")]
    return P

def bathtub():
    # WS-106 bath tub: rim height and mixer rough-in (70 / 0.53 as dimensioned) — fixed accessories assumed
    P = [box((-80, 0, -40), (80, 1.5, 40), "#c9c2b0", "ghost", n="الأرضية"), box((-80, 0, -42), (80, 150, -40), "#c9c2b0", "ghost", n="جدار الخلّاط"),
         box((-76, 10, -38), (76, 55, 38), "#f5f5f2", "gloss", n="حوض الاستحمام (Bath tub) — الحافة 55 سم"), box((-70, 18, -32), (70, 55.2, 32), "#e9e9e5", "gloss", n="الفراغ الداخلي"), cyl((-62, 18.2, 0), 2.6, 0.5, "#c9ced4", "metal", seg=16, n="مصرف الحوض (Waste)"),
         cyl((0, 70, -40), 1.4, 12, "#c9ced4", "metal", ax="y", seg=12, n="خلّاط حائطي (Wall mixer) عند 70 سم"), box((-4, 69, -40), (4, 71, -26), "#c9ced4", "metal", n="فوهة الصنبور (Spout)"), cyl((-9, 70, -40.5), 1.8, 1.4, "#c9ced4", "metal", ax="z", seg=14, n="مقبض الماء الساخن"), cyl((9, 70, -40.5), 1.8, 1.4, "#c9ced4", "metal", ax="z", seg=14, n="مقبض الماء البارد")]
    return P

def bidet():
    # WS-106 bidet rough-in: angle valve 20 cm above floor, outlet 75 mm
    P = [box((-30, 0, -28), (30, 1.5, 28), "#c9c2b0", "ghost", n="الأرضية"), box((-30, 0, -30), (30, 100, -28), "#c9c2b0", "ghost", n="الجدار"),
         box((-17, 1.5, -26), (17, 38, 20), "#f5f5f2", "gloss", n="حوض البيديه (Bidet)"), box((-14, 36, -24), (14, 40, 16), "#ececea", "gloss", n="الفراغ الداخلي"), cyl((0, 40, -22), 1.2, 9, "#c9ced4", "metal", seg=12, n="خلّاط البيديه"),
         py(1.5, 20, 9, -28, 0.7, CU, n="مخرج الماء عند 20 سم"), cyl((9, 20, -28.3), 1.4, 3, BRASS, "metal", ax="z", seg=12, n="صمام زاوية (Angle valve)"), pz(-4, 8, 0, 7.5, 3.75, PVC, "gloss", seg=18, n="وصلة التصريف 75 مم")]
    return P

def floor_drain(ug=False):
    # DR-106 #02 (below ground) / #03 (typical floor): 100x100 grating, uPVC extension pipe, access plug, trapped floor gully with auxiliary inlets, outlet; concrete pad below ground
    P = [box((-35, 0, -35), (35, 15, 35), "#b4b4ae", "ghost", n="بلاطة الأرضية (Floor slab)")]
    P += [box((-5, 15, -5), (5, 15.8, 5), "#c9ced4", "metal", n="شبكة المصرف 100×100 مم (Grating)")]
    for k in range(5): P.append(box((-5 + 0.8 + k * 1.9, 15.1, -4.4), (-5 + 1.4 + k * 1.9, 15.9, 4.4), "#9aa1a8", "metal", n="فتحات الشبكة"))
    P += [py(-6, 15, 0, 0, 2.6, PVC, "gloss", n="أنبوب تمديد uPVC (UPVC extension pipe)"), cyl((0, -14, 0), 5.5, 12, "#d8d3c2", "gloss", seg=20, n="مصيدة أرضية بمصرف (UPVC trapped floor gully)"), cyl((0, -3, 0), 3.2, 2, "#8e949c", "metal", seg=14, n="سدادة وصول (Access plug)"),
          px(0, 60, -10, 0, 2.6, PVC, "gloss", n="المخرج (Outlet) 82 مم"), px(-60, 0, -10, 0, 2.6, PVC, "gloss", n="المدخل (Inlet)"), pz(-45, 0, 0, -8, 1.8, PVC, "gloss", n="مدخل مساعد (Auxiliary inlet)")]
    if ug: P += [box((-35, -30, -35), (35, -22, 35), "#bdbab2", "matte", n="وسادة خرسانية (Concrete pad)")]
    return P

def gully_trap():
    # DR-106 #04: gully trap — 300x300 cover & frame, PVC sealed cover, inlet/outlet 110 mm, 300x300 chamber, 100/150 mm concrete surround
    return [box((-20, 0, -20), (20, 4, 20), "#3a3f45", "metal", n="غطاء وإطار 300×300 مم (Cover & frame)"), box((-15, 4, -15), (15, 5, 15), "#2c3036", "metal", n="غطاء PVC محكم (Sealed cover)"),
            box((-30, -45, -30), (30, 0, 30), "#b4b4ae", "ghost", n="محيط خرساني (Concrete surround) 100/150 مم"), box((-15, -32, -15), (15, 0, 15), "#d8d3c2", "gloss", n="غرفة المصيدة 300×300 مم"),
            px(-40, -12, -22, 0, 5.5, PVC, "gloss", n="المدخل 110 مم (Inlet)"), px(12, 40, -28, 0, 5.5, PVC, "gloss", n="المخرج 110 مم (Waste outlet inv. level & pipe size per drainage plan)"), box((-14, -30, -14), (14, -26, 14), "#cfc9b8", "matte", n="قاع القناة (Channel invert)")]

def manhole_90():
    # DR-106 #05: section through a manhole up to 90 cm deep: cover, 10 cm concrete make-up, 20 mm render in two coats + 3 coats of bitumen paint outside, benching rendered 1:6, 15 cm base, 5 cm blinding
    P = [box((-55, -5, -55), (55, 0, 55), "#d6d3c4", "matte", n="خرسانة نظافة (Blinding) 5 سم"), box((-50, 0, -50), (50, 15, 50), "#b4b4ae", "matte", n="قاعدة خرسانية 15 سم"),
         box((-50, 15, -50), (-30, 85, 50), "#c9c2b0", "ghost", n="جدار الغرفة (بلوك/خرسانة)"), box((30, 15, -50), (50, 85, 50), "#c9c2b0", "ghost"), box((-30, 15, -50), (30, 85, -30), "#c9c2b0", "ghost"), box((-30, 15, 30), (30, 85, 50), "#c9c2b0", "ghost"),
         box((-31, 15, -30), (-30, 85, 30), "#e8e4d4", "matte", n="لياسة 20 مم بطبقتين + طلاء إيبوكسي مقاوم"), box((-52, 15, -50), (-50, 85, 50), "#1c1c1c", "matte", n="3 طبقات دهان بيتومين على الوجه الخارجي"),
         box((-30, 85, -30), (30, 95, 30), "#bdbab2", "matte", n="تعبئة خرسانية 10 سم (Concrete make-up) درجة 2"), box((-24, 95, -24), (24, 97, 24), "#3a3f45", "metal", n="غطاء فتحة التفتيش (Manhole cover)"),
         box((-30, 15, -30), (30, 24, 30), "#d9d4c4", "matte", n="تدريج القناة (Benching) بميل 1:6 مدهون سيليكات الصوديوم"), cyl((0, 24, 0), 8, 30, "#8e949c", "ghost", ax="x", seg=20, n="قناة التصريف (Half channel)")]
    return P

def catch_basin():
    # DR-106 #11: catch basin 450x450 mm, GRP perforated basket (250 wide), 400 wide heavy-duty cover 50 mm thick, outlet to the Ø150 main WP
    P = [box((-30, 0, -30), (30, 50, 30), "#b4b4ae", "ghost", n="حوض التجميع (Catch basin) 450×450 مم"), box((-22.5, 5, -22.5), (22.5, 50, 22.5), "#9a9890", "ghost", n="جدران الحوض"),
         box((-20, 50, -20), (20, 55, 20), "#2c3036", "metal", n="غطاء شبكي ثقيل 400 مم سماكة 50 مم (Heavy duty)"), box((-12.5, 12, -12.5), (12.5, 48, 12.5), "#8aa6a0", "gloss", n="سلة GRP مثقّبة (Perforated basket) 250 مم")]
    for k in range(4): P.append(box((-12.6, 20 + k * 7, -3), (12.6, 21 + k * 7, 3), "#223", "matte", n="ثقوب السلة"))
    P += [px(22.5, 70, 18, 0, 7.5, PVC, "gloss", n="مخرج ⌀150 مم إلى الخط الرئيسي (Main WP)"), pz(-4, 4, 0, 52, 0.3, "#333", n="مقابض الغطاء")]
    return P

def pump_chamber():
    # DR-106 pump chamber: two submersible sewage pumps on guide rails (stainless 316, greased), lifting chains on hooks, wall-mounted valve arrangement, uPVC wall sleeve, 2 manhole covers 900x600, 110 vent with cowl
    P = [box((-120, -10, -80), (120, 0, 80), "#b4b4ae", "ghost", n="قاع الغرفة"), box((-120, 0, -80), (-110, 250, 80), "#c9c2b0", "ghost", n="جدار الغرفة"), box((110, 0, -80), (120, 250, 80), "#c9c2b0", "ghost"),
         box((-120, 250, -80), (120, 262, 80), "#bdbab2", "matte", n="بلاطة السقف مع فتحتي تفتيش")]
    for x, tag in ((-45, "A"), (45, "B")):
        P += [cyl((x, 5, 0), 17, 40, "#2c4a73", "gloss", seg=24, n=f"مضخة صرف غاطسة {tag} (Submersible sewage pump)"), cyl((x, 45, 0), 11, 12, "#2c4a73", "gloss", seg=20, n="رأس المحرك"),
              py(10, 250, x - 12, -14, 1.6, "#c9ced4", n="سكة توجيه ستانلس 316 (Guide rail) مدهونة بالشحم"), py(10, 250, x + 12, -14, 1.6, "#c9ced4"), cyl((x, 250, -14), 0.0001 + 3.5, 1, "#8e949c", "metal", seg=14, n="دعامة السكة"),
              cyl((x, 62, 0), 0.5, 188, "#c9ced4", "metal", seg=6, n="سلسلة رفع ستانلس على خطاف (S.S.316 lifting chain on hook)"), py(30, 190, x, 18, 3.8, "#4a4f55", n="أنبوب طرد حديد مطاوع (Ductile iron discharge)")]
    P += [px(-45, 45, 190, 18, 3.8, "#4a4f55", n="مجمّع الطرد (Discharge header)"), px(45, 140, 190, 18, 3.8, "#4a4f55", n="الطرد خارج الغرفة"), cyl((0, 180, 18), 6.0, 5, "#5a6570", "metal", ax="y", seg=16, n="صمام عدم رجوع (NRV)"), cyl((0, 150, 18), 6.0, 6, "#3a5f8f", "metal", ax="y", seg=16, n="صمام عزل (Wall mounted valve)"),
          px(-140, -110, 120, 0, 9.0, PVC, "gloss", n="مدخل الصرف الوارد (Inlet pipe)"), cyl((-114, 120, 0), 12, 2, "#aab0b8", "metal", ax="x", seg=24, n="كم uPVC عند الجدار (Wall protection sleeve)"),
          box((-70, 262, -30), (-10, 264, 30), "#3a3f45", "metal", n="غطاء فتحة 900×600 مم — الأول (2 Nos. manhole cover)"), box((10, 262, -30), (70, 264, 30), "#3a3f45", "metal", n="غطاء فتحة 900×600 مم — الثاني"),
          py(262, 330, 95, 50, 5.5, PVC, "gloss", n="أنبوب تهوية 110 مم (Vent)"), cyl((95, 330, 50), 8, 8, "#aab0b8", "metal", seg=18, n="غطاء تهوية مخروطي (Cowl)"), box((-100, 70, -78), (-60, 150, -70), "#c9ced4", "metal", n="لوحة التحكم الجدارية (To control panel)")]
    return P

def stack_connection():
    # DR-106 #09: vertical riser / stack connection: 110 foul waste stack in the riser shaft, vertical pipe support on the wall, horizontal branch in the false ceiling with access plug
    P = [box((-60, -5, -30), (60, 0, 30), "#b4b4ae", "ghost", n="بلاطة الدور السفلي (SSL)"), box((-60, 150, -30), (60, 160, 30), "#b4b4ae", "ghost", n="بلاطة الدور العلوي (SSL)"), box((20, 0, -30), (40, 150, 30), "#c9c2b0", "ghost", n="جدار الدعم (Support wall)"),
         box((-60, 110, -30), (20, 112, 30), "#e8e6df", "matte", n="مستوى السقف المستعار (False ceiling level)")]
    P += [py(-30, 175, 0, 0, 5.5, PVC, "gloss", n="ماسورة تصريف رأسية 110 مم (110Ø foul waste stack)"), box((-6.5, 60, -2), (6.5, 64, 2), "#8e949c", "metal", n="دعامة رأسية للأنبوب (Vertical pipe support)"), box((6.5, 60, -1), (20, 62, 1), "#8e949c", "metal"),
          px(-50, -4, 100, 0, 5.5, PVC, "gloss", n="فرع أفقي 110 مم (Horizontal branch)"), cyl((-9, 100, 0), 6.4, 2, "#8e949c", "metal", ax="x", seg=18, n="سدادة وصول (Access plug) للتنظيف"), box((-5, 108, -6), (5, 110, 6), "#c9ced4", "metal", n="لوحة وصول بالسقف (Access panel)"),
          cyl((0, 20, 0), 6.8, 3, "#c9c5b6", "gloss", seg=18, n="وصلة تمدد/وصل"), cyl((0, 90, 0), 6.8, 3, "#c9c5b6", "gloss", seg=18)]
    return P

def pipe_support_drain():
    # DR-106 #01/#08 supports: threaded rod + clamp; schedule (uPVC): dia 50 -> 1.10 H / 1.20 V ; 82 -> 1.40 / 1.50 ; 110 -> 1.50 / 1.70 ; 160 -> 1.80 / 2.10 m
    return [box((-14, 60, -10), (14, 68, 10), "#b4b4ae", "ghost", n="البلاطة (Slab)"), py(14, 60, 0, 0, 0.5, GI, n="قضيب مسنن (Threaded rod)"), tor((0, 7, 0), 5.8, 0.5, "#6f757c", m="metal", ax="z", seg=24, n="مشبك الأنبوب (Clamp)"),
            cyl((0, 7, -15), 5.5, 30, PVC, "gloss", ax="z", seg=24, n="أنبوب uPVC 110 مم"), box((-1.2, 12, -1), (1.2, 15, 1), "#6f757c", "metal", n="رأس المشبك"), cyl((0, 40, 0), 1.1, 1.0, "#8e949c", "metal", seg=6, n="صامولة")]

def pipe_bedding(cls="B"):
    # DR-106 #06 bedding: class 'B' — granular material 150 min under/around the pipe + selected material hand-compacted in 150 layers; class 'O' — concrete grade 'A' surround 150 min
    P = [box((-60, -10, -40), (60, 0, 40), "#8d8a82", "matte", n="قاع الخندق (Trench bed) 100/150 مم")]
    if cls == "B":
        P += [box((-40, 0, -40), (40, 30, 40), "#b8a98a", "ghost", n="مادة حبيبية (Granular) — ظهر الأنبوب 150 مم على الأقل"), box((-60, 30, -40), (60, 90, 40), "#8a7d62", "ghost", n="مادة مختارة مدموكة يدويًا (طبقات 150 مم)")]
    else:
        P += [box((-40, 0, -40), (40, 45, 40), "#b4b4ae", "ghost", n="خرسانة درجة A — إحاطة كاملة (Class O) 150 مم على الأقل"), box((-60, 45, -40), (60, 90, 40), "#8a7d62", "ghost", n="ردم مختار")]
    P += [pz(-40, 40, 0, 22, 5.5, PVC, "gloss", seg=22, n="أنبوب التصريف (Pipe O.D.)")]
    return P

def fcu_cond_trap():
    # DR-106 #07: FCU condensate drain connection — U-trap with unions (to dismantle for cleaning) connected to the nearest drain
    P = [box((-50, 100, -20), (50, 108, 20), "#b4b4ae", "ghost", n="البلاطة"), box((-30, 70, -14), (30, 100, 14), "#c7ccd2", "ghost", n="وحدة FCU (CEILING)"), box((-60, 20, -20), (60, 22, 20), "#e8e6df", "matte", n="السقف المستعار (Ceiling)")]
    P += [pz(14, 22, 20, 74, 1.25, PVC, "gloss", n="مخرج تكثيف من FCU"), py(32, 74, 20, 22, 1.25, PVC, "gloss", n="أنبوب نازل"), cyl((20, 52, 22), 1.9, 1.6, "#c9c5b6", "gloss", seg=14, n="وصلة فكّ (Union)"), py(32, 40, 28, 22, 1.25, PVC, "gloss", n="الساق الثانية"),
          px(20, 28, 32, 22, 1.25, PVC, "gloss", n="مصيدة U (U-trap)"), cyl((28, 46, 22), 1.9, 1.6, "#c9c5b6", "gloss", seg=14, n="وصلة فكّ"), px(28, 70, 40, 22, 1.25, PVC, "gloss", n="إلى أقرب مصرف بميل 1:40"), py(8, 40, 70, 22, 1.25, PVC, "gloss", n="نزول إلى المصرف")]
    return P

# ====================================================================================================== FIRE (FF-106)
def alarm_check_valve():
    # FF-106 typical alarm check valve: 150 mm alarm valve with trim kit + retarding chamber, water-motor alarm gong, electric alarm pressure switch, pressure gauges (upstream/downstream), main drain valve, discharge to drain
    P = [box((-40, -5, -22), (70, 0, 22), "#bdbab2", "ghost", n="أرضية غرفة المضخات"), box((-48, 0, -26), (-44, 190, 26), "#c9c2b0", "ghost", n="الجدار")]
    P += [py(0, 30, 0, 0, 7.8, FIRE, n="الأنبوب الرئيسي من شبكة الإطفاء (From fire fighting main) ⌀150"), cyl((0, 30, 0), 11, 28, FIRE, "metal", seg=24, n="صمام الإنذار ⌀150 (Alarm check valve)"), cyl((0, 58, 0), 8, 6, "#8e949c", "metal", seg=20, n="غطاء الصمام"),
          py(58, 120, 0, 0, 7.8, FIRE, n="إلى شبكة الرشاشات (To sprinkler system)"), px(-40, 0, 12, 0, 1.6, FIRE, n="خط الإنذار الجانبي"), cyl((-14, 12, 0), 3.2, 14, "#c9ced4", "metal", seg=16, n="غرفة التأخير (Retard chamber)")]
    P += [px(-40, -10, 36, 0, 1.4, "#c9ced4", n="خط إنذار إلى الجرس"), cyl((-42, 36, 0), 6, 4, "#b08d57", "metal", ax="x", seg=24, n="جرس الإنذار المائي (Water motor alarm gong)"), box((-34, 40, -6), (-24, 52, 6), "#c9ced4", "metal", n="محرك مائي للجرس"),
          box((-14, 70, 7), (-2, 80, 15), "#2c3e50", "matte", n="مفتاح ضغط إنذار كهربائي (Alarm pressure switch) → لوحة الإنذار"), py(58, 70, -8, 11, 0.9, FIRE, n="وصلة المفتاح")]
    P += gauge(14, 20, 9, "مقياس ضغط — أعلى المجرى (Upstream)") + gauge(14, 74, 9, "مقياس ضغط — أسفل المجرى (Downstream)")
    P += [px(0, 40, 6, -9, 1.9, FIRE, n="خط التصريف الرئيسي (Main drain)"), cyl((22, 6, -9), 2.8, 6, "#3a5f8f", "metal", ax="x", seg=14, n="صمام تصريف رئيسي (Main drain valve)"), py(-3, 6, 40, -9, 1.9, FIRE, n="تصريف إلى مصرف مناسب (Discharge to suitable drain)"), box((30, -5, -26), (50, 0, -14), "#4a4f55", "metal", n="مصرف أرضي")]
    return P

def zone_control_valve():
    # FF-106 zone control valve detail: 150 mm indicating-type floor control valve with supervisory switch, pressure gauge, water flow switch, test valve with sight glass and orifice union (flow equivalent to the smallest sprinkler), 25 mm drain to the drain riser
    P = [px(-60, 80, 40, 0, 7.8, FIRE, n="خط المنطقة ⌀150 (From riser) → إلى الرشاشات"), py(0, 40, 90, 0, 7.8, FIRE, n="الرايزر (Riser)")] + \
        [cyl((-30, 40, 0), 11, 14, "#8b1a14", "metal", ax="x", seg=24, n="صمام تحكم مؤشّر أرضي (Indicating-type floor control valve)"), cyl((-30, 51, 0), 5, 10, "#8b1a14", "metal", seg=16, n="جسم المؤشّر"), cyl((-30, 61, 0), 7.5, 1.2, RED, "gloss", seg=20, n="عجلة التشغيل"),
         box((-40, 56, -5), (-33, 62, 5), "#2c3e50", "matte", n="مفتاح مراقبة (Supervisory switch) → لوحة الإنذار"), cyl((20, 40, 0), 9, 10, "#3a5f8f", "metal", ax="x", seg=20, n="مفتاح تدفق المياه (Water flow switch)"), box((17, 48, -6), (25, 58, 6), "#2c3e50", "matte", n="رأس مفتاح التدفق")]
    P += gauge(-6, 47, 5, "مقياس ضغط (Pressure gauge)")
    P += [py(10, 40, 50, 0, 1.9, FIRE, n="خط الاختبار 25 مم"), cyl((50, 18, 0), 2.8, 6, "#3a5f8f", "metal", seg=14, n="صمام اختبار (Test valve)"), cyl((50, 26, 0), 2.6, 4, "#aad8e6", "glass", seg=14, n="زجاجة رؤية (Sight glass)"), cyl((50, 30, 0), 2.4, 2, "#8e949c", "metal", seg=14, n="وصلة بفتحة معايَرة (Union with orifice) مكافئة لأصغر رشاش"),
          pz(0, 40, 50, 10, 1.9, FIRE, n="تصريف 25 مم إلى رايزر التصريف"), py(-10, 10, 50, 40, 1.9, FIRE, n="رايزر التصريف (Drain riser)"), cyl((50, 0, 20), 2.8, 6, "#3a5f8f", "metal", ax="z", seg=14, n="صمام تصريف (Drain valve)")]
    return P

def fire_pump_set():
    # FF-106 fire fighting pump set: electric pump + jockey pump + diesel engine pump, control panel, pressure vessel 100 l, NRV, flexible couplings, gate valves, PG/PS, test line (project: 750 gpm electric/diesel, 40 gpm jockey)
    P = [box((-150, 0, -90), (150, 10, 90), "#bdbab2", "matte", n="قاعدة خرسانية للمجموعة (Common base)")]
    rows = [(-60, "مضخة كهربائية (Electric pump) 750 GPM", "#c0281f", 14), (0, "مضخة تعويضية (Jockey pump) 40 GPM", "#c0281f", 6.5), (60, "مضخة بمحرك ديزل (Diesel engine pump) 750 GPM", "#c0281f", 14)]
    for z, nm, c, r in rows:
        P += [cyl((-30, 10 + r, z), r, 40, c, "gloss", ax="x", seg=22, n=nm), px(10, 60, 10 + r, z, r * 0.8, "#2c4a73" if "Diesel" not in nm else "#4a4f55", "gloss", n="المحرك"), px(-100, -50, 10 + r, z, 5.5 if r > 10 else 3.2, FIRE, n="خط الشفط (Suction) من خزان الإطفاء"),
              px(-72, -64, 10 + r, z, 6.2 if r > 10 else 4, "#3a5f8f", n="صمام بوابة (Gate valve)"), px(-58, -52, 10 + r, z, 6.4 if r > 10 else 4, "#8e949c", n="وصلة مرنة (Flexible coupling)"),
              py(10 + r, 70, -22, z, 5.0 if r > 10 else 3.0, FIRE, n="رفع الطرد"), px(-22, 90, 70, z, 5.0 if r > 10 else 3.0, FIRE, n="طرد المضخة (Discharge)"), cyl((-5, 70, z), 5.6, 7, "#5a6570", "metal", ax="x", seg=18, n="صمام عدم رجوع (NRV)")]
        P += gauge(-10, 10 + 2 * r, z + 2, "مقياس ضغط (PG)") + [box((0, 10 + 2 * r + 1, z - 3), (8, 10 + 2 * r + 7, z + 3), "#2c3e50", "matte", n="مفتاح ضغط (PS)")]
    P += [pz(-60, 60, 90, 70, 6.0, FIRE, n="المجمّع الرئيسي (To system)"), cyl((125, 10, 0), 17, 60, "#2a6fb5", "gloss", seg=24, n="وعاء الضغط 100 لتر (Pressure tank)"), box((95, 20, -80), (115, 90, -66), "#8e949c", "metal", n="لوحة التحكم (Control panel)"),
          px(90, 140, 100, 0, 1.9, FIRE, n="خط الاختبار (Test line)"), cyl((130, 30, 50), 6, 2, "#2c3e50", "metal", seg=14, n="فتحة العادم للمحرك الديزل (Exhaust)")]
    return P

def breeching_inlet(four=False):
    # FF-106 breeching inlet detail (surface type): 4"x2 way cabinet 600x400x300 / 6"x4 way cabinet 600x600x300 (L x H x D); 2.5" instantaneous female inlets with caps + chain, check valve, drain, 'FIRE DEPT. INLET' plate
    H = 60 if four else 40; n = 4 if four else 2
    P = [box((-30, 0, 0), (30, H, 30), "#b8261d", "gloss", n=f"خزانة مدخل التنفيس (Breeching inlet) {'6″×4' if four else '4″×2'} اتجاه — 600×{H*10}×300 مم"), box((-28, 2, 0.5), (28, H - 2, 31), "#9d1f17", "gloss", n="الباب الأمامي المفصلي"),
         box((-14, H - 8, 31), (14, H - 3, 31.4), "#f2f2ee", "matte", n="لوحة «FIRE DEPT. INLET»"), box((-30, -1, -2), (30, 0.4, 32), "#6f757c", "metal", n="قاعدة تثبيت جدارية")]
    cols = [(-14, 14)] if not four else [(-14, 14)]
    for i in range(n):
        x = -16 if i % 2 == 0 else 16; y = 12 + (i // 2) * 20
        P += [pz(2, 30, x, y, 3.0, "#d0b070", n="مدخل 2½″ من نحاس (Instantaneous female inlet)"), cyl((x, y, 30), 3.8, 1.6, "#b08d57", "metal", ax="z", seg=18, n="وصلة سريعة مؤنثة"), cyl((x, y, 31.6), 4.1, 1.2, "#8e949c", "metal", ax="z", seg=18, n="غطاء بسلسلة (Cap & chain)"),
              cyl((x + 5, y - 5, 31.5), 0.3, 6, "#8e949c", "metal", seg=6, n="سلسلة الغطاء")]
    P += [py(-30, 4, 0, 14, 4.2, FIRE, n="أنبوب التغذية إلى الشبكة (Breeching main) ⌀100/150"), cyl((0, -12, 14), 4.6, 6, "#5a6570", "metal", seg=16, n="صمام عدم رجوع (Check valve)"), cyl((0, -22, 14), 2.0, 3, "#3a5f8f", "metal", ax="x", seg=12, n="صمام تصريف (Drain)")]
    return P

def sprinkler_hanger():
    # FF-106 pipe hanger detail: G.I. threaded rod M10/M12 from the slab (anchor with expansion shield), adjustable swivel ring hanger around the sprinkler pipe; max 305 mm from the soffit, min 25 mm
    return [box((-14, 72, -12), (14, 80, 12), "#b4b4ae", "ghost", n="البلاطة (Soffit of slab)"), cyl((0, 66, 0), 1.2, 6.5, "#8e949c", "metal", seg=10, n="مرساة تمدد M10 (Threaded anchor bolt w/ expansion shield)"), py(20, 72, 0, 0, 0.55, GI, n="قضيب G.I. مسنن M10/M12 (G.I. threaded rod)"),
            cyl((0, 35, 0), 1.2, 1, "#8e949c", "metal", seg=6, n="صامولة ضبط"), cyl((0, 20, 0), 1.0, 5, "#8e949c", "metal", seg=10, n="مفصلة دوارة (Swivel)"), tor((0, 13, 0), 4.8, 0.55, "#6f757c", m="metal", ax="z", seg=24, n="حلقة تعليق قابلة للضبط (Adjustable swivel ring)"),
            cyl((0, 13, -14), 3.2, 28, FIRE, "gloss", ax="z", seg=22, n="أنبوب الرشاشات (Sprinkler branch pipe) 25–100 مم")]

def sprinkler_sidewall():
    # FF-106 sidewall sprinkler: 25 mm branch from the ceiling-level pipe, M10 hanger, head projecting from the wall (fire-rated caulking), deflector horizontal
    P = [box((-30, 0, -10), (30, 90, 0), "#c9c2b0", "ghost", n="الجدار الجانبي (Side wall)"), box((-30, 88, -10), (30, 100, 30), "#b4b4ae", "ghost", n="البلاطة (Slab)"), px(-30, 30, 78, 14, 1.7, FIRE, n="خط الرش الفرعي 25 مم (250 pipe)"), py(78, 86, 0, 14, 0.5, GI, n="قضيب تعليق M10")]
    P += [pz(0, 14, 0, 78, 1.7, FIRE, n="وصلة إلى الرشاش"), cyl((0, 78, 0), 3.2, 1.2, "#aab0b8", "metal", ax="z", seg=18, n="وردة الجدار (Escutcheon)"), cyl((0, 78, 0.0), 2.4, 0.8, "#4a4f55", "rubber", ax="z", seg=18, n="مانع تسرّب مقاوم للحريق (Fire rated caulking)"),
          pz(-5, 0, 0, 78, 1.0, FIRE, n="رأس الرشاش الجانبي (Sidewall sprinkler)"), box((-2.6, 75.5, -8.4), (2.6, 76.3, -4), "#c9ced4", "metal", n="العاكس (Deflector)"), cyl((0, 78, -3), 1.0, 1.5, "#d63a2a", "gloss", ax="z", seg=10, n="بصيلة زجاجية (Glass bulb) 68°م")]
    return P

def extinguisher(kind="co2", kg=5):
    # FF-106 extinguisher schedule: CO2 5 kg / 12 kg wheeled; multi-purpose dry powder 2.5 / 4 / 6 kg; wheeled foam 13 gal
    c = "#c0281f"; r = 8.0 if kg <= 6 else 12.0; h = 48 if kg <= 6 else 80
    P = [cyl((0, 0, 0), r, h, c, "gloss", seg=24, n=f"أسطوانة طفاية {'CO₂' if kind == 'co2' else 'بودرة جافة متعددة الأغراض (ABC)'} {kg} كجم"), cyl((0, h, 0), r * 0.92, 4, c, "gloss", seg=24, n="كتف الأسطوانة"), cyl((0, h + 4, 0), 3.2, 3, "#8e949c", "metal", seg=14, n="رأس الصمام"),
         box((-2, h + 6, -1.2), (8, h + 7.4, 1.2), "#222", "metal", n="مقبض الحمل"), box((-8, h + 3, -1.2), (0, h + 4.4, 1.2), "#222", "metal", n="ذراع التشغيل (Lever)"), cyl((0, h + 5, 0), 0.8, 2, "#f5c518", "metal", ax="x", seg=8, n="دبوس الأمان (Safety pin)"),
         cyl((r + 1.5, h - 6, 0), 0.0001 + 1.0, 1.0, "#c9ced4", "metal", ax="x", seg=8, n="مقياس الضغط") if kind != "co2" else cyl((r * 0.7, h * 0.55, r * 0.7), 0.0001 + 0.1, 0.1, c, "gloss", seg=4, n="ملصق")]
    if kind == "co2": P += [py(h * 0.4, h + 2, r + 1.2, 0, 0.9, "#222", "rubber", n="خرطوم الطفاية"), cyl((r + 1.2, h * 0.4 - 3, 0), 3.6, 4, "#222", "rubber", seg=14, n="فوهة CO₂ (Horn)")]
    P += [cyl((0, h * 0.35, r + 0.05), 4.6, 0.2, "#f2f2ee", "matte", ax="z", seg=18, n=f"ملصق الطفاية: {kg} كجم"), cyl((0, h * 0.62, r + 0.05), 3.0, 0.2, "#111", "matte", ax="z", seg=14, n="ملصق التعليمات")]
    return P

# ====================================================================================================== ELECTRICAL (EP-108 / EP-109 / FA-108 / LPT-106)
GREY_P = "#9aa1a8"; PANEL = "#c9ced4"; DARKP = "#3f464d"
def louvres(x0, x1, y0, y1, z, n, c="#7a828a", nm="شرائح تهوية (Louvres)"):
    return rep(box((x0, y0, z), (x1, f"({y0})+1.2", f"({z})+1.2"), c, "metal", rot=[-25, 0, 0], n=nm), n, (0, f"(({y1})-({y0})-1.2)/{max(1, n - 1)}", 0))

def transformer_dry():
    # EP-108: 1000 kVA dry-type transformer 22 / 0.415 kV in its enclosure: 4000 x 1700 x 3200 mm incl. LV cable box (80 cm) and HV cable box; plan 320 x 170 core + boxes
    P = [box(("-W/2", 0, "-D/2"), ("W/2", 12, "D/2"), "#4a4f55", "metal", n="شاسيه القاعدة (Base frame) مع عجلات"), box(("-W/2+80", 12, "-D/2"), ("W/2-60", "H-30", "D/2"), "#c9d2da", "gloss", n="غلاف المحوّل المثقّب (Enclosure) — IP31"),
         box(("-W/2", 12, "-D/2"), ("-W/2+80", "H-90", "D/2"), "#aab0b8", "metal", n="صندوق كابلات الجهد المنخفض LV (80 سم)"), box(("W/2-60", 12, "-D/2"), ("W/2", "H-60", "D/2"), "#aab0b8", "metal", n="صندوق كابلات الجهد العالي HV")]
    for k in range(3):
        P += [cyl((f"-W/2+105+{k}*70", 20, 0), 26, "H-80", "#d8a35a", "ghost", seg=24, n=f"ملف راتنج مصبوب (Cast-resin coil) — طور {k+1}"), cyl((f"-W/2+105+{k}*70", 20, 0), 12, "H-70", "#6b6f75", "ghost", seg=18, n="قلب حديدي")]
    P += [box(("-W/2+80", "H-30", "-D/2-1"), ("W/2-60", "H-26", "D/2+1"), "#8e949c", "metal", n="غطاء علوي"), louvres("-W/2+90", "W/2-70", 40, "H-60", "D/2", 14, nm="شرائح تهوية أمامية (Ventilation louvres)"),
          louvres("-W/2+90", "W/2-70", 40, "H-60", "-D/2-1.2", 14, nm="شرائح تهوية خلفية"), box(("W/2-45", "H-110", "D/2"), ("W/2-15", "H-90", "D/2+1.5"), "#f2f2ee", "matte", n="لوحة بيانات المحوّل (Rating plate) 1000 kVA 22/0.415 kV"),
          box(("-W/2+20", "H-150", "D/2"), ("-W/2+60", "H-120", "D/2+2.5"), "#1f2226", "matte", n="جهاز مراقبة الحرارة (Temperature controller)")]
    for sx in (-1, 1): P.append(tor((f"{sx}*(W/2-40)", "H-26", 0), 7, 1.4, "#c9ced4", m="metal", ax="z", seg=16, n="عين رفع (Lifting eye)"))
    for sx in (-1, 1):
        for sz in (-1, 1): P.append(cyl((f"{sx}*(W/2-30)", 0, f"{sz}*(D/2-12)"), 7, 5, "#222", "rubber", ax="z", seg=18, n="عجلة المحوّل (Roller)"))
    return P

def hv_switchgear_22kv():
    # EP-108: 22 kV switchgear line-up: three bays (FEEDER | TRANSFORMER | FEEDER), each 900 mm wide x 2500 mm deep x 2350 mm high; cable entry from the trench below
    P = [box(("-W/2", 0, "-D/2"), ("W/2", 20, "D/2"), "#3f464d", "metal", n="قاعدة اللوحة + ممر الكابلات (Cable chamber base)")]
    for k, nm in enumerate(("مغذٍّ FEEDER", "محوّل TRANSFORMER", "مغذٍّ FEEDER")):
        x0 = f"-W/2+{k}*(W/3)"; x1 = f"-W/2+{k+1}*(W/3)"
        P += [box((f"{x0}+0.4", 20, "-D/2"), (f"{x1}-0.4", "H-12", "D/2"), "#c9d2da", "gloss", n=f"خلية {nm} — Metal-clad 22 kV"), box((f"{x0}+0.4", "H-12", "-D/2"), (f"{x1}-0.4", "H", "D/2"), "#aab0b8", "metal", n="غرفة الضغط الاحتياطي / فتحة تنفيس الضغط (Pressure relief)"),
              box((f"{x0}+8", 150, "D/2"), (f"{x1}-8", 215, "D/2+1.5"), "#e2e6ea", "gloss", n="باب مقصورة الأجهزة (LV compartment)"), box((f"{x0}+14", 170, "D/2+1.5"), (f"{x1}-14", 195, "D/2+2.2"), "#0b2a3a", "emit", n="مخطط انسيابي (Mimic diagram) + مؤشرات"),
              box((f"{x0}+8", 30, "D/2"), (f"{x1}-8", 140, "D/2+1.5"), "#d5dade", "gloss", n="باب مقصورة القاطع (Breaker compartment)"), cyl((f"({x0}+{x1})/2", 90, "D/2+1.6"), 5, 1, "#c0281f", "gloss", ax="z", seg=16, n="مقبض التشغيل/التأريض (Operating handle)"),
              cyl((f"({x0}+{x1})/2", 215, "D/2+1.6"), 1.0, 0.8, "#2ecc40", "emit", ax="z", seg=10, n="مصباح حالة (Closed)"), box((f"({x0}+{x1})/2-6", "60", "D/2+1.6"), (f"({x0}+{x1})/2+6", "66", "D/2+2.2"), "#f2f2ee", "matte", n="لوحة بيانات الخلية")]
        for j in range(3): P.append(cyl((f"{x0}+22+{j}*22", 20 - 40, "-D/2+30"), 2.2, 40, "#222", "rubber", seg=10, n="كابلات 22 kV أحادية القلب (HV cables) إلى المجرى"))
    return P

def lv_metering_panel():
    # EP-108: LV metering panel 600 x 800 x 1800 mm (W x D x H): floor-standing, glazed meter window, CT/meter compartment
    return [box(("-W/2", 0, "-D/2"), ("W/2", 10, "D/2"), "#4a4f55", "metal", n="قاعدة (Plinth)"), box(("-W/2", 10, "-D/2"), ("W/2", "H", "D/2"), "#c9ced4", "gloss", n="جسم اللوحة (Sheet steel, IP54)"),
            box(("-W/2+5", 110, "D/2"), ("W/2-5", 160, "D/2+1.4"), "#aad8e6", "glass", n="نافذة قراءة العدّادات (Toughened perspex window)"), rep(box(("-W/2+9", 118, "D/2"), ("-W/2+19", 152, "D/2+1"), "#f2f2ee", "gloss", n="عدّاد طاقة (kWh meter)"), 4, (12, 0, 0)),
            box(("-W/2+5", 20, "D/2"), ("W/2-5", 100, "D/2+1.4"), "#d5dade", "gloss", n="باب مقصورة محوّلات التيار (CT compartment)"), box(("W/2-14", 55, "D/2+1.4"), ("W/2-9", 75, "D/2+3.4"), "#222", "metal", n="مقبض بقفل (Lockable handle)"),
            rep(box(("-W/2+4", 10, "-D/2+6"), ("-W/2+8", "H-10", "-D/2+8"), "#8e949c", "metal", n="فتحات تهوية خلفية"), 3, (20, 0, 0))]

def dms_rtu():
    # EP-108: DMS RTU cabinet 1000 x 300 x 1000 mm (distribution management system remote terminal unit) — wall mounted
    return [box(("-W/2", 0, "-D/2"), ("W/2", "H", "D/2"), "#c9ced4", "gloss", n="خزانة وحدة RTU (DMS) — صاج مدهون"), box(("-W/2+4", 4, "D/2"), ("W/2-4", "H-4", "D/2+1.2"), "#aeb4ba", "gloss", n="باب أمامي"), box(("W/2-12", 40, "D/2+1.2"), ("W/2-8", 60, "D/2+3"), "#222", "metal", n="مقبض"),
            box(("-W/2+10", "H-30", "D/2+1.2"), ("-W/2+40", "H-12", "D/2+1.8"), "#0b2a3a", "emit", n="شاشة/مؤشرات الحالة"), box(("-W/2-3", 5, "-D/2"), ("-W/2", "H-5", "D/2"), "#6f757c", "metal", n="لوحة تثبيت جداري"), box(("W/2", 5, "-D/2"), ("W/2+3", "H-5", "D/2"), "#6f757c", "metal")]

def battery_rack():
    # EP-108: battery rack 1200 x 500 x 1290 mm: two tiers of sealed lead-acid blocks (48 V DC bank)
    P = [box(("-W/2", 0, "-D/2"), ("W/2", 8, "D/2"), "#2c3036", "metal", n="قاعدة الرف الفولاذية"), *[box((f"{sx}*(W/2-2)-2", 8, "-D/2"), (f"{sx}*(W/2-2)+2", "H", "-D/2+4"), "#c0281f", "metal", n="عمود الرف (Rack post)") for sx in (-1, 1)],
         *[box((f"{sx}*(W/2-2)-2", 8, "D/2-4"), (f"{sx}*(W/2-2)+2", "H", "D/2"), "#c0281f", "metal") for sx in (-1, 1)]]
    for tier, y in enumerate((40, 90)):
        P += [box(("-W/2", y - 4, "-D/2"), ("W/2", y, "D/2"), "#c0281f", "metal", n=f"رف البطاريات {tier+1}")]
        P += [rep(box(("-W/2+6", y, "-D/2+6"), ("-W/2+30", y + 30, "D/2-6"), "#2c3e6b", "gloss", n="بطارية مغلقة رصاص-حمض 12 فولت (VRLA)"), 4, (28, 0, 0)), rep(cyl(("-W/2+12", y + 30, 0), 0.9, 1.4, "#c9ced4", "metal", seg=8, n="قطب البطارية (Terminal)"), 8, (14, 0, 0))]
    P += [box(("-W/2+4", 112, "-D/2+4"), ("W/2-4", 114, "D/2-4"), "#8e949c", "metal", n="غطاء علوي مفتوح")]
    return P

def dc_supply_48v():
    # EP-108: 48 V DC supply cabinet 820 x 600 x 2082 mm: rectifier modules + distribution + control
    P = [box(("-W/2", 0, "-D/2"), ("W/2", 8, "D/2"), "#2c3036", "metal", n="قاعدة (Plinth)"), box(("-W/2", 8, "-D/2"), ("W/2", "H", "D/2"), "#cfd4d9", "gloss", n="خزانة مزوّد 48 فولت DC (Rack)")]
    for k in range(6): P.append(box(("-W/2+6", 20 + k * 22, "D/2"), ("W/2-6", 38 + k * 22, "D/2+3"), "#7a828a" if k < 4 else "#0b2a3a", "gloss" if k < 4 else "emit", n="وحدة مقوّم 48 فولت (Rectifier module)" if k < 4 else "وحدة مراقبة وتحكم"))
    P += [box(("-W/2+6", 160, "D/2"), ("W/2-6", 190, "D/2+3"), "#d5dade", "gloss", n="لوحة توزيع الفروع (DC distribution)"), rep(box(("-W/2+10", 164, "D/2+3"), ("-W/2+18", 186, "D/2+4"), "#222", "metal", n="قاطع فرعي (Breaker)"), 8, (9, 0, 0)), box(("W/2-14", 100, "D/2+3"), ("W/2-9", 125, "D/2+5"), "#222", "metal", n="مقبض")]
    return P

def mdb_2000a():
    # EP-108 / SLD (EP-107): main distribution board MDB, 320 x 80 x 200 cm, Form-4 Type-6, 2000 A ACB TPN incomer, 50 kA, IP54; eight 40 cm sections (assumed split)
    P = [box(("-W/2", 0, "-D/2"), ("W/2", 10, "D/2"), "#2c3036", "metal", n="قاعدة (Plinth) 10 سم")]
    for k in range(8):
        x0 = f"-W/2+{k}*(W/8)"; x1 = f"-W/2+{k+1}*(W/8)"
        P += [box((f"{x0}+0.3", 10, "-D/2"), (f"{x1}-0.3", "H-10", "D/2"), "#d5dade", "gloss", n=f"خلية {k+1} من MDB — Form 4 Type 6"), box((f"{x0}+4", 20 if k else 25, "D/2"), (f"{x1}-4", "H-30", "D/2+1.2"), "#c3c8cd", "gloss", n="باب الخلية")]
        if k == 0: P += [box((f"{x0}+6", 40, "D/2+1.2"), (f"{x1}-6", 120, "D/2+7"), "#3f464d", "gloss", n="قاطع رئيسي هوائي ACB 2000 أمبير TPN (Incomer)"), cyl((f"({x0}+{x1})/2", 90, "D/2+7.4"), 4, 1, "#c0281f", "gloss", ax="z", seg=14, n="مقبض/زر ACB")]
        else: P += [rep(box((f"{x0}+8", 30, "D/2+1.2"), (f"{x1}-8", 48, "D/2+5"), "#3f464d", "gloss", n="قاطع صندوقي مصبوب MCCB (Outgoing)"), 5, (0, 26, 0)), rep(box((f"{x0}+10", 160, "D/2+1.2"), (f"{x0}+22", 170, "D/2+2"), "#0b2a3a", "emit", n="عدّاد رقمي/مؤشر"), 1, (0, 0, 0))]
        P += [box((f"{x0}+3", "H-10", "-D/2"), (f"{x1}-3", "H", "D/2"), "#aab0b8", "metal", n="غرفة قضبان التوزيع العلوية (Busbar chamber)"), box((f"{x1}-8", 100, "D/2+1.2"), (f"{x1}-5", 118, "D/2+3.2"), "#222", "metal", n="مقبض")]
    return P

def generator_set():
    # EP-108 / SLD: diesel generating set ~200 kVA (plan 260 x 110 cm): engine + alternator on a skid with integral fuel tank, radiator, silencer, control panel, battery; room ventilation as per manufacturer
    P = [box(("-W/2", 0, "-D/2"), ("W/2", 22, "D/2"), "#2c3036", "metal", n="شاسيه القاعدة + خزان الوقود اليومي (Skid with base fuel tank)"), box(("-W/2+6", 22, "-D/2+6"), ("-W/2+120", 95, "D/2-6"), "#f2a900", "gloss", n="محرك ديزل (Diesel engine)"),
         cyl(("-W/2+130", 62, 0), 34, 58, "#2e6f3f", "gloss", ax="x", seg=26, n="مولّد التيار المتناوب (Alternator)"), box(("W/2-28", 22, "-D/2+8"), ("W/2-6", 100, "D/2-8"), "#3f464d", "metal", n="مبرّد المحرك (Radiator) مع مروحة"), cyl(("W/2-30", 62, 0), 36, 4, "#222", "metal", ax="x", seg=24, n="مروحة التبريد"),
         box(("-W/2+30", 95, -22), ("-W/2+70", 112, -6), "#d9a21b", "metal", n="غطاء الصمامات"), cyl(("-W/2+90", 98, 28), 7, 55, "#6f757c", "metal", seg=16, n="كاتم صوت العادم (Silencer)"), cyl(("-W/2+90", 153, 28), 4, 30, "#6f757c", "metal", ax="x", seg=14, n="خط العادم"),
         box(("-W/2+180", 95, -25), ("-W/2+215", 130, 25), "#c9ced4", "gloss", n="لوحة التحكم (Generator controller) مع شاشة"),
         box(("-W/2+185", 112, 25), ("-W/2+210", 126, 26), "#0b2a3a", "emit", n="شاشة المراقبة"), box(("-W/2+6", 22, "D/2-22"), ("-W/2+30", 48, "D/2-6"), "#222", "metal", n="بطارية البدء (Starter battery)"), cyl(("-W/2+6", 30, 0), 4, 16, "#c9ced4", "metal", ax="z", seg=10, n="مدخل الوقود")]
    return P

def smdb_meter_enclosure():
    # EP-108 / EP-109: SMDB with an aluminium/steel meter enclosure for the residences (6 Nos kWh meters), toughened clear perspex viewing windows, single-core trunking inside; 80 cm wide, top at 180 cm AFFL
    P = [box((-40, 0, -9), (40, 190, 9), "#c9ced4", "gloss", n="خزانة عدّادات الوحدات (Metering enclosure) — صاج/ألمنيوم يطابق SMDB"), box((-38, 4, 9), (38, 186, 9.8), "#d5dade", "gloss", n="باب مقسّم")]
    for r in range(3):
        for c in range(2):
            x = -20 + c * 40; y = 55 + r * 40
            P += [box((x - 14, y - 12, 9.8), (x + 14, y + 12, 10.4), "#aad8e6", "glass", n="نافذة بيرسبكس شفافة (Toughened perspex)"), box((x - 8, y - 8, 8), (x + 8, y + 8, 9), "#f2f2ee", "gloss", n="عدّاد طاقة (kWh meter)"), cyl((x, y, 8), 5, 0.4, "#111", "matte", ax="z", seg=18, n="قرص العدّاد")]
    P += [box((-30, 150, 9.8), (30, 180, 10.4), "#0b2a3a", "matte", n="مقصورة القاطع الرئيسي (SMDB incomer)"), rep(box((-28, 154, 10.4), (-20, 176, 11), "#222", "metal", n="قاطع (MCB)"), 7, (8.4, 0, 0)), box((-6, 190, -5), (6, 200, 5), "#8e949c", "metal", n="مدخل كابلات علوي (Gland plate)")]
    return P

def cable_tray_installation():
    # EP-109 cable tray typical installation: hot-dip galvanised tray, G.I. closed cover, cantilever support bracket with MS hank bush, wall fixing
    P = [box((-60, 0, -10), (-50, 70, 0), "#c9c2b0", "ghost", n="الجدار/العمود"), box((-52, 24, -26), (-50, 36, 26), "#aab0b8", "metal", n="ظهر ذراع الحامل")]
    P += [rep(box((-52 + 0, 24, -26 + 0), (28, 26, -22), "#aab0b8", "metal", n="ذراع حامل (Cantilever bracket) — حديد مجلفن بالغمس الساخن"), 2, (0, 0, 48)), box((-4, 26, -26), (28, 27, 26), "#b9c2ca", "metal", n="قاعدة الصينية (Cable tray)"), box((-4, 27, -26), (28, 36, -24.6), "#b9c2ca", "metal", n="حافة الصينية"), box((-4, 27, 24.6), (28, 36, 26), "#b9c2ca", "metal"),
          box((-4, 38, -26), (28, 39, 26), "#9aa1a8", "metal", n="غطاء مغلق G.I. (Closed cover)"), rep(cyl((0, 26.5, -22), 0.9, 1.2, "#8e949c", "metal", ax="y", seg=8, n="برغي ربط الصينية مع الحامل"), 2, (24, 0, 0))]
    P += [rep(cyl((-1 + 6, 27, -8 + 0), 1.2, 7, "#222", "rubber", seg=10, n="كابلات الطاقة على الصينية"), 4, (0, 0, 5))]
    P += [box((-52, 56, -9), (-48, 60, 9), "#8e949c", "metal", n="كم/كتف تثبيت (MS hank bush)")]
    return P

def downlight_install():
    # EP-109 down-light fixing: 20 mm PVC circular box cast in the slab, 20 mm PVC adapter, locknut with clamp, 3C x 2.5 mm2 flexible wire inside 20 mm flexible conduit, fixture in the false ceiling
    P = [box((-30, 50, -30), (30, 70, 30), "#b4b4ae", "ghost", n="البلاطة الخرسانية"), box((-30, 0, -30), (30, 2, 30), "#e8e6df", "matte", n="السقف المستعار (False ceiling)"), cyl((0, 54, 0), 4.6, 6, "#e8e4d8", "gloss", seg=20, n="علبة PVC دائرية 20 مم مدفونة في البلاطة (Circular box)"),
         cyl((0, 50, 0), 4.8, 0.8, "#e8e4d8", "gloss", seg=20, n="غطاء العلبة (Circular cover)"), py(38, 50, 0, 0, 1.0, "#e8e4d8", "gloss", n="وصلة PVC 20 مم (PVC adapter)"), cyl((0, 44, 0), 1.5, 1.2, "#8e949c", "metal", seg=8, n="صامولة قفل + مشبك (Lock nut with clamp)"),
         py(14, 38, 0, 0, 1.0, "#222", "rubber", n="مواسير مرنة 20 مم (Flexible conduit) بداخلها سلك 3C×2.5 مم²"), cyl((0, 2, 0), 9, 0.4, "#f2f2ee", "gloss", seg=26, n="إطار كشاف غاطس (Down light)"), cyl((0, 1.6, 0), 7.2, 0.5, "#fff", "emit", seg=26, n="مصدر الضوء LED"),
         cyl((0, 2.4, 0), 7.6, 6, "#c9ced4", "metal", seg=22, n="جسم الكشاف الغاطس"), box((-2, 10, -1), (2, 14, 1), "#222", "matte", n="سائق LED (Driver) مع علبة توصيل")]
    return P

def fa_device_mount(kind="detector"):
    # FA-108: fixing details — detector on the false ceiling (25 mm PVC concealed conduit, circular box, FP200 cable); speaker/flasher at 2300 mm; manual pull station at 1400 (+/-200) mm; fire telephone jack at 1250 mm
    P = [box((-40, 0, -20), (40, 4, 20), "#b4b4ae", "ghost", n="الأرضية (FFL)"), box((-40, 0, -22), (40, 330, -20), "#c9c2b0", "ghost", n="الجدار"), box((-40, 330, -22), (40, 345, 20), "#b4b4ae", "ghost", n="البلاطة"), box((-40, 270, -20), (40, 273, 20), "#e8e6df", "matte", n="السقف المستعار (False ceiling)")]
    if kind == "detector":
        P += [cyl((0, 332, 0), 4.6, 6, PVC, "gloss", seg=20, n="علبة دائرية في البلاطة"), py(310, 330, 0, 0, 1.3, PVC, "gloss", n="ماسورة PVC 25 مم مخفية"), py(273, 310, 0, 0, 0.5, "#c0281f", "rubber", n="كابل FP200 مقاوم للحريق"), cyl((0, 273.3, 0), 5.5, 1.0, "#f2f2ee", "gloss", seg=24, n="قاعدة كاشف (Detector base)"),
              cyl((0, 270, 0), 5.2, 3.4, "#f2f2ee", "gloss", seg=24, n="كاشف دخان/حرارة ضوئي (Optical smoke / heat detector)"), cyl((0, 270, 0), 0.9, 0.3, "#d63a2a", "emit", seg=10, n="مؤشر LED")]
    else:
        y = {"speaker": 230, "pull": 140, "tel": 125}[kind]; nm = {"speaker": "مكبّر/وامض (Speaker / flasher) — 2300 مم", "pull": "نقطة كسر زجاج يدوية (Manual pull station) — 1400 (±200) مم", "tel": "مقبس هاتف الإطفاء (Fire telephone jack) — 1250 مم"}[kind]
        P += [py(y, 330, 0, -17, 1.3, PVC, "gloss", n="ماسورة PVC 25 مم مخفية في الجدار"), box((-4, y - 4, -20), (4, y + 4, -17), "#6f757c", "metal", n="علبة خلفية (Back box)"), box((-6, y - 6, -17), (6, y + 6, -14), "#c0281f" if kind != "tel" else "#f2f2ee", "gloss", n=nm)]
        if kind == "pull": P += [box((-3, y - 3, -14), (3, y + 3, -13.4), "#f2f2ee", "glass", n="زجاج الكسر")]
    return P

def exit_light_install():
    # FA-108 exit-light fitting installation: 2x2.5 mm2 PVC/LSF wire with GI pipe on the slab, fixable conduit, PG gland with locknut, EXIT luminaire above the door
    return [box((-60, 330, -20), (60, 345, 20), "#b4b4ae", "ghost", n="البلاطة الخرسانية"), box((-60, 0, -20), (60, 4, 20), "#b4b4ae", "ghost", n="الأرضية"), box((-45, 2, -2), (45, 205, 2), "#cfc9b8", "ghost", n="الباب (Door)"),
            px(-40, 0, 326, 0, 0.8, "#444", "metal", n="ماسورة GI على البلاطة"), py(222, 326, 0, 0, 0.9, "#222", "rubber", n="ماسورة مرنة (Fixable conduit) وبداخلها سلك 2×2.5 مم² PVC/LSF"), cyl((0, 220, 0), 1.4, 1.2, "#8e949c", "metal", seg=8, n="غدّة PG مع صامولة قفل (PG gland with locknut)"),
            box((-17, 208, -2), (17, 220, 2.6), "#2e8b3a", "gloss", n="كشاف مخرج الطوارئ (EXIT luminaire)"), box((-14, 210, 2.6), (14, 218, 3), "#e8f5e9", "emit", n="لوحة «EXIT» مضيئة")]

def earth_pit_detail():
    # LPT-106 detail A: down conductor & earth pit: 25x3 mm bare copper tape from the roof, concrete pit with cover and 5-hole earth bar EBC 05 (test point), rod-to-tape clamp, driving stud, 20 x 1200 mm solid copper earth rod (resistance < 10 ohm), 1C x 70 mm2 looping cable, 50 mm PVC conduit
    P = [box((-60, -130, -40), (60, 0, 40), "#b8a98a", "ghost", n="التربة"), box((-60, 0, -40), (60, 8, 40), "#d6d3c4", "matte", n="منطقة التشطيب (Finish area)"), box((-24, -28, -24), (24, 0, 24), "#b4b4ae", "matte", n="حفرة خرسانية (Concrete pit)"), box((-18, -24, -18), (18, 0, 18), "#2b2b2b", "ghost", n="فراغ الحفرة"),
         box((-20, 0, -20), (20, 1.4, 20), "#c9ced4", "metal", n="غطاء الحفرة (Pit lid)"), box((-14, -8, -2), (14, -5, 2), "#b87333", "metal", n="قضيب تأريض بخمس فتحات EBC 05 (5-hole earth bar / test point)")]
    P += [rep(cyl((-10, -8, 0), 0.0001 + 0.9, 3.4, "#c9ced4", "metal", seg=8, n="مسمار توصيل (Terminal stud)"), 5, (5, 0, 0)), py(-130, -10, 0, 0, 1.0, "#b87333", n="قضيب تأريض نحاسي مصمت 20 مم × 1200 مم (Solid copper earth rod)"), cyl((0, -128, 0), 1.0, 3, "#6f757c", "metal", seg=8, n="رأس طرق/مسمار تثبيت (Driving spike)"),
          cyl((0, -78, 0), 1.6, 3, "#8e949c", "metal", seg=10, n="وصلة تمديد القضيب (Coupler)"), cyl((0, -14, 0), 2.0, 2.6, "#8e949c", "metal", seg=10, n="مشبك القضيب بالشريط (Rod to tape clamp)"), px(0, 40, -9, 0, 0.7, "#2ecc40", n="كابل 1C×70 مم² للربط مع الحفرة التالية (Looping)"),
          box((-3, -6, -0.3), (3, -2, 0.3), "#b87333", "metal", n="شريط نحاس عارٍ 25×3 مم (Bare copper tape)"), py(8, 140, -16, 6, 0.0001 + 0.7, "#b87333", n="شريط/موصل نزول 25×3 مم على العمود (Down conductor)"), pz(-30, 6, -16, 0, 2.5, "#e8e4d8", "gloss", n="ماسورة PVC ⌀50 مم (50 mm PVC conduit)")]
    return P

def air_terminal_free_standing():
    # LPT-106 details F/H: free-standing air terminal rod with multiple point (MPC 16), tripod support ATS 001 on a concrete base, 25x3 mm bare copper tape on the parapet; protective angle by LPS class (76.3 deg @ 1 m height, class III)
    P = [box((-30, 0, -30), (30, 30, 30), "#b4b4ae", "matte", n="قاعدة خرسانية (Concrete base)")]
    for k in range(3):
        a = k * 120
        P.append(dict(cyl((0, 31, 0), 0.0001 + 0.7, 52, "#c9ced4", "metal", seg=8, n="رجل الحامل الثلاثي (Tripod support ATS 001)"), rot=[22, a, 0]))
    P += [cyl((0, 30, 0), 5, 2, "#8e949c", "metal", seg=14, n="قاعدة الحامل (Air rod base ASGL 16M)"), py(32, 300, 0, 0, 0.8, "#c9ced4", n="قضيب الصاعقة (Air terminal rod) ⌀16 مم"), cyl((0, 300, 0), 0.8, 4, "#c9ced4", "metal", seg=8, n="رأس قضيب (Multiple point MPC 16)")]
    for k in range(4): P.append(dict(cyl((0, 300, 0), 0.3, 12, "#c9ced4", "metal", seg=6, n="أطراف الرأس المتعدد (Multiple points)"), rot=[0, k * 90, 55]))
    P += [px(0, 40, 4, 0, 0.5, "#b87333", n="شريط نحاس عارٍ 25×3 مم (Bare copper tape)")]
    return P

def dc_tape_clip():
    # LPT-106 details I/M: metallic DC tape clip fixing the 25x3 mm copper tape on a parapet wall; square tape clamp / junction clamp
    P = [box((-40, 0, -14), (40, 36, 0), "#c9c2b0", "ghost", n="جدار السور (Parapet wall)"), box((-40, 36, -14), (40, 42, 6), "#b4b4ae", "ghost", n="حافة السور (Parapet top)"), box((-40, 41.9, -1.25), (40, 42.2, 1.25), "#b87333", "metal", n="شريط نحاس عارٍ 25×3 مم (Bare copper tape)")]
    P += [rep(box((-33, 42.2, -2.2), (-27, 43.2, 2.2), "#c9ced4", "metal", n="مشبك شريط معدني DC (Metallic DC tape clip)"), 3, (22, 0, 0)), rep(cyl((-30, 41.2, 0), 0.5, 1, "#8e949c", "metal", seg=6, n="مسمار تثبيت المشبك"), 3, (22, 0, 0)),
          box((30, 42.2, -2.8), (36, 44.6, 2.8), "#c9ced4", "metal", n="مشبك شريط مربّع (Square tape clamp)"), box((32, 44.6, -0.8), (34, 46, 0.8), "#8e949c", "metal", n="برغي المشبك"), box((-40, 36, 6), (40, 38, 7), "#8e949c", "ghost", n="غطاء ألمنيوم للسور")]
    return P

# ====================================================================================================== registry
def make():
    out = {}
    def D(id_, name, en, cat, parts, dims, src, facts, asm=None, conf="derived", lod=6.0):
        t = sample(id_, name, en, cat, parts, place=NONE, lod=lod, conf=conf, src=src, facts=facts, asm=(asm or []) + [A_COL], dims=dims)
        out[t[0]] = t[1]
    M_, P_, F_, E_ = "mechanical", "plumbing", "fire", "electrical"
    # ---------------- mechanical
    D("det_fcu_connection", "وصلات FCU النموذجية: صمامات عزل + مصفاة + موازنة + تحكم + تنفيس + مصيدة تكثيف", "Typical FCU piping connection + condensate trap", M_, fcu_pipe_connection(), {"W": 150, "D": 60, "H": 60}, SRC_AC + SRC_DR,
      [["العنوان في المخطط", "TYPICAL FAN COIL CONNECTION DETAILS + FCU COND. DRAIN CONNECTION"], ["مصيدة التكثيف", "U-trap بوصلات فكّ تُوصَّل بأقرب مصرف (DR-106 تفصيل 07)"], ["ميل التصريف", "1:40 (جدول DR-106)"]],
      ["ترتيب الصمامات وقياس الأنابيب (¾″) من التفصيل القياسي — الرسم في المستند بلا قياسات"])
    D("det_fcu_mount", "تثبيت FCU بالتعليق: قضبان M10 + عوازل مطاطية + صواميل مزدوجة", "FCU hanger mounting", M_, fcu_hanger_mount(), {"W": 125, "D": 60, "H": 100}, SRC_AC,
      [["العنوان", "FAN COIL UNIT MOUNTING DETAIL (AC-107)"], ["القضبان", "4 قضبان مسننة من البلاطة (M10)"]], ["قطر القضيب وعوازل الاهتزاز: قياسية"])
    D("det_duct_hanger", "تعليق المجاري: عارضة زاوية + قضيبان ⌀10 مم (جدول AC-107)", "Duct trapeze hanger (per AC-107 table)", M_, duct_hanger_set(), {"W": 60, "H": 40}, SRC_AC,
      [["قضيب التعليق", "⌀10 مم"], ["مجرى ≤ 760 مم", "زاوية 25×25×3 على تباعد 2.4 م"], ["مجرى 790–1520 مم", "زاوية 40×40×3 على تباعد 1.8 م"], ["مجرى ≥ 1250 مم", "زاوية 50×50×6 على تباعد 1.8 م"]],
      ["تحديد الفئة عند الحدود المتداخلة (1250–1520 مم) يحتاج مراجعة الجدول الأصلي"], conf="doc")
    D("det_duct_access_door", "باب وصول على المجرى (AC D-37)", "Duct access door", M_, duct_access_door(), {"W": 60, "D": 12, "H": 40}, SRC_AC, [["التفصيل", "ACCESS DOOR ON DUCT (AC D-37)"], ["المكوّنات", "إطار + باب معزول + جوان + مفصلتان + قفلا كامة"]], ["أبعاد الباب 27×25 سم تقريبية (المخطط بلا قياسات صريحة)"])
    D("det_vaned_elbow", "كوع مجرى بريش توجيه (AC D-28)", "Vaned elbow", M_, vaned_elbow(), {"W": 40, "H": 30}, SRC_AC, [["التفصيل", "VANED ELBOW DETAIL (AC D-28)"], ["ريش التوجيه", "تُركَّب في كل كوع مربّع"]], ["عدد الريش وشكلها (قوس مبسّط بصفائح 45°) — افتراض"])
    D("det_fd_curtain", "مخمد حريق بستارة منسدلة (AC D-25)", "Drop-curtain fire damper", M_, fd_drop_curtain(), {"W": 40, "H": 30}, SRC_AC, [["التفصيل", "DROP CURTAIN FIRE DAMPERS (AC D-25)"], ["الملاحظة", "مخمد حريق لكل مجرى يخترق أرضية/جدار مقاوم للحريق"]], ["رابط الانصهار 72°م وأبعاد الصندوق: قياسية"])
    D("det_duct_smoke_detector", "كاشف دخان للمجرى (AC D-21)", "Duct smoke detector", M_, duct_smoke_detector(), {"W": 70, "D": 40, "H": 40}, SRC_AC, [["التفصيل", "SMOKE DETECTOR INSTALLATION IN RECTANGULAR OR SQUARE DUCT (AC D-21)"], ["أنبوب العيّنة", "يبرز ≥ 32 مم داخل تيار الهواء"]], ["قياس الغلاف ومسافات الأنابيب: قياسية"])
    D("det_roof_duct_penetration", "اختراق مجرى لبلاطة السطح: كتلة مصمتة + حجر تغطية 0.5 م + أخدود تنقيط", "Duct roof penetration", M_, roof_duct_penetration(), {"W": 170, "D": 130, "H": 130}, SRC_AC,
      [["التفصيل", "DUCT ROOF PENETRATION DETAIL — يصلح لكل اختراقات السطح"], ["حجر التغطية", "خرساني بنتوء 0.5 م مع أخدود تنقيط (Drip groove)"], ["الإحكام", "مستكي + اختبار تسرّب بالماء"]], ["ارتفاع الكتلة والقياسات: قياسية"], conf="doc")
    D("det_pipe_sleeve", "اختراق أنبوب لجدار/بلاطة: كم 20 gauge + حشو ليفي + سدّ حريق + وردة", "Pipe penetration with sleeve + firestop", M_, pipe_sleeve_penetration(), {"W": 80, "D": 18, "H": 80}, SRC_AC,
      [["الكم", "صاج 20 gauge (1.6 مم تلسكوبي)"], ["الفراغ", "25 مم يُحشى بمادة ليفية"], ["السدّ", "مادة سدّ حريق بسماكة 120 mils"], ["الغطاء", "وردة معدنية (Escutcheon) على الوجهين"]], ["قطر الكم: افتراض"], conf="doc")
    D("det_riser_clamp", "مشبك رايزر على كمرة فولاذية (جدول AC-107)", "Riser clamp", M_, riser_clamp(), {"W": 60, "D": 16, "H": 70}, SRC_AC,
      [["قطاع المشبك", "50×6 / 40×6 / 32×6 / 32×5 مم حسب قطر الأنبوب"], ["قطر البرغي", "10–15 مم"], ["اللحام", "مستمر 3 مم"], ["أقطار الأنابيب في الجدول", "12–25 / 32–75 / 125–150 / 200–250 مم"]], ["مطابقة قطاع المشبك لكل قطر: من الجدول الأصلي"], conf="doc")
    D("det_pipe_insulation", "عزل الأنابيب داخلي (25 مم) وخارجي (50 مم + غلاف ألمنيوم)", "Indoor / outdoor pipe insulation", M_, pipe_insulation_pair(), {"W": 100, "D": 40, "H": 20}, SRC_AC + SRC_WS,
      [["المادة", "ألياف زجاجية بموصلية ≤ 0.032 واط/م·°م (WS-106 ملاحظة 7)"], ["السماكة", "25 مم في الحيز المكيّف، 50 مم في الأماكن المكشوفة"]], ["الغلاف PVC/ألمنيوم وسيور الربط: قياسية"], conf="doc")
    D("det_aav", "مفتاح تنفيس هواء أوتوماتيكي (AAV)", "Automatic air vent", M_, aav(), {"W": 8, "D": 8, "H": 16}, SRC_AC + SRC_WS, [["الرمز", "AAV — AUTOMATIC AIR VENT"]], ["القياس ⅜″ ومسار التصريف: قياسية"])
    D("det_pump_foundation", "أساس المضخة: وسادة خرسانية + قاعدة قصور ذاتي + نوابض (انحراف 50 مم)", "Pump foundation with inertia base + spring isolators", M_, pump_foundation(), {"W": 180, "D": 100, "H": 40}, SRC_WS,
      [["الوسادة", "10 سم فوق البلاطة (الملاحظة 11: قاعدة خرسانية ≥ 30 سم لمجموعات الضخ)"], ["النوابض", "عوازل نابضية بانحراف 50 مم"], ["العنوان", "TYPICAL PUMP FOUNDATION DETAIL"]], ["قياس القاعدة الفولاذية: قياسي"], conf="doc")
    D("det_pump_piping", "مضخة مياه مبردة وتمديداتها (AC-107): عزل + مصفاة + وصلات مرنة + عدم رجوع + مقاييس", "Typical pump & piping connection", M_, pump_piping_connection(), {"W": 190, "D": 120, "H": 70}, SRC_AC,
      [["العنوان", "TYPICAL PUMP & PIPING CONNECTION DETAILS"], ["المضخات في المشروع", "3 مضخات مياه مبردة (2 عاملة + 1 احتياط) — 168 GPM @ 100 ft"]], ["ترتيب المكوّنات من التفصيل القياسي؛ الأقطار تقديرية"])
    # ---------------- plumbing & drainage
    D("det_clevis_hanger", "حامل أنبوب قابل للضبط (Clevis hanger)", "Adjustable clevis hanger", P_, clevis_hanger(), {"W": 20, "D": 30, "H": 70}, SRC_WS, [["العنوان", "TYPICAL ADJUSTABLE CLEVIS HANGER (WS-106)"]], ["قطر القضيب (M10) وقياس الحزام: قياسي"], conf="doc")
    D("det_pipe_encasement", "تغليف أنابيب uPVC بالخرسانة (20 سم من كل جهة)", "Concrete encasement of uPVC pipes", P_, pipe_encasement(), {"W": 60, "D": 60, "H": 40}, SRC_WS,
      [["الغطاء الخرساني", "20 سم على كل جانب (الرسم: 20 | PIPE Ø | 20)"], ["الكم", "كم uPVC عند اختراق الجدار"]], ["القياسات بنسبة قطر الأنبوب"], conf="doc")
    D("det_valve_pit", "غرفة صمامات (Valve pit) 60×60 سم بغطاء حديد زهر 40×60", "Valve pit", P_, valve_pit(), {"W": 100, "D": 100, "H": 115}, SRC_WS,
      [["الغرفة", "60×60 سم داخليًا، عمق 50 سم (حسب الرسم)"], ["الغطاء", "حديد زهر متوسط التحمل 40×60 سم"], ["التجهيزات", "صمام عزل + مصفاة + نقطة أخذ عيّنة + مصرف تسريب (Soak away)"]], ["سماكة الجدران ومادة الغطاء التفصيلية: قياسية"])
    D("det_water_heater_install", "تركيب سخان المياه: مشبك L + صمام زاوية مخفي + صمام أمان إلى المصرف", "Water heater installation", P_, water_heater_install(), {"W": 120, "D": 40, "H": 135}, SRC_WS, [["العنوان", "INSTALLATION DETAIL OF WATER HEATER (منظر جانبي وخلفي)"], ["الملاحظة 12", "السخانات المخدومة بالمياه تكون مبطّنة بالزجاج (Glass lined)"]], ["مواضع الوصلات: من الشكل التخطيطي"])
    D("det_booster_pumps", "مضخات الرفع (Booster): مضختان عاملة/احتياط مع صمامات ووعاء ضغط", "Booster pumps connection", P_, booster_pump_set(), {"W": 230, "D": 100, "H": 100}, SRC_WS,
      [["الرموز", "IV عزل — NRV عدم رجوع — FC وصلة مرنة — ST مصفاة — PG مقياس — PS مفتاح ضغط — PV وعاء ضغط"], ["الخط الموازي", "Bypass pipe"], ["الحماية", "مجموعات الضخ تُحمى بخزانة ألمنيوم على قاعدة خرسانية ≥ 30 سم (ملاحظة 11)"]], ["قياسات المضخات والأنابيب: تقديرية"], conf="doc")
    D("det_transfer_pumps", "مضخة نقل (Transfer pump) مع مجمّعات الشفط والطرد", "Transfer pump connection", P_, transfer_pump_set(), {"W": 180, "D": 70, "H": 90}, SRC_WS, [["العنوان", "TRANSFER PUMP CONNECTION DETAILS"], ["التحكم", "مفتاح عوامة كهربائي من الخزان الأرضي"]], ["أقطار الأنابيب: تقديرية"])
    D("det_washbasin", "حوض غسيل: الحافة 85 سم + مخارج الماء عند +60 سم + مصيدة زجاجة", "Wash basin rough-in", P_, wash_basin(), {"W": 60, "D": 50, "H": 150}, SRC_WS, [["ارتفاع الحافة", "85 سم"], ["مخارج الماء", "+60 سم A.F.F.L. بتباعد 10 سم من كل جهة عن المحور"], ["الصمامات", "صمام زاوية + مصيدة زجاجة (Bottle trap)"]], ["أبعاد الحوض والخلّاط: قياسية"], conf="doc")
    D("det_water_closet", "مرحاض: صمام زاوية عند 15 سم وخزان طرد ملاصق", "Water closet rough-in", P_, water_closet(), {"W": 60, "D": 60, "H": 120}, SRC_WS, [["القياسات في الرسم", "150 / 400 / 75 / 200 مم (دون تسمية صريحة)"], ["مخرج الأرضية", "110 مم (DR-106)"]], ["إسناد الأرقام 150/400/75/200 للمكوّنات تفسير للرسم — يحتاج تأكيد"])
    D("det_bathtub", "حوض استحمام وخلّاط حائطي", "Bath tub", P_, bathtub(), {"W": 160, "D": 80, "H": 150}, SRC_WS, [["القياسات في الرسم", "700 / 0.53 (دون تسمية صريحة)"]], ["ارتفاع الخلّاط 70 سم وارتفاع الحافة: تفسير للرسم يحتاج تأكيد"])
    D("det_bidet", "شطّاف (Bidet): صمام زاوية عند 20 سم", "Bidet rough-in", P_, bidet(), {"W": 60, "D": 60, "H": 100}, SRC_WS, [["القياسات في الرسم", "75 / 200 مم"]], ["إسناد الأرقام للمكوّنات: تفسير يحتاج تأكيد"])
    D("det_floor_drain_typ", "مصرف أرضي — دور نموذجي (DR-106 تفصيل 03)", "Floor drain (typical floor)", P_, floor_drain(False), {"W": 70, "D": 70, "H": 50}, SRC_DR, [["الشبكة", "100×100 مم"], ["المصيدة", "UPVC trapped floor gully مع مدخلين مساعدين"], ["القطر (جدول DR-106)", "الأرضي FT: 82 مم (3″) بميل 1:40"]], ["شكل المصيدة الداخلي مبسّط"], conf="doc")
    D("det_floor_drain_ug", "مصرف أرضي تحت الأرض + وسادة خرسانية (DR-106 تفصيل 02)", "Floor drain below ground", P_, floor_drain(True), {"W": 70, "D": 70, "H": 50}, SRC_DR, [["الشبكة", "100×100 مم"], ["الوسادة", "Concrete pad تحت المصيدة"]], ["سماكة الوسادة: افتراض"], conf="doc")
    D("det_gully_trap", "مصيدة أرضية خارجية (Gully trap) — غطاء وإطار 300×300", "Gully trap", P_, gully_trap(), {"W": 60, "D": 60, "H": 50}, SRC_DR, [["الغطاء", "300×300 مم مع إطار + غطاء PVC محكم"], ["المحيط الخرساني", "100/150 مم"], ["القطر (جدول DR-106)", "GT → MH: 110 مم (4″) بميل 1:60"]], ["العمق التفصيلي: يختلف حسب الموقع (VARIES)"], conf="doc")
    D("det_manhole_90", "غرفة تفتيش حتى عمق 90 سم (DR-106 تفصيل 05)", "Manhole up to 90 cm", P_, manhole_90(), {"W": 110, "D": 110, "H": 100}, SRC_DR,
      [["القاعدة", "خرسانة 15 سم + نظافة 5 سم"], ["اللياسة", "20 مم بطبقتين + 3 طبقات بيتومين خارجًا"], ["التدريج (Benching)", "ميل 1:6 مدهون بسيليكات الصوديوم مرتين"], ["التعبئة تحت الغطاء", "خرسانة 10 سم درجة 2"]], ["سماكة الجدران 20 سم: افتراض"], conf="doc")
    D("det_catch_basin", "حوض تجميع (Catch basin) 450×450 مم بسلة GRP", "Catch basin", P_, catch_basin(), {"W": 80, "D": 60, "H": 55}, SRC_DR, [["الغطاء", "400 مم عرضًا بسماكة 50 مم (تحمّل ثقيل)"], ["السلة", "GRP مثقّبة 250 مم"], ["المخرج", "إلى خط ⌀150 مم رئيسي (Main WP)"]], ["ارتفاع الحوض ومواضع الثقوب: قياسية"], conf="doc")
    D("det_pump_chamber", "غرفة مضخات الصرف (Pump chamber) بمضختين غاطستين", "Sewage pump chamber", P_, pump_chamber(), {"W": 240, "D": 160, "H": 335}, SRC_DR,
      [["السكك", "ستانلس 316 مدهونة بالشحم + سلاسل رفع ستانلس 316"], ["فتحتا التفتيش", "غطاءان 900×600 مم (عدد 2)"], ["التهوية", "أنبوب 110 مم بغطاء مخروطي (Cowl)"], ["الطرد", "حديد مطاوع مطلي من الداخل والخارج"]], ["أبعاد الغرفة وارتفاعها: تقديرية (المخطط الأصلي بلا أبعاد كلية)"])
    D("det_stack_connection", "وصلة الرايزر/الماسورة الرأسية 110 مم (DR-106 تفصيل 09)", "Vertical stack connection", P_, stack_connection(), {"W": 120, "D": 60, "H": 175}, SRC_DR, [["الماسورة الرأسية", "110 مم Foul waste stack"], ["الدعم", "دعامة رأسية للأنبوب + سدادة وصول + لوحة وصول بالسقف"]], ["مواضع الدعامات الرأسية: من جدول التباعد"], conf="doc")
    D("det_pipe_support_drain", "دعامة أنبوب تصريف uPVC وجدول التباعد", "uPVC pipe support + spacing schedule", P_, pipe_support_drain(), {"W": 30, "D": 30, "H": 70}, SRC_DR,
      [["تباعد الدعامات الأفقي (م)", "⌀50: 1.10 — ⌀82: 1.40 — ⌀110: 1.50 — ⌀160: 1.80"], ["التباعد الرأسي (م)", "⌀50: 1.20 — ⌀82: 1.50 — ⌀110: 1.70 — ⌀160: 2.10"]], ["نوع المشبك: قياسي"], conf="doc")
    D("det_bedding_B", "فرشة خندق الأنبوب — فئة B (حبيبية)", "Pipe bedding class B", P_, pipe_bedding("B"), {"W": 120, "D": 80, "H": 90}, SRC_DR, [["جدول الفرشات", "0–600 تحت الطرق: O؛ داخل المباني/الأساسات: B؛ أخرى: O"], ["الفرشة B", "مادة حبيبية 150 مم على الأقل + ردم مختار بطبقات 150 مم"]], ["عرض الخندق: حسب المواصفات (غير مذكور)"], conf="doc")
    D("det_bedding_O", "فرشة خندق الأنبوب — فئة O (خرسانة)", "Pipe bedding class O", P_, pipe_bedding("O"), {"W": 120, "D": 80, "H": 90}, SRC_DR, [["الفرشة O", "إحاطة خرسانية درجة A بسماكة 150 مم على الأقل"], ["الاستخدام", "تحت الطرق وإذا كان ظهر الأنبوب ضمن 300 مم من بلاطة الأرضية"]], ["عرض الخندق: حسب المواصفات (غير مذكور)"], conf="doc")
    D("det_fcu_cond_trap", "مصيدة تكثيف FCU وتصريفها (DR-106 تفصيل 07)", "FCU condensate trap detail", P_, fcu_cond_trap(), {"W": 100, "D": 40, "H": 108}, SRC_DR, [["التفصيل", "FCU COND DRAIN CONNECTION — U-trap + وصلات فكّ لتنظيفها، متصلة بأقرب مصرف"]], ["قطر الأنبوب 25 مم: افتراض"], conf="doc")
    # ---------------- fire fighting
    D("det_alarm_check_valve", "صمام إنذار ACV ⌀150 مع الجرس المائي ومفتاح الضغط ومقياسي الضغط", "Alarm check valve assembly", F_, alarm_check_valve(), {"W": 110, "D": 50, "H": 190}, SRC_FF,
      [["الصمام", "150 مم مع Trim kit + غرفة تأخير + جرس إنذار مائي + مفتاح ضغط كهربائي + مقياسا ضغط (أعلى/أسفل)"], ["الربط", "واجهة مع نظام إنذار الحريق"], ["الكود", "UAE Life Safety Code 2018 / الفصل 9"]], ["أبعاد التركيب: من الشكل التخطيطي"], conf="doc")
    D("det_zone_control_valve", "صمام تحكم المنطقة بمفتاح تدفق وصمام اختبار وتصريف", "Zone control valve assembly", F_, zone_control_valve(), {"W": 150, "D": 40, "H": 70}, SRC_FF,
      [["الصمام", "150 مم مؤشّر (Indicating) أرضي بمفتاح مراقبة ومقياس ضغط"], ["الاختبار", "صمام اختبار + زجاجة رؤية + وصلة بفتحة معايَرة مكافئة لأصغر رشاش"], ["التصريف", "25 مم إلى رايزر التصريف"], ["الملاحظة", "أي منطقة بضغط > 12 بار تحتاج صمام تخفيض ضغط"]], ["الأطوال: من الشكل"], conf="doc")
    D("det_fire_pump_set", "مجموعة مضخات الإطفاء: كهربائية + تعويضية + ديزل بلوحة تحكم ووعاء ضغط", "Fire fighting pump set", F_, fire_pump_set(), {"W": 300, "D": 180, "H": 100}, SRC_FF,
      [["المضخات", "كهربائية 750 GPM (88 كيلوواط)، ديزل 750 GPM، تعويضية 40 GPM (5 كيلوواط)"], ["وعاء الضغط", "100 لتر"], ["المكوّنات", "صمام بوابة، عدم رجوع، وصلة مرنة، مقياس وضغط، خط اختبار"], ["الخزانات", "خزّانا إطفاء 2×22,500 غالون أمريكي"]], ["الترتيب المكاني والأقطار: من الشكل التخطيطي"], conf="doc")
    D("det_breeching_2way", "مدخل تنفس/إطفاء 4″ × اتجاهين — خزانة 600×400×300", "Breeching inlet 4\"x2-way", F_, breeching_inlet(False), {"W": 60, "D": 30, "H": 40}, SRC_FF, [["الخزانة", "سطحية 600(L)×400(H)×300(D) مم"], ["الموقع في المشروع", "FF-101: «2 NOS OF 4-WAY BREECHING INLET» عند الواجهة"]], ["لون الخزانة وتفاصيل الوصلات: قياسية"], conf="doc")
    D("det_breeching_4way", "مدخل تنفس/إطفاء 6″ × 4 اتجاهات — خزانة 600×600×300", "Breeching inlet 6\"x4-way", F_, breeching_inlet(True), {"W": 60, "D": 30, "H": 60}, SRC_FF, [["الخزانة", "سطحية 600(L)×600(H)×300(D) مم"], ["الموقع في المشروع", "FF-101 — FF-105: رايزر Breeching"]], ["لون الخزانة وتفاصيل الوصلات: قياسية"], conf="doc")
    D("det_sprinkler_hanger", "حامل أنبوب الرشاشات: قضيب G.I. + حلقة دوّارة + مرساة تمدد", "Sprinkler pipe hanger", F_, sprinkler_hanger(), {"W": 30, "D": 40, "H": 80}, SRC_FF, [["القضيب", "M10 / M12 مسنن من G.I."], ["المسافة من أسفل البلاطة", "من 25 مم إلى 305 مم كحد أقصى"], ["التثبيت", "مرساة تمدد M10/M12"]], ["قطر الأنبوب 25–100 مم: حسب الشبكة"], conf="doc")
    D("det_sprinkler_sidewall", "رشاش جانبي (Sidewall) مع مانع تسرّب مقاوم للحريق", "Sidewall sprinkler", F_, sprinkler_sidewall(), {"W": 60, "D": 40, "H": 100}, SRC_FF, [["الفرع", "25 مم من خط الرش + قضيب M10 من البلاطة"], ["الإحكام", "Fire rated caulking عند الجدار"]], ["درجة حرارة البصيلة 68°م: قياسية"], conf="doc")
    for kind, kg, ar, en in (("co2", 5, "طفاية ثاني أكسيد الكربون CO₂ — 5 كجم", "CO2 extinguisher 5 kg"), ("co2", 12, "طفاية CO₂ على عجلات — 12 كجم", "Wheeled CO2 extinguisher 12 kg"), ("dcp", 4, "طفاية بودرة جافة متعددة الأغراض — 4 كجم", "ABC powder extinguisher 4 kg"), ("dcp", 6, "طفاية بودرة جافة متعددة الأغراض — 6 كجم", "ABC powder extinguisher 6 kg")):
        D(f"det_ext_{kind}_{kg}", ar, en, F_, extinguisher(kind, kg), {"W": 26 if kg <= 6 else 36, "D": 26 if kg <= 6 else 36, "H": 60 if kg <= 6 else 100}, SRC_FF,
          [["جدول الطفايات", "غرفة المحول/HV: CO₂ 12 كجم على عجلات؛ ممرات: CO₂ 5 كجم + بودرة 4 كجم؛ غرفة كهرباء/LV: CO₂ 5 كجم؛ مطبخ: بودرة 2.5 + CO₂ 5؛ نفايات: بودرة 6 كجم"]], ["الألوان والمقابض: قياسية"], conf="doc")
    # ---------------- electrical
    D("det_transformer_dry", "محوّل جاف 1000 kVA — 22/0.415 kV بغلاف وصناديق كابلات HV/LV", "Dry-type transformer 1000 kVA", E_, transformer_dry(), {"W": 400, "D": 170, "H": 320}, SRC_EP,
      [["الأبعاد من الجدول", "الطول 4000 × العرض 1700 × الارتفاع 3200 مم"], ["القدرة والجهد", "1000 kVA، 22 kV / 0.415 kV، ثلاثي الطور (المخطط الأحادي EP-107)"], ["صندوق LV", "80 سم (مسقط EP-108)"]], ["إسناد جدول EP-108 للمحوّل: ترتيب الجدول ملتبس (يحتاج تأكيد)", "الملفات الراتنجية وعدد الشرائح: قياسية"], conf="derived")
    D("det_hv_switchgear", "لوحة قواطع 22 kV (3 خلايا: مغذٍّ — محوّل — مغذٍّ)", "22 kV switchgear line-up", E_, hv_switchgear_22kv(), {"W": 270, "D": 250, "H": 235}, SRC_EP,
      [["أبعاد الخلية (الجدول)", "الطول 2500 × العرض 900 × الارتفاع 2350 مم"], ["الترتيب في المسقط", "FEEDER | TRANSFORMER | FEEDER بعرض 90 سم لكل خلية"], ["غرفة HV", "A = 30.20 م²، F.F.L. +0.90"]], ["تفسير «الطول 2500» كعمق الخلية (المسقط: 250 سم عمق) — يحتاج تأكيد", "عدد الخلايا الفعلي"], conf="derived")
    D("det_lv_metering", "لوحة قياس الجهد المنخفض LV Metering panel", "LV metering panel", E_, lv_metering_panel(), {"W": 60, "D": 80, "H": 180}, SRC_EP, [["الأبعاد (الجدول)", "الطول 600 × العرض 800 × الارتفاع 1800 مم"]], ["عدد العدّادات وتفاصيل الغلاف: قياسية"], conf="derived")
    D("det_dms_rtu", "وحدة RTU لنظام إدارة التوزيع DMS", "DMS RTU cabinet", E_, dms_rtu(), {"W": 100, "D": 30, "H": 100}, SRC_EP, [["الأبعاد (الجدول)", "الطول 1000 × العرض 300 × الارتفاع 1000 مم"]], ["تركيب جداري: من موضعها في مسقط غرفة HV"], conf="derived")
    D("det_battery_rack", "رف بطاريات 48 فولت", "Battery rack", E_, battery_rack(), {"W": 120, "D": 50, "H": 129}, SRC_EP, [["الأبعاد (الجدول)", "الطول 1200 × العرض 500 × الارتفاع 1290 مم"]], ["نوع البطاريات وعددها: غير مذكوران (VRLA مفترض)"], conf="derived")
    D("det_dc_supply", "مزوّد قدرة 48 فولت DC", "48 V DC supply", E_, dc_supply_48v(), {"W": 82, "D": 60, "H": 208}, SRC_EP, [["الأبعاد (الجدول)", "الطول 820 × العرض 600 × الارتفاع 2082 مم"]], ["عدد وحدات المقوّم: افتراض"], conf="derived")
    D("det_mdb_2000a", "اللوحة الرئيسية MDB 2000 أمبير (Form 4 Type 6)", "Main distribution board", E_, mdb_2000a(), {"W": 320, "D": 80, "H": 200}, SRC_EP + ["ELEC1 ص16: المخطط الأحادي SLD"],
      [["الأبعاد", "320 × 80 × 200 سم (EP-108)"], ["القاطع الرئيسي", "ACB 2000 أمبير TPN"], ["القضبان", "نحاس مقلّون 2000 أمبير 4P"], ["قدرة القطع", "50 كيلو أمبير، IP54"]], ["عدد الخلايا (8) وتوزيعها: افتراض"], conf="derived")
    D("det_generator", "مجموعة مولّد ديزل ~200 kVA بالشاسيه وخزان الوقود", "Diesel generator set", E_, generator_set(), {"W": 260, "D": 110, "H": 190}, SRC_EP + ["ELEC1 ص16: SLD (ATS / مولّد)"],
      [["مسقط المولّد", "260 × 110 سم (EP-108)"], ["غرفة المولّد", "A = 11.50 م²، F.F.L. +0.35"], ["التهوية", "حسب توصية المصنّع (ملاحظة EP-108)"]], ["القدرة (≈200 kVA) من ATS في المخطط الأحادي — يحتاج تأكيد", "الارتفاع 190 سم وتفاصيل المحرك: افتراض"], conf="derived")
    D("det_smdb_enclosure", "لوحة SMDB + خزانة عدّادات الوحدات (6 عدّادات) بنوافذ بيرسبكس", "SMDB with kWh meter enclosure", E_, smdb_meter_enclosure(), {"W": 80, "D": 18, "H": 200}, SRC_EP + SRC_EG,
      [["عدد العدّادات", "6 عدّادات kWh (6 Nos)"], ["الغلاف", "ألمنيوم/فولاذ يطابق SMDB وDB — باب بنوافذ بيرسبكس شفافة مقسّاة لقراءة DEWA"], ["الداخل", "قنوات كابلات مفردة داخل الغلاف"], ["ارتفاع قمة اللوحة", "180 سم من الأرضية"]], ["ترتيب العدّادات 3×2 وأبعاد النوافذ: افتراض"], conf="derived")
    D("det_cable_tray", "تركيب صينية كابلات مجلفنة بالغمس الساخن بغطاء مغلق وذراع حامل", "Cable tray typical installation", E_, cable_tray_installation(), {"W": 100, "D": 60, "H": 70}, SRC_EG, [["العنوان", "CABLE TRAY TYPICAL INSTALLATION DETAILS (EP-109)"], ["المكوّنات", "صينية + غطاء G.I. مغلق + ذراع حامل + MS hank bush"], ["المعدن", "حديد مجلفن بالغمس الساخن (Hot dip galvanized)"]], ["قياس الصينية (60×5 سم): مثال، المسقط يذكر صينية 800×50 مم في غرفة الكهرباء"], conf="doc")
    D("det_downlight_install", "تركيب كشاف غاطس: علبة PVC مدفونة + محوّل + قابلو مرن 3C×2.5", "Down-light fixing detail", E_, downlight_install(), {"W": 60, "D": 60, "H": 70}, SRC_EG,
      [["علبة البلاطة", "علبة PVC دائرية 20 مم مدفونة في الخرسانة"], ["التوصيل", "وصلة PVC 20 مم + صامولة قفل بمشبك + ماسورة مرنة 20 مم"], ["السلك", "3C × 2.5 مم² مرن"]], ["قياس الكشاف الغاطس: حسب نوعه (TYPE-8: 26 واط)"], conf="doc")
    D("det_fa_detector", "تثبيت كاشف دخان/حرارة على السقف المستعار (FA-108)", "Detector fixing detail", E_, fa_device_mount("detector"), {"W": 80, "D": 40, "H": 345}, SRC_EG + ["ELEC2 ص10: FA-108"], [["الأنبوب", "PVC مخفي 25 مم + علبة دائرية"], ["الكابل", "FP200 مقاوم للحريق"], ["الكاشف", "ضوئي (Optical) دخان/حرارة على السقف المستعار"]], ["ارتفاع السقف 2.7 م: من الدور النموذجي"], conf="doc")
    D("det_fa_speaker", "مكبّر صوت/وامض على ارتفاع 2300 مم (FA-108)", "Speaker / flasher fixing", E_, fa_device_mount("speaker"), {"W": 80, "D": 40, "H": 345}, SRC_EG + ["ELEC2 ص10: FA-108"], [["الارتفاع", "2300 مم فوق الأرضية (تحت السقف المستعار)"], ["التمديد", "قناتان PVC مخفيتان 25 مم في الجدار + علبة خلفية"]], ["القياس 12×12 سم: افتراض"], conf="doc")
    D("det_fa_pull_station", "نقطة كسر زجاج يدوية على ارتفاع 1400 (±200) مم (FA-108)", "Manual pull station fixing", E_, fa_device_mount("pull"), {"W": 80, "D": 40, "H": 345}, SRC_EG + ["ELEC2 ص10: FA-108"], [["الارتفاع", "1400 مم ± 200"], ["التمديد", "PVC مخفي 25 مم + علبة دائرية + علبة خلفية"]], ["القياس 12×12 سم: افتراض"], conf="doc")
    D("det_fa_telephone_jack", "مقبس هاتف الإطفاء (مخفي) — 1250 مم (FA-108)", "Fire telephone jack fixing", E_, fa_device_mount("tel"), {"W": 80, "D": 40, "H": 345}, SRC_EG + ["ELEC2 ص10: FA-108"], [["الارتفاع", "1250 مم (وارتفاع الفتحة 700 مم في الرسم)"], ["التمديد", "PVC مخفي 25 مم في العمود/الجدار"]], ["القياس 12×12 سم: افتراض"], conf="doc")
    D("det_exit_light_install", "تركيب كشاف مخرج الطوارئ EXIT فوق الباب (FA-108)", "Exit light fitting installation", E_, exit_light_install(), {"W": 120, "D": 40, "H": 345}, SRC_EG + ["ELEC2 ص10: FA-108"], [["السلك", "2×2.5 مم² PVC / LSF على ماسورة GI فوق البلاطة"], ["التوصيل", "ماسورة مرنة + غدّة PG بصامولة قفل"]], ["ارتفاع التركيب فوق الباب: افتراض"], conf="doc")
    D("det_earth_pit", "حفرة تأريض وموصل نزول: قضيب نحاس 20×1200 + قضيب أرضي بخمس فتحات", "Down conductor & earth pit", E_, earth_pit_detail(), {"W": 120, "D": 80, "H": 150}, ["ELEC2 ص17: LPT-106 (تفصيل A)"],
      [["الموصل", "شريط نحاس عارٍ 25×3 مم على السطح والسور والعمود"], ["القضيب", "نحاس مصمت 20 × 1200 مم يُدقّ حتى مقاومة < 10 أوم"], ["الحفرة", "خرسانية مع قضيب أرضي بخمس فتحات EBC 05 ونقطة اختبار"], ["الربط", "كابل 1C×70 مم² للتوصيل مع الحفرة التالية"], ["الحماية", "ماسورة PVC ⌀50 مم"]], ["أبعاد الحفرة: افتراض"], conf="doc")
    D("det_air_terminal", "قضيب صاعقة حر الوقوف بقاعدة خرسانية وحامل ثلاثي", "Free-standing air terminal", E_, air_terminal_free_standing(), {"W": 60, "D": 60, "H": 305}, ["ELEC2 ص17: LPT-106 (تفصيلا F وH)"],
      [["الحامل الثلاثي", "ATS 001 على قاعدة خرسانية"], ["الرأس", "نقاط متعددة MPC 16 على قضيب ASGL 16M"], ["الزاوية الواقية (LPS III)", "76.3° عند ارتفاع 1 م — نصف قطر 4.0 م؛ 74.1° عند 3 م — 10.3 م"]], ["ارتفاع القضيب (3 م): افتراض من الجدول (ارتفاع القضيب عن مستوى المرجع)"], conf="derived")
    D("det_dc_tape_clip", "تثبيت شريط النحاس على السور: مشابك DC معدنية ومشبك مربّع", "Metallic DC tape clip on parapet", E_, dc_tape_clip(), {"W": 80, "D": 20, "H": 46}, ["ELEC2 ص17: LPT-106 (تفصيلا I وM)"], [["الموصل", "شريط نحاس 25×3 مم"], ["المشابك", "DC tape clip معدني + Square tape clamp (JG 253) + شريط TC253"]], ["تباعد المشابك: افتراض"], conf="doc")
    return out

RULES = []
