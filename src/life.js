/* ===== System life-cycle tests: «اختبارات دورة الحياة» (owner 2026-10-08) =====
   «قم بدورة حياة للكهرباء على أن تضيء فقط ما هو موصل داخل المجسم بموصلات فعلية … وكذلك التكييف والمياه والصرف والحريق … اعتبرها اختبارات».
   The numbers come from pipeline/lifecycle.py (M.lifecycle): every system is switched on from its sources and only what is connected through REAL geometry (pipes, ducts, conductors, valves, dampers that touch)
   is energised; what does not reach a source stays dark and fails its test.  Here: a card per system (pass rate), the tests with their counts, a player that lights the network outward from the source in the
   order the current really travels (arrival distance), and the failing devices as a list that flies to each one.  The colouring uses the viewer's lens (custom classes), so the white look / «عزل» work with it.  ES2018 style. */
(function(){
'use strict';
function initLife(ctx){
  const {M,$,esc,LVL,UNITS,TYPES,setLens,LENS,wake,flyToBox,bboxOf,highlight,clearHL,select,toast,grpMap,openSec}=ctx;
  const box=$('lifeBox'); const LC=M.lifecycle; if(!box) return null;
  if(!LC||!LC.systems||!LC.systems.length){ box.innerHTML='<div class="muted">لا نتائج اختبارات في هذا النموذج (شغّل pipeline/lifecycle.py).</div>'; return null; }
  const CLS=[{k:'src',n:'مصدر',c:'#0072B2',h:'نقطة تشغيل النظام (خزان، مبرّد، سخان، لوحة …)'},{k:'con',n:'موصل مُغذّى',c:'#56B4E9',h:'ماسورة أو مجرى أو موصل موصول فعليًا بالمصدر'},
    {k:'ok',n:'نهاية مُغذّاة',c:'#009E73',h:'جهاز موصول بالمصدر عبر هندسة فعلية'},{k:'bad',n:'نهاية غير موصولة',c:'#D55E00',h:'جهاز لا يصله المصدر — اختبار فاشل'},{k:'orph',n:'موصل يتيم',c:'#DB7F4A',h:'ماسورة أو مجرى لا يصل إلى أي مصدر'}];
  let cur=0, timer=0, playing=false, T=0, hideOther=false, finalMode=false; const sys=()=>LC.systems[cur];
  const lvName=l=>(LVL[l]&&LVL[l].name)||l;
  const total=(s)=>s.tests.length, passN=s=>s.tests.filter(t=>t.p).length;
  /* ---- per-system derived sets (built once on demand) ---- */
  const cache={};
  function prep(s){
    if(cache[s.id]) return cache[s.id];
    const els=M.els, n=s.ri.length; const grpOf=i=>els[i].grp||null; const srcSet=new Set(s.src);
    const unitOf=i=>{ const g=grpOf(i); return g?('g:'+g):('e:'+i); };
    const bad=new Map(); s.x.forEach(i=>{ const k=unitOf(i); if(!bad.has(k)) bad.set(k,[]); bad.get(k).push(i); });
    const ok=new Set(); for(let k=0;k<n;k++){ if(s.rk[k]==='t') ok.add(unitOf(s.ri[k])); }
    const expand=(i)=>{ const g=grpOf(i); return g&&grpMap&&grpMap[g]?grpMap[g]:[i]; };
    return cache[s.id]={bad,ok,expand,srcSet,maxD:s.rd.length?s.rd[s.rd.length-1]:0};
  }
  function classMap(s,upto,fin){
    const P=prep(s), map=new Map(); const n=s.ri.length;
    for(let k=0;k<n&&s.rd[k]<=upto;k++){ const i=s.ri[k], r=s.rk[k];
      if(r==='s') map.set(i,1); else if(r==='c') map.set(i,2); else P.expand(i).forEach(j=>{ if(!map.has(j)||map.get(j)!==1) map.set(j,3); }); }
    if(fin){ s.x.forEach(i=>{ P.expand(i).forEach(j=>{ if(!map.has(j)) map.set(j,4); }); }); s.o.forEach(i=>{ if(!map.has(i)) map.set(i,5); }); }
    return map;
  }
  function paint(upto,fin){ const s=sys(); setLens('custom',{classes:CLS,map:classMap(s,upto,fin),label:'دورة حياة: '+s.name,hideRest:hideOther}); document.querySelectorAll('#viewMenu button[data-lens]').forEach(b=>b.classList.remove('on')); }
  /* ---- player ---- */
  function stop(keep){ playing=false; clearInterval(timer); timer=0; const b=$('lfPlay'); if(b){ b.textContent='▶ تشغيل الدورة'; b.classList.remove('on'); } if(!keep) setBar(0); }
  function setBar(v){ const r=$('lfBar'); if(r) r.value=v; const t=$('lfBarT'); if(t) t.textContent=Math.round(v)+'%'; }
  function play(){
    const s=sys(), P=prep(s); if(!s.ri.length){ toast('لا مصدر موصول في هذا النظام — لا شيء يُضاء'); paint(0,true); return; }
    stop(true); playing=true; finalMode=false; T=0; const b=$('lfPlay'); if(b){ b.textContent='⏸ إيقاف'; b.classList.add('on'); }
    const t0=performance.now(), dur=7000, max=Math.max(P.maxD,1);
    paint(0,false); wake(dur+500);
    timer=setInterval(()=>{ const k=Math.min(1,(performance.now()-t0)/dur), e=k<0.5?2*k*k:1-Math.pow(-2*k+2,2)/2; T=e*max; setBar(e*100); if(k>=1){ stop(true); setBar(100); finalMode=true; paint(max,true); result(); } else paint(T,false); wake(400); },120);
  }
  function result(){ const s=sys(); toast(s.icon+' '+s.name+': '+s.cnt.ok.toLocaleString('en')+' من '+s.cnt.ter.toLocaleString('en')+' نهاية مُغذّاة'+(s.cnt.ter-s.cnt.ok?' — '+(s.cnt.ter-s.cnt.ok).toLocaleString('en')+' غير موصولة':'')+(s.cnt.orph?' · '+s.cnt.orph.toLocaleString('en')+' موصل يتيم':''),5200); }
  function showFinal(){ stop(true); const s=sys(), P=prep(s); finalMode=true; setBar(100); paint(Math.max(P.maxD,1),true); wake(800); }
  function focusUnits(keys,color){ const s=sys(), P=prep(s); const idx=[]; keys.forEach(k=>{ (P.bad.get(k)||[]).forEach(i=>P.expand(i).forEach(j=>idx.push(j))); }); if(!idx.length) return; const u=[...new Set(idx)]; if(select) select(-1); highlight(u,color||0xd55e00,true,0.5); flyToBox(bboxOf(u)); }
  /* ---- panel ---- */
  const pct=(a,b)=>b?Math.round(a*100/b):0;
  function render(){
    const all=LC.systems.reduce((a,s)=>a+total(s),0), pass=LC.systems.reduce((a,s)=>a+passN(s),0);
    let h='<div class="lf-top"><b>'+pass+' من '+all+' اختبارًا ناجح</b><small class="muted">بناء '+esc(LC.built||'')+' · فجوة التلامس المقبولة '+Math.round(LC.tol*100)+' سم</small></div>';
    h+='<p class="muted lf-how">يُشغَّل كل نظام من مصادره، ولا يُضاء إلا ما هو موصول بالمصدر عبر هندسة فعلية في النموذج (مواسير ومجاري وموصلات ومحابس تتلامس). ما لا يصل يبقى مظلمًا ويُحسب فشلًا ويظهر في القائمة لتراجعه.</p>';
    h+='<div class="lf-cards">'+LC.systems.map((s,i)=>{ const p=pct(s.cnt.ok,s.cnt.ter), np=passN(s); return '<button type="button" class="lf-card'+(i===cur?' on':'')+'" data-lf="sel" data-i="'+i+'" style="--lc:'+esc(s.color)+'"><span class="lf-ic">'+esc(s.icon)+'</span><b>'+esc(s.name)+'</b><span class="lf-pb"><i style="width:'+p+'%"></i></span><small>'+s.cnt.ok.toLocaleString('en')+' / '+s.cnt.ter.toLocaleString('en')+' موصول · '+np+'/'+total(s)+' اختبار</small></button>'; }).join('')+'</div>';
    const s=sys(), P=prep(s);
    h+='<div class="lf-det"><h4>'+esc(s.icon)+' '+esc(s.name)+'</h4><p class="muted">'+esc(s.desc)+'</p>';
    h+='<div class="lf-ctl"><button type="button" id="lfPlay" class="lf-pri" data-lf="play">▶ تشغيل الدورة</button><button type="button" data-lf="final">النتيجة</button><button type="button" data-lf="hide" class="'+(hideOther?'on':'')+'" title="إخفاء كل ما ليس من هذا النظام">عزل النظام</button><button type="button" data-lf="off">إيقاف التلوين</button></div>';
    h+='<div class="lf-bar"><input id="lfBar" type="range" min="0" max="100" value="0" aria-label="تقدّم الدورة"><span id="lfBarT">0%</span></div>';
    h+='<table class="lf-t"><tbody>'+s.tests.map(t=>'<tr class="'+(t.p?'ok':'no')+'"><td class="lf-st">'+(t.p?'✔':'✖')+'</td><td>'+esc(t.n)+'</td><td class="lf-n">'+t.ok.toLocaleString('en')+' / '+t.of.toLocaleString('en')+'</td></tr>').join('')+'</tbody></table>';
    const d=s.cnt, iso=d.isl||0;
    h+='<div class="lf-diag">'+(s.cnt.ter-s.cnt.ok?'<span>غير موصولة <b>'+(s.cnt.ter-s.cnt.ok).toLocaleString('en')+'</b></span>':'')+(d.orph?'<span>موصلات يتيمة <b>'+d.orph.toLocaleString('en')+'</b></span>':'')+(d.near?'<span title="يوجد موصل من النظام قربها في المسقط">وصلة أخيرة ناقصة <b>'+d.near+'</b></span>':'')+(d.far?'<span title="لا شيء موثّق قربها">لا شيء قربها <b>'+d.far+'</b></span>':'')+'</div>';
    // failing list
    const keys=[...P.bad.keys()];
    if(keys.length){
      const byL={}; keys.forEach(k=>{ const e=M.els[P.bad.get(k)[0]]; (byL[e.l]=byL[e.l]||[]).push(k); });
      h+='<div class="lf-fh"><b>الأجهزة غير الموصولة ('+keys.length.toLocaleString('en')+')</b><button type="button" class="mini" data-lf="allbad">اعرضها كلها</button></div><div class="lf-fl">';
      Object.keys(byL).sort((a,b)=>((LVL[b]||{idx:0}).idx)-((LVL[a]||{idx:0}).idx)).forEach(l=>{
        h+='<details class="lf-lv"><summary>'+esc(lvName(l))+' <small class="muted">'+byL[l].length+'</small><button type="button" class="mini" data-lf="lvbad" data-l="'+esc(l)+'">اعرض</button></summary>';
        byL[l].slice(0,40).forEach(k=>{ const e=M.els[P.bad.get(k)[0]], T=TYPES[e.t]||{}; const u=e.u?(UNITS.find(x=>x.id===e.u)||{}).name:''; h+='<button type="button" class="lf-fi" data-lf="one" data-k="'+esc(k)+'">'+esc((T.n||e.t||e.c).slice(0,38))+(u?' · '+esc(u):'')+'</button>'; });
        if(byL[l].length>40) h+='<small class="muted">و'+(byL[l].length-40)+' أخرى</small>';
        h+='</details>'; });
      h+='</div>';
    } else h+='<div class="lf-allok">كل نهايات هذا النظام موصولة بمصدره.</div>';
    h+='</div>';
    box.innerHTML=h; setBar(finalMode?100:0);
  }
  box.addEventListener('click',ev=>{ const b=ev.target.closest('[data-lf]'); if(!b) return; ev.stopPropagation(); const a=b.dataset.lf;
    if(a==='sel'){ stop(); cur=+b.dataset.i; finalMode=false; render(); }
    else if(a==='play'){ if(playing) { stop(); } else play(); }
    else if(a==='final'){ showFinal(); }
    else if(a==='hide'){ hideOther=!hideOther; b.classList.toggle('on',hideOther); if(finalMode) showFinal(); else if(LENS&&LENS.mode==='custom') paint(T,false); }
    else if(a==='off'){ stop(); setLens('off'); clearHL(); }
    else if(a==='allbad'){ focusUnits([...prep(sys()).bad.keys()]); }
    else if(a==='lvbad'){ const l=b.dataset.l, P=prep(sys()); focusUnits([...P.bad.keys()].filter(k=>M.els[P.bad.get(k)[0]].l===l)); }
    else if(a==='one'){ focusUnits([b.dataset.k]); } });
  box.addEventListener('input',ev=>{ if(ev.target.id==='lfBar'){ stop(true); const s=sys(), P=prep(s), v=+ev.target.value; T=P.maxD*v/100; finalMode=v>=100; paint(T,finalMode); $('lfBarT').textContent=Math.round(v)+'%'; } });
  render();
  return {render,play,stop,select:i=>{ cur=i; render(); },get systems(){ return LC.systems; },state:()=>({cur,playing,hideOther,finalMode,T})};
}
window.initLife=initLife;
})();
