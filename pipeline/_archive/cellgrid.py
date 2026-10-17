import numpy as np, collections, math, bisect

def cluster(vals, tol):
    vals=sorted(vals); out=[]
    for v in vals:
        if out and v-out[-1][-1]<=tol: out[-1].append(v)
        else: out.append([v])
    return [sum(c)/len(c) for c in out]

class CellGrid:
    """Compressed-coordinate grid from orthogonal segments. Cells between consecutive unique x / y.
       vblock[i,j]: wall line on x=xs[i] spanning row j (between cell i-1 and i).
       hblock[i,j]: wall line on y=ys[j] spanning column i (between cell j-1 and j)."""
    def __init__(self, segs, tol=0.8, ext=1.6, bbox=None):
        # segs: (x1,y1,x2,y2) cm. keep orthogonal ones
        V=[];H=[]
        for x1,y1,x2,y2 in segs:
            if abs(x1-x2)<=tol*0.9 and abs(y1-y2)>0.5: V.append((0.5*(x1+x2),min(y1,y2),max(y1,y2)))
            elif abs(y1-y2)<=tol*0.9 and abs(x1-x2)>0.5: H.append((0.5*(y1+y2),min(x1,x2),max(x1,x2)))
        xs=[v[0] for v in V]+[c for h in H for c in (h[1],h[2])]
        ys=[h[0] for h in H]+[c for v in V for c in (v[1],v[2])]
        if bbox:
            xs+= [bbox[0],bbox[2]]; ys+=[bbox[1],bbox[3]]
        self.xs=np.array(cluster(xs,tol)); self.ys=np.array(cluster(ys,tol))
        nx=len(self.xs)-1; ny=len(self.ys)-1
        self.nx,self.ny=nx,ny
        self.vblock=np.zeros((nx+1,ny),bool); self.hblock=np.zeros((nx,ny+1),bool)
        def idx(arr,v): return int(np.argmin(np.abs(arr-v)))
        for x,y0,y1 in V:
            i=idx(self.xs,x)
            j0=bisect.bisect_left(self.ys,y0-ext); j1=bisect.bisect_right(self.ys,y1+ext)-1
            # cells j in [j0, j1-1] where cell j spans ys[j]..ys[j+1]
            self.vblock[i,max(j0,0):max(min(j1,ny),0)]=True
        for y,x0,x1 in H:
            j=idx(self.ys,y)
            i0=bisect.bisect_left(self.xs,x0-ext); i1=bisect.bisect_right(self.xs,x1+ext)-1
            self.hblock[max(i0,0):max(min(i1,nx),0),j]=True
        self.cw=np.diff(self.xs); self.ch=np.diff(self.ys)
    def label(self):
        nx,ny=self.nx,self.ny
        lab=-np.ones((nx,ny),int)
        cur=0
        for si in range(nx):
            for sj in range(ny):
                if lab[si,sj]>=0: continue
                lab[si,sj]=cur
                dq=collections.deque([(si,sj)])
                while dq:
                    i,j=dq.popleft()
                    if i>0 and lab[i-1,j]<0 and not self.vblock[i,j]: lab[i-1,j]=cur; dq.append((i-1,j))
                    if i<nx-1 and lab[i+1,j]<0 and not self.vblock[i+1,j]: lab[i+1,j]=cur; dq.append((i+1,j))
                    if j>0 and lab[i,j-1]<0 and not self.hblock[i,j]: lab[i,j-1]=cur; dq.append((i,j-1))
                    if j<ny-1 and lab[i,j+1]<0 and not self.hblock[i,j+1]: lab[i,j+1]=cur; dq.append((i,j+1))
                cur+=1
        self.lab=lab; self.ncomp=cur
        return lab
    def comp_stats(self):
        lab=self.lab
        area=collections.defaultdict(float); per=collections.defaultdict(float)
        bbox={}
        for i in range(self.nx):
            for j in range(self.ny):
                c=lab[i,j]; w=self.cw[i]; h=self.ch[j]
                area[c]+=w*h
                b=bbox.setdefault(c,[1e9,1e9,-1e9,-1e9])
                b[0]=min(b[0],self.xs[i]); b[1]=min(b[1],self.ys[j]); b[2]=max(b[2],self.xs[i+1]); b[3]=max(b[3],self.ys[j+1])
                # exposed edges (to a different component or blocked)
                if i==0 or lab[i-1,j]!=c: per[c]+=h
                if i==self.nx-1 or lab[i+1,j]!=c: per[c]+=h
                if j==0 or lab[i,j-1]!=c: per[c]+=w
                if j==self.ny-1 or lab[i,j+1]!=c: per[c]+=w
        return area,per,bbox
    def cells_of(self, comp_ids):
        out=[]
        S=set(comp_ids)
        for i in range(self.nx):
            for j in range(self.ny):
                if self.lab[i,j] in S: out.append((i,j))
        return out
    def rects(self, mask):
        """greedy merge of True cells (mask nx x ny) into rectangles -> list of (x0,y0,x1,y1)"""
        m=mask.copy(); out=[]
        nx,ny=self.nx,self.ny
        for j in range(ny):
            i=0
            while i<nx:
                if m[i,j]:
                    # extend along x
                    i2=i
                    while i2+1<nx and m[i2+1,j]: i2+=1
                    # extend along y while the whole run is True
                    j2=j
                    while j2+1<ny and m[i:i2+1,j2+1].all(): j2+=1
                    m[i:i2+1,j:j2+1]=False
                    out.append((self.xs[i],self.ys[j],self.xs[i2+1],self.ys[j2+1]))
                    i=i2+1
                else: i+=1
        return out
