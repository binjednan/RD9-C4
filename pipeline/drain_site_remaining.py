# -*- coding: utf-8 -*-
"""Drawn DR-102 service portions rejected by the old ground-floor crop.

python3 pipeline/drain_site_remaining.py writes extraction data only.
build(M, els) regenerates DRG in memory.  Source route vertices are retained.
Vent air and the pressurised discharge remain distinct from gravity drainage.
No connector may be generated from these elements merely to close a gap.
"""
import collections
import json
import os
import re

import lib

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, 'data', 'drain_site_remaining.json')
ID_RE = re.compile(r'-DRG\d{4}$')
# Actual complete, unfilled pipe strokes, not the nearby MH / GT outlines,
# dimension lines, arrow heads or half-circle hatch strips.
ROUTES = [(7300, 'soil'), (7385, 'soil'), (7532, 'soil'),
          (5747, 'vent'), (7530, 'vent'),
          (7386, 'waste'), (7387, 'pressure'), (7388, 'waste'),
          (7546, 'waste'), (7614, 'waste')]
CHAMBERS = [(5900, 5899, 'GT'), (6429, 6428, 'GT'),
            (6581, 6580, 'GT'), (7110, 7109, 'GT'), (7269, 7268, 'PR')]
GRATINGS = [(5673, 'P.drain-G-M0020'), (5696, 'P.drain-G-M0021')]
TYPES = {
 'site_gt': {'n': 'مصيدة جالي GT خارج المبنى', 'cf': 'doc',
    'sp': [['الموضع والبصمة', 'الإطاران الخارجي والداخلي من DR-102'], ['المقاس', 'نحو60×60سم خارجًا و30×30سم داخلًا من الرسم']],
    'sr': ['MECH2 ص4 DR-102، مفتاح GT وص9 تفصيل المصيدة'], 'asm': ['عمق العرض90سم وتكوين الجدران رأسيًا افتراض؛ التفصيل النهائي معلق']},
 'site_pr': {'n': 'غرفة PR عند مخرج الخط المضغوط', 'cf': 'doc',
    'sp': [['الهوية', 'PR في المسقط وخط4 بوصات PRESSURIZED PIPE'], ['المقاس', 'الإطاران نحو60/30سم من المسقط']],
    'sr': ['MECH2 ص4 DR-102'], 'asm': ['التسمية الكاملة وتفصيل الغرفة معلقان؛ عمق العرض90سم افتراض']},
 'vent_drain_pipe': {'n': 'خط تهوية صرف إلى نطاق غرفة التفتيش', 'cf': 'doc',
    'sp': [['الوسط', 'هواء تهوية؛ مستقل عن تدفق مياه الصرف'], ['الموضع', 'M_DR_VP، دون نقل النهايات']],
    'sr': ['MECH2 ص4 DR-102'], 'asm': ['المنسوب3.30م والقطر100مم افتراضيان؛ وظيفة النهاية قربMH تحتاج تفصيلًا']},
 'pressure_drain_pipe': {'n': 'خط تصريف مضغوط إلى PR', 'cf': 'doc',
    'sp': [['الهوية', '4 بوصات PRESSURIZED PIPE'], ['الوسط', 'تصريف مضغوط؛ مستقل عن مسار الجاذبية']],
    'sr': ['MECH2 ص2 وص4'], 'asm': ['المنسوب−0.58م افتراض؛ الربط إلى مضخة البدروم غير ممثل دون مطابقة مصدرية']},
 'grating_channel': {'n': 'قناة تصريف بغطاء شبكي', 'cf': 'doc',
    'sp': [['الموضع', 'GRATING CHANNEL والإطار الكامل من المسقط']],
    'sr': ['MECH2 ص4 DR-102'], 'asm': ['عمق القناة15سم وسُمك العرض افتراض؛ المصب يثبت من رموز المصدر لا قرب المسارات']},
}


def _record(sh, di, kind, pi=0):
    d = sh.D[di]; pdf = [list(p) for p in d['polys'][pi]]
    xy = [list(sh.T(*p)) for p in pdf]
    return {'drawing_index': di, 'poly_index': pi, 'layer': d['layer'], 'kind': kind,
            'pdf_points': pdf, 'xy': xy, 'source_transform': dict(sh.reg),
            'source_graphic_colour_rgb': d.get('color'),
            'bbox_cm': [min(p[0] for p in xy), min(p[1] for p in xy),
                        max(p[0] for p in xy), max(p[1] for p in xy)]}


def extract():
    sh = lib.Sheet('MECH2', 4); routes = []; chambers = []; gratings = []
    for di, family in ROUTES:
        q = _record(sh, di, 'pipe')
        assert not sh.D[di].get('fill') and len(q['xy']) in (2, 3), (di, 'not a plain pipe stroke')
        assert 1900 < q['bbox_cm'][3] < 1970, (di, 'not rejected by old crop')
        expected = 'M_DR_SP' if family == 'soil' else 'M_DR_VP' if family == 'vent' else 'M_DR_WP'
        assert q['layer'] == expected, (di, q['layer'], expected)
        q.update(family=family, diameter_mm=100 if family in ('vent', 'pressure') else 110 if family=='soil' else 80,
                 omitted_by='all(vertices.y<=1900) in mep_bg.inside(G); whole drawn path was rejected',
                 no_connectors=True)
        routes.append(q)
    for outer, inner, mark in CHAMBERS:
        q = _record(sh, outer, 'chamber'); r = _record(sh, inner, 'chamber_inner')
        b = q['bbox_cm']; ib = r['bbox_cm']
        assert q['layer'] == r['layer'] == 'M_DR_SP'
        assert 58 < b[2]-b[0] < 62 and 58 < b[3]-b[1] < 62
        assert 29 < ib[2]-ib[0] < 31 and 29 < ib[3]-ib[1] < 31
        q.update(inner_drawing=inner, inner_pdf_points=r['pdf_points'], inner_xy=r['xy'], mark=mark,
                 family='pressure' if mark=='PR' else 'waste', depth_assumed_m=.9)
        chambers.append(q)
    for di, old in GRATINGS:
        q = _record(sh, di, 'grating'); q['old_false_pipe_id'] = old
        assert q['layer']=='M_DR_WP' and len(q['xy'])==5
        gratings.append(q)
    labels = []
    for i, t in enumerate(sh.TX):
        txt=t['s'].strip()
        if txt not in ('GT','PR') and 'GRATING CHANNEL' not in txt:continue
        r=t['bbox'];xy=sh.T((r[0]+r[2])/2,(r[1]+r[3])/2)
        if xy[0]>2400:continue  # table/legend is separate from plan instances
        labels.append({'text_index':i,'text':txt,'xy':list(xy),'layer':t['layer']})
    names=collections.Counter(t['text'] for t in labels if t['text'] in ('GT','PR'))
    assert names=={'GT':4,'PR':1},names
    return {'source_set':'MECH2','source_page':4,'sheet':'DR-102',
            'registration':dict(sh.reg),'routes':routes,'chambers':chambers,'gratings':gratings,
            'label_inventory':labels,'chamber_label_counts':dict(names),
            'counts':{'routes':10,'GT':4,'PR':1,'grating_channels':2},
            'old_crop':{'x0':-30,'y0':-100,'x1':3230,'y1':1900},
            'source_gap_correction':'DR-102 draws connections via GT/PR and direct SP to MH-01..03; the prior chain=0 statement wrongly attributed the extraction crop to absent drawing geometry.',
            'retained_existing':{'MH':['P.drain-G-ST0001','P.drain-G-ST0002','P.drain-G-ST0003'],
                                 'site_pipe_source':'MECH2:1; agrees with DR-102 within about0.4cm'}}


def build(M,els,verbose=False):
    els[:]=[e for e in els if not ID_RE.search(e['id'])]
    D=json.load(open(DATA,encoding='utf-8'));M.setdefault('types',{}).update(TYPES)
    source='MECH2 ص4 DR-102: محاور حقيقية إلىMH وأربعةGT ورمزPR وقناتانشبكيتان؛ الحذف القديم بحدy1900كان سبب سقوط المواضع المرسومة. VP والخطالمضغوط مستقلان ولا موصلات مشتقة منهما.'
    if source not in M['sp']:M['sp'].append(source)
    si=M['sp'].index(source);n=0;count=collections.Counter()
    def add(q,g,t,mark,assumed,medium):
        nonlocal n
        n+=1;count[t]+=1
        a={'sys':'drain_site_vent' if medium=='vent' else 'drain_site_pressure' if medium=='pressure' else 'drain_site',
           'no_connectors':True,'flow_medium':medium,'source_kind':'drawn_route' if q['kind']=='pipe' else 'drawn_symbol_outline',
           'source_page':'MECH2:4','source_drawing':q['drawing_index'],'source_poly_index':q['poly_index'],
           'source_layer':q['layer'],'source_pdf_points':q['pdf_points'],'source_transform':q['source_transform'],
           'source_xy':q['xy'],'assumed':assumed,
           'geometry_role':'source_route_display' if q['kind']=='pipe' else 'source_symbol_display',
           'material_status':'not_specified_in_reviewed_source',
           'finish_status':'not_specified_in_reviewed_source',
           'dimension_status':'nominal_diameter_from_4inch_label' if q['kind']=='pipe' and medium=='pressure' else 'display_assumption_unverified' if q['kind']=='pipe' else 'drawn_symbol_outline_only',
           'elevation_status':'display_assumption_unverified',
           'physical_geometry_status':'display_proxy_pending_dimensions_and_mounting',
           'source_graphic_colour_rgb':q.get('source_graphic_colour_rgb')}
        if q.get('inner_pdf_points'):
            a.update(source_inner_drawing=q['inner_drawing'],source_inner_pdf_points=q['inner_pdf_points'],source_inner_xy=q['inner_xy'])
        els.append({'id':f'P.drain-G-DRG{n:04d}','c':'P.drain','l':'G','g':g,'mark':mark,
                    't':t,'m':'p_vent' if medium=='vent' else 'p_soil' if medium=='soil' else 'p_waste','a':a,'s':[si]})
    for q in D['routes']:
        medium=q['family'];typ='vent_drain_pipe' if medium=='vent' else 'pressure_drain_pipe' if medium=='pressure' else 'pipe_'+medium
        z=3.30 if medium=='vent' else -.63 if medium=='soil' else -.58
        g=['t',[[round(x,4),round(y,4),z]for x,y in q['xy']],q['diameter_mm']/10]
        add(q,g,typ,q['layer'],f'محور{z:.2f}م افتراض تمثيلي؛ القطر{q["diameter_mm"]}مم '+('من وسم4بوصات للخطالمضغوط.' if medium=='pressure' else 'افتراضي لعدم وسم مستقل علىهذهالقطعة.')+' محاورالرسم محفوظة؛ لا إثبات منسوب مدفون أو صلة رأسية إلىB، ولا موصلقرب لتعويض الفراغات.',medium)
    for q in D['chambers']:
        g=['p',[[round(x,4),round(y,4)]for x,y in q['xy'][:-1]],-.70,.20,
           [[[round(x,4),round(y,4)]for x,y in q['inner_xy'][:-1]]]]
        add(q,g,'site_pr' if q['mark']=='PR' else 'site_gt',q['mark'],
            'الإطاران60/30سم من المسقط؛ غطاءعندFFL الموقع+0.20م الظاهر فيDR-102 وعمق90سم افتراض. جسمالجدرانمشتقمنالإطار،لا قاع/وصلاتمخترعة؛ تفاصيلالتنفيذوالإسنادبالتربةمعلقة.',q['family'])
    for q in D['gratings']:
        b=q['bbox_cm'];g=['r',*[round(v,4)for v in b],.20,.365]
        add(q,g,'grating_channel','GRATING CHANNEL',
            'بصمةالقناة كاملة منالمسقط؛ قاع+.20م وغطاء+.365م يفترضان عمق15سم أسفلتشطيبغرفالأرضي+.35م،وسمكعرض1.5سم. لايعنيالإطارأنبوبًاولايثبتموضعمخرجالقناة.', 'waste')
    M.setdefault('meta',{})['drain_site_remaining']={'counts':dict(count),'source':'MECH2:4','old_ymax_cm':1900,
       'new_source_routes':10,'derived_connectors_allowed':False,'vertical_datums_verified':False}
    if verbose:print('drawn ground drain crop recovery:',dict(count))
    return dict(count)


if __name__=='__main__':
    D=extract()
    with open(DATA,'w',encoding='utf-8')as f:json.dump(D,f,ensure_ascii=False,indent=2);f.write('\n')
    print('DR-102 missing source:',D['counts'])
