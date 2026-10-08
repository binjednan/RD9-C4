# جرد المشروع الكامل — نموذج C4 ثلاثي الأبعاد (RD09)

يُولَّد آليًا بأمر `python3 pipeline/post_model.py` من الملفات نفسها (آخر توليد: 2026-10-08 08:58). كل رقم هنا مقيس لا مكتوب باليد.

## 1) النموذج

- **27,010** عنصرًا في **295** نوعًا على **9** مستويات و**30** وحدة سكنية، بـ**207** خامة و**35** رمز تشطيب (A500).
- كماليات إخراجية (للعرض لا للتنفيذ): **2,997** عنصرًا.

### درجات الموثوقية (ما يمكن الاعتماد عليه من كل عنصر)

| الدرجة | العناصر | النسبة | المعنى |
|---|---:|---:|---|
| موثّق | 4,188 | 15.5% | الموضع والمنسوب والمواصفة مقروءة من المخططات والجداول |
| مشتق | 12,852 | 47.6% | محسوب بقاعدة معلومة المعطيات (ارتفاعات التركيب، سقف FCL، سحب الجهاز إلى الجدار ...) |
| تخمين | 6,973 | 25.8% | اختاره النموذج لغياب البيان (مناسيب الخدمات في فراغ السقف، أقطار مفترضة، أجهزة بلا حامل ...) |
| إخراجي | 2,997 | 11.1% | كماليات للعرض فقط |

لا يوجد عنصر «مطابق للمنفَّذ» بعد؛ تلك الدرجة تُمنح عند اعتماد مخططات الأز-بيلت (BIM Forum LOD 500 = متحقَّق ميدانيًا).

### حسب القسم

| القسم | العناصر | موثّق | مشتق | تخمين | إخراجي |
|---|---:|---:|---:|---:|---:|
| الإنشائي | 784 | 17 | 767 | 0 | 0 |
| المعماري | 15,382 | 4,160 | 6,347 | 1,878 | 2,997 |
| الميكانيكي (تكييف وتهوية) | 2,515 | 0 | 888 | 1,627 | 0 |
| الكهربائي | 3,281 | 0 | 3,110 | 171 | 0 |
| الإمدادات الصحية والإطفاء | 5,048 | 11 | 1,740 | 3,297 | 0 |

### حسب الطابق

| الطابق | العناصر | موثّق | مشتق | تخمين | إخراجي | تعارض مؤكد | مرشح | تخمينات فردية |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| البدروم (-3.70) | 1,414 | 334 | 686 | 394 | 0 | 9 | 13 | 26 |
| الأرضي (+0.35) | 3,467 | 586 | 995 | 561 | 1,325 | 3 | 4 | 50 |
| الأول (+5.75) | 4,288 | 664 | 2,218 | 1,072 | 334 | 9 | 28 | 28 |
| الثاني (+9.25) | 4,229 | 628 | 2,149 | 1,116 | 336 | 9 | 30 | 31 |
| الثالث (+12.75) | 4,240 | 628 | 2,161 | 1,116 | 335 | 9 | 30 | 31 |
| الرابع (+16.25) | 4,232 | 628 | 2,149 | 1,116 | 339 | 9 | 30 | 31 |
| الخامس (+19.75) | 4,222 | 628 | 2,150 | 1,116 | 328 | 9 | 22 | 31 |
| السطح (+23.35) | 862 | 88 | 294 | 480 | 0 | 1 | 2 | 53 |
| سطح الغرف العلوي (+26.85) | 56 | 4 | 50 | 2 | 0 | 0 | 0 | 6 |

## 2) المصادر (المخططات)

226 ورقة في 7 ملفات؛ **130** منها مُستشهَد بها في النموذج (57%).

| الملف | الأوراق | المستعملة |
|---|---:|---:|
| المعماري — الجزء 1 | 18 | 13 |
| المعماري — الجزء 2 | 58 | 32 |
| الإنشائي | 32 | 23 |
| الميكانيكا — الجزء 1 | 29 | 13 |
| الميكانيكا — الجزء 2 | 37 | 19 |
| الكهرباء — الجزء 1 | 18 | 14 |
| الكهرباء — الجزء 2 | 34 | 16 |

| نوع الورقة | العدد | المستعمل |
|---|---:|---:|
| أخرى | 15 | 4 |
| ملاحظات / مفتاح | 9 | 6 |
| مسقط | 120 | 76 |
| مقطع / واجهة | 15 | 11 |
| جدول | 6 | 4 |
| تفصيل | 46 | 26 |
| مخطط تخطيطي | 15 | 3 |

### أوراق غير مستعملة من نوع مسقط / تفصيل / مقطع (مرشحة للاستخراج التالي)

| الملف | ص | الرقم | العنوان |
|---|---:|---|---|
| ARCH1 | 14 | A 300 | Section A-A |
| ARCH1 | 15 | A 301 | Section B-B |
| ARCH2 | 8 | A607 | Ramp Details 02 |
| ARCH2 | 10 | A701 | Door Details |
| ARCH2 | 16 | A803 | Window Details |
| ARCH2 | 18 | A1100 | Garbage Chute / Structural Details |
| ARCH2 | 27 | A1302 | Wardrobe Detail 03 |
| ARCH2 | 30 | A1402 | Ceiling Details |
| ARCH2 | 33 | 00 | Curtain Wall Details |
| ARCH2 | 36 | A1700 | Canopy Details |
| ARCH2 | 37 | A1800 | Ladder Details |
| ARCH2 | 39 | A1901 | Car Parking Details 02 |
| ARCH2 | 41 | A1903 | Traffic Control / Sign Details |
| ARCH2 | 43 | A2100 | Reception Dusk / Details |
| ARCH2 | 44 | A2200 | Basement Floor Signage / Layouts |
| ARCH2 | 45 | A2201 | Ground Floor Signage / Layouts |
| ARCH2 | 46 | A2202 | First Floor Signage / Layouts |
| ARCH2 | 47 | A2203 | Typical Floor Signage / Layouts |
| ARCH2 | 48 | A2204 | Roof Floor Signage / Layouts |
| ARCH2 | 52 | A2303 | Landscape Section / Details 02 |
| ARCH2 | 53 | A2304 | Landscape Section / Details 03 |
| STR | 5 | 00 | Basement Floor Loading Layout |
| STR | 6 | 00 | Ground Floor Loading Layout |
| STR | 7 | 00 | 1St - 5Th Floor Loading Layout |
| STR | 8 | 00 | Roof Floor Loading Layout |
| STR | 9 | 00 | Top Floor Loading Layout |
| STR | 13 | 00 | Shoring Plan |
| MECH1 | 9 | AC-107-B | Ac Details |
| MECH1 | 10 | AC-107-B | Ac Details |
| MECH1 | 17 | SM-100 | Basement Floor Plan / Smoke Management Layout |
| MECH1 | 18 | SM-101 | Ground Floor Plan / Smoke Management Layout |
| MECH1 | 19 | SM-102 | First Floor Plan / Smoke Management Layout |
| MECH1 | 20 | 00 | Typical Floor Plan / Smoke Management Layout |
| MECH1 | 21 | SM-104 | Roof Floor Plan / Smoke Management Layout |
| MECH1 | 23 | 00 | Basement Floor Plan / Ventilation Layout |
| MECH1 | 24 | 00 | Ground Floor Plan / Ventilation Layout |
| MECH1 | 25 | 00 | First Floor Plan / Ventilation Layout |
| MECH1 | 26 | 00 | Typical Floor Plan / Ventilation Layout |
| MECH1 | 27 | 00 | Roof Floor Plan / Ventilation Layout |
| MECH2 | 1 | 00 | Site Plan / Drainage Layout |
| MECH2 | 9 | DR-106 | Drainage Details |
| MECH2 | 16 | 00 | Fire Fighting Details |
| MECH2 | 17 | 00 | Site Plan / Water Supply Layout |
| MECH2 | 25 | 00 | Basement Floor Plan / Irrigation Layout |
| MECH2 | 26 | 00 | Ground Floor Plan / Irrigation Layout |
| MECH2 | 27 | 00 | Ground Floor Plan / Storm Water Layout |
| MECH2 | 28 | 00 | First Floor Plan / Storm Water Layout |
| MECH2 | 29 | 00 | Typical Floor Plan / Storm Water Layout |
| MECH2 | 30 | 00 | Roof Floor Plan / Storm Water Layout |
| MECH2 | 31 | SW-105 | Top Roof Plan / Storm Water Layout |
| MECH2 | 32 | 00 | Basement Floor Plan / Chilled Water Connection Layout |
| MECH2 | 33 | 00 | Ground Floor Plan / Chilled Water Connection Layout |
| MECH2 | 34 | CHW-102 | First Floor Plan / Chilled Water Connection Layout |
| MECH2 | 35 | CHW-103 | Typical Floor Plan / Chilled Water Connection Layout |
| MECH2 | 36 | 00 | Roof Floor Plan / Chilled Water Connection Layout |
| ELEC1 | 8 | 00 | Site Plan / Power Layout |
| ELEC1 | 18 | 00 | Electrical / General Details |
| ELEC2 | 1 | 00 | Ground Floor Plan / Earthing Protection Layout |
| ELEC2 | 10 | 00 | Fire Alarm / General Details |
| ELEC2 | 11 | 00 | Basement Floor Plan / Lightning Protection Layout |
| ELEC2 | 12 | 00 | Ground Floor Plan / Lightning Protection Layout |
| ELEC2 | 13 | 00 | First Floor Plan / Spot |
| ELEC2 | 14 | — | Typical Floor Plan / Lightning Protection Layout |
| ELEC2 | 17 | 00 | Lightning Protection / General Details |
| ELEC2 | 27 | 00 | Site Plan / Power Layout |
| ELEC2 | 28 | 00 | Basement Floor Plan / Telephone Layout |
| ELEC2 | 32 | 00 | Roof Floor Plan / Telephone Layout |
| ELEC2 | 34 | 00 | Telephone / General Details |

## 3) المتابعة

- **التعارضات** (521): مؤكد **58** · مرشح (اختلاف منسوب) **159** · هامشي **304** — في **471** مجموعة.
- **التخمينات**: **211** قاعدة (مرتفعة الأثر 45 · متوسطة 87 · منخفضة 79) و**287** قرارًا فرديًا بموضع/إزاحة.

### إغلاق القسم المعماري (ARCH_CLOSURE)

| البند | الحالة | الوصف |
|---|---|---|
| A | مغلق | الواجهات والنوافذ: عتبة بلوك+بورسلين 60 سم، شبكة الخلايا F/S/مفصلية، إطار بيج فاتح وزجاج بني فاتح عاكس |
| B | مغلق | الأسقف: مناسيب FCL الفعلية (شقق 2.40، ممر 2.35/2.50، ردهة الأرضي 3.40/3.55، خدمات 2.80، أروقة 3.75)، حذف أسقف الأدراج/المصاعد العائمة |
| C | مغلق | الدرج والبلاطات: فتحة بلاطة السطح العلوي (T) لمرور الدرج، أطراف الجدران عند الدرج |
| D | جزئي | اكتمال الجدران والغلاف: لا فجوات بين الأدوار ولا نهايات حرة |
| E | جزئي | تجهيزات الداخل: أجهزة صحية، مطابخ، دواليب (A1300–A1302)، إطارات الأبواب ومقابضها |
| F | جزئي | الخزانات (سطح + بدروم) والمعدات الظاهرة بأشكال حقيقية بدل المكعبات (مبرّدات، FAHU، مضخات، مراوح، سخانات، FCU، لوحات، محوّل، مولّد) |
| G | مفتوح | تشطيبات B/G/R حسب الجدول المعتمد وكسوة الردهات (W7 ترافرتين، W13 جرانيت) |
| H | جزئي | الواقعية: إنارة مشغّلة، ستائر، خامات إجرائية، أوراق أشجار، بقع ماء، ملعب الأطفال حسب اعتماد INEX/EDUPARK، تفاصيل خارجية |
| I | مفتوح | تدقيق نهائي + لقطات + توثيق |

## 4) العارض (الواجهة)

| المجال | الميزة | موجودة |
|---|---|---|
| 3D | نموذج ثلاثي الأبعاد بالمجسمات المجمّعة (Three.js) في ملف واحد | نعم |
| 3D | تحكم بالكاميرا: ماوس / تراك باد / لمس (إصبع تدوير، إصبعان تحريك وقرص) | نعم |
| 3D | قص أفقي وطولي وتفكيك الطوابق وعزل الوحدات (شقق) | نعم |
| 3D | إضاءة: نهار / غروب / ليل + تشغيل المصابيح | نعم |
| اللوحة | لوحة جانبية واحدة بأقسام قابلة للطيّ مع بحث سريع | نعم |
| اللوحة | بطاقة العنصر المحدد أعلى اللوحة (أقسام قابلة للطيّ، مصدر كل بيان) | نعم |
| اللوحة | إخفاء اللوحة بزر وتذكّر الحالة | نعم |
| التحليل | تعارضات: قائمة بحالات ومسار وصول وجولة مشي | نعم |
| التحليل | تصنيف التعارضات (مؤكد / مرشح اختلاف منسوب / هامشي) ومجموعات | نعم |
| التحليل | سجل التخمينات وأفضل موضع للمكوّنات بلا حامل | نعم |
| التحليل | درجة موثوقية لكل عنصر (موثّق / مشتق / تخمين / إخراجي) | نعم |
| العينات | مكتبة عينات تفصيلية بمعاينة منفردة وانتقال إلى الموضع | نعم |
| العينات | حديد التسليح بالأسياخ المستديرة عند الطلب | نعم |
| الواجهة | تبديل ما يفعله السحب بإصبع واحد (أزرار الوضع) | نعم |

## 5) الشيفرة والتوثيق والمخرجات

- خط الاستخراج (`pipeline/`): 84 ملفًا، 12,666 سطرًا. العارض (`src/`): 14 ملفات JavaScript + القالب، 3,314 سطرًا.
- التوثيق (`docs/`): ARCH_CLOSURE.md, CLASH_LOG.md, CONFLICTS.md, HANDOFF_2026-10-07.md, HANDOFF_2026-10-08.md, INVENTORY.md, PLACEMENT_AUDIT.md, PROGRESS.md, REMOVED_AUDIT.md, SAMPLES.md, SITE_PHOTOS.md.
- المخرج: `index.html` ملف واحد (11.62 م.ب) · المستودع `binjednan/RD9-C4` · العرض المباشر https://binjednan.github.io/RD9-C4/
