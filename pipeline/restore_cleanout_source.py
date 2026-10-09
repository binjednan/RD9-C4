# -*- coding: utf-8 -*-
"""Recover uniquely bound CO plan caps, including split words in PDF spans.

Data extraction reads individual PDF words: a span 'COCOCO' can contain three
different labels. A cap may have four or five vertices; five vertices draw a T
with two opposite arms. Shared nearest caps are pending, never forced apart.
apply() preserves existing CO Z and explicitly reports the high-level mismatch.
No connector is generated from the newly recovered marks.
"""
import collections
import copy
import json
import math
import os
import re

import lib

HERE=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(HERE,'data','cleanout_source_restore.json')
ID_RE=re.compile(r'-DCO\d{4}$')
PAGES={2:['B'],3:['G'],4:['G'],5:['1'],6:['2','3','4','5'],7:['R']}


def cap_records(sh):
    caps=[]
    for di,d in enumerate(sh.D):
        if d['layer'] not in ('M_DR_WP','M_DR_SP','M_DR_VP') or d.get('fill'):continue
        for pi,p in enumerate(d['polys']):
            if len(p) not in (4,5) or p[1]!=p[3]:continue
            stem=[p[0][k]-p[1][k]for k in(0,1)]
            arm=[p[2][k]-p[1][k]for k in(0,1)]
            a,b=math.hypot(*stem),math.hypot(*arm)
            if a==0 or b==0 or abs(sum(stem[k]*arm[k]for k in(0,1)))/(a*b)>.1:continue
            if not 2<b*sh.reg['s']<25 or not 2<a*sh.reg['s']<70:continue
            if len(p)==5:
                other=[p[4][k]-p[1][k]for k in(0,1)];c=math.hypot(*other)
                if c==0 or not 2<c*sh.reg['s']<25 or abs(sum(arm[k]*other[k]for k in(0,1))/(b*c)+1)>.05:continue
            caps.append({'drawing_index':di,'poly_index':pi,'layer':d['layer'],
                'cap_pdf_points':[list(q)for q in p],'source_pdf_points':[list(p[1])],
                'source_xy':list(sh.T(*p[1])),'source_transform':dict(sh.reg),
                'anchor_kind':'cap_intersection','vertex_count':len(p),
                'source_graphic_colour_rgb':d.get('color')})
    return caps


def source_page(M,e):
    for si in e.get('s',[]):
        m=re.search(r'MECH2 (?:ص|p)(\d+) وسم (?:CO|FCO)',M['sp'][si])
        if m:return int(m.group(1))
    a=e.get('a')or{}
    if a.get('source_page') and e.get('t')=='cleanout':
        m=re.search(r'MECH2:(\d+)',a['source_page'])
        if m:return int(m.group(1))
    return None


def extract(M):
    anchors={};new=[];pending=[];inventory=[];nnew=0
    for page,levels in PAGES.items():
        sh=lib.Sheet('MECH2',page);caps=cap_records(sh);labels=[]
        for wi,w in enumerate(sh.WD):
            xy=sh.T(w['x'],w['y']);xmax,ymax=(4440,4440)if page==2 else(3230,1900)
            if w['s']not in('CO','FCO') or not(w['layer']=='M_DR_TEXT' or not w['layer']):continue
            if not -30<xy[0]<xmax or not -100<xy[1]<ymax:continue
            # The repeated key and note samples occupy the right margin at
            # PDF x1908..1939 on these 1:50 sheets, inside the old broad crop.
            # Their CO/FCO labels are examples, not plan instances.
            if page in (5,6,7) and w['x']>1800:continue
            nearest=sorted(caps,key=lambda q:math.dist(xy,q['source_xy']))
            labels.append({'word_index':wi,'text':w['s'],'layer':w['layer'],
                'pdf_bbox':list(w['bbox']),'pdf_centre':[w['x'],w['y']],'xy':list(xy),
                'nearest':nearest[0], 'distance_cm':math.dist(xy,nearest[0]['source_xy']),
                'second_nearest_distance_cm':math.dist(xy,nearest[1]['source_xy'])})
        reuse=collections.Counter((q['nearest']['drawing_index'],q['nearest']['poly_index'])for q in labels if q['distance_cm']<60)
        qualified=[q for q in labels if q['distance_cm']<60 and reuse[q['nearest']['drawing_index'],q['nearest']['poly_index']]==1]
        pending_labels=[q for q in labels if q not in qualified]
        restored=0;added=0
        for level in levels:
            existing=[e for e in M['els']if e['l']==level and e.get('t')=='cleanout' and not ID_RE.search(e['id']) and source_page(M,e)==page]
            bound={}
            for e in existing:
                label_xy=(e.get('a')or{}).get('source_label_xy') or e['g'][1:3]
                hits=[q for q in labels if math.dist(q['xy'],label_xy)<.2]
                assert len(hits)==1,(e['id'],'legacy label is not a single raw word',label_xy)
                bound[hits[0]['word_index']]=e
            for q in labels:
                e=bound.get(q['word_index']);anchor=q['nearest']
                record=dict(copy.deepcopy(anchor),source_page=page,level=level,label={k:v for k,v in q.items()if k!='nearest'},
                    identity_binding='unique closest cap, no cap is shared by another plan CO label')
                if q not in qualified:
                    pending.append({'id':e['id']if e else None,'source_page':page,'level':level,'label':record['label'],
                        'candidate':anchor,'reason_ar':'أكثر من وسم CO يقابل النهاية الأقرب نفسها، أو الرمز بعيد؛ لا ربط إجباري.'})
                    continue
                if e:
                    record['original_g']=copy.deepcopy(e['g']);anchors[e['id']]=record;restored+=1
                else:
                    nnew+=1;record['id']=f'P.drain-{level}-DCO{nnew:04d}';new.append(record);added+=1
        inventory.append({'page':page,'levels':levels,'CO_word_labels':len(labels),'raw_cap_candidates':len(caps),
            'uniquely_bound_labels':len(qualified),'pending_labels':len(pending_labels),
            'restored_existing_devices':restored,'newly_recovered_devices':added})
    assert len(anchors)+sum(q['id']is not None for q in pending)==133
    return {'source_set':'MECH2','source_anchors':anchors,'new_caps':new,'pending':pending,'inventory':inventory,
        'counts':{'existing_xy_verified':len(anchors),'new_caps':len(new),'pending_model_devices':sum(q['id']is not None for q in pending),
                  'pending_source_labels':sum(q['id']is None for q in pending)},
        'vertical_review_ar':'أجسام CO القائمة تحتفظ Z القديم لأنه غير مثبت. ص3 عنوانHIGH LEVEL DRAINAGE LAYOUT؛ CO عندارتفاع التشطيب القديم يتعارض مع فئة المنسوب ويحتاج تثبيتًا من تفصيل/مسار المصدر. الأجسام الجديدة فيص3 تمثل عندمحور3.13/3.17/3.30م افتراضي حسبالوسط؛ لا يثبت هذا صلتها الرأسية.'}


def apply(M,els=None):
    if els is None:els=M['els']
    D=json.load(open(DATA,encoding='utf-8'));els[:]=[e for e in els if not ID_RE.search(e['id'])]
    byid={e['id']:e for e in els};history=M.setdefault('meta',{}).setdefault('drawing_corrections',{});changed=[]
    records=list(D['source_anchors'].items())+[(q['id'],q)for q in D['new_caps']]
    for eid,q in records:
        e=byid.get(eid);isnew=e is None
        if isnew:
            level=q['level'];ffl=next(l['ffl']for l in M['levels']if l['id']==level)
            z=(3.13 if q['layer']=='M_DR_SP' else 3.30 if q['layer']=='M_DR_VP' else 3.17) if q['source_page']==3 else ffl
            e={'id':eid,'c':'P.drain','l':level,'g':['cyl',0,0,6,round(z-.015,3),round(z+.015,3)],
                'mark':q['label']['text'],'t':'cleanout','m':'p_waste','a':{'no_connectors':True},'s':[]}
            els.append(e)
        if e.get('t')!='cleanout' or e['l']!=q['level'] or e['g'][0]!='cyl':raise ValueError('CO source identity changed: '+eid)
        old=copy.deepcopy(e['g']);x,y=q['source_xy'];e['g'][1:3]=[round(x,4),round(y,4)]
        a=e.setdefault('a',{})
        for k in list(a):
            if k.startswith('guess_')or k in('mount_note','unsupported','ceil_dz'):a.pop(k,None)
        a.update(sys='drain_legacy',source_page=f'MECH2:{q["source_page"]}',source_drawing=q['drawing_index'],
            source_poly_index=q['poly_index'],source_layer=q['layer'],source_pdf_points=q['source_pdf_points'],
            source_transform=q['source_transform'],source_xy=q['source_xy'],source_anchor_kind='cap_intersection',
            source_kind='cleanout_actual_cap',source_label_xy=q['label']['xy'],
            source_elevation_class='high_level'if q['source_page']==3 else 'unverified',
            geometry_role='source_symbol_display',material_status='not_specified_in_reviewed_source',
            finish_status='not_specified_in_reviewed_source',dimension_status='not_specified_in_reviewed_source',
            elevation_status='display_assumption_unverified'if isnew else 'retained_legacy_value_unverified',
            physical_geometry_status='display_proxy_pending_dimensions_and_mounting',
            source_graphic_colour_rgb=q.get('source_graphic_colour_rgb'),
            assumed='مركز CO من تقاطع نهاية الخام؛ قطر العرض12سم وسماكة3سم افتراض. '+('Z جديد افتراضي من فرض مستويات مواسير الاستخراج؛ لا موصل قرب.'if isnew else 'Z القديم محفوظ وغير مثبت من المخطط؛ لم يعالج بنقل إلى مضيف.')+(' عنوانص3HIGH LEVEL بينما ارتفاعCOالقديم عندالتشطيب؛ اختلاففئةمنسوبمعلق.'if q['source_page']==3 and not isnew else ''))
        source=f'MECH2 ص{q["source_page"]} DR: رمز CO الفعلي، الرسم{q["drawing_index"]}؛ الوسم كلمةPDF{q["label"]["word_index"]} منفصلة.'
        if source not in M['sp']:M['sp'].append(source)
        si=M['sp'].index(source)
        if si not in e['s']:e['s'].append(si)
        if old!=e['g']and not isnew:
            changed.append(eid);h=history.setdefault(eid,{'element':eid,'old_geometry':old,'source':source,
                'source_record':copy.deepcopy(q),'note':'ردXYإلىتقاطعالرمزالفريد؛Zالقائممحفوظ وغيرمثبت.'});h['new_geometry']=copy.deepcopy(e['g'])
    for q in D['pending']:
        e=byid.get(q['id'])
        if e:e.setdefault('a',{}).update(source_position_pending=True,source_position_review=q['reason_ar'],
            source_pending_page=f'MECH2:{q["source_page"]}',source_pending_label_xy=q['label']['xy'])
    M['meta']['cleanout_source_restore']={'qualified':len(D['source_anchors']),'changed':len(changed),
        'new_caps':len(D['new_caps']),'pending':copy.deepcopy(D['pending']),
        'inventory':D['inventory'],'vertical_review_ar':D['vertical_review_ar']}
    return {'qualified_existing':len(D['source_anchors']),'changed':len(changed),'new_caps':len(D['new_caps']),'pending':len(D['pending'])}


if __name__=='__main__':
    M=json.load(open(os.path.join(os.path.dirname(HERE),'src','model.json'),encoding='utf-8'))
    D=extract(M)
    with open(DATA,'w',encoding='utf-8')as f:json.dump(D,f,ensure_ascii=False,indent=2);f.write('\n')
    print('CO source:',D['counts']);print('CO inventory:',D['inventory'])
