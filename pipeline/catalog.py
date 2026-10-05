import sys, collections, math, re, json
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import lib, symbols as SY
import fitz
from PIL import Image, ImageDraw

def build_catalog(key, page, ref_page, layers, out_png, topn=48, maxdim=60, q=0.22, plan_box=None, gap=0.5):
    ref=lib.Sheet("ARCH1",ref_page)
    sh=lib.Sheet(key,page,ref=ref) if key!="ARCH1" else lib.Sheet(key,page)
    prims=SY.prim_list(sh,layers,maxdim_pt=maxdim)
    groups=SY.cluster_prims(prims,gap=gap)
    S=collections.defaultdict(list)
    for ids in groups:
        inf=SY.group_info(prims,ids)
        sig=SY.signature_norm(prims,ids,q=q)
        S[sig].append((inf,ids))
    ranked=sorted(S.items(),key=lambda kv:-len(kv[1]))[:topn]
    doc=lib.doc(key); pg=doc[page-1]
    cell=170; cols=8; rows=(len(ranked)+cols-1)//cols
    im=Image.new("RGB",(cols*cell,rows*cell),(255,255,255)); dd=ImageDraw.Draw(im)
    cat=[]
    for k,(sig,lst) in enumerate(ranked):
        inf,ids=lst[0]
        c=inf["c"]; half=max(inf["w"],inf["h"])*0.5+8
        clip=fitz.Rect(c[0]-half,c[1]-half,c[0]+half,c[1]+half)
        sc=(cell-30)/(2*half)
        pix=pg.get_pixmap(matrix=fitz.Matrix(sc,sc),clip=clip,alpha=False)
        t=Image.frombytes("RGB",(pix.width,pix.height),pix.samples)
        x=(k%cols)*cell+8; y=(k//cols)*cell+18
        im.paste(t,(x,y))
        dd.rectangle([(k%cols)*cell,(k//cols)*cell,(k%cols)*cell+cell-1,(k//cols)*cell+cell-1],outline=(200,200,200))
        r=sh.reg["s"]
        dd.text(((k%cols)*cell+4,(k//cols)*cell+3),f"#{k} n={len(lst)} {round(inf['w']*r)}x{round(inf['h']*r)}cm p{inf['n']}",fill=(200,0,0))
        cat.append({"id":k,"count":len(lst),"w_cm":round(inf["w"]*r,1),"h_cm":round(inf["h"]*r,1),"nprim":inf["n"],"sig":repr(sig),"example_pt":[round(c[0],1),round(c[1],1)]})
    im.save(out_png)
    return cat, sh

if __name__=="__main__":
    SP="/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/img/"
    cat,sh=build_catalog("ELEC1",4,7,("E.LIGHT","ELE.LIGHT"),SP+"cat_light.png",topn=48)
    print(len(cat))
