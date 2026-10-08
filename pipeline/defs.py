# shared definitions: levels, layer tree, materials
LEVELS=[
 {"id":"B","name":"البدروم","en":"Basement","ffl":-3.70,"top":-0.45},
 {"id":"G","name":"الأرضي","en":"Ground","ffl":0.35,"top":5.37},
 {"id":"1","name":"الأول","en":"1st","ffl":5.75,"top":8.87},
 {"id":"2","name":"الثاني","en":"2nd","ffl":9.25,"top":12.37},
 {"id":"3","name":"الثالث","en":"3rd","ffl":12.75,"top":15.87},
 {"id":"4","name":"الرابع","en":"4th","ffl":16.25,"top":19.37},
 {"id":"5","name":"الخامس","en":"5th","ffl":19.75,"top":22.87},
 {"id":"R","name":"السطح","en":"Roof","ffl":23.35,"top":26.40},
 {"id":"T","name":"سطح الغرف العلوي","en":"Top roof","ffl":26.85,"top":27.25},
]
LAYERS=[
 {"id":"S","name":"الإنشائي","color":"#8A94A3","subs":[
   ["S.raft","اللبشة والأساسات"],["S.pile","الخوازيق"],["S.col","الأعمدة"],["S.wall","الجدران الخرسانية والنوى"],["S.slab","البلاطات"],["S.beam","الجسور"],["S.stair","السلالم الخرسانية"],["S.ramp","منحدر السيارات"]]},
 {"id":"A","name":"المعماري","color":"#B9A89A","subs":[
   ["A.wall","الجدران والقواطع"],["A.door","الأبواب"],["A.win","النوافذ والواجهات الزجاجية"],["A.clad","الكسوة والواجهات"],["A.floor","تشطيب الأرضيات"],["A.ceil","الأسقف المستعارة"],["A.rail","الدرابزين والأسوار"],["A.fix","التجهيزات (مطبخ/حمامات/خزائن)"],["A.site","الموقع والتنسيق"]]},
 {"id":"M","name":"الميكانيكي (تكييف وتهوية)","color":"#3F7FBF","subs":[
   ["M.equip","معدات التكييف"],["M.duct","مجاري الهواء"],["M.outlet","ناشرات وشبكات الهواء"],["M.damper","المخمدات"],["M.pipe","أنابيب المياه المبردة"],["M.fan","المراوح"]]},
 {"id":"E","name":"الكهربائي","color":"#9A6FD0","subs":[
   ["E.panel","اللوحات والمحولات"],["E.gen","المولد"],["E.tray","مسارات الكابلات"],["E.light","الإنارة"],["E.emerg","إنارة الطوارئ"],["E.socket","المقابس والمفاتيح"],["E.fa","الإنذار والحريق"],["E.lc","التيار الخفيف"],["E.ltg","الصواعق والتأريض"]]},
 {"id":"P","name":"الإمدادات الصحية والإطفاء","color":"#1FA187","subs":[
   ["P.tank","الخزانات"],["P.pump","المضخات"],["P.cold","مياه باردة"],["P.hot","مياه ساخنة"],["P.drain","صرف صحي"],["P.storm","تصريف أمطار"],["P.irr","الري"],["P.fix","الأجهزة الصحية"],["P.heater","السخانات"],["P.ff","شبكة الإطفاء"]]},
]
MATS={
 "conc":{"name":"خرسانة مسلحة C40 (OPC) — فوق منسوب الأرضي","color":"#bdbab2","code":"Mix D/E"},
 "conc_sr":{"name":"خرسانة مسلحة C40 مقاومة للكبريتات (SRC) — تحت الأرض","color":"#a5a8ab","code":"Mix B/C"},
 "block":{"name":"بلوك مجوف (قواطع داخلية 100/200 مم)","color":"#e7e1d3","code":"BOQ 4.2"},
 "block_ext":{"name":"بلوك 200 مم (جدران محيطية/حرارية)","color":"#d8d1c0","code":"BOQ 4.2/4.4"},
 "door_wood":{"name":"باب خشبي — قشرة جوز","color":"#7a5236","code":"A700"},
 "door_steel":{"name":"باب فولاذ مجلفن مدهون","color":"#8c9199","code":"A700"},
 "door_alu":{"name":"باب ألمنيوم مع لوفر","color":"#b4b9c0","code":"A700"},
 "glass_vis":{"name":"زجاج مزدوج عاكس 6-12-6 (رؤية)","color":"#7fb2c8","opacity":0.42,"code":"A200 بند 3"},
 "glass_span":{"name":"زجاج سباندريل (غير شفاف)","color":"#3f5d6d","opacity":0.9,"code":"A200 رمز S"},
 "frame_alu":{"name":"إطار ألمنيوم مطلي بالمسحوق (اللون RAL غير محدد)","color":"#5b6168","code":"A200 بند 3"},
 "clad_porc":{"name":"كسوة بورسلين 60×120 سم (W12)","color":"#e8e8e4","code":"W12"},
 "clad_grc":{"name":"GRC دهان أكريليك بيج","color":"#d8c8a6","code":"A200 بند 2"},
}
MATS.update({
 "m_fcu":{"name":"وحدة ملف مروحة FCU","color":"#7b4fa3","code":"AC-106"},
 "m_duct":{"name":"مجرى هواء معزول (صاج مجلفن)","color":"#9db7cf","code":"AC-100..105"},
 "m_diffuser":{"name":"ناشر تغذية 4 اتجاهات","color":"#3fa34d","code":"M_SAD_DIFF"},
 "m_diffuser_r":{"name":"ناشر رجوع","color":"#c9473f","code":"M_RAD_DIFF"},
 "m_grille":{"name":"شبكة تغذية","color":"#2fb3b3","code":"M_SAG_GRILL"},
 "m_grille_r":{"name":"شبكة رجوع","color":"#e08a2c","code":"M_RAG_GRILL"},
 "m_damper":{"name":"مخمد (VCD/FD/MFD)","color":"#3b3f45","code":"M_HVAC_DAM"},
 "m_therm":{"name":"ثرموستات","color":"#2b6fd6","code":"T"},
})
MATS.update({
 "p_cold":{"name":"أنبوب مياه باردة PPR/PEX","color":"#2a74d9","code":"M_WS_CW"},
 "p_hot":{"name":"أنبوب مياه ساخنة PPR مستقر","color":"#d94a2a","code":"M_WS_HW"},
 "p_soil":{"name":"أنبوب صرف (Soil) UPVC","color":"#8a6a3a","code":"M_DR_SP"},
 "p_waste":{"name":"أنبوب صرف (Waste) UPVC","color":"#a8844a","code":"M_DR_WP"},
 "p_vent":{"name":"أنبوب تهوية UPVC","color":"#b9b07a","code":"M_DR_VP"},
 "p_ff":{"name":"أنبوب إطفاء فولاذ أسود (رشاشات)","color":"#d11f1f","code":"M_FF_PIPE"},
 "p_sprk":{"name":"رشاش إطفاء","color":"#c0392b","code":"M_FF_SP"},
 "p_ffc":{"name":"صندوق إطفاء (خرطوم وصمام هبوط)","color":"#e03a3a","code":"M_FF_FFC"},
 "p_heater":{"name":"سخان مياه كهربائي أفقي","color":"#19b5b5","code":"WATER"},
 "p_valve":{"name":"صمام/عداد","color":"#3a3f46","code":"M_WS_TEXT"},
})
MATS.update({
 "m_light":{"name":"كشاف إنارة LED","color":"#ffe27a","code":"EL-LEGEND"},
 "m_plate":{"name":"لوحة مقبس/مفتاح","color":"#e8e2c9","code":"EP-LEGEND"},
 "m_plate_wp":{"name":"مقبس مقاوم للماء W/P","color":"#cfc7a5","code":"EP-LEGEND"},
 "m_isolator":{"name":"عازل كهربائي","color":"#d9822b","code":"EP-LEGEND"},
 "m_fan":{"name":"مروحة شفط","color":"#a0a8b0","code":"EL-LEGEND"},
 "m_sensor":{"name":"حساس","color":"#f0ead2","code":"EL-LEGEND"},
 "m_panel":{"name":"لوحة كهربائية/تحكم","color":"#7b8794","code":"EP-LEGEND"},
 "m_fa":{"name":"كاشف إنذار حريق","color":"#f7f3e8","code":"FA-LEGEND"},
 "m_fa_red":{"name":"نقطة/صفارة إنذار (أحمر)","color":"#d62828","code":"FA-LEGEND"},
 "m_emerg":{"name":"إنارة طوارئ","color":"#3da35d","code":"FA-LEGEND"},
 "m_exit":{"name":"لوحة مخرج طوارئ","color":"#2fa84f","code":"FA-LEGEND"},
 "m_speaker":{"name":"سماعة إخلاء","color":"#b8bec6","code":"FA-LEGEND"},
 "m_plate_lc":{"name":"مخرج تيار خفيف","color":"#7c6fd6","code":"LC-LEGEND"},
 "m_dish":{"name":"صحن استقبال","color":"#dfe6ec","code":"LC-LEGEND"},
 "m_access":{"name":"تحكم بالدخول","color":"#5a6b7a","code":"LC-LEGEND"},
 "m_cctv":{"name":"كاميرا مراقبة","color":"#2b2f36","code":"LC-LEGEND"},
 "m_cu":{"name":"نحاس عاري (صواعق/تأريض)","color":"#b87333","code":"LP-LEGEND"},
 "m_earth":{"name":"حفرة تأريض","color":"#7a5a3a","code":"LP-LEGEND"},
 "m_conduit":{"name":"مسار أنابيب/كابلات (توصيل الدوائر)","color":"#e9b200","code":"E.CONNE"},
 "m_tray":{"name":"حامل كابلات مجلفن","color":"#9aa5b1","code":"EP-109"},
 "m_gen":{"name":"مولد/محوّل/معدات الكهرباء الرئيسية","color":"#5f7d95","code":"EP-108"},
})
import finishes as _FN
for _k,_v in _FN.FIN.items():
    MATS["fin_"+_k]={"name":_v[0],"color":_v[1],"code":_k}
