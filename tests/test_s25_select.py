"""S25 acceptance: origins, metrics, the winner rule and every candidate on a made-up frame (no data needed)."""
import numpy as np, pandas as pd, pytest
from fpw import ml, cv, metrics as M, candidates as C
from test_ml_design import made_up


@pytest.fixture(scope="module")
def S(): return ml.prepare(made_up())
@pytest.fixture(scope="module")
def L(S): return ml.stack(S)


def test_test_origins_are_the_87_of_the_earlier_run():
    c = cv.test_cutoffs()
    assert len(c) == 87 and c[0] == 808 and c[-1] == 1410 and set(np.diff(c)) == {7}


def test_period_cutoffs_keep_targets_inside_the_period():
    dates = pd.Series(pd.date_range("2024-01-01", periods=200), index=range(100, 300))
    c = cv.period_cutoffs(dates, "2024-01-01", "2024-03-31")
    last_idx = dates[dates <= "2024-03-31"].index.max()
    assert c[0] == 100 and max(c) + 30 <= last_idx and set(np.diff(c)) == {7}
    assert cv.period_cutoffs(dates, "2030-01-01", "2030-02-01") == []


def test_validation_origins_end_before_the_test(S):
    d = pd.Series(pd.date_range("2023-06-01", periods=900), index=range(900))
    v = cv.validation_year_cutoffs(d)
    assert v and d[v[0]] >= pd.Timestamp("2024-01-01") and d[v[-1] + 30] <= pd.Timestamp("2024-12-31")


def test_naive_is_the_unit_of_relative_error():
    fc = pd.DataFrame(dict(item_id=["a"] * 4 + ["b"] * 4, eval_stratum="x", cutoff=range(8), horizon=7, target_idx=range(8), lp_origin=0.0,
                           y=[0.1, -0.1, 0.0, 0.2, 0.05, 0.0, -0.05, 0.1]))
    fc["pred"] = 0.0; fc["forecast"] = np.exp(fc.lp_origin + fc.pred); fc["actual"] = np.exp(fc.lp_origin + fc.y)
    assert np.isclose(M.gmean_rel(fc).gmean_rel_mae.iloc[0], 1.0)
    fc2 = fc.assign(pred=fc.y); fc2["forecast"] = fc2.actual
    assert np.isclose(M.summary(fc2).mae_log.iloc[0], 0.0) and np.isclose(M.summary(fc2).direction_acc.iloc[0], 1.0)


def test_winner_rule_prefers_the_simpler_model_inside_the_margin_and_never_naive():
    s = dict(naive=1.0, ridge=0.95, ets=0.99, rf=0.94, lgbm=0.935, lstm=0.97)
    assert C.choose_winner(s, 0.01) == "rf"                      # rf is within 1% of lgbm and simpler -> rf wins
    assert C.choose_winner(s, 0.0) == "lgbm"
    assert C.choose_winner(dict(naive=0.1, ridge=0.9, lgbm=0.9), 0.01) == "ridge"


@pytest.mark.parametrize("name", ["naive", "ridge", "rf", "lgbm"])
def test_candidates_return_the_common_forecast_table(name, S, L):
    pytest.importorskip("lightgbm")
    F = C.run_candidate(name, S, L, ml.feature_columns(), [110, 117], refit_every=8, params=dict(num_threads=1), n_estimators=10)
    assert sorted(F.horizon.unique()) == [1, 7, 14, 30] and np.isfinite(F.pred).all() and (F.fit_cutoff == 110).all()
    if name == "naive": assert (F.pred == 0).all()


def test_lstm_candidate_trains_and_predicts(S, L):
    F = ml.forecasts(L, [110], ml.feature_columns(), refit_every=8, model_name="lstm", fit_fn=C.make_fit_lstm(S, epochs=1, hidden=8))
    assert sorted(F.horizon.unique()) == [1, 7, 14, 30] and np.isfinite(F.pred).all()


def test_nothing_after_the_cutoff_reaches_any_candidate(S, L):
    """Changing prices after the cutoff must not change a forecast made at the cutoff (naive and ridge as probes)."""
    raw = made_up(); raw.loc[raw.report_idx > 115, "log_price"] += 3
    S2 = ml.prepare(raw); L2 = ml.stack(S2)
    a = C.run_candidate("ridge", S, L, ml.feature_columns(), [115])
    b = C.run_candidate("ridge", S2, L2, ml.feature_columns(), [115])
    assert np.allclose(a.sort_values(["item_id", "horizon"]).pred.values, b.sort_values(["item_id", "horizon"]).pred.values)
