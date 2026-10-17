# تعليمات تنفيذ لـ Codex — إدارة الدخان في نموذج C4 (مخططات MECH1 ص17–22)

> **الصق هذا الملف كاملًا في Codex.** كل القرارات الهندسية محسومة هنا وكل الأرقام مأخوذة من المخططات ومُتحقَّق منها. **نفّذ حرفيًا بالترتيب. لا تُعد التصميم ولا تقترح بدائل ولا تسأل المالك.** إن ظهر تعارض بين هذا الملف وما تراه فعلًا (ملف مفقود، رقم مختلف، اختبار يفشل) فتوقّف عند تلك النقطة وسجّله في التقرير (القسم 11) ثم أكمل ما لا يتأثر به. المالك: مهند بن قضير. اللغة في كل نص يراه المستخدم: **العربية**؛ الإنجليزية داخل الشيفرة والمسارات والأوامر فقط.

## 0. المطلوب في أربعة أسطر

1. استخراج مخططات إدارة الدخان (MECH1 ص17–21) إلى `pipeline/data/smoke.json` بالسكربت الجاهز في القسم 4.
2. بناء **209 عنصرًا** بلاحقة المعرّف `-SMnnnn` في `src/model.json` (مجاري وصواعد ومخمّدات ومراوح وشبكات وناشرات وردّادات) بالوصفات الحرفية في القسم 5.
3. أربعة أنظمة اختبار دورة حياة جديدة (`smk_cp_fa`، `smk_cp_ea`، `smk_co_fa`، `smk_co_ea`) وتسمية عربية لمفاتيح الخصائص الجديدة وتوثيق الدفعة 17.
4. فحص الصحة (أرقام متوقعة + ثبات المعرّفات + فحص مرئي) ثم تقرير عربي بالقالب في القسم 11. **لا commit ولا push.**

## 1. قواعد لا تُكسر

- **لا push ولا commit ولا تنزيل ولا وصول لأي شبكة.** العمل محلي في `~/Downloads/C4-3D-MODEL` مباشرة (لا نسخة معزولة).
- **لا تخترع خطًّا ولا عنصرًا لم يرسمه المخطط.** ما لم يُرسم يبقى غير موجود ويُسجَّل «بانتظار تأكيدك» (القسم 9 فيه قائمة المسجَّلات الجاهزة).
- **لا تلمس** `src/model.json` و`index.html` يدويًا (يُنتجان بـ`post_model.py` و`build.py`)، ولا ملفات `pipeline/data/*.json` الأخرى، ولا أي عنصر `S.*`، ولا معرّفات العناصر الموجودة. لاحقة المعرّفات الجديدة **`SM` فقط** (المحجوزة سابقًا: `X K L M C S V W VT`).
- **لا صور موقع خاصة** (مستودع `c4-docs-privet` خاص ولا يُنسخ منه شيء).
- **لا تعدّل شيئًا خارج الملفات المذكورة في القسم 3.** أي تغيير آخر ممنوع حتى لو بدا تحسينًا.
- **لا تضبط نتيجة اختبار بالتحايل:** ممنوع رفع `TOL` في `lifecycle.py` أو إضافة «وصلة» يدوية لإنجاح اختبار. فشل الوصل = خطأ في شيفرتك ما لم تكن الفجوة في بيانات المسقط ≥ 10 سم (عندها سجّلها في التقرير).
- كل نص عربي تكتبه في الشيفرة أو التوثيق: **انسخه من هذا الملف** حيث وُفِّر، وما لم يُوفَّر فاكتبه بالأسلوب الهندسي المختصر نفسه.

## 2. البيئة والأوامر (قراءة قبل البدء)

```bash
cd ~/Downloads/C4-3D-MODEL
python3 pipeline/post_model.py && python3 src/build.py      # إعادة بناء النموذج ثم العارض (دقيقتان تقريبًا؛ لا تُشغّلهما معًا بالتوازي)
python3 pipeline/lifecycle.py                                # اختبارات دورة الحياة على src/model.json (6 ثوانٍ)
python3 pipeline/lifecycle.py --baseline                     # تسجيل السقف (مرة واحدة في الآخر، بعد نجاح كل شيء)
/System/Library/Frameworks/JavaScriptCore.framework/Versions/Current/Helpers/jsc tools/jscheck.js -- src/*.js    # فحص صيغة JavaScript
```

**فخان معروفان:**
1. **ممنوع** وضع `pipeline/` في `PYTHONPATH` أو تشغيل `python3 -c` من داخله: الملف `pipeline/site.py` يحجب وحدة `site` القياسية فيفشل Python عند الإقلاع. السكربتات نفسها تضيف مسارها بعد الإقلاع فهي سليمة؛ للتجارب الجانبية استعمل `sys.path.insert(0, "pipeline")` داخل السكربت.
2. الملفات المصدرية PDF في `~/Downloads/` (الأسماء في `pipeline/lib.py` → `FILES`؛ `MECH1` = «Mechanical Drawings Part I (1).pdf»). التحليل الأول لكل ورقة بطيء (دقائق) ثم يُخزَّن في `lib.CACHE`. **إن فشلت الكتابة في `CACHE`** (Permission denied) فغيّر في `pipeline/lib.py` السطر `CACHE = ...` إلى `CACHE = os.environ.get("C4_CACHE", "/tmp/c4_cache/")` وأنشئ المجلد، ولا تغيّر شيئًا آخر في `lib.py`، ودوّن ذلك في التقرير.

**اقرأ هذه الملفات أولًا (للنمط فقط، لا تعدّلها إلا حيث يُقال):**
`pipeline/vent_extract.py` و`pipeline/vent_build.py` (التهوية: النموذج الذي تنسخ نمطه)، `pipeline/lifecycle.py` (الأسطر 145–200: `VENT_T` و`SYSTEMS`)، `pipeline/connectors.py` (السطر 26 `CONN_SYS`)، `pipeline/post_model.py` (ابحث عن `-VT\d{4}$` وعن `_VT.build` وعن `_VT.TYPES`)، `docs/HANDOFF_2026-10-08.md` §7–8.

## 3. خريطة الملفات

| الملف | العملية | الغرض |
|---|---|---|
| `pipeline/smoke_extract.py` | **جديد** (القسم 4) | استخراج الأوراق ص17–21 → `pipeline/data/smoke.json` |
| `pipeline/data/smoke.json` | **جديد** (مُولَّد) | بيانات الرسم كما هي، بالسنتيمتر (11 كيلوبايت) |
| `pipeline/smoke_build.py` | **جديد** (القسم 5) | بناء العناصر + `TYPES` + `MATS` |
| `pipeline/post_model.py` | تعديل 3 مواضع (6.1) | حذف `-SM` وبناؤها وتسجيل الأنواع |
| `pipeline/lifecycle.py` | تعديل موضعين (6.2) | `SMK_T` ثم `VENT_T` + أربعة أنظمة |
| `pipeline/connectors.py` | تعديل سطر (6.3) | وصلات مرنة لأنواع الدخان |
| `pipeline/inventory.py` | تعديل (6.4) | بنود الميزات |
| `src/app.js` | تعديل سطر (6.5) | تسميات عربية لمفاتيح الخصائص |
| `README.md` | تعديل (9.3) | سطر دورة الحياة |
| `docs/PROGRESS.md` | إضافة «الدفعة 17» (9.1) | |
| `docs/HANDOFF_2026-10-08.md` | إضافة §9 (9.2) | |
| `docs/INVENTORY.md` و`docs/LIFECYCLE_TESTS.md` و`docs/CLASH_LOG.md` و`src/model.json` و`index.html` و`pipeline/data/lifecycle_baseline.json` | تُنتَج آليًّا | لا تحرّرها يدويًا |

## 4. الخطوة 1 — `pipeline/smoke_extract.py`

أنشئ الملف بالمحتوى التالي **حرفيًا** (جُرِّب على الأوراق الفعلية وأعطى الأرقام الموجودة في الملحق أ):

```python
# -*- coding: utf-8 -*-
"""Smoke-management layouts (MECH1 p17–21: SM-100 basement, SM-101 ground, SM-102 first floor, SM-103 typical floors, SM-104 roof) -> pipeline/data/smoke.json
(needs the source PDFs, see lib.py; post_model.py merges the json through pipeline/smoke_build.py)

Owner 2026-10-08: «أكمل استعمال جميع المخططات لتكون البيئة مناسبة للاختبار».  What these sheets draw (layer names of the NHR MEP drawings):

  B   p17  M_FA_GRILL / M_EX_GRILL   car-park make-up (FA) / extract (EA) system: the single-line duct polylines (a main with two arms, stubs 29 / 50 cm long, a connection piece to the shaft),
                                     the 13 grille symbols of each system (a cluster of 16 filled slivers), the shaft box (rectangle, 140 x 100 / 160 x 100 cm)
           M_VE_DAM                  the 26 volume-control dampers (VCD, 7-vertex outline);  M_HVAC_DAM the two fire dampers (FD);  M_HVAC_EQP the two ceiling-suspended fans
           M_FA_TEXT / M_EX_TEXT     duct size labels «600x1300» (mm, width x height) and the words FD / VCD
  G   p18  M_FA_GRILL / M_EX_GRILL   the two shaft boxes again (the louver text has no position on the plan)
  1 / TY / R   p19 / p20 / p21       corridor smoke system: the two riser boxes, the dampers (MFD / VCD), the extract branch and corridor duct, the two extract diffusers (EAD, crossed squares),
                                     the fresh-air grille box (SMS FAG); on the roof the two ducts, the two fan units (AV-MAC rectangles) and their louver hatch (M1-EQUP)

Everything is stored as drawn (plan centimetres, 1 decimal); pipeline/smoke_build.py associates sizes and builds the elements.

    python3 pipeline/smoke_extract.py       # parses five big sheets (cached by lib.py)"""
import sys, os, re, json, math, collections
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lib, geo
from vent_extract import crosses                         # pairs of opposite diagonals = the crossed-square diffusers (already used for the ventilation sheets)

OUT = os.path.join(HERE, "data", "smoke.json")
SHEETS = {"B": 17, "G": 18, "1": 19, "TY": 20, "R": 21}   # MECH1 pages
FAMS = (("fa", "M_FA_GRILL"), ("ea", "M_EX_GRILL"))
SIZE_RE = re.compile(r"^\d{2,4}x\d{2,4}$")
KEEP_WORDS = ("FD", "VCD", "MFD")


def short(layer): return (layer or "").split("$")[-1]
def r1(v): return round(v, 1)
def wh(w):
    b = geo.bbox(w); return b[2] - b[0], b[3] - b[1]
def box(w):
    b = geo.bbox(w); return {"x": r1((b[0] + b[2]) / 2), "y": r1((b[1] + b[3]) / 2), "w": r1(b[2] - b[0]), "h": r1(b[3] - b[1])}
def rect(w):
    b = geo.bbox(w); return [r1(b[0]), r1(b[1]), r1(b[2]), r1(b[3])]
def closed(w, n): return len(w) == n and geo.is_closed(w, 1.5)
def pts(w): return [[r1(p[0]), r1(p[1])] for p in w]


def polys(sh, layers, test):
    """[(layer, plan polyline, drawing)] of every polyline on the given layers that passes test(w, d)"""
    out = []
    for d in sh.D:
        ly = short(d["layer"])
        if ly not in layers: continue
        for pl in d["polys"]:
            w = [sh.T(x, y) for x, y in pl]
            if test(w, d): out.append((ly, w, d))
    return out


def words_of(sh, layers):
    """size labels («500x900») and damper words (FD / VCD / MFD) of the given text layers, plan position of the word centre"""
    out = []
    for w in sh.words():
        ly = short(w["layer"])
        if ly in layers and (SIZE_RE.match(w["s"]) or w["s"] in KEEP_WORDS):
            X, Y = sh.T(w["x"], w["y"]); out.append({"t": w["s"], "x": r1(X), "y": r1(Y), "layer": ly})
    return out


def clusters(sh, layer):
    """the grille symbols: 16 filled 4-vertex slivers per grille; slivers whose boxes are within 4 cm of each other form one cluster -> bbox centre / size of the cluster (legend symbols at x >= 5000 are skipped)"""
    items = [geo.bbox(w) for ly, w, d in polys(sh, (layer,), lambda w, d: d.get("fill") and closed(w, 4) and geo.bbox(w)[0] < 5000)]
    par = list(range(len(items)))
    def find(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if a[0] - 4 <= b[2] and b[0] - 4 <= a[2] and a[1] - 4 <= b[3] and b[1] - 4 <= a[3]: par[find(i)] = find(j)
    groups = collections.defaultdict(list)
    for i, it in enumerate(items): groups[find(i)].append(it)
    out = []
    for v in groups.values():
        x0 = min(b[0] for b in v); y0 = min(b[1] for b in v); x1 = max(b[2] for b in v); y1 = max(b[3] for b in v)
        out.append({"x": r1((x0 + x1) / 2), "y": r1((y0 + y1) / 2), "w": r1(x1 - x0), "h": r1(y1 - y0)})
    return sorted(out, key=lambda c: (c["x"], c["y"]))


def shaft_of(sh, layer):
    """the shaft box: one closed 5-vertex rectangle 120–200 x 80–120 cm on the layer (the X inside it is a 4-vertex open path)"""
    found = [rect(w) for ly, w, d in polys(sh, (layer,), lambda w, d: closed(w, 5) and geo.bbox(w)[0] < 5000 and 120 <= max(wh(w)) <= 200 and 80 <= min(wh(w)) <= 120)]
    assert len(found) == 1, (layer, found)
    return found[0]


def car_park(sh):
    out = {}
    for fam, layer in FAMS:
        sb = shaft_of(sh, layer)
        def is_x(w, sb=sb):
            b = geo.bbox(w); return all(abs(b[i] - sb[i]) <= 1.0 for i in range(4))
        paths = [pts(w) for ly, w, d in polys(sh, (layer,), lambda w, d: len(w) >= 2 and not geo.is_closed(w, 1.5) and geo.bbox(w)[0] < 5000 and geo.polyline_len(w) >= 25 and not is_x(w))]
        out[fam] = {"shaft": sb, "paths": paths, "grilles": clusters(sh, layer)}
    out["vcd"] = [box(w) for ly, w, d in polys(sh, ("M_VE_DAM",), lambda w, d: closed(w, 7))]
    out["fd"] = [box(w) for ly, w, d in polys(sh, ("M_HVAC_DAM",), lambda w, d: closed(w, 7))]
    out["fans"] = [rect(w) for ly, w, d in polys(sh, ("M_HVAC_EQP",), lambda w, d: closed(w, 5))]
    out["words"] = words_of(sh, ("M_FA_TEXT", "M_EX_TEXT", "M_HVAC_DAM", "M_VE_DAM"))
    assert [len(out[f]["grilles"]) for f, _ in FAMS] == [13, 13] and len(out["vcd"]) == 26 and len(out["fd"]) == 2 and len(out["fans"]) == 2, "basement counts"
    return out


def ground(sh):
    out = {}
    for fam, layer in FAMS:
        found = polys(sh, (layer,), lambda w, d: closed(w, 5) and geo.bbox(w)[0] < 5000 and 120 <= max(wh(w)) <= 200 and 80 <= min(wh(w)) <= 120)
        assert len(found) == 1, (layer, len(found))
        out[fam] = box(found[0][1])
    return out


def corridor(sh, roof):
    S = {}
    S["fa_riser"] = [box(w) for ly, w, d in polys(sh, ("M_FA_DUCT",), lambda w, d: closed(w, 5) and 20 <= wh(w)[0] <= 30 and 35 <= wh(w)[1] <= 45)]
    S["ea_riser"] = [box(w) for ly, w, d in polys(sh, ("M_T.EX_DIFF",), lambda w, d: closed(w, 5) and 15 <= wh(w)[0] <= 25 and 25 <= wh(w)[1] <= 35)]
    S["dampers"] = [dict(box(w), layer=ly) for ly, w, d in polys(sh, ("M_HVAC_DAM", "M_VE_DAM"), lambda w, d: closed(w, 7) and geo.bbox(w)[0] < 2500)]
    S["words"] = words_of(sh, ("M_HVAC_DAM", "M_VE_DAM", "M_FA_TEXT", "M_T.EX_TEXT"))
    if not roof:
        S["ea_branch"] = [pts(w) for ly, w, d in polys(sh, ("M_T.EX_DIFF",), lambda w, d: len(w) == 2 and 120 <= geo.polyline_len(w) <= 160 and abs(w[0][0] - w[1][0]) < 1)]
        S["ea_main"] = [pts(w) for ly, w, d in polys(sh, ("M_T.EX_DIFF",), lambda w, d: len(w) == 2 and geo.polyline_len(w) > 800)]
        S["ead"] = crosses(sh, ("M_T.EX_DIFF",))
        S["fag_box"] = [box(w) for ly, w, d in polys(sh, ("M_SAG_GRILL",), lambda w, d: closed(w, 5) and geo.bbox(w)[0] < 2500)]
        assert len(S["fa_riser"]) == 1 and len(S["ea_riser"]) == 1 and len(S["ea_branch"]) == 1 and len(S["ea_main"]) == 1 and len(S["ead"]) == 2 and len(S["fag_box"]) == 2, "corridor counts"
    else:
        S["fa_duct"] = [pts(w) for ly, w, d in polys(sh, ("M_DR_WP",), lambda w, d: len(w) == 4 and geo.polyline_len(w) > 900)]          # the layer name is odd (drain / waste); the polyline joins the FA riser to the supply fan
        S["ea_duct"] = [pts(w) for ly, w, d in polys(sh, ("M_EX_GRILL",), lambda w, d: len(w) == 6 and geo.polyline_len(w) > 1500)]
        S["fan_rects"] = [dict(box(w), layer=ly) for ly, w, d in polys(sh, ("AV-MAC",), lambda w, d: closed(w, 5) and geo.bbox(w)[0] < 500)]      # outer + inner rectangle of each unit
        S["fan_circles"] = [dict(box(w), layer=ly) for ly, w, d in polys(sh, ("AV-MAC",), lambda w, d: len(w) == 41 and geo.bbox(w)[0] < 500)]
        strokes = collections.defaultdict(list)                                                                                           # louver hatch west of each fan unit
        for d in sh.D:
            if short(d["layer"]) != "M1-EQUP": continue
            for pl in d["polys"]:
                w = [sh.T(x, y) for x, y in pl]; b = geo.bbox(w)
                if b[2] < 310: strokes["fa" if b[1] < 1500 else "ea"].append(b)
        S["louvers"] = {k: {"x0": r1(min(b[0] for b in v)), "y0": r1(min(b[1] for b in v)), "x1": r1(max(b[2] for b in v)), "y1": r1(max(b[3] for b in v))} for k, v in strokes.items()}
        assert len(S["fa_duct"]) == 1 and len(S["ea_duct"]) == 1 and len(S["fan_rects"]) == 4 and len(S["fan_circles"]) == 2 and sorted(S["louvers"]) == ["ea", "fa"], "roof counts"
    return S


def run(out=OUT):
    ref = lib.Sheet("ARCH1", 7); res = {}
    for key, page in SHEETS.items():
        sh = lib.Sheet("MECH1", page, ref=ref)
        if sh.reg is None: raise SystemExit(f"no registration for MECH1 p{page}")
        if key == "B": body = car_park(sh)
        elif key == "G": body = ground(sh)
        else: body = corridor(sh, roof=(key == "R"))
        res[key] = dict({"sheet": f"MECH1 p{page}", "scale": round(sh.reg["s"], 3)}, **body)
        print(key, f"MECH1 p{page}", {k: (len(v) if isinstance(v, (list, dict)) else v) for k, v in body.items()})
    json.dump(res, open(out, "w", encoding="utf-8"), separators=(",", ":"), ensure_ascii=False)
    print("saved", out, round(os.path.getsize(out) / 1e3), "kB")


if __name__ == "__main__":
    run()
```

ثم شغّله: `python3 pipeline/smoke_extract.py`. **المتوقع:** يطبع الأسطر الخمسة (B وG و1 وTY وR) بلا `AssertionError` ويحفظ `pipeline/data/smoke.json` بحجم ≈ 11 كيلوبايت.

**تحقق من المطابقة مع الملحق أ:** احفظ الملحق أ (الكتلة JSON في آخر هذا الملف) في `/tmp/smoke_expected.json` ثم شغّل:

```bash
python3 - <<'PY'
import json
exp = json.load(open("/tmp/smoke_expected.json")); got = json.load(open("pipeline/data/smoke.json"))
bad = []
def cmp(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in a:
            if k in ("scale", "sheet"): continue
            if k not in b: bad.append(path + "/" + k + " missing")
            else: cmp(a[k], b[k], path + "/" + k)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): bad.append(path + " len %d != %d" % (len(a), len(b))); return
        key = lambda v: json.dumps(v, sort_keys=True)
        try: a2, b2 = sorted(a, key=key), sorted(b, key=key)
        except Exception: a2, b2 = a, b
        for i, (x, y) in enumerate(zip(a2, b2)): cmp(x, y, path + "[%d]" % i)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if abs(a - b) > 1.5: bad.append(f"{path}: {a} vs {b}")
    elif a != b: bad.append(f"{path}: {a!r} vs {b!r}")
cmp(exp, got); print("MISMATCHES:", len(bad)); print("\n".join(bad[:30]))
PY
```
**المطلوب:** `MISMATCHES: 0` (فرق ≤ 1.5 سم مقبول). إن اختلف: صحّح الاستخراج (لا تنسخ الملحق إلى `smoke.json`)؛ وإن تعذّر الاستخراج كليًّا بعد ثلاث محاولات لسبب في قراءة PDF فاحفظ الملحق أ نفسه كـ`pipeline/data/smoke.json` وأضف فيه المفتاح `"source": "appendix"` وسجّل ذلك في التقرير.

## 5. الخطوة 2 — `pipeline/smoke_build.py`

### 5.1 الهيكل العام (انسخ نمط `vent_build.py` حرفيًا)

```python
# -*- coding: utf-8 -*-
"""Smoke management as model elements (data: pipeline/data/smoke.json from pipeline/smoke_extract.py; sheets MECH1 p17–22 = SM-100 … SM-105).  <اكتب هنا شرحًا بالإنجليزية من 8 أسطر يلخّص الأقسام 5.3–5.6>"""
import os, re, sys, json, math, collections
from shapely.geometry import Polygon, Point
from shapely.strtree import STRtree
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
DATA = os.path.join(HERE, "data", "smoke.json")
ID_RE = re.compile(r"-SM\d{4}$")
ORDER = ["B", "G", "1", "2", "3", "4", "5", "R"]
FLOORS = ["1", "2", "3", "4", "5"]          # the corridor system serves these floors (sheet "1" for floor 1, sheet "TY" for 2–5)
# ... (الثوابت 5.2، ثم دوال الطوبولوجيا 5.3، ثم MATS وTYPES 5.7، ثم build)
def build(M, els, verbose=False):
    els[:] = [e for e in els if not ID_RE.search(e["id"])]
    if not os.path.exists(DATA): return {}
    D = json.load(open(DATA, encoding="utf-8"))
    sp = M["sp"]
    for t in (SRC_CP, SRC_CO):
        if t not in sp: sp.append(t)
    s_cp, s_co = sp.index(SRC_CP), sp.index(SRC_CO)
    for k, v in MATS.items(): M["mats"].setdefault(k, v)
    for k, v in TYPES.items(): M.setdefault("types", {})[k] = v
    ffl = {l["id"]: l["ffl"] for l in M["levels"]}
    new = []; counter = collections.Counter(); stats = collections.Counter()
    # add(), unit_at(), plates/ceil_z(), slab/slab_bot()  — القسم 5.4
    # ... الوصفات 5.5 بالترتيب: car park (fa ثم ea) ← G risers ← floors 1..5 ← roof
    els.extend(new)
    if verbose: print("smoke management:", len(new), dict(sorted(stats.items())))
    return dict(stats)

if __name__ == "__main__":
    SRC = os.path.join(os.path.dirname(HERE), "src", "model.json")
    M = json.load(open(SRC, encoding="utf-8")); n0 = len(M["els"]); build(M, M["els"], verbose=True); print("elements", n0, "->", len(M["els"]))
```

للتجربة السريعة أثناء الكتابة: `python3 pipeline/smoke_build.py` يحمّل `src/model.json` ويبني العناصر في الذاكرة ويطبع `smoke management: N {...}` **دون أن يحفظ شيئًا** (أسرع من `post_model.py`؛ لا يُجري الدعم ولا اختبارات دورة الحياة).

### 5.2 الثوابت (ضعها بعد `FLOORS` حرفيًا)

```python
Z_SOFFIT_GAP = 0.05          # m   the top of the car-park ducts sits this far under the underside of the ground-floor slab (slab["G"][0] = -0.45 -> top at -0.50)
BOTTOM_COR = 2.52            # m   above the floor: underside of the corridor extract ducts (the same as the ventilation ducts of floors 1–5 in vent_build.py)
Z_FAG = (2.05, 2.25)         # m   above the floor: the SMS FAG box on the shaft wall, its branch and its MFD
ROOF_BOTTOM = 0.60           # m   above the roof floor: underside of the roof smoke ducts (on stands)
FAN_ROOF_H = 1.20            # m   height of a roof fan casing, from the roof floor
LOUVER_ROOF = (0.30, 1.20)   # m   above the roof floor: louver of a roof fan
LOUVER_HEAD_H = 1.50         # m   height of the louver head on a car-park shaft (the SM-101 text says L X H 2 M X 1.5 M)
FAN_LEN_CP = 80.0            # cm  assumed length of a car-park fan casing along its duct
GRILLE_LEN = {"fa": 150.0, "ea": 170.0}   # cm  FAG 1500x200 mm / EAG 1700x200 mm (SM-100 text); the drawn bar is 80 cm (schematic)
GRILLE_H = 20.0              # cm
STUB_W, STUB_H = 30.0, 20.0  # cm  the 300x200 mm branch of every car-park grille
DAMPER_ALONG, DAMPER_PAD = 12.0, 8.0   # cm  a damper box: 12 along the duct, duct width + 8 across; its z span is the duct's +/- 0.04 m
VCD_R, CLUSTER_R = 30.0, 20.0           # cm  a VCD symbol / grille cluster belongs to the stub whose grille end is this close
RISER = {"fa": (25.0, 40.0), "ea": (20.0, 30.0)}   # cm plan x, y of the corridor risers (labels 400x250 / 300x200 and the drawn boxes)
RISER_CENTRE = {"fa": (1327.5, 1044.9), "ea": (1355.0, 1039.9)}   # sheet "1" centres, used on every level so the shaft is one straight stack
COR_FA_BRANCH = (25.0, 20.0)  # cm  w, h of the stub between the FA riser and its SMS FAG (the drawn 25 x 20 box)
COR_EA_BRANCH = (30.0, 20.0)  # cm  300x200
COR_EA_MAIN = (25.0, 15.0)    # cm  250x150
FAG_COR = (40.0, 4.0, 20.0)   # cm  SMS FAG 400x200 mm: width along x, depth, height
EAD = 25.0                    # cm  SMS EAD 225x225 mm: the drawn 25 x 25 plate
ROOF_DUCT = {"fa": (40.0, 25.0), "ea": (30.0, 20.0)}   # cm  400x250 / 300x200
```

### 5.3 دوال الطوبولوجيا (انسخ **حرفيًا**، جُرِّبت على البيانات)

```python
# --- car-park duct topology (goes into pipeline/smoke_build.py) -------------------------------------------------------------------------------------------------------------------------
import re, math

SIZE_RE = re.compile(r"^(\d{2,4})x(\d{2,4})$")
STUB_STD = (300, 200)             # mm  the branch stub of every grille («300x200» on the make-up side; the extract stubs carry no label and are taken equal)
STUB_MAX = 60.0                   # cm  an arm's last segment (or a free 2-vertex polyline) up to this long is a grille stub
LABEL_R = 60.0                    # cm  a size label this close to an arm belongs to it
CONN_R = 250.0                    # cm  a size label this close to the connection piece (shaft -> junction) may size it


def dist(p, q): return math.hypot(p[0] - q[0], p[1] - q[1])
def plen(pl): return sum(dist(a, b) for a, b in zip(pl, pl[1:]))


def project(pl, pt):
    """(arclength of the point of polyline pl closest to pt, distance to it)"""
    best = (1e9, 0.0); acc = 0.0
    for a, b in zip(pl, pl[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]; l2 = dx * dx + dy * dy; seg = math.sqrt(l2)
        t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dy) / l2))
        d = math.hypot(pt[0] - (a[0] + dx * t), pt[1] - (a[1] + dy * t))
        if d < best[0]: best = (d, acc + seg * t)
        acc += seg
    return best[1], best[0]


def point_at(pl, s):
    acc = 0.0
    for a, b in zip(pl, pl[1:]):
        seg = dist(a, b)
        if acc + seg >= s - 1e-9:
            t = 0.0 if seg == 0 else (s - acc) / seg
            return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t]
        acc += seg
    return list(pl[-1])


def cut(pl, s0, s1):
    """the part of polyline pl between arclengths s0 < s1 (the vertices in between are kept)"""
    out = [point_at(pl, s0)]; acc = 0.0
    for a, b in zip(pl, pl[1:]):
        acc += dist(a, b)
        if s0 + 1e-6 < acc < s1 - 1e-6: out.append(list(b))
    out.append(point_at(pl, s1)); return out


def topology(F, labels):
    """F = smoke.json['B'][fam] ({shaft, paths, grilles}); labels = the size words of that family ({t, x, y}).
    -> {J, conn, conn_size, arms: [{pts, sections: [{s0, s1, size, labelled}]}], stubs: [{grille_end, duct_end, arm, s}]}   sizes are (width_mm, height_mm)"""
    sb = F["shaft"]; paths = [[list(p) for p in pl] for pl in F["paths"]]
    inside = lambda p: sb[0] - 5 <= p[0] <= sb[2] + 5 and sb[1] - 5 <= p[1] <= sb[3] + 5
    main = max(paths, key=plen)
    conn_src = [p for p in paths if p is not main and any(inside(v) for v in p)][0]
    ji = [i for i, v in enumerate(conn_src) if any(dist(v, m) < 2 for m in main)][0]
    J = [m for m in main if dist(m, conn_src[ji]) < 2][0]; jidx = main.index(J)
    ii = [i for i, v in enumerate(conn_src) if inside(v)][0]
    if ii < ji: conn = conn_src[ii:ji + 1][::-1]; rest = conn_src[ji:]
    else: conn = conn_src[ji:ii + 1]; rest = conn_src[:ji + 1][::-1]
    arm_pts = [a for a in (main[jidx:], main[:jidx + 1][::-1]) if len(a) > 1]
    if len(rest) > 1:
        arm = rest[:]
        for e in paths:
            if e is main or e is conn_src or len(e) < 3: continue
            if dist(e[-1], arm[-1]) < 3: arm = arm + e[::-1][1:]
            elif dist(e[0], arm[-1]) < 3: arm = arm + e[1:]
        arm_pts.append(arm)
    # stubs: free 2-vertex polylines + the last segment of every arm
    stubs = []
    for e in paths:
        if len(e) == 2 and e is not conn_src and 20 <= plen(e) <= STUB_MAX:
            d0 = min(project(a, e[0])[1] for a in arm_pts); d1 = min(project(a, e[1])[1] for a in arm_pts)
            stubs.append({"grille_end": e[0], "duct_end": e[1]} if d1 <= d0 else {"grille_end": e[1], "duct_end": e[0]})
    for k, a in enumerate(arm_pts):
        if plen(a[-2:]) <= STUB_MAX: stubs.append({"grille_end": a[-1], "duct_end": a[-2]}); arm_pts[k] = a[:-1]
    for st in stubs:
        best = min(((project(a, st["duct_end"]), k) for k, a in enumerate(arm_pts)), key=lambda t: t[0][1])
        (s, d), k = best
        assert d <= 1.5, ("stub does not touch an arm", st, d)
        st["arm"], st["s"] = k, s
    lab = []
    for w in labels:
        m = SIZE_RE.match(w["t"])
        if m: lab.append(((w["x"], w["y"]), (int(m.group(1)), int(m.group(2)))))
    arms = []
    for k, a in enumerate(arm_pts):
        L = plen(a); taps = sorted(set(round(st["s"], 1) for st in stubs if st["arm"] == k))
        bounds = [0.0] + [t for t in taps if 0.5 < t < L - 0.5] + [L]
        secs = [{"s0": b0, "s1": b1} for b0, b1 in zip(bounds, bounds[1:])]
        near = [(project(a, p)[0], size) for p, size in lab if project(a, p)[1] <= LABEL_R]
        for i, sec in enumerate(secs):
            last = i == len(secs) - 1; mid = (sec["s0"] + sec["s1"]) / 2
            cand = [(abs(s - mid), size) for s, size in near if sec["s0"] - 0.1 <= s < sec["s1"] + (0.1 if last else -0.1) and (size != STUB_STD or last)]
            sec["size"], sec["labelled"] = (min(cand)[1], True) if cand else (None, False)
        first = next((s["size"] for s in secs if s["size"]), STUB_STD)
        prev = None
        for sec in secs:
            if sec["size"] is None: sec["size"] = prev or first
            prev = sec["size"]
        arms.append({"pts": a, "len": L, "sections": secs})
    big = [(size[0] * size[1], size) for p, size in lab if size != STUB_STD and min(project(conn, p)[1], dist(p, conn[0]), dist(p, conn[-1])) <= CONN_R]
    conn_size = max(big)[1] if big else arms[0]["sections"][0]["size"]
    return {"J": J, "conn": conn, "conn_size": conn_size, "arms": arms, "stubs": stubs}


def pieces(arm):
    """[(p, q, size, labelled)] one duct piece per vertex-to-vertex segment of every section (pieces shorter than 6 cm are dropped)"""
    out = []
    for sec in arm["sections"]:
        sub = cut(arm["pts"], sec["s0"], sec["s1"])
        for p, q in zip(sub, sub[1:]):
            if dist(p, q) >= 6.0: out.append((p, q, sec["size"], sec["labelled"]))
    return out
```

### 5.4 الدوال المساعدة داخل `build` (انسخها من `vent_build.py` كما هي، مع الأسماء نفسها)

```python
    def unit_at(lv, x, y):
        for u in M.get("units", []):
            if u["level"] != lv: continue
            for r in u["rects"]:
                if r[0] <= x <= r[2] and r[1] <= y <= r[3]: return u["id"]
        return None

    def add(cat, lv, g, typ, mat, area, mark=None, a=None):
        counter[(cat, lv)] += 1
        e = {"id": f"{cat}-{lv}-SM{sum(counter.values()):04d}", "c": cat, "l": lv, "g": g, "mark": mark, "t": typ, "m": mat, "a": a or {}, "s": [s_cp if area == "cp" else s_co]}
        u = unit_at(lv, g[1], g[2]) if g[0] == "b" else unit_at(lv, g[1][0][0], g[1][0][1])
        if u: e["u"] = u
        new.append(e); stats[typ] += 1; return e

    plates = {}
    for lv in ORDER:
        P = []
        for e in els:
            if e["c"] == "A.ceil" and e["l"] == lv and e["g"][0] == "p":
                try: pg = Polygon(e["g"][1]).buffer(0)
                except Exception: continue
                if not pg.is_empty: P.append((pg, e["g"][2]))
        plates[lv] = (STRtree([p for p, _ in P]), P) if P else None

    def ceil_z(lv, x, y, default):
        pl = plates.get(lv)
        if pl is None: return default
        tree, P = pl
        for i in tree.query(Point(x, y)):
            if P[int(i)][0].contains(Point(x, y)): return P[int(i)][1]
        return default

    slab = {}
    for e in els:
        if e["c"] == "S.slab" and e["g"][0] == "p": z0, z1 = slab.get(e["l"], (1e9, -1e9)); slab[e["l"]] = (min(z0, e["g"][2]), max(z1, e["g"][3]))
    def slab_bot(lv): return slab[lv][0] if lv in slab and lv not in ("B", "G") else ffl[lv] - (0.10 if lv != "B" else 0.0)
    Z_TOP_B = slab["G"][0] - Z_SOFFIT_GAP
    def ang(p, q): return round(math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])), 1)
    def zc_b(h_cm): return round(Z_TOP_B - h_cm / 200.0, 3)               # centre z of a car-park duct h_cm high, top-aligned under the slab
```

صيغ الهندسة المستعملة (كما في `vent_build.py`): `["d", [[x, y, z], [x, y, z]], w_cm, h_cm]` مجرى بقطعة مستقيمة (w العرض الأفقي وh الارتفاع)؛ `["b", cx, cy, w, d, rot_deg, z0, z1]` صندوق موجَّه (w على المحور المحلي x الذي يدور بـ`rot` درجة عكس عقارب الساعة، d على المحلي y). كل `z` بالمتر وكل البقية بالسنتيمتر. **قيم `z` تُقرَّب إلى 3 منازل وبقية الأرقام إلى منزل واحد.**

### 5.5 وصفات بناء العناصر (حرفية؛ الترتيب أدناه هو ترتيب الإنشاء ولا يتغير لأن المعرّفات تعتمد عليه)

**(أ) موقف البدروم — لكل `fam` بالترتيب `fa` ثم `ea`** (`F = D["B"][fam]`، `labels = [w for w in D["B"]["words"] if w["layer"] == ("M_FA_TEXT" if fam == "fa" else "M_EX_TEXT")]`، `top = topology(F, labels)`، `sb = F["shaft"]`):

مقادير: `wc, hc = top["conn_size"][0] / 10, top["conn_size"][1] / 10` (سم)، `zc = zc_b(hc)`، `J = top["J"]`، `S = top["conn"][-1]` (نقطة داخل الشفت)، `cang = ang(J, S)`، `cx, cy = (sb[0]+sb[2])/2, (sb[1]+sb[3])/2`، `sw, sd = sb[2]-sb[0], sb[3]-sb[1]`.

| # | العنصر | الفئة / المستوى / النوع / المادة | الهندسة | الوسم `mark` |
|---|---|---|---|---|
| 1 | الشفت (صاعد) | `M.duct` / `B` / `riser_cp_{fam}` / `m_duct_sm_{fam}` | `["b", cx, cy, sw, sd, 0, round(Z_TOP_B - hc/100, 3), ffl["G"]]` | — |
| 2 | رأس الردّادات | `M.outlet` / `G` / `louver_cp_{fam}` / `m_grille_fa` | `["b", cx, cy, sw, sd, 0, ffl["G"], round(ffl["G"] + LOUVER_HEAD_H, 3)]` | — |
| 3 | قطعة الوصل | `M.duct` / `B` / `duct_cp_{fam}` / `m_duct_sm_{fam}` | `["d", [[J[0], J[1], zc], [S[0], S[1], zc]], wc, hc]` | — |
| 4 | مخمّد FD | `M.damper` / `B` / `damper_cp_{fam}` / `m_damper_ve` | الأقرب إلى مركز الشفت من `D["B"]["fd"]` (مركزه `fx, fy`): `["b", fx, fy, DAMPER_ALONG, wc + DAMPER_PAD, cang, round(zc - hc/200 - 0.04, 3), round(zc + hc/200 + 0.04, 3)]` | `"FD"` |
| 5 | المروحة | `M.fan` / `B` / `fan_cp_{fam}` / `m_fan` | الأقرب إلى مركز الشفت من `D["B"]["fans"]` (مستطيل `[x0,y0,x1,y1]`، مركزه `mx, my`): `["b", mx, my, FAN_LEN_CP, wc, cang, round(zc - hc/200, 3), round(zc + hc/200, 3)]` | — |
| 6 | قطع الأذرع | `M.duct` / `B` / `duct_cp_{fam}` / `m_duct_sm_{fam}` | لكل ذراع بترتيب `top["arms"]` ولكل `(p, q, size, labelled)` من `pieces(arm)`: `w, h = size[0]/10, size[1]/10`، `z = zc_b(h)`: `["d", [[p[0], p[1], z], [q[0], q[1], z]], w, h]` | — |
| 7 | الفروع، **لكل `stub` بترتيب `sorted(top["stubs"], key=lambda s: (s["grille_end"][1], s["grille_end"][0]))`** (يتكرر 7.أ–7.ج لكل فرع قبل الانتقال لتاليه): | | | |
| 7.أ | الفرع | `M.duct` / `B` / `duct_cp_{fam}` / `m_duct_sm_{fam}` | `de, ge = stub["duct_end"], stub["grille_end"]`، `z = zc_b(STUB_H)`: `["d", [[de[0], de[1], z], [ge[0], ge[1], z]], STUB_W, STUB_H]` | — |
| 7.ب | VCD | `M.damper` / `B` / `damper_cp_{fam}` / `m_damper_ve` | أقرب عنصر من `D["B"]["vcd"]` لـ`ge` (المسافة ≤ `VCD_R`): `["b", v["x"], v["y"], DAMPER_ALONG, STUB_W + DAMPER_PAD, ang(de, ge), round(z - STUB_H/200 - 0.04, 3), round(z + STUB_H/200 + 0.04, 3)]` | `"VCD"` |
| 7.ج | الشبكة | `M.outlet` / `B` / `grille_cp_{fam}` / `m_grille_fa` | أقرب عنقود `c` من `F["grilles"]` لـ`ge` (≤ `CLUSTER_R`)؛ إن كان `c["h"] > c["w"]` فـ`rot, T = 90, c["w"]` وإلا `rot, T = 0, c["h"]`: `["b", c["x"], c["y"], GRILLE_LEN[fam], T, rot, round(z - GRILLE_H/200, 3), round(z + GRILLE_H/200, 3)]` | `"FAG"` أو `"EAG"` |

**(ب) صاعدا الممرات في الدور الأرضي** (مستوى `G`، النوعان `riser_co_fa` ثم `riser_co_ea`، المادة `m_duct_sm_fa` / `m_duct_sm_ea`، الفئة `M.duct`): `["b", RISER_CENTRE[fam][0], RISER_CENTRE[fam][1], RISER[fam][0], RISER[fam][1], 0, ffl["G"], round(slab_bot("1"), 3)]`، الخاصية `a.shaft = True`.

**(ج) طوابق الممرات — لكل `lv` في `FLOORS` بالترتيب** (`S = D["1"] if lv == "1" else D["TY"]`، `f0 = ffl[lv]`، `nxt = ORDER[ORDER.index(lv) + 1]`):

| # | العنصر | الفئة / النوع / المادة | الهندسة | `mark` |
|---|---|---|---|---|
| 1 | صاعد FA | `M.duct` / `riser_co_fa` / `m_duct_sm_fa` | `["b", *RISER_CENTRE["fa"], *RISER["fa"], 0, round(slab_bot(lv), 3), round(slab_bot(nxt), 3)]` و`a.shaft = True` | — |
| 2 | صاعد EA | `M.duct` / `riser_co_ea` / `m_duct_sm_ea` | `["b", *RISER_CENTRE["ea"], *RISER["ea"], 0, round(slab_bot(lv), 3), round(slab_bot(nxt), 3)]` و`a.shaft = True` | — |
| 3 | فرع FA إلى الشبكة | `M.duct` / `duct_co_fa` / `m_duct_sm_fa` | `fx = S["fa_riser"][0]["x"]`، `fy0 = S["fa_riser"][0]["y"]`، `fy1 = min(S["fag_box"], key=lambda b: b["h"])["y"]` (الوجه الرفيع 34×2.3 سم)، `z = round(f0 + sum(Z_FAG)/2, 3)`: `["d", [[fx, fy0, z], [fx, fy1, z]], COR_FA_BRANCH[0], COR_FA_BRANCH[1]]` | — |
| 4 | MFD الخاص بـFA | `M.damper` / `damper_co_fa` / `m_damper_ve` | المخمّد من `S["dampers"]` الذي `layer == "M_HVAC_DAM"` ومركزه x < 1340 (مركزه `dx, dy`): `["b", dx, dy, DAMPER_ALONG, COR_FA_BRANCH[0] + DAMPER_PAD, -90.0, round(z - 0.14, 3), round(z + 0.14, 3)]` | `"MFD"` |
| 5 | شبكة SMS FAG | `M.outlet` / `grille_co_fa` / `m_grille_fa` | `["b", fx, fy1, FAG_COR[0], FAG_COR[1], 0, round(f0 + Z_FAG[0], 3), round(f0 + Z_FAG[1], 3)]` | `"FAG"` |
| 6 | فرع EA | `M.duct` / `duct_co_ea` / `m_duct_sm_ea` | `ex, ey0 = S["ea_riser"][0]["x"], S["ea_riser"][0]["y"]`، `b = S["ea_branch"][0]`، `ey1 = b[1][1]` (نهاية الفرع)، `ez = round(f0 + BOTTOM_COR + COR_EA_BRANCH[1]/200, 3)`: `["d", [[ex, ey0, ez], [b[1][0], ey1, ez]], COR_EA_BRANCH[0], COR_EA_BRANCH[1]]` | — |
| 7 | MFD الخاص بـEA | `M.damper` / `damper_co_ea` / `m_damper_ve` | الذي `layer == "M_VE_DAM"` ومركزه 1340 < x < 1370 (مركزه `dx, dy`): `["b", dx, dy, DAMPER_ALONG, COR_EA_BRANCH[0] + DAMPER_PAD, -90.0, round(ez - 0.14, 3), round(ez + 0.14, 3)]` | `"MFD"` |
| 8 | مجرى الممر (قطعتان) | `M.duct` / `duct_co_ea` / `m_duct_sm_ea` | `m = S["ea_main"][0]`، `jx = b[1][0]` (x نقطة الوصل)، `mz = round(f0 + BOTTOM_COR + COR_EA_MAIN[1]/200, 3)`، `my = m[0][1]`: قطعة 1 من `m[0]` إلى `[jx, my]` ثم قطعة 2 من `[jx, my]` إلى `m[1]`، كلتاهما `["d", [[x0, my, mz], [x1, my, mz]], COR_EA_MAIN[0], COR_EA_MAIN[1]]` | — |
| 9 | VCD (اثنان بترتيب x) | `M.damper` / `damper_co_ea` / `m_damper_ve` | من `S["dampers"]` الذي `layer == "M_VE_DAM"` ومركزه x < 1340 أو x > 1370: `["b", dx, my, DAMPER_ALONG, COR_EA_MAIN[0] + DAMPER_PAD, 0, round(mz - COR_EA_MAIN[1]/200 - 0.04, 3), round(mz + COR_EA_MAIN[1]/200 + 0.04, 3)]` | `"VCD"` |
| 10 | ناشرا EAD (اثنان بترتيب x) | `M.outlet` / `diff_co_ea` / `m_diff_ea` | `z1 = round(ceil_z(lv, d["x"], d["y"], f0 + 2.40), 3)`: `["b", d["x"], d["y"], EAD, EAD, 0, round(z1 - 0.04, 3), z1]` (`d` من `S["ead"]`) | `"EAD"` |

**(د) السطح `R`** (`S = D["R"]`، `f0 = ffl["R"]`):
1. صاعد FA: `riser_co_fa` / `m_duct_sm_fa`: `["b", *RISER_CENTRE["fa"], *RISER["fa"], 0, round(slab_bot("R"), 3), round(f0 + ROOF_BOTTOM + ROOF_DUCT["fa"][1]/100 + 0.02, 3)]` و`a.shaft = True`.
2. صاعد EA: بالمثل بـ`riser_co_ea` / `RISER["ea"]` / `ROOF_DUCT["ea"][1]`.
3. مجرى FA: النقطة الأولى من `S["fa_duct"][0]` **تُستبدل بمركز صاعد FA** `RISER_CENTRE["fa"]` ثم قطعة لكل ضلع (ثلاث قطع): `["d", [[x0,y0,z],[x1,y1,z]], 40.0, 25.0]` بـ`z = round(f0 + ROOF_BOTTOM + 25.0/200, 3)`، النوع `duct_co_fa`.
4. مجرى EA: كذلك من `S["ea_duct"][0]` (النقطة الأولى تُستبدل بـ`RISER_CENTRE["ea"]`) خمس قطع، `30.0 × 20.0`، `z = round(f0 + ROOF_BOTTOM + 20.0/200, 3)`، النوع `duct_co_ea`.
5. مخمّدا MFD (من `S["dampers"]` كلاهما `M_HVAC_DAM`): الذي x < 1340 على مجرى FA (`damper_co_fa`، عرض الصندوق 40 + 8 = 48) والذي x > 1340 على مجرى EA (`damper_co_ea`، 30 + 8 = 38): `["b", dx, dy, DAMPER_ALONG, width + DAMPER_PAD, 0, round(z - h/200 - 0.04, 3), round(z + h/200 + 0.04, 3)]` بـ`z` ومركزه الرأسي ومقاسه h الخاصّين بمجراه، و`mark = "MFD"`.
6. المروحتان `M.fan` / `m_fan`: **SMSF** (`fan_co_fa`، `mark "SMSF"`) = المستطيل ذو أكبر `w` من `fan_rects` التي `abs(y - 1138) < 60`: `["b", r["x"], r["y"], r["w"], r["h"], 0, round(f0, 3), round(f0 + FAN_ROOF_H, 3)]`؛ **SMEF** (`fan_co_ea`، `mark "SMEF"`) = المستطيل ذو أكبر `w` من `fan_rects` التي `abs(y - 1758) < 60`.
7. ردّادا المروحتين `M.outlet` / `m_grille_fa`: `lv = S["louvers"]["fa"]` (`louver_co_fa`) و`["ea"]` (`louver_co_ea`): `["b", (x0+x1)/2, (y0+y1)/2, x1 - x0, y1 - y0, 0, round(f0 + LOUVER_ROOF[0], 3), round(f0 + LOUVER_ROOF[1], 3)]`.

**ترتيب إنشاء المعرّفات الكامل (لا يتغير):** البدروم `fa` (بنود 1–6 ثم 7 لكل فرع) ← البدروم `ea` ← (ب) ← (ج) للطوابق 1..5 ← (د) بالترتيب 1..7.

**المجموع المتوقع: 209 عنصرًا** (تفصيله في القسم 7).

### 5.6 خصائص `a` لكل عنصر (حرفيًا)

المفاتيح: `sys` (معرّف النظام)، `w_cm` وh_cm (أبعاد المقطع أو المسقط)، `kind` (وصف عربي قصير)، `part` (الجزء)، `size_note` (للمجاري فقط)، `assumed` (نص الافتراض إن وُجد)، `flow_ls` أو `flow_modes_ls`، `label` (الوسم المنسوخ من المخطط)، `size_mm`، `damper`، `shaft`. أمثلة جاهزة للنسخ:

```python
SYS = {("cp", "fa"): "smk_cp_fa", ("cp", "ea"): "smk_cp_ea", ("co", "fa"): "smk_co_fa", ("co", "ea"): "smk_co_ea"}
NOTE_WH = "مقاس الوسم «العرض×الارتفاع» بالمليمتر؛ إن كان الترتيب معكوسًا فالارتفاع الصافي تحت المجرى أكبر — بانتظار تأكيدك"
ASSUME_Z_CP = "ارتفاع المجرى افتراض: قمته تحت بلاطة الدور الأرضي بـ5 سم (−0.50 م)؛ المخطط يعطي المسقط والمقاس لا المنسوب"
ASSUME_Z_COR = "ارتفاع المجرى في فراغ السقف افتراض: الجنب السفلي 2.52 م فوق الأرضية"
ASSUME_Z_FAG = "ارتفاع فتحة الهواء على جدار الشفت افتراض: 2.05–2.25 م فوق الأرضية (تحت السقف المستعار 2.40 م)"
ASSUME_Z_ROOF = "ارتفاع المجرى فوق السطح افتراض: الجنب السفلي 0.60 م فوق الأرضية على حوامل"
ASSUME_FAN_CP = "هيكل المروحة افتراض: رمز المسقط (37×54 سم) تخطيطي؛ طول الهيكل 80 سم وعرضه بعرض المجرى وارتفاعه بارتفاعه"
ASSUME_FAN_ROOF = "هيكل المروحة من مستطيل AV-MAC في مسقط السطح؛ ارتفاعه 1.20 م افتراض"
ASSUME_LOUVER_HEAD = "الردّادات: المرسوم نص «L×H 2 م × 1.5 م — 3 عدد» ولا موضع لها في المسقط؛ رُسم رأس بصمة الشفت نفسها بارتفاع 1.5 م، ومواضع الردّادات الثلاثة الفعلية — بانتظار تأكيدك"
ASSUME_LOUVER_ROOF = "ردّاد مروحة السطح: مستطيل التهشير في المسقط؛ ارتفاعه 0.9 م (0.30–1.20 م فوق الأرضية) افتراض"
ASSUME_INHERIT = "مقطع بلا وسم مقاس: أُخذ مقاس المقطع الأقرب إلى نقطة الوصل (أو أقرب وسم) — بانتظار تأكيدك"
ASSUME_STUB_EA = "الفروع 300×200 مم بلا وسم على جانب الشفط؛ أُخذت مساويةً لجانب هواء التعويض الموسوم — بانتظار تأكيدك"
```

- **المجاري ذات الأذرع:** `a = {"sys": SYS[area, fam], "w_cm": w, "h_cm": h, "kind": "مجرى هواء تعويض لإدارة الدخان" أو "مجرى شفط دخان", "part": "قطعة وصل بين الشفت والتفرّع الرئيسي" | "مجرى رئيسي (ذراع)" | "فرع 300×200 مم إلى الشبكة", "size_note": ("من وسم المخطط" if labelled else ASSUME_INHERIT) + ". " + NOTE_WH, "assumed": ASSUME_Z_CP}` (والفرع على جانب الشفط يُضاف إلى `assumed`: ` + " | " + ASSUME_STUB_EA`). في الممرات `assumed = ASSUME_Z_COR` (وللفرع FA: `ASSUME_Z_FAG`) وفي السطح `ASSUME_Z_ROOF`.
- **الصواعد والرؤوس:** `a = {"sys": ..., "w_cm": sw, "h_cm": sd, "shaft": True, "kind": ..., "label": ..., "size_mm": ...}` بالقيم: البدروم FA: `label "P.FA DUCT-F/A 9000 L/S 1400 mm x 1000 mm"`، `size_mm "1400x1000"`؛ EA: `label "P.EX DUCT-T/A 10600 L/S 1600 mm x 1000 mm"`، `size_mm "1600x1000"`؛ رأس الردّادات: `label "FRESH AIR INTAKE LOUVER — L X H 2 M X 1.5 M — 3 NOS."` أو `"EXTRACT AIR LOUVER — L X H 2 M X 1.5 M — 3 NOS."` و`assumed ASSUME_LOUVER_HEAD`. صواعد الممرات: `label "SMS FA DUCT 284 L/S 400 x 250 -F/A-T/B"` (`size_mm "400x250"`، `flow_ls 284`) و`"SMS EA DUCT 167 L/S 300 x 200 -F/B-T/A"` (`size_mm "300x200"`، `flow_ls 167`)؛ وفي الدور الأرضي أضِف `part: "القطعة من مخطط الصاعد SM-105؛ مسقط SM-101 لا يرسم الصاعد ولا فرع الدور الأرضي — بانتظار تأكيدك"`.
- **المراوح:** البدروم FA: `kind "مروحة هواء التعويض معلّقة بالسقف (Ceiling suspended Type) — Car Park Makeup Fan"`، `flow_modes_ls "9000 (10 ACH) · 5400 (6 ACH) · 2700 (3 ACH)"`؛ EA: `kind "مروحة شفط الدخان معلّقة بالسقف (Ceiling suspended Type) — Car Park E.A Fan"`، `flow_modes_ls "10600 (10 ACH) · 6360 (6 ACH) · 3180 (3 ACH)"`؛ وكلتاهما `assumed ASSUME_FAN_CP`. السطح: `kind "مروحة هواء تعويض الممرات SMSF — مقاومة 400 °م لساعتين"` (`flow_ls 284`) و`"مروحة شفط دخان الممرات SMEF — مقاومة 400 °م لساعتين"` (`flow_ls 167`) و`assumed ASSUME_FAN_ROOF`.
- **المخمّدات:** `a = {"sys": ..., "damper": "FD"|"VCD"|"MFD", "kind": "مخمّد حريق FD عند الشفت" | "مخمّد ضبط تدفق VCD" | "مخمّد حريق ودخان آلي MFD (يُسمّى MSFD في مخطط الصاعد SM-105)"}`.
- **الشبكات:** البدروم: `a = {"sys":..., "w_cm": GRILLE_LEN[fam], "h_cm": GRILLE_H, "size_mm": "1500x200" | "1700x200", "kind": "شبكة هواء تعويض FAG" | "شبكة شفط دخان EAG", "flow_modes_ls": "208 (3 ACH، CO منخفض) · 415 (6 ACH، CO مرتفع) · 693 (10 ACH، حريق)" | "245 (3 ACH) · 489 (6 ACH) · 815 (10 ACH، حريق)", "label": "13 NO. FAG 1500 mm x 200 mm" | "13 NO. EAG 1700 mm x 200 mm", "assumed": "الطول من وسم المخطط؛ رمز المسقط (80 سم) تخطيطي"}`. الممرات: `grille_co_fa`: `flow_ls 142`، `size_mm "400x200"`، `label "SMS FAG 142 L/S 400x200 mm"`، `assumed ASSUME_Z_FAG`؛ `diff_co_ea`: `flow_ls 84`، `size_mm "225x225"`، `label "2 No. SMS EAD 84 L/S EACH 225 x 225 mm"`.
- **الردّادات (السطح):** `a = {"sys":..., "kind": "ردّاد مروحة السطح (مصيدة رمل وشبكة طيور)", "assumed": ASSUME_LOUVER_ROOF}`.

### 5.7 `MATS` و`TYPES` (انسخ حرفيًا ثم أكمل الحلقة)

```python
SRC_CP = "مخططات إدارة الدخان لموقف السيارات: SM-100 (البدروم، MECH1 ص17) وSM-101 (الدور الأرضي، MECH1 ص18) ومخطط الصاعد SM-105 (MECH1 ص22): المسارات والمقاسات ومواضع الشبكات والمخمّدات والمراوح كما رُسمت؛ ارتفاع المجاري وأبعاد هياكل المراوح افتراض (pipeline/smoke_build.py)"
SRC_CO = "مخططات إدارة الدخان للممرات: SM-102 (الأول، MECH1 ص19) وSM-103 (النمطي، MECH1 ص20) وSM-104 (السطح، MECH1 ص21) ومخطط الصاعد SM-105 (MECH1 ص22): الصاعدان والفروع والناشرات والمخمّدات والمراوح كما رُسمت؛ المناسيب افتراض (pipeline/smoke_build.py)"
MATS = {"m_duct_sm_fa": {"name": "مجرى هواء تعويض لإدارة الدخان", "color": "#4f8fa8", "code": "SM"},
        "m_duct_sm_ea": {"name": "مجرى شفط دخان (مقاوم للحرارة)", "color": "#a8553a", "code": "SM"}}
AREA_AR = {"cp": "موقف السيارات (البدروم)", "co": "الممرات"}
FAM_AR = {"fa": "هواء التعويض", "ea": "شفط الدخان"}
KIND_AR = {"duct": "مجرى", "riser": "صاعد / شفت", "damper": "مخمّد", "duct_flex": "وصلة مرنة (مشتقة)", "fan": "مروحة", "louver": "ردّاد", "grille": "شبكة", "diff": "ناشر شفط EAD"}
CF = {"duct": "doc", "riser": "doc", "damper": "doc", "duct_flex": "derived", "fan": "doc", "louver": "assumed", "grille": "doc", "diff": "doc"}
SP_AR = {"cp": "مخططات SM-100 وSM-101 وSM-105 (MECH1 ص17 وص18 وص22)", "co": "مخططات SM-102 وSM-103 وSM-104 وSM-105 (MECH1 ص19–22)"}
TYPES = {}
for _area in ("cp", "co"):
    for _fam in ("fa", "ea"):
        kinds = ["duct", "riser", "damper", "duct_flex", "fan", "louver"] + (["grille"] if (_area, _fam) != ("co", "ea") else ["diff"])
        for _k in kinds:
            spl = [["المصدر", SP_AR[_area]], ["المقاومة", "400 °م لساعتين بحسب ملاحظات المخطط"]]
            if _k == "duct": spl += [["المقاس", "وسم المقاس على المخطط (مم، العرض × الارتفاع)"], ["الارتفاع", "افتراض (المخطط يعطي المسقط لا المنسوب)"]]
            if _k == "riser": spl += [["المقاس", "صندوق الشفت في المسقط ووسم المقاس"]]
            if _k == "damper": spl += [["النوع", "FD أو VCD أو MFD بحسب الكلمة المجاورة للرمز"]]
            if _k == "duct_flex": spl += [["الأصل", "وصلة مشتقة من المسقط (pipeline/connectors.py)"]]
            t = {"n": f"{KIND_AR[_k]} — {FAM_AR[_fam]} — {AREA_AR[_area]}", "cf": CF[_k], "sp": spl, "sr": []}
            if _k == "fan": t["asm"] = ["أبعاد هيكل المروحة افتراض؛ رمز المسقط تخطيطي"]
            if _k == "louver": t["asm"] = ["موضع الردّادات الثلاثة (2×1.5 م) غير مرسوم؛ رُسم رأس بصمة الشفت" if _area == "cp" else "ارتفاع ردّاد مروحة السطح افتراض"]
            TYPES[f"{_k}_{_area}_{_fam}"] = t
```
هذا يُنتج **28 نوعًا** (24 + 3 شبكات + ناشر واحد) بأسماء مثل `duct_cp_fa` و`duct_flex_co_ea` و`grille_co_fa` و`diff_co_ea`.

## 6. الخطوة 3 — التوصيل (تعديلات صغيرة بنصوص حرفية)

### 6.1 `pipeline/post_model.py` (ثلاثة مواضع؛ ابحث بالنص الظاهر)

1. بعد السطر الذي يحوي `-VT\d{4}$` (نحو السطر 33) أضف:
```python
els[:] = [e for e in els if not re.search(r"-SM\d{4}$", e["id"])]     # smoke-management ducts / fans / grilles of pipeline/smoke_build.py (suffix SM) are rebuilt before the support analysis
```
2. استبدل
```python
import vent_build as _VT
_VT.build(M, els, verbose=True)
M["els"] = els
```
بـ
```python
import vent_build as _VT
_VT.build(M, els, verbose=True)
import smoke_build as _SM                                                  # smoke management (MECH1 p17–22): same slot, after the ceilings (EAD plates) and before the support analysis
_SM.build(M, els, verbose=True)
M["els"] = els
```
3. بعد السطر `M["types"].update(_VT.TYPES)` أضف: `M["types"].update(_SM.TYPES)                                           # smoke-management types (cards written in pipeline/smoke_build.py)`

### 6.2 `pipeline/lifecycle.py`

1. استبدل السطر الذي يبدأ بـ`VENT_T = (` بسطرين:
```python
SMK_T = tuple(f"{k}_{a}_{f}" for a in ("cp", "co") for f in ("fa", "ea") for k in ("duct", "riser", "damper", "duct_flex"))     # the smoke-management network (pipeline/smoke_build.py)
VENT_T = ("duct_ea", "duct_fa", "riser_ea", "riser_fa", "damper_ea", "damper_fa", "duct_flex_ea", "duct_flex_fa") + SMK_T       # the ventilation + smoke networks are tested apart from the supply air
```
2. قبل السطر `SYSTEMS = [` أضف الدالة:
```python
def _smk_sys(sid, area, fam, name, icon, color, desc, src_name, term_t, term_name, sink=False):
    cond = (f"duct_{area}_{fam}", f"riser_{area}_{fam}", f"damper_{area}_{fam}", f"duct_flex_{area}_{fam}")
    d = dict(id=sid, name=name, icon=icon, color=color, desc=desc,
             source=lambda e: e["c"] == "M.fan" and _t(e) == f"fan_{area}_{fam}",
             variants=[("الشبكة", lambda e: e["c"] in ("M.duct", "M.damper") and _t(e) in cond)],
             terminal=lambda e: e["c"] == "M.outlet" and _t(e) == term_t,
             term_name=lambda e: term_name, source_name=src_name, conductor_name="مجرى إدارة الدخان")
    if sink: d["sink"] = True
    return d
```
3. داخل القائمة، **قبل** السطر `    dict(id="cold", joint_end_only=False,` أضف الأسطر الأربعة:
```python
    _smk_sys("smk_cp_fa", "cp", "fa", "إدارة الدخان — هواء تعويض الموقف", "🅿", "#3f8fb0",
             "مروحة هواء التعويض المعلّقة بالسقف في البدروم (9000 لتر/ث) ← الشفت 1400×1000 مم والمخمّد FD ← المجرى الرئيسي بمقاطعه المتناقصة ← الفروع 300×200 مم ومخمّدات VCD ← 13 شبكة FAG 1500×200 مم (المرسوم في SM-100 وSM-101 وSM-105)",
             "مروحة هواء تعويض الموقف", "grille_cp_fa", "شبكة FAG"),
    _smk_sys("smk_cp_ea", "cp", "ea", "إدارة الدخان — شفط دخان الموقف", "💨", "#9a5a3c",
             "الشبكات EAG 1700×200 مم (13) ← الفروع ومخمّدات VCD ← المجرى الرئيسي ← المخمّد FD والمروحة المعلّقة بالسقف (10600 لتر/ث) ← الشفت 1600×1000 مم (الاتجاه معكوس: يُختبر الوصل من المروحة نحو الشبكات)",
             "مروحة شفط دخان الموقف", "grille_cp_ea", "شبكة EAG", sink=True),
    _smk_sys("smk_co_fa", "co", "fa", "إدارة الدخان — هواء تعويض الممرات", "🚪", "#5aa9a0",
             "مروحة السطح SMSF (284 لتر/ث) ← مجرى السطح 400×250 مم والمخمّد MFD ← الصاعد ينزل بين الطوابق ← فرع كل طابق ومخمّده MFD ← شبكة SMS FAG 400×200 مم (142 لتر/ث) في الطوابق 1–5 (SM-102…SM-105)",
             "مروحة السطح SMSF", "grille_co_fa", "شبكة SMS FAG"),
    _smk_sys("smk_co_ea", "co", "ea", "إدارة الدخان — شفط دخان الممرات", "🌫", "#8a6f9e",
             "ناشرا SMS EAD (225×225 مم، 84 لتر/ث لكلٍّ) في كل طابق ← مجرى الممر 250×150 مم ومخمّدا VCD ← الفرع 300×200 مم والمخمّد MFD ← الصاعد إلى السطح ← المخمّد والمجرى 300×200 مم ← المروحة SMEF (167 لتر/ث) (الاتجاه معكوس: يُختبر الوصل من المروحة نحو الناشرات)",
             "مروحة السطح SMEF", "diff_co_ea", "ناشر SMS EAD", sink=True),
```

### 6.3 `pipeline/connectors.py`
استبدل السطر الذي يبدأ بـ`CONN_SYS = {` بـ:
```python
CONN_SYS = {"vent_ea": ("duct_flex_ea", "m_duct_ea"), "vent_fa": ("duct_flex_fa", "m_duct_fa"),      # the ventilation and smoke ducts have their own types: the supply-air test must not count their flexible pieces
            "smk_cp_fa": ("duct_flex_cp_fa", "m_duct_sm_fa"), "smk_cp_ea": ("duct_flex_cp_ea", "m_duct_sm_ea"),
            "smk_co_fa": ("duct_flex_co_fa", "m_duct_sm_fa"), "smk_co_ea": ("duct_flex_co_ea", "m_duct_sm_ea")}
```

### 6.4 `pipeline/inventory.py`
1. في قائمة `FEATURES` استبدل نص بند دورة الحياة القائم «اختبارات دورة الحياة لتسعة أنظمة (كهرباء، إطفاء، مبردة، هواء تغذية، تهوية نقية وشفط، باردة، ساخنة، صرف)» بـ«اختبارات دورة الحياة لثلاثة عشر نظامًا (كهرباء، إطفاء، مبردة، هواء تغذية، تهوية نقية وشفط، باردة، ساخنة، صرف، وإدارة الدخان: تعويض الموقف وشفطه وتعويض الممرات وشفطها)».
2. بعد بند التهوية أضف: `("الأنظمة", "إدارة الدخان: مجاري هواء التعويض وشفط الدخان لموقف البدروم (13 شبكة FAG و13 EAG) وصاعدا الممرات ومخمّدات MFD ومروحتا السطح (مخططات SM-100…SM-105)", "pipeline/smoke_build.py", r"def build", None),`

### 6.5 `src/app.js` (تسميات عربية للمفاتيح؛ تفيد التهوية وإدارة الدخان معًا)
في السطر الذي ينتهي بـ`sched_note:'ملاحظة مطابقة الجدول'};` (داخل الكائن `ATTR`) استبدل النهاية بـ:
```js
sched_note:'ملاحظة مطابقة الجدول',sys:'النظام',flow_ls:'التدفق (لتر/ث)',flow_modes_ls:'التدفق بحسب الوضع (لتر/ث)',damper:'نوع المخمّد',neck_mm:'الرقبة (مم)',label:'الوسم على المخطط',bar_cm:'طول الرمز (سم)',bridge:'جسر قطع في الرسم',shaft:'صاعد / شفت',size_mm:'المقاس (مم)'};
```
ثم شغّل فحص JavaScriptCore (القسم 2) وتأكد أن كل الملفات `ok`.

## 7. الخطوة 4 — التشغيل والتحقق (كلها إلزامية)

1. `python3 pipeline/post_model.py > /tmp/pm.log 2>&1; tail -30 /tmp/pm.log` ثم `python3 src/build.py`. ابحث في السجل عن السطر `smoke management: 209 {...}` و`support analysis:` (لا يجوز أن يظهر عنصر `-SM` في قائمة `no host found`).
2. **عدد العناصر والأنواع:**
```bash
python3 - <<'PY'
import json, re, collections
M = json.load(open("src/model.json", encoding="utf-8"))
sm = [e for e in M["els"] if re.search(r"-SM\d{4}$", e["id"])]
print("total", len(sm))
print("by type:", sorted(collections.Counter(e["t"] for e in sm).items()))
print("by level:", sorted(collections.Counter(e["l"] for e in sm).items()))
PY
```
**المتوقع حرفيًا:** `total 209`؛ الأنواع: `damper_co_ea 16`، `damper_co_fa 6`، `damper_cp_ea 14`، `damper_cp_fa 14`، `diff_co_ea 10`، `duct_co_ea 20`، `duct_co_fa 8`، `duct_cp_ea 31`، `duct_cp_fa 35`، `fan_co_ea 1`، `fan_co_fa 1`، `fan_cp_ea 1`، `fan_cp_fa 1`، `grille_co_fa 5`، `grille_cp_ea 13`، `grille_cp_fa 13`، `louver_co_ea 1`، `louver_co_fa 1`، `louver_cp_ea 1`، `louver_cp_fa 1`، `riser_co_ea 7`، `riser_co_fa 7`، `riser_cp_ea 1`، `riser_cp_fa 1`؛ والمستويات: `B 124`، `G 4`، `1 13`، `2 13`، `3 13`، `4 13`، `5 13`، `R 16`.
3. **اختبارات دورة الحياة:** `python3 pipeline/lifecycle.py | tail -16`. **المتوقع:** الأنظمة الأربعة الجديدة تُظهر `terminals` = 13 و13 و5 و10 وعدد `distribution` مساويًا لها بالضبط (`failed 0`)، والأنظمة القديمة بلا تغيير: `power 766`، `fire 475`، `chw 85`، `air 360`، `vent_fa 68`، `vent_ea 125`، `cold 282`، `hot 121`، `drain 134`، وبلا سطر `REGRESSION`. إن لم يُوصَل طرف استهلاك فشخّص (الأمر `python3 pipeline/lifecycle.py` يذكر السبب) وصحّح **شيفرتك**؛ ممنوع تغيير `TOL`. **أداة التشخيص** (غيّر `smk_cp_fa` إلى النظام المطلوب):
```bash
python3 - <<'PY'
import sys, json; sys.path.insert(0, "pipeline")
import lifecycle as L
M = json.load(open("src/model.json", encoding="utf-8")); world = L.World(M["els"])
sd = next(s for s in L.SYSTEMS if s["id"] == "smk_cp_fa")
R = L.analyse_system(M, sd, world)
print("unreached terminals:", [M["els"][R["units"][k][0]]["id"] for k in R["bad"]])
print("orphan conductors:", [M["els"][i]["id"] for i in R["orph"]][:20], len(R["orph"]))
PY
```
العنصر غير الموصول إما لا يلامس فرعه (راجع الهندسة في 5.5) أو يلامس شبكة منفصلة (راجع إحداثيات الاستخراج).
4. **الوصلات المرنة:** في سجل `post_model` سطر `connectors:` يجب أن يحوي `smk_co_ea/stub` بقيمة 10 (± 2). إن ظهرت وصلات `joint` أو `stub` لأنظمة `smk_cp_*` فهذا يعني فجوة هندسية في شيفرتك (الشبكات لا تلامس فروعها): راجع القسم 5.5 (7.ج).
5. **ثبات المعرّفات (ثلاث دورات):**
```bash
cp src/model.json /tmp/m0.json
python3 pipeline/post_model.py > /dev/null 2>&1 && cp src/model.json /tmp/m1.json
python3 pipeline/post_model.py > /dev/null 2>&1 && cp src/model.json /tmp/m2.json
python3 - <<'PY'
import json
a, b, c = [json.load(open(f"/tmp/m{i}.json", encoding="utf-8")) for i in (0, 1, 2)]
ids = lambda m: {e["id"] for e in m["els"]}
print("ids equal 0=1:", ids(a) == ids(b), " 1=2:", ids(b) == ids(c), " count:", len(ids(c)))
import re
sm = lambda m: sorted((e["id"], json.dumps(e["g"], sort_keys=True)) for e in m["els"] if re.search(r"-SM\d{4}$", e["id"]))
print("SM geometry equal 1=2:", sm(b) == sm(c))
PY
```
**المتوقع:** `ids equal 0=1: True  1=2: True` (حيث 0 هو الناتج بعد الخطوة 1 من القسم 7 نفسها) و`SM geometry equal 1=2: True`. ثم أعد البناء `python3 src/build.py`.
6. **عدد الأوراق في الجرد:** `docs/INVENTORY.md` يجب أن يُظهر ارتفاع «أوراق مُستشهَد بها» من 136 إلى **142** (الأوراق 17–22 من MECH1)؛ إن اختلف الرقم فاذكره في التقرير.
7. **الفرق في التعارضات:** سجّل سطر `clashes` الجديد من `post_model` (كان 564 قبل هذه الدفعة) في التقرير. **لا تحاول «إصلاح» التعارضات الجديدة بتحريك العناصر**: هي نتيجة المناسيب الافتراضية والبلاطات غير المثقوبة وتُرفع للمالك.

## 8. الخطوة 5 — الفحص المرئي (إلزامي إن أمكن تشغيل Chrome)

```bash
# 1) خادم الصفحة (من جذر المستودع) ثم 2) Chrome بلا واجهة (مرة واحدة) — الأوامر الأصلية في رأس tools/cdp.py
python3 -m http.server 8765 &
~/Library/Caches/ms-playwright/chromium_headless_shell-1223/chrome-headless-shell-mac-arm64/chrome-headless-shell --no-sandbox --remote-debugging-port=9222 \
  --use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader --hide-scrollbars --user-data-dir=/tmp/c4qa about:blank &
```
احفظ هذه الخطوات في `/tmp/smk_steps.json` ثم شغّل `python3 tools/qa.py 1400x900 /tmp/smk_steps.json` ثم `python3 tools/qa.py 390x844 /tmp/smk_steps.json`:

```json
[
 {"wait": 3},
 {"print": "window.__dbg.LIFE.systems.filter(s=>s.id.indexOf('smk_')===0).map(s=>[s.id,s.cnt.ter,s.cnt.ok,s.tests.map(t=>t.p).join('')])"},
 {"eval": "(()=>{const L=window.__dbg.LIFE;L.select(L.systems.findIndex(s=>s.id==='smk_cp_fa'));L.play();return 1})()"}, {"wait": 3}, {"shot": "smk_cp_fa"},
 {"eval": "(()=>{const L=window.__dbg.LIFE;L.stop();L.select(L.systems.findIndex(s=>s.id==='smk_cp_ea'));L.play();return 1})()"}, {"wait": 3}, {"shot": "smk_cp_ea"},
 {"eval": "(()=>{const L=window.__dbg.LIFE;L.stop();L.select(L.systems.findIndex(s=>s.id==='smk_co_fa'));L.play();return 1})()"}, {"wait": 3}, {"shot": "smk_co_fa"},
 {"eval": "(()=>{const L=window.__dbg.LIFE;L.stop();L.select(L.systems.findIndex(s=>s.id==='smk_co_ea'));L.play();return 1})()"}, {"wait": 3}, {"shot": "smk_co_ea"},
 {"eval": "window.__dbg.LIFE.stop();1"}
]
```
**المتوقع:** السطر المطبوع يُظهر الأنظمة الأربعة بـ`[id, 13, 13, ...]` و`[id, 13, 13...]` و`5/5` و`10/10`؛ وفي آخر التشغيل `errors: []` للحجمين. **افحص اللقطات** (`/tmp/claude-501/shots/smk_*.png`): يجب أن تظهر الشبكة مضاءة متصلة من المروحة إلى الشبكات بلا قطع ظاهرة. إن تعذّر Chrome فاكتب ذلك صراحة في التقرير ولا تعدّ الفحص المرئي منجزًا.

## 9. الخطوة 6 — التوثيق

### 9.1 `docs/PROGRESS.md` — أضِف قسمًا جديدًا **قبل** السطر `## الدفعة 8 — بطاقات كل الأنواع` (املأ الأرقام من تشغيلك الفعلي)
```markdown
## الدفعة 17 — إدارة الدخان: موقف البدروم والممرات (2026-10-08، نُفِّذت بتعليمات مكتوبة عبر Codex)
- **المصدر:** MECH1 ص17–22 (SM-100…SM-105). `pipeline/smoke_extract.py` ← `pipeline/data/smoke.json` ← `pipeline/smoke_build.py` (معرّفات `-SMnnnn`، تُحذف وتُبنى كل مرة قبل مدقّق الدعم). **209 عناصر:** مجاريان رئيسيان للموقف (هواء تعويض 9000 لتر/ث وشفط 10600 لتر/ث) بمقاطعهما المتناقصة من وسوم المخطط، و13 شبكة FAG و13 EAG بفروعها 300×200 مم ومخمّدات VCD، ومخمّدا FD ومروحتان معلّقتان بالسقف وشفتان 1400×1000 و1600×1000 مم؛ وصاعدا الممرات (400×250 و300×200 مم) من الدور الأرضي إلى السطح وفرع كل طابق من 1 إلى 5 (مخمّد MFD وشبكة SMS FAG ومجرى الممر 250×150 مم وناشرا SMS EAD) ومروحتا السطح SMSF وSMEF بقناتيهما وردّاديهما.
- **اختبارات دورة الحياة:** أربعة أنظمة جديدة `smk_cp_fa` و`smk_cp_ea` و`smk_co_fa` و`smk_co_ea`؛ النتيجة {أدرج من التشغيل}. `SMK_T` يعزل مجاري الدخان عن «هواء التغذية». وصلات مرنة مشتقة للناشرين EAD (`smk_co_ea/stub`).
- **ما لم يُرسم فلم يُنشأ:** مواضع الردّادات الثلاثة (2×1.5 م) عند كل شفت في الدور الأرضي؛ صاعد ممرات الدور الأرضي وفرعه (يرسمهما SM-105 ولا يرسمهما SM-101)؛ حساسات CO؛ ستائر الدخان (ملاحظة عامة بلا مواضع)؛ مضخات ضغط الدرج والمصعد LPF/SPF (في المفتاح فقط).
- **افتراضات موسومة (انظر `a.assumed` في بطاقة كل عنصر):** ارتفاع مجاري الموقف (قمتها −0.50 م تحت بلاطة الدور الأرضي)، ومنسوب فتحة SMS FAG على جدار الشفت (2.05–2.25 م)، ومنسوب مجاري الممر (2.52 م) والسطح (0.60 م)، وأبعاد هياكل المراوح، وارتفاع الردّادات، ومقاسات الفروع على جانب الشفط (300×200 كجانب التعويض الموسوم).
- **ملاحظات للمالك:** (1) ترتيب مقاس الوسم «العرض×الارتفاع» مفترض؛ إن كان الارتفاع أولًا فالمجاري الرئيسية للموقف أخفض ارتفاعًا (حاليًا ارتفاعها حتى 1.30 م فيبقى صافي ≈ 1.90 م تحتها) — بانتظار تأكيدك. (2) ورقة السطح SM-104 ترسم مجرى هواء التعويض على طبقة اسمها `M_DR_WP` (تصريف)؛ اعتُبر مجرى لأن طرفيه يلامسان الصاعد والمروحة. (3) التعارضات الجديدة {العدد} (البلاطات غير مثقوبة عند الشفتات والصواعد؛ المناسيب افتراض).
```
### 9.2 `docs/HANDOFF_2026-10-08.md` — أضِف في الآخر
```markdown
## 9) إدارة الدخان (الدفعة 17، تعليمات `docs/CODEX_PROMPT_SMOKE_MANAGEMENT.md`)
- الملفات: `pipeline/smoke_extract.py` (يحتاج PDF) ← `pipeline/data/smoke.json` ← `pipeline/smoke_build.py` (المعرّفات `-SMnnnn`؛ تُستدعى من `post_model.py` بعد التهوية وقبل الدعم). الأنظمة `smk_cp_fa/ea` و`smk_co_fa/ea` في `lifecycle.py`، و`SMK_T` مضاف إلى `VENT_T`.
- **المتبقي بعد هذه الدفعة:** (ب) مياه الأمطار MECH2 ص27–31 وتصريف الموقع ص1/ص9 والري ص25–26 والمياه الباردة للموقع ص17 ومخطط صاعد المياه ص23؛ (ج) كهرباء الموقع ELEC1 ص8 وELEC2 ص27، الصواعق ELEC2 ص11–17، التأريض ص1، الهاتف ص28–34، وإضافات الإنذار والتيار الخفيف؛ (د) بقايا المبردة عند B/G/R ومضخات الإطفاء FF-105/FF-101؛ (هـ) تتمة التهوية (ردّاد العادم ورقم FAN-04 وفجوات المجاري)؛ (و) حاوية الدرج 3 وأبوابه A101 والغاز (قرار المالك).
```
### 9.3 `README.md`
في بند «اختبارات دورة الحياة» أضِف بعد «تهوية بشقيها الهواء النقي والشفط»: «وإدارة الدخان (تعويض الموقف وشفطه وتعويض الممرات وشفطها)»، وفي آخر البند غيّر `§8` إلى `§9`.

## 10. ممنوعات إضافية

- لا تُضِف أنواعًا أو عناصر غير مذكورة (ولا حساسات CO ولا ستائر دخان ولا ردّادات إضافية ولا مضخات ضغط).
- لا تعدّل `vent_build.py` ولا `vent_extract.py`.
- لا تحوّل القيم الافتراضية إلى «موثّقة» (لا تحذف `assumed`).
- لا تُشغّل `git add` ولا `git commit` ولا `git push`.
- لا تحذف الكاش ولا ملفات `/tmp` الخاصة بغيرك.

## 11. التقرير النهائي (بالعربية، بهذا الترتيب وبلا مقدمات)

1. **الحالة:** منجز كليًّا / منجز جزئيًّا (وما الذي لم يُنجَز ولماذا).
2. **الأرقام المتحقَّقة:** (أ) `smoke.json` يطابق الملحق أ؟ (ب) 209 عنصر؟ والأنواع والمستويات كما في 7.2؟ (ج) نتائج الأنظمة الأربعة (نهايات الاستهلاك الموصولة/الكلية والاختبارات الناجحة من الكلية)، (د) عدد الوصلات المرنة، (هـ) ثبات المعرّفات، (و) عدد الأوراق المستشهَد بها، (ز) التعارضات الجديدة (قبل/بعد)، (ح) نتيجة فحص JavaScriptCore، (ط) نتيجة الفحص المرئي للحجمين ومسارات اللقطات.
3. **الملفات المعدّلة والجديدة** (قائمة مسارات).
4. **ما انحرف عن هذا الملف** وسببه (إن وُجد، بما فيه تعديل `lib.py` للكاش).
5. **أسئلة المالك المعلّقة** (انسخها من 9.1 مع أي إضافة).

---

## ملحق أ — `pipeline/data/smoke.json` المرجعي (أرقام السنتيمتر؛ الحقلان `sheet` و`scale` يُهملان في المقارنة)

```json
{
  "B": {
    "sheet": "MECH1 p17",
    "scale": 3.753,
    "fa": {
      "shaft": [9.8, 3650.5, 149.9, 3750.4],
      "paths": [
        [[130.1, 4045.4], [80.1, 4045.4], [80.1, 3845.5]],
        [[299.9, 3697.7], [299.9, 3545.5], [80.1, 3545.5], [80.1, 2485.4], [625.0, 2485.4], [625.0, 1890.5], [2720.1, 1890.5], [2720.1, 390.3], [2770.1, 390.3]],
        [[130.1, 3385.2], [80.1, 3385.2]],
        [[130.1, 2985.3], [80.1, 2985.3]],
        [[130.1, 2585.4], [80.1, 2585.4]],
        [[2290.0, 1940.4], [2290.0, 1890.5]],
        [[2689.9, 1940.4], [2689.9, 1890.5]],
        [[2770.1, 1390.6], [2720.1, 1390.6]],
        [[2770.1, 890.2], [2720.1, 890.2]],
        [[1890.1, 1940.4], [1890.1, 1890.5]],
        [[1490.2, 1940.4], [1490.2, 1890.5]],
        [[1089.8, 1940.4], [1089.8, 1890.5]],
        [[689.9, 1940.4], [689.9, 1890.5]],
        [[83.2, 3697.7], [299.9, 3697.7], [299.9, 3845.5], [80.1, 3845.5]]
      ],
      "grilles": [
        {"x": 141.3, "y": 2585.4, "w": 24.3, "h": 81.1},
        {"x": 141.3, "y": 2985.3, "w": 24.3, "h": 81.1},
        {"x": 141.3, "y": 3385.2, "w": 24.3, "h": 81.1},
        {"x": 141.3, "y": 4045.4, "w": 24.3, "h": 81.1},
        {"x": 689.9, "y": 1951.9, "w": 81.1, "h": 23.9},
        {"x": 1089.8, "y": 1951.9, "w": 81.1, "h": 23.9},
        {"x": 1489.9, "y": 1951.9, "w": 80.6, "h": 23.9},
        {"x": 1890.1, "y": 1951.9, "w": 81.1, "h": 23.9},
        {"x": 2290.0, "y": 1951.9, "w": 81.1, "h": 23.9},
        {"x": 2689.9, "y": 1951.9, "w": 81.1, "h": 23.9},
        {"x": 2781.6, "y": 390.3, "w": 23.9, "h": 81.1},
        {"x": 2781.6, "y": 890.4, "w": 23.9, "h": 80.6},
        {"x": 2781.6, "y": 1390.6, "w": 23.9, "h": 81.1}
      ]
    },
    "ea": {
      "shaft": [4230.2, 3650.5, 4390.0, 3750.4],
      "paths": [
        [[2198.6, 3541.0], [2198.6, 3570.3]],
        [[2698.5, 3541.0], [2698.5, 3570.3]],
        [[3198.8, 3541.0], [3198.8, 3570.3]],
        [[3698.7, 3541.0], [3698.7, 3570.3]],
        [[4198.6, 3541.0], [4198.6, 3570.3]],
        [[4281.0, 3070.4], [4310.3, 3070.4]],
        [[4281.0, 2570.5], [4310.3, 2570.5]],
        [[4281.0, 2070.1], [4310.3, 2070.1]],
        [[3755.9, 1400.5], [3785.2, 1400.5]],
        [[4281.0, 970.4], [4310.3, 970.4]],
        [[4281.0, 570.4], [4310.3, 570.4]],
        [[4281.0, 70.5], [4310.3, 70.5], [4310.3, 1030.3], [3785.2, 1030.3], [3785.2, 1770.2], [4310.3, 1770.2], [4310.3, 3570.3], [1698.7, 3570.3], [1698.7, 3541.0]],
        [[4310.3, 3570.3], [4310.3, 3700.5]]
      ],
      "grilles": [
        {"x": 1698.7, "y": 3529.5, "w": 81.1, "h": 23.9},
        {"x": 2198.6, "y": 3529.5, "w": 81.1, "h": 23.9},
        {"x": 2698.5, "y": 3529.5, "w": 81.1, "h": 23.9},
        {"x": 3198.8, "y": 3529.5, "w": 81.1, "h": 23.9},
        {"x": 3698.7, "y": 3529.5, "w": 81.1, "h": 23.9},
        {"x": 3744.4, "y": 1400.5, "w": 23.9, "h": 81.1},
        {"x": 4198.6, "y": 3529.5, "w": 81.1, "h": 23.9},
        {"x": 4269.3, "y": 70.5, "w": 24.3, "h": 81.1},
        {"x": 4269.3, "y": 570.4, "w": 24.3, "h": 81.1},
        {"x": 4269.3, "y": 970.4, "w": 24.3, "h": 81.1},
        {"x": 4269.3, "y": 2070.4, "w": 24.3, "h": 80.6},
        {"x": 4269.3, "y": 2570.5, "w": 24.3, "h": 81.1},
        {"x": 4269.3, "y": 3070.4, "w": 24.3, "h": 81.1}
      ]
    },
    "vcd": [
      {"x": 135.3, "y": 4045.4, "w": 14.0, "h": 80.2},
      {"x": 1698.7, "y": 3535.6, "w": 80.2, "h": 13.5},
      {"x": 2198.6, "y": 3535.6, "w": 80.2, "h": 13.5},
      {"x": 2698.5, "y": 3535.6, "w": 80.2, "h": 13.5},
      {"x": 3198.6, "y": 3535.6, "w": 79.7, "h": 13.5},
      {"x": 3698.7, "y": 3535.6, "w": 80.2, "h": 13.5},
      {"x": 4198.6, "y": 3535.6, "w": 80.2, "h": 13.5},
      {"x": 4275.4, "y": 3070.4, "w": 14.0, "h": 80.2},
      {"x": 4275.4, "y": 2570.3, "w": 14.0, "h": 79.7},
      {"x": 4275.4, "y": 2070.4, "w": 14.0, "h": 79.7},
      {"x": 3750.3, "y": 1400.5, "w": 14.0, "h": 80.2},
      {"x": 4275.4, "y": 970.4, "w": 14.0, "h": 80.2},
      {"x": 4275.4, "y": 570.4, "w": 14.0, "h": 80.2},
      {"x": 4275.4, "y": 70.5, "w": 14.0, "h": 80.2},
      {"x": 135.3, "y": 3385.2, "w": 14.0, "h": 80.2},
      {"x": 135.3, "y": 2985.3, "w": 14.0, "h": 80.2},
      {"x": 135.3, "y": 2585.4, "w": 14.0, "h": 80.2},
      {"x": 2290.0, "y": 1945.8, "w": 80.2, "h": 13.5},
      {"x": 2689.9, "y": 1945.8, "w": 80.2, "h": 13.5},
      {"x": 2775.5, "y": 1390.3, "w": 13.5, "h": 79.7},
      {"x": 2775.5, "y": 890.4, "w": 13.5, "h": 79.7},
      {"x": 2775.5, "y": 390.3, "w": 13.5, "h": 80.2},
      {"x": 1890.1, "y": 1945.8, "w": 80.2, "h": 13.5},
      {"x": 1489.9, "y": 1945.8, "w": 79.7, "h": 13.5},
      {"x": 1089.8, "y": 1945.8, "w": 80.2, "h": 13.5},
      {"x": 689.9, "y": 1945.8, "w": 80.2, "h": 13.5}
    ],
    "fd": [
      {"x": 4311.4, "y": 3640.3, "w": 40.1, "h": 14.0},
      {"x": 205.7, "y": 3698.0, "w": 13.5, "h": 40.1}
    ],
    "fans": [
      [4283.3, 3582.0, 4336.9, 3618.5],
      [218.3, 3672.1, 254.8, 3726.1]
    ],
    "words": [
      {"t": "VCD", "x": 143.4, "y": 3973.2, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 1777.7, "y": 3526.4, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 2277.6, "y": 3526.4, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 2777.5, "y": 3526.4, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 3277.9, "y": 3526.4, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 3777.8, "y": 3526.4, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 4277.7, "y": 3526.4, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 4272.3, "y": 2990.5, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 4272.3, "y": 2490.6, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 4272.3, "y": 1990.2, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 3747.6, "y": 1320.5, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 4272.3, "y": 890.5, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 4272.3, "y": 490.5, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 4272.3, "y": -9.4, "layer": "M_VE_DAM"},
      {"t": "300x250", "x": 1966.5, "y": 3584.5, "layer": "M_EX_TEXT"},
      {"t": "400x375", "x": 2466.8, "y": 3584.5, "layer": "M_EX_TEXT"},
      {"t": "500x450", "x": 2966.3, "y": 3584.5, "layer": "M_EX_TEXT"},
      {"t": "500x1075", "x": 4341.1, "y": 3324.6, "layer": "M_EX_TEXT"},
      {"t": "500x900", "x": 4341.1, "y": 2817.1, "layer": "M_EX_TEXT"},
      {"t": "500x750", "x": 4341.1, "y": 2317.2, "layer": "M_EX_TEXT"},
      {"t": "500x600", "x": 4341.1, "y": 1864.6, "layer": "M_EX_TEXT"},
      {"t": "500x450", "x": 3750.7, "y": 1181.9, "layer": "M_EX_TEXT"},
      {"t": "400x375", "x": 4341.1, "y": 817.5, "layer": "M_EX_TEXT"},
      {"t": "300x250", "x": 4341.1, "y": 317.2, "layer": "M_EX_TEXT"},
      {"t": "VCD", "x": 143.4, "y": 3312.9, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 143.4, "y": 2913.0, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 143.4, "y": 2513.1, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 2382.6, "y": 1947.4, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 2782.5, "y": 1947.4, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 2783.9, "y": 1318.3, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 2783.9, "y": 817.9, "layer": "M_VE_DAM"},
      {"t": "VCD", "x": 2783.9, "y": 318.0, "layer": "M_VE_DAM"},
      {"t": "500x625", "x": 2201.1, "y": 1917.3, "layer": "M_FA_TEXT"},
      {"t": "500x500", "x": 2602.4, "y": 1917.3, "layer": "M_FA_TEXT"},
      {"t": "400x325", "x": 2698.7, "y": 1137.7, "layer": "M_FA_TEXT"},
      {"t": "300x200", "x": 2698.7, "y": 637.4, "layer": "M_FA_TEXT"},
      {"t": "FD", "x": 4355.8, "y": 3637.7, "layer": "M_HVAC_DAM"},
      {"t": "FD", "x": 202.6, "y": 3653.5, "layer": "M_HVAC_DAM"},
      {"t": "475x400", "x": 2698.7, "y": 1637.6, "layer": "M_FA_TEXT"},
      {"t": "500x775", "x": 1806.2, "y": 1917.3, "layer": "M_FA_TEXT"},
      {"t": "500x900", "x": 1399.5, "y": 1917.3, "layer": "M_FA_TEXT"},
      {"t": "500x1050", "x": 594.6, "y": 2140.6, "layer": "M_FA_TEXT"},
      {"t": "550x1200", "x": 58.2, "y": 2823.3, "layer": "M_FA_TEXT"},
      {"t": "550x1325", "x": 58.2, "y": 3242.2, "layer": "M_FA_TEXT"},
      {"t": "600x1300", "x": 54.2, "y": 3489.9, "layer": "M_FA_TEXT"},
      {"t": "300x200", "x": 2747.8, "y": 1137.3, "layer": "M_FA_TEXT"},
      {"t": "300x200", "x": 2747.8, "y": 1637.2, "layer": "M_FA_TEXT"},
      {"t": "300x200", "x": 107.8, "y": 2832.4, "layer": "M_FA_TEXT"},
      {"t": "300x200", "x": 107.8, "y": 3232.4, "layer": "M_FA_TEXT"},
      {"t": "300x200", "x": 103.3, "y": 3494.0, "layer": "M_FA_TEXT"},
      {"t": "300x200", "x": 2458.7, "y": 1917.3, "layer": "M_FA_TEXT"},
      {"t": "500x600", "x": 3300.4, "y": 3584.5, "layer": "M_EX_TEXT"},
      {"t": "1000x975", "x": 4094.3, "y": 3633.6, "layer": "M_EX_TEXT"},
      {"t": "300x200", "x": 2858.6, "y": 1917.3, "layer": "M_FA_TEXT"},
      {"t": "VCD", "x": 1982.7, "y": 1947.4, "layer": "M_VE_DAM"},
      {"t": "300x200", "x": 2058.8, "y": 1917.3, "layer": "M_FA_TEXT"},
      {"t": "VCD", "x": 1582.7, "y": 1947.4, "layer": "M_VE_DAM"},
      {"t": "300x200", "x": 1658.9, "y": 1917.3, "layer": "M_FA_TEXT"},
      {"t": "VCD", "x": 1182.4, "y": 1947.4, "layer": "M_VE_DAM"},
      {"t": "300x200", "x": 1258.5, "y": 1917.3, "layer": "M_FA_TEXT"},
      {"t": "VCD", "x": 782.5, "y": 1947.4, "layer": "M_VE_DAM"},
      {"t": "300x200", "x": 858.6, "y": 1917.3, "layer": "M_FA_TEXT"},
      {"t": "500x750", "x": 3944.9, "y": 3584.5, "layer": "M_EX_TEXT"},
      {"t": "300x200", "x": 58.2, "y": 3938.5, "layer": "M_FA_TEXT"}
    ]
  },
  "G": {
    "sheet": "MECH1 p18",
    "scale": 3.754,
    "fa": {"x": 79.9, "y": 3700.4, "w": 140.1, "h": 100.0},
    "ea": {"x": 4311.3, "y": 3700.4, "w": 159.9, "h": 100.0}
  },
  "1": {
    "sheet": "MECH1 p19",
    "scale": 1.876,
    "fa_riser": [
      {"x": 1327.5, "y": 1044.9, "w": 25.0, "h": 39.8}
    ],
    "ea_riser": [
      {"x": 1355.0, "y": 1039.9, "w": 20.0, "h": 29.9}
    ],
    "dampers": [
      {"x": 1027.9, "y": 899.9, "w": 13.7, "h": 29.9, "layer": "M_VE_DAM"},
      {"x": 2052.2, "y": 899.9, "w": 13.7, "h": 29.9, "layer": "M_VE_DAM"},
      {"x": 1327.4, "y": 1015.4, "w": 34.2, "h": 13.7, "layer": "M_HVAC_DAM"},
      {"x": 1354.5, "y": 1015.4, "w": 19.1, "h": 13.7, "layer": "M_VE_DAM"}
    ],
    "words": [
      {"t": "VCD", "x": 1027.4, "y": 922.4, "layer": "M_HVAC_DAM"},
      {"t": "VCD", "x": 2052.6, "y": 922.4, "layer": "M_HVAC_DAM"},
      {"t": "250x150", "x": 1619.1, "y": 910.9, "layer": "M_T.EX_TEXT"},
      {"t": "250x150", "x": 1185.0, "y": 910.9, "layer": "M_T.EX_TEXT"},
      {"t": "300x200", "x": 1364.2, "y": 956.6, "layer": "M_T.EX_TEXT"},
      {"t": "MFD", "x": 1295.1, "y": 1013.8, "layer": "M_HVAC_DAM"},
      {"t": "400x200", "x": 1235.9, "y": 936.6, "layer": "M_FA_TEXT"},
      {"t": "MFD", "x": 1380.2, "y": 1013.8, "layer": "M_HVAC_DAM"}
    ],
    "ea_branch": [
      [[1355.1, 1039.8], [1355.1, 900.0]]
    ],
    "ea_main": [
      [[997.1, 900.0], [2082.9, 900.0]]
    ],
    "ead": [
      {"x": 997.0, "y": 899.9, "w": 25.0, "h": 25.0, "layer": "M_T.EX_DIFF"},
      {"x": 2083.0, "y": 899.9, "w": 25.0, "h": 25.0, "layer": "M_T.EX_DIFF"}
    ],
    "fag_box": [
      {"x": 1327.5, "y": 998.8, "w": 34.0, "h": 2.3},
      {"x": 1327.5, "y": 1010.0, "w": 25.0, "h": 20.0}
    ]
  },
  "TY": {
    "sheet": "MECH1 p20",
    "scale": 1.877,
    "fa_riser": [
      {"x": 1327.2, "y": 1045.3, "w": 25.0, "h": 40.1}
    ],
    "ea_riser": [
      {"x": 1354.9, "y": 1040.3, "w": 20.0, "h": 30.2}
    ],
    "dampers": [
      {"x": 1027.4, "y": 900.3, "w": 13.7, "h": 30.0, "layer": "M_VE_DAM"},
      {"x": 2052.2, "y": 900.3, "w": 13.7, "h": 30.0, "layer": "M_VE_DAM"},
      {"x": 1327.0, "y": 1015.9, "w": 34.2, "h": 13.7, "layer": "M_HVAC_DAM"},
      {"x": 1354.3, "y": 1015.9, "w": 18.9, "h": 13.7, "layer": "M_VE_DAM"}
    ],
    "words": [
      {"t": "VCD", "x": 1026.9, "y": 922.9, "layer": "M_HVAC_DAM"},
      {"t": "VCD", "x": 2052.6, "y": 922.9, "layer": "M_HVAC_DAM"},
      {"t": "250x150", "x": 1618.9, "y": 911.1, "layer": "M_T.EX_TEXT"},
      {"t": "250x150", "x": 1184.6, "y": 911.1, "layer": "M_T.EX_TEXT"},
      {"t": "300x200", "x": 1364.1, "y": 956.9, "layer": "M_T.EX_TEXT"},
      {"t": "MFD", "x": 1295.0, "y": 1014.3, "layer": "M_HVAC_DAM"},
      {"t": "400x200", "x": 1235.5, "y": 937.0, "layer": "M_FA_TEXT"},
      {"t": "MFD", "x": 1379.9, "y": 1014.3, "layer": "M_HVAC_DAM"}
    ],
    "ea_branch": [
      [[1354.7, 1040.3], [1354.7, 900.2]]
    ],
    "ea_main": [
      [[996.6, 900.2], [2083.0, 900.2]]
    ],
    "ead": [
      {"x": 996.7, "y": 900.3, "w": 25.0, "h": 25.0, "layer": "M_T.EX_DIFF"},
      {"x": 2083.1, "y": 900.3, "w": 25.0, "h": 25.0, "layer": "M_T.EX_DIFF"}
    ],
    "fag_box": [
      {"x": 1327.3, "y": 999.1, "w": 33.8, "h": 2.3},
      {"x": 1327.2, "y": 1010.2, "w": 25.0, "h": 20.0}
    ]
  },
  "R": {
    "sheet": "MECH1 p21",
    "scale": 1.876,
    "fa_riser": [
      {"x": 1326.8, "y": 1044.8, "w": 25.0, "h": 40.1}
    ],
    "ea_riser": [
      {"x": 1354.2, "y": 1039.8, "w": 20.0, "h": 29.9}
    ],
    "dampers": [
      {"x": 1375.0, "y": 1041.2, "w": 13.7, "h": 40.1, "layer": "M_HVAC_DAM"},
      {"x": 1303.8, "y": 1046.2, "w": 13.7, "h": 40.1, "layer": "M_HVAC_DAM"}
    ],
    "words": [
      {"t": "MFD", "x": 1375.2, "y": 1068.1, "layer": "M_HVAC_DAM"},
      {"t": "MFD", "x": 1303.2, "y": 1073.1, "layer": "M_HVAC_DAM"}
    ],
    "fa_duct": [
      [[1326.9, 1044.8], [1126.8, 1044.8], [1126.8, 1138.0], [433.4, 1138.0]]
    ],
    "ea_duct": [
      [[1354.4, 1039.9], [1404.3, 1039.9], [1404.3, 1308.0], [758.7, 1308.0], [758.7, 1757.8], [408.6, 1757.8]]
    ],
    "fan_rects": [
      {"x": 374.6, "y": 1757.8, "w": 73.4, "h": 73.4, "layer": "AV-MAC"},
      {"x": 374.6, "y": 1757.9, "w": 68.0, "h": 68.2, "layer": "AV-MAC"},
      {"x": 388.0, "y": 1138.0, "w": 97.9, "h": 97.7, "layer": "AV-MAC"},
      {"x": 387.9, "y": 1138.0, "w": 90.9, "h": 90.9, "layer": "AV-MAC"}
    ],
    "fan_circles": [
      {"x": 374.8, "y": 1757.9, "w": 14.6, "h": 14.6, "layer": "AV-MAC"},
      {"x": 388.0, "y": 1138.1, "w": 19.6, "h": 19.6, "layer": "AV-MAC"}
    ],
    "louvers": {
      "ea": {"x0": 272.9, "y0": 1730.5, "x1": 294.5, "y1": 1784.8},
      "fa": {"x0": 279.9, "y0": 1109.9, "x1": 296.7, "y1": 1166.2}
    }
  }
}
```

## ملحق المراجعة — إصلاح الحوامل بعد التسليم

1. المخمّد أو الشبكة ذات `a.sys` داخل مجرى `M.duct` وعلى منسوبه تحملها شبكة المجرى في `pipeline/support.py`؛ لا تُنقل إلى الجدار القريب. شمل ذلك عناصر الدخان والتهوية السابقة.
2. السطح السفلي لشرائح بلاطة المنحدر `S.ramp` مضيف للمجاري المعلّقة تحته؛ زال تصنيف فرع شفط البدروم قرب س≈3698.7 كعنصر عائم.
3. ردّاد مروحة السطح يقف على أرضية السطح: `LOUVER_ROOF = (0.0, 1.20)`، وتحدّث نص `ASSUME_LOUVER_ROOF`. بعد ذلك صارت اختبارات الدخان الأربعة 5/5 لكل منها، وتتحقق بوابة `tools/check_network_relocation.py` من عدم نقل أي عنصر شبكة مرسوم.
