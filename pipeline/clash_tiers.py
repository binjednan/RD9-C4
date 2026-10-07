# -*- coding: utf-8 -*-
"""Clash tiers, plain-language titles, suggested resolutions and groups (owner 2026-10-07: «حدد التعارضات: ما هو مؤكد تعارض، وما هو مرشح اختلاف منسوب، وما هو في القائمة»).

The old list showed 521 volumes of overlap between a service and a structural element with the same weight.  Most services (ducts, pipes, trays, FCUs) are drawn in plan only: their
elevation in the ceiling void is assumed, so an overlap with a beam may disappear when the service runs at another height.  Every clash is therefore classified by asking
«can the service be moved vertically inside the void and clear the obstruction?»:

  c  تعارض مؤكد              the overlap survives any elevation inside the void (column / concrete wall across the whole height, a beam deeper than the free height, two services that cannot
                             be stacked) or both elements have documented elevations   -> needs a sleeve / re-route / structural decision
  k  مرشح — اختلاف منسوب     a clear vertical band exists under (or over) the obstruction: the clash comes from the assumed elevation and disappears at the suggested level
  m  هامشي (في القائمة)       overlap thinner than 3 cm or smaller than 3 litres: drawing tolerance, listed for completeness only

Numbers (free band, needed clearance, suggested elevation) are stored on every clash so the viewer can show them; groups collect the clashes of one service run against one kind of
obstruction on one level, so one pipe crossing six beams is one issue with six places (the way Navisworks / ACC group clashes)."""
import math, collections
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
import support as SUP

MARGIN_M = 0.05
TIER_AR = {"c": "تعارض مؤكد", "k": "مرشح — اختلاف منسوب", "m": "هامشي (في القائمة)"}
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
        if (depth is not None and depth < 3.0) or c["v"] < 0.003:
            tier = "m"; why = "تداخل طفيف (أقل من 3 سم أو 3 لترات): فرق رسم/تقريب لا يستوجب إجراء"; fix = "لا إجراء؛ يُتحقق منه عند تنسيق الموقع"
        elif scat == "P.tank":
            tier = "c"; band = None
            why = "جسم الخزان في A2500 يتقاطع مع عنصر إنشائي في المخطط الإنشائي: خلاف بين الورقتين لا علاقة له بالمنسوب"
            fix = "طابق A2500 مع المخطط الإنشائي: اخصم العنصر الإنشائي من الحجم الصافي أو عدّل جدار الخزان"
        elif ocat in ("S.col", "S.wall"):
            tier = "c"; kind_ar = "العمود" if ocat == "S.col" else "الجدار/النواة الخرسانية"
            why = f"{kind_ar} يمتد على كل ارتفاع الدور فلا منسوب يتجنّبه؛ الخدمة تعبره في المسقط"
            fix = "كمّ عبور (sleeve) باعتماد المهندس الإنشائي أو تحويل المسار حول العنصر"
        elif ocat == "S.beam":
            under = oz0 - zc - thick                                        # clear height under the beam for a service of this thickness
            band = [round(zc, 2), round(oz0, 2)]
            if under >= MARGIN_M:
                tier = "k"; z_sug = oz0 - thick - MARGIN_M
                why = f"الجسر يهبط حتى {oz0:.2f} م وفوق السقف المستعار/الحد الأدنى ({zc:.2f} م) يبقى {oz0 - zc:.2f} م: الخدمة تمرّ أسفله إن خُفض منسوبها"
                fix = f"اضبط قمة الخدمة عند ≤ {z_sug + thick:.2f} م (مركزها ≈ {z_sug + thick / 2:.2f} م) لتمرّ تحت الجسر بخلوص {MARGIN_M*100:.0f} سم"
            else:
                tier = "c"
                why = f"أسفل الجسر ({oz0:.2f} م) لا يتسع لخدمة بسماكة {thick*100:.0f} سم فوق {zc:.2f} م: المتاح {max(0.0, oz0 - zc)*100:.0f} سم"
                fix = "كمّ عبر الجسر باعتماد المهندس الإنشائي، أو خفض السقف المستعار/تحويل المسار"
        elif ocat.startswith(("M.", "P.", "E.")):
            need_both = thick + othick + MARGIN_M
            band = [round(zc, 2), round(zs, 2)]
            if void_h >= need_both:
                tier = "k"; why = f"الخدمتان بمنسوبين افتراضيين؛ ارتفاع الفراغ {void_h:.2f} م يتسع لتراكبهما ({need_both:.2f} م)"
                fix = f"ضع إحداهما فوق الأخرى بخلوص {MARGIN_M*100:.0f} سم (الأنبوب أسفل المجرى عادة)"
            else:
                tier = "c"; why = f"ارتفاع الفراغ {void_h:.2f} م لا يتسع لتراكب الخدمتين ({need_both:.2f} م)"
                fix = "حوّل مسار إحداهما أو اخفض السقف المستعار موضعيًا"
        else:
            tier = "k"; why = "تقاطع بمنسوب افتراضي"; fix = "راجع المنسوب في مخطط التنفيذ"
        if scat == "M.equip" and ocat == "S.col" and tier != "m":
            tier = "c"; why = "وحدة التكييف تتداخل مع عمود في المسقط؛ الارتفاع لا يغيّر ذلك"; fix = "أزِح الوحدة عن العمود أو اعتمد موضعًا بديلًا"
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
    M["clashNote"] = ("تصنيف كل تعارض بالسؤال: هل تزول المشكلة بتغيير منسوب الخدمة داخل الفراغ؟ «مؤكد»: العنصر الإنشائي ممتد على كل الارتفاع أو لا يتسع الفراغ؛ "
                      "«مرشح — اختلاف منسوب»: يوجد نطاق خالٍ فتزول المشكلة عند المنسوب المقترح؛ «هامشي»: تداخل أقل من 3 سم أو 3 لترات. مناسيب الخدمات في فراغ السقف افتراضية، "
                      "وثقوب العبور عبر الجدران والجسور غير ظاهرة في النموذج وقد تكون مصمَّمة فعلًا.")
    print("clash tiers:", dict(stats), "| groups:", len(glist))
    return stats
