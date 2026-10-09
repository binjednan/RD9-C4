/* ===== Issue centre («مركز المتابعة»): clashes and best-guess decisions in ONE design =====
   Ideas taken (restated, not copied): Navisworks / ACC Model Coordination — clashes grouped per service run and obstruction, with a status; Revizto — pins on the 2-D sheet and in 3-D, clash matrix;
   Solibri — severity as traffic-light tiers; BCF — one camera view-point per issue; Sketchfab — previous / next and autopilot; Shneiderman — overview first, filter, details on demand.
   Data: M.clashes / M.clashGroups (pipeline/clash_tiers.py) and M.guesses (pipeline/guesses.py).  Engine of the marker, access route and walking tour: clash.js.  2-D plan: planmap.js.
   Layout: priorities (group cards) | map (plan with pins and before→after arrows) | matrix (system × obstruction, level × tier, kind × discipline); detail drawer in the info dock. */
(function(){
'use strict';
const TRANK={c:0,k:1,m:2};
const IMPACT={high:{n:'مرتفع الأثر',c:'#0072B2',i:'▲',r:0},med:{n:'متوسط الأثر',c:'#56B4E9',i:'◆',r:1},low:{n:'منخفض الأثر',c:'#9AA3AD',i:'●',r:2}};
const CONFI={high:'●',med:'◆',low:'▲'};
const CONFN={high:'نقل ≤30 سم',med:'نقل ≤100 سم',low:'نقل أكبر / تغيّر تركيب'};
const CST={open:'#8b949e',checking:'#bf8700',resolved:'#1a7f37',accepted:'#0969da',false:'#6e7781',design:'#cf222e',historical:'#8b949e'};
const CDONE={resolved:1,accepted:1,false:1};
const GST={open:'لم يؤشر المستخدم',checking:'قيد مراجعة المستخدم',verified:'تأشير مستخدم: مطابق للمصدر',wrong:'تأشير مستخدم: يخالف المصدر',pending:'متابعة معلقة',historical:'تأشير تاريخي — يحتاج مراجعة'};
const GSTC={open:'#8b949e',checking:'#bf8700',verified:'#1a7f37',wrong:'#cf222e',pending:'#8250df',historical:'#8b949e'};
const GDONE={verified:1};
const OBSC=[['beam','جسر'],['col','عمود'],['wall','جدار/نواة'],['svc','خدمة أخرى']];
const LAYS=[['S','إنشائي'],['A','معماري'],['M','ميكانيكي'],['E','كهربائي'],['P','صحي وإطفاء']];
const MOUNT={wall:'جدار/عمود/كسوة',ceil:'سقف/بلاطة/جسر',floor:'سطح الأرضية',fcu:'غلاف وحدة FCU',equip:'غلاف آلة',stand:'قائم من الأرضية',hang:'تعليق بالسقف'};
const LVAB={B:'ب',G:'أ',R:'س',T:'ع'};
const TLAB={c:'يحتاج تنسيقًا',k:'مرشح منسوب/شكل',m:'أثر صغير'};
const TTITLE={c:'تداخل يحتاج تنسيقًا؛ إثبات المصدر والمنسوب في مطابقة المشروع',k:'مرشح منسوب أو شكل: الحل الرأسي يحتاج تفاصيل المصدر',m:'أثر صغير هندسيًا؛ الحجم وحده لا يثبت أنه مقبول'};
const TFULL={c:'تداخل يحتاج تنسيقًا',k:'مرشح اختلاف منسوب / شكل',m:'أثر صغير يحتاج تحققًا'};
const THEAD={c:'تداخلات تحتاج تنسيقًا',k:'مرشحة — اختلاف منسوب / شكل',m:'آثار صغيرة تحتاج تحققًا'};
const PAGE=40, PAGE_LOC=30, AP_N=10, AP_MS=6500, EL_LIST_MAX=500;
const plural=(n,one,two,few,many)=>n===1?one:n===2?two:(n>=3&&n<=10)?n+' '+few:n+' '+many;
const P_POS=n=>plural(n,'موضع واحد','موضعان','مواضع','موضعًا'), P_GRP=n=>plural(n,'مجموعة واحدة','مجموعتان','مجموعات','مجموعة'),
      P_EL=n=>plural(n,'عنصر واحد','عنصران','عناصر','عنصرًا'), P_DEC=n=>plural(n,'قرار واحد','قراران','قرارات','قرارًا'), P_RULE=n=>plural(n,'افتراض واحد','افتراضان','افتراضات','افتراضًا');
const NUM=v=>'<span class="num">'+v+'</span>';
const F2=z=>(z<0?'−':'')+Math.abs(z).toFixed(2);
const shortSt=s=>String(s).split(' — ')[0].replace(/\s*\(.*\)$/,'');
const TIPS={
  clash:'تقاطعات في المجسم مرتبة حسب الحاجة إلى التنسيق. الحكم المثبت من المخططات وفجوات المنسوب يظهران في «مطابقة المشروع».',
  guess:'اختيارات سابقة للمجسم عند غياب بيان في المصادر المرفقة (موضع، منسوب، مقاس، مادة). تأشير المستخدم سجل متابعة محلي؛ تحقق المصدر الحالي وحدود المنسوب والمقاس يظهران في «مطابقة المشروع».',
  conf:'فئات مسافة النقل السابقة: حتى 30 سم، حتى 100 سم، أو أكبر من ذلك/تغيّر تركيب. المسافة لا تثبت صحة الموضع أو المنسوب أو النوع. «القرارات الفردية» نقل أو سحب سابق إلى مضيف؛ «الافتراضات العامة» تخص مقاسًا أو مادة أو تمثيلًا. التأشير المحفوظ لا يثبت التنفيذ في الموقع.'
};
// A synchronous context fingerprint for local annotations, not a source-proof hash.
function annotationFingerprint(value){
  const stable=v=>Array.isArray(v)?v.map(stable):v&&typeof v==='object'?Object.keys(v).sort().reduce((o,k)=>{if(v[k]!==undefined)o[k]=stable(v[k]);return o;},{}):v;
  const text=JSON.stringify(stable(value));let a=2166136261,b=2246822507;
  for(let i=0;i<text.length;i++){a=Math.imul(a^text.charCodeAt(i),16777619);b=Math.imul(b^text.charCodeAt(i),3266489909);}
  return (a>>>0).toString(16).padStart(8,'0')+(b>>>0).toString(16).padStart(8,'0');
}
/* ---- clash cross-section sketch (pure functions) ---- */
/* reference implementation of the clash cross-section sketch (pure functions: no DOM access, no THREE) */
var SK_UID=0;
function zRangeAt(e,xcm,ycm){            // vertical extent [z0,z1] in metres of element e near the plan point (xcm,ycm)
  const g=e.g,k=g[0];
  if(k==='t'||k==='d'){
    const pts=g[1]; let best=1e18,bz=pts[0][2];
    for(let i=0;i<pts.length-1;i++){const a=pts[i],b=pts[i+1],dx=b[0]-a[0],dy=b[1]-a[1],L2=dx*dx+dy*dy||1e-9;
      let t=((xcm-a[0])*dx+(ycm-a[1])*dy)/L2; t=Math.max(0,Math.min(1,t));
      const px=a[0]+t*dx,py=a[1]+t*dy,d=(px-xcm)*(px-xcm)+(py-ycm)*(py-ycm);
      if(d<best){best=d;bz=a[2]+t*(b[2]-a[2]);}}
    const h=(k==='t'?g[2]:g[3])/200; return [bz-h,bz+h];}
  if(k==='b') return [g[6],g[7]]; if(k==='cyl') return [g[4],g[5]]; if(k==='r') return [g[5],g[6]]; if(k==='p') return [g[2],g[3]];
  return null;}
function sketchInputs(M,c){               // -> null when no meaningful section can be drawn
  if(c.tier==='m'||!c.void) return null;
  const A=M.els[c.a],B=M.els[c.b]; const xcm=c.pt[0]*100,ycm=-c.pt[2]*100;
  const oid=String(c.oid||''); let okind=null;
  if(/^P\.tank/.test(String(c.sid||''))) return null;
  if(/^S\.beam/.test(oid)){ if(!c.band) return null; okind='beam'; } else if(/^S\.(col|wall)/.test(oid)) okind='full'; else if(/^[MPE]\./.test(oid)) okind='svc'; else return null;
  const sr=zRangeAt(A,xcm,ycm); if(!sr) return null;
  const orr=okind==='svc'?zRangeAt(B,xcm,ycm):null; if(okind==='svc'&&!orr) return null;
  const zc=c.void[0],zs=c.void[1],need=c.need||(sr[1]-sr[0]);
  let sug=null;
  if(c.tier==='k'){
    if(okind==='beam'&&c.band){const hi=c.band[1]-0.05; sug=[hi-need,hi];}
    else if(okind==='svc'){let hi=orr[0]-0.05,lo=hi-need; if(lo>=zc-1e-6) sug=[lo,hi]; else {lo=orr[1]+0.05; hi=lo+need; if(hi<=zs+1e-6) sug=[lo,hi];}}}
  return {zc,zs,have:c.void[2]===1,sz0:sr[0],sz1:sr[1],okind,oz0:okind==='beam'?c.band[1]:(orr?orr[0]:null),oz1:orr?orr[1]:null,tier:c.tier,sug};}
function sketchSVG(p,labels){
  const L=Object.assign({ceil:'سقف مستعار',noceil:'لا سقف مستعار',slab:'بلاطة',beam:'جسر',full:'عنصر ممتد',svc:'خدمة أخرى',cur:'الحالي',sug:'المقترح'},labels||{});
  const W=260,H=124,X0=66,X1=254,YT=8,YB=116,uid='ish'+(++SK_UID);
  const zlo=p.zc-0.28,zhi=p.zs+0.22,span=zhi-zlo;
  const Y=z=>YT+(zhi-Math.min(zhi,Math.max(zlo,z)))/span*(YB-YT);
  const F=z=>(z<0?'−':'')+Math.abs(z).toFixed(2);
  const col={c:'#D55E00',k:'#DB7F4A',m:'#7B8794'}[p.tier]||'#7B8794';
  const ox=p.okind==='full'?[150,196]:p.okind==='beam'?[136,210]:[146,200];
  let s=`<svg class="is-sk" viewBox="0 0 ${W} ${H}" width="100%" style="direction:ltr" role="img" aria-label="مقطع رأسي في فراغ السقف">`;
  s+=`<defs><pattern id="${uid}h" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#dfe4ea"/><line x1="0" y1="0" x2="0" y2="6" stroke="#9aa3ad" stroke-width="1.2"/></pattern></defs>`;
  s+=`<rect x="0" y="0" width="${W}" height="${H}" rx="8" fill="#fbfcfe"/>`;
  // slab above the void, ceiling below it
  s+=`<rect x="${X0}" y="${YT}" width="${X1-X0}" height="${(Y(p.zs)-YT).toFixed(1)}" fill="url(#${uid}h)"/>`;
  s+=`<line x1="${X0}" y1="${Y(p.zs).toFixed(1)}" x2="${X1}" y2="${Y(p.zs).toFixed(1)}" stroke="#5b6573" stroke-width="1.4"/>`;
  s+=p.have?`<rect x="${X0}" y="${Y(p.zc).toFixed(1)}" width="${X1-X0}" height="${(YB-Y(p.zc)).toFixed(1)}" fill="#eceff3"/><line x1="${X0}" y1="${Y(p.zc).toFixed(1)}" x2="${X1}" y2="${Y(p.zc).toFixed(1)}" stroke="#5b6573" stroke-width="1.4"/>`
            :`<line x1="${X0}" y1="${Y(p.zc).toFixed(1)}" x2="${X1}" y2="${Y(p.zc).toFixed(1)}" stroke="#5b6573" stroke-width="1.2" stroke-dasharray="4 3"/>`;
  s+=`<text x="${X1-3}" y="${(Y(p.zs)-3).toFixed(1)}" font-size="8.5" fill="#445" text-anchor="end">${L.slab}</text>`;
  s+=`<text x="${X1-3}" y="${(Y(p.zc)+10).toFixed(1)}" font-size="8.5" fill="#667" text-anchor="end">${p.have?L.ceil:L.noceil}</text>`;
  // obstacle
  let oy0,oy1;
  if(p.okind==='full'){oy0=Y(p.zs);oy1=Y(p.zc);} else if(p.okind==='beam'){oy0=Y(p.zs);oy1=Y(p.oz0);} else {oy0=Y(p.oz1);oy1=Y(p.oz0);}
  s+=`<rect x="${ox[0]}" y="${Math.min(oy0,oy1).toFixed(1)}" width="${ox[1]-ox[0]}" height="${Math.abs(oy1-oy0).toFixed(1)}" fill="${p.okind==='svc'?'#f4d9b4':'#9aa3ad'}" stroke="#4a5360" stroke-width="1.1"/>`;
  const ol=p.okind==='beam'?L.beam:p.okind==='full'?L.full:L.svc; const oly=Math.min(oy0,oy1)+Math.abs(oy1-oy0)/2+3;
  s+=`<text x="${(ox[0]+ox[1])/2}" y="${oly.toFixed(1)}" font-size="8.5" fill="#fff" stroke="#3a4350" stroke-width="2.4" paint-order="stroke" text-anchor="middle">${ol}</text>`;
  // suggested position
  if(p.sug){const y0=Y(p.sug[1]),y1=Y(p.sug[0]);
    s+=`<rect x="${X0}" y="${y0.toFixed(1)}" width="${X1-X0}" height="${Math.max(3,y1-y0).toFixed(1)}" rx="2" fill="#009E7326" stroke="#009E73" stroke-width="1.4" stroke-dasharray="4 3"/>`;
    const my=(Y((p.sz0+p.sz1)/2)), sy=(y0+y1)/2; if(Math.abs(sy-my)>6){
      s+=`<line x1="${X0+22}" y1="${my.toFixed(1)}" x2="${X0+22}" y2="${sy.toFixed(1)}" stroke="#009E73" stroke-width="1.6"/><path d="M${X0+22} ${sy.toFixed(1)} l-4 ${sy>my?-7:7} l8 0 z" fill="#009E73"/>`;}
    s+=`<text x="${X1-4}" y="${(sy+3).toFixed(1)}" font-size="8.5" fill="#00694d" text-anchor="end">${L.sug}</text>`;}
  // current service (drawn last = on top), the part crossing the obstacle in the tier colour
  const y0=Y(p.sz1),y1=Y(p.sz0),hh=Math.max(4,y1-y0);
  s+=`<rect x="${X0}" y="${y0.toFixed(1)}" width="${X1-X0}" height="${hh.toFixed(1)}" rx="2" fill="#0072B2" fill-opacity=".82" stroke="#0b4f7a" stroke-width="1"/>`;
  const ya=Math.max(y0,Math.min(oy0,oy1)),yb=Math.min(y0+hh,Math.max(oy0,oy1));
  if(yb>ya) s+=`<rect x="${ox[0]}" y="${ya.toFixed(1)}" width="${ox[1]-ox[0]}" height="${(yb-ya).toFixed(1)}" fill="${col}" stroke="#7a2e00" stroke-width="1.1"/>`;
  s+=`<text x="${X0+3}" y="${(y0-2.5).toFixed(1)}" font-size="8.5" fill="#0b4f7a">${L.cur}</text>`;
  // elevation labels in the left gutter (priority order, no overlaps)
  const lab=[[p.zs,'#445'],[p.zc,'#445']]; if(p.sug) lab.push([(p.sug[0]+p.sug[1])/2,'#00694d']); lab.push([(p.sz0+p.sz1)/2,'#0b4f7a']); if(p.okind==='beam') lab.push([p.oz0,'#445']);
  const used=[]; lab.forEach(([z,c])=>{const y=Y(z); if(used.some(u=>Math.abs(u-y)<9)) return; used.push(y); s+=`<text x="${X0-4}" y="${(y+3).toFixed(1)}" font-size="9" fill="${c}" text-anchor="end">${F(z)}</text>`;});
  return s+'</svg>';}

function initIssues(ctx){
  const {M,THREE,scene,camera,controls,renderer,$,esc,normAr,LVL,UNITS,wake,flyTo,flyToBox,ensureVisible,highlight,addHL,clearHL,toast,setGhost,focusEl,bboxOf,setLens,levelVisible,exploded,showDrawer,hideDrawer,CLASH,LENS,PAL}=ctx;
  const select=ctx.select, PlanMap=ctx.PlanMap;
  const box=$('issuesBox'), sec=document.querySelector('.acc[data-sec="pIssues"]');
  const els=M.els, clashes=M.clashes||[], GU=M.guesses||{rules:[],items:[],kinds:{},impact:{}};
  const CLS={open:'لم يؤشر المستخدم',checking:'قيد مراجعة المستخدم',resolved:'تأشير مستخدم: عولج',accepted:'تأشير مستخدم: مقبول',false:'تأشير مستخدم: ليس تعارضًا',design:'تأشير مستخدم: يحتاج قرارًا',historical:'تأشير تاريخي — يحتاج مراجعة'}, CLKEYS=Object.keys(CLS).filter(k=>k!=='historical');
  const API={open(){},focus(){},next(){},prev(){},close(){},autopilot(){},setFilter(){},setStatus(){},state(){return {built:false};},csv(){return '';},tap(){return false;},frame(){},pinAt(){return null;},get active(){return false;}};
  if(!box||!sec||!PAL) return API;

  /* ---------------- derived data (computed once) ---------------- */
  const idOf=new Map(); els.forEach((e,i)=>idOf.set(e.id,i));
  const typeEls=new Map(); els.forEach((e,i)=>{let a=typeEls.get(e.t); if(!a){a=[]; typeEls.set(e.t,a);} a.push(i);});
  const tierOf=c=>c.tier||'k';
  const obsOf=c=>{const o=String(c.oid||''); return /^S\.beam/.test(o)?'beam':/^S\.col/.test(o)?'col':/^S\.wall/.test(o)?'wall':'svc';};
  const GMETA=new Map((M.clashGroups||[]).map(g=>[g.k,g]));
  const TOT={c:0,k:0,m:0}; clashes.forEach(c=>{TOT[tierOf(c)]++;});
  const elName=ei=>{const e=els[ei],T=M.types&&M.types[e?.t]; if(!e) return 'عنصر غير متاح'; return (e.mark||e.id||e.t||e.c||'عنصر غير مسمّى')+' — '+((T&&T.n)||ctx.CATS?.[e.c]?.name||e.t||e.c||e.id||'عنصر غير مسمّى');};
  const clashOtherName=(c,ei)=>{
    const named=ei===c.a?c.obs:c.svc;
    if(typeof named==='string'&&named.trim()) return named.trim();
    const other=els[ei===c.a?c.b:c.a];
    if(ctx.elementDisplayName) return ctx.elementDisplayName(other);
    const T=other&&M.types?.[other.t];
    return other?.mark||T?.n||ctx.CATS?.[other?.c]?.name||other?.id||other?.t||other?.c||'عنصر غير متاح';
  };
  const unitName=ei=>{const u=els[ei].u; if(!u) return null; const x=UNITS.find(y=>y.id===u); return x?x.name:null;};
  const lvName=l=>(LVL[l]&&LVL[l].name)||l, lvAb=l=>LVAB[l]||l;
  const RULES=(GU.rules||[]).map(r=>{
    const R={r,items:[],layer:'',lv:{},_idx:null,hasItems:false};
    R.idx=()=>{ if(R._idx) return R._idx; let a=r.els; if(!a){a=[]; (r.types||[]).forEach(t=>{const x=typeEls.get(t); if(x) for(let k=0;k<x.length;k++) a.push(x[k]);});} R._idx=a; return a; };
    const cnt={}; R.idx().forEach(i=>{const e=els[i]; R.lv[e.l]=(R.lv[e.l]||0)+1; const L=e.c[0]; cnt[L]=(cnt[L]||0)+1;});
    let best='',bn=0; ['S','A','M','E','P'].forEach(L=>{if((cnt[L]||0)>bn){bn=cnt[L]; best=L;}}); R.layer=best;
    return R;});
  const RULE_BY_ID=new Map(RULES.map(R=>[R.r.id,R]));
  const ITEMS=(GU.items||[]).map((it,ii)=>{const e=els[it.e]; const R=RULE_BY_ID.get(it.r); if(R) R.items.push(ii); return {it,ei:it.e,e,key:it.r+'|'+e.id};});
  RULES.forEach(R=>{R.hasItems=R.items.length>0;});
  const IMPT={high:0,med:0,low:0}; RULES.forEach(R=>{IMPT[R.r.impact]++;});
  const aftC=new Map();
  function after(ii){ let a=aftC.get(ii); if(a) return a; const b=bboxOf([ITEMS[ii].ei]); a={c:b.c,mn:b.mn,mx:b.mx,xcm:b.c[0]*100,ycm:-b.c[2]*100,zb:b.mn[1]}; aftC.set(ii,a); return a; }
  try{ const bd=$('accN_pIssues'); if(bd) bd.textContent=String(TOT.c+TOT.k); }catch(e){}

  /* ---------------- statuses and notes (this device only) ---------------- */
  const KEY='c4issues'; let ST={v:2,c:{},g:{},r:{}};
  function saveStore(){ try{localStorage.setItem(KEY,JSON.stringify(ST));}catch(e){ toast('تعذّر الحفظ على هذا الجهاز'); } }
  (function loadStore(){
    let o=null; try{o=JSON.parse(localStorage.getItem(KEY)||'null');}catch(e){}
    if(o&&(o.v===1||o.v===2)){ST={v:2,c:o.c||{},g:o.g||{},r:o.r||{}}; return;}
    try{ let moved=false; for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i); if(k&&k.indexOf('c4clash:')===0){ let v=null; try{v=JSON.parse(localStorage.getItem(k)||'null');}catch(e){} if(v&&(v.st||v.tx)){ST.c[k.slice(8)]={st:v.st||'open',tx:v.tx||'',ts:v.ts||''}; moved=true;} } } if(moved) saveStore(); }catch(e){}
  })();
  const bagOf=kind=>ST[kind==='clash'?'c':kind==='guess'?'g':'r'];
  const keyOf=(kind,id)=>kind==='clash'?clashes[id].id:kind==='guess'?ITEMS[id].key:id;
  const entryOf=(kind,id)=>bagOf(kind)[keyOf(kind,id)]||null;
  const contextCache=new Map(),clashIndex=new Map(clashes.map((c,i)=>[c.id,i]));
  const elementContext=e=>({id:e.id,c:e.c,l:e.l,g:e.g,t:e.t,m:e.m,a:e.a||{},sources:(e.s||[]).map(i=>M.sp?.[i]??i),type:M.types?.[e.t]||{},source_xy_status:M.componentReview?.status_by_id?.[e.id]||'unverified'});
  function annotationContext(kind,id){
    const key=kind+'|'+keyOf(kind,id);if(contextCache.has(key))return contextCache.get(key);
    let facts;
    if(kind==='clash'){const c=clashes[id];facts={elements:[elementContext(els[c.a]),elementContext(els[c.b])],kind:c.k,level:c.l,volume:c.v,point:c.pt,tier:c.tier,checks:c.classification_checks};}
    else if(kind==='guess'){const I=ITEMS[id];facts={element:elementContext(I.e),decision:{...I.it,e:I.e.id},rule:RULE_BY_ID.get(I.it.r)?.r?.id};}
    else {const R=RULE_BY_ID.get(id);facts={rule:R?{...R.r,els:undefined}:id,elements:R?R.idx().map(i=>elementContext(els[i])).sort((a,b)=>a.id.localeCompare(b.id)):[]};}
    const ctx={basis:'geometry_type_source_context_v1',fingerprint:annotationFingerprint(facts),viewer_version:String(ctxVersion())};contextCache.set(key,ctx);return ctx;
  }
  function ctxVersion(){return ctx.version||document.getElementById('ver')?.textContent||'غير مسجل';}
  const isCurrent=(kind,id,e)=>!!(e?.context&&e.context.basis==='geometry_type_source_context_v1'&&e.context.fingerprint===annotationContext(kind,id).fingerprint);
  function localStatus(kind,id,fallback){const e=entryOf(kind,id);return e?(isCurrent(kind,id,e)?e.st||'open':'historical'):(fallback&&fallback!=='open'?'historical':'open');}
  function putEntry(kind,id,st,tx){
    const bag=bagOf(kind),k=keyOf(kind,id),old=bag[k];
    if((!st||st==='open')&&!tx&&!old) delete bag[k];
    else {const history=old?.history?[...old.history]:[];if(old){const previous={...old};delete previous.history;history.push(previous);}bag[k]={st:st||'open',tx:tx||'',ts:new Date().toISOString(),context:annotationContext(kind,id),history};}
    saveStore();
  }
  const clashStatus=c=>localStatus('clash',clashIndex.get(c.id),c.st);
  const itemStatus=ii=>localStatus('guess',ii);
  const ruleStatus=rid=>localStatus('rule',rid);

  /* ---------------- state and filters ---------------- */
  const defaults=k=>k==='clash'?{tiers:{c:1,k:1,m:0},lv:new Set(),sys:'',obs:'',st:'',q:'',sort:'prio'}:{imps:{high:1,med:1,low:1},lv:new Set(),kind:'',layer:'',st:'',q:'',sort:'prio'};
  const S={kind:'clash',view:'list',page:{clash:PAGE,guess:PAGE},open:new Set(),pageLoc:{},sel:null,mapLevel:null,pins:true,lens:false,ap:null,ghost:8,how:false,adv:false,qn:{clash:'',guess:''},f:{clash:defaults('clash'),guess:defaults('guess')}};
  const sameSet=(a,b)=>a.size===b.size&&[...a].every(x=>b.has(x));
  function isDefault(kind){ const f=S.f[kind],d=defaults(kind); if(f.lv.size||f.st||f.q||f.sort!==d.sort) return false;
    if(kind==='clash') return !f.sys&&!f.obs&&['c','k','m'].every(t=>!!f.tiers[t]===!!d.tiers[t]);
    return !f.kind&&!f.layer&&['high','med','low'].every(t=>!!f.imps[t]===!!d.imps[t]); }
  function statusMatch(sel,st,done){ return sel===''||(sel==='*open'?!done[st]:st===sel); }
  const cTxt=new Map(), rTxt=new Map();
  function clashText(ci){ let t=cTxt.get(ci); if(t===undefined){ const c=clashes[ci]; t=normAr([c.id,c.ea,c.eb,c.svc,c.obs,c.sys,lvName(c.l),els[c.a].mark||'',els[c.b].mark||''].join(' ')); cTxt.set(ci,t);} return t; }
  function ruleText(R){ let t=rTxt.get(R.r.id); if(t===undefined){ const r=R.r; t=normAr([r.id,r.title,r.why,r.how||'',r.basis,r.verify,(GU.kinds||{})[r.kind]||'',R.items.map(ii=>ITEMS[ii].e.id+' '+(ITEMS[ii].e.mark||'')).join(' ')].join(' ')); rTxt.set(r.id,t);} return t; }
  function matchClash(ci,skip){ const c=clashes[ci],f=S.f.clash; skip=skip||{};
    if(!skip.tier&&!f.tiers[tierOf(c)]) return false;
    if(!skip.lv&&f.lv.size&&!f.lv.has(c.l)) return false;
    if(!skip.sys&&f.sys&&c.sys!==f.sys) return false;
    if(!skip.obs&&f.obs&&obsOf(c)!==f.obs) return false;
    if(!statusMatch(f.st,clashStatus(c),CDONE)) return false;
    if(S.qn.clash&&clashText(ci).indexOf(S.qn.clash)<0) return false;
    return true; }
  function matchRule(R,skip){ const f=S.f.guess,r=R.r; skip=skip||{};
    if(!f.imps[r.impact]) return false;
    if(!skip.kind&&f.kind&&r.kind!==f.kind) return false;
    if(!skip.layer&&f.layer&&R.layer!==f.layer) return false;
    if(!statusMatch(f.st,ruleStatus(r.id),GDONE)) return false;
    if(!skip.lv&&f.lv.size){ let ok=false; f.lv.forEach(l=>{if(R.lv[l]>0) ok=true;}); if(!ok) return false; }
    if(S.qn.guess&&ruleText(R).indexOf(S.qn.guess)<0) return false;
    return true; }
  /* rows (cached until the next refresh) */
  let ROWS={clash:null,guess:null};
  function clashRows(){
    const by=new Map(),out=[];
    for(let ci=0;ci<clashes.length;ci++){ if(!matchClash(ci)) continue; const c=clashes[ci]; let g=by.get(c.gk);
      if(!g){ g={gk:c.gk,meta:GMETA.get(c.gk)||{svc:c.svc,obs:c.obs,sys:c.sys,l:c.l},idx:[],tier:'m',vol:0,nc:0,nk:0,nm:0}; by.set(c.gk,g); out.push(g); }
      g.idx.push(ci); g.vol+=c.v||0; const t=tierOf(c); if(t==='c') g.nc++; else if(t==='k') g.nk++; else g.nm++; }
    out.forEach(g=>{ g.idx.sort((a,b)=>TRANK[tierOf(clashes[a])]-TRANK[tierOf(clashes[b])]||(clashes[b].v||0)-(clashes[a].v||0)); g.tier=g.nc?'c':g.nk?'k':'m'; });
    const prio=(a,b)=>TRANK[a.tier]-TRANK[b.tier]||b.nc-a.nc||b.vol-a.vol, s=S.f.clash.sort;
    out.sort(s==='vol'?(a,b)=>b.vol-a.vol||prio(a,b):s==='n'?(a,b)=>b.idx.length-a.idx.length||prio(a,b):s==='lvl'?(a,b)=>LVL[a.meta.l].idx-LVL[b.meta.l].idx||prio(a,b):prio);
    return out; }
  function ruleRows(){
    const out=RULES.filter(R=>matchRule(R)),kinds=Object.keys(GU.kinds||{}),s=S.f.guess.sort;
    const prio=(a,b)=>((b.hasItems?1:0)-(a.hasItems?1:0))||IMPACT[a.r.impact].r-IMPACT[b.r.impact].r||b.r.n-a.r.n;
    out.sort(s==='n'?(a,b)=>b.r.n-a.r.n||prio(a,b):s==='kind'?(a,b)=>kinds.indexOf(a.r.kind)-kinds.indexOf(b.r.kind)||prio(a,b):prio);
    return out; }
  function getRows(kind){ kind=kind||S.kind; if(!ROWS[kind]) ROWS[kind]=kind==='clash'?clashRows():ruleRows(); return ROWS[kind]; }
  function ruleItems(R){ const f=S.f.guess,rank={low:0,med:1,high:2};
    return R.items.filter(ii=>!f.lv.size||f.lv.has(ITEMS[ii].e.l)).sort((a,b)=>rank[ITEMS[a].it.conf]-rank[ITEMS[b].it.conf]||(ITEMS[b].it.cm||0)-(ITEMS[a].it.cm||0)); }
  function ruleEls(R){ const f=S.f.guess; return R.idx().filter(i=>!f.lv.size||f.lv.has(els[i].l)).sort((a,b)=>LVL[els[a].l].idx-LVL[els[b].l].idx||(els[a].id<els[b].id?-1:1)); }
  function guessUnits(){ let t=0,d=0; getRows('guess').forEach(R=>{ if(R.hasItems){ ruleItems(R).forEach(ii=>{t++; if(GDONE[itemStatus(ii)]) d++;}); } else { t++; if(GDONE[ruleStatus(R.r.id)]) d++; } }); return {t,d}; }
  function levelCounts(){
    const out={}; M.levels.forEach(l=>{out[l.id]=0;});
    if(S.kind==='clash'){ for(let ci=0;ci<clashes.length;ci++) if(matchClash(ci,{lv:1})) out[clashes[ci].l]++; }
    else RULES.forEach(R=>{ if(!matchRule(R,{lv:1})) return; for(const l in R.lv) if(R.lv[l]>0&&out[l]!==undefined) out[l]++; });
    return out; }

  /* ---------------- HTML: head, cards, lists ---------------- */
  const pill=(t,cls,style)=>'<span class="is-pill'+(cls?' '+cls:'')+'"'+(style?' style="'+style+'"':'')+'>'+t+'</span>';
  const stPillClash=st=>st==='open'?'':pill(esc(shortSt(CLS[st]||st)),'st','background:'+(CST[st]||'#8b949e'));
  const stPillGuess=st=>st==='open'?'':pill(esc(GST[st]||st),'st','background:'+(GSTC[st]||'#8b949e'));
  const opts=(list,cur)=>list.map(o=>'<option value="'+esc(o[0])+'"'+(String(o[0])===String(cur)?' selected':'')+'>'+esc(o[1])+'</option>').join('');
  function tabsHTML(){ $('isTabs').innerHTML=['clash','guess'].map(k=>'<button type="button" role="tab" class="is-tab'+(S.kind===k?' on':'')+'" data-tab="'+k+'" aria-selected="'+(S.kind===k)+'">'+(k==='clash'?'التعارضات':'التخمينات')+' <b>'+(k==='clash'?clashes.length:RULES.length)+'</b></button>').join(''); }
  function viewsHTML(){ $('isViews').innerHTML=[['list','الأولويات'],['map','الخريطة'],['mx','المصفوفة']].map(v=>'<button type="button" role="tab" class="is-vw'+(S.view===v[0]?' on':'')+'" data-view="'+v[0]+'" aria-selected="'+(S.view===v[0])+'">'+v[1]+'</button>').join(''); }
  function toolsHTML(){ $('isTools').innerHTML='<button type="button" class="mini'+(S.lens?' on':'')+'" data-act="lens" aria-pressed="'+S.lens+'" title="يلوّن المبنى بنتيجة المرشحات الحالية">'+(S.lens?'إلغاء التلوين':'لوّن المجسم')+'</button><button type="button" class="mini'+(S.pins?' on':'')+'" data-act="pins" aria-pressed="'+S.pins+'" title="إظهار أو إخفاء الدبابيس في المجسم">الدبابيس'+(S.pins?' ✓':'')+'</button><button type="button" class="mini'+(S.ap?' on':'')+'" data-act="ap" aria-pressed="'+(!!S.ap)+'" title="جولة تلقائية على أهم النتائج؛ أي حركة للكاميرا توقفها">'+(S.ap?'■ إيقاف':'▶ تلقائي')+'</button><button type="button" class="mini" data-act="csv" title="تصدير القائمة المعروضة بمرشحاتها الحالية">⬇ CSV</button>'; }
  function advCount(){ const f=S.f[S.kind]; return S.kind==='clash'?(f.sys?1:0)+(f.obs?1:0)+(f.st?1:0)+(f.sort!=='prio'?1:0):(f.kind?1:0)+(f.layer?1:0)+(f.st?1:0)+(f.sort!=='prio'?1:0); }
  function updateAdv(){ const n=advCount(),b=$('isAdvN'); if(b){ b.textContent=n||''; b.style.display=n?'':'none'; } const bt=$('isAdvB'); if(bt) bt.setAttribute('aria-expanded',String(S.adv)); }
  function buildHead(){
    const k=S.kind,f=S.f[k]; let h='<p class="is-lead">'+esc(TIPS[k])+' <button type="button" class="is-howb" data-act="how" aria-expanded="'+S.how+'">'+(k==='clash'?'كيف صُنّفت؟':'كيف تُقرأ فئات النقل؟')+'</button></p><div class="is-how" id="isHow"'+(S.how?'':' hidden')+'>'+esc(k==='clash'?(M.clashNote||''):TIPS.conf)+'</div>';
    h+='<div class="is-tiles" role="group" aria-label="'+(k==='clash'?'الدرجة':'الأثر')+'">';
    if(k==='clash') ['c','k','m'].forEach(t=>{const T=PAL.TIER[t]; h+='<button type="button" class="is-tile'+(f.tiers[t]?' on':'')+'" data-tier="'+t+'" aria-pressed="'+(!!f.tiers[t])+'" style="--tc:'+T.c+';--tcb:'+T.c+'1a" title="'+esc(TTITLE[t])+'"><span class="is-ic">'+T.i+'</span><b>'+TOT[t]+'</b><span class="l">'+TLAB[t]+'</span></button>';});
    else ['high','med','low'].forEach(t=>{const T=IMPACT[t]; h+='<button type="button" class="is-tile'+(f.imps[t]?' on':'')+'" data-imp="'+t+'" aria-pressed="'+(!!f.imps[t])+'" style="--tc:'+T.c+';--tcb:'+T.c+'1a" title="'+esc(T.n)+'"><span class="is-ic">'+T.i+'</span><b>'+IMPT[t]+'</b><span class="l">'+T.n+'</span></button>';});
    h+='</div><div class="is-prog" id="isProg"></div><div class="is-lv" id="isLv" role="group" aria-label="الطابق"></div>';
    h+='<div class="is-find"><input class="is-q" type="search" data-f="q" value="'+esc(f.q)+'" placeholder="بحث: رمز، وسم، نظام…" autocomplete="off" aria-label="بحث"><button type="button" class="mini" data-act="adv" id="isAdvB" aria-expanded="'+S.adv+'" title="النظام، العائق، الحالة، الترتيب">تصفية متقدمة <b class="is-badge" id="isAdvN"></b></button></div><div class="is-sel" id="isAdv"'+(S.adv?'':' hidden')+'>';
    if(k==='clash'){
      const cnt={}; clashes.forEach(c=>{cnt[c.sys]=(cnt[c.sys]||0)+1;}); const systems=Object.keys(cnt).sort((a,b)=>cnt[b]-cnt[a]||(a<b?-1:1));
      h+='<label>النظام<select data-f="sys">'+opts([['','الكل']].concat(systems.map(s=>[s,s])),f.sys)+'</select></label>';
      h+='<label>العائق<select data-f="obs">'+opts([['','الكل']].concat(OBSC),f.obs)+'</select></label>';
      h+='<label>متابعة المستخدم<select data-f="st">'+opts([['','الكل'],['*open','دون تأشير معالجة حالي']].concat(Object.keys(CLS).map(s=>[s,CLS[s]])),f.st)+'</select></label>';
      h+='<label>الترتيب<select data-f="sort">'+opts([['prio','الأولوية'],['vol','الأكبر حجمًا'],['n','الأكثر مواضع'],['lvl','حسب الطابق']],f.sort)+'</select></label>';
    } else {
      const kinds=Object.keys(GU.kinds||{}).filter(x=>RULES.some(R=>R.r.kind===x));
      h+='<label>النوع<select data-f="kind">'+opts([['','الكل']].concat(kinds.map(x=>[x,GU.kinds[x]])),f.kind)+'</select></label>';
      h+='<label>التخصص<select data-f="layer">'+opts([['','الكل']].concat(LAYS),f.layer)+'</select></label>';
      h+='<label>متابعة المستخدم<select data-f="st">'+opts([['','الكل'],['*open','دون تأشير مطابقة حالي']].concat(Object.keys(GST).map(s=>[s,GST[s]])),f.st)+'</select></label>';
      h+='<label>الترتيب<select data-f="sort">'+opts([['prio','الأثر ثم العدد'],['n','الأكثر عناصر'],['kind','حسب النوع']],f.sort)+'</select></label>';
    }
    h+='</div>';
    $('isHead').innerHTML=h; updateAdv(); }
  function updateLevels(){ const c=levelCounts(),f=S.f[S.kind]; let h='<button type="button" class="chip'+(f.lv.size?'':' on')+'" data-lv="*">كل الطوابق</button>';
    M.levels.forEach(l=>{const n=c[l.id]||0; h+='<button type="button" class="chip'+(f.lv.has(l.id)?' on':'')+(n?'':' zero')+'" data-lv="'+l.id+'">'+esc(l.name)+' <b>'+n+'</b></button>';}); $('isLv').innerHTML=h; }
  function updateProg(){ const el=$('isProg'); let t=0,d=0;
    if(S.kind==='clash'){ for(let ci=0;ci<clashes.length;ci++) if(matchClash(ci)){t++; if(CDONE[clashStatus(clashes[ci])]) d++;} } else { const u=guessUnits(); t=u.t; d=u.d; }
    if(!t){el.style.display='none'; el.innerHTML=''; return;} el.style.display=''; const p=Math.round(d*100/t);
    el.innerHTML='<span>تأشير المستخدم الحالي '+d+' من '+t+' ('+p+'%) — متابعة محلية فقط</span><span class="bar"><span style="width:'+p+'%"></span></span>'; }
  function updateSum(){ const rows=getRows(); let txt;
    if(S.kind==='clash'){ const n=rows.reduce((a,g)=>a+g.idx.length,0); txt=P_GRP(rows.length)+' ('+P_POS(n)+') من '+((M.clashGroups||[]).length||rows.length); }
    else { const d=rows.reduce((a,R)=>a+(R.hasItems?ruleItems(R).length:0),0); txt=P_RULE(rows.length)+' من '+RULES.length+' · القرارات الفردية: '+d; }
    $('isSum').innerHTML='<span>'+txt+'</span>'+(isDefault(S.kind)?'':'<button type="button" class="mini" data-act="reset">إعادة ضبط المرشحات</button>'); }

  const skC=new Map();
  function sketchFor(ci){ let s=skC.get(ci); if(s===undefined){ const p=sketchInputs(M,clashes[ci]); s=p?sketchSVG(p):''; skC.set(ci,s);} return s; }
  function noteBox(c){ if(tierOf(c)==='m'||/^P\.tank/.test(String(c.sid||''))) return esc(c.why); return ''; }
  function visHTML(c,ci){ const s=sketchFor(ci); if(s) return '<div class="is-vis">'+s+'</div>'; const n=noteBox(c); return n?'<div class="is-vis"><div class="is-none">'+n+'</div></div>':''; }
  function locsClashHTML(g){
    const lim=S.pageLoc[g.gk]||PAGE_LOC;
    let h='<div class="is-bulk"><select data-bulk="'+esc(g.gk)+'"><option value="">تعيين حالة كل المواضع…</option>'+CLKEYS.map(s=>'<option value="'+esc(s)+'">'+esc(CLS[s])+'</option>').join('')+'</select></div><ol class="is-locs">';
    g.idx.slice(0,lim).forEach((ci,k)=>{ const c=clashes[ci],t=tierOf(c),st=clashStatus(c),hh=c.pt[1]-LVL[c.l].ffl,sel=S.sel&&S.sel.kind==='clash'&&S.sel.id===ci;
      h+='<li class="is-loc'+(sel?' sel':'')+'" data-ci="'+ci+'"><button type="button" class="is-lb" data-act="loc"><span class="is-ic" style="--tc:'+PAL.TIER[t].c+'">'+PAL.TIER[t].i+'</span><span class="t">الموضع '+(k+1)+' — <code>'+esc(c.id)+'</code></span>'+(st==='open'?'<span></span>':stPillClash(st))+'<small>ارتفاع '+NUM(hh.toFixed(2))+' م فوق الأرضية · حجم '+NUM(c.v)+' م³</small></button></li>'; });
    h+='</ol>'; if(g.idx.length>lim) h+='<button type="button" class="chip is-more" data-act="more" data-more="locs" data-id="'+esc(g.gk)+'">عرض المزيد ('+(g.idx.length-lim)+')</button>'; return h; }
  function clashCardHTML(g){
    const w=clashes[g.idx[0]],t=g.tier,T=PAL.TIER[t],n=g.idx.length; let done=0,any=false;
    g.idx.forEach(ci=>{const st=clashStatus(clashes[ci]); if(st!=='open') any=true; if(CDONE[st]) done++;});
    const open=S.open.has(g.gk),sel=S.sel&&((S.sel.kind==='group'&&S.sel.id===g.gk)||(S.sel.kind==='clash'&&clashes[S.sel.id].gk===g.gk));
    let h='<article class="is-card'+(sel?' sel':'')+(done===n?' done':'')+'" data-gid="'+esc(g.gk)+'" style="--tc:'+T.c+'"><header class="is-ch"><span class="is-ic">'+T.i+'</span><h4>'+esc(g.meta.svc)+' × '+esc(g.meta.obs)+'</h4></header>';
    h+='<div class="is-meta">'+pill(esc(lvName(g.meta.l)))+pill(esc(g.meta.sys))+pill(P_POS(n))+pill('≈ '+(g.vol<0.01?'< 0.01':g.vol.toFixed(2))+' م³')+(any?pill(done+' من '+n+' بتأشير متابعة حالي','st','background:'+(done===n?'#1a7f37':'#bf8700')):'')+'</div>';
    h+=visHTML(w,g.idx[0]);
    h+='<dl class="is-wf"><dt>السبب</dt><dd>'+esc(w.why)+'</dd><dt>الحل المقترح</dt><dd>'+esc(w.fix)+'</dd></dl>';
    h+='<div class="is-act"><button type="button" class="mini pri" data-act="view">عرض</button><button type="button" class="mini" data-act="locs" aria-expanded="'+open+'">المواضع '+(open?'▴':'▾')+'</button></div>';
    if(open) h+=locsClashHTML(g);
    return h+'</article>'; }
  function lvStrip(R){ const mx=Math.max(1,...M.levels.map(l=>R.lv[l.id]||0));
    return '<div class="is-lvs" role="img" aria-label="توزيع العناصر على الطوابق">'+M.levels.map(l=>{const n=R.lv[l.id]||0; return '<span class="'+(n?'':'z')+'" title="'+esc(l.name)+': '+n+'"><em style="height:'+(n?Math.max(6,Math.round(n/mx*100)):0)+'%"></em><b>'+lvAb(l.id)+'</b></span>';}).join('')+'</div>'; }
  function locsRuleHTML(R){
    const lim=S.pageLoc[R.r.id]||PAGE_LOC; let h='<ol class="is-locs">',total=0;
    if(R.hasItems){ const list=ruleItems(R); total=list.length;
      list.slice(0,lim).forEach(ii=>{ const I=ITEMS[ii],it=I.it,cf=PAL.CONF[it.conf]||PAL.CONF.low,st=itemStatus(ii),sel=S.sel&&S.sel.kind==='guess'&&S.sel.id===ii;
        const what=it.r==='G-SNAP'?'سُحب '+Math.round(it.cm)+' سم إلى وجه الجدار':'نُقل '+Math.round(it.cm)+' سم ← '+(MOUNT[it.k]||'');
        h+='<li class="is-loc'+(sel?' sel':'')+'" data-ii="'+ii+'"><button type="button" class="is-lb" data-act="loc"><span class="is-ic" style="--tc:'+cf.c+'">'+(CONFI[it.conf]||'●')+'</span><span class="t">'+esc(elName(I.ei))+'</span>'+pill(CONFN[it.conf]||'','st','background:'+cf.c+';color:#0b2a3d')+'<small>'+esc(lvName(I.e.l))+' · '+esc(what)+(st==='open'?'':' · '+esc(GST[st]||st))+'</small></button></li>'; }); }
    else { const list=ruleEls(R); total=list.length; list.slice(0,lim).forEach(ei=>{ h+='<li class="is-loc" data-ei="'+ei+'"><button type="button" class="is-lb" data-act="loc"><span class="is-ic">·</span><span class="t">'+esc(elName(ei))+'</span><span></span><small>'+esc(lvName(els[ei].l))+'</small></button></li>'; }); }
    h+='</ol>'; if(total>lim) h+='<button type="button" class="chip is-more" data-act="more" data-more="locs" data-id="'+esc(R.r.id)+'">عرض المزيد ('+(total-lim)+')</button>'; return h; }
  function ruleCardHTML(R){
    const r=R.r,T=IMPACT[r.impact],open=S.open.has(r.id),sel=S.sel&&((S.sel.kind==='rule'&&S.sel.id===r.id)||(S.sel.kind==='guess'&&ITEMS[S.sel.id].it.r===r.id));
    let stp='',doneAll=false;
    if(R.hasItems){ let d=0; R.items.forEach(ii=>{if(GDONE[itemStatus(ii)]) d++;});const hist=R.items.filter(ii=>itemStatus(ii)==='historical').length;stp=d?pill('أشر المستخدم مطابقة '+d+' من '+R.items.length+' قرارًا','st','background:#1a7f37'):hist?pill('تأشير تاريخي: '+hist+' قرارًا','st','background:#8b949e'):''; doneAll=d===R.items.length; }
    else { const st=ruleStatus(r.id); stp=stPillGuess(st); doneAll=!!GDONE[st]; }
    let h='<article class="is-card is-gc'+(sel?' sel':'')+(doneAll?' done':'')+'" data-rid="'+esc(r.id)+'" style="--tc:'+T.c+'"><header class="is-ch"><span class="is-ic">'+T.i+'</span><h4>'+esc(r.title)+'</h4></header>';
    h+='<div class="is-meta">'+pill(esc((GU.kinds||{})[r.kind]||r.kind))+pill(T.n)+pill(P_EL(r.n))+(R.hasItems?pill('قرارات فردية'):'')+stp+'</div><div class="is-vis">'+lvStrip(R)+'</div>';
    h+='<dl class="is-wf"><dt>لماذا خُمّن</dt><dd>'+esc(r.why)+'</dd>'+(r.how?'<dt>كيف اختير</dt><dd>'+esc(r.how)+'</dd>':'')+'<dt>الأساس</dt><dd>'+esc(r.basis)+'</dd><dt>ما يحسمه</dt><dd>'+esc(r.verify)+'</dd></dl>';
    const canList=R.hasItems||(r.els&&r.els.length<=EL_LIST_MAX);
    h+='<div class="is-act"><button type="button" class="mini pri" data-act="hl">أبرِز في المجسم</button><button type="button" class="mini" data-act="det">التفاصيل</button>'+(canList?'<button type="button" class="mini" data-act="locs" aria-expanded="'+open+'">'+(R.hasItems?'القرارات':'العناصر')+' '+(open?'▴':'▾')+'</button>':'')+'</div>';
    if(open&&canList) h+=locsRuleHTML(R);
    return h+'</article>'; }
  const emptyHTML=()=>'<div class="is-empty">لا نتائج بهذه المرشحات.<br><button type="button" class="mini" data-act="reset">إعادة ضبط المرشحات</button></div>';
  function clashListHTML(){
    const rows=getRows('clash'); if(!rows.length) return emptyHTML(); const lim=S.page.clash,cnt={c:0,k:0,m:0}; rows.forEach(g=>{cnt[g.tier]++;});
    let h='',last=''; rows.slice(0,lim).forEach(g=>{ if(S.f.clash.sort==='prio'&&g.tier!==last){ h+='<h5 class="is-sh">'+THEAD[g.tier]+' ('+cnt[g.tier]+')</h5>'; last=g.tier; } h+=clashCardHTML(g); });
    if(rows.length>lim) h+='<button type="button" class="chip is-more" data-act="more" data-more="cards">عرض المزيد ('+(rows.length-lim)+')</button>'; return h; }
  function guessListHTML(){
    const rows=getRows('guess'); if(!rows.length) return emptyHTML(); const lim=S.page.guess,n1=rows.filter(R=>R.hasItems).length,n2=rows.length-n1;
    let h='',last=null; rows.slice(0,lim).forEach(R=>{ if(S.f.guess.sort==='prio'&&R.hasItems!==last){ h+='<h5 class="is-sh">'+(R.hasItems?'قرارات فردية ('+n1+')':'افتراضات عامة ('+n2+')')+'</h5>'; last=R.hasItems; } h+=ruleCardHTML(R); });
    if(rows.length>lim) h+='<button type="button" class="chip is-more" data-act="more" data-more="cards">عرض المزيد ('+(rows.length-lim)+')</button>'; return h; }

  /* ---------------- HTML: matrix ---------------- */
  const hex2=a=>Math.max(0,Math.min(255,Math.round(a*255))).toString(16).padStart(2,'0');
  function mcell(n,mx,segs,attrs,label){
    if(!n) return '<td><button type="button" class="is-cell zero" tabindex="-1" aria-label="'+esc(label)+': 0"><b>·</b></button></td>';
    const worst=(segs.find(s=>s[0]>0)||[0,'#7B8794'])[1];
    return '<td><button type="button" class="is-cell" '+attrs+' aria-label="'+esc(label)+': '+n+'" style="background:'+worst+hex2(0.12+0.6*n/mx)+'"><b>'+n+'</b><span class="bar">'+segs.map(s=>s[0]?'<span style="width:'+(s[0]/n*100)+'%;background:'+s[1]+'"></span>':'').join('')+'</span></button></td>'; }
  function matrixHTML(){
    const note='<div class="muted">اضغط خلية لتصفية القائمة بها.</div>';
    if(S.kind==='clash'){
      const cnt={},tot={}; let mx=1;
      for(let ci=0;ci<clashes.length;ci++){ if(!matchClash(ci,{sys:1,obs:1})) continue; const c=clashes[ci],key=c.sys+'|'+obsOf(c); const o=cnt[key]||(cnt[key]={c:0,k:0,m:0}); o[tierOf(c)]++; tot[c.sys]=(tot[c.sys]||0)+1; }
      Object.keys(cnt).forEach(k=>{const o=cnt[k]; mx=Math.max(mx,o.c+o.k+o.m);});
      const systems=[]; clashes.forEach(c=>{if(systems.indexOf(c.sys)<0) systems.push(c.sys);}); systems.sort((a,b)=>(tot[b]||0)-(tot[a]||0)||(a<b?-1:1));
      let h='<table class="is-mx"><caption>النظام × العائق</caption><thead><tr><th></th>'+OBSC.map(o=>'<th scope="col">'+o[1]+'</th>').join('')+'</tr></thead><tbody>';
      systems.forEach(s=>{ h+='<tr><th scope="row">'+esc(s)+'</th>'+OBSC.map(o=>{const v=cnt[s+'|'+o[0]]||{c:0,k:0,m:0}; return mcell(v.c+v.k+v.m,mx,[[v.c,PAL.TIER.c.c],[v.k,PAL.TIER.k.c],[v.m,PAL.TIER.m.c]],'data-sys="'+esc(s)+'" data-obs="'+o[0]+'"',s+' × '+o[1]);}).join('')+'</tr>'; });
      h+='</tbody></table>'+note;
      const c2={}; let m2=1; for(let ci=0;ci<clashes.length;ci++){ if(!matchClash(ci,{tier:1,lv:1})) continue; const c=clashes[ci],k=c.l+'|'+tierOf(c); c2[k]=(c2[k]||0)+1; m2=Math.max(m2,c2[k]); }
      const lvs=M.levels.filter(l=>clashes.some(c=>c.l===l.id));
      h+='<table class="is-mx"><caption>الطابق × الدرجة</caption><thead><tr><th></th>'+['c','k','m'].map(t=>'<th scope="col"><span class="is-ic" style="--tc:'+PAL.TIER[t].c+'">'+PAL.TIER[t].i+'</span> '+TLAB[t]+'</th>').join('')+'</tr></thead><tbody>';
      lvs.forEach(l=>{ h+='<tr><th scope="row">'+esc(l.name)+'</th>'+['c','k','m'].map(t=>mcell(c2[l.id+'|'+t]||0,m2,[[c2[l.id+'|'+t]||0,PAL.TIER[t].c]],'data-lvl="'+l.id+'" data-tier="'+t+'"',l.name+' × '+TLAB[t])).join('')+'</tr>'; });
      return h+'</tbody></table>'+note; }
    const kinds=Object.keys(GU.kinds||{}).filter(x=>RULES.some(R=>R.r.kind===x)),cnt={}; let mx=1;
    RULES.forEach(R=>{ if(!matchRule(R,{kind:1,layer:1})||!R.layer) return; const key=R.r.kind+'|'+R.layer; const o=cnt[key]||(cnt[key]={high:0,med:0,low:0}); o[R.r.impact]++; });
    Object.keys(cnt).forEach(k=>{const o=cnt[k]; mx=Math.max(mx,o.high+o.med+o.low);});
    let h='<table class="is-mx"><caption>نوع الافتراض × التخصص</caption><thead><tr><th></th>'+LAYS.map(l=>'<th scope="col">'+l[1]+'</th>').join('')+'</tr></thead><tbody>';
    kinds.forEach(kd=>{ h+='<tr><th scope="row">'+esc(GU.kinds[kd])+'</th>'+LAYS.map(l=>{const v=cnt[kd+'|'+l[0]]||{high:0,med:0,low:0}; return mcell(v.high+v.med+v.low,mx,[[v.high,IMPACT.high.c],[v.med,IMPACT.med.c],[v.low,IMPACT.low.c]],'data-kind="'+kd+'" data-layer="'+l[0]+'"',GU.kinds[kd]+' × '+l[1]);}).join('')+'</tr>'; });
    return h+'</tbody></table>'+note; }

  /* ---------------- map (2-D plan with pins and before→after arrows) ---------------- */
  let suspended=false;   // guided tours hide the pins
  let pm=null,mapCv=null,mapRO=null,lastCam=null,mapData=null; const _dv=new THREE.Vector3();
  const selKey=()=>S.sel&&S.sel.kind==='clash'?'c:'+S.sel.id:S.sel&&S.sel.kind==='guess'?'g:'+S.sel.id:null;
  function mapPins(){
    const pins=[],arrows=[];
    if(S.kind==='clash'){ for(let ci=0;ci<clashes.length;ci++){ if(!matchClash(ci)) continue; const c=clashes[ci],t=tierOf(c);
        pins.push({x:c.pt[0]*100,y:-c.pt[2]*100,l:c.l,c:PAL.TIER[t].c,s:{c:'s',k:'d',m:'o'}[t],k:'c:'+ci,r:6,dim:!!CDONE[clashStatus(c)],ref:{kind:'clash',id:ci}}); } }
    else getRows('guess').forEach(R=>ruleItems(R).forEach(ii=>{ const I=ITEMS[ii],it=I.it,a=after(ii);
      pins.push({x:a.xcm,y:a.ycm,l:I.e.l,c:(PAL.CONF[it.conf]||PAL.CONF.low).c,s:{high:'o',med:'d',low:'t'}[it.conf]||'o',k:'g:'+ii,r:5,dim:!!GDONE[itemStatus(ii)],ref:{kind:'guess',id:ii}});
      if(it.from&&it.cm>=1) arrows.push({x0:it.from[0],y0:it.from[1],x1:a.xcm,y1:a.ycm,c:'#0072B2',l:I.e.l}); }));
    return {pins,arrows}; }
  function mapApply(){ if(!pm||!mapData||!mapCv||mapCv.clientWidth<10) return; pm.setLevel(S.mapLevel); pm.setPins(mapData.pins); pm.setArrows(mapData.arrows.filter(a=>a.l===S.mapLevel)); pm.setSel(selKey()); updateCam(true); }
  function renderMap(){
    const p=$('isPane'); if(!PlanMap){ p.innerHTML='<div class="is-empty">الخريطة غير متاحة (وحدة المسقط غير محمّلة).</div>'; return; }
    mapData=mapPins(); const byL={}; mapData.pins.forEach(x=>{byL[x.l]=(byL[x.l]||0)+1;});
    const lvs=M.levels.filter(l=>byL[l.id]),f=S.f[S.kind];
    if(!lvs.length){ p.innerHTML=S.kind==='guess'?'<div class="is-empty">لا قرارات فردية ضمن المرشحات الحالية.<br><button type="button" class="mini" data-act="reset">إعادة ضبط المرشحات</button></div>':emptyHTML(); return; }
    if(!S.mapLevel||!byL[S.mapLevel]) S.mapLevel=(f.lv.size===1&&byL[[...f.lv][0]])?[...f.lv][0]:lvs.slice().sort((a,b)=>byL[b.id]-byL[a.id])[0].id;
    const leg=S.kind==='clash'?['c','k','m'].map(t=>'<span><span class="is-ic" style="--tc:'+PAL.TIER[t].c+'">'+PAL.TIER[t].i+'</span>'+TLAB[t]+'</span>').join(''):['high','med','low'].map(t=>'<span><span class="is-ic" style="--tc:'+PAL.CONF[t].c+'">'+CONFI[t]+'</span>'+CONFN[t]+'</span>').join('')+'<span><span class="is-ic" style="--tc:#0072B2">→</span>موضع سابق ← موضع التخمين</span>';
    const hint='اضغط دبوسًا لفتح تفاصيله · اضغط أرضًا فارغة لنقل الكاميرا إلى هناك · قرص أو عجلة للتقريب · نقرتان لإعادة الضبط'+(S.kind==='guess'?'<br>الخريطة تعرض القرارات الفردية فقط (الأجهزة المنقولة والمسحوبة)؛ الافتراضات العامة تخص أنواعًا لا مواضع.':'');
    p.innerHTML='<div class="is-mapbox"><div class="is-maplv" role="group" aria-label="طابق الخريطة">'+lvs.map(l=>'<button type="button" class="chip'+(l.id===S.mapLevel?' on':'')+'" data-ml="'+l.id+'">'+esc(l.name)+' <b>'+byL[l.id]+'</b></button>').join('')+'</div><div id="isMapSlot"></div><div class="is-leg">'+leg+'</div><div class="muted">'+hint+'</div></div>';
    if(!mapCv){ mapCv=document.createElement('canvas'); mapCv.id='isMap'; mapCv.className='is-mapcv'; pm=new PlanMap(mapCv,{M,LVL});
      pm.onPick=pin=>{ if(pin.ref) focus(pin.ref.kind,pin.ref.id); }; pm.onGround=(x,y,l)=>flyToPlan(x,y,l);
      if(window.ResizeObserver){ mapRO=new ResizeObserver(()=>{ if(pm&&mapCv.isConnected&&mapCv.clientWidth>10){ if(pm.L) pm.resize(); else mapApply(); } }); mapRO.observe(mapCv); } }
    $('isMapSlot').appendChild(mapCv); pm.resize(); mapApply(); }
  function updateCam(force){
    if(!pm||!mapCv||!mapCv.isConnected||!pm.L) return; camera.getWorldDirection(_dv);
    const x=camera.position.x*100,y=-camera.position.z*100,yaw=Math.atan2(_dv.z,_dv.x);
    if(!force&&lastCam&&Math.abs(x-lastCam.x)<1&&Math.abs(y-lastCam.y)<1&&Math.abs(yaw-lastCam.yaw)<0.01) return; lastCam={x,y,yaw}; pm.setCamera({x,y,yaw}); }
  function flyToPlan(x,y,l){ const t=new THREE.Vector3(x/100,LVL[l].ffl+1.3,-y/100),p=t.clone().add(new THREE.Vector3(-0.5,0.55,0.7).normalize().multiplyScalar(9)); flyTo(p,t,900); wake(1200); }
  function mapSync(){ if(S.view!=='map'||!pm) return; const s=S.sel; const L=s&&s.kind==='clash'?clashes[s.id].l:s&&s.kind==='guess'?ITEMS[s.id].e.l:null;
    if(L&&L!==S.mapLevel){ S.mapLevel=L; renderMap(); } else pm.setSel(selKey()); }

  /* ---------------- 3-D pins, selected ring, before→after marker ---------------- */
  const pinG=new THREE.Group(); pinG.visible=false; scene.add(pinG);
  const texC={};
  function pinTex(shape){
    if(texC[shape]) return texC[shape]; const cv=document.createElement('canvas'); cv.width=cv.height=64; const g=cv.getContext('2d'); g.lineJoin='round'; g.beginPath();
    if(shape==='sq') g.rect(13,13,38,38); else if(shape==='di'){g.moveTo(32,6);g.lineTo(58,32);g.lineTo(32,58);g.lineTo(6,32);g.closePath();} else if(shape==='tr'){g.moveTo(32,8);g.lineTo(58,54);g.lineTo(6,54);g.closePath();} else g.arc(32,32,23,0,Math.PI*2);
    if(shape==='ring'){ g.lineWidth=9; g.strokeStyle='#ffffff'; g.stroke(); g.lineWidth=3.2; g.strokeStyle='#1c2430'; g.stroke(); }
    else { g.fillStyle='#ffffff'; g.fill(); g.lineWidth=5; g.strokeStyle='#1c2430'; g.stroke(); }
    return (texC[shape]=new THREE.CanvasTexture(cv)); }
  let pinRefs=[],pinObjs=[],selPts=null,lvSig='';
  function pinData(){
    const out=[]; if(!built) return out;
    if(S.kind==='clash'){ for(let ci=0;ci<clashes.length;ci++){ if(!matchClash(ci)) continue; const c=clashes[ci]; if(!levelVisible(c.l)) continue; const t=tierOf(c);
        out.push({x:c.pt[0],y:c.pt[1],z:c.pt[2],cls:t,shape:{c:'sq',k:'di',m:'ci'}[t],color:PAL.TIER[t].c,ref:{kind:'clash',id:ci}}); } }
    else getRows('guess').forEach(R=>ruleItems(R).forEach(ii=>{ const I=ITEMS[ii]; if(!levelVisible(I.e.l)) return; const a=after(ii),cf=PAL.CONF[I.it.conf]||PAL.CONF.low;
      out.push({x:a.c[0],y:a.c[1],z:a.c[2],cls:I.it.conf,shape:{high:'ci',med:'di',low:'tr'}[I.it.conf]||'ci',color:cf.c,ref:{kind:'guess',id:ii}}); }));
    return out; }
  function pinClear(){ pinObjs.forEach(o=>{pinG.remove(o); o.geometry.dispose(); o.material.dispose();}); pinObjs=[]; pinRefs=[]; }
  function rebuildPins(){
    pinClear(); lvSig=M.levels.map(l=>levelVisible(l.id)?1:0).join(''); const by={}; pinData().forEach(d=>{(by[d.cls]=by[d.cls]||[]).push(d);});
    Object.keys(by).forEach(k=>{ const arr=by[k],pos=new Float32Array(arr.length*3); arr.forEach((d,i)=>{pos[i*3]=d.x; pos[i*3+1]=d.y; pos[i*3+2]=d.z;});
      const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.BufferAttribute(pos,3));
      const m=new THREE.PointsMaterial({map:pinTex(arr[0].shape),color:new THREE.Color(arr[0].color),size:17,sizeAttenuation:false,transparent:true,opacity:0.95,depthTest:false,depthWrite:false,alphaTest:0.05});
      const p=new THREE.Points(g,m); p.renderOrder=1004; p.frustumCulled=false; pinG.add(p); pinObjs.push(p); arr.forEach(d=>pinRefs.push(d)); });
    updateSelPin(); wake(); }
  function updateSelPin(){
    let pos=null,color='#1f6feb';
    if(S.sel&&S.sel.kind==='clash'){ const c=clashes[S.sel.id]; pos=c.pt; color=PAL.TIER[tierOf(c)].c; }
    else if(S.sel&&S.sel.kind==='guess'){ const a=after(S.sel.id); pos=a.c; color=(PAL.CONF[ITEMS[S.sel.id].it.conf]||PAL.CONF.low).c; }
    if(!pos){ if(selPts) selPts.visible=false; return; }
    if(!selPts){ const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.BufferAttribute(new Float32Array(3),3));
      selPts=new THREE.Points(g,new THREE.PointsMaterial({map:pinTex('ring'),size:34,sizeAttenuation:false,transparent:true,depthTest:false,depthWrite:false,alphaTest:0.05})); selPts.renderOrder=1005; selPts.frustumCulled=false; scene.add(selPts); }
    const a=selPts.geometry.attributes.position; a.array[0]=pos[0]; a.array[1]=pos[1]; a.array[2]=pos[2]; a.needsUpdate=true; selPts.material.color.set(color); selPts.visible=true; wake(300); }
  let fx=null;
  function fxClear(){ if(!fx) return; scene.remove(fx); fx.traverse(o=>{ if(o.geometry) o.geometry.dispose(); if(o.material) o.material.dispose(); }); fx=null; wake(); }
  function fxShow(it,a){
    fxClear(); if(!it.from) return; const half=(a.mx[1]-a.mn[1])/2,bx=it.from[0]/100,by=it.from[2]+half,bz=-it.from[1]/100; const g=new THREE.Group();
    const pg=new THREE.BufferGeometry(); pg.setAttribute('position',new THREE.BufferAttribute(new Float32Array([bx,by,bz]),3));
    const pts=new THREE.Points(pg,new THREE.PointsMaterial({map:pinTex('ring'),color:new THREE.Color('#7B8794'),size:24,sizeAttenuation:false,transparent:true,depthTest:false,depthWrite:false,alphaTest:0.05})); pts.renderOrder=1003; pts.frustumCulled=false; g.add(pts);
    const lg=new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(bx,by,bz),new THREE.Vector3(a.c[0],a.c[1],a.c[2])]);
    const ln=new THREE.Line(lg,new THREE.LineDashedMaterial({color:0x0072B2,dashSize:0.12,gapSize:0.08,depthTest:false,transparent:true})); ln.computeLineDistances(); ln.renderOrder=1002; ln.frustumCulled=false; g.add(ln);
    scene.add(g); fx=g; wake(1500); }
  const sectionOpen=()=>sec.classList.contains('on');
  function tap(cx,cy){
    if(!pinG.visible||!pinRefs.length) return false; const r=renderer.domElement.getBoundingClientRect(),lim=matchMedia('(pointer:coarse)').matches?24:14; let best=null,bd=1e9; const v=new THREE.Vector3();
    for(const p of pinRefs){ v.set(p.x,p.y,p.z).project(camera); if(v.z>1||v.z<-1) continue; const sx=r.left+(v.x+1)/2*r.width,sy=r.top+(1-v.y)/2*r.height,d=Math.hypot(sx-cx,sy-cy); if(d<lim&&d<bd){bd=d; best=p;} }
    if(!best) return false; focus(best.ref.kind,best.ref.id); return true; }
  function pinAt(i){ const p=pinRefs[i]; if(!p) return null; const r=renderer.domElement.getBoundingClientRect(),v=new THREE.Vector3(p.x,p.y,p.z).project(camera); return {kind:p.ref.kind,id:p.ref.id,x:r.left+(v.x+1)/2*r.width,y:r.top+(1-v.y)/2*r.height,visible:v.z>-1&&v.z<1}; }

  /* ---------------- lens button: colour the model by the current list ---------------- */
  function lensData(){
    if(S.kind==='clash'){ const ts=['c','k','m'].filter(t=>S.f.clash.tiers[t]),idx={},map=new Map(); ts.forEach((t,i)=>{idx[t]=i+1;});
      for(let ci=0;ci<clashes.length;ci++){ if(!matchClash(ci)) continue; const c=clashes[ci],v=idx[tierOf(c)]; [c.a,c.b].forEach(e=>{const o=map.get(e); if(o===undefined||v<o) map.set(e,v);}); }
      return {classes:ts.map(t=>({k:t,n:TFULL[t],c:PAL.TIER[t].c})),map,label:'التعارضات المعروضة'}; }
    const idx={low:1,med:2,high:3},map=new Map();
    getRows('guess').forEach(R=>ruleItems(R).forEach(ii=>{ const I=ITEMS[ii],v=idx[I.it.conf]||1,o=map.get(I.ei); if(o===undefined||v<o) map.set(I.ei,v); }));
    return {classes:['low','med','high'].map(k=>({k,n:CONFN[k],c:PAL.CONF[k].c})),map,label:'فئات النقل السابقة'}; }
  function applyLens(){ if(!LENS) return; const d=lensData(); setLens('custom',{classes:d.classes,map:d.map,hideRest:false,label:d.label}); }
  function syncLens(){ if(S.lens) applyLens(); }
  function toggleLens(){ if(!LENS) return; if(S.lens){ setLens('off'); S.lens=false; } else { closeFocus(); S.lens=true; applyLens(); } toolsHTML(); }

  /* ---------------- drawer ---------------- */
  function flatIds(){
    if(!S.sel) return []; const k=S.sel.kind;
    if(k==='clash'){ const out=[]; getRows('clash').forEach(g=>g.idx.forEach(ci=>out.push(ci))); return out; }
    if(k==='guess'){ const R=RULE_BY_ID.get(ITEMS[S.sel.id].it.r); return R?ruleItems(R):[]; }
    if(k==='rule') return getRows('guess').map(R=>R.r.id);
    return []; }
  function navHTML(){ const ids=flatIds(),i=ids.indexOf(S.sel.id);
    return '<div class="is-nav"><button type="button" class="mini" data-act="prev">› السابق</button><b>'+(i<0?'—':(i+1))+' / '+ids.length+'</b><button type="button" class="mini" data-act="next">التالي ‹</button></div>'; }
  function navStep(d){ const ids=flatIds(); if(!ids.length||!S.sel) return; let i=ids.indexOf(S.sel.id); i=i<0?(d>0?0:ids.length-1):(i+d+ids.length)%ids.length; focus(S.sel.kind,ids[i]); }
  const dHead=(title,sub)=>'<div class="ih"><b>'+title+'</b><span class="ihb"><button type="button" class="is-mlist" id="isdList" aria-label="القائمة">☰ القائمة</button><button type="button" id="isdCol" aria-label="طيّ التفاصيل أو فردها" title="طيّ / فرد">▴</button><button type="button" id="isdCl" aria-label="إغلاق" title="إنهاء التركيز">×</button></span></div><div class="isub">'+sub+'</div><div class="ibody is-dr">';
  function noteHTML(kind,id){
    const ent=entryOf(kind,id)||{},names=kind==='clash'?CLS:GST,list=(kind==='clash'?CLKEYS:Object.keys(GST).filter(s=>s!=='historical')).map(s=>[s,names[s]]),cur=ent.st||'open',current=ent.st&&isCurrent(kind,id,ent);
    const ph='اكتب المرجع والورقة أو ملاحظة المراجعة؛ التنفيذ في الموقع يحتاج دليله الخاص.';
    let note='<p class="muted">تأشير المستخدم على هذا الجهاز لا يعتمد التنفيذ في الموقع ولا يغيّر نتيجة فحص المصدر والتنسيق.</p>';
    if(ent.st&&!current)note+='<p class="note">تأشير تاريخي محفوظ: '+esc(names[ent.st]||ent.st)+(ent.ts?' · '+esc(ent.ts):'')+'. سياق المصدر أو الهندسة تغير، أو لم تحفظ له بصمة. لا يُحسب تأشيرًا حاليًا. الحفظ يربط اختيارك الحالي بهذا السياق ويحفظ التأشير السابق.</p>';
    else if(current)note+='<p class="muted">التأشير مرتبط بسياق الهندسة والنوع والمراجع الحالي'+(ent.ts?' · '+esc(ent.ts):'')+'.</p>';
    const history=ent.history||[];if(history.length)note+='<details><summary>التأشيرات السابقة المحفوظة ('+history.length+')</summary>'+history.slice().reverse().map(h=>'<p>'+esc(names[h.st]||h.st||'ملاحظة')+' · '+esc(h.ts||'تاريخ غير مسجل')+(h.context?.viewer_version?' · إصدار '+esc(h.context.viewer_version):'')+'</p><p class="muted">'+esc(h.tx||'دون ملاحظة')+'</p>').join('')+'</details>';
    return '<details class="idet" open><summary>متابعتي وملاحظتي المحلية</summary>'+note+'<div class="mynote"><select id="isdSt" aria-label="تأشير المستخدم">'+opts(list,cur)+'</select><textarea id="isdTx" rows="2" placeholder="'+esc(ph)+'">'+esc(ent.tx||'')+'</textarea><div class="is-act"><button type="button" class="mini pri" data-act="save">حفظ على هذا الجهاز</button><button type="button" class="mini" data-act="clear">مسح التأشير الحالي</button></div></div></details>'; }
  function clashDrawerHTML(ci){
    const c=clashes[ci],t=tierOf(c),T=PAL.TIER[t],L=LVL[c.l],ffl=L.ffl,hh=c.pt[1]-ffl,p=sketchInputs(M,c),sk=p?sketchSVG(p):'',unit=unitName(c.a)||unitName(c.b);
    let h=dHead(esc(c.svc)+' × '+esc(c.obs),'<span class="is-ic" style="--tc:'+T.c+'">'+T.i+'</span><span style="color:'+T.c+';font-weight:600">'+esc(TFULL[t])+'</span><code>'+esc(c.id)+'</code><span>'+esc(L.name)+'</span><span>'+esc(c.sys)+'</span>');
    h+=navHTML();
    h+='<details class="idet" open><summary>الرسم: مقطع رأسي في فراغ السقف</summary>';
    h+=sk?sk+'<div class="is-ld"><span><span class="sw" style="background:#0072B2"></span>الخدمة حاليًا</span>'+(p.sug?'<span><span class="sw" style="background:#009E73"></span>المنسوب المقترح</span>':'')+'<span><span class="sw" style="background:#9aa3ad"></span>العائق</span><span><span class="sw" style="background:'+T.c+'"></span>موضع التقاطع</span></div>':'<div class="is-vis"><div class="is-none">'+(noteBox(c)||esc(c.why))+'</div></div>';
    h+='<div class="sliderrow"><span>شفافية المحيط</span><input type="range" id="isdGhost" min="0" max="40" value="'+S.ghost+'" aria-label="شفافية المحيط"><b id="isdGhostV">'+S.ghost+'%</b></div></details>';
    h+='<details class="idet" open><summary>التفاصيل</summary><table>'
      +'<tr><th>الخدمة (A)</th><td><a href="#" data-f="'+c.a+'">'+esc(elName(c.a))+'</a></td></tr>'
      +'<tr><th>العائق (B)</th><td><a href="#" data-f="'+c.b+'">'+esc(elName(c.b))+'</a></td></tr>'
      +'<tr><th>الطابق</th><td>'+esc(L.name)+' (منسوب الأرضية '+NUM(F2(ffl))+' م)</td></tr>'
      +'<tr><th>الموضع (سم)</th><td><code class="num">X '+Math.round(c.pt[0]*100)+' · Y '+Math.round(-c.pt[2]*100)+'</code></td></tr>'
      +'<tr><th>الارتفاع</th><td>'+NUM(hh.toFixed(2))+' م فوق الأرضية (مطلق '+NUM(F2(c.pt[1]))+' م)'+(hh>2.6&&c.l!=='B'?' — <b>فوق السقف المستعار</b>':'')+'</td></tr>'
      +(c.void?'<tr><th>فراغ السقف</th><td>'+NUM(F2(c.void[0])+' ← '+F2(c.void[1]))+' م ('+(c.void[2]?'سقف مستعار موجود':'لا سقف مستعار: ارتفاع صافٍ 2.40 م')+')</td></tr>':'')
      +'<tr><th>حجم التداخل</th><td>≈ '+NUM(c.v)+' م³'+(c.depth!=null?' — عمق '+NUM(c.depth)+' سم':'')+'</td></tr>'
      +(c.need!=null?'<tr><th>سماكة الخدمة</th><td>'+NUM(Math.round(c.need*100))+' سم</td></tr>':'')
      +'<tr><th>الوحدة / الموقع</th><td>'+esc(unit||'أجزاء مشتركة (ممر/ردهة/خدمات)')+'</td></tr></table></details>';
    h+='<details class="idet" open><summary>السبب والحل</summary><dl class="is-wf"><dt>السبب</dt><dd>'+esc(c.why)+'</dd><dt>الحل المقترح</dt><dd>'+esc(c.fix)+'</dd></dl><div class="muted">حدود المنسوب والافتراضات تُراجع لكل طرف في «مطابقة المشروع»؛ الاقتراح لا يثبت حلًا منفذًا.</div></details>';
    if((c.st&&c.st!=='open')||c.res||c.note) h+='<details class="idet"><summary>سجل متابعة تاريخي من الملف</summary>'+stPillClash('historical')+' '+esc((M.clashLog?.statuses||{})[c.st]||c.st||'')+' '+(c.date?'<small>'+esc(c.date)+'</small>':'')+' '+(c.by?'<small>— '+esc(c.by)+'</small>':'')+(c.res?'<div><b>طريقة الحل المسجلة:</b> '+esc(c.res)+'</div>':'')+(c.note?'<div>'+esc(c.note)+'</div>':'')+'<p class="muted">حالة مسجلة سابقًا؛ لا تثبت مصدر الإصدار الحالي أو التنفيذ في الموقع.</p></details>';
    h+=noteHTML('clash',ci)+'<div id="isdSteps"></div><div class="is-act"><button type="button" class="mini" data-act="route">مسار الوصول</button><button type="button" class="mini" data-act="tour">جولة مشي</button><button type="button" class="mini" data-act="aim">إعادة توجيه الكاميرا</button><button type="button" class="mini" data-act="end">إنهاء التركيز</button></div></div>';
    return h; }
  function moveSentence(it){ let s='السجل السابق: نُقل '+Math.round(it.cm)+' سم أفقيًا'; if(it.dz&&Math.abs(it.dz)>=0.5) s+=' وعُدّل منسوبه '+Math.round(it.dz)+' سم'; if(MOUNT[it.k]) s+=' إلى «'+MOUNT[it.k]+'»'+(it.host?' (<code>'+esc(it.host)+'</code>)':''); if(it.conv) s+='؛ تغيّر نوع التركيب'; return s+'. المسافة المسجلة لا تقيس انحراف المجسم الحالي عن المصدر.'; }
  function guessDrawerHTML(ii){
    const I=ITEMS[ii],it=I.it,e=I.e,R=RULE_BY_ID.get(it.r),r=R?R.r:{},cf=PAL.CONF[it.conf]||PAL.CONF.low,a=after(ii),T=M.types&&M.types[e.t],unit=unitName(I.ei),q=e.q||'ddd';
    let h=dHead(esc((T&&T.n)||e.t),'<span class="is-ic" style="--tc:'+cf.c+'">'+(CONFI[it.conf]||'●')+'</span><span style="font-weight:600">'+esc(CONFN[it.conf]||'فئة نقل سابقة')+'</span><code>'+esc(e.id)+'</code><span>'+esc(lvName(e.l))+'</span>'+(unit?'<span>'+esc(unit)+'</span>':''));
    h+=navHTML();
    if(it.from) h+='<details class="idet" open><summary>السجل السابق ← المجسم الحالي</summary><div class="is-ba"><div><h6>موضع سابق مسجل — ليس تحقق مصدر</h6><span class="num">X '+it.from[0]+' · Y '+it.from[1]+'</span> سم<br>المنسوب '+NUM(F2(it.from[2]))+' م</div><div class="af"><h6>الموضع الحالي في المجسم</h6><span class="num">X '+a.xcm.toFixed(1)+' · Y '+a.ycm.toFixed(1)+'</span> سم<br>المنسوب '+NUM(F2(a.zb))+' م</div></div><div class="muted">'+moveSentence(it)+'</div></details>';
    else h+='<details class="idet" open><summary>الموضع الحالي وسجل السحب السابق</summary><div class="is-ba"><div class="af" style="grid-column:1/3"><h6>الموضع الحالي في المجسم</h6><span class="num">X '+a.xcm.toFixed(1)+' · Y '+a.ycm.toFixed(1)+'</span> سم<br>المنسوب '+NUM(F2(a.zb))+' م</div></div><div class="muted">السجل السابق يذكر سحبًا '+NUM(Math.round(it.cm))+' سم إلى جدار. لا يثبت هذا السجل موضع المصدر أو التلامس الحالي؛ تحقق الموضع في «مطابقة المشروع».</div></details>';
    h+='<details class="idet" open><summary>لماذا وكيف</summary><dl class="is-wf">'+(r.why?'<dt>لماذا خُمّن</dt><dd>'+esc(r.why)+'</dd>':'')+(r.how?'<dt>كيف اختير</dt><dd>'+esc(r.how)+'</dd>':'')+(r.basis?'<dt>الأساس</dt><dd>'+esc(r.basis)+'</dd>':'')+(r.verify?'<dt>ما يحسمه</dt><dd>'+esc(r.verify)+'</dd>':'')+'</dl>'+(e.a&&e.a.mount_note?'<div class="muted">'+esc(e.a.mount_note)+'</div>':'')+'</details>';
    h+='<details class="idet"><summary>تصنيف الاستخراج التاريخي بعد التخمين</summary><p class="muted">هذه العلامات السابقة لا تثبت صحة المصدر أو المنسوب أو المواصفة. دليل الفحص الحالي في «مطابقة المشروع».</p><div class="is-q3">'+[['الموضع',q[0]],['المنسوب',q[1]],['المواصفة',q[2]]].map(x=>{const g=PAL.GRADE[x[1]]||PAL.GRADE.d; return pill(x[0]+': '+esc(g.n),'st','background:'+g.c+';color:#0b2a3d');}).join('')+'</div></details>';
    h+=noteHTML('guess',ii)+'<div class="is-act"><button type="button" class="mini" data-act="card">بطاقة العنصر الكاملة</button><button type="button" class="mini" data-act="end">إنهاء التركيز</button></div></div>';
    return h; }
  function ruleDrawerHTML(rid){
    const R=RULE_BY_ID.get(rid),r=R.r,T=IMPACT[r.impact],nl=M.levels.filter(l=>R.lv[l.id]).length;
    let h=dHead(esc(r.title),'<span class="is-ic" style="--tc:'+T.c+'">'+T.i+'</span><span style="font-weight:600">'+T.n+'</span><code>'+esc(r.id)+'</code><span>'+esc((GU.kinds||{})[r.kind]||r.kind)+'</span>');
    h+=navHTML();
    h+='<details class="idet" open><summary>التفاصيل</summary><dl class="is-wf"><dt>لماذا خُمّن</dt><dd>'+esc(r.why)+'</dd>'+(r.how?'<dt>كيف اختير</dt><dd>'+esc(r.how)+'</dd>':'')+'<dt>الأساس</dt><dd>'+esc(r.basis)+'</dd><dt>ما يحسمه</dt><dd>'+esc(r.verify)+'</dd></dl></details>';
    h+='<details class="idet" open><summary>التوزيع على الطوابق</summary><div class="is-vis">'+lvStrip(R)+'</div><div class="muted">'+P_EL(r.n)+' في '+nl+' من '+M.levels.length+' طوابق.</div></details>';
    h+=noteHTML('rule',rid)+'<div class="is-act"><button type="button" class="mini pri" data-act="hl">أبرِز في المجسم</button><button type="button" class="mini" data-act="end">إنهاء التركيز</button></div></div>';
    return h; }
  function focusElLink(ei){ const c=S.sel&&S.sel.kind==='clash'?clashes[S.sel.id]:null; clearHL(); highlight([ei],c&&ei===c.a?0xff8a00:0x2f81f7,true,0.35);
    const bb=bboxOf([ei]),p=new THREE.Vector3(bb.c[0],bb.c[1],bb.c[2]); flyTo(p.clone().add(new THREE.Vector3(-0.55,0.4,0.7).normalize().multiplyScalar(Math.max(2.5,bb.r*2.4))),p); }
  function drawerAct(a,el){
    const s=S.sel; if(!s) return;
    if(a==='prev') navStep(-1); else if(a==='next') navStep(1); else if(a==='end') closeFocus();
    else if(a==='save'){ setStatus(s.kind,s.id,$('isdSt').value,$('isdTx').value.trim()); toast('حُفظت حالتك على هذا الجهاز'); }
    else if(a==='clear'){ setStatus(s.kind,s.id,'open',''); $('isdTx').value=''; $('isdSt').value='open'; toast('أزيل التأشير الحالي؛ بقي سجل التأشيرات السابقة محفوظًا'); }
    else if(a==='route'&&s.kind==='clash'){ $('isdSteps').innerHTML=CLASH.showRoute(clashes[s.id]); }
    else if(a==='tour'&&s.kind==='clash'){ $('isdSteps').innerHTML=CLASH.runTour(clashes[s.id]); }
    else if(a==='aim'&&s.kind==='clash'){ CLASH.show(s.id); if(S.ghost!==8) setGhost(true,S.ghost/100,[clashes[s.id].l]); }
    else if(a==='card'&&s.kind==='guess'){ select(ITEMS[s.id].ei,true); }
    else if(a==='hl'&&s.kind==='rule'){ focusRule(s.id); } }
  function bindDrawer(el){
    el.onclick=ev=>{ const t=ev.target;
      if(t.closest('#isdCl')){ closeFocus(); return; }
      if(t.closest('#isdCol')){ el.classList.toggle('min'); return; }
      if(t.closest('#isdList')){ document.body.classList.add('panel-open'); return; }
      const f=t.closest('a[data-f]'); if(f){ ev.preventDefault(); focusElLink(+f.dataset.f); return; }
      const b=t.closest('[data-act]'); if(b) drawerAct(b.dataset.act,el); };
    el.oninput=ev=>{ if(ev.target.id==='isdGhost'&&S.sel&&S.sel.kind==='clash'){ S.ghost=+ev.target.value; $('isdGhostV').textContent=S.ghost+'%'; setGhost(true,S.ghost/100,[clashes[S.sel.id].l]); } }; }
  function setStatus(kind,id,st,tx){ putEntry(kind,id,st,tx); if(built) refresh(); }

  /* ---------------- panes ---------------- */
  let built=false;
  function renderPane(){ const p=$('isPane'); if(!p) return; if(S.view==='list') p.innerHTML=S.kind==='clash'?clashListHTML():guessListHTML(); else if(S.view==='mx') p.innerHTML=matrixHTML(); else renderMap(); }
  function renderCard(id){
    const p=$('isPane'); if(!p||S.view!=='list') return; const el=p.querySelector(S.kind==='clash'?'.is-card[data-gid="'+id+'"]':'.is-card[data-rid="'+id+'"]'); if(!el) return;
    const rows=getRows(S.kind); let html='';
    if(S.kind==='clash'){ const g=rows.find(x=>x.gk===id); if(!g) return; html=clashCardHTML(g); } else { const R=rows.find(x=>x.r.id===id); if(!R) return; html=ruleCardHTML(R); }
    const tmp=document.createElement('div'); tmp.innerHTML=html; if(tmp.firstElementChild) el.replaceWith(tmp.firstElementChild); }
  function markSel(){
    const p=$('isPane'); if(!p) return; p.querySelectorAll('.is-card.sel,.is-loc.sel').forEach(x=>x.classList.remove('sel')); const s=S.sel; if(!s||S.view!=='list') return;
    let card=null,loc=null;
    if(s.kind==='group'||s.kind==='clash'){ const gk=s.kind==='group'?s.id:clashes[s.id].gk; card=p.querySelector('.is-card[data-gid="'+gk+'"]'); if(s.kind==='clash') loc=p.querySelector('.is-loc[data-ci="'+s.id+'"]'); }
    else { const rid=s.kind==='rule'?s.id:ITEMS[s.id].it.r; card=p.querySelector('.is-card[data-rid="'+rid+'"]'); if(s.kind==='guess') loc=p.querySelector('.is-loc[data-ii="'+s.id+'"]'); }
    if(card) card.classList.add('sel'); if(loc) loc.classList.add('sel');
    const t=loc||card; if(t&&sectionOpen()&&t.scrollIntoView) t.scrollIntoView({block:'nearest',behavior:'smooth'}); }
  function refresh(){ if(!built) return; ROWS={clash:null,guess:null}; updateLevels(); updateProg(); updateSum(); renderPane(); rebuildPins(); syncLens(); }
  function render(){ if(!built) return; $('isRoot').dataset.kind=S.kind; tabsHTML(); buildHead(); viewsHTML(); toolsHTML(); refresh(); }
  function drawingIssuesHTML(){
    const ds=M.drawingIssues||[]; if(!ds.length) return '';
    const st={corrected:'صحح في النموذج',source_conflict:'تعارض مصدر مفتوح',source_gap:'نقص مصدر',model_candidate:'تداخل مرشح يحتاج تنسيقًا'};
    return '<details id="drawingIssues"><summary>مراجعة المواضع والمصادر ('+ds.length+')</summary><div class="note">التصحيحات تخص المجسم؛ لا تثبت التنفيذ في الموقع. لكل حالة مصدر وموضع وإجراء.</div>'+ds.map((d,i)=>'<article class="is-card"><b>'+esc(d.title)+'</b><small>'+esc(st[d.status]||d.status)+' · '+esc(d.id)+'</small><p>'+esc(d.note)+'</p><small>'+esc(d.source)+(d.xy_cm?' · X/Y سم: '+esc(d.xy_cm.join(' / ')):'')+'</small><button type="button" class="mini" data-drawing-issue="'+i+'">تفاصيل وموضع</button></article>').join('')+'</details>';
  }
  function focusDrawing(i){
    const d=(M.drawingIssues||[])[i]; if(!d) return;
    const inds=(d.elements||[]).map(id=>idOf.get(id)).filter(j=>j!==undefined);
    CLASH.endFocus(); clearHL();
    if(inds.length){inds.forEach(ensureVisible);highlight(inds,0x2f81f7,true,.3);flyToBox(bboxOf(inds));}
    else if(d.xy_cm&&LVL[d.level]){const p=new THREE.Vector3(d.xy_cm[0]/100,d.z_m==null?LVL[d.level].ffl:d.z_m,-d.xy_cm[1]/100);flyTo(p.clone().add(new THREE.Vector3(-3,4,5)),p);}
    const val=v=>v==null?'غير محدد':JSON.stringify(v);
    showDrawer('<section dir="rtl"><h3>'+esc(d.title)+'</h3><p>'+esc(d.note)+'</p><table class="ctab"><tr><th>المصدر</th><td>'+esc(d.source)+'</td></tr><tr><th>الموضع</th><td>'+esc(d.level||'عام')+' / '+esc(val(d.xy_cm))+' سم</td></tr><tr><th>المنسوب</th><td>'+esc(val(d.z_m))+' م</td></tr><tr><th>قبل</th><td>'+esc(val(d.before))+'</td></tr><tr><th>بعد</th><td>'+esc(val(d.after))+'</td></tr></table><p>الحالة تخص المجسم أو تعارض الأوراق؛ لا توثّق معالجة منفذة في الموقع.</p></section>',()=>{});
    wake();
  }
  function buildRoot(){
    if(built) return; built=true;
    box.innerHTML=drawingIssuesHTML()+'<div class="is-root" id="isRoot" data-kind="clash"><div class="is-tabs" role="tablist" aria-label="نوع القائمة" id="isTabs"></div><div id="isHead"></div><div class="is-bar" id="isBar"><div class="is-sum" id="isSum" aria-live="polite"></div><div class="is-views" role="tablist" id="isViews"></div></div><div class="is-tools" id="isTools"></div><div class="is-pane" id="isPane"></div></div>';
    box.addEventListener('click',onClick); box.addEventListener('change',onChange); box.addEventListener('input',onInput); render(); }

  /* ---------------- focus in 3-D ---------------- */
  function afterFocusUI(){ if(!built) return; markSel(); toolsHTML(); mapSync(); }
  function revealCard(id,open){
    if(!built||S.view!=='list') return; const rows=getRows(S.kind),i=rows.findIndex(x=>(S.kind==='clash'?x.gk:x.r.id)===id); if(i<0) return;
    if(open!==false) S.open.add(id); if(i>=S.page[S.kind]){ S.page[S.kind]=Math.ceil((i+1)/PAGE)*PAGE; renderPane(); } else renderCard(id); }
  function focusClash(ci,opt){
    opt=opt||{}; if(!opt.ap) stopAp(); const c=clashes[ci];
    fxClear(); if(LENS&&LENS.mode==='custom') setLens('off'); S.lens=false;
    CLASH.show(ci); if(S.ghost!==8) setGhost(true,S.ghost/100,[c.l]);
    S.sel={kind:'clash',id:ci}; revealCard(c.gk); showDrawer(clashDrawerHTML(ci),bindDrawer); updateSelPin(); afterFocusUI(); wake(); }
  function focusGroup(gk,opt){
    opt=opt||{}; if(!opt.ap) stopAp(); const g=getRows('clash').find(x=>x.gk===gk); if(!g) return;
    fxClear(); CLASH.endFocus(); hideDrawer();
    const pts=[],map=new Map(); g.idx.forEach(ci=>{ const c=clashes[ci]; ensureVisible(c.a); ensureVisible(c.b); map.set(c.a,1); if(!map.has(c.b)) map.set(c.b,2); pts.push(c.pt); });
    const mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9]; pts.forEach(p=>{ for(let i=0;i<3;i++){ mn[i]=Math.min(mn[i],p[i]); mx[i]=Math.max(mx[i],p[i]); } });
    if(LENS) setLens('custom',{classes:[{k:'svc',n:'الخدمة',c:'#0072B2'},{k:'obs',n:'العائق',c:PAL.TIER[g.tier].c}],map,hideRest:false,label:'مجموعة: '+g.meta.svc+' × '+g.meta.obs}); S.lens=false;
    setGhost(true,1,[g.meta.l]);   // show only the group's level (no transparency: the lens colours stay clear)
    flyToBox({c:[(mn[0]+mx[0])/2,(mn[1]+mx[1])/2,(mn[2]+mx[2])/2],r:Math.max(1.5,Math.hypot(mx[0]-mn[0],mx[1]-mn[1],mx[2]-mn[2])/2+1)});
    document.body.classList.remove('panel-open'); S.sel={kind:'group',id:gk}; revealCard(gk); updateSelPin(); afterFocusUI(); wake(); }
  function focusGuess(ii,opt){
    opt=opt||{}; if(!opt.ap) stopAp(); const I=ITEMS[ii],it=I.it,ei=I.ei,e=I.e;
    fxClear(); CLASH.endFocus(); if(LENS&&LENS.mode==='custom') setLens('off'); S.lens=false;
    ensureVisible(ei); const hi=it.host?idOf.get(it.host):undefined; if(hi!==undefined) ensureVisible(hi);
    setGhost(true,0.10,[e.l]); clearHL(); highlight([ei],0x0072B2,true,0.45); if(hi!==undefined) addHL([hi],0x9AA3AD,true,0.2);
    fxShow(it,after(ii)); flyToBox(bboxOf([ei]),[-0.55,0.45,0.7]);
    S.sel={kind:'guess',id:ii}; revealCard(it.r); showDrawer(guessDrawerHTML(ii),bindDrawer); updateSelPin(); afterFocusUI(); wake(); }
  function focusRule(rid,opt){
    opt=opt||{}; if(!opt.ap) stopAp(); const R=RULE_BY_ID.get(rid); if(!R) return; const r=R.r;
    fxClear(); CLASH.endFocus();
    const nm=r.title.length>60?r.title.slice(0,57)+'…':r.title;
    if(!opt.drawerOnly){ const all=R.idx(),sub=all.filter(i=>ctx.elVisible(i));
      if(LENS) setLens('custom',{classes:[{k:'r',n:nm,c:IMPACT[r.impact].c}],map:new Map(all.map(i=>[i,1])),hideRest:false,label:'افتراض: '+nm}); S.lens=false;
      if(sub.length) flyToBox(bboxOf(sub.length>4000?sub.slice(0,4000):sub)); else toast('عناصر هذا الافتراض مخفية حاليًا — فعّل أقسامها أو طوابقها'); }
    S.sel={kind:'rule',id:rid}; revealCard(rid,false); showDrawer(ruleDrawerHTML(rid),bindDrawer); updateSelPin(); afterFocusUI(); wake(); }
  function focus(kind,id,opt){
    if(!built) buildRoot(); const want=(kind==='clash'||kind==='group')?'clash':'guess'; if(S.kind!==want) setKind(want);
    if(kind==='clash') focusClash(+id,opt); else if(kind==='group') focusGroup(id,opt); else if(kind==='guess') focusGuess(+id,opt); else if(kind==='rule') focusRule(id,opt); }
  function closeFocus(){
    stopAp(); if(!S.sel&&!fx) return; fxClear(); CLASH.endFocus(); clearHL(); hideDrawer(); if(LENS&&LENS.mode==='custom') setLens('off'); S.lens=false; S.sel=null;
    updateSelPin(); if(built){ markSel(); toolsHTML(); mapSync(); } wake(); }

  /* ---------------- autopilot ---------------- */
  function apList(){
    if(S.kind==='clash') return getRows('clash').slice(0,AP_N).map(g=>({kind:'clash',id:g.idx[0]}));
    const out=[]; getRows('guess').forEach(R=>{ if(R.hasItems) ruleItems(R).forEach(ii=>out.push(ii)); }); return out.slice(0,AP_N).map(ii=>({kind:'guess',id:ii})); }
  function startAp(){ const list=apList(); if(!list.length){ toast('لا عناصر للتشغيل التلقائي ضمن المرشحات الحالية'); return; } if(S.sel) closeFocus(); S.ap={list,i:0,t:0}; toolsHTML(); stepAp(); }
  function stepAp(){ const a=S.ap; if(!a) return; if(a.i>=a.list.length){ stopAp(); toast('انتهى التشغيل التلقائي'); return; }
    const it=a.list[a.i]; focus(it.kind,it.id,{ap:true}); toast('تشغيل تلقائي: '+(a.i+1)+' من '+a.list.length+' — حرّك الكاميرا أو اضغط «إيقاف» لإنهائه',AP_MS-400); a.i++; a.t=setTimeout(stepAp,AP_MS); }
  function stopAp(){ if(!S.ap) return; clearTimeout(S.ap.t); S.ap=null; if(built) toolsHTML(); }
  try{ controls.addEventListener('start',()=>{ if(S.ap) stopAp(); }); }catch(e){}

  /* ---------------- keyboard: [ previous, ] next (event.code: independent of the keyboard language) ---------------- */
  window.addEventListener('keydown',ev=>{
    if(!S.sel||ev.ctrlKey||ev.metaKey||ev.altKey) return; const t=ev.target;
    if(t&&((t.tagName==='INPUT'&&t.type!=='range'&&t.type!=='checkbox')||t.tagName==='TEXTAREA'||t.tagName==='SELECT'||t.isContentEditable)) return;
    if(ev.code==='BracketRight'){ ev.preventDefault(); navStep(1); } else if(ev.code==='BracketLeft'){ ev.preventDefault(); navStep(-1); } });

  /* ---------------- CSV ---------------- */
  const q2=v=>'"'+String(v==null?'':v).replace(/"/g,'""')+'"';
  function csv(kind){
    kind=kind||S.kind; const rows=[]; const stl=(k,id)=>{ const e=entryOf(k,id)||{},names=k==='clash'?CLS:GST,current=e.st&&isCurrent(k,id,e);return [e.st?(current?(names[e.st]||e.st):names.historical+' ('+(names[e.st]||e.st)+')'):'',e.tx||'',current?'مرتبط بالسياق الحالي':e.st?'تاريخي؛ لا يحسم تحقق المصدر':'',e.context?.viewer_version||'',e.context?.fingerprint||'']; };
    if(kind==='clash'){
      rows.push(['id','الدرجة','الطابق','النظام','الخدمة','العائق','عنصر الخدمة','عنصر العائق','X سم','Y سم','المنسوب المطلق م','الارتفاع فوق الأرضية م','حجم التداخل م3','عمق التداخل سم','سماكة الخدمة سم','النطاق الحر م','السبب','الحل المقترح','حالة مسجلة تاريخيًا من الملف','تأشير المستخدم','ملاحظتي','سياق التأشير','إصدار التأشير','بصمة سياق التأشير']);
      getRows('clash').forEach(g=>g.idx.forEach(ci=>{ const c=clashes[ci],s=stl('clash',ci); rows.push([c.id,TFULL[tierOf(c)],lvName(c.l),c.sys,c.svc,c.obs,c.ea,c.eb,Math.round(c.pt[0]*100),Math.round(-c.pt[2]*100),c.pt[1].toFixed(2),(c.pt[1]-LVL[c.l].ffl).toFixed(2),c.v,c.depth==null?'':c.depth,c.need==null?'':Math.round(c.need*100),c.band?c.band[0]+'..'+c.band[1]:'',c.why,c.fix,(M.clashLog?.statuses||{})[c.st||'open']||c.st,...s]); })); }
    else {
      rows.push(['نوع الصف','معرّف القاعدة','عنوان القاعدة','النوع','الأثر','عدد العناصر','معرّف العنصر','الوسم','نوع العنصر','الطابق','قبل X سم','قبل Y سم','قبل المنسوب م','مسافة النقل سم','تغيّر المنسوب سم','المضيف','طريقة التركيب','فئة النقل السابقة','لماذا','كيف','الأساس','ما يحسمه','تأشير المستخدم','ملاحظتي','سياق التأشير','إصدار التأشير','بصمة سياق التأشير']);
      getRows('guess').forEach(R=>{ const r=R.r,s=stl('rule',r.id); rows.push(['قاعدة',r.id,r.title,(GU.kinds||{})[r.kind]||r.kind,IMPACT[r.impact].n,r.n,'','','','','','','','','','','','',r.why,r.how||'',r.basis,r.verify,...s]);
        ruleItems(R).forEach(ii=>{ const I=ITEMS[ii],it=I.it,e=I.e,t=M.types&&M.types[e.t],s2=stl('guess',ii); rows.push(['قرار',r.id,r.title,(GU.kinds||{})[r.kind]||r.kind,IMPACT[r.impact].n,1,e.id,e.mark||'',(t&&t.n)||e.t,lvName(e.l),it.from?it.from[0]:'',it.from?it.from[1]:'',it.from?it.from[2]:'',it.cm==null?'':it.cm,it.dz==null?'':it.dz,it.host||'',MOUNT[it.k]||'',CONFN[it.conf]||'',r.why,r.how||'',r.basis,r.verify,...s2]); }); }); }
    return '﻿'+rows.map(r=>r.map(q2).join(',')).join('\n'); }
  function downloadCsv(){
    const text=csv(S.kind),d=new Date(),ds=d.getFullYear()+String(d.getMonth()+1).padStart(2,'0')+String(d.getDate()).padStart(2,'0');
    const a=document.createElement('a'); a.href=URL.createObjectURL(new Blob([text],{type:'text/csv;charset=utf-8'})); a.download=(S.kind==='clash'?'c4_clashes_':'c4_guesses_')+ds+'.csv'; document.body.appendChild(a); a.click();
    setTimeout(()=>{URL.revokeObjectURL(a.href); a.remove();},500); toast('صُدِّر '+(text.split('\n').length-1)+' صفًّا'); }

  /* ---------------- events ---------------- */
  function setKind(k){ if(k===S.kind) return; if(S.sel||S.ap) closeFocus(); S.kind=k; S.mapLevel=null; ROWS={clash:null,guess:null}; render(); }
  function setView(v){ if(v===S.view) return; S.view=v; viewsHTML(); renderPane(); markSel(); }
  function toggleTile(b){
    const f=S.f[S.kind],bag=S.kind==='clash'?f.tiers:f.imps,key=b.dataset.tier||b.dataset.imp,on=Object.keys(bag).filter(x=>bag[x]);
    if(bag[key]&&on.length===1) return; bag[key]=bag[key]?0:1; b.classList.toggle('on',!!bag[key]); b.setAttribute('aria-pressed',String(!!bag[key])); S.page[S.kind]=PAGE; refresh(); }
  function toggleLevel(l){ const f=S.f[S.kind]; if(l==='*') f.lv=new Set(); else if(f.lv.has(l)) f.lv.delete(l); else f.lv.add(l); S.page[S.kind]=PAGE; refresh(); }
  function cellClick(b){
    const d=b.dataset,f=S.f[S.kind];
    if(d.sys!==undefined){ f.sys=d.sys; f.obs=d.obs; } else if(d.lvl!==undefined){ f.tiers={c:0,k:0,m:0}; f.tiers[d.tier]=1; f.lv=new Set([d.lvl]); } else if(d.kind!==undefined){ f.kind=d.kind; f.layer=d.layer; } else return;
    S.view='list'; S.page[S.kind]=PAGE; render(); }
  function act(b){
    const a=b.dataset.act;
    if(a==='reset'){ S.f[S.kind]=defaults(S.kind); S.qn[S.kind]=''; S.page[S.kind]=PAGE; render(); return; }
    if(a==='lens'){ toggleLens(); return; }
    if(a==='pins'){ S.pins=!S.pins; toolsHTML(); wake(); return; }
    if(a==='ap'){ if(S.ap) stopAp(); else startAp(); return; }
    if(a==='csv'){ downloadCsv(); return; }
    if(a==='how'){ S.how=!S.how; $('isHow').hidden=!S.how; b.setAttribute('aria-expanded',String(S.how)); return; }
    if(a==='adv'){ S.adv=!S.adv; $('isAdv').hidden=!S.adv; updateAdv(); return; }
    if(a==='more'){ if(b.dataset.more==='cards'){ S.page[S.kind]+=PAGE; renderPane(); markSel(); } else { const id=b.dataset.id; S.pageLoc[id]=(S.pageLoc[id]||PAGE_LOC)+PAGE_LOC; renderCard(id); } return; }
    const card=b.closest('.is-card');
    if(a==='locs'&&card){ const id=card.dataset.gid||card.dataset.rid; if(S.open.has(id)) S.open.delete(id); else S.open.add(id); renderCard(id); return; }
    if(a==='view'&&card){ const g=getRows('clash').find(x=>x.gk===card.dataset.gid); if(!g) return; if(g.idx.length===1) focus('clash',g.idx[0]); else focusGroup(g.gk); return; }
    if(a==='hl'&&card){ focusRule(card.dataset.rid); return; }
    if(a==='det'&&card){ focusRule(card.dataset.rid,{drawerOnly:true}); return; }
    if(a==='loc'){ const li=b.closest('.is-loc'); if(!li) return; if(li.dataset.ci!==undefined) focus('clash',+li.dataset.ci); else if(li.dataset.ii!==undefined) focus('guess',+li.dataset.ii); else if(li.dataset.ei!==undefined) focusEl(+li.dataset.ei); } }
  function onClick(ev){
    const t=ev.target; let b;
    if((b=t.closest('[data-drawing-issue]'))){focusDrawing(+b.dataset.drawingIssue);return;}
    if((b=t.closest('[data-tab]'))){ setKind(b.dataset.tab); return; }
    if((b=t.closest('.is-tile'))){ toggleTile(b); return; }
    if((b=t.closest('#isLv [data-lv]'))){ toggleLevel(b.dataset.lv); return; }
    if((b=t.closest('.is-vw'))){ setView(b.dataset.view); return; }
    if((b=t.closest('[data-ml]'))){ S.mapLevel=b.dataset.ml; renderMap(); return; }
    if((b=t.closest('.is-cell'))){ if(!b.classList.contains('zero')) cellClick(b); return; }
    if((b=t.closest('[data-act]'))) act(b); }
  function onChange(ev){
    const t=ev.target;
    if(t.tagName==='SELECT'&&t.dataset.f){ S.f[S.kind][t.dataset.f]=t.value; S.page[S.kind]=PAGE; updateAdv(); refresh(); return; }
    if(t.tagName==='SELECT'&&t.dataset.bulk!==undefined){ const st=t.value; if(!st) return; const g=getRows('clash').find(x=>x.gk===t.dataset.bulk); if(!g) return;
      g.idx.forEach(ci=>{ const e=entryOf('clash',ci)||{}; putEntry('clash',ci,st,e.tx||''); }); toast('عُيّنت الحالة لـ'+P_POS(g.idx.length)); refresh(); } }
  let qT=0;
  function onInput(ev){ const t=ev.target; if(!t.classList||!t.classList.contains('is-q')) return; clearTimeout(qT);
    qT=setTimeout(()=>{ const k=S.kind; S.f[k].q=t.value; S.qn[k]=normAr(t.value.trim()); S.page[k]=PAGE; refresh(); },150); }

  /* ---------------- public API ---------------- */
  function open(kind,opts){ opts=opts||{}; if(!built) buildRoot(); if(kind&&kind!==S.kind) setKind(kind); if(opts.view) setView(opts.view); }
  function setFilter(kind,o){
    const f=S.f[kind]; Object.keys(o||{}).forEach(k=>{ if(k==='lv') f.lv=new Set(o.lv||[]); else if(k==='tiers'||k==='imps') Object.assign(f[k],o[k]); else if(k==='q'){ f.q=o.q||''; S.qn[kind]=normAr(f.q.trim()); } else f[k]=o[k]; });
    S.page[kind]=PAGE; ROWS={clash:null,guess:null}; if(built){ if(kind!==S.kind) setKind(kind); else render(); } }
  function state(){
    const f=S.f[S.kind],rows=built?getRows():[],o={built,kind:S.kind,view:S.view,sel:S.sel,autopilot:!!S.ap,lens:S.lens,pins:pinRefs.length,filters:{lv:[...f.lv],sort:f.sort,q:f.q,st:f.st},counts:{}};
    if(S.kind==='clash'){ o.filters.tiers=Object.assign({},f.tiers); o.filters.sys=f.sys; o.filters.obs=f.obs; o.counts={groups:rows.length,clashes:rows.reduce((a,g)=>a+g.idx.length,0)}; }
    else { o.filters.imps=Object.assign({},f.imps); o.filters.kind=f.kind; o.filters.layer=f.layer; o.counts={rules:rows.length,decisions:rows.reduce((a,R)=>a+(R.hasItems?ruleItems(R).length:0),0)}; }
    o.map={level:S.mapLevel,pins:mapData?mapData.pins.length:0,arrows:mapData?mapData.arrows.length:0}; return o; }
  function frame(now){
    if(!built) return;
    const sig=M.levels.map(l=>levelVisible(l.id)?1:0).join(''); if(sig!==lvSig) rebuildPins();
    const want=S.pins&&!suspended&&(sectionOpen()||!!S.sel)&&!exploded(); if(pinG.visible!==want){ pinG.visible=want; wake(); }
    if(selPts){ const sv=!!(S.sel&&(S.sel.kind==='clash'||S.sel.kind==='guess'))&&!exploded(); if(selPts.visible!==sv) selPts.visible=sv; if(sv){ selPts.material.size=32+5*Math.sin(now/280); wake(120); } }
    if(S.view==='map'&&pm) updateCam(false);
    if(S.lens&&LENS&&LENS.mode!=='custom'){ S.lens=false; toolsHTML(); } }


  /* ---------------- element-card hooks: what does the issue centre know about this element? ---------------- */
  const itemOfEl=new Map(); ITEMS.forEach((I,ii)=>{ if(!itemOfEl.has(I.ei)) itemOfEl.set(I.ei,ii); });
  const clashesOfEl=new Map(); clashes.forEach((c,ci)=>{ [c.a,c.b].forEach(e=>{ let a=clashesOfEl.get(e); if(!a){a=[]; clashesOfEl.set(e,a);} a.push(ci); }); });
  function infoHTML(ei){
    let h=''; const ii=itemOfEl.get(ei);
    if(ii!==undefined){ const I=ITEMS[ii],it=I.it,cf=PAL.CONF[it.conf]||PAL.CONF.low,R=RULE_BY_ID.get(it.r);
      h+='<div class="is-inf"><b>تخمين تاريخي مسجَّل في «مركز المتابعة»</b>'+esc(R?R.r.title:'')+' — <span style="font-weight:600">'+esc(CONFN[it.conf]||'فئة نقل سابقة')+'</span>'+' · مسافة مسجلة '+Math.round(it.cm)+' سم؛ ليست انحرافًا مثبتًا في الإصدار الحالي<br><button type="button" class="mini" data-iss="g:'+ii+'">اعرض السجل والموضع الحالي</button></div>'; }
    const cl=clashesOfEl.get(ei);
    if(cl&&cl.length){ const sorted=cl.slice().sort((a,b)=>TRANK[tierOf(clashes[a])]-TRANK[tierOf(clashes[b])]);
      h+='<div class="is-inf"><b>تعارضات يشارك فيها هذا العنصر ('+cl.length+')</b>'+sorted.slice(0,6).map(ci=>{ const c=clashes[ci],t=tierOf(c); return '<button type="button" class="chip" data-iss="c:'+ci+'" style="border-color:'+PAL.TIER[t].c+'"><span class="is-ic" style="--tc:'+PAL.TIER[t].c+'">'+PAL.TIER[t].i+'</span> '+esc(TLAB[t])+' — '+esc(clashOtherName(c,ei))+'</button>'; }).join('')+(cl.length>6?' <small>و'+(cl.length-6)+' أخرى</small>':'')+'</div>'; }
    return h; }
  document.addEventListener('click',ev=>{ const b=ev.target.closest&&ev.target.closest('[data-iss]'); if(!b) return; const p=b.dataset.iss.split(':'); if(p[0]==='g') focus('guess',+p[1]); else if(p[0]==='c') focus('clash',+p[1]); });

  try{ new MutationObserver(()=>{ if(sectionOpen()&&!built) buildRoot(); wake(); }).observe(sec,{attributes:true,attributeFilter:['class']}); }catch(e){}
  if(sectionOpen()) buildRoot();
  return {open,focus,infoHTML,suspend:on=>{ suspended=!!on; wake(); },next:()=>navStep(1),prev:()=>navStep(-1),close:closeFocus,autopilot:on=>{ if(on) startAp(); else stopAp(); },setFilter,setStatus,state,csv,tap,frame,pinAt,get active(){return !!S.sel||!!S.ap;}};
}
window.initIssues=initIssues;
})();
