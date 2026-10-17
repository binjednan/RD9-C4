# -*- coding: utf-8 -*-
"""Extract drawn WS-010 and IR-100/101 geometry; schemas remain information only."""
import os, json, math, collections
import lib, geo

HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, 'data', 'water_site.json')
PAGES = (17, 22, 23, 24, 25, 26)

def rnd(v): return round(v, 1)
def xy(v): return [rnd(q) for q in v]
def bounds(w): return [rnd(q) for q in geo.bbox(w)]
def centre(w):
    b = geo.bbox(w)
    return xy(((b[0]+b[2])/2, (b[1]+b[3])/2))
def entries(sh, layer):
    for i, d in enumerate(sh.D):
        if d['layer'] != layer: continue
        for j, pl in enumerate(d['polys']):
            yield i, j, d, [sh.T(*p) for p in pl], pl
def item(sh, i, j, w, raw):
    return {'page': sh.pageno, 'primitive': [i,j], 'points': [xy(p) for p in w],
            'pdf_points': [[round(q,5) for q in p] for p in raw], 'source_transform': dict(sh.reg),
            'source_graphic_colour_rgb': sh.D[i].get('color')}
def texts(sh):
    return [{'text':w['s'], 'x':rnd(w['X']), 'y':rnd(w['Y']), 'layer':w['layer']}
            for w in sh.words() if w['X']<1600 and w['Y']<3600 and
            w['layer'] in ('M_WS_TEXT','WS TEXT','MECH')]
def dedup(rows):
    out=[]
    for q in rows:
        if not any(q.get('centre')==p.get('centre') and q.get('bounds')==p.get('bounds') for p in out):out.append(q)
    return sorted(out, key=lambda p:(p.get('centre') or p['points'][0]))

def site(sh):
    assert sh.reg['nx']==17 and sh.reg['ny']==11 and 5.30<sh.reg['s']<5.32, sh.reg
    pipes=[]; meters=[]; fills=[]; chambers=[]; tanks=[]; cabinet=[]
    for i,j,d,w,raw in entries(sh,'M_WS_CW'):
        b=geo.bbox(w); L=geo.polyline_len(w)
        if b[0]>1600 or b[3]>2500:continue
        q=item(sh,i,j,w,raw)
        if not geo.is_closed(w,1) and len(w)<=5 and L>=25:
            q['diameter_mm']=50; pipes.append(q)
        if len(w)==41 and geo.is_closed(w,1):
            width=b[2]-b[0]; depth=b[3]-b[1]
            if 18<width<19 and 18<depth<19:
                q.update(centre=centre(w), diameter_cm=rnd(width));meters.append(q)
            elif 9<width<10 and 9<depth<10:
                q.update(centre=centre(w), diameter_mm=50);fills.append(q)
        if len(w)==5 and geo.is_closed(w,1):
            if 59<b[2]-b[0]<61 and 59<b[3]-b[1]<61 and b[0]<0:
                q.update(centre=centre(w),bounds=bounds(w),size_cm=[60,60,50]);chambers.append(q)
            if 299<b[2]-b[0]<301 and 249<b[3]-b[1]<251 and b[3]<350:
                q.update(centre=centre(w),bounds=bounds(w),size_cm=[300,250,200]);tanks.append(q)
    # M.B frame is composed of eight filled triangular corner polygons, not eight pipes.
    corners=[]
    for i,j,d,w,raw in entries(sh,'M_WS_CW'):
        b=geo.bbox(w)
        if len(w)==4 and 325<b[0]<400 and 1560<b[1]<1610 and 'f' in d['type']:corners.extend(w)
    assert corners, 'meter box frame missing'
    cb=geo.bbox(corners)
    cabinet={'page':17,'bounds':[rnd(v) for v in cb], 'centre':xy(((cb[0]+cb[2])/2,(cb[1]+cb[3])/2)),
             'source_transform':dict(sh.reg), 'pdf_points':[[round(q,5) for q in sh.Tinv(cb[0],cb[1])],[round(q,5) for q in sh.Tinv(cb[2],cb[3])]]}
    pipes.sort(key=lambda p: p['points']);meters=dedup(meters);fills=dedup(fills);chambers=dedup(chambers);tanks=dedup(tanks)
    T=texts(sh)
    meter_labels=[w for w in T if w['text']=='M' and 300<w['x']<380 and 1000<w['y']<1550]
    assert len(pipes)==10 and len(meters)==len(meter_labels)==4 and len(fills)==4 and len(chambers)==1 and len(tanks)==2, (len(pipes),len(meters),len(fills),len(chambers),len(tanks))
    roof_labels=sum(w['text'] in ('RAW','FILTERED') for w in T)
    assert roof_labels==len(tanks), (roof_labels,len(tanks))
    return {'page':17,'pipes':pipes,'meters':meters,'fill_drops':fills,'chambers':chambers,'tanks':tanks,'cabinet':cabinet,
            'label_inventory':T,'independent_counts':{'M_labels':len(meter_labels),'M_symbols':len(meters),'M_B_labels':sum(w['text']=='M.B' for w in T),'M_H_labels':sum(w['text']=='M.H' for w in T),'chambers':len(chambers),'roof_tank_labels':roof_labels,'roof_tank_rectangles':len(tanks)}}

def irrigation(basement, ground):
    pipes=[]; closed=[]; fill=[]
    for i,j,d,w,raw in entries(basement,'M_WS_CW'):
        b=geo.bbox(w);L=geo.polyline_len(w)
        if b[0]>1600 or b[3]>3500:continue
        q=item(basement,i,j,w,raw)
        if not geo.is_closed(w,1) and ((len(w)==4 and L>2000) or (len(w)==2 and abs(w[0][0]-w[1][0])<.5 and 70<L<100 and 645<b[0]<667)):
            q.update(diameter_mm=50);pipes.append(q)
        if len(w)==5 and geo.is_closed(w,1) and 18<b[2]-b[0]<20 and 15<b[3]-b[1]<17 and 600<b[0]<640 and 1590<b[1]<1700:
            q.update(centre=centre(w),bounds=bounds(w));closed.append(q)
        if len(w)==41 and 658<b[0]<660 and 1510<b[1]<1516:
            q.update(centre=centre(w),diameter_mm=50);fill.append(q)
    closed=sorted(closed,key=lambda v:v['centre'][1])
    # The closed rectangle identifies each motor; extend only to the actual outer pump strokes.
    pumps=[]
    for c in closed:
        cy=c['centre'][1];P=[]
        for i,j,d,w,raw in entries(basement,'M_WS_CW'):
            b=geo.bbox(w)
            if 580<b[0]<655 and b[2]<655 and cy-18<b[1] and b[3]<cy+18:P.extend(w)
        assert P
        b=geo.bbox(P)
        pumps.append({'page':25,'centre':xy(((b[0]+b[2])/2,(b[1]+b[3])/2)), 'bounds':bounds(P),
                      'source_transform':dict(basement.reg),'pdf_points':[[round(q,5) for q in basement.Tinv(b[0],b[1])],[round(q,5) for q in basement.Tinv(b[2],b[3])]],
                      'flow_gpm':45,'pressure_bar':4,'power_kw':2.2,'duty':'تشغيل' if len(pumps)==0 else 'احتياط'})
    gp=[];chamber=[]
    for i,j,d,w,raw in entries(ground,'M_WS_CW'):
        b=geo.bbox(w);q=item(ground,i,j,w,raw)
        if b[0]>1600 or b[3]>3500:continue
        if len(w)==2 and not geo.is_closed(w,1) and geo.polyline_len(w)>250:
            q['diameter_mm']=50;gp.append(q)
        if len(w)==5 and geo.is_closed(w,1) and 59<b[2]-b[0]<61 and 59<b[3]-b[1]<61:
            q.update(centre=centre(w),bounds=bounds(w),size_cm=[60,60,50]);chamber.append(q)
    T=texts(basement);G=texts(ground)
    pump_labels=sum(w['text']=='PUMP' and w['layer']=='MECH' for w in T)
    capacities=[t['s'] for t in basement.texts() if 900<t['X']<1600 and 1610<t['Y']<1745 and 'STANDBY' in t['s']]
    assert len(capacities)==1 and '1 DUTY/1 STANDBY' in capacities[0],capacities
    assert len(pipes)==4 and len(pumps)==2 and len(gp)==1 and len(chamber)==1, (len(pipes),len(pumps),len(gp),len(chamber))
    end=max(pipes,key=lambda v:geo.polyline_len(v['points']))['points'][-1]
    gend=max(gp[0]['points'],key=lambda p:p[0])
    gap=round(math.dist(end,gend),1)
    return {'basement_page':25,'ground_page':26,'pipes':sorted(pipes,key=lambda v:v['points']),'pumps':pumps,'suction_points':fill,'ground_pipes':gp,'chambers':chamber,
            'label_inventory':{'B':T,'G':G}, 'capacity_notes':capacities,'independent_counts':{'pump_set_labels':pump_labels,'duty_and_standby':2,'pump_symbols':len(pumps),'50_diameter_labels_B':sum(w['text']=='50Ø' for w in T),'M_H_labels_G':sum(w['text']=='M.H' for w in G),'M_H_symbols_G':len(chamber)},
            'riser_plan_gap':{'B_point':end,'G_pipe_end':gend,'distance_cm':gap,'note':'نقطة T/A بالبدروم داخل غرفة الأرضي لكن محوري الخطين يختلفان؛ لم ينشأ مسار إزاحة بينهما'}}

def run(out=OUT):
    ref=lib.Sheet('ARCH1',7)
    sheets={p:lib.Sheet('MECH2',p,ref=ref) for p in PAGES}
    S=site(sheets[17]);I=irrigation(sheets[25],sheets[26])
    cross=[]
    for t in S['tanks']:
        choices=[]
        for i,j,d,w,raw in entries(sheets[22],'M_WS_CW'):
            b=geo.bbox(w)
            if len(w)==5 and 299<b[2]-b[0]<301 and 249<b[3]-b[1]<251:
                choices.append(centre(w))
        n=min(choices,key=lambda v:math.dist(t['centre'],v));cross.append({'site':t['centre'],'roof':n,'delta_cm':round(math.dist(t['centre'],n),1)})
    assert max(q['delta_cm'] for q in cross)<=.8,cross
    info={}
    for p in (23,24):
        assert sheets[p].reg is None, ('schematic unexpectedly registered',p)
        info[str(p)]={'kind':'مخطط رأسي' if p==23 else 'تفاصيل تركيب','spatial_geometry':False,
                     'specifications':[t['s'] for t in sheets[p].texts() if any(k in t['s'].upper() for k in ('PUMP','TANK','METER','CAPACITY','INSTALLATION','DETAIL'))]}
    D={'units':'cm','source':'MECH2 ص17 وص23–26؛ تأكيد موضع خزانات السطح ص22','site':S,'irrigation':I,'roof_tank_alignment':cross,'information_sheets':info,
       'model_errors':[{'ids':['P.cold-R-M0025','P.cold-R-M0026','P.cold-R-M0027','P.cold-R-M0028'],'reason':'حدود خزانات وإطاراتها مستخرجة خطأ كمواسير 22 مم؛ تستبدل بالخزانين في موضعيهما الحقيقيين'}]}
    os.makedirs(os.path.dirname(out),exist_ok=True)
    with open(out,'w',encoding='utf-8') as f:json.dump(D,f,ensure_ascii=False,indent=2)
    print('water site extraction',S['independent_counts'],I['independent_counts'],'alignment',cross,'riser gap',I['riser_plan_gap'])
    return D

if __name__=='__main__':run()
