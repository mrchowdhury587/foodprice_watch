"""Driver columns: calendar, exchange rate, weather. Formulas as in the earlier run (archive/old_pipeline/src/fpw/features.py).

Leakage rule: a driver value is used on report day t only if it was available on or before t.
  weather: day d is available from d + lag_days; exchange rate: the last rate dated on or before t.
  A value older than cap_days at t is left empty. Missing stays empty, never 0. A driver an item does not use is empty.
"""
import numpy as np
import pandas as pd

CAL = ["month", "dow", "days_to_ramadan", "days_to_eid_fitr", "days_to_eid_adha", "in_ramadan"]
WEATHER = ["wx_tmax_7d", "wx_tmean_30d", "wx_rain_7d"]
FX = ["fx_lvl", "fx_ch30"]
COLUMNS = ["Date", "item_id", "Price_Min", "Price_Max", "Price_Avg", "report_idx", "gap_2022", "days_since_prev_report",
           "reports_since_change", *CAL, *WEATHER, *FX]


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
    return cal


def weather_table(w, lag_days):
    """Bangladesh mean of locations 0-10, rolled daily. `available` = last day of the window + lag_days."""
    bd = w[w.location_id <= 10].groupby("time").agg(rain=("precipitation_sum", "mean"), tmax=("temperature_2m_max", "mean"),
                                                   tmean=("temperature_2m_mean", "mean")).asfreq("D")
    t = pd.DataFrame({"wx_tmax_7d": bd.tmax.rolling(7).mean(), "wx_tmean_30d": bd.tmean.rolling(30).mean(),
                      "wx_rain_7d": bd.rain.rolling(7).sum()})
    t["available"] = t.index + pd.Timedelta(days=lag_days)
    return t.reset_index(drop=True)


def fx_table(fx, cap_days=7):
    """Log taka per dollar and its change over 30 calendar days. The earlier value is the last quote on or before the date
    30 days back (Yahoo has no Saturday quotes and few on Fridays and Sundays, so an exact-day lookup is often empty)."""
    fx = fx.sort_values("date").copy()
    fx["fx_lvl"] = np.log(fx.bdt_per_usd)
    back = pd.DataFrame({"date": fx.date, "back": fx.date - pd.Timedelta(days=30)})
    prev = pd.merge_asof(back.sort_values("back"), fx[["date", "fx_lvl"]].rename(columns={"date": "prev_date", "fx_lvl": "prev"}),
                         left_on="back", right_on="prev_date", direction="backward").set_index("date")
    prev.loc[(prev.back - prev.prev_date).dt.days > cap_days, "prev"] = np.nan
    fx["fx_ch30"] = fx.fx_lvl - prev.prev.reindex(fx.date).values
    return fx


def add_drivers(panel, ramadan_eid, weather, fx, *, weather_items, fx_items, lag_days, cap_days):
    """The price rows plus calendar, weather and exchange-rate columns (write `COLUMNS` of it to the data file).
    Returns (table, availability) where availability holds the source date used on each report day (for the checks)."""
    dates = pd.DataFrame({"Date": sorted(panel.Date.unique())})
    cal = calendar(dates, ramadan_eid)
    wx = asof(dates, weather_table(weather, lag_days), WEATHER, cap_days).rename(columns={"available": "wx_available"})
    fxa = asof(dates, fx_table(fx, cap_days), FX, cap_days).rename(columns={"available": "fx_available"})
    D = panel.merge(cal, on="Date", how="left").merge(wx, on="Date", how="left").merge(fxa, on="Date", how="left")
    for c in WEATHER:
        D.loc[~D.item_id.isin(weather_items), c] = np.nan
    for c in FX:
        D.loc[~D.item_id.isin(fx_items), c] = np.nan
    D = D.sort_values(["item_id", "Date"]).reset_index(drop=True)
    avail = D[["Date", "item_id", "wx_available", "fx_available"]].copy()
    return D, avail
