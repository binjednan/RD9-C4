/* ===== C4 BIM viewer app ===== */
const M=window.__MODEL__;
const $=id=>document.getElementById(id);
const LVL={}; M.levels.forEach((l,i)=>{l.idx=i;LVL[l.id]=l;});
const CATS={}; M.layers.forEach(L=>L.subs.forEach(s=>{CATS[s[0]]={id:s[0],name:s[1],layer:L.id,color:L.color};}));
const LAYER={}; M.layers.forEach(L=>LAYER[L.id]=L);
const MATS=M.mats; const TYPES=M.types||{};
const matIndex={}; Object.keys(MATS).forEach((k,i)=>matIndex[k]=i);
const UNITS=M.units||[]; const unitIndex={}; UNITS.forEach((u,i)=>unitIndex[u.id]=i);
const ATTR={thk_cm:'السماكة (سم)',w_cm:'العرض (سم)',h_cm:'الارتفاع (سم)',d_cm:'العمق (سم)',dia_cm:'القطر (سم)',len_m:'الطول (م)',kind:'النوع',loc:'الموقع',side:'الجهة',room:'الغرفة',wall_cm:'سماكة الجدار (سم)',step:'رقم الدرجة',rise_cm:'ارتفاع الدرجة (سم)',tread_cm:'عرض الدرجة (سم)',flight:'الجناح',stops:'المحطات',cab_cm:'مقصورة (سم)',h_m:'الارتفاع (م)',top:'منسوب القمة',part:'الجزء',assumed_h:'ارتفاع السقف المستعار (م) — افتراضي',
  dia_mm:'القطر (مم)',length_m:'الطول (م)',size_cm:'المقاس (سم)',dia_note:'ملاحظة القطر',size_note:'ملاحظة المقاس',cls:'رمز الفئة (من المفتاح)',match:'درجة مطابقة الرمز',derived_type:'النوع مشتق من المخطط',tag_floor:'الطابق في الوسم',cap_l:'السعة (لتر)',cap_known:'السعة مذكورة في المخطط',mount_note:'ملاحظة التركيب (افتراض)',display_note:'ملاحظة العرض'};
const CONF={doc:['مستخرج من المستندات','#1a7f37'],derived:['مشتق/محسوب من المستندات','#9a6700'],assumed:['افتراض هندسي — يحتاج تأكيد','#cf222e']};
const STAGE_KINDS={furniture:'أثاث',tree:'أشجار',plant:'نباتات',car:'سيارات',person:'أشخاص',shade:'مظلات ظل',play:'ألعاب أطفال',other:'أخرى'};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmtVal=v=>v===true?'نعم':v===false?'لا':Array.isArray(v)?v.join(' '):v;
const normAr=s=>String(s).toLowerCase().replace(/[ً-ْـ]/g,'').replace(/[أإآ]/g,'ا').replace(/ى/g,'ي').replace(/ة/g,'ه');
function stageKind(e){ if(e.stage===true||e.stage===1) return 'other'; if(e.stage) return String(e.stage); if(/\.stage$/.test(e.c)) return 'other'; return null; }
let toastT=0; function toast(msg,ms=3200){const t=$('toast'); t.textContent=msg; t.classList.add('on'); clearTimeout(toastT); toastT=setTimeout(()=>t.classList.remove('on'),ms);}
let awakeUntil=0; function wake(ms=1500){const t=performance.now()+ms; if(t>awakeUntil) awakeUntil=t;}
['pointerdown','pointermove','pointerup','wheel','keydown','keyup','input','change','click','touchstart','touchmove'].forEach(ev=>window.addEventListener(ev,()=>wake(1200),{passive:true,capture:true}));

/* ---------- renderer / scene ---------- */
const wrap=$('view'); const IS_SMALL=window.innerWidth<860; let perfMode=false;
const renderer=new THREE.WebGLRenderer({antialias:true,powerPreference:'high-performance'});
const ratioFor=()=>perfMode?Math.min(window.devicePixelRatio,1)*0.8:Math.min(window.devicePixelRatio,IS_SMALL?1.5:2);
renderer.setPixelRatio(ratioFor()); renderer.localClippingEnabled=true;
wrap.insertBefore(renderer.domElement,wrap.firstChild);
const scene=new THREE.Scene(); scene.background=new THREE.Color(0xe9edf2);
const camera=new THREE.PerspectiveCamera(42,1,0.3,900);
const HOME={pos:new THREE.Vector3(-34,36,26),tgt:new THREE.Vector3(18,9,-17)};
function aspectK(){const asp=wrap.clientWidth/Math.max(1,wrap.clientHeight);return asp<1?Math.min(2.2,Math.pow(1/asp,0.9)):1;}
function homeView(){const dir=HOME.pos.clone().sub(HOME.tgt).multiplyScalar(aspectK());return {pos:HOME.tgt.clone().add(dir),tgt:HOME.tgt.clone()};}
camera.position.copy(homeView().pos);
const controls=new CameraRig(camera,renderer.domElement);
controls.target.copy(HOME.tgt); camera.lookAt(HOME.tgt);
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
    sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\nattribute vec2 aUnit; attribute float aClip; attribute float aHide; varying vec2 vUnit; varying float vClip; varying vec3 vWPos;')
      .replace('#include <begin_vertex>','#include <begin_vertex>\nvUnit=aUnit; vClip=aClip; vWPos=(modelMatrix*vec4(transformed,1.0)).xyz;')
      .replace('#include <project_vertex>','#include <project_vertex>\n if(aHide>0.5) gl_Position=vec4(2.0,2.0,2.0,1.0);');
    sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\nvarying vec2 vUnit; varying float vClip; varying vec3 vWPos; uniform float uIso; uniform float uMaskOn; uniform sampler2D uMask; uniform vec4 uMaskBox;')
      .replace('void main() {','void main() {\n if(uIso>-0.5 && vClip<0.5 && abs(vUnit.x-uIso)>0.5 && abs(vUnit.y-uIso)>0.5) discard;\n if(uIso>-0.5 && vClip>0.5){ vec2 uv=(vWPos.xz-uMaskBox.xy)/uMaskBox.zw; if(uv.x<0.||uv.x>1.||uv.y<0.||uv.y>1.||texture2D(uMask,uv).r<0.5) discard; }');
  };
  mat.customProgramCacheKey=()=> 'bimpatch';
  return mat;
}

/* ---------- build merged geometry ---------- */
const groups={}; const elRange=new Array(M.els.length); const elBB=new Float32Array(M.els.length*6);
const grpMap={}; // grp -> [element idx]
const stageCount={}; let stageTotal=0;
function gkey(e){const st=stageKind(e);return e.c+'|'+e.l+'|'+(e.m||'conc')+(st?'|st:'+st:'')+(e.t==='lift_car'?'|'+e.id:'');}
function uidx(u){return (u==null)?-1:(unitIndex[u]!==undefined?unitIndex[u]:-1);}
function buildAll(){
  const t0=performance.now();
  M.els.forEach((e,ei)=>{
    const k=gkey(e); const st=stageKind(e); let G=groups[k]; if(!G){G=groups[k]={g:new Group(k,(e.c==='S.slab'||e.c==='S.beam')?1:0),cat:e.c,lvl:e.l,mat:e.m||'conc',clip:(e.c==='S.slab'||e.c==='S.beam'),stage:st,lift:e.t==='lift_car',dy:0};}
    if(st){stageCount[st]=(stageCount[st]||0)+1; stageTotal++;}
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
    G.hideAttr=new THREE.Uint8BufferAttribute(new Uint8Array(g.n*3),1); bg.setAttribute('aHide',G.hideAttr);
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

/* ---------- visibility + per-section opacity ---------- */
const catVis={}; Object.keys(CATS).forEach(c=>catVis[c]=true);
const lvlVis={}; M.levels.forEach(l=>lvlVis[l.id]=true);
const layerOp={}; M.layers.forEach(L=>layerOp[L.id]=1);
const catOp={}; Object.keys(CATS).forEach(c=>catOp[c]=1);
const stageVis={all:true}; Object.keys(stageCount).forEach(k=>stageVis[k]=true);
let isoUnit=null, explode=0, LOD=null, focusGhost=false, focusOp=0.08, focusLevels=null, CLASH=null;
const stageOn=k=>stageVis.all&&stageVis[k]!==false;
function groupVisible(G){
  if(G.stage&&!stageOn(G.stage)) return false;
  if(focusGhost&&focusLevels&&!G.lift&&!focusLevels.includes(G.lvl)) return false;
  if(G.lift) return !!catVis[G.cat];
  if(isoUnit!==null){ if(G.clip) return catVis[G.cat]&&G.lvl===UNITS[isoUnit].level; return catVis[G.cat]; }
  return catVis[G.cat]&&lvlVis[G.lvl];
}
function effOpacity(G){const lo=layerOp[G.cat[0]],co=catOp[G.cat];return (G.matBase.userData.baseOpacity||1)*(lo===undefined?1:lo)*(co===undefined?1:co)*(focusGhost?focusOp:1);}
function applyVis(){
  for(const k in groups){const G=groups[k]; if(!G.mesh) continue; G.mesh.visible=groupVisible(G);
    const o=effOpacity(G),m=G.matBase,tr=o<0.999; m.opacity=o; if(m.transparent!==tr){m.transparent=tr;m.needsUpdate=true;} m.depthWrite=!tr;
    const lv=LVL[G.lvl]; G.mesh.position.y=explode*(lv?lv.idx:0)+(G.dy||0);
  }
  if(LOD) LOD.invalidate();
  wake();
}
function resize(){const w=Math.max(1,wrap.clientWidth),h=Math.max(1,wrap.clientHeight);renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();wake();}
window.addEventListener('resize',resize); window.addEventListener('orientationchange',()=>setTimeout(resize,250)); resize();

/* ---------- picking ---------- */
const ray=new THREE.Raycaster(); const mouse=new THREE.Vector2();
function offOf(ei){const e=M.els[ei];const lv=LVL[e.l];const G=groups[elRange[ei].gk];return explode*(lv?lv.idx:0)+((G&&G.dy)||0);}
function elVisible(ei){
  const e=M.els[ei]; const G=groups[elRange[ei].gk]; if(!G||!G.mesh||!G.mesh.visible) return false;
  if(isoUnit!==null){const a=uidx(e.u),b=uidx(e.u2); if(a!==isoUnit&&b!==isoUnit) return false;}
  return true;
}
function rayAABB(o,d,bb,off){let tmin=0,tmax=1e9;for(let i=0;i<3;i++){const lo=bb[i]+(i===1?off:0),hi=bb[i+3]+(i===1?off:0);const oi=o[i],di=d[i];if(Math.abs(di)<1e-9){if(oi<lo||oi>hi)return -1;}else{let t1=(lo-oi)/di,t2=(hi-oi)/di;if(t1>t2){const t=t1;t1=t2;t2=t;}if(t1>tmin)tmin=t1;if(t2<tmax)tmax=t2;if(tmin>tmax)return -1;}}return tmin;}
function rayTri(o,d,a,b,c){const e1=[b[0]-a[0],b[1]-a[1],b[2]-a[2]],e2=[c[0]-a[0],c[1]-a[1],c[2]-a[2]];const p=[d[1]*e2[2]-d[2]*e2[1],d[2]*e2[0]-d[0]*e2[2],d[0]*e2[1]-d[1]*e2[0]];const det=e1[0]*p[0]+e1[1]*p[1]+e1[2]*p[2];if(Math.abs(det)<1e-12)return -1;const iv=1/det;const t=[o[0]-a[0],o[1]-a[1],o[2]-a[2]];const u=(t[0]*p[0]+t[1]*p[1]+t[2]*p[2])*iv;if(u<0||u>1)return -1;const q=[t[1]*e1[2]-t[2]*e1[1],t[2]*e1[0]-t[0]*e1[2],t[0]*e1[1]-t[1]*e1[0]];const v=(d[0]*q[0]+d[1]*q[1]+d[2]*q[2])*iv;if(v<0||u+v>1)return -1;const tt=(e2[0]*q[0]+e2[1]*q[1]+e2[2]*q[2])*iv;return tt>1e-4?tt:-1;}
function pickHit(clientX,clientY){
  const r=renderer.domElement.getBoundingClientRect();
  mouse.set(((clientX-r.left)/r.width)*2-1,-((clientY-r.top)/r.height)*2+1);
  ray.setFromCamera(mouse,camera); const o=[ray.ray.origin.x,ray.ray.origin.y,ray.ray.origin.z], d=[ray.ray.direction.x,ray.ray.direction.y,ray.ray.direction.z];
  const cand=[];
  for(let ei=0;ei<M.els.length;ei++){
    if(!elVisible(ei)) continue;
    if(effOpacity(groups[elRange[ei].gk])<0.2) continue; // nearly transparent sections let the click pass through
    const off=offOf(ei);
    const t=rayAABB(o,d,elBB.subarray(ei*6,ei*6+6),off); if(t>=0) cand.push([t,ei,off]);
  }
  cand.sort((a,b)=>a[0]-b[0]);
  let best=null;
  for(let k=0;k<cand.length&&k<80;k++){
    if(best&&cand[k][0]>best[0]) break;
    const [t0,ei,off]=cand[k]; const rg=elRange[ei]; const G=groups[rg.gk]; const P=G.posArr;
    for(let tri=rg.start;tri<rg.start+rg.count;tri++){
      const i=tri*9; const a=[P[i],P[i+1]+off,P[i+2]],b=[P[i+3],P[i+4]+off,P[i+5]],c=[P[i+6],P[i+7]+off,P[i+8]];
      const t=rayTri(o,d,a,b,c); if(t>0){const hp=[o[0]+d[0]*t,o[1]+d[1]*t,o[2]+d[2]*t]; if(hp[1]>clipYv||hp[0]>clipXv) continue; if(!best||t<best[0]) best=[t,ei];}
    }
  }
  return best?{ei:best[1],t:best[0],pt:new THREE.Vector3(o[0]+d[0]*best[0],o[1]+d[1]*best[0],o[2]+d[2]*best[0])}:null;
}
function pick(clientX,clientY){const h=pickHit(clientX,clientY);return h?h.ei:-1;}
controls.hitTest=(x,y)=>{const h=pickHit(x,y);return h?h.pt:null;};
let clipYv=1000, clipXv=1000;

/* ---------- selection highlight ---------- */
let hlObjs=[], selIdx=-1, selSet=[];
function clearHL(){ hlObjs.forEach(o=>{scene.remove(o);o.geometry.dispose();}); hlObjs=[]; wake(); }
function addHL(idxs,color=0xffb000,edges=true,opacity=0.8){
  idxs=idxs.filter(elVisible); if(!idxs.length) return;
  const pos=[];
  idxs.forEach(ei=>{const rg=elRange[ei]; const G=groups[rg.gk]; const off=offOf(ei); const P=G.posArr; for(let i=rg.start*9;i<(rg.start+rg.count)*9;i+=3){pos.push(P[i],P[i+1]+off,P[i+2]);}});
  const bg=new THREE.BufferGeometry(); bg.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
  const mesh=new THREE.Mesh(bg,new THREE.MeshBasicMaterial({color,transparent:true,opacity,depthTest:false,side:THREE.DoubleSide})); mesh.renderOrder=999; scene.add(mesh); hlObjs.push(mesh);
  if(edges&&pos.length<600000){const eg=new THREE.EdgesGeometry(bg,35); const ln=new THREE.LineSegments(eg,new THREE.LineBasicMaterial({color:0xb35c00,depthTest:false})); ln.renderOrder=1000; scene.add(ln); hlObjs.push(ln);}
  wake();
}
function highlight(idxs,color=0xffb000,edges=true,opacity=0.8){clearHL(); addHL(idxs,color,edges,opacity);}
function bboxOf(idxs){const mn=[1e9,1e9,1e9],mx=[-1e9,-1e9,-1e9];idxs.forEach(ei=>{for(let i=0;i<3;i++){mn[i]=Math.min(mn[i],elBB[ei*6+i]);mx[i]=Math.max(mx[i],elBB[ei*6+3+i]);}});return {mn,mx,c:[(mn[0]+mx[0])/2,(mn[1]+mx[1])/2,(mn[2]+mx[2])/2],r:Math.hypot(mx[0]-mn[0],mx[1]-mn[1],mx[2]-mn[2])/2};}

/* ---------- camera fly (interpolated in spherical coords so it never cuts through the building) ---------- */
let fly=null;
function sphOf(p,t){const o=p.clone().sub(t);const r=Math.max(o.length(),1e-6);return {r,ph:Math.acos(THREE.MathUtils.clamp(o.y/r,-1,1)),th:Math.atan2(o.x,o.z)};}
function flyTo(pos,tgt,ms=900){const a=sphOf(camera.position,controls.target),b=sphOf(pos,tgt);let dth=b.th-a.th;dth=Math.atan2(Math.sin(dth),Math.cos(dth));controls.stop();fly={t0:controls.target.clone(),t1:tgt.clone(),a,b,dth,s:performance.now(),d:ms};wake(ms+300);}
function stepFly(){
  const k=Math.min(1,(performance.now()-fly.s)/fly.d);const e=k<0.5?2*k*k:1-Math.pow(-2*k+2,2)/2;
  controls.target.lerpVectors(fly.t0,fly.t1,e); const r=fly.a.r+(fly.b.r-fly.a.r)*e,ph=fly.a.ph+(fly.b.ph-fly.a.ph)*e,th=fly.a.th+fly.dth*e,sp=Math.sin(ph);
  camera.position.set(controls.target.x+r*sp*Math.sin(th),controls.target.y+r*Math.cos(ph),controls.target.z+r*sp*Math.cos(th)); camera.lookAt(controls.target); if(k>=1) fly=null;
}
function flyToBox(b,dir=[-0.55,0.6,0.55]){const r=Math.max(b.r,1.2)*2.6; const t=new THREE.Vector3(b.c[0],b.c[1],b.c[2]); const p=t.clone().add(new THREE.Vector3(dir[0],dir[1],dir[2]).normalize().multiplyScalar(r)); flyTo(p,t);}
function goHome(){const h=homeView();flyTo(h.pos,h.tgt);}
const VIEWDIR={top:[0,1,0.03],front:[0,0.16,1],back:[0,0.16,-1],right:[1,0.16,0],left:[-1,0.16,0]};
function viewPreset(name){
  if(name==='persp'){goHome();return;}
  const d=VIEWDIR[name]; if(!d) return; const k=aspectK(); const R=(name==='top'?72:64)*k;
  const tgt=HOME.tgt.clone(); if(name!=='top') tgt.y=11;
  flyTo(tgt.clone().add(new THREE.Vector3(d[0],d[1],d[2]).normalize().multiplyScalar(R)),tgt);
}
controls.addEventListener('start',()=>{fly=null;$('viewMenu').classList.remove('on');});
controls.onHome=goHome; controls.onFocus=()=>{if(selIdx>=0) flyToBox(bboxOf(selSet));};

/* ---------- info panel ---------- */
function row(k,v){return `<tr><th>${esc(k)}</th><td>${v}</td></tr>`;}
function showInfo(ei){
  const e=M.els[ei]; const T=TYPES[e.t]||{}; const c=CATS[e.c]; const lv=LVL[e.l];
  const unit=e.u?UNITS[unitIndex[e.u]]:null; const st=stageKind(e);
  let h=`<div class=ih><b>${esc(T.n||c.name)}</b><button id=icl aria-label="إغلاق">×</button></div>`;
  h+=`<div class=tags><span style="background:${c.color}22;color:${c.color}">${esc(LAYER[c.layer].name)}</span><span>${esc(c.name)}</span>${st?'<span style="background:#fff1f0;color:#cf222e">كمالية إخراجية — للعرض لا للتنفيذ</span>':''}</div>`;
  h+=`<h4>الهوية</h4><table>`+row('الرمز التعريفي (ID)',`<code>${esc(e.id)}</code>`)+(e.mark?row('الوسم / Tag',`<code>${esc(e.mark)}</code>`):'')+row('الطابق',esc(lv.name)+` (${lv.ffl>0?'+':''}${lv.ffl.toFixed(2)})`)+(unit?row('الوحدة',esc(unit.name)):'')+`</table>`;
  const sp=(T.sp||[]).slice(); const at=e.a||{};
  const extra=[]; for(const k in at){ if(k==='fin'||at[k]===null||at[k]===''||(Array.isArray(at[k])&&!at[k].length)) continue; extra.push([ATTR[k]||k,esc(fmtVal(at[k]))]); }
  if(at.fin&&at.fin.length) extra.push(['رموز التشطيب (A500)',at.fin.map(f=>esc(M.fin&&M.fin[f]?`${f} — ${M.fin[f][0]}`:f)).join('<br>')]);
  if(sp.length||extra.length){h+=`<h4>المواصفات الفنية</h4><table>`+sp.map(r=>row(r[0],esc(r[1]))).join('')+extra.map(r=>row(r[0],r[1])).join('')+`</table>`;}
  const mt=(T.mt||[]);
  h+=`<h4>الصيانة والتشغيل</h4><table>`+(mt.length?mt.map(r=>row(r[0],esc(r[1]))).join(''):row('البيانات','غير مذكورة في المستندات المرفقة'))+`</table>`;
  if(T.asm&&T.asm.length) h+=`<div class=asm><b>افتراضات هندسية — تحتاج تأكيد</b><ul>`+T.asm.map(a=>`<li>${esc(a)}</li>`).join('')+`</ul></div>`;
  if(T.adv&&T.adv.length) h+=`<div class=adv><b>إرشاد عام — غير مستخرج من المستندات</b><ul>`+T.adv.map(a=>`<li>${esc(a)}</li>`).join('')+`</ul></div>`;
  const cf=CONF[T.cf||'doc']; const srcs=(e.s||[]).map(i=>M.sp[i]).concat(T.sr||[]);
  h+=`<h4>مصدر البيانات</h4><div class=src><span class=cf style="background:${cf[1]}1a;color:${cf[1]}">${cf[0]}</span><ul>`+srcs.map(s=>`<li>${esc(s)}</li>`).join('')+`</ul></div>`;
  const grp=e.grp&&grpMap[e.grp]?grpMap[e.grp].length:0; if(grp>1) h+=`<div class=muted>جزء من مجموعة (${grp} عنصر)</div>`;
  $('info').innerHTML=h; $('info').classList.add('on'); document.body.classList.add('info-open'); document.body.classList.remove('panel-open'); $('icl').onclick=()=>{select(-1);};
  wake();
}
function select(ei,fit=false){
  selIdx=ei; if(ei<0){clearHL();$('info').classList.remove('on');document.body.classList.remove('info-open');selSet=[];document.querySelectorAll('.res.sel,.mrow.sel').forEach(x=>x.classList.remove('sel'));return;}
  const e=M.els[ei]; selSet=(e.grp&&grpMap[e.grp])?grpMap[e.grp]:[ei];
  highlight(selSet); showInfo(ei); if(fit) flyToBox(bboxOf(selSet));
}
let downXY=null, lastTap={t:0,x:0,y:0}, touchDbl=0;
const cv=renderer.domElement;
cv.addEventListener('pointerdown',ev=>{downXY=[ev.clientX,ev.clientY,ev.button];});
cv.addEventListener('pointerup',ev=>{
  if(!downXY) return; const d=downXY; downXY=null;
  if(d[2]!==0||Math.hypot(ev.clientX-d[0],ev.clientY-d[1])>6||controls.lastGestureMulti) return;
  const ei=pick(ev.clientX,ev.clientY);
  if(ev.pointerType!=='mouse'){ // touch / pen: manual double-tap = focus on the element
    const now=performance.now();
    if(now-lastTap.t<380&&Math.hypot(ev.clientX-lastTap.x,ev.clientY-lastTap.y)<28){touchDbl=now;lastTap.t=0; if(ei>=0) select(ei,true); return;}
    lastTap={t:now,x:ev.clientX,y:ev.clientY};
  }
  select(ei);
});
cv.addEventListener('dblclick',ev=>{if(performance.now()-touchDbl<700) return; const ei=pick(ev.clientX,ev.clientY); if(ei>=0) select(ei,true);});

/* ---------- visibility helpers used by search / clashes / materials ---------- */
function setCatVis(c,on){catVis[c]=on; const cb=document.querySelector(`#layers input[data-cat="${c}"]`); if(cb) cb.checked=on; const L=CATS[c].layer; const lc=document.querySelector(`#layers input[data-layer="${L}"]`); if(lc) lc.checked=Object.keys(CATS).some(k=>CATS[k].layer===L&&catVis[k]);}
function setLvlVis(l,on){lvlVis[l]=on; const cb=document.querySelector(`#levels input[data-lvl="${l}"]`); if(cb) cb.checked=on;}
function ensureVisible(ei){
  const e=M.els[ei];
  if(isoUnit!==null){const a=uidx(e.u),b=uidx(e.u2); if(a!==isoUnit&&b!==isoUnit) exitIso(true);}
  setCatVis(e.c,true); setLvlVis(e.l,true);
  const st=stageKind(e); if(st){stageVis.all=true;stageVis[st]=true;syncStageBox();}
  applyVis();
}
function focusEl(ei){ensureVisible(ei); select(ei,true); document.body.classList.remove('panel-open');}

/* ---------- UI: layers (visibility + per-section / per-branch opacity) ---------- */
const lp=$('layers');
M.layers.forEach(L=>{
  const box=document.createElement('div'); box.className='lay';
  const head=document.createElement('label'); head.className='lh'; head.innerHTML=`<input type=checkbox checked data-layer="${L.id}"><span class=dot style="background:${L.color}"></span><b>${L.name}</b>`;
  const only=document.createElement('button'); only.textContent='فقط'; only.className='mini'; only.onclick=(ev)=>{ev.preventDefault();M.layers.forEach(L2=>{lp.querySelector(`input[data-layer="${L2.id}"]`).checked=(L2.id===L.id); lp.querySelectorAll(`input[data-cat^="${L2.id}."]`).forEach(i=>{i.checked=(L2.id===L.id);catVis[i.dataset.cat]=(L2.id===L.id);});}); applyVis();};
  head.appendChild(only); box.appendChild(head);
  const opr=document.createElement('div'); opr.className='opr'; opr.innerHTML=`<span>الشفافية</span><input type=range min=5 max=100 value=100 data-opl="${L.id}" aria-label="شفافية ${L.name}"><b data-opv="${L.id}">100%</b><button class=mini data-subtog="1" title="شفافية كل فرع على حدة" aria-label="شفافية الفروع">الفروع</button>`;
  box.appendChild(opr);
  const subs=document.createElement('div'); subs.className='subs';
  L.subs.forEach(s=>{const n=M.els.filter(e=>e.c===s[0]).length; if(!n) return;
    const w=document.createElement('div'); w.innerHTML=`<label class=sl><input type=checkbox checked data-cat="${s[0]}"> ${s[1]} <i>${n}</i></label><div class=sop><span>شفافية</span><input type=range min=5 max=100 value=100 data-opc="${s[0]}" aria-label="شفافية ${s[1]}"><b data-opcv="${s[0]}">100%</b></div>`; subs.appendChild(w);});
  box.appendChild(subs); lp.appendChild(box);
});
lp.addEventListener('change',ev=>{const t=ev.target; if(t.dataset.layer){lp.querySelectorAll(`input[data-cat^="${t.dataset.layer}."]`).forEach(i=>{i.checked=t.checked;catVis[i.dataset.cat]=t.checked;});} else if(t.dataset.cat){catVis[t.dataset.cat]=t.checked;} applyVis();});
lp.addEventListener('input',ev=>{const t=ev.target; if(t.dataset.opl){const v=+t.value; layerOp[t.dataset.opl]=v/100; lp.querySelector(`[data-opv="${t.dataset.opl}"]`).textContent=v+'%'; applyVis();}
  else if(t.dataset.opc){const v=+t.value; catOp[t.dataset.opc]=v/100; lp.querySelector(`[data-opcv="${t.dataset.opc}"]`).textContent=v+'%'; applyVis();}});
lp.addEventListener('click',ev=>{const b=ev.target.closest('[data-subtog]'); if(b){b.closest('.lay').classList.toggle('subop'); b.classList.toggle('on');}});
$('opReset').onclick=()=>{M.layers.forEach(L=>layerOp[L.id]=1); Object.keys(catOp).forEach(c=>catOp[c]=1); lp.querySelectorAll('[data-opl],[data-opc]').forEach(i=>i.value=100); lp.querySelectorAll('[data-opv],[data-opcv]').forEach(b=>b.textContent='100%'); applyVis(); toast('أُعيدت الشفافية إلى 100% لكل الأقسام');};
const lv=$('levels');
M.levels.slice().reverse().forEach(l=>{const lab=document.createElement('label'); lab.innerHTML=`<input type=checkbox checked data-lvl="${l.id}"> ${l.name} <i>${l.ffl>0?'+':''}${l.ffl.toFixed(2)}</i>`; lv.appendChild(lab);});
lv.addEventListener('change',ev=>{const t=ev.target; if(t.dataset.lvl){lvlVis[t.dataset.lvl]=t.checked;applyVis();}});
$('clipY').addEventListener('input',ev=>{const v=+ev.target.value; clipYv=(v>=30)?1000:v; clipY.constant=clipYv; $('clipYV').textContent=(v>=30)?'بدون':v.toFixed(1)+' م';});
$('clipX').addEventListener('input',ev=>{const v=+ev.target.value; clipXv=(v>=46)?1000:v; clipX.constant=clipXv; $('clipXV').textContent=(v>=46)?'بدون':v.toFixed(1)+' م';});
$('expl').addEventListener('input',ev=>{explode=+ev.target.value/10; applyVis(); if(selIdx>=0) highlight(selSet);});
$('btnHome').onclick=goHome;
$('btnAll').onclick=()=>{M.layers.forEach(L=>{lp.querySelector(`input[data-layer="${L.id}"]`).checked=true;lp.querySelectorAll(`input[data-cat^="${L.id}."]`).forEach(i=>{i.checked=true;catVis[i.dataset.cat]=true;});});lv.querySelectorAll('input').forEach(i=>{i.checked=true;lvlVis[i.dataset.lvl]=true;});stageVis.all=true;Object.keys(stageCount).forEach(k=>stageVis[k]=true);syncStageBox();applyVis();};

/* ---------- stage items (display-only props): one global switch + per-kind switches ---------- */
function buildStageBox(){
  const box=$('stageBox'); if(!stageTotal){box.innerHTML='';return;}
  let h=`<div class=lay style="border-color:#e0b4b0"><label class=lh><input type=checkbox checked data-stage="all"><span class=dot style="background:#cf222e"></span><b>الكماليات الإخراجية</b><i>${stageTotal}</i></label><div class=muted style="margin:0 0 4px">للعرض لا للتنفيذ (أثاث، أشجار، سيارات…). لا تمسّ العناصر الموثّقة في المخططات.</div><div class=subs>`;
  Object.keys(stageCount).forEach(k=>{h+=`<label><input type=checkbox checked data-stage="${k}"> ${STAGE_KINDS[k]||k} <i>${stageCount[k]}</i></label>`;});
  box.innerHTML=h+`</div></div>`;
}
function syncStageBox(){document.querySelectorAll('#stageBox input[data-stage]').forEach(i=>{i.checked=i.dataset.stage==='all'?stageVis.all:stageVis[i.dataset.stage]!==false;});}
$('stageBox').addEventListener('change',ev=>{const t=ev.target; if(!t.dataset.stage) return; if(t.dataset.stage==='all') stageVis.all=t.checked; else stageVis[t.dataset.stage]=t.checked; applyVis();});
buildStageBox();

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
  (u.rects||[]).forEach(r=>{
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
function exitIso(noFly){isoUnit=null;U.iso.value=-1;U.maskOn.value=0;ghost.visible=false; catVis['A.ceil']=ceilWasOn; const cb=document.querySelector('input[data-cat="A.ceil"]'); if(cb) cb.checked=ceilWasOn; applyVis();$('isoBar').classList.remove('on');document.querySelectorAll('.ub').forEach(b=>b.classList.remove('sel')); if(noFly!==true) goHome();}
$('isoExit').onclick=()=>exitIso();

/* ---------- tabs ---------- */
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('on'));document.querySelectorAll('.pane').forEach(x=>x.classList.remove('on'));t.classList.add('on');$(t.dataset.pane).classList.add('on');t.scrollIntoView&&t.scrollIntoView({block:'nearest',inline:'nearest'});if(t.dataset.pane==='pSearch'&&matchMedia('(pointer:fine)').matches) $('q').focus();});

/* ---------- search by tag / ID / name ---------- */
let sIdx=null, lastHits=[];
function buildSearchIndex(){sIdx=new Array(M.els.length);for(let i=0;i<M.els.length;i++){const e=M.els[i],T=TYPES[e.t]||{},a=e.a||{};sIdx[i]=normAr([e.id,e.mark||'',T.n||'',CATS[e.c].name,LVL[e.l].name,fmtVal(a.room||''),a.loc||'',a.kind||''].join(' '));}}
function runSearch(raw){
  const box=$('qres'),info=$('qinfo'); const q=normAr(raw.trim()); if(!q){box.innerHTML='';info.textContent='اكتب Tag مثل FCU-1-3.2 أو جزءًا من الـID أو اسم الغرفة أو الفئة.';lastHits=[];return;}
  if(!sIdx) buildSearchIndex(); const toks=q.split(/\s+/).filter(Boolean); const hits=[];
  for(let i=0;i<sIdx.length;i++){const s=sIdx[i]; let ok=true; for(const t of toks){if(s.indexOf(t)<0){ok=false;break;}} if(!ok) continue;
    const e=M.els[i],mk=(e.mark||'').toLowerCase(),id=e.id.toLowerCase(); const sc=(mk===q||id===q)?0:(mk.startsWith(q)||id.startsWith(q))?1:(mk.includes(q)||id.includes(q))?2:3; hits.push([sc,i]);}
  hits.sort((a,b)=>a[0]-b[0]||a[1]-b[1]); lastHits=hits.map(h=>h[1]);
  info.innerHTML=`${hits.length.toLocaleString('en')} نتيجة`+(hits.length>80?' — يُعرض أول 80':'')+(hits.length&&hits.length<=1500?` <button class=mini id=qhl>إبراز الكل</button>`:'');
  box.innerHTML=lastHits.slice(0,80).map(i=>{const e=M.els[i],T=TYPES[e.t]||{};return `<div class=res data-i="${i}"><b>${esc(e.mark||e.id)}</b><small>${esc(T.n||CATS[e.c].name)} • ${esc(CATS[e.c].name)} • ${esc(LVL[e.l].name)}${e.mark?' • '+esc(e.id):''}</small></div>`;}).join('');
}
let qT=0; $('q').addEventListener('input',ev=>{clearTimeout(qT);qT=setTimeout(()=>runSearch(ev.target.value),130);});
$('qres').addEventListener('click',ev=>{const r=ev.target.closest('.res'); if(!r) return; document.querySelectorAll('#qres .res.sel').forEach(x=>x.classList.remove('sel')); r.classList.add('sel'); focusEl(+r.dataset.i);});
$('qinfo').addEventListener('click',ev=>{if(ev.target.id!=='qhl') return; lastHits.forEach(ensureVisible); select(-1); clearHL(); addHL(lastHits,0xffb000,lastHits.length<300); flyToBox(bboxOf(lastHits)); document.body.classList.remove('panel-open');});
runSearch('');

/* ---------- materials legend + finishes vs BOQ ---------- */
let matSel=null;
function buildMat(){
  const byMat={},byFin={}; M.els.forEach((e,i)=>{const m=e.m||'conc'; (byMat[m]=byMat[m]||[]).push(i); ((e.a&&e.a.fin)||[]).forEach(f=>(byFin[f]=byFin[f]||[]).push(i));});
  let h=`<h3>دليل المواد (اضغط لإبراز كل عناصرها)</h3>`;
  Object.keys(MATS).filter(k=>byMat[k]&&!k.startsWith('fin_')).sort((a,b)=>byMat[b].length-byMat[a].length).forEach(k=>{const m=MATS[k]; h+=`<div class=mrow data-mat="${esc(k)}"><span class=sw style="background:${m.color};${m.opacity?'opacity:'+Math.max(m.opacity,0.45):''}"></span><div><b>${esc(m.name)}</b><small>${m.code?esc(m.code):''}</small></div><span class=n>${byMat[k].length}</span></div>`;});
  const fins=Object.keys(M.fin||{}).filter(f=>byFin[f]||(M.finq&&M.finq[f]));
  if(fins.length){
    h+=`<h3>رموز التشطيب (A500) ومطابقة الكميات مع BOQ</h3><div class=note>كمية BOQ مأخوذة من جدول الكميات. «النموذج» مساحة محسوبة من هندسة العناصر لما أمكن (أرضيات وأسقف)؛ الفروق تحتاج مراجعة ولا تعني خطأ بالضرورة.</div>`;
    fins.sort((a,b)=>a.localeCompare(b,'en',{numeric:true})).forEach(f=>{const d=M.fin[f],q=M.finq&&M.finq[f]; const n=(byFin[f]||[]).length;
      let qr=`<div class=qrow><span>BOQ: <b>${d[4]} ${esc(d[3])}</b></span>`;
      if(q&&q.area!=null){const df=(q.area-d[4])/d[4]*100; qr+=`<span>النموذج: <b>${q.area.toLocaleString('en')} م²</b>${q.tower!=null&&q.tower!==q.area?` <small>(الطوابق 1–5: ${q.tower.toLocaleString('en')})</small>`:''}</span><span class="${Math.abs(df)>10?'bad':'ok'}"><b>${df>0?'+':''}${df.toFixed(0)}%</b></span>`;} else qr+=`<span>النموذج: <b>—</b></span>`;
      qr+='</div>';
      h+=`<div class=mrow data-fin="${esc(f)}"><span class=sw style="background:${d[1]}"></span><div><b>${esc(f)} — ${esc(d[0])}</b><small>بند BOQ ${esc(d[2])}</small>${qr}</div><span class=n>${n}</span></div>`;});
  }
  if(M.ral&&M.ral.rows){
    h+=`<h3>أنظمة الدهان وألوان RAL (من الجدول المرفق)</h3><div class=note>${esc(M.ral.note||'')}</div>`;
    M.ral.rows.forEach(r=>{h+=`<div class=mrow style="grid-template-columns:50px 1fr"><b style="direction:ltr">${esc(r.code)}</b><div><b>${esc(r.cat)} — ${esc(r.space)}</b><small>${esc(r.system)} • ${esc(r.finish)} • ${esc(r.ral)} <span class=bad>(غير محدد)</span></small>${r.flag?`<small class=bad>${esc(r.flag)}</small>`:''}</div></div>`;});
  }
  $('matBox').innerHTML=h;
  $('matBox').onclick=ev=>{const r=ev.target.closest('.mrow'); if(!r||(!r.dataset.mat&&!r.dataset.fin)) return; const key=r.dataset.mat?'m:'+r.dataset.mat:'f:'+r.dataset.fin;
    document.querySelectorAll('#matBox .mrow.sel').forEach(x=>x.classList.remove('sel'));
    if(matSel===key){matSel=null;clearHL();return;} matSel=key; r.classList.add('sel');
    const idx=r.dataset.mat?byMat[r.dataset.mat]:byFin[r.dataset.fin]; if(!idx||!idx.length) return; const vis=idx.filter(i=>{const e=M.els[i];return catVis[e.c]&&lvlVis[e.l];});
    selIdx=-1; $('info').classList.remove('on'); document.body.classList.remove('info-open'); clearHL(); addHL(vis.length?vis:idx,0xffb000,idx.length<250); if(!vis.length) toast('عناصر هذه المادة مخفية حاليًا — فعّل أقسامها أو طوابقها'); else flyToBox(bboxOf(vis)); document.body.classList.remove('panel-open');};
}
buildMat();

/* ---------- clash list ---------- */
function setGhost(on,op,levels){focusGhost=!!on; if(op!==undefined) focusOp=op; focusLevels=on?(levels||null):null; applyVis();}
function buildClash(){
  if(!window.initClash){$('clashBox').innerHTML='<div class=muted>وحدة التعارضات غير محمّلة.</div>';return;}
  CLASH=initClash({M,THREE,scene,camera,controls,$,esc,LVL,UNITS,wake,flyTo,ensureVisible,select,highlight,addHL,clearHL,toast,setGhost,focusEl,bboxOf});
}
buildClash();

/* ---------- lifts: optional car motion (illustrative; speed and dwell are NOT from the documents) ---------- */
const lifts=[]; let liftSim=false;
function parseStops(s){const out=[]; String(s||'').split(',').forEach(p=>{p=p.trim(); const m=p.match(/^(\d+)\s*[–-]\s*(\d+)$/); if(m){for(let i=+m[1];i<=+m[2];i++) out.push(String(i));} else if(p) out.push(p);}); return out.filter(id=>LVL[id]);}
(function(){M.els.forEach((e,ei)=>{if(e.t!=='lift_car') return; const G=groups[elRange[ei].gk]; const st=parseStops(e.a&&e.a.stops); if(!G||st.length<2) return;
  const base=LVL[e.l].ffl; const idx=Math.max(0,st.indexOf(e.l)); lifts.push({G,base,ffl:st.map(id=>LVL[id].ffl),idx,dir:idx>=st.length-1?-1:1,dy:0,wait:0,last:null});});
  if(lifts.length) $('liftRow').style.display='flex';})();
function stepLifts(dt){lifts.forEach(L=>{
  if(L.wait>0){L.wait-=dt;return;} const goal=L.ffl[L.idx]-L.base,d=goal-L.dy,st=1.6*dt;
  if(Math.abs(d)<=st){L.dy=goal;L.wait=1.8;L.idx+=L.dir; if(L.idx>=L.ffl.length||L.idx<0){L.dir*=-1;L.idx+=2*L.dir;}} else L.dy+=Math.sign(d)*st;
  L.G.dy=L.dy; const lv=LVL[L.G.lvl]; L.G.mesh.position.y=explode*(lv?lv.idx:0)+L.dy;});}
$('liftBtn').onclick=()=>{liftSim=!liftSim; $('liftBtn').textContent=liftSim?'إيقاف':'تشغيل'; $('liftBtn').classList.toggle('on',liftSim); if(liftSim){clearHL(); toast('محاكاة توضيحية: السرعة وزمن التوقف غير واردين في المستندات',4200);} else {lifts.forEach(L=>{L.dy=0;L.G.dy=0;L.idx=Math.max(0,L.ffl.findIndex(f=>Math.abs(f-L.base)<1e-6));L.wait=0;}); applyVis();}};

/* ---------- samples: swap the plain proxy for the detailed sample when the camera is close (src/detail.js + samples.json) ---------- */
if(window.SampleLOD&&window.__SAMPLES__){
  LOD=new SampleLOD({M,scene,camera,groups,elRange,elBB,wake,exploded:()=>explode!==0,liftRunning:()=>liftSim,
    unitVisible:u=>u.eis.every(ei=>{const G=groups[elRange[ei].gk]; return elVisible(ei)&&effOpacity(G)/(G.matBase.userData.baseOpacity||1)>0.95;})});
  const chk=$('lodChk'); if(chk){ let saved=null; try{saved=localStorage.getItem('c4lod');}catch(e){} if(saved==='0'){chk.checked=false; LOD.setEnabled(false);}
    chk.onchange=ev=>{LOD.setEnabled(ev.target.checked); try{localStorage.setItem('c4lod',ev.target.checked?'1':'0');}catch(e){} toast(ev.target.checked?'عند التقريب يُستبدل المجسم المبسّط بعينة تفصيلية':'عُطّل استبدال العينات التفصيلية');}; }
}
/* ---------- toolbar: modes, views, fullscreen, performance, help ---------- */
document.querySelectorAll('#modes button').forEach(b=>b.onclick=()=>controls.setMode(b.dataset.m));
controls.addEventListener('mode',ev=>{document.querySelectorAll('#modes button').forEach(b=>b.classList.toggle('on',b.dataset.m===ev.mode));wake();});
$('btnViews').onclick=ev=>{ev.stopPropagation();$('viewMenu').classList.toggle('on');};
$('viewMenu').onclick=ev=>{const b=ev.target.closest('button[data-v]'); if(!b) return; viewPreset(b.dataset.v); $('viewMenu').classList.remove('on');};
document.addEventListener('click',ev=>{if(!ev.target.closest('#viewMenu,#btnViews')) $('viewMenu').classList.remove('on');});
const FS_OK=document.fullscreenEnabled||document.webkitFullscreenEnabled; if(!FS_OK) $('btnFs').style.display='none';
$('btnFs').onclick=()=>{const d=document,el=d.documentElement; if(d.fullscreenElement||d.webkitFullscreenElement){(d.exitFullscreen||d.webkitExitFullscreen).call(d);} else (el.requestFullscreen||el.webkitRequestFullscreen).call(el);};
document.addEventListener('fullscreenchange',()=>{$('btnFs').classList.toggle('on',!!document.fullscreenElement);setTimeout(resize,150);});
function setPerf(on,auto){perfMode=on; renderer.setPixelRatio(ratioFor()); resize(); $('btnPerf').classList.toggle('on',on); $('btnPerf').setAttribute('aria-pressed',on); $('perfChk').checked=on; try{localStorage.setItem('c4perf',on?'1':'0');}catch(e){} if(auto) toast('فُعّل وضع الأداء تلقائيًا لسلاسة العرض (يمكن إيقافه من زر «أداء»)',4500);}
$('btnPerf').onclick=()=>setPerf(!perfMode); $('perfChk').onchange=ev=>setPerf(ev.target.checked);
$('ptrKind').onchange=ev=>{controls.pointerKind=ev.target.value;};
const helpOpen=on=>$('help').classList.toggle('on',on); $('btnHelp').onclick=()=>helpOpen(true); $('helpBtn2').onclick=()=>helpOpen(true); $('helpClose').onclick=()=>helpOpen(false); $('help').onclick=ev=>{if(ev.target===$('help')) helpOpen(false);};
window.addEventListener('keydown',ev=>{ if(ev.key==='Escape'){ if($('help').classList.contains('on')) helpOpen(false); else{ $('viewMenu').classList.remove('on'); if(selIdx>=0) select(-1); document.body.classList.remove('panel-open'); } } });
$('fab').onclick=()=>document.body.classList.add('panel-open'); $('panelClose').onclick=()=>document.body.classList.remove('panel-open');

/* ---------- loop (renders only while something changes: saves battery on phones) ---------- */
let frames=0,tLast=performance.now(),tPrev=performance.now(),perfProbe={t0:0,f:0,done:false};
function loop(){requestAnimationFrame(loop);
  const now=performance.now(),dt=Math.min(0.1,(now-tPrev)/1000); tPrev=now;
  if(fly){stepFly();wake(300);}
  if(controls.update()) wake(300);
  if(liftSim&&lifts.length){stepLifts(dt);wake(300);}
  if(LOD&&LOD.update()) wake(300);
  if(CLASH) CLASH.frame(now,dt);
  if(now<awakeUntil){renderer.render(scene,camera);frames++;
    if(!perfProbe.done){ if(!perfProbe.t0&&now>0) {perfProbe.t0=now+900;} if(now>perfProbe.t0){perfProbe.f++; if(now>perfProbe.t0+2200){perfProbe.done=true; const fps=perfProbe.f*1000/(now-perfProbe.t0); let saved=null; try{saved=localStorage.getItem('c4perf');}catch(e){} if(saved===null&&fps<18&&!perfMode) setPerf(true,true);}}}
  }
  if(now-tLast>1000){$('fps').textContent=frames?Math.round(frames*1000/(now-tLast))+' fps · ':'';frames=0;tLast=now;}
}
{let saved=null; try{saved=localStorage.getItem('c4perf');}catch(e){} if(saved==='1') setPerf(true,false); else if(saved==='0') perfProbe.done=true;}
wake(4200); loop(); applyVis();
{const L=$('loader'); if(L){L.classList.add('off'); setTimeout(()=>L.remove(),600);} }
$('stat').textContent=M.els.length.toLocaleString('en')+' عنصر';
window.__dbg={LOD,get CLASH(){return CLASH;},scene,camera,controls,groups,renderer,select,isolate,pick,M,focusEl,viewPreset,setPerf,layerOp,catOp,applyVis,runSearch,wake,get perfMode(){return perfMode;},get flying(){return !!fly;},pickHit,get awake(){return awakeUntil;}};
