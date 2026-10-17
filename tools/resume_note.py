# -*- coding: utf-8 -*-
"""Update one row of the status table at the top of docs/RESUME_STATE.md:  python3 tools/resume_note.py "<row key>" "<status text>" [--after "<stamp>"]
Rows are lines starting with '| <key> |'; a missing key is appended to the table (before the first blank line after the table)."""
import sys, re, os
p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "RESUME_STATE.md")
key, text = sys.argv[1], sys.argv[2]
s = open(p, encoding="utf-8").read().split("\n")
rows = [i for i, l in enumerate(s) if l.startswith("| ") and not l.startswith("| #") and not l.startswith("|---")]
name, status = text.split("||", 1) if "||" in text else (key, text)
new = "| %s | %s | %s |" % (key, name.strip(), status.strip())
for i in rows:
    if s[i].split("|")[1].strip() == key:
        s[i] = new; break
else:
    s.insert(rows[-1] + 1, new)
for i, l in enumerate(s):
    if l.startswith("آخر تحديث:"):
        s[i] = "آخر تحديث: بعد البند " + key + ". الشجرة: work/checkpoint/C4-3D-MODEL. لا commit ولا push. نسخة احتياطية قبل كل شيء: ~/Documents/Claude/C4-archive/pre-cleanup-2026-10-17/tree.tar."
open(p, "w", encoding="utf-8").write("\n".join(s))
