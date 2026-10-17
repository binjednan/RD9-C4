# -*- coding: utf-8 -*-
"""Per-step gate runner (work order 3b+4).  Runs: relations.py, check_schema, element fingerprint diff, check_network_relocation.

  python3 tools/step_gates.py --make-ref        # store the fingerprint reference from the current src/model.json (do this right after a deliberate refreeze)
  python3 tools/step_gates.py [--show 5]        # run all gates; prints diff counts against the reference

Fingerprint per element: full = md5(canonical element JSON), xy = md5(plan coordinates only, rounded 0.01 cm).
Reference lives in pipeline/data/baseline/fingerprint_ref.json.  "generated" = element with a.sample or in pipeline/data/generated.
Memory is measured separately by tools/measure_memory.py (needs a browser, outside the sandbox).
"""
import argparse, hashlib, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
REF = os.path.join(ROOT, "pipeline", "data", "baseline", "fingerprint_ref.json")
MODEL = os.path.join(ROOT, "src", "model.json")
PT_KINDS = {"p", "d", "t", "tri", "rs", "mesh"}

def h(x): return hashlib.md5(json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()[:16]

def xy_of(g):
    k = g[0]
    if k in PT_KINDS:
        pts = g[1]
        return [[round(q[0], 2), round(q[1], 2)] for q in pts] if k != "rs" else [[round(q[0], 2), round(q[1], 2)] for q in pts]
    if k == "r": return [round((g[1] + g[3]) / 2, 2), round((g[2] + g[4]) / 2, 2)]      # box centre: a profile resize about its centre plane is not a move
    return [round(g[1], 2), round(g[2], 2)]

def fingerprints(M):
    return {e["id"]: [h(e), h(xy_of(e["g"]))] for e in M["els"]}

def make_ref(from_baseline=False):
    M = json.load(open(os.path.join(ROOT, "pipeline", "data", "baseline", "model.base.json") if from_baseline else MODEL, encoding="utf-8"))
    fp = fingerprints(M)
    json.dump(fp, open(REF, "w"), separators=(",", ":"))
    print("fingerprint ref:", len(fp), "elements")

def compare(show):
    M = json.load(open(MODEL, encoding="utf-8")); cur = fingerprints(M)
    ref = json.load(open(REF))
    added = sorted(set(cur) - set(ref)); removed = sorted(set(ref) - set(cur))
    changed = sorted(i for i in cur if i in ref and cur[i][0] != ref[i][0])
    moved = sorted(i for i in changed if cur[i][1] != ref[i][1])
    gen = {e["id"] for e in M["els"] if (e.get("a") or {}).get("sample")}
    print("fingerprint: ref %d | now %d | added %d (generated %d) | removed %d | content-changed %d | XY-moved %d" %
          (len(ref), len(cur), len(added), len(set(added) & gen), len(removed), len(changed), len(moved)))
    for name, ids in (("added", added), ("removed", removed), ("changed", changed), ("moved", moved)):
        if ids and show: print("  %s sample:" % name, ids[:show])
    return {"added": added, "removed": removed, "changed": changed, "moved": moved}

def run(cmd, tail=3):
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()[-tail:]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--make-ref", action="store_true"); ap.add_argument("--from-baseline", action="store_true"); ap.add_argument("--show", type=int, default=5); ap.add_argument("--skip-schema", action="store_true"); a = ap.parse_args()
    if a.make_ref: make_ref(a.from_baseline); return 0
    ok = True
    for name, cmd in (("ports", [sys.executable, "-B", "pipeline/ports.py"]),
                      ("relations", [sys.executable, "-B", "pipeline/relations.py"]),
                      ("check_schema", [sys.executable, "-B", "tools/check_schema.py"]),
                      ("check_network_relocation", [sys.executable, "-B", "tools/check_network_relocation.py"]),
                      ("lifecycle_snapshot", [sys.executable, "-B", "tools/lifecycle_snapshot.py"])):
        if a.skip_schema and name == "check_schema": continue
        rc, tail = run(cmd, 12 if name == "lifecycle_snapshot" else 3); print("[%s] exit=%d | %s" % (name, rc, " / ".join(t[:200] for t in tail))); ok = ok and rc == 0
    d = compare(a.show)
    json.dump({k: v for k, v in d.items()}, open(os.path.join(ROOT, ".cache", "last_diff.json"), "w")) if os.path.isdir(os.path.join(ROOT, ".cache")) else None
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
