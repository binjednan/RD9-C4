# -*- coding: utf-8 -*-
"""Freeze src/model.json as the immutable input of the generation pipeline.

  python3 pipeline/freeze_baseline.py --reason "why"     # (re)freeze the current src/model.json; appends to MANIFEST history
  python3 pipeline/freeze_baseline.py --verify           # check baseline bytes against MANIFEST (exit 1 on mismatch)

post_model.py reads ONLY pipeline/data/baseline/model.base.json (verified against the manifest, fail-closed) and
writes src/model.json as a pure output.  Changing the baseline is a deliberate, logged act, never a side effect.
"""
import argparse, hashlib, json, os, shutil, stat, sys, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE_DIR = os.path.join(HERE, "data", "baseline")
BASE = os.path.join(BASE_DIR, "model.base.json")
MANIFEST = os.path.join(BASE_DIR, "MANIFEST.json")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def load_manifest():
    with open(MANIFEST, encoding="utf-8") as f:
        return json.load(f)

def verify(raise_on_error=True):
    """Return the manifest if the baseline matches it, else raise SystemExit (fail-closed)."""
    try:
        man = load_manifest()
        ok = os.path.isfile(BASE) and sha256(BASE) == man["sha256"]
    except (OSError, ValueError, KeyError):
        ok = False; man = None
    if not ok and raise_on_error:
        raise SystemExit("baseline missing or does not match MANIFEST.json: %s (re-freeze deliberately with freeze_baseline.py --reason ...)" % BASE)
    return man if ok else None

def freeze(reason):
    src = os.path.join(ROOT, "src", "model.json")
    with open(src, encoding="utf-8") as f:
        M = json.load(f)
    history = []
    if os.path.isfile(MANIFEST):
        history = load_manifest().get("history", [])
        history.append({k: v for k, v in load_manifest().items() if k != "history"})
    if os.path.isfile(BASE):
        os.chmod(BASE, stat.S_IWUSR | stat.S_IRUSR)
    shutil.copyfile(src, BASE)
    os.chmod(BASE, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    man = {"sha256": sha256(BASE), "bytes": os.path.getsize(BASE), "elements": len(M["els"]),
           "frozen_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "reason": reason,
           "note": "post-processed model frozen as input; the original raw generator is not recoverable (temp session folders)",
           "history": history}
    with open(MANIFEST, "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    print("frozen:", man["elements"], "elements,", man["sha256"][:12])

if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--reason"); p.add_argument("--verify", action="store_true")
    a = p.parse_args()
    if a.verify:
        m = verify(False); print("baseline OK" if m else "baseline MISMATCH"); sys.exit(0 if m else 1)
    if not a.reason:
        raise SystemExit("--reason is required")
    freeze(a.reason)
