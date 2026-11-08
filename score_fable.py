import json
from collections import Counter
from pathlib import Path

import scenarios_v2 as V

F = Path(__file__).resolve().parent / "fable"
idx = {r["tid"]: r for r in json.load(open(F / "main_index.json"))}
c = Counter()
for r in json.load(open(F / "main_results.json"))["results"]:
    if r["model"] != "fable":
        continue
    m = idx[r["tid"]]
    c[V.outcome(m["key"], m["version"], r["text"] or "")] += 1
n = sum(c.values())
print("fable-5.1 n", n, "A", round((c["decoy_named"] + c["decoy_unnamed"]) / n, 3), "FP", round(c["decoy_named"] / n, 3), dict(c))
