# -*- coding: utf-8 -*-
"""Pipe diameter correction from standards (work order item 8).  Axes are never touched: only the tube DIAMETER g[2] changes.

The drawings write INNER diameters for plumbing (MECH2 ص24 note 1 / WS note 8) and nominal DN for chilled-water steel (BOQ 12.9).  The model drew the written
number as the outside diameter without wall or insulation.  Here, per path (geometry 't' in the pipe categories, not alt, not a proposed route):
  1. resolve the written label (undo the model's own 1.1x padding where the value is not a standard size);
  2. pick the pipe from the standard (library: pipeline/data/library/dimensions.json): steel -> ASME B36.10M Sch 40 by DN; PPR -> ISO 15874 PN20, smallest
     size whose INNER diameter >= the written inner diameter; drainage/storm/irrigation -> EN 1329 outside-diameter series (label = OD);
  3. add insulation where the documents state it (chw 25/50, hot 25/50, cold 50 when exposed; exposed = levels R, T);
  4. draw the jacket (OD + 2 x insulation) or the bare OD as the tube diameter; record everything in attributes with the standard's name.
Proposed routes (assumed cross-section) are left alone.  Run order: before decisions.apply (lifecycle is recomputed afterwards).
"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "data", "library", "dimensions.json")
import ports as P

_EXPOSED = ("R", "T")
STEEL_LABELS = [15, 20, 25, 32, 40, 50, 65, 80, 100, 125, 150, 200]
PPR_LABELS = [20, 25, 32, 40, 50, 65, 75, 100, 125, 150]
PLAIN_PIPE_FAM = {"drain", "storm", "irrigation"}

def load():
    return json.load(open(LIB, encoding="utf-8"))

def resolve_label(dn, basis, allowed, extra=()):
    notes = []
    ok = set(allowed) | set(extra)
    if dn in ok: return next(a for a in ok if a == dn), notes
    for a in sorted(ok):
        if abs(dn - a * 1.1) <= max(0.6, 0.015 * dn):
            notes.append("written %.4g = 1.1 x %d: the model padded its own default; label taken as %d" % (dn, a, a)); return a, notes
    pick = min(sorted(ok), key=lambda a: (abs(a - dn), -a))      # nearest listed size, a tie goes to the larger
    notes.append("written %.4g is not a standard size; nearest listed %d used (assumed)" % (dn, pick))
    return pick, notes

def compute(e, fam, dn, dnbasis, lib):
    """Return dict of attributes (or None when the family is not dimensioned)."""
    exposed = e["l"] in _EXPOSED; a = {}; assumed = []
    if fam in ("chw_s", "chw_r", "fire"):
        lab, n = resolve_label(dn, dnbasis, STEEL_LABELS, extra=(75,)); assumed += n
        d = 80 if lab == 75 else lab
        if lab == 75: assumed.append("DN75 in BOQ = NPS 3 = DN80 (assumed alias)")
        row = lib["steel_pipe_sch40"]["rows"][str(d)]
        od, wall = row["od"], row["wall"]
        ins = (lib["insulation"]["chw_exposed"] if exposed else lib["insulation"]["chw_indoor"]) if fam.startswith("chw") else 0
        spec = "ASME B36.10M Sch 40 DN%d (NPS %s)" % (d, row["nps"]); std = "ASME B36.10M"
        st = lib["steel_pipe_sch40"]["status"]["15-100" if d <= 100 else "125-200"]
        if fam == "fire": assumed.append("fire pipe material is not stated in the sheets: black steel Sch 40 assumed")
        kind = "nominal"
    elif fam in ("cold", "hot"):
        lab, n = resolve_label(dn, dnbasis, PPR_LABELS); assumed += n
        rows = lib["ppr_pn20"]["rows"]; pick = None
        for k in sorted(rows, key=lambda x: int(x)):
            if rows[k]["id"] >= lab: pick = k; break
        if pick is None: pick = max(rows, key=lambda x: int(x)); assumed.append("no PPR size reaches the written inner diameter; largest listed used")
        od, wall = rows[pick]["od"], rows[pick]["wall"]
        if fam == "hot": ins = lib["insulation"]["hot_exposed"] if exposed else lib["insulation"]["hot_indoor"]
        else: ins = lib["insulation"]["cold_exposed"] if exposed else 0
        spec = "ISO 15874 PP-R PN20 (SDR 6) %dx%.1f" % (od, wall); std = "ISO 15874"
        if fam == "cold": assumed.append("cold-water PPR PN is not stated (PN20 assumed)")
        st = "verified_1_source" if pick in ("25", "40", "125") else "derived_rule"
        kind = "inner"
    elif fam in PLAIN_PIPE_FAM:
        sizes = lib["upvc_soil_waste_en1329"]["od_sizes"]
        lab, n = resolve_label(dn, dnbasis, sizes); assumed += n
        if lab == 150: pass
        od, wall, ins = float(lab), None, 0
        spec = "uPVC EN 1329 OD %d (wall not verified)" % lab; std = "EN 1329"; st = "verified_1_source"
        assumed.append("drain/storm pipe label read as nominal outside diameter (EN 1329 series); wall and material class not stated")
        kind = "nominal_od"
    else:
        return None
    jacket = od + 2 * ins if ins else None
    drawn = (jacket if ins else od) / 10.0
    return {"dn_label_mm": lab, "dn_label_kind": kind, "od_mm": od, "wall_mm": wall, "insul_mm": ins, "jacket_od_mm": jacket, "dim_spec": spec,
            "dim_source": {"type": "standard", "standard": std, "status": st, "assumptions": assumed}, "_drawn_cm": round(drawn, 4)}

def _assignments():
    p = os.path.join(HERE, "data", "library", "drain_assignments.json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {"rows": {}, "sample": None}

def apply(M):
    lib = load(); by = {e["id"]: e for e in M["els"]}; changed = 0; skipped = 0; fams = {}
    AS = _assignments()
    for e in M["els"]:
        if not P.is_pipe_path(e): continue
        if (e.get("t") or "").startswith("proposed_route"): skipped += 1; continue
        fam, _ = P.family_of(e, by)
        dn, basis = P.dn_of(e); asg = AS["rows"].get(e["id"])
        if asg: dn, basis = float(asg["label_mm"]), "sample_dr106"
        r = compute(e, fam, dn, basis, lib)
        if r is None: skipped += 1; continue
        drawn = r.pop("_drawn_cm")
        if asg:
            r["dim_source"]["assumptions"].append("diameter from the DR-106 device rule: %s reaches %s (%d mm); the written diameter %.4g was a type default" % (e["id"], asg["device"], asg["label_mm"], P.dn_of(e)[0]))
            r["slope_dr106"] = asg["slope"]; r["slope_source"] = {"type": "drawing_sample", "sample": dict(AS["sample"])}
        e["a"].update(r)
        if e["g"][2] != drawn: e["g"][2] = drawn; changed += 1
        fams[fam] = fams.get(fam, 0) + 1
    return {"module": "pipe_dimensions", "dimensioned": sum(fams.values()), "diameter_changed": changed, "skipped_proposals_or_other": skipped, "by_family": fams}
