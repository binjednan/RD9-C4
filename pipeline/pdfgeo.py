import fitz, math, collections
from PIL import Image, ImageDraw

def flat_items(dr, seg_per_curve=8):
    """Return list of polylines (list of (x,y)) for a drawing dict."""
    polys=[]
    cur=[]
    for it in dr["items"]:
        op=it[0]
        if op=="l":
            p1,p2=it[1],it[2]
            if cur and abs(cur[-1][0]-p1.x)<1e-6 and abs(cur[-1][1]-p1.y)<1e-6:
                cur.append((p2.x,p2.y))
            else:
                if cur: polys.append(cur)
                cur=[(p1.x,p1.y),(p2.x,p2.y)]
        elif op=="c":
            p1,c1,c2,p2=it[1],it[2],it[3],it[4]
            pts=[]
            for i in range(1,seg_per_curve+1):
                t=i/seg_per_curve
                x=(1-t)**3*p1.x+3*(1-t)**2*t*c1.x+3*(1-t)*t*t*c2.x+t**3*p2.x
                y=(1-t)**3*p1.y+3*(1-t)**2*t*c1.y+3*(1-t)*t*t*c2.y+t**3*p2.y
                pts.append((x,y))
            if cur and abs(cur[-1][0]-p1.x)<1e-6 and abs(cur[-1][1]-p1.y)<1e-6:
                cur.extend(pts)
            else:
                if cur: polys.append(cur)
                cur=[(p1.x,p1.y)]+pts
        elif op=="re":
            r=it[1]
            if cur: polys.append(cur); cur=[]
            polys.append([(r.x0,r.y0),(r.x1,r.y0),(r.x1,r.y1),(r.x0,r.y1),(r.x0,r.y0)])
        elif op=="qu":
            q=it[1]
            if cur: polys.append(cur); cur=[]
            polys.append([(q.ul.x,q.ul.y),(q.ur.x,q.ur.y),(q.lr.x,q.lr.y),(q.ll.x,q.ll.y),(q.ul.x,q.ul.y)])
    if cur: polys.append(cur)
    return polys

def layer_summary(page):
    dr=page.get_drawings()
    c=collections.Counter()
    for d in dr: c[d.get("layer")]+=1
    return c

def render(page, layers=None, bbox=None, scale=1.0, out="out.png", exclude=None, fills=True, width_scale=1.0, bg=(255,255,255)):
    """Render drawings of selected layers to PNG using PIL. bbox in PDF pts (x0,y0,x1,y1)."""
    dr=page.get_drawings()
    if bbox is None: bbox=(0,0,page.rect.width,page.rect.height)
    x0,y0,x1,y1=bbox
    W=int((x1-x0)*scale); H=int((y1-y0)*scale)
    im=Image.new("RGB",(W,H),bg)
    dd=ImageDraw.Draw(im)
    def tp(p): return ((p[0]-x0)*scale,(p[1]-y0)*scale)
    for d in dr:
        ly=d.get("layer")
        if layers is not None and ly not in layers: continue
        if exclude and ly in exclude: continue
        col=d.get("color"); fil=d.get("fill")
        w=max(1,int(round((d.get("width") or 0.5)*scale*width_scale)))
        polys=flat_items(d)
        for pl in polys:
            pts=[tp(p) for p in pl]
            if fills and fil is not None and len(pts)>=3:
                try: dd.polygon(pts, fill=tuple(int(c*255) for c in fil))
                except: pass
            if col is not None and len(pts)>=2:
                dd.line(pts, fill=tuple(int(c*255) for c in col), width=w)
            elif fil is None and len(pts)>=2:
                dd.line(pts, fill=(0,0,0), width=w)
    im.save(out)
    return im
