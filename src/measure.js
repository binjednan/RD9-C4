/* ===== Measure tool (2026-10-08, roadmap item of docs/HANDOFF_2026-10-07.md §5) =====
   Researched practice (Autodesk Viewer, xeokit DistanceMeasurements, Navisworks): two-point distance with a snap that prefers a real corner of the geometry under the pointer, the horizontal / vertical
   components next to the straight distance, measurements that stay until cleared, one key to enter / leave the mode, Esc cancels the pending point.
   Here: «القياس (M)» in the «⋯» menu or the key M. The pointer ray is the viewer's own picker (src/app.js pickHit), which now also returns the hit triangle; the point snaps to the nearest corner of that
   triangle within 16 px (26 px on touch), otherwise it is the exact point on the surface. Diagonals of the triangulation are never snapped to (they are not edges of the building).
   Each measurement = line + end points in 3-D (drawn on top) and a label «المسافة · أفقي · رأسي» that follows it; the panel lists them with copy / delete. Distances are metres (centimetres below 1 m).
   Nothing is stored (a measurement describes what is on screen). ES2018 style. */
(function(){
'use strict';
function initMeasure(ctx){
  const {THREE,scene,camera,renderer,$,pickHit,wake,toast,esc}=ctx;
  let on=false,A=null,hover=null; const list=[]; const v=new THREE.Vector3();
  const G=new THREE.Group(); G.renderOrder=1010; scene.add(G);
  const view=$('view'); const host=document.createElement('div'); host.id='msLabels'; view.appendChild(host);
  const snapEl=document.createElement('div'); snapEl.id='msSnap'; snapEl.hidden=true; view.appendChild(snapEl);
  const bar=document.createElement('div'); bar.id='msBar'; bar.hidden=true; view.appendChild(bar);
  const fmt=m=>m>=1?m.toFixed(2)+' م':Math.round(m*100)+' سم';
  const comp=(a,b)=>{ const dx=b[0]-a[0],dy=b[1]-a[1],dz=b[2]-a[2]; return {d:Math.hypot(dx,dy,dz),hz:Math.hypot(dx,dz),vt:Math.abs(dy),dx:Math.abs(dx),dy:Math.abs(dz)}; };
  const lblHTML=c=>'<b>'+esc(fmt(c.d))+'</b><small>أفقي '+esc(fmt(c.hz))+' · رأسي '+esc(fmt(c.vt))+'</small>';
  const textOf=(a,b,i)=>{ const c=comp(a,b); return 'قياس '+(i+1)+': المسافة '+fmt(c.d)+' · أفقي '+fmt(c.hz)+' · رأسي '+fmt(c.vt)+' · الفرق على المحور X '+fmt(c.dx)+' وY '+fmt(c.dy); };
  const toScr=p=>{ const r=renderer.domElement.getBoundingClientRect(); v.set(p[0],p[1],p[2]).project(camera); return [r.left+(v.x+1)/2*r.width,r.top+(1-v.y)/2*r.height,v.z]; };

  /* ---------------- snapping ---------------- */
  function snap(cx,cy){
    const h=pickHit(cx,cy); if(!h) return null; const coarse=window.matchMedia&&matchMedia('(pointer:coarse)').matches,rv=coarse?26:16; let best=null,bd=1e9;
    (h.tri||[]).forEach(p=>{ const s=toScr(p),d=Math.hypot(s[0]-cx,s[1]-cy); if(d<rv&&d<bd){ bd=d; best={p:[p[0],p[1],p[2]],kind:'v'}; } });
    return best||{p:[h.pt.x,h.pt.y,h.pt.z],kind:'s'}; }

  /* ---------------- drawing ---------------- */
  const lineMat=new THREE.LineBasicMaterial({color:0xd6336c,depthTest:false,transparent:true}), ptMat=new THREE.PointsMaterial({color:0xd6336c,size:9,sizeAttenuation:false,depthTest:false,transparent:true});
  const rubMat=new THREE.LineDashedMaterial({color:0xd6336c,dashSize:0.14,gapSize:0.09,depthTest:false,transparent:true,opacity:0.8});
  let rubber=null;
  function clearG(){ for(let i=G.children.length-1;i>=0;i--){ const o=G.children[i]; G.remove(o); if(o.geometry) o.geometry.dispose(); } rubber=null; }
  function rebuild(){
    clearG(); const pts=[];
    list.forEach(m=>{ const g=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(m.a[0],m.a[1],m.a[2]),new THREE.Vector3(m.b[0],m.b[1],m.b[2])]); const l=new THREE.Line(g,lineMat); l.renderOrder=1010; l.frustumCulled=false; G.add(l); pts.push(m.a,m.b); });
    if(A) pts.push(A);
    if(pts.length){ const arr=new Float32Array(pts.length*3); pts.forEach((p,i)=>{ arr[i*3]=p[0]; arr[i*3+1]=p[1]; arr[i*3+2]=p[2]; }); const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.BufferAttribute(arr,3)); const P=new THREE.Points(g,ptMat); P.renderOrder=1011; P.frustumCulled=false; G.add(P); }
    host.innerHTML=''; list.forEach((m,i)=>{ const d=document.createElement('div'); d.className='ms-lbl'; d.dataset.i=i; d.innerHTML=lblHTML(comp(m.a,m.b)); host.appendChild(d); });
    panel(); wake(); }
  function drawRubber(p){
    if(rubber){ G.remove(rubber); rubber.geometry.dispose(); rubber=null; } if(!A||!p) return;
    const g=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(A[0],A[1],A[2]),new THREE.Vector3(p[0],p[1],p[2])]); rubber=new THREE.Line(g,rubMat); rubber.computeLineDistances(); rubber.renderOrder=1010; rubber.frustumCulled=false; G.add(rubber); wake(); }

  /* ---------------- panel ---------------- */
  function panel(){
    bar.hidden=!on; if(!on) return;
    let h='<div class="ms-h"><b>📏 القياس</b><span class="ms-hint">'+(A?'انقر النقطة الثانية (Esc للإلغاء)':'انقر النقطة الأولى — تلتصق بأقرب ركن')+'</span><button type="button" data-ms="end" class="mini" title="إنهاء القياس (M)">إنهاء</button></div>';
    if(list.length){ h+='<div class="ms-l">'+list.map((m,i)=>'<div class="ms-r"><span>'+esc(textOf(m.a,m.b,i))+'</span><button type="button" class="mini" data-ms="copy" data-i="'+i+'">نسخ</button><button type="button" class="mini" data-ms="del" data-i="'+i+'">حذف</button></div>').join('')+'</div><div class="ms-f"><button type="button" class="mini" data-ms="copyall">نسخ الكل</button><button type="button" class="mini" data-ms="clear">مسح الكل</button></div>'; }
    bar.innerHTML=h; }
  function copyText(t){ const ok=()=>toast('نُسخ القياس',1800); if(navigator.clipboard&&window.isSecureContext) navigator.clipboard.writeText(t).then(ok,()=>fb(t)); else fb(t);
    function fb(s){ try{ const ta=document.createElement('textarea'); ta.value=s; ta.style.cssText='position:fixed;opacity:0'; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); ok(); }catch(e){ toast('تعذّر النسخ'); } } }
  bar.addEventListener('click',ev=>{ const b=ev.target.closest('[data-ms]'); if(!b) return; ev.stopPropagation(); const a=b.dataset.ms,i=+b.dataset.i;
    if(a==='end') set(false); else if(a==='clear'){ list.length=0; A=null; rebuild(); } else if(a==='del'){ list.splice(i,1); rebuild(); }
    else if(a==='copy') copyText(textOf(list[i].a,list[i].b,i)); else if(a==='copyall') copyText(list.map((m,k)=>textOf(m.a,m.b,k)).join('\n')); });

  /* ---------------- mode ---------------- */
  function set(x){ on=!!x; A=null; hover=null; snapEl.hidden=true; document.body.classList.toggle('measuring',on); const bt=$('btnMeasure'); if(bt) bt.classList.toggle('on',on); rebuild(); if(on) toast('القياس: انقر نقطتين على المجسم — تلتصق النقطة بأقرب ركن',3200); }
  let mvT=0; renderer.domElement.addEventListener('pointermove',ev=>{ if(!on||ev.pointerType==='touch') return; const now=performance.now(); if(now-mvT<45) return; mvT=now;
    if(ev.buttons) { snapEl.hidden=true; return; } const s=snap(ev.clientX,ev.clientY); hover=s;
    if(!s){ snapEl.hidden=true; drawRubber(null); return; } const sc=toScr(s.p),vr=view.getBoundingClientRect(); snapEl.hidden=false; snapEl.className='ms-snap '+s.kind; snapEl.style.left=(sc[0]-vr.left)+'px'; snapEl.style.top=(sc[1]-vr.top)+'px'; drawRubber(s.p); });
  function tap(cx,cy){
    if(!on) return false; const s=snap(cx,cy); if(!s){ toast('لا سطح تحت هذه النقطة — انقر على المبنى',2200); return true; }
    if(!A){ A=s.p; } else { list.push({a:A,b:s.p}); A=null; hover=null; snapEl.hidden=true; toast('القياس '+list.length+': '+fmt(comp(list[list.length-1].a,list[list.length-1].b).d),2600); }
    rebuild(); return true; }
  function frame(){
    if(!list.length&&!A) return; const vr=view.getBoundingClientRect(); const labels=host.children;
    for(let i=0;i<list.length;i++){ const m=list[i],mid=[(m.a[0]+m.b[0])/2,(m.a[1]+m.b[1])/2,(m.a[2]+m.b[2])/2],s=toScr(mid),d=labels[i]; if(!d) continue;
      if(s[2]>1||s[2]<-1){ d.style.display='none'; continue; } d.style.display='block'; d.style.left=Math.round(s[0]-vr.left)+'px'; d.style.top=Math.round(s[1]-vr.top)+'px'; } }
  function escape(){ if(A){ A=null; hover=null; snapEl.hidden=true; drawRubber(null); rebuild(); return true; } if(on){ set(false); return true; } return false; }
  window.addEventListener('keydown',ev=>{ if(ev.ctrlKey||ev.metaKey||ev.altKey||ev.code!=='KeyM') return; const t=ev.target;
    if(t&&((t.tagName==='INPUT'&&t.type!=='range'&&t.type!=='checkbox')||t.tagName==='TEXTAREA'||t.tagName==='SELECT'||t.isContentEditable)) return; ev.preventDefault(); set(!on); });
  const mb=$('btnMeasure'); if(mb) mb.onclick=()=>{ set(!on); };
  return {tap,frame,esc:escape,set,get active(){ return on; },get count(){ return list.length; },
    state(){ return {on,pending:!!A,count:list.length,list:list.map(m=>comp(m.a,m.b))}; },
    add(a,b){ list.push({a,b}); rebuild(); }};
}
window.initMeasure=initMeasure;
})();
