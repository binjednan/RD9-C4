# -*- coding: utf-8 -*-
"""Independent originalPDF gate:333 closedL glyphbbox anchors; sixR gaps.

Currentdevice dimensions/Z/mount/ports are never approved by this check.
Original emitterorder only identifies retained IDs; it never suppliesXY.
"""
import collections
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
DATA_PATH=ROOT/'pipeline/data/hvac_damper_source.json'
TOL=.2
_FROZEN_DATA_SHA='5c3732cbdb23a92e2b6ef416dd294746e79f6885181d91b2cd2fbd3f657f8b0b'
_SCHEMA='c4.hvac-damper-source.v2'
_PAGE={'B':1,'G':2,'1':3,'2':4,'3':4,'4':4,'5':5}
_START={'B':1,'G':1,'1':1,'2':62,'3':124,'4':186,'5':248}
_COUNT={'B':2,'G':17,'1':61,'2':62,'3':62,'4':62,'5':62}


def _items(v):
    import fitz
    if isinstance(v,fitz.Point):return [v.x,v.y]
    if isinstance(v,fitz.Quad):return [[p.x,p.y] for p in v]
    if isinstance(v,fitz.Rect):return list(v)
    if isinstance(v,(tuple,list)):return [_items(q) for q in v]
    return v


def _raw(page):
    from shapely.geometry import Polygon
    sys.path.insert(0,str(ROOT/'pipeline'));import reg
    ds=page.get_drawings();grid=[d for d in ds if d.get('layer') and ('GRID' in d['layer'].upper() or 'AXIS' in d['layer'].upper()) and 'IDEN' not in d['layer'].upper()]
    vv,hh=reg.grid_clusters(None,layers=None,drawings=grid,minlen=50);T=reg.register_free(vv,hh)
    if not T or T['nx']<4 or T['ny']<3 or T['ex']/T['nx']>=2.2 or T['ey']/T['ny']>=2.2:
        raise ValueError('Original damper page has no qualified full rawgridT')
    primitives=[]
    for di,d in enumerate(ds):
        if d.get('layer')!='M_HVAC_DAM':continue
        if len(d['items'])!=6 or not all(q[0]=='l' for q in d['items']):raise ValueError('Original closedL prototype changed')
        pts=[_items(d['items'][0][1])]+[_items(q[2]) for q in d['items']]
        if pts[0]!=pts[-1]:raise ValueError('Original damperL is not closed')
        bb=[min(p[k] for p in pts) for k in (0,1)]+[max(p[k] for p in pts) for k in (0,1)]
        primitives.append({'drawing':di,'poly':0,'points':pts,'items':_items(d['items']),'bbox':bb})
    remaining=set(range(len(primitives)));groups=[]
    while remaining:
        first=min(remaining);remaining.remove(first);ids=[first];stack=[first]
        while stack:
            i=stack.pop();a=primitives[i]['bbox']
            for j in list(remaining):
                b=primitives[j]['bbox']
                if a[0]-.6<=b[2] and b[0]-.6<=a[2] and a[1]-.6<=b[3] and b[1]-.6<=a[3]:
                    remaining.remove(j);ids.append(j);stack.append(j)
        unique=[]
        for i in sorted(ids):
            q=primitives[i];polygon=Polygon(q['points'])
            existing=next((a for a in unique if polygon.equals(Polygon(a[0]['points']))),None)
            if existing is None:unique.append([q])
            else:existing.append(q)
        groups.append(unique)
    return groups,T,vv,hh,ds


def audit(M):
    # Rehydrate external audit inputs; geometry remains the live model.
    import sys as _audit_sys
    from pathlib import Path as _AuditPath
    _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
    from source_audit_sidecar import audit_model as _source_audit_model
    M = _source_audit_model(M)
    import fitz
    data_bytes=DATA_PATH.read_bytes();data=json.loads(data_bytes);data_sha=hashlib.sha256(data_bytes).hexdigest();pdf=Path(data['source_pdf']);pdf_sha=hashlib.sha256(pdf.read_bytes()).hexdigest()
    global_findings=[];expected_records=set();expected_additions=set()
    if data_sha!=_FROZEN_DATA_SHA:global_findings.append({'kind':'frozen_data_fingerprint','reason':'Frozen original source ledger SHA differs'})
    if data.get('schema')!=_SCHEMA:global_findings.append({'kind':'source_schema','reason':'Frozen original source ledger schema differs'})
    by={e['id']:e for e in M['els']};checks=[];pages={};new_ordinal=0
    with fitz.open(pdf) as doc:
        for pn in range(1,6):pages[pn]=_raw(doc[pn-1])
        for level,pn in _PAGE.items():
            groups,T,vv,hh,ds=pages[pn]
            if len(groups)!=_COUNT[level]:raise ValueError('Original ordered damper inventory differs')
            for ordinal,distinct in enumerate(groups):
                base='M.damper-'+level+('-M' if level in ['B','G'] else '-')+str(_START[level]+ordinal).zfill(4)
                for slot,duplicates in enumerate(distinct):
                    eid=base
                    if slot:
                        new_ordinal+=1;eid='M.damper-'+level+'-HDB'+str(new_ordinal).zfill(4)
                    (expected_additions if slot else expected_records).add(eid)
                    row=(data['additions'] if slot else data['records']).get(eid);e=by.get(eid);q=duplicates[0];errors=[]
                    bb=q['bbox'];anchor=[(bb[0]+bb[2])/2,(bb[1]+bb[3])/2]
                    xy=[anchor[0]*T['s']+T['ox'],T['oy']-anchor[1]*T['s']]
                    w=(bb[2]-bb[0])*T['s'];h=(bb[3]-bb[1])*T['s'];size=[max(w,h),min(w,h)];angle=0 if w>=h else 90
                    check={'id':eid,'reference':'MECH1:'+str(pn),'source_kind':'closed_L_damper_graphic_bbox_proxy','method':'Original ordered6line closedL contour; distinct polygon split; exact CADduplicates retained once; freshrawgridT', 'source_xy':xy,'source_primitives':[[d['drawing'],d['poly']] for d in duplicates],'graphic_size_cm':size,'graphic_angle':angle,'scope':'graphic_anchor_extent_angle_only_not_body_Z_material_mount_ports','physical_source_acceptance':False}
                    if row is None or e is None:
                        errors.append('Missing exact333 qualified source identity');check.update(errors=errors);check['pass']=False;checks.append(check);continue
                    s=row['source'];a=e.get('a') or {};di=[d['drawing'] for d in duplicates];pts=[d['points'] for d in duplicates];items=[d['items'] for d in duplicates]
                    if pdf_sha!=data['source_pdf_sha256'] or s['source_pdf_sha256']!=pdf_sha or a.get('source_pdf_sha256')!=pdf_sha:errors.append('Original PDF fingerprint changed')
                    if (e['c'],e['t'],e['l'],e.get('m'),e['g'][0])!=('M.damper','damper',level,row['m'],'b'):errors.append('Source genericclass/level/material identity changed')
                    if (s['source_drawing_indices']!=di or s['source_pdf_points']!=pts or s['source_raw_items']!=items or
                            a.get('source_drawing_indices')!=di or a.get('source_pdf_points')!=pts or a.get('source_raw_items')!=items):errors.append('Original closedL contour primitive differs')
                    if s['source_transform']!=T or a.get('source_transform')!=T or data['pages'][str(pn)]['raw_grid_v']!=vv or data['pages'][str(pn)]['raw_grid_h']!=hh:errors.append('Fresh original rawgridregistration differs')
                    sha=hashlib.sha256(json.dumps(s,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
                    if row['source_record_sha256']!=sha or a.get('source_record_sha256')!=sha:errors.append('Source record fingerprint differs')
                    delta=math.dist(e['g'][1:3],xy);dim=max(abs(e['g'][3+k]-size[k]) for k in [0,1]);rotation=abs(e['g'][5]-angle)
                    metadata=max(math.dist(a.get('source_xy',[1e10,1e10]),xy),math.dist(s['source_xy'],xy))
                    if metadata>TOL or a.get('source_anchor_pdf')!=anchor or s['source_bbox_pdf']!=bb:
                        errors.append('Original glyphanchor metadata differs')
                    if delta>TOL:errors.append('Original glyphanchor differs beyond0.2cm')
                    if dim>TOL:errors.append('Display graphicbbox extent differs beyond0.2cm')
                    if rotation>.001:errors.append('Graphicbbox orientation differs')
                    dz=float(a.get('ceil_dz',0));base_z=[round(v-dz,3) for v in e['g'][6:8]]
                    snapshot_base=[round(v-row['before_ceil_dz'],3) for v in row['before_g'][6:8]]
                    if base_z!=snapshot_base or base_z!=row['assumed_base_Z_procedural_guard']:errors.append('Existing assumedbaseZ changed without matching procedural ceil_dz')
                    if a.get('source_geometry_review')!='body_graphic_only' or a.get('size_cm')!=str(round(e['g'][3],1))+'×'+str(round(e['g'][4],1)):errors.append('Graphicbody review/symbolicsize label missing')
                    if any(a.get(k) for k in ['source_dimensions_verified','source_Z_verified','source_material_verified','source_mount_verified','source_contact_verified','source_ports_verified','source_rotation_verified']):errors.append('Unsafe physicalbody/Z/material/mount/port promotion')
                    if not a.get('source_locked_xy') or a.get('source_anchor')!='closed_L_symbol_bbox_centre_not_port':errors.append('Sourceanchor guard/scope metadata missing')
                    check.update(deviation_cm=delta,graphic_size_deviation_cm=dim,graphic_angle_deviation_deg=rotation,metadata_deviation_cm=metadata,assumed_base_Z_procedural=base_z,absolute_Z_source_accepted=False,errors=errors)
                    check['pass']=not errors;checks.append(check)
    for name,expected in [('records',expected_records),('additions',expected_additions)]:
        actual=set(data[name])
        if actual!=expected:global_findings.append({'kind':'exact_original_inventory_set','ledger':name,'unexpected_ids':sorted(actual-expected),'missing_ids':sorted(expected-actual),'reason':'Ledger identities differ from actual ordered originalPDF symbols'})
    counts=collections.Counter(e['id'] for e in M['els'])
    duplicated=sorted(eid for eid in expected_records|expected_additions if counts[eid]!=1)
    if duplicated:global_findings.append({'kind':'qualified_model_identity_multiplicity','ids':duplicated,'reason':'Each qualified source identity must occur once in model'})
    pending=[]
    for eid,row in data['pending'].items():
        e=by.get(eid)
        pending.append({'id':eid,'reference':'MECH1:6','status':'source_gap_unverified_transform','source_promotion':False,'geometry_preserved':bool(e and e['g']==row['g']),'reason':row['reason_ar']})
    for q in pending:
        if not q['geometry_preserved']:global_findings.append({'kind':'pending_geometry_preservation','id':q['id'],'reason':'Unverified roof symbol geometry changed or identity absent; preservation claim fails'})
    return {'checks':checks,'pending':pending,'global_findings':global_findings,'summary':{'checked':len(checks),'findings':sum(not q['pass'] for q in checks)+len(global_findings),'raw_check_findings':sum(not q['pass'] for q in checks),'global_findings':len(global_findings),'uncovered':sum('Missing exact333 qualified source identity' in q['errors'] for q in checks),'max_deviation_cm':max(q.get('deviation_cm',0) for q in checks),'pending_source_transform':len(pending),'pending_geometry_changed':sum(not q['geometry_preserved'] for q in pending),'physical_body_Z_material_mount_ports_accepted':False,'source_PDF_sha256':pdf_sha,'source_data_sha256':data_sha}}
