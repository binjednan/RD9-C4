/* ===== Lenses: colour the whole model by one property (idea: Speckle «colour by property», Navisworks / ACC clash colours, BIM Forum LOD) =====
   Every element is given a class index 1..14 (0 = «not concerned», 255 = hidden) per lens; the class is written into the per-vertex attribute aLens of its merged group and the
   shader (app.js patch) mixes the class colour into the material.  Switching a lens only rewrites that attribute (no geometry is rebuilt), so it is instant on 25k elements.
   Lenses: off | grade (data reliability) | layer (discipline) | level | system (services) | tier (clash tiers) | guess (best-guess confidence) | finish (A500 codes) | custom (set by a panel). */
(function(){
'use strict';
const OKABE={vermillion:'#D55E00',orange:'#E69F00',sky:'#56B4E9',green:'#009E73',blue:'#0072B2',purple:'#CC79A7',yellow:'#F0E442',gray:'#9AA3AD',slate:'#7B8794'};
const GRADE={d:{n:'موثّق',c:OKABE.green,h:'الموضع والمنسوب والمواصفة مقروءة من المخططات'},v:{n:'مشتق',c:OKABE.sky,h:'محسوب بقاعدة معلومة المعطيات'},a:{n:'تخمين',c:OKABE.orange,h:'اختاره النموذج لغياب البيان'},s:{n:'إخراجي',c:OKABE.gray,h:'للعرض فقط'}};
const TIER={c:{n:'تعارض مؤكد',c:OKABE.vermillion,i:'■'},k:{n:'مرشح — اختلاف منسوب',c:OKABE.orange,i:'◆'},m:{n:'هامشي',c:OKABE.slate,i:'●'}};
const CONF={high:{n:'تخمين عالي الثقة',c:OKABE.blue},med:{n:'تخمين متوسط الثقة',c:OKABE.sky},low:{n:'تخمين منخفض الثقة',c:OKABE.purple},rule:{n:'افتراض عام على نوعه',c:'#f3d9a4'}};
const LEVELC=['#440154','#482878','#3e4a89','#31688e','#26828e','#1f9e89','#35b779','#6ece58','#b5de2b'];
const SYSTEMS=[['duct','مجاري الهواء','#3b82c4'],['chw','مياه مبردة','#1d4ed8'],['cold','مياه باردة','#06b6d4'],['hot','مياه ساخنة','#ef6c3a'],['drain','صرف وأمطار','#8a6d4b'],['ff','إطفاء','#dc2626'],['elec','كهرباء','#d6a100'],['equip','معدات','#7c3aed'],['other','أخرى','#9AA3AD']];
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
  const finOf=ei=>{const e=M.els[ei]; const f=(e.a&&e.a.fin)||null; return f&&f.length?f[0]:null;};
  const FINS=Object.keys(M.fin||{}).sort((a,b)=>a.localeCompare(b,'en',{numeric:true}));
  const FINC=['#c9a227','#8c5a3c','#6a9d3c','#3b82c4','#cc79a7','#e3732f','#56b4e9','#7b6fd1','#d95a5a','#2aa198','#9a7b4f','#b5651d','#4f7f4f','#c34f8b'];
  const MODES={
    grade:{n:'موثوقية البيانات',d:'موثّق / مشتق / تخمين / إخراجي',cls:()=>['d','v','a','s'].map(k=>({k,n:GRADE[k].n,c:GRADE[k].c,h:GRADE[k].h})),of:e=>{const q=e.q||'ddd'; if(q==='sss') return 's'; return ['d','v','a'][Math.max(['d','v','a'].indexOf(q[0]),['d','v','a'].indexOf(q[1]),['d','v','a'].indexOf(q[2]))];}},
    layer:{n:'التخصصات',d:'إنشائي / معماري / ميكانيكي / كهربائي / صحي',cls:()=>M.layers.map(L=>({k:L.id,n:L.name,c:L.color})),of:e=>e.c[0]},
    level:{n:'الطوابق',d:'لون لكل طابق',cls:()=>M.levels.map((l,i)=>({k:l.id,n:l.name,c:LEVELC[i%LEVELC.length]})),of:e=>e.l},
    system:{n:'أنظمة الخدمات',d:'تكييف / مياه / صرف / إطفاء / كهرباء',cls:()=>SYSTEMS.slice(0,8).map(s=>({k:s[0],n:s[1],c:s[2]})),of:e=>sysOf(e)},
    tier:{n:'التعارضات',d:'مؤكد / مرشح اختلاف منسوب / هامشي',cls:()=>['c','k','m'].map(k=>({k,n:TIER[k].n,c:TIER[k].c})),ofi:ei=>tierOf.get(ei)||null},
    guess:{n:'التخمينات',d:'ثقة موضع كل جهاز ونوع الافتراض',cls:()=>['high','med','low','rule'].map(k=>({k,n:CONF[k].n,c:CONF[k].c})),ofi:ei=>guessInfo.get(ei)||null},
    finish:{n:'التشطيبات (A500)',d:'لون لكل رمز تشطيب',cls:()=>FINS.slice(0,14).map((f,i)=>({k:f,n:f+' — '+((M.fin[f]||[''])[0]),c:M.fin[f]?M.fin[f][1]:FINC[i%FINC.length]})),ofi:ei=>{const f=finOf(ei); return f&&FINS.indexOf(f)>=0&&FINS.indexOf(f)<14?f:null;}},
  };
  function paint(clsIdx){ // clsIdx(ei) -> 0..14 | 255
    for(const k in groups){const G=groups[k]; if(G.lensAttr) G.lensAttr.needsUpdate=true;}
    const touched=new Set();
    for(let ei=0;ei<N;ei++){const rg=elRange[ei]; if(!rg) continue; const G=groups[rg.gk]; if(!G||!G.lensAttr) continue; G.lensAttr.array.fill(clsIdx(ei),rg.start*3,(rg.start+rg.count)*3); touched.add(G);}
    touched.forEach(G=>{G.lensAttr.needsUpdate=true;});
  }
  function setPalette(list){for(let i=0;i<16;i++) pal[i].set(0.86,0.89,0.93); list.forEach((c,i)=>{const h=hex(c.c); pal[i+1].set(h[0],h[1],h[2]);});}
  function set(m,opt){
    opt=opt||{}; mode=m; hideRest=!!opt.hideRest;
    if(m==='off'){U.lensOn.value=0; legend=[]; custom=null; label=''; paint(()=>0); renderLegend(); ctx.onChange&&ctx.onChange(mode); applyVis(); return;}
    if(m==='custom'){const C=opt.classes||[]; setPalette(C); custom={C,map:opt.map}; legend=C.map(c=>({...c,n:c.n,count:0})); paint(ei=>{const k=opt.map.get(ei); return k===undefined?(hideRest?255:0):k;});
      legend.forEach((l,i)=>{let n=0; opt.map.forEach(v=>{if(v===i+1) n++;}); l.count=n;}); U.lensOn.value=1; label=opt.label||'تلوين مخصّص'; renderLegend(); ctx.onChange&&ctx.onChange(mode); applyVis(); return;}
    const D=MODES[m]; if(!D) return; const cls=D.cls(); setPalette(cls); const idxOf=new Map(cls.map((c,i)=>[c.k,i+1])); const counts=new Array(cls.length).fill(0);
    paint(ei=>{const e=M.els[ei]; const k=D.ofi?D.ofi(ei):D.of(e); const i=idxOf.get(k); if(!i) return hideRest?255:0; counts[i-1]++; return i;});
    legend=cls.map((c,i)=>({...c,count:counts[i]})); U.lensOn.value=1; label=D.n; custom=null; renderLegend(); ctx.onChange&&ctx.onChange(mode); applyVis();
  }
  function renderLegend(){
    const box=$('lensLegend'); if(!box) return;
    if(mode==='off'){box.classList.remove('on'); box.innerHTML=''; return;}
    const total=legend.reduce((a,l)=>a+l.count,0);
    let h=`<div class=lg-h><b>${esc(label)}</b><span class=lg-btns><button type=button data-lg="hide" class="mini${hideRest?' on':''}" title="إخفاء ما لا يتعلق بالعدسة">عزل</button><button type=button data-lg="off" class=mini title="إيقاف العدسة" aria-label="إيقاف العدسة">✕</button></span></div><div class=lg-b>`;
    legend.forEach((l,i)=>{h+=`<button type=button class=lg-i data-lgi="${i+1}" title="${esc(l.h||l.n)}"><span class=lg-s style="background:${l.c}"></span><span class=lg-n>${esc(l.n)}</span><span class=lg-c>${l.count.toLocaleString('en')} عنصر</span></button>`;});
    h+=`</div><div class=lg-f>العناصر غير المعنيّة تظهر باهتة${total?'':' — لا عناصر'}</div>`;
    box.innerHTML=h; box.classList.add('on');
  }
  // legend interaction: click a class = isolate it (others dimmed), click again = back to all classes
  let solo=0;
  function soloClass(i){ solo=(solo===i)?0:i; const keep=solo; paint(ei=>{const rg=elRange[ei]; const G=groups[rg.gk]; return 0;}); /* repaint below */
    // re-run the mode with only the chosen class coloured
    const m=mode; if(m==='custom'){ set('custom',{classes:custom.C,map:new Map([...custom.map].filter(([e,v])=>!keep||v===keep)),hideRest,label}); return; }
    const D=MODES[m]; if(!D) return; const cls=D.cls(); setPalette(cls); const idxOf=new Map(cls.map((c,k)=>[c.k,k+1]));
    paint(ei=>{const e=M.els[ei]; const k=D.ofi?D.ofi(ei):D.of(e); const i=idxOf.get(k); if(!i||(keep&&i!==keep)) return hideRest?255:0; return i;}); wake(); }
  const box=$('lensLegend');
  if(box) box.addEventListener('click',ev=>{const b=ev.target.closest('[data-lg],[data-lgi]'); if(!b) return;
    if(b.dataset.lg==='off'){set('off'); const bt=document.querySelectorAll('#viewMenu button[data-lens]'); bt.forEach(x=>x.classList.toggle('on',x.dataset.lens==='off')); return;}
    if(b.dataset.lg==='hide'){hideRest=!hideRest; const m=mode; if(m==='custom') set('custom',{classes:custom.C,map:custom.map,hideRest,label}); else set(m,{hideRest}); return;}
    if(b.dataset.lgi){soloClass(+b.dataset.lgi); document.querySelectorAll('#lensLegend .lg-i').forEach(x=>x.classList.toggle('sel',solo&&+x.dataset.lgi===solo));}
  });
  return {set,get mode(){return mode;},modes:Object.keys(MODES).map(k=>({id:k,n:MODES[k].n,d:MODES[k].d})),GRADE,TIER,CONF,OKABE,tierOf,guessInfo,legendOf:()=>legend};
}
window.initLens=initLens; window.LENS_PAL={GRADE,TIER,CONF,OKABE};
})();
