import csv
from collections import Counter
from pathlib import Path

C = Path(__file__).resolve().parent / "coding"


def load(name):
    with open(C / name) as f:
        return {r["item"]: r for r in csv.DictReader(f)}


def kappa(a, b):
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / n ** 2
    return po, (po - pe) / (1 - pe) if pe < 1 else float("nan")


def show(label, a, b):
    po, k = kappa(a, b)
    print(f"{label:34s} n={len(a):3d}  agree {po:.3f}  kappa {k:.3f}  PABAK {2 * po - 1:.3f}")
    return k


jc, by, cons, key = load("JC.csv"), load("BY.csv"), load("consensus.csv"), load("key.csv")
items = sorted(jc)
show("DETECT, JC vs BY", [jc[i]["detect"] for i in items], [by[i]["detect"] for i in items])
both = [i for i in items if jc[i]["fix"] and by[i]["fix"]]
show("FIX, JC vs BY", [jc[i]["fix"] for i in both], [by[i]["fix"] for i in both])

final = {i: jc[i]["detect"] for i in items if jc[i]["detect"] == by[i]["detect"]}
final.update({i: r["detect"] for i, r in cons.items()})
ok = [i for i in items if final[i] in ("0", "1")]
print(f"\nAMBIG dropped: {len(items) - len(ok)}")
for label in ("all", "silent", "implied", "chain"):
    sub = [i for i in ok if label == "all" or key[i]["version"] == label]
    h = [int(final[i]) for i in sub]
    r = [int(key[i]["regex_detect"]) for i in sub]
    k = show(f"regex vs consensus, {label}", h, r)
    tp = sum(x and y for x, y in zip(h, r))
    print(f"{'':34s} sensitivity {tp}/{sum(h)}  specificity {sum(not x and not y for x, y in zip(h, r))}/{len(h) - sum(h)}")
    if label == "all":
        kall = k
print(f"\nmisses: {[i for i in ok if int(final[i]) != int(key[i]['regex_detect'])]}")
print(f"kappa {kall:.3f} vs 0.70 -> {'informed adoption confirmatory' if kall >= 0.70 else 'informed adoption exploratory'}")
