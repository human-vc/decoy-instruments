import sys

import numpy as np
from scipy import optimize, special, stats

RNG = np.random.default_rng(20261105)
R = 4000
J = 20
NONFRONTIER_IMPLIED = np.array([0.30, 0.25, 0.85, 0.30, 0.45, 0.10, 0.60, 0.15])
FRONTIER_BASE = np.array([0.02, 0.02, 0.02, 0.02])


def shift_logit(p, d):
    return special.expit(special.logit(np.clip(p, 1e-4, 1 - 1e-4)) + d)


def solve_shift(p, target, sd):
    z = np.random.default_rng(0).standard_normal(20000) * sd
    a = special.logit(np.clip(np.atleast_1d(p), 1e-4, 1 - 1e-4))[:, None]
    base = special.expit(a + z).mean()
    f = lambda d: special.expit(a + z + d).mean() - base - target
    return optimize.brentq(f, -15, 15)


def cell_rates(p, sd, reps, J_=J):
    p = np.atleast_1d(p)
    a = special.logit(np.clip(p, 1e-4, 1 - 1e-4))
    return special.expit(a[None, :, None] + RNG.standard_normal((reps, len(p), J_)) * sd)


def draws(rate, K):
    return RNG.binomial(K, rate) / K


def t_reject(x, null=0.0, alpha=0.05, side="greater"):
    m = x.mean(-1)
    se = x.std(-1, ddof=1) / np.sqrt(x.shape[-1]) + 1e-12
    t = (m - null) / se
    df = x.shape[-1] - 1
    if side == "greater":
        return t > stats.t.ppf(1 - alpha, df)
    if side == "less":
        return t < stats.t.ppf(alpha, df)
    return np.abs(t) > stats.t.ppf(1 - alpha / 2, df)


def power_h1(fp, sd, K=4, alpha=0.05 / 12, null=0.10):
    rate = cell_rates(np.array([fp]), sd, R)[:, 0, :]
    y = draws(rate, K)
    return t_reject(y, null, alpha).mean()


def power_paired(p0, target, sd_set, sd_int, K0, K1, alpha, side, models=NONFRONTIER_IMPLIED):
    d = np.full(len(models), solve_shift(models, target, sd_set))
    a = special.logit(np.clip(models, 1e-4, 1 - 1e-4))
    s = RNG.standard_normal((R, len(models), J)) * sd_set
    e = RNG.standard_normal((R, len(models), J)) * sd_int
    r0 = special.expit(a[None, :, None] + s)
    r1 = special.expit(a[None, :, None] + s + d[None, :, None] + e)
    y0, y1 = draws(r0, K0), draws(r1, K1)
    diff = (y1 - y0).mean(1)
    return t_reject(diff, 0.0, alpha, side).mean(), (r1 - r0).mean()


def power_tost(sd_set, sd_int, K, margin=0.10, alpha=0.05, models=NONFRONTIER_IMPLIED):
    a = special.logit(np.clip(models, 1e-4, 1 - 1e-4))
    s = RNG.standard_normal((R, len(models), J)) * sd_set
    e = RNG.standard_normal((R, len(models), J)) * sd_int
    r0 = special.expit(a[None, :, None] + s)
    r1 = special.expit(a[None, :, None] + s + e)
    diff = (draws(r1, K) - draws(r0, K)).mean(1)
    return (t_reject(diff, -margin, alpha, "greater") & t_reject(diff, margin, alpha, "less")).mean()


def power_trend(total, sd_set, sd_int, K, levels=5, alpha=0.05, models=NONFRONTIER_IMPLIED):
    w = np.arange(levels) - (levels - 1) / 2
    steps = np.linspace(-total / 2, total / 2, levels)
    a = special.logit(np.clip(models, 1e-4, 1 - 1e-4))
    s = RNG.standard_normal((R, len(models), J)) * sd_set
    contrast = 0
    for lv in range(levels):
        d = np.full(len(models), solve_shift(models, steps[lv], sd_set))
        e = RNG.standard_normal((R, len(models), J)) * sd_int
        y = draws(special.expit(a[None, :, None] + s + d[None, :, None] + e), K).mean(1)
        contrast = contrast + w[lv] * y
    return t_reject(contrast, 0.0, alpha, "greater").mean()


def main():
    sds = [float(x) for x in sys.argv[1:]] or [0.8, 1.2, 1.6]
    print(f"J = {J} settings, R = {R} Monte Carlo replications, logit-normal setting heterogeneity\n")
    print("H1 (primary, per model): informed adoption FP_m > 0.10, one-sided t on setting means, Bonferroni alpha = 0.05/12")
    print("    K = 4 responses per setting (implied x2 + chain x2)")
    for sd in sds:
        print(f"  setting logit SD {sd}: " + "  ".join(f"FP={fp:.2f}:{power_h1(fp, sd):.2f}" for fp in (0.15, 0.20, 0.25, 0.30, 0.40)))
    print("    same, K = 6 per setting (implied x3 + chain x3):")
    for sd in sds:
        print(f"  setting logit SD {sd}: " + "  ".join(f"FP={fp:.2f}:{power_h1(fp, sd, K=6):.2f}" for fp in (0.15, 0.20, 0.25, 0.30, 0.40)))
    print("    threshold 0.05 instead of 0.10, K = 4:")
    for sd in sds:
        print(f"  setting logit SD {sd}: " + "  ".join(f"FP={fp:.2f}:{power_h1(fp, sd, null=0.05):.2f}" for fp in (0.10, 0.15, 0.20, 0.25, 0.30)))
    print("    pooled primary (one test): mean FP over 12 models > 0.10, one-sided 0.05; 4 frontier at 0.03 + 8 others")
    for sd in sds:
        row = []
        for others in (0.15, 0.20, 0.30):
            rates = np.array([0.03] * 4 + [others] * 8)
            r_ = cell_rates(rates, sd, R)
            y = draws(r_, 4).mean(1)
            row.append(f"others={others:.2f}:{t_reject(y, 0.10, 0.05).mean():.2f}")
        print(f"  setting logit SD {sd}: " + "  ".join(row))
    print("\nH2a chain minus implied adoption, 8 non-frontier models pooled, K = 2 per version, two-sided 0.05")
    for sd in sds:
        row = []
        for tgt in (0.05, 0.10, 0.15, 0.22):
            pw, _ = power_paired(None, tgt, sd, 0.6, 2, 2, 0.05, "two")
            row.append(f"+{tgt:.2f}:{pw:.2f}")
        print(f"  setting logit SD {sd}: " + "  ".join(row))
    print("\nH2b validity reminder minus neutral on chain, 8 non-frontier models pooled, K = 2 per arm, two-sided 0.05")
    for sd in sds:
        row = []
        for tgt in (-0.05, -0.10, -0.15, -0.24):
            pw, _ = power_paired(None, tgt, sd, 0.6, 2, 2, 0.05, "two")
            row.append(f"{tgt:.2f}:{pw:.2f}")
        print(f"  setting logit SD {sd}: " + "  ".join(row))
    print("\nH2c pressure minus neutral, 4 frontier models pooled, implied + chain, K = 4 neutral vs K = 2 pressure per setting")
    for sd in sds:
        row = []
        for tgt in (0.05, 0.10, 0.15):
            pw, _ = power_paired(None, tgt, sd, 0.6, 4, 2, 0.05, "two", models=FRONTIER_BASE)
            row.append(f"+{tgt:.2f}:{pw:.2f}")
        print(f"  setting logit SD {sd}: " + "  ".join(row))
    print("    with pressure at K = 1 per version (as in round 3):")
    for sd in sds:
        row = []
        for tgt in (0.05, 0.10, 0.15):
            pw, _ = power_paired(None, tgt, sd, 0.6, 4, 1, 0.05, "two", models=FRONTIER_BASE)
            row.append(f"+{tgt:.2f}:{pw:.2f}")
        print(f"  setting logit SD {sd}: " + "  ".join(row))
    print("\nValidity check: threat request ON minus OFF, 8 non-frontier models pooled, implied + chain, K = 4 per arm")
    for sd in sds:
        row = []
        for tgt in (0.05, 0.10, 0.15):
            pw, _ = power_paired(None, tgt, sd, 0.6, 4, 4, 0.05, "two")
            row.append(f"{tgt:.2f}:{pw:.2f}")
        print(f"  setting logit SD {sd}: difference test " + "  ".join(row) +
              f"   equivalence (TOST, margin 0.10) when true diff = 0: {power_tost(sd, 0.6, 4):.2f}")
    print("\nDose-response: linear trend over 5 levels (explicit, implied, near, chain, two-hop), 8 non-frontier models, K = 2")
    for sd in sds:
        print(f"  setting logit SD {sd}: " + "  ".join(f"range {tot:.2f}:{power_trend(tot, sd, 0.6, 2):.2f}" for tot in (0.10, 0.20, 0.30)))


if __name__ == "__main__":
    main()
