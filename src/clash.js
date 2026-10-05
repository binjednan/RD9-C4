/* ===== clash inspector =====
   select a clash -> surroundings are ghosted, the two elements are highlighted, the exact point is pinned (marker + label),
   an access route (entrance -> lift -> floor -> point) can be drawn and walked, and the site status / resolution is shown.
   Statuses and notes come from pipeline/data/clash_log.json (merged into model.clashes[].st/res/note/date/by by post_model.py);
   the viewer also keeps the user's own inspection notes in localStorage and can export them as CSV. */
(function(){
'use strict';
const S=0.01;
/* ---------------- navigation grid (per level) ---------------- */
class NavGrid{
  constructor(M,level,cell=10){
    this.cell=cell; this.level=level;
    let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9; const E=[];
    for(const e of M.els){ if(e.l!==level) continue; const g=e.g;
      if(!['A.wall','S.wall','S.col','A.win','S.stair','A.fix','S.slab'].includes(e.c)) continue;
      const bb=g[0]==='r'?[Math.min(g[1],g[3]),Math.min(g[2],g[4]),Math.max(g[1],g[3]),Math.max(g[2],g[4])]:(g[0]==='p'?polyBB(g[1]):null); if(!bb) continue;
      if(e.c!=='S.slab'){x0=Math.min(x0,bb[0]);y0=Math.min(y0,bb[1]);x1=Math.max(x1,bb[2]);y1=Math.max(y1,bb[3]);} E.push(e); }
    this.x0=x0-100; this.y0=y0-100; this.nx=Math.ceil((x1-x0+200)/cell); this.ny=Math.ceil((y1-y0+200)/cell);
    this.blocked=new Uint8Array(this.nx*this.ny); this.walk=new Uint8Array(this.nx*this.ny).fill(1);
    let hasSlab=false; for(const e of E) if(e.c==='S.slab') hasSlab=true;
    if(hasSlab){ this.walk.fill(0); for(const e of E) if(e.c==='S.slab'){ const g=e.g; if(g[0]==='r') this.fillRect(this.walk,g[1],g[2],g[3],g[4],1); else if(g[0]==='p'){ this.fillPoly(this.walk,g[1],1); for(const h of (g[4]||[])) this.fillPoly(this.walk,h,0); } } }
    for(const e of E){ if(e.c==='S.slab') continue; const g=e.g; if(e.t==='lift_car'||e.c!=='A.fix'){ if(g[0]==='r') this.fillRect(this.blocked,g[1],g[2],g[3],g[4],1); else if(g[0]==='p'){ this.fillPoly(this.blocked,g[1],1); for(const h of (g[4]||[])) this.fillPoly(this.blocked,h,0); } } }
    this.inflated={}; // by radius in cells
  }
  idx(ix,iy){return iy*this.nx+ix;}
  cellOf(x,y){return [Math.floor((x-this.x0)/this.cell),Math.floor((y-this.y0)/this.cell)];}
  xyOf(ix,iy){return [this.x0+(ix+0.5)*this.cell,this.y0+(iy+0.5)*this.cell];}
  fillRect(arr,xa,ya,xb,yb,v){const [ix0,iy0]=this.cellOf(Math.min(xa,xb),Math.min(ya,yb)),[ix1,iy1]=this.cellOf(Math.max(xa,xb),Math.max(ya,yb));
    for(let iy=Math.max(0,iy0);iy<=Math.min(this.ny-1,iy1);iy++)for(let ix=Math.max(0,ix0);ix<=Math.min(this.nx-1,ix1);ix++) arr[iy*this.nx+ix]=v;}
  fillPoly(arr,poly,v){const bb=polyBB(poly); const [ix0,iy0]=this.cellOf(bb[0],bb[1]),[ix1,iy1]=this.cellOf(bb[2],bb[3]);
    for(let iy=Math.max(0,iy0);iy<=Math.min(this.ny-1,iy1);iy++){ const y=this.y0+(iy+0.5)*this.cell; const xs=[]; for(let i=0;i<poly.length;i++){const a=poly[i],b=poly[(i+1)%poly.length]; if((a[1]<=y&&b[1]>y)||(b[1]<=y&&a[1]>y)) xs.push(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]));}
      xs.sort((p,q)=>p-q); for(let k=0;k+1<xs.length;k+=2){ const ia=Math.max(0,Math.ceil((xs[k]-this.x0)/this.cell-0.5)), ib=Math.min(this.nx-1,Math.floor((xs[k+1]-this.x0)/this.cell-0.5)); for(let ix=ia;ix<=ib;ix++) arr[iy*this.nx+ix]=v; } } }
  blockedMap(r){ // obstacles dilated by r cells (person radius) + outside the slab
    if(this.inflated[r]) return this.inflated[r]; const nx=this.nx,ny=this.ny,b=this.blocked,w=this.walk; let a=new Uint8Array(nx*ny); for(let i=0;i<a.length;i++) a[i]=(b[i]||!w[i])?1:0;
    if(r>0){ const t=new Uint8Array(nx*ny); for(let iy=0;iy<ny;iy++)for(let ix=0;ix<nx;ix++){ if(!(b[iy*nx+ix])) continue; for(let k=-r;k<=r;k++){const jx=ix+k; if(jx>=0&&jx<nx) t[iy*nx+jx]=1;} }
      const o=new Uint8Array(nx*ny); for(let iy=0;iy<ny;iy++)for(let ix=0;ix<nx;ix++){ if(!t[iy*nx+ix]) continue; for(let k=-r;k<=r;k++){const jy=iy+k; if(jy>=0&&jy<ny) o[jy*nx+ix]=1;} }
      for(let i=0;i<a.length;i++) if(o[i]||!w[i]) a[i]=1; }
    return (this.inflated[r]=a);
  }
  nearestFree(x,y,map,maxR=60){ let [cx,cy]=this.cellOf(x,y); cx=Math.min(this.nx-1,Math.max(0,cx)); cy=Math.min(this.ny-1,Math.max(0,cy)); if(!map[cy*this.nx+cx]) return [cx,cy];
    for(let r=1;r<=maxR;r++){ let best=null,bd=1e9; for(let iy=cy-r;iy<=cy+r;iy++)for(let ix=cx-r;ix<=cx+r;ix++){ if(Math.max(Math.abs(ix-cx),Math.abs(iy-cy))!==r) continue; if(ix<0||iy<0||ix>=this.nx||iy>=this.ny) continue; if(map[iy*this.nx+ix]) continue; const d=(ix-cx)**2+(iy-cy)**2; if(d<bd){bd=d;best=[ix,iy];} } if(best) return best; } return null; }
  flood(sx,sy,map){ const nx=this.nx,ny=this.ny; const seen=new Uint8Array(nx*ny); const q=[sy*nx+sx]; seen[q[0]]=1; for(let h=0;h<q.length;h++){ const i=q[h],ix=i%nx,iy=(i/nx)|0;
      for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){ const jx=ix+dx,jy=iy+dy; if(jx<0||jy<0||jx>=nx||jy>=ny) continue; const j=jy*nx+jx; if(seen[j]||map[j]) continue; seen[j]=1; q.push(j); } } return seen; }
  astar(sx,sy,gx,gy,map){
    const nx=this.nx,ny=this.ny,N=nx*ny; const g=new Float32Array(N).fill(1e9), par=new Int32Array(N).fill(-1), closed=new Uint8Array(N); const heap=[]; const push=(i,f)=>{heap.push([f,i]);let k=heap.length-1;while(k>0){const p=(k-1)>>1;if(heap[p][0]<=heap[k][0])break;[heap[p],heap[k]]=[heap[k],heap[p]];k=p;}};
    const pop=()=>{const t=heap[0],l=heap.pop(); if(heap.length){heap[0]=l;let k=0;for(;;){let a=2*k+1,b=a+1,m=k;if(a<heap.length&&heap[a][0]<heap[m][0])m=a;if(b<heap.length&&heap[b][0]<heap[m][0])m=b;if(m===k)break;[heap[m],heap[k]]=[heap[k],heap[m]];k=m;}}return t;};
    const s=sy*nx+sx,t=gy*nx+gx; g[s]=0; push(s,0); const h=(ix,iy)=>{const dx=Math.abs(ix-gx),dy=Math.abs(iy-gy);return (dx+dy)+(Math.SQRT2-2)*Math.min(dx,dy);};
    while(heap.length){ const [f,i]=pop(); if(closed[i]) continue; closed[i]=1; if(i===t) break; const ix=i%nx,iy=(i/nx)|0;
      for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){ if(!dx&&!dy) continue; const jx=ix+dx,jy=iy+dy; if(jx<0||jy<0||jx>=nx||jy>=ny) continue; const j=jy*nx+jx; if(map[j]||closed[j]) continue;
        if(dx&&dy&&(map[iy*nx+jx]||map[jy*nx+ix])) continue; const ng=g[i]+(dx&&dy?Math.SQRT2:1); if(ng<g[j]){g[j]=ng;par[j]=i;push(j,ng+h(jx,jy));} } }
    if(par[t]<0&&s!==t) return null; const path=[]; for(let i=t;i>=0;i=par[i]){path.push([i%nx,(i/nx)|0]); if(i===s) break;} path.reverse(); return path;
  }
  los(a,b,map){ let [x0,y0]=a,[x1,y1]=b; const dx=Math.abs(x1-x0),dy=Math.abs(y1-y0),sx=x0<x1?1:-1,sy=y0<y1?1:-1; let err=dx-dy; for(;;){ if(map[y0*this.nx+x0]) return false; if(x0===x1&&y0===y1) return true; const e2=2*err; if(e2>-dy){err-=dy;x0+=sx;} if(e2<dx){err+=dx;y0+=sy;} } }
  route(a,b){ // a,b in cm -> polyline in cm (null if no path); tries person radius 2, 1, 0 cells
    for(const r of [2,1,0]){ const map=this.blockedMap(r); const A=this.nearestFree(a[0],a[1],map),B=this.nearestFree(b[0],b[1],map); if(!A||!B) continue;
      const p=this.astar(A[0],A[1],B[0],B[1],map); if(!p) continue; const sm=[p[0]]; let k=0; while(k<p.length-1){ let j=p.length-1; while(j>k+1&&!this.los(p[k],p[j],map)) j--; sm.push(p[j]); k=j; }
      const pts=sm.map(c=>this.xyOf(c[0],c[1])); pts[0]=[a[0],a[1]]; pts[pts.length-1]=[b[0],b[1]]; return {pts,radius:r,snapStart:Math.hypot(this.xyOf(A[0],A[1])[0]-a[0],this.xyOf(A[0],A[1])[1]-a[1]),snapEnd:Math.hypot(this.xyOf(B[0],B[1])[0]-b[0],this.xyOf(B[0],B[1])[1]-b[1])}; }
    return null; }
}
function polyBB(p){let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;for(const q of p){x0=Math.min(x0,q[0]);y0=Math.min(y0,q[1]);x1=Math.max(x1,q[0]);y1=Math.max(y1,q[1]);}return [x0,y0,x1,y1];}
const plen=pts=>{let L=0;for(let i=1;i<pts.length;i++)L+=Math.hypot(pts[i][0]-pts[i-1][0],pts[i][1]-pts[i-1][1]);return L;};
const COMPASS=['شرقًا','شمال شرق','شمالًا','شمال غرب','غربًا','جنوب غرب','جنوبًا','جنوب شرق'];
const dirWord=(dx,dy)=>COMPASS[Math.round(((Math.atan2(dy,dx)*180/Math.PI+360)%360)/45)%8];

/* ---------------- inspector ---------------- */
function initClash(ctx){
  const {M,THREE,scene,camera,controls,$,esc,LVL,UNITS,wake,flyTo,ensureVisible,select,highlight,addHL,clearHL,toast,setGhost,focusEl}=ctx;
  const C=M.clashes||[]; const K=M.clashKinds||{}; const LOGM=M.clashLog||{statuses:{open:'مفتوح'},counts:{},history:[]}; const ST=LOGM.statuses||{};
  const ENTRANCE={x:1690,y:1630,note:'المدخل الرئيسي: الفتحة بين واجهتَي الزجاج GFR-5 وGFR-6 على الواجهة الشمالية للمبنى؛ تتطابق مع وسم ENTRANCE في A102 — موضع تقديري'};
  const grids={}; const gridOf=l=>grids[l]||(grids[l]=new NavGrid(M,l));
  const liftEl=M.els.find(e=>e.t==='lift_car'); const lift=liftEl?{x:(liftEl.g[1]+liftEl.g[3])/2,y:(liftEl.g[2]+liftEl.g[4])/2,bb:[Math.min(liftEl.g[1],liftEl.g[3]),Math.min(liftEl.g[2],liftEl.g[4]),Math.max(liftEl.g[1],liftEl.g[3]),Math.max(liftEl.g[2],liftEl.g[4])],stops:(liftEl.a&&liftEl.a.stops)||''}:null;
  const localKey=id=>'c4clash:'+id; const getLocal=id=>{try{return JSON.parse(localStorage.getItem(localKey(id))||'null');}catch(e){return null;}}; const setLocal=(id,v)=>{try{if(v) localStorage.setItem(localKey(id),JSON.stringify(v)); else localStorage.removeItem(localKey(id));}catch(e){}};
  let cur=-1, ghostOp=0.08, marker=null, route=null, routeObj=null, tour=null, pinEl=null, stFilter='*', kFilter='*', shown=120;
  /* marker */
  function makeMarker(){
    const g=new THREE.Group(); const mat=c=>new THREE.MeshBasicMaterial({color:c,depthTest:false,transparent:true,opacity:0.95}); g.renderOrder=1002;
    const sp=new THREE.Mesh(new THREE.SphereGeometry(0.08,18,12),mat(0xff2bd6)); sp.renderOrder=1003; g.add(sp);
    const ring=(rot)=>{const r=new THREE.Mesh(new THREE.TorusGeometry(0.3,0.012,8,40),mat(0xff2bd6)); r.rotation.set(rot[0],rot[1],rot[2]); r.renderOrder=1002; return r;};
    g.userData.rings=[ring([Math.PI/2,0,0]),ring([0,0,0]),ring([0,Math.PI/2,0])]; g.userData.rings.forEach(r=>g.add(r));
    const lm=new THREE.LineBasicMaterial({color:0xff2bd6,depthTest:false,transparent:true}); const pts=[]; for(const a of [[1,0,0],[0,1,0],[0,0,1]]){pts.push(new THREE.Vector3(-0.75*a[0],-0.75*a[1],-0.75*a[2]),new THREE.Vector3(0.75*a[0],0.75*a[1],0.75*a[2]));}
    const cross=new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(pts),lm); cross.renderOrder=1002; g.add(cross);
    g.userData.drop=new THREE.Line(new THREE.BufferGeometry(),new THREE.LineDashedMaterial({color:0xff2bd6,dashSize:0.12,gapSize:0.08,depthTest:false,transparent:true})); g.userData.drop.renderOrder=1002; scene.add(g.userData.drop);
    g.userData.floor=new THREE.Mesh(new THREE.RingGeometry(0.18,0.26,32),new THREE.MeshBasicMaterial({color:0xff2bd6,depthTest:false,transparent:true,opacity:0.9,side:THREE.DoubleSide})); g.userData.floor.rotation.x=-Math.PI/2; g.userData.floor.renderOrder=1002; scene.add(g.userData.floor);
    scene.add(g); return g;
  }
  function placeMarker(c){
    if(!marker) marker=makeMarker(); const p=new THREE.Vector3(c.pt[0],c.pt[1],c.pt[2]); marker.position.copy(p); marker.visible=true;
    const fl=LVL[c.l].ffl; marker.userData.drop.geometry.setFromPoints([p,new THREE.Vector3(p.x,fl+0.02,p.z)]); marker.userData.drop.computeLineDistances(); marker.userData.drop.visible=true;
    marker.userData.floor.position.set(p.x,fl+0.03,p.z); marker.userData.floor.visible=true; wake(2000);
  }
  function clearMarker(){ if(!marker) return; marker.visible=false; marker.userData.drop.visible=false; marker.userData.floor.visible=false; if(pinEl) pinEl.style.display='none'; }
  function elName(ei){const e=M.els[ei]; return (e.mark||e.id)+' — '+((M.types&&M.types[e.t]&&M.types[e.t].n)||e.t||e.c);}
  function unitOf(ei){const e=M.els[ei]; const u=e.u&&UNITS.find(x=>x.id===e.u); return u?u.name:null;}
  function planXY(c){return [Math.round(c.pt[0]*100),Math.round(-c.pt[2]*100)];}
  /* route */
  function buildRoute(c){
    const [tx,ty]=planXY(c); const lv=c.l; const out={legs:[],steps:[],total:0,warn:[]}; const fl=l=>LVL[l].ffl;
    const entry=[ENTRANCE.x,ENTRANCE.y];
    const addWalk=(level,a,b,label)=>{ const G=gridOf(level); const r=G.route(a,b); if(!r){ out.warn.push(`تعذّر إيجاد ممر حرّ في الطابق ${LVL[level].name} — رُسم خط مباشر تقريبي`); const pts=[a,b]; out.legs.push({kind:'walk',level,pts,approx:true,label}); out.total+=plen(pts); return pts; }
      if(r.radius<2) out.warn.push(`ضيق في الممر قرب ${label}: استُعمل نصف قطر مرور أصغر`); out.legs.push({kind:'walk',level,pts:r.pts,label,snapEnd:r.snapEnd}); out.total+=plen(r.pts); return r.pts; };
    const lobby=(level,toward)=>{ const G=gridOf(level); const map=G.blockedMap(2); const base=lift?[lift.x,lift.bb[3]+70]:toward; const A=G.nearestFree(toward[0],toward[1],map)||G.nearestFree(toward[0],toward[1],G.blockedMap(0)); if(!A) return base;
      const seen=G.flood(A[0],A[1],map); let best=null,bd=1e9; const lx=lift.x,ly=lift.y; for(let iy=0;iy<G.ny;iy++)for(let ix=0;ix<G.nx;ix++){ if(!seen[iy*G.nx+ix]) continue; const [x,y]=G.xyOf(ix,iy); if(x>=lift.bb[0]-5&&x<=lift.bb[2]+5&&y>=lift.bb[1]-5&&y<=lift.bb[3]+5) continue; const d=Math.hypot(x-lx,y-ly); if(d<bd){bd=d;best=[x,y];} } return best||base; };
    if(lv==='G'||!lift){ addWalk('G',entry,[tx,ty],'المدخل الرئيسي → موضع التعارض'); out.steps.push({t:`ادخل من المدخل الرئيسي (${ENTRANCE.note})`}); }
    else {
      const gl=lobby('G',entry); addWalk('G',entry,gl,'المدخل → ردهة المصعد'); out.steps.push({t:`ادخل من المدخل الرئيسي (${ENTRANCE.note})`});
      const ll=lobby(lv,[tx,ty]); out.legs.push({kind:'lift',from:'G',to:lv,pt:[ll[0],ll[1]],ptG:[gl[0],gl[1]]}); out.steps.push({t:`اركب المصعد (موقع المصعد ≈ X ${Math.round(lift.x)} / Y ${Math.round(lift.y)} سم) من الطابق الأرضي إلى «${LVL[lv].name}» — محطات المصعد: ${lift.stops}`});
      addWalk(lv,ll,[tx,ty],'ردهة المصعد → موضع التعارض'); }
    return out;
  }
  function describeLeg(L){ const p=L.pts; if(p.length<2) return; const parts=[]; let acc=0; const hd=(i)=>dirWord(p[i+1][0]-p[i][0],p[i+1][1]-p[i][1]);
    parts.push({t:`${L.label}: امشِ ${Math.round(Math.hypot(p[1][0]-p[0][0],p[1][1]-p[0][1])/10)/10} م ${hd(0)}`});
    for(let i=1;i<p.length-1;i++){ const a=[p[i][0]-p[i-1][0],p[i][1]-p[i-1][1]],b=[p[i+1][0]-p[i][0],p[i+1][1]-p[i][1]]; const cr=a[0]*b[1]-a[1]*b[0],dt=a[0]*b[0]+a[1]*b[1]; const ang=Math.atan2(cr,dt)*180/Math.PI; const side=Math.abs(ang)<20?'تابع':(ang>0?'انعطف يسارًا':'انعطف يمينًا');
      parts.push({t:`${side} ثم امشِ ${Math.round(Math.hypot(b[0],b[1])/10)/10} م ${dirWord(b[0],b[1])}`}); }
    return parts; }
  function drawRoute(r,c){
    if(routeObj){scene.remove(routeObj); routeObj.traverse(o=>{if(o.geometry)o.geometry.dispose();});} routeObj=new THREE.Group(); routeObj.renderOrder=1001;
    const cols={walk:0x00c2a8,lift:0xff9f1c}; const addLine=(pts3,color,dashed)=>{ const g=new THREE.BufferGeometry().setFromPoints(pts3); const m=dashed?new THREE.LineDashedMaterial({color,dashSize:0.2,gapSize:0.12,depthTest:false,transparent:true}):new THREE.LineBasicMaterial({color,depthTest:false,transparent:true,opacity:0.95,linewidth:2}); const ln=new THREE.Line(g,m); if(dashed) ln.computeLineDistances(); ln.renderOrder=1001; routeObj.add(ln);
      // thick look: duplicate lines with small offsets
      for(const o of [[0.02,0],[0,0.02],[-0.02,0]]){ const g2=new THREE.BufferGeometry().setFromPoints(pts3.map(p=>new THREE.Vector3(p.x+o[0],p.y,p.z+o[1]))); const l2=new THREE.Line(g2,m); if(dashed) l2.computeLineDistances(); l2.renderOrder=1001; routeObj.add(l2);} };
    const W=(p,l)=>new THREE.Vector3(p[0]*S,LVL[l].ffl+0.12,-p[1]*S);
    r.legs.forEach(L=>{ if(L.kind==='walk'){ addLine(L.pts.map(p=>W(p,L.level)),cols.walk,!!L.approx);
        // arrow cones every 3 m
        let acc=0; for(let i=1;i<L.pts.length;i++){ const a=L.pts[i-1],b=L.pts[i]; const len=Math.hypot(b[0]-a[0],b[1]-a[1]); const n=Math.max(1,Math.floor(len/300)); for(let k=1;k<=n;k++){ const t=(k-0.5)/n; const x=a[0]+(b[0]-a[0])*t,y=a[1]+(b[1]-a[1])*t; const cone=new THREE.Mesh(new THREE.ConeGeometry(0.1,0.28,10),new THREE.MeshBasicMaterial({color:cols.walk,depthTest:false,transparent:true})); cone.position.copy(W([x,y],L.level)); cone.position.y+=0.05; cone.renderOrder=1001;
            const dir=new THREE.Vector3((b[0]-a[0]),0,-(b[1]-a[1])).normalize(); cone.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),dir); routeObj.add(cone);} } }
      else { const p=[W(L.ptG,L.from),W(L.pt,L.to)]; addLine(p,cols.lift,true); const lb=new THREE.Mesh(new THREE.SphereGeometry(0.14,12,8),new THREE.MeshBasicMaterial({color:cols.lift,depthTest:false,transparent:true})); lb.position.copy(p[0]); lb.renderOrder=1001; routeObj.add(lb); const lb2=lb.clone(); lb2.position.copy(p[1]); routeObj.add(lb2); } });
    // start + end flags
    const mk=(pos,color)=>{const m=new THREE.Mesh(new THREE.SphereGeometry(0.16,12,8),new THREE.MeshBasicMaterial({color,depthTest:false,transparent:true})); m.position.copy(pos); m.renderOrder=1002; routeObj.add(m);};
    const f=r.legs[0]; mk(W(f.pts[0],f.level),0x2ecc40); scene.add(routeObj); wake(1500);
  }
  function clearRoute(){ if(routeObj){scene.remove(routeObj); routeObj.traverse(o=>{if(o.geometry)o.geometry.dispose();}); routeObj=null;} route=null; tour=null; }
  /* tour: camera walks the route at eye height, ends looking at the clash point */
  function startTour(c){
    if(!route) route=buildRoute(c); if(!tour) tour=null; const eye=1.65; const pts=[];
    route.legs.forEach(L=>{ if(L.kind==='walk'){ const ps=resample(L.pts,150); ps.forEach(p=>pts.push({x:p[0]*S,y:LVL[L.level].ffl+eye,z:-p[1]*S})); } else { pts.push({x:L.ptG[0]*S,y:LVL[L.from].ffl+eye,z:-L.ptG[1]*S,lift:true}); pts.push({x:L.pt[0]*S,y:LVL[L.to].ffl+eye,z:-L.pt[1]*S,lift:true}); } });
    if(pts.length<2) return; tour={pts,i:0,t:0,look:new THREE.Vector3(c.pt[0],c.pt[1],c.pt[2]),done:false,endAt:0}; controls.stop(); drawRoute(route,c); toast('جولة المشي: انقر أو اسحب لإيقافها',2500); wake(1000);
  }
  function resample(pts,step){ const out=[pts[0]]; for(let i=1;i<pts.length;i++){ const a=pts[i-1],b=pts[i]; const len=Math.hypot(b[0]-a[0],b[1]-a[1]); const n=Math.max(1,Math.round(len/step)); for(let k=1;k<=n;k++) out.push([a[0]+(b[0]-a[0])*k/n,a[1]+(b[1]-a[1])*k/n]); } return out; }
  function frame(now,dt){
    if(marker&&marker.visible){ const k=1+0.18*Math.sin(now/260); marker.userData.rings.forEach((r,i)=>r.scale.setScalar(k+(i*0.04))); wake(100); updatePin(); }
    if(tour){ const T=tour; const sp=2.2; // m/s
      if(T.i>=T.pts.length-1){ if(!T.done){T.done=true;T.endAt=now;} const k=Math.min(1,(now-T.endAt)/900); camera.lookAt(T.look.clone().lerp(camera.position,0)); controls.target.copy(T.look); camera.lookAt(controls.target); if(now-T.endAt>1200){tour=null;} wake(300); return; }
      const a=T.pts[T.i],b=T.pts[T.i+1]; const dx=b.x-a.x,dy=b.y-a.y,dz=b.z-a.z; const L=Math.hypot(dx,dy,dz)||1e-6; const spd=(b.lift?1.6:sp); T.t+=dt*spd/L; if(T.t>=1){T.t=0;T.i++;}
      const t=Math.min(1,T.t); const px=a.x+dx*t,py=a.y+dy*t,pz=a.z+dz*t; camera.position.set(px,py,pz); const nxt=T.pts[Math.min(T.pts.length-1,T.i+2)]; const tgt=(T.i>=T.pts.length-3)?T.look:new THREE.Vector3(nxt.x,Math.min(nxt.y,py),nxt.z); controls.target.copy(tgt); camera.lookAt(tgt); wake(300); }
  }
  function updatePin(){ if(!pinEl||cur<0||!marker||!marker.visible){ if(pinEl) pinEl.style.display='none'; return; }
    const v=marker.position.clone().project(camera); if(v.z>1||v.z<-1||Math.abs(v.x)>1.1||Math.abs(v.y)>1.1){pinEl.style.display='none';return;} const r=$('view').getBoundingClientRect(); pinEl.style.display='block'; pinEl.style.left=((v.x+1)/2*r.width+14)+'px'; pinEl.style.top=((1-v.y)/2*r.height-18)+'px'; }
  /* UI */
  function stBadge(st){ const col={open:'#8b949e',checking:'#bf8700',resolved:'#1a7f37',accepted:'#0969da',false:'#6e7781',design:'#cf222e'}[st]||'#8b949e'; return `<span class="stb" style="background:${col}">${esc(ST[st]||st)}</span>`; }
  function listHTML(){
    const kinds={}; C.forEach(c=>kinds[c.k]=(kinds[c.k]||0)+1);
    let h=`<div class=note>${esc(M.clashNote||'')}</div><div class=chips><span class="chip ${kFilter==='*'?'on':''}" data-k="*">الكل (${C.length})</span>`+Object.keys(kinds).map(k=>`<span class="chip ${kFilter===k?'on':''}" data-k="${esc(k)}">${esc(K[k]||k)} (${kinds[k]})</span>`).join('')+`</div>`;
    const cnt=LOGM.counts||{}; h+=`<div class=chips><span class="chip ${stFilter==='*'?'on':''}" data-s="*">كل الحالات</span>`+Object.keys(ST).map(s=>`<span class="chip ${stFilter===s?'on':''}" data-s="${s}">${esc(ST[s])} (${cnt[s]||0})</span>`).join('')+`</div>`;
    const list=C.map((c,i)=>[c,i]).filter(x=>(kFilter==='*'||x[0].k===kFilter)&&(stFilter==='*'||(x[0].st||'open')===stFilter));
    h+=`<div class=row style="gap:6px;flex-wrap:wrap"><button class="mini" id="clPlan">خطة تفتيش مرتّبة (${Math.min(list.length,60)})</button><button class="mini" id="clExport">تصدير ملاحظاتي CSV</button></div>`;
    h+=list.slice(0,shown).map(([c,i])=>`<div class="res${i===cur?' sel':''}" data-c="${i}"><b>${esc(K[c.k]||c.k)}</b> ${stBadge(c.st||'open')}<small>${esc(M.els[c.a].mark||M.els[c.a].id)} × ${esc(M.els[c.b].mark||M.els[c.b].id)} • ${esc(LVL[c.l].name)}${c.v?' • حجم التداخل ≈ '+c.v+' م³':''}${(getLocal(c.id)||{}).st?' • <i>ملاحظتي: '+esc(ST[getLocal(c.id).st]||'')+'</i>':''}</small></div>`).join('');
    if(list.length>shown) h+=`<div class="chip" id="clMore" style="text-align:center;margin-top:8px">عرض المزيد (${list.length-shown})</div>`;
    return h; }
  function detailHTML(c){
    const [px,py]=planXY(c); const ffl=LVL[c.l].ffl; const above=c.pt[1]-ffl; const loc=getLocal(c.id)||{}; const ua=unitOf(c.a),ub=unitOf(c.b);
    const assumed=[c.a,c.b].some(i=>/افتراض/.test(((M.els[i].s||[]).map(k=>M.sp[k]||'')).join(' ')));
    let h=`<div class="cdet"><div class="chead"><b>${esc(K[c.k]||c.k)}</b> <code>${esc(c.id||'')}</code> ${stBadge(c.st||'open')}</div>
      <table class="ctab"><tr><th>العنصر A (برتقالي)</th><td><a href="#" data-f="${c.a}">${esc(elName(c.a))}</a></td></tr><tr><th>العنصر B (أزرق)</th><td><a href="#" data-f="${c.b}">${esc(elName(c.b))}</a></td></tr>
      <tr><th>الطابق</th><td>${esc(LVL[c.l].name)} (منسوب الأرضية ${ffl.toFixed(2)} م)</td></tr>
      <tr><th>الموضع (سم من نقطة أصل المخطط)</th><td>X = ${px} ، Y = ${py}</td></tr>
      <tr><th>الارتفاع</th><td>${(above).toFixed(2)} م فوق أرضية الطابق (المنسوب المطلق ${c.pt[1].toFixed(2)} م)${above>2.6&&c.l!=='B'?' — <b>فوق السقف المستعار</b>':''}</td></tr>
      <tr><th>الوحدة / الموقع</th><td>${esc(ua||ub||'أجزاء مشتركة (ممر/ردهة/خدمات)')}</td></tr>
      ${c.v?`<tr><th>حجم التداخل</th><td>≈ ${c.v} م³</td></tr>`:''}</table>
      ${assumed?'<div class="warnbox">أحد العنصرين أو كليهما بمنسوب افتراضي (انظر بطاقة العنصر) — التعارض مرشّح للمراجعة وليس حكمًا.</div>':''}`;
    if(c.st&&c.st!=='open'||c.res||c.note) h+=`<div class="okbox"><b>سجل الموقع:</b> ${stBadge(c.st||'open')} ${c.date?'<small>'+esc(c.date)+'</small>':''} ${c.by?'<small>— '+esc(c.by)+'</small>':''}${c.res?'<div><b>طريقة الحل:</b> '+esc(c.res)+'</div>':''}${c.note?'<div>'+esc(c.note)+'</div>':''}</div>`;
    h+=`<div class="sliderrow"><span>شفافية المحيط</span><input type="range" id="clGhost" min="0" max="40" value="${Math.round(ghostOp*100)}"><b id="clGhostV">${Math.round(ghostOp*100)}%</b></div>
      <div class=row style="gap:6px;flex-wrap:wrap"><button class="mini" id="clRoute">مسار الوصول</button><button class="mini" id="clTour">جولة مشي</button><button class="mini" id="clCam">إعادة التوجيه</button><button class="mini" id="clEnd">إنهاء التركيز</button></div>
      <div id="clSteps"></div>
      <div class="mynote"><b>ملاحظتي بعد المعاينة:</b><select id="clMySt"><option value="">— لا شيء —</option>${Object.keys(ST).map(s=>`<option value="${s}" ${loc.st===s?'selected':''}>${esc(ST[s])}</option>`).join('')}</select>
      <textarea id="clMyTx" rows="2" placeholder="كيف حُلّ في الواقع؟ (مرور عبر ثقب / تغيير مسار / رفع منسوب...)">${esc(loc.tx||'')}</textarea><button class="mini" id="clMySave">حفظ على هذا الجهاز</button></div></div>`;
    return h; }
  function stepsHTML(r){ let n=1; let h='<ol class="steps">'; const legsText=[]; r.legs.forEach(L=>{ if(L.kind==='walk'){ const d=describeLeg(L)||[]; legsText.push(...d.map(x=>x.t)); } else legsText.push(`الصعود بالمصعد من ${LVL[L.from].name} إلى ${LVL[L.to].name}`); });
    r.steps.forEach(s=>h+=`<li>${esc(s.t)}</li>`); legsText.forEach(t=>h+=`<li>${esc(t)}</li>`);
    const c=C[cur]; const above=c.pt[1]-LVL[c.l].ffl; h+=`<li>${above>2.6&&c.l!=='B'?'افتح بلاطة السقف المستعار (أو فتحة الصيانة) عند هذه النقطة ثم عاين على ارتفاع '+above.toFixed(2)+' م فوق الأرضية — أحضر سلّمًا مناسبًا.':'عاين على ارتفاع '+above.toFixed(2)+' م فوق الأرضية.'}</li></ol>`;
    h+=`<div class="muted">إجمالي المشي ≈ ${(r.total/100).toFixed(0)} م · الاتجاهات بالنسبة لمحاور المخطط (الشمال = أعلى المخطط وليس الشمال الجغرافي)</div>`; r.warn.forEach(w=>h+=`<div class="warnbox">${esc(w)}</div>`); return h; }
  function show(i){
    cur=i; const c=C[i]; ensureVisible(c.a); ensureVisible(c.b); clearRoute(); setGhost(true,ghostOp,[c.l]); clearHL(); highlight([c.a],0xff8a00,true,0.32); addHL([c.b],0x2f81f7,true,0.28); placeMarker(c);
    const p=new THREE.Vector3(c.pt[0],c.pt[1],c.pt[2]); const dirv=new THREE.Vector3(-0.55,0.35,0.75).normalize(); flyTo(p.clone().addScaledVector(dirv,3.2),p); document.body.classList.remove('panel-open');
    $('clashDetail').innerHTML=detailHTML(c); $('clashDetail').style.display='block'; bindDetail(c); refreshList(); updatePin(); if(pinEl) pinEl.innerHTML=`◎ ${esc(c.id||'')}<br><small>${esc(LVL[c.l].name)} · ${(c.pt[1]-LVL[c.l].ffl).toFixed(2)} م فوق الأرضية</small>`; }
  function endFocus(){ cur=-1; setGhost(false); clearHL(); clearMarker(); clearRoute(); $('clashDetail').style.display='none'; $('clashDetail').innerHTML=''; refreshList(); wake(); }
  function bindDetail(c){
    const d=$('clashDetail');
    d.querySelectorAll('a[data-f]').forEach(a=>a.onclick=ev=>{ev.preventDefault(); const ei=+a.dataset.f; clearHL(); highlight([ei],ei===c.a?0xff8a00:0x2f81f7,true,0.35); const bb=ctx.bboxOf([ei]); const p=new THREE.Vector3(bb.c[0],bb.c[1],bb.c[2]); flyTo(p.clone().add(new THREE.Vector3(-0.55,0.4,0.7).normalize().multiplyScalar(Math.max(2.5,bb.r*2.4))),p);});
    $('clGhost').oninput=ev=>{ghostOp=ev.target.value/100; $('clGhostV').textContent=ev.target.value+'%'; setGhost(true,ghostOp,[c.l]);};
    $('clEnd').onclick=endFocus; $('clCam').onclick=()=>{const p=new THREE.Vector3(c.pt[0],c.pt[1],c.pt[2]); flyTo(p.clone().addScaledVector(new THREE.Vector3(-0.55,0.35,0.75).normalize(),3.2),p);};
    $('clRoute').onclick=()=>{ if(!route) route=buildRoute(c); drawRoute(route,c); $('clSteps').innerHTML=stepsHTML(route); const pts=[]; route.legs.forEach(L=>{ if(L.kind==='walk') L.pts.forEach(p=>pts.push(p)); }); wake(1500); // frame the whole route
      let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9; pts.concat([[c.pt[0]*100,-c.pt[2]*100]]).forEach(p=>{x0=Math.min(x0,p[0]);y0=Math.min(y0,p[1]);x1=Math.max(x1,p[0]);y1=Math.max(y1,p[1]);}); const cx=(x0+x1)/2*S,cz=-(y0+y1)/2*S,r=Math.max(6,Math.hypot(x1-x0,y1-y0)*S*0.7); flyTo(new THREE.Vector3(cx-r*0.3,LVL[c.l].ffl+r*1.1,cz+r*0.9),new THREE.Vector3(cx,LVL[c.l].ffl,cz),900); };
    $('clTour').onclick=()=>{ if(!route){route=buildRoute(c);} $('clSteps').innerHTML=stepsHTML(route); startTour(c); };
    $('clMySave').onclick=()=>{ const st=$('clMySt').value,tx=$('clMyTx').value.trim(); setLocal(c.id,(st||tx)?{st,tx,ts:new Date().toISOString()}:null); toast('حُفظت ملاحظتك على هذا الجهاز'); refreshList(); };
  }
  function refreshList(){ const box=$('clashBox'); const top=box.scrollTop; box.innerHTML=listHTML(); box.scrollTop=top; }
  function plan(){
    const list=C.map((c,i)=>[c,i]).filter(x=>(kFilter==='*'||x[0].k===kFilter)&&(stFilter==='*'||(x[0].st||'open')===stFilter)).slice(0,60); const order=[]; const order_l=M.levels.map(l=>l.id);
    const byL={}; list.forEach(x=>(byL[x[0].l]=byL[x[0].l]||[]).push(x)); let cum=0,h='<div class="note"><b>خطة تفتيش مرتّبة:</b> حسب الطابق ثم الأقرب فالأقرب (المسافة تقريب مستقيم). انقر عنصرًا لفتحه.</div><ol class="steps">';
    order_l.forEach(l=>{ const arr=byL[l]; if(!arr) return; let cx=ENTRANCE.x,cy=ENTRANCE.y; const rest=arr.slice(); h+=`<li><b>${esc(LVL[l].name)}</b> (${arr.length})<ol>`; while(rest.length){ let bi=0,bd=1e18; rest.forEach((x,k)=>{const [px,py]=planXY(x[0]); const d=(px-cx)**2+(py-cy)**2; if(d<bd){bd=d;bi=k;}}); const [c,i]=rest.splice(bi,1)[0]; const [px,py]=planXY(c); cum+=Math.sqrt(bd)/100; cx=px;cy=py; order.push([c,i]); h+=`<li><a href="#" data-c="${i}">${esc(K[c.k]||c.k)} — ${esc(M.els[c.a].mark||M.els[c.a].id)} × ${esc(M.els[c.b].mark||M.els[c.b].id)}</a> <small>(${(c.pt[1]-LVL[c.l].ffl).toFixed(1)} م)</small></li>`; } h+='</ol></li>'; });
    h+=`</ol><div class="muted">إجمالي مسافة التنقل التقريبية بين النقاط ≈ ${cum.toFixed(0)} م</div>`; const d=$('clashDetail'); d.innerHTML=h; d.style.display='block'; d.querySelectorAll('a[data-c]').forEach(a=>a.onclick=ev=>{ev.preventDefault();show(+a.dataset.c);}); }
  function exportCSV(){
    const rows=[['id','level','kind','element_a','element_b','x_cm','y_cm','z_above_floor_m','site_status','my_status','my_note']];
    C.forEach(c=>{const l=getLocal(c.id); const [px,py]=planXY(c); rows.push([c.id,c.l,K[c.k]||c.k,c.ea,c.eb,px,py,(c.pt[1]-LVL[c.l].ffl).toFixed(2),ST[c.st||'open']||'',l&&l.st?ST[l.st]:'',l&&l.tx?l.tx:'']);});
    const csv='﻿'+rows.map(r=>r.map(v=>'"'+String(v==null?'':v).replace(/"/g,'""')+'"').join(',')).join('\n'); const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([csv],{type:'text/csv'})); a.download='c4_clash_inspection.csv'; document.body.appendChild(a); a.click(); setTimeout(()=>{URL.revokeObjectURL(a.href);a.remove();},500); }
  function build(){
    const box=$('clashBox'); if(!C.length){box.innerHTML='<div class=muted>لا توجد تعارضات محسوبة في هذا الإصدار من النموذج.</div>';return;}
    pinEl=$('clashPin'); box.innerHTML=listHTML();
    box.onclick=ev=>{ const ch=ev.target.closest('.chip[data-k]'); if(ch){kFilter=ch.dataset.k;shown=120;refreshList();return;} const cs=ev.target.closest('.chip[data-s]'); if(cs){stFilter=cs.dataset.s;shown=120;refreshList();return;}
      if(ev.target.closest('#clMore')){shown+=200;refreshList();return;} if(ev.target.closest('#clPlan')){plan();return;} if(ev.target.closest('#clExport')){exportCSV();return;}
      const r=ev.target.closest('.res[data-c]'); if(r) show(+r.dataset.c); };
    window.addEventListener('pointerdown',ev=>{ if(tour&&ev.target&&ev.target.closest&&ev.target.closest('#view')) {tour=null; toast('أُوقفت الجولة');} },true);
  }
  build();
  window.__nav=gridOf; return {show,endFocus,frame,get current(){return cur;},buildRoute};
}
window.initClash=initClash;
})();
