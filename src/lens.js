/* ===== Lenses: colour the whole model by one property (idea: Speckle «colour by property», Navisworks / ACC clash colours, BIM Forum LOD) =====
   Every element is given a class index 1..31 (0 = «not concerned», 255 = hidden) per lens; the class is written into the per-vertex attribute aLens of its merged group and the
   shader (app.js patch) mixes the class colour into the material.  Switching a lens only rewrites that attribute (no geometry is rebuilt), so it is instant on 25k elements.
   Lenses: off | grade (data reliability) | layer (discipline) | level | system (services) | tier (clash tiers) | guess (best-guess confidence) | finishF / finishW / finishC (A500 floor / wall / ceiling codes) | custom (set by a panel). */
(function(){
'use strict';
// Display colours are user-adopted analytical meanings, never physical specifications.
const PALETTE=window.C4_PALETTE;
const OKABE={vermillion:'#AC2E40',orange:'#A86528',sky:'#417FAD',green:'#167568',blue:'#315EA1',purple:'#83596F',lilac:'#64509E',gray:'#69788C',slate:'#4D6E87'};
// Kept only for older assumption panels; source verification uses BASIS below.
const GRADE={d:{n:'تصنيف استخراج قديم',c:OKABE.green,h:'تصنيف تاريخي؛ لا يثبت المصدر أو المنسوب أو المواصفة'},v:{n:'مشتق',c:OKABE.sky,h:'قاعدة حساب؛ ليست اعتمادًا للمصدر'},a:{n:'افتراض',c:OKABE.orange,h:'بيان غير محدد بالمخطط'},s:{n:'إخراجي',c:OKABE.gray,h:'للعرض فقط'}};
const TIER={c:{n:'تداخل المجسم يحتاج إثبات المصدر',c:OKABE.vermillion},k:{n:'مرشح اختلاف منسوب أو شكل',c:OKABE.orange},m:{n:'أثر صغير يحتاج تحققًا',c:OKABE.slate}};
const CONF={high:{n:'أولوية مراجعة عالية',c:OKABE.vermillion},med:{n:'أولوية مراجعة متوسطة',c:OKABE.orange},low:{n:'أولوية مراجعة منخفضة',c:OKABE.slate},rule:{n:'افتراض عام على النوع',c:OKABE.purple}};
const LEVELC=PALETTE.levels;
const SYSTEMS=Object.entries(PALETTE.systems).map(([k,p])=>({k,n:p.name,c:p.color}));
function sysOf(e){
 const c=e.c,a=e.a||{},v=a.sys||'';
 if(v.startsWith('smk_'))return v;
 if(v==='garbage_chute')return 'garbage_chute';
 if(v==='hvac_controls')return 'hvac_controls';if(v==='air')return 'air';
 if(v==='cold'||v==='hot')return v;
 if(v==='fa'||v==='ea')return 'vent_'+v;
 if(v==='ltg')return 'lightning';if(v==='earth')return 'earthing';
 if(v==='water_roof'||v==='water_site'||v==='site')return 'water_site';
 if(v==='telephone'||v==='irrigation')return v;
 if(v==='drain_legacy_vent'||e.t==='vent_drain_pipe'||e.t==='pipe_vent')return 'drain_vent';
 if(e.t==='pipe_pressure'||v==='drain_pressure')return 'drain_pressure';
 if(v.startsWith('drain'))return 'drain';if(v.startsWith('fire'))return c==='P.pump'?'fire_pumps':'fire';
 if(c==='M.duct'||c==='M.outlet'||c==='M.damper'||c==='M.fan')return 'air';
 if(c==='M.pipe')return 'chw';if(c==='P.cold')return 'cold';if(c==='P.hot'||c==='P.heater')return 'hot';
 if(c==='P.storm')return 'storm';if(c==='P.drain'||c==='P.fix')return 'drain';if(c==='P.ff')return 'fire';
 if(c==='P.irr')return 'irrigation';if(c[0]==='E')return 'power';
 if(c==='M.equip')return 'chw';if(c==='P.pump'||c==='P.tank')return 'equipment';return null;
}
function hex(c){const n=parseInt(c.replace('#',''),16); return [((n>>16)&255)/255,((n>>8)&255)/255,(n&255)/255];}

function initLens(ctx){
  const {M,THREE,groups,elRange,U,applyVis,wake,CATS,LAYER,LVL,$,esc}=ctx;
  const N=M.els.length; let mode='off', legend=[], custom=null, hideRest=false, label='';
  const pal=U.lensPal.value;
  /* ---------- per-element class functions: return {idx, cls[]} ---------- */
  const guessInfo=(()=>{ // element -> best-guess confidence (item level) or 'rule' when only a systematic assumption covers its type
    const G=M.guesses||{rules:[],items:[]}; const el=new Map(); const rank={high:3,med:2,low:1};
    (G.items||[]).forEach(it=>{const cur=el.get(it.e); if(!cur||rank[it.conf]>rank[cur]) el.set(it.e,it.conf);});
    (G.rules||[]).forEach(r=>{ if(r.els&&r.id!=='G-SNAP') r.els.forEach(i=>{if(!el.has(i)&&r.id!=='G-STAGE') el.set(i,'rule');}); });
    return el;})();
  const tierOf=new Map(),coordOf=new Map(),idIndex=new Map(M.els.map((e,i)=>[e.id,i]));
  const ranks={confirmed:5,confirmed_plan:4,source_elevation:3,model_collision:2,candidate_height:1};
  function addCoord(ids,key){if(!ranks[key])return;ids.forEach(id=>{const i=idIndex.get(id);if(i===undefined)return;const old=coordOf.get(i);if(!old||ranks[key]>ranks[old])coordOf.set(i,key);tierOf.set(i,key==='candidate_height'?'k':'c');});}
  (M.coordinationReview?.issues||[]).forEach(c=>addCoord([c.ea,c.eb],c.classification?.lane));
  (M.coordinationReview?.source_conflicts||[]).filter(c=>c.zconflict).forEach(c=>addCoord(c.elements||[], 'source_elevation'));
  const proofOf=M.componentReview?.status_by_id||{};
  const sysIdx=M.els.map(sysOf);
  // Explicit source family wins; lifecycle membership identifies otherwise unlabelled devices.
  (M.lifecycle?.systems||[]).forEach(S=>{[...(S.src||[]),...(S.ri||[]),...(S.x||[]),...(S.o||[])].forEach(i=>{const e=M.els[i];if(e&&!e.a?.sys&&['P.pump','P.tank'].includes(e.c))sysIdx[i]=S.id;});});
  // Display-only inheritance: supports do not join the parent's lifecycle network.
  M.els.forEach((e,i)=>{const parent=e.a?.bracket_for||e.a?.clip_for;if(parent&&e.a?.not_a_host){const j=idIndex.get(parent);if(j!==undefined)sysIdx[i]=sysIdx[j];}});
  const FINS=Object.keys(M.fin||{}).sort((a,b)=>a.localeCompare(b,'en',{numeric:true}));
  const FINRE={finishF:/^(F\d|CSP)/,finishW:/^W\d/,finishC:/^C\d/};
  const FINCAT=PALETTE.finish_codes;
  const finCount={}; M.els.forEach(e=>{ const f=e.a&&e.a.fin; if(f) for(let i=0;i<f.length;i++) finCount[f[i]]=(finCount[f[i]]||0)+1; });
  const finCodes=m=>FINS.filter(f=>FINRE[m].test(f)&&finCount[f]);   // only codes that sit on elements (group rows such as «CSP» of the BOQ table have none)
  const finOfMode=(ei,m)=>{const f=(M.els[ei].a&&M.els[ei].a.fin)||null; if(!f) return null; for(let i=0;i<f.length;i++) if(FINRE[m].test(f[i])) return f[i]; return null;};
  const finMode=(m,n,d)=>({n,d,cls:()=>finCodes(m).slice(0,31).map((f,i)=>({k:f,n:f+' — '+((M.fin[f]||[''])[0]),c:FINCAT[i%FINCAT.length],h:'لون تحليلي لرمز التشطيب، وليس لون المادة الفعلي'})),ofi:ei=>finOfMode(ei,m)});
  const MODES={
    grade:{n:'دليل المصدر',d:'تحقق مستقل لـXY / اتساق تاريخي / مشتق / غير مثبت',cls:()=>Object.entries(PALETTE.proof).map(([k,p])=>({k,n:p.name,c:p.color,h:'درجة تحقق الموضع XY فقط. المنسوب والمادة والمقاس تحتاج دليلًا مستقلًا.'})),of:e=>proofOf[e.id]||'unverified'},
    layer:{n:'التخصصات',d:'ألوان تحليلية للتخصصات؛ ليست مواد',cls:()=>M.layers.map(L=>({k:L.id,n:L.name,c:PALETTE.disciplines[L.id]})).concat([{k:'X',n:'عناصر إخراجية غير معتمدة من المصدر',c:'#7F8793'}]),of:e=>(e.stage||/\.stage$/.test(e.c))?'X':e.c[0]},
    level:{n:'الطوابق',d:'تسلسل لوني من القبو إلى أعلى المبنى',cls:()=>M.levels.map((l,i)=>({k:l.id,n:l.name,c:LEVELC[i%LEVELC.length]})),of:e=>e.l},
    system:{n:'أنظمة الخدمات',d:'شبكات منفصلة حسب خدمة العنصر؛ الأمطار والتهوية والدخان مستقلة',cls:()=>SYSTEMS,ofi:i=>sysIdx[i]},
    smoke:{n:'إدارة الدخان',d:'المواقف والممرات؛ تعويض وسحب مستقلان',cls:()=>SYSTEMS.filter(p=>p.k.startsWith('smk_')),ofi:i=>sysIdx[i]?.startsWith('smk_')?sysIdx[i]:null},
    ventilation:{n:'التهوية',d:'الهواء النقي والسحب بشبكتين مستقلتين',cls:()=>SYSTEMS.filter(p=>p.k.startsWith('vent_')),ofi:i=>sysIdx[i]?.startsWith('vent_')?sysIdx[i]:null},
    tier:{n:'التنسيق والمناسيب',d:'دليل المصدر منفصل عن تداخل الهندسة والمرشح',cls:()=>Object.entries(PALETTE.coordination).map(([k,p])=>({k,n:p.name,c:p.color})),ofi:i=>coordOf.get(i)||null},
    guess:{n:'التخمينات',d:'ثقة موضع كل جهاز ونوع الافتراض',cls:()=>['high','med','low','rule'].map(k=>({k,n:CONF[k].n,c:CONF[k].c})),ofi:ei=>guessInfo.get(ei)||null},
    finishF:finMode('finishF','التشطيبات — الأرضيات','رمز الأرضية في A500 (F وCSP)'),
    finishW:finMode('finishW','التشطيبات — الجدران','رمز الجدار في A500 (W)'),
    finishC:finMode('finishC','التشطيبات — الأسقف','رمز السقف في A500 (C)'),
  };
  document.querySelectorAll('button[data-lens] .lsw').forEach(sw=>{const m=sw.parentElement.dataset.lens,cls=MODES[m]?.cls()||[{c:'#8793A1'}];sw.style.background='linear-gradient(90deg,'+cls.slice(0,8).map(p=>p.c).join(',')+')';});
  function paint(clsIdx){ // clsIdx(ei) -> 0..31 | 255
    for(const k in groups){const G=groups[k]; if(G.lensAttr) G.lensAttr.needsUpdate=true;}
    const touched=new Set();
    for(let ei=0;ei<N;ei++){const rg=elRange[ei]; if(!rg) continue; const G=groups[rg.gk]; if(!G||!G.lensAttr) continue; G.lensAttr.array.fill(clsIdx(ei),rg.start*3,(rg.start+rg.count)*3); touched.add(G);}
    touched.forEach(G=>{G.lensAttr.needsUpdate=true;});
  }
  function setPalette(list){for(let i=0;i<32;i++) pal[i].set(0.86,0.89,0.93); list.slice(0,31).forEach((c,i)=>{const h=hex(c.c); pal[i+1].set(h[0]<=.04045?h[0]/12.92:Math.pow((h[0]+.055)/1.055,2.4),h[1]<=.04045?h[1]/12.92:Math.pow((h[1]+.055)/1.055,2.4),h[2]<=.04045?h[2]/12.92:Math.pow((h[2]+.055)/1.055,2.4));});}
  /* which legend classes are coloured: a clicked set (multi-select). Empty = all classes in the colour look, none in the white look (the model stays white / grey until a section is chosen) —
     except for a custom lens or while «عزل» is on, where empty always means all. Non-coloured elements are washed (colour look) or plain white / grey (white look, shader uMono). */
  let sel=new Set(), idxOfMode=null;
  const mono=()=>!!(U.mono&&U.mono.value>0.5);
  const emptyAll=()=>true;
  const coloured=i=>sel.size?sel.has(i):emptyAll();
  function repaint(){
    if(mode==='off'){ paint(()=>0); return; }
    if(mode==='custom'){ paint(ei=>{const k=custom.map.get(ei); return (k===undefined||!coloured(k))?(hideRest?255:0):k;}); return; }
    const D=MODES[mode]; if(!D||!idxOfMode) return;
    paint(ei=>{const e=M.els[ei]; const k=D.ofi?D.ofi(ei):D.of(e); const i=idxOfMode.get(k); return (!i||!coloured(i))?(hideRest?255:0):i;});
  }
  function set(m,opt){
    if(M.meta?.owner_render_only&&m==='grade')m='off';
    opt=opt||{}; if(m!==mode||opt.keepSel!==true) sel.clear(); mode=m; hideRest=!!opt.hideRest;
    if(m==='off'){U.lensOn.value=0; legend=[]; custom=null; label=''; idxOfMode=null; paint(()=>0); renderLegend(); ctx.onChange&&ctx.onChange(mode); applyVis(); return;}
    if(m==='custom'){const C=opt.classes||[]; setPalette(C); custom={C,map:opt.map}; idxOfMode=null; legend=C.map(c=>({...c,n:c.n,count:0})); repaint();
      legend.forEach((l,i)=>{let n=0; opt.map.forEach(v=>{if(v===i+1) n++;}); l.count=n;}); U.lensOn.value=1; label=opt.label||'تلوين مخصّص'; renderLegend(); ctx.onChange&&ctx.onChange(mode); applyVis(); return;}
    const D=MODES[m]; if(!D) return; const cls=D.cls(); setPalette(cls); idxOfMode=new Map(cls.map((c,i)=>[c.k,i+1])); const counts=new Array(cls.length).fill(0);
    for(let ei=0;ei<N;ei++){const e=M.els[ei]; const k=D.ofi?D.ofi(ei):D.of(e); const i=idxOfMode.get(k); if(i) counts[i-1]++;}
    repaint(); legend=cls.map((c,i)=>({...c,count:counts[i]})); U.lensOn.value=1; label=D.n; custom=null; renderLegend(); ctx.onChange&&ctx.onChange(mode); applyVis();
  }
  function renderLegend(){
    const box=$('lensLegend'); if(!box) return;
    if(mode==='off'){box.classList.remove('on'); box.innerHTML=''; return;}
    const total=legend.reduce((a,l)=>a+l.count,0), M1=mono(), allOn=sel.size===0;
    let h=`<div class=lg-h><b>${esc(label)}</b><button type=button data-lg="off" class=mini title="إيقاف العدسة" aria-label="إيقاف العدسة">✕</button><span class=lg-btns style="flex-basis:100%"><button type=button data-lg="look" class=mini title="${M1?'اختيار المظهر المحايد':'اختيار المظهر المحايد'}">المظهر المحايد</button>${mode!=='custom'?`<button type=button data-lg="all" class="mini${allOn?' on':''}" title="إزالة اختيار الفئات وإظهارها كلها">إظهار كل الفئات</button>`:''}<button type=button data-lg="hide" class="mini${hideRest?' on':''}" title="إخفاء ما لا يتعلق بالعدسة">عزل</button></span></div><div class=lg-b>`;
    legend.forEach((l,i)=>{const on=sel.size?sel.has(i+1):emptyAll(); h+=`<button type=button class="lg-i${sel.has(i+1)?' sel':''}${on?'':' off'}" data-lgi="${i+1}" aria-pressed="${on?'true':'false'}" title="${esc(l.h||l.n)}"><span class=lg-s style="background:${l.c}"></span><span class=lg-n>${esc(l.n)}</span><span class=lg-c>${l.count.toLocaleString('en')} عنصر</span></button>`;});
    h+=`</div><div class=lg-f>${hideRest?'العناصر غير المعنيّة مخفية ولا يمكن تحديدها':'اضغط فئة لتركيزها؛ الاسم والعدد يحددان معناها'}${total?'':' — لا عناصر'} · ألوان تحليلية، وليست ألوان مواد · العينات التفصيلية متوقفة أثناء العدسة</div>`;
    box.innerHTML=h; box.classList.add('on');
  }
  // legend interaction: click a class = colour it / stop colouring it (several allowed); «عزل» hides the rest; «تلوين الكل» (white look) colours every class; «أبيض / ألوان المواد» flips the look
  function toggleClass(i){ if(sel.has(i)) sel.delete(i); else sel.add(i); repaint(); renderLegend(); applyVis(); }
  function refresh(){ if(mode==='off') return; repaint(); renderLegend(); applyVis(); }
  function setSelection(arr){ sel=new Set((arr||[]).filter(i=>i>=1&&i<=legend.length)); repaint(); renderLegend(); applyVis(); }
  const box=$('lensLegend');
  if(box) box.addEventListener('click',ev=>{const b=ev.target.closest('[data-lg],[data-lgi]'); if(!b) return;
    if(b.dataset.lg==='off'){set('off'); const bt=document.querySelectorAll('button[data-lens]'); bt.forEach(x=>x.classList.toggle('on',x.dataset.lens==='off')); return;}
    if(b.dataset.lg==='hide'){hideRest=!hideRest; repaint(); renderLegend(); ctx.onChange&&ctx.onChange(mode); applyVis(); return;}
    if(b.dataset.lg==='all'){ sel.clear(); repaint(); renderLegend(); applyVis(); return; }
    if(b.dataset.lg==='look'){ if(ctx.setLook) ctx.setLook('clay'); return; }
    if(b.dataset.lgi){toggleClass(+b.dataset.lgi);}
  });
  /* the class of one element as painted (0 = not concerned, 255 = hidden, -1 when no lens is on): the picker skips what the lens hides and, while classes are chosen or «عزل» is on, what it only dims */
  function classOf(ei){ if(U.lensOn.value<0.5) return -1; const rg=elRange[ei]; if(!rg) return 0; const G=groups[rg.gk]; return (G&&G.lensAttr)?G.lensAttr.array[rg.start*3]:0; }
  return {set,refresh,setSelection,classOf,get restrict(){return mode!=='off'&&(hideRest||sel.size>0);},get hideRest(){return hideRest;},get solo(){return sel.size;},get selected(){return [...sel];},get mode(){return mode;},modes:Object.keys(MODES).map(k=>({id:k,n:MODES[k].n,d:MODES[k].d})),GRADE,TIER,CONF,OKABE,tierOf,guessInfo,legendOf:()=>legend};
}
window.initLens=initLens; window.LENS_PAL={GRADE,TIER,CONF,OKABE};
})();
