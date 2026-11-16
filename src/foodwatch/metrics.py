"""Accuracy metrics on the common forecast table (item_id, cutoff, horizon, target_idx, lp_origin, y, pred, forecast, actual, model).
Main metric: mean absolute error of the log price change (about the percentage error, comparable across items); Tk errors alongside.
"Tomorrow = today" is pred = 0, so its error is |y|. Ported from archive/old_pipeline/src/fpw/metrics.py."""
import numpy as np
import pandas as pd
from scipy import stats


def scored(fc):
    return fc[fc.y.notna()].copy()


def _row_metrics(g):
    e = g.pred - g.y
    ch = g.y != 0
    ek = g.forecast - g.actual
    mape = float((ek.abs() / g.actual).mean())
    return pd.Series(dict(n=len(g), mae_log=e.abs().mean(), mae_log_naive=g.y.abs().mean(), mae_tk=ek.abs().mean(),
                          mae_tk_naive=(np.exp(g.lp_origin) - g.actual).abs().mean(), mape=mape, accuracy=1 - mape,
                          accuracy_naive=1 - float(((np.exp(g.lp_origin) - g.actual).abs() / g.actual).mean()),
                          bias_log=e.mean(), share_change_days=float(ch.mean()),
                          direction_acc=float((np.sign(g.pred[ch]) == np.sign(g.y[ch])).mean()) if ch.any() else np.nan))


def summary(fc, by=("model", "horizon")):
    t = scored(fc).groupby(list(by)).apply(_row_metrics, include_groups=False).reset_index()
    t["rel_mae_pooled"] = t.mae_log / t.mae_log_naive
    return t


def rel_mae_by_item(fc, by=("model", "item_id", "horizon")):
    """Per item and horizon: MAE of the model / MAE of "tomorrow = today" (1.00 = tie)."""
    s = scored(fc)
    g = s.groupby(list(by)).apply(lambda x: pd.Series(dict(mae=(x.pred - x.y).abs().mean(), naive=x.y.abs().mean(), n=len(x))),
                                  include_groups=False).reset_index()
    g["rel"] = np.where(g.naive > 0, g.mae / g.naive, np.nan)
    return g


def gmean(r):
    r = r[(r > 0) & np.isfinite(r)]
    return float(np.exp(np.log(r).mean())) if len(r) else np.nan


def gmean_rel(fc, by=("model", "horizon")):
    """Geometric mean over items of the relative MAE (items whose naive error is 0 are left out)."""
    g = rel_mae_by_item(fc)
    return g.groupby(list(by)).rel.apply(gmean).rename("gmean_rel_mae").reset_index()


def dm_hln(e1, e2, h):
    """Diebold-Mariano on absolute loss with the Harvey-Leybourne-Newbold correction. (stat, p); stat < 0 means model 1 is better."""
    d = np.abs(e1) - np.abs(e2); d = d[~np.isnan(d)]; n = len(d)
    if n < 8 or np.allclose(d, 0):
        return np.nan, np.nan
    q = max(int(np.ceil(h / 7)) - 1, 0)                     # origins every 7 report days -> overlapping targets
    dc = d - d.mean(); gam = [np.dot(dc[k:], dc[:n - k]) / n for k in range(q + 1)]
    v = (gam[0] + 2 * sum(gam[1:])) / n
    if v <= 0:
        return np.nan, np.nan
    t = d.mean() / np.sqrt(v) * np.sqrt((n + 1 - 2 * q + q * (q - 1) / n) / n)
    return float(t), float(2 * stats.t.sf(abs(t), df=n - 1))


def holm(p):
    p = np.asarray(p, float); m = int(np.isfinite(p).sum()); out = np.full_like(p, np.nan); run = 0.0
    for r, i in enumerate(np.argsort(np.where(np.isfinite(p), p, np.inf))[:m]):
        run = max(run, min(1.0, (m - r) * p[i])); out[i] = run
    return out


def dm_vs_naive(fc):
    """Per model and horizon, items averaged per origin: DM-HLN against "tomorrow = today", Holm-corrected over all tests."""
    rows = []
    for (model, h), g in scored(fc).groupby(["model", "horizon"]):
        d = g.assign(em=(g.pred - g.y).abs(), en=g.y.abs()).groupby("cutoff")[["em", "en"]].mean()
        t, p = dm_hln(d.em.values, d.en.values, h)
        rows.append(dict(model=model, horizon=h, dm_stat=t, p_value=p, origins=len(d)))
    out = pd.DataFrame(rows)
    out["p_holm"] = holm(out.p_value.values)
    return out
