"""S34 TCB price-rise reference for alerts (docs/PROJECT_DESIGN_DRAFT.md section 12).

A rise is defined from reported TCB prices only, so it does not depend on the forecast bounds (the alert is not judged by itself):
R = P_t / P_(t-w) - 1 on report days; a rise episode is a run of at least `persist` consecutive report days with R >= threshold.
Alert runs (first day of an uninterrupted alert) are matched one-to-one with rise episodes of the same item. Positions are report-day indices."""
import numpy as np, pandas as pd


def rise_days(F, w, thr):
    """Per (item, report day): R and the rise flag. F needs item_id, report_idx, log_price (NaN = not reported) and gap_2022. Windows that touch the sparse 2022 period give NaN."""
    F = F.sort_values(["item_id", "report_idx"]).reset_index(drop=True)
    s = F.set_index(["item_id", "report_idx"]).log_price
    prev = s.reindex(pd.MultiIndex.from_arrays([F.item_id.values, F.report_idx.values - w])).values
    gap = F.loc[F.gap_2022, "report_idx"]
    g0, g1 = (int(gap.min()), int(gap.max())) if len(gap) else (10 ** 9, -10 ** 9)
    touch = (F.report_idx.values >= g0) & (F.report_idx.values - w <= g1)
    R = np.exp(F.log_price.values - prev) - 1
    R = np.where(touch, np.nan, R)
    out = F[["item_id", "report_idx"]].copy(); out["R"] = R; out["rise"] = np.nan_to_num(R, nan=-1.0) >= thr
    return out


def episodes(D, persist, merge_gap):
    """Runs of consecutive rise days of one item with length >= persist; runs closer than merge_gap report days are merged. Returns item_id, onset_idx, end_idx, peak_R."""
    rows = []
    for it, g in D.groupby("item_id"):
        g = g.sort_values("report_idx"); idx = g.report_idx.values; fl = g.rise.values; R = g.R.values
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
        rows += [dict(item_id=it, onset_idx=a, end_idx=b, peak_R=p) for a, b, p in merged]
    return pd.DataFrame(rows, columns=["item_id", "onset_idx", "end_idx", "peak_R"])


def match(runs, eps, before, after):
    """One-to-one: each episode (in time order) takes the earliest unmatched alert run of the same item that starts from `before` report days before the onset to `after` after the end.
    runs: item_id, start_idx. Returns (eps with detected and delay_reports, runs with matched)."""
    eps = eps.sort_values(["onset_idx", "item_id"]).reset_index(drop=True).copy(); runs = runs.reset_index(drop=True).copy()
    runs["matched"] = False; eps["detected"] = False; eps["delay_reports"] = np.nan
    for i, e in eps.iterrows():
        c = runs[(runs.item_id == e.item_id) & ~runs.matched & (runs.start_idx >= e.onset_idx - before) & (runs.start_idx <= e.end_idx + after)].sort_values("start_idx")
        if len(c):
            runs.loc[c.index[0], "matched"] = True; eps.loc[i, "detected"] = True; eps.loc[i, "delay_reports"] = float(c.start_idx.iloc[0] - e.onset_idx)
    return eps, runs


def prf(eps, runs):
    """Recall = detected episodes / episodes; precision = matched alert runs / alert runs; F1 of the two."""
    rec = float(eps.detected.mean()) if len(eps) else np.nan
    pre = float(runs.matched.mean()) if len(runs) else np.nan
    f1 = 2 * pre * rec / (pre + rec) if np.isfinite(pre) and np.isfinite(rec) and (pre + rec) > 0 else np.nan
    return dict(episodes=int(len(eps)), detected=int(eps.detected.sum()), recall=rec, alert_runs=int(len(runs)), matched_runs=int(runs.matched.sum()), precision=pre, f1=f1,
                median_delay_reports=float(eps.delay_reports.median()) if eps.detected.any() else np.nan)


def placebo(runs, eps, before, after, lo, hi, draws=300, seed=42):
    """Random-date control: the alert-run dates of each item are shifted by a random whole number of report days (wrapping inside [lo, hi]); recall is recomputed.
    Returns the observed recall, the mean placebo recall and the share of draws at least as high as observed (p, with the +1 correction)."""
    rng = np.random.default_rng(seed); span = hi - lo + 1
    obs = match(runs, eps, before, after)[0].detected.mean()
    out = []
    for _ in range(draws):
        sh = runs.copy(); off = {it: int(rng.integers(1, span)) for it in sh.item_id.unique()}
        sh["start_idx"] = lo + (sh.start_idx - lo + sh.item_id.map(off)) % span
        out.append(match(sh[["item_id", "start_idx"]], eps, before, after)[0].detected.mean())
    out = np.array(out)
    return dict(observed_recall=float(obs), placebo_mean=float(out.mean()), placebo_p=float(((out >= obs).sum() + 1) / (draws + 1)), draws=draws)
