/* Project fulfilment workspace: every model type, source evidence and coordination results.
   Classification, isolation/context and evidence-on-demand follow the patterns documented
   in docs/DESIGN_PROJECT_REVIEW.md. A citation is never treated as a geometric check. */
(function(){
'use strict';
const LANES={scoped_overlap:['تداخل أغلفة ضمن فحص الاستكمال','◇','info'],confirmed_model_error:['اختلاف مؤكد بين المجسم والمخطط','!','danger'],confirmed:['تعارض مثبت من المصدر','■','danger'],confirmed_plan:['عبور مثبت بالمسقط؛ تفصيل الفتحة يحتاج حسمًا','■','danger'],candidate_height:['مرشح اختلاف منسوب / شكل','◆','warn'],model_collision:['تداخل في المجسم يحتاج تحقق المصدر','●','info'],source_elevation:['اختلاف منسوب مثبت بين المصادر','↕','danger'],source_conflict:['اختلاف بين المخططات','↔','warn'],corrected:['الشكل الحالي — افتراضي مؤقت','○','muted'],source_gap:['تفصيل أو اتصال غير مثبت','?','muted']};
const BASIS={source_checked:'XY مفحوص مستقلًا من PDF',legacy_extract_match:'اتساق تاريخي فقط — لا اعتماد مصدر',derived:'هندسة مشتقة',unverified:'لم تتحقق الهندسة مستقلًا'};
function initProjectReview(ctx){
 const {M,setSourceAlternatives,$,esc,LVL,setLens,openSec,bboxOf,flyToBox,ensureVisible,highlight,addHL,clearHL,setGhost,showDrawer,hideDrawer,toast,wake}=ctx;
 const box=$('projectReviewBox');if(!box)return;
 const idMap=new Map(M.els.map((e,i)=>[e.id,i])),types=M.types||{},coverage=M.componentReview||{},review=M.coordinationReview||{};
 const proof=new Map((coverage.rows||[]).map(r=>[r.id,r])),groupMap=new Map();
 
 M.els.forEach((e,i)=>{const key=e.c+'|'+e.t;if(!groupMap.has(key))groupMap.set(key,{key,c:e.c,t:e.t,ids:[]});groupMap.get(key).ids.push(i);});
 const groups=[...groupMap.values()].sort((a,b)=>a.c.localeCompare(b.c)||a.t.localeCompare(b.t));
 const states={tab:'coordination',discipline:'',level:'',basis:'',lane:'',match:'',q:'',limit:36,selected:null,mode:'context'};
 const names=new Map(M.layers.flatMap(l=>l.subs));
 const levelName=k=>(LVL[k]||{}).name||k||'عام';
 const typeName=e=>(types[e.t]||{}).n||e.t;
 const norm=t=>String(t||'').toLocaleLowerCase().replace(/[أإآ]/g,'ا').replace(/ى/g,'ي');
 const sourceOf=e=>(e.s||[]).map(i=>M.sp[i]).filter(Boolean);
 const basisOf=e=>proof.get(e.id)?.status||coverage.status_by_id?.[e.id]||'unverified';
 const num=v=>Number(v||0).toLocaleString('en');
 function baseMatch(e){return (!states.discipline||e.c[0]===states.discipline)&&(!states.level||e.l===states.level)&&(!states.q||norm([e.id,e.mark,e.t,typeName(e),e.c,...sourceOf(e)].join(' ')).includes(norm(states.q)));}
 const issues=(review.issues||[]).map((d,i)=>({kind:'clash',index:i,id:d.id,lane:d.classification?.lane||'model_collision',level:d.level,title:((M.els[idMap.get(d.ea)]||{}).t?typeName(M.els[idMap.get(d.ea)]):d.ea)+' × '+((M.els[idMap.get(d.eb)]||{}).t?typeName(M.els[idMap.get(d.eb)]):d.eb),note:d.classification?.reason_ar||'',refs:d.source?.refs||[...new Set((d.source?.elements||[]).flatMap(e=>e.refs||[]))],ids:[d.ea,d.eb],detail:d}));
 // Supplemental envelope witnesses stay separate from the legacy clash list.
 (M.completionCoordination?.rows||[]).filter(d=>!d.existing_clash_id).forEach((d,i)=>{
  const members=[d.ea,d.eb].map(id=>M.els[idMap.get(id)]).filter(Boolean);
  issues.push({kind:'clash',index:(review.issues||[]).length+i,id:d.id,lane:'scoped_overlap',level:d.level,
   title:members.map(typeName).join(' × '),note:d.note_ar,refs:[...new Set(members.flatMap(sourceOf))],ids:[d.ea,d.eb],
   detail:{...d,source:{elements:members.map(e=>({id:e.id,refs:sourceOf(e),xy_basis:'source_reference_without_independent_bounds_proof',height_basis:'not_independently_verified',height_assumptions:[e.a?.assumed||'راجع نطاق مصدر الجسم والمنسوب']})),limitations:[M.completionCoordination.limit_ar,'شاهد تداخل أغلفة فقط؛ لا يحسم اتصالًا مقصودًا أو خطأ تنفيذ ولا يجيز نقل العنصر.']}}});
 });
 const sourceGroups=new Map((M.sourceConflictGroups||[]).flatMap(g=>(g.issue_ids||[g.id]).map(id=>[id,g])));
 const reviewedSources=new Map((review.source_conflicts||[]).map(d=>[d.id,d]));
 (M.drawingIssues||[]).forEach((d,i)=>{const verified=reviewedSources.get(d.id)||d;issues.push({kind:'source',index:i,id:d.id,lane:verified.zconflict?'source_elevation':d.status==='model_candidate'?'model_collision':d.status,level:d.level,title:d.title,note:d.note,refs:[d.source],ids:d.elements||[],detail:verified});});
 (M.sourceConflictGroups||[]).filter(g=>!issues.some(d=>(g.issue_ids||[g.id]).includes(d.id))).forEach((g,i)=>issues.push({kind:'alternative',index:i,id:g.id,lane:'source_conflict',level:g.level,title:g.title||g.id,note:g.note_ar||'',refs:g.sources.map(s=>s.file+' ص '+s.page),ids:g.sources.flatMap(s=>s.element_ids||[]),detail:g}));
 function issueMatch(d){const es=d.ids.map(id=>M.els[idMap.get(id)]).filter(Boolean);return (!states.lane||d.lane===states.lane)&&(!states.level||d.level===states.level)&&(!states.discipline||es.some(e=>e.c[0]===states.discipline))&&(!states.q||norm([d.id,d.title,d.note,...d.refs].join(' ')).includes(norm(states.q)));}
 function badge(key){const p=LANES[key]||[key,'●','muted'];return '<span class="pr-badge '+p[2]+'">'+p[1]+' '+esc(p[0])+'</span>';}
 function filters(){return '<div class="pr-filters"><label>التخصص<select data-pr-filter="discipline"><option value="">كل التخصصات</option>'+M.layers.map(l=>'<option value="'+esc(l.id)+'"'+(l.id===states.discipline?' selected':'')+'>'+esc(l.name)+'</option>').join('')+'</select></label><label>المستوى<select data-pr-filter="level"><option value="">كل المستويات</option>'+M.levels.map(l=>'<option value="'+esc(l.id)+'"'+(l.id===states.level?' selected':'')+'>'+esc(l.name)+'</option>').join('')+'</select></label></div><label class="pr-search">البحث في المكونات والمصادر<input type="search" id="prQuery" placeholder="اسم، نوع، معرّف أو ورقة…" value="'+esc(states.q)+'" autocomplete="off"></label>';}
 function shell(){
  box.innerHTML='<header class="pr-hero"><small>من المخطط إلى المجسم</small><h3>مطابقة المشروع</h3><p>الأشكال من مواضعها المرسومة. عند اختلاف المصادر تُعرض بدائلها، والشكل الحالي افتراضي مؤقت.</p><div class="pr-metrics"><span><b>'+num(M.els.length)+'</b> عنصر</span><span><b>'+num(groups.length)+'</b> مجموعة نوعية</span><span><b>'+num(M.levels.length)+'</b> مستويات</span></div></header><div class="pr-tabs" role="tablist" aria-label="مراجعة المشروع">'+[['components','كل المكونات'],['coordination','قائمة التعارضات'],['sources','سجل المصدر']].map(([k,n])=>'<button type="button" role="tab" aria-selected="'+(states.tab===k)+'" data-pr-tab="'+k+'">'+n+'</button>').join('')+'</div>'+filters()+'<div id="prSummary" class="pr-summary" aria-live="polite"></div><div id="prControls"></div><div id="prResults"></div><div class="pr-actions"><button type="button" class="mini" data-pr-act="reset">إزالة الفلاتر</button><button type="button" class="mini" data-pr-act="exit">إنهاء عرض المراجعة</button><button type="button" class="mini" data-pr-act="export">تصدير القائمة CSV</button></div>';
  renderResults();
 }
 function renderResults(){
  const out=$('prResults'),controls=$('prControls');if(!out)return;
  if(states.tab==='components'){
   controls.innerHTML='';
   const rows=groups.map(g=>({...g,visible:g.ids.filter(i=>baseMatch(M.els[i]))})).filter(g=>g.visible.length),total=rows.reduce((s,g)=>s+g.visible.length,0);
   $('prSummary').textContent=num(total)+' عنصرًا في '+num(rows.length)+' مجموعة مطابقة للفلاتر';
   out.innerHTML=rows.slice(0,states.limit).map(g=>{
    const counts={};g.visible.forEach(i=>{const k=basisOf(M.els[i]);counts[k]=(counts[k]||0)+1;});const ls=[...new Set(g.visible.map(i=>M.els[i].l))];
    return '<article class="pr-card"><div class="pr-card-top"><b>'+esc((types[g.t]||{}).n||g.t)+'</b><span class="pr-count">'+num(g.visible.length)+'</span></div><small>'+esc(names.get(g.c)||g.c)+' · '+ls.map(levelName).map(esc).join('، ')+'</small><div class="pr-actions"><button type="button" class="mini pri" data-pr-group="'+esc(g.key)+'">فحص هذه المكونات</button></div></article>';
   }).join('')+more(rows.length);
  }else{
   const wantSource=states.tab==='sources';const rows=issues.filter(d=>(!wantSource||d.kind==='source')&&issueMatch(d));const counts={};(wantSource?issues.filter(d=>d.kind==='source'):issues).forEach(d=>counts[d.lane]=(counts[d.lane]||0)+1);
   controls.innerHTML='<div class="pr-lanes" role="group" aria-label="نوع النتيجة"><button type="button" data-pr-lane="" aria-pressed="'+!states.lane+'">الكل</button>'+Object.keys(LANES).filter(k=>counts[k]).map(k=>'<button type="button" data-pr-lane="'+k+'" aria-pressed="'+(states.lane===k)+'">'+badge(k)+' <b>'+num(counts[k])+'</b></button>').join('')+'</div>';
   $('prSummary').textContent=num(rows.length)+' نتيجة مطابقة للفلاتر';
   out.innerHTML='<div class="pr-note">المؤكد من المصدر يحتاج إثبات الهندسة والمنسوب. التداخل الهندسي في المجسم وحده لا يثبت تعارضًا في التنفيذ.</div>'+rows.slice(0,states.limit).map(d=>'<article class="pr-card">'+badge(d.lane)+'<b class="pr-title">'+esc(d.title)+'</b><small>'+esc(levelName(d.level))+' · <bdi>'+esc(d.id)+'</bdi></small><p>'+esc(d.note)+'</p><small>'+d.refs.map(esc).join(' · ')+'</small><button type="button" class="mini pri" data-pr-issue="'+esc(d.kind+':'+d.index)+'">الموضع والدليل</button></article>').join('')+more(rows.length);
   if(!review.issues?.length&&!wantSource)out.innerHTML='<div class="pr-note">تقرير التدقيق الهندسي المستقل لم يُضمّن في هذا الإصدار بعد. حالات مراجعة المصادر أدناه.</div>'+out.innerHTML;
  }
 }
 function more(n){return n>states.limit?'<button type="button" class="pr-more" data-pr-act="more">عرض '+Math.min(36,n-states.limit)+' نتيجة أخرى من '+num(n)+'</button>':n===0?'<div class="pr-empty">لا توجد نتائج لهذه الفلاتر. غيّر المستوى أو أزل الفلاتر.</div>':'';}
 function activate(ids,mode){
  const inds=ids.map(id=>idMap.get(id)).filter(i=>i!==undefined);if(!inds.length){toast('لا توجد هندسة محددة لهذه الحالة؛ راجع دليل المصدر');return;}
  if(!states.presentation){states.presentation={};[['expl','0'],['clipY','30'],['clipX','46']].forEach(([id,value])=>{const el=$(id);if(el){states.presentation[id]=el.value;if(el.value!==value){el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));}}});}
  window.ISSUES?.close();window.ISSUES?.suspend(true);window.__dbg?.CLASH.endFocus();clearHL();setGhost(false);
  const selectedColor=states.selected?.sourceColor||'#c76422';const map=new Map(inds.map((i,n)=>[i,!states.selected?.sourceColor&&ids.length===2?n+1:1]));setLens('custom',{classes:[{n:'المصدر المختار للعرض',c:selectedColor},{n:'المكوّن B',c:'#126eae'}],map,hideRest:mode==='isolate',label:'فحص المكوّن ومصدره'});
  inds.forEach(ensureVisible);if(mode==='context')setGhost(true,.12,[...new Set(inds.map(i=>M.els[i].l))]);
  if(inds.length<=250){highlight([inds[0]],parseInt(selectedColor.slice(1),16),true,.45);if(inds.length>1)addHL(inds.slice(1),states.selected?.sourceColor?parseInt(selectedColor.slice(1),16):0x126eae,true,.3);}
  const p=states.selected?.point;
  if(p&&states.selected.frame!=='pair'){const [xc,yc,z]=p,x=xc/100,y=-yc/100;flyToBox({mn:[x-1.5,z-1,y-1.5],mx:[x+1.5,z+1,y+1.5],c:[x,z,y],r:2.35},[-.45,.65,.9]);}
  else flyToBox(bboxOf(inds),[-.45,.65,.9]);document.body.classList.remove('panel-open');wake();
 }
 function focusGroup(key){
  setSourceAlternatives();const g=groupMap.get(key);if(!g)return;const inds=g.ids.filter(i=>baseMatch(M.els[i]));if(!inds.length)return;
  states.selected={kind:'group',ids:inds.map(i=>M.els[i].id),key};activate(states.selected.ids,states.mode);
  const t=types[g.t]||{},sources=[...new Set(inds.flatMap(i=>sourceOf(M.els[i])))],assumptions=[...new Set(inds.map(i=>M.els[i].a?.assumed).filter(Boolean))];
  let h='<section dir="rtl" class="pr-detail"><h3>'+esc(t.n||g.t)+'</h3><p>'+num(inds.length)+' عنصرًا · '+esc(names.get(g.c)||g.c)+'</p>'+viewActions()+'<h4>خصائص النوع</h4>'+table(t.sp||[])+'<h4>المصدر والافتراضات</h4><p>'+sources.map(esc).join('<br>')+'</p>'+(assumptions.length?'<ul>'+assumptions.map(a=>'<li>'+esc(a)+'</li>').join('')+'</ul>':'')+'<h4>العناصر ومواضعها</h4>';
  h+='<div class="pr-element-list">'+inds.slice(0,120).map(i=>{const e=M.els[i],p=proof.get(e.id);return '<button type="button" data-pr-element="'+esc(e.id)+'"><bdi>'+esc(e.id)+'</bdi><span>'+esc(levelName(e.l))+'</span>'+(p?.findings?.length?'<small>'+esc(JSON.stringify(p.findings))+'</small>':'')+'</button>';}).join('')+'</div>'+(inds.length>120?'<p>عرض أول 120 عنصرًا؛ ضيق الفلتر إلى مستوى واحد أو صدر القائمة الكاملة.</p>':'')+'</section>';
  showDrawer(h,bindDrawer);
 }
 function value(v){
  if(typeof v==='number')return '<bdi dir="ltr">'+esc(Number(v.toFixed(4)))+'</bdi>';
  if(Array.isArray(v)&&v.every(x=>typeof x==='number'))return '<bdi dir="ltr">['+v.map(n=>esc(Number(n.toFixed(4)))).join(', ')+']</bdi>';
  if(Array.isArray(v)&&v.every(x=>typeof x==='string'))return v.map(s=>'<div>'+esc(s)+'</div>').join('')||'—';
  if(typeof v==='object')return '<details><summary>عرض البيانات التفصيلية</summary><pre dir="ltr" class="pr-data">'+esc(JSON.stringify(v,null,2))+'</pre></details>';
  return esc(v);
 }
 function table(rows){return '<table class="ctab">'+rows.map(([k,v])=>'<tr><th>'+esc(k)+'</th><td>'+value(v)+'</td></tr>').join('')+'</table>';}
 function viewActions(){return '<div class="pr-actions"><button class="mini" type="button" data-pr-view="context">إظهار مع السياق</button><button class="mini" type="button" data-pr-view="isolate">عزل المكونات</button><button class="mini" type="button" data-pr-view="fit">'+(states.selected?.point?'موضع التقاطع':'إعادة توجيه')+'</button>'+(states.selected?.point?'<button class="mini" type="button" data-pr-view="pair">كامل الطرفين</button>':'')+'<button class="mini" type="button" data-pr-view="exit">إنهاء</button></div>';}
 function focusIssue(key){
  const [kind,ix]=key.split(':'),d=issues.find(d=>d.kind===kind&&d.index===+ix);if(!d)return;
  const sourceGroup=sourceGroups.get(d.id)||(d.kind==='alternative'?d.detail:null);setSourceAlternatives(sourceGroup?.sources.flatMap(s=>s.element_ids||[])||[],false);
  const witness=d.detail.geometry?.witness_xy_cm,witnessZ=d.detail.geometry?.witness_z_m;
  states.selected={kind:'issue',ids:d.ids,key,point:witness&&witnessZ!=null?[...witness,witnessZ]:null,frame:'point',sourceGroup,alternativesShown:false};
  if(d.ids.some(id=>idMap.has(id)))activate(d.ids,states.mode);
  else if(d.detail.xy_cm){const [xc,yc]=d.detail.xy_cm,z=d.detail.z_m??LVL[d.level]?.ffl??0,x=xc/100,y=-yc/100;flyToBox({mn:[x-1,z-.5,y-1],mx:[x+1,z+.5,y+1],c:[x,z,y],r:1.5});document.body.classList.remove('panel-open');}
  const data=d.detail,geometry=data.geometry||{},source=data.source||{};
  const basisNames={source_metadata_present:'بيانات موضع مصدر موجودة؛ تحقق الحدود مستقل',source_reference_without_independent_bounds_proof:'مرجع مصدر دون تحقق مستقل للحدود',explicit_assumption:'منسوب مفترض صراحة',not_independently_verified:'لم يتحقق مستقلًا'};
  const rows=d.kind==='clash'?[['شاهد التداخل في XY سم',geometry.witness_xy_cm],['Z عند شاهد التداخل م',geometry.witness_z_m],['نطاق Z للتداخل م',geometry.z_overlap_m],['إثبات الحجم',geometry.positive_volume_proved?'تقاطع إيجابي مثبت في المجسم':'لم يثبت؛ راجع حدود هندسة القراءة'],['أساس XY',(source.elements||[]).map(e=>e.id+': '+(basisNames[e.xy_basis]||e.xy_basis))],['أساس المنسوب',(source.elements||[]).map(e=>e.id+': '+(basisNames[e.height_basis]||e.height_basis))],['فرضيات المنسوب',(source.elements||[]).flatMap(e=>e.height_assumptions||[])],['تدقيق هذه الحالة',data.case_audit_ar],['حدود الدليل',source.limitations]]:[['XY سم',data.xy_cm],['Z م',data.z_m],['قيم المنسوب في المصدر',data.z_source_comparison?.sources],['فرق المنسوب بالمتر',data.z_source_comparison?.difference_m],[d.lane==='corrected'?'قبل التصحيح':'البيانات السابقة',data.before],[d.lane==='corrected'?'بعد التصحيح':'البيانات والأبعاد محل المراجعة',data.after]];
  showDrawer('<section dir="rtl" class="pr-detail">'+badge(d.lane)+'<h3>'+esc(d.title)+'</h3><p>'+esc(d.note)+'</p>'+viewActions()+sourceChips(sourceGroup)+table([['المعرّف',d.id],['المستوى',levelName(d.level)],...rows.filter(r=>r[1]!=null),['المصدر',d.refs]])+'<h4>المكونات المرتبطة</h4>'+d.ids.map(id=>'<button class="mini" type="button" data-pr-element="'+esc(id)+'"><bdi>'+esc(id)+'</bdi></button>').join('')+'<p>نتيجة محلية مرتبطة بهذا الإصدار. حسم المنسوب أو اعتماد تغيير التصميم لا يُستنتج من اللون أو تغيير حالة المراجعة.</p></section>',bindDrawer);
 }
 function showElement(id){
  const e=M.els[idMap.get(id)];if(!e)return;
  const old=states.selected;states.selected={kind:'element',ids:[id],sourceGroup:old?.sourceGroup,sourceColor:old?.sourceColor};
  activate([id],states.mode);
  showDrawer('<section dir="rtl" class="pr-detail"><h3>'+esc(typeName(e))+'</h3>'+viewActions()+table([['المعرّف',id],['النوع',typeName(e)],['المصدر والورقة ورقم الرسم',e.a?.alt_source||sourceOf(e)],...((e.a?.assumed||types[e.t]?.asm?.length)?[['الافتراض',e.a?.assumed||types[e.t].asm]]:[])])+'</section>',bindDrawer);
 }
 function sourceChips(g){if(!g)return '';
  return '<h4>مصادر التعارض</h4><div class="pr-actions">'+g.sources.map((s,i)=>'<button type="button" class="mini" style="border-inline-start:5px solid '+esc(s.color)+'" data-pr-source="'+i+'"><bdi>'+String(i+1)+'</bdi> · '+esc(s.label||s.file)+' · ص '+esc(s.page)+' · '+esc(Array.isArray(s.drawing)?s.drawing.join('، '):s.drawing||'')+'</button>').join('')+'</div><button type="button" class="mini" data-pr-alternatives aria-pressed="false">إظهار البدائل</button><div id="prSourceValues">'+g.sources.map(s=>'<h4 style="color:'+esc(s.color)+'">'+esc(s.label||s.file)+'</h4>'+table(Object.entries(s.values||{}))+(s.unrepresented_reason?'<p>'+esc(s.unrepresented_reason)+'</p>':'')).join('')+'</div><div id="prConflictEvidence"></div>';
 }
 async function showConflictEvidence(g){
  const box=$('prConflictEvidence');if(!box||!g)return;box.textContent='تحميل أدلة التعارض…';
  try{const all=await window.loadConflictEvidence();const evidence=all.groups?.[g.id]||{};box.innerHTML='<h4>أدلة هذا التعارض</h4>'+value(evidence);
   for(const ref of evidence.image_refs||[]){const im=all.images?.[ref];if(im){const el=document.createElement('img');el.src=im;el.alt='قصاصة المصدر '+ref;el.style.cssText='max-width:100%;height:auto';box.appendChild(el);}}
  }catch(e){box.textContent='تعذر تحميل الدليل: '+e.message;}
 }
 function bindDrawer(el){el.addEventListener('click',ev=>{
  const v=ev.target.closest('[data-pr-view]');if(v){if(v.dataset.prView==='exit')exit();else if(states.selected){if(v.dataset.prView==='pair'||v.dataset.prView==='fit')states.selected.frame=v.dataset.prView==='pair'?'pair':'point';else states.mode=v.dataset.prView;activate(states.selected.ids,states.mode);}return;}
  const source=ev.target.closest('[data-pr-source]');if(source){const selected=states.selected,g=selected?.sourceGroup,src=g?.sources[+source.dataset.prSource];if(src){selected.ids=src.element_ids||[];selected.sourceColor=src.color;selected.point=null;selected.alternativesShown=true;setSourceAlternatives(selected.ids);activate(selected.ids,states.mode);const toggle=el.querySelector('[data-pr-alternatives]');if(toggle){toggle.setAttribute('aria-pressed','true');toggle.textContent='إخفاء البدائل';}}return;}
  const toggle=ev.target.closest('[data-pr-alternatives]');if(toggle){const selected=states.selected;if(selected?.sourceGroup){selected.alternativesShown=!selected.alternativesShown;if(!selected.alternativesShown){clearHL();setLens('off');}setSourceAlternatives(selected.sourceGroup.sources.flatMap(s=>s.element_ids||[]),selected.alternativesShown);toggle.setAttribute('aria-pressed',String(selected.alternativesShown));toggle.textContent=selected.alternativesShown?'إخفاء البدائل':'إظهار البدائل';}return;}
  if(ev.target.closest('[data-pr-evidence]')){showConflictEvidence(states.selected?.sourceGroup);return;}
  const b=ev.target.closest('[data-pr-element]');if(b)showElement(b.dataset.prElement);
 });}
 function exit(opt){setSourceAlternatives();clearHL();setGhost(false);setLens('off');window.ISSUES?.suspend(false);hideDrawer();if(states.presentation){Object.entries(states.presentation).forEach(([id,value])=>{const el=$(id);if(el&&el.value!==value){el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));}});states.presentation=null;}states.selected=null;if(!opt?.quiet)toast('انتهى عرض المراجعة وأعيد القص وتفكيك الطوابق');wake();}
 function exportCSV(){const rows=states.tab==='components'?M.els.filter(baseMatch).map(e=>[e.id,typeName(e),e.c,e.l,sourceOf(e).join(' / '),e.a?.assumed||'']):issues.filter(d=>(states.tab!=='sources'||d.kind==='source')&&issueMatch(d)).map(d=>[d.id,d.title,d.lane,d.level,d.note,d.refs.join(' / '),d.ids.join(' / ')]);const heads=states.tab==='components'?['المعرّف','النوع','الفئة','المستوى','المصدر','الافتراض']:['المعرّف','العنوان','نوع النتيجة','المستوى','السبب','المصدر','العناصر'];const csv='\uFEFF'+[heads,...rows].map(r=>r.map(v=>'"'+String(v??'').replace(/"/g,'""')+'"').join(',')).join('\r\n');const u=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=u;a.download='C4-'+states.tab+'-review.csv';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);toast('صُدّرت '+num(rows.length)+' نتيجة من الفلاتر الحالية');}
 let timer;
 box.addEventListener('input',ev=>{if(ev.target.id==='prQuery'){states.q=ev.target.value;states.limit=36;clearTimeout(timer);timer=setTimeout(renderResults,160);}});
 box.addEventListener('change',ev=>{const k=ev.target.dataset.prFilter;if(k){states[k]=ev.target.value;states.limit=36;renderResults();}});
 box.addEventListener('click',ev=>{const b=ev.target.closest('button');if(!b)return;
  if(b.dataset.prTab){states.tab=b.dataset.prTab;states.limit=36;states.lane='';shell();}
  else if(b.hasAttribute('data-pr-lane')){states.lane=b.dataset.prLane;states.limit=36;renderResults();}
  else if(b.hasAttribute('data-pr-match')){states.match=b.dataset.prMatch;states.limit=36;renderResults();}
  else if(b.dataset.prElement)showElement(b.dataset.prElement);
  else if(b.dataset.prGroup)focusGroup(b.dataset.prGroup);
  else if(b.dataset.prIssue)focusIssue(b.dataset.prIssue);
  else if(b.dataset.prAct==='more'){states.limit+=36;renderResults();}
  else if(b.dataset.prAct==='reset'){Object.assign(states,{q:'',discipline:'',level:'',basis:'',lane:'',match:'',limit:36});shell();}
  else if(b.dataset.prAct==='exit')exit();
  else if(b.dataset.prAct==='export')exportCSV();
 });
 shell();return {open(tab){if(tab)states.tab=tab;openSec('pProject',{scroll:true,only:true});shell();},state(){return {...states,groups:groups.length,issues:issues.length};},exit,focusIssue};
}
window.initProjectReview=initProjectReview;
})();
