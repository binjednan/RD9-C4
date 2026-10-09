/* ===== BIM-lite engine for C4 model (cm plan units, metres elevation) ===== */
const S=0.01;
const V3=THREE.Vector3;
function triNormal(a,b,c){const ux=b[0]-a[0],uy=b[1]-a[1],uz=b[2]-a[2],vx=c[0]-a[0],vy=c[1]-a[1],vz=c[2]-a[2];let nx=uy*vz-uz*vy,ny=uz*vx-ux*vz,nz=ux*vy-uy*vx;const l=Math.hypot(nx,ny,nz)||1;return [nx/l,ny/l,nz/l];}
// world mapping: plan (x,y cm), z m -> three (x*S, z, -y*S)
function W(x,y,z){return [x*S,z,-y*S];}

class Group{
  constructor(key,cl){this.key=key;this.pos=[];this.nrm=[];this.unit=[];this.mat=[];this.clip=[];this.cl=cl||0;this.n=0;}
  tri(a,b,c,u1,u2,mi){const n=triNormal(a,b,c);for(const p of [a,b,c]){this.pos.push(p[0],p[1],p[2]);this.nrm.push(n[0],n[1],n[2]);this.unit.push(u1,u2);this.mat.push(mi);this.clip.push(this.cl);}this.n++;}
  quad(a,b,c,d,u1,u2,mi){this.tri(a,b,c,u1,u2,mi);this.tri(a,c,d,u1,u2,mi);}
}
// Indexed source surfaces: plan coordinates are cm, elevation is m. Preserve
// the supplied faces and winding; do not infer thickness, caps or extra faces.
function indexedMesh(g,vertices,faces,u1,u2,mi){
  if(!Array.isArray(vertices)||!vertices.length||!Array.isArray(faces)||!faces.length) throw new Error('mesh requires vertices and triangle faces');
  const pts=vertices.map((p,i)=>{
    if(!Array.isArray(p)||p.length!==3||!p.every(Number.isFinite)) throw new Error('mesh invalid vertex '+i);
    return W(p[0],p[1],p[2]);
  });
  // Validate the whole primitive before emitting any part of it.
  faces.forEach((f,i)=>{
    if(!Array.isArray(f)||f.length!==3||!f.every(j=>Number.isInteger(j)&&j>=0&&j<pts.length)||new Set(f).size!==3) throw new Error('mesh invalid face '+i);
    const a=pts[f[0]],b=pts[f[1]],c=pts[f[2]],ux=b[0]-a[0],uy=b[1]-a[1],uz=b[2]-a[2],vx=c[0]-a[0],vy=c[1]-a[1],vz=c[2]-a[2];
    const area2=Math.hypot(uy*vz-uz*vy,uz*vx-ux*vz,ux*vy-uy*vx);
    if(!Number.isFinite(area2)||area2===0) throw new Error('mesh degenerate face '+i);
  });
  const n0=g.n;
  faces.forEach(f=>g.tri(pts[f[0]],pts[f[1]],pts[f[2]],u1,u2,mi));
  return g.n-n0;
}
function polyArea(p){let a=0;for(let i=0;i<p.length;i++){const q=p[(i+1)%p.length];a+=p[i][0]*q[1]-q[0]*p[i][1];}return a/2;}
function dedupe(p){const o=[];for(const q of p){const l=o[o.length-1];if(!l||Math.abs(l[0]-q[0])>0.05||Math.abs(l[1]-q[1])>0.05)o.push(q);}if(o.length>2){const a=o[0],b=o[o.length-1];if(Math.abs(a[0]-b[0])<=0.05&&Math.abs(a[1]-b[1])<=0.05)o.pop();}return o;}
function prism(g,poly,holes,z0,z1,u1,u2,mi){
  poly=dedupe(poly); if(poly.length<3) return 0;
  holes=(holes||[]).map(dedupe).filter(h=>h.length>=3);
  const n0=g.n;
  // orient: outer CCW, holes CW (in plan coords)
  let outer=poly.slice(); if(polyArea(outer)<0) outer.reverse();
  const hs=holes.map(h=>{h=h.slice(); if(polyArea(h)>0) h.reverse(); return h;});
  const V2=outer.map(p=>new THREE.Vector2(p[0],p[1])); const H2=hs.map(h=>h.map(p=>new THREE.Vector2(p[0],p[1])));
  let faces; try{faces=THREE.ShapeUtils.triangulateShape(V2,H2);}catch(e){faces=[];}
  const all=outer.concat(...hs);
  // top & bottom caps
  for(const f of faces){
    const a=all[f[0]],b=all[f[1]],c=all[f[2]];
    // plan is CCW when viewed from +z (up). three: y up, z=-y => orientation preserved? handle by emitting both then DoubleSide ok
    g.tri(W(a[0],a[1],z1),W(b[0],b[1],z1),W(c[0],c[1],z1),u1,u2,mi);
    g.tri(W(c[0],c[1],z0),W(b[0],b[1],z0),W(a[0],a[1],z0),u1,u2,mi);
  }
  const ring=(r)=>{for(let i=0;i<r.length;i++){const a=r[i],b=r[(i+1)%r.length];g.quad(W(a[0],a[1],z0),W(b[0],b[1],z0),W(b[0],b[1],z1),W(a[0],a[1],z1),u1,u2,mi);}};
  ring(outer); hs.forEach(ring);
  return g.n-n0;
}
function rectPrism(g,x0,y0,x1,y1,z0,z1,u1,u2,mi){return prism(g,[[x0,y0],[x1,y0],[x1,y1],[x0,y1]],null,z0,z1,u1,u2,mi);}
function cylinder(g,cx,cy,r,z0,z1,u1,u2,mi,seg=14){const pts=[];for(let i=0;i<seg;i++){const a=2*Math.PI*i/seg;pts.push([cx+r*Math.cos(a),cy+r*Math.sin(a)]);}return prism(g,pts,null,z0,z1,u1,u2,mi);}

/* ---- additional primitives ---- */
function orientedBox(g,cx,cy,w,d,rotDeg,z0,z1,u1,u2,mi){
  const a=rotDeg*Math.PI/180,c=Math.cos(a),s=Math.sin(a),hw=w/2,hd=d/2;
  const pts=[[-hw,-hd],[hw,-hd],[hw,hd],[-hw,hd]].map(p=>[cx+p[0]*c-p[1]*s,cy+p[0]*s+p[1]*c]);
  return prism(g,pts,null,z0,z1,u1,u2,mi);
}
// box between two 3D points (cm plan, m z) with cross-section (w cm across plan, h cm vertical) -- duct segment
function ductSeg(g,p,q,w,h,u1,u2,mi){
  const n0=g.n;
  const dx=q[0]-p[0],dy=q[1]-p[1]; const L=Math.hypot(dx,dy,(q[2]-p[2])*100);
  if(L<0.5) return 0;
  const lx=dx/Math.hypot(dx,dy||1e-9), ly=dy/Math.hypot(dx,dy||1e-9); // plan dir
  const nx=-ly,ny=lx; const hw=w/2, hh=h/200;
  const P=(pt,sw,sh)=>W(pt[0]+nx*hw*sw,pt[1]+ny*hw*sw,pt[2]+hh*sh);
  const c=[[1,1],[-1,1],[-1,-1],[1,-1]];
  const A=c.map(k=>P(p,k[0],k[1])), B=c.map(k=>P(q,k[0],k[1]));
  for(let i=0;i<4;i++){const j=(i+1)%4; g.quad(A[i],A[j],B[j],B[i],u1,u2,mi);}
  g.quad(A[3],A[2],A[1],A[0],u1,u2,mi); g.quad(B[0],B[1],B[2],B[3],u1,u2,mi);
  return g.n-n0;
}
function tubeSeg(g,p,q,r,u1,u2,mi,seg=8){
  const n0=g.n;
  const a=W(p[0],p[1],p[2]), b=W(q[0],q[1],q[2]);
  const ax=[b[0]-a[0],b[1]-a[1],b[2]-a[2]]; const L=Math.hypot(...ax); if(L<0.002) return 0;
  const d=[ax[0]/L,ax[1]/L,ax[2]/L];
  let up=Math.abs(d[1])>0.9?[1,0,0]:[0,1,0];
  let n1=[d[1]*up[2]-d[2]*up[1],d[2]*up[0]-d[0]*up[2],d[0]*up[1]-d[1]*up[0]]; let l1=Math.hypot(...n1); n1=n1.map(v=>v/l1);
  const n2=[d[1]*n1[2]-d[2]*n1[1],d[2]*n1[0]-d[0]*n1[2],d[0]*n1[1]-d[1]*n1[0]];
  const rr=r*S; const ring=(c)=>{const o=[];for(let i=0;i<seg;i++){const t=2*Math.PI*i/seg;o.push([c[0]+rr*(Math.cos(t)*n1[0]+Math.sin(t)*n2[0]),c[1]+rr*(Math.cos(t)*n1[1]+Math.sin(t)*n2[1]),c[2]+rr*(Math.cos(t)*n1[2]+Math.sin(t)*n2[2])]);}return o;};
  const A=ring(a),B=ring(b);
  for(let i=0;i<seg;i++){const j=(i+1)%seg;g.quad(A[i],A[j],B[j],B[i],u1,u2,mi);}
  return g.n-n0;
}

/* ---- curtain: pleated vertical sheet along the plan segment (x0,y0)->(x1,y1) (cm), z0..z1 (m); `folds` pleats of amplitude `amp` (cm) across the segment ---- */
function curtain(g,x0,y0,x1,y1,z0,z1,folds,amp,u1,u2,mi){
  const n0=g.n; const dx=x1-x0,dy=y1-y0,L=Math.hypot(dx,dy); if(L<5) return 0; const nx=-dy/L,ny=dx/L; const N=Math.max(6,Math.round(folds*6));
  for(let i=0;i<N;i++){const t0=i/N,t1=(i+1)/N,o0=amp*Math.sin(2*Math.PI*folds*t0),o1=amp*Math.sin(2*Math.PI*folds*t1);
    const px0=x0+dx*t0+nx*o0,py0=y0+dy*t0+ny*o0,px1=x0+dx*t1+nx*o1,py1=y0+dy*t1+ny*o1;
    g.quad(W(px0,py0,z0),W(px1,py1,z0),W(px1,py1,z1),W(px0,py0,z1),u1,u2,mi);}
  return g.n-n0;
}

/* ---- leaf cloud: `count` small leaf quads scattered on an ellipsoid shell (horizontal radius rx cm, z0..z1 m, inner radius fraction `inner`), deterministic by `seed` -- tree crowns, shrubs, flower clusters ---- */
function leafCloud(g,cx,cy,rx,z0,z1,count,size,seed,u1,u2,mi,inner){
  const n0=g.n; let s=(seed>>>0)||1;
  const rnd=()=>{s=(s+0x6D2B79F5)>>>0; let t=s; t=Math.imul(t^(t>>>15),t|1); t^=t+Math.imul(t^(t>>>7),t|61); return ((t^(t>>>14))>>>0)/4294967296;};
  const zc=(z0+z1)*50, rz=(z1-z0)*50, f0=(inner===undefined?0.6:inner);
  for(let i=0;i<count;i++){
    const u=rnd()*2-1, ph=rnd()*6.2831853, r=Math.sqrt(1-u*u), dx=r*Math.cos(ph), dy=r*Math.sin(ph), dz=u;
    const f=f0+(1-f0)*Math.pow(rnd(),0.5), p=[cx+dx*rx*f, cy+dy*rx*f, zc+dz*rz*f];
    let nx=dx+(rnd()-0.5), ny=dy+(rnd()-0.5), nz=dz+(rnd()-0.5); const nl=Math.hypot(nx,ny,nz)||1; nx/=nl; ny/=nl; nz/=nl;
    const flat=Math.abs(nz)<0.9, ax=flat?0:1, az=flat?1:0;
    let t1=[ny*az, nz*ax-nx*az, -ny*ax]; const l1=Math.hypot(t1[0],t1[1],t1[2])||1; t1=[t1[0]/l1,t1[1]/l1,t1[2]/l1];
    const t2=[ny*t1[2]-nz*t1[1], nz*t1[0]-nx*t1[2], nx*t1[1]-ny*t1[0]];
    const al=rnd()*6.2831853, ca=Math.cos(al), sa=Math.sin(al);
    const a1=[t1[0]*ca+t2[0]*sa, t1[1]*ca+t2[1]*sa, t1[2]*ca+t2[2]*sa], a2=[-t1[0]*sa+t2[0]*ca, -t1[1]*sa+t2[1]*ca, -t1[2]*sa+t2[2]*ca];
    const L=size*(0.7+0.6*rnd()), h1=L/2, h2=L*0.30;
    const V=(k1,k2)=>W(p[0]+a1[0]*k1+a2[0]*k2, p[1]+a1[1]*k1+a2[1]*k2, (p[2]+a1[2]*k1+a2[2]*k2)/100);
    g.quad(V(h1,0),V(0,h2),V(-h1,0),V(0,-h2),u1,u2,mi);
  }
  return g.n-n0;
}

/* ---- landscape / canopy primitives ---- */
// vertical ellipsoid: circular in plan (radius r cm), from z0 to z1 (m) -- tree canopies, shrubs, small plants
function ellipsoid(g,cx,cy,r,z0,z1,u1,u2,mi,seg=8,rings=5){
  const n0=g.n; const zc=(z0+z1)/2, hz=(z1-z0)/2;
  const P=(i,j)=>{const th=Math.PI*i/rings, ph=2*Math.PI*j/seg; return W(cx+r*Math.sin(th)*Math.cos(ph),cy+r*Math.sin(th)*Math.sin(ph),zc+hz*Math.cos(th));};
  for(let i=0;i<rings;i++)for(let j=0;j<seg;j++){
    const a=P(i,j),b=P(i,j+1),c=P(i+1,j+1),d=P(i+1,j);
    if(i===0) g.tri(a,c,d,u1,u2,mi); else if(i===rings-1) g.tri(a,b,c,u1,u2,mi); else g.quad(a,b,c,d,u1,u2,mi);
  }
  return g.n-n0;
}
// triangle in space with thickness (cm) -- shade sails, hip-roof panels.  pts = [[x,y,z],[x,y,z],[x,y,z]] (cm plan, m height)
function triPlane(g,pts,thickCm,u1,u2,mi){
  const n0=g.n; const A=pts.map(p=>W(p[0],p[1],p[2])); const n=triNormal(A[0],A[1],A[2]); const h=(thickCm||1)*S/2;
  const T=(k)=>A.map(p=>[p[0]+n[0]*h*k,p[1]+n[1]*h*k,p[2]+n[2]*h*k]);
  const U=T(1),D=T(-1);
  g.tri(U[0],U[1],U[2],u1,u2,mi); g.tri(D[2],D[1],D[0],u1,u2,mi);
  for(let i=0;i<3;i++){const j=(i+1)%3; g.quad(D[i],D[j],U[j],U[i],u1,u2,mi);}
  return g.n-n0;
}
// sloped strip along centreline [[x,y,z_top]...] width cm, thickness m
function rampStrip(g,pts,width,thick,u1,u2,mi){
  const n0=g.n; const hw=width/2;
  const L=[],Rr=[];
  for(let i=0;i<pts.length;i++){
    const a=pts[Math.max(0,i-1)],b=pts[Math.min(pts.length-1,i+1)];
    let dx=b[0]-a[0],dy=b[1]-a[1]; const l=Math.hypot(dx,dy)||1; dx/=l;dy/=l;
    L.push([pts[i][0]-dy*hw,pts[i][1]+dx*hw,pts[i][2]]); Rr.push([pts[i][0]+dy*hw,pts[i][1]-dx*hw,pts[i][2]]);
  }
  for(let i=0;i<pts.length-1;i++){
    const a=L[i],b=Rr[i],c=Rr[i+1],d=L[i+1];
    g.quad(W(a[0],a[1],a[2]),W(b[0],b[1],b[2]),W(c[0],c[1],c[2]),W(d[0],d[1],d[2]),u1,u2,mi);
    g.quad(W(d[0],d[1],d[2]-thick),W(c[0],c[1],c[2]-thick),W(b[0],b[1],b[2]-thick),W(a[0],a[1],a[2]-thick),u1,u2,mi);
    g.quad(W(a[0],a[1],a[2]-thick),W(a[0],a[1],a[2]),W(d[0],d[1],d[2]),W(d[0],d[1],d[2]-thick),u1,u2,mi);
    g.quad(W(b[0],b[1],b[2]),W(b[0],b[1],b[2]-thick),W(c[0],c[1],c[2]-thick),W(c[0],c[1],c[2]),u1,u2,mi);
  }
  return g.n-n0;
}
