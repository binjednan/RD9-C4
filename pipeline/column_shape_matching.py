"""Bounded C1 column source matching and one planted-column identity correction."""
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import reg

DATA_PATH=Path(__file__).with_name('data')/'column_shape_matching.json'
DATA_SHA256='7039f059d407e8671e7d6377a31824d10d4af54a4f2b3caa99a727ac1c0edc98'
TYPES={}
PROOF_FILE='../review-evidence/column-shape-matching/source-proof.json'
IDENTITY_ISSUE='CM-COLUMN-G0072-IDENTITY'
SPAN_ISSUE='CM-COLUMN-G0072-PLANTED-SPAN'


def digest(v):
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def geometry_sha(e):return digest([e['id'],e['c'],e['t'],e['l'],e['g']])


def data():
    raw=DATA_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=DATA_SHA256:
        raise ValueError('Column matching source ledger changed')
    return json.loads(raw)


def _serial(v):
    if isinstance(v,(str,int,float,bool)) or v is None:return v
    return [_serial(x) for x in v]


def _drawing(ds,i):
    d=ds[i]
    return {'index':i,**{k:_serial(d.get(k)) for k in ('layer','type','rect','items','fill','color','closePath')}}


def _trace(ts,i):
    t=ts[i]
    return {'index':i,'text':''.join(chr(c[0]) for c in t['chars']),'bbox':_serial(t['bbox']),'layer':t.get('layer'),'chars':_serial(t['chars'])}


def _quad(d,T):
    assert d['layer']=='S-COLUMN' and len(d['items'])==1 and d['items'][0][0]=='qu'
    q=d['items'][0][1]
    return [list(T(p.x,p.y)) for p in (q.ul,q.ur,q.lr,q.ll)]


def _bounds(xy):
    return [min(p[0] for p in xy),min(p[1] for p in xy),max(p[0] for p in xy),max(p[1] for p in xy)]


def _cyclic_equal(a,b):
    return len(a)==len(b) and any(a==q[i:]+q[:i] for q in (b,list(reversed(b))) for i in range(len(q)))


def _raw_sources(D):
    import fitz
    path=Path(os.environ.get('C4_STR_PDF',D['source_pdf']['path']))
    assert hashlib.sha256(path.read_bytes()).hexdigest()==D['source_pdf']['sha256'],'Original STR PDF changed'
    doc=fitz.open(path);raw={};regs={}
    for n,s in D['pages'].items():
        p=doc[int(n)-1];ds=p.get_drawings();ts=p.get_texttrace();ws=p.get_text('words');aa=list(p.annots() or [])
        for r in s['drawings']:assert _drawing(ds,r['index'])==r
        for r in s['traces']:assert _trace(ts,r['index'])==r
        for r in s['words']:assert list(ws[r['index']])==r['word']
        for r in s['annotations']:
            a=aa[r['index']]
            assert {'index':r['index'],'xref':a.xref,'rect':list(a.rect),'content':a.info['content'],'id':a.info['id']}==r
        raw[int(n)]={'drawings':ds,'traces':ts,'words':ws}
        if 'registration' in s:
            grids=[d for d in ds if d.get('layer') and ('GRID' in d['layer'].upper() or 'AXIS' in d['layer'].upper()) and 'IDEN' not in d['layer'].upper()]
            vv,hh=reg.grid_clusters(None,layers=None,drawings=grids,minlen=50)
            regs[int(n)]=reg.register_free(vv,hh)
            assert regs[int(n)]==s['registration']
    text=lambda n,i:_trace(raw[n]['traces'],i)['text']
    assert text(12,52)=='CL.- 3.9' and text(12,53)=='TOP'
    assert text(20,119)=='C.L. -0.10' and 'THICKNESS IS 35CMS' in text(20,24)
    assert text(20,231)=='C.L (-0.45)'
    assert text(21,108)=='C.L. +5.65' and 'THICKNESS IS 28CMS' in text(21,1)
    assert text(21,171)=='C.L (+5.37)'
    z={'B':[-3.9,round(-.1-35/100,2)],'G':[-.1,round(5.65-28/100,2)]}
    # Schedule dimensions are vector SHX glyphs, visually transcribed and guarded
    # above by their original operators. The NTS detail is never scaled.
    sch=D['visually_read_schedule']
    assert sch['scale']=='NTS' and sch['C1']['literal_dimensions_cm']==[30,160]
    assert sch['C9']['literal_dimensions_cm']==[20,160]
    assert D['pages']['25']['annotations'][0]['content']=='DETAIL OF COLUMN-C1'
    assert D['pages']['25']['annotations'][1]['content']=='DETAIL OF COLUMN-C9'
    return raw,regs,z


def audit(M):
    D=data();raw,regs,z=_raw_sources(D)
    by={}
    for e in M['els']:by.setdefault(e['id'],[]).append(e)
    results=[];checks=[];conflicts=[]
    for eid,r in D['records'].items():
        if len(by.get(eid,[]))!=1:raise ValueError('Column identity missing/duplicate: '+eid)
        e=by[eid][0]
        if (e['c'],e['t'],e['l'],e.get('mark'))!=(r['category'],r['type'],r['level'],'C1'):
            raise ValueError('C1 identity changed: '+eid)
        n=r['page'];xy=_quad(raw[n]['drawings'][r['drawing_index']],reg.make_T(regs[n]))
        word=raw[n]['words'][r['C1_word_index']]
        assert word[4]=='C1'
        rounded=[[round(x,1),round(y,1)] for x,y in xy]
        expected=['p',rounded,*z[e['l']]]
        # The ledger must agree with independent reconstruction, not vice versa.
        assert expected==r['before_g'] and digest(expected)==r['geometry_sha256']
        g=e['g'];kind_ok=g[0]=='p' and len(g) in (4,5) and not (g[4] if len(g)>4 else None)
        footprint_ok=kind_ok and _cyclic_equal(g[1],rounded)
        z_ok=kind_ok and g[2:4]==z[e['l']]
        matched=footprint_ok and z_ok
        refs=[f'STR:{n} '+D['pages'][str(n)]['drawing_id'],'STR:25 S-20 C1']+[f'STR:{p} '+D['pages'][str(p)]['drawing_id'] for p in r['z_source_pages']]
        ids=[] if matched else ['CM-COLUMN-'+eid.replace('.','-')+'-POSITION-SHAPE']
        result={'id':eid,'element_id':eid,'status':'matched' if matched else 'conflict',
                'position_checked':True,'shape_checked':True,'position_match':matched,'shape_match':matched,
                'source_refs':refs,'evidence':{'raw_plan_drawing':r['drawing_index'],'source_C1_word':r['C1_word_index'],
                    'source_g':expected,'registered_footprint_match':footprint_ok,'absolute_z_match':z_ok,
                    'source_shape':'constant rectangular C1 concrete column segment'},
                'proof_file':PROOF_FILE,'conflict_ids':ids,'geometry_sha256':geometry_sha(e)}
        results.append(result)
        b=_bounds(xy);dims=sorted([b[2]-b[0],b[3]-b[1]])
        checks.append({'id':eid,'raw_registered_dimensions_cm':dims,'literal_section_cm':[30,160],
                       'registered_minus_literal_cm':[dims[0]-30,dims[1]-160],
                       'expected_z_m':z[e['l']],'matched':matched})
        if ids:
            conflicts.append({'id':ids[0],'title':'اختلاف جسم العمود '+eid+' عن المسقط والمناسيب المصدرية',
                'status':'confirmed_model_error','source':' / '.join(refs),'elements':[eid],
                'before':{'g':copy.deepcopy(g)},'after':{'source_expected_g':expected},
                'note':'أكمل الفحص بقية الأعمدة؛ لم يغيّر هذا الفحص جسم العنصر المختلف.'})
    # The ninth outline is horizontal and unfilled in the ground plan; upper
    # plan labels the same registered horizontal column C9, not vertical C1.
    r=D['identity_correction'];eid=r['id']
    if len(by.get(eid,[]))!=1:raise ValueError('Planted column identity missing/duplicate: '+eid)
    e=by[eid][0];before=r['before_identity'];after=r['after_identity']
    if e['c']!='S.col' or e['l']!='G' or (e['t'],e.get('mark')) not in [(before['type'],before['mark']),(after['type'],after['mark'])]:
        raise ValueError('Planted column identity changed: '+eid)
    ground=_quad(raw[16]['drawings'][2106],reg.make_T(regs[16]))
    upper=_quad(raw[17]['drawings'][1223],reg.make_T(regs[17]))
    assert raw[17]['words'][45][4]=='C9'
    # Same documented grid bay and centroid rounded to printed centimetres;
    # this proves the type association, not an approved ground-floor Z span.
    gb,ub=_bounds(ground),_bounds(upper)
    gc=[(gb[i]+gb[i+2])/2 for i in range(2)];uc=[(ub[i]+ub[i+2])/2 for i in range(2)]
    assert [round(v) for v in gc]==[round(v) for v in uc]
    assert gb[2]-gb[0]>gb[3]-gb[1] and ub[2]-ub[0]>ub[3]-ub[1]
    original_ground=['p',[[round(x,1),round(y,1)] for x,y in ground],-.1,5.37]
    assert original_ground==r['before_e']['g']
    geometry_same=digest(e['g'])==r['geometry_sha256']
    results.append({'id':eid,'element_id':eid,'status':'conflict','position_checked':True,'shape_checked':True,
        'position_match':False,'shape_match':False,'source_refs':['STR:16 S-11 raw2106','STR:17 S-12 raw1223 / C9 word45','STR:25 S-20 C9'],
        'evidence':{'identity':'planted plan outline associated with upper C9','ground_geometry_retained':geometry_same,
                    'ground_centroid_cm':gc,'upper_centroid_cm':uc,'centroid_difference_cm':math.dist(gc,uc),
                    'ground_z_m':e['g'][2:4] if e['g'][0]=='p' else None,'ground_Z_source_confirmed':False},
        'proof_file':PROOF_FILE,'conflict_ids':[SPAN_ISSUE],'geometry_sha256':geometry_sha(e)})
    conflicts.append({'id':SPAN_ISSUE,'title':'امتداد العمود المزروع C9 داخل الدور الأرضي يحتاج مطابقة تفصيل الزراعة',
        'status':'source_gap','source':'STR ص16 S-11 رسم2106 / ص17 S-12 رسم1223 / ص25 S-20 C9',
        'elements':[eid],'note':r['limits_ar'],
        'before':{'g':copy.deepcopy(e['g'])},'after':{'geometry_retained':geometry_same,'position_shape_matched':False}})
    return {'schema':'c4.column-shape-matching-audit.v1','pass':True,'data_sha256':DATA_SHA256,
            'source_pdf_sha256':D['source_pdf']['sha256'],'results':results,'records':results,
            'matched_count':sum(q['status']=='matched' for q in results),'conflict_count':sum(q['status']=='conflict' for q in results),
            'conflicts':conflicts,'checks':checks,'registrations':regs,'source_z_boundaries':z,
            'model_metadata_used_as_proof':False,'source_schedule_NTS_scaled':False,
            'visual_schedule_transcription':copy.deepcopy(D['visually_read_schedule']),
            'scope_ar':'الموقع والشكل لأجسام الأعمدة المحددة؛ لا تسليح أو مواد توريد أو تثبيت أو تشغيل أو اعتماد ميداني.'}


def apply(M,els=None):
    if els is not None and els is not M['els']:
        proxy=dict(M,els=els)
    else:proxy=M
    D=data();r=D['identity_correction'];by={}
    for e in proxy['els']:by.setdefault(e['id'],[]).append(e)
    if len(by.get(r['id'],[]))!=1:raise ValueError('Column correction identity missing/duplicate')
    e=by[r['id']][0]
    if digest(e['g'])!=r['geometry_sha256']:
        raise ValueError('Planted column exact geometry guard failed')
    proof=audit(proxy)  # all source and identity guards precede the only edit
    before_hash=geometry_sha(e);before={'type':e['t'],'mark':e.get('mark')}
    changed=before!=r['after_identity']
    e['t']=r['after_identity']['type'];e['mark']=r['after_identity']['mark']
    e.setdefault('a',{}).update(
        column_shape_identity_correction=True,
        source_identity_kind='derived_from_planted_and_upper_column_plans',
        source_identity_reference='STR:16 S-11 raw2106 / STR:17 S-12 raw1223 and C9 word45 / STR:25 S-20 C9',
        source_identity_note='الوسم C1 يخص العمود الرأسي المجاور؛ الجسم الأفقي المزروع يطابق C9 في المسقط العلوي.',
        source_identity_caveat=r['limits_ar'],
        column_identity_data_sha256=DATA_SHA256,
        source_ground_vertical_span_verified=False,
    )
    after_hash=geometry_sha(e)
    for q in proof['results']:
        if q['id']==e['id']:q['geometry_sha256']=after_hash
    proof.update(identity_changed=int(changed),identity_changed_ids=[e['id']] if changed else [],
        identity_correction={'id':e['id'],'before':before,'after':copy.deepcopy(r['after_identity']),
                             'before_identity_geometry_sha256':before_hash,'after_identity_geometry_sha256':after_hash,
                             'body_geometry_sha256':digest(e['g']),'geometry_unchanged':True})
    return proof


def issue_records(M,report=None):
    proof=report or audit(M);D=data();r=D['identity_correction']
    e=next(e for e in M['els'] if e['id']==r['id'])
    if (e['t'],e.get('mark'))!=(r['after_identity']['type'],r['after_identity']['mark']):
        raise ValueError('Apply column identity correction before corrected issue')
    return [{'id':IDENTITY_ISSUE,'title':'تصحيح هوية عمود مزروع من C1 إلى الارتباط المثبت بـC9',
        'status':'corrected','source':'STR ص16 رسم2106 / ص17 رسم1223 ووسم C9 / ص25 جدول C9',
        'elements':[r['id']],'before':copy.deepcopy(r['before_identity']),'after':copy.deepcopy(r['after_identity']),
        'note':'تغيرت الهوية فقط. بقي جسم العمود كاملًا وموقعه وامتداده الرأسي كما هي، وسجل تعارض الامتداد في '+SPAN_ISSUE+'.',
        'body_geometry_sha256':digest(e['g'])}]+copy.deepcopy(proof['conflicts'])
