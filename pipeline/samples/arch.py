# -*- coding: utf-8 -*-
"""architectural samples: doors (A700 schedule), curtain-wall windows (A800-A802), lift car (A900), fences/parapets"""
from .lib import *

def _hinges(xh, ys, face_z, steel, hc):
    out = []
    for y in ys:
        out.append(cyl((xh, f"({y})-5", 0), 0.9 if not steel else 1.1, 10, hc, "metal", n="مفصلة (Butt hinge) — الأسطوانة"))
        out.append(box((f"({xh})-0.2", f"({y})-5", -0.15), (f"({xh})+3.0", f"({y})+5", 0.15), hc, "metal", n="ريشة المفصلة"))
    return out

def door_wood(fire=False, entrance=False, bath=False, color=WALNUT, edge=WALNUT_D, fire_min=0):
    fj = 3.5
    xs = f"-W/2+{fj}+0.3"; xe = f"W/2-{fj}-0.3"
    P = []
    P += [box(("-W/2", 0, "-T/2"), (f"-W/2+{fj}", "H", "T/2"), edge, "matte", n="بطانة الإطار — الجانب الأيسر (خشب جوز)"),
          box((f"W/2-{fj}", 0, "-T/2"), ("W/2", "H", "T/2"), edge, "matte", n="بطانة الإطار — الجانب الأيمن"),
          box((f"-W/2+{fj}", f"H-{fj}", "-T/2"), (f"W/2-{fj}", "H", "T/2"), edge, "matte", n="بطانة الإطار — العلوية")]
    # architrave (casing) on both faces
    P += [dict(box(("-W/2-6.5", 0, "T/2"), ("-W/2", "H+6.5", "T/2+1.6"), color, "matte", n="أرشيتراف (إطار تغطية) — جانب"), mz=True),
          dict(box(("W/2", 0, "T/2"), ("W/2+6.5", "H+6.5", "T/2+1.6"), color, "matte", n="أرشيتراف — جانب"), mz=True),
          dict(box(("-W/2", "H", "T/2"), ("W/2", "H+6.5", "T/2+1.6"), color, "matte", n="أرشيتراف — علوي"), mz=True)]
    # leaf
    P += [box((xs, 1.0, -2.0), (xe, f"H-{fj}-0.3", 2.0), color, "matte", n="ورقة الباب (قشرة جوز على قلب رقائقي) — سماكة 4 سم")]
    # leaf edge banding (dark line on both vertical edges)
    P += [box((xs, 1.0, -2.05), (f"{xs}+0.6", f"H-{fj}-0.3", 2.05), edge, "matte", n="حافة الورقة (شريط جوز مصمت)"),
          box((f"{xe}-0.6", 1.0, -2.05), (xe, f"H-{fj}-0.3", 2.05), edge, "matte")]
    # hinges (3) on the left edge
    P += _hinges(xs, [22, "(H-fj)/2".replace("fj", str(fj)), f"H-{fj}-26"], 0, False, STEEL)
    # lever handle set on the latch side (both faces)
    xl = f"{xe}-5.5"
    for side, z in ((1, 2.0), (-1, -2.0)):
        P += [cyl((xl, 100, z if side > 0 else z - 0.8), 2.5, 0.8, STEEL, "metal", ax="z", n="وردة المقبض (Rose)"),
              cyl((xl, 100, z + (0.8 if side > 0 else -2.6)), 0.8, 1.8, STEEL, "metal", ax="z", n="ساق المقبض"),
              box((f"{xl}-11.5", 99.2, (z + 2.6) if side > 0 else (z - 4.4)), (f"{xl}+1.0", 100.9, (z + 4.4) if side > 0 else (z - 2.6)), STEEL, "metal", n="ذراع المقبض (Lever) — ستانلس")]
    P += [box((f"{xe}-0.2", 84, -1.0), (f"{xe}+0.3", 116, 1.0), STEEL, "metal", n="لوحة اللسان (Latch faceplate)"),
          box((f"{xe}+0.3", 90, -0.6), (f"{xe}+0.8", 102, 0.6), STEEL_D, "metal", n="لسان القفل (Latch bolt)"),
          box((f"W/2-{fj}", 86, -1.0), (f"W/2-{fj}+0.4", 114, 1.0), STEEL, "metal", n="لوحة التعشيق (Strike plate) على الإطار")]
    if entrance:
        P += [cyl((xl, 92, 2.0), 1.6, 1.0, BRASS, "metal", ax="z", n="غطاء الأسطوانة (Euro cylinder)"),
              cyl((f"{xs}+(W-{2*fj}-0.6)/2", 150, -2.4), 0.7, 4.8, STEEL_D, "metal", ax="z", n="عين الباب (Peephole)"),
              cyl((f"{xs}+(W-{2*fj}-0.6)/2", 150, 2.0), 1.3, 0.4, STEEL, "metal", ax="z"),
              box((f"{xs}+(W-{2*fj}-0.6)/2-6", 166, 2.0), (f"{xs}+(W-{2*fj}-0.6)/2+6", 172, 2.3), BRASS, "metal", n="لوحة رقم الشقة (نحاسية)")]
    if bath:
        P += [cyl((xl, 100, -2.9), 1.7, 1.2, STEEL, "metal", ax="z", n="مقبض خصوصية (Privacy turn)")]
    if fire:
        P += [box((f"-W/2+{fj}-0.6", 0, -0.9), (f"-W/2+{fj}", "H-3.5", 0.9), "#2b2b2b", "rubber", n="شريط انتفاخي مقاوم للحريق (Intumescent) على الجانب الأيسر"),
              box((f"W/2-{fj}", 0, -0.9), (f"W/2-{fj}+0.6", "H-3.5", 0.9), "#2b2b2b", "rubber", n="شريط انتفاخي — الأيمن"),
              box((f"-W/2+{fj}", f"H-{fj}-0.6", -0.9), (f"W/2-{fj}", f"H-{fj}", 0.9), "#2b2b2b", "rubber", n="شريط انتفاخي — علوي"),
              box((f"{xs}+0.4", f"H-{fj}-14", 2.0), (f"{xs}+7.4", f"H-{fj}-10.5", 2.25), "#d9d34a", "matte", n=f"ملصق مقاومة الحريق FD{fire_min}")]
        # overhead door closer on the pull face
        P += [box((f"{xs}+14", f"H-{fj}-9", 2.0), (f"{xs}+14+28", f"H-{fj}-2.6", 7.8), GALV, "metal", n="ذراع إغلاق علوي (Door closer) — الجسم"),
              box((f"{xs}+14+28", f"H-{fj}-8", 2.5), (f"{xs}+14+31", f"H-{fj}-3", 4.5), GALV, "metal", n="ذراع الإغلاق — المفصل"),
              dict(box((f"{xs}+14", f"H-{fj}-5.6", 6.8), (f"{xs}+14+28", f"H-{fj}-4.4", 7.8), STEEL_D, "metal", n="ذراع الإغلاق — الذراع المتعاقب"), rot=[0, 18, 0])]
    # gap / drop seal at the bottom
    P += [box((xs, 0.2, -1.5), (xe, 1.0, 1.5), "#3a3a3a", "rubber", n="مانع تسرب سفلي (Drop seal)")]
    return P

def door_steel(fire=True, double=False, panic=False, closer=True, color="#c9ced4", louvre=False, alu=False):
    fj = 5.0
    frame = ALU if alu else GALV; leafc = "#d8dce0" if not alu else ALU
    P = []
    # pressed steel frame with return (rebate) lines
    for (xa, xb) in (("-W/2", f"-W/2+{fj}"), (f"W/2-{fj}", "W/2")):
        P.append(box((xa, 0, "-T/2-0.3"), (xb, "H", "T/2+0.3"), frame, "metal", n="إطار فولاذ مجلفن مضغوط (Pressed frame)"))
    P.append(box((f"-W/2+{fj}", f"H-{fj}", "-T/2-0.3"), (f"W/2-{fj}", "H", "T/2+0.3"), frame, "metal", n="إطار — علوي"))
    # leaf (or two leaves)
    xs = f"-W/2+{fj}+0.4"; xe = f"W/2-{fj}-0.4"
    if not double:
        P.append(box((xs, 1.2, -2.25), (xe, f"H-{fj}-0.4", 2.25), leafc, "matte", n="ورقة فولاذ مجلفن مدهونة إيبوكسي (4.5 سم)"))
        P.append(box((xs, 1.2, 2.25), (xe, 33, 2.4), STEEL, "metal", n="لوح حماية سفلي (Kick plate) ستانلس"))
        lx = [xe]
    else:
        P.append(box((xs, 1.2, -2.25), ("-0.35", f"H-{fj}-0.4", 2.25), leafc, "matte", n="الورقة اليسرى"))
        P.append(box(("0.35", 1.2, -2.25), (xe, f"H-{fj}-0.4", 2.25), leafc, "matte", n="الورقة اليمنى"))
        P.append(box(("-0.5", 1.2, -2.4), ("0.5", f"H-{fj}-0.4", 2.4), GALV, "metal", n="قضيب التقاء (Astragal)"))
        P.append(box((xs, 1.2, 2.25), (xe, 33, 2.4), STEEL, "metal", n="لوح حماية سفلي (Kick plate)"))
        lx = ["-1.0", "1.0"]
    if louvre:
        P.append(rep(box(("-W/2+14", "H-190", 2.3), ("W/2-14", "H-186", 3.4), ALU_D, "metal", rot=[-30, 0, 0], n="ريشة لوفر (Louvre blade)"), 22, (0, 6, 0)))
        P.append(box(("-W/2+11", "H-198", 2.25), ("W/2-11", "H-196", 3.0), ALU, "metal", n="إطار الفتحة"))
    # hinges (3 heavy, ball bearing) on the outer edge(s)
    hy = [25, "(H-5)/2", "H-5-28"]
    P += _hinges(xs, hy, 0, True, STEEL_D)
    if double:
        for y in hy:
            P.append(cyl((xe, f"({y})-5", 0), 1.1, 10, STEEL_D, "metal", n="مفصلة — الورقة اليمنى"))
    # handles
    if panic:
        P += [box(("W/2-30" if not double else "-5", 98, 2.6), ("W/2-6" if not double else "-40", 106, 4.6), RED, "matte", n="عارضة الهروب (Panic bar) — دفع للخروج"),
              cyl(("W/2-8" if not double else "-8", 99, 2.25), 1.0, 1.0, STEEL, "metal", ax="z", n="دعامة العارضة")]
    else:
        for z, sgn in ((2.4, 1), (-2.4, -1)):
            P += [cyl((f"{lx[0]}-6", 100, z if sgn > 0 else z - 0.8), 2.6, 0.8, STEEL, "metal", ax="z", n="وردة المقبض"),
                  box((f"{lx[0]}-17", 99.1, z + (0.8 if sgn > 0 else -3.0)), (f"{lx[0]}-5", 100.9, z + (3.0 if sgn > 0 else -0.8)), STEEL, "metal", n="ذراع المقبض — فولاذ لا يصدأ")]
    if closer:
        P += [box((xs + "+12", f"H-{fj}-10", 2.4), (xs + "+12+30", f"H-{fj}-3", 8.4), GALV, "metal", n="ذراع إغلاق علوي (Door closer)"),
              dict(box((xs + "+12", f"H-{fj}-6", 7.4), (xs + "+12+30", f"H-{fj}-4.6", 8.4), STEEL_D, "metal", n="ذراع الإغلاق — الذراع"), rot=[0, 16, 0])]
    P += [box((xs, f"H-{fj}-20", 2.25), (f"{xs}+8", f"H-{fj}-16", 2.5), "#d9d34a", "matte", n="ملصق مقاومة الحريق")] if fire else []
    P += [box((xs, 0.2, -1.5), (xe, 1.2, 1.5), "#3a3a3a", "rubber", n="مانع تسرب سفلي")]
    P += [cyl(("W/2-14", 0, 12), 3.5, 3, STEEL_D, "metal", r1=2.6, n="مصدّ أرضي (Floor stop)")]
    return P

def make():
    out = {}
    def add(t): out[t[0]] = t[1]
    SRC = ["جدول الأبواب A700 (ARCH2 ص9) + تفاصيل A701 + مجموعات الإكسسوار A702/A703", "BOQ بند الأبواب (8.1/8.2/8.3)"]
    ASM_DOOR = ["جهة الفصّات (يسار) واتجاه فتح الورقة غير مرسومين على المخططات: الورقة مرسومة مغلقة والفصّات على الجانب الأيسر — افتراض",
                "تفصيل الإكسسوار (نوع المقبض، الأرشيتراف 6.5 سم، المانع السفلي) توضيحي قياسي — مجموعة الإكسسوار الفعلية في A702/A703 ويلزم تثبيتها قبل التوريد"]
    wood = [("D1", "باب خشب جوز مصمت — مدخل الشقة (حريق 60 د)", True, True, False, "FD60", 60),
            ("D2", "باب خشب جوز مصمت — غرف النوم", False, False, False, None, 0),
            ("D3", "باب خشب جوز مصمت — الحمامات والمخازن", False, False, True, None, 0),
            ("D4", "باب خشب جوز مقاوم للحريق — المطبخ (60 د)", True, False, False, "FD60", 60),
            ("D5", "باب خشب جوز مقاوم للحريق — السلم الداخلي (90 د)", True, False, False, "FD90", 90),
            ("D7", "باب خشب جوز مقاوم للحريق — غرف الخدمات (90 د)", True, False, False, "FD90", 90)]
    for code, nm, fire, ent, bath, lab, fm in wood:
        add(sample(f"door_{code}", nm, f"Walnut veneer flush door {code}", "architecture", door_wood(fire=fire, entrance=ent, bath=bath, fire_min=fm),
                   place={"mode": "rect", "anchor": "bottom"}, lod=5.0, conf="derived", src=SRC,
                   facts=[["الأبعاد الاسمية", "حسب جدول A700 (عرض × ارتفاع)"], ["الورقة", "قلب رقائقي مصمت + قشرة جوز، سماكة 4 سم"], ["الإطار", "بطانة وأرشيتراف من خشب الجوز"],
                          ["مقاومة الحريق", f"{fm} دقيقة" if fm else "غير مطلوب"]], asm=ASM_DOOR, varmap={"T": "wall_cm"}, defaults={"T": 10},
                   dims={"W": 96, "D": 4, "H": 215, "T": 10}))
    steel = [("D6", "باب فولاذ مجلفن مقاوم للحريق — مخرج السلم 02 (90 د)", dict(panic=True, closer=True)),
             ("D8", "باب فولاذ — غرفة الجهد العالي HV", dict(closer=True)),
             ("D10", "باب فولاذ — غرفتا الجهد المنخفض LV والهاتف", dict(closer=True)),
             ("D11", "باب فولاذ — غرفة الحارس / دورة المياه", dict(closer=True)),
             ("D12", "باب فولاذ — غرفة المضخات", dict(closer=True)),
             ("D13", "باب فولاذ — النفايات/الغاز/القيادة", dict(closer=True)),
             ("D14", "باب فولاذ — المخازن", dict(closer=True)),
             ("D15", "باب فولاذ — غرفة مضخات المياه المبردة", dict(closer=False, fire=False))]
    for code, nm, kw in steel:
        dbl = code in ("D8", "D10", "D12", "D14")
        add(sample(f"door_{code}", nm, f"Galvanised steel door {code}", "architecture", door_steel(double=dbl, **kw), place={"mode": "rect", "anchor": "bottom"}, lod=6.0, conf="derived", src=SRC,
                   facts=[["الورقة", "فولاذ مجلفن مدهون إيبوكسي"], ["الإطار", "فولاذ مجلفن مضغوط"], ["الورقات", "ورقتان" if dbl else "ورقة واحدة"]],
                   asm=ASM_DOOR + (["عدد الأوراق (1 أو 2) غير مذكور في الجدول؛ افتُرضت ورقتان لأن العرض ≥ 150 سم — بانتظار تأكيدك"] if dbl else []),
                   varmap={"T": "wall_cm"}, defaults={"T": 20}, dims={"W": 96, "D": 4, "H": 215, "T": 20}))
    add(sample("door_D9", "باب ألمنيوم بلوفر تهوية — غرفة المحول والمولد", "Aluminium louvred door D9", "architecture", door_steel(double=True, fire=False, closer=False, louvre=True, alu=True),
               place={"mode": "rect", "anchor": "bottom"}, lod=6.0, conf="derived", src=SRC,
               facts=[["الورقة والإطار", "ألمنيوم مطلي بالمسحوق"], ["التهوية", "ريش لوفر ثابتة"]], asm=ASM_DOOR + ["عدد الأوراق وارتفاع حقل اللوفر وزاوية الريش: افتراض (غير مفصّلة في الجدول)"],
               varmap={"T": "wall_cm"}, defaults={"T": 20}, dims={"W": 226, "D": 4, "H": 345, "T": 20}))
    add(sample("door_D16", "باب فولاذ — درج التنسيق الخارجي", "Steel hatch door D16", "architecture", door_steel(closer=False, fire=False), place={"mode": "rect", "anchor": "bottom"},
               lod=5.0, conf="derived", src=["ARCH2 ص5 A604 / BOQ ص8 البند8.3.12"], asm=ASM_DOOR + ["هذه عينة إجرائية عامة وليست جسم D16 المرسوم أو مقاسات تصنيعه؛ تمثيله في المجسم مستقل من المسقط.", "A604 يحدد فتحة125×110سم ومقاومة90دقيقة؛ BOQ يطبع125X1100mm وN/A. التعارضان لم يحسما."], defaults={"T": 20}, varmap={"T": "wall_cm"}, dims={"W": 121, "D": 4, "H": 105, "T": 20}))
    return out

RULES = [{"c": "A.door", "t": f"door_{c}", "s": f"door_{c}"} for c in ["D1","D2","D3","D4","D5","D6","D7","D8","D9","D10","D11","D12","D13","D14","D15","D16"]]
