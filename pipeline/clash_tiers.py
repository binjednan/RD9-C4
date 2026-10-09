# -*- coding: utf-8 -*-
"""Legacy clash priority, titles, local height hints and groups.

c means a model overlap which needs coordination; k means a possible height or
shape correction; m means a small volume/depth. None of these labels verifies
source bounds, drawing tolerance, site conditions or acceptance. A local clear
band is a diagnostic hint, not a solved route or an approved penetration.

Vertical routes cannot be stacked using their story length as thickness.
Nonpositive ceiling voids are unknown. Water domains and possibly shared tank
concrete require semantic review. Canonical source confidence is returned by
coordination_review.audit with separate 3-D and plan-crossing evidence.
"""
import math, collections
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
import support as SUP

MARGIN_M = 0.05
TIER_AR = {"c": "تداخل يحتاج تنسيقًا", "k": "مرشح منسوب أو شكل", "m": "أثر صغير يحتاج تحققًا"}
OBS_AR = {"S.col": "عمود خرساني", "S.wall": "جدار/نواة خرسانية", "S.beam": "جسر خرساني", "M.duct": "مجرى هواء", "M.pipe": "أنبوب", "P.": "أنبوب"}
ROLE_SERVICE = ("M.", "P.", "E.")


def _svc_geom(e):
    """(shapely 2-D shape, z0, z1, thickness_m) of a service element"""
    g = e["g"]; k = g[0]
    if k == "t":
        pts = g[1]; r = g[2] / 2.0; segs = [LineString([(a[0], a[1]), (b[0], b[1])]).buffer(r) for a, b in zip(pts[:-1], pts[1:]) if math.hypot(b[0] - a[0], b[1] - a[1]) > 0.5]
        zs = [p[2] for p in pts]
        return (unary_union(segs) if segs else None), min(zs) - r / 100.0, max(zs) + r / 100.0, g[2] / 100.0
    if k == "d":
        pts = g[1]; w = g[2] / 2.0; segs = [LineString([(a[0], a[1]), (b[0], b[1])]).buffer(w, cap_style=2) for a, b in zip(pts[:-1], pts[1:]) if math.hypot(b[0] - a[0], b[1] - a[1]) > 0.5]
        zs = [p[2] for p in pts]; h = g[3] / 100.0
        return (unary_union(segs) if segs else None), min(zs) - h / 2, max(zs) + h / 2, h
    p = SUP.poly_of(g); z0, z1 = SUP.zr(g)
    return p, z0, z1, (z1 - z0) if z0 is not None else 0.0


class _Voids:
    """for a point and an elevation: the top of the false ceiling below it and the soffit (slab / beam bottom) above it, searching every level
    (the drains of level N hang under the slab of level N, i.e. in the ceiling void of the level below)"""
    def __init__(self, els, LV):
        self.LV = LV; self.ceil = []; self.slab = []
        for e in els:
            if e["c"] == "A.ceil":
                p = SUP.poly_of(e["g"]); z0, z1 = SUP.zr(e["g"])
                if p is not None and not p.is_empty: self.ceil.append((p, z1))
            elif e["c"] == "S.slab":
                p = SUP.poly_of(e["g"]); z0, z1 = SUP.zr(e["g"])
                if p is not None and not p.is_empty: self.slab.append((p, z0, z1))
        self.floors = sorted((l["ffl"], l["id"]) for l in LV.values())

    def at(self, x, y, zmid):
        from shapely.geometry import Point
        P = Point(x, y); zc = None; zs = None
        for (p, z1) in self.ceil:
            if z1 <= zmid + 0.02 and p.contains(P) and (zc is None or z1 > zc): zc = z1
        for (p, z0, z1) in self.slab:
            if z0 >= zmid - 0.02 and p.contains(P) and (zs is None or z0 < zs): zs = z0
        have_ceil = zc is not None
        if zc is None:
            below = [f for f, _ in self.floors if f <= zmid + 0.02]
            zc = (max(below) if below else self.floors[0][0]) + 2.40          # no false ceiling here (car park, plant room): clear height 2.40 m
        if zs is None: zs = zmid + 0.5
        return zc, zs, have_ceil


def classify(M, els):
    LV = {l["id"]: l for l in M["levels"]}; T = M.get("types", {}); C = M.get("clashes", [])
    V = _Voids(els, LV)
    groups = collections.OrderedDict(); stats = collections.Counter()
    tname = lambda e: (T.get(e.get("t")) or {}).get("n") or e.get("t") or e["c"]
    for c in C:
        A, B = els[c["a"]], els[c["b"]]; k = c["k"]; lv = c["l"]
        svc, obs = A, B                                                    # the first element is always the service (the one whose elevation is assumed)
        sg, sz0, sz1, thick = _svc_geom(svc)
        og, oz0, oz1, othick = _svc_geom(obs)
        x_cm, y_cm, zmid = c["pt"][0] * 100, -c["pt"][2] * 100, c["pt"][1]
        zc, zs, have_ceil = V.at(x_cm, y_cm, zmid)
        void_h = zs - zc
        depth = None
        try:
            if sg is not None and og is not None:
                inter = sg.intersection(og)
                if not inter.is_empty:
                    bx = inter.bounds; depth = min(bx[2] - bx[0], bx[3] - bx[1])
        except Exception:
            pass
        tier = "k"; why = ""; fix = ""; band = None
        ocat = obs["c"]; scat = svc["c"]
        vertical = any((e.get("a") or {}).get("shaft") or str(e.get("t", "")).startswith(("riser_", "storm_stack")) for e in (svc, obs))
        water_domain = any(e.get("t") == "tank_water" for e in (svc, obs))
        shared_concrete = scat == "P.tank" and svc.get("t") == "tank_wall" and ocat.startswith("S.")
        void_valid = zs > zc
        c.pop("band", None)
        c["classification_checks"] = {"vertical_route": bool(vertical), "water_domain": water_domain,
                                       "possible_shared_concrete": shared_concrete, "void_positive": void_valid,
                                       "source_confirmation": "not established by legacy tier"}
        if water_domain:
            tier = "k"
            why = "حجم الماء الحسابي يتقاطع مع عنصر في المجسم؛ هذا ليس جسم خدمة صلبًا ولا يثبت وحده تصادمًا ماديًا"
            fix = "تحقق من حدود الخزان وصافي حجم الماء والعناصر الداخلية في المصدر؛ لا نقل للعمود أو تعديل الجدار دون حسم"
        elif shared_concrete:
            tier = "k"
            why = "جدار الخزان والعنصر الإنشائي قد يمثلان اتصالًا مقصودًا أو وصفين لجسم خرساني مشترك"
            fix = "طابق المسقط والقطاع والدلالة الإنشائية قبل تصنيفه كتصادم غير مقصود"
        elif not void_valid:
            tier = "k"
            why = "حدود الفراغ الرأسي المحسوبة غير موجبة؛ لا تصلح للحكم على إمكان المرور أو التكديس"
            fix = "تحقق من المستوى والحدود الرأسية الفعلية للمضيف والخدمة؛ لا اقتراح منسوب من هذا الفراغ"
        elif vertical:
            tier = "k"
            why = "مسار رأسي يتداخل في المجسم؛ طوله بين الطوابق ليس سماكة قابلة للتكديس في فراغ السقف"
            fix = "راجع مقطع الصاعد وفتحة العبور وموضع الخدمات في المسقط؛ لا يفترض حله بوضع أحد الصاعدين فوق الآخر"
        elif (depth is not None and depth < 3.0) or c["v"] < 0.003:
            tier = "m"; why = "أثر صغير بحسب عتبة العمق أو الحجم؛ لا تثبت هذه العتبة سماحة رسم مقبولة"; fix = "تحقق من المصدر والمقاس والدلالة قبل إغلاق الحالة"
        elif ocat in ("S.col", "S.wall"):
            tier = "c"; kind_ar = "العمود" if ocat == "S.col" else "الجدار/النواة الخرسانية"
            why = f"الخدمة تعبر مسقط {kind_ar} وتتداخل معه ضمن حدودZ الحالية في المجسم؛ دليل المصدر وحدود الامتداد والعبور يحتاج تحققًا"
            fix = "تحقق من الموضع والقطاع وفتحة العبور؛ أي sleeve أو تحويل مسار يحتاج قرارًا تصميميًا"
        elif ocat == "S.beam":
            under = oz0 - zc - thick                                        # clear height under the beam for a service of this thickness
            band = [round(zc, 2), round(oz0, 2)]
            if under >= MARGIN_M:
                tier = "k"; z_sug = oz0 - thick - MARGIN_M
                why = f"الجسر يهبط حتى {oz0:.2f} م وفوق السقف المستعار/الحد الأدنى ({zc:.2f} م) يبقى {oz0 - zc:.2f} م: الخدمة تمرّ أسفله إن خُفض منسوبها"
                fix = f"اضبط قمة الخدمة عند ≤ {z_sug + thick:.2f} م (مركزها ≈ {z_sug + thick / 2:.2f} م) لتمرّ تحت الجسر بخلوص {MARGIN_M*100:.0f} سم"
            else:
                tier = "c"
                why = f"الفراغ المحلي المحسوب تحت الجسر ({oz0:.2f} م) لا يتسع لسماكة المجسم {thick*100:.0f} سم فوق {zc:.2f} م؛ هذا حكم على الأبعاد والحدود الحالية لا اعتماد مصدر"
                fix = "تحقق من مقاس الخدمة ومنسوبها وحد الفراغ وفتحات العبور قبل قرار تغيير السقف أو المسار"
        elif ocat.startswith(("M.", "P.", "E.")):
            need_both = thick + othick + MARGIN_M
            band = [round(zc, 2), round(zs, 2)]
            if void_h >= need_both:
                tier = "k"; why = f"الخدمتان بمنسوبين افتراضيين؛ ارتفاع الفراغ {void_h:.2f} م يتسع لتراكبهما ({need_both:.2f} م)"
                fix = f"ضع إحداهما فوق الأخرى بخلوص {MARGIN_M*100:.0f} سم (الأنبوب أسفل المجرى عادة)"
            else:
                tier = "c"; why = f"ارتفاع الفراغ المحلي المحسوب {void_h:.2f} م لا يتسع لأبعاد المجسم الحالية ({need_both:.2f} م)؛ يلزم تحقق المصدر"
                fix = "تحقق من المقاسات والمناسيب وحدود الفراغ والمسار كاملًا قبل اقتراح تحويل أو تغيير السقف"
        else:
            tier = "k"; why = "تقاطع بمنسوب افتراضي"; fix = "راجع المنسوب في مخطط التنفيذ"
        if (scat == "M.equip" and ocat == "S.col" and tier != "m"
                and void_valid and not vertical and not water_domain and not shared_concrete):
            tier = "c"; why = "وحدة التكييف تتداخل مع مسقط العمود وحدوده الحالية في المجسم؛ مصدر الموضع وحدودZ يحتاج تحققًا"; fix = "تحقق من مسقط المعدة والعمود والقاعدة والارتفاع قبل اعتماد موضع بديل"
        sysname = next((s_[1] for L_ in M["layers"] for s_ in L_["subs"] if s_[0] == scat), scat)
        obsn = OBS_AR.get(ocat) or (tname(obs) if ocat[0] in "MPE" else ocat)
        svc_t = tname(svc)
        gk = f"{svc['id']}|{ocat}|{lv}"
        c["tier"] = tier; c["why"] = why; c["fix"] = fix; c["sys"] = sysname; c["obs"] = obsn; c["svc"] = svc_t; c["gk"] = gk
        if band: c["band"] = band
        c["need"] = round(thick, 3)
        if depth is not None: c["depth"] = round(depth, 1)
        c["void"] = [round(zc, 2), round(zs, 2), 1 if have_ceil else 0]
        c["sid"] = svc["id"]; c["oid"] = obs["id"]
        g = groups.setdefault(gk, {"k": gk, "n": 0, "tiers": collections.Counter(), "sys": sysname, "obs": obsn, "svc": svc_t, "l": lv, "sid": svc["id"], "v": 0.0})
        g["n"] += 1; g["tiers"][tier] += 1; g["v"] += c["v"]
        stats[tier] += 1
    glist = []
    for g in groups.values():
        t = "c" if g["tiers"]["c"] else ("k" if g["tiers"]["k"] else "m")
        n = g["n"]
        title = f"{g['svc']} × {g['obs']}" + (f" ({n} موضعًا)" if n > 1 else "")
        glist.append({"k": g["k"], "n": n, "t": t, "tc": g["tiers"]["c"], "tk": g["tiers"]["k"], "tm": g["tiers"]["m"], "sys": g["sys"], "obs": g["obs"], "svc": g["svc"], "l": g["l"],
                      "title": title, "v": round(g["v"], 3), "sid": g["sid"]})
    glist.sort(key=lambda g: ({"c": 0, "k": 1, "m": 2}[g["t"]], -g["tc"], -g["v"]))
    M["clashGroups"] = glist
    M["clashTiers"] = {"c": TIER_AR["c"], "k": TIER_AR["k"], "m": TIER_AR["m"]}
    M["clashNote"] = ("هذه درجات أولوية لتداخلات المجسم،وليست تأكيدًا من المصدر أو الموقع. حدود الفراغ والمقاسات والمناسيب قد تكون مفترضة؛ "
                      "الاقتراح الرأسي فحص موضعي ولا يثبت صلاحية المسار كاملًا. الصواعد لا تُكدّس بطولها،وحجم الماء يحتاج مراجعة صافي السعة، "
                      "والأثر الصغير لا يساوي سماحة رسم مقبولة. الحكم المستقل للمصدر في coordination_review؛فتحات العبور غير الممثلة تحتاج تحققًا.")
    print("clash tiers:", dict(stats), "| groups:", len(glist))
    return stats
