# -*- coding: utf-8 -*-
"""Gate: drawn network components must remain at their documented positions."""
import json, os, sys

M = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "model.json"), encoding="utf-8"))
KNOWN = {"M.duct-G-VT0043"}  # legacy ground-floor duct: unsupported, not moved
bad = [(e["id"], e["t"], (e.get("a") or {}).get("guess_kind") or "unsupported") for e in M["els"]
       if (e.get("a") or {}).get("sys") and ((e.get("a") or {}).get("guess_from") or (e.get("a") or {}).get("unsupported")) and e["id"] not in KNOWN]
print("network components moved or unsupported:", len(bad))
moved = [e for e in M["els"] if (e.get("a") or {}).get("sys") and (e.get("a") or {}).get("guess_from")]
unsupported = [e for e in M["els"] if (e.get("a") or {}).get("sys") and (e.get("a") or {}).get("unsupported") and e["id"] not in KNOWN]
print("moved:", len(moved), "| unsupported:", len(unsupported), "| known legacy unsupported:", len(KNOWN))
for b in bad[:40]: print("  ", b)
sys.exit(1 if bad else 0)
