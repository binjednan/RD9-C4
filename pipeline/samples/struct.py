# -*- coding: utf-8 -*-
"""structural samples with the reinforcement of the column / wall schedules (STR p25-26 'COLUMN SCHEDULE 1/2', S-20), shown inside a ghost concrete body.
Bars: number and diameter from the schedule, spread evenly along the inside perimeter; links at the schedule spacing (10 cm in the end zones, 15 cm mid-height).
Cover 40 mm is a typical value (not stated in the extracted notes). All bars are round cylinders; every link is a hoop of four round legs whose outer face sits at the cover, with the main bars inside it (no solid plates). Beams / slabs / raft details are typical sections from the general details (S-22, S-8)."""
from .lib import *

REBAR = "#6b4a2f"; TIE = "#7a5a3a"
SRC_C = ["STR ص25-26: جداول الأعمدة والجدران (S-20) — عدد القضبان وأقطارها وتباعد الكانات", "STR ص2: تفاصيل الأعمدة النموذجية (مناطق الكانات)", "STR ص1: مواصفة الخرسانة (Fcu 40 N/mm²، Fy 460 N/mm²)"]

def _s(N):          # distance along the perimeter for bar i
    return f"((i+0.5)*P/{N})"

def column(N, db, link, sp_mid=15, sp_end=10, cover=4.0):
    # all bars are ROUND (cylinders): main bars inside the link hoops, hoops = four round legs; the outer face of a hoop sits at the concrete cover
    s = _s(N)
    x = f"({s}<Wi ? -Wi/2+{s} : ({s}<Wi+Di ? Wi/2 : ({s}<2*Wi+Di ? Wi/2-({s}-Wi-Di) : -Wi/2)))"
    z = f"({s}<Wi ? -Di/2 : ({s}<Wi+Di ? -Di/2+({s}-Wi) : ({s}<2*Wi+Di ? Di/2 : Di/2-({s}-2*Wi-Di))))"
    r = db / 20.0; lr = link / 20.0
    P = [box(("-W/2", 0, "-D/2"), ("W/2", "H", "D/2"), "#b4b4ae", "ghost", n=f"جسم الخرسانة المسلّحة (شفاف لإظهار التسليح) — Fcu 40")]
    P += [rep(cyl((x, 3.0, z), r, "H-6", REBAR, "metal", seg=10, n=f"قضيب رئيسي مستدير T{db} — {N} قضيبًا حسب الجدول"), N, (0, 0, 0))]
    # links: end zones (bottom, top) every sp_end, middle every sp_mid; each link = a hoop of 4 round legs (two along x, two along z)
    hx, hz = f"(W/2-{cover}-{lr})", f"(D/2-{cover}-{lr})"
    def ring(y_expr, step_expr, n_expr, nm):
        y = f"({y_expr})+{lr}"
        return [rep(cyl((f"-{hx}", y, f"-{hz}"), lr, f"2*{hx}", TIE, "metal", ax="x", seg=8, n=nm), n_expr, (0, step_expr, 0)),
                rep(cyl((f"-{hx}", y, f"{hz}"), lr, f"2*{hx}", TIE, "metal", ax="x", seg=8), n_expr, (0, step_expr, 0)),
                rep(cyl((f"-{hx}", y, f"-{hz}"), lr, f"2*{hz}", TIE, "metal", ax="z", seg=8), n_expr, (0, step_expr, 0)),
                rep(cyl((f"{hx}", y, f"-{hz}"), lr, f"2*{hz}", TIE, "metal", ax="z", seg=8), n_expr, (0, step_expr, 0))]
    He = "min(60,H/3)"
    P += ring("4", f"{sp_end}", f"round({He}/{sp_end})", f"كانة T{link} كل {sp_end} سم (منطقة النهاية السفلية)")
    P += ring(f"H-4-{He}", f"{sp_end}", f"round({He}/{sp_end})", f"كانة T{link} كل {sp_end} سم (منطقة النهاية العلوية)")
    P += ring(f"4+{He}+{sp_mid}", f"{sp_mid}", f"max(0,floor((H-2*{He}-{sp_mid}-8)/{sp_mid}))", f"كانة T{link} كل {sp_mid} سم (منتصف العمود)")
    return P

def wall_rc(db, link, sp=15, cover=4.0):
    # two curtains (both faces): horizontal bars in the outer layer, vertical bars inside them, cross-links every 2nd bar both ways; all ROUND bars. W = long side, D = thickness
    rv = db / 20.0; rh = link / 20.0; dh = link / 10.0
    zh = f"(D/2-{cover}-{rh})"                      # centre line of a horizontal bar (outer layer)
    zv = f"(D/2-{cover}-{dh}-{rv})"                 # centre line of a vertical bar (inside the horizontals)
    xv = cover + dh + rv                            # first vertical bar from the wall end
    nvert = f"floor((W-{2*xv})/{sp})+1"
    P = [box(("-W/2", 0, "-D/2"), ("W/2", "H", "D/2"), "#b4b4ae", "ghost", n="جسم الجدار الخرساني المسلّح (شفاف)"),
         rep(cyl((f"-W/2+{xv}", 3.0, f"-{zv}"), rv, "H-6", REBAR, "metal", seg=10, n=f"قضيب رأسي مستدير T{db} كل {sp} سم — الوجه الأول"), nvert, (sp, 0, 0)),
         rep(cyl((f"-W/2+{xv}", 3.0, f"{zv}"), rv, "H-6", REBAR, "metal", seg=10, n=f"قضيب رأسي مستدير T{db} كل {sp} سم — الوجه الثاني"), nvert, (sp, 0, 0)),
         rep(cyl((f"-W/2+{cover}", 6, f"-{zh}"), rh, f"W-{2*cover}", TIE, "metal", ax="x", seg=8, n=f"قضيب أفقي مستدير T{link} كل {sp} سم — الوجه الأول"), f"floor((H-12)/{sp})", (0, sp, 0)),
         rep(cyl((f"-W/2+{cover}", 6, f"{zh}"), rh, f"W-{2*cover}", TIE, "metal", ax="x", seg=8, n=f"قضيب أفقي مستدير T{link} كل {sp} سم — الوجه الثاني"), f"floor((H-12)/{sp})", (0, sp, 0))]
    for k in range(20):                             # cross-links: one row every 2*sp cm of height (up to 6 m), one per second vertical bar
        P.append(rep(cyl((f"-W/2+{xv}", 6 + k * sp * 2, f"-{zh}"), rh, f"2*{zh}", TIE, "metal", ax="z", seg=6, n=f"رباط عرضي T{link} (Link) بين الوجهين" if k == 0 else None),
                     f"(H-12>={k * sp * 2}) ? floor((W-{2*xv})/{sp * 2})+1 : 0", (sp * 2, 0, 0)))
    return P

def beam():
    # typical beam: 2T20 top + 2T20 bottom, T10 links @10 near the supports (L=100 cm) and @20 elsewhere (S-22: punching / strip details)
    # every link is a RECTANGULAR HOOP of four round bars (not a solid plate) and the main bars sit inside it; the hoop's outer face is at the cover c
    c = 3.5; dl = 1.0; lr = dl / 2; rb = 1.0
    zb = f"(D/2-{c}-{dl}-{rb})"
    P = [box(("-W/2", 0, "-D/2"), ("W/2", "H", "D/2"), "#b4b4ae", "ghost", n="جسم الجسر الخرساني (شفاف)")]
    for sz in (-1, 1):
        P += [cyl(("-W/2+3", f"{c + dl + rb}", f"{sz}*{zb}"), rb, "W-6", REBAR, "metal", ax="x", seg=10, n="قضيب سفلي مستدير T20 — تفصيل نموذجي (S-22)"),
              cyl(("-W/2+3", f"H-{c + dl + rb}", f"{sz}*{zb}"), rb, "W-6", REBAR, "metal", ax="x", seg=10, n="قضيب علوي مستدير T20")]
    hz = f"(D/2-{c}-{lr})"
    def link(x0, n, step, nm):
        return [rep(cyl((f"{x0}", f"{c + lr}", f"-{hz}"), lr, f"2*{hz}", TIE, "metal", ax="z", seg=8, n=nm), n, (step, 0, 0)),
                rep(cyl((f"{x0}", f"H-{c + lr}", f"-{hz}"), lr, f"2*{hz}", TIE, "metal", ax="z", seg=8), n, (step, 0, 0)),
                rep(cyl((f"{x0}", f"{c + lr}", f"-{hz}"), lr, f"H-{2 * (c + lr)}", TIE, "metal", seg=8), n, (step, 0, 0)),
                rep(cyl((f"{x0}", f"{c + lr}", f"{hz}"), lr, f"H-{2 * (c + lr)}", TIE, "metal", seg=8), n, (step, 0, 0))]
    P += link("-W/2+5", "round(min(100,W/3)/10)", 10, "كانة T10 كل 10 سم (منطقة الدعامات 100 سم)")
    P += link("W/2-5-min(100,W/3)", "round(min(100,W/3)/10)", 10, "كانة T10 كل 10 سم (منطقة الدعامة الثانية)")
    P += link("-W/2+5+min(100,W/3)+20", "max(0,floor((W-10-2*min(100,W/3)-20)/20))", 20, "كانة T10 كل 20 سم (الوسط)")
    return P

def slab_plain():
    return [box(("-W/2", 0, "-D/2"), ("W/2", "H", "D/2"), "#b4b4ae", "matte", n="بلاطة خرسانية مصمتة — Fcu 40"),
            rep(box(("-W/2", "H", "-D/2"), ("W/2", "H+0.05", "-D/2+0.3"), "#8e8c85", "matte", n="خط فوّاصل الصب (Formwork line)"), "floor(D/120)+1", (0, 0, 120))]

def pile():
    return [cyl((0, 0, 0), 30, "H", "#b4b4ae", "ghost", seg=24, n="خازوق خرساني ⌀60 سم — يُعرض 30 سم فقط تحت اللبشة"),
            rep(cyl((f"20*cos(i*PI/4)", 3, f"20*sin(i*PI/4)"), 1.0, "H-3", REBAR, "metal", seg=8, n="قضيب رئيسي (حسب جدول الخوازيق — غير متوفر في الملفات المستخرجة)"), 8, (0, 0, 0)),
            tor((0, 6, 0), 21, 0.5, TIE, ax="y", m="metal", n="حلزون تقييد (Spiral)")]

COLS = {"C1": (34, 32, 12), "C2": (34, 20, 10), "C3": (24, 20, 10), "C4": (12, 20, 10), "C5": (20, 32, 12), "C6": (30, 25, 10), "C7": (28, 25, 10), "C8": (32, 25, 10), "C9": (32, 25, 10), "C10": (12, 20, 10), "C11": (10, 20, 10)}
CSZ = {"C1": (30, 160), "C2": (30, 160), "C3": (25, 150), "C4": (50, 50), "C5": (60, 60), "C6": (30, 140), "C7": (20, 140), "C8": (20, 160), "C9": (20, 160), "C10": (20, 70), "C11": (20, 60)}
WALLS = {"W1": (25, 10, 705), "W2": (25, 10, 580), "W3": (25, 10, 300), "W4": (20, 10, 240)}

def make():
    out = {}
    def add(t): out[t[0]] = t[1]
    for k, (n, db, lk) in COLS.items():
        w, d = CSZ[k]
        sp_mid = 15
        add(sample(f"col_{k}", f"عمود {k} ({w}×{d} سم) — {n}T{db} وكانات T{lk}", f"Column {k} reinforcement detail", "structure", column(n, db, lk, sp_mid, 10), place={"mode": "prism", "anchor": "bottom"}, lod=6.0, conf="doc", src=SRC_C,
                   facts=[["المقطع", f"{w} × {d} سم"], ["التسليح الرئيسي", f"{n} T{db}"], ["الكانات", f"T{lk} كل 10–15 سم"], ["الخرسانة", "Fcu 40 N/mm² / Fy 460"]],
                   asm=["توزيع القضبان على المحيط بالتساوي (الجدول يعرض الترتيب بالرسم، وقد تختلف أماكن القضبان الفردية)", "الغطاء الخرساني 40 مم: قياسي", "طول التراكب (Lap) وبداية القضبان: غير معروضة", "العمود يُعرض شفافًا لإظهار التسليح"],
                   vars={"cc": round(4.0 + lk / 10.0 + db / 20.0, 3), "Wi": "W-2*cc", "Di": "D-2*cc", "P": "2*(Wi+Di)"}, dims={"W": w, "D": d, "H": 320}))
    out["col_column"] = dict(out["col_C7"]); out["col_column"]["name"] = "عمود (غير مصنّف) — يُعرض كما C7"; out["col_column"]["asm"] = out["col_C7"]["asm"] + ["لا وسم لهذا العمود في المخطط الإنشائي؛ عُرض بتسليح C7 (20×140) لتطابق المقطع — يحتاج تأكيدًا"]
    for k, (db, lk, L) in WALLS.items():
        add(sample(f"col_{k}", f"جدار خرساني {k} — T{db}@15 + T{lk}@15", f"RC wall {k} reinforcement detail", "structure", wall_rc(db, lk, 15), place={"mode": "prism", "anchor": "bottom"}, lod=7.0, conf="doc", src=SRC_C,
                   facts=[["الجدار", k], ["التسليح الرأسي", f"T{db} كل 15 سم على الوجهين"], ["الأفقي", f"T{lk} كل 15 سم"]], asm=["الغطاء 40 مم والتراكبات: قياسية", "جزء الجدار يُعرض شفافًا لإظهار التسليح"], dims={"W": L, "D": 20, "H": 320}))
    out["col_W3*"] = dict(out["col_W3"]); out["col_W3*"]["name"] = "جدار خرساني W3* (تفاصيل W3 بعرض 20 سم)"
    add(sample("beam", "جسر خرساني (نموذجي) — 2T20 علوي وسفلي وكانات T10", "Typical RC beam detail", "structure", beam(), place={"mode": "prism", "anchor": "bottom"}, lod=6.0, conf="assumed", src=["STR ص27: تفاصيل المقاطع S-22 (تسليح البلاطة والجسور القابلة للاستنتاج)"],
               facts=[["الخرسانة", "Fcu 40 N/mm²"], ["الأبعاد", "من مخطط البلاطات (العرض × العمق)"]], asm=["جدول الجسور بتسليحها غير موجود في الملفات المستخرجة؛ التسليح المعروض نموذجي من تفاصيل S-22 (2T20 علوي وسفلي، كانات T10 @10 سم عند الدعامات ثم @20 سم) — يحتاج تأكيدًا من المهندس الإنشائي"], dims={"W": 300, "D": 25, "H": 70}))
    for k in ("B1", "B2", "B3", "B4", "B5", "B6", "B7", "None", "B1*"):
        out[f"beam_{k}"] = out["beam"]
    add(sample("slab_T", "بلاطة السطح العلوي T (25 سم)", "Top roof slab", "structure", slab_plain(), place={"mode": "rect", "anchor": "bottom"}, lod=8.0, conf="derived", src=["STR ص24: مخطط بلاطة السطح العلوي"], facts=[["السماكة", "25 سم"]], asm=["تسليح البلاطة: «refer to plan» — غير مفصّل في الملفات المستخرجة؛ تُعرض الخرسانة فقط"], dims={"W": 600, "D": 300, "H": 25}))
    add(sample("pile", "خازوق خرساني ⌀60 سم", "Concrete pile", "structure", pile(), place={"mode": "cyl", "anchor": "bottom"}, lod=8.0, conf="derived", src=["STR ص11: مخطط الأساسات", "STR ص12: تفاصيل الأساسات S-8"], facts=[["القطر", "60 سم"], ["الطول الفعلي", "13 م (يُعرض 30 سم)"]], asm=["تسليح الخازوق: غير متوفر في الملفات المستخرجة؛ القضبان الـ8 والحلزون توضيحية — يحتاج جدول الخوازيق"], dims={"W": 60, "D": 60, "H": 30}))
    # catalog-only samples (continuous slabs / raft: far too large to swap)
    for k, nm, thk in (("raft80", "لبشة 80 سم", 80), ("raft150", "لبشة 150 سم", 150)):
        add(sample(k, f"{nm} — خرسانة Fcu 40 مع طبقات العزل (قطاع S-8)", f"Raft {thk} cm (section)", "structure",
                   [box(("-W/2", 0, "-D/2"), ("W/2", "H", "D/2"), "#b4b4ae", "ghost", n=f"اللبشة خرسانة مسلّحة {thk} سم"),
                    box(("-W/2-10", "-10", "-D/2-10"), ("W/2+10", 0, "D/2+10"), "#d6d3c4", "matte", n="خرسانة نظافة (Blinding) 10 سم @20 N/mm²"),
                    box(("-W/2-10", "-10.4", "-D/2-10"), ("W/2+10", "-10", "D/2+10"), "#1c1c1c", "matte", n="عزل مائي بيتوميني Polybit/Polyprime"),
                    box(("-W/2-10", "-10.6", "-D/2-10"), ("W/2+10", "-10.4", "D/2+10"), "#f2f2ee", "matte", n="طبقة بولي إيثيلين 1000 gauge")] +
                   [rep(cyl(("-W/2+6", 7, "-D/2+6"), 0.8, "D-12", REBAR, "metal", ax="z", seg=8, n="قضيب سفلي T16 كل 20 سم (S-8)"), "floor((W-12)/20)+1", (20, 0, 0)),
                    rep(cyl(("-W/2+6", 9, "-D/2+6"), 0.8, "W-12", REBAR, "metal", ax="x", seg=8, n="قضيب سفلي T16 كل 20 سم — الاتجاه الآخر"), "floor((D-12)/20)+1", (0, 0, 20))],
                   place={"mode": "none"}, lod=8.0, conf="derived", src=["STR ص12: تفاصيل الأساسات S-8 (قطاعات 1-A و1-B و1-C)", "STR ص11: مخطط الأساسات"], facts=[["السماكة", f"{thk} سم"], ["التسليح السفلي", "T16 @200"], ["الخرسانة", "Fcu 40 N/mm²"], ["العزل", "Polybit-Polyprime SB على خرسانة نظافة 10 سم + بولي إيثيلين"]],
                   asm=["التسليح العلوي والتقوية: «refer to raft reinf. plan» — غير مفصّل", "العينة قطاع 1.2×1.2 م فقط (اللبشة كاملها كبيرة جدًا للاستبدال التلقائي)"], dims={"W": 120, "D": 120, "H": thk}))
    add(sample("ramp_slab", "بلاطة منحدر السيارات 35 سم — Y16@15 و Y12@15 (قطاع S-23)", "Vehicle ramp slab 35 cm (section)", "structure",
               [box(("-W/2", 0, "-D/2"), ("W/2", 35, "D/2"), "#b4b4ae", "ghost", n="بلاطة المنحدر خرسانة مسلّحة Fcu 40، سماكة 35 سم"),
                box(("-W/2", 35, "-D/2"), ("W/2", 36.5, "D/2"), "#3c3f44", "matte", n="طبقة تشطيب سطح المنحدر — غير محددة في المستندات (أسفلت/خرسانة مخشّنة) — افتراض"),
                box(("-W/2", -0.6, "-D/2"), ("W/2", 0, "D/2"), "#1c1c1c", "matte", n="عزل مائي بيتوميني (WATERPROOFING POLYBIT / BITU PLUS E-4180 كما في S-23)")] +
               [rep(cyl(("-W/2+4", 5, "-D/2+4"), 0.8, "D-8", REBAR, "metal", ax="z", seg=8, n="قضيب رئيسي سفلي Y16 كل 15 سم (S-23)"), "floor((W-8)/15)+1", (15, 0, 0)),
                rep(cyl(("-W/2+4", 7.2, "-D/2+4"), 0.6, "W-8", REBAR, "metal", ax="x", seg=8, n="قضيب توزيع سفلي Y12 كل 15 سم"), "floor((D-8)/15)+1", (0, 0, 15)),
                rep(cyl(("-W/2+4", 28, "-D/2+4"), 0.8, "D-8", REBAR, "metal", ax="z", seg=8, n="قضيب رئيسي علوي Y16 كل 15 سم (T&B في S-23)"), "floor((W-8)/15)+1", (15, 0, 0)),
                rep(cyl(("-W/2+4", 26.2, "-D/2+4"), 0.6, "W-8", REBAR, "metal", ax="x", seg=8, n="قضيب توزيع علوي Y12 كل 20 سم"), "floor((D-8)/20)+1", (0, 0, 20))],
               place={"mode": "none"}, lod=8.0, conf="derived", src=["STR ص28: تفاصيل المنحدر S-23 (TH=35 سم، Y16@15 و Y12@15/20 علوي وسفلي)", "ARCH2 ص7: A606 — ميل 16.5% ومنحدر انتقالي 8%"],
               facts=[["السماكة", "35 سم"], ["التسليح", "Y16@150 + Y12@150 (T&B) — الخرسانة Fcu 40 N/mm²"], ["العرض", "6 م بين الجدران"], ["الميل", "16.5% + انتقالي 8% × 3 م"]],
               asm=["العينة قطاع 1.2×1.2 م (المنحدر كامله منحنٍ وطويل)", "تشطيب السطح غير محدد في المستندات", "الغطاء 25 مم للبلاطات المصمتة: من ملاحظات STR"], dims={"W": 120, "D": 120, "H": 35}))
    add(sample("slab_floor", "بلاطة أرضية/سقف طابق (قطاع نموذجي)", "Floor slab typical section", "structure", slab_plain(), place={"mode": "none"}, lod=8.0, conf="derived", src=["STR ص20-24: مخططات البلاطات"], asm=["البلاطات الكبيرة متعددة الأضلاع لا تُستبدل تلقائيًا؛ تُعرض كعينة كتالوج"], dims={"W": 200, "D": 150, "H": 28}))
    return out

RULES = [{"c": "S.col", "t": f"col_{k}", "s": f"col_{k}"} for k in list(COLS) + ["column"]] + [{"c": "S.wall", "t": f"col_{k}", "s": f"col_{k}"} for k in list(WALLS) + ["W3*"]] + \
        [{"c": "S.beam", "t": f"beam_{k}", "s": f"beam_{k}"} for k in ("B1", "B2", "B3", "B4", "B5", "B6", "B7", "None", "B1*")] + [{"c": "S.slab", "t": "slab_T", "s": "slab_T"}, {"c": "S.pile", "t": "pile", "s": "pile"},
         {"c": "S.raft", "t": "raft80", "s": "raft80"}, {"c": "S.raft", "t": "raft150", "s": "raft150"}, {"c": "S.slab", "t": "slab_G", "s": "slab_floor"}, {"c": "S.slab", "t": "slab_1", "s": "slab_floor"}, {"c": "S.slab", "t": "slab_2", "s": "slab_floor"},
         {"c": "S.slab", "t": "slab_3", "s": "slab_floor"}, {"c": "S.slab", "t": "slab_4", "s": "slab_floor"}, {"c": "S.slab", "t": "slab_5", "s": "slab_floor"}, {"c": "S.slab", "t": "slab_R", "s": "slab_floor"}, {"c": "S.ramp", "t": "ramp_slab", "s": "ramp_slab"}]
