import sys, math, json, collections, re, bisect
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import numpy as np
import lib, cellgrid, arch_floor as AF, geo, textgroup

BB={4:(-120,-120,4560,4560),5:(-120,-120,4560,4560),6:(-150,-250,3400,2150),7:(-150,-250,3400,2150),8:(-150,-250,3400,2150),9:(-150,-250,3400,2150)}
HVAC_PAGE={4:1,5:2,6:3,7:4,8:6}   # MECH1 pages for FCU tags

ROOM_KEYS=[("LIVING","living"),("M.BED","master_bed"),("BED","bedroom"),("KITCHEN","kitchen"),("M.BATH","bath"),("MAIN","bath"),("BATH","bath"),("W.C","wc"),("WC","wc"),("DRESS","dress"),
 ("LOBBY","lobby"),("ENTRANCE","entrance"),("STORE","store"),("LAUNDRY","laundry"),("LANDRY","laundry"),("GARBAGE","garbage"),("ELE","elec"),("TEL","tel"),("LIFT","lift"),("WASH","wash"),("RETAIL","retail"),("PUMP","pump"),("TANK","tank"),("TRANS","trans"),("GEN","gen"),("HV","hv"),("LV","lv"),("COMMAND","cmd"),("GUARD","guard"),("FILTER","filter"),("CHILLER","pump"),("IRRIGATION","pump"),("SUMP","pump"),("STAIR","stair")]

def analyze(pn, verbose=False):
    sh=lib.Sheet("ARCH1",pn); bb=BB[pn]
    g,mask,segs=AF.wall_mask(sh,bb,thin=36)
    # allow big thin comps (rings) too:
    cands=AF.door_candidates(g,mask,gmax=300)
    tags=[w for w in sh.words() if w["layer"] in ("",None,"A-DOOR TAG") and re.match(r'^D\d+$',w["s"])]
    import kb as _kb
    expw={k:v['w'] for k,v in _kb.DOORS.items()}
    asg=AF.assign_tags(tags,cands,expw=expw)
    doors=[]
    for ti,(ci,d) in asg.items():
        c=dict(cands[ci]); c["tag"]=tags[ti]["s"]; c["tagpos"]=(tags[ti]["X"],tags[ti]["Y"]); c["dist"]=d; doors.append(c)
    unassigned=[t for i,t in enumerate(tags) if i not in asg]
    clos=AF.door_closures(doors)
    glz=[s for s in sh.segments(("A-GALZ","A-WINDOW")) if AF.in_building(s,bb)]
    colsegs=[s for s in sh.segments("0") if AF.in_building(s,bb)]
    g2=cellgrid.CellGrid(segs+clos+glz+colsegs,bbox=bb,tol=1.0,ext=2.0); g2.label()
    area,per,bbox_=g2.comp_stats()
    return dict(sh=sh,bb=bb,g=g,mask=mask,segs=segs,doors=doors,unassigned=unassigned,g2=g2,area=area,per=per,bbox=bbox_,tags=tags)

if __name__=="__main__":
    for pn in (4,5,6,8):
        r=analyze(pn)
        print(pn,"doors",len(r["doors"]),"tags",len(r["tags"]),"unassigned",[(t["s"],round(t["X"]),round(t["Y"])) for t in r["unassigned"]][:10])
        print("   door tag counts",collections.Counter(d["tag"] for d in r["doors"]))

def room_kind(text):
    t=text.upper().replace(" ","")
    for k,v in ROOM_KEYS:
        if k.replace(" ","") in t: return v
    return None

def comp_words(r, words):
    """assign words to comps -> {comp: [words]}"""
    g2=r["g2"]; res=collections.defaultdict(list)
    for w in words:
        c=AF.cell_of(g2,w["X"],w["Y"])
        if c is not None: res[c].append(w)
    return res

def parse_area(s):
    m=re.search(r'A\s*=\s*([\d.]+)',s)
    return float(m.group(1)) if m else None

def build_rooms(r, pn):
    sh=r["sh"]; g2=r["g2"]
    words=sh.words(layer="A-TEXT-DETAIL")
    cw=comp_words(r,words)
    ext=g2.lab[0,0]
    rooms=[]
    for c in range(g2.ncomp):
        if c==ext: continue
        A=r["area"][c]
        if A<8000: continue   # < 0.8 m2
        ws=sorted(cw.get(c,[]),key=lambda w:(-w["Y"],w["X"]))
        txt=" ".join(w["s"] for w in ws)
        areas=[parse_area(w["s"]+" "+"") for w in ws]
        # area strings split like 'A=9.20' 'M²' -> combine
        a_ann=None
        for w in ws:
            v=parse_area(w["s"])
            if v is not None: a_ann=(a_ann or 0)+v
        names=[w["s"] for w in ws if not w["s"].startswith("A=") and w["s"] not in ("M²","M2","2","H","MV")]
        kind=room_kind(" ".join(names))
        b=r["bbox"][c]
        rooms.append({"comp":c,"area_m2":round(A/1e4,2),"ann_m2":a_ann,"names":names,"kind":kind,"bbox":[round(v) for v in b]})
    return rooms

def flats_of(r, pn, rooms):
    g2=r["g2"]; uf=AF.UF()
    for d in r["doors"]:
        a,b=AF.door_sides(g2,d)
        if a is None or b is None: continue
        if d["tag"] in ("D2","D3","D4"): uf.u(a,b)
    groups=collections.defaultdict(list)
    for rm in rooms: groups[uf.f(rm["comp"])].append(rm)
    return uf,groups
