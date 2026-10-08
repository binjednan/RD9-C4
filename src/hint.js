/* ===== First-visit hint (2026-10-08, roadmap item of docs/HANDOFF_2026-10-07.md §5) =====
   One small card, shown once per browser: how to move, how to pick, and where the look / lenses / notes live — written for a visitor who has never seen the model. It never blocks: the first drag on the
   model, Esc, the «فهمت» button or 25 s dismiss it, and the choice is remembered (localStorage c4hint). It is not shown for a shared-view link (#v=…) or a QA run (?qa=…).  ES2018 style. */
(function(){
'use strict';
function initHint(ctx){
  const {$,wake}=ctx; let seen=false; try{ seen=localStorage.getItem('c4hint')==='1'; }catch(e){}
  if(seen||/[?&]qa=/.test(location.search)||/[#&]v=/.test(location.hash)) return {shown:false};
  const view=$('view'); if(!view) return {shown:false};
  const touch=!!(window.matchMedia&&matchMedia('(pointer:coarse)').matches);
  const el=document.createElement('div'); el.id='hint'; el.setAttribute('role','dialog'); el.setAttribute('aria-label','تلميح الزيارة الأولى');
  el.innerHTML='<b>ابدأ من هنا</b><ul>'+
    '<li>'+(touch?'إصبع واحد يدوّر المبنى (حتى أسفله أيضًا) وحول العنصر إن كان محددًا، وإصبعان معًا يحرّكان، وتباعدهما يقرّب وتقاربهما يبعّد.':'اسحب بالزر الأيسر لتدوير المبنى — حتى أسفله لترى بطون البلاطات، وحول العنصر إن كان محددًا — والعجلة للتقريب، والزر الأيمن للتحريك.')+'</li>'+
    '<li>انقر أي عنصر لتظهر بطاقته بمصدر كل بيان؛ ومنها تُخفيه أو تكتب عليه ملاحظة لتعديلات قادمة.</li>'+
    '<li>من «العرض ▾»: المظهر الأبيض والرمادي، والعدسات التي تُلوّن قسمًا واحدًا. ومن القائمة الجانبية: الأقسام والوحدات والمتابعة.</li></ul>'+
    '<div class="hint-b"><button type="button" class="hint-ok">فهمت</button><button type="button" class="hint-help">دليل التحكم</button></div>';
  view.appendChild(el);
  let t=null; const done=()=>{ if(!el.parentNode) return; el.classList.remove('on'); try{ localStorage.setItem('c4hint','1'); }catch(e){} clearTimeout(t); window.removeEventListener('keydown',onKey,true); view.removeEventListener('pointerdown',onDown,true); setTimeout(()=>{ if(el.parentNode) el.parentNode.removeChild(el); },400); };
  const onKey=ev=>{ if(ev.key==='Escape') done(); }; const onDown=ev=>{ if(ev.target&&ev.target.closest&&ev.target.closest('#hint')) return; if(ev.target&&ev.target.tagName==='CANVAS') done(); };
  el.querySelector('.hint-ok').onclick=done; el.querySelector('.hint-help').onclick=()=>{ done(); const b=$('btnHelp'); if(b) b.click(); };
  window.addEventListener('keydown',onKey,true); view.addEventListener('pointerdown',onDown,true);
  setTimeout(()=>{ el.classList.add('on'); wake(); },1600); t=setTimeout(done,25000);
  return {shown:true,dismiss:done,el};
}
window.initHint=initHint;
})();
