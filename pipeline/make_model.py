import sys, json, collections, os
import numpy as np
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import defs, assemble_struct, assemble_arch as AA, geo, hvac, plumb, elec_emit as EE
from floormap import FLAT_INFO
OUT="/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/www/model.json"
els=[]; cnt=collections.Counter()
assemble_struct.build(els)
def add(c,l,g,mark=None,typ=None,mat="conc",attrs=None,src=None,u=None,u2=None,flat_no=None,grp=None):
    cnt[c]+=1
    e={"id":f"{c}-{l}-{cnt[c]:04d}","c":c,"l":l,"g":g,"mark":mark,"t":typ,"m":mat,"a":attrs or {},"s":src or []}
    if u: e["u"]=f"{l}-{u}"
    if u2: e["u2"]=f"{l}-{u2}"
    if grp: e["grp"]=grp
    els.append(e)
units=[]
for lvl in ("1","2","3","4","5"):
    AA.build_tower_level(els,add,lvl)
    AA.build_floor_finishes(els,add,lvl)
    AA.build_facade_level(els,add,lvl,6 if lvl=="1" else 7)
    fm=AA.fmap(AA.TOWER_LV[lvl]["pn"],AA.TOWER_LV[lvl]["hvac"])
    for no,fl in sorted(fm.flats.items()):
        bed,gross=FLAT_INFO[no]
        m=np.zeros_like(fm.g2.lab,dtype=bool)
        for c in fl["comps"]: m|=(fm.g2.lab==c)
        units.append({"id":f"{lvl}-{no}","level":lvl,"flat":no,"name":f"شقة {no}","bed":bed,"gross":gross,"net":round(float(fl["area"]),1),"rects":[[round(a,1) for a in r] for r in fm.g2.rects(m)]})
for lvl in ("G","R","B"):
    AA.build_level_generic(els,add,lvl)
    AA.build_floor_finishes(els,add,lvl)
AA.build_stairs(add); AA.build_lifts(add); AA.build_parapets(add); AA.build_ground_front(add)
# ---- HVAC (AC layout sheets)
_RAC={}
def rac(page,ref):
    if page not in _RAC: _RAC[page]=hvac.extract_ac(page,ref)
    return _RAC[page]
for lvl,page,ref,fl in (("1",3,6,"1"),("2",4,7,"4"),("3",4,7,"4"),("4",4,7,"4"),("5",5,7,"5")):
    fm=AA.fmap(AA.TOWER_LV[lvl]["pn"],AA.TOWER_LV[lvl]["hvac"])
    hvac.emit_ac(add,lvl,rac(page,ref),fm,AA.FFL[lvl],floor_label=fl)
# ---- plumbing / fire fighting
_RP={}
def rp(kind,page,ref):
    k=(kind,page)
    if k not in _RP: _RP[k]={"ws":plumb.extract_ws,"dr":plumb.extract_dr,"ff":plumb.extract_ff}[kind](page,ref)
    return _RP[k]
for lvl,(wsp,drp,ffp) in (("1",(20,5,12)),("2",(21,6,13)),("3",(21,6,13)),("4",(21,6,13)),("5",(21,6,13))):
    fm=AA.fmap(AA.TOWER_LV[lvl]["pn"],AA.TOWER_LV[lvl]["hvac"]); ref=6 if lvl=="1" else 7
    plumb.emit_ws(add,lvl,rp("ws",wsp,ref),fm,AA.FFL[lvl])
    plumb.emit_dr(add,lvl,rp("dr",drp,ref),fm,AA.FFL[lvl])
    plumb.emit_ff(add,lvl,rp("ff",ffp,ref),fm,AA.FFL[lvl])
# ---- electrical devices (symbols matched to each sheet's legend)
def fm_for(level):
    if level in AA.TOWER_LV: P=AA.TOWER_LV[level]; return AA.fmap(P["pn"],P["hvac"])
    if level in ("G","R","B"): C=AA.LEVEL_CFG[level]; return AA.fmap(C["pn"],C["hvac"])
    return None
_WR={}
def wr(level):
    if level not in _WR:
        f=fm_for(level); _WR[level]=f.wall_rects() if f is not None else None
    return _WR[level]
nel=0
for fam in ("light","power","fa","lc","tel","ltg"):
    for famkey,lvls in EE.FAM_LV.items():
        for level in lvls:
            nel+=EE.emit_family(add,fam,famkey,level,fm_for(level),AA.FFL[level],wall_rects=wr(level))
print("electrical devices",nel)
# assign units to structural columns/walls inside flats
for e in els:
    if e["c"] in ("S.col","S.wall") and e["l"] in ("1","2","3","4","5") and e["g"][0]=="p":
        bb=geo.bbox(e["g"][1]); cx=(bb[0]+bb[2])/2; cy=(bb[1]+bb[3])/2
        fm=AA.fmap(AA.TOWER_LV[e["l"]]["pn"],AA.TOWER_LV[e["l"]]["hvac"])
        fl=fm.flat_at(cx,cy,search=True)
        if fl:
            e["u"]=f"{e['l']}-{fl[0]}"
            if len(fl)>1 and fl[1]!=fl[0]: e["u2"]=f"{e['l']}-{fl[1]}"
env=[]
for l in defs.LEVELS:
    if l["id"]=="B": env.append([-30,-30,4440,4440,-4.7,-0.1]); continue
    if l["id"]=="G": env.append([95,220,2495,1640,-0.1,5.4]); continue
    if l["id"] in ("1","2","3","4","5"): env.append([84,-91,3205,1880,l["ffl"]-0.4,l["top"]]); continue
    if l["id"]=="R": env.append([84,-91,3205,1880,l["ffl"]-0.4,25.25])
POOL=[];PIDX={}
def pool(s):
    if s not in PIDX: PIDX[s]=len(POOL); POOL.append(s)
    return PIDX[s]
for e in els: e["s"]=[pool(s) for s in e.get("s",[])]
model={"sp":POOL,"env":env,"meta":{"project":"مبنى مروان الزعابي السكني — القطعة C4، مدينة الرياض RD09"},"levels":defs.LEVELS,"layers":defs.LAYERS,"mats":defs.MATS,"units":units,"els":els}
json.dump(model,open(OUT,"w"),separators=(",",":"))
print(len(els), os.path.getsize(OUT)//1024,"KB", cnt)
