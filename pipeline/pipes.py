import sys, math, collections, re
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import lib, geo, mep_common as MC, symbols as SY

def axis_merge(segs, gap=12.0, tol=0.8, ang_tol_deg=1.0):
    """merge collinear (axis-aligned) segments separated by gaps<=gap (dashed lines); other segments kept"""
    H=collections.defaultdict(list); V=collections.defaultdict(list); other=[]
    for a,b in segs:
        dx=b[0]-a[0]; dy=b[1]-a[1]
        if abs(dy)<=tol and abs(dx)>0.01: H[round((a[1]+b[1])/2/tol)].append((min(a[0],b[0]),max(a[0],b[0]),(a[1]+b[1])/2))
        elif abs(dx)<=tol and abs(dy)>0.01: V[round((a[0]+b[0])/2/tol)].append((min(a[1],b[1]),max(a[1],b[1]),(a[0]+b[0])/2))
        else: other.append((a,b))
    out=[]
    for key,L in H.items():
        L.sort(); cur=list(L[0])
        for lo,hi,c in L[1:]:
            if lo-cur[1]<=gap: cur[1]=max(cur[1],hi)
            else: out.append(((cur[0],cur[2]),(cur[1],cur[2]))); cur=[lo,hi,c]
        out.append(((cur[0],cur[2]),(cur[1],cur[2])))
    for key,L in V.items():
        L.sort(); cur=list(L[0])
        for lo,hi,c in L[1:]:
            if lo-cur[1]<=gap: cur[1]=max(cur[1],hi)
            else: out.append(((cur[2],cur[0]),(cur[2],cur[1]))); cur=[lo,hi,c]
        out.append(((cur[2],cur[0]),(cur[2],cur[1])))
    return out+other

def layer_segments(sheet, layers, min_poly_len=6.0, skip_closed=True):
    segs=[]
    for pl,d in sheet.polys(layers):
        if skip_closed and geo.is_closed(pl,1.2) and geo.polyline_len(pl)<60: continue
        if geo.polyline_len(pl)<min_poly_len: continue
        for a,b in zip(pl[:-1],pl[1:]):
            if math.hypot(a[0]-b[0],a[1]-b[1])>0.3: segs.append((a,b))
    return segs

def label_items(sheet, layers, regex):
    rx=re.compile(regex); out=[]
    for s in MC.spans(sheet,layers):
        m=rx.search(s["s"])
        if m: out.append({"v":m.groups(),"x":s["X"],"y":s["Y"],"s":s["s"]})
    return out

def assign_sizes(segs, labels, rmax=95.0, to_num=lambda g:int(g[0])):
    res=[]
    for a,b in segs:
        best=None
        for l in labels:
            d=geo.dist_pt_seg((l["x"],l["y"]),a,b)
            if d<rmax and (best is None or d<best[0]): best=(d,to_num(l["v"]))
        res.append((a,b,best[1] if best else None))
    return res
