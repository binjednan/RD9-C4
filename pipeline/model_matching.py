# -*- coding: utf-8 -*-
"""Per-element drawing match: position AND shape, with source-specific evidence.

No XY coverage count is promoted into this register. The comparison is against
plans/sections/elevations as available, not an engineering/site certification.
"""
import collections, copy, hashlib, json

CRITERIA_AR = 'مطابقة موقع العنصر وشكله وأبعاده للمخططات والرسومات باستخدام المساقط والواجهات والقطاعات المتاحة؛ لا يكفي فحص XY وحده.'
LABELS = {'matched':'معتمد المطابقة — الموقع والشكل','conflict':'تعارض مسجل','not_reviewed':'لم تُفحص المطابقة الكاملة بعد'}

def geometry_sha(e):
    return hashlib.sha256(json.dumps([e['id'],e['c'],e['t'],e['l'],e['g']],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def build(M, records):
    by={e['id']:e for e in M['els']}
    if len(by)!=len(M['els']):raise ValueError('Duplicate live element ID')
    registry={}
    for raw in records:
        r=copy.deepcopy(raw);eid=r['id']
        if eid not in by:raise ValueError('Drawing match has no live element: '+eid)
        if eid in registry:raise ValueError('Duplicate drawing match: '+eid)
        if r['status']not in ('matched','conflict'):raise ValueError('Invalid reviewed state')
        if r.get('geometry_sha256')!=geometry_sha(by[eid]):raise ValueError('Stale drawing match geometry: '+eid)
        if not r.get('source_refs')or not r.get('proof_file'):raise ValueError('Missing source evidence: '+eid)
        if r['status']=='matched':
            if not all(r.get(k)is True for k in ('position_match','shape_match')):raise ValueError('Partial proof cannot approve: '+eid)
            if r.get('conflict_ids'):raise ValueError('Approved shape cannot carry unresolved shape conflict: '+eid)
        elif not r.get('conflict_ids'):raise ValueError('Unlinked drawing conflict: '+eid)
        registry[eid]=r
    issue_ids={q['id']for q in M.get('drawingIssues',[])}
    for r in registry.values():
        if any(q not in issue_ids for q in r.get('conflict_ids',[])):raise ValueError('Missing conflict in drawing list: '+r['id'])
    counts=collections.Counter(r['status']for r in registry.values())
    counts['not_reviewed']=len(by)-len(registry)
    counts['matched']+=0;counts['conflict']+=0
    result={'schema':'c4.model-position-shape-matching.v1','criteria_ar':CRITERIA_AR,
            'user_definition_ar':'الاعتماد يعني في الموقع والشكل بناءً على المخطط',
            'model_elements':len(by),'reviewed_elements':len(registry),'counts':dict(counts),
            'labels':LABELS,'records':[registry[e['id']]for e in M['els']if e['id']in registry],
            'model_geometry_sha256':hashlib.sha256(json.dumps([[e['id'],e['g']]for e in M['els']],ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),
            'xy_only_is_approval':False,'site_or_operational_acceptance':False,
            'conflicts_do_not_block_other_reviews':True}
    M['modelMatching']=copy.deepcopy(result)
    return result
