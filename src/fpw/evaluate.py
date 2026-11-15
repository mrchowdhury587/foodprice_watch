"""S27 evaluation tables and figures on the common forecast table (see fpw.metrics). Pure functions: they read frames, return frames."""
import numpy as np, pandas as pd
from . import metrics as M


def gmean_rel_by(fc, strata, keys):
    """Geometric mean over items of (model MAE / naive MAE), grouped by `keys` (any of horizon, eval_stratum)."""
    g = M.rel_mae_by_item(fc).merge(strata, on="item_id")
    g = g[(g.rel > 0) & np.isfinite(g.rel)]
    return g.groupby(list(keys)).rel.apply(lambda r: float(np.exp(np.log(r).mean()))).rename("gmean_rel_mae").reset_index()


def by_horizon(fc, strata):
    return M.summary(fc, by=["horizon"]).merge(gmean_rel_by(fc, strata, ["horizon"]), on="horizon")


def by_group(fc, strata):
    return M.summary(fc, by=["eval_stratum", "horizon"]).merge(gmean_rel_by(fc, strata, ["eval_stratum", "horizon"]), on=["eval_stratum", "horizon"])


def by_item(fc, scale):
    """Per item and horizon, with MASE (log-change MAE over the item's in-sample naive error)."""
    t = M.summary(fc, by=["item_id", "horizon"]).merge(scale, on=["item_id", "horizon"], how="left")
    t["mase"] = t.mae_log / t.naive_scale
    return t


def tag(fc, dates, cal):
    """Adds origin date, target date, month, a Ramadan/Eid flag, direction of the actual move and an era flag (before/after mid-2024)."""
    f = M.scored(fc)
    f["origin_date"] = f.cutoff.map(dates); f["target_date"] = f.target_idx.map(dates)
    c = cal.reindex(f.cutoff.values)
    f["ramadan_or_eid"] = np.where((c.in_ramadan.values == 1) | (c.days_to_eid_fitr.values <= 14) | (c.days_to_eid_adha.values <= 14), "ramadan/eid window", "normal")
    f["direction"] = np.where(f.y > 0, "rising", np.where(f.y < 0, "falling", "unchanged"))
    f["era"] = np.where(f.origin_date < pd.Timestamp("2024-07-01"), "before mid-2024", "from mid-2024")
    f["month"] = f.target_date.dt.month
    return f


def error_analysis(tagged):
    out = []
    for col in ["ramadan_or_eid", "direction", "era", "month"]:
        t = tagged.groupby([col, "horizon"]).apply(M._row_metrics, include_groups=False).reset_index().rename(columns={col: "level"})
        t.insert(0, "split", col); out.append(t[["split", "level", "horizon", "n", "mae_log", "mae_log_naive", "bias_log", "mae_tk"]])
    return pd.concat(out, ignore_index=True)


def worst(tagged, k=20):
    t = tagged.assign(abs_err_log=(tagged.pred - tagged.y).abs())
    return t.sort_values("abs_err_log", ascending=False).head(k)[["item_id", "horizon", "origin_date", "target_date", "pred", "y", "forecast", "actual", "abs_err_log"]]


def bias_over_time(tagged, horizon=7):
    t = tagged[tagged.horizon == horizon].groupby("origin_date").apply(lambda x: pd.Series(dict(bias_log=(x.pred - x.y).mean(), mae_log=(x.pred - x.y).abs().mean(), n=len(x))), include_groups=False)
    return t.reset_index()


def learning_curve(L, cutoff, cols, params, n_estimators, holdout_share=0.15):
    """Train and holdout L1 by number of trees. The holdout is the most recent share of report days available at `cutoff`; training stops before it (no overlap in time)."""
    import lightgbm as lgb
    from . import ml
    tr = ml.train_rows(L, cutoff)
    split = int(tr.report_idx.quantile(1 - holdout_share))
    a, b = tr[tr.target_idx < split], tr[tr.report_idx >= split]
    p = dict(ml.PARAMS, **(params or {})); p.pop("n_estimators", None); p["metric"] = "l1"
    cat = [c for c in ["item_code", "stratum_code"] if c in cols]
    da = lgb.Dataset(a[cols], a["y"], categorical_feature=cat, free_raw_data=False)
    db = lgb.Dataset(b[cols], b["y"], categorical_feature=cat, reference=da, free_raw_data=False)
    res = {}
    lgb.train(p, da, num_boost_round=n_estimators, valid_sets=[da, db], valid_names=["train", "holdout"], callbacks=[lgb.record_evaluation(res)])
    return pd.DataFrame(dict(trees=np.arange(1, n_estimators + 1), train_l1=res["train"]["l1"], holdout_l1=res["holdout"]["l1"]))


def figures(tagged, h_table, curve, bias, outdir, key_items=("Onion", "Rice", "Egg", "Potato", "Sugar")):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    outdir.mkdir(parents=True, exist_ok=True); paths = []
    fig, ax = plt.subplots(figsize=(6, 3.5)); ax.bar(h_table.horizon.astype(str), h_table.gmean_rel_mae, color="#4c78a8"); ax.axhline(1, color="k", lw=1)
    ax.set_xlabel("horizon (report days)"); ax.set_ylabel("error relative to tomorrow = today"); ax.set_title("Relative error by horizon (1.0 = tie)")
    paths.append(outdir / "F10_relative_error_by_horizon.png"); fig.tight_layout(); fig.savefig(paths[-1], dpi=150); plt.close(fig)
    h7 = tagged[tagged.horizon == 7]
    fig, ax = plt.subplots(figsize=(6, 3.5)); ax.hist((h7.pred - h7.y).clip(-0.3, 0.3), bins=60, color="#4c78a8"); ax.set_xlabel("forecast error of the log change (7 reports ahead)")
    ax.set_ylabel("count"); ax.set_title("Error distribution")
    paths.append(outdir / "F11_error_distribution.png"); fig.tight_layout(); fig.savefig(paths[-1], dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(7, 3.5)); ax.plot(bias.origin_date, bias.bias_log.rolling(4, min_periods=1).mean(), color="#e45756"); ax.axhline(0, color="k", lw=1)
    ax.set_ylabel("mean error (pred - actual), log"); ax.set_title("Bias over time (7 reports ahead, 4-origin mean)")
    paths.append(outdir / "F12_bias_over_time.png"); fig.tight_layout(); fig.savefig(paths[-1], dpi=150); plt.close(fig)
    fig, ax = plt.subplots(figsize=(6, 3.5)); ax.plot(curve.trees, curve.train_l1, label="training"); ax.plot(curve.trees, curve.holdout_l1, label="holdout"); ax.legend()
    ax.set_xlabel("number of trees"); ax.set_ylabel("mean absolute error (log change)"); ax.set_title("Learning curve")
    paths.append(outdir / "F13_learning_curve.png"); fig.tight_layout(); fig.savefig(paths[-1], dpi=150); plt.close(fig)
    items = [i for k in key_items for i in sorted(h7.item_id.unique()) if i.startswith(k)][:5]
    if items:
        fig, axes = plt.subplots(len(items), 1, figsize=(8, 2.2 * len(items)), sharex=True)
        for ax, it in zip(np.atleast_1d(axes), items):
            g = h7[h7.item_id == it].sort_values("target_date"); ax.plot(g.target_date, g.actual, label="actual", color="k", lw=1); ax.plot(g.target_date, g.forecast, label="forecast", color="#e45756", lw=1)
            ax.set_title(it, fontsize=8); ax.tick_params(labelsize=7)
        np.atleast_1d(axes)[0].legend(fontsize=7); paths.append(outdir / "F14_actual_vs_forecast.png"); fig.tight_layout(); fig.savefig(paths[-1], dpi=130); plt.close(fig)
    return paths
