import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LONG_SCALE, EST_SCALE, REC_SCALE = 1.007, 1.215, 1.154
PREFIX_SHARE = 0.61
TAIL = 200

PRICE = {
    "opus-5.5": dict(i=4.00, w5=5.00, w60=8.00, r=0.20, o=20.0, batch=0.5, cache="explicit"),
    "sonnet-5.5": dict(i=2.00, w5=2.50, w60=4.00, r=0.10, o=10.0, batch=0.5, cache="explicit"),
    "haiku-5.5": dict(i=0.10, w5=0.125, w60=0.20, r=0.01, o=0.50, batch=0.5, cache="explicit"),
    "haiku-4.5": dict(i=1.00, w5=1.25, w60=2.00, r=0.10, o=5.00, batch=0.5, cache="explicit"),
    "gpt-6.1-sol": dict(i=2.00, w5=2.50, w60=2.50, r=0.10, o=10.0, batch=0.5, cache="auto"),
    "gpt-5-mini": dict(i=0.25, w5=0.25, w60=0.25, r=0.025, o=2.00, batch=0.5, cache="auto"),
    "gpt-4o-mini": dict(i=0.15, w5=0.15, w60=0.15, r=0.075, o=0.60, batch=0.5, cache="auto_nobatchcache"),
    "gemini-4-argon": dict(i=2.00, w5=2.00, w60=2.00, r=0.10, o=10.0, batch=0.5, cache="implicit"),
    "gemini-3.8-flash": dict(i=0.75, w5=0.75, w60=0.75, r=0.075, o=3.75, batch=0.5, cache="implicit"),
    "gemma-4-31b": dict(i=0.20, w5=0.20, w60=0.20, r=0.20, o=0.40, batch=1.0, cache="none"),
    "qwen-3.8-27b": dict(i=0.15, w5=0.15, w60=0.15, r=0.0375, o=1.875, batch=1.0, cache="implicit"),
    "deepseek-v4.1-flash": dict(i=0.045, w5=0.045, w60=0.045, r=0.018, o=0.50, batch=1.0, cache="implicit"),
}
OPENROUTER_FEE = {"gemini-4-argon", "gemini-3.8-flash", "gemma-4-31b", "qwen-3.8-27b", "deepseek-v4.1-flash"}

MEASURED = {
    "opus-5.5": "claude-opus-5-5", "haiku-5.5": "claude-haiku-5-5", "gpt-6.1-sol": "gpt-6.1-sol",
    "gpt-5-mini": "gpt-5-mini", "gemini-4-argon": "google_gemini-4-argon", "gemma-4-31b": "google_gemma-4-31b-it",
}
ANALOG_OUT = {
    "sonnet-5.5": dict(long=1740, estimate=1390, recall=870, src="usage_probe: 1.77x Opus long, 1.42x Opus short"),
    "haiku-4.5": dict(long=350, estimate=300, recall=250, src="assumed: no thinking by default"),
    "gpt-4o-mini": dict(long=300, estimate=250, recall=200, src="assumed: no reasoning"),
    "gemini-3.8-flash": dict(long=600, estimate=400, recall=250, src="assumed: Argon plus 15 percent"),
    "qwen-3.8-27b": dict(long=1500, estimate=1200, recall=900, src="assumed: thinking on, UNVERIFIED"),
    "deepseek-v4.1-flash": dict(long=1200, estimate=1000, recall=700, src="assumed: reasoning on, UNVERIFIED"),
}
IN_TOKENS = {"anthropic": dict(long=27400, estimate=940, recall=615), "other": dict(long=18800, estimate=650, recall=420)}
FAMILY = {m: ("anthropic" if m.split("-")[0] in ("opus", "sonnet", "haiku") else "other") for m in PRICE}

FRONTIER = ["opus-5.5", "sonnet-5.5", "gpt-6.1-sol", "gemini-4-argon"]
OTHER = ["gpt-5-mini", "haiku-5.5", "gemma-4-31b", "qwen-3.8-27b", "deepseek-v4.1-flash", "gpt-4o-mini", "haiku-4.5",
         "gemini-3.8-flash"]
J, J_REC, J_BOUNDS, J_MONO = 20, 18, 19, 3


def measured_out():
    out = {}
    for short, stem in MEASURED.items():
        f = ROOT / "out4" / f"{stem}.jsonl"
        acc = {}
        for line in f.open():
            r = json.loads(line)
            step = r["key"].split("|")[0]
            step = "long" if step in ("agent", "pressure") else step
            acc.setdefault(step, []).append(r["usage"]["out"])
        out[short] = {k: sum(v) / len(v) for k, v in acc.items()}
    out["gemma-4-31b"].update(estimate=220, recall=180)
    return out


ARMS = ["gpt-5-mini", "haiku-5.5", "gemma-4-31b", "deepseek-v4.1-flash", "gpt-4o-mini"]
MONO = ["opus-5.5", "gpt-6.1-sol", "gpt-5-mini", "haiku-5.5", "gemma-4-31b", "deepseek-v4.1-flash"]
RECALL = ["gpt-6.1-sol", "gemini-4-argon", "gpt-5-mini", "haiku-5.5"]


def plan(model, tier):
    if model == "sonnet-5.5" and tier == "A":
        return None
    if model in FRONTIER:
        k = 2 if tier == "B" else 1
        per = dict(silent=1, implied=k + 1, chain=k + 2)
        est = J + (4 if tier == "B" else 2) * J + J_BOUNDS
    else:
        arms = tier == "B" or model in ARMS
        per = dict(silent=1, implied=3 + (2 if arms else 0), chain=3 + (4 if arms else 0))
        if arms:
            per.update(explicit=2, near=2, hop2=2)
        est = J + 4 * J + J_BOUNDS
    mono = 2 if model in MONO else 0
    recall = J_REC * 4 if model in RECALL else 0
    return per, mono, est, recall


def cost(model, mode, outs, hit=0.6, tier="A"):
    pl = plan(model, tier)
    if pl is None:
        return 0.0, 0, 0
    per, mono, est, recall = pl
    p = PRICE[model]
    fam = IN_TOKENS[FAMILY[model]]
    o = outs.get(model) or ANALOG_OUT[model]
    L = fam["long"] * LONG_SCALE
    P, M = L * PREFIX_SHARE, L * (1 - PREFIX_SHARE) - TAIL
    batch = p["batch"] if mode == "batch" else 1.0
    cache_ok = mode != "nocache" and p["cache"] != "none" and not (mode == "batch" and p["cache"] in ("implicit", "auto_nobatchcache"))
    w = p["w60"] if mode == "batch" else p["w5"]
    h = hit if mode == "batch" else 0.85
    if p["cache"] == "implicit" and mode != "batch":
        h, w = 0.25, p["i"]
    rd = h * p["r"] + (1 - h) * p["i"]
    n_long = J * sum(per.values()) + J_MONO * mono
    if not cache_ok:
        long_in = n_long * L * p["i"]
    else:
        per_setting = P * w + (sum(per.values()) - 1) * P * rd
        for v, c in per.items():
            if c >= 3:
                per_setting += M * w + (c - 1) * M * rd + c * TAIL * p["i"]
            else:
                per_setting += c * (M + TAIL) * p["i"]
        long_in = J * per_setting + J_MONO * mono * L * p["i"]
    long_out = n_long * o["long"] * p["o"]
    short_in = (est * fam["estimate"] * EST_SCALE + recall * fam["recall"] * REC_SCALE) * p["i"]
    short_out = (est * o["estimate"] + recall * o.get("recall", o["estimate"])) * p["o"]
    total = (long_in + long_out + short_in + short_out) / 1e6 * batch
    if model in OPENROUTER_FEE:
        total *= 1.055
    return total, n_long, est + recall


def manifest(tier="A"):
    sys_path = str(ROOT)
    import sys
    if sys_path not in sys.path:
        sys.path.insert(0, sys_path)
    import scenarios_v2 as V
    import estimate_v2 as E
    rows = []
    for m in FRONTIER + OTHER:
        pl = plan(m, tier)
        if pl is None:
            continue
        frontier = m in FRONTIER
        k = 2 if tier == "B" else 1
        for key in V.ORDER:
            rows.append((m, "agent", key, "silent", "neutral", True, 0))
            kk = k if frontier else 3
            for v in ("implied", "chain"):
                rows += [(m, "agent", key, v, "neutral", True, i) for i in range(kk)]
            if frontier:
                rows += [(m, "agent", key, v, "pressure", True, 0) for v in ("implied", "chain")]
                rows.append((m, "agent", key, "chain", "neutral", False, 0))
            elif tier == "B" or m in ARMS:
                rows += [(m, "agent", key, "chain", "honesty", True, i) for i in range(2)]
                rows += [(m, "agent", key, v, "neutral", False, i) for v in ("implied", "chain") for i in range(2)]
                rows += [(m, "agent", key, v, "neutral", True, i) for v in ("explicit", "near", "hop2") for i in range(2)]
            full = (not frontier) or tier == "B"
            rows += [(m, "estimate", key, c, "-", True, 0) for c in E.conditions_for(key, full)]
            if m in RECALL and V.S[key]["named_ok"]:
                rows += [(m, "recall", key, v, nm, True, 0) for v in ("silent", "implied") for nm in ("masked", "named")]
        if m in MONO:
            rows += [(m, "agent", key, "mono", "neutral", True, i) for key in V.LENIENCY for i in range(2)]
    return rows


def check_manifest(tier="A"):
    rows = manifest(tier)
    for m in FRONTIER + OTHER:
        pl = plan(m, tier)
        if pl is None:
            assert not any(r[0] == m for r in rows)
            continue
        per, mono, est, recall = pl
        n_long = sum(1 for r in rows if r[0] == m and r[1] == "agent")
        assert n_long == J * sum(per.values()) + J_MONO * mono, (m, n_long)
        n_est = sum(1 for r in rows if r[0] == m and r[1] == "estimate")
        assert n_est == est, (m, n_est, est)
        assert sum(1 for r in rows if r[0] == m and r[1] == "recall") == recall, m
    assert len(rows) == len(set(rows))
    return len(rows)


def main():
    outs = measured_out()
    print("measured mean output tokens per call (out4):")
    for m, d in outs.items():
        print(f"  {m:20s} " + "  ".join(f"{k}={v:.0f}" for k, v in sorted(d.items())))
    print("assumed output tokens for models without round-3 data:")
    for m, d in ANALOG_OUT.items():
        print(f"  {m:20s} long={d['long']} estimate={d['estimate']} ({d['src']})")
    for tier in ("A", "B"):
        print(f"\n== tier {tier}: {check_manifest(tier)} calls in the manifest, counts match the cost plan ==")
        print(f"{'model':22s}{'long':>6s}{'short':>7s}{'sync, no cache':>16s}{'sync + cache':>14s}{'batch/flex + cache':>20s}")
        tot = [0, 0, 0]
        for m in FRONTIER + OTHER:
            a, nl, ns = cost(m, "nocache", outs, tier=tier)
            b, _, _ = cost(m, "sync", outs, tier=tier)
            c, _, _ = cost(m, "batch", outs, tier=tier)
            tot = [tot[0] + a, tot[1] + b, tot[2] + c]
            print(f"{m:22s}{nl:6d}{ns:7d}{a:16.2f}{b:14.2f}{c:20.2f}")
        print(f"{'TOTAL':22s}{'':13s}{tot[0]:16.2f}{tot[1]:14.2f}{tot[2]:20.2f}")
        lo = sum(cost(m, "batch", outs, hit=0.3, tier=tier)[0] for m in FRONTIER + OTHER)
        hi = sum(cost(m, "batch", outs, hit=0.98, tier=tier)[0] for m in FRONTIER + OTHER)
        print(f"batch total across the documented Anthropic batch cache-hit range (98% to 30%): {hi:.2f} to {lo:.2f}")
        g = cost("gemini-4-argon", "batch", outs, tier=tier)[0] + cost("gemini-3.8-flash", "batch", outs, tier=tier)[0]
        print(f"Gemini share of the batch total: {g:.2f}; adds about {g:.2f} if run after the 2026-12-01 / 2027-01-01 price doublings")


if __name__ == "__main__":
    main()
