# -*- coding: utf-8 -*-
"""build dev viewer.html (separate files) and the single-file index.html (everything inlined)"""
import sys, os, json, datetime, re
WWW=os.path.dirname(os.path.abspath(__file__))
OUT_DIR=os.path.dirname(WWW)
def rd(n): return open(os.path.join(WWW,n),encoding="utf-8").read()
tpl=rd("template.html")
ver=datetime.datetime.now().strftime("v%Y.%m.%d-%H%M")
tpl=tpl.replace("{{VERSION}}",ver)
# ---- dev
dev=tpl.replace("{{SCRIPTS}}","""<script src="three.min.js"></script><script src="engine.js"></script><script src="controls.js"></script><script src="detail.js"></script><script src="clash.js"></script>
<script>Promise.all([fetch('model.json').then(r=>r.json()),fetch('samples.json').then(r=>r.json()).catch(()=>null)]).then(([m,sm])=>{window.__MODEL__=m;window.__SAMPLES__=sm;const s=document.createElement('script');s.src='app.js?'+Date.now();document.body.appendChild(s);});</script>""")
open(os.path.join(WWW,"viewer.html"),"w",encoding="utf-8").write(dev)
# ---- single file
three=rd("three.min.js"); eng=rd("engine.js"); ctl=rd("controls.js"); det=rd("detail.js"); cls=rd("clash.js"); app=rd("app.js")
smp=open(os.path.join(WWW,"samples.json"),encoding="utf-8").read() if os.path.exists(os.path.join(WWW,"samples.json")) else "null"
model=open(os.path.join(WWW,"model.json"),encoding="utf-8").read()
for name,src in (("three",three),("engine",eng),("controls",ctl),("detail",det),("clash",cls),("app",app)):
    assert "</script" not in src.lower(), name
model_safe=model.replace("</","<\\/"); smp_safe=smp.replace("</","<\\/")
boot="""<script id="appsrc" type="text/plain">%s</script>
<script id="mdl" type="application/json">%s</script>
<script id="smp" type="application/json">%s</script>
<script>
requestAnimationFrame(function(){setTimeout(function(){
  try{
    window.__MODEL__=JSON.parse(document.getElementById('mdl').textContent);
    try{window.__SAMPLES__=JSON.parse(document.getElementById('smp').textContent);}catch(e){window.__SAMPLES__=null;}
    var s=document.createElement('script'); s.text=document.getElementById('appsrc').textContent; document.body.appendChild(s);
  }catch(e){ var m=document.getElementById('lmsg'); if(m) m.textContent='تعذّر تشغيل النموذج: '+e.message; console.error(e); }
},40);});
</script>""" % (app,model_safe,smp_safe)
single=tpl.replace("{{SCRIPTS}}","<script>"+three+"</script>\n<script>"+eng+"</script>\n<script>"+ctl+"</script>\n<script>"+det+"</script>\n<script>"+cls+"</script>\n"+boot)
os.makedirs(OUT_DIR,exist_ok=True)
p=os.path.join(OUT_DIR,"index.html")
open(p,"w",encoding="utf-8").write(single)
print("built",ver,"index.html",round(os.path.getsize(p)/1e6,2),"MB")
