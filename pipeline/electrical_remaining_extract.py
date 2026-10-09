# -*- coding: utf-8 -*-
"""Remaining electrical geometry from source vectors; stores PDF coordinates and registration evidence.
Never converts NTS diagrams to XY, snaps to model geometry, or writes the model.
"""
import os,sys,json,math,re,collections,copy
import numpy as np
HERE=os.path.dirname(os.path.abspath(__file__));sys.path.insert(0,HERE)
import lib,reg
DATA=os.path.join(HERE,'data','electrical_remaining.json')
PLANS=[('ELEC1',8),('ELEC2',1)]+[('ELEC2',p) for p in range(11,17)]+[('ELEC2',p) for p in range(27,33)]
DETAILS=[('ELEC1',p) for p in (7,15,18)]+[('ELEC2',p) for p in (7,8,9,10,17,24,25,26,33,34)]
LEVEL={1:'G',11:'B',12:'G',13:'1',14:'TY',15:'R',16:'T',27:'G',28:'B',29:'G',30:'1',31:'TY',32:'R'}
def center(d):
 x,y,u,v=d['rect'];return ((x+u)/2,(y+v)/2)
def wh(d):
 x,y,u,v=d['rect'];return (u-x,v-y)
def phone_triangles(sh,p):
 """True outlet glyphs comprise three separate straight strokes; the curved-tail V is a label arrow."""
 sc=2 if p in(30,31) else 1;segs=[];nodes=[];adj=collections.defaultdict(list);edges=[]
 for i,d in enumerate(sh.D):
  X,Y=sh.T(*center(d))
  if d['layer']=='TELEPHONE' and d['type']=='s' and -350<X<4550 and -250<Y<4550 and len(d['polys'])==1 and len(d['polys'][0])==2:
   q=d['polys'][0]
   if 6.8*sc<math.dist(q[0],q[1])<7.4*sc:segs.append((i,q))
 for i,q in segs:
  ab=[]
  for pt in q:
   n=next((n for n,t in enumerate(nodes) if math.dist(pt,t)<.2),None)
   if n is None:n=len(nodes);nodes.append(pt)
   ab.append(n)
  a,b=ab;adj[a].append(b);adj[b].append(a);edges.append((i,a,b))
 seen=set();out=[]
 for n in range(len(nodes)):
  if n in seen:continue
  todo=[n];comp=[];seen.add(n)
  while todo:
   a=todo.pop();comp.append(a)
   for b in adj[a]:
    if b not in seen:seen.add(b);todo.append(b)
  if len(comp)!=3 or not all(len(adj[n])==2 for n in comp):continue
  members=[z for z in edges if z[1] in comp]
  base=next((z for z in members if abs(nodes[z[1]][0]-nodes[z[2]][0])<.2 or abs(nodes[z[1]][1]-nodes[z[2]][1])<.2),None)
  if base is None:continue
  tip=next(n for n in comp if n not in base[1:]);i=next(z[0] for z in members if tip in z[1:])
  out.append({'tip':nodes[tip],'vertices':[nodes[n] for n in comp],'drawing':i,'outline_drawings':[z[0] for z in members],'rotation':90 if abs(nodes[base[1]][0]-nodes[base[2]][0])<.2 else 0})
 return out
def joint_site27():
 ds=[d for d in lib.doc('ELEC2')[26].get_drawings() if d.get('layer') and d['layer'].endswith('S-GRID')]
 vv,hh=reg.grid_clusters(None,drawings=ds,layers=None,minlen=50);A=[];b=[];pairs=[]
 for pts,master,sign in [(vv,reg.GX_list,1),(hh,reg.GY_list,-1)]:
  s,off,_,_=reg.fit_axis_free(pts,master,sign<0,smin=5,smax=9)
  for p in pts:
   m=min(master,key=lambda m:abs(sign*p*s+off-m))
   if abs(sign*p*s+off-m)<=3.5:
    A.append([sign*p,int(sign>0),int(sign<0)]);b.append(m);pairs.append({'axis':'x' if sign>0 else 'y','pdf':p,'world':m})
 s,ox,oy=np.linalg.lstsq(A,b,rcond=None)[0];err=np.array(A)@np.array([s,ox,oy])-b
 return {'s':float(s),'ox':float(ox),'oy':float(oy),'nx':17,'ny':11,'by':'source_grid_joint','max_residual_cm':round(float(max(abs(err))),4),'anchors':pairs}
def site8(rg):
 a=lib.Sheet('ELEC1',8,auto_reg=False);b=lib.Sheet('ELEC1',10,auto_reg=False);b.reg=rg['ELEC1:10'];A=[];v=[];anchors=[]
 for name in ['MDB','TRANSFORMER','DMS RTU','BATTERY RACK']:
  aa=[t for t in a.TX if t['s'].strip()==name and t['layer']=='E.POWER'];bb=[t for t in b.TX if t['s'].strip()==name and t['layer']=='E.POWER']
  assert len(aa)==len(bb)==1,name
  x,y,u,w=aa[0]['bbox'];px,py=(x+u)/2,(y+w)/2
  x,y,u,w=bb[0]['bbox'];X,Y=b.T((x+u)/2,(y+w)/2);A.extend([[px,1,0],[-py,0,1]]);v.extend([X,Y]);anchors.append({'name':name,'pdf':[px,py],'reference_cm':[X,Y],'ref':'ELEC1:10'})
 s,ox,oy=np.linalg.lstsq(A,v,rcond=None)[0];err=np.array(A)@np.array([s,ox,oy])-v
 return {'s':float(s),'ox':float(ox),'oy':float(oy),'by':'named_source_source_similarity','max_residual_cm':round(float(max(abs(err))),4),'anchors':anchors}
def run(save=True):
 rg=json.load(open(os.path.join(HERE,'data','reg_all.json')))
 verified=os.path.join(HERE,'data','reg_verified.json')
 if os.path.exists(verified):
  vr=json.load(open(verified));rg.update(vr.get('registrations',vr))
 r27=joint_site27();r8=site8(rg);rg.update({'ELEC2:27':r27,'ELEC1:8':r8})
 out={'sheets':{},'details':[],'conflicts':[]}
 def rec(sh,i,d,kind,pdf=None,**kw):
  pt=pdf or center(d);X,Y=sh.T(*pt)
  return {'kind':kind,'drawing':i,'layer':d['layer'],'pdf':[round(v,5) for v in pt],'xy':[round(X,1),round(Y,1)],**kw}
 def main(sh,d):
  X,Y=sh.T(*center(d));return -350<X<4550 and -250<Y<4550
 for key,p in PLANS:
  sh=lib.Sheet(key,p,auto_reg=False)
  r=rg.get(f'{key}:{p}')
  if not r:
   # Roof telephone shares exactly the roof architecture underlay with ELEC2:15.
   if (key,p)==('ELEC2',32):
    ref=lib.Sheet('ELEC2',15,auto_reg=False);ref.reg=rg['ELEC2:15'];r=sh.register_by_layer(ref)
   if not r:raise RuntimeError(f'Unregistered plan {key}:{p}')
  sh.reg=r;row={'level':'G' if key=='ELEC1' else LEVEL[p],'registration':r,'items':[],'audit':{}};items=row['items']
  out['sheets'][f'{key}:{p}']=row
  # Copper/earth conductors: paired filled triangular paths represent one drawn stripe.
  if key=='ELEC2' and p in(1,11,12,15,16):
   for i,d in enumerate(sh.D):
    if d['layer'] not in ('EARTHNING','LIGHT PROTECTION') or not main(sh,d):continue
    w,h=wh(d)
    if 'f' in d['type'] and len(d['polys'])==2 and 0.9<min(w,h)<1.6 and max(w,h)>10 and sum(map(len,d['polys']))<=9:
     x,y,u,v=d['rect'];q=[[(x+u)/2,y],[(x+u)/2,v]] if h>w else [[x,(y+v)/2],[u,(y+v)/2]]
     items.append(rec(sh,i,d,'earth_cable' if p==1 else 'lightning_tape',path_pdf=q,path=[[round(a,1),round(b,1)] for a,b in map(lambda z:sh.T(*z),q)]))
   if p in(1,11):
    for i,d in enumerate(sh.D):
     if d['layer']!='EARTHNING' or not main(sh,d):continue
     w,h=wh(d)
     if abs(w-12.4)<.2 and abs(h-12.4)<.2:
      cp=center(d);circle=any(a['layer']=='EARTHNING' and math.dist(center(a),cp)<.5 and 16.7<wh(a)[0]<17.1 and 16.7<wh(a)[1]<17.1 for a in sh.D)
      items.append(rec(sh,i,d,'clean_earth_pit' if p==1 and not circle else 'earth_pit'))
    row['audit']['pits']=sum(z['kind'].endswith('pit') for z in items)
   if p==1:
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    hatches=[]
    for i,d in enumerate(sh.D):
     if d['layer']!='EARTHNING' or d['type']!='s' or not main(sh,d):continue
     for q in d['polys']:
      if len(q)==2:
       dx=q[1][0]-q[0][0];dy=q[1][1]-q[0][1]
       if .5<abs(dx)<10 and abs(abs(dx)-abs(dy))<.2:hatches.append((i,LineString(q)))
    u=unary_union([l.buffer(2) for _,l in hatches]);groups=list(u.geoms) if hasattr(u,'geoms') else [u]
    for g in groups:
     members=[(i,l) for i,l in hatches if g.intersects(l)]
     if len(members)<5:continue
     x,y,v,w=unary_union([l for _,l in members]).bounds;i=members[0][0]
     items.append(rec(sh,i,sh.D[i],'earth_bar',[(x+v)/2,(y+w)/2],hatch_strokes=[i for i,_ in members],outline_pdf=[x,y,v,w]))
    row['audit']['earth_bar_symbols']=sum(z['kind']=='earth_bar' for z in items)

  # Circles are the actual down-conductor position, not the arrow or annotation baseline.
  if key=='ELEC2' and p==11:
   for i,d in enumerate(sh.D):
    w,h=wh(d)
    if d['layer']=='LIGHT PROTECTION' and main(sh,d) and 5.2<w<5.6 and 5.2<h<5.6 and len(d['items'])==4 and all(t[0]=='c' for t in d['items']):items.append(rec(sh,i,d,'basement_down_marker'))
   row['audit']['connection_dot_symbols']=sum(z['kind']=='basement_down_marker' for z in items)
  if key=='ELEC2' and p in(12,13,14,15):
   for i,d in enumerate(sh.D):
    if d['layer']=='Down conductor' and main(sh,d) and len(d['items'])==4 and all(t[0]=='c' for t in d['items']):items.append(rec(sh,i,d,'down_marker'))
   row['audit']['down_symbols']=sum(z['kind']=='down_marker' for z in items)
  if key=='ELEC2' and p in(15,16):
   for i,d in enumerate(sh.D):
    w,h=wh(d)
    if d['layer']=='LIGHT PROTECTION' and d['type']=='s' and main(sh,d) and abs(max(w,h)-8.52)<.03 and abs(min(w,h)-4.8)<.03 and len(d['polys'])==1 and len(d['polys'][0])==5:items.append(rec(sh,i,d,'tape_clip'))
   row['audit']['tape_clip_symbols']=sum(z['kind']=='tape_clip' for z in items)
  if key=='ELEC2' and p==16:
   # Independent count of six equipment boxes: closed quadrilateral, excluding its two diagonals.
   for i,d in enumerate(sh.D):
    w,h=wh(d)
    if d['layer']=='LIGHT PROTECTION' and main(sh,d) and 14.2<w<14.7 and 14.2<h<14.7 and d['items'][0][0]=='qu':items.append(rec(sh,i,d,'equipment_bond'))
   # Three air rods are repeated isometric symbols. The two long parallel strokes locate each rod axis;
   # projection of their lower ends to the adjacent drawn tape gives the base centre in this plan.
   strokes=[]
   for i,d in enumerate(sh.D):
    w,h=wh(d)
    if d['layer']=='ACCESSORIES' and main(sh,d) and 45<h<48 and 6<w<9 and len(d['polys'])==1:
     q=d['polys'][0];lo=max(q,key=lambda pt:pt[1]);strokes.append((i,d,lo))
   groups=[]
   for i,d,pt in strokes:
    found=next((a for a in groups if math.dist(a[0][2],pt)<5),None)
    if found is None:groups.append([(i,d,pt)])
    else:found.append((i,d,pt))
   from shapely.geometry import Point,LineString
   tapes=[z for z in items if z['kind']=='lightning_tape']
   for group in groups:
    assert len(group)==2,'rod outline strokes'
    pt=[sum(a[2][j] for a in group)/2 for j in(0,1)]
    candidates=[(LineString(z['path_pdf']).distance(Point(pt)),z) for z in tapes]
    dist,z=min(candidates,key=lambda k:k[0]);ls=LineString(z['path_pdf']);anchor=ls.interpolate(ls.project(Point(pt)))
    assert dist<10,'rod base must touch its drawn tape'
    items.append(rec(sh,group[0][0],group[0][1],'air_terminal',[anchor.x,anchor.y],base_evidence=[a[0] for a in group],length_mm=500))
   row['audit']['equipment_symbols']=sum(z['kind']=='equipment_bond' for z in items);row['audit']['air_terminal_labels']=sum('500mm Air terminal' in t['s'] for t in sh.TX);row['audit']['air_terminal_symbols']=len(groups)
  if (key,p)==('ELEC1',8):
   # Five parallel boundaries bound four incoming 150 mm pipes; stops at the drawn endpoints.
   bd=[]
   for i,d in enumerate(sh.D):
    w,h=wh(d)
    if d['layer']=='E.POWER' and w<.1 and 53<h<55 and 1025<d['rect'][0]<1036:bd.append((i,d))
   bd.sort(key=lambda q:center(q[1])[0]);assert len(bd)==5
   for a,b in zip(bd,bd[1:]):
    x=(center(a[1])[0]+center(b[1])[0])/2;y0=a[1]['rect'][1];y1=a[1]['rect'][3];q=[[x,y0],[x,y1]]
    items.append(rec(sh,a[0],a[1],'site_power_duct',path_pdf=q,path=[[round(X,1),round(Y,1)] for X,Y in [sh.T(*pt) for pt in q]],dia_mm=150,boundaries=[a[0],b[0]]))
   row['audit']['pipe_boundaries']=len(bd);row['audit']['pipes_label_count']=4
  if key=='ELEC2' and p==27:
   # The long rectangle is the containment actually drawn between telephone room and site edge.
   ds=[(i,d) for i,d in enumerate(sh.D) if d['layer']=='0' and abs(d['rect'][0]-880.28)<.2 and abs(d['rect'][1]-1149.44)<.2 and abs(d['rect'][3]-1333.64)<.2]
   assert len(ds)==1
   i,d=ds[0];x,y,u,v=d['rect']
   for n in range(2):
    cx=x+(n+.5)*(u-x)/2;q=[[cx,y],[cx,v]]
    items.append(rec(sh,i,d,'site_phone_duct',path_pdf=q,path=[[round(X,1),round(Y,1)] for X,Y in [sh.T(*pt) for pt in q]],dia_mm=100,pair_index=n+1))
   # Eight straight fibre entry/end stubs are explicitly visible around the site boundary, four each side.
   for i,d in enumerate(sh.D):
    if d['layer']=='E-TL-FIBER_CABLE' and len(d['polys'])==1 and len(d['polys'][0])==2:
     q=d['polys'][0];items.append(rec(sh,i,d,'site_fiber_stub',path_pdf=q,path=[[round(X,1),round(Y,1)] for X,Y in [sh.T(*pt) for pt in q]]))
   row['audit']['containment_rectangles']=1;row['audit']['fibers_drawn_straight']=sum(z['kind']=='site_fiber_stub' for z in items)
  if key=='ELEC2' and p in(29,30,31,32):
   arrow_candidates=[];dual_halves=[]
   for i,d in enumerate(sh.D):
    if d['layer']!='TELEPHONE' or not main(sh,d):continue
    w,h=wh(d);L,S=max(w,h),min(w,h)
    if not S:continue
    for q in d['polys']:
     if len(q)==3 and 1.45<L/S<1.55 and (10.9<L<11.9 if p in(30,31) else 5.4<L<6):arrow_candidates.append(i)
     if len(q)==4 and math.dist(q[0],q[-1])<.1 and 1.68<L/S<1.78 and (11.9<L<12.5 if p in(30,31) else 5.9<L<6.3):dual_halves.append(rec(sh,i,d,'rj45_dual'))
   from shapely.geometry import Polygon,Point
   singles=[];duals=[];triangles=phone_triangles(sh,p)
   for tri in triangles:
    half=[q for q in dual_halves if Polygon(tri['vertices']).buffer(.2).covers(Point(q['pdf']))]
    assert len(half)<=1,'one filled half per dual symbol'
    # Anchor at the glyph apex in the source; some apexes face a window or stop short of the architecture.
    kind='rj45_dual' if half else 'rj45_single';i=tri['drawing']
    item=rec(sh,i,sh.D[i],kind,tri['tip'],outline_drawings=tri['outline_drawings'],outline_pdf=tri['vertices'],rotation=tri['rotation'],anchor='drawn_triangle_apex')
    if half:item['filled_half_drawing']=half[0]['drawing']
    (duals if half else singles).append(item)
   assert len(duals)==len(dual_halves),(p,'dual half triangles unmatched')
   floorboxes=[]
   if p==29:
    for i,d in enumerate(sh.D):
     w,h=wh(d)
     if d['layer']=='E.POWER' and main(sh,d) and len(d['items'])==1 and d['items'][0][0]=='qu' and 12<max(w,h)<12.5 and 6<min(w,h)<6.3:floorboxes.append(rec(sh,i,d,'phone_floorbox'))
   items.extend(singles+duals+floorboxes)
   tags=re.findall(r'S\d+',''.join(t['s'] for t in sh.TX if 'to ONU' in t['s']));ports=len(singles)+2*len(duals)+2*len(floorboxes)
   assert len(tags)==ports,(p,'telephone port labels',len(tags),ports)
   row['audit']['source_port_labels']=len(tags);row['audit']['ports_from_symbols']=ports
   row['audit'].update({'single_symbols':len(singles),'dual_symbols':len(duals),'annotation_arrows_excluded':len(arrow_candidates),'true_outlet_triangle_symbols':len(triangles),'candidate_label_arrows':len(arrow_candidates),'floorbox_symbols':len(floorboxes)})
   for i,d in enumerate(sh.D):
    if d['layer']!='TELEPHONE' or not main(sh,d):continue
    w,h=wh(d);q=d['polys'][0];L,S=max(w,h),min(w,h)
    if p in(30,31) and 33<L<35 and 8<S<9 and len(d['polys'])==8:
     items.append(rec(sh,i,d,'onu',width_cm=60,depth_cm=15,rotation=90 if h>w else 0));continue
    if len(d['polys'])!=1:continue
    closed=len(q)>=4 and math.dist(q[0],q[-1])<.1
    # Some ONU outlines are split into two U-shaped drawing records, so select both halves and deduplicate their bbox.
    if closed and len(q)==5 and (15.5<L<18 if p in(29,32) else 30<L<35):
     if p in(30,31) and S>10:kind='mini_odf'
     else:kind='onu'
     items.append(rec(sh,i,d,kind,width_cm=60,depth_cm=30 if p==29 else 15,rotation=90 if h>w else 0))
    elif p in(30,31) and 30<L<35 and 4<S<9 and (closed or len(q)==4):
     if not any(z['kind']=='onu' and math.dist(z['pdf'],center(d))<.2 for z in items):items.append(rec(sh,i,d,'onu',width_cm=60,depth_cm=15,rotation=90 if h>w else 0))
    if p==29 and closed and len(q)==5 and abs(w-22.68)<.2 and abs(h-22.68)<.2:items.append(rec(sh,i,d,'mdf_rack',width_cm=80,depth_cm=80))
   if p==29:
    # Exact centre lines of the two L-shaped tray outlines, including their short terminal turn.
    for i,nominal,path in [(39821,450,[[845.6,1257.92],[869.96,1257.92],[869.96,1079.36],[1038.32,1079.36]]),(40452,300,[[845.6,1245.86],[856.46,1245.86],[856.46,1065.86],[1038.32,1065.86]])]:
     d=sh.D[i];assert d['layer']=='0' and len(d['polys'][0])==10
     items.append(rec(sh,i,d,'phone_tray' if nominal==450 else 'gsm_tray',path_pdf=path,path=[[round(X,1),round(Y,1)] for X,Y in [sh.T(*pt) for pt in path]],width_mm=nominal,height_mm=50))
   row['audit']['onu_symbols']=sum(z['kind']=='onu' for z in items);row['audit']['mini_odf_symbols']=sum(z['kind']=='mini_odf' for z in items);row['audit']['mdf_racks']=sum(z['kind']=='mdf_rack' for z in items)
 for key,p in DETAILS:
  text=lib.doc(key)[p-1].get_text();out['details'].append({'sheet':f'{key}:{p}','spatial':False,'text':text})
 G=[z for z in out['sheets']['ELEC2:12']['items'] if z['kind']=='down_marker'];F=[z for z in out['sheets']['ELEC2:13']['items'] if z['kind']=='down_marker']
 for a in F:
  b=min(G,key=lambda b:math.dist(a['xy'],b['xy']));dist=math.dist(a['xy'],b['xy'])
  if dist>10:
   missing=a['xy'][0]<500 and a['xy'][1]>1500
   out['conflicts'].append({'kind':'down_conductor_missing_lower_symbol' if missing else 'down_conductor_plan_mismatch','from_sheet':'ELEC2:12','from_cm':None if missing else b['xy'],'to_sheet':'ELEC2:13','to_cm':a['xy'],'distance_cm':None if missing else round(dist,1),'status':'unresolved_in_sources','note':'لا يوجد رمز شمال غرب G مقابل هذا الموصل في الأول؛ الأقرب ليس هوية الموصل ولا مسارًا منحرفًا' if missing else 'المواضع مختلفة في المصدرين؛ لا وصلة تعوض فرقًا غير مرسوم'})
 B=[z for z in out['sheets']['ELEC2:11']['items'] if z['kind']=='basement_down_marker']
 for a in G:
  b=min(B,key=lambda b:math.dist(a['xy'],b['xy']));dist=math.dist(a['xy'],b['xy'])
  if dist>3:out['conflicts'].append({'kind':'down_conductor_plan_mismatch','from_sheet':'ELEC2:11','from_cm':b['xy'],'to_sheet':'ELEC2:12','to_cm':a['xy'],'distance_cm':round(dist,1),'status':'unresolved_in_sources'})
 assert out['sheets']['ELEC2:16']['audit']['air_terminal_symbols']==out['sheets']['ELEC2:16']['audit']['air_terminal_labels']==3
 assert out['sheets']['ELEC2:16']['audit']['equipment_symbols']==6
 if save:json.dump(out,open(DATA,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
 for sk,row in out['sheets'].items():print(sk,dict(collections.Counter(z['kind'] for z in row['items'])),row['audit'])
 return out
if __name__=='__main__':run()
