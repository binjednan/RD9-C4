import sys, math, collections, re
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import lib, geo

def spans(sheet, layers):
    """text spans (runs) with world centre and string"""
    out=[]
    for t in sheet.TX:
        if layers is not None:
            if isinstance(layers,str):
                if t["layer"]!=layers: continue
            elif t["layer"] not in layers: continue
        b=t["bbox"]; cx=(b[0]+b[2])/2; cy=(b[1]+b[3])/2
        X,Y=sheet.T(cx,cy)
        (x0,y1),(x1,y0)=sheet.T(b[0],b[1]),sheet.T(b[2],b[3])
        out.append({"s":t["s"].strip(),"X":X,"Y":Y,"layer":t["layer"],"w":abs(x1-x0),"h":abs(y1-y0),"dir":t["dir"]})
    return out

def polylines(sheet, layers, minlen=3.0):
    """world-cm polylines for layer(s) (each drawing path -> polyline)"""
    out=[]
    for pl,d in sheet.polys(layers):
        L=geo.polyline_len(pl)
        if L<minlen: continue
        out.append(pl)
    return out

def closed_shapes(sheet, layers):
    out=[]
    for pl,d in sheet.polys(layers):
        if geo.is_closed(pl,1.5) and len(pl)>=4:
            b=geo.bbox(pl); out.append({"pl":pl,"bb":b,"w":b[2]-b[0],"h":b[3]-b[1],"c":((b[0]+b[2])/2,(b[1]+b[3])/2),"n":len(pl),"fill":d["fill"] is not None})
    return out

def seg_dist(p,a,b): return geo.dist_pt_seg(p,a,b)

def merge_polylines(pls, tol=1.5):
    """join polylines sharing endpoints into longer polylines (greedy)"""
    pls=[list(p) for p in pls if len(p)>=2]
    changed=True
    def near(a,b): return math.hypot(a[0]-b[0],a[1]-b[1])<=tol
    while changed:
        changed=False
        for i in range(len(pls)):
            if pls[i] is None: continue
            for j in range(len(pls)):
                if j==i or pls[j] is None: continue
                A=pls[i]; B=pls[j]
                if near(A[-1],B[0]): pls[i]=A+B[1:]; pls[j]=None; changed=True; break
                if near(A[-1],B[-1]): pls[i]=A+B[::-1][1:]; pls[j]=None; changed=True; break
                if near(A[0],B[-1]): pls[i]=B+A[1:]; pls[j]=None; changed=True; break
                if near(A[0],B[0]): pls[i]=B[::-1]+A[1:]; pls[j]=None; changed=True; break
    return [p for p in pls if p]

def simplify_poly(pl, tol=1.0):
    out=[pl[0]]
    for i in range(1,len(pl)-1):
        a=out[-1]; b=pl[i]; c=pl[i+1]
        cr=(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])
        L=math.hypot(c[0]-a[0],c[1]-a[1])
        if L>0 and abs(cr)/L<=tol: continue
        out.append(b)
    out.append(pl[-1])
    return out
