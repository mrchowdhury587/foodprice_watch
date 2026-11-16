"""S34 on made-up prices: rise days and episodes, persistence, merging, the 2022 gap, one-to-one matching, precision/recall/F1, placebo, prereg determinism."""
import numpy as np, pandas as pd
from fpw import rises as R, prereg


def panel(prices_a, prices_b=None, gap=()):
    rows = []
    for it, ps in (("A | kg", prices_a), ("B | kg", prices_b if prices_b is not None else [100.0] * len(prices_a))):
        for i, p in enumerate(ps):
            rows.append(dict(item_id=it, report_idx=i, log_price=np.log(p) if p == p else np.nan, gap_2022=i in gap))
    return pd.DataFrame(rows)


def test_rise_needs_the_threshold_over_the_window_and_persistence():
    p = [100.0] * 20 + [115.0] * 8 + [100.0] * 20                       # +15 % for 8 report days, then back
    D = R.rise_days(panel(p), w=14, thr=0.10)
    assert D[(D.item_id == "A | kg") & D.rise].report_idx.min() == 20       # R compares with the price 14 report days earlier
    E = R.episodes(D, persist=5, merge_gap=14)
    assert list(E.item_id) == ["A | kg"] and E.onset_idx.iloc[0] == 20 and E.peak_R.iloc[0] > 0.14
    short = R.episodes(R.rise_days(panel([100.0] * 20 + [115.0] * 3 + [100.0] * 25), 14, 0.10), persist=5, merge_gap=14)
    assert short.empty                                                   # 3 days is too short to count


def test_nearby_runs_of_one_item_merge_and_far_runs_do_not():
    base = [100.0] * 20
    near = base + [120.0] * 6 + [100.0] * 3 + [125.0] * 6 + [100.0] * 20
    far = base + [120.0] * 6 + [100.0] * 40 + [125.0] * 6 + [100.0] * 20
    assert len(R.episodes(R.rise_days(panel(near), 14, 0.10), 5, 14)) <= 2
    assert len(R.episodes(R.rise_days(panel(far), 14, 0.10), 5, 14)) == 2


def test_missing_prices_and_the_2022_gap_never_make_a_rise():
    p = [100.0] * 10 + [np.nan] * 10 + [130.0] * 10
    D = R.rise_days(panel(p), 14, 0.10)
    a = D[D.item_id == "A | kg"].set_index("report_idx").rise
    assert not a.loc[:19].any() and not a.loc[24:].any() and a.loc[20:23].all()   # R needs both prices reported: days 24+ compare with unreported days
    g = R.rise_days(panel([100.0] * 10 + [150.0] * 20, gap=range(5, 12)), 14, 0.10)
    assert not g[(g.item_id == "A | kg") & (g.report_idx <= 25)].rise.any()   # windows touching the gap are excluded


def test_matching_is_one_to_one_on_the_same_item_inside_the_window():
    eps = pd.DataFrame(dict(item_id=["A", "A", "B"], onset_idx=[100, 200, 100], end_idx=[110, 210, 110], peak_R=[.2, .2, .2]))
    runs = pd.DataFrame(dict(item_id=["A", "A", "B", "A"], start_idx=[95, 98, 300, 500]))
    e, r = R.match(runs, eps, before=14, after=7)
    assert list(e.detected) == [True, False, False]                       # one run per episode; B's only run is far away
    assert list(r.matched) == [True, False, False, False]                 # the second run in the same window stays unmatched
    assert e.delay_reports.iloc[0] == -5
    s = R.prf(e, r); assert abs(s["recall"] - 1 / 3) < 1e-9 and abs(s["precision"] - 0.25) < 1e-9 and abs(s["f1"] - 2 * (1 / 3) * 0.25 / (1 / 3 + 0.25)) < 1e-9


def test_placebo_is_low_when_alerts_sit_on_the_episodes_and_is_reproducible():
    eps = pd.DataFrame(dict(item_id=["A", "B", "C"] * 3, onset_idx=[100, 100, 100, 400, 400, 400, 700, 700, 700], end_idx=[110, 110, 110, 410, 410, 410, 710, 710, 710], peak_R=.2))
    runs = eps.assign(start_idx=eps.onset_idx + 1)[["item_id", "start_idx"]]
    a = R.placebo(runs, eps, 14, 7, 0, 1000, draws=100); b = R.placebo(runs, eps, 14, 7, 0, 1000, draws=100)
    assert a["observed_recall"] == 1.0 and a["placebo_p"] < 0.1 and a["placebo_mean"] < 0.3 and a == b


def test_prereg_s34_is_deterministic_and_states_the_rule_and_labels():
    t = prereg.s34(0.95); assert t == prereg.s34(0.95)
    for s in ("window_reports: 14", "threshold: 0.1", "persist_reports: 5", "retrospective", "news_used: false", "tuned_on_shock_episodes: false"):
        assert s in t
