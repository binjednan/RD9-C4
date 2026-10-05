import fitz, collections, math, itertools

# Master grid (cm). X: Q..A left->right; Y: 1..11 bottom->top. Verified: total 4410 both ways.
GX = {"Q":0,"P":105,"O":495,"N":735,"M":845,"L":1095,"K":1365,"J":1525,"I":1745,"H":1965,"G":2085,"F":2635,"E":2815,"D":3185,"C":3505,"B":3935,"A":4410}
GY = {"1":0,"2":510,"3":790,"4":1010,"5":1230,"6":1810,"7":2335,"8":2695,"9":3195,"10":3810,"11":4410}
GX_list = sorted(GX.values()); GY_list = sorted(GY.values())

def grid_clusters(page, layers=("S-GRID","GRID","AXIS LINE"), minlen=150, drawings=None):
    dr = drawings if drawings is not None else page.get_drawings()
    V=collections.defaultdict(float); H=collections.defaultdict(float)
    for it in dr:
        ly=it.get("layer")
        if layers is not None and ly not in layers and not (ly and ly.endswith("S-GRID")) : continue
        for op in it["items"]:
            if op[0]!="l": continue
            a,b=op[1],op[2]
            L=((a.x-b.x)**2+(a.y-b.y)**2)**.5
            if abs(a.x-b.x)<0.2 and L>0.4: V[round(a.x*2)/2]+=L
            elif abs(a.y-b.y)<0.2 and L>0.4: H[round(a.y*2)/2]+=L
    vv=sorted(k for k,v in V.items() if v>minlen)
    hh=sorted(k for k,v in H.items() if v>minlen)
    # merge near duplicates (<1.5pt)
    def merge(a):
        out=[]
        for x in a:
            if out and x-out[-1]<1.5: continue
            out.append(x)
        return out
    return merge(vv), merge(hh)

def fit_axis(pts, master, s, flip=False, tol=4.0):
    """pts: pt coords of grid lines; master: sorted cm positions; s: cm per pt.
       returns (offset, nmatch, resid) such that world_cm = sign*(pt)*s + offset"""
    sign=-1.0 if flip else 1.0
    best=(None,-1,1e9)
    cm=[sign*p*s for p in pts]
    for c in cm:
        for m in master:
            off=m-c
            n=0; err=0.0
            for c2 in cm:
                w=c2+off
                d=min(abs(w-mm) for mm in master)
                if d<=tol: n+=1; err+=d
            if n>best[1] or (n==best[1] and err<best[2]):
                best=(off,n,err)
    return best

def register_page(page, s_cm_per_pt, drawings=None, layers=("S-GRID","GRID","AXIS LINE")):
    vv,hh=grid_clusters(page,layers=layers,drawings=drawings)
    ox,nx,ex=fit_axis(vv,GX_list,s_cm_per_pt,flip=False)
    oy,ny,ey=fit_axis(hh,GY_list,s_cm_per_pt,flip=True)
    return {"ox":ox,"oy":oy,"s":s_cm_per_pt,"nx":nx,"ny":ny,"nv":len(vv),"nh":len(hh),"ex":ex,"ey":ey}

def make_T(reg):
    s=reg["s"]; ox=reg["ox"]; oy=reg["oy"]
    def T(x,y): return (x*s+ox, -y*s+oy)   # world cm; x right, y up
    return T

def _score(cm, master, tol):
    n=0; err=0.0; pairs=[]
    for c in cm:
        best=min(master,key=lambda m:abs(m-c))
        d=abs(best-c)
        if d<=tol: n+=1; err+=d; pairs.append((c,best))
    return n,err,pairs

def fit_axis_free(pts, master, flip, smin=1.5, smax=3.8, tol=3.5):
    """find scale s and offset: world = sign*pt*s + off. returns (s,off,n,err)"""
    sign=-1.0 if flip else 1.0
    best=None
    P=sorted(pts)
    if len(P)<2: return None
    cand_s=set()
    for i in range(len(P)):
        for j in range(i+1,len(P)):
            dp=P[j]-P[i]
            for a in range(len(master)):
                for b in range(a+1,len(master)):
                    s=(master[b]-master[a])/dp
                    if smin<=s<=smax: cand_s.add(round(s,3))
    # always add standard scales
    for s0 in (S100,S50): cand_s.add(round(s0,3))
    for s in cand_s:
        cm=[sign*p*s for p in P]
        for c in cm[:3]:
            for m in master:
                off=m-c
                n,err,_=_score([x+off for x in cm],master,tol)
                if best is None or n>best[2] or (n==best[2] and err<best[3]):
                    best=(s,off,n,err)
    return best

S100 = 100*0.3527777778/10
S50 = S100/2

def register_free(vv,hh):
    """joint fit; returns reg dict"""
    bx=fit_axis_free(vv,GX_list,flip=False) if len(vv)>=2 else None
    by=fit_axis_free(hh,GY_list,flip=True) if len(hh)>=2 else None
    cands=[b for b in (bx,by) if b]
    if not cands: return None
    # choose scale from the candidate with more matches
    cands.sort(key=lambda b:(-b[2],b[3]))
    s=cands[0][0]
    # refine offsets given s on each axis
    def off_given(pts,master,flip):
        sign=-1.0 if flip else 1.0
        cm=[sign*p*s for p in pts]
        best=(0,0,-1,1e9)
        for c in cm:
            for m in master:
                off=m-c
                n,err,_=_score([x+off for x in cm],master,3.5)
                if n>best[2] or (n==best[2] and err<best[3]): best=(0,off,n,err)
        return best
    ox=off_given(vv,GX_list,False) if vv else (0,0,0,0)
    oy=off_given(hh,GY_list,True) if hh else (0,0,0,0)
    return {"ox":ox[1],"oy":oy[1],"s":s,"nx":ox[2],"ny":oy[2],"nv":len(vv),"nh":len(hh),"ex":ox[3],"ey":oy[3]}
