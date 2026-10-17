# -*- coding: utf-8 -*-
"""Builds pipeline/data/decisions/OWNER-no-facade-wires.json  (owner decision: no wires on the facade, from photos of the built building).

  python3 tools/build_facade_decision.py [--write]     # run on a model WITHOUT the decision applied (remove the decision file first)

Rule (work order item 6), applied to E.tray conductors and proposed routes at levels G,1,2,3,4,5,R,T (basement excluded: no facade):
  envelope(l) = outer ring of the union of A.wall, S.wall, S.col, A.win, A.door, A.clad footprints at level l (closed by 10 cm); for G the envelope of level 1
                is used because the ground floor shell is open (assumed - awaiting owner confirmation)
  a path is a FACADE wire when the MAJORITY (>= 50%) of its length lies outside the envelope buffered by 0.2 cm or within 0.2 cm of its exterior ring
  (a wire that merely crosses the face to reach a facade device keeps its inside part: whole elements are never trimmed -> kept, listed as partial)
  closure: a facade candidate that another REMAINING wire names as an end (from/to/from_id/to_id) is kept, iterated to a fixed point
  -> no remaining wire is left pointing at a removed one (no new orphan ends by reference)
  kept although outside: E.tray that are not conductors/routes (earthing_pvc_sleeve, elr_* ducts/fiber/trays, site boxes)
  carried items removed with them: owner_wire_clip whose clip_for is a removed wire (owner_box_bracket / owner_flexible_bracket carry DEVICES, never wires -> kept)
"""
import json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import ports as P
from shapely.geometry import Polygon, LineString
from shapely.ops import unary_union
OUT = os.path.join(ROOT, "pipeline", "data", "decisions", "OWNER-no-facade-wires.json")
LEVELS = ["G", "1", "2", "3", "4", "5", "R", "T"]
ENV_CATS = ("A.wall", "S.wall", "S.col", "A.win", "A.door", "A.clad")
WIRE_TYPES = {"proposed_route_power", "wire_light", "wire_drop", "wire_power", "wire_circuit_end", "wire_homerun_open"}
RULE = "any_part"      # owner 2026-10-17 (second instruction): ANY conductor with ANY part outside the envelope (or touching its exterior face) goes, with its clips; only earthing and lightning routes are spared
PROTECTED_ROUTES = {"proposed_route_earthing", "proposed_route_lightning"}   # earthing/lightning/fibre service routes: removing them orphans earth rods, tape and fibre ducts (acceptance: no new orphan ends)
KEEP_TYPES = {"earthing_pvc_sleeve", "elr_power_duct", "elr_fiber", "elr_phone_tray", "elr_gsm_tray", "elr_site_phone", "site_telephone_service_box"}

def envelopes(els):
    env = {}
    for L in LEVELS[1:]:
        fs = []
        for e in els:
            if e["l"] == L and e["c"] in ENV_CATS and e["g"][0] in ("r", "p", "b", "cyl") and not (e["a"] or {}).get("alt"):
                s = P.device_shape(e)
                if s and s[0] is not None and not s[0].is_empty: fs.append(s[0])
        U = unary_union(fs).buffer(10).buffer(-10)
        polys = sorted(U.geoms if U.geom_type == "MultiPolygon" else [U], key=lambda p: -p.area)
        env[L] = Polygon(polys[0].exterior)
    env["G"] = env["1"]
    return env

def build(M):
    els = M["els"]; env = envelopes(els); by = {e["id"]: e for e in els}
    wires = []; kept = []; per_level = collections.Counter()
    for e in els:
        if e["c"] != "E.tray" or e["g"][0] != "t" or e["l"] not in env: continue
        ls = LineString([(p[0], p[1]) for p in e["g"][1]]); E = env[e["l"]]
        if ls.length == 0: continue
        out_len = ls.difference(E.buffer(0.2)).length; face = ls.intersection(E.exterior.buffer(0.2)).length; d = ls.distance(E.exterior)
        if not (out_len > 0.2 or d <= 0.2): continue
        why = "outside_envelope" if out_len > 0.2 else "touches_exterior_face"
        frac = round((out_len + face) / ls.length, 3)
        if e["t"] in PROTECTED_ROUTES: kept.append({"id": e["id"], "type": e["t"], "level": e["l"], "why": why, "kept_because": "protected: earthing/lightning/telephone service route (removal would orphan earth rods / tape / fibre)"}); continue
        if e["t"] in KEEP_TYPES: kept.append({"id": e["id"], "type": e["t"], "level": e["l"], "why": why, "kept_because": "not a conductor/route"}); continue
        if RULE != "any_part" and frac < 0.5: kept.append({"id": e["id"], "type": e["t"], "level": e["l"], "why": why, "fraction_outside": frac, "kept_because": "partial: crosses the face, majority inside"}); continue
        wires.append({"id": e["id"], "type": e["t"], "level": e["l"], "why": why, "fraction_outside": frac}); per_level[e["l"]] += 1
    cand = {w["id"]: w for w in wires}
    while RULE != "any_part":                                   # closure: keep a candidate that a remaining wire still names as an end
        blocked = {}
        for e in els:
            if e["c"] != "E.tray" or e["id"] in cand: continue
            for k in ("from", "to", "from_id", "to_id"):
                v = (e["a"] or {}).get(k)
                if v in cand: blocked.setdefault(v, []).append(e["id"])
        if not blocked: break
        for v, deps in blocked.items():
            w = cand.pop(v); kept.append({"id": v, "type": w["type"], "level": w["level"], "why": w["why"], "fraction_outside": w["fraction_outside"],
                                          "kept_because": "closure: remaining wire(s) depend on it", "dependents": sorted(deps)[:5], "dependents_n": len(deps)})
    wires = [cand[w["id"]] for w in wires if w["id"] in cand]; per_level = collections.Counter(w["level"] for w in wires)
    wid = {w["id"] for w in wires}
    clips = sorted(e["id"] for e in els if e["t"] == "owner_wire_clip" and (e["a"].get("clip_for") in wid))
    # wires that stay but name a removed wire as an end (would be left with a loose end)
    dangling = []
    for e in els:
        if e["c"] != "E.tray" or e["id"] in wid: continue
        for k in ("from", "to", "from_id", "to_id"):
            if (e["a"] or {}).get(k) in wid: dangling.append((e["id"], k, e["a"][k]))
    return wires, kept, clips, dangling, per_level

def orphan_set(M):
    L = M["lifecycle"]; out = set()
    for mode, items in (("orig", {s["id"]: s for s in L["systems"]}), ("prop", L.get("proposals") or {})):
        for sid, s in items.items():
            for i in s.get("o") or []: out.add((mode, sid, M["els"][i]["id"] if isinstance(i, int) else i))
    return out

def simulate(M, ids):
    """Apply the removal on a copy exactly as pipeline/decisions.py does and return the lifecycle orphan set afterwards."""
    import copy, lifecycle as LC
    from source_batch import remap_index_refs
    C = copy.deepcopy(M); before = [e["id"] for e in C["els"]]
    C["els"][:] = [e for e in C["els"] if e["id"] not in ids]; after = {e["id"]: i for i, e in enumerate(C["els"])}
    remap_index_refs(C, {i: after[x] for i, x in enumerate(before) if x in after}, [i for i, x in enumerate(before) if x not in after], include_lifecycle=False)
    res = LC.run(C, False); C["lifecycle"] = LC.pack(C, res); LC.add_proposals(C)
    return orphan_set(C), C

if __name__ == "__main__":
    M = json.load(open(os.path.join(ROOT, "src", "model.json"), encoding="utf-8"))
    if any(x["id"] == "OWNER-no-facade-wires" for x in (M.get("meta") or {}).get("decisions") or []): raise SystemExit("the facade decision is already applied: delete its file and rerun pipeline/post_model.py first")
    wires, kept, clips, dangling, per_level = build(M)
    base_orph = orphan_set(M); by_ = {e["id"]: e for e in M["els"]}
    ids = {w["id"] for w in wires} | {e["id"] for e in M["els"] if e["t"] == "owner_wire_clip" and e["a"].get("clip_for") in {w["id"] for w in wires}}
    new_orph, C = simulate(M, ids)            # consequences only (nothing is added to the removal under the any-part rule)
    fresh = sorted({i for (_, _, i) in new_orph - base_orph}); other = [i for i in fresh if i in by_]
    print("any-part rule: removed %d | NEW lifecycle orphans after removal: %d" % (len(ids), len(fresh)))
    wid_all = {w["id"] for w in wires}
    clips = sorted(e["id"] for e in M["els"] if e["t"] == "owner_wire_clip" and e["a"].get("clip_for") in wid_all)
    dangling = [(e["id"], k, e["a"][k]) for e in M["els"] if e["c"] == "E.tray" and e["id"] not in wid_all for k in ("from", "to", "from_id", "to_id") if (e["a"] or {}).get(k) in wid_all]
    print("new orphan elements:", collections.Counter(by_[i]["t"] for i in fresh if i in by_))
    print("facade wires:", len(wires), dict(per_level), "| by type:", dict(collections.Counter(w["type"] for w in wires)))
    print("kept although outside (not conductors/routes):", len(kept), "| clips removed with them:", len(clips), "| remaining wires naming a removed wire:", len(dangling))
    for x in dangling[:10]: print("   ", x)
    if "--write" in sys.argv:
        doc = {"schema": "c4.decision.v1", "id": "OWNER-no-facade-wires", "owner": "مهند بن قضير", "date": "2026-10-17",
               "statement": "لا أسلاك على الواجهة (من صور المبنى المنفَّذ)", "rule_version": "any_part (owner 2026-10-17, second instruction)", "photos": ["BP-01","BP-02","BP-03","BP-04","BP-05","BP-06"], "evidence_note_current": "BP-01..06: لا أسلاك كهربائية على الواجهة؛ الظاهر صواعد غاز صفراء وعلبة غاز وكشافات جدارية بلا أسلاك ظاهرة", "evidence_note": "الصور الست المذكورة في أمر العمل لم تصل للجلسة؛ نُفِّذ القرار نصًّا بالقاعدة أدناه.",
               "rule": __doc__.strip(), "assumed": ["envelope(G)=envelope(1)", "basement excluded", "box/flexible brackets carry devices so are kept", "earthing and lightning proposed routes are spared (owner); telephone/fibre routes are NOT spared any more", "a remaining wire that named a removed wire as an end keeps no reference (moved to retired_<field>) and may become an orphan end"],
               "retire_refs": {i: {k: v for (j, k, v) in dangling if j == i} for i in sorted({j for (j, k, v) in dangling})}, "removes": sorted([w["id"] for w in wires] + clips), "removed_wires": wires, "removed_clips": clips,
               "kept_outside_not_wires": kept, "rollback": "delete this file and rerun pipeline/post_model.py"}
        json.dump(doc, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1); print("written", OUT)
