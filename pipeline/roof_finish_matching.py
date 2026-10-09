"""Read-only independent plan/section audit of one F12 finish and three upstands.

No source geometry or acceptance flags are read from model metadata. The
expected solids are reconstructed from fresh original PDF primitives, grid
registration, finish-schedule numbers and the two agreeing level drawings.
"""
import hashlib
import json
import os
from pathlib import Path
import re

import reg

DATA_PATH=Path(__file__).with_name('data')/'roof_finish_matching.json'
DATA_SHA256='bc61d0dc937b73a5eba98b126441ad36650a4f03ecc9267b682f068cef6e622b'


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def data():
    raw=DATA_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=DATA_SHA256:
        raise ValueError('Roof matching independent source ledger changed')
    return json.loads(raw)


def _serial(v):
    if isinstance(v,(str,int,float,bool)) or v is None:return v
    return [_serial(x) for x in v]


def _drawing(ds,i):
    d=ds[i]
    return {'index':i,**{k:_serial(d.get(k)) for k in ('layer','type','rect','items','fill','color','closePath')}}


def _trace(ts,i):
    t=ts[i]
    return {'index':i,'text':''.join(chr(c[0]) for c in t['chars']),
            'bbox':_serial(t['bbox']),'layer':t.get('layer'),'chars':_serial(t['chars'])}


def _annotation(aa,i):
    a=aa[i]
    return {'index':i,'xref':a.xref,'rect':list(a.rect),'content':a.info['content'],'id':a.info['id']}


def _line(ds,i):
    ops=ds[i]['items']
    assert len(ops)==1 and ops[0][0]=='l', ('Expected one source line',i)
    return [list(ops[0][1]),list(ops[0][2])]


def _rectangle(x0,y0,x1,y1):
    return [[x0,y0],[x1,y0],[x1,y1],[x0,y1]]


def audit(M):
    import fitz
    D=data()
    docs={}
    for name,r in D['sources'].items():
        path=Path(os.environ.get('C4_'+name+'_PDF',r['path']))
        assert hashlib.sha256(path.read_bytes()).hexdigest()==r['sha256'], 'Original PDF changed: '+name
        docs[name]=fitz.open(path)
    raw={}
    for key in ('plan','section','schedule','structural_level'):
        spec=D[key]; p=docs[spec['source']][spec['page']-1]
        raw[key]={'drawings':p.get_drawings(),'traces':p.get_texttrace(),'words':p.get_text('words')}
        if spec.get('annotations'):
            aa=list(p.annots() or [])
            raw[key]['annotations']={r['index']:_annotation(aa,r['index']) for r in spec['annotations']}
            assert list(raw[key]['annotations'].values())==spec['annotations']
        for r in spec.get('drawings',[]):assert _drawing(raw[key]['drawings'],r['index'])==r
        for r in spec.get('traces',[]):assert _trace(raw[key]['traces'],r['index'])==r
    # Re-register the plan independently from its original full-page grids.
    ds=raw['plan']['drawings']; ts=raw['plan']['traces']
    grids=[d for d in ds if d.get('layer') and ('GRID' in d['layer'].upper() or 'AXIS' in d['layer'].upper()) and 'IDEN' not in d['layer'].upper()]
    vv,hh=reg.grid_clusters(None,layers=None,drawings=grids,minlen=50)
    registration=reg.register_free(vv,hh)
    assert registration==D['plan']['registration']
    north,south,west,east=(_line(ds,i) for i in (4460,4462,4463,4461))
    assert north[0][1]==north[1][1] and south[0][1]==south[1][1]
    assert west[0][0]==west[1][0] and east[0][0]==east[1][0]
    left,right=west[0][0],east[0][0]
    top,bottom=north[0][1],south[0][1]
    assert sorted([p[0] for p in north])==sorted([p[0] for p in south])==[left,right]
    assert sorted([p[1] for p in west])==[top,bottom]
    assert min(p[1] for p in east)<=top<bottom<=max(p[1] for p in east)
    inner_pdf=[[left,bottom],[right,bottom],[right,top],[left,top]]
    # The missing fourth edge is the A-WALL line crossing both inner endpoints.
    assert ds[4461]['layer']=='A-WALL' and all(ds[i]['layer']=='ELE 4' for i in (4459,4460,4462,4463))
    outpts=[list(p) for op in ds[4459]['items'] for p in op[1:]]
    ox0,oy0=min(p[0] for p in outpts),min(p[1] for p in outpts)
    ox1,oy1=max(p[0] for p in outpts),max(p[1] for p in outpts)
    assert ox1==right and ox0<left and oy0<top<bottom<oy1
    outer_pdf=[[ox0,oy1],[ox1,oy1],[ox1,oy0],[ox0,oy0]]
    T=reg.make_T(registration)
    inner=[list(T(*p)) for p in inner_pdf]; outer=[list(T(*p)) for p in outer_pdf]
    # Bind printed dimensions to the actual dimension lines at the same ends.
    dims={i:_trace(ts,i)['text'] for i in (128,130,328,329)}
    assert dims=={128:'420',130:'200',328:'440',329:'240'}
    assert sorted([_line(ds,2279)[0][0],_line(ds,2280)[0][0]])==[left,right]
    assert sorted([_line(ds,2287)[0][1],_line(ds,2288)[0][1]])==[top,bottom]
    assert sorted([_line(ds,4947)[0][0],_line(ds,4948)[0][0]])==[ox0,ox1]
    assert sorted([_line(ds,4951)[0][1],_line(ds,4952)[0][1]])==[oy0,oy1]
    label=_trace(ts,71); plan_ffl=_trace(ts,89)
    assert label['text']=='TOP LIFT' and left<label['bbox'][0]<right and top<label['bbox'][1]<bottom
    assert left<plan_ffl['bbox'][0]<right and top<plan_ffl['bbox'][1]<bottom
    ffl=float(re.search(r'\+([\d.]+)',plan_ffl['text']).group(1))
    # Decode the table independently: roof row -> F12 -> its stated 3 cm.
    strings={}
    for key,win in [('roof_row_words','roof_row_window'),('F12_words','F12_window')]:
        x0,y0,x1,y1=D['schedule'][win]
        fresh=[{'index':i,'word':list(w)} for i,w in enumerate(raw['schedule']['words']) if x0<=w[0]<x1 and y0<=w[1] and w[3]<=y1]
        assert fresh==D['schedule'][key]
        strings[key]=' '.join(w['word'][4] for w in fresh)
    assert strings['roof_row_words']=='Roof & Top Roof F12 - - -'
    assert strings['F12_words'].startswith('F12 Concrete tiles 300 X 300')
    thickness_cm=int(re.search(r'Thick (\d+)cm',strings['F12_words']).group(1))
    # Section5 contains the same FFL and a horizontal finish line at its arrow tip.
    sec=raw['section']; anns=sec['annotations']; sd=sec['drawings']
    section_ffl=float(anns[39]['content'])
    tops=[float(anns[i]['content']) for i in (41,43)]
    assert ffl==section_ffl==24.20 and tops==[24.65,24.65]
    assert anns[40]['content']==anns[42]['content']==anns[44]['content']=='FFL'
    finish_line=_line(sd,7681); rear_top=_line(sd,7701)
    finish_y=finish_line[0][1]; top_y=rear_top[0][1]
    assert finish_line[1][1]==finish_y and rear_top[1][1]==top_y
    assert sorted(p[0] for p in finish_line)==sorted(p[0] for p in rear_top)
    arrow_tip=max((list(p) for op in sd[7423]['items'] for p in op[1:]),key=lambda p:p[1])
    assert abs(arrow_tip[1]-finish_y)<.0001 and min(p[0] for p in finish_line)<arrow_tip[0]<max(p[0] for p in finish_line)
    side_rects=[list(sd[i]['rect']) for i in (7679,7680)]
    assert all(abs(r[1]-top_y)<.0001 for r in side_rects)
    assert all(r[3]>finish_y for r in side_rects)
    concrete_top=float(re.search(r'\+([\d.]+)',_trace(raw['structural_level']['traces'],43)['text']).group(1))
    assert concrete_top==24.00
    # Section220 is grid4 to grid5, not an alternative finish width.
    assert _trace(sec['traces'],164)['text']=='220'
    assert {anns[53]['content'],anns[54]['content']}=={'4','5'}
    section_scale=(tops[0]-ffl)*100/(finish_y-top_y)
    section_base_from_side=ffl-(side_rects[0][3]-finish_y)*section_scale/100
    x0,y0=outer[0]; x1,y1=outer[2]; ix0,iy0=inner[0]; _,iy1=inner[2]
    expected=[('A.floor-R-SRF0002','A.floor','floor_F12',inner,round(ffl-thickness_cm/100,3),ffl),
              ('A.wall-R-SRF0003','A.wall','lift_roof_source_upstand',_rectangle(x0,y0,ix0,y1),concrete_top,tops[0]),
              ('A.wall-R-SRF0004','A.wall','lift_roof_source_upstand',_rectangle(ix0,y0,x1,iy0),concrete_top,tops[0]),
              ('A.wall-R-SRF0005','A.wall','lift_roof_source_upstand',_rectangle(ix0,iy1,x1,y1),concrete_top,tops[0])]
    by={}
    for e in M['els']:by.setdefault(e['id'],[]).append(e)
    records=[]
    for eid,category,typ,xy,z0,z1 in expected:
        assert len(by.get(eid,[]))==1,'Model element missing/duplicate: '+eid
        e=by[eid][0]
        assert (e['c'],e['t'],e['l'])==(category,typ,'R')
        g=['p',[[round(x,4),round(y,4)] for x,y in xy],z0,z1,None]
        assert e['g']==g,'Source-derived site and solid disagree: '+eid
        records.append({'id':eid,'category':category,'type':typ,'status':'matched_location_and_shape',
            'geometry_sha256':digest(e['g']),'expected_g':g,
            'evidence':['ARCH1:8 A105','ARCH2:17 A900 section 5']+(['ARCH1:18 A500'] if category=='A.floor' else ['STR:23 CL+24.00 only']),
            'xy_checked':True,'absolute_z_checked':True,'shape_checked':True,
            'acceptance_scope':'architectural_model_component_location_and_solid_envelope',
            'excluded_claims':['installed_material','fixing','waterproofing_layers','structural_slab_extent','operation','site_as_built']})
    results=[]
    for r in records:
        e=by[r['id']][0]
        results.append({'id':r['id'],'status':'matched','position_match':True,'shape_match':True,
            'evidence':r['evidence'],'source_refs':r['evidence'],'conflict_ids':[],
            'proof_file':'../review-evidence/roof-finish-matching/source-proof.json',
            'geometry_sha256':digest([e['id'],e['c'],e['t'],e['l'],e['g']]),
            'scope_ar':'الموقع والشكل المجسم لعنصر التشطيب أو الدروة فقط؛ لايشملموادالتوريدأوالتثبيتوماوراءطبقةالتشطيب.'})
    return {'schema':'c4.roof-finish-matching-audit.v1','pass':True,'data_sha256':DATA_SHA256,
        'source_hashes':{k:v['sha256'] for k,v in D['sources'].items()},
        'accepted_ids':[r['id'] for r in records],'records':records,'results':results,'accepted_count':len(records),
        'registration':registration,'raw_plan_inner_pdf':inner_pdf,'raw_plan_outer_pdf':outer_pdf,
        'literal_inner_dimensions_cm':[420,200],
        'registered_inner_dimensions_cm':[inner[2][0]-inner[0][0],inner[2][1]-inner[0][1]],
        'registered_minus_literal_cm':[inner[2][0]-inner[0][0]-420,inner[2][1]-inner[0][1]-200],
        'comparison_rule':'exact equality to reconstructed original PDF geometry after existing model rounding to 0.0001 cm; literal dimension residual reported, never used to move the outline',
        'floor_z_m':[round(ffl-thickness_cm/100,3),ffl], 'floor_thickness_cm':thickness_cm,
        'upstand_z_m':[concrete_top,tops[0]],'upstand_above_finish_cm':round((tops[0]-ffl)*100,3),
        'section_side_base_from_level_scale_m':section_base_from_side,
        'unmodeled_buildup_gap_cm':round((ffl-thickness_cm/100-concrete_top)*100,3),
        'unrelated_structural_cap_accepted':False,'model_metadata_used_as_proof':False,
        'limits_ar':['الحكم على موقع وشكل طبقةتشطيب واحدة وثلاثةأجسامدروة معمارية فقط.',
                     'طبقات17سم بينCL+24.00 وأسفلF12 غير ممثلة؛ لا تؤثر على تطابق طبقةF12 نفسها ولا تصبح معتمدة بهذا الفحص.',
                     'الأبعاد النصية420×200سم؛ إسقاط خطوطPDF يعطي419.735×199.713سم ضمن رسم المصدر المسجل، وحُفظ الفرق العددي صراحة.',
                     'لايشملA.detail-R-SRF0001 أو أيS.slab أومادةتوريد أوتثبيت أوعزل أوتشغيل أوتنفيذميداني.']}


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',type=Path,default=Path(__file__).resolve().parents[1]/'src/model.json')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    M=json.loads(args.model.read_text()); before=digest(M)
    result=audit(M)
    assert digest(M)==before,'Read-only audit changed model'
    result['model_unchanged']=True
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('records','results','raw_plan_inner_pdf','raw_plan_outer_pdf')},ensure_ascii=False))
