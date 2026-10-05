# -*- coding: utf-8 -*-
"""electrical symbol extraction (raster-matched against each sheet's own legend) -> data/elec_inst.json"""
import sys, json, collections, math, re, pickle, os
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import lib, symbols as SY, ras, kb_elec as K, mep_common as MC

OUT="/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work/data/elec_inst.json"
LIGHT_LAYERS=("E.LIGHT","ELE.LIGHT")
POWER_LAYERS=("E.POWER","POWER")
FA_LAYERS=("FIRE ALARM",)
LC_LAYERS=("S.M.A TV","LOW CURRENT","ACCESS CONTROL","CCTV")
TEL_LAYERS=("TELEPHONE",)
LTG_LAYERS=("Down conductor","ACCESSORIES","LIGHT PROTECTION")

LIGHT_SPECS=[("L1",277,1345),("L2",276,1361),("L4",277,1394),("L5",276,1419),("L6",276,1446),("L7",277,1468),("L8",276,1485),("L9",276,1503),("L10",276,1522),("L11",276,1539),("L12",276,1559),("L13",277,1583),
 ("S1",618,1347),("S2",618,1364),("S3",618,1382),("S4",618,1398),("S5",618,1416),("S6",618,1435),("S7",616,1454),("S8",617,1469),("S9",615,1481),("S10",623,1492),("S11",618,1504)]

def exemplars_light(ref):
    sh=lib.Sheet("ELEC1",4,ref=ref)
    specs=[{"label":l,"x":x,"y":y,"r":3.0} for l,x,y in LIGHT_SPECS]
    ex,used=ras.build_exemplars(sh,LIGHT_LAYERS,specs,maxdim=70)
    return ex,used
def exemplars_by_legend(ref,key,page,layers,regions,rules,maxdim=70,extra=None):
    sh=lib.Sheet(key,page,ref=ref)
    leg=SY.build_legend(sh,layers,regions,text_layers=None,ywin=7.0,maxdim=maxdim)
    specs=[]
    for t,sig,g in leg:
        cid=K.map_label(rules,t.replace(" Apr 12, 2022","").strip())
        if cid: specs.append({"label":cid,"x":g["c"][0],"y":g["c"][1],"r":2.5})
    ex,used=ras.build_exemplars(sh,layers,specs,maxdim=maxdim)
    return ex,used

LC_MAP=[(r'T\.V OUTLET',"T1"),(r'T\.V JUNCTION',"T2"),(r'MULTI SWITCHER',"T3"),(r'DISH',"T4"),(r'AUDIO VIDEO INTERCOM SPOT|SINGLE SWITCH',"T5"),(r'AUDIO VIDEO INTERCOM',"T6"),
 (r'PROXIMITY',"T7"),(r'DOOR CONTACT',"T8"),(r'MAGNETIC LOCK',"T9"),(r'EXIT PUSH',"T10"),(r'ACCESS CONTROL JUNCTION',"T11"),(r'FIXED IP CAMERA',"T12"),(r'W/P IP CAMERA',"T13"),(r'VIDEO DIGITAL RECORDER',"T14")]
TEL_MAP=[(r'RJ45 SINGLE',"T16"),(r'RJ45 DUAL',"T17"),(r'FLOOR BOX',"P11"),(r'OPTICAL NETWORK UNIT',"T18"),(r'MINI OPTICAL',"T19"),(r'MAIN DISTRIBUTION FRAME',"T20")]
LTG_MAP=[(r'COPPER TAPE',"G1"),(r'TAPE CLIP',"G2"),(r'EARTH INSPECTION',"G3"),(r'AIR TERMINAL',"G4")]

PAGES={
 "light":("ELEC1",LIGHT_LAYERS,{"B":1,"G":2,"1":3,"TY":4,"R":5,"T":6}),
 "power":("ELEC1",POWER_LAYERS,{"S":8,"B":9,"G":10,"1":11,"TY":12,"R":13,"T":14}),
 "fa":("ELEC2",FA_LAYERS,{"B":2,"G":3,"1":4,"TY":5,"R":6}),
 "lc":("ELEC2",LC_LAYERS,{"B":18,"G":19,"1":20,"TY":21,"R":22,"T":23}),
 "tel":("ELEC2",TEL_LAYERS,{"B":28,"G":29,"1":30,"TY":31,"R":32}),
 "ltg":("ELEC2",LTG_LAYERS,{"B":11,"G":12,"1":13,"TY":14,"R":15,"T":16}),
}
def legend_rects(sh):
    return [(w["x"]-70,w["y"]-35,w["x"]+360,w["y"]+330) for w in sh.WD if "LEGEND" in w["s"].upper() and w["x"]<2200]

def run(save=True):
    ref=lib.Sheet("ARCH1",7)
    EX={}
    EX["light"],u1=exemplars_light(ref)
    EX["power"],u2=exemplars_by_legend(ref,"ELEC1",12,POWER_LAYERS,[(360,1405,620,1610),(625,1405,900,1610)],K.POWER_MAP,maxdim=60)
    EX["fa"],u3=exemplars_by_legend(ref,"ELEC2",5,FA_LAYERS,[(660,1385,925,1545),(925,1385,1165,1545),(1165,1385,1450,1545)],K.FA_MAP,maxdim=70)
    EX["lc"],u4=exemplars_by_legend(ref,"ELEC2",21,LC_LAYERS+("0",),[(940,1425,1120,1480),(1125,1425,1330,1480),(940,1490,1120,1575),(1125,1490,1330,1575)],LC_MAP,maxdim=90)
    EX["tel"],u5=exemplars_by_legend(ref,"ELEC2",31,TEL_LAYERS,[(985,1462,1340,1590)],TEL_MAP,maxdim=70)
    EX["ltg"],u6=exemplars_by_legend(ref,"ELEC2",14,LTG_LAYERS,[(1040,1555,1330,1640)],LTG_MAP,maxdim=70)
    print("exemplars",{k:len(v) for k,v in EX.items()})
    res={}
    for fam,(key,layers,pg) in PAGES.items():
        for lv,page in pg.items():
            sh=lib.Sheet(key,page,ref=ref)
            if sh.reg is None: print("skip (no registration)",fam,lv,page); continue
            lr=legend_rects(sh)
            skip=lambda x,y,lr=lr: x>=2040 or any(r[0]<=x<=r[2] and r[1]<=y<=r[3] for r in lr)
            maxd=60 if fam!="ltg" else 40
            inst,prims=ras.classify(sh,layers,EX[fam],maxdim=maxd,thr=0.76,skip=skip,size_tol=(0.0,1e9))
            rec=[]
            for i in inst:
                if (i["w"]<2.5 and i["h"]<2.5): continue
                rec.append({"x":round(i["x"],1),"y":round(i["y"],1),"w":round(i["w"],1),"h":round(i["h"],1),"n":i["n"],"c":i["label"],"sc":round(float(i["score"]),2),"b":i["best"]})
            res[f"{fam}|{lv}"]={"sheet":f"{key} p{page}","s":round(sh.reg["s"],3),"inst":rec}
            c=collections.Counter(r["c"] for r in rec)
            print(fam,lv,f"{key} p{page}","s",round(sh.reg["s"],2),"n",len(rec),"unclassified",c.get(None,0),dict(sorted((k,v) for k,v in c.items() if k)))
    if save: json.dump(res,open(OUT,"w"),separators=(",",":"))
    return res

if __name__=="__main__":
    run()
