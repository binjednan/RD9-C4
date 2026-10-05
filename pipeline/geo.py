import math, collections

def area(poly):
    a=0.0
    n=len(poly)
    for i in range(n):
        x1,y1=poly[i]; x2,y2=poly[(i+1)%n]
        a+=x1*y2-x2*y1
    return a/2.0

def bbox(pts):
    xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
    return (min(xs),min(ys),max(xs),max(ys))

def is_closed(pl, tol=1.0):
    return len(pl)>=4 and math.hypot(pl[0][0]-pl[-1][0], pl[0][1]-pl[-1][1])<=tol

def simplify_closed(pl, tol=0.6):
    """drop duplicate last point and collinear/duplicate vertices"""
    p=list(pl)
    if is_closed(p): p=p[:-1]
    out=[]
    for q in p:
        if out and math.hypot(q[0]-out[-1][0], q[1]-out[-1][1])<=tol: continue
        out.append(q)
    if len(out)>2 and math.hypot(out[0][0]-out[-1][0], out[0][1]-out[-1][1])<=tol: out.pop()
    # remove collinear
    res=[]
    n=len(out)
    for i in range(n):
        a=out[i-1]; b=out[i]; c=out[(i+1)%n]
        cr=(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])
        if abs(cr)<1e-6*max(1,math.hypot(b[0]-a[0],b[1]-a[1])*math.hypot(c[0]-b[0],c[1]-b[1])): continue
        res.append(b)
    return res if len(res)>=3 else out

def key_poly(pl, q=1.0):
    pts=sorted((round(x/q),round(y/q)) for x,y in pl)
    return tuple(pts)

def pt_in_poly(pt, poly):
    x,y=pt; inside=False
    n=len(poly)
    for i in range(n):
        x1,y1=poly[i]; x2,y2=poly[(i+1)%n]
        if (y1>y)!=(y2>y):
            xi=x1+(y-y1)*(x2-x1)/(y2-y1)
            if xi>x: inside=not inside
    return inside

def dist_pt_seg(p,a,b):
    ax,ay=a; bx,by=b; px,py=p
    dx=bx-ax; dy=by-ay
    L2=dx*dx+dy*dy
    if L2==0: return math.hypot(px-ax,py-ay)
    t=max(0,min(1,((px-ax)*dx+(py-ay)*dy)/L2))
    return math.hypot(px-(ax+t*dx),py-(ay+t*dy))

def dist_pt_polyline(p,pl):
    return min(dist_pt_seg(p,pl[i],pl[i+1]) for i in range(len(pl)-1))

def polyline_len(pl):
    return sum(math.hypot(pl[i+1][0]-pl[i][0],pl[i+1][1]-pl[i][1]) for i in range(len(pl)-1))

def sample_polyline(pl, step=20):
    pts=[]
    for i in range(len(pl)-1):
        a=pl[i]; b=pl[i+1]
        L=math.hypot(b[0]-a[0],b[1]-a[1])
        n=max(1,int(L//step))
        for k in range(n):
            t=k/n
            pts.append((a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t))
    pts.append(pl[-1])
    return pts

def pair_open_polylines(opens, dmin=8, dmax=45, minlen=30):
    """pair parallel open polylines into wall polygons (robust to corners/ends). returns (polys, unpaired)"""
    used=[False]*len(opens); out=[]
    samp=[sample_polyline(p,20) for p in opens]
    def frac_ok(S, other):
        ds=[dist_pt_polyline(q,other) for q in S]
        if len(ds)>6: ds=ds[2:-2]   # ignore ends
        ok=[d for d in ds if dmin-2<=d<=dmax+2]
        med=sorted(ds)[len(ds)//2]
        return len(ok)/len(ds), med
    for i in range(len(opens)):
        if used[i]: continue
        best=None
        for j in range(len(opens)):
            if j==i or used[j]: continue
            fi,mi=frac_ok(samp[i],opens[j]); fj,mj=frac_ok(samp[j],opens[i])
            if fi<0.85 or fj<0.85: continue
            if not (dmin<=mi<=dmax and dmin<=mj<=dmax): continue
            sc=abs(mi-mj)+(1-fi)+(1-fj)
            if best is None or sc<best[0]: best=(sc,j)
        if best:
            j=best[1]; used[i]=used[j]=True
            A=list(opens[i]); B=list(opens[j])
            if math.hypot(A[0][0]-B[0][0],A[0][1]-B[0][1])>math.hypot(A[0][0]-B[-1][0],A[0][1]-B[-1][1]): B=B[::-1]
            out.append(A+B[::-1])
    unp=[opens[i] for i in range(len(opens)) if not used[i]]
    return out,unp
