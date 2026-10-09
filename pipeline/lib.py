import fitz, math, collections, os, pickle, sys, json
sys.path.insert(0, os.path.dirname(__file__))
import reg

DL = "/Users/binqdair/Downloads/"
FILES = {"ARCH1":"Arch. Drawings Part I (1).pdf","ARCH2":"Arch. Drawings Part II.pdf","STR":"Structure Drawings (1).pdf",
         "MECH1":"Mechanical Drawings Part I (1).pdf","MECH2":"Mechanical Drawings Part II (1).pdf",
         "ELEC1":"Electrical Drawings Part I (1).pdf","ELEC2":"Electrical Drawings Part II (1).pdf","BOQ":"2849- Bill of Quantities.pdf"}
CACHE = "/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work/cache/"
os.makedirs(CACHE, exist_ok=True)
S100 = 100*0.3527777778/10   # cm per pt at 1:100
S50  = S100/2

_docs = {}
def doc(key):
    if key not in _docs: _docs[key] = fitz.open(DL+FILES[key])
    return _docs[key]

def flat_path(dr, seg_per_curve=10):
    """polylines (lists of (x,y)) in PDF pts for one drawing dict, plus flag closed"""
    polys=[]; cur=[]
    def flush():
        nonlocal cur
        if len(cur)>=2: polys.append(cur)
        cur=[]
    for it in dr["items"]:
        op=it[0]
        if op=="l":
            p1,p2=it[1],it[2]
            if cur and abs(cur[-1][0]-p1.x)<1e-4 and abs(cur[-1][1]-p1.y)<1e-4: cur.append((p2.x,p2.y))
            else: flush(); cur=[(p1.x,p1.y),(p2.x,p2.y)]
        elif op=="c":
            p1,c1,c2,p2=it[1],it[2],it[3],it[4]
            pts=[]
            for i in range(1,seg_per_curve+1):
                t=i/seg_per_curve; u=1-t
                pts.append((u**3*p1.x+3*u*u*t*c1.x+3*u*t*t*c2.x+t**3*p2.x, u**3*p1.y+3*u*u*t*c1.y+3*u*t*t*c2.y+t**3*p2.y))
            if cur and abs(cur[-1][0]-p1.x)<1e-4 and abs(cur[-1][1]-p1.y)<1e-4: cur.extend(pts)
            else: flush(); cur=[(p1.x,p1.y)]+pts
        elif op=="re":
            flush(); r=it[1]
            polys.append([(r.x0,r.y0),(r.x1,r.y0),(r.x1,r.y1),(r.x0,r.y1),(r.x0,r.y0)])
        elif op=="qu":
            flush(); q=it[1]
            polys.append([(q.ul.x,q.ul.y),(q.ur.x,q.ur.y),(q.lr.x,q.lr.y),(q.ll.x,q.ll.y),(q.ul.x,q.ul.y)])
    flush()
    return polys


def build_words(tt):
    """split texttrace spans into words using char geometry. returns list of dict(s,x,y,size,dx,dy,layer,bbox)"""
    out=[]
    for t in tt:
        chars=t["chars"]
        if not chars: continue
        dx,dy=t["dir"]; size=t["size"]
        cur=[]; 
        def flush():
            nonlocal cur
            if not cur: return
            s="".join(chr(c[0]) for c in cur)
            xs=[c[3][0] for c in cur]+[c[3][2] for c in cur]; ys=[c[3][1] for c in cur]+[c[3][3] for c in cur]
            if s.strip():
                out.append({"s":s.strip(),"x":(min(xs)+max(xs))/2,"y":(min(ys)+max(ys))/2,"size":size,"dx":dx,"dy":dy,"layer":t.get("layer"),"bbox":(min(xs),min(ys),max(xs),max(ys))})
            cur=[]
        prev=None
        for c in chars:
            ch=chr(c[0]); ox,oy=c[2]
            if ch==" ":
                flush(); prev=None; continue
            if prev is not None:
                pt=prev[2][0]*dx+prev[2][1]*dy; ct=ox*dx+oy*dy
                pp=-prev[2][0]*dy+prev[2][1]*dx; cp=-ox*dy+oy*dx
                adv=prev[3][2]-prev[3][0] if abs(dx)>abs(dy) else prev[3][3]-prev[3][1]
                gap=ct-pt-abs(adv)
                if gap>0.7*size or abs(cp-pp)>0.45*size or ct<pt-0.2*size:
                    flush()
            cur.append(c); prev=c
        flush()
    return out

class Sheet:
    def __init__(self, key, pageno, scale=None, auto_reg=True, ref=None, layers_grid=("S-GRID","GRID","AXIS LINE")):
        self.key=key; self.pageno=pageno
        cpath=CACHE+f"{key}_{pageno:02d}.pkl"
        if os.path.exists(cpath):
            self.__dict__.update(pickle.load(open(cpath,"rb")))
            if not hasattr(self,"WD"):
                self.WD=build_words(doc(key)[pageno-1].get_texttrace())
        else:
            p=doc(key)[pageno-1]
            dr=p.get_drawings()
            D=[]
            for d in dr:
                D.append({"layer":d.get("layer"),"type":d["type"],"color":d.get("color"),"fill":d.get("fill"),"width":d.get("width"),
                          "closed":d.get("closePath"),"even_odd":d.get("even_odd"),"polys":flat_path(d),
                          "items":[(it[0],)+tuple((q.x,q.y) if hasattr(q,"x") else ((q.x0,q.y0,q.x1,q.y1) if hasattr(q,"x0") else None) for q in it[1:]) for it in d["items"]],
                          "rect":(d["rect"].x0,d["rect"].y0,d["rect"].x1,d["rect"].y1)})
            tt=p.get_texttrace()
            TX=[]
            for t in tt:
                s="".join(chr(c[0]) for c in t["chars"])
                b=t["bbox"]
                TX.append({"s":s,"layer":t.get("layer"),"bbox":b,"size":t["size"],"dir":t["dir"],"color":t["color"]})
            self.D=D; self.TX=TX; self.W=p.rect.width; self.H=p.rect.height
            self.WD=build_words(tt)
            self.reg=None
            pickle.dump({"D":D,"TX":TX,"WD":self.WD,"W":self.W,"H":self.H,"reg":None},open(cpath,"wb"))
        if scale is not None:
            self.s=scale
        # Explicit source measurements override a cached weak grid fit.  In particular,
        # the old free fit only searched scales <=3.8 cm/pt and misregistered site
        # sheets printed at 1:150 / 1:200.  Keep the original registry intact.
        verified_path = os.path.join(os.path.dirname(__file__), "data", "reg_verified.json")
        if os.path.exists(verified_path):
            measured = json.load(open(verified_path, encoding="utf-8")).get(f"{key}:{pageno}")
            if measured:
                self.reg = dict(measured["reg"])
        if auto_reg and self.reg is None:
            self.register(scale, ref)
    def register(self, scale=None, ref=None):
        class Pt:
            def __init__(s,x,y): s.x=x; s.y=y
        drs=[{"layer":d["layer"],"items":[(it[0],Pt(*it[1]),Pt(*it[2])) for it in d["items"] if it[0]=="l"]} for d in self.D if d["layer"] and ("GRID" in d["layer"].upper() or "AXIS" in d["layer"].upper()) and "IDEN" not in d["layer"].upper()]
        vv,hh=reg.grid_clusters(None,layers=None,drawings=drs,minlen=50)
        r=reg.register_free(vv,hh)
        good = r and r["nx"]>=4 and r["ny"]>=3 and r["ex"]/max(r["nx"],1)<2.2 and r["ey"]/max(r["ny"],1)<2.2
        if not good and ref is not None:
            r2=self.register_by_layer(ref)
            if r2: r=r2
        self.reg=r
        cpath=CACHE+f"{self.key}_{self.pageno:02d}.pkl"
        pickle.dump({"D":self.D,"TX":self.TX,"WD":self.WD,"W":self.W,"H":self.H,"reg":self.reg},open(cpath,"wb"))
    def wall_pts(self, suffix="A-WALL"):
        P=[]
        for d in self.D:
            ly=d["layer"] or ""
            if ly==suffix or ly.endswith("$"+suffix):
                for pl in d["polys"]:
                    for a,b in zip(pl[:-1],pl[1:]):
                        L=math.hypot(a[0]-b[0],a[1]-b[1])
                        P.append((a,b,L))
        return P
    def register_by_layer(self, ref, suffix="A-WALL", scales=None):
        """register using a registered reference Sheet that has the same xref'd layer (arch plan): vote on translation."""
        rs=ref.wall_pts(suffix); ts=self.wall_pts(suffix)
        if not rs or not ts: return None
        R=[]
        for a,b,L in rs:
            R.append(ref.T(*a)); R.append(ref.T(*b))
        Tp=[]
        for a,b,L in ts:
            Tp.append(a); Tp.append(b)
        # also consider scale candidates derived from long-line length ratios
        cands=set(scales or [3.528,1.764,3.753,1.876,3.72,1.86,3.65,1.83])
        rl=sorted([L*ref.reg["s"] for a,b,L in rs],reverse=True)[:12]
        tl=sorted([L for a,b,L in ts],reverse=True)[:12]
        for x in tl[:6]:
            for y in rl:
                sc=y/x
                if 1.5<=sc<=4.0: cands.add(round(sc,3))
        best=None
        for s_ in sorted(cands):
            votes=collections.Counter()
            for (x,y) in Tp[::2]:
                for (X,Y) in R[::1]:
                    ox=X-x*s_; oy=Y+y*s_
                    votes[(round(ox/2.5),round(oy/2.5))]+=1
            (kx,ky),n=votes.most_common(1)[0]
            if best is None or n>best[0]: best=(n,s_,kx*2.5,ky*2.5)
        n,s_,ox,oy=best
        # refine offset by averaging inliers
        inl=[]
        H={}
        for X,Y in R: H.setdefault((int(X//4),int(Y//4)),[]).append((X,Y))
        for (x,y) in Tp:
            X0=x*s_+ox; Y0=-y*s_+oy
            for dx in (-1,0,1):
                for dy in (-1,0,1):
                    for (a,b) in H.get((int(X0//4)+dx,int(Y0//4)+dy),[]):
                        if abs(a-X0)<=3.5 and abs(b-Y0)<=3.5: inl.append((a-X0,b-Y0)); break
        if len(inl)<20 or len(inl)<0.25*len(Tp): return None
        ox+=sum(i[0] for i in inl)/len(inl); oy+=sum(i[1] for i in inl)/len(inl)
        return {"ox":ox,"oy":oy,"s":s_,"nx":0,"ny":0,"nv":0,"nh":0,"ex":0,"ey":0,"by":"layer","score":len(inl)/len(Tp)}
    # transform pts -> world cm (x right, y up)
    def T(self,x,y):
        r=self.reg
        if r is None: return (x*S100, -y*S100)
        return (x*r["s"]+r["ox"], -y*r["s"]+r["oy"])
    def Tinv(self,X,Y):
        r=self.reg
        return ((X-r["ox"])/r["s"], (r["oy"]-Y)/r["s"])
    def layers(self):
        c=collections.Counter(d["layer"] for d in self.D); return c
    def drawings(self, layer=None, pred=None):
        for d in self.D:
            if layer is not None:
                if isinstance(layer,str):
                    if d["layer"]!=layer: continue
                elif d["layer"] not in layer: continue
            if pred and not pred(d): continue
            yield d
    def polys(self, layer, closed_only=False):
        """world-cm polylines for layer(s)"""
        out=[]
        for d in self.drawings(layer):
            for pl in d["polys"]:
                w=[self.T(x,y) for x,y in pl]
                out.append((w,d))
        return out
    def segments(self, layer):
        out=[]
        for pl,d in self.polys(layer):
            for a,b in zip(pl[:-1],pl[1:]): out.append((a[0],a[1],b[0],b[1]))
        return out
    def texts(self, layer=None):
        out=[]
        for t in self.TX:
            if layer is not None:
                if isinstance(layer,str):
                    if t["layer"]!=layer: continue
                elif t["layer"] not in layer: continue
            b=t["bbox"]
            cx=(b[0]+b[2])/2; cy=(b[1]+b[3])/2
            X,Y=self.T(cx,cy)
            out.append({"s":t["s"],"X":X,"Y":Y,"layer":t["layer"],"size":t["size"],"bbox_w":(self.T(b[0],b[1]),self.T(b[2],b[3]))})
        return out

    def words(self, layer=None, pred=None):
        out=[]
        for w in self.WD:
            if layer is not None:
                if isinstance(layer,str):
                    if w["layer"]!=layer: continue
                elif w["layer"] not in layer: continue
            X,Y=self.T(w["x"],w["y"])
            r=dict(w); r["X"]=X; r["Y"]=Y
            if pred and not pred(r): continue
            out.append(r)
        return out
