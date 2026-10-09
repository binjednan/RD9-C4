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
  const status=M.componentReview?.status_by_id||{},G=M.componentReview?.counts||{},tot=M.els.length||1;
  const GR=M.displayPalette?.proof||window.C4_PALETTE.proof,ks=Object.keys(GR);
  const sh=inv.sheets; const ic=inv.issues;
  let h=`<div class=hub-t><b>${esc((M.meta&&M.meta.project)||'المشروع')}</b><small>إصدار النموذج ${esc(($('ver')||{}).textContent||'')} · جرد ${esc(inv.built||'')}</small></div>`;
  const cc=M.componentReview?.counts||{}, cr=M.coordinationReview?.counts||{};
  const xyRate=((cc.source_checked||0)*100/tot).toFixed(2), usedRate=(sh.total?sh.used*100/sh.total:0).toFixed(1);
  h+=`<div class="pr-hero"><small>تحقيق المشروع المرسوم</small><h3>المكوّن ← المصدر ← التنسيق</h3><p>راجع جميع المكونات، واعزل أي مجموعة، واقرأ دليل الموضع والمنسوب لكل نتيجة.</p><div class="pr-actions"><button class="mini pri" data-act="tour:project">ابدأ عرض المشروع</button><button class="mini" data-act="project:components">مطابقة المكونات</button><button class="mini" data-act="project:coordination">التعارض والمنسوب</button></div>${Object.keys(cc).length?`<p>فحص مستقل لـXY ${cc.source_checked||0} · اتساق تاريخي فقط ${cc.legacy_extract_match||0} · مشتق ${cc.derived||0} · يحتاج تحققًا مستقلاً ${cc.unverified||0}</p>`:''}${Object.keys(cr).length?`<p>تعارض ثلاثي الأبعاد مثبت ${cr.confirmed||0} · عبور مسقط مثبت ${cr.confirmed_plan||0} · مرشح منسوب/شكل ${cr.candidate_height||0} · تداخل يحتاج تحقق المصدر ${cr.model_collision||0}</p>`:''}</div>`;
  // ---- KPI tiles
  h+=`<div class=kpis>`;
  h+=`<button class=kpi data-act="lens:layer" title="لوّن المبنى حسب التخصص"><b>${inv.model.els.toLocaleString('en')}</b><span>عنصر في ${inv.model.types} نوعًا</span><div class=sub><span>${inv.model.levels} مستويات</span><span>${inv.model.units} وحدة</span></div></button>`;
  h+=`<button class=kpi data-act="project:coordination" title="افتح دليل التنسيق"><b>${(cr.candidate_height||0)+(cr.model_collision||0)+(cr.confirmed_plan||0)+(cr.confirmed||0)}</b><span>نتيجة تنسيق هندسي</span><div class=sub><span>${cr.candidate_height||0} مرشح منسوب/شكل</span><span>${cr.model_collision||0} يحتاج إثبات المصدر</span></div></button>`;
  h+=`<button class=kpi data-act="issues:guess" title="افتح قائمة التخمينات"><b>${ic.guess.items}</b><span>قرار تخمين فردي + ${ic.guess.rules} افتراضًا عامًا</span><div class=sub><span class=pill style="background:#0072B2">${ic.guess.impact.high} مرتفع الأثر</span></div></button>`;
  h+=`</div>`;
  // Saved source corrections have a different scope from the independent XY gate.
  const savedChanges=[];
  const heaterFix=M.meta?.water_heater_capacity_source;
  if(heaterFix) savedChanges.push(`السخانات: تصحيح سعات ${heaterFix.type_property_corrections} عنصرًا؛ الحالي ${heaterFix.capacity80L} × 80 لترًا و${heaterFix.capacity50L} × 50 لترًا. مواضع الأجسام وهندستها محفوظة.`);
  const stairFix=M.meta?.core_stairs_source_surfaces;
  if(stairFix) savedChanges.push(`السلالم: تصحيح ${stairFix.groups} مجموعات؛ استبدال ${stairFix.before_bodies} جسمًا بـ${stairFix.after_assemblies} تجميعًا، تضم ${stairFix.tread_surfaces} نائمة و${stairFix.riser_surfaces} قائمة و${stairFix.landing_surfaces} بسطات. القوالب المتطابقة منسوخة؛ جسم الخرسانة وتفاصيله ما زالت تحتاج مصدرًا.`);
  const scoped=M.completionCoordination; if(scoped) savedChanges.push(`فحص أغلفة الاستكمال: ${scoped.target_count} هدفًا؛ ${scoped.positive_volume_pairs} شاهد تداخل موجب منها ${scoped.new_to_legacy_list} غير مسجل في قائمة التعارضات السابقة. هذه نتائج مراجعة هندسية، وأسـطح الدرج المفتوحة خارج فحص الحجم؛ يمكن عرضها من قائمة التعارضات.`);
  (M.meta?.applied_source_batches||[]).forEach(b=>{if(b.saved===true&&b.summary_ar)savedChanges.push(b.summary_ar);});
  if(savedChanges.length) h+=`<section class="unused" aria-label="التصحيحات المحفوظة"><h3>التصحيحات المحفوظة من المخططات</h3>${savedChanges.map(s=>`<p>${esc(s)}</p>`).join('')}<p>سجلات التصحيح الحالية: ${(M.drawingIssues||[]).filter(r=>r.status==='corrected').length}. السجل قد يجمع عدة عناصر؛ عدد العناصر المتأثرة محدد أعلاه لكل دفعة.</p><button class="mini" data-act="project:components">فتح دليل المكونات والتصحيحات</button></section>`;
  // Count source anchors explicitly without promoting composite bodies.
  const nativeDoorIds=new Set(M.els.filter(e=>e.a?.source_door_instance===e.id&&e.a?.source_hinge_side_anchor_xy_cm&&status[e.id]!=='source_checked').map(e=>e.id));
  const doorAnchorN=nativeDoorIds.size;
  if(doorAnchorN){
    const allAnchorN=(cc.source_checked||0)+doorAnchorN;
    const batch=(M.meta?.applied_source_batches||[]).find(b=>b.id==='source-components-E6-FHC-doors-20261009'&&b.saved);
    const newXY=batch?.new_XY_checked||0, electricalN=M.meta?.electrical_room_source_corrections?.controlled_ids?.length||0;
    h+=`<section class="unused" aria-label="تسوية عداد المراجعة"><h3>تسوية أعداد المراجعة</h3><p>تصنيف فحص XY: <bdi dir="ltr">7149 + ${electricalN} + ${newXY-electricalN} = ${7149+newXY}</bdi>؛ السابق + الأجهزة الكهربائية + مواضع تجاويف الإطفاء.</p><p>فحوص XY اللاحقة: <b>${(cc.source_checked||0)-(7149+newXY)}</b>؛ تصنيف XY الحالي: <b>${cc.source_checked||0}</b>.</p><p>درفات أُعيد بناؤها ولها مرساة مصدر مفحوصة: <b>${doorAnchorN}</b>. تبقى مصنفة أجسامًا مركبة لحين استكمال محيط الدرفة وتفاصيلها.</p><p>الإجمالي الفريد للفئتين: <bdi dir="ltr">${cc.source_checked||0} + ${doorAnchorN} = ${allAnchorN}</bdi> عنصرًا له دليل موضع أو مرساة مصدر. هذا عداد مراجعة محدودة، وليس عدد المكونات المعتمدة بالكامل.</p></section>`;
  }
  // Progress is measured by independent gates; extraction coverage is not conformity.
  const hc=M.componentReview?.height_counts||{};
  h+=`<section class="unused" aria-label="تقدم التحقق من المشروع"><h3>تقدم التحقق من المصدر</h3><p><b>${xyRate}%</b> من جميع عناصر المجسم اجتازت فحص موضع XY مستقلًا: ${(cc.source_checked||0).toLocaleString('en')} / ${tot.toLocaleString('en')}.</p><p><b>${usedRate}%</b> من أوراق الحزمة مذكورة في مراجع العناصر والأنواع الحالية: ${sh.used} / ${sh.total}. الاستشهاد لا يثبت استخراج الورقة كاملة أو مراجعة كل تفاصيلها.</p><p>المناسيب: ${(hc.assumed_or_derived||0).toLocaleString('en')} مفترضة أو مشتقة · ${(hc.not_independently_checked||0).toLocaleString('en')} لم تُفحص مستقلًا · ${(hc.drawn_ffl_only||0).toLocaleString('en')} لها مرجع أرضية فقط. تحديد منسوب الأرضية لا يثبت منسوب تركيب الجهاز.</p><p class="note">نسبة اكتمال المطابقة الشاملة لم تُعتمد بعد؛ يلزم إغلاق بوابات المقاسات والمناسيب والمواد واتصال الشبكات. الأعداد أعلاه تحقق محدد من النسخة الحالية.</p></section>`;
  // ---- guided tours
  const tl=(window.TOURS&&window.TOURS.list)||[];
  if(tl.length) h+=`<h3>جولات موجّهة <small class=muted>(كاميرا ونص لكل محطة)</small></h3><div class=tours>`+tl.map(t=>`<button class=tourc data-act="tour:${esc(t.id)}"><b>${esc(t.t)}</b><span>${esc(t.d)}</span><em class=pill style="background:#1f6feb">${t.n} محطات</em></button>`).join('')+`</div>`;
  // ---- the building at a glance
  h+=`<h3>المبنى بنظرة: دليل الموضع لكل طابق <small class=muted>(اضغط طابقًا لعزله)</small></h3><div class=lvstack>`;
  inv.levels.slice().reverse().forEach(l=>{const q={};M.els.filter(e=>e.l===l.id).forEach(e=>{const k=status[e.id]||'unverified';q[k]=(q[k]||0)+1;}); const n=l.n||1; const c=l.clash||{};
    h+=`<button class=lvrow data-act="level:${esc(l.id)}" title="عزل ${esc(l.name)}"><span class=lvn>${esc(l.name)}</span><span class=gbar>${ks.map(k=>`<i style="width:${(q[k]||0)*100/n}%;background:${GR[k].color}" title="${GR[k].name} ${q[k]||0}"></i>`).join('')}</span><span class=lvb>${(c.c||0)?`<em class=pill style="background:#D55E00" title="تداخل يحتاج تنسيقًا">${c.c}</em>`:''}${l.guess?`<em class=pill style="background:#0072B2" title="تخمينات فردية">${l.guess}</em>`:''}</span></button>`;});
  h+=`<button class="mini" data-act="level:all" style="margin-top:4px">إظهار كل الطوابق</button></div>`;
  h+=`<div class=lgrow>${ks.map(k=>`<span><i style="background:${GR[k].color}"></i>${GR[k].name}</span>`).join('')}<span><em class=pill style="background:#D55E00">n</em> يحتاج تنسيقًا</span><span><em class=pill style="background:#0072B2">n</em> تخمين فردي</span></div>`;
  h+=`<p class="note">تصنيفات الإغلاق السابقة في أمر العمل سجل متابعة تاريخي. دليل المصدر الحالي أعلاه هو مرجع المطابقة؛ المنسوب والمادة والاتصال لا تُعتمد بنسبة الجرد.</p>`;
  // ---- sources
  h+=`<h3>المخططات المستشهد بها حاليًا <small class=muted>${sh.used} من ${sh.total} ورقة (${usedRate}%)</small></h3><div class=srcs>`;
  sh.sets.forEach(s=>{h+=`<div class=srow><span>${esc(s.name)}</span><span class=pbar><i style="width:${pct(s.used,s.pages)}%"></i></span><b>${s.used}/${s.pages}</b></div>`;});
  h+=`</div>`;
  /* Sheets without a citation on the current elements/types; not proof that no prior extraction or review occurred. */
  const unl=sh.list.filter(r=>!r.c&&['plan','detail','section'].includes(r.k)), KA={plan:'مسقط',detail:'تفصيل',section:'مقطع / واجهة'};
  h+=`<details class=unused><summary>${unl.length} ورقة مسقط/تفصيل/مقطع بلا مرجع في العناصر الحالية <small class=muted>(اضغط للقائمة)</small></summary>`+sh.sets.map(s=>{ const rows=unl.filter(r=>r.s===s.id); return rows.length?`<div class=unh>${esc(s.name)} <small class=muted>${rows.length}</small></div>`+rows.map(r=>`<div class=unr><code>ص${r.p}</code><b>${esc(r.no||'—')}</b><span>${esc(r.t)}</span><em>${KA[r.k]||''}</em></div>`).join(''):''; }).join('')+`<div class=note>قائمة الجرد الكاملة في <code>docs/INVENTORY.md</code>.</div></details>`;
  // ---- features present
  /* only what needs a note (owner 2026-10-08: «اذكر ما يحتاج للتنويه فقط»): capabilities he asked for that are not obvious on screen («جديد»), behaviours worth knowing («تنبيه»), and anything whose code is missing;
     the ordinary features stay in docs/INVENTORY.md (pipeline/inventory.py FEATURES) */
  const f=(inv.features||[]).filter(x=>x.n||!x.ok); const tag={new:['جديد','ok'],warn:['تنبيه','warn']};
  if(f.length) h+=`<h3>ما يحتاج تنويهًا في العارض <small class=muted>${f.length}</small></h3><ul class=feat>`+f.map(x=>{ const t=x.ok?(tag[x.n]||['','ok']):['غير موجود','no']; return `<li class="${t[1]}"><em>${t[0]}</em> ${esc(x.t)}</li>`; }).join('')+`</ul>`;
  box.innerHTML=h;
  box.addEventListener('click',ev=>{const b=ev.target.closest('[data-act]'); if(!b) return; const [a,v]=b.dataset.act.split(':');
    if(a==='lens'){setLens(v); toast('عدسة «'+({layer:'التخصصات',grade:'دليل المصدر'}[v]||v)+'» — الأيقونة في «العرض ▾»',2600);}
    else if(a==='issues'){openSec('pIssues',{scroll:true}); if(window.ISSUES) window.ISSUES.open(v);}
    else if(a==='level'){ if(v==='all') showAllLevels(); else onlyLevel(v); }
    else if(a==='tour'){ if(window.TOURS) window.TOURS.start(v); }
    else if(a==='project'){window.PROJECT_REVIEW?.open(v);}
  });
}
window.initHub=initHub;
})();

/* Owner's ordered construction preview. Catalogue is derived lazily on opening. */
(function(){
'use strict';
window.initProjectBuild=function(ctx){
  const {M,$,esc,LVL,UNITS,openSec,wake,toast,begin,reveal,end,isHidden}=ctx;
  const sec=document.createElement('section');sec.className='acc';sec.dataset.sec='pBuild';
  sec.innerHTML='<button class="acc-h" type="button" aria-expanded="false"><span class="acc-t">بناء المشروع</span><span class="acc-c">▾</span></button><div class="acc-b"><div class="pane" id="pBuild" dir="rtl"></div></div>';
  $('acc').appendChild(sec);
  const nav=document.createElement('button');nav.type='button';nav.dataset.go='pBuild';nav.textContent='بناء المشروع';$('navTools').appendChild(nav);
  const style=document.createElement('style');style.textContent=`
  #pBuild .pb-row{display:flex;align-items:center;gap:6px;padding:6px 0;border-bottom:1px solid var(--line,#dbe1e8)}
  #pBuild .pb-row label{flex:1;min-width:0;display:flex;align-items:center;gap:7px}
  #pBuild input[type=checkbox]{flex:0 0 auto;width:17px;height:17px}
  #pBuild .pb-row small{white-space:nowrap;font-variant-numeric:tabular-nums}
  #pBuild .pb-order{display:flex;align-items:center;gap:3px}
  #pBuild .pb-order b{min-width:20px;text-align:center}
  #pBuild .pb-order button{min-width:30px;min-height:32px;padding:3px}
  #pBuild .pb-ctl{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
  #pBuild .pb-ctl button,#pBuild select{min-height:36px}
  #pBuild progress{width:100%;accent-color:var(--accent,#2772a3)}
  #pBuild details{margin:9px 0}#pBuild summary{cursor:pointer;font-weight:600;padding:7px 0}
  #pBuild .pb-status{min-height:2.6em;margin:8px 0}#pBuild textarea{width:100%;min-height:150px;box-sizing:border-box;direction:rtl}
  #pBuild button:disabled{opacity:.4}#pBuild .pb-row:focus-within{outline:1px solid var(--accent,#2772a3);outline-offset:2px}
  `;document.head.appendChild(style);
  const box=$('pBuild'),KEY='c4-project-build-v1';let catalogue=null,byKey=null,order=[],speed=1,run=null,raf=0,active=false,paused=false;
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  function prepare(){
    if(catalogue)return;
    catalogue=[];byKey=new Map();
    const add=(key,name,section)=>{const row={key,name,section,ids:[]};catalogue.push(row);byKey.set(key,row);};
    [['A','معماري'],['S','إنشائي'],['M','ميكانيك'],['E','كهرباء'],['site','موقع']].forEach(([k,n])=>add('d:'+k,n,0));
    (M.lifecycle?.systems||[]).forEach(s=>add('s:'+s.id,s.name,1));
    ['B','G','1','2','3','4','5','R','T'].forEach(l=>add('l:'+l,(LVL[l]?.name||l)+' ('+l+')',2));
    UNITS.forEach(u=>add('u:'+u.id,u.name+' — '+(LVL[u.level]?.name||u.level),2));
    const put=(k,i)=>{const row=byKey.get(k);if(row)row.ids.push(i);};
    M.els.forEach((e,i)=>{
      if(e.a?.alt)return;
      const site=e.c==='A.site'||e.c==='P.irr'||e.a?.sys==='water_site'||/^site_/.test(e.t||'')||['tree','plant','car','shade','play','ground'].includes(e.stage);
      const d=site?'site':/^[MP]\./.test(e.c)?'M':e.c[0];put('d:'+d,i);put('s:'+e.a?.sys,i);put('l:'+e.l,i);
      if(e.u!=null)put('u:'+e.u,i);if(e.u2!=null&&e.u2!==e.u)put('u:'+e.u2,i);
    });
    try{const saved=JSON.parse(localStorage.getItem(KEY)||'null');if(saved&&Array.isArray(saved.order)){order=[...new Set(saved.order)].filter(k=>byKey.has(k));if([.5,1,2,4].includes(saved.speed))speed=saved.speed;}}catch(e){}
  }
  function save(){try{localStorage.setItem(KEY,JSON.stringify({v:1,order,speed}));}catch(e){}}
  function render(){
    prepare();
    box.innerHTML='<p class="muted">اختر مجموعات البناء ثم رتّبها. تظهر المكوّنات تدريجيًا في مواضعها الحالية؛ المكوّن المشترك يظهر عند أول مجموعة تشملُه. البدائل تبقى مخفية.</p>'+
      '<div class="pb-ctl"><button type="button" data-pb="play">تشغيل البناء</button><button type="button" data-pb="pause">إيقاف مؤقت</button><button type="button" data-pb="skip">تخطٍّ</button><button type="button" data-pb="restart">إعادة</button><button type="button" data-pb="restore">استعادة العرض</button></div>'+
      '<label>السرعة <select id="pbSpeed" aria-label="سرعة البناء">'+[.5,1,2,4].map(v=>'<option value="'+v+'"'+(v===speed?' selected':'')+'>'+v+' ×</option>').join('')+'</select></label><div class="pb-status" id="pbStatus" role="status" aria-live="polite"></div><progress id="pbProgress" max="1" value="0" aria-label="تقدّم البناء"></progress><div class="pb-ctl"><button type="button" data-pb="copy">نسخ كتوجيه</button></div>'+
      ['الأقسام','الأنظمة','الأدوار والوحدات'].map((name,g)=>'<details'+(g===0?' open':'')+'><summary>'+name+' ('+catalogue.filter(r=>r.section===g).length+')</summary>'+catalogue.filter(r=>r.section===g).map(row=>{
        const p=order.indexOf(row.key),key=esc(row.key),label=esc(row.name);
        return '<div class="pb-row"><label><input type="checkbox" data-key="'+key+'"'+(p>=0?' checked':'')+'><span>'+label+'</span></label><small>'+row.ids.length.toLocaleString('en')+'</small><span class="pb-order"><b data-priority="'+key+'">'+(p>=0?p+1:'')+'</b><button type="button" data-pb="up" data-key="'+key+'" aria-label="رفع أولوية '+label+'">↑</button><button type="button" data-pb="down" data-key="'+key+'" aria-label="خفض أولوية '+label+'">↓</button></span></div>';
      }).join('')+'</details>').join('')+'<small class="muted">الميكانيك يشمل التكييف والصحي والإطفاء. أعداد الأنظمة تخص العناصر الموسومة بالنظام، وقد تتداخل المجموعات.</small><textarea id="pbCopyText" hidden readonly aria-label="نص توجيه البناء"></textarea>';
    sync();
  }
  function sync(){
    if(!$('pbStatus'))return;
    box.querySelectorAll('input[data-key]').forEach(el=>{el.checked=order.includes(el.dataset.key);el.disabled=active;});
    box.querySelectorAll('[data-priority]').forEach(el=>{const p=order.indexOf(el.dataset.priority);el.textContent=p>=0?p+1:'';});
    box.querySelectorAll('[data-pb=up],[data-pb=down]').forEach(b=>{const p=order.indexOf(b.dataset.key);b.disabled=active||p<0||(b.dataset.pb==='up'?p===0:p===order.length-1);});
    const pause=box.querySelector('[data-pb=pause]');pause.disabled=!active||run?.done;pause.textContent=paused?'استئناف':'إيقاف مؤقت';
    box.querySelector('[data-pb=skip]').disabled=!active||run?.done;
    box.querySelector('[data-pb=restore]').disabled=!active;
    ['play','restart','copy'].forEach(a=>box.querySelector('[data-pb='+a+']').disabled=!order.length);
    const p=$('pbProgress');p.max=run?.plan.length||Math.max(order.length,1);p.value=run?(run.done?run.plan.length:run.index):0;
    $('pbStatus').textContent=run?(run.done?'اكتمل العرض — '+run.shown.toLocaleString('en')+' عنصرًا':(paused?'متوقف مؤقتًا — ':'')+(run.index+1)+' / '+run.plan.length+' — '+run.plan[run.index].name):'حدّد المجموعات ورتّبها بالأولوية ('+order.length+' محددة).';
  }
  function stop(restore=true){cancelAnimationFrame(raf);raf=0;run=null;paused=false;if(restore&&active){end();active=false;}sync();}
  function phase(){
    if(!run)return;
    if(run.index>=run.plan.length){run.done=true;sync();return;}
    run.pending=run.plan[run.index].ids.filter(isHidden);run.offset=0;run.elapsed=0;run.last=performance.now();sync();
  }
  function start(){
    if(!order.length)return;
    stop();begin();active=true;run={plan:order.map(k=>byKey.get(k)),index:0,pending:[],offset:0,shown:0,elapsed:0,last:performance.now(),done:false};phase();raf=requestAnimationFrame(tick);
  }
  function tick(now){
    if(!run||paused||run.done)return;
    run.elapsed+=Math.min(now-run.last,100)*speed;run.last=now;
    const target=reduced?run.pending.length:Math.ceil(run.pending.length*Math.min(1,run.elapsed/220));
    const upto=Math.min(target,run.offset+750);
    if(upto>run.offset){reveal(run.pending.slice(run.offset,upto));run.shown+=upto-run.offset;run.offset=upto;}
    if(run.elapsed>=950&&run.offset>=run.pending.length){run.index++;phase();}
    if(!run.done){wake(100);raf=requestAnimationFrame(tick);}
  }
  async function copy(){
    const text='بناء المشروع أمامي بالترتيب التالي:\n'+order.map((k,i)=>(i+1)+'. '+byKey.get(k).name+' — '+byKey.get(k).ids.length+' عنصرًا').join('\n')+'\nأظهر كل مجموعة بعد سابقتها، مع إبقاء مواضع المكوّنات وارتفاعاتها كما هي. المكوّن المشترك يظهر مرة واحدة.';
    try{await navigator.clipboard.writeText(text);toast('نُسخ توجيه البناء');}catch(e){const area=$('pbCopyText');area.value=text;area.hidden=false;area.focus();area.select();toast('حدّد النص الظاهر وانسخه');}
  }
  box.addEventListener('change',ev=>{
    if(ev.target.id==='pbSpeed'){speed=Number(ev.target.value);save();return;}
    const k=ev.target.dataset.key;if(!k||active)return;
    if(ev.target.checked){if(!order.includes(k))order.push(k);}else order=order.filter(x=>x!==k);
    save();sync();
  });
  box.addEventListener('click',ev=>{
    const b=ev.target.closest('[data-pb]');if(!b)return;const a=b.dataset.pb;
    if(a==='play'||a==='restart')start();
    else if(a==='restore')stop();
    else if(a==='pause'&&run&&!run.done){paused=!paused;cancelAnimationFrame(raf);if(!paused){run.last=performance.now();raf=requestAnimationFrame(tick);}sync();}
    else if(a==='skip'&&run&&!run.done){reveal(run.pending.slice(run.offset));run.shown+=run.pending.length-run.offset;run.index++;phase();}
    else if(a==='copy')copy();
    else if((a==='up'||a==='down')&&!active){const i=order.indexOf(b.dataset.key),j=i+(a==='up'?-1:1);if(i>=0&&j>=0&&j<order.length){[order[i],order[j]]=[order[j],order[i]];save();sync();}}
  });
  const open=()=>{if(!catalogue)render();openSec('pBuild');};nav.onclick=open;sec.querySelector('.acc-h').onclick=open;
  // Leave the transient mask before another tool changes visibility; notes keep their own hide bit.
  document.addEventListener('click',ev=>{if(active&&!sec.contains(ev.target)&&ev.target.closest('#secnav button,.acc-h,#btnAll,#btnHome,#isoExit,#viewMenu button,#bar button:not(#btnMore)'))stop();},true);
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&active&&run&&!run.done&&!paused){paused=true;cancelAnimationFrame(raf);sync();}});
  return {open,stop,state:()=>({active,paused,done:!!run?.done,index:run?.index||0,shown:run?.shown||0,order:order.slice(),speed,groups:catalogue?.length||0})};
};
})();
