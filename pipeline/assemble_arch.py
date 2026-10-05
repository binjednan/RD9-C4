import sys, json, math, collections, re
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import geo, kb, finishes as FN
from floormap import FloorMap, FLAT_INFO
import arch_floor as AF
D="/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work/data/"
from build_struct import SLAB, FFL, COLSPAN

TOWER_LV={"1":dict(pn=6,hvac=3),"2":dict(pn=7,hvac=4),"3":dict(pn=7,hvac=4),"4":dict(pn=7,hvac=4),"5":dict(pn=7,hvac=4)}
CEIL_H=2.70   # false-ceiling height above FFL (assumed; not stated in documents)
_FM={}
def fmap(pn,hvac):
    k=(pn,hvac)
    if k not in _FM: _FM[k]=FloorMap(pn,hvac_page=hvac)
    return _FM[k]

def R(x0,y0,x1,y1,z0,z1): return ["r",round(x0,1),round(y0,1),round(x1,1),round(y1,1),round(z0,3),round(z1,3)]

def poly_overlap_frac(rect, polys, step=6):
    x0,y0,x1,y1=rect
    nx=max(1,int((x1-x0)/step)); ny=max(1,int((y1-y0)/step))
    tot=0; hit=0
    for i in range(nx):
        for j in range(ny):
            p=(x0+(i+0.5)*(x1-x0)/nx, y0+(j+0.5)*(y1-y0)/ny)
            tot+=1
            for pl in polys:
                b=pl["bb"]
                if b[0]<=p[0]<=b[2] and b[1]<=p[1]<=b[3] and geo.pt_in_poly(p,pl["pts"]):
                    hit+=1; break
    return hit/max(tot,1)

def struct_polys(lvl):
    st=json.load(open(D+"struct.json"))
    out=[]
    for c in st["cols"]:
        if c["lvl"]==lvl: out.append({"pts":c["poly"],"bb":geo.bbox(c["poly"])})
    for w in st["walls"]:
        if w["lvl"]==lvl: out.append({"pts":w["poly"],"bb":geo.bbox(w["poly"])})
    for rg in st["rings"]:
        if rg["lvl"]==lvl:
            pass
    return out

def side_kinds(fm,x,y,o,t):
    """room kinds on both sides of a wall rect centre"""
    off=t/2+10
    if o=="h": pts=[(x,y+off),(x,y-off)]
    else: pts=[(x+off,y),(x-off,y)]
    res=[]
    for p in pts:
        c=fm.comp_at(*p)
        rm=fm.comp_room.get(c)
        kind=rm["kind"] if rm else None
        res.append((c,kind,fm.flat_of_comp.get(c)))
    return res

def room_finish(rm, in_flat):
    if rm is None: return (None,None,None)
    k=rm["kind"]
    if k=="lobby" and in_flat: return ("F4","W2","C1")
    if k is None: return ("F4","W2","C1") if in_flat else ("F16","W7","C1")
    return FN.BY_KIND.get(k,(None,None,None))

def build_tower_level(els, add, lvl):
    P=TOWER_LV[lvl]; fm=fmap(P["pn"],P["hvac"])
    ffl=FFL[lvl]; ztop={"1":SLAB["2"][0]-SLAB["2"][1],"2":SLAB["3"][0]-SLAB["3"][1],"3":SLAB["4"][0]-SLAB["4"][1],"4":SLAB["5"][0]-SLAB["5"][1],"5":SLAB["R"][0]-SLAB["R"][1]}[lvl]
    sp=struct_polys(lvl)
    rects=fm.wall_rects()
    nwall=0
    for (x0,y0,x1,y1) in rects:
        w=x1-x0; h=y1-y0; t=min(w,h)
        if t<4: continue
        if poly_overlap_frac((x0,y0,x1,y1),sp)>0.6: continue
        o="h" if w>=h else "v"
        cx=(x0+x1)/2; cy=(y0+y1)/2
        sk=side_kinds(fm,cx,cy,o,t)
        fins=[]
        for c,kind,fl in sk:
            rm=fm.comp_room.get(c)
            f=room_finish(rm, fl is not None)
            if f[1] and f[1] not in fins: fins.append(f[1])
        flats=[fl for c,kind,fl in sk if fl]
        u=flats[0] if flats else None; u2=flats[1] if len(flats)>1 and flats[1]!=flats[0] else None
        ext = (x0<130 or x1>3160 or y0<-20 or y1>1830)
        tcls="blk100" if t<=12 else ("blk200" if t<=22 else "blk_t")
        add("A.wall",lvl,R(x0,y0,x1,y1,ffl,ztop),typ="wall_"+tcls,mat="block_ext" if ext else "block",attrs={"thk_cm":round(t),"fin":fins},u=u,u2=u2,src=[f"ARCH1 p{P['pn']} layer A-WALL (مضلعات الجدران)"],flat_no=u)
        nwall+=1
    # doors
    for d in fm.r["doors"]:
        tag=d["tag"]; spec=kb.DOORS.get(tag)
        if not spec: continue
        cx,cy,wd,t,o=d["cx"],d["cy"],d["w"],d["t"],d["o"]
        dh=spec["h"]/100.0
        flats=fm.flat_at(cx,cy,search=True) if tag in("D2","D3","D4") else fm.flat_at(cx,cy,search=True)
        u=flats[0] if flats else None; u2=flats[1] if len(flats)>1 else None
        if tag=="D1":
            # entrance: belongs to the flat on the room side; choose by side comps
            sk=side_kinds(fm,cx,cy,o,t)
            fl=[x[2] for x in sk if x[2]]
            u=fl[0] if fl else u; u2=None
        # lintel above door (wall piece)
        if o=="h": lint=R(d["x0"],d["y0"],d["x1"],d["y1"],ffl+dh,ztop)
        else: lint=R(d["x0"],d["y0"],d["x1"],d["y1"],ffl+dh,ztop)
        add("A.wall",lvl,lint,typ="wall_lintel",mat="block",attrs={"thk_cm":round(t),"fin":[]},u=u,u2=u2,src=[f"ARCH1 p{P['pn']} — بلاطة فوق الباب {tag}"])
        # leaf (closed) + frame
        leaf_t=4
        if o=="h":
            leaf=R(cx-wd/2+2,cy-leaf_t/2,cx+wd/2-2,cy+leaf_t/2,ffl+0.02,ffl+dh-0.03)
        else:
            leaf=R(cx-leaf_t/2,cy-wd/2+2,cx+leaf_t/2,cy+wd/2-2,ffl+0.02,ffl+dh-0.03)
        mat={"D6":"door_steel","D8":"door_steel","D10":"door_steel","D11":"door_steel","D12":"door_steel","D13":"door_steel","D14":"door_steel","D15":"door_steel","D9":"door_alu"}.get(tag,"door_wood")
        add("A.door",lvl,leaf,mark=tag,typ="door_"+tag,mat=mat,attrs={"w_cm":round(wd),"h_cm":round(dh*100),"wall_cm":round(t)},u=u,u2=u2,src=[f"ARCH1 p{P['pn']} — وسم الباب {tag} + فتحة الجدار (قياس مباشر {round(wd)} سم)",kb.DOORS[tag]["sheet"]])
    return nwall

def build_floor_finishes(els, add, lvl):
    if lvl in TOWER_LV:
        P=TOWER_LV[lvl]; pn=P["pn"]; hv=P["hvac"]; ffl=FFL[lvl]
    else:
        P=LEVEL_CFG[lvl]; pn=P["pn"]; hv=P["hvac"]; ffl=P["ffl"]
    fm=fmap(pn,hv)
    n=0
    for rm in fm.rooms:
        c=rm["comp"]; in_flat=c in fm.flat_of_comp
        f,wc,cc=room_finish(rm,in_flat)
        if lvl=="B" and rm["kind"] is None: f=None; cc=None
        u=fm.flat_of_comp.get(c)
        g2=fm.g2
        m=(g2.lab==c)
        for (x0,y0,x1,y1) in g2.rects(m):
            if (x1-x0)<10 or (y1-y0)<10: continue
            if f:
                add("A.floor",lvl,R(x0,y0,x1,y1,ffl,ffl+0.012),mark=f,typ="floor_"+f,mat="fin_"+f,attrs={"room":rm["names"][:3],"kind":rm["kind"],"fin":[f]},u=u,src=[f"ARCH1 p{pn} غرفة + A500"])
                n+=1
            if cc in ("C1","C3","C4","C9") and lvl!="B":
                add("A.ceil",lvl,R(x0,y0,x1,y1,ffl+CEIL_H,ffl+CEIL_H+0.02),mark=cc,typ="ceil_"+cc,mat="fin_"+cc,attrs={"room":rm["names"][:3],"kind":rm["kind"],"fin":[cc],"assumed_h":CEIL_H},u=u,src=[f"ARCH1 p{pn} غرفة + A500 (الارتفاع {CEIL_H} م افتراضي)"])
    return n

# ---------------- facade (curtain wall, pilasters, slab-edge bands) ----------------
import lib
FACE={"S":{"o":"h","y0":-91,"y1":-61},"N":{"o":"h","y0":1850,"y1":1880},"W":{"o":"v","x0":84,"x1":114},"E":{"o":"v","x0":3175,"x1":3205}}
def win_tags(pn):
    sh=lib.Sheet("ARCH1",pn)
    out=[]
    for w in sh.words(layer="A-WINDOW -IDEN"):
        if re.match(r'^(CW|W)-\d+$',w["s"]): out.append(w)
    return out
def side_of(x,y):
    if y<-100: return "S"
    if y>1900: return "N"
    if x<60: return "W"
    if x>3230: return "E"
    return None   # interior (e.g. W-04 kitchen window)

def build_facade_level(els, add, lvl, pn):
    ffl=FFL[lvl]
    ztop={"1":SLAB["2"][0]-SLAB["2"][1],"2":SLAB["3"][0]-SLAB["3"][1],"3":SLAB["4"][0]-SLAB["4"][1],"4":SLAB["5"][0]-SLAB["5"][1],"5":SLAB["R"][0]-SLAB["R"][1]}[lvl]
    fm=fmap(TOWER_LV[lvl]["pn"],TOWER_LV[lvl]["hvac"])
    tags=win_tags(pn)
    units=collections.defaultdict(list)
    for t in tags:
        s=side_of(t["X"],t["Y"])
        if not s: continue
        spec=kb.WINS.get(t["s"])
        if not spec: continue
        W_,H_,loc,qty=spec
        c=t["Y"] if s in("W","E") else t["X"]
        units[s].append((c-W_/2,c+W_/2,t["s"],W_,H_,loc))
    nwin=0
    for s,lst in units.items():
        lst.sort()
        F=FACE[s]
        for (a,b,tag,W_,H_,loc) in lst:
            H=min(H_/100.0, ztop-ffl)
            u=None
            mid=(a+b)/2
            if s in("S","N"):
                pt=(mid, (F["y0"]+F["y1"])/2 + (60 if s=="S" else -60))
            else:
                pt=((F["x0"]+F["x1"])/2 + (60 if s=="W" else -60), mid)
            fl=fm.flat_at(*pt)
            u=fl[0] if fl else None
            grp=f"WIN-{lvl}-{s}-{round(mid)}"
            # vision glass (F) from FFL to FFL+H ; spandrel (S) above up to soffit
            if s in("S","N"):
                gy0=(F["y0"]+F["y1"])/2-1.5; gy1=gy0+3
                vis=R(a,gy0,b,gy1,ffl+0.05,ffl+H); span=R(a,gy0,b,gy1,ffl+H,ztop)
                fr=[R(a,F["y0"]+5,a+5,F["y1"]-5,ffl,ztop),R(b-5,F["y0"]+5,b,F["y1"]-5,ffl,ztop),R(a,F["y0"]+8,b,F["y1"]-8,ffl,ffl+0.05)]
            else:
                gx0=(F["x0"]+F["x1"])/2-1.5; gx1=gx0+3
                vis=R(gx0,a,gx1,b,ffl+0.05,ffl+H); span=R(gx0,a,gx1,b,ffl+H,ztop)
                fr=[R(F["x0"]+5,a,F["x1"]-5,a+5,ffl,ztop),R(F["x0"]+5,b-5,F["x1"]-5,b,ffl,ztop),R(F["x0"]+8,a,F["x1"]-8,b,ffl,ffl+0.05)]
            at={"w_cm":round(W_),"h_cm":round(H_),"loc":loc,"side":s}
            src=[f"ARCH1 p{pn} وسم {tag} (A-WINDOW -IDEN) + مقاس BOQ 8.4.1","A800–A802 (جدول الزجاج)"]
            add("A.win",lvl,vis,mark=tag,typ="win_"+tag,mat="glass_vis",attrs=at,u=u,src=src,grp=grp)
            add("A.win",lvl,span,mark=tag,typ="win_"+tag,mat="glass_span",attrs=dict(at,part="spandrel"),u=u,src=src,grp=grp)
            for k,f in enumerate(fr):
                add("A.win",lvl,f,mark=tag,typ="win_"+tag,mat="frame_alu",attrs=dict(at,part="frame"),u=u,src=src,grp=grp)
            nwin+=1
    # pilasters between units + slab-edge band
    ext={"S":(84,3205),"N":(84,3205),"W":(-91,1880),"E":(-91,1880)}
    for s,lst in units.items():
        lst=sorted(lst); F=FACE[s]; lo,hi=ext[s]; cur=lo
        gaps=[]
        for (a,b,tag,W_,H_,loc) in lst:
            if a-cur>6: gaps.append((cur,a))
            cur=max(cur,b)
        if hi-cur>6: gaps.append((cur,hi))
        for (a,b) in gaps:
            if s in("S","N"): g=R(a,F["y0"],b,F["y1"],ffl,ztop)
            else: g=R(F["x0"],a,F["x1"],b,ffl,ztop)
            add("A.clad",lvl,g,mark="W12",typ="clad_porcelain",mat="clad_porc",attrs={"fin":["W12"],"side":s,"w_cm":round(b-a)},src=[f"ARCH1 p{pn} — فراغات بين وحدات الزجاج (أعمدة الواجهة المكسوة)","A200–A203 (بند 1: كسوة بورسلين 60×120)"])
    # slab edge band (below FFL)
    bz0=ffl-0.40; bz1=ffl
    add("A.clad",lvl,R(84,-91,3205,-61,bz0,bz1),mark="W12",typ="clad_edge",mat="clad_porc",attrs={"fin":["W12"],"side":"S"},src=["A1500 (مقطع الجدار): حافة البلاطة 40 سم كسوة بورسلين"])
    add("A.clad",lvl,R(84,1850,3205,1880,bz0,bz1),mark="W12",typ="clad_edge",mat="clad_porc",attrs={"fin":["W12"],"side":"N"},src=["A1500"])
    add("A.clad",lvl,R(84,-61,114,1850,bz0,bz1),mark="W12",typ="clad_edge",mat="clad_porc",attrs={"fin":["W12"],"side":"W"},src=["A1500"])
    add("A.clad",lvl,R(3175,-61,3205,1850,bz0,bz1),mark="W12",typ="clad_edge",mat="clad_porc",attrs={"fin":["W12"],"side":"E"},src=["A1500"])
    return nwin

# ---------------- generic level builder (G, R, T, B) ----------------
LEVEL_CFG={
 "G":dict(pn=5,hvac=2,ffl=0.35,ztop=SLAB["1"][0]-SLAB["1"][1],stlvl="G"),
 "R":dict(pn=8,hvac=6,ffl=23.35,ztop=SLAB["T"][0]-SLAB["T"][1],stlvl="R"),
 "T":dict(pn=9,hvac=None,ffl=26.85,ztop=27.25,stlvl="T"),
 "B":dict(pn=4,hvac=1,ffl=-3.70,ztop=SLAB["G"][0]-SLAB["G"][1],stlvl="B"),
}
def build_level_generic(els, add, lvl):
    C=LEVEL_CFG[lvl]; pn=C["pn"]; fm=fmap(pn,C["hvac"]) if lvl!="T" else None
    if fm is None: return 0
    ffl=C["ffl"]; ztop=C["ztop"]
    sp=struct_polys(C["stlvl"])
    rects=fm.wall_rects(); n=0
    for (x0,y0,x1,y1) in rects:
        w=x1-x0; h=y1-y0; t=min(w,h)
        if t<4: continue
        o="h" if w>=h else "v"
        boundary=(lvl in("G","B")) and (x0<-60 or x1>4480 or y0<-60 or y1>4480)
        if lvl=="B" and (x0<5 and x1<... if False else False): pass
        if not boundary and poly_overlap_frac((x0,y0,x1,y1),sp)>0.6: continue
        if boundary:
            if lvl=="B": continue
            add("A.site",lvl,R(x0,y0,x1,y1,SLAB["G"][0],3.0),typ="wall_boundary",mat="block_ext",attrs={"thk_cm":round(t),"fin":["W11"]},src=[f"ARCH1 p{pn} A-WALL — سور الموقع (T.O.B +3.00)"]); n+=1; continue
        cx=(x0+x1)/2; cy=(y0+y1)/2
        sk=side_kinds(fm,cx,cy,o,t)
        fins=[]
        for c,kind,fl in sk:
            rm=fm.comp_room.get(c); f=room_finish(rm, False)
            if f[1] and f[1] not in fins: fins.append(f[1])
        ext=(x0<130 or x1>3160 or y0<-20 or y1>1830)
        tcls="blk100" if t<=12 else ("blk200" if t<=22 else "blk_t")
        add("A.wall",lvl,R(x0,y0,x1,y1,ffl,ztop),typ="wall_"+tcls,mat="block_ext" if ext else "block",attrs={"thk_cm":round(t),"fin":fins},src=[f"ARCH1 p{pn} layer A-WALL"]); n+=1
    for d in fm.r["doors"]:
        tag=d["tag"]; spec=kb.DOORS.get(tag)
        if not spec: continue
        cx,cy,wd,t,o=d["cx"],d["cy"],d["w"],d["t"],d["o"]; dh=spec["h"]/100.0
        add("A.wall",lvl,R(d["x0"],d["y0"],d["x1"],d["y1"],ffl+dh,ztop),typ="wall_lintel",mat="block",attrs={"thk_cm":round(t),"fin":[]},src=[f"ARCH1 p{pn} — بلاطة فوق الباب {tag}"])
        leaf_t=4
        leaf=R(cx-wd/2+2,cy-leaf_t/2,cx+wd/2-2,cy+leaf_t/2,ffl+0.02,ffl+dh-0.03) if o=="h" else R(cx-leaf_t/2,cy-wd/2+2,cx+leaf_t/2,cy+wd/2-2,ffl+0.02,ffl+dh-0.03)
        mat={"D6":"door_steel","D8":"door_steel","D10":"door_steel","D11":"door_steel","D12":"door_steel","D13":"door_steel","D14":"door_steel","D15":"door_steel","D9":"door_alu"}.get(tag,"door_wood")
        add("A.door",lvl,leaf,mark=tag,typ="door_"+tag,mat=mat,attrs={"w_cm":round(wd),"h_cm":round(dh*100),"wall_cm":round(t)},src=[f"ARCH1 p{pn} — وسم الباب {tag} + فتحة الجدار (قياس مباشر {round(wd)} سم)",kb.DOORS[tag]["sheet"]]); n+=1
    return n

# ---------------- stairs, lifts, parapets, ground storefront ----------------
LV_ORDER=["B","G","1","2","3","4","5","R","T"]
def stair_levels(first,last):
    i0=LV_ORDER.index(first); i1=LV_ORDER.index(last)
    return LV_ORDER[i0:i1+1]
def dogleg(add, name, well, x_flight, y_split, lvl_from, lvl_to, z0, z1, risers=10, grp=None, cat="S.stair", mat="conc", u=None):
    """dog-leg stair in a rectangular well: flights run along x; flight A lower half (y<y_split) from west->east, flight B upper half east->west.
       well=(x0,y0,x1,y1); x_flight=(xa,xb) tread run limits; rise split in two flights of `risers` steps"""
    x0,y0,x1,y1=well; xa,xb=x_flight
    h=z1-z0; rise=h/(2*risers)
    tread=(xb-xa)/risers
    gap=10
    ymid_lo=y_split-gap/2; ymid_hi=y_split+gap/2
    for k in range(risers):
        xs=xa+k*tread; xe=xs+tread
        zt=z0+(k+1)*rise
        add(cat,lvl_from,R(xs,y0,xe,ymid_lo,zt-rise-0.12,zt),mark=name,typ="stair_step",mat=mat,attrs={"flight":"A","step":k+1,"rise_cm":round(rise*100,1),"tread_cm":round(tread)},grp=grp,src=["A600/A602 + مخطط الدرج (طبقة stairs)"])
    # mid landing (east)
    zl=z0+risers*rise
    add(cat,lvl_from,R(xb,y0,x1,y1,zl-0.2,zl),mark=name,typ="stair_landing",mat=mat,attrs={"kind":"mid-landing"},grp=grp,src=["A600/A602"])
    for k in range(risers):
        xs=xb-(k+1)*tread; xe=xs+tread
        zt=zl+(k+1)*rise
        add(cat,lvl_from,R(xs,ymid_hi,xe,y1,zt-rise-0.12,zt),mark=name,typ="stair_step",mat=mat,attrs={"flight":"B","step":risers+k+1,"rise_cm":round(rise*100,1),"tread_cm":round(tread)},grp=grp,src=["A600/A602 + مخطط الدرج (طبقة stairs)"])

def build_stairs(add):
    # Stair 1 (west core): well (95,760)-(655,1040); treads x 235..535
    for lv in stair_levels("B","T"):
        i=LV_ORDER.index(lv)
        if lv=="T": continue
        nxt=LV_ORDER[i+1]
        z0=FFL[lv]+(0.0 if lv!="B" else 0.0); z1=FFL[nxt]
        # use slab-top datum to avoid z-fighting: start at FFL
        dogleg(add,"درج 1",(95,760,655,1040),(235,535),900,lv,nxt,z0,z1,grp=f"STAIR1-{lv}",u=None)
    # Stair 2 (centre): from G to R; well (1535,520)-(2075,780); treads x 1655..1955 ; flights along x
    for lv in stair_levels("G","R"):
        i=LV_ORDER.index(lv)
        if lv=="R": continue
        nxt=LV_ORDER[i+1]
        dogleg(add,"درج 2",(1535,520,2075,780),(1655,1955),650,lv,nxt,FFL[lv],FFL[nxt],grp=f"STAIR2-{lv}")

def build_lifts(add):
    cars=[("مصعد 1",(1535,1020,1735,1220),"G"),("مصعد 2",(1755,1020,1955,1220),"3")]
    for nm,(x0,y0,x1,y1),lv in cars:
        cx=(x0+x1)/2; cy=(y0+y1)/2
        z0=FFL[lv]+0.05
        add("A.fix",lv,R(cx-70,cy-80,cx+70,cy+80,z0,z0+2.20),mark=nm,typ="lift_car",mat="door_steel",attrs={"cab_cm":"140×160 (تقديري من فتحة البئر)","stops":"B,G,1–5,R"},src=["A900 (تفاصيل المصعد) + فتحة البئر من STR p15–19","BOQ 13.1.1: مصعدان"])

def build_parapets(add):
    z0=FFL["R"]; z1=25.25
    ring=[(84,-91,3205,-61),(84,1850,3205,1880),(84,-61,114,1850),(3175,-61,3205,1850)]
    for (a,b,c,d) in ring:
        add("A.rail","R",R(a,b,c,d,z0,z1),mark="PARAPET-R",typ="parapet_roof",mat="clad_porc",attrs={"h_m":round(z1-z0,2),"top":"+25.25"},src=["A300 (مقطع A-A): ROOF PARAPET +25.25","A1501 (مقطع الجدار 2)"])
    # top roof parapet: edges of top slab rects
    rects=[(95,760,675,1040),(655,460,2645,800),(1975,800,2645,1340)]
    z0=SLAB["T"][0]; z1=27.25
    def inside(px,py):
        for r in rects:
            if r[0]+1<px<r[2]-1 and r[1]+1<py<r[3]-1: return True
        return False
    for r in rects:
        for (a,b,c,d,mx,my) in [(r[0],r[1],r[2],r[1]+20,(r[0]+r[2])/2,r[1]-5),(r[0],r[3]-20,r[2],r[3],(r[0]+r[2])/2,r[3]+5),(r[0],r[1],r[0]+20,r[3],r[0]-5,(r[1]+r[3])/2),(r[2]-20,r[1],r[2],r[3],r[2]+5,(r[1]+r[3])/2)]:
            if inside(mx,my): continue
            add("A.rail","T",R(a,b,c,d,z0,z1),mark="PARAPET-T",typ="parapet_top",mat="clad_porc",attrs={"h_m":round(z1-z0,2),"top":"+27.25"},src=["A300: TOP PARAPET +27.25"])

def build_ground_front(add):
    z0=FFL["G"]; zg=3.35; zt=SLAB["1"][0]-SLAB["1"][1]
    runs=[("S",170,370,235),("S",570,1270,235),("S",1595,2195,235),("S",2395,2495,235),("W",338,638,105),("N",1425,1590,1630),("N",1790,1955,1630)]
    for k,(s,a,b,c) in enumerate(runs):
        grp=f"GFR-{k}"
        if s in("S","N"):
            vis=R(a,c-2,b,c+2,z0+0.05,zg); fas=R(a,c-12,b,c+12,zg,zt)
            fr=[R(a,c-6,a+5,c+6,z0,zg),R(b-5,c-6,b,c+6,z0,zg)]
        else:
            vis=R(c-2,a,c+2,b,z0+0.05,zg); fas=R(c-12,a,c+12,b,zg,zt)
            fr=[R(c-6,a,c+6,a+5,z0,zg),R(c-6,b-5,c+6,b,z0,zg)]
        add("A.win","G",vis,mark="CW-G",typ="win_CW-G",mat="glass_vis",attrs={"loc":"واجهة محلات الطابق الأرضي","h_cm":round((zg-z0)*100)},grp=grp,src=["ARCH1 p5 طبقة A-GALZ (خطوط الزجاج)","BOQ 8.4.1.1–8.4.1.6 (CW1–CW6)"])
        for f in fr: add("A.win","G",f,mark="CW-G",typ="win_CW-G",mat="frame_alu",attrs={"part":"frame"},grp=grp,src=["ARCH1 p5"])
        add("A.clad","G",fas,mark="W12",typ="clad_porcelain",mat="clad_porc",attrs={"fin":["W12"],"loc":"قاطع علوي فوق الواجهة الزجاجية"},src=["A200 (ارتفاع الطابق الأرضي 5.0 م)"])
