"""Match the bounded above-grade C* column parts and block panels to source.

The shared raw-source reconstructor independently rebuilds plan geometry from
the original PDF and registered architectural plot. This module adds original
BW1/BW2 section bindings, literal Z limits, and explicit component-part scope.
It never changes elements, types, geometry or existing acceptance flags.
"""
import copy
import hashlib
import json
import sys
from pathlib import Path

import fitz
from shapely.geometry import LineString, Polygon

ROOT=Path(__file__).resolve().parents[1]
DATA_PATH=ROOT/'pipeline/data/boundary_wall_matching.json'
DATA_SHA256='03abd44a7af406b9ef32096eed6765cfa01e0e18335b3a6bf5324e82cc1424f7'
SCHEMA='c4.boundary-wall-matching.v1'
IDS=tuple(['S.col-G-BND%04d'%i for i in range(1,42)]+['A.site-G-BND%04d'%i for i in range(1,38)])
PROOF_FILE='pipeline/data/matching-boundary-wall-proof.json'

def digest(v):
    return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def _sha(b):return hashlib.sha256(b).hexdigest()

def data():
    b=DATA_PATH.read_bytes()
    if _sha(b)!=DATA_SHA256:raise ValueError('Boundary wall source ledger changed')
    return json.loads(b)

def _serial(v):
    if v is None or isinstance(v,(str,int,float,bool)):return v
    return [_serial(x)for x in v]

def _drawing(ds,i):
    d=ds[i]
    return {'index':i,**{k:_serial(d.get(k))for k in ('layer','type','rect','items','fill','color','closePath')}}

def _source(D,verify_images=True):
    sys.path.insert(0,str(ROOT/'tools'))
    import check_boundary_source as C
    if _sha((ROOT/'tools/check_boundary_source.py').read_bytes())!=D['base_raw_gate_sha256']:
        raise ValueError('Independent raw source reconstructor changed')
    if _sha((ROOT/'pipeline/data/boundary_source_remaining.json').read_bytes())!=D['base_ledger_sha256']:
        raise ValueError('Base source identity ledger changed')
    if _sha(C.STR.read_bytes())!=D['source_pdf']['sha256'] or _sha(C.ARCH.read_bytes())!=D['arch_pdf']['sha256']:
        raise ValueError('Original source PDF fingerprint changed')
    raw=C._sources(C._revision(C.STR),C._revision(C.ARCH))
    if raw['transform']!=D['source_transform']:raise ValueError('Raw project registration differs')
    doc=fitz.open(C.STR);p=doc[31];ds=p.get_drawings();ts=p.get_texttrace();aa=list(p.annots())
    for q in D['drawings']:
        if _drawing(ds,q['index'])!=q:raise ValueError('Original section/cut operator differs')
    for q in D['texts']:
        t=ts[q['index']]
        if {'index':q['index'],'text':C._text(t),'bbox':list(t['bbox'])}!=q:raise ValueError('Section/datum literal differs')
    for q in D['annotations']:
        a=aa[q['index']]
        if {'index':q['index'],'xref':a.xref,'rect':list(a.rect),'content':a.info['content']}!=q:raise ValueError('Section annotation differs')
    text=lambda i:C._text(ts[i])
    assert text(87)=='BW' and text(88)=='1' and text(89)=='BW' and text(90)=='2'
    assert text(97)==text(102)=='CL.+ 3.0' and text(99)==text(104)=='CL.-0.10'
    assert aa[16].info['content']=='200' and aa[22].info['content']=='300'
    assert aa[30].info['content']=='BLOCK WALL'
    assert aa[32].info['content'].strip()==aa[49].info['content'].strip()=='COPING BM - CB1'
    sections=[]
    for name,s in D['section_bindings'].items():
        item=ds[s['plan_cut_drawing']]['items'][s['segment_index']]
        assert item[0]=='l'
        cut=LineString([[v.x,v.y]for v in item[1:3]])
        hits=[eid for eid,q in raw['expected'].items()if q['category']!='S.beam' and cut.intersects(q['pdf_poly'])]
        if hits!=[s['crossed_id']]:raise ValueError('Section plan cut no longer binds uniquely to intended component')
        sides=[ds[i]['items'][0]for i in s['outer_sides']]
        assert all(q[0]=='l' and q[1].x==q[2].x for q in sides)
        slab=ds[s['slab_top_drawing']]['rect'].y0
        assert all(min(q[1].y,q[2].y)<slab<=max(q[1].y,q[2].y)+.12 for q in sides)
        # These are shape/continuity checks only. No length is scaled from NTS.
        assert ds[s['slab_top_drawing']]['rect'].x0<sides[0][1].x
        assert 'SECTION  BW -'+name[-1] in text(s['section_title_trace'])
        sections.append({'section':name,'unique_plan_cut_component':hits[0],
            'plan_cut_drawing_index':s['plan_cut_drawing'],'plan_cut_segment_index':s['segment_index'],
            'section_constant_vertical_face_drawings':s['outer_sides'],
            'grade_slab_top_drawing':s['slab_top_drawing'],'top_datum_m':3.0,'grade_datum_m':-.1,
            'CB1_literal_depth_m':.3,'modeled_top_derived_m':round(3-.3,2),
            'NTS_section_scaled':False,'slab_face_endpoint_gap_pdf_pt':abs(slab-max(sides[0][1].y,sides[0][2].y))})
    renders=[]
    if verify_images:
        for q in D['renderings']:
            path=(ROOT/q['path']).resolve()
            png=p.get_pixmap(matrix=fitz.Matrix(q['scale'],q['scale']),clip=fitz.Rect(q['clip']),annots=q['annots']).tobytes('png')
            if not path.is_file() or _sha(path.read_bytes())!=q['sha256'] or _sha(png)!=q['sha256']:
                raise ValueError('Original section evidence rendering differs')
            renders.append({'path':q['path'],'sha256':q['sha256'],'pass':True})
    doc.close()
    return raw,{'source_pdf_sha256':D['source_pdf']['sha256'],'arch_pdf_sha256':D['arch_pdf']['sha256'],
        'drawing_checks':len(D['drawings']),'text_checks':len(D['texts']),'annotation_checks':len(D['annotations']),
        'renderings':renders,'sections':sections,'source_transform':raw['transform'],
        'reference_registration':raw['reference_registration'],'A400_width_difference_cm':raw['A400_width_difference_cm'],
        'A400_side_difference_cm':raw['A400_side_difference_cm'],'scope_ar':D['source_scope_ar'],
        'derivation_ar':D['derivation_ar'],'model_metadata_used_as_source_proof':False}

def audit(M,verify_images=True):
    D=data();raw,source=_source(D,verify_images)
    by={}
    for e in M['els']:by.setdefault(e['id'],[]).append(e)
    results=[];conflicts=[]
    for eid,r in D['records'].items():
        es=by.get(eid,[]);e=es[0]if len(es)==1 else {};q=raw['expected'][eid];errors=[]
        if len(es)!=1:errors.append('هوية العنصر مفقودة أو مكررة')
        if (e.get('c'),e.get('t'),e.get('l'))!=(r['category'],r['type'],r['level']):errors.append('تعريف العنصر لا يطابق الجزء المقصود من السور')
        if not (e.get('a')or{}).get('scope_above_grade_only'):errors.append('نطاق العنصر لم يعد معرفًا كجزء فوق الأرض')
        assert sorted(q['required_indices'])==r['source_drawing_indices'] and q['z']==r['z_m']
        delta=zdelta=None;g=e.get('g')
        try:
            assert g[0]=='p' and len(g)in(4,5) and not(g[4]if len(g)>4 else None)
            poly=Polygon(g[1]);delta=poly.hausdorff_distance(q['world_poly'])
            if not poly.is_valid or delta>.0001:errors.append('حدود المسقط تختلف عن الوجوه المصدرية المسجلة')
            zdelta=max(abs(a-b)for a,b in zip(g[2:4],[-.1,round(3-.3,2)]))
            if zdelta>1e-8:errors.append('نهايات الجزء الرأسية تختلف عن −0.10 وأسفل CB1 +2.70')
        except Exception:errors.append('جسم الجزء غير صالح كمنشور مغلق ثابت المسقط')
        b=q['world_poly'].bounds;dims=sorted([b[2]-b[0],b[3]-b[1]])
        assert dims==r['raw_registered_dimensions_cm']
        matched=not errors;issue='MM-BOUNDARY-WALL-'+eid.replace('.','-')+'-POSITION-SHAPE'
        note=('تطابق موقع وشكل الجزء فوق الأرض من −0.10 إلى +2.70 م، بمسقط المصدر وحدود BW‑1.'if r['category']=='S.col'else
              'تطابق الحشوة بين وجهي العمودين من −0.10 إلى +2.70 م، بحدود المسقط ومقطع BW‑2.')
        note+=' نطاق المطابقة هو الجزء الممثل فوق البلاطة، وليس كامل العمود مع امتداده داخل البلاطة والأساس. عرض الرسم وفَرْقه عن20 سم محفوظان.'
        results.append({'id':eid,'status':'matched'if matched else'conflict','model_geometry_match':matched,
            'position_match':matched,'shape_match':matched,'geometry_sha256':digest([eid,e.get('c'),e.get('t'),e.get('l'),g]),
            'source_refs':['STR:31 S-26','STR:32 S-27 '+r['section'],'ARCH1:4 A101','ARCH1:16 A400'],
            'note_ar':note if matched else'؛ '.join(errors),'conflict_ids':[]if matched else[issue],
            'checks':{'source_registered_plan':delta is not None and delta<=.0001,'literal_derived_Z':zdelta is not None and zdelta<=1e-8,
                'closed_constant_section_prism':not any('منشور' in x for x in errors),'explicit_above_grade_part':bool((e.get('a')or{}).get('scope_above_grade_only'))},
            'measurements':{'source_XY_deviation_cm':delta,'z_deviation_m':zdelta,'source_z_m':[-.1,2.7],
                'raw_registered_dimensions_cm':dims,'nominal_cross_width_cm':20.,'drawn_cross_width_cm':dims[0],
                'nominal_cross_width_difference_cm':dims[0]-20},
            'evidence':{'source_drawing_indices':r['source_drawing_indices'],'source_shape_kind':r['proof_kind'],
                'section':r['section'],'section_bound_part_only':True,'data_sha256':DATA_SHA256,
                'source_pdf_sha256':D['source_pdf']['sha256'],'shape_NTS_scaled':False},
            'errors':errors,'physical_or_site_acceptance':False})
        if not matched:conflicts.append({'id':issue,'title':'اختلاف الجزء الممثل من السور '+eid,'status':'confirmed_model_error',
            'elements':[eid],'source':'STR ص32 S-27 '+r['section'],'note':'؛ '.join(errors),
            'before':{'g':copy.deepcopy(g)},'after':{'source_z_m':[-.1,2.7],'source_plan_drawing_indices':r['source_drawing_indices']}})
    return {'schema':SCHEMA,'pass':True,'results':results,'matched_count':sum(r['status']=='matched'for r in results),
        'conflict_count':len(conflicts),'conflicts':conflicts,'errors':[], 'source_proof':source,
        'data_sha256':DATA_SHA256,'source_scope_ar':D['source_scope_ar'],'physical_or_site_acceptance':False,
        'comparison_tolerance_cm':.0001,'tolerance_scope':'PDF geometry replay comparison only; not a construction tolerance'}

def apply(M,els=None):
    proxy=M if els is None or els is M['els']else dict(M,els=els)
    # Read-only with respect to all elements and all existing acceptance flags.
    report=audit(proxy)
    M['boundaryWallMatching']=report
    return report

def issue_records(M,report=None):return copy.deepcopy((report or audit(M))['conflicts'])
