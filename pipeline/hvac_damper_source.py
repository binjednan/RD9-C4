# -*- coding: utf-8 -*-
"""333 original damper graphicanchors; six roofsymbols explicitly unresolved.

328 retained identities + five distinctFD glyphsplits. Geometry represents the
raw symbolbbox, not a fabricated devicehousing. ExistingZ/material remain
assumptions. No VT/SM geometry, connectors, mounting or globalregistration.
"""
import copy
import functools
import hashlib
import json
from pathlib import Path

DATA_PATH=Path(__file__).with_name('data')/'hvac_damper_source.json'
_FROZEN_DATA_SHA='5c3732cbdb23a92e2b6ef416dd294746e79f6885181d91b2cd2fbd3f657f8b0b'
TYPES={}


def _items(value):
    import fitz
    if isinstance(value,fitz.Point):return [value.x,value.y]
    if isinstance(value,fitz.Quad):return [[p.x,p.y] for p in value]
    if isinstance(value,fitz.Rect):return list(value)
    if isinstance(value,(list,tuple)):return [_items(p) for p in value]
    return value


@functools.lru_cache(maxsize=2)
def _verify(data_text,pdf_path,mtime_ns,size):
    import fitz
    import reg
    if hashlib.sha256(data_text.encode()).hexdigest()!=_FROZEN_DATA_SHA:
        raise ValueError('HDB frozen source data changed')
    data=json.loads(data_text)
    if hashlib.sha256(Path(pdf_path).read_bytes()).hexdigest()!=data['source_pdf_sha256']:
        raise ValueError('HDB original PDF fingerprint changed')
    with fitz.open(pdf_path) as doc:
        drawings={}
        for pn,page in data['pages'].items():
            ds=doc[int(pn)-1].get_drawings();drawings[pn]=ds
            grid=[d for d in ds if d.get('layer') and ('GRID' in d['layer'].upper() or 'AXIS' in d['layer'].upper()) and 'IDEN' not in d['layer'].upper()]
            vv,hh=reg.grid_clusters(None,layers=None,drawings=grid,minlen=50)
            if vv!=page['raw_grid_v'] or hh!=page['raw_grid_h'] or reg.register_free(vv,hh)!=page['transform']:
                raise ValueError('HDB original freegrid registration changed')
            for q in page['grid_primitives']:
                d=ds[q['drawing']]
                if d.get('layer')!=q['layer'] or _items(d['items'])!=q['items']:
                    raise ValueError('HDB original grid primitive changed')
        for row in list(data['records'].values())+list(data['additions'].values()):
            s=row['source'];ds=drawings[s['source_page'].split(':')[1]]
            sha=hashlib.sha256(json.dumps(s,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if sha!=row['source_record_sha256']:raise ValueError('HDB record fingerprint changed')
            for di,items,points in zip(s['source_drawing_indices'],s['source_raw_items'],s['source_pdf_points']):
                d=ds[di]
                if d.get('layer')!='M_HVAC_DAM' or _items(d['items'])!=items:
                    raise ValueError('HDB original symbol primitive changed')
                actual=[_items(d['items'][0][1])]+[_items(op[2]) for op in d['items']]
                if actual!=points or len(actual)!=7 or actual[0]!=actual[-1]:
                    raise ValueError('HDB original closedL profile changed')
    return True


def _identity(e,row):
    return (e['id'],e['c'],e['t'],e['l'],e.get('m'))==(row['id'],row['c'],row['t'],row['l'],row['m'])


def _assumed_base_z(e):
    dz=float((e.get('a') or {}).get('ceil_dz',0))
    return [round(v-dz,3) for v in e['g'][6:8]]


def _geometry_guard(e,row,addition=False):
    # ceil_dz is a procedural offset; it is not a surveyed/source elevation.
    core=[row['after_g'][:6]] if addition else [row['before_g'][:6],row['after_g'][:6]]
    return e['g'][:6] in core and _assumed_base_z(e)==row['assumed_base_Z_procedural_guard']


def _attributes(row):
    s=copy.deepcopy(row['source'])
    s.update(sys='air',source_locked_xy=True,source_damper_record=row['id'],
             source_record_sha256=row['source_record_sha256'],
             source_anchor='closed_L_symbol_bbox_centre_not_port',
             source_graphic_bbox_verified=True,source_graphic_rotation_verified=True,
             source_semantics_checked=True,source_class_semantics_checked=True,
             source_subtype_verified=False,source_rotation_verified=False,
             source_dimensions_verified=False,source_Z_verified=False,
             source_material_verified=False,source_mount_verified=False,
             source_contact_verified=False,source_ports_verified=False,
             source_body_dimensions_assumed=True,source_height_assumed=True,
             source_geometry_role='display_bbox_proxy_for_closed_L_plan_symbol',
             source_geometry_review='body_graphic_only',
             size_cm=str(round(row['after_g'][3],1))+'×'+str(round(row['after_g'][4],1)),
             no_connectors=True,no_hangers=True,
             assumed='رمزL يثبت مركز وبصمة/زاوية الرسم فقط، وليس جسم مخمد تنفيذيًا أو منفذه. جسم العرض بصندوقbbox مشتق من الرمز؛ Z القائمة ومواد العرض والمقاس التنفيذي والتثبيت غير مثبتة. رمزاFD المنفصلان يمثلان علامتين مرسومتين؛ لا تثبت كميتهما كمية المصنع. لم يختَر أقرب جدار أو منفذ، ولم تُضف وصلة أو دعامة.')
    if row['source_symbol_type']:
        s['source_pair_tag_context']=row['source_symbol_type']
    return s


def apply(M,els=None):
    els=M['els'] if els is None else els
    data_text=DATA_PATH.read_text(encoding='utf-8');data=json.loads(data_text)
    pdf=Path(data['source_pdf']);stat=pdf.stat();_verify(data_text,str(pdf),stat.st_mtime_ns,stat.st_size)
    by={e['id']:e for e in els};counts={}
    for e in els:counts[e['id']]=counts.get(e['id'],0)+1
    for eid,row in data['records'].items():
        e=by.get(eid)
        if e is None or counts[eid]!=1 or not _identity(e,row) or not _geometry_guard(e,row):
            raise ValueError('HDB exact current identity/geometry guard failed: '+eid)
    for eid,row in data['additions'].items():
        e=by.get(eid)
        if e is not None and (counts[eid]!=1 or not _identity(e,row) or not _geometry_guard(e,row,addition=True)):
            raise ValueError('HDB existing split identity/geometry guard failed: '+eid)
    changes=[];added=[]
    for eid,row in list(data['records'].items())+list(data['additions'].items()):
        e=by.get(eid)
        if e is None:
            e=copy.deepcopy(by[row['original_id']]);e['id']=eid;els.append(e);by[eid]=e;added.append(eid)
        before=copy.deepcopy(e['g']);e['g']=copy.deepcopy(row['after_g'][:6])+copy.deepcopy(before[6:])
        a=e.setdefault('a',{})
        for key in ['mount_note','guess_from','guess_host','guess_kind','guess_cm','guess_conf','snap_cm','snap_note']:
            a.pop(key,None)
        a.update(_attributes(row))
        if before!=e['g']:changes.append({'id':eid,'before_g':before,'after_g':copy.deepcopy(e['g']),'source_record_sha256':row['source_record_sha256']})
    stats={**data['summary'],'source_data_sha256':hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
           'scope_ar':data['scope_ar'],'added_this_apply':added,'changed_this_apply':len(changes),
           'changes':changes,'pending_R_source_gaps':list(data['pending'].values())}
    M.setdefault('meta',{})['hvac_damper_source']=stats
    return stats


build=apply
