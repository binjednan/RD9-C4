"""Persist the bounded continuation around the legacy post_model pipeline.

The upper hook restores exact controlled inputs before legacy guards. The lower
hook runs after legacy reviews and before inventory/model publication. Neither
hook runs post_model, a build, or a full lifecycle/clash scan. The only lifecycle
systems recomputed are those whose complete declared dependencies changed.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import completion_batch as CB
import core_stairs_source_surfaces as CSF
import stair_completion as SC
import equipment_completion as EC
import door_completion as DC
import source_batch as SB


def _equipment_preflight(M):
    records=EC.data()['records'];by=SB.by_id(M)
    for eid,r in records.items():
        e=by.get(eid)
        if e is None or any(e.get(k)!=r['before_e'].get(k)for k in ('c','t','l','m','mark','grp')):
            raise ValueError('Completion post equipment identity changed: '+eid)
        if e['g']not in (r['before_e']['g'],r['after_g']):
            raise ValueError('Completion post equipment geometry changed: '+eid)
    return records,by


def restore_before_post(M,els=None):
    """After FHC link capture, before frozen CSF/legacy guards.

    The 204-door restore already belongs to door_source_templates at post entry.
    Index references are kept valid for the 32 reinserted stair members. The
    following legacy CSF stage has its own preexisting restoration lifecycle.
    """
    if els is not None and els is not M['els']:
        raise ValueError('Completion post requires actual M els array')
    # Preflight the whole controlled scope before the first restoration.
    SC._state(M,SC.data())
    records,by=_equipment_preflight(M)
    indices={e['id']:i for i,e in enumerate(M['els'])}
    stairs=SC.restore_before_post(M)
    equipment=[]
    if M.get('meta',{}).get('equipment_completion')or any(by[k].get('a',{}).get('equipment_completion')for k in records):
        plans={k:copy.deepcopy(r['before_e'])for k,r in records.items()}
        M['els'][:]=[plans.get(e['id'],e)for e in M['els']]
        equipment=list(plans)
        M.setdefault('meta',{}).pop('equipment_completion',None)
    current={e['id']:i for i,e in enumerate(M['els'])}
    remap=SB.remap_index_refs(M,{i:current[k]for k,i in indices.items()}) if stairs['restored_this_apply'] else {'references':0,'changed_indices':0,'retired_references':0}
    M.setdefault('meta',{}).pop('completion_post_adapter',None)
    return {'stairs':stairs,'equipment_restored':equipment,'index_remap':remap,
            'scope':'controlled source inputs only; FHC capture precedes this hook'}


def apply_after_legacy(M,coverage):
    """Restore final source state after all frozen legacy reviews, before INV.

    Returns fresh complete coverage/source/coordination reports for post_model to
    publish only after this function succeeds. Uses current legacy results as
    dependency witnesses; no stale checkpoint report is injected into a new run.
    """
    if coverage.get('model_geometry_sha256')!=SB.cc_geometry_sha(M):
        raise ValueError('Completion post input coverage is stale')
    SC._state(M,SC.data())
    _equipment_preflight(M)
    review,doorbase=DC.data();DC._guard(M,review,doorbase)
    base=copy.deepcopy(M)
    stair_stats=SC.apply(M)
    remap=SB.remap_index_refs(M,stair_stats['old_to_new_indices'],stair_stats['retired_indices'])
    equipment_stats=EC.apply(M)
    door_stats=DC.apply(M)
    old_issues=CB.remap_source_issues(M,stair_stats)
    equipment_issues=EC.issue_records(M);issue_ids={q['id']for q in equipment_issues}
    M['drawingIssues']=[q for q in M.get('drawingIssues',[])if q['id']not in issue_ids]+equipment_issues
    stairs,equipment,doors=SC.audit(M),CB.EG.audit(M),DC.audit(M)
    if not all(r.get('pass',r.get('summary',{}).get('pass',False))for r in (stairs,equipment,doors)):
        raise ValueError('Completion post native source audit failed')
    source_ids={e['id']for g in SC.data()['groups']for e in g['after_records']}
    for e in M['els']:
        if e['id']in source_ids:e['q']='vva'
    geometry=CB.GI.audit(M)
    if not geometry['pass']:raise ValueError('Completion post geometry integrity failed')
    result=CB.refresh_coverage(M,coverage,stairs,equipment,doors)
    lifecycle=CB.refresh_lifecycle(M,base)
    CB.refresh_coordination(M,base)
    targets=set(DC.data()[0]['instances'])|set(EC.data()['records'])
    coordination=CB.CO.audit(M,targets)
    M['completionCoordination']={k:v for k,v in coordination.items()if k not in ('unsupported_elements','excluded_stage_elements')}
    M['completionCoordination']['external_report']='pipeline/data/completion_coordination.json'
    SB.aggregate_reliability(M)
    # Retain the same canonical continuation record used by completion_batch.
    # The history entry is not duplicated on each future post cycle.
    summary=('استكمال درج01 بالبدروم والأرضي:42 جسمًا إجرائيًا استبدلت بـ10 تجميعات أسطح؛ '
             'تصحيح غلافي لوحة الجهد العالي والمولد، وتوثيق تعارضي تفاصيل الأبواب. '
             'أجسام الخرسانة والتثبيت والمنافذ والمواد غير المعتمدة تبقى معلقة.')
    batches=M['meta'].setdefault('applied_source_batches',[])
    if not any(q.get('id')==CB.BATCH_ID for q in batches):
        batches.append({'id':CB.BATCH_ID,'saved':True,'summary_ar':summary,'new_XY_checked':2,'whole_assembly_accepted':0})
    M['meta']['component_continuation']={'id':CB.BATCH_ID,'base_model_sha256':CB.BASE_SHA,
        'stairs':SC.data()['summary'],'equipment':equipment_stats,'doors':door_stats,
        'source_audits_pass':True,'physical_acceptance':False}
    dependency_result={'changed_systems':lifecycle['recomputed_systems'],
        'reason_ar':('الهويتان خارج مدخلاتLC الحالية؛ ثبت تطابق مدخلات ونتائج20 نظامًا حسب الهوية. لا تشغيل قدرة جديد.'
                     if not lifecycle['recomputed_systems']else 'أعيد تحليل الأنظمة التي تغيرت مدخلاتها فقط.')}
    M['meta']['equipment_completion']['actual_lifecycle_dependency_result']=copy.deepcopy(dependency_result)
    M['meta']['component_continuation']['actual_lifecycle_dependency_result']=dependency_result
    proof={'schema':'c4.completion-post-adapter.v1','pass':True,'before_elements':len(base['els']),
        'after_elements':len(M['els']),'source_data':{'stairs':SC.DATA_SHA,'equipment':EC.DATA_SHA256,'doors':DC.DATA_SHA},
        'source_audits_pass':True,'geometry_integrity_pass':True,
        'index_references_remapped':remap['references'],'retired_references':remap['retired_references'],
        'lifecycle':lifecycle,'source_issues_refreshed':len(old_issues),
        'no_full_post_build_or_network_invoked_by_adapter':True,'physical_acceptance':False}
    M['meta']['completion_post_adapter']=copy.deepcopy(proof)
    return {'proof':proof,'coverage':result,'coordination':coordination,'stairs':stairs,
            'equipment':equipment,'doors':doors,'geometry':geometry,'index_remap':remap}


def _canonical(M):
    """Shallow model view; exclude only enumerated runtime/provenance fields."""
    C=dict(M)
    C['meta']=dict(M.get('meta',{}))
    C['meta'].pop('completion_post_adapter',None)
    C['inventory']=copy.deepcopy(M.get('inventory',{}))
    C['inventory'].pop('built',None)
    # One newly added adapter changes code count/LOC; rebuilt HTML changes bytes.
    C['inventory'].get('code',{}).pop('pipeline',None)
    C['inventory'].get('out',{}).pop('index_mb',None)
    return C


def verify_staged(stage):
    """Execute adapter hooks, never import/execute post_model itself."""
    stage=Path(stage)
    before=json.loads((stage/'before-model.json').read_text())
    expected=json.loads((stage/'after-model.json').read_text())
    coverage=json.loads((stage/'before-component-coverage.json').read_text())
    controlled={e['id']for g in SC.data()['groups']for e in g['before_records']}|set(EC.data()['records'])
    expected_controlled={e['id']:copy.deepcopy(e)for e in before['els']if e['id']in controlled}
    print('adapter test: applying reviewed continuation in memory',flush=True)
    result=apply_after_legacy(before,coverage);CB.INV.build(before)
    a,b=_canonical(before),_canonical(expected)
    different=[k for k in set(a)|set(b)if a.get(k)!=b.get(k)]
    if different:
        differences=[]
        def find(x,y,path=''):
            if x==y:return
            if isinstance(x,dict)and isinstance(y,dict):
                for key in set(x)|set(y):find(x.get(key),y.get(key),path+'/'+str(key))
            elif isinstance(x,list)and isinstance(y,list)and len(x)==len(y):
                for i,(v,w)in enumerate(zip(x,y)):find(v,w,path+'/'+str(i))
            else:differences.append({'path':path,'actual':str(x)[:500],'expected':str(y)[:500]})
        find(a,b)
        raise ValueError('Completion adapter differs from staged batch: '+str(differences[:20]))
    # Exact restore is exercised on the integrated state. The legacy regeneration
    # boundary is represented by the authenticated before fixture, not a claim
    # that the large post_model pipeline was executed by this test.
    print('adapter test: staged final state matches; restoring controlled inputs',flush=True)
    unrelated_digest=SB.digest([e for e in before['els']if e['id']not in controlled])
    restore=restore_before_post(before)
    restored_by=SB.by_id(before)
    if any(restored_by[k]!=expected_controlled[k]for k in controlled):
        raise ValueError('Controlled post inputs did not restore exactly')
    if SB.digest([e for e in before['els']if e['id']not in controlled])!=unrelated_digest:
        raise ValueError('Continuation restore modified unrelated elements')
    # Restored arrays still resolve the same packed lifecycle IDs/results.
    if SB.packed_lifecycle_identity(before)!=SB.packed_lifecycle_identity(expected):
        raise ValueError('Restore remapping changed lifecycle identity/result')
    frozen_csf=CSF.apply(before)
    if frozen_csf['retired_this_apply']!=0:
        raise ValueError('Frozen CSF baseline state was unexpectedly rebuilt')
    # Reject partial/unknown owned input before restoration mutates anything.
    probe={'els':[copy.deepcopy(e)for e in expected['els']if e.get('grp')in ('STAIR1-B','STAIR1-G','STAIR1-2','STAIR2-2')or e['id']in EC.data()['records']], 'meta':{}}
    next(e for e in probe['els']if e['id']in EC.data()['records'])['g'][3]+=.01
    frozen=copy.deepcopy(probe)
    try:restore_before_post(probe)
    except ValueError:pass
    else:raise ValueError('Unknown equipment extent was accepted')
    if probe!=frozen:raise ValueError('Rejected restoration mutated input')
    # Hook placement is checked by syntax-tree/source ordering without invoking
    # the file's import-time pipeline side effects.
    import ast
    post=(ROOT/'pipeline/post_model.py').read_text();ast.parse(post)
    if not(post.index('_FC_POST.capture_before_K_cleanup')<post.index('_COMPLETION_POST.restore_before_post')<post.index('_CSF.restore_before_post')):
        raise ValueError('Upper continuation hook order is wrong')
    if not(post.index('_DHC_REVIEW.refresh(M, _cc)')<post.index('_COMPLETION_POST.apply_after_legacy')<post.index('_INV.build(M)')):
        raise ValueError('Lower continuation hook order is wrong')
    proof={'schema':'c4.completion-post-adapter-test.v1','pass':True,
        'staged_before_sha256':CB.sha(stage/'before-model.json'),'staged_after_sha256':CB.sha(stage/'after-model.json'),
        'adapter_matches_staged_after_except_runtime_provenance':True,'different_top_level_keys':different,
        'controlled_restore_exact_members':len(controlled),'unrelated_full_elements_preserved':True,
        'restore_lifecycle_identity_preserved':True,'frozen_CSF_pending_guard_pass':True,
        'unknown_extent_preflight_atomic':True,'post_hook_placement_verified':True,
        'source_replay_checks':len(result['stairs']['source_checks']),
        'no_full_post_build_executed':True,'adapter_run':result['proof']}
    return proof


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--verify-stage',type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(verify_staged(args.verify_stage),ensure_ascii=False,indent=2))
