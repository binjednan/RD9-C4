# -*- coding: utf-8 -*-
"""Build water-site and irrigation objects in their registered drawing positions."""
import os, json, re, collections

HERE=os.path.dirname(__file__)
DATA=os.path.join(HERE,'data','water_site.json')
ID_RE=re.compile(r'-WS\d{4}$')
MATS={'p_irr':{'name':'خط ري 50 مم','color':'#5ba45d','code':'IR-100/101'},
      'p_grp':{'name':'خزان GRP','color':'#52c2cf','opacity':0.45,'code':'WS-010/104'}}
TYPES={
 'ws_site_pipe':{'n':'خط تغذية مياه الموقع 50 مم','cf':'doc','sp':[['القطر','50 مم']],'sr':['MECH2 ص17'],'asm':['منسوب الأنبوب غير معطى؛ افتراض موسوم']},
 'ws_fill_drop':{'n':'مقطع تعبئة خزان من أعلى','cf':'doc','sp':[['القطر','50 مم؛ دائرة مقطع رأسي']],'sr':['MECH2 ص17','MECH2 ص25'],'asm':['امتداد القطعة إلى سطح الماء −0.90 م افتراض']},
 'ws_site_meter':{'n':'عداد مياه تعبئة الخزان','cf':'doc','sp':[['المصدر','رمز M؛ أربعة في WS-010']],'sr':['MECH2 ص17'],'asm':['تمثيل جسم العداد وارتفاعه افتراض']},
 'ws_meter_box':{'n':'صندوق عدادات مياه الموقع','cf':'doc','sp':[['المصدر','M.B؛ حدود الصندوق من المسقط']],'sr':['MECH2 ص17'],'asm':['ارتفاع الصندوق غير معطى']},
 'ws_site_chamber':{'n':'غطاء غرفة تغذية مياه الموقع','cf':'doc','sp':[['الغرفة','60×60×50 سم']],'sr':['MECH2 ص17'],'asm':['المجسم يظهر الغطاء؛ عمق الغرفة محفوظ دون جسم حفر افتراضي']},
 'ws_tank_raw':{'n':'خزان مياه خام GRP على السطح','cf':'doc','sp':[['المقاس','3×2.5×2 م'],['صافي التخزين','2600 IGal']],'sr':['MECH2 ص17','MECH2 ص22','MECH2 ص23'],'asm':['قاع الخزان عند سطح R؛ اعتماد الموقع يحتاج تنسيقًا']},
 'ws_tank_filtered':{'n':'خزان مياه مفلترة GRP على السطح','cf':'doc','sp':[['المقاس','3×2.5×2 م'],['صافي التخزين','2600 IGal']],'sr':['MECH2 ص17','MECH2 ص22','MECH2 ص23'],'asm':['قاع الخزان عند سطح R؛ اعتماد الموقع يحتاج تنسيقًا']},
 'irr_pump':{'n':'مضخة ري أفقية','cf':'doc','sp':[['الترتيب','واحدة تشغيل وواحدة احتياط'],['التصريف والضغط','45 GPM عند 4 بار'],['القدرة','2.2 كيلوواط']],'sr':['MECH2 ص25'],'asm':['ارتفاع الجسم 60 سم افتراض؛ المعماري −3.50 م مقابل الميكانيكي −3.30 م']},
 'irr_pipe':{'n':'ماسورة ري 50 مم','cf':'doc','sp':[['القطر','50 مم']],'sr':['MECH2 ص25–26'],'asm':['المنسوب غير معطى؛ مسار المسقط محفوظ']},
 'irr_chamber':{'n':'غطاء غرفة الري عند المصطبة','cf':'doc','sp':[['المقاس','60×60 سم من الرمز'],['المصدر','WALL CHAMBER FOR IRRIGATION']],'sr':['MECH2 ص26'],'asm':['الغطاء على سطح المصطبة؛ عمق 50 سم غير منصوص عليه للري ولا يفترض']},
}

def build(M,els,verbose=False):
    els[:]=[e for e in els if not ID_RE.search(e['id'])]
    if not os.path.exists(DATA):return {}
    D=json.load(open(DATA,encoding='utf-8'))
    M.setdefault('mats',{}).update(MATS)
    for t,v in TYPES.items():M.setdefault('types',{}).setdefault(t,v)
    refs=['تغذية الموقع WS-010 (MECH2 ص17): تسجيل 17×11 محورًا، خطوط 50 مم وأربعة عدادات وصندوق وغرفة مياه وخزانان GRP على السطح؛ موضعا الخزانين مؤكدان في WS-104 ص22.',
          'الري IR-100/101 (MECH2 ص25–26): مضختا تشغيل واحتياط وخطوط 50 مم وغرفة عند المصطبة؛ اختلاف مناسيب غرفة المضخات بين المعماري والميكانيكي موثق.',
          'مخطط المياه الرأسي WS-105 وتفاصيل WS-501 (MECH2 ص23–24): معلومات السعات والرفع والتعزيز والتوصيل؛ لا مواقع مسقط مشتقة من إحداثيات المخطط الرأسي.']
    for s in refs:
        if s not in M['sp']:M['sp'].append(s)
    sources=[M['sp'].index(s) for s in refs]
    ffl={v['id']:v['ffl'] for v in M['levels']}
    from shapely.geometry import Point
    import support
    sup=support.Support(els,M['levels'])
    def host(x,y,limit):
        surfaces=[h[0] for h in sup.H.hits(Point(x,y),3) if h[3]=='floor' and h[0]<=limit+.04]
        assert surfaces, ('no floor host at drawn XY',x,y,limit)
        return round(max(surfaces),3)
    n=0;stats=collections.Counter()
    def add(c,lv,g,t,mat,sys,record,mark,assumed,extra=None):
        nonlocal n
        n+=1;stats[t]+=1
        a={'sys':sys,'assumed':assumed,'source_page':f'MECH2:{record["page"]}',
           'source_transform':record['source_transform'],'source_pdf_points':record.get('pdf_points'),
           'source_xy':record.get('centre',record.get('points')),
           'geometry_role':'source_route_display' if g[0]=='t' else 'source_symbol_display',
           'material_status':'GRP_explicit_source' if t in ('ws_tank_raw','ws_tank_filtered') else 'not_specified_in_reviewed_source',
           'finish_status':'not_specified_in_reviewed_source',
           'dimension_status':'explicit_source_dimensions' if t in ('ws_tank_raw','ws_tank_filtered','ws_site_chamber') else 'nominal_diameter_50mm_from_label' if t in ('ws_site_pipe','ws_fill_drop','irr_pipe') else 'drawn_symbol_outline_only',
           'elevation_status':'local_floor_surface_derived_and_display_height_assumed',
           'physical_geometry_status':'source_dimensions_with_unverified_support_elevation' if t in ('ws_tank_raw','ws_tank_filtered') else 'display_proxy_pending_dimensions_and_mounting',
           'source_graphic_colour_rgb':record.get('source_graphic_colour_rgb')}
        a.update(extra or {})
        e={'id':f'{c}-{lv}-WS{n:04d}','c':c,'l':lv,'g':g,'mark':mark,'t':t,'m':mat,'a':a,
           's':[sources[1] if sys=='irrigation' else sources[0]]}
        els.append(e);return e
    S=D['site'];z=round(ffl['G']+.10,3)
    for i,p in enumerate(S['pipes'],1):
        add('P.cold','G',['t',[[x,y,z] for x,y in p['points']],5],'ws_site_pipe','p_cold','water_site',p,f'50 mm {i}',
            'محور التغذية أعلى منسوب الأرضي بـ10 سم (0.45 م) افتراض؛ خط ADDC وموقع كل نقطة من المسقط ولا منسوب تركيب معتمد',{'dia_mm':50})
    for i,p in enumerate(S['fill_drops'],1):
        x,y=p['centre']
        add('P.cold','G',['t',[[x,y,-.90],[x,y,z]],5],'ws_fill_drop','p_cold','water_site',p,f'50 mm T/B {i}',
            'القطعة الرأسية تبدأ عند منسوب ماء الخزانات المعماري −0.90 م وتصل إلى التغذية 0.45 م؛ امتدادها الرأسي افتراض والموضع من دائرة المسقط',{'dia_mm':50})
    for i,p in enumerate(S['meters'],1):
        x,y=p['centre'];b=host(x,y,ffl['G']);size=p['diameter_cm']
        add('P.cold','G',['b',x,y,size,size,0,b,round(z+.10,3)],'ws_site_meter','p_valve','water_site',p,f'M {i}',
            'الرمز M ومركزه من المسقط؛ جسم العداد تمثيل مبسط عند الأرضية وحول محور التغذية الافتراضي 0.45 م')
    p=S['cabinet'];x,y=p['centre'];b=p['bounds'];bottom=host(x,y,ffl['G'])
    add('P.cold','G',['r',b[0],b[1],b[2],b[3],bottom,round(bottom+.50,3)],'ws_meter_box','p_valve','water_site',p,'M.B',
        'ارتفاع صندوق العدادات 50 سم افتراض؛ حدود المسقط من الإطار المرسوم')
    for p in S['chambers']:
        x,y=p['centre'];bottom=host(x,y,ffl['G']);b=p['bounds']
        add('P.cold','G',['r',b[0],b[1],b[2],b[3],bottom,round(bottom+.04,3)],'ws_site_chamber','p_site','water_site',p,'M.H 60×60×50',
            'يظهر غطاء الغرفة عند سطح الموقع الحقيقي؛ سُمك الغطاء 4 سم افتراض؛ عمق الغرفة 50 سم منصوص عليه ومحفوظ دون جسم حفر غير مرسوم',{'chamber_depth_cm':50})
    for i,p in enumerate(S['tanks']):
        x,y=p['centre'];b=p['bounds'];bottom=host(x,y,ffl['R']);t='ws_tank_raw' if i==0 else 'ws_tank_filtered'
        add('P.tank','R',['r',b[0],b[1],b[2],b[3],bottom,round(bottom+2,3)],t,'p_grp','water_roof',p,'RAW GRP' if i==0 else 'FILTERED GRP',
            'قاع الخزان على سطح R المعماري 23.35 م؛ ارتفاع 2 م وأبعاد 300×250 سم منصوص عليها، وموضعه مؤكد من ص17 وص22',{'net_capacity_igal':2600,'dimensions_cm':[300,250,200]})
    I=D['irrigation'];zb=-3.10
    for p in I['pumps']:
        b=p['bounds']
        add('P.pump','B',['r',b[0],b[1],b[2],b[3],-3.50,-2.90],'irr_pump','p_irr','irrigation',p,p['duty'],
            'قاع المضخة عند −3.50 م وفق ARCH1 ص4؛ IR-100 يذكر −3.30 م بفارق 20 سم بانتظار الحسم؛ ارتفاع الجسم 60 سم افتراض',
            {'flow_gpm':45,'pressure_bar':4,'power_kw':2.2,'duty':p['duty']})
    for p in I['pipes']:
        add('P.irr','B',['t',[[x,y,zb] for x,y in p['points']],5],'irr_pipe','p_irr','irrigation',p,'50 mm',
            'محور خطوط البدروم أعلى أرضية غرفة الري المعمارية −3.50 م بـ40 سم افتراض؛ محاور المسقط الأصلية محفوظة',{'dia_mm':50})
    chamber=I['chambers'][0];cx,cy=chamber['centre'];ground=host(cx,cy,1.0)
    for p in I['ground_pipes']:
        add('P.irr','G',['t',[[x,y,round(ground+.05,3)] for x,y in p['points']],5],'irr_pipe','p_irr','irrigation',p,'50 mm F/B',
            'محور خط الري أعلى سطح المصطبة الحقيقية بـ5 سم افتراض؛ لا مسار مرسوم إلى شبكة تنقيط ولا إزاحة صاعد بين نقطتي البدروم والأرضي',{'dia_mm':50})
    b=chamber['bounds']
    add('P.irr','G',['r',b[0],b[1],b[2],b[3],ground,round(ground+.04,3)],'irr_chamber','p_irr','irrigation',chamber,'M.H',
        'تمثيل غطاء غرفة الري فوق سطح المصطبة؛ سُمك الغطاء 4 سم افتراض والعمق غير معطى',{'plan_riser_gap_cm':I['riser_plan_gap']['distance_cm']})
    if verbose:print('water site & irrigation',n,dict(sorted(stats.items())))
    return dict(stats)

if __name__=='__main__':
    raise SystemExit('Call build(M, els) from post_model integration; this script does not write the model.')
