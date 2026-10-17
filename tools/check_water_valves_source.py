"""Original-PDF gate for167 water-valve graphics; physical acceptance excluded."""
import collections
import hashlib
import json
import math
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA_PATH=ROOT/'pipeline/data/water_valve_source.json'
FROZEN_SHA='04dad88b5cb3f4b6d79bf982866bb8d2c3c810c0838ec1c1f4de9beb83b7a73d'
SCHEMA='c4.water-valve-source.v1'
TOL=.2
_BINDINGS_RAW='{\n  "19": [\n    [\n      137,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        5798\n      ]\n    ],\n    [\n      138,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        5815\n      ]\n    ],\n    [\n      141,\n      [\n        0,\n        1\n      ],\n      "GV",\n      [\n        5895\n      ]\n    ],\n    [\n      142,\n      [\n        0,\n        1\n      ],\n      "GV",\n      [\n        5897\n      ]\n    ],\n    [\n      157,\n      [\n        7,\n        8,\n        9\n      ],\n      "NRV",\n      [\n        6690,\n        6691,\n        6692,\n        6693,\n        6694,\n        6695,\n        6696,\n        6697,\n        6698,\n        6699,\n        6700\n      ]\n    ],\n    [\n      157,\n      [\n        10,\n        11\n      ],\n      "IV",\n      [\n        6689\n      ]\n    ],\n    [\n      158,\n      [\n        7,\n        8,\n        9\n      ],\n      "NRV",\n      [\n        6709,\n        6710,\n        6711,\n        6712,\n        6713,\n        6714,\n        6715,\n        6716,\n        6717\n      ]\n    ],\n    [\n      158,\n      [\n        10,\n        11\n      ],\n      "IV",\n      [\n        6708\n      ]\n    ],\n    [\n      167,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        6835\n      ]\n    ],\n    [\n      176,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        6898\n      ]\n    ]\n  ],\n  "20": [\n    [\n      161,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        17514\n      ]\n    ],\n    [\n      165,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        17534\n      ]\n    ],\n    [\n      166,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        17565\n      ]\n    ],\n    [\n      170,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        17762\n      ]\n    ],\n    [\n      173,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        17853\n      ]\n    ],\n    [\n      174,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        17854\n      ]\n    ],\n    [\n      176,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        17865\n      ]\n    ],\n    [\n      179,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        18014\n      ]\n    ],\n    [\n      180,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        18140\n      ]\n    ],\n    [\n      181,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        18174\n      ]\n    ],\n    [\n      182,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        18254\n      ]\n    ],\n    [\n      185,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        18530\n      ]\n    ],\n    [\n      186,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        18531\n      ]\n    ],\n    [\n      187,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        18657\n      ]\n    ],\n    [\n      189,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        18805\n      ]\n    ],\n    [\n      190,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        18909\n      ]\n    ],\n    [\n      192,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        19064\n      ]\n    ],\n    [\n      193,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        19065\n      ]\n    ],\n    [\n      195,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        19169\n      ]\n    ],\n    [\n      199,\n      [\n        7,\n        8,\n        9\n      ],\n      "NRV",\n      [\n        19314,\n        19315,\n        19316,\n        19317,\n        19318,\n        19319,\n        19320,\n        19321,\n        19322,\n        19323\n      ]\n    ],\n    [\n      199,\n      [\n        10,\n        11\n      ],\n      "IV",\n      [\n        19313\n      ]\n    ],\n    [\n      200,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        19336\n      ]\n    ],\n    [\n      213,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        19554\n      ]\n    ]\n  ],\n  "21": [\n    [\n      128,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        18357\n      ]\n    ],\n    [\n      129,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        18500\n      ]\n    ],\n    [\n      130,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        18535\n      ]\n    ],\n    [\n      131,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        18615\n      ]\n    ],\n    [\n      134,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        18891\n      ]\n    ],\n    [\n      135,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        18892\n      ]\n    ],\n    [\n      136,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        19047\n      ]\n    ],\n    [\n      138,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        19246\n      ]\n    ],\n    [\n      139,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        19350\n      ]\n    ],\n    [\n      141,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        19536\n      ]\n    ],\n    [\n      142,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        19537\n      ]\n    ],\n    [\n      144,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        19651\n      ]\n    ],\n    [\n      145,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        19759\n      ]\n    ],\n    [\n      149,\n      [\n        7,\n        8,\n        9\n      ],\n      "NRV",\n      [\n        19979,\n        19980,\n        19981,\n        19982,\n        19983,\n        19984,\n        19985,\n        19986,\n        19987,\n        19988\n      ]\n    ],\n    [\n      149,\n      [\n        10,\n        11\n      ],\n      "IV",\n      [\n        19978\n      ]\n    ],\n    [\n      150,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        20001\n      ]\n    ],\n    [\n      166,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        20349\n      ]\n    ],\n    [\n      186,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        20602\n      ]\n    ],\n    [\n      187,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        20632\n      ]\n    ],\n    [\n      191,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        20682\n      ]\n    ],\n    [\n      192,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        20694\n      ]\n    ],\n    [\n      193,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        20764\n      ]\n    ],\n    [\n      198,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        21123\n      ]\n    ],\n    [\n      199,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        21142\n      ]\n    ],\n    [\n      203,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        21208\n      ]\n    ]\n  ],\n  "22": [\n    [\n      70,\n      [\n        7,\n        8,\n        9\n      ],\n      "NRV",\n      [\n        3544,\n        3545,\n        3546,\n        3547,\n        3548,\n        3549,\n        3550,\n        3551,\n        3552,\n        3553\n      ]\n    ],\n    [\n      70,\n      [\n        10,\n        11\n      ],\n      "IV",\n      [\n        3543\n      ]\n    ],\n    [\n      74,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        3604\n      ]\n    ],\n    [\n      74,\n      [\n        9,\n        10,\n        11\n      ],\n      "NRV",\n      [\n        3615,\n        3616,\n        3617,\n        3618,\n        3619,\n        3620,\n        3621,\n        3622,\n        3623,\n        3624\n      ]\n    ],\n    [\n      74,\n      [\n        12,\n        13\n      ],\n      "IV",\n      [\n        3614\n      ]\n    ],\n    [\n      82,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        3784\n      ]\n    ],\n    [\n      85,\n      [\n        0,\n        1\n      ],\n      "IV",\n      [\n        3853\n      ]\n    ],\n    [\n      85,\n      [\n        2,\n        3\n      ],\n      "IV",\n      [\n        3829\n      ]\n    ],\n    [\n      85,\n      [\n        4,\n        5\n      ],\n      "IV",\n      [\n        3846\n      ]\n    ],\n    [\n      85,\n      [\n        6,\n        7\n      ],\n      "IV",\n      [\n        3854\n      ]\n    ],\n    [\n      85,\n      [\n        8,\n        9\n      ],\n      "IV",\n      [\n        3861\n      ]\n    ],\n    [\n      85,\n      [\n        10,\n        11\n      ],\n      "IV",\n      [\n        3884\n      ]\n    ]\n  ]\n}'
_BINDINGS={int(k):v for k,v in json.loads(_BINDINGS_RAW).items()}
_LEVELS={'G':19,'1':20,'2':21,'3':21,'4':21,'5':21,'R':22}
_OLD_IV={'G':[80,81,83,84],'1':[x for x in range(221,243)if x!=232],'2':[x for x in range(466,489)if x!=470],'3':[x for x in range(712,735)if x!=716],'4':[x for x in range(958,981)if x!=962],'5':[x for x in range(1204,1227)if x!=1208],'R':[71]}


def _items(v):
    import fitz
    if isinstance(v,fitz.Point):return [v.x,v.y]
    if isinstance(v,fitz.Quad):return [[p.x,p.y]for p in v]
    if isinstance(v,fitz.Rect):return list(v)
    if isinstance(v,(tuple,list)):return [_items(q)for q in v]
    return v


def _sha(v):
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def _words(tt):
    # Original char geometry, never an imported annotation centre.
    words=[]
    for ti,t in enumerate(tt):
        dx,dy=t['dir'];size=t['size'];current=[];previous=None
        def flush():
            if not current:return
            cs=[c for i,c in current];txt=''.join(chr(c[0])for c in cs).strip()
            if not txt:return
            bb=[min(c[3][0]for c in cs),min(c[3][1]for c in cs),max(c[3][2]for c in cs),max(c[3][3]for c in cs)]
            words.append({'text':txt,'texttrace_index':ti,'char_indices':[i for i,c in current],'char_codes':[c[0]for c in cs],
                          'char_bboxes':[list(c[3])for c in cs],'layer':t.get('layer'),'bbox':bb,'centre':[(bb[0]+bb[2])/2,(bb[1]+bb[3])/2],
                          'dir':list(t['dir']),'full_trace_text':''.join(chr(c[0])for c in t['chars'])})
        for ci,c in enumerate(t['chars']):
            ch=chr(c[0]);ox,oy=c[2]
            if ch==' ':flush();current=[];previous=None;continue
            if previous is not None:
                p=previous;pt=p[2][0]*dx+p[2][1]*dy;ct=ox*dx+oy*dy
                pp=-p[2][0]*dy+p[2][1]*dx;cp=-ox*dy+oy*dx
                advance=p[3][2]-p[3][0]if abs(dx)>abs(dy)else p[3][3]-p[3][1]
                if ct-pt-abs(advance)>.7*size or abs(cp-pp)>.45*size or ct<pt-.2*size:flush();current=[]
            current.append((ci,c));previous=c
        flush()
    return words


def _raw(page,pn):
    sys.path.insert(0,str(ROOT/'pipeline'));import reg,lib
    ds=page.get_drawings();tt=page.get_texttrace();words=_words(tt)
    grid=[d for d in ds if d.get('layer')and ('GRID'in d['layer'].upper()or 'AXIS'in d['layer'].upper())and 'IDEN'not in d['layer'].upper()]
    vv,hh=reg.grid_clusters(None,layers=None,drawings=grid,minlen=50);T=reg.register_free(vv,hh)
    if not T or T['nx']<4 or T['ny']<3 or T['ex']/T['nx']>=2.2 or T['ey']/T['ny']>=2.2:raise ValueError('No qualified original whole-plan grid')
    tags={(w['texttrace_index'],tuple(w['char_indices'])):w for w in words if w['text']in ('IV','GV','NRV')and w['centre'][1]>600}
    observed=set(tags);expected={(ti,tuple(ci))for ti,ci,code,indices in _BINDINGS[pn]}
    if observed!=expected:raise ValueError('Original complete field abbreviation inventory changed')
    quads={};qfingerprints=[]
    for di,d in enumerate(ds):
        if d.get('layer')!='M_WS_CW'or len(d['items'])!=1 or d['items'][0][0]!='qu':continue
        pts=lib.flat_path(d)[0];w=d['rect'].width;h=d['rect'].height
        area=sum(a[0]*b[1]-a[1]*b[0]for a,b in zip(pts,pts[1:]))
        if abs(area)>.05 or min(w,h)<1 or not(1.5<max(w,h)/min(w,h)<2):continue
        # Exact crossed-quad paths, with both diagonal edges and end caps.
        edges=sorted(tuple(sorted((tuple(a),tuple(b))))for a,b in zip(pts,pts[1:]))
        fingerprint=tuple(edges)
        if fingerprint in qfingerprints:raise ValueError('Unexpected duplicate original valve graphic')
        qfingerprints.append(fingerprint);quads[di]=d
    symbols=[];used=set()
    for ti,ci,code,inds in _BINDINGS[pn]:
        tag=tags[(ti,tuple(ci))]
        if tag['text']!=code:raise ValueError('Field subtype literal changed')
        parts=[ds[i]for i in inds]
        if any(d.get('layer')!='M_WS_CW'for d in parts):raise ValueError('Whole valve graphic layer changed')
        if code in ('IV','GV'):
            if len(inds)!=1 or inds[0]not in quads:raise ValueError('Field IV/GV no longer has its exact whole bow-tie')
            used.add(inds[0])
        else:
            strokes=[op for d in parts if d['type']=='s'for op in d['items']if op[0]=='l']
            diagonal=[op for op in strokes if abs(op[1].x-op[2].x)>.1 and abs(op[1].y-op[2].y)>.1]
            if len(diagonal)!=4 or sum(d['type']=='fs'for d in parts)<3 or len(strokes)<6:raise ValueError('Whole NRV strokes/filled centre anatomy changed')
        symbols.append({'tag':tag,'code':code,'indices':inds,'parts':parts})
    for di,d in quads.items():
        if di not in used:symbols.append({'tag':None,'code':'UNKNOWN_VALVE','indices':[di],'parts':[d]})
    if len(symbols)!={19:10,20:24,21:26,22:29}[pn]:raise ValueError('Original whole symbol quantity changed')
    for q in symbols:
        parts=q['parts'];bb=[min(d['rect'].x0 for d in parts),min(d['rect'].y0 for d in parts),max(d['rect'].x1 for d in parts),max(d['rect'].y1 for d in parts)]
        C=[(bb[0]+bb[2])/2,(bb[1]+bb[3])/2];w=(bb[2]-bb[0])*T['s'];h=(bb[3]-bb[1])*T['s']
        q.update(bbox=bb,anchor_pdf=C,xy=[C[0]*T['s']+T['ox'],T['oy']-C[1]*T['s']],size=[max(w,h),min(w,h)],angle=0 if w>=h else 90,
                 points=[_items(lib.flat_path(d))for d in parts],items=[_items(d['items'])for d in parts],raw_types=[d['type']for d in parts])
    keys={w['text']:w for w in words if w['text']in ('IV','GV','NRV')and w['centre'][0]>1700 and w['centre'][1]<600}
    if set(keys)!=set(('IV','GV','NRV')):raise ValueError('Original abbreviation key missing')
    for code,literal in [('IV','ISOLATING VALVE'),('GV','GATE VALVE'),('NRV','NON RETURN VALVE')]:
        if literal not in keys[code]['full_trace_text']:raise ValueError('Original abbreviation definition changed')
    return {'symbols':symbols,'T':T,'vv':vv,'hh':hh,'drawings':ds,'text':tt,'keys':keys}


def audit(M):
    # Rehydrate external audit inputs; geometry remains the live model.
    import sys as _audit_sys
    from pathlib import Path as _AuditPath
    _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
    from source_audit_sidecar import audit_model as _source_audit_model
    M = _source_audit_model(M)
    import fitz
    data_bytes=DATA_PATH.read_bytes();data=json.loads(data_bytes);pdf=Path(data['source_pdf']);pdfsha=hashlib.sha256(pdf.read_bytes()).hexdigest()
    global_findings=[];checks=[];counts=collections.Counter(e['id']for e in M['els']);by={e['id']:e for e in M['els']};expected_records=set();expected_additions=set()
    if hashlib.sha256(data_bytes).hexdigest()!=FROZEN_SHA:global_findings.append({'kind':'frozen_data_fingerprint','reason':'Frozen original valve ledger changed'})
    if data.get('schema')!=SCHEMA:global_findings.append({'kind':'schema','reason':'Frozen source schema changed'})
    if pdfsha!=data['source_pdf_sha256']:global_findings.append({'kind':'original_pdf','reason':'Original PDF SHA changed'})
    with fitz.open(pdf)as doc:pages={pn:_raw(doc[pn-1],pn)for pn in (19,20,21,22)}
    additions=[];original=[]
    for level,pn in _LEVELS.items():
        P=pages[pn];old_iv=[q for q in P['symbols']if q['code']=='IV'and q['tag']['full_trace_text'].strip()=='IV'];old_iv.sort(key=lambda q:q['tag']['texttrace_index'])
        if len(old_iv)!=len(_OLD_IV[level]):raise ValueError('Original former-emitter identity order changed')
        prefix='P.cold-'+level+('-M'if level in ('G','R')else '-')
        for ordinal,q in zip(_OLD_IV[level],old_iv):original.append((prefix+str(ordinal).zfill(4),level,pn,q))
        old_gv=[q for q in P['symbols']if q['code']=='GV'and q['tag']['full_trace_text'].strip()=='GV']
        if level=='G':
            if len(old_gv)!=1:raise ValueError('Original G gate-valve literal identity order changed')
            original.append(('P.cold-G-M0082',level,pn,old_gv[0]))
        elif old_gv:raise ValueError('Unexpected old GV literal')
        old_keys={tuple(q['indices'])for q in old_iv+old_gv}
        for q in P['symbols']:
            if tuple(q['indices'])not in old_keys:additions.append((level,pn,q))
    additions.sort(key=lambda x:(list(_LEVELS).index(x[0]),min(x[2]['indices']),x[2]['code']))
    entries=[(eid,lev,pn,q,False)for eid,lev,pn,q in original]+[('P.cold-'+lev+'-VSC'+str(n).zfill(4),lev,pn,q,True)for n,(lev,pn,q)in enumerate(additions,1)]
    for eid,level,pn,Q,is_new in entries:
        (expected_additions if is_new else expected_records).add(eid);row=data['additions'if is_new else'records'].get(eid);e=by.get(eid);errors=[];P=pages[pn]
        check={'id':eid,'reference':'MECH2:'+str(pn),'source_kind':'whole_water_valve_graphic_bbox_proxy','source_code':Q['code'],'source_primitives':Q['indices'],'source_xy':Q['xy'],
               'method':'Original whole bow-tie or NRV strokes+filled centre; literal char tags and source context; fresh raw grid; no nearest model body',
               'scope':'graphic_bbox_anchor_angle_only; subtype_only_if_explicit_tag; no physicalbody/Z/material/ports/installation/operation',
               'source_provision_only':Q['code']=='GV','physical_source_acceptance':False}
        if row is None or e is None:
            errors.append('Missing exact original source marker identity');check.update(pass_=False,errors=errors);check['pass']=False;checks.append(check);continue
        s=row['source'];a=e.get('a')or {};code=Q['code'];typ=('valve_source' if M.get('meta',{}).get('owner_render_only') else 'valve_source_graphic')if code=='UNKNOWN_VALVE'else 'valve_'+code
        if (e['c'],e['t'],e['l'],e.get('m'),e['g'][0])!=('P.cold',typ,level,row['m'],'b'):errors.append('Source graphic identity/class/level/material differs')
        if s['source_drawing_indices']!=Q['indices']or s['source_raw_items']!=Q['items']or s['source_pdf_points']!=Q['points']or s['source_raw_types']!=Q['raw_types']:errors.append('Original full symbol operators differ in ledger')
        if a.get('source_drawing_indices')!=Q['indices']or a.get('source_raw_items')!=Q['items']or a.get('source_pdf_points')!=Q['points']:errors.append('Original full symbol operators differ in element metadata')
        if s['source_tag']!=Q['tag']or a.get('source_tag')!=Q['tag']or s['source_code']!=code or a.get('source_code')!=code:errors.append('Original field char/tag subtype binding differs')
        if s['source_key']!=(P['keys'].get(code))or a.get('source_key')!=P['keys'].get(code):errors.append('Original subtype key binding differs')
        if s['source_transform']!=P['T']or a.get('source_transform')!=P['T']or data['pages'][str(pn)]['raw_grid_v']!=P['vv']or data['pages'][str(pn)]['raw_grid_h']!=P['hh']:errors.append('Fresh original raw grid registration differs')
        if pdfsha!=s['source_pdf_sha256']or a.get('source_pdf_sha256')!=pdfsha:errors.append('Original PDF fingerprint differs')
        record_sha=_sha(s)
        if row['source_record_sha256']!=record_sha or a.get('source_record_sha256')!=record_sha:errors.append('Source record fingerprint differs')
        delta=math.dist(e['g'][1:3],Q['xy']);dimension=max(abs(e['g'][3+k]-Q['size'][k])for k in(0,1));rotation=abs(e['g'][5]-Q['angle'])
        metadata=max(math.dist(s['source_xy'],Q['xy']),math.dist(a.get('source_xy',[1e10,1e10]),Q['xy']))
        if delta>TOL:errors.append('Original graphic centre exceeds0.2cm')
        if dimension>TOL:errors.append('Original graphic bbox size exceeds0.2cm')
        if rotation>.001:errors.append('Original graphic rotation differs')
        if metadata>TOL or s['source_bbox_pdf']!=Q['bbox']or s['source_anchor_pdf']!=Q['anchor_pdf']:errors.append('Original graphic bbox/anchor metadata differs')
        # Checking the complete rendered rectangle avoids a centre-only pass.
        gx,gy=e['g'][1:3];ew,eh=e['g'][3:5]
        if e['g'][5]==90:ew,eh=eh,ew
        expected_bb=[Q['bbox'][0]*P['T']['s']+P['T']['ox'],P['T']['oy']-Q['bbox'][3]*P['T']['s'],Q['bbox'][2]*P['T']['s']+P['T']['ox'],P['T']['oy']-Q['bbox'][1]*P['T']['s']]
        extent=max(abs(x-y)for x,y in zip([gx-ew/2,gy-eh/2,gx+ew/2,gy+eh/2],expected_bb))
        if extent>TOL:errors.append('Complete graphic bbox footprint differs beyond0.2cm')
        dz=float(a.get('ceil_dz',0));base=[round(z-dz,3)for z in e['g'][6:8]]
        if base!=row['assumed_base_Z_procedural_guard']:errors.append('Assumed procedural baseZ changed without matching ceil_dz')
        if any(a.get(k)for k in ['source_dimensions_verified','source_Z_verified','source_material_verified','source_colour_verified','source_mount_verified','source_contact_verified','source_ports_verified','source_installation_verified','source_operational_verified','source_subtype_verified','source_rotation_verified']):errors.append('Unsafe physical dimension/Z/material/subtype/mount/ports/operation promotion')
        if not a.get('source_locked_xy')or a.get('source_geometry_review')!='body_graphic_only'or not a.get('no_connectors')or not a.get('no_hangers')or a.get('sys')!='cold' or not a.get('source_graphic_family_verified') or not a.get('source_graphic_bbox_verified') or not a.get('source_graphic_rotation_verified'):errors.append('Graphic source guard/scope metadata missing')
        if a.get('source_provision_only')!=(code=='GV')or a.get('source_installation_status')!=('source_provision_only_installation_unverified'if code=='GV'else'installation_unverified'):errors.append('FOR PROVISION/installation-unverified status differs')
        if code=='UNKNOWN_VALVE'and (a.get('source_graphic_subtype_verified')or not a.get('source_subtype_gap')):errors.append('Unlabelled graphic wrongly accepted as resolved subtype')
        check.update(deviation_cm=delta,graphic_size_deviation_cm=dimension,graphic_angle_deviation_deg=rotation,graphic_full_bbox_deviation_cm=extent,metadata_deviation_cm=metadata,assumed_base_Z_procedural=base,absolute_Z_source_accepted=False,errors=errors)
        check['pass']=not errors;checks.append(check)
    for name,expected in [('records',expected_records),('additions',expected_additions)]:
        actual=set(data[name])
        if actual!=expected:global_findings.append({'kind':'exact_raw_inventory_set','ledger':name,'extra_ids':sorted(actual-expected),'missing_ids':sorted(expected-actual)})
    bad=[eid for eid in expected_records|expected_additions if counts[eid]!=1]
    if bad:global_findings.append({'kind':'identity_multiplicity','ids':sorted(bad)})
    extra_ids=[eid for eid in counts if '-VSC'in eid and eid not in expected_additions]
    if extra_ids:global_findings.append({'kind':'unexpected_source_namespace','ids':sorted(extra_ids)})
    if data.get('pending'):global_findings.append({'kind':'unexpected_pending_ledger','reason':'This frozen inventory qualifies all167 graphics; physical/subtype gaps remain per-record, not new invented source identities'})
    return {'checks':checks,'global_findings':global_findings,'pending_subtype':[q['id']for q in checks if q['source_code']=='UNKNOWN_VALVE'],
            'summary':{'checked':len(checks),'findings':sum(not q['pass']for q in checks)+len(global_findings),'raw_check_findings':sum(not q['pass']for q in checks),'global_findings':len(global_findings),
                       'uncovered':sum('Missing exact original source marker identity'in q['errors']for q in checks),'max_deviation_cm':max(q.get('deviation_cm',0)for q in checks),
                       'max_graphic_full_bbox_deviation_cm':max(q.get('graphic_full_bbox_deviation_cm',0)for q in checks),'source_generic_subtype_pending':22,'source_provision_markers':2,
                       'physical_dimensions_Z_material_mount_ports_operating_accepted':False,'source_pdf_sha256':pdfsha,'source_data_sha256':hashlib.sha256(data_bytes).hexdigest()}}
