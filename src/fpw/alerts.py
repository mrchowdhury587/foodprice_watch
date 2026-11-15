"""S28 Ranges and the alert rule on daily rolling forecasts. Alerts are abnormal-rise DETECTION, not early warning.

For every report day the actual price is compared with the forecast made h report days earlier. The expected range of a forecast is built from the
item's own last `window` forecast errors that were already known when the forecast was made (target date <= origin). An alert starts when the price is above
the upper bound on k of the last m report days. The level is chosen on 2024 periods outside the event windows; the 12 shock episodes are only scored afterwards."""
import numpy as np, pandas as pd
from scipy import stats


def bounds(fc, horizon, levels, window, min_obs):
    """Per item, for one horizon: quantile bounds of the log forecast error. Rows are origins (one per report day); the error of origin o-h has its target at o,
    so at origin o only errors up to row o-h are used. Adds resid, hi<level> (upper) and lo<level> (lower = quantile 1-level)."""
    P = fc[fc.horizon == horizon].sort_values(["item_id", "cutoff"]).reset_index(drop=True)
    P["resid"] = P.y - P.pred                                      # NaN where the target price was not reported
    known = P.groupby("item_id").resid.shift(horizon)
    for lv in levels:
        for name, q in ((f"hi{lv}", lv), (f"lo{lv}", 1 - lv)):
            P[name] = known.groupby(P.item_id).transform(lambda s, q=q: s.rolling(window, min_periods=min_obs).quantile(q))
    return P


def flag_alerts(P, levels, k, m):
    """exceed<level>: the error is above the upper bound; alert<level>: exceeded on at least k of the last m report days of the item."""
    P = P.copy()
    for lv in levels:
        e = (P.resid > P[f"hi{lv}"]) & P[f"hi{lv}"].notna()
        P[f"exceed{lv}"] = e
        P[f"alert{lv}"] = e.astype(float).groupby(P.item_id).transform(lambda s: s.rolling(m, min_periods=1).sum()) >= k
    return P


def episodes(P, col):
    """First report day of each uninterrupted alert run, per item."""
    on = P[col].fillna(False).astype(bool)
    prev = on.groupby(P.item_id).shift(1, fill_value=False)
    return P[on & ~prev]


def end_dates(P, col):
    """For each alert run: last report day of the run."""
    on = P[col].fillna(False).astype(bool); run = (on & ~on.groupby(P.item_id).shift(1, fill_value=False)).groupby(P.item_id).cumsum().where(on)
    return P[on].assign(run=run[on]).groupby(["item_id", "run"]).tdate.agg(["min", "max", "size"]).reset_index()


def load_events(path):
    e = pd.read_csv(path)
    e = e[e.in_window.astype(str).str.lower() == "true"].copy()
    for c in ["onset", "news_peak", "end"]:
        e[c] = pd.to_datetime(e[c])
    return e.reset_index(drop=True)


def windows(ev, items_of_product, before, after):
    """Event windows per affected item: `before` days before the onset to `after` days after the news peak."""
    rows = []
    for r in ev.itertuples():
        for it in items_of_product.get(r.product, []):
            rows.append(dict(event_id=r.event_id, product=r.product, item_id=it, onset=r.onset, news_peak=r.news_peak,
                             w0=r.onset - pd.Timedelta(days=before), w1=max(r.news_peak, r.onset) + pd.Timedelta(days=after)))
    return pd.DataFrame(rows)


def in_any_window(df, W):
    if W.empty:
        return pd.Series(False, index=df.index)
    m = df[["item_id", "tdate"]].reset_index().merge(W[["item_id", "w0", "w1"]], on="item_id")
    hit = m[(m.tdate >= m.w0) & (m.tdate <= m.w1)]["index"].unique()
    return pd.Series(df.index.isin(hit), index=df.index)


def false_alarms_per_item_year(P, col, W, start, end, days_per_year=250.0):
    """Alert runs that start outside every event window, per item-year of non-event report days, within [start, end]."""
    d = P[(P.tdate >= pd.Timestamp(start)) & (P.tdate <= pd.Timestamp(end))].copy()
    d["inwin"] = in_any_window(d, W)
    st = episodes(d, col); st = st.assign(inwin=d.loc[st.index, "inwin"])
    years = d[~d.inwin].groupby("item_id").tdate.nunique() / days_per_year
    fa = st[~st.inwin].groupby("item_id").size().reindex(years.index, fill_value=0)
    return float(fa.sum() / years.sum()) if years.sum() > 0 else np.nan


def choose_level(P, levels, W, target, start="2024-01-01", end="2024-12-31"):
    """The most sensitive (lowest) level whose false alarms per item-year in 2024 outside the event windows stay at or below the target."""
    fa = {lv: false_alarms_per_item_year(P, f"alert{lv}", W, start, end) for lv in levels}
    ok = [lv for lv in sorted(levels) if np.isfinite(fa[lv]) and fa[lv] <= target]
    level = ok[0] if ok else max(levels)
    rule = (f"lowest level with at most {target} false alarms per item-year in 2024 outside the event windows" if ok
            else f"no level reached {target} false alarms per item-year in 2024; the highest level is used")
    return level, rule, {str(lv): round(float(v), 3) for lv, v in fa.items()}


def score_events(P, col, W, ev):
    """Per event: detected when an alert run starts inside the window of any affected item; lead = first such start minus the news peak (days, negative = before)."""
    st = episodes(P, col)[["item_id", "tdate"]]
    rows = []
    for r in ev.itertuples():
        w = W[W.event_id == r.event_id]
        s = st.merge(w[["item_id", "w0", "w1", "news_peak"]], on="item_id")
        s = s[(s.tdate >= s.w0) & (s.tdate <= s.w1)].sort_values("tdate")
        rows.append(dict(event_id=r.event_id, product=r.product, onset=r.onset, news_peak=r.news_peak, items=int(len(w)),
                         detected=bool(len(s)), first_alert=s.tdate.iloc[0] if len(s) else pd.NaT, lead_days_vs_news_peak=int((s.tdate.iloc[0] - s.news_peak.iloc[0]).days) if len(s) else np.nan))
    return pd.DataFrame(rows)


def precision(P, col, W):
    """Share of alert runs that start inside an event window (a run outside every window is a false alarm)."""
    st = episodes(P, col); inwin = in_any_window(P, W).loc[st.index]
    return float(inwin.mean()) if len(st) else np.nan, int(len(st))


def placebo(P, col, W, ev, draws=300, seed=42):
    """Random-date control: shift each event's windows (all affected items together) to a random start inside the evaluation period and count detections."""
    rng = np.random.default_rng(seed)
    st = episodes(P, col)[["item_id", "tdate"]]; days = np.sort(P.tdate.dropna().unique()); n = len(days)
    real = score_events(P, col, W, ev).detected.mean()
    out = []
    for _ in range(draws):
        hit = 0
        for r in ev.itertuples():
            w = W[W.event_id == r.event_id]
            if w.empty: continue
            span = (w.w1.iloc[0] - w.w0.iloc[0]).days; new0 = pd.Timestamp(days[rng.integers(0, max(n - 1, 1))])
            s = st.merge(w[["item_id"]].drop_duplicates(), on="item_id"); hit += bool(((s.tdate >= new0) & (s.tdate <= new0 + pd.Timedelta(days=span))).any())
        out.append(hit / max(len(ev), 1))
    out = np.array(out)
    return dict(observed_recall=float(real), placebo_mean=float(out.mean()), placebo_p=float(((out >= real).sum() + 1) / (draws + 1)), draws=draws)


def kupiec(n_exc, n, p):
    """Kupiec proportion-of-failures test: p-value that the exceedance rate equals p."""
    if n == 0: return np.nan
    x, ph = n_exc, n_exc / n
    ll1 = 0.0 if x in (0, n) else x * np.log(ph) + (n - x) * np.log(1 - ph)
    ll0 = x * np.log(p) + (n - x) * np.log(1 - p)
    return float(stats.chi2.sf(-2 * (ll0 - ll1), 1))


def range_quality(P, level, by=("horizon",)):
    """Coverage of the upper bound and of the central interval, average width (log and Tk), pinball loss at the upper tau, Winkler score of the interval."""
    d = P[P.resid.notna() & P[f"hi{level}"].notna()].copy()
    d["below_hi"] = d.resid <= d[f"hi{level}"]; d["inside"] = d.below_hi & (d.resid >= d[f"lo{level}"])
    d["width_log"] = d[f"hi{level}"] - d[f"lo{level}"]; d["width_tk"] = np.exp(d.lp_origin + d.pred) * (np.exp(d[f"hi{level}"]) - np.exp(d[f"lo{level}"]))
    rows = []
    for key, g in d.groupby(list(by)):
        key = key if isinstance(key, tuple) else (key,)
        a = 1 - (2 * level - 1) if level > 0.5 else 0.05
        rows.append(dict(zip(by, key), n=len(g), nominal_upper=level, upper_coverage=float(g.below_hi.mean()), interval_coverage=float(g.inside.mean()),
                         mean_width_log=float(g.width_log.mean()), mean_width_tk=float(g.width_tk.mean()),
                         pinball_upper=float(np.mean(np.maximum(level * (g.resid - g[f"hi{level}"]), (level - 1) * (g.resid - g[f"hi{level}"])))),
                         winkler=float(np.mean(g.width_log + (2 / a) * np.maximum(g[f"lo{level}"] - g.resid, 0) + (2 / a) * np.maximum(g.resid - g[f"hi{level}"], 0))),
                         kupiec_p=kupiec(int((~g.below_hi).sum()), len(g), 1 - level)))
    return pd.DataFrame(rows)
