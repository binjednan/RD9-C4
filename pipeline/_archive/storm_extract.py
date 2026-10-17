# -*- coding: utf-8 -*-
"""Extract site drainage and storm symbols from MECH2 p1 and p27-31, in plan cm."""
import os, sys, json, math, re, collections, itertools
sys.path.insert(0, os.path.dirname(__file__))
import lib, geo

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, 'data', 'storm.json')
PAGES = {'G': 27, '1': 28, 'TY': 29, 'R': 30, 'T': 31}

def r(v): return round(v, 1)
def ly(d): return (d.get('layer') or '').split('$')[-1]
def pos(sh, w): return sh.T(w['x'], w['y'])
def ds(sh, layer, limit):
    for d in sh.D:
        if ly(d) != layer: continue
        for pl in d['polys']:
            w = [sh.T(*p) for p in pl]
            if geo.bbox(w)[0] < limit: yield d, w
def centre(w):
    b=geo.bbox(w); return (r((b[0]+b[2])/2), r((b[1]+b[3])/2))
def unique(points, tol=1):
    out=[]
    for x,y in points:
        if not any(math.dist((x,y), p)<tol for p in out):out.append((x,y))
    return sorted(out)
def inventory(sh, limit):
    out=[]
    for w in sh.words():
        x,y=pos(sh,w);s=w['s']
        if x>=limit:continue
        if s in ('RD','CO','FCO','MH-01','MH-02','MH-03','6"','4"','6"Ø','4"Ø') or 'W.PIPE' in s or s in ('DISCHARGE','discharge','RAIN','6"ØRAIN','4"ØRAIN','CONNECTED'):
            out.append({'text':s,'x':r(x),'y':r(y)})
    return out
def circles(sh, limit):
    pts=[]
    for d,w in ds(sh,'M_DR_RAIN',limit):
        if len(w)==41 and geo.is_closed(w,1.5):
            b=geo.bbox(w)
            if 14<=b[2]-b[0]<=18 and 14<=b[3]-b[1]<=18:pts.append(centre(w))
    return unique(pts)
def label_info(q, x,y, words):
    if not q:return None
    if math.dist((x,y),(q['x'],q['y']))>380:return None
    dia=4 if any(w['text'].startswith('4"') and abs(w['y']-q['y'])<5 and abs(w['x']-q['x'])<240 for w in words) else 6
    return {'text':q['text'],'diameter_in':dia,'distance_cm':r(math.dist((x,y),(q['x'],q['y'])))}
def rain(sh, pg):
    limit=2800
    I=[w for w in inventory(sh,limit) if w['y'] < (2100 if pg==27 else 2000)]; C=circles(sh,limit)
    labels=[w for w in I if 'W.PIPE' in w['text']]
    assert len(labels)==len(C),(pg,len(labels),len(C))
    assignment=min(itertools.permutations(range(len(labels))),
                   key=lambda p:sum(math.dist(C[i],(labels[j]['x'],labels[j]['y'])) for i,j in enumerate(p)))
    grates=unique([centre(w) for d,w in ds(sh,'M_DR_RAIN',limit) if len(w)==21 and 13<min(geo.bbox(w)[2]-geo.bbox(w)[0],geo.bbox(w)[3]-geo.bbox(w)[1])<17 and 28<max(geo.bbox(w)[2]-geo.bbox(w)[0],geo.bbox(w)[3]-geo.bbox(w)[1])<32])
    R=[]; RD=[]
    for i,(x,y) in enumerate(C):
        grate=min((math.dist((x,y),p) for p in grates),default=999)
        lbl=label_info(labels[assignment[i]],x,y,I)
        if grate<70:
            rd=min((w for w in I if w['text']=='RD'),key=lambda w:math.dist((x,y),(w['x'],w['y'])))
            dia=next((int(w['text'][0]) for w in I if w['text'] in ('6"','4"') and abs(w['y']-rd['y'])<5 and abs(w['x']-rd['x'])<60),None)
            assert dia in (4,6),(pg,x,y)
            RD.append({'x':x,'y':y,'diameter_in':dia,'mark':f'RD {dia}"','vertical_label':lbl})
        else:R.append({'x':x,'y':y,'diameter_in':lbl['diameter_in'] if lbl else 6,'label':lbl})
    # Ground-floor dashed pipe runs: classify the drawn 25 cm dash strokes, excluding arrowhead strokes.
    pipes=[]
    if pg==27:
        groups=collections.defaultdict(list)
        for d,w in ds(sh,'M_DR_RAIN',limit):
            if len(w)!=2:continue
            a,b=w; dx=b[0]-a[0];dy=b[1]-a[1];L=math.hypot(dx,dy)
            if not 18<=L<=29:continue
            if abs(dy)<0.5 and abs(a[1]-712.2)<1: key='west'
            elif abs(dx)<0.5 and abs(a[0]-2205.3)<1: key='east'
            elif abs(abs(dx)-abs(dy))<1.5 and 300<a[0]<600:key='southwest'
            elif abs(abs(dx)-abs(dy))<1.5 and 2000<a[0]<2200:key='northeast'
            else:continue
            groups[key].extend((a,b))
        assert set(groups)=={'west','east','southwest','northeast'},groups.keys()
        for k,pts in sorted(groups.items()):
            if k=='west': a,b=min(pts,key=lambda p:p[0]),max(pts,key=lambda p:p[0])
            elif k=='east': a,b=min(pts,key=lambda p:p[1]),max(pts,key=lambda p:p[1])
            else:a,b=min(pts,key=lambda p:p[0]),max(pts,key=lambda p:p[0])
            pipes.append({'kind':'dashed','name':k,'points':[[r(v) for v in a],[r(v) for v in b]],'diameter_cm':15})
        for d,w in ds(sh,'M_DR_RAIN',limit):
            if len(w)==5 and geo.polyline_len(w)>250:
                b=geo.bbox(w)
                if b[0]<0 or b[3]>1800:
                    axis=([[r(b[0]),r((b[1]+b[3])/2)],[r(b[2]),r((b[1]+b[3])/2)]] if b[0]<0
                          else [[r((b[0]+b[2])/2),r(b[1])],[r((b[0]+b[2])/2),r(b[3])]])
                    pipes.append({'kind':'solid','name':'free-discharge-line','points':axis,'diameter_cm':15})
    co=[]
    co_labels=[w for w in I if w['text'] in ('CO','FCO')]
    if pg==27:
        # The sheet legend shows CO as a pipe termination with a perpendicular cap.
        # Five plan caps are split into a four-vertex half-cap plus its opposite stroke;
        # two caps are included in the long free-discharge polylines. Text centres are
        # annotation positions, never component positions.
        for di,d in enumerate(sh.D):
            if ly(d)!='M_DR_RAIN':continue
            for pi,pl in enumerate(d['polys']):
                w=[sh.T(*p) for p in pl]
                if geo.bbox(w)[0]>=limit:continue
                point=None
                if len(w)==4 and math.dist(w[1],w[3])<.1:
                    stem=math.dist(w[0],w[1]);cap=math.dist(w[1],w[2])
                    a=(w[1][0]-w[0][0],w[1][1]-w[0][1]);b=(w[2][0]-w[1][0],w[2][1]-w[1][1])
                    if 18<stem<22 and 6<cap<9 and abs(a[0]*b[0]+a[1]*b[1])/(stem*cap)<.06:point=w[1]
                elif len(w)==5 and geo.polyline_len(w)>250:
                    a=(w[2][0]-w[1][0],w[2][1]-w[1][1]);b=(w[4][0]-w[3][0],w[4][1]-w[3][1])
                    al=math.hypot(*a);bl=math.hypot(*b)
                    if al>200 and 14<bl<17 and abs(a[0]*b[0]+a[1]*b[1])/(al*bl)<.02 and math.dist(w[2],((w[3][0]+w[4][0])/2,(w[3][1]+w[4][1])/2))<.4:point=w[2]
                if point is not None:
                    co.append({'x':r(point[0]),'y':r(point[1]),'mark':'CO','symbol':'نهاية خط بعارضة عمودية كما في مفتاح CLEAN OUT',
                               'source_primitive':[di,pi],'source_pdf_point':[round(v,5) for v in sh.Tinv(*point)],
                               'source_transform':dict(sh.reg),'label':None})
        co.sort(key=lambda q:(q['x'],q['y']))
        assert len(co)==7 and len(co_labels)==6,(len(co),len(co_labels))
        match=min(itertools.permutations(range(len(co)),len(co_labels)),
                  key=lambda p:sum(math.dist((co[j]['x'],co[j]['y']),(co_labels[i]['x'],co_labels[i]['y'])) for i,j in enumerate(p)))
        for i,j in enumerate(match):
            lab=co_labels[i];co[j]['label']=lab
            co[j]['label_distance_cm']=r(math.dist((co[j]['x'],co[j]['y']),(lab['x'],lab['y'])))
            assert co[j]['label_distance_cm']<30,(lab,co[j])
        assert sum(q['label'] is None for q in co)==1
        for q in co:
            if q['label'] is None:q['note']='رمز CLEAN OUT مطابق للمفتاح في المسقط، بلا وسم CO مستقل؛ لم يُستنتج موضعه من قرب الماسورة'
    outlet=[]
    if pg==27:
        for w in I:
            if w['text'].lower()=='discharge':
                # text position is separate from the drawn termination; resolve to the solid-line end.
                x,y=w['x'],w['y']; target=min((p for pipe in pipes if pipe['kind']=='solid' for p in (pipe['points'][0],pipe['points'][-1])),key=lambda p:math.dist((x,y),p))
                q={'x':target[0],'y':target[1],'label_x':x,'label_y':y}
                if not any(math.dist((q['x'],q['y']),(v['x'],v['y']))<5 for v in outlet):outlet.append(q)
    if pg==30:
        for w in I:
            if w['text']!='DISCHARGE':continue
            assert R, 'roof free-discharge label without a riser'
            target=min(R,key=lambda p:math.dist((w['x'],w['y']),(p['x'],p['y'])))
            assert math.dist((w['x'],w['y']),(target['x'],target['y']))<310,(w,target)
            q={'x':target['x'],'y':target['y'],'label_x':w['x'],'label_y':w['y']}
            if not any(math.dist((q['x'],q['y']),(v['x'],v['y']))<5 for v in outlet):outlet.append(q)
        assert len(outlet)==3,outlet
    return {'page':pg,'risers':R,'drains':RD,'pipes':pipes,'cleanouts':co,'outlets':outlet,'label_inventory':I,
            'symbol_counts':{'vertical_circles':len(C),'rd_grates':len(grates),'rd':len(RD),'risers':len(R),'cleanouts':len(co),'cleanout_labels':len(co_labels)}}

def site(sh):
    squares=[]
    for d,w in ds(sh,'M_DR_SP',2700):
        b=geo.bbox(w)
        if len(w)==5 and geo.is_closed(w,1.5) and 55<=b[2]-b[0]<=105 and 55<=b[3]-b[1]<=105 and 1850<b[1]<2050:squares.append((centre(w),r(b[2]-b[0])))
    C=unique([p for p,v in squares]);assert len(C)==3,C
    manholes=[{'mark':f'MH-{i:02d}','x':x,'y':y,'size_cm':100} for i,(x,y) in enumerate(sorted(C,reverse=True),1)]
    wp=[]
    for d,w in ds(sh,'M_DR_WP',2700):
        b=geo.bbox(w)
        if 1900<b[1]<2050 and b[2]-b[0]>80:wp.append(w)
    west=min(p[0] for w in wp for p in w);east=max(p[0] for w in wp for p in w)
    # Filled triangular arrowheads, separate from the narrow double pipe lines.
    arrows=[]
    for d,w in ds(sh,'M_DR_WP',2700):
        b=geo.bbox(w)
        if len(w)==4 and 80<b[2]-b[0]<100 and 35<b[3]-b[1]<50 and 1900<b[1]<2050:
            arrows.append({'x':r(min(p[0] for p in w)),'y':r(sum(p[1] for p in w[:3])/3),'direction':'غرب'})
    assert len(arrows)==2,arrows
    return {'page':1,'manholes':manholes,'pipe_axis':[[r(west),r(C[0][1])],[r(east),r(C[0][1])]],'arrows':sorted(arrows,key=lambda a:a['x']),
            'outlet':{'x':r(west),'y':r(C[0][1]),'note':'TO BE CONNECTED WITH؛ وجهة الربط غير مرسومة'},'label_inventory':inventory(sh,2700)}

def continuity(sheets):
    order=['G','1','2','3','4','5','R','T']
    def symbols(lv):
        sh=sheets['TY' if lv in ('2','3','4','5') else lv]
        return [(v,v.get('label')) for v in sh['risers']]+[(v,v.get('vertical_label')) for v in sh['drains']]
    gaps=[]; mismatches=[]
    for i,lv in enumerate(order):
        for v,label in symbols(lv):
            if not label:continue
            for token,j in (('F/A',i+1),('T/B',i-1)):
                if token not in label['text'] or not 0<=j<len(order):continue
                other=order[j]; cand=[u for u,_ in symbols(other)]
                near=min(cand,key=lambda u:math.dist((v['x'],v['y']),(u['x'],u['y']))) if cand else None
                dist=math.dist((v['x'],v['y']),(near['x'],near['y'])) if near else 1e9
                if dist>25:gaps.append({'from_level':lv,'to_level':other,'x':v['x'],'y':v['y'],'label':label['text'],'distance_cm':r(dist) if near else None})
                elif token=='F/A' and v['diameter_in']!=near['diameter_in']:
                    mismatches.append({'from_level':lv,'to_level':other,'x':v['x'],'y':v['y'],
                                       'diameter_in':v['diameter_in'],'next_diameter_in':near['diameter_in']})
    return gaps,mismatches

def run(out=OUT):
    ref=lib.Sheet('ARCH1',7)
    S=site(lib.Sheet('MECH2',1,ref=ref))
    sheets={lv:rain(lib.Sheet('MECH2',pg,ref=ref),pg) for lv,pg in PAGES.items()}
    assert len(S['manholes'])==3
    assert len(sheets['R']['drains'])==4 and len(sheets['T']['drains'])==4
    assert sum(w['text'].startswith('MH-') for w in S['label_inventory'])==3
    assert [sum('W.PIPE' in w['text'] for w in sheets[k]['label_inventory']) for k in ('G','1','TY')]==[5,5,4]
    assert [sum(w['text']=='RD' for w in sheets[k]['label_inventory']) for k in ('R','T')]==[4,4]
    assert len(sheets['G']['outlets'])==2 and len(sheets['R']['outlets'])==3
    gaps,mismatches=continuity(sheets)
    assert len(gaps)==1 and len(mismatches)==1,(gaps,mismatches)
    D={'site':S,'sheets':sheets,'continuity_gaps':gaps,'diameter_mismatches':mismatches,'units':'cm','source':'MECH2 ص1 وص27–31'}
    os.makedirs(os.path.dirname(out),exist_ok=True)
    with open(out,'w',encoding='utf-8') as f:json.dump(D,f,ensure_ascii=False,indent=2)
    print('storm extract:',{lv:{k:len(v) for k,v in s.items() if isinstance(v,list) and k!='label_inventory'} for lv,s in sheets.items()},'site manholes',len(S['manholes']),'arrows',len(S['arrows']),'continuity gaps',len(gaps),'diameter mismatches',len(mismatches))
    return D
if __name__=='__main__':run()
