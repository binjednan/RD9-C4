# -*- coding: utf-8 -*-
"""The 'floating in the air' audit.  usage: python3 pipeline/audit_support.py [--json out]
Every non-structural element must be carried by something (see pipeline/support.py).  Prints how many are not."""
import json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import support
def main():
    M = json.load(open(os.path.join(HERE, "..", "src", "model.json")))
    wt = set()
    try:
        for k, v in json.load(open(os.path.join(HERE, "..", "src", "samples.json")))["samples"].items():
            if (v.get("place") or {}).get("mount") == "wall": wt.add(k)
    except Exception: pass
    wt.discard("fhc")
    S = support.Support(M["els"], M["levels"], wt)
    res = collections.defaultdict(list); tot = 0
    for i, e in enumerate(M["els"]):
        if e["c"][0] in "SA": continue
        r = S.analyse(i); 
        if r["kind"] == "skip": continue
        tot += 1; res[(r["kind"], e["c"], e.get("t"), e["l"])].append(i)
    cnt = collections.Counter({k[0]: 0 for k in res})
    for k, v in res.items(): cnt[k[0]] += len(v)
    print("checked", tot, "|", dict(cnt))
    for k in ("float", "rod", "hang", "stand"):
        rows = sorted(((c, t, l, len(v)) for (kk, c, t, l), v in res.items() if kk == k), key=lambda r: -r[3])
        print(f"-- {k}: {sum(r[3] for r in rows)}"); [print(f"   {c:9} {str(t):15} {l:2} {n}") for c, t, l, n in rows[:14]]
    if "--json" in sys.argv: json.dump({"|".join(map(str, k)): v for k, v in res.items()}, open(sys.argv[sys.argv.index("--json") + 1], "w"))
if __name__ == "__main__": main()
