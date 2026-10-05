import sys, math, json, collections, re
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import numpy as np
import lib, geo, cellgrid
from build_struct import SLAB, FFL, RAFT_TOP, COLSPAN
OUT="/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work/data/struct2.json"

PAGE_SLAB={"G":20,"1":21,"2":22,"3":22,"4":22,"5":22,"R":23,"T":24}

def seg_pairs(segs, dmin=14, dmax=170, ang_tol=1.5, ov_min=0.55):
    """pair parallel line segments -> oriented rectangles (cx,cy,len,width,angle_deg)"""
    S=[]
    for s in segs:
        L=math.hypot(s[2]-s[0],s[3]-s[1])
        if L<40: continue
        a=math.degrees(math.atan2(s[3]-s[1],s[2]-s[0]))%180
        S.append((s,L,a))
    used=set(); rects=[]
    for i in range(len(S)):
        if i in used: continue
        si,Li,ai=S[i]
        best=None
        ux=math.cos(math.radians(ai)); uy=math.sin(math.radians(ai)); nx_,ny_=-uy,ux
        for j in range(len(S)):
            if j==i or j in used: continue
            sj,Lj,aj=S[j]
            da=min(abs(ai-aj),180-abs(ai-aj))
            if da>ang_tol: continue
            # perpendicular distance between lines
            mj=((sj[0]+sj[2])/2,(sj[1]+sj[3])/2); mi=((si[0]+si[2])/2,(si[1]+si[3])/2)
            d=(mj[0]-mi[0])*nx_+(mj[1]-mi[1])*ny_
            if not(dmin<=abs(d)<=dmax): continue
            # overlap along u
            ti=sorted([(si[0]*ux+si[1]*uy),(si[2]*ux+si[3]*uy)]); tj=sorted([(sj[0]*ux+sj[1]*uy),(sj[2]*ux+sj[3]*uy)])
            ov=min(ti[1],tj[1])-max(ti[0],tj[0])
            if ov<ov_min*min(Li,Lj): continue
            sc=abs(abs(d))+ (1-ov/min(Li,Lj))*100
            if best is None or sc<best[0]: best=(sc,j,d,max(ti[0],tj[0]),min(ti[1],tj[1]))
        if best:
            sc,j,d,t0,t1=best; used.add(i); used.add(j)
            # rectangle corners
            mi=((si[0]+si[2])/2,(si[1]+si[3])/2)
            base=(mi[0]*ux+mi[1]*uy, mi[0]*nx_+mi[1]*ny_)  # (t,n) of line i
            n0=base[1]; n1=base[1]+d
            pts=[(t0*ux+n0*nx_, t0*uy+n0*ny_),(t1*ux+n0*nx_, t1*uy+n0*ny_),(t1*ux+n1*nx_, t1*uy+n1*ny_),(t0*ux+n1*nx_, t0*uy+n1*ny_)]
            rects.append({"poly":pts,"w":abs(d),"len":t1-t0,"ang":ai})
    return rects

def beams_of(page):
    sh=lib.Sheet("STR",page)
    segs=[]
    for pl,d in sh.polys("BEAM"):
        if geo.is_closed(pl): continue
        b=geo.bbox(pl)
        if b[0]<-120 or b[2]>4600 or b[1]<-120 or b[3]>4600: continue
        for a,b2 in zip(pl[:-1],pl[1:]): segs.append((a[0],a[1],b2[0],b2[1]))
    labels=[w for w in sh.words() if re.match(r'^B\d\*?$',w["s"])]
    rects=seg_pairs(segs)
    out=[]
    for r in rects:
        c=(sum(p[0] for p in r["poly"])/4,sum(p[1] for p in r["poly"])/4)
        best=None
        for w in labels:
            dd=math.hypot(w["X"]-c[0],w["Y"]-c[1])
            if dd<300 and (best is None or dd<best[0]): best=(dd,w["s"])
        r["mark"]=best[1] if best else None
        out.append(r)
    return sh,out

# beam depth tables (cm) by level group & width (from SCHEDULE OF BEAMS on each slab layout)
def beam_depth(lvl,w,mark):
    if lvl=="G":
        if w>=140: return 70
        if w>=70: return 32
        return 113 if mark=="B2" else 70
    if lvl=="1":
        if w>=170: return 50
        if w>=120: return 100
        return 80
    if lvl in ("2","3","4","5","R"):
        if w>=100: return 45
        return 80
    return 60

# slab outer outlines + openings (cm) -------------------------------------------------
TOWER=(95,-80,3195,1870)
LIFTS=[(1535,1020,1735,1220),(1755,1020,1955,1220)]
STAIR1=(95,760,655,1040)
STAIR2=(1535,520,2075,780)
def rect(b): return [(b[0],b[1]),(b[2],b[1]),(b[2],b[3]),(b[0],b[3])]

def shaft_rects(page):
    sh=lib.Sheet("STR",page)
    items=[]
    for pl,d in sh.polys("SHAFT"):
        b=geo.bbox(pl)
        if b[0]<-120 or b[2]>4600 or b[1]<-120 or b[3]>4600: continue
        items.append(b)
    # cluster
    par=list(range(len(items)))
    def find(a):
        while par[a]!=a: par[a]=par[par[a]]; a=par[a]
        return a
    for i in range(len(items)):
        for j in range(i+1,len(items)):
            a=items[i]; b=items[j]
            if a[0]-8<=b[2] and b[0]-8<=a[2] and a[1]-8<=b[3] and b[1]-8<=a[3]: par[find(i)]=find(j)
    g=collections.defaultdict(list)
    for i in range(len(items)): g[find(i)].append(i)
    out=[]
    for ids in g.values():
        x0=min(items[i][0] for i in ids); y0=min(items[i][1] for i in ids); x1=max(items[i][2] for i in ids); y1=max(items[i][3] for i in ids)
        if (x1-x0)>=18 and (y1-y0)>=18 and (x1-x0)*(y1-y0)>=2800: out.append((x0,y0,x1,y1))
    return sorted(out)

def ramp_polygon():
    """ramp channel (opening in ground slab): strip y 3810..4410 x 1550..2920 + annulus quadrant R400..R1000/1025 about (2920,3410)"""
    cx,cy=2920,3410
    pts=[(1550,4410),(1550,3810),(2920,3810)]
    # inner arc R=400 from 90deg to 0deg
    for k in range(0,13):
        a=math.radians(90-90*k/12); pts.append((cx+400*math.cos(a),cy+400*math.sin(a)))
    # to outer arc start (R=1000 at 0deg) then arc to 90deg
    for k in range(0,25):
        a=math.radians(0+90*k/24); pts.append((cx+1000*math.cos(a),cy+1000*math.sin(a)))
    pts.append((2920,4410))
    return [(round(x,1),round(y,1)) for x,y in pts]

def run():
    out={"slabs":[],"beams":[],"openings":{}, "ramp_poly":ramp_polygon()}
    # slabs
    outer_G=[(-30,-30),(4440,-30),(4440,4440),(-30,4440)]
    sG=shaft_rects(20)
    holesG=[rect(LIFTS[0]),rect(LIFTS[1]),rect(STAIR1),rect((3990,1180,4300,1620))]+[rect(r) for r in sG]
    out["slabs"].append({"lvl":"G","outer":outer_G,"holes":holesG+[out["ramp_poly"]],"top":SLAB["G"][0],"t":SLAB["G"][1]})
    s1=shaft_rects(21)
    typ_holes=[rect(LIFTS[0]),rect(LIFTS[1]),rect(STAIR1),rect(STAIR2)]
    out["slabs"].append({"lvl":"1","outer":rect(TOWER),"holes":typ_holes+[rect(r) for r in s1],"top":SLAB["1"][0],"t":SLAB["1"][1]})
    st=shaft_rects(22)
    for l in ("2","3","4","5"):
        out["slabs"].append({"lvl":l,"outer":rect(TOWER),"holes":typ_holes+[rect(r) for r in st],"top":SLAB[l][0],"t":SLAB[l][1]})
    sr=shaft_rects(23)
    out["slabs"].append({"lvl":"R","outer":rect(TOWER),"holes":typ_holes+[rect(r) for r in sr],"top":SLAB["R"][0],"t":SLAB["R"][1]})
    # top roof slab (plant rooms + stair-1 head house): from beam loops on STR p24 (S-141)
    out["slabs"].append({"lvl":"T","rects":[[95,760,675,1040],[655,460,2645,800],[1975,800,2645,1340]],"top":SLAB["T"][0],"t":SLAB["T"][1],"holes":[rect(r) for r in shaft_rects(24)]})
    # beams
    for lvl,page in (("G",20),("1",21),("2",22),("R",23),("T",24)):
        sh,bs=beams_of(page)
        for r in bs:
            r["depth"]=beam_depth(lvl,r["w"],r["mark"])
            out["beams"].append({"lvl":lvl,"poly":[[round(x,1),round(y,1)] for x,y in r["poly"]],"w":round(r["w"],1),"depth":r["depth"],"mark":r["mark"],"len":round(r["len"],1),"page":page})
    json.dump(out,open(OUT,"w"))
    return out

if __name__=="__main__":
    o=run()
    print({k:len(v) if isinstance(v,(list,dict)) else v for k,v in o.items()})
    c=collections.Counter((b["lvl"],round(b["w"]),b["mark"]) for b in o["beams"])
    print(sorted(c.items()))
    for s in o["slabs"]: print(s["lvl"],"holes",len(s["holes"]),"rects",len(s.get("rects",[])))
