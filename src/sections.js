/* ===== Visible section planes + plan-cut chips (2026-10-08, roadmap item of docs/HANDOFF_2026-10-07.md §5) =====
   The two cut sliders («قص أفقي» / «قص طولي») already clip the model; here the cut is also SHOWN: a translucent plane with an outline at the cut position (blue = horizontal, rose = longitudinal) that
   moves with the slider and disappears when the cut is off, so it is always clear where the model has been sliced (the fill fades out when the view is straight down / along the plane, leaving the outline).
   Under the sliders, chips «مسقط الطابق» cut at 1.20 m above that level's finished floor (the architects' plan-cut height) and look straight down; «إلغاء القص» removes both cuts and restores the perspective view.
   The planes sit 1 cm on the kept side of the cut (the renderer's global clipping planes would otherwise remove them), take no part in picking (raycast disabled) and are skipped by the shadow pass.  ES2018 style. */
(function(){
'use strict';
function initSections(ctx){
  const {THREE,scene,camera,$,M,wake,viewPreset,elBB}=ctx; const cy=$('clipY'),cx=$('clipX'); if(!cy||!cx) return null;
  const bb=[1e9,1e9,1e9,-1e9,-1e9,-1e9]; { const a=elBB; for(let i=0;i<M.els.length;i++){ for(let k=0;k<3;k++){ const lo=a[i*6+k],hi=a[i*6+3+k]; if(lo<bb[k]) bb[k]=lo; if(hi>bb[3+k]) bb[3+k]=hi; } } }
  const pad=3, X0=bb[0]-pad, X1=bb[3]+pad, Z0=bb[2]-pad, Z1=bb[5]+pad, Y0=bb[1], Y1=bb[4]+2;
  const mk=(col)=>({fill:new THREE.MeshBasicMaterial({color:col,transparent:true,opacity:0.10,side:THREE.DoubleSide,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-1,polygonOffsetUnits:-1}),line:new THREE.LineBasicMaterial({color:col,transparent:true,opacity:0.85})});
  const g=new THREE.Group(); g.name='sectionPlanes'; scene.add(g);
  function plane(col,w,h){ const m=mk(col),q=new THREE.Mesh(new THREE.PlaneGeometry(1,1),m.fill),o=new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(-.5,-.5,0),new THREE.Vector3(.5,-.5,0),new THREE.Vector3(.5,.5,0),new THREE.Vector3(-.5,.5,0)]),m.line); const grp=new THREE.Group(); grp.add(q); grp.add(o);
    [q,o].forEach(x=>{ x.raycast=()=>{}; x.castShadow=false; x.receiveShadow=false; x.renderOrder=1003; }); grp.visible=false; grp.userData.size=[w,h]; g.add(grp); return grp; }
  const PY=plane(0x1f6feb,X1-X0,Z1-Z0), PX=plane(0xd6336c,Z1-Z0,Y1-Y0);
  PY.rotation.x=-Math.PI/2; PY.scale.set(X1-X0,Z1-Z0,1);
  PX.rotation.y=Math.PI/2; PX.scale.set(Z1-Z0,Y1-Y0,1);
  function update(){
    const y=+cy.value, x=+cx.value, ya=y<30, xa=x<46;
    PY.visible=ya; if(ya){ PY.position.set((X0+X1)/2,y-0.01,(Z0+Z1)/2); }
    PX.visible=xa; if(xa){ PX.position.set(x-0.01,(Y0+Y1)/2,(Z0+Z1)/2); }
    document.querySelectorAll('#cutChips [data-cut]').forEach(b=>b.classList.toggle('on',ya&&Math.abs(y-(+b.dataset.cut))<0.06)); wake(); }
  cy.addEventListener('input',update); cx.addEventListener('input',update);
  /* the fill is a hint for oblique views only: looking straight down (or up) at the horizontal plane, or straight along the longitudinal one, it would just tint the whole picture, so it fades out there
     and only the outline stays */
  const dv=new THREE.Vector3(), sm=(a,b,x)=>{ const t=Math.min(1,Math.max(0,(x-a)/(b-a))); return t*t*(3-2*t); }; let lastK=[-1,-1];
  function frame(){
    if(!PY.visible&&!PX.visible) return; camera.getWorldDirection(dv);
    const ky=1-sm(0.78,0.96,Math.abs(dv.y)), kx=1-sm(0.78,0.96,Math.abs(dv.x));
    if(Math.abs(ky-lastK[0])>0.01||Math.abs(kx-lastK[1])>0.01){ lastK=[ky,kx]; PY.children[0].material.opacity=0.10*ky; PX.children[0].material.opacity=0.10*kx; } }
  /* chips */
  const host=document.createElement('div'); host.id='cutChips'; host.className='cut-chips';
  host.innerHTML='<div class="cut-h">مسقط الطابق (قص عند +1.20 م فوق الأرضية ونظر من أعلى)</div><div class="cut-r">'+M.levels.map(l=>{ const v=Math.round((l.ffl+1.2)*10)/10; if(v>=+cy.max||v<+cy.min) return ''; return '<button type="button" class="mini" data-cut="'+v+'" title="'+l.name+' — قص عند '+v.toFixed(1)+' م">'+l.name.replace('سطح الغرف العلوي','غرف السطح')+'</button>'; }).join('')+'<button type="button" class="mini" data-cut="off">إلغاء القص</button></div>';
  cy.insertAdjacentElement('afterend',host);
  host.addEventListener('click',ev=>{ const b=ev.target.closest('[data-cut]'); if(!b) return; const v=b.dataset.cut;
    if(v==='off'){ cy.value=cy.max; cx.value=cx.max; cy.dispatchEvent(new Event('input')); cx.dispatchEvent(new Event('input')); viewPreset('persp'); return; }
    cy.value=v; cy.dispatchEvent(new Event('input')); viewPreset('top'); });
  update();
  return {update,frame,get active(){ return PY.visible||PX.visible; },bounds:()=>({X0,X1,Z0,Z1,Y0,Y1})};
}
window.initSections=initSections;
})();
