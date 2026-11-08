import gzip
import json
from pathlib import Path

import scenarios_nat as N
import scenarios_v2 as V

VERSIONS = ("silent", "implied", "chain")


def case(mod, key, source):
    s = mod.N[key] if mod is N else V.S[key]
    return dict(key=key, source=source, var=s["var"], alt_var=s["alt_var"], plant_re=s["plant_re"],
                prompts={v: "".join(mod.agent_parts(key, v)) for v in VERSIONS})


cases = [case(V, k, "main") for k in V.ORDER] + [case(N, k, "published") for k in N.ORDER]
out = Path(__file__).resolve().parent / "decoybench" / "cases.json.gz"
with gzip.open(out, "wt") as f:
    json.dump(cases, f)
print(len(cases), "cases written to", out)
