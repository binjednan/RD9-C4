import sys, json, math, collections
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import geo
D="/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work/data/"
from build_struct import SLAB, FFL, RAFT_TOP, COLSPAN

LNAME={"B":"البدروم","G":"الأرضي","1":"الأول","2":"الثاني","3":"الثالث","4":"الرابع","5":"الخامس","R":"السطح","T":"سطح الغرف العلوي"}

def R(x0,y0,x1,y1,z0,z1): return ["r",round(x0,1),round(y0,1),round(x1,1),round(y1,1),round(z0,3),round(z1,3)]
def P(pts,z0,z1,holes=None):
    g=["p",[[round(x,1),round(y,1)] for x,y in pts],round(z0,3),round(z1,3)]
    if holes: g.append([[[round(x,1),round(y,1)] for x,y in h] for h in holes])
    return g

def build(els):
    st=json.load(open(D+"struct.json")); s2=json.load(open(D+"struct2.json")); piles=json.load(open("/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work/piles.json"))
    n=collections.Counter()
    def add(c,l,g,mark=None,typ=None,mat="conc",attrs=None,src=None,u=None):
        n[c]+=1
        els.append({"id":f"{c}-{l}-{n[c]:04d}","c":c,"l":l,"g":g,"mark":mark,"t":typ,"m":mat,"a":attrs or {},"s":src or [],"u":u})
    # ---- raft / foundations
    PC1=[(-31,2435),(767,2435),(767,1940),(3286,1940),(3286,-31),(-31,-31)]
    outer=[(-30,-30),(4440,-30),(4440,4440),(-30,4440)]
    add("S.raft","B",P(outer,RAFT_TOP-0.80,RAFT_TOP,holes=[PC1]),"RAFT-80",typ="raft80",attrs={"thk_cm":80},src=["STR p11: «SLAB -80cm THICK RAFT»"])
    add("S.raft","B",P(PC1,RAFT_TOP-1.50,RAFT_TOP),"PC1-150",typ="raft150",attrs={"thk_cm":150},src=["STR p11: «PC1 - 150cm»"])
    for k,(x,y) in enumerate(piles):
        add("S.pile","B",["cyl",round(x,1),round(y,1),30,round(RAFT_TOP-1.50-13.0,2),round(RAFT_TOP-1.50,2)],mark=f"P1-{k+1:02d}",typ="pile",mat="conc_sr",attrs={"dia_cm":60,"len_m":13},src=["STR p11 layer PILES$0$ST-PILE (دائرة Ø60)","STR p11: Pile length = 13m"])
    # ---- columns / walls / cores
    for c in st["cols"]:
        kind=c["kind"]; cat="S.col" if kind=="column" else "S.wall"
        l=c["lvl"]
        add(cat,l,P(c["poly"],c["z0"],c["z1"]),mark=c.get("mark"),typ="col_"+(c.get("mark") or kind),mat="conc_sr" if l in("B",) else "conc",attrs={"kind":kind},src=[c["src"]])
    for w in st["walls"]:
        add("S.wall",w["lvl"],P(w["poly"],w["z0"],w["z1"]),typ="wall_rc",mat="conc_sr" if w["lvl"]=="B" else "conc",src=[w["src"]])
    for rg in st["rings"]:
        add("S.wall",rg["lvl"],P(rg["outer"],rg["z0"],rg["z1"],holes=[rg["inner"]]),mark="BASEMENT-WALL",typ="wall_base300",mat="conc_sr",attrs={"thk_cm":30},src=[rg["src"]])
    # ---- slabs
    for s in s2["slabs"]:
        z1=s["top"]; z0=z1-s["t"]
        if "rects" in s:
            for r in s["rects"]:
                add("S.slab",s["lvl"],R(r[0],r[1],r[2],r[3],z0,z1),mark="SLAB-"+s["lvl"],typ="slab_"+s["lvl"],attrs={"thk_cm":round(s["t"]*100)},src=["STR p24 (S-19 TOP ROOF SLAB LAYOUT)"])
        else:
            add("S.slab",s["lvl"],P(s["outer"],z0,z1,holes=s["holes"]),mark="SLAB-"+s["lvl"],typ="slab_"+s["lvl"],attrs={"thk_cm":round(s["t"]*100)},src=["STR slab layout"])
    # ---- beams (typical beams of floor 2 repeated for 3,4,5)
    for b in s2["beams"]:
        lv=[b["lvl"]] if b["lvl"]!="2" else ["2","3","4","5"]
        for l in lv:
            top=SLAB[l][0]
            add("S.beam",l,P(b["poly"],top-b["depth"]/100.0,top),mark=b["mark"],typ="beam_"+str(b["mark"]),attrs={"w_cm":b["w"],"d_cm":b["depth"]},src=[f"STR p{b['page']} layer BEAM"])
    return n

if __name__=="__main__":
    els=[]
    n=build(els)
    print(n, len(els))
    json.dump(els,open(D+"els_struct.json","w"))
