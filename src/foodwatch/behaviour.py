"""Price behaviour study (notebook 03): how often and how much the 8 prices move, and their sustained rise episodes.

Descriptive only, no model. Rules: the 2022 gap is never bridged; a blank price is "not reported", never a zero change;
real jumps are kept. A day-to-day change is counted only between two consecutive report days that are both reported and
both outside the 2022 gap. Output tables hold rates, counts, sizes of changes and dates, never a price series.

Rise reference (unchanged from the earlier run, archive/old_pipeline/src/fpw/rises.py): R = P_t / P_(t-w) - 1 over w report
days; a rise day has R >= threshold; an episode is a run of at least `persist` consecutive rise days; episodes of one item
closer than `merge_gap` report days are merged. A window that touches the 2022 gap gives no R.
"""
import numpy as np
import pandas as pd


def pairs(D):
    """One row per item and report day that has a valid day-to-day change."""
    D = D.sort_values(["item_id", "report_idx"]).reset_index(drop=True)
    g = D.groupby("item_id")
    prev_p, prev_idx, prev_gap = g.Price_Avg.shift(), g.report_idx.shift(), g.gap_2022.shift()
    ok = ((D.report_idx - prev_idx) == 1) & ~D.gap_2022 & prev_gap.eq(False) & D.Price_Avg.notna() & prev_p.notna()
    P = D.loc[ok, ["item_id", "Date", "report_idx"]].copy()
    P["ch_tk"] = (D.Price_Avg - prev_p)[ok]
    P["ch_pct"] = (D.Price_Avg / prev_p - 1)[ok]
    P["changed"] = P.ch_tk != 0
    P["year"] = P.Date.dt.year
    return P.reset_index(drop=True)


def change_frequency(P):
    """Share of report days on which the price changed (and moved up / down), by item and year, plus all years."""
    def agg(x):
        return pd.Series(dict(report_days=len(x), share_changed=x.changed.mean(),
                              share_up=(x.ch_tk > 0).mean(), share_down=(x.ch_tk < 0).mean()))
    by_year = P.groupby(["item_id", "year"]).apply(agg, include_groups=False).reset_index()
    total = P.groupby("item_id").apply(agg, include_groups=False).reset_index().assign(year="all")
    out = pd.concat([by_year.astype({"year": str}), total], ignore_index=True)
    out["report_days"] = out.report_days.astype(int)
    return out.round(4)


def change_size(P):
    """On days the price changed: size of the change in Tk and in percent, by item."""
    rows = []
    for item, x in P[P.changed].groupby("item_id"):
        a, pct = x.ch_tk.abs(), x.ch_pct.abs() * 100
        rows.append(dict(item_id=item, changes=len(x), share_up=round((x.ch_tk > 0).mean(), 4),
                         median_abs_tk=a.median(), p95_abs_tk=round(a.quantile(0.95), 2),
                         median_abs_pct=round(pct.median(), 2), p95_abs_pct=round(pct.quantile(0.95), 2),
                         largest_up_pct=round(x.ch_pct.max() * 100, 2), largest_down_pct=round(x.ch_pct.min() * 100, 2)))
    return pd.DataFrame(rows)


def unchanged_runs(P):
    """Runs of consecutive report days with no price change, by item. A run ends at a change, a blank price or the 2022 gap."""
    g = P.sort_values(["item_id", "report_idx"]).copy()
    g["block"] = (g.changed | (g.groupby("item_id").report_idx.diff() != 1)).cumsum()
    runs = g[~g.changed].groupby(["item_id", "block"]).agg(days=("report_idx", "size"), start=("Date", "min"), end=("Date", "max")).reset_index()
    rows = []
    for item, r in runs.groupby("item_id"):
        top = r.loc[r.days.idxmax()]
        rows.append(dict(item_id=item, runs=len(r), mean_days=round(r.days.mean(), 2), median_days=r.days.median(),
                         p90_days=round(r.days.quantile(0.9), 1), longest_days=int(top.days),
                         longest_from=str(top.start.date()), longest_to=str(top.end.date())))
    return pd.DataFrame(rows)


def price_step(P):
    """Smallest and most common size of a price change, in Tk, by item (TCB reports whole taka for Min and Max)."""
    rows = []
    for item, x in P[P.changed].groupby("item_id"):
        a = x.ch_tk.abs().round(2)
        rows.append(dict(item_id=item, smallest_step_tk=a.min(), most_common_step_tk=a.mode().iloc[0],
                         share_steps_multiple_of_0_5=round(float(np.isclose(a * 2, np.round(a * 2)).mean()), 4)))
    return pd.DataFrame(rows)


def rise_days(D, w):
    """Per item and report day: R = P_t / P_(t-w report days) - 1. NaN if either price is blank or the window touches the 2022 gap."""
    D = D.sort_values(["item_id", "report_idx"]).reset_index(drop=True)
    s = D.set_index(["item_id", "report_idx"]).Price_Avg
    prev = s.reindex(pd.MultiIndex.from_arrays([D.item_id.values, D.report_idx.values - w])).values
    gap = D.loc[D.gap_2022, "report_idx"]
    g0, g1 = (int(gap.min()), int(gap.max())) if len(gap) else (10 ** 9, -10 ** 9)
    touch = (D.report_idx.values >= g0) & (D.report_idx.values - w <= g1)
    R = np.where(touch, np.nan, D.Price_Avg.values / prev - 1)
    out = D[["item_id", "Date", "report_idx"]].copy()
    out["R"] = R
    return out


def episodes(Rd, threshold, persist, merge_gap):
    """Sustained rise episodes: runs of >= persist consecutive report days with R >= threshold; merged when closer than merge_gap."""
    rows = []
    dates = Rd.drop_duplicates("report_idx").set_index("report_idx").Date
    for item, g in Rd.sort_values("report_idx").groupby("item_id"):
        idx, R = g.report_idx.values, g.R.values
        fl = np.nan_to_num(R, nan=-1.0) >= threshold
        runs, i = [], 0
        while i < len(g):
            if fl[i]:
                j = i
                while j + 1 < len(g) and fl[j + 1] and idx[j + 1] == idx[j] + 1:
                    j += 1
                if j - i + 1 >= persist:
                    runs.append([int(idx[i]), int(idx[j]), float(np.nanmax(R[i:j + 1]))])
                i = j + 1
            else:
                i += 1
        merged = []
        for r in runs:
            if merged and r[0] - merged[-1][1] < merge_gap:
                merged[-1][1] = r[1]; merged[-1][2] = max(merged[-1][2], r[2])
            else:
                merged.append(r)
        rows += [dict(item_id=item, onset_idx=a, end_idx=b, onset_date=dates[a], end_date=dates[b],
                      length_reports=b - a + 1, peak_rise=round(p, 4)) for a, b, p in merged]
    return pd.DataFrame(rows, columns=["item_id", "onset_idx", "end_idx", "onset_date", "end_date", "length_reports", "peak_rise"])


def episodes_by_item_year(Rd, eps_by_threshold, main):
    """Episode counts per item and onset year for each threshold, plus, for the main threshold, the share of report days
    that are rise days and the median episode length and peak."""
    Rd = Rd.assign(year=Rd.Date.dt.year)
    out = Rd[Rd.R.notna()].groupby(["item_id", "year"]).R.apply(lambda r: round(float((r >= main).mean()), 4)).rename("share_rise_days").reset_index()
    for thr, E in eps_by_threshold.items():
        c = E.assign(year=E.onset_date.dt.year).groupby(["item_id", "year"]).size().rename(f"episodes_{round(thr * 100)}pct")
        out = out.merge(c.reset_index(), on=["item_id", "year"], how="left")
    E = eps_by_threshold[main].assign(year=lambda e: e.onset_date.dt.year)
    m = E.groupby(["item_id", "year"]).agg(median_length_reports=("length_reports", "median"), median_peak_rise=("peak_rise", "median")).reset_index()
    out = out.merge(m, on=["item_id", "year"], how="left")
    cnt = [c for c in out if c.startswith("episodes_")]
    out[cnt] = out[cnt].fillna(0).astype(int)
    return out


def ramadan(Rd, D, window_days, w, threshold):
    """Median w-report change in the window_days before Ramadan against all other days, by item. Descriptive only."""
    X = Rd.merge(D[["item_id", "Date", "days_to_ramadan", "in_ramadan"]], on=["item_id", "Date"]).dropna(subset=["R"])
    pre = ~X.in_ramadan & X.days_to_ramadan.between(1, window_days)
    rows = []
    for item, x in X.assign(pre=pre).groupby("item_id"):
        a, b = x[x.pre], x[~x.pre]
        rows.append(dict(item_id=item, days_before_ramadan=len(a), ramadans=int(a.Date.dt.year.nunique()),
                         median_change_before_ramadan_pct=round(a.R.median() * 100, 2), median_change_other_days_pct=round(b.R.median() * 100, 2),
                         share_rise_days_before_ramadan=round(float((a.R >= threshold).mean()), 4), share_rise_days_other=round(float((b.R >= threshold).mean()), 4)))
    out = pd.DataFrame(rows)
    out.attrs["window"] = f"{w}-report change; before Ramadan = 1 to {window_days} days before its first day"
    return out
