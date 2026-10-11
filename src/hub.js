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
  if(M.meta?.owner_render_only){
    const base=M.els.filter(e=>!e.a?.alt),groups=M.sourceConflictGroups||[],systems=M.lifecycle?.systems||[];
    box.innerHTML='<h2>المشروع</h2><div class="kpis"><button class="kpi" data-home="pLayers"><b>'+base.length.toLocaleString('en')+'</b><span>مكوّن</span></button><button class="kpi" data-home="pUnits"><b>'+M.units.length+'</b><span>وحدة</span></button><button class="kpi" data-home="pIssues"><b>'+groups.length+'</b><span>تعارض مصادر</span></button></div><div class="tours"><button class="tourc" data-home="pUnits"><b>استكشف الوحدات</b><span>الأدوار والمساحات</span></button><button class="tourc" data-home="pLife"><b>اختبر الأنظمة</b><span>'+systems.length+' نظامًا</span></button><button class="tourc" data-home="pBuild"><b>بناء المشروع</b><span>عرض المكوّنات بالتتابع</span></button></div><h3>الأدوار</h3><div class="lvstack">'+M.levels.slice().reverse().map(l=>'<button class="lvrow" data-floor="'+esc(l.id)+'"><span class="lvn">'+esc(l.name)+'</span><span>'+base.filter(e=>e.l===l.id).length.toLocaleString('en')+'</span></button>').join('')+'</div><button type="button" class="mini" data-floor="all">المبنى كاملًا</button>';
    box.addEventListener('click',ev=>{const b=ev.target.closest('[data-home],[data-floor]');if(!b)return;if(b.dataset.home==='pBuild')window.PROJECT_BUILD?.open();else if(b.dataset.home)openSec(b.dataset.home);else if(b.dataset.floor==='all')showAllLevels();else onlyLevel(b.dataset.floor);});return;
  }
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

/* Per-element presentation animation. Source positions are never rewritten. */
window.createBuildAnimator=function({THREE,M,groups,elRange,elBB}){
  const width=256,height=Math.ceil(M.els.length/width),state=new Float32Array(width*height*4),centres=new Float32Array(state.length),specs=new Map();
  const texture=data=>{const t=new THREE.DataTexture(data,width,height,THREE.RGBAFormat,THREE.FloatType);t.minFilter=t.magFilter=THREE.NearestFilter;t.needsUpdate=true;return t;};
  const U={uBuildOn:{value:0},uBuildMode:{value:1},uBuildMotion:{value:1},uBuildState:{value:texture(state)},uBuildCentres:{value:texture(centres)},uBuildSize:{value:new THREE.Vector2(width,height)}};
  let ready=false,lastActive=[],running=false;
  const vertex=`attribute vec2 aBuild;uniform float uBuildOn;uniform float uBuildMode;uniform float uBuildMotion;uniform sampler2D uBuildState;uniform sampler2D uBuildCentres;uniform vec2 uBuildSize;varying vec3 vBuild;`;
  const transform=`vBuild=vec3(1.,0.,0.);if(uBuildOn>.5&&aBuild.x>.5){float bi=aBuild.x-1.;vec2 uv=(vec2(mod(bi,uBuildSize.x),floor(bi/uBuildSize.x))+.5)/uBuildSize;vec4 bs=texture2D(uBuildState,uv);vBuild=vec3(bs.r,aBuild.y/65535.,bs.g);if(uBuildMode>1.5&&uBuildMode<2.5){float k=bs.r*bs.r*(3.-2.*bs.r);vec3 c=texture2D(uBuildCentres,uv).xyz;if(uBuildMotion<1.5)transformed.y+=1.8*(1.-k);else if(uBuildMotion<2.5)transformed.y-=1.8*(1.-k);else if(uBuildMotion<3.5)transformed=c+(transformed-c)*max(.001,k);else transformed+=vec3((c.x-18.)*.15,1.2,(c.z+17.)*.15)*(1.-k);}}`;
  const fragment=`uniform float uBuildOn;uniform float uBuildMode;varying vec3 vBuild;`;
  const discard=`if(uBuildOn>.5){if(vBuild.x<=0.)discard;if(uBuildMode<1.5&&vBuild.z>.5){if(vBuild.y>vBuild.x)discard;}else if(uBuildMode>2.5||(uBuildMode<1.5&&vBuild.z<.5)){float noise=fract(sin(dot(floor(gl_FragCoord.xy),vec2(12.9898,78.233)))*43758.5453);if(noise>vBuild.x)discard;}}`;
  function patch(sh){Object.assign(sh.uniforms,U);sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\n'+vertex).replace('#include <begin_vertex>','#include <begin_vertex>\n'+transform);sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\n'+fragment).replace('void main() {','void main() {\n'+discard);}
  function spec(i){
    if(specs.has(i))return specs.get(i);
    const e=M.els[i],b=elBB.subarray(i*6,i*6+6),g=e.g;let s;
    if((g[0]==='t'||g[0]==='d')&&g[1].length>1){
      const paths=[];let length=0;
      for(let j=1;j<g[1].length;j++){const u=g[1][j-1],v=g[1][j],a=[u[0]/100,u[2],-u[1]/100],q=[v[0]/100,v[2],-v[1]/100],d=q.map((n,k)=>n-a[k]),l=Math.hypot(...d);if(l>.0001){paths.push({a,d,l,start:length});length+=l;}}
      s={kind:1,paths,length};
    }else{
      const grow=/^(S\.|A\.(wall|clad|floor|ceil|wfin|cfin|rail|shaft))/.test(e.c);
      const axis=/^(S\.(beam|slab|raft|ramp)|A\.(floor|ceil|cfin))$/.test(e.c)?(b[3]-b[0]>=b[5]-b[2]?0:2):1;
      s={kind:grow?1:0,axis,lo:b[axis],length:Math.max(.001,b[axis+3]-b[axis])};
    }
    specs.set(i,s);return s;
  }
  function along(s,x,y,z){
    if(!s.paths)return Math.max(0,Math.min(1,([x,y,z][s.axis]-s.lo)/s.length));
    let best=Infinity,at=0;
    for(const q of s.paths){const dx=x-q.a[0],dy=y-q.a[1],dz=z-q.a[2],t=Math.max(0,Math.min(1,(dx*q.d[0]+dy*q.d[1]+dz*q.d[2])/(q.l*q.l))),dist=(dx-q.d[0]*t)**2+(dy-q.d[1]*t)**2+(dz-q.d[2]*t)**2;if(dist<best){best=dist;at=(q.start+t*q.l)/s.length;}}
    return at;
  }
  function bindEdges(G,geometry,ids){const base=G.mesh.geometry.attributes.aBuild;if(!base)return;if(geometry.index){geometry.setAttribute('aBuild',base);return;}const data=new Uint16Array(ids.length*2);for(let k=0;k<ids.length;k++){data[k*2]=base.array[ids[k]*2];data[k*2+1]=base.array[ids[k]*2+1];}geometry.setAttribute('aBuild',new THREE.Uint16BufferAttribute(data,2));}
  function prepare(){
    if(ready)return;ready=true;
    for(const G of Object.values(groups))if(G.mesh)G.mesh.geometry.setAttribute('aBuild',new THREE.Uint16BufferAttribute(new Uint16Array(G.posArr.length/3*2),2));
    M.els.forEach((e,i)=>{const r=elRange[i],G=groups[r?.gk];if(!G?.mesh)return;const s=spec(i),a=G.mesh.geometry.attributes.aBuild.array,b=elBB.subarray(i*6,i*6+6);centres.set([(b[0]+b[3])/2,(b[1]+b[4])/2,(b[2]+b[5])/2,0],i*4);state[i*4+1]=s.kind;
      for(let j=r.start*3;j<(r.start+r.count)*3;j++){a[j*2]=i+1;a[j*2+1]=Math.round(along(s,G.posArr[j*3],G.posArr[j*3+1],G.posArr[j*3+2])*65535);}
    });
    for(const G of Object.values(groups))if(G.mesh)for(const c of G.mesh.children)if(c.userData.buildVertices)bindEdges(G,c.geometry,c.userData.buildVertices);
    U.uBuildCentres.value.needsUpdate=true;
  }
  function start(items,mode,motion){prepare();for(let i=0;i<M.els.length;i++)state[i*4]=0;lastActive=[];U.uBuildOn.value=1;U.uBuildMode.value=mode==='assembly'?2:mode==='growth'?1:3;U.uBuildMotion.value=motion;running=true;for(const G of Object.values(groups))if(G.mesh){G.buildFrustum=G.mesh.frustumCulled;G.mesh.frustumCulled=false;}U.uBuildState.value.needsUpdate=true;}
  function update(items,seconds,rewind=false){
    if(rewind){for(let i=0;i<M.els.length;i++)state[i*4]=0;lastActive=items;}
    for(const item of lastActive)state[item.i*4]=Math.max(0,Math.min(1,(seconds-item.start)/item.duration));
    const now=[];for(const item of items){const p=Math.max(0,Math.min(1,(seconds-item.start)/item.duration));state[item.i*4]=p;if(p>0&&p<1)now.push(item);}
    lastActive=now;U.uBuildState.value.needsUpdate=true;
  }
  function stop(){U.uBuildOn.value=0;running=false;lastActive=[];for(const G of Object.values(groups))if(G.mesh&&G.buildFrustum!==undefined){G.mesh.frustumCulled=G.buildFrustum;delete G.buildFrustum;}}
  function pickable(i,point){if(!running)return true;const p=state[i*4];if(p<=0)return false;if(U.uBuildMode.value===2&&p<1)return false;return !point||U.uBuildMode.value!==1||state[i*4+1]<.5||along(spec(i),...point)<=p+.0001;}
  return {patch,bindEdges,start,update,stop,pickable,get active(){return running;},progress:i=>state[i*4],bytes:()=>ready?Object.values(groups).reduce((n,g)=>n+(g.mesh?.geometry.attributes.aBuild?.array.byteLength||0),0)+state.byteLength+centres.byteLength:state.byteLength+centres.byteLength};
};

/* Continuous construction preview, ordered by the actual world elevation. */
(function(){
'use strict';
window.initProjectBuild=function(ctx){
  const {M,$,esc,LVL,UNITS,openSec,wake,toast,begin,reveal,end,bounds,canDraw,canInclude,fx,hide,phase,setHeights,frame}=ctx;
  const sec=document.createElement('section');sec.className='acc';sec.dataset.sec='pBuild';
  sec.innerHTML='<button class="acc-h" type="button" aria-expanded="false"><span class="acc-t">بناء المشروع</span><span class="acc-c">▾</span></button><div class="acc-b"><div class="pane" id="pBuild" dir="rtl"></div></div>';
  $('acc').appendChild(sec);
  const nav=document.createElement('button');nav.type='button';nav.dataset.go='pBuild';nav.textContent='بناء المشروع';$('navTools').appendChild(nav);
  const style=document.createElement('style');style.textContent=`
  #pBuild .pb-row{display:flex;align-items:center;gap:6px;padding:6px 0;border-bottom:1px solid var(--line,#dbe1e8)}
  #pBuild .pb-row label{flex:1;min-width:0;display:flex;align-items:center;gap:7px}
  #pBuild input[type=checkbox]{flex:0 0 auto;width:17px;height:17px}
  #pBuild .pb-row small{white-space:nowrap;font-variant-numeric:tabular-nums}
  #pBuild .pb-order{display:flex;align-items:center;gap:3px}#pBuild .pb-order b{min-width:20px;text-align:center}
  #pBuild .pb-order button{min-width:32px;min-height:36px;padding:3px}
  #pBuild .pb-ctl{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0}
  #pBuild .pb-ctl button,#pBuild select{min-height:44px}#pBuild progress{width:100%;accent-color:var(--accent,#2772a3)}
  #pBuild select{max-width:100%}#pBuild .pb-ctl label{min-width:0}#pBuild .pb-schedule-row{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding:8px 0;border-bottom:1px solid var(--line,#ddd)}#pBuild .pb-schedule-row select{grid-column:1/-1;width:100%}#pBuild input[type=date]{width:100%;min-width:0;box-sizing:border-box;min-height:40px}#pBuild [hidden]{display:none!important}
  #pBuild .pb-phases{display:flex;gap:6px;flex-wrap:wrap;font-size:12px}#pBuild .pb-phases span{padding:6px 8px;border-radius:8px;background:var(--soft,#eef2f6)}#pBuild .pb-phases b{font-variant-numeric:tabular-nums}
  #pBuild details{margin:9px 0}#pBuild summary{cursor:pointer;font-weight:600;padding:9px 0}
  #pBuild .pb-status{min-height:2em;margin:8px 0}#pBuild textarea{width:100%;min-height:150px;box-sizing:border-box;direction:rtl}
  #pBuild button:disabled{opacity:.4}#pBuild .pb-row:focus-within{outline:1px solid var(--accent,#2772a3)}
  #buildTransport{position:fixed;z-index:80;inset-inline:12px;bottom:calc(68px + env(safe-area-inset-bottom));margin:auto;max-width:600px;display:flex;align-items:center;flex-wrap:wrap;gap:6px;padding:9px;border:1px solid var(--line,#dbe1e8);border-radius:12px;background:var(--panel,#fff);box-shadow:0 3px 16px #13233322;color:var(--text,#1c2a3b)}
  #buildTransport[hidden]{display:none}#pbRunName{flex:1 0 100%;font-size:12px}#buildTransport button,#buildTransport select{min-height:44px;padding:5px 8px;border:1px solid var(--line,#dbe1e8);border-radius:8px;background:transparent;color:inherit;font:inherit;font-size:12px}
  @media(max-width:860px){body.panel-open #buildTransport{display:none}}
  @media(min-width:861px){#buildTransport{inset-inline-start:auto;inset-inline-end:20px;min-width:390px}}
  `;document.head.appendChild(style);
  const transport=document.createElement('div');transport.id='buildTransport';transport.hidden=true;transport.dir='rtl';transport.setAttribute('role','toolbar');transport.setAttribute('aria-label','عرض البناء');
  const speeds=()=>[.5,1,2,4].map(v=>'<option value="'+v+'">'+v+' ×</option>').join('');
  transport.innerHTML='<span id="pbRunName" role="status" aria-live="polite"></span><input data-build-seek type="range" min="0" max="1000" value="0" style="width:100%" aria-label="موضع البناء"><button data-pb="pause">إيقاف مؤقت</button><button data-pb="skip">الدور التالي</button><button data-pb="restart">إعادة</button><select data-speed aria-label="سرعة البناء">'+speeds()+'</select><button data-pb="restore">إنهاء</button>';document.body.appendChild(transport);
  const box=$('pBuild'),KEY='c4-project-build-v1';let catalogue=null,byKey=null,order=[],speed=1,scope='all',sequence='growth',motion=1,scheduleRows=[],run=null,raf=0,active=false,paused=false;
  const phaseNames=['الإمدادات','الإنشاءات','المعمار والموقع'];
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const levels=M.levels.slice().sort((a,b)=>a.ffl-b.ffl);
  function prepare(){
    if(catalogue)return;
    catalogue=[];byKey=new Map();
    const add=(key,name,section)=>{const row={key,name,section,ids:[]};catalogue.push(row);byKey.set(key,row);};
    [['A','معماري'],['S','إنشائي'],['M','ميكانيك'],['E','كهرباء'],['site','موقع']].forEach(([k,n])=>add('d:'+k,n,0));
    (M.lifecycle?.systems||[]).forEach(s=>add('s:'+s.id,s.name,1));
    ['B','G','1','2','3','4','5','R','T'].forEach(l=>add('l:'+l,(LVL[l]?.name||l)+' ('+l+')',2));
    UNITS.forEach(u=>add('u:'+u.id,u.name+' — '+(LVL[u.level]?.name||u.level),2));
    const put=(k,i)=>byKey.get(k)?.ids.push(i);
    M.els.forEach((e,i)=>{
      if(e.a?.alt||!canInclude(i))return;
      const site=e.c==='A.site'||e.c==='P.irr'||e.a?.sys==='water_site'||/^site_/.test(e.t||'')||['tree','plant','car','shade','play','ground'].includes(e.stage);
      const d=site?'site':/^[MP]\./.test(e.c)?'M':e.c[0];put('d:'+d,i);put('s:'+e.a?.sys,i);put('l:'+e.l,i);
      if(e.u!=null)put('u:'+e.u,i);if(e.u2!=null&&e.u2!==e.u)put('u:'+e.u2,i);
    });
    try{const saved=JSON.parse(localStorage.getItem(KEY)||'null');if(saved&&Array.isArray(saved.order)){order=[...new Set(saved.order)].filter(k=>byKey.has(k));if([.5,1,2,4].includes(saved.speed))speed=saved.speed;if(['staggered','together','growth','assembly','schedule'].includes(saved.sequence))sequence=saved.sequence;if([1,2,3,4].includes(saved.motion))motion=saved.motion;if(Array.isArray(saved.schedule))scheduleRows=saved.schedule.filter(r=>r&&byKey.has(r.key)&&typeof r.start==='string'&&typeof r.end==='string').slice(0,100);}}catch(e){}
  }
  function save(){try{localStorage.setItem(KEY,JSON.stringify({v:4,order,speed,sequence,motion,schedule:scheduleRows}));}catch(e){}}
  function render(){
    prepare();
    box.innerHTML='<div class="pb-ctl"><label>نمط البناء <select id="pbSequence"><option value="growth">نمو المكوّنات باتجاهها</option><option value="staggered">مراحل متداخلة</option><option value="assembly">تجميع القطع</option><option value="schedule">جدول التنفيذ</option><option value="together">عرض متزامن</option></select></label></div><div class="pb-ctl"><label>العرض <select id="pbScope"><option value="all">المشروع كاملًا</option><option value="selected">المجموعات المحددة</option></select></label><label>السرعة <select data-speed aria-label="سرعة البناء">'+speeds()+'</select></label></div>'+
      '<div id="pbMotionBox" class="pb-ctl"><label>حركة القطع <select id="pbMotion"><option value="1">هبوط من الأعلى</option><option value="2">صعود من الأسفل</option><option value="3">ظهور من المركز</option><option value="4">تجمّع إلى الموضع</option></select></label></div><div id="pbSchedule"></div><div class="pb-ctl"><button type="button" data-pb="play">تشغيل البناء</button><button type="button" data-pb="pause">إيقاف مؤقت</button><button type="button" data-pb="skip">الدور التالي</button><button type="button" data-pb="restore">استعادة العرض</button></div>'+
      '<div class="pb-status" id="pbStatus" role="status" aria-live="polite"></div><progress id="pbProgress" max="100" value="0" aria-label="تقدّم البناء"></progress>'+
      '<label style="display:block">موضع العرض <input id="pbSeek" type="range" min="0" max="1000" value="0" style="width:100%" aria-label="موضع البناء"></label><div id="pbPhases" class="pb-phases"></div><details><summary>تخصيص المجموعات</summary>'+['الأقسام','الأنظمة','الأدوار والوحدات'].map((name,g)=>'<details><summary>'+name+'</summary>'+catalogue.filter(r=>r.section===g).map(row=>{
        const key=esc(row.key),label=esc(row.name);
        return '<div class="pb-row"><label><input type="checkbox" data-key="'+key+'"><span>'+label+'</span></label><small>'+row.ids.length.toLocaleString('en')+'</small><span class="pb-order"><b data-priority="'+key+'"></b><button type="button" data-pb="up" data-key="'+key+'" aria-label="رفع أولوية '+label+'">↑</button><button type="button" data-pb="down" data-key="'+key+'" aria-label="خفض أولوية '+label+'">↓</button></span></div>';
      }).join('')+'</details>').join('')+'</details><div class="pb-ctl"><button type="button" data-pb="copy">نسخ كتوجيه</button></div><textarea id="pbCopyText" hidden readonly aria-label="توجيه البناء"></textarea>';
    renderSchedule();sync();
  }
  function dateValue(v){if(!/^\d{4}-\d{2}-\d{2}$/.test(v))return NaN;const t=Date.parse(v+'T00:00:00Z');return Number.isFinite(t)&&new Date(t).toISOString().slice(0,10)===v?t:NaN;}
  function scheduleValid(){return scheduleRows.length>0&&scheduleRows.every(r=>Number.isFinite(dateValue(r.start))&&dateValue(r.end)>=dateValue(r.start)&&byKey.has(r.key));}
  function renderSchedule(){
    if(!$('pbSchedule'))return;
    $('pbSchedule').innerHTML='<div class="muted">'+(scheduleRows.length?'المجموعات وتواريخ التنفيذ':'أضف المجموعات وتواريخ التنفيذ')+'</div>'+scheduleRows.map((r,i)=>'<div class="pb-schedule-row"><select data-schedule="key" data-row="'+i+'" aria-label="مجموعة النشاط">'+catalogue.filter(x=>x.ids.length).map(x=>'<option value="'+esc(x.key)+'" '+(r.key===x.key?'selected':'')+'>'+esc(x.name)+' ('+x.ids.length+')</option>').join('')+'</select><label>البداية<input type="date" data-schedule="start" data-row="'+i+'" value="'+esc(r.start)+'"></label><label>النهاية<input type="date" data-schedule="end" data-row="'+i+'" value="'+esc(r.end)+'"></label><button data-pb="remove-date" data-row="'+i+'">حذف النشاط</button></div>').join('')+'<div class="pb-ctl"><button data-pb="add-date">إضافة نشاط</button></div>';
  }
  function planItems(items){
    if(sequence==='schedule'){
      if(!scheduleValid())return null;
      const start=Math.min(...scheduleRows.map(r=>dateValue(r.start))),finish=Math.max(...scheduleRows.map(r=>dateValue(r.end)+86400000)),map=new Map(items.map(e=>[e.i,e])),planned=[],seen=new Set();
      scheduleRows.forEach(r=>{for(const i of byKey.get(r.key).ids){if(seen.has(i)||!map.has(i))continue;seen.add(i);planned.push({...map.get(i),start:30*(dateValue(r.start)-start)/(finish-start),duration:30*(dateValue(r.end)+86400000-dateValue(r.start))/(finish-start)});}});
      return {items:planned,duration:30,calendar:{start,finish},unlinked:items.length-planned.length};
    }
    const buckets=new Map();for(const e of items){const level=levels.findIndex(l=>l.id===M.els[e.i].l),k=level+':'+e.phase;let b=buckets.get(k);if(!b){b={level,phase:e.phase,items:[]};buckets.set(k,b);}b.items.push(e);}
    const planned=[];
    for(const b of buckets.values()){
      b.items.sort((a,z)=>a.priority-z.priority||M.els[a.i].g[1]-M.els[z.i].g[1]||a.i-z.i);
      b.items.forEach((e,j)=>{const facade=/^A\.(win|clad|wfin)$/.test(M.els[e.i].c),delay=facade?.65:0;planned.push({...e,start:Math.max(0,b.level)*2.8+b.phase*.85+delay+1.4*j/Math.max(1,b.items.length),duration:sequence==='staggered'?.45:sequence==='assembly'?.85:1.15});});
    }
    if(reduced)planned.forEach(e=>{e.start*=.1;e.duration=.15;});
    return {items:planned,duration:Math.max(...planned.map(e=>e.start+e.duration)),unlinked:0};
  }
  function floorName(y){let l=levels[0];for(const x of levels){if(x.ffl<=y+.01)l=x;else break;}return y<levels[0].ffl?'الأساسات':l.name;}
  function sync(){
    if(!$('pbStatus'))return;
    box.querySelectorAll('input[data-key]').forEach(el=>{el.checked=order.includes(el.dataset.key);el.disabled=active;});
    box.querySelectorAll('[data-priority]').forEach(el=>{const p=order.indexOf(el.dataset.priority);el.textContent=p>=0?p+1:'';});
    box.querySelectorAll('[data-pb=up],[data-pb=down]').forEach(b=>{const p=order.indexOf(b.dataset.key);b.disabled=active||p<0||(b.dataset.pb==='up'?p===0:p===order.length-1);});
    for(const root of [box,transport]){
      const b=root.querySelector('[data-pb=pause]');b.disabled=!active||run?.done;b.textContent=paused?'استئناف':'إيقاف مؤقت';
      root.querySelector('[data-pb=skip]').disabled=!active||run?.done;root.querySelector('[data-pb=restore]').disabled=!active;
      root.querySelector('[data-speed]').value=String(speed);
    }
    $('pbScope').value=scope;$('pbScope').disabled=active||sequence==='schedule';$('pbSequence').value=sequence;$('pbSequence').disabled=active;$('pbMotionBox').hidden=sequence!=='assembly';$('pbMotion').value=String(motion);$('pbMotion').disabled=active;$('pbSchedule').hidden=sequence!=='schedule';$('pbSchedule').querySelectorAll('input,select,button').forEach(e=>e.disabled=active);$('pbSeek').disabled=!active||!run?.elementMode;$('pbSeek').value=run?Math.round(run.elapsed/run.duration*1000):0;const seek=transport.querySelector('[data-build-seek]');seek.disabled=!active||!run?.elementMode;seek.value=$('pbSeek').value;
    box.querySelector('[data-pb=play]').disabled=sequence==='schedule'?!scheduleValid():scope==='selected'&&!order.length;
    box.querySelector('[data-pb=copy]').disabled=scope==='selected'&&!order.length;
    const p=run?Math.min(100,100*run.elapsed/run.duration):0;$('pbProgress').value=p;
    const date=run?.calendar?new Date(Math.min(run.calendar.finish-1,run.calendar.start+(run.calendar.finish-run.calendar.start)*p/100)).toISOString().slice(0,10):null;
    const status=run?(run.done?'اكتمل البناء · '+run.ids.length.toLocaleString('en')+' مكوّن':(paused?'متوقف · ':'')+(date||floorName(run.height))+' · '+Math.round(p)+'%'):'من الأساسات إلى السطح · '+(scope==='all'?'كل المكوّنات':'المجموعات المحددة');
    $('pbPhases').innerHTML=sequence!=='together'?phaseNames.map((n,i)=>'<span>'+n+(run?' <b>'+Math.round((run.phases[i]?.progress||0)*100)+'%</b>':'')+'</span>').join(''):'';
    $('pbStatus').textContent=status+((run?.missing.length)?' · '+run.missing.length+' بلا مجسّم':'')+(run?.unlinked?' · '+run.unlinked+' غير مجدول':'');$('pbRunName').textContent=status;transport.hidden=!active;
  }
  function stop(){cancelAnimationFrame(raf);raf=0;run=null;paused=false;if(active){active=false;end();}sync();}
  function start(){
    prepare();if(sequence==='schedule'&&!scheduleValid())return;if(sequence!=='schedule'&&scope==='selected'&&!order.length)return;
    stop();const rank=new Map();
    if(scope==='all'||sequence==='schedule')M.els.forEach((e,i)=>{if(!e.a?.alt&&canInclude(i))rank.set(i,0);});
    else order.forEach((k,p)=>byKey.get(k).ids.forEach(i=>{if(!rank.has(i))rank.set(i,p);}));
    const missing=[],items=[];rank.forEach((priority,i)=>{if(!canDraw(i)){missing.push(M.els[i].id);return;}const b=bounds(i);items.push({i,lo:b[0],hi:b[1],priority,phase:phase(i)});});
    if(!items.length){toast('لا توجد مجسّمات في هذا الاختيار');return;}
    if(sequence!=='together'){
      const plan=planItems(items);if(!plan?.items.length){toast('لا توجد مكوّنات مرتبطة بهذا الجدول');return;}
      const list=plan.items.sort((a,b)=>a.start-b.start||a.i-b.i),ids=list.map(e=>e.i),lo=Math.min(...list.map(e=>e.lo)),hi=Math.max(...list.map(e=>e.hi));
      begin();active=true;setHeights(null);fx.start(list,reduced?'staggered':sequence,motion);
      run={...plan,items:list,ids,missing,lo,hi,height:lo,offset:0,elapsed:0,last:performance.now(),duration:plan.duration*1000,done:false,syncAt:0,elementMode:true,phases:phaseNames.map((name,i)=>({name,items:list.filter(e=>e.phase===i),progress:0,offset:0,height:lo,delay:0}))};
      sync();raf=requestAnimationFrame(tick);return;
    }
    items.sort((a,b)=>a.lo-b.lo||a.priority-b.priority||a.i-b.i);
    const lo=items[0].lo-.02,hi=items.reduce((v,r)=>Math.max(v,r.hi),lo)+.02;
    const travel=reduced?1200:Math.max(18000,Math.min(55000,(hi-lo)*1100)),gap=reduced?100:1200;
    let activePhase=0;
    const phases=phaseNames.map((name,k)=>{
      const list=items.filter(e=>e.phase===k),low=list.length?list[0].lo-.02:lo,high=list.reduce((v,e)=>Math.max(v,e.hi+.02),low);
      const stagger=sequence==='staggered',delay=stagger&&list.length?activePhase++*gap:0;
      return {name,items:list,lo:stagger?low:lo,hi:stagger?high:hi,delay,duration:stagger?Math.max(250,travel*(high-low)/(hi-lo)):travel,offset:0,progress:0,height:stagger?low:lo};
    });
    const duration=Math.max(...phases.filter(p=>p.items.length).map(p=>p.delay+p.duration));
    begin();active=true;const ids=items.map(e=>e.i);
    run={ids,items,phases,missing,lo,hi,height:lo,offset:0,elapsed:0,last:performance.now(),duration,done:false,syncAt:0};
    setHeights(phases.map(p=>p.height));sync();raf=requestAnimationFrame(tick);
  }
  function advance(elapsed){
    const previous=run.elapsed;run.elapsed=Math.max(0,Math.min(run.duration,elapsed));const p=run.elapsed/run.duration;
    if(run.elementMode){
      const seconds=run.elapsed/1000;let next=0;while(next<run.items.length&&run.items[next].start<=seconds)next++;
      if(next<run.offset)hide(run.ids.slice(next,run.offset));else if(next>run.offset)reveal(run.ids.slice(run.offset,next));run.offset=next;
      fx.update(run.items,seconds,previous>run.elapsed);
      for(const band of run.phases){band.offset=band.items.filter(e=>e.start<=seconds).length;band.progress=band.items.length?band.items.reduce((n,e)=>n+Math.max(0,Math.min(1,(seconds-e.start)/e.duration)),0)/band.items.length:1;band.height=band.offset?Math.max(...band.items.filter(e=>e.start<=seconds).map(e=>e.lo)):run.lo;}
      run.height=Math.max(...run.phases.map(b=>b.height));run.done=p>=1;if(run.done)sync();wake(100);return;
    }
    // Each discipline grows in place; the following disciplines start a little later.
    const visible=[];
    for(const band of run.phases){
      band.progress=Math.min(1,Math.max(0,(run.elapsed-band.delay)/band.duration));
      band.height=band.lo+(band.hi-band.lo)*band.progress;
      while(band.offset<band.items.length&&band.items[band.offset].lo<=band.height){visible.push(band.items[band.offset++].i);}
    }
    run.height=Math.max(...run.phases.filter(b=>b.items.length).map(b=>b.height));
    setHeights(run.phases.map(b=>b.height));
    if(visible.length){reveal(visible);run.offset+=visible.length;}
    if(p>=1){run.done=true;setHeights(null);sync();}wake(100);
  }
  function tick(now){
    if(!run||paused||run.done)return;
    const dt=Math.min(Math.max(0,now-run.last),150);run.last=now;advance(run.elapsed+dt*speed);
    if(now-run.syncAt>180){run.syncAt=now;sync();}
    if(!run.done)raf=requestAnimationFrame(tick);
  }
  async function copy(){
    const text='اعرض بناء '+(scope==='all'?'المشروع كاملًا':order.map(k=>byKey.get(k).name).join('، '))+' تدريجيًا من الأساسات إلى السطح'+({staggered:'؛ بمراحل متداخلة',growth:'؛ بنمو المكوّنات باتجاهها',assembly:'؛ بتجميع القطع في مواضعها',schedule:'؛ وفق الأنشطة والتواريخ: '+scheduleRows.map(r=>byKey.get(r.key)?.name+' من '+r.start+' إلى '+r.end).join('، '),together:'، بالتزامن بين الأقسام'}[sequence])+'، مع جميع مكوّناته وفي مواضعها ومناسيبها الحالية.';
    try{await navigator.clipboard.writeText(text);toast('نُسخ توجيه البناء');}catch(e){const area=$('pbCopyText');area.value=text;area.hidden=false;area.focus();area.select();}
  }
  function change(ev){
    if(ev.target.dataset.schedule&&!active){const r=scheduleRows[+ev.target.dataset.row];if(r){r[ev.target.dataset.schedule]=ev.target.value;save();sync();}return;}
    if(ev.target.id==='pbMotion'&&!active){motion=+ev.target.value;save();return;}
    if(ev.target.matches('[data-speed]')){speed=Number(ev.target.value);save();sync();return;}
    if(ev.target.id==='pbSequence'&&!active){sequence=ev.target.value;save();sync();return;}
    if(ev.target.id==='pbScope'){scope=ev.target.value;sync();return;}
    const k=ev.target.dataset.key;if(!k||active)return;
    if(ev.target.checked){if(!order.includes(k))order.push(k);}else order=order.filter(x=>x!==k);
    scope='selected';save();sync();
  }
  function action(ev){
    const b=ev.target.closest('[data-pb]');if(!b)return;const a=b.dataset.pb;
    if(a==='play'||a==='restart')start();
    else if(a==='restore')stop();
    else if(a==='pause'&&run&&!run.done){paused=!paused;cancelAnimationFrame(raf);if(!paused){run.last=performance.now();raf=requestAnimationFrame(tick);}sync();}
    else if(a==='skip'&&run&&!run.done){
      if(run.elementMode){const t=run.elapsed/1000,next=run.items.find(e=>e.start>t+.05&&e.lo>run.height+.1);advance(next?next.start*1000:run.duration);run.last=performance.now();sync();return;}
      const unfinished=run.phases.filter(p=>p.items.length&&p.progress<1),height=Math.min(...unfinished.map(p=>p.height));
      const h=levels.find(l=>l.ffl>height+.02)?.ffl??run.hi;
      const next=Math.max(...unfinished.map(p=>p.delay+p.duration*Math.min(1,Math.max(0,(h+.021-p.lo)/(p.hi-p.lo)))));
      advance(Math.max(run.elapsed,next));run.last=performance.now();sync();
    }
    else if(a==='add-date'&&!active){scheduleRows.push({key:'l:G',start:'',end:''});renderSchedule();save();sync();}
    else if(a==='remove-date'&&!active){scheduleRows.splice(+b.dataset.row,1);renderSchedule();save();sync();}
    else if(a==='copy')copy();
    else if((a==='up'||a==='down')&&!active){const i=order.indexOf(b.dataset.key),j=i+(a==='up'?-1:1);if(i>=0&&j>=0&&j<order.length){[order[i],order[j]]=[order[j],order[i]];save();sync();}}
  }
  [box,transport].forEach(root=>root.addEventListener('input',ev=>{if((ev.target.id==='pbSeek'||ev.target.hasAttribute('data-build-seek'))&&run&&run.elementMode){paused=true;cancelAnimationFrame(raf);advance(+ev.target.value/1000*run.duration);sync();}}));
  [box,transport].forEach(el=>{el.addEventListener('change',change);el.addEventListener('click',action);});
  const open=()=>{if(!catalogue)render();openSec('pBuild');};nav.onclick=open;sec.querySelector('.acc-h').onclick=open;
  document.addEventListener('click',ev=>{if(active&&!sec.contains(ev.target)&&!transport.contains(ev.target)&&ev.target.closest('#secnav button,.acc-h,#btnAll,#btnHome,#isoExit,#viewMenu button,#bar button:not(#btnMore)'))stop();},true);
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&active&&run&&!run.done&&!paused){paused=true;cancelAnimationFrame(raf);sync();}});
  document.addEventListener('keydown',ev=>{if(ev.key==='Escape'&&active)stop();});
  return {open,stop,get playing(){return active&&!paused&&!run?.done;},state:()=>({active,paused,done:!!run?.done,shown:run?.offset||0,total:run?.ids.length||0,height:run?.height,progress:run?run.elapsed/run.duration:0,missing:run?.missing||[],order:order.slice(),scope,sequence,motion,speed,calendar:run?.calendar||null,unlinked:run?.unlinked||0,scheduleValid:!!catalogue&&scheduleValid(),phases:run?.phases.map(p=>({name:p.name,height:p.height,progress:p.progress,shown:p.offset,total:p.items.length,delay:p.delay}))||[],groups:catalogue?.length||0})};
};
})();
