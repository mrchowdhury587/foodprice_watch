"""S24 Single-model design: ONE LightGBM for all items and all horizons.

Each (item, report day) row is stacked once per horizon h in {1, 7, 14, 30}; the target is the log price change from that
report day to h report days later; the forecast is today's price x exp(predicted change). Not recursive.

Rules enforced here (each has a unit test in tests/test_ml_design.py):
- a target uses only an actually reported future price (never a missing, zero or imputed one)
- the sparse 2022 period is history only: no feature window and no target window may touch it
- a model fitted for origin `cutoff` sees only rows whose target date is <= cutoff
- the price an input carries forward is the last reported price; targets are never carried forward
"""
import numpy as np, pandas as pd
from .project import PCFG

PRICE_HISTORY_NOTE = "lp, r<k>, dev<k>, vol<k>, rsc, item_code, stratum_code, horizon"


def settings():
    f = PCFG["features"]
    return dict(horizons=list(PCFG["horizons"]), lags=list(f["lags"]), rolling=list(f["rolling"]), min_periods=int(f["rolling_min_periods"]))


def _at(F, col, offset):
    """Value of `col` for the same item `offset` report days later (negative = earlier); NaN when that item has no row there."""
    s = F.set_index(["item_id", "report_idx"])[col]
    idx = pd.MultiIndex.from_arrays([F["item_id"].values, F["report_idx"].values + offset])
    return s.reindex(idx).values


def prepare(F, long_history_only=True, cfg=None):
    """Features-v2 table -> modelling table with price-history inputs and the four targets. Rows stay one per (item, report day)."""
    cfg = cfg or settings()
    assert 1 in cfg["lags"], "vol<k> is built from the 1-report change"
    F = F[~F.short_history] if long_history_only else F
    F = F.sort_values(["item_id", "report_idx"]).reset_index(drop=True).copy()
    F["lp"] = F.groupby("item_id").log_price.ffill()             # input only: the last reported price carried forward
    for k in cfg["lags"]:
        F[f"r{k}"] = F.lp - _at(F, "lp", -k)
    g = F.groupby("item_id")
    for k in cfg["rolling"]:
        F[f"dev{k}"] = F.lp - g.lp.transform(lambda s: s.rolling(k, min_periods=cfg["min_periods"]).mean())
        F[f"vol{k}"] = g.r1.transform(lambda s: s.rolling(k, min_periods=cfg["min_periods"]).std())
    changed = (F.r1.fillna(0) != 0).astype(int)
    F["rsc"] = changed.groupby([F.item_id, changed.groupby(F.item_id).cumsum()]).cumcount()    # reports since the price last changed
    F["item_code"] = F.item_id.astype("category").cat.codes
    F["stratum_code"] = F.eval_stratum.astype("category").cat.codes
    gi = F.report_idx.values
    gap = F.loc[F.gap_2022, "report_idx"]
    g0, g1 = (int(gap.min()), int(gap.max())) if len(gap) else (10**9, -10**9)
    window = max(cfg["lags"] + cfg["rolling"])
    F["touch_gap"] = (gi >= g0) & (gi - window <= g1)            # an input window overlaps the sparse 2022 period
    for h in cfg["horizons"]:
        F[f"y{h}"] = _at(F, "log_price", h) - F.lp               # NaN unless the future price was actually reported
        F[f"tgap{h}"] = (gi + h >= g0) & (gi <= g1)              # the target window overlaps the sparse 2022 period
    return F


def feature_columns(cfg=None, pcfg=None):
    """Model inputs in a fixed order: price history, calendar, weather, onion export measure, exchange rate (groups of config/project.yaml)."""
    cfg = cfg or settings(); pcfg = pcfg or PCFG
    grp = pcfg["features"]["groups"]
    price = ["lp"] + [f"r{k}" for k in cfg["lags"]] + [f"dev{k}" for k in cfg["rolling"]] + [f"vol{k}" for k in cfg["rolling"]] + ["rsc", "item_code", "stratum_code", "horizon"]
    return price + list(grp["calendar"]) + list(grp["weather"]) + list(grp["onion_export_measures"]) + list(grp["exchange_rate"])


def group_of(cols, pcfg=None):
    """Feature -> driver group name, for the explanation step."""
    pcfg = pcfg or PCFG
    cfg = settings(); out = {}
    price = set(["lp"] + [f"r{k}" for k in cfg["lags"]] + [f"dev{k}" for k in cfg["rolling"]] + [f"vol{k}" for k in cfg["rolling"]] + ["rsc", "item_code", "stratum_code", "horizon"])
    for c in cols:
        if c in price: out[c] = "price_history"
        else:
            for name, members in pcfg["features"]["groups"].items():
                if c in members: out[c] = name
    return out


def stack(S, horizons=None):
    """One block per horizon: columns horizon, y (target change), tgap (target window touches the 2022 gap)."""
    horizons = horizons or settings()["horizons"]
    blocks = []
    for h in horizons:
        b = S.copy(); b["horizon"] = h; b["y"] = b[f"y{h}"]; b["tgap"] = b[f"tgap{h}"]; b["target_idx"] = b.report_idx + h
        blocks.append(b)
    return pd.concat(blocks, ignore_index=True)


def train_rows(L, cutoff):
    """Rows a model fitted for origin `cutoff` may learn from: target date <= cutoff, target reported, nothing touching the 2022 gap."""
    m = (L.target_idx <= cutoff) & L.y.notna() & L.lp.notna() & ~L.touch_gap & ~L.tgap
    return L[m]


PARAMS = dict(objective="l1", learning_rate=0.05, num_leaves=31, min_data_in_leaf=50, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1,
              verbose=-1, seed=42, num_threads=2)
N_ESTIMATORS = 300


def fit(L, cutoff, cols, params=None, n_estimators=None):
    import lightgbm as lgb
    tr = train_rows(L, cutoff)
    assert len(tr), f"no training rows for cutoff {cutoff}"
    p = dict(PARAMS, **(params or {})); n = n_estimators or p.pop("n_estimators", None) or N_ESTIMATORS; p.pop("n_estimators", None)
    ds = lgb.Dataset(tr[cols], tr["y"], categorical_feature=[c for c in ["item_code", "stratum_code"] if c in cols], free_raw_data=False)
    return lgb.train(p, ds, num_boost_round=n)


def origin_rows(L, cutoff):
    """Rows to forecast from: every item reported or carried at report day `cutoff`; the input price must exist."""
    return L[(L.report_idx == cutoff) & L.lp.notna() & ~L.touch_gap]


def to_forecast(O, pred, model_name):
    """Common forecast table for every candidate: change, price forecast and (when reported) the actual change."""
    f = O[["item_id", "eval_stratum", "report_idx", "horizon", "target_idx", "lp", "y"]].copy()
    f = f.rename(columns={"report_idx": "cutoff", "lp": "lp_origin"})
    f["pred"] = np.asarray(pred, float)
    f["forecast"] = np.exp(f.lp_origin + f.pred)
    f["actual"] = np.where(f.y.notna(), np.exp(f.lp_origin + f.y), np.nan)
    f["model"] = model_name
    return f.reset_index(drop=True)


def forecasts(L, cutoffs, cols, refit_every=8, params=None, n_estimators=None, model_name="lgbm", fit_fn=None):
    """Rolling-origin forecasts from the stacked table L. A model is fitted at the first cutoff of each block of `refit_every` origins and
    reused inside the block; it only saw rows whose target date is <= that first cutoff, so nothing leaks.
    fit_fn(L, cutoff, cols) -> object with .predict(DataFrame); the default is the LightGBM model above. Returns the common forecast table."""
    fit_fn = fit_fn or (lambda L_, c, cols_: fit(L_, c, cols_, params, n_estimators))
    out, model, start = [], None, None
    for i, c in enumerate(cutoffs):
        if model is None or i % refit_every == 0:
            model, start = fit_fn(L, c, cols), c
        O = origin_rows(L, c)
        if len(O):
            out.append(to_forecast(O, model.predict(O[cols]), model_name).assign(fit_cutoff=start))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()
