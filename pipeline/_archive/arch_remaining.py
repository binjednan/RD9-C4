# -*- coding: utf-8 -*-
"""A500 roof and concrete-soffit finishes and explicit A101 local floor levels."""
import collections, re
from shapely.ops import unary_union
from shapely import normalize, set_precision
from support import poly_of, zr

# Numerical precision for temporary overlays, not source/model accuracy.
# The former 0.1 cm serialization collapsed thin holes into self-touching rings;
# the global polygon repair then changed the derived soffit at every rebuild.
# Keep source geometries untouched and retain the small, valid overlay details.
CALC_GRID_CM = .0001

def calc_poly(g):
 p=poly_of(g)
 # Equivalent source rings can arrive with a different start vertex after a
 # finish pass. Canonicalize before precision reduction as well as after it:
 # GEOS overlays otherwise choose different roundoff paths for the same ring.
 return normalize(set_precision(normalize(p),CALC_GRID_CM)) if p is not None else None

TYPES = {
 'floor_F12': {'n':'تشطيب السطح F12 — بلاط خرساني 3 سم','cf':'doc','sp':[['المقاس','300×300×30 مم'],['التطبيق','السطح والسطح العلوي، صف K في A500']],'sr':['ARCH1 ص18'],'asm':['مكونات العزل والتسوية غير مفصلة']},
 'soffit_C10': {'n':'دهان C10 على بطن خرسانة البدروم','cf':'doc','sp':[['النوع','أكريليك مضاد للكربنة على برايمر وحشو']],'sr':['ARCH1 ص18','ARCH2 ص28'],'asm':['سمك العرض 0.3 مم، لا يدل على سمك تنفيذ معتمد']},
}

def pool(M,text):
 if text not in M['sp']:M['sp'].append(text)
 return M['sp'].index(text)

def pieces(p):
 p=normalize(set_precision(p,CALC_GRID_CM))
 return sorted([q for q in (list(p.geoms) if hasattr(p,'geoms') else [p]) if q.geom_type=='Polygon' and q.area>100],key=lambda q:(q.bounds,q.area))

def geom(p,z0,z1):
 p=normalize(set_precision(p,CALC_GRID_CM))
 ring=lambda h:[[round(x,4),round(y,4)] for x,y in list(h.coords)[:-1]]
 return ['p',ring(p.exterior),round(z0,4),round(z1,4),[ring(h) for h in p.interiors] or None]

def correct_levels(M,els):
 log=M.setdefault('meta',{}).setdefault('drawing_corrections',{})
 src=pool(M,'ARCH1 ص4 A101: المواقف والممر والمشاة F.F.L. −3.60، ردهة المصاعد وغرفتا مضخات الري والصرف −3.50؛ ARCH2 ص57 A2500 يؤكد غرفة الري −3.50؛ A300/A301 يثبتان مرجع B العام −3.70.')
 changed=[]
 for e in els:
  if e['c']!='A.floor' or e['l']!='B' or e['g'][0] not in ('r','p'):continue
  a=e.get('a') or {};k=a.get('kind');room=' '.join(a.get('room') or [])
  target=-3.60 if k in ('driveway','bay','walkway') else -3.50 if k=='lobby' or k=='pump' and any(x in room for x in ('IRRIGATION','SUMP')) else None
  if target is None:continue
  z0,z1=zr(e['g']);ix=(5,6) if e['g'][0]=='r' else (2,3)
  if abs(z1-target)>.0001:
   p=poly_of(e['g']);e['g'][ix[0]],e['g'][ix[1]]=round(target-(z1-z0),4),target
   log.setdefault(e['id'],{'element':e['id'],'level':'B','xy_cm':[round(p.centroid.x,1),round(p.centroid.y,1)],'old_z_m':[z0,z1],'new_z_m':[e['g'][ix[0]],target],'source':'ARCH1 ص4 A101','note':'تصحيح منسوب التشطيب المحلي من الوسم؛ لم يتغير المسقط أو المستوى العام.'})
   changed.append(e['id'])
  e.setdefault('a',{})['drawn_ffl_m']=target
  if src not in e.setdefault('s',[]):e['s'].append(src)
 return changed

def build(M,els,verbose=False):
 els[:]=[e for e in els if not re.search(r'-ARF\d{4}$',e['id'])]
 changed=correct_levels(M,els)
 for L in M['layers']:
  if L['id']=='A' and not any(s[0]=='A.cfin' for s in L['subs']):L['subs'].append(['A.cfin','دهان بطون الخرسانة'])
 sr=pool(M,'ARCH1 ص18 A500 صف K: Roof & Top Roof = F12؛ بلاط خرساني 300×300×30 مم؛ بصمة البلاطات القائمة ومساقط A105/A106 باستثناء الغرف ذات التشطيب المستقل.')
 sc=pool(M,'ARCH1 ص18 A500 صفوف M/U/V + ARCH2 ص28 A1400: C10 دهان بطن خرسانة الممر والمواقف والمشاة والمنحدر في البدروم؛ ليس سقفًا مستعارًا.')
 n=0;stats=collections.Counter()
 def add(c,lv,g,t,mat,src,a):
  nonlocal n
  n+=1;stats[t]+=1
  els.append({'id':f'{c}-{lv}-ARF{n:04d}','c':c,'l':lv,'g':g,'mark':'F12' if t=='floor_F12' else 'C10','t':t,'m':mat,'a':a,'s':[src]})
 levels={l['id']:l for l in M['levels']}
 for lv in ('R','T'):
  scope=unary_union([calc_poly(e['g']) for e in els if e['c']=='S.slab' and e['l']==lv])
  cut=[calc_poly(e['g']) for e in els if e['l']==lv and (e['c'] in ('A.wall','S.col','S.wall') or e['c']=='A.floor' and e.get('a',{}).get('fin'))]
  cut=unary_union([p for p in cut if p is not None])
  for p in pieces(scope.difference(cut).buffer(0)):
   ffl=levels[lv]['ffl']
   add('A.floor',lv,geom(p,ffl-.03,ffl),'floor_F12','fin_F12',sr,{'kind':'roof_finish','fin':['F12'],'area_m2':round(p.area/1e4,2),'drawn_ffl_m':ffl,'assumed':'البصمة مشتقة من البلاطة والمساقط؛ مكونات العزل والتسوية تحت البلاط غير محددة.'})
 area=unary_union([calc_poly(e['g']) for e in els if e['c']=='A.floor' and e['l']=='B' and e.get('a',{}).get('kind') in ('driveway','bay','walkway')])
 for e in list(els):
  if e['c']=='S.slab' and e['l']=='G':
   p=calc_poly(e['g']);z0,z1=zr(e['g'])
   if p is not None:
    for q in pieces(p.intersection(area)):
     add('A.cfin','B',geom(q,z0-.0003,z0),'soffit_C10','fin_C10',sc,{'kind':'concrete_soffit_paint','fin':['C10'],'host':e['id'],'area_m2':round(q.area/1e4,2),'assumed':'سمك العرض 0.3 مم افتراض بصري؛ نطاق الدهان مشتق من حدود أرضية المواقف والممر والمشاة.'})
  if e['c']=='S.ramp' and e['g'][0]=='rs':
   g=e['g'];pts=[[p[0],p[1],round(p[2]-g[3],4)] for p in g[1]]
   add('A.cfin','B',['rs',pts,g[2],.0003],'soffit_C10','fin_C10',sc,{'kind':'concrete_soffit_paint','fin':['C10'],'host':e['id'],'assumed':'سمك العرض 0.3 مم افتراض بصري.'})
 M.setdefault('meta',{})['arch_remaining']=dict(stats,floor_levels_changed=len(changed),
  calculation_grid_cm=CALC_GRID_CM,input_xy_preserved=True,
  precision_note='شبكة عددية للقص والتسلسل في نسخ مؤقتة؛ ليست دقة مسح ميداني. حفظ الثقوب الدقيقة يمنع انهدامها بتقريب1مم ثم إصلاح متكرر؛ لم تتغير هندسة المصادر أو البلاطات الإنشائية.')
 if verbose:print('remaining architectural finishes:',dict(stats),'| local floors corrected:',len(changed))
 return dict(stats)
