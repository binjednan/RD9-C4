# -*- coding: utf-8 -*-
"""build dev viewer.html (separate files) and the single-file index.html (everything inlined)"""
import sys, os, json, datetime, re
WWW=os.path.dirname(os.path.abspath(__file__))
OUT_DIR=os.path.dirname(WWW)
def rd(n): return open(os.path.join(WWW,n),encoding="utf-8").read()
# libraries / modules loaded before app.js, in order (each one registers itself on window)
MODS=["three.min.js","engine.js","controls.js","detail.js","lens.js","planmap.js","thumbs.js","clash.js","issues.js","hub.js","samples-ui.js"]
MODS=[m for m in MODS if os.path.exists(os.path.join(WWW,m))]
tpl=rd("template.html")
ver=datetime.datetime.now().strftime("v%Y.%m.%d-%H%M")
tpl=tpl.replace("{{VERSION}}",ver)
# ---- dev
tags="".join('<script src="%s"></script>'%m for m in MODS)
dev=tpl.replace("{{SCRIPTS}}",tags+"""
<script>Promise.all([fetch('model.json').then(r=>r.json()),fetch('samples.json').then(r=>r.json()).catch(()=>null),fetch('photos.json').then(r=>r.json()).catch(()=>null)]).then(([m,sm,ph])=>{window.__MODEL__=m;window.__SAMPLES__=sm;window.__PHOTOS__=ph;const s=document.createElement('script');s.src='app.js?'+Date.now();document.body.appendChild(s);});</script>""")
open(os.path.join(WWW,"viewer.html"),"w",encoding="utf-8").write(dev)
# ---- single file
app=rd("app.js")
srcs={m:rd(m) for m in MODS}
def opt(n): 
    p=os.path.join(WWW,n); return open(p,encoding="utf-8").read() if os.path.exists(p) else "null"
smp=opt("samples.json"); photos=opt("photos.json")
model=open(os.path.join(WWW,"model.json"),encoding="utf-8").read()
for name,src in list(srcs.items())+[("app",app)]:
    assert "</script" not in src.lower(), name
safe=lambda t:t.replace("</","<\\/")
boot="""<script id="appsrc" type="text/plain">%s</script>
<script id="mdl" type="application/json">%s</script>
<script id="smp" type="application/json">%s</script>
<script id="pho" type="application/json">%s</script>
<script>
requestAnimationFrame(function(){setTimeout(function(){
  try{
    window.__MODEL__=JSON.parse(document.getElementById('mdl').textContent);
    try{window.__SAMPLES__=JSON.parse(document.getElementById('smp').textContent);}catch(e){window.__SAMPLES__=null;}
    try{window.__PHOTOS__=JSON.parse(document.getElementById('pho').textContent);}catch(e){window.__PHOTOS__=null;}
    var s=document.createElement('script'); s.text=document.getElementById('appsrc').textContent; document.body.appendChild(s);
  }catch(e){ var m=document.getElementById('lmsg'); if(m) m.textContent='تعذّر تشغيل النموذج: '+e.message; console.error(e); }
},40);});
</script>""" % (safe(app),safe(model),safe(smp),safe(photos))
single=tpl.replace("{{SCRIPTS}}","\n".join("<script>"+srcs[m]+"</script>" for m in MODS)+"\n"+boot)
os.makedirs(OUT_DIR,exist_ok=True)
p=os.path.join(OUT_DIR,"index.html")
open(p,"w",encoding="utf-8").write(single)
print("built",ver,"index.html",round(os.path.getsize(p)/1e6,2),"MB | modules:",",".join(MODS))
