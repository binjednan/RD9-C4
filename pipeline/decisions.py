# -*- coding: utf-8 -*-
"""Owner decisions applied AFTER the layers are merged (work order 3b-6).  The frozen baseline is never touched; rollback = delete the file.

File: pipeline/data/decisions/*.json   {"schema": "c4.decision.v1", "id", "removes": [element ids], "set_attrs": {id: {attr: value}}, "set_g": {id: {slot index: value}}, "retire_refs": {id: {field: removed id}}, "types_asm_replace": {type: [[old line, new line]]}, ...}
Applying a decision removes the listed elements (every id must exist: fail-closed), remaps element-index references (like source_batch does) and
records M['meta']['decisions'].  When anything was removed the lifecycle (network tests) is recomputed so the displayed results match the model.
"""
import hashlib, json
from pathlib import Path

DIR = Path(__file__).resolve().parent / "data" / "decisions"

def files():
    return sorted(DIR.glob("*.json")) if DIR.is_dir() else []

def apply(M, force_lifecycle=False):
    done = []; removed_total = 0; geom_total = 0
    for p in files():
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("schema") != "c4.decision.v1": raise ValueError("%s: unknown decision schema" % p.name)
        ids = set(d["removes"]); present = {e["id"] for e in M["els"]}
        missing = sorted(ids - present)
        if missing: raise ValueError("%s: %d ids to remove are not in the model, e.g. %s" % (p.name, len(missing), missing[:3]))
        by = {e["id"]: e for e in M["els"]}
        for eid, kv in (d.get("set_attrs") or {}).items():
            if eid not in by: raise ValueError("%s: set_attrs id not in the model: %s" % (p.name, eid))
            by[eid].setdefault("a", {}).update(kv)
        for eid, kv in (d.get("set_g") or {}).items():            # replace numeric geometry slots by index (Z of boxes etc.); plan XY is never given here
            if eid not in by: raise ValueError("%s: set_g id not in the model: %s" % (p.name, eid))
            for i, v in kv.items(): by[eid]["g"][int(i)] = v
        for t, pairs in (d.get("types_asm_replace") or {}).items():
            asm = (M.get("types") or {}).get(t, {}).get("asm")
            if asm is None: raise ValueError("%s: type %s has no asm lines" % (p.name, t))
            for old_line, new_line in pairs:
                if old_line not in asm: raise ValueError("%s: line to replace not found in type %s" % (p.name, t))
                asm[asm.index(old_line)] = new_line
        for eid, refs in (d.get("retire_refs") or {}).items():   # an end that names a removed element keeps only a trace (retired_<field>), never a dangling id
            if eid not in by: raise ValueError("%s: retire_refs id not in the model: %s" % (p.name, eid))
            for k, v in refs.items():
                if (by[eid].get("a") or {}).get(k) == v:
                    del by[eid]["a"][k]; by[eid]["a"]["retired_" + k] = v
        before = [e["id"] for e in M["els"]]
        M["els"][:] = [e for e in M["els"] if e["id"] not in ids]
        after = {e["id"]: i for i, e in enumerate(M["els"])}
        from source_batch import remap_index_refs
        remap_index_refs(M, {i: after[eid] for i, eid in enumerate(before) if eid in after}, [i for i, eid in enumerate(before) if eid not in after], include_lifecycle=False)  # lifecycle is rebuilt below
        done.append({"id": d["id"], "file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "removed": len(ids), "attrs_set": len(d.get("set_attrs") or {}), "geom_set": len(d.get("set_g") or {})}); removed_total += len(ids); geom_total += len(d.get("set_g") or {})
    M.setdefault("meta", {})["decisions"] = done
    if removed_total or force_lifecycle or geom_total:
        import lifecycle as LC
        results = LC.run(M, False); M["lifecycle"] = LC.pack(M, results); LC.add_proposals(M)
        import freeze_baseline as FB
        M["lifecycle"]["built"] = FB.load_manifest()["frozen_at"][:16].replace("T", " ")   # deterministic stamp (the baseline's), not the wall clock
    return {"module": "decisions", "removed": removed_total, "files": [x["file"] for x in done]}
