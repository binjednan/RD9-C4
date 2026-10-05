# -*- coding: utf-8 -*-
"""Electrical device class catalogue.  Names / specs come from the legend tables of the supplied drawings
(ELEC1 EL-103 light legend, EP-103 power legend, ELEC2 FA / LC / TEL / LTG legends) and the mounting-height
diagram of EP-109.  Everything not in the documents is flagged by the 'asm' list (assumed)."""

# mounting heights given in EP-109 (mm AFFL)
MH={"socket":0.40,"tel":0.40,"tv":0.40,"switch":1.30,"fa_bg":1.30,"fa_bell":2.20,"isolator":1.30,"db_top":1.80,"fcu_unit":1.30,"plant_socket":1.30,"timesw":1.90,"cooker_flex":0.40}

# id -> dict(cat, ar, en, mat, shape, mode, z0(m: abs AFFL or relative to ceiling), h(m), wh(cm default w,d), spec[(k,v)], asm[], src)
# shape: disc | box | plate | pend | lin | mast
# mode : ceil (z0 = ceiling-offset) | wall (z0 = AFFL) | floor
C={}
def add(id,cat,ar,en,mat,shape,mode,z0,h,wd=None,spec=(),asm=(),src="",cap=(6,150)):
    C[id]=dict(id=id,cat=cat,ar=ar,en=en,mat=mat,shape=shape,mode=mode,z0=z0,h=h,wd=wd,spec=list(spec),asm=list(asm),src=src,cap=cap)

LIGHT_SRC="ELEC1 مفتاح الإنارة (ELEC. LIGHT LEGEND) في لوحات EL-101..EL-106"
asm_h="ارتفاع التركيب وأبعاد الجهاز الفعلية غير مذكورة؛ البصمة من رمز المخطط"
# ---- luminaires (legend TYPE-1..13)
add("L1","E.light","كشاف سقفي خطي 2×22 واط LED","Ceiling mounting fixture 2x22W LED","m_light","lin","ceil",-0.08,0.08,None,[("القدرة","2×22 واط LED"),("الفيض الضوئي","5670 لومن"),("درجة الحماية","IP65"),("الجهد/التردد","240 فولت / 50 هرتز"),("النوع في المفتاح","TYPE-1")],[asm_h],LIGHT_SRC)
add("L2","E.light","كشاف سقفي 22 واط LED","Ceiling mounting fixture 22W LED","m_light","lin","ceil",-0.08,0.08,None,[("القدرة","22 واط LED"),("الفيض الضوئي","2835 لومن"),("درجة الحماية","IP65"),("الجهد/التردد","240 فولت / 50 هرتز"),("النوع في المفتاح","TYPE-2")],[asm_h],LIGHT_SRC)
add("L3","E.light","كشاف سقفي/جداري 18 واط LED","Ceiling/wall mounting fixture 18W LED","m_light","lin","ceil",-0.08,0.08,None,[("القدرة","18 واط LED"),("الفيض الضوئي","1872 لومن"),("درجة الحماية","IP54"),("النوع في المفتاح","TYPE-3")],[asm_h],LIGHT_SRC)
add("L4","E.light","كشاف سقفي/جداري 18 واط مع مقبس حلاقة","Ceiling/wall fixture 18W LED with built-in shaver socket","m_light","lin","wall",2.00,0.12,None,[("القدرة","18 واط LED"),("الفيض الضوئي","1872 لومن"),("درجة الحماية","IP54"),("ملحق","مقبس حلاقة مدمج"),("النوع في المفتاح","TYPE-4")],[asm_h,"التركيب فوق المرآة بارتفاع 2.0 م: افتراض"],LIGHT_SRC)
add("L5","E.light","كشاف غاطس بعاكس مزدوج 43 واط LED","Recessed fixture with double-parabolic louvre 43W LED","m_light","box","ceil",-0.05,0.05,None,[("القدرة","43 واط LED"),("الفيض الضوئي","4900 لومن"),("درجة الحماية","IP20"),("الغطاء","شبكة عاكسة مزدوجة (Flexi-glass louvre)"),("النوع في المفتاح","TYPE-5")],[asm_h],LIGHT_SRC)
add("L6","E.light","كشاف غاطس بناشر منشوري 31 واط LED","Recessed fixture with prismatic diffuser 31W LED","m_light","box","ceil",-0.05,0.05,None,[("القدرة","31 واط LED"),("الفيض الضوئي","3700 لومن"),("درجة الحماية","IP54"),("الغطاء","ناشر منشوري"),("النوع في المفتاح","TYPE-6")],[asm_h],LIGHT_SRC)
add("L7","E.light","كشاف سلم سقفي 19 واط LED","Ceiling mounting staircase fixture 19W LED","m_light","disc","ceil",-0.07,0.07,None,[("القدرة","19 واط LED"),("الفيض الضوئي","1920 لومن"),("درجة الحماية","IP40"),("النوع في المفتاح","TYPE-7")],[asm_h],LIGHT_SRC)
add("L8","E.light","كشاف هابط غاطس 26 واط LED","Recessed down light 26W LED","m_light","disc","ceil",-0.04,0.04,None,[("القدرة","26 واط LED"),("الفيض الضوئي","2000 لومن"),("درجة الحماية","IP54"),("النوع في المفتاح","TYPE-8")],[asm_h],LIGHT_SRC)
add("L9","E.light","كشاف هابط غاطس 28 واط LED بناشر معتم","Recessed down light 28W LED, opal diffuser","m_light","disc","ceil",-0.04,0.04,None,[("القدرة","28 واط LED"),("الفيض الضوئي","3000 لومن"),("درجة الحماية","IP40"),("الغطاء","ناشر أوبال"),("النوع في المفتاح","TYPE-9")],[asm_h],LIGHT_SRC)
add("L10","E.light","كشاف منحدر 26 واط LED","Ramp light 26W LED","m_light","box","ceil",-0.10,0.10,None,[("القدرة","26 واط LED"),("الفيض الضوئي","1200 لومن"),("درجة الحماية","IP65"),("النوع في المفتاح","TYPE-10")],[asm_h],LIGHT_SRC)
add("L11","E.light","كشاف جداري خارجي 2×10 واط LED","Wall mounting external light 2x10W LED","m_light","plate","wall",2.20,0.12,(18,10),[("القدرة","2×10 واط LED"),("الفيض الضوئي","936 لومن"),("درجة الحماية","IP65"),("النوع في المفتاح","TYPE-11")],[asm_h,"ارتفاع التركيب 2.2 م: افتراض"],LIGHT_SRC)
add("L12","E.light","ثريا (خطاف ووردة سقف ولمبة LED) — صغيرة","Chandelier light (hook, ceiling rose, LED lamp) — small","m_light","pend","ceil",-0.55,0.30,None,[("النوع في المفتاح","TYPE-12"),("القدرة","غير مذكورة في المفتاح")],[asm_h,"طول التعليق: افتراض"],LIGHT_SRC)
add("L13","E.light","ثريا (خطاف ووردة سقف ولمبة LED) — كبيرة","Chandelier light (hook, ceiling rose, LED lamp) — large","m_light","pend","ceil",-0.60,0.35,None,[("النوع في المفتاح","TYPE-13"),("القدرة","غير مذكورة في المفتاح")],[asm_h,"طول التعليق: افتراض"],LIGHT_SRC)
# ---- light switches / control (legend refs 1..11)
SW_NOTE="(10 أمبير، 20 أمبير عند أكثر من 10 نقاط إنارة)"
for i,(ar,en,n) in enumerate([("مفتاح إنارة مفرد باتجاه واحد","One gang one way switch",1),("مفتاح إنارة مزدوج باتجاه واحد","Two gang one way switch",2),("مفتاح إنارة ثلاثي باتجاه واحد","Three gang one way switch",3),("مفتاح إنارة مفرد مقاوم للماء","Water-proof one gang one way switch",1),("مفتاح إنارة مزدوج مقاوم للماء","Water-proof two gang one way switch",2),("مفتاح مفرد باتجاهين","One gang two ways switch",1)],start=1):
    add(f"S{i}","E.socket",ar,en,"m_plate","plate","wall",MH["switch"],0.09,(9+4*(n-1),9),[("التيار",SW_NOTE),("عدد المفاتيح",str(n)),("المرجع في المفتاح",str(i))],["ارتفاع التركيب 1.30 م من مخطط تفاصيل EP-109"],LIGHT_SRC)
add("S7","E.socket","مفتاح تحكم (Override) بالإنارة الخارجية","Override switch to control external lights","m_plate","plate","wall",MH["switch"],0.09,(10,9),[("المرجع في المفتاح","7")],["ارتفاع التركيب 1.30 م من EP-109"],LIGHT_SRC)
add("S8","E.socket","مفتاح ضغط للسلم مع مؤقت","Stair case push switch with timer","m_plate","plate","wall",MH["switch"],0.09,(9,9),[("المرجع في المفتاح","8")],["ارتفاع التركيب 1.30 م من EP-109"],LIGHT_SRC)
add("S9","M.fan","مروحة شفط خطية (Inline)","Inline type exhaust fan","m_fan","disc","ceil",-0.25,0.25,None,[("المرجع في المفتاح","9")],["القدرة والتدفق غير مذكورين في مفتاح الإنارة؛ راجع جدول التهوية الميكانيكي"],LIGHT_SRC)
add("S10","E.socket","جرس وزر جرس","Bell and bell push","m_plate","plate","wall",MH["switch"],0.09,(8,8),[("المرجع في المفتاح","10")],["ارتفاع التركيب 1.30 م من EP-109"],LIGHT_SRC)
add("S11","E.socket","حساس حركة","Motion sensor","m_sensor","disc","ceil",-0.05,0.05,None,[("المرجع في المفتاح","11")],["نوع الحساس وزاوية الكشف غير مذكورة"],LIGHT_SRC)

PWR_SRC="ELEC1 مفتاح القوى (ELEC. POWER LEGEND) في لوحات EP-101..EP-105"
def sock(id,ar,en,w,d,mz,h=0.09,spec=(),asm=(),mode="wall",mat="m_plate"):
    add(id,"E.socket",ar,en,mat,"plate",mode,mz,h,(w,d),spec,list(asm)+(["ارتفاع التركيب 0.40 م من مخطط تفاصيل EP-109"] if abs(mz-0.4)<1e-6 else []),PWR_SRC)
sock("P1","مقبس 13 أمبير مفرد مع مفتاح","13A switch socket outlet",9,9,MH["socket"],spec=[("التيار","13 أمبير"),("النوع","مقبس مفتاحي مفرد")])
sock("P2","مقبس 13 أمبير مزدوج مع مفتاح","13A double switch socket outlet",15,9,MH["socket"],spec=[("التيار","13 أمبير"),("النوع","مقبس مفتاحي مزدوج")])
sock("P3","مقبس 13 أمبير بمستوى السقف","13A switch socket — ceiling level",9,9,2.30,spec=[("التيار","13 أمبير"),("الموضع","بمستوى السقف")],asm=["ارتفاع التركيب 2.3 م: افتراض"])
sock("P4","مقبس 13 أمبير مقاوم للماء (W/P)","13A switch socket W/P",10,10,MH["socket"],h=0.10,spec=[("التيار","13 أمبير"),("الحماية","مقاوم للماء W/P")],mat="m_plate_wp")
sock("P5","مقبس 15 أمبير لوحدة FCU (مفتاح ثنائي القطب مع مؤشر نيون)","15A switch socket for FCU (DP switch with neon)",9,9,MH["fcu_unit"],spec=[("التيار","15 أمبير"),("النوع","مفتاح ثنائي القطب مع مؤشر نيون"),("الغرض","تغذية وحدة ملف المروحة FCU")],asm=["ارتفاع 1.30 م (وحدة اتصال مفتاحية عامة) من EP-109"])
sock("P6","مخرج 15 أمبير للافتات (Spur)","15A spur outlet (for sign board)",9,9,2.20,spec=[("التيار","15 أمبير"),("الغرض","لوحة إعلان")],asm=["ارتفاع التركيب: افتراض"])
sock("P7","مقبس 20 أمبير مع مخرج مرن","20A switch socket with flex outlet",9,9,MH["cooker_flex"],spec=[("التيار","20 أمبير"),("الغرض","مخرج مرن (طباخ/جهاز)")],asm=["ارتفاع 0.40 م (مخرج الطباخ المرن) من EP-109"])
sock("P8","مفتاح 20 أمبير ثنائي القطب مع مخرج مرن","20A DP switch socket with flex outlet",9,9,MH["isolator"],spec=[("التيار","20 أمبير"),("الغرض","سخان مياه / جهاز ثابت")],asm=["ارتفاع 1.30 م (عازل) من EP-109"])
sock("P9","وحدة تحكم الطباخ CCU","CCU for cooker",9,14,1.10,h=0.14,spec=[("الغرض","وحدة تحكم الطباخ"),("الارتفاع","200 مم فوق سطح العمل")],asm=["سطح العمل 0.90 م: افتراض؛ المركز 1.10 م"])
sock("P10","نقطة سخان مياه","Water heater connection",12,6,2.15,h=0.12,spec=[("الغرض","توصيل سخان مياه كهربائي")],asm=["ارتفاع التركيب: افتراض"])
sock("P11","صندوق أرضي بمقبس 13 أمبير مزدوج ومخرج RJ45 مزدوج","Floor box with 13A double socket and dual RJ45",15,10,0.0,h=0.05,spec=[("المقبس","13 أمبير مزدوج"),("البيانات","مخرج RJ45 مزدوج")],mode="floor")
sock("P12","عازل ثلاثي الأطوار TPN (حسب قدرة الآلة)","TPN isolator 1P65 (rated per machine)",16,12,MH["isolator"],h=0.16,spec=[("النوع","عازل TPN"),("الحماية","IP65"),("السعة","حسب قدرة الآلة")],asm=["ارتفاع 1.30 م من EP-109"],mat="m_isolator")
sock("P13","عازل أحادي الطور SPN (حسب قدرة الآلة)","SPN isolator 1P65 (rated per machine)",13,12,MH["isolator"],h=0.14,spec=[("النوع","عازل SPN"),("الحماية","IP65"),("السعة","حسب قدرة الآلة")],asm=["ارتفاع 1.30 م من EP-109"],mat="m_isolator")
sock("P14","لوحة تحكم (C.P)","Control panel (C.P)",40,18,1.00,h=0.60,spec=[("النوع","لوحة تحكم")],asm=["الأبعاد من رمز المخطط؛ ارتفاع التركيب: افتراض"],mat="m_panel")
sock("P15","بنك مكثفات (CB)","Capacitor bank (CB)",60,30,0.0,h=1.20,spec=[("النوع","بنك مكثفات"),("السعة (من المخطط الأحادي)","220 كيلوفار")],asm=["أبعاد البنك: من رمز المخطط"],mode="floor",mat="m_panel")
sock("P16","وحدة تحكم المستهلك (CCU)","Consumer control unit",20,10,1.60,h=0.20,spec=[("النوع","وحدة تحكم المستهلك")],asm=["ارتفاع التركيب: افتراض"],mat="m_panel")
sock("P17","لوحة توزيع (DB)","Distribution board (DB)",40,15,1.20,h=0.60,spec=[("العرض × الارتفاع","40 × 60 سم (DB-S)"),("أعلى اللوحة عن الأرضية","180 سم")],asm=["العمق 15 سم: افتراض"],mat="m_panel")
sock("P18","لوحة توزيع فرعية رئيسية (SMDB)","Sub main distribution board (SMDB)",80,25,0.80,h=1.00,spec=[("العرض × الارتفاع","80 × 100 سم (SMDB-F)"),("أعلى اللوحة عن الأرضية","180 سم (افتراض بنفس منطق DB)")],asm=["العمق 25 سم: افتراض"],mat="m_panel")
sock("P19","لوحة توزيع رئيسية (MDB)","Main distribution board (MDB)",200,60,0.0,h=2.20,spec=[("النوع","MDB من 12 مخرجًا Form-4 Type-6"),("القاطع الرئيسي","ACB بقدرة 2000 أمبير TPN"),("قضبان التوزيع","نحاس مقلّون 2000 أمبير 4P"),("قدرة القطع","50 كيلو أمبير"),("الحماية","IP54")],asm=["أبعاد اللوحة من رمز المخطط؛ الارتفاع 2.2 م: افتراض"],mode="floor",mat="m_panel")

FA_SRC="ELEC2 مفتاح الإنذار (FIRE ALARM LEGEND) في لوحات FA-101..FA-105"
def fa(id,cat,ar,en,mat,shape,mode,z0,h,wd=None,spec=(),asm=(),src=FA_SRC):
    add(id,cat,ar,en,mat,shape,mode,z0,h,wd,spec,asm,src)
fa("F1","E.fa","كاشف دخان (SD)","Smoke detector (SD)","m_fa","disc","ceil",-0.06,0.06,(10,10),[("النوع","كاشف دخان نقطي")],["الطراز والعنوان (addressable) غير مذكورين"])
fa("F2","E.fa","كاشف حرارة (H)","Heat detector (H)","m_fa","disc","ceil",-0.06,0.06,(10,10),[("النوع","كاشف حرارة نقطي")],["الطراز ودرجة التفعيل غير مذكورين"])
fa("F3","E.fa","نقطة كسر زجاج (إنذار يدوي)","Break glass point","m_fa_red","plate","wall",MH["fa_bg"],0.09,(9,9),[("النوع","نقطة إنذار يدوي")],["ارتفاع التركيب 1.30 م من EP-109"])
fa("F4","E.fa","جرس/صفارة مع وامض (Sounder with flasher)","Sounder with flasher","m_fa_red","plate","wall",MH["fa_bell"],0.10,(14,10),[("النوع","صفارة مع وامض")],["ارتفاع التركيب 2.2 م (جرس الإنذار) من EP-109"])
fa("F5","E.fa","كاشف دخان مع صفارة","Smoke detector with sounder","m_fa","disc","ceil",-0.07,0.07,(12,12),[("النوع","كاشف دخان مع صفارة مدمجة")],["الطراز غير مذكور"])
fa("F6","E.fa","كاشف أول أكسيد الكربون (CO)","Carbon monoxide detector","m_fa","disc","ceil",-0.06,0.06,(10,10),[("النوع","كاشف CO")],["موضع الكاشف على السقف: افتراض (بعض المنتجات تُركّب على الجدار)"])
fa("F7","E.panel","لوحة CO","CO panel","m_panel","plate","wall",1.40,0.40,(40,15),[("النوع","لوحة كواشف CO")],["الأبعاد من رمز المخطط؛ الارتفاع: افتراض"])
fa("F8","E.panel","لوحة التحكم بالإنذار (FACP)","Fire alarm control panel (FACP)","m_panel","plate","wall",1.30,0.60,(55,18),[("النوع","لوحة تحكم إنذار الحريق"),("منظومة الإنذار","عنونة (حسب مخطط FA)")],["الأبعاد من رمز المخطط؛ الارتفاع: افتراض"])
fa("F9","E.panel","لوحة تكرار إنذار الحريق (Repeater)","Repeated fire alarm control panel","m_panel","plate","wall",1.30,0.50,(45,15),[("النوع","لوحة تكرار")],["الأبعاد من رمز المخطط؛ الارتفاع: افتراض"])
fa("F10","E.emerg","إنارة طوارئ LED ذاتية (سطحية)","Emergency light LED self-contained (surface)","m_emerg","disc","ceil",-0.07,0.07,(14,14),[("النوع","إنارة طوارئ LED ذاتية البطارية"),("التركيب","سطحي")],["الاستطاعة ومدة التشغيل غير مذكورتين"])
fa("F11","E.emerg","إنارة طوارئ LED ذاتية (غاطسة)","Emergency light LED self-contained (recessed)","m_emerg","disc","ceil",-0.04,0.04,(14,14),[("النوع","إنارة طوارئ LED ذاتية البطارية"),("التركيب","غاطس")],["الاستطاعة ومدة التشغيل غير مذكورتين"])
fa("F12","E.emerg","إنارة طوارئ LED ذاتية IP54 (غاطسة)","Emergency light LED self-contained IP54 (recessed)","m_emerg","disc","ceil",-0.04,0.04,(14,14),[("النوع","إنارة طوارئ LED ذاتية البطارية"),("الحماية","IP54"),("التركيب","غاطس")],["الاستطاعة ومدة التشغيل غير مذكورتين"])
fa("F13","E.emerg","لوحة مخرج طوارئ (EXIT) LED ذاتية","Exit sign (LED) self-contained","m_exit","plate","wall",2.20,0.18,(35,6),[("النوع","لوحة مخرج LED ذاتية")],["ارتفاع التركيب 2.2 م: افتراض (فوق الباب)"])
fa("F14","E.panel","لوحة المراقبة المركزية","Central monitoring control panel","m_panel","plate","wall",1.30,0.50,(45,15),[("النوع","لوحة مراقبة مركزية")],["الأبعاد من رمز المخطط؛ الارتفاع: افتراض"])
fa("F15","E.fa","سماعة إخلاء جدارية","Wall mounted evacuation speaker","m_speaker","plate","wall",2.20,0.16,(16,10),[("النوع","سماعة إخلاء صوتي جدارية")],["ارتفاع التركيب 2.2 م: افتراض"])
fa("F16","E.fa","سماعة إخلاء جدارية مقاومة للجو IP54","Weatherproof wall mounted evacuation speaker IP54","m_speaker","plate","wall",2.20,0.16,(16,10),[("النوع","سماعة إخلاء جدارية"),("الحماية","IP54")],["ارتفاع التركيب: افتراض"])
fa("F17","E.fa","سماعة إخلاء سقفية","Ceiling mounted evacuation speaker","m_speaker","disc","ceil",-0.08,0.08,(16,16),[("النوع","سماعة إخلاء سقفية")],["القدرة غير مذكورة"])
fa("F18","E.lc","مقبس هاتف (Telephone jack)","Telephone jack","m_plate","plate","wall",MH["tel"],0.09,(9,9),[("النوع","مقبس هاتف")],["ارتفاع التركيب 0.40 م من EP-109"],"ELEC2 FA legend")
fa("F19","E.panel","لوحة التحكم بالإخلاء الصوتي","Voice evacuation control panel","m_panel","plate","wall",1.30,0.50,(45,15),[("النوع","لوحة تحكم الإخلاء الصوتي")],["الأبعاد من رمز المخطط؛ الارتفاع: افتراض"])

LC_SRC="ELEC2 مفاتيح التيار الخفيف (SMATV / INTERCOM / ACCESS CONTROL / CCTV) في لوحات LC-101..LC-106"
def lc(id,ar,en,mat,shape,mode,z0,h,wd=None,spec=(),asm=(),cat="E.lc"):
    add(id,cat,ar,en,mat,shape,mode,z0,h,wd,spec,asm,LC_SRC)
lc("T1","مخرج تلفزيون","T.V outlet","m_plate_lc","plate","wall",MH["tv"],0.09,(9,9),[("النوع","مخرج SMATV")],["ارتفاع التركيب 0.40 م من EP-109"])
lc("T2","صندوق وصلات تلفزيون","T.V junction box","m_plate_lc","plate","wall",2.00,0.20,(20,10),[("النوع","صندوق وصلات SMATV")],["ارتفاع التركيب: افتراض"])
lc("T3","مبدّل متعدد 16 مدخل (IF+1RF)","16 M.S IF+1RF multi switcher","m_panel","plate","wall",1.50,0.40,(40,15),[("النوع","مبدّل متعدد 16 مخرجًا")],["الأبعاد وارتفاع التركيب: افتراض"])
lc("T4","صحن استقبال 1.2 م (SMATV)","1.2 m dish (SMATV)","m_dish","dish","floor",1.10,0.10,(120,120),[("القطر","1.2 م")],["موضع الارتفاع على السطح: افتراض"])
lc("T5","مبدّل مفرد (Single switch)","Single switch","m_plate_lc","plate","wall",1.50,0.20,(20,10),[("النوع","مبدّل مفرد SMATV")],["الأبعاد: افتراض"])
lc("T6","وحدة إنتركم صوت/صورة","Audio video intercom","m_plate_lc","plate","wall",1.40,0.20,(15,5),[("النوع","وحدة إنتركم صوت وصورة")],["الأبعاد وارتفاع التركيب: افتراض"])
lc("T7","قارئ بطاقة قرب (Proximity card reader)","Proximity card reader","m_access","plate","wall",1.20,0.12,(8,4),[("النوع","قارئ بطاقة قرب")],["ارتفاع التركيب 1.2 م: افتراض"])
lc("T8","ملامس باب (Door contact)","Door contact","m_access","plate","wall",2.05,0.05,(5,2),[("النوع","ملامس باب مغناطيسي")],["ارتفاع التركيب: افتراض"])
lc("T9","قفل مغناطيسي","Magnetic lock","m_access","plate","wall",2.00,0.25,(25,4),[("النوع","قفل مغناطيسي")],["الأبعاد وارتفاع التركيب: افتراض"])
lc("T10","زر خروج","Exit push button","m_access","plate","wall",1.20,0.09,(9,4),[("النوع","زر خروج")],["ارتفاع التركيب: افتراض"])
lc("T11","صندوق وصلات (Access control)","Junction box (access control)","m_access","plate","wall",2.10,0.15,(15,8),[("النوع","صندوق وصلات")],["ارتفاع التركيب: افتراض"])
lc("T12","كاميرا IP ثابتة","Fixed IP camera","m_cctv","disc","ceil",-0.12,0.12,(14,14),[("النوع","كاميرا مراقبة IP ثابتة")],["الطراز والدقة غير مذكورين"])
lc("T13","كاميرا IP مقاومة للجو W/P","W/P IP camera","m_cctv","plate","wall",2.60,0.14,(12,22),[("النوع","كاميرا IP مقاومة للجو")],["ارتفاع التركيب: افتراض"])
lc("T14","مسجّل فيديو رقمي (VDR)","Video digital recorder","m_panel","plate","wall",1.30,0.20,(45,30),[("النوع","مسجّل فيديو رقمي")],["الأبعاد وارتفاع التركيب: افتراض"])
lc("T15","شاشة LED 42 بوصة","42\" LED monitor","m_panel","plate","wall",1.60,0.55,(95,8),[("المقاس","42 بوصة")],["ارتفاع التركيب: افتراض"])
lc("T16","مخرج RJ45 مفرد","RJ45 single outlet","m_plate_lc","plate","wall",MH["tel"],0.09,(9,9),[("النوع","مخرج بيانات RJ45 مفرد")],["ارتفاع التركيب 0.40 م من EP-109"])
lc("T17","مخرج RJ45 مزدوج (صوت وCATV)","RJ45 dual outlet (voice & CATV)","m_plate_lc","plate","wall",MH["tel"],0.09,(15,9),[("النوع","مخرج RJ45 مزدوج (صوت وCATV)")],["ارتفاع التركيب 0.40 م من EP-109"])
lc("T18","وحدة شبكة ضوئية ONU 60×60×15 سم","Optical network unit 60x60x15 cm","m_panel","plate","wall",1.50,0.60,(60,15),[("الأبعاد","60 × 60 × 15 سم")],["ارتفاع التركيب: افتراض"])
lc("T19","لوح توزيع ضوئي صغير (Mini ODF)","Mini optical distribution frame","m_panel","plate","wall",1.40,0.40,(45,15),[("النوع","Mini ODF")],["الأبعاد وارتفاع التركيب: افتراض"])
lc("T20","لوح التوزيع الرئيسي MDF","Main distribution frame (MDF)","m_panel","plate","wall",1.00,1.00,(80,25),[("النوع","MDF")],["الأبعاد وارتفاع التركيب: افتراض"])

LTG_SRC="ELEC2 مفتاح الصواعق (LIGHTNING PROTECTION LEGEND) في لوحات LP-101..LP-107 ولوحة التفاصيل LP-108"
add("G1","E.ltg","مسطرة نحاس عارية 25×3 مم","25x3mm bare copper tape","m_cu","tape","wall",0.0,0.003,None,[("المقطع","25 × 3 مم"),("المادة","نحاس عاري")],["مسار الشريط من المخطط؛ الارتفاع على السطح/الواجهة: افتراض"],LTG_SRC)
add("G2","E.ltg","مشبك شريط","Tape clip","m_cu","disc","wall",0.0,0.03,(3,3),[("النوع","مشبك تثبيت الشريط")],[],LTG_SRC)
add("G3","E.ltg","حفرة تفتيش للتأريض مع قضيب","Earth inspection pit with earth rod","m_earth","disc","floor",-0.05,0.10,(30,30),[("القضيب","16 مم² — 3 × 1.2 م كحد أدنى")],["بقية الأبعاد من لوحة التفاصيل LP-108"],LTG_SRC)
add("G4","E.ltg","رأس صاعقة (Air terminal) 500 مم","Air terminal 500 mm","m_cu","mast","floor",0.0,0.50,(2,2),[("الطول","500 مم")],[],LTG_SRC)

# ---- legend text / cluster keyword -> class id (ordered, first match wins)
import re
LEG_MAP=[
 (r'^TYPE-(\d+)$', lambda m: "L"+m.group(1)),
 (r'ONE GANG ONE WAY SWITCH$|^ONE GANG ONE WAY', "S1"),
]
POWER_MAP=[
 (r'TPN ISOLATOR',"P12"),(r'SPN ISOLATOR',"P13"),
 (r'13A DOUBLE SWITCH SOCKET',"P2"),(r'13A SWITCH SOCKET OUTLET',"P1"),(r'CEILING LEVEL',"P3"),(r'W/P',"P4"),
 (r'15A SWITCH SOCKET FOR FCU',"P5"),(r'FLOOR BOX',"P11"),(r'15A SPUR',"P6"),
 (r'^20A SWITCH SOCKET WITH FLEX',"P7"),(r'^20 A DP',"P8"),(r'CCU FOR COOKER',"P9"),(r'WATER HEATER',"P10"),
 (r'CONTROL PANEL',"P14"),(r'CAPICTOR|CAPACITOR',"P15"),(r'CONSUMER CONTROL',"P16"),(r'SUB MAIN DISTRIBUTION',"P18"),(r'MAIN DISTRIBUTION BOARD',"P19"),(r'^DISTRIBUTION BOARD',"P17"),
]
FA_MAP=[
 (r'SMOKE DETECTOR WITH SOUNDER',"F5"),(r'SMOKE DETECTOR',"F1"),(r'HEAT DETECTOR',"F2"),(r'BREAK GLASS',"F3"),(r'SOUNDER WITH FLASHER',"F4"),(r'CARBON MONOXIDE',"F6"),
 (r'^CO PANEL',"F7"),(r'REPEATED FIRE ALARM',"F9"),(r'FIRE ALARM CONTROL PANEL',"F8"),
 (r'IP 54 EMERGENCY',"F12"),(r'EMERGENCY LIGHT.*Recessed',"F11"),(r'EMERGENCY LIGHT',"F10"),(r'EXIT SIGN',"F13"),(r'CENTRAL MONITORING CONTROL',"F14"),
 (r'WEATHERPROOF WALL MOUNTED EVAC',"F16"),(r'WALL MOUNTED EVAC',"F15"),(r'CEILING MOUNTED EVAC',"F17"),(r'TELEPHONE JACK',"F18"),(r'VOICE EVACUATION CONTROL',"F19"),
]
def map_label(rules,text):
    for rx,val in rules:
        m=re.search(rx,text)
        if m: return val(m) if callable(val) else val
    return None
