"""Append source-backed component corrections without rerunning unrelated audits."""
import copy

def append_to(M, issues):
    active={e['id']:e for e in M['els']}
    rows=[]
    def add(id,title,status,source,note,elements,before=None,after=None,level=None):
        rows.append(dict(id=id,title=title,status=status,source=source,note=note,
                         level=level,xy_cm=None,z_m=None,elements=elements,
                         before=before,after=after))
    if M.get('meta',{}).get('electrical_room_source_corrections'):
        import electrical_room_source_corrections as ER
        D=ER.data();ids=list(D['records'])
        for eid,r in D['records'].items():
            assert active[eid]['g']==r['after_g'], 'Electrical source correction is not saved: '+eid
        add('DP-ELECTRICAL-ROOM-SOURCE-EXTENTS','تصحيح أبعاد ومواضع ستة أجهزة في الغرفة الكهربائية','corrected',
            'ELEC1 ص10 EP-101 / ص17 EP-108',
            'استبدلت المقاسات التقريبية بالمقاسات المكتوبة، وأعيد مركز كل جهاز إلى رمزه الأصلي. '
            'المحول400×170سم، MDB320×80، عدادLV60×80، RTU100×30، البطاريات120×50، و48V82×60. '
            'الأجسام أغلفة أبعاد كلية؛ وجوهها وتفاصيلها الداخلية والمادة والتثبيت والمنافذ غير معتمدة. '
            'منسوب البدء محفوظ؛ ارتفاعات الأغلفة تتفق مع الجدول، ولا تثبت منسوب التركيب المطلق.',ids,
            {eid:r['before_e']['g'] for eid,r in D['records'].items()},
            {eid:r['after_g'] for eid,r in D['records'].items()},'G')
        add('DP-ELECTRICAL-ROOM-BODY-SCOPE','تفاصيل أجسام الأجهزة الكهربائية ومناسيب تركيبها تحتاج مصدرًا','source_gap',
            'ELEC1 EP-101 / EP-108',
            'ثبتت مرساة المسقط والأبعاد الكلية المكتوبة لكل جهاز. مادة الغلاف ووجه التشغيل والتثبيت '
            'والمنسوب المطلق ونقاط توصيل الكابلات غير مثبتة بهذه الأبعاد؛ لا تعتمد الوصلات من التلامس وحده.',ids,
            None,{'source_anchor_and_overall_dimensions':True,'whole_physical_body_accepted':False},'G')
    if M.get('meta',{}).get('fire_cabinet_source'):
        import fire_cabinet_source as FC
        D=FC.data();ids=list(D['records']);retired=set(D['exact_retired_ids'])
        assert not retired.intersection(active), 'False cabinet identity/connector remains'
        for eid,r in D['records'].items():
            assert active[eid]['g']==r['before_e']['g'], 'Retained recess geometry changed'
        add('DP-FHC-FALSE-LEAF-RETIREMENT','إزالة تكرار صناديق الإطفاء الناتج عن ورقة الباب المرسومة','corrected',
            'MECH2 ص10–13 طبقةFHC / ص16 FF-106',
            'المسقط يرسم تجويفًا وورقة باب مفتوحة لكل موضع. كان الاستخراج يحولهما إلى صندوقين. '
            'حذفت12 ورقة باب ممثلة خطأ كصندوق مستقل و11 وصلة مشتقة إليها. بقيت12 هوية في مواضع '
            'التجاويف المرسومة. سجل CL-8B0EAB32 سحب من النتائج النشطة مع حفظه تاريخيًا لأن أحد طرفيه جسم زائف. '
            'لم تنقل الوصلات إلى جسم بديل ولم يستنتج منفذ جديد.',ids,
            {'cabinet_proxy_count':24,'retired_ids':sorted(retired),'derived_ghost_stubs':11},
            {'source_recess_identities':12,'retired_total':23,'connection_redirection':False,
             'withdrawn_clash':'CL-8B0EAB32','physical_cabinet_acceptance':False})
        add('DP-FHC-PHYSICAL-BODY-SCOPE','استكمال أجسام صناديق الإطفاء وتخصيص تفصيلها','source_gap',
            'MECH2 FF-100–103 / FF-106 FHC1 وFHC2',
            'حد العرض الحالي نحو88×32سم يخص تجويفًا معماريًا، وليس حد تصنيع الصندوق. التفصيل يحدد '
            '750مم عرضًا و300مم عمقًا؛1500/1550مم أبعاد رأسية. تعيين النوع والحد التنفيذي والمنسوب '
            'والتثبيت والمادة والمنافذ لكل موضع يحتاج ربطًا مستقلًا. هذا نقص دليل جسم، لا تعارض مؤكد بين عرض150سم وتجويف88سم.',ids,
            None,{'graphic_bbox_verified':True,'whole_body_and_absolute_Z_verified':False})
    owned={r['id']for r in rows}
    return [r for r in issues if r['id']not in owned]+rows

def apply(M):
    M['drawingIssues']=append_to(M,M.get('drawingIssues',[]))
    return M['drawingIssues']
