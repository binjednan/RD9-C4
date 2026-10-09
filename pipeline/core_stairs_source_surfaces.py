# -*- coding: utf-8 -*-
"""Scratch drop-in: open finished-stair graphic assemblies, no concrete waist."""
import copy, hashlib, json, math
from pathlib import Path
FROZEN_SHA = 'be716ad11f882d41e0b01cb6c111481a83c8d599a2cf9ef01a70c467005cb186'
_DATA = Path(__file__).with_name('core_stairs_source_surfaces.json')
if not _DATA.exists():
    _DATA = Path(__file__).resolve().parent / 'data' / 'core_stairs_source_surfaces.json'
TYPES = {
    'stair_finished_source_flight': {'n':'رحلة درج — أسطح النائمات والقوائم من الرسم','source_scope':'أسطح عرض مفتوحة؛ ليست جسم خرسانة أو قبول تسليح/ارتكاز','material_assignment_verified':False},
    'stair_finished_source_landing': {'n':'بسطة درج — سطح مصدر مشتق','source_scope':'سطح بلا سمك؛ حدود المسقط ومناسيب المصدر فقط','material_assignment_verified':False},
}
FIELDS = ('id','c','t','l','m','grp','g')
def signature(e): return {k:copy.deepcopy(e.get(k)) for k in FIELDS}
def load():
    b=_DATA.read_bytes()
    if FROZEN_SHA!='DRAFT' and hashlib.sha256(b).hexdigest()!=FROZEN_SHA: raise ValueError('CSF: frozen data SHA mismatch')
    return json.loads(b)
def _quad(v,f,p):
    n=len(v);v.extend([[float(x),float(y),float(z)] for x,y,z in p]);f.extend([[n,n+1,n+2],[n,n+2,n+3]])
def _direction(cells):
    a=cells[0]['surface_xy_cm'];b=cells[-1]['surface_xy_cm']
    dx=sum(p[0]for p in b)/4-sum(p[0]for p in a)/4
    if abs(dx)<1:raise ValueError('CSF: unknown flight direction')
    return 1 if dx>0 else -1

def flight_mesh(cells,start_z,end_z):
    """One open surface assembly: tread quads and the11/other derived riser planes."""
    v=[];f=[];sgn=_direction(cells)
    for c in cells:
        _quad(v,f,[[x,y,c['top_Z_m']]for x,y in c['surface_xy_cm']])
    # All cells have two original parallel nosings; use their actual shared edge.
    edges=[]
    for c in cells:
        p=c['surface_xy_cm'];xs=sorted(set(q[0]for q in p))
        if len(xs)!=2:raise ValueError('CSF: not two parallel original nosing edges')
        left=sorted([q for q in p if q[0]==xs[0]],key=lambda q:q[1]);right=sorted([q for q in p if q[0]==xs[1]],key=lambda q:q[1])
        if len(left)!=2 or len(right)!=2:raise ValueError('CSF: invalid raw nosing edges')
        edges.append((left,right))
    def edge(e,start=False):
        return e[0] if (sgn>0)==start else e[1]
    e=edge(edges[0],True)
    _quad(v,f,[[*e[0],start_z],[*e[1],start_z],[*e[1],cells[0]['top_Z_m']],[*e[0],cells[0]['top_Z_m']]])
    for a,b,ca,cb in zip(edges[:-1],edges[1:],cells[:-1],cells[1:]):
        aa=edge(a);bb=edge(b,True)
        if aa!=bb:raise ValueError('CSF: raw adjacent nosing boundaries do not match exactly')
        _quad(v,f,[[*aa[0],ca['top_Z_m']],[*aa[1],ca['top_Z_m']],[*aa[1],cb['top_Z_m']],[*aa[0],cb['top_Z_m']]])
    e=edge(edges[-1]);_quad(v,f,[[*e[0],cells[-1]['top_Z_m']],[*e[1],cells[-1]['top_Z_m']],[*e[1],end_z],[*e[0],end_z]])
    return ['mesh',v,f]
def landing_mesh(l):
    v=[];f=[];_quad(v,f,[[x,y,l['top_Z_m']]for x,y in l['surface_xy_cm']]);return ['mesh',v,f]
def compile_after(D):
    out={};templates={};template_order=[]
    def template_copy(g):
        origin=[min(p[0]for p in g[1]),min(p[1]for p in g[1]),min(p[2]for p in g[1])]
        local=[[round(p[i]-origin[i],12)for i in range(3)]for p in g[1]]
        key=json.dumps([local,g[2]],separators=(',',':'))
        if key not in templates:
            templates[key]=copy.deepcopy(local);template_order.append(key)
        placed=[[p[i]+origin[i]for i in range(3)]for p in copy.deepcopy(templates[key])]
        delta=max(abs(a[i]-b[i])*(100 if i==2 else 1)for a,b in zip(g[1],placed)for i in range(3))
        if delta>1e-9:raise ValueError('CSF: template copy changes source geometry')
        return ['mesh',placed,copy.deepcopy(g[2])],template_order.index(key)+1,origin,delta

    for r in D['groups']:
        levels=[r['literal_datums']['start_FFL']]+[p['top_Z_m']for p in r['after_landing_surfaces']]+[r['literal_datums']['end_landing_FFL']]
        flights=sorted(set(c['flight']for c in r['after_tread_surfaces']))
        specs=[]
        for i,fi in enumerate(flights):
            cells=sorted([c for c in r['after_tread_surfaces']if c['flight']==fi],key=lambda c:c['ordinal_within_flight'])
            expected=r['source_rise_allocation'][i]
            if len(cells)+1!=expected:raise ValueError('CSF: risers versus tread intervals mismatch')
            step=(levels[i+1]-levels[i])/expected
            for j,c in enumerate(cells):
                if abs(c['top_Z_m']-(levels[i]+step*(j+1)))>1e-12:raise ValueError('CSF: source datum interpolation mismatch')
            specs.append(('flight',fi,flight_mesh(cells,levels[i],levels[i+1]),len(cells),expected,[levels[i],levels[i+1]]))
        for i,l in enumerate(r['after_landing_surfaces']):specs.append(('landing',i+1,landing_mesh(l),0,0,[l['top_Z_m'],l['top_Z_m']]))
        for old_id,s in zip(r['assembly_member_IDs'],specs):
            kind,ordinal,g,nt,nr,levels=s;g,template_id,source_pose,template_delta=template_copy(g);old=D['before_records'][old_id];e=copy.deepcopy(old)
            e['g']=g;e['t']='stair_finished_source_'+kind;e.pop('q',None)
            e['a']={
                'source_kind':'derived_finished_stair_'+kind+'_surface_mesh',
                'source_locked_xy':True,'source_geometry_review':'finished_graphic_surfaces_only',
                'source_graphic_XY_checked':True,'source_surface_Z_checked':True,
                'source_local_datums_verified':True,'source_absolute_Z_verified':False,
                'source_dimension_scope':'نوسينغ المسقط ومناسيب البسطات؛ القوائم الداخلية مشتقة من تقسيم الرحلة المرسوم',
                'source_body_closed':False,'source_body_verified':False,'source_waist_verified':False,
                'source_material_verified':False,'source_material_assignment_verified':False,
                'source_ports_verified':False,'source_bearing_verified':False,'source_rebar_verified':False,
                'source_physical_acceptance':False,'source_material_color_verified':False,
                'flight_ordinal' if kind=='flight' else 'landing_ordinal':ordinal,
                'tread_intervals':nt,'riser_intervals':nr,'surface_datums_m':levels,
                'source_copy_template_id':template_id,'source_copy_pose_xyz':source_pose,'source_copy_template_max_float_delta_cm':template_delta,
                'source_member_identity_scope':'المعرف القديم حارس إجرائي فقط، ليس هوية raw مرسومة مستقلة',
                'core_stairs_source_surfaces':True,'source_data_sha256':FROZEN_SHA,
                'assumed':'تمثيل أسطح الرسم المفتوحة فقط؛ سمك وبطن الخرسانة والتسليح والارتكاز ومادة الجسم غير معتمدة. لا أبعاد جسم من النموذج القديم.'}
            out[old_id]=e
    if len(out)!=29:raise ValueError('CSF: exact assembly set is not29')
    return out

def generation_checks(after):
    checks=[]
    for i,e in after.items():
        g=e['g'];errs=[]
        for p in g[1]:
            if len(p)!=3 or any(not math.isfinite(v)for v in p):errs.append('non-finite mesh vertex')
        for f in g[2]:
            if len(f)!=3 or len(set(f))!=3 or any(not isinstance(v,int)or not 0<=v<len(g[1])for v in f):errs.append('invalid triangle indices');continue
            a,b,c=[g[1][j]for j in f];u=[b[j]-a[j]for j in range(3)];v=[c[j]-a[j]for j in range(3)]
            n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
            if sum(x*x for x in n)==0:errs.append('degenerate source face')
        checks.append({'id':i,'group':e['grp'],'source_kind':e['a']['source_kind'],'errors':errs,'scope':'sourcefinishedsurfaceonly;no concretewaist/material/physicalacceptance'})
    return checks

def apply(M,els=None):
    D=load();els=M['els']if els is None else els;after=compile_after(D);checks=generation_checks(after)
    if any(c['errors']for c in checks):raise ValueError('CSF: invalid sourceface encoding')
    for table in D['raw_source_tables'].values():
        if hashlib.sha256(Path(table['source_pdf']).read_bytes()).hexdigest()!=table['source_pdf_sha256']:raise ValueError('CSF: originalPDF SHA changed')
    ids=[e['id']for e in els]
    if len(ids)!=len(set(ids)):raise ValueError('CSF: duplicate model identity')
    by={e['id']:e for e in els};before=D['before_records'];owned=set(before);present=owned&set(by)
    old_state=present==owned and all(signature(by[k])==signature(v)for k,v in before.items())
    final_state=present==set(after) and all(signature(by[k])==signature(v) and all(by[k].get('a',{}).get(a)==b for a,b in v.get('a',{}).items())for k,v in after.items())
    if not(old_state or final_state):raise ValueError('CSF: unknown/partial before or after geometry/class/level/identity')
    for k,v in D['pending_preserved_records'].items():
        if k not in by or signature(by[k])!=signature(v):raise ValueError('CSF: out-of-scope pending stair changed '+k)
    if final_state:return {'groups':9,'assemblies':29,'retired_this_apply':0,'scope':'finished_source_surfaces_only','checks':checks,'global_findings':[],'uncovered':[]}
    # Preflight was complete before a single mutation.
    refs={s:i for i,s in enumerate(M.setdefault('sp',[]))}
    def ref(s):
        if s not in refs:refs[s]=len(M['sp']);M['sp'].append(s)
        return refs[s]
    result=[]
    for e in els:
        if e['id']not in owned:result.append(e);continue
        if e['id']not in after:continue
        n=copy.deepcopy(after[e['id']]);r=next(x for x in D['groups']if x['group']==e['grp'])
        page=r['source_plan'].get('page','ARCH2:3');n['s']=[ref('مخطط '+page.replace(':',' ص')+' — نوسينغ الدرج وحدود بسطة مشتقة من الوجوه الداخلية'),ref('ARCH2 ص1–4 A600/A601/A602/A603 — عدد القوائم ومناسيب الرحلات والبسطات؛ أسطح الرسم فقط')]
        result.append(n)
    before_index={e['id']:i for i,e in enumerate(els)}
    els[:]=result;M['els']=els
    after_index={e['id']:i for i,e in enumerate(els)}
    M.setdefault('meta',{})['core_stairs_source_surfaces']={'data_sha256':FROZEN_SHA,'groups':9,'before_bodies':189,'after_assemblies':29,'retired_ids':D['exactretired_ids'],'tread_surfaces':190,'landing_surfaces':10,'riser_surfaces':209,'physical_body_accepted':False}
    return {'groups':9,'assemblies':29,'retired_this_apply':160,'scope':'finished_source_surfaces_only','checks':checks,'global_findings':[],'uncovered':[],'old_to_new_indices':{i:after_index[k]for k,i in before_index.items()if k in after_index},'retired_indices':[before_index[k]for k in D['exactretired_ids']]}

def restore_before_post(M,els=None):
    """Reverse only this finished-surface wave before legacy procedural generators."""
    D=load();els=M['els']if els is None else els;after=compile_after(D);before=D['before_records']
    ids=[e['id']for e in els]
    if len(ids)!=len(set(ids)):raise ValueError('CSF restore: duplicate identity')
    by={e['id']:e for e in els};present=set(before)&set(by)
    old_state=present==set(before)and all(signature(by[k])==signature(v)for k,v in before.items())
    final_state=present==set(after)and all(signature(by[k])==signature(v)and all(by[k].get('a',{}).get(a)==b for a,b in v.get('a',{}).items())for k,v in after.items())
    if not(old_state or final_state):raise ValueError('CSF restore: unknown partial/geometry/Z/class state')
    for k,v in D['pending_preserved_records'].items():
        if k not in by or signature(by[k])!=signature(v):raise ValueError('CSF restore: pending out-of-scope changed')
    if old_state:return {'restored_this_apply':0,'old_bodies':189}
    # Reinsert each original group at its own surviving assembly position.
    # This preserves all unrelated order and first/next-cycle element-index behavior.
    old_groups={r['group']:r['before_current_objects']for r in D['groups']};seen=set();out=[]
    for e in els:
        if e['id']not in after:out.append(e);continue
        group=e['grp']
        if group not in seen:out.extend(copy.deepcopy(old_groups[group]));seen.add(group)
    if seen!=set(old_groups):raise ValueError('CSF restore: exact group insertion set mismatch')
    els[:]=out;M['els']=els
    M.setdefault('meta',{}).pop('core_stairs_source_surfaces',None)
    return {'restored_this_apply':189,'removed_source_assemblies':29,'old_bodies':189}

def data():return load()
