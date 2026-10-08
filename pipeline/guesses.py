# -*- coding: utf-8 -*-
"""Best-guess placement of the components that have no host in the model, and the registry of every guess (the viewer's «قائمة التخمينات»).

Owner 2026-10-07: «guess the most correct position of the components and list them in the guesses list, until the as-built drawings are approved».

relocate(): every element the support analysis left unsupported (no wall / ceiling / floor within reach of its plan symbol) gets the most plausible host:
    wall devices (sockets, switches, panels, exit signs, cameras, thermostats) -> the nearest wall / column / cladding face on the level (<= 300 cm), the device slides along the
                                                                                      shortest axis until its back touches the face (and is lowered / raised onto the wall if needed)
    ceiling devices (lights, detectors, grilles)                                  -> the false ceiling / slab / beam / stair soffit above it (<= 150 cm), else a wall within 150 cm
    floor-standing (earth pits, isolators on the roof)                            -> the slab / roof surface below, else the nearest wall
    FCU switches                                                                  -> the casing of the nearest FCU
  The original plan position is kept in a['guess_from'] = [x, y, z] together with the host and the distance, so the viewer can draw «before → after» and the reviewer can compare it with
  the as-built drawings.  Confidence: high <= 30 cm, medium <= 100 cm, low above (or a conversion between mount kinds).
registry(): collects every decision of this kind (relocations, wall snaps, stair-well mounts, FCU switches, buried drains, assumed sizes, schedule matches ...) plus the systematic
  assumptions of the type cards (253 types carry some), classified by kind (position / elevation / size / material / ...) and by impact, into M['guesses'] for the viewer."""
import math, collections, re
from shapely.geometry import Polygon, Point, box
from shapely.strtree import STRtree
from shapely.ops import nearest_points
import support as SUP

WALL_CATS = ("A.wall", "S.wall", "S.col", "A.clad", "A.fix", "A.rail")
CEIL_REACH_M = 1.5
WALL_REACH_CM = 300.0
KIND_AR = {"pos": "الموضع", "elev": "المنسوب", "host": "جهة التثبيت", "dim": "المقاس", "mat": "المادة / اللون", "qty": "العدد / الكمية", "repr": "التمثيل", "orient": "الاتجاه",
           "spec": "المواصفة", "pending": "بانتظار تأكيدك", "gen": "عام"}
IMPACT_AR = {"high": "مرتفع", "med": "متوسط", "low": "منخفض"}


def _pz(e):
    p = SUP.poly_of(e["g"]); z0, z1 = SUP.zr(e["g"])
    return p, z0, z1


def _move_xy(e, dx, dy):
    g = e["g"]
    if g[0] in ("b", "cyl"): g[1] = round(g[1] + dx, 1); g[2] = round(g[2] + dy, 1)
    elif g[0] == "r": g[1] = round(g[1] + dx, 1); g[3] = round(g[3] + dx, 1); g[2] = round(g[2] + dy, 1); g[4] = round(g[4] + dy, 1)


def _shift_z(e, dz):
    g = e["g"]
    if g[0] == "b": g[6] = round(g[6] + dz, 3); g[7] = round(g[7] + dz, 3)
    elif g[0] == "cyl": g[4] = round(g[4] + dz, 3); g[5] = round(g[5] + dz, 3)
    elif g[0] == "r": g[5] = round(g[5] + dz, 3); g[6] = round(g[6] + dz, 3)


def _centre(e):
    g = e["g"]
    if g[0] in ("b", "cyl"): return g[1], g[2]
    if g[0] == "r": return (g[1] + g[3]) / 2, (g[2] + g[4]) / 2
    return None


def _hosts(els):
    H = collections.defaultdict(lambda: {"wall": [], "ceil": [], "floor": [], "equip": []})
    for i, e in enumerate(els):
        c = e["c"]; lv = e["l"]
        if c in WALL_CATS or c == "S.beam":
            p, z0, z1 = _pz(e)
            if p is not None and not p.is_empty and z0 is not None: H[lv]["wall"].append((p, z0, z1, i))
        if c == "A.ceil":
            p, z0, z1 = _pz(e)
            if p is not None and not p.is_empty: H[lv]["ceil"].append((p, z0, i))
        if c == "S.slab":
            p, z0, z1 = _pz(e)
            if p is not None and not p.is_empty: H[lv]["ceil"].append((p, z0, i)); H[lv]["floor"].append((p, z1, i))
        if c in ("S.beam",):
            p, z0, z1 = _pz(e)
            if p is not None and not p.is_empty: H[lv]["ceil"].append((p, z0, i))
        if c in ("M.equip", "M.fan", "P.heater", "P.pump", "E.gen") and e["g"][0] in ("b", "r", "cyl"):
            p, z0, z1 = _pz(e)
            if p is not None and not p.is_empty and z0 is not None: H[lv]["equip"].append((p, z0, z1, i))
        if c in ("A.floor", "A.site", "S.raft"):
            p, z0, z1 = _pz(e)
            if p is not None and not p.is_empty: H[lv]["floor"].append((p, z1, i))
    return H


def intent_of(t, wall_types, samples):
    """how the component is meant to be mounted: 'wall' | 'ceil' | 'floor' (from the sample library: place.mount / anchor)"""
    if t in wall_types: return "wall"
    pl = (samples.get(t) or {}).get("place") or {}
    if pl.get("mount") == "wall": return "wall"
    if pl.get("anchor") == "top": return "ceil"
    return "floor"


def relocate(M, els, wall_types, samples=None):
    """moves every 'unsupported' element to its most plausible host; returns the ids moved and the ids that found no host"""
    samples = samples or {}
    H = _hosts(els); moved = []; failed = []
    fcus = collections.defaultdict(list)
    for i, e in enumerate(els):
        if e["c"] == "M.equip" and e.get("t") == "fcu" and e["g"][0] == "b": fcus[e["l"]].append(i)
    for i, e in enumerate(els):
        a = e.get("a") or {}
        if a.get("unsupported") and e["g"][0] in ("t", "d"):          # pipes / ducts with no support: a stand to the floor below, else a hanger to the soffit above (<= 2 m)
            zs = [p[2] for p in e["g"][1]]; half = (e["g"][2] / 200.0) if e["g"][0] == "t" else (e["g"][3] / 200.0)
            zmin, zmax = min(zs) - half, max(zs) + half; lv = e["l"]
            cx = sum(p[0] for p in e["g"][1]) / len(e["g"][1]); cy = sum(p[1] for p in e["g"][1]) / len(e["g"][1])
            from shapely.geometry import Point as _Pt
            P = _Pt(cx, cy); fl = [fz for (fp, fz, fi2) in H[lv]["floor"] if fz <= zmin + 0.02 and zmin - fz <= 3.0 and fp.buffer(60).contains(P)]
            ce = [cz for (cp, cz, ci) in H[lv]["ceil"] if cz >= zmax - 0.02 and cz - zmax <= 2.0 and cp.buffer(60).contains(P)]
            if fl or ce:
                if fl and (not ce or (zmin - max(fl)) <= (min(ce) - zmax)):
                    a["stand_cm"] = max(8, round((zmin - max(fl)) * 100)); kind = "stand"
                else:
                    a["hang_cm"] = max(8, round((min(ce) - zmax) * 100)); kind = "hang"
                a.pop("unsupported", None); a["guess_from"] = [round(cx, 1), round(cy, 1), round(zmin, 3)]; a["guess_kind"] = kind; a["guess_cm"] = 0.0; a["guess_dz_cm"] = 0.0; a["guess_conf"] = "med"
                a["mount_note"] = "تخمين: خط أنابيب بلا حامل في النموذج؛ الموضع كما في المسقط وأُضيف " + ("قائم" if kind == "stand" else "تعليق") + " — بانتظار تأكيد الأز-بيلت"
                e["a"] = a; moved.append(e["id"])
            continue
        if not a.get("unsupported") or e["g"][0] not in ("b", "cyl", "r"): continue
        lv = e["l"]; ctr = _centre(e); bp = SUP.poly_of(e["g"]); z0, z1 = SUP.zr(e["g"])
        if ctr is None or bp is None: continue
        old = [round(ctr[0], 1), round(ctr[1], 1), round(z0, 3)]
        t = e.get("t"); intent = intent_of(t, wall_types, samples); ffl = M_levels[lv]["ffl"]
        best = None          # (cost, kind, host index, (dx, dy, dz), why, conversion)
        def offer(cost, kind, hi, vec, why, conv=False):
            nonlocal best
            if best is None or cost < best[0]: best = (cost, kind, hi, vec, why, conv)
        # --- FCU switch: casing of the nearest FCU of the level (the FCU hangs in the ceiling void; the generic 1.30 m wall height left the switch in mid-air)
        if t == "e_P5":
            for fi in fcus[lv]:
                fb = SUP.poly_of(els[fi]["g"]); d = fb.distance(bp)
                if d <= 400:
                    pa, pb = nearest_points(bp, fb); dx, dy = pb.x - pa.x, pb.y - pa.y
                    if abs(dx) >= abs(dy): dy = 0.0
                    else: dx = 0.0
                    fz0, fz1 = SUP.zr(els[fi]["g"]); dz = (fz0 + 0.06) - z0
                    offer(d, "fcu", fi, (dx, dy, dz), "على غلاف أقرب وحدة FCU (المفتاح يخدمها)")
        # --- wall hosts (walls / columns / cladding only: never rails or cabinets)
        def walls(reach, conv):
            for (wp, wz0, wz1, wi) in H[lv]["wall"]:
                if wi == i or els[wi]["c"] not in ("A.wall", "S.wall", "S.col", "A.clad"): continue
                if els[wi]["c"] == "A.clad" and str(els[wi].get("t", "")).startswith(("grc_cornice", "clad_band")): continue      # decorative bands carry nothing
                d = wp.distance(bp)
                if d > reach: continue
                zc = (z0 + z1) / 2; dz = 0.0
                if zc > wz1:
                    if zc - wz1 > 0.8: continue                    # far above the wall top: not this wall
                    dz = (wz1 - 0.12) - z1
                elif zc < wz0:
                    if wz0 - zc > 0.3: continue                    # a lintel above a door is not a place for a socket
                    dz = (wz0 + 0.12) - z0
                pa, pb = nearest_points(bp, wp); dx, dy = pb.x - pa.x, pb.y - pa.y
                fx, fy = dx, dy
                if abs(dx) >= abs(dy): dy = 0.0
                else: dx = 0.0
                from shapely.affinity import translate as _tr
                if wp.distance(_tr(bp, dx, dy)) > 1.0: dx, dy = fx, fy                  # a corner approach: slide diagonally so the device really touches
                offer(d + abs(dz) * 60, "wall", wi, (dx, dy, dz), "على وجه أقرب جدار/عمود/كسوة", conv)
        # --- ceiling hosts above
        def ceilings():
            for (cp, cz, ci) in H[lv]["ceil"]:
                gap = cz - z1
                if gap < -0.02 or gap > CEIL_REACH_M or not cp.buffer(30).intersects(bp): continue
                cdx = cdy = 0.0
                if not cp.buffer(-4).intersects(bp):
                    pa, pb = nearest_points(bp, cp); vx, vy = pb.x - pa.x, pb.y - pa.y; L = math.hypot(vx, vy) or 1.0
                    cdx, cdy = vx + vx / L * 6.0, vy + vy / L * 6.0                 # 6 cm further in: the device really sits under the plate
                offer(gap * 100 * 0.6 + math.hypot(cdx, cdy), "ceil", ci, (cdx, cdy, gap), "على أقرب سقف/بلاطة/جسر فوقه")
        def floors():
            for (fp, fz, fi2) in H[lv]["floor"]:
                if fz > z0 + 0.02 or z0 - fz > 0.4 or not fp.buffer(5).intersects(bp): continue
                offer((z0 - fz) * 100, "floor", fi2, (0.0, 0.0, fz - z0), "على أقرب سطح أرضية/بلاطة تحته")
        if intent == "wall": walls(WALL_REACH_CM, False)
        elif intent == "ceil":
            ceilings()
            if best is None: walls(150, True)                       # no soffit above: wall bracket instead (conversion of the mount kind)
        else:
            floors()
            if best is None: walls(WALL_REACH_CM, True)
        if best is None and intent == "wall": walls(450, False)     # last resort: a wall up to 4.5 m away (low confidence)
        if best is None and intent == "wall":                        # machine isolators and similar: the casing of the nearest machine (<= 4 m)
            for (qp, qz0, qz1, qi) in H[lv]["equip"]:
                d = qp.distance(bp)
                if d > 400 or qi == i: continue
                pa, pb = nearest_points(bp, qp); dx, dy = pb.x - pa.x, pb.y - pa.y
                if abs(dx) >= abs(dy): dy = 0.0
                else: dx = 0.0
                dz = 0.0 if qz0 - 0.1 <= (z0 + z1) / 2 <= qz1 + 0.1 else ((qz0 + 0.6 * (qz1 - qz0)) - (z0 + z1) / 2)
                offer(d + 120 + abs(dz) * 40, "equip", qi, (dx, dy, dz), "على غلاف أقرب آلة (مفتاح عزل الآلة)", True)
        if best is None and intent != "wall": walls(450, True)
        if best is None:
            failed.append(e["id"]); continue
        cost, kind, hi, (dx, dy, dz), why, conv = best
        if kind == "wall" and math.hypot(dx, dy) > 150:
            mates = sum(1 for o in els if o is not e and o["l"] == lv and o.get("t") == t and (_centre(o) is not None) and math.hypot(_centre(o)[0] - ctr[0], _centre(o)[1] - ctr[1]) < 100)
            fl = [(fz, fi2) for (fp, fz, fi2) in H[lv]["floor"] if fp.buffer(5).intersects(bp) and fz <= z0 - 0.05]
            if mates >= 2 and fl:
                fz, fi2 = max(fl)
                a["guess_from"] = old; a["guess_host"] = els[fi2]["id"]; a["guess_kind"] = "stand"; a["guess_cm"] = 0.0; a["guess_dz_cm"] = 0.0; a["guess_conf"] = "low"; a["guess_intent"] = intent
                a["stand_cm"] = round((z0 - fz) * 100); a.pop("unsupported", None)
                a["mount_note"] = (f"تخمين: مجموعة من {mates + 1} أجهزة متجاورة بلا جدار/سقف قريب (أقرب مضيف {round(math.hypot(dx, dy))} سم)؛ الموضع كما في المسقط وأُضيف قائم من أرضية الدور ({els[fi2]['id']}) — بانتظار تأكيد الأز-بيلت")
                e["a"] = a; moved.append(e["id"]); continue
        _move_xy(e, dx, dy)
        if abs(dz) > 1e-6: _shift_z(e, dz)
        dist = math.hypot(dx, dy)
        host_set_z = kind in ("fcu", "ceil", "floor")                # the host fixes the height: only wall lowering / raising counts against the confidence
        bad_dz = 0.0 if host_set_z else abs(dz)
        conf = "high" if dist <= 30 and bad_dz <= 0.15 and not conv else ("med" if dist <= 100 and bad_dz <= 0.5 else "low")
        a["guess_from"] = old; a["guess_host"] = els[hi]["id"]; a["guess_kind"] = kind; a["guess_cm"] = round(dist, 1); a["guess_dz_cm"] = round(dz * 100, 1)
        a["guess_conf"] = conf; a["guess_intent"] = intent
        if conv: a["guess_conv"] = 1
        a.pop("unsupported", None)
        a["mount_note"] = ("تخمين: رمز المخطط بلا حامل قريب" + ("؛ التركيب المقصود سقفي ولا سقف تحته فركّب جداريًا" if conv else "") + f"؛ " +
                           (f"نُقل {round(dist)} سم" if dist >= 1 else "الموضع في المسقط كما هو") + (f" وعُدّل منسوبه {round(dz*100)} سم" if abs(dz) > 0.005 else "") + f" {why} ({els[hi]['id']}) — بانتظار تأكيد الأز-بيلت")
        e["a"] = a
        moved.append(e["id"])
    return moved, failed


M_levels = {}


def prepare(M):
    M_levels.clear()
    for l in M["levels"]: M_levels[l["id"]] = l


# ------------------------------------------------------------------------------------------------------------------------------------------ registry
STALE_NOTE = "لا يوجد جدار/سقف/أرضية مضيف قريب"
VERIFY = {"elev": "مناسيب التنفيذ / الأز-بيلت", "pos": "مواضع الأز-بيلت", "host": "تفاصيل التركيب في الأز-بيلت", "dim": "جداول ومقاسات المورد المعتمد", "mat": "اعتماد المواد والعينات من المالك",
          "qty": "BOQ المحدَّث بعد التنفيذ", "repr": "لا تحقق مطلوب (تمثيل للعرض)", "orient": "تفاصيل المورد المعتمد", "spec": "جداول المعدات المعتمدة", "pending": "قرار المالك / المصمم", "gen": "المخططات المعتمدة"}
KW = [("orient", ("اتجاه الفتح", "المفصلة", "اتجاه الواجهة")), ("repr", ("تمثيل", "بصري", "مبسّط", "مبسط", "للعرض", "إخراجي", "توضيحي", "تقريبي")),
      ("qty", ("عدد", "كمية", "BOQ", "الجمع", "مقابل المرسوم", "الجدول يعطي")), ("mat", ("لون", "مادة", "خامة", "ورنيش", "جرانيت", "رخام", "قماش", "خرسانة", "Mix")),
      ("dim", ("قطر", "مقاس", "أبعاد", "عرض", "سماكة", "طول", "حجم", "سعة", "عمق", "بصمة")), ("elev", ("منسوب", "ارتفاع", "فوق الأرضية", "فوق السقف", "أسفل البلاطة", "تحت البلاطة", "المستوى العالي", "فوق السطح")),
      ("pos", ("موضع", "مواضع", "مكان", "ترتيب"))]


def classify_asm(text):
    t = str(text)
    for kind, words in KW:
        if any(w in t for w in words): return kind
    return "gen"


def _impact(kind, text, cats):
    services = any(c[0] in "MPE" for c in cats)
    pending = "بانتظار تأكيدك" in text or "يحتاج تأكيد" in text or "تحتاج تأكيد" in text
    if kind in ("elev", "pos", "host") and services: return "high"
    if kind in ("dim", "qty", "spec") and services: return "med"
    if pending: return "med"
    if kind in ("elev", "pos", "host", "dim", "qty", "spec"): return "med" if kind in ("qty", "dim") else "low"
    return "low"


def registry(M, els):
    """collects every guess into M['guesses'] (rules + element-level items); element indexes are those of the final element list"""
    T = M.get("types", {}); LV = {l["id"]: l for l in M["levels"]}
    byt = collections.defaultdict(list); cats_by_type = collections.defaultdict(set)
    for i, e in enumerate(els):
        byt[e["t"]].append(i); cats_by_type[e["t"]].add(e["c"])
    rules = []; items = []

    def rule(rid, kind, impact, title, why, how, basis, verify, idxs=None, types=None, k=None):
        n = len(idxs) if idxs is not None else sum(len(byt[t]) for t in (types or []))
        if not n: return None
        r = {"id": rid, "kind": kind, "impact": impact, "title": title, "why": why, "basis": basis, "verify": verify or VERIFY.get(kind, ""), "n": n}
        if how: r["how"] = how
        if idxs is not None: r["els"] = idxs
        if types: r["types"] = sorted(types)
        rules.append(r); return r

    A = lambda e: e.get("a") or {}
    # --- element-level decisions
    reloc = [i for i, e in enumerate(els) if A(e).get("guess_from")]
    if reloc:
        rid = "G-RELOC"
        rule(rid, "pos", "high", "جهاز بلا حامل قريب — نُقل لأصحّ موضع", "رمز الجهاز في المخطط لا يقع قرب جدار أو سقف أو أرضية في النموذج فبقي معلّقًا في الهواء",
             "اختير أقرب مضيف يناسب طريقة تركيب نوع الجهاز (جداري / سقفي / أرضي / على غلاف آلة) وعُدّل الموضع ليلمسه؛ يبقى موضع المخطط الأصلي محفوظًا للمقارنة",
             "مكتبة العينات (طريقة التركيب) + هندسة النموذج (الجدران والأسقف والأرضيات)", "مواضع الأجهزة في الأز-بيلت (الكهرباء والتكييف)", idxs=reloc)
        for i in reloc:
            a = A(els[i]); items.append({"e": i, "r": rid, "from": a["guess_from"], "cm": a.get("guess_cm", 0), "dz": a.get("guess_dz_cm", 0), "host": a.get("guess_host"), "k": a.get("guess_kind"),
                                         "conf": a.get("guess_conf", "low"), "conv": a.get("guess_conv", 0)})
    snap = [i for i, e in enumerate(els) if A(e).get("snap_cm")]
    rule("G-SNAP", "pos", "med", "جهاز جداري سُحب إلى وجه الجدار", "رمز المخطط يبعد عن وجه الجدار فكان الجهاز يطفو أمامه",
         "سُحب الجهاز على محور أقصر مسافة حتى يلامس ظهره الجدار (حتى 80–120 سم)", "المخطط (موضع الرمز) + أقرب جدار", "الأز-بيلت: مواضع المقابس واللوحات", idxs=snap)
    for i in snap:
        a = A(els[i]); cm = a["snap_cm"]
        items.append({"e": i, "r": "G-SNAP", "cm": cm, "conf": "high" if cm <= 15 else ("med" if cm <= 50 else "low")})
    by_note = collections.defaultdict(list)
    for i, e in enumerate(els):
        n = str(A(e).get("mount_note") or "")
        if not n or n.startswith(STALE_NOTE) or A(e).get("guess_from") or n.startswith("تخمين:"): continue
        if "على غلاف الوحدة" in n or "غلاف الوحدة" in n: by_note["G-FCUSW"].append(i)
        elif "فتحة السلم/المصعد" in n: by_note["G-WELL"].append(i)
        elif "نُقل إلى سطح الدور R" in n: by_note["G-TR"].append(i)
        elif "الجدار المضيف أخفض" in n or "جدار بئر الدرج الخارجي" in n: by_note["G-LOW"].append(i)
        elif "مدفون في طبقة التسوية" in n: by_note["G-BURIED"].append(i)
    rule("G-FCUSW", "host", "med", "مفتاح وحدة FCU على غلاف الوحدة", "المفتاح مرسوم بجانب الوحدة وهي معلّقة في فراغ السقف؛ الارتفاع الافتراضي 1.30 م كان يتركه معلّقًا",
         "رُكّب على غلاف أقرب وحدة FCU في الطابق", "EP-103: مفتاح 15A لوحدة FCU + موضع الوحدة", "الأز-بيلت: موضع مفتاح الوحدة", idxs=by_note["G-FCUSW"])
    rule("G-WELL", "host", "med", "جهاز سقفي ثُبّت على جدار فتحة السلم/المصعد", "لا سقف مستعار داخل فتحة السلم/المصعد (A1401) فلا يوجد سقف يحمل الجهاز",
         "ثُبّت الجهاز على جدار الفتحة بنفس الارتفاع", "A1401 + مخططات الإنارة والإنذار", "الأز-بيلت: تركيب كشافات وكواشف الأدراج", idxs=by_note["G-WELL"])
    rule("G-TR", "pos", "med", "جهاز نُقل من الدور T إلى السطح R", "لا بلاطة علوية T تحت موضعه (الدور T غرف صغيرة على السطح)", "نُقل ليقوم على سطح الدور R", "مخطط السطح + S-19",
         "الأز-بيلت: مواضع تجهيزات السطح", idxs=by_note["G-TR"])
    rule("G-LOW", "elev", "low", "جهاز جداري خُفض ليلامس جدارًا أخفض من ارتفاع التركيب", "الجدار المضيف أقصر من ارتفاع التركيب الافتراضي", "خُفض الجهاز حتى يلامس قمة الجدار", "A604 + هندسة الجدار",
         "الأز-بيلت: ارتفاع الجدار والجهاز", idxs=by_note["G-LOW"])
    rule("G-BURIED", "elev", "med", "أنبوب صرف مدفون في طبقة التسوية بالقبو", "الأنبوب تحت أرضية المواقف فوق اللبشة (−3.90..−3.70 م): لا قضبان تعليق", "عُدّ مدفونًا بلا حوامل؛ العمق والغطاء غير محددين",
         "DR-100: مصرف أرضي تحت الأرض + فرشة الأنابيب المدفونة", "الأز-بيلت: مناسيب الصرف تحت أرضية القبو", idxs=by_note["G-BURIED"] or [i for i, e in enumerate(els) if A(e).get("buried")])
    # --- assumed sizes / schedule matches
    duct = [i for i, e in enumerate(els) if e["c"] == "M.duct" and "افتراضي" in str(A(e).get("size_note") or "")]
    rule("G-DUCTSZ", "dim", "med", "مقاس مجرى هواء افتراضي", "لا وسم مقاس قريب من هذه القطعة على المخطط", "أُعطي المقاس السائد في المجرى نفسه", "MECH1 (وسوم المجاري)", VERIFY["dim"], idxs=duct)
    drain = [i for i, e in enumerate(els) if e["c"] == "P.drain" and "افتراضي" in str(A(e).get("dia_note") or "")]
    rule("G-DRAINDIA", "dim", "med", "قطر أنبوب صرف افتراضي", "المخطط يسمّي الأقطار بالبوصة عند الأعمدة فقط", "قُدّر القطر حسب نوع الخط (110/80/50 مم)", "DR-100..105", VERIFY["dim"], idxs=drain)
    sched = [i for i, e in enumerate(els) if e["c"] == "M.equip" and A(e).get("sched_note")]
    rule("G-SCHED", "spec", "med", "مطابقة وحدة FCU بصف الجدول مستنتجة", "الوسم غير مقروء في المسقط أو الصف قُرئ بالعين أو يخص عدة أدوار", "ربطت الوحدة بصف AC-106 بالإقصاء/التماثل", "AC-106 + المسقط",
         VERIFY["spec"], idxs=sched)
    # --- finish decisions (pipeline/arch_finfix.py)
    park = [i for i, e in enumerate(els) if A(e).get("fin_guess") == "zone"]
    rule("G-PARK", "mat", "med", "مناطق تشطيب أرضية البدروم مقروءة من هاشور A101 (ممر CSP-3، مواقف CSP-4، منحدر CSP-2، مسار مشاة F13)",
         "A101 لا يضع وسم غرفة على الأرضية المفتوحة سوى «DRIVE WAY» و«LOBBY»، لكن طبقاته تحمل التقسيم: A-PAIVING = هاشور إنترلوك (472 م²، BOQ F13 = 475)، وA-CAR = رموز المواقف، والباقي ممر 6 م، والمنحدر M؛ "
         "وA500 يعرّف CSP-2 المنحدر وCSP-3 الممر وCSP-4 المواقف والمشاة وF13 «Walk way (Basement)»",
         "قُسّمت الأرضية المفتوحة بحدود هذه الطبقات (±10 سم): CSP-3 + CSP-4 + طبقة CSP-2 على سطح المنحدر ≈ 1,190 م² (BOQ 1,190)، وF13 ≈ 422 م² (BOQ 475 تشمل ما تحت المنحدر)؛ وردهة المصاعد غرفة مرسومة 540×380 سم (20.62 م²) لا تقدير",
         "A101 (A-PAIVING وA-CAR وA-WALL) + A500 (CSP-2/3/4 وF13) + BOQ 9.1.1.4.1 و9.1.1.4.6", "الأز-بيلت: تشطيب أرضية الممر والمواقف والمنحدر ومسار المشاة في البدروم (وهل هاشور الإنترلوك فعلًا F13)", idxs=park)
    rooms = [i for i, e in enumerate(els) if A(e).get("fin_guess") == "room"]
    rule("G-ROOMKIND", "mat", "low", "غرف معدات بوسوم مختصرة أُسند لها تشطيب غرف المعدات", "«TRA. RM» و«M.C.C» و«GSM» اختصارات لم يعرفها جدول أنواع الغرف فبقيت على تشطيب الردهة (F16)",
         "أُسند تشطيب غرف المعدات في A500 (F6)", "A103/A105 (وسوم الغرف) + A500", "A500: تشطيب هذه الغرف", idxs=rooms)
    wfin = [i for i, e in enumerate(els) if e["c"] == "A.wfin"]
    rule("G-WFIN", "elev", "med", "تكسية البلاط في الحمامات والمطابخ: ارتفاعها بملاحظة A500 والوجه والامتداد مقدَّران",
         "A500 يعطي رمز تشطيب الجدار (W4 مطبخ، W6 حمام، W9 غرفة القمامة) وملاحظة «Finishing to be extended 10 cm above false ceiling level»، ولا يحدد أي وجه من الجدار يحمل الرمز ولا هل التكسية بكامل الجدار أم خلف أدوات المطبخ فقط («Ceramic tiles… required behind the kitchen cabinet»)",
         "رُسمت طبقة بلاط 1.2 سم على وجوه الجدران المواجهة للغرف الرطبة من الأرضية حتى السقف المستعار 2.40 م + 10 سم = 2.50 م؛ والوجه يُقدَّر من الغرفة التي يواجهها؛ والمطابخ المفتوحة على المعيشة (20 من 30) غير مفصولة فلا طبقة لها",
         "A500 + حدود الغرف من المساقط", "الأز-بيلت: امتداد البلاط في المطابخ والحمامات وأوجه الجدران", idxs=wfin)
    # --- model-added closures
    strips = [i for i, e in enumerate(els) if e.get("mark") == "FLOOR-STRIP"]
    rule("G-STRIP", "pos", "low", "أشرطة سد الفراغ بين التشطيب والجدار", "خلايا التشطيب تنتهي قبل الجدار بـ4–10 سم فكان البلاط الإنشائي يظهر", "أُكملت الأشرطة بنفس تشطيب الخلية المجاورة", "هندسة النموذج", "الأز-بيلت: حدود التشطيب عند الجدران والعتبات", idxs=strips)
    bu = [i for i, e in enumerate(els) if e.get("t") == "floor_buildup"]
    rule("G-BUILDUP", "mat", "med", "طبقة التسوية تحت التشطيب", "تحت لوحة التشطيب فراغ 10 سم (45 سم في الأرضي، 20 سم في القبو) لا تحدد المستندات مكوّناته", "جسم صلب موحّد من البلاطة الإنشائية حتى أسفل التشطيب",
         "A500 + الفرق بين المناسيب", "الأز-بيلت: تفاصيل أرضية الأدوار", idxs=bu)
    drops = [i for i, e in enumerate(els) if e.get("t") == "sprk_drop"]
    rule("G-SPRKDROP", "dim", "low", "وصلات الرشاشات 25 مم", "المخطط يرسم رمز الرشاش فقط", "وصلة 1\" (NFPA 13) بين الرشاش وأنبوب الفرع", "FF-100..105 + NFPA 13", "الأز-بيلت: شبكة الرشاشات", idxs=drops)
    pile = [i for i, e in enumerate(els) if e["c"] == "S.pile"]
    rule("G-PILE", "repr", "low", "طول الخازوق للعرض 30 سم", "الطول الفعلي 13 م لا يُعرض كاملًا", "يُعرض 30 سم تحت اللبشة للدلالة", "STR ص11–12", VERIFY["repr"], idxs=pile)
    stage = [i for i, e in enumerate(els) if e["c"] == "A.stage"]
    rule("G-STAGE", "repr", "low", "كماليات إخراجية (أثاث، ستائر، نباتات، سيارات، ألعاب)", "غير مشمولة بالعقد؛ تُعرض لقراءة الفراغ فقط", "مواضعها وألوانها اقتراح للعرض وتُخفى بمفتاح واحد", "A2300 + الصور + اقتراح",
         "لا تحقق مطلوب (للعرض)", idxs=stage)
    # --- systematic assumptions of the type cards (every distinct statement = one rule, shared by all types that state it)
    by_text = collections.defaultdict(set)
    for tname, t in T.items():
        for s in (t.get("asm") or []): by_text[s].add(tname)
    for n, (text, tset) in enumerate(sorted(by_text.items(), key=lambda kv: -sum(len(byt[t]) for t in kv[1]))):
        kind = classify_asm(text); cats = set().union(*[cats_by_type[t] for t in tset]) if tset else set()
        types = [t for t in tset if byt[t]]
        title = text if len(text) <= 120 else text[:117] + "…"
        rule(f"A{n+1:03d}", kind, _impact(kind, text, cats), title, text, None, "بطاقة النوع (ما نصّت عليه المستندات وما افترضه النموذج)", VERIFY.get(kind, ""), types=types)
    M["guesses"] = {"kinds": KIND_AR, "impact": IMPACT_AR, "rules": rules, "items": items,
                    "summary": {"rules": len(rules), "items": len(items), "high": sum(1 for r in rules if r["impact"] == "high"), "med": sum(1 for r in rules if r["impact"] == "med"),
                                "low": sum(1 for r in rules if r["impact"] == "low")}}
    print("guesses registry:", M["guesses"]["summary"])
    return M["guesses"]
