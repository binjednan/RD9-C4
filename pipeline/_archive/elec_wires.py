# -*- coding: utf-8 -*-
"""Electrical conductors and distribution boards read from the plan sheets -> pipeline/data/elec_wires.json  (needs the source PDFs, see lib.py; post_model.py merges the json through elec_build.py)

Owner 2026-10-08: «قم بدورة حياة للكهرباء على أن تضيء فقط ما هو موصل داخل المجسم بموصلات كهرباء فعلية».  The model had devices only — no conductor at all.  The electrical plans do draw them:

  ELEC1 lighting plans p1–p6   layer «E.LIGHT CONNE. NORMAL»   a continuous line from fixture to fixture to switch, ends with an arrow and a tag «R1/DB-F1» (phase R/Y/B, circuit number, board)
  ELEC1 power plans    p9–p14  layer «E.POWER. CONNE.NORMAL»   the same circuits drawn DASHED (each dash is its own 2-point drawing: wiring concealed in the floor), tags on layer «E.POWER TEXT»
  boards                       the label of every distribution board sits on layer «E.POWER» next to its symbol: DB-F1 … DB-F6 (one per flat), DB-SR (service rooms), SMDB-n, SMDB-LIFT

What is extracted: every conductor as polylines in plan centimetres (dashes joined, arcs simplified to 3 cm), the arrow tips with their tags, and the board labels with their positions.  What is NOT drawn
(and therefore left to the life-cycle tests to flag): the route from an arrow to its board, and the feeders from the main board to the sub-main boards.

    python3 pipeline/elec_wires.py        # ~ minutes: parses the big sheets once (cached by lib.py)"""
import sys, os, re, json, math, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lib

OUT = os.path.join(HERE, "data", "elec_wires.json")
SHEETS = {   # family -> (pdf, {sheet key: page}, conductor layer fragment, circuit tag layer fragment)
    "light": ("ELEC1", {"B": 1, "G": 2, "1": 3, "TY": 4, "R": 5, "T": 6}, "CONNE", "E.LIGHT TEXT"),
    "power": ("ELEC1", {"B": 9, "G": 10, "1": 11, "TY": 12, "R": 13, "T": 14}, "CONNE", "E.POWER TEXT"),
}
TAG = re.compile(r"^[RYB]\s?\d{1,2}\s*/\s*[A-Z]{2,6}-?[A-Z0-9]*$")
BOARD = re.compile(r"^(S?MDB(?:-[A-Z0-9]+)*|EDB(?:-[A-Z0-9]+)*|DB(?:-[A-Z0-9]+)+)$")      # DB-F1, DB-1-F4, DB-SR, DB-GF, DB-SH-2, SMDB-LIFT, MDB …
TOL = 0.8; GAP = 6.0; SIMP = 3.0


def dp(pts, eps):
    """Douglas–Peucker"""
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]; dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1e-9
    best, bi = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = abs((pts[i][0] - a[0]) * dy - (pts[i][1] - a[1]) * dx) / L
        if d > best: best, bi = d, i
    if best <= eps: return [a, b]
    return dp(pts[:bi + 1], eps)[:-1] + dp(pts[bi:], eps)


def segments_of(sh, frag):
    segs = []
    for d in sh.D:
        lay = d["layer"] or ""
        if frag.upper() not in lay.upper(): continue
        if d.get("fill") and d["polys"] and all(len(pl) <= 5 for pl in d["polys"]): continue        # conductor-count hash marks (small filled slivers)
        for pl in d["polys"]:
            w = [sh.T(x, y) for x, y in pl]
            for a, b in zip(w, w[1:]):
                if math.hypot(a[0] - b[0], a[1] - b[1]) > 0.05: segs.append((a, b))
    return segs


def chains_of(segs):
    """join segments into chains: shared ends within TOL are one node; DASHES are bridged only between FREE ends (degree 1) that are within GAP and collinear with their segments.
    Every chain is returned as a list of simplified polylines (a daisy chain with a fork gives one polyline per branch)."""
    nid = {}; pos = {}
    def node(p):
        key = (round(p[0] / TOL), round(p[1] / TOL))
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                k2 = (key[0] + dx, key[1] + dy)
                if k2 in nid: return nid[k2]
        n = len(nid); nid[key] = n; pos[n] = p; return n
    adj = collections.defaultdict(set); owner = {}
    for i, (a, b) in enumerate(segs):
        na, nb = node(a), node(b)
        if na != nb: adj[na].add(nb); adj[nb].add(na); owner.setdefault(na, i); owner.setdefault(nb, i)
    free = [n for n, v in adj.items() if len(v) == 1]
    grid = collections.defaultdict(list)
    for n in free: grid[(int(pos[n][0] // GAP), int(pos[n][1] // GAP))].append(n)
    def dir_of(n):
        m = next(iter(adj[n])); return (pos[n][0] - pos[m][0], pos[n][1] - pos[m][1])           # pointing OUT of the segment
    for n in free:
        gx, gy = int(pos[n][0] // GAP), int(pos[n][1] // GAP); a = dir_of(n); na_ = math.hypot(*a)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for m in grid.get((gx + dx, gy + dy), ()):
                    if m <= n or m in adj[n]: continue
                    gv = (pos[m][0] - pos[n][0], pos[m][1] - pos[n][1]); ng = math.hypot(*gv)
                    if ng > GAP or na_ == 0: continue
                    b = dir_of(m); nb_ = math.hypot(*b)
                    if nb_ == 0: continue
                    # both segments point at each other along the gap vector
                    if ng == 0 or (gv[0] * a[0] + gv[1] * a[1]) / (ng * na_) > 0.93 and (-gv[0] * b[0] - gv[1] * b[1]) / (ng * nb_) > 0.93:
                        adj[n].add(m); adj[m].add(n)
    seen = set(); paths = []
    def walk(start, nxt):
        path = [start, nxt]; seen.add(frozenset((start, nxt)))
        prev, cur = start, nxt
        while len(adj[cur]) == 2:
            n2 = [x for x in adj[cur] if x != prev][0]
            if frozenset((cur, n2)) in seen: break
            seen.add(frozenset((cur, n2))); path.append(n2); prev, cur = cur, n2
        return path
    for n in list(adj):
        if len(adj[n]) != 2:
            for m in list(adj[n]):
                if frozenset((n, m)) not in seen: paths.append(walk(n, m))
    for n in list(adj):                                                      # pure loops
        for m in list(adj[n]):
            if frozenset((n, m)) not in seen: paths.append(walk(n, m))
    # components over the final graph
    par = {}
    def f(x):
        par.setdefault(x, x)
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for n, v in adj.items():
        for m in v: par[f(n)] = f(m)
    comp = collections.defaultdict(list)
    for pth in paths:
        pl = dp([pos[n] for n in pth], SIMP)
        pl = [[round(x, 1), round(y, 1)] for x, y in pl]
        if len(pl) >= 2 and sum(math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in zip(pl, pl[1:])) > 2.0: comp[f(pth[0])].append(pl)
    return list(comp.values())


def run():
    ref = lib.Sheet("ARCH1", 7)
    res = {}
    for fam, (pdf, pages, frag, tlayer) in SHEETS.items():
        for sk, page in pages.items():
            sh = lib.Sheet(pdf, page, ref=ref)
            if sh.reg is None: print("skip (no registration)", fam, sk, page); continue
            segs = segments_of(sh, frag)
            chains = chains_of(segs)
            words = sh.words()
            # circuit tags / destinations: «R1/DB-F1» whole, or the «DB-F1» half of a tag split in two words, on the text layer of the sheet
            tags = [{"t": re.sub(r"\s+", "", w["s"]), "x": round(w["X"], 1), "y": round(w["Y"], 1)} for w in words if (tlayer.upper() in (w["layer"] or "").upper()) and (TAG.match(w["s"].strip()) or BOARD.match(w["s"].strip()))]
            # board symbols: their label is on the plain device layer (E.POWER / E.LIGHT), not on the text layer
            boards = [{"n": w["s"].strip(), "x": round(w["X"], 1), "y": round(w["Y"], 1)} for w in words if BOARD.match(w["s"].strip()) and (w["layer"] or "").upper().strip() in ("E.POWER", "E.LIGHT", "POWER")]
            res[f"{fam}|{sk}"] = {"sheet": f"{pdf} p{page}", "chains": chains, "tags": tags, "boards": boards}
            print(fam, sk, f"{pdf} p{page}", "segments", len(segs), "chains", len(chains), "polylines", sum(len(c) for c in chains), "tags", len(tags), "boards", len(boards))
    json.dump(res, open(OUT, "w"), separators=(",", ":"), ensure_ascii=False)
    print("saved", OUT, round(os.path.getsize(OUT) / 1e3), "kB")


if __name__ == "__main__":
    run()
