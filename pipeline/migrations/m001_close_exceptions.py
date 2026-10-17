# -*- coding: utf-8 -*-
"""Migration 001 (work order 3b-1): close the three schema exceptions found by the gate on 2026-10-17.

  1. category A.shaft (3 source-alternative shaft outlines) was missing from layers[A].subs  -> registered.
  2. materials fin_CSP-2/3/4 (175 car-park floor zones) were missing from mats -> registered with the SAME
     'unknown_not_independently_reviewed' template as the parent fin_CSP (no new claim about the material).
  3. two source-candidate return ducts named outlets retired in HVO v2 (they were duct strokes, not grille bodies;
     docs/HANDOFF_REMAINING_ARCH_FIRE.md) -> source_group_ids moved to retired_source_group_ids (identity kept as trace).

Reads src/model.json, writes src/model.json (then freeze_baseline.py --reason ...).  Idempotent.
"""
import copy, json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "src", "model.json")
RETIRED = {"M.duct-1-MECH1-P03-D16680-P0-SRC": ["M.outlet-1-0150"], "M.duct-1-MECH1-P03-D16740-P0-SRC": ["M.outlet-1-0154"]}

def apply(M):
    log = {}
    A = next(L for L in M["layers"] if L["id"] == "A")
    if not any(s[0] == "A.shaft" for s in A["subs"]):
        A["subs"].append(["A.shaft", "فتحات المناور (بدائل المصدر)"]); log["layers"] = "A.shaft registered"
    base = M["mats"]["fin_CSP"]
    for n in (2, 3, 4):
        k = "fin_CSP-%d" % n
        if k not in M["mats"]:
            m = copy.deepcopy(base)
            m["name"] = "وصف قديم غير معتمد — طلاء أرضيات مواقف السيارات CSP-%d (جوتا فلور)" % n
            m["historical_definition"] = dict(m["historical_definition"], code="CSP-%d" % n)
            m["registered_by"] = "migration m001 (2026-10-17): registered only to close the schema exception; material identity still not independently reviewed"
            m["source_refs"] = ["A500:CSP-%d (listed, not reviewed)" % n]
            M["mats"][k] = m; log.setdefault("mats", []).append(k)
    by = {e["id"]: e for e in M["els"]}
    for did, ids in RETIRED.items():
        a = by[did]["a"]
        if "source_group_ids" in a and a["source_group_ids"] == ids:
            del a["source_group_ids"]
            a["retired_source_group_ids"] = ids
            a["retired_source_group_reason"] = "identity retired in HVO v2: the old outlet was a duct stroke/break, not a grille body (docs/HANDOFF_REMAINING_ARCH_FIRE.md); kept as trace, no device implied"
            log.setdefault("ducts", []).append(did)
    return log

if __name__ == "__main__":
    M = json.load(open(SRC, encoding="utf-8"))
    log = apply(M)
    with open(SRC + ".tmp", "w", encoding="utf-8") as f:
        json.dump(M, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(SRC + ".tmp", SRC)
    print("m001:", json.dumps(log, ensure_ascii=False))
