"""Proposed post-only stage adapter. No source extraction or saved-model IO.

Uses the immutable FHC source packet and an independently bounded continuity
ledger for11 existing derived display links. Never supplies physical ports.
"""
import copy,hashlib,json
from pathlib import Path
import fire_cabinet_source as FC
LEDGER_PATH=Path(__file__).with_name('fire_cabinet_preserved_display_links.json')
LEDGER_SHA='ff6e14d23002e5ef516428121b0fe3df71d634912630108e731b07d04c6a5e68'
def ledger():
 raw=LEDGER_PATH.read_bytes()
 if hashlib.sha256(raw).hexdigest()!=LEDGER_SHA:raise ValueError('FHC continuity ledger changed')
 D=json.loads(raw)
 if D['fhc_source_data_sha256']!=FC.FROZEN_SHA or len(D['records'])!=11 or set(D['records'])!=set(D['exact_ids']):raise ValueError('FHC continuity exact inventory')
 return D
def reserved_ids():return set(ledger()['reserved_K_ids'])
def _by(els):
 E={e['id']:e for e in els}
 if len(E)!=len(els):raise ValueError('FHC post duplicate identity')
 return E
def capture_before_K_cleanup(M,els=None):
 E=_by(M['els']if els is None else els);D=ledger()
 for eid,r in D['records'].items():
  if E.get(eid)!=r['before_e']:raise ValueError('FHC existing derived-link fullobject guard: '+eid)
 return {'ledger_sha256':LEDGER_SHA,'records':copy.deepcopy(D['records'])}
def apply_generated_after_mep_merge(M,els=None):
 """Exactly24 regenerated source objects, before q/support/connector passes."""
 els=M['els']if els is None else els;E=_by(els);D=FC.data();L=ledger();plans=[]
 expected={eid:r['before_e']for eid,r in D['records'].items()}
 expected.update({r['id']:r['before_e']for r in D['retirements']if r['reason']=='false_second_cabinet_from_open_door_leaf'})
 if {e['id']for e in els if e.get('t')=='fhc'}!=set(expected):raise ValueError('FHC generated exact24 identity set')
 for eid,before in expected.items():
  signature=copy.deepcopy(before);signature.pop('q',None)
  # No absent field except the generated q is accepted; no field is ignored.
  if E[eid]!=signature:raise ValueError('FHC generated full signature guard: '+eid)
 for eid in L['reserved_K_ids']:
  if eid in E:raise ValueError('FHC preconnector stage still contains reserved K: '+eid)
 leaf={r['id']for r in D['retirements']if r['reason']=='false_second_cabinet_from_open_door_leaf'}
 for eid,r in D['records'].items():plans.append((E[eid],FC._after(r)))
 # All preflight above; the source marker keeps no_connectors=True.
 for e,after in plans:e.clear();e.update(after)
 els[:]=[e for e in els if e['id']not in leaf]
 stats={**D['summary'],'source_data':'pipeline/data/fire_cabinet_source.json','source_data_sha256':FC.FROZEN_SHA,'retired_ids':D['exact_retired_ids'],'retired_this_apply':len(leaf),'derived_ghost_stubs_absent_before_connectors':11,'source_stage':'regenerated_mep_bg_before_q_support_connectors','retired_leaf_to_survivor_source_identity_only':D['retired_leaf_to_survivor'],'historical_withdrawn_clashes':copy.deepcopy(D['withdrawn_clashes']),'scope_limit_ar':D['scope_limit_ar']}
 M.setdefault('meta',{})['fire_cabinet_source']=stats
 M.setdefault('types',{}).update(copy.deepcopy(FC.TYPES))
 return {'retired_leaves_this_stage':12,'preserved_source_graphic_markers':12,'connectors_new_to_markers_prohibited':True}
def restore_after_connectors(M,captured,els=None):
 els=M['els']if els is None else els;E=_by(els);D=ledger()
 if captured!={'ledger_sha256':LEDGER_SHA,'records':D['records']}:raise ValueError('FHC captured ledger drift')
 plans=[]
 for eid,r in D['records'].items():
  if eid in E:raise ValueError('FHC reserved derived ID collision: '+eid)
  for role in ['from_record','to_record']:
   expected=r[role];e=E.get(expected['id'])
   if not e or any(e.get(k)!=v for k,v in expected.items()):raise ValueError('FHC derived-link endpoint changed: '+eid+'/'+role)
  if E[r['before_e']['a']['to']].get('a',{}).get('no_connectors')is not True:raise ValueError('FHC source marker lost no_connectors flag')
  plans.append(copy.deepcopy(r['before_e']))
 retired_ghost={r['id']for r in FC.data()['retirements']if r['reason']=='derived_stub_to_false_open_leaf_identity'}
 if set(E)&retired_ghost:raise ValueError('FHC retired ghost connector reappeared')
 els.extend(plans)
 M.setdefault('meta',{})['fire_cabinet_preserved_display_links']={'ledger_sha256':LEDGER_SHA,'ids':D['exact_ids'],'restored':11,'source_ports_verified':False,'source_Z_verified':False,'source':'continuity_of_existing_derived_display_network_only','source_pipeline_state':'restored_after_CN_before_LC','reason_ar':D['reason_ar']}
 return {'restored':11,'exact_objects_preserved':True,'ports_or_source_connection_accepted':False}
