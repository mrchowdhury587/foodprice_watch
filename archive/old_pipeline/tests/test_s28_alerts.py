"""S28 acceptance on made-up data: bounds use only errors known at the origin, 3-of-5 persistence, episodes, level choice outside event windows,
event scoring, placebo, coverage near nominal. Wording is checked separately by tests/test_wording.py."""
import numpy as np, pandas as pd, pytest
from fpw import alerts as A

START = pd.Timestamp("2023-01-01")
LEVELS = [0.9, 0.95, 0.975, 0.99]


def synth(n=700, seed=0, spike=None):
    rng = np.random.default_rng(seed); rows = []
    for it in ["A | kg", "B | kg"]:
        for h in (1, 7):
            for c in range(n):
                y = rng.normal(0, 0.02)
                if spike and it == "A | kg" and spike[0] <= c + h <= spike[1]: y += 0.25
                rows.append(dict(item_id=it, eval_stratum="x", cutoff=c, horizon=h, target_idx=c + h, lp_origin=4.0, pred=0.0, y=y))
    fc = pd.DataFrame(rows); fc["tdate"] = START + pd.to_timedelta(fc.target_idx, unit="D"); fc["forecast"] = np.exp(fc.lp_origin + fc.pred)
    return fc


def prepared(fc, h=7, **kw):
    P = A.bounds(fc, h, LEVELS, window=120, min_obs=30)
    return A.flag_alerts(P, LEVELS, k=3, m=5)


def test_bounds_use_only_errors_known_at_the_origin():
    fc = synth(); fc2 = fc.copy(); fc2.loc[fc2.cutoff >= 400, "y"] += 5.0          # errors of origins >= 400 are not known before target 407
    a, b = A.bounds(fc, 7, LEVELS, 120, 30), A.bounds(fc2, 7, LEVELS, 120, 30)
    early = a.cutoff <= 406
    assert np.allclose(a.loc[early, "hi0.975"].fillna(-9), b.loc[early, "hi0.975"].fillna(-9))
    assert not np.allclose(a.loc[~early, "hi0.975"].fillna(-9), b.loc[~early, "hi0.975"].fillna(-9))


def test_no_bound_before_enough_history():
    P = A.bounds(synth(), 7, LEVELS, 120, 30)
    assert P[P.cutoff < 30].filter(like="hi").isna().all().all() and P[P.cutoff > 200]["hi0.975"].notna().all()


def test_persistence_needs_three_of_the_last_five():
    P = pd.DataFrame(dict(item_id="A", tdate=pd.date_range("2024-01-01", periods=12), resid=[0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1.0], **{"hi0.9": 0.5}))
    out = A.flag_alerts(P, [0.9], k=3, m=5)
    assert list(out["exceed0.9"].astype(int)) == [0, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1]
    assert list(out["alert0.9"].astype(int)) == [0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0]
    assert list(A.episodes(out, "alert0.9").index) == [5]                          # one run, counted once


def test_level_is_chosen_outside_the_event_windows_and_never_on_events():
    fc = synth(spike=(600, 640))                                                  # a real rise on item A late in the period
    P = prepared(fc); P["tdate"] = P.tdate
    ev = pd.DataFrame(dict(event_id=[1], product=["A"], onset=[START + pd.Timedelta(days=600)], news_peak=[START + pd.Timedelta(days=620)], end=[START + pd.Timedelta(days=640)]))
    W = A.windows(ev, {"A": ["A | kg"]}, 14, 30)
    level, rule, fa = A.choose_level(P, LEVELS, W, target=2.0, start="2024-06-01", end="2025-01-31")
    assert level in LEVELS and set(fa) == {"0.9", "0.95", "0.975", "0.99"} and "false alarms per item-year" in rule
    assert fa["0.9"] >= fa["0.99"]                                                # a lower level can only raise false alarms


def test_events_are_detected_with_lead_days_and_placebo_is_computed():
    fc = synth(spike=(600, 640)); P = prepared(fc)
    ev = pd.DataFrame(dict(event_id=[1], product=["A"], onset=[START + pd.Timedelta(days=598)], news_peak=[START + pd.Timedelta(days=620)], end=[START + pd.Timedelta(days=640)]))
    W = A.windows(ev, {"A": ["A | kg"]}, 14, 30)
    s = A.score_events(P, "alert0.975", W, ev)
    assert bool(s.detected.iloc[0]) and s.lead_days_vs_news_peak.iloc[0] < 0         # alert starts before the news peak
    pr, n = A.precision(P, "alert0.975", W); assert 0 <= pr <= 1 and n >= 1
    pl = A.placebo(P, "alert0.975", W, ev, draws=50); assert 0 <= pl["placebo_p"] <= 1 and pl["observed_recall"] == 1.0


def test_coverage_is_near_nominal_on_stationary_errors():
    P = A.bounds(synth(n=900), 7, LEVELS, 120, 30)
    q = A.range_quality(P.assign(tdate=P.cutoff), 0.975, by=("horizon",))
    assert abs(q.upper_coverage.iloc[0] - 0.975) < 0.02 and 0.9 < q.interval_coverage.iloc[0] < 0.99 and q.kupiec_p.iloc[0] > 0.01


def test_kupiec_accepts_the_expected_rate_and_rejects_a_far_one():
    assert A.kupiec(25, 1000, 0.025) > 0.9 and A.kupiec(100, 1000, 0.025) < 0.001
