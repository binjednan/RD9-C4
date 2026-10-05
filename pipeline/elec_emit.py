# -*- coding: utf-8 -*-
"""emit electrical device elements from data/elec_inst.json"""
import sys, json, math, collections
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import kb_elec as K

D="/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work/data/"
_INST=None
def inst():
    global _INST
    if _INST is None: _INST=json.load(open(D+"elec_inst.json"))
    return _INST

FAM_LV={"TY":("2","3","4","5"),"1":("1",),"G":("G",),"B":("B",),"R":("R",),"T":("T",)}
FAM_NAME={"light":"ELEC1 مخطط الإنارة","power":"ELEC1 مخطط القوى","fa":"ELEC2 مخطط إنذار الحريق","lc":"ELEC2 مخطط التيار الخفيف","tel":"ELEC2 مخطط الهاتف","ltg":"ELEC2 مخطط الصواعق"}
FAM_ONLY={"tel":{"T18","T19","T20"}}   # telephone sheets: only the ONU / ODF / MDF boards are classified reliably

def ceil_z(level,ffl):
    return ffl+3.25 if level=="B" else ffl+2.70      # B: slab soffit (no false ceiling); others: false ceiling 2.70 (assumed, as in the architectural model)

def _snap(x,y,rects,maxd=32.0):
    """nearest wall rect face -> (cx,cy,rot_deg,nx,ny) or None.  rects: list of (x0,y0,x1,y1) in cm"""
    best=None
    for (x0,y0,x1,y1) in rects:
        dx=max(x0-x,0,x-x1); dy=max(y0-y,0,y-y1)
        d=math.hypot(dx,dy)
        if d>maxd: continue
        if best is None or d<best[0]: best=(d,(x0,y0,x1,y1))
    if best is None: return None
    d,(x0,y0,x1,y1)=best
    w=x1-x0; h=y1-y0
    if w>=h:   # horizontal wall: faces at y0 / y1
        if abs(y-y0)<=abs(y-y1): return (min(max(x,x0),x1),y0,0.0,0.0,-1.0)
        return (min(max(x,x0),x1),y1,0.0,0.0,1.0)
    if abs(x-x0)<=abs(x-x1): return (x0,min(max(y,y0),y1),90.0,-1.0,0.0)
    return (x1,min(max(y,y0),y1),90.0,1.0,0.0)

def R3(v): return round(v,3)
def emit_family(add, fam, famkey, level, fm, ffl, wall_rects=None, sheet_label=None):
    """add elements for one family+level.  returns count"""
    rec=inst().get(f"{fam}|{famkey}")
    if not rec: return 0
    only=FAM_ONLY.get(fam)
    cz=ceil_z(level,ffl)
    n=0
    for i in rec["inst"]:
        c=i["c"]
        if not c or c not in K.C: continue
        if only is not None and c not in only: continue
        if fam=="lc" and c=="T14" and level!="G": c="T2"   # VDR/monitor exist only in the security room; elsewhere this symbol is the TV junction box
        k=K.C[c]
        x,y,w,h=i["x"],i["y"],i["w"],i["h"]
        u=u2=None
        if fm is not None and getattr(fm,"flats",None):
            fl=fm.flat_at(x,y,search=True)
            if fl: u=fl[0]; u2=fl[1] if len(fl)>1 else None
        z0=(cz+k["z0"]) if k["mode"]=="ceil" else (ffl+k["z0"])
        z1=z0+k["h"]
        shape=k["shape"]; geo=None
        if shape=="disc":
            r=(k["wd"][0]/2.0) if k["wd"] else max(3.0,min(12.0,min(w,h)/2.0))
            geo=["cyl",round(x,1),round(y,1),round(r,1),R3(z0),R3(z1)]
        elif shape=="pend":
            r=max(5.0,min(22.0,min(w,h)/2.0))
            geo=["cyl",round(x,1),round(y,1),round(r,1),R3(z0),R3(z1)]
        elif shape in("lin","box"):
            L=max(w,h); S=min(w,h)
            L=min(max(L,k["cap"][0]),k["cap"][1] if shape=="lin" else 70); S=min(max(S,k["cap"][0]*0.6),L if shape=="box" else 20)
            ang=0.0 if w>=h else 90.0
            if k["mode"]=="wall":
                sn=_snap(x,y,wall_rects or [])
                if sn: x,y,ang,_,_=sn[0],sn[1],sn[2],sn[3],sn[4]
            geo=["b",round(x,1),round(y,1),round(L,1),round(S,1),ang,R3(z0),R3(z1)]
        elif shape=="plate":
            wd=k["wd"] or (9,4)
            width=wd[0]; thk=4.0 if k["h"]<=0.16 else wd[1]
            sn=_snap(x,y,wall_rects or []) if k["mode"]=="wall" else None
            if sn:
                cx,cy,ang,nx,ny=sn
                cx+=nx*thk/2.0; cy+=ny*thk/2.0
                geo=["b",round(cx,1),round(cy,1),round(width,1),round(thk,1),ang,R3(z0),R3(z1)]
            else:
                ang=0.0 if w>=h else 90.0
                geo=["b",round(x,1),round(y,1),round(width,1),round(thk,1),ang,R3(z0),R3(z1)]
        elif shape=="dish":
            geo=["cyl",round(x,1),round(y,1),60.0,R3(z0),R3(z0+0.18)]
        elif shape=="mast":
            geo=["cyl",round(x,1),round(y,1),1.2,R3(z0),R3(z1)]
        if geo is None: continue
        srcs=[f"{FAM_NAME[fam]} ({rec['sheet']}) — مطابقة رمز الجهاز بمفتاح المخطط (تصنيف آلي بالمطابقة الشكلية، درجة التشابه {i['sc']})"]
        srcs.append("الموضع من المخطط (إحداثيات مسجّلة على شبكة المحاور)")
        if k["src"]: srcs.append("المرجع: "+k["src"])
        cat=k["cat"]
        add(cat,level,geo,mark=None,typ="e_"+c,mat=k["mat"],attrs={"cls":c,"match":i["sc"]},u=u,u2=u2,src=srcs)
        n+=1
    return n
