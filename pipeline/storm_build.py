# -*- coding: utf-8 -*-
"""Build only the site and storm features extracted from MECH2 p1 and p27-31."""
import os, re, json, collections, math

HERE=os.path.dirname(__file__)
DATA=os.path.join(HERE,'data','storm.json')
ID_RE=re.compile(r'-ST\d{4}$')
MATS={'p_storm':{'name':'ماسورة تصريف مياه الأمطار','color':'#658fa8','code':'SW-101…105'},
      'p_site':{'name':'صرف الموقع وغرف التفتيش','color':'#8b9487','code':'DR-010'}}
TYPES={
 'site_mh':{'n':'غرفة تفتيش صرف الموقع','cf':'doc','sp':[['المقاس','100×100 سم من المسقط'],['المناسيب','افتراض موسوم؛ جدول الغرف فارغ']],'sr':['MECH2 ص1'],'asm':['الغطاء والقاع افتراض؛ بانتظار تأكيدك']},
 'pipe_site':{'n':'ماسورة صرف الموقع 6 بوصات','cf':'doc','sp':[['المقاس','6"Ø U.P.V.C CLASS 16']],'sr':['MECH2 ص1'],'asm':['منسوب الماسورة افتراض']},
 'drain_outlet':{'n':'طرف صرف الموقع الغربي','cf':'doc','sp':[['النهاية','TO BE CONNECTED WITH؛ الوجهة غير مرسومة']],'sr':['MECH2 ص1'],'asm':['منسوب الطرف افتراض']},
 'storm_rd':{'n':'مصرف مياه أمطار السطح','cf':'doc','sp':[['الرمز','دائرتان مع مشبك مصرف المطر']],'sr':['MECH2 ص30–31'],'asm':['المنسوب عند أرضية السطح افتراض']},
 'storm_stack':{'n':'صاعد تصريف مياه الأمطار','cf':'doc','sp':[['الرمز','دائرتان متحدتا المركز ووسم F/A أو T/B']],'sr':['MECH2 ص27–31'],'asm':['امتداد القطعة بين البلاطات افتراض']},
 'storm_pipe':{'n':'ماسورة أفقية لمياه الأمطار','cf':'doc','sp':[['الرمز','خطوط حمراء متقطعة أو متصلة في المسقط']],'sr':['MECH2 ص27'],'asm':['منسوب HL افتراض']},
 'storm_co':{'n':'فتحة تنظيف مياه الأمطار','cf':'doc','sp':[['الموضع','محور الرمز ذي العارضة العمودية كما في المفتاح؛ 6 موسومة ورمز سابع بلا وسم']],'sr':['MECH2 ص27'],'asm':['المنسوب وحجم جسم العرض افتراض']},
 'storm_outlet':{'n':'نهاية تصريف حر لمياه الأمطار','cf':'doc','sp':[['الوسم','Rain water free discharge']],'sr':['MECH2 ص27'],'asm':['منسوب الماسورة افتراض']},
}

def build(M, els, verbose=False):
    els[:]=[e for e in els if not ID_RE.search(e['id'])]
    if not os.path.exists(DATA):return {}
    D=json.load(open(DATA,encoding='utf-8'))
    for k,v in MATS.items():M.setdefault('mats',{}).setdefault(k,v)
    for k,v in TYPES.items():M.setdefault('types',{}).setdefault(k,v)
    refs=['تصريف الموقع DR-010 (MECH2 ص1): ثلاث غرف تفتيش وخط 6 بوصات وسهما جريان ونص الطرف الغربي؛ المناسيب غير معطاة.',
          'تصريف مياه الأمطار SW-101…105 (MECH2 ص27–31): الصواعد والمصارف والخطوط ونهايات التصريف الحر؛ المناسيب الافتراضية موسومة.']
    for s in refs:
        if s not in M['sp']:M['sp'].append(s)
    src=[M['sp'].index(s) for s in refs]
    ffl={v['id']:v['ffl'] for v in M['levels']}
    slab={e['l']:e['g'][2:4] for e in els if e['c']=='S.slab' and e['g'][0]=='p' and e['l'] not in ('B','G')}
    def slab_bot(lv):return slab[lv][0] if lv in slab else ffl[lv]-0.1
    n=0;stats=collections.Counter()
    def add(cat,lv,g,t,mat,system,mark=None,a=None,site=False):
        nonlocal n
        n+=1;stats[t]+=1
        at={'sys':system};at.update(a or {})
        e={'id':f'{cat}-{lv}-ST{n:04d}','c':cat,'l':lv,'g':g,'mark':mark,'t':t,'m':mat,'a':at,'s':[src[0] if site else src[1]]}
        els.append(e);return e
    # Drainage site, with explicit unverified vertical datum.
    S=D['site']; cover=round(ffl['G']-0.30,3); bottom=round(cover-1.50,3); axis=round(bottom+0.075,3)
    mh=sorted(S['manholes'],key=lambda x:-x['x'])
    for v in mh:
        add('P.drain','G',['b',v['x'],v['y'],100,100,0,bottom,cover],'site_mh','p_site','site',v['mark'],
            {'shaft':1,'assumed':'جدول الغرف فارغ؛ غطاء الغرفة عند منسوب الأرضي ناقص 0.30 م وقاعها 1.50 م أسفل الغطاء؛ ترتيب MH-01…03 شرقًا إلى غربًا افتراض — بانتظار تأكيدك',
             'support_note':'غرفة مدفونة في التربة خارج نطاق بلاطات النموذج؛ تصنّف كعنصر رأسي قائم بذاته'},True)
    west=S['outlet']; X=[west['x']]+[v['x'] for v in reversed(mh)]
    X[-1]=S['pipe_axis'][-1][0]  # end at the drawn axis vertex, not the manhole centre
    for i,(x0,x1) in enumerate(zip(X,X[1:]),1):
        add('P.drain','G',['t',[[x0,west['y'],axis],[x1,west['y'],axis]],15],'pipe_site','p_site','site',f'6" U.P.V.C {i}',
            {'assumed':'محور الماسورة على ارتفاع نصف القطر فوق قاع الغرفة المفترض؛ جدول المناسيب فارغ — بانتظار تأكيدك','diameter_cm':15},True)
    add('P.drain','G',['cyl',west['x'],west['y'],10,axis-0.05,axis+0.05],'drain_outlet','p_site','site','TO BE CONNECTED WITH',
        {'shaft':1,'note':'النص TO BE CONNECTED WITH فقط؛ وجهة الربط غير مرسومة','assumed':'منسوب النهاية تابع لمنسوب قاع الغرفة المفترض — بانتظار تأكيدك',
         'support_note':'نهاية مدفونة ومحمولة على ماسورة الموقع؛ التربة خارج نطاق مدقّق البلاطات'},True)
    # One vertical segment for each drawn riser at each floor; the typical sheet applies to levels 2..5.
    order=['G','1','2','3','4','5','R','T']
    pages={'G':'G','1':'1','2':'TY','3':'TY','4':'TY','5':'TY','R':'R'}
    for lv,key in pages.items():
        upper=order[order.index(lv)+1]
        z0=ffl['G'] if lv=='G' else slab_bot(lv)
        z1=slab_bot(upper)
        risers=list(D['sheets'][key]['risers'])
        if lv=='R':
            # The RD at (917,748) also carries an explicit F/A-T/B vertical-pipe label.
            risers += [dict(v,label=v['vertical_label']) for v in D['sheets']['R']['drains']
                       if v.get('vertical_label') and 'F/A' in v['vertical_label']['text']]
        for v in risers:
            dia=15 if v['diameter_in']==6 else 10
            add('P.storm',lv,['cyl',v['x'],v['y'],dia/2,round(z0,3),round(z1,3)],'storm_stack','p_storm','storm',f'{v["diameter_in"]}" F/A–T/B',
                {'shaft':1,'assumed':'امتداد الصاعد الرأسي بين أسفل البلاطتين افتراض؛ الموضع والقطر من المسقط','diameter_cm':dia,'label':v.get('label')})
    # A roof drain has a visible grate at floor level and body through the roof build-up.
    for lv in ('R','T'):
        for v in D['sheets'][lv]['drains']:
            dia=15 if v['diameter_in']==6 else 10
            add('P.storm',lv,['cyl',v['x'],v['y'],dia/2,round(slab_bot(lv),3),round(ffl[lv]+0.02,3)],'storm_rd','p_storm','storm',v['mark'],
                {'shaft':1,'assumed':'المصرف عند أرضية السطح، وجسمه يعبر طبقة السطح حتى أسفل البلاطة — افتراض','diameter_cm':dia})
    # Only the actual drawn ground-floor pipe runs; no invented roof or external storm network.
    Z=round(slab_bot('1')-0.15-15/200,3)
    for v in D['sheets']['G']['pipes']:
        pts=[[p[0],p[1],Z] for p in v['points']]
        add('P.storm','G',['t',pts,v['diameter_cm']],'storm_pipe','p_storm','storm',v['name'],
            {'assumed':'أنبوب HL تحت بلاطة الدور الأول بـ15 سم مع تصحيح نصف القطر؛ المنسوب غير معطى','drawn_line':v['kind']})
    for v in D['sheets']['G']['cleanouts']:
        add('P.storm','G',['cyl',v['x'],v['y'],6,Z-0.04,Z+0.04],'storm_co','p_storm','storm',v['mark'],
            {'source_xy':[v['x'],v['y']], 'source_pdf_points':[v['source_pdf_point']], 'source_transform':v['source_transform'],
             'source_primitive':v['source_primitive'], 'unlabelled':v.get('unlabelled',False),
             'assumed':'منسوب الجسم على محور HL وحجم العرض 12 سم افتراض؛ XY من محور رمز التنظيف نفسه'})
    for v in D['sheets']['G']['outlets']:
        add('P.storm','G',['cyl',v['x'],v['y'],7.5,Z-0.05,Z+0.05],'storm_outlet','p_storm','storm','FREE DISCHARGE',
            {'shaft':1,'note':'تصريف حر بلا شبكة موقع — لا وجهة مرسومة','assumed':'منسوب النهاية عند منسوب ماسورة HL الافتراضي',
             'support_note':'نهاية رأسية محمولة على ماسورة المطر عند الواجهة؛ طرفها خارج نطاق بلاطات النموذج'})
    for v in D['sheets']['R']['outlets']:
        zr=ffl['R']
        add('P.storm','R',['cyl',v['x'],v['y'],7.5,round(zr-0.02,3),round(zr+0.08,3)],'storm_outlet','p_storm','storm','FREE DISCHARGE',
            {'shaft':1,'note':'تصريف حر من السطح العلوي إلى السطح R؛ لا شبكة موقع مرسومة',
             'assumed':'ارتفاع نهاية التصريف عند أرضية السطح R افتراض',
             'support_note':'نهاية صاعد رأسية مثبتة بالماسورة المرسومة من الأعلى'})
    if verbose:print('storm & site:',n,dict(sorted(stats.items())))
    return dict(stats)
