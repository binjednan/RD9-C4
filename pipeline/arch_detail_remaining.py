# -*- coding: utf-8 -*-
"""A102/A105 source positions and A2100/A1800 details; stable AD suffix.

The extracted PDF geometry lives in arch_struct_review.json. No registration or
S.* geometry is changed. A1800's height/material conflicts remain explicit.
"""
import collections
import copy
import json
import math
import os
import re
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
from source_support import footprint
from support import zr

DATA=os.path.join(os.path.dirname(__file__),"data","arch_struct_review.json")
ID_RE=re.compile(r"-AD\d{4}$")
MATS={
 "ad_solid_wood":{"name":"خشب صلب مكتب الاستقبال — A2100","color":"#99774f","rough":.65},
 "ad_chrome_gold":{"name":"CHROME GOLD — مكتب الاستقبال A2100","color":"#b8a167","metal":.8,"rough":.22},
 "ad_ladder_metal":{"name":"تمثيل معدني سلّم A1800 — وصف stainless/galvanized متعارض","color":"#aab2b5","metal":.65,"rough":.35},
 "ad_mirror":{"name":"مرآة دخول الأرضي — A1600 قطاع D–D","color":"#c1ccd2","metal":.95,"rough":.03},
}
TYPES={
 "reception_counter_wood":{"n":"مكتب الاستقبال — خشب صلب","cf":"doc","sp":[["الموضع","A102: x1410.2–1474.5،y1351.1–1509.4 سم"],["المقاس التفصيلي","158×64 سم خارجي؛ 150×60 سم داخلي"],["قطاع A2100","سطح العمل80 سم؛ إجمالي واجهة الاستقبال90 سم؛ ألواح68 سم بين إطارات5/2/5 سم"]],"sr":["ARCH1 ص5 A102","ARCH2 ص43 A2100"],"asm":["عمق جلد الخشب2 سم افتراض؛ لا مسامير أو وصلات توريد معتمدة"]},
 "reception_counter_gold":{"n":"مكتب الاستقبال — حافة CHROME GOLD","cf":"doc","sp":[["الواجهة الذهبية","من75 إلى90 سم في القطاع A–A"],["المادة","CHROME GOLD من النص"]],"sr":["ARCH2 ص43 A2100"],"asm":["سماكة الغلاف2 سم افتراض؛ الغطاء مفرغ،وليس كتلة مصمتة15سم"]},
 "reception_counter_slat":{"n":"شريحة خشب واجهة مكتب الاستقبال","cf":"derived","sp":[["الموضع/العرض","شرائط رمز المسقط في A02_FURNITURE_FIXED"],["الارتفاع","68سم من A2100"]],"sr":["ARCH1 ص5 A102","ARCH2 ص43 A2100"],"asm":["عمق الشريحة1 سم افتراض"]},
 "cat_ladder_side":{"n":"سلّم CAT LADDER — جانب زاوية","cf":"doc","sp":[["زاوية الجانب","7.5×7.5×0.9سم من callout"],["المناسيب التفصيلية","R+23.35 → A1800 TOP+27.25؛ امتداد جانبي50سم"],["التعارض","A106: FFL+26.85/T.OP+27.25؛ A1800: FFL+27.25"]],"sr":["ARCH1 ص8–9 A105/A106","ARCH2 ص37 A1800"],"asm":["مادة العنوان STAINLESS خلاف GALVANIZED في callouts؛ لا اعتماد مادة توريد"]},
 "cat_ladder_rung":{"n":"سلّم CAT LADDER — درجة","cf":"doc","sp":[["القطر","2سم من callout"],["التوزيع","12درجة؛ أولها40سم فوق R،كل30سم،الأخيرة20سم تحت+27.25"]],"sr":["ARCH2 ص37 A1800","ARCH1 ص8 A105"],"asm":["عرض المسقط وموقعه من الرسم؛ وصف stainless/galvanized متعارض"]},
 "cat_ladder_mount":{"n":"تثبيت سلّم CAT LADDER المرسوم","cf":"derived","sp":[["لوحة القاعدة","100×100×8مم من التفصيل5"],["الوصلة","أنبوب30مم ملحوم إلى القاعدة من النص"]],"sr":["ARCH2 ص37 A1800 détails5/6"],"asm":["مركز مستويَي التثبيت قرئ من الواجهة غير المرقمة؛ يتطلب اعتماد shopdrawing"]},
 "lobby_W7_detail":{"n":"كسوة W7 لوجهي ردهة البدروم الجانبيين","cf":"doc","sp":[["المادة","20مم polished white travertine،1200×600مم"],["حدود التنفيذ في المجسم","وجهان جانبيان فقط،على أجزاء الجدار الموجودة؛ الارتفاع225سم من القطاع A–A"]],"sr":["ARCH1 ص4 A101","ARCH2 ص34 A1600 قطاع A–A"],"asm":["تقسيم البلاطات والمونة والوصلات غير مجسّم؛ W13 وواجهات الردهة الأخرى باقية للمراجعة"]},
 "corridor_W7_detail":{"n":"كسوة W7 لواجهات الممر المحددة","cf":"doc","sp":[["المادة","20مم polished white travertine،1200×600مم"],["النطاق","الأول والأدوار2–5؛ A–A وطرفا B–B وC–C مع استثناء لوح W13"],["الارتفاع","235سم من قطاع A1601؛ فتحات المصاعد والأبواب محفوظة"]],"sr":["ARCH1 ص6–7 A103/A104","ARCH2 ص35 A1601"],"asm":["الكسوة مشتقة من وجوه الجدار الموجودة؛ تقسيم البلاطات والمونة والتثبيت غير مجسّم؛ عمق رجوع اللوح في C–C غير مرقم"]},
 "corridor_W13_detail":{"n":"لوح W13 لرقم الطابق","cf":"doc","sp":[["المادة","20مم Granite Type02،600×600مم"],["الموضع","قطاع C–C معكوس جهة النظر؛ الربط مثبت بأربعة إطارات أبواب فعلية"],["الحدود","الوجه المركزي بين الخطين491.42/593.48 نقطةPDF؛ ارتفاع235سم"]],"sr":["ARCH2 ص35 A1601 قطاع C–C","ARCH1 ص6–7 A103/A104"],"asm":["العرض180سم مقروء من الرسم؛ بروز/رجوع اللوح والمثبتات غير مرقمة؛ يمثل كطبقة20مم على الجدار"]},
 "entrance_W13_frame":{"n":"إطار W13 حول مرآة دخول الأرضي","cf":"doc","sp":[["الإطار","300×340سم،20مم Granite Type02"],["المرآة الداخلية","140×210سم مقروءة من الحد المرسوم؛ قاعها20سم فوقFFL"],["الموضع","على وجه الجدار الغربي،40سم من زاوية الدخول الشمالية؛ A1600D–D/A102"]],"sr":["ARCH2 ص34 A1600 قطاع D–D","ARCH1 ص5 A102"],"asm":["أجزاء الإطار مستنتجة من الحد الخارجي وفتحة المرآة؛ تقسيم البلاطات والمونة والتثبيت غير مجسّم"]},
 "entrance_mirror":{"n":"مرآة دخول الأرضي","cf":"doc","sp":[["الحدود","الحد الداخلي المرسوم في A1600D–D،140×210سم"]],"sr":["ARCH2 ص34 A1600 قطاع D–D"],"asm":["سمك المرآة4مم وموضعها داخل طبقة الإطار افتراض تجسيم؛ لا زجاج توريد معتمد"]},
 "entrance_W7_detail":{"n":"كسوة W7 على الجدار الغربي لدخول الأرضي","cf":"doc","sp":[["المادة","20مم polished white travertine،1200×600مم"],["النطاق","الجدار الغربي في قطاعD–D باستثناء إطار W13 والمرآة"],["الارتفاع","340سم من A1600D–D؛ قص على الأجسام والفتحات الموجودة"]],"sr":["ARCH2 ص34 A1600 قطاع D–D","ARCH1 ص5 A102"],"asm":["طبقة وجه مشتقة من الجدار؛ لا تقسيم بلاطات أو مثبتات ولا تعميم على الغرف المجاورة"]},
}

def _prism(p,z0,z1):
    return ["p",[[round(x,2),round(y,2)]for x,y in list(p.exterior.coords)[:-1]],round(z0,3),round(z1,3),
            [[[round(x,2),round(y,2)]for x,y in list(h.coords)[:-1]]for h in p.interiors]or None]

def build(M,els,verbose=False):
    els[:]=[e for e in els if not ID_RE.search(e['id'])]
    D=json.load(open(DATA,encoding='utf-8')); sources=D['detail_geometry']
    M.setdefault('mats',{}).update(copy.deepcopy(MATS));M.setdefault('types',{}).update(copy.deepcopy(TYPES))
    for L in M['layers']:
        if L['id']=='A' and not any(s[0]=='A.detail' for s in L['subs']):L['subs'].append(['A.detail','تفاصيل موضعية من المخطط: مكتب وسلّم'])
    refs={
      'desk':'ARCH1 ص5 A102: مكتب الاستقبال A02_FURNITURE_FIXED؛ ARCH2 ص43 A2100: شكل وأبعاد وقطاعات المكتب. المحاور محفوظة،التمثيل التفصيلي مشتق من حدود المسقط.',
      'ladder':'ARCH1 ص8–9 A105/A106: CAT LADDER طبقة X-AD738-Top Roof Plan$0$A-LADDER؛ ARCH2 ص37 A1800: عرض80سم،12درجة Ø2سم/30سم وزاوية7.5×7.5×0.9سم. تعارض FFL+26.85/A1800+27.25 وتعارض stainless/galvanized محفوظان.'}
    si={}
    for k,v in refs.items():
        if v not in M['sp']:M['sp'].append(v)
        si[k]=M['sp'].index(v)
    n=0;stats=collections.Counter()
    def add(kind,lv,g,t,mat,attrs=None):
        nonlocal n
        n+=1;stats[t]+=1;src=sources[kind]
        a={'source_kind':'derived_from_outline','source_reference':f"{src['set']}:{src['page']} {src['source_no']} / {src['layer']}",
           'source_page':src['page'],'source_drawing_indices':src['drawing_indices'],'source_transform':src['source_transform'],
           'source_xy':src['bbox_cm'],'source_xy_units':'cm','registration':'محاور المصدر دون إزاحة'}
        if attrs:a.update(attrs)
        els.append({'id':f'A.detail-{lv}-AD{n:04d}','c':'A.detail','l':lv,'g':g,'t':t,'m':mat,'mark':'A2100'if kind=='desk'else'CAT LADDER',
                    'a':a,'s':[si[kind]],'grp':'AD-'+kind})
    # The complete top outline is the convex hull of the drawn counter edges.
    # A2100 makes the front skin 90 cm, with an 80 cm work surface behind it.
    S=sources['desk'];top=Polygon(S['top_xy']);inside=Polygon(S['worktop_xy']);inner=inside.buffer(-2)
    rear=box(top.bounds[0]-1,top.bounds[1]+34,top.bounds[0]+4,top.bounds[3]-34)
    skin=inside.difference(inner).difference(rear)
    z=.35
    for p in ([skin]if skin.geom_type=='Polygon'else skin.geoms):
        add('desk','G',_prism(p,z+.05,z+.75),'reception_counter_wood','ad_solid_wood',{'assumed':'عمق جلد الخشب2سم افتراض؛ فتحة ظهر المكتب تتبع الجزء المستقيم المرسوم؛ الغلاف مشتق من حدود المسقط'})
    add('desk','G',_prism(inside,z+.75,z+.80),'reception_counter_wood','ad_solid_wood',{'height_above_ffl_cm':80,'source_pdf_points':S['source_pdf_points']})
    # Front gold upstand, following the U shaped skin; no solid 15 cm block.
    gold=top.difference(top.buffer(-2)).difference(rear)
    for p in ([gold]if gold.geom_type=='Polygon'else gold.geoms):
        add('desk','G',_prism(p,z+.75,z+.90),'reception_counter_gold','ad_chrome_gold',{'assumed':'سماكة الغلاف الذهبي2سم افتراض؛ ارتفاع15سم مكتوب في A2100'})
    for sl in S['slats']:
        xy=sl['xy'];line=LineString(xy)
        if line.length<.5:continue
        p=line.buffer(.5,cap_style=2,join_style=2)
        add('desk','G',_prism(p,z+.07,z+.75),'reception_counter_slat','ad_solid_wood',{'assumed':'عمق الشريحة1سم افتراض؛ الارتفاع68سم من A2100',
            'source_kind':'derived_from_plan_strip','source_xy':xy,'source_pdf_points':sl['pdf_points'],'source_drawing_indices':[sl['drawing_index']]})
    # Source plan outer rail edges: 80 cm; the source wall face is at y800.4.
    S=sources['ladder'];xl,xr=1155.29,1235.28;y=823.06;wall_y=800.4
    for x,sg in [(xl,1),(xr,-1)]:
        for p in [box(min(x,x+sg*7.5),y-4.75,max(x,x+sg*7.5),y-3.85),box(min(x,x+sg*.9),y-4.75,max(x,x+sg*.9),y+2.75)]:
            add('ladder','R',_prism(p,23.65,27.75),'cat_ladder_side','ad_ladder_metal',{'source_pdf_points':S['source_pdf_points'],
                 'drawing_conflict':'A1800 FF L+27.25/390سم مقابل A106 FFL+26.85 وT.OP+27.25؛ مادة STAINLESS في العنوان خلاف GALVANIZED في callouts'})
    for i in range(12):
        zz=round(23.35+.40+i*.30,3)
        add('ladder','R',['t',[[xl+.9,y,zz],[xr-.9,y,zz]],2.0],'cat_ladder_rung','ad_ladder_metal',{'rung':i+1,'above_roof_ffl_cm':round((zz-23.35)*100),
            'drawing_conflict':'عرض وموقع المسقط ثابتان؛ منسوب منصة A1800+27.25 مختلف عن FFL+26.85 في A106'})
    # The two fixing bands are measured in A1800's front elevation (PDF y169.4,
    # y381.92; FFL27.25 line y118.64; 1:20 scale), not invented support points.
    for zz in [26.892,25.392]:
        for x in [xl+3.75,xr-3.75]:
            add('ladder','R',['r',round(x-5,2),wall_y,round(x+5,2),wall_y+.8,round(zz-.05,3),round(zz+.05,3)],'cat_ladder_mount','ad_ladder_metal',
                {'assumed':'منسوب مركز نطاق التثبيت قرئ من واجهة A1800 غير مرقم؛ راجع shopdrawing','fixing_pdf_y':169.4 if zz>26 else 381.92,'fixing_scale_cm_per_pt':.70555556})
            add('ladder','R',['t',[[round(x,2),wall_y+.8,zz],[round(x,2),y,zz]],3.0],'cat_ladder_mount','ad_ladder_metal',
                {'assumed':'منسوب تثبيت غير مرقم بالواجهة؛ طول الوصلة مشتق من فرق وجه الجدار ونقاط المسقط؛ لا shaft أو دعم مصطنع'})
    # A1600 section A-A explicitly marks both lateral B lobby faces W7.
    # Crop to the A101 lobby and actual existing wall segments; the left door
    # opening is retained. No W13 or lift-front facing is inferred.
    M['mats'].setdefault('fin_W7',{'name':'W7 — رخام travertine أبيض مصقول','color':'#ddd3bf','rough':.2})
    sr='ARCH2 ص34 A1600 قطاع A–A: W7 على وجهي ردهة البدروم الجانبيين،20مم وارتفاع225سم؛ ARCH1 ص4 A101: حدود الردهة540×380سم وFFL−3.50؛ الكسوة مقصوصة على وجوه الجدار الفعلية دون إغلاق الفتحات.'
    if sr not in M['sp']:M['sp'].append(sr)
    wsrc=M['sp'].index(sr)
    for face,sign in [(1534.6,1),(2074.8,-1)]:
        spans=[]
        for e in els:
            if e['c']!='A.wall' or e['l']!='B' or e['g'][0]!='r':continue
            g=e['g'];fixed=g[3] if sign>0 else g[1]
            if abs(fixed-face)>.15:continue
            lo,hi=max(1239.8,g[2]),min(1619.8,g[4])
            if hi>lo:spans.append(box(min(face,face+sign*2),lo,max(face,face+sign*2),hi))
        if not spans:continue
        cover=unary_union(spans)
        for p in ([cover]if cover.geom_type=='Polygon'else cover.geoms):
            n+=1;stats['lobby_W7_detail']+=1
            els.append({'id':f'A.detail-B-AD{n:04d}','c':'A.detail','l':'B','g':_prism(p,-3.50,-1.25),'t':'lobby_W7_detail','m':'fin_W7','mark':'W7','grp':'AD-B-lobby-W7',
                        'a':{'source_kind':'derived_from_model_face','source_reference':'ARCH1:4 A101 / ARCH2:34 A1600 section A-A','source_xy':list(p.bounds),
                             'face_cm':face,'height_cm':225,'thickness_mm':20,'ffl_m':-3.50,
                             'note':'وجهان جانبيان مؤكدان فقط؛ لم تُغط فتحة اليسار أو واجهة المصاعد،ولم يُعمم W13'},'s':[wsrc]})
    # A1601's A-A wall and the B-B ends are unambiguously W7. The partial
    # plan was registered against A104 at s=1.7645, ox=360.38198,
    # oy=1196.31417 (source-layer inlier ratio .8421). The full A103/A104
    # source and existing wall faces supply the final per-floor positions.
    # C-C looks in the opposite direction. Four actual door-frame pairs give
    # plan_x = 1326.89489 - elevation_x, with <= .0151 pt residual.
    sr = ('ARCH2 ص35 A1601: W7 في الواجهة A–A والطرفين B–B،20مم وارتفاع235سم؛ '
          'ARCH1 ص6–7 A103/A104: وجوه الممر على y≈800/1000 وx≈674/2365سم؛ '
          'الكسوة مشتقة من الجسم الموجود ومقصوصة على الفتحات ومناسيب العتبات؛ قطاع C–C معكوس الاتجاه ولوح W13 مستثنى من W7.')
    if sr not in M['sp']:
        M['sp'].append(sr)
    csrc = M['sp'].index(sr)
    walls = [e for e in els if e['c'] in ('A.wall','S.wall','S.col')]
    corridor_counts = collections.Counter()
    cal = D['lobby_detail_review']['C_C_reversed_calibration']
    for lv in ('1','2','3','4','5'):
        ffl = next(q['ffl'] for q in M['levels'] if q['id'] == lv)
        left, right, south = (675.8,2364.9,799.7) if lv == '1' else (674.3,2364.8,800.0)
        rg = cal['plan_registrations']['6' if lv == '1' else '7']
        u0,v0,u1,v1 = cal['panel_inner_pdf']
        px0,px1 = sorted([rg['s']*(cal['offset_pdf']-u)+rg['ox'] for u in (u0,u1)])
        groups = {}
        hosts = collections.defaultdict(set)
        for e in walls:
            if e['l'] != lv:
                continue
            p = footprint(e['g'])
            z0,z1 = zr(e['g'])
            if p is None or not p.is_valid or z0 is None:
                continue
            lo,hi = max(ffl,z0),min(ffl+2.35,z1)
            if hi <= lo:
                continue
            q = list(p.exterior.coords)
            for a,b in zip(q,q[1:]):
                if abs(a[1]-b[1]) < .01 and 999.5 <= a[1] <= 1001.0:
                    axis,fixed,sign = 'x',a[1],-1
                    start,end = max(left,min(a[0],b[0])),min(right,max(a[0],b[0]))
                    outside = (start+end)/2,fixed-.01
                elif abs(a[1]-b[1]) < .01 and 799.5 <= a[1] <= 800.5:
                    axis,fixed,sign = 'x',a[1],1
                    start,end = max(left,min(a[0],b[0])),min(right,max(a[0],b[0]))
                    outside = (start+end)/2,fixed+.01
                elif abs(a[0]-b[0]) < .01 and left-.5 <= a[0] <= left+.5:
                    axis,fixed,sign = 'y',a[0],1
                    start,end = max(south,min(a[1],b[1])),min(999.9,max(a[1],b[1]))
                    outside = fixed+.01,(start+end)/2
                elif abs(a[0]-b[0]) < .01 and right-.5 <= a[0] <= right+.5:
                    axis,fixed,sign = 'y',a[0],-1
                    start,end = max(south,min(a[1],b[1])),min(999.9,max(a[1],b[1]))
                    outside = fixed-.01,(start+end)/2
                else:
                    continue
                if end-start <= .1 or p.contains(Point(outside)):
                    continue
                key = (axis,round(fixed,3),sign,round(lo,3),round(hi,3))
                plate = box(start,min(fixed,fixed+sign*2),end,max(fixed,fixed+sign*2)) if axis == 'x' else box(min(fixed,fixed+sign*2),start,max(fixed,fixed+sign*2),end)
                if axis == 'x' and sign == 1:
                    plate = plate.difference(box(px0,799.0,px1,803.0))
                if plate.is_empty:
                    continue
                groups.setdefault(key,[]).append(plate)
                hosts[key].add(e['id'])
        for key in sorted(groups):
            axis,fixed,sign,z0,z1 = key
            cover = unary_union(groups[key])
            for p in ([cover] if cover.geom_type == 'Polygon' else cover.geoms):
                n += 1
                stats['corridor_W7_detail'] += 1
                corridor_counts[lv] += 1
                els.append({'id':f'A.detail-{lv}-AD{n:04d}','c':'A.detail','l':lv,'g':_prism(p,z0,z1),
                    't':'corridor_W7_detail','m':'fin_W7','mark':'W7','grp':'AD-corridor-W7-'+lv,
                    'a':{'source_kind':'derived_from_model_face','source_reference':f'ARCH1:{6 if lv == "1" else 7} A103/A104 / ARCH2:35 A1601 sections A-A/B-B',
                         'source_xy':list(p.bounds),'source_set':'ARCH1','source_page':6 if lv == '1' else 7,
                         'detail_registration':D.get('lobby_detail_review',{}).get('A1601_plan_registration'),
                         'host_ids':sorted(hosts[key]),'face_axis':axis,'face_cm':fixed,'height_cm':235,'thickness_mm':20,'ffl_m':ffl,
                         'assumed':'نطاق المادة من A1601؛ الهندسة مشتقة من وجوه الجدار الموجودة مع حفظ الفتحات ولوح W13؛ لا تقسيم بلاط أو مونة أو مثبتات؛ عمق رجوع حواف اللوح غير معطى'},'s':[csrc]})
        n += 1
        stats['corridor_W13_detail'] += 1
        els.append({'id':f'A.detail-{lv}-AD{n:04d}','c':'A.detail','l':lv,
            'g':['r',round(px0,2),south,round(px1,2),south+2,ffl,round(ffl+2.35,3)],
            't':'corridor_W13_detail','m':'fin_W13','mark':'W13 — رقم الطابق '+lv,'grp':'AD-corridor-W13-'+lv,
            'a':{'source_kind':'derived_from_section','source_reference':'ARCH2:35 A1601 section C-C / ARCH1:A103/A104',
                 'source_set':'ARCH2','source_page':35,'source_layer':'ELE 3','source_drawing_indices':cal['panel_inner_drawings'],
                 'source_pdf_points':[[u0,v0],[u0,v1],[u1,v1],[u1,v0]],'section_calibration':copy.deepcopy(cal),
                 'source_xy':[px0,south,px1,south+2],'floor_number':lv,'ffl_m':ffl,'height_cm':235,'thickness_mm':20,
                 'assumed':'العرض180سم من الحدين المرسومين،لا رقم مقاس مكتوب؛ البروز/الرجوع غير معطى،يمثل اللوح كطبقة20مم على وجه الجدار؛ لا حروف أو مثبتات تخمينية'},'s':[csrc]})
    # Ground mirror frame: its left margin is the dimensioned 40 cm from the
    # north inside corner of the entrance. The A102 wall anchor is raw2072.
    G = D['lobby_detail_review']['G_mirror_section']
    scale,origin,front,face = G['scale_cm_per_pt'],G['origin_pdf_u'],G['front_anchor_y_cm'],G['wall_face_cm']
    def projected_rect(q):
        us=[p[0] for p in q];vs=[p[1] for p in q]
        ys=sorted([front-scale*(u-origin) for u in (min(us),max(us))])
        zs=sorted([.35+scale*(G['ffl_pdf_v']-v)/100 for v in (min(vs),max(vs))])
        return ys+zs
    y0,y1,z0,z1 = projected_rect(G['outer_pdf'])
    my0,my1,mz0,mz1 = projected_rect(G['mirror_pdf'])
    sr='ARCH2 ص34 A1600 قطاعD–D: إطارW13 300×340سم ومرآة داخلية،هامش40سم من زاوية الدخول؛ ARCH1 ص5 A102،الجدار الخام2072 عندx1344.994 وy1619.911؛ لا موضع مستنتج من نص المرآة.'
    if sr not in M['sp']:
        M['sp'].append(sr)
    gsrc=M['sp'].index(sr)
    def ground_add(typ,geom,indices,raw,attrs=None):
        nonlocal n
        n += 1
        stats[typ] += 1
        a={'source_kind':'derived_from_section','source_reference':'ARCH2:34 A1600 section D-D / ARCH1:5 A102 raw2072',
           'source_set':'ARCH2','source_page':34,'source_layer':'ELE 5','source_drawing_indices':indices,'source_pdf_points':raw,
           'section_calibration':copy.deepcopy(G),'source_xy':[geom[1],geom[2],geom[3],geom[4]],'ffl_m':.35}
        if attrs:
            a.update(attrs)
        els.append({'id':f'A.detail-G-AD{n:04d}','c':'A.detail','l':'G','g':geom,'t':typ,
                    'm':'ad_mirror' if typ=='entrance_mirror' else ('fin_W13' if typ=='entrance_W13_frame' else 'fin_W7'),
                    'mark':'مرآة دخول الأرضي' if typ=='entrance_mirror' else ('W13' if typ=='entrance_W13_frame' else 'W7'),
                    'grp':'AD-G-entrance-detail','a':a,'s':[gsrc]})
    for ya,yb,za,zb in [(y0,my0,z0,z1),(my1,y1,z0,z1),(my0,my1,z0,mz0),(my0,my1,mz1,z1)]:
        ground_add('entrance_W13_frame',['r',round(face,2),round(ya,2),round(face+2,2),round(yb,2),round(za,3),round(zb,3)],
                   [G['outer_drawing'],G['inner_drawing']],G['outer_pdf'],{'assumed':'أجزاء إطار مشتقة من الحد الخارجي وفتحة المرآة،سماكة20مم موثقة؛ المونة والمثبتات وتقسيم البلاطات غير مجسّمة'})
    ground_add('entrance_mirror',['r',round(face+1.5,2),round(my0,2),round(face+1.9,2),round(my1,2),round(mz0,3),round(mz1,3)],
               [G['inner_drawing']],G['mirror_pdf'],{'assumed':'سمك المرآة4مم وموضعها داخل سمك الإطار افتراض تجسيم؛ الحدود والمناسيب من الرسم'})
    for e in walls:
        if e['l']!='G' or e['g'][0]!='r' or abs(e['g'][3]-face)>.15:
            continue
        g=e['g'];lo,hi=max(.35,g[5]),min(3.75,g[6])
        for ya,yb in [(max(219.86,g[2]),min(y0,g[4])),(max(y1,g[2]),min(front,g[4]))]:
            if yb<=ya or hi<=lo:
                continue
            ground_add('entrance_W7_detail',['r',round(g[3],2),round(ya,2),round(g[3]+2,2),round(yb,2),round(lo,3),round(hi,3)],
                       [G['wall_ref_drawing']],G['wall_ref_pdf_points'],{'source_kind':'derived_from_model_face','host_ids':[e['id']],
                        'source_set':'ARCH1','source_page':5,'source_layer':'A-WALL','source_transform':G['wall_ref_transform'],
                        'assumed':'W7 على وجه الجدار الغربي المرسوم فيD–D فقط،مع حفظ إطارW13 والأبواب؛ لا تقسيم بلاطات أو مثبتات'})
    M.setdefault('meta',{})['arch_detail_remaining']={'count':n,'sources':copy.deepcopy(sources),'by_type':dict(stats),
        'review_file':'pipeline/data/arch_struct_review.json','conflicts':[c for c in D['conflicts']if c['id'].startswith('AR-LADDER')],
        'corridor_W7_by_level':dict(corridor_counts),
        'w7_w13':'W7 على وجهي B الجانبيين وواجهات الممر1–5؛ W13 لوح رقم الطابق من قطاعC–C المعكوس وإطار مرآةG منD–D بهامش40سم؛ مواد موضعية مع فتحات محفوظة،وتفاصيل المورد/البروز/التثبيت غير مغلقة.'}
    if verbose:print('architectural source details:',n,dict(stats))
    return dict(stats)
