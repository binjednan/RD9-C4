/* ===== Guided tours («جولات موجّهة») =====
   Idea: Sketchfab annotations (one camera view-point + one sentence per stop, previous / next / autoplay) and BCF view-points (a stop also fixes what is visible).
   A stop = what is visible (levels / disciplines / unit), a lens, a highlighted set of elements, a camera and a caption.  Every stop is applied from a clean state (all visible, no lens, no
   isolation), so stops never leak into each other; ending the tour puts back exactly what the visitor had.  Every number in a caption is counted from the model when the stop is shown. */
(function(){
'use strict';
function initTours(ctx){
  const {M,THREE,camera,controls,$,esc,UNITS,CATS,wake,flyTo,flyToBox,bboxOf,highlight,clearHL,setLens,LENS,viewPreset,isolate,exitIso,isoActive,applyVis,setLvlVis,setCatVis,lvlVis,catVis,setGhost,select,toast,closeMenus}=ctx;
  const els=M.els, N=v=>Number(v).toLocaleString('en'), cache=new Map(), view=$('view');
  const LV=id=>(M.levels.find(l=>l.id===id)||{}).name||id;
  function sel(q){ const k=JSON.stringify(q); if(cache.has(k)) return cache.get(k); const out=[];
    for(let i=0;i<els.length;i++){ const e=els[i];
      if(q.c&&!(q.c.slice(-1)==='.'?e.c.indexOf(q.c)===0:e.c===q.c)) continue; if(q.l&&e.l!==q.l) continue; if(q.ls&&q.ls.indexOf(e.l)<0) continue;
      if(q.t){ const t=String(e.t||''); if(q.t.slice(-1)==='*'?t.indexOf(q.t.slice(0,-1))!==0:t!==q.t) continue; } if(q.stage&&e.stage!==q.stage) continue; if(q.u&&e.u!==q.u&&e.u2!==q.u) continue; out.push(i); }
    cache.set(k,out); return out; }
  const n=q=>sel(q).length, units=()=>UNITS, grades=()=>(M.inventory&&M.inventory.grades)||{d:0,v:0,a:0,s:0}, tot=()=>Object.values(grades()).reduce((a,b)=>a+b,0)||1, pc=k=>Math.round(grades()[k]*100/tot());
  const D_FAR=[-0.55,0.6,0.55];
  const bedrooms=k=>k==null?'':k===1?'غرفة نوم واحدة':k===2?'غرفتا نوم':k+' غرف نوم';
  /* ---------------- the tours ---------------- */
  const TOURS=[
   {id:'ext',t:'المبنى من الخارج',d:'الواجهات والسطح والموقع',steps:[
     {t:'نظرة عامة',view:'persp',x:()=>`مبنى سكني من المستويات: ${M.levels.map(l=>l.name).join('، ')}. النموذج ${N(els.length)} عنصرًا مبنيًّا من المخططات المعتمدة. اسحب للتدوير وانقر أي عنصر لتظهر بطاقته.`},
     {t:'الواجهة',view:'front',x:()=>'نوافذ بأنماط CW-07 إلى CW-19 حسب الجدول المعتمد (A801/A802) مع عتبة من البلوك والبورسلين بارتفاع 60 سم. كسوة الدور الأرضي رمادية كما في صور الموقع (اللون من الصور لا من المخطط).'},
     {t:'السطح والمعدات',hl:{c:'M.equip',l:'R'},focus:{ls:['R','T']},dir:[-0.5,0.95,0.5],x:()=>`المعدات المُبرزة بالأزرق على السطح: مبرّدات (${n({c:'M.equip',l:'R',t:'chiller'})}) · مضخات مياه مبردة (${n({c:'M.equip',l:'R',t:'chwp'})}) · وحدة هواء طازج FAHU (${n({c:'M.equip',l:'R',t:'fahu'})}) · مراوح (${n({c:'M.fan',l:'R'})}).`},
     {t:'الموقع والحديقة',focus:{stage:'tree'},dir:[0.35,0.85,-0.55],x:()=>'الحديقة ومنطقة ألعاب الأطفال في الدور الأرضي مأخوذتان من A2300 وتقديم INEX/EDUPARK. هذه كماليات إخراجية للعرض لا للتنفيذ وتُخفى بمفتاح واحد من «الأقسام والطوابق».'}]},
   {id:'str',t:'الهيكل الإنشائي',d:'اللبشة والأعمدة والجسور والبلاطات',steps:[
     {t:'الهيكل وحده',layers:['S'],view:'persp',x:()=>`الهيكل الإنشائي بلا أي تخصص آخر: لبشة على ${N(n({c:'S.pile'}))} خازوقًا و${N(n({c:'S.col'}))} عمودًا و${N(n({c:'S.beam'}))} جسرًا وبلاطات وجدران قص ونوى الدرج والمصاعد.`},
     {t:'اللبشة والخوازيق',layers:['S'],levels:['B'],focus:{c:'S.',l:'B'},dir:[-0.45,-0.55,0.7],x:()=>`في البدروم، منظورًا من تحت اللبشة: ${N(n({c:'S.pile'}))} خازوقًا و${N(n({c:'S.col',l:'B'}))} عمودًا فوق اللبشة. طول الخازوق الفعلي 13 م في المخطط الإنشائي ويُعرض 30 سم فقط تحت اللبشة للدلالة.`},
     {t:'دور نموذجي',layers:['S'],levels:['2'],focus:{c:'S.',l:'2'},dir:[-0.45,0.8,0.6],x:()=>`الدور الثاني: ${n({c:'S.col',l:'2'})} عمودًا و${n({c:'S.beam',l:'2'})} جسورًا وبلاطة وجدران قص. الأدوار 2–5 متماثلة في الهيكل (${n({c:'S.col',l:'3'})} عمودًا في كل دور).`},
     {t:'الدور الأرضي',layers:['S'],levels:['G'],focus:{c:'S.',l:'G'},dir:[-0.45,0.8,0.6],x:()=>`الدور الأرضي: ${n({c:'S.col',l:'G'})} عمودًا و${n({c:'S.beam',l:'G'})} جسرًا و${n({c:'S.slab',l:'G'})} قطع بلاطة (بينها فتحة المنحدر).`}]},
   {id:'flat',t:'شقة نموذجية',d:'مساحتها وتشطيباتها وخدماتها',steps:[
     {t:'الشقة 1 في الدور الأول',unit:'1-1',focus:{u:'1-1'},k:0.8,dir:[-0.25,0.95,0.4],x:()=>{const u=units().find(x=>x.id==='1-1')||{}; return `${u.name||'الشقة'}: ${bedrooms(u.bed)}${u.bed!=null?' · ':''}المساحة الإجمالية ${u.gross||'—'} م² والصافية ${u.net||'—'} م². باقي المبنى يظهر شبحيًا لتبقى الشقة في سياقها.`;}},
     {t:'التشطيبات: الأرضيات',unit:'1-1',focus:{u:'1-1'},k:0.8,dir:[-0.25,0.95,0.4],lens:'finishF',x:()=>'أرضيات الشقة حسب جدول A500: بورسلين F4 للمعيشة والنوم، وسيراميك F2 للحمامات، وسيراميك F1 للمطبخ. الألوان هنا لتمييز الرموز لا للخامات.'},
     {t:'الخدمات فوق السقف',unit:'1-1',focus:{u:'1-1'},k:0.8,dir:[-0.35,0.8,0.5],lens:'system',x:()=>'الخدمات داخل الشقة: مجاري التكييف ووحدات FCU وأنابيب المياه والإطفاء والتمديدات الكهربائية. مناسيبها فوق السقف المستعار افتراضية وتحتاج الأز-بيلت.'}]},
   {id:'mep',t:'الخدمات فوق السقف',d:'تكييف ومياه وكهرباء والتعارضات',steps:[
     {t:'دور نموذجي بالخدمات',levels:['2'],layers:['M','E','P','S'],lens:'system',focus:{l:'2'},dir:D_FAR,x:()=>`الدور الثاني بالخدمات والهيكل: ${N(n({c:'M.duct',l:'2'}))} قطعة مجرى هواء و${N(n({c:'M.pipe',l:'2'}))} قطعة أنابيب مياه مبردة و${N(n({c:'P.',l:'2'}))} عنصر صحي وإطفاء. الألوان حسب النظام.`},
     {t:'التعارضات المؤكدة',issues:'clash',x:()=>`التعارضات: ${N((M.inventory&&M.inventory.issues.clash.c)||0)} مؤكدًا و${N((M.inventory&&M.inventory.issues.clash.k)||0)} مرشحًا لاختلاف المنسوب. الدبابيس في المجسم تُظهر مواضعها، والضغط على دبوس يفتح تفاصيله.`}]},
   {id:'base',t:'القبو والخزانات',d:'موقف السيارات والخزانات',steps:[
     {t:'البدروم: موقف السيارات',levels:['B'],lens:'finishF',focus:{c:'S.',l:'B'},dir:D_FAR,x:()=>{ const a=c=>(M.finq&&M.finq[c]&&M.finq[c].area)||0, csp=a('CSP'), boq=M.fin&&M.fin.CSP?M.fin.CSP[4]:0; return `أرضية البدروم مقسّمة بطبقات A101 نفسها: ممر CSP-3 (${N(a('CSP-3'))} م²) ومواقف CSP-4 (${N(a('CSP-4'))} م²) ومنحدر CSP-2 (${N(a('CSP-2'))} م²) — مجموعها ${N(csp)} م² مقابل ${N(boq)} م² في بند BOQ الواحد؛ ومسار المشاة F13 رصف إنترلوك (${N(a('F13'))} م² مقابل ${M.fin&&M.fin.F13?N(M.fin.F13[4]):'—'}). وردهة المصاعد غرفة مرسومة 540×380 سم (20.62 م² في المخطط).`; }},
     {t:'الخزانات',levels:['B'],hl:{c:'P.tank'},focus:{c:'P.tank'},dir:[-0.45,0.8,0.6],x:()=>`الخزانات الخرسانية تحت الأرض (A2500): ${N(n({c:'P.tank',t:'tank_water'}))} خزانات ماء بجدرانها ودرجها وفتحاتها. الخرسانة هنا هي حدود الخزان؛ تعارضها مع الهيكل مذكور في مركز المتابعة.`}]},
   {id:'trust',t:'ما يمكن الاعتماد عليه',d:'درجات موثوقية البيانات والتخمينات',steps:[
     {t:'موثوقية العناصر',lens:'grade',view:'persp',x:()=>`${pc('d')}% من العناصر موثّقة من المخططات و${pc('v')}% مشتقة بقاعدة معلومة و${pc('a')}% تخمين و${pc('s')}% إخراجي للعرض. التلوين هنا حسب أسوأ محور (الموضع أو المنسوب أو المواصفة).`},
     {t:'التخمينات',lens:'guess',view:'persp',x:()=>'التلوين حسب ثقة التخمين: الأجهزة التي نُقلت لأصحّ مضيف بثقة عالية/متوسطة/منخفضة، وما غُطّي بافتراض عام على نوعه.'},
     {t:'قائمة التخمينات',issues:'guess',x:()=>`في «مركز المتابعة» ${N((M.guesses&&M.guesses.rules.length)||0)} افتراضًا و${N((M.guesses&&M.guesses.items.length)||0)} قرارًا فرديًا بصيغة «قبل ← بعد»؛ تبقى تخمينًا حتى تُطابَق بمخططات الأز-بيلت.`}]}
  ];
  /* ---------------- state ---------------- */
  let T=null,i=0,play=null,saved=null; const bar=document.createElement('div'); bar.id='tourBar'; bar.setAttribute('role','region'); bar.setAttribute('aria-label','جولة موجّهة'); bar.hidden=true; view.appendChild(bar);
  function snapshot(){ return {lv:Object.assign({},lvlVis),cat:Object.assign({},catVis),lens:LENS?LENS.mode:'off',pos:camera.position.clone(),tgt:controls.target.clone()}; }
  function reset(){ clearHL(); setGhost(false); if(isoActive()) exitIso(true); if(LENS&&LENS.mode!=='off') setLens('off'); if(window.ISSUES&&ISSUES.active) ISSUES.close();
    M.levels.forEach(l=>setLvlVis(l.id,true)); Object.keys(CATS).forEach(c=>setCatVis(c,true)); applyVis(); }
  function frame(st){
    if(st.view){ viewPreset(st.view); return; }
    if(st.focus){ const idx=sel(st.focus); if(idx.length){ const b=bboxOf(idx); flyToBox(st.k?{c:b.c,r:b.r*st.k}:b,st.dir||D_FAR); } return; }
    if(st.levels&&st.levels.length===1){ const idx=sel({l:st.levels[0]}).filter(k=>els[k].c[0]!=='A'||els[k].c==='A.wall'); if(idx.length) flyToBox(bboxOf(idx),st.dir||D_FAR); } }
  function show(k){
    i=Math.max(0,Math.min(T.steps.length-1,k)); const st=T.steps[i]; reset(); if(window.ISSUES&&ISSUES.suspend) ISSUES.suspend(!st.issues);
    if(st.levels) M.levels.forEach(l=>setLvlVis(l.id,st.levels.indexOf(l.id)>=0));
    if(st.layers) Object.keys(CATS).forEach(c=>setCatVis(c,st.layers.indexOf(CATS[c].layer)>=0));
    applyVis();
    if(st.unit) isolate(st.unit);
    if(st.lens&&LENS) setLens(st.lens);
    if(st.hl){ const idx=sel(st.hl); if(idx.length) highlight(idx,0x2f7bff,true,0.4); }
    if(st.issues&&window.ISSUES){ ISSUES.open(st.issues,{view:'list'}); if(matchMedia('(min-width:861px)').matches&&window.openSec) window.openSec('pIssues',{scroll:true}); }
    frame(st); document.body.classList.remove('panel-open'); wake(2500); render(); }
  function render(){
    const st=T.steps[i]; let txt=''; try{ txt=st.x?st.x():''; }catch(e){ txt=''; }
    bar.innerHTML='<div class="tb-h"><b>'+esc(T.t)+'</b><span class="tb-n">'+(i+1)+' / '+T.steps.length+'</span><button type="button" class="tb-x" data-t="stop" aria-label="إنهاء الجولة" title="إنهاء الجولة (Esc)">×</button></div>'
      +'<div class="tb-b"><h5>'+esc(st.t)+'</h5><p>'+esc(txt)+'</p></div>'
      +'<div class="tb-c"><button type="button" class="mini" data-t="prev"'+(i===0?' disabled':'')+'>› السابق</button><button type="button" class="mini pri" data-t="play">'+(play?'⏸ إيقاف مؤقت':'▶ تشغيل')+'</button><button type="button" class="mini" data-t="next"'+(i===T.steps.length-1?' disabled':'')+'>التالي ‹</button><span class="tb-dots">'+T.steps.map((s,k)=>'<span class="'+(k===i?'on':'')+'"></span>').join('')+'</span></div>'; }
  function tick(){ if(!T||!play) return; if(i>=T.steps.length-1){ setPlay(false); return; } show(i+1); play=setTimeout(tick,9000); }
  function setPlay(on){ clearTimeout(play); play=null; if(on&&T){ play=setTimeout(tick,9000); } if(T) render(); }
  function start(id){
    const t=TOURS.find(x=>x.id===id); if(!t) return; if(closeMenus) closeMenus(); if(T) stop(true); T=t; saved=snapshot(); document.body.classList.add('tour-on'); bar.hidden=false; show(0); }
  function stop(quiet){
    if(!T) return; clearTimeout(play); play=null; const s=saved; T=null; bar.hidden=true; bar.innerHTML=''; document.body.classList.remove('tour-on');
    reset(); if(window.ISSUES&&ISSUES.suspend) ISSUES.suspend(false); if(s){ M.levels.forEach(l=>setLvlVis(l.id,s.lv[l.id]!==false)); Object.keys(CATS).forEach(c=>setCatVis(c,s.cat[c]!==false)); applyVis(); if(LENS&&s.lens&&s.lens!=='off') setLens(s.lens); if(!quiet) flyTo(s.pos,s.tgt); }
    saved=null; wake(1500); }
  bar.addEventListener('click',ev=>{ const b=ev.target.closest('[data-t]'); if(!b||b.disabled) return; const a=b.dataset.t;
    if(a==='stop') stop(); else if(a==='prev'){ setPlay(false); show(i-1); } else if(a==='next'){ setPlay(false); show(i+1); } else if(a==='play') setPlay(!play); });
  /* entry points: the «⋯» menu */
  const mm=$('moreMenu'); if(mm){ const hr=document.createElement('hr'); mm.appendChild(hr); TOURS.forEach(t=>{ const b=document.createElement('button'); b.type='button'; b.textContent='جولة: '+t.t; b.title=t.d; b.onclick=()=>start(t.id); mm.appendChild(b); }); }
  return {start,stop,list:TOURS.map(t=>({id:t.id,t:t.t,d:t.d,n:t.steps.length})),get active(){return !!T;},get step(){return i;},go:k=>{ if(T) show(k); }};
}
window.initTours=initTours;
})();
