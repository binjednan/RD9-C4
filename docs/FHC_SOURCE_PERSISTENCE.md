# استمرار تصحيح E6 وFHC في تشغيل post لاحق

## النتيجة الجاهزة

هذه مراجعة/حزمة اقتراح فيwork فقط، وليست تشغيلpost أو كتابةmodel. sourcepacketFHC المجمّد لم يتغير ولم يُفحصPDF من جديد. `onepass-stage-continuity-proof.json` يثبت من مرجع33160: حذف12ورقةباب زائفة و11stub لها، وحفظ11stub أخرى إلىU الصحيحة كاملة، واستعادة11بعد غيابها فيfixture مرحلةCN. العدد33137 لهذه الحزمة وحدها؛ جميع العناصر غير المملوكة متطابقة كاملة. تغير طرف بمقدار1سم رفض قبل التعديل.

ملفات جاهزة: `fire_cabinet_post_adapter.py`، `fire_cabinet_preserved_display_links.json`، `post-hooks.proposed.patch`، `onepass-stage-continuity-proof.json`. عندالنشر يبقيadapterوالledger sibling فيpipeline، أو يحددالجذرمسارledger/data صراحة ويحدثSHAللمحول فقط. الـsourcepacketالأصلي لا يتغير.

## ترتيب الدمج

1. قبل حذفK فيpost، `capture_before_K_cleanup`:11objectguards كاملة من ledger الاستمرارية. هي وصلات عرض مشتقة قائمة؛ لا مرجع منافذ فعلي.
2. بعد دمجER، `electrical_room_source_corrections.apply`:6أجسام من sourceanchor/overallextent قبلnearest/support. يحرسg-before/after؛absoluteZ/material/portsFalse.
3. بعد دمجmep_bg مباشرة، `apply_generated_after_mep_merge`: المصدر يعيد24FHC دونq؛ الحارس يطابقكلحقلgenموجود تمامًا، ويحذف12leaf ويضع12sourcegraphicmetadata. ليس تجاهلًا لحقول مخالفة.11ghostK غائبة هنا لأنpostحذفK سابقًا. لا يُستدعىapply المجمّد الكامل في هذه المرحلة لأنه يتطلبq/11Kللمرجع المحفوظ.
4. بعد تجميعtypes النهائي، تحديثFC.TYPES كي لا يطغىMEPBG_TYPES القديم على وصفgraphic-only.
5. فيCN.build، حجز22اسمK محددًا:11مستعادة و11متقاعدة. الحجز يغيرالهويةالإجرائيةفقط؛ لايغيرالمسارات أوcontact أوالمنسوب. صياغةpatchالمرفقة يراجعهاالجذر، ولم ينفذCN هنا.
6. بعدCN وقبلreliability/registry/LC، `restore_after_connectors`:11fullobjectexact؛from/to ID وc/t/l/m/mark/grp/g مطابقون. لاcollision أوnearest أوredirect. `no_connectors=True` يبقى لمنع إنشاء وصلات أخرى إلىgraphicproxy. إذا تغيرطرف تُرفض الاستعادة بدل اختراعحل.
7. DD قبلCR/CC/INV يحتاج ميتاداتاE6/FHC/continuity؛graphicfootprint scope منفصل عن جسم/مادة/Z/ports. الـCC عندالبناء لايُرقّي12proxy إلىقبولجسم تنفيذي كامل.

## المراجع والتصادم المسحوب

`FHC-E6-persistency-review.json` فيwork يثبت أن `source_batch.remap_index_refs(...include_lifecycle=False)` اجتاز1163مرجعًا/179تغيرindex دون مرجع متقاعد عام، وأنfullhistoricalCL محفوظ بعدremap. `a/b` داخلhistoricalrecord و`before_index=16` أرقام مرجع قديم، وليستindexفيelsالجديدة؛walk الحالي لايحولهما داخلmeta. source_leaf_retirement_identity نصهويةتاريخية لاgeometryalias.

يبقىCL-8B0EAB32 القديم فيhistory فقط. بعدFHCapply وقبلنشرالدفعة يجب سحبه من `coordinationReview.issues` وتحديثcounts/reviewcases/clashGroups؛genericremap لا يزيلIDstrings تلقائيًا. مسار E المحدود يفعل ذلك فيcoordination/refresh_withdrawn_groups. لا تغيير لحالة مراجعةمستخدم أو سجلclash_log تاريخي علىأنهحل موقعي.

LC: لا يجوزremap لنتيجةfire القديمة بما فيها23هويةمتقاعدة. مسار E يزيلpower/fire منالpack، يعيدربط18نظامًا القديم بالـIDs، ثم يحللpower/fire مرة واحدة ويعيدpack معindicesالحالية. إعادةremap لنتيجتيهما الجديدتين مرةثانية خطأ. لا تعديلbaselineولاقبولports/flow.

## حدود الاستمرارية

الحارسمرحلي من توقيعmep_bg الحالي وبـsourcepool الموجود؛ لايدعيقبولfreshmake_modelمعsourcepoolمختلف. أيتغيرقيمة/s/metadataموجودة يرفض بدل تجاهلها. sourceafterbodymetadata بقيتphysicaldimensions/Z/material/mount/portsFalse. fixtureالمصدر هنامرحلةpost/CNفقط، لااختبارتوليدCNكامل أواعتمادكلpost.

## الموجة التالية دون تحقيق جديد

الأولوية الحاليةأبوابالشقق204المثبتة عندWater/الجذر:قوالبالمقاسالمثبت تنسخ معsourcepose لكلطابق؛ لا إعادةبحثمكرر. بعدها تختارحزمةfixturesمتكررة فقطعندمايتوفرbindingplan+detaildimension واضح؛لااعتمادcatalogأوالقديم. الخزائن WR القابلةللنسخ تبقىمعلقة لاختيارالارتفاع250منA1300مقابل240منA1301؛لااختياراعتباطي. تعارضاتCHW/roofالمثبتة والروابطغيرالمحددة تبقىسجلاتمصدر مستقلة،ولا تحركالمواقع لتغطيةنقصالمصدر. لم يبدأ أيبحثجديد هنا.
