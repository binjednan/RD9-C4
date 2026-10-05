# -*- coding: utf-8 -*-
"""landscape / play / shade catalogue samples (catalogue only: place = none).  The elements themselves are in the base model (pipeline/landscape_els.py), always visible."""
from .lib import *

def make():
    out = {}
    def add(t): out[t[0]] = t[1]
    SRC = ["ARCH2 ص19 (A2300 خطة الزراعة)", "ARCH2 ص24 (A2305 الجازيبو وظلة الألعاب)", "ARCH2 ص21 (A2302 مقاطع الأحواض)", "صور الموقع 7 أغسطس"]
    N = {"mode": "none"}
    def tree(sid, ar, en, stem, h, rc, col, extra):
        parts = [cyl((0, 0, 0), 7, stem * 100 + 40, "#6b5236", "matte", n="الجذع"), sph((0, stem * 100 + (h - stem) * 50, 0), rc, col, "matte", s=[rc, (h - stem) * 50, rc], seg=14, n="التاج")]
        add(sample(sid, ar, en, "architecture", parts, place=N, conf="assumed", src=SRC, facts=[["الجدول A2300", extra]], asm=["شكل التاج كروي مبسّط؛ الارتفاع الكلي والقطر ذُكرا فقط حيث وردا في الجدول"], dims={"W": rc * 2, "D": rc * 2, "H": h * 100}))
    tree("tree_azad", "نيم (Azadirachta indica)", "Neem tree", 1.8, 5.0, 200, "#4d8a3b", "ساق 1.8 م، قطر 40–50 مم، 5 أشجار (AZAD.I)")
    tree("tree_hibi", "هبسكس (Hibiscus tiliaceus)", "Sea hibiscus tree", 1.8, 4.2, 170, "#5c9c48", "ساق 1.8 م، قطر 40–50 مم، 14 شجرة (HIBI.T)")
    tree("tree_plum", "فرنجبان (Plumeria obtusa)", "Plumeria", 1.0, 3.0, 85, "#6fae4f", "ارتفاع 3.0 م، 4 فروع كحد أدنى، قطر 70–80 مم، 22 شجرة (PLUM.O)")
    add(sample("tree_trunk", "جذع شجرة", "Tree trunk", "architecture", [cyl((0, 0, 0), 7, 220, "#6b5236", "matte", n="جذع")], place=N, conf="assumed", src=SRC, dims={"W": 14, "D": 14, "H": 220}))
    add(sample("shrub_jatr", "جاتروفا (Jatropha pandurifolia)", "Jatropha shrub", "architecture", [sph((0, 37, 0), 25, "#3f7f3a", "matte", s=[25, 37, 25], n="شجيرة"), cyl((0, 0, 0), 3, 20, "#6b5236", "matte", n="ساق")],
               place=N, conf="derived", src=SRC, facts=[["الجدول A2300", "ارتفاع 0.70–0.80 م، 3 فروع كحد أدنى، 55 شجيرة (JATR.P)"]], dims={"W": 50, "D": 50, "H": 75}))
    add(sample("plant_small", "نبات صغير (مغطّي تربة/عصاري)", "Ground cover / succulent", "architecture", [sph((0, 17, 0), 12, "#86b252", "matte", s=[12, 17, 12], n="نبات")],
               place=N, conf="assumed", src=SRC, facts=[["الأنواع المحتملة", "Ruellia ciliosa، Alternanthera versicolor، Bougainvillea 'Pink Pixie'، Vitex rotundifolia، Adenium obesum، Zamia furfuracea"]],
               asm=["الدوائر r≈12 سم لا تحدّد النوع؛ الارتفاع 0.35 م افتراض"], dims={"W": 24, "D": 24, "H": 35}))
    add(sample("site_bench", "مقعد جرانيت مدمج في جدار الحوض (TOS +0.65)", "Built-in granite bench", "architecture",
               [box(("-W/2", 0, "-D/2"), ("W/2", 45, "D/2"), "#3b3e44", "gloss", n="جسم المقعد جرانيت"), box(("-W/2", 45, "-D/2"), ("W/2", 48, "D/2"), "#2f3238", "gloss", n="غطاء جرانيت مصقول")],
               place=N, conf="derived", src=SRC, facts=[["منسوب سطح المقعد", "TOS +0.65 م (A2302 مقطع 1)"], ["الرصف المجاور", "PASCO F13 +0.20 م"]], asm=["العمق والتفاصيل: من الرمز على A102"], dims={"W": 200, "D": 45, "H": 48}))
    add(sample("shed_post", "عمود ظلة منطقة الألعاب — ماسورة فولاذ ⌀200 مم", "Shade-sail steel post", "architecture",
               [cyl((0, 0, 0), 10, 430, "#4a4f55", "metal", n="ماسورة فولاذ ⌀200 مم"), cyl((0, 0, 0), 20, 1, "#3b3f45", "metal", n="لوح قاعدة"), box((-6, 430, -6), (6, 440, 6), "#e6e0c8", "emit", n="كشاف")],
               place=N, conf="doc", src=SRC, facts=[["القطر", "⌀200 مم"], ["القمة", "+4.50 م (أو +3.50 م) من F.L. +0.20"]], asm=["أي الأعمدة +4.50 وأيها +3.50 غير مفصّل بوضوح — افتُرض الصف الشمالي +4.50"], dims={"W": 40, "D": 40, "H": 440}))
    add(sample("shed_sail", "شراع ظل PVC (Knitted shade cloth)", "PVC shade sail", "architecture",
               [ext([[0, 0], [400, 0], [200, 300]], 0.4, "#e3dcc6", "matte", n="قماش PVC مثقّب")], place=N, conf="assumed", src=SRC, facts=[["المادة", "PVC Fabric (knitted shade cloth)"], ["المسافات", "400 / 400 / 800 / 1200 / 620 سم (A2305)"]],
               asm=["الأشرعة في المخطط منحنية الحواف؛ العيّنة مسطّحة تقريبية"], dims={"W": 400, "D": 300, "H": 1}))
    for sid, ar, en in (("gazebo_post", "عمود الجازيبو — ماسورة فولاذ ⌀200 مم", "Gazebo steel post"), ("gazebo_rail", "عارضة الجازيبو الخشبية (علوية 50 سم / سفلية 40 سم)", "Gazebo timber rail"),
                        ("gazebo_roof", "سقف الجازيبو الهرمي — عوارض/لوفر خشب (+3.95 إلى +5.00)", "Gazebo hip roof"), ("gazebo_lattice", "شبك خشبي للجازيبو (190 سم)", "Gazebo wooden lattice"),
                        ("gazebo_bench", "مقعد الجازيبو الخشبي", "Gazebo bench"), ("gazebo_floor", "أرضية الجازيبو +0.95 — ⌀680 سم", "Gazebo floor")):
        parts = {"gazebo_post": [cyl((0, 0, 0), 10, 300, "#4a4f55", "metal", n="⌀200 مم")],
                 "gazebo_rail": [box(("-W/2", 0, -4), ("W/2", 50, 4), "#a9794c", "matte", n="عارضة خشب")],
                 "gazebo_roof": [ext([[0, 0], [345, 0], [172, 300]], 0.5, "#a9794c", "matte", n="لوح سقف خشبي")] + [rep(box((0, 0, 0), (345, 3, 6), "#8a5f38", "matte", n="لوفر"), 20, (0, 0, 15))],
                 "gazebo_lattice": [box(("-W/2", 0, -1.5), ("W/2", 190, 1.5), "#c49a6c", "matte", n="لوح الشبك")] + [rep(box(("-W/2", 0, -2), ("-W/2+1.5", 190, 2), "#8a5f38", "matte", n="قائم"), 14, (20, 0, 0))],
                 "gazebo_bench": [box(("-W/2", 0, -20), ("W/2", 45, 20), "#a9794c", "matte", n="مقعد")],
                 "gazebo_floor": [cyl((0, 0, 0), 340, 75, "#c9b99c", "matte", seg=48, n="منصة +0.95")]}[sid]
        add(sample(sid, ar, en, "architecture", parts, place=N, conf="derived", src=SRC, facts=[["A2305", "جازيبو ⌀680 سم؛ الأرضية +0.95؛ القمة +3.95؛ الذروة +5.00؛ أعمدة فولاذ ⌀200 مم"]],
                   asm=["تفاصيل الشبك والمقاعد تقريبية من المسقط والواجهات 1:50"], dims={"W": 200, "D": 60, "H": 300}))
    add(sample("fence_play", "سياج ساحة الألعاب — ارتفاع 120 سم", "Play-area fence", "architecture",
               [cyl((0, 0, 0), 2.5, 120, "#3d4248", "metal", n="عمود"), box((-75, 100, -1.5), (75, 103, 1.5), "#3d4248", "metal", n="قضيب علوي"), box((-75, 15, -1.5), (75, 18, 1.5), "#3d4248", "metal", n="قضيب سفلي")] + [rep(cyl((-70, 18, 0), 1, 85, "#3d4248", "metal", n="قضيب عمودي"), 8, (20, 0, 0))],
               place=N, conf="derived", src=SRC, facts=[["الارتفاع", "FENCING HIGHT 120cm (A2300)"]], asm=["القضبان العمودية من الصور (سياج فولاذي رمادي داكن)"], dims={"W": 150, "D": 6, "H": 120}))
    add(sample("fence_post", "عمود سياج", "Fence post", "architecture", [cyl((0, 0, 0), 2.5, 120, "#3d4248", "metal", n="عمود")], place=N, conf="derived", src=SRC, dims={"W": 5, "D": 5, "H": 120}))
    add(sample("play_part", "ألعاب الأطفال (7 أنواع من A2300)", "Kids play equipment", "architecture",
               [cyl((0, 0, 0), 49, 6, "#d8402f", "matte", n="ترامبولين ⌀100"), box((-150, 35, -9), (150, 42, 9), "#f2c230", "matte", n="أرجوحة توازن"), box((-200, 230, -3), (200, 238, 3), "#7b838c", "metal", n="عارضة الأرجوحة"),
                box((-45, 120, -42), (45, 128, 42), "#f2c230", "matte", n="منصة برج الزحاليق")], place=N, conf="assumed", src=SRC,
               facts=[["الأنواع والأعداد", "أرجوحة 1، أرجوحة شبكة العنكبوت 1، أرجوحة توازن 3، ترامبولين 1، مجموعة 3 زحاليق 1، حصان زنبركي 2، دوّارة 1"]],
               asm=["المسقط من A2300؛ الارتفاعات والتفاصيل افتراض"], dims={"W": 400, "D": 100, "H": 260}))
    return out

RULES = [{"c": c, "t": t, "s": t} for c, t in (("A.stage", "tree_azad"), ("A.stage", "tree_hibi"), ("A.stage", "tree_plum"), ("A.stage", "tree_trunk"), ("A.stage", "shrub_jatr"), ("A.stage", "plant_small"),
        ("A.stage", "play_part"), ("A.site", "site_bench"), ("A.site", "shed_post"), ("A.site", "shed_sail"), ("A.site", "gazebo_post"), ("A.site", "gazebo_rail"), ("A.site", "gazebo_roof"),
        ("A.site", "gazebo_lattice"), ("A.site", "gazebo_bench"), ("A.site", "gazebo_floor"), ("A.rail", "fence_play"), ("A.rail", "fence_post"))]
