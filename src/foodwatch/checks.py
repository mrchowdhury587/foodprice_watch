"""Invariants of the data table, as numbers. The notebook asserts them."""
import numpy as np
import pandas as pd

from .features import COLUMNS, FX, WEATHER


def data_checks(D, avail, n_items, weather_items, fx_items, cap_days, gap_reports_expected=24):
    """D: the full table from features.add_drivers (before only COLUMNS are written)."""
    both = D.Price_Min.notna() & D.Price_Max.notna()
    lag = D[["item_id", "Date", "Price_Min"]].copy(); lag["Date"] = lag.Date + pd.Timedelta(days=7)
    wk = D[["item_id", "Date", "Week_Ago_Min"]].merge(lag, on=["item_id", "Date"]).dropna()
    num = D[COLUMNS].select_dtypes("number")
    wx_age = (avail.Date - avail.wx_available).dt.days
    fx_age = (avail.Date - avail.fx_available).dt.days
    w, x = D.item_id.isin(weather_items), D.item_id.isin(fx_items)
    c = dict(rows=len(D), columns=len(COLUMNS), items=int(D.item_id.nunique()), report_days=int(D.Date.nunique()),
             date_min=str(D.Date.min().date()), date_max=str(D.Date.max().date()),
             dup_keys=int(D.duplicated(["Date", "item_id"]).sum()),
             avg_mid_violations=int((both & D.Price_Avg.notna() & ~np.isclose(D.Price_Avg, (D.Price_Min + D.Price_Max) / 2)).sum()),
             min_gt_max=int((D.Price_Min > D.Price_Max).sum()), zero_or_negative=int(D.zero_price.sum()),
             not_reported=int(D.Price_Avg.isna().sum()), gap_2022_reports=int(D.loc[D.gap_2022, "Date"].nunique()),
             week_ago_match_share=round(float(np.isclose(wk.Week_Ago_Min, wk.Price_Min).mean()), 4),
             infinite_values=int((~np.isfinite(num.fillna(0))).sum().sum()),
             weather_items=int(D.loc[w, "item_id"].nunique()), fx_items=int(D.loc[x, "item_id"].nunique()),
             weather_used_before_available=int((wx_age < 0).sum()), fx_used_before_available=int((fx_age < 0).sum()),
             driver_older_than_cap=int(((wx_age > cap_days) | (fx_age > cap_days)).sum()),
             weather_empty_on_weather_items=int(D.loc[w, WEATHER].isna().any(axis=1).sum()),
             fx_empty_on_fx_items=int(D.loc[x, FX].isna().any(axis=1).sum()),
             driver_on_other_items=int(D.loc[~w, WEATHER].notna().any(axis=1).sum() + D.loc[~x, FX].notna().any(axis=1).sum()),
             last_weather_day=str(D.loc[D.wx_tmax_7d.notna(), "Date"].max().date()),
             last_fx_day=str(D.loc[D.fx_lvl.notna(), "Date"].max().date()))
    c["ok"] = (c["items"] == n_items and c["dup_keys"] == 0 and c["avg_mid_violations"] == 0 and c["min_gt_max"] == 0
               and c["gap_2022_reports"] == gap_reports_expected and c["infinite_values"] == 0
               and c["weather_used_before_available"] == 0 and c["fx_used_before_available"] == 0 and c["driver_older_than_cap"] == 0
               and c["driver_on_other_items"] == 0 and c["weather_empty_on_weather_items"] == 0 and c["fx_empty_on_fx_items"] == 0)
    return c


def compare_with_old(D, old_panel, old_features, fx_switch="2024-03-02"):
    """Regression check against the earlier run's panel and features for the same items.
    Prices, day numbers, calendar and weather must be identical. The exchange rate differs by design: the earlier run used Yahoo x 1.0151
    before fx_switch and another source after, so before fx_switch fx_lvl must differ by the constant log(1.0151) and fx_ch30 must match
    wherever the earlier run had a value."""
    key = ["Date", "item_id"]
    op = old_panel[old_panel.item_id.isin(D.item_id.unique())]
    a = D.merge(op, on=key, how="outer", suffixes=("", "_old"), indicator=True)
    out = dict(rows_new=len(D), rows_old=len(op), rows_unmatched=int((a._merge != "both").sum()))
    a = a[a._merge == "both"]
    for c in ["Price_Avg", "report_idx", "reports_since_change", "days_since_prev_report"]:
        out[f"{c}_diff"] = int((~np.isclose(a[c].astype(float).fillna(-1), a[f"{c}_old"].astype(float).fillna(-1))).sum())
    out["gap_2022_diff"] = int((a.gap_2022 != a.gap_2022_old).sum())
    of = old_features[old_features.item_id.isin(D.item_id.unique())].rename(
        columns={"weather_1": "wx_tmax_7d", "weather_2": "wx_tmean_30d", "weather_3": "wx_rain_7d"})
    b = D.merge(of, on=key, how="inner", suffixes=("", "_old"))
    for c in ["month", "dow", "days_to_ramadan", "days_to_eid_fitr", "days_to_eid_adha", "in_ramadan", *WEATHER]:
        out[f"{c}_diff"] = int((~np.isclose(b[c].astype(float).fillna(-999), b[f"{c}_old"].astype(float).fillna(-999))).sum())
    pre = b[(b.Date < pd.Timestamp(fx_switch)) & b.fx_lvl.notna() & b.fx_lvl_old.notna()]
    out["fx_lvl_offset_before_switch"] = round(float((pre.fx_lvl_old - pre.fx_lvl).mean()), 5)
    out["fx_lvl_offset_sd_before_switch"] = round(float((pre.fx_lvl_old - pre.fx_lvl).std()), 6)
    both30 = pre[pre.fx_ch30_old.notna()]
    out["fx_ch30_mismatch_before_switch"] = int((~np.isclose(both30.fx_ch30.fillna(-999), both30.fx_ch30_old, atol=1e-9)).sum())
    out["fx_ch30_filled_where_old_empty"] = int((pre.fx_ch30_old.isna() & pre.fx_ch30.notna()).sum())
    post = b[(b.Date >= pd.Timestamp(fx_switch)) & b.fx_lvl.notna() & b.fx_lvl_old.notna()]
    out["fx_lvl_mean_abs_diff_after_switch"] = round(float((post.fx_lvl_old - post.fx_lvl).abs().mean()), 5)
    out["fx_ch30_mean_abs_diff_after_switch"] = round(float((post.fx_ch30_old - post.fx_ch30).abs().mean()), 5)
    must_be_zero = ["rows_unmatched", "fx_ch30_mismatch_before_switch", *[k for k in out if k.endswith("_diff")]]
    out["ok"] = (all(out[k] == 0 for k in must_be_zero) and abs(out["fx_lvl_offset_before_switch"] - float(np.log(1.0151))) < 1e-4
                 and out["fx_lvl_offset_sd_before_switch"] < 1e-6)
    return out


def item_summary(D, groups):
    """Per item: dates, report days, share not reported, share of reported days with the same price as the previous report.
    Summary rates only, no prices (safe for git). groups: item_id -> item group from settings."""
    rows = []
    for item, g in D.groupby("item_id"):
        r = g[g.Price_Avg.notna() & ~g.gap_2022]
        rows.append(dict(item_id=item, group=groups[item], first_date=str(g.Date.min().date()), last_date=str(g.Date.max().date()),
                         report_days=len(g), share_not_reported=round(float(g.Price_Avg.isna().mean()), 4),
                         share_unchanged=round(float((r.Price_Avg.diff() == 0).iloc[1:].mean()), 4)))
    return pd.DataFrame(rows)
