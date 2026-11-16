"""The item x report-day panel for the 8 items.

Rules: time runs in report days (days TCB published a sheet); a blank or zero price is "not reported" and is never filled;
real jumps are kept; the sparse 2022 period is flagged, never bridged.
"""
import numpy as np
import pandas as pd


def reports_since_change(values):
    """Number of reports since the mid price last changed; NaN where not reported."""
    out, count, last = [], 0, np.nan
    for v in values:
        if pd.isna(v):
            out.append(np.nan); continue
        count = 0 if (pd.isna(last) or v != last) else count + 1
        out.append(count); last = v
    return out


def build(raw, items, gap, groups):
    """raw: all TCB rows (from load.prices). items: the item_ids to keep. gap: (first, last) date of the 2022 gap.
    groups: item_id -> item group. Report days are numbered over the whole file, so report_idx means the same day as before."""
    dates = pd.DataFrame({"Date": sorted(raw.Date.unique())})
    dates["report_idx"] = np.arange(len(dates))
    dates["days_since_prev_report"] = dates.Date.diff().dt.days
    dates["gap_2022"] = dates.Date.between(pd.Timestamp(gap[0]), pd.Timestamp(gap[1]))
    missing = set(items) - set(raw.item_id)
    assert not missing, f"items not in the price file: {sorted(missing)}"
    cols = ["Date", "item_id", "Category", "Product", "Unit", "Price_Min", "Price_Max", "Price_Avg", "Week_Ago_Min"]
    p = raw.loc[raw.item_id.isin(items), cols].merge(dates, on="Date", how="left")
    p = p.sort_values(["item_id", "Date"]).reset_index(drop=True)
    p["zero_price"] = (p[["Price_Min", "Price_Max", "Price_Avg"]] <= 0).any(axis=1)
    p.loc[p.zero_price, "Price_Avg"] = np.nan
    p["is_reported"] = p.Price_Avg.notna()
    p["log_price"] = np.log(p.Price_Avg)
    p["reports_since_change"] = p.groupby("item_id")["Price_Avg"].transform(lambda s: pd.Series(reports_since_change(s.values), index=s.index))
    p["group"] = p.item_id.map(groups)
    return p
