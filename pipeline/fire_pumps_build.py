# -*- coding: utf-8 -*-
"""Build the fire-pump assembly at FF-101 positions, with no outside route."""
import collections
import json
import os
import re

HERE=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(HERE,"data","fire_pumps.json")
ID_RE=re.compile(r"-FP\d{4}$")
MATS={"p_fire_pump":{"name":"مجموعة مضخات الإطفاء","color":"#ad5448","code":"FF-101 / FF-105"}}
TYPES={
 "fp_electric":{"n":"مضخة إطفاء كهربائية FP-EP","cf":"doc","sp":[["التدفق","750 GPM"],["الضغط","10 bar"],["قدرة المحرك","88 kW"],["النوع بالنص","Vertical Turbine، UL Listed / FM Approved"]],"sr":["MECH2 ص11","MECH2 ص15–16"],"asm":["ارتفاع الغلاف 1.20 م افتراض؛ الرمز مبسط"]},
 "fp_diesel":{"n":"مضخة إطفاء ديزل FP-DP","cf":"doc","sp":[["التدفق","750 GPM"],["الضغط","10 bar"],["النوع بالنص","Vertical Turbine، UL Listed / FM Approved"]],"sr":["MECH2 ص11","MECH2 ص15–16"],"asm":["ارتفاع الغلاف 1.20 م افتراض؛ الرمز مبسط"]},
 "fp_jockey":{"n":"مضخة تثبيت ضغط الإطفاء FP-JP","cf":"doc","sp":[["التدفق","40 GPM"],["الضغط","10 bar"],["قدرة المحرك","5 kW"]],"sr":["MECH2 ص11","MECH2 ص15–16"],"asm":["ارتفاع الغلاف 0.90 م افتراض"]},
 "fp_pressure_vessel":{"n":"وعاء ضغط مجموعة الإطفاء","cf":"doc","sp":[["رمز المسقط","دائرة قطر45.4 سم؛ ليس مقاس توريد معتمدًا"]],"sr":["MECH2 ص11","MECH2 ص16"],"asm":["ارتفاع الوعاء1.10 م افتراض"]},
 "pipe_fp_header":{"n":"مجمع مجموعة مضخات الإطفاء","cf":"doc","sp":[["موضع المحور","من حافتي الخط في رمز المسقط؛ لا ربط خارج المجموعة"]],"sr":["MECH2 ص11","MECH2 ص15–16"],"asm":["منسوب المحور+0.60 م فوق الأرضية وقطر11.1 سم تمثيل رمزي غير معتمد للتنفيذ"]},
 "pipe_fp_branch":{"n":"فرع مرسوم داخل مجموعة الإطفاء","cf":"doc","sp":[["الموضع","بين جسم المضخة/الوعاء والمجمع في المسقط"]],"sr":["MECH2 ص11"],"asm":["منسوب المحور+0.60 م فوق الأرضية؛ قطر11.1 سم تمثيل رمزي"]},
}


def build(M,els,verbose=False):
    els[:]=[e for e in els if not ID_RE.search(e["id"])]
    if not os.path.exists(DATA):
        return {}
    D=json.load(open(DATA,encoding="utf-8"))
    for k,v in MATS.items():M.setdefault("mats",{}).setdefault(k,v)
    M.setdefault("types",{}).update(TYPES)
    refs=["مجموعة مضخات الإطفاء: مواقع أجسام المضخات والوعاء والمجمع من المسقط FF-101 (MECH2 ص11)؛ السعات والهوية من المخطط الرأسي FF-105 (MECH2 ص15)؛ التفاصيل من FF-106 (MECH2 ص16). لا تُنشأ مسارات من مخطط NTS."]
    for r in refs:
        if r not in M["sp"]:M["sp"].append(r)
    src=[M["sp"].index(r) for r in refs]
    ffl=next(l["ffl"] for l in M["levels"] if l["id"]=="G")
    n=0;stats=collections.Counter()
    def add(c,g,t,mark,a):
        nonlocal n
        n+=1;stats[t]+=1
        attrs={"sys":"fire","plan_source":"MECH2 ص11 FF-101","registration":"محاور المسقط؛ لا إزاحة"};attrs.update(a)
        e={"id":f"{c}-G-FP{n:04d}","c":c,"l":"G","g":g,"t":t,"mark":mark,"m":"p_fire_pump" if t.startswith("fp_") else "p_ff","a":attrs,"s":src}
        els.append(e)
    for p in D["pumps"]:
        x0,y0,x1,y1=p["bbox_cm"];h=.9 if p["kind"]=="jockey" else 1.2
        add("P.pump",["r",x0,y0,x1,y1,ffl,round(ffl+h,3)],"fp_"+p["kind"],p["mark"],
            {"assumed":f"الارتفاع{h:.2f} م افتراض؛ الغلاف مطابق لحدود الرمز المبسط؛ قاعه عند FFL+0.35 المرسوم؛ النوع Vertical Turbine من النص وليس استنتاجًا من شكل الرمز",
             "source_strokes":p["source_strokes"],"bbox_drawn_cm":p["bbox_cm"]})
    p=D["pressure_vessel"]
    add("P.pump",["cyl",*p["xy_cm"],round(p["diameter_cm"]/2,1),ffl,round(ffl+1.1,3)],"fp_pressure_vessel","PRESSURE VESSEL",
        {"assumed":"ارتفاع1.10 م افتراض؛ قطر45.4 سم من رمز المسقط ولا يعد مقاس توريد معتمدًا"})
    z=round(ffl+.6,3);dia=D["header"]["symbol_width_cm"]
    for t,lines in (("pipe_fp_header",[D["header"]["axis_cm"]]),("pipe_fp_branch",D["branches_cm"])):
        for i,pl in enumerate(lines,1):
            add("P.ff",["t",[[x,y,z] for x,y in pl],dia],t,"FF ASSEMBLY "+str(i),
                {"assumed":"محور المجموعة0.60 م فوق أرضية الغرفة افتراض؛ قطر التجسيم11.1 سم من عرض الرمز وليس قطرًا هيدروليكيًا معتمدًا",
                 "drawing_scope":"داخل حدود رمز مجموعة المضخات فقط؛ لا وصلة خارجية مستنتجة"})
    if verbose:print("fire pumps:",n,dict(stats))
    return dict(stats)
