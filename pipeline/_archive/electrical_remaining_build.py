# -*- coding: utf-8 -*-
"""Build the remaining drawn electrical geometry. Source XY is immutable, NTS pages are metadata.
ELR IDs are rebuilt deterministically. apply_corrections retains existing IDs and before/after evidence.
"""
import os,sys,json,math,re,copy,collections
HERE=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,HERE)
DATA=os.path.join(HERE,'data','electrical_remaining.json');ID_RE=re.compile(r'-ELR\d{4}$')
MATS={'elr_phone':{'name':'مواسير/حامل الهاتف والألياف','color':'#825bbd','code':'TE-105'},'elr_power':{'name':'مواسير دخول ADDC','color':'#8057b8','code':'EP-010'}}
def typ(name,sr,sp=(),asm=()):return {'n':name,'cf':'doc','sp':list(sp),'asm':list(asm),'sr':list(sr)}
TYPES={
 'elr_tape':typ('شريط نحاس الصواعق 25×3 مم',['ELEC2 ص11–16','ELEC2 ص17'],[['المقطع','25×3 مم؛ قطاع مستطيل'],['الموضع','مركز الشريط المرسوم في المسقط']]),
 'elr_down':typ('موصل الصواعق النازل — امتداد موضع متطابق',['ELEC2 ص11–15','ELEC2 ص17'],[['المقطع','25×3 مم'],['الأصل','نفس رمز الموصل في مسقطين متجاورين']],['اتجاه وجه الشريط غير مذكور؛ الربط بين المناسيب مشتق']),
 'elr_earth':typ('موصل تأريض 70 مم²',['ELEC2 ص1'],[['المقطع','70 مم² PVC Y/G في جراب38مم'],['الأصل','المسار مرسوم إلى قضيب وحفرة التأريض']],['ارتفاع التمديد وعمق الغلاف غير مبينين']),
 'elr_earth_bar':typ('قضيب تجميع التأريض',['ELEC2 ص1','ELEC2 ص17'],[['الأصل','رمز مستطيل مظلل بستة مواضع فيص1']],['أبعاد التصنيع وارتفاع التثبيت غير مبينة']),
 'elr_earth_pit':typ('حفرة فحص التأريض',['ELEC2 ص1','ELEC2 ص11','ELEC2 ص17'],[['القضيب','المفتاح16مم،3×1.2م كحد أدنى'],['اختلاف المصدر','تفصيلص17 يذكر20×1200مم']],['أبعاد الحفرة وعمقها افتراض']),
 'elr_clean_pit':typ('تأريض نظيف للهاتف',['ELEC2 ص1'],[['الموضع','رمز CLEAN EARTH PIT شمال غرفة الهاتف']],['أبعاد الحفرة وعمقها افتراض']),
 'elr_earth_rod':typ('قضيب تأريض 16مم — طول3.6م',['ELEC2 ص1','ELEC2 ص11'],[['المفتاح','16mm2-3X1.2m MINIMUM']],['فسرت16mm2 في المفتاح كقطر16مم؛ التفصيلص17 يذكرقطر20مم؛ يحتاج اعتماد']),
 'elr_air_terminal':typ('قضيب التقاط الصواعق500مم',['ELEC2 ص16','ELEC2 ص17'],[['الطول','500 مم؛ ثلاثة رموز وثلاث تسميات مستقلة']],['قطر القضيب وارتفاع قاعدة التثبيت افتراض']),
 'elr_bond':typ('نقطة ربط معدة بشريط الصواعق',['ELEC2 ص16','ELEC2 ص17'],[['الأصل','مربع MECH. EQUIPMENT متصل بالشريط']],['شكل مشبك الربط وارتفاع الجهاز غير محددين']),
 'elr_clip':typ('مشبك شريط النحاس على الدروة',['ELEC2 ص15–17'],[['الدروة','R:+25.25م؛T:+27.25م']],['الأبعاد تمثيل افتراضي3سم×3سم؛ لا تعيد قاعدة الإسناد إسقاطه إلى R']),
 'elr_power_duct':typ('مواسير دخول القدرة — أربعة150مم',['ELEC1 ص8'],[['المفتاح','4No.s150mmPVC PIPES FROM ADDC']],['العمق−0.60م افتراض؛ نهاية خارج المبنى مفتوحة عند حد الرسم']),
 'elr_site_phone':typ('جراب هاتف الموقع100مم',['ELEC2 ص27','ELEC2 ص33'],[['العدد','2×100mm uPVC من JRC الأقرب؛ المبني فقط الجزء المرسوم']],['العمق−0.60م افتراض؛ لا تمدد إلى غرفة توزيع عامة غير مرسومة']),
 'elr_fiber':typ('جزء مرسوم لمدخل ألياف الموقع',['ELEC2 ص27','ELEC2 ص33'],[['المخطط','24/48Core SingleMode Etisalat/DU']],['قطر التمثيل1سم والعمق−0.60م افتراض؛ لا تحدد الخطوط وحدها المزود']),
 'elr_mdf_rack':typ('رف MDF ‏42U للهاتف',['ELEC2 ص27','ELEC2 ص29','ELEC2 ص33–34'],[['المسقط','80×80 سم؛ رف Etisalat ورفDU/Other']],['الارتفاع2م افتراض؛42U قياس الوحدات داخل الرف وليسارتفاعالغلاف']),
 'elr_mini_odf':typ('MINI-ODF في غرفة هاتف الطابق',['ELEC2 ص30–31','ELEC2 ص33–34'],[['الأبعاد','600×600مم'],['الغرفة','TEL بالطوابقالأول–الخامس']],['العمق15سم وارتفاعأسفل1م افتراض']),
 'elr_onu':typ('وحدة الشبكة الضوئية ONU',['ELEC2 ص29–33'],[['الأبعاد','الأرضي60×60×30سم؛الشققوالحارس60×60×15سم']],['ارتفاعأسفل1م افتراض']),
 'elr_rj45_single':typ('مخرج RJ45 مفرد',['ELEC2 ص29–32','ELEC2 ص34'],[['المخطط','رمزRJ45 SINGLEOUTLET']],['أبعاداللوحة9×4×9سم وارتفاع0.3م افتراض؛مسارالتوصيلإلىONUغيرمرسوم']),
 'elr_rj45_dual':typ('مخرج RJ45 مزدوج',['ELEC2 ص29–32','ELEC2 ص34'],[['المخطط','VOICE &CATV؛منفذان']],['أبعاداللوحة9×4×9سم وارتفاع0.3م افتراض؛مسارالتوصيلإلىONUغيرمرسوم']),
 'elr_floorbox':typ('صندوق أرضي13A ومخرجRJ45مزدوج',['ELEC2 ص29','ELEC2 ص34'],[['الأصل','FLOORBOX مع13A DOUBLE SWITCHSOCKETوDUALRJ45']],['أبعاد25×25×8سم افتراض']),
 'elr_phone_tray':typ('حامل كابلات الهاتف450×50مم',['ELEC2 ص29','ELEC2 ص33–34'],[['الأبعاد','450×50مم']],['المنسوب+2.70مفوقالأرضية افتراض؛المخطط يذكرHIGHLEVEL']),
 'elr_gsm_tray':typ('حامل كابلاتGSM300×50مم',['ELEC2 ص29','ELEC2 ص33–34'],[['الأبعاد','300×50مم']],['المنسوب+2.70مفوقالأرضية افتراض؛المخطط يذكرHIGHLEVEL']),
}
DETAIL_REFS={
 'ELEC1:7':'EL-106 التحكم بالإنارة: حساس الحركة إرشادي؛المصمم/المقاول يحدد العدد النهائي؛إنارة الخارج بمؤقتوPhotocell',
 'ELEC1:15':'EP-106 إطار جدولالأحمال فقط؛لا يوجد جدولقابللاستخراج الأحمال داخل الصفحة',
 'ELEC1:18':'EP-109 تفاصيللوحاتومقابسوحامل؛صفحةNTSلا مواقعXY',
 'ELEC2:7':'FA-105 مخططإنذارالحريق:واجهةالمضخاتوالتهوية والتحكمبالإنارة والإنتركم؛FP200 2×2.5مم²في25مم',
 'ELEC2:8':'FA-106 المراقبةالمركزية:أعدادEL/EXITوتوصيل2Core+E2.5مم²FP200في25مم؛بلاXY',
 'ELEC2:9':'FA-107 الإخلاءالصوتي:تحكمفيCOMMANDROOMوبطاريةDCوربطFACP؛بلاXY',
 'ELEC2:10':'FA-108 تفاصيلإنذارالحريق:لوحةومكررومناسيبالتثبيت؛بلاXY',
 'ELEC2:17':'LPT-106 تفاصيلصواعق:25×3مم،ربطبالتسليحواختبارالحفرة؛تعارض16ممبالمفتاحمع20ممبالتفصيل',
 'ELEC2:24':'LC-106 مخططSMATV:ثلاثأطباق120سمNilesat/Arabsat/Hotbird؛RG11/RG6وحامل16IF+1RF؛بلاXY',
 'ELEC2:25':'LC-107 مخططالإنتركم/CCTV؛توزيعوظيفيوتوصيلاتمنطقيةبلاXY',
 'ELEC2:26':'LC-108 تفاصيلالتيارالخفيف؛مقاساتوتركيببلاXY',
 'ELEC2:33':'TE-105 مخططهاتف:2×100مم،MDFرفان42U،MINI-ODF600×600،ONU60×60×15/30؛لايشكل مسارXYZ',
 'ELEC2:34':'TE-106 تفصيلغرفMDFوGSMوODFورف12U300عمقًا؛بلاXY',
}
def _load():return json.load(open(DATA,encoding='utf-8'))
def _source(M,sk):
 key,p=sk.split(':');label=f'{key} ص{p} — هندسة مباشرة من الرسم؛ electrical_remaining_extract.py'
 if label not in M['sp']:M['sp'].append(label)
 return M['sp'].index(label)
def _attrs(row,q,sk,sysname):
 return {'sys':sysname,'source_page':sk,'source_transform':row['registration'],'source_pdf_points':q.get('path_pdf',[q['pdf']]),'source_xy':q.get('path',q['xy']),'source_drawing':q['drawing'],'kind':q['kind']}
def apply_corrections(M,els=None):
 els=M['els'] if els is None else els;D=_load();hist={z['id']:z for z in M.get('meta',{}).get('electrical_model_corrections',[])};changes=[]
 def change(e,sk,kind,new_g,new_l,new_t,reason,q=None):
  old={k:copy.deepcopy(e.get(k)) for k in ('l','t','g')};new={'l':new_l,'t':new_t,'g':new_g}
  if old!=new:
   changes.append({'id':e['id'],'sheet':sk,'reason':reason,'before':old,'after':copy.deepcopy(new),'status':'model_corrected_source_preserved'})
   if e['id'] not in hist:hist[e['id']]=copy.deepcopy(changes[-1])
   else:hist[e['id']]['after']=copy.deepcopy(new)
  e.update(new);a=e.setdefault('a',{});a.update({'sys':'ltg' if kind.startswith('ltg') else 'telephone','model_correction':reason,'assumed':'ارتفاع تثبيت المعدة غير محدد بالمقطع؛ الموضع XY من الرمز'})
  if q:
   a.update(_attrs(D['sheets'][sk],q,sk,a['sys']));a.pop('guess_from',None)
  e['s']=sorted(set(e.get('s',[])+[_source(M,sk)]));return e
 for e in els:
  if e['c']=='E.ltg' and e.get('t') in ('e_G2','elr_clip') and not ID_RE.search(e['id']):
   is_t='-T-' in e['id'];level='T' if is_t else 'R';sk='ELEC2:16' if is_t else 'ELEC2:15';z=27.25 if is_t else 25.25
   q=min((q for q in D['sheets'][sk]['items'] if q['kind']=='tape_clip'),key=lambda q:math.dist(q['xy'],e['g'][1:3]));g=copy.deepcopy(e['g']);g[1:3]=q['xy'];g[-2:]=[z,z+.03]
   change(e,sk,'ltg_clip',g,level,'elr_clip','المشبك أعلى دروة المستوى المرسوم؛ كان عند FFL أو R بدل سطح الغرف T؛ مركز رمز المشبك محفوظ',q)
  if e['c']=='E.ltg' and e['id'] in ('E.ltg-T-0013','E.ltg-T-0015'):
   q=min((q for q in D['sheets']['ELEC2:16']['items'] if q['kind']=='equipment_bond'),key=lambda q:math.dist(q['xy'],e['g'][1:3]))
   x,y=q['xy'];change(e,'ELEC2:16','ltg_bond',['cyl',x,y,3,27.25,27.28],'T','elr_bond','رمز MECH. EQUIPMENT نقطة ربط بالنحاس؛ تصنيفه حفرة تأريض على السطح كان خاطئًا',q)
  if e['c']=='E.lc' and e.get('t') in ('e_T20','elr_mini_odf','elr_mdf_rack') and not ID_RE.search(e['id']):
   if e['l'] in('1','2','3','4','5') and math.dist(e['g'][1:3],[1285,612.5])<40:
    sk='ELEC2:30' if e['l']=='1' else 'ELEC2:31';qs=[q for q in D['sheets'][sk]['items'] if q['kind']=='mini_odf'];assert len(qs)==1;q=qs[0];x,y=q['xy'];f=next(l['ffl'] for l in M['levels'] if l['id']==e['l'])
    change(e,sk,'phone_mini_odf',['b',x,y,60,15,0,round(f+1,3),round(f+1.6,3)],e['l'],'elr_mini_odf','المصنف MDF بالطابق هو MINI-ODF ‏600×600 مم في غرفة TEL؛ الموضع من الرمز',q)
   elif e['l']=='G':
    qs=sorted((q for q in D['sheets']['ELEC2:29']['items'] if q['kind']=='mdf_rack'),key=lambda q:q['xy'][0]);q=qs[0];x,y=q['xy']
    change(e,'ELEC2:29','phone_mdf_rack',['b',x,y,80,80,0,.35,2.35],'G','elr_mdf_rack','صندوق MDF كان في إحداثي التسمية؛ صحح مركز الرف الأول 80×80 سم استنادًا إلى المسقط',q)
 M.setdefault('meta',{})['electrical_model_corrections']=list(hist.values());return changes

def build(M,verbose=False):
 D=_load();els=M['els'];els[:]=[e for e in els if not ID_RE.search(e['id'])]
 M.setdefault('types',{}).update(TYPES);M['mats'].update(MATS);apply_corrections(M)
 ffl={l['id']:l['ffl'] for l in M['levels']};new=[];counts=collections.Counter()
 def add(c,l,g,t,m,sk,q,a=None,mark=None):
  row=D['sheets'][sk];sysname='ltg' if c=='E.ltg' and t not in('elr_earth','elr_earth_bar') and sk!='ELEC2:1' else 'earth' if c=='E.ltg' else 'site_power' if t=='elr_power_duct' else 'telephone'
  attrs=_attrs(row,q,sk,sysname)
  if q.get('path') and g[0] not in ('t','d'):
   attrs['source_path_cm']=q['path'];attrs['source_xy']=[round((min(p[k] for p in q['path'])+max(p[k] for p in q['path']))/2,3) for k in(0,1)]
  attrs.update(a or {});e={'id':f'{c}-{l}-ELR{len(new)+1:04d}','c':c,'l':l,'g':g,'t':t,'m':m,'mark':mark or q['kind'],'a':attrs,'s':[_source(M,sk)]};new.append(e);counts[t]+=1;return e
 for sk,row in D['sheets'].items():
  levels=['2','3','4','5'] if row['level']=='TY' else [row['level']]
  for l in levels:
   for q in row['items']:
    k=q['kind'];x,y=q['xy'];f=ffl[l]
    if k in('down_marker','basement_down_marker','mini_odf'):continue
    if k=='tape_clip' and any(e.get('t')=='elr_clip' and e['l']==l and math.dist(e['g'][1:3],[x,y])<1 for e in els):continue
    if k=='mdf_rack' and any(e.get('t')=='elr_mdf_rack' and e['l']==l and math.dist(e['g'][1:3],[x,y])<1 for e in els):continue
    if k=='equipment_bond' and any(e.get('t')=='elr_bond' and math.dist(e['g'][1:3],[x,y])<1 for e in els):continue
    if k in('earth_pit','clean_earth_pit'):
     typid='elr_clean_pit' if k=='clean_earth_pit' else 'elr_earth_pit';z=f
     add('E.ltg',l,['b',x,y,40,40,0,round(z-.4,3),round(z,3)],typid,'m_earth',sk,q,{'assumed':'الحفرة 40×40 سم وعمق 40 سم ومنسوب غلافها FFL افتراض؛ غير مبين في الرسم'},f'EPIT-{l}-{q["drawing"]}')
     add('E.ltg',l,['cyl',x,y,.8,round(z-4,3),round(z-.4,3)],'elr_earth_rod','m_cu',sk,q,{'assumed':'القضيب16مم وطول3.6ممنالمفتاح؛بدايتهأسفلحفرةعمق40سمافتراض'})
    elif k=='earth_bar':
     op=q['outline_pdf'];rot=90 if op[3]-op[1]>op[2]-op[0] else 0
     add('E.ltg',l,['b',x,y,30,4,rot,round(f+1,3),round(f+1.03,3)],'elr_earth_bar','m_cu',sk,q,{'assumed':'أبعاد القضيب 30×4×3 سم وارتفاع FFL+1 م افتراض؛ المركز من رمز التهشير'})
    elif k=='earth_cable':
     add('E.ltg',l,['t',[[a,b,round(f+1,3)] for a,b in q['path']],.94],'elr_earth','m_cu',sk,q,{'section_mm2':70,'assumed':'الارتفاع FFL+1 م افتراض؛ الدائرة المكافئة لقطاع 70 مم²، الغلاف 38 مم غير ممثل'})
    elif k=='lightning_tape':
     z=25.25 if l=='R' else 27.25 if l=='T' else f
     a,b=q['path'];L=math.dist(a,b);ang=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]));geo=['b',round((a[0]+b[0])/2,1),round((a[1]+b[1])/2,1),round(L,1),2.5,round(ang,3),round(z,3),round(z+.003,3)]
     add('E.ltg',l,geo,'elr_tape','m_cu',sk,q,{'section_mm':'25×3','trace_cm':[[a[0],a[1],z],[b[0],b[1],z]],'assumed':'امتدادالشريطخارجحدوددروةالغرفةيحتاجتفصيلتثبيت؛XYيحفظالرسم؛منسوبB/GغيرمحددافترضFFL'})
    elif k=='tape_clip':
     z=25.25 if l=='R' else 27.25
     add('E.ltg',l,['cyl',x,y,1.5,z,round(z+.03,3)],'elr_clip','m_cu',sk,q,{'assumed':'مشبك تمثيلي 3×3سم عند دروة المستوى المرسوم؛ الأبعاد والتفصيل غير محددين'})
    elif k in('equipment_bond','air_terminal'):
     t='elr_bond' if k=='equipment_bond' else 'elr_air_terminal';z=27.25;h=.03 if k=='equipment_bond' else .5;r=3 if k=='equipment_bond' else .8
     add('E.ltg',l,['cyl',x,y,r,z,round(z+h,3)],t,'m_cu',sk,q,{'assumed':'القطر 16 مم وقاعدة عند دروة +27.25 م افتراض؛ طول القضيب 500 مم موثق' if k=='air_terminal' else 'شكلالمشبكوقاعدةالربطبالمعدةغيرمبين؛رمز الربطبحجمتعبيري6سم'})
    elif k in('site_power_duct','site_phone_duct','site_fiber_stub'):
     t={'site_power_duct':'elr_power_duct','site_phone_duct':'elr_site_phone','site_fiber_stub':'elr_fiber'}[k];dia=q.get('dia_mm',10)/10
     add('E.tray',l,['t',[[a,b,-.6] for a,b in q['path']],dia],t,'elr_power' if k=='site_power_duct' else 'elr_phone',sk,q,{'dia_mm':q.get('dia_mm'),'assumed':'منسوب المحور −0.60 م افتراض؛ حد الرسم مفتوح ولا توجد إحداثيات لمرفق الشبكة العامة'})
    elif k in('mdf_rack','onu'):
     rack=k=='mdf_rack';w=q.get('width_cm',80);d=q.get('depth_cm',80);z=f if rack else f+1;h=2 if rack else .6
     add('E.lc',l,['b',x,y,w,d,q.get('rotation',0),round(z,3),round(z+h,3)],'elr_mdf_rack' if rack else 'elr_onu','m_panel',sk,q,{'assumed':'ارتفاع غلاف الرف 2 م افتراض' if rack else 'ارتفاع أسفل ONU عند FFL+1 م افتراض'})
    elif k in('rj45_single','rj45_dual','phone_floorbox'):
     floor=k=='phone_floorbox';t='elr_floorbox' if floor else 'elr_'+k;w=d=25 if floor else 9;z=f-.08 if floor else f+.3;h=.08 if floor else .09
     add('E.lc',l,['b',x,y,w,d if floor else 4,q.get('rotation',0),round(z,3),round(z+h,3)],t,'m_plate_lc',sk,q,{'ports':2 if k in('rj45_dual','phone_floorbox') else 1,'assumed':'أبعادالصندوق25×25×8سم افتراض' if floor else 'أبعاد اللوحة 9×4×9 سم ومنسوب FFL+0.3 م افتراض؛ XY من رأس مثلث رمز المخرج، وبعض الرموز تشير إلى نافذة أو تفصلها مسافة عن الجدار','network_gap':'المسار إلى ONU غير مرسوم؛ بانتظار تأكيد المسار الفعلي'})
    elif k in('phone_tray','gsm_tray'):
     z=f+2.7
     for j,(a,b) in enumerate(zip(q['path'],q['path'][1:])):
      part=dict(q,path=[a,b],path_pdf=q['path_pdf'][j:j+2]);L=math.dist(a,b);ang=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0]));add('E.tray',l,['b',round((a[0]+b[0])/2,1),round((a[1]+b[1])/2,1),round(L,1),q['width_mm']/10,round(ang,3),round(z,3),round(z+.05,3)],'elr_'+k,'m_tray',sk,part,{'trace_cm':[[a[0],a[1],z],[b[0],b[1],z]],'assumed':'المنسوب FFL+2.70 م افتراض؛ الوصف HIGH LEVEL؛ الأبعاد 450/300×50 مم موثقة'})
 # Derived down conductors only between the same source position. Source mismatch remains visible/open.
 rows=[]
 for l,sk in [('B','ELEC2:11'),('G','ELEC2:12'),('1','ELEC2:13'),('2','ELEC2:14'),('3','ELEC2:14'),('4','ELEC2:14'),('5','ELEC2:14'),('R','ELEC2:15')]:
  rows.append((l,sk,[q for q in D['sheets'][sk]['items'] if q['kind'] in('down_marker','basement_down_marker')]))
 for (la,sa,aa),(lb,sb,bb) in zip(rows,rows[1:]):
  for b in bb:
   a=min(aa,key=lambda a:math.dist(a['xy'],b['xy']))
   if math.dist(a['xy'],b['xy'])>3:continue
   x0,y0=a['xy'];x1,y1=b['xy'];z0=ffl[la];z1=25.25 if lb=='R' else ffl[lb]
   add('E.ltg',lb,['b',x1,y1,2.5,.3,0,round(z0,3),round(z1,3)],'elr_down','m_cu',sb,b,{'source_other_page':sa,'source_other_pdf':a['pdf'],'source_other_xy':a['xy'],'trace_cm':[[x1,y1,z0],[x1,y1,z1]],'derived_source_tolerance_cm':round(math.dist(a['xy'],b['xy']),2),'assumed':'القطاع25×3مم؛امتدادالموصلرأسيبينرمزينمتطابقين±3سم؛وجهالشريطافتراضولاانحرافمرسوملإغلاقفروقأكبربالمسقط'})
 els.extend(new)
 details=[]
 for sk,note in DETAIL_REFS.items():
  _source(M,sk);details.append({'sheet':sk,'note':note,'spatial':False})
 M.setdefault('meta',{})['electrical_remaining']={'counts':dict(counts),'plan_audit':{k:r['audit'] for k,r in D['sheets'].items()},'source_conflicts':D['conflicts'],'details':details,'notes':['XY من الرموز والمسارات المسجلة؛ لا تصحيح نحو أقرب سند','المخططات التوضيحية بلا مواضع XYZ','اتصال الهاتف بين ONU والمخارج غير مرسوم']}
 if verbose:print('electrical remaining:',len(new),dict(counts),'source conflicts:',len(D['conflicts']))
 return len(new)
