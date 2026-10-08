/* ===== Project overview («نظرة عامة»): the first thing a visitor sees (idea: Shneiderman «overview first, zoom and filter, details on demand»; digital-twin dashboards) =====
   Everything shown comes from M.inventory (pipeline/inventory.py, measured on every build): model size, data reliability, where the issues are, how much of the drawing set the model uses,
   how far the architectural closure has got.  Each tile is also a door: it switches a lens, opens the issue centre or isolates a level. */
(function(){
'use strict';
function donut(parts,size,thick){
  const R=size/2-thick/2, C=2*Math.PI*R; let off=0; const tot=parts.reduce((a,p)=>a+p.v,0)||1;
  let svg=`<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}" role="img" aria-label="توزيع الموثوقية"><g transform="rotate(-90 ${size/2} ${size/2})">`;
  parts.forEach(p=>{const len=C*p.v/tot; svg+=`<circle cx="${size/2}" cy="${size/2}" r="${R}" fill="none" stroke="${p.c}" stroke-width="${thick}" stroke-dasharray="${len} ${C-len}" stroke-dashoffset="${-off}"/>`; off+=len;});
  return svg+`</g></svg>`;
}
const pct=(a,b)=>b?Math.round(a*100/b):0;
function initHub(ctx){
  const {M,$,esc,LVL,setLens,openSec,onlyLevel,showAllLevels,PAL,toast}=ctx; const inv=M.inventory; const box=$('hubBox'); if(!box||!inv) return;
  const G=inv.grades||{}; const tot=Object.values(G).reduce((a,b)=>a+b,0)||1; const GR=PAL.GRADE;
  const sh=inv.sheets; const ic=inv.issues;
  let h=`<div class=hub-t><b>${esc((M.meta&&M.meta.project)||'المشروع')}</b><small>إصدار النموذج ${esc(($('ver')||{}).textContent||'')} · جرد ${esc(inv.built||'')}</small></div>`;
  // ---- KPI tiles
  h+=`<div class=kpis>`;
  h+=`<button class=kpi data-act="lens:layer" title="لوّن المبنى حسب التخصص"><b>${inv.model.els.toLocaleString('en')}</b><span>عنصر في ${inv.model.types} نوعًا</span><div class=sub><span>${inv.model.levels} مستويات</span><span>${inv.model.units} وحدة</span></div></button>`;
  h+=`<button class=kpi data-act="lens:grade" title="لوّن المبنى حسب موثوقية البيانات"><div class=kdon>${donut(['d','v','a','s'].map(k=>({v:G[k]||0,c:GR[k].c})),58,11)}<b>${pct((G.d||0)+(G.v||0),tot)}%</b></div><span>موثّق أو مشتق من المخططات</span><div class=sub><span style="color:${GR.a.c}">● تخمين ${pct(G.a||0,tot)}%</span><span style="color:${GR.s.c}">● إخراجي ${pct(G.s||0,tot)}%</span></div></button>`;
  h+=`<button class=kpi data-act="issues:clash" title="افتح مركز التعارضات"><b>${ic.clash.c+ic.clash.k}</b><span>تعارض يستحق المتابعة من ${ic.clash.c+ic.clash.k+ic.clash.m}</span><div class=sub><span class=pill style="background:#D55E00">${ic.clash.c} مؤكد</span><span class=pill style="background:#E69F00">${ic.clash.k} مرشح</span></div></button>`;
  h+=`<button class=kpi data-act="issues:guess" title="افتح قائمة التخمينات"><b>${ic.guess.items}</b><span>قرار تخمين فردي + ${ic.guess.rules} افتراضًا عامًا</span><div class=sub><span class=pill style="background:#0072B2">${ic.guess.impact.high} مرتفع الأثر</span></div></button>`;
  h+=`</div>`;
  // ---- guided tours
  const tl=(window.TOURS&&window.TOURS.list)||[];
  if(tl.length) h+=`<h3>جولات موجّهة <small class=muted>(كاميرا ونص لكل محطة)</small></h3><div class=tours>`+tl.map(t=>`<button class=tourc data-act="tour:${esc(t.id)}"><b>${esc(t.t)}</b><span>${esc(t.d)}</span><em class=pill style="background:#1f6feb">${t.n} محطات</em></button>`).join('')+`</div>`;
  // ---- the building at a glance
  h+=`<h3>المبنى بنظرة: موثوقية كل طابق <small class=muted>(اضغط طابقًا لعزله)</small></h3><div class=lvstack>`;
  inv.levels.slice().reverse().forEach(l=>{const q=l.q||{}; const n=l.n||1; const c=l.clash||{};
    h+=`<button class=lvrow data-act="level:${esc(l.id)}" title="عزل ${esc(l.name)}"><span class=lvn>${esc(l.name)}</span><span class=gbar>${['d','v','a','s'].map(k=>`<i style="width:${(q[k]||0)*100/n}%;background:${GR[k].c}" title="${GR[k].n} ${q[k]||0}"></i>`).join('')}</span><span class=lvb>${(c.c||0)?`<em class=pill style="background:#D55E00" title="تعارض مؤكد">${c.c}</em>`:''}${l.guess?`<em class=pill style="background:#0072B2" title="تخمينات فردية">${l.guess}</em>`:''}</span></button>`;});
  h+=`<button class="mini" data-act="level:all" style="margin-top:4px">إظهار كل الطوابق</button></div>`;
  h+=`<div class=lgrow>${['d','v','a','s'].map(k=>`<span><i style="background:${GR[k].c}"></i>${GR[k].n}</span>`).join('')}<span><em class=pill style="background:#D55E00">n</em> تعارض مؤكد</span><span><em class=pill style="background:#0072B2">n</em> تخمين فردي</span></div>`;
  // ---- closure of the architectural section
  const cl=inv.closure||[]; const sc={closed:['مغلق','#1a7f37'],partial:['جزئي','#bf8700'],open:['مفتوح','#8b949e']};
  h+=`<h3>إغلاق القسم المعماري</h3><div class=closure>`;
  cl.forEach(r=>{const s=sc[r.st]; h+=`<div class=clrow><b>${esc(r.id)}</b><span class=cltt>${esc(r.title.replace(/\*\*/g,'').slice(0,64))}</span><span class=pill style="background:${s[1]}">${s[0]}</span></div>`;});
  h+=`</div>`;
  // ---- sources
  h+=`<h3>المخططات المستعملة <small class=muted>${sh.used} من ${sh.total} ورقة (${pct(sh.used,sh.total)}%)</small></h3><div class=srcs>`;
  sh.sets.forEach(s=>{h+=`<div class=srow><span>${esc(s.name)}</span><span class=pbar><i style="width:${pct(s.used,s.pages)}%"></i></span><b>${s.used}/${s.pages}</b></div>`;});
  h+=`</div>`;
  const un=sh.list.filter(r=>!r.c&&['plan','detail','section'].includes(r.k)).length;
  h+=`<div class=note>${un} ورقة مسقط/تفصيل/مقطع لم يُستخرج منها شيء بعد — قائمة الجرد الكاملة في <code>docs/INVENTORY.md</code>.</div>`;
  // ---- features present
  const f=inv.features||[]; const ok=f.filter(x=>x.ok).length;
  h+=`<h3>إمكانات العارض <small class=muted>${ok}/${f.length}</small></h3><ul class=feat>`+f.map(x=>`<li class="${x.ok?'ok':'no'}">${esc(x.t)}</li>`).join('')+`</ul>`;
  box.innerHTML=h;
  box.addEventListener('click',ev=>{const b=ev.target.closest('[data-act]'); if(!b) return; const [a,v]=b.dataset.act.split(':');
    if(a==='lens'){setLens(v); toast('عدسة «'+({layer:'التخصصات',grade:'موثوقية البيانات'}[v]||v)+'» — الأيقونة في «العرض ▾»',2600);}
    else if(a==='issues'){openSec('pIssues',{scroll:true}); if(window.ISSUES) window.ISSUES.open(v);}
    else if(a==='level'){ if(v==='all') showAllLevels(); else onlyLevel(v); }
    else if(a==='tour'){ if(window.TOURS) window.TOURS.start(v); }
  });
}
window.initHub=initHub;
})();
