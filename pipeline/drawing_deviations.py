# -*- coding: utf-8 -*-
"""Model corrections and drawing conflicts; independent of physical-site clash status."""
import json,os,re,collections,hashlib
from support import zr,poly_of
HERE=os.path.dirname(__file__)
def read(name):
 p=os.path.join(HERE,'data',name+'.json');return json.load(open(p)) if os.path.exists(p) else {}
def apply(M,els):
 issues=[]
 def add(id,title,status,source,note,lv=None,xy=None,z=None,eids=None,before=None,after=None):
  issues.append(dict(id=id,title=title,status=status,source=source,note=note,level=lv,xy_cm=xy,z_m=z,elements=eids or [],before=before,after=after))
 corrections=M.get('meta',{}).get('drawing_corrections',{})
 floors=[v for v in corrections.values() if v.get('new_z_m')]
 for oldtop,vs in sorted(collections.defaultdict(list, {t:[v for v in floors if v['new_z_m'][-1]==t] for t in set(v['new_z_m'][-1] for v in floors)}).items()):
  v=vs[0];add('DP-FFL-'+str(oldtop),'منسوب تشطيب البدروم المحلي — '+str(len(vs))+' قطعة','corrected',v['source'],'رفع التشطيب إلى المنسوب المرسوم وتجديد الملء المشتق تحته؛ المرجع العام B−3.70 والعناصر الإنشائية محفوظان. كل قطعة لها سجل مستقل في meta.drawing_corrections.','B',v['xy_cm'],oldtop,[r['element'] for r in vs],v['old_z_m'],v['new_z_m'])
 add('DP-TANKS','حدود خزاني GRP كانت مستخرجة كمواسير22مم','corrected','MECH2 ص17/22','حذف4مواسير الحدود واستبدالها بخزانين300×250×200سم في مركزي المصدر، على FFL23.35.','R',[374.85,174.9],23.35,[e['id'] for e in els if e['t'].startswith('ws_tank_')],{'ids':list(k for k in corrections if 'P.cold-R-M' in k),'z_axis':26.15},{'z_base':23.35,'centres':[[374.85,174.9],[772.75,174.9]]})
 tank_ids=[e['id'] for e in els if e['t'].startswith('ws_tank_')]
 add('DP-PG-TANK-SOURCE','مواضع وأبعاد خزانات السطح تختلف بين العمارة والميكانيكا','source_conflict','ARCH1 ص9 A106 / MECH2 ص17 WS-010 وص22 WS-104','A106 يرسم خزاني 300×200 سم تقريبًا: مركزي الغرب465.344/240.463 والشرق805.109/240.463؛ رموز الألواح في WS-010 نحو374.814/174.917 و772.761/174.917 بأبعاد300×250.2 سم. فرق المصدر111.768 سم غربًا و73.095 سم شرقًا؛ WS-104 يطابق WS-010 بفارق0.55/0.31 سم. بقي جسم الخزان من الميكانيكا والبرجولة من العمارة،فتداخل عمودا البرجولة مع جسم الخزان يحتاج حسم المصدر. لم تنقل أي ورقة أو جسم.','R',[374.85,174.9],23.35,tank_ids+[e['id'] for e in els if e['c']=='A.pergola' and e.get('a',{}).get('unit')=='grp'],{'ARCH':{'centres_cm':[[465.344,240.463],[805.109,240.463]],'plan_cm':[300,199.71]}},{'MECH':{'panel_centres_cm':[[374.814,174.917],[772.761,174.917]],'plan_cm':[300,250.2]}})
 for key,v in read('reg_verified').items():
  if key.startswith(('MECH','ELEC')):add('DP-REG-'+key.replace(':','-'),'تصحيح تسجيل المسقط '+key,'corrected',key,v['evidence'],None,None,None,[],{'old':'تسجيل جزئي خاطئ'},{'reg':v['reg']})
 add('DP-IR-FFL','تعارض منسوب غرفة مضخات الري','source_conflict','ARCH1 ص4 A101 / ARCH2 ص57 A2500 / MECH2 ص25 IR-100','المعماريان −3.50 م، الميكانيكي −3.30 م؛ اتبع جسم المضختين أرضية العمارة، وبقي فرق 20 سم مسجلًا للحسم.','B',[618.7,1644.75],-3.50,[e['id'] for e in els if e['t']=='irr_pump'],{'IR-100':-3.30},{'A101/A2500':-3.50})
 I=read('water_site').get('irrigation',{});gap=I.get('riser_plan_gap',{})
 add('DP-IR-RISER','اختلاف صاعد الري بين المسقطين','source_conflict','MECH2 ص25–26',json.dumps(gap,ensure_ascii=False)+'؛ لم يضف صاعد مائل أو وصلة بلا مصدر.','G',[1455.1,3218.1],.85,[e['id'] for e in els if e['a'].get('sys')=='irrigation'],[1469.5,3232.7],[1455.1,3218.1])
 add('DP-WS-FILL','نهاية تعبئة خارج حدود حوض الحريق المعماري','source_conflict','MECH2 ص17 WS-010 / ARCH2 ص57 A2500','نهاية التعبئة عند الموضع المرسوم خارج الحوضين المعماريين؛ لا تنقل إلى أقرب حوض لادعاء الاتصال. يلزم حسم تقسيم الخزانات ووجهة التعبئة.','B',[354.5,1070.1],-.9,[e['id'] for e in els if e['t']=='ws_fill_drop'])
 add('DP-WS-DT','وحدة وسعة الخزان المنزلي تختلف بين العمارة والميكانيكا','source_conflict','ARCH2 ص57 A2500 / MECH2 ص17/23/25','A2500 يكتب5500 USG بجوار RCC WATER FOR DOMESTIC وA=9.45م² وV=28.35م³؛ مخططات الميكانيكا تحدد5200 IGal. قيمتان من أصلين مختلفين، وليست مقارنة بالنموذج القديم. لم يغير جسم الحوض لتقليد رقم نصي؛ يلزم حسم السعة والوحدة وصافي حجم الماء.',None,None,None,[e['id'] for e in els if e['c']=='P.tank' and e.get('mark')=='DT' and e.get('t')=='tank_water'],{'ARCH2:57 A2500':'5500 USG','raw_texttrace_index':41},{'MECH2 WS/IR':'5200 IGal'})
 add('DP-SIGN-R','لوحة علامات السطح تحمل مسقط الدور الأول','source_conflict','ARCH2 ص48 A2204','العنوان Roof Floor Signage Plan، داخل الرسم FIRST FLOOR PLAN / A2202 ووحدات1ST؛ لم تُنقل علاماته إلى السطح.','R',None,23.35)
 add('DP-SIGN-MOUNT','مواضع العلامات لا تحسم وجوه تركيبها','source_gap','ARCH2 ص34–35/44–47','أضيف119مؤشرًا عند وسوم المسقط، لا119لوحة مادية؛ ارتفاع المؤشر افتراض موسوم. يلزم حسم الوجه والارتفاع من تفصيل التثبيت لكل نوع.',None,None,None,[e['id'] for e in els if e['t']=='signage_plan_marker'])
 windows=read('window_source_height_review')
 if windows:
  active={e['id']:e for e in els}
  changed=[q for q in windows.get('records',[]) if q['id'] in active and active[q['id']]['g'][5:7]==q['after_g'][5:7]]
  add('DP-WINDOW-OUTER-HEIGHT','تصحيح ارتفاع النوافذ الخارجي إلى الأبعاد المطبوعة','corrected','ARCH2 ص14 A801 وص15 A802 وص31 A1500','كانت110 مجموعات نوافذ شقق ترتفع252سم بدل250سم فوق عتبة60سم،وكان إطار CW19 الأخير يزيد2.5سم فوق إجمالي2065سم. أُصلح المولد بوضع الإطار العلوي داخل الحد الخارجي. صُححت652قطعة إطار وزجاج دون تغيير عدد المجموعات أو FFL. ارتفاع المصدر مستقل عن مراجعة XY وإسناد الواجهة والمناسيب المطلقة وقطاع الإطار ومادته؛ لا تعتمد تلك القيم من هذا التصحيح.',None,None,None,[q['id'] for q in changed],{'apartment_outer_cm':252,'stair_outer_cm':2067.5},{'apartment_outer_cm':250,'stair_outer_cm':2065,'changed_parts':len(changed),'groups':111})
 w7=[e for e in els if e['t'] in ('lobby_W7_detail','corridor_W7_detail','entrance_W7_detail')]
 if w7:
  f=w7[0];p=poly_of(f['g']);xy=[round(p.centroid.x,2),round(p.centroid.y,2)]
  add('DP-W7','استكمال كسوة الواجهات المحددة بالمسقط والقطاع','corrected','ARCH1 ص4–7 A101–A104 / ARCH2 ص34–35 A1600/A1601','لوحتا البدروم بارتفاع225 سم،و200 قطعة بالممرات1–5 بارتفاع235 سم،و5 قطع على الجدار الغربي لدخول الأرضي بارتفاع340 سم. سماكة20 مم؛ قص على الأجسام الموجودة مع إبقاء الفتحات ولوح W13. كسوة مشتقة من الوجوه،ولا يعني ذلك تطابق كل حافة عمود مع العمارة؛ فرق نحو0.33 سم موثق دون نقل الإنشاء.',f['l'],xy,zr(f['g'])[0],[e['id'] for e in w7],{'before':'كسوة الواجهات المحددة مفقودة'},{'panels':len(w7)})
 w13=[e for e in els if e['t'] in ('corridor_W13_detail','entrance_W13_frame','entrance_mirror')]
 if w13:
  f=w13[0];p=poly_of(f['g']);xy=[round(p.centroid.x,2),round(p.centroid.y,2)]
  add('DP-W13','ربط W13 والمرآة بالوجه الصحيح','corrected','ARCH1 ص5–7 / ARCH2 ص34–35 A1600/A1601','ثبّتت أربعة أزواج إطارات أبواب عكس جهة قراءة C–C؛ أضيفت5 لوحات رقم طابق180×235 سم،وإطار مرآة الدخول300×340 سم بأربعة أجزاء وفتحة140×210 سم. سُمك المرآة4 مم والبروز والمثبتات غير المرقمة افتراضات موسومة. لم تعمم كسوة على وجوه غير محددة.',f['l'],xy,zr(f['g'])[0],[e['id'] for e in w13],{'before':'لم يحسم الربط في المراجعة الأولية'},{'parts':len(w13)})
 add('DP-SW-END','طرف خط صرف الموقع مد إلى مركز MH','corrected','MECH2 ص1','أعيد الطرف إلى الرأس المرسوم2029.2سم بدل2059.1سم، دون اختراع30سم داخل الغرفة.','G',[2029.2,1990.2],-1.375,[e['id'] for e in els if e['t']=='pipe_site'],[2059.1,1990.2],[2029.2,1990.2])
 add('DP-SW-CO','فتحات التنظيف كانت عند النص بدل الرمز','corrected','MECH2 ص27 SW-101','تصحيح6مواضع إلى محور رمزCO ذي العارضة العمودية بفروق15–23سم؛ أضيف رمزسابع غير موسوم أثبته المفتاح.','G',[143.8,712.2],next((e['g'][4] for e in els if e['t']=='storm_co'),None),[e['id'] for e in els if e['t']=='storm_co'])
 add('DP-SMK-XY','مراكز صواعد دخان الممرات كانت موحدة','corrected','MECH1 ص19–21','الموضع محفوظ لكل مسقط الآن؛ تصحيح انحرافات0.4–0.8سم وإزالة استبدال أول رأس بمجرى السطح. فرق بسيط بين الأوراق لا يبرر نقل الرسم.','R',[1326.8,1044.8],23.35,[e['id'] for e in els if e['t'] in ('riser_co_fa','riser_co_ea')])
 for v in corrections.values():
  if v.get('new_geometry'):
   title='إعادة العنصر إلى رمز المسقط الفعلي'
   add('DP-RESTORE-'+v['element'],title,'corrected',v['source'],v['note'],v.get('level') or next((e['l'] for e in els if e['id']==v['element']),None),v.get('xy_cm') or v.get('source_xy_cm') or (v['new_geometry'][1:3] if v['new_geometry'][0] in ('b','cyl') else None),zr(v['new_geometry'])[0],[v['element']],v['old_geometry'],v['new_geometry'])
 for i,d in enumerate(read('electrical_remaining').get('conflicts',[])):
  paired=d.get('from_cm') is not None and d.get('to_cm') is not None
  add('DP-LTG-'+str(i+1),'اختلاف موضع رمزي موصل الصواعق بين الأدوار' if paired else 'هوية الطرف المقابل لموصل الصواعق غير مثبتة','source_conflict' if paired else 'source_gap',d.get('from_sheet','')+' / '+d.get('to_sheet',''),('الموضعان موثقان، لكن لا توجد وصلة مرسومة بينهما؛ المقارنة تشخيصية ولا تثبت اتصالًا أو مسارًا ثلاثي الأبعاد. ' if paired else 'لا يوجد طرف مقابل محدد من المصدر؛ غياب الهوية ليس اختلاف XY مؤكدًا. لم يختر أقرب رمز ولم تنشأ وصلة بلا مصدر. ')+d.get('note',''),None,d.get('to_cm'),None,[],d.get('from_cm'),d.get('to_cm'))
 eg=collections.defaultdict(list)
 for v in corrections.values():
  if v.get('scope')=='model_xy_correction_only':eg[(v['source'],v['level'])].append(v)
 for (source,lv),vs in sorted(eg.items()):
  first=vs[0]
  add('DP-E-XY-'+source.replace(':','-')+'-'+lv,'استعادة مراكز الرموز الكهربائية المرسومة','corrected',source,str(len(vs))+' رمزًا كان منحرفًا؛ أعيد XY إلى الرمز الخام مع حفظ المستوى وZ والاتجاه والمقاس. كل ID له سجل قبل/بعد وبصمة مصدر في electrical_source_restore.json وmeta.drawing_corrections.',lv,first['new_xy_cm'],None,[v['element'] for v in vs],{'corrected':len(vs),'max_displacement_cm':round(max(v['delta_cm'] for v in vs),4)},{'xy_from_pdf':True,'z_unchanged':True})
 if M.get('meta',{}).get('hvac_source_restore'):
  active_ids={e['id'] for e in els}
  for eid,row in read('restore_hvac_source').get('records',{}).items():
   if eid not in active_ids:continue
   src=row['source']; fcu=row['type']=='fcu'
   add('DP-HVAC-XY-'+eid,'استعادة موضع '+('FCU-R-LR' if fcu else 'الترموستات T')+' من رمز المسقط','corrected',src['source_page']+' / '+src['source_sheet'],'أعيد مركز XY إلى '+('المستطيل المرسوم وزاويته' if fcu else 'دائرة الرمز الخام المقترنة بحرف T أسفلها')+'؛ أُلغي النقل الموروث إلى أقرب جدار. هذا يثبت موضع الرمز فقط؛ وجه التثبيت وأبعاد الجسم وZ والمادة واللون الفعلي غير مثبتة. سجل قبل/بعد ومعرف الرسم وبصمة PDF محفوظة في restore_hvac_source.json.',row['level'],src['source_xy'],None,[eid],{'geometry':row['before_g'],'legacy_snap_cm':row.get('legacy_snap_cm'),'legacy_guess_host':row.get('legacy_guess_host')},{'source_xy_cm':src['source_xy'],'source_angle_deg':src['source_angle'] if fcu else None,'Z_dimensions_material_unchanged':True,'physical_mount_pending':True})
 for row in read('electrical_trace_restore').get('records',[]):
  ids=['E.tray-'+row['level']+'-ETR'+str(n).zfill(4) for n in (1,2,3,4)]
  add('DP-POWER-TAIL-'+row['id'],'استكمال ساق دائرة قوى مرسومة حتى سهم المصدر','corrected',row['source'],'كان فلتر CONNE قد أسقط منحنى وخطًا وسهمًا فعليين من POWER-CONN. استعيدت ساق الدائرة وحدّها عند السهم من المصدر؛ لا مسار مخترع من السهم إلى اللوحة. وصلة صغيرة إلى جسم العرض داخل glyph مشتقة ومعلنة، والمنسوب والقطر والمضيف غير مثبتة.',row['level'],row['source_anchor_xy'],None,[row['id']]+ids,{'before':'ساق المصدر مفقودة من الاستخراج'},{'raw_paths':ids[:2],'arrow_boundary':ids[2],'derived_proxy_connector':ids[3],'board_feeder_added':False})
 srf=M.get('meta',{}).get('roof_lift_source',{})
 if srf:
  new_ids=srf.get('new_ids',[])
  add('DP-LIFT-ROOF-COVER','استكمال غطاء المصعدين المحلي والدروات','corrected','ARCH1 ص8 A105 / ARCH2 ص17 A900 قطاع5 / STR ص23 / ARCH1 ص18 A500','حد الغطاء المعماري من A105، قمة الخرسانة24.00 وسماكتها25سم من STR، التشطيب F12 عند24.20 ودروة24.65 من العمارة. الجسم المعماري مركب من هذه الشواهد؛ لا يثبت حد ارتكاز بلاطة S. لم تُرفع البلاطة العامة. لم تُنشأ طبقات17سم غير المفصلة تحت البلاط.','R',[1734.8117,1120.5255],24.20,new_ids,{'local_display_floor_m':23.35},{'concrete_top_m':24.00,'F12_top_m':24.20,'upstand_top_m':24.65,'new_parts':len(new_ids)})
  add('DP-LIFT-R-FALSE-LANDING','إزالة توقف المصعد المختلق على السطح','corrected','ARCH1 ص8 A105 / ARCH2 ص17 A900 قطاع5','كان المولد يكرر أبواب الهبوط والنداء والجدار الأمامي عند R. المخطط يبيّن غطاء البئر ومعدات الرفع ولا يبيّن هذا التوقف. أُصلح مولد extras كي لا يعيد20جزءًا زائفًا؛ بقيت المقصورتان والتوقفات B وG و1–5. معرفات20جزءًا قبل التصحيح محفوظة في roof_lift_source.json.','R',None,None,[],{'retired_ids':srf.get('removed_roof_landing',[])},{'stops':['B','G','1','2','3','4','5'],'R_landing_generated':False})
  add('DP-LIFT-ROOF-BEARING','حد ارتكاز الغطاء الإنشائي يحتاج حسم المصدر','source_gap','STR ص23 / ARCH1 ص8 A105','STR يثبت CL24.00 وسمك25سم، لكن لا يوجد حد مغلق فريد للبلاطة المحلية. غلاف وجوه الدعامات460×240سم ليس محيط البلاطة؛ الحد المعماري440×240سم مستقل. جسم الغطاء معماري مشتق، ولم يُنشأ S.slab من غلاف الدعامات. يلزم حسم الارتكاز والبروز وطبقات17سم أسفل F12.','R',[1734.8117,1120.5255],24.00,new_ids)
  fcu=next((e for e in els if e['id']=='M.equip-R-S0225'),None)
  if fcu:
   add('DP-FCU-LIFT-HEIGHT','منسوب جسم FCU-R-LR يحتاج مطابقة الغطاء','model_candidate','MECH1 ص6 AC105 وص7 AC106 / ARCH1 ص8 A105 / ARCH2 ص17 A900','XY أعيد إلى رمز FCU-R-LR الخام، والجدول يسمي خدمته Lift Room. جسم العرض عند26.07–26.37م، فوق سطح الغطاء24.20 بنحو1.87–2.17م. FFL24.20 لا يثبت ارتفاع تثبيت الوحدة أو مسار اتصالها بالغرفة؛ لا اعتماد لهذا Z ولا خفض تلقائي لمجرد أقرب سقف.','R',fcu['g'][1:3],zr(fcu['g'])[0],[fcu['id']]+new_ids,{'body_z_m':zr(fcu['g'])},{'cover_FFL_m':24.20,'mount_elevation':'unverified'})
 lhs=M.get('meta',{}).get('lift_head_supports',{})
 if lhs:
  ids=lhs.get('new_structural_ids',[])
  add('DP-LIFT-HEAD-WALLS','استكمال رأسي الجدارين الإنشائيين للمصعدين','corrected','STR ص23 S-COL-HATCH رسم3489/3488 / ARCH2 ص17 A900 قطاع5','أضيف جداران فقط بحدود الخرسانة المغلقة من STR في موضعيهما؛ الارتفاع60سم مشتق بين CL23.15 وأسفل الغطاء24.00−0.25=23.75. لا تسليح أو مرابط مختلقة؛ هذه الإضافة لا تغير عناصر S القديمة. التصحيحات المحددة الأخرى للخوازيق وتمثيل البلاطات وتصنيف C9 لها أدلة مستقلة. المنسوب المشتق ليس بعدًا مرقمًا لنفس الجدار.','R',None,23.15,ids,{'missing_structural_wall_heads':2},{'new_parts':2,'z_m':[23.15,23.75],'height_status':'datum-derived','bearing_reinforcement':'pending'})
  add('DP-LIFT-HEAD-DETAILS','تفصيل اتصال رأسي الجدارين بالغطاء يحتاج استكمالًا','source_gap','STR ص23 / ARCH2 ص17 A900 قطاع5','حدود المسقط الخام مثبتة. تفاصيل التسليح والوصلات والمرابط والارتكاز لا يثبتها هذا الجرد، ولا تُستنتج من الجدران القائمة.','R',None,23.75,ids)
 bnd=M.get('meta',{}).get('boundary_source_remaining',{})
 if bnd:
  ids=[e['id'] for e in els if re.search(r'-BND\d{4}$',e['id'])]
  add('DP-BOUNDARY-CSTAR-CB1','استكمال أعمدة وغطاء وحشوات السور من المصدر','corrected','STR ص31–32 S26/S27 / ARCH1 ص4 A101 وص16 A400','استبدلت ثلاثة أغلفة A.site عامة بحدود41 عمودًا مغلقًا C* و37 حشوة بلوك بين وجوهها و6 قطع غطاء CB1 تغطي جميع رؤوس الأعمدة. حدود الأعمدة من المصدر الخام؛ الغطاء والحشوات مشتقة من خطوط المسقط والوجوه. القطاع200×300مم وقمة CL+3.00؛ منسوب بقية الجزء فوق الأرض مشتق. صفر تراكب حجمي داخل هذه المجموعة وصفر مساحة رأس غير مغطاة، دون قص إلى أغلفة الملف القديم أو نقل الإنشاء. فرق الحجم الكلي موثق ويعود إلى حدود المصدر والفواصل.', 'G',None,3.00,ids,{'retired_envelopes':bnd.get('retired_source_envelopes',[]),'volume_m3':bnd.get('before_volume_m3')},{'new_parts':len(ids),'new_structural':len(bnd.get('new_structural_ids',[])),'volume_m3_by_category':bnd.get('after_volume_m3_by_category',{}),'head_uncovered_cm2':bnd.get('source_column_head_uncovered_area_cm2'),'internal_positive_volume_overlap':bnd.get('assembly_positive_volume_overlap_count')})
  add('DP-BOUNDARY-CB1-REBAR','اختلاف تسليح CB1 بين الجدول والقطاع','source_conflict','STR ص32 S27 — جدول CB1 / قطاع BW2','الجدول يحدد2T12 والقطاع يحدد2T16. هذا اختلاف مواصفة تسليح حرفي وليس تصادمًا هندسيًا أو اختلاف منسوب. لم يُنشأ حديد للغطاء قبل حسم المرجع.','G',None,3.00,[e['id'] for e in els if e.get('t')=='boundary_coping_cb1'],{'table':'2T12'},{'section':'2T16','reinforcement_added':False})
  add('DP-BOUNDARY-JOINTS','تنفيذ فواصل السور واتصال الغطاء يحتاج حسمًا','source_gap','STR ص31–32 S26/S27','النص يحدد ثلاثة فواصل2سم بينما الرمز الرسومي يقاس نحو2.96–3.18سم، وخط الغطاء في المسقط مستمر. قطعه عند الوجوه اشتقاق مصرح به من النص؛ قياس الرمز لا يثبت عرض التنفيذ. يلزم تفصيل الفاصل وربط الأعمدة والتسليح والبلوك والتشطيب.','G',None,None,ids)
 raft=M.get('meta',{}).get('raft_source_restore',{})
 if raft:
  add('DP-RAFT-PC1-SOURCE','تصحيح حدود اللبشة وPC1 من المخطط الإنشائي الخام','corrected','STR ص11 — S-COLUMN رسم3561 وPILES$0$ST-PILE-Caps رسم6285،وسماكتا80/150سم','أعيد الحد الخارجي وحد PC1 من مضلعين مغلقين في الورقة نفسها. امتداد PC1 القديم1سم خارج اللبشة كان إدخالًا يدويًا، لا تفصيلًا مرسومًا. جسم80سم هو الحد الخارجي ناقص PC1 الخام؛ لم تُملأ مساحة buffer0 ولم يُقص PC1 إلى الحد القديم. فرق حافتي المصدر0.00043سم من دقة PDF ولا يثبت اختلاف تنفيذ. Z والمادة والتسليح القائمة لم تُعتمد بهذا التصحيح.','B',[-30.5388,-30.7018],None,raft.get('ids',[]),{'old_outer_max_difference_cm':1.4533164,'old_PC1_max_difference_cm':.5490587,'old_invalid_hole_outside_area_cm2':5782},{'source_valid_domain':True,'geometry_relation':raft.get('source_geometry_relation'),'Z_and_thickness_unchanged':True,'physical_bearing_approval':False})
 stp=M.get('meta',{}).get('structural_topology_repairs',{})
 if stp:
  add('DP-SLAB-TOPOLOGY','إصلاح تمثيل فتحة الدرج الملامسة لحافة ست بلاطات','corrected','هندسة المجسم الحالية / structural_topology_repairs.json؛ ليس تحقق موضع من PDF','كانت فتحة الدرج حلقة ثقب تلامس المحيط، فأنتجت مضلعًا غير صالح عند95/1040سم. أعيد تمثيل المجال نفسه كتجويف في المحيط: صفر فرق للمجال الخارجي ناقص الفتحات، وصفر تغيير مساحة أو Z أو موضع حد أو إضافة فتحة. هذا يصلح الرسم والتحليل ولا يعتمد حدود أو فتحات الملف القديم كمصدر.',None,[95,1040],None,stp.get('records',[]),{'invalid_touching_hole_slabs':6},{'valid_polygon_slabs':6,'defined_domain_symdiff_cm2':0,'holes_added':0,'source_placement_verified':False})
 wheels=[e for e in els if e.get('a',{}).get('geometry_encoding_correction')]
 if wheels:
  add('DP-PARKING-WHEEL-ENCODING','إصلاح تمثيل ثقبي رمزي مواقف ذوي الإعاقة','corrected','مولد extras.parking_details؛ ليس تحقق موضع أو مقاس من PDF','حلقة عجلة الرمز كانت ترسل قائمة نقاط كثقب بدل قائمة حلقات، فيتعذر قراءتها كمضلع. صُحح غلاف القائمة فقط؛ كل نقطة وZ والمساحة والمجال المقصود محفوظان. هذا إصلاح ترميز للرسم ولا يعتمد تفاصيل الرمز القديمة كأبعاد تنفيذ.', 'G',None,.205,[e['id'] for e in wheels],{'malformed_hole_lists':2},{'valid_annuli':2,'defined_domain_symdiff_cm2':0,'source_placement_verified':False})
 landing=[e for e in els if e.get('a',{}).get('landing_ffl_correction_m')==0.20]
 if landing:
  add('DP-LIFT-B-LANDING','تصحيح هبوط المصعد بالبدروم بفارق20سم','corrected','ARCH1 ص4 A101 ردهة المصاعد / ARCH2 ص17 A900 قطاع A-A/4 Annotation27/xref6756','المنسوب المحلي المرسوم−3.50م يطابق المخطط والقطاع. صححت أبواب الهبوط والجدار الأمامي والمؤشرات والنداء التابعة له؛ المرجع العامB−3.70م وعمق البئر والمقصورتان مستقلون. لا تغيير في XY؛ ارتفاع تركيب الملحقات وأبعادها القديمة تبقى افتراضات عرض.','B',[1745,1020],-3.50,[e['id'] for e in landing],{'landing_ffl_m':-3.70},{'landing_ffl_m':-3.50,'parts':len(landing),'XY_unchanged':True})
 hvo=M.get('meta',{}).get('hvac_outlets_source_restore',{})
 if hvo and hvo.get('historical_v1_acceptance_revoked'):
  data=read('restore_hvac_outlets_source');counts=data.get('summary',{})
  add('DP-HVAC-OUTLETS-SOURCE','تصحيح أجسام مخارج التكييف واستبعاد الأسهم والخطوط','corrected','MECH1 ص2–5: M_SAD_DIFF/M_RAD_DIFF/M_SAG_GRILL/M_RAG_GRILL','أعيد جرد الجسم من إطاره المربع/X أو قطاعه الشريطي المغلق، بدل صندوق مجموعة تضم أسهمًا وقادة وخطوط مجارٍ. جرد861 مجموعة رسمية يشمل42 مجموعة مفتاح ولا يعني861 جهازًا. بقي471 رمز جسم، وقاعد352 تمثيلًا زائفًا، وفصلت أربع مجموعات ذات جسمين. صُحح142 مركزًا و228 بصمة/زاوية رسمية؛ أكبر انتقال لمركز محفوظ118.72سم. مراجعة22 القديمة ألغيت دلاليًا:21 منها أسهم. حدود الرمز ليست مقاس العنق أو جسم المصنع؛ Z والمادة والمنافذ والتثبيت غير مثبتة.',None,None,None,list(data.get('records',{})),{'old_plan_candidate_groups':819,'historical_v1_body_acceptance_revoked':True},{'actual_body_graphic_anchors':counts.get('reviewed_body_anchor_ids'),'retired_non_device_graphics':counts.get('retired_non_device_ids'),'new_separate_body_graphics':counts.get('split_new_body_ids'),'source_Z_physical_dimensions_ports_mount_material_verified':False})
 hdb=M.get('meta',{}).get('hvac_damper_source',{})
 if hdb:
  data=read('hvac_damper_source');records={**data.get('records',{}),**data.get('additions',{})}
  add('DP-HVAC-DAMPERS-SOURCE','فصل خمسة أزواج مخمّدات وتصحيح مواضع رموزها','corrected','MECH1 ص1–5: M_HVAC_DAM / رموزL مغلقة ومحاور التسجيل الخام','ثبت333 موضع رمز رسومي:328 هوية قائمة وخمسة رموزHDB إضافية. كان كل زوجFD ممثلًا بصندوق واحد بين الرمزين، وفصل كل قطاع مستقل مع إبقاء تكرارCAD المطابق مرة واحدة. ثبت موضع وبصمة/زاوية الرسم فقط؛ لا أبعاد تنفيذية أو منافذ أو Z أو مادة أو وجه تثبيت. حراسة Z الحالية بعد طرحceil_dz إجرائية، ولا تعتمد منسوبًا من المصدر.',None,None,None,list(records),{'retained_old_identities':328,'merged_distinct_pairs':5},{'raw_graphic_anchors':333,'added_distinct_graphics':5,'normalized_assumed_Z_base_guard':True,'physical_source_body_or_Z_verified':False})
  add('DP-HVAC-DAMPERS-ROOF-XY','ستة رموز مخمّدات سطح بلا تسجيل مصدر محسوم','source_gap','MECH1 ص6: M_HVAC_DAM / خطاPLOT LIMIT باسمGRID','الورقة لا تقدم مجموعة محاور تسمح بالتسجيل المباشر: خط رأسي وخط أفقي طويلان يمثلان حد الموقع، والضربات الأخرى صغيرة. اسم طبقةGRID وحده لا يثبت هوية محور. لم تُنقل الرموز الستة أو تُعتمدXY قديمة/تحويل underlay، وبقيت مواضعها غير مثبتة مستقلاً.', 'R',None,None,list(data.get('pending',{})),None,{'source_promotion':False,'geometry_changed':False,'pending_source_transform':6})
 return_gap=read('hvac_return_route_gap')
 if hvo.get('historical_v1_acceptance_revoked') and return_gap:
  rows=return_gap.get('records',[]);existing_ids={e['id'] for e in els};ids=sorted({eid for row in rows for eid in row.get('original_group_ids',[]) if eid in existing_ids})
  add('DP-HVAC-RETURN-ROUTE-GAP','خطوط رجوع هواء مرسومة غير ممثلة كمسارات مستقلة','source_gap','MECH1 ص3–5: M_RAG_GRILL / العمليات الخام فيhvac_return_route_gap.json','المستخرج القديم كان يصدرM_HVAC_SAD كمسارات تغذية فقط. بعد فصل جسم الشبكة عن الخطوط، حُدد44 سجل خط مستقيم/كوع مفتوح و48 رمز قطع منحني، تظهر على المستويات ك70 ضربة خط و72 رمز قطع. هذه ليست142 مجرى كاملًا؛ رمز القطع لا يُملأ بوصلات تخمين. توجد42 شهادة تماس طرف رسومي بوجه شبكة، ولا تثبت منفذًا أو اتصالًا فعليًا. أبعاد النص المجاور سياق لم يُعيّن للمسار؛ المقاس وZ والمادة والسند يحتاجون مرجعًا قبل بناء الجسم.',None,None,None,ids,{'extractor_return_duct_type_count':0},{'raw_open_strokes_unique':44,'raw_break_graphics_unique':48,'instanced_open_strokes':70,'instanced_break_graphics':72,'model_routes_added':0,'physical_connection_verified':False})
 protected_mount=[e for e in els if str(e.get('a',{}).get('mount_gap','')).startswith('الرمز في موضعه المرسوم')]
 if protected_mount:
  guard=M.get('meta',{}).get('arch_ceiling_source_guard',{})
  add('DP-E-CEILING-SOURCE-GUARD','منع إزاحة رموز المصدر إلى أقرب جدار وإلغاء أثر ترميز فتحة الدرج على Z','corrected','ELEC1/2 رموز الأجهزة / ARCH2 A1401 / إصلاح ترميز STP المحفوظ المجال','كانت مرحلة السقف تعيد نقل31 جهازًا مثبت XY إلى أقرب جدار، فأوقف النقل للعناصر المقيدة بالمصدر. فتحة تلامس المحيط تبقى قناع استبعاد من السقف بعد تمثيلها كتجويف؛ لم تقطع فتحة جديدة. ألغي ارتفاع10 أجهزة أرضية +2.71م الذي نتج من فقد القناع، مع إرجاع Z الافتراضي السابق فقط. لا اعتماد لمنسوب أو وجه تثبيت من هذه المعالجة.',None,None,None,[e['id']for e in protected_mount],{'source_XY_devices_resnapped':31,'encoding_induced_Z_rise_m':2.71},{'source_XY_retained':True,'guarded_void_devices':len(protected_mount),'bounded_Z_rollback_ids':guard.get('encoding_induced_z_rollback_ids',[]),'source_Z_verified':False})
  add('DP-VOID-DEVICE-MOUNT','تفاصيل تثبيت الأجهزة داخل نطاق الفتحات غير مثبتة','source_gap','رموز ELEC/MECH / نطاقات السقف A1401','المواضع تتبع رموز مخططها. لا يعني وقوع الرمز داخل نطاق الفتحة وجود سقف أو جدار أو منفذ اتصال فعلي عنده. يحتاج وجه التثبيت والمنسوب وتفصيل الحامل إلى مصدر فريد؛ لا تستخدم أقرب جدار لحسمها.',None,None,None,[e['id']for e in protected_mount])
 wsc=M.get('meta',{}).get('water_supply_source_corrections',{})
 if wsc:
  data=read('water_supply_source_corrections');markers=data.get('device_markers',[])
  added=wsc.get('added_ids',[])
  add('DP-WS-SOURCE-SEMANTICS','تصحيح رموز معدات وضربات قطع مستخرجة كمواسير ماء','corrected','MECH2 ص19–22 WS-101/102/103/104','حذف61 مسارًا زائفًا من دوائر المحركات والقارنات وأطر الفلترة وأوعية المعدات، واستعادة17 مسار ماء حقيقي من رؤوسه الخام مع حفظ Z والقطر الحاليين كافتراضات. أضيفت4 أجزاء مرسومة منفصلة؛ لا جسر عبر رمز صمام أو قطع. فحص كامل primitive والوسم يحرس هوية المصدر، لا الطبقة وحدها أو أقرب خط. لا حذف لأنابيب الحريق: قادة وسوم معدات الماء على طبقة M_FF_PIPE لا يقابلها أي عنصر P.ff فعلي بالمجسم.',None,None,None,[r['id'] for r in data.get('restore_records',[])]+[x for x in added if x.startswith('P.cold')],{'retired_ids':wsc.get('retired_ids',[]),'retired_false_pipe_glyphs':61},{'restored_existing_paths':17,'added_disconnected_raw_parts':4,'Z_diameter_preserved_as_assumptions':True,'forced_connectors_added':0})
  add('DP-WS-SOURCE-EQUIPMENT','استكمال علامات معدات الماء الناقصة من رموز المصدر','corrected','MECH2 ص19 WS-101 وص22 WS-104 وص23 WS-106','أضيف مؤشر واحد عند مركز اتحاد كامل رمز كل جهاز: مضختا رفع ومضختا فلترة ومضختا تعزيز ووعاءا فلتر متعدد الوسائط ووعاء ضغط110L وخزان كسر الضغط ومعقماUV. الوسم والقائد وعدد رموز الأجهزة يثبتان الحضور وXY فقط؛ قطر3سم وارتفاع2سم لكل مؤشر حجم عرض معلن، وليس مقاس الجهاز التنفيذي. أجهزة العمل والاحتياط لا تعين لكل رمز، ولا وصلات أو منافذ مختلقة.',None,None,None,[d['id'] for d in markers],{'missing_device_symbols':12},{'source_markers':12,'physical_device_bodies_added':0,'physical_mount_or_connection_verified':False})
  add('DP-WS-EQUIPMENT-BODIES','أبعاد ومناسيب ومنافذ معدات الماء تحتاج استكمال المصدر','source_gap','MECH2 ص19/22/23','علامات الأجهزة12 مثبتة في مواضع المصدر، لكن لا أبعاد جسم فريدة أو منسوب تركيب أو مادة أو تفصيل منافذ يربطها كاملة بالمجسم. لا تحول الدائرة الرسومية إلى قطر جهاز. إبقاء فجوات الصمامات كما رُسمت يفصل بعض مانيفولدات السطح؛ وصول نهايات الاستهلاك لا يثبت سلسلة كاملة من المصدر.',None,None,None,[d['id'] for d in markers])
 wst=M.get('meta',{}).get('water_supply_mixed_corrections',{})
 if wst:
  data=read('water_supply_mixed_corrections')
  add('DP-WS-MIXED-SOURCE','تصحيح المسارات المختلطة بالماء من رؤوس المصدر','corrected','MECH2 ص19–22 WS-101/102/103/104','تقاعد39 مسارًا زائفًا: ضربات قطع S وأطر ورموز معدات. استعيد50 مسارًا حقيقيًا وأضيف49 جزءًا منفصلًا من رؤوس الخام دون جسر فوق صمام أو ضربات قطع. تحقق342 مسارًا كاملًا كخط مفتوح ضمن0.2سم. استمرار129 مسار ماء ساخن اشتقاق موثق من مفتاح الخط المتقطع وسياق T والانعطاف والتقاطع، وليس قطعة أنبوب حرفية عند كل شرطة ولا إثبات اتصال هيدروليكي عند أي تقاطع. Z والقطر والمادة والمنافذ غير مثبتة.',None,None,None,[r['id']for r in data['restore_records']]+wst.get('added_ids',[]),{'retired_false_glyph_ids':wst.get('retired_ids',[])},{'restored_existing':50,'new_raw_parts':49,'whole_open_XY_checked':342,'HW_dash_route_derived':129,'HW_dash_pending':0,'forced_source_gap_bridges':0})
 wmt=M.get('meta',{}).get('water_meter_source_remaining',{})
 if wmt:
  add('DP-WATER-METER-SEMANTICS','فصل عدادات دائرة M عن وسم W/M للغسالة','corrected','MECH2 ص20 WS-102 وص21 WS-103 / مفتاح WATER METER / ARCH2 رمز الغسالة','كان الاستخراج يصنف W/M داخل غرف WASH كعداد ماء، فحذفت5 أجسام صمام زائفة بهويتها وحراس هندستها. الغسالات ممثلة معماريًا بالفعل ولم تضف أجهزة من النص. أضيف30 مؤشر عداد في مراكز دوائر M المرسومة: ستة في كل طابق1–5. هذه مؤشرات حضور XY فقط؛ الأبعاد وZ والمادة والمنافذ والاتصال لا تثبتها دائرة الرسم.',None,None,None,wmt.get('added_ids',[]),{'false_WM_text_proxy_ids':wmt.get('retired_ids',[])},{'circle_M_source_markers':30,'physical_meter_bodies_verified':0,'automatic_connections_added':0})
  add('DP-WATER-METER-BODY-GAP','أجسام العدادات ومناسيبها ومنافذها تحتاج مصدرًا','source_gap','MECH2 WS-102/103 دائرة M','كل مؤشر مربوط بدائرة M وحرف M والمفتاح والتسجيل الخاص بورقته. قطر3سم وارتفاع2سم وFFL موضع عرض معلن؛ لا يؤخذ قطر الرمز كقطر عداد ولا يشتق منفذ من قرب خط الماء.',None,None,None,wmt.get('added_ids',[]))
 vsc=M.get('meta',{}).get('water_valve_source',{})
 if vsc:
  data=read('water_valve_source');records=data.get('records',{});new=data.get('additions',{})
  all_rows={**records,**new};live_ids={e['id'] for e in els};ids=[eid for eid in all_rows if eid in live_ids]
  generic=[eid for eid,r in all_rows.items() if r['source']['source_code']=='UNKNOWN_VALVE']
  provision=[eid for eid,r in all_rows.items() if r['source']['source_provision_only']]
  before={eid:r['before_g'][1:3] for eid,r in records.items()}
  after={eid:{'xy_cm':r['after_g'][1:3],'source_page':r['source']['source_page'],'raw_indices':r['source']['source_drawing_indices']} for eid,r in all_rows.items()}
  add('DP-WATER-VALVE-SOURCE','تصحيح مواضع رموز صمامات الماء وإضافة الرموز الناقصة','corrected','MECH2 ص19–22 WS-101/102/103/104 / حروف الوسوم بكل الطبقات ورموز CW الخام','كان115 جسم عرض عند مركز النص، لا الرمز؛ صححت مراسيها الرسومية مع إبقاء الهوية والمنسوب الحالي. جرد المصدر يثبت145 علامة نوعية:134IV و2GV و9NRV. أضيف30 رمزًا نوعيًا و22 رمز عائلة صمام بلا نوع تفصيلي فريد، ليصبح النطاق167 مرساة رسم. وسمان إضافيان كانا ضمن نص مركب بطبقة فارغة. لا تعتمد حدود الرمز كغلاف أو قطر صمام تنفيذي؛ لم تنشأ وصلة أو دعامة لتغيير reach.',None,None,None,ids,{'old_text_proxy_centres_xy_cm':before},{'source_graphic_anchors':after,'source_physical_dimensions_Z_ports_material_mount_verified':False})
  add('DP-WATER-VALVE-BODY-GAP','أجسام الصمامات ومناسيبها ومنافذها غير مثبتة','source_gap','MECH2 WS-101…104 / رموز IV/GV/NRV وعائلة الصمام','ثبت وجود ومركز وبصمة/زاوية رمز المسقط فقط. صناديق العرض بديل رسومي معلن؛ Z مستعارة إجرائيًا من المستوى وليست منسوب تركيب. تماس خط CW مع الرمز لا يثبت منفذًا أو تدفقًا أو حالة فتح الصمام أو قبوله في الموقع.',None,None,None,ids)
  add('DP-WATER-VALVE-SUBTYPE','نوع22 رمز صمام عام يحتاج حسمًا','source_gap','MECH2 ص20–22 / M_WS_CW','19 رمزًا خامًا فريدًا تتكرر كـ22 علامة عبر الأدوار، مستقلة عن رموز المعدات وممثلة في مراسيها. لا يوجد وسم نوعي فريد يربطها بـIV أوGV أوNRV؛ حفظت كعائلة صمام عامة دون تعيين نوع بالتخمين.',None,None,None,generic)
  add('DP-WATER-VALVE-PROVISION','علامتاGV موسومتان للتجهيز المستقبلي','source_gap','MECH2 ص19 WS-101 / FOR PROVISION','وصف FOR PROVISION يثبت قصد التجهيز في المخطط، ولا يثبت تركيبًا أو عدم تركيب فعلي أو تشغيلًا بالموقع. لا تُحسب العلامتان كصمامي تشغيل معتمدين.',None,None,None,provision)
 gc=M.get('meta',{}).get('garbage_chute_remaining',{})
 if gc:
  ids=[e['id'] for e in els if e.get('a',{}).get('sys')=='garbage_chute']
  add('DP-GARBAGE-COMPONENTS','استكمال مكونات مجرى النفايات المثبتة بالمخطط','corrected','ARCH1 ص6–9 A103–A106 / ARCH2 ص18 A1100','5 قطاعات مجرى و5 أبواب استقبال وقطاع تهوية ومؤشر واحد للمروحة في مراسي كل ورقة الأصلية. القطر600/300مم وسماكةSS3041.5مم نصوص منفصلة عن حجم الدائرة الرمزية. Z والتثبيت والفتحات غير معتمدة؛ مؤشر المروحة ليس جسم جهاز ولا يكرر الجهاز عند R وT.',None,[1254,1193],None,ids,{'missing_components':12},{'parts':12,'physical_fan_bodies':0,'structural_openings_added':0,'Z_verified':False})
  titles={'GC-SHAFT-DEPTH':'اختلاف عمق شافت النفايات بين المسقط والتفصيل','GC-PLAN-DETAIL-ROOM':'اختلاف توزيع غرفة النفايات المرتبط بعمق الشافت','GC-FUSIBLE-TEMP':'اختلاف حرفي في درجة وصلة باب التفريغ','GC-ACOUSTIC-COAT':'اختلاف وصف سماكة طلاء الصوت','GC-VENT-Z':'نهاية تصريف النفايات ومنسوب جسم المروحة يحتاجان حسمًا','GC-GLYPH-DIAMETER':'مقياس رمز النفايات لا يثبت قطر الجسم'}
  for q in gc.get('conflicts',[]):
   status='source_conflict' if q.get('status') in ('confirmed_source_conflict','confirmed_literal_variant') else 'source_gap'
   note=q['description_ar']
   if q.get('coordination_issue_id'):
    note+=' هذا أثر من مسألة توزيع واحدة مشتركة مع البند الآخر، وليس خطأ مستقلًا؛ التوزيع60+10+150 مقابل70+10+140 ضمن220سم.'
   if q.get('status')=='confirmed_literal_variant':note+=' اختلاف مواصفة نصية؛ لا تصادم هندسي أو اختلاف منسوب مثبت، ونطاق المنتج/التطبيق يحتاج حسمًا.'
   add(q['id'],titles[q['id']],status,' / '.join(q['source_refs']),note,None,[1254,1193],None,ids,{'source_classification':q.get('status'),'coordination_issue_id':q.get('coordination_issue_id')},{'conflict_kind':q.get('conflict_kind'),'geometry_clash':False if q.get('status')!='confirmed_source_conflict' else None})
  for q in gc.get('unbuilt_components',[]):
   add('DP-GARBAGE-GAP-'+str(gc.get('unbuilt_components',[]).index(q)+1),q['component_ar'],'source_gap','ARCH1 ص5 A102 / ARCH2 ص18 A1100',q['reason_ar'],None,[1254,1193],None,ids)
 co=M.get('meta',{}).get('cleanout_source_restore',{})
 if co:
  new_co=[e for e in els if re.search(r'-DCO\d{4}$',e['id'])]
  add('DP-DCO','استكمال رموز التسليك المرسومة واستعادة مواضعها','corrected','MECH2 ص2–7 DR','123 رمزًا قائمًا رُبط بالعارضة الفعلية، وأضيف65 رمزًا لم يستخرجها النص الأحادي القديم. التحقق لمركز XY الرمز فقط؛ جسم الجهاز وZ والمادة غير مثبتة. لا يضاف موصل لإجبار نجاح الاختبار.',None,None,None,[e['id'] for e in new_co],{'legacy':133},{'new':len(new_co),'total':198,'source_qualified':188})
  add('DP-DCO-PENDING','رموز تسليك تحتاج حسم مطابقة المصدر','source_gap','MECH2 ص2–7 DR','10 رموز قديمة وموضعان جديدان لم يثبت ربط فريد لهما؛ لم ينقل القديم ولم ينشأ الجديد.',None,None,None,[q['id'] for q in co.get('pending',[]) if q['id'] in {e['id'] for e in els}],{'pending':co.get('pending',[])})
 ess=M.get('meta',{}).get('electrical_symbol_semantics',{})
 if ess:
  data=read('electrical_symbol_semantics'); records=data.get('records',[])
  add('DP-E-SEMANTICS','تصحيح دلالات رموز الكهرباء من الأشكال الخام','corrected','ELEC1 مساقط الرموز / ELEC2 مساقط القوى','الـ609 المعلقة:556 رمزًا صحيحًا،35 تصحيح تصنيف/موضع،18 شظية غير جهاز؛ مع4 شظايا إضافية صار الحذف22. لوحاتDB34 تعاد كمراكز رموز مثبتة، وأضيف حسّاسان حركيان في الأول. غلاف الأجهزة وZ والألوان الفيزيائية غير مثبتة؛ لونCAD لون رمز مسقط فقط.',None,None,None,[],{'reviewed':609},{'removed':22,'reclassified':35,'added_sensor':2,'board_reuse':34})
 dsm=M.get('meta',{}).get('drain_semantics',{})
 if dsm:
  pit=[e['id'] for e in els if e['t']=='sump_pit']
  add('DP-SUMP-FFL','اختلاف منسوب غرفة حفرة التجميع','source_conflict','MECH2 ص2 DR-100 / ARCH1 ص4 A101','المخطط الميكانيكي−3.30م، تشطيب العمارة−3.50م؛ فرق20سم. قاع الجسم مشتق من العمارة مع بقاء اختلاف المصدر.','B',[1418.127,1544.441],-3.50,pit,{'DR-100':-3.30},{'A101':-3.50})
  add('DP-SUMP-SIZE','مقاس حفرة التجميع النصي يختلف عن إطار المسقط','source_conflict','MECH2 ص2 DR-100','النص1.5×1.5م، الإطار الخام119.73×120.15سم؛ حفظت حدود الرسم دون تكبير أو تعديل بلاطة S.','B',[1418.127,1544.441],-3.50,pit,{'text_cm':[150,150]},{'drawn_cm':[119.73,120.15]})
  add('DP-SUMP-OPENING','فتحة حفرة التجميع الإنشائية غير مثبتة','source_gap','MECH2 ص2 DR-100 / STR البدروم','جسم الحفرة من المصدر الميكانيكي؛ لم يثبت تفصيل الفتحة الإنشائية. لا قص أو تحريك S لإخفاء التداخل.','B',[1418.127,1544.441],-3.50,pit)
  add('DP-DRAIN-SEMANTICS','حدود وتهشير الصرف كانت مستخرجة كمواسير','corrected','MECH2 ص2/4 DR-100/102','حذف29 مسارًا زائفًا محدد الهوية؛ إضافة حفرة ومضختين وSDT وفاصل زيت وقناة، وفصل مساري التصريف المضغوط. سجل المصدر الكامل يوضح كل رسم ومعرّف.','B',[1418.127,1544.441],-3.50,[e['id'] for e in els if '-DSM' in e['id']],{'false_pipe_ids':dsm['removed_false_pipe_ids']},{'bodies':dsm['added_bodies'],'pressure_ids':dsm['pressure_reclassified_ids']})
  u=dsm.get('unresolved_ft',{})
  add('DP-FT-UNPROVED','أربعة FT عند نص داخل shaft دون رمز مثبت','source_gap','MECH2 ص6 DR-103',u.get('description_ar',''),'2',u.get('xy_cm'),None,u.get('ids'))
 for suffix,source,title in [('DTR','MECH2 ص8 DR-105','استكمال نهايات الصرف في السقف العلوي'),('DRG','MECH2 ص4 DR-102','استكمال مسارات الأرضي إلى الموقع')]:
  vs=[e for e in els if re.search('-'+suffix+r'\d{4}$',e['id'])]
  if vs:
   first=vs[0];g=first['g'];xy=g[1][0][:2] if g[0] in ('t','d','p') else g[1:3]
   add('DP-DRAIN-'+suffix,title,'corrected',source,'المكونات موجودة في الرسم الأصلي وكانت ساقطة من الاستخراج. استعيدت في تسجيل ورقتها؛ الجهة والارتفاع والاتصال غير المرسوم تبقى معلنة. ادعاء أن G→MH غير مرسوم كان خطأ مراجعة سابقًا؛ سبب السقوط حد القص y=1900سم.',first['l'],xy,zr(g)[0],[e['id']for e in vs],{'before':'مفقودة من النموذج'},{'parts':len(vs)})
 add('DP-TE-TITLE','عنوان لوحة الهاتف منسوخ من القدرة','source_conflict','ELEC2 ص27 EP-010','عنوان المصدر SITE PLAN POWER LAYOUT، بينما محتواه جراب هاتف وألياف ورفا MDF؛ فهرس العنوان الأصلي محفوظ مع تعريف المحتوى الفعلي.')
 D=read('chw_review')
 for p in D.get('geometry_comparison',[]):
  for layer,v in p.get('layers',{}).items():
   d=v.get('set1_to_set2',{});xy=d.get('max_at_cm');delta=d.get('max_cm',0)
   if delta>25:add('DP-CHW-'+p['level']+'-'+layer,'اختلاف مسار CHW بين الإصدارين','source_conflict',' / '.join(p['sheets']),f'أكبر فرق{delta}سم عند النقطة المحددة؛ إبقاء MECH1 تقديم30-03-2022، MECH2 تقديم09-02-2022. كلاهماrev00؛ الاعتماد النهائي يحتاج حسمًا.',p['level'],xy,None)
 add('DP-CHW-SCH','سعات ومقاسات المبردات تختلف بين الجداول والمسقط','source_conflict','MECH1 ص15–16 / MECH2 ص36–37',json.dumps(D.get('schedule_disagreements',[]),ensure_ascii=False),'R',[1165,1626],23.35,[e['id'] for e in els if e['t']=='chiller'])
 for id,title,src,note in [('DP-STR-FUT','أحمال طوابق مستقبلية','STR ص1 S-N1 / ص10 S-6','الملاحظات تنفي أي امتداد رأسي بينما جدول ردود الأفعال يذكر3FUTURE FLOORS؛ لم يتغير S.*.'),('DP-STR-COVER','اختلاف غطاء التسليح','STR ص1 / ص26/28','غطاء35مم للأعمدة و30للجدران/الجسور في الملاحظات،40مم في الجداول؛ عينة التسليح تستخدم40وفق الجدول دون ادعاء اعتماد هندسي.'),('DP-CAT-LEVEL','منسوب نهاية سلّم السطح','ARCH1 ص9 A106 / ARCH2 ص37 A1800','A1800 يسمي27.25FFL ويحدد390سم؛ A106 يحدد26.85FFL و27.25T.OP. السلم حتى27.25 من التفصيل؛ المنصة لم تتحرك.')]:add(id,title,'source_conflict',src,note)
 pg=M.get('meta',{}).get('pergola_remaining',{})
 if pg:
  add('DP-PERGOLA','استكمال برجولات معدات السطح من مواضعها المثبتة','corrected','ARCH1 ص8–9 A105/A106 / ARCH2 ص36 A1700','المراجعة الأولية لم تحسم المواضع؛ ثبتت حدود ثلاث وحدات في طبقة A-ABOVE ومحاور A106: 12×3 م فوق المبردات،7×3 م فوق خزاني GRP،4×2.5 م فوق FAHU. أضيفت الإطارات و22 عمودًا و88 شريحة مرسومة؛ الارتفاع 2.95 م من A1700، والمراسي غير محددة.','R',[1434.92,1524.635],23.35,[e['id'] for e in els if e['c']=='A.pergola'],{'before':'مفقودة؛ لم تحسم مواضعها أولًا'},{'units':3,'elements':pg.get('count')})
  for typ,title,delta,source in [('chiller','اختلاف موضعي المبردين بين العمارة والميكانيكا',[[-21.067,-100.187],[-12.340,-100.187]],'ARCH1 ص9 A106 / MECH2 ص36 CHW-104، محاور مستقلة / MECH1 ص15 تشخيص طبقة'),('fahu','اختلاف موضع FAHU بين العمارة والميكانيكا',[[105.714,77.346]],'ARCH1 ص9 A106 / MECH2 ص36')]:
   es=[e for e in els if e['t']==typ and e['l']=='R']
   if es:
    f=es[0];p=poly_of(f['g']);xy=[round(p.centroid.x,2),round(p.centroid.y,2)]
    add('DP-PG-EQUIP-'+typ,title,'source_conflict',source,'قياس رموز المساقط المستقل يثبت فروق ARCH−MECH2 بالسم: '+json.dumps(delta)+'؛ ليست إزاحة تسجيل عامة. مواقع المبردين في MECH1/MECH2 تتفق ضمن1.15 سم؛ تسجيل MECH1 هنا تشخيص طبقة،والرقم المعتمد من محاور MECH2. حفظت المعدات الميكانيكية والبرجولة المعمارية في مواضع كل مصدر؛ تحتاج الأعمدة/الأجهزة تنسيقًا قبل الاعتماد.','R',xy,zr(f['g'])[0],[e['id'] for e in es],{'source_delta_ARCH_minus_MECH_cm':delta},{'model_action':'لا نقل أو تصغير لإخفاء التداخل'})
 existing_sources=('AR-A2204-COPY','AR-LADDER-LEVEL','ST-FUTURE-LOAD','ST-COVER')
 for d in read('arch_struct_review').get('conflicts',[]):
  if d['id'] not in existing_sources:
   add(d['id'],d.get('location','تعارض تفصيل'),'source_conflict',' / '.join(d['source']),d.get('before','')+'؛ '+d.get('after',''),None,None,None,[],d.get('before'),d.get('after'))
 for v in M.get('meta',{}).get('electrical_model_corrections',[]):
  after=v.get('after',{});g=after.get('g',[]);xy=g[1:3] if g and g[0] in ('b','cyl') else None
  add('DP-E-'+v['id'],'تصحيح موضع/نوع كهربائي','corrected',v.get('sheet','ELEC2'),v.get('reason',''),after.get('l'),xy,None,[v['id']],v.get('before'),after)
 ss=M.get('meta',{}).get('source_support',{}).get('changes',[])
 valid=[v for v in ss if v.get('new',{}).get('status')=='existing_body_contact']
 if valid:
  add('DP-E-SUPPORT','تصحيح تصنيف الإسناد من تماس جسم موجود','corrected','ELEC2 مساقط الصواعق والهاتف / مضيفات العمارة والإنشاء بالمجسم',str(len(valid))+' عنصرًا: النحاس النازل يلامس جدارًا/عمودًا خلال ارتفاع موجب؛ قاعدة رأس الصواعق تلامس قمة الدروة؛ الصندوق الأرضي بكامل حجمه داخل طبقة الأرضية. لم يتغير موضع أو منسوب، ولم يزد التسامح. تفاصيل تثبيت المشابك والقواعد تظل بحاجة اعتماد.',None,None,None,[v['id'] for v in valid],{'before':'تصنيف عائم أو مضيف أخفض'},{'after':'تماس حجم فعلي؛ الدليل والمضيف في meta.source_support'})
 gaps=collections.defaultdict(list)
 for e in els:
  a=e.get('a') or {}
  if (a.get('sys') or a.get('source_locked_xy')) and a.get('unsupported'):
   gaps[(a.get('sys') or ('source_'+e['c']),e['l'])].append(e)
 for (sys,lv),vs in sorted(gaps.items()):
  v=vs[0];g=v['g'];xy=g[1:3] if g[0] in ('b','cyl') else ((g[1][0][:2]) if g[0] in ('t','d','p') else None)
  names={'ltg':'الصواعق','earth':'التأريض','telephone':'الهاتف','hvac_legacy':'تكييف السطح','hvac_controls':'تحكم التكييف','air':'التكييف الهوائي','drain_legacy':'الصرف القائم','fire_legacy':'الإطفاء القائم','fa':'الهواء النقي'}
  add('DP-SUPPORT-'+sys+'-'+lv,'مواضع شبكة تحتاج حسم الإسناد — '+names.get(sys,sys),'source_gap',' / '.join(M['sp'][s] for s in v.get('s',[]) if isinstance(s,int) and s<len(M['sp'])),str(len(vs))+' عنصرًا محفوظًا في موضع المسقط. لم يثبت المضيف في المجسم؛ لا نقل إلى أقرب جدار ولا وصلة مخترعة. تفاصيل الإحداثيات ومعرّفات العناصر في سجل التسليم.',lv,xy,zr(g)[0],[e['id'] for e in vs])
 import pergola_conflicts as PC
 pg_review=PC.audit(M,els)
 M['pergolaReview']=pg_review
 for v in pg_review['pairs']:
  typ=M['types'].get(v['service_type'],{}).get('n',v['service_type'])
  add(v['id'],'تداخل مرشح للبرجولة مع '+typ,'model_candidate',' / '.join(v['source_refs']),v['reason_ar'],v['level'],[round(x,3) for x in v['xy_cm']],v['z_overlap_m'][0],[v['pergola_id'],v['service_id']],{'z_overlap_m':v['z_overlap_m'],'assumptions':v['height_assumptions']},{'model_overlap_volume_m3':v['volume_m3'],'action':'الموضع محفوظ؛ يلزم حسم التنسيق قبل اعتماد تعديل'})
 ssr=M.get('meta',{}).get('structural_source_restore',{})
 if ssr:
  piles=[e['id'] for e in els if e['c']=='S.pile']
  add('DP-PILE-LENGTH','تصحيح تقصير الخوازيق الموروث من30 سم إلى13 م','corrected','STR ص11 S-7 PILE DETAILS / STR ص12 S-8 SECTION1-B','89 خازوقًا بقطر60سم وطول13م كما في نص المخطط. XY محفوظ؛ قمة−5.40م مشتقة من أسفل PC1 ولا تثبت القطع أو الغرس. قاع الجسم−18.40م مشتق. أصلح التسليح في العينة إلى10T16/T10،وبقية تفاصيل الترتيب والخطوة غير مرقمة.', 'B', None,-5.40,piles,{'display_length_m':.30},{'source_length_m':13,'diameter_cm':60,'head_anchor':'derived; embedment unverified'})
 heater=M.get('meta',{}).get('water_heater_capacity_source')
 if heater:
  data=read('water_heater_capacity_source');active={e['id']:e for e in els};ids=[]
  with open(os.path.join(HERE,'data','water_heater_capacity_source.json'),'rb')as f:
   assert hashlib.sha256(f.read()).hexdigest()==heater['source_data_sha256'],'Heater property source changed'
  for eid,r in data['records'].items():
   e=active[eid]
   assert e['c']==r['category']and e['l']==r['level']and e['g']==r['before_g'],'Heater body moved while recording capacity correction'
   assert e['t']==r['after_type']and e.get('mark')==r['after_mark']and e.get('a',{}).get('cap_l')==r['source_capacity_l'],'Heater source capacity is not applied'
   if r['source_capacity_l']==50:ids.append(eid)
  assert len(ids)==21,'Heater50 source quantity is not21'
  add('DP-HEATER-CAPACITY','تصحيح سعات21 سخانًا من80 إلى50 لتر','corrected','MECH2 ص19–22 رموز WS / MECH2 ص20 مفتاح الرموز / BOQ ص12','الرموز الأصلية تربط61 سخانًا بسعة80 لتر و21 بسعة50 لتر،وتطابق الكميات جدول المواد. صُححت السعة والنوع والوسم فقط؛ جسم العرض وXY وZ والمادة محفوظة وتبقى بحاجة دليلها الخاص. القدرة في مفتاح المصدر:50 لتر/1.2kW و80 لتر/1.5kW. لم تضف وصلة أو يعاد بناء جسم صحيح لمجرد تغيير السعة.',None,None,None,ids,{'incorrect_type':'heater80','incorrect_capacity_l':80},{'corrected_type':'heater50','source_capacity_l':50,'source_power_kw':1.2,'geometry_changed':False,'physical_body_dimensions_accepted':False})
 core=read('core_stairs_source_review')
 if core:
  path=os.path.join(HERE,'data','core_stairs_source_review.json')
  with open(path,'rb')as source_file:assert hashlib.sha256(source_file.read()).hexdigest()=='9e52a6fba2fde5f3e7dc2cfa371dd478f08197710131e74207c0ea05903144f8','Core stair review changed without a new source stage'
  for page in core['source_pages'].values():
   with open(page['source_pdf'],'rb')as source_file:assert hashlib.sha256(source_file.read()).hexdigest()==page['source_pdf_sha256'],'Core stair original PDF changed'
  active={e['id']:e for e in els};groups={q['group']:q for q in core['remaining_groups']}
  surface_groups=set();surface_after={}
  if M.get('meta',{}).get('core_stairs_source_surfaces'):
   import core_stairs_source_surfaces as CSF
   surface_data=CSF.data();surface_after=CSF.compile_after(surface_data)
   surface_groups={q['group']for q in surface_data['groups']}
  for q in groups.values():
   members=[e for e in surface_after.values()if e['grp']==q['group']]if q['group']in surface_groups else q['members']
   expected={e['id']for e in members};actual={e['id']for e in els if e.get('grp')==q['group']}
   assert actual==expected,'Core stair review inventory no longer bound: '+q['group']
   for e in members:
    v=active[e['id']];assert all(v.get(k)==e.get(k)for k in ['c','t','l','m','grp','g']),'Core stair review no longer bound to geometry: '+e['id']
  names={'CORE-STAIRS-G-RISE':'خطأ مؤكد في تقسيم قوائم سلالم الأرضي','CORE-STAIRS-N-RISE':'خطأ مؤكد في تقسيم قوائم السلالم المتكررة','CORE-STAIRS-B-DATUM':'خطأ مؤكد في اعتماد منسوب البسطة المحلية للبدروم','CORE-STAIRS-ROOF-DATUM':'خطأ مؤكد في منسوب نهاية الدرج عند السطح','CORE-STAIRS-G-THREE-FLIGHT-LAYOUT':'خطأ مؤكد في عدد أجنحة سلالم الأرضي وعروضها','CORE-STAIRS-MID-10.10':'اختلاف منسوب البسطة المكتوب عن ترقيم القوائم داخل المصدر'}
  notes={'CORE-STAIRS-G-RISE':'المصدر يحدد33 قائمة بنحو16.36سم لارتفاع5.40م؛ التقسيم الحالي20×27سم لا يطابقه. إعادة بناء الأجنحة والبسطات من القطاع والمسقط جارية.',
   'CORE-STAIRS-N-RISE':'المصدر يحدد22 قائمة بنحو15.90سم للدور3.50م؛ المجسم يقسمه20×17.50سم، وآخر دور20×18سم. عدد مكعبات النائمات لا يساوي عدد القوائم؛ لا تضاف قطعتان بالحساب وحده.',
   'CORE-STAIRS-B-DATUM':'بسطة درج01 في A101/A600 عند−3.50م، بينما المولد اعتمد المرجع العام−3.70م. هذا تصحيح محلي مطلوب، ولا يرفع أرضيات البدروم كلها.',
   'CORE-STAIRS-ROOF-DATUM':'بسطة نهاية الدرج عند+23.25م في المصدر، بينما آخر درجة بالمجسم عند+23.35م. منسوب تشطيب السطح الخارجي+23.35 مستقل عن بسطة الدرج المحلية.',
   'CORE-STAIRS-G-THREE-FLIGHT-LAYOUT':'قطاعا A601/A602 يثبتان ثلاثة أجنحة وبسطتي+2.15/+3.95 بين+.35 و+5.75م؛ المجسم يمثل جناحين وبسطة+3.05. أول11 قائمة في درج02 بعرض200سم، تليها120سم؛ شكل كل سلم يتطلب بناء مستقلًا.',
   'CORE-STAIRS-MID-10.10':'المنسوب+10.10 مطبوع في المسقطين وتؤكده حروف CAD في القطاع. فرق85سم فوق+9.25 لا يطابق11 قائمة×15.90سم. قيمة11.00 الناتجة من الحساب لم تعتمد أو تستبدل النص؛ حل المنسوب مرشح يحتاج حسم المصدر.'}
  for issue in core['issues']:
   corrected=[g for g in issue['groups']if g in surface_groups]
   pending=[g for g in issue['groups']if g not in surface_groups]
   ids=[e['id']for group in pending for e in groups[group]['members']]
   status='confirmed_model_error'if issue['classification']=='confirmed_model_error'else'source_conflict'
   if pending:
    note=notes[issue['id']]
    if corrected:note+=' صُححت أسطح المجموعات '+', '.join(corrected)+'؛ الخطأ الحالي هنا مقصور على '+', '.join(pending)+'.'
    add('DP-'+issue['id'],names[issue['id']],status,'ARCH1 ص4–8 / ARCH2 ص1–4 A600–A603',note,None,None,None,ids,{'current_model':issue.get('model'),'review_reference_elements':core['model_count']},{'literal_source':issue['literal'],'pending_groups':pending,'correction_pending':True,'physical_site_clash_verified':False,'complete_stair_body_accepted':False})
   if corrected:
    corrected_ids=[eid for eid,e in surface_after.items()if e['grp']in corrected]
    cid='DP-'+issue['id']+('-SURFACES-CORRECTED'if pending else'')
    add(cid,'تصحيح أسطح الدرج — '+names[issue['id']],'corrected','ARCH1 ص6–8 / ARCH2 ص1–4 A600–A603','حُذفت الأجسام ذات التقسيم أو الشكل الخاطئ،وأعيدت أسطح النائمات والقوائم والبسطات من نوسينغ المسقط ومناسيب القطاع. المجموعات: '+', '.join(corrected)+'. القوالب المتطابقة منسوخة إلى مواضعها؛ المثلثات تفاصيل سطح وليست عناصر مستقلة. هذا يصحح هندسة أسطح الرسم فقط؛ بطن وسماكة الخرسانة والتسليح والارتكاز والمادة غير مثبتة.',None,None,None,corrected_ids,{'model_error':issue.get('model')},{'literal_source':issue['literal'],'corrected_surface_groups':corrected,'physical_site_clash_verified':False,'complete_stair_body_accepted':False})
  if surface_groups:
   add('DP-CORE-STAIRS-SURFACE-BODY-SCOPE','تفاصيل الأجسام الخرسانية للسلالم المصححة تحتاج استكمال المصدر','source_gap','A600–A603 / التفاصيل الإنشائية','أُصلحت أسطح تسع مجموعات من المصدر:190 نائمة و209 قوائم و10 بسطات داخل29 تجميعة. الأجسام أسطح مفتوحة بلا سماكة مخترعة؛ لا يعتمد بطن الخرسانة أو التسليح أو الارتكاز أو مادة الجسم. تُحفظ مجموعات البدروم والأرضي لدرج01 والدور الثاني للدرجين دون تغيير إلى حين حسم المصدر.',None,None,None,list(surface_after),None,{'source_surface_groups':9,'whole_structural_body_accepted':False})
 d16=M.get('meta',{}).get('d16_source_remaining',{})
 if d16:
  data=read('d16_source_remaining');ids=list(data['records']);host=data['existing_host_position_difference'];active={e['id']:e for e in els}
  assert all(eid in active for eid in ids),'Missing D16 source part while recording issues'
  h=active.get(host['model_id'])
  _host_corrected=bool(h and h.get('a',{}).get('source_d16_host_correction'))
  if _host_corrected:
   import d16_host_source_correction as _DHC
   _host_source_rows=_DHC.issue_records(M)
  else:
   assert h and h['g']==host['guard_g'] and (h['c'],h['t'],h['l'])==(host['c'],host['t'],host['l']),'D16 host review no longer bound to preserved geometry'
  add('DP-D16-SOURCE-PARTS','إضافة مجموعة D16 المفقودة في موضعها المرسوم','corrected','ARCH1 ص5 A102 / ARCH2 ص5 A604','أضيفت مجموعة واحدة ممثلة بأربع بصمات: درفتان في وضعيتهما المفتوحة ومقطعا الإطار الخارجيان من أوامر المسقط الأصلية. لم يعتمد مركز الوسم الذي يبعد نحو42سم، ولم تحول أقواس الفتح أو مقاطع التقاء الدرفتين إلى عتاد أو قوائم ثابتة.','G',[4072.913654,1562.334249],None,ids,{'missing_source_assemblies':1},{'source_assemblies':1,'plan_parts':4,'physical_body_and_Z_accepted':False})
  add('DP-D16-OPENING-WIDTH','اختلاف عرض فتحة D16 بين المخطط وجدول الكميات','source_conflict','ARCH2 ص5 A604 / BOQ ص8 البند8.3.12','A604 يطبع125سم للفتحة الإنشائية، بينما BOQ يطبع125X1100mm حرفيًا. الفرق مؤكد في النص؛ احتمال سقوط صفر في BOQ لم يُحسم أو يصحح تلقائيًا. لا يعتمد مقاس الفتحة كعرض تصنيع كل درفة.','G',[4072.913654,1562.334249],None,ids,{'A604_width_mm':1250},{'BOQ_printed_width_mm':125,'source_resolution_pending':True})
  add('DP-D16-FIRE-RATING','اختلاف مقاومة حريق D16 بين المخطط وجدول الكميات','source_conflict','ARCH2 ص5 A604 / BOQ ص8 البند8.3.12','A604 يحدد90min بينما BOQ يطبعrating:N/A. هذا اختلاف مواصفة نصية مؤكد، ولا يثبت قبول مجموعة الباب المركبة أو تعارضًا هندسيًا أو اختلاف منسوب.','G',[4072.913654,1562.334249],None,ids,{'A604':'90 min'},{'BOQ':'N/A','fire_assembly_accepted':False})
  if _host_corrected:
   issues.extend(_host_source_rows)
  else:
   add('DP-D16-HOST-OPENING','خطأ مؤكد في موضع فتحة حاجز درج03 الحالية','confirmed_model_error','ARCH1 ص5 A102 drawing37188 والدرفتان47675–47682','طرفا الإطار يطابقان مرجع فتحة الدرج في الخام. حافة شريط الحاجز الحالي عندY1620سم، ومركز الإطار عندY1562.334سم؛ الفرق57.666سم. أُبقي الباب عند المصدر، وبقي تصحيح المضيف ضمن مراجعة هندسته كاملة. هذا خطأ في المجسم مقارنة بالمخطط، وليس إثبات خطأ تنفيذ في الموقع.','G',[4072.913654,1562.334249],None,[host['model_id']]+ids,{'model_wall_inner_edge_y_cm':1620},{'source_frame_center_y_cm':1562.334249,'difference_cm':host['source_frame_center_vs_nearest_north_wall_inner_edge_y_cm'],'host_correction_pending':True,'physical_site_clash_verified':False})
  add('DP-D16-PHYSICAL-SCOPE','تفاصيل جسم D16 وتثبيته تحتاج استكمال المصدر','source_gap','A102 / A604 / BOQ8.3.12','ثبتت بصمات المسقط وفئة الفولاذ المجلفن ونص الفتحة. نطاق العرض+.20..+1.30م مشروط بارتفاع الفتحة فوق البسطة، ولا يعتمد ارتفاع كل جزء أو سماكة الصاج أو عمق الإطار أو التثبيت والعتاد واللون. اختلاف العرض ومقاومة الحريق مسجلان منفصلين.','G',[4072.913654,1562.334249],None,ids)
 scr=M.get('meta',{}).get('stair01_roof_source_correction',{})
 if scr:
  data=read('stair01_roof_source_correction');caps=data.get('records',{})
  add('DP-STAIR01-ROOF-FLIGHT','إزالة جناح درج01 الزائد فوق بسطة السطح','corrected','ARCH2 ص1–2 A600/A601 / ARCH1 ص8–9 A105/A106 / STR ص24','المسقط والقطاع يثبتان نهاية درج01 عند بسطة السطح +23.25م، وغطاء TOP ROOF فوقها، دون جناح صاعد من R إلى T. أزيلت 21 قطعة درج و65 قطعة درابزين مشتقة، وأُلغي قص الغطاء الناتج عنها مع إزالة جزء القص الزائد. حُفظت هويات بقية الدرج والعناصر الإنشائية؛ هذا لا يعتمد بقية السلالم أو مناسيبها أو تفاصيلها.','R',[385,900],23.25,list(data.get('retirement_records',{})),{'unsupported_stair_parts':21,'derived_rail_parts':65,'cut_fragments':1},{'retired_exact_ids':list(data.get('retirement_records',{})),'remaining_stair_body_acceptance':False})
  add('DP-STAIR01-ROOF-CAP','إصلاح قص غطاء درج01 الناتج عن الجناح الزائد','corrected','نهاية الدرج في A600/A601 وA105/A106 / عملية القص الإجرائية arch_stairs.py','أعيد المجال الإجرائي للبلاطتين T-0008 وT-0009 قبل قص HEAD الخاطئ، ثم أعيد طرح فتحات الشافت الست من STR24. الاستعادة تعكس عملية محددة مثبتة، ولا تعتمد المحيط الخارجي القديم أو Z أو المادة أو التسليح من المصدر.','T',None,None,list(caps),{'known_procedural_HEAD_cut':True},{'restored_before_shaft_subtraction':{eid:r['restored_before_TRO_g']for eid,r in caps.items()},'whole_cap_source_accepted':False})
 tro=M.get('meta',{}).get('top_roof_shaft_openings_source',{})
 if tro:
  data=read('top_roof_shaft_openings_source');rows=data.get('records',{})
  active={e['id']:e for e in els};ids=[eid for eid in rows if eid in active]
  add('DP-TOP-ROOF-SHAFT-OPENINGS','تصحيح ست فتحات شافت مهملة في بلاطة السطح العلوي','corrected','STR ص24 TOP ROOF SLAB LAYOUT / طبقة SHAFT / raw2148–2151 و2156–2157','كان مسار بناء البلاطات المستطيلة يهمل فتحات الشافت المحفوظة في الاستخراج. طُرحت ست بصمات مصدر مغلقة بعلامة X من نطاق الجسمين S.slab-T-0009 و0010؛ القص على حدود القطعتين ينتج سبعة أجزاء، ومنها تجويف على الحافة. حُفظت الهويات والمناسيب وبقية مجال البلاطة. تجميع أقنعة الفتحات صار يشمل كل قطع المستوى، فيراعي السقف المشتق هذه الفتحات. هذا تصحيح فتحة في المسقط، ولا يثبت كامل حدود البلاطة أو المنسوب المطلق أو تفاصيل تسليح الحواف.', 'T',None,None,ids,{'before_g':{eid:r['before_g'] for eid,r in rows.items()}},{'after_g':{eid:r['after_g'] for eid,r in rows.items()},'source_openings':len(data.get('source_openings',[])),'unrelated_structure_and_Z_changed':False})
  add('DP-TOP-ROOF-SLAB-SOURCE-GAP','حدود بلاطات السطح العلوي ومناسيبها وتفاصيل حواف الفتحات تحتاج استكمال المصدر','source_gap','STR ص24 / قطاعات وملاحظات البلاطات','قبول بصمة الفتحة لا يثبت المجال الخارجي القديم للبلاطة، أو غطاء وتسليح حواف الفتحة، أو SSL المطلق، أو تفاصيل مرور الخدمات والإغلاق والحماية. السماكة25سم تطابق الملاحظة العامة المشروطة ما لم يحدد خلافها؛ يلزم ربط الاستثناء المحلي بالقطاع.', 'T',None,None,ids)
  comparison=read('top_roof_opening_source_comparison')
  assert comparison.get('schema')=='c4.top-roof-opening-source-comparison.v1' and len(comparison.get('opening_bindings',[]))==6,'Missing original ARCH/STR opening comparison'
  for path,expected in comparison['source_files_sha256'].items():
   with open(path,'rb')as source_file:assert hashlib.sha256(source_file.read()).hexdigest()==expected,'Opening comparison original PDF changed: '+path
  conflicts=comparison.get('source_conflicts',[])
  assert len(conflicts)==1 and conflicts[0]['id']=='DP-TOP-ROOF-SHAFT-ARCH-STR','Unexpected opening comparison conflict scope'
  for q in conflicts:
   add(q['id'],'اختلاف حد فتحة الشافت بين المعماري والإنشائي','source_conflict',' / '.join(q['source_refs']),'حد الفتحة المغلق وعلامة X في المصدرين يثبتان هوية الفتحة نفسها. قياس الحدود الخام بعد تسجيل مستقل يعطي الإنشائي100.096×49.942سم،والمعماري100.279×60.083سم؛ فرق عمق10.140952سم لا تفسره إزاحة التسجيل. مركز الإنشائي X865.045/Y755.479سم. بقي قص البلاطة على حد STR24، ولم تنقل أي ورقة أو توسع الفتحة لإخفاء الاختلاف. المؤكد اختلاف الحدود الرسومية في المسقط؛ صافي الفتحة والارتكاز والتسليح ومرور الخدمات والمناسيب المطلقة تحتاج حسم التفصيل.',q['level'],q['xy_cm'],None,q['elements'],{'STR_bbox_cm':q['STR_bbox_cm'],'STR_size_cm':q['STR_size_cm']},{'ARCH_bbox_cm':q['ARCH_bbox_cm'],'ARCH_size_cm':q['ARCH_size_cm'],'ARCH_minus_STR_size_cm':q['ARCH_minus_STR_size_cm'],'model_opening_source_retained':q['model_opening_source_retained'],'physical_coordination_verified':False})
 for d in read('source_material_review').get('conflicts',[]):
  codes=d.get('codes',[]);ids=[e['id'] for e in els if any(f in codes for f in e.get('a',{}).get('fin',[]))]
  add(d['id'],'اختلاف مادة وسماكة F16/F17 بين A500 وBOQ','source_conflict',' / '.join(d['source_refs']),d['reason_ar'],None,None,None,ids,d['a'],d['b'])
 for d in M.get('meta',{}).get('drain_trace_review',{}).get('pending_cases',[]):
  eid=d['id']; pts=d.get('model_xy_cm') or []
  add('DP-DRAIN-TRACE-'+eid,d.get('title_ar','دلالة جزء من مسار الصرف تحتاج حسمًا'),'source_gap',d.get('source','MECH2 ص2–7'),d.get('reason_ar') or d.get('note_ar') or d.get('limit_ar','رموز وأجزاء مشتقة في المسقط؛ لا يعتمد قوس الرمز انحناء ماسورة دون تفصيل.'),d.get('level'),d.get('xy_cm') or (pts[0] if pts else None),None,[eid],{'source_primitives':d.get('raw_source_primitives',[]),'source_candidate_xy_cm':d.get('source_candidate_xy_cm',[])},{'model_xy_cm':pts,'status':d.get('status')})
 M['drawingIssues']=issues
 return issues
