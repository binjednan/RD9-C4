# حالة التسليم — 2026-10-09
الشجرة: جذر المشروع؛ العارض v2026.10.09-1719، الحجم 9,656,108 بايت؛ بُني post_model ثم العارض مرة واحدة في نهاية العمل.
النموذج: 34,655 عنصرًا، منها 125 بديلًا؛ لا نوع ينتهي بـ _graphic. لم تُنقل الأجهزة أو الأسلاك أو تتغير ارتفاعاتها أو سماحة 0.2 سم.
الحوامل: 168 حامل جهاز، منها 40 جديدة للحالات الـ148؛ المشابك: 2,203 في 794 مجموعة، صُغّر مقطعها إلى 1.5 × 1.5 سم مع حفظ المحاور والأطوال.
عدسة الأنظمة تورّث لون الجهاز أو السلك إلى حامله؛ عرض المواد يعطي الحوامل والمشابك رماديًا مطفأً، بلا إضافة وسم نظام إليها.
الأسلاك: 808 مشمولة، 774 مكتملة الدعم و34 غير مكتملة؛ لسلكي W0164 وW0165 تسعة مشابك وعشر محطات بلا مضيف لكل منهما. مساراتها وارتفاعاتها محفوظة.
HEIGHT_REVIEW.json خارج المستودع: 38 حالة ارتفاع لم تتغير؛ من 148 حالة بعيدة أو خارج البصمة أضيفت حوامل إلى 40 وبقيت 108 غير محسومة؛ 147 لها قراءة مصدر وحالة مشتقة بلا رمز مستقل.
FACP E.panel-G-0012: ELEC2 ص3، FA-101؛ حامل بطول 60.008 سم إلى S.wall-G-RS002، حد الجدار مثبت من ARCH1 ص5 A102؛ ارتفاع الجسم 0.78 إلى 1.38 م محفوظ، ووسم الخروج عن البصمة باقٍ.
الباقي: E.panel-G-0006 في ELEC2 ص3 يبعد 210.142 سم عن جدار المصدر؛ M.equip-R-S0225 في MECH1 ص6 AC-105 يبعد 207.896 سم؛ P.drain-G-K1209 مشتق قديم بلا رمز مستقل. لا أعد عدم إثبات المضيف دليلًا على خطأ المخطط.
window_surrounds.json: 117 مجموعة و2,853 معرّف جزء من A1500 وA1501 وA1502 وA800–A802؛ أُسندت 57 قطعة أرضية إلى أنواعها وأضيفت 20 قطعة CW-06 بالبدروم.
STR-14: 79 عمودًا محفوظًا، واستُبدلت ثماني مساحات خاطئة بثلاثة بدائل جدران ذات فراغاتها؛ لم تُحذف أشكال المصادر الأخرى.
## الواجهة
التصحيحات السابقة: 306 ألواح زجاج بسماكة 2.4 سم، 146 رأس جدار أو كسوة وفق الارتفاع المكتوب، مادة 14 قطعة GRC إلى بيج أكريليك دون افتراض RAL.
A202: المقياس المستقل أفقيًا 3.527868106 ورأسيًا 3.52680514 سم لكل وحدة PDF؛ فرق امتداد 4570 سم عن التسجيل المحفوظ 2266.778974 سم، أكبر من حد 1 سم.
A203: المقياس المستقل أفقيًا 3.527541178 ورأسيًا 3.526804055؛ فرق الامتداد عن المحفوظ 2059.282320 سم. لم يُعدّل التسجيل ولم تُستكمل مطابقة الفتحات بعد فشل شرط التطابق.
متبقٍ: مواضع وأعداد الفتحات؛ مقطع GRC واتصاله؛ فصل جسم الواجهة المركب 30 سم عن قشرة البورسلان 2 سم؛ تفاصيل الدروة والإطارات والقيم اللونية غير المكتوبة.
## البوابات والأنظمة
بوابات اللقطة السابقة: 28 اجتازت، والتغطية جرد فقط؛ لم تُعد كلها على v1719. المواضع سابقًا: 7,877 مفحوصًا و442 غير مغطى، moved = 0 في فحص النقل السابق.
دورة الحياة الموروثة، الموصول / النهايات ثم اليتيم: الكهرباء 785 / 2598 و1115؛ الهاتف والألياف 0 / 232 و55؛ الصواعق 0 / 5 و59؛ التأريض 0 / 6 و18.
الري 0 / 1 و4؛ الأمطار 4 / 8 و24؛ الصرف 139 / 257 و752؛ المياه المبردة 85 / 107 و194. هذه أرقام محفوظة لا إثبات جديد لاكتمال الأنظمة.
غير مرسوم في المصدر: وصل أسهم الدوائر بلوحات التوزيع، وMDB باللوحات الفرعية، وONU بمخارج RJ45؛ لم تُخترع وصلات. فجوتا الري 20.5 سم والأمطار 438.9 سم لم تُسدّا.
## العرض والأداء
لوحة بناء المشروع تعمل بخمسة أقسام و20 نظامًا والأدوار والوحدات، ترتيب وحفظ محلي، سرعة وتوقف وتخطٍ وإعادة واستعادة ونسخ كتوجيه.
قياس 1400 × 900 و390 × 844 بلا أخطاء: أول إطار 5344 / 5277 مللي ثانية؛ ذاكرة JavaScript أثناء العرض 458 / 468 م.ب؛ الحركة 52 / 55.6 إطارًا في الثانية.
RSS لعملية العرض 981 / 1133 م.ب: حد 800 م.ب لم يجتز؛ الذاكرة أول بند أداء قادم. قياس Chrome على Mac بحجم هاتف ليس اختبار آيفون فعليًا.
فحص العرض: 962 حاملًا أو مجموعة مشابك تطابق لون الأصل؛ 4406 أوجه طرفية بلا خطأ مقطع؛ 34,530 عنصرًا أساسيًا ظاهرًا، والبدائل مخفية؛ اختبارات لوحة البناء اجتازت.
المتبقي بالترتيب: ذاكرة العرض وآيفون فعلي، الحالات الـ108 وقرارات الارتفاع، تسجيل الواجهات وفتحاتها، ثم استكمال الشبكات بما تثبته المصادر فقط.
النشر: استُبعدت الملفات أدناه لوجود مسارات محلية جديدة أو تجاوز 50 م.ب؛ استُبدل مرجع PDF محلي واحد في بيانات model.json المنشورة باسم الملف فقط. AGENT_PROMPT.md غير موجود في شجرة العمل فحُفظ ملف المستودع القائم.
ملفات مستبعدة: pipeline/raft_model_acceptance.py؛ pipeline/data/hvac_return_route_gap.json؛ pipeline/data/hvac_damper_source.json؛ pipeline/data/water_valve_source.json؛ pipeline/data/core_stairs_source_review.json؛ pipeline/data/fire_cabinet_source.json؛ pipeline/data/restore_hvac_outlets_source.json؛ pipeline/data/electrical_room_source_corrections.json؛ pipeline/data/roof_finish_matching.json؛ pipeline/data/window_source_xy.json؛ pipeline/data/core_stairs_source_surfaces.json؛ pipeline/data/boundary_wall_matching.json؛ pipeline/data/boundary_source_remaining.json؛ pipeline/data/drawn_position_audit.json؛ pipeline/data/top_roof_shaft_openings_source.json؛ pipeline/data/raft_source_restore.json؛ pipeline/data/d16_host_source_correction.json؛ pipeline/data/column_shape_matching.json؛ pipeline/data/water_heater_capacity_source.json؛ pipeline/data/top_roof_opening_source_comparison.json؛ pipeline/data/stair_concrete_completion.json؛ pipeline/data/door_completion.json؛ pipeline/data/source_stair_lightning_alternatives.json؛ pipeline/data/d16_source_remaining.json؛ pipeline/data/stair01_roof_source_correction.json؛ pipeline/data/ceiling_shape_match.json؛ pipeline/data/equipment_completion.json؛ pipeline/data/coordination_source_cases.json؛ pipeline/data/stair_completion.json؛ pipeline/data/structural_source_restore.json؛ pipeline/data/door_source_templates.json؛ pipeline/data/fire_source_corrections.json؛ docs/CODEX_WORKORDER_01.md؛ docs/CONTINUATION_2026-10-09.md؛ docs/DESIGN_WATER_VALVE_SOURCE.md؛ docs/CODEX_PROMPT_SMOKE_MANAGEMENT.md؛ pipeline/data/component_coverage.json.
لا تُنشر ملفات العملاء أو الصور أو work أو outputs أو handoff أو الذاكرة المؤقتة؛ HEIGHT_REVIEW.json يبقى خارج المستودع، وsrc/photos.json محذوف.
