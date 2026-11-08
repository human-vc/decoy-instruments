import json, glob, re, sys
sys.path.insert(0, ".")
import scenarios_nat as N
hits = []
for f in sorted(glob.glob("out_nat/*.jsonl")):
    for l in open(f):
        r = json.loads(l)
        if r["version"] != "silent": continue
        if N.named_plant(r["setting"], r["text"]):
            hits.append(r)
print(len(hits))
import collections
print(collections.Counter((h["model"], h["setting"]) for h in hits))
out = []
for h in hits:
    t = h["text"]; pat = N.N[h["setting"]]["plant_re"]
    snips = []
    for m in re.finditer(pat, t, re.I):
        a, b = max(0, m.start()-220), min(len(t), m.end()+220)
        snips.append(t[a:b].replace("\n", " "))
    out.append(dict(model=h["model"], setting=h["setting"], o=N.outcome(h["setting"], "silent", t), snips=snips[:3]))
json.dump(out, open("silent_hits.json", "w"), indent=1)
