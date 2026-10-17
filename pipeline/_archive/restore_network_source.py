# -*- coding: utf-8 -*-
"""Recover immutable legacy network XY and retain explicit support assumptions."""
import copy,json,os
IDS={'P.ff-B-M0138':[4211.1,1604.7],'P.ff-B-M0148':[4211.1,1304.6]}
ROOF_GRILLES={f'M.outlet-R-S{i:04d}' for i in (237,238,239,240,241,248,249,250,251)}
# Observed in the pre-task model; fresh roof merges otherwise discard the old
# positions before this correction runs. Preserve that evidence in the history.
DISPLACED_XY={'M.outlet-R-S0237':[1919.8,1039.8],'M.outlet-R-S0248':[1911.1,1033.9]}
ZERO_MOVE_TUBES={'M.pipe-R-S0029','M.pipe-R-S0135','P.ff-R-M0007'}
def apply(M,els):
 hist=M.setdefault('meta',{}).setdefault('drawing_corrections',{})
 roof=json.load(open(os.path.join(os.path.dirname(__file__),'data','roof.json'),encoding='utf-8'))['els']
 for e in els:
  a=e.get('a') or {}
  if e['id'] in ROOF_GRILLES or (e['c']=='M.outlet' and '-R-S' in e['id'] and a.get('guess_from') and a.get('guess_cm')==0 and a.get('guess_dz_cm')==0):
   ix=int(e['id'][-4:])-1;src=roof[ix];assert src['c']==e['c'] and src['t']==e['t'],e['id']
   xy=src['g'][1:3];old=copy.deepcopy(e['g']);e['g'][1:3]=xy
   if e['id'] in DISPLACED_XY:
    observed=copy.deepcopy(old)
    if old==e['g']:observed[1:3]=DISPLACED_XY[e['id']]
    hist.setdefault(e['id'],{'element':e['id'],'level':'R','old_geometry':observed,'new_geometry':copy.deepcopy(e['g']),
     'xy_cm':xy,'source':'pipeline/data/roof.json record '+str(ix+1)+'؛ MECH1 ص6 '+('M_SAG_GRILL' if e['t']=='grille_supply' else 'M_RAG_GRILL'),
     'note':'استعادة موضع شبكة المسقط الأصلي؛ موضع الجدار الخاطئ موثق في نسخة النموذج قبل المهمة. سحبتها آلية الإسناد184.2/198.4سم. ارتفاع التركيب محفوظ كافتراض الاستخراج، ولا يعد اعتماد إسناد.'})
   for k in list(a):
    if k.startswith('guess_') or k=='mount_note':a.pop(k,None)
   a.update({'sys':'hvac_legacy','source_xy':copy.deepcopy(xy),'source_page':'MECH1:6','source_roof_record':ix+1,
    'assumed':'ارتفاع شبكة التكييف 25.69..25.91م افتراض الاستخراج الأصلي؛ XY محفوظ من المسقط. القائم/الإسناد إن وُجد مشتق من النموذج ولم يحرك العنصر.'})
   e['a']=a
  elif e['id'] in IDS:
   xy=IDS[e['id']];old=copy.deepcopy(e['g']);e['g'][1:3]=xy
   # The ceiling rehoming was based on the shifted point in a stair opening.
   dz=a.pop('ceil_dz',0);e['g'][4]=round(e['g'][4]-dz,3);e['g'][5]=round(e['g'][5]-dz,3)
   hist.setdefault(e['id'],{'element':e['id'],'level':'B','xy_cm':xy,'old_geometry':old,'new_geometry':copy.deepcopy(e['g']),'source':'MECH2 ص10 FF-100 / M_FF_SP، الرسم24604 أو24654','note':'مركز المصدر4211.1سم، كان4266بعدسحب50سمإلىجدارالفتحة ثم5سمإلىوجهه؛ أزيلت إزاحة السقف المعتمدة على النقطة المنقولة. المنسوب الأصلي افتراض ويحتاج تفصيل تثبيت في فتحة السلم.'})
   for k in list(a):
    if k.startswith('guess_') or k=='mount_note':a.pop(k,None)
   a.update({'sys':'fire_legacy','source_xy':xy,'assumed':'المنسوب−1.08..−0.98م افتراض الاستخراج الأصلي؛ مصدرXY محفوظ، لا سقف مضيف مثبت في فتحة السلم.'})
   e['a']=a
  elif e['id'] in ZERO_MOVE_TUBES or (e['c'] in ('M.pipe','P.ff') and a.get('guess_from') and a.get('guess_cm')==0 and a.get('guess_dz_cm')==0 and e['g'][0] in ('t','d')):
   a['support_assumption']='قائم/تعليق مشتق سابقًا من سطح النموذج؛ لم يتحرك مسار المصدر.'
   a['sys']='hvac_legacy' if e['c']=='M.pipe' else 'fire_legacy'
   for k in list(a):
    if k.startswith('guess_'):a.pop(k,None)
   if a.get('mount_note','').startswith('تخمين:'):a['mount_note']=a['support_assumption']
   e['a']=a
 return hist
