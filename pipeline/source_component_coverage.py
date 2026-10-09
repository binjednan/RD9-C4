"""Post-CC persistence adapter for E6 anchors/FHC12 recess graphic identities.

Future full post only: call after ordinary CC.apply, before serialising. This
does not modify elements, geometry, LC or write files. Targeted native audits are
called only when a reviewed audit bundle was not supplied by the current caller.
"""
import collections,copy,hashlib,json
def _check(ok,reason):
    if not ok:raise ValueError('Scoped E6/FHC coverage: '+reason)
def _sha(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def _geometry_sha(M):
    return hashlib.sha256(json.dumps(sorted((e['id'],e['g'])for e in M['els']),separators=(',',':')).encode()).hexdigest()
def _audit(result,expected,label):
    summary=result.get('summary')or {};checks=result.get('checks')or []
    _check(summary.get('findings')==0 and summary.get('uncovered')==0 and not result.get('global_findings')and not result.get('uncovered'),label+' global/summary failure')
    ids=[q.get('id')for q in checks]
    _check(len(ids)==len(set(ids))and set(ids)==set(expected),label+' exact target check set differs')
    _check(all(q.get('pass')is True and not q.get('errors')for q in checks),label+' target row failed')
    return {q['id']:q for q in checks}
def refresh(M,report,audits=None):
    import electrical_room_source_corrections as EC
    import fire_cabinet_source as FC
    import check_component_coverage as CC
    E,F=EC.data(),FC.data();owned=set(E['records'])|set(F['records']);retired=set(F['exact_retired_ids']);by={}
    for e in M['els']:by.setdefault(e['id'],[]).append(e)
    _check(all(len(by.get(id,[]))==1 for id in owned),'missing/duplicate controlled element')
    _check(not(set(by)&retired),'source-retired false identity survived')
    _check(len(by)==len(M['els']),'duplicate global identity')
    for id,r in E['records'].items():
        e=by[id][0];old=r['before_e'];a=e.get('a',{})
        _check(e['g']==r['after_g'],'E6 final extent differs: '+id)
        _check(all(e.get(k)==old.get(k)for k in ('id','c','t','l','m','mark','grp')),'E6 identity differs: '+id)
        _check(a.get('source_record_sha256')==r['source_record_sha256']and a.get('source_data_sha256')==EC.DATA_SHA256,'E6 record binding missing: '+id)
    for id,r in F['records'].items():
        e=by[id][0];expected=FC._after(r)
        _check(all(e.get(k)==expected.get(k)for k in ('id','c','t','l','m','g','mark','s')),'FHC source graphic identity/geometry differs: '+id)
        _check(all(e.get('a',{}).get(k)==v for k,v in expected.get('a',{}).items()if k.startswith('source_')or k=='no_connectors'),'FHC source evidence/flags differ: '+id)
    for id in owned:
        a=by[id][0].get('a',{})
        for flag in ('source_physical_body_verified','source_Z_verified','source_absolute_Z_verified','source_material_verified','source_mount_verified','source_ports_verified','source_contact_verified','source_colour_verified'):
            _check(a.get(flag)is not True,'unsupported whole-body/physical promotion: '+id+'/'+flag)
    if audits is None:
        import check_electrical_room_source as EG
        import check_fire_cabinet_source as FG
        audits={'E6':EG.audit(M),'FHC':FG.audit(M)}
    ec=_audit(audits['E6'],E['records'],'E6');fc=_audit(audits['FHC'],F['records'],'FHC')
    retirement=audits['FHC'].get('retirement_checks')or []
    _check(len(retirement)==len(retired)and {q.get('id')for q in retirement}==retired and all(q.get('pass')is True and not q.get('errors')for q in retirement),'FHC retirement audit differs')
    page_checks=audits['FHC'].get('source_checks')or []
    _check(len(page_checks)==4 and all(q.get('pass')is True and not q.get('errors')for q in page_checks),'FHC raw page checks failed/missing')
    _check(report['model_geometry_sha256']==_geometry_sha(M),'ordinary full CC report is stale')
    out=copy.deepcopy(report);rows={q['id']:q for q in out['rows']}
    _check(len(rows)==len(out['rows']),'CC row identity repeated')
    for id in retired:rows.pop(id,None);out['details'].pop(id,None)
    _check(set(rows)==set(by),'CC current element set differs')
    checks={**ec,**fc}
    for id in owned:
        e=by[id][0];refs=CC.references(M,e);z,notes=CC.height_basis(M,e,refs);is_e=id in E['records']
        rows[id]={'id':id,'status':'source_checked','xy_basis':'مرساة مركز الجهاز المسمى في المسقط؛ الأبعاد الكلية من جدول مستقل ولا تثبت الجسم التنفيذي كله'if is_e else'مستطيل تجويف FHC المعماري مفحوص؛ ورقة الباب رمز وليست جهازًا ثانيًا','z_basis':z,'source':' / '.join(refs),'findings':['نطاق التحقق مرساة أو بصمة XY فقط؛ الجسم التنفيذي والمنسوب المطلق والخامة والتثبيت والمنافذ غير معتمدة']}
        out['details'][id]={'category':e['c'],'type':e['t'],'level':e['l'],'geometry_kind':e['g'][0],'xy_cm':CC.xy(e['g']),'z_m':CC.z_range(e['g']),'source_refs':refs,'height_assumptions':notes,'evidence':{'scoped_native_source_audit':copy.deepcopy(checks[id])},'needs_original_xy_proof':False,'needs_height_proof':True,'needs_dimension_semantic_review':not is_e,'whole_physical_body_source_accepted':False,'literal_overall_extent_dimensions_verified':is_e}
    out['rows']=[rows[e['id']]for e in M['els']];out['counts']=dict(collections.Counter(q['status']for q in out['rows']));families=collections.defaultdict(collections.Counter)
    for q in out['rows']:families[by[q['id']][0]['c'][0]][q['status']]+=1
    out['by_family']={k:dict(v)for k,v in families.items()};out['height_counts']=dict(collections.Counter(q['z_basis']for q in out['rows']));out['model_elements']=len(M['els']);out['model_geometry_sha256']=_geometry_sha(M)
    out['missing_components']=[q for q in out.get('missing_components',[])if q.get('id')not in retired]
    out.setdefault('raw_new_component_source_inventory',{}).update(electrical_room_source_corrections=copy.deepcopy(audits['E6']),fire_cabinet_source=copy.deepcopy(audits['FHC']))
    out['source_component_coverage_persistence']={'controlled_XY_rows':18,'retired_ids':sorted(retired),'targeted_native_audits_used':True,'whole_physical_body_source_accepted':0,'report_before_sha256':_sha(report),'physical_Z_material_ports_verified':0}
    M['componentReview']=CC.compact(out);return out
