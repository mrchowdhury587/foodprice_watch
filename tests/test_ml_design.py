"""S24 acceptance: one model predicts all four horizons; no target uses a missing or gap-period price; nothing after the cutoff is trained on."""
import numpy as np, pandas as pd, pytest
from fpw import ml
from fpw.project import PCFG

GAP = (40, 49)           # report days of the made-up sparse period
N = 150


def made_up(seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for it, strat in [("A | kg", "volatile_perishable"), ("B | kg", "imported_staple"), ("C | kg", "spice")]:
        lp = 4 + np.cumsum(rng.normal(0, 0.02, N)) * (rng.random(N) < 0.5)      # sticky: about half the days unchanged
        for t in range(N):
            rows.append(dict(item_id=it, Date=pd.Timestamp("2023-01-01") + pd.Timedelta(days=t), eval_stratum=strat, short_history=False,
                             gap_2022=GAP[0] <= t <= GAP[1], report_idx=t, log_price=lp[t]))
    F = pd.DataFrame(rows)
    F.loc[(F.item_id == "B | kg") & F.report_idx.isin([70, 71, 100]), "log_price"] = np.nan      # not reported
    F["Price_Avg"] = np.exp(F.log_price)
    g = PCFG["features"]["groups"]
    for c in g["calendar"] + g["weather"] + g["onion_export_measures"] + g["exchange_rate"]:
        F[c] = rng.normal(size=len(F))
    return F


@pytest.fixture(scope="module")
def S(): return ml.prepare(made_up())
@pytest.fixture(scope="module")
def L(S): return ml.stack(S)


def test_targets_use_only_reported_future_prices(S):
    b = S[S.item_id == "B | kg"].set_index("report_idx")
    assert np.isnan(b.loc[70 - 1, "y1"]) and np.isnan(b.loc[71 - 1, "y1"])           # next day not reported -> no target
    assert np.isnan(b.loc[100 - 7, "y7"])
    t = 120; raw = made_up(); r = raw[raw.item_id == "B | kg"].set_index("report_idx").log_price
    assert np.isclose(b.loc[t, "y7"], r[t + 7] - b.loc[t, "lp"])                     # y = reported future price - carried price today


def test_inputs_carry_the_last_price_but_targets_never_do(S):
    b = S[S.item_id == "B | kg"].set_index("report_idx")
    assert b.loc[70, "lp"] == b.loc[69, "lp"]                                         # input carried forward over a missing report
    assert np.isnan(b.loc[69, "y1"])


def test_features_use_only_the_past():
    a = ml.prepare(made_up()); raw = made_up(); raw.loc[raw.report_idx >= 120, "log_price"] += 5      # change the future
    b = ml.prepare(raw)
    cols = ["lp", "r1", "r7", "r14", "r30", "dev30", "vol30", "rsc"]
    assert np.allclose(a.loc[a.report_idx < 120, cols].fillna(-9).values, b.loc[b.report_idx < 120, cols].fillna(-9).values)


def test_stack_has_all_four_horizons(L):
    assert sorted(L.horizon.unique()) == [1, 7, 14, 30]
    assert len(L) == 4 * len(made_up())


def test_no_training_target_after_the_cutoff(L):
    for c in (100, 120):
        tr = ml.train_rows(L, c)
        assert (tr.target_idx <= c).all() and tr.y.notna().all()


def test_no_training_row_touches_the_gap(L):
    tr = ml.train_rows(L, 140)
    inside = tr.report_idx.between(*GAP) | tr.target_idx.between(*GAP) | ((tr.report_idx < GAP[0]) & (tr.target_idx > GAP[1]))
    assert not inside.any()
    assert not (tr.touch_gap | tr.tgap).any()


def test_one_model_predicts_all_four_horizons(L):
    pytest.importorskip("lightgbm")
    cols = ml.feature_columns()
    assert "horizon" in cols and len(cols) == len(set(cols))
    F = ml.forecasts(L, [110, 117], cols, refit_every=8, params=dict(num_threads=1), n_estimators=20)
    assert sorted(F.horizon.unique()) == [1, 7, 14, 30]
    assert F.groupby(["cutoff", "item_id"]).horizon.nunique().eq(4).all()
    assert (F.fit_cutoff == 110).all()                                                # second origin reuses the first block's model
    assert np.allclose(F.forecast, np.exp(F.lp_origin + F.pred))                      # forecast = price x exp(predicted change)
    ok = F.actual.notna()
    assert np.allclose(np.log(F.actual[ok] / np.exp(F.lp_origin[ok])), F.y[ok])


def test_a_later_origin_gets_a_refit_model(L):
    pytest.importorskip("lightgbm")
    F = ml.forecasts(L, list(range(100, 117)), ml.feature_columns(), refit_every=8, params=dict(num_threads=1), n_estimators=10)
    assert sorted(F.fit_cutoff.unique()) == [100, 108, 116]


def test_groups_cover_every_feature():
    cols = ml.feature_columns(); g = ml.group_of(cols)
    assert set(g) == set(cols) and set(g.values()) == {"price_history", "calendar", "weather", "onion_export_measures", "exchange_rate"}
