"""Draw competing water/shaft sources without choosing or moving one.

Owned ALT objects only. The original model and its review decisions are never
edited. Missing horizontal dimensions remain a source illustration with an
explicit unrepresented reason, rather than a stretched NTS section in 3D.
"""
import copy
import json
from pathlib import Path

DATA_PATH=Path(__file__).with_name('data')/'source_water_shaft_alternatives.json'
OWNER='water_shaft_sources'
TYPES={'alt_water_shaft_source':{'n':'بديل مصدر — مياه وشافت','cf':'derived','asm':['رسم مستقل للمصدر؛ التمثيل الحالي افتراضي مؤقت.']}}
MATS={
 'alt_water_source':{'name':'بديل المصدر الميكانيكي','color':'#a37be0','rough':.8},
 'alt_shaft_source':{'name':'بديل المصدر المعماري','color':'#45adce','rough':.8},
}

def data():return json.loads(DATA_PATH.read_text())

def apply(M,els=None):
    """Append deterministic source ALT elements; replay replaces only owned ALT IDs.

    Return file/page counts, conflict source values and unrepresented reasons
    for the caller's lazy index. This does not write files or existing review
    registries, change an original body, or create a source acceptance decision.
    """
    D=data();target=M['els']if els is None else els
    ids={e['id']for e in D['elements']}
    if len(ids)!=len(D['elements']):raise ValueError('Repeated owned alternative identity')
    for e in target:
        if e['id']in ids and (e.get('a')or{}).get('alt_owner')!=OWNER:
            raise ValueError('Alternative identity collides with existing element '+e['id'])
    # Only our previous alternatives can be replaced, and their deterministic
    # location comes from the source ledger, never from the current model.
    target[:]=[e for e in target if (e.get('a')or{}).get('alt_owner')!=OWNER]
    M.setdefault('types',{}).update(copy.deepcopy(TYPES))
    M.setdefault('mats',{}).update(copy.deepcopy(MATS))
    sp=M.setdefault('sp',[])
    for saved in D['elements']:
        e=copy.deepcopy(saved);s=e['a']['alt_source']
        label=f"بديل مصدر: {s['file']}، ص {s['page']}، الرسم "+str(s['drawing'])
        if label not in sp:sp.append(label)
        e['s']=[sp.index(label)];target.append(e)
    report={
        'schema':D['schema'],'owner':OWNER,'element_ids':[e['id']for e in D['elements']],
        'counts_by_file_page':copy.deepcopy(D['counts_by_file_page']),
        'summary':copy.deepcopy(D['summary']),
        'conflict_groups':copy.deepcopy(D['conflict_groups']),
        'current_source_bindings':copy.deepcopy(D['current_source_bindings']),
        'undrawn':copy.deepcopy(D['undrawn']),
        'unrepresented_reasons':copy.deepcopy(D['unrepresented_reasons']),
        'source_data_file':'pipeline/data/source_water_shaft_alternatives.json',
        'source_crops':copy.deepcopy(D['crops']),
        'covered_conflict_ids':copy.deepcopy(D['covered_conflict_ids']),
        'source_inventories':copy.deepcopy(D.get('source_inventories',[])),
        'requested_aliases':copy.deepcopy(D['requested_aliases']),
        'element_evidence':copy.deepcopy(D.get('element_evidence',{})),
        'current_geometry_policy_ar':D['current_geometry_policy_ar'],
    }
    M['sourceWaterShaftAlternatives']=report
    return report
