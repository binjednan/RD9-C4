/* ===== PlanMap: a 2-D plan of one level drawn from the model itself, with pins (idea: Revizto issue pins on 2-D sheets, Matterport floor-plan view) =====
   Walls, columns, slab outline, doors, windows and stairs of the chosen level are drawn from M.els; pins and arrows (before → after of a best guess) sit on top; the 3-D camera is shown
   as a small cone so the plan and the model always agree.  Wheel / pinch = zoom, drag = pan, tap a pin = pick it, tap empty ground = fly the 3-D camera there. */
(function(){
'use strict';
function ringPath(p,ring){ring.forEach((q,i)=>{if(i) p.lineTo(q[0],q[1]); else p.moveTo(q[0],q[1]);}); p.closePath();}
function geomRings(g){
  if(g[0]==='p') return {rings:[g[1]].concat(g[4]&&g[4].length?g[4]:[]),holes:g[4]&&g[4].length?g[4].length:0};
  if(g[0]==='r'){const x0=Math.min(g[1],g[3]),x1=Math.max(g[1],g[3]),y0=Math.min(g[2],g[4]),y1=Math.max(g[2],g[4]); return {rings:[[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]],holes:0};}
  if(g[0]==='b'){const a=g[5]*Math.PI/180,c=Math.cos(a),s=Math.sin(a),hw=g[3]/2,hd=g[4]/2; const P=[[-hw,-hd],[hw,-hd],[hw,hd],[-hw,hd]].map(q=>[g[1]+q[0]*c-q[1]*s,g[2]+q[0]*s+q[1]*c]); return {rings:[P],holes:0};}
  if(g[0]==='cyl'){const R=g[3],P=[]; for(let i=0;i<10;i++){const t=i/10*2*Math.PI; P.push([g[1]+R*Math.cos(t),g[2]+R*Math.sin(t)]);} return {rings:[P],holes:0};}
  return null;
}
class PlanMap{
  constructor(canvas,ctx){
    this.cv=canvas; this.g=canvas.getContext('2d'); this.M=ctx.M; this.LVL=ctx.LVL; this.level=null; this.pins=[]; this.arrows=[]; this.cam=null; this.sel=null;
    this.k=0.1; this.ox=0; this.oy=0; this.cache={}; this.onPick=null; this.onGround=null; this.interactive=ctx.interactive!==false; this.dpr=Math.min(2,window.devicePixelRatio||1);
    this._bind();
  }
  _layers(lv){
    if(this.cache[lv]) return this.cache[lv];
    const L={slab:new Path2D(),walls:new Path2D(),cols:new Path2D(),doors:new Path2D(),wins:new Path2D(),stairs:new Path2D(),tanks:new Path2D(),bb:[1e9,1e9,-1e9,-1e9]};
    const grow=(rings)=>{rings.forEach(r=>r.forEach(q=>{if(q[0]<L.bb[0])L.bb[0]=q[0];if(q[1]<L.bb[1])L.bb[1]=q[1];if(q[0]>L.bb[2])L.bb[2]=q[0];if(q[1]>L.bb[3])L.bb[3]=q[1];}));};
    for(const e of this.M.els){ if(e.l!==lv) continue; const c=e.c; let tgt=null;
      if(c==='A.wall'||c==='S.wall') tgt=L.walls; else if(c==='S.col') tgt=L.cols; else if(c==='A.door') tgt=L.doors; else if(c==='A.win'&&e.t!=='win_sill') tgt=L.wins; else if(c==='S.stair') tgt=L.stairs; else if(c==='S.slab'||c==='S.raft') tgt=L.slab; else if(c==='P.tank') tgt=L.tanks;
      if(!tgt) continue; const gr=geomRings(e.g); if(!gr) continue;
      if(c==='S.slab'||c==='S.raft'){ // slab with holes: even-odd fill later
        gr.rings.forEach(r=>ringPath(L.slab,r)); continue; }
      gr.rings.forEach(r=>ringPath(tgt,r));
      if(tgt===L.walls||tgt===L.cols) grow(gr.rings);
    }
    if(L.bb[0]>1e8){L.bb=[0,0,3400,1900];}
    this.cache[lv]=L; return L;
  }
  setLevel(id,keepView){this.level=id; this.L=this._layers(id); if(!keepView) this.fit(); else this.draw();}
  fit(pad=24){const b=this.L.bb; const w=this.cv.clientWidth,h=this.cv.clientHeight; const bw=b[2]-b[0]+160,bh=b[3]-b[1]+160; this.k=Math.min((w-pad)/bw,(h-pad)/bh); this.ox=w/2-(b[0]+b[2])/2*this.k; this.oy=h/2+(b[1]+b[3])/2*this.k; this.draw();}
  resize(){const r=this.cv.getBoundingClientRect(); const w=Math.max(60,Math.round(r.width)),h=Math.max(60,Math.round(r.height)); if(this.cv.width!==w*this.dpr||this.cv.height!==h*this.dpr){this.cv.width=w*this.dpr;this.cv.height=h*this.dpr;} if(this.L) this.fit();}
  setPins(p){this.pins=p||[]; this.draw();}
  setArrows(a){this.arrows=a||[]; this.draw();}
  setCamera(c){this.cam=c; this.draw();}
  setSel(k){this.sel=k; this.draw();}
  px(x,y){return [x*this.k+this.ox, -y*this.k+this.oy];}
  mm(px,py){return [(px-this.ox)/this.k, -(py-this.oy)/this.k];}
  draw(){
    const g=this.g,cv=this.cv,L=this.L; if(!L) return; const dpr=this.dpr; g.setTransform(dpr,0,0,dpr,0,0); g.clearRect(0,0,cv.clientWidth,cv.clientHeight);
    g.fillStyle='#f6f8fb'; g.fillRect(0,0,cv.clientWidth,cv.clientHeight);
    g.save(); g.translate(this.ox,this.oy); g.scale(this.k,-this.k);
    g.fillStyle='#e9eef4'; g.fill(L.slab,'evenodd'); g.lineWidth=1.2/this.k; g.strokeStyle='#c7d0db'; g.stroke(L.slab);
    g.fillStyle='#d3d9e1'; g.fill(L.stairs); g.fillStyle='#bcd3ea'; g.fill(L.tanks);
    g.fillStyle='#46515f'; g.fill(L.walls); g.fillStyle='#16202c'; g.fill(L.cols);
    g.fillStyle='#8cc0ee'; g.fill(L.wins); g.fillStyle='#d88a3a'; g.fill(L.doors);
    g.restore();
    // arrows (before -> after)
    this.arrows.forEach(a=>{const p=this.px(a.x0,a.y0),q=this.px(a.x1,a.y1); g.strokeStyle=a.c||'#0072B2'; g.fillStyle=g.strokeStyle; g.lineWidth=1.6; g.setLineDash([4,3]); g.beginPath(); g.moveTo(p[0],p[1]); g.lineTo(q[0],q[1]); g.stroke(); g.setLineDash([]); g.beginPath(); g.arc(p[0],p[1],3,0,7); g.globalAlpha=0.55; g.fill(); g.globalAlpha=1; const an=Math.atan2(q[1]-p[1],q[0]-p[0]); g.beginPath(); g.moveTo(q[0],q[1]); g.lineTo(q[0]-8*Math.cos(an-0.45),q[1]-8*Math.sin(an-0.45)); g.lineTo(q[0]-8*Math.cos(an+0.45),q[1]-8*Math.sin(an+0.45)); g.closePath(); g.fill();});
    // pins
    this.pins.forEach(pn=>{ if(pn.l&&pn.l!==this.level) return; const p=this.px(pn.x,pn.y); const r=(pn.r||6)*(pn.k===this.sel?1.5:1); g.fillStyle=pn.c||'#d55e00'; g.strokeStyle='#fff'; g.lineWidth=pn.k===this.sel?2.5:1.5; g.globalAlpha=pn.dim?0.45:1;
      g.beginPath(); const s=pn.s||'o';
      if(s==='s'){g.rect(p[0]-r,p[1]-r,2*r,2*r);} else if(s==='d'){g.moveTo(p[0],p[1]-r*1.25);g.lineTo(p[0]+r*1.25,p[1]);g.lineTo(p[0],p[1]+r*1.25);g.lineTo(p[0]-r*1.25,p[1]);g.closePath();} else if(s==='t'){g.moveTo(p[0],p[1]-r*1.2);g.lineTo(p[0]+r*1.1,p[1]+r);g.lineTo(p[0]-r*1.1,p[1]+r);g.closePath();} else {g.arc(p[0],p[1],r,0,7);}
      g.fill(); g.stroke(); g.globalAlpha=1; if(pn.k===this.sel){g.strokeStyle=pn.c||'#d55e00'; g.lineWidth=1.5; g.beginPath(); g.arc(p[0],p[1],r+6,0,7); g.stroke();} });
    // camera cone
    if(this.cam){const p=this.px(this.cam.x,this.cam.y); const a=this.cam.yaw; g.fillStyle='rgba(31,111,235,.22)'; g.strokeStyle='#1f6feb'; g.lineWidth=1.4; g.beginPath(); g.moveTo(p[0],p[1]); g.arc(p[0],p[1],22,a-0.55,a+0.55); g.closePath(); g.fill(); g.stroke(); g.fillStyle='#1f6feb'; g.beginPath(); g.arc(p[0],p[1],3.4,0,7); g.fill();}
    // level title
    const lv=this.LVL[this.level]; if(lv){g.fillStyle='#223'; g.font='600 11.5px system-ui,sans-serif'; g.textAlign='right'; g.fillText((lv.name)+' ('+(lv.ffl>0?'+':'')+lv.ffl.toFixed(2)+')',cv.clientWidth-8,16);}
  }
  _bind(){
    if(!this.interactive) return; const cv=this.cv; cv.style.touchAction='none'; const pts=new Map(); let drag=null,pinch=null,moved=0;
    cv.addEventListener('pointerdown',e=>{cv.setPointerCapture(e.pointerId); pts.set(e.pointerId,[e.clientX,e.clientY]); drag=[e.clientX,e.clientY]; moved=0; if(pts.size===2){const a=[...pts.values()]; pinch=Math.hypot(a[0][0]-a[1][0],a[0][1]-a[1][1]);}});
    cv.addEventListener('pointermove',e=>{ if(!pts.has(e.pointerId)) return; const old=pts.get(e.pointerId); pts.set(e.pointerId,[e.clientX,e.clientY]);
      if(pts.size===2){const a=[...pts.values()],d=Math.hypot(a[0][0]-a[1][0],a[0][1]-a[1][1]); if(pinch) this._zoom(d/pinch,(a[0][0]+a[1][0])/2,(a[0][1]+a[1][1])/2); pinch=d; moved=99; return;}
      if(!drag) return; this.ox+=e.clientX-old[0]; this.oy+=e.clientY-old[1]; moved+=Math.abs(e.clientX-old[0])+Math.abs(e.clientY-old[1]); this.draw();});
    const up=e=>{ if(!pts.has(e.pointerId)) return; pts.delete(e.pointerId); if(pts.size<2) pinch=null; if(!pts.size){ if(moved<6) this._tap(e.clientX,e.clientY); drag=null; } };
    cv.addEventListener('pointerup',up); cv.addEventListener('pointercancel',up);
    cv.addEventListener('wheel',e=>{e.preventDefault(); this._zoom(Math.exp(-e.deltaY*0.0015),e.clientX,e.clientY);},{passive:false});
    cv.addEventListener('dblclick',()=>this.fit());
  }
  _zoom(f,cx,cy){const r=this.cv.getBoundingClientRect(); const x=cx-r.left,y=cy-r.top; const nk=Math.min(2,Math.max(0.02,this.k*f)); const mx=(x-this.ox)/this.k,my=(y-this.oy)/this.k; this.k=nk; this.ox=x-mx*nk; this.oy=y-my*nk; this.draw();}
  _tap(cx,cy){const r=this.cv.getBoundingClientRect(); const x=cx-r.left,y=cy-r.top; let best=null,bd=1e9;
    this.pins.forEach(pn=>{ if(pn.l&&pn.l!==this.level) return; const p=this.px(pn.x,pn.y); const d=Math.hypot(p[0]-x,p[1]-y); if(d<Math.max(14,(pn.r||6)+7)&&d<bd){bd=d;best=pn;}});
    if(best&&this.onPick){this.onPick(best); return;} const m=this.mm(x,y); if(this.onGround) this.onGround(m[0],m[1],this.level); }
}
window.PlanMap=PlanMap;
})();
