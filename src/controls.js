/* ===== CameraRig: one camera controller for touch, mouse, trackpad and keyboard =====
   - pointer events only (no legacy touch events); camera position/target stay the source of truth,
     so external animations (flyTo) can overwrite them freely.
   - mode ('rotate'|'pan'|'zoom') decides what a one-finger / left-button drag does.
   - mouse: left = mode action, right / Shift+left = pan, middle = zoom, wheel = zoom to cursor.
   - trackpad: pinch (wheel+ctrlKey, Safari gesture*) = zoom, two-finger scroll = pan; rotate = three-finger drag (macOS turns it into a
     mouse drag) or Alt + two-finger scroll.
   - touch (tablets, owner 2026-10-07): one finger = rotate (the bottom mode buttons can change it), two fingers moving TOGETHER = pan, two fingers moving TOWARD each
     other = zoom in, moving APART = zoom out (switchable: pinchInZooms=false gives the usual spread = zoom in). A two-finger gesture is classified once (pan or zoom),
     so a pan never zooms and a pinch never drifts; after a short pause the next movement is classified again.
   - keyboard: arrows rotate, W/A/S/D pan, Q/E down/up, + / - zoom, Home = full view, F = focus.        */
class CameraRig extends THREE.EventDispatcher{
  constructor(camera,dom){
    super();
    this.camera=camera; this.dom=dom; this.target=new THREE.Vector3(); this.enabled=true;
    this.minDistance=0.15; this.maxDistance=260; this.minSurface=0.25; this.hitTest=null; this.minPolarAngle=0.02; this.maxPolarAngle=Math.PI*0.499;
    this.bounds=new THREE.Box3(new THREE.Vector3(-30,-6,-85),new THREE.Vector3(85,48,35));
    this.mode='rotate'; this.pointerKind='auto'; this.rotateSpeed=1; this.zoomSpeed=1; this.padSpeed=1;
    this.onHome=null; this.onFocus=null; this.lastGestureMulti=false; this.pinchInZooms=true;
    this._ptrs=new Map(); this._drag=null; this._pinch=null; this._vel={th:0,ph:0}; this._keys=new Set();
    this._t=performance.now(); this._lastPad=0; this._wheelTimer=0; this._started=false; this._gs=1;
    this._o=new THREE.Vector3(); this._f=new THREE.Vector3(); this._r=new THREE.Vector3(); this._u=new THREE.Vector3(); this._d=new THREE.Vector3();
    this._bind();
  }
  /* ---- spherical helpers (position relative to target) ---- */
  _sph(){const o=this._o.copy(this.camera.position).sub(this.target);const r=Math.max(o.length(),1e-6);return {r,ph:Math.acos(THREE.MathUtils.clamp(o.y/r,-1,1)),th:Math.atan2(o.x,o.z)};}
  _setSph(r,ph,th){
    r=THREE.MathUtils.clamp(r,this.minDistance,this.maxDistance); ph=THREE.MathUtils.clamp(ph,this.minPolarAngle,this.maxPolarAngle);
    const sp=Math.sin(ph); this.camera.position.set(this.target.x+r*sp*Math.sin(th),this.target.y+r*Math.cos(ph),this.target.z+r*sp*Math.cos(th)); this.camera.lookAt(this.target);
  }
  _clampTarget(){const t=this.target,b=this.bounds,x=t.x,y=t.y,z=t.z; t.clamp(b.min,b.max); if(t.x!==x||t.y!==y||t.z!==z){this.camera.position.add(this._o.set(t.x-x,t.y-y,t.z-z));}}
  /* ---- primitive motions ---- */
  rotate(dth,dph){const s=this._sph();this._setSph(s.r,s.ph+dph,s.th+dth);}
  pan(dxPx,dyPx){
    const h=Math.max(this.dom.clientHeight,200),s=this._sph(),k=2*s.r*Math.tan(THREE.MathUtils.degToRad(this.camera.fov/2))/h;
    this._f.copy(this.target).sub(this.camera.position).normalize(); this._r.crossVectors(this._f,this.camera.up).normalize(); this._u.crossVectors(this._r,this._f).normalize();
    const mv=this._o.copy(this._r).multiplyScalar(-dxPx*k).addScaledVector(this._u,dyPx*k); this.target.add(mv); this.camera.position.add(mv); this._clampTarget();
  }
  moveWorld(dx,dy,dz){this.target.x+=dx;this.target.y+=dy;this.target.z+=dz;this.camera.position.x+=dx;this.camera.position.y+=dy;this.camera.position.z+=dz;this._clampTarget();}
  _pointOnTargetPlane(cx,cy,out){ // cursor ray hit on the plane through target facing the camera
    const r=this.dom.getBoundingClientRect(); const nx=((cx-r.left)/r.width)*2-1,ny=-((cy-r.top)/r.height)*2+1;
    this.camera.updateMatrixWorld(true); const d=this._d.set(nx,ny,0.5).unproject(this.camera).sub(this.camera.position).normalize();
    this._f.copy(this.target).sub(this.camera.position); const dist=this._f.length(); this._f.normalize(); const den=d.dot(this._f);
    return den>1e-6?out.copy(this.camera.position).addScaledVector(d,dist/den):out.copy(this.target);
  }
  dolly(scale,cx,cy){
    if(this.hitTest&&this._dollySurface(scale,cx,cy)) return;
    const s=this._sph(); const nr=THREE.MathUtils.clamp(s.r*scale,this.minDistance,this.maxDistance); if(Math.abs(nr-s.r)<1e-6) return;
    const useCur=cx!==undefined&&cy!==undefined; const a=new THREE.Vector3(),b=new THREE.Vector3();
    if(useCur) this._pointOnTargetPlane(cx,cy,a);
    this._setSph(nr,s.ph,s.th);
    if(useCur){this._pointOnTargetPlane(cx,cy,b); const mv=a.sub(b); this.target.add(mv); this.camera.position.add(mv); this._clampTarget(); this.camera.lookAt(this.target);}
  }
  /* zoom toward the real surface under the cursor (or the screen centre), then pivot the orbit on the surface at the screen centre */
  _dollySurface(scale,cx,cy){
    const r=this.dom.getBoundingClientRect(); const px=cx!==undefined?cx:r.left+r.width/2,py=cy!==undefined?cy:r.top+r.height/2;
    const hit=this.hitTest(px,py); if(!hit) return false;
    const cam=this.camera.position,v=this._d.copy(hit).sub(cam),dist=v.length(); if(dist<1e-4) return false;
    let k=scale; if(k<1&&dist*k<this.minSurface) k=Math.max(this.minSurface/dist,Math.min(1,k+0.0)); if(k<1&&dist<=this.minSurface+1e-3) return true; // already touching
    if(k>1&&this._sph().r*k>this.maxDistance) return true;
    const mv=v.multiplyScalar(1-k); cam.add(mv); this.target.add(mv);
    const c=this.hitTest(r.left+r.width/2,r.top+r.height/2); if(c&&c.distanceTo(cam)>this.minDistance) this.target.copy(c);
    this._clampTarget(); this.camera.lookAt(this.target); return true;
  }
  /* ---- plumbing ---- */
  _start(){if(!this._started){this._started=true;this.dispatchEvent({type:'start'});}}
  _end(){if(this._started&&!this._ptrs.size&&!this._keys.size){this._started=false;this.dispatchEvent({type:'end'});}}
  setMode(m){this.mode=m;this.dispatchEvent({type:'mode',mode:m});}
  _bind(){
    const d=this.dom; d.style.touchAction='none'; d.style.userSelect='none'; d.style.webkitUserSelect='none'; d.tabIndex=0; d.style.outline='none';
    d.addEventListener('contextmenu',e=>e.preventDefault());
    d.addEventListener('pointerdown',e=>this._down(e)); d.addEventListener('pointermove',e=>this._move(e));
    d.addEventListener('pointerup',e=>this._up(e)); d.addEventListener('pointercancel',e=>this._up(e));
    d.addEventListener('wheel',e=>this._wheel(e),{passive:false});
    // Safari (macOS trackpad pinch, iOS pinch): gesture* events
    d.addEventListener('gesturestart',e=>{e.preventDefault(); this._gs=e.scale||1;},{passive:false});
    d.addEventListener('gesturechange',e=>{e.preventDefault(); if(this._ptrs.size>=2||!this.enabled) return; this._start(); const k=this._gs/(e.scale||1); this._gs=e.scale||1; this.dolly(Math.pow(k,this.zoomSpeed),e.clientX,e.clientY); clearTimeout(this._wheelTimer); this._wheelTimer=setTimeout(()=>this._end(),180);},{passive:false});
    d.addEventListener('gestureend',e=>e.preventDefault(),{passive:false});
    window.addEventListener('keydown',e=>this._keydown(e)); window.addEventListener('keyup',e=>this._keyup(e)); window.addEventListener('blur',()=>{this._keys.clear();this._end();});
  }
  /* ---- pointers ---- */
  _down(e){
    if(!this.enabled) return; try{this.dom.setPointerCapture(e.pointerId);}catch(_){}
    if(!this._ptrs.size) this.lastGestureMulti=false;
    this._ptrs.set(e.pointerId,{x:e.clientX,y:e.clientY,type:e.pointerType,btn:e.button,t:performance.now()});
    this._vel.th=this._vel.ph=0; this._start();
    if(this._ptrs.size===1){this._drag={x:e.clientX,y:e.clientY,btn:e.button,type:e.pointerType,shift:e.shiftKey||e.ctrlKey||e.metaKey,last:performance.now(),moved:0};}
    else if(this._ptrs.size===2){this.lastGestureMulti=true; this._drag=null; this._initPinch();}
    if(e.pointerType==='mouse') this.dom.focus({preventScroll:true});
  }
  _initPinch(){const [a,b]=[...this._ptrs.values()]; const dist=Math.hypot(a.x-b.x,a.y-b.y)||1,mx=(a.x+b.x)/2,my=(a.y+b.y)/2; this._pinch={dist,mx,my,d0:dist,mx0:mx,my0:my,kind:null,last:performance.now()};}
  _pinchScale(prev,cur){const r=this.pinchInZooms?cur/prev:prev/cur; return Math.pow(r,this.zoomSpeed);}   // < 1 = camera moves closer
  _move(e){
    const p=this._ptrs.get(e.pointerId); if(!p||!this.enabled) return;
    const dx=e.clientX-p.x,dy=e.clientY-p.y; p.x=e.clientX; p.y=e.clientY;
    if(this._ptrs.size>=2&&this._pinch){
      const [a,b]=[...this._ptrs.values()]; const dist=Math.hypot(a.x-b.x,a.y-b.y)||1,mx=(a.x+b.x)/2,my=(a.y+b.y)/2;
      const P=this._pinch,now=performance.now();
      if(P.kind&&now-P.last>240){P.kind=null;P.d0=P.dist;P.mx0=P.mx;P.my0=P.my;}                   // fingers paused: classify the next movement again
      P.last=now;
      if(!P.kind){
        const dD=Math.abs(dist-P.d0),dM=Math.hypot(mx-P.mx0,my-P.my0);
        if(Math.max(dD,dM)<9){P.dist=dist;P.mx=mx;P.my=my;return;}                                   // too small to tell pan from pinch: wait
        P.kind=dD>1.2*dM?'zoom':'pan'; P.dist=P.d0; P.mx=P.mx0; P.my=P.my0;                           // then apply everything since the start of the gesture
      }
      if(P.kind==='zoom') this.dolly(this._pinchScale(P.dist,dist),mx,my); else this.pan(mx-P.mx,my-P.my);
      P.dist=dist; P.mx=mx; P.my=my; return;
    }
    const D=this._drag; if(!D) return; D.moved+=Math.abs(dx)+Math.abs(dy);
    let act; if(D.type==='mouse'){ act=D.btn===2?'pan':D.btn===1?'zoom':(D.shift?'pan':this.mode);} else act=this.mode;
    const h=Math.max(this.dom.clientHeight,300),k=2*Math.PI/h*this.rotateSpeed;
    if(act==='rotate'){this.rotate(-dx*k,-dy*k); const now=performance.now(),dt=Math.max(now-D.last,1); D.last=now; this._vel.th=0.7*this._vel.th+0.3*(-dx*k)/dt*16; this._vel.ph=0.7*this._vel.ph+0.3*(-dy*k)/dt*16;}
    else if(act==='pan') this.pan(dx,dy);
    else this.dolly(Math.exp(dy*0.006*this.zoomSpeed));
  }
  _up(e){
    if(!this._ptrs.has(e.pointerId)) return; this._ptrs.delete(e.pointerId);
    try{this.dom.releasePointerCapture(e.pointerId);}catch(_){}
    if(this._ptrs.size===1){const q=[...this._ptrs.values()][0]; this._pinch=null; this._drag={x:q.x,y:q.y,btn:q.btn,type:q.type,shift:false,last:performance.now(),moved:99}; this._vel.th=this._vel.ph=0;}
    else if(!this._ptrs.size){
      const idle=performance.now()-(this._drag?this._drag.last:0); this._drag=null; this._pinch=null;
      if(idle>80) this._vel.th=this._vel.ph=0; this._end();
    }
  }
  /* ---- wheel / trackpad ---- */
  _wheelKind(e){
    if(e.ctrlKey) return 'pinch';
    if(this.pointerKind==='mouse') return 'mouse'; if(this.pointerKind==='pad') return 'pad';
    if(e.deltaMode!==0) return 'mouse';
    const now=performance.now(),ax=Math.abs(e.deltaX),ay=Math.abs(e.deltaY);
    if(ax>0||ay%1!==0||ay<50||now-this._lastPad<250){this._lastPad=now;return 'pad';}
    return 'mouse';
  }
  _wheel(e){
    if(!this.enabled) return; e.preventDefault(); this._start();
    const u=e.deltaMode===1?16:e.deltaMode===2?100:1,dx=e.deltaX*u,dy=e.deltaY*u,kind=this._wheelKind(e);
    if(kind==='pinch') this.dolly(Math.exp(dy*0.01*this.zoomSpeed),e.clientX,e.clientY);
    else if(kind==='mouse') this.dolly(Math.exp(dy*0.0012*this.zoomSpeed),e.clientX,e.clientY);
    else if(e.altKey){const h=Math.max(this.dom.clientHeight,300),k=2*Math.PI/h*this.rotateSpeed*this.padSpeed; this.rotate(dx*k,dy*k);}   // Alt + two-finger scroll = rotate (fallback for 3-finger drag)
    else if(this.mode==='zoom') this.dolly(Math.exp(dy*0.004*this.zoomSpeed),e.clientX,e.clientY);
    else this.pan(-dx*this.padSpeed,-dy*this.padSpeed);                                                                                        // two-finger scroll = pan
    clearTimeout(this._wheelTimer); this._wheelTimer=setTimeout(()=>this._end(),180);
  }
  /* ---- keyboard ---- */
  _typing(e){const t=e.target; return t&&(t.tagName==='INPUT'&&t.type!=='range'&&t.type!=='checkbox'||t.tagName==='TEXTAREA'||t.tagName==='SELECT'||t.isContentEditable);}
  _keydown(e){
    if(!this.enabled||e.ctrlKey||e.metaKey||e.altKey||this._typing(e)) return;
    const c=e.code,k=e.key;
    if(c==='Home'){e.preventDefault(); if(this.onHome) this.onHome(); return;}
    if(c==='KeyF'){e.preventDefault(); if(this.onFocus) this.onFocus(); return;}
    const id=this._keyId(c,k); if(!id) return; e.preventDefault();
    if(!this._keys.has(id)){this._keys.add(id); this._t=performance.now(); this._start();} this._shift=e.shiftKey;
  }
  _keyup(e){const id=this._keyId(e.code,e.key); if(id){this._keys.delete(id);} if(!this._keys.size) this._end();}
  _keyId(c,k){
    switch(c){case 'ArrowLeft':return 'rl';case 'ArrowRight':return 'rr';case 'ArrowUp':return 'ru';case 'ArrowDown':return 'rd';
      case 'KeyW':return 'pf';case 'KeyS':return 'pb';case 'KeyA':return 'pl';case 'KeyD':return 'pr';case 'KeyQ':return 'dn';case 'KeyE':return 'up';
      case 'NumpadAdd':return 'zi';case 'NumpadSubtract':return 'zo';}
    if(k==='+'||k==='=') return 'zi'; if(k==='-'||k==='_') return 'zo'; return null;
  }
  /* returns true while something is still moving (keys held / inertia) so the caller keeps rendering */
  update(){
    const now=performance.now(),dt=Math.min(0.1,(now-this._t)/1000); this._t=now; let busy=false;
    if(this._keys.size){
      busy=true; const sp=this._shift?2.6:1,K=this._keys,s=this._sph();
      let dth=0,dph=0; if(K.has('rl'))dth-=1; if(K.has('rr'))dth+=1; if(K.has('ru'))dph-=1; if(K.has('rd'))dph+=1;
      if(dth||dph) this.rotate(dth*1.5*sp*dt,dph*1.2*sp*dt);
      let f=0,r=0,v=0; if(K.has('pf'))f+=1; if(K.has('pb'))f-=1; if(K.has('pr'))r+=1; if(K.has('pl'))r-=1; if(K.has('up'))v+=1; if(K.has('dn'))v-=1;
      if(f||r||v){const sd=s.r*0.9*sp*dt; this._f.copy(this.target).sub(this.camera.position); this._f.y=0; if(this._f.lengthSq()<1e-9) this._f.set(0,0,-1); this._f.normalize(); this._r.crossVectors(this._f,this.camera.up).normalize();
        this.moveWorld((this._f.x*f+this._r.x*r)*sd,v*sd*0.8,(this._f.z*f+this._r.z*r)*sd);}
      let z=0; if(K.has('zi'))z-=1; if(K.has('zo'))z+=1; if(z) this.dolly(Math.exp(z*1.1*this.zoomSpeed*sp*dt));
    }
    if(!this._ptrs.size&&(Math.abs(this._vel.th)>1e-5||Math.abs(this._vel.ph)>1e-5)){
      busy=true; const f=Math.pow(0.9,dt*60); this.rotate(this._vel.th*dt*60,this._vel.ph*dt*60); this._vel.th*=f; this._vel.ph*=f; if(Math.abs(this._vel.th)<1e-5&&Math.abs(this._vel.ph)<1e-5){this._vel.th=this._vel.ph=0;}
    }
    return busy||this._ptrs.size>0;
  }
  stop(){this._vel.th=this._vel.ph=0;}
}
