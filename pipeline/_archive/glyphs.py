# -*- coding: utf-8 -*-
"""Pipe-layer drawings that are not pipes: flow-arrow heads (closed 3-5 point outlines, 15-80 cm), valve bow-ties, leader ticks, and the
polylines that result when an arrow head is merged with the pipe it sits on.  Shared by mep_bg.py (new extraction) and post_model.py
(existing tower-level elements).  A pipe is a polyline = list of (x, y, ...) points in cm."""
import math, collections

def _len(pl):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pl[:-1], pl[1:]))

def _closed(pl, tol=2.0):
    return len(pl) > 2 and math.hypot(pl[0][0] - pl[-1][0], pl[0][1] - pl[-1][1]) < tol

def _loops(pl, tol=1.5):
    """polyline returns to an earlier vertex (arrow head merged with its shaft)"""
    for i in range(len(pl)):
        for j in range(i + 2, len(pl)):
            if math.hypot(pl[i][0] - pl[j][0], pl[i][1] - pl[j][1]) <= tol and j - i >= 2 and not (i == 0 and j == len(pl) - 1 and len(pl) > 6):
                return True
    return False

def flags(pls):
    """pls: list of polylines -> list of bool 'is glyph'"""
    pts = collections.defaultdict(list)
    for i, p in enumerate(pls):
        for q in (p[0], p[-1]): pts[(round(q[0] / 3), round(q[1] / 3))].append(i)
    def touches(i, q):
        k = (round(q[0] / 3), round(q[1] / 3))
        return any(j != i for dx in (-1, 0, 1) for dy in (-1, 0, 1) for j in pts.get((k[0] + dx, k[1] + dy), []))
    out = []
    for i, pl in enumerate(pls):
        L = _len(pl)
        if _closed(pl) and L < 100 and len(pl) <= 6: out.append(True); continue
        if L < 150 and _loops(pl): out.append(True); continue
        if L < 45 and not (touches(i, pl[0]) and touches(i, pl[-1])): out.append(True); continue
        out.append(False)
    return out
