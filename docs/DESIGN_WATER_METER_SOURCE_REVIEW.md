# عدادات الماء ورمز الغسالة — WMT

<div dir="rtl">

## المرجع والقرار

MECH2:20 يحتوي ست دوائرMخام19285/19286/19287/19288/19289/19291،وMECH2:21 يحتوي19950/19951/19952/19953/19954/19956. دائرةالمفتاح20470/21950وحرفMنص277/251 والعبارة`WATER METER`نص279/253 تثبت الدلالة. تكرر المسقط21للطوابق2–5؛الحصيلة30مؤشرًا،لا30شكلًا خامًا مختلفًا في الورق.

النص`W/M` داخلWASH بجوارD/W ليس دائرةM. `plumb.extract_ws/emit_ws` حوله خطأ إلى`valve_WM` نصي. تقاعدت الهويات `P.cold-1-0232/2-0470/3-0716/4-0962/5-1208` بحراسcategory/type/level/gSHA. لم يضاف صمام أو washer جديد من النص.

الغسالة موجودة أصلًا كجسم عرض معماري مستقل: الأول`A.stage-1-X8498`والمتكرر`A.stage-2-X5732/3-X6419/4-X7106/5-X7793`. مصدرARCH1:6raw20133–20138 وARCH1:7raw18118–18123 يحتوي المربع والدوائر في غرفةWASH. هذا إثبات حضور الرمز وتجنب التكرار؛أبعاد جسم العرض القديم ومنسوبه ومادته لا تصبح مثبتة بهذا الفحص.

## التمثيل وحدوده

أضيف30عنصر`P.equip-<level>-WMT####`،نوع`ws_water_meter_graphic`،syscold،مؤشر3سم×2سم للعرض فقط عندFFL الطابق. XY مركز دائرةM الفعلية بكامل منحنياتها،معrawitems وMchar ومفتاح الرسم وتسجيل المصدر. قطر دائرةالرسم≈7سم ليس قطر جهاز تنفيذي،ولا مقامًا لإثبات مقاس أو منفذ.

كل مؤشراتWMT تحمل`source_locked_xy` و`no_connectors`؛أبعاد جسم العداد وZ والمادة واللون والتركيب والمنافذ/contact غير مثبتة صراحة. لا يدخل المؤشر كطرف/مصدر أو conductor فيlifecycle،ولا يصل إلى أقرب أنبوب.

## API والبيانات والبوابة

`water_meter_source_remaining.apply(M, els=None, verbose=False)` بعدWSC/WST وقبلSUP/CN؛aliasbuild. `TYPES` يحتوي النوع السابق؛P.equip subcategoryموجودة للأجهزة المثبتة بالرموز. البيانات `pipeline/data/water_meter_source_remaining.json` تشمل30binding،5تقاعد،5شواهدwasher ومفاتيح الصفحتين. إثباتFireالخام: `work/water-meter-source-semantics.json`.

البوابة`water_meter_source_check` تقرأ4منحنياتcلكل دائرة وMcharمنPDF الحالي،تتحقق احتواءالحرف وتطابق المفتاح ثم تقيس مركزg. `water_meter_source_checks` يتحققW/Mالخام والتقاعد وبقاءwasherمرةواحدة؛لا يرقّي جسمwasher إلىrawexact.

30rawchecks+10sourcepresence/retirementchecks:صفر فشل،أقصىXY0.00005492سم. probe+1سم يفشل،وتغييرdrawingindex يفشل،والتطبيق2×هندسيًا ثابت؛جميع أجسامS وبقيةالهويات الباقية دون تغيير.

بصمة البيانات: `71ec7c4aec35770a247357fdf05bdd0c4a41a39acaf8573868acfcd76ac31fc7`.

## أثر lifecycle المعزول

بعدWST ثم إعادةCNللcold/hotفي الذاكرة:قبلWMTcoldcon1362/orph199/reach1163/dist282؛بعدهcoldcon1356/orph193/reach1163/dist282. الستة المزالة منconductors موصلاتK مشتقة غيرreachable،ولا تثبت صلة بالجهاز. hotcon572/orph24/reach548/dist121 ثابت. سجل الفحص `work/water-meter-source-wave-proof.json`؛لا تغييرbaseline أوmodel في هذا العمل.

</div>
