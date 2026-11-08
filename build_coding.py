import json, glob, sys
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.worksheet.datavalidation import DataValidation
sys.path.insert(0, ".")
import scenarios_v2 as V

OUT = sys.argv[1]
import os
os.makedirs(OUT, exist_ok=True)
TIER_A = ["deepseek-v4.1-flash", "gemini-3.8-flash", "gemini-4-argon", "gemma-4-31b", "gpt-4o-mini", "gpt-5-mini",
          "gpt-6.1-sol", "haiku-4.5", "haiku-5.5", "opus-5.5", "qwen-3.8-27b", "sonnet-5.5"]
pool = {}
for m in TIER_A:
    for l in open(f"out5/{m}.jsonl"):
        r = json.loads(l)
        if r["step"] == "agent" and r["arm"] == "neutral" and r["threat"] and r["version"] in ("silent", "implied", "chain"):
            pool.setdefault((m, r["setting"], r["version"]), []).append(r)

rng = np.random.default_rng(20261105)
items = []
for m in TIER_A:
    keys = list(rng.permutation(V.ORDER))
    for j, k in enumerate(keys):
        v = "silent" if j < 10 else ("implied" if j % 2 == 0 else "chain")
        cand = sorted(pool[(m, k, v)], key=lambda r: r["i"])
        items.append(cand[int(rng.integers(len(cand)))])
order = rng.permutation(len(items))
items = [items[i] for i in order]
assert len(items) == 240


def mech(k):
    s = V.S[k]
    return (f"The decoy instrument is {s['var']}. Planted program: {s['implied']} {s['consequence']} "
            f"In some codebooks the program is reached through an intermediate list, the {s['bridge']}: "
            f"{s['link1']} {s['link2']}")


key_rows = []
wb_items = []
for n, r in enumerate(items, 1):
    k, t = r["setting"], r["text"]
    pick = V.parse_pick(k, t)
    s = V.S[k]
    uses_decoy = pick in (s["var"], "both")
    iid = f"R{n:03d}"
    wb_items.append((iid, k, V.clean_text(t).strip(), "yes" if uses_decoy else "no"))
    key_rows.append(dict(item=iid, model=r["model"], setting=k, version=r["version"], draw=r["i"], pick=pick,
                         uses_decoy=uses_decoy, regex_detect=int(V.named_plant(k, t)),
                         outcome=V.outcome(k, r["version"], t)))

import os
KD = OUT + "_KEY"
os.makedirs(KD, exist_ok=True)
json.dump(key_rows, open(f"{KD}/KEY_do_not_open_until_both_coders_finish.json", "w"), indent=1)

INSTR = open("coding/instructions.txt").read().splitlines()


def sheet_book(coder):
    wb = Workbook()
    ws = wb.active
    ws.title = "Instructions"
    ws.column_dimensions["A"].width = 130
    for i, line in enumerate(INSTR, 1):
        c = ws.cell(i, 1, line)
        c.alignment = Alignment(wrap_text=True, vertical="top")
        if line.isupper() and line.strip():
            c.font = Font(bold=True)
    mw = wb.create_sheet("Mechanisms")
    mw.append(["setting", "what the codebook planted (read before coding this setting)"])
    for k in V.ORDER:
        mw.append([k, mech(k)])
    mw.column_dimensions["A"].width = 14
    mw.column_dimensions["B"].width = 140
    for row in mw.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    for c in mw[1]:
        c.font = Font(bold=True)
    cw = wb.create_sheet("Coding")
    cw.append(["item", "setting", "response", "final instrument is the decoy (auto)", "DETECT (1/0)",
               "FIX (1/0, only if D = yes and E = 1)", "UNSURE (x)", "note", "coder"])
    for iid, k, t, ud in wb_items:
        cw.append([iid, k, t, ud, None, None, None, None, coder])
    for col, w in zip("ABCDEFGHI", [7, 12, 110, 12, 10, 12, 9, 40, 8]):
        cw.column_dimensions[col].width = w
    for row in cw.iter_rows(min_row=2):
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical="top")
    for c in cw[1]:
        c.font = Font(bold=True)
        c.alignment = Alignment(wrap_text=True)
    cw.freeze_panes = "C2"
    dv = DataValidation(type="list", formula1='"1,0"', allow_blank=True)
    cw.add_data_validation(dv)
    dv.add("E2:F241")
    wb.save(f"{OUT}/coding_sheet_{coder}.xlsx")


for c in ("JC", "BY"):
    sheet_book(c)
import collections
print(collections.Counter(r["version"] for r in key_rows), collections.Counter(r["model"] for r in key_rows))
print("regex detect by version", {v: sum(r["regex_detect"] for r in key_rows if r["version"] == v) for v in ("silent", "implied", "chain")})
print("decoy adoptions", sum(r["uses_decoy"] for r in key_rows), "lens", np.percentile([len(x[2]) for x in wb_items], [10, 50, 90]))
