# -*- coding: utf-8 -*-
"""Ground-floor columns that do not exist at the ground floor.

Owner 2026-10-07: «the selected columns and those like them are columns of the underground floor only and have no extension in the ground floor».
Checked against the drawings:
  * S-11 (GROUND FLOOR COLUMN LAYOUT) draws every 20 x 140 facade fin (tags C5 / untagged, y = -10 and 1800) as an EMPTY outline = PLANTED COLUMN (PC, legend of the sheet): a column that is
    planted on the slab, it starts at the level above and is NOT a ground-storey column; S-12 (typical floor) draws the same fins again as PC: they are the facade fins of the first floor and above.
  * A102 (ground floor plan) shows at those positions no column at all (the colonnade is the black 60 x 60 columns with their GRC wrap, 440 cm clear between them).
So the 20 x 140 fins are removed from the ground level (they stay from the first floor up).  The four corner ones (x = 105 / 3185) overlap the corner 60 x 60 column by only 35 %: also removed.
Matching is by plan centre (3 cm) and size, so the removal is stable when ids are renumbered."""
import collections

# (cx, cy, w, h) of the S.col elements removed at level G
PLANTED = [(505, 1800, 20, 140), (1195, 1800, 20, 140), (1785, 1800, 20, 140), (2155, 1800, 20, 140), (2815, 1800, 20, 140),
           (505, -10, 20, 140), (1195, -10, 20, 140), (1785, -10, 20, 140), (2155, -10, 20, 140), (2815, -10, 20, 140),
           (105, 1800, 20, 140), (105, -10, 20, 140), (3185, 1800, 20, 140), (3185, -10, 20, 140)]
EVIDENCE = ("STR ص16 (S-11): رمز العمود المزروع PC (مستطيل مفرغ) عند هذه المواضع؛ ARCH1 ص5 (A102): لا عمود عند هذه المواضع في الدور الأرضي؛ "
            "تظهر في STR ص17 (S-12) من الدور الأول فما فوق")


def _box(g):
    if g[0] == "p":
        xs = [p[0] for p in g[1]]; ys = [p[1] for p in g[1]]
        return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs), max(ys) - min(ys)
    if g[0] == "r":
        return (g[1] + g[3]) / 2, (g[2] + g[4]) / 2, abs(g[3] - g[1]), abs(g[4] - g[2])
    return None


def remove_planted(els):
    """removes the planted (PC) fin columns from level G in place; returns the removed ids"""
    gone = []
    keep = []
    for e in els:
        if e["c"] == "S.col" and e["l"] == "G":
            b = _box(e["g"])
            if b and any(abs(b[0] - x) <= 3 and abs(b[1] - y) <= 3 and abs(b[2] - w) <= 3 and abs(b[3] - h) <= 3 for x, y, w, h in PLANTED):
                gone.append(e["id"]); continue
        keep.append(e)
    els[:] = keep
    return gone
