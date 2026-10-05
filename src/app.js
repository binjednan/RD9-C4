/* ===== C4 BIM viewer app ===== */
const M=window.__MODEL__;
const $=id=>document.getElementById(id);
const LVL={}; M.levels.forEach((l,i)=>{l.idx=i;LVL[l.id]=l;});
const CATS={}; M.layers.forEach(L=>L.subs.forEach(s=>{CATS[s[0]]={id:s[0],name:s[1],layer:L.id,color:L.color};}));
const LAYER={}; M.layers.forEach(L=>LAYER[L.id]=L);
const MATS=M.mats; const TYPES=M.types||{};
const matIndex={}; Object.keys(MATS).forEach((k,i)=>matIndex[k]=i);
const UNITS=M.units||[]; const unitIndex={}; UNITS.forEach((u,i)=>unitIndex[u.id]=i);
const ATTR={thk_cm:'السماكة (سم)',w_cm:'العرض (سم)',h_cm:'الارتفاع (سم)',d_cm:'العمق (سم)',dia_cm:'القطر (سم)',len_m:'الطول (م)',kind:'النوع',loc:'الموقع',side:'الجهة',room:'الغرفة',wall_cm:'سماكة الجدار (سم)',step:'رقم الدرجة',rise_cm:'ارتفاع الدرجة (سم)',tread_cm:'عرض الدرجة (سم)',flight:'الجناح',stops:'المحطات',cab_cm:'مقصورة (سم)',h_m:'الارتفاع (م)',top:'منسوب القمة',part:'الجزء',assumed_h:'ارتفاع السقف المستعار (م) — افتراضي'};
const CONF={doc:['مستخرج من المستندات','#1a7f37'],derived:['مشتق/محسوب من المستندات','#9a6700'],assumed:['افتراض هندسي — يحتاج تأكيد','#cf222e']};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

/* ---------- renderer / scene ---------- */
const wrap=$('view');
const renderer=new THREE.WebGLRenderer({antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(Math.min(window.devicePixelRatio,window.innerWidth<860?1.5:2)); renderer.localClippingEnabled=true;
wrap.appendChild(renderer.domElement);
const scene=new THREE.Scene(); scene.background=new THREE.Color(0xe9edf2);
const camera=new THREE.PerspectiveCamera(42,1,0.3,900);
const HOME={pos:new THREE.Vector3(-34,36,26),tgt:new THREE.Vector3(18,9,-17)};
function homeView(){const asp=wrap.clientWidth/Math.max(1,wrap.clientHeight);const k=asp<1?Math.min(2.1,Math.pow(1/asp,0.9)):1;const dir=HOME.pos.clone().sub(HOME.tgt).multiplyScalar(k);return {pos:HOME.tgt.clone().add(dir),tgt:HOME.tgt.clone()};}
camera.position.copy(homeView().pos);
const controls=new THREE.OrbitControls(camera,renderer.domElement);
controls.target.copy(HOME.tgt); controls.enableDamping=true; controls.dampingFactor=0.12; controls.maxPolarAngle=Math.PI*0.499;
scene.add(new THREE.HemisphereLight(0xffffff,0x8a8f98,0.85));
const sun=new THREE.DirectionalLight(0xffffff,0.75); sun.position.set(-40,70,30); scene.add(sun);
const sun2=new THREE.DirectionalLight(0xffffff,0.25); sun2.position.set(50,30,-40); scene.add(sun2);
const clipY=new THREE.Plane(new THREE.Vector3(0,-1,0),1000);
const clipX=new THREE.Plane(new THREE.Vector3(-1,0,0),1000);
renderer.clippingPlanes=[clipY,clipX];

/* ---------- shader patch: unit isolation ---------- */
const U={iso:{value:-1},maskOn:{value:0},mask:{value:null},maskBox:{value:new THREE.Vector4(0,-21,34,23)}};
function patch(mat){
  mat.onBeforeCompile=(sh)=>{
    sh.uniforms.uIso=U.iso; sh.uniforms.uMaskOn=U.maskOn; sh.uniforms.uMask=U.mask; sh.uniforms.uMaskBox=U.maskBox;
    sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\nattribute vec2 aUnit; attribute float aClip; varying vec2 vUnit; varying float vClip; varying vec3 vWPos;')
      .replace('#include <begin_vertex>','#include <begin_vertex>\nvUnit=aUnit; vClip=aClip; vWPos=(modelMatrix*vec4(transformed,1.0)).xyz;');
    sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\nvarying vec2 vUnit; varying float vClip; varying vec3 vWPos; uniform float uIso; uniform float uMaskOn; uniform sampler2D uMask; uniform vec4 uMaskBox;')
      .replace('void main() {','void main() {\n if(uIso>-0.5 && vClip<0.5 && abs(vUnit.x-uIso)>0.5 && abs(vUnit.y-uIso)>0.5) discard;\n if(uIso>-0.5 && vClip>0.5){ vec2 uv=(vWPos.xz-uMaskBox.xy)/uMaskBox.zw; if(uv.x<0.||uv.x>1.||uv.y<0.||uv.y>1.||texture2D(uMask,uv).r<0.5) discard; }');
  };
  mat.customProgramCacheKey=()=> 'bimpatch';
  return mat;
}

/* ---------- build merged geometry ---------- */
const groups={}; const elRange=new Array(M.els.length); const elBB=new Float32Array(M.els.length*6);
const grpMap={}; // grp -> [element idx]
function gkey(e){return e.c+'|'+e.l+'|'+(e.m||'conc');}
function uidx(u){return (u==null)?-1:(unitIndex[u]!==undefined?unitIndex[u]:-1);}
function buildAll(){
  const t0=performance.now();
  M.els.forEach((e,ei)=>{
    const k=gkey(e); let G=groups[k]; if(!G){G=groups[k]={g:new Group(k,(e.c==='S.slab'||e.c==='S.beam')?1:0),cat:e.c,lvl:e.l,mat:e.m||'conc',clip:(e.c==='S.slab'||e.c==='S.beam')};}
    const g=G.g; const u1=uidx(e.u), u2=uidx(e.u2); const mi=(matIndex[e.m]!==undefined?matIndex[e.m]:0);
    const n0=g.n; const geo=e.g;
    switch(geo[0]){
      case 'p': prism(g,geo[1],geo[4]||null,geo[2],geo[3],u1,u2,mi); break;
      case 'r': rectPrism(g,geo[1],geo[2],geo[3],geo[4],geo[5],geo[6],u1,u2,mi); break;
      case 'cyl': cylinder(g,geo[1],geo[2],geo[3],geo[4],geo[5],u1,u2,mi); break;
      case 'b': orientedBox(g,geo[1],geo[2],geo[3],geo[4],geo[5],geo[6],geo[7],u1,u2,mi); break;
      case 'd': {const pts=geo[1]; for(let i=0;i<pts.length-1;i++) ductSeg(g,pts[i],pts[i+1],geo[2],geo[3],u1,u2,mi); break;}
      case 't': {const pts=geo[1]; for(let i=0;i<pts.length-1;i++) tubeSeg(g,pts[i],pts[i+1],geo[2]/2,u1,u2,mi); break;}
      case 'rs': rampStrip(g,geo[1],geo[2],geo[3],u1,u2,mi); break;
      default: break;
    }
    elRange[ei]={gk:k,start:n0,count:g.n-n0};
    // bbox
    let mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9];
    for(let i=n0*9;i<g.n*9;i+=3){const x=g.pos[i],y=g.pos[i+1],z=g.pos[i+2]; if(x<mn[0])mn[0]=x;if(y<mn[1])mn[1]=y;if(z<mn[2])mn[2]=z;if(x>mx[0])mx[0]=x;if(y>mx[1])mx[1]=y;if(z>mx[2])mx[2]=z;}
    elBB.set([mn[0],mn[1],mn[2],mx[0],mx[1],mx[2]],ei*6);
    if(e.grp){(grpMap[e.grp]=grpMap[e.grp]||[]).push(ei);}
  });
  for(const k in groups){
    const G=groups[k]; const g=G.g; if(!g.n) continue;
    const bg=new THREE.BufferGeometry();
    bg.setAttribute('position',new THREE.Float32BufferAttribute(g.pos,3));
    bg.setAttribute('normal',new THREE.Float32BufferAttribute(g.nrm,3));
    bg.setAttribute('aUnit',new THREE.Float32BufferAttribute(g.unit,2)); bg.setAttribute('aClip',new THREE.Float32BufferAttribute(g.clip,1));
    bg.computeBoundingSphere();
    const m=MATS[G.mat]||{color:'#bbbbbb'};
    const op=(m.opacity!==undefined)?m.opacity:1;
    const mat=patch(new THREE.MeshStandardMaterial({color:new THREE.Color(m.color),roughness:op<1?0.15:0.9,metalness:op<1?0.2:0.0,side:THREE.DoubleSide,transparent:op<1,opacity:op,depthWrite:op>=1,polygonOffset:true,polygonOffsetFactor:1,polygonOffsetUnits:1}));
    mat.userData.baseOpacity=op; G.matBase=mat;
    const mesh=new THREE.Mesh(bg,mat); mesh.userData={cat:G.cat,lvl:G.lvl,key:k}; mesh.frustumCulled=false; G.mesh=mesh; scene.add(mesh);
    g.pos=g.nrm=g.unit=g.mat=g.clip=null; G.posArr=bg.attributes.position.array;
  }
  console.log('built',Object.keys(groups).length,'groups in',Math.round(performance.now()-t0),'ms');
}
buildAll();

/* ---------- ghost envelope (shown while a unit is isolated) ---------- */
const ghost=new THREE.Group(); ghost.visible=false; scene.add(ghost);
(function(){
  const gm=new THREE.MeshBasicMaterial({color:0x6a7f95,transparent:true,opacity:0.10,depthWrite:false,side:THREE.DoubleSide});
  const lm=new THREE.LineBasicMaterial({color:0x5b6f85,transparent:true,opacity:0.55});
  (M.env||[]).forEach(r=>{
    const w=(r[2]-r[0])*S,d=(r[3]-r[1])*S,h=r[5]-r[4];
    const b=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),gm); b.position.set((r[0]+r[2])/2*S,(r[4]+r[5])/2,-(r[1]+r[3])/2*S); ghost.add(b);
    const e=new THREE.LineSegments(new THREE.EdgesGeometry(b.geometry),lm); e.position.copy(b.position); ghost.add(e);
  });
})();

/* ---------- visibility ---------- */
const catVis={}; Object.keys(CATS).forEach(c=>catVis[c]=true);
const lvlVis={}; M.levels.forEach(l=>lvlVis[l.id]=true);
let structOpacity=1, isoUnit=null, explode=0;
function groupVisible(G){ if(isoUnit!==null){ if(G.clip) return catVis[G.cat]&&G.lvl===UNITS[isoUnit].level; return catVis[G.cat]; } return catVis[G.cat]&&lvlVis[G.lvl];}
function applyVis(){
  for(const k in groups){const G=groups[k]; if(!G.mesh) continue; G.mesh.visible=groupVisible(G);
    if(G.cat[0]==='S'){const o=structOpacity*(G.matBase.userData.baseOpacity||1); G.matBase.opacity=o; G.matBase.transparent=o<0.999; G.matBase.depthWrite=o>=0.999; G.matBase.needsUpdate=true;}
    const lv=LVL[G.lvl]; G.mesh.position.y=explode*(lv?lv.idx:0);
  }
  ghost.children.forEach(c=>{});
}
function resize(){const w=wrap.clientWidth,h=wrap.clientHeight;renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}
window.addEventListener('resize',resize); resize();

/* ---------- picking ---------- */
const ray=new THREE.Raycaster(); const mouse=new THREE.Vector2();
function elVisible(ei){
  const e=M.els[ei]; const G=groups[elRange[ei].gk]; if(!G||!G.mesh||!G.mesh.visible) return false;
  if(isoUnit!==null){const a=uidx(e.u),b=uidx(e.u2); if(a!==isoUnit&&b!==isoUnit) return false;}
  return true;
}
function rayAABB(o,d,bb,off){let tmin=0,tmax=1e9;for(let i=0;i<3;i++){const lo=bb[i]+(i===1?off:0),hi=bb[i+3]+(i===1?off:0);const oi=o[i],di=d[i];if(Math.abs(di)<1e-9){if(oi<lo||oi>hi)return -1;}else{let t1=(lo-oi)/di,t2=(hi-oi)/di;if(t1>t2){const t=t1;t1=t2;t2=t;}if(t1>tmin)tmin=t1;if(t2<tmax)tmax=t2;if(tmin>tmax)return -1;}}return tmin;}
function rayTri(o,d,a,b,c){const e1=[b[0]-a[0],b[1]-a[1],b[2]-a[2]],e2=[c[0]-a[0],c[1]-a[1],c[2]-a[2]];const p=[d[1]*e2[2]-d[2]*e2[1],d[2]*e2[0]-d[0]*e2[2],d[0]*e2[1]-d[1]*e2[0]];const det=e1[0]*p[0]+e1[1]*p[1]+e1[2]*p[2];if(Math.abs(det)<1e-12)return -1;const iv=1/det;const t=[o[0]-a[0],o[1]-a[1],o[2]-a[2]];const u=(t[0]*p[0]+t[1]*p[1]+t[2]*p[2])*iv;if(u<0||u>1)return -1;const q=[t[1]*e1[2]-t[2]*e1[1],t[2]*e1[0]-t[0]*e1[2],t[0]*e1[1]-t[1]*e1[0]];const v=(d[0]*q[0]+d[1]*q[1]+d[2]*q[2])*iv;if(v<0||u+v>1)return -1;const tt=(e2[0]*q[0]+e2[1]*q[1]+e2[2]*q[2])*iv;return tt>1e-4?tt:-1;}
function pick(clientX,clientY){
  const r=renderer.domElement.getBoundingClientRect();
  mouse.set(((clientX-r.left)/r.width)*2-1,-((clientY-r.top)/r.height)*2+1);
  ray.setFromCamera(mouse,camera); const o=[ray.ray.origin.x,ray.ray.origin.y,ray.ray.origin.z], d=[ray.ray.direction.x,ray.ray.direction.y,ray.ray.direction.z];
  const cand=[];
  for(let ei=0;ei<M.els.length;ei++){
    if(!elVisible(ei)) continue;
    const lv=LVL[M.els[ei].l]; const off=explode*(lv?lv.idx:0);
    const t=rayAABB(o,d,elBB.subarray(ei*6,ei*6+6),off); if(t>=0) cand.push([t,ei,off]);
  }
  cand.sort((a,b)=>a[0]-b[0]);
  let best=null;
  for(let k=0;k<cand.length&&k<80;k++){
    if(best&&cand[k][0]>best[0]) break;
    const [t0,ei,off]=cand[k]; const rg=elRange[ei]; const G=groups[rg.gk]; const P=G.posArr;
    // clip plane test uses world pos: skip hits above clipY
    for(let tri=rg.start;tri<rg.start+rg.count;tri++){
      const i=tri*9; const a=[P[i],P[i+1]+off,P[i+2]],b=[P[i+3],P[i+4]+off,P[i+5]],c=[P[i+6],P[i+7]+off,P[i+8]];
      const t=rayTri(o,d,a,b,c); if(t>0){const hp=[o[0]+d[0]*t,o[1]+d[1]*t,o[2]+d[2]*t]; if(hp[1]>clipYv||hp[0]>clipXv) continue; if(!best||t<best[0]) best=[t,ei];}
    }
  }
  return best?best[1]:-1;
}
let clipYv=1000, clipXv=1000;

/* ---------- selection highlight ---------- */
let hlMesh=null, hlLines=null, selIdx=-1, selSet=[];
function clearHL(){ if(hlMesh){scene.remove(hlMesh);hlMesh.geometry.dispose();hlMesh=null;} if(hlLines){scene.remove(hlLines);hlLines.geometry.dispose();hlLines=null;} }
function highlight(idxs,color=0xffb000){
  clearHL(); if(!idxs.length) return;
  const pos=[]; 
  idxs.forEach(ei=>{const rg=elRange[ei]; const G=groups[rg.gk]; const lv=LVL[M.els[ei].l]; const off=explode*(lv?lv.idx:0); const P=G.posArr; for(let i=rg.start*9;i<(rg.start+rg.count)*9;i+=3){pos.push(P[i],P[i+1]+off,P[i+2]);}});
  const bg=new THREE.BufferGeometry(); bg.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
  hlMesh=new THREE.Mesh(bg,new THREE.MeshBasicMaterial({color,transparent:true,opacity:0.8,depthTest:false,side:THREE.DoubleSide})); hlMesh.renderOrder=999; scene.add(hlMesh);
  const eg=new THREE.EdgesGeometry(bg,35); hlLines=new THREE.LineSegments(eg,new THREE.LineBasicMaterial({color:0xb35c00,depthTest:false})); hlLines.renderOrder=1000; scene.add(hlLines);
}
function bboxOf(idxs){const mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9];idxs.forEach(ei=>{for(let i=0;i<3;i++){mn[i]=Math.min(mn[i],elBB[ei*6+i]);mx[i]=Math.max(mx[i],elBB[ei*6+3+i]);}});return {mn,mx,c:[(mn[0]+mx[0])/2,(mn[1]+mx[1])/2,(mn[2]+mx[2])/2],r:Math.hypot(mx[0]-mn[0],mx[1]-mn[1],mx[2]-mn[2])/2};}
/* ---------- camera fly ---------- */
let fly=null;
function flyTo(pos,tgt,ms=900){fly={p0:camera.position.clone(),t0:controls.target.clone(),p1:pos,t1:tgt,s:performance.now(),d:ms};}
function flyToBox(b,dir=[-0.55,0.6,0.55]){const r=Math.max(b.r,1.2)*2.6; const t=new THREE.Vector3(b.c[0],b.c[1],b.c[2]); const p=t.clone().add(new THREE.Vector3(dir[0],dir[1],dir[2]).normalize().multiplyScalar(r)); flyTo(p,t);}

/* ---------- info panel ---------- */
function row(k,v){return `<tr><th>${esc(k)}</th><td>${v}</td></tr>`;}
function showInfo(ei){
  const e=M.els[ei]; const T=TYPES[e.t]||{}; const c=CATS[e.c]; const lv=LVL[e.l];
  const unit=e.u?UNITS[unitIndex[e.u]]:null;
  let h=`<div class=ih><b>${esc(T.n||c.name)}</b><button id=icl>×</button></div>`;
  h+=`<div class=tags><span style="background:${c.color}22;color:${c.color}">${esc(LAYER[c.layer].name)}</span><span>${esc(c.name)}</span></div>`;
  h+=`<h4>الهوية</h4><table>`+row('الرمز التعريفي (ID)',`<code>${esc(e.id)}</code>`)+(e.mark?row('الوسم / Tag',`<code>${esc(e.mark)}</code>`):'')+row('الطابق',esc(lv.name)+` (${lv.ffl>0?'+':''}${lv.ffl.toFixed(2)})`)+(unit?row('الوحدة',esc(unit.name)):'')+`</table>`;
  const sp=(T.sp||[]).slice(); const at=e.a||{};
  const extra=[]; for(const k in at){ if(k==='fin'||at[k]===null||at[k]==='') continue; extra.push([ATTR[k]||k,Array.isArray(at[k])?at[k].join('، '):at[k]]); }
  if(at.fin&&at.fin.length) extra.push(['رموز التشطيب (A500)',at.fin.join(' + ')]);
  if(sp.length||extra.length){h+=`<h4>المواصفات الفنية</h4><table>`+sp.map(r=>row(r[0],esc(r[1]))).join('')+extra.map(r=>row(r[0],esc(r[1]))).join('')+`</table>`;}
  const mt=(T.mt||[]);
  h+=`<h4>الصيانة والتشغيل</h4><table>`+(mt.length?mt.map(r=>row(r[0],esc(r[1]))).join(''):row('البيانات','غير مذكورة في المستندات المرفقة'))+`</table>`;
  if(T.adv&&T.adv.length) h+=`<div class=adv><b>إرشاد عام — غير مستخرج من المستندات</b><ul>`+T.adv.map(a=>`<li>${esc(a)}</li>`).join('')+`</ul></div>`;
  const cf=CONF[T.cf||'doc']; const srcs=(e.s||[]).map(i=>M.sp[i]).concat(T.sr||[]);
  h+=`<h4>مصدر البيانات</h4><div class=src><span class=cf style="background:${cf[1]}1a;color:${cf[1]}">${cf[0]}</span><ul>`+srcs.map(s=>`<li>${esc(s)}</li>`).join('')+`</ul></div>`;
  const grp=e.grp&&grpMap[e.grp]?grpMap[e.grp].length:0; if(grp>1) h+=`<div class=muted>جزء من مجموعة (${grp} عنصر)</div>`;
  $('info').innerHTML=h; $('info').classList.add('on'); document.body.classList.add('info-open'); document.body.classList.remove('panel-open'); $('icl').onclick=()=>{select(-1);};
}
function select(ei,fit=false){
  selIdx=ei; if(ei<0){clearHL();$('info').classList.remove('on');document.body.classList.remove('info-open');selSet=[];return;}
  const e=M.els[ei]; selSet=(e.grp&&grpMap[e.grp])?grpMap[e.grp]:[ei];
  highlight(selSet); showInfo(ei); if(fit) flyToBox(bboxOf(selSet));
}
let downXY=null;
renderer.domElement.addEventListener('pointerdown',ev=>{downXY=[ev.clientX,ev.clientY];});
renderer.domElement.addEventListener('pointerup',ev=>{ if(!downXY) return; if(Math.hypot(ev.clientX-downXY[0],ev.clientY-downXY[1])>4) return; const ei=pick(ev.clientX,ev.clientY); select(ei); });
renderer.domElement.addEventListener('dblclick',ev=>{const ei=pick(ev.clientX,ev.clientY); if(ei>=0) select(ei,true);});

/* ---------- UI: layers / levels ---------- */
const lp=$('layers');
M.layers.forEach(L=>{
  const box=document.createElement('div'); box.className='lay';
  const head=document.createElement('label'); head.className='lh'; head.innerHTML=`<input type=checkbox checked data-layer="${L.id}"><span class=dot style="background:${L.color}"></span><b>${L.name}</b>`;
  const only=document.createElement('button'); only.textContent='فقط'; only.className='mini'; only.onclick=(ev)=>{ev.preventDefault();M.layers.forEach(L2=>{lp.querySelector(`input[data-layer="${L2.id}"]`).checked=(L2.id===L.id); lp.querySelectorAll(`input[data-cat^="${L2.id}."]`).forEach(i=>{i.checked=(L2.id===L.id);catVis[i.dataset.cat]=(L2.id===L.id);});}); applyVis();};
  head.appendChild(only); box.appendChild(head);
  const subs=document.createElement('div'); subs.className='subs';
  L.subs.forEach(s=>{const n=M.els.filter(e=>e.c===s[0]).length; if(!n) return; const lab=document.createElement('label'); lab.innerHTML=`<input type=checkbox checked data-cat="${s[0]}"> ${s[1]} <i>${n}</i>`; subs.appendChild(lab);});
  box.appendChild(subs); lp.appendChild(box);
});
lp.addEventListener('change',ev=>{const t=ev.target; if(t.dataset.layer){lp.querySelectorAll(`input[data-cat^="${t.dataset.layer}."]`).forEach(i=>{i.checked=t.checked;catVis[i.dataset.cat]=t.checked;});} else if(t.dataset.cat){catVis[t.dataset.cat]=t.checked;} applyVis();});
const lv=$('levels');
M.levels.slice().reverse().forEach(l=>{const lab=document.createElement('label'); lab.innerHTML=`<input type=checkbox checked data-lvl="${l.id}"> ${l.name} <i>${l.ffl>0?'+':''}${l.ffl.toFixed(2)}</i>`; lv.appendChild(lab);});
lv.addEventListener('change',ev=>{const t=ev.target; if(t.dataset.lvl){lvlVis[t.dataset.lvl]=t.checked;applyVis();}});
$('sOpa').addEventListener('input',ev=>{structOpacity=ev.target.value/100;applyVis();});
$('clipY').addEventListener('input',ev=>{const v=+ev.target.value; clipYv=(v>=30)?1000:v; clipY.constant=clipYv; $('clipYV').textContent=(v>=30)?'بدون':v.toFixed(1)+' م';});
$('clipX').addEventListener('input',ev=>{const v=+ev.target.value; clipXv=(v>=46)?1000:v; clipX.constant=clipXv; $('clipXV').textContent=(v>=46)?'بدون':v.toFixed(1)+' م';});
$('expl').addEventListener('input',ev=>{explode=+ev.target.value/10; applyVis(); if(selIdx>=0) highlight(selSet);});
$('btnHome').onclick=()=>{const h=homeView();flyTo(h.pos,h.tgt);};
$('btnAll').onclick=()=>{M.layers.forEach(L=>{lp.querySelector(`input[data-layer="${L.id}"]`).checked=true;lp.querySelectorAll(`input[data-cat^="${L.id}."]`).forEach(i=>{i.checked=true;catVis[i.dataset.cat]=true;});});lv.querySelectorAll('input').forEach(i=>{i.checked=true;lvlVis[i.dataset.lvl]=true;});applyVis();};

/* ---------- units ---------- */
const up=$('units');
(function(){
  const byLvl={}; UNITS.forEach(u=>{(byLvl[u.level]=byLvl[u.level]||[]).push(u);});
  Object.keys(byLvl).sort((a,b)=>LVL[b].idx-LVL[a].idx).forEach(l=>{
    const h=document.createElement('div'); h.className='uh'; h.textContent='الطابق '+LVL[l].name; up.appendChild(h);
    const row=document.createElement('div'); row.className='ur';
    byLvl[l].forEach(u=>{const b=document.createElement('button'); b.className='ub'; b.dataset.u=u.id; b.innerHTML=`<b>${u.name}</b><i>${u.bed!=null?u.bed+' غ.ن · ':''}${u.gross?u.gross+' م²':''}</i>`; b.onclick=()=>isolate(u.id); row.appendChild(b);});
    up.appendChild(row);
  });
})();
function unitElements(uid){const i=unitIndex[uid];const out=[];M.els.forEach((e,ei)=>{if(uidx(e.u)===i||uidx(e.u2)===i) out.push(ei);});return out;}
function makeMask(u){
  const W=34*20,H=23*20; const c=document.createElement('canvas'); c.width=W; c.height=H; const x=c.getContext('2d'); x.fillStyle='#000'; x.fillRect(0,0,W,H); x.fillStyle='#fff';
  (u.rects||[]).forEach(r=>{ // plan cm -> world m: X=x/100, Z=-y/100 ; box origin (0,-21) size (34,23)
    const px0=(r[0]/100-0.25)*20, px1=(r[2]/100+0.25)*20; const pz0=((-r[3]/100-0.25)-(-21))*20, pz1=((-r[1]/100+0.25)-(-21))*20; x.fillRect(px0,pz0,px1-px0,pz1-pz0);});
  const t=new THREE.CanvasTexture(c); t.minFilter=THREE.LinearFilter; t.magFilter=THREE.LinearFilter; return t;
}
let ceilWasOn=true;
function isolate(uid){
  document.body.classList.remove('panel-open'); isoUnit=uidx(uid); U.iso.value=isoUnit; ghost.visible=true; U.mask.value=makeMask(UNITS[isoUnit]); U.maskOn.value=1; ceilWasOn=catVis['A.ceil']; catVis['A.ceil']=false; const cb=document.querySelector('input[data-cat="A.ceil"]'); if(cb) cb.checked=false; applyVis(); $('isoBar').classList.add('on'); const u=UNITS[isoUnit]; $('isoName').textContent=u.name+' — الطابق '+LVL[u.level].name;
  document.querySelectorAll('.ub').forEach(b=>b.classList.toggle('sel',b.dataset.u===uid));
  const idx=unitElements(uid); const b=bboxOf(idx); flyToBox(b,[-0.2,0.9,0.9]); select(-1);
  $('isoCount').textContent=idx.length+' عنصر داخل الوحدة';
}
function exitIso(){isoUnit=null;U.iso.value=-1;U.maskOn.value=0;ghost.visible=false; catVis['A.ceil']=ceilWasOn; const cb=document.querySelector('input[data-cat="A.ceil"]'); if(cb) cb.checked=ceilWasOn; applyVis();$('isoBar').classList.remove('on');document.querySelectorAll('.ub').forEach(b=>b.classList.remove('sel'));{const h=homeView();flyTo(h.pos,h.tgt);}}
$('isoExit').onclick=exitIso;

/* ---------- tabs ---------- */
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));document.querySelectorAll('.pane').forEach(x=>x.classList.remove('on'));t.classList.add('on');$(t.dataset.pane).classList.add('on');});

/* ---------- loop ---------- */
let frames=0,tLast=performance.now();
function loop(){requestAnimationFrame(loop);
  if(fly){const k=Math.min(1,(performance.now()-fly.s)/fly.d);const e=k<0.5?2*k*k:1-Math.pow(-2*k+2,2)/2;camera.position.lerpVectors(fly.p0,fly.p1,e);controls.target.lerpVectors(fly.t0,fly.t1,e);if(k>=1)fly=null;}
  controls.update();renderer.render(scene,camera);frames++;const t=performance.now();if(t-tLast>1000){$('fps').textContent=Math.round(frames*1000/(t-tLast))+' fps';frames=0;tLast=t;}}
loop(); applyVis();
$('fab').onclick=()=>document.body.classList.add('panel-open'); $('panelClose').onclick=()=>document.body.classList.remove('panel-open');
{const L=$('loader'); if(L){L.classList.add('off'); setTimeout(()=>L.remove(),600);} }
$('stat').textContent=M.els.length.toLocaleString('en')+' عنصر';
window.__dbg={scene,camera,controls,groups,renderer,select,isolate,pick,M};
