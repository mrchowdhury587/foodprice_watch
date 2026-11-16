"""Invariants of the panel and the features, as numbers. The notebook asserts them."""
import numpy as np
import pandas as pd


def panel_checks(p, n_items, gap_reports_expected=24):
    both = p.Price_Min.notna() & p.Price_Max.notna()
    lag = p[["item_id", "Date", "Price_Min"]].copy(); lag["Date"] = lag.Date + pd.Timedelta(days=7)
    wk = p[["item_id", "Date", "Week_Ago_Min"]].merge(lag, on=["item_id", "Date"]).dropna()
    c = dict(rows=len(p), items=int(p.item_id.nunique()), report_days=int(p.Date.nunique()),
             date_min=str(p.Date.min().date()), date_max=str(p.Date.max().date()),
             dup_keys=int(p.duplicated(["Date", "item_id"]).sum()),
             avg_mid_violations=int((both & p.Price_Avg.notna() & ~np.isclose(p.Price_Avg, (p.Price_Min + p.Price_Max) / 2)).sum()),
             min_gt_max=int((p.Price_Min > p.Price_Max).sum()), zero_or_negative=int(p.zero_price.sum()),
             not_reported=int((~p.is_reported).sum()), gap_2022_reports=int(p.loc[p.gap_2022, "Date"].nunique()),
             week_ago_match_share=round(float(np.isclose(wk.Week_Ago_Min, wk.Price_Min).mean()), 4))
    c["ok"] = (c["items"] == n_items and c["dup_keys"] == 0 and c["avg_mid_violations"] == 0 and c["min_gt_max"] == 0
               and c["gap_2022_reports"] == gap_reports_expected)
    return c


def feature_checks(F, avail, lag_days, cap_days):
    num = F.select_dtypes("number")
    wx_age = (avail.Date - avail.wx_available).dt.days
    fx_age = (avail.Date - avail.fx_available).dt.days
    c = dict(rows=len(F), columns=list(F.columns),
             infinite_values=int((~np.isfinite(num.fillna(0))).sum().sum()),
             weather_items=int(F.loc[F.has_weather == 1, "item_id"].nunique()),
             fx_items=int(F.loc[F.has_fx == 1, "item_id"].nunique()),
             weather_used_before_available=int((wx_age < 0).sum()),
             fx_used_before_available=int((fx_age < 0).sum()),
             driver_older_than_cap=int(((wx_age > cap_days) | (fx_age > cap_days)).sum()),
             weather_empty_on_weather_items=int(F.loc[F.has_weather == 1, "weather_1"].isna().sum()),
             fx_empty_on_fx_items=int(F.loc[F.has_fx == 1, "fx_lvl"].isna().sum()),
             fx_ch30_empty_on_fx_items=int(F.loc[F.has_fx == 1, "fx_ch30"].isna().sum()),
             driver_on_unmapped_items=int(F.loc[F.has_weather == 0, "weather_1"].notna().sum() + F.loc[F.has_fx == 0, "fx_lvl"].notna().sum()),
             last_weather_day=str(F.loc[F.weather_1.notna(), "Date"].max().date()),
             last_fx_day=str(F.loc[F.fx_lvl.notna(), "Date"].max().date()))
    c["ok"] = (c["infinite_values"] == 0 and c["weather_used_before_available"] == 0 and c["fx_used_before_available"] == 0
               and c["driver_older_than_cap"] == 0 and c["driver_on_unmapped_items"] == 0
               and c["fx_ch30_empty_on_fx_items"] <= 0.01 * max(1, int((F.has_fx == 1).sum())))
    return c


def compare_with_old(p, F, old_panel, old_features, fx_switch="2024-03-02"):
    """Regression check against the earlier run's panel and features for the same items.
    Panel and calendar/weather columns must be identical. The exchange rate differs by design: the earlier run used Yahoo x 1.0151
    before fx_switch and another source after, so before fx_switch fx_lvl must differ by the constant log(1.0151) and fx_ch30 must match
    wherever the earlier run had a value."""
    key = ["Date", "item_id"]
    op = old_panel[old_panel.item_id.isin(p.item_id.unique())]
    a = p.merge(op, on=key, how="outer", suffixes=("", "_old"), indicator=True)
    out = dict(panel_rows_new=len(p), panel_rows_old=len(op), panel_rows_unmatched=int((a._merge != "both").sum()))
    a = a[a._merge == "both"]
    out["price_avg_diff"] = int((~np.isclose(a.Price_Avg.fillna(-1), a.Price_Avg_old.fillna(-1))).sum())
    out["report_idx_diff"] = int((a.report_idx != a.report_idx_old).sum())
    out["is_reported_diff"] = int((a.is_reported != a.is_reported_old).sum())
    out["reports_since_change_diff"] = int((~np.isclose(a.reports_since_change.fillna(-1), a.reports_since_change_old.fillna(-1))).sum())
    of = old_features[old_features.item_id.isin(F.item_id.unique())]
    b = F.merge(of, on=key, how="inner", suffixes=("", "_old"))
    for c in ["month", "dow", "days_to_ramadan", "days_to_eid_fitr", "days_to_eid_adha", "in_ramadan", "days_since_prev_report",
              "weather_1", "weather_2", "weather_3", "has_weather", "has_fx"]:
        out[f"{c}_diff"] = int((~np.isclose(b[c].astype(float).fillna(-999), b[f"{c}_old"].astype(float).fillna(-999))).sum())
    pre = b[(b.Date < pd.Timestamp(fx_switch)) & b.fx_lvl.notna() & b.fx_lvl_old.notna()]
    out["fx_lvl_offset_before_switch"] = round(float((pre.fx_lvl_old - pre.fx_lvl).mean()), 5)
    out["fx_lvl_offset_sd_before_switch"] = round(float((pre.fx_lvl_old - pre.fx_lvl).std()), 6)
    # the earlier run left fx_ch30 empty when no quote existed exactly 30 days back; compare only where it had a value
    both30 = pre[pre.fx_ch30_old.notna()]
    out["fx_ch30_diff_before_switch"] = int((~np.isclose(both30.fx_ch30.fillna(-999), both30.fx_ch30_old, atol=1e-9)).sum())
    out["fx_ch30_filled_where_old_empty"] = int((pre.fx_ch30_old.isna() & pre.fx_ch30.notna()).sum())
    post = b[(b.Date >= pd.Timestamp(fx_switch)) & b.fx_lvl.notna() & b.fx_lvl_old.notna()]
    out["fx_lvl_mean_abs_diff_after_switch"] = round(float((post.fx_lvl_old - post.fx_lvl).abs().mean()), 5)
    out["fx_ch30_mean_abs_diff_after_switch"] = round(float((post.fx_ch30_old - post.fx_ch30).abs().mean()), 5)
    same = ["panel_rows_unmatched", "price_avg_diff", "report_idx_diff", "is_reported_diff", "reports_since_change_diff",
            *[k for k in out if k.endswith("_diff") and not k.startswith("fx")], "fx_ch30_diff_before_switch"]
    out["ok"] = (all(out[k] == 0 for k in same) and abs(out["fx_lvl_offset_before_switch"] - float(np.log(1.0151))) < 1e-4
                 and out["fx_lvl_offset_sd_before_switch"] < 1e-6)
    return out


def item_summary(p):
    """Per item: dates, report days, share not reported, share of reported days with the same price as the previous report.
    Summary rates only, no prices (safe for git)."""
    rows = []
    for item, g in p.groupby("item_id"):
        r = g[g.is_reported & ~g.gap_2022]
        rows.append(dict(item_id=item, group=g.group.iloc[0], first_date=str(g.Date.min().date()), last_date=str(g.Date.max().date()),
                         report_days=len(g), share_not_reported=round(float((~g.is_reported).mean()), 4),
                         share_unchanged=round(float((r.Price_Avg.diff() == 0).iloc[1:].mean()), 4)))
    return pd.DataFrame(rows)
