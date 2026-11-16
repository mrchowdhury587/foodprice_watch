"""Abnormal-rise alert rules (notebooks 05a, 05b). Alerts are abnormal-rise DETECTION, not early warning.

For every report day t the actual price is compared with the forecast made h report days earlier (origin t-h).
  A. ML range:     the LightGBM error y - pred is above the item's quantile `level` of its last `window` known errors;
  B. simple range: the same on the "tomorrow = today" forecast (pred = 0), so the error is the h-report log change itself;
  C. fixed threshold: the h-report change is at least `threshold` (same for all items).
An error is "known" at origin o only if its target is <= o (the error of origin o-h). An alert is on when the bound was
exceeded on at least k of the item's last m report days; an alert run starts on the first day of an uninterrupted alert.
Runs are matched one-to-one with the sustained rise episodes of notebook 03 (ported from archive/old_pipeline/src/fpw/rises.py).
"""
import numpy as np
import pandas as pd
from scipy import stats


def table(F7, model, horizon):
    """One row per item and target day for one model: resid = actual h-report log change - predicted change."""
    P = F7[(F7.model == model) & (F7.horizon == horizon)].sort_values(["item_id", "cutoff"]).reset_index(drop=True).copy()
    P["resid"] = P.y - P.pred
    P["tdate"] = pd.to_datetime(P.target_date)
    return P


def consecutive(P):
    """True if every item has one row per report day (needed for 'shift by h rows = h report days')."""
    return bool((P.groupby("item_id").cutoff.diff().dropna() == 1).all())


def bounds(P, horizon, levels, window, min_obs):
    """Adds hi<level>: quantile of the item's last `window` known errors (errors of origins <= cutoff - horizon)."""
    P = P.copy()
    known = P.groupby("item_id").resid.shift(horizon)
    for lv in levels:
        P[f"hi{lv}"] = known.groupby(P.item_id).transform(lambda s, q=lv: s.rolling(window, min_periods=min_obs).quantile(q))
    return P


def flag(P, exceed, k, m):
    """Alert on a target day: the bound was exceeded on at least k of the item's last m report days."""
    e = exceed.fillna(False).astype(float)
    return e.groupby(P.item_id).transform(lambda s: s.rolling(m, min_periods=1).sum()) >= k


def range_alerts(P, level, k, m):
    ex = (P.resid > P[f"hi{level}"]) & P[f"hi{level}"].notna() & P.resid.notna()
    return ex, flag(P, ex, k, m)


def threshold_alerts(P, threshold, k, m):
    ex = P.y >= np.log1p(threshold)
    return ex, flag(P, ex, k, m)


def runs(P, on):
    """Alert runs: item, start report day (target_idx) and date of the first day of each uninterrupted alert."""
    on = on.fillna(False).astype(bool)
    prev = on.groupby(P.item_id).shift(1, fill_value=False)
    st = P[on & ~prev]
    return pd.DataFrame({"item_id": st.item_id.values, "start_idx": st.target_idx.values.astype(int), "start_date": st.tdate.values})


def in_period(df, col, period):
    return df[(pd.to_datetime(df[col]) >= pd.Timestamp(period[0])) & (pd.to_datetime(df[col]) <= pd.Timestamp(period[1]))]


def match(rn, eps, before, after):
    """One-to-one: each episode (in time order) takes the earliest unmatched run of the same item starting from `before` report days
    before the onset to `after` report days after the end. Returns (episodes with detected, delay_reports; runs with matched)."""
    eps = eps.sort_values(["onset_idx", "item_id"]).reset_index(drop=True).copy()
    rn = rn.reset_index(drop=True).copy()
    rn["matched"] = False; eps["detected"] = False; eps["delay_reports"] = np.nan
    for i, e in eps.iterrows():
        c = rn[(rn.item_id == e.item_id) & ~rn.matched & (rn.start_idx >= e.onset_idx - before) & (rn.start_idx <= e.end_idx + after)].sort_values("start_idx")
        if len(c):
            rn.loc[c.index[0], "matched"] = True; eps.loc[i, "detected"] = True; eps.loc[i, "delay_reports"] = float(c.start_idx.iloc[0] - e.onset_idx)
    return eps, rn


def prf(eps, rn, item_years):
    rec = float(eps.detected.mean()) if len(eps) else np.nan
    pre = float(rn.matched.mean()) if len(rn) else np.nan
    f1 = 2 * pre * rec / (pre + rec) if np.isfinite(pre) and np.isfinite(rec) and (pre + rec) > 0 else np.nan
    return dict(episodes=int(len(eps)), detected=int(eps.detected.sum()), recall=rec, alert_runs=int(len(rn)), matched_runs=int(rn.matched.sum()),
                precision=pre, f1=f1, median_delay_reports=float(eps.delay_reports.median()) if eps.detected.any() else np.nan,
                runs_per_item_year=len(rn) / item_years, unmatched_per_item_year=int((~rn.matched).sum()) / item_years)


def item_years(P, period, days_per_year=250.0):
    """Item-years of scorable report days (target days with a bound or a change) inside the period."""
    d = in_period(P, "tdate", period)
    return float(d.groupby("item_id").tdate.nunique().sum() / days_per_year)


def choose(values, order, target):
    """values: {setting: unmatched runs per item-year}. The first setting in `order` (most sensitive first) at or below the target;
    if none, the last (strictest)."""
    ok = [s for s in order if np.isfinite(values[s]) and values[s] <= target]
    return (ok[0], True) if ok else (order[-1], False)


def placebo(rn, eps, before, after, lo, hi, draws=300, seed=42):
    """Random-date control: each item's alert runs are shifted by one random number of report days (wrapping inside [lo, hi]);
    recall is recomputed. Returns observed recall, mean placebo recall and p (share of draws at least as high, +1 corrected)."""
    rng = np.random.default_rng(seed); span = hi - lo + 1
    obs = match(rn, eps, before, after)[0].detected.mean()
    out = []
    for _ in range(draws):
        sh = rn.copy(); off = {it: int(rng.integers(1, span)) for it in sh.item_id.unique()}
        sh["start_idx"] = lo + (sh.start_idx - lo + sh.item_id.map(off)) % span
        out.append(match(sh, eps, before, after)[0].detected.mean())
    out = np.array(out)
    return dict(placebo_recall=float(out.mean()), placebo_p=float(((out >= obs).sum() + 1) / (draws + 1)))


def overlap(eA, eB):
    """Episodes caught by both rules, by one only, by neither (same episode list)."""
    k = ["item_id", "onset_idx"]
    m = eA[k + ["detected"]].merge(eB[k + ["detected"]], on=k, suffixes=("_A", "_B"))
    return dict(episodes=len(m), both=int((m.detected_A & m.detected_B).sum()), A_only=int((m.detected_A & ~m.detected_B).sum()),
                B_only=int((~m.detected_A & m.detected_B).sum()), neither=int((~m.detected_A & ~m.detected_B).sum()))


def kupiec(n_exc, n, p):
    """Kupiec proportion-of-failures test: p-value that the exceedance rate equals p."""
    if n == 0:
        return np.nan
    x, ph = n_exc, n_exc / n
    ll1 = 0.0 if x in (0, n) else x * np.log(ph) + (n - x) * np.log(1 - ph)
    ll0 = x * np.log(p) + (n - x) * np.log(1 - p)
    return float(stats.chi2.sf(-2 * (ll0 - ll1), 1))


def coverage(P, level, period):
    """Share of target days at or below the upper bound against the nominal level, and the Kupiec p."""
    d = in_period(P[P.resid.notna() & P[f"hi{level}"].notna()], "tdate", period)
    below = d.resid <= d[f"hi{level}"]
    return dict(n=len(d), nominal=level, coverage=float(below.mean()) if len(d) else np.nan, kupiec_p=kupiec(int((~below).sum()), len(d), 1 - level))
