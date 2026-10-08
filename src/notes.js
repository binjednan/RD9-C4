/* ===== Owner's notes + «إخفاء العنصر» (2026-10-08) =====
   Two small tools that live in the element card and in a side-panel section («ملاحظاتي»):
   * HIDE — the selected element (the whole group it belongs to) or every element of its type is taken out of the model (bit 2 of the per-vertex aHide flag, app.js setUserHidden);
     it cannot be picked, highlighted or drawn in detail until it is shown again. The set is remembered on this device (localStorage c4hidden) and a toolbar button
     «إظهار المخفية (N)» is always visible while anything is hidden, so nothing silently goes missing.
   * NOTE — a free-text comment on the selected element: what the owner wants changed in the next revision. Saved on this device (c4notes), pinned in 3-D, listed in the panel,
     and exported as text (copy / share) or JSON so it can be pasted straight into the conversation. Each note keeps a snapshot of the element (id, type, level, unit, position)
     so it can still be located after the model is rebuilt.
   Nothing here touches the model data, the pipeline or any other module's state. ES2018 style (no ?. / ??). */
(function(){
'use strict';
function initNotes(ctx){
  const {M,THREE,scene,camera,renderer,$,esc,LVL,UNITS,TYPES,CATS,wake,toast,bboxOf,grpMap,userHidden,setUserHidden,sel,clearHL,highlight,focusEl,flyTo,levelVisible,openSec}=ctx;
  const KN='c4notes', KH='c4hidden';
  let store={v:1,general:'',notes:{}}, canSave=true;
  try{ localStorage.setItem('c4probe','1'); localStorage.removeItem('c4probe'); }catch(e){ canSave=false; }
  try{ const s=localStorage.getItem(KN); if(s){ const o=JSON.parse(s); if(o&&typeof o==='object'&&o.notes&&typeof o.notes==='object') store={v:1,general:String(o.general||''),notes:o.notes}; } }catch(e){}
  function save(){ try{ localStorage.setItem(KN,JSON.stringify(store)); canSave=true; }catch(e){ canSave=false; } }
  function saveHidden(){ const ids=[]; userHidden.forEach(ei=>ids.push(M.els[ei].id)); try{ localStorage.setItem(KH,JSON.stringify(ids)); }catch(e){ canSave=false; } }

  /* ---------------- element helpers ---------------- */
  const idIdx=new Map(), typeIdx=new Map();
  M.els.forEach((e,i)=>{ idIdx.set(e.id,i); let a=typeIdx.get(e.t); if(!a) typeIdx.set(e.t,a=[]); a.push(i); });
  const keyOf=ei=>{ const e=M.els[ei]; return e.grp?('G:'+e.grp):e.id; };
  const membersOf=ei=>{ const e=M.els[ei]; return (e.grp&&grpMap[e.grp])?grpMap[e.grp]:[ei]; };
  const typeName=ei=>{ const e=M.els[ei],T=TYPES[e.t]||{},c=CATS[e.c]; return T.n||(c&&c.name)||e.t; };
  const lvTxt=l=>{ const v=LVL[l]; return v?(v.name+' ('+(v.ffl>0?'+':'')+v.ffl.toFixed(2)+')'):String(l); };
  const unitName=u=>{ if(!u) return null; const x=UNITS.find(q=>q.id===u); return x?x.name:String(u); };
  function snapOf(ei){ const e=M.els[ei],mem=membersOf(ei),b=bboxOf(mem);
    return {id:e.id,nm:typeName(ei),lv:e.l,lvn:lvTxt(e.l),un:unitName(e.u),n:mem.length,p:[+b.c[0].toFixed(3),+b.c[1].toFixed(3),+b.c[2].toFixed(3)]}; }
  const getNote=ei=>store.notes[keyOf(ei)]||null;
  const hiddenId=id=>{ const i=idIdx.get(id); return i!==undefined&&userHidden.has(i); };

  /* ---------------- hide / show ---------------- */
  function hideSet(idxs,on){
    const S=sel(); setUserHidden(idxs,on); saveHidden();
    if(S.idx>=0&&S.set.some(i=>idxs.indexOf(i)>=0)){ if(on) clearHL(); else highlight(S.set); }
    changed(); }
  function unhideAll(){ const a=[]; userHidden.forEach(i=>a.push(i)); if(!a.length) return; hideSet(a,false); toast('أُظهرت كل العناصر المخفية ('+a.length+')',2400); }
  function restore(){
    let ids=[]; try{ const s=localStorage.getItem(KH); if(s) ids=JSON.parse(s)||[]; }catch(e){}
    const idx=[]; ids.forEach(id=>{ const i=idIdx.get(id); if(i!==undefined) idx.push(i); });
    if(idx.length) setUserHidden(idx,true); }

  /* ---------------- the element card ---------------- */
  function barInner(ei){
    const e=M.els[ei],mem=membersOf(ei),allH=mem.every(i=>userHidden.has(i)),tl=typeIdx.get(e.t)||[ei],tAll=tl.every(i=>userHidden.has(i)),nt=getNote(ei);
    let h='<button type="button" class="nt-b'+(allH?' on':'')+'" data-nt="hide" title="إخفاء هذا العنصر من المجسم أو إظهاره (مفتاح H)"><span class="nt-ic">'+(allH?'◉':'⊘')+'</span><span>'+(allH?'إظهار العنصر':'إخفاء العنصر')+'</span></button>';
    if(tl.length>1) h+='<button type="button" class="nt-b'+(tAll?' on':'')+'" data-nt="hidetype" title="'+esc('كل عناصر النوع: '+typeName(ei))+'"><span class="nt-ic">'+(tAll?'◉':'⊘')+'</span><span>'+(tAll?'إظهار النوع':'إخفاء النوع')+' ('+tl.length+')</span></button>';
    h+='<button type="button" class="nt-b'+(nt?' has':'')+'" data-nt="note" title="اكتب ما تريد تنفيذه على هذا العنصر"><span class="nt-ic">✎</span><span>ملاحظتي</span><i class="nt-dot"></i></button>';
    return h; }
  let pend=null,pendT=0;
  function flush(){ if(!pend) return; clearTimeout(pendT); const p=pend; pend=null; setNote(p.ei,p.text); }
  function infoHTML(ei){
    flush(); const nt=getNote(ei);
    return '<div class="nt-bar" data-ei="'+ei+'">'+barInner(ei)+'</div>'
      +'<div class="nt-ed" data-ei="'+ei+'"'+(nt?'':' hidden')+'><textarea class="nt-ta" dir="auto" rows="3" maxlength="4000" placeholder="اكتب ما تريد تنفيذه على هذا العنصر في التعديلات القادمة…" aria-label="ملاحظتي على هذا العنصر">'+esc(nt?nt.t:'')+'</textarea>'
      +'<div class="nt-meta"><span class="nt-st">'+(nt?stamp(nt.ts)+' · محفوظة على هذا الجهاز':'تُحفظ تلقائيًا على هذا الجهاز')+'</span><span class="nt-ba"><button type="button" class="mini" data-nt="copy1">نسخ</button><button type="button" class="mini nt-del" data-nt="del1">حذف</button></span></div></div>'; }
  function stamp(ts){ if(!ts) return ''; const d=new Date(ts),p=n=>String(n).padStart(2,'0'); return d.getFullYear()+'-'+p(d.getMonth()+1)+'-'+p(d.getDate())+' '+p(d.getHours())+':'+p(d.getMinutes()); }
  function setNote(ei,text){
    const k=keyOf(ei); text=String(text||'').replace(/\s+$/,''); const old=store.notes[k];
    if(!text.trim()){ if(old){ delete store.notes[k]; save(); changed(); } return; }
    store.notes[k]=Object.assign(snapOf(ei),{t:text,ts:Date.now(),c0:old&&old.c0?old.c0:Date.now(),done:!!(old&&old.done&&old.t===text)});
    save(); changed(); }
  function cardOf(ei){ const bar=document.querySelector('.nt-bar[data-ei="'+ei+'"]'); return bar?{bar,ed:bar.nextElementSibling}:null; }
  function syncCard(ei){ const c=cardOf(ei); if(!c) return; c.bar.innerHTML=barInner(ei); const nt=getNote(ei); const st=c.ed&&c.ed.querySelector('.nt-st'); if(st&&nt) st.textContent=stamp(nt.ts)+' · محفوظة على هذا الجهاز'; }
  function openEditor(ei,focus){ const c=cardOf(ei); if(!c||!c.ed) return; c.ed.hidden=false; const ta=c.ed.querySelector('textarea'); if(ta&&focus&&!matchMedia('(pointer:coarse)').matches){ ta.focus(); } }

  document.addEventListener('click',ev=>{
    const b=ev.target.closest?ev.target.closest('[data-nt]'):null; if(!b) return; const a=b.dataset.nt; const host=b.closest('[data-ei]'); const ei=host?+host.dataset.ei:-1;
    ev.preventDefault();
    if(a==='hide'&&ei>=0){ const mem=membersOf(ei),on=!mem.every(i=>userHidden.has(i)); hideSet(mem,on); toast(on?'أُخفي العنصر — «إظهار المخفية» في الشريط العلوي أو مفتاح Shift+H لإعادته':'أُظهر العنصر',2800); }
    else if(a==='hidetype'&&ei>=0){ const tl=typeIdx.get(M.els[ei].t)||[ei],on=!tl.every(i=>userHidden.has(i)); hideSet(tl,on); toast(on?'أُخفي كل عناصر النوع ('+tl.length+')':'أُظهر كل عناصر النوع ('+tl.length+')',2800); }
    else if(a==='note'&&ei>=0){ const c=cardOf(ei); if(!c) return; const open=c.ed.hidden; c.ed.hidden=!open; if(open){ const ta=c.ed.querySelector('textarea'); if(ta&&!matchMedia('(pointer:coarse)').matches) ta.focus(); } }
    else if(a==='copy1'&&ei>=0){ flush(); const n=getNote(ei); if(!n){ toast('لا ملاحظة لهذا العنصر بعد'); return; } copyOut(textOf([Object.assign({k:keyOf(ei)},n)],false),'نُسخت الملاحظة'); }
    else if(a==='del1'&&ei>=0){ if(b.dataset.arm!=='1'){ b.dataset.arm='1'; b.textContent='تأكيد الحذف'; setTimeout(()=>{ b.dataset.arm='0'; b.textContent='حذف'; },3000); return; }
      pend=null; clearTimeout(pendT); const c=cardOf(ei); if(c&&c.ed){ c.ed.querySelector('textarea').value=''; } setNote(ei,''); b.dataset.arm='0'; b.textContent='حذف'; toast('حُذفت الملاحظة'); }
    else if(a==='go'){ focusKey(b.dataset.k); }
    else if(a==='done'){ const n=store.notes[b.dataset.k]; if(n){ n.done=!n.done; save(); changed(); } }
    else if(a==='delk'){ if(b.dataset.arm!=='1'){ b.dataset.arm='1'; b.textContent='تأكيد'; setTimeout(()=>{ b.dataset.arm='0'; b.textContent='حذف'; },3000); return; } delete store.notes[b.dataset.k]; save(); changed(); }
    else if(a==='unhide'){ const i=+b.dataset.i; hideSet(membersOf(i),false); }
    else if(a==='unhideAll'){ unhideAll(); }
    else if(a==='copyAll'){ flush(); copyOut(textOf(listNotes(),true),'نُسخت الملاحظات — الصقها في المحادثة'); }
    else if(a==='share'){ flush(); const t=textOf(listNotes(),true); try{ navigator.share({title:'ملاحظات نموذج C4',text:t}).catch(()=>{}); }catch(e){ copyOut(t,'نُسخت الملاحظات'); } }
    else if(a==='dl'){ flush(); download(); }
    else if(a==='pins'){ pinsOn=!pinsOn; rebuildPins(); renderPanel(); }
    else if(a==='clearAll'){ if(b.dataset.arm!=='1'){ b.dataset.arm='1'; b.textContent='اضغط مرة أخرى لمسح كل الملاحظات'; setTimeout(()=>{ b.dataset.arm='0'; b.textContent='مسح كل الملاحظات'; },3500); return; } store.notes={}; store.general=''; save(); changed(); toast('مُسحت كل الملاحظات'); }
  });
  document.addEventListener('input',ev=>{
    const t=ev.target; if(!t||!t.classList) return;
    if(t.classList.contains('nt-gen')){ store.general=t.value; save(); updateBadge(); return; }
    if(!t.classList.contains('nt-ta')) return; const host=t.closest('[data-ei]'); if(!host) return; const ei=+host.dataset.ei; pend={ei,text:t.value}; clearTimeout(pendT); pendT=setTimeout(flush,350);
    const st=host.querySelector('.nt-st'); if(st) st.textContent='يُحفظ…'; });
  document.addEventListener('focusout',ev=>{ if(ev.target&&ev.target.classList&&ev.target.classList.contains('nt-ta')) flush(); });
  window.addEventListener('keydown',ev=>{
    if(ev.ctrlKey||ev.metaKey||ev.altKey||ev.code!=='KeyH') return; const t=ev.target;
    if(t&&((t.tagName==='INPUT'&&t.type!=='range'&&t.type!=='checkbox')||t.tagName==='TEXTAREA'||t.tagName==='SELECT'||t.isContentEditable)) return;
    ev.preventDefault();
    if(ev.shiftKey){ unhideAll(); return; }
    const S=sel(); if(S.idx<0){ toast('حدّد عنصرًا أولًا ثم اضغط H لإخفائه'); return; }
    const mem=membersOf(S.idx),on=!mem.every(i=>userHidden.has(i)); hideSet(mem,on); toast(on?'أُخفي العنصر — Shift+H لإظهار كل المخفية':'أُظهر العنصر',2400); });

  /* ---------------- the list, export ---------------- */
  function listNotes(){ return Object.keys(store.notes).map(k=>Object.assign({k},store.notes[k])).sort((a,b)=>(a.done?1:0)-(b.done?1:0)||(a.c0||a.ts||0)-(b.c0||b.ts||0)); }
  function hiddenList(){ const out=[]; userHidden.forEach(ei=>out.push({ei,id:M.els[ei].id,nm:typeName(ei),lv:M.els[ei].l})); return out; }
  const VER=()=>{ const v=$('ver'); return v?v.textContent:''; };
  function posTxt(n){ return n.p?('X '+Math.round(n.p[0]*100)+' · Y '+Math.round(-n.p[2]*100)+' سم · المنسوب '+n.p[1].toFixed(2)+' م'):''; }
  function textOf(L,full){
    const open=L.filter(n=>!n.done).length,H=full?hiddenList():[]; const out=[];
    if(full){ out.push('ملاحظات المالك على نموذج C4 (RD09) — النسخة '+VER()+' — '+stamp(Date.now())); out.push('عدد الملاحظات: '+L.length+' (مفتوحة '+open+'، منفّذة '+(L.length-open)+') · عناصر مخفية: '+H.length);
      if(store.general.trim()){ out.push('','— ملاحظة عامة —',store.general.trim()); } }
    L.forEach((n,i)=>{ out.push('',(i+1)+') '+n.nm+(n.done?' [منفّذة]':''),'   المعرّف: '+n.id+(n.n>1?' (مجموعة من '+n.n+' عنصر)':''),'   الموضع: '+[n.lvn,n.un,posTxt(n)].filter(Boolean).join(' · '),'   الحالة في المجسم: '+(hiddenId(n.id)?'مخفي':'ظاهر'),'   الملاحظة: '+String(n.t).replace(/\n/g,'\n      ')); });
    if(H.length){ out.push('','— العناصر المخفية —'); H.forEach(h=>out.push('• '+h.nm+' — '+h.id+' — '+(LVL[h.lv]?LVL[h.lv].name:h.lv))); }
    return out.join('\n').replace(/^\n/,''); }
  function copyOut(t,okMsg){
    const done=ok=>{ if(ok) toast(okMsg,2600); else manual(t); };
    if(navigator.clipboard&&window.isSecureContext){ navigator.clipboard.writeText(t).then(()=>done(true),()=>done(fallbackCopy(t))); } else done(fallbackCopy(t)); }
  function fallbackCopy(t){ try{ const ta=document.createElement('textarea'); ta.value=t; ta.setAttribute('readonly',''); ta.style.cssText='position:fixed;top:0;left:0;opacity:0'; document.body.appendChild(ta); ta.select(); ta.setSelectionRange(0,t.length); const ok=document.execCommand('copy'); document.body.removeChild(ta); return ok; }catch(e){ return false; } }
  function manual(t){ openSec('pNotes',{scroll:true}); const b=$('notesBox'); if(!b) return; let m=b.querySelector('.nt-man'); if(!m){ m=document.createElement('div'); m.className='nt-man'; b.insertBefore(m,b.firstChild); }
    m.innerHTML='<div class="muted">تعذّر النسخ التلقائي في هذا المتصفح — حدّد النص يدويًا وانسخه:</div><textarea readonly rows="8" dir="auto"></textarea>'; const ta=m.querySelector('textarea'); ta.value=t; ta.focus(); ta.select(); }
  function download(){
    const L=listNotes(),o={app:'RD9-C4',version:VER(),exportedAt:new Date().toISOString(),general:store.general,notes:L.map(n=>({id:n.id,key:n.k,name:n.nm,level:n.lvn,unit:n.un,members:n.n,xy_cm:n.p?[Math.round(n.p[0]*100),Math.round(-n.p[2]*100)]:null,elevation_m:n.p?n.p[1]:null,text:n.t,done:!!n.done,hidden:hiddenId(n.id),created:n.c0?new Date(n.c0).toISOString():null})),hidden:hiddenList().map(h=>h.id)};
    const blob=new Blob([JSON.stringify(o,null,1)],{type:'application/json'}),a=document.createElement('a'),d=new Date(),p=n=>String(n).padStart(2,'0');
    a.href=URL.createObjectURL(blob); a.download='c4-notes-'+d.getFullYear()+p(d.getMonth()+1)+p(d.getDate())+'-'+p(d.getHours())+p(d.getMinutes())+'.json'; document.body.appendChild(a); a.click(); setTimeout(()=>{ URL.revokeObjectURL(a.href); a.remove(); },500); toast('نُزّل ملف الملاحظات'); }

  /* ---------------- panel ---------------- */
  function renderPanel(){
    const box=$('notesBox'); if(!box) return; const L=listNotes(),H=hiddenList(); let h='';
    h+='<div class="nt-sum"><b>'+L.length+'</b> ملاحظة · <b>'+H.length+'</b> عنصر مخفي</div>';
    h+='<p class="muted nt-how">حدّد أي عنصر في المجسم ثم «✎ ملاحظتي» لتكتب ما تريد تنفيذه عليه، أو «إخفاء العنصر» لإخفائه. تُحفظ على هذا الجهاز وهذا المتصفح فقط؛ اضغط «نسخ كل الملاحظات» والصقها لي في المحادثة.'+(canSave?'':' <b style="color:#cf222e">تنبيه: الحفظ على هذا المتصفح غير متاح (وضع خاص؟) — انسخ ملاحظاتك قبل الإغلاق.</b>')+'</p>';
    h+='<div class="nt-tools"><button type="button" class="nt-pri" data-nt="copyAll">نسخ كل الملاحظات</button>'+(navigator.share?'<button type="button" data-nt="share">مشاركة…</button>':'')+'<button type="button" data-nt="dl">تنزيل (JSON)</button><button type="button" class="'+(pinsOn?'on':'')+'" data-nt="pins" aria-pressed="'+(pinsOn?'true':'false')+'">الدبابيس: '+(pinsOn?'ظاهرة':'مخفية')+'</button></div>';
    h+='<div class="is-sh">ملاحظة عامة (غير مرتبطة بعنصر)</div><textarea class="nt-ta nt-gen" dir="auto" rows="3" maxlength="6000" placeholder="أي توجيه عام للتعديلات القادمة…" aria-label="ملاحظة عامة">'+esc(store.general)+'</textarea>';
    h+='<div class="is-sh">ملاحظات العناصر ('+L.length+')</div>';
    if(!L.length) h+='<div class="muted">لا ملاحظات بعد.</div>';
    L.forEach(n=>{ const ei=idIdx.get(n.id),gone=ei===undefined,hid=!gone&&hiddenId(n.id);
      h+='<div class="nt-card'+(n.done?' done':'')+'"><div class="nt-ct"><button type="button" class="nt-go" data-nt="go" data-k="'+esc(n.k)+'" title="الانتقال إلى العنصر"><b>'+esc(n.nm)+'</b></button>'+(hid?'<span class="nt-chip warn">مخفي</span>':'')+(gone?'<span class="nt-chip warn">غير موجود في هذه النسخة</span>':'')+'</div>'
        +'<div class="nt-cs"><code>'+esc(n.id)+'</code><span>'+esc(n.lvn||'')+'</span>'+(n.un?'<span>'+esc(n.un)+'</span>':'')+'</div>'
        +'<div class="nt-tx">'+esc(n.t)+'</div>'
        +'<div class="nt-cb"><label class="nt-chk"><input type="checkbox" data-nt="done" data-k="'+esc(n.k)+'"'+(n.done?' checked':'')+'> تمّ التنفيذ</label><button type="button" class="mini nt-del" data-nt="delk" data-k="'+esc(n.k)+'">حذف</button></div></div>'; });
    h+='<div class="is-sh">العناصر المخفية ('+H.length+')</div>';
    if(!H.length) h+='<div class="muted">لا عناصر مخفية.</div>';
    else { H.slice(0,200).forEach(x=>{ h+='<div class="nt-hr"><span><b>'+esc(x.nm)+'</b> <code>'+esc(x.id)+'</code> <span class="muted">'+esc(LVL[x.lv]?LVL[x.lv].name:x.lv)+'</span></span><button type="button" class="mini" data-nt="unhide" data-i="'+x.ei+'">إظهار</button></div>'; });
      if(H.length>200) h+='<div class="muted">… و'+(H.length-200)+' غيرها</div>'; h+='<div class="nt-tools"><button type="button" class="nt-pri" data-nt="unhideAll">إظهار الكل ('+H.length+')</button></div>'; }
    if(L.length||store.general.trim()) h+='<div class="nt-foot"><button type="button" class="nt-del" data-nt="clearAll">مسح كل الملاحظات</button></div>';
    const keepMan=box.querySelector('.nt-man'); box.innerHTML=h; if(keepMan) box.insertBefore(keepMan,box.firstChild); }
  function updateBadge(){ const b=$('accN_pNotes'); if(b){ const n=Object.keys(store.notes).length+(store.general.trim()?1:0); b.textContent=(n||userHidden.size)?(n+(userHidden.size?' · '+userHidden.size+' مخفي':'')):''; } }
  /* toolbar button: always visible while something is hidden */
  const bar=$('bar'),more=$('btnMore'),ub=document.createElement('button'); ub.type='button'; ub.id='btnUnhide'; ub.hidden=true; if(bar) bar.insertBefore(ub,more||null); ub.onclick=unhideAll;
  function syncUnhide(){ const n=userHidden.size; ub.hidden=!n; ub.textContent='إظهار المخفية ('+n+')'; }
  function focusKey(k){
    const n=store.notes[k]; if(!n) return; const ei=idIdx.get(n.id);
    if(ei!==undefined){ focusEl(ei); if(userHidden.has(ei)) toast('هذا العنصر مخفي — افتح «إظهار العنصر» في بطاقته',3000); setTimeout(()=>openEditor(ei,true),90); }
    else if(n.p){ flyTo(new THREE.Vector3(n.p[0]-2,n.p[1]+2.4,n.p[2]+4),new THREE.Vector3(n.p[0],n.p[1],n.p[2])); toast('هذا العنصر غير موجود في هذه النسخة من النموذج — عُرض موضعه المحفوظ',3200); } }

  /* ---------------- 3-D pins ---------------- */
  const pinG=new THREE.Group(); scene.add(pinG); let pinsOn=true,pinObj=null,pinRefs=[],lvSig='';
  const pinTex=(()=>{ const cv=document.createElement('canvas'); cv.width=cv.height=64; const g=cv.getContext('2d'); g.lineJoin='round'; g.beginPath();
    g.moveTo(17,8); g.lineTo(47,8); g.quadraticCurveTo(57,8,57,18); g.lineTo(57,35); g.quadraticCurveTo(57,45,47,45); g.lineTo(32,45); g.lineTo(20,58); g.lineTo(22,45); g.lineTo(17,45); g.quadraticCurveTo(7,45,7,35); g.lineTo(7,18); g.quadraticCurveTo(7,8,17,8); g.closePath();
    g.lineWidth=8; g.strokeStyle='#ffffff'; g.stroke(); g.fillStyle='#1f6feb'; g.fill(); g.lineWidth=2.6; g.strokeStyle='#0b3d91'; g.stroke();
    g.strokeStyle='#ffffff'; g.lineWidth=3.4; g.lineCap='round'; [[17,20,47,20],[17,28,47,28],[17,36,35,36]].forEach(l=>{ g.beginPath(); g.moveTo(l[0],l[1]); g.lineTo(l[2],l[3]); g.stroke(); });
    return new THREE.CanvasTexture(cv); })();
  function clearPins(){ if(pinObj){ pinG.remove(pinObj); pinObj.geometry.dispose(); pinObj.material.dispose(); pinObj=null; } pinRefs=[]; }
  function rebuildPins(){
    clearPins(); lvSig=M.levels.map(l=>levelVisible(l.id)?1:0).join(''); if(!pinsOn) { wake(); return; }
    const pts=[]; listNotes().forEach(n=>{ if(!n.p||!levelVisible(n.lv)) return; pts.push({x:n.p[0],y:n.p[1],z:n.p[2],k:n.k}); }); if(!pts.length){ wake(); return; }
    const pos=new Float32Array(pts.length*3); pts.forEach((p,i)=>{ pos[i*3]=p.x; pos[i*3+1]=p.y; pos[i*3+2]=p.z; });
    const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.BufferAttribute(pos,3));
    pinObj=new THREE.Points(g,new THREE.PointsMaterial({map:pinTex,size:26,sizeAttenuation:false,transparent:true,opacity:0.97,depthTest:false,depthWrite:false,alphaTest:0.05})); pinObj.renderOrder=1006; pinObj.frustumCulled=false; pinG.add(pinObj); pinRefs=pts; wake(); }
  function tap(cx,cy){
    if(!pinsOn||!pinRefs.length) return false; const r=renderer.domElement.getBoundingClientRect(),lim=matchMedia('(pointer:coarse)').matches?26:16; let best=null,bd=1e9; const v=new THREE.Vector3();
    for(let i=0;i<pinRefs.length;i++){ const p=pinRefs[i]; v.set(p.x,p.y,p.z).project(camera); if(v.z>1||v.z<-1) continue; const sx=r.left+(v.x+1)/2*r.width,sy=r.top+(1-v.y)/2*r.height-8,d=Math.hypot(sx-cx,sy-cy); if(d<lim&&d<bd){ bd=d; best=p; } }
    if(!best) return false; focusKey(best.k); return true; }
  function frame(){ const sig=M.levels.map(l=>levelVisible(l.id)?1:0).join(''); if(sig!==lvSig) rebuildPins(); }

  let rT=0; function changed(){ syncUnhide(); updateBadge(); rebuildPins(); clearTimeout(rT); rT=setTimeout(renderPanel,60); const S=sel(); if(S.idx>=0) syncCard(S.idx); wake(); }
  restore(); updateBadge(); syncUnhide(); rebuildPins(); renderPanel();
  return {infoHTML,tap,frame,hideSet,unhideAll,flush,openEditor,focusKey,exportText:()=>textOf(listNotes(),true),
    get count(){ return Object.keys(store.notes).length; }, get hiddenCount(){ return userHidden.size; }, get pins(){ return pinRefs.length; }, get canSave(){ return canSave; },
    state(){ return {notes:Object.keys(store.notes).length,hidden:userHidden.size,pins:pinRefs.length,general:store.general.length,canSave}; }};
}
window.initNotes=initNotes;
})();
