# -*- coding: utf-8 -*-
"""assemble the sample library -> src/samples.json  (+ docs/SAMPLES.md catalog + coverage check against src/model.json)
   python3 pipeline/samples_build.py"""
import json, os, sys, importlib, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
MODS = ["arch", "windows", "elec", "mep", "plumb_fire", "paths", "finish", "struct", "site"]
CLASSES = {
    "matte": {"rough": 0.85, "metal": 0.0}, "metal": {"rough": 0.4, "metal": 0.3}, "gloss": {"rough": 0.18, "metal": 0.05}, "rubber": {"rough": 0.95, "metal": 0.0},
    "glass": {"rough": 0.05, "metal": 0.0, "opacity": 0.30}, "ghost": {"rough": 0.9, "metal": 0.0, "opacity": 0.22}, "emit": {"basic": True},
}

def main():
    samples = {}; rules = []
    for mn in MODS:
        try: m = importlib.import_module("samples." + mn)
        except ModuleNotFoundError as e:
            if e.name == "samples." + mn: continue
            raise
        out = m.make(); samples.update(out)
        for r in getattr(m, "RULES", []): rules.append(r)
    lib = {"v": 1, "title": "مكتبة العينات التفصيلية — مشروع C4 (RD09)", "classes": CLASSES, "samples": samples, "map": rules,
           "note": "عينة واقعية مفصلة لكل نوع مكوّن؛ تحل محل المجسم المبسّط في النموذج عند التقريب. الأبعاد الأساسية من المستندات وما عداها قياسي موسوم في «asm»."}
    json.dump(lib, open(os.path.join(ROOT, "src", "samples.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print("samples:", len(samples), "rules:", len(rules), "size KB:", os.path.getsize(os.path.join(ROOT, "src", "samples.json")) // 1024)
    # coverage against the model
    M = json.load(open(os.path.join(ROOT, "src", "model.json"), encoding="utf-8"))
    def match(e):
        for r in rules:
            if r.get("c") and r["c"] != e["c"]: continue
            t = r.get("t")
            if t:
                if t.endswith("*"):
                    if not (e["t"] and e["t"].startswith(t[:-1])): continue
                elif t != e["t"]: continue
            return r["s"]
        return None
    cov = collections.Counter(); miss = collections.Counter()
    for e in M["els"]:
        s = match(e)
        if s: cov[(e["c"], e["t"])] += 1
        else: miss[(e["c"], e["t"])] += 1
    print("types covered:", len(cov), "| elements covered:", sum(cov.values()), "of", len(M["els"]))
    # human-readable catalog
    CAT = {"architecture": "العمارة", "electrical": "الكهرباء", "mechanical": "الميكانيكا (تكييف وتهوية)", "plumbing": "السباكة والصرف", "fire": "الإطفاء", "structure": "الإنشائي"}
    CONF = {"doc": "من المستندات", "derived": "مشتق من المستندات", "assumed": "افتراض"}
    byc = collections.defaultdict(list)
    for sid, sm in samples.items(): byc[sm["cat"]].append((sid, sm))
    out = ["# مكتبة العينات التفصيلية", "", "يُولَّد آليًا من `pipeline/samples/*.py` عبر `python3 pipeline/samples_build.py` (الملف الناتج: `src/samples.json` المدمج في المُعرِض).",
           "عند تقريب الكاميرا من مكوّن له عينة، يستبدل المُعرِض مجسّمه المبسّط بالعينة التفصيلية ويعيده عند الابتعاد. الأبعاد الأساسية من المستندات؛ ما سواه قياسي ومذكور في عمود «افتراضات».", "",
           f"عدد العينات: **{len(samples)}** · عدد قواعد الربط بأنواع النموذج: **{len(rules)}**", ""]
    for cat in ("architecture", "electrical", "mechanical", "plumbing", "fire", "structure"):
        if cat not in byc: continue
        out += [f"## {CAT[cat]}", "", "| المعرّف | الاسم | النوع | الدرجة | حقائق من المستندات | افتراضات |", "|---|---|---|---|---|---|"]
        for sid, sm in sorted(byc[cat]):
            facts = "؛ ".join(f"{a}: {b}" for a, b in sm["facts"][:5]); asm = "؛ ".join(sm["asm"][:3])
            out.append(f"| `{sid}` | {sm['name']} | {sm['kind']} | {CONF.get(sm['conf'], sm['conf'])} | {facts} | {asm} |")
        out.append("")
    open(os.path.join(ROOT, "docs", "SAMPLES.md"), "w", encoding="utf-8").write("\n".join(out))
    if miss:
        print("NOT covered:")
        for k, v in sorted(miss.items(), key=lambda x: -x[1]): print("   ", k, v)
if __name__ == "__main__":
    main()
