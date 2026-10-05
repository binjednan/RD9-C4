import sys, math, collections
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import numpy as np
import lib, cellgrid, geo

def in_building(s, bb):
    return bb[0]<=min(s[0],s[2]) and max(s[0],s[2])<=bb[2] and bb[1]<=min(s[1],s[3]) and max(s[1],s[3])<=bb[3]

def wall_mask(sheet, bb, thin=36, tol=0.8, ext=1.6, layer="A-WALL"):
    segs=[s for s in sheet.segments(layer) if in_building(s,bb)]
    g=cellgrid.CellGrid(segs, bbox=bb, tol=tol, ext=ext)
    g.label()
    area,per,bbox_=g.comp_stats()
    S=set(c for c in range(g.ncomp) if per[c]>0 and 2*area[c]/per[c]<=thin and area[c]<4e5)
    mask=np.zeros((g.nx,g.ny),bool)
    for i in range(g.nx):
        for j in range(g.ny):
            if g.lab[i,j] in S: mask[i,j]=True
    return g,mask,segs

def run_gaps(m, xs, ys, gmin=55, gmax=140):
    out=[]
    nx,ny=m.shape
    for j in range(ny):
        runs=[]; i=0
        while i<nx:
            if m[i,j]:
                i2=i
                while i2+1<nx and m[i2+1,j]: i2+=1
                runs.append((xs[i],xs[i2+1])); i=i2+1
            else: i+=1
        for a,b in zip(runs[:-1],runs[1:]):
            gap=b[0]-a[1]
            if gmin<=gap<=gmax: out.append((a[1],b[0],ys[j],ys[j+1]))
    return out

def merge_gaps(c):
    c=sorted(c); out=[]
    for x in c:
        if out and abs(out[-1][0]-x[0])<1.5 and abs(out[-1][1]-x[1])<1.5 and abs(out[-1][3]-x[2])<1.5:
            out[-1]=(out[-1][0],out[-1][1],out[-1][2],x[3])
        else: out.append(x)
    return out

def door_candidates(g, mask, tmax=45, gmin=55, gmax=140):
    H=merge_gaps(run_gaps(mask,g.xs,g.ys,gmin,gmax))
    Vr=merge_gaps(run_gaps(mask.T,g.ys,g.xs,gmin,gmax))
    V=[(c[2],c[3],c[0],c[1]) for c in Vr]
    cands=[]
    for c in H:
        if c[3]-c[2]<=tmax: cands.append({"x0":c[0],"x1":c[1],"y0":c[2],"y1":c[3],"o":"h","w":c[1]-c[0],"t":c[3]-c[2],"cx":(c[0]+c[1])/2,"cy":(c[2]+c[3])/2})
    for c in V:
        if c[1]-c[0]<=tmax: cands.append({"x0":c[0],"x1":c[1],"y0":c[2],"y1":c[3],"o":"v","w":c[3]-c[2],"t":c[1]-c[0],"cx":(c[0]+c[1])/2,"cy":(c[2]+c[3])/2})
    return cands

def assign_tags(tags, cands, rmax=170, expw=None):
    pairs=[]
    for ti,t in enumerate(tags):
        for ci,c in enumerate(cands):
            d=math.hypot(t["X"]-c["cx"],t["Y"]-c["cy"])
            if d<rmax:
                if expw and t["s"] in expw:
                    dw=abs(c["w"]-expw[t["s"]])
                    if dw>35: continue
                    d=d+0.5*dw
                pairs.append((d,ti,ci))
    pairs.sort()
    ut=set();uc=set();res={}
    for d,ti,ci in pairs:
        if ti in ut or ci in uc: continue
        ut.add(ti);uc.add(ci);res[ti]=(ci,d)
    return res

import bisect
def cell_of(g, x, y):
    i=bisect.bisect_right(list(g.xs),x)-1; j=bisect.bisect_right(list(g.ys),y)-1
    if i<0 or j<0 or i>=g.nx or j>=g.ny: return None
    return g.lab[i,j]

def door_closures(doors):
    clos=[]
    for c in doors:
        if c["o"]=="h": clos.append((c["x0"],(c["y0"]+c["y1"])/2,c["x1"],(c["y0"]+c["y1"])/2))
        else: clos.append(((c["x0"]+c["x1"])/2,c["y0"],(c["x0"]+c["x1"])/2,c["y1"]))
    return clos

def door_sides(g2, d, off=28):
    if d["o"]=="h":
        a=cell_of(g2,d["cx"],d["y1"]+off); b=cell_of(g2,d["cx"],d["y0"]-off)
    else:
        a=cell_of(g2,d["x1"]+off,d["cy"]); b=cell_of(g2,d["x0"]-off,d["cy"])
    return a,b

class UF:
    def __init__(self): self.p={}
    def f(self,a):
        self.p.setdefault(a,a)
        while self.p[a]!=a:
            self.p[a]=self.p[self.p[a]]; a=self.p[a]
        return a
    def u(self,a,b): self.p[self.f(a)]=self.f(b)
