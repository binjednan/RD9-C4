# -*- coding: utf-8 -*-
"""Full deterministic rebuild:  python3 pipeline/rebuild.py
 post_model (frozen baseline -> layers/dimensions/sections/decisions)  ->  drain_assign + kits (read that output, ignoring generated members)  ->  post_model again
 -> ports -> relations -> schema gate -> build.  Run twice: the generated files and src/model.json must keep the same sha256 (checked by --verify-stable)."""
import hashlib, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
def run(*a):
    r = subprocess.run([sys.executable, "-B"] + list(a), cwd=ROOT, capture_output=True, text=True)
    print("$ %s -> exit %d" % (" ".join(a), r.returncode), (r.stdout.strip().splitlines() or [""])[-1][:150])
    if r.returncode: print(r.stderr[-1500:]); sys.exit(r.returncode)
def digest():
    h = hashlib.sha256()
    gdir = os.path.join(HERE, "data", "generated")
    for f in sorted(os.listdir(gdir)): h.update(open(os.path.join(gdir, f), "rb").read())
    h.update(open(os.path.join(ROOT, "src", "model.json"), "rb").read()); return h.hexdigest()[:16]
if __name__ == "__main__":
    for step in (["pipeline/post_model.py"], ["pipeline/drain_assign.py"], ["pipeline/kits.py"], ["pipeline/post_model.py"], ["pipeline/ports.py"], ["pipeline/relations.py"], ["tools/check_schema.py"], ["src/build.py"]): run(*step)
    print("generated+model digest:", digest())
