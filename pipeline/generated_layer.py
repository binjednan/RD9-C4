# -*- coding: utf-8 -*-
"""Generated layer: assemblies produced from drawing SAMPLES (work order 3b-4).  Merged by post_model.py right after the frozen baseline
is read; never written into the baseline.

Files: pipeline/data/generated/*.json   (override the folder with env C4_GENERATED_DIR for tests)
  {"schema": "c4.generated.v1", "family": "...", "kit_library_version": "...",
   "elements": [ ... normal elements + src[] strings ... ],
   "types": {...}, "mats": {...},
   "assemblies": [ {"id", "kit", "kit_version", "host", "carrier", "sample": {"id","sheet","version"}, "slots": {"<slot>": "<element id>"}} ]}
Every generated element carries  a.basis = "sample", a.sample = {id, sheet, version}, a.assembly = {id, kit, slot[, carrier]}.
Ids are deterministic from (host, kit, slot) - see element_id().  The loader refuses duplicates and anything that would replace an existing element.
"""
import copy, hashlib, json, os
from pathlib import Path

HERE = Path(__file__).resolve().parent

def generated_dir():
    return Path(os.environ.get("C4_GENERATED_DIR") or (HERE / "data" / "generated"))

def files():
    d = generated_dir()
    return sorted(p for p in d.glob("*.json")) if d.is_dir() else []

def element_id(cat, level, kit, host_id, slot):
    """Deterministic id: <cat>-<level>-ASM-<kit>-<host tail>-<slot>   (host tail = host id without '<cat>-<level>-')."""
    tail = host_id.split("-", 2)[2] if host_id.count("-") >= 2 else host_id
    return "%s-%s-ASM-%s-%s-%s" % (cat, level, kit, tail, slot)

def sha256_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def apply(M):
    existing = {e["id"] for e in M["els"]}
    sp = M.setdefault("sp", []); sidx = {s: i for i, s in enumerate(sp)}
    assemblies = []; per_file = {}; hashes = {}; added = 0
    for p in files():
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("schema") != "c4.generated.v1": raise ValueError("%s: unknown generated schema" % p.name)
        for k, v in (d.get("types") or {}).items(): M.setdefault("types", {}).setdefault(k, copy.deepcopy(v))
        for k, v in (d.get("mats") or {}).items(): M.setdefault("mats", {}).setdefault(k, copy.deepcopy(v))
        n = 0
        for saved in d.get("elements") or []:
            if saved["id"] in existing: raise ValueError("generated element would duplicate an existing id: " + saved["id"])
            e = copy.deepcopy(saved); refs = []
            for s in e.pop("src", []):
                if s not in sidx: sidx[s] = len(sp); sp.append(s)
                refs.append(sidx[s])
            e["s"] = refs
            M["els"].append(e); existing.add(e["id"]); n += 1
        assemblies.extend(d.get("assemblies") or [])
        per_file[p.stem] = n; added += n; hashes[p.name] = sha256_file(p)
    M["assemblies"] = sorted(assemblies, key=lambda a: a["id"])
    M.setdefault("meta", {})["generated_layer"] = {"files": hashes, "elements": added, "assemblies": len(assemblies)}
    return {"module": "generated_layer", "added": added, "assemblies": len(assemblies), "by_file": per_file}
