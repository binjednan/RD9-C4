# -*- coding: utf-8 -*-
"""Recover six DR-100 device positions from actual PDF symbols.

Call apply(M, els) after local floor-level corrections and before support/guesses.
The old extraction placed bodies at FT/CO text, then guesses moved them to walls.
FT positions are outer-circle centres; CO positions are the perpendicular cap
intersections. PDF drawing indices are stable provenance, checked by the XY gate.
CO elevations retain the original extraction assumption. FT grates follow the
actual local basement floor; that height is explicitly derived, never exact XY.
This module does not save the model, change support tolerances, or add connectors.
"""
import copy
import json
import os

from shapely.geometry import Point
import lib
from support import poly_of, zr

HERE=os.path.dirname(__file__)
# (source drawing, original symbol anchor; drawing polys are read afresh)
SOURCE={
 'P.drain-B-M0071':(5453,'circle_centre'),
 'P.drain-B-M0072':(5317,'circle_centre'),
 'P.drain-B-M0073':(5332,'cap_intersection'),
 'P.drain-B-M0074':(5334,'cap_intersection'),
 'P.drain-B-M0075':(5504,'cap_intersection'),
 'P.drain-B-M0076':(5642,'cap_intersection'),
}

def apply(M,els):
    sh=lib.Sheet('MECH2',2)
    original=[e for e in json.load(open(os.path.join(HERE,'data','mep_bg.json'),encoding='utf-8'))['els']
              if e['c']=='P.drain' and e['l']=='B']
    hist=M.setdefault('meta',{}).setdefault('drawing_corrections',{})
    changes=[]
    for e in els:
        if e['id'] not in SOURCE:continue
        di,anchor=SOURCE[e['id']];d=sh.D[di]
        assert d['layer']=='M_DR_WP',(e['id'],di,d['layer'])
        baseline=original[int(e['id'][-4:])-1]
        assert baseline['t']==e['t'],(e['id'],baseline['t'],e['t'])
        if anchor=='circle_centre':
            r=d['rect'];pdf=[(r[0]+r[2])/2,(r[1]+r[3])/2]
            assert len(d['polys'][0])==41,(e['id'],'outer FT circle changed')
        else:
            p=d['polys'][0]
            assert len(p)==4 and p[1]==p[3],(e['id'],'CO cap source changed')
            pdf=list(p[1])
        xy=[round(v,1) for v in sh.T(*pdf)];old=copy.deepcopy(e['g'])
        g=copy.deepcopy(baseline['g']);g[1:3]=xy
        assumed='منسوب CO −3.72..−3.69م محفوظ من افتراض الاستخراج الأصلي؛ المخطط يحدد رمز النهاية ولا يثبت ارتفاعه، بانتظار تفصيل التركيب.'
        host=None
        if anchor=='circle_centre':
            point=Point(*xy)
            floors=[(zr(f['g'])[1],f['id']) for f in els if f['c']=='A.floor' and f['l']=='B'
                    and (f.get('a') or {}).get('kind')!='طبقة تسوية تحت التشطيب'
                    and poly_of(f['g']) is not None and poly_of(f['g']).covers(point)]
            assert floors,(e['id'],'no actual basement floor at drawn floor-trap centre',xy)
            z,host=max(floors);g[4:6]=[round(z-.02,3),round(z+.01,3)]
            assumed=f'مصيدة أرضية من دائرة FT الفعلية؛ منسوب الجسم مشتق من سطح التشطيب المحلي {z:.2f}م ({host})، سماكة العرض3سم حول السطح افتراض.'
        a=e.setdefault('a',{})
        for key in list(a):
            if key.startswith('guess_') or key in ('mount_note','unsupported','ceil_dz'):a.pop(key,None)
        a.update({'sys':'drain_legacy','source_page':'MECH2:2','source_xy':xy,
                  'source_pdf_points':[[round(v,6) for v in pdf]],'source_transform':dict(sh.reg),
                  'source_drawing':di,'source_anchor_kind':anchor,'assumed':assumed,
                  'source_label_xy':baseline['g'][1:3],'model_correction':'من نص FT/CO ثم سحب للجدار إلى محور الرمز الفعلي من المسقط'})
        if host:a['floor_host']=host
        e['g']=g
        source=f'MECH2 ص2 DR-100: رمز {e.get("mark")} الحقيقي في M_DR_WP، الرسم{di}؛ السورس القديم M_DR_TEXT كان عند التسمية وليس الجسم.'
        if source not in M['sp']:M['sp'].append(source)
        si=M['sp'].index(source)
        if si not in e.setdefault('s',[]):e['s'].append(si)
        record=hist.setdefault(e['id'],{'element':e['id'],'level':'B','old_geometry':old,
            'original_label_geometry':copy.deepcopy(baseline['g']),'source':source,
            'source_pdf_points':a['source_pdf_points'],'source_transform':dict(sh.reg),
            'note':'المصدر الفعلي هو رمز المسقط؛ كان المجسم عند التسمية، ثم نقلته آلية الإسناد إلى جدار بعد تصحيح منسوب التشطيب. لم يثبت ارتفاع CO من الرسم.'})
        record['new_geometry']=copy.deepcopy(g);record['xy_cm']=xy
        if old!=g:changes.append(e['id'])
    return changes
