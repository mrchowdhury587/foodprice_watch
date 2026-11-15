"""Forecast origins (cutoffs). A cutoff is the last report day a model may see; the targets lie 1..30 report days later.
Rolling origin with an expanding window is the main scheme. No random or stratified k-fold (it would leak the future)."""
import pandas as pd
from .project import PCFG


def test_cutoffs():
    t = PCFG["test"]
    return list(range(int(t["first_cutoff"]), int(t["last_cutoff"]) + 1, int(t["step"])))      # 808..1410 step 7 = 87 origins


def period_cutoffs(dates, start, end, step=7, max_h=30):
    """dates: Series report_idx -> Date. Origins in [start, end] whose longest target still lies inside the period (<= its last report day)."""
    d = dates.sort_index()
    inside = d[(d >= pd.Timestamp(start)) & (d <= pd.Timestamp(end))]
    if inside.empty:
        return []
    return list(range(int(inside.index.min()), int(inside.index.max()) - max_h + 1, step))


def validation_year_cutoffs(dates):
    t = PCFG["validation"]
    return period_cutoffs(dates, t["tune"][0], t["confirm"][1])


def tune_cutoffs(dates):
    return period_cutoffs(dates, *PCFG["validation"]["tune"])


def confirm_cutoffs(dates):
    return period_cutoffs(dates, *PCFG["validation"]["confirm"])


def walk_forward_cutoffs(dates, years=(2023, 2024)):
    """Year-by-year walk-forward: origins inside each calendar year (2024 is the tuning year and is labelled as such). 2025-26 is the main test."""
    return {y: period_cutoffs(dates, f"{y}-01-01", f"{y}-12-31") for y in years}
