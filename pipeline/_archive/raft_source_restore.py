# coding:utf-8
"""Correct only two original raft footprints from STR11, retaining all Z values."""
import copy
import hashlib
import json
from pathlib import Path
from shapely.geometry import Polygon

DATA_PATH=Path(__file__).with_name('data')/'raft_source_restore.json'
def _sha(v):return hashlib.sha256(json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def build(M,els=None,verbose=False):
 els=M['els'] if els is None else els;D=json.loads(DATA_PATH.read_text());by={e['id']:e for e in els}
 old_other={e['id']:copy.deepcopy(e) for e in els if e['id'] not in D['records']}
 changed=[]
 text=('STR ص11: S-COLUMN رسم3561 حد اللبشة الخارجي المغلق، وPILES$0$ST-PILE-Caps رسم6285 حدPC1 المغلق. '
       'annotation63/xref1250 SLAB−80cm THICK RAFT وannotation67/xref1254 PC1−150cm. '
       'صُحح المجال80سم إلى الحد الخارجي ناقص PC1 من الخام؛ لم يُقص PC1 ولم يُستخدم buffer0. '
       'فرق الحد الخام0.00043سم دقة PDF؛ الامتداد1سم في المجسم السابق خطأ إدخال يدوي. '
       'مناسيب Z القائمة محفوظة دون ترقيتها إلى دليل مصدر مطلق؛ المادة والتسليح والارتكاز خارج نطاق التحقق.')
 if text not in M['sp']:M['sp'].append(text)
 si=M['sp'].index(text)
 for eid,row in D['records'].items():
  if eid not in by:raise ValueError('Missing controlled raft identity '+eid)
  e=by[eid];q=row['source']
  if (e['c'],e['t'],e['l'])!=(row['category'],row['type'],row['level']):raise ValueError('Raft identity guard differs '+eid)
  if e['g'] not in (row['before_g'],row['after_g']):raise ValueError('Raft geometry guard differs '+eid)
  if row['before_g'][2:4]!=row['after_g'][2:4]:raise AssertionError('Raft Z changed in source ledger')
  if not Polygon(row['after_g'][1],row['after_g'][4]).is_valid:raise AssertionError('Invalid source raft domain')
  if e['g']!=row['after_g']:changed.append(eid);e['g']=copy.deepcopy(row['after_g'])
  e.setdefault('a',{}).update(source_kind=q['source_kind'],source_page=q['source_page'],source_sheet=q['source_sheet'],
   source_pdf_sha256=q['source_pdf_sha256'],source_drawing_indices=copy.deepcopy(q['source_drawing_indices']),
   source_pdf_points=copy.deepcopy(q['source_pdf_points']),source_transform=copy.deepcopy(q['source_transform']),
   source_xy=copy.deepcopy(q['source_xy']),source_locked_xy=True,source_semantics_checked=True,
   source_structural_XY_verified=eid=='S.raft-B-0002',source_footprint_derived=eid=='S.raft-B-0001',
   source_Z_verified=False,source_thickness_verified=True,source_thickness_cm=row['thickness_cm'],
   source_material_verified=False,source_material_class_verified=False,source_physical_color_verified=False,
   source_reinforcement_verified=False,source_bearing_verified=False,
   raft_source_restore_record=eid,source_correction_before_g=copy.deepcopy(row['before_g']),
   source_correction_after_g=copy.deepcopy(row['after_g']),source_annotation=copy.deepcopy(q['source_annotation']),
   assumed='XY أعيد من المسقط الخام؛ سماكة80/150سم موسومة. Z والمادة القائمة محفوظة ولم تُراجع من المصدر هنا؛ اللون ليس طلاء تنفيذيًا مثبتًا. فرق إحداثيات الحافتين0.00043سم دقة PDF، ولا قص PC1 أو ملء buffer0.')
  if si not in e['s']:e['s'].append(si)
 unchanged=len(old_other)==sum(e['id'] in old_other for e in els) and all(e==old_other[e['id']] for e in els if e['id'] in old_other)
 if not unchanged:raise AssertionError('Raft source correction changed another element')
 stats={'ids':list(D['records']),'changed_this_run':changed,'Z_and_thickness_unchanged':True,
  'all_other_elements_unchanged':unchanged,'geometry_sha256':_sha([(i,by[i]['g']) for i in D['records']]),
  'data_sha256':hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
  'source_geometry_relation':copy.deepcopy(D['source_geometry_relation']),'pending':copy.deepcopy(D['pending_ar'])}
 M.setdefault('meta',{})['raft_source_restore']=stats
 if verbose:print('RFT source footprints:',len(changed),'other elements unchanged:',unchanged)
 return stats
