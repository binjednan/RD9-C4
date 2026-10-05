# -*- coding: utf-8 -*-
"""helpers that write the sample recipes (parts are plain dicts, see src/detail.js for the meaning of every key).
Local frame of a sample (cm): x = width, y = up, z = depth (+z = front); origin = bottom-centre of the element (anchor 'bottom'),
top-centre ('top', ceiling devices hang below y=0) or centre ('center').  Any number may be an expression string using W, D, H, T, i ..."""

def box(a, b, c, m="matte", n=None, **kw):
    """box between two corners a=(x0,y0,z0) b=(x1,y1,z1)"""
    d = {"k": "box", "a": list(a), "b": list(b), "c": c, "m": m}
    if n: d["n"] = n
    d.update(kw); return d

def cyl(p, r, h, c, m="matte", ax="y", seg=18, r1=None, n=None, **kw):
    """cylinder / cone: p = centre of the base, length h along ax (y|x|z), radius r (base) and r1 (top)"""
    d = {"k": "cyl", "p": list(p), "r": r, "h": h, "c": c, "m": m, "seg": seg}
    if ax != "y": d["ax"] = ax
    if r1 is not None: d["r1"] = r1
    if n: d["n"] = n
    d.update(kw); return d

def sph(p, r, c, m="matte", s=None, seg=14, n=None, **kw):
    d = {"k": "sph", "p": list(p), "c": c, "m": m, "seg": seg}
    if s is not None: d["s"] = s
    else: d["r"] = r
    if n: d["n"] = n
    d.update(kw); return d

def tor(p, R, r, c, m="matte", ax="y", seg=24, n=None, **kw):
    d = {"k": "tor", "p": list(p), "R": R, "r": r, "c": c, "m": m, "seg": seg}
    if ax != "y": d["ax"] = ax
    if n: d["n"] = n
    d.update(kw); return d

def ext(poly, h, c, m="matte", p=(0, 0, 0), n=None, **kw):
    """polygon in the x-z plane (list of [x, z]) extruded upward by h from y=p[1]"""
    d = {"k": "ext", "poly": [list(q) for q in poly], "h": h, "p": list(p), "c": c, "m": m}
    if n: d["n"] = n
    d.update(kw); return d

def rep(part, n, d):
    """repeat a part n times (expression allowed) shifted by d=(dx,dy,dz) each time (i = 0..n-1 is available in expressions)"""
    part = dict(part); part["rep"] = {"n": n, "d": list(d)}; return part

def mx(part):
    part = dict(part); part["mx"] = True; return part

def sample(id_, name, en, cat, parts, *, kind="object", place=None, dims=None, lod=4.5, conf="derived", src=None, facts=None, asm=None,
           varmap=None, defaults=None, vars=None, notes=None, clip=False):
    s = {"name": name, "en": en, "cat": cat, "kind": kind, "place": place or {"mode": "box", "anchor": "bottom"}, "dims": dims or {},
         "lod": {"r": lod}, "conf": conf, "src": src or [], "facts": facts or [], "asm": asm or [], "parts": parts}
    if varmap: s["varmap"] = varmap
    if defaults: s["defaults"] = defaults
    if vars: s["vars"] = vars
    if notes: s["notes"] = notes
    if clip: s["clip"] = True      # engine clamps every vertex to the unit's W x D footprint (ceilings / finishes must not spill over the room)
    return id_, s

# palette (sRGB hex)
WALNUT = "#7a5236"; WALNUT_D = "#5e3f2a"; STEEL = "#c4c9cf"; STEEL_D = "#8e949c"; GALV = "#aab0b8"; BLACK = "#1f2226"; WHITE = "#f2f2ee"
BRASS = "#b08d57"; RED = "#c0392b"; ALU = "#b9bec4"; ALU_D = "#8a9097"; GLASS = "#9fd0e0"; CONC = "#b4b4ae"; PLASTIC = "#eceae2"; GREY = "#6b7178"
