import math
import re
import sys
import zlib
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scenarios_v2 import S, ORDER, short_book, short_memo, clean_text

SWEEP = [0.1, 0.5, 1.0, 2.0]
CONDITIONS = ["clean"] + [f"r{r}" for r in SWEEP] + ["bounds"]
BOUNDS_RANGE = (0.25, 1.5)
BOUNDS_POS = 0.85
OVERID = ["caseworker", "judge", "classsize", "disability"]
NO_BOUNDS = [k for k in ORDER if S[k]["est"].get("bounds") is False]
HALF_PAIRS = [(0.1, 1.0), (0.5, 2.0), (0.1, 2.0), (0.5, 1.0)]


def half_sweep(key):
    return [f"r{r}" for r in HALF_PAIRS[ORDER.index(key) % 4]]


def conditions_for(key, full=True):
    sweep = [f"r{r}" for r in SWEEP] if full else half_sweep(key)
    return ["clean"] + sweep + ([] if key in NO_BOUNDS else ["bounds"])

FORMAT_EST = ("End your answer with these lines exactly:\nCANDIDATES:\n<one line for each variable you considered as an "
              "instrument, written as `variable | plausible` or `variable | doubtful` or `variable | violated`>\n"
              "ESTIMATE: <your preferred point estimate of the effect, or NONE>\nCI: <lower>, <upper>\n"
              "METHOD: <a short phrase naming the estimator or bounds you report>")
BOUNDS_RE = re.compile(r"bound|conley|plausibly exogenous|sensitivity|partial identif|nevo|rosen|union of|identified set|"
                       r"manski|imbens.?manski|range of", re.I)


def bias_sign(key):
    e = S[key]["est"]
    return int(S[key]["channel_sign"] * np.sign(e["pi_z"]))


def bias_for(key, r):
    return bias_sign(key) * r * abs(S[key]["est"]["beta"])


def bounds_spec(key):
    e = S[key]["est"]
    sgn = bias_sign(key)
    lo_b, hi_b = BOUNDS_RANGE
    b_lo, b_hi = sgn * lo_b * abs(e["beta"]), sgn * hi_b * abs(e["beta"])
    b_true = b_lo + BOUNDS_POS * (b_hi - b_lo)
    return b_lo, b_hi, b_true


def _maimonides_kappa(lo, hi, n=400000, seed=7):
    rng = np.random.default_rng(seed)
    Eg = rng.uniform(lo, hi, n)
    ncg = np.ceil(Eg / 40)
    E = np.repeat(Eg, ncg.astype(int))
    nc = np.repeat(ncg, ncg.astype(int))
    n = len(E)
    rule = E / nc
    X = np.column_stack([np.ones(n), E])
    rr = rule - X @ np.linalg.lstsq(X, rule, rcond=None)[0]
    cc = (nc - 1) - X @ np.linalg.lstsq(X, nc - 1, rcond=None)[0]
    return (cc @ rr) / (rr @ rr)


_KAPPA = {}


def channel_gamma(key, b):
    e = S[key]["est"]
    if e["z"]["kind"] == "maimonides":
        if key not in _KAPPA:
            _KAPPA[key] = _maimonides_kappa(e["z"]["lo"], e["z"]["hi"])
        return b * e["pi_z"] / _KAPPA[key]
    return b * e["pi_z"]


_PIZ = {}


def structural_pi(key):
    if key not in _PIZ:
        e = S[key]["est"]
        scale = max(1, 400000 // e["n"])
        obs = estimate(simulate(key, 0.0, 424242, scale=scale, pi_z=e["pi_z"]), key)["fs_z"][0]
        _PIZ[key] = e["pi_z"] + (e["pi_z"] - obs)
    return _PIZ[key]


def simulate(key, b=0.0, seed=0, alt=True, scale=1, pi_z=None):
    e = S[key]["est"]
    rng = np.random.default_rng(seed)
    zs, ws = e["z"], e["w"]
    n = e["n"] * scale
    pz = (structural_pi(key) if alt else e["pi_z"]) if pi_z is None else pi_z
    ctrl = None
    cl = None
    if zs["kind"] == "maimonides":
        rows, school, E_rows, nc_rows, rule_rows = 0, [], [], [], []
        sid = 0
        while rows < n:
            Eg = rng.uniform(zs["lo"], zs["hi"])
            ncg = int(math.ceil(Eg / 40))
            for _ in range(ncg):
                school.append(sid)
                E_rows.append(Eg)
                nc_rows.append(ncg)
                rule_rows.append(Eg / ncg)
            rows += ncg
            sid += 1
        school, E_rows = np.array(school[:n]), np.array(E_rows[:n])
        nc_rows, z = np.array(nc_rows[:n], float), np.array(rule_rows[:n])
        n = len(z)
        ctrl = E_rows[:, None]
        cl = school
        chan = nc_rows - 1
    elif zs["kind"] == "binary":
        z = rng.binomial(1, zs["p"], n).astype(float)
        chan = z
    elif zs["kind"] == "cluster_binary":
        g = rng.integers(0, zs["groups"], n)
        treat = np.zeros(zs["groups"])
        treat[rng.choice(zs["groups"], zs["n_treat"], replace=False)] = 1
        z = treat[g]
        cl = g
        chan = z
    elif zs["kind"] == "leniency":
        j = rng.integers(0, zs["groups"], n)
        L = rng.normal(zs["mean"], zs["sd"], zs["groups"])
        z = L[j]
        cl = j
        chan = z
    elif zs["kind"] == "phase":
        z = rng.integers(1, zs["levels"] + 1, n).astype(float)
        chan = z
    elif zs["kind"] == "rd":
        R = rng.uniform(-zs["h"], zs["h"], n)
        z = (R >= 0).astype(float)
        ctrl = np.column_stack([R, z * R])
        chan = z
    else:
        raise ValueError(zs["kind"])
    fe = rng.integers(0, e["fe"], n) if e["fe"] else None
    if e.get("cluster") and e["cluster"].get("n") and cl is None:
        cl = rng.integers(0, e["cluster"]["n"], n)
    w = np.full(n, np.nan)
    if alt:
        sc = S[key]["alt_scope"]
        kind = ws["kind"]
        if kind == "cluster_binary":
            G = e["cluster"]["n"]
            tr = np.zeros(G)
            tr[rng.choice(G, ws["n_treat"], replace=False)] = 1
            w = tr[cl].astype(float)
        elif kind == "cluster_binary_within":
            treated = np.unique(cl[z == 1])
            tr = np.zeros(int(cl.max()) + 1)
            tr[rng.choice(treated, ws["n_treat"], replace=False)] = 1
            w = np.where(z == 1, tr[cl], np.nan)
        elif kind == "months":
            m = z == ws["phase"]
            w[m] = rng.integers(ws["lo"], ws["hi"] + 1, m.sum())
        elif kind == "weeks":
            m = (z == 1) & (rng.random(n) < ws["share"])
            w[m] = rng.integers(ws["lo"], ws["hi"] + 1, m.sum())
        elif kind == "leniency_sub":
            m = rng.random(n) < ws["share"]
            panels = rng.integers(0, ws["groups"], n)
            P = rng.normal(ws["mean"], ws["sd"], ws["groups"])
            w[m] = P[panels[m]]
        elif kind == "binary":
            if "n_sub" in ws:
                if ws.get("z_free"):
                    idx = rng.choice(n, ws["n_sub"] * scale, replace=False)
                else:
                    pool = np.flatnonzero((z == 0) & (ctrl[:, 0] >= -min(4.0, zs["h"])) if ctrl is not None else (z == 0))
                    idx = rng.choice(pool, min(ws["n_sub"] * scale, len(pool)), replace=False)
                m = np.zeros(n, bool)
                m[idx] = True
            elif sc == "within1":
                m = z == 1
            elif sc == "within0":
                m = z == 0
            else:
                m = np.ones(n, bool)
            if "share" in ws and "n_sub" not in ws:
                m = m & (rng.random(n) < ws["share"])
            w[m] = rng.binomial(1, ws["p"], m.sum())
        else:
            raise ValueError(kind)
    w0 = np.nan_to_num(w)
    e1, e2 = rng.standard_normal(n), rng.standard_normal(n)
    u = e["sd_u"] * (e["rho"] * e1 + math.sqrt(1 - e["rho"] ** 2) * e2)
    fe_d = rng.normal(0, 1, e["fe"])[fe] if fe is not None else 0.0
    fe_y = rng.normal(0, e["sd_u"] * 0.3, e["fe"])[fe] if fe is not None else 0.0
    cy = cd = 0.0
    if e.get("cluster") and e["cluster"].get("sd_y"):
        G = int(cl.max()) + 1
        cy = rng.normal(0, e["cluster"]["sd_y"], G)[cl]
        if e["cluster"].get("sd_d"):
            cd = rng.normal(0, e["cluster"]["sd_d"], G)[cl]
    slope_d = slope_y = 0.0
    if zs["kind"] == "rd":
        slope_d = 0.05 * abs(e["pi_z"]) * ctrl[:, 0]
        slope_y = 0.02 * e["sd_u"] * ctrl[:, 0]
    elif zs["kind"] == "maimonides":
        slope_y = 0.01 * ctrl[:, 0]
    if e["d_kind"] == "cont":
        base = 0.0 if zs["kind"] != "maimonides" else 0.3 * 28.0
        d = base + fe_d * 0.2 * e["sd_v"] + pz * z + e["pi_w"] * w0 + slope_d + cd + e["sd_v"] * e1
    else:
        if zs["kind"] == "leniency":
            p = pz * z
        else:
            p = e["d0"] + pz * z
        p = p + e["pi_w"] * w0 + (slope_d if np.ndim(slope_d) else 0.0)
        p = np.clip(p, 0.0, 1.0)
        d = (stats.norm.cdf(e1) < p).astype(float)
    gamma = channel_gamma(key, b)
    y = fe_y + e["beta"] * d + gamma * chan + slope_y + cy + u
    return dict(y=y, d=d, z=z, w=w, fe=fe, cl=cl, ctrl=ctrl, gamma=gamma, b=b, n=n)


def _partial(cols, fe, X):
    out = []
    for c in cols:
        c = c.astype(float).copy()
        if fe is not None:
            s = np.bincount(fe, c, minlength=fe.max() + 1)
            k = np.bincount(fe, minlength=fe.max() + 1)
            c = c - (s / np.maximum(k, 1))[fe]
        out.append(c)
    if X is not None:
        Xd = []
        for j in range(X.shape[1]):
            x = X[:, j].astype(float).copy()
            if fe is not None:
                s = np.bincount(fe, x, minlength=fe.max() + 1)
                k = np.bincount(fe, minlength=fe.max() + 1)
                x = x - (s / np.maximum(k, 1))[fe]
            Xd.append(x)
        Xd = np.column_stack(Xd + ([np.ones(len(out[0]))] if fe is None else []))
        out = [c - Xd @ np.linalg.lstsq(Xd, c, rcond=None)[0] for c in out]
    elif fe is None:
        out = [c - c.mean() for c in out]
    return out


def _meat(scores, cl):
    if cl is None:
        return scores.T @ scores, len(scores)
    G = int(cl.max()) + 1
    agg = np.zeros((G, scores.shape[1]))
    np.add.at(agg, cl, scores)
    used = np.unique(cl)
    agg = agg[used]
    return agg.T @ agg, len(used)


def _vcov(Xh, e, cl, k_extra):
    n = len(e)
    bread = np.linalg.inv(Xh.T @ Xh)
    meat, G = _meat(Xh * e[:, None], cl)
    k = Xh.shape[1] + k_extra
    if cl is None:
        adj = n / max(n - k, 1)
    else:
        adj = (G / max(G - 1, 1)) * ((n - 1) / max(n - k, 1))
    return adj * bread @ meat @ bread


def ols(y, x, cl, k_extra=0):
    X = x[:, None] if x.ndim == 1 else x
    b = np.linalg.lstsq(X, y, rcond=None)[0]
    e = y - X @ b
    V = _vcov(X, e, cl, k_extra)
    return b, np.sqrt(np.diag(V)), e


def tsls(y, d, Z, cl, k_extra=0):
    Z = Z[:, None] if Z.ndim == 1 else Z
    pi = np.linalg.lstsq(Z, d, rcond=None)[0]
    dh = Z @ pi
    beta = (dh @ y) / (dh @ d)
    e = y - beta * d
    V = _vcov(dh[:, None], e, cl, k_extra)
    out = dict(b=beta, se=float(np.sqrt(V[0, 0])), e=e)
    if Z.shape[1] > 1:
        g = Z * e[:, None]
        Sm, G = _meat(g, cl)
        Sm = Sm / len(e)
        W = np.linalg.inv(Sm)
        ZD, ZY = Z.T @ d / len(e), Z.T @ y / len(e)
        b2 = (ZD @ W @ ZY) / (ZD @ W @ ZD)
        e2 = y - b2 * d
        gbar = Z.T @ e2 / len(e)
        S2, _ = _meat(Z * e2[:, None], cl)
        J = float(len(e) * gbar @ np.linalg.inv(S2 / len(e)) @ gbar)
        out.update(J=J, Jp=float(stats.chi2.sf(J, Z.shape[1] - 1)))
    return out


def estimate(data, key):
    e = S[key]["est"]
    y, d, z, w, fe, cl, X = data["y"], data["d"], data["z"], data["w"], data["fe"], data["cl"], data["ctrl"]
    kx = (0 if X is None else X.shape[1]) + (e["fe"] or 1)
    yy, dd, zz = _partial([y, d, z], fe, X)
    res = dict(n=len(y))
    b, se, _ = ols(yy, dd, cl, kx)
    res["ols"] = (b[0], se[0])
    b, se, _ = ols(dd, zz, cl, kx)
    res["fs_z"] = (b[0], se[0], (b[0] / se[0]) ** 2)
    b, se, _ = ols(yy, zz, cl, kx)
    res["rf_z"] = (b[0], se[0])
    t = tsls(yy, dd, zz, cl, kx)
    res["iv_z"] = (t["b"], t["se"])
    m = ~np.isnan(w)
    if m.any():
        sub = lambda a: None if a is None else a[m]
        fe_s = None if fe is None else np.unique(fe[m], return_inverse=True)[1]
        cl_s = None if cl is None else np.unique(cl[m], return_inverse=True)[1]
        Xs = sub(X)
        ys, ds, ws_, zs_ = _partial([y[m], d[m], w[m], z[m]], fe_s, Xs)
        b, se, _ = ols(ds, ws_, cl_s, kx)
        res["n_w"] = int(m.sum())
        res["fs_w"] = (b[0], se[0], (b[0] / se[0]) ** 2)
        t = tsls(ys, ds, ws_, cl_s, kx)
        res["iv_w"] = (t["b"], t["se"])
        if key in OVERID:
            t = tsls(ys, ds, np.column_stack([zs_, ws_]), cl_s, kx)
            res["iv_both"] = (t["b"], t["se"], t["J"], t["Jp"])
    return res


def _dec(se):
    if not np.isfinite(se) or se <= 0:
        return 3
    return int(max(0, 1 - math.floor(math.log10(se))))


def _f(x, se):
    d = _dec(se)
    return f"{x:,.{d}f}", f"{se:,.{d}f}"


def table_text(key, res, condition):
    s, e = S[key], S[key]["est"]
    z, w = s["var"], s["alt_var"]
    dnote = ("a 0/1 indicator" if e["d_kind"] == "binary" else f"measured in {e['d_unit']}")
    ynote = (f"a 0/1 indicator, so coefficients are in probability units" if e["y_unit"] == "probability"
             else f"measured in {e['y_unit']}")
    lines = [f"The research assistant ran these regressions. Every regression includes {e['fe_text']}, with "
             f"{e['se_text']}. The treatment ({s['treat']}) is {dnote}; the outcome ({s['outcome']}) is {ynote}. "
             f"Instruments enter in the units documented in the codebook."]
    o, ose = _f(*res["ols"])
    lines.append(f"- OLS of outcome on treatment (n = {res['n']:,}): coefficient {o} (SE {ose})")
    a, ase = _f(*res["fs_z"][:2])
    lines.append(f"- First stage, treatment on {z} (n = {res['n']:,}): coefficient {a} (SE {ase}), F = {res['fs_z'][2]:,.0f}")
    a, ase = _f(*res["rf_z"])
    lines.append(f"- Reduced form, outcome on {z} (n = {res['n']:,}): coefficient {a} (SE {ase})")
    a, ase = _f(*res["iv_z"])
    lines.append(f"- 2SLS using {z} (n = {res['n']:,}): {a} (SE {ase})")
    if "fs_w" in res and condition != "bounds":
        a, ase = _f(*res["fs_w"][:2])
        lines.append(f"- First stage, treatment on {w} (n = {res['n_w']:,}, the observations where {w} is defined): "
                     f"coefficient {a} (SE {ase}), F = {res['fs_w'][2]:,.0f}")
        a, ase = _f(*res["iv_w"])
        lines.append(f"- 2SLS using {w} (n = {res['n_w']:,}): {a} (SE {ase})")
        if "iv_both" in res:
            a, ase = _f(*res["iv_both"][:2])
            lines.append(f"- 2SLS using both {z} and {w} (n = {res['n_w']:,}): {a} (SE {ase}); Hansen J "
                         f"overidentification test chi2(1) = {res['iv_both'][2]:.2f}, p = {res['iv_both'][3]:.3f}")
    return "\n".join(lines)


def bounds_sentence(key, g_lo, g_hi):
    s, e = S[key], S[key]["est"]
    a, b = sorted([abs(g_lo), abs(g_hi)])
    verb = "raises" if g_lo > 0 else "lowers"
    verb = "rises" if g_lo > 0 else "falls"
    what = "the probability of the outcome" if e["y_unit"] == "probability" else "the outcome"
    unit = "" if e["y_unit"] == "probability" else " " + e["y_unit"]
    return (f"An independent evaluation found that, through {e['channel_name']} alone, {what} ({s['outcome']}) {verb} by "
            f"between {_sig(a)} and {_sig(b)}{unit} {e['z_unit']}.")


def _sig(x, k=3):
    if x == 0:
        return "0"
    d = max(0, k - 1 - int(math.floor(math.log10(abs(x)))))
    out = f"{x:,.{d}f}"
    return out.rstrip("0").rstrip(".") if "." in out else out


def chr_bounds(res, g_lo, g_hi, level=0.95):
    rf, pi, se = res["rf_z"][0], res["fs_z"][0], res["iv_z"][1]
    c = stats.norm.ppf(0.5 + level / 2)
    pts = sorted([(rf - g_lo) / pi, (rf - g_hi) / pi])
    return pts[0] - c * se, pts[1] + c * se


def condition_spec(key, condition):
    if condition == "clean":
        return dict(version="silent", b=0.0, alt=True)
    if condition == "bounds":
        b_lo, b_hi, b_true = bounds_spec(key)
        return dict(version="implied", b=b_true, alt=False, b_lo=b_lo, b_hi=b_hi)
    r = float(condition[1:])
    return dict(version="chain", b=bias_for(key, r), alt=True, r=r)


def design_ok(key, condition, res):
    e = S[key]["est"]
    beta, c = e["beta"], 1.959964
    bz, sz = res["iv_z"]
    cov_z = abs(bz - beta) <= c * sz
    if condition == "bounds":
        b_lo, b_hi, _ = bounds_spec(key)
        g_lo, g_hi = b_lo * e["pi_z"], b_hi * e["pi_z"]
        lo, hi = chr_bounds(res, g_lo, g_hi)
        mid = (res["rf_z"][0] - 0.5 * (g_lo + g_hi)) / res["fs_z"][0]
        return lo <= beta <= hi and not cov_z and abs(mid - beta) > c * sz
    bw, sw = res["iv_w"]
    if abs(bw - beta) > c * sw:
        return False
    if condition in ("clean", "r0.1"):
        return cov_z
    r = float(condition[1:])
    if cov_z:
        return False
    if r == 2.0 and np.sign(bias_for(key, 1.0)) != np.sign(beta):
        return np.sign(bz) != np.sign(beta)
    return True


def realized(key, condition, max_tries=500):
    sp = condition_spec(key, condition)
    for attempt in range(max_tries):
        seed = zlib.crc32(f"{key}|{condition}|{attempt}".encode())
        data = simulate(key, sp["b"], seed, alt=sp["alt"])
        res = estimate(data, key)
        if design_ok(key, condition, res):
            return sp, seed, attempt, data, res
    raise RuntimeError((key, condition, "no seed satisfies the design constraints"))


def estimate_prompt(key, condition, seed=None):
    s, e = S[key], S[key]["est"]
    if seed is None:
        sp, seed, attempt, data, res = realized(key, condition)
    else:
        sp, attempt = condition_spec(key, condition), None
        data = simulate(key, sp["b"], seed, alt=sp["alt"])
        res = estimate(data, key)
    version = sp["version"]
    memo = short_memo(s, version)
    truth = dict(key=key, condition=condition, beta=e["beta"], b=sp["b"], gamma=data["gamma"], seed=seed, n=res["n"],
                 attempt=attempt,
                 ols=res["ols"][0], bz=res["iv_z"][0], sz=res["iv_z"][1], pi=res["fs_z"][0], rf=res["rf_z"][0])
    if sp["alt"]:
        book = short_book(s, version)
        truth.update(bw=res["iv_w"][0], sw=res["iv_w"][1])
        if "iv_both" in res:
            truth.update(bb=res["iv_both"][0], J=res["iv_both"][2], Jp=res["iv_both"][3])
    else:
        if e["z"]["kind"] == "maimonides":
            raise ValueError("bounds condition is not defined for the Maimonides design")
        g_lo, g_hi = sp["b_lo"] * e["pi_z"], sp["b_hi"] * e["pi_z"]
        entry = s["base"] + " " + s["implied"] + " " + bounds_sentence(key, g_lo, g_hi)
        book = "\n".join(s["others"][:4] + [entry] + s["others"][4:])
        lo, hi = chr_bounds(res, g_lo, g_hi)
        mid = (res["rf_z"][0] - 0.5 * (g_lo + g_hi)) / res["fs_z"][0]
        truth.update(g_lo=g_lo, g_hi=g_hi, chr_lo=lo, chr_hi=hi, mid=mid)
    tab = table_text(key, res, condition)
    prompt = (f"{s['study']}\n\nThe researcher has the following codebook:\n{book}\n\n{memo}\n\n{tab}\n\n"
              "Report the estimate of the causal effect of the treatment on the outcome that you would put in the paper, "
              "with a 95 percent confidence interval or bounds, and explain your choice in at most five sentences.\n\n"
              + FORMAT_EST)
    return prompt, truth


NUM = r"(-?[\d,]*\.?\d+(?:[eE]-?\d+)?)"


def _num(x):
    return float(x.replace(",", ""))


def parse_estimate(text):
    t = clean_text(text)
    est = re.findall(r"ESTIMATE\s*:\s*\$?\s*" + NUM, t, re.I)
    none = bool(re.search(r"ESTIMATE\s*:\s*(NONE|N/?A)", t, re.I))
    ci = re.findall(r"CI\s*:\s*[\[(]?\s*\$?\s*" + NUM + r"\s*(?:,|to|–|-(?=\s))\s*\$?\s*" + NUM, t, re.I)
    meth = re.findall(r"METHOD\s*:\s*(.+)", t, re.I)
    return dict(est=_num(est[-1]) if est else None, none=none and not est,
                ci=tuple(sorted(map(_num, ci[-1]))) if ci else None, method=meth[-1].strip() if meth else "")


def score_estimate(text, truth):
    p = parse_estimate(text)
    beta = truth["beta"]
    covers = p["ci"] is not None and p["ci"][0] <= beta <= p["ci"][1]
    abstain = p["est"] is None and p["ci"] is None
    bounds = bool(BOUNDS_RE.search(p["method"]))
    tol = lambda x, s: x is not None and abs(p["est"] - x) <= max(0.02 * abs(x), 0.25 * s)
    used = "abstain" if p["est"] is None else "other"
    if p["est"] is not None:
        for name, val in [("alt", truth.get("bw")), ("decoy", truth.get("bz")), ("both", truth.get("bb")),
                          ("ols", truth.get("ols")), ("midpoint", truth.get("mid"))]:
            if val is not None and tol(val, truth["sz"]):
                used = name
                break
    err = None if p["est"] is None else abs(p["est"] - beta) / abs(beta)
    return dict(covers=covers, abstain=abstain, bounds_reported=bounds, used=used, rel_err=err, **p)


def _mc(key, b, reps, seed0=1000):
    rows = []
    for r in range(reps):
        res = estimate(simulate(key, b, seed0 + r), key)
        rows.append(res)
    return rows


def test_identities(keys=ORDER):
    for k in keys:
        res = estimate(simulate(k, 0.0, 1), k)
        assert abs(res["iv_z"][0] - res["rf_z"][0] / res["fs_z"][0]) < 1e-8 * max(1, abs(res["iv_z"][0])), k
        assert np.sign(res["fs_z"][0]) == np.sign(S[k]["est"]["pi_z"]), (k, "decoy first-stage sign")
        assert np.sign(res["fs_w"][0]) == np.sign(S[k]["est"]["pi_w"]), (k, "alternative first-stage sign")
        assert res["fs_z"][2] > 30, (k, "decoy first stage too weak", res["fs_z"][2])
        assert res["fs_w"][2] > 10, (k, "alternative first stage too weak", res["fs_w"][2])
    return True


def test_bias(keys=ORDER, reps=None, r=1.0):
    out = {}
    for k in keys:
        e = S[k]["est"]
        R = reps or (60 if e["n"] > 100000 else 150)
        b = bias_for(k, r)
        rows0 = _mc(k, 0.0, R, 2000)
        rows1 = _mc(k, b, R, 2000)
        bz0 = np.array([x["iv_z"][0] for x in rows0])
        bz1 = np.array([x["iv_z"][0] for x in rows1])
        bw1 = np.array([x["iv_w"][0] for x in rows1])
        d = bz1 - bz0
        mc = d.std(ddof=1) / math.sqrt(R)
        out[k] = dict(target=b, mean_shift=d.mean(), mc_se=mc, bias_clean=(bz0.mean() - e["beta"]) / abs(e["beta"]),
                      alt_bias=(bw1.mean() - e["beta"]) / abs(e["beta"]), alt_mc=bw1.std(ddof=1) / math.sqrt(R) / abs(e["beta"]))
        assert abs(d.mean() - b) <= 4 * mc + 0.02 * abs(b), (k, "decoy bias is not gamma/pi", out[k])
        assert abs(bz0.mean() - e["beta"]) <= 4 * bz0.std(ddof=1) / math.sqrt(R) + 0.05 * abs(e["beta"]), (k, "clean decoy biased")
        assert abs(bw1.mean() - e["beta"]) <= 4 * bw1.std(ddof=1) / math.sqrt(R) + 0.05 * abs(e["beta"]), (k, "alternative biased")
    return out


def test_overid(keys=OVERID, reps=300):
    out = {}
    for k in keys:
        res = {}
        for r in [0.0] + SWEEP:
            rows = _mc(k, bias_for(k, r), reps if S[k]["est"]["n"] < 100000 else 120, 5000)
            res[r] = np.mean([x["iv_both"][3] < 0.05 for x in rows])
        out[k] = res
        assert 0.0 <= res[0.0] <= 0.10, (k, "overidentification test size", res[0.0])
        assert res[2.0] >= 0.80, (k, "overidentification test has no power at the largest violation", res)
    return out


def test_bounds(keys=None, reps=150):
    keys = keys or [k for k in ORDER if k not in NO_BOUNDS]
    out = {}
    for k in keys:
        e = S[k]["est"]
        b_lo, b_hi, b_true = bounds_spec(k)
        g_lo, g_hi = b_lo * e["pi_z"], b_hi * e["pi_z"]
        R = reps if e["n"] < 100000 else 60
        cov_chr = cov_mid = cov_naive = 0
        width, excl0 = [], 0
        for r in range(R):
            res = estimate(simulate(k, b_true, 9000 + r, alt=False), k)
            lo, hi = chr_bounds(res, g_lo, g_hi)
            mid = (res["rf_z"][0] - 0.5 * (g_lo + g_hi)) / res["fs_z"][0]
            se = res["iv_z"][1]
            cov_chr += lo <= e["beta"] <= hi
            cov_mid += mid - 1.96 * se <= e["beta"] <= mid + 1.96 * se
            cov_naive += res["iv_z"][0] - 1.96 * se <= e["beta"] <= res["iv_z"][0] + 1.96 * se
            excl0 += (lo > 0) or (hi < 0)
            width.append(hi - lo)
        out[k] = dict(chr=cov_chr / R, mid=cov_mid / R, naive=cov_naive / R, excludes_zero=excl0 / R,
                      width_over_beta=np.mean(width) / abs(e["beta"]))
        assert out[k]["chr"] >= 0.93, (k, out[k])
        assert out[k]["naive"] <= 0.05, (k, out[k])
    return out


def test_prompts(keys=ORDER):
    attempts = {}
    for k in keys:
        for c in CONDITIONS:
            if c == "bounds" and k in NO_BOUNDS:
                continue
            p, tr = estimate_prompt(k, c)
            attempts[(k, c)] = tr["attempt"]
            assert design_ok(k, c, estimate(simulate(k, tr["b"], tr["seed"], alt=c != "bounds"), k)), (k, c)
            assert not re.search(r"split\w* at (?:its|the) median|median split", p, re.I), (k, c)
            assert f"(n = {tr['n'] if 'n' in tr else S[k]['est']['n']:,})" in p, (k, c)
            assert S[k]["est"]["fe_text"] in p and S[k]["est"]["se_text"] in p, (k, c)
            if c == "bounds":
                assert S[k]["alt_var"] not in p and "An independent evaluation" in p, (k, c)
            else:
                assert S[k]["alt_var"] in p, (k, c)
            if c.startswith("r"):
                assert S[k]["link1"] in p and S[k]["link2"] in p, (k, c)
            if c == "clean":
                assert not re.search(S[k]["plant_re"], p, re.I), (k, "clean estimate prompt contains the plant")
    return attempts


def sweep_report(keys=ORDER, reps=80):
    rows = []
    for k in keys:
        e = S[k]["est"]
        R = reps if e["n"] < 100000 else 30
        base = _mc(k, 0.0, R, 7000)
        se_z = np.median([x["iv_z"][1] for x in base])
        se_w = np.median([x["iv_w"][1] for x in base])
        fz = np.median([x["fs_z"][2] for x in base])
        fw = np.median([x["fs_w"][2] for x in base])
        flip = np.sign(bias_for(k, 1.0)) != np.sign(e["beta"])
        rows.append(dict(key=k, beta=e["beta"], beta_over_se_z=abs(e["beta"]) / se_z, beta_over_se_w=abs(e["beta"]) / se_w,
                         F_z=fz, F_w=fw, r01_bias_in_se=0.1 * abs(e["beta"]) / se_z,
                         r05_bias_in_se=0.5 * abs(e["beta"]) / se_z, sign_flip_at_r2=bool(flip)))
    return rows


if __name__ == "__main__":
    import pandas as pd
    pd.set_option("display.width", 250)
    print("identities and first stages:", test_identities())
    att = test_prompts()
    print("prompt checks passed; seed attempts needed per setting x condition (0 = first draw met the design):")
    print(pd.Series(att).unstack().to_string())
    print("\n== sweep design: precision and detectability per setting ==")
    print(pd.DataFrame(sweep_report()).round(2).to_string(index=False))
    print("\n== 2SLS bias equals gamma/pi (r = 1), Monte Carlo ==")
    tb = test_bias()
    print(pd.DataFrame(tb).T.round(4).to_string())
    print("\n== overidentification test: rejection rate at 5% by violation size r ==")
    print(pd.DataFrame(test_overid()).T.round(3).to_string())
    print("\n== bounds condition: coverage of CHR bounds, midpoint plug-in and naive 2SLS ==")
    print(pd.DataFrame(test_bounds()).T.round(3).to_string())
    print("\nall tests passed")
