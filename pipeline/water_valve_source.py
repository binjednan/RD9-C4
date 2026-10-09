"""167 source valve graphics; no physical housing, ports, Z or operating proof."""
import copy
import functools
import hashlib
import json
from pathlib import Path

DATA_PATH=Path(__file__).with_name('data')/'water_valve_source.json'
_FROZEN_DATA_SHA='04dad88b5cb3f4b6d79bf982866bb8d2c3c810c0838ec1c1f4de9beb83b7a73d'
_SCHEMA='c4.water-valve-source.v1'
TYPES={code:{'n':name,'cf':'derived','sp':[['التمثيل','علامة مصدر رسومية فقط؛ صندوق bbox للرمز وليس جسم مصنع'],['المادة واللون','غير محددين بالمصدر؛ مادة العرض القائمة لا تثبت مادة الصمام'],['Z والاتصال','افتراضيان؛ لا ports أو تشغيل أو تركيب مثبت']],'sr':['MECH2 ص19–22: مختصرات المفتاح + رمز المسقط وحروف الوسم']} for code,name in [('valve_IV','علامة IV — صمام عزل حسب مفتاح المصدر'),('valve_GV','علامة GV — تجهيز مستقبلي FOR PROVISION'),('valve_NRV','علامة NRV — عدم رجوع حسب مفتاح المصدر'),('valve_source_graphic','علامة صمام مياه — النوع التفصيلي غير مثبت')]}


def _items(v):
    import fitz
    if isinstance(v,fitz.Point):return [v.x,v.y]
    if isinstance(v,fitz.Quad):return [[q.x,q.y]for q in v]
    if isinstance(v,fitz.Rect):return list(v)
    if isinstance(v,(list,tuple)):return [_items(q)for q in v]
    return v


def _sha(v):
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _text_guard(tt,tag):
    t=tt[tag['texttrace_index']];cs=[t['chars'][i]for i in tag['char_indices']]
    return (t.get('layer')==tag['layer'] and ''.join(chr(c[0])for c in cs)==tag['text'] and
            [c[0]for c in cs]==tag['char_codes'] and [list(c[3])for c in cs]==tag['char_bboxes'] and
            ''.join(chr(c[0])for c in t['chars'])==tag['full_trace_text'])


@functools.lru_cache(maxsize=2)
def _verify(text,pdfpath,mtime,size):
    import fitz,lib,reg
    if hashlib.sha256(text.encode()).hexdigest()!=_FROZEN_DATA_SHA:raise ValueError('VSC frozen source data changed')
    data=json.loads(text)
    if data.get('schema')!=_SCHEMA:raise ValueError('VSC schema changed')
    if hashlib.sha256(Path(pdfpath).read_bytes()).hexdigest()!=data['source_pdf_sha256']:raise ValueError('VSC original PDF changed')
    with fitz.open(pdfpath)as doc:
        raw={}
        for pn,p in data['pages'].items():
            page=doc[int(pn)-1];ds=page.get_drawings();tt=page.get_texttrace();raw[pn]=(ds,tt)
            grid=[d for d in ds if d.get('layer')and ('GRID'in d['layer'].upper()or 'AXIS'in d['layer'].upper())and 'IDEN'not in d['layer'].upper()]
            vv,hh=reg.grid_clusters(None,layers=None,drawings=grid,minlen=50)
            if vv!=p['raw_grid_v']or hh!=p['raw_grid_h']or reg.register_free(vv,hh)!=p['transform']:raise ValueError('VSC original freegrid registration changed')
            for g in p['grid_primitives']:
                d=ds[g['drawing']]
                if d.get('layer')!=g['layer']or _items(d['items'])!=g['items']:raise ValueError('VSC raw grid operator changed')
            for tag in p['legend_tags']:
                if not _text_guard(tt,tag):raise ValueError('VSC original legend tag changed')
        for row in list(data['records'].values())+list(data['additions'].values()):
            s=row['source'];ds,tt=raw[s['source_page'].split(':')[1]]
            if _sha(s)!=row['source_record_sha256']:raise ValueError('VSC source record fingerprint changed')
            if not(len(s['source_drawing_indices'])==len(s['source_raw_items'])==len(s['source_pdf_points'])):raise ValueError('VSC primitive ledger shape changed')
            for di,items,pts,typ in zip(s['source_drawing_indices'],s['source_raw_items'],s['source_pdf_points'],s['source_raw_types']):
                d=ds[di]
                if d.get('layer')!='M_WS_CW'or d['type']!=typ or _items(d['items'])!=items or _items(lib.flat_path(d))!=pts:raise ValueError('VSC original whole symbol primitive changed')
            if s['source_tag']and not _text_guard(tt,s['source_tag']):raise ValueError('VSC original field tag changed')
            if s['source_key']and not _text_guard(tt,s['source_key']):raise ValueError('VSC original key changed')
            for contact in s['source_pipe_contact']:
                d=ds[contact['drawing_index']];it=d['items'][contact['item_index']]
                if d.get('layer')!='M_WS_CW'or it[0]!='l'or _items(it[1:])!=contact['points']:raise ValueError('VSC source pipe context changed')
    return True


def _identity(e,row):
    return (e['id'],e['c'],e['t'],e['l'],e.get('m'))==(row['id'],row['c'],row['t'],row['l'],row['m'])


def _base(e):
    dz=float((e.get('a')or {}).get('ceil_dz',0))
    return [round(z-dz,3)for z in e['g'][6:8]]


def _guard(e,row,addition=False):
    allowed=[row['after_g'][:6]]if addition else [row['before_g'][:6],row['after_g'][:6]]
    return e['g'][:6]in allowed and _base(e)==row['assumed_base_Z_procedural_guard']


def _attrs(row):
    s=copy.deepcopy(row['source']);code=s['source_code']
    s.update(sys='cold',source_locked_xy=True,source_valve_record=row['id'],source_record_sha256=row['source_record_sha256'],
             source_anchor='whole_valve_graphic_bbox_centre_not_port',source_graphic_bbox_verified=True,source_graphic_rotation_verified=True,
             source_semantics_checked=True,source_class_semantics_checked=True,source_graphic_family_verified=True,source_graphic_subtype_verified=code!='UNKNOWN_VALVE',
             source_subtype_verified=False,source_rotation_verified=False,source_dimensions_verified=False,source_Z_verified=False,
             source_material_verified=False,source_colour_verified=False,source_mount_verified=False,source_contact_verified=False,source_ports_verified=False,
             source_installation_verified=False,source_operational_verified=False,source_unit_verified=False,
             source_geometry_role='display_bbox_proxy_for_water_valve_plan_symbol',source_geometry_review='body_graphic_only',
             source_body_dimensions_assumed=True,source_height_assumed=True,no_connectors=True,no_hangers=True,
             size_cm=str(round(row['after_g'][3],1))+'×'+str(round(row['after_g'][4],1)),
             source_installation_status='source_provision_only_installation_unverified'if s['source_provision_only']else 'installation_unverified',
             mount_gap='الرمز في موضعه المرسوم؛ لا تفصيل تثبيت أو منفذ أو Z مصدرية فريدة لهذه العلامة.',
             assumed='المركز ومقاس/زاوية بصمة الرمز من PDF فقط؛ صندوق العرض ليس غلاف صمام تنفيذيًا. Z الحالية إجرائية افتراضية ومواد/ألوان العرض غير مثبتة. تماس CW هنا رسومي؛ لا منفذ أو تدفق أو تركيب وتشغيل معتمد. لم تُخترع وصلة أو دعامة ولم ينقل إلى أقرب جدار.')
    if code=='UNKNOWN_VALVE':s['source_subtype_gap']='رمز صمام مياه عام على CW؛ لا IV/GV/NRV ميداني فريد يثبت النوع التفصيلي.'
    if s['source_provision_only']:s['source_provision_note']='FOR PROVISION بالمخطط: تجهيز مستقبلي فقط؛ ليس دليل تركيب صمام أو فتح دائرة تشغيل.'
    return s


def _ref(M,text):
    sp=M.setdefault('sp',[])
    if text not in sp:sp.append(text)
    return sp.index(text)


def apply(M,els=None):
    els=M['els']if els is None else els
    text=DATA_PATH.read_text(encoding='utf-8');data=json.loads(text);pdf=Path(data['source_pdf']);st=pdf.stat();_verify(text,str(pdf),st.st_mtime_ns,st.st_size)
    by={e['id']:e for e in els};count={}
    for e in els:count[e['id']]=count.get(e['id'],0)+1
    unexpected=[eid for eid in by if '-VSC'in eid and eid not in data['additions']]
    if unexpected:raise ValueError('VSC unexpected namespace identity: '+','.join(unexpected))
    for eid,row in data['records'].items():
        e=by.get(eid)
        if e is None or count[eid]!=1 or not _identity(e,row)or not _guard(e,row):raise ValueError('VSC exact existing identity/geometry guard failed: '+eid)
    for eid,row in data['additions'].items():
        e=by.get(eid)
        if e is not None and (count[eid]!=1 or not _identity(e,row)or not _guard(e,row,True)):raise ValueError('VSC exact added identity/geometry guard failed: '+eid)
        proto=by[row['prototype_id']]
        if _base(proto)!=row['assumed_base_Z_procedural_guard']:raise ValueError('VSC same-level assumed Z prototype guard failed: '+eid)
    changes=[];added=[]
    for eid,row in list(data['records'].items())+list(data['additions'].items()):
        e=by.get(eid)
        if e is None:
            e=copy.deepcopy(by[row['prototype_id']]);e.update(id=eid,c=row['c'],t=row['t'],l=row['l'],m=row['m']);els.append(e);by[eid]=e;added.append(eid)
            for key in ['u','u2']:e.pop(key,None)
        before=copy.deepcopy(e['g']);e['g']=copy.deepcopy(row['after_g'][:6])+copy.deepcopy(before[6:8]);a=e.setdefault('a',{})
        for key in ['mount_note','guess_from','guess_host','guess_kind','guess_cm','guess_conf','snap_cm','snap_note']:a.pop(key,None)
        a.update(_attrs(row));e.pop('q',None);e['mark']=row['source']['source_code']if row['source']['source_code']!='UNKNOWN_VALVE'else 'صمام — نوع معلق'
        refs=[f"{row['source']['source_page']} طبقة M_WS_CW: رمز صمام المصدر، raw {','.join(map(str,row['source']['source_drawing_indices']))}",'موضع/مقاس/زاوية رسم فقط؛ Z/مادة/جسم/تثبيت/ports وتشغيل غير مثبتة']
        if row['source']['source_provision_only']:refs.append('FOR PROVISION: تجهيز مستقبلي بالمصدر؛ ليس تركيبًا منفذًا')
        e['s']=[_ref(M,r)for r in refs]
        if before!=e['g']:changes.append({'id':eid,'before_g':before,'after_g':copy.deepcopy(e['g']),'source_record_sha256':row['source_record_sha256']})
    stats={**data['summary'],'source_data_sha256':_FROZEN_DATA_SHA,'scope_ar':data['scope_ar'],'added_this_apply':added,'changed_this_apply':len(changes),'changes':changes,'pending_subtype_ids':[r['id']for r in data['additions'].values()if r['source']['source_code']=='UNKNOWN_VALVE']}
    M.setdefault('meta',{})['water_valve_source']=stats
    return stats


build=apply
