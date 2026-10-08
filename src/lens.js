/* ===== Lenses: colour the whole model by one property (idea: Speckle «colour by property», Navisworks / ACC clash colours, BIM Forum LOD) =====
   Every element is given a class index 1..14 (0 = «not concerned», 255 = hidden) per lens; the class is written into the per-vertex attribute aLens of its merged group and the
   shader (app.js patch) mixes the class colour into the material.  Switching a lens only rewrites that attribute (no geometry is rebuilt), so it is instant on 25k elements.
   Lenses: off | grade (data reliability) | layer (discipline) | level | system (services) | tier (clash tiers) | guess (best-guess confidence) | finishF / finishW / finishC (A500 floor / wall / ceiling codes) | custom (set by a panel). */
(function(){
'use strict';
const OKABE={vermillion:'#D55E00',orange:'#DB7F4A',sky:'#56B4E9',green:'#009E73',blue:'#0072B2',purple:'#CC79A7',lilac:'#B7A6D8',gray:'#9AA3AD',slate:'#7B8794'};   // Okabe–Ito (colour-blind safe) with the orange moved to a warm coral and no yellow: owner 2026-10-08 «اللون الأصفر غير جميل أبدًا»
const GRADE={d:{n:'موثّق',c:OKABE.green,h:'الموضع والمنسوب والمواصفة مقروءة من المخططات'},v:{n:'مشتق',c:OKABE.sky,h:'محسوب بقاعدة معلومة المعطيات'},a:{n:'تخمين',c:OKABE.orange,h:'اختاره النموذج لغياب البيان'},s:{n:'إخراجي',c:OKABE.gray,h:'للعرض فقط'}};
const TIER={c:{n:'تعارض مؤكد',c:OKABE.vermillion,i:'■'},k:{n:'مرشح — اختلاف منسوب',c:OKABE.orange,i:'◆'},m:{n:'هامشي',c:OKABE.slate,i:'●'}};
const CONF={high:{n:'تخمين عالي الثقة',c:OKABE.blue},med:{n:'تخمين متوسط الثقة',c:OKABE.sky},low:{n:'تخمين منخفض الثقة',c:OKABE.purple},rule:{n:'افتراض عام على نوعه',c:'#C9C3DA'}};
const LEVELC=['#2D2A6E','#32479A','#2F63B8','#2C7FC3','#2A99C3','#2CB0B3','#35C4A0','#55D18B','#86DD7F'];   // blue → teal → green (no yellow end)
const SYSTEMS=[['duct','مجاري الهواء','#3b82c4'],['chw','مياه مبردة','#1d4ed8'],['cold','مياه باردة','#06b6d4'],['hot','مياه ساخنة','#ef6c3a'],['drain','صرف وأمطار','#8a6d4b'],['ff','إطفاء','#dc2626'],['elec','كهرباء','#8C6BD0'],['equip','معدات','#C0508F'],['other','أخرى','#9AA3AD']];
function sysOf(e){const c=e.c; if(c==='M.duct'||c==='M.outlet'||c==='M.damper'||c==='M.fan') return 'duct'; if(c==='M.pipe') return 'chw'; if(c==='P.cold') return 'cold'; if(c==='P.hot'||c==='P.heater') return 'hot'; if(c==='P.drain'||c==='P.storm') return 'drain'; if(c==='P.ff') return 'ff'; if(c[0]==='E') return 'elec'; if(c==='M.equip'||c==='P.pump'||c==='P.tank') return 'equip'; return null;}
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
  const tierOf=(()=>{const m=new Map(); const rank={c:3,k:2,m:1}; (M.clashes||[]).forEach(c=>{[c.a,c.b].forEach(i=>{const cur=m.get(i); if(!cur||rank[c.tier||'k']>rank[cur]) m.set(i,c.tier||'k');});}); return m;})();
  const FINS=Object.keys(M.fin||{}).sort((a,b)=>a.localeCompare(b,'en',{numeric:true}));
  const FINRE={finishF:/^(F\d|CSP)/,finishW:/^W\d/,finishC:/^C\d/};
  const FINCAT=['#DB7F4A','#56B4E9','#009E73','#8E7CC3','#0072B2','#D55E00','#CC79A7','#8c564b','#17becf','#7f7f7f','#6FA861','#e377c2','#1f77b4','#2ca02c','#9467bd'];   // categorical colours: 15 classes at most
  const finCount={}; M.els.forEach(e=>{ const f=e.a&&e.a.fin; if(f) for(let i=0;i<f.length;i++) finCount[f[i]]=(finCount[f[i]]||0)+1; });
  const finCodes=m=>FINS.filter(f=>FINRE[m].test(f)&&finCount[f]);   // only codes that sit on elements (group rows such as «CSP» of the BOQ table have none)
  const finOfMode=(ei,m)=>{const f=(M.els[ei].a&&M.els[ei].a.fin)||null; if(!f) return null; for(let i=0;i<f.length;i++) if(FINRE[m].test(f[i])) return f[i]; return null;};
  const finMode=(m,n,d)=>({n,d,cls:()=>finCodes(m).slice(0,15).map((f,i)=>({k:f,n:f+' — '+((M.fin[f]||[''])[0]),c:FINCAT[i%FINCAT.length]})),ofi:ei=>finOfMode(ei,m)});
  const MODES={
    grade:{n:'موثوقية البيانات',d:'موثّق / مشتق / تخمين / إخراجي',cls:()=>['d','v','a','s'].map(k=>({k,n:GRADE[k].n,c:GRADE[k].c,h:GRADE[k].h})),of:e=>{const q=e.q||'ddd'; if(q==='sss') return 's'; return ['d','v','a'][Math.max(['d','v','a'].indexOf(q[0]),['d','v','a'].indexOf(q[1]),['d','v','a'].indexOf(q[2]))];}},
    layer:{n:'التخصصات',d:'إنشائي / معماري / ميكانيكي / كهربائي / صحي + الكماليات',cls:()=>M.layers.map(L=>({k:L.id,n:L.name,c:L.color})).concat([{k:'X',n:'كماليات إخراجية (أثاث، أشجار، سيارات)',c:'#8FA39B',h:'للعرض فقط وليست من العقد'}]),of:e=>(e.stage||/\.stage$/.test(e.c))?'X':e.c[0]},
    level:{n:'الطوابق',d:'لون لكل طابق',cls:()=>M.levels.map((l,i)=>({k:l.id,n:l.name,c:LEVELC[i%LEVELC.length]})),of:e=>e.l},
    system:{n:'أنظمة الخدمات',d:'تكييف / مياه / صرف / إطفاء / كهرباء',cls:()=>SYSTEMS.slice(0,8).map(s=>({k:s[0],n:s[1],c:s[2]})),of:e=>sysOf(e)},
    tier:{n:'التعارضات',d:'مؤكد / مرشح اختلاف منسوب / هامشي',cls:()=>['c','k','m'].map(k=>({k,n:TIER[k].n,c:TIER[k].c})),ofi:ei=>tierOf.get(ei)||null},
    guess:{n:'التخمينات',d:'ثقة موضع كل جهاز ونوع الافتراض',cls:()=>['high','med','low','rule'].map(k=>({k,n:CONF[k].n,c:CONF[k].c})),ofi:ei=>guessInfo.get(ei)||null},
    finishF:finMode('finishF','التشطيبات — الأرضيات','رمز الأرضية في A500 (F وCSP)'),
    finishW:finMode('finishW','التشطيبات — الجدران','رمز الجدار في A500 (W)'),
    finishC:finMode('finishC','التشطيبات — الأسقف','رمز السقف في A500 (C)'),
  };
  function paint(clsIdx){ // clsIdx(ei) -> 0..14 | 255
    for(const k in groups){const G=groups[k]; if(G.lensAttr) G.lensAttr.needsUpdate=true;}
    const touched=new Set();
    for(let ei=0;ei<N;ei++){const rg=elRange[ei]; if(!rg) continue; const G=groups[rg.gk]; if(!G||!G.lensAttr) continue; G.lensAttr.array.fill(clsIdx(ei),rg.start*3,(rg.start+rg.count)*3); touched.add(G);}
    touched.forEach(G=>{G.lensAttr.needsUpdate=true;});
  }
  function setPalette(list){for(let i=0;i<16;i++) pal[i].set(0.86,0.89,0.93); list.forEach((c,i)=>{const h=hex(c.c); pal[i+1].set(h[0],h[1],h[2]);});}
  /* which legend classes are coloured: a clicked set (multi-select). Empty = all classes in the colour look, none in the white look (the model stays white / grey until a section is chosen) —
     except for a custom lens or while «عزل» is on, where empty always means all. Non-coloured elements are washed (colour look) or plain white / grey (white look, shader uMono). */
  let sel=new Set(), idxOfMode=null;
  const mono=()=>!!(U.mono&&U.mono.value>0.5);
  const emptyAll=()=>mode==='custom'||!mono()||hideRest;
  const coloured=i=>sel.size?sel.has(i):emptyAll();
  function repaint(){
    if(mode==='off'){ paint(()=>0); return; }
    if(mode==='custom'){ paint(ei=>{const k=custom.map.get(ei); return (k===undefined||!coloured(k))?(hideRest?255:0):k;}); return; }
    const D=MODES[mode]; if(!D||!idxOfMode) return;
    paint(ei=>{const e=M.els[ei]; const k=D.ofi?D.ofi(ei):D.of(e); const i=idxOfMode.get(k); return (!i||!coloured(i))?(hideRest?255:0):i;});
  }
  function set(m,opt){
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
    const total=legend.reduce((a,l)=>a+l.count,0), M1=mono(), allOn=sel.size===legend.length&&legend.length>0;
    let h=`<div class=lg-h><b>${esc(label)}</b><button type=button data-lg="off" class=mini title="إيقاف العدسة" aria-label="إيقاف العدسة">✕</button><span class=lg-btns style="flex-basis:100%"><button type=button data-lg="look" class=mini title="${M1?'العودة إلى ألوان المواد':'عرض النموذج أبيض ورمادي (تُلوَّن الأقسام التي تختارها فقط)'}">${M1?'ألوان المواد':'أبيض ورمادي'}</button>${M1&&mode!=='custom'?`<button type=button data-lg="all" class="mini${allOn?' on':''}" title="تلوين كل الأقسام أو إلغاؤه">تلوين الكل</button>`:''}<button type=button data-lg="hide" class="mini${hideRest?' on':''}" title="إخفاء ما لا يتعلق بالعدسة">عزل</button></span></div><div class=lg-b>`;
    legend.forEach((l,i)=>{const on=sel.size?sel.has(i+1):emptyAll(); h+=`<button type=button class="lg-i${sel.has(i+1)?' sel':''}${on?'':' off'}" data-lgi="${i+1}" aria-pressed="${on?'true':'false'}" title="${esc(l.h||l.n)}"><span class=lg-s style="background:${l.c}"></span><span class=lg-n>${esc(l.n)}</span><span class=lg-c>${l.count.toLocaleString('en')} عنصر</span></button>`;});
    h+=`</div><div class=lg-f>${hideRest?'العناصر غير المعنيّة مخفية ولا يمكن تحديدها':(M1?'اضغط قسمًا لتلوينه فقط — الباقي أبيض ورمادي':'العناصر غير المعنيّة تظهر باهتة')}${total?'':' — لا عناصر'} · العينات التفصيلية متوقفة أثناء العدسة</div>`;
    box.innerHTML=h; box.classList.add('on');
  }
  // legend interaction: click a class = colour it / stop colouring it (several allowed); «عزل» hides the rest; «تلوين الكل» (white look) colours every class; «أبيض / ألوان المواد» flips the look
  function toggleClass(i){ if(sel.has(i)) sel.delete(i); else sel.add(i); repaint(); renderLegend(); applyVis(); }
  function refresh(){ if(mode==='off') return; repaint(); renderLegend(); applyVis(); }
  function setSelection(arr){ sel=new Set((arr||[]).filter(i=>i>=1&&i<=legend.length)); repaint(); renderLegend(); applyVis(); }
  const box=$('lensLegend');
  if(box) box.addEventListener('click',ev=>{const b=ev.target.closest('[data-lg],[data-lgi]'); if(!b) return;
    if(b.dataset.lg==='off'){set('off'); const bt=document.querySelectorAll('#viewMenu button[data-lens]'); bt.forEach(x=>x.classList.toggle('on',x.dataset.lens==='off')); return;}
    if(b.dataset.lg==='hide'){hideRest=!hideRest; repaint(); renderLegend(); ctx.onChange&&ctx.onChange(mode); applyVis(); return;}
    if(b.dataset.lg==='all'){ if(sel.size===legend.length) sel.clear(); else legend.forEach((l,i)=>sel.add(i+1)); repaint(); renderLegend(); applyVis(); return; }
    if(b.dataset.lg==='look'){ if(ctx.setLook) ctx.setLook(mono()?'mat':'white'); return; }
    if(b.dataset.lgi){toggleClass(+b.dataset.lgi);}
  });
  /* the class of one element as painted (0 = not concerned, 255 = hidden, -1 when no lens is on): the picker skips what the lens hides and, while classes are chosen or «عزل» is on, what it only dims */
  function classOf(ei){ if(U.lensOn.value<0.5) return -1; const rg=elRange[ei]; if(!rg) return 0; const G=groups[rg.gk]; return (G&&G.lensAttr)?G.lensAttr.array[rg.start*3]:0; }
  return {set,refresh,setSelection,classOf,get restrict(){return mode!=='off'&&(hideRest||sel.size>0);},get hideRest(){return hideRest;},get solo(){return sel.size;},get selected(){return [...sel];},get mode(){return mode;},modes:Object.keys(MODES).map(k=>({id:k,n:MODES[k].n,d:MODES[k].d})),GRADE,TIER,CONF,OKABE,tierOf,guessInfo,legendOf:()=>legend};
}
window.initLens=initLens; window.LENS_PAL={GRADE,TIER,CONF,OKABE};
})();
