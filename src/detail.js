/* ===== sample library + level-of-detail swapping =====
   samples.json (window.__SAMPLES__) holds one detailed, realistic sample per component type of the project.
   When the camera comes close to an element that has a sample, the plain proxy of the model is hidden (per-vertex aHide flag)
   and the sample is drawn in its place (instanced meshes). Far away the original proxy is shown again.
   Units: model cm for sample dimensions, metres in the scene. Local sample frame: x = width, y = up, z = depth (+z = front). */
(function(){
'use strict';
const S=0.01;
/* ---------- tiny safe expression evaluator (no eval) ---------- */
const FN={min:Math.min,max:Math.max,abs:Math.abs,round:Math.round,floor:Math.floor,ceil:Math.ceil,sqrt:Math.sqrt,sin:Math.sin,cos:Math.cos,tan:Math.tan,atan2:Math.atan2,pow:Math.pow,clamp:(a,l,h)=>Math.min(h,Math.max(l,a))};
const CACHE=new Map();
function tokenize(s){const t=[];const re=/\s*(\d+\.?\d*|\.\d+|[A-Za-z_][A-Za-z_0-9]*|<=|>=|==|!=|&&|\|\||[-+*\/%(),?:<>!])/y;let m;re.lastIndex=0;while(re.lastIndex<s.length&&(m=re.exec(s))){t.push(m[1]);}return t;}
function compile(src){
  if(CACHE.has(src)) return CACHE.get(src);
  const tk=tokenize(src); let i=0;
  const peek=()=>tk[i], next=()=>tk[i++];
  function ternary(){const c=logic(); if(peek()==='?'){next();const a=ternary();if(next()!==':')throw new Error('expr ":" expected in '+src);const b=ternary();return v=>c(v)?a(v):b(v);} return c;}
  function logic(){let l=cmp();while(peek()==='&&'||peek()==='||'){const op=next(),r=cmp(),L=l;l=op==='&&'?(v=>L(v)&&r(v)):(v=>L(v)||r(v));}return l;}
  function cmp(){let l=add();const o=peek();if(['<','>','<=','>=','==','!='].includes(o)){next();const r=add(),L=l;return o==='<'?v=>L(v)<r(v):o==='>'?v=>L(v)>r(v):o==='<='?v=>L(v)<=r(v):o==='>='?v=>L(v)>=r(v):o==='=='?v=>L(v)===r(v):v=>L(v)!==r(v);}return l;}
  function add(){let l=mul();while(peek()==='+'||peek()==='-'){const o=next(),r=mul(),L=l;l=o==='+'?v=>L(v)+r(v):v=>L(v)-r(v);}return l;}
  function mul(){let l=un();while(peek()==='*'||peek()==='/'||peek()==='%'){const o=next(),r=un(),L=l;l=o==='*'?v=>L(v)*r(v):o==='/'?v=>L(v)/r(v):v=>L(v)%r(v);}return l;}
  function un(){if(peek()==='-'){next();const e=un();return v=>-e(v);} if(peek()==='+'){next();return un();} if(peek()==='!'){next();const e=un();return v=>e(v)?0:1;} return prim();}
  function prim(){const t=next(); if(t===undefined) throw new Error('expr end in '+src);
    if(t==='('){const e=ternary();if(next()!==')')throw new Error('expr ")" expected in '+src);return e;}
    if(/^[\d.]/.test(t)){const n=parseFloat(t);return ()=>n;}
    if(/^[A-Za-z_]/.test(t)){ if(peek()==='('){next();const args=[];if(peek()!==')'){for(;;){args.push(ternary());if(peek()===',')next();else break;}}if(next()!==')')throw new Error('expr ")" expected in '+src);const f=FN[t];if(!f)throw new Error('unknown function '+t);return v=>f(...args.map(a=>a(v)));}
      if(t==='PI') return ()=>Math.PI; return v=>{const x=v[t];if(x===undefined)throw new Error('unknown variable '+t+' in '+src);return x;};}
    throw new Error('bad token '+t+' in '+src);}
  const f=ternary(); if(i<tk.length) throw new Error('trailing tokens in '+src);
  CACHE.set(src,f); return f;
}
const ev=(x,v)=>typeof x==='number'?x:(typeof x==='string'?compile(x)(v):x);
const evA=(a,v)=>a.map(x=>ev(x,v));
const hexRGB=h=>{h=h.replace('#','');if(h.length===3)h=h.split('').map(c=>c+c).join('');const n=parseInt(h,16);return [((n>>16)&255)/255,((n>>8)&255)/255,(n&255)/255];};

/* ---------- geometry from parts ---------- */
class Buf{constructor(){this.pos=[];this.nrm=[];this.col=[];}}
function addTri(B,a,b,c,na,nb,nc,col){B.pos.push(a[0],a[1],a[2],b[0],b[1],b[2],c[0],c[1],c[2]);B.nrm.push(na[0],na[1],na[2],nb[0],nb[1],nb[2],nc[0],nc[1],nc[2]);for(let i=0;i<3;i++)B.col.push(col[0],col[1],col[2]);}
function flatTri(B,a,b,c,col){const ux=b[0]-a[0],uy=b[1]-a[1],uz=b[2]-a[2],vx=c[0]-a[0],vy=c[1]-a[1],vz=c[2]-a[2];let nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx;const l=Math.hypot(nx,ny,nz)||1;nx/=l;ny/=l;nz/=l;addTri(B,a,b,c,[nx,ny,nz],[nx,ny,nz],[nx,ny,nz],col);}
function flatQuad(B,a,b,c,d,col){flatTri(B,a,b,c,col);flatTri(B,a,c,d,col);}
const _m=new THREE.Matrix4(), _e=new THREE.Euler(), _v=new THREE.Vector3(), _n=new THREE.Vector3(), _nm=new THREE.Matrix3();
function partMatrix(pos,rot,ax){
  const M=new THREE.Matrix4(); M.makeTranslation(pos[0],pos[1],pos[2]);
  if(rot&&(rot[0]||rot[1]||rot[2])){_e.set(rot[0]*Math.PI/180,rot[1]*Math.PI/180,rot[2]*Math.PI/180,'YXZ');M.multiply(_m.makeRotationFromEuler(_e));}
  if(ax==='x') M.multiply(_m.makeRotationZ(-Math.PI/2)); else if(ax==='z') M.multiply(_m.makeRotationX(Math.PI/2));
  return M;
}
function emit(B,M,tri){ // tri: array of [pa,pb,pc,na,nb,nc] in local space
  _nm.getNormalMatrix(M);
  for(const t of tri){const p=[],n=[];for(let k=0;k<3;k++){_v.set(t[k][0],t[k][1],t[k][2]).applyMatrix4(M);p.push([_v.x,_v.y,_v.z]);_n.set(t[3+k][0],t[3+k][1],t[3+k][2]).applyMatrix3(_nm).normalize();n.push([_n.x,_n.y,_n.z]);}
    addTri(B,p[0],p[1],p[2],n[0],n[1],n[2],t.col);}
}
function boxTris(sx,sy,sz,col){
  const x=sx/2,y=sy/2,z=sz/2,out=[]; const P=(a,b,c)=>[a,b,c];
  const f=(a,b,c,d,n)=>{out.push(Object.assign([a,b,c,n,n,n],{col}));out.push(Object.assign([a,c,d,n,n,n],{col}));};
  f([x,-y,-z],[x,y,-z],[x,y,z],[x,-y,z],[1,0,0]); f([-x,-y,z],[-x,y,z],[-x,y,-z],[-x,-y,-z],[-1,0,0]);
  f([-x,y,-z],[-x,y,z],[x,y,z],[x,y,-z],[0,1,0]); f([-x,-y,z],[-x,-y,-z],[x,-y,-z],[x,-y,z],[0,-1,0]);
  f([-x,-y,z],[x,-y,z],[x,y,z],[-x,y,z],[0,0,1]); f([x,-y,-z],[-x,-y,-z],[-x,y,-z],[x,y,-z],[0,0,-1]);
  return out;
}
function cylTris(r0,r1,h,seg,col,caps){
  const out=[]; const sl=(r0-r1)/Math.max(h,1e-6);
  for(let i=0;i<seg;i++){const a0=2*Math.PI*i/seg,a1=2*Math.PI*(i+1)/seg,c0=Math.cos(a0),s0=Math.sin(a0),c1=Math.cos(a1),s1=Math.sin(a1);
    const p00=[r0*c0,0,r0*s0],p01=[r0*c1,0,r0*s1],p10=[r1*c0,h,r1*s0],p11=[r1*c1,h,r1*s1];
    const n0=[c0,sl,s0],n1=[c1,sl,s1];
    out.push(Object.assign([p00,p10,p11,n0,n0,n1],{col}));out.push(Object.assign([p00,p11,p01,n0,n1,n1],{col}));
    if(caps!==false){ if(r1>0) out.push(Object.assign([[0,h,0],p11,p10,[0,1,0],[0,1,0],[0,1,0]],{col})); if(r0>0) out.push(Object.assign([[0,0,0],p00,p01,[0,-1,0],[0,-1,0],[0,-1,0]],{col}));}
  } return out;
}
function sphTris(rx,ry,rz,seg,col){
  const out=[],ns=Math.max(6,seg),nl=Math.max(4,Math.round(seg/2));
  const pt=(i,j)=>{const th=Math.PI*j/nl,ph=2*Math.PI*i/ns;const nx=Math.sin(th)*Math.cos(ph),ny=Math.cos(th),nz=Math.sin(th)*Math.sin(ph);return [[rx*nx,ry*ny,rz*nz],[nx/rx,ny/ry,nz/rz]];};
  for(let j=0;j<nl;j++)for(let i=0;i<ns;i++){const a=pt(i,j),b=pt(i+1,j),c=pt(i+1,j+1),d=pt(i,j+1);
    if(j>0) out.push(Object.assign([a[0],c[0],b[0],a[1],c[1],b[1]],{col})); if(j<nl-1) out.push(Object.assign([a[0],d[0],c[0],a[1],d[1],c[1]],{col}));}
  return out;
}
function torTris(R,r,su,sv,col){
  const out=[]; const pt=(i,j)=>{const u=2*Math.PI*i/su,v=2*Math.PI*j/sv;const cx=Math.cos(u),sx=Math.sin(u),cv=Math.cos(v),sv_=Math.sin(v);return [[(R+r*cv)*cx,r*sv_,(R+r*cv)*sx],[cv*cx,sv_,cv*sx]];};
  for(let i=0;i<su;i++)for(let j=0;j<sv;j++){const a=pt(i,j),b=pt(i+1,j),c=pt(i+1,j+1),d=pt(i,j+1);out.push(Object.assign([a[0],b[0],c[0],a[1],b[1],c[1]],{col}));out.push(Object.assign([a[0],c[0],d[0],a[1],c[1],d[1]],{col}));}
  return out;
}
function extTris(poly,h,col){
  const out=[]; const V=poly.map(p=>new THREE.Vector2(p[0],p[1])); let faces=[]; try{faces=THREE.ShapeUtils.triangulateShape(V,[]);}catch(e){}
  for(const f of faces){const a=poly[f[0]],b=poly[f[1]],c=poly[f[2]];out.push(Object.assign([[a[0],h,a[1]],[b[0],h,b[1]],[c[0],h,c[1]],[0,1,0],[0,1,0],[0,1,0]],{col}));out.push(Object.assign([[c[0],0,c[1]],[b[0],0,b[1]],[a[0],0,a[1]],[0,-1,0],[0,-1,0],[0,-1,0]],{col}));}
  for(let i=0;i<poly.length;i++){const a=poly[i],b=poly[(i+1)%poly.length];const dx=b[0]-a[0],dz=b[1]-a[1],l=Math.hypot(dx,dz)||1;const n=[dz/l,0,-dx/l];
    out.push(Object.assign([[a[0],0,a[1]],[b[0],0,b[1]],[b[0],h,b[1]],n,n,n],{col}));out.push(Object.assign([[a[0],0,a[1]],[b[0],h,b[1]],[a[0],h,a[1]],n,n,n],{col}));}
  return out;
}
const DIM=new Set(['W','D','H','T']);
function buildBufs(sample,vars,classesOut){
  const V=Object.assign({},sample.vars?{}:{},vars);
  if(sample.vars){for(const k of Object.keys(sample.vars)) V[k]=ev(sample.vars[k],V);}
  const bufs={};
  const run=(part,v)=>{
    const m=part.m||'matte'; const B=bufs[m]||(bufs[m]=new Buf());
    const col=hexRGB(part.c||'#c8c8c8'); let tri=null,pos,rot=part.rot?evA(part.rot,v):null;
    switch(part.k){
      case 'box':{let p,s; if(part.a){const a=evA(part.a,v),b=evA(part.b,v);p=[(a[0]+b[0])/2,(a[1]+b[1])/2,(a[2]+b[2])/2];s=[Math.abs(b[0]-a[0]),Math.abs(b[1]-a[1]),Math.abs(b[2]-a[2])];} else {p=evA(part.p,v);s=evA(part.s,v);} if(s[0]<=0||s[1]<=0||s[2]<=0) return; tri=boxTris(s[0],s[1],s[2],col);pos=p;break;}
      case 'cyl':{const p=evA(part.p,v);const r0=ev(part.r0!==undefined?part.r0:part.r,v),r1=part.r1!==undefined?ev(part.r1,v):r0,h=ev(part.h,v); if(h<=0||(r0<=0&&r1<=0)) return; tri=cylTris(r0,r1,h,part.seg||16,col,part.caps);pos=p;break;}
      case 'sph':{const p=evA(part.p,v);const r=part.s?evA(part.s,v):[ev(part.r,v),ev(part.r,v),ev(part.r,v)];tri=sphTris(r[0],r[1],r[2],part.seg||14,col);pos=p;break;}
      case 'tor':{const p=evA(part.p,v);tri=torTris(ev(part.R,v),ev(part.r,v),part.seg||24,part.sv||8,col);pos=p;break;}
      case 'ext':{const poly=part.poly.map(q=>evA(q,v));tri=extTris(poly,ev(part.h,v),col);pos=evA(part.p||[0,0,0],v);break;}
      default: return;
    }
    emit(B,partMatrix(pos,rot,part.ax),tri);
  };
  for(const part of sample.parts){
    const n=part.rep?Math.max(0,Math.round(ev(part.rep.n,V))):1;
    for(let i=0;i<n;i++){
      const v=part.rep?Object.assign({},V,{i}):V;
      const d=part.rep?evA(part.rep.d,v):[0,0,0];
      if(part.rep){ // evaluate with offset: shift placement by i*d
        const pp=Object.assign({},part); const off=[d[0]*i,d[1]*i,d[2]*i];
        const shifted=shiftPart(pp,off,v); run(shifted,v);
        if(part.mx){const m1=mirrorPart(shifted,v,'x');run(m1,v);} if(part.mz){const m2=mirrorPart(shifted,v,'z');run(m2,v);}
      } else { run(part,v); if(part.mx) run(mirrorPart(part,v,'x'),v); if(part.mz) run(mirrorPart(part,v,'z'),v); }
    }
  }
  if(sample.clip){ // finishes / ceilings must stay inside the footprint of the unit they replace
    const hx=ev('W/2',V)+0.01,hz=ev('D/2',V)+0.01;
    for(const B of Object.values(bufs)){const p=B.pos; for(let i=0;i<p.length;i+=3){ if(p[i]>hx)p[i]=hx; else if(p[i]<-hx)p[i]=-hx; if(p[i+2]>hz)p[i+2]=hz; else if(p[i+2]<-hz)p[i+2]=-hz; }}
  }
  return bufs;
}
function shiftPart(p,off,v){const q=Object.assign({},p); const sh=(a)=>a?a.map((x,k)=>`(${typeof x==='number'?x:x})+${off[k]}`):a; if(q.p) q.p=sh(q.p); if(q.a){q.a=sh(q.a);q.b=sh(q.b);} q.rep=null; return q;}
function mirrorPart(p,v,axis){const q=Object.assign({},p); const k=axis==='x'?0:2; const neg=(a)=>a?a.map((x,i)=>i===k?`-(${x})`:x):a; if(q.p) q.p=neg(q.p); if(q.a){q.a=neg(q.a);q.b=neg(q.b);} if(q.poly) q.poly=q.poly.map(pt=>pt.map((x,i)=>i===(axis==='x'?0:1)?`-(${x})`:x)); q.mx=false;q.mz=false;q.rep=null; return q;}

/* ---------- engine ---------- */
class SampleLOD{
  constructor(ctx){
    this.c=ctx; this.lib=window.__SAMPLES__; this.enabled=true; this.active=new Map(); this.units=[]; this.dirty=true; this.lastPos=new THREE.Vector3(1e9,0,0); this.lastT=0; this.entries=new Map(); this.stat={active:0,units:0,types:0};
    if(!this.lib||!this.lib.samples) {this.enabled=false;return;}
    this.root=new THREE.Group(); this.root.renderOrder=5; ctx.scene.add(this.root);
    this.mats={}; const cls=this.lib.classes||{};
    for(const k of Object.keys(cls)){const c=cls[k]; let m;
      if(c.basic) m=new THREE.MeshBasicMaterial({vertexColors:true,side:THREE.DoubleSide});
      else m=new THREE.MeshStandardMaterial({vertexColors:true,roughness:c.rough!==undefined?c.rough:0.8,metalness:c.metal||0,side:THREE.DoubleSide,transparent:c.opacity!==undefined&&c.opacity<1,opacity:c.opacity!==undefined?c.opacity:1,depthWrite:!(c.opacity!==undefined&&c.opacity<1)});
      this.mats[k]=m;}
    this.index();
  }
  ruleFor(e){
    const R=this.rules; for(const r of R){ if(r.c&&r.c!==e.c) continue; if(r.t){ if(r.tp){ if(!(e.t&&e.t.startsWith(r.tp))) continue; } else if(r.t!==e.t) continue; } return r.s; }
    return null;
  }
  index(){
    const M=this.c.M, lib=this.lib; this.rules=lib.map.map(r=>({c:r.c,t:r.t&&r.t.endsWith('*')?null:r.t,tp:r.t&&r.t.endsWith('*')?r.t.slice(0,-1):null,s:r.s}));
    const typeCache=new Map(); const walls=[]; this.wallGrid=new Map();
    const unitsByGrp=new Map(); const types=new Set();
    M.els.forEach((e,ei)=>{
      if((e.c==='A.wall'||e.c==='S.wall'||e.c==='S.col')&&e.g[0]==='r') walls.push({x0:Math.min(e.g[1],e.g[3]),y0:Math.min(e.g[2],e.g[4]),x1:Math.max(e.g[1],e.g[3]),y1:Math.max(e.g[2],e.g[4]),l:e.l});
    });
    walls.forEach(w=>{for(let ix=Math.floor((w.x0-30)/200);ix<=Math.floor((w.x1+30)/200);ix++)for(let iy=Math.floor((w.y0-30)/200);iy<=Math.floor((w.y1+30)/200);iy++){const k=ix+','+iy;(this.wallGrid.get(k)||this.wallGrid.set(k,[]).get(k)).push(w);}});
    M.els.forEach((e,ei)=>{
      const key=e.c+'|'+e.t; let sid=typeCache.get(key); if(sid===undefined){sid=this.ruleFor(e)||null;typeCache.set(key,sid);} if(!sid||!lib.samples[sid]) return;
      const smp=lib.samples[sid]; const pl=smp.place||{}; if(pl.mode==='none') return; const g=e.g; const a=e.a||{};
      if(pl.mode==='group'){
        if(!e.grp) return; const k=sid+'|'+e.grp; let u=unitsByGrp.get(k); if(!u){u={sid,eis:[],bb:[1e9,1e9,1e9,-1e9,-1e9,-1e9],e0:ei,mode:'group',lvl:e.l,a};unitsByGrp.set(k,u);}
        u.eis.push(ei); const bb=this.c.elBB; for(let i=0;i<3;i++){u.bb[i]=Math.min(u.bb[i],bb[ei*6+i]);u.bb[i+3]=Math.max(u.bb[i+3],bb[ei*6+3+i]);}
        return;
      }
      let u=null;
      if(g[0]==='b'&&(pl.mode==='box'||!pl.mode)){u={sid,eis:[ei],mode:'box',x:g[1],y:g[2],W:g[3],D:g[4],ang:g[5],z0:g[6],z1:g[7]};}
      else if(g[0]==='cyl'&&(pl.mode==='cyl'||!pl.mode)){u={sid,eis:[ei],mode:'cyl',x:g[1],y:g[2],W:g[3]*2,D:g[3]*2,ang:0,z0:g[4],z1:g[5]};}
      else if(g[0]==='r'&&(pl.mode==='rect'||!pl.mode)){const dx=Math.abs(g[3]-g[1]),dy=Math.abs(g[4]-g[2]);const horiz=dx>=dy;u={sid,eis:[ei],mode:'rect',x:(g[1]+g[3])/2,y:(g[2]+g[4])/2,W:Math.max(dx,dy),D:Math.min(dx,dy),ang:horiz?0:90,z0:g[5],z1:g[6]};}
      else if(g[0]==='p'&&pl.mode==='prism'){ if((g[4]&&g[4].length)||g[1].length>5) return; const bb=bboxPoly(g[1]); const w=bb[2]-bb[0],d=bb[3]-bb[1]; if(w<=0||d<=0) return; if(polyAreaAbs(g[1])<0.97*w*d) return; const hz=w>=d; u={sid,eis:[ei],mode:'prism',x:(bb[0]+bb[2])/2,y:(bb[1]+bb[3])/2,W:Math.max(w,d),D:Math.min(w,d),ang:hz?0:90,z0:g[2],z1:g[3]};}
      if(!u) return; u.lvl=e.l; u.a=a; this.units.push(u); types.add(sid);
    });
    for(const u of unitsByGrp.values()){
      const smp=lib.samples[u.sid]; const bb=u.bb; // world metres
      const cx=(bb[0]+bb[3])/2/S, cy=-(bb[2]+bb[5])/2/S; const dx=(bb[3]-bb[0])/S, dy=(bb[5]-bb[2])/S; const horiz=dx>=dy;
      u.x=cx;u.y=cy;u.W=Math.max(dx,dy);u.D=Math.min(dx,dy);u.ang=horiz?0:90;u.z0=bb[1];u.z1=bb[4]; this.units.push(u); types.add(u.sid);
    }
    // path units (pipes / ducts): one unit per polyline
    M.els.forEach((e,ei)=>{
      const key=e.c+'|'+e.t; const sid=typeCache.get(key); if(!sid||!lib.samples[sid]) return; const smp=lib.samples[sid]; if(smp.kind!=='path') return;
      const g=e.g; if(g[0]!=='t'&&g[0]!=='d') return; const pts=g[1]; if(pts.length<2) return;
      const vars={}; if(g[0]==='t'){vars.Dp=Math.round(g[2]*10)/10;} else {vars.W=g[2]; vars.H=g[3];}
      this.units.push({sid,eis:[ei],mode:'path',pts,vars,lvl:e.l,a:e.a||{},key:sid+'|'+Object.keys(vars).sort().map(k=>k+vars[k]).join(',')});types.add(sid);
    });
    // finish units: world centre, bbox, radius, orientation for wall mounts, variables
    const bbE=this.c.elBB;
    for(const u of this.units){
      const smp=lib.samples[u.sid]; const pl=smp.place||{}; u.R=((smp.lod&&smp.lod.r)||4.5);
      const bb=[1e9,1e9,1e9,-1e9,-1e9,-1e9]; for(const ei of u.eis){for(let i=0;i<3;i++){bb[i]=Math.min(bb[i],bbE[ei*6+i]);bb[i+3]=Math.max(bb[i+3],bbE[ei*6+3+i]);}} u.bb=bb;
      if(u.mode==='path'){u.cx=(bb[0]+bb[3])/2; u.cz=(bb[2]+bb[5])/2; u.cy=(bb[1]+bb[4])/2; continue;}
      const H=(u.z1-u.z0)*100; u.H=H;
      const anchor=pl.anchor||'bottom'; u.y0=anchor==='top'?u.z1:(anchor==='center'?(u.z0+u.z1)/2:u.z0);
      u.cx=u.x*S; u.cz=-u.y*S; u.cy=(u.z0+u.z1)/2;
      let ang=u.ang;
      if(pl.mount==='wall'){const n=this.hostNormal(u); if(n){ang=Math.atan2(n[0],-n[1])*180/Math.PI;u.n=n;}}
      if(!u.n&&(pl.orient==='side'||pl.mount==='wall')){const sd=(u.a&&u.a.side)||''; const nm={S:[0,-1],N:[0,1],E:[1,0],W:[-1,0]}[sd]; if(nm){ang=Math.atan2(nm[0],-nm[1])*180/Math.PI;u.n=nm;}}
      u.th=ang*Math.PI/180;
      const vars={W:Math.round(u.W*2)/2,D:Math.round(u.D*2)/2,H:Math.round(H*2)/2};
      const a=u.a||{}; if(smp.varmap){for(const k of Object.keys(smp.varmap)){const v=a[smp.varmap[k]];if(typeof v==='number') vars[k]=v;}}
      if(smp.defaults){for(const k of Object.keys(smp.defaults)) if(vars[k]===undefined) vars[k]=smp.defaults[k];}
      u.vars=vars; u.key=u.sid+'|'+Object.keys(vars).sort().map(k=>k+vars[k]).join(',');
    }
    // spatial grid (5 m cells over world x,z): every unit is registered in all cells within R of its bbox, so a query only needs the camera cell
    this.cell=5; this.grid=new Map();
    this.units.forEach((u,i)=>{const R=u.R,bb=u.bb; const ix0=Math.floor((bb[0]-R)/this.cell),ix1=Math.floor((bb[3]+R)/this.cell),iz0=Math.floor((bb[2]-R)/this.cell),iz1=Math.floor((bb[5]+R)/this.cell);
      for(let ix=ix0;ix<=ix1;ix++)for(let iz=iz0;iz<=iz1;iz++){const k=ix+','+iz;(this.grid.get(k)||this.grid.set(k,[]).get(k)).push(i);}});
    this.stat.units=this.units.length; this.stat.types=types.size;
  }
  hostNormal(u){
    // plate mounted on a wall face: find which side of the symbol touches a wall rectangle
    const cand=(u.ang===0)?[[0,-1],[0,1]]:[[-1,0],[1,0]]; const half=u.D/2+0.4;
    let best=null;
    for(const n of cand){const px=u.x-n[0]*half,py=u.y-n[1]*half; const k=Math.floor(px/200)+','+Math.floor(py/200); const L=this.wallGrid.get(k)||[];
      for(const w of L){ if(px>=w.x0-0.6&&px<=w.x1+0.6&&py>=w.y0-0.6&&py<=w.y1+0.6){ best=n; break; } } if(best) break; }
    return best;
  }
  setEnabled(on){this.enabled=!!on; this.dirty=true; if(!on) this.clear();}
  invalidate(){this.dirty=true;}
  clear(){for(const [i,u] of this.active) this.hide(u,false); this.active.clear(); for(const e of this.entries.values()){for(const m of Object.values(e.meshes)) m.count=0;} if(this.pathMeshes) for(const m of Object.values(this.pathMeshes)) m.visible=false; this.c.wake(); this.stat.active=0;}
  hide(u,on){const c=this.c; for(const ei of u.eis){const rg=c.elRange[ei]; const G=c.groups[rg.gk]; if(!G||!G.hideAttr) continue; const arr=G.hideAttr.array; arr.fill(on?1:0,rg.start*3,(rg.start+rg.count)*3); G.hideAttr.needsUpdate=true;}}
  entryFor(u){
    let e=this.entries.get(u.key); if(e) return e;
    const smp=this.lib.samples[u.sid]; const bufs=buildBufs(smp,u.vars); e={geoms:{},meshes:{},cap:0,units:[]};
    for(const cl of Object.keys(bufs)){const B=bufs[cl]; if(!B.pos.length) continue; const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.Float32BufferAttribute(B.pos,3)); g.setAttribute('normal',new THREE.Float32BufferAttribute(B.nrm,3)); g.setAttribute('color',new THREE.Float32BufferAttribute(B.col,3)); g.computeBoundingSphere(); e.geoms[cl]=g;}
    this.entries.set(u.key,e); return e;
  }
  ensureCap(e,n){
    if(n<=e.cap) return; const cap=Math.max(16,Math.pow(2,Math.ceil(Math.log2(n)))); e.cap=cap;
    for(const cl of Object.keys(e.geoms)){ if(e.meshes[cl]){this.root.remove(e.meshes[cl]); e.meshes[cl].dispose&&e.meshes[cl].dispose();}
      const m=new THREE.InstancedMesh(e.geoms[cl],this.mats[cl]||this.mats.matte,cap); m.frustumCulled=false; m.count=0; m.renderOrder=cl==='glass'?7:5; this.root.add(m); e.meshes[cl]=m; }
  }
  update(){
    if(!this.enabled||!this.lib||!this.units.length) return false;
    const c=this.c, cam=c.camera.position, now=performance.now();
    const moved=cam.distanceTo(this.lastPos);
    if(!this.dirty&&moved<0.12&&now-this.lastT<400) return false;
    if(!this.dirty&&now-this.lastT<90) return false;
    this.lastPos.copy(cam); this.lastT=now; this.dirty=false;
    if(c.exploded()||c.liftRunning()){ if(this.active.size) {this.clear(); return true;} return false; }
    const L=this.grid.get(Math.floor(cam.x/this.cell)+','+Math.floor(cam.z/this.cell));
    const cand=[];
    if(L) for(const ui of L){const u=this.units[ui]; const bb=u.bb; const dx=Math.max(bb[0]-cam.x,0,cam.x-bb[3]),dy=Math.max(bb[1]-cam.y,0,cam.y-bb[4]),dz=Math.max(bb[2]-cam.z,0,cam.z-bb[5]); const d2=dx*dx+dy*dy+dz*dz; if(d2>u.R*u.R) continue; cand.push([d2,ui]);}
    cand.sort((a,b)=>a[0]-b[0]);
    const next=new Map(); const MAXU=this.maxUnits||700; let nPath=0;
    for(const [d2,ui] of cand){ if(next.size>=MAXU) break; const u=this.units[ui]; if(u.mode==='path'){ if(nPath>=160) continue; nPath++; } if(this.skipSids&&this.skipSids.has(u.sid)) continue; if(!c.unitVisible(u)) continue; next.set(ui,u); }
    let changed=false, pathChanged=false;
    for(const [ui,u] of this.active){ if(!next.has(ui)){this.hide(u,false);changed=true; if(u.mode==='path') pathChanged=true;} }
    for(const [ui,u] of next){ if(!this.active.has(ui)){this.hide(u,true);changed=true; if(u.mode==='path') pathChanged=true;} }
    this.active=next;
    // instanced objects
    const per=new Map();
    for(const u of next.values()){ if(u.mode==='path') continue; let Lk=per.get(u.key); if(!Lk) per.set(u.key,Lk=[]); Lk.push(u); }
    for(const e of this.entries.values()) for(const m of Object.values(e.meshes)) m.count=0;
    const dm=new THREE.Matrix4(), q=new THREE.Quaternion(), ax=new THREE.Vector3(0,1,0), one=new THREE.Vector3(S,S,S), pos=new THREE.Vector3();
    for(const [key,Lk] of per){
      const e=this.entryFor(Lk[0]); this.ensureCap(e,Lk.length);
      Lk.forEach((u,i)=>{ q.setFromAxisAngle(ax,u.th); pos.set(u.cx,u.y0,u.cz); dm.compose(pos,q,one); for(const cl of Object.keys(e.meshes)) e.meshes[cl].setMatrixAt(i,dm); });
      for(const cl of Object.keys(e.meshes)){e.meshes[cl].count=Lk.length; e.meshes[cl].instanceMatrix.needsUpdate=true;}
    }
    if(pathChanged) this.rebuildPaths();
    this.stat.active=next.size;
    if(changed) c.wake(400);
    return changed;
  }
  rebuildPaths(){
    const merged={}; let n=0;
    for(const u of this.active.values()){ if(u.mode!=='path') continue; if(!u.pb){ try{u.pb=buildPath(this.lib.samples[u.sid],u);}catch(err){console.warn('path sample',u.sid,err.message);u.pb={};} }
      for(const cl of Object.keys(u.pb)){ (merged[cl]||(merged[cl]=[])).push(u.pb[cl]); } n++; }
    if(!this.pathMeshes) this.pathMeshes={};
    for(const cl of Object.keys(this.pathMeshes)){ const m=this.pathMeshes[cl]; m.visible=false; }
    for(const cl of Object.keys(merged)){
      const L=merged[cl]; let tot=0; for(const b of L) tot+=b.pos.length; const pos=new Float32Array(tot),nrm=new Float32Array(tot),col=new Float32Array(tot); let o=0;
      for(const b of L){pos.set(b.pos,o);nrm.set(b.nrm,o);col.set(b.col,o);o+=b.pos.length;}
      let m=this.pathMeshes[cl]; if(!m){ m=new THREE.Mesh(new THREE.BufferGeometry(),this.mats[cl]||this.mats.matte); m.frustumCulled=false; m.renderOrder=cl==='glass'?7:5; this.root.add(m); this.pathMeshes[cl]=m; }
      m.geometry.dispose(); const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.BufferAttribute(pos,3)); g.setAttribute('normal',new THREE.BufferAttribute(nrm,3)); g.setAttribute('color',new THREE.BufferAttribute(col,3)); m.geometry=g; m.visible=true;
    }
    // drop cached geometry of units that are no longer near (keeps memory bounded)
    if(this.units.length>0){ let cached=0; for(const u of this.units) if(u.pb) cached++; if(cached>400){ for(const u of this.units) if(u.pb&&!this.active.has(this.units.indexOf(u))) u.pb=null; } }
  }
}
// ---- path samples (pipes / ducts): the sample is built per segment in a local frame (x along the segment, y up, z across), then placed in the scene (metres)
function buildPath(smp,u){
  const out={}; const pts=u.pts; const base=u.vars; const _m=new THREE.Matrix4(), v=new THREE.Vector3(), nv=new THREE.Vector3(), nm=new THREE.Matrix3();
  const push=(bufs,M)=>{ nm.getNormalMatrix(M); for(const cl of Object.keys(bufs)){ const B=bufs[cl]; const o=out[cl]||(out[cl]={pos:[],nrm:[],col:[]});
      for(let i=0;i<B.pos.length;i+=3){ v.set(B.pos[i],B.pos[i+1],B.pos[i+2]).applyMatrix4(M); o.pos.push(v.x,v.y,v.z); nv.set(B.nrm[i],B.nrm[i+1],B.nrm[i+2]).applyMatrix3(nm).normalize(); o.nrm.push(nv.x,nv.y,nv.z); }
      for(let i=0;i<B.col.length;i++) o.col.push(B.col[i]); } };
  const W3=p=>[p[0]*S,p[2],-p[1]*S];
  const frame=(a,b)=>{ const d=new THREE.Vector3(b[0]-a[0],b[1]-a[1],b[2]-a[2]); const L=d.length(); d.normalize(); let up=new THREE.Vector3(0,1,0); if(Math.abs(d.y)>0.97) up.set(1,0,0); const z=new THREE.Vector3().crossVectors(d,up).normalize(); const y=new THREE.Vector3().crossVectors(z,d).normalize(); return {d,y,z,L}; };
  for(let i=0;i<pts.length-1;i++){
    const a=W3(pts[i]),b=W3(pts[i+1]); const f=frame(a,b); const Lcm=f.L/S; if(Lcm<0.5) continue;
    const vars=Object.assign({},base,{L:Math.round(Lcm*10)/10}); const bufs=buildBufs(smp,vars);
    const M=new THREE.Matrix4().makeBasis(f.d,f.y,f.z); M.setPosition(a[0],a[1],a[2]); M.multiply(new THREE.Matrix4().makeScale(S,S,S)); push(bufs,M);
  }
  if(smp.vparts){ const vs=Object.assign({},smp.vars_v||{}); const tmp={parts:smp.vparts,vars:smp.vars};
    for(let i=1;i<pts.length-1;i++){ const a=W3(pts[i-1]),b=W3(pts[i]); const f=frame(a,b); const bufs=buildBufs(tmp,Object.assign({},base,{L:1})); const M=new THREE.Matrix4().makeBasis(f.d,f.y,f.z); M.setPosition(b[0],b[1],b[2]); M.multiply(new THREE.Matrix4().makeScale(S,S,S)); push(bufs,M); } }
  const res={}; for(const cl of Object.keys(out)){res[cl]={pos:new Float32Array(out[cl].pos),nrm:new Float32Array(out[cl].nrm),col:new Float32Array(out[cl].col)};}
  return res;
}
function polyAreaAbs(p){let a=0;for(let i=0;i<p.length;i++){const q=p[(i+1)%p.length];a+=p[i][0]*q[1]-q[0]*p[i][1];}return Math.abs(a/2);}
function bboxPoly(p){let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;for(const q of p){x0=Math.min(x0,q[0]);y0=Math.min(y0,q[1]);x1=Math.max(x1,q[0]);y1=Math.max(y1,q[1]);}return [x0,y0,x1,y1];}
window.SampleLOD=SampleLOD; window.SampleGeo={buildBufs,compile,ev};
})();
