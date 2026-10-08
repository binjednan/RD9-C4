# -*- coding: utf-8 -*-
"""Reliability grade of every element (what the model can be trusted for), shown by the viewer as a colour lens and as three chips on the element card.

Three axes, each one letter (d = documented, v = derived, a = assumed, s = staged for display only):

  xy   horizontal position  d: read from the plan symbol / outline          v: computed or moved by a documented rule (snapped to a wall, fixture from a symbol,
                                                                               window module of the A801/A802 grid ...)   a: chosen by the modeller (no drawing)
  z    elevation            d: levels / sections / schedules                  v: rule with documented parameters (false-ceiling FCL, legend mounting heights)
                                                                            a: chosen by the modeller (services in the ceiling void, pipes under slabs ...)
  spec type, size, material d: schedule / legend / BOQ  v: derived from the drawing (size of a symbol ...)  a: assumed (card says «افتراض»)

The element code is the three letters, e.g. "dva"; the overall grade is the worst letter (d < v < a); 's' wins for staged elements.  Rules follow the BIM Forum LOD idea that a
model element is only as reliable as the information it can be relied on for ("field-verified" would be a 4th level 'f' once the as-built drawings are approved: nothing is 'f' yet).
The rules are data (below) so the inventory and the viewer use the same source of truth; they are applied by post_model.py after every other pass."""
import collections

LET = {"doc": "d", "derived": "v", "assumed": "a"}
ORDER = {"d": 0, "v": 1, "a": 2}

# z grade per category (sub-category overrides first)
Z_BY_CAT = {
    "S.beam": "v", "S.pile": "v", "S.ramp": "v", "S.": "d",
    "A.ceil": "v", "A.rail": "v", "A.fix": "v", "A.wfin": "a", "A.stage": "s", "A.": "d",
    "M.equip": "a", "M.duct": "a", "M.pipe": "a", "M.damper": "a", "M.outlet": "v", "M.fan": "v",
    "E.tray": "a", "E.gen": "d", "E.": "v",
    "P.tank": "d", "P.pump": "d", "P.fix": "v", "P.heater": "v", "P.": "a",
}
# types whose elevation follows from the element they hang on (so 'derived', not assumed)
Z_TYPE = {"sprk_pendent": "v", "sprk_upright": "v", "sprk_double": "v", "sprk_drop": "a"}
# categories whose plan position is derived (read from a symbol with a rule) rather than copied from an outline
XY_DERIVED_CATS = ("A.fix", "A.win", "P.fix", "A.wfin")


def _by_prefix(table, c):
    best = None
    for k in table:
        if c == k or c.startswith(k):
            if best is None or len(k) > len(best): best = k
    return table.get(best, "d")


def grade(e, T):
    """returns the three-letter code of one element"""
    a = e.get("a") or {}; c = e["c"]; t = T.get(e.get("t"), {})
    if c == "A.stage" or e.get("stage"): return "sss"
    if a.get("connector") or a.get("riser"): return "vvv"      # derived link between documented ends / riser inferred from the plans (pipeline/connectors.py, pipeline/risers.py)
    spec = LET.get(t.get("cf") or "doc", "d")
    if a.get("assumed") and spec != "a": spec = "a" if c not in ("A.floor",) else spec
    if c == "M.duct" and "افتراضي" in str(a.get("size_note") or ""): spec = "a"
    if c == "P.drain" and "افتراضي" in str(a.get("dia_note") or ""): spec = "a"
    if a.get("derived_type"): spec = "v" if spec == "d" else spec
    xy = "d"
    suffix = e["id"].rsplit("-", 1)[-1]
    if c in XY_DERIVED_CATS and suffix.startswith("X"): xy = "v"
    if a.get("snap_cm"): xy = "v"
    if a.get("guess_from"): xy = "a"                           # relocated by guesses.py (best guess)
    if e.get("t") == "sprk_drop": xy = "v"
    if a.get("unsupported"): xy = "a"
    z = Z_TYPE.get(e.get("t")) or _by_prefix(Z_BY_CAT, c)
    if a.get("buried") or a.get("unsupported") or a.get("guess_from"): z = "a"
    if a.get("mount_note") and "افتراض" in str(a.get("mount_note")): z = "a" if ORDER[z] < 2 else z
    return xy + z + spec


def overall(code):
    if code == "sss": return "s"
    return max(code, key=lambda ch: ORDER.get(ch, 0))


def assign(M):
    T = M.get("types", {}); cnt = collections.Counter(); by_layer = collections.defaultdict(collections.Counter); by_level = collections.defaultdict(collections.Counter)
    axes = {"xy": collections.Counter(), "z": collections.Counter(), "spec": collections.Counter()}
    for e in M["els"]:
        q = grade(e, T); e["q"] = q; o = overall(q)
        cnt[o] += 1; by_layer[e["c"][0]][o] += 1; by_level[e["l"]][o] += 1
        axes["xy"][q[0]] += 1; axes["z"][q[1]] += 1; axes["spec"][q[2]] += 1
    M.setdefault("meta", {})["reliability"] = {"overall": dict(cnt), "layer": {k: dict(v) for k, v in by_layer.items()}, "level": {k: dict(v) for k, v in by_level.items()},
                                              "axes": {k: dict(v) for k, v in axes.items()}}
    print("reliability:", dict(cnt), "| axes", {k: dict(v) for k, v in axes.items()})
    return cnt
