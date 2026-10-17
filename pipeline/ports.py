# -*- coding: utf-8 -*-
"""Ports and pipe-network joins, derived from the drawn pipe paths (work order 3b-2).  Element geometry is never changed.

  python3 pipeline/ports.py            # reads src/model.json, writes pipeline/data/ports.json

Every pipe path (geometry kind 't' in the pipe categories, not a source alternative) gets TWO ports: `<id>#S` (first point) and
`<id>#E` (last point).  A port carries: xyz (x,y cm, z m as in the model), sys (system FAMILY: cold, hot, drain, storm, fire, chw_s,
chw_r, irrigation), dn_mm and dn_basis.
Joining (tolerance 0.2 cm in 3D, same system family only):
  state 'joined'  - another port of the SAME family is within tolerance (peers listed; `dn_differs` when nominal diameters differ (a data fact; a reducer fitting is only decided later by the dimensions library))
  state 'branch'  - the port lies on the interior of another same-family path (a tee is needed there)
  state 'open'    - no connection; `reason` is one of
        cross_system:<id>   touches a path of ANOTHER family (never joined)
        at_device:<id>      the end sits inside/at a device footprint (devices have no ports yet; this is a classification, not a join)
        near_miss:<id>:<cm> a same-family port/path is within 5 cm but not touching
        free_end            nothing within 5 cm
A join is never made across families; a `dn_differs` join keeps both diameters.  Deterministic output (sorted).
"""
import json, math, os, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
MODEL = os.path.join(ROOT, "src", "model.json")
OUT = os.path.join(HERE, "data", "ports.json")
TOL_CM = 0.2
NEAR_CM = 5.0
PIPE_CATS = ("M.pipe", "P.cold", "P.hot", "P.drain", "P.ff", "P.storm", "P.irr")
DEVICE_CATS = ("P.fix", "P.tank", "P.heater", "P.pump", "P.equip", "P.irr", "P.storm", "P.drain", "P.ff", "P.cold", "P.hot", "M.pipe", "M.equip")

FAMILY_BY_TYPE = {
    "pipe_cold": "cold", "proposed_route_cold": "cold", "ws_site_pipe": "cold", "ws_fill_drop": "cold", "proposed_route_water_site": "cold",
    "pipe_hot": "hot", "proposed_route_hot": "hot",
    "pipe_waste": "drain", "pipe_soil": "drain", "proposed_route_drain": "drain", "vent_drain_pipe": "drain", "vent_top_termination": "drain",
    "pressure_drain_pipe": "drain", "pipe_site": "drain",
    "storm_pipe": "storm", "proposed_route_storm": "storm",
    "pipe_ff": "fire", "pipe_ffc": "fire", "sprk_drop": "fire", "pipe_fp_branch": "fire", "pipe_fp_header": "fire", "riser_spr": "fire",
    "riser_ffc": "fire", "pipe_suction": "fire", "proposed_route_fire": "fire",
    "pipe_chws": "chw_s", "pipe_chwr": "chw_r",
    "irr_pipe": "irrigation", "proposed_route_irrigation": "irrigation",
}

def is_pipe_path(e):
    a = e.get("a") or {}
    return e["c"] in PIPE_CATS and e["g"][0] == "t" and not a.get("alt") and not a.get("assembly")   # generated assembly members declare their own kit_ports

def family_of(e, by):
    t = e.get("t"); a = e.get("a") or {}
    if t in FAMILY_BY_TYPE: return FAMILY_BY_TYPE[t], "type"
    if t == "proposed_route_chw":
        fams = set()
        for k in ("from_id", "to_id"):
            o = by.get(a.get(k))
            if o and o.get("t") in FAMILY_BY_TYPE: fams.add(FAMILY_BY_TYPE[o["t"]])
        if len(fams) == 1: return fams.pop(), "inherited_from_endpoints"
        return "chw", "proposal_unresolved"
    return "unclassified:" + t, "category_fallback"

def dn_of(e):
    a = e.get("a") or {}
    if isinstance(a.get("dia_mm"), (int, float)):
        note = a.get("dia_note") or ""
        basis = "written" if note.startswith("من وسم") else ("assumed_default" if note.startswith("افتراضي") else ("written_riser" if "FF-105" in note else "model_value"))
        return a["dia_mm"], basis
    return round(e["g"][2] * 10, 1), "drawn_diameter_assumed"

def d3(p, q):
    return math.sqrt((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + ((p[2] - q[2]) * 100.0) ** 2)

def seg_dist3(p, a, b):
    ax, ay, az, bx, by_, bz = a[0], a[1], a[2] * 100.0, b[0], b[1], b[2] * 100.0
    px, py, pz = p[0], p[1], p[2] * 100.0
    vx, vy, vz = bx - ax, by_ - ay, bz - az
    L2 = vx * vx + vy * vy + vz * vz
    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy + (pz - az) * vz) / L2))
    cx, cy, cz = ax + t * vx, ay + t * vy, az + t * vz
    return math.sqrt((px - cx) ** 2 + (py - cy) ** 2 + (pz - cz) ** 2), t

def device_shape(e):
    """Return (shapely geometry in plan, z0, z1) of a non-path element, or None."""
    from shapely.geometry import Point, Polygon, box
    from shapely.affinity import rotate
    g = e["g"]; k = g[0]
    try:
        if k == "b":
            r = box(g[1] - g[3] / 2, g[2] - g[4] / 2, g[1] + g[3] / 2, g[2] + g[4] / 2)
            return rotate(r, g[5], origin=(g[1], g[2])) if g[5] else r, g[6], g[7]
        if k == "cyl": return Point(g[1], g[2]).buffer(g[3]), g[4], g[5]
        if k == "r": return box(min(g[1], g[3]), min(g[2], g[4]), max(g[1], g[3]), max(g[2], g[4])), g[5], g[6]
        if k == "p" and len(g[1]) >= 3:
            pg = Polygon(g[1]);  pg = pg if pg.is_valid else pg.buffer(0)
            return pg, g[2], g[3]
    except Exception:
        return None
    return None

def derive(M):
    from shapely.geometry import Point, LineString
    from shapely.strtree import STRtree
    els = M["els"]; by = {e["id"]: e for e in els}
    paths = [e for e in els if is_pipe_path(e)]
    ports = []
    for e in paths:
        fam, fb = family_of(e, by); dn, db = dn_of(e); pts = e["g"][1]
        for end, p in (("S", pts[0]), ("E", pts[-1])):
            ports.append({"id": e["id"] + "#" + end, "el": e["id"], "end": end, "xyz": [round(p[0], 3), round(p[1], 3), round(p[2], 4)],
                          "sys": fam, "sys_basis": fb, "dn_mm": dn, "dn_basis": db, "level": e["l"]})
    for e in els:                      # ports declared by generated assemblies (a.kit_ports); pipe paths above get theirs from geometry
        for pr in (e.get("a") or {}).get("kit_ports") or []:
            ports.append({"id": e["id"] + "#" + pr["end"], "el": e["id"], "end": pr["end"], "xyz": [round(v, 4) for v in pr["xyz"]],
                          "sys": pr["sys"], "sys_basis": "kit", "dn_mm": pr["dn_mm"], "dn_basis": pr.get("dn_basis", "kit"), "level": e["l"],
                          "joint": pr.get("joint")})
    pb = {p["id"]: p for p in ports}
    # --- grid hash for port-port search (cell = NEAR_CM)
    cell = NEAR_CM; grid = collections.defaultdict(list)
    for p in ports: grid[(math.floor(p["xyz"][0] / cell), math.floor(p["xyz"][1] / cell), math.floor(p["xyz"][2] * 100 / cell))].append(p)
    def neighbours(p, r):
        cx, cy, cz = math.floor(p["xyz"][0] / cell), math.floor(p["xyz"][1] / cell), math.floor(p["xyz"][2] * 100 / cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for q in grid.get((cx + dx, cy + dy, cz + dz), ()):
                        if q["id"] != p["id"] and q["el"] != p["el"]:
                            d = d3(p["xyz"], q["xyz"])
                            if d <= r: yield q, d
    # --- segments of paths for branch tests
    segs = []; seglines = []
    for e in paths:
        pts = e["g"][1]
        for i in range(len(pts) - 1):
            segs.append((e["id"], pts[i], pts[i + 1])); seglines.append(LineString([(pts[i][0], pts[i][1]), (pts[i + 1][0], pts[i + 1][1])]))
    tree = STRtree(seglines)
    # --- devices
    dev = [e for e in els if e["c"] in DEVICE_CATS and e["g"][0] != "t" and not (e.get("a") or {}).get("alt")]
    dshapes = []; dgeoms = []
    for e in dev:
        s = device_shape(e)
        if s and s[0] is not None and not s[0].is_empty: dshapes.append((e["id"], s[1], s[2])); dgeoms.append(s[0])
    dtree = STRtree(dgeoms) if dgeoms else None
    joins = {}; state = {}
    for p in ports:
        peers = []; cross = []; near = []           # peers: (port, d); cross/near: (element id, d)
        for q, d in neighbours(p, NEAR_CM):
            if d <= TOL_CM:
                if q["sys"] == p["sys"]: peers.append((q, d))
                else: cross.append((q["el"], d))
            elif q["sys"] == p["sys"]: near.append((q["el"], d))
        branch = []; inline = []
        pt = Point(p["xyz"][0], p["xyz"][1])
        for i in sorted(int(x) for x in tree.query(pt.buffer(NEAR_CM))):
            sid, a, b = segs[i]
            if sid == p["el"]: continue
            d, t = seg_dist3(p["xyz"], a, b)
            if d > NEAR_CM or d3(p["xyz"], a) <= TOL_CM or d3(p["xyz"], b) <= TOL_CM: continue   # segment ends are port-port cases
            ofam, _ = family_of(by[sid], by)
            if d <= TOL_CM:
                if ofam != p["sys"]: cross.append((sid, d))
                elif ((by[p["el"]].get("a") or {}).get("assembly") or {}).get("carrier") == sid: inline.append((sid, d))
                else: branch.append((sid, d))
            elif ofam == p["sys"]: near.append((sid, d))
        for q, d in peers:
            key = tuple(sorted((p["id"], q["id"])))
            if key not in joins:
                dn_differs = abs(p["dn_mm"] - q["dn_mm"]) > 1e-6
                joins[key] = {"kind": "joined", "a": key[0], "b": key[1], "dist_cm": round(d, 3), "sys": p["sys"], "dn_differs": dn_differs,
                              "dn_mm": sorted([p["dn_mm"], q["dn_mm"]])}
        for sid, d in inline:
            joins[(p["id"], sid)] = {"kind": "inline", "a": p["id"], "b": sid, "dist_cm": round(d, 3), "sys": p["sys"], "dn_differs": False, "dn_mm": [p["dn_mm"]]}
        for sid, d in branch:
            joins[(p["id"], sid)] = {"kind": "branch", "a": p["id"], "b": sid, "dist_cm": round(d, 3), "sys": p["sys"], "dn_differs": False, "dn_mm": [p["dn_mm"]]}
        if peers: state[p["id"]] = ("joined", None)
        elif branch: state[p["id"]] = ("branch", None)
        elif inline: state[p["id"]] = ("inline", None)
        else:
            reason = None
            if cross: reason = "cross_system:" + sorted(c[0] for c in cross)[0]
            else:
                if dtree is not None:
                    for i in sorted(int(x) for x in dtree.query(pt.buffer(TOL_CM))):
                        did, z0, z1 = dshapes[i]
                        if z0 - 0.005 <= p["xyz"][2] <= z1 + 0.005 and dgeoms[i].distance(pt) <= TOL_CM:
                            reason = "at_device:" + did; break
                if reason is None:
                    if near:
                        qid, d = sorted(near, key=lambda x: (x[1], x[0]))[0]; reason = "near_miss:%s:%.2f" % (qid, d)
                    else: reason = "free_end"
            state[p["id"]] = ("open", reason)
    for p in ports: p["state"], p["reason"] = state[p["id"]]
    ports.sort(key=lambda p: p["id"])
    jl = sorted(joins.values(), key=lambda j: (j["kind"], j["a"], j["b"]))
    return {"ports": ports, "joins": jl}

def summary(d):
    c = collections.Counter(p["state"] for p in d["ports"])
    r = collections.Counter((p["reason"] or "").split(":")[0] for p in d["ports"] if p["state"] == "open")
    return {"ports": len(d["ports"]), "states": dict(c), "open_reasons": dict(r), "joins": len(d["joins"]),
            "dn_differs": sum(1 for j in d["joins"] if j["dn_differs"])}

def main():
    M = json.load(open(MODEL, encoding="utf-8")); d = derive(M)
    doc = {"schema": "c4.ports.v1", "tolerance_cm": TOL_CM, "near_cm": NEAR_CM, "summary": summary(d), "ports": d["ports"], "joins": d["joins"]}
    with open(OUT + ".tmp", "w", encoding="utf-8") as f: json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(OUT + ".tmp", OUT)
    print("ports:", json.dumps(doc["summary"], ensure_ascii=False))

if __name__ == "__main__":
    main()
