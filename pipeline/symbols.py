import math, collections
import geo

def prim_list(sheet, layers, maxdim_pt=60):
    """small primitives (in PDF pts) of given layers: list of dict(bbox,pts,type,len,nitems,fill)"""
    out=[]
    for d in sheet.D:
        if d["layer"] not in layers: continue
        for pl in d["polys"]:
            xs=[p[0] for p in pl]; ys=[p[1] for p in pl]
            w=max(xs)-min(xs); h=max(ys)-min(ys)
            if max(w,h)>maxdim_pt: continue
            nc=sum(1 for it in d["items"] if it[0]=="c")
            out.append({"bb":(min(xs),min(ys),max(xs),max(ys)),"n":len(pl),"w":w,"h":h,"curve":nc>0,"fill":d["fill"] is not None,"closed":geo.is_closed(pl,0.3),"layer":d["layer"],"pl":pl})
    return out

def cluster_prims(prims, gap=0.6):
    n=len(prims); par=list(range(n))
    def find(a):
        while par[a]!=a: par[a]=par[par[a]]; a=par[a]
        return a
    # grid hash
    cell=max(4.0,gap*4)
    H=collections.defaultdict(list)
    for i,p in enumerate(prims):
        b=p["bb"]
        for cx in range(int((b[0]-gap)//cell),int((b[2]+gap)//cell)+1):
            for cy in range(int((b[1]-gap)//cell),int((b[3]+gap)//cell)+1):
                H[(cx,cy)].append(i)
    for ids in H.values():
        for a in range(len(ids)):
            for b2 in range(a+1,len(ids)):
                i,j=ids[a],ids[b2]
                A=prims[i]["bb"]; B=prims[j]["bb"]
                if A[0]-gap<=B[2] and B[0]-gap<=A[2] and A[1]-gap<=B[3] and B[1]-gap<=A[3]:
                    par[find(i)]=find(j)
    g=collections.defaultdict(list)
    for i in range(n): g[find(i)].append(i)
    return list(g.values())

def signature(prims, ids, q=0.25):
    """rotation-invariant signature of a symbol group"""
    items=[]
    for i in ids:
        p=prims[i]
        items.append((round(max(p["w"],p["h"])/q),round(min(p["w"],p["h"])/q),p["n"] if p["n"]<6 else 6,int(p["curve"]),int(p["fill"]),int(p["closed"])))
    items.sort()
    b0=min(prims[i]["bb"][0] for i in ids); b1=min(prims[i]["bb"][1] for i in ids); b2=max(prims[i]["bb"][2] for i in ids); b3=max(prims[i]["bb"][3] for i in ids)
    dims=sorted([round((b2-b0)/q),round((b3-b1)/q)])
    return (tuple(items),tuple(dims))

def group_info(prims, ids):
    b0=min(prims[i]["bb"][0] for i in ids); b1=min(prims[i]["bb"][1] for i in ids); b2=max(prims[i]["bb"][2] for i in ids); b3=max(prims[i]["bb"][3] for i in ids)
    return {"bb":(b0,b1,b2,b3),"c":((b0+b2)/2,(b1+b3)/2),"w":b2-b0,"h":b3-b1,"n":len(ids)}

def signature_norm(prims, ids, q=0.12):
    inf=group_info(prims,ids); D=max(inf["w"],inf["h"]) or 1.0
    items=[]
    for i in ids:
        p=prims[i]
        items.append((round(max(p["w"],p["h"])/D/q),round(min(p["w"],p["h"])/D/q),min(p["n"],6),int(p["curve"]),int(p["fill"]),int(p["closed"])))
    items.sort()
    asp=round(min(inf["w"],inf["h"])/D/0.1)
    return (len(ids),tuple(items),asp)

def legend_rows(sheet, xr, yr, layers=None):
    """text rows (PDF pts) inside region; returns list of dict(text,x0,x1,y)"""
    ws=[w for w in sheet.WD if xr[0]<=w["x"]<=xr[1] and yr[0]<=w["y"]<=yr[1] and (layers is None or w["layer"] in layers)]
    ws.sort(key=lambda w:(round(w["y"]/3),w["x"]))
    rows=[]
    for w in ws:
        if rows and abs(rows[-1]["y"]-w["y"])<=2.2 and w["bbox"][0]-rows[-1]["x1"]<14:
            rows[-1]["text"]+=" "+w["s"]; rows[-1]["x1"]=w["bbox"][2]
        else:
            rows.append({"text":w["s"],"x0":w["bbox"][0],"x1":w["bbox"][2],"y":w["y"]})
    return rows

def match_legend(sheet, layers, rows, xwin=(-70,-2), ywin=8, maxdim=80, gap=0.5):
    """for each legend row find symbol cluster to its left. returns list of (row, group_info, signature)"""
    prims=prim_list(sheet,layers,maxdim_pt=maxdim)
    groups=cluster_prims(prims,gap=gap)
    G=[]
    for ids in groups:
        inf=group_info(prims,ids); inf["sig"]=signature_norm(prims,ids); inf["ids"]=ids; G.append(inf)
    out=[]
    for r in rows:
        best=None
        for g in G:
            dx=g["c"][0]-r["x0"]; dy=g["c"][1]-r["y"]
            if xwin[0]<=dx<=xwin[1] and abs(dy)<=ywin:
                d=abs(dy)+abs(dx+10)*0.1
                if best is None or d<best[0]: best=(d,g)
        out.append((r,best[1] if best else None))
    return out,prims,G

def sig_dist(a,b):
    """distance between normalized signatures (n, items, asp)"""
    if a[0]!=b[0]: return 1e9
    d=abs(a[2]-b[2])*0.5
    for x,y in zip(a[1],b[1]):
        d+=abs(x[0]-y[0])+abs(x[1]-y[1])+abs(x[2]-y[2])*2+abs(x[3]-y[3])*3+abs(x[4]-y[4])*2+abs(x[5]-y[5])*2
    return d

def classify_plan(sheet, layers, legend, plan_box=None, maxdim=60, gap=0.5, thr=3.0):
    """legend: list of (label, signature). returns plan symbol instances: dict(c,x,y,w,h,label,dist) in world cm"""
    prims=prim_list(sheet,layers,maxdim_pt=maxdim)
    groups=cluster_prims(prims,gap=gap)
    out=[]
    for ids in groups:
        inf=group_info(prims,ids); sig=signature_norm(prims,ids)
        best=None
        for lab,ls in legend:
            d=sig_dist(sig,ls)
            if best is None or d<best[0]: best=(d,lab)
        (x0,y1),(x1,y0)=sheet.T(inf["bb"][0],inf["bb"][1]),sheet.T(inf["bb"][2],inf["bb"][3])
        rec={"x":(x0+x1)/2,"y":(y0+y1)/2,"w":abs(x1-x0),"h":abs(y1-y0),"n":inf["n"],"pts":(inf["c"][0],inf["c"][1]),"label":best[1] if best and best[0]<=thr else None,"dist":best[0] if best else None,"sig":sig}
        out.append(rec)
    return out

def legend_table(sheet, layers, region, text_layers=None, ywin=7.0, maxdim=70, gap=0.5):
    """generic legend parse: region=(x0,y0,x1,y1) in PDF pts. returns rows [(text, group_info|None, signature)]"""
    xr=(region[0],region[2]); yr=(region[1],region[3])
    rows=legend_rows(sheet,xr,yr,text_layers)
    prims=[p for p in prim_list(sheet,layers,maxdim_pt=maxdim) if region[0]<=(p["bb"][0]+p["bb"][2])/2<=region[2] and region[1]<=(p["bb"][1]+p["bb"][3])/2<=region[3]]
    groups=cluster_prims(prims,gap=gap)
    G=[]
    for ids in groups:
        inf=group_info(prims,ids); inf["sig"]=signature_norm(prims,ids); inf["ids"]=ids; G.append(inf)
    out=[]
    for r in rows:
        best=None
        for g in G:
            dy=abs(g["c"][1]-r["y"]); dx=r["x0"]-g["c"][0]
            if dy<=ywin and -4<=dx<=120:
                sc=dy*2+dx*0.15
                if best is None or sc<best[0]: best=(sc,g)
        out.append((r,best[1] if best else None))
    return out,G

def build_legend(sheet, layers, regions, text_layers=None, ywin=7.0, maxdim=70):
    """merge multi-line rows that share the same symbol group; returns [(label, sig, info)]"""
    legend=[]
    for reg in regions:
        rows,G=legend_table(sheet,layers,reg,text_layers,ywin=ywin,maxdim=maxdim)
        cur=None
        for r,g in rows:
            if g is None:
                if cur is not None and abs(r["y"]-cur["y"])<14 and r["x0"]>=cur["x0"]-3 and len(r["text"])>3 and not r["text"].upper().startswith(("LEGEND","SYMBOL","REF","DESC")):
                    cur["text"]+=" "+r["text"]; cur["y"]=r["y"]
                continue
            if cur is not None and cur["g"] is g:
                cur["text"]+=" "+r["text"]; cur["y"]=r["y"]
            else:
                if cur: legend.append(cur)
                cur={"text":r["text"],"g":g,"y":r["y"],"x0":r["x0"]}
        if cur: legend.append(cur)
    return [(l["text"],l["g"]["sig"],l["g"]) for l in legend if not l["text"].upper().startswith(("LEGEND","SYMBOL","DESCRIPTION"))]
