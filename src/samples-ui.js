/* ===== samples catalog tab + stand-alone preview =====
   Lists every sample of src/samples.json (grouped by discipline), previews it on its own (drag = rotate, wheel = zoom, dimension fields rebuild it),
   and can fly the main camera to the nearest place in the building where that sample is used (the level-of-detail engine then shows it in place). */
(function(){
'use strict';
function initSamplesUI(ctx){
  const {M,THREE,$,esc,LOD,flyTo,wake,toast,ensureVisible,camera,setGhost,elBB}=ctx; const bbAll=elBB;
  const lib=window.__SAMPLES__; const pane=$('pSamp'); if(!lib||!pane||!LOD){ if(pane) pane.innerHTML='<div class=muted>مكتبة العينات غير محمّلة.</div>'; return; }
  const CATN={architecture:'العمارة',electrical:'الكهرباء',mechanical:'الميكانيكا (تكييف وتهوية)',plumbing:'السباكة والصرف',fire:'الإطفاء',structure:'الإنشائي'};
  const CONFN={doc:['من المستندات','#1a7f37'],derived:['مشتق من المستندات','#9a6700'],assumed:['افتراض — يحتاج تأكيد','#cf222e']};
  // instances per sample (units + catalog-only mapped types)
  const cnt={}; LOD.units.forEach(u=>cnt[u.sid]=(cnt[u.sid]||0)+1);
  const typeCnt={}; const rules=lib.map; M.els.forEach(e=>{ for(const r of rules){ if(r.c&&r.c!==e.c) continue; if(r.t){ if(r.t.endsWith('*')){ if(!(e.t&&e.t.startsWith(r.t.slice(0,-1)))) continue; } else if(r.t!==e.t) continue; } typeCnt[r.s]=(typeCnt[r.s]||0)+1; break; } });
  let q='';
  function listHTML(){
    const ids=Object.keys(lib.samples).filter(id=>{const s=lib.samples[id]; if(!q) return true; const t=(id+' '+s.name+' '+(s.en||'')).toLowerCase(); return q.split(/\s+/).every(w=>t.includes(w));});
    const by={}; ids.forEach(id=>(by[lib.samples[id].cat]=by[lib.samples[id].cat]||[]).push(id));
    let h=`<div class="note">${esc(lib.note||'')}</div><div class="muted">${ids.length} عينة من ${Object.keys(lib.samples).length} — انقر عينة لمعاينتها منفردة، ومنها «اذهب إلى موضعها في المبنى».</div>`;
    for(const c of Object.keys(CATN)){ const arr=by[c]; if(!arr) continue; h+=`<details open><summary><b>${CATN[c]}</b> (${arr.length})</summary>`+arr.sort().map(id=>{const s=lib.samples[id]; const cf=CONFN[s.conf]||['',''];
        return `<div class="res" data-s="${esc(id)}"><b>${esc(s.name)}</b><small><code>${esc(id)}</code> • <span style="color:${cf[1]}">${cf[0]}</span> • ${typeCnt[id]?typeCnt[id]+' عنصر في النموذج':'كتالوج فقط'}${s.place&&s.place.mode==='none'?' (لا استبدال تلقائي)':''}</small></div>`;}).join('')+`</details>`; }
    return h; }
  pane.innerHTML=`<input id="smpQ" type="search" placeholder="ابحث في العينات (اسم، معرّف، نوع)…" autocomplete="off"><div id="smpList"></div>`;
  const render=()=>{$('smpList').innerHTML=listHTML();}; render();
  $('smpQ').oninput=ev=>{q=ev.target.value.trim().toLowerCase(); render();};
  $('smpList').onclick=ev=>{const r=ev.target.closest('.res[data-s]'); if(r) openPreview(r.dataset.s);};
  /* ---------- preview ---------- */
  const dlg=$('smpPrev'); let R=null;
  function openPreview(id){
    const s=lib.samples[id]; dlg.classList.add('on'); const wrap=$('smpCanvas'); wrap.innerHTML='';
    const dims=Object.assign({},s.defaults||{},s.dims||{}); const keys=Object.keys(s.dims||{}); if(!keys.length&&s.kind==='path') keys.push('L');
    const cf=CONFN[s.conf]||['',''];
    $('smpInfo').innerHTML=`<h3>${esc(s.name)}</h3><div class="muted">${esc(s.en||'')} • <code>${esc(id)}</code> • <b style="color:${cf[1]}">${cf[0]}</b></div>
      <div class="dimrow">${keys.map(k=>`<label>${k}<input type="number" data-d="${k}" value="${dims[k]}" step="1" min="0.1"></label>`).join('')}<span class="muted">سم — غيّر الأبعاد لرؤية تكيّف العينة</span></div>
      ${(s.facts&&s.facts.length)?'<h4>من المستندات</h4><table class="ctab">'+s.facts.map(f=>`<tr><th>${esc(f[0])}</th><td>${esc(f[1])}</td></tr>`).join('')+'</table>':''}
      ${(s.asm&&s.asm.length)?'<h4>افتراضات هندسية — تحتاج تأكيد</h4><ul class="asm">'+s.asm.map(a=>`<li>${esc(a)}</li>`).join('')+'</ul>':''}
      ${(s.src&&s.src.length)?'<h4>المصادر</h4><ul>'+s.src.map(a=>`<li>${esc(a)}</li>`).join('')+'</ul>':''}
      <h4>الأجزاء المرسومة</h4><div class="muted parts" id="smpParts"></div>
      <div class="row" style="gap:6px;margin-top:8px"><button class="mini" id="smpGo" ${(cnt[id]?'':'disabled')}>${cnt[id]?'اذهب إلى أقرب موضع في المبنى':'لا استبدال تلقائي (كتالوج)'}</button><button class="mini" id="smpClose2">إغلاق</button></div>`;
    const names=[...new Set((s.parts||[]).map(p=>p.n).filter(Boolean))]; $('smpParts').textContent=names.join(' • ')||'—';
    build(id,dims); wrap.appendChild(R.renderer.domElement);
    $('smpInfo').querySelectorAll('input[data-d]').forEach(i=>i.onchange=()=>{const d=Object.assign({},dims); $('smpInfo').querySelectorAll('input[data-d]').forEach(x=>d[x.dataset.d]=parseFloat(x.value)||dims[x.dataset.d]); build(id,d,true);});
    $('smpClose2').onclick=closePreview; $('smpGo').onclick=()=>goTo(id);
  }
  function build(id,dims,keepCam){
    const s=lib.samples[id]; if(!R){ const rd=new THREE.WebGLRenderer({antialias:true,alpha:false}); rd.setPixelRatio(Math.min(window.devicePixelRatio,2)); R={renderer:rd,scene:null,cam:new THREE.PerspectiveCamera(32,1,0.1,5000),az:0.7,el:0.35,dist:1,tgt:new THREE.Vector3()}; bindOrbit(); }
    const scene=new THREE.Scene(); scene.background=new THREE.Color(0xdfe5ec); scene.add(new THREE.HemisphereLight(0xffffff,0x888a90,0.95)); const dl=new THREE.DirectionalLight(0xffffff,0.8); dl.position.set(3,6,5); scene.add(dl); const dl2=new THREE.DirectionalLight(0xffffff,0.35); dl2.position.set(-4,-2,-3); scene.add(dl2);
    const g=new THREE.Group(); let bufs; try{bufs=SampleGeo.buildBufs(s,dims);}catch(e){console.warn(e); toast('تعذّر بناء العينة: '+e.message); return;}
    for(const cl of Object.keys(bufs)){ const B=bufs[cl]; if(!B.pos.length) continue; const bg=new THREE.BufferGeometry(); bg.setAttribute('position',new THREE.Float32BufferAttribute(B.pos,3)); bg.setAttribute('normal',new THREE.Float32BufferAttribute(B.nrm,3)); bg.setAttribute('color',new THREE.Float32BufferAttribute(B.col,3)); const m=new THREE.Mesh(bg,LOD.mats[cl]||LOD.mats.matte); m.renderOrder=(cl==='glass'||cl==='ghost')?2:1; g.add(m); }
    scene.add(g); const box=new THREE.Box3().setFromObject(g); const c=box.getCenter(new THREE.Vector3()),sz=box.getSize(new THREE.Vector3()); R.scene=scene; R.tgt.copy(c); const rad=Math.max(sz.x,sz.y,sz.z)*0.5+1; if(!keepCam){R.dist=rad*3.2;} R.rad=rad; R.root=g; fit(); draw();
  }
  function fit(){ const w=Math.max(200,$('smpCanvas').clientWidth),h=Math.max(200,$('smpCanvas').clientHeight); R.renderer.setSize(w,h); R.cam.aspect=w/h; R.cam.updateProjectionMatrix(); }
  function draw(){ if(!R||!R.scene) return; const sp=Math.sin(R.az),cp=Math.cos(R.az),ce=Math.cos(R.el),se=Math.sin(R.el); R.cam.position.set(R.tgt.x+R.dist*sp*ce,R.tgt.y+R.dist*se,R.tgt.z+R.dist*cp*ce); R.cam.lookAt(R.tgt); R.renderer.render(R.scene,R.cam); }
  function bindOrbit(){ const el=R.renderer.domElement; let drag=null,pinch=null; const pts=new Map();
    el.style.touchAction='none';
    el.addEventListener('pointerdown',ev=>{el.setPointerCapture(ev.pointerId); pts.set(ev.pointerId,[ev.clientX,ev.clientY]); drag={x:ev.clientX,y:ev.clientY}; if(pts.size===2){const a=[...pts.values()]; pinch=Math.hypot(a[0][0]-a[1][0],a[0][1]-a[1][1]);}});
    el.addEventListener('pointermove',ev=>{ if(!pts.has(ev.pointerId)) return; pts.set(ev.pointerId,[ev.clientX,ev.clientY]); if(pts.size===2){const a=[...pts.values()],d=Math.hypot(a[0][0]-a[1][0],a[0][1]-a[1][1]); if(pinch){R.dist=Math.max(R.rad*0.3,Math.min(R.rad*20,R.dist*pinch/d));} pinch=d; draw(); return;}
      if(!drag) return; R.az-=(ev.clientX-drag.x)*0.008; R.el=Math.max(-1.45,Math.min(1.45,R.el+(ev.clientY-drag.y)*0.008)); drag={x:ev.clientX,y:ev.clientY}; draw(); });
    const up=ev=>{pts.delete(ev.pointerId); if(pts.size<2) pinch=null; if(!pts.size) drag=null;}; el.addEventListener('pointerup',up); el.addEventListener('pointercancel',up);
    el.addEventListener('wheel',ev=>{ev.preventDefault(); R.dist=Math.max(R.rad*0.3,Math.min(R.rad*20,R.dist*(1+Math.sign(ev.deltaY)*0.12))); draw();},{passive:false});
    window.addEventListener('resize',()=>{if(dlg.classList.contains('on')){fit();draw();}}); }
  function closePreview(){ dlg.classList.remove('on'); $('smpCanvas').innerHTML=''; }
  $('smpClose').onclick=closePreview; dlg.addEventListener('click',ev=>{if(ev.target===dlg) closePreview();});
  /* fly to the nearest instance: the level is ghosted (other levels hidden) so the sample is visible from a clear angle; a chip ends the mode */
  let chip=null;
  let rebarPrev=null;
  function endNear(){ LOD.skipSids=null; if(rebarPrev!==null){LOD.setRebar(rebarPrev); rebarPrev=null;} LOD.invalidate(); setGhost(false); if(chip){chip.remove();chip=null;} wake(); }
  function goTo(id){
    const us=LOD.units.filter(u=>u.sid===id);
    if(!us.length){ /* architecture is never swapped (its details are always in the model): fly to the nearest element of that type instead */
      const bb=elBB, cam0=camera.position; let bi=-1,bd0=1e18; M.els.forEach((e,i)=>{ if(LOD.ruleFor(e)!==id) return; const d=((bb[i*6]+bb[i*6+3])/2-cam0.x)**2+((bb[i*6+1]+bb[i*6+4])/2-cam0.y)**2+((bb[i*6+2]+bb[i*6+5])/2-cam0.z)**2; if(d<bd0){bd0=d;bi=i;} });
      if(bi<0){ toast('لا يوجد موضع لهذه العينة في النموذج'); return; }
      ctx.ensureVisible(bi); const c0=new THREE.Vector3((bb[bi*6]+bb[bi*6+3])/2,(bb[bi*6+1]+bb[bi*6+4])/2,(bb[bi*6+2]+bb[bi*6+5])/2); const sz=Math.max(bb[bi*6+3]-bb[bi*6],bb[bi*6+4]-bb[bi*6+1],bb[bi*6+5]-bb[bi*6+2]);
      closePreview(); document.body.classList.remove('panel-open'); flyTo(c0.clone().add(new THREE.Vector3(0.6,0.3,0.75).normalize().multiplyScalar(Math.max(2.5,Math.min(14,sz*1.5+1.5)))),c0,1100);
      toast('التفاصيل المعمارية معروضة دائمًا في النموذج (لا تُستبدل بالتقريب) — هذا أقرب موضع للعينة «'+(lib.samples[id].name)+'»',4200); wake(2500); return; }
    const cam=camera.position; let best=null,bd=1e18;
    us.forEach(u=>{const d=(u.cx-cam.x)**2+(u.cy-cam.y)**2+(u.cz-cam.z)**2; if(d<bd){bd=d;best=u;}}); const u=best; ctx.ensureVisible(u.eis[0]);
    const smp=lib.samples[id]; const lv=M.levels.find(l=>l.id===u.lvl); const size=Math.max(u.W||50,u.H||50,u.D||50)/100; const dist=Math.max(1.0,Math.min(9,size*1.6+0.8));
    const c=new THREE.Vector3(u.cx,(u.bb[1]+u.bb[4])/2,u.cz);
    const hung=lv&&(u.bb[1]-lv.ffl)>2.2; // above ceiling height: in the ceiling void → look from below, level ghosted
    let dir; if(u.n) dir=new THREE.Vector3(u.n[0],hung?-0.2:0.15,-u.n[1]).normalize(); else if(hung||(smp.place&&smp.place.anchor==='top')) dir=new THREE.Vector3(0.55,-0.3,0.8).normalize(); else dir=new THREE.Vector3(0.6,0.3,0.75).normalize();
    closePreview(); document.body.classList.remove('panel-open');
    // near-inspection: samples of the building shell (walls, doors, windows, cladding, structure) are not swapped in, otherwise they stand between the camera and the target
    const occl=/^(ceil_|floor_|slab|raft|site_paving)/; const shell=c=>c==='architecture'||c==='structure';
    LOD.skipSids=shell(smp.cat)?(occl.test(id)?null:new Set(Object.keys(lib.samples).filter(k=>occl.test(k)))):new Set(Object.keys(lib.samples).filter(k=>shell(lib.samples[k].cat)&&k!==id));
    if(smp.cat==='structure'){ if(rebarPrev===null) rebarPrev=LOD.rebarOn; LOD.setRebar(true); }
    setGhost(true,0.10,[u.lvl],true);
    if(!chip){chip=document.createElement('button'); chip.textContent='إنهاء الفحص القريب ✕'; chip.style.cssText='position:fixed;z-index:30;bottom:78px;left:50%;transform:translateX(-50%);padding:8px 16px;border-radius:20px;border:1px solid #888;background:#fff;color:#111;font:600 13px system-ui;box-shadow:0 2px 8px #0004;cursor:pointer'; chip.onclick=endNear; document.body.appendChild(chip);}
    flyTo(c.clone().addScaledVector(dir,dist),c,1100); toast('اقتربت من '+(smp.name)+' — باقي المبنى شفّاف؛ اضغط «إنهاء الفحص القريب» للعودة',4200); LOD.setEnabled(true); LOD.invalidate(); wake(3000);
  }
  return {open:openPreview};
}
window.initSamplesUI=initSamplesUI;
})();
