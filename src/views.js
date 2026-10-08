/* ===== Saved views + shareable link (2026-10-08, roadmap item of docs/HANDOFF_2026-10-07.md §5) =====
   Researched practice (BCF viewpoints, Sketchfab annotations, Matterport): a view is the camera + what is shown + how it is coloured, stored with a thumbnail and a name; the same state can travel as a link.
   Captured: camera (position + target), hidden levels / sections, lens (mode, chosen classes, «عزل»), look (white / materials + shadows / edges), section cuts, explode, isolated unit, lighting preset,
   the selected element. Restored in a fixed order (visibility → isolation → look / lighting → lens → camera fly → selection).
   • «حفظ المنظور» (panel «ملاحظاتي» or the «⋯» menu) stores it on this device (localStorage c4views, 40 at most).
   • «نسخ رابط المنظور» puts the whole state in the URL (#v=…): opening that link restores it, so a view can be sent in a message and discussed.  ES2018 style. */
(function(){
'use strict';
function initViews(ctx){
  const {THREE,renderer,camera,controls,$,esc,wake,toast,M,CATS,lvlVis,catVis,UNITS,flyTo,applyVis,setLvlVis,setCatVis,isolate,exitIso,getIso,getLens,setLens,getPreset,applyPreset,getClip,setClip,getExplode,setExplode,selIdxOf,select,render}=ctx;
  const KEY='c4views',MAX=40; let views=[]; try{ views=JSON.parse(localStorage.getItem(KEY)||'[]')||[]; }catch(e){ views=[]; }
  const persist=()=>{ try{ localStorage.setItem(KEY,JSON.stringify(views)); }catch(e){ toast('تعذّر حفظ المناظير على هذا المتصفح (وضع خاص؟)'); } };
  const r3=a=>[+a.x.toFixed(3),+a.y.toFixed(3),+a.z.toFixed(3)];
  const idIdx=new Map(); M.els.forEach((e,i)=>idIdx.set(e.id,i));

  function capture(){
    const L=getLens(), look=window.LOOK?window.LOOK.snapshot():null; const lensOn=L&&L.mode!=='off'&&L.mode!=='custom';
    const lvOff=M.levels.filter(l=>lvlVis[l.id]===false).map(l=>l.id), off=Object.keys(CATS).filter(c=>catVis[c]===false); const si=selIdxOf();
    const v={v:1,cam:{p:r3(camera.position),t:r3(controls.target)}};
    if(lvOff.length) v.lvOff=lvOff; if(off.length) v.off=off;
    if(lensOn) v.lens={m:L.mode,s:L.selected,h:L.hideRest?1:0};
    if(look) v.look=look; const cl=getClip(); if(cl.y<30||cl.x<46) v.clip=cl; const ex=getExplode(); if(ex) v.ex=ex;
    const iso=getIso(); if(iso) v.iso=iso; const pre=getPreset(); if(pre!=='day') v.pre=pre; if(si>=0) v.sel=M.els[si].id; return v; }
  function apply(v,opt){
    if(!v||v.v!==1) { toast('منظور غير صالح'); return; } opt=opt||{};
    if(getIso()) exitIso(true);
    M.levels.forEach(l=>setLvlVis(l.id,!(v.lvOff||[]).includes(l.id))); Object.keys(CATS).forEach(c=>setCatVis(c,!(v.off||[]).includes(c)));
    setExplode(v.ex||0); const cl=v.clip||{y:30,x:46}; setClip(cl.y,cl.x);
    if(v.pre&&v.pre!==getPreset()) applyPreset(v.pre); else if(!v.pre&&getPreset()!=='day') applyPreset('day');
    if(window.LOOK&&v.look) window.LOOK.restore(v.look); else if(window.LOOK&&window.LOOK.white) window.LOOK.set('mat',{quiet:true});
    applyVis(); if(v.iso) isolate(v.iso);
    const L=getLens(); if(v.lens){ setLens(v.lens.m,{hideRest:!!v.lens.h}); if(L&&L.setSelection) L.setSelection(v.lens.s||[]); } else if(L&&L.mode!=='off') setLens('off');
    const p=new THREE.Vector3(v.cam.p[0],v.cam.p[1],v.cam.p[2]),t=new THREE.Vector3(v.cam.t[0],v.cam.t[1],v.cam.t[2]); if(!v.iso||opt.camera) flyTo(p,t,opt.instant?1:900);
    if(v.sel){ const i=idIdx.get(v.sel); if(i!==undefined) select(i); } else select(-1);
    wake(2000); }
  function thumb(){
    try{ render(); const cv=renderer.domElement,w=192,h=Math.max(60,Math.round(192*cv.height/Math.max(1,cv.width))),c=document.createElement('canvas'); c.width=w; c.height=h; c.getContext('2d').drawImage(cv,0,0,w,h); return c.toDataURL('image/jpeg',0.62); }catch(e){ return null; } }

  /* ---------------- panel ---------------- */
  const box=$('viewsBox'); let nameEl=null;
  const dt=ts=>{ const d=new Date(ts),p=n=>String(n).padStart(2,'0'); return d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate())+' '+p(d.getHours())+':'+p(d.getMinutes()); };
  function render_(){
    if(!box) return; let h='<div class="is-sh">المناظير المحفوظة ('+views.length+')</div><p class="muted vw-how">احفظ زاوية الكاميرا مع ما هو ظاهر ومُلوَّن، وانسخ رابطًا يعيد المنظور نفسه لمن يفتحه.</p>';
    h+='<div class="vw-add"><input id="vwName" type="text" placeholder="اسم المنظور (اختياري)" maxlength="60" autocomplete="off"><button type="button" class="nt-pri" data-vw="save">حفظ المنظور الحالي</button><button type="button" data-vw="linkNow">نسخ رابط المنظور الحالي</button></div>';
    if(!views.length) h+='<div class="muted">لا مناظير محفوظة بعد.</div>';
    views.forEach((v,i)=>{ h+='<div class="vw-card"><img src="'+esc(v.th||'')+'" alt="" width="96" height="60"'+(v.th?'':' hidden')+'><div class="vw-t"><b>'+esc(v.n)+'</b><small>'+esc(dt(v.ts))+(v.s.lens?' · عدسة':'')+(v.s.look&&v.s.look.w?' · أبيض':'')+(v.s.iso?' · معزولة':'')+'</small><span class="vw-b"><button type="button" class="mini nt-pri" data-vw="go" data-i="'+i+'">عرض</button><button type="button" class="mini" data-vw="link" data-i="'+i+'">رابط</button><button type="button" class="mini nt-del" data-vw="del" data-i="'+i+'">حذف</button></span></div></div>'; });
    box.innerHTML=h; nameEl=$('vwName'); }
  const toLink=s=>{ const b=btoa(unescape(encodeURIComponent(JSON.stringify(s)))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''); return location.href.split('#')[0]+'#v='+b; };
  const fromCode=c=>{ try{ const b=c.replace(/-/g,'+').replace(/_/g,'/'),pad=(4-b.length%4)%4; return JSON.parse(decodeURIComponent(escape(atob(b+'='.repeat(pad))))); }catch(e){ return null; } };
  function copy(t,msg){ const ok=()=>toast(msg,2600); if(navigator.clipboard&&window.isSecureContext) navigator.clipboard.writeText(t).then(ok,()=>fb()); else fb();
    function fb(){ try{ const ta=document.createElement('textarea'); ta.value=t; ta.style.cssText='position:fixed;opacity:0'; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta); ok(); }catch(e){ prompt('انسخ الرابط:',t); } } }
  function save(name){ const s=capture(); const n=(name||'').trim()||('منظور '+(views.length+1)); views.unshift({n,ts:Date.now(),s,th:thumb()}); if(views.length>MAX) views.length=MAX; persist(); render_(); toast('حُفظ المنظور «'+n+'»',2200); }
  document.addEventListener('click',ev=>{ const b=ev.target.closest&&ev.target.closest('[data-vw]'); if(!b) return; ev.preventDefault(); const a=b.dataset.vw,i=+b.dataset.i;
    if(a==='save'){ save(nameEl?nameEl.value:''); } else if(a==='linkNow'){ copy(toLink(capture()),'نُسخ رابط المنظور الحالي — افتحه في أي جهاز'); }
    else if(a==='go'&&views[i]){ apply(views[i].s,{}); if(window.innerWidth<=860) document.body.classList.remove('panel-open'); }
    else if(a==='link'&&views[i]){ copy(toLink(views[i].s),'نُسخ رابط المنظور'); }
    else if(a==='del'&&views[i]){ if(b.dataset.arm!=='1'){ b.dataset.arm='1'; b.textContent='تأكيد'; setTimeout(()=>{ b.dataset.arm='0'; b.textContent='حذف'; },3000); return; } views.splice(i,1); persist(); render_(); } });
  const bs=$('btnSaveView'); if(bs) bs.onclick=()=>save('');
  const bl=$('btnLinkView'); if(bl) bl.onclick=()=>copy(toLink(capture()),'نُسخ رابط المنظور الحالي');
  render_();
  /* a link restores its view once the model has drawn */
  function fromHash(){ const m=/[#&]v=([A-Za-z0-9_-]+)/.exec(location.hash||''); if(!m) return false; const v=fromCode(m[1]); if(!v) return false; setTimeout(()=>{ apply(v,{}); toast('طُبّق المنظور المشارَك',2600); },1400); return true; }
  const fromLink=fromHash();
  return {capture,apply,save,toLink,fromCode,list:()=>views.slice(),fromLink};
}
window.initViews=initViews;
})();
