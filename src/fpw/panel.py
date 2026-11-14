"""Build the item x report-day panel from a TCB price CSV (stage S22). Same derived columns as the earlier S01.

Rules: time index = report days; blank price = not reported (never filled); real jumps kept; suspicious values only flagged.
"""
import numpy as np, pandas as pd


def reports_since_change(s):
    """Per item: number of reports since the mid price last changed; NaN where not reported."""
    out, c, last = [], 0, np.nan
    for v in s:
        if pd.isna(v):
            out.append(np.nan); continue
        c = 0 if (pd.isna(last) or v != last) else c + 1
        out.append(c); last = v
    return out


def build(df, meta, candidates, gap):
    """df: raw price rows (Date parsed). meta: item_meta. candidates: set of (Timestamp, item_id) flagged for the audit.
    gap: (first, last) date of the sparse 2022 period. Returns the panel sorted by item_id, Date."""
    df = df.copy()
    df["item_id"] = df["Product"] + " | " + df["Unit"]
    missing, extra = set(meta.item_id) - set(df.item_id), set(df.item_id) - set(meta.item_id)
    assert not missing and not extra, f"item_id mismatch with item_meta: missing {sorted(missing)}, new {sorted(extra)}"
    dates = pd.DataFrame({"Date": sorted(df.Date.unique())})
    dates["report_idx"] = range(len(dates))
    dates["days_since_prev_report"] = dates.Date.diff().dt.days
    dates["gap_2022"] = dates.Date.between(pd.Timestamp(gap[0]), pd.Timestamp(gap[1]))
    df = df.merge(dates, on="Date", how="left").sort_values(["item_id", "Date"]).reset_index(drop=True)
    df["is_reported"] = df.Price_Avg.notna()
    df["spread_rel"] = (df.Price_Max - df.Price_Min) / df.Price_Avg
    df["reports_since_change"] = df.groupby("item_id")["Price_Avg"].transform(lambda s: pd.Series(reports_since_change(s.values), index=s.index))
    df["flag_min_only"] = df.Price_Min.notna() & df.Price_Max.isna()
    df["flag_audit_candidate"] = [(d, i) in candidates for d, i in zip(df.Date, df.item_id)]
    df = df.merge(meta[["item_id", "eval_stratum", "stratum", "short_history"]], on="item_id", how="left")
    df["exclude_palm_olein"] = df.Product.str.startswith("Palm Olein")
    return df


def checks(df):
    """The S01 invariants as numbers (asserted by the stage and by tests/test_v2_panel.py)."""
    both = df.Price_Min.notna() & df.Price_Max.notna()
    lag = df[["item_id", "Date", "Price_Min"]].copy(); lag["Date"] = lag.Date + pd.Timedelta(days=7)
    m = df[["item_id", "Date", "Week_Ago_Min"]].merge(lag, on=["item_id", "Date"]).dropna()
    return dict(rows=len(df), dates=int(df.Date.nunique()), date_min=str(df.Date.min().date()), date_max=str(df.Date.max().date()),
                items=int(df.item_id.nunique()), dup_keys=int(df.duplicated(["Date", "item_id"]).sum()),
                avg_mid_violations=int((both & ~np.isclose(df.Price_Avg, (df.Price_Min + df.Price_Max) / 2)).sum()),
                min_gt_max=int((df.Price_Min > df.Price_Max).sum()), min_only_rows=int(df.flag_min_only.sum()),
                zero_or_negative=int((df[["Price_Min", "Price_Max", "Price_Avg"]] <= 0).any(axis=1).sum()),
                missing_share=round(float(df.Price_Avg.isna().mean()), 4), gap_2022_reports=int(df.loc[df.gap_2022, "Date"].nunique()),
                week_ago_match_share=round(float(np.isclose(m.Week_Ago_Min, m.Price_Min).mean()), 4), week_ago_n=len(m))


def same_as_base(new_raw, base_raw, last_date, cols):
    """Rows of the extended raw file dated up to last_date must equal the base raw file exactly (values and row count).
    Returns the number of differing cells (0 = identical)."""
    key = ["Date", "Product", "Unit"]
    a = new_raw[new_raw.Date <= pd.Timestamp(last_date)].sort_values(key).reset_index(drop=True)
    b = base_raw.sort_values(key).reset_index(drop=True)
    if len(a) != len(b) or not (a[key].values == b[key].values).all():
        return max(len(a), len(b))
    diff = 0
    for c in cols:
        x, y = a[c], b[c]
        if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y):
            diff += int(((x.isna() != y.isna()) | (x.notna() & y.notna() & ~np.isclose(x.fillna(0), y.fillna(0)))).sum())
        else:
            diff += int((x.fillna("").astype(str) != y.fillna("").astype(str)).sum())
    return diff
