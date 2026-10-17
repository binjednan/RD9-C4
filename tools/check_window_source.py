# -*- coding: utf-8 -*-
"""Read-only original-PDF checks for111 raw window anchors and relative heights.

The2776 modelparts remain derived_excluded: only their aggregate anchor,
literal schedulewidth and relative envelope are checked. This is not a claim
of2776 independently drawn physicalparts, absoluteZ, frame depth or mounting.
"""
import collections
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'pipeline/data/window_source_xy.json'
TOL = .2
_WIDTHS = {7: [12,18], 8: [31,33], 9: [47,48], 10: list(range(73,80)),
           11: list(range(117,124)), 12: [139,140,141], 13: [159,160,161,162],
           14: [177,178,179,180], 15: [8,9,10], 16: [27,28,29],
           17: [48,49,50], 18: [66,67,68], 19: [81]}
_ROWS = {7:[13,14,15],8:[32,29,30],9:[46,45,44],10:[69,70,71],
         11:[114,115,116],12:[135,136,137],13:[156,157,158],14:[184,183,182],
         15:[11,12,13],16:[30,31,32],17:[45,46,47],18:[63,64,65]}


def _items(value):
    import fitz
    if isinstance(value, fitz.Point): return [value.x, value.y]
    if isinstance(value, fitz.Quad): return [[p.x,p.y] for p in value]
    if isinstance(value, fitz.Rect): return list(value)
    if isinstance(value, (list,tuple)): return [_items(p) for p in value]
    return value


def _paths(drawing):
    """Exact line/quad loops, no curve approximation used as a window plane."""
    out=[]; current=[]
    def flush():
        nonlocal current
        if len(current)>1: out.append(current)
        current=[]
    for op in drawing['items']:
        if op[0]=='l':
            a,b=_items(op[1]),_items(op[2])
            if current and math.dist(current[-1],a)<1e-4: current.append(b)
            else: flush(); current=[a,b]
        elif op[0]=='qu':
            flush();q=op[1];p=[_items(q.ul),_items(q.ur),_items(q.lr),_items(q.ll)];out.append(p+[p[0]])
        elif op[0]=='re':
            flush();r=op[1];out.append([[r.x0,r.y0],[r.x1,r.y0],[r.x1,r.y1],[r.x0,r.y1],[r.x0,r.y0]])
        else: flush()
    flush();return out


def _original(page):
    from shapely.geometry import Polygon,Point
    sys.path.insert(0,str(ROOT/'pipeline'))
    import reg
    drawings=page.get_drawings();text=page.get_texttrace()
    grid=[d for d in drawings if d.get('layer') and ('GRID' in d['layer'].upper() or 'AXIS' in d['layer'].upper()) and 'IDEN' not in d['layer'].upper()]
    vv,hh=reg.grid_clusters(None,layers=None,drawings=grid,minlen=50)
    transform=reg.register_free(vv,hh)
    def xy(p): return [p[0]*transform['s']+transform['ox'],transform['oy']-p[1]*transform['s']]
    raw=[i for i,d in enumerate(drawings) if d.get('layer')=='A-GALZ']
    remaining=set(raw);components=[]
    # Independent floodfill directly from original component bboxes.
    while remaining:
        seed=min(remaining);remaining.remove(seed);group=[seed];stack=[seed]
        while stack:
            i=stack.pop();a=drawings[i]['rect']+(-1,-1,1,1)
            for j in list(remaining):
                if a.intersects(drawings[j]['rect']+(-1,-1,1,1)):
                    remaining.remove(j);group.append(j);stack.append(j)
        components.append(sorted(group))
    if len(components)!=25:raise ValueError('Original window symbol inventory differs from25')
    rows=[]
    for indices in components:
        boxes=[drawings[i]['rect'] for i in indices]
        full=[min(b[k] for b in boxes) for k in (0,1)]+[max(b[k] for b in boxes) for k in (2,3)]
        middle=xy([(full[0]+full[2])/2,(full[1]+full[3])/2]);x,y=middle
        side='W' if x<200 else 'E' if x>3100 else 'S' if y<0 else 'N' if y>1800 else None
        if side is None:continue
        axis=1 if side in 'WE' else 0;normal=1-axis;closed=[];bands=[]
        for di in indices:
            d=drawings[di]
            for pi,path in enumerate(_paths(d)):
                if len(path)>3 and math.dist(path[0],path[-1])<1e-4:closed.append((di,pi,path))
            b=d['rect']
            if len(d['items'])==1 and d['items'][0][0]=='qu' and min(b.width,b.height)<1 and max(b.width,b.height)>8:
                bands.append({'drawing':di,'poly':0,'pdf_points':_paths(d)[0],'normal_plane_pdf':(b[normal]+b[normal+2])/2})
        if not closed or not bands or max(q['normal_plane_pdf'] for q in bands)-min(q['normal_plane_pdf'] for q in bands)>.001:
            raise ValueError('Closed raw profile or unique glass plane missing')
        pts=[p for di,pi,path in closed for p in path]
        bbox=[min(p[k] for p in pts) for k in (0,1)]+[max(p[k] for p in pts) for k in (0,1)]
        anchor=[0,0];anchor[axis]=(bbox[axis]+bbox[axis+2])/2;anchor[normal]=bands[0]['normal_plane_pdf']
        rows.append({'side':side,'drawing_indices':indices,'closed_profile_primitives':[[di,pi] for di,pi,path in closed],
                     'closed_profile_bbox_pdf':bbox,'bands':bands,'anchor_pdf':anchor,'xy':xy(anchor),
                     'raw_items':[{'drawing':i,'layer':drawings[i].get('layer'),'items':_items(drawings[i]['items'])} for i in indices]})
    tags=[]
    for ti,span in enumerate(text):
        code=''.join(chr(c[0]) for c in span['chars']).strip()
        if span.get('layer')!='A-WINDOW -IDEN' or not code.startswith('CW-'):continue
        b=span['bbox'];p=[(b[0]+b[2])/2,(b[1]+b[3])/2];x,y=xy(p)
        side='W' if x<200 else 'E' if x>3100 else 'S' if y<0 else 'N' if y>1800 else None
        if side is None:continue
        hexes=[]
        for di,d in enumerate(drawings):
            if d.get('layer')=='A-WINDOW -IDEN':
                for pi,path in enumerate(_paths(d)):
                    if len(path)>3 and math.dist(path[0],path[-1])<1e-4 and Polygon(path).covers(Point(p)):
                        hexes.append([di,pi,path])
        if len(hexes)!=1:raise ValueError('CW code is not inside exactly one original taghex')
        tags.append({'side':side,'code':code,'trace':ti,'bbox':list(b),'chars':[[c[0],_items(c[2]),_items(c[3])] for c in span['chars']], 'hex':hexes[0],'xy_identity_only':xy(p)})
    if len(rows)!=23 or len(tags)!=23:raise ValueError('Original facade CW inventory differs from23')
    out={}
    for side in 'WESN':
        ax=1 if side in 'WE' else 0
        symbols=sorted([r for r in rows if r['side']==side],key=lambda r:r['xy'][ax])
        labels=sorted([t for t in tags if t['side']==side],key=lambda t:t['xy_identity_only'][ax])
        if len(symbols)!=len(labels):raise ValueError('Original ordered code/glyph count differs')
        for rank,(r,t) in enumerate(zip(symbols,labels)):
            r.update(tag=t,facade_ordinal=rank);out[(side,rank)]=r
    return out,transform,vv,hh


def _literal(span):
    return ''.join(chr(c[0]) for c in span['chars']).strip()


def _schedule(data):
    import fitz
    pdf=Path('/Users/binqdair/Downloads/Arch. Drawings Part II.pdf')
    out={};checks=[]
    with fitz.open(pdf) as doc:
        text14=doc[13].get_texttrace();text15=doc[14].get_texttrace()
        for number,indices in _WIDTHS.items():
            text=text14 if number<=14 else text15
            values=[float(_literal(text[i])) for i in indices]
            if number==19:
                # PDF emission order differs from physical top-to-bottom order.
                row_indices=sorted(range(82,99),key=lambda i:text15[i]['bbox'][1])
                rows=[float(_literal(text15[i])) for i in row_indices];height=sum(rows)
            else:
                rows=[float(_literal(text[i])) for i in _ROWS[number]];height=sum(rows)
            code='CW-'+str(number).zfill(2)
            out[code]={'width':sum(values),'height':height,'rows':rows,'widths':values,'width_texttrace_indices':indices,'source_page':'ARCH2:14' if number<=14 else 'ARCH2:15'}
            expected=data['schedule']['PAT'].get(code)
            errors=[]
            if number==19:
                if rows!=[float(h) for kind,h in data['schedule']['CW19']][::-1]:errors.append('Raw CW19 printed row heights differ')
            elif not expected or values!=expected['cols'] or rows!=[60.,140.,50.]:errors.append('Raw printed widths/row heights differ from schedule binding')
            checks.append({'code':code,**out[code],'scope':'printed_dimensions_only_FSV_visually_reviewed_separately','pass':not errors,'errors':errors})
        clear=doc[30].get_texttrace()[29]
        if _literal(clear)!='310':raise ValueError('A1500 floor-to-soffit310 literal changed')
    return out,checks,hashlib.sha256(pdf.read_bytes()).hexdigest()


def audit(M):
    # Rehydrate external audit inputs; geometry remains the live model.
    import sys as _audit_sys
    from pathlib import Path as _AuditPath
    _audit_sys.path.insert(0, str(_AuditPath(__file__).resolve().parents[1] / 'pipeline'))
    from source_audit_sidecar import audit_model as _source_audit_model
    M = _source_audit_model(M)
    import fitz
    data=json.loads(DATA_PATH.read_text(encoding='utf-8'))
    pdf=Path(data['source_pdf']);pdf_sha=hashlib.sha256(pdf.read_bytes()).hexdigest()
    groups=collections.defaultdict(list)
    for e in M['els']:
        if e['c']=='A.win' and e.get('grp') in data['units']:groups[e['grp']].append(e)
    schedule,schedulechecks,schedule_sha=_schedule(data)
    checks=[];pages={};parts=[]
    with fitz.open(pdf) as doc:
        for pn in [6,7]:pages[pn]=_original(doc[pn-1])
        for grp,u in data['units'].items():
            pn=int(u['source_page'].split(':')[1]);raw,T,vv,hh=pages[pn];r=raw[(u['side'],u['facade_ordinal'])]
            els=groups[grp];s=u['source_anchor'];errors=[]
            q={'id':grp,'ids':[e['id'] for e in els],'reference':u['source_page'],'source_kind':'window_assembly_anchor_from_raw_closed_graphic',
               'method':'Original A-GALZ component/profile tangentcentre and unique closedglazingplane; original CWtag insidehex, facadeordinal identity',
               'proof_scope':'assembly_anchor_XY_schedule_width_and_relative_height_only','absolute_Z_frame_depth_material_mounting_accepted':False,
               'source_xy':r['xy'],'source_anchor_pdf':r['anchor_pdf'],'source_primitives':r['drawing_indices']}
            if not els:
                errors.append('Missing111 source group');q.update(errors=errors,pass_=False);q['pass']=False;checks.append(q);continue
            if pdf_sha!=data['source_pdf_sha256']:errors.append('Original PDF fingerprint changed')
            if [e['id'] for e in els] != u['model_member_ids']:
                errors.append('Procedural member identities/order changed; source geometry proof does not authorize nearest-ID reassignment')
            if r['tag']['code']!=u['code'] or any(e['l']!=u['level'] or (e.get('a') or {}).get('source_window_group')!=grp for e in els):errors.append('Raw code/facadeordinal/level identity differs')
            rawpairs=[('drawing_indices','drawing_indices'),('closed_profile_primitives','closed_profile_primitives'),('closed_profile_bbox_pdf','closed_profile_bbox_pdf'),('bands','bands'),('raw_items','raw_items')]
            if any(s[k]!=r[v] for k,v in rawpairs):errors.append('Raw complete glyph/profile/plane primitive identity differs')
            if (s['tag']['texttrace_index']!=r['tag']['trace'] or s['tag']['code']!=r['tag']['code'] or s['tag']['tag_hex']!=r['tag']['hex'] or s['tag']['chars']!=r['tag']['chars']):errors.append('Original taghex/texttrace/code differs')
            if data['pages'][str(pn)]['registration']!=T or data['pages'][str(pn)]['grid_pdf_v']!=vv or data['pages'][str(pn)]['grid_pdf_h']!=hh:errors.append('Fresh original registration differs')
            source_sha=hashlib.sha256(json.dumps(s,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
            if u['source_record_sha256']!=source_sha:errors.append('Data source record fingerprint differs')
            frames=[e for e in els if (e.get('a') or {}).get('part')=='frame']
            if not frames or any(e['g'][0]!='r' for e in els):errors.append('Expected derived frame rectangle envelope missing')
            else:
                bbox=[min(e['g'][k] for e in frames) for k in (1,2)]+[max(e['g'][k] for e in frames) for k in (3,4)]
                actual=[(bbox[0]+bbox[2])/2,(bbox[1]+bbox[3])/2];delta=math.dist(actual,r['xy'])
                normal=0 if u['side'] in 'WE' else 1
                tangent=1-normal
                width=bbox[3]-bbox[1] if u['side'] in 'WE' else bbox[2]-bbox[0]
                low=min(e['g'][5] for e in frames);high=max(e['g'][6] for e in frames)
                height=(high-low)*100;expected=schedule[u['code']]
                if delta>TOL:errors.append('Assembly anchor differs from original glyph beyond0.2cm')
                if abs(width-expected['width'])>TOL:errors.append('Schedule width differs from literal dimension')
                if abs(height-expected['height'])>TOL:errors.append('Relative outer height differs from literal dimension')
                q.update(deviation_cm=delta,normal_plane_deviation_cm=abs(actual[normal]-r['xy'][normal]),
                         tangent_centre_deviation_cm=abs(actual[tangent]-r['xy'][tangent]),
                         actual_anchor=actual,relative_height_cm=height,literal_height_cm=expected['height'],literal_width_cm=expected['width'],width_deviation_cm=abs(width-expected['width']))
            for e in els:
                a=e.get('a') or {}
                if (a.get('source_window_member_identity') != e['id'] or
                        a.get('source_page') != u['source_page'] or a.get('source_pdf_sha256') != pdf_sha or
                        e['t'] != ('win_sill' if a.get('part')=='sill' else u['type'])):
                    errors.append('Model member/code/PDF identity differs: '+e['id'])
                if (a.get('source_drawing_indices')!=r['drawing_indices'] or a.get('source_closed_profile_primitives')!=r['closed_profile_primitives'] or a.get('source_glazing_bands')!=r['bands'] or a.get('source_transform')!=T or a.get('source_record_sha256')!=source_sha or a.get('source_tag_hex_drawing')!=r['tag']['hex'][0] or a.get('source_tag_texttrace')!=r['tag']['trace']):errors.append('Model metadata raw binding differs: '+e['id'])
                if math.dist(a.get('source_xy',[1e10,1e10]),r['xy'])>TOL or a.get('source_anchor_pdf')!=r['anchor_pdf']:errors.append('Model metadata anchor differs: '+e['id'])
                if any(a.get(k) for k in ['source_absolute_Z_verified','source_Z_verified','source_frame_width_depth_verified','source_material_assignment_verified','source_material_verified','source_mount_verified','source_dimensions_verified','source_body_part_independently_drawn']):errors.append('Unsafe promotion of physical body/Z/material/mounting: '+e['id'])
                parts.append({'id':e['id'],'source_group':grp,'source_kind':'derived_window_assembly_part','status':'derived_excluded','scope':'group_anchor_and_relative_envelope_checked_not_independent_part_geometry'})
            q.update(metadata_deviation_cm=max(math.dist((e.get('a') or {}).get('source_xy',[1e10,1e10]),r['xy']) for e in els),errors=errors)
            q['pass']=not errors;checks.append(q)
    return {'checks':checks,'derived':parts,'schedule_checks':schedulechecks,'summary':{'checked':len(checks),'raw_anchor_checks':len(checks),'relative_height_checks':len(checks),'derived_excluded':len(parts),'findings':sum(not q['pass'] for q in checks)+sum(not q['pass'] for q in schedulechecks),'uncovered':sum('Missing111 source group' in q['errors'] for q in checks),'max_deviation_cm':max(q.get('deviation_cm',0) for q in checks),'source_PDF_sha256':pdf_sha,'schedule_PDF_sha256':schedule_sha,'source_data_sha256':hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),'source_absolute_Z_physical_frame_material_mounting_accepted':False}}
