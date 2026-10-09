"""Draw competing stair/down-conductor sources without choosing or moving one.

Owned ALT objects only. The original model and its review decisions are never
edited. Missing horizontal dimensions remain a source illustration with an
explicit unrepresented reason, rather than a stretched NTS section in 3D.
"""
import copy
import json
from pathlib import Path

DATA_PATH=Path(__file__).with_name('data')/'source_stair_lightning_alternatives.json'
OWNER='stair_lightning_sources'
TYPES={
 'alt_source_stair':{'n':'بديل مصدر — درج 01','cf':'derived','asm':['تمثيل مؤقت للمصدر؛ لا اختيار بين المصادر المتعارضة.']},
 'alt_source_down_symbol':{'n':'بديل مصدر — رمز الموصل النازل','cf':'derived','asm':['رمز المسقط في موضعه؛ لا يمثل اتصالًا بين الأدوار.']},
}
MATS={
 'alt_str':{'name':'بديل الرسم الإنشائي','color':'#ef9c36','rough':.8},
 'alt_arch':{'name':'بديل الرسم المعماري','color':'#45adce','rough':.8},
 'alt_ltg':{'name':'بديل رمز الصواعق من المصدر','color':'#b98ae6','rough':.8},
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
        'source_data_file':'pipeline/data/source_stair_lightning_alternatives.json',
        'source_crops':copy.deepcopy(D['crops']),
        'element_evidence':copy.deepcopy(D.get('element_evidence',{})),
        'current_geometry_policy_ar':D['current_geometry_policy_ar'],
    }
    M['sourceStairLightningAlternatives']=report
    return report
