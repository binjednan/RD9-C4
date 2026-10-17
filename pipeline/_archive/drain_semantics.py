# -*- coding: utf-8 -*-
"""Replace specifically proved non-pipe DR primitives after the MEP merge.

Run this file to save source evidence only. build(M, els) works in memory.
The removal ledger is limited to named model IDs whose original paths coincide
with independently read frames, leaders, symbol hatching or pump glyphs. A real
route touching these glyphs is retained. No structural opening is invented.
"""
import collections
import copy
import json
import os
import re

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

import lib
from support import poly_of, zr

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data', 'drain_semantic_review.json')
ID_RE = re.compile(r'-DSM\d{4}$')
TYPES = {
    'sump_pit': {'n': 'حفرة تجميع صرف في البدروم', 'cf': 'doc',
        'sp': [['المسقط', 'إطار خارجي نحو120×120سم وداخلي106×106سم'],
               ['اختلاف المقاس', 'نص DR-100 يذكر1.5×1.5×1.5م؛ لم تكبّر البصمة إلى النص']],
        'sr': ['MECH2 ص2 DR-100، رسوم5286/5287'],
        'asm': ['العمق1.5م من النص؛ المنسوب مشتق من التشطيب المحلي؛ الفتحة الإنشائية غير مثبتة']},
    'sump_pump_symbol': {'n': 'مضخة غاطسة داخل حفرة التجميع', 'cf': 'doc',
        'sp': [['العدد', 'رمزان دائريان للمضخات في المسقط'], ['الحجم', 'قطر الرمز نحو41سم؛ ليس مقاس جسم معتمدًا']],
        'sr': ['MECH2 ص2 DR-100، رسوم5305/5308 ووسم Submersible pump'],
        'asm': ['جسم العرض مستخرج من حجم الرمز وارتفاع40سم افتراض؛ قدرة المضخة والربط الرأسي غير مرسومين']},
    'drain_sdt': {'n': 'مصيدة ترسيب SDT', 'cf': 'doc',
        'sp': [['الموضع', 'إطار رمز SDT من المسقط'], ['حد التمثيل', 'بصمة رمز الخدمة؛ ليست اعتماد مقاس جهاز']],
        'sr': ['MECH2 ص2 DR-100'], 'asm': ['عمق الجسم60سم افتراض؛ بيانات الجهاز غير محددة']},
    'drain_oil_separator': {'n': 'فاصل زيت/وقود', 'cf': 'doc',
        'sp': [['الموضع', 'رمز OIL مرتبط بوسم OIL / FUEL SEPERATOR']],
        'sr': ['MECH2 ص2 DR-100'], 'asm': ['بصمة إطار الرمز وعمق60سم للعرض؛ المقاس التنفيذي غير معتمد']},
}


def record(sh, di, kind, pi=0):
    d = sh.D[di]
    pdf = [list(p) for p in d['polys'][pi]]
    xy = [list(sh.T(*p)) for p in pdf]
    return {'drawing_index': di, 'poly_index': pi, 'layer': d['layer'],
            'pdf_points': pdf, 'xy': xy, 'source_transform': dict(sh.reg), 'kind': kind,
            'bbox_cm': [min(p[0] for p in xy), min(p[1] for p in xy),
                        max(p[0] for p in xy), max(p[1] for p in xy)],
            'source_graphic_colour_rgb':d.get('color')}


def extract():
    sheets = {p: lib.Sheet('MECH2', p) for p in (2, 4)}
    original = {}
    count = collections.Counter()
    for e in json.load(open(os.path.join(HERE, 'data', 'mep_bg.json'), encoding='utf-8'))['els']:
        count[e['c'], e['l']] += 1
        original[f"{e['c']}-{e['l']}-M{count[e['c'], e['l']]:04d}"] = e
    # Named source meanings, rather than a generic short-line/closed-loop test.
    removal = [(2, 10, list(range(5506, 5515)), 'SDT symbol octagon'),
               (2, 11, list(range(5506, 5515)), 'SDT symbol octagon'),
               (2, 14, [5569], 'leader from OIL symbol to its text'),
               (2, 27, [5286], 'outer sump-pit frame'),
               (2, 28, [5287], 'inner sump-pit frame'),
               (2, 30, [5329], 'basement grating channel outline'),
               (2, 32, [5356], 'frame containing complete Sump Pit callout text'),
               (2, 45, [5515], 'SDT symbol frame'),
               (2, 46, [5525], 'OIL symbol frame'),
               (2, 50, [5567], 'leader from sump pit to its callout'),
               (2, 55, [5290], 'sump pit hatch'), (2, 56, [5291], 'sump pit hatch'),
               (2, 57, [5293], 'sump pit hatch'), (2, 58, [5296], 'sump pit hatch'),
               (2, 59, [5302], 'sump pit hatch'), (2, 60, [5303], 'sump pit hatch'),
               (2, 61, [5295, 5305], 'sump pit hatch merged with pump-circle glyph'),
               (2, 62, [5306, 5307], 'pump triangle glyph'),
               (2, 63, [5308], 'pump-circle glyph'),
               (2, 64, [5309, 5310], 'pump triangle glyph'),
               (4, 20, [5673], 'ground grating channel outline'),
               (4, 21, [5696], 'ground grating channel outline')]
    for old, raw in [(7,7465),(8,7466),(9,7467),(10,7468),(17,8046),(18,8047),(19,8048)]:
        removal.append((4, old, [raw], 'hatch strip inside circular drain symbol'))
    removed = []
    for page, ordinal, indices, meaning in removal:
        level = 'B' if page == 2 else 'G'; identity = f'P.drain-{level}-M{ordinal:04d}'
        old = original[identity];sh = sheets[page]
        sources = [record(sh, i, meaning, pi) for i in indices for pi in range(len(sh.D[i]['polys']))]
        actual = unary_union([LineString(q['xy']) for q in sources])
        path = LineString([p[:2] for p in old['g'][1]])
        # Old simplification is measured explicitly. This checks identity before
        # removal; it does not relax the 0.2cm gate for the replacement geometry.
        error = max(path.interpolate(k/128, normalized=True).distance(actual) for k in range(129))
        # SDT has deliberate dashed gaps of about6cm. The old extractor joined
        # those gaps; this ID-specific allowance is for the removal evidence,
        # never for a rebuilt part's exact-position gate.
        removal_limit = 3.1 if meaning == 'SDT symbol octagon' else .9 if ordinal == 61 and page == 2 else .85
        assert old['t'] == 'pipe_waste' and error < removal_limit, (identity, indices, error)
        removed.append({'id': identity, 'source_page': page, 'meaning': meaning,
                        'original_g': old['g'], 'sources': sources,
                        'old_simplified_path_deviation_cm': error,
                        'old_path_identity_limit_cm':removal_limit})
    bodies = [record(sheets[2], 5286, 'sump_pit'),
              record(sheets[2], 5305, 'sump_pump_symbol'),
              record(sheets[2], 5308, 'sump_pump_symbol'),
              record(sheets[2], 5515, 'drain_sdt'),
              record(sheets[2], 5525, 'drain_oil_separator'),
              record(sheets[2], 5329, 'grating_channel')]
    inner = record(sheets[2], 5287, 'sump_inner')
    bodies[0].update(inner_drawing=5287, inner_pdf_points=inner['pdf_points'], inner_xy=inner['xy'])
    pressure = record(sheets[4], 7270, 'pressure_route')
    pressure.update(id='P.drain-G-M0023', diameter_mm=100)
    manifold = record(sheets[2], 5311, 'pump_common_route')
    manifold.update(id='P.drain-B-M0029', diameter_mm=None)
    texts = []
    for n,t in enumerate(sheets[2].TX):
        if 'Sump Pit' in t['s'] or 'OIL / FUEL' in t['s'] or t['s'] in ('SDT','OIL'):
            texts.append({'text_index': n, 'text': t['s'], 'layer':t['layer'], 'pdf_bbox':t['bbox']})
    return {'source_set':'MECH2', 'removed_false_pipes':removed, 'bodies':bodies,
            'pressure_routes':[pressure,manifold], 'texts':texts,
            'counts':{'non_pipe_ids':len(removed),'new_bodies':len(bodies)},
            'source_conflicts':[
                {'kind':'dimension', 'source':'MECH2:2', 'xy_cm':[1418.12698,1544.44088],
                 'description_ar':'نص حفرة التجميع1.5×1.5م يعارض إطار المسقط119.73×120.15سم؛ البصمة المرئية محفوظة دون تكبير.'},
                {'kind':'elevation', 'source':'MECH2:2 / ARCH1:4',
                 'description_ar':'DR-100 يكتب−3.30م لغرفة التجميع، وتشطيب ARCH المستخدم في المجسم−3.50م؛ فرق20سم محفوظ كتعارض مصدر.'},
                {'kind':'structural_opening', 'source':'MECH2:2 / STR basement',
                 'description_ar':'حفرة التجميع مرسومة في الميكانيكا؛ فتحتها في بلاطة S لم تثبت استقلالًا. لا قص إنشائي ولا اعتماد دعم تم تنفيذه.'}],
            'retained_real_routes':['P.drain-B-M0001','P.drain-B-M0012','P.drain-B-M0029'],
            'uncertain_text_only_ft':{'page':6,'xy_cm':[2217.5,1164.8],
                 'ids':['P.drain-2-0657','P.drain-3-0980','P.drain-4-1303','P.drain-5-1626'],
                 'description_ar':'FT نص حقيقي داخل electrical shaft؛ لا دائرة أو مسار M_DR ضمن50سم. الجسم القديم عند النص غير مثبت؛ يحتاج رمز/تفصيل ولا ينقل إلى أقرب ماسورة.'}}


def build(M, els):
    D = json.load(open(DATA, encoding='utf-8'))
    els[:] = [e for e in els if not ID_RE.search(e['id'])]
    gone = {q['id']: q for q in D['removed_false_pipes']}
    histories = M.setdefault('meta', {}).setdefault('drawing_corrections', {})
    for e in els:
        if e['id'] not in gone:continue
        q = gone[e['id']]
        if e['g'] != q['original_g']:
            raise ValueError('Non-pipe removal source identity changed: '+e['id'])
        histories.setdefault(e['id'], {'element':e['id'], 'old_geometry':copy.deepcopy(e['g']),
            'source':f"MECH2 ص{q['source_page']} DR مسار خام موثق في drain_semantic_review.json",
            'note':q['meaning'], 'source_primitives':copy.deepcopy(q['sources']),
            'new_geometry':None, 'semantic_correction':'رمز/حد جسم/تعليق، وليس أنبوبًا'})
    els[:] = [e for e in els if e['id'] not in gone]
    M.setdefault('types', {}).update(copy.deepcopy(TYPES))
    M.setdefault('mats',{}).setdefault('p_sump_pump',{'name':'رمز جسم مضخة غاطسة — مادة العرض افتراض','color':'#637482','code':'DR-100'})
    source='MECH2 ص2 DR-100: حفرة تجميع ومضختان وSDT وفاصل زيت وقناة شبكية من الرموز الخام؛ حدود الرموز والتهشير والـleaders ليست أنابيب.'
    if source not in M['sp']:M['sp'].append(source)
    si=M['sp'].index(source)
    def floor(x,y):
        candidates=[]
        for e in els:
            if e['c']!='A.floor' or e['l']!='B' or (e.get('a')or{}).get('kind')=='طبقة تسوية تحت التشطيب':continue
            p=poly_of(e['g'])
            if p is not None and p.covers(Point(x,y)):candidates.append((zr(e['g'])[1],e['id']))
        if not candidates:raise ValueError(f'No local floor under drawn sump component: {x},{y}')
        return max(candidates)
    for n,q in enumerate(D['bodies'],1):
        b=q['bbox_cm'];x,y=(b[0]+b[2])/2,(b[1]+b[3])/2;ffl,host=floor(x,y)
        kind=q['kind'];a={'sys':'drain_semantics','no_connectors':True,'source_page':'MECH2:2',
            'source_drawing':q['drawing_index'],'source_poly_index':q['poly_index'],
            'source_layer':q['layer'],'source_pdf_points':q['pdf_points'],
            'source_transform':q['source_transform'],'source_xy':q['xy'],
            'source_kind':'drawn_service_symbol','floor_host':host,'ffl_derived_m':ffl}
        a.update(geometry_role='source_symbol_display',material_status='not_specified_in_reviewed_source',
            finish_status='not_specified_in_reviewed_source',
            dimension_status='source_outline_conflicts_text'if kind=='sump_pit'else 'not_specified_in_reviewed_source',
            elevation_status='derived_from_local_finish_and_assumed_depth',
            physical_geometry_status='display_proxy_pending_dimensions_and_mounting',
            source_graphic_colour_rgb=q.get('source_graphic_colour_rgb'))
        if kind=='sump_pit':
            g=['p',[[round(x,4),round(y,4)]for x,y in q['xy'][:-1]],round(ffl-1.5,3),ffl,
               [[[round(x,4),round(y,4)]for x,y in q['inner_xy'][:-1]]]]
            a.update(source_inner_drawing=q['inner_drawing'],source_inner_pdf_points=q['inner_pdf_points'],source_inner_xy=q['inner_xy'],
                assumed='بصمة الإطارين نحو120/106سم من المسقط؛ نص1.5×1.5م متعارض معها. عمق1.5م من النص، وغطاء عند التشطيب المحلي−3.50م مقابل−3.30م في DR. الجدران مشتقة رأسيًا ولا يوجد إثبات فتحة S أو قاع مصبوب.')
        elif kind=='sump_pump_symbol':
            g=['cyl',round(x,4),round(y,4),round((b[2]-b[0])/2,4),round(ffl-1.45,3),round(ffl-1.05,3)]
            a['assumed']='المركز من الدائرة الفعلية؛ قطر41سم هو حجم رمز المسقط لا جسم جهاز معتمد. ارتفاع40سم وقاع أعلى قاع الحفرة5سم افتراض عرض؛ لا يوصل إلى مخطط رأسي أو خط قريب تلقائيًا.'
        elif kind=='grating_channel':
            g=['r',*[round(v,4)for v in b],round(ffl-.15,3),round(ffl+.015,3)]
            a['assumed']='بصمة قناة الشبك من الإطار الخام؛ عمق15سم وسمك غطاء1.5سم افتراض عند سطح التشطيب المحلي. لا يثبت رمز FT وحده تفصيل مخرج القناة.'
        else:
            g=['r',*[round(v,4)for v in b],round(ffl-.6,3),round(ffl+.015,3)]
            a['assumed']='الجسم يوضح موضع وبصمة إطار رمز الخدمة60سم؛ ليس مقاسًا تنفيذيًا. عمق60سم وغطاء1.5سم والمنسوب من التشطيب المحلي افتراض؛ بيانات الجهاز والفتحة الإنشائية غير مثبتة.'
        cat='P.pump' if kind=='sump_pump_symbol' else 'P.drain'
        els.append({'id':f'{cat}-B-DSM{n:04d}','c':cat,'l':'B','g':g,'t':kind,
            'mark':{'sump_pit':'SUMP PIT','sump_pump_symbol':'SUBMERSIBLE PUMP','drain_sdt':'SDT',
                    'drain_oil_separator':'OIL / FUEL SEPARATOR','grating_channel':'GRATING CHANNEL'}[kind],
            'm':'p_sump_pump' if kind=='sump_pump_symbol' else 'p_site','a':a,'s':[si]})
    for q in D['pressure_routes']:
        e=next((e for e in els if e['id']==q['id']),None)
        if e is None:continue
        before=copy.deepcopy(e['g']);z=e['g'][1][0][2]
        e['t']='pressure_drain_pipe'
        e['g']=['t',[[round(x,4),round(y,4),z]for x,y in q['xy']],10 if q['diameter_mm'] else before[2]]
        e.setdefault('a',{}).update(sys='drain_pressure_legacy',no_connectors=True,flow_medium='pressure',
            source_page='MECH2:4' if e['l']=='G' else 'MECH2:2',source_drawing=q['drawing_index'],
            source_poly_index=q['poly_index'],source_layer=q['layer'],source_pdf_points=q['pdf_points'],
            source_transform=q['source_transform'],source_xy=q['xy'],source_kind='drawn_pressure_route',
            geometry_role='source_route_display',material_status='not_specified_in_reviewed_source',
            finish_status='not_specified_in_reviewed_source',
            dimension_status='nominal_diameter_from_4inch_label' if q['diameter_mm'] else 'retained_legacy_value_unverified',
            elevation_status='retained_legacy_value_unverified',physical_geometry_status='pending_source_elevation_and_diameter',
            source_graphic_colour_rgb=q.get('source_graphic_colour_rgb'),
            assumed='محور Z محفوظ من افتراض الاستخراج؛ تحويل النوع إلى تصريف مضغوط لا يثبت المنسوب أو الصلة الرأسية. قطر4بوصات100مم في G من الوسم؛ قطرmanifold البدروم80مم افتراض قديم بلا وسم مستقل.')
        histories.setdefault(e['id'],{'element':e['id'],'old_geometry':before,'source':'MECH2 DR-100/102، التصريف المضغوط من حفرة المضخات إلى PR',
            'new_geometry':copy.deepcopy(e['g']),'note':'حفظ رؤوس المصدر الخام وتصنيف الضغط منفصلًا عن الجاذبية؛ لا موصلات قرب.'})
    M['meta']['drain_semantics']={'removed_false_pipe_ids':sorted(gone),'added_bodies':len(D['bodies']),
        'pressure_reclassified_ids':[q['id']for q in D['pressure_routes']],
        'source_conflicts':copy.deepcopy(D['source_conflicts']),
        'unresolved_ft':copy.deepcopy(D['uncertain_text_only_ft'])}
    return {'removed_false_pipes':len(gone),'source_bodies':len(D['bodies']),'pressure_routes':len(D['pressure_routes'])}


if __name__=='__main__':
    D=extract()
    with open(DATA,'w',encoding='utf-8')as f:json.dump(D,f,ensure_ascii=False,indent=2);f.write('\n')
    print('Drain source semantics:',D['counts'])
