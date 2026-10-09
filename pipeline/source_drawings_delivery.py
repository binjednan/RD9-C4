"""Append literal source drawings and keep conflict witnesses lazy in the viewer.

This module changes no original geometry, registrations, source tolerances or
review decisions. It packages the requested alternative sources after analysis.
"""
import copy,importlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'pipeline/data'
COLORS=['#bc6321','#177ca5','#9061bb','#358257','#bc4362','#787327']
MODULES=['source_chw_roof_alternatives','source_stair_lightning_alternatives','source_ramp_ladder_stair_datum_alternatives','source_water_shaft_alternatives']
ALIASES={
 'ALT-STAIR1-G-FLIGHT3-13-11':['DP-STAIR-CONCRETE-G-SECTION-PLAN'],
 'ALT-LIGHTNING-PLAN-11-12-13':['DP-LTG-1','DP-LTG-3','DP-LTG-4','DP-LTG-5','DP-LTG-6','DP-LTG-7','DP-LTG-8','DP-LTG-9','DP-LTG-10'],
 'ALT-CHW-MECH2-32':['DP-CHW-B-M_CHI_S'],
 'ALT-CHW-MECH2-33':['DP-CHW-G-M_CHI_S','DP-CHW-G-M_CHI_R'],
 'ALT-CHW-MECH2-34':['DP-CHW-1-M_CHI_S','DP-CHW-1-M_CHI_R'],
 'ALT-CHW-MECH2-35':['DP-CHW-TY-M_CHI_S','DP-CHW-TY-M_CHI_R'],
 'ALT-CHW-MECH2-36':['DP-CHW-R-M_CHI_S','DP-CHW-R-M_CHI_R'],
 'ALT-CHW-SCHEMATIC-37':['DP-CHW-SCH'],
 'ALT-ARCH1-ROOF-CHILLER':['DP-PG-EQUIP-chiller'],
 'ALT-ARCH1-ROOF-FAHU':['DP-PG-EQUIP-fahu'],
 'ALT-ARCH1-ROOF-TANK':['DP-PG-TANK-SOURCE'],
}

def apply(M,els=None):
    reports=[]
    for name in MODULES:
        reports.append(importlib.import_module(name).apply(M,els))
    import source_removed_candidates,source_missing_electrical_symbols,source_a2300_plants
    source_removed_candidates.apply(M,els)
    source_missing_electrical_symbols.apply(M,els)
    source_a2300_plants.apply(M,els)
    import source_details_loader
    source_details_loader.apply(M,els)
    groups=[]
    for r in reports:
        groups.extend(r.get('conflict_groups',[]))
    values=DATA/'source_value_conflicts.json'
    if values.exists():groups.extend(json.loads(values.read_text())['conflict_groups'])
    by={e['id']:e for e in M['els']}
    compact=[]
    for g in groups:
        gid=g['id']
        C={'id':gid,'issue_ids':g.get('issue_ids')or ALIASES.get(gid)or[gid],'title':g.get('title')or g.get('title_ar')or gid,
           'level':g.get('level')or(g.get('levels')or[None])[0],'note_ar':g.get('note_ar','الشكل الحالي افتراضي مؤقت؛ كل مصدر معروض كما هو.'),'sources':[]}
        for i,s in enumerate(g['sources']):
            t={k:copy.deepcopy(s[k])for k in('label','file','file_key','page','drawing','element_ids','unrepresented_reason')if k in s}
            t['color']=COLORS[i%len(COLORS)];t.setdefault('element_ids',[])
            if any(id not in by for id in t['element_ids']):raise ValueError('Unknown source shape: '+gid)
            vals=copy.deepcopy(s.get('values',{}))
            vals.pop('existing_geometry_unchanged',None)
            # Polygon evidence belongs to the lazy source witness, not the boot model.
            if 'components'in vals:
                vals={'أجسام المصدر':len(vals['components'])}
            if vals:t['values']=vals
            if not t['element_ids'] and not vals and not t.get('unrepresented_reason'):
                t['unrepresented_reason']=s.get('reason_ar')or'بانتظار تأكيدك: موضع المصدر غير مربوط بمحاور المشروع في البيانات المتاحة.'
            C['sources'].append(t)
        compact.append(C)
    M['sourceConflictGroups']=compact
    M.pop('sourceDrawingSummary',None)
    M.pop('sourceStairLightningAlternatives',None)
    M.pop('sourceWaterShaftAlternatives',None)
    M.pop('sourceRampLadderStairDatumAlternatives',None)
    return compact


def display_only(M):
    """Remove the prior per-component verification presentation, not geometry."""
    for key in('modelMatching','raftModelAcceptance','componentReview','materialReview'):M.pop(key,None)
    for e in M['els']:
        e.pop('q',None)
        # Display assumptions remain; placement guesses do not become decisions.
        a=e.get('a',{})
        for key in('source_checked','verified','approval_status','accepted','matching_status'):a.pop(key,None)
    return M
