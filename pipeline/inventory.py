# -*- coding: utf-8 -*-
"""Full inventory of the project (owner 2026-10-07: «قم بجرد المشروع بالكامل»): sources, model, reliability, issues, viewer, code, docs and deliverables.

build(M) -> M['inventory'] (a compact dict the viewer's «نظرة عامة» shows) and write_doc(M) -> docs/INVENTORY.md (the same facts as a readable Arabic report).
Everything is measured from the files themselves on every run (nothing is typed by hand except the feature list, which is verified by looking for the code that implements each feature)."""
import os, re, json, collections, datetime

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
SET_AR = {"ARCH1": "المعماري — الجزء 1", "ARCH2": "المعماري — الجزء 2", "STR": "الإنشائي", "MECH1": "الميكانيكا — الجزء 1", "MECH2": "الميكانيكا — الجزء 2",
          "ELEC1": "الكهرباء — الجزء 1", "ELEC2": "الكهرباء — الجزء 2"}
PAT = re.compile(r"\b(ARCH1|ARCH2|STR|MECH1|MECH2|ELEC1|ELEC2)\s*(?:p|P|ص)\s*(\d+)(?:\s*[–\-]\s*(\d+))?")
KIND_WORDS = [("notes", ("NOTES", "LEGEND", "CALCULATION", "SCHEDULE OF", "KEY")), ("schedule", ("SCHEDULE", "TABLE", "BOQ")), ("diagram", ("DIAGRAM", "SCHEMATIC", "RISER")),
              ("section", ("SECTION", "ELEVATION", "FACADE")), ("detail", ("DETAIL",)), ("plan", ("PLAN", "LAYOUT", "LOADING"))]
KIND_AR = {"plan": "مسقط", "section": "مقطع / واجهة", "detail": "تفصيل", "schedule": "جدول", "diagram": "مخطط تخطيطي", "notes": "ملاحظات / مفتاح", "other": "أخرى"}
# what each feature needs in the sources to count as implemented  (group, text, file, regex, note)
# note: "new" = a capability the owner asked for that is not obvious on screen · "warn" = a behaviour worth knowing before relying on the model · None = ordinary (listed in docs/INVENTORY.md only —
# the viewer's overview shows only what needs a note, owner 2026-10-08: «اذكر ما يحتاج للتنويه فقط»; a feature whose code is missing is always shown)
FEATURES = [
    ("المظهر", "مظهر «أبيض ورمادي» بظلال ناعمة وعمق، واختيار قسم في العدسة يُلوّنه وحده (العرض ▾ ← المظهر)", "look.js", r"initLook", "new"),
    ("المظهر", "«عزل» في العدسة: يبقى ما اخترته وحده، ولا يُحدَّد بالنقر إلا المعزول", "lens.js", r"hideRest", "new"),
    ("الكاميرا", "دوران حرّ بالسحب حتى أسفل المبنى لرؤية بطون البلاطات والسقوف والأساس", "controls.js", r"Math\.PI-0\.02", "new"),
    ("الكاميرا", "التدوير حول العنصر المحدد (تظهر حلقة عند مركزه)؛ وبلا تحديد يدور كما كان حول نقطة النظر", "controls.js", r"_rotateAbout", "new"),
    ("القص", "مستوى قص مرئي، وأزرار «مسقط الطابق» تقصّ عند +1.20 م وتنظر من أعلى", "sections.js", r"initSections", "new"),
    ("الأدوات", "إخفاء أي عنصر (H) وكتابة ملاحظة عليه لتنفيذها في التعديلات القادمة", "notes.js", r"initNotes", "new"),
    ("الأدوات", "قياس المسافة بين نقطتين تلتصق بأقرب ركن (M)", "measure.js", r"initMeasure", "new"),
    ("الأدوات", "حفظ المناظير ونسخ رابط يعيد المنظور نفسه لمن يفتحه", "views.js", r"initViews", "new"),
    ("تنبيه", "الملاحظات والمناظير تُحفظ في هذا المتصفح فقط؛ انسخها (أو انسخ الرابط) لتبقى", "notes.js", r"c4notes", "warn"),
    ("تنبيه", "الظلال والعمق تتوقفان أثناء القص وفي وضع الأداء", "look.js", r"clipActive", "warn"),
    ("تنبيه", "الكماليات الإخراجية (أثاث وأشجار وسيارات) للعرض لا للتنفيذ، وتُخفى من «الأقسام»", "app.js", r"STAGE_KINDS", "warn"),
    ("تنبيه", "الخوازيق تُعرض 30 سم تحت اللبشة للدلالة فقط (الطول الفعلي 13 م)", "pipeline/post_model.py", r"يُعرض 30 سم فقط", "warn"),
    ("تنبيه", "صور العينات مرخّصة ومنسوبة لأصحابها (docs/PHOTO_CREDITS.md)", "samples-ui.js", r"photoFigure", "warn"),
    ("3D", "نموذج ثلاثي الأبعاد بالمجسمات المجمّعة (Three.js) في ملف واحد", "app.js", r"buildAll\(", None),
    ("3D", "تحكم بالكاميرا: ماوس / تراك باد / لمس (إصبع تدوير، إصبعان تحريك وقرص)", "controls.js", r"pinchInZooms", None),
    ("3D", "قص أفقي وطولي وتفكيك الطوابق وعزل الوحدات (شقق)", "app.js", r"clipY|exitIso", None),
    ("3D", "إضاءة: نهار / غروب / ليل + تشغيل المصابيح", "app.js", r"applyPreset", None),
    ("اللوحة", "لوحة جانبية واحدة بأقسام قابلة للطيّ مع بحث سريع", "app.js", r"toggleSec", None),
    ("اللوحة", "بطاقة العنصر المحدد أعلى اللوحة (أقسام قابلة للطيّ، مصدر كل بيان)", "app.js", r"infoDock", None),
    ("اللوحة", "إخفاء اللوحة بزر وتذكّر الحالة", "app.js", r"setDock", None),
    ("التحليل", "تعارضات: قائمة بحالات ومسار وصول وجولة مشي", "clash.js", r"startTour", None),
    ("التحليل", "تصنيف التعارضات (مؤكد / مرشح اختلاف منسوب / هامشي) ومجموعات", "pipeline/clash_tiers.py", r"def classify", None),
    ("التحليل", "سجل التخمينات وأفضل موضع للمكوّنات بلا حامل", "pipeline/guesses.py", r"def relocate", None),
    ("التحليل", "درجة موثوقية لكل عنصر (موثّق / مشتق / تخمين / إخراجي)", "pipeline/reliability.py", r"def assign", None),
    ("الأنظمة", "التهوية: مجاري الشفط والهواء النقي والناشرات والشبكات السلكية والمخمّدات والصواعد ومراوح الدور الأرضي (مخططات VE-100…VE-105)", "pipeline/vent_build.py", r"def build", None),
    ("الأنظمة", "اختبارات دورة الحياة لتسعة أنظمة (كهرباء، إطفاء، مبردة، هواء تغذية، تهوية نقية وشفط، باردة، ساخنة، صرف)", "pipeline/lifecycle.py", r"SYSTEMS", None),
    ("العينات", "مكتبة عينات تفصيلية بمعاينة منفردة وانتقال إلى الموضع", "samples-ui.js", r"openPreview", None),
    ("العينات", "حديد التسليح بالأسياخ المستديرة عند الطلب", "detail.js", r"setRebar", None),
    ("الواجهة", "تبديل ما يفعله السحب بإصبع واحد (أزرار الوضع)", "app.js", r"setModes", None),
]
LOC_GROUPS = [("pipeline", "pipeline/*.py"), ("samples", "pipeline/samples/*.py"), ("viewer", "src/*.js"), ("template", "src/template.html")]


def _read(p):
    try: return open(p, encoding="utf-8").read()
    except Exception: return ""


def _loc(pattern):
    import glob
    n = 0; files = 0
    for f in glob.glob(os.path.join(ROOT, pattern)):
        if os.path.basename(f) in ("three.min.js", "model.json", "samples.json"): continue
        n += _read(f).count("\n"); files += 1
    return files, n


def sheets(M):
    idx = json.load(open(os.path.join(HERE, "data", "sheet_index.json"), encoding="utf-8"))
    cites = collections.Counter()
    texts = list(M.get("sp", []))
    for t in (M.get("types") or {}).values(): texts += list(t.get("sr") or [])
    for tx in texts:
        for m in PAT.finditer(str(tx)):
            s = m.group(1); a = int(m.group(2)); b = int(m.group(3)) if m.group(3) else a
            for pg in range(a, min(b, a + 40) + 1): cites[(s, pg)] += 1
    sets = []; lst = []
    for s, rows in idx.items():
        used = 0
        for r in rows:
            title = r["title"].upper(); kind = "other"
            for k, words in KIND_WORDS:
                if any(w in title for w in words): kind = k; break
            c = cites.get((s, r["page"]), 0)
            used += 1 if c else 0
            lst.append({"s": s, "p": r["page"], "no": (r["no"] or "").replace(" 00", "").strip(), "t": r["title"].title(), "k": kind, "c": c})
        sets.append({"id": s, "name": SET_AR[s], "pages": len(rows), "used": used})
    by_kind = collections.defaultdict(lambda: [0, 0])
    for r in lst:
        by_kind[r["k"]][0] += 1; by_kind[r["k"]][1] += 1 if r["c"] else 0
    return {"sets": sets, "list": lst, "kinds": {k: {"name": KIND_AR[k], "n": v[0], "used": v[1]} for k, v in by_kind.items()}, "total": sum(s["pages"] for s in sets), "used": sum(s["used"] for s in sets)}


def closure():
    rows = []
    txt = _read(os.path.join(ROOT, "docs", "ARCH_CLOSURE.md"))
    for ln in txt.splitlines():
        m = re.match(r"^\|\s*([A-I])\s*\|(.+?)\|(.+?)\|(.+)\|\s*$", ln)
        if not m: continue
        status = m.group(4); st = "open"; pct = 0
        if "**مغلق**" in status or status.strip().startswith("مغلق —"): st, pct = "closed", 100
        elif "مغلق جزئيًا" in status or "قيد التنفيذ" in status: st, pct = "partial", 60
        if status.strip() in ("—", "-", ""): st, pct = "open", 0
        rows.append({"id": m.group(1), "title": m.group(2).strip()[:140], "st": st, "pct": pct})
    return rows


def features():
    out = []
    for grp, title, f, rx, note in FEATURES:
        p = os.path.join(ROOT, f) if "/" in f else os.path.join(ROOT, "src", f)
        out.append({"g": grp, "t": title, "ok": bool(re.search(rx, _read(p))), "n": note})
    return out


def build(M):
    els = M["els"]; rel = (M.get("meta") or {}).get("reliability") or {}
    layers = []
    for L in M["layers"]:
        o = rel.get("layer", {}).get(L["id"], {}); n = sum(o.values())
        layers.append({"id": L["id"], "name": L["name"], "n": n, "q": o})
    levels = []
    cl = collections.defaultdict(lambda: collections.Counter())
    for c in M.get("clashes", []): cl[c["l"]][c.get("tier", "k")] += 1
    gl = collections.Counter(); gcount = collections.defaultdict(int)
    for it in (M.get("guesses") or {}).get("items", []): gcount[els[it["e"]]["l"]] += 1
    for l in M["levels"]:
        o = rel.get("level", {}).get(l["id"], {}); n = sum(o.values())
        levels.append({"id": l["id"], "name": l["name"], "ffl": l["ffl"], "n": n, "q": o, "clash": dict(cl[l["id"]]), "guess": gcount[l["id"]]})
    ct = collections.Counter(c.get("tier", "k") for c in M.get("clashes", []))
    G = M.get("guesses") or {}
    files_py, loc_py = _loc("pipeline/*.py"); files_s, loc_s = _loc("pipeline/samples/*.py"); files_js, loc_js = _loc("src/*.js"); _, loc_t = _loc("src/template.html")
    docs = sorted(f for f in os.listdir(os.path.join(ROOT, "docs")) if f.endswith(".md")) if os.path.isdir(os.path.join(ROOT, "docs")) else []
    idx = os.path.join(ROOT, "index.html")
    inv = {"v": 1, "built": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
           "model": {"els": len(els), "types": len(M.get("types", {})), "levels": len(M["levels"]), "units": len(M.get("units", [])), "mats": len(M.get("mats", {})), "fin": len(M.get("fin", {})),
                     "stage": sum(1 for e in els if e["c"] == "A.stage")},
           "grades": rel.get("overall", {}), "axes": rel.get("axes", {}), "layers": layers, "levels": levels, "sheets": sheets(M), "closure": closure(), "features": features(),
           "issues": {"clash": {"c": ct.get("c", 0), "k": ct.get("k", 0), "m": ct.get("m", 0), "groups": len(M.get("clashGroups", []))},
                      "guess": {"rules": len(G.get("rules", [])), "items": len(G.get("items", [])), "impact": {k: G.get("summary", {}).get(k, 0) for k in ("high", "med", "low")}}},
           "code": {"pipeline": {"files": files_py + files_s, "loc": loc_py + loc_s}, "viewer": {"files": files_js, "loc": loc_js + loc_t}},
           "docs": docs, "out": {"index_mb": round(os.path.getsize(idx) / 1e6, 2) if os.path.exists(idx) else None, "repo": "binjednan/RD9-C4", "pages": "https://binjednan.github.io/RD9-C4/"}}
    M["inventory"] = inv
    sh = inv["sheets"]
    print("inventory: sheets", sh["used"], "/", sh["total"], "| closure", [(r["id"], r["st"]) for r in inv["closure"]])
    return inv


def write_doc(M):
    inv = M["inventory"]; out = []
    P = out.append
    P("# جرد المشروع الكامل — نموذج C4 ثلاثي الأبعاد (RD09)"); P("")
    P(f"يُولَّد آليًا بأمر `python3 pipeline/post_model.py` من الملفات نفسها (آخر توليد: {inv['built']}). كل رقم هنا مقيس لا مكتوب باليد.")
    P("")
    m = inv["model"]; g = inv["grades"]; tot = sum(g.values()) or 1
    P("## 1) النموذج"); P("")
    P(f"- **{m['els']:,}** عنصرًا في **{m['types']}** نوعًا على **{m['levels']}** مستويات و**{m['units']}** وحدة سكنية، بـ**{m['mats']}** خامة و**{m['fin']}** رمز تشطيب (A500).")
    P(f"- كماليات إخراجية (للعرض لا للتنفيذ): **{m['stage']:,}** عنصرًا.")
    P("")
    P("### درجات الموثوقية (ما يمكن الاعتماد عليه من كل عنصر)"); P("")
    P("| الدرجة | العناصر | النسبة | المعنى |"); P("|---|---:|---:|---|")
    for k, nm, ds in (("d", "موثّق", "الموضع والمنسوب والمواصفة مقروءة من المخططات والجداول"), ("v", "مشتق", "محسوب بقاعدة معلومة المعطيات (ارتفاعات التركيب، سقف FCL، سحب الجهاز إلى الجدار ...)"),
                      ("a", "تخمين", "اختاره النموذج لغياب البيان (مناسيب الخدمات في فراغ السقف، أقطار مفترضة، أجهزة بلا حامل ...)"), ("s", "إخراجي", "كماليات للعرض فقط")):
        P(f"| {nm} | {g.get(k, 0):,} | {g.get(k, 0) * 100 / tot:.1f}% | {ds} |")
    P(""); P("لا يوجد عنصر «مطابق للمنفَّذ» بعد؛ تلك الدرجة تُمنح عند اعتماد مخططات الأز-بيلت (BIM Forum LOD 500 = متحقَّق ميدانيًا).")
    P(""); P("### حسب القسم"); P(""); P("| القسم | العناصر | موثّق | مشتق | تخمين | إخراجي |"); P("|---|---:|---:|---:|---:|---:|")
    for L in inv["layers"]:
        q = L["q"]; P(f"| {L['name']} | {L['n']:,} | {q.get('d', 0):,} | {q.get('v', 0):,} | {q.get('a', 0):,} | {q.get('s', 0):,} |")
    P(""); P("### حسب الطابق"); P(""); P("| الطابق | العناصر | موثّق | مشتق | تخمين | إخراجي | تعارض مؤكد | مرشح | تخمينات فردية |"); P("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for L in inv["levels"]:
        q = L["q"]; c = L["clash"]
        P(f"| {L['name']} ({L['ffl']:+.2f}) | {L['n']:,} | {q.get('d', 0):,} | {q.get('v', 0):,} | {q.get('a', 0):,} | {q.get('s', 0):,} | {c.get('c', 0)} | {c.get('k', 0)} | {L['guess']} |")
    P("")
    sh = inv["sheets"]
    P("## 2) المصادر (المخططات)"); P("")
    P(f"{sh['total']} ورقة في 7 ملفات؛ **{sh['used']}** منها مُستشهَد بها في النموذج ({sh['used'] * 100 // max(1, sh['total'])}%).")
    P(""); P("| الملف | الأوراق | المستعملة |"); P("|---|---:|---:|")
    for s in sh["sets"]: P(f"| {s['name']} | {s['pages']} | {s['used']} |")
    P(""); P("| نوع الورقة | العدد | المستعمل |"); P("|---|---:|---:|")
    for k, v in sh["kinds"].items(): P(f"| {v['name']} | {v['n']} | {v['used']} |")
    P(""); P("### أوراق غير مستعملة من نوع مسقط / تفصيل / مقطع (مرشحة للاستخراج التالي)"); P("")
    un = [r for r in sh["list"] if not r["c"] and r["k"] in ("plan", "detail", "section")]
    P("| الملف | ص | الرقم | العنوان |"); P("|---|---:|---|---|")
    for r in un[:80]: P(f"| {r['s']} | {r['p']} | {r['no'] or '—'} | {r['t']} |")
    if len(un) > 80: P(f"| … | | | و{len(un) - 80} ورقة أخرى |")
    P("")
    P("## 3) المتابعة"); P("")
    i = inv["issues"]
    P(f"- **التعارضات** ({i['clash']['c'] + i['clash']['k'] + i['clash']['m']}): مؤكد **{i['clash']['c']}** · مرشح (اختلاف منسوب) **{i['clash']['k']}** · هامشي **{i['clash']['m']}** — في **{i['clash']['groups']}** مجموعة.")
    P(f"- **التخمينات**: **{i['guess']['rules']}** قاعدة (مرتفعة الأثر {i['guess']['impact']['high']} · متوسطة {i['guess']['impact']['med']} · منخفضة {i['guess']['impact']['low']}) و**{i['guess']['items']}** قرارًا فرديًا بموضع/إزاحة.")
    P(""); P("### إغلاق القسم المعماري (ARCH_CLOSURE)"); P(""); P("| البند | الحالة | الوصف |"); P("|---|---|---|")
    stn = {"closed": "مغلق", "partial": "جزئي", "open": "مفتوح"}
    for r in inv["closure"]: P(f"| {r['id']} | {stn[r['st']]} | {r['title']} |")
    P("")
    P("## 4) العارض (الواجهة)"); P(""); P("«نظرة عامة» تعرض ما يحتاج تنويهًا فقط (جديد بطلب المالك أو تنبيه)؛ الجدول كاملًا هنا."); P("")
    P("| المجال | الميزة | موجودة | في النظرة |"); P("|---|---|---|---|")
    nt = {"new": "جديد", "warn": "تنبيه", None: "—"}
    for f in inv["features"]: P(f"| {f['g']} | {f['t']} | {'نعم' if f['ok'] else 'لا'} | {nt[f['n']]} |")
    P("")
    c = inv["code"]
    P("## 5) الشيفرة والتوثيق والمخرجات"); P("")
    P(f"- خط الاستخراج (`pipeline/`): {c['pipeline']['files']} ملفًا، {c['pipeline']['loc']:,} سطرًا. العارض (`src/`): {c['viewer']['files']} ملفات JavaScript + القالب، {c['viewer']['loc']:,} سطرًا.")
    P(f"- التوثيق (`docs/`): {', '.join(inv['docs'])}.")
    o = inv["out"]
    P(f"- المخرج: `index.html` ملف واحد ({o['index_mb']} م.ب) · المستودع `{o['repo']}` · العرض المباشر {o['pages']}")
    open(os.path.join(ROOT, "docs", "INVENTORY.md"), "w", encoding="utf-8").write("\n".join(out) + "\n")
