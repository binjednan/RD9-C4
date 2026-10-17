# -*- coding: utf-8 -*-
"""Draw source signage markers, not invented mounting plates."""
import json,os,re,collections
TYPES={'signage_plan_marker':{'n':'وسم علامة من مسقط A2200…A2203','cf':'doc','sp':[['التمثيل','مؤشر موضع صغير؛ لا يجسم مقاس لوحة توريد']],'sr':['ARCH2 ص34–35','ARCH2 ص44–47'],'asm':['ارتفاع المؤشر 1.5م فوق FFL افتراض للعرض؛ موضع النص مستخرج حرفيًا ولا يثبت وجه التثبيت']}}

def build(M,els,verbose=False):
 els[:]=[e for e in els if not re.search(r'-SG\d{4}$',e['id'])]
 D=json.load(open(os.path.join(os.path.dirname(__file__),'data','signage_remaining.json')))
 M['mats'].setdefault('signage_marker',{'name':'مؤشر موضع علامات المسقط','color':'#44687c','code':'A2200…A2203'})
 for L in M['layers']:
  if L['id']=='A' and not any(s[0]=='A.sign' for s in L['subs']):L['subs'].append(['A.sign','مؤشرات علامات المسقط'])
 ffl={l['id']:l['ffl'] for l in M['levels']};n=0;stats=collections.Counter()
 for pg in D['pages']:
  src=f'ARCH2 ص{pg["page"]}: موضع وسم العلامة من FURN-SPECS؛ النوع من A1301/1302 ص34–35. ليس جسم لوحة مثبتة. ص48 A2204 يحتوي مسقط الدور الأول ويستبعد من السطح.'
  if src not in M['sp']:M['sp'].append(src)
  for lv in (['2','3','4','5'] if pg['level']=='TY' else [pg['level']]):
   for v in pg['markers']:
    n+=1;x,y=v['xy_cm'];z=ffl[lv]+1.5;stats[lv]+=1
    els.append({'id':f'A.sign-{lv}-SG{n:04d}','c':'A.sign','l':lv,'g':['cyl',x,y,2,round(z-.02,3),round(z+.02,3)], 't':'signage_plan_marker','mark':v['code'],'m':'signage_marker','s':[M['sp'].index(src)],'a':{'kind':'signage_annotation','source_xy':[x,y],'source_pdf_points':[v['source_pdf_point']],'source_transform':pg['reg'],'source_page':f'ARCH2:{pg["page"]}','assumed':'مؤشر فقط عند وسم المسقط؛ ارتفاع1.5م وحجم4سم للعرض، لا اعتماد لوجه تركيب اللوحة أو أبعادها.'}})
 M.setdefault('meta',{})['signage_remaining']={'markers':n,'by_level':dict(stats),'physical_plates':0,'excluded_page':48}
 if verbose:print('signage source markers:',n,dict(stats),'| physical plates: 0')
 return dict(stats)
