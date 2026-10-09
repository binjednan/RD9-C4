# -*- coding: utf-8 -*-
"""build dev viewer.html (separate files) and the single-file index.html (everything inlined)"""
import sys, os, json, datetime, re, gzip, base64
WWW=os.path.dirname(os.path.abspath(__file__))
OUT_DIR=os.path.dirname(WWW)
def rd(n): return open(os.path.join(WWW,n),encoding="utf-8").read()
# libraries / modules loaded before app.js, in order (each one registers itself on window)
MODS=["three.min.js","engine.js","controls.js","detail.js","lens.js","planmap.js","thumbs.js","clash.js","issues.js","project-review.js","tours.js","notes.js","look.js","measure.js","sections.js","views.js","hub.js","life.js","hint.js","samples-ui.js"]
MODS=[m for m in MODS if os.path.exists(os.path.join(WWW,m))]
palette=json.load(open(os.path.join(OUT_DIR,"pipeline","data","display_palette.json"),encoding="utf-8"))
paltag="<script>window.C4_PALETTE="+json.dumps(palette,ensure_ascii=False,separators=(",",":"))+";</script>"
tpl=rd("template.html")
ver=datetime.datetime.now().strftime("v%Y.%m.%d-%H%M")
tpl=tpl.replace("{{VERSION}}",ver)
# Conflict witnesses are never parsed or decompressed at boot.
evidence_path=os.path.join(OUT_DIR,'pipeline','data','source_conflict_evidence.json')
evidence_bytes=open(evidence_path,'rb').read() if os.path.exists(evidence_path) else b'{}'
evidence_b64=base64.b64encode(gzip.compress(evidence_bytes,mtime=0)).decode('ascii')
evidence_tag='<script id="conflict-evidence" type="application/json" data-encoding="gzip-base64">'+json.dumps(evidence_b64)+'</script>'
evidence_loader="""<script>
window.loadConflictEvidence=function(){
 if(!window.__conflictEvidencePromise)window.__conflictEvidencePromise=(async function(){
  const encoded=JSON.parse(document.getElementById('conflict-evidence').textContent);
  const data=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
  const stream=new Blob([data]).stream().pipeThrough(new DecompressionStream('gzip'));
  return JSON.parse(await new Response(stream).text());
 })();return window.__conflictEvidencePromise;
};
</script>"""
# ---- dev
tags="".join('<script src="%s"></script>'%m for m in MODS)
dev=tpl.replace("{{SCRIPTS}}",paltag+evidence_tag+evidence_loader+tags+"""
<script>Promise.all([fetch('model.json').then(r=>r.json()),fetch('samples.json').then(r=>r.json()).catch(()=>null),fetch('photos.json').then(r=>r.json()).catch(()=>null)]).then(([m,sm,ph])=>{window.__MODEL__=m;window.__SAMPLES__=sm;window.__PHOTOS__=ph;const s=document.createElement('script');s.src='app.js?'+Date.now();document.body.appendChild(s);});</script>""")
open(os.path.join(WWW,"viewer.html"),"w",encoding="utf-8").write(dev)
# ---- single file
app=rd("app.js")
srcs={m:rd(m) for m in MODS}
def opt(n): 
    p=os.path.join(WWW,n); return open(p,encoding="utf-8").read() if os.path.exists(p) else "null"
smp=opt("samples.json"); photos=opt("photos.json")
model_data=json.loads(open(os.path.join(WWW,"model.json"),encoding="utf-8").read())
# Gate inputs and historical conformity reports are never shipped to the viewer.
model_data['meta']={k:v for k,v in model_data.get('meta',{}).items() if k in ('project','owner_render_only')}
for retired in ('modelMatching','raftModelAcceptance','componentReview','materialReview'):
    model_data.pop(retired,None)
model_data['drawingIssues']=[d for d in model_data.get('drawingIssues',[]) if d.get('status')!='corrected']
for issue in model_data.get('coordinationReview',{}).get('issues',[]):
    for field in ('geometry','case_audit_ar','source'):
        issue.pop(field,None)
model_json=json.dumps(model_data,ensure_ascii=False,separators=(',',':'))
model=json.dumps(base64.b64encode(gzip.compress(model_json.encode('utf-8'),mtime=0)).decode('ascii'))
# Keep canonical geometry unchanged in the deliverable: source audit, clash witness
# and selection all refer to these exact polygons, rather than display simplification.
print("viewer geometry: canonical source-model polygons retained")
for name,src in list(srcs.items())+[("app",app)]:
    assert "</script" not in src.lower(), name
safe=lambda t:t.replace("</","<\\/")
boot="""<script id="appsrc" type="text/plain">%s</script>
<script id="mdl" type="application/json" data-encoding="gzip-base64">%s</script>
<script id="smp" type="application/json">%s</script>
<script id="pho" type="application/json">%s</script>
<script>
requestAnimationFrame(function(){setTimeout(async function(){
  try{
    const encoded=JSON.parse(document.getElementById('mdl').textContent);
    const bytes=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
    const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'));
    window.__MODEL__=JSON.parse(await new Response(stream).text());
    try{window.__SAMPLES__=JSON.parse(document.getElementById('smp').textContent);}catch(e){window.__SAMPLES__=null;}
    try{window.__PHOTOS__=JSON.parse(document.getElementById('pho').textContent);}catch(e){window.__PHOTOS__=null;}
    var s=document.createElement('script'); s.text=document.getElementById('appsrc').textContent; document.body.appendChild(s);
  }catch(e){ var m=document.getElementById('lmsg'); if(m) m.textContent='تعذّر تشغيل النموذج: '+e.message; console.error(e); }
},40);});
</script>""" % (safe(app),safe(model),safe(smp),safe(photos))
single=tpl.replace("{{SCRIPTS}}",paltag+evidence_tag+evidence_loader+"\n".join("<script>"+srcs[m]+"</script>" for m in MODS)+"\n"+boot)
os.makedirs(OUT_DIR,exist_ok=True)
p=os.path.join(OUT_DIR,"index.html")
open(p,"w",encoding="utf-8").write(single)
print("built",ver,"index.html",round(os.path.getsize(p)/1e6,2),"MB | modules:",",".join(MODS))
