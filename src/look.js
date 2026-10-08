/* ===== Look: «ألوان المواد» (the real material colours) or «أبيض ورمادي» (a white / grey clay model) — owner 2026-10-08 =====
   «اللون الأصفر غير جميل أبدًا … أضف وضعًا تظهر فيه الألوان معزولة بالأبيض ودرجات الرمادي مع التظليل والعمق، وإذا اخترت قسمًا يُلوَّن هذا القسم فقط».
   What the white look is made of (researched: clay renders are one neutral grey under soft even light; ambient occlusion / eye-dome lighting give depth to untextured models; a frozen sun shadow map costs one pass per change):
   1. MONO     — shader uniform U.mono (src/app.js patch + the detail materials): every material becomes a grey in 0.50–0.97 by its own luminance, so windows / frames / floors keep their relative tone;
                 the lens (src/lens.js) colours only the classes the owner chose, everything else stays white / grey.
   2. SHADOWS  — the sun casts a soft shadow map (2048², PCF-soft) that is NOT redrawn every frame: it is rebuilt only when something that casts shadows changes (visibility, lens, hide, explode, lighting
                 preset); glass does not cast; hidden elements are culled by the same flags as the main pass (customDepthMaterial); while a section clip is on, shadows are suspended (they would show the removed part).
   3. DEPTH    — a screen-space pass over the depth buffer: eye-dome lighting (dark halo behind every depth step = silhouettes and edges) + a small depth-only ambient occlusion (creases) + FXAA, drawn after
                 the scene has been rendered into a render target with a depth texture (WebGL2 or WEBGL_depth_texture). Without that support the look falls back to MONO + shadows.
   4. FOG      — a very light distance fade toward the sky colour (depth cue).
   Everything here is off in the default «مواد» look, so the default experience and its cost do not change.  ES2018 style. */
(function(){
'use strict';
function initLook(ctx){
  const {THREE,renderer,scene,camera,U,groups,hemi,sun,sun2,wake,toast,$,LP,getPreset,isPerf,clipActive,getLens}=ctx;
  let white=false, shadowsOn=true, edgesOn=true, dirtyShadow=true, postOk=null;
  try{ const s=JSON.parse(localStorage.getItem('c4look')||'null'); if(s){ white=!!s.w; shadowsOn=s.s!==0; edgesOn=s.e!==0; } }catch(e){}
  const save=()=>{ try{ localStorage.setItem('c4look',JSON.stringify({w:white?1:0,s:shadowsOn?1:0,e:edgesOn?1:0})); }catch(e){} };
  const TG=new THREE.Vector3(18,8,-17);                      // centre of the building (shadow frustum)
  const v2=new THREE.Vector2();

  /* ---------------- shadows ---------------- */
  const depthMat=new THREE.MeshDepthMaterial({depthPacking:THREE.RGBADepthPacking});
  depthMat.onBeforeCompile=sh=>{
    sh.uniforms.uIso=U.iso; sh.uniforms.uMaskOn=U.maskOn; sh.uniforms.uMask=U.mask; sh.uniforms.uMaskBox=U.maskBox; sh.uniforms.uLensOn=U.lensOn;
    sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\nattribute vec2 aUnit; attribute float aClip; attribute float aHide; attribute float aLens; uniform float uLensOn; varying vec2 vUnit; varying float vClip; varying vec3 vWPos;')
      .replace('#include <begin_vertex>','#include <begin_vertex>\nvUnit=aUnit; vClip=aClip; vWPos=(modelMatrix*vec4(transformed,1.0)).xyz;')
      .replace('#include <project_vertex>','#include <project_vertex>\n if(mod(floor(aHide*0.5),2.0)>0.5 || (uLensOn>0.5 && aLens>254.5)) gl_Position=vec4(2.0,2.0,2.0,1.0);');   // owner-hidden / lens-hidden never cast (the detail swap bit stays a caster)
    sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\nvarying vec2 vUnit; varying float vClip; varying vec3 vWPos; uniform float uIso; uniform float uMaskOn; uniform sampler2D uMask; uniform vec4 uMaskBox;')
      .replace('void main() {','void main() {\n if(uIso>-0.5 && vClip<0.5 && abs(vUnit.x-uIso)>0.5 && abs(vUnit.y-uIso)>0.5) discard;\n if(uIso>-0.5 && vClip>0.5){ vec2 uv=(vWPos.xz-uMaskBox.xy)/uMaskBox.zw; if(uv.x<0.||uv.x>1.||uv.y<0.||uv.y>1.||texture2D(uMask,uv).r<0.5) discard; }');
  };
  depthMat.customProgramCacheKey=()=>'bimdepth';
  renderer.shadowMap.type=THREE.PCFSoftShadowMap; renderer.shadowMap.autoUpdate=false;
  sun.shadow.mapSize.set(2048,2048); { const c=sun.shadow.camera; c.left=-62; c.right=62; c.top=62; c.bottom=-62; c.near=4; c.far=280; c.updateProjectionMatrix(); }
  sun.shadow.bias=-0.0005; sun.shadow.normalBias=0.07; scene.add(sun.target);
  for(const k in groups){ const G=groups[k]; if(!G.mesh) continue; G.mesh.castShadow=!(G.matBase&&(G.matBase.userData.baseOpacity||1)<1); G.mesh.receiveShadow=true; G.mesh.customDepthMaterial=depthMat; }
  const matsUpdate=()=>{ for(const k in groups){ const G=groups[k]; if(G.matBase) G.matBase.needsUpdate=true; } if(ctx.lodMats) ctx.lodMats().forEach(m=>{m.needsUpdate=true;}); };
  const shadowActive=()=>white&&shadowsOn&&!isPerf()&&!clipActive();

  /* ---------------- lights, fog ---------------- */
  function lights(){
    const name=getPreset(), P=LP[name]; if(!P) return; const w=white;
    hemi.color.set(P.hs); hemi.groundColor.set(w&&name==='day'?0xa7afb9:P.hg); hemi.intensity=P.hi*(w&&name==='day'?0.82:1);
    sun.color.set(P.sc); sun.intensity=P.si*(w&&name==='day'&&shadowsOn?1.32:1); sun2.intensity=P.s2*(w&&name==='day'?0.8:1);
    const d=new THREE.Vector3(P.sp[0],P.sp[1],P.sp[2]).normalize();
    if(w&&shadowsOn){ sun.target.position.copy(TG); sun.position.copy(TG).addScaledVector(d,120); }   // same direction, but the shadow frustum is centred on the building
    else { sun.target.position.set(0,0,0); sun.position.set(P.sp[0],P.sp[1],P.sp[2]); }
    sun.target.updateMatrixWorld(); dirtyShadow=true; wake();
  }
  function fog(){
    if(white&&getPreset()==='day'){ const c=new THREE.Color(0xe9edf2); if(!scene.fog) scene.fog=new THREE.Fog(c,150,520); else { scene.fog.color.copy(c); scene.fog.near=150; scene.fog.far=520; } }
    else if(scene.fog) scene.fog=null;
  }

  /* ---------------- post pass: eye-dome lighting + depth ambient occlusion + FXAA ---------------- */
  const post={rt:null,rt2:null,qs:null,qc:null,edl:null,fxaa:null,w:0,h:0};
  const QV='varying vec2 vUv; void main(){ vUv=uv; gl_Position=vec4(position.xy,0.0,1.0); }';
  const EDL_F=`precision highp float; varying vec2 vUv; uniform sampler2D tColor; uniform sampler2D tDepth; uniform vec2 uTexel; uniform float uNear; uniform float uFar; uniform float uEdl; uniform float uAo; uniform float uRad;
    float lin(float d){ float z=d*2.0-1.0; return 2.0*uNear*uFar/(uFar+uNear-z*(uFar-uNear)); }
    void main(){
      vec4 c=texture2D(tColor,vUv); float d=texture2D(tDepth,vUv).r;
      if(d>0.99995){ gl_FragColor=c; return; }
      float z=lin(d), lz=log2(z), edl=0.0, ao=0.0;
      for(int i=0;i<8;i++){
        float a=float(i)*0.7853982; vec2 o=vec2(cos(a),sin(a))*uRad*uTexel;
        float dn=texture2D(tDepth,vUv+o).r; float zn=dn>0.99995?z*3.0:lin(dn);
        edl+=max(0.0,lz-log2(zn));
        float dz=z-zn; ao+=smoothstep(0.03,0.30,dz)*(1.0-smoothstep(0.9,3.0,dz));
        vec2 o2=o*2.6; float dn2=texture2D(tDepth,vUv+o2).r; float zn2=dn2>0.99995?z*3.0:lin(dn2); float dz2=z-zn2; ao+=0.7*smoothstep(0.05,0.45,dz2)*(1.0-smoothstep(1.4,4.0,dz2));
      }
      float shade=exp(-edl*uEdl)*(1.0-uAo*clamp(ao/13.6,0.0,1.0));
      gl_FragColor=vec4(c.rgb*shade,c.a);
    }`;
  const FXAA_F=`precision highp float; varying vec2 vUv; uniform sampler2D tColor; uniform vec2 uTexel;
    void main(){
      vec3 rgbNW=texture2D(tColor,vUv+vec2(-1.0,-1.0)*uTexel).rgb; vec3 rgbNE=texture2D(tColor,vUv+vec2(1.0,-1.0)*uTexel).rgb;
      vec3 rgbSW=texture2D(tColor,vUv+vec2(-1.0,1.0)*uTexel).rgb; vec3 rgbSE=texture2D(tColor,vUv+vec2(1.0,1.0)*uTexel).rgb; vec3 rgbM=texture2D(tColor,vUv).rgb;
      vec3 luma=vec3(0.299,0.587,0.114); float lNW=dot(rgbNW,luma),lNE=dot(rgbNE,luma),lSW=dot(rgbSW,luma),lSE=dot(rgbSE,luma),lM=dot(rgbM,luma);
      float lMin=min(lM,min(min(lNW,lNE),min(lSW,lSE))), lMax=max(lM,max(max(lNW,lNE),max(lSW,lSE)));
      vec2 dir; dir.x=-((lNW+lNE)-(lSW+lSE)); dir.y=((lNW+lSW)-(lNE+lSE));
      float dirReduce=max((lNW+lNE+lSW+lSE)*(0.25*0.125),1.0/128.0); float rcpDirMin=1.0/(min(abs(dir.x),abs(dir.y))+dirReduce);
      dir=min(vec2(6.0),max(vec2(-6.0),dir*rcpDirMin))*uTexel;
      vec3 rgbA=0.5*(texture2D(tColor,vUv+dir*(1.0/3.0-0.5)).rgb+texture2D(tColor,vUv+dir*(2.0/3.0-0.5)).rgb);
      vec3 rgbB=rgbA*0.5+0.25*(texture2D(tColor,vUv+dir*-0.5).rgb+texture2D(tColor,vUv+dir*0.5).rgb); float lB=dot(rgbB,luma);
      gl_FragColor=vec4((lB<lMin||lB>lMax)?rgbA:rgbB,1.0);
    }`;
  function supportsPost(){ if(postOk!==null) return postOk; try{ postOk=!!(renderer.capabilities.isWebGL2||renderer.extensions.has('WEBGL_depth_texture')); }catch(e){ postOk=false; } return postOk; }
  function disposePost(){ ['rt','rt2'].forEach(k=>{ if(post[k]){ if(post[k].depthTexture) post[k].depthTexture.dispose(); post[k].dispose(); post[k]=null; } }); }
  function ensurePost(){
    if(!supportsPost()) return false; renderer.getDrawingBufferSize(v2); const w=Math.max(2,v2.x|0), h=Math.max(2,v2.y|0);
    if(post.rt&&post.w===w&&post.h===h) return true;
    try{
      disposePost(); const dt=new THREE.DepthTexture(w,h); dt.type=renderer.capabilities.isWebGL2?THREE.UnsignedIntType:THREE.UnsignedShortType; dt.format=THREE.DepthFormat; dt.minFilter=dt.magFilter=THREE.NearestFilter;
      post.rt=new THREE.WebGLRenderTarget(w,h,{minFilter:THREE.NearestFilter,magFilter:THREE.NearestFilter,format:THREE.RGBAFormat,depthBuffer:true,stencilBuffer:false}); post.rt.depthTexture=dt;
      post.rt2=new THREE.WebGLRenderTarget(w,h,{minFilter:THREE.LinearFilter,magFilter:THREE.LinearFilter,format:THREE.RGBAFormat,depthBuffer:false,stencilBuffer:false});
      post.w=w; post.h=h;
      if(!post.qs){
        post.qs=new THREE.Scene(); post.qc=new THREE.OrthographicCamera(-1,1,1,-1,0,1); const g=new THREE.PlaneGeometry(2,2);
        post.edl=new THREE.ShaderMaterial({vertexShader:QV,fragmentShader:EDL_F,depthTest:false,depthWrite:false,uniforms:{tColor:{value:null},tDepth:{value:null},uTexel:{value:new THREE.Vector2()},uNear:{value:0.3},uFar:{value:900},uEdl:{value:0.55},uAo:{value:0.42},uRad:{value:1.2}}});
        post.fxaa=new THREE.ShaderMaterial({vertexShader:QV,fragmentShader:FXAA_F,depthTest:false,depthWrite:false,uniforms:{tColor:{value:null},uTexel:{value:new THREE.Vector2()}}});
        post.quad=new THREE.Mesh(g,post.edl); post.quad.frustumCulled=false; post.qs.add(post.quad);
      }
      return true;
    }catch(err){ console.warn('look: post pass unavailable',err&&err.message); postOk=false; disposePost(); return false; }
  }
  function render(){
    const sh=shadowActive(); if(sun.castShadow!==sh) sun.castShadow=sh;
    if(sh&&dirtyShadow){ renderer.shadowMap.needsUpdate=true; dirtyShadow=false; }
    if(!(white&&edgesOn&&!isPerf()&&ensurePost())){ renderer.render(scene,camera); return; }
    renderer.setRenderTarget(post.rt); renderer.render(scene,camera);
    const u=post.edl.uniforms; u.tColor.value=post.rt.texture; u.tDepth.value=post.rt.depthTexture; u.uTexel.value.set(1/post.w,1/post.h); u.uNear.value=camera.near; u.uFar.value=camera.far; u.uRad.value=Math.max(1.0,1.15*renderer.getPixelRatio());
    post.quad.material=post.edl; renderer.setRenderTarget(post.rt2); renderer.render(post.qs,post.qc);
    const f=post.fxaa.uniforms; f.tColor.value=post.rt2.texture; f.uTexel.value.set(1/post.w,1/post.h); post.quad.material=post.fxaa; renderer.setRenderTarget(null); renderer.render(post.qs,post.qc);
  }

  /* ---------------- switching ---------------- */
  function apply(first){
    U.mono.value=white?1:0; const wasShadow=renderer.shadowMap.enabled, wantShadow=white&&shadowsOn&&!isPerf();
    renderer.shadowMap.enabled=wantShadow; fog(); lights();
    if(wasShadow!==wantShadow||first||(!!scene.fog)!==fogWas){ matsUpdate(); } fogWas=!!scene.fog; dirtyShadow=true;
    ui(); const L=getLens(); if(L&&L.refresh) L.refresh(); wake(1500);
  }
  let fogWas=false;
  function set(mode,opt){
    const w=mode==='white'; if(w===white&&!(opt&&opt.force)) return; white=w; save(); apply(false);
    if(!(opt&&opt.quiet)) toast(w?'المظهر الأبيض والرمادي: اختر قسمًا في العدسة ليُلوَّن وحده':'عادت ألوان المواد',2600);
  }
  function setFlag(k,on){ if(k==='shadows') shadowsOn=on; else if(k==='edges') edgesOn=on; save(); apply(false); }
  function ui(){
    document.querySelectorAll('#viewMenu [data-look]').forEach(b=>b.classList.toggle('on',(b.dataset.look==='white')===white));
    document.querySelectorAll('#viewMenu [data-lk]').forEach(b=>{ const on=b.dataset.lk==='shadows'?shadowsOn:edgesOn; b.classList.toggle('on',on); b.disabled=!white; b.setAttribute('aria-pressed',on?'true':'false'); });
    document.body.classList.toggle('look-white',white);
  }
  const vm=$('viewMenu'); if(vm) vm.addEventListener('click',ev=>{ const b=ev.target.closest('[data-look],[data-lk]'); if(!b||b.disabled) return; ev.stopPropagation();
    if(b.dataset.look) set(b.dataset.look); else if(b.dataset.lk) setFlag(b.dataset.lk,!(b.dataset.lk==='shadows'?shadowsOn:edgesOn)); });
  apply(true);
  return {set,render,dirty(){ dirtyShadow=true; },afterPreset:lights,setFog:fog,get active(){ return white; },get edges(){ return white&&edgesOn&&!isPerf()&&postOk!==false; },get white(){ return white; },
    state(){ return {white,shadowsOn,edgesOn,shadowMap:renderer.shadowMap.enabled,castShadow:sun.castShadow,post:postOk,fog:!!scene.fog,mono:U.mono.value}; }};
}
window.initLook=initLook;
})();
