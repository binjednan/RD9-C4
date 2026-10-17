# -*- coding: utf-8 -*-
"""Progress log shown INSIDE the viewer (tab «مراجعة» ← «سجل الإنجاز»).  Builds M['progress'] from docs/RESUME_STATE.md (status table) + the generated layer.
Nothing here touches elements; it only lets the owner follow the work from the project file itself."""
import json, os, re, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)

def apply(M):
    items = []; path = os.path.join(ROOT, "docs", "RESUME_STATE.md")
    if os.path.exists(path):
        for ln in open(path, encoding="utf-8").read().split("\n"):
            if not ln.startswith("| ") or ln.startswith("| #") or ln.startswith("|---"): continue
            p = [x.strip() for x in ln.strip().strip("|").split("|", 2)]
            if len(p) == 3 and p[0] and p[0] != "—": items.append({"k": p[0], "t": p[1], "s": p[2]})
    nxt = []
    pn = os.path.join(HERE, "data", "progress_next.json")
    if os.path.exists(pn): nxt = json.load(open(pn, encoding="utf-8")).get("next", [])
    fam = collections.Counter(); kits = collections.Counter()
    for e in M["els"]:
        a = e.get("a") or {}
        if a.get("assembly"): kits[a["assembly"]["kit"]] += 1
    gl = (M.get("meta") or {}).get("generated_layer") or {}
    M["progress"] = {"items": items, "next": nxt, "generated": {"elements": gl.get("elements", 0), "assemblies": gl.get("assemblies", 0), "by_kit": dict(sorted(kits.items()))},
                     "elements": len(M["els"]), "note": "يُحدَّث تلقائيًا من docs/RESUME_STATE.md عند كل بناء"}
    return {"module": "progress", "items": len(items)}
