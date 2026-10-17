# -*- coding: utf-8 -*-
"""Derive ONE normalized relation table from the free attribute fields already in the model.

  python3 pipeline/relations.py          # reads src/model.json, writes pipeline/data/relations.json

Element content is never changed.  The vocabulary lives in data/schema/relation_registry.json
(each legacy field -> a relation type); a field that references element ids but is not in the registry
is reported as `unregistered_reference_fields` (the gate in tools/check_schema.py fails on it).
Row: {"t": type, "s": subject id, "o": object id, "via": [fields], "basis": "confirmed"|"assumed"}.
"""
import json, os, collections
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODEL = os.path.join(ROOT, "src", "model.json")
REGISTRY = os.path.join(HERE, "data", "schema", "relation_registry.json")
OUT = os.path.join(HERE, "data", "relations.json")

def load_registry():
    with open(REGISTRY, encoding="utf-8") as f:
        return json.load(f)

import re
def _label_kind(lab):
    """Mechanical, not semantic: which room labels cannot be a space NAME."""
    t = lab.strip()
    if re.fullmatch(r"[0-9.\-/ ]+", t): return "numeric_only"
    if re.search(r"M²|m²|M2$", t): return "area_annotation"
    if len(t) <= 1: return "single_character"
    if t.upper() in ("ROOM", "RM"): return "generic_placeholder"
    return "name"

def derive(M, R=None):
    R = R or load_registry()
    F = R["fields"]; selfref = set(R["self_reference_fields"]); labels = set(R["label_fields_not_relations"])
    els = M["els"]; ids = {e["id"] for e in els}
    rows = {}; dangling_ids = {}
    dangling = collections.Counter(); self_refs = collections.Counter(); unreg = collections.Counter(); notid = collections.Counter()
    for e in els:
        a = e.get("a") or {}
        for k, v in a.items():
            vals = v if isinstance(v, list) else [v]
            strs = [x for x in vals if isinstance(x, str)]
            if k in F:
                spec = F[k]
                for x in strs:
                    if x not in ids:
                        dangling[k] += 1; dangling_ids.setdefault(k, []).append(x); continue
                    if x == e["id"]:
                        self_refs[k] += 1; continue
                    if spec["type"] == "connects":
                        continue            # handled below as one row per link element
                    s, o = (x, e["id"]) if spec.get("reverse") else (e["id"], x)
                    key = (spec["type"], s, o)
                    r = rows.setdefault(key, {"t": spec["type"], "s": s, "o": o, "via": [], "basis": spec["basis"]})
                    if k not in r["via"]: r["via"].append(k)
                    if spec["basis"] == "assumed": r["basis"] = "assumed"
            elif k in selfref or k in labels:
                if k in selfref: self_refs[k] += sum(1 for x in strs if x == e["id"])
            else:
                n = sum(1 for x in strs if x in ids)
                if n: unreg[k] += n
        # one `connects` row per link element: s=from, o=to, link=element id
        ends = {}
        for k in ("from_id", "from"):
            if isinstance(a.get(k), str) and a[k] in ids: ends.setdefault("from", a[k]); ends.setdefault("from_via", []).append(k)
        for k in ("to_id", "to"):
            if isinstance(a.get(k), str) and a[k] in ids: ends.setdefault("to", a[k]); ends.setdefault("to_via", []).append(k)
        if "from" in ends and "to" in ends:
            key = ("connects", e["id"], ends["from"], ends["to"])
            rows[key] = {"t": "connects", "s": ends["from"], "o": ends["to"], "link": e["id"],
                         "via": ends["from_via"] + ends["to_via"], "basis": "confirmed"}
        elif "from" in ends or "to" in ends:
            side = "from" if "from" in ends else "to"
            key = ("connects", e["id"], ends.get("from"), ends.get("to"))
            rows[key] = {"t": "connects", "s": ends.get("from"), "o": ends.get("to"), "link": e["id"], "open": "to" if side == "from" else "from",
                         "via": ends.get(side + "_via", []), "basis": "confirmed"}
    # a.sys / a.room -> relations to node tables (the legacy fields stay); a value that cannot be a node is listed as an orphan with its reason
    pal = (M.get("displayPalette") or {}).get("systems") or {}
    systems = {}; spaces = {}; orphans = {"sys": [], "room": []}
    for e in els:
        a = e.get("a") or {}
        v = a.get("sys")
        if isinstance(v, str) and v:
            n = systems.setdefault(v, {"id": "SYS:" + v, "value": v, "name": (pal.get(v) or {}).get("name"), "color": (pal.get(v) or {}).get("color"),
                                       "name_basis": "displayPalette.systems" if v in pal else None, "elements": 0, "cats": collections.Counter()})
            n["elements"] += 1; n["cats"][e["c"]] += 1
            rows[("member_of_system", e["id"], "SYS:" + v)] = {"t": "member_of_system", "s": e["id"], "o": "SYS:" + v, "via": ["a.sys"], "basis": "label"}
        rm = a.get("room")
        for lab in (rm if isinstance(rm, list) else [rm]):
            if isinstance(lab, str) and lab:
                key = "SPC:%s:%s" % (e["l"], lab)
                n = spaces.setdefault(key, {"id": key, "level": e["l"], "label": lab, "label_kind": _label_kind(lab), "elements": 0, "cats": collections.Counter()})
                n["elements"] += 1; n["cats"][e["c"]] += 1
                rows[("in_space", e["id"], key)] = {"t": "in_space", "s": e["id"], "o": key, "via": ["a.room"], "basis": "label"}
    for v, n in sorted(systems.items()):
        if n["name"] is None: orphans["sys"].append({"id": n["id"], "reason": "no name in displayPalette.systems (legacy or internal label)", "elements": n["elements"]})
    for k, n in sorted(spaces.items()):
        if n["label_kind"] != "name": orphans["room"].append({"id": k, "reason": n["label_kind"], "elements": n["elements"]})
    tables = {"systems": [dict(n, cats=dict(sorted(n["cats"].items()))) for _, n in sorted(systems.items())],
              "spaces": [dict(n, cats=dict(sorted(n["cats"].items()))) for _, n in sorted(spaces.items())], "orphans": orphans}
    # assemblies generated from drawing samples: member -> assembly, assembly host -> member relation, all basis=sample
    for e in els:
        asm = (e.get("a") or {}).get("assembly")
        if asm:
            smp = (e["a"].get("sample") or {})
            rows[("part_of_assembly", e["id"], asm["id"])] = {"t": "part_of_assembly", "s": e["id"], "o": asm["id"], "via": ["a.assembly"], "slot": asm.get("slot"),
                                                              "basis": e["a"].get("basis"), "sample": {k: smp.get(k) for k in ("id", "sheet", "version")}}
    for A in M.get("assemblies") or []:
        if A.get("host") in ids:
            rows[("assembled_on", A["id"], A["host"])] = {"t": "assembled_on", "s": A["id"], "o": A["host"], "via": ["assemblies"], "kit": A["kit"],
                                                          "basis": "sample", "sample": dict(A.get("sample") or {})}
    # ports / pipe-network joins (derived from geometry by pipeline/ports.py; element content untouched)
    import ports as _PORTS
    pd = _PORTS.derive(M); pel = {p["id"]: p["el"] for p in pd["ports"]}
    for j in pd["joins"]:
        s_ = pel[j["a"]]; o_ = pel.get(j["b"], j["b"])
        t_ = {"joined": "joins", "branch": "branches_from", "inline": "inserted_in"}[j["kind"]]
        rows[(t_, s_, o_, j["a"], j["b"])] = {"t": t_, "s": s_, "o": o_, "via": ["port"], "ports": [j["a"], j["b"]], "dist_cm": j["dist_cm"],
                                               "dn_differs": j["dn_differs"], "basis": "derived_contact"}
    return {"relations": list(rows.values()), "dangling": dict(dangling), "self_refs": dict(self_refs),
            "unregistered_reference_fields": dict(unreg), "dangling_ids": dangling_ids, "tables": tables}

def main():
    with open(MODEL, encoding="utf-8") as f:
        M = json.load(f)
    d = derive(M)
    by_type = collections.Counter(r["t"] for r in d["relations"])
    doc = {"schema": "c4.relations.v1", "elements": len(M["els"]), "counts": dict(by_type),
           "diagnostics": {k: d[k] for k in ("dangling", "self_refs", "unregistered_reference_fields", "dangling_ids")},
           "tables": d["tables"],
           "relations": sorted(d["relations"], key=lambda r: (r["t"], r["s"] or "", r["o"] or "", r.get("link", ""), str(r.get("ports", ""))))}
    with open(OUT + ".tmp", "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(OUT + ".tmp", OUT)
    print("relations:", dict(by_type), "| diagnostics:", doc["diagnostics"])

if __name__ == "__main__":
    main()
