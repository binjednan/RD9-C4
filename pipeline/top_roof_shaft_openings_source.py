"""Local STR24 shaft-void subtraction; preserve every other structural domain."""
import copy
import functools
import hashlib
import json
from pathlib import Path
DATA_PATH=Path(__file__).with_name('data')/'top_roof_shaft_openings_source.json'
FROZEN_DATA_SHA='5d0c5f960609f47d9765f3b49129534de8b7511c6dff2fc9361c793d5fa2db7f'
SCHEMA='c4.top-roof-shaft-openings-source.v2'
TYPES={}

def _items(v):
 import fitz
 if isinstance(v,fitz.Point):return[v.x,v.y]
 if isinstance(v,fitz.Quad):return[_items(q)for q in v]
 if isinstance(v,fitz.Rect):return list(v)
 if isinstance(v,(list,tuple)):return[_items(q)for q in v]
 return v

def _sha(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

@functools.lru_cache(maxsize=2)
def _verify(text,pdfpath,mtime,size):
 import fitz,lib,reg
 from shapely.geometry import Polygon,box
 from shapely.ops import unary_union
 if hashlib.sha256(text.encode()).hexdigest()!=FROZEN_DATA_SHA:raise ValueError('TRSO frozen source ledger changed')
 D=json.loads(text)
 if D['schema']!=SCHEMA or set(D['records'])!={'S.slab-T-0009','S.slab-T-0010'}:raise ValueError('TRSO frozen identity/schema changed')
 if hashlib.sha256(Path(pdfpath).read_bytes()).hexdigest()!=D['source_pdf_sha256']:raise ValueError('TRSO original PDF changed')
 with fitz.open(pdfpath)as doc:
  page=doc[23];ds=page.get_drawings();tt=page.get_texttrace();grid=[d for d in ds if d.get('layer')and('GRID'in d['layer'].upper()or'AXIS'in d['layer'].upper())and'IDEN'not in d['layer'].upper()];v,h=reg.grid_clusters(None,layers=None,drawings=grid,minlen=50);T=reg.register_free(v,h)
  if v!=D['raw_grid_v']or h!=D['raw_grid_h']or T!=D['source_transform']:raise ValueError('TRSO original grid registration changed')
  for row in D['raw_grid_primitives']:
   d=ds[row['drawing_index']]
   if d.get('layer')!=row['layer']or _items(d['items'])!=row['raw_items']:raise ValueError('TRSO original grid operator changed')
  for note in D['source_notes']:
   t=tt[note['texttrace_index']]
   if t.get('layer')!=note['layer']or ''.join(chr(c[0])for c in t['chars'])!=note['literal_text']or _items(t['chars'])!=note['raw_chars']:raise ValueError('TRSO original notes changed')
  for row in D['source_openings']:
   for di,it,pts,typ in zip(row['source_drawing_indices'],row['source_raw_items'],row['source_pdf_points'],row['source_raw_types']):
    d=ds[di]
    if d.get('layer')!='SHAFT'or _items(d['items'])!=it or _items(lib.flat_path(d))!=pts or d['type']!=typ:raise ValueError('TRSO original closed shaft/X primitive changed')
  voids=unary_union([Polygon(s['source_xy_polygon'])for s in D['source_openings']])
  for row in D['records'].values():
   def domain(g):return Polygon(g[1],g[4]if len(g)>4 else [])if g[0]=='p'else box(*g[1:5])
   if _sha(row['before_g'])!=row['before_geometry_sha256']or _sha(row['after_g'])!=row['after_geometry_sha256']:raise ValueError('TRSO preserved/corrected geometry fingerprint changed')
   after=domain(row['after_g']);expected=domain(row['before_g']).difference(voids)
   if not after.is_valid or after.symmetric_difference(expected).area>1e-7:raise ValueError('TRSO nonlocal domain change')
 return True

def _data():
 text=DATA_PATH.read_text(encoding='utf-8');D=json.loads(text);pdf=Path(D['source_pdf']);st=pdf.stat();_verify(text,str(pdf),st.st_mtime_ns,st.st_size);return D

def _identity(slab,row):return(slab['id'],slab['c'],slab['t'],slab['l'],slab.get('m'))==(row['id'],row['c'],row['t'],row['l'],row['m'])

def _attributes(row,D):
 ids={c['source_opening_id']for c in row['clipped_voidrings']};sources=[copy.deepcopy(s)for s in D['source_openings']if s['id']in ids]
 return {'top_roof_shaft_openings_source':True,'top_roof_shaft_source_record':row['id'],'top_roof_shaft_source_data_sha256':FROZEN_DATA_SHA,'top_roof_shaft_after_geometry_sha256':row['after_geometry_sha256'],
         'source_page':'STR:24','source_kind':'derived_preserved_slab_domain_minus_original_closed_SHAFT_voids','source_locked_xy':True,
         'source_drawing_indices':[i for s in sources for i in s['source_drawing_indices']],
         'source_pdf_points':[p for s in sources for p in s['source_pdf_points']],
         'source_transform':copy.deepcopy(D['source_transform']),'source_pdf_sha256':D['source_pdf_sha256'],
         'source_openings':sources,'clipped_source_voidrings':copy.deepcopy(row['clipped_voidrings']),
         'source_opening_plan_XY_verified':True,'source_outer_XY_verified':False,'source_absolute_Z_verified':False,'source_Z_verified':False,'source_material_verified':False,'source_physical_body_verified':False,'source_dimensions_verified':False,
         'source_geometry_review':'source_bound_opening_subtraction_only','source_preserved_baseline_not_source_authority':True,
         'source_coordination_gap':'STR24 يطلب تنسيق أبعاد الفتحات معARCH؛ موضع SHAFT المرسوم مثبت، وتسليح الحواف والتحمل والتفاصيل التنفيذية غير مثبتة بهذه الموجة.',
         'assumed':'طرح فتحات SHAFT الست المرسومة فقط من مجال البلاطة المحفوظ. حدود البلاطة القديمة ومناسيب26.40–26.65 وسماكة25سم محفوظة إجرائيًا؛ ليست إثباتًا كاملاً من المصدر. لا اعتماد للمادة أوgrade أوالتسليح أوالتحمل.'}

def _ref(M,text):
 pool=M.setdefault('sp',[])
 if text not in pool:pool.append(text)
 return pool.index(text)

def apply(M,els=None):
 D=_data();els=M['els']if els is None else els;by={e['id']:e for e in els}
 for eid,row in D['records'].items():
  e=by.get(eid)
  if e is None or sum(q['id']==eid for q in els)!=1 or not _identity(e,row)or e['g']not in[row['before_g'],row['after_g']]:raise ValueError('TRSO exact identity/full geometry guard failed: '+eid)
 changes=[]
 for eid,row in D['records'].items():
  e=by[eid];before=copy.deepcopy(e['g']);e['g']=copy.deepcopy(row['after_g']);e.setdefault('a',{}).update(_attributes(row,D));e.pop('q',None)
  refs=['STR ص24: TOP ROOF SLAB LAYOUT؛ حدود فتحات SHAFT المغلقة مع X من أوامر PDF الأصلية','STR ص24: trace2 تسليح الفتحات وتنسيق أبعادها معARCH؛ trace3 سماكة25سم مشروطة فقط','طرح فتحات المصدر محليًا؛ حدود البلاطة ومناسيبها وموادها المحفوظة ليست قبولًا كاملًا من المصدر']
  e['s']=[_ref(M,t)for t in refs]
  if before!=e['g']:changes.append({'id':eid,'before_g':before,'after_g':copy.deepcopy(e['g']),'removed_area_cm2':row['removed_area_cm2']})
 result={**D['summary'],'source_data_sha256':FROZEN_DATA_SHA,'changed_this_apply':len(changes),'changes':changes,'controlled_S_ids':list(D['records'])}
 M.setdefault('meta',{})['top_roof_shaft_openings_source']=result;return result

def opening_polygons(slab):
 """Only seven guarded source clips, including two sides of the shared notch."""
 from shapely.geometry import Polygon
 D=_data();row=D['records'].get(slab.get('id'));a=slab.get('a')or{}
 if row is None or not _identity(slab,row)or slab['g']!=row['after_g']or any(a.get(k)!=v for k,v in _attributes(row,D).items()):raise ValueError('TRSO source mask exact after-domain/metadata guard failed')
 return [Polygon(c['clipped_void_polygon'])for c in row['clipped_voidrings']]

build=apply
