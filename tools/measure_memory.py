# -*- coding: utf-8 -*-
"""Boot index.html in headless Chrome and report memory (needs to run OUTSIDE the Bash sandbox).

  python3 tools/measure_memory.py [--wait 6]

Prints: boot seconds, element count seen by the viewer, JS heap MB, and process RSS MB (sum over the Chrome process
tree started here, plus the biggest process).  Limit to hold: 800 MB total RSS.  Run twice for a stable number.
"""
import argparse, json, os, subprocess, sys, tempfile, time, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from cdp import Page
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

def rss_tree(tag):
    out = subprocess.run(["ps", "-axo", "pid=,rss=,command="], capture_output=True, text=True).stdout
    rows = []
    for ln in out.splitlines():
        p = ln.split(None, 2)
        if len(p) == 3 and tag in p[2]:
            rows.append((int(p[1]) / 1024.0, int(p[0]), p[2][:60]))
    return rows

def once(root, port, wait):
    udir = tempfile.mkdtemp(prefix="c4mem_")
    srv = subprocess.Popen([sys.executable, "-m", "http.server", str(port + 100), "--bind", "127.0.0.1"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ch = subprocess.Popen([CHROME, "--headless=new", "--no-sandbox", "--remote-debugging-port=%d" % port, "--use-gl=angle", "--use-angle=swiftshader",
                           "--enable-unsafe-swiftshader", "--user-data-dir=" + udir, "--no-first-run", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        import urllib.request
        for _ in range(60):
            try: urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port); break
            except Exception: time.sleep(0.5)
        p = Page(port=port); p.size(1400, 900)
        t0 = time.time(); p.call("Page.navigate", url="http://127.0.0.1:%d/index.html?mem=%d" % (port + 100, int(t0)))
        p.wait("window.__dbg", timeout=240); boot = time.time() - t0
        time.sleep(wait)
        p.call("HeapProfiler.enable"); p.call("HeapProfiler.collectGarbage"); heap = p.call("Runtime.getHeapUsage")["usedSize"] / 1048576.0
        rows = rss_tree(udir); tot = sum(r[0] for r in rows); big = max(rows)[0] if rows else 0
        p.close()
        return {"boot_s": round(boot, 2), "js_heap_gc_mb": round(heap, 1), "rss_total_mb": round(tot), "rss_largest_mb": round(big)}
    finally:
        ch.terminate(); srv.terminate(); time.sleep(2); shutil.rmtree(udir, ignore_errors=True)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--wait", type=float, default=6); ap.add_argument("--port", type=int, default=9333); ap.add_argument("--root", default=ROOT); ap.add_argument("--runs", type=int, default=3); a = ap.parse_args()
    rs = [once(a.root, a.port + 7 * i, a.wait) for i in range(a.runs)]
    big = sorted(r["rss_largest_mb"] for r in rs)
    print(json.dumps({"runs": a.runs, "rss_largest_mb_median": big[len(big) // 2], "rss_largest_mb_min": big[0], "rss_largest_mb_max": big[-1],
                      "js_heap_gc_mb_median": sorted(r["js_heap_gc_mb"] for r in rs)[len(rs) // 2], "boot_s_median": sorted(r["boot_s"] for r in rs)[len(rs) // 2], "all": [r["rss_largest_mb"] for r in rs]}))

if __name__ == "__main__":
    main()
