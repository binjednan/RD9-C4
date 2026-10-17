# -*- coding: utf-8 -*-
"""Boot the built viewer in headless Chrome (run OUTSIDE the sandbox) and print: element count, errors, a JS expression result.
  python3 tools/viewer_probe.py ["<js expression>"]"""
import json, os, subprocess, sys, tempfile, time, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
from cdp import Page
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
udir = tempfile.mkdtemp(prefix="c4probe_")
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8767", "--bind", "127.0.0.1"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
ch = subprocess.Popen([CHROME, "--headless=new", "--no-sandbox", "--remote-debugging-port=9334", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                       "--user-data-dir=" + udir, "--no-first-run", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    import urllib.request
    for _ in range(60):
        try: urllib.request.urlopen("http://127.0.0.1:9334/json/version"); break
        except Exception: time.sleep(0.5)
    p = Page(port=9334); p.size(1400, 900)
    p.call("Runtime.enable"); p.call("Page.enable")
    p.eval("window.__errs=[];window.addEventListener('error',e=>window.__errs.push(String(e.message)));0")
    p.call("Page.navigate", url="http://127.0.0.1:8767/index.html?probe=%d" % int(time.time()))
    p.wait("window.__dbg", timeout=240); time.sleep(4)
    p.eval("window.__errs=window.__errs||[];0")
    for js in (sys.argv[1:] or ["JSON.stringify({keys:Object.keys(window.__dbg||{}).slice(0,12)})"]):
        print(json.dumps(p.eval(js), ensure_ascii=False)[:3000])
    print("errors:", p.eval("JSON.stringify(window.__errs||[])"))
    p.close()
finally:
    ch.terminate(); srv.terminate(); time.sleep(1); shutil.rmtree(udir, ignore_errors=True)
