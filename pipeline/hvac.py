import sys, math, collections, re, json
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import lib, geo, symbols as SY, mep_common as MC

SIZE_RE=re.compile(r'^\s*(\d{2,4})\s*[xX×]\s*(\d{2,4})\s*(mm)?\s*$')
def rect_orient(pl):
    """oriented bbox from polygon: returns (cx,cy,w,h,angle_deg) with w along longest edge"""
    n=len(pl)-1 if geo.is_closed(pl,1.5) else len(pl)
    best=None
    for i in range(n):
        a=pl[i]; b=pl[(i+1)%n]
        L=math.hypot(b[0]-a[0],b[1]-a[1])
        if best is None or L>best[0]: best=(L,math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]))%180)
    ang=best[1]
    c=math.cos(math.radians(ang)); s=math.sin(math.radians(ang))
    us=[p[0]*c+p[1]*s for p in pl]; vs=[-p[0]*s+p[1]*c for p in pl]
    w=max(us)-min(us); h=max(vs)-min(vs); cu=(max(us)+min(us))/2; cv=(max(vs)+min(vs))/2
    return (cu*c-cv*s, cu*s+cv*c, w, h, ang)

def extract_ac(page, ref_page):
    ref=lib.Sheet("ARCH1",ref_page); sh=lib.Sheet("MECH1",page,ref=ref)
    R={"page":page}
    tags=[w for w in sh.words(layer="M_HVAC_TEXT") if re.match(r'^FCU-',w["s"])]
    # equipment rectangles
    eq=[]
    for s_ in MC.closed_shapes(sh,"M_HVAC_EQP"):
        if s_["n"]<=6 and 60<=max(s_["w"],s_["h"])<=140 and 30<=min(s_["w"],s_["h"])<=60:
            eq.append(s_)
    # dedupe overlapping
    ded=[]
    for e in eq:
        if any(math.hypot(e["c"][0]-d["c"][0],e["c"][1]-d["c"][1])<8 for d in ded): continue
        ded.append(e)
    fcus=[]
    for e in ded:
        cx,cy,w,h,ang=rect_orient(e["pl"])
        best=None
        for t in tags:
            d=math.hypot(t["X"]-cx,t["Y"]-cy)
            if d<75 and (best is None or d<best[0]): best=(d,t["s"])
        fcus.append({"x":cx,"y":cy,"w":w,"h":h,"ang":ang,"tag":best[1] if best else None})
    R["fcus"]=fcus
    R["fcu_tags_unmatched"]=[t["s"] for t in tags if not any(f["tag"]==t["s"] for f in fcus)]
    # ducts from SAD layer (exclude circles = thermostats)
    pls=MC.polylines(sh,"M_HVAC_SAD",minlen=8)
    ducts=[];therm=[]
    for pl in pls:
        if len(pl)>=30 and geo.is_closed(pl,1.5):
            b=geo.bbox(pl); therm.append({"x":(b[0]+b[2])/2,"y":(b[1]+b[3])/2,"d":max(b[2]-b[0],b[3]-b[1])}); continue
        ducts.append(MC.simplify_poly(pl,1.0))
    sizes=[s for s in MC.spans(sh,"M_HVAC_TEXT") if SIZE_RE.match(s["s"])]
    for s in sizes:
        m=SIZE_RE.match(s["s"]); s["wd"]=int(m.group(1)); s["ht"]=int(m.group(2))
    out=[]
    for pl in ducts:
        for a,b in zip(pl[:-1],pl[1:]):
            L=math.hypot(b[0]-a[0],b[1]-a[1])
            if L<6: continue
            mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
            best=None
            for s in sizes:
                d=geo.dist_pt_seg((s["X"],s["Y"]),a,b)
                if d<85 and (best is None or d<best[0]): best=(d,s)
            out.append({"a":a,"b":b,"w":best[1]["wd"] if best else None,"h":best[1]["ht"] if best else None})
    R["duct_segs"]=out; R["therm"]=therm
    def syms(layer,minn=1):
        prims=SY.prim_list(sh,(layer,),maxdim_pt=200)
        res=[]
        if not prims: return res
        for ids in SY.cluster_prims(prims,gap=0.6):
            inf=SY.group_info(prims,ids)
            (x0,y1),(x1,y0)=sh.T(inf["bb"][0],inf["bb"][1]),sh.T(inf["bb"][2],inf["bb"][3])
            res.append({"x":(x0+x1)/2,"y":(y0+y1)/2,"w":abs(x1-x0),"h":abs(y1-y0)})
        return res
    for key,ly in (("sad","M_SAD_DIFF"),("rad","M_RAD_DIFF"),("sag","M_SAG_GRILL"),("rag","M_RAG_GRILL"),("dam","M_HVAC_DAM")):
        R[key]=syms(ly)
    # labels with flow: 'NNN L/S' near outlets ; collect 'S/RAG','SAD','S/RAD' text with positions
    R["labels"]=[{"s":s["s"],"x":s["X"],"y":s["Y"]} for s in MC.spans(sh,"M_HVAC_TEXT") if re.match(r'^(\d+\s*L/S|S/RAG|SAD|RAD|S/RAD|\d+\s*No\. S/RAD)$',s["s"])]
    R["notes"]=[s["s"] for s in MC.spans(sh,"AC-TEXT") if s["s"].startswith("General Note")]
    return R

if __name__=="__main__":
    R=extract_ac(4,7)
    print({k:(len(v) if isinstance(v,list) else v) for k,v in R.items()})
    print([ (f["tag"],round(f["x"]),round(f["y"]),round(f["w"]),round(f["h"])) for f in R["fcus"]][:20])
    print("unmatched tags",R["fcu_tags_unmatched"])
    c=collections.Counter((d["w"],d["h"]) for d in R["duct_segs"]); print(c.most_common(10))

CEIL=2.70; SOFFIT_REL=3.10
def _R(x0,y0,x1,y1,z0,z1): return ["r",round(x0,1),round(y0,1),round(x1,1),round(y1,1),round(z0,3),round(z1,3)]
def _B(x,y,w,d,ang,z0,z1): return ["b",round(x,1),round(y,1),round(w,1),round(d,1),round(ang,1),round(z0,3),round(z1,3)]

def emit_ac(add, level, R, fm, ffl, tagmap=None, floor_label=None, src_extra=""):
    """create elements for one AC layout extraction. fm: FloorMap (for flat membership) or None"""
    sheet=f"MECH1 p{R['page']}"
    def unit_of(x,y):
        if fm is None: return (None,None)
        fl=fm.flat_at(x,y,search=True)
        return (fl[0] if fl else None, fl[1] if len(fl)>1 else None)
    n=0
    for f in R["fcus"]:
        u,u2=unit_of(f["x"],f["y"])
        tag=f["tag"] or "FCU-?"
        add("M.equip",level,_B(f["x"],f["y"],f["w"],f["h"],f["ang"],ffl+2.78,ffl+3.08),mark=tag,typ="fcu",mat="m_fcu",attrs={"tag_floor":floor_label or level},u=u,u2=u2,src=[f"{sheet} طبقة M_HVAC_EQP + وسم {tag}","AC-106: جدول وحدات FCU (سعات وتدفقات)","ارتفاع التركيب فوق السقف المستعار: افتراض هندسي (غير مذكور)"]); n+=1
    for d in R["duct_segs"]:
        a,b=d["a"],d["b"]
        w=d["w"] or 200; h=d["h"] or 150
        mid=((a[0]+b[0])/2,(a[1]+b[1])/2)
        u,u2=unit_of(*mid)
        zc=ffl+SOFFIT_REL-h/200.0
        add("M.duct",level,["d",[[round(a[0],1),round(a[1],1),round(zc,3)],[round(b[0],1),round(b[1],1),round(zc,3)]],w,h],typ="duct_supply",mat="m_duct",attrs={"w_cm":w/1.0,"h_cm":h/1.0,"size_note":"من وسم المخطط" if d["w"] else "مقاس افتراضي (لا وسم قريب)"},u=u,u2=u2,src=[f"{sheet} طبقة M_HVAC_SAD (مسار مجرى التغذية) + وسم المقاس",f"ارتفاع المجرى: افتراض (قمة المجرى عند {SOFFIT_REL} م فوق الأرضية)"]); n+=1
    for key,typ,mat,z0,z1,cat in (("sad","diff_supply","m_diffuser",CEIL-0.04,CEIL,"M.outlet"),("rad","diff_return","m_diffuser_r",CEIL-0.04,CEIL,"M.outlet"),("sag","grille_supply","m_grille",CEIL-0.30,CEIL-0.08,"M.outlet"),("rag","grille_return","m_grille_r",CEIL-0.30,CEIL-0.08,"M.outlet")):
        for s in R[key]:
            u,u2=unit_of(s["x"],s["y"])
            ang=0 if s["w"]>=s["h"] else 90
            add(cat,level,_B(s["x"],s["y"],max(s["w"],s["h"]),min(s["w"],s["h"]),ang,ffl+z0,ffl+z1),typ=typ,mat=mat,attrs={"size_cm":f"{round(max(s['w'],s['h']))}×{round(min(s['w'],s['h']))}"},u=u,u2=u2,src=[f"{sheet} طبقة {'M_'+key.upper()+('_DIFF' if key in('sad','rad') else '_GRILL')}"]); n+=1
    for s in R["dam"]:
        u,u2=unit_of(s["x"],s["y"]); ang=0 if s["w"]>=s["h"] else 90
        add("M.damper",level,_B(s["x"],s["y"],max(s["w"],s["h"]),max(8,min(s["w"],s["h"])),ang,ffl+2.92,ffl+3.10),typ="damper",mat="m_damper",u=u,u2=u2,src=[f"{sheet} طبقة M_HVAC_DAM (رمز مخمد: VCD/FD/MFD)"]); n+=1
    for t in R["therm"]:
        u,u2=unit_of(t["x"],t["y"])
        add("M.equip",level,_B(t["x"],t["y"],10,10,0,ffl+1.40,ffl+1.50),mark="T",typ="thermostat",mat="m_therm",u=u,u2=u2,src=[f"{sheet} رمز ثرموستات T (طبقة M_HVAC_SAD)","ارتفاع التركيب 1.4 م: افتراض"]); n+=1
    return n
