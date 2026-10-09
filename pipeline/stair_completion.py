# -*- coding: utf-8 -*-
"""Guarded source-finished surfaces for STAIR1-B/G. No model file IO.

Apply after core_stairs_source_surfaces.apply. Restore before that module's
restore_before_post. This layer owns exactly42 old IDs and retains10 assemblies.
"""
import copy, hashlib, json
from pathlib import Path
import core_stairs_source_surfaces as CSF
DATA_PATH=Path(__file__).parent/'data'/'stair_completion.json'
DATA_SHA='3ca2472969e72051c2ca00412906395f3fe65d5194688a5a4284cafbcc9c6db4'
TYPES=copy.deepcopy(CSF.TYPES)

def data():
 b=DATA_PATH.read_bytes()
 if hashlib.sha256(b).hexdigest()!=DATA_SHA:raise ValueError('stair_completion: source data SHA changed')
 D=json.loads(b)
 if hashlib.sha256(Path(D['source_pdf']).read_bytes()).hexdigest()!=D['source_pdf_sha256']:raise ValueError('stair_completion: original PDF SHA changed')
 return D

def _records(D):
 before={e['id']:e for g in D['groups']for e in g['before_records']}
 after={e['id']:copy.deepcopy(e)for g in D['groups']for e in g['after_records']}
 for e in after.values():e['a']['stair_completion_data_sha256']=DATA_SHA
 return before,after

def _state(M,D):
 before,after=_records(D);by={e['id']:e for e in M['els']}
 if len(by)!=len(M['els']):raise ValueError('stair_completion: duplicate identity')
 present=set(before)&set(by)
 old=present==set(before)and all(CSF.signature(by[k])==CSF.signature(e)for k,e in before.items())
 final=present==set(after)and all(CSF.signature(by[k])==CSF.signature(e)and all(by[k].get('a',{}).get(a)==b for a,b in e['a'].items())for k,e in after.items())
 if not(old or final):raise ValueError('stair_completion: partial or unknown geometry/type/level/identity state')
 # The two +10.10 groups are still byte-for-byte source signature guards.
 held=CSF.data()['pending_preserved_records']
 for k,e in held.items():
  if e['grp']in D['unresolved_groups']and (k not in by or CSF.signature(by[k])!=CSF.signature(e)):raise ValueError('stair_completion: held +10.10 member changed '+k)
 return old,final,before,after,by

def apply(M,els=None):
 if els is not None and els is not M['els']:raise ValueError('stair_completion: pass M els by identity')
 D=data();old,final,before,after,by=_state(M,D)
 checks=CSF.generation_checks(after)
 if any(c['errors']for c in checks):raise ValueError('stair_completion: degenerate/nonfinite source mesh')
 old_index={e['id']:i for i,e in enumerate(M['els'])}
 retired_to_new={k:v for g in D['groups']for k,v in g['retired_to_new'].items()}
 if old:
  refs={s:i for i,s in enumerate(M.setdefault('sp',[]))}
  source='ARCH2 ص1 A600 المحاور الأصلية والتفاصيل المحلية؛ ص2 A601 نوسينغ التشطيب ومناسيب الرحلات؛ أسطح مفتوحة فقط'
  if source not in refs:refs[source]=len(M['sp']);M['sp'].append(source)
  out=[]
  for e in M['els']:
   if e['id']not in before:out.append(e)
   elif e['id']in after:
    n=copy.deepcopy(after[e['id']]);n['s']=[refs[source]];out.append(n)
  M['els'][:]=out
 M.setdefault('types',{}).update(copy.deepcopy(TYPES))
 stats={**D['summary'],'source_data_sha256':DATA_SHA,'source_joint_residuals':copy.deepcopy(D['source_joint_residuals']),'scope':D['scope']}
 M.setdefault('meta',{})['stair_completion']=stats
 new_index={e['id']:i for i,e in enumerate(M['els'])}
 return{**stats,'retired_this_apply':len(before)-len(after)if old else 0,'checks':checks,'global_findings':[],'uncovered':[],'old_to_new_indices':{i:new_index[k]for k,i in old_index.items()if k in new_index},'retired_indices':[old_index[k]for k in retired_to_new if k in old_index],'retired_to_new':retired_to_new,'retired_to_new_scope':'procedural group membership only; one-to-many aliases MUST NOT become physical connection edges'}

def restore_before_post(M,els=None):
 if els is not None and els is not M['els']:raise ValueError('stair_completion: pass M els by identity')
 D=data();old,final,before,after,by=_state(M,D)
 if old:return {'restored_this_apply':0,'old_bodies':42}
 groups={g['group']:g['before_records']for g in D['groups']};seen=set();out=[]
 for e in M['els']:
  if e['id']not in after:out.append(e)
  elif e['grp']not in seen:out.extend(copy.deepcopy(groups[e['grp']]));seen.add(e['grp'])
 if seen!=set(groups):raise ValueError('stair_completion: group insertion incomplete')
 M['els'][:]=out;M.setdefault('meta',{}).pop('stair_completion',None)
 return {'restored_this_apply':42,'removed_source_assemblies':10}

def original_pending_view(M):
 """Read-only compatibility view for the frozen29-assembly CSF checker.

The old checker explicitly owns the preceding phase's84 pending records.
Never change its frozen data: validate this layer first, then audit this view.
 """
 D=data();old,final,before,after,by=_state(M,D)
 if old:return M
 V={**M,'els':copy.deepcopy(M['els']),'meta':copy.deepcopy(M.get('meta',{}))}
 restore_before_post(V);return V

def issue_records(M):
 D=data();old,final,before,after,by=_state(M,D)
 if not final:raise ValueError('stair_completion: issue records require corrected state')
 ids=list(after);j=D['source_joint_residuals']
 return [
 {'id':'DP-STAIR-COMPLETION-B-G','title':'تصحيح أسطح درج01 للبدروم والأرضي من التفاصيل والقطاع','status':'corrected','source':'ARCH2 ص1 A600 المحاور Q/P/O و4/3؛ ص2 A601 نوسينغ التشطيب4916–4936','note':'استبدلت42 كتلة إجرائية بـ10 تجميعات سطح:52 نائمة و58 قائمة و4 بسطات. البدروم6+11+8 من−3.50 إلى+.35، والأرضي11+11+11 عبر+.35/+2.15/+3.95/+5.75. نوسينغ منتصف الأرضي يستمد X من القطاع الأصلي وY من وجهي المسقط. لا سماكة أو مادة أو تسليح أو ارتكاز معتمد.','level':None,'xy_cm':None,'z_m':None,'elements':ids,'before':{'procedural_bodies':42},'after':D['summary']},
 {'id':'DP-STAIR-COMPLETION-SOURCE-RESIDUALS','title':'فروق الرسم عند وصل إسقاطات السلالم محفوظة','status':'source_gap','source':'A600 تفصيلا البدروم والأرضي؛ A601 نوسينغ منتصف الأرضي','note':f"فرق X لوصلة البدروم {j['B_local_A600_nosing_join_X_cm']:.8f}سم، وفرق Y {j['B_local_A600_low_face_Y_cm']:.8f}سم. أكبر فرق مقارنة لنوسينغ قطاع الأرضي ومسقطه {max(abs(v)for v in j['G_middle_section_to_plan_nosing_deltas_X_cm']):.8f}سم. لم تسحب الحواف أو تدمج بمتوسط. هذه فروق تسجيل/إسقاط مصدرية، لا فتحة مقاسة بالموقع ولا اتصال إنشائي مقبول.",'level':None,'xy_cm':None,'z_m':None,'elements':ids,'before':None,'after':j},
 {'id':'DP-STAIR-COMPLETION-BODY','title':'الأجسام الخرسانية ومادة السلالم واتصالاتها غير مثبتة','status':'source_gap','source':'A600/A601 أسطح النهاية فقط','note':'الأسطح مفتوحة بلا بطن أو سماكة مستحدثة. صب الخرسانة والتسليح والمادة والارتكاز والاتصالات تحتاج شاهدًا مستقلًا. مجموعتا الدور الثاني42 جسمًا باقيتان دون تغيير لتعارض+10.10؛ لا اعتماد+11.00 بالحساب.','level':None,'xy_cm':None,'z_m':None,'elements':ids,'before':None,'after':{'physical_body_accepted':False,'held_groups':D['unresolved_groups'],'held_bodies':42}}
 ]

def apply_issues(M):
 rows=issue_records(M);owned={q['id']for q in rows};dd=M.setdefault('drawingIssues',[]);dd[:]=[q for q in dd if q['id']not in owned]+rows
 return {'owned_issue_ids':sorted(owned),'physical_acceptance':False}

def audit(M,source_replay=True):
 D=data();old,final,before,after,by=_state(M,D);checks=CSF.generation_checks(after);source=[]
 if source_replay:
  import fitz
  from importlib.util import spec_from_file_location,module_from_spec
  # Original operators and text chars are compared independently to the frozen data.
  def serial(it):
   if it[0]=='l':return ['l',list(it[1]),list(it[2])]
   if it[0]=='qu':return ['qu',[list(p)for p in it[1]]]
   if it[0]=='re':return ['re',list(it[1]),it[2]]
   return [it[0],*[list(p)for p in it[1:]]]
  with fitz.open(D['source_pdf'])as doc:
   drawings={p:doc[p-1].get_drawings()for p in {r['page']for r in D['raw_drawings']}}
   texts={p:doc[p-1].get_texttrace()for p in {r['page']for r in D['raw_texts']}}
   for v in D['source_renderings']:
    pix=doc[v['source_page']-1].get_pixmap(matrix=fitz.Matrix(v['matrix_scale'],v['matrix_scale']),clip=fitz.Rect(v['clip_pdf_pt']),alpha=False,annots=v['annots']);source.append({'ref':v['file'],'kind':'raw_pdf_rendering','pass':hashlib.sha256(pix.tobytes('png')).hexdigest()==v['png_sha256']})
   for r in D['raw_drawings']:
    d=drawings[r['page']][r['drawing_index']];ok=d.get('layer')==r['layer']and d['type']==r['type']and d.get('closePath')==r['closePath']and[serial(it)for it in d['items']]==r['items'];source.append({'ref':f"A{599+r['page']}:{r['drawing_index']}",'kind':'raw_drawing','pass':ok})
   for r in D['raw_texts']:
    t=texts[r['page']][r['texttrace_index']];ok=''.join(chr(c[0])for c in t['chars'])==r['literal']and list(t['bbox'])==r['bbox']and[{'unicode':c[0],'origin':list(c[2]),'bbox':list(c[3])}for c in t['chars']]==r['chars'];source.append({'ref':f"page{r['page']}:trace{r['texttrace_index']}",'kind':'raw_text','pass':ok})
 errs=[]
 if not final:errs.append('correction not applied')
 if any(not s['pass']for s in source):errs.append('original source replay failed')
 if any(c['errors']for c in checks):errs.append('mesh generation check failed')
 return {'pass':not errs,'checks':checks,'source_checks':source,'global_findings':errs,'uncovered':[],'summary':D['summary'],'source_joint_residuals':D['source_joint_residuals']}
