import sys, math, json, collections, re
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import lib, geo
OUT="/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work/data/struct.json"

# ---- levels (meters, relative to road datum +-0.00) from section A-A (A300) and slab layouts (S-101..S-141)
SLAB = {  # id: (top, thickness)
 "G":(-0.10,0.35), "1":(5.65,0.28), "2":(9.15,0.28), "3":(12.65,0.28), "4":(16.15,0.28), "5":(19.65,0.28), "R":(23.15,0.28), "T":(26.65,0.25)}
FFL = {"B":-3.70,"G":0.35,"1":5.75,"2":9.25,"3":12.75,"4":16.25,"5":19.75,"R":23.35,"T":26.85}
RAFT_TOP=-3.90
def soffit(l): return SLAB[l][0]-SLAB[l][1]
# vertical extents of column/wall layouts
COLSPAN = {
 "B":(RAFT_TOP, soffit("G")),
 "G":(SLAB["G"][0], soffit("1")),
 "1":(SLAB["1"][0], soffit("2")),
 "2":(SLAB["2"][0], soffit("3")),
 "3":(SLAB["3"][0], soffit("4")),
 "4":(SLAB["4"][0], soffit("5")),
 "5":(SLAB["5"][0], soffit("R")),
 "R":(SLAB["R"][0], soffit("T")),
 "T":(SLAB["T"][0], 27.25),
}
PAGE_OF = {"B":15,"G":16,"1":17,"2":17,"3":17,"4":17,"5":17,"R":18,"T":19}
LBL=re.compile(r'^(C\d+|W\d+\*?|CORE|S?W\d+)$')

def extract_solids(page):
    sh=lib.Sheet("STR",page)
    closed=[];opened=[];seen=set()
    for pl,d in sh.polys("S-COLUMN"):
        b=geo.bbox(pl)
        if b[0]<-120 or b[2]>4600 or b[1]<-120 or b[3]>4600: continue
        if geo.is_closed(pl):
            pc=geo.simplify_closed(pl)
            if len(pc)<3: continue
            k=geo.key_poly(pc,1.5)
            if k in seen: continue
            seen.add(k); closed.append(pc)
        elif len(pl)>=2: opened.append(pl)
    # ring detection: closed polygon that contains another closed polygon with uniform offset <=45
    closed.sort(key=lambda p:-abs(geo.area(p)))
    rings=[];used=set()
    for i,A in enumerate(closed):
        if i in used: continue
        for j,B in enumerate(closed):
            if j<=i or j in used: continue
            ba=geo.bbox(A); bb=geo.bbox(B)
            if not(ba[0]<=bb[0]+1 and ba[1]<=bb[1]+1 and ba[2]>=bb[2]-1 and ba[3]>=bb[3]-1): continue
            if abs(geo.area(A))<5e5: continue
            # all vertices of B within 45cm of A boundary
            ds=[geo.dist_pt_polyline(p,A+[A[0]]) for p in B]
            if max(ds)<=48 and min(ds)>=8:
                rings.append((A,B)); used.add(i); used.add(j); break
    solids=[p for k,p in enumerate(closed) if k not in used]
    pairs,unp=geo.pair_open_polylines(opened,dmin=8,dmax=48)
    labels=[w for w in sh.words() if LBL.match(w["s"])]
    return sh,solids,rings,pairs,unp,labels

def classify(poly):
    b=geo.bbox(poly); w=b[2]-b[0]; h=b[3]-b[1]
    a=abs(geo.area(poly))
    short=min(w,h); long_=max(w,h)
    if a<1e4*1.0 and long_<=200: return "column" if short>=15 else "column"
    if len(poly)>6: return "core"
    if long_/max(short,1)>=3.5 and long_>=150: return "wall"
    return "column"

def nearest_label(poly,labels,rmax=220):
    c=((geo.bbox(poly)[0]+geo.bbox(poly)[2])/2,(geo.bbox(poly)[1]+geo.bbox(poly)[3])/2)
    best=None
    for w in labels:
        d=math.hypot(w["X"]-c[0],w["Y"]-c[1])
        if d<rmax and (best is None or d<best[0]): best=(d,w["s"])
    return best[1] if best else None

def run():
    out={"levels":{"slab":SLAB,"ffl":FFL,"raft_top":RAFT_TOP,"colspan":COLSPAN},"cols":[],"walls":[],"rings":[]}
    done_pages={}
    for lvl,page in PAGE_OF.items():
        if page not in done_pages:
            done_pages[page]=extract_solids(page)
        sh,solids,rings,pairs,unp,labels=done_pages[page]
        z0,z1=COLSPAN[lvl]
        for p in solids:
            kind=classify(p)
            out["cols"].append({"lvl":lvl,"poly":[[round(x,1),round(y,1)] for x,y in p],"kind":kind,"mark":nearest_label(p,labels),"z0":round(z0,3),"z1":round(z1,3),"src":f"STR p{page} S-COLUMN"})
        for A,B in rings:
            out["rings"].append({"lvl":lvl,"outer":[[round(x,1),round(y,1)] for x,y in A],"inner":[[round(x,1),round(y,1)] for x,y in B],"z0":round(z0,3),"z1":round(z1,3),"src":f"STR p{page} S-COLUMN"})
        for p in pairs:
            out["walls"].append({"lvl":lvl,"poly":[[round(x,1),round(y,1)] for x,y in p],"z0":round(z0,3),"z1":round(z1,3),"src":f"STR p{page} S-COLUMN (paired faces)"})
        if lvl=="B" or lvl=="G":
            for u in unp: out.setdefault("unpaired",[]).append({"lvl":lvl,"pl":[[round(x,1),round(y,1)] for x,y in u]})
    # fix: typical page 17 content repeated for levels 1..5 (done above via PAGE_OF)
    json.dump(out,open(OUT,"w"))
    return out

if __name__=="__main__":
    o=run()
    print({k:len(v) if isinstance(v,list) else '...' for k,v in o.items()})
    c=collections.Counter((x["lvl"],x["kind"]) for x in o["cols"])
    print(sorted(c.items()))
    print("rings",len(o["rings"]),"walls(pairs)",len(o["walls"]),"unpaired",len(o.get("unpaired",[])))
