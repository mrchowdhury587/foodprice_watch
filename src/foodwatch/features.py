"""Driver features: calendar, exchange rate, weather. Formulas as in the earlier run (archive/old_pipeline/src/fpw/features.py).

Leakage rule: a driver value is used on report day t only if it was available on or before t.
  weather: day d is available from d + lag_days; exchange rate: the last rate dated on or before t.
  A value older than cap_days at t is left empty. Missing stays empty, never 0.
"""
import numpy as np
import pandas as pd

CAL = ["month", "dow", "days_to_ramadan", "days_to_eid_fitr", "days_to_eid_adha", "in_ramadan", "days_since_prev_report"]


def asof(dates, src, valcols, cap_days):
    """For each report date: the last row of src with available <= Date; empty if that row is older than cap_days.
    Keeps `available` so the caller can check it."""
    s = src.sort_values("available")[["available", *valcols]].dropna(subset=valcols, how="all")
    out = pd.merge_asof(dates[["Date"]], s, left_on="Date", right_on="available", direction="backward")
    stale = (out.Date - out.available).dt.days > cap_days
    out.loc[stale, valcols] = np.nan
    out.loc[stale, "available"] = pd.NaT
    return out


def days_to_next(ds, events):
    ev = np.sort(pd.to_datetime(pd.Series(events)).values)
    idx = np.searchsorted(ev, ds.values)
    nxt = np.where(idx < len(ev), ev[np.minimum(idx, len(ev) - 1)], np.datetime64("NaT"))
    return (pd.to_datetime(nxt) - ds).dt.days


def calendar(dates, ramadan_eid):
    """Known in advance. ramadan_eid: ramadan_start, eid_ul_fitr, eid_ul_adha (';' separates two Eid al-Adha dates in one year)."""
    re_ = ramadan_eid.copy()
    adha = pd.to_datetime(re_.eid_ul_adha.astype(str).str.split(";").explode().str.strip())
    for c in ["ramadan_start", "eid_ul_fitr"]:
        re_[c] = pd.to_datetime(re_[c])
    cal = dates[["Date"]].copy()
    cal["month"] = cal.Date.dt.month
    cal["dow"] = cal.Date.dt.dayofweek
    cal["days_to_ramadan"] = days_to_next(cal.Date, re_.ramadan_start)
    cal["days_to_eid_fitr"] = days_to_next(cal.Date, re_.eid_ul_fitr)
    cal["days_to_eid_adha"] = days_to_next(cal.Date, adha)
    cal["in_ramadan"] = False
    for r in re_.itertuples():
        cal.loc[cal.Date.between(r.ramadan_start, r.eid_ul_fitr - pd.Timedelta(days=1)), "in_ramadan"] = True
    cal["days_since_prev_report"] = cal.Date.diff().dt.days
    return cal


def weather_table(w, lag_days):
    """Bangladesh mean of locations 0-10, rolled daily. `available` = last day of the window + lag_days."""
    bd = w[w.location_id <= 10].groupby("time").agg(rain=("precipitation_sum", "mean"), tmax=("temperature_2m_max", "mean"),
                                                   tmean=("temperature_2m_mean", "mean")).asfreq("D")
    t = pd.DataFrame({"wx_bd_rain_7d": bd.rain.rolling(7).sum(), "wx_bd_tmax_7d": bd.tmax.rolling(7).mean(),
                      "wx_bd_tmean_30d": bd.tmean.rolling(30).mean()})
    t["available"] = t.index + pd.Timedelta(days=lag_days)
    return t.reset_index(drop=True)


def fx_table(fx):
    """Log taka per dollar and its change over 30 calendar days."""
    fx = fx.sort_values("date").copy()
    fx["fx_lvl"] = np.log(fx.bdt_per_usd)
    fx["fx_ch30"] = fx.fx_lvl - fx.set_index("date").fx_lvl.shift(30, freq="D").reindex(fx.date).values
    return fx


def build(panel, ramadan_eid, weather, fx, *, weather_cols, weather_items, fx_items, lag_days, cap_days):
    """One row per (item, report day) of the panel. Prices are copied, never changed.
    Returns (features, availability) where availability holds the source date used for each report day (for the checks)."""
    p = panel[["Date", "item_id", "group", "gap_2022", "report_idx", "is_reported", "Price_Avg", "log_price"]].copy()
    dates = pd.DataFrame({"Date": sorted(p.Date.unique())})
    cal = calendar(dates, ramadan_eid)
    wx = asof(dates, weather_table(weather, lag_days), list(weather_cols), cap_days).rename(columns={"available": "wx_available"})
    fxa = asof(dates, fx_table(fx), ["fx_lvl", "fx_ch30"], cap_days).rename(columns={"available": "fx_available"})
    F = p.merge(cal, on="Date", how="left").merge(wx, on="Date", how="left").merge(fxa, on="Date", how="left")
    w = F.item_id.isin(weather_items)
    F["has_weather"] = w.astype(int)
    for i, c in enumerate(weather_cols, 1):
        F[f"weather_{i}"] = np.where(w, F[c], np.nan)
    x = F.item_id.isin(fx_items)
    F["has_fx"] = x.astype(int)
    F["fx_lvl"] = np.where(x, F.fx_lvl, np.nan)
    F["fx_ch30"] = np.where(x, F.fx_ch30, np.nan)
    avail = F[["Date", "item_id", "wx_available", "fx_available"]].copy()
    keep = ["Date", "item_id", "group", "gap_2022", "report_idx", "is_reported", "Price_Avg", "log_price", *CAL,
            *[f"weather_{i}" for i in range(1, len(weather_cols) + 1)], "has_weather", "fx_lvl", "fx_ch30", "has_fx"]
    F = F[keep].sort_values(["item_id", "Date"]).reset_index(drop=True)
    return F, avail
