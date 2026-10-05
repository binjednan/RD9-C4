import sys, math, collections, re
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import lib, geo, mep_common as MC, symbols as SY, pipes as PP

INCH={"1":25,"1¼":32,"1½":40,"2":50,"2½":65,"3":80,"4":100,"6":150,"8":200}
def inch_to_mm(txt):
    m=re.match(r'^(\d+)(½|¼)?"?Ø?',txt)
    if not m: return None
    k=m.group(1)+(m.group(2) or "")
    return INCH.get(k)

def _polys_from_segs(sized, default_mm):
    """group by diameter then merge into polylines"""
    byd=collections.defaultdict(list)
    for a,b,d in sized: byd[d or default_mm].append((a,b))
    out=[]
    for d,segs in byd.items():
        pls=MC.merge_polylines([[a,b] for a,b in segs],tol=1.2)
        for pl in pls:
            pl=MC.simplify_poly(pl,0.8)
            if geo.polyline_len(pl)<4: continue
            out.append((d,pl,d in [x for x in set(s[2] for s in sized if s[2])]))
    return out

def extract_ws(page, ref_page):
    ref=lib.Sheet("ARCH1",ref_page); sh=lib.Sheet("MECH2",page,ref=ref)
    R={"page":page}
    labs=PP.label_items(sh,("M_WS_TEXT","WS TEXT"),r'^(\d+)\s*Ø$')
    for name,layers,defmm in (("cold","M_WS_CW",20),("hot","M_WS_HW",20)):
        segs=PP.axis_merge(PP.layer_segments(sh,layers),gap=14)
        sized=PP.assign_sizes(segs,labs)
        R[name]=[{"d":d,"pl":pl} for d,pl,_ in _polys_from_segs(sized,defmm)]
    # heaters: clusters in layer WATER ~ 70x45
    prims=SY.prim_list(sh,("WATER",),maxdim_pt=80); s=sh.reg["s"]
    wh=[]
    labels=[{"x":sp["X"],"y":sp["Y"],"s":sp["s"]} for sp in MC.spans(sh,("M_WS_TEXT","WS TEXT","WATER"))]
    for ids in SY.cluster_prims(prims,gap=0.6):
        inf=SY.group_info(prims,ids)
        w=inf["w"]*s; h=inf["h"]*s
        if 55<=max(w,h)<=95 and 30<=min(w,h)<=60:
            (x0,y1),(x1,y0)=sh.T(inf["bb"][0],inf["bb"][1]),sh.T(inf["bb"][2],inf["bb"][3])
            cx,cy=(x0+x1)/2,(y0+y1)/2
            cap=None
            for l in labels:
                if math.hypot(l["x"]-cx,l["y"]-cy)<60:
                    m=re.search(r'(\d+)\s*L',l["s"])
                    if m and m.group(1) in("50","80"): cap=int(m.group(1))
            wh.append({"x":cx,"y":cy,"w":abs(x1-x0),"h":abs(y1-y0),"cap":cap})
    R["heaters"]=wh
    # valves / meters by text
    R["valves"]=[{"x":sp["X"],"y":sp["Y"],"t":sp["s"]} for sp in MC.spans(sh,"M_WS_TEXT") if sp["s"] in("IV","NRV","W/M","GRV","GV","WHA")]
    return R

def extract_dr(page, ref_page):
    ref=lib.Sheet("ARCH1",ref_page); sh=lib.Sheet("MECH2",page,ref=ref)
    R={"page":page}
    for name,layer,defmm in (("waste","M_DR_WP",80),("soil","M_DR_SP",110),("vent","M_DR_VP",50)):
        segs=PP.axis_merge(PP.layer_segments(sh,layer),gap=6)
        R[name]=[{"d":defmm,"pl":pl} for d,pl,_ in _polys_from_segs([(a,b,None) for a,b in segs],defmm)]
    # floor traps / cleanouts from text
    R["ft"]=[{"x":sp["X"],"y":sp["Y"]} for sp in MC.spans(sh,"M_DR_TEXT") if sp["s"] in("FT","FW")]
    R["co"]=[{"x":sp["X"],"y":sp["Y"]} for sp in MC.spans(sh,"M_DR_TEXT") if sp["s"] in("CO","FCO")]
    return R

def drop_short_diag(segs, minlen=80.0):
    """flow-arrow heads, valve bow-ties and leader ticks live on the pipe layers as short diagonal strokes; real sprinkler pipes are orthogonal
    (the few long diagonals, >= 80 cm, are kept)"""
    return [(a,b) for a,b in segs if not (abs(a[0]-b[0])>0.8 and abs(a[1]-b[1])>0.8 and math.hypot(a[0]-b[0],a[1]-b[1])<minlen)]

def extract_ff(page, ref_page):
    ref=lib.Sheet("ARCH1",ref_page); sh=lib.Sheet("MECH2",page,ref=ref)
    R={"page":page}
    labs=[]
    for sp in MC.spans(sh,("M_FF_TEXT","WS TEXT")):
        mm=inch_to_mm(sp["s"]) if re.match(r'^\d',sp["s"]) else None
        if mm: labs.append({"v":(mm,),"x":sp["X"],"y":sp["Y"],"s":sp["s"]})
    segs=drop_short_diag(PP.axis_merge(PP.layer_segments(sh,("M_FF_PIPE","SPR_MAIN_LINE")),gap=6))
    sized=PP.assign_sizes(segs,labs)
    R["pipes"]=[{"d":d,"pl":pl} for d,pl,_ in _polys_from_segs(sized,32)]
    lg=[w for w in sh.WD if w["s"]=="LEGEND"]
    legend=[]
    if lg:
        rows=[r for r in SY.legend_rows(sh,(lg[0]["x"]+30,lg[0]["x"]+340),(lg[0]["y"]+10,lg[0]["y"]+420)) if r["x0"]>1790]
        res,prims,G=SY.match_legend(sh,("M_FF_SP","M_FF_FFC"),rows)
        legend=[(r["text"],SY.signature_norm(prims,g["ids"])) for r,g in res if g is not None]
    inst=SY.classify_plan(sh,("M_FF_SP","M_FF_FFC"),legend,maxdim=80) if legend else []
    R["heads"]=[{"x":i["x"],"y":i["y"],"w":i["w"],"h":i["h"],"label":i["label"]} for i in inst]
    return R

HEAD_TYPES={"SPRINKLER (PENDENT)":"sprk_pendent","SPRINKLER (UPRIGHT)":"sprk_upright","DOUBLE SPRINKLER (PENDENT & UPRIGHT)":"sprk_double","SIDE WALL SPRINKLER":"sprk_side","EXTENDED SIDE WALL SPRINKLER":"sprk_side_ext","FIRE FIGHTING CABINET WITH LANDING VALVE":"fhc"}

def _tube(pl,z,d_mm):
    return ["t",[[round(p[0],1),round(p[1],1),round(z,3)] for p in pl],round(max(d_mm/10.0,2.2),1)]

def emit_ws(add, level, R, fm, ffl, label=""):
    sheet=f"MECH2 p{R['page']}"
    def unit_of(x,y):
        if fm is None: return (None,None)
        fl=fm.flat_at(x,y,search=True); return (fl[0] if fl else None, fl[1] if len(fl)>1 else None)
    n=0
    for key,cat,typ,mat,z in (("cold","P.cold","pipe_cold","p_cold",ffl+2.92),("hot","P.hot","pipe_hot","p_hot",ffl+2.86)):
        for p in R[key]:
            mid=p["pl"][len(p["pl"])//2]; u,u2=unit_of(*mid)
            add(cat,level,_tube(p["pl"],z,p["d"]),typ=typ,mat=mat,attrs={"dia_mm":p["d"],"length_m":round(geo.polyline_len(p["pl"])/100,2)},u=u,u2=u2,src=[f"{sheet} طبقة {'M_WS_CW' if key=='cold' else 'M_WS_HW'}",f"القطر: {'من وسم المخطط' if p['d']!=20 else 'افتراضي (لا وسم قريب)'}",f"منسوب التمديد في فراغ السقف: افتراض ({z-ffl:.2f} م فوق الأرضية)"]); n+=1
    for h in R["heaters"]:
        u,u2=unit_of(h["x"],h["y"]); ang=0 if h["w"]>=h["h"] else 90
        cap=h["cap"] or 80
        add("P.heater",level,["b",round(h["x"],1),round(h["y"],1),round(max(h["w"],h["h"]),1),round(min(h["w"],h["h"]),1),ang,round(ffl+2.55,2),round(ffl+2.98,2)],mark=f"WH-{cap}L",typ=f"heater{cap}",mat="p_heater",attrs={"cap_l":cap,"cap_known":bool(h["cap"])},u=u,u2=u2,src=[f"{sheet} طبقة WATER (رمز سخان) + وسم السعة","مفتاح المخطط: سخان كهربائي أفقي 50 لتر/1.2 كيلوواط و80 لتر/1.5 كيلوواط"]); n+=1
    for v in R["valves"]:
        u,u2=unit_of(v["x"],v["y"])
        add("P.cold",level,["b",round(v["x"],1),round(v["y"],1),9,9,0,round(ffl+2.86,2),round(ffl+2.98,2)],mark=v["t"],typ="valve_"+v["t"].replace("/",""),mat="p_valve",u=u,u2=u2,src=[f"{sheet} وسم {v['t']} (M_WS_TEXT)"]); n+=1
    return n

def emit_dr(add, level, R, fm, ffl):
    sheet=f"MECH2 p{R['page']}"
    def unit_of(x,y):
        if fm is None: return (None,None)
        fl=fm.flat_at(x,y,search=True); return (fl[0] if fl else None, fl[1] if len(fl)>1 else None)
    n=0
    for key,typ,mat,z in (("soil","pipe_soil","p_soil",ffl-0.50),("waste","pipe_waste","p_waste",ffl-0.46),("vent","pipe_vent","p_vent",ffl+2.95)):
        for p in R[key]:
            mid=p["pl"][len(p["pl"])//2]; u,u2=unit_of(*mid)
            add("P.drain",level,_tube(p["pl"],z,p["d"]),typ=typ,mat=mat,attrs={"dia_mm":p["d"],"length_m":round(geo.polyline_len(p["pl"])/100,2),"dia_note":"افتراضي حسب نوع الخط (التسميات بالبوصة عند الأعمدة فقط)"},u=u,u2=u2,src=[f"{sheet} طبقة {'M_DR_SP' if key=='soil' else 'M_DR_WP' if key=='waste' else 'M_DR_VP'}","منسوب الصرف أسفل البلاطة: افتراض"]); n+=1
    for key,typ,txt in (("ft","floor_trap","FT"),("co","cleanout","CO")):
        for s in R[key]:
            u,u2=unit_of(s["x"],s["y"])
            add("P.drain",level,["cyl",round(s["x"],1),round(s["y"],1),6,round(ffl-0.02,3),round(ffl+0.01,3)],mark=txt,typ=typ,mat="p_waste",u=u,u2=u2,src=[f"{sheet} وسم {txt} (M_DR_TEXT)"]); n+=1
    return n

def emit_ff(add, level, R, fm, ffl):
    sheet=f"MECH2 p{R['page']}"
    def unit_of(x,y):
        if fm is None: return (None,None)
        fl=fm.flat_at(x,y,search=True); return (fl[0] if fl else None, fl[1] if len(fl)>1 else None)
    n=0
    for p in R["pipes"]:
        mid=p["pl"][len(p["pl"])//2]; u,u2=unit_of(*mid)
        add("P.ff",level,_tube(p["pl"],ffl+2.98,p["d"]),typ="pipe_ff",mat="p_ff",attrs={"dia_mm":p["d"],"length_m":round(geo.polyline_len(p["pl"])/100,2)},u=u,u2=u2,src=[f"{sheet} طبقتا M_FF_PIPE / SPR_MAIN_LINE (شبكة الرشاشات)"]); n+=1
    for h in R["heads"]:
        lab=h["label"]
        if lab is None and 28<=h["w"]<=38 and 28<=h["h"]<=38: lab="SPRINKLER (PENDENT)"; derived=True
        else: derived=False
        typ=HEAD_TYPES.get(lab)
        if not typ: continue
        u,u2=unit_of(h["x"],h["y"])
        if typ=="fhc":
            add("P.ff",level,["b",round(h["x"],1),round(h["y"],1),60,25,0,round(ffl+0.9,2),round(ffl+1.9,2)],mark="FHC",typ="fhc",mat="p_ffc",u=u,u2=u2,src=[f"{sheet} طبقة M_FF_FFC (صندوق إطفاء بصمام هبوط)"]); n+=1; continue
        z0=ffl+2.62 if typ in("sprk_pendent","sprk_side","sprk_side_ext") else ffl+2.95
        add("P.ff",level,["cyl",round(h["x"],1),round(h["y"],1),4,round(z0,2),round(z0+0.10,2)],mark=lab.split("(")[0].strip().title() if lab else None,typ=typ,mat="p_sprk",attrs={"derived_type":derived},u=u,u2=u2,src=[f"{sheet} طبقة M_FF_SP + مفتاح المخطط",("النوع مشتق بالحجم (لم يطابق رمز المفتاح)" if derived else "النوع من مطابقة رمز المفتاح")]); n+=1
    return n
