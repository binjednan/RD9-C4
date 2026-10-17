# -*- coding: utf-8 -*-
"""DR-106 sample applied to drain paths that end AT a fixture or trap (work order item 10-f).

  python3 pipeline/drain_assign.py        # reads src/model.json (generated members ignored) -> pipeline/data/library/drain_assignments.json

Sample (MECH2 ص9, DR-106): toilet 110 mm slope 1:60; bidet/basin/tub/sink/washer 50 mm slope 1:40; floor drain 82 mm.
A path is assigned only when one of its ENDS lies at such a device (ports.py reason at_device); the label becomes the written diameter that
pipe_dimensions.py then turns into an EN 1329 OD.  Paths that reach no device keep their assumed diameter (the downstream network is not sized here), and
slopes are recorded as an attribute (a.slope_dr106) - the assumed Z of the connected paths is NOT altered.
"""
import json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
import ports as P, kits as K
OUT = os.path.join(HERE, "data", "library", "drain_assignments.json")
RULE = {"san_wc": (110, "1:60"), "san_tub": (50, "1:40"), "san_basin": (50, "1:40"), "san_shower": (50, "1:40"), "floor_trap": (82, "1:40")}

def main():
    M = K.model_without_generated(); by = {e["id"]: e for e in M["els"]}
    pd = P.derive(M); paths = {e["id"] for e in M["els"] if P.is_pipe_path(e) and e["t"] in ("pipe_waste", "pipe_soil")}
    cand = collections.defaultdict(list)
    for p in pd["ports"]:
        if p["el"] in paths and p["state"] == "open" and (p["reason"] or "").startswith("at_device:"):
            dev = by[p["reason"].split(":", 1)[1]]
            if dev["t"] in RULE: cand[p["el"]].append((RULE[dev["t"]][0], RULE[dev["t"]][1], dev["id"], dev["t"]))
    rows = {}
    for pid, c in sorted(cand.items()):
        lab, slope, did, dt = max(c)                                   # the largest sample size among the devices it reaches
        rows[pid] = {"label_mm": lab, "slope": slope, "device": did, "device_type": dt, "devices_reached": len(c)}
    doc = {"schema": "c4.drain_assignments.v1", "sample": {"id": "MECH2.DR-106.DEVICES", "sheet": "MECH2 ص9 (DR-106)", "version": "1"}, "paths_total": len(paths), "assigned": len(rows), "rows": rows}
    with open(OUT + ".tmp", "w", encoding="utf-8") as f: json.dump(doc, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    os.replace(OUT + ".tmp", OUT)
    print("drain_assign: %d of %d waste/soil paths assigned" % (len(rows), len(paths)), dict(collections.Counter(r["device_type"] for r in rows.values())))

if __name__ == "__main__":
    main()
