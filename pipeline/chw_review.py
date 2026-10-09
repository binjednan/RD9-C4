# -*- coding: utf-8 -*-
"""Compare the two CHW sheet sets without merging incompatible pipe routes."""
import collections
import copy
import json
import math
import os
import re
import sys
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

HERE=os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,HERE)
import lib
import mep_common as MC
import pipes as PP

DATA=os.path.join(HERE,"data","chw_review.json")
PAIRS=[("B",11,32,4),("G",12,33,5),("1",13,34,6),("TY",14,35,7),("R",15,36,8)]
DETAILS={
 "MECH1:9":["تفاصيل دعم مجاري التكييف والأنابيب وعبور الجدران والبلاطات؛ لا مواقع جديدة","الحد الأدنى لمجرى شفط الدخان 1.2 مم بغض النظر عن المقطع","مجرى شفط هود المطبخ مقاوم للحريق ساعتين وأقل سماكة 1.2 مم ولحام محكم"],
 "MECH1:10":["نفس AC-107-B والنصوص الهندسية لصفحة 9؛ تُراجع كصفحة مكررة، بلا هندسة مكررة"],
 "MECH1:29":["جدول FAHU: تغذية 3820 لتر/ث وشفط 3360 لتر/ث، قدرة مروحة 3.9 و3.4 kW؛ ملف تبريد 134 kW إجمالي/114 kW محسوس","ضغط ساكن 0.5 kPa؛ يجب إعادة حسابه بعد اعتماد المعدات","تشابك FAHU ومراوح الشفط مع إنذار الحريق؛ تصريف التكاثف إلى أقرب مصرف سطح، لكن مساره غير مرسوم","6 مراوح شفط بالجدول 70/45/80/60/85/130 لتر/ث؛ لا إضافة لمروحة من موضع اسم جدول"]}


def long_axes(sh,layer):
    out=[]
    # Return lines are dashed in the PDF. Merge only collinear dashes using
    # the established 14 cm dash gap, so their comparison has useful length.
    for a,b in PP.axis_merge(PP.layer_segments(sh,layer),gap=14 if layer=="M_CHI_R" else 8):
        if math.dist(a,b)<80 or not(abs(a[0]-b[0])<1 or abs(a[1]-b[1])<1):continue
        if all(-50<x<3300 and -100<y<1900 for x,y in (a,b)):out.append(LineString([a,b]))
    return out


def distance_sample(a,b):
    target=unary_union(b)
    samples=[]
    for line in a:
        for i in range(max(2,int(line.length/20)+1)):
            q=line.interpolate(i/(max(2,int(line.length/20)+1)-1),normalized=True)
            samples.append((target.distance(q),[round(q.x,1),round(q.y,1)]))
    if not samples:return None
    vals=sorted(v for v,q in samples)
    worst=max(samples,key=lambda q:q[0])
    return {"sample_count":len(samples),"median_cm":round(vals[len(vals)//2],1),
            "over_5cm":sum(v>5 for v,q in samples),"over_25cm":sum(v>25 for v,q in samples),
            "max_cm":round(worst[0],1),"max_at_cm":worst[1]}


def main_rings(sh,layer):
    return [{"xy_cm":[round(v,1) for v in q["c"]],"diameter_symbol_cm":round(q["w"],1)}
            for q in MC.closed_shapes(sh,layer)
            if q["n"]>=30 and 10<q["w"]<12 and 10<q["h"]<12
            and 800<q["c"][0]<1200 and 650<q["c"][1]<1150]


def collect():
    pairs=[]
    for lv,p1,p2,arch in PAIRS:
        ref=lib.Sheet("ARCH1",arch)
        a,b=lib.Sheet("MECH1",p1,ref=ref),lib.Sheet("MECH2",p2,ref=ref)
        row={"level":lv,"sheets":[f"MECH1:{p1}",f"MECH2:{p2}"],"registration":[a.reg,b.reg],"layers":{}}
        for ly in ("M_CHI_S","M_CHI_R"):
            ga,gb=long_axes(a,ly),long_axes(b,ly)
            ra,rb=main_rings(a,ly),main_rings(b,ly)
            r={"drawn_paths":[a.layers().get(ly,0),b.layers().get(ly,0)],
               "long_axis_count":[len(ga),len(gb)],"main_rings":[ra,rb],
               "set1_to_set2":distance_sample(ga,gb),"set2_to_set1":distance_sample(gb,ga)}
            if len(ra)==len(rb)==1:r["main_ring_delta_cm"]=round(math.dist(ra[0]["xy_cm"],rb[0]["xy_cm"]),1)
            row["layers"][ly]=r
        pairs.append(row)
    diffs=[
      {"field":"قدرة التبريد لكل مبرد","MECH1:16":"70 TR","MECH2:37":"76 TR"},
      {"field":"التدفق لكل مبرد","MECH1:16":"168 GPM","MECH2:37":"182.4 GPM"},
      {"field":"قدرة المبرد","MECH1:16":"110 kW","MECH2:37":"120 kW"},
      {"field":"تدفق مضخات CHW المقدر","MECH1:16":"168 GPM @100 ft","MECH2:37":"183 GPM @100 ft"},
      {"field":"تدفق الشبكة عند السطح","MECH1:16":"311.1 GPM","MECH2:37":"323.16 GPM"},
      {"field":"طول المبرد في الوسم التخطيطي","MECH1:16":"3.6 m","MECH2:37":"4.8 m"},
      {"field":"طول المبرد في جدول الصفحة نفسها","MECH1:16":"3.6 m","MECH2:37":"3.6 m"}]
    text1=lib.doc("MECH1")[8].get_text();text2=lib.doc("MECH1")[9].get_text()
    assert text1==text2,"AC details pages 9/10 differ; review the duplicate decision"
    for lv,p1,p2,arch in PAIRS:
        assert "30-03-2022" in lib.doc("MECH1")[p1-1].get_text()
        assert "09-02-2022" in lib.doc("MECH2")[p2-1].get_text()
    return {"reviewed_pages":{"MECH1":[9,10,11,12,13,14,15,16,29],"MECH2":[32,33,34,35,36,37]},
            "submission_dates":{"MECH1":"30-03-2022","MECH2":"09-02-2022"},
            "revision":"00 in both sets; Apr 12 2022 stamps in both",
            "geometry_comparison":pairs,"schedule_disagreements":diffs,
            "nonspatial_knowledge":DETAILS,
            "decision":"المجموعة الحالية من MECH1 محفوظة لأنها المسقط المستخدم وتقديمه متأخر؛ لا تُدمج شبكات MECH2 المخالفة. قبول التصميم التنفيذي يتطلب حسم إصدار معتمد.",
            "specific_conflicts":[
              {"location":"صاعد CHW الدور الأول/النمطي قرب اللوبي","kind":"اختلاف بين نسختي المخطط","sources":["MECH1 ص13–14","MECH2 ص34–35"],"note":"الموقع الفعلي للدائرة يقارن في main_rings؛ موضع نص CHW PIPES ليس موضع الصاعد"},
              {"location":"مبردا السطح x≈1165,1745 وy≈1626 سم","kind":"تعارض المسقط والجدول","sources":["MECH1 ص15–16","MECH2 ص36–37"],"note":"المسقط≈480×250 سم؛ جدول كلا النسختين 360×250 سم، ووسم ص37 وحده 480 سم. لا تصغير أو تكرار للأجسام."}]}


def apply_sources(M,els=None):
    """Add source evidence and visible equipment-card conflicts, without geometry."""
    if not os.path.exists(DATA):return {}
    d=json.load(open(DATA,encoding="utf-8"))
    M.setdefault("meta",{})["chw_source_review"]=d
    refs=["مراجعة نسختي مسقط CHW: MECH1 ص11–16 تقديم 30-03-2022 مقابل MECH2 ص32–37 تقديم 09-02-2022؛ اختلاف مواقع الصواعد والتدفقات والسعات، لا دمج لمسارات متعارضة.",
          "تفاصيل التكييف AC-107-B (MECH1 ص9–10): صفحتان متطابقتان؛ دعم وعزل وعبور حريق ومجرى دخان 1.2 مم وهود مطبخ مقاوم ساعتين؛ لا مواضع جديدة.",
          "جدول التهوية VE-106 (MECH1 ص29): FAHU تغذية 3820 وشفط 3360 لتر/ث، ملف 134/114 kW، ومراوح غرفة المضخات/القمامة/المولد والمحولات/LV/HV؛ المسارات لا تُشتق من الجدول."]
    for r in refs:
        if r not in M["sp"]:M["sp"].append(r)
    for typ,spec in {
        "chiller":[["تعارض جدول/مسقط","المسقط 480×250 سم؛ كلا الجدولين 360×250 سم"],["تعارض نسختي السعة","70 TR/110 kW مقابل 76 TR/120 kW؛ يلزم إصدار معتمد"]],
        "chwp":[["تعارض نسختي التدفق","168 مقابل 183 GPM عند 100 ft، كلاهما تقديري ويتطلب حساب المقاول"]],
        "fahu":[["جدول VE-106","تغذية 3820/شفط 3360 لتر/ث؛ قدرة تبريد 134 kW إجمالي و114 kW محسوس"],["التحكم والتكاثف","تشابك إنذار حريق؛ تصريف إلى أقرب RD، المسار غير مرسوم"]]}.items():
        if typ not in M.get("types",{}):continue
        t=M["types"][typ]
        for r in spec:
            if r not in t.setdefault("sp",[]):t["sp"].append(r)
        for sr in (["MECH2 ص37"] if typ in ("chiller","chwp") else ["MECH1 ص29"]):
            if sr not in t.setdefault("sr",[]):t["sr"].append(sr)
    for e in els if els is not None else M["els"]:
        if e.get("t")=="chiller":e.setdefault("a",{})["drawing_conflict"]="المسقط 480×250 سم والجدول 360×250 سم؛ اختلاف سعة بين نسختي CHW، بانتظار إصدار معتمد"
    return {"reviewed_pages":15,"geometry_changed":0}


if __name__=="__main__":
    d=collect()
    with open(DATA,"w",encoding="utf-8") as f:json.dump(d,f,ensure_ascii=False,indent=2)
    for p in d["geometry_comparison"]:
        print(p["level"],p["sheets"],[(k,v.get("main_ring_delta_cm"),v["long_axis_count"]) for k,v in p["layers"].items()])
    print("CHW sources reviewed: 15 pages; incompatible routes kept separate")
