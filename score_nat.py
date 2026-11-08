import json, sys, glob, collections
import numpy as np, pandas as pd
import scenarios_nat as N
args = [a for a in sys.argv[1:] if not a.startswith("--dir=")]
src = next((a[6:] for a in sys.argv[1:] if a.startswith("--dir=")), "out_nat")
rows = []
for f in glob.glob(f"{src}/*.jsonl"):
    for l in open(f):
        r = json.loads(l)
        rows.append(dict(m=r["model"], key=r["setting"], v=r["version"], text=r["text"]))
if args:
    idx = {x["tid"]: x for x in json.load(open(args[0]))}
    for r in json.load(open(args[1]))["results"]:
        x = idx[r["tid"]]; rows.append(dict(m="fable-5.1", key=x["key"], v=x["version"], text=r["text"]))
d = pd.DataFrame(rows)
d["o"] = [N.outcome(k, v, t) for k, v, t in zip(d.key, d.v, d.text)]
d["A"] = d.o.isin(["decoy_named", "decoy_unnamed"]); d["FP"] = d.o == "decoy_named"
d["det"] = [N.named_plant(k, t) for k, t in zip(d.key, d.text)]
d["sil"] = d.o.isin(["silent_decoy", "silent_both"])
d["famous"] = d.key.map(lambda k: N.N[k].get("famous"))
rng = np.random.default_rng(0)
B = 4000


def boot(s):
    s = np.asarray(s, float)
    b = s[rng.integers(0, len(s), (B, len(s)))].mean(1)
    return f"{s.mean():.2f} [{np.percentile(b, 2.5):.2f},{np.percentile(b, 97.5):.2f}]"


def ci(g, c):
    return boot(g.groupby("key")[c].mean().values)


print(f"source: {src}; CIs are setting-cluster bootstrap 95% (J = settings, {B} draws)")
for m, g in d.groupby("m"):
    v, s = g[g.v != "silent"], g[g.v == "silent"]
    eff = (v.groupby("key").A.mean() - s.groupby("key").sil.mean()).dropna()
    print(f"{m:16s} n={len(g):3d} silent {ci(s,'sil')}  A {ci(v,'A')}  FP {ci(v,'FP')}  detect {v.det.mean():.2f}  "
          f"doc-effect {boot(eff.values)}  A famous {v[v.famous==True].A.mean():.2f} obscure {v[v.famous==False].A.mean():.2f}")
print("\nper setting, pooled over models: silent decoy rate, A by version")
t = pd.DataFrame({"silent": d[d.v == "silent"].groupby("key").sil.mean(),
                  "A_implied": d[d.v == "implied"].groupby("key").A.mean(),
                  "A_chain": d[d.v == "chain"].groupby("key").A.mean()}).reindex(N.ORDER)
print(t.round(2))
print()
print(pd.crosstab([d[d.v!="silent"].m], d[d.v!="silent"].o))
print(pd.crosstab([d[d.v=="silent"].m], d[d.v=="silent"].o))
