# -*- coding: utf-8 -*-
"""Kit generator: applies drawing SAMPLES (assemblies) to every host that matches (work order item 9).  Output is DATA for pipeline/generated_layer.py.

  python3 pipeline/kits.py [--only fcu_chw]     # reads src/model.json (generated members are ignored), writes pipeline/data/generated/<family>.json

Determinism: same input -> same bytes (sorted, fixed formatting).  Run order: post_model -> kits -> post_model (see pipeline/rebuild.py).
Nothing existing is moved: components are placed ON the carrier path (its axis untouched); the carrier keeps passing through them (overlay).
Every generated element carries a.basis='sample', a.sample{id,sheet,version}, a.assembly{id,kit,slot,carrier}, a.kit_ports (A toward the host, B away),
a.joint on each port, and a.assumed listing what is a choice of this generator and not a statement of the drawings.
"""
import copy, json, math, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import ports as P, pipe_dimensions as PD, generated_layer as GEN
LIBDIR = os.path.join(HERE, "data", "library"); OUTDIR = os.path.join(HERE, "data", "generated")
MODEL = os.path.join(ROOT, "src", "model.json")
GAP_CM = 0.0

def jload(p): return json.load(open(p, encoding="utf-8"))
def components(): return jload(os.path.join(LIBDIR, "components.json"))
def kit_def(kid): return jload(os.path.join(LIBDIR, "kits", kid + ".json"))

# ---------- geometry helpers (x,y cm ; z metres) ----------
def p3(q): return (q[0], q[1], q[2] * 100.0)
def seglen(a, b): return math.dist(p3(a), p3(b))
def lerp(a, b, t): return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]

class Carrier:
    """A walk from the host outward over one carrier path (plus end-to-end neighbours of the same family and DN when it is too short).
    Components are placed on straight intervals only (never across a vertex)."""
    def __init__(self, el, pts, extend=None):
        self.el = el                                    # the drawn carrier that touches the host (first piece)
        self.pieces = [(el, [list(q) for q in pts])] + [(e2, [list(q) for q in p2]) for e2, p2 in (extend or [])]
        self.segs = []; cum = 0.0
        for e, pp in self.pieces:
            for i in range(len(pp) - 1):
                L = seglen(pp[i], pp[i + 1]); self.segs.append((e, pp[i], pp[i + 1], cum, cum + L)); cum += L
        self.cursor = 0.0; self.pts = self.pieces[0][1]
    def point_at(self, s):
        for e, A, B, s0, s1 in self.segs:
            if s0 <= s <= s1 and s1 - s0 > 1e-9: return lerp(A, B, (s - s0) / (s1 - s0)), e
        return None
    def place(self, length_cm, start=None):
        s = self.cursor if start is None else start
        for e, A, B, s0, s1 in self.segs:
            if s1 - s0 < 1e-9: continue
            lo = max(s, s0)
            if lo + length_cm <= s1 + 1e-9:
                t0, t1 = (lo - s0) / (s1 - s0), (lo + length_cm - s0) / (s1 - s0)
                self.cursor = lo + length_cm + GAP_CM
                return lerp(A, B, t0), lerp(A, B, t1), e
        return None

def mk_element(cat, level, kit, host, slot, typ, mat, geom, a, src):
    return {"id": GEN.element_id(cat, level, kit, host, slot), "c": cat, "l": level, "g": geom, "t": typ, "m": mat, "mark": None, "a": a, "src": src}

def port(end, xyz, sys_, dn, joint, basis="carrier"):
    return {"end": end, "xyz": [round(xyz[0], 3), round(xyz[1], 3), round(xyz[2], 4)], "sys": sys_, "dn_mm": dn, "dn_basis": basis, "joint": joint}

def joint_for(fam, dn):
    if fam in ("chw_s", "chw_r", "fire"): return "threaded" if dn <= 40 else "flanged"
    if fam in ("cold", "hot"): return "socket_coupling"
    return "socket_coupling"

class Builder:
    def __init__(self, kit, comps, host, carrier_by_line):
        self.kit = kit; self.comps = comps; self.host = host; self.els = []; self.slots = {}; self.assumed = list(kit.get("assumed", []))
        self.sample = dict(kit["sample"]); self.aid = "ASM:%s:%s" % (kit["id"], host["id"])
    def base_attrs(self, slot, carrier_id, extra=None):
        a = {"basis": "sample", "sample": dict(self.sample), "assembly": {"id": self.aid, "kit": self.kit["id"], "slot": slot, "carrier": carrier_id},
             "assumed": "; ".join(self.assumed), "source_graphic": 1}   # source_graphic: the life-cycle (network test) engine skips overlays; their connectivity is judged by ports
        if extra: a.update(extra)
        return a
    def add(self, slot, el):
        self.els.append(el); self.slots[slot] = el["id"]
    def inline(self, slot, kind, carrier, fam, dn, od_bare, jacket, level, src, mn=None):
        c = self.comps["kinds"][kind]; L = c["length_mm"][str(dn)] / 10.0 if str(dn) in c["length_mm"] else None
        if L is None:
            ks = sorted(int(k) for k in c["length_mm"]); k = min(ks, key=lambda x: abs(x - dn)); L = c["length_mm"][str(k)] / 10.0; self.assumed.append("%s length for DN%d taken from DN%d" % (kind, dn, k))
        r = carrier.place(L)
        if r is None: return None
        q0, q1, hosting = r
        body = max(c["body_k"] * od_bare, ((jacket or od_bare) + 15.0)) / 10.0
        j = joint_for(fam, dn)
        a = self.base_attrs(slot, hosting["id"], {"component": kind, "component_name": c["name"], "length_cm": round(L, 2), "body_d_cm": round(body, 2), "length_basis": c["length_basis"] if isinstance(c["length_basis"], str) else json.dumps(c["length_basis"]),
                                                      "kit_ports": [port("A", q0, fam, dn, j), port("B", q1, fam, dn, j)]})
        self.add(slot, mk_element(hosting["c"], level, self.kit["id"], self.host["id"], slot, c["type"], c["mat"], ["t", [[round(v, 3) for v in q0], [round(v, 3) for v in q1]], round(body, 3)], a, src))
        return q0, q1
    def side(self, slot, kind, carrier, fam, dn, od_bare, jacket, level, src, at_s=None):
        c = self.comps["kinds"][kind]; w = c["stub_d_mm"] / 10.0
        r = carrier.place(0.0, start=at_s)   # a side fitting sits AT the junction between two neighbours and takes no length
        if r is None: return None
        q0, q1, hosting = r; m = lerp(q0, q1, 0.5)
        h = c["stub_len_mm"] / 10.0 / 100.0 + 0.0
        top = [m[0], m[1], m[2] + (-h if c.get("down") else h)]
        j = joint_for(fam, dn)
        a = self.base_attrs(slot, hosting["id"], {"component": kind, "component_name": c["name"], "length_cm": round(c["stub_len_mm"] / 10.0, 2), "body_d_cm": round(w, 2), "length_basis": c["length_basis"],
                                                      "kit_ports": [port("A", m, fam, dn, j)]})
        self.add(slot, mk_element(hosting["c"], level, self.kit["id"], self.host["id"], slot, c["type"], c["mat"], ["t", [[round(v, 3) for v in m], [round(v, 3) for v in top]], round(w, 3)], a, src))
        return m
    def assembly(self, carriers):
        return {"id": self.aid, "kit": self.kit["id"], "kit_version": self.kit["version"], "host": self.host["id"], "carriers": sorted(set(carriers)), "sample": dict(self.sample), "slots": dict(sorted(self.slots.items()))}

def extend_chain(el, far_end, by, peers, famcache, hops):
    """Follow end-to-end joins (same family and DN label) from the far end of a carrier; returns [(element, pts oriented outward)]."""
    out = []; cur = el; end = far_end; seen = {el["id"]}
    for _ in range(hops):
        cands = []
        for q in peers.get(cur["id"] + "#" + end, ()):
            eid, qend = q.rsplit("#", 1)
            o = by.get(eid)
            if o is None or eid in seen or famcache.get(eid) != famcache.get(el["id"]): continue
            if o["a"].get("dn_label_mm") != el["a"].get("dn_label_mm"): continue
            cands.append((eid, qend))
        if not cands: break
        eid, qend = sorted(cands)[0]; o = by[eid]; pts = o["g"][1]
        out.append((o, pts if qend == "S" else pts[::-1])); seen.add(eid); cur = o; end = "E" if qend == "S" else "S"
    return out

def _place_line(b, kit, comps, car, line, fam, label, h, src):
    e = car.el; dn = int(e["a"].get("dn_label_mm") or label); od = float(e["a"].get("od_mm") or 26.7); jk = e["a"].get("jacket_od_mm")
    order = sorted((x for x in kit["slots"] if x["line"] == line and not x.get("side_of")), key=lambda x: x["order_from_host"]) + [x for x in kit["slots"] if x["line"] == line and x.get("side_of")]
    for sl in order:
        c = comps["kinds"][sl["component"]]
        res = b.side(sl["slot"], sl["component"], car, fam, dn, od, jk, h["l"], src) if c.get("side") else b.inline(sl["slot"], sl["component"], car, fam, dn, od, jk, h["l"], src)
        if res is None: return False
    return True

def model_without_generated():
    M = jload(MODEL)
    M["els"] = [e for e in M["els"] if not (e.get("a") or {}).get("assembly")]
    return M

def local_to_global(host, lx, ly):
    g = host["g"]; th = math.radians(g[5])
    return g[1] + lx * math.cos(th) - ly * math.sin(th), g[2] + lx * math.sin(th) + ly * math.cos(th)

# ---------- family: FCU ----------
def gen_fcu(M, comps):
    from shapely.geometry import Point
    kit = kit_def("fcu_chw"); by = {e["id"]: e for e in M["els"]}
    hosts = sorted((e for e in M["els"] if e["t"] == kit["host"]["type"]), key=lambda e: e["id"])
    pipes = [e for e in M["els"] if P.is_pipe_path(e) and not (e.get("t") or "").startswith("proposed_route")]
    famcache = {e["id"]: P.family_of(e, by)[0] for e in pipes}
    out_el = []; asms = []; stats = collections.Counter(); notes = []
    src = [kit["sample"]["sheet"]]
    pd = P.derive(M); peers = collections.defaultdict(list)
    for j in pd["joins"]:
        if j["kind"] == "joined": peers[j["a"]].append(j["b"]); peers[j["b"]].append(j["a"])
    for h in hosts:
        sh, z0, z1 = P.device_shape(h); zc = (z0 + z1) / 2
        b = Builder(kit, comps, h, None); carriers = {}
        want = {"supply": ("chw_s", -0.13, -7.5), "return": ("chw_r", -0.19, 7.5)}
        label = None
        try: label = int(h["a"]["chw_pipe"].split("(")[1].split()[0])
        except Exception: label = 20
        for line, (fam, dz, ly) in want.items():
            best = None
            for e in pipes:
                if famcache[e["id"]] != fam or e["l"] != h["l"]: continue
                pts = e["g"][1]
                for end, q in (("S", pts[0]), ("E", pts[-1])):
                    d = sh.distance(Point(q[0], q[1]))
                    if d <= 1.0 and abs(q[2] - zc) <= 0.5 and (e["a"].get("dn_label_mm") or 0) <= max(label * 1.6, 32):   # a much larger pipe is a main passing the unit, not its stub
                        key = (abs(q[2] - (zc + dz)), abs((e["a"].get("dn_label_mm") or 0) - label), e["id"])
                        if best is None or key < best[0]: best = (key, e, end)
            if best:
                _, e, end = best; pts = e["g"][1]; seq = pts if end == "S" else pts[::-1]
                ext = extend_chain(e, "E" if end == "S" else "S", by, peers, famcache, hops=3)
                carriers[line] = Carrier(e, seq, ext); stats["carrier_drawn"] += 1; stats["carrier_extended"] += 1 if ext else 0
            else:
                # assumed stub from the unit's end face (local -x), 80 cm long
                lx = -h["g"][3] / 2; gx, gy = local_to_global(h, lx, ly); gx2, gy2 = local_to_global(h, lx - 80.0, ly)
                z = round(zc + dz, 4)
                dn = label; r = PD.compute({"l": h["l"]}, fam, float(dn), "model_value", PD.load())
                drawn = r.pop("_drawn_cm")
                slot = "stub_" + line[0]
                a = b.base_attrs(slot, None, {"component": "assumed_stub", "kit_ports": [port("S", (gx, gy, z), fam, dn, "threaded", "assumed_stub"), port("E", (gx2, gy2, z), fam, dn, "threaded", "assumed_stub")],
                                              "stub_assumed": "no drawn pipe touches this unit's %s connection; an 80 cm stub is assumed so the sample can be applied" % line})
                a.update(r)
                el = mk_element("M.pipe", h["l"], kit["id"], h["id"], slot, "kit_assumed_stub", "m_chws" if fam == "chw_s" else "m_chwr", ["t", [[round(gx, 3), round(gy, 3), z], [round(gx2, 3), round(gy2, 3), z]], drawn], a, src)
                b.add(slot, el)
                carriers[line] = Carrier(el, [[gx, gy, z], [gx2, gy2, z]]); stats["carrier_assumed_stub"] += 1
        # place by order_from_host
        for line in ("supply", "return"):
            car = carriers[line]; fam = want[line][0]; e = car.el
            snapshot = (dict(b.slots), len(b.els))
            for attempt, (flex_mm, gap) in enumerate(((None, 0.0), (200, 0.0), (150, 0.0), (100, 0.0))):
                global GAP_CM
                GAP_CM = gap; car.cursor = 0.0
                del b.els[snapshot[1]:]; b.slots.clear(); b.slots.update(snapshot[0])
                if flex_mm:
                    comps["kinds"]["flex_connector"]["length_mm"] = {k: min(v, flex_mm) for k, v in comps_base["kinds"]["flex_connector"]["length_mm"].items()}
                else:
                    comps["kinds"]["flex_connector"]["length_mm"] = dict(comps_base["kinds"]["flex_connector"]["length_mm"])
                ok = _place_line(b, kit, comps, car, line, fam, label, h, src)
                if ok: break
            GAP_CM = 0.0
            comps["kinds"]["flex_connector"]["length_mm"] = dict(comps_base["kinds"]["flex_connector"]["length_mm"])
            if not ok: stats["line_unplaced"] += 1; notes.append((h["id"], line)); continue
            if attempt: stats["line_compressed"] += 1; b.assumed.append("%s line compressed to fit (flexible connector %s mm, gap %s cm)" % (line, flex_mm, gap))
            continue
            dn = 0; od = 0; jk = None
            for sl in []: pass
        for line in ():
            car = carriers[line]; fam = want[line][0]; e = car.el
            dn = int(e["a"].get("dn_label_mm") or label); od = float(e["a"].get("od_mm") or 26.7); jk = e["a"].get("jacket_od_mm")
            for sl in sorted((s for s in kit["slots"] if s["line"] == line), key=lambda s: s["order_from_host"]):
                if sl["slot"] in b.slots: continue
                if sl.get("side_of"):
                    continue
                c = comps["kinds"][sl["component"]]
                if c.get("side"): res = b.side(sl["slot"], sl["component"], car, fam, dn, od, jk, h["l"], src)
                else: res = b.inline(sl["slot"], sl["component"], car, fam, dn, od, jk, h["l"], src)
                if res is None: stats["slot_unplaced"] += 1; notes.append((h["id"], sl["slot"]))
            # side_of slots (drain valve after strainer)
            for sl in [s for s in kit["slots"] if s["line"] == line and s.get("side_of")]:
                ref = b.slots.get(sl["side_of"])
                if ref is None: stats["slot_unplaced"] += 1; continue
                refel = next(x for x in b.els if x["id"] == ref); pa, pb = refel["g"][1]
                mid_s = 0  # place beside the strainer: advance on the carrier to just after the strainer
                res = b.side(sl["slot"], sl["component"], car, fam, dn, od, jk, h["l"], src)
                if res is None: stats["slot_unplaced"] += 1; notes.append((h["id"], sl["slot"]))
        # bypass valve between lines: from a point on the supply carrier to a point on the return carrier, nearest to the unit
        s_car, r_car = carriers["supply"], carriers["return"]
        c = comps["kinds"]["bypass_valve"]; w = c["body_d_mm"] / 10.0
        sA, se = s_car.point_at(2.0); sB, re_ = r_car.point_at(2.0)
        if math.dist(p3(sA), p3(sB)) < 1.0: sB, re_ = r_car.point_at(8.0)
        a = b.base_attrs("b01", se["id"], {"component": "bypass_valve", "component_name": c["name"], "body_d_cm": round(w, 2), "length_basis": c["length_basis"],
                                             "bypass_between": [se["id"], re_["id"]],
                                             "kit_ports": [port("A", sA, "chw_s", int(se["a"].get("dn_label_mm") or label), "threaded"), port("B", sB, "chw_r", int(re_["a"].get("dn_label_mm") or label), "threaded")]})
        b.add("b01", mk_element("M.pipe", h["l"], kit["id"], h["id"], "b01", c["type"], c["mat"], ["t", [[round(v, 3) for v in sA], [round(v, 3) for v in sB]], round(w, 3)], a, src))
        out_el += b.els; asms.append(b.assembly([c_.el["id"] for c_ in carriers.values() if "assembly" not in c_.el["a"]]))
        stats["hosts"] += 1
    return {"elements": out_el, "assemblies": asms, "stats": dict(stats), "notes": notes, "kit": kit}


# ---------- family: generic equipment connections (plant: chiller, pumps, FAHU, auxiliaries) ----------
FAMMAT = {"chw_s": "m_chws", "chw_r": "m_chwr", "fire": "p_ff", "cold": "p_cold", "hot": "p_hot"}   # display material keys that already exist in the model

def carrier_dims(e, fam):
    a = e["a"]
    if a.get("od_mm"): return int(a["dn_label_mm"]), float(a["od_mm"]), a.get("jacket_od_mm")
    dn, basis = P.dn_of(e); r = PD.compute(e, fam, dn, basis, PD.load())
    r.pop("_drawn_cm"); return int(r["dn_label_mm"]), float(r["od_mm"]), r["jacket_od_mm"]

def chain_len(kit, comps, line, dn):
    tot = 0.0
    for sl in kit["slots"]:
        if sl["line"] != line: continue
        c = comps["kinds"][sl["component"]]
        if c.get("side"): continue
        lm = c["length_mm"]; k = min((int(x) for x in lm), key=lambda x: abs(x - dn)); tot += lm[str(k)] / 10.0
    return tot

def slab_zones(M):
    L = M["levels"]; return [(L[i]["top"], L[i + 1]["ffl"], L[i]["id"], L[i + 1]["id"]) for i in range(len(L) - 1)]

def slab_crossings(M, pts):
    """Full crossings of a slab zone by one polyline: [(zone, x, y)] (a segment must pass BOTH faces of the zone)."""
    out = []
    for (t0, t1, la, lb) in slab_zones(M):
        for i in range(len(pts) - 1):
            za, zb = pts[i][2], pts[i + 1][2]
            lo, hi = min(za, zb), max(za, zb)
            if lo <= t0 + 0.02 and hi >= t1 - 0.02 and hi - lo > 0.05:
                t = ((t0 + t1) / 2 - za) / (zb - za)
                out.append(((t0, t1, la, lb), pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t))
                break
    return out

def host_selector(kit, M):
    hs = kit.get("host") or {}
    if kit.get("status") == "not_instantiated" or hs.get("rule") == "none" or not hs: return []
    if hs.get("rule") == "valve_hosts": return valve_hosts_from_disk()
    if hs.get("rule") == "duct_paths":
        return sorted((e for e in M["els"] if e["c"] == "M.duct" and e["g"][0] == "d" and not (e.get("t") or "").startswith(("proposed_route", "duct_return_source_candidate", "duct_flex"))
                       and not (e.get("a") or {}).get("alt") and not (e.get("a") or {}).get("assembly") and not (e.get("a") or {}).get("source_graphic")), key=lambda e: e["id"])
    if hs.get("rule") == "fitting_hosts":
        plan = fitting_plan(M); by = {e["id"]: e for e in M["els"]}
        return sorted((by[i] for i in plan), key=lambda e: e["id"])
    if hs.get("rule") in ("pipe_paths", "slab_crossing_paths"):
        by = {e["id"]: e for e in M["els"]}; out = []
        for e in M["els"]:
            if not P.is_pipe_path(e) or (e.get("t") or "").startswith("proposed_route") or e["t"] in hs.get("exclude_types", ()): continue
            if e["a"].get("buried"): continue
            if P.family_of(e, by)[0] not in hs["families"]: continue
            if hs["rule"] == "slab_crossing_paths" and not slab_crossings(M, e["g"][1]): continue
            out.append(e)
        return sorted(out, key=lambda e: e["id"])
    if hs.get("rule") == "fixture_group":
        pre = [hs["group_prefix"]] if isinstance(hs["group_prefix"], str) else hs["group_prefix"]; mp = [hs["main_part"]] if isinstance(hs["main_part"], str) else hs["main_part"]
        return sorted((e for e in M["els"] if e["c"] == "P.fix" and e.get("grp") and e["grp"].split("-")[0] in pre and (e.get("a") or {}).get("part") in mp and not (e.get("a") or {}).get("assembly")), key=lambda e: e["id"])
    types = [hs["type"]] if isinstance(hs["type"], str) else hs["type"]
    return sorted((e for e in M["els"] if e["t"] in types and not (e.get("a") or {}).get("assembly") and (not hs.get("level") or e["l"] in hs["level"]) and not (hs.get("alt") is False and (e.get("a") or {}).get("alt"))), key=lambda e: e["id"])

def gen_generic(kit_id):
    def run(M, comps):
        from shapely.geometry import Point
        kit = kit_def(kit_id); by = {e["id"]: e for e in M["els"]}; hosts = host_selector(kit, M); src = [kit["sample"]["sheet"]]
        pipes = [e for e in M["els"] if P.is_pipe_path(e) and not (e.get("a") or {}).get("alt")]
        famcache = {e["id"]: P.family_of(e, by)[0] for e in pipes}
        pd = P.derive(M); peers = collections.defaultdict(list)
        for j in pd["joins"]:
            if j["kind"] == "joined": peers[j["a"]].append(j["b"]); peers[j["b"]].append(j["a"])
        out_el = []; asms = []; stats = collections.Counter(); notes = []
        for h in hosts:
            sh, z0, z1 = P.device_shape(h); zc = (z0 + z1) / 2; b = Builder(kit, comps, h, None); carriers = {}
            minx, miny, maxx, maxy = sh.bounds
            for k, ln in enumerate(kit["lines"]):
                fam = ln["fam"]; best = None
                for e in pipes:
                    if famcache[e["id"]] != fam or e["l"] != h["l"]: continue
                    pts = e["g"][1]
                    for end, q in (("S", pts[0]), ("E", pts[-1])):
                        if sh.distance(Point(q[0], q[1])) <= 5.0 and z0 - 0.3 <= q[2] <= z1 + 0.3:
                            dn_l = carrier_dims(e, fam)[0]
                            key = (-dn_l, 0 if not e["t"].startswith("proposed_route") else 1, e["id"], end)
                            if best is None or key < best[0]: best = (key, e, end)
                if best:
                    _, e, end = best; pts = e["g"][1]; seq = pts if end == "S" else pts[::-1]
                    ext = extend_chain(e, "E" if end == "S" else "S", by, peers, famcache, hops=3) if e["a"].get("dn_label_mm") else []
                    carriers[ln["line"]] = (Carrier(e, seq, ext), fam); stats["carrier_drawn"] += 1
                else:
                    dn = kit.get("stub_dn") or (20 if fam.startswith("chw") and h["t"] in ("chw_dosing_unit",) else 50)
                    y = (miny + maxy) / 2 + (k - (len(kit["lines"]) - 1) / 2) * 25.0; x0 = maxx; z = round(zc + (0.08 if fam in ("chw_s",) else -0.08), 4)
                    r = PD.compute({"l": h["l"]}, fam, float(dn), "model_value", PD.load()); drawn = r.pop("_drawn_cm"); slot = "stub_%s" % ln["line"]
                    a = b.base_attrs(slot, None, {"component": "assumed_stub", "kit_ports": [port("S", (x0, y, z), fam, dn, "flanged", "assumed_stub"), port("E", (x0 + 80.0, y, z), fam, dn, "flanged", "assumed_stub")],
                                                  "stub_assumed": "no drawn pipe touches this unit's %s connection; an 80 cm stub is assumed (DN%d) so the sample can be applied" % (ln["line"], dn)}); a.update(r)
                    el = mk_element("M.pipe", h["l"], kit["id"], h["id"], slot, "kit_assumed_stub", FAMMAT.get(fam, "m_chwr"), ["t", [[round(x0, 3), round(y, 3), z], [round(x0 + 80.0, 3), round(y, 3), z]], drawn], a, src)
                    b.add(slot, el); carriers[ln["line"]] = (Carrier(el, [[x0, y, z], [x0 + 80.0, y, z]]), fam); stats["carrier_assumed_stub"] += 1
            for k, ln in enumerate(kit["lines"]):
                car, fam = carriers[ln["line"]]; dn, od, jk = carrier_dims(car.el, fam); snapshot = (dict(b.slots), len(b.els)); ok = False
                for attempt, flex_mm in enumerate((None, 200, 150, 100)):
                    car.cursor = 0.0; del b.els[snapshot[1]:]; b.slots.clear(); b.slots.update(snapshot[0])
                    comps["kinds"]["flex_connector"]["length_mm"] = {k2: min(v, flex_mm) if flex_mm else v for k2, v in comps_base["kinds"]["flex_connector"]["length_mm"].items()}
                    ok = _place_line(b, kit, comps, car, ln["line"], fam, dn, h, src)
                    if ok: break
                comps["kinds"]["flex_connector"]["length_mm"] = dict(comps_base["kinds"]["flex_connector"]["length_mm"])
                if not ok:                                   # the drawn pipe is too short for the sample: use an assumed stub from the unit's edge instead
                    del b.els[snapshot[1]:]; b.slots.clear(); b.slots.update(snapshot[0])
                    need = chain_len(kit, comps, ln["line"], dn); L = max(80.0, math.ceil(need * 1.15 + 10)); slot = "stub_%s" % ln["line"]; dn = int(kit.get("stub_dn") or dn)
                    y = (miny + maxy) / 2 + (k - (len(kit["lines"]) - 1) / 2) * 25.0; x0 = maxx; z = round(zc + (0.08 if fam == "chw_s" else -0.08), 4)
                    r = PD.compute({"l": h["l"]}, fam, float(dn), "model_value", PD.load()); drawn = r.pop("_drawn_cm")
                    a = b.base_attrs(slot, None, {"component": "assumed_stub", "kit_ports": [port("S", (x0, y, z), fam, dn, "flanged", "assumed_stub"), port("E", (x0 + L, y, z), fam, dn, "flanged", "assumed_stub")],
                                                  "stub_assumed": "the drawn pipe touching this connection (%s) is too short for the sample; a %d cm stub DN%d is assumed" % (car.el["id"], L, dn)}); a.update(r)
                    el = mk_element("M.pipe", h["l"], kit["id"], h["id"], slot, "kit_assumed_stub", FAMMAT.get(fam, "m_chwr"), ["t", [[round(x0, 3), round(y, 3), z], [round(x0 + L, 3), round(y, 3), z]], drawn], a, src)
                    b.add(slot, el); car = Carrier(el, [[x0, y, z], [x0 + L, y, z]]); carriers[ln["line"]] = (car, fam); stats["carrier_replaced_by_stub"] += 1
                    dn2, od, jk = carrier_dims(el, fam) if False else (dn, float(r["od_mm"]), r["jacket_od_mm"])
                    for flex_mm in (None, 200, 150):
                        car.cursor = 0.0; mark = len(b.els); sl_mark = dict(b.slots)
                        comps["kinds"]["flex_connector"]["length_mm"] = {k2: min(v, flex_mm) if flex_mm else v for k2, v in comps_base["kinds"]["flex_connector"]["length_mm"].items()}
                        ok = _place_line(b, kit, comps, car, ln["line"], fam, dn, h, src)
                        if ok: break
                        del b.els[mark:]; b.slots.clear(); b.slots.update(sl_mark)
                    comps["kinds"]["flex_connector"]["length_mm"] = dict(comps_base["kinds"]["flex_connector"]["length_mm"])
                    if not ok: stats["line_unplaced"] += 1; notes.append((h["id"], ln["line"]))
                elif attempt: stats["line_compressed"] += 1; b.assumed.append("%s line compressed to fit (flexible connector %s mm)" % (ln["line"], flex_mm))
            out_el += b.els; asms.append(b.assembly([c_.el["id"] for c_, _ in carriers.values() if "assembly" not in c_.el["a"]])); stats["hosts"] += 1
        return {"elements": out_el, "assemblies": asms, "stats": dict(stats), "notes": notes, "kit": kit}
    return run

# ---------- family: pipe supports and slab sleeves ----------
def _near(table, dn):
    ks = sorted(int(k) for k in table); k = min(ks, key=lambda x: (abs(x - dn), x)); return table[str(k)], k

def support_spacing(lib, fam, dn, od, vertical):
    sp = lib["support_spacing"]
    if fam in ("chw_s", "chw_r"):
        v, k = _near(sp["steel_water_service"]["m"], dn); rod, _ = _near(sp["steel_water_service"]["rod_mm"], dn)
        return v, rod, "MSS SP-58 family table via Engineering ToolBox (verified_1_source; standard attribution unconfirmed)" + (" [DN%d taken from DN%d]" % (dn, k) if k != dn else "")
    if fam == "fire":
        v, k = _near(sp["fire_nfpa13"]["m"], dn); rod, _ = _near(sp["fire_nfpa13"]["rod_mm"], dn)
        return v, rod, "NFPA 13 Table 17.4.2.1(a) (secondary source)" + (" [DN%d taken from DN%d]" % (dn, k) if k != dn else "")
    t = sp["upvc_drain_dr106"]; table = t["vertical_m"] if vertical else t["horizontal_m"]
    ks = sorted(int(x) for x in table); k = min(ks, key=lambda x: (abs(x - od), table[str(x)])); return table[str(k)], t["rod_mm"], "DR-106 (MECH2 ص9) uPVC spacing, row %d for OD %g" % (k, od)

def gen_supports(kit_id):
    def run(M, comps):
        kit = kit_def(kit_id); lib = PD.load(); by = {e["id"]: e for e in M["els"]}; hosts = host_selector(kit, M); src = [kit["sample"]["sheet"]]
        lv = {l["id"]: l for l in M["levels"]}; out_el = []; asms = []; stats = collections.Counter()
        for h in hosts:
            fam = P.family_of(h, by)[0]; a_ = h["a"]; dn = int(a_.get("dn_label_mm") or 0); od = float(a_.get("od_mm") or 0); jk = a_.get("jacket_od_mm")
            b = Builder(kit, comps, h, None); pts = h["g"][1]; n = 0; lvl = lv[h["l"]]
            body_cm = (jk or od) / 10.0
            for i in range(len(pts) - 1):
                A, B = pts[i], pts[i + 1]; L3 = seglen(A, B)
                if L3 < 1.0: continue
                vert = abs(B[2] - A[2]) * 100.0 / L3 > 0.7
                sp_m, rod_mm, basis = support_spacing(lib, fam, dn, od, vert)
                cnt = max(1, math.ceil(L3 / (sp_m * 100.0)))
                for k in range(cnt):
                    t = (k + 0.5) / cnt; q = lerp(A, B, t); n += 1; tag = "h%03d" % n
                    common = {"spacing_m": sp_m, "spacing_basis": basis, "dn_label_mm": dn, "kind": "riser clamp" if vert else "hanger"}
                    if fam in ("chw_s", "chw_r"): sl_cm = 30.0
                    elif fam == "fire": sl_cm = 4.0
                    else: sl_cm = 4.0
                    sl_cm = min(sl_cm, L3 / (2 * cnt))
                    ux, uy, uz = (B[0] - A[0]) / L3, (B[1] - A[1]) / L3, (B[2] - A[2]) * 100.0 / L3
                    p0 = [q[0] - ux * sl_cm / 2, q[1] - uy * sl_cm / 2, q[2] - uz * sl_cm / 200.0]; p1 = [q[0] + ux * sl_cm / 2, q[1] + uy * sl_cm / 2, q[2] + uz * sl_cm / 200.0]
                    a = b.base_attrs(tag + "c", h["id"], dict(common, component="riser_clamp" if vert else "saddle", component_name="مشبك صاعد" if vert else "سرج/حلقة تثبيت", length_cm=round(sl_cm, 2), body_d_cm=round(body_cm + 1.2, 2),
                                                               length_basis="assumed", dim_source={"type": "standard", "standard": basis, "status": "verified_1_source", "assumptions": []}))
                    b.add(tag + "c", mk_element(h["c"], h["l"], kit["id"], h["id"], tag + "c", "kit_riser_clamp" if vert else "kit_saddle", "kit_saddle_pvc" if fam in ("chw_s", "chw_r", "drain", "storm") else "kit_hanger_steel",
                                                ["t", [[round(v, 3) for v in p0], [round(v, 3) for v in p1]], round(body_cm + 1.2, 3)], a, src))
                    if not vert:
                        zc = q[2]
                        if zc - lvl["ffl"] < 0.9:     # roof / low pipes stand on a post
                            ztop = zc - (body_cm + 1.2) / 200.0; zb = lvl["ffl"]
                            if ztop - zb > 0.03:
                                ar = b.base_attrs(tag + "r", h["id"], dict(common, component="post", component_name="دعامة قائمة", length_cm=round((ztop - zb) * 100, 1), body_d_cm=4.0, length_basis="assumed (post dia 4 cm)"))
                                b.add(tag + "r", mk_element(h["c"], h["l"], kit["id"], h["id"], tag + "r", "kit_post", "kit_hanger_steel", ["t", [[round(q[0], 3), round(q[1], 3), round(zb, 4)], [round(q[0], 3), round(q[1], 3), round(ztop, 4)]], 4.0], ar, src))
                        else:
                            zb = zc + (body_cm + 1.2) / 200.0; ztop = max(lvl["top"], zb + 0.03)
                            ar = b.base_attrs(tag + "r", h["id"], dict(common, component="hanger_rod", component_name="قضيب تعليق", length_cm=round((ztop - zb) * 100, 1), body_d_cm=round(rod_mm / 10.0, 2), length_basis="rod %.1f mm (%s)" % (rod_mm, basis)))
                            b.add(tag + "r", mk_element(h["c"], h["l"], kit["id"], h["id"], tag + "r", "kit_hanger_rod", "kit_hanger_steel", ["t", [[round(q[0], 3), round(q[1], 3), round(zb, 4)], [round(q[0], 3), round(q[1], 3), round(ztop, 4)]], round(rod_mm / 10.0, 3)], ar, src))
            if not b.slots: stats["host_without_support"] += 1
            out_el += b.els; asms.append(b.assembly([h["id"]])); stats["hosts"] += 1; stats["supports"] += n
        return {"elements": out_el, "assemblies": asms, "stats": dict(stats), "notes": [], "kit": kit}
    return run

def gen_sleeves(kit_id):
    def run(M, comps):
        kit = kit_def(kit_id); lib = PD.load(); by = {e["id"]: e for e in M["els"]}; hosts = host_selector(kit, M); src = [kit["sample"]["sheet"]]
        rows = lib["steel_pipe_sch40"]["rows"]; out_el = []; asms = []; stats = collections.Counter()
        for h in hosts:
            a_ = h["a"]; jk = a_.get("jacket_od_mm") or a_.get("od_mm") or 20.0; b = Builder(kit, comps, h, None)
            need = float(jk) + 10.0; pick = None
            for dn in sorted(int(k) for k in rows):
                if rows[str(dn)]["od"] - 2 * rows[str(dn)]["wall"] >= need: pick = dn; break
            if pick is None: pick = 200; b.assumed.append("pipe larger than the biggest listed sleeve; DN200 used")
            r = rows[str(pick)]
            for n, ((t0, t1, la, lb), x, y) in enumerate(slab_crossings(M, h["g"][1]), 1):
                tag = "z%02d" % n
                a = b.base_attrs(tag, h["id"], {"component": "fire_sleeve", "component_name": "كُمّ Sch 40 مع مانع حريق", "slab_between": [la, lb], "sleeve_dn": pick, "sleeve_od_mm": r["od"], "sleeve_wall_mm": r["wall"],
                                                  "firestop": {"rating_h": 2, "basis": "MECH1 ص9–10 / MECH2 ص16 / S-N4 (stated)"}, "dim_source": {"type": "standard", "standard": "ASME B36.10M", "status": "verified_2_sources" if pick <= 100 else "recalled_unverified", "assumptions": ["sleeve ID = pipe jacket OD + 10 mm clearance (assumed)"]}})
                b.add(tag, mk_element(h["c"], lb if False else h["l"], kit["id"], h["id"], tag, "kit_fire_sleeve", "kit_sleeve_steel", ["cyl", round(x, 3), round(y, 3), round(r["od"] / 20.0, 3), round(t0, 4), round(t1, 4)], a, src))
                stats["sleeves"] += 1
            out_el += b.els; asms.append(b.assembly([h["id"]])); stats["hosts"] += 1
        return {"elements": out_el, "assemblies": asms, "stats": dict(stats), "notes": [], "kit": kit}
    return run
# ---------- family: sanitary fixtures and water heaters ----------
TYPE_NAMES = {"kit_shower_hose": "خرطوم دش", "kit_bottle_trap": "مصيدة زجاجة", "kit_relief_valve": "صمام أمان", "kit_l_bracket": "مشبك L", "kit_drain_stub": "تصريف لأقرب نقطة",
              "kit_angle_valve": "صمام زاوية", "kit_duct_rods": "قضيبا تعليق مجرى", "kit_duct_shelf": "زاوية رف مجرى", "kit_pump_base": "قاعدة مضخة", "kit_pump_casing": "غلاف مضخة", "kit_pump_guard": "غطاء وصلة المحور", "kit_pump_motor": "محرك مضخة", "kit_flange": "شفة", "kit_valve_stem": "ساق صمام", "kit_handwheel": "عجلة صمام", "kit_valve_lever": "ذراع صمام", "kit_actuator": "محرك صمام", "kit_strainer_cap": "غطاء تصريف المصفاة", "kit_elbow": "كوع", "kit_coupling": "قارنة/شفة/union", "kit_tee_run": "تيه — مجرى", "kit_tee_branch": "تيه — فرع", "kit_fcu_rod": "قضيب تعليق FCU", "kit_vibration_isolator": "عازل اهتزاز", "kit_cdp_stub": "وصلة تصريف التكثيف", "kit_u_trap": "فخ U", "kit_cdp_run": "أنبوب تصريف التكثيف", "kit_osy_valve": "صمام بوابة OS&Y", "kit_saddle": "سرج/حلقة تثبيت أنبوب", "kit_riser_clamp": "مشبك صاعد", "kit_hanger_rod": "قضيب تعليق", "kit_post": "دعامة قائمة", "kit_fire_sleeve": "كُمّ Sch 40 مع مانع حريق ساعتين"}

def _tube(b, kit, h, slot, kind, comps, cat, level, p0, p1, dia_mm, ports, src, extra=None):
    c = comps["kinds"][kind]
    a = b.base_attrs(slot, None, dict({"component": kind, "component_name": c["name"], "length_cm": round(math.dist(p3(p0), p3(p1)), 2), "body_d_cm": round(dia_mm / 10.0, 2), "length_basis": c["length_basis"], "kit_ports": ports}, **(extra or {})))
    b.add(slot, mk_element(cat, level, kit["id"], h["id"], slot, c["type"], c["mat"], ["t", [[round(v, 3) for v in p0], [round(v, 3) for v in p1]], round(dia_mm / 10.0, 3)], a, src))

def gen_fixtures(kit_id):
    def run(M, comps):
        from shapely.geometry import Point
        from shapely.ops import unary_union, nearest_points
        kit = kit_def(kit_id); hosts = host_selector(kit, M); src = [kit["sample"]["sheet"]]; lv = {l["id"]: l for l in M["levels"]}
        groups = collections.defaultdict(list)
        for e in M["els"]:
            if e["c"] == "P.fix" and e.get("grp") and not (e.get("a") or {}).get("assembly"): groups[(e["l"], e["grp"])].append(e)
        walls = {}
        for L in lv:
            fs = [P.device_shape(e)[0] for e in M["els"] if e["l"] == L and e["c"] in ("A.wall", "S.wall") and e["g"][0] in ("r", "p", "b") and not (e["a"] or {}).get("alt") and P.device_shape(e)]
            walls[L] = unary_union([f for f in fs if f is not None and not f.is_empty]) if fs else None
        out_el = []; asms = []; stats = collections.Counter()
        for h in hosts:
            parts = groups[(h["l"], h["grp"])]; shapes = [P.device_shape(e)[0] for e in parts if P.device_shape(e)]
            U = unary_union(shapes); cx, cy = U.centroid.x, U.centroid.y; ffl = lv[h["l"]]["ffl"]; b = Builder(kit, comps, h, None)
            W = walls.get(h["l"]); ux, uy = 0.0, 1.0; wx, wy = U.bounds[0] + (U.bounds[2] - U.bounds[0]) / 2, U.bounds[1]
            if W is not None:
                c_pt, w_pt = nearest_points(Point(cx, cy), W)
                d = c_pt.distance(w_pt)
                if 0 < d <= 150.0: ux, uy = (cx - w_pt.x) / d, (cy - w_pt.y) / d; wx, wy = w_pt.x, w_pt.y; stats["wall_found"] += 1
                else: stats["wall_fallback"] += 1
            nx, ny = -uy, ux; is_wc = kit_id == "sanitary_wc"; zv = ffl + (0.15 if is_wc else 0.60)
            ends = {}
            for sl in kit["slots"]:
                kind = sl["component"]; fam = {"cold": "cold", "hot": "hot", "water": "cold", "waste": "drain"}[sl["line"]]
                if kind == "angle_valve":
                    off = 0.0 if is_wc else (8.0 if fam == "cold" else -8.0); L = comps["kinds"]["angle_valve"]["length_mm"]["15"] / 10.0
                    q0 = [wx + ux * 0.5 + nx * off, wy + uy * 0.5 + ny * off, zv]; q1 = [q0[0] + ux * L, q0[1] + uy * L, zv]
                    _tube(b, kit, h, sl["slot"], kind, comps, "P.fix", h["l"], q0, q1, 22.0, [port("A", q0, fam, 15, "compression", "assumed"), port("B", q1, fam, 15, "compression", "assumed")], src); ends[sl["slot"]] = q1
                elif kind == "shower_hose":
                    q0 = ends["w01"]; q1 = [cx, cy, ffl + 0.40]
                    _tube(b, kit, h, sl["slot"], kind, comps, "P.fix", h["l"], q0, q1, 12.0, [port("A", q0, "cold", 15, "compression", "assumed"), port("B", q1, "cold", 15, "compression", "assumed")], src)
                elif kind == "bottle_trap":
                    q0 = [cx, cy, ffl + 0.45]; q1 = [cx, cy, ffl + 0.20]
                    _tube(b, kit, h, sl["slot"], kind, comps, "P.fix", h["l"], q0, q1, 32.0, [port("A", q0, "drain", 32, "compression", "assumed"), port("B", q1, "drain", 32, "compression", "assumed")], src)
            out_el += b.els; asms.append(b.assembly([])); stats["hosts"] += 1
        return {"elements": out_el, "assemblies": asms, "stats": dict(stats), "notes": [], "kit": kit}
    return run

def gen_heaters(kit_id):
    def run(M, comps):
        kit = kit_def(kit_id); hosts = host_selector(kit, M); src = [kit["sample"]["sheet"]]; out_el = []; asms = []; stats = collections.Counter()
        for h in hosts:
            g = h["g"]; cx, cy, w, d, rot, z0, z1 = g[1:8]; zc = (z0 + z1) / 2; b = Builder(kit, comps, h, None)
            def G(lx, ly, z): x, y = local_to_global(h, lx, ly); return [x, y, z]
            for slot, lx in (("k01", -w / 4), ("k02", w / 4)):
                q0 = G(lx, -d / 2, zc); q1 = G(lx, -d / 2 - 15.0, zc)
                _tube(b, kit, h, slot, "l_bracket", comps, "P.heater", h["l"], q0, q1, 20.0, [], src)
            r0 = G(w / 4, 0, z0); r1 = G(w / 4, 0, z0 - 0.08)
            _tube(b, kit, h, "v01", "relief_valve", comps, "P.heater", h["l"], r0, r1, 28.0, [port("A", r0, "cold", 15, "compression", "assumed"), port("B", r1, "cold", 15, "compression", "assumed")], src)
            a0 = G(-w / 4, 0, z0); a1 = G(-w / 4, 0, z0 - 0.045)
            _tube(b, kit, h, "v02", "angle_valve", comps, "P.heater", h["l"], a0, a1, 22.0, [port("A", a0, "cold", 15, "compression", "assumed"), port("B", a1, "cold", 15, "compression", "assumed")], src)
            d1 = [r1[0], r1[1], r1[2] - 0.20]
            _tube(b, kit, h, "d01", "drain_stub", comps, "P.heater", h["l"], r1, d1, 16.0, [port("A", r1, "cold", 15, "compression", "assumed"), port("B", d1, "cold", 15, "compression", "assumed")], src)
            out_el += b.els; asms.append(b.assembly([])); stats["hosts"] += 1
        return {"elements": out_el, "assemblies": asms, "stats": dict(stats), "notes": [], "kit": kit}
    return run

def gen_on_host(kit_id):
    """The host IS the carrier (e.g. a riser): the set is placed on it from `start_cm` along its axis."""
    def run(M, comps):
        kit = kit_def(kit_id); hosts = host_selector(kit, M); src = [kit["sample"]["sheet"]]; oh = kit["on_host"]; out_el = []; asms = []; stats = collections.Counter(); notes = []
        for h in hosts:
            fam = oh["fam"]; dn, od, jk = carrier_dims(h, fam); b = Builder(kit, comps, h, None); car = Carrier(h, h["g"][1]); car.cursor = oh.get("start_cm", 0.0)
            if not _place_line(b, kit, comps, car, oh["line"], fam, dn, h, src): stats["line_unplaced"] += 1; notes.append(h["id"])
            out_el += b.els; asms.append(b.assembly([h["id"]])); stats["hosts"] += 1
        return {"elements": out_el, "assemblies": asms, "stats": dict(stats), "notes": notes, "kit": kit}
    return run

def gen_fcu_mount(kit_id):
    def run(M, comps):
        kit = kit_def(kit_id); hosts = host_selector(kit, M); src = [kit["sample"]["sheet"]]; lv = {l["id"]: l for l in M["levels"]}
        traps = [e for e in M["els"] if e["t"] == "floor_trap" and not (e.get("a") or {}).get("assembly")]
        out_el = []; asms = []; stats = collections.Counter()
        for h in hosts:
            cx, cy, w, d, rot, z0, z1 = h["g"][1:8]; b = Builder(kit, comps, h, None); top = lv[h["l"]]["top"]
            def G(lx, ly, z): x, y = local_to_global(h, lx, ly); return [x, y, z]
            n = 0
            for sx in (-1, 1):
                for sy in (-1, 1):
                    n += 1; lx, ly = sx * (w / 2 - 10.0), sy * (d / 2 - 5.0); zt = z1 + max(top - z1, 0.04)
                    q0, q1 = G(lx, ly, z1), G(lx, ly, zt)
                    _tube(b, kit, h, "r%02d" % n, "fcu_rod", comps, "M.equip", h["l"], q0, q1, 10.0, [], src)
                    zm = (z1 + zt) / 2; i0, i1 = G(lx, ly, zm - 0.02), G(lx, ly, zm + 0.02)
                    _tube(b, kit, h, "i%02d" % n, "vibration_isolator", comps, "M.equip", h["l"], i0, i1, 30.0, [], src)
            o = G(w / 2 - 6.0, 0, z0); s1 = [o[0], o[1], z0 - 0.10]; s2 = [o[0], o[1], z0 - 0.16]
            prt = lambda end, q: port(end, q, "drain", 25, "socket_coupling", "assumed")
            _tube(b, kit, h, "c01", "cdp_stub", comps, "M.equip", h["l"], o, s1, 44.0, [prt("A", o), prt("B", s1)], src)
            _tube(b, kit, h, "c02", "u_trap", comps, "M.equip", h["l"], s1, s2, 44.0, [prt("A", s1), prt("B", s2)], src)
            near = sorted(((math.hypot(t["g"][1] - o[0], t["g"][2] - o[1]), t["id"]) for t in traps if t["l"] == h["l"]))
            if near and near[0][0] <= 1500.0:
                D, tid = near[0]; t = by_id(M, tid); tx, ty, tz1 = t["g"][1], t["g"][2], t["g"][5]
                zrun = s2[2] - (D / 100.0) * 0.01; e0 = [tx, ty, round(zrun, 4)]
                _tube(b, kit, h, "c03", "cdp_run", comps, "M.equip", h["l"], s2, e0, 44.0, [prt("A", s2), prt("B", e0)], src, {"drain_to": tid, "run_cm": round(D, 1), "fall": "1%"})
                e1 = [tx, ty, round(max(tz1, zrun - 0.30), 4)]
                if e1[2] >= zrun - 0.005: e1[2] = round(zrun - 0.02, 4)
                _tube(b, kit, h, "c04", "cdp_run", comps, "M.equip", h["l"], e0, e1, 44.0, [prt("A", e0), prt("B", e1)], src, {"drain_to": tid})
                stats["drain_to_trap"] += 1
            else:
                e0 = [s2[0] - 150.0 * math.cos(math.radians(rot)), s2[1] - 150.0 * math.sin(math.radians(rot)), round(s2[2] - 0.015, 4)]
                _tube(b, kit, h, "c03", "cdp_run", comps, "M.equip", h["l"], s2, e0, 44.0, [prt("A", s2), prt("B", e0)], src, {"drain_to": None, "note": "no floor trap within 15 m"})
                e1 = [e0[0], e0[1], round(e0[2] - 0.05, 4)]
                _tube(b, kit, h, "c04", "cdp_run", comps, "M.equip", h["l"], e0, e1, 44.0, [prt("A", e0), prt("B", e1)], src, {"drain_to": None})
                stats["drain_free_end"] += 1
            out_el += b.els; asms.append(b.assembly([])); stats["hosts"] += 1
        return {"elements": out_el, "assemblies": asms, "stats": dict(stats), "notes": [], "kit": kit}
    return run

def by_id(M, i):
    for e in M["els"]:
        if e["id"] == i: return e

# ---------- family: pipe fittings (elbows, couplings, tees) on every joint ----------
def _unit(a, b):
    d = [b[0] - a[0], b[1] - a[1], (b[2] - a[2]) * 100.0]; n = math.sqrt(sum(x * x for x in d)) or 1.0
    return [x / n for x in d], n
def _step(p, u, cm):
    return [p[0] + u[0] * cm, p[1] + u[1] * cm, p[2] + u[2] * cm / 100.0]
def _tbl(tb, dn):
    ks = sorted(int(k) for k in tb); k = min(ks, key=lambda x: (abs(x - dn), x)); return tb[str(k)]

def fit_dims(lib, fam, dn, od, jk):
    """(leg_cm, tee_c_cm, body_cm, coupling) for a pipe: standard sizes for steel, 1.2 x OD for plastics (assumed)."""
    steel = fam in ("chw_s", "chw_r", "fire"); ins = jk is not None and jk > od
    if steel:
        A = _tbl(lib["elbow_90_long_radius"]["A"], dn) / 10.0; C = _tbl(lib["tee_equal"]["C_equals_M"], dn) / 10.0
        body = (jk * 1.04 if ins else od * 1.2) / 10.0
        if dn <= 40: cp = {"type": "union", "body": od * 1.45 / 10.0, "len": 4.0, "joint": "threaded"}
        elif dn <= 50:
            fl = _tbl(lib["flange_class150"]["rows"], dn); cp = {"type": "flange_pair", "body": fl["od"] / 10.0, "len": (2 * fl["t"] + 3.0) / 10.0, "joint": "flanged"}
        else: cp = {"type": "grooved", "body": (od + 25.0) / 10.0, "len": 6.0, "joint": "grooved"}
    else:
        A = C = 1.2 * od / 10.0; body = (jk * 1.04 if ins else od * 1.2) / 10.0
        cp = {"type": "socket", "body": (jk * 1.04 if ins else od * 1.25) / 10.0, "len": 5.0, "joint": "socket_coupling"}
    return A, C, body, cp

def fitting_plan(M):
    """{host path id: [descriptor, ...]}  the single place that decides which fittings exist (used by the generator and by the gate)."""
    lib = PD.load(); by = {e["id"]: e for e in M["els"]}; pd = P.derive(M); pp = {p["id"]: p for p in pd["ports"]}
    paths = {e["id"]: e for e in M["els"] if P.is_pipe_path(e) and not (e.get("t") or "").startswith("proposed_route") and e["a"].get("od_mm")}
    info = {}
    for i, e in paths.items():
        fam = P.family_of(e, by)[0]; a = e["a"]; dn = int(a["dn_label_mm"]); od = float(a["od_mm"]); jk = a.get("jacket_od_mm")
        info[i] = (fam, dn, od, jk) + fit_dims(lib, fam, dn, od, jk)
    plan = collections.defaultdict(list)
    for i, e in sorted(paths.items()):
        fam, dn, od, jk, A, C, body, cp = info[i]; pts = e["g"][1]
        for v in range(1, len(pts) - 1):                                   # elbows at bends
            u1, l1 = _unit(pts[v], pts[v - 1]); u2, l2 = _unit(pts[v], pts[v + 1])
            if l1 < 1.0 or l2 < 1.0: continue
            cosang = -(u1[0] * u2[0] + u1[1] * u2[1] + u1[2] * u2[2])
            if cosang > 0.9962: continue                                   # < 5 degrees: not a bend
            L = min(A, 0.45 * l1, 0.45 * l2)
            plan[i].append({"slot": "v%02d" % v, "type": "kit_elbow", "pts": [_step(pts[v], u1, L), list(pts[v]), _step(pts[v], u2, L)], "dia": body, "carrier": i, "dn": dn, "fam": fam, "joint": cp["joint"], "what": "elbow"})
    for j in pd["joins"]:
        if j["kind"] == "joined":
            pa, pb = pp[j["a"]], pp[j["b"]]
            if pa["el"] not in info or pb["el"] not in info or pa["el"] == pb["el"]: continue
            ea, eb = paths[pa["el"]], paths[pb["el"]]
            ptsa = ea["g"][1] if pa["end"] == "S" else ea["g"][1][::-1]; ptsb = eb["g"][1] if pb["end"] == "S" else eb["g"][1][::-1]
            ua, la = _unit(ptsa[0], ptsa[1]); ub, lb = _unit(ptsb[0], ptsb[1]); P0 = ptsa[0]
            fam, dn, od, jk, A, C, body, cp = info[pa["el"]]; fam2, dn2, od2, jk2, A2, C2, body2, cp2 = info[pb["el"]]
            key = "j%s%d" % (pa["end"], len([x for x in plan[pa["el"]] if x["slot"].startswith("j" + pa["end"])]))
            straight = -(ua[0] * ub[0] + ua[1] * ub[1] + ua[2] * ub[2]) < -0.9962 or (ua[0] * ub[0] + ua[1] * ub[1] + ua[2] * ub[2]) < -0.9962
            if dn != dn2:
                big = max((dn, body, od), (dn2, body2, od2)); H = _tbl(lib["reducer_concentric"]["H_by_large_dn"], big[0]) / 10.0 if fam in ("chw_s", "chw_r", "fire") else 1.2 * big[2] / 10.0
                H = min(H, 0.45 * la, 0.45 * lb)
                plan[pa["el"]].append({"slot": key, "type": "kit_reducer", "pts": [_step(P0, ua, H / 2), _step(P0, ub, H / 2)] if not straight else [_step(P0, ua, H / 2), _step(P0, ub, H / 2)], "dia": (body + body2) / 2.0, "carrier": pa["el"], "dn": dn, "fam": fam, "joint": cp["joint"], "what": "reducer", "also": pb["el"]})
            elif straight:
                Lh = min(cp["len"], 0.9 * la, 0.9 * lb) / 2.0
                plan[pa["el"]].append({"slot": key, "type": "kit_coupling", "pts": [_step(P0, ua, Lh), _step(P0, ub, Lh)], "dia": cp["body"], "carrier": pa["el"], "dn": dn, "fam": fam, "joint": cp["joint"], "what": cp["type"], "also": pb["el"]})
            else:
                L = min(A, 0.45 * la, 0.45 * lb)
                plan[pa["el"]].append({"slot": key, "type": "kit_elbow", "pts": [_step(P0, ua, L), list(P0), _step(P0, ub, L)], "dia": body, "carrier": pa["el"], "dn": dn, "fam": fam, "joint": cp["joint"], "what": "elbow", "also": pb["el"]})
        elif j["kind"] == "branch":
            pa = pp[j["a"]]; run = paths.get(j["b"])
            if pa["el"] not in info or run is None: continue
            eb = paths[pa["el"]]; ptsb = eb["g"][1] if pa["end"] == "S" else eb["g"][1][::-1]; ub, lb = _unit(ptsb[0], ptsb[1]); J = ptsb[0]
            best = None
            for k in range(len(run["g"][1]) - 1):
                dist, t = P.seg_dist3(J, run["g"][1][k], run["g"][1][k + 1])
                if best is None or dist < best[0]: best = (dist, k)
            k = best[1]; ur, lr = _unit(run["g"][1][k], run["g"][1][k + 1])
            fam, dn, od, jk, A, C, body, cp = info[pa["el"]]; rfam, rdn, rod, rjk, rA, rC, rbody, rcp = info[run["id"]]
            Cc = min(rC, 0.45 * lr); M_ = min(C, 0.45 * lb)
            n = len([x for x in plan[pa["el"]] if x["slot"].startswith("t" + pa["end"])])
            plan[pa["el"]].append({"slot": "t%s%d_run" % (pa["end"], n), "type": "kit_tee_run", "pts": [_step(J, ur, -Cc), _step(J, ur, Cc)], "dia": rbody, "carrier": run["id"], "dn": rdn, "fam": rfam, "joint": rcp["joint"], "what": "tee run", "also": run["id"]})
            plan[pa["el"]].append({"slot": "t%s%d_br" % (pa["end"], n), "type": "kit_tee_branch", "pts": [list(J), _step(J, ub, M_)], "dia": body, "carrier": pa["el"], "dn": dn, "fam": fam, "joint": cp["joint"], "what": "tee branch", "also": run["id"]})
    return plan

def gen_fittings(kit_id):
    def run(M, comps):
        kit = kit_def(kit_id); by = {e["id"]: e for e in M["els"]}; plan = fitting_plan(M); src = [kit["sample"]["sheet"]]; out_el = []; asms = []; stats = collections.Counter()
        for hid in sorted(plan):
            h = by[hid]; b = Builder(kit, comps, h, None); mat = h["m"]
            for d in plan[hid]:
                pts = [[round(v, 3) for v in q] for q in d["pts"]]
                ends = (pts[0], pts[-1]) if d["type"] != "kit_elbow" else (pts[0], pts[2])
                a = b.base_attrs(d["slot"], d["carrier"], {"component": d["what"], "component_name": d["what"], "body_d_cm": round(d["dia"], 2), "length_basis": "ASME B16.9/B16.5 for steel; 1.2 x OD assumed for plastics",
                                                          "kit_ports": [port("A", ends[0], d["fam"], d["dn"], d["joint"]), port("B", ends[1], d["fam"], d["dn"], d["joint"])]})
                if d.get("also"): a["joins_also"] = d["also"]
                cmat = mat if d["type"] in ("kit_elbow", "kit_tee_run", "kit_tee_branch") else "kit_coupling_steel"
                b.add(d["slot"], mk_element(h["c"], h["l"], kit["id"], h["id"], d["slot"], d["type"], cmat, ["t", pts, round(d["dia"], 3)], a, src)); stats[d["type"]] += 1
            out_el += b.els; asms.append(b.assembly([hid])); stats["hosts"] += 1
        return {"elements": out_el, "assemblies": asms, "stats": dict(stats), "notes": [], "kit": kit}
    return run

# ---------- family: valve details (flanges, stem, handwheel / lever / actuator) on the generated valves ----------
VALVE_STYLE = {"gate_valve": "wheel", "os_y_valve": "wheel_tall", "balancing_valve": "wheel", "picv": "wheel", "butterfly_valve": "lever", "indicating_valve": "lever",
               "motor_valve": "actuator", "check_valve": "flanges", "alarm_valve": "flanges", "suction_diffuser": "flanges", "measuring_station": "flanges", "y_strainer": "strainer"}

def valve_hosts_from_disk():
    out = []
    for f in sorted(os.listdir(OUTDIR)) if os.path.isdir(OUTDIR) else []:
        if f == "valve_details.json": continue
        for e in json.load(open(os.path.join(OUTDIR, f), encoding="utf-8"))["elements"]:
            a = e.get("a") or {}
            if e["g"][0] == "t" and len(e["g"][1]) == 2 and a.get("component") in VALVE_STYLE: out.append(e)
    return sorted(out, key=lambda e: e["id"])

def _cross(a, b): return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
def _norm(v):
    n = math.sqrt(sum(x * x for x in v)) or 1.0; return [x / n for x in v]

def gen_valve_details(kit_id):
    def run(M, comps):
        kit = kit_def(kit_id); lib = PD.load(); hosts = host_selector(kit, M); src = [kit["sample"]["sheet"]]; out_el = []; asms = []; stats = collections.Counter()
        rows = lib["flange_class150"]["rows"]
        for h in hosts:
            a0 = h["a"]; kind = a0["component"]; style = VALVE_STYLE[kind]; p0, p1 = h["g"][1]; D = float(h["g"][2]); dn = int(a0["kit_ports"][0]["dn_mm"])
            u, L = _unit(p0, p1); b = Builder(kit, comps, h, None); mid = [(p0[i] + p1[i]) / 2.0 for i in range(3)]
            def add(slot, typ, mat, pts, dia, what):
                a = b.base_attrs(slot, h["id"], {"component": what, "component_name": what, "body_d_cm": round(dia, 2), "length_basis": "ASME B16.5 (flanges) / generic proportions (assumed)"})
                b.add(slot, mk_element(h["c"], h["l"], kit["id"], h["id"], slot, typ, mat, ["t", [[round(v, 3) for v in q] for q in pts], round(dia, 3)], a, src)); stats[typ] += 1
            if dn >= 50:
                fl = _tbl(rows, dn); t = fl["t"] / 10.0; od = fl["od"] / 10.0
                if t * 2 < L - 0.5:
                    add("fa", "kit_flange", "kit_strainer_steel", [p0, _step(p0, u, t)], od, "flange"); add("fb", "kit_flange", "kit_strainer_steel", [_step(p1, u, -t), p1], od, "flange")
            up = [0.0, 0.0, 1.0]; s = up if abs(u[2]) < 0.7 else _norm(_cross(u, [0.0, 1.0, 0.0]))
            base = _step(mid, s, D / 2.0)
            if style in ("wheel", "wheel_tall"):
                hgt = (0.8 if style == "wheel" else 1.4) * D + 3.0; top = _step(base, s, hgt)
                add("st", "kit_valve_stem", "kit_hanger_steel", [base, top], 1.6 if dn >= 50 else 1.0, "stem"); add("wh", "kit_handwheel", "kit_valve_brass", [top, _step(top, s, 1.0)], max(6.0, 0.9 * D if style == "wheel" else 1.1 * D), "handwheel")
            elif style == "lever":
                top = _step(base, s, 0.4 * D + 2.0); w = _norm(_cross(s, u))
                add("st", "kit_valve_stem", "kit_hanger_steel", [base, top], 1.6, "stem"); add("lv", "kit_valve_lever", "kit_valve_brass", [_step(top, w, -4.0), _step(top, w, 16.0)], 1.4, "lever")
            elif style == "actuator":
                top = _step(base, s, 6.0); add("st", "kit_valve_stem", "kit_hanger_steel", [base, top], 2.0, "stem"); add("ac", "kit_actuator", "kit_strainer_steel", [top, _step(top, s, 14.0)], 12.0, "actuator")
            elif style == "strainer":
                dn_ = [0.0, 0.0, -1.0] if abs(u[2]) < 0.7 else _norm(_cross(u, [0.0, 1.0, 0.0])); lo = _step(mid, dn_, D / 2.0)
                add("cp", "kit_strainer_cap", "kit_strainer_steel", [lo, _step(lo, dn_, 6.0)], max(3.5, 0.45 * D), "blow-off cap")
            if not b.els: stats["host_without_detail"] += 1
            out_el += b.els; asms.append(b.assembly([])); stats["hosts"] += 1
        return {"elements": out_el, "assemblies": asms, "stats": dict(stats), "notes": [], "kit": kit}
    return run

# ---------- family: pump bodies inside the drawn footprint ----------
def gen_pump_bodies(kit_id):
    def run(M, comps):
        kit = kit_def(kit_id); hosts = host_selector(kit, M); src = [kit["sample"]["sheet"]]; out_el = []; asms = []; stats = collections.Counter()
        for h in hosts:
            g = h["g"]
            if g[0] != "r": stats["host_not_box"] += 1; continue
            x0, y0, x1, y1, z0, z1 = g[1:7]; dx, dy = abs(x1 - x0), abs(y1 - y0); cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
            along_x = dx >= dy; Lg, W = (dx, dy) if along_x else (dy, dx); H = z1 - z0
            zc = z0 + 0.12 + (H - 0.12) / 2.0; avail = (H - 0.12) * 100.0; b = Builder(kit, comps, h, None)
            def ax(t, zz=None):                                                       # point on the pump axis at fraction t of the long side (t in -0.5..0.5)
                return [cx + (t * Lg if along_x else 0.0), cy + (0.0 if along_x else t * Lg), zz if zz is not None else zc]
            def add(slot, typ, mat, pts, dia, what):
                a = b.base_attrs(slot, h["id"], {"component": what, "component_name": what, "body_d_cm": round(dia, 2), "length_basis": "generic proportions of the footprint (assumed)"})
                b.add(slot, mk_element(h["c"], h["l"], kit["id"], h["id"], slot, typ, mat, ["t", [[round(v, 3) for v in q] for q in pts], round(dia, 3)], a, src)); stats[typ] += 1
            ins = 0.03; bx = ["r", round(min(x0, x1) + ins * dx, 3), round(min(y0, y1) + ins * dy, 3), round(max(x0, x1) - ins * dx, 3), round(max(y0, y1) - ins * dy, 3), round(z0, 4), round(z0 + 0.12, 4)]
            ab = b.base_attrs("bs", h["id"], {"component": "base plate", "component_name": "base plate", "body_d_cm": 0.0, "length_basis": "generic proportions of the footprint (assumed)"})
            b.add("bs", mk_element(h["c"], h["l"], kit["id"], h["id"], "bs", "kit_pump_base", "kit_strainer_steel", bx, ab, src)); stats["kit_pump_base"] += 1
            add("cs", "kit_pump_casing", h["m"] if h.get("m") else "kit_valve_brass", [ax(-0.42), ax(-0.08)], min(0.8 * W, 0.9 * avail), "pump casing")
            add("cg", "kit_pump_guard", "kit_strainer_steel", [ax(-0.08), ax(0.04)], min(0.35 * W, 0.4 * avail), "coupling guard")
            add("mt", "kit_pump_motor", "kit_strainer_steel", [ax(0.04), ax(0.44)], min(0.75 * W, 0.9 * avail), "motor")
            out_el += b.els; asms.append(b.assembly([])); stats["hosts"] += 1
        return {"elements": out_el, "assemblies": asms, "stats": dict(stats), "notes": [], "kit": kit}
    return run

# ---------- family: duct hangers (table of MECH1 p9-10) ----------
DUCT_HANGER = [(750, 10, 4.0, 2400), (1065, 10, 4.0, 1800), (1370, 13, 5.0, 1800), (2130, 13, 5.0, 1200), (3050, 13, 7.5, 1200)]   # up to mm: rod dia, angle leg cm, max spacing mm

def gen_duct_hangers(kit_id):
    def run(M, comps):
        kit = kit_def(kit_id); hosts = host_selector(kit, M); src = [kit["sample"]["sheet"]]; lv = {l["id"]: l for l in M["levels"]}; out_el = []; asms = []; stats = collections.Counter()
        for h in hosts:
            pts = h["g"][1]; w, hh = float(h["g"][2]), float(h["g"][3]); big = max(w, hh) * 10.0
            row = next((r for r in DUCT_HANGER if big <= r[0]), DUCT_HANGER[-1]); rod_mm, leg, sp = row[1], row[2], row[3]
            b = Builder(kit, comps, h, None); n = 0; lvl = lv[h["l"]]
            for i in range(len(pts) - 1):
                A, B_ = pts[i], pts[i + 1]; u, L = _unit(A, B_)
                if L < 5.0 or abs(u[2]) > 0.5: continue
                if A[2] - hh / 200.0 - lvl["ffl"] < 0.9: continue
                nx, ny = -u[1], u[0]; nn = math.hypot(nx, ny) or 1.0; nx, ny = nx / nn, ny / nn
                cnt = max(1, math.ceil(L / (sp / 10.0)))
                for k in range(cnt):
                    t = (k + 0.5) / cnt; q = _step(A, u, t * L); zb = q[2] - hh / 200.0 - leg / 100.0 / 2.0; zt = max(lvl["top"], q[2] + hh / 200.0 + 0.04); off = w / 2.0 + 4.0
                    L1 = [q[0] + nx * off, q[1] + ny * off]; R1 = [q[0] - nx * off, q[1] - ny * off]; n += 1; tag = "h%03d" % n
                    ra = b.base_attrs(tag + "r", h["id"], {"component": "hanger_rods", "component_name": "قضيبا تعليق", "rod_mm": rod_mm, "body_d_cm": round(rod_mm / 10.0, 2), "length_basis": "MECH1 p9-10 table (stated)", "spacing_max_mm": sp})
                    b.add(tag + "r", mk_element(h["c"], h["l"], kit["id"], h["id"], tag + "r", "kit_duct_rods", "kit_hanger_steel", ["t", [[round(L1[0], 3), round(L1[1], 3), round(zt, 4)], [round(L1[0], 3), round(L1[1], 3), round(zb, 4)], [round(R1[0], 3), round(R1[1], 3), round(zb, 4)], [round(R1[0], 3), round(R1[1], 3), round(zt, 4)]], round(rod_mm / 10.0, 3)], ra, src))
                    sa = b.base_attrs(tag + "s", h["id"], {"component": "shelf_angle", "component_name": "زاوية الرف", "angle_leg_cm": leg, "body_d_cm": round(leg, 2), "length_basis": "MECH1 p9-10 table (stated)"})
                    b.add(tag + "s", mk_element(h["c"], h["l"], kit["id"], h["id"], tag + "s", "kit_duct_shelf", "kit_hanger_steel", ["t", [[round(L1[0], 3), round(L1[1], 3), round(zb, 4)], [round(R1[0], 3), round(R1[1], 3), round(zb, 4)]], round(leg, 3)], sa, src)); stats["hangers"] += 1
            if not b.els: stats["host_without_hanger"] += 1
            out_el += b.els; asms.append(b.assembly([h["id"]])); stats["hosts"] += 1
        return {"elements": out_el, "assemblies": asms, "stats": dict(stats), "notes": [], "kit": kit}
    return run

FAMILIES = {"fcu_chw": gen_fcu, "chiller_chw": gen_generic("chiller_chw"), "chwp_chw": gen_generic("chwp_chw"), "fahu_chw": gen_generic("fahu_chw"), "chw_aux": gen_generic("chw_aux"), "pipe_support_steel": gen_supports("pipe_support_steel"), "pipe_support_upvc": gen_supports("pipe_support_upvc"), "slab_sleeve": gen_sleeves("slab_sleeve"), "sanitary_wc": gen_fixtures("sanitary_wc"), "sanitary_basin": gen_fixtures("sanitary_basin"), "sanitary_tub": gen_fixtures("sanitary_tub"), "heater_wh": gen_heaters("heater_wh"), "ws_pump": gen_generic("ws_pump"), "fire_zcv": gen_on_host("fire_zcv"), "fire_acv": gen_on_host("fire_acv"), "fire_pump": gen_generic("fire_pump"), "fcu_mount": gen_fcu_mount("fcu_mount"), "pipe_fittings": gen_fittings("pipe_fittings"), "valve_details": gen_valve_details("valve_details"), "pump_bodies": gen_pump_bodies("pump_bodies"), "duct_hangers": gen_duct_hangers("duct_hangers")}

def write_family(name, res, comps):
    types = {}; mats = {}
    for e in res["elements"]:
        t = e["t"]
        if t not in types:
            if t == "kit_assumed_stub":
                types[t] = {"n": "وصلة ربط افتراضية (طقم) — كعب أنبوب 80 سم", "cf": "assumed", "sp": [["السبب", "لا أنبوب مرسوم يلامس طرف الوحدة؛ افتُرض كعب ليُطبَّق الطقم"]], "asm": ["الطول 80 سم والمسار افتراضيان"], "sr": [res["kit"]["sample"]["sheet"]]}
            else:
                k = next((v for v in comps["kinds"].values() if v["type"] == t), None) or {"name": TYPE_NAMES.get(t, t)}
                types[t] = {"n": k["name"] + " — من طقم " + res["kit"]["id"], "cf": "assumed", "sp": [["الأبعاد", "نمطية افتراضية من components.json؛ ليست من المخطط"], ["المادة", "غير مذكورة في المخطط"]],
                            "asm": ["الصنف والترتيب من العينة " + res["kit"]["sample"]["sheet"] + "؛ الطول والجسم افتراضيان؛ نوع الوصلة حسب سياسة الربط (لا لحام)"], "sr": [res["kit"]["sample"]["sheet"]]}
        m = e["m"]
        if m not in mats and m not in ("m_chws", "m_chwr"):
            mats[m] = {"name": "مادة عرض لطقم — لا تثبت مادة الصنف", "code": "unknown", "status": "unknown_not_independently_reviewed", "registered_by": "pipeline/kits.py (work order item 9)"}
    doc = {"schema": "c4.generated.v1", "family": name, "kit_library_version": "1", "elements": sorted(res["elements"], key=lambda e: e["id"]), "types": dict(sorted(types.items())),
           "mats": dict(sorted(mats.items())), "assemblies": sorted(res["assemblies"], key=lambda a: a["id"])}
    os.makedirs(OUTDIR, exist_ok=True)
    path = os.path.join(OUTDIR, name + ".json")
    with open(path + ".tmp", "w", encoding="utf-8") as f: json.dump(doc, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    os.replace(path + ".tmp", path)
    return path

def main():
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    M = model_without_generated(); comps = components()
    global comps_base
    comps_base = copy.deepcopy(comps)
    for name, fn in FAMILIES.items():
        if only and name != only: continue
        res = fn(M, comps); path = write_family(name, res, comps)
        print(name, "->", os.path.basename(path), "| elements", len(res["elements"]), "| assemblies", len(res["assemblies"]), "|", res["stats"], "| unplaced:", res["notes"][:5])

if __name__ == "__main__":
    main()
