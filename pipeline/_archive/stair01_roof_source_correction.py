"""Undo only the source-disproved STAIR1-R flight and its causal cap cuts."""
import copy,functools,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA_PATH=Path(__file__).with_name('data')/'stair01_roof_source_correction.json'
FROZEN_DATA_SHA='744205d5d6e609c857282781f399d4fa661cebf9efa7ad10fedc22602c6336c3'
SCHEMA='c4.stair01-roof-source-correction.v1'
TYPES={}

@functools.lru_cache(maxsize=2)
def _verify(text,pdf_stats):
 if hashlib.sha256(text.encode()).hexdigest()!=FROZEN_DATA_SHA:raise ValueError('SCR frozen source ledger changed')
 D=json.loads(text)
 sys.path.insert(0,str(ROOT/'tools'))
 from check_stair01_roof_source_correction import source_facts,ledger_errors
 errors=ledger_errors(D)+source_facts(D)['errors']
 if errors:raise ValueError('SCR original source/ledger guard: '+','.join(errors))
 return True

def _data():
 text=DATA_PATH.read_text();D=json.loads(text);paths=sorted({q['source_pdf']for q in D['source_pages'].values()})
 _verify(text,tuple((p,Path(p).stat().st_mtime_ns,Path(p).stat().st_size)for p in paths));return D

def _identity(e,row):return(e['id'],e['c'],e['t'],e['l'],e.get('m'))==(row['id'],row['c'],row['t'],row['l'],row.get('m'))

def _ref(M,t):
 pool=M.setdefault('sp',[])
 if t not in pool:pool.append(t)
 return pool.index(t)

def apply(M,els=None):
 D=_data();els=M['els']if els is None else els;by={e['id']:e for e in els};count={eid:sum(e['id']==eid for e in els)for eid in set(D['records'])|set(D['retirement_records'])}
 # Entire preflight runs before geometry, references, metadata or list mutation.
 for e in els:
  if e.get('grp')=='STAIR1-R'or(e.get('grp')or'').startswith('rail-STAIR1-R'):
   if e['id']not in D['retirement_records']:raise ValueError('SCR unknown flight/rail identity: '+e['id'])
  if(e.get('a')or{}).get('stair01_roof_source_correction')and e['id']not in D['records']:raise ValueError('SCR unexpected source claim')
 for eid,row in D['retirement_records'].items():
  e=by.get(eid)
  if e is None:continue
  if count[eid]!=1 or not _identity(e,row)or e['g']!=row['g']or e.get('grp')!=row.get('grp'):raise ValueError('SCR exact retirement identity/full geometry: '+eid)
 for eid,row in D['records'].items():
  e=by.get(eid);known=[q['g']for q in row['known_exact_input_geometries']]
  if e is None or count[eid]!=1 or not _identity(e,row)or e.get('grp')is not None or e['g']not in known:raise ValueError('SCR preserved-cap identity/full geometry: '+eid)
 changes=[];retired=[copy.deepcopy(by[eid])for eid in D['retirement_records']if eid in by]
 els[:]=[e for e in els if e['id']not in D['retirement_records']]
 for eid,row in D['records'].items():
  e=by[eid];before=copy.deepcopy(e['g']);e['g']=copy.deepcopy(row['restored_before_TRO_g']);a=e.setdefault('a',{});a.pop('opening_note',None)
  # Remove only the superseded TROv1 source-mask attributes before TROv2 reapplies.
  if eid=='S.slab-T-0009':
   for k in ['top_roof_shaft_openings_source','top_roof_shaft_source_record','top_roof_shaft_source_data_sha256','top_roof_shaft_after_geometry_sha256','source_openings','clipped_source_voidrings']:
    a.pop(k,None)
   a['source_opening_plan_XY_verified']=False  # Restored fullcap has no void mask until TROv2.
  a.update(stair01_roof_source_correction=True,stair01_roof_source_data_sha256=FROZEN_DATA_SHA,
    source_geometry_review='preserved_procedural_cap_undo_source_disproved_stair_headcut',
    source_preserved_baseline_not_source_authority=True,source_outer_XY_verified=False,
    source_absolute_Z_verified=False,source_Z_verified=False,source_material_verified=False,source_physical_body_verified=False,source_dimensions_verified=False,
    stair01_roof_correction_note='إلغاء قصHEAD2.05م/buffer4سم الناتج عن جناحR→T غيرمرسوم. آخر درج01 ينتهي عندبسطةالسطح+23.25؛+26.85 غطاءفوقه. المجالالخارجي والمناسيب والمواد محفوظةإجرائيًا،ولا تُقبلمنالمصدر بهذهالاستعادة.')
  e.pop('q',None);e['s']=[_ref(M,t)for t in ['ARCH2 ص1–2 A600/A601 وARCH1 ص8–9 A105/A106: نهايةدرج01 عندبسطةالسطح،وغطاءTOP ROOF فوقها','STR ص24: غطاءدرج01 CL+26.65 وتسليحالمسقط؛عكسقصإجرائيقديم فقط دونإثباتالمجالالخارجي أوZ أوالمادة']]
  if before!=e['g']:changes.append({'id':eid,'before_g':before,'restored_before_TRO_g':copy.deepcopy(e['g'])})
 result={**D['summary'],'source_data_sha256':FROZEN_DATA_SHA,'retired_this_apply':len(retired),'retired_ids_this_apply':[e['id']for e in retired],'retired_inventory_ids':list(D['retirement_records']),'changed_caps_this_apply':len(changes),'changes':changes,'retirement_installation_or_quantity_acceptance':False}
 M.setdefault('meta',{})['stair01_roof_source_correction']=result;return result

build=apply
