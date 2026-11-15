"""Accuracy, range and alert metrics on the common forecast table (columns item_id, eval_stratum, cutoff, horizon, target_idx, lp_origin, pred, forecast, actual, y).
Primary accuracy metric: mean absolute error of the log price change (about the percentage error, comparable across items); Tk errors are reported alongside.
'Tomorrow = today' (naive) is pred = 0, so its error is |y| and it needs no separate forecast."""
import numpy as np, pandas as pd
from scipy import stats


def scored(fc):
    return fc[fc.y.notna()].copy()


def _row_metrics(g):
    e = g.pred - g.y
    ch = g.y != 0
    sa = np.sign(g.pred[ch]) == np.sign(g.y[ch])
    ek = g.forecast - g.actual
    sst = ((g.y - g.y.mean()) ** 2).sum()
    return pd.Series(dict(
        n=len(g), mae_log=e.abs().mean(), mae_log_naive=g.y.abs().mean(),
        mae_tk=ek.abs().mean(), rmse_tk=float(np.sqrt((ek ** 2).mean())), mape=float((ek.abs() / g.actual).mean()), bias_tk=ek.mean(), bias_log=e.mean(),
        direction_acc=float(sa.mean()) if ch.any() else np.nan, share_change_days=float(ch.mean()),
        mae_log_change_days=e[ch].abs().mean() if ch.any() else np.nan, mae_log_unchanged_days=e[~ch].abs().mean() if (~ch).any() else np.nan,
        r2_changes=1 - float((e ** 2).sum() / sst) if sst > 0 else np.nan))


def summary(fc, by=("horizon",)):
    s = scored(fc)
    t = s.groupby(list(by)).apply(_row_metrics, include_groups=False).reset_index()
    t["rel_mae_pooled"] = t.mae_log / t.mae_log_naive
    return t


def rel_mae_by_item(fc):
    """Per item and horizon: MAE of the model / MAE of 'tomorrow = today' (1.00 = tie). Geometric mean over items is the headline relative error."""
    s = scored(fc)
    g = s.groupby(["item_id", "horizon"]).apply(lambda x: pd.Series(dict(mae=(x.pred - x.y).abs().mean(), naive=x.y.abs().mean(), n=len(x))), include_groups=False).reset_index()
    g["rel"] = np.where(g.naive > 0, g.mae / g.naive, np.nan)
    return g


def gmean_rel(fc, by="horizon"):
    g = rel_mae_by_item(fc)
    g = g[(g.rel > 0) & np.isfinite(g.rel)]
    return g.groupby(by).rel.apply(lambda r: float(np.exp(np.log(r).mean()))).rename("gmean_rel_mae").reset_index()


def mase_scale(L, upto_idx):
    """Per item and horizon: mean |h-step change| of the reported price up to report day `upto_idx` (in-sample naive error)."""
    m = (L.target_idx <= upto_idx) & L.y.notna() & ~L.touch_gap & ~L.tgap
    return L[m].groupby(["item_id", "horizon"]).y.apply(lambda s: s.abs().mean()).rename("naive_scale").reset_index()


def dm_hln(e1, e2, h):
    """Diebold-Mariano on absolute loss with the Harvey-Leybourne-Newbold correction. Returns (stat, p); stat < 0 means model 1 is better."""
    d = np.abs(e1) - np.abs(e2); d = d[~np.isnan(d)]; n = len(d)
    if n < 8 or np.allclose(d, 0):
        return np.nan, np.nan
    q = max(int(np.ceil(h / 7)) - 1, 0)                                      # origins every 7 report days -> overlapping targets
    dc = d - d.mean(); g = [np.dot(dc[k:], dc[:n - k]) / n for k in range(q + 1)]
    v = (g[0] + 2 * sum(g[1:])) / n
    if v <= 0:
        return np.nan, np.nan
    dm = d.mean() / np.sqrt(v); k = np.sqrt((n + 1 - 2 * q + q * (q - 1) / n) / n)
    t = dm * k
    return float(t), float(2 * stats.t.sf(abs(t), df=n - 1))


def holm(p):
    p = np.asarray(p, float); m = np.isfinite(p).sum(); out = np.full_like(p, np.nan); idx = np.argsort(np.where(np.isfinite(p), p, np.inf)); run = 0
    for r, i in enumerate(idx[:m]):
        run = max(run, min(1, (m - r) * p[i])); out[i] = run
    return out


def dm_vs_naive(fc):
    """Per horizon, pooled over items (items averaged per origin): DM-HLN of the model against 'tomorrow = today'. Supporting evidence only."""
    s = scored(fc); rows = []
    for h, g in s.groupby("horizon"):
        d = g.assign(e_m=(g.pred - g.y), e_n=(0 - g.y)).groupby("cutoff")[["e_m", "e_n"]].apply(lambda x: pd.Series(dict(m=x.e_m.abs().mean(), n=x.e_n.abs().mean())), include_groups=False)
        t, p = dm_hln(d.m.values, d.n.values, h)        # losses are already absolute means; pass them as signed positives
        rows.append(dict(horizon=h, dm_stat=t, p_value=p, origins=len(d)))
    return pd.DataFrame(rows)


def pinball(y, q, tau):
    d = y - q
    return float(np.mean(np.maximum(tau * d, (tau - 1) * d)))


def winkler(y, lo, hi, alpha):
    w = hi - lo
    return float(np.mean(w + (2 / alpha) * np.maximum(lo - y, 0) + (2 / alpha) * np.maximum(y - hi, 0)))
