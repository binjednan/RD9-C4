# -*- coding: utf-8 -*-
"""Floor-finish corrections for the basement and the utility rooms (owner 2026-10-07: «ابدأ التشطيبات»; 2026-10-08: «نعم مع تحديد في التفاصيل ماذا موجود في المخططات»).

The finish cells of the model (one rectangle per cell of the A500 grid) took their room kind from the nearest room label of the plan.  Two kinds of mistakes came out of that:

1. BASEMENT (A101): the whole open floor (drive way + car park + walk way, ≈ 1,608 m²) is one cell-component whose only labels are «6 m WIDE DRIVE WAY» and «LOBBY», so it became a granite lobby (F16)
   and later (first fix) one big car-park paint.  A101 itself says much more — read from the sheet's own layers (pipeline/extract_a101_zones.py → data/a101_zones.json):
   * the LOBBY is a drawn room (inner 540 × 380 cm, «AREA:20.62 M²», F.F.L. -3.50) — no longer an estimate;
   * layer A-PAIVING = interlock paving hatch = «Walk way (Basement): F13 & CPF-2» of A500 (472 m² of the open floor; BOQ F13 = 475 m²);
   * layer A-CAR = the parking bays (CSP-4 «car park deck coating, parking bays & pedestrian areas»);
   * the white remainder is the 6 m wide drive way (CSP-3); the ramp («M», 16.5 % / transition 8 %) is CSP-2 and is drawn as a sloped plate on the ramp slab itself.
   The plan area under the ramp slab carries no finish in the drawings, so no plate is drawn there.   Result (m²): CSP-3 + CSP-4 + CSP-2 ≈ 1,190 (BOQ 9.1.1.4.6 = 1,190, «basement driveway, car parking & ramp»).
2. Utility rooms whose labels are abbreviations the room-kind table did not know («TRA. RM» transformer room, «M.C.C» motor control centre, «GSM» telecom room) kept the
   default lobby granite -> they get the plant-room finish of A500 (F6).

Everything is idempotent (a second run finds every piece inside one zone and changes nothing) and every changed element carries a['fin_guess'] where the result is still an approximation
(zone borders read from hatch strokes, ±10 cm) so guesses.registry() lists it in the viewer's guesses list.
"""
import os, re, json, copy
from shapely.geometry import Polygon, box, MultiPolygon, LineString
from shapely.ops import unary_union
import finishes as FN

ZONES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "a101_zones.json")
NAME_KIND = [("TRA.", "trans"), ("M.C.C", "elec"), ("GSM", "tel")]
OPEN = ("lobby", "parking", "driveway", "walkway", "bay")      # basement cells that came from the open floor (earlier steps called all of it «lobby» then «parking»)
MIN_PIECE = 5000.0                                              # cm2 (0.5 m2): a zone must cover at least this much of a cell to cut it; smaller overlaps are hatch-edge noise
DUST = 100.0                                                    # cm2 (0.01 m2): anything smaller is dropped (a hairline of a zone border, not a piece of floor)
SRC = "ARCH1 ص4 (A101 مخطط البدروم): طبقات A-PAIVING وA-CAR وA-WALL + A500 (CSP-2/3/4 وF13) + BOQ 9.1.1.4.1 و9.1.1.4.6"
NOTE_LOBBY = ("ردهة المصاعد في البدروم مرسومة في A101 كغرفة داخلية 540×380 سم (مساحة مكتوبة 20.62 م²، F.F.L. -3.50) بين غرفة مضخة الصرف والمصعدين؛ تشطيبها حسب A500 «Corridor & Basement lobby»: "
              "F16+F17 / W7+W13 / C1")
NOTE_WALK = ("منطقة هاشور الإنترلوك (طبقة A-PAIVING) في A101 = «Walk way (Basement)» في A500: F13 رصف إنترلوك 60 مم مع بردورة + CPF-2؛ حدودها مقروءة من ضربات الهاشور (±10 سم) "
             "ومعنى الهاشور مستنتج من اسم الطبقة ومن مطابقة الكمية مع BOQ (472 م² مقابل 475) — بانتظار تأكيدك")
NOTE_BAY = ("مواقف السيارات (رموز طبقة A-CAR في A101؛ الموقف 2.70×5.50 م) = CSP-4 «Car park deck coating — parking bays & pedestrian areas» (600 ميكرون، ناعم) في A500؛ "
            "حدود المناطق مقروءة من الرسم — بانتظار تأكيدك")
NOTE_DRIVE = ("الممر «6 m WIDE DRIVE WAY» في A101 = CSP-3 «System for drive way» (840 ميكرون، حبيبات متوسطة) في A500: كل مساحة الأرضية المفتوحة خارج الهاشور والمواقف والمنحدر؛ "
              "حدود المناطق مقروءة من الرسم — بانتظار تأكيدك")
NOTE_RAMP = ("المنحدر «M» في A101 (ميل 16.5% وانتقالي 8%) = CSP-2 «System for ramp» (1240 ميكرون، حبيبات خشنة) في A500؛ رُسم كطبقة 1.2 سم على سطح البلاطة المنحدرة نفسها؛ "
             "ولا يحمل الجزء من أرضية البدروم تحت المنحدر أي تشطيب في المخطط فلم تُرسم له لوحة")
NOTE_ROOM = "وسم الغرفة اختصار لم يعرفه جدول أنواع الغرف فبقي على تشطيب الردهة؛ أُسند تشطيب غرف المعدات في A500 (F6) — بانتظار تأكيدك"
KINDS = {                                                        # kind -> (code, rooms, note, guess tag)
    "lobby": (FN.BY_KIND["lobby"][0], ["LOBBY"], NOTE_LOBBY, None),
    "walkway": ("F13", ["WALK WAY (BASEMENT)"], NOTE_WALK, "zone"),
    "bay": ("CSP-4", ["CAR PARK BAYS"], NOTE_BAY, "zone"),
    "driveway": ("CSP-3", ["DRIVE WAY"], NOTE_DRIVE, "zone"),
}


def _poly(g):
    if g[0] == "p": return Polygon(g[1], g[4] if len(g) > 4 and g[4] else None).buffer(0)
    if g[0] == "r": return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4]))
    return None


def _z(g):
    return (g[5], g[6]) if g[0] == "r" else (g[2], g[3])


def _parts(geom):
    return [q for q in (list(geom.geoms) if hasattr(geom, "geoms") else [geom]) if q.geom_type == "Polygon" and q.area >= DUST]


def _as_geom(poly, z0, z1):
    ext = [[round(x, 1), round(y, 1)] for x, y in list(poly.exterior.coords)[:-1]]
    holes = [[[round(x, 1), round(y, 1)] for x, y in list(h.coords)[:-1]] for h in poly.interiors if Polygon(h).area > 200]
    return ["p", ext, z0, z1, holes or None]


def _pool_idx(M, text):
    sp = M["sp"]
    if text not in sp: sp.append(text)
    return sp.index(text)


def _set_fin(e, code, kind, rooms, note, guess):
    a = e.setdefault("a", {})
    a["kind"] = kind; a["fin"] = [code]; a["room"] = rooms; a["note"] = note
    if guess: a["fin_guess"] = guess
    else: a.pop("fin_guess", None)
    e["mark"] = code; e["t"] = "floor_" + code; e["m"] = "fin_" + code


def _src(e, si):
    s = e.setdefault("s", [])
    if si not in s: s.append(si)


def _zones():
    Z = json.load(open(ZONES, encoding="utf-8"))
    pav = unary_union([Polygon(p["ext"], p["holes"] or None).buffer(0) for p in Z["paving"]])
    bay = unary_union([Polygon(p["ext"]).buffer(0) for p in Z["bays"]])
    return Z, box(*Z["lobby"]["rect"]), pav, bay


def _ramp_foot(els, lv):
    out = [LineString([(p[0], p[1]) for p in e["g"][1]]).buffer(e["g"][2] / 2.0, cap_style=2) for e in els if e["c"] == "S.ramp" and e["l"] == lv and e["g"][0] == "rs"]
    return unary_union(out) if out else Polygon()


def _split(P, lobby, ramp, pav, bay):
    """one open-floor cell -> [(kind, polygon)] by the drawing's zones (lobby room, ramp, interlock walk way, parking bays, the rest = drive way); slivers join the main piece"""
    rest = P; out = []
    for kind, zone in (("lobby", lobby), ("ramp", ramp), ("walkway", pav), ("bay", bay)):
        part = rest.intersection(zone)
        if (not part.is_empty) and part.area >= MIN_PIECE: out.append([kind, part]); rest = rest.difference(zone)
    if (not rest.is_empty) and rest.area >= DUST: out.append(["driveway", rest])
    if len(out) > 1:
        big = max(out, key=lambda k: k[1].area); keep = [big]
        for k in out:
            if k is big: continue
            if k[1].area < MIN_PIECE:
                if k[1].area >= DUST: big[1] = unary_union([big[1], k[1]]).buffer(0)       # a sliver joins the main piece (it may make it multi-part: the caller writes one element per part)
            else: keep.append(k)
        out = keep
    return out


def _ramp_plates(els, si):
    """CSP-2 finish plate (1.2 cm) on the sloped surface of every ramp strip (the strip's top = the polyline z; the plate sits on it)"""
    out = []
    for e in els:
        if e["c"] != "S.ramp" or e["g"][0] != "rs": continue
        pts = [[p[0], p[1], round(p[2] + 0.012, 3)] for p in e["g"][1]]; w = e["g"][2]
        L = sum(((pts[i + 1][0] - pts[i][0]) ** 2 + (pts[i + 1][1] - pts[i][1]) ** 2 + ((pts[i + 1][2] - pts[i][2]) * 100.0) ** 2) ** .5 for i in range(len(pts) - 1)) / 100.0
        out.append({"id": f"A.floor-{e['l']}-RAMP", "c": "A.floor", "l": e["l"], "g": ["rs", pts, w, 0.012], "mark": "CSP-2", "t": "floor_CSP-2", "m": "fin_CSP-2",
                    "a": {"kind": "ramp", "fin": ["CSP-2"], "room": ["CAR RAMP"], "note": NOTE_RAMP, "area_m2": round(L * w / 100.0, 1), "fin_guess": "zone"}, "s": [si]})
    return out


def apply(M, els):
    Z, lobby, pav, bay = _zones(); si = _pool_idx(M, SRC)
    els[:] = [e for e in els if not (e["c"] == "A.floor" and re.search(r"-RAMP$", e["id"]))]
    ramp = _ramp_foot(els, "B"); stats = {"lobby": 0, "walkway": 0, "bay": 0, "driveway": 0, "split": 0, "under_ramp_removed": 0, "rooms": 0}; area = {"under_ramp_m2": 0.0}
    used = {e["id"] for e in els}; add = []; drop = set()
    for e in els:
        if e["c"] != "A.floor" or e["l"] != "B": continue
        a = e.get("a") or {}
        if a.get("kind") not in OPEN or e["g"][0] not in ("p", "r"): continue
        P = _poly(e["g"])
        if P is None or P.is_empty or P.area < DUST: drop.add(e["id"]); continue                 # degenerate leftovers of an earlier split
        z0, z1 = _z(e["g"]); pieces = _split(P, lobby, ramp, pav, bay); base = re.sub(r"(-[LPZ]\d+)+$", "", e["id"]); first = True; n = 0
        proto = copy.deepcopy(e)
        for kind, geom in pieces:
            if kind == "ramp": area["under_ramp_m2"] += geom.area / 1e4; stats["under_ramp_removed"] += 1; continue
            code, rooms, note, guess = KINDS[kind]
            for q in _parts(geom):
                if first:
                    tgt = e; first = False
                else:
                    n += 1; nid = f"{base}-Z{n}"
                    while nid in used: n += 1; nid = f"{base}-Z{n}"
                    used.add(nid); tgt = copy.deepcopy(proto); tgt["id"] = nid; add.append(tgt); stats["split"] += 1
                tgt["g"] = _as_geom(q, z0, z1); _set_fin(tgt, code, kind, list(rooms), note, guess); _src(tgt, si); stats[kind] += 1
        if first: drop.add(e["id"])                       # the whole cell lies under the ramp: no finish plate
    els[:] = [e for e in els if e["id"] not in drop]
    els.extend(add)
    plates = _ramp_plates(els, si); els.extend(plates)
    # ---- utility rooms with abbreviated labels
    for e in els:
        if e["c"] != "A.floor": continue
        a = e.get("a") or {}
        if a.get("kind") is None and a.get("room") and a.get("fin") == ["F16"]:
            names = " ".join(a.get("room") or []).upper()
            for key, kind in NAME_KIND:
                if key in names:
                    _set_fin(e, FN.BY_KIND[kind][0], kind, a.get("room"), NOTE_ROOM, "room"); stats["rooms"] += 1; break
    stats["ramp_plates_m2"] = round(sum(p["a"]["area_m2"] for p in plates), 1); stats["under_ramp_m2"] = round(area["under_ramp_m2"], 1)
    stats["zones_src"] = Z["source"]
    return stats
