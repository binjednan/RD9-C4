# -*- coding: utf-8 -*-
"""Restore proven FT centres from actual concentric DR plan circles.

Run this file to save source records. apply(M, els) changes the model in memory.
An FT label binds only to a unique double-circle glyph within60cm; another
candidate inside that distance makes the binding ambiguous. The four typical
floor text-only FT marks in an electrical shaft are listed as unresolved.
Device body dimensions are display assumptions; no pipe or connection is added.
"""
import copy
import json
import math
import os

from shapely.geometry import Point
import lib
from support import poly_of, zr

HERE=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(HERE,'data','floortrap_source_restore.json')
PAGES={2:['B'],4:['G'],5:['1'],6:['2','3','4','5'],7:['R']}


def extract(M):
    anchors={};unresolved=[];inventory=[]
    for page,levels in PAGES.items():
        sh=lib.Sheet('MECH2',page);circles=[]
        for di,d in enumerate(sh.D):
            if d['layer']!='M_DR_WP' or d.get('fill') or len(d['polys'])!=1 or len(d['polys'][0])!=41:continue
            r=d['rect'];w=(r[2]-r[0])*sh.reg['s'];h=(r[3]-r[1])*sh.reg['s']
            if 11.0<w<15.4 and abs(w-h)<.1:
                pdf=[(r[0]+r[2])/2,(r[1]+r[3])/2]
                circles.append({'drawing_index':di,'diameter_symbol_cm':w,'pdf_centre':pdf,'xy':list(sh.T(*pdf))})
        candidates=[]
        for q in circles:
            inside=[r for r in circles if .5<q['diameter_symbol_cm']-r['diameter_symbol_cm']<1.6 and math.dist(q['xy'],r['xy'])<.35]
            if len(inside)==1:candidates.append(dict(q,inner_drawing=inside[0]['drawing_index']))
        labels=[]
        for ti,t in enumerate(sh.TX):
            if t['layer']!='M_DR_TEXT' or t['s'].strip()not in ('FT','FW'):continue
            b=t['bbox'];pdf=[(b[0]+b[2])/2,(b[1]+b[3])/2]
            labels.append({'text_index':ti,'text':t['s'].strip(),'pdf_centre':pdf,'xy':list(sh.T(*pdf))})
        count=0
        for level in levels:
            devices=[e for e in M['els']if e['l']==level and e.get('t')=='floor_trap']
            assert len(devices)==len(labels),(page,level,len(devices),len(labels))
            used=set()
            for e,t in zip(devices,labels):
                near=sorted(candidates,key=lambda q:math.dist(t['xy'],q['xy']))
                hits=[q for q in near if math.dist(t['xy'],q['xy'])<60]
                if len(hits)!=1 or hits[0]['drawing_index']in used:
                    unresolved.append({'id':e['id'],'level':level,'source_page':page,'label':t,
                        'nearest_circle_distance_cm':math.dist(t['xy'],near[0]['xy']),
                        'reason_ar':'وسم FT حقيقي دون رمز مصيدة فريد في نطاق60سم؛ لا نقل إلى رمز بعيد أو أقرب خط.'})
                    continue
                q=hits[0];used.add(q['drawing_index']);count+=1
                old_distance=math.dist(e['g'][1:3],t['xy'])
                prior=(e.get('a')or{}).get('source_drawing')
                assert old_distance<=.2 or prior==q['drawing_index'],(e['id'],'legacy label identity moved',old_distance)
                anchors[e['id']]={'level':level,'source_page':page,'drawing_index':q['drawing_index'],
                    'inner_drawing':q['inner_drawing'],'layer':'M_DR_WP',
                    'source_pdf_points':[q['pdf_centre']],'source_xy':q['xy'],'source_transform':dict(sh.reg),
                    'outer_pdf_points':sh.D[q['drawing_index']]['polys'][0],
                    'inner_pdf_points':sh.D[q['inner_drawing']]['polys'][0],
                    'source_label':t,'label_to_glyph_cm':math.dist(t['xy'],q['xy']),
                    'symbol_diameter_cm':q['diameter_symbol_cm'],
                    'source_graphic_colour_rgb':sh.D[q['drawing_index']].get('color')}
        inventory.append({'page':page,'levels':levels,'FT_labels':len(labels),'double_circle_candidates':len(candidates),
                          'matched_model_devices':count,'candidate_limit':'unlabelled circles are not automatically emitted'})
    assert len(anchors)==117 and len(unresolved)==4,(len(anchors),len(unresolved))
    return {'source_set':'MECH2','source_anchors':anchors,'unresolved':unresolved,'inventory':inventory,
        'counts':{'source_circles_restored':117,'text_only_unresolved_devices':4},
        'method':'Unique FT label and concentric-circle plan glyph; no nearest-pipe binding',
        'classification_limit':'Circle centre is exact drawn XY. Body diameter, Z and connection remain separately derived or assumed.'}


def apply(M,els=None):
    if els is None:els=M['els']
    D=json.load(open(DATA,encoding='utf-8'));byid={e['id']:e for e in els};changes=[]
    history=M.setdefault('meta',{}).setdefault('drawing_corrections',{})
    floors={}
    for f in els:
        if f['c']!='A.floor' or (f.get('a')or{}).get('kind')=='طبقة تسوية تحت التشطيب':continue
        p=poly_of(f['g'])
        if p is not None and not p.is_empty:floors.setdefault(f['l'],[]).append((p,zr(f['g'])[1],f['id']))
    for eid,q in D['source_anchors'].items():
        e=byid.get(eid)
        if e is None or e.get('t')!='floor_trap' or e['l']!=q['level'] or e['g'][0]!='cyl':
            raise ValueError('Floor-trap source identity missing or changed: '+eid)
        x,y=q['source_xy'];point=Point(x,y)
        found=[(z,h)for p,z,h in floors.get(e['l'],[])if p.covers(point)]
        if not found:raise ValueError('No local finish at actual floor-trap centre: '+eid)
        z,host=max(found);old=copy.deepcopy(e['g'])
        e['g'][1:3]=[round(x,4),round(y,4)]
        e['g'][4:6]=[round(z-.02,3),round(z+.01,3)]
        a=e.setdefault('a',{})
        prior={k:a[k]for k in a if k.startswith('guess_')}
        for k in list(a):
            if k.startswith('guess_')or k in ('mount_note','unsupported','ceil_dz'):a.pop(k,None)
        a.update(sys='drain_legacy',source_page=f'MECH2:{q["source_page"]}',source_drawing=q['drawing_index'],
            source_inner_drawing=q['inner_drawing'],source_layer=q['layer'],source_pdf_points=q['source_pdf_points'],
            source_transform=q['source_transform'],source_xy=q['source_xy'],source_anchor_kind='circle_centre',
            source_kind='floortrap_actual_circle',source_label_xy=q['source_label']['xy'],floor_host=host,
            geometry_role='source_symbol_display',material_status='not_specified_in_reviewed_source',
            finish_status='not_specified_in_reviewed_source',dimension_status='not_specified_in_reviewed_source',
            elevation_status='derived_from_local_finish_unverified_mount',
            physical_geometry_status='display_proxy_pending_dimensions_and_mounting',
            source_graphic_colour_rgb=q.get('source_graphic_colour_rgb'),
            assumed=f'المركز من دائرتي FT الخامتين؛ المنسوب مشتق من التشطيب المحلي{z:.3f}م ({host}) وسمك العرض3سم حول سطحه افتراض. قطر الجسم12سم محفوظ من تمثيل قديم؛ رمز المسقط نحو{q["symbol_diameter_cm"]:.2f}سم وليس اعتماد مقاس تنفيذ.')
        source=f'MECH2 ص{q["source_page"]} DR: مركز رمز FT المزدوج، الرسم{q["drawing_index"]} وداخله{q["inner_drawing"]}، لا مركز التسمية.'
        if source not in M['sp']:M['sp'].append(source)
        si=M['sp'].index(source)
        if si not in e.setdefault('s',[]):e['s'].append(si)
        if old!=e['g']:
            changes.append(eid)
            h=history.setdefault(eid,{'element':eid,'level':e['l'],'old_geometry':old,'source':source,
                'source_record':copy.deepcopy(q),'prior_placement':prior,
                'note':'من موضع النص إلى مركز رمز المصيدة الفعلي؛ منسوب الجسم مشتق من التشطيب المحلي ولم تنشأ وصلة.'})
            h['new_geometry']=copy.deepcopy(e['g'])
    for q in D['unresolved']:
        e=byid.get(q['id'])
        if e:e.setdefault('a',{}).update(source_position_pending=True,source_position_review=q['reason_ar'],
            source_pending_page=f'MECH2:{q["source_page"]}',source_pending_label_xy=q['label']['xy'],
            geometry_role='unverified_legacy_display',material_status='not_specified_in_reviewed_source',
            finish_status='not_specified_in_reviewed_source',dimension_status='not_specified_in_reviewed_source',
            elevation_status='retained_legacy_value_unverified',physical_geometry_status='display_proxy_pending_source_position')
    M['meta']['floortrap_source_restore']={'qualified':len(D['source_anchors']),'changed':len(changes),
        'unresolved':copy.deepcopy(D['unresolved']),'geometry_claim':'Circle-centre XY only; local floor Z is derived'}
    return {'qualified':len(D['source_anchors']),'changed':len(changes),'unresolved':len(D['unresolved'])}


if __name__=='__main__':
    model=json.load(open(os.path.join(os.path.dirname(HERE),'src','model.json'),encoding='utf-8'))
    D=extract(model)
    with open(DATA,'w',encoding='utf-8')as f:json.dump(D,f,ensure_ascii=False,indent=2);f.write('\n')
    print('FT source:',D['counts'])
