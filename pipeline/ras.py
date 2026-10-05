"""raster-based symbol matching: robust to primitive splitting differences between legend blocks and plan instances"""
import sys, math, collections
import numpy as np
from PIL import Image, ImageDraw
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import symbols as SY

SZ=40
def render(prims, ids, size=SZ, pad=3):
    polys=[]; fills=[]
    for i in ids:
        p=prims[i]; polys.append(p["pl"]); fills.append(p["fill"] and p["closed"])
    xs=[q[0] for pl in polys for q in pl]; ys=[q[1] for pl in polys for q in pl]
    x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys)
    D=max(x1-x0,y1-y0) or 1.0
    sc=(size-2*pad)/D
    ox=(size-(x1-x0)*sc)/2; oy=(size-(y1-y0)*sc)/2
    img=Image.new("L",(size,size),0); dd=ImageDraw.Draw(img)
    for pl,f in zip(polys,fills):
        pts=[((x-x0)*sc+ox,(y-y0)*sc+oy) for x,y in pl]
        if len(pts)<2: continue
        if f and len(pts)>=3: dd.polygon(pts,fill=255)
        dd.line(pts,fill=255,width=1)
    return np.asarray(img)>0

def variants(a):
    out=[]
    for k in range(4):
        r=np.rot90(a,k); out.append(r); out.append(r[:,::-1])
    return out

def dil(a):
    b=a.copy()
    b[1:,:]|=a[:-1,:]; b[:-1,:]|=a[1:,:]; b[:,1:]|=a[:,:-1]; b[:,:-1]|=a[:,1:]
    return b

def cov(a,db):
    n=a.sum()
    return (a&db).sum()/n if n else 0.0

def score(a,b):
    """a plan bitmap, b exemplar variant"""
    return 0.5*(cov(a,dil(b))+cov(b,dil(a)))

class Exemplar:
    def __init__(self,label,bm,size_pt,extra=None):
        self.label=label; self.vars=[(v,dil(v)) for v in variants(bm)]; self.size=size_pt; self.extra=extra
    def best(self,a,da):
        s=0.0
        for v,dv in self.vars:
            sc=0.5*((a&dv).sum()/max(a.sum(),1)+(v&da).sum()/max(v.sum(),1))
            if sc>s: s=sc
        return s

def legend_clusters(sheet, layers, region, text_layers=None, ywin=7.0, maxdim=70, gap=0.5):
    """like symbols.legend_table but returns prims too. region=(x0,y0,x1,y1) in pts"""
    xr=(region[0],region[2]); yr=(region[1],region[3])
    rows=SY.legend_rows(sheet,xr,yr,text_layers)
    prims=[p for p in SY.prim_list(sheet,layers,maxdim_pt=maxdim) if region[0]<=(p["bb"][0]+p["bb"][2])/2<=region[2] and region[1]<=(p["bb"][1]+p["bb"][3])/2<=region[3]]
    groups=SY.cluster_prims(prims,gap=gap)
    G=[]
    for ids in groups:
        inf=SY.group_info(prims,ids); inf["ids"]=ids; G.append(inf)
    return rows,prims,G

def build_exemplars(sheet, layers, specs, maxdim=70, gap=0.5):
    """specs: list of dict(label, x,y: legend symbol centre approx in pts, r: search radius) -> exemplars from nearest cluster"""
    prims=SY.prim_list(sheet,layers,maxdim_pt=maxdim)
    groups=SY.cluster_prims(prims,gap=gap)
    G=[]
    for ids in groups:
        inf=SY.group_info(prims,ids); inf["ids"]=ids; G.append(inf)
    ex=[]; used=[]
    for sp in specs:
        best=None
        for g in G:
            d=math.hypot(g["c"][0]-sp["x"],g["c"][1]-sp["y"])
            if d<=sp.get("r",14) and (best is None or d<best[0]): best=(d,g)
        if best is None:
            used.append((sp["label"],None)); continue
        g=best[1]
        ex.append(Exemplar(sp["label"],render(prims,g["ids"]),max(g["w"],g["h"]),extra=sp.get("extra")))
        used.append((sp["label"],(round(g["c"][0]),round(g["c"][1]),g["n"])))
    return ex,used

def classify(sheet, layers, exemplars, maxdim=60, gap=0.5, thr=0.78, size_tol=(0.5,2.0), skip=None):
    prims=SY.prim_list(sheet,layers,maxdim_pt=maxdim)
    groups=SY.cluster_prims(prims,gap=gap)
    out=[]
    for ids in groups:
        inf=SY.group_info(prims,ids)
        if skip and skip(inf["c"][0],inf["c"][1]): continue
        a=render(prims,ids); da=dil(a)
        D=max(inf["w"],inf["h"])
        best=(0.0,None); second=(0.0,None)
        for e in exemplars:
            r=D/e.size if e.size else 1
            if not (size_tol[0]<=r<=size_tol[1]): continue
            s=e.best(a,da)
            if s>best[0]: second=best; best=(s,e)
            elif s>second[0]: second=(s,e)
        (x0,y1),(x1,y0)=sheet.T(inf["bb"][0],inf["bb"][1]),sheet.T(inf["bb"][2],inf["bb"][3])
        s_cm=sheet.reg["s"]
        out.append({"x":(x0+x1)/2,"y":(y0+y1)/2,"w":abs(x1-x0),"h":abs(y1-y0),"n":inf["n"],"pts":(inf["c"][0],inf["c"][1]),"score":best[0],"label":best[1].label if best[1] is not None and best[0]>=thr else None,"best":best[1].label if best[1] is not None else None,"extra":best[1].extra if best[1] is not None and best[0]>=thr else None,"ids":ids,"bm":a})
    return out,prims
