/* ===== Thumbnails: the model's own DRAWING of a component, rendered once and cached (for the info card and the sample list) =====
   Source of the drawing, in this order: the detailed sample of the library (src/detail.js buildBufs, same dimensions as the element) → the element's own proxy geometry.
   A real photo (window.__PHOTOS__, built from licensed sources only — never from the private site photos) is shown beside it when one exists for the sample id or the type.
   One off-screen WebGL renderer is shared; every picture is a small JPEG data URL kept in memory by (sample, dimensions) or (type, size). */
(function(){
'use strict';
function initThumbs(ctx){
  const {M,THREE,LOD,groups,elRange,elBB,esc}=ctx; const lib=window.__SAMPLES__, SG=window.SampleGeo;
  const W=240,H=170,K=2, SKIP=new Set(['S.slab','S.raft','S.wall','A.wall','A.floor','A.ceil','A.site','A.clad','A.slab','S.pile']);
  let rd=null,cam=null; const cache=new Map();
  function ensure(){ if(rd) return true; try{ rd=new THREE.WebGLRenderer({antialias:true,alpha:false,preserveDrawingBuffer:true}); rd.setPixelRatio(1); rd.setSize(W*K,H*K,false); rd.setClearColor(0xf2f5f9,1); cam=new THREE.PerspectiveCamera(30,W/H,0.01,3000); return true; }catch(e){ rd=null; return false; } }
  function dispose(g){ g.traverse(o=>{ if(o.geometry) o.geometry.dispose(); if(o.userData&&o.userData.own&&o.material) o.material.dispose(); }); }
  function shoot(group){
    if(!ensure()) return null; const sc=new THREE.Scene(); sc.add(new THREE.HemisphereLight(0xffffff,0x8a8f98,0.95)); const d1=new THREE.DirectionalLight(0xffffff,0.85); d1.position.set(3,6,5); sc.add(d1); const d2=new THREE.DirectionalLight(0xffffff,0.3); d2.position.set(-4,-1,-3); sc.add(d2);
    sc.add(group); const box=new THREE.Box3().setFromObject(group); if(box.isEmpty()){ dispose(group); return null; }
    const sph=box.getBoundingSphere(new THREE.Sphere()),dir=new THREE.Vector3(0.62,0.46,0.78).normalize(),dist=sph.radius/Math.sin(THREE.MathUtils.degToRad(cam.fov/2))*1.12;
    cam.position.copy(sph.center).addScaledVector(dir,dist); cam.near=Math.max(0.01,dist-sph.radius*3); cam.far=dist+sph.radius*4; cam.updateProjectionMatrix(); cam.lookAt(sph.center);
    rd.render(sc,cam); const url=rd.domElement.toDataURL('image/jpeg',0.86); sc.remove(group); dispose(group); return url; }
  const edges=(bg,deg)=>{ const m=new THREE.LineBasicMaterial({color:0x2f3a48,transparent:true,opacity:0.5}); const l=new THREE.LineSegments(new THREE.EdgesGeometry(bg,deg),m); l.userData.own=true; return l; };
  function sampleGroup(sid,vars){
    const s=lib.samples[sid],bufs=SG.buildBufs(s,vars),g=new THREE.Group();
    for(const cl of Object.keys(bufs)){ const B=bufs[cl]; if(!B.pos.length) continue; const bg=new THREE.BufferGeometry();
      bg.setAttribute('position',new THREE.Float32BufferAttribute(B.pos,3)); bg.setAttribute('normal',new THREE.Float32BufferAttribute(B.nrm,3)); bg.setAttribute('color',new THREE.Float32BufferAttribute(B.col,3));
      g.add(new THREE.Mesh(bg,LOD.mats[cl]||LOD.mats.matte)); if(cl!=='glass'&&cl!=='ghost') g.add(edges(bg,32)); }
    return g; }
  function geomGroup(ei){
    const rg=elRange[ei]; if(!rg) return null; const G=groups[rg.gk]; if(!G||!G.posArr) return null; const pos=G.posArr.slice(rg.start*9,(rg.start+rg.count)*9); if(!pos.length) return null;
    const bg=new THREE.BufferGeometry(); bg.setAttribute('position',new THREE.BufferAttribute(pos,3)); bg.computeVertexNormals();
    const mb=G.matBase,op=(mb.userData&&mb.userData.baseOpacity)||1,m=new THREE.MeshStandardMaterial({color:new THREE.Color('#D4DADD'),roughness:0.85,metalness:0.05,side:THREE.DoubleSide,transparent:op<0.999,opacity:op});
    const me=new THREE.Mesh(bg,m); me.userData.own=true; const g=new THREE.Group(); g.add(me); g.add(edges(bg,30)); return g; }
  const unitByEl=new Map(); if(LOD&&LOD.units) LOD.units.forEach(u=>{ if(u.eis) u.eis.forEach(e=>{ if(!unitByEl.has(e)) unitByEl.set(e,u); }); });
  const defaultsOf=s=>{ const v=Object.assign({},s.defaults||{},s.dims||{}); if(s.kind==='path'&&v.L===undefined) v.L=120; return v; };
  function forSample(sid){
    if(!lib||!lib.samples[sid]||!SG||!LOD||!LOD.mats) return null; const key='s|'+sid+'|def'; if(cache.has(key)) return cache.get(key);
    let url=null; try{ url=shoot(sampleGroup(sid,defaultsOf(lib.samples[sid]))); }catch(e){ url=null; } cache.set(key,url); return url; }
  function forElement(ei){
    const e=M.els[ei]; if(!e||SKIP.has(e.c)) return null;
    const u=unitByEl.get(ei);
    if(u&&lib&&lib.samples[u.sid]&&SG&&LOD&&LOD.mats){ const key='s|'+(u.key||u.sid); let url=cache.get(key); if(url===undefined){ try{ url=shoot(sampleGroup(u.sid,u.vars||defaultsOf(lib.samples[u.sid]))); }catch(err){ url=null; } cache.set(key,url); }
      if(url) return {url,kind:'sample',sid:u.sid,label:lib.samples[u.sid].name}; }
    const b=elBB.subarray(ei*6,ei*6+6),dx=b[3]-b[0],dy=b[4]-b[1],dz=b[5]-b[2]; if(Math.max(dx,dy,dz)>6.5) return null;
    const key='g|'+e.t+'|'+[dx,dy,dz].map(v=>Math.round(v*100)).join('x')+'|'+(e.m||''); let url=cache.get(key);
    if(url===undefined){ try{ const g=geomGroup(ei); url=g?shoot(g):null; }catch(err){ url=null; } cache.set(key,url); }
    return url?{url,kind:'geometry',sid:null,label:''}:null; }
  /* photos (window.__PHOTOS__, src/photos.json): {u,a,l,s,t} or {r:'other key'} (the same illustrative photo serves a whole family of types) */
  const resolve=p=>{ const P=window.__PHOTOS__; if(!P||!p) return null; if(p.r) p=P[p.r]; return (p&&p.u)?p:null; };
  function photoOfKey(k){ const P=window.__PHOTOS__; return P?resolve(P[k]):null; }
  function photoFor(ei){ const P=window.__PHOTOS__; if(!P) return null; const e=M.els[ei],u=unitByEl.get(ei); return (u&&resolve(P[u.sid]))||resolve(P[e.t])||null; }
  const credit=p=>'صورة واقعية توضيحية لمنتج مماثل — ليست من الموقع'+(p.a?' · '+esc(p.a):'')+(p.l?' · '+esc(p.l):'')+(p.s?' · <a href="'+esc(p.s)+'" target="_blank" rel="noopener">المصدر (ويكيميديا كومنز)</a>':'');
  function photoFigure(p){ return '<figure><img src="'+esc(p.u)+'" alt="صورة واقعية توضيحية" loading="lazy"><figcaption>'+credit(p)+'</figcaption></figure>'; }
  function fill(el,ei){
    if(!el) return;
    setTimeout(()=>{ if(!el.isConnected) return; const d=forElement(ei),p=photoFor(ei); if(!d&&!p) return; let h='<div class="ith-row">';
      if(d) h+='<figure><img src="'+d.url+'" alt="رسم المكوّن" width="'+W+'" height="'+H+'"><figcaption>رسم النموذج'+(d.kind==='sample'?' — عينة «'+esc(d.label)+'»':' — هندسة العنصر في النموذج')+'</figcaption></figure>';
      if(p) h+=photoFigure(p);
      el.innerHTML=h+'</div>'; el.hidden=false; },0); }
  /* sample list: every <img data-sid> is drawn when it scrolls into view (one at a time, so the panel never stalls) */
  let io=null,q=[],busy=false;
  function pump(){ if(busy) return; busy=true; const step=()=>{ const img=q.shift(); if(!img){ busy=false; return; } if(img.isConnected&&!img.src){ const u=forSample(img.dataset.sid); if(u) img.src=u; } (window.requestAnimationFrame||setTimeout)(step); }; step(); }
  function attach(root){
    if(!root) return; const imgs=root.querySelectorAll('img.sthumb[data-sid]'); if(!imgs.length) return;
    if(!('IntersectionObserver' in window)){ imgs.forEach(i=>q.push(i)); pump(); return; }
    if(!io) io=new IntersectionObserver(es=>{ es.forEach(en=>{ if(en.isIntersecting){ io.unobserve(en.target); q.push(en.target); } }); pump(); },{rootMargin:'120px'});
    imgs.forEach(i=>io.observe(i)); }
  return {forElement,forSample,photoFor,photoOfKey,photoFigure,fill,attach,get cached(){return cache.size;}};
}
window.initThumbs=initThumbs;
})();
