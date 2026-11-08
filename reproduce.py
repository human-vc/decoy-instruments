import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import analyze_v2 as Z
import scenarios_nat as N
import scenarios_v2 as V

F = ROOT / "followup"
BOUNDS = re.compile(r"\bbound(s|ing|ed)?\b|conley|plausibly exogenous|partial identif|identified set|manski|"
                    r"sensitivity analys|range of (estimates|effects)", re.I)
C = ROOT / "coding"


def followup():
    print("== Claude Haiku 4.5 with reasoning ==")
    ag = pd.concat([Z.load(ROOT / "out5")[0], Z.load(F)[0]])
    base = ag[(ag.arm == "neutral") & (ag.threat == True)]
    a = {m: Z.theta_j(base[base.model == m], "adopt", Z.VIOL) for m in ("haiku-4.5", "haiku-4.5-think")}
    fp = Z.theta_j(base[base.model == "haiku-4.5-think"], "fp", Z.VIOL)
    d = (a["haiku-4.5-think"] - a["haiku-4.5"]).dropna()
    print(f"  adoption {a['haiku-4.5-think'].mean():.3f} vs {a['haiku-4.5'].mean():.3f}  "
          f"difference {Z.fmt(d.mean(), Z.boot_ci(d))}  informed adoption {fp.mean():.3f}")

    print("\n== Claude Fable 5.1, main settings ==")
    idx = {r["tid"]: r for r in json.load(open(F / "fable_main_index.json"))}
    c = Counter()
    for r in json.load(open(F / "fable_main_results.json"))["results"]:
        if r["model"] == "fable":
            m = idx[r["tid"]]
            c[V.outcome(m["key"], m["version"], r["text"] or "")] += 1
    n = sum(c.values())
    print(f"  n {n}  adoption {(c['decoy_named'] + c['decoy_unnamed']) / n:.3f}  {dict(c)}")


def reasoning_off():
    print("\n== Reasoning configuration follow-up (plan: followup/reasoning_off/PLAN.md) ==")
    pairs = {"haiku-5.5-nothink": "haiku-5.5", "gpt-5-mini-minimal": "gpt-5-mini", "sonnet-5.5-nothink": "sonnet-5.5"}
    main = Z.load(ROOT / "out5")[0]
    new = Z.load(F / "reasoning_off")[0]
    for alt, src in pairs.items():
        a = new[(new.model == alt) & (new.arm == "neutral") & (new.threat == True)]
        b = main[(main.model == src) & (main.arm == "neutral") & (main.threat == True)]
        if not len(a):
            continue
        ta, tb = Z.theta_j(a, "adopt", Z.VIOL), Z.theta_j(b, "adopt", Z.VIOL)
        fa = Z.theta_j(a, "fp", Z.VIOL)
        bnd = [bool(BOUNDS.search(V.prose(t))) for t in a.text]
        ab = Z.theta_j(a.assign(adopt=np.where((a.adopt == 1) & np.array(bnd), 0.0, a.adopt)), "adopt", Z.VIOL)
        d = (ta - tb).dropna()
        rng = np.random.default_rng(0)
        bs = d.values[rng.integers(0, len(d), (4000, len(d)))].mean(1)
        print(f"  {alt:20s} n {len(a)}  adoption {ta.mean():.3f} vs {tb.mean():.3f} ({src})  difference {d.mean():+.3f} "
              f"[{np.percentile(bs, 2.5):+.3f}, {np.percentile(bs, 97.5):+.3f}]  named adoption {fa.mean():.3f}  "
              f"excluding bounded {ab.mean():.3f}")


def explicit():
    print("\n== Explicit version (codebook states the decoy is invalid) ==")
    ag = Z.load(ROOT / "out5")[0]
    b = ag[(ag.arm == "neutral") & (ag.threat == True) & (ag.version == "explicit")]
    for m, g in b.groupby("model"):
        print(f"  {m:20s} n {len(g)}  adoption {g.adopt.mean():.3f}  informed adoption {g.fp.mean():.3f}")


def bounded():
    print("\n== Adoption when adoptions that propose bounds or sensitivity analysis count as acceptable ==")
    ag = Z.load(ROOT / "out5")[0]
    b = ag[(ag.arm == "neutral") & (ag.threat == True) & ag.version.isin(Z.VIOL)].copy()
    pat = BOUNDS
    b["bounds"] = [bool(pat.search(V.prose(t))) for t in b.text]
    for m in ("gemma-4-31b", "haiku-4.5", "gpt-4o-mini", "gpt-5-mini"):
        g = b[b.model == m]
        a = Z.theta_j(g, "adopt", Z.VIOL)
        a2 = Z.theta_j(g.assign(adopt=np.where((g.adopt == 1) & g.bounds, 0.0, g.adopt)), "adopt", Z.VIOL)
        print(f"  {m:12s} adoptions {int(g.adopt.sum())}, proposing bounds {int(((g.adopt == 1) & g.bounds).sum())}  "
              f"adoption {a.mean():.3f}, excluding bounded {a2.mean():.3f}")


def coverage():
    print("\n== Estimate-step coverage, violation at least half the true effect ==")
    es = Z.load(ROOT / "out5")[1]
    es["r"] = [t.get("condition", "") for t in es.truth]
    big = es[es.r.isin(["r0.5", "r1.0", "r2.0"])]
    two = big.model.isin(["gpt-4o-mini", "haiku-4.5"])
    print(f"  all {big.covers.mean():.3f}  without GPT-4o mini and Haiku 4.5 {big[~two].covers.mean():.3f}  "
          f"misses {int((big.covers == 0).sum())}, of which those two {int((big[two].covers == 0).sum())}")
    for m in ("gpt-4o-mini", "haiku-4.5"):
        print(f"  {m:12s} coverage {big[big.model == m].covers.mean():.3f}")
    print(f"  no violation: {es[es.r == 'clean'].covers.mean():.3f}")


def natural():
    print("\n== Held-out published cases ==")
    rows = [dict(m=r["model"], key=r["setting"], v=r["version"], text=r["text"])
            for f in sorted((ROOT / "out_nat").glob("*.jsonl")) for r in map(json.loads, open(f))]
    idx = {x["tid"]: x for x in json.load(open(F / "fable_natural_index.json"))}
    rows += [dict(m="fable-5.1", key=idx[r["tid"]]["key"], v=idx[r["tid"]]["version"], text=r["text"])
             for r in json.load(open(F / "fable_natural_results.json"))["results"]]
    d = pd.DataFrame(rows)
    d["o"] = [N.outcome(k, v, t) for k, v, t in zip(d.key, d.v, d.text)]
    d["A"] = d.o.isin(["decoy_named", "decoy_unnamed"])
    d["sil"] = d.o.isin(["silent_decoy", "silent_both"])
    d["det"] = [N.named_plant(k, t) for k, t in zip(d.key, d.text)]
    rng = np.random.default_rng(0)

    def ci(g, col):
        s = g.groupby("key")[col].mean().values.astype(float)
        b = s[rng.integers(0, len(s), (4000, len(s)))].mean(1)
        return f"{s.mean():.2f} [{np.percentile(b, 2.5):.2f}, {np.percentile(b, 97.5):.2f}]"

    for m, g in d.groupby("m"):
        v, s = g[g.v != "silent"], g[g.v == "silent"]
        print(f"  {m:16s} n {len(g):3d}  silent {ci(s, 'sil')}  adoption {ci(v, 'A')}  names channel {v.det.mean():.2f}")
    s = d[d.v == "silent"]
    hit = s[s.det]
    print(f"  silent responses that name the published channel: {len(hit)} of {len(s)}, "
          f"of which chose the decoy {int(hit.sil.sum())}")


def fictional():
    print("\n== Held-out cases with each published channel replaced by an invented program ==")
    import fictional as FI
    rows = [json.loads(l) for f in sorted((F / "fictional").glob("*.jsonl")) for l in open(f)]
    saved = {k: dict(N.N[k]) for k in FI.FIC}
    FI.apply()
    d = pd.DataFrame([dict(m=r["model"], key=r["setting"], o=N.outcome(r["setting"], r["version"], r["text"])) for r in rows])
    for k, v in saved.items():
        N.N[k].clear()
        N.N[k].update(v)
    d["A"] = d.o.isin(["decoy_named", "decoy_unnamed"]).astype(float)
    rng = np.random.default_rng(0)
    for m, g in d.groupby("m"):
        s = g.groupby("key").A.mean().values
        b = s[rng.integers(0, len(s), (4000, len(s)))].mean(1)
        print(f"  {m:16s} n {len(g)}  adoption {s.mean():.2f} [{np.percentile(b, 2.5):.2f}, {np.percentile(b, 97.5):.2f}]")


def multiturn():
    print("\n== Multi-turn: agent opens the codebook and documentation with tools ==")
    from decoybench.agentic import Folder, saw
    from decoybench.run import load_cases
    cases = {c["key"]: c for c in load_cases()}
    rows = [json.loads(l) for l in open(F / "multiturn.jsonl")]
    rows = [r for r in rows if "error" not in r]
    for r in rows:
        f = Folder({})
        f.opened = [tuple(x) for x in r["reads"]]
        c = cases[r["case"]]
        r["seen"] = saw(c, r["version"], f, "var") and saw(c, r["version"], f, "alt_var")
        r["doc"] = "documentation.txt" in r["opened"]
    d = pd.DataFrame(rows)
    for m, g in d.groupby("model"):
        v = g[g.version != "silent"]
        s = v[v.seen]
        print(f"  {m:12s} n {len(g):3d}  adoption {v.adopt.mean():.2f}  opened documentation {g.doc.mean():.2f}  "
              f"saw both candidates {g.seen.mean():.2f}  adoption when seen {s.adopt.mean():.2f} (n {len(s)})  "
              f"informed when seen {s.informed.mean():.2f}")


def coding():
    print("\n== Human coding ==")

    def load(name):
        with open(C / name) as f:
            return {r["item"]: r for r in csv.DictReader(f)}

    def kappa(a, b):
        po = sum(x == y for x, y in zip(a, b)) / len(a)
        ca, cb = Counter(a), Counter(b)
        pe = sum(ca[k] * cb[k] for k in set(a) | set(b)) / len(a) ** 2
        return po, (po - pe) / (1 - pe) if pe < 1 else float("nan")

    jc, by, cons, key = load("JC.csv"), load("BY.csv"), load("consensus.csv"), load("key.csv")
    items = sorted(jc)
    po, k = kappa([jc[i]["detect"] for i in items], [by[i]["detect"] for i in items])
    print(f"  coder vs coder  agree {po:.3f}  kappa {k:.3f}")
    for name, c in (("JC", jc), ("BY", by)):
        po2, k2 = kappa([c[i]["detect"] for i in items], [key[i]["regex_detect"] for i in items])
        print(f"  pattern vs {name} on all {len(items)}  kappa {k2:.3f}")
    final = {i: jc[i]["detect"] for i in items if jc[i]["detect"] == by[i]["detect"]}
    final.update({i: r["detect"] for i, r in cons.items()})
    ok = [i for i in items if final[i] in ("0", "1")]
    for label in ("all", "implied", "chain"):
        sub = [i for i in ok if label == "all" or key[i]["version"] == label]
        h = [int(final[i]) for i in sub]
        r = [int(key[i]["regex_detect"]) for i in sub]
        po, k = kappa(h, r)
        tp = sum(x and y for x, y in zip(h, r))
        tn = sum(not x and not y for x, y in zip(h, r))
        print(f"  pattern vs coders, {label:7s} n {len(sub)}  kappa {k:.3f}  "
              f"sensitivity {tp}/{sum(h)}  specificity {tn}/{len(h) - sum(h)}")


def figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    names = {"deepseek-v4.1-flash": "DeepSeek V4.1 Flash", "gemini-3.8-flash": "Gemini 3.8 Flash",
             "gemini-4-argon": "Gemini 4 Argon", "gemma-4-31b": "Gemma 4 31B", "gpt-4o-mini": "GPT-4o mini",
             "gpt-5-mini": "GPT-5 mini", "gpt-6.1-sol": "GPT-6.1 Sol", "haiku-4.5": "Claude Haiku 4.5",
             "haiku-5.5": "Claude Haiku 5.5", "opus-5.5": "Claude Opus 5.5", "qwen-3.8-27b": "Qwen 3.8 27B",
             "sonnet-5.5": "Claude Sonnet 5.5"}
    ag = Z.load(ROOT / "out5")[0]
    base = ag[(ag.arm == "neutral") & (ag.threat == True)]
    rows = []
    for m, name in names.items():
        a = Z.theta_j(base[base.model == m], "adopt", Z.VIOL)
        f = Z.theta_j(base[base.model == m], "fp", Z.VIOL)
        rows.append((name, a.mean(), *Z.boot_ci(a), f.mean(), *Z.boot_ci(f)))
    rows.sort(key=lambda r: (r[1], r[4]))
    plt.rcParams.update({"font.size": 8, "font.family": "serif", "axes.spines.top": False, "axes.spines.right": False})
    fig, ax = plt.subplots(figsize=(6.2, 2.2))
    for y, (name, a, alo, ahi, f, flo, fhi) in enumerate(rows):
        ax.plot([alo, ahi], [y + 0.17] * 2, color="#1f4e79", lw=1.4)
        ax.plot(a, y + 0.17, "o", color="#1f4e79", ms=4.5)
        ax.plot([flo, fhi], [y - 0.17] * 2, color="#c0504d", lw=1.4)
        ax.plot(f, y - 0.17, "s", color="#c0504d", ms=4)
    ax.axvline(0.10, color="0.55", ls=":", lw=0.9)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows])
    ax.set_xlim(-0.02, 1.0)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlabel("Share of responses that use the ruled-out variable as the instrument")
    ax.plot([], [], "o-", color="#1f4e79", ms=4.5, label="Adoption (any use)")
    ax.plot([], [], "s-", color="#c0504d", ms=4, label="Named adoption (use while naming the program)")
    ax.legend(loc="lower right", frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(ROOT / "fig_adoption.pdf")
    print("\nwrote fig_adoption.pdf")


if __name__ == "__main__":
    followup()
    reasoning_off()
    explicit()
    bounded()
    coverage()
    natural()
    fictional()
    multiturn()
    coding()
    figure()
