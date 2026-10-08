/* ===== C4 BIM viewer app ===== */
const M=window.__MODEL__;
const $=id=>document.getElementById(id);
const LVL={}; M.levels.forEach((l,i)=>{l.idx=i;LVL[l.id]=l;});
const CATS={}; M.layers.forEach(L=>L.subs.forEach(s=>{CATS[s[0]]={id:s[0],name:s[1],layer:L.id,color:L.color};}));
const LAYER={}; M.layers.forEach(L=>LAYER[L.id]=L);
const MATS=M.mats; const TYPES=M.types||{};
const matIndex={}; Object.keys(MATS).forEach((k,i)=>matIndex[k]=i);
let lightPreset='day',lightsOn=false,glow=null,lampsPinned=false,lastPL=0;   // lighting state (the block further down uses them; applyVis() may run earlier)
const UNITS=M.units||[]; const unitIndex={}; UNITS.forEach((u,i)=>unitIndex[u.id]=i);
const ATTR={head:'رأس الرشاش المخدوم (ID)',buried:'مدفون تحت الأرضية',model:'كود المنتج (الموديل)',area_m2:'المساحة (م²)',thickness_mm:'السماكة (مم)',state:'الحالة',thk_cm:'السماكة (سم)',w_cm:'العرض (سم)',h_cm:'الارتفاع (سم)',d_cm:'العمق (سم)',dia_cm:'القطر (سم)',len_m:'الطول (م)',kind:'النوع',loc:'الموقع',side:'الجهة',room:'الغرفة',wall_cm:'سماكة الجدار (سم)',step:'رقم الدرجة',rise_cm:'ارتفاع الدرجة (سم)',tread_cm:'عرض الدرجة (سم)',flight:'الجناح',stops:'المحطات',cab_cm:'مقصورة (سم)',h_m:'الارتفاع (م)',top:'منسوب القمة',part:'الجزء',assumed_h:'ارتفاع السقف المستعار (م) — افتراضي',
    hang_cm:'طول التعليقة (سم)',car:'المصعد',level:'الطابق',clear_w_cm:'العرض الصافي (سم)',clear_h_cm:'الارتفاع الصافي (سم)',door_clear_cm:'فتحة الباب الصافية (سم)',cab_h_m:'ارتفاع المقصورة (م)',bay:'رقم الموقف',accessible:'موقف ذوي الإعاقة',base_z_m:'منسوب القاعدة (م)',name_ar:'الاسم',note:'ملاحظة',snap_note:'ملاحظة السحب إلى الجدار',snap_cm:'مسافة السحب إلى الجدار (سم)',stand_cm:'ارتفاع الحامل (سم)',species:'النوع النباتي (رمز)',canopy_diam_cm:'قطر التاج (سم)',total_h_m:'الارتفاع الكلي (م)',pole_h_m:'ارتفاع العمود (م)',bays:'المواقف (أرقام)',block:'الكتلة',ribs:'عدد الأضلاع',span_cm:'الفتحة (سم)',top_of_beam_m:'قمة الحزمة (م)',rod_cm:'طول القضيب (سم)',height_m:'الارتفاع (م)',power_w:'القدرة (واط)',mount_h_m:'ارتفاع التركيب (م)',unsupported:'غير محمول',top_m:'منسوب القمة (م)',dim_note:'ملاحظة الأبعاد',level_note:'ملاحظة المنسوب',area_m2:'المساحة (م²)',height_cm:'الارتفاع (سم)',thick_cm:'السماكة (سم)',n:'العدد',from_level:'من الطابق',to_level:'إلى الطابق',x_cm:'الإحداثي x (سم)',y_cm:'الإحداثي y (سم)',riser_note:'ملاحظة الرايزر',where:'الموضع',floor_note:'ملاحظة الأرضية',finish_note:'ملاحظة التشطيب',top_of_seat_m:'منسوب سطح المقعد (م)',face_note:'ملاحظة اتجاه الواجهة',devices:'عدد الأجهزة',dims_mm:'الأبعاد (مم)',sand_top_m:'منسوب الرمل (م)',fl_m:'المنسوب النهائي F.L. (م)',fill_note:'ملاحظة الردم',duty:'الخدمة',ffl_m:'منسوب الأرضية (م)',width_cm:'العرض (سم)',slope_pct:'الميل (%)',transition_pct:'ميل الانتقال (%)',transition_cm:'طول الانتقال (سم)',z_note:'ملاحظة المنسوب',level_m:'المنسوب (م)',height_note:'ملاحظة الارتفاع',cladding:'الكسوة',kva:'القدرة (ك.ف.أ)',hv_kv:'الجهد العالي (ك.ف)',lv_kv:'الجهد المنخفض (ك.ف)',amps:'التيار (أمبير)',dims_cm:'الأبعاد (سم)',dims_note:'ملاحظة الأبعاد',
  dia_mm:'القطر (مم)',length_m:'الطول (م)',size_cm:'المقاس (سم)',dia_note:'ملاحظة القطر',size_note:'ملاحظة المقاس',cls:'رمز الفئة (من المفتاح)',match:'درجة مطابقة الرمز',derived_type:'النوع مشتق من المخطط',tag_floor:'الطابق في الوسم',cap_l:'السعة (لتر)',cap_known:'السعة مذكورة في المخطط',mount_note:'ملاحظة التركيب (افتراض)',display_note:'ملاحظة العرض',
  sched_unit:'الوحدة في جدول AC-106',serving:'تخدم (من الجدول)',fcu_kind:'نوع الوحدة',cap_total_kw:'السعة الكلية للتبريد (كيلوواط)',cap_sens_kw:'السعة المحسوسة (كيلوواط)',chw_gpm:'تدفق المياه المبردة (GPM)',chw_pipe:'وصلة المياه المبردة',air_lps:'تدفق الهواء (لتر/ثانية)',esp_pa:'الضغط الاستاتيكي (باسكال)',coil_on:'هواء الدخول للملف — جاف/رطب (°م)',coil_off:'هواء الخروج من الملف — جاف/رطب (°م)',elec_kw:'القدرة الكهربائية (كيلوواط)',qty_floors:'عدد الوحدات المماثلة في الجدول',sched_note:'ملاحظة مطابقة الجدول'};
const CONF={doc:['مستخرج من المستندات','#1a7f37'],derived:['مشتق/محسوب من المستندات','#9a6700'],assumed:['افتراض هندسي — يحتاج تأكيد','#cf222e']};
const STAGE_KINDS={furniture:'أثاث',tree:'أشجار',plant:'نباتات',car:'سيارات',person:'أشخاص',shade:'مظلات ظل',play:'ألعاب أطفال',appliance:'أجهزة المطبخ (غير مشمولة بالعقد)',curtain:'ستائر',ground:'تفاصيل الأرض (رمل مبلّل، خراطيم ري)',other:'أخرى'};
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
const hemi=new THREE.HemisphereLight(0xffffff,0x8a8f98,0.85); scene.add(hemi);
const sun=new THREE.DirectionalLight(0xffffff,0.75); sun.position.set(-40,70,30); scene.add(sun);
const sun2=new THREE.DirectionalLight(0xffffff,0.25); sun2.position.set(50,30,-40); scene.add(sun2);
/* bounce light from below (owner 2026-10-08: the camera may now look up at the undersides): created with the other lights so the materials compile once; its intensity is 0 above the horizon and rises
   to full at about 19° under it, so the undersides of slabs / soffits / the raft read clearly instead of being lit by the hemisphere's ground colour alone. It casts no shadow. */
const under=new THREE.DirectionalLight(0xffffff,0); under.position.set(0,-60,9); scene.add(under);
function stepUnder(){ const o=camera.position.y-controls.target.y, r=Math.max(camera.position.distanceTo(controls.target),1e-3); const k=THREE.MathUtils.clamp(-o/r*3.2,0,1), I=k*(lightPreset==='night'?0.22:0.62); if(Math.abs(under.intensity-I)>0.003) under.intensity=I; }
const clipY=new THREE.Plane(new THREE.Vector3(0,-1,0),1000);
const clipX=new THREE.Plane(new THREE.Vector3(-1,0,0),1000);
renderer.clippingPlanes=[clipY,clipX];

/* ---------- shader patch: unit isolation ---------- */
const U={iso:{value:-1},maskOn:{value:0},mask:{value:null},maskBox:{value:new THREE.Vector4(0,-21,34,23)},lensOn:{value:0},mono:{value:0},lensPal:{value:Array.from({length:16},()=>new THREE.Vector3(0.86,0.89,0.93))}};
function patch(mat){
  mat.onBeforeCompile=(sh)=>{
    sh.uniforms.uIso=U.iso; sh.uniforms.uMaskOn=U.maskOn; sh.uniforms.uMask=U.mask; sh.uniforms.uMaskBox=U.maskBox; sh.uniforms.uLensOn=U.lensOn; sh.uniforms.uLensPal=U.lensPal; sh.uniforms.uMono=U.mono;
    sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\nattribute vec2 aUnit; attribute float aClip; attribute float aHide; attribute float aLens; uniform vec3 uLensPal[16]; uniform float uLensOn; varying vec2 vUnit; varying float vClip; varying vec3 vWPos; varying vec3 vLensC; varying float vLensK;')
      .replace('#include <begin_vertex>','#include <begin_vertex>\nvUnit=aUnit; vClip=aClip; vWPos=(modelMatrix*vec4(transformed,1.0)).xyz; { int li=(aLens>15.5)?0:int(aLens+0.5); vLensC=uLensPal[li]; vLensK=(aLens<0.5)?0.0:1.0; }')
      .replace('#include <project_vertex>','#include <project_vertex>\n if(aHide>0.5 || (uLensOn>0.5 && aLens>254.5)) gl_Position=vec4(2.0,2.0,2.0,1.0);');
    sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\nvarying vec2 vUnit; varying float vClip; varying vec3 vWPos; varying vec3 vLensC; varying float vLensK; uniform float uLensOn; uniform float uMono; uniform float uIso; uniform float uMaskOn; uniform sampler2D uMask; uniform vec4 uMaskBox;')
      .replace('#include <color_fragment>','#include <color_fragment>\n { vec3 lb=diffuseColor.rgb; float lu=clamp(dot(lb,vec3(0.299,0.587,0.114)),0.0,1.0); vec3 mn=vec3(mix(0.50,0.97,pow(lu,0.75)));\n if(uLensOn>0.5){ diffuseColor.rgb=(vLensK>0.5)?vLensC*(0.62+0.38*lu):(uMono>0.5?mn:mix(lb,vec3(0.88,0.9,0.93),0.76)); } else if(uMono>0.5){ diffuseColor.rgb=mn; } }')
      .replace('void main() {','void main() {\n if(uIso>-0.5 && vClip<0.5 && abs(vUnit.x-uIso)>0.5 && abs(vUnit.y-uIso)>0.5) discard;\n if(uIso>-0.5 && vClip>0.5){ vec2 uv=(vWPos.xz-uMaskBox.xy)/uMaskBox.zw; if(uv.x<0.||uv.x>1.||uv.y<0.||uv.y>1.||texture2D(uMask,uv).r<0.5) discard; }');
  };
  mat.customProgramCacheKey=()=> 'bimpatch';
  return mat;
}

/* ---------- build merged geometry ---------- */
const groups={}; const elRange=new Array(M.els.length); const elBB=new Float32Array(M.els.length*6);
const grpMap={}; // grp -> [element idx]
const stageCount={}; let stageTotal=0;
function gkey(e){const st=stageKind(e);return e.c+'|'+e.l+'|'+(e.m||'conc')+(st?'|st:'+st:'')+(e.t==='lift_car'?'|'+((e.a&&e.a.car)||e.id):'');}
function uidx(u){return (u==null)?-1:(unitIndex[u]!==undefined?unitIndex[u]:-1);}

/* ---------- supports: what carries every element (pipeline/support.py wrote rod_cm / hang_cm / stand_cm on the elements that need one) ---------- */
function addSupports(g,e,geo,u1,u2,mi){
  const a=e.a; if(!a||(!a.rod_cm&&!a.hang_cm&&!a.stand_cm)) return; const k=geo[0];
  if(a.stand_cm&&(k==='b'||k==='cyl'||k==='r')){   // a device that stands on a post from the floor below (best-guess support, guesses.py)
    let x,y,z0; if(k==='b'){x=geo[1];y=geo[2];z0=geo[6];} else if(k==='cyl'){x=geo[1];y=geo[2];z0=geo[4];} else {x=(geo[1]+geo[3])/2;y=(geo[2]+geo[4])/2;z0=geo[5];}
    const gap=a.stand_cm/100; cylinder(g,x,y,2.5,z0-gap,z0,u1,u2,mi,10); cylinder(g,x,y,10,z0-gap-0.01,z0-gap,u1,u2,mi,14); return;
  }
  if(a.rod_cm&&(k==='b'||k==='cyl'||k==='r')){
    let x,y,z1; if(k==='b'){x=geo[1];y=geo[2];z1=geo[7];} else if(k==='cyl'){x=geo[1];y=geo[2];z1=geo[5];} else {x=(geo[1]+geo[3])/2;y=(geo[2]+geo[4])/2;z1=geo[6];}
    const gap=a.rod_cm/100; cylinder(g,x,y,0.45,z1,z1+gap,u1,u2,mi,8); cylinder(g,x,y,3,z1+gap-0.006,z1+gap,u1,u2,mi,10); return;
  }
  if((k==='t'||k==='d')&&(a.hang_cm||a.stand_cm)){
    const pts=geo[1]; const isT=k==='t'; const half=isT?geo[2]/200:geo[3]/200; const wid=isT?0:geo[2]/2;
    for(let i=0;i<pts.length-1;i++){
      const p=pts[i],q=pts[i+1]; const dx=q[0]-p[0],dy=q[1]-p[1]; const L=Math.hypot(dx,dy); if(L<20) continue; const n=Math.max(1,Math.round(L/240)); const nx=-dy/L,ny=dx/L;
      for(let j=0;j<n;j++){
        const t=(j+0.5)/n,x=p[0]+dx*t,y=p[1]+dy*t,z=p[2]+(q[2]-p[2])*t;
        if(a.hang_cm){const gap=a.hang_cm/100,zt=z+half+(isT?0:0.025); const offs=isT?[0]:[wid+4,-wid-4];
          for(const o of offs){cylinder(g,x+nx*o,y+ny*o,0.5,zt,zt+gap,u1,u2,mi,8); cylinder(g,x+nx*o,y+ny*o,3,zt+gap-0.006,zt+gap,u1,u2,mi,10);} 
          if(!isT){ orientedBox(g,x,y,wid*2+10,4,Math.atan2(dy,dx)*180/Math.PI+90,zt-0.04,zt-0.0,u1,u2,mi); }
        } else {const gap=a.stand_cm/100,zb=z-half-(isT?0:0.025); cylinder(g,x,y,2,zb-gap,zb,u1,u2,mi,8); cylinder(g,x,y,8,zb-gap-0.01,zb-gap,u1,u2,mi,12); if(!isT) orientedBox(g,x,y,wid*2+10,5,Math.atan2(dy,dx)*180/Math.PI+90,zb-0.04,zb,u1,u2,mi);}
      }
    }
  }
}
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
      case 't': {const pts=geo[1]; const sd=geo[2]<=3.5?5:(geo[2]<=7?6:8); for(let i=0;i<pts.length-1;i++) tubeSeg(g,pts[i],pts[i+1],geo[2]/2,u1,u2,mi,sd); break;}   // thin conduits / small pipes need fewer sides (vertex load is what the GPU pays for here)
      case 'rs': rampStrip(g,geo[1],geo[2],geo[3],u1,u2,mi); break;
      case 'sph': ellipsoid(g,geo[1],geo[2],geo[3],geo[4],geo[5],u1,u2,mi,geo[6]||8,geo[7]||5); break;
      case 'tri': triPlane(g,geo[1],geo[2],u1,u2,mi); break;
      case 'leaf': leafCloud(g,geo[1],geo[2],geo[3],geo[4],geo[5],geo[6],geo[7],geo[8],u1,u2,mi,geo[9]); break;
      case 'cur': curtain(g,geo[1],geo[2],geo[3],geo[4],geo[5],geo[6],geo[7],geo[8],u1,u2,mi); break;
      default: break;
    }
    addSupports(g,e,geo,u1,u2,mi);
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
    G.lensAttr=new THREE.Uint8BufferAttribute(new Uint8Array(g.n*3),1); bg.setAttribute('aLens',G.lensAttr);
    bg.computeBoundingSphere();
    const m=MATS[G.mat]||{color:'#bbbbbb'};
    const op=(m.opacity!==undefined)?m.opacity:1;
    const mat=patch(new THREE.MeshStandardMaterial({color:new THREE.Color(m.color),roughness:m.rough!==undefined?m.rough:(op<1?0.15:0.9),metalness:m.metal!==undefined?m.metal:(op<1?0.2:0.0),side:THREE.DoubleSide,transparent:op<1,opacity:op,depthWrite:op>=1,polygonOffset:true,polygonOffsetFactor:1,polygonOffsetUnits:1}));
    if(m.emissive){mat.emissive=new THREE.Color(m.emissive); mat.emissiveIntensity=m.emissiveIntensity||0.9;}
    mat.userData.baseOpacity=op; G.matBase=mat;
    const mesh=new THREE.Mesh(bg,mat); mesh.userData={cat:G.cat,lvl:G.lvl,key:k}; mesh.frustumCulled=true; G.mesh=mesh; scene.add(mesh);   // a group the camera cannot see is not sent to the GPU (close-ups drop ~40–55 % of the triangles)
    g.pos=g.nrm=g.unit=g.mat=g.clip=null; G.posArr=bg.attributes.position.array;
  }
  console.log('built',Object.keys(groups).length,'groups in',Math.round(performance.now()-t0),'ms');
}
buildAll();

/* ---------- context envelope (shown while a unit is isolated): OUTLINES ONLY ----------
   owner 2026-10-08: «عند عرض الوحدات هذه الطبقات تعيق النظر» — the translucent filled box of every level (two faces each, nine levels) stacked into a haze over the isolated unit. What it is for is only to show
   where the unit sits in the building, so the fills are gone and the nine boxes are drawn as thin edge lines in one draw call. */
const ghost=new THREE.Group(); ghost.visible=false; scene.add(ghost);
(function(){
  const pos=[], E=[[0,1],[1,2],[2,3],[3,0],[4,5],[5,6],[6,7],[7,4],[0,4],[1,5],[2,6],[3,7]];
  (M.env||[]).forEach(r=>{ const x0=r[0]*S,x1=r[2]*S,z0=-r[3]*S,z1=-r[1]*S,y0=r[4],y1=r[5];
    const c=[[x0,y0,z0],[x1,y0,z0],[x1,y0,z1],[x0,y0,z1],[x0,y1,z0],[x1,y1,z0],[x1,y1,z1],[x0,y1,z1]]; E.forEach(e=>{ pos.push(c[e[0]][0],c[e[0]][1],c[e[0]][2],c[e[1]][0],c[e[1]][1],c[e[1]][2]); }); });
  const g=new THREE.BufferGeometry(); g.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
  const l=new THREE.LineSegments(g,new THREE.LineBasicMaterial({color:0x5b6f85,transparent:true,opacity:0.4})); l.frustumCulled=false; l.raycast=()=>{}; ghost.add(l);
})();

/* ---------- visibility + per-section opacity ---------- */
const catVis={}; Object.keys(CATS).forEach(c=>catVis[c]=true);
const lvlVis={}; M.levels.forEach(l=>lvlVis[l.id]=true);
const layerOp={}; M.layers.forEach(L=>layerOp[L.id]=1);
const catOp={}; Object.keys(CATS).forEach(c=>catOp[c]=1);
const stageVis={all:true}; Object.keys(stageCount).forEach(k=>stageVis[k]=true);
let isoUnit=null, explode=0, LOD=null, focusGhost=false, focusOp=0.08, focusLevels=null, focusSamples=false, CLASH=null, ISSUES=null;
const stageOn=k=>stageVis.all&&stageVis[k]!==false;
function groupVisible(G){
  if(G.stage&&!stageOn(G.stage)) return false;
  if(focusGhost&&focusLevels&&!G.lift&&!focusLevels.includes(G.lvl)) return false;
  if(G.lift) return !!catVis[G.cat];
  if(isoUnit!==null){ if(G.clip) return catVis[G.cat]&&G.lvl===UNITS[isoUnit].level; return catVis[G.cat]; }
  return catVis[G.cat]&&lvlVis[G.lvl];
}
function effOpacity(G,noGhost){const lo=layerOp[G.cat[0]],co=catOp[G.cat];return (G.matBase.userData.baseOpacity||1)*(lo===undefined?1:lo)*(co===undefined?1:co)*(focusGhost&&!noGhost?focusOp:1);}
function applyVis(){
  for(const k in groups){const G=groups[k]; if(!G.mesh) continue; G.mesh.visible=groupVisible(G);
    const o=effOpacity(G),m=G.matBase,tr=o<0.999; m.opacity=o; if(m.transparent!==tr){m.transparent=tr;m.needsUpdate=true;} m.depthWrite=!tr;
    const lv=LVL[G.lvl]; G.mesh.position.y=explode*(lv?lv.idx:0)+(G.dy||0);
  }
  if(LOD) LOD.invalidate();
  updateGlow();
  if(window.LOOK) window.LOOK.dirty();
  wake();
}
/* phones: the bottom sheet (portrait) or the side card (landscape) covers part of the canvas — the frame's centre moves to the part that stays visible by a projection offset
   (so picking, projected labels and pins stay consistent with what is drawn); it eases in and out with the card */
let inset={x:0,y:0};
function insetWant(){
  const el=$('info'); if(!el||!el.classList.contains('on')||!window.matchMedia||!window.matchMedia('(max-width:860px)').matches) return [0,0];
  const vr=wrap.getBoundingClientRect(),r=el.getBoundingClientRect(); if(!vr.width||!vr.height||!r.height) return [0,0];
  if(r.width>=vr.width*0.9&&Math.abs(r.bottom-vr.bottom)<6) return [0,Math.min(r.height,vr.height*0.7)/2];
  if(Math.abs(r.right-vr.right)<6&&r.height>vr.height*0.4) return [Math.min(r.width,vr.width*0.6)/2,0];
  return [0,0];
}
function applyInset(){
  const w=Math.max(1,wrap.clientWidth),h=Math.max(1,wrap.clientHeight);
  if(Math.abs(inset.x)<0.5&&Math.abs(inset.y)<0.5){ inset.x=0; inset.y=0; if(camera.view&&camera.view.enabled) camera.clearViewOffset(); }
  else camera.setViewOffset(w,h,inset.x,inset.y,w,h);
}
function stepInset(dt){
  const t=insetWant(),dx=t[0]-inset.x,dy=t[1]-inset.y; if(Math.abs(dx)<0.5&&Math.abs(dy)<0.5&&inset.x===t[0]&&inset.y===t[1]) return;
  if(Math.abs(dx)<0.5&&Math.abs(dy)<0.5){ inset.x=t[0]; inset.y=t[1]; } else { const k=1-Math.exp(-Math.min(dt||0.016,0.1)*14); inset.x+=dx*k; inset.y+=dy*k; wake(300); }
  applyInset();
}
function resize(){const w=Math.max(1,wrap.clientWidth),h=Math.max(1,wrap.clientHeight);renderer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();applyInset();wake();}
window.addEventListener('resize',resize); window.addEventListener('orientationchange',()=>setTimeout(resize,250)); resize(); if(window.ResizeObserver){ new ResizeObserver(()=>resize()).observe(wrap); new ResizeObserver(()=>wake(700)).observe($('info')); }

/* ---------- lenses (src/lens.js) ---------- */
let LENS=null;
function setLens(m,opt){ if(!LENS) return; LENS.set(m,opt); document.querySelectorAll('#viewMenu button[data-lens]').forEach(b=>b.classList.toggle('on',b.dataset.lens===m)); }

/* ---------- picking ---------- */
const ray=new THREE.Raycaster(); const mouse=new THREE.Vector2();
function offOf(ei){const e=M.els[ei];const lv=LVL[e.l];const G=groups[elRange[ei].gk];return explode*(lv?lv.idx:0)+((G&&G.dy)||0);}
/* elements hidden by the owner («إخفاء العنصر», src/notes.js): bit 2 of the per-vertex aHide flag (bit 1 belongs to the detail swap, which keeps bit 2 intact) */
const uHid=new Set();
function setUserHidden(idxs,on){
  const touched=new Set();
  idxs.forEach(ei=>{ const rg=elRange[ei]; if(!rg) return; const G=groups[rg.gk]; if(!G||!G.hideAttr) return; if(on) uHid.add(ei); else uHid.delete(ei);
    const a=G.hideAttr.array; for(let i=rg.start*3,n=(rg.start+rg.count)*3;i<n;i++) a[i]=on?(a[i]|2):(a[i]&1); touched.add(G); });
  touched.forEach(G=>{G.hideAttr.needsUpdate=true;}); if(LOD) LOD.invalidate(); if(window.LOOK) window.LOOK.dirty(); wake();
}
function elVisible(ei){
  if(uHid.size&&uHid.has(ei)) return false;
  if(U.lensOn.value>0.5&&LENS&&LENS.classOf(ei)>254.5) return false;   // hidden by the lens («عزل»): it is neither drawn, picked nor highlighted
  const e=M.els[ei]; const G=groups[elRange[ei].gk]; if(!G||!G.mesh||!G.mesh.visible) return false;
  if(isoUnit!==null){const a=uidx(e.u),b=uidx(e.u2); if(a!==isoUnit&&b!==isoUnit) return false;}
  return true;
}
/* what a click may select: visible, and — while a lens class is isolated or «عزل» is on — only what the lens concerns (dimmed elements let the click pass through to the isolated ones behind them) */
function elPickable(ei){ if(!elVisible(ei)) return false; if(LENS&&LENS.restrict&&LENS.classOf(ei)<0.5) return false; return true; }
function rayAABB(o,d,bb,off){let tmin=0,tmax=1e9;for(let i=0;i<3;i++){const lo=bb[i]+(i===1?off:0),hi=bb[i+3]+(i===1?off:0);const oi=o[i],di=d[i];if(Math.abs(di)<1e-9){if(oi<lo||oi>hi)return -1;}else{let t1=(lo-oi)/di,t2=(hi-oi)/di;if(t1>t2){const t=t1;t1=t2;t2=t;}if(t1>tmin)tmin=t1;if(t2<tmax)tmax=t2;if(tmin>tmax)return -1;}}return tmin;}
function rayTri(o,d,a,b,c){const e1=[b[0]-a[0],b[1]-a[1],b[2]-a[2]],e2=[c[0]-a[0],c[1]-a[1],c[2]-a[2]];const p=[d[1]*e2[2]-d[2]*e2[1],d[2]*e2[0]-d[0]*e2[2],d[0]*e2[1]-d[1]*e2[0]];const det=e1[0]*p[0]+e1[1]*p[1]+e1[2]*p[2];if(Math.abs(det)<1e-12)return -1;const iv=1/det;const t=[o[0]-a[0],o[1]-a[1],o[2]-a[2]];const u=(t[0]*p[0]+t[1]*p[1]+t[2]*p[2])*iv;if(u<0||u>1)return -1;const q=[t[1]*e1[2]-t[2]*e1[1],t[2]*e1[0]-t[0]*e1[2],t[0]*e1[1]-t[1]*e1[0]];const v=(d[0]*q[0]+d[1]*q[1]+d[2]*q[2])*iv;if(v<0||u+v>1)return -1;const tt=(e2[0]*q[0]+e2[1]*q[1]+e2[2]*q[2])*iv;return tt>1e-4?tt:-1;}
function pickHit(clientX,clientY){
  const r=renderer.domElement.getBoundingClientRect();
  mouse.set(((clientX-r.left)/r.width)*2-1,-((clientY-r.top)/r.height)*2+1);
  ray.setFromCamera(mouse,camera); const o=[ray.ray.origin.x,ray.ray.origin.y,ray.ray.origin.z], d=[ray.ray.direction.x,ray.ray.direction.y,ray.ray.direction.z];
  const cand=[];
  for(let ei=0;ei<M.els.length;ei++){
    if(!elPickable(ei)) continue;
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
      const t=rayTri(o,d,a,b,c); if(t>0){const hp=[o[0]+d[0]*t,o[1]+d[1]*t,o[2]+d[2]*t]; if(hp[1]>clipYv||hp[0]>clipXv) continue; if(!best||t<best[0]) best=[t,ei,a,b,c];}
    }
  }
  return best?{ei:best[1],t:best[0],pt:new THREE.Vector3(o[0]+d[0]*best[0],o[1]+d[1]*best[0],o[2]+d[2]*best[0]),tri:[best[2],best[3],best[4]]}:null;
}
function pick(clientX,clientY){const h=pickHit(clientX,clientY);return h?h.ei:-1;}
controls.hitTest=(x,y)=>{const h=pickHit(x,y);return h?h.pt:null;};
let clipYv=1000, clipXv=1000;

/* ---------- selection highlight ---------- */
let hlObjs=[], selIdx=-1, selSet=[];
function clearHL(){ hlObjs.forEach(o=>{scene.remove(o);o.geometry.dispose();}); hlObjs=[]; wake(); }
const HL_BLUE=0x2f7bff;   // selection = light translucent blue shading (surface pass + faint see-through pass + thin outline)
function addHL(idxs,color=HL_BLUE,edges=true,opacity=0.36){
  idxs=idxs.filter(elVisible); if(!idxs.length) return;
  const pos=[];
  idxs.forEach(ei=>{const rg=elRange[ei]; const G=groups[rg.gk]; const off=offOf(ei); const P=G.posArr; for(let i=rg.start*9;i<(rg.start+rg.count)*9;i+=3){pos.push(P[i],P[i+1]+off,P[i+2]);}});
  const bg=new THREE.BufferGeometry(); bg.setAttribute('position',new THREE.Float32BufferAttribute(pos,3));
  const surf=new THREE.Mesh(bg,new THREE.MeshBasicMaterial({color,transparent:true,opacity,depthTest:true,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-3,polygonOffsetUnits:-3,side:THREE.DoubleSide})); surf.renderOrder=998; scene.add(surf); hlObjs.push(surf);
  const ghost=new THREE.Mesh(bg,new THREE.MeshBasicMaterial({color,transparent:true,opacity:Math.min(0.12,opacity*0.4),depthTest:false,depthWrite:false,side:THREE.DoubleSide})); ghost.renderOrder=997; scene.add(ghost); hlObjs.push(ghost);
  if(edges&&pos.length<600000){const eg=new THREE.EdgesGeometry(bg,35); const ln=new THREE.LineSegments(eg,new THREE.LineBasicMaterial({color:0x1747b8,transparent:true,opacity:0.8,depthTest:false})); ln.renderOrder=1000; scene.add(ln); hlObjs.push(ln);}
  wake();
}
function highlight(idxs,color=HL_BLUE,edges=true,opacity=0.36){clearHL(); addHL(idxs,color,edges,opacity);}
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
controls.addEventListener('start',()=>{fly=null;closeMenus();});
controls.onHome=goHome; controls.onFocus=()=>{if(selIdx>=0) flyToBox(bboxOf(selSet));};

/* ---------- info panel ---------- */
function row(k,v){return `<tr><th>${esc(k)}</th><td>${v}</td></tr>`;}
const DESK=window.matchMedia('(min-width:861px)'); let infoMin=false;
function infoDocked(){return DESK.matches&&!document.body.classList.contains('dock-off');}
/* the issue drawer (src/issues.js) shares the info dock with the element card: drawerHTML !== null while the drawer is what the dock shows */
let drawerHTML=null, drawerBind=null;
function hideInfo(){drawerHTML=null; drawerBind=null; ['info','infoDock'].forEach(k=>{$(k).classList.remove('on');$(k).innerHTML='';}); document.body.classList.remove('info-open');}
function renderDrawer(){
  if(drawerHTML===null) return; const docked=infoDocked(), el=docked?$('infoDock'):$('info'), other=docked?$('info'):$('infoDock');
  other.classList.remove('on'); other.innerHTML=''; el.innerHTML=drawerHTML; el.classList.remove('min'); el.classList.add('on'); el.scrollTop=0;
  document.body.classList.toggle('info-open',!docked); document.body.classList.remove('panel-open'); if(drawerBind) drawerBind(el); wake();
}
function showDrawer(html,bind){drawerHTML=html; drawerBind=bind||null; renderDrawer();}
function hideDrawer(){if(drawerHTML!==null) hideInfo();}
function refreshInfo(){if(drawerHTML!==null) renderDrawer(); else if(selIdx>=0) showInfo(selIdx);}
function showInfo(ei){
  drawerHTML=null; drawerBind=null;
  const e=M.els[ei]; const T=TYPES[e.t]||{}; const c=CATS[e.c]; const lv=LVL[e.l];
  const unit=e.u?UNITS[unitIndex[e.u]]:null; const st=stageKind(e);
  const sec=(t,body,open)=>`<details class=idet${open?' open':''}><summary>${t}</summary>${body}</details>`;
  let h=`<div class=ih><b>${esc(T.n||c.name)}</b><span class=ihb><button id=icol type=button aria-label="طيّ التفاصيل أو فردها" title="طيّ / فرد">▴</button><button id=icl type=button aria-label="إغلاق" title="إلغاء التحديد">×</button></span></div>`;
  h+=`<div class=isub><code>${esc(e.id)}</code><span>${esc(lv.name)} (${lv.ffl>0?'+':''}${lv.ffl.toFixed(2)})</span>${unit?`<span>${esc(unit.name)}</span>`:''}</div><div class=ibody>`;
  h+=`<div class=tags><span style="background:${c.color}22;color:${c.color}">${esc(LAYER[c.layer].name)}</span><span>${esc(c.name)}</span>${st?'<span style="background:#fff1f0;color:#cf222e">كمالية إخراجية — للعرض لا للتنفيذ</span>':''}</div>`;
  {const q=e.q,P=window.LENS_PAL; if(q&&P){ const nm=['الموضع','المنسوب','المواصفة']; h+=`<div class=relq title="موثوقية بيانات هذا العنصر: موثّق من المخطط · مشتق بقاعدة · تخمين · إخراجي">`+[0,1,2].map(i=>{const g=P.GRADE[q[i]]||P.GRADE.d; return `<span class="is-pill st" style="background:${g.c};color:#0b2a3d" title="${esc(g.h)}">${nm[i]}: ${esc(g.n)}</span>`;}).join('')+`</div>`;}}
  if(window.NOTES&&window.NOTES.infoHTML) h+=window.NOTES.infoHTML(ei);   // hide / note actions come first: always in reach, the drawing follows
  h+=`<div class=ithumb id=ithumb hidden></div>`;
  h+=sec('الهوية',`<table>`+row('الرمز التعريفي (ID)',`<code>${esc(e.id)}</code>`)+(e.mark?row('الوسم / Tag',`<code>${esc(e.mark)}</code>`):'')+row('الطابق',esc(lv.name)+` (${lv.ffl>0?'+':''}${lv.ffl.toFixed(2)})`)+(unit?row('الوحدة',esc(unit.name)):'')+`</table>`,true);
  const sp=(T.sp||[]).slice(); const at=e.a||{};
  const extra=[]; for(const k in at){ if(k==='fin'||k==='assumed'||at[k]===null||at[k]===''||(Array.isArray(at[k])&&!at[k].length)) continue; extra.push([ATTR[k]||k,esc(fmtVal(at[k]))]); }
  if(at.fin&&at.fin.length) extra.push(['رموز التشطيب (A500)',at.fin.map(f=>esc(M.fin&&M.fin[f]?`${f} — ${M.fin[f][0]}`:f)).join('<br>')]);
  if(sp.length||extra.length){h+=sec('المواصفات الفنية',`<table>`+sp.map(r=>row(r[0],esc(r[1]))).join('')+extra.map(r=>row(r[0],r[1])).join('')+`</table>`,true);}
  const mt=(T.mt||[]);
  h+=sec('الصيانة والتشغيل',`<table>`+(mt.length?mt.map(r=>row(r[0],esc(r[1]))).join(''):row('البيانات','غير مذكورة في المستندات المرفقة'))+`</table>`,false);
  {const asmL=(T.asm||[]).slice(); if(at.assumed) asmL.push(String(at.assumed)); if(asmL.length) h+=`<div class=asm><b>افتراضات هندسية — تحتاج تأكيد</b><ul>`+asmL.map(a=>`<li>${esc(a)}</li>`).join('')+`</ul></div>`;}
  if(T.adv&&T.adv.length) h+=`<div class=adv><b>إرشاد عام — غير مستخرج من المستندات</b><ul>`+T.adv.map(a=>`<li>${esc(a)}</li>`).join('')+`</ul></div>`;
  const cf=CONF[T.cf||'doc']; const srcs=(e.s||[]).map(i=>M.sp[i]).concat(T.sr||[]);
  h+=sec(`مصدر البيانات <span class=cf style="background:${cf[1]}1a;color:${cf[1]}">${cf[0]}</span>`,`<div class=src><ul>`+srcs.map(s=>`<li>${esc(s)}</li>`).join('')+`</ul></div>`,false);
  const grp=e.grp&&grpMap[e.grp]?grpMap[e.grp].length:0; if(grp>1) h+=`<div class=muted>جزء من مجموعة (${grp} عنصر)</div>`;
  if(window.ISSUES&&ISSUES.infoHTML) h+=ISSUES.infoHTML(ei);
  h+=`</div>`;
  /* ONE dock: on a desktop the card lives at the top of the side panel (no second floating panel over the model); on phones / with the panel hidden it is a compact card or bottom sheet */
  const docked=infoDocked(), el=docked?$('infoDock'):$('info'), other=docked?$('info'):$('infoDock');
  other.classList.remove('on'); other.innerHTML='';
  el.innerHTML=h; el.classList.toggle('min',infoMin); el.classList.add('on'); el.scrollTop=0;
  document.body.classList.toggle('info-open',!docked); document.body.classList.remove('panel-open');
  $('icl').onclick=()=>{select(-1);}; $('icol').onclick=()=>{infoMin=!infoMin; el.classList.toggle('min',infoMin);}; if(window.THUMBS) THUMBS.fill($('ithumb'),ei);
  wake();
}
function select(ei,fit=false){
  selIdx=ei; if(ei<0){clearHL();hideInfo();selSet=[];document.querySelectorAll('.res.sel,.mrow.sel').forEach(x=>x.classList.remove('sel'));return;}
  const e=M.els[ei]; selSet=(e.grp&&grpMap[e.grp])?grpMap[e.grp]:[ei];
  highlight(selSet); showInfo(ei); if(fit) flyToBox(bboxOf(selSet));
}
let downXY=null, lastTap={t:0,x:0,y:0}, touchDbl=0, lastClick={t:0,ei:-2};
const cv=renderer.domElement;
cv.addEventListener('pointerdown',ev=>{downXY=[ev.clientX,ev.clientY,ev.button];});
cv.addEventListener('pointerup',ev=>{
  if(!downXY) return; const d=downXY; downXY=null;
  if(d[2]!==0||Math.hypot(ev.clientX-d[0],ev.clientY-d[1])>6||controls.lastGestureMulti) return;
  if(window.MEASURE&&window.MEASURE.tap&&window.MEASURE.tap(ev.clientX,ev.clientY)) return;
  if(window.ISSUES&&window.ISSUES.tap&&window.ISSUES.tap(ev.clientX,ev.clientY)) return;
  if(window.NOTES&&window.NOTES.tap&&window.NOTES.tap(ev.clientX,ev.clientY)) return;
  const ei=pick(ev.clientX,ev.clientY); const now=performance.now();
  if(ev.pointerType!=='mouse'){ // touch / pen: manual double-tap = focus on the element
    if(now-lastTap.t<380&&Math.hypot(ev.clientX-lastTap.x,ev.clientY-lastTap.y)<28){touchDbl=now;lastTap.t=0; lastClick={t:now,ei}; if(ei>=0) select(ei,true); return;}
    lastTap={t:now,x:ev.clientX,y:ev.clientY};
  }
  // a single press on what is already selected (the element or any part of its group) clears the selection; a quick second press stays a double-click/tap = focus
  const quick=now-lastClick.t<380&&lastClick.ei===ei; lastClick={t:now,ei};
  if(ei>=0&&!quick&&selSet.includes(ei)){select(-1);return;}
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
function focusEl(ei){ensureVisible(ei); select(ei,true); document.body.classList.remove('panel-open'); if(uHid.has(ei)) toast('هذا العنصر مخفي — افتح بطاقته واضغط «إظهار العنصر»',3200);}

/* ---------- UI: layers (visibility + per-section / per-branch opacity) ---------- */
const lp=$('layers');
M.layers.forEach(L=>{
  const box=document.createElement('div'); box.className='lay';
  const head=document.createElement('label'); head.className='lh'; head.innerHTML=`<input type=checkbox checked data-layer="${L.id}"><span class=dot style="background:${L.color}"></span><b>${L.name}</b>`;
  const only=document.createElement('button'); only.textContent='فقط'; only.className='mini'; only.onclick=(ev)=>{ev.preventDefault();M.layers.forEach(L2=>{lp.querySelector(`input[data-layer="${L2.id}"]`).checked=(L2.id===L.id); lp.querySelectorAll(`input[data-cat^="${L2.id}."]`).forEach(i=>{i.checked=(L2.id===L.id);catVis[i.dataset.cat]=(L2.id===L.id);});}); applyVis();};
  head.appendChild(only); const chv=document.createElement('button'); chv.className='mini chv'; chv.textContent='▾'; chv.title='عرض / إخفاء الفروع'; chv.setAttribute('aria-label','عرض فروع '+L.name); chv.onclick=(ev)=>{ev.preventDefault(); box.classList.toggle('open');}; head.appendChild(chv); box.appendChild(head);
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
  let h=`<div class=lay style="border-color:#e0b4b0"><label class=lh><input type=checkbox checked data-stage="all"><span class=dot style="background:#cf222e"></span><b>الكماليات الإخراجية</b><i>${stageTotal}</i><button type=button class="mini chv" data-chv=1 title="عرض / إخفاء الأنواع" aria-label="عرض أنواع الكماليات">▾</button></label><div class=muted style="margin:0 0 4px">للعرض لا للتنفيذ (أثاث، أشجار، سيارات…). لا تمسّ العناصر الموثّقة في المخططات.</div><div class=subs>`;
  Object.keys(stageCount).forEach(k=>{h+=`<label><input type=checkbox checked data-stage="${k}"> ${STAGE_KINDS[k]||k} <i>${stageCount[k]}</i></label>`;});
  box.innerHTML=h+`</div></div>`;
}
function syncStageBox(){document.querySelectorAll('#stageBox input[data-stage]').forEach(i=>{i.checked=i.dataset.stage==='all'?stageVis.all:stageVis[i.dataset.stage]!==false;});}
$('stageBox').addEventListener('click',ev=>{const b=ev.target.closest('[data-chv]'); if(b){ev.preventDefault(); b.closest('.lay').classList.toggle('open');}});
$('stageBox').addEventListener('change',ev=>{const t=ev.target; if(!t.dataset.stage) return; if(t.dataset.stage==='all') stageVis.all=t.checked; else stageVis[t.dataset.stage]=t.checked; applyVis();});
buildStageBox();

/* ---------- units ---------- */
const up=$('units');
(function(){
  /* the buttons follow the plan, north row first and west on the left (owner 2026-10-08: «3 2 1 / 4 5 6»): rows are found from the unit rectangles (plan y grows to the north, a gap of more than 5 m
     starts a new row), each row runs west → east; the grid is laid out left-to-right (.ur{direction:ltr}) so the first button of a row is the western one */
  const planOrder=list=>{ const cen=u=>{ const r=u.rects||[]; if(!r.length) return [0,0]; let sx=0,sy=0; r.forEach(a=>{ sx+=(a[0]+a[2])/2; sy+=(a[1]+a[3])/2; }); return [sx/r.length,sy/r.length]; };
    const a=list.map(u=>({u,c:cen(u)})).sort((p,q)=>q.c[1]-p.c[1]), rows=[];
    a.forEach(o=>{ const L=rows[rows.length-1]; if(L&&Math.abs(L.y-o.c[1])<500) L.items.push(o); else rows.push({y:o.c[1],items:[o]}); });
    return [].concat(...rows.map(r=>r.items.sort((p,q)=>p.c[0]-q.c[0]).map(o=>o.u))); };
  const byLvl={}; UNITS.forEach(u=>{(byLvl[u.level]=byLvl[u.level]||[]).push(u);});
  Object.keys(byLvl).sort((a,b)=>LVL[b].idx-LVL[a].idx).forEach(l=>{
    const h=document.createElement('div'); h.className='uh'; h.textContent='الطابق '+LVL[l].name; up.appendChild(h);
    const row=document.createElement('div'); row.className='ur';
    planOrder(byLvl[l]).forEach(u=>{const b=document.createElement('button'); b.className='ub'; b.dataset.u=u.id; b.innerHTML=`<b>${u.name}</b><i>${u.bed!=null?u.bed+' غ.ن · ':''}${u.gross?u.gross+' م²':''}</i>`; b.onclick=()=>isolate(u.id); row.appendChild(b);});
    up.appendChild(row);
  });
})();
function unitElements(uid){const i=unitIndex[uid];const out=[];M.els.forEach((e,ei)=>{if(uidx(e.u)===i||uidx(e.u2)===i) out.push(ei);});return out;}
function makeMask(u){
  const W=34*20,H=23*20; const c=document.createElement('canvas'); c.width=W; c.height=H; const x=c.getContext('2d'); x.fillStyle='#000'; x.fillRect(0,0,W,H); x.fillStyle='#fff';
  (u.rects||[]).forEach(r=>{
    const px0=(r[0]/100-0.25)*20, px1=(r[2]/100+0.25)*20; const pz0=((-r[3]/100-0.25)-(-21))*20, pz1=((-r[1]/100+0.25)-(-21))*20; x.fillRect(px0,pz0,px1-px0,pz1-pz0);});
  /* flipY=false: the shader reads v = (z − maskBox.y) / maskBox.w, and the canvas is drawn with row = (z + 21)·20 from the top — with the default flipY=true the image was sampled upside down, so the
   structural slab / beam pieces kept by the isolation appeared in the MIRRORED place (the floor of the unit across the corridor) instead of under the isolated unit (owner 2026-10-08) */
  const t=new THREE.CanvasTexture(c); t.flipY=false; t.minFilter=THREE.LinearFilter; t.magFilter=THREE.LinearFilter; return t;
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

/* ---------- panel: ONE scrolling panel of collapsible sections (accordion) ---------- */
const ACC_KEY='c4acc';
function accState(){try{return JSON.parse(localStorage.getItem(ACC_KEY)||'null');}catch(e){return null;}}
function accSave(){try{localStorage.setItem(ACC_KEY,JSON.stringify([...document.querySelectorAll('.acc.on')].map(x=>x.dataset.sec)));}catch(e){}}
var openSec=function(id,opt){opt=opt||{}; const sec=document.querySelector('.acc[data-sec="'+id+'"]'); if(!sec) return; if(opt.only) document.querySelectorAll('.acc.on').forEach(x=>{if(x!==sec){x.classList.remove('on');x.querySelector('.acc-h').setAttribute('aria-expanded','false');}});
  sec.classList.add('on'); sec.querySelector('.acc-h').setAttribute('aria-expanded','true'); accSave();
  if(opt.scroll!==false) setTimeout(()=>{const c=$('acc'); if(c) c.scrollTo({top:sec.offsetTop-2,behavior:'smooth'});},30);
  if(id==='pSearch'&&opt.focus&&matchMedia('(pointer:fine)').matches) $('q').focus();};
var toggleSec=function(sec){const on=!sec.classList.contains('on'); sec.classList.toggle('on',on); sec.querySelector('.acc-h').setAttribute('aria-expanded',on?'true':'false'); accSave();
  if(on) setTimeout(()=>{const c=$('acc'); if(c&&sec.offsetTop<c.scrollTop) c.scrollTo({top:sec.offsetTop-2,behavior:'smooth'});},30);};
function syncNav(){document.querySelectorAll('#secnav button').forEach(b=>{const sec=document.querySelector('.acc[data-sec="'+b.dataset.go+'"]'); b.classList.toggle('on',!!(sec&&sec.classList.contains('on')));});}
const _openSec=openSec, _toggleSec=toggleSec; openSec=function(id,opt){_openSec(id,opt); syncNav();}; toggleSec=function(sec){_toggleSec(sec); syncNav();};
/* a chip is a switch (owner 2026-10-08): the first press opens its section and goes to it, the second press closes it — it no longer just scrolls to an open section so it has to be closed by hand */
document.querySelectorAll('#secnav button').forEach(b=>b.onclick=()=>{const sec=document.querySelector('.acc[data-sec="'+b.dataset.go+'"]'); if(!sec) return; if(sec.classList.contains('on')) toggleSec(sec); else openSec(b.dataset.go,{scroll:true,focus:true});});
document.querySelectorAll('.acc-h').forEach(h=>h.onclick=()=>toggleSec(h.parentElement));
syncNav();
{const st=accState(); if(st&&Array.isArray(st)){document.querySelectorAll('.acc').forEach(x=>{const on=st.includes(x.dataset.sec); x.classList.toggle('on',on); x.querySelector('.acc-h').setAttribute('aria-expanded',on?'true':'false');}); syncNav();}}

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
let qT=0; $('q').addEventListener('input',ev=>{clearTimeout(qT);qT=setTimeout(()=>runSearch(ev.target.value),130); if(ev.target.value.trim()) openSec('pSearch',{scroll:true});});
$('q').addEventListener('focus',()=>{if($('q').value.trim()) openSec('pSearch',{scroll:false});});
{const bu=$('accN_pUnits'); if(bu) bu.textContent=String(UNITS.length);}   // the issue centre (src/issues.js) writes its own badge
$('qres').addEventListener('click',ev=>{const r=ev.target.closest('.res'); if(!r) return; document.querySelectorAll('#qres .res.sel').forEach(x=>x.classList.remove('sel')); r.classList.add('sel'); focusEl(+r.dataset.i);});
$('qinfo').addEventListener('click',ev=>{if(ev.target.id!=='qhl') return; lastHits.forEach(ensureVisible); select(-1); clearHL(); addHL(lastHits,HL_BLUE,lastHits.length<300); flyToBox(bboxOf(lastHits)); document.body.classList.remove('panel-open');});
runSearch('');

/* ---------- materials legend + finishes vs BOQ ---------- */
let matSel=null;
function buildMat(){
  const byMat={},byFin={}; M.els.forEach((e,i)=>{const m=e.m||'conc'; (byMat[m]=byMat[m]||[]).push(i); ((e.a&&e.a.fin)||[]).forEach(f=>(byFin[f]=byFin[f]||[]).push(i));});
  let h=`<h3>دليل المواد (اضغط لإبراز كل عناصرها)</h3>`;
  Object.keys(MATS).filter(k=>byMat[k]&&!k.startsWith('fin_')).sort((a,b)=>byMat[b].length-byMat[a].length).forEach(k=>{const m=MATS[k]; h+=`<div class=mrow data-mat="${esc(k)}"><span class=sw style="background:${m.color};${m.opacity?'opacity:'+Math.max(m.opacity,0.45):''}"></span><div><b>${esc(m.name)}</b><small>${m.code?esc(m.code):''}</small></div><span class=n>${byMat[k].length}</span></div>`;});
  ['CSP-2','CSP-3','CSP-4'].forEach(c=>{ (byFin[c]||[]).forEach(i=>{ (byFin.CSP=byFin.CSP||[]).push(i); }); });   // BOQ prices the three car-park systems as one item «CSP»
  const fins=Object.keys(M.fin||{}).filter(f=>byFin[f]||(M.finq&&M.finq[f]));
  if(fins.length){
    h+=`<h3>رموز التشطيب (A500) ومطابقة الكميات مع BOQ</h3><div class=note>كمية BOQ مأخوذة من جدول الكميات. «النموذج» مساحة محسوبة من هندسة العناصر لما أمكن (أرضيات وأسقف)؛ الفروق تحتاج مراجعة ولا تعني خطأ بالضرورة.</div>`;
    fins.sort((a,b)=>a.localeCompare(b,'en',{numeric:true})).forEach(f=>{const d=M.fin[f],q=M.finq&&M.finq[f]; const n=(byFin[f]||[]).length;
      const own=d[4]!=null&&d[4]>0; let qr=`<div class=qrow><span>BOQ: ${own?`<b>${d[4]} ${esc(d[3])}</b>`:'<b>ضمن بند «CSP» الواحد</b>'}</span>`;
      if(q&&q.area!=null){qr+=`<span>النموذج: <b>${q.area.toLocaleString('en')} م²</b>${q.tower!=null&&q.tower!==q.area?` <small>(الطوابق 1–5: ${q.tower.toLocaleString('en')})</small>`:''}</span>`; if(own){const df=(q.area-d[4])/d[4]*100; qr+=`<span class="${Math.abs(df)>10?'bad':'ok'}"><b>${df>0?'+':''}${df.toFixed(0)}%</b></span>`;}} else qr+=`<span>النموذج: <b>—</b></span>`;
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
    selIdx=-1; hideInfo(); clearHL(); addHL(vis.length?vis:idx,HL_BLUE,idx.length<250); if(!vis.length) toast('عناصر هذه المادة مخفية حاليًا — فعّل أقسامها أو طوابقها'); else flyToBox(bboxOf(vis)); document.body.classList.remove('panel-open');};
}
buildMat();

/* ---------- clash list ---------- */
function setGhost(on,op,levels,samples){focusGhost=!!on; if(op!==undefined) focusOp=op; focusLevels=on?(levels||null):null; focusSamples=!!(on&&samples); applyVis();}
function buildClash(){
  if(!window.initClash){const cb=$('clashBox'); if(cb) cb.innerHTML='<div class=muted>وحدة التعارضات غير محمّلة.</div>'; return;}
  CLASH=initClash({M,THREE,scene,camera,controls,$,esc,LVL,UNITS,wake,flyTo,ensureVisible,select,highlight,addHL,clearHL,toast,setGhost,focusEl,bboxOf});
}
buildClash();

/* ---------- lifts: optional car motion (illustrative; speed and dwell are NOT from the documents) ---------- */
const lifts=[]; let liftSim=false;
function parseStops(s){const out=[]; String(s||'').split(',').forEach(p=>{p=p.trim(); const m=p.match(/^(\d+)\s*[–-]\s*(\d+)$/); if(m){for(let i=+m[1];i<=+m[2];i++) out.push(String(i));} else if(p) out.push(p);}); return out.filter(id=>LVL[id]);}
(function(){const byCar={}; M.els.forEach((e,ei)=>{if(e.t!=='lift_car') return; const G=groups[elRange[ei].gk]; if(!G) return; const key=(e.a&&e.a.car)||e.id;
  let L=byCar[key]; if(!L){const st=parseStops(e.a&&e.a.stops); if(st.length<2) return; const base=LVL[e.l].ffl; const idx=Math.max(0,st.indexOf(e.l));
    L=byCar[key]={Gs:[],base,ffl:st.map(id=>LVL[id].ffl),idx,dir:idx>=st.length-1?-1:1,dy:0,wait:0,last:null}; lifts.push(L);}
  if(!L.Gs.includes(G)) L.Gs.push(G);});
  if(lifts.length) $('liftRow').style.display='flex';})();
function stepLifts(dt){lifts.forEach(L=>{
  if(L.wait>0){L.wait-=dt;return;} const goal=L.ffl[L.idx]-L.base,d=goal-L.dy,st=1.6*dt;
  if(Math.abs(d)<=st){L.dy=goal;L.wait=1.8;L.idx+=L.dir; if(L.idx>=L.ffl.length||L.idx<0){L.dir*=-1;L.idx+=2*L.dir;}} else L.dy+=Math.sign(d)*st;
  L.Gs.forEach(G=>{G.dy=L.dy; const lv=LVL[G.lvl]; G.mesh.position.y=explode*(lv?lv.idx:0)+L.dy;});});}
$('liftBtn').onclick=()=>{liftSim=!liftSim; $('liftBtn').textContent=liftSim?'إيقاف':'تشغيل'; $('liftBtn').classList.toggle('on',liftSim); if(liftSim){clearHL(); toast('محاكاة توضيحية: السرعة وزمن التوقف غير واردين في المستندات',4200);} else {lifts.forEach(L=>{L.dy=0;L.Gs.forEach(G=>{G.dy=0;});L.idx=Math.max(0,L.ffl.findIndex(f=>Math.abs(f-L.base)<1e-6));L.wait=0;}); applyVis();}};

/* ---------- samples: swap the plain proxy for the detailed sample when the camera is close (src/detail.js + samples.json) ---------- */
if(window.SampleLOD&&window.__SAMPLES__){
  LOD=new SampleLOD({M,scene,camera,groups,elRange,elBB,wake,mono:U.mono,exploded:()=>explode!==0,liftRunning:()=>liftSim,
    unitVisible:u=>U.lensOn.value<0.5&&u.eis.every(ei=>{const G=groups[elRange[ei].gk]; return elVisible(ei)&&effOpacity(G,focusSamples)/(G.matBase.userData.baseOpacity||1)>0.95;})});   // detailed samples keep their own colours, so they are off while a lens colours / isolates the model
  const chk=$('lodChk'); if(chk){ let saved=null; try{saved=localStorage.getItem('c4lod');}catch(e){} if(saved==='0'){chk.checked=false; LOD.setEnabled(false);}
    const rb=$('rebarChk'); if(rb){ let sv=null; try{sv=localStorage.getItem('c4rebar');}catch(e){} if(sv==='1'){rb.checked=true; LOD.setRebar(true);}
      rb.onchange=ev=>{LOD.setRebar(ev.target.checked); try{localStorage.setItem('c4rebar',ev.target.checked?'1':'0');}catch(e){} toast(ev.target.checked?'عند التقريب من الأعمدة والجسور والجدران يظهر حديد التسليح داخل الخرسانة الشفافة':'الخرسانة تبقى مصمتة عند التقريب (حديد التسليح مخفي)');};}
    chk.onchange=ev=>{LOD.setEnabled(ev.target.checked); try{localStorage.setItem('c4lod',ev.target.checked?'1':'0');}catch(e){} toast(ev.target.checked?'عند التقريب يُستبدل المجسم المبسّط بعينة تفصيلية':'عُطّل استبدال العينات التفصيلية');}; }
}
if(window.initThumbs) window.THUMBS=initThumbs({M,THREE,LOD,groups,elRange,elBB,esc});   // the model's own drawing of a component (src/thumbs.js)
if(window.initSamplesUI&&LOD) initSamplesUI({M,THREE,$,esc,LOD,flyTo,wake,toast,ensureVisible,camera,setGhost,elBB}); else if($('pSamp')) $('pSamp').innerHTML='<div class=muted>مكتبة العينات غير محمّلة.</div>';
/* ---------- toolbar: modes, views, fullscreen, performance, help ---------- */
document.querySelectorAll('#modes button').forEach(b=>b.onclick=()=>controls.setMode(b.dataset.m));
/* mode buttons: shown on mouse devices, hidden on touch tablets (gestures replace them); «⋯» menu switches them */
function setModes(on,noSave){document.body.classList.toggle('modes-on',!!on); $('btnModes').classList.toggle('on',!!on); if(!on) controls.setMode('rotate'); if(!noSave){try{localStorage.setItem('c4modes',on?'1':'0');}catch(e){}}}
{let sv=null; try{sv=localStorage.getItem('c4modes');}catch(e){} setModes(sv===null?!matchMedia('(pointer:coarse)').matches:sv==='1',true);}
$('btnModes').onclick=()=>setModes(!document.body.classList.contains('modes-on'));
{const pc=$('pinchChk'); let sv=null; try{sv=localStorage.getItem('c4pinch2');}catch(e){} controls.pinchInZooms=sv==='1'; pc.checked=controls.pinchInZooms;   // c4pinch2: the old key (c4pinch) held the previous default and is ignored
  pc.onchange=ev=>{controls.pinchInZooms=ev.target.checked; try{localStorage.setItem('c4pinch2',ev.target.checked?'1':'0');}catch(e){} toast(ev.target.checked?'اللمس: تقريب الإصبعين من بعضهما = تقريب (عكس المعتاد)':'اللمس: تباعد الإصبعين = تقريب (الاتجاه المعتاد)');};}
controls.addEventListener('mode',ev=>{document.querySelectorAll('#modes button').forEach(b=>b.classList.toggle('on',b.dataset.m===ev.mode));wake();});
const MENU_IDS=['viewMenu','moreMenu'];
function closeMenus(except){MENU_IDS.forEach(m=>{if(m!==except) $(m).classList.remove('on');});}
window.addEventListener('resize',()=>closeMenus());
function toggleMenu(mid,bid){const m=$(mid),b=$(bid); const on=!m.classList.contains('on'); closeMenus(on?mid:null); m.classList.toggle('on',on);
  if(on){const vr=$('view').getBoundingClientRect(), br=b.getBoundingClientRect(); m.style.top=Math.round(Math.max(br.bottom,$('bar').getBoundingClientRect().bottom)-vr.top+6)+'px'; m.style.right=Math.max(8,Math.min(Math.round(vr.right-br.right),Math.round(vr.width-m.offsetWidth-8)))+'px';}}
$('btnViews').onclick=ev=>{ev.stopPropagation();toggleMenu('viewMenu','btnViews');};
$('btnMore').onclick=ev=>{ev.stopPropagation();toggleMenu('moreMenu','btnMore');};
$('viewMenu').onclick=ev=>{const b=ev.target.closest('button'); if(!b) return;
  if(b.dataset.v){viewPreset(b.dataset.v); closeMenus(); return;}
  if(b.dataset.lens){setLens(b.dataset.lens); closeMenus(); return;}
  if(b.dataset.l){const l=b.dataset.l; if(l==='lamps'){lampsPinned=!lightsOn; setLightsOn(!lightsOn);} else {applyPreset(l);} closeMenus();}};
$('moreMenu').onclick=ev=>{if(ev.target.closest('button')) setTimeout(closeMenus,0);};
document.addEventListener('click',ev=>{if(!ev.target.closest('#viewMenu,#moreMenu,#btnViews,#btnMore')) closeMenus();});
const FS_OK=document.fullscreenEnabled||document.webkitFullscreenEnabled; if(!FS_OK) $('btnFs').style.display='none';
$('btnFs').onclick=()=>{const d=document,el=d.documentElement; if(d.fullscreenElement||d.webkitFullscreenElement){(d.exitFullscreen||d.webkitExitFullscreen).call(d);} else (el.requestFullscreen||el.webkitRequestFullscreen).call(el);};
document.addEventListener('fullscreenchange',()=>{$('btnFs').classList.toggle('on',!!document.fullscreenElement);setTimeout(resize,150);});
function setPerf(on,auto){perfMode=on; renderer.setPixelRatio(ratioFor()); resize(); if(window.LOOK) window.LOOK.set(window.LOOK.white?'white':'mat',{force:true,quiet:true}); $('btnPerf').classList.toggle('on',on); $('btnPerf').setAttribute('aria-pressed',on); $('perfChk').checked=on; try{localStorage.setItem('c4perf',on?'1':'0');}catch(e){} if(auto) toast('فُعّل وضع الأداء تلقائيًا لسلاسة العرض (يمكن إيقافه من زر «أداء»)',4500);}
$('btnPerf').onclick=()=>setPerf(!perfMode); $('perfChk').onchange=ev=>setPerf(ev.target.checked);
$('ptrKind').onchange=ev=>{controls.pointerKind=ev.target.value;};
const helpOpen=on=>$('help').classList.toggle('on',on); $('btnHelp').onclick=()=>helpOpen(true); $('helpBtn2').onclick=()=>helpOpen(true); $('helpClose').onclick=()=>helpOpen(false); $('help').onclick=ev=>{if(ev.target===$('help')) helpOpen(false);};
window.addEventListener('keydown',ev=>{ if(ev.key==='Escape'){ if($('help').classList.contains('on')) helpOpen(false); else if(window.MEASURE&&window.MEASURE.esc&&window.MEASURE.esc()){} else{ closeMenus(); if(window.TOURS&&TOURS.active) TOURS.stop(); else if(ISSUES&&ISSUES.active) ISSUES.close(); if(selIdx>=0) select(-1); document.body.classList.remove('panel-open'); } } });
function setDock(off,noSave){document.body.classList.toggle('dock-off',!!off); const b=$('dockBtn'); b.textContent=off?'\u2039':'\u203A'; b.setAttribute('aria-expanded',off?'false':'true'); if(!noSave){try{localStorage.setItem('c4dock',off?'1':'0');}catch(e){}} refreshInfo(); setTimeout(resize,40);}
$('dockBtn').onclick=()=>setDock(!document.body.classList.contains('dock-off'));
{let sv=null; try{sv=localStorage.getItem('c4dock');}catch(e){} if(sv==='1') setDock(true,true);}
DESK.addEventListener?DESK.addEventListener('change',refreshInfo):DESK.addListener(refreshInfo);
$('fab').onclick=()=>document.body.classList.add('panel-open'); $('panelClose').onclick=()=>document.body.classList.remove('panel-open');


/* ---------- lighting: day / dusk / night presets and "lights on" (emissive fixtures + glow sprites + a few real point lights that follow the view) ---------- */
const LP={
  day:{bg:0xe9edf2,sky:null,hs:0xffffff,hg:0x8a8f98,hi:0.85,sc:0xffffff,si:0.75,s2:0.25,sp:[-40,70,30]},
  dusk:{bg:0xf0b78f,sky:['#34477a','#b2708b','#f2b27f','#f6d8a8'],hs:0xffdcc0,hg:0x6a5560,hi:0.62,sc:0xffa968,si:0.62,s2:0.14,sp:[-70,18,-35]},
  night:{bg:0x0a0f1d,sky:['#03060f','#0b1428','#18284a','#26385f'],hs:0x5f74a8,hg:0x141829,hi:0.34,sc:0x8095d0,si:0.26,s2:0.06,sp:[-30,60,20]},
};
function skyTex(stops){const c=document.createElement('canvas');c.width=2;c.height=256;const g=c.getContext('2d');const gr=g.createLinearGradient(0,0,0,256);stops.forEach((s,i)=>gr.addColorStop(i/(stops.length-1),s));g.fillStyle=gr;g.fillRect(0,0,2,256);return new THREE.CanvasTexture(c);}
const PLIGHTS=[]; for(let i=0;i<4;i++){const l=new THREE.PointLight(0xffd9a6,0,6.5,1.4); l.visible=false; scene.add(l); PLIGHTS.push(l);}
function buildGlow(){
  const pos=[],eis=[];
  M.els.forEach((e,ei)=>{const m=MATS[e.m]; if(!(m&&m.night&&m.night.glow)) return; const b=elBB.subarray(ei*6,ei*6+6); pos.push((b[0]+b[3])/2,(b[1]+b[4])/2-0.03,(b[2]+b[5])/2); eis.push(ei);});
  const c=document.createElement('canvas');c.width=c.height=64;const g=c.getContext('2d');const gr=g.createRadialGradient(32,32,0,32,32,32);gr.addColorStop(0,'rgba(255,238,200,1)');gr.addColorStop(0.18,'rgba(255,214,150,0.55)');gr.addColorStop(0.5,'rgba(255,190,110,0.14)');gr.addColorStop(1,'rgba(255,180,100,0)');g.fillStyle=gr;g.fillRect(0,0,64,64);
  const geo=new THREE.BufferGeometry(); const P=new Float32Array(pos), C=new Float32Array(pos.length).fill(1);
  geo.setAttribute('position',new THREE.BufferAttribute(P.slice(),3)); geo.setAttribute('color',new THREE.BufferAttribute(C,3));
  const mat=new THREE.PointsMaterial({size:0.95,map:new THREE.CanvasTexture(c),vertexColors:true,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,sizeAttenuation:true});
  const pts=new THREE.Points(geo,mat); pts.frustumCulled=false; pts.visible=false; scene.add(pts);
  return {pts,base:P,eis};
}
function updateGlow(){
  if(!glow||!lightsOn) return; const a=glow.pts.geometry.attributes; const P=a.position.array,C=a.color.array;
  for(let i=0;i<glow.eis.length;i++){const ei=glow.eis[i]; const v=elVisible(ei)?1:0; C[i*3]=C[i*3+1]=C[i*3+2]=v; P[i*3]=glow.base[i*3]; P[i*3+1]=glow.base[i*3+1]+offOf(ei); P[i*3+2]=glow.base[i*3+2];}
  a.position.needsUpdate=true; a.color.needsUpdate=true; wake();
}
function setLightsOn(on){
  lightsOn=on;
  for(const k in groups){const G=groups[k]; const m=MATS[G.mat]; if(!G.matBase||!m||!m.night) continue; G.matBase.emissive.set(on?m.night.c:0x000000); G.matBase.emissiveIntensity=on?m.night.i:0;}
  if(on&&!glow) glow=buildGlow();
  if(glow) glow.pts.visible=on;
  PLIGHTS.forEach(l=>l.visible=on); lastPL=0;
  $('lampsBtn').classList.toggle('on',on); updateGlow(); wake();
}
function applyPreset(name){
  lightPreset=name; const P=LP[name];
  if(P.sky){const t=skyTex(P.sky); if(scene.background&&scene.background.isTexture) scene.background.dispose(); scene.background=t;} else scene.background=new THREE.Color(P.bg);
  hemi.color.set(P.hs); hemi.groundColor.set(P.hg); hemi.intensity=P.hi; sun.color.set(P.sc); sun.intensity=P.si; sun2.intensity=P.s2; sun.position.set(P.sp[0],P.sp[1],P.sp[2]);
  document.querySelectorAll('#viewMenu button[data-l]').forEach(b=>{if(b.dataset.l!=='lamps') b.classList.toggle('on',b.dataset.l===name);});
  if(name!=='day'&&!lightsOn) setLightsOn(true); else if(name==='day'&&lightsOn&&!lampsPinned) setLightsOn(false);
  if(window.LOOK){ window.LOOK.afterPreset(); if(window.LOOK.setFog) window.LOOK.setFog(); }
  wake();
}
function stepPLights(now){
  if(!lightsOn||!glow||now-lastPL<350) return; lastPL=now; const t=controls.target; const P=glow.base; const best=[];
  for(let i=0;i<glow.eis.length;i++){ if(!elVisible(glow.eis[i])) continue; const dx=P[i*3]-t.x,dy=P[i*3+1]+offOf(glow.eis[i])-t.y,dz=P[i*3+2]-t.z; const d=dx*dx+dy*dy+dz*dz; if(d>400) continue; if(best.length<PLIGHTS.length||d<best[best.length-1][0]){best.push([d,i]); best.sort((u,v)=>u[0]-v[0]); if(best.length>PLIGHTS.length) best.pop();} }
  PLIGHTS.forEach((l,k)=>{const b=best[k]; if(!b){l.intensity=0;return;} const i=b[1]; l.position.set(P[i*3],P[i*3+1]+offOf(glow.eis[i])-0.1,P[i*3+2]); l.intensity=lightPreset==='day'?0.35:1.15;});
  wake(300);
}
applyPreset('day');

/* ---------- loop (renders only while something changes: saves battery on phones) ---------- */
let frames=0,tLast=performance.now(),tPrev=performance.now(),perfProbe={t0:0,f:0,done:false};
function loop(){requestAnimationFrame(loop);
  const now=performance.now(),dt=Math.min(0.1,(now-tPrev)/1000); tPrev=now;
  if(fly){stepFly();wake(300);}
  stepInset(dt);
  if(controls.update()) wake(300);
  if(liftSim&&lifts.length){stepLifts(dt);wake(300);}
  if(LOD&&LOD.update()) wake(300);
  stepPLights(now); stepUnder();
  if(CLASH) CLASH.frame(now,dt);
  if(ISSUES) ISSUES.frame(now,dt);
  if(window.NOTES) window.NOTES.frame();
  if(window.MEASURE) window.MEASURE.frame();
  if(window.SECTIONS) window.SECTIONS.frame();
  if(now<awakeUntil){ if(window.LOOK) window.LOOK.render(); else renderer.render(scene,camera); frames++;
    if(!perfProbe.done){ if(!perfProbe.t0&&now>0) {perfProbe.t0=now+900;} if(now>perfProbe.t0){perfProbe.f++; if(now>perfProbe.t0+2200){perfProbe.done=true; const fps=perfProbe.f*1000/(now-perfProbe.t0); let saved=null; try{saved=localStorage.getItem('c4perf');}catch(e){} if(saved===null&&fps<18&&!perfMode) setPerf(true,true);}}}
  }
  if(now-tLast>1000){$('fps').textContent=frames?Math.round(frames*1000/(now-tLast))+' fps · ':'';frames=0;tLast=now;}
}
{let saved=null; try{saved=localStorage.getItem('c4perf');}catch(e){} if(saved==='1') setPerf(true,false); else if(saved==='0') perfProbe.done=true;}
wake(4200); loop(); applyVis();
{const L=$('loader'); if(L){L.classList.add('off'); setTimeout(()=>L.remove(),600);} }
if(window.initLens) LENS=initLens({M,THREE,groups,elRange,U,applyVis,wake,CATS,LAYER,LVL,$,esc,setLook:m=>{ if(window.LOOK) window.LOOK.set(m); }});
/* overview hub (src/hub.js): tiles are doors to lenses / the issue centre / a single level */
function onlyLevel(id){ M.levels.forEach(l=>setLvlVis(l.id,l.id===id)); applyVis(); const idx=[]; M.els.forEach((e,i)=>{if(e.l===id&&e.c[0]!=='A'||e.l===id&&e.c==='A.wall') idx.push(i);}); if(idx.length) flyToBox(bboxOf(idx),[-0.55,0.75,0.65]); document.body.classList.remove('panel-open'); toast('عُزل الطابق «'+LVL[id].name+'» — «إظهار كل الطوابق» للعودة',2600); }
function showAllLevels(){ M.levels.forEach(l=>setLvlVis(l.id,true)); applyVis(); goHome(); }
/* guided tours (src/tours.js): a stop = visibility + lens + highlight + camera + caption */
if(window.initTours) window.TOURS=initTours({M,THREE,camera,controls,$,esc,UNITS,CATS,wake,flyTo,flyToBox,bboxOf,highlight,clearHL,setLens,LENS,viewPreset,isolate,exitIso,isoActive:()=>isoUnit!==null,applyVis,setLvlVis,setCatVis,lvlVis,catVis,setGhost,select,toast,closeMenus});
if(window.initHub) initHub({M,$,esc,LVL,setLens,openSec,onlyLevel,showAllLevels,PAL:window.LENS_PAL,toast});
/* issue centre (src/issues.js): clashes and best-guess decisions with one shared design */
if(window.initIssues){ ISSUES=initIssues({M,THREE,scene,camera,controls,renderer,$,esc,normAr,LVL,LAYER,CATS,TYPES,UNITS,wake,flyTo,flyToBox,ensureVisible,select,highlight,addHL,clearHL,toast,setGhost,focusEl,bboxOf,setLens,openSec,onlyLevel,showAllLevels,elVisible,levelVisible:l=>lvlVis[l]!==false,exploded:()=>explode!==0,showDrawer,hideDrawer,CLASH,LENS,PAL:window.LENS_PAL,PlanMap:window.PlanMap}); window.ISSUES=ISSUES; }
/* white / grey look with soft shadows and depth (src/look.js) */
if(window.initLook) window.LOOK=initLook({THREE,renderer,scene,camera,U,groups,hemi,sun,sun2,wake,toast,$,LP,getPreset:()=>lightPreset,isPerf:()=>perfMode,clipActive:()=>clipYv<999||clipXv<999,getLens:()=>LENS,lodMats:()=>(LOD&&LOD.mats)?Object.keys(LOD.mats).map(k=>LOD.mats[k]):[]});
/* saved views + shareable link (src/views.js) */
if(window.initViews) window.VIEWS=initViews({THREE,renderer,camera,controls,$,esc,wake,toast,M,CATS,lvlVis,catVis,UNITS,flyTo,applyVis,setLvlVis,setCatVis,isolate,exitIso,getIso:()=>isoUnit!==null?UNITS[isoUnit].id:null,getLens:()=>LENS,setLens,getPreset:()=>lightPreset,applyPreset,
  getClip:()=>({y:+$('clipY').value,x:+$('clipX').value}),setClip:(y,x)=>{ $('clipY').value=y; $('clipX').value=x; $('clipY').dispatchEvent(new Event('input')); $('clipX').dispatchEvent(new Event('input')); },
  getExplode:()=>+$('expl').value,setExplode:v=>{ $('expl').value=v; $('expl').dispatchEvent(new Event('input')); },selIdxOf:()=>selIdx,select,render:()=>{ if(window.LOOK) window.LOOK.render(); else renderer.render(scene,camera); }});
/* measure tool (src/measure.js) */
if(window.initMeasure) window.MEASURE=initMeasure({THREE,scene,camera,renderer,$,pickHit,wake,toast,esc});
/* visible section planes + plan-cut chips (src/sections.js) */
if(window.initSections) window.SECTIONS=initSections({THREE,scene,camera,$,M,wake,viewPreset,elBB});
/* owner's notes + hide (src/notes.js) */
if(window.initNotes){ window.NOTES=initNotes({M,THREE,scene,camera,renderer,$,esc,LVL,UNITS,TYPES,CATS,wake,toast,bboxOf,grpMap,userHidden:uHid,setUserHidden,sel:()=>({idx:selIdx,set:selSet}),clearHL,highlight,focusEl,flyTo,levelVisible:l=>lvlVis[l]!==false,openSec}); }
$('stat').textContent=M.els.length.toLocaleString('en')+' عنصر';
/* system life-cycle tests (src/life.js, data: M.lifecycle from pipeline/lifecycle.py) */
if(window.initLife) window.LIFE=initLife({M,$,esc,LVL,UNITS,TYPES,setLens,LENS,wake,flyToBox,bboxOf,highlight,clearHL,select,toast,grpMap,openSec});
/* first-visit hint (src/hint.js) */
if(window.initHint) window.HINT=initHint({$,wake});
window.__dbg={setLens,get LENS(){return LENS;},setLightsOn,applyPreset,LOD,get CLASH(){return CLASH;},get ISSUES(){return ISSUES;},get NOTES(){return window.NOTES;},get LOOK(){return window.LOOK;},get MEASURE(){return window.MEASURE;},get SECTIONS(){return window.SECTIONS;},get LIFE(){return window.LIFE;},get VIEWS(){return window.VIEWS;},uHid,setUserHidden,get selIdx(){return selIdx;},flyToBox,bboxOf,flyTo,scene,camera,controls,groups,renderer,select,isolate,pick,M,focusEl,viewPreset,setPerf,layerOp,catOp,applyVis,runSearch,wake,get perfMode(){return perfMode;},get flying(){return !!fly;},pickHit,get awake(){return awakeUntil;}};
