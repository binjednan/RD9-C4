"""Floor analysis wrapper: walls, doors, rooms, flats + unit lookup, per architectural plan page."""
import sys, math, json, collections, re, pickle, os
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work".replace("2745ee0d2f2c","2745ee0d2f2c"))
import numpy as np
import lib, cellgrid, arch_floor as AF, build_arch as BA, geo

D="/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work/data/"

FLAT_INFO={  # official unit schedule from typical floor plan labels (A104): flat no -> (bedrooms, gross area m2)
 1:(2,92.10),2:(1,60.20),3:(2,88.0),4:(2,89.0),5:(1,57.80),6:(2,96.20)}

class FloorMap:
    def __init__(self,pn,hvac_page=None,gmax=140):
        self.pn=pn
        self.r=BA.analyze(pn)
        self.sh=self.r["sh"]; self.g=self.r["g"]; self.g2=self.r["g2"]
        self.rooms=BA.build_rooms(self.r,pn)
        self.comp_room={rm["comp"]:rm for rm in self.rooms}
        self.uf,self.groups=BA.flats_of(self.r,pn,self.rooms)
        self.flat_of_comp={}
        self.flats={}
        self.hvac_page=hvac_page
        if hvac_page: self._flats_from_fcu(hvac_page)
    def _flats_from_fcu(self,hp):
        msh=lib.Sheet("MECH1",hp)
        fcus=[w for w in msh.words(layer="M_HVAC_TEXT") if re.match(r'^FCU-',w["s"])]
        votes=collections.defaultdict(collections.Counter)
        for f in fcus:
            m=re.match(r'^FCU-\w+-(\d)\.\d$',f["s"])
            if not m: continue
            c=AF.cell_of(self.g2,f["X"],f["Y"])
            if c is None: continue
            votes[self.uf.f(c)][int(m.group(1))]+=1
        for root,cn in votes.items():
            no=cn.most_common(1)[0][0]
            comps=[rm["comp"] for rm in self.groups[root]]
            self.flats[no]={"no":no,"comps":comps,"area":sum(rm["area_m2"] for rm in self.groups[root])}
            for c in comps: self.flat_of_comp[c]=no
    def comp_at(self,x,y): return AF.cell_of(self.g2,x,y)
    def flat_at(self,x,y,search=True):
        c=self.comp_at(x,y)
        if c is not None and c in self.flat_of_comp: return [self.flat_of_comp[c]]
        if not search: return []
        found=[]
        for rad in (14,30,48):
            for k in range(8):
                a=k*math.pi/4
                c2=self.comp_at(x+rad*math.cos(a),y+rad*math.sin(a))
                if c2 in self.flat_of_comp:
                    f=self.flat_of_comp[c2]
                    if f not in found: found.append(f)
            if found: break
        return found[:2]
    def wall_rects(self):
        return self.g.rects(self.r["mask"])

if __name__=="__main__":
    fm=FloorMap(7,hvac_page=4)
    print({k:(round(v["area"],1),len(v["comps"])) for k,v in fm.flats.items()})
    print(fm.flat_at(300,1500), fm.flat_at(1600,1500), fm.flat_at(1600,900))
