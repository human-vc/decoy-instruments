import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import scenarios_v2 as V
import estimate_v2 as E
import cost_v2 as C

B_BOOT = 10_000
RNG = np.random.default_rng(20261106)
VIOL = ["implied", "chain"]
DOSE = {"explicit": -2, "implied": -1, "near": 0, "chain": 1, "hop2": 2}
R_LEVELS = {"clean": 0.0, "r0.1": 0.1, "r0.5": 0.5, "r1.0": 1.0, "r2.0": 2.0}
DEVELOPER = {"opus": "anthropic", "sonnet": "anthropic", "haiku": "anthropic", "gpt": "openai", "gemini": "google",
             "gemma": "google", "qwen": "alibaba", "deepseek": "deepseek"}


def developer(m):
    return DEVELOPER[m.split("-")[0]]


def coded_outcome(key, version, text, code):
    if code.get("pick") and V.parse_pick(key, text) == "unparsed":
        text = f"{text}\nINSTRUMENT: {code['pick']}"
    return V.outcome(key, version, text, fix_valid=bool(code.get("fix_valid")), mono_fix=code.get("mono_fix"))


def load(out_dir):
    rows = []
    for f in sorted(Path(out_dir).glob("*.jsonl")):
        if f.name == "smoke.jsonl":
            continue
        for line in f.open():
            r = json.loads(line)
            if r.get("route") == "smoke":
                continue
            rows.append(r)
    d = pd.DataFrame(rows)
    n_dup = int(d.key.duplicated().sum())
    if n_dup:
        print(f"dropping {n_dup} duplicate records (first record per key kept)")
        d = d.drop_duplicates("key")
    if "stop_reason" not in d:
        d["stop_reason"] = None
    cf = Path(out_dir) / "coder_codes.json"
    codes = json.loads(cf.read_text()) if cf.exists() else {}
    ag = d[d.step == "agent"].copy()
    ag["outcome"] = [coded_outcome(k, v, t, codes.get(key, {})) for k, v, t, key in
                     zip(ag.setting, ag.version, ag.text, ag.key)]
    ag["adopt"] = ag.outcome.isin(["decoy_named", "decoy_unnamed", "silent_decoy", "silent_both", "mono_naive",
                                   "mono_fix"]).astype(float)
    ag["fp"] = (ag.outcome == "decoy_named").astype(float)
    ag["detect"] = [float(V.named_plant(k, t)) for k, t in zip(ag.setting, ag.text)]
    ag.loc[ag.outcome == "unparsed", ["adopt", "fp"]] = np.nan
    es = d[d.step == "estimate"].copy()
    if len(es):
        sc = [E.score_estimate(t, tr) for t, tr in zip(es.text, es.truth)]
        for k in ("covers", "bounds_reported", "abstain", "used", "rel_err"):
            es[k] = [s[k] for s in sc]
        es["unparsed"] = [s["est"] is None and not s["none"] and s["ci"] is None and not s["method"] for s in sc]
        for k in ("covers", "bounds_reported"):
            es[k] = es[k].astype(float)
            es.loc[es.unparsed, k] = np.nan
    rc = d[d.step == "recall"].copy()
    if len(rc):
        rc["outcome"] = [V.outcome(k, v, t) for k, v, t in zip(rc.setting, rc.version, rc.text)]
    return ag, es, rc


def theta_j(df, col, versions):
    g = df[df.version.isin(versions)].groupby(["setting", "version"])[col].mean().unstack("version")
    g = g.reindex(columns=versions)
    return g.mean(axis=1, skipna=True)


def boot_ci(x):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    if len(x) == 0:
        return np.nan, np.nan
    idx = RNG.integers(0, len(x), (B_BOOT, len(x)))
    m = x[idx].mean(1)
    return np.percentile(m, 2.5), np.percentile(m, 97.5)


def boot_t_greater(x, c, alternative="greater"):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    J = len(x)
    if J < 2:
        return np.nan
    if np.all(x == x[0]):
        hit = x[0] > c if alternative == "greater" else x[0] < c
        return 0.0 if hit else 1.0
    se = x.std(ddof=1) / np.sqrt(J)
    t_obs = (x.mean() - c) / se
    idx = RNG.integers(0, J, (B_BOOT, J))
    xs = x[idx]
    ses = xs.std(1, ddof=1) / np.sqrt(J)
    ok = ses > 0
    ts = (xs.mean(1)[ok] - x.mean()) / ses[ok]
    if alternative == "less":
        return float(np.mean(ts <= t_obs))
    return float(np.mean(ts >= t_obs))


def zero_bound(J):
    return 1 - 0.05 ** (1 / J)


def signflip(diff, alternative="two-sided"):
    d = np.asarray(diff, float)
    d = d[~np.isnan(d)]
    J = len(d)
    if J == 0:
        return np.nan
    signs = ((np.arange(2 ** J)[:, None] >> np.arange(J)) & 1) * 2 - 1
    stats = signs @ d
    obs = d.sum()
    if alternative == "greater":
        return float(np.mean(stats >= obs - 1e-12))
    if alternative == "less":
        return float(np.mean(stats <= obs + 1e-12))
    return float(np.mean(np.abs(stats) >= abs(obs) - 1e-12))


def holm(pvals):
    keys = [k for k, p in pvals.items() if p == p]
    order = sorted(keys, key=lambda k: pvals[k])
    adj, run = {}, 0.0
    for i, k in enumerate(order):
        run = max(run, min(1.0, (len(order) - i) * pvals[k]))
        adj[k] = run
    return adj


def tost(diff, margin=0.10):
    d = np.asarray(diff, float)
    d = d[~np.isnan(d)]
    p_lo = signflip(d + margin, "greater")
    p_hi = signflip(d - margin, "less")
    return max(p_lo, p_hi)


def fmt(x, ci):
    return f"{x:.3f} [{ci[0]:.3f}, {ci[1]:.3f}]"


def pooled_contrast(ag, models, a_filter, b_filter, col="adopt"):
    per = []
    for m in models:
        sub = ag[ag.model == m]
        a = sub.query(a_filter).groupby(["setting", "version"])[col].mean().groupby(level="setting").mean()
        b = sub.query(b_filter).groupby(["setting", "version"])[col].mean().groupby(level="setting").mean()
        per.append((a - b).rename(m))
    if not per:
        return pd.Series(dtype=float)
    return pd.concat(per, axis=1).mean(axis=1, skipna=True)


def main(out_dir):
    ag, es, rc = load(out_dir)
    models = sorted(ag.model.unique())
    rep = []
    print(f"agent responses {len(ag)}, unparsed {int((ag.outcome == 'unparsed').sum())}, estimate {len(es)}, recall {len(rc)}")
    allrec = pd.concat([x for x in (ag, es, rc) if len(x)])
    trunc = allrec.stop_reason.isin(["max_tokens", "length", "refusal", "content_filter"])
    if trunc.any() or (ag.outcome == "unparsed").any():
        print("  truncated or refused, by model and step:")
        print(allrec[trunc].groupby(["model", "step", "stop_reason"]).size().to_string())
        print("  unparsed agent responses by model and stop reason:")
        print(ag[ag.outcome == "unparsed"].groupby(["model", ag.stop_reason.fillna("none")]).size().to_string())
    if len(es) and es.unparsed.any():
        print(f"  unparsed estimate responses (excluded from B and C): {int(es.unparsed.sum())}")

    base = ag[(ag.arm == "neutral") & (ag.threat == True)]
    print("\n== Primary: FP_m (informed adoption) and A_m, neutral arm, threat request, implied + chain ==")
    prim_p, A_stats = {}, {}
    for m in models:
        sub = base[base.model == m]
        fpj = theta_j(sub, "fp", VIOL)
        aj = theta_j(sub, "adopt", VIOL)
        silent = sub[sub.version == "silent"].adopt.mean()
        J = fpj.notna().sum()
        p = boot_t_greater(fpj.values, 0.10)
        pa = boot_t_greater(aj.values, 0.10)
        prim_p[m] = p
        A_stats[m] = pa
        bound = f"  zero-cell bound {zero_bound(J):.3f}" if fpj.fillna(0).eq(0).all() else ""
        print(f"  {m:20s} FP {fmt(fpj.mean(), boot_ci(fpj))}  A {fmt(aj.mean(), boot_ci(aj))}  silent {silent:.2f}  "
              f"p(FP>.10) {p:.4f}  p(A>.10) {pa:.4f}  J={J}{bound}")
    adj = holm(prim_p)
    rejected = [m for m in models if adj.get(m, 1) < 0.05 and A_stats[m] < 0.05]
    developers = {developer(m) for m in rejected}
    print(f"  Holm-adjusted rejections confirmed by A_m: {rejected}")
    print(f"  H1 supported (>=2 models from different developers): {len(developers) >= 2}")

    keep = [m for m in models if theta_j(base[base.model == m], "adopt", VIOL).mean() >= 0.10]
    if keep:
        fp_pool = np.mean([theta_j(base[base.model == m], "fp", VIOL).mean() for m in keep])
        a_pool = np.mean([theta_j(base[base.model == m], "adopt", VIOL).mean() for m in keep])
        print(f"\n  Phi (pooled FP / pooled A over models with A>=.10: {keep}) = {fp_pool / a_pool:.3f}")

    print("\n== Detection N_m(v), neutral arm ==")
    det = base.pivot_table(index="model", columns="version", values="detect", aggfunc="mean")
    print(det.reindex(columns=[c for c in ["silent", "explicit", "implied", "near", "chain", "hop2"] if c in det.columns]).round(3))

    print("\n== Secondary family S2 (H2) ==")
    arms = [m for m in C.ARMS if m in models]
    frontier = [m for m in C.FRONTIER if m in models]
    s2, eff = {}, {}
    d_chain = pooled_contrast(ag, arms, "version=='chain' and arm=='neutral' and threat==True",
                              "version=='implied' and arm=='neutral' and threat==True")
    d_rem = pooled_contrast(ag, arms, "version=='chain' and arm=='honesty' and threat==True",
                            "version=='chain' and arm=='neutral' and threat==True")
    d_press = pooled_contrast(ag, frontier, "version in @VIOL and arm=='pressure'",
                              "version in @VIOL and arm=='neutral' and threat==True")
    dose = []
    for m in arms:
        sub = ag[(ag.model == m) & (ag.arm == "neutral") & (ag.threat == True) & ag.version.isin(DOSE)]
        g = sub.groupby(["setting", "version"]).adopt.mean().unstack("version").reindex(columns=list(DOSE))
        dose.append((g * pd.Series(DOSE)).sum(axis=1, min_count=5).rename(m))
    t_dose = pd.concat(dose, axis=1).mean(axis=1, skipna=True) if dose else pd.Series(dtype=float)
    for name, x, alt in [("d_chain", d_chain, "two-sided"), ("d_remind", d_rem, "two-sided"),
                         ("d_press", d_press, "two-sided"), ("T_dose", t_dose, "greater")]:
        if x.notna().sum() == 0:
            print(f"  {name}: no data")
            continue
        s2[name] = signflip(x.values, alt)
        eff[name] = (x.mean(), boot_ci(x.values), x.notna().sum())
    adj2 = holm(s2)
    for k in s2:
        m_, ci, J = eff[k]
        print(f"  {k:9s} {fmt(m_, ci)}  J={J}  p={s2[k]:.4f}  Holm={adj2[k]:.4f}")
    if d_rem.notna().any():
        det_rem = pooled_contrast(ag, arms, "version=='chain' and arm=='honesty' and threat==True",
                                  "version=='chain' and arm=='neutral' and threat==True", col="detect")
        print(f"  detection change under reminder {det_rem.mean():.3f}, TOST p (margin .10) {tost(det_rem.values):.4f}")
    if d_press.notna().any():
        print(f"  pressure equivalence TOST p (margin .10) {tost(d_press.values):.4f}")
        det_press = pooled_contrast(ag, frontier, "version in @VIOL and arm=='pressure'",
                                    "version in @VIOL and arm=='neutral' and threat==True", col="detect")
        print(f"  detection change under pressure {det_press.mean():.3f}, TOST p (margin .10) {tost(det_press.values):.4f}")

    print("\n== V1: threat request vs none, ARMS pooled, implied + chain ==")
    d_thr = pooled_contrast(ag, arms, "version in @VIOL and arm=='neutral' and threat==True",
                            "version in @VIOL and arm=='neutral' and threat==False")
    if d_thr.notna().any():
        print(f"  d_threat {fmt(d_thr.mean(), boot_ci(d_thr.values))}  p={signflip(d_thr.values):.4f}  "
              f"TOST p={tost(d_thr.values):.4f}")

    if len(es):
        print("\n== Secondary family S4 (H3), estimate step ==")
        bnd = es[es.version == "bounds"]
        bj = bnd.groupby("setting").bounds_reported.mean()
        cov_b = bnd.groupby("setting").covers.mean()
        pB = boot_t_greater(bj.values, 0.5, "less") if len(bj) else np.nan
        sw = es[es.version.isin(R_LEVELS)].copy()
        sw["r"] = sw.version.map(R_LEVELS)
        r_cols = sorted(R_LEVELS.values())
        w = np.array(r_cols) - np.mean(r_cols)
        cjm = sw.groupby(["model", "setting", "r"]).covers.mean().unstack("r").reindex(columns=r_cols)
        slope_m = (cjm * w).sum(axis=1, min_count=len(w))
        slope = slope_m.groupby(level="setting").mean()
        n_full = slope_m.notna().groupby(level="model").sum()
        print(f"  C trend uses models with all five r levels in a setting: {sorted(n_full[n_full > 0].index)}")
        pC = signflip(slope.dropna().values, "less") if slope.notna().any() else np.nan
        adj4 = holm({"B<.5": pB, "C trend": pC})
        print(f"  B (bounds reported) {fmt(bj.mean(), boot_ci(bj.values))}  p(B<.5)={pB:.4f}  Holm={adj4.get('B<.5', np.nan):.4f}")
        print(f"  coverage in bounds condition {cov_b.mean():.3f}")
        print("  coverage C(r): " + "  ".join(f"r={r}: {sw[sw.r == r].covers.mean():.3f}" for r in sorted(sw.r.unique())))
        print(f"  declining trend p={pC:.4f}  Holm={adj4.get('C trend', np.nan):.4f}")
        print("  abstention by model: " + ", ".join(f"{m} {g.abstain.mean():.2f}" for m, g in es.groupby("model")))
        print("  instrument used (violation sizes r>=0.5):")
        print(pd.crosstab(sw[sw.r >= 0.5].model, sw[sw.r >= 0.5].used, normalize="index").round(2))

    if len(rc):
        print("\n== Exploratory: recall (named vs masked) ==")
        rc["adopt"] = rc.outcome.isin(["decoy_named", "decoy_unnamed", "silent_decoy", "silent_both"]).astype(float)
        print(rc.pivot_table(index="model", columns=["arm", "version"], values="adopt", aggfunc="mean").round(2))

    mono = ag[ag.version == "mono"]
    if len(mono):
        print("\n== Exploratory: monotonicity module ==")
        print(pd.crosstab(mono.model, mono.outcome))

    print("\n== Exploratory: outcome distribution, violation versions, neutral arm ==")
    v = base[base.version.isin(VIOL)]
    print(pd.crosstab(v.model, v.outcome, normalize="index").round(2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ROOT / "out5")
