# المخطط والعلاقات (الخطوة 3 من الترحيل التدريجي)

لم يتغيّر أي عنصر في `src/model.json`؛ الطبقة الجديدة فوقه فقط.

| الملف | الدور |
|---|---|
| `pipeline/data/schema/element.schema.json` | عقد العنصر (مفاتيح مطلوبة، أنواع، أحجام هندسة كل نوع) + الاستثناءات المثبَّتة |
| `pipeline/data/schema/attribute_registry.json` | سجل مفاتيح `a` الـ362 (أنواع القيم، العدد، الدور بقاعدة آلية) |
| `pipeline/data/schema/relation_registry.json` | قاموس العلاقات: كل حقل قديم ← نوع علاقة واحد (hosted_by / supported_by / connects / serves / sleeve_of / extends / level_reference / member_of_source_group) |
| `pipeline/relations.py` | يشتق `pipeline/data/relations.json` (11,504 علاقة) دون تعديل العناصر |
| `tools/check_schema.py` | البوابة (تفشل مغلقة): E1–E4 للعنصر، R1–R5 للعلاقات |

التشغيل: `python3 pipeline/relations.py && python3 tools/check_schema.py`.
مفتاح جديد في `a` أو حقل يحمل معرّفات عناصر يفشل البوابة حتى يُسجَّل عمدًا (`--init-registry` لإعادة التوليد بعد قرار).

## مثبَّت لا مخفي (يحتاج قرارك)
- الفئة `A.shaft` غير معرَّفة في `layers`، والخامات `fin_CSP-2/3/4` غير معرَّفة في `mats`.
- رابطان في `source_group_ids` يشيران لمخرجين غير موجودين: `M.outlet-1-0150` و`M.outlet-1-0154`.

## ما لم يُغطَّ بعد
`a.sys` (تجمّع الشبكة) و`a.room` تبقى حقولًا نصية لا علاقات؛ والمخطط يثبّت الموجود ولا يُثبت صحة المعنى. منافذ الأنابيب (IfcPort) غير مولَّدة.


## ما أُضيف بأمر العمل 3ب+4 (2026-10-17)
- `pipeline/ports.py` ← `pipeline/data/ports.json`؛ `pipeline/generated_layer.py` و`pipeline/kits.py` و`pipeline/data/library/*` و`pipeline/data/decisions/*` و`pipeline/pipe_dimensions.py` و`pipeline/window_sections.py` و`pipeline/drain_assign.py`.
- قواعد جديدة في `tools/check_schema.py`: P1–P4 (المنافذ)، S1–S6 (العينات/التجميعات)، T1–T2 (الأنظمة/الفراغات)، B1 (أنواع المصادر).
- التقرير الكامل: `docs/REPORT_3B_4_2026-10-17.md`.
