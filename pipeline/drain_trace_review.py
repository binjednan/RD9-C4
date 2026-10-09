# -*- coding: utf-8 -*-
"""Audit legacy drain traces against original PDF linework; annotate only.

Run to save data, never the model. apply(M, els) preserves every coordinate,
diameter and level. Four VP lines receive a separate ventilation classification.
Recorded old geometry is an identity guard, not the source of any position.
Approximate compositions remain pending; no nearest-path reconstruction occurs.
"""
import collections
import copy
import hashlib
import json
import math
import os
import re
import sys

from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree
import lib
import risers

HERE=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(HERE,'data','drain_trace_review.json')
PAGES={'B':2,'G':4,'1':5,'2':6,'3':6,'4':6,'5':6,'R':7}
LAYERS={'pipe_waste':'M_DR_WP','pipe_soil':'M_DR_SP','pipe_vent':'M_DR_VP','vent_drain_pipe':'M_DR_VP'}
VP_IDS={'P.drain-G-M0033','P.drain-G-M0064','P.drain-G-M0065','P.drain-G-M0066'}
TOL=.2

def geometry_hash(g):
    return hashlib.sha256(json.dumps(g,separators=(',',':')).encode()).hexdigest()

def raw_sheet(page,layer):
    sh=lib.Sheet('MECH2',page);records=[];lines=[]
    for di,d in enumerate(sh.D):
        if d['layer']!=layer or d.get('fill'):continue
        for pi,path in enumerate(d['polys']):
            world=[list(sh.T(*v))for v in path]
            if len(world)<2 or all(math.dist(world[0],v)<1e-8 for v in world):continue
            records.append({'drawing':di,'poly':pi,'layer':layer,'pdf_points':copy.deepcopy(path),
                            'xy':world,'graphic_colour_rgb':d.get('color')})
            lines.append(LineString(world))
    return sh,records,lines,STRtree(lines)

def _spans(shape):
    return [[list(v)for v in p.coords] for p in getattr(shape,'geoms',[shape])
            if p.geom_type=='LineString' and not p.is_empty and p.length>1e-8]

def extract(M):
    sheets={};records={};counts=collections.Counter();cases=[]
    for e in M['els']:
        if e['c']!='P.drain' or e['g'][0]!='t' or e.get('t')not in LAYERS:continue
        if re.search(r'-(K|ST|DTR|DRG|DSM)\d{4}$',e['id']):continue
        page=PAGES.get(e['l'])
        for si in e.get('s',[]):
            match=re.search(r'MECH2 (?:ص|p)(\d+) طبقة',M['sp'][si])
            if match:page=int(match.group(1));break
        layer=LAYERS[e['t']];key=(page,layer)
        if key not in sheets:sheets[key]=raw_sheet(*key)
        sh,raw,lines,tree=sheets[key];xy=[p[:2]for p in e['g'][1]]
        route=LineString(xy);derived=bool(re.search(r'-V\d{4}$',e['id']))
        # Exact nearby primitives establish only linework coverage; this is not
        # a device classifier or permission to snap a route to those primitives.
        hit=list(tree.query(route.buffer(3 if not derived else 10),predicate='intersects'))
        selected=[raw[int(i)]for i in hit]
        probes=[Point(v)for v in xy]+[route.interpolate(i*.5)for i in range(1,int(route.length/.5))]
        nearest=tree.nearest(probes)
        delta=max(p.distance(lines[int(i)])for p,i in zip(probes,nearest))
        vertices=[Point(v)for v in xy];vi=tree.nearest(vertices)
        vertex_delta=max(p.distance(lines[int(i)])for p,i in zip(vertices,vi))
        # Rounded caps express the .2cm Euclidean distance threshold at source
        # endpoints. Flat caps incorrectly reject a .04cm rounding overhang.
        nearby=unary_union([lines[int(i)]for i in hit])
        outside=route.difference(nearby.buffer(TOL,cap_style=1,join_style=1))
        if derived:status='derived_vertical_riser';exact=False
        elif outside.is_empty:status='raw_drawn_linework';exact=True
        elif vertex_delta>TOL:status='arc_glyph_composition_pending';exact=False
        else:status='derived_bridge_through_source_symbols';exact=False
        q={'id':e['id'],'category':e['c'],'type':e['t'],'level':e['l'],
           'source':f'MECH2:{page}','layer':layer,'registration':dict(sh.reg),
           'geometry_guard_sha256':geometry_hash(e['g']),'reviewed_g':copy.deepcopy(e['g']),
           'source_primitives':[[p['drawing'],p['poly']]for p in selected],'raw_primitives':selected,
           'status':status,'whole_trace_xy_verified':exact,'physical_geometry_verified':False,
           'sampled_deviation_cm':delta,'vertex_deviation_cm':vertex_delta,
           'outside_source_trace_cm':outside.length,'outside_source_spans_xy_cm':_spans(outside),
           'reviewed_model_xy_cm':xy,
           'nominal_diameter_status':'not_specified_in_reviewed_source',
           'elevation_status':'retained_legacy_value_unverified',
           'material_status':'not_specified_in_reviewed_source','finish_status':'not_specified_in_reviewed_source',
           'no_reconstructed_source_route':True,
           'method':'Complete XY trace against original layer vectors at .2cm; raw indices and points retained; no source geometry from the old model'}
        if derived:q['limit_ar']='الصاعد رأسي مشتق بين المستويات؛ رموز المسقط القريبة مرشحات فقط، ولا تثبت المحاذاة الرأسية أو Z.'
        elif exact:q['limit_ar']='المسار داخل خط المصدر؛ الطبقة تثبت وسط الخدمة، ولا تثبت القطر الافتراضي أو Z أو مادة/تشطيب الجسم.'
        else:q['limit_ar']='مسار قديم يخلط رؤوس الخط مع أقواس/رموز أو يصل فراغاتها. لم يثبت مسار خام فريد كامل، فلا تصحيح من الأقرب ولا اعتماد كأنبوب منحني فعلي.'
        records[e['id']]=q;counts[status]+=1
        if not exact:
            cases.append({'id':e['id'],'level':e['l'],'source':q['source'],'status':status,
                          'model_xy_cm':xy,'raw_source_primitives':q['source_primitives'],
                          'source_candidate_xy_cm':[p['xy']for p in selected],
                          'reason_ar':q['limit_ar']})
    assert len(records)==798 and sum(q['status']=='derived_vertical_riser'for q in records.values())==70
    return {'schema':'drain_trace_review_v1','records':records,'counts':dict(counts),'VP_ids':sorted(VP_IDS),
            'pending_cases':cases,'tolerance_cm':TOL,
            'source_scope':'MECH2:2–7 original unfilled M_DR_WP/SP/VP vectors;728 plan routes and70 derived risers',
            'scope_limit_ar':'مطابقة XY الخطوط وحدها؛ لا إثبات لمقاسات الأجسام أو Z أو اللون والمادة. الأقواس المركبة والجسور لا ترقّى إلى مصدر هندسة فعلية.'}

def derived_riser_bindings(M,els=None,records=None):
    """Read-only exact canonical mapping; V ordinals never identify a source."""
    if records is None:
        with open(DATA,encoding='utf-8')as f:records=json.load(f)['records']
    return risers.derived_drain_bindings(M,els,records)


def apply(M,els=None):
    els=M['els']if els is None else els
    with open(DATA,encoding='utf-8')as f:D=json.load(f)
    byid={e['id']:e for e in els};seen=[];mismatches=[];vp=[]
    for eid,q in D['records'].items():
        # Earlier media change the global V ordinal. Current drain risers are
        # classified from their actual generator and matched by exact c/t/l/g
        # below; an old V ID may now refer to a different derived segment.
        if q['status']=='derived_vertical_riser':continue
        e=byid.get(eid)
        if e is None:mismatches.append({'id':eid,'reason':'reviewed identity absent'});continue
        if e['l']!=q['level']or e['c']!=q['category']or geometry_hash(e['g'])!=q['geometry_guard_sha256']:
            mismatches.append({'id':eid,'reason':'reviewed geometry or identity changed'});continue
        if e.get('t') not in (q['type'],'vent_drain_pipe'if eid in VP_IDS else q['type']):
            mismatches.append({'id':eid,'reason':'reviewed service type changed'});continue
        a=e.setdefault('a',{})
        a.update(source_trace_review=True,source_trace_status=q['status'],source_trace_record=eid,
            source_page=q['source'],source_transform=copy.deepcopy(q['registration']),
            source_primitives=copy.deepcopy(q['source_primitives']),source_trace_limit=q['limit_ar'],
            geometry_role='derived_riser_display'if q['status']=='derived_vertical_riser'else'source_route_display',
            material_status=q['material_status'],finish_status=q['finish_status'],
            dimension_status=q['nominal_diameter_status'],elevation_status=q['elevation_status'],
            physical_geometry_status='display_proxy_pending_diameter_elevation_and_semantic_parts')
        if q['whole_trace_xy_verified']:
            a.update(source_locked_xy=True,source_kind='drawn_layer_trace')
        else:
            a.pop('source_locked_xy',None)
            a.update(source_kind=q['status'],source_position_pending=True,
                     source_position_review=q['limit_ar'])
        if eid in VP_IDS:
            e['t']='vent_drain_pipe';a.update(sys='drain_legacy_vent',no_connectors=True,flow_medium='vent_air');vp.append(eid)
        seen.append(eid)
    current_counts=collections.Counter(D['records'][eid]['status']for eid in seen)
    bindings=risers.annotate_derived_drains(M,els,D['records'])
    seen.extend(bindings['bindings'])
    current_counts['derived_vertical_riser']=bindings['current_count']
    pending=[copy.deepcopy(q)for q in D['pending_cases']if q['status']!='derived_vertical_riser']
    for eid,binding in bindings['bindings'].items():
        e=byid[eid];historical=D['records'].get(binding['historical_id'])if binding['historical_id']else None
        pending.append({'id':eid,'historical_record':binding['historical_id'],'level':e['l'],
            'source':historical['source']if historical else None,'status':'derived_vertical_riser',
            'model_xy_cm':[p[:2]for p in e['g'][1]],
            'raw_source_primitives':copy.deepcopy(historical['source_primitives'])if historical else [],
            'source_candidate_xy_cm':[p['xy']for p in historical['raw_primitives']]if historical else [],
            'binding_status':binding['binding_status'],'reason_ar':risers.DRAIN_LIMIT,
            'proof_scope':'derived_identity_only_not_drawn_XY_Z_or_contact'})
    M.setdefault('meta',{})['drain_trace_review']={'annotated':len(seen),'counts':dict(current_counts),
        'historical_counts':D['counts'],'current_counts':dict(current_counts),'derived_riser_bindings':bindings,
        'VP_reclassified':vp,'identity_mismatches':mismatches,'coordinate_changes':0,
        'pending_cases':pending,'source_scope':D['source_scope'],
        'current_scope_ar':'728 مسار مسقط تاريخي بحراس هندسته، مع قوائم الصرف الحالية من مولّد risers.py. الربط التاريخي للصواعد exact c/t/l/g فقط، ولا إثبات موضع رأسي خام.'}
    return {'annotated':len(seen),'counts':dict(current_counts),'VP_reclassified':vp,
        'derived_risers':bindings['current_count'],'derived_riser_exact_unique_bindings':bindings['exact_unique_count'],
        'derived_riser_unmatched':bindings['unmatched_count'],'derived_riser_ambiguous':bindings['ambiguous_count'],
        'identity_mismatches':mismatches,'coordinate_changes':0}

if __name__=='__main__':
    with open(os.path.join(os.path.dirname(HERE),'src','model.json'),encoding='utf-8')as f:M=json.load(f)
    D=extract(M)
    with open(DATA,'w',encoding='utf-8')as f:json.dump(D,f,ensure_ascii=False,indent=2);f.write('\n')
    print('drain source trace review:',D['counts'])
