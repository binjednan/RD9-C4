/* Material colours and component feature lines are presentation only.
   Geometry, source material records and analytical lens colours stay intact. */
(function(){
'use strict';
function initLook(ctx){
  const {THREE,renderer,scene,camera,U,groups,hemi,sun,sun2,wake,toast,$,LP,getPreset,isPerf,clipActive,getLens}=ctx;
  const PALETTES={
    materials:{label:'ألوان المواد',bg:0xecefe9,neutral:[0.86,0.88,0.92],ground:0x9e9b90,hemi:0.72,sun:1.30,fill:0.34,edl:0.50,ao:0.28},
    day:{label:'نهاري',bg:0xedf1f5,neutral:[0.86,0.88,0.92],ground:0x9fa9b5,hemi:0.58,sun:1.25,fill:0.26,edl:0.48,ao:0.30},
    dark:{label:'داكن',bg:0x17212d,neutral:[0.46,0.52,0.58],ground:0x667180,hemi:0.48,sun:1.45,fill:0.28,edl:0.48,ao:0.28},
    clay:{label:'مجسم محايد',bg:0xf0eee9,neutral:[0.76,0.73,0.68],ground:0xa7a9ad,hemi:0.34,sun:1.85,fill:0.16,edl:0.70,ao:0.44},
    xray:{label:'شفاف للشبكات',bg:0xe9f0f5,neutral:[0.65,0.69,0.73],ground:0x9baaba,hemi:0.95,sun:0.70,fill:0.34,edl:0.38,ao:0.24}
  };
  const alias=m=>m==='white'?'clay':m==='mat'?'materials':m==='daylight'?'day':PALETTES[m]?m:'day';
  let mode='materials', shadowsOn=true, edgesOn=true, dirtyShadow=true, postOk=null;
  let sceneRenderInfo={calls:0,triangles:0};
  const captureSceneInfo=()=>{sceneRenderInfo={calls:renderer.info.render.calls,triangles:renderer.info.render.triangles};};
  try{ localStorage.removeItem('c4look'); const s=JSON.parse(localStorage.getItem('c4look-v3')||'null'); if(s){ mode=alias(s.mode); shadowsOn=s.s!==0; edgesOn=s.e!==0; } }catch(e){}
  const save=()=>{ try{ localStorage.setItem('c4look-v3',JSON.stringify({mode,s:shadowsOn?1:0,e:edgesOn?1:0})); }catch(e){} };
  const TG=new THREE.Vector3(18,8,-17);                      // centre of the building (shadow frustum)
  const v2=new THREE.Vector2();
  const opacityBases=new WeakMap();
  // Approximate material-family appearance; never written back to source data.
  const appearanceCache=new Map();
  function appearance(key){
    if(appearanceCache.has(key))return appearanceCache.get(key);
    const source=ctx.M?.mats?.[key]||{},text=(key+' '+(source.source_material_literal||'')+' '+(source.source_finish_literal||'')).toLowerCase();
    let color='#d4d0c7',rough=.72,metal=0;
    const pick=(c,r=.72,m=0)=>{color=c;rough=r;metal=m;};
    if(key==='owner_bracket_steel')pick('#8c949b',.9,0);
    else if(/conc|concrete|lhs_|srf_|bnd_concrete/.test(text))pick('#b7b3aa',.94);
    else if(/block|masonry/.test(text))pick('#c8bca7',.95);
    else if(/glass|glaz|mirror/.test(text))pick(/span/.test(key)?'#807b6e':'#96b7b0',.12,.18);
    else if(/chrome|stainless|ss304|steel|metal|alumin|m_tray|m_duct|m_grille|m_damper|m_fan|m_fcu|m_fahu|m_chiller/.test(text))pick(/gold/.test(text)?'#c9aa62':'#aeb4b7',.38,.58);
    else if(/copper|m_cu|m_earth/.test(text))pick('#b87745',.38,.62);
    else if(/wood|walnut|timber|mdf/.test(text))pick(/light/.test(key)?'#c6a47b':/dark|walnut/.test(text)?'#765039':'#a07953',.62);
    else if(/crema marfil|marble/.test(text))pick(/gray/.test(text)?'#a4a5a2':'#d8cbb3',.27);
    else if(/granite/.test(text))pick('#878883',.42);
    else if(/grc|porcelain|ceramic|gypsum|plaster|clad_porc/.test(text))pick('#e4dfd2',/polish/.test(text)?.24:.67);
    else if(/ppr/.test(text)||/^(p_cold|p_hot|p_irr)$/.test(key))pick('#809d78',.52);
    else if(/upvc|pvc|^(p_soil|p_waste|p_vent|p_storm|p_site|m_conduit)$/.test(text))pick('#c1c3bf',.56);
    else if(/^(m_chws|m_chwr|hose_black)$|rubber|insulat/.test(text))pick('#45484a',.92);
    else if(/^p_ff|m_fa_red|fire_pump/.test(key))pick('#aa3b34',.52);
    else if(/^p_sprk|valve/.test(key))pick('#b89a58',.35,.42);
    else if(/grass|leaf|shrub|plant_|tree_(azad|hibi|plum)/.test(key))pick('#647952',.94);
    else if(/sand|floor_fill/.test(key))pick('#baa98a',.98);
    else if(/asphalt/.test(key))pick('#595b59',.98);
    else if(/furn_fabric|cur_|fabric/.test(text))pick('#b7aa96',.96);
    else if(/^m_|^app_|^san_|^p_heater|^kit_|^fin_C/.test(key))pick('#e3e1d8',.58);
    // Presentation assets can keep their authored colour; service CAD colours cannot.
    else if(/^(site_|play_|hold_|flower_|furn_)/.test(key))color=source.color||source.historical_display_color||color;
    if(/^#[0-9a-f]{6}$/i.test(source.physical_color_hex||''))color=source.physical_color_hex;
    const result={color,rough,metal};appearanceCache.set(key,result);return result;
  }
  function surfaceAppearance(){
    for(const k in groups){const G=groups[k],m=G.matBase;if(!m)continue;
      const a=appearance(G.mat);m.color.set(mode==='materials'?a.color:'#D4DADD').convertSRGBToLinear();
      m.roughness=mode==='materials'?a.rough:.78;m.metalness=mode==='materials'?a.metal:0;
    }
  }

  function isGlass(G){return /glass/i.test(G.mat||'')||(G.cat==='A.glass');}
  function opacity(){
    for(const k in groups){
      const G=groups[k],m=G.matBase; if(!m) continue;
      if(!m.userData) m.userData={};
      let b=opacityBases.get(m);
      if(!b){ b={base:m.userData.baseOpacity===undefined?(m.opacity===undefined?1:m.opacity):m.userData.baseOpacity}; opacityBases.set(m,b); }
      const previous=m.userData.baseOpacity===undefined?b.base:m.userData.baseOpacity;
      const multiplier=previous>0?Math.max(0,Math.min(1,m.opacity/previous)):1;
      const structural=/^[AS]\./.test(G.cat||'');
      const next=mode==='materials'?(isGlass(G)?.42:1):mode==='xray'&&!isGlass(G)?(structural?0.22:1):b.base;
      m.userData.baseOpacity=next; m.userData.lookOriginalOpacity=b.base;
      const o=next*multiplier,tr=o<0.999;
      m.opacity=o; if(m.transparent!==tr){m.transparent=tr;m.needsUpdate=true;} m.depthWrite=!tr;
      if(G.mesh) G.mesh.castShadow=!isGlass(G)&&next>=0.999;
    }
  }

  /* Fine feature lines follow the existing architectural, structural and MEP
     bodies. Coplanar triangle diagonals are omitted; boundaries between
     separate model components are preserved. Rounded tube/cylinder facets
     stay smooth: only their mesh boundaries and true sharp rim edges remain.
     Source coordinates are never moved. The original visibility, lens, unit,
     clipping and exploded-level transforms apply to these lines as well. */
  const featureLines=[];
  const featureStats={elements:0,segments:0,byCategory:{}};
  let featuresBuilt=false;
  function buildFeatureLines(){
    if(featuresBuilt)return;featuresBuilt=true;
    if(!ctx.M||!ctx.elRange)return;
    const byGroup=new Map();
    ctx.M.els.forEach((e,ei)=>{
      const rg=ctx.elRange[ei],G=rg&&groups[rg.gk];if(!G?.mesh||G.stage||!/^[ASMEP]\./.test(e.c)||!rg.count)return;
      // These primitives are round bodies tessellated for rendering. Their
      // 5/6/8-sided axial facets are not fabricated equipment panel seams.
      const rounded=e.g&&['t','cyl','sph'].includes(e.g[0]);
      const crease=Math.cos((rounded?75:20)*Math.PI/180);
      const p=G.posArr,edges=new Map(),ids=[];
      const key=v=>[p[v*3],p[v*3+1],p[v*3+2]].map(x=>Math.round(x*10000)).join(',');
      for(let t=rg.start*3;t<(rg.start+rg.count)*3;t+=3){
        const ax=p[(t+1)*3]-p[t*3],ay=p[(t+1)*3+1]-p[t*3+1],az=p[(t+1)*3+2]-p[t*3+2];
        const bx=p[(t+2)*3]-p[t*3],by=p[(t+2)*3+1]-p[t*3+1],bz=p[(t+2)*3+2]-p[t*3+2];
        let nx=ay*bz-az*by,ny=az*bx-ax*bz,nz=ax*by-ay*bx;const length=Math.hypot(nx,ny,nz);if(length<1e-10)continue;nx/=length;ny/=length;nz/=length;
        const normal=[nx,ny,nz,nx*p[t*3]+ny*p[t*3+1]+nz*p[t*3+2]];
        const ks=[key(t),key(t+1),key(t+2)];
        for(let j=0;j<3;j++){
          const a=t+j,b=t+(j+1)%3,ka=ks[j],kb=ks[(j+1)%3];if(ka===kb)continue;const k=ka<kb?ka+'|'+kb:kb+'|'+ka;
          const old=edges.get(k);
          if(old){if(!old.other)old.other=normal;else if(old.extra)old.extra.push(normal);else old.extra=[normal];}
          else edges.set(k,{a,b,normal,other:null,extra:null});
        }
      }
      edges.forEach(v=>{
        if(!v.other){ids.push(v.a,v.b);return;}
        if(!v.extra){if(Math.abs(v.normal[0]*v.other[0]+v.normal[1]*v.other[1]+v.normal[2]*v.other[2])<crease)ids.push(v.a,v.b);return;}
        let ns=[v.normal,v.other,...v.extra];
        if(ns.length>2){
          // Consecutive duct primitives have coincident opposite caps at a
          // straight joint. Cancel those internal faces before comparing the
          // remaining outside faces; their ring is not an equipment panel.
          const used=new Uint8Array(ns.length);
          for(let i=0;i<ns.length;i++){if(used[i])continue;for(let j=i+1;j<ns.length;j++){
            if(!used[j]&&ns[i][0]*ns[j][0]+ns[i][1]*ns[j][1]+ns[i][2]*ns[j][2]<-.99999999&&Math.abs(ns[i][3]+ns[j][3])<1e-5){used[i]=used[j]=1;break;}
          }}
          ns=ns.filter((n,i)=>!used[i]);
        }
        let feature=ns.length===1;
        for(let i=0;!feature&&i<ns.length;i++)for(let j=i+1;j<ns.length;j++){
          if(Math.abs(ns[i][0]*ns[j][0]+ns[i][1]*ns[j][1]+ns[i][2]*ns[j][2])<crease){feature=true;break;}
        }
        if(feature)ids.push(v.a,v.b);
      });
      if(ids.length){let list=byGroup.get(rg.gk);if(!list){list=[];byGroup.set(rg.gk,list);}ids.forEach(i=>list.push(i));featureStats.elements++;featureStats.byCategory[e.c]=(featureStats.byCategory[e.c]||0)+1;}
    });
    byGroup.forEach((ids,k)=>{
      const G=groups[k],source=G.mesh.geometry,position=[],unit=[],clip=[];
      ids.forEach(i=>{position.push(G.posArr[i*3],G.posArr[i*3+1],G.posArr[i*3+2]);unit.push(source.attributes.aUnit.array[i*2],source.attributes.aUnit.array[i*2+1]);clip.push(source.attributes.aClip.array[i]);});
      const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(position,3));g.setAttribute('aUnit',new THREE.Int16BufferAttribute(unit,2));g.setAttribute('aClip',new THREE.Uint8BufferAttribute(clip,1));g.setAttribute('aHide',new THREE.Uint8BufferAttribute(new Uint8Array(ids.length),1));g.setAttribute('aLens',new THREE.Uint8BufferAttribute(new Uint8Array(ids.length),1));g.computeBoundingSphere();
      const mat=new THREE.LineBasicMaterial({color:0x8da5bc,transparent:true,opacity:.22,depthTest:true,depthWrite:false,toneMapped:false});
      // Bundled r128 Color.setHex stores raw components. These display hexes
      // are sRGB: convert once before the renderer's sRGB output conversion.
      // Otherwise pale feature lines are brightened a second time by output.
      mat.color.convertSRGBToLinear();
      mat.onBeforeCompile=sh=>{
        sh.uniforms.uIso=U.iso;sh.uniforms.uMask=U.mask;sh.uniforms.uMaskBox=U.maskBox;sh.uniforms.uLensOn=U.lensOn;
        sh.vertexShader=sh.vertexShader.replace('#include <common>','#include <common>\nattribute vec2 aUnit;attribute float aClip;attribute float aHide;attribute float aLens;uniform float uLensOn;varying vec2 vUnit;varying float vClip;varying vec3 vWPos;')
          .replace('#include <begin_vertex>','#include <begin_vertex>\nvUnit=aUnit;vClip=aClip;vWPos=(modelMatrix*vec4(transformed,1.0)).xyz;')
          .replace('#include <project_vertex>','#include <project_vertex>\nvec4 edgeView=mvPosition;edgeView.z+=0.0002;gl_Position=projectionMatrix*edgeView;\nif(aHide>0.5||(uLensOn>0.5&&aLens>254.5))gl_Position=vec4(2.0,2.0,2.0,1.0);');
        sh.fragmentShader=sh.fragmentShader.replace('#include <common>','#include <common>\nuniform float uIso;uniform sampler2D uMask;uniform vec4 uMaskBox;varying vec2 vUnit;varying float vClip;varying vec3 vWPos;')
          .replace('void main() {','void main() {\nif(uIso>-.5&&vClip<.5&&abs(vUnit.x-uIso)>.5&&abs(vUnit.y-uIso)>.5)discard;\nif(uIso>-.5&&vClip>.5){vec2 uv=(vWPos.xz-uMaskBox.xy)/uMaskBox.zw;if(uv.x<0.||uv.x>1.||uv.y<0.||uv.y>1.||texture2D(uMask,uv).r<.5)discard;}');
      };
      mat.customProgramCacheKey=()=> 'c4-feature-lines-v3';
      const lines=new THREE.LineSegments(g,mat);lines.renderOrder=2;lines.userData.presentationOnly=true;lines.raycast=()=>{};G.mesh.add(lines);
      featureLines.push({G,lines,ids:new Uint32Array(ids),hideVersion:-1,lensVersion:-1});featureStats.segments+=ids.length/2;
    });
  }
  function syncFeatureLines(){
    const active=edgesOn&&!isPerf()&&mode!=='xray';if(active)buildFeatureLines();
    featureLines.forEach(f=>{
      f.lines.visible=active;
      if(!active)return;
      f.lines.material.color.setHex(mode==='dark'?0xb5c5d2:mode==='clay'?0x5d5c59:0x30383f).convertSRGBToLinear();
      f.lines.material.opacity=(mode==='materials'||mode==='day'?(/^[MEP]\./.test(f.G.cat)? .56:.46):.38)*Math.min(1,f.G.matBase.opacity*2);
      for(const pair of [['hideVersion','aHide',f.G.hideAttr],['lensVersion','aLens',f.G.lensAttr]]){
        const [version,key,source]=pair;if(!source||f[version]===source.version)continue;
        const target=f.lines.geometry.attributes[key];for(let i=0;i<f.ids.length;i++)target.array[i]=source.array[f.ids[i]];target.needsUpdate=true;f[version]=source.version;
      }
    });
  }

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
  const shadowActive=()=>mode!=='xray'&&shadowsOn&&!isPerf()&&!clipActive();

  /* ---------------- lights, fog ---------------- */
  function lights(){
    const p=PALETTES[mode],P=LP[getPreset()]||LP.day;
    hemi.color.set(0xffffff); hemi.groundColor.set(p.ground); hemi.intensity=p.hemi;
    sun.color.set(0xffffff); sun.intensity=p.sun; sun2.color.set(0xffffff); sun2.intensity=p.fill;
    const sp=getPreset()==='day'?[-50,70,-45]:(P?P.sp:[-50,70,-45]),d=new THREE.Vector3(sp[0],sp[1],sp[2]).normalize();
    if(shadowActive()){ sun.target.position.copy(TG); sun.position.copy(TG).addScaledVector(d,120); }
    else { sun.target.position.set(0,0,0); sun.position.set(sp[0],sp[1],sp[2]); }
    if(scene.background&&scene.background.isTexture) scene.background.dispose();
    scene.background=new THREE.Color(p.bg);
    sun.target.updateMatrixWorld(); dirtyShadow=true; wake();
  }
  function fog(){
    // Model scale is metres; fog must not conceal surfaces under review.
    scene.fog=null;
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
      post.rt=new THREE.WebGLRenderTarget(w,h,{minFilter:THREE.NearestFilter,magFilter:THREE.NearestFilter,format:THREE.RGBAFormat,depthBuffer:true,stencilBuffer:false}); post.rt.depthTexture=dt; post.rt.texture.encoding=renderer.outputEncoding;
      post.rt2=new THREE.WebGLRenderTarget(w,h,{minFilter:THREE.LinearFilter,magFilter:THREE.LinearFilter,format:THREE.RGBAFormat,depthBuffer:false,stencilBuffer:false});
      post.rt2.texture.encoding=renderer.outputEncoding;
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
    syncFeatureLines();
    const sh=shadowActive(); if(sun.castShadow!==sh) sun.castShadow=sh;
    if(sh&&dirtyShadow){ renderer.shadowMap.needsUpdate=true; dirtyShadow=false; }
    if(!(edgesOn&&!isPerf()&&!ctx.isMoving?.()&&ensurePost())){ renderer.render(scene,camera); captureSceneInfo(); return; }
    renderer.setRenderTarget(post.rt); renderer.render(scene,camera); captureSceneInfo();
    const u=post.edl.uniforms; u.tColor.value=post.rt.texture; u.tDepth.value=post.rt.depthTexture; u.uTexel.value.set(1/post.w,1/post.h); u.uNear.value=camera.near; u.uFar.value=camera.far; u.uRad.value=Math.max(1.0,1.15*renderer.getPixelRatio());
    u.uEdl.value=PALETTES[mode].edl; u.uAo.value=PALETTES[mode].ao;
    post.quad.material=post.edl; renderer.setRenderTarget(post.rt2); renderer.render(post.qs,post.qc);
    const f=post.fxaa.uniforms; f.tColor.value=post.rt2.texture; f.uTexel.value.set(1/post.w,1/post.h); post.quad.material=post.fxaa; renderer.setRenderTarget(null); renderer.render(post.qs,post.qc);
  }

  /* ---------------- switching ---------------- */
  function apply(first){
    U.mono.value=mode==='materials'?0:1;if(U.highKey)U.highKey.value=mode==='day'?1:0;if(U.xray)U.xray.value=mode==='xray'?1:0;
    const nc=PALETTES[mode].neutral;
    if(U.neutral){ const n=U.neutral.value; if(n&&n.setRGB) n.setRGB(nc[0],nc[1],nc[2]); else if(n&&n.set) n.set(nc[0],nc[1],nc[2]); else U.neutral.value=nc.slice(); }
    const wasShadow=renderer.shadowMap.enabled,wantShadow=shadowActive();
    renderer.shadowMap.enabled=wantShadow;
    if(ctx.setPresetLight&&getPreset()!=='day') ctx.setPresetLight('day');
    surfaceAppearance(); opacity(); fog(); lights();
    if(wasShadow!==wantShadow||first||(!!scene.fog)!==fogWas){ matsUpdate(); } fogWas=!!scene.fog; dirtyShadow=true;
    ui(); const L=getLens(); if(L&&L.refresh) L.refresh(); wake(1500);
  }
  let fogWas=false;
  function set(name,opt){
    const next=alias(name); if(next===mode&&!(opt&&opt.force)) return; mode=next; save(); apply(false);
    if(!(opt&&opt.quiet)) toast('المظهر: '+PALETTES[mode].label+(mode==='materials'?' — درجات الخامات تقريبية':''),2600);
  }
  function snapshot(){ return {mode,w:mode==='clay'?1:0,s:shadowsOn?1:0,e:edgesOn?1:0}; }
  function restore(o){ mode=o&&o.mode?alias(o.mode):o&&o.w?'clay':'materials'; shadowsOn=!(o&&o.s===0); edgesOn=!(o&&o.e===0); save(); apply(false); }
  function setFlag(k,on){ if(k==='shadows') shadowsOn=on; else if(k==='edges') edgesOn=on; save(); apply(false); }
  function ui(){
    document.querySelectorAll('button[data-look]').forEach(b=>{const on=alias(b.dataset.look)===mode;b.classList.toggle('on',on);b.setAttribute('aria-pressed',on?'true':'false');});
    document.querySelectorAll('button[data-lk]').forEach(b=>{ const wanted=b.dataset.lk==='shadows'?shadowsOn:edgesOn; const inactive=isPerf()||(b.dataset.lk==='shadows'&&mode==='xray');const on=wanted&&!inactive; b.classList.toggle('on',on); b.disabled=inactive; b.setAttribute('aria-pressed',on?'true':'false'); });
    ['materials','day','dark','clay','xray'].forEach(k=>document.body.classList.toggle('look-'+k,k===mode));
    document.body.classList.toggle('look-white',mode==='clay');
    document.body.classList.toggle('theme-dark',mode==='dark');
    document.body.dataset.look=mode;
  }
  document.addEventListener('click',ev=>{ const b=ev.target.closest('button[data-look],button[data-lk]'); if(!b||b.disabled) return; ev.stopPropagation();
    if(b.dataset.look) set(b.dataset.look); else if(b.dataset.lk) setFlag(b.dataset.lk,!(b.dataset.lk==='shadows'?shadowsOn:edgesOn)); });
  apply(true);
  return {set,snapshot,restore,render,dirty(){ opacity();dirtyShadow=true; },afterPreset:lights,setFog:fog,get lastRenderInfo(){return sceneRenderInfo;},get active(){ return true; },get edges(){ return edgesOn&&!isPerf()&&postOk!==false; },get white(){ return mode==='clay'; },get mode(){ return mode; },
    state(){ return {mode,white:mode==='clay',shadowsOn,edgesOn,featureLines:{...featureStats,active:edgesOn&&!isPerf()&&mode!=='xray'},shadowMap:renderer.shadowMap.enabled,castShadow:sun.castShadow,post:postOk,fog:!!scene.fog,mono:U.mono.value,neutral:PALETTES[mode].neutral.slice(),opacityMode:mode==='xray'?'structure_0.22':'base',materialColors:mode==='materials',approximateMaterialAppearance:true,physicalColors:false}; }};
}
window.initLook=initLook;
})();
