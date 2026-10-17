# -*- coding: utf-8 -*-
"""Lifecycle (system tests) snapshot and diff.  python3 tools/lifecycle_snapshot.py --save | python3 tools/lifecycle_snapshot.py [--detail]
Reads M['lifecycle'] from src/model.json: per system (original drawings + with proposals) the counts and the test results.
Totals line mirrors the owner's reference format: <tests ok>/<tests total> and <ends ok>/<ends total>.  --save stores pipeline/data/baseline/lifecycle_ref.json."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, "pipeline", "data", "baseline", "lifecycle_ref.json")

def snap(M):
    L = M["lifecycle"]; out = {}
    for mode, items in (("orig", {s["id"]: s for s in L["systems"]}), ("prop", L.get("proposals") or {})):
        for sid, s in items.items():
            out["%s:%s" % (mode, sid)] = {"cnt": s["cnt"], "tests": {t["id"]: [t["ok"], t["of"]] for t in s.get("tests") or []}}
    return out

def totals(sn, mode):
    tests_ok = tests_all = ends_ok = ends_all = 0
    for k, v in sn.items():
        if not k.startswith(mode + ":"): continue
        for ok, of in v["tests"].values(): tests_all += 1; tests_ok += 1 if ok == of else 0
        ends_all += v["cnt"].get("ter", 0); ends_ok += v["cnt"].get("ok", 0)
    return "tests %d/%d | ends %d/%d" % (tests_ok, tests_all, ends_ok, ends_all)

def effective(sn):
    """Owner's reference metric: per system the proposal result where it exists, else the original-drawings result (21 networks)."""
    ids = sorted({k.split(":", 1)[1] for k in sn if k.startswith("orig:")}); ta = to = ea = eo = 0
    for sid in ids:
        v = sn.get("prop:" + sid) or sn["orig:" + sid]
        for ok, of in v["tests"].values(): ta += 1; to += 1 if ok == of else 0
        ea += v["cnt"].get("ter", 0); eo += v["cnt"].get("ok", 0)
    return "%d networks | tests %d/%d | ends %d/%d" % (len(ids), to, ta, eo, ea)

def main():
    M = json.load(open(os.path.join(ROOT, "src", "model.json"), encoding="utf-8")); sn = snap(M)
    if "--save" in sys.argv:
        json.dump(sn, open(REF, "w"), ensure_ascii=False, sort_keys=True); print("lifecycle ref saved:", len(sn), "systems")
    print("original: ", totals(sn, "orig")); print("proposals:", totals(sn, "prop")); print("effective (owner reference format):", effective(sn))
    if os.path.exists(REF) and "--save" not in sys.argv:
        ref = json.load(open(REF)); ch = 0
        for k in sorted(set(sn) | set(ref)):
            a, b = ref.get(k), sn.get(k)
            if a != b:
                ch += 1
                ca, cb = (a or {}).get("cnt", {}), (b or {}).get("cnt", {})
                print("  changed", k, {x: (ca.get(x), cb.get(x)) for x in set(ca) | set(cb) if ca.get(x) != cb.get(x)})
                ta, tb = (a or {}).get("tests", {}), (b or {}).get("tests", {})
                for t in sorted(set(ta) | set(tb)):
                    if ta.get(t) != tb.get(t): print("     test", t, ta.get(t), "->", tb.get(t))
        print("systems changed vs ref: %d" % ch)

if __name__ == "__main__":
    main()
