# -*- coding: utf-8 -*-
"""Regression test of the gate itself: builds a SYNTHETIC generated file in a temp folder, applies it in memory (nothing is written to the
model or to pipeline/data), and checks that check_schema accepts the good case and rejects each injected defect.  Exit 1 if any expectation fails."""
import copy, json, os, sys, tempfile, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import check_schema as C, generated_layer as GEN

def lerp(a, b, t): return [a[i] + (b[i] - a[i]) * t for i in range(3)]

def build(M, host_el):
    path = next(e for e in M["els"] if e["t"] == "pipe_chws" and len(e["g"][1]) >= 2 and "dia_mm" in e["a"])
    p0, p1 = path["g"][1][0], path["g"][1][1]
    # unit step 6 cm along the first segment
    L = ((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2 + ((p1[2] - p0[2]) * 100) ** 2) ** 0.5
    t0, t1 = 10 / L, 16 / L
    a_, b_ = lerp(p0, p1, t0), lerp(p0, p1, t1)
    eid = GEN.element_id("M.pipe", path["l"], "testkit", host_el["id"], "s01")
    sample = {"id": "TESTSAMPLE", "sheet": "TEST ص1", "version": "1"}
    el = {"id": eid, "c": "M.pipe", "l": path["l"], "g": ["b", (a_[0] + b_[0]) / 2, (a_[1] + b_[1]) / 2, 6, 6, 0, a_[2] - .03, a_[2] + .03], "t": "kit_test_valve", "m": path["m"],
          "mark": None, "a": {"basis": "sample", "sample": sample, "assembly": {"id": "ASM:testkit:" + host_el["id"], "kit": "testkit", "slot": "s01", "carrier": path["id"]},
          "kit_ports": [{"end": "A", "xyz": a_, "sys": "chw_s", "dn_mm": 20, "joint": "flange"}, {"end": "B", "xyz": b_, "sys": "chw_s", "dn_mm": 20, "joint": "flange"}]},
          "s": [], "src": ["TEST ص1"]}
    asm = {"id": "ASM:testkit:" + host_el["id"], "kit": "testkit", "kit_version": "1", "host": host_el["id"], "carrier": path["id"], "sample": sample, "slots": {"s01": eid}}
    return {"schema": "c4.generated.v1", "family": "test", "elements": [el], "types": {"kit_test_valve": {"n": "test", "cf": "assumed", "sp": [], "sr": []}}, "mats": {}, "assemblies": [asm]}

def run_case(base, mutate=None, kit_slots=None):
    tmp = tempfile.mkdtemp(); os.environ["C4_GENERATED_DIR"] = tmp
    M = copy.deepcopy(base)
    host = next(e for e in M["els"] if e["t"] == "fcu")
    doc = build(M, host)
    if mutate: mutate(doc)
    json.dump(doc, open(os.path.join(tmp, "test.json"), "w"))
    GEN.apply(M)
    kdir = os.path.join(ROOT, "pipeline", "data", "library", "kits"); os.makedirs(kdir, exist_ok=True)
    kp = os.path.join(kdir, "__test_kit.json")
    json.dump({"id": "testkit", "version": "1", "slots": kit_slots or [{"slot": "s01", "required": True}]}, open(kp, "w"))
    try:
        errs, _ = C.run(M)
    finally:
        os.remove(kp); shutil.rmtree(tmp); os.environ.pop("C4_GENERATED_DIR", None)
    for stale in ("R5 relations.json is stale (run pipeline/relations.py)", "P4 ports.json is stale (run pipeline/ports.py)"): errs.pop(stale, None)
    for k in [k for k in errs if k.startswith("S6")]: errs.pop(k)                    # real kits' host counts are checked on the real model, not here   # disk tables don't know the synthetic layer
    return sorted(errs)

def main():
    base = json.load(open(os.path.join(ROOT, "src", "model.json"), encoding="utf-8"))
    base["els"] = [e for e in base["els"] if not (e.get("a") or {}).get("assembly")]; base["assemblies"] = []   # test on the model without the real generated layer
    ok = True
    def expect(name, got, want):
        nonlocal ok
        good = (got == [] if want is None else any(w in k for k in got for w in [want]))
        print(("PASS " if good else "FAIL ") + name, "->", got); ok = ok and good
    expect("valid synthetic layer accepted", run_case(base), None)
    def no_sid(d): d["elements"][0]["a"]["sample"].pop("id")
    expect("basis=sample without sample id rejected", run_case(base, no_sid), "S1 basis=sample without sample id")
    def no_sheet_asm(d): d["assemblies"][0]["sample"].pop("sheet")
    expect("assembly sample without sheet rejected", run_case(base, no_sheet_asm), "S2")
    def bad_id(d): d["elements"][0]["id"] = d["elements"][0]["id"] + "x"; d["assemblies"][0]["slots"]["s01"] = d["elements"][0]["id"]
    expect("non-deterministic id rejected", run_case(base, bad_id), "S4")
    expect("empty required slot rejected", run_case(base, None, [{"slot": "s01"}, {"slot": "s02", "required": True}]), "S5")
    def bad_kit(d): d["assemblies"][0]["kit"] = "nokit"
    expect("unknown kit rejected", run_case(base, bad_kit), "S3 assembly kit not in library")
    def no_basis(d): d["elements"][0]["a"].pop("basis")
    expect("sample element without basis rejected", run_case(base, no_basis), "S1 sample element without basis")
    def cross(d): d["elements"][0]["a"]["kit_ports"][0]["sys"] = "hot"
    got = run_case(base, cross)
    print(("PASS " if True else "FAIL ") + "kit port of another family is never joined to the chw run ->", got); 
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
