# -*- coding: utf-8 -*-
"""Apply source shape corrections and record complete position/shape matches."""
import copy,json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import completion_batch as CB
import model_matching as MM
import ceiling_shape_match as CE
import check_ceiling_shape_match as CG
import stair_concrete_completion as ST
import raft_model_acceptance as RA
import roof_finish_matching as RF
import boundary_joint_matching as BJ
import column_shape_matching as CL


def merge_issues(M, rows):
    ids={q['id']for q in rows}
    M['drawingIssues']=[q for q in M['drawingIssues']if q['id']not in ids]+rows


def conflict(M, eid, ids, refs, note, proof, checks=None):
    e=next(e for e in M['els']if e['id']==eid)
    return {'id':eid,'status':'conflict','geometry_sha256':MM.geometry_sha(e),
            'position_match':False,'shape_match':False,'source_refs':refs,'note_ar':note,
            'conflict_ids':ids,'proof_file':proof,'checks':checks or {}}


def refresh_concrete_coverage(coverage, ids):
    source='STR ص29 S-24 +ص21 S-16؛ ARCH2 ص1 A600 وص2 A601'
    finding='خواص الخرسانة موثقة:25سم للخصر عموديًا على الميل والبسطات، ومناسيبCL؛ تعارض13/11قائمة وحدود جسم/ارتكاز غير مكتملة، فلا قبول لجسم الخرسانة من أسطح التشطيب.'
    controlled=set(ids)
    for row in coverage['rows']:
        if row['id']in controlled:
            row['xy_basis']='أسطح تشطيب مشتقة من المسقط والقطاع؛ موضع جسم الخرسانة وشكله في قائمة التعارضات'
            row['source']=source
            row['findings']=[finding]
            detail=coverage['details'][row['id']]
            detail['source_refs']=list(dict.fromkeys(detail.get('source_refs',[])+[source]))
            detail['height_assumptions']=[finding]


def refresh_matching_coordination(M,base):
    import collections
    before={e['id']:e for e in base['els']}
    cr=copy.deepcopy(base['coordinationReview'])
    old={q['id']:q for q in cr['issues']}
    geometry_changed=[];source_changed=[]
    for c in M['clashes']:
        pair=[M['els'][c[k]]for k in ('a','b')]
        if [e['id']for e in pair]!=[c['ea'],c['eb']]:raise ValueError('Clash identity index changed')
        moved=any(e['g']!=before[e['id']]['g']for e in pair)
        semantic=any(CB.CR._basis(M,e)!=CB.CR._basis(base,before[e['id']])for e in pair)
        if moved or semantic:
            old[c['id']]=CB.CR.classify(M,c,geometry=None if moved else old[c['id']]['geometry'])
            (geometry_changed if moved else source_changed).append(c['id'])
    cr['issues']=[old[q['id']]for q in cr['issues']]
    cr['counts']=dict(collections.Counter(q['classification']['lane']for q in cr['issues']))
    cr['geometry_counts']=dict(collections.Counter(q['geometry']['state']for q in cr['issues']))
    cr['source_conflicts']=[CB.CR._source_conflict(q)for q in M['drawingIssues']if q['status']=='source_conflict']
    cr['zconflicts']=[q for q in cr['source_conflicts']if q.get('zconflict')]
    cr['coverage'].update(source_conflicts=len(cr['source_conflicts']),source_zconflicts=len(cr['zconflicts']),
        geometry_unproved=sum(q['geometry']['state']=='unproved'for q in cr['issues']),
        geometry_unsupported=sum(bool(q['geometry'].get('unsupported_geometry_elements'))for q in cr['issues']),
        confirmed_plan_source_routes=len({q['source']['plan_proof']['source_physical_route_group']for q in cr['issues']if q['classification']['plan_crossing_confirmed']}))
    cr['review_cases']=[q for q in cr['issues']if q.get('case_audit_ar')]
    cr['model_geometry_sha256']=CB.CR._hash([[e['id'],e['g']]for e in M['els']])
    cr['incremental_reuse']={'existing_pairs':len(M['clashes']),
        'geometry_recomputed_ids':geometry_changed,'source_classification_refreshed_ids':source_changed,
        'unchanged_pair_geometry_reused':len(M['clashes'])-len(geometry_changed),
        'limit_ar':'أعيدت هندسة الشاهد عند تغير الجسم، ودليل المصدر عند تغير الهوية؛ بقية الأزواج محفوظة بهندستها المثبتة.'}
    M['coordinationReview']=cr


def apply(M, previous_coverage):
    if previous_coverage['model_geometry_sha256']!=CB.SB.cc_geometry_sha(M):
        raise ValueError('Model matching input coverage is stale')
    base=copy.deepcopy(M)
    before_by={e['id']:e for e in base['els']}
    ceiling=CE.apply(M)
    concrete=ST.apply(M)
    boundary=BJ.apply(M)
    columns=CL.apply(M)
    planted=next(e for e in M['els']if e['id']==CL.data()['identity_correction']['id'])
    planted['a']['source_reference']=planted['a']['source_identity_reference']
    # A shared type names the schedule; instance-specific raw references stay
    # with each element and must not incorrectly attribute G0070 to G0072.
    M['types'][planted['t']]['sr']=['STR ص16 S-11 مفتاح PLANTED COLUMN؛ راجع دليل كل عنصر لمعرف الرسم',
        'STR ص17 S-12 وص18 S-13: وسومC9 في الأدوار العليا؛ STR ص25 S-20 جدولC9']
    merge_issues(M,CE.issue_records(M))
    ST.apply_issues(M)
    merge_issues(M,CL.issue_records(M,columns))
    merge_issues(M,[{'id':'MM-BOUNDARY-CB1-JOINTS','status':'corrected',
        'title':'تصحيح فواصل كمرات السور CB1 إلى البعد المكتوب 2 سم',
        'source':'STR ص31 S-26 / ص32 S-27','elements':list(BJ.IDS),
        'note':'صُححت نهايات ست كمرات عند ثلاثة فواصل إلى2سم حول منتصف وجهي العمودين في الرسم. بقيت بقية الحدود والمناسيب كما هي؛ عرض القطاع الرسومي20.1094–20.1101سم مقابل20سم الاسمية، والفرق مسجل في دليل المطابقة.',
        'after':{'joint_width_cm':2,'source_anchor':'derived STR32 opposing column face midpoint'}}])
    for q in M['drawingIssues']:
        if q['id']=='DP-STAIR-COMPLETION-BODY':
            q['note']='أسطح البدروم والأرضي تبقى مفتوحة. وُثقت خواص خرسانة درج01 الأرضي منS-24:سماكة الخصر25سم عمودية على الميل والبسطات25سم ومناسيبCL؛ وظهر تعارض13/11قائمة معS-16. راجع DP-STAIR-CONCRETE-G-SECTION-PLAN وDP-STAIR-CONCRETE-G-BODY-EXTENTS. هندسة الخرسانة الكاملة لم تستبدل بأسطح التشطيب.'
        elif q['id']=='DP-BOUNDARY-JOINTS':
            q['note']='اكتملت مطابقة حدود كمراتCB1 وفواصلها الممثلة إلى2سم منSTR31/32 ضمن MM-BOUNDARY-CB1-JOINTS. هذا السجل يخص تفصيل تنفيذ الفاصل وربط الغطاء خارج حدود الجسم الممثل؛ لا يحجب اعتماد مطابقة موقع وشكل الكمرات.'
    cproof=CG.audit(M);sproof=ST.audit(M)
    raft=RA.apply(M);roof=RF.audit(M)
    for label,r in [('ceilings',cproof),('stair_concrete',sproof),('raft',raft),('roof',roof)]:
        if not r.get('pass'):raise ValueError('Failed native drawing proof: '+label+' '+str(r.get('errors')))
    for q in raft['conflicts']:
        merge_issues(M,[{'id':q['id'],'title':q['title_ar'],'status':'confirmed_model_error',
            'source':' / '.join(q['source_pages']),'note':q['detail_ar'],'elements':q['ids'],
            'level':'B','xy_cm':None,'z_m':None,'after':{'position_shape_match':False}}])
    records=[];by={e['id']:e for e in M['els']}
    for report,label,proof_file in [(raft,'اللبشة','pipeline/data/matching-raft-proof.json'),
                                   (roof,'تشطيب غطاء المصعدين','pipeline/data/matching-roof-proof.json'),
                                   (boundary,'كمرات السور','pipeline/data/matching-boundary-proof.json'),
                                   (columns,'الأعمدة','pipeline/data/matching-columns-proof.json')]:
        for r in report['results']:
            eid=r['id'];matched=r['status']=='matched'
            records.append({'id':eid,'status':r['status'],'geometry_sha256':MM.geometry_sha(by[eid]),
                'position_match':matched,'shape_match':matched,
                'source_refs':r.get('source_refs') or (['STR:11 S-7','STR:12 S-8']if label=='اللبشة'else ['STR:31 S-26','STR:32 S-27']if label=='كمرات السور'else['ARCH1:8 A105','ARCH1:18 A500','ARCH2:17 A900']),
                'note_ar':r.get('note_ar')or('تطابق الموقع والشكل والأبعاد مع المسقط والقطاع.'if matched else 'اختلاف شكل حفرة المصعد بين المقطع والمجسم؛ راجع التعارض المرتبط.'),
                'conflict_ids':r.get('conflict_ids',[]),'proof_file':proof_file,
                'checks':r.get('checks',{}),'source_evidence':r.get('evidence',{}),
                'measurements':r.get('measurements',{})})
            if label=='كمرات السور':
                records[-1]['note_ar']='تطابق الموقع وحدود الرسم المسجل ومنسوبا2.70–3.00م؛ صُحح الفاصل إلى2سم. عرض القطاع المستخرج20.1094–20.1101سم مقابل20سم الاسمية، مع إبقاء فرق الاستخراج ظاهرًا.'
            elif label=='الأعمدة':
                records[-1]['note_ar']=r.get('note_ar')or('تطابق جسم العمود C1 مع المسقط وجدول30×160سم وحدود المنسوب في القطاع.'if matched else 'اختلاف في حد الجسم الرأسي أو هويته المصدرية؛ راجع دليل المقطع والتعارض المرتبط.')
    for eid in CE.data()['records']:
        records.append(conflict(M,eid,['DP-CEILING-SHAPE-LOCATION-BOUNDARY'],
            ['ARCH1:18 A500','ARCH2:29 A1401','ARCH2:34 A1600','ARCH2:35 A1601'],
            'صُححت سماكة الشكل حسب النوع؛ حدود الشكل وتوزيعه ومنسوبه الحالي مشتقة ولم تثبت مطابقتها بالرسم لكل منطقة.',
            'pipeline/data/matching-ceilings-proof.json',{'literal_thickness_match':True}))
    for eid in concrete['controlled_ids']:
        issues=[q for q in M['drawingIssues']if eid in q.get('elements',[])and q['id'].startswith('DP-STAIR-CONCRETE')and q['status']!='corrected']
        if not issues:raise ValueError('Concrete stair has no source shape conflict')
        records.append(conflict(M,eid,[q['id']for q in issues],['STR:29 S-24','STR:21 S-16','ARCH2:1 A600','ARCH2:2 A601'],
            'تعارض عدد القوائم بين المسقط والمقطع الإنشائي، مع اختلاف حدود جسم الخرسانة عن أسطح التشطيب الممثلة.',
            'pipeline/data/matching-stair-concrete-proof.json',{'source_thickness_properties_recorded':True}))
    # The reviewed door detail contradictions concern shape and stay on the same
    # conflict list; they do not prevent independent components being matched.
    doors=CB.DC.audit(M)
    if not doors['summary']['pass']:raise ValueError('Door source conflict proof changed')
    for eid in CB.DC.data()[0]['instances']:
        issues=[q for q in M['drawingIssues']if q['id'].startswith('DP-DOOR-COMPLETION')and eid in q.get('elements',[])]
        records.append(conflict(M,eid,[q['id']for q in issues],['ARCH2:9 A700','ARCH2:10 A701'],
            'اختلاف أبعاد تفاصيل شكل الباب بين وصف المصدر ورسمه؛ القيم المتعارضة محفوظة في قائمة التعارضات.',
            'pipeline/data/matching-doors-proof.json'))
    matching=MM.build(M,records)
    geometry=CB.GI.audit(M)
    if not geometry['pass']:raise ValueError('Final matching geometry integrity failed')
    coverage=copy.deepcopy(previous_coverage)
    for e in M['els']:
        if e['id']in CE.data()['records']:
            details=coverage['details'][e['id']]
            details['z_m']=CB.CC.z_range(e['g'])
            details.setdefault('evidence',{})['ceiling_source_thickness_match']={
                'thickness_mm':e['a']['ceiling_source_thickness_mm'],'proof_file':'pipeline/data/matching-ceilings-proof.json',
                'location_and_shape_accepted':False,'current_geometry_sha256':CB.SB.digest(e['g'])}
    refresh_concrete_coverage(coverage,concrete['controlled_ids'])
    coverage_rows={r['id']:r for r in coverage['rows']}
    column_ids=set(CL.data()['records'])|{CL.data()['identity_correction']['id']}
    for r in matching['records']:
        if r['id']in set(BJ.IDS)|column_ids:
            e=by[r['id']];d=coverage['details'][r['id']]
            d['type']=e['t'];d['xy_cm']=CB.CC.xy(e['g']);d['z_m']=CB.CC.z_range(e['g'])
            d['source_refs']=list(dict.fromkeys(d.get('source_refs',[])+r['source_refs']))
            d.setdefault('evidence',{})['model_position_shape_matching']=copy.deepcopy(r)
            coverage_rows[r['id']]['findings']=[r['note_ar']]
        if r['status']=='matched':
            d=coverage['details'][r['id']]
            d.setdefault('evidence',{})['model_position_shape_matching']=copy.deepcopy(r)
            d['needs_original_xy_proof']=False;d['needs_height_proof']=False
            d['needs_dimension_semantic_review']=False
            coverage_rows[r['id']]['z_basis']='source_plan_and_section_match'
        elif r['id']in concrete['controlled_ids']:
            coverage['details'][r['id']].setdefault('evidence',{})['structural_section_properties']={
                'proof_file':'pipeline/data/matching-stair-concrete-proof.json','source_thickness_cm':25,
                'whole_shape_matched':False,'conflict_ids':r['conflict_ids']}
    import collections
    coverage['height_counts']=dict(collections.Counter(r['z_basis']for r in coverage['rows']))
    coverage['model_geometry_sha256']=CB.SB.cc_geometry_sha(M)
    coverage['model_matching_summary']={'counts':matching['counts'],'criteria_ar':matching['criteria_ar'],'separate_from_XY':True}
    M['componentReview']=CB.CC.compact(coverage)
    lifecycle=CB.refresh_lifecycle(M,base)
    refresh_matching_coordination(M,base)
    coordination=CB.CO.audit(M,set(CB.DC.data()[0]['instances'])|set(CB.EC.data()['records']))
    M['completionCoordination']={k:v for k,v in coordination.items()if k not in ('unsupported_elements','excluded_stage_elements')}
    M['completionCoordination']['external_report']='pipeline/data/completion_coordination.json'
    CB.SB.aggregate_reliability(M)
    owned=set(CE.data()['records'])|set(concrete['controlled_ids'])|set(BJ.IDS)|set(CL.data()['records'])|{CL.data()['identity_correction']['id']}
    before_by={e['id']:e for e in base['els']}
    for e in M['els']:
        if e['id']not in owned and e!=before_by[e['id']]:raise ValueError('Unowned full element changed: '+e['id'])
    if len(M['els'])!=len(base['els']):raise ValueError('Unexpected count change')
    summary='مطابقة الموقع والشكل: اعتماد الأجسام المثبتة بالمسقط والقطاع، وتصحيح سُمك281 سقفًا وفواصل6 كمرات وهوية عمود مزروع؛ حفظ الاختلافات في قائمة التعارضات.'
    batch={'id':'position-shape-matching-20261009','saved':True,'summary_ar':summary,'matched_elements':matching['counts']['matched']}
    batches=M['meta'].setdefault('applied_source_batches',[])
    batches[:]=[b for b in batches if b.get('id')!=batch['id']]+[batch]
    changed_geometry=[e['id']for e in M['els']if e['g']!=before_by[e['id']]['g']]
    proof={'schema':'c4.model-matching-batch.v1','pass':True,'elements':len(M['els']),
        'changed_geometry_ids':changed_geometry,'changed_geometry_count':len(changed_geometry),
        'identity_changed_ids':columns['identity_changed_ids'],
        'unrelated_full_elements_unchanged':len(M['els'])-len(owned),'matching_counts':matching['counts'],
        'geometry_integrity_pass':True,'lifecycle':lifecycle,'all_input_native_proofs_pass':True,
        'full_post_executed':False,'site_or_operational_acceptance':False}
    M['meta']['model_matching_batch']=copy.deepcopy(proof)
    CB.INV.build(M)
    return {'proof':proof,'coverage':coverage,'coordination':coordination,'matching':matching,
            'ceilings':cproof,'stair-concrete':sproof,'raft':raft,'roof':roof,'doors':doors,'geometry':geometry,
            'boundary':boundary,'columns':columns}


def prepare(model_path,coverage_path,stage):
    model_path,coverage_path,stage=Path(model_path),Path(coverage_path),Path(stage)
    M=json.loads(model_path.read_text());C=json.loads(coverage_path.read_text())
    before_model=model_path.read_bytes();before_coverage=coverage_path.read_bytes()
    result=apply(M,C)
    stage.mkdir(parents=True,exist_ok=True)
    (stage/'before-model.json').write_bytes(before_model)
    (stage/'before-component-coverage.json').write_bytes(before_coverage)
    result['proof']['before_model_sha256']=hashlib.sha256(before_model).hexdigest()
    after=CB.encoded(M);(stage/'after-model.json').write_bytes(after)
    result['proof']['after_model_sha256']=hashlib.sha256(after).hexdigest()
    for name,r in result.items():(stage/(name+'.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2))
    return result['proof']


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--model',default=ROOT/'src/model.json');p.add_argument('--coverage',default=ROOT/'pipeline/data/component_coverage.json');p.add_argument('--stage',required=True)
    a=p.parse_args();print(json.dumps(prepare(a.model,a.coverage,a.stage),ensure_ascii=False,indent=2))
