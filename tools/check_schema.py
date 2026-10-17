# -*- coding: utf-8 -*-
"""Schema + relation gate for src/model.json (fail-closed; exit 1 on any new violation).

  python3 tools/check_schema.py                 # run the gate
  python3 tools/check_schema.py --init-registry # (re)generate pipeline/data/schema/attribute_registry.json from the model (deliberate act)

Checks
  E1 element core: required keys/types, unique ids
  E2 domains: level in levels, category in layers (+pinned exceptions), material in mats (+pinned exceptions)
  E3 geometry: kind known and arity matches the pinned set in element.schema.json
  E4 attributes: every element.a key is in attribute_registry.json and its value type was registered
  R1 relations: no new dangling reference (only pipeline/data/schema/relation_registry.json known_dangling)
  R2 no id-valued field outside the relation registry
  R3 hosts: object category inside the registered object_cats of the field
  R4 inverse pairs agree (support_bracket_id<->bracket_for, support_clip_id<->clip_for, sleeve_id<->parent_conductor_id)
  R5 the relation table on disk is current with the model
  P1 every pipe path has exactly two ports (#S, #E), each with a system family (classified) and a numeric dn_mm > 0
  P2 no silent port end: state is joined/branch/open; open carries a known reason; joined/branch has a recorded join
  P3 every join is re-measured from the model: <= 0.2 cm in 3D and both ends in the SAME system family
  P4 pipeline/data/ports.json is current with the model
  T1 every a.sys string and every a.room label has a relation to a node of tables.systems / tables.spaces
  T2 orphan lists agree with the node tables (system without palette name; label that cannot be a space name) and no relation points at an unknown node
  B1 every a.<x>_source = {type,...} uses a registered source type (pipeline/data/schema/source_types.json) and carries its required fields
  S1 sample basis is complete: a.basis='sample' <=> a.sample{id,sheet,version} and a.assembly{id,kit,slot}
  S2 every relation/assembly with basis 'sample' names its sample id and sheet
  S3 assemblies are consistent (host, members, slots, kit in library, kit version)
  S4 generated ids are deterministic from (cat, level, kit, host, slot)
  S5 no required kit slot is empty
  S6 one assembly per matching host, and the host count equals the kit definition's expected count
"""
import argparse, collections, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import relations as REL
import ports as PORTS
SCHEMA_DIR = os.path.join(ROOT, "pipeline", "data", "schema")
ELEMENT_SCHEMA = os.path.join(SCHEMA_DIR, "element.schema.json")
ATTR_REGISTRY = os.path.join(SCHEMA_DIR, "attribute_registry.json")
MODEL = os.path.join(ROOT, "src", "model.json")

def role_of(key, types, rel_fields):
    if key in rel_fields: return "relation"
    if "source" in key: return "source"
    if "assum" in key or key in ("asm",): return "assumption"
    if set(types) <= {"int", "float"}: return "measure"
    if set(types) <= {"bool"}: return "flag"
    if set(types) <= {"str", "NoneType"}: return "label"
    return "structure"

def init_registry(M):
    R = REL.load_registry(); rel_fields = set(R["fields"]) | set(R["self_reference_fields"]) | set(R["label_fields_not_relations"])
    cnt = collections.Counter(); tp = collections.defaultdict(collections.Counter)
    for e in M["els"]:
        for k, v in (e.get("a") or {}).items():
            cnt[k] += 1; tp[k][type(v).__name__] += 1
    for k, t in (("kit_ports", ["list"]), ("sample", ["dict"]), ("assembly", ["dict"]), ("basis", ["str"])):   # vocabulary of the generated layer, reserved even when empty
        if k not in cnt: cnt[k] = 0; tp[k] = collections.Counter({x: 0 for x in t})
    reg = {"version": 1, "note": "Every element.a key that exists. role is assigned by a mechanical rule (role_basis) and is NOT a semantic claim; 'label' = free text/enum, 'measure' = numeric. New keys must be added here deliberately.",
           "role_basis": "relation=in relation_registry; source=name has 'source'; assumption=name has 'assum'; measure=int/float only; flag=bool; label=str/None; else structure",
           "keys": {k: {"types": sorted(tp[k]), "count": cnt[k], "role": role_of(k, tp[k], rel_fields)} for k in sorted(cnt)}}
    with open(ATTR_REGISTRY, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=1)
    roles = collections.Counter(v["role"] for v in reg["keys"].values())
    print("attribute registry:", len(reg["keys"]), "keys", dict(roles))

def init_element_schema(M):
    ar = collections.defaultdict(set)
    for e in M["els"]: ar[e["g"][0]].add(len(e["g"]))
    sch = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "C4 model element", "type": "object",
           "required": ["id", "c", "l", "g", "t", "m", "a", "s"],
           "properties": {"id": {"type": "string"}, "c": {"type": "string", "description": "category = layers[].subs[][0]"},
                          "l": {"type": "string", "description": "level id = levels[].id"}, "t": {"type": "string"}, "m": {"type": "string", "description": "material = mats key"},
                          "mark": {"type": ["string", "null"]}, "a": {"type": "object", "description": "free attributes; keys governed by attribute_registry.json"},
                          "s": {"type": "array", "description": "source index references"}, "u": {"type": ["string", "null"]}, "u2": {"type": "string"},
                          "grp": {"type": "string"}, "stage": {"type": "string"}, "g": {"type": "array", "description": "[kind, ...]; arity per kind in x-geometry-arity"}},
           "additionalProperties": False,
           "x-geometry-arity": {k: sorted(v) for k, v in sorted(ar.items())},
           "x-pinned-exceptions": {"categories_not_in_layers": [], "materials_not_in_mats": [],
                                   "note": "closed by migration m001 (2026-10-17); any new violation now fails the gate"}}
    with open(ELEMENT_SCHEMA, "w", encoding="utf-8") as f:
        json.dump(sch, f, ensure_ascii=False, indent=1)
    print("element schema written; geometry kinds:", {k: sorted(v) for k, v in ar.items()})

def run(M):
    errs = collections.defaultdict(list)
    sch = json.load(open(ELEMENT_SCHEMA, encoding="utf-8")); reg = json.load(open(ATTR_REGISTRY, encoding="utf-8"))["keys"]
    R = REL.load_registry(); els = M["els"]; by = {e["id"]: e for e in els}
    allowed = set(sch["properties"]); pin = sch["x-pinned-exceptions"]
    levels = {l["id"] for l in M["levels"]}; cats = {s[0] for L in M["layers"] for s in L["subs"]} | set(pin["categories_not_in_layers"])
    mats = set(M["mats"]) | set(pin["materials_not_in_mats"]); arity = sch["x-geometry-arity"]
    if len(by) != len(els): errs["E1 duplicate ids"].append(len(els) - len(by))
    for e in els:
        missing = [k for k in sch["required"] if k not in e]
        if missing: errs["E1 missing keys"].append((e.get("id"), missing)); continue
        extra = set(e) - allowed
        if extra: errs["E1 unknown element keys"].append((e["id"], sorted(extra)))
        if not isinstance(e["a"], dict) or not isinstance(e["g"], list) or not isinstance(e["s"], list): errs["E1 wrong container type"].append(e["id"])
        if e["l"] not in levels: errs["E2 unknown level"].append((e["id"], e["l"]))
        if e["c"] not in cats: errs["E2 unknown category"].append((e["id"], e["c"]))
        if e["m"] not in mats: errs["E2 unknown material"].append((e["id"], e["m"]))
        k = e["g"][0] if e["g"] else None
        if k not in arity or len(e["g"]) not in arity[k]: errs["E3 geometry kind/arity"].append((e["id"], k, len(e["g"])))
        for key, v in e["a"].items():
            r = reg.get(key)
            if r is None: errs["E4 unregistered attribute key"].append(key)
            elif type(v).__name__ not in r["types"]: errs["E4 unregistered value type"].append((key, type(v).__name__))
    d = REL.derive(M, R)
    known = {(k, x) for k, xs in R.get("known_dangling", {}).items() if isinstance(xs, list) for x in xs}
    for k, xs in d["dangling_ids"].items():
        for x in xs:
            if (k, x) not in known: errs["R1 new dangling reference"].append((k, x))
    for k, n in d["unregistered_reference_fields"].items(): errs["R2 id field outside relation registry"].append((k, n))
    F = R["fields"]
    for r in d["relations"]:
        if r["t"] != "hosted_by": continue
        for v in r["via"]:
            oc = F[v].get("object_cats")
            if oc and by[r["o"]]["c"] not in oc: errs["R3 host category outside registered domain"].append((v, r["s"], by[r["o"]]["c"]))
    for fa, fb in (("support_bracket_id", "bracket_for"), ("support_clip_id", "clip_for"), ("sleeve_id", "parent_conductor_id")):
        A = {(e["id"], e["a"][fa]) for e in els if isinstance(e["a"].get(fa), str)}
        B = {(e["a"][fb], e["id"]) for e in els if isinstance(e["a"].get(fb), str)}
        if A != B: errs["R4 inverse pair mismatch"].append((fa, fb, len(A ^ B)))
    pd = PORTS.derive(M); pp = {p["id"]: p for p in pd["ports"]}
    paths = [e for e in els if PORTS.is_pipe_path(e)]
    for e in paths:
        for end in ("S", "E"):
            q = pp.get(e["id"] + "#" + end)
            if q is None: errs["P1 pipe path without port"].append(e["id"] + "#" + end); continue
            if not q["sys"] or q["sys"].startswith("unclassified"): errs["P1 port without classified system"].append(q["id"])
            if not isinstance(q["dn_mm"], (int, float)) or q["dn_mm"] <= 0: errs["P1 port without diameter"].append(q["id"])
    joined_ports = set()
    for j in pd["joins"]:
        joined_ports.add(j["a"]); joined_ports.add(j["b"])
        if j["kind"] == "joined":
            pa, pb_ = pp[j["a"]], pp[j["b"]]
            if pa["sys"] != pb_["sys"]: errs["P3 join across systems"].append((j["a"], j["b"]))
            if PORTS.d3(pa["xyz"], pb_["xyz"]) > PORTS.TOL_CM + 1e-6: errs["P3 join farther than 0.2 cm"].append((j["a"], j["b"]))
        else:                                        # branch / inline: port on the interior of another run of the same family
            pa = pp[j["a"]]; o = by[j["b"]]
            if PORTS.family_of(o, by)[0] != pa["sys"]: errs["P3 branch across systems"].append((j["a"], j["b"]))
            dmin = min(PORTS.seg_dist3(pa["xyz"], o["g"][1][i], o["g"][1][i + 1])[0] for i in range(len(o["g"][1]) - 1))
            if dmin > PORTS.TOL_CM + 1e-6: errs["P3 branch farther than 0.2 cm"].append((j["a"], j["b"]))
    known_reasons = ("cross_system:", "at_device:", "near_miss:", "free_end")
    for q in pd["ports"]:
        if q["state"] not in ("joined", "branch", "inline", "open"): errs["P2 silent port state"].append(q["id"])
        elif q["state"] == "open" and not (q["reason"] or "").startswith(known_reasons): errs["P2 open end without reason"].append(q["id"])
        elif q["state"] in ("joined", "branch", "inline") and q["id"] not in joined_ports: errs["P2 joined port without join record"].append(q["id"])
    try:
        pdisk = json.load(open(PORTS.OUT, encoding="utf-8"))
        if pdisk["ports"] != pd["ports"] or pdisk["joins"] != pd["joins"]: errs["P4 ports.json is stale (run pipeline/ports.py)"].append(1)
    except OSError:
        errs["P4 ports.json missing"].append(1)
    ST = json.load(open(os.path.join(SCHEMA_DIR, "source_types.json"), encoding="utf-8"))["types"]
    for e in els:
        for k, v in e["a"].items():
            if k.endswith("_source") and isinstance(v, dict) and "type" in v:
                st = ST.get(v["type"])
                if st is None: errs["B1 unknown source type"].append((e["id"], k, v["type"]))
                else:
                    miss = [r for r in st.get("requires", []) if not v.get(r.split(".")[0])]
                    if miss: errs["B1 source type without its required fields"].append((e["id"], k, miss))
    def sample_ok(x): return isinstance(x, dict) and all(isinstance(x.get(k), str) and x.get(k) for k in ("id", "sheet", "version"))
    import generated_layer as GEN
    kits = {}
    kdir = os.path.join(ROOT, "pipeline", "data", "library", "kits")
    for fn in sorted(os.listdir(kdir)) if os.path.isdir(kdir) else []:
        if fn.endswith(".json"):
            kd = json.load(open(os.path.join(kdir, fn), encoding="utf-8")); kits[kd["id"]] = kd
    A_by = {A["id"]: A for A in M.get("assemblies") or []}
    if len(A_by) != len(M.get("assemblies") or []): errs["S3 duplicate assembly id"].append(1)
    for e in els:
        a = e["a"]
        if a.get("basis") == "sample" or "sample" in a or "assembly" in a:
            if a.get("basis") != "sample": errs["S1 sample element without basis=sample"].append(e["id"])
            if not sample_ok(a.get("sample")): errs["S1 basis=sample without sample id/sheet/version"].append(e["id"])
            asm = a.get("assembly")
            if not (isinstance(asm, dict) and asm.get("id") and asm.get("slot") and asm.get("kit")): errs["S1 sample element without assembly id/kit/slot"].append(e["id"]); continue
            A = A_by.get(asm["id"])
            if A is None: errs["S3 member of unknown assembly"].append((e["id"], asm["id"])); continue
            if A["slots"].get(asm["slot"]) != e["id"]: errs["S3 slot table disagrees with element"].append((e["id"], asm["slot"]))
            if A["host"] in by and e["id"] != GEN.element_id(e["c"], e["l"], asm["kit"], A["host"], asm["slot"]): errs["S4 non-deterministic id"].append(e["id"])
    for r in d["relations"]:
        if r.get("basis") == "sample" and not sample_ok(r.get("sample")): errs["S2 sample relation without sample id/sheet"].append((r["t"], r["s"], r["o"]))
    for kid, kd in kits.items():                               # S6: one assembly per matching host, exactly the expected count
        hs = kd.get("host") or {}
        import kits as KITS
        hosts = KITS.host_selector(kd, {"els": [e for e in els if not e["a"].get("assembly")], "levels": M["levels"]})
        n_asm = sum(1 for A in A_by.values() if A["kit"] == kid)
        if "expected" in hs and len(hosts) != hs["expected"]: errs["S6 host count differs from the kit definition"].append((kid, len(hosts), hs["expected"]))
        if n_asm != len(hosts): errs["S6 assemblies differ from matching hosts"].append((kid, n_asm, len(hosts)))
    for A in A_by.values():
        if A["host"] not in by: errs["S3 assembly host missing"].append(A["id"])
        if not sample_ok(A.get("sample")): errs["S2 assembly without sample id/sheet/version"].append(A["id"])
        kd = kits.get(A["kit"])
        if kd is None: errs["S3 assembly kit not in library"].append((A["id"], A["kit"])); continue
        if kd["version"] != A.get("kit_version"): errs["S3 assembly kit version differs from library"].append((A["id"], A.get("kit_version"), kd["version"]))
        for sl in kd["slots"]:
            if sl.get("required", True) and sl["slot"] not in A["slots"]: errs["S5 assembly with empty required slot"].append((A["id"], sl["slot"]))
        for sl, eid in A["slots"].items():
            if eid not in by: errs["S3 slot element missing"].append((A["id"], sl, eid))
    T = d["tables"]; sys_ids = {n["id"] for n in T["systems"]}; spc_ids = {n["id"] for n in T["spaces"]}
    have = collections.defaultdict(set)
    for r in d["relations"]:
        if r["t"] in ("member_of_system", "in_space"): have[r["t"]].add((r["s"], r["o"]))
    for e in els:
        v = e["a"].get("sys")
        if isinstance(v, str) and v:
            if (e["id"], "SYS:" + v) not in have["member_of_system"] or "SYS:" + v not in sys_ids: errs["T1 a.sys without relation/node"].append((e["id"], v))
        rm = e["a"].get("room")
        for lab in (rm if isinstance(rm, list) else [rm]):
            if isinstance(lab, str) and lab:
                k = "SPC:%s:%s" % (e["l"], lab)
                if (e["id"], k) not in have["in_space"] or k not in spc_ids: errs["T1 a.room label without relation/node"].append((e["id"], lab))
    orph_sys = {o["id"] for o in T["orphans"]["sys"]}; orph_room = {o["id"] for o in T["orphans"]["room"]}
    for n in T["systems"]:
        if (n["name"] is None) != (n["id"] in orph_sys): errs["T2 orphan system list disagrees with table"].append(n["id"])
    for n in T["spaces"]:
        if (n["label_kind"] != "name") != (n["id"] in orph_room): errs["T2 orphan space list disagrees with table"].append(n["id"])
    for r in d["relations"]:
        if r["t"] == "member_of_system" and r["o"] not in sys_ids: errs["T2 relation to unknown system node"].append(r["o"])
        if r["t"] == "in_space" and r["o"] not in spc_ids: errs["T2 relation to unknown space node"].append(r["o"])
    try:
        disk = json.load(open(REL.OUT, encoding="utf-8"))
        cur = sorted(d["relations"], key=lambda r: (r["t"], r["s"] or "", r["o"] or "", r.get("link", ""), str(r.get("ports", ""))))
        if disk["relations"] != cur or disk.get("tables") != json.loads(json.dumps(d["tables"], ensure_ascii=False)): errs["R5 relations.json is stale (run pipeline/relations.py)"].append(1)
    except OSError:
        errs["R5 relations.json missing"].append(1)
    return errs, d

def main():
    p = argparse.ArgumentParser(); p.add_argument("--init-registry", action="store_true"); a = p.parse_args()
    with open(MODEL, encoding="utf-8") as f: M = json.load(f)
    if a.init_registry:
        init_element_schema(M); init_registry(M); return 0
    errs, d = run(M)
    for k in sorted(errs): print("FAIL", k, len(errs[k]), errs[k][:3])
    print("schema gate: %d elements, %d relations, %d violations" % (len(M["els"]), len(d["relations"]), sum(len(v) for v in errs.values())))
    return 1 if errs else 0

if __name__ == "__main__":
    sys.exit(main())
