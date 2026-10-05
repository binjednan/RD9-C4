import sys, json, collections, time
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import fitz, reg, lib
class Pt:
    def __init__(s,x,y): s.x=x; s.y=y
out={}
t0=time.time()
for key in ["ARCH1","STR","MECH1","MECH2","ELEC1","ELEC2","ARCH2"]:
    d=lib.doc(key)
    for i in range(len(d)):
        p=d[i]
        try:
            dr=p.get_drawings()
        except Exception as e:
            out[f"{key}:{i+1}"]=None; continue
        drs=[]
        for it in dr:
            ly=it.get("layer")
            if ly and ("GRID" in ly.upper() or "AXIS" in ly.upper()) and "IDEN" not in ly.upper():
                drs.append({"layer":ly,"items":[(o[0],o[1],o[2]) for o in it["items"] if o[0]=="l"]})
        vv,hh=reg.grid_clusters(None,layers=None,drawings=drs,minlen=100)
        r=reg.register_free(vv,hh) if (len(vv)>=2 or len(hh)>=2) else None
        out[f"{key}:{i+1}"]=r
    print(key,"done",round(time.time()-t0),flush=True)
json.dump(out,open("/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work/reg_all.json","w"),indent=0)
