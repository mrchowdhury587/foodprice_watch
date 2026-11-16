"""Forecast benchmark (notebooks 04a, 04b): "tomorrow = today", ETS and one LightGBM for all 8 items and all horizons.

Ported from the earlier run (archive/old_pipeline/src/fpw/ml.py, cv.py, candidates.py), adapted to data_8.csv.
Each (item, report day) row is stacked once per horizon h; the target is the log price change from that report day to h report days
later; the forecast is today's price x exp(predicted change). Not recursive.

Rules:
- a target uses only an actually reported future price (never a blank, zero or carried one);
- the 2022 gap is history only: no input window and no target window may touch it; ETS is fitted only on the history after the gap;
- a model fitted for origin `cutoff` sees only rows whose target date is <= cutoff;
- inputs may carry the last reported price forward; targets never do.
"""
import itertools

import numpy as np
import pandas as pd

DRIVERS = ["month", "dow", "days_to_ramadan", "days_to_eid_fitr", "days_to_eid_adha", "in_ramadan", "days_since_prev_report",
           "wx_tmax_7d", "wx_tmean_30d", "wx_rain_7d", "fx_lvl", "fx_ch30"]
BASE_PARAMS = dict(min_data_in_leaf=50, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, verbose=-1, seed=42, num_threads=2)


def _at(F, col, offset):
    """Value of `col` for the same item `offset` report days later (negative = earlier); NaN when there is no row."""
    s = F.set_index(["item_id", "report_idx"])[col]
    return s.reindex(pd.MultiIndex.from_arrays([F.item_id.values, F.report_idx.values + offset])).values


def gap_bounds(D):
    gap = D.loc[D.gap_2022, "report_idx"]
    return (int(gap.min()), int(gap.max())) if len(gap) else (10 ** 9, -10 ** 9)


def prepare(D, horizons, lags, rolling, min_periods):
    """data_8 table -> modelling table: price-history inputs, targets y<h>, and flags for windows touching the 2022 gap."""
    F = D.sort_values(["item_id", "report_idx"]).reset_index(drop=True).copy()
    F["log_price"] = np.log(F.Price_Avg)                                  # NaN = not reported
    F["lp"] = F.groupby("item_id").log_price.ffill()                      # input only: last reported price carried forward
    for k in lags:
        F[f"r{k}"] = F.lp - _at(F, "lp", -k)
    g = F.groupby("item_id")
    for k in rolling:
        F[f"dev{k}"] = F.lp - g.lp.transform(lambda s: s.rolling(k, min_periods=min_periods).mean())
        F[f"vol{k}"] = g.r1.transform(lambda s: s.rolling(k, min_periods=min_periods).std())
    changed = (F.r1.fillna(0) != 0).astype(int)
    F["rsc"] = changed.groupby([F.item_id, changed.groupby(F.item_id).cumsum()]).cumcount()
    F["item_code"] = F.item_id.astype("category").cat.codes
    F["in_ramadan"] = F.in_ramadan.astype(int)
    gi = F.report_idx.values
    g0, g1 = gap_bounds(F)
    window = max(list(lags) + list(rolling))
    F["touch_gap"] = (gi >= g0) & (gi - window <= g1)
    for h in horizons:
        F[f"y{h}"] = _at(F, "log_price", h) - F.lp
        F[f"tgap{h}"] = (gi + h >= g0) & (gi <= g1)
    return F


def feature_columns(feature_set, lags, rolling):
    price = ["lp", *[f"r{k}" for k in lags], *[f"dev{k}" for k in rolling], *[f"vol{k}" for k in rolling], "rsc", "item_code", "horizon"]
    return price + (DRIVERS if feature_set == "price_plus_drivers" else [])


def stack(S, horizons):
    blocks = []
    for h in horizons:
        b = S.copy(); b["horizon"] = h; b["y"] = b[f"y{h}"]; b["tgap"] = b[f"tgap{h}"]; b["target_idx"] = b.report_idx + h
        blocks.append(b)
    return pd.concat(blocks, ignore_index=True)


def train_rows(L, cutoff):
    """Rows a model fitted for origin `cutoff` may learn from: target date <= cutoff, target reported, nothing touching the 2022 gap."""
    return L[(L.target_idx <= cutoff) & L.y.notna() & L.lp.notna() & ~L.touch_gap & ~L.tgap]


def origin_rows(L, cutoff):
    return L[(L.report_idx == cutoff) & L.lp.notna() & ~L.touch_gap & ~L.tgap]


def to_forecast(O, pred, model):
    f = O[["item_id", "report_idx", "horizon", "target_idx", "lp", "y"]].rename(columns={"report_idx": "cutoff", "lp": "lp_origin"}).copy()
    f["pred"] = np.asarray(pred, float)
    f["forecast"] = np.exp(f.lp_origin + f.pred)
    f["actual"] = np.where(f.y.notna(), np.exp(f.lp_origin + f.y), np.nan)
    f["model"] = model
    return f.reset_index(drop=True)


class Naive:
    def predict(self, X):
        return np.zeros(len(X))


def fit_naive(L, cutoff, cols):
    return Naive()


def make_fit_lgbm(params, rounds):
    def fit(L, cutoff, cols):
        import lightgbm as lgb
        tr = train_rows(L, cutoff)
        assert len(tr) and tr.target_idx.max() <= cutoff
        ds = lgb.Dataset(tr[cols], tr.y, categorical_feature=["item_code"], free_raw_data=False)
        return lgb.train(dict(BASE_PARAMS, **params), ds, num_boost_round=rounds)
    return fit


def rolling_forecasts(L, cutoffs, cols, fit_fn, refit_every, model):
    """A model is fitted at the first origin of each block of `refit_every` origins and reused inside the block."""
    out, m, start = [], None, None
    for i, c in enumerate(cutoffs):
        if m is None or i % refit_every == 0:
            m, start = fit_fn(L, c, cols), c
        O = origin_rows(L, c)
        if len(O):
            out.append(to_forecast(O, m.predict(O[cols]), model).assign(fit_cutoff=start))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def ets_forecasts(S, L, cutoffs, horizons, min_obs=30, model="ets"):
    """AutoETS (season_length=1) on each item's own carried log price after the 2022 gap, refitted at every origin."""
    from statsforecast import StatsForecast
    from statsforecast.models import AutoETS
    g1 = gap_bounds(S)[1]
    H, out = max(horizons), []
    for c in cutoffs:
        hist = S[(S.report_idx <= c) & (S.report_idx > g1) & S.lp.notna()].sort_values(["item_id", "report_idx"])
        Y = hist[["item_id", "lp"]].rename(columns={"item_id": "unique_id", "lp": "y"})
        Y["ds"] = Y.groupby("unique_id").cumcount() + 1
        n = Y.groupby("unique_id").ds.max()
        Y = Y[Y.unique_id.map(n) >= min_obs]
        f = StatsForecast(models=[AutoETS(season_length=1)], freq=1, n_jobs=1).forecast(df=Y[["unique_id", "ds", "y"]], h=H)
        f = f.reset_index() if "unique_id" not in f.columns else f
        f["step"] = f.ds - f.unique_id.map(n)
        O = origin_rows(L, c)
        for h in horizons:
            Oh = O[O.horizon == h]
            fh = f[f.step == h].set_index("unique_id")["AutoETS"]
            pred = Oh.item_id.map(fh).values - Oh.lp.values
            out.append(to_forecast(Oh, np.where(np.isnan(pred), 0.0, pred), model).assign(fit_cutoff=c))
    return pd.concat(out, ignore_index=True)


def period_origins(dates, start, end, step, max_h):
    """dates: Series report_idx -> Date. Weekly origins in [start, end] whose longest target still lies inside the period."""
    d = dates.sort_index()
    inside = d[(d >= pd.Timestamp(start)) & (d <= pd.Timestamp(end))]
    return list(range(int(inside.index.min()), int(inside.index.max()) - max_h + 1, step)) if len(inside) else []


def grid(spec):
    """All LightGBM configurations, simplest first (the order breaks ties)."""
    rows = []
    for fs, nl, lr, obj in itertools.product(spec["feature_sets"], sorted(spec["num_leaves"]), sorted(spec["learning_rate"]), spec["objective"]):
        rows.append(dict(config=f"{fs}|leaves{nl}|lr{lr}|{obj}", feature_set=fs, params=dict(num_leaves=nl, learning_rate=lr, objective=obj)))
    return rows


def choose(scores, order, margin):
    """scores: {config: overall relative MAE}. The best wins unless a config earlier in `order` is within `margin` (relative) of it."""
    best = min(scores, key=scores.get)
    close = [c for c in order if scores[c] <= scores[best] * (1 + margin)]
    return close[0]


def daily_h7(L, dates, cols, fit_fn, start, refit_every, h=7):
    """Horizon-h forecasts from every report day on or after `start` (outside the 2022 gap), for the alert ranges of notebook 05.
    The model is refitted every `refit_every` report days and only sees targets dated <= its fitting day."""
    days = sorted(int(i) for i in dates[dates >= pd.Timestamp(start)].index)
    Lh = L[L.horizon == h]
    out, m = [], None
    for i, c in enumerate(days):
        if m is None or i % refit_every == 0:
            m, start_c = fit_fn(L, c, cols), c
        O = origin_rows(Lh, c)
        if len(O):
            out.append(to_forecast(O, m.predict(O[cols]), "lgbm").assign(fit_cutoff=start_c))
    f = pd.concat(out, ignore_index=True)
    return f
