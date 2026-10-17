# -*- coding: utf-8 -*-
"""Availability of details by the model's own reliability axes (xy, z, spec).  python3 tools/reliability_report.py [model.json]
Counts elements without the 3,000 display-only 'stage' ones.  'available' = documented (d) or derived (v); 'no assumption' = no axis is 'a'; 'all documented' = d on all three.
Grades are recomputed with pipeline/reliability.py on the file given (default src/model.json), so a rule change shows at once."""
import json, os, sys, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import reliability as R

def report(M, strict=False):
    """strict=True: a sample element whose own size/length is catalogue-assumed (length_basis mentions assumed) keeps spec 'a' (the sample fixed only its type and place)."""
    T = M.get("types", {}); ax = {k: collections.Counter() for k in ("xy", "z", "spec")}; none_a = all_d = n = 0
    for e in M["els"]:
        q = R.grade(e, T)
        if strict and (e.get("a") or {}).get("sample") and "assumed" in str((e["a"].get("length_basis") or "")) and q != "sss": q = q[:2] + "a"
        if q == "sss": continue
        n += 1
        for i, k in enumerate(("xy", "z", "spec")): ax[k][q[i]] += 1
        if "a" not in q: none_a += 1
        if q == "ddd": all_d += 1
    pct = lambda x: round(100.0 * x / n, 1)
    out = {"elements": n, "axes_available_pct": {k: pct(v["d"] + v["v"]) for k, v in ax.items()}, "axes_direct_pct": {k: pct(v["d"]) for k, v in ax.items()},
           "level_and_spec_mean_pct": round((pct(ax["z"]["d"] + ax["z"]["v"]) + pct(ax["spec"]["d"] + ax["spec"]["v"])) / 2, 1), "no_assumption_pct": pct(none_a), "all_documented_pct": pct(all_d)}
    return out

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "src", "model.json")
    M = json.load(open(path, encoding="utf-8"))
    print(json.dumps({"as_ordered": report(M), "strict": report(M, True)}, ensure_ascii=False))
