"""Driver features of the prediction system (stage S23): calendar, weather, India onion export measures, exchange rate.

Same rules and formulas as the earlier S04 (src/stages/s04.py, left unchanged), reduced to the drivers that are kept.
Every function takes frames and returns frames, so each rule can be tested on a small made-up input.

Leakage rule: a driver value may be used on report day t only if it was published on or before t.
  weather: day d is usable from d + lag_days (5); exchange rate: the last value dated on or before t.
  A value older than cap_days at t is left empty (not carried further). Missing stays empty, never 0.
"""
import numpy as np, pandas as pd

CAL = ["month", "dow", "days_to_ramadan", "days_to_eid_fitr", "days_to_eid_adha", "in_ramadan", "holiday_next7", "days_since_prev_report"]
WEATHER_CANDIDATES = ["wx_bd_rain_7d", "wx_bd_rain_30d", "wx_bd_tmax_7d", "wx_bd_tmean_30d", "wx_bd_soilm_30d", "wx_nashik_rain_30d"]


def asof(dates, src, valcols, cap_days):
    """For each report date: the last row of src with available <= Date; empty if that row is older than cap_days.
    dates: frame with a sorted Date column. src: frame with `available` and valcols."""
    s = src.sort_values("available")[["available", *valcols]].dropna(subset=valcols, how="all")
    out = pd.merge_asof(dates[["Date"]], s, left_on="Date", right_on="available", direction="backward")
    stale = (out.Date - out.available).dt.days > cap_days
    out.loc[stale, valcols] = np.nan
    return out


def days_to_next(ds, ev):
    ev = np.sort(pd.to_datetime(pd.Series(ev)).values); idx = np.searchsorted(ev, ds.values)
    nxt = np.where(idx < len(ev), ev[np.minimum(idx, len(ev) - 1)], np.datetime64("NaT"))
    return (pd.to_datetime(nxt) - ds).dt.days


def calendar(dates, ramadan_eid, holidays):
    """Known in advance. ramadan_eid: columns ramadan_start, eid_ul_fitr, eid_ul_adha (';' separates two dates in one year).
    holidays: a series of dates."""
    re_ = ramadan_eid.copy()
    adha = pd.to_datetime(re_.eid_ul_adha.astype(str).str.split(";").explode().str.strip())
    for c in ["ramadan_start", "eid_ul_fitr"]: re_[c] = pd.to_datetime(re_[c])
    hol = pd.to_datetime(pd.Series(holidays))
    cal = dates[["Date"]].copy()
    cal["month"] = cal.Date.dt.month; cal["dow"] = cal.Date.dt.dayofweek
    cal["days_to_ramadan"] = days_to_next(cal.Date, re_.ramadan_start)
    cal["days_to_eid_fitr"] = days_to_next(cal.Date, re_.eid_ul_fitr)
    cal["days_to_eid_adha"] = days_to_next(cal.Date, adha)
    cal["in_ramadan"] = False
    for r in re_.itertuples(): cal.loc[cal.Date.between(r.ramadan_start, r.eid_ul_fitr - pd.Timedelta(days=1)), "in_ramadan"] = True
    cal["holiday_next7"] = [int(((hol > d) & (hol <= d + pd.Timedelta(days=7))).sum()) for d in cal.Date]
    cal["days_since_prev_report"] = cal.Date.diff().dt.days
    return cal


def weather_candidates(w, lag_days):
    """w: Open-Meteo rows (location_id, time, precipitation_sum, temperature_2m_max, temperature_2m_mean,
    soil_moisture_0_to_7cm_mean, relative_humidity_2m_mean). Locations 0-10 = Bangladesh, 12 = Nashik (India's onion belt).
    Returns daily rolling features with `available` = last day in the window + lag_days."""
    bd = w[w.location_id <= 10].groupby("time").agg(rain=("precipitation_sum", "mean"), tmax=("temperature_2m_max", "mean"),
            tmean=("temperature_2m_mean", "mean"), soilm=("soil_moisture_0_to_7cm_mean", "mean"))
    nas = w[w.location_id == 12].set_index("time").precipitation_sum.rename("nashik_rain")
    bd = bd.join(nas).asfreq("D")
    cand = pd.DataFrame({"wx_bd_rain_7d": bd.rain.rolling(7).sum(), "wx_bd_rain_30d": bd.rain.rolling(30).sum(), "wx_bd_tmax_7d": bd.tmax.rolling(7).mean(),
                         "wx_bd_tmean_30d": bd.tmean.rolling(30).mean(), "wx_bd_soilm_30d": bd.soilm.rolling(30).mean(), "wx_nashik_rain_30d": bd.nashik_rain.rolling(30).sum()})
    cand["available"] = cand.index + pd.Timedelta(days=lag_days)
    return cand.reset_index(drop=True)


def fx_table(fx):
    """fx: columns date, bdt_per_usd (spliced series from fpw.drivers.fx). Adds log level and change over 30 calendar days."""
    fx = fx.sort_values("date").copy()
    fx["fx_lvl"] = np.log(fx.bdt_per_usd)
    fx["fx_ch30"] = fx.fx_lvl - fx.set_index("date").fx_lvl.shift(30, freq="D").reindex(fx.date).values
    fx["available"] = fx.date
    return fx


def event_active(F, events, items_by_key, keycol="item"):
    """1 while a listed measure is in force, 0 otherwise inside the table's coverage, empty outside it (unknown) and for unmapped items."""
    ex = events.copy(); ex["start"] = pd.to_datetime(ex.start); ex["end"] = pd.to_datetime(ex.end)
    cov0, cov1 = ex.start.min(), ex.end.max()
    out = pd.Series(np.nan, index=F.index); incov = F.Date.between(cov0, cov1)
    for key, items in items_by_key.items():
        m = F.item_id.isin(items); act = pd.Series(0.0, index=F.index)
        for r in ex[ex[keycol] == key].itertuples(): act[F.Date.between(r.start, r.end)] = 1.0
        out[m & incov] = act[m & incov]
    return out


def build(panel, ramadan_eid, holidays, weather, fx, export_events, *, weather_cols, weather_items, weather_lag_days, export_items, fx_strata, cap_days):
    """One row per (item, report day) of the panel, with the kept drivers. Prices are copied, never changed."""
    p = panel[["Date", "item_id", "Product", "eval_stratum", "short_history", "Price_Avg", "gap_2022", "report_idx"]].copy()
    dates = pd.DataFrame({"Date": sorted(p.Date.unique())})
    cal = calendar(dates, ramadan_eid, holidays)
    wx = asof(dates, weather_candidates(weather, weather_lag_days), list(weather_cols), cap_days).drop(columns="available")
    fxa = asof(dates, fx_table(fx), ["fx_lvl", "fx_ch30"], cap_days).drop(columns="available")
    F = p.merge(cal, on="Date", how="left").merge(wx, on="Date", how="left").merge(fxa, on="Date", how="left")
    F["log_price"] = np.log(F.Price_Avg)
    g5 = F.item_id.isin(weather_items); F["has_weather"] = g5.astype(int)
    for i, c in enumerate(weather_cols, 1): F[f"weather_{i}"] = np.where(g5, F[c], np.nan)
    F["own_export_measure"] = event_active(F, export_events, export_items)
    F["has_export_measure"] = F.item_id.isin(sum(export_items.values(), [])).astype(int)
    fxm = F.eval_stratum.isin(fx_strata); F["has_fx"] = fxm.astype(int)
    F["fx_lvl"] = np.where(fxm, F.fx_lvl, np.nan); F["fx_ch30"] = np.where(fxm, F.fx_ch30, np.nan)
    keep = ["Date", "item_id", "Product", "eval_stratum", "short_history", "gap_2022", "report_idx", "Price_Avg", "log_price", *CAL,
            *[f"weather_{i}" for i in range(1, len(weather_cols) + 1)], "has_weather", "own_export_measure", "has_export_measure", "fx_lvl", "fx_ch30", "has_fx"]
    F = F[keep].sort_values(["item_id", "Date"]).reset_index(drop=True)
    assert np.isfinite(F.select_dtypes("number").fillna(0)).all().all(), "inf in features"
    return F
