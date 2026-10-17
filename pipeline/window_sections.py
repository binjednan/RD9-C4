# -*- coding: utf-8 -*-
"""Window frame sections measured from the sample sheets A803 (vent, 52 x 120 mm) and A1502 (fixed mullion, 60 x 100 mm)  (work order item 10-g).
Only the wall-normal DEPTH of the frame PARTS of windows CW-07..CW-19 changes (8 cm -> 12 cm / 10 cm), symmetrically about the existing centre plane: plan centres and heights of every part are unchanged.
The face widths of the sheets (52 / 60 mm) are recorded but NOT applied: the schedule widths of A800-A802 include the frames and the assembly envelope check must stay inside 0.2 cm.  Parts are 'frame' boxes ['r', x0, y0, x1, y1, z0, z1]; the wall-normal axis is the one with the 8 cm extent.
"""
import json, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "data", "library", "window_sections.json")

def apply(M):
    L = json.load(open(LIB, encoding="utf-8")); S = L["sections"]; types = set(L["types"])
    groups = collections.defaultdict(list)
    for e in M["els"]:
        if e["t"] in types and e.get("grp"): groups[(e["l"], e["grp"])].append(e)
    done = collections.Counter(); skipped = 0
    for key, parts in sorted(groups.items()):
        sec_id = "A803_vent" if any((p.get("a") or {}).get("part") == "vent_glass" for p in parts) else "A1502_mullion"; sec = S[sec_id]
        face, depth = sec["face_mm"] / 10.0, sec["depth_mm"] / 10.0
        for e in parts:
            a = e["a"]
            if a.get("part") != "frame" or e["g"][0] != "r": continue
            g = e["g"]; dx, dy, dz = g[3] - g[1], g[4] - g[2], g[6] - g[5]
            ax = 0 if abs(dx - 8.0) < 0.15 else (1 if abs(dy - 8.0) < 0.15 else None)
            if ax is None: skipped += 1; continue
            n = list(g); lo, hi = (1, 3) if ax == 0 else (2, 4); c = (g[lo] + g[hi]) / 2
            n[lo], n[hi] = round(c - depth / 2, 3), round(c + depth / 2, 3)                      # wall-normal depth
            # the face width / thickness stays at its schedule-given value (A800-A802 widths include the frames: the assembly envelope must not grow); the sheet's face is recorded only
            e["g"] = n
            a["section_basis"] = "sample"; a["section_sample"] = dict(sec["sample"]); a["section_dims_mm"] = {"face_sheet": sec["face_mm"], "depth": sec["depth_mm"]}; a["section_face_applied"] = False
            a["section_assumed"] = "previous 50 x 80 mm was a visual assumption; centre plane kept"
            done[sec_id] += 1
    return {"module": "window_sections", "frames_updated": dict(done), "skipped": skipped}
