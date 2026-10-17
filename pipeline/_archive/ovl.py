import sys, json, hashlib
sys.path.insert(0,"/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work")
import lib, fitz
from PIL import Image, ImageDraw
def color(c):
    if c is None: return (255,0,0)
    h=int(hashlib.md5(c.encode()).hexdigest()[:6],16)
    return (60+(h>>16)%160,40+(h>>8)%140,40+h%160)
def overlay(key,fam,lv,out,crop=None,sc=1.0,page=None):
    R=json.load(open("/private/tmp/claude-501/-Users-binqdair/9a1652f3-ec18-4d97-b6e3-2745ee0d2f2c/scratchpad/work/data/elec_inst.json"))
    rec=R[f"{fam}|{lv}"]
    ref=lib.Sheet("ARCH1",7)
    pn=int(rec["sheet"].split("p")[-1]); K=rec["sheet"].split()[0]
    sh=lib.Sheet(K,pn,ref=ref)
    pg=lib.doc(K)[pn-1]
    pix=pg.get_pixmap(matrix=fitz.Matrix(sc,sc),alpha=False)
    im=Image.frombytes("RGB",(pix.width,pix.height),pix.samples); dd=ImageDraw.Draw(im)
    for i in rec["inst"]:
        px,py=sh.Tinv(i["x"],i["y"])
        c=color(i["c"])
        r=max(i["w"],i["h"])/sh.reg["s"]/2+3
        dd.rectangle([(px-r)*sc,(py-r)*sc,(px+r)*sc,(py+r)*sc],outline=c,width=2 if i["c"] is None else 1)
        dd.text(((px-r)*sc,(py-r-11)*sc),i["c"] or "?",fill=c)
    if crop: im=im.crop(crop)
    im.save(out)
    print(out,im.size)
if __name__=="__main__":
    fam,lv=sys.argv[1],sys.argv[2]; key=sys.argv[3]
    crop=tuple(int(v) for v in sys.argv[5].split(",")) if len(sys.argv)>5 else None
    overlay(key,fam,lv,sys.argv[4],crop)
