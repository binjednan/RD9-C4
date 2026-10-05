# -*- coding: utf-8 -*-
"""path samples: the sample is built once per straight segment in a local frame (x along the pipe/duct from 0 to L, y up, z across).
Variables: L (segment length, cm), Dp (pipe diameter, cm) or W,H (duct cross-section, cm). 'vparts' are placed at inner vertices (bends)."""
from .lib import *

def _pipe(c, Dp="Dp", jacket=None, jc="#2a2a2a", coupling=None, cc="#d62828", hanger_every=300, joint_every=600, rod="Hg", stripe=None, name="أنبوب"):
    rod = "Hg"   # hanger rod length = real distance to the soffit (element attribute hang_cm), 12 cm by default
    R = f"({Dp}/2)"
    P = [cyl((0, 0, 0), f"{Dp}/2", "L", c, "gloss", ax="x", seg=16, n=f"{name} (جسم الأنبوب)")]
    if stripe: P.append(cyl((0, 0, 0), f"{Dp}/2+0.04", "L", stripe, "gloss", ax="x", seg=16, caps=False, n="خط تمييز على الأنبوب"))
    if jacket:
        P.append(cyl((0, 0, 0), f"{Dp}/2+{jacket}", "L", jc, "rubber", ax="x", seg=16, n=f"عزل مطاطي مغلق الخلايا (سماكة {jacket} سم)"))
    top = f"({Dp}/2+{jacket or 0})"
    # hangers
    n_h = f"max(1,ceil(L/{hanger_every}))"
    P += [rep(tor((f"L/(2*{n_h})", 0, 0), f"{top}+0.35", 0.28, "#8e949c", m="metal", ax="x", seg=14, n="طوق التعليق (Clevis hanger ring)"), f"Hg>0?{n_h}:0", (f"L/{n_h}", 0, 0)),
          rep(cyl((f"L/(2*{n_h})", f"{top}+0.6", 0), 0.5, rod, "#aab0b8", "metal", n="قضيب تعليق مسنن M10"), f"Hg>0?{n_h}:0", (f"L/{n_h}", 0, 0)),
          rep(box((f"L/(2*{n_h})-3", f"{top}+0.6+{rod}", -3), (f"L/(2*{n_h})+3", f"{top}+0.6+{rod}+0.5", 3), "#8e949c", "metal", n="لوح تثبيت بالبلاطة (Anchor plate)"), f"Hg>0?{n_h}:0", (f"L/{n_h}", 0, 0))]
    P += [rep(cyl((f"L/(2*{n_h})", f"-{top}-St", 0), 1.0, "St", "#6f757c", "metal", seg=10, n="قائم دعم أنبوب على السطح (Pipe stand — AC D-32)"), f"St>0?{n_h}:0", (f"L/{n_h}", 0, 0)),
          rep(cyl((f"L/(2*{n_h})", f"-{top}-St-0.6", 0), 4.0, 0.6, "#8e949c", "metal", seg=12, n="لوحة قاعدة القائم"), f"St>0?{n_h}:0", (f"L/{n_h}", 0, 0))]
    if coupling:
        n_j = f"floor(L/{joint_every})"
        P += [rep(cyl((f"{joint_every}", 0, 0), f"{top}+0.9", 5.5, coupling, "gloss", ax="x", seg=18, n="وصلة مجرّزة (Grooved coupling)"), n_j, (f"{joint_every}", 0, 0)),
              rep(box((f"{joint_every}-1", f"{top}+0.7", -1.2), (f"{joint_every}+1", f"{top}+1.5", 1.2), "#444", "metal", n="برغي الوصلة"), n_j, (f"{joint_every}", 0, 0))]
    return P

def _vparts(Dp="Dp", jacket=None, c="#888", cc=None):
    r = f"({Dp}/2+{jacket or 0})*1.02"
    return [sph((0, 0, 0), 1, c, s=[r, r, r], seg=10, m="gloss", n="كوع / وصلة تغيير اتجاه (Elbow fitting)")]

def make():
    out = {}
    def add(t): out[t[0]] = t[1]
    def P(id_, name, en, cat, parts, vparts=None, conf="derived", facts=None, asm=None, src=None, dims=None, lod=7.0):
        t = sample(id_, name, en, cat, parts, kind="path", place={"mode": "path"}, lod=lod, conf=conf, src=src or [], facts=facts or [], asm=asm or [], dims=dims or {}, defaults={"Hg": 12, "St": 0})
        if vparts: t[1]["vparts"] = vparts
        add(t)
    A_H = "منسوب التمديد وطول قضبان التعليق (12 سم) وتباعد المعلّقات: افتراض (تفصيل تنفيذي قياسي، غير مرسوم)"
    # ---- fire fighting (black steel, red painted)
    P("pipe_ff", "أنبوب شبكة الرشاشات (فولاذ أسود Sch40 مدهون أحمر)", "Sprinkler pipe (black steel Sch40, red)", "fire", _pipe("#c0281f", coupling="#b3261e", hanger_every=300, joint_every=600),
      vparts=_vparts(c="#a8231b"), facts=[["المادة", "فولاذ أسود (M_FF_PIPE)"], ["القطر", "من وسم المخطط (25–150 مم)"], ["الوصلات", "مجرّزة (Grooved) كل 6 م"]], asm=[A_H, "نوع الوصلات (مجرّزة/لحام/سنّ) غير مذكور؛ عُرض مجرّز قياسيًا"], src=["MECH2: مخططات الإطفاء FF-100..105"], dims={"L": 300, "Dp": 8})
    P("pipe_ffc", "أنبوب خط صناديق الإطفاء FFC (فولاذ أسود 6″)", "FFC hose-cabinet line (black steel 6\")", "fire", _pipe("#1f5fbf", coupling="#17428a", hanger_every=300, joint_every=600),
      vparts=_vparts(c="#17428a"), facts=[["القطر", "6″ (150 مم) — مخطط FF-105"], ["اللون", "أزرق (تمييز خط الخراطيم)"]], asm=[A_H, "لون التمييز: افتراض"], src=["MECH2 ص15: FF-105"], dims={"L": 300, "Dp": 15})
    P("riser_spr", "رايزر شبكة الرشاشات 6″ (رأسي)", "Sprinkler riser 6\"", "fire", _pipe("#c0281f", coupling="#b3261e", hanger_every=360, joint_every=600, rod=8), conf="derived",
      facts=[["القطر", "6″"], ["الرمز", "دائرة 15.7 سم على M_FF_PIPE"]], asm=["تخصيص الجاف/الرطب غير مرسوم"], src=["MECH2 ص10-14"], dims={"L": 350, "Dp": 15})
    P("riser_ffc", "رايزر خط FFC 6″ (رأسي)", "FFC riser 6\"", "fire", _pipe("#1f5fbf", coupling="#17428a", hanger_every=360, joint_every=600, rod=8), facts=[["القطر", "6″"]], asm=["تخصيص الجاف/الرطب غير مرسوم"], src=["MECH2 ص10-14"], dims={"L": 350, "Dp": 15})
    P("pipe_suction", "خط شفط مضخات الإطفاء 6″", "Fire pump suction line 6\"", "fire", _pipe("#c0281f", coupling="#b3261e", hanger_every=300, joint_every=600, rod=8), facts=[["القطر", "6″"]], asm=["منسوب الخط داخل الخزان وعند المضخات: افتراض"], src=["MECH2 ص10-11"], dims={"L": 350, "Dp": 15})
    # ---- plumbing
    P("pipe_cold", "أنبوب مياه باردة PPR/PEX", "Cold water pipe PPR", "plumbing", _pipe("#3a86d9", stripe="#ffffff", hanger_every=120, joint_every=400, rod=10, coupling=None) + [rep(cyl(("400", 0, 0), "Dp/2+0.45", 2.2, "#2f78c7", "gloss", ax="x", seg=14, n="وصلة اندماج (Fusion socket)"), "floor(L/400)", ("400", 0, 0))],
      vparts=_vparts(c="#2f78c7"), facts=[["المادة", "PPR/PEX (M_WS_CW)"], ["الوصلات", "اندماج حراري"]], asm=[A_H, "نوع المادة (PPR/PEX) حسب مفتاح الطبقة"], src=SRC if False else ["MECH2: مخططات التغذية بالمياه WS"], dims={"L": 300, "Dp": 2.2})
    P("pipe_hot", "أنبوب مياه ساخنة PPR معزول", "Hot water pipe PPR insulated", "plumbing", _pipe("#d94a2a", jacket=1.3, jc="#2a2a2a", hanger_every=120, joint_every=400, rod=10), vparts=_vparts(jacket=1.3, c="#222"),
      facts=[["المادة", "PPR مستقر (M_WS_HW)"], ["العزل", "مطاطي مغلق الخلايا — ملاحظة عامة: «Hot water pipes shall be insulated»"]], asm=[A_H, "سماكة العزل 13 مم: افتراض"], src=["MECH2: مخططات WS (الملاحظة العامة 1)"], dims={"L": 300, "Dp": 2.2})
    P("pipe_waste", "أنبوب صرف (Waste) UPVC", "Waste pipe UPVC", "plumbing", _pipe("#b79a64", hanger_every=120, joint_every=300, rod=8, coupling="#a8895a"), vparts=_vparts(c="#a8895a"), facts=[["المادة", "UPVC (M_DR_WP)"]], asm=[A_H, "القطر افتراضي حسب نوع الخط (التسميات بالبوصة عند الأعمدة فقط)"], src=["MECH2: مخططات الصرف DR"], dims={"L": 300, "Dp": 8})
    P("pipe_soil", "أنبوب صرف (Soil) UPVC", "Soil pipe UPVC", "plumbing", _pipe("#8a6a3a", hanger_every=120, joint_every=300, rod=8, coupling="#7a5a2f"), vparts=_vparts(c="#7a5a2f"), facts=[["المادة", "UPVC (M_DR_SP)"]], asm=[A_H, "القطر افتراضي حسب نوع الخط"], src=["MECH2: مخططات الصرف DR"], dims={"L": 300, "Dp": 11})
    P("pipe_vent", "أنبوب تهوية UPVC", "Vent pipe UPVC", "plumbing", _pipe("#c4b885", hanger_every=150, joint_every=300, rod=8, coupling="#b0a470"), vparts=_vparts(c="#b0a470"), facts=[["المادة", "UPVC (M_DR_VP)"]], asm=[A_H], src=["MECH2: مخططات الصرف DR"], dims={"L": 300, "Dp": 5})
    # ---- stair hand rail (A604): stainless tube + wall-stub brackets (assumed spec)
    hr = [cyl((0, 0, 0), "Dp/2", "L", "#c9ced4", "metal", ax="x", seg=14, n="أنبوب الدرابزين ستانلس ⌀48 مم (افتراض)"),
          cyl((0, 0, 0), "Dp/2+0.05", 0.4, "#aab0b8", "metal", ax="x", seg=14, n="غطاء طرف الأنبوب"),
          rep(cyl(("L/(2*max(1,ceil(L/120)))", "-Dp/2-3", 0), 0.8, 6, "#aab0b8", "metal", n="ذراع تثبيت (Bracket) — افتراض"), "max(1,ceil(L/120))", ("L/max(1,ceil(L/120))", 0, 0)),
          rep(cyl(("L/(2*max(1,ceil(L/120)))", "-Dp/2-3.5", 0), 2.0, 0.8, "#8e949c", "metal", n="لوحة تثبيت دائرية"), "max(1,ceil(L/120))", ("L/max(1,ceil(L/120))", 0, 0))]
    P("stair_handrail", "درابزين ستانلس للدرج الخارجي 03", "Stair hand rail (stainless)", "architecture", hr, vparts=_vparts(Dp="Dp", c="#aab0b8"), conf="assumed",
      facts=[["الارتفاع", "قمة الجدار H.L +1.40 م (A604)"], ["الأنبوب", "ستانلس ⌀48 مم (افتراض)"]], asm=["مواصفات الدرابزين وارتفاعه غير مذكورة — افتراض يحتاج تأكيد"], src=["ARCH2 ص5 (A604)", "ARCH2: تفاصيل الدرابزين A605"], dims={"L": 300, "Dp": 4.8})
    # ---- chilled water (insulated)
    P("pipe_chws", "أنبوب مياه مبردة — تغذية (معزول)", "Chilled water supply pipe (insulated)", "mechanical", _pipe("#2d8bd6", jacket=2.5, jc="#2b2e33", hanger_every=200, joint_every=600, rod=10) + [rep(cyl(("200", 0, 0), "Dp/2+2.55", 3.0, "#b8bcc2", "metal", ax="x", seg=14, n="شريط حاجز بخار / وصلة عزل"), "floor(L/200)", ("200", 0, 0))],
      vparts=_vparts(jacket=2.5, c="#2b2e33"), facts=[["الاتجاه", "تغذية 7 م°"], ["العزل", "مطاطي مغلق الخلايا 25 مم"]], asm=[A_H, "سماكة العزل 25 مم: افتراض"], src=["MECH1: مخططات CHW-100..104", "MECH1 ص16: مخطط CHW-105"], dims={"L": 300, "Dp": 3.2})
    P("pipe_chwr", "أنبوب مياه مبردة — رجوع (معزول)", "Chilled water return pipe (insulated)", "mechanical", _pipe("#e07b39", jacket=2.5, jc="#2b2e33", hanger_every=200, joint_every=600, rod=10) + [rep(cyl(("200", 0, 0), "Dp/2+2.55", 3.0, "#b8bcc2", "metal", ax="x", seg=14, n="شريط حاجز بخار / وصلة عزل"), "floor(L/200)", ("200", 0, 0))],
      vparts=_vparts(jacket=2.5, c="#2b2e33"), facts=[["الاتجاه", "رجوع 12 م°"], ["العزل", "مطاطي مغلق الخلايا 25 مم"]], asm=[A_H, "سماكة العزل 25 مم: افتراض"], src=["MECH1: مخططات CHW-100..104"], dims={"L": 300, "Dp": 3.2})
    # ---- duct
    duct = [box((0, "-H/2", "-W/2"), ("L", "H/2", "W/2"), "#b9c2ca", "metal", n="مجرى صاج مجلفن (G.I. duct)"),
            box((0, "H/2", "-W/2-0.0"), ("L", "H/2+2.5", "W/2"), "#dcd7c8", "matte", n="عزل حراري للمجرى (فوم/ألياف مبطّنة بقصدير) 25 مم"),
            box((0, "-H/2-2.5", "-W/2"), ("L", "-H/2", "W/2"), "#dcd7c8", "matte"),
            box((0, "-H/2", "W/2"), ("L", "H/2", "W/2+2.5"), "#dcd7c8", "matte"), box((0, "-H/2", "-W/2-2.5"), ("L", "H/2", "-W/2"), "#dcd7c8", "matte"),
            rep(box(("120-0.0", "-H/2-3.2", "-W/2-3.2"), ("120+3", "H/2+3.2", "W/2+3.2"), "#8e949c", "metal", n="شفة وصل عرضية (TDC flange) كل 1.2 م"), "floor(L/120)", ("120", 0, 0)),
            rep(box(("150/2*0+L/(2*max(1,ceil(L/150)))-2", "-H/2-3.2", "-W/2-6"), ("L/(2*max(1,ceil(L/150)))+2", "-H/2-1.2", "W/2+6"), "#6f757c", "metal", n="عارضة تعليق زاوية (Trapeze angle 40×40)"), "Hg>0?max(1,ceil(L/150)):0", ("L/max(1,ceil(L/150))", 0, 0)),
            rep(cyl(("L/(2*max(1,ceil(L/150)))", "H/2+2.6", "-W/2-5.2"), 0.5, "Hg", "#aab0b8", "metal", n="قضيب تعليق M10 — الطول = المسافة إلى البلاطة"), "Hg>0?max(1,ceil(L/150)):0", ("L/max(1,ceil(L/150))", 0, 0)),
            rep(cyl(("L/(2*max(1,ceil(L/150)))", "H/2+2.6", "W/2+5.2"), 0.5, "Hg", "#aab0b8", "metal"), "Hg>0?max(1,ceil(L/150)):0", ("L/max(1,ceil(L/150))", 0, 0)),
            rep(cyl(("L/(2*max(1,ceil(L/150)))", "-H/2-3.2-St", "-W/2-5.2"), 1.0, "St", "#6f757c", "metal", seg=10, n="قائم دعم مجرى على السطح"), "St>0?max(1,ceil(L/150)):0", ("L/max(1,ceil(L/150))", 0, 0)),
            rep(cyl(("L/(2*max(1,ceil(L/150)))", "-H/2-3.2-St", "W/2+5.2"), 1.0, "St", "#6f757c", "metal", seg=10), "St>0?max(1,ceil(L/150)):0", ("L/max(1,ceil(L/150))", 0, 0))]
    P("duct_supply", "مجرى هواء تغذية معزول (صاج مجلفن)", "Insulated supply air duct (GI)", "mechanical", duct, vparts=[box(("-W/2-3.5", "-H/2-3.5", "-W/2-3.5"), ("W/2+3.5", "H/2+3.5", "W/2+3.5"), "#b9c2ca", "metal", n="كوع المجرى (Duct elbow)")],
      conf="derived", facts=[["المقاس", "من وسم المخطط (W×H مم → سم)"], ["الوصلات", "شفة TDC كل 1.2 م"]], asm=["منسوب المجرى (القمة عند 3.10 م) وتباعد المعلّقات 1.5 م وسماكة العزل 25 مم: افتراض"], src=["MECH1: مخططات AC-100..105 (طبقة M_HVAC_SAD)"], dims={"L": 300, "W": 40, "H": 25})
    return out

RULES = [{"c": c, "t": t, "s": t} for c, t in (("P.ff", "pipe_ff"), ("P.ff", "pipe_ffc"), ("P.ff", "riser_spr"), ("P.ff", "riser_ffc"), ("P.ff", "pipe_suction"), ("P.cold", "pipe_cold"), ("P.hot", "pipe_hot"),
         ("P.drain", "pipe_waste"), ("P.drain", "pipe_soil"), ("P.drain", "pipe_vent"), ("M.pipe", "pipe_chws"), ("M.pipe", "pipe_chwr"), ("M.duct", "duct_supply"), ("A.rail", "stair_handrail"))]
